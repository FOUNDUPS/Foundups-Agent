"""Fail-closed correspondence sender boundary.

This module is the mandatory seam between a recipient-preflight SEND receipt and
any repo-owned provider mutation. It deliberately accepts provider behavior as
injected callables so Gmail, Slack, or another correspondence adapter can share
the same boundary contract.

The boundary never infers authorization from a prompt, draft, prior send, cached
state, or a successful provider call. A fresh receipt must be bound to the exact
current transaction before provider invocation, and VERIFIED_SENT is only
returned after exact provider recipient read-back.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from hashlib import sha256
import json
from typing import Callable, Mapping, Sequence, TypeVar

from .reddog_recipient_preflight import (
    PreflightDecision,
    PreflightReceipt,
    ProposedRecipient,
    RecipientRole,
    normalize_address,
    verify_sent_readback,
)


class SenderBoundaryDecision(str, Enum):
    """Terminal result of one sender-boundary execution attempt."""

    BLOCK = "BLOCK"
    VERIFIED_SENT = "VERIFIED_SENT"
    PROVIDER_SENT_INTEGRITY_INCIDENT = "PROVIDER_SENT_INTEGRITY_INCIDENT"
    PROVIDER_STATE_UNKNOWN = "PROVIDER_STATE_UNKNOWN"


@dataclass(frozen=True)
class CorrespondenceTransaction:
    """Exact provider transaction that a preflight receipt authorizes."""

    provider: str
    purpose_scope: str
    recipients: tuple[ProposedRecipient, ...]
    content_digest: str
    provider_object_id: str | None = None
    thread_id: str | None = None


@dataclass(frozen=True)
class BoundPreflightReceipt:
    """Fresh SEND/BLOCK receipt bound to one exact transaction digest."""

    receipt: PreflightReceipt
    transaction_digest: str
    issued_at: str
    expires_at: str


@dataclass(frozen=True)
class ProviderSendResult:
    """Minimal provider identifiers returned after submission."""

    provider_message_id: str
    provider_thread_id: str | None = None


@dataclass(frozen=True)
class SenderBoundaryResult:
    """Machine-readable execution receipt for callers and persistence layers."""

    decision: SenderBoundaryDecision
    provider_invoked: bool
    reasons: tuple[str, ...]
    provider_result: ProviderSendResult | None = None


T = TypeVar("T")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def _parse_aware_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return _aware_utc(parsed)


def transaction_digest(transaction: CorrespondenceTransaction) -> str:
    """Return a deterministic digest for exact recipient/content/scope state."""

    recipients = sorted(
        (
            recipient.identity_id,
            recipient.role.value,
            normalize_address(recipient.address),
        )
        for recipient in transaction.recipients
    )
    payload = {
        "provider": transaction.provider,
        "purpose_scope": transaction.purpose_scope,
        "recipients": recipients,
        "content_digest": transaction.content_digest,
        "provider_object_id": transaction.provider_object_id,
        "thread_id": transaction.thread_id,
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(serialized.encode("utf-8")).hexdigest()


def bind_preflight_receipt(
    receipt: PreflightReceipt,
    transaction: CorrespondenceTransaction,
    *,
    issued_at: datetime,
    ttl_seconds: int = 300,
) -> BoundPreflightReceipt:
    """Bind a preflight receipt to one current transaction for a short window."""

    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")
    issued = _aware_utc(issued_at)
    expires = issued + timedelta(seconds=ttl_seconds)
    return BoundPreflightReceipt(
        receipt=receipt,
        transaction_digest=transaction_digest(transaction),
        issued_at=issued.isoformat(),
        expires_at=expires.isoformat(),
    )


def _validate_authorization(
    authorization: BoundPreflightReceipt | None,
    current: CorrespondenceTransaction,
    *,
    now: datetime,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if authorization is None:
        return ("MISSING_PREFLIGHT_RECEIPT",)

    if authorization.receipt.decision is not PreflightDecision.SEND:
        reasons.append("PREFLIGHT_NOT_SEND")

    try:
        issued = _parse_aware_utc(authorization.issued_at)
        expires = _parse_aware_utc(authorization.expires_at)
        observed_now = _aware_utc(now)
    except (TypeError, ValueError):
        reasons.append("INVALID_RECEIPT_TIME")
    else:
        if expires <= issued:
            reasons.append("INVALID_RECEIPT_WINDOW")
        if observed_now < issued:
            reasons.append("PREFLIGHT_NOT_YET_VALID")
        if observed_now > expires:
            reasons.append("STALE_PREFLIGHT_RECEIPT")

    if authorization.transaction_digest != transaction_digest(current):
        reasons.append("TRANSACTION_MISMATCH")

    return tuple(reasons)


def execute_sender_boundary(
    *,
    authorization: BoundPreflightReceipt | None,
    load_current_transaction: Callable[[], CorrespondenceTransaction],
    provider_send: Callable[[CorrespondenceTransaction], ProviderSendResult],
    provider_readback: Callable[
        [ProviderSendResult], Mapping[RecipientRole, Sequence[str]]
    ],
    now: datetime,
) -> SenderBoundaryResult:
    """Execute one provider mutation only after fail-closed boundary checks.

    The current transaction is loaded immediately before authorization so a
    changed draft/recipient set/content digest invalidates an older receipt.

    A provider exception is state-unknown, not permission to retry. Callers must
    reconcile provider Sent state before any later attempt.
    """

    if authorization is None:
        return SenderBoundaryResult(
            decision=SenderBoundaryDecision.BLOCK,
            provider_invoked=False,
            reasons=("MISSING_PREFLIGHT_RECEIPT",),
        )

    try:
        current = load_current_transaction()
    except Exception:
        return SenderBoundaryResult(
            decision=SenderBoundaryDecision.BLOCK,
            provider_invoked=False,
            reasons=("CURRENT_TRANSACTION_READ_FAILED",),
        )

    reasons = _validate_authorization(authorization, current, now=now)
    if reasons:
        return SenderBoundaryResult(
            decision=SenderBoundaryDecision.BLOCK,
            provider_invoked=False,
            reasons=reasons,
        )

    try:
        provider_result = provider_send(current)
    except Exception:
        return SenderBoundaryResult(
            decision=SenderBoundaryDecision.PROVIDER_STATE_UNKNOWN,
            provider_invoked=True,
            reasons=("PROVIDER_SEND_RAISED_RECONCILE_BEFORE_RETRY",),
        )

    try:
        actual = provider_readback(provider_result)
    except Exception:
        return SenderBoundaryResult(
            decision=SenderBoundaryDecision.PROVIDER_SENT_INTEGRITY_INCIDENT,
            provider_invoked=True,
            provider_result=provider_result,
            reasons=("PROVIDER_READBACK_FAILED",),
        )

    readback = verify_sent_readback(authorization.receipt, actual)
    if not readback.ok:
        return SenderBoundaryResult(
            decision=SenderBoundaryDecision.PROVIDER_SENT_INTEGRITY_INCIDENT,
            provider_invoked=True,
            provider_result=provider_result,
            reasons=readback.reasons,
        )

    return SenderBoundaryResult(
        decision=SenderBoundaryDecision.VERIFIED_SENT,
        provider_invoked=True,
        provider_result=provider_result,
        reasons=(),
    )
