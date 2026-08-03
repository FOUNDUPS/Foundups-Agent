"""Authenticated one-shot E0 signer secret-access grant boundary."""

from __future__ import annotations

import threading
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol, TypeVar
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant_contract import (
    ExpectedSignerSecretGrantBinding,
    GRANT_PREFIX,
    GRANT_SCHEMA,
    MAX_GRANT_TTL_SECONDS,
    REJECT_BINDING as REJECT_BINDING,
    REJECT_CAPABILITY,
    REJECT_DIGEST as REJECT_DIGEST,
    REJECT_GRANT_ID,
    REJECT_ISSUER as REJECT_ISSUER,
    REJECT_MALFORMED as REJECT_MALFORMED,
    REJECT_NONCE,
    REJECT_NON_ASCII as REJECT_NON_ASCII,
    REJECT_REVOKED,
    REJECT_SIGNATURE,
    REJECT_TIME,
    SignerSecretAccessGrantRejected,
    canonical_signer_secret_access_grant_input,
    signer_secret_access_grant_id,
    signer_secret_access_request_digest,
    validated_signer_secret_grant,
    verify_expected_signer_secret_grant,
    verify_signer_secret_grant_issuer,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_nonce_store import (
    DurableSignerSecretGrantNonceStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_oracle import (
    AtomicSignerSecretGrantRevocationOracle,
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

    def authorize_use(
        self,
        *,
        grant_id: str,
        key_epoch: str,
        at_epoch: int,
        action: Callable[[], "_T"],
    ) -> "_T": ...


_T = TypeVar("_T")


class SignerSecretAccessGrantBoundary:
    """Process-local capabilities backed by injected nonce durability."""

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

    def replay_store_matches(self, expected: ExpectedSignerSecretGrantBinding) -> bool:
        store = self._nonce_store
        return bool(
            type(store) is DurableSignerSecretGrantNonceStore
            and _same(store.replay_store_binding_digest,
                      expected.replay_store_binding_digest)
            and _same(store.replay_store_id, expected.replay_store_id)
            and _same(store.durability_receipt_id,
                      expected.replay_store_durability_receipt_id)
            and _same(store.replay_store_instance_digest,
                      expected.replay_store_instance_digest)
        )

    @property
    def atomic_revocation(self) -> bool:
        return type(self._revocation_oracle) is AtomicSignerSecretGrantRevocationOracle

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
        if type(self._nonce_store) is DurableSignerSecretGrantNonceStore:
            consumed = self._nonce_store.consume_grant(expected)
        else:
            try:
                consumed = self._nonce_store.consume(str(expected["nonce"])) is True
            except Exception:
                consumed = False
        if not consumed:
            raise SignerSecretAccessGrantRejected(REJECT_NONCE)
        return expected

    def authorize_consumed_use(
        self, grant: Mapping[str, Any], action: Callable[[], _T]
    ) -> _T:
        """Execute one sign under the revocation authority's atomic fence."""
        validated = validated_signer_secret_grant(grant, self._now())
        if not self.atomic_revocation:
            raise SignerSecretAccessGrantRejected(REJECT_REVOKED)

        def checked_action() -> _T:
            result = action()
            validated_signer_secret_grant(validated, self._now())
            return result

        try:
            return self._revocation_oracle.authorize_use(
                grant_id=str(validated["grant_id"]),
                key_epoch=str(validated["key_epoch"]),
                at_epoch=self._now(),
                action=checked_action,
            )
        except SignerSecretAccessGrantRejected:
            raise
        except Exception:
            raise SignerSecretAccessGrantRejected(REJECT_REVOKED) from None

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


def _same(left: object, right: str) -> bool:
    return type(left) is str and type(right) is str and constant_time_compare(left, right)
__all__ = [
    "ExpectedSignerSecretGrantBinding", "GRANT_PREFIX", "GRANT_SCHEMA",
    "MAX_GRANT_TTL_SECONDS", "SignerSecretAccessGrantBoundary",
    "SignerSecretGrantRevocationOracle",
    "SignerSecretAccessGrantRejected", "canonical_signer_secret_access_grant_input",
    "signer_secret_access_grant_id",
    "signer_secret_access_request_digest",
]
