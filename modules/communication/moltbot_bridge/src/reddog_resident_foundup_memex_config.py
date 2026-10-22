"""Build exact-source FoundUp Memex supply inputs for resident cycles.

The config is derived only from the canonical FoundUp registry, manifest and
module roadmap. It supplies read-only identity/roadmap metadata to the existing
operational Memex owner; it is not a new memory store or promotion authority.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_operational_memex_snapshot_supplier import (
    OperationalMemexSnapshotSupplyConfig,
)
from modules.communication.moltbot_bridge.src.reddog_resident_memory_context import (
    bounded_json_file,
)

REGISTRY_PATH = Path("modules/foundups/foundup_registry.json")


def build_resident_foundup_memex_supply_config(
    *,
    repo_root: Path | str,
    foundup_id: str,
    principal_id: str,
    max_records: int = 32,
) -> OperationalMemexSnapshotSupplyConfig:
    root = Path(repo_root).resolve()
    foundup = str(foundup_id or "").strip()
    principal = str(principal_id or "").strip()
    if not foundup or not principal:
        raise ValueError("resident_memex_scope_missing")

    registry = bounded_json_file(root / REGISTRY_PATH)
    if not isinstance(registry, Mapping):
        raise ValueError("resident_memex_registry_unavailable")
    entities = registry.get("entities")
    if not isinstance(entities, list):
        raise ValueError("resident_memex_registry_invalid")
    matches = [
        item
        for item in entities
        if isinstance(item, Mapping)
        and str(item.get("foundup_id") or "").strip() == foundup
    ]
    if len(matches) != 1:
        raise ValueError("resident_memex_foundup_not_unique")
    entry = matches[0]

    module_path = _confined_path(
        root, str(entry.get("module_path") or ""), "resident_memex_module_path"
    )
    manifest_relative = str(entry.get("manifest_path") or "").strip()
    manifest_path = _confined_path(
        root,
        manifest_relative or str(Path(str(entry.get("module_path") or "")) / "foundup_manifest.json"),
        "resident_memex_manifest_path",
    )
    manifest = bounded_json_file(manifest_path)
    if (
        not isinstance(manifest, Mapping)
        or str(manifest.get("foundup_id") or "").strip() != foundup
    ):
        raise ValueError("resident_memex_manifest_scope_mismatch")

    roadmap_path = module_path / "ROADMAP.md"
    roadmap_bytes = _bounded_bytes(roadmap_path, max_bytes=524_288)
    roadmap_digest = "sha256:" + hashlib.sha256(roadmap_bytes).hexdigest()
    name = str(manifest.get("name") or entry.get("display_name") or "").strip()
    if not name:
        raise ValueError("resident_memex_identity_name_missing")

    identity = {
        "foundup_id": foundup,
        "name": name,
        "stage": str(
            manifest.get("lifecycle_stage") or entry.get("stage") or ""
        ).strip(),
        "purpose": str(manifest.get("description") or "").strip(),
        "outcome": "",
        "solution": str(manifest.get("tagline") or "").strip(),
        "pain": "",
    }
    roadmap_state = {
        "foundup_id": foundup,
        "roadmap_id": roadmap_path.relative_to(root).as_posix(),
        "version": roadmap_digest,
        "content_digest": roadmap_digest,
        "active_item_ids": (),
        "blocked_item_ids": (),
    }
    return OperationalMemexSnapshotSupplyConfig(
        foundup_id=foundup,
        principal_id=principal,
        identity=identity,
        roadmap_state=roadmap_state,
        max_records=_positive_int(max_records, default=32),
    )


def _confined_path(root: Path, value: str, reason: str) -> Path:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError(reason + "_missing")
    candidate = root / Path(raw)
    if candidate.is_symlink():
        raise ValueError(reason + "_link")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(reason + "_escape") from exc
    if not resolved.exists():
        raise ValueError(reason + "_missing")
    return resolved


def _bounded_bytes(path: Path, *, max_bytes: int) -> bytes:
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError("resident_memex_roadmap_unavailable")
        size = path.stat().st_size
        if size <= 0 or size > max_bytes:
            raise ValueError("resident_memex_roadmap_size_invalid")
        return path.read_bytes()
    except OSError as exc:
        raise ValueError("resident_memex_roadmap_unavailable") from exc


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


__all__ = ["build_resident_foundup_memex_supply_config"]
