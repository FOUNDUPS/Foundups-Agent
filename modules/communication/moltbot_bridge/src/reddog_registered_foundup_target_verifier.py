"""Current-checkout verifier for a registered FoundUp target receipt."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Optional, Sequence

from jsonschema import Draft202012Validator

RECEIPT_SCHEMA = "registered_foundup_target_receipt.v1"
REGISTRY_PATH = "modules/foundups/foundup_registry.json"
SCHEMA_PATH = "modules/foundups/foundup_registry.schema.json"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)

def _digest(value: Any) -> str:
    if isinstance(value, bytes):
        raw = value
    else:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"

def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}

def _path(root: Path, relative: Any) -> Optional[Path]:
    text = str(relative or "").replace("\\", "/")
    pure = PurePosixPath(text)
    if not text or pure.is_absolute() or ".." in pure.parts or ":" in text:
        return None
    target = (root / Path(*pure.parts)).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target if target.is_file() and not target.is_symlink() else None


def _receipt_integrity(receipt: Mapping[str, Any]) -> bool:
    payload = {key: value for key, value in receipt.items() if key != "receipt_id"}
    return (
        receipt.get("schema_version") == RECEIPT_SCHEMA
        and receipt.get("passed") is True
        and receipt.get("grants_authority") is False
        and receipt.get("receipt_id") == _digest(payload)
    )


def _git_head(root: Path) -> str:
    marker = root / ".git"
    if marker.is_dir():
        git_dir = marker.resolve()
    elif marker.is_file():
        line = marker.read_text(encoding="utf-8").strip()
        if not line.startswith("gitdir:"):
            return ""
        git_dir = (root / line.split(":", 1)[1].strip()).resolve()
    else:
        return ""
    head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    if _SHA_RE.fullmatch(head):
        return head.lower()
    if not head.startswith("ref: "):
        return ""
    reference = head[5:].strip()
    common_file = git_dir / "commondir"
    common = (git_dir / common_file.read_text(encoding="utf-8").strip()).resolve() if common_file.is_file() else git_dir
    for base in (git_dir, common):
        ref_file = base / Path(*PurePosixPath(reference).parts)
        if ref_file.is_file():
            value = ref_file.read_text(encoding="utf-8").strip()
            return value.lower() if _SHA_RE.fullmatch(value) else ""
    packed = common / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8").splitlines():
            if line.endswith(" " + reference) and _SHA_RE.fullmatch(line.split(" ", 1)[0]):
                return line.split(" ", 1)[0].lower()
    return ""


def _binding_reasons(
    receipt: Mapping[str, Any],
    selection: Mapping[str, Any],
    work_order: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    foundup_id = str(receipt.get("foundup_id") or "")
    receipt_id = str(receipt.get("receipt_id") or "")
    if selection and (
        str(selection.get("foundup_id") or "") != foundup_id
        or str(selection.get("registered_foundup_target_receipt_id") or "") != receipt_id
    ):
        reasons.append("registered_foundup_target_selection_mismatch")
    if work_order and (
        str(work_order.get("foundup_id") or "") != foundup_id
        or str(work_order.get("registered_foundup_target_receipt_id") or "") != receipt_id
        or _mapping(work_order.get("registered_foundup_target_receipt")) != receipt
    ):
        reasons.append("registered_foundup_target_work_order_mismatch")
    safe = [str(value) for value in receipt.get("safe_mutation_surfaces") or []]
    allowed = [str(value) for value in work_order.get("allowed_paths") or []]
    if work_order and (
        any(value not in safe for value in allowed)
        or work_order.get("safe_mutation_surface_digest") != _digest({"safe_mutation_surfaces": safe})
    ):
        reasons.append("registered_foundup_target_scope_mismatch")
    return reasons


def _load_authority(root: Path, target: Mapping[str, Any], reasons: list[str]) -> Mapping[str, Any]:
    registry_file, schema_file = _path(root, REGISTRY_PATH), _path(root, SCHEMA_PATH)
    if not registry_file or not schema_file:
        reasons.append("registered_foundup_target_authority_missing")
        return {}
    try:
        registry_bytes, schema_bytes = registry_file.read_bytes(), schema_file.read_bytes()
        registry, schema = json.loads(registry_bytes), json.loads(schema_bytes)
        Draft202012Validator(schema).validate(registry)
    except Exception:
        reasons.append("registered_foundup_target_schema_invalid")
        return {}
    if target.get("registry_digest") != _digest(registry_bytes) or target.get("registry_schema_digest") != _digest(schema_bytes):
        reasons.append("registered_foundup_target_registry_changed")
    entities = [item for item in registry.get("entities", []) if item.get("foundup_id") == target.get("foundup_id")]
    if len(entities) != 1 or target.get("registry_entity_digest") != _digest(entities[0] if entities else {}):
        reasons.append("registered_foundup_target_entity_changed")
    return registry


def _verify_evidence(root: Path, target: Mapping[str, Any], reasons: list[str]) -> None:
    evidence = target.get("evidence_digests")
    if not isinstance(evidence, Sequence) or isinstance(evidence, (str, bytes)):
        reasons.append("registered_foundup_target_evidence_invalid")
        evidence = []
    paths = {str(_mapping(record).get("path") or "") for record in evidence}
    required = {REGISTRY_PATH, SCHEMA_PATH}
    if target.get("manifest_path"):
        required.add(str(target["manifest_path"]))
    if not required.issubset(paths):
        reasons.append("registered_foundup_target_evidence_incomplete")
    for record in evidence:
        item = _mapping(record)
        evidence_file = _path(root, item.get("path"))
        if not evidence_file or item.get("content_digest") != _digest(evidence_file.read_bytes()):
            reasons.append("registered_foundup_target_evidence_changed")
            return


def _verify_manifest(root: Path, target: Mapping[str, Any], reasons: list[str]) -> None:
    if not target.get("manifest_path"):
        return
    manifest_file = _path(root, target["manifest_path"])
    try:
        manifest = json.loads(manifest_file.read_bytes()) if manifest_file else {}
        safe = manifest.get("build_contract", {}).get("safe_mutation_surface", [])
    except Exception:
        manifest, safe = {}, []
    if manifest.get("foundup_id") != target.get("foundup_id") or safe != target.get("safe_mutation_surfaces"):
        reasons.append("registered_foundup_target_manifest_changed")


def verify_registered_foundup_target(
    repo_root: Path,
    receipt: Optional[Mapping[str, Any]],
    *,
    selection_receipt: Optional[Mapping[str, Any]] = None,
    work_order: Optional[Mapping[str, Any]] = None,
) -> tuple[str, ...]:
    """Return stable rejection reasons; an empty tuple means current-checkout PASS."""

    root = Path(repo_root).resolve()
    selection = _mapping(selection_receipt)
    order = _mapping(work_order)
    target = _mapping(receipt)
    binding_claimed = any(
        str(value or "")
        for value in (
            selection.get("foundup_id"), selection.get("registered_foundup_target_receipt_id"),
            order.get("foundup_id"), order.get("registered_foundup_target_receipt_id"),
        )
    )
    if not target:
        return ("registered_foundup_target_receipt_missing",) if binding_claimed else ()
    if not _receipt_integrity(target):
        return ("registered_foundup_target_receipt_invalid",)
    reasons = _binding_reasons(target, selection, order)
    registry = _load_authority(root, target, reasons)
    if not registry:
        return tuple(dict.fromkeys(reasons))
    if target.get("repo_head_sha") != _git_head(root):
        reasons.append("registered_foundup_target_repo_head_mismatch")
    _verify_evidence(root, target, reasons)
    _verify_manifest(root, target, reasons)
    if target.get("repo_root_digest") != _digest(str(root)):
        reasons.append("registered_foundup_target_repo_root_mismatch")
    return tuple(dict.fromkeys(reasons))
__all__ = ["verify_registered_foundup_target"]
