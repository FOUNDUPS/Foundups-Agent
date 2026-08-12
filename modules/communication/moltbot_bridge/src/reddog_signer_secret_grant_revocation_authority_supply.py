"""Uncomposed local durability foundation for revocation snapshots."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    SignerGrantRevocationAuthorityBinding,
    expected_snapshot_binding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_store import (
    RevocationAuthorityStoreState,
    SignerGrantRevocationAuthorityStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_store_codec import (
    require_monotonic,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_contract import (
    verify_signer_grant_revocation_snapshot,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_root_anchor import (
    next_revocation_sequence,
    required_revocation_high_water,
    require_revocation_root_anchor,
    revocation_high_water,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PrincipalKeyResolver,
    SignatureVerifier,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
)


class UncomposedDurableSignerGrantRevocationAuthoritySupply:
    """Exercise local store/witness consensus without production authority."""

    def __init__(
        self, *, binding: SignerGrantRevocationAuthorityBinding,
        policy: Mapping[str, Any], store: SignerGrantRevocationAuthorityStore,
        witness: SqliteMonotonicAuthorityStore,
        anchor: ProposalReplayHighWaterStore,
        principal_key_resolver: PrincipalKeyResolver,
        signature_verifier: SignatureVerifier,
    ) -> None:
        if (
            type(binding) is not SignerGrantRevocationAuthorityBinding
            or type(store) is not SignerGrantRevocationAuthorityStore
            or type(witness) is not SqliteMonotonicAuthorityStore
        ):
            raise ValueError("revocation_supply_dependency_invalid")
        _require_topology(binding, store, witness)
        require_revocation_root_anchor(binding, anchor)
        self.binding = binding
        self.expected = expected_snapshot_binding(dict(policy), binding)
        self.store = store
        self.witness = witness
        self.anchor = anchor
        self.resolver = principal_key_resolver
        self.verifier = signature_verifier

    def publish(
        self, snapshot: Mapping[str, Any], *, now_epoch: int
    ) -> Mapping[str, Any]:
        with self._lock():
            state = self._recover(now_epoch, allow_expired=True)
            checked = self._verify(snapshot, now_epoch)
            if checked["sequence"] != next_revocation_sequence(state.current):
                raise ValueError("revocation_supply_sequence_invalid")
            self.store._prepare_under_lock(checked)
            self.witness.advance(
                self.binding.witness_binding_digest(),
                expected=revocation_high_water(state.current),
                next_value=required_revocation_high_water(checked),
            )
            self.anchor.advance(
                self.binding.anchor_binding_digest(),
                expected=revocation_high_water(state.current),
                next_value=required_revocation_high_water(checked),
            )
            self.store._finalize_under_lock(str(checked["snapshot_id"]))
            committed = self._require_consensus(self.store.state())
            if committed.current != checked:
                raise RuntimeError("revocation_supply_commit_unverified")
            return checked

    def recover(self, *, now_epoch: int) -> Mapping[str, Any] | None:
        with self._lock():
            return self._recover(now_epoch, allow_expired=False).current

    def _recover(
        self, now_epoch: int, *, allow_expired: bool,
    ) -> RevocationAuthorityStoreState:
        state = self.store.state()
        current = (
            None if state.current is None else self._verify_recovery_value(
                state.current, now_epoch, allow_expired=allow_expired,
            )
        )
        if state.pending is None:
            return self._require_consensus(
                RevocationAuthorityStoreState(current=current, pending=None)
            )
        pending = self._verify_recovery_value(
            state.pending, now_epoch, allow_expired=allow_expired,
        )
        require_monotonic(current, pending)
        current_high = revocation_high_water(current)
        pending_high = required_revocation_high_water(pending)
        observed = self.witness.load(self.binding.witness_binding_digest())
        anchored = self.anchor.load(self.binding.anchor_binding_digest())
        if observed == current_high:
            self.witness.advance(
                self.binding.witness_binding_digest(),
                expected=current_high, next_value=pending_high,
            )
        elif observed != pending_high:
            raise RuntimeError("revocation_supply_recovery_divergence")
        if anchored == current_high:
            self.anchor.advance(
                self.binding.anchor_binding_digest(),
                expected=current_high, next_value=pending_high,
            )
        elif anchored != pending_high:
            raise RuntimeError("revocation_supply_anchor_divergence")
        self.store._finalize_under_lock(str(pending["snapshot_id"]))
        return self._require_consensus(self.store.state())

    def _require_consensus(
        self, state: RevocationAuthorityStoreState
    ) -> RevocationAuthorityStoreState:
        if state.pending is not None:
            raise RuntimeError("revocation_supply_pending")
        observed = self.witness.load(self.binding.witness_binding_digest())
        if observed != revocation_high_water(state.current):
            raise RuntimeError("revocation_supply_witness_mismatch")
        anchored = self.anchor.load(self.binding.anchor_binding_digest())
        if anchored != revocation_high_water(state.current):
            raise RuntimeError("revocation_supply_anchor_mismatch")
        return state

    def _verify(self, value: Mapping[str, Any], now_epoch: int) -> dict[str, Any]:
        return verify_signer_grant_revocation_snapshot(
            value, expected=self.expected,
            principal_key_resolver=self.resolver,
            signature_verifier=self.verifier, now_epoch=now_epoch,
        )

    def _verify_integrity(
        self, value: Mapping[str, Any], now_epoch: int,
    ) -> dict[str, Any]:
        return verify_signer_grant_revocation_snapshot(
            value, expected=self.expected,
            principal_key_resolver=self.resolver,
            signature_verifier=self.verifier, now_epoch=now_epoch,
            require_freshness=False,
        )

    def _verify_recovery_value(
        self, value: Mapping[str, Any], now_epoch: int, *, allow_expired: bool,
    ) -> dict[str, Any]:
        if allow_expired:
            return self._verify_integrity(value, now_epoch)
        return self._verify(value, now_epoch)

    def _lock(self):
        return confined_runtime_operation_lock(
            self.binding.operation_lock_path,
            repo_root=self.store.repo_root,
            allowed_root=self.store.allowed_root,
        )


def _require_topology(
    binding: SignerGrantRevocationAuthorityBinding,
    store: SignerGrantRevocationAuthorityStore,
    witness: SqliteMonotonicAuthorityStore,
) -> None:
    expected = (
        store.binding, str(store.path), witness.store_id,
        witness.durability_receipt_id, str(witness.path),
        str(witness.rollback_domain_root),
    )
    actual = (
        binding, binding.primary_path, binding.witness_store_id,
        binding.witness_durability_receipt_id, binding.witness_path,
        binding.witness_root,
    )
    if expected != actual:
        raise ValueError("revocation_supply_topology_invalid")


__all__ = ["UncomposedDurableSignerGrantRevocationAuthoritySupply"]
