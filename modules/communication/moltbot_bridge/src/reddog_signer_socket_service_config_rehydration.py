"""Strict rehydration for manifest-bound RedDog signer service config."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
    SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    SignerSocketServiceRuntimeWiringConfig,
    architect_proposal_security_context_digest,
    validate_signer_socket_service_runtime_config,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


def rehydrate_signer_socket_service_runtime_config(
    repo_root: Path,
    expected_runtime_root: Path,
    payload: dict[str, Any],
    *,
    expected_config_digest: str | None = None,
) -> SignerSocketServiceRuntimeWiringConfig | None:
    """Return one strict typed config or fail closed."""

    try:
        if not _header_valid(payload, expected_config_digest):
            return None
        roots = _runtime_paths(repo_root, expected_runtime_root, payload)
        if roots is None:
            return None
        runtime_root, signer_root, socket_path, control_anchor = roots
        conversation = _conversation_inputs(
            repo_root, signer_root, payload
        )
        proposal = _proposal_inputs(repo_root, signer_root, payload)
        profiles = _profile_inputs(payload)
        if conversation is None or proposal is None or profiles is None:
            return None
        config = _config(
            repo_root,
            payload,
            runtime_root,
            signer_root,
            socket_path,
            control_anchor,
            conversation,
            proposal,
            profiles,
        )
        if config.proposal_authority_policy is not None:
            config = replace(
                config,
                proposal_security_context_digest=(
                    architect_proposal_security_context_digest(config)
                ),
            )
    except Exception:
        return None
    return None if validate_signer_socket_service_runtime_config(config) else config


def _header_valid(
    payload: Mapping[str, Any], expected_digest: str | None
) -> bool:
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    actual = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    proposal = payload.get("proposal_authority_policy") is not None
    return bool(
        payload.get("schema_version") == SIGNER_SERVICE_CONFIG_SCHEMA_VERSION
        and payload.get("control_loop_anchor_path")
        and (
            isinstance(payload.get("control_loop_authority_policy"), dict)
            or proposal
        )
        and (
            not proposal
            or (
                expected_digest is not None
                and hmac.compare_digest(expected_digest, actual)
            )
        )
    )


def _runtime_paths(
    repo: Path, expected: Path, payload: Mapping[str, Any]
) -> tuple[Path, Path, Path, Path] | None:
    runtime = validate_runtime_root_path(payload["runtime_root"], repo_root=repo)
    signer = validate_runtime_root_path(
        payload["signer_runtime_root"], repo_root=repo
    )
    if (
        runtime != expected.resolve()
        or signer == runtime
        or runtime in signer.parents
        or signer in runtime.parents
    ):
        return None
    socket_path = validate_runtime_artifact_path(
        payload["socket_path"], repo_root=repo, allowed_root=runtime
    )
    anchor = validate_runtime_artifact_path(
        payload["control_loop_anchor_path"],
        repo_root=repo,
        allowed_root=signer,
    )
    if socket_path.parent != runtime or anchor.parent != signer:
        return None
    return runtime, signer, socket_path, anchor


def _conversation_inputs(
    repo: Path, signer: Path, payload: Mapping[str, Any]
) -> tuple[Path | None, Mapping[str, Any] | None] | None:
    policy = payload.get("conversation_scope_signer_policy")
    raw_path = payload.get("conversation_scope_anchor_path")
    if (policy is None) != (raw_path is None):
        return None
    if policy is None:
        return None, None
    if not isinstance(policy, Mapping):
        return None
    path = validate_runtime_artifact_path(
        raw_path, repo_root=repo, allowed_root=signer
    )
    return (path, dict(policy)) if path.parent == signer else None


def _proposal_inputs(
    repo: Path, signer: Path, payload: Mapping[str, Any]
) -> tuple[Any, Any, Path | None, str | None, str | None] | None:
    policy = payload.get("proposal_authority_policy")
    authorization = payload.get("proposal_policy_authorization")
    raw_path = payload.get("proposal_nonce_store_path")
    store_id = payload.get("proposal_replay_high_water_store_id")
    durability = payload.get(
        "proposal_replay_high_water_durability_receipt_id"
    )
    values = (policy, authorization, raw_path, store_id, durability)
    if len({value is None for value in values}) != 1:
        return None
    if policy is None:
        return None, None, None, None, None
    if not isinstance(policy, Mapping) or not isinstance(authorization, Mapping):
        return None
    path = validate_runtime_artifact_path(
        raw_path, repo_root=repo, allowed_root=signer
    )
    if (
        path.parent != signer
        or not isinstance(store_id, str)
        or not store_id.strip()
        or not store_id.isascii()
        or not _sha256(durability)
    ):
        return None
    return dict(policy), dict(authorization), path, store_id, str(durability)


def _profile_inputs(
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, tuple[dict[str, Any], ...], dict[str, Any]] | None:
    peer = payload.get("peer_policy")
    profile = payload.get("key_provider_profile")
    profiles = payload.get("key_provider_profiles") or ()
    if not isinstance(peer, dict) or (profile is not None and profiles):
        return None
    if profile is not None and not isinstance(profile, dict):
        return None
    if profiles and (
        not isinstance(profiles, list)
        or not all(isinstance(item, dict) for item in profiles)
    ):
        return None
    normalized = tuple(dict(item) for item in profiles)
    if profile is None and not normalized:
        return None
    return profile, normalized, peer


def _config(
    repo: Path, payload: Mapping[str, Any], runtime: Path, signer: Path,
    socket_path: Path, control_anchor: Path,
    conversation: tuple[Path | None, Mapping[str, Any] | None],
    proposal: tuple[Any, Any, Path | None, str | None, str | None],
    profiles: tuple[dict[str, Any] | None, tuple[dict[str, Any], ...], dict[str, Any]],
) -> SignerSocketServiceRuntimeWiringConfig:
    conversation_path, conversation_policy = conversation
    proposal_policy, authorization, nonce_path, store_id, durability = proposal
    profile, profile_values, peer = profiles
    return SignerSocketServiceRuntimeWiringConfig(
        repo_root=repo, runtime_root=runtime, signer_runtime_root=signer,
        socket_path=socket_path, peer_policy=peer,
        key_provider_profile=profile, key_provider_profiles=profile_values,
        provider_mode=str(payload.get("provider_mode") or ""),
        allow_test_only_key_material=payload.get("allow_test_only_key_material") is True,
        permission_snapshot_fresh=payload.get("permission_snapshot_fresh") is True,
        max_requests=payload.get("max_requests"), timeout_s=payload.get("timeout_s"),
        max_request_bytes=payload.get("max_request_bytes"),
        max_response_bytes=payload.get("max_response_bytes"),
        control_loop_anchor_path=control_anchor,
        control_loop_authority_policy=payload.get("control_loop_authority_policy"),
        conversation_scope_anchor_path=conversation_path,
        conversation_scope_signer_policy=conversation_policy,
        verified_outcome_signer_policy=payload.get("verified_outcome_signer_policy"),
        proposal_authority_policy=proposal_policy,
        proposal_policy_authorization=authorization,
        proposal_nonce_store_path=nonce_path,
        proposal_replay_high_water_store_id=store_id,
        proposal_replay_high_water_durability_receipt_id=durability,
    )


def _sha256(value: object) -> bool:
    text = value if isinstance(value, str) else ""
    return bool(
        len(text) == 71
        and text.startswith("sha256:")
        and all(char in "0123456789abcdef" for char in text[7:])
    )


__all__ = ["rehydrate_signer_socket_service_runtime_config"]
