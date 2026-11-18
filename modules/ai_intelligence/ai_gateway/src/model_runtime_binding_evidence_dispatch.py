"""Dispatch serialized SINGLE or PANEL model evidence to canonical verifiers."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)

from .model_intelligence_selection import SelectionMode
from .model_runtime_binding import ModelRuntimeBindingPolicy
from .model_runtime_binding_panel_rehydration import (
    rehydrate_verified_panel_evidence_bundle,
)
from .model_selection_artifact_supply import _rehydrate_verified_evidence_bundle
from .model_signed_evidence import ModelEvidenceKeyResolver


def rehydrate_verified_runtime_evidence(
    *,
    verified_evidence_bundle: Mapping[str, Any],
    snapshot: Any,
    selection: Any,
    policy: ModelRuntimeBindingPolicy,
    runtime_policy_payload: Mapping[str, Any],
    trusted_keys_payload: Mapping[str, Any],
    key_resolver: ModelEvidenceKeyResolver,
    signature_verifier: SignatureVerifier,
    now: int,
) -> Any:
    revoked = _revoked_epochs(trusted_keys_payload, "revoked_key_epochs")
    if selection.requirements.selection_mode == SelectionMode.PANEL:
        evidence = rehydrate_verified_panel_evidence_bundle(
            verified_evidence_bundle,
            catalog_snapshot=snapshot,
            selection_receipt=selection,
            runtime_policy=policy,
            context_receipt_ids=_panel_context_ids(runtime_policy_payload),
            key_resolver=key_resolver,
            signature_verifier=signature_verifier,
            now=now,
            revoked_member_key_epochs=_revoked_epochs(
                trusted_keys_payload, "revoked_member_key_epochs", revoked
            ),
            revoked_panel_key_epochs=_revoked_epochs(
                trusted_keys_payload, "revoked_panel_key_epochs", revoked
            ),
        )
    else:
        evidence = _rehydrate_verified_evidence_bundle(
            verified_evidence_bundle,
            key_resolver=key_resolver,
            signature_verifier=signature_verifier,
            now=now,
            consume_nonces=False,
            revoked_key_epochs=revoked,
        )
    return evidence


def _panel_context_ids(value: Mapping[str, Any]) -> Mapping[str, Any]:
    result = value.get("panel_context_receipt_ids")
    if not isinstance(result, Mapping):
        raise ValueError("panel_context_receipt_ids_missing")
    return result


def _revoked_epochs(
    value: Mapping[str, Any],
    name: str,
    fallback: tuple[str, ...] = (),
) -> tuple[str, ...]:
    raw = value.get(name)
    if raw is None:
        return fallback
    if not isinstance(raw, (list, tuple)):
        raise ValueError(f"{name}_invalid")
    result = tuple(str(item).strip() for item in raw)
    if any(not item for item in result) or len(result) != len(set(result)):
        raise ValueError(f"{name}_invalid")
    return result


__all__ = [
    "rehydrate_verified_runtime_evidence",
]
