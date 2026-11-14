"""Root-authority validation for signer protected-use operations."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service import (
    RootAuthoritySnapshot,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_state import (
    RootVerifiedOutcomeAuthorityState,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_protocol import (
    RootProtectedUseRequest,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_authority import (
    lease_root_revocation_policy,
    root_revocation_authority_repo,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_validation import (
    require_root_revocation_context,
    revocation_high_water,
    verified_root_revocation_snapshot,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_reader import (
    SignerGrantRevocationAuthorityReader,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityReader,
)


@dataclass(frozen=True)
class ValidatedProtectedUseAcquire:
    revocation_binding: str
    expected_revocation: ProposalReplayHighWater


@contextmanager
def validate_protected_use_acquire(
    request: RootProtectedUseRequest, *, snapshot: RootAuthoritySnapshot,
    state: RootVerifiedOutcomeAuthorityState, authority: object,
    now_epoch: int,
) -> Iterator[ValidatedProtectedUseAcquire]:
    """Observe local consensus before root-locked generation/revocation CAS."""

    with lease_root_revocation_policy(authority, request.policy) as lease:
        binding = lease.revocation_binding
        require_root_revocation_context(
            request, snapshot, state, lease.policy, binding
        )
        yield _validated_acquire(
            request, state=state, binding=binding,
            repo=root_revocation_authority_repo(authority),
            policy=lease.policy, resolver=lease.resolver,
            now_epoch=now_epoch,
        )


def _validated_acquire(
    request: RootProtectedUseRequest, *, state: RootVerifiedOutcomeAuthorityState,
    binding: object, repo: object, policy: object, resolver: object,
    now_epoch: int,
) -> ValidatedProtectedUseAcquire:
    local = SignerGrantRevocationAuthorityReader(
        binding, repo_root=repo
    ).state()
    if local.pending is not None or local.current is None:
        raise RuntimeError("root_protected_use_revocation_state_invalid")
    current = verified_root_revocation_snapshot(
        local.current, binding, policy, resolver, now_epoch, fresh=True
    )
    assert current is not None
    high = revocation_high_water(current)
    assert high is not None
    _require_witness(binding, repo, high)
    if state.load(binding.anchor_binding_digest()) != high:
        raise RuntimeError("root_protected_use_anchor_mismatch")
    if _revoked(current, request.grant_id, request.key_epoch):
        raise RuntimeError("root_protected_use_revoked")
    return ValidatedProtectedUseAcquire(
        revocation_binding=binding.anchor_binding_digest(),
        expected_revocation=high,
    )


def validate_protected_use_finish_context(
    request: RootProtectedUseRequest, *, snapshot: RootAuthoritySnapshot,
    state: RootVerifiedOutcomeAuthorityState, authority: object,
) -> None:
    with lease_root_revocation_policy(authority, request.policy) as lease:
        require_root_revocation_context(
            request, snapshot, state, lease.policy, lease.revocation_binding
        )


def _require_witness(
    binding: object, repo: object, expected: ProposalReplayHighWater,
) -> None:
    witness = SqliteMonotonicAuthorityReader(
        binding.witness_path, allowed_root=binding.witness_root,
        repo_root=repo, store_id=binding.witness_store_id,
        durability_receipt_id=binding.witness_durability_receipt_id,
    )
    if witness.load(binding.witness_binding_digest()) != expected:
        raise RuntimeError("root_protected_use_witness_mismatch")


def _revoked(snapshot: object, grant_id: str, key_epoch: str) -> bool:
    return bool(
        grant_id in snapshot["revoked_grant_ids"]
        or key_epoch in snapshot["revoked_key_epochs"]
    )


__all__ = [
    "ValidatedProtectedUseAcquire", "validate_protected_use_acquire",
    "validate_protected_use_finish_context",
]
