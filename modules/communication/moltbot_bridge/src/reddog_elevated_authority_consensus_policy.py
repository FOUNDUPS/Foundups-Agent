"""Authoritative policy and evidence bindings for elevated consensus."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_contract import (
    canonical_json_digest,
)


@dataclass(frozen=True, slots=True)
class ReviewerRuntimeEvidence:
    reviewer_model_id: str
    model_selection_receipt_id: str
    model_selection_digest: str
    model_runtime_binding_receipt_id: str
    model_runtime_binding_digest: str
    expires_at: int


class ReviewerRuntimeEvidenceResolver(Protocol):
    def resolve(
        self,
        reviewer_principal_id: str,
        model_selection_receipt_id: str,
        model_runtime_binding_receipt_id: str,
    ) -> ReviewerRuntimeEvidence | None: ...


@dataclass(frozen=True, slots=True)
class AuthorRuntimeEvidence:
    model_selection_receipt_id: str
    model_selection_digest: str
    model_runtime_binding_receipt_id: str
    model_runtime_binding_digest: str
    verification_receipt_id: str
    verification_digest: str
    expires_at: int


class AuthorRuntimeEvidenceResolver(Protocol):
    def resolve(
        self, verification_receipt_id: str
    ) -> AuthorRuntimeEvidence | None: ...


@dataclass(frozen=True, slots=True)
class ReviewerKeyAuthority:
    public_key: str
    key_epoch: str
    expires_at: int


class ReviewerKeyAuthorityResolver(Protocol):
    def resolve(
        self, reviewer_principal_id: str, reviewer_principal_provider: str
    ) -> ReviewerKeyAuthority | None: ...


@dataclass(frozen=True, slots=True)
class SovereignAuthorizationEvidence:
    authorization_digest: str
    authority_request_digest: str
    principal_id: str
    principal_provider: str
    principal_public_key: str
    reddog_id: str
    reddog_public_key: str
    repo_full_name: str
    foundup_id: str
    work_order_id: str
    key_epoch: str
    expires_at: int


class SovereignAuthorizationEvidenceResolver(Protocol):
    def resolve(
        self, authorization_digest: str
    ) -> SovereignAuthorizationEvidence | None: ...


@dataclass(frozen=True, slots=True)
class ElevatedConsensusPolicy:
    policy_receipt_id: str
    policy_digest: str
    authority_principal_id: str
    reviewer_membership: tuple[tuple[str, str, str], ...]
    minimum_approvals: int
    required_roles: tuple[str, ...]
    maximum_ttl_seconds: int = 600
    maximum_future_skew_seconds: int = 60


class ElevatedConsensusPolicyResolver(Protocol):
    def resolve(self, policy_digest: str) -> ElevatedConsensusPolicy | None: ...


def elevated_consensus_policy_digest(policy: ElevatedConsensusPolicy) -> str:
    payload = asdict(policy)
    payload.pop("policy_digest")
    return canonical_json_digest(payload)


def elevated_consensus_policy_valid(policy: object) -> bool:
    if type(policy) is not ElevatedConsensusPolicy:
        return False
    membership = policy.reviewer_membership
    roles = policy.required_roles
    return all(
        (
            policy.policy_digest == elevated_consensus_policy_digest(policy),
            policy.policy_receipt_id.startswith("elevated-consensus-policy:"),
            bool(policy.authority_principal_id),
            type(membership) is tuple,
            bool(membership),
            len(set(membership)) == len(membership),
            all(
                type(item) is tuple
                and len(item) == 3
                and all(type(value) is str and value and value.isascii() for value in item)
                for item in membership
            ),
            type(roles) is tuple,
            bool(roles),
            len(set(roles)) == len(roles),
            set(roles).issubset({role for _, _, role in membership}),
            type(policy.minimum_approvals) is int,
            1 <= policy.minimum_approvals <= len(membership),
            type(policy.maximum_ttl_seconds) is int,
            1 <= policy.maximum_ttl_seconds <= 3600,
            type(policy.maximum_future_skew_seconds) is int,
            0 <= policy.maximum_future_skew_seconds <= 300,
        )
    )


__all__ = [
    "AuthorRuntimeEvidence",
    "AuthorRuntimeEvidenceResolver",
    "ElevatedConsensusPolicy",
    "ElevatedConsensusPolicyResolver",
    "ReviewerKeyAuthority",
    "ReviewerKeyAuthorityResolver",
    "ReviewerRuntimeEvidence",
    "ReviewerRuntimeEvidenceResolver",
    "SovereignAuthorizationEvidence",
    "SovereignAuthorizationEvidenceResolver",
    "elevated_consensus_policy_digest",
    "elevated_consensus_policy_valid",
]
