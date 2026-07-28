"""Pure binding checks for signed-worker exact-CAS finalization."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


_ASSURANCE_CAPABILITY = "independent_slice_verification"


def finalization_binding(
    task_id: str,
    claim: Any,
    use: Any,
) -> tuple[str, Mapping[str, Any], Mapping[str, Any]] | None:
    """Return the exact admitted owner and receipts when bindings hold."""

    if not isinstance(claim, Mapping) or not isinstance(use, Mapping):
        return None
    expected_claim, expected_use = dict(claim), dict(use)
    assigned_to = str(expected_claim.get("assigned_to") or "")
    if (
        str(expected_claim.get("task_id") or "") != task_id
        or str(expected_use.get("task_id") or "") != task_id
        or str(expected_claim.get("status") or "") != "CLAIMED"
        or str(expected_use.get("status") or "") != "CONSUMED"
        or expected_use.get("claim_receipt_id")
        != expected_claim.get("receipt_id")
        or expected_use.get("token_digest")
        != expected_claim.get("token_digest")
        or not assigned_to
        or not _valid_receipt(expected_claim)
        or not _valid_receipt(expected_use)
    ):
        return None
    return assigned_to, expected_claim, expected_use


def assurance_request_matches(
    result_context: Mapping[str, Any],
    request: Mapping[str, Any] | None,
) -> bool:
    """Require verifier finalization to carry its receipt-bound request."""

    intent = result_context.get("worker_dispatch_intent")
    intent = dict(intent) if isinstance(intent, Mapping) else {}
    capability = str(
        result_context.get("capability") or intent.get("capability") or ""
    )
    required = capability == _ASSURANCE_CAPABILITY
    if required != (request is not None):
        return False
    if request is None:
        return True
    receipt = result_context.get("signed_worker_task_last_result")
    receipt = dict(receipt) if isinstance(receipt, Mapping) else {}
    return receipt.get("assurance_completion_request") == dict(request)


def _valid_receipt(receipt: Mapping[str, Any]) -> bool:
    body = dict(receipt)
    receipt_id = str(body.pop("receipt_id", "") or "")
    return _is_digest(receipt_id) and receipt_id == canonical_digest(body)


def canonical_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_digest(value: Any) -> bool:
    text = str(value or "").removeprefix("sha256:")
    return len(text) == 64 and all(char in "0123456789abcdef" for char in text)


__all__ = [
    "assurance_request_matches",
    "canonical_digest",
    "finalization_binding",
]
