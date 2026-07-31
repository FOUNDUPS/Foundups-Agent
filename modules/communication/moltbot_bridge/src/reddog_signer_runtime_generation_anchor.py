"""Authenticated durable high-water anchor for signer runtime generations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    is_sha256,
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
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
    validate_runtime_root_path,
)


SCHEMA_VERSION = "reddog_signer_runtime_generation_anchor.v1"
_MAX_AUTHENTICATION_TAG_LENGTH = 4096


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
        rollback_root = validate_runtime_root_path(
            verified.store.rollback_domain_root,
            repo_root=self._store.repo_root,
        )
        if _paths_overlap(rollback_root, self._store.allowed_root):
            raise ValueError("generation_anchor_high_water_domain_overlap")
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
        self._transaction_lock = self._store.path.with_name(
            self._store.path.name + ".generation-anchor.lock"
        )

    @property
    def path(self) -> Path:
        return self._store.path

    def load(self) -> SignerRuntimeGenerationActivation | None:
        with self._lock():
            return self._recover_current()

    def recover(self) -> SignerRuntimeGenerationActivation | None:
        """Complete only an authenticated one-generation pending advance."""

        with self._lock():
            return self._recover_current()

    def activate(
        self,
        binding: SignerRuntimeGenerationBinding,
        *,
        expected_revision: str | None,
    ) -> SignerRuntimeGenerationActivation:
        _validate_binding(binding)
        _validate_expected_revision(expected_revision)
        with self._lock():
            current = self._recover_current()
            _require_expected_revision(current, expected_revision)
            _require_next_generation(current, binding)
            unsigned = self._unsigned(binding, expected_revision)
            state = _authenticated_state(
                unsigned, self._signer, self._verifier
            )
            if _is_transactional(self._high_water_store):
                return _activate_transactional(
                    self,
                    state=state,
                    current=current,
                    expected_revision=expected_revision,
                )
            revision = self._store.commit(
                state,
                expected_revision=expected_revision,
            )
            activation = self._decode({**state, "revision": revision})
            if activation is None:
                raise RuntimeError("generation_anchor_commit_missing")
            self._high_water_store.advance(
                self._anchor_id,
                expected=_high_water(current),
                next_value=_high_water(activation),
            )
            if self._high_water_store.load(self._anchor_id) != _high_water(
                activation
            ):
                raise RuntimeError("generation_anchor_high_water_unverified")
            return activation

    def _recover_current(
        self,
    ) -> SignerRuntimeGenerationActivation | None:
        current = self._decode(self._store.load())
        if _is_transactional(self._high_water_store):
            current = _recover_transaction(self, current)
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
        if current is None:
            if high_water is not None:
                raise ValueError("generation_anchor_rollback_detected")
            return None
        current_value = _high_water(current)
        if high_water == current_value:
            return current
        raise ValueError("generation_anchor_rollback_detected")


def _activate_transactional(
    anchor: DurableSignerRuntimeGenerationAnchor,
    *,
    state: Mapping[str, Any],
    current: SignerRuntimeGenerationActivation | None,
    expected_revision: str | None,
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
    pending = store.prepare(
        anchor._anchor_id, expected=expected, next_value=next_value
    )
    _validate_pending(pending, expected=expected, next_value=next_value)
    if store.pending(anchor._anchor_id) != pending:
        raise RuntimeError("generation_anchor_prepare_unverified")
    return _commit_transactional_activation(
        anchor,
        store=store,
        pending=pending,
        state=state,
        activation=activation,
        expected_revision=expected_revision,
    )


def _commit_transactional_activation(
    anchor: DurableSignerRuntimeGenerationAnchor,
    *,
    store: TransactionalSignerRuntimeGenerationHighWaterStore,
    pending: SignerRuntimeGenerationPendingAdvance,
    state: Mapping[str, Any],
    activation: SignerRuntimeGenerationActivation,
    expected_revision: str | None,
) -> SignerRuntimeGenerationActivation:
    try:
        revision = anchor._store.commit(
            state, expected_revision=expected_revision
        )
    except Exception:
        persisted = anchor._decode(anchor._store.load())
        if _high_water(persisted) == pending.next_value:
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
    _finish_pending(store, anchor._anchor_id, pending)
    return activation


def _finish_pending(
    store: TransactionalSignerRuntimeGenerationHighWaterStore,
    anchor_id: str,
    pending: SignerRuntimeGenerationPendingAdvance,
) -> None:
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
) -> SignerRuntimeGenerationActivation | None:
    store = anchor._high_water_store
    assert isinstance(
        store, TransactionalSignerRuntimeGenerationHighWaterStore
    )
    pending = store.pending(anchor._anchor_id)
    if pending is None:
        return current
    _validate_pending(
        pending,
        expected=store.load(anchor._anchor_id),
        next_value=pending.next_value,
    )
    current_value = _high_water(current)
    if current_value == pending.next_value:
        store.commit_prepared(anchor._anchor_id, pending.transaction_id)
        _verify_transaction_cleared(
            store, anchor._anchor_id, pending.next_value
        )
        return current
    if current_value == pending.expected:
        store.abort_prepared(anchor._anchor_id, pending.transaction_id)
        _verify_transaction_cleared(
            store, anchor._anchor_id, pending.expected
        )
        return current
    raise ValueError("generation_anchor_pending_state_mismatch")


def _validate_pending(
    value: Any,
    *,
    expected: SignerRuntimeGenerationHighWater | None,
    next_value: SignerRuntimeGenerationHighWater | None,
) -> None:
    if (
        not isinstance(value, SignerRuntimeGenerationPendingAdvance)
        or value.expected != expected
        or value.next_value != next_value
        or not is_sha256(value.transaction_id)
        or value.transaction_id == "sha256:" + "0" * 64
    ):
        raise ValueError("generation_anchor_pending_invalid")


def _verify_transaction_cleared(
    store: TransactionalSignerRuntimeGenerationHighWaterStore,
    anchor_id: str,
    expected: SignerRuntimeGenerationHighWater | None,
) -> None:
    if store.pending(anchor_id) is not None or store.load(anchor_id) != expected:
        raise RuntimeError("generation_anchor_high_water_unverified")


def _is_transactional(
    value: SignerRuntimeGenerationHighWaterStore,
) -> bool:
    return isinstance(
        value,
        TransactionalSignerRuntimeGenerationHighWaterStore,
    )


def decode_signer_runtime_generation_state(
    state: Mapping[str, Any],
    *,
    anchor_id: str,
    verifier: SignerRuntimeGenerationVerifier,
    high_water_store_id: str,
    high_water_durability_receipt_id: str,
) -> SignerRuntimeGenerationActivation | None:
    if not state:
        return None
    _validate_state_header(
        state,
        anchor_id=anchor_id,
        verifier=verifier,
        high_water_store_id=high_water_store_id,
        high_water_durability_receipt_id=high_water_durability_receipt_id,
    )
    binding = _binding_from_state(state)
    _validate_binding(binding)
    previous = state.get("previous_revision")
    _validate_expected_revision(previous)
    revision = str(state.get("revision") or "")
    if revision != _state_revision(state):
        raise ValueError("generation_anchor_revision_invalid")
    tag = str(state.get("authentication_tag") or "")
    _validate_authentication_tag(tag)
    unsigned = dict(state)
    unsigned.pop("authentication_tag")
    unsigned.pop("revision")
    if not verifier.verify(_authentication_input(unsigned), tag):
        raise ValueError("generation_anchor_authentication_invalid")
    return SignerRuntimeGenerationActivation(
        anchor_id=anchor_id,
        **asdict(binding),
        previous_revision=previous,
        authenticator_id=verifier.authenticator_id,
        high_water_store_id=high_water_store_id,
        high_water_durability_receipt_id=high_water_durability_receipt_id,
        authentication_tag=tag,
        revision=revision,
    )


def _validate_state_header(
    state: Mapping[str, Any],
    *,
    anchor_id: str,
    verifier: SignerRuntimeGenerationVerifier,
    high_water_store_id: str,
    high_water_durability_receipt_id: str,
) -> None:
    expected_fields = {
        "schema_version",
        "anchor_id",
        "generation",
        "manifest_id",
        "artifact_generation_digest",
        "config_digest",
        "config_raw_digest",
        "run_packet_digest",
        "previous_revision",
        "authenticator_id",
        "high_water_store_id",
        "high_water_durability_receipt_id",
        "authentication_tag",
        "revision",
    }
    if set(state) != expected_fields:
        raise ValueError("generation_anchor_state_shape_invalid")
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("generation_anchor_schema_invalid")
    if state.get("anchor_id") != anchor_id:
        raise ValueError("generation_anchor_identity_mismatch")
    if state.get("authenticator_id") != verifier.authenticator_id:
        raise ValueError("generation_anchor_authenticator_mismatch")
    if (
        state.get("high_water_store_id") != high_water_store_id
        or state.get("high_water_durability_receipt_id")
        != high_water_durability_receipt_id
    ):
        raise ValueError("generation_anchor_high_water_mismatch")


def _unsigned_state(
    binding: SignerRuntimeGenerationBinding,
    *,
    anchor_id: str,
    authenticator_id: str,
    high_water_store_id: str,
    high_water_durability_receipt_id: str,
    previous_revision: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "anchor_id": anchor_id,
        **asdict(binding),
        "previous_revision": previous_revision,
        "authenticator_id": authenticator_id,
        "high_water_store_id": high_water_store_id,
        "high_water_durability_receipt_id": high_water_durability_receipt_id,
    }


def _binding_from_state(state: Mapping[str, Any]) -> SignerRuntimeGenerationBinding:
    return SignerRuntimeGenerationBinding(
        generation=state.get("generation"),
        manifest_id=state.get("manifest_id"),
        artifact_generation_digest=state.get("artifact_generation_digest"),
        config_digest=state.get("config_digest"),
        config_raw_digest=state.get("config_raw_digest"),
        run_packet_digest=state.get("run_packet_digest"),
    )


def _validate_binding(binding: SignerRuntimeGenerationBinding) -> None:
    if not isinstance(binding, SignerRuntimeGenerationBinding):
        raise TypeError("generation_anchor_binding_type_invalid")
    if type(binding.generation) is not int or binding.generation < 1:
        raise ValueError("generation_anchor_generation_invalid")
    values = (
        binding.manifest_id,
        binding.artifact_generation_digest,
        binding.config_digest,
        binding.config_raw_digest,
        binding.run_packet_digest,
    )
    if not all(is_sha256(value) for value in values):
        raise ValueError("generation_anchor_binding_digest_invalid")


def _require_next_generation(
    current: SignerRuntimeGenerationActivation | None,
    binding: SignerRuntimeGenerationBinding,
) -> None:
    expected = 1 if current is None else current.generation + 1
    if binding.generation != expected:
        raise ValueError("generation_anchor_generation_not_monotonic")
    if current is not None and (
        binding.manifest_id == current.manifest_id
        or binding.artifact_generation_digest == current.artifact_generation_digest
    ):
        raise ValueError("generation_anchor_generation_replay")


def _require_expected_revision(
    current: SignerRuntimeGenerationActivation | None,
    expected_revision: str | None,
) -> None:
    actual = None if current is None else current.revision
    if actual != expected_revision:
        raise RuntimeError("generation_anchor_revision_conflict")


def _validate_expected_revision(value: Any) -> None:
    if value is not None and (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError("generation_anchor_expected_revision_invalid")


def _require_signer(
    value: Any,
) -> SignerRuntimeGenerationSigner:
    if not callable(getattr(value, "authenticate", None)):
        raise ValueError("generation_anchor_signer_invalid")
    _require_ascii_text(
        getattr(value, "authenticator_id", None),
        "authenticator_id",
    )
    return value


def _require_verifier(
    value: Any,
) -> SignerRuntimeGenerationVerifier:
    if not callable(getattr(value, "verify", None)) or callable(
        getattr(value, "authenticate", None)
    ):
        raise ValueError("generation_anchor_verifier_invalid")
    _require_ascii_text(
        getattr(value, "authenticator_id", None),
        "authenticator_id",
    )
    return value


def _authenticated_state(
    unsigned: Mapping[str, Any],
    signer: SignerRuntimeGenerationSigner,
    verifier: SignerRuntimeGenerationVerifier,
) -> dict[str, Any]:
    payload = _authentication_input(unsigned)
    tag = signer.authenticate(payload)
    _validate_authentication_tag(tag)
    if not verifier.verify(payload, tag):
        raise ValueError("generation_anchor_authentication_rejected")
    return {**unsigned, "authentication_tag": tag}


def _high_water(
    value: SignerRuntimeGenerationActivation | None,
) -> SignerRuntimeGenerationHighWater | None:
    if value is None:
        return None
    return SignerRuntimeGenerationHighWater(
        generation=value.generation,
        revision=value.revision,
    )


def _validate_authentication_tag(value: Any) -> None:
    if (
        not isinstance(value, str)
        or not value
        or not value.isascii()
        or len(value) > _MAX_AUTHENTICATION_TAG_LENGTH
    ):
        raise ValueError("generation_anchor_authentication_tag_invalid")


def _require_ascii_text(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or not value.isascii()
        or len(value) > 1024
    ):
        raise ValueError(f"generation_anchor_{name}_invalid")
    return value.strip()


def _paths_overlap(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents


def _authentication_input(state: Mapping[str, Any]) -> bytes:
    return json.dumps(
        state,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _state_revision(state: Mapping[str, Any]) -> str:
    unsigned = dict(state)
    unsigned.pop("revision", None)
    return hashlib.sha256(_authentication_input(unsigned)).hexdigest()


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
