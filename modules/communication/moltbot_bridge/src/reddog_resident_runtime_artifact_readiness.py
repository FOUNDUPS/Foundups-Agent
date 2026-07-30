"""Semantic readiness validation for the seven resident live-canary artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import SelectionDecision
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    ModelRuntimeBindingDecision,
    rehydrate_model_runtime_binding_receipt,
    rehydrate_model_selection_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_digest import (
    canonical_model_runtime_binding_digest,
)
from modules.communication.moltbot_bridge.src.reddog_bounded_artifact_generation_runtime import (
    RUNTIME_SURFACE_ARTIFACT_GENERATION,
)
from modules.communication.moltbot_bridge.src.reddog_execution_valve_environment_supply import (
    resolve_reddog_execution_valve_expected_bindings,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    GovernedExecutionValveEnvironment,
    validate_governed_execution_valve_environment,
)
from modules.communication.moltbot_bridge.src.reddog_execution_valve_use_time_authority import (
    AUTHENTICATED_RUNTIME_ARTIFACT_MANIFEST_SELECTION_MISSING,
    CURRENT_RUNTIME_ARTIFACT_GENERATION_VERIFIER_MISSING,
    DURABLE_RUNTIME_ARTIFACT_MANIFEST_REPLAY_STATE_MISSING,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
    SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


REQUIRED_RUNTIME_ARTIFACTS = (
    "authoritative_work_state.json", "authority_profile.json", "execution_valve_env.json",
    "permission_snapshots.json", "principal_authority_records.json",
    "signer_service_config.json", "signer_service_run_packet.json",
)
_SIGNER_CONFIG_FIELDS = {
    "schema_version", "runtime_root", "signer_runtime_root", "socket_path",
    "control_loop_anchor_path", "control_loop_authority_policy",
    "provider_mode", "allow_test_only_key_material",
    "permission_snapshot_fresh", "max_requests", "timeout_s", "max_request_bytes",
    "max_response_bytes", "key_provider_profiles", "peer_policy",
}
_SIGNER_PROFILE_FIELDS = {
    "signer_profile_id", "signer_agent_id", "signing_key_ref", "audit_mac_key_ref",
    "expected_public_key", "expected_key_fingerprint", "expected_key_epoch",
    "permission_snapshot_digest", "ttl_seconds",
}
_PEER_POLICY_FIELDS = {
    "uid_to_principal", "allowed_gids", "transport", "credential_source_prefix",
}
_RUN_PACKET_FIELDS = {
    "schema_version", "run_mode", "repo_root", "working_directory", "python_module",
    "argv", "config_path", "config_digest", "socket_path", "profile_count",
    "provider_mode", "op_executable", "op_timeout_s", "ttl_seconds", "session_id",
    "process_owner_requirement", "redDog_must_not_spawn", "main_py_must_not_spawn",
    "shell_required", "shell_command", "no_secret_values_in_packet", "run_packet_id",
}


@dataclass(frozen=True)
class RuntimeArtifactSemanticCheck:
    filename: str
    accepted: bool
    rejection_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResidentRuntimeArtifactReadiness:
    accepted: bool
    checks: tuple[RuntimeArtifactSemanticCheck, ...]
    authorization_mode: str | None
    authorization_binding_digest: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_reddog_resident_runtime_artifacts(
    *, repo_root: Path | str, runtime_root: Path | str, queue_item_id: str, now_epoch: int,
) -> ResidentRuntimeArtifactReadiness:
    """Load exact canonical paths and cross-validate one resident queue lineage."""

    root = Path(repo_root).resolve()
    runtime = Path(os.path.abspath(Path(runtime_root).expanduser()))
    payloads, load_reasons = _load_artifacts(root, runtime)
    reasons = {name: list(load_reasons.get(name, ())) for name in REQUIRED_RUNTIME_ARTIFACTS}
    if not any(reasons.values()):
        _validate_governed_lineage(payloads, queue_item_id, now_epoch, reasons)
        _validate_model_bindings(payloads, reasons)
        _validate_signer_artifacts(root, runtime, payloads, reasons)
        reasons["execution_valve_env.json"].extend(
            (
                AUTHENTICATED_RUNTIME_ARTIFACT_MANIFEST_SELECTION_MISSING,
                DURABLE_RUNTIME_ARTIFACT_MANIFEST_REPLAY_STATE_MISSING,
                CURRENT_RUNTIME_ARTIFACT_GENERATION_VERIFIER_MISSING,
            )
        )
    checks = tuple(
        RuntimeArtifactSemanticCheck(name, not reasons[name], tuple(dict.fromkeys(reasons[name])))
        for name in REQUIRED_RUNTIME_ARTIFACTS
    )
    valve = payloads.get("execution_valve_env.json", {})
    return ResidentRuntimeArtifactReadiness(
        accepted=all(item.accepted for item in checks),
        checks=checks,
        authorization_mode=_text(valve.get("authorization_mode")) or None,
        authorization_binding_digest=_text(valve.get("authorization_binding_digest")) or None,
    )


def _load_artifacts(
    repo_root: Path, runtime_root: Path,
) -> tuple[dict[str, Mapping[str, Any]], dict[str, tuple[str, ...]]]:
    payloads: dict[str, Mapping[str, Any]] = {}
    reasons: dict[str, tuple[str, ...]] = {}
    if _inside(runtime_root, repo_root):
        return {}, {name: ("runtime_root_inside_repo",) for name in REQUIRED_RUNTIME_ARTIFACTS}
    for name in REQUIRED_RUNTIME_ARTIFACTS:
        path = runtime_root / name
        if path.is_symlink() or not path.is_file():
            reasons[name] = ("artifact_missing_or_symlink",)
            continue
        try:
            payload = read_reddog_runtime_json_mapping(path, allowed_root=runtime_root)
        except Exception:
            reasons[name] = ("artifact_malformed",)
            continue
        if not isinstance(payload, Mapping):
            reasons[name] = ("artifact_not_mapping",)
            continue
        payloads[name] = payload
    return payloads, reasons


def _validate_governed_lineage(
    payloads: Mapping[str, Mapping[str, Any]], queue_id: str, now_epoch: int,
    reasons: dict[str, list[str]],
) -> None:
    work = payloads["authoritative_work_state.json"]
    profile = payloads["authority_profile.json"]
    permissions = payloads["permission_snapshots.json"]
    principals = payloads["principal_authority_records.json"]
    _validate_resolver_schemas(permissions, principals, reasons)
    if not _work_state_revision_valid(work):
        reasons["authoritative_work_state.json"].append("work_state_revision_invalid")
    bindings, binding_reasons = resolve_reddog_execution_valve_expected_bindings(
        work_state=work, authority_profile=profile, permission_snapshots=permissions,
        principal_authority_records=principals, queue_item_id=queue_id,
    )
    for reason in binding_reasons:
        reasons[_reason_artifact(reason)].append(reason)
    _freshness_reasons(profile, permissions, now_epoch, reasons)
    if bindings is not None:
        _validate_valve(payloads["execution_valve_env.json"], bindings, reasons)


def _validate_valve(
    payload: Mapping[str, Any], bindings: Mapping[str, Any], reasons: dict[str, list[str]],
) -> None:
    try:
        governed = GovernedExecutionValveEnvironment.from_mapping(payload)
    except ValueError as exc:
        reasons["execution_valve_env.json"].append(str(exc))
        return
    reasons["execution_valve_env.json"].extend(
        validate_governed_execution_valve_environment(governed, bindings)
    )


def _validate_model_bindings(
    payloads: Mapping[str, Mapping[str, Any]], reasons: dict[str, list[str]],
) -> None:
    profile = payloads["authority_profile.json"]
    try:
        selection = rehydrate_model_selection_receipt(profile["model_selection_receipt"])
        if selection.decision != SelectionDecision.SELECTED:
            raise ValueError("selection_not_selected")
        if profile.get("model_selection_receipt_id") != selection.receipt_id:
            raise ValueError("selection_id")
        if profile.get("model_selection_digest") != _digest(profile["model_selection_receipt"]):
            raise ValueError("selection_digest")
    except Exception:
        reasons["authority_profile.json"].append("model_selection_receipt_invalid")
    try:
        binding = rehydrate_model_runtime_binding_receipt(profile["model_runtime_binding_receipt"])
        if binding.decision != ModelRuntimeBindingDecision.BOUND:
            raise ValueError("runtime_not_bound")
        if binding.runtime_surface != RUNTIME_SURFACE_ARTIFACT_GENERATION:
            raise ValueError("runtime_surface")
        if profile.get("model_runtime_binding_receipt_id") != binding.receipt_id:
            raise ValueError("runtime_id")
        if profile.get(
            "model_runtime_binding_digest"
        ) != canonical_model_runtime_binding_digest(
            profile["model_runtime_binding_receipt"]
        ):
            raise ValueError("runtime_digest")
    except Exception:
        reasons["authority_profile.json"].append("model_runtime_binding_receipt_invalid")


def _validate_signer_artifacts(
    repo_root: Path, runtime_root: Path, payloads: Mapping[str, Mapping[str, Any]],
    reasons: dict[str, list[str]],
) -> None:
    profile = payloads["authority_profile.json"]
    config = payloads["signer_service_config.json"]
    packet = payloads["signer_service_run_packet.json"]
    config_reasons = _signer_config_reasons(repo_root, runtime_root, profile, config)
    reasons["signer_service_config.json"].extend(config_reasons)
    packet_reasons = _signer_packet_reasons(repo_root, runtime_root, config, packet)
    reasons["signer_service_run_packet.json"].extend(packet_reasons)


def _signer_config_reasons(
    repo: Path, runtime: Path, profile: Mapping[str, Any], config: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if set(config) != _SIGNER_CONFIG_FIELDS:
        reasons.append("signer_config_field_set_invalid")
    if _forbidden_serialized_keys(config):
        reasons.append("signer_config_forbidden_key_present")
    if config.get("schema_version") != SIGNER_SERVICE_CONFIG_SCHEMA_VERSION:
        reasons.append("signer_config_schema_invalid")
    if config.get("provider_mode") != "WSP71_PERMISSIONED":
        reasons.append("signer_provider_mode_invalid")
    if config.get("allow_test_only_key_material") is not False:
        reasons.append("signer_test_key_material_forbidden")
    reasons.extend(_signer_runtime_path_reasons(repo, runtime, config))
    reasons.extend(_signer_control_policy_reasons(profile, config))
    expected = (
        ("principal-identity", profile.get("principal_public_key")),
        ("reddog-work-authority", profile.get("reddog_public_key")),
    )
    providers = config.get("key_provider_profiles")
    if not isinstance(providers, Sequence) or len(providers) != 2:
        return [*reasons, "signer_profile_count_invalid"]
    op_refs: list[str] = []
    for item, (profile_id, public_key) in zip(providers, expected):
        if not isinstance(item, Mapping) or item.get("signer_profile_id") != profile_id:
            reasons.append("signer_profile_identity_invalid")
            continue
        if set(item) != _SIGNER_PROFILE_FIELDS:
            reasons.append("signer_profile_field_set_invalid")
        checks = (
            (item.get("expected_public_key"), public_key),
            (item.get("expected_key_fingerprint"), public_key_fingerprint(str(public_key or ""))),
            (item.get("expected_key_epoch"), profile.get("key_epoch")),
            (item.get("permission_snapshot_digest"), profile.get("permission_snapshot_digest")),
        )
        if any(left != right for left, right in checks):
            reasons.append("signer_profile_binding_mismatch")
        if not str(item.get("signing_key_ref") or "").startswith("op://"):
            reasons.append("signer_key_reference_invalid")
        op_refs.extend((str(item.get("signing_key_ref") or ""), str(item.get("audit_mac_key_ref") or "")))
    if len(set(op_refs)) != 4 or not all(value.startswith("op://") for value in op_refs):
        reasons.append("signer_key_reference_reused_or_invalid")
    peer = config.get("peer_policy")
    if not isinstance(peer, Mapping) or set(peer) != _PEER_POLICY_FIELDS:
        reasons.append("signer_peer_policy_field_set_invalid")
    elif (
        peer.get("transport") != "unix_socket"
        or peer.get("credential_source_prefix") != "kernel_peer_credential"
        or not isinstance(peer.get("uid_to_principal"), Mapping)
        or not peer.get("uid_to_principal")
    ):
        reasons.append("signer_peer_policy_invalid")
    # The server verifies client credentials, but no client-side fresh signed
    # challenge currently authenticates the signer peer.
    reasons.append("signer_client_peer_handshake_verifier_missing")
    return reasons


def _signer_runtime_path_reasons(
    repo: Path,
    runtime: Path,
    config: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    try:
        configured_runtime = validate_runtime_root_path(
            config.get("runtime_root"),
            repo_root=repo,
        )
        signer_runtime = validate_runtime_root_path(
            config.get("signer_runtime_root"),
            repo_root=repo,
        )
        socket_path = validate_runtime_artifact_path(
            config.get("socket_path"),
            repo_root=repo,
            allowed_root=configured_runtime,
        )
        anchor_path = validate_runtime_artifact_path(
            config.get("control_loop_anchor_path"),
            repo_root=repo,
            allowed_root=signer_runtime,
        )
    except (TypeError, ValueError):
        return ["signer_runtime_path_invalid"]
    roots_overlap = (
        signer_runtime == configured_runtime
        or configured_runtime in signer_runtime.parents
        or signer_runtime in configured_runtime.parents
    )
    if configured_runtime != runtime or roots_overlap:
        reasons.append("signer_runtime_root_binding_invalid")
    if socket_path != runtime / "reddog_signer.sock":
        reasons.append("signer_socket_path_invalid")
    if anchor_path.parent != signer_runtime:
        reasons.append("signer_control_loop_anchor_path_invalid")
    return reasons


def _signer_control_policy_reasons(
    profile: Mapping[str, Any],
    config: Mapping[str, Any],
) -> list[str]:
    policy = config.get("control_loop_authority_policy")
    if not isinstance(policy, Mapping):
        return ["signer_control_loop_authority_policy_invalid"]
    expected = {
        "issuer_principal_id": profile.get("principal_id"),
        "signer_public_key": profile.get("reddog_public_key"),
        "key_epoch": profile.get("key_epoch"),
        "consensus_receipt_digest": profile.get("consensus_receipt_digest"),
        "authority_profile_digest": _digest(profile),
        "authority_profile_source_receipt_id": profile.get(
            "authority_profile_source_receipt_id"
        ),
    }
    if set(policy) != set(expected):
        return ["signer_control_loop_authority_policy_field_set_invalid"]
    if any(policy.get(key) != value for key, value in expected.items()):
        return ["signer_control_loop_authority_policy_binding_mismatch"]
    return []


def _signer_packet_reasons(
    repo: Path, runtime: Path, config: Mapping[str, Any], packet: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if set(packet) != _RUN_PACKET_FIELDS:
        reasons.append("signer_run_packet_field_set_invalid")
    if _forbidden_serialized_keys(packet):
        reasons.append("signer_run_packet_forbidden_key_present")
    checks = {
        "schema_version": "reddog_signer_service_run_packet.v1",
        "run_mode": "signer_owned_cli_sidecar",
        "repo_root": str(repo),
        "working_directory": str(repo),
        "config_path": str((runtime / "signer_service_config.json").resolve()),
        "config_digest": _digest(config),
        "socket_path": str((runtime / "reddog_signer.sock").resolve()),
        "provider_mode": "WSP71_PERMISSIONED",
        "process_owner_requirement": "distinct_signer_os_principal",
        "redDog_must_not_spawn": True,
        "main_py_must_not_spawn": True,
        "shell_required": False,
        "shell_command": None,
        "no_secret_values_in_packet": True,
    }
    for field, expected in checks.items():
        if packet.get(field) != expected:
            reasons.append(f"signer_run_packet_binding_mismatch:{field}")
    body = dict(packet)
    run_packet_id = body.pop("run_packet_id", None)
    if run_packet_id != _digest(body):
        reasons.append("signer_run_packet_id_invalid")
    return reasons


def _forbidden_serialized_keys(payload: Any) -> tuple[str, ...]:
    found: list[str] = []

    def walk(value: Any, prefix: str) -> None:
        if isinstance(value, Mapping):
            for raw_key, child in value.items():
                key = str(raw_key).strip().lower().replace("-", "_")
                location = f"{prefix}.{key}" if prefix else key
                allowed_reference = key in {
                    "signing_key_ref",
                    "audit_mac_key_ref",
                    "no_secret_values_in_packet",
                }
                forbidden = (
                    key == "token"
                    or "password" in key
                    or "secret" in key
                    or "private_key" in key
                    or "access_token" in key
                    or "refresh_token" in key
                    or "sovereign_token" in key
                )
                if forbidden and not allowed_reference:
                    found.append(location)
                walk(child, location)
        elif isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                walk(child, f"{prefix}[{index}]")

    walk(payload, "")
    return tuple(found)


def _validate_resolver_schemas(
    permissions: Mapping[str, Any], principals: Mapping[str, Any],
    reasons: dict[str, list[str]],
) -> None:
    schema = "reddog_authority_runtime_resolver_supply.v1"
    snapshots = permissions.get("snapshots")
    records = principals.get("principals")
    if permissions.get("schema_version") != schema or not isinstance(snapshots, Mapping):
        reasons["permission_snapshots.json"].append("permission_store_schema_invalid")
    elif permissions.get("snapshot_count") != len(snapshots):
        reasons["permission_snapshots.json"].append("permission_store_count_invalid")
    if principals.get("schema_version") != schema or not isinstance(records, Mapping):
        reasons["principal_authority_records.json"].append("principal_store_schema_invalid")
    elif principals.get("principal_count") != len(records):
        reasons["principal_authority_records.json"].append("principal_store_count_invalid")


def _freshness_reasons(
    profile: Mapping[str, Any], permissions: Mapping[str, Any], now: int,
    reasons: dict[str, list[str]],
) -> None:
    try:
        if int(profile["identity_expires_at"]) <= now or int(profile["work_authority_expires_at"]) <= now:
            reasons["authority_profile.json"].append("authority_profile_expired")
        snapshot = permissions["snapshots"][profile["permission_snapshot_digest"]]
        if int(snapshot["expires_at"]) <= now:
            reasons["permission_snapshots.json"].append("permission_snapshot_expired")
    except Exception:
        reasons["authority_profile.json"].append("authority_freshness_invalid")


def _work_state_revision_valid(work: Mapping[str, Any]) -> bool:
    revision = str(work.get("revision") or "")
    body = dict(work)
    body.pop("revision", None)
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return revision == hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _reason_artifact(reason: str) -> str:
    if reason.startswith(("permission_", "resolver_")):
        return "permission_snapshots.json"
    if reason.startswith("principal_"):
        return "principal_authority_records.json"
    if reason.startswith("authority_"):
        return "authority_profile.json"
    return "authoritative_work_state.json"


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _inside(child: Path, parent: Path) -> bool:
    return child == parent or parent in child.parents


def _text(value: Any) -> str:
    return str(value or "").strip()


__all__ = [
    "REQUIRED_RUNTIME_ARTIFACTS", "ResidentRuntimeArtifactReadiness",
    "RuntimeArtifactSemanticCheck", "validate_reddog_resident_runtime_artifacts",
]
