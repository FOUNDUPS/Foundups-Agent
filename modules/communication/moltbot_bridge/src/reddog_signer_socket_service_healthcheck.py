"""Healthcheck for an already-running RedDog signer socket service.

Slice: REDDOG_SIGNER_SERVICE_HEALTHCHECK_PREFLIGHT_PHASE1

This module validates a signer service run packet and performs an optional
bounded healthcheck roundtrip against an already-running signer socket. It does
not start the signer, resolve secrets, bind sockets, parse environment
variables, mutate the repository, enqueue OpenClaw, dispatch Hermes, publish
PRs, settle rewards, or re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    DEFAULT_SIGNER_SOCKET_MAX_RESPONSE_BYTES,
    DEFAULT_SIGNER_SOCKET_TIMEOUT_S,
    SignerSocketConnector,
    build_reddog_isolated_signer_socket_client,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_run_packet_supply import (
    SIGNER_SERVICE_RUN_PACKET_SCHEMA_VERSION,
)


SIGNER_SERVICE_HEALTHCHECK_READY = "SIGNER_SERVICE_HEALTHCHECK_READY"
SIGNER_SERVICE_HEALTHCHECK_REJECT = "SIGNER_SERVICE_HEALTHCHECK_REJECT"

FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_PATH_INVALID = "signer_healthcheck_run_packet_path_invalid"
FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED = "signer_healthcheck_run_packet_malformed"
FAIL_SIGNER_HEALTHCHECK_CONFIG_MISMATCH = "signer_healthcheck_config_mismatch"
FAIL_SIGNER_HEALTHCHECK_PROFILE_MISSING = "signer_healthcheck_profile_missing"
FAIL_SIGNER_HEALTHCHECK_REQUESTER_INVALID = "signer_healthcheck_requester_invalid"
FAIL_SIGNER_HEALTHCHECK_CLIENT_REJECTED = "signer_healthcheck_client_rejected"
FAIL_SIGNER_HEALTHCHECK_SIGNER_REJECTED = "signer_healthcheck_signer_rejected"


@dataclass(frozen=True)
class SignerServiceHealthcheckResult:
    """Audit-safe result for signer socket service healthcheck."""

    accepted: bool
    status: str
    run_packet_path: str | None
    run_packet_id: str | None
    config_path: str | None
    config_digest: str | None
    socket_path: str | None
    signer_profile_id: str | None
    signer_public_key: str | None
    requester_principal_id: str | None
    request_digest: str | None
    response_digest: str | None
    rejection_reasons: tuple[str, ...]
    no_signature_value_returned: bool = True
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


def run_reddog_signer_socket_service_healthcheck(
    *,
    repo_root: Path | str,
    run_packet_path: Path | str | None,
    requester_principal_id: str | None = None,
    signer_profile_id: str = "reddog-work-authority",
    timeout_s: float = DEFAULT_SIGNER_SOCKET_TIMEOUT_S,
    max_response_bytes: int = DEFAULT_SIGNER_SOCKET_MAX_RESPONSE_BYTES,
    connector: Optional[SignerSocketConnector] = None,
) -> SignerServiceHealthcheckResult:
    """Validate run packet/config and probe an already-running signer socket."""

    root = Path(repo_root).resolve()
    packet, packet_path, packet_reasons = _read_run_packet(root, run_packet_path)
    if packet_reasons:
        return _reject(packet_reasons)
    assert packet is not None
    assert packet_path is not None
    config, config_digest, config_reasons = _read_bound_config(root, packet)
    if config_reasons:
        return _reject(config_reasons, packet_path=str(packet_path), packet=packet)
    assert config is not None
    assert config_digest is not None
    profile = _select_profile(config, signer_profile_id)
    if profile is None:
        return _reject(
            (FAIL_SIGNER_HEALTHCHECK_PROFILE_MISSING,),
            packet_path=str(packet_path),
            packet=packet,
            config_digest=config_digest,
        )
    requester = requester_principal_id or _default_requester(config)
    if not _ascii_string(requester):
        return _reject(
            (FAIL_SIGNER_HEALTHCHECK_REQUESTER_INVALID,),
            packet_path=str(packet_path),
            packet=packet,
            config_digest=config_digest,
        )
    socket_path = Path(str(packet["socket_path"])).resolve()
    built = build_reddog_isolated_signer_socket_client(
        repo_root=root,
        socket_path=socket_path,
        timeout_s=timeout_s,
        max_response_bytes=max_response_bytes,
        connector=connector,
    )
    if not built.accepted or built.client is None:
        return _reject(
            (FAIL_SIGNER_HEALTHCHECK_CLIENT_REJECTED, *built.rejection_reasons),
            packet_path=str(packet_path),
            packet=packet,
            config_digest=config_digest,
            profile=profile,
            requester=requester,
        )
    request = _health_request(packet=packet, profile=profile, requester=requester)
    response = built.client.sign(request)
    if not response.accepted or response.signer_public_key != profile["expected_public_key"]:
        return _reject(
            (
                FAIL_SIGNER_HEALTHCHECK_SIGNER_REJECTED,
                str(response.rejection_code or ""),
            ),
            packet_path=str(packet_path),
            packet=packet,
            config_digest=config_digest,
            profile=profile,
            requester=requester,
            request_digest=_digest(request.to_dict()),
        )
    return SignerServiceHealthcheckResult(
        accepted=True,
        status=SIGNER_SERVICE_HEALTHCHECK_READY,
        run_packet_path=str(packet_path),
        run_packet_id=str(packet["run_packet_id"]),
        config_path=str(packet["config_path"]),
        config_digest=config_digest,
        socket_path=str(socket_path),
        signer_profile_id=str(profile["signer_profile_id"]),
        signer_public_key=str(profile["expected_public_key"]),
        requester_principal_id=str(requester),
        request_digest=_digest(request.to_dict()),
        response_digest=_digest(response.to_dict()),
        rejection_reasons=(),
    )


def _read_run_packet(
    repo_root: Path,
    value: Path | str | None,
) -> tuple[dict[str, Any] | None, Path | None, tuple[str, ...]]:
    path, reasons = _resolve_existing_outside_file(
        repo_root,
        value,
        FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_PATH_INVALID,
    )
    if reasons:
        return None, None, reasons
    assert path is not None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, None, (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
    if not isinstance(payload, dict) or _packet_reasons(repo_root, payload):
        return None, None, (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
    return payload, path, ()


def _packet_reasons(repo_root: Path, payload: Mapping[str, Any]) -> tuple[str, ...]:
    if payload.get("schema_version") != SIGNER_SERVICE_RUN_PACKET_SCHEMA_VERSION:
        return (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
    if not _ascii_deep(payload):
        return (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
    packet_id = str(payload.get("run_packet_id") or "")
    if not packet_id.startswith("sha256:"):
        return (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
    without_id = {key: value for key, value in payload.items() if key != "run_packet_id"}
    if packet_id != _digest(without_id):
        return (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
    if payload.get("run_mode") != "signer_owned_cli_sidecar":
        return (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
    if payload.get("redDog_must_not_spawn") is not True:
        return (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
    if payload.get("main_py_must_not_spawn") is not True:
        return (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
    if payload.get("shell_required") is not False or payload.get("shell_command") is not None:
        return (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
    if payload.get("no_secret_values_in_packet") is not True:
        return (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
    if not str(payload.get("config_digest") or "").startswith("sha256:"):
        return (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
    argv = payload.get("argv")
    if (
        not isinstance(argv, list)
        or len(argv) < 3
        or not all(isinstance(item, str) and item for item in argv)
    ):
        return (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
    for key in ("repo_root", "working_directory"):
        if not _ascii_string(payload.get(key)):
            return (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
        if Path(str(payload[key])).resolve() != repo_root:
            return (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
    for key in ("config_path", "socket_path"):
        path_text = str(payload.get(key) or "")
        if "\x00" in path_text or path_text.startswith("\\\\?\\") or path_text.startswith("//?/"):
            return (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
        path = Path(path_text)
        if not path.is_absolute() or _is_inside(path.resolve(), repo_root):
            return (FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,)
    return ()


def _read_bound_config(
    repo_root: Path,
    packet: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str | None, tuple[str, ...]]:
    config_path, reasons = _resolve_existing_outside_file(
        repo_root,
        packet.get("config_path"),
        FAIL_SIGNER_HEALTHCHECK_CONFIG_MISMATCH,
    )
    if reasons:
        return None, None, reasons
    assert config_path is not None
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return None, None, (FAIL_SIGNER_HEALTHCHECK_CONFIG_MISMATCH,)
    if not isinstance(payload, dict) or not _ascii_deep(payload):
        return None, None, (FAIL_SIGNER_HEALTHCHECK_CONFIG_MISMATCH,)
    digest = _digest(payload)
    if digest != str(packet.get("config_digest") or ""):
        return None, None, (FAIL_SIGNER_HEALTHCHECK_CONFIG_MISMATCH,)
    if str(payload.get("socket_path") or "") != str(packet.get("socket_path") or ""):
        return None, None, (FAIL_SIGNER_HEALTHCHECK_CONFIG_MISMATCH,)
    return payload, digest, ()


def _select_profile(config: Mapping[str, Any], signer_profile_id: str) -> Mapping[str, Any] | None:
    profiles = config.get("key_provider_profiles")
    if not isinstance(profiles, list):
        return None
    for item in profiles:
        if isinstance(item, Mapping) and item.get("signer_profile_id") == signer_profile_id:
            return item
    for item in profiles:
        if isinstance(item, Mapping) and item.get("signer_profile_id") == "reddog-profile":
            return item
    return None


def _default_requester(config: Mapping[str, Any]) -> str | None:
    peer_policy = config.get("peer_policy")
    if not isinstance(peer_policy, Mapping):
        return None
    uid_map = peer_policy.get("uid_to_principal")
    if not isinstance(uid_map, Mapping) or not uid_map:
        return None
    first_key = sorted(str(key) for key in uid_map.keys())[0]
    return str(uid_map.get(first_key) or "")


def _health_request(
    *,
    packet: Mapping[str, Any],
    profile: Mapping[str, Any],
    requester: str,
) -> SigningRequest:
    payload = {
        "run_packet_id": str(packet["run_packet_id"]),
        "config_digest": str(packet["config_digest"]),
        "socket_path": str(packet["socket_path"]),
        "signer_profile_id": str(profile["signer_profile_id"]),
    }
    signing_input = "reddog-signer-health.v1." + json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return SigningRequest(
        signing_input=signing_input,
        payload_digest=_digest(payload),
        signer_role="healthcheck",
        signer_public_key=str(profile["expected_public_key"]),
        requester_principal_id=requester,
        nonce="signer-healthcheck:" + str(packet["run_packet_id"]).removeprefix("sha256:")[:16],
        key_epoch=str(profile["expected_key_epoch"]),
        requested_operation="signer_socket_healthcheck",
        authority_tier="LOW",
        consensus_receipt_digest=None,
    )


def _resolve_existing_outside_file(
    repo_root: Path,
    value: object,
    reason: str,
) -> tuple[Path | None, tuple[str, ...]]:
    if not value:
        return None, (reason,)
    text = str(value)
    if "\x00" in text or text.startswith("\\\\?\\") or text.startswith("//?/"):
        return None, (reason,)
    path = Path(text)
    if not path.is_absolute():
        return None, (reason,)
    resolved = path.resolve()
    if _is_inside(resolved, repo_root) or not resolved.is_file():
        return None, (reason,)
    return resolved, ()


def _reject(
    reasons: tuple[str, ...],
    *,
    packet_path: str | None = None,
    packet: Mapping[str, Any] | None = None,
    config_digest: str | None = None,
    profile: Mapping[str, Any] | None = None,
    requester: str | None = None,
    request_digest: str | None = None,
) -> SignerServiceHealthcheckResult:
    return SignerServiceHealthcheckResult(
        accepted=False,
        status=SIGNER_SERVICE_HEALTHCHECK_REJECT,
        run_packet_path=packet_path,
        run_packet_id=str(packet.get("run_packet_id") or "") if packet else None,
        config_path=str(packet.get("config_path") or "") if packet else None,
        config_digest=config_digest,
        socket_path=str(packet.get("socket_path") or "") if packet else None,
        signer_profile_id=str(profile.get("signer_profile_id") or "") if profile else None,
        signer_public_key=str(profile.get("expected_public_key") or "") if profile else None,
        requester_principal_id=requester,
        request_digest=request_digest,
        response_digest=None,
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
    return isinstance(value, str) and all(ord(char) < 128 for char in value) and bool(value)


def _ascii_deep(value: object) -> bool:
    if isinstance(value, str):
        return all(ord(char) < 128 for char in value)
    if isinstance(value, Mapping):
        return all(
            isinstance(key, str)
            and all(ord(char) < 128 for char in key)
            and _ascii_deep(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return all(_ascii_deep(item) for item in value)
    if value is None or isinstance(value, (bool, int, float)):
        return True
    return False


__all__ = [
    "FAIL_SIGNER_HEALTHCHECK_CLIENT_REJECTED",
    "FAIL_SIGNER_HEALTHCHECK_CONFIG_MISMATCH",
    "FAIL_SIGNER_HEALTHCHECK_PROFILE_MISSING",
    "FAIL_SIGNER_HEALTHCHECK_REQUESTER_INVALID",
    "FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED",
    "FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_PATH_INVALID",
    "FAIL_SIGNER_HEALTHCHECK_SIGNER_REJECTED",
    "SIGNER_SERVICE_HEALTHCHECK_READY",
    "SIGNER_SERVICE_HEALTHCHECK_REJECT",
    "SignerServiceHealthcheckResult",
    "run_reddog_signer_socket_service_healthcheck",
]
