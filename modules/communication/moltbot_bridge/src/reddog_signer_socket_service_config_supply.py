"""Signer socket service config supplier for resident RedDog runtime.

Slice: REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY_PHASE1

This module materializes the outside-repo JSON config consumed by the
signer-owned CLI. It binds the existing promoted authority profile to explicit
WSP71 op:// references and a signer-owned peer policy. It does not resolve
secrets, start the signer service, bind sockets, parse environment variables,
spawn processes, mutate the repository, enqueue OpenClaw, dispatch Hermes,
publish PRs, settle rewards, or re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_WSP71_PERMISSIONED,
)
from modules.infrastructure.secrets_mcp.src.vault_resolver import parse_op_reference


SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT = "SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT"
SIGNER_SERVICE_CONFIG_SUPPLY_REJECT = "SIGNER_SERVICE_CONFIG_SUPPLY_REJECT"
SIGNER_SERVICE_CONFIG_SCHEMA_VERSION = "reddog_signer_service_config.v1"

FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID = "signer_config_authority_profile_invalid"
FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID = "signer_config_output_path_invalid"
FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID = "signer_config_socket_path_invalid"
FAIL_SIGNER_CONFIG_OP_REF_INVALID = "signer_config_op_ref_invalid"
FAIL_SIGNER_CONFIG_OP_REF_REUSED = "signer_config_op_ref_reused"
FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID = "signer_config_peer_policy_invalid"
FAIL_SIGNER_CONFIG_LIMITS_INVALID = "signer_config_limits_invalid"
FAIL_SIGNER_CONFIG_WRITE_FAILED = "signer_config_write_failed"

_REQUIRED_AUTHORITY_FIELDS = (
    "principal_id",
    "principal_public_key",
    "reddog_id",
    "reddog_public_key",
    "permission_snapshot_digest",
    "key_epoch",
)


@dataclass(frozen=True)
class SignerServiceConfigSupplyResult:
    """Audit-safe result for signer service config materialization."""

    accepted: bool
    status: str
    config_supply_receipt_id: str | None
    config_path: str | None
    config_digest: str | None
    socket_path: str | None
    principal_id: str | None
    reddog_id: str | None
    profile_count: int
    rejection_reasons: tuple[str, ...]
    no_secret_values_written: bool = True
    no_secret_values_resolved: bool = True
    no_signer_started: bool = True
    no_socket_bound: bool = True
    no_process_spawned: bool = True
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_signer_socket_service_config_supply(
    *,
    repo_root: Path | str,
    authority_profile: Mapping[str, Any] | None,
    output_path: Path | str | None,
    socket_path: Path | str | None,
    principal_signing_key_ref: str,
    principal_audit_mac_key_ref: str,
    reddog_signing_key_ref: str,
    reddog_audit_mac_key_ref: str,
    peer_uid_to_principal: Mapping[int | str, str],
    allowed_gids: Sequence[int | str] = (),
    max_requests: int = 16,
    timeout_s: float = 5.0,
    max_request_bytes: int = 16384,
    max_response_bytes: int = 16384,
    principal_signer_agent_id: str = "signer:principal",
    reddog_signer_agent_id: str = "signer:reddog",
) -> SignerServiceConfigSupplyResult:
    """Write one signer CLI config from existing authority artifacts."""

    root = Path(repo_root).resolve()
    profile = _mapping(authority_profile)
    reasons: list[str] = []
    reasons.extend(_authority_profile_reasons(profile))
    out, output_reasons = _resolve_output_path(root, output_path)
    reasons.extend(output_reasons)
    sock, socket_reasons = _resolve_socket_path(root, socket_path)
    reasons.extend(socket_reasons)
    op_refs = (
        principal_signing_key_ref,
        principal_audit_mac_key_ref,
        reddog_signing_key_ref,
        reddog_audit_mac_key_ref,
    )
    reasons.extend(_op_ref_reasons(op_refs))
    peer_policy, peer_reasons = _peer_policy(peer_uid_to_principal, allowed_gids)
    reasons.extend(peer_reasons)
    reasons.extend(_limit_reasons(max_requests, timeout_s, max_request_bytes, max_response_bytes))

    deduped = _dedupe(reasons)
    if deduped:
        return _reject(deduped)

    assert out is not None
    assert sock is not None
    assert peer_policy is not None
    config = _config(
        authority_profile=profile,
        socket_path=sock,
        principal_signing_key_ref=principal_signing_key_ref,
        principal_audit_mac_key_ref=principal_audit_mac_key_ref,
        reddog_signing_key_ref=reddog_signing_key_ref,
        reddog_audit_mac_key_ref=reddog_audit_mac_key_ref,
        peer_policy=peer_policy,
        max_requests=max_requests,
        timeout_s=timeout_s,
        max_request_bytes=max_request_bytes,
        max_response_bytes=max_response_bytes,
        principal_signer_agent_id=principal_signer_agent_id,
        reddog_signer_agent_id=reddog_signer_agent_id,
    )
    config_digest = _digest(config)
    receipt = {
        "schema_version": SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
        "config_digest": config_digest,
        "config_path": str(out),
        "socket_path": str(sock),
        "principal_id": str(profile["principal_id"]),
        "reddog_id": str(profile["reddog_id"]),
        "profile_count": 2,
        "no_secret_values_written": True,
        "no_secret_values_resolved": True,
        "no_signer_started": True,
        "no_socket_bound": True,
    }
    receipt["config_supply_receipt_id"] = _digest(receipt)
    try:
        _write_json_atomic(out, config)
    except Exception:
        return _reject((FAIL_SIGNER_CONFIG_WRITE_FAILED,))
    return SignerServiceConfigSupplyResult(
        accepted=True,
        status=SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT,
        config_supply_receipt_id=str(receipt["config_supply_receipt_id"]),
        config_path=str(out),
        config_digest=config_digest,
        socket_path=str(sock),
        principal_id=str(profile["principal_id"]),
        reddog_id=str(profile["reddog_id"]),
        profile_count=2,
        rejection_reasons=(),
    )


def _config(
    *,
    authority_profile: Mapping[str, Any],
    socket_path: Path,
    principal_signing_key_ref: str,
    principal_audit_mac_key_ref: str,
    reddog_signing_key_ref: str,
    reddog_audit_mac_key_ref: str,
    peer_policy: Mapping[str, Any],
    max_requests: int,
    timeout_s: float,
    max_request_bytes: int,
    max_response_bytes: int,
    principal_signer_agent_id: str,
    reddog_signer_agent_id: str,
) -> dict[str, Any]:
    principal_public = str(authority_profile["principal_public_key"])
    reddog_public = str(authority_profile["reddog_public_key"])
    permission_digest = str(authority_profile["permission_snapshot_digest"])
    key_epoch = str(authority_profile["key_epoch"])
    return {
        "schema_version": SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
        "socket_path": str(socket_path),
        "provider_mode": PROVIDER_MODE_WSP71_PERMISSIONED,
        "allow_test_only_key_material": False,
        "permission_snapshot_fresh": True,
        "max_requests": int(max_requests),
        "timeout_s": float(timeout_s),
        "max_request_bytes": int(max_request_bytes),
        "max_response_bytes": int(max_response_bytes),
        "key_provider_profiles": [
            {
                "signer_profile_id": "principal-identity",
                "signer_agent_id": str(principal_signer_agent_id),
                "signing_key_ref": str(principal_signing_key_ref),
                "audit_mac_key_ref": str(principal_audit_mac_key_ref),
                "expected_public_key": principal_public,
                "expected_key_fingerprint": public_key_fingerprint(principal_public),
                "expected_key_epoch": key_epoch,
                "permission_snapshot_digest": permission_digest,
                "ttl_seconds": int(authority_profile.get("identity_ttl_seconds") or 300),
            },
            {
                "signer_profile_id": "reddog-work-authority",
                "signer_agent_id": str(reddog_signer_agent_id),
                "signing_key_ref": str(reddog_signing_key_ref),
                "audit_mac_key_ref": str(reddog_audit_mac_key_ref),
                "expected_public_key": reddog_public,
                "expected_key_fingerprint": public_key_fingerprint(reddog_public),
                "expected_key_epoch": key_epoch,
                "permission_snapshot_digest": permission_digest,
                "ttl_seconds": int(authority_profile.get("work_authority_ttl_seconds") or 300),
            },
        ],
        "peer_policy": dict(peer_policy),
    }


def _authority_profile_reasons(profile: Mapping[str, Any]) -> list[str]:
    if not profile or not _ascii_deep(profile):
        return [FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID]
    missing = [field for field in _REQUIRED_AUTHORITY_FIELDS if not str(profile.get(field) or "")]
    if missing:
        return [FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID + ":" + field for field in missing]
    if str(profile.get("principal_public_key")) == str(profile.get("reddog_public_key")):
        return [FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID + ":key_reuse"]
    return []


def _resolve_output_path(repo_root: Path, value: Path | str | None) -> tuple[Path | None, list[str]]:
    path, reasons = _resolve_outside_repo(repo_root, value, FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID)
    if reasons:
        return None, reasons
    assert path is not None
    if path.exists() and not path.is_file():
        return None, [FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID]
    return path, []


def _resolve_socket_path(repo_root: Path, value: Path | str | None) -> tuple[Path | None, list[str]]:
    path, reasons = _resolve_outside_repo(repo_root, value, FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID)
    if reasons:
        return None, reasons
    assert path is not None
    if path.exists():
        return None, [FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID]
    return path, []


def _resolve_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    reason: str,
) -> tuple[Path | None, list[str]]:
    if not value:
        return None, [reason]
    text = str(value)
    if "\x00" in text or text.startswith("\\\\?\\") or text.startswith("//?/"):
        return None, [reason]
    path = Path(value)
    if not path.is_absolute():
        return None, [reason]
    resolved = path.resolve()
    if _is_inside(resolved, repo_root):
        return None, [reason]
    return resolved, []


def _op_ref_reasons(values: Sequence[str]) -> list[str]:
    refs = tuple(str(value or "").strip() for value in values)
    reasons: list[str] = []
    for ref in refs:
        if not parse_op_reference(ref):
            reasons.append(FAIL_SIGNER_CONFIG_OP_REF_INVALID)
    if len(set(refs)) != len(refs):
        reasons.append(FAIL_SIGNER_CONFIG_OP_REF_REUSED)
    return reasons


def _peer_policy(
    uid_to_principal: Mapping[int | str, str],
    allowed_gids: Sequence[int | str],
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        uid_map = {int(uid): str(principal) for uid, principal in uid_to_principal.items()}
        gids = tuple(int(gid) for gid in allowed_gids)
    except Exception:
        return None, [FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID]
    if not uid_map:
        return None, [FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID]
    if any(uid < 0 for uid in uid_map) or any(gid < 0 for gid in gids):
        return None, [FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID]
    if any(not principal or not _ascii_string(principal) for principal in uid_map.values()):
        return None, [FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID]
    return {
        "uid_to_principal": {str(uid): principal for uid, principal in sorted(uid_map.items())},
        "allowed_gids": list(gids),
        "transport": "unix_socket",
        "credential_source_prefix": "kernel_peer_credential",
    }, []


def _limit_reasons(
    max_requests: int,
    timeout_s: float,
    max_request_bytes: int,
    max_response_bytes: int,
) -> list[str]:
    if (
        not isinstance(max_requests, int)
        or max_requests < 2
        or max_requests > 128
        or timeout_s <= 0
        or timeout_s > 30
        or max_request_bytes < 1024
        or max_request_bytes > 262144
        or max_response_bytes < 1024
        or max_response_bytes > 262144
    ):
        return [FAIL_SIGNER_CONFIG_LIMITS_INVALID]
    return []


def _mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, sort_keys=True, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _reject(reasons: Sequence[str]) -> SignerServiceConfigSupplyResult:
    return SignerServiceConfigSupplyResult(
        accepted=False,
        status=SIGNER_SERVICE_CONFIG_SUPPLY_REJECT,
        config_supply_receipt_id=None,
        config_path=None,
        config_digest=None,
        socket_path=None,
        principal_id=None,
        reddog_id=None,
        profile_count=0,
        rejection_reasons=_dedupe(reasons),
    )


def _digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
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


__all__ = [
    "FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID",
    "FAIL_SIGNER_CONFIG_LIMITS_INVALID",
    "FAIL_SIGNER_CONFIG_OP_REF_INVALID",
    "FAIL_SIGNER_CONFIG_OP_REF_REUSED",
    "FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID",
    "FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID",
    "FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID",
    "FAIL_SIGNER_CONFIG_WRITE_FAILED",
    "SIGNER_SERVICE_CONFIG_SCHEMA_VERSION",
    "SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT",
    "SIGNER_SERVICE_CONFIG_SUPPLY_REJECT",
    "SignerServiceConfigSupplyResult",
    "run_reddog_signer_socket_service_config_supply",
]
