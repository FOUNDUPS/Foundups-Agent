"""Verifier-owned canonical-registry scope resolution for exact Git archives."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

from modules.infrastructure.wre_core.scripts.generate_test_registry import (
    build_registry, canonical_bytes,
)
from modules.infrastructure.wre_core.src.wre_test_registry import (
    CanonicalTestRegistry, REGISTRY_PATH, load_canonical_test_registry,
)
from modules.infrastructure.wre_core.src.wre_test_registry_classification import (
    owner_for_path,
)
from modules.infrastructure.wre_core.src.wre_test_scope_coverage import (
    resolve_test_scope_coverage,
)

FAIL_PROJECTION = "FAIL_TEST_REGISTRY_PROJECTION"
FAIL_SCOPE = "FAIL_TEST_REGISTRY_SCOPE"
FAIL_BOUNDS = "FAIL_TEST_REGISTRY_BOUNDS"
FAIL_QUARANTINED_CHANGED_TEST = "FAIL_QUARANTINED_CHANGED_TEST"
MAX_PROJECTED_TEST_FILES = 4096
MAX_REGISTRY_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True)
class RegistrySidePlan:
    registry_digest: str
    shard_ids: tuple[str, ...]
    paths: tuple[str, ...]
    batches: tuple[tuple[str, ...], ...]
    plan_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RegistryDifferentialPlan:
    accepted: bool
    impact_class: str
    required_suite_kind: str
    logical_scope_digest: str
    base: RegistrySidePlan | None
    candidate: RegistrySidePlan | None
    rejection_reasons: tuple[str, ...]


def plan_registry_differential(
    base_root: Path, candidate_root: Path, *, changed_paths: Sequence[str],
    requested_impact: str, max_shards_per_batch: int,
    max_total_shards: int, max_files: int,
) -> RegistryDifferentialPlan:
    """Verify both projections and derive bounded per-SHA shard plans."""
    if not (
        1 <= max_shards_per_batch <= 32
        and 1 <= max_total_shards <= 512
        and 1 <= max_files <= 4096
    ):
        return _reject(FAIL_BOUNDS)
    try:
        base_registry = _verified_registry(base_root)
        candidate_registry = _verified_registry(candidate_root)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return _reject(FAIL_PROJECTION)
    scope = _logical_scope(changed_paths, requested_impact)
    if scope is None:
        return _reject(FAIL_SCOPE)
    if _changed_quarantined(base_registry, candidate_registry, changed_paths):
        return _reject(FAIL_QUARANTINED_CHANGED_TEST)
    base = _side_plan(
        base_registry, scope, changed_paths, max_shards_per_batch
    )
    candidate = _side_plan(
        candidate_registry, scope, changed_paths, max_shards_per_batch
    )
    if base is None or candidate is None or not (base.shard_ids or candidate.shard_ids):
        return _reject(FAIL_SCOPE)
    if any(
        len(side.shard_ids) > max_total_shards or len(side.paths) > max_files
        for side in (base, candidate)
    ):
        return _reject(FAIL_BOUNDS)
    logical = _digest({
        "changed_paths": sorted(changed_paths), "impact_class": scope.effective_impact,
        "base": base.to_dict(), "candidate": candidate.to_dict(),
    })
    return RegistryDifferentialPlan(
        True, scope.effective_impact, scope.required_suite_kind,
        logical, base, candidate, (),
    )


def _verified_registry(root: Path) -> CanonicalTestRegistry:
    paths = tuple(sorted(
        path.relative_to(root).as_posix() for path in root.rglob("test_*.py")
        if path.is_file()
    ))
    if len(paths) > MAX_PROJECTED_TEST_FILES:
        raise ValueError("test_registry_file_count_exceeded")
    projected = canonical_bytes(build_registry(root, test_paths=paths))
    registry_path = root / REGISTRY_PATH
    if registry_path.stat().st_size > MAX_REGISTRY_BYTES:
        raise ValueError("test_registry_size_exceeded")
    checked = registry_path.read_bytes()
    if checked != projected:
        raise ValueError("test_registry_projection_mismatch")
    return load_canonical_test_registry(root)


def _logical_scope(changed: Sequence[str], impact: str):
    if not isinstance(changed, (list, tuple)) or not changed:
        return None
    operational = tuple(path for path in changed if path != REGISTRY_PATH)
    if not operational:
        return None
    owners = {owner_for_path(PurePosixPath(path)) for path in operational}
    if impact == "SYSTEMIC":
        selection = ["."]
    elif len(owners) == 1 and impact == "MODULAR":
        selection = [f"{next(iter(owners))}/tests"]
    elif impact == "ISOLATED" and len(operational) == 1:
        selection = [str(operational[0])]
    else:
        return None
    result = resolve_test_scope_coverage(operational, impact, selection)
    return result if result.accepted else None


def _side_plan(
    registry: CanonicalTestRegistry, scope: Any, changed: Sequence[str],
    batch_size: int,
) -> RegistrySidePlan | None:
    operational = tuple(path for path in changed if path != REGISTRY_PATH)
    shards = registry.automated_shards()
    if scope.effective_impact == "SYSTEMIC":
        selected = shards
    elif scope.effective_impact == "MODULAR":
        selected = tuple(shard for shard in shards if shard.owner == scope.module_root)
    else:
        selected = tuple(shard for shard in shards if operational[0] in shard.paths)
        target = PurePosixPath(operational[0])
        if not selected and not (
            target.name.startswith("test_") and target.suffix == ".py"
        ):
            owner = owner_for_path(PurePosixPath(operational[0]))
            selected = tuple(shard for shard in shards if shard.owner == owner)
    paths = tuple(path for shard in selected for path in shard.paths)
    if len(paths) != len(set(paths)):
        return None
    shard_ids = tuple(shard.shard_id for shard in selected)
    batches = tuple(
        shard_ids[index:index + batch_size]
        for index in range(0, len(shard_ids), batch_size)
    )
    payload = {
        "registry_digest": registry.registry_digest,
        "shards": [shard.to_dict() for shard in selected],
        "batches": batches,
    }
    return RegistrySidePlan(
        registry.registry_digest, shard_ids, paths, batches, _digest(payload),
    )


def _changed_quarantined(
    base: CanonicalTestRegistry, candidate: CanonicalTestRegistry,
    changed: Sequence[str],
) -> tuple[str, ...]:
    quarantined = {
        entry.path for entry in (*base.entries, *candidate.entries)
        if not entry.collectable
    }
    return tuple(
        path for path in changed
        if path in quarantined
    )


def _reject(reason: str) -> RegistryDifferentialPlan:
    return RegistryDifferentialPlan(False, "", "", "", None, None, (reason,))


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("ascii")).hexdigest()


__all__ = [
    "FAIL_BOUNDS", "FAIL_PROJECTION", "FAIL_QUARANTINED_CHANGED_TEST",
    "FAIL_SCOPE", "MAX_PROJECTED_TEST_FILES", "MAX_REGISTRY_BYTES",
    "RegistryDifferentialPlan",
    "RegistrySidePlan", "plan_registry_differential",
]
