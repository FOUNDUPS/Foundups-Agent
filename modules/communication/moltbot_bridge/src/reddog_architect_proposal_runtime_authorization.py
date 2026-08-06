"""Verify architect proposal policy against the active isolated-signer context."""

from __future__ import annotations

import hmac
from pathlib import Path
from typing import Mapping

from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    ArchitectProposalPolicyAuthorization,
    ArchitectProposalSignerPolicy,
    architect_proposal_replay_store_binding_digest,
    architect_proposal_signer_instance_id,
    verify_architect_proposal_policy_authorization,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_TEST_ONLY_DRYRUN,
    PROVIDER_MODE_WSP71_PERMISSIONED,
    SignerKeyProviderProfile,
    validate_signer_key_provider_profile,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    REDDOG_WORK_AUTHORITY_SIGNER_AGENT_ID,
    SignerSocketServiceRuntimeWiringConfig,
    architect_proposal_security_context_digest,
    rehydrate_architect_proposal_signer_policy,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PrincipalKeyResolver,
)


def verify_architect_proposal_runtime_authorization(
    config: SignerSocketServiceRuntimeWiringConfig,
    *,
    principal_key_resolver: PrincipalKeyResolver | None,
    now_epoch: int,
    require_trusted_principal: bool = True,
) -> tuple[
    ArchitectProposalSignerPolicy,
    ArchitectProposalPolicyAuthorization,
]:
    """Reconstruct and verify the principal-authorized signer runtime."""

    policy, raw_authorization = _policy_and_authorization(config)
    profile, signer_instance_id, replay_binding, security_digest = (
        _runtime_context(config, policy)
    )
    principal_id = str(raw_authorization.get("principal_id") or "")
    principal_provider = str(raw_authorization.get("principal_provider") or "")
    trusted_key = str(raw_authorization.get("principal_public_key") or "")
    if require_trusted_principal:
        if principal_key_resolver is None:
            raise ValueError("architect_proposal_runtime_principal_untrusted")
        trusted_key = principal_key_resolver.resolve(
            principal_id, principal_provider
        )
    if not trusted_key:
        raise ValueError("architect_proposal_runtime_principal_untrusted")
    authority_profile = {
        "principal_id": policy.expected_payload.requester_principal_id,
        "principal_provider": principal_provider,
        "principal_public_key": str(
            raw_authorization.get("principal_public_key") or ""
        ),
        "reddog_id": policy.expected_payload.reddog_id,
        "reddog_public_key": profile.expected_public_key,
        "key_epoch": profile.expected_key_epoch,
        "authority_profile_source_receipt_id": (
            policy.expected_payload.authority_profile_source_receipt_id
        ),
    }
    verified = verify_architect_proposal_policy_authorization(
        raw_authorization,
        policy=policy,
        authority_profile=authority_profile,
        trusted_principal_public_key=str(trusted_key),
        expected_signer_instance_id=signer_instance_id,
        expected_replay_store_binding_digest=replay_binding,
        expected_security_context_digest=security_digest,
        now_epoch=int(now_epoch),
    )
    return policy, verified


def _policy_and_authorization(
    config: SignerSocketServiceRuntimeWiringConfig,
) -> tuple[ArchitectProposalSignerPolicy, Mapping[str, object]]:
    if not isinstance(config, SignerSocketServiceRuntimeWiringConfig):
        raise ValueError("architect_proposal_runtime_config_invalid")
    valid_mode = (
        config.provider_mode == PROVIDER_MODE_WSP71_PERMISSIONED
        and not config.allow_test_only_key_material
    ) or (
        config.provider_mode == PROVIDER_MODE_TEST_ONLY_DRYRUN
        and config.allow_test_only_key_material
    )
    if not valid_mode or not config.permission_snapshot_fresh:
        raise ValueError("architect_proposal_runtime_not_production")
    try:
        policy = rehydrate_architect_proposal_signer_policy(
            config.proposal_authority_policy
        )
    except (TypeError, ValueError):
        policy = None
    authorization = config.proposal_policy_authorization
    if not isinstance(policy, ArchitectProposalSignerPolicy):
        raise ValueError("architect_proposal_runtime_policy_missing")
    raw = (
        authorization.to_dict()
        if isinstance(authorization, ArchitectProposalPolicyAuthorization)
        else authorization
    )
    if not isinstance(raw, Mapping):
        raise ValueError("architect_proposal_runtime_authorization_missing")
    return policy, raw


def _runtime_context(
    config: SignerSocketServiceRuntimeWiringConfig,
    policy: ArchitectProposalSignerPolicy,
) -> tuple[SignerKeyProviderProfile, str, str, str]:
    profile = _proposal_profile(config, policy)
    signer_root = Path(config.signer_runtime_root).resolve()
    nonce_path = config.proposal_nonce_store_path
    store_id = str(
        config.proposal_replay_high_water_store_id or ""
    ).strip()
    durability = str(
        config.proposal_replay_high_water_durability_receipt_id or ""
    ).strip()
    if nonce_path is None or not store_id or not durability.startswith(
        "sha256:"
    ):
        raise ValueError("architect_proposal_runtime_replay_store_invalid")
    signer_id = architect_proposal_signer_instance_id(
        signer_root, profile.expected_public_key, profile.expected_key_epoch
    )
    replay_binding = architect_proposal_replay_store_binding_digest(
        signer_id, nonce_path, store_id
    )
    security_digest = architect_proposal_security_context_digest(config)
    if not hmac.compare_digest(
        str(config.proposal_security_context_digest or ""), security_digest
    ):
        raise ValueError("architect_proposal_runtime_security_context_invalid")
    return profile, signer_id, replay_binding, security_digest


def _proposal_profile(
    config: SignerSocketServiceRuntimeWiringConfig,
    policy: ArchitectProposalSignerPolicy,
) -> SignerKeyProviderProfile:
    raw_profiles = (
        tuple(config.key_provider_profiles)
        if config.key_provider_profiles
        else (config.key_provider_profile,)
    )
    profiles = [
        profile
        for raw in raw_profiles
        if (profile := _typed_profile(raw)) is not None
        and profile.signer_agent_id == REDDOG_WORK_AUTHORITY_SIGNER_AGENT_ID
        and profile.expected_public_key
        == policy.expected_payload.signer_public_key
        and profile.expected_key_epoch == policy.expected_payload.key_epoch
        and validate_signer_key_provider_profile(profile) is None
    ]
    if len(profiles) != 1:
        raise ValueError("architect_proposal_runtime_profile_invalid")
    return profiles[0]


def _typed_profile(
    value: SignerKeyProviderProfile | Mapping[str, object] | None,
) -> SignerKeyProviderProfile | None:
    if isinstance(value, SignerKeyProviderProfile):
        return value
    if not isinstance(value, Mapping):
        return None
    try:
        return SignerKeyProviderProfile(**dict(value))
    except (TypeError, ValueError):
        return None


__all__ = ["verify_architect_proposal_runtime_authorization"]
