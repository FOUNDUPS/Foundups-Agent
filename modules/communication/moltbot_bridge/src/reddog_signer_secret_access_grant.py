"""Authenticated one-shot E0 signer secret-access grant boundary."""

from __future__ import annotations

import threading
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant_contract import (
    ExpectedSignerSecretGrantBinding,
    GRANT_PREFIX,
    GRANT_SCHEMA,
    MAX_GRANT_TTL_SECONDS,
    REJECT_BINDING,
    REJECT_CAPABILITY,
    REJECT_DIGEST,
    REJECT_GRANT_ID,
    REJECT_ISSUER,
    REJECT_MALFORMED,
    REJECT_NONCE,
    REJECT_NON_ASCII,
    REJECT_REVOKED,
    REJECT_SIGNATURE,
    REJECT_TIME,
    SignerSecretAccessGrantRejected,
    canonical_signer_secret_access_grant_input,
    signer_secret_access_grant_id,
    validated_signer_secret_grant,
    verify_expected_signer_secret_grant,
    verify_signer_secret_grant_issuer,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    NonceStore,
    PrincipalKeyResolver,
    SignatureVerifier,
    constant_time_compare,
)


class SignerSecretGrantRevocationOracle(Protocol):
    def is_revoked(
        self, *, grant_id: str, key_epoch: str, at_epoch: int
    ) -> bool: ...


class SignerSecretAccessGrantBoundary:
    """Process-local issuer and one-shot consumer for verified grants."""

    def __init__(
        self,
        *,
        nonce_store: NonceStore,
        revocation_oracle: SignerSecretGrantRevocationOracle,
        clock: Callable[[], int],
    ) -> None:
        self._seal = object()
        self._capability_type = _capability_type(self._seal)
        self._issued: WeakKeyDictionary[object, Mapping[str, Any]] = WeakKeyDictionary()
        self._lock = threading.Lock()
        self._nonce_store = nonce_store
        self._revocation_oracle = revocation_oracle
        self._clock = clock

    def verify(
        self, grant: Mapping[str, Any], *, expected: ExpectedSignerSecretGrantBinding,
        signature_verifier: SignatureVerifier, principal_key_resolver: PrincipalKeyResolver,
    ) -> object:
        raw = validated_signer_secret_grant(grant, self._now())
        if not constant_time_compare(
            str(raw["grant_id"]), signer_secret_access_grant_id(raw)
        ):
            raise SignerSecretAccessGrantRejected(REJECT_GRANT_ID)
        verify_expected_signer_secret_grant(raw, expected)
        verify_signer_secret_grant_issuer(raw, principal_key_resolver)
        try:
            valid = signature_verifier.verify(
                str(raw["issuer_public_key"]),
                canonical_signer_secret_access_grant_input(raw), str(raw["signature"]),
            ) is True
        except Exception:
            valid = False
        if not valid:
            raise SignerSecretAccessGrantRejected(REJECT_SIGNATURE)
        self._require_not_revoked(raw)
        values = MappingProxyType(dict(raw))
        capability = self._capability_type()
        with self._lock:
            self._issued[capability] = values
        return capability

    def consume(self, capability: object) -> Mapping[str, Any]:
        if not isinstance(capability, self._capability_type):
            raise SignerSecretAccessGrantRejected(REJECT_CAPABILITY)
        with self._lock:
            expected = self._issued.pop(capability, None)
        if expected is None or getattr(capability, "_seal", None) is not self._seal:
            raise SignerSecretAccessGrantRejected(REJECT_CAPABILITY)
        validated_signer_secret_grant(expected, self._now())
        self._require_not_revoked(expected)
        try:
            consumed = self._nonce_store.consume(str(expected["nonce"])) is True
        except Exception:
            consumed = False
        if not consumed:
            raise SignerSecretAccessGrantRejected(REJECT_NONCE)
        return expected

    def _now(self) -> int:
        try:
            value = self._clock()
        except Exception:
            raise SignerSecretAccessGrantRejected(REJECT_TIME) from None
        if type(value) is not int:
            raise SignerSecretAccessGrantRejected(REJECT_TIME)
        return value

    def _require_not_revoked(self, grant: Mapping[str, Any]) -> None:
        try:
            verdict = self._revocation_oracle.is_revoked(
                grant_id=str(grant["grant_id"]),
                key_epoch=str(grant["key_epoch"]),
                at_epoch=self._now(),
            )
        except Exception:
            raise SignerSecretAccessGrantRejected(REJECT_REVOKED) from None
        if type(verdict) is not bool or verdict is not False:
            raise SignerSecretAccessGrantRejected(REJECT_REVOKED)


def _capability_type(seal: object) -> type:
    class Capability:
        __slots__ = ("_seal", "__weakref__")

        def __init__(self) -> None:
            object.__setattr__(self, "_seal", seal)

        def __setattr__(self, _name: str, _value: Any) -> None:
            raise TypeError(REJECT_CAPABILITY)

        def __copy__(self):
            raise TypeError(REJECT_CAPABILITY)

        def __deepcopy__(self, _memo: Any):
            raise TypeError(REJECT_CAPABILITY)

        def __reduce__(self):
            raise TypeError(REJECT_CAPABILITY)

    return Capability
__all__ = [
    "ExpectedSignerSecretGrantBinding", "GRANT_PREFIX", "GRANT_SCHEMA",
    "MAX_GRANT_TTL_SECONDS", "SignerSecretAccessGrantBoundary",
    "SignerSecretGrantRevocationOracle",
    "SignerSecretAccessGrantRejected", "canonical_signer_secret_access_grant_input",
    "signer_secret_access_grant_id",
]
