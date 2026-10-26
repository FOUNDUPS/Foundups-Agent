"""Atomic persistence for issued delegated-authority records."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence


def commit_issued_authority(
    store: Any, *, request: Any, identity_digest: str,
    work_authority_digest: str, receipt_id: str,
    schema_version: str, issued_status: str,
) -> str:
    """Commit one issued authority and its consumed nonces atomically."""

    current = store.load()
    expected_revision = current.get("revision")
    nonces = (
        current.get("nonces")
        if isinstance(current.get("nonces"), Mapping)
        else {}
    )
    issued = (
        current.get("issued_authorities")
        if isinstance(current.get("issued_authorities"), Mapping)
        else {}
    )
    if request.work_order_id in issued:
        raise RuntimeError("duplicate_work_order")
    next_state = json.loads(json.dumps(current, sort_keys=True))
    next_state.setdefault("schema_version", schema_version)
    next_state["nonces"] = {
        "identity": list(
            _append_unique(
                nonces.get("identity", ()),
                request.identity_nonce,
            )
        ),
        "work_authority": list(
            _append_unique(
                nonces.get("work_authority", ()),
                request.work_authority_nonce,
            )
        ),
    }
    issued_next = dict(issued)
    issued_next[request.work_order_id] = _issued_record(
        request,
        identity_digest=identity_digest,
        work_authority_digest=work_authority_digest,
        receipt_id=receipt_id,
        issued_status=issued_status,
    )
    next_state["issued_authorities"] = issued_next
    return store.commit(next_state, expected_revision=expected_revision)


def _issued_record(
    request: Any,
    *,
    identity_digest: str,
    work_authority_digest: str,
    receipt_id: str,
    issued_status: str,
) -> dict[str, Any]:
    record = {
        "receipt_id": receipt_id,
        "identity_digest": identity_digest,
        "work_authority_digest": work_authority_digest,
        "work_order_digest": request.work_order_digest,
        "queue_consumer_receipt_digest": request.queue_consumer_receipt_digest,
        "selected_slice": str(request.queue_consumer_receipt["slice_id"]),
        "base_ref": request.base_ref,
        "principal_id": request.principal_id,
        "reddog_id": request.reddog_id,
        "foundup_id": request.foundup_id,
        "repo_full_name": request.repo_full_name,
        "wsp15_allocation_receipt_id": request.wsp15_allocation_receipt_id,
        "wsp15_allocation_digest": request.wsp15_allocation_digest,
        "status": issued_status,
    }
    _copy_optional_pairs(record, request)
    return record


def _copy_optional_pairs(record: dict[str, Any], request: Any) -> None:
    pairs = (
        (
            "model_runtime_binding_receipt_id",
            "model_runtime_binding_digest",
        ),
        ("model_selection_receipt_id", "model_selection_digest"),
        ("memex_supply_receipt_id", "memex_supply_digest"),
        (
            "architect_fix_publication_receipt_id",
            "architect_fix_publication_binding_digest",
        ),
    )
    for id_field, digest_field in pairs:
        receipt_id = getattr(request, id_field)
        digest = getattr(request, digest_field)
        if receipt_id or digest:
            record[id_field] = str(receipt_id or "")
            record[digest_field] = str(digest or "")


def _append_unique(items: Sequence[str], item: str) -> tuple[str, ...]:
    values = list(map(str, items))
    if item not in values:
        values.append(item)
    return tuple(values)


__all__ = ["commit_issued_authority"]
