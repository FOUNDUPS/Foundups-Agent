"""Server-derived validation for signer-revocation root transitions."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service import (
    RootAuthoritySnapshot,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_state import (
    RootVerifiedOutcomeAuthorityState,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_authority import (
    lease_root_revocation_policy,
    root_revocation_authority_repo,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_protocol import (
    OP_ADVANCE,
    RootRevocationRequest,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_reader import (
    SignerGrantRevocationAuthorityReader,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_contract import (
    verify_signer_grant_revocation_snapshot,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_store_codec import (
    require_monotonic,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityReader,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    constant_time_compare,
)


@dataclass(frozen=True)
class ValidatedRootRevocationOperation:
    binding_digest: str
    expected: ProposalReplayHighWater | None
    wanted: ProposalReplayHighWater | None


@contextmanager
def validate_root_revocation_operation(
    request: RootRevocationRequest, *, snapshot: RootAuthoritySnapshot,
    state: RootVerifiedOutcomeAuthorityState, authority: object,
    now_epoch: int,
) -> Iterator[ValidatedRootRevocationOperation]:
    with lease_root_revocation_policy(authority, request.policy) as lease:
        binding = lease.revocation_binding
        require_root_revocation_context(
            request, snapshot, state, lease.policy, binding
        )
        if request.operation != OP_ADVANCE:
            yield ValidatedRootRevocationOperation(
                binding.anchor_binding_digest(), None, None
            )
            return
        yield _derive_advance(
            request, binding=binding, policy=lease.policy,
            resolver=lease.resolver, repo=root_revocation_authority_repo(authority),
            now_epoch=now_epoch,
        )


def require_root_revocation_context(
    request: object, snapshot: RootAuthoritySnapshot,
    state: RootVerifiedOutcomeAuthorityState, policy: Mapping[str, Any],
    binding: Any,
) -> None:
    descriptor = snapshot.descriptor
    expected = (
        request.owner_config_id, request.policy_id, request.binding_digest,
        str(descriptor["signer_public_key"]), state.store_id,
        state.durability_receipt_id, state.state_binding_digest,
    )
    actual = (
        str(policy["owner_config_id"]), str(policy["policy_id"]),
        binding.anchor_binding_digest(), str(policy["target_signer_public_key"]),
        binding.anchor_store_id, binding.anchor_durability_receipt_id,
        binding.anchor_state_binding_digest,
    )
    if any(not constant_time_compare(str(a), str(b)) for a, b in zip(expected, actual)):
        raise ValueError("root_revocation_authority_binding_invalid")
    if any(
        _overlap(root, local)
        for root in state.rollback_domain_roots
        for local in (binding.primary_root, binding.witness_root)
    ):
        raise ValueError("root_revocation_authority_domains_overlap")


def _derive_advance(
    request: RootRevocationRequest, *, binding: Any, policy: Mapping[str, Any],
    resolver: Any, repo: Any, now_epoch: int,
) -> ValidatedRootRevocationOperation:
    local = SignerGrantRevocationAuthorityReader(binding, repo_root=repo).state()
    current = verified_root_revocation_snapshot(
        local.current, binding, policy, resolver, now_epoch, fresh=False
    )
    pending = verified_root_revocation_snapshot(
        local.pending, binding, policy, resolver, now_epoch, fresh=True
    )
    requested = request.snapshot_id
    if pending is not None and pending["snapshot_id"] == requested:
        require_monotonic(current, pending)
        expected, wanted = revocation_high_water(current), revocation_high_water(pending)
    elif pending is None and current is not None and current["snapshot_id"] == requested:
        expected, wanted = None, revocation_high_water(current)
    else:
        raise ValueError("root_revocation_pending_snapshot_mismatch")
    witness = SqliteMonotonicAuthorityReader(
        binding.witness_path, allowed_root=binding.witness_root, repo_root=repo,
        store_id=binding.witness_store_id,
        durability_receipt_id=binding.witness_durability_receipt_id,
    )
    if witness.load(binding.witness_binding_digest()) != wanted:
        raise ValueError("root_revocation_witness_mismatch")
    return ValidatedRootRevocationOperation(
        binding.anchor_binding_digest(), expected, wanted
    )


def _overlap(left: object, right: object) -> bool:
    first = Path(str(left)).resolve()
    second = Path(str(right)).resolve()
    return first == second or first in second.parents or second in first.parents


def verified_root_revocation_snapshot(
    value: Mapping[str, Any] | None, binding: Any, policy: Mapping[str, Any],
    resolver: Any, now_epoch: int, *, fresh: bool,
) -> dict[str, Any] | None:
    if value is None:
        return None
    from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
        expected_snapshot_binding,
    )

    return verify_signer_grant_revocation_snapshot(
        value, expected=expected_snapshot_binding(policy, binding),
        principal_key_resolver=resolver,
        signature_verifier=Ed25519SignatureVerifier(), now_epoch=now_epoch,
        require_freshness=fresh,
    )


def revocation_high_water(
    value: Mapping[str, Any] | None,
) -> ProposalReplayHighWater | None:
    if value is None:
        return None
    return ProposalReplayHighWater(
        int(value["sequence"]), str(value["snapshot_id"])[7:]
    )


__all__ = [
    "ValidatedRootRevocationOperation", "require_root_revocation_context",
    "revocation_high_water", "validate_root_revocation_operation",
    "verified_root_revocation_snapshot",
]
