"""Signer-owned atomic revocation fence for one secret-grant use."""

from __future__ import annotations

import threading
from typing import Callable, TypeVar

_T = TypeVar("_T")


class AtomicSignerSecretGrantRevocationOracle:
    """Linearize revocation updates with the complete signing callback."""

    def __init__(
        self,
        *,
        revoked_grant_ids: frozenset[str] = frozenset(),
        revoked_key_epochs: frozenset[str] = frozenset(),
    ) -> None:
        self._revoked_grant_ids = set(revoked_grant_ids)
        self._revoked_key_epochs = set(revoked_key_epochs)
        self._lock = threading.RLock()

    def is_revoked(
        self, *, grant_id: str, key_epoch: str, at_epoch: int
    ) -> bool:
        del at_epoch
        with self._lock:
            return self._is_revoked(grant_id, key_epoch)

    def authorize_use(
        self,
        *,
        grant_id: str,
        key_epoch: str,
        at_epoch: int,
        action: Callable[[], _T],
    ) -> _T:
        del at_epoch
        with self._lock:
            if self._is_revoked(grant_id, key_epoch):
                raise RuntimeError("signer_secret_grant_revoked")
            result = action()
            if self._is_revoked(grant_id, key_epoch):
                raise RuntimeError("signer_secret_grant_revoked")
            return result

    def replace_revocations(
        self,
        *,
        revoked_grant_ids: frozenset[str],
        revoked_key_epochs: frozenset[str],
    ) -> None:
        with self._lock:
            self._revoked_grant_ids = set(revoked_grant_ids)
            self._revoked_key_epochs = set(revoked_key_epochs)

    def revoke_grant(self, grant_id: str) -> None:
        with self._lock:
            self._revoked_grant_ids.add(grant_id)

    def revoke_key_epoch(self, key_epoch: str) -> None:
        with self._lock:
            self._revoked_key_epochs.add(key_epoch)

    def _is_revoked(self, grant_id: str, key_epoch: str) -> bool:
        return (
            grant_id in self._revoked_grant_ids
            or key_epoch in self._revoked_key_epochs
        )


__all__ = ["AtomicSignerSecretGrantRevocationOracle"]
