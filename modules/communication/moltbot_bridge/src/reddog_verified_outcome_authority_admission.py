"""Lazy admission for the verified-outcome signer dependency."""

from __future__ import annotations

from typing import Callable

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VerifiedOutcomeSigningAuthority,
)

VerifiedOutcomeAuthoritySupplier = Callable[[], VerifiedOutcomeSigningAuthority]


def admit_verified_outcome_authority(
    policy: object | None,
    authority: VerifiedOutcomeSigningAuthority | None,
    supplier: VerifiedOutcomeAuthoritySupplier | None,
) -> VerifiedOutcomeSigningAuthority | None:
    """Resolve root authority only for a configured outcome policy."""

    if policy is None:
        return None
    if authority is not None:
        return authority
    if supplier is None:
        return None
    try:
        return supplier()
    except Exception:
        return None


__all__ = ["admit_verified_outcome_authority"]
