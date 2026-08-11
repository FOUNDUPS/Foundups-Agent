"""Uncomposed local durability foundation for revocation snapshots."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
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
        self.binding = binding
        self.expected = expected_snapshot_binding(dict(policy), binding)
        self.store = store
        self.witness = witness
        self.resolver = principal_key_resolver
        self.verifier = signature_verifier

    def publish(
        self, snapshot: Mapping[str, Any], *, now_epoch: int
    ) -> Mapping[str, Any]:
        with self._lock():
            state = self._recover(now_epoch)
            checked = self._verify(snapshot, now_epoch)
            if checked["sequence"] != _next_sequence(state.current):
                raise ValueError("revocation_supply_sequence_invalid")
            self.store._prepare_under_lock(checked)
            self.witness.advance(
                self.binding.witness_binding_digest(),
                expected=_high_water(state.current),
                next_value=_required_high_water(checked),
            )
            self.store._finalize_under_lock(str(checked["snapshot_id"]))
            committed = self._require_consensus(self.store.state())
            if committed.current != checked:
                raise RuntimeError("revocation_supply_commit_unverified")
            return checked

    def recover(self, *, now_epoch: int) -> Mapping[str, Any] | None:
        with self._lock():
            return self._recover(now_epoch).current

    def _recover(self, now_epoch: int) -> RevocationAuthorityStoreState:
        state = self.store.state()
        current = (
            None if state.current is None else self._verify(state.current, now_epoch)
        )
        if state.pending is None:
            return self._require_consensus(
                RevocationAuthorityStoreState(current=current, pending=None)
            )
        pending = self._verify(state.pending, now_epoch)
        require_monotonic(current, pending)
        current_high = _high_water(current)
        pending_high = _required_high_water(pending)
        observed = self.witness.load(self.binding.witness_binding_digest())
        if observed == current_high:
            self.witness.advance(
                self.binding.witness_binding_digest(),
                expected=current_high, next_value=pending_high,
            )
        elif observed != pending_high:
            raise RuntimeError("revocation_supply_recovery_divergence")
        self.store._finalize_under_lock(str(pending["snapshot_id"]))
        return self._require_consensus(self.store.state())

    def _require_consensus(
        self, state: RevocationAuthorityStoreState
    ) -> RevocationAuthorityStoreState:
        if state.pending is not None:
            raise RuntimeError("revocation_supply_pending")
        observed = self.witness.load(self.binding.witness_binding_digest())
        if observed != _high_water(state.current):
            raise RuntimeError("revocation_supply_witness_mismatch")
        return state

    def _verify(self, value: Mapping[str, Any], now_epoch: int) -> dict[str, Any]:
        return verify_signer_grant_revocation_snapshot(
            value, expected=self.expected,
            principal_key_resolver=self.resolver,
            signature_verifier=self.verifier, now_epoch=now_epoch,
        )

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


def _high_water(value: Mapping[str, Any] | None) -> ProposalReplayHighWater | None:
    return None if value is None else _required_high_water(value)


def _required_high_water(value: Mapping[str, Any]) -> ProposalReplayHighWater:
    return ProposalReplayHighWater(
        sequence=int(value["sequence"]),
        state_revision=str(value["snapshot_id"]).removeprefix("sha256:"),
    )


def _next_sequence(value: Mapping[str, Any] | None) -> int:
    return 1 if value is None else int(value["sequence"]) + 1


__all__ = ["UncomposedDurableSignerGrantRevocationAuthoritySupply"]
