"""Read-only startup adapter for runtime compatibility evidence."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)

from .runtime_compatibility_receipt import (
    RuntimeCompatibilityReceipt,
    build_not_ready_receipt,
    build_runtime_compatibility_receipt,
)


MAX_EVIDENCE_BYTES = 256 * 1024


def run_runtime_compatibility_advisory(
    repo_root: Path | str,
    *,
    environment: Mapping[str, str] | None = None,
) -> RuntimeCompatibilityReceipt:
    """Load cached evidence, emit one advisory line, and never block startup."""
    env = environment if environment is not None else os.environ
    try:
        evidence = _load_evidence(repo_root, env)
        receipt = build_runtime_compatibility_receipt(evidence)
    except Exception as exc:
        receipt = build_not_ready_receipt((_safe_reason(exc),))
    reasons = ",".join(receipt.reasons) if receipt.reasons else "none"
    print(
        f"[RUNTIME-COMPAT] preflight={receipt.overall_state} "
        f"receipt={receipt.receipt_id} reasons={reasons}"
    )
    return receipt


def _load_evidence(repo_root: Path | str, env: Mapping[str, str]) -> dict[str, object]:
    root_value = str(env.get("REDDOG_RUNTIME_COMPATIBILITY_ROOT", "")).strip()
    path_value = str(env.get("REDDOG_RUNTIME_COMPATIBILITY_EVIDENCE", "")).strip()
    if not root_value:
        raise ValueError("runtime_compatibility_root_missing")
    if not path_value:
        raise ValueError("runtime_compatibility_evidence_missing")
    root = validate_runtime_root_path(root_value, repo_root=repo_root)
    path = validate_runtime_artifact_path(path_value, repo_root=repo_root, allowed_root=root)
    if not path.is_file() or path.is_symlink():
        raise ValueError("runtime_compatibility_evidence_unavailable")
    if path.stat().st_size > MAX_EVIDENCE_BYTES:
        raise ValueError("runtime_compatibility_evidence_too_large")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("runtime_compatibility_evidence_not_mapping")
    return payload


def _safe_reason(exc: Exception) -> str:
    text = str(exc).strip().lower().replace(" ", "_")
    allowed = "".join(char for char in text if char.isalnum() or char == "_")
    if allowed.startswith("runtime_") and len(allowed) <= 120:
        return allowed
    return f"runtime_compatibility_error:{type(exc).__name__}"


__all__ = ["MAX_EVIDENCE_BYTES", "run_runtime_compatibility_advisory"]
