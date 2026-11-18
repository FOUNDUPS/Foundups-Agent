"""Current-checkout verifier for a registered FoundUp target receipt."""

from __future__ import annotations

import hashlib
import json
import re
import stat
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Optional, Sequence

from jsonschema import Draft202012Validator

RECEIPT_SCHEMA = "registered_foundup_target_receipt.v1"
REGISTRY_PATH = "modules/foundups/foundup_registry.json"
SCHEMA_PATH = "modules/foundups/foundup_registry.schema.json"
BRAND_SCHEMA_PATH = "modules/foundups/brand_context.schema.json"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)

def _digest(value: Any) -> str:
    if isinstance(value, bytes):
        raw = value
    else:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"

def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}

def _path(root: Path, relative: Any) -> Optional[Path]:
    text = str(relative or "").replace("\\", "/")
    pure = PurePosixPath(text)
    if not text or pure.is_absolute() or ".." in pure.parts or ":" in text:
        return None
    source_path = pure.suffix.lower() in {
        ".c", ".cc", ".cpp", ".cs", ".go", ".h", ".hpp", ".java", ".js", ".jsx",
        ".md", ".mjs", ".py", ".rs", ".rst", ".ts", ".tsx",
    }
    if any(_private_component(part, source_path) for part in pure.parts):
        return None
    target = root
    try:
        for part in pure.parts:
            target = target / part
            if target.is_symlink() or getattr(target.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                return None
        resolved = target.resolve()
        resolved.relative_to(root)
        return resolved if resolved.is_file() and resolved.stat().st_nlink == 1 else None
    except (OSError, ValueError):
        return None


def _private_component(part: str, source_path: bool) -> bool:
    # Same public-read exclusions as target_read_path_policy.js, without config I/O.
    value = part.lower().rstrip(" .")
    if value != part.lower() or value in {".git", ".ssh", ".gnupg", ".aws", ".azure", ".gcloud", "node_modules", "__pycache__", ".venv"}:
        return True
    blocked = (".env", ".netrc", ".npmrc", ".pypirc", ".git-credentials", ".dockerconfigjson")
    if any(value == name or value.startswith(name + ".") for name in blocked):
        return True
    if re.search(r"(?:^|[._-])(?:secrets?|credentials?|api[_-]?keys?|private[_-]?keys?|signing[_-]?keys?|service[_-]?accounts?)(?=[._-]|$)|^tokens?(?:[._-](?:data|store|cache|secret|vault))?$", value):
        return True
    if not source_path and (any(marker in value for marker in ("secret", "credential", "token"))
                            or re.search(r"(?:^|[._-])auth(?=[._-]|$)", value)):
        return True
    return bool(re.search(r"(?:^|\.)(?:pem|key|p12|pfx|jks|keystore|vsix)(?:\.|$)", value)
                or re.match(r"^id_(?:rsa|dsa|ecdsa|ed25519)(?:\.pub)?(?:[._-]|$)", value)
                or re.match(r"^(?:con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\.|$)", value))



def _receipt_integrity(receipt: Mapping[str, Any]) -> bool:
    payload = {key: value for key, value in receipt.items() if key != "receipt_id"}
    try:
        payload_digest = _digest(payload)
    except UnicodeError:
        return False
    return (
        receipt.get("schema_version") == RECEIPT_SCHEMA
        and receipt.get("passed") is True
        and receipt.get("grants_authority") is False
        and receipt.get("receipt_id") == payload_digest
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
    if target.get("brand_context_path"):
        required.update({str(target["brand_context_path"]), BRAND_SCHEMA_PATH})
    if not required.issubset(paths):
        reasons.append("registered_foundup_target_evidence_incomplete")
    for record in evidence:
        item = _mapping(record)
        evidence_file = _path(root, item.get("path"))
        if not evidence_file or item.get("content_digest") != _digest(evidence_file.read_bytes()):
            reasons.append("registered_foundup_target_evidence_changed")
            return


def _verify_brand_context(
    root: Path,
    target: Mapping[str, Any],
    registry: Mapping[str, Any],
    reasons: list[str],
) -> None:
    entities = [item for item in registry.get("entities", []) if item.get("foundup_id") == target.get("foundup_id")]
    entity = entities[0] if len(entities) == 1 else {}
    declared = entity.get("brand_context_path")
    receipt_path = target.get("brand_context_path")
    if declared is not None and (not isinstance(declared, str) or not declared):
        reasons.append("registered_foundup_target_brand_context_invalid")
        return
    if declared != receipt_path:
        reasons.append("registered_foundup_target_brand_path_mismatch")
        return
    if not declared:
        expected = {"brand_foundup_id": entity.get("foundup_id"), "canonical_brand": entity.get("display_name")}
        if any(key in target and target[key] != value for key, value in expected.items()):
            reasons.append("registered_foundup_target_brand_selection_mismatch")
        return
    context_file, schema_file = _path(root, declared), _path(root, BRAND_SCHEMA_PATH)
    try:
        if not context_file or not schema_file:
            raise ValueError("brand_context_missing")
        context = json.loads(context_file.read_bytes())
        schema = json.loads(schema_file.read_bytes())
        Draft202012Validator(schema).validate(context)
    except Exception:
        reasons.append("registered_foundup_target_brand_context_invalid")
        return
    if context.get("foundup_id") != target.get("foundup_id"):
        reasons.append("registered_foundup_target_brand_identity_mismatch")
        return
    brand_id = str(target.get("brand_foundup_id") or "")
    canonical = str(target.get("canonical_brand") or "")
    try:
        expected, aliases = _brand_identities(context, entity)
    except ValueError:
        reasons.append("registered_foundup_target_brand_identity_ambiguous")
        return
    if (brand_id not in expected or expected.get(brand_id) != canonical
            or aliases.get(target.get("matched_reference")) != brand_id):
        reasons.append("registered_foundup_target_brand_selection_mismatch")


def _brand_identities(context: Mapping[str, Any], entity: Mapping[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    identities, aliases = {}, {}
    for brand in [context, *context.get("child_foundups", [])]:
        identity = brand["foundup_id"]
        if identity in identities:
            raise ValueError("duplicate_brand_identity")
        identities[identity] = brand["canonical_brand"]
        values = [identity, brand["canonical_brand"], *brand.get("aliases", [])]
        if identity == entity["foundup_id"]:
            values += [entity.get("display_name"), entity.get("token_symbol"), PurePosixPath(entity.get("module_path") or "").name]
        for value in values:
            if not value:
                continue
            alias = unicodedata.normalize("NFKC", value).lower()
            alias = re.sub(r"[_-]+", " ", alias)
            alias = re.sub(r"[^a-z0-9\u3040-\u30ff\u3400-\u9fff.]+", " ", alias)
            alias = " ".join(alias.split())
            if not alias or (alias in aliases and aliases[alias] != identity):
                raise ValueError("ambiguous_brand_alias")
            aliases[alias] = identity
    return identities, aliases


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
    _verify_brand_context(root, target, registry, reasons)
    _verify_manifest(root, target, reasons)
    if target.get("repo_root_digest") != _digest(str(root)):
        reasons.append("registered_foundup_target_repo_root_mismatch")
    return tuple(dict.fromkeys(reasons))
__all__ = ["verify_registered_foundup_target"]
