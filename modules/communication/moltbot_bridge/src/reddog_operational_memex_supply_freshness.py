"""Bounded freshness policy for operational Memex supply receipts."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


DEFAULT_MAX_AGE_SECONDS = 300
DEFAULT_MAX_TTL_SECONDS = 600


class MemexSupplyPolicyWindow(Protocol):
    policy_issued_at: str
    policy_expires_at: str


def validate_operational_memex_supply_freshness(
    receipt: MemexSupplyPolicyWindow,
    *,
    now_iso: str,
    max_age_seconds: int,
    max_ttl_seconds: int,
) -> None:
    """Reject stale, overlong, timezone-ambiguous policy windows."""

    if type(max_age_seconds) is not int or max_age_seconds <= 0:
        raise ValueError("memex_supply_receipt_max_age_invalid")
    if type(max_ttl_seconds) is not int or max_ttl_seconds <= 0:
        raise ValueError("memex_supply_receipt_max_ttl_invalid")
    try:
        issued = _parse(receipt.policy_issued_at)
        expires = _parse(receipt.policy_expires_at)
        now = _parse(now_iso)
    except (TypeError, ValueError):
        raise ValueError("memex_supply_receipt_time_invalid") from None
    if issued > now or expires <= now or expires <= issued:
        raise ValueError("memex_supply_receipt_expired")
    if (now - issued).total_seconds() > max_age_seconds:
        raise ValueError("memex_supply_receipt_too_old")
    if (expires - issued).total_seconds() > max_ttl_seconds:
        raise ValueError("memex_supply_receipt_ttl_exceeded")


def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("memex_supply_receipt_time_timezone_missing")
    return parsed


__all__ = [
    "DEFAULT_MAX_AGE_SECONDS",
    "DEFAULT_MAX_TTL_SECONDS",
    "MemexSupplyPolicyWindow",
    "validate_operational_memex_supply_freshness",
]
