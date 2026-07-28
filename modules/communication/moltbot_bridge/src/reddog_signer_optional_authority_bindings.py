"""Optional receipt bindings carried by signed delegated authority."""

from __future__ import annotations

import hmac
import re
from typing import Any

_SHA256_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

_OPTIONAL_BINDING_FIELDS = (
    ("model_selection_receipt_id", "model_selection_digest"),
    ("memex_supply_receipt_id", "memex_supply_digest"),
    (
        "architect_fix_publication_receipt_id",
        "architect_fix_publication_binding_digest",
    ),
)


def is_sha256_digest(value: Any) -> bool:
    """Return True only for a canonical lowercase SHA-256 digest."""

    return isinstance(value, str) and _SHA256_DIGEST_RE.fullmatch(value) is not None


def optional_authority_binding_values_valid(receipt_id: Any, digest: Any) -> bool:
    """Require an absent pair or a non-empty receipt ID plus canonical digest."""

    if receipt_id in (None, "") and digest in (None, ""):
        return True
    if not isinstance(receipt_id, str) or not receipt_id:
        return False
    return is_sha256_digest(digest)


def optional_authority_binding_values_match(
    receipt_id: Any,
    digest: Any,
    authoritative_receipt_id: Any,
    authoritative_digest: Any,
    *,
    allow_absent_source: bool = True,
) -> bool:
    """Require a valid source pair to equal the authoritative pair."""

    if not optional_authority_binding_values_valid(
        authoritative_receipt_id,
        authoritative_digest,
    ):
        return False
    if receipt_id in (None, "") and digest in (None, "") and allow_absent_source:
        return True
    if not optional_authority_binding_values_valid(receipt_id, digest):
        return False
    return hmac.compare_digest(receipt_id, authoritative_receipt_id) and hmac.compare_digest(
        digest,
        authoritative_digest,
    )


def optional_authority_bindings_valid(request: Any) -> bool:
    """Require paired receipt IDs and SHA-256 digests."""

    for receipt_field, digest_field in _OPTIONAL_BINDING_FIELDS:
        receipt_id = getattr(request, receipt_field)
        digest = getattr(request, digest_field)
        if receipt_field == "memex_supply_receipt_id":
            valid = optional_authority_binding_values_valid(receipt_id, digest)
        else:
            valid = bool(receipt_id) == bool(digest) and (
                not digest or str(digest).startswith("sha256:")
            )
        if not valid:
            return False
    return True


def attach_optional_authority_bindings(
    work_authority: dict[str, Any],
    request: Any,
) -> None:
    """Copy validated optional bindings into the signed payload."""

    for receipt_field, digest_field in _OPTIONAL_BINDING_FIELDS:
        receipt_id = getattr(request, receipt_field)
        digest = getattr(request, digest_field)
        if receipt_id and digest:
            work_authority[receipt_field] = str(receipt_id)
            work_authority[digest_field] = str(digest)


__all__ = [
    "attach_optional_authority_bindings",
    "is_sha256_digest",
    "optional_authority_binding_values_match",
    "optional_authority_binding_values_valid",
    "optional_authority_bindings_valid",
]
