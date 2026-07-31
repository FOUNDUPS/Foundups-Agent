"""Authenticated durable high-water anchor for signer runtime generations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import is_sha256
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor_codec import (
    SCHEMA_VERSION,
    _authenticated_state,
    _high_water,
    _paths_overlap,
    _require_ascii_text,
    _require_expected_revision,
    _require_next_generation,
    _require_signer,
    _require_verifier,
    _state_revision,
    _unsigned_state,
    _validate_binding,
    _validate_expected_revision,
    decode_signer_runtime_generation_state,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    SignerRuntimeGenerationActivation,
    SignerRuntimeGenerationBinding,
    SignerRuntimeGenerationHighWater,
    SignerRuntimeGenerationHighWaterAuthorityBoundary,
    SignerRuntimeGenerationHighWaterStore,
    SignerRuntimeGenerationPendingAdvance,
    SignerRuntimeGenerationSigner,
    SignerRuntimeGenerationVerifier,
    TransactionalSignerRuntimeGenerationHighWaterStore,
    VerifiedSignerRuntimeGenerationHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_commit_guard import (
    decode_previous_anchor_state,
    encode_anchor_state,
    run_commit_guard_or_rollback,
    validate_pending_generation,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
    validate_runtime_root_path,
)


class DurableSignerRuntimeGenerationAnchor:
    """Confined atomic generation CAS; never grants execution authority."""

    def __init__(
        self,
        path: Path | str,
        *,
        allowed_root: Path | str,
        repo_root: Path | str,
        anchor_id: str,
        signer: SignerRuntimeGenerationSigner,
        verifier: SignerRuntimeGenerationVerifier,
        high_water_authority: object,
        high_water_authority_boundary: (
            SignerRuntimeGenerationHighWaterAuthorityBoundary
        ),
    ) -> None:
        self._anchor_id = _require_ascii_text(anchor_id, "anchor_id")
        self._signer = _require_signer(signer)
        self._verifier = _require_verifier(verifier)
        if self._signer.authenticator_id != self._verifier.authenticator_id:
            raise ValueError("generation_anchor_signer_verifier_mismatch")
        self._store = AtomicJsonAuthorityRuntimeStore(
            path,
            allowed_root=allowed_root,
            repo_root=repo_root,
        )
        verified = high_water_authority_boundary.require(high_water_authority)
        if (
            verified.store_id != verified.store.store_id
            or verified.durability_receipt_id
            != verified.store.durability_receipt_id
        ):
            raise ValueError("generation_anchor_high_water_authority_mismatch")
        if not isinstance(
            verified.store,
            TransactionalSignerRuntimeGenerationHighWaterStore,
        ):
            raise ValueError(
                "generation_anchor_transactional_high_water_required"
            )
        rollback_root, witness_root = _validate_generation_domains(
            self._store, verified.store
        )
        self._high_water_store = verified.store
        self._high_water_store_id = _require_ascii_text(
            verified.store_id, "high_water_store_id"
        )
        if not is_sha256(verified.durability_receipt_id):
            raise ValueError("generation_anchor_high_water_receipt_invalid")
        self._high_water_durability_receipt_id = (
            verified.durability_receipt_id
        )
        self._repo_root = self._store.repo_root
        self._allowed_root = self._store.allowed_root
        self._witness_rollback_domain_root = witness_root
        self._transaction_lock = self._store.path.with_name(
            self._store.path.name + ".generation-anchor.lock"
        )

    @property
    def path(self) -> Path:
        return self._store.path

    @property
    def authority_root(self) -> Path:
        return self._allowed_root

    @property
    def rollback_domain_root(self) -> Path:
        return self._high_water_store.rollback_domain_root

    @property
    def witness_rollback_domain_root(self) -> Path:
        return self._witness_rollback_domain_root

    def load(self) -> SignerRuntimeGenerationActivation | None:
        with self._lock():
            return self._recover_current(commit_guard=None)

    def recover(
        self,
        *,
        commit_guard: (
            Callable[[SignerRuntimeGenerationActivation], None] | None
        ) = None,
    ) -> SignerRuntimeGenerationActivation | None:
        """Complete only an authenticated one-generation pending advance."""

        with self._lock():
            return self._recover_current(commit_guard=commit_guard)

    def activate(
        self,
        binding: SignerRuntimeGenerationBinding,
        *,
        expected_revision: str | None,
        commit_guard: (
            Callable[[SignerRuntimeGenerationActivation], None] | None
        ) = None,
    ) -> SignerRuntimeGenerationActivation:
        _validate_binding(binding)
        _validate_expected_revision(expected_revision)
        if commit_guard is not None and not callable(commit_guard):
            raise TypeError("generation_anchor_commit_guard_invalid")
        with self._lock():
            current = self._recover_current(commit_guard=commit_guard)
            _require_expected_revision(current, expected_revision)
            _require_next_generation(current, binding)
            unsigned = self._unsigned(binding, expected_revision)
            state = _authenticated_state(
                unsigned, self._signer, self._verifier
            )
            return _activate_transactional(
                self,
                state=state,
                current=current,
                expected_revision=expected_revision,
                commit_guard=commit_guard,
            )

    def _recover_current(
        self,
        *,
        commit_guard: (
            Callable[[SignerRuntimeGenerationActivation], None] | None
        ),
    ) -> SignerRuntimeGenerationActivation | None:
        current = self._decode(self._store.load())
        current = _recover_transaction(
            self, current, commit_guard=commit_guard
        )
        return self._reconcile_high_water(current)

    def _decode(
        self, state: Mapping[str, Any] | None
    ) -> SignerRuntimeGenerationActivation | None:
        return decode_signer_runtime_generation_state(
            state,
            anchor_id=self._anchor_id,
            verifier=self._verifier,
            high_water_store_id=self._high_water_store_id,
            high_water_durability_receipt_id=(
                self._high_water_durability_receipt_id
            ),
        )

    def _unsigned(
        self,
        binding: SignerRuntimeGenerationBinding,
        previous_revision: str | None,
    ) -> dict[str, Any]:
        return _unsigned_state(
            binding,
            anchor_id=self._anchor_id,
            authenticator_id=self._verifier.authenticator_id,
            high_water_store_id=self._high_water_store_id,
            high_water_durability_receipt_id=(
                self._high_water_durability_receipt_id
            ),
            previous_revision=previous_revision,
        )

    def _lock(self):
        return confined_runtime_operation_lock(
            self._transaction_lock,
            repo_root=self._repo_root,
            allowed_root=self._allowed_root,
        )

    def _reconcile_high_water(
        self,
        current: SignerRuntimeGenerationActivation | None,
    ) -> SignerRuntimeGenerationActivation | None:
        high_water = self._high_water_store.load(self._anchor_id)
        witness = self._high_water_store.witness_load(self._anchor_id)
        if current is None:
            if high_water is not None or witness is not None:
                raise ValueError("generation_anchor_rollback_detected")
            return None
        current_value = _high_water(current)
        if high_water == current_value and witness == current_value:
            return current
        raise ValueError("generation_anchor_rollback_detected")


def _validate_generation_domains(store, high_water_store):
    rollback_root = validate_runtime_root_path(
        high_water_store.rollback_domain_root,
        repo_root=store.repo_root,
    )
    witness_root = validate_runtime_root_path(
        high_water_store.witness_rollback_domain_root,
        repo_root=store.repo_root,
    )
    if (
        _paths_overlap(rollback_root, store.allowed_root)
        or _paths_overlap(witness_root, store.allowed_root)
        or _paths_overlap(witness_root, rollback_root)
    ):
        raise ValueError("generation_anchor_high_water_domain_overlap")
    return rollback_root, witness_root


def _activate_transactional(
    anchor: DurableSignerRuntimeGenerationAnchor,
    *,
    state: Mapping[str, Any],
    current: SignerRuntimeGenerationActivation | None,
    expected_revision: str | None,
    commit_guard: Callable[[SignerRuntimeGenerationActivation], None] | None,
) -> SignerRuntimeGenerationActivation:
    store = anchor._high_water_store
    assert isinstance(
        store, TransactionalSignerRuntimeGenerationHighWaterStore
    )
    activation = anchor._decode(
        {**state, "revision": _state_revision(state)}
    )
    if activation is None:
        raise RuntimeError("generation_anchor_prepare_invalid")
    expected = _high_water(current)
    next_value = _high_water(activation)
    previous_state = anchor._store.load()
    if anchor._decode(previous_state) != current:
        raise RuntimeError("generation_anchor_previous_state_changed")
    previous_state_json = encode_anchor_state(previous_state)
    pending = store.prepare(
        anchor._anchor_id,
        expected=expected,
        next_value=next_value,
        previous_anchor_state_json=previous_state_json,
    )
    validate_pending_generation(
        pending,
        expected=expected,
        next_value=next_value,
        previous_anchor_state_json=previous_state_json,
    )
    if store.pending(anchor._anchor_id) != pending:
        raise RuntimeError("generation_anchor_prepare_unverified")
    if anchor._store.load() != previous_state:
        raise RuntimeError("generation_anchor_previous_state_changed")
    return _commit_transactional_activation(
        anchor,
        store=store,
        pending=pending,
        state=state,
        activation=activation,
        expected_revision=expected_revision,
        previous_state=previous_state,
        commit_guard=commit_guard,
    )


def _commit_transactional_activation(
    anchor: DurableSignerRuntimeGenerationAnchor,
    *,
    store: TransactionalSignerRuntimeGenerationHighWaterStore,
    pending: SignerRuntimeGenerationPendingAdvance,
    state: Mapping[str, Any],
    activation: SignerRuntimeGenerationActivation,
    expected_revision: str | None,
    previous_state: Mapping[str, Any],
    commit_guard: Callable[[SignerRuntimeGenerationActivation], None] | None,
) -> SignerRuntimeGenerationActivation:
    try:
        revision = anchor._store.commit(
            state, expected_revision=expected_revision
        )
    except Exception:
        persisted = anchor._decode(anchor._store.load())
        if _high_water(persisted) == pending.next_value:
            run_commit_guard_or_rollback(
                anchor,
                store=store,
                pending=pending,
                activation=activation,
                previous_state=previous_state,
                commit_guard=commit_guard,
            )
            _finish_pending(store, anchor._anchor_id, pending)
            return persisted
        if _high_water(persisted) != pending.expected:
            raise ValueError("generation_anchor_pending_state_mismatch")
        store.abort_prepared(anchor._anchor_id, pending.transaction_id)
        _verify_transaction_cleared(
            store, anchor._anchor_id, pending.expected
        )
        raise
    if revision != activation.revision:
        raise RuntimeError("generation_anchor_revision_changed")
    run_commit_guard_or_rollback(
        anchor,
        store=store,
        pending=pending,
        activation=activation,
        previous_state=previous_state,
        commit_guard=commit_guard,
    )
    _finish_pending(store, anchor._anchor_id, pending)
    return activation


def _finish_pending(
    store: TransactionalSignerRuntimeGenerationHighWaterStore,
    anchor_id: str,
    pending: SignerRuntimeGenerationPendingAdvance,
) -> None:
    witness = store.witness_load(anchor_id)
    if witness == pending.expected:
        store.witness_advance(
            anchor_id,
            expected=pending.expected,
            next_value=pending.next_value,
        )
    elif witness != pending.next_value:
        raise ValueError("generation_anchor_witness_mismatch")
    try:
        store.commit_prepared(anchor_id, pending.transaction_id)
    except Exception:
        if (
            store.pending(anchor_id) is None
            and store.load(anchor_id) == pending.next_value
        ):
            return
        raise
    _verify_transaction_cleared(store, anchor_id, pending.next_value)


def _recover_transaction(
    anchor: DurableSignerRuntimeGenerationAnchor,
    current: SignerRuntimeGenerationActivation | None,
    *,
    commit_guard: Callable[[SignerRuntimeGenerationActivation], None] | None,
) -> SignerRuntimeGenerationActivation | None:
    store = anchor._high_water_store
    assert isinstance(
        store, TransactionalSignerRuntimeGenerationHighWaterStore
    )
    pending = store.pending(anchor._anchor_id)
    if pending is None:
        return current
    validate_pending_generation(
        pending,
        expected=store.load(anchor._anchor_id),
        next_value=pending.next_value,
    )
    current_value = _high_water(current)
    if current_value == pending.next_value:
        if commit_guard is None:
            raise ValueError(
                "generation_anchor_pending_verification_required"
            )
        previous_state = decode_previous_anchor_state(pending)
        if _high_water(anchor._decode(previous_state)) != pending.expected:
            raise ValueError("generation_anchor_previous_state_invalid")
        if store.witness_load(anchor._anchor_id) == pending.next_value:
            commit_guard(current)
        else:
            run_commit_guard_or_rollback(
                anchor,
                store=store,
                pending=pending,
                activation=current,
                previous_state=previous_state,
                commit_guard=commit_guard,
            )
        _finish_pending(store, anchor._anchor_id, pending)
        return current
    if current_value == pending.expected:
        if store.witness_load(anchor._anchor_id) != pending.expected:
            raise ValueError("generation_anchor_witness_mismatch")
        store.abort_prepared(anchor._anchor_id, pending.transaction_id)
        _verify_transaction_cleared(
            store, anchor._anchor_id, pending.expected
        )
        return current
    raise ValueError("generation_anchor_pending_state_mismatch")


def _verify_transaction_cleared(
    store: TransactionalSignerRuntimeGenerationHighWaterStore,
    anchor_id: str,
    expected: SignerRuntimeGenerationHighWater | None,
) -> None:
    if store.pending(anchor_id) is not None or store.load(anchor_id) != expected:
        raise RuntimeError("generation_anchor_high_water_unverified")


__all__ = [
    "DurableSignerRuntimeGenerationAnchor",
    "SCHEMA_VERSION",
    "decode_signer_runtime_generation_state",
    "SignerRuntimeGenerationActivation",
    "SignerRuntimeGenerationBinding",
    "SignerRuntimeGenerationHighWater",
    "SignerRuntimeGenerationPendingAdvance",
    "SignerRuntimeGenerationSigner",
    "SignerRuntimeGenerationVerifier",
    "SignerRuntimeGenerationHighWaterAuthorityBoundary",
    "SignerRuntimeGenerationHighWaterStore",
    "TransactionalSignerRuntimeGenerationHighWaterStore",
    "VerifiedSignerRuntimeGenerationHighWater",
]
