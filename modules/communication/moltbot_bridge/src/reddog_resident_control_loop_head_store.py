"""Rollback-resistant high-water state for authenticated control receipts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    AtomicJsonAuthorityRuntimeStore,
)


CONTROL_RECEIPT_HEAD_SCHEMA_VERSION = "reddog_control_receipt_head.v1"


def load_control_receipt_head(
    path: Path | str,
) -> tuple[AtomicJsonAuthorityRuntimeStore, dict[str, Any], dict[str, Any] | None]:
    resolved = Path(path).resolve()
    store = AtomicJsonAuthorityRuntimeStore(resolved, allowed_root=resolved.parent)
    state = store.load()
    if not isinstance(state, dict):
        raise ValueError("resident_control_loop_head_state_invalid")
    raw = state.get("control_receipt_head")
    if raw is None:
        return store, state, None
    if not isinstance(raw, Mapping):
        raise ValueError("resident_control_loop_head_invalid")
    head = dict(raw)
    _validate_head_shape(head)
    return store, state, head


def build_control_receipt_head(
    *,
    receipt: Mapping[str, Any],
    receipt_ids: tuple[str, ...],
    consumed_child_receipt_ids: tuple[str, ...],
    consumed_child_evidence_digests: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema_version": CONTROL_RECEIPT_HEAD_SCHEMA_VERSION,
        "sequence_number": int(receipt["sequence_number"]),
        "receipt_count": len(receipt_ids),
        "receipt_id": str(receipt["receipt_id"]),
        "previous_receipt_id": str(receipt["previous_receipt_id"]),
        "receipt_ids_digest": _digest(list(receipt_ids)),
        "signed_receipt": dict(receipt),
        "consumed_child_receipt_ids": list(consumed_child_receipt_ids),
        "consumed_child_evidence_digests": list(
            consumed_child_evidence_digests
        ),
    }


def commit_control_receipt_head(
    *,
    store: AtomicJsonAuthorityRuntimeStore,
    state: Mapping[str, Any],
    head: Mapping[str, Any],
) -> str:
    next_state = dict(state)
    expected_revision = next_state.get("revision")
    next_state.pop("revision", None)
    next_state["control_receipt_head"] = dict(head)
    return store.commit(next_state, expected_revision=expected_revision)


def commit_next_control_receipt_head(
    *,
    store: AtomicJsonAuthorityRuntimeStore,
    state: Mapping[str, Any],
    chain: Mapping[str, Any],
    receipt: Any,
) -> str:
    receipt_ids = (*chain["current_receipt_ids"], receipt.receipt_id)
    child_receipts = tuple(
        sorted({*chain["child_receipt_ids"], *receipt.child_execution_receipt_ids})
    )
    child_digests = tuple(
        sorted(
            {
                *chain["child_evidence_digests"],
                *receipt.child_execution_evidence_digests,
            }
        )
    )
    head = build_control_receipt_head(
        receipt=receipt.to_dict(), receipt_ids=receipt_ids,
        consumed_child_receipt_ids=child_receipts,
        consumed_child_evidence_digests=child_digests,
    )
    return commit_control_receipt_head(store=store, state=state, head=head)


def verify_control_receipt_head(
    head: Mapping[str, Any], *, receipt_ids: tuple[str, ...]
) -> None:
    _validate_head_shape(head)
    if (
        int(head["receipt_count"]) != len(receipt_ids)
        or int(head["sequence_number"]) != len(receipt_ids)
        or str(head["receipt_id"]) != (receipt_ids[-1] if receipt_ids else "")
        or str(head["receipt_ids_digest"]) != _digest(list(receipt_ids))
    ):
        raise ValueError("resident_control_loop_head_chain_mismatch")


def verify_control_receipt_head_against_chain(
    head: Mapping[str, Any],
    *,
    receipt_ids: tuple[str, ...],
    child_receipt_ids: tuple[str, ...],
    child_evidence_digests: tuple[str, ...],
) -> None:
    """Verify the full high-water witness before any downstream execution."""

    verify_control_receipt_head(head, receipt_ids=receipt_ids)
    _verify_consumed_evidence(
        head,
        {
            "child_receipt_ids": frozenset(child_receipt_ids),
            "child_evidence_digests": frozenset(child_evidence_digests),
        },
    )


def reconcile_control_receipt_head(
    *,
    target: Path,
    chain: Mapping[str, Any],
    head: Mapping[str, Any] | None,
    repo_root: Path | str,
    signing_context: Any,
    verify_receipt: Callable[..., Any],
    append_receipt: Callable[..., None],
    validate_chain: Callable[..., dict[str, Any]],
    read_chain: Callable[[Path], str],
) -> dict[str, Any]:
    current_ids = tuple(chain["current_receipt_ids"])
    if head is None:
        if current_ids:
            raise ValueError("resident_control_loop_head_missing_for_existing_chain")
        return dict(chain)
    if int(head["receipt_count"]) == len(current_ids):
        verify_control_receipt_head_against_chain(
            head,
            receipt_ids=current_ids,
            child_receipt_ids=tuple(chain["child_receipt_ids"]),
            child_evidence_digests=tuple(chain["child_evidence_digests"]),
        )
        return dict(chain)
    if int(head["receipt_count"]) != len(current_ids) + 1:
        raise ValueError("resident_control_loop_head_rollback_detected")
    pending = _verify_pending_receipt(
        head, chain, repo_root, signing_context, verify_receipt
    )
    append_receipt(
        target, pending, repo_root,
        signing_context=signing_context, require_authentication=True,
    )
    recovered = validate_chain(
        read_chain(target), signing_context=signing_context,
        require_authenticated_current=True,
    )
    verify_control_receipt_head_against_chain(
        head,
        receipt_ids=tuple(recovered["current_receipt_ids"]),
        child_receipt_ids=tuple(recovered["child_receipt_ids"]),
        child_evidence_digests=tuple(recovered["child_evidence_digests"]),
    )
    return recovered


def _verify_pending_receipt(
    head: Mapping[str, Any],
    chain: Mapping[str, Any],
    repo_root: Path | str,
    context: Any,
    verify_receipt: Callable[..., Any],
) -> Any:
    pending = verify_receipt(
        dict(head["signed_receipt"]), expected_repo_root=repo_root,
        expected_signer_public_key=context.signer_public_key,
        expected_key_epoch=context.key_epoch,
        expected_consensus_receipt_digest=context.consensus_receipt_digest,
        expected_authority_profile_digest=context.authority_profile_digest,
        expected_authority_profile_source_receipt_id=(
            context.authority_profile_source_receipt_id
        ),
        expected_issuer_principal_id=context.issuer_principal_id,
        require_authenticated=True, signature_verifier=context.signature_verifier,
    )
    if (
        pending.sequence_number != int(head["receipt_count"])
        or pending.previous_receipt_id != chain["last_receipt_id"]
        or pending.receipt_id != head["receipt_id"]
    ):
        raise ValueError("resident_control_loop_head_pending_receipt_invalid")
    return pending


def _verify_consumed_evidence(
    head: Mapping[str, Any], chain: Mapping[str, Any]
) -> None:
    if set(head["consumed_child_receipt_ids"]) != set(chain["child_receipt_ids"]):
        raise ValueError("resident_control_loop_head_child_receipts_invalid")
    if set(head["consumed_child_evidence_digests"]) != set(
        chain["child_evidence_digests"]
    ):
        raise ValueError("resident_control_loop_head_child_evidence_invalid")


def _validate_head_shape(head: Mapping[str, Any]) -> None:
    required = {
        "schema_version", "sequence_number", "receipt_count", "receipt_id",
        "previous_receipt_id", "receipt_ids_digest", "signed_receipt",
        "consumed_child_receipt_ids", "consumed_child_evidence_digests",
    }
    if set(head) != required or head.get("schema_version") != CONTROL_RECEIPT_HEAD_SCHEMA_VERSION:
        raise ValueError("resident_control_loop_head_schema_invalid")
    sequence = head.get("sequence_number")
    count = head.get("receipt_count")
    if (
        isinstance(sequence, bool)
        or not isinstance(sequence, int)
        or sequence < 1
        or isinstance(count, bool)
        or not isinstance(count, int)
        or sequence != count
        or not isinstance(head.get("signed_receipt"), Mapping)
    ):
        raise ValueError("resident_control_loop_head_shape_invalid")
    for key in ("consumed_child_receipt_ids", "consumed_child_evidence_digests"):
        values = head.get(key)
        if not isinstance(values, list) or len(values) > 4096 or len(set(values)) != len(values):
            raise ValueError("resident_control_loop_head_consumed_evidence_invalid")


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "build_control_receipt_head",
    "commit_control_receipt_head",
    "commit_next_control_receipt_head",
    "load_control_receipt_head",
    "reconcile_control_receipt_head",
    "verify_control_receipt_head",
    "verify_control_receipt_head_against_chain",
]
