"""Load the exact manifest-bound signer config selected for this generation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_bootstrap import (
    rehydrate_signer_socket_service_runtime_config,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    constant_time_compare,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_text,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


def load_current_generation_signer_config_payload(
    *, repo_root: Path, selection: Mapping[str, Any]
) -> tuple[dict[str, Any], Any]:
    """Rehydrate the selected config only after path and digest verification."""

    runtime = validate_runtime_root_path(selection["runtime_root"], repo_root=repo_root)
    path = validate_runtime_artifact_path(
        selection["config_path"], repo_root=repo_root, allowed_root=runtime
    )
    if path.parent != runtime:
        raise ValueError("e0_selected_config_path_invalid")
    text = secure_read_confined_text(path, allowed_root=runtime, max_bytes=256 * 1024)
    payload = json.loads(text, parse_constant=_reject_constant)
    if not isinstance(payload, dict):
        raise ValueError("e0_selected_config_invalid")
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    digest = "sha256:" + hashlib.sha256(canonical.encode("ascii")).hexdigest()
    if not constant_time_compare(digest, str(selection["config_digest"])):
        raise ValueError("e0_selected_config_digest_mismatch")
    config = rehydrate_signer_socket_service_runtime_config(
        repo_root, runtime, payload, expected_config_digest=digest
    )
    if config is None:
        raise ValueError("e0_selected_config_invalid")
    return payload, config


def load_current_generation_signer_config(
    *, repo_root: Path, selection: Mapping[str, Any]
) -> Any:
    """Return the verified config without policy-specific authorization claims."""

    return load_current_generation_signer_config_payload(
        repo_root=repo_root, selection=selection
    )[1]


def _reject_constant(_value: str) -> None:
    raise ValueError("e0_selected_config_invalid")


__all__ = [
    "load_current_generation_signer_config",
    "load_current_generation_signer_config_payload",
]
