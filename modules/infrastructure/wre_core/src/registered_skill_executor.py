"""Registry-bound programmatic Skillz executor resolution and dispatch."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.infrastructure.wre_core.src.skill_path_security import (
    absolute_unresolved,
    has_link_or_reparse_component as _has_link_or_reparse_component,
    path_has_link_or_reparse,
)

logger = logging.getLogger(__name__)

_BUNDLE_FILES = ("SKILLz.md", "SKILL.md", "executor.py", "SKILL_MANIFEST.json")


def validate_runtime_skill_admission(
    *,
    skills_loader: Any,
    skill_name: str,
) -> tuple[bool, str]:
    """Require matching production registry and Skillz frontmatter state."""
    skill_info = skills_loader.registry.get("skills", {}).get(skill_name)
    if not isinstance(skill_info, dict):
        return False, "skill is not registered"
    if skill_info.get("promotion_state") != "production":
        return False, "skill is not admitted for production execution"
    try:
        metadata = skills_loader.get_skill_metadata(skill_name)
    except Exception:
        return False, "registered skill metadata is unavailable"
    if not isinstance(metadata, Mapping):
        return False, "registered skill metadata is malformed"
    expected = {
        "name": skill_name,
        "version": str(skill_info.get("version", "")),
        "intent_type": str(skill_info.get("intent_type", "")),
        "promotion_state": "production",
    }
    actual = {
        "name": str(metadata.get("name", "")),
        "version": str(metadata.get("version", "")),
        "intent_type": str(metadata.get("intent_type", "")),
        "promotion_state": str(metadata.get("promotion_state", "")),
    }
    if actual != expected:
        return False, "registry and Skillz production metadata do not match"
    return True, "production Skillz metadata admitted"


def resolve_registered_skill_executor(
    *,
    repo_root: Path,
    skill_file: Optional[Path],
) -> Optional[Path]:
    """Resolve only a regular, non-link executor beside the admitted skill."""
    if skill_file is None:
        return None
    root = repo_root.resolve()
    raw_skill = Path(skill_file)
    raw_executor = raw_skill.parent / "executor.py"
    if _has_link_or_reparse_component(root, raw_skill):
        return None
    if _has_link_or_reparse_component(root, raw_executor):
        return None
    skill_dir = raw_skill.parent.resolve()
    executor = raw_executor.resolve()
    try:
        skill_dir.relative_to(root)
        executor.relative_to(skill_dir)
        executor.relative_to(root)
    except ValueError:
        return None
    if not executor.is_file():
        return None
    return executor


def dispatch_registered_skill_executor(
    *,
    executor_path: Path,
    skill_name: str,
    input_context: Mapping[str, Any],
    agent: str,
    admission_fingerprint: Optional[str] = None,
) -> dict[str, Any]:
    """Execute only executor bytes bound to the scanner admission fingerprint."""
    try:
        source = _read_manifest_bound_executor(
            executor_path, admission_fingerprint=admission_fingerprint
        )
        namespace: dict[str, Any] = {
            "__file__": str(executor_path),
            "__name__": f"wre_executor_{skill_name}",
            "__package__": None,
        }
        exec(compile(source, str(executor_path), "exec"), namespace)
        execute_fn = namespace.get("execute")
        if not callable(execute_fn):
            return _error("missing_execute", "registered skill executor has no execute() function")
        task = dict(input_context)
        task.setdefault("skill_name", skill_name)
        task.setdefault("agent", agent)
        result = execute_fn(task)
        if not isinstance(result, dict):
            return _error("invalid_executor_result", "registered skill executor returned a non-object result")
        if type(result.get("success")) is not bool:
            return _error("invalid_executor_result", "executor success must be a boolean")
        if result["success"] is not True:
            return _error("executor_reported_failure", "registered skill executor reported failure")
        if not _valid_effect_receipts(result.get("effect_receipts")):
            return _error("missing_effect_receipt", "executor success requires typed effect receipts")
        normalized = dict(result)
        normalized["_executor_dispatch"] = True
        normalized["_effect_evidence"] = True
        return normalized
    except Exception as exc:
        logger.error(
            "[WRE-EXECUTOR] Executor failed for %s; error_type=%s",
            skill_name,
            type(exc).__name__,
        )
        return _error("executor_exception", "registered skill executor failed")


def skill_bundle_fingerprint(skill_dir: Path) -> str:
    """Hash one unresolved, regular-file Skillz bundle in canonical order."""
    return _fingerprint_snapshot(_capture_skill_bundle(skill_dir))


def _capture_skill_bundle(skill_dir: Path) -> dict[str, bytes]:
    raw_dir = absolute_unresolved(skill_dir)
    if path_has_link_or_reparse(raw_dir):
        raise ValueError("Skillz bundle root crosses a link or reparse point")
    snapshot: dict[str, bytes] = {}
    for name in _BUNDLE_FILES:
        path = raw_dir / name
        if _has_link_or_reparse_component(raw_dir, path):
            raise ValueError("Skillz bundle crosses a link or reparse point")
        if path.is_file():
            snapshot[name] = path.read_bytes()
    if not snapshot:
        raise FileNotFoundError("no Skillz bundle files")
    return snapshot


def _fingerprint_snapshot(snapshot: Mapping[str, bytes]) -> str:
    digest = hashlib.sha256()
    digest.update(b"WRE_SKILL_BUNDLE_V1\x00")
    for name in _BUNDLE_FILES:
        encoded_name = name.encode("utf-8")
        digest.update(len(encoded_name).to_bytes(4, "big"))
        digest.update(encoded_name)
        content = snapshot.get(name)
        if content is None:
            digest.update(b"\x00")
            continue
        digest.update(b"\x01")
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _read_manifest_bound_executor(
    executor_path: Path, *, admission_fingerprint: Optional[str]
) -> bytes:
    """Read captured executor bytes only from the exact admitted bundle."""
    if not isinstance(admission_fingerprint, str) or len(admission_fingerprint) != 64:
        raise ValueError("executor admission fingerprint is missing")
    path = absolute_unresolved(executor_path)
    snapshot = _capture_skill_bundle(path.parent)
    observed = _fingerprint_snapshot(snapshot)
    if not hmac.compare_digest(observed, admission_fingerprint.lower()):
        raise ValueError("executor bundle differs from scanner admission")
    manifest_bytes = snapshot.get("SKILL_MANIFEST.json")
    source = snapshot.get("executor.py")
    if manifest_bytes is None or source is None:
        raise ValueError("executor or manifest is unavailable")
    payload = json.loads(manifest_bytes.decode("utf-8"))
    entries = payload.get("files")
    if not isinstance(entries, list):
        raise ValueError("executor manifest is malformed")
    expected = next(
        (
            entry.get("sha256")
            for entry in entries
            if isinstance(entry, dict) and entry.get("path") == "executor.py"
        ),
        None,
    )
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("executor is not manifest-bound")
    if hashlib.sha256(source).hexdigest() != expected.lower():
        raise ValueError("executor digest does not match manifest")
    return source


def _valid_effect_receipts(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for receipt in value:
        if not isinstance(receipt, dict):
            return False
        if not isinstance(receipt.get("receipt_id"), str) or not receipt["receipt_id"].strip():
            return False
        if not isinstance(receipt.get("effect_type"), str) or not receipt["effect_type"].strip():
            return False
    return True


def _error(error_code: str, message: str) -> dict[str, Any]:
    return {
        "success": False,
        "output": "",
        "error": message,
        "error_code": error_code,
        "_executor_dispatch": True,
        "_executor_error": True,
        "_effect_evidence": False,
    }
