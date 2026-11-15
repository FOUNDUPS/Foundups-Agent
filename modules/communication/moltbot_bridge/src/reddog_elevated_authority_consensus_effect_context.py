"""Inert effect-approval context data; parsing never authenticates approval."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from .reddog_elevated_authority_consensus_contract import (
    EFFECT_TARGET_BINDING_SCHEMA_VERSION,
)
from .reddog_elevated_authority_consensus_rehydration import (
    MAX_CONSENSUS_DECISIONS,
    MAX_CONSENSUS_RECEIPT_BYTES,
)
from .reddog_signer_optional_authority_bindings import is_sha256_digest


EFFECT_APPROVAL_CONTEXT_SCHEMA_VERSION = "reddog_effect_approval_context.v1"
EFFECT_APPROVAL_CONTEXT_PREFIX = b"reddog-effect-approval-context.v1."
MAX_EFFECT_CONTEXT_TEXT_CHARS = 256
_DIGEST_FIELDS = (
    "parent_authority_request_digest", "target_signing_request_digest",
    "effect_request_digest", "sovereign_authorization_digest",
    "consensus_policy_digest",
)


@dataclass(frozen=True, slots=True)
class EffectApprovalContext:
    """Untrusted assertions; neither this type nor its digest grants authority."""

    schema_version: str
    binding_schema_version: str
    parent_authority_request_digest: str
    target_signing_request_digest: str
    effect_request_digest: str
    sovereign_authorization_digest: str
    consensus_policy_digest: str
    required_approvals: int
    required_roles: tuple[str, ...]
    nonce: str
    issued_at: int
    expires_at: int

    def to_dict(self) -> dict:
        payload = {name: getattr(self, name) for name in self.__dataclass_fields__}
        payload["required_roles"] = list(self.required_roles)
        return payload


def rehydrate_effect_approval_context(value: object) -> EffectApprovalContext:
    """Decode exact bounded data, without checking provenance, clock or scope."""
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise ValueError("effect_approval_context_schema_invalid")
    if set(value) != set(EffectApprovalContext.__dataclass_fields__):
        raise ValueError("effect_approval_context_schema_invalid")
    versions = (
        ("schema_version", EFFECT_APPROVAL_CONTEXT_SCHEMA_VERSION),
        ("binding_schema_version", EFFECT_TARGET_BINDING_SCHEMA_VERSION),
    )
    if any(type(value[key]) is not str or value[key] != version for key, version in versions):
        raise ValueError("effect_approval_context_domain_invalid")
    if any(type(value[key]) is not str or not is_sha256_digest(value[key]) for key in _DIGEST_FIELDS):
        raise ValueError("effect_approval_context_digest_invalid")
    _validate_assertions(value)
    _canonical_wire_bytes(value)
    return EffectApprovalContext(**{**value, "required_roles": tuple(value["required_roles"])})


def _validate_assertions(value: dict) -> None:
    roles = value["required_roles"]
    if (type(roles) is not list or not 1 <= len(roles) <= MAX_CONSENSUS_DECISIONS
            or any(not _bounded_text(role) for role in roles)
            or len(set(roles)) != len(roles)):
        raise ValueError("effect_approval_context_roles_invalid")
    approvals = value["required_approvals"]
    if type(approvals) is not int or not 1 <= approvals <= MAX_CONSENSUS_DECISIONS:
        raise ValueError("effect_approval_context_approvals_invalid")
    if not _bounded_text(value["nonce"]):
        raise ValueError("effect_approval_context_nonce_invalid")
    issued, expires = value["issued_at"], value["expires_at"]
    if type(issued) is not int or type(expires) is not int or not 0 <= issued < expires:
        raise ValueError("effect_approval_context_times_invalid")


def _bounded_text(value: object) -> bool:
    return (type(value) is str and value.isascii()
            and 1 <= len(value) <= MAX_EFFECT_CONTEXT_TEXT_CHARS)


def _canonical_wire_bytes(value: dict) -> bytes:
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("effect_approval_context_encoding_invalid") from exc
    if len(encoded) > MAX_CONSENSUS_RECEIPT_BYTES:
        raise ValueError("effect_approval_context_size_invalid")
    return encoded


def canonical_effect_approval_context_bytes(context: EffectApprovalContext) -> bytes:
    """Encode a validated data context in its distinct domain, without signing."""
    if type(context) is not EffectApprovalContext or type(context.required_roles) is not tuple:
        raise ValueError("effect_approval_context_type_invalid")
    payload = context.to_dict()
    rehydrate_effect_approval_context(payload)
    return EFFECT_APPROVAL_CONTEXT_PREFIX + _canonical_wire_bytes(payload)


def canonical_effect_approval_context_digest(context: EffectApprovalContext) -> str:
    """Hash exact domain-separated bytes; the digest is not a verified receipt."""
    return "sha256:" + hashlib.sha256(canonical_effect_approval_context_bytes(context)).hexdigest()


def effect_approval_context_matches(context, *, parent, target, expected_target, now) -> bool:
    """Check current structural correlation only; authenticate no approval."""
    from .reddog_elevated_authority_consensus_evidence import effect_target_binding_matches
    from .reddog_authoritative_use_lease_contract import validate_authoritative_use_lease_request

    try:
        canonical_effect_approval_context_bytes(context)
        if type(now) is not int or not context.issued_at <= now < context.expires_at:
            return False
        binding = {
            "schema_version": context.binding_schema_version,
            "parent_authority_request_digest": context.parent_authority_request_digest,
            "target_signing_request_digest": context.target_signing_request_digest,
            "effect_request_digest": context.effect_request_digest,
        }
        if not effect_target_binding_matches(
            binding, parent=parent, target=target, expected_target=expected_target, now=now,
        ):
            return False
        payload = validate_authoritative_use_lease_request(target, now_epoch=now)
        return payload is not None and context.expires_at <= payload["expires_at"]
    except Exception:
        return False


def _effect_review_set_preflight(decisions, context, parent, target, expected_target, policy, now):
    """Freeze bounded wire assertions before consulting evidence resolvers."""
    from .reddog_elevated_authority_consensus_contract import APPROVE
    from .reddog_elevated_authority_consensus_policy import _effect_policy_matches
    from .reddog_elevated_authority_consensus_rehydration import rehydrate_effect_reviewer_decision
    from .reddog_elevated_authority_consensus_reviewer_evidence import (
        _forbidden_reviewer_ids, _reviewer_membership,
    )

    if type(decisions) not in (list, tuple) or not 1 <= len(decisions) <= MAX_CONSENSUS_DECISIONS:
        raise ValueError("effect_review_set_count_invalid")
    reviews = tuple(rehydrate_effect_reviewer_decision(item) for item in decisions)
    _canonical_wire_bytes({"decisions": [review.to_dict() for review in reviews]})
    if (not effect_approval_context_matches(
            context, parent=parent, target=target, expected_target=expected_target, now=now,
        ) or not _effect_policy_matches(context, policy)
            or len(reviews) < policy.minimum_approvals):
        raise ValueError("effect_review_set_context_invalid")
    digest = canonical_effect_approval_context_digest(context)
    forbidden_ids = _forbidden_reviewer_ids(parent)
    forbidden_keys = {parent.principal_public_key, parent.reddog_public_key}
    if any(
        review.consensus_context_digest != digest or review.decision != APPROVE
        or _reviewer_membership(review) not in policy.reviewer_membership
        or review.reviewer_principal_id in forbidden_ids
        or review.reviewer_public_key in forbidden_keys
        or review.model_runtime_binding_digest == parent.model_runtime_binding_digest
        for review in reviews
    ):
        raise ValueError("effect_review_set_membership_invalid")
    return reviews, digest


__all__ = [
    "EffectApprovalContext", "rehydrate_effect_approval_context",
    "canonical_effect_approval_context_bytes", "canonical_effect_approval_context_digest",
    "effect_approval_context_matches",
]
