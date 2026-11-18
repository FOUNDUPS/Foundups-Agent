"""Digest-bound recovery admission for signed AgentDB task publication."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_signed_worker_dispatch_runtime_types import (
    SignedWorkerDispatchRuntimeReceipt,
    SignedWorkerDispatchTaskSpec,
    canonical_digest,
)


@dataclass(frozen=True)
class SignedWorkerPublicationAdmission:
    """One nonce and digest authorized for an idempotent task publication."""

    nonce: str
    binding_digest: str
    status: str
    recovering: bool


def prepare_signed_worker_publication(
    *,
    nonce_store: Any,
    work_authority: Mapping[str, Any],
    tasks: Sequence[SignedWorkerDispatchTaskSpec],
    receipt: SignedWorkerDispatchRuntimeReceipt,
) -> SignedWorkerPublicationAdmission | None:
    """Reserve and authorize one exact publication, or fail closed."""

    nonce = str(work_authority.get("nonce") or "")
    receipt_binding = receipt.to_dict()
    for field in ("created_at", "receipt_id", "receipt_digest"):
        receipt_binding.pop(field, None)
    binding_digest = canonical_digest(
        {
            "work_authority": dict(work_authority),
            "tasks": [task.to_dict() for task in tasks],
            "receipt": receipt_binding,
        }
    )
    if not nonce:
        return None
    reserved = advance_signed_worker_publication_state(
        nonce_store, nonce, binding_digest, "RESERVED"
    )
    if reserved not in {"RESERVED", "AUTHORIZED", "APPLIED"}:
        return None
    authorized = reserved
    if reserved != "APPLIED":
        authorized = advance_signed_worker_publication_state(
            nonce_store, nonce, binding_digest, "AUTHORIZED"
        )
        if authorized != "AUTHORIZED":
            return None
    return SignedWorkerPublicationAdmission(
        nonce=nonce,
        binding_digest=binding_digest,
        status=authorized,
        recovering=reserved != "RESERVED",
    )


def complete_signed_worker_publication(
    nonce_store: Any,
    admission: SignedWorkerPublicationAdmission,
) -> bool:
    """Mark an exact publication applied after AgentDB confirms the batch."""

    return advance_signed_worker_publication_state(
        nonce_store,
        admission.nonce,
        admission.binding_digest,
        "APPLIED",
    ) == "APPLIED"


def advance_signed_worker_publication_state(
    nonce_store: Any,
    nonce: str,
    binding_digest: str,
    target_status: str,
) -> str:
    operation = getattr(nonce_store, "advance_publication", None)
    if not callable(operation):
        return ""
    try:
        return str(operation(nonce, binding_digest, target_status) or "")
    except Exception:
        return ""


__all__ = [
    "SignedWorkerPublicationAdmission",
    "advance_signed_worker_publication_state",
    "complete_signed_worker_publication",
    "prepare_signed_worker_publication",
]
