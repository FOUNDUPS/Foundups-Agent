"""Canonical signed-authority binding for RedDog worker dispatch."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    WorkAuthorityVerificationPhase,
    verify_delegated_work_authority,
)

AUTHORITY_VERIFICATION_BINDING_SCHEMA = (
    "reddog_worker_dispatch_authority_verification_binding.v1"
)

_AUTHORITY_RUNTIME_ACCEPT = "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT"
_AUTHORITY_VERIFICATION_ACCEPT = "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT"
_AUTHORITY_ISSUED = "DELEGATED_AUTHORITY_ISSUED"
_SIGNED_EFFECT_FIELDS = (
    "work_order_id", "foundup_id", "requested_operation",
    "wsp15_allocation_receipt_id", "wsp15_allocation_digest", "wsp15_priority",
    "wsp15_mps_total", "wsp15_reasoning_tier", "model_runtime_binding_receipt_id",
    "model_runtime_binding_digest", "architect_fix_publication_receipt_id",
    "architect_fix_publication_binding_digest",
)


@dataclass(frozen=True)
class WorkerDispatchAuthorityVerificationContext:
    """Configured use-time dependencies for worker-dispatch authority admission."""
    signature_verifier: Any
    principal_key_resolver: Any
    nonce_store: Any
    snapshot_resolver: Any
    revocation_oracle: Any
    trusted_now_epoch: Callable[[], int]
    required_valve_state: str
    forbidden_operations: tuple[str, ...] = ()
    revoked_key_epochs: tuple[str, ...] = ()
    leeway_s: int = 60


def recorded_authority_verification_binding(
    authority_runtime_result: Mapping[str, Any],
    authority_verification_result: Mapping[str, Any],
) -> Mapping[str, str]:
    """Recompute the dispatch proof from recorded authority and verification stages."""
    runtime = _mapping(authority_runtime_result)
    verification = _mapping(authority_verification_result)
    authority = _mapping(runtime.get("authority_result"))
    signer_receipt = _mapping(authority.get("receipt"))
    work_authority = _mapping(authority.get("work_authority"))
    verified_result = _mapping(verification.get("verification_result"))
    if (
        runtime.get("decision") != _AUTHORITY_RUNTIME_ACCEPT
        or authority.get("accepted") is not True
        or signer_receipt.get("status") != _AUTHORITY_ISSUED
        or verification.get("decision") != _AUTHORITY_VERIFICATION_ACCEPT
        or verified_result.get("accepted") is not True
        or not work_authority
    ):
        return {}

    authority_digest = _digest(work_authority)
    if (
        signer_receipt.get("work_authority_digest") != authority_digest
        or verification.get("verified_work_authority_digest") != authority_digest
    ):
        return {}

    seed = {
        "schema_version": AUTHORITY_VERIFICATION_BINDING_SCHEMA,
        "authority_receipt_id": str(signer_receipt.get("receipt_id") or ""),
        "verified_work_authority_digest": authority_digest,
        "verification_result_digest": _digest(verified_result),
        "work_order_id": str(work_authority.get("work_order_id") or ""),
    }
    if not seed["authority_receipt_id"] or not seed["work_order_id"]:
        return {}
    receipt_id = "reddog_authority_verification:" + _digest(seed)[7:23]
    binding = {
        **seed,
        "authority_verification_receipt_id": receipt_id,
    }
    return {
        "verified_work_authority_digest": authority_digest,
        "authority_verification_receipt_id": receipt_id,
        "authority_verification_receipt_digest": _digest(binding),
    }


def authority_verification_binding_matches(
    candidate: Mapping[str, Any],
    expected: Mapping[str, str],
) -> bool:
    """Require every persisted proof field to equal the recomputed binding."""

    return bool(expected) and all(
        hmac.compare_digest(str(candidate.get(key) or ""), value)
        for key, value in expected.items()
    )


def authenticated_recorded_authority_binding(
    *,
    context: WorkerDispatchAuthorityVerificationContext,
    authority_runtime_result: Mapping[str, Any],
    authority_verification_result: Mapping[str, Any],
    dryrun_receipt: Mapping[str, Any],
) -> Mapping[str, str]:
    """Reverify the signed authority at the writer boundary and bind its lineage."""

    expected = recorded_authority_verification_binding(
        authority_runtime_result,
        authority_verification_result,
    )
    if not (
        authority_verification_binding_matches(
            authority_verification_result,
            expected,
        )
        and authority_verification_binding_matches(dryrun_receipt, expected)
    ):
        return {}
    authority = _mapping(
        _mapping(authority_runtime_result).get("authority_result")
    )
    work_authority = _mapping(authority.get("work_authority"))
    if not _signed_effect_matches(work_authority, dryrun_receipt):
        return {}
    return expected if _authoritative_preflight_accepted(context, authority) else {}


def _signed_effect_matches(
    work_authority: Mapping[str, Any],
    dryrun_receipt: Mapping[str, Any],
) -> bool:
    return bool(work_authority) and all(
        hmac.compare_digest(
            str(work_authority.get(field) or ""),
            str(dryrun_receipt.get(field) or ""),
        )
        for field in _SIGNED_EFFECT_FIELDS
    )


def _authoritative_preflight_accepted(
    context: WorkerDispatchAuthorityVerificationContext,
    authority: Mapping[str, Any],
) -> bool:
    try:
        fresh_now_epoch = int(context.trusted_now_epoch())
        verification = verify_delegated_work_authority(
            work_authority=_mapping(authority.get("work_authority")),
            identity=_mapping(authority.get("identity")),
            signature_verifier=context.signature_verifier,
            principal_key_resolver=context.principal_key_resolver,
            nonce_store=context.nonce_store,
            snapshot_resolver=context.snapshot_resolver,
            revocation_oracle=context.revocation_oracle,
            now=fresh_now_epoch,
            required_valve_state=context.required_valve_state,
            forbidden_operations=context.forbidden_operations,
            revoked_key_epochs=context.revoked_key_epochs,
            leeway_s=context.leeway_s,
            verification_phase=WorkAuthorityVerificationPhase.PREFLIGHT_NON_CONSUMING,
        )
    except Exception:
        return False
    return verification.accepted is True


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    return value if isinstance(value, Mapping) else {}
def _digest(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
__all__ = [
    "AUTHORITY_VERIFICATION_BINDING_SCHEMA",
    "WorkerDispatchAuthorityVerificationContext",
    "authenticated_recorded_authority_binding",
    "authority_verification_binding_matches",
    "recorded_authority_verification_binding",
]
