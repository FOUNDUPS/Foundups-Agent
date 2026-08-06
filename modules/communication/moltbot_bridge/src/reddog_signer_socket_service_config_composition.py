"""Validation and canonical composition for signer service config supply."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_publication import (
    architect_fix_committed_publication_reasons,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_records import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    ArchitectProposalPolicyAuthorization,
    ArchitectProposalSignerPolicy,
    DEFAULT_PROPOSAL_AUTHENTICITY_MAX_TTL_SECONDS,
)
from modules.communication.moltbot_bridge.src.reddog_authority_profile_safety import (
    authority_profile_malformed_digest_paths,
    authority_profile_runtime_unknown_field_paths,
    authority_profile_secret_field_paths,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    ConversationScopeSignerPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import (
    validate_resident_signer_socket_limits,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_WSP71_PERMISSIONED,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply_contract import (
    FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID,
    FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID,
    FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID,
    FAIL_SIGNER_CONFIG_LIMITS_INVALID,
    FAIL_SIGNER_CONFIG_OP_REF_INVALID,
    FAIL_SIGNER_CONFIG_OP_REF_REUSED,
    FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID,
    FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID,
    FAIL_SIGNER_CONFIG_PROPOSAL_NONCE_PATH_INVALID,
    FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_INVALID,
    FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID,
    SIGNER_SERVICE_CONFIG_FILENAME,
    SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
    canonical_config_digest,
)
from modules.infrastructure.secrets_mcp.src.vault_resolver import parse_op_reference
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


_REQUIRED_AUTHORITY_FIELDS = (
    "principal_id",
    "principal_provider",
    "principal_public_key",
    "reddog_id",
    "reddog_public_key",
    "permission_snapshot_digest",
    "key_epoch",
    "consensus_receipt_digest",
    "authority_profile_source_receipt_id",
)


@dataclass(frozen=True)
class RuntimeArtifactPaths:
    runtime: Path | None
    signer_runtime: Path | None
    output: Path | None
    socket: Path | None
    anchor: Path | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ConfigInputs:
    authority_profile: Mapping[str, Any]
    runtime_root: Path
    signer_runtime_root: Path
    socket_path: Path
    principal_signing_key_ref: str
    principal_audit_mac_key_ref: str
    reddog_signing_key_ref: str
    reddog_audit_mac_key_ref: str
    peer_policy: Mapping[str, Any]
    max_requests: int
    timeout_s: float
    max_request_bytes: int
    max_response_bytes: int
    principal_signer_agent_id: str
    reddog_signer_agent_id: str
    control_loop_anchor_path: Path
    conversation_scope_anchor_path: Path | None
    conversation_scope_signer_policy: ConversationScopeSignerPolicy | None
    proposal_authority_policy: ArchitectProposalSignerPolicy | None
    proposal_policy_authorization: ArchitectProposalPolicyAuthorization | None
    proposal_nonce_store_path: Path | None
    proposal_replay_high_water_store_id: str | None
    proposal_replay_high_water_durability_receipt_id: str | None


def runtime_artifact_paths(
    repo: Path,
    runtime_value: Path | str,
    signer_value: Path | str,
    output_value: Path | str | None,
    socket_value: Path | str | None,
    anchor_value: Path | str | None,
) -> RuntimeArtifactPaths:
    runtime, runtime_reason = _runtime_root(
        repo, runtime_value, FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID
    )
    signer, signer_reason = _runtime_root(
        repo, signer_value, FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID
    )
    reasons = [reason for reason in (runtime_reason, signer_reason) if reason]
    if _roots_overlap(runtime, signer):
        reasons.append(FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID)
    output, reason = _artifact_path(repo, runtime, output_value, "output")
    reasons.extend(reason)
    socket, reason = _artifact_path(repo, runtime, socket_value, "socket")
    reasons.extend(reason)
    anchor_value = anchor_value or (
        signer / "signer_control_loop_anchor.json" if signer else None
    )
    anchor, reason = _artifact_path(repo, signer, anchor_value, "anchor")
    reasons.extend(reason)
    if output and runtime and output != runtime / SIGNER_SERVICE_CONFIG_FILENAME:
        reasons.append(FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID)
    if output and socket and output == socket:
        reasons.append(FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID)
    return RuntimeArtifactPaths(
        runtime, signer, output, socket, anchor, tuple(reasons)
    )


def _runtime_root(
    repo: Path, value: Path | str, reason: str
) -> tuple[Path | None, str | None]:
    try:
        return validate_runtime_root_path(value, repo_root=repo), None
    except ValueError:
        return None, reason


def _roots_overlap(runtime: Path | None, signer: Path | None) -> bool:
    return bool(
        runtime
        and signer
        and (runtime == signer or runtime in signer.parents or signer in runtime.parents)
    )


def _artifact_path(
    repo: Path,
    root: Path | None,
    value: Path | str | None,
    kind: str,
) -> tuple[Path | None, tuple[str, ...]]:
    reason = {
        "output": FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID,
        "socket": FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID,
        "anchor": FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID,
    }[kind]
    if root is None or not value:
        return None, (reason,)
    try:
        path = validate_runtime_artifact_path(
            value, repo_root=repo, allowed_root=root
        )
    except ValueError:
        return None, (reason,)
    occupied = kind == "socket" and path.exists()
    wrong = path.parent != root or (kind == "output" and path.exists() and not path.is_file())
    if wrong or occupied:
        return None, (reason,)
    return path, ()


def proposal_runtime_inputs(
    repo: Path,
    signer_root: Path | None,
    profile: Mapping[str, Any],
    policy: ArchitectProposalSignerPolicy | None,
    nonce_value: Path | str | None,
    store_id: str | None,
    durability_id: str | None,
    signer_agent_id: str,
) -> tuple[Path | None, str | None, tuple[str, ...]]:
    if policy is None:
        absent = nonce_value is None and store_id is None and durability_id is None
        return None, None, (() if absent else (FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_INVALID,))
    if not _proposal_policy_inputs_valid(
        signer_root, profile, policy, store_id, durability_id, signer_agent_id
    ):
        return None, None, (FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_INVALID,)
    target = _proposal_nonce_path(repo, signer_root, nonce_value)
    if target is None:
        return None, None, (FAIL_SIGNER_CONFIG_PROPOSAL_NONCE_PATH_INVALID,)
    return target, str(store_id).strip(), ()


def _proposal_policy_inputs_valid(
    signer_root: Path | None,
    profile: Mapping[str, Any],
    policy: ArchitectProposalSignerPolicy,
    store_id: str | None,
    durability_id: str | None,
    signer_agent_id: str,
) -> bool:
    from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
        REDDOG_WORK_AUTHORITY_SIGNER_AGENT_ID,
    )

    payload = policy.expected_payload
    ttl = int(payload.expires_at) - int(payload.issued_at)
    return bool(
        signer_root
        and ascii_string(store_id)
        and sha256_digest(durability_id)
        and signer_agent_id == REDDOG_WORK_AUTHORITY_SIGNER_AGENT_ID
        and _proposal_identity_matches(profile, payload)
        and 0 < policy.max_ttl_seconds <= DEFAULT_PROPOSAL_AUTHENTICITY_MAX_TTL_SECONDS
        and 0 < ttl <= int(policy.max_ttl_seconds)
    )


def _proposal_identity_matches(profile: Mapping[str, Any], payload: Any) -> bool:
    expected = (
        ("principal_id", payload.requester_principal_id),
        ("reddog_id", payload.reddog_id),
        ("reddog_public_key", payload.signer_public_key),
        ("key_epoch", payload.key_epoch),
        ("consensus_receipt_digest", payload.consensus_receipt_digest),
        ("authority_profile_source_receipt_id", payload.authority_profile_source_receipt_id),
    )
    return all(str(profile.get(key) or "") == value for key, value in expected)


def _proposal_nonce_path(
    repo: Path, signer_root: Path | None, value: Path | str | None
) -> Path | None:
    if signer_root is None:
        return None
    canonical = signer_root / "architect_proposal_nonce_store.json"
    try:
        target = validate_runtime_artifact_path(
            value or canonical, repo_root=repo, allowed_root=signer_root
        )
    except (OSError, TypeError, ValueError):
        return None
    if target.parent != signer_root or target.resolve() != canonical.resolve():
        return None
    return None if target.exists() and not target.is_file() else target


def config_mapping(**values: Any) -> dict[str, Any]:
    values.setdefault("conversation_scope_anchor_path", None)
    values.setdefault("conversation_scope_signer_policy", None)
    return build_config(ConfigInputs(**values))


def build_config(inputs: ConfigInputs) -> dict[str, Any]:
    config = _base_config(inputs)
    config["key_provider_profiles"] = _key_profiles(inputs)
    config["peer_policy"] = dict(inputs.peer_policy)
    _add_conversation_config(config, inputs)
    _add_proposal_config(config, inputs)
    return config


def _base_config(inputs: ConfigInputs) -> dict[str, Any]:
    profile = inputs.authority_profile
    reddog_public = str(profile["reddog_public_key"])
    key_epoch = str(profile["key_epoch"])
    return {
        "schema_version": SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
        "runtime_root": str(inputs.runtime_root),
        "signer_runtime_root": str(inputs.signer_runtime_root),
        "socket_path": str(inputs.socket_path),
        "control_loop_anchor_path": str(inputs.control_loop_anchor_path),
        "provider_mode": PROVIDER_MODE_WSP71_PERMISSIONED,
        "allow_test_only_key_material": False,
        "permission_snapshot_fresh": True,
        "control_loop_authority_policy": _control_policy(profile, reddog_public, key_epoch),
        "verified_outcome_signer_policy": _outcome_policy(profile, reddog_public, key_epoch),
        "max_requests": int(inputs.max_requests),
        "timeout_s": float(inputs.timeout_s),
        "max_request_bytes": int(inputs.max_request_bytes),
        "max_response_bytes": int(inputs.max_response_bytes),
    }


def _control_policy(
    profile: Mapping[str, Any], public_key: str, key_epoch: str
) -> dict[str, Any]:
    return {
        "issuer_principal_id": str(profile["principal_id"]),
        "signer_public_key": public_key,
        "key_epoch": key_epoch,
        "consensus_receipt_digest": str(profile["consensus_receipt_digest"]),
        "authority_profile_digest": canonical_config_digest(profile),
        "authority_profile_source_receipt_id": str(
            profile["authority_profile_source_receipt_id"]
        ),
    }


def _outcome_policy(
    profile: Mapping[str, Any], public_key: str, key_epoch: str
) -> dict[str, Any]:
    return {
        "issuer_principal_id": str(profile["principal_id"]),
        "reddog_id": str(profile["reddog_id"]),
        "signer_public_key": public_key,
        "key_epoch": key_epoch,
        "authority_tier": "HIGH",
        "consensus_receipt_digest": str(profile["consensus_receipt_digest"]),
        "max_future_skew_seconds": 60,
    }


def _key_profiles(inputs: ConfigInputs) -> list[dict[str, Any]]:
    profile = inputs.authority_profile
    common = {
        "expected_key_epoch": str(profile["key_epoch"]),
        "permission_snapshot_digest": str(profile["permission_snapshot_digest"]),
    }
    principal = _key_profile(
        "principal-identity", inputs.principal_signer_agent_id,
        inputs.principal_signing_key_ref, inputs.principal_audit_mac_key_ref,
        str(profile["principal_public_key"]),
        int(profile.get("identity_ttl_seconds") or 300), common,
    )
    reddog = _key_profile(
        "reddog-work-authority", inputs.reddog_signer_agent_id,
        inputs.reddog_signing_key_ref, inputs.reddog_audit_mac_key_ref,
        str(profile["reddog_public_key"]),
        int(profile.get("work_authority_ttl_seconds") or 300), common,
    )
    return [principal, reddog]


def _key_profile(
    profile_id: str, agent_id: str, key_ref: str, mac_ref: str,
    public_key: str, ttl_seconds: int, common: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "signer_profile_id": profile_id,
        "signer_agent_id": str(agent_id),
        "signing_key_ref": str(key_ref),
        "audit_mac_key_ref": str(mac_ref),
        "expected_public_key": public_key,
        "expected_key_fingerprint": public_key_fingerprint(public_key),
        **dict(common),
        "ttl_seconds": ttl_seconds,
    }


def _add_conversation_config(config: dict[str, Any], inputs: ConfigInputs) -> None:
    policy = inputs.conversation_scope_signer_policy
    if policy is None:
        return
    if inputs.conversation_scope_anchor_path is None:
        raise ValueError("conversation_scope_anchor_required")
    config["conversation_scope_anchor_path"] = str(
        inputs.conversation_scope_anchor_path
    )
    config["conversation_scope_signer_policy"] = asdict(policy)


def _add_proposal_config(config: dict[str, Any], inputs: ConfigInputs) -> None:
    policy = inputs.proposal_authority_policy
    if policy is None:
        return
    if not all((
        inputs.proposal_nonce_store_path,
        inputs.proposal_replay_high_water_store_id,
        inputs.proposal_replay_high_water_durability_receipt_id,
    )):
        raise ValueError("proposal_runtime_binding_required")
    config["key_provider_profiles"] = [config["key_provider_profiles"][1]]
    config.pop("control_loop_authority_policy", None)
    config["proposal_authority_policy"] = {
        "expected_payload": policy.expected_payload.to_dict(),
        "max_ttl_seconds": int(policy.max_ttl_seconds),
    }
    config["proposal_nonce_store_path"] = str(inputs.proposal_nonce_store_path)
    config["proposal_replay_high_water_store_id"] = (
        inputs.proposal_replay_high_water_store_id
    )
    config["proposal_replay_high_water_durability_receipt_id"] = (
        inputs.proposal_replay_high_water_durability_receipt_id
    )
    if inputs.proposal_policy_authorization is not None:
        config["proposal_policy_authorization"] = (
            inputs.proposal_policy_authorization.to_dict()
        )


def conversation_scope_policy(
    profile: Mapping[str, Any],
) -> ConversationScopeSignerPolicy | None:
    values = tuple(
        str(profile.get(field) or "").strip()
        for field in (
            "principal_id", "principal_provider", "repo_full_name",
            "reddog_public_key", "key_epoch",
        )
    )
    if any(not value or not value.isascii() for value in values) or "/" not in values[2]:
        return None
    ttl = int(profile.get("identity_ttl_seconds") or 300)
    if not 0 < ttl <= 86400:
        return None
    return ConversationScopeSignerPolicy(
        issuer_principal_id=values[0], issuer_principal_provider=values[1],
        repo_full_name=values[2], signer_public_key=values[3],
        key_epoch=values[4], max_scope_ttl_seconds=ttl,
    )


def authority_profile_reasons(
    profile: Mapping[str, Any], *, require_principal_provider: bool
) -> tuple[str, ...]:
    if not profile or not ascii_deep(profile):
        return (FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID,)
    unsafe_paths = (
        tuple(authority_profile_secret_field_paths(profile))
        + tuple(authority_profile_runtime_unknown_field_paths(profile))
        + tuple(authority_profile_malformed_digest_paths(profile))
    )
    if unsafe_paths:
        return tuple(
            FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID + ":" + path
            for path in unsafe_paths
        )
    required = tuple(
        field for field in _REQUIRED_AUTHORITY_FIELDS
        if require_principal_provider or field != "principal_provider"
    )
    missing = tuple(field for field in required if not str(profile.get(field) or ""))
    if missing:
        return tuple(
            FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID + ":" + field
            for field in missing
        )
    if str(profile.get("principal_public_key")) == str(profile.get("reddog_public_key")):
        return (FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID + ":key_reuse",)
    digests = (
        "permission_snapshot_digest", "consensus_receipt_digest",
        "authority_profile_source_receipt_id",
    )
    invalid = tuple(field for field in digests if not sha256_digest(profile.get(field)))
    return tuple(
        FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID + ":" + field
        for field in invalid
    )


def architect_publication_reasons(
    profile: Mapping[str, Any],
    supplied_state: Mapping[str, Any] | None,
    runtime_root: Path | None,
    state_path: Path | str | None,
) -> tuple[str, ...]:
    durable = _read_work_state(runtime_root, state_path)
    if durable is None:
        return (FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID,)
    if isinstance(supplied_state, Mapping) and canonical_digest(supplied_state) != canonical_digest(durable):
        return (FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID,)
    binding = profile.get("operational_context_binding")
    binding = binding if isinstance(binding, Mapping) else {}
    reasons = architect_fix_committed_publication_reasons(
        durable, profile, queue_item_id=str(binding.get("queue_item_id") or ""),
        claim_id=str(binding.get("claim_id") or ""),
    )
    return () if not reasons else (FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID,)


def _read_work_state(
    runtime_root: Path | None, state_path: Path | str | None
) -> Mapping[str, Any] | None:
    if runtime_root is None or not state_path:
        return None
    try:
        return read_reddog_runtime_json_mapping(
            state_path, allowed_root=runtime_root
        )
    except Exception:
        return None


def op_ref_reasons(values: Sequence[str]) -> tuple[str, ...]:
    refs = tuple(str(value or "").strip() for value in values)
    reasons = [FAIL_SIGNER_CONFIG_OP_REF_INVALID for ref in refs if not parse_op_reference(ref)]
    if len(set(refs)) != len(refs):
        reasons.append(FAIL_SIGNER_CONFIG_OP_REF_REUSED)
    return tuple(reasons)


def peer_policy(
    uid_to_principal: Mapping[int | str, str], allowed_gids: Sequence[int | str]
) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    try:
        uid_map = {int(uid): str(value) for uid, value in uid_to_principal.items()}
        gids = tuple(int(gid) for gid in allowed_gids)
    except Exception:
        return None, (FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID,)
    invalid = (
        not uid_map or any(uid < 0 for uid in uid_map)
        or any(gid < 0 for gid in gids)
        or any(not value or not ascii_string(value) for value in uid_map.values())
    )
    if invalid:
        return None, (FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID,)
    return {
        "uid_to_principal": {
            str(uid): value for uid, value in sorted(uid_map.items())
        },
        "allowed_gids": list(gids),
        "transport": "unix_socket",
        "credential_source_prefix": "kernel_peer_credential",
    }, ()


def limit_reasons(
    max_requests: int, timeout_s: float,
    max_request_bytes: int, max_response_bytes: int,
) -> tuple[str, ...]:
    reasons = validate_resident_signer_socket_limits(
        max_requests=max_requests, timeout_s=timeout_s,
        max_request_bytes=max_request_bytes, max_response_bytes=max_response_bytes,
    )
    invalid = reasons or type(max_requests) is not int or max_requests < 2
    return (FAIL_SIGNER_CONFIG_LIMITS_INVALID,) if invalid else ()


def sha256_digest(value: object) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


def ascii_string(value: object) -> bool:
    return isinstance(value, str) and all(ord(char) < 128 for char in value)


def ascii_deep(value: object) -> bool:
    if isinstance(value, str):
        return value.isascii()
    if isinstance(value, Mapping):
        return all(ascii_deep(key) and ascii_deep(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(ascii_deep(item) for item in value)
    return value is None or isinstance(value, (bool, int, float))


__all__ = [
    "ConfigInputs", "RuntimeArtifactPaths", "architect_publication_reasons",
    "authority_profile_reasons", "config_mapping", "conversation_scope_policy",
    "limit_reasons", "op_ref_reasons", "peer_policy", "proposal_runtime_inputs",
    "runtime_artifact_paths",
]
