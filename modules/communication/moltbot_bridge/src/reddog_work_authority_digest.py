"""Canonical digest validation for signed RedDog work-authority payloads."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Mapping


_ENVELOPE_FIELDS = frozenset(
    {
        "accepted",
        "signature_gate_digest",
        "signed_work_authority_digest",
    }
)


def canonical_work_authority_digest(payload: Mapping[str, Any]) -> str:
    """Return the canonical digest used by signer and dispatch authority receipts."""

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def work_authority_digest_matches(
    payload: Mapping[str, Any],
    expected_digest: Any,
) -> bool:
    """Constant-time validation of a recorded work-authority digest."""

    if not isinstance(expected_digest, str):
        return False
    try:
        current_digest = canonical_work_authority_digest(payload)
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(current_digest, expected_digest)


def signed_authority_envelope_digest_matches(
    signed_authority: Mapping[str, Any],
) -> bool:
    """Validate a verifier-facing authority envelope against its signed payload."""

    if signed_authority.get("accepted") is not True:
        return False
    expected_digest = signed_authority.get(
        "signature_gate_digest"
    ) or signed_authority.get("signed_work_authority_digest")
    work_authority = {
        key: value
        for key, value in signed_authority.items()
        if key not in _ENVELOPE_FIELDS
    }
    return bool(work_authority) and work_authority_digest_matches(
        work_authority,
        expected_digest,
    )


__all__ = [
    "canonical_work_authority_digest",
    "signed_authority_envelope_digest_matches",
    "work_authority_digest_matches",
]
