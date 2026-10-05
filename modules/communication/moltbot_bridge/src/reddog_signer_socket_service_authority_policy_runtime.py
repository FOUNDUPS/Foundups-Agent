"""Existing control-loop and outcome policy composition for signer runtime."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VerifiedOutcomeSignerPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    ControlLoopAuthorityPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_control_loop_anchor import (
    AtomicSignerControlLoopAnchorStore,
    ControlLoopAnchorStore,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    ArchitectProposalPolicyAuthorization, ArchitectProposalSignerPolicy,
    DEFAULT_PROPOSAL_AUTHENTICITY_MAX_TTL_SECONDS,
    rehydrate_architect_proposal_authenticity_payload,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import PrincipalKeyResolver
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import SignerKeyProviderProfile

FAIL_CONTROL_ANCHOR = "FAIL_SIGNER_RUNTIME_CONTROL_ANCHOR_INVALID"


def control_loop_anchor_store(
    config: Any,
) -> tuple[ControlLoopAnchorStore | None, tuple[str, ...]]:
    if config.control_loop_anchor_path is None:
        return None, ()
    try:
        repo = Path(config.repo_root).resolve()
        runtime = validate_runtime_root_path(config.runtime_root, repo_root=repo)
        signer = validate_runtime_root_path(config.signer_runtime_root, repo_root=repo)
        if signer == runtime or runtime in signer.parents or signer in runtime.parents:
            raise ValueError("signer_runtime_overlap")
        path = validate_runtime_artifact_path(
            config.control_loop_anchor_path, repo_root=repo, allowed_root=signer
        )
        if path.parent != signer:
            raise ValueError("control_anchor_parent")
        return AtomicSignerControlLoopAnchorStore(
            path, runtime_root=signer, repo_root=repo
        ), ()
    except Exception:
        return None, (FAIL_CONTROL_ANCHOR,)


def control_loop_authority_policy(
    value: ControlLoopAuthorityPolicy | Mapping[str, Any] | None,
) -> ControlLoopAuthorityPolicy | None:
    policy = _policy(value, ControlLoopAuthorityPolicy)
    if policy is None:
        return None
    values = (
        policy.issuer_principal_id, policy.signer_public_key, policy.key_epoch,
        policy.consensus_receipt_digest, policy.authority_profile_digest,
        policy.authority_profile_source_receipt_id,
    )
    return policy if all(_ascii(item) for item in values) and all(
        _sha256(item) for item in values[3:]
    ) else None


def verified_outcome_signer_policy(
    value: VerifiedOutcomeSignerPolicy | Mapping[str, Any] | None,
) -> VerifiedOutcomeSignerPolicy | None:
    policy = _policy(value, VerifiedOutcomeSignerPolicy)
    if policy is None:
        return None
    values = (
        policy.issuer_principal_id, policy.reddog_id, policy.signer_public_key,
        policy.key_epoch, policy.authority_tier, policy.consensus_receipt_digest,
    )
    return policy if (
        all(_ascii(item) for item in values)
        and _sha256(policy.consensus_receipt_digest)
        and 0 < policy.max_future_skew_seconds <= 300
    ) else None


def _policy(value: Any, kind: type) -> Any:
    if isinstance(value, kind):
        return value
    if isinstance(value, Mapping):
        try:
            return kind(**dict(value))
        except (TypeError, ValueError):
            return None
    return None


def _ascii(value: Any) -> bool:
    return bool(isinstance(value, str) and value and value.isascii())


def _sha256(value: Any) -> bool:
    return bool(
        isinstance(value, str) and len(value) == 71
        and value.startswith("sha256:")
        and all(char in "0123456789abcdef" for char in value[7:])
    )


def rehydrate_architect_proposal_signer_policy(
    value: ArchitectProposalSignerPolicy | Mapping[str, Any] | None,
) -> ArchitectProposalSignerPolicy | None:
    if isinstance(value, ArchitectProposalSignerPolicy):
        return (
            value
            if 0 < int(value.max_ttl_seconds)
            <= DEFAULT_PROPOSAL_AUTHENTICITY_MAX_TTL_SECONDS
            else None
        )
    if not isinstance(value, Mapping):
        return None
    expected = value.get("expected_payload")
    try:
        payload = rehydrate_architect_proposal_authenticity_payload(
            expected if isinstance(expected, Mapping) else {}
        )
        max_ttl = int(value.get("max_ttl_seconds"))
    except (TypeError, ValueError):
        return None
    if not 0 < max_ttl <= DEFAULT_PROPOSAL_AUTHENTICITY_MAX_TTL_SECONDS:
        return None
    return ArchitectProposalSignerPolicy(payload, max_ttl)


def _proposal_policy_authorization(
    config: Any,
    *,
    principal_key_resolver: PrincipalKeyResolver | None,
    require_trusted_principal: bool,
) -> ArchitectProposalPolicyAuthorization | None:
    try:
        from modules.communication.moltbot_bridge.src.reddog_architect_proposal_runtime_authorization import (
            verify_architect_proposal_runtime_authorization,
        )

        _, verified = verify_architect_proposal_runtime_authorization(
            config,
            principal_key_resolver=principal_key_resolver,
            now_epoch=int(time.time()),
            require_trusted_principal=require_trusted_principal,
        )
        return verified
    except (OSError, TypeError, ValueError):
        return None


def _is_proposal_signer_profile(
    profile: SignerKeyProviderProfile,
    policy: ArchitectProposalSignerPolicy | None,
) -> bool:
    return bool(
        policy is not None
        and profile.signer_profile_id
        == "reddog-work-authority"
        and profile.signer_agent_id
        == "signer:reddog"
        and profile.expected_public_key
        == policy.expected_payload.signer_public_key
        and profile.expected_key_epoch == policy.expected_payload.key_epoch
    )


__all__ = [
    "FAIL_CONTROL_ANCHOR", "control_loop_anchor_store",
    "control_loop_authority_policy", "verified_outcome_signer_policy",
]
