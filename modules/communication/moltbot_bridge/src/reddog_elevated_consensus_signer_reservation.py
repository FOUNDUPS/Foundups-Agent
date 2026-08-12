"""Opaque signer-side reservation for one elevated consensus child nonce."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_capability import (
    ConsensusNonceAuthority,
)


class VerifiedElevatedConsensusSignerReservation:
    """Opaque nonce reservation committed only after an accepted signature."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *_args: Any, **_kwargs: Any):
        raise TypeError("elevated_consensus_reservation_construction_forbidden")

    def __copy__(self) -> Any:
        raise TypeError("elevated_consensus_reservation_copy_forbidden")

    def __deepcopy__(self, _memo: Any) -> Any:
        raise TypeError("elevated_consensus_reservation_copy_forbidden")

    def __reduce__(self) -> Any:
        raise TypeError("elevated_consensus_reservation_pickle_forbidden")


@dataclass(frozen=True, slots=True)
class _ReservationSeal:
    authority: ConsensusNonceAuthority
    token: str


_LOCK = threading.Lock()
_RESERVATIONS: WeakKeyDictionary[
    VerifiedElevatedConsensusSignerReservation, _ReservationSeal
] = WeakKeyDictionary()


def reserve_elevated_consensus_nonce(
    authority: ConsensusNonceAuthority,
    nonce: str,
    *,
    expires_at: int,
    subject: str,
) -> VerifiedElevatedConsensusSignerReservation | None:
    token = authority.reserve(nonce, expires_at=expires_at, subject=subject)
    if not token:
        return None
    reservation = object.__new__(VerifiedElevatedConsensusSignerReservation)
    with _LOCK:
        _RESERVATIONS[reservation] = _ReservationSeal(authority, token)
    return reservation


def commit_elevated_consensus_nonce(reservation: Any) -> bool:
    seal = _take(reservation)
    if seal is None:
        return False
    try:
        seal.authority.commit(seal.token)
        return True
    except Exception:
        _rollback_seal(seal)
        return False


def rollback_elevated_consensus_nonce(reservation: Any) -> None:
    seal = _take(reservation)
    if seal is not None:
        _rollback_seal(seal)


def _take(reservation: Any) -> _ReservationSeal | None:
    if type(reservation) is not VerifiedElevatedConsensusSignerReservation:
        return None
    with _LOCK:
        return _RESERVATIONS.pop(reservation, None)


def _rollback_seal(seal: _ReservationSeal) -> None:
    try:
        seal.authority.rollback(seal.token)
    except Exception:
        pass


__all__ = [
    "VerifiedElevatedConsensusSignerReservation",
    "commit_elevated_consensus_nonce",
    "reserve_elevated_consensus_nonce",
    "rollback_elevated_consensus_nonce",
]
