"""Canonical WRE test-registry loading, validation, and shard planning."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from .wre_test_registry_classification import (
    SUITE_CLASSES, owner_for_path, shard_slug,
)

SCHEMA_VERSION = "wsp_test_registry.v2"
GENERATION_POLICY = "git-tracked-python-tests.v1"
REGISTRY_PATH = "WSP_knowledge/WSP_Test_Registry.json"
MAX_FILES_PER_SHARD = 32
_ENTRY_KEYS = {
    "id", "path", "owner", "suite_class", "shard_id", "capabilities",
    "execution_type", "collectable", "timeout_s", "quarantine_reasons",
    "description",
}

@dataclass(frozen=True)
class TestRegistryEntry:
    id: str
    path: str
    owner: str
    suite_class: str
    shard_id: str
    capabilities: tuple[str, ...]
    execution_type: str
    collectable: bool
    timeout_s: int
    quarantine_reasons: tuple[str, ...]
    description: str
@dataclass(frozen=True)
class TestShard:
    shard_id: str
    owner: str
    suite_class: str
    paths: tuple[str, ...]
    timeout_s: int
    registry_digest: str
    plan_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
@dataclass(frozen=True)
class CanonicalTestRegistry:
    entries: tuple[TestRegistryEntry, ...]
    registry_digest: str
    quarantined_count: int

    def automated_shards(self) -> tuple[TestShard, ...]:
        grouped: dict[tuple[str, str, str], list[TestRegistryEntry]] = {}
        for entry in self.entries:
            if entry.collectable:
                grouped.setdefault(
                    (entry.shard_id, entry.owner, entry.suite_class), []
                ).append(entry)
        shards = []
        for (shard_id, owner, suite_class), entries in sorted(grouped.items()):
            ordered = sorted(entries, key=lambda item: item.path)
            paths = tuple(item.path for item in ordered)
            payload = {
                "registry_digest": self.registry_digest, "shard_id": shard_id,
                "owner": owner, "suite_class": suite_class, "paths": paths,
                "timeout_s": max(item.timeout_s for item in ordered),
            }
            shards.append(TestShard(
                shard_id=shard_id, owner=owner, suite_class=suite_class,
                paths=paths, timeout_s=payload["timeout_s"],
                registry_digest=self.registry_digest, plan_digest=_digest(payload),
            ))
        return tuple(shards)
def load_canonical_test_registry(repo_root: Path | str) -> CanonicalTestRegistry:
    """Load the exact schema and reject malformed, missing, or unsafe rows."""
    root = Path(repo_root).resolve(strict=True)
    path = root / REGISTRY_PATH
    raw = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(raw, Mapping):
        raise ValueError("test_registry_not_mapping")
    required = {
        "schema_version", "generation_policy", "total_tests",
        "quarantined_tests", "tests",
    }
    if set(raw) != required:
        raise ValueError("test_registry_fields_invalid")
    if raw["schema_version"] != SCHEMA_VERSION:
        raise ValueError("test_registry_schema_invalid")
    if raw["generation_policy"] != GENERATION_POLICY:
        raise ValueError("test_registry_generation_policy_invalid")
    rows = raw["tests"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("test_registry_rows_invalid")
    entries = tuple(_entry(root, row) for row in rows)
    paths = [entry.path for entry in entries]
    ids = [entry.id for entry in entries]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ValueError("test_registry_paths_not_canonical")
    if len(ids) != len(set(ids)):
        raise ValueError("test_registry_ids_not_unique")
    quarantined = sum(not entry.collectable for entry in entries)
    if raw["total_tests"] != len(entries) or raw["quarantined_tests"] != quarantined:
        raise ValueError("test_registry_counts_invalid")
    _validate_derived_entries(entries)
    return CanonicalTestRegistry(entries, _digest(raw), quarantined)
def registry_payload(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted((dict(entry) for entry in entries), key=lambda item: item["path"])
    return {
        "schema_version": SCHEMA_VERSION,
        "generation_policy": GENERATION_POLICY,
        "total_tests": len(ordered),
        "quarantined_tests": sum(not item["collectable"] for item in ordered),
        "tests": ordered,
    }
def _entry(root: Path, raw: Any) -> TestRegistryEntry:
    if not isinstance(raw, Mapping) or set(raw) != _ENTRY_KEYS:
        raise ValueError("test_registry_entry_fields_invalid")
    path = _confined_path(raw.get("path"))
    target = root / PurePosixPath(path)
    suite_class = raw.get("suite_class")
    sequences = (raw.get("capabilities"), raw.get("quarantine_reasons"))
    valid = (
        path and target.is_file() and target.name.startswith("test_")
        and target.suffix == ".py" and suite_class in SUITE_CLASSES
        and all(_string_list(value) for value in sequences)
        and type(raw.get("collectable")) is bool
        and type(raw.get("timeout_s")) is int
        and 1 <= raw.get("timeout_s", 0) <= 3600
        and all(isinstance(raw.get(name), str) and raw[name] for name in (
            "id", "owner", "shard_id", "execution_type"
        ))
        and isinstance(raw.get("description"), str)
        and len(raw.get("description", "")) <= 500
    )
    if not valid:
        raise ValueError(f"test_registry_entry_invalid:{path or 'unknown'}")
    if raw["collectable"] != (suite_class in {"unit", "integration"} and not raw["quarantine_reasons"]):
        raise ValueError(f"test_registry_collectable_invalid:{path}")
    return TestRegistryEntry(
        id=raw["id"], path=path, owner=raw["owner"],
        suite_class=suite_class, shard_id=raw["shard_id"],
        capabilities=tuple(raw["capabilities"]),
        execution_type=raw["execution_type"], collectable=raw["collectable"],
        timeout_s=raw["timeout_s"],
        quarantine_reasons=tuple(raw["quarantine_reasons"]),
        description=raw["description"],
    )
def _validate_derived_entries(entries: Sequence[TestRegistryEntry]) -> None:
    groups: dict[tuple[str, str], list[TestRegistryEntry]] = {}
    for entry in entries:
        path = PurePosixPath(entry.path)
        expected_id = "test::" + entry.path.removesuffix(".py").replace("/", "::")
        if entry.id != expected_id or entry.owner != owner_for_path(path):
            raise ValueError(f"test_registry_derived_identity_invalid:{entry.path}")
        if entry.execution_type != entry.suite_class:
            raise ValueError(f"test_registry_execution_type_invalid:{entry.path}")
        groups.setdefault((entry.owner, entry.suite_class), []).append(entry)
    for (owner, suite_class), rows in groups.items():
        ordered = sorted(rows, key=lambda item: item.path)
        collectable = [item for item in ordered if item.collectable]
        count = (len(collectable) + MAX_FILES_PER_SHARD - 1) // MAX_FILES_PER_SHARD
        base = shard_slug(owner, suite_class)
        for index, entry in enumerate(collectable):
            part = index // MAX_FILES_PER_SHARD + 1
            expected = base if count == 1 else f"{base}-part-{part:02d}"
            if entry.shard_id != expected:
                raise ValueError(f"test_registry_shard_invalid:{entry.path}")
def _confined_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        return ""
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".."} for part in path.parts):
        return ""
    return path.as_posix()
def _string_list(value: Any) -> bool:
    return isinstance(value, list) and value == sorted(set(value)) and all(
        isinstance(item, str) and item for item in value
    )
def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


__all__ = [
    "CanonicalTestRegistry", "GENERATION_POLICY", "MAX_FILES_PER_SHARD",
    "REGISTRY_PATH", "SCHEMA_VERSION", "TestRegistryEntry", "TestShard",
    "load_canonical_test_registry", "registry_payload",
]
