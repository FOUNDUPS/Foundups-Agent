"""Optional receipt bindings carried by signed delegated authority."""

from __future__ import annotations

from typing import Any

_OPTIONAL_BINDING_FIELDS = (
    ("model_selection_receipt_id", "model_selection_digest"),
    ("memex_supply_receipt_id", "memex_supply_digest"),
    (
        "architect_fix_publication_receipt_id",
        "architect_fix_publication_binding_digest",
    ),
)


def optional_authority_bindings_valid(request: Any) -> bool:
    """Require paired receipt IDs and SHA-256 digests."""

    for receipt_field, digest_field in _OPTIONAL_BINDING_FIELDS:
        receipt_id = getattr(request, receipt_field)
        digest = getattr(request, digest_field)
        if bool(receipt_id) != bool(digest):
            return False
        if digest and not str(digest).startswith("sha256:"):
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
    "optional_authority_bindings_valid",
]
