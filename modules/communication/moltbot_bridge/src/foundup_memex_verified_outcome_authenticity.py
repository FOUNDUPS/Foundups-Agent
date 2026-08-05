"""Authenticated, one-shot verified outcomes for resident FoundUp Memex views."""

from __future__ import annotations

import copy
import hashlib
import json
import threading
import weakref
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_receipt_rehydration import (
    rehydrate_held_out_outcome_receipt,
    rehydrate_verified_slice_receipt,
    verified_outcome_evidence_bundle_digest,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_validation import (
    VERIFIED_OUTCOME_BINDING_SCHEMA,
    VERIFIED_OUTCOME_RECORD_SCHEMA,
    VerifiedOutcomeSource,
    load_validated_outcome,
    validate_outcome_evidence_links,
    verified_at_epoch,
)
from modules.communication.moltbot_bridge.src.reddog_signed_receipt_chain import (
    SIGNED_RECEIPT_CHAIN_ACCEPT,
    ReceiptSignatureVerifier,
    SignedReceipt,
    verify_signed_receipt_chain,
)
from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
    reddog_verified_pattern_memory_record_digest,
)

class VerifiedOutcomeReplayStore(Protocol):
    def consume_many_once(self, receipt_ids: Sequence[str]) -> bool: ...

    def consume_once(self, receipt_id: str) -> bool: ...


class VerifiedFoundUpOutcomeCapability:
    """Opaque handle accepted only by the verifier instance that minted it."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "VerifiedFoundUpOutcomeCapability":
        raise TypeError("verified_foundup_outcome_factory_required")

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("verified_foundup_outcome_capability_is_immutable")

    def __copy__(self) -> "VerifiedFoundUpOutcomeCapability":
        raise TypeError("verified_foundup_outcome_capability_copy_forbidden")

    def __deepcopy__(self, _memo: dict[int, Any]) -> "VerifiedFoundUpOutcomeCapability":
        raise TypeError("verified_foundup_outcome_capability_copy_forbidden")

    def __reduce_ex__(self, _protocol: int) -> Any:
        raise TypeError("verified_foundup_outcome_capability_pickle_forbidden")


@dataclass(frozen=True)
class _OutcomeSeal:
    projection: Mapping[str, Any]
    projection_digest: str
    replay_store: VerifiedOutcomeReplayStore
    replay_receipt_id: str
    not_before: int
    expires_at: int


_LOCK = threading.Lock()
_CAPABILITIES: weakref.WeakKeyDictionary[
    VerifiedFoundUpOutcomeCapability, _OutcomeSeal
] = weakref.WeakKeyDictionary()


def verify_and_issue_foundup_memex_outcome(
    *,
    source: VerifiedOutcomeSource,
    record_id: str,
    verification_receipt: Mapping[str, Any],
    held_out_receipt: Mapping[str, Any],
    signed_receipts: Sequence[SignedReceipt | Mapping[str, Any]],
    reddog_public_key: str,
    signature_verifier: ReceiptSignatureVerifier,
    reddog_id: str,
    expected_foundup_id: str,
    expected_snapshot_id: str,
    expected_snapshot_content_digest: str,
    replay_store: VerifiedOutcomeReplayStore,
    now_epoch: int,
    max_age_seconds: int = 600,
) -> VerifiedFoundUpOutcomeCapability:
    _validate_trust_dependencies(source, replay_store, signature_verifier)
    record, binding = load_validated_outcome(
        source=source,
        record_id=record_id,
        expected_foundup_id=expected_foundup_id,
        expected_snapshot_id=expected_snapshot_id,
        expected_snapshot_content_digest=expected_snapshot_content_digest,
        now_epoch=now_epoch,
        max_age_seconds=max_age_seconds,
    )
    verifier = rehydrate_verified_slice_receipt(verification_receipt)
    held_out = rehydrate_held_out_outcome_receipt(
        held_out_receipt,
        verifier=verifier,
    )
    return _issue_validated_outcome(
        record=record,
        binding=binding,
        record_id=record_id,
        verifier=verifier.to_dict(),
        held_out=held_out.to_dict(),
        signed_receipts=signed_receipts,
        reddog_public_key=reddog_public_key,
        signature_verifier=signature_verifier,
        reddog_id=reddog_id,
        replay_store=replay_store,
        now_epoch=now_epoch,
        max_age_seconds=max_age_seconds,
    )


def _issue_validated_outcome(
    *,
    record: Mapping[str, Any],
    binding: Mapping[str, Any],
    record_id: str,
    verifier: Mapping[str, Any],
    held_out: Mapping[str, Any],
    signed_receipts: Sequence[SignedReceipt | Mapping[str, Any]],
    reddog_public_key: str,
    signature_verifier: ReceiptSignatureVerifier,
    reddog_id: str,
    replay_store: VerifiedOutcomeReplayStore,
    now_epoch: int,
    max_age_seconds: int,
) -> VerifiedFoundUpOutcomeCapability:
    validate_outcome_evidence_links(record, binding, verifier, held_out)
    signed_digest = verified_outcome_evidence_bundle_digest(
        record=record,
        verifier_receipt=verifier,
        held_out_receipt=held_out,
    )
    terminal, chain = _verify_signed_bundle(
        signed_receipts=signed_receipts,
        reddog_public_key=reddog_public_key,
        signature_verifier=signature_verifier,
        work_order_id=str(record["work_order_id"]),
        reddog_id=reddog_id,
        signed_digest=signed_digest,
        now_epoch=now_epoch,
        max_age_seconds=max_age_seconds,
    )
    return _mint_verified_bundle(
        record=record,
        binding=binding,
        record_id=record_id,
        signed_digest=signed_digest,
        terminal=terminal,
        chain=chain,
        replay_store=replay_store,
        now_epoch=now_epoch,
        max_age_seconds=max_age_seconds,
    )


def _mint_verified_bundle(
    *,
    record: Mapping[str, Any],
    binding: Mapping[str, Any],
    record_id: str,
    signed_digest: str,
    terminal: SignedReceipt,
    chain: Any,
    replay_store: VerifiedOutcomeReplayStore,
    now_epoch: int,
    max_age_seconds: int,
) -> VerifiedFoundUpOutcomeCapability:
    projection = _projection(
        record,
        binding,
        record_id,
        reddog_verified_pattern_memory_record_digest(record),
        signed_digest,
        terminal,
        chain,
    )
    return _mint_capability(
        projection,
        replay_store=replay_store,
        replay_receipt_id=terminal.receipt_id,
        not_before=now_epoch,
        expires_at=_capability_expiry(
            binding=binding,
            terminal_issued_at=terminal.issued_at,
            now_epoch=now_epoch,
            max_age_seconds=max_age_seconds,
        ),
    )


def _capability_expiry(
    *,
    binding: Mapping[str, Any],
    terminal_issued_at: int,
    now_epoch: int,
    max_age_seconds: int,
) -> int:
    return min(
        now_epoch + max_age_seconds,
        terminal_issued_at + max_age_seconds,
        verified_at_epoch(binding["verified_at"]) + max_age_seconds,
    )


def _verify_signed_bundle(
    *,
    signed_receipts: Sequence[SignedReceipt | Mapping[str, Any]],
    reddog_public_key: str,
    signature_verifier: ReceiptSignatureVerifier,
    work_order_id: str,
    reddog_id: str,
    signed_digest: str,
    now_epoch: int,
    max_age_seconds: int,
) -> tuple[SignedReceipt, Any]:
    chain = verify_signed_receipt_chain(
        signed_receipts,
        reddog_public_key=reddog_public_key,
        signature_verifier=signature_verifier,
        work_order_id=work_order_id,
        reddog_id=reddog_id,
        now=now_epoch,
        allow_empty=False,
    )
    if chain.decision != SIGNED_RECEIPT_CHAIN_ACCEPT or not chain.accepted:
        raise ValueError("verified_outcome_signed_receipt_chain_rejected")
    terminal = _terminal_receipt(signed_receipts)
    if terminal.covered_action_digest != signed_digest:
        raise ValueError("verified_outcome_signed_digest_mismatch")
    if (
        now_epoch - terminal.issued_at < 0
        or now_epoch - terminal.issued_at > max_age_seconds
    ):
        raise ValueError("verified_outcome_signature_expired")
    return terminal, chain


def _mint_capability(
    projection: Mapping[str, Any],
    *,
    replay_store: VerifiedOutcomeReplayStore,
    replay_receipt_id: str,
    not_before: int,
    expires_at: int,
) -> VerifiedFoundUpOutcomeCapability:
    capability = object.__new__(VerifiedFoundUpOutcomeCapability)
    with _LOCK:
        _CAPABILITIES[capability] = _OutcomeSeal(
            projection=projection,
            projection_digest=_digest(projection),
            replay_store=replay_store,
            replay_receipt_id=replay_receipt_id,
            not_before=not_before,
            expires_at=expires_at,
        )
    return capability


def inspect_verified_foundup_memex_outcome(
    capability: Any,
    *,
    expected_foundup_id: str,
    expected_snapshot_id: str,
    expected_snapshot_content_digest: str,
    now_epoch: int,
) -> Mapping[str, Any] | None:
    """Inspect one capability without consuming local or durable replay state."""

    if type(capability) is not VerifiedFoundUpOutcomeCapability:
        return None
    with _LOCK:
        inspected = _inspect_capability_locked(
            capability,
            expected_foundup_id=expected_foundup_id,
            expected_snapshot_id=expected_snapshot_id,
            expected_snapshot_content_digest=expected_snapshot_content_digest,
            now_epoch=now_epoch,
        )
        return copy.deepcopy(inspected[1]) if inspected is not None else None


def consume_verified_foundup_memex_outcomes(
    capabilities: Sequence[Any],
    *,
    expected_foundup_id: str,
    expected_snapshot_id: str,
    expected_snapshot_content_digest: str,
    now_epoch: int,
    expected_projections: Sequence[Mapping[str, Any]] | None = None,
) -> bool:
    """Atomically admit one capability set through its shared replay store."""

    values = tuple(capabilities)
    expected_values = tuple(expected_projections or ())
    if not values or (expected_projections is not None and len(expected_values) != len(values)):
        return False
    with _LOCK:
        inspected = _inspect_capability_set_locked(
            values,
            expected_foundup_id=expected_foundup_id,
            expected_snapshot_id=expected_snapshot_id,
            expected_snapshot_content_digest=expected_snapshot_content_digest,
            now_epoch=now_epoch,
        )
        if inspected is None:
            return False
        seals, projections = inspected
        if expected_projections is not None and tuple(
            _digest(item) for item in expected_values
        ) != tuple(seal.projection_digest for seal in seals):
            return False
        replay_store = seals[0].replay_store
        receipt_ids = tuple(seal.replay_receipt_id for seal in seals)
        if replay_store.consume_many_once(receipt_ids) is not True:
            return False
        for capability in values:
            _CAPABILITIES.pop(capability, None)
        return len(projections) == len(values)


def consume_verified_foundup_memex_outcome(
    capability: Any,
    *,
    expected_foundup_id: str,
    expected_snapshot_id: str,
    expected_snapshot_content_digest: str,
    now_epoch: int,
) -> Mapping[str, Any] | None:
    """Consume one capability through the atomic batch admission path."""

    projection = inspect_verified_foundup_memex_outcome(
        capability,
        expected_foundup_id=expected_foundup_id,
        expected_snapshot_id=expected_snapshot_id,
        expected_snapshot_content_digest=expected_snapshot_content_digest,
        now_epoch=now_epoch,
    )
    if projection is None:
        return None
    accepted = consume_verified_foundup_memex_outcomes(
        (capability,),
        expected_foundup_id=expected_foundup_id,
        expected_snapshot_id=expected_snapshot_id,
        expected_snapshot_content_digest=expected_snapshot_content_digest,
        now_epoch=now_epoch,
        expected_projections=(projection,),
    )
    return projection if accepted else None


def _inspect_capability_set_locked(
    capabilities: Sequence[Any],
    **expected: Any,
) -> tuple[tuple[_OutcomeSeal, ...], tuple[Mapping[str, Any], ...]] | None:
    if len({id(value) for value in capabilities}) != len(capabilities):
        return None
    inspected = tuple(
        _inspect_capability_locked(value, **expected) for value in capabilities
    )
    if any(item is None for item in inspected):
        return None
    seals = tuple(item[0] for item in inspected if item is not None)
    projections = tuple(item[1] for item in inspected if item is not None)
    if any(seal.replay_store is not seals[0].replay_store for seal in seals):
        return None
    if len({seal.replay_receipt_id for seal in seals}) != len(seals):
        return None
    return seals, projections


def _inspect_capability_locked(
    capability: Any,
    *,
    expected_foundup_id: str,
    expected_snapshot_id: str,
    expected_snapshot_content_digest: str,
    now_epoch: int,
) -> tuple[_OutcomeSeal, Mapping[str, Any]] | None:
    seal = _CAPABILITIES.get(capability)
    if seal is None or _digest(seal.projection) != seal.projection_digest:
        return None
    if type(now_epoch) is not int or not seal.not_before <= now_epoch <= seal.expires_at:
        return None
    projection = dict(seal.projection)
    actual = (
        projection.get("foundup_id"),
        projection.get("snapshot_id"),
        projection.get("snapshot_content_digest"),
    )
    expected = (
        expected_foundup_id,
        expected_snapshot_id,
        expected_snapshot_content_digest,
    )
    return (seal, projection) if actual == expected else None


def is_verified_foundup_memex_outcome_capability(value: Any) -> bool:
    return type(value) is VerifiedFoundUpOutcomeCapability


def _validate_trust_dependencies(source: Any, replay_store: Any, verifier: Any) -> None:
    required = (
        getattr(source, "load_verified_outcome", None),
        getattr(replay_store, "consume_many_once", None),
        getattr(verifier, "verify", None),
    )
    if not all(callable(item) for item in required):
        raise ValueError("verified_outcome_trust_dependency_invalid")


def _terminal_receipt(
    receipts: Sequence[SignedReceipt | Mapping[str, Any]],
) -> SignedReceipt:
    raw = receipts[-1]
    if isinstance(raw, SignedReceipt):
        return raw
    return SignedReceipt(
        receipt_id=str(raw["receipt_id"]),
        work_order_id=str(raw["work_order_id"]),
        reddog_id=str(raw["reddog_id"]),
        prev_receipt_hash=raw.get("prev_receipt_hash"),
        covered_action_digest=str(raw["covered_action_digest"]),
        reward_account=raw.get("reward_account"),
        issued_at=int(raw["issued_at"]),
        signature=str(raw["signature"]),
    )


def _projection(
    record: Mapping[str, Any],
    binding: Mapping[str, Any],
    record_id: str,
    record_digest: str,
    evidence_bundle_digest: str,
    terminal: SignedReceipt,
    chain: Any,
) -> Mapping[str, Any]:
    return {
        "foundup_id": binding["foundup_id"],
        "snapshot_id": binding["snapshot_id"],
        "snapshot_content_digest": binding["snapshot_content_digest"],
        "outcome_id": record_id,
        "work_order_id": record["work_order_id"],
        "slice_name": record["slice_name"],
        "worker_id": binding["worker_id"],
        "verifier_id": binding["verifier_id"],
        "verification_receipt_id": record["verifier_receipt_id"],
        "held_out_receipt_id": record["gate_id"],
        "held_out_suite_id": record["held_out_suite_id"],
        "head_sha": record["candidate_head_sha"],
        "content_digest": record_digest,
        "evidence_bundle_digest": evidence_bundle_digest,
        "signed_receipt_id": terminal.receipt_id,
        "signed_receipt_terminal_hash": chain.terminal_receipt_hash,
        "verified_at": binding["verified_at"],
        "scope_origin": "verified_capability",
        "accepted": True,
        "held_out_passed": True,
    }


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "VERIFIED_OUTCOME_BINDING_SCHEMA",
    "VERIFIED_OUTCOME_RECORD_SCHEMA",
    "VerifiedFoundUpOutcomeCapability",
    "VerifiedOutcomeReplayStore",
    "VerifiedOutcomeSource",
    "consume_verified_foundup_memex_outcome",
    "consume_verified_foundup_memex_outcomes",
    "inspect_verified_foundup_memex_outcome",
    "is_verified_foundup_memex_outcome_capability",
    "verify_and_issue_foundup_memex_outcome",
]
