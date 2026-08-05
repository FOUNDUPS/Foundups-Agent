"""Fail-closed placeholder for externally issued effect authority.

Current-generation integrity is audit evidence, not work authority. A live
lease must eventually come from the isolated signer peer boundary; this module
therefore exposes validation hooks but deliberately has no local issuer.
"""

from __future__ import annotations

from typing import Any


class AuthoritativeUseLease:
    """Unconstructible marker reserved for the external signer integration."""

    __slots__ = ()

    def __new__(cls, *_args: Any, **_kwargs: Any):
        raise TypeError("external_authoritative_use_lease_issuer_required")

    @property
    def expires_at_epoch(self) -> int:
        raise ValueError("external_authoritative_use_lease_unavailable")

    def consume(self) -> bool:
        return False


def is_authoritative_use_lease(_value: Any) -> bool:
    """Reject until a peer-authenticated external issuer is integrated."""

    return False


def consume_authoritative_use_lease(_value: Any) -> bool:
    return False


__all__ = [
    "AuthoritativeUseLease",
    "consume_authoritative_use_lease",
    "is_authoritative_use_lease",
]
