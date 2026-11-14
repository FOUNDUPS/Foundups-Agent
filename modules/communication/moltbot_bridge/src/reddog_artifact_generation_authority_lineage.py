"""Independent model-authority lineage checks for artifact generation."""

from __future__ import annotations

import hmac
from typing import Any, Mapping

from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import (
    SelectionDecision,
    SelectionPurpose,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    VerifiedRuntimeBindingCapability,
    canonical_model_runtime_binding_digest,
    verification_receipt_digest,
    verified_runtime_binding_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    rehydrate_model_selection_receipt,
)

from .reddog_artifact_generation_model_binding import artifact_generation_digest


def validated_model_authority_lineage(
    *,
    receipt: Any,
    binding: Mapping[str, Any],
    signed_authority: Mapping[str, Any],
    selection: Mapping[str, Any],
    capability: VerifiedRuntimeBindingCapability | None,
) -> tuple[Any, Any] | None:
    """Return selection and verification only when all signed lineage agrees."""

    verification = verified_runtime_binding_receipt(binding)
    try:
        selected = rehydrate_model_selection_receipt(selection)
    except Exception:
        return None
    if verification is None or not _selection_matches_runtime(selected, receipt):
        return None
    expected = _expected_authority_values(
        receipt, selected, selection, verification, signed_authority
    )
    if type(capability) is not VerifiedRuntimeBindingCapability:
        return None
    return (selected, verification) if all(_matches(*pair) for pair in expected) else None


def _selection_matches_runtime(selection: Any, runtime: Any) -> bool:
    return (
        selection.decision == SelectionDecision.SELECTED
        and selection.requirements.purpose == SelectionPurpose.PRODUCTION
        and selection.receipt_id == runtime.selection_receipt_id
        and tuple(selection.selected_model_ids)
        == (str(runtime.principal_model or ""), *tuple(runtime.panel_models))
        and _selection_roles(selection) == _runtime_roles(runtime)
    )


def _expected_authority_values(
    runtime: Any,
    selection_receipt: Any,
    selection: Mapping[str, Any],
    verification: Any,
    authority: Mapping[str, Any],
) -> tuple[tuple[Any, Any], ...]:
    return (
        (runtime.receipt_id, authority.get("model_runtime_binding_receipt_id")),
        (
            canonical_model_runtime_binding_digest(runtime),
            authority.get("model_runtime_binding_digest"),
        ),
        (
            selection_receipt.receipt_id,
            authority.get("model_selection_receipt_id"),
        ),
        (artifact_generation_digest(selection), authority.get("model_selection_digest")),
        (
            verification.receipt_id,
            authority.get("model_runtime_binding_verification_receipt_id"),
        ),
        (
            verification_receipt_digest(verification),
            authority.get("model_runtime_binding_verification_digest"),
        ),
    )


def _matches(actual: Any, trusted: Any) -> bool:
    return (
        isinstance(actual, str)
        and bool(actual)
        and isinstance(trusted, str)
        and hmac.compare_digest(actual, trusted)
    )


def _selection_roles(receipt: Any) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (item.role, item.canonical_model_id, item.provider)
        for item in receipt.role_assignments
    )


def _runtime_roles(receipt: Any) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (item.role, item.model_id, item.provider)
        for item in receipt.role_bindings
    )


__all__ = ["validated_model_authority_lineage"]
