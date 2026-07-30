"""Signer socket service run-packet supplier for resident RedDog runtime.

Slice: REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY_PHASE1

This module materializes an outside-repo run packet for a signer-owned service
manager to start the signer socket CLI. It validates the signer service config
and emits a shell-free argv list. It does not start the signer, resolve
secrets, bind sockets, parse environment variables, mutate the repository,
enqueue OpenClaw, dispatch Hermes, publish PRs, settle rewards, or re-index
HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_WSP71_PERMISSIONED,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
    SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_bootstrap import (
    rehydrate_signer_socket_service_runtime_config,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_schema import (
    SIGNER_SERVICE_RUN_PACKET_SCHEMA_VERSION,
)
from modules.infrastructure.shared_utilities.reddog_runtime_artifact_generation import (
    reddog_runtime_artifact_generation_lock,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
    secure_read_confined_text,
    validate_runtime_root_path,
)

SIGNER_SERVICE_RUN_PACKET_SUPPLY_ACCEPT = "SIGNER_SERVICE_RUN_PACKET_SUPPLY_ACCEPT"
SIGNER_SERVICE_RUN_PACKET_SUPPLY_REJECT = "SIGNER_SERVICE_RUN_PACKET_SUPPLY_REJECT"

FAIL_SIGNER_RUN_PACKET_CONFIG_PATH_INVALID = "signer_run_packet_config_path_invalid"
FAIL_SIGNER_RUN_PACKET_CONFIG_MALFORMED = "signer_run_packet_config_malformed"
FAIL_SIGNER_RUN_PACKET_OUTPUT_PATH_INVALID = "signer_run_packet_output_path_invalid"
FAIL_SIGNER_RUN_PACKET_OP_EXECUTABLE_INVALID = "signer_run_packet_op_executable_invalid"
FAIL_SIGNER_RUN_PACKET_LIMITS_INVALID = "signer_run_packet_limits_invalid"
FAIL_SIGNER_RUN_PACKET_SESSION_INVALID = "signer_run_packet_session_invalid"
FAIL_SIGNER_RUN_PACKET_WRITE_FAILED = "signer_run_packet_write_failed"
FAIL_SIGNER_RUN_PACKET_PROPOSAL_RUNTIME_ADAPTERS_UNAVAILABLE = (
    "signer_run_packet_proposal_runtime_adapters_unavailable"
)

_CLI_MODULE = (
    "modules.communication.moltbot_bridge.src."
    "reddog_signer_socket_service_runtime_cli"
)


@dataclass(frozen=True)
class SignerServiceRunPacketSupplyResult:
    """Audit-safe result for signer service run-packet materialization."""

    accepted: bool
    status: str
    run_packet_id: str | None
    run_packet_path: str | None
    run_packet_digest: str | None
    config_path: str | None
    config_digest: str | None
    socket_path: str | None
    profile_count: int
    rejection_reasons: tuple[str, ...]
    no_secret_values_written: bool = True
    no_secret_values_resolved: bool = True
    no_signer_started: bool = True
    no_socket_bound: bool = True
    no_process_spawned: bool = True
    no_shell_command_emitted: bool = True
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_signer_socket_service_run_packet_supply(
    *,
    repo_root: Path | str,
    config_path: Path | str | None,
    output_path: Path | str | None,
    op_executable: str = "op",
    op_timeout_s: float = 10.0,
    ttl_seconds: int = 300,
    session_id: str = "op-cli-session",
    python_executable: str | None = None,
) -> SignerServiceRunPacketSupplyResult:
    """Write one signer service run packet from an existing signer config."""

    root = Path(repo_root).resolve()
    config, config_digest, config_resolved, config_reasons = _read_config(root, config_path)
    output_resolved, output_reasons = _resolve_output_path(root, output_path)
    reasons: list[str] = []
    reasons.extend(config_reasons)
    reasons.extend(output_reasons)
    reasons.extend(_op_executable_reasons(op_executable))
    reasons.extend(_limit_reasons(op_timeout_s, ttl_seconds))
    reasons.extend(_session_reasons(session_id, python_executable or sys.executable))
    deduped = _dedupe(reasons)
    if deduped:
        return _reject(deduped)

    assert config is not None
    assert config_digest is not None
    assert config_resolved is not None
    assert output_resolved is not None
    if config.get("proposal_authority_policy") is not None:
        return _reject(
            (
                FAIL_SIGNER_RUN_PACKET_PROPOSAL_RUNTIME_ADAPTERS_UNAVAILABLE,
            )
        )
    socket_path = Path(str(config["socket_path"])).resolve()
    profiles = tuple(config.get("key_provider_profiles") or ())
    executable = str(python_executable or sys.executable)
    argv = (
        executable,
        "-m",
        _CLI_MODULE,
        "--repo-root",
        str(root),
        "--config",
        str(config_resolved),
        "--expected-config-digest",
        config_digest,
        "--run-packet",
        str(output_resolved),
        "--op-executable",
        str(op_executable),
        "--op-timeout-s",
        _number_text(float(op_timeout_s)),
        "--ttl-seconds",
        str(int(ttl_seconds)),
        "--session-id",
        str(session_id),
    )
    packet: dict[str, Any] = {
        "schema_version": SIGNER_SERVICE_RUN_PACKET_SCHEMA_VERSION,
        "run_mode": "signer_owned_cli_sidecar",
        "repo_root": str(root),
        "working_directory": str(root),
        "python_module": _CLI_MODULE,
        "argv": list(argv),
        "config_path": str(config_resolved),
        "config_digest": config_digest,
        "socket_path": str(socket_path),
        "profile_count": len(profiles),
        "provider_mode": str(config.get("provider_mode") or ""),
        "op_executable": str(op_executable),
        "op_timeout_s": float(op_timeout_s),
        "ttl_seconds": int(ttl_seconds),
        "session_id": str(session_id),
        "process_owner_requirement": "distinct_signer_os_principal",
        "redDog_must_not_spawn": True,
        "main_py_must_not_spawn": True,
        "shell_required": False,
        "shell_command": None,
        "no_secret_values_in_packet": True,
    }
    packet["run_packet_id"] = _digest(packet)
    packet_digest = _digest(packet)
    try:
        _write_json_atomic(output_resolved, packet, repo_root=root)
    except Exception:
        return _reject((FAIL_SIGNER_RUN_PACKET_WRITE_FAILED,))
    return SignerServiceRunPacketSupplyResult(
        accepted=True,
        status=SIGNER_SERVICE_RUN_PACKET_SUPPLY_ACCEPT,
        run_packet_id=str(packet["run_packet_id"]),
        run_packet_path=str(output_resolved),
        run_packet_digest=packet_digest,
        config_path=str(config_resolved),
        config_digest=config_digest,
        socket_path=str(socket_path),
        profile_count=len(profiles),
        rejection_reasons=(),
    )


def _read_config(
    repo_root: Path,
    value: Path | str | None,
) -> tuple[dict[str, Any] | None, str | None, Path | None, tuple[str, ...]]:
    path, reasons = _resolve_existing_file(repo_root, value, FAIL_SIGNER_RUN_PACKET_CONFIG_PATH_INVALID)
    if reasons:
        return None, None, None, reasons
    assert path is not None
    try:
        runtime_root = validate_runtime_root_path(path.parent, repo_root=repo_root)
        payload = json.loads(
            secure_read_confined_text(
                path,
                allowed_root=runtime_root,
                max_bytes=256 * 1024,
            ),
            parse_constant=_reject_json_constant,
        )
    except Exception:
        return None, None, None, (FAIL_SIGNER_RUN_PACKET_CONFIG_MALFORMED,)
    if not isinstance(payload, dict) or _config_reasons(
        repo_root,
        path.parent,
        payload,
    ):
        return None, None, None, (FAIL_SIGNER_RUN_PACKET_CONFIG_MALFORMED,)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload, digest, path, ()


def _config_reasons(
    repo_root: Path,
    expected_runtime_root: Path,
    payload: Mapping[str, Any],
) -> tuple[str, ...]:
    if payload.get("schema_version") != SIGNER_SERVICE_CONFIG_SCHEMA_VERSION:
        return (FAIL_SIGNER_RUN_PACKET_CONFIG_MALFORMED,)
    if payload.get("provider_mode") != PROVIDER_MODE_WSP71_PERMISSIONED:
        return (FAIL_SIGNER_RUN_PACKET_CONFIG_MALFORMED,)
    if payload.get("allow_test_only_key_material") is not False:
        return (FAIL_SIGNER_RUN_PACKET_CONFIG_MALFORMED,)
    if payload.get("permission_snapshot_fresh") is not True:
        return (FAIL_SIGNER_RUN_PACKET_CONFIG_MALFORMED,)
    if rehydrate_signer_socket_service_runtime_config(
        repo_root,
        expected_runtime_root,
        dict(payload),
        expected_config_digest=_digest(payload),
    ) is None:
        return (FAIL_SIGNER_RUN_PACKET_CONFIG_MALFORMED,)
    socket_path = str(payload.get("socket_path") or "")
    if "\x00" in socket_path or socket_path.startswith("\\\\?\\") or socket_path.startswith("//?/"):
        return (FAIL_SIGNER_RUN_PACKET_CONFIG_MALFORMED,)
    socket_resolved = Path(socket_path)
    if not socket_resolved.is_absolute() or _is_inside(socket_resolved.resolve(), repo_root):
        return (FAIL_SIGNER_RUN_PACKET_CONFIG_MALFORMED,)
    profiles = payload.get("key_provider_profiles")
    if not isinstance(profiles, list) or len(profiles) < 1 or len(profiles) > 8:
        return (FAIL_SIGNER_RUN_PACKET_CONFIG_MALFORMED,)
    if not all(isinstance(item, dict) for item in profiles):
        return (FAIL_SIGNER_RUN_PACKET_CONFIG_MALFORMED,)
    if not _ascii_deep(payload):
        return (FAIL_SIGNER_RUN_PACKET_CONFIG_MALFORMED,)
    return ()


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non_finite_json_constant:{value}")


def _resolve_existing_file(
    repo_root: Path,
    value: Path | str | None,
    reason: str,
) -> tuple[Path | None, tuple[str, ...]]:
    path, reasons = _resolve_outside_repo(repo_root, value, reason)
    if reasons:
        return None, reasons
    assert path is not None
    if not path.is_file():
        return None, (reason,)
    return path, ()


def _resolve_output_path(repo_root: Path, value: Path | str | None) -> tuple[Path | None, tuple[str, ...]]:
    path, reasons = _resolve_outside_repo(repo_root, value, FAIL_SIGNER_RUN_PACKET_OUTPUT_PATH_INVALID)
    if reasons:
        return None, reasons
    assert path is not None
    if path.exists() and not path.is_file():
        return None, (FAIL_SIGNER_RUN_PACKET_OUTPUT_PATH_INVALID,)
    return path, ()


def _resolve_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    reason: str,
) -> tuple[Path | None, tuple[str, ...]]:
    if not value:
        return None, (reason,)
    text = str(value)
    if "\x00" in text or text.startswith("\\\\?\\") or text.startswith("//?/"):
        return None, (reason,)
    path = Path(value)
    if not path.is_absolute():
        return None, (reason,)
    resolved = path.resolve()
    if _is_inside(resolved, repo_root):
        return None, (reason,)
    return resolved, ()


def _op_executable_reasons(value: str) -> tuple[str, ...]:
    if not _op_executable_allowed(value):
        return (FAIL_SIGNER_RUN_PACKET_OP_EXECUTABLE_INVALID,)
    return ()


def _op_executable_allowed(value: str) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    stripped = value.strip()
    if stripped != value:
        return False
    basename = stripped.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return basename in {"op", "op.exe"}


def _limit_reasons(op_timeout_s: float, ttl_seconds: int) -> tuple[str, ...]:
    if (
        not isinstance(ttl_seconds, int)
        or ttl_seconds < 30
        or ttl_seconds > 3600
        or float(op_timeout_s) <= 0
        or float(op_timeout_s) > 60
    ):
        return (FAIL_SIGNER_RUN_PACKET_LIMITS_INVALID,)
    return ()


def _session_reasons(session_id: str, python_executable: str) -> tuple[str, ...]:
    if not _ascii_string(session_id) or not session_id or len(session_id) > 128:
        return (FAIL_SIGNER_RUN_PACKET_SESSION_INVALID,)
    if not _ascii_string(python_executable) or not python_executable or "\x00" in python_executable:
        return (FAIL_SIGNER_RUN_PACKET_SESSION_INVALID,)
    return ()


def _write_json_atomic(
    path: Path,
    payload: Mapping[str, Any],
    *,
    repo_root: Path,
) -> None:
    with runtime_operation_lock(str(path) + ".operation"):
        with reddog_runtime_artifact_generation_lock(
            path.parent, repo_root=repo_root
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(
                prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                    json.dump(payload, handle, sort_keys=True, indent=2)
                    handle.write("\n")
                os.replace(tmp_name, path)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)


def _reject(reasons: tuple[str, ...]) -> SignerServiceRunPacketSupplyResult:
    return SignerServiceRunPacketSupplyResult(
        accepted=False,
        status=SIGNER_SERVICE_RUN_PACKET_SUPPLY_REJECT,
        run_packet_id=None,
        run_packet_path=None,
        run_packet_digest=None,
        config_path=None,
        config_digest=None,
        socket_path=None,
        profile_count=0,
        rejection_reasons=_dedupe(reasons),
    )


def _digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _ascii_string(value: object) -> bool:
    return isinstance(value, str) and all(ord(char) < 128 for char in value)


def _ascii_deep(value: object) -> bool:
    if isinstance(value, str):
        return _ascii_string(value)
    if isinstance(value, Mapping):
        return all(_ascii_string(key) and _ascii_deep(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_ascii_deep(item) for item in value)
    if value is None or isinstance(value, (bool, int, float)):
        return True
    return False


def _number_text(value: float) -> str:
    return str(int(value)) if value.is_integer() else str(value)


__all__ = [
    "FAIL_SIGNER_RUN_PACKET_CONFIG_MALFORMED",
    "FAIL_SIGNER_RUN_PACKET_CONFIG_PATH_INVALID",
    "FAIL_SIGNER_RUN_PACKET_LIMITS_INVALID",
    "FAIL_SIGNER_RUN_PACKET_OP_EXECUTABLE_INVALID",
    "FAIL_SIGNER_RUN_PACKET_OUTPUT_PATH_INVALID",
    "FAIL_SIGNER_RUN_PACKET_SESSION_INVALID",
    "FAIL_SIGNER_RUN_PACKET_WRITE_FAILED",
    "SIGNER_SERVICE_RUN_PACKET_SCHEMA_VERSION",
    "SIGNER_SERVICE_RUN_PACKET_SUPPLY_ACCEPT",
    "SIGNER_SERVICE_RUN_PACKET_SUPPLY_REJECT",
    "SignerServiceRunPacketSupplyResult",
    "run_reddog_signer_socket_service_run_packet_supply",
]
