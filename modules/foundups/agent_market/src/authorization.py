"""Explicit host-injected authority for FAM verification and payout admission.

Only a trusted host may construct this context after authenticating the caller
and resolving its grants. Client payloads, profiles and compute access are not
authority sources. This module does not implement an entitlement issuer.
"""

from dataclasses import dataclass
from typing import Optional

from .exceptions import PermissionDeniedError, ValidationError


def _text(value: object) -> bool:
    return type(value) is str and bool(value.strip())


@dataclass(frozen=True, slots=True)
class CallerAuthorization:
    """One authenticated principal and immutable exact (FoundUp, role) grants."""

    principal_id: str
    role_grants: frozenset[tuple[str, str]]

    def __post_init__(self) -> None:
        if not _text(self.principal_id):
            raise ValidationError("Authorization principal must be a non-empty string")
        if type(self.role_grants) is not frozenset or any(
            type(grant) is not tuple or len(grant) != 2 or not all(_text(part) for part in grant)
            for grant in self.role_grants
        ):
            raise ValidationError("Authorization grants must be a frozenset of (FoundUp, role) pairs")


def require_authorization(
    authorization: Optional[CallerAuthorization], actor_id: str, foundup_id: str, role: str,
) -> None:
    """Deny absent, payload-shaped, mismatched or insufficient authority."""
    if (
        type(authorization) is not CallerAuthorization
        or authorization.principal_id != actor_id
        or (foundup_id, role) not in authorization.role_grants
    ):
        raise PermissionDeniedError(f"Authenticated {role} authority required for this FoundUp")


def require_verification_authorization(authorization, task_id, task, proof, decision) -> None:
    """Bind authority and independent verifier to the stored task/proof pair."""
    require_authorization(authorization, decision.verifier_id, task.foundup_id, "verifier")
    require_bound_independent_verification(task_id, task, proof, decision)


def require_bound_independent_verification(task_id, task, proof, decision) -> None:
    """Check stored identity/independence without inventing historical grants."""
    if (
        proof is None or decision is None or task.task_id != task_id or decision.task_id != task_id
        or task.proof_id != proof.proof_id or proof.task_id != task_id
        or not _text(task.assignee_id) or proof.submitter_id != task.assignee_id
        or type(decision.approved) is not bool
    ):
        raise ValidationError("Verification requires a bound task, decision and proof")
    if decision.verifier_id in (task.assignee_id, proof.submitter_id):
        raise PermissionDeniedError("Verifier must be independent of the assignee and proof submitter")
