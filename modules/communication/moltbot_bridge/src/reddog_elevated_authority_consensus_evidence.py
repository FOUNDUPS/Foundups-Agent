"""Shared authority and reviewer evidence verification for elevated consensus."""

from __future__ import annotations

from typing import Any

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_contract import (
    CONSENSUS_SCHEMA_VERSION,
    EFFECT_TARGET_BINDING_SCHEMA_VERSION,
    ElevatedAuthorityConsensusReceipt,
    canonical_authority_request_digest,
    canonical_consensus_receipt_digest,
    canonical_json_digest,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_policy import (
    AuthorRuntimeEvidence,
    SovereignAuthorizationEvidence,
    elevated_consensus_policy_valid,
)
from modules.communication.moltbot_bridge.src.reddog_signer_optional_authority_bindings import (
    is_sha256_digest,
)


def author_runtime_evidence_matches(
    evidence: object, request: Any, now: int
) -> bool:
    if type(evidence) is not AuthorRuntimeEvidence or evidence.expires_at <= now:
        return False
    required_ids = (
        request.model_selection_receipt_id,
        request.model_runtime_binding_receipt_id,
        request.model_runtime_binding_verification_receipt_id,
    )
    required_digests = (
        request.model_selection_digest,
        request.model_runtime_binding_digest,
        request.model_runtime_binding_verification_digest,
    )
    if not all(type(value) is str and value for value in required_ids):
        return False
    if not all(is_sha256_digest(value) for value in required_digests):
        return False
    if not str(required_ids[1]).startswith("reddog_model_runtime_binding:"):
        return False
    if not str(required_ids[2]).startswith("model_runtime_binding_verification:"):
        return False
    expected = (
        (evidence.model_selection_receipt_id, request.model_selection_receipt_id),
        (evidence.model_selection_digest, request.model_selection_digest),
        (
            evidence.model_runtime_binding_receipt_id,
            request.model_runtime_binding_receipt_id,
        ),
        (evidence.model_runtime_binding_digest, request.model_runtime_binding_digest),
        (
            evidence.verification_receipt_id,
            request.model_runtime_binding_verification_receipt_id,
        ),
        (
            evidence.verification_digest,
            request.model_runtime_binding_verification_digest,
        ),
    )
    return all(left == right for left, right in expected)


def consensus_receipt_matches(
    receipt: ElevatedAuthorityConsensusReceipt,
    request: Any,
    request_digest: str,
    policy: Any,
    sovereign: Any,
    now: int,
) -> bool:
    if not elevated_consensus_policy_valid(policy):
        return False
    if type(sovereign) is not SovereignAuthorizationEvidence:
        return False
    context = receipt.context
    expected_roles = tuple(dict.fromkeys(policy.required_roles))
    membership = set(policy.reviewer_membership)
    return all(
        (
            receipt.schema_version == CONSENSUS_SCHEMA_VERSION,
            receipt.receipt_id == canonical_consensus_receipt_digest(receipt),
            str(getattr(request, "consensus_receipt_digest", "") or "")
            == receipt.receipt_id,
            context.schema_version == CONSENSUS_SCHEMA_VERSION,
            context.authority_request_digest == request_digest,
            context.consensus_policy_digest == policy.policy_digest,
            context.sovereign_authorization_digest
            == str(getattr(request, "sovereign_authorization_digest", "") or ""),
            _sovereign_matches(sovereign, request, request_digest, now),
            context.required_approvals == policy.minimum_approvals,
            context.required_roles == expected_roles,
            len(membership) == len(policy.reviewer_membership),
            all(role in expected_roles for _, _, role in membership),
            len(receipt.decisions) >= policy.minimum_approvals,
            context.issued_at <= now + policy.maximum_future_skew_seconds,
            context.expires_at > now,
            0 < context.expires_at - context.issued_at
            <= policy.maximum_ttl_seconds,
        )
    )


def _sovereign_matches(evidence: Any, request: Any, digest: str, now: int) -> bool:
    expected = (
        (evidence.authorization_digest, request.sovereign_authorization_digest),
        (evidence.authority_request_digest, digest),
        (evidence.principal_id, request.principal_id),
        (evidence.principal_provider, request.principal_provider),
        (evidence.principal_public_key, request.principal_public_key),
        (evidence.reddog_id, request.reddog_id),
        (evidence.reddog_public_key, request.reddog_public_key),
        (evidence.repo_full_name, request.repo_full_name),
        (evidence.foundup_id, request.foundup_id),
        (evidence.work_order_id, request.work_order_id),
        (evidence.key_epoch, request.key_epoch),
    )
    return evidence.expires_at > now and all(left == right for left, right in expected)


def build_effect_target_binding(*, parent, target, expected_target, now) -> dict[str, str] | None:
    """Correlate pure HIGH/worktree data; authenticate neither parent nor target."""
    from .reddog_signer_delegated_authority_runtime import (
        DelegatedAuthorityRuntimeRequest, SigningRequest, delegated_authority_tier,
    )
    from .reddog_authoritative_use_lease_contract import validate_authoritative_use_lease_request
    from .reddog_signer_secret_access_grant_contract import signer_secret_access_request_digest

    try:
        if (type(parent) is not DelegatedAuthorityRuntimeRequest or type(target) is not SigningRequest
                or type(expected_target) is not dict or type(now) is not int):
            return None
        if parent.requested_operation != "worktree_create" or delegated_authority_tier(parent) != "HIGH":
            return None
        times = (parent.issued_at, parent.identity_expires_at, parent.work_authority_expires_at)
        if not all(type(value) is int for value in times) or not times[0] <= now < min(times[1:]):
            return None
        if target.authority_tier != "HIGH" or target.elevated_consensus_proof is not None:
            return None
        target_payload = target.to_dict()
        if "elevated_consensus_proof" in target_payload:
            return None
        payload = validate_authoritative_use_lease_request(target, now_epoch=now)
        if payload is None or payload["effect_kind"] != "worktree_create":
            return None
        effect = payload["effect_payload"]
        if (effect["work_order_id"] != parent.work_order_id
                or effect["work_order_digest"] != parent.work_order_digest
                or payload["expires_at"] > min(times[1:])):
            return None
        if canonical_json_digest(target_payload) != canonical_json_digest(expected_target):
            return None
        return {
            "schema_version": EFFECT_TARGET_BINDING_SCHEMA_VERSION,
            "parent_authority_request_digest": canonical_authority_request_digest(parent),
            "target_signing_request_digest": signer_secret_access_request_digest(target_payload),
            "effect_request_digest": payload["effect_request_digest"],
        }
    except Exception:
        return None


def effect_target_binding_matches(binding, *, parent, target, expected_target, now) -> bool:
    """Recompute all binding fields; supplied digests confer no authority."""
    if type(binding) is not dict or not all(type(value) is str for value in binding.values()):
        return False
    expected = build_effect_target_binding(
        parent=parent, target=target, expected_target=expected_target, now=now,
    )
    return expected is not None and binding == expected


__all__ = [
    "author_runtime_evidence_matches", "consensus_receipt_matches",
    "build_effect_target_binding", "effect_target_binding_matches",
]
