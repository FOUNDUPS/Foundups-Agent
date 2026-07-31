"""Factory-issued public-key verifier authority for signer generations."""

from __future__ import annotations

import hashlib
import threading
from typing import Any, Protocol
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    decode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    SignerRuntimeGenerationVerifier,
)


class SignerRuntimeGenerationVerifierAuthorityBoundary(Protocol):
    def require(self, value: object) -> SignerRuntimeGenerationVerifier: ...


def _build_private_registry():
    lock = threading.RLock()
    records: WeakKeyDictionary[object, Any] = WeakKeyDictionary()

    def issue(key: object, value: Any) -> None:
        with lock:
            if key in records:
                raise ValueError("generation_verifier_handle_already_issued")
            records[key] = value

    def lookup(key: object) -> Any:
        with lock:
            try:
                return records[key]
            except KeyError as exc:
                raise ValueError("generation_verifier_handle_unverified") from exc

    return issue, lookup


_issue_verifier_target, _lookup_verifier_target = _build_private_registry()
_issue_verifier_authority, _lookup_verifier_authority = (
    _build_private_registry()
)
del _build_private_registry


class _PublicGenerationVerifier:
    __slots__ = ("authenticator_id", "_public_key")

    def __init__(self, public_key: str) -> None:
        decoded = decode_ed25519_public_key(public_key)
        if decoded is None:
            raise ValueError("generation_verifier_public_key_invalid")
        self._public_key = public_key
        self.authenticator_id = (
            "ed25519-generation:"
            + hashlib.sha256(decoded).hexdigest()
        )

    def verify(self, payload: bytes, authentication_tag: str) -> bool:
        try:
            signing_input = payload.decode("ascii")
        except (AttributeError, UnicodeDecodeError):
            return False
        return Ed25519SignatureVerifier().verify(
            self._public_key,
            signing_input,
            authentication_tag,
        )


class _VerifierHandle:
    __slots__ = ("__weakref__",)

    @property
    def authenticator_id(
        self, _lookup: Any = _lookup_verifier_target
    ) -> str:
        return _lookup(self).authenticator_id

    def verify(
        self,
        payload: bytes,
        authentication_tag: str,
        _lookup: Any = _lookup_verifier_target,
    ) -> bool:
        return _lookup(self).verify(payload, authentication_tag)


class _VerifierAuthorityBoundary:
    __slots__ = ("__weakref__",)

    def require(
        self,
        value: object,
        _lookup: Any = _lookup_verifier_authority,
    ) -> SignerRuntimeGenerationVerifier:
        authority, verifier = _lookup(self)
        if value is not authority:
            raise ValueError("generation_verifier_authority_unverified")
        return verifier


def create_signer_runtime_generation_verifier_authority(
    public_key: str,
    _issue_target: Any = _issue_verifier_target,
    _issue_authority: Any = _issue_verifier_authority,
) -> tuple[object, SignerRuntimeGenerationVerifierAuthorityBoundary]:
    """Mint one process-local authority around public verification material."""

    target = _PublicGenerationVerifier(public_key)
    verifier = _VerifierHandle()
    _issue_target(verifier, target)
    authority = object()
    boundary = _VerifierAuthorityBoundary()
    _issue_authority(boundary, (authority, verifier))
    return authority, boundary


def require_signer_runtime_generation_verifier_authority(
    authority: object,
    boundary: SignerRuntimeGenerationVerifierAuthorityBoundary,
) -> SignerRuntimeGenerationVerifier:
    if type(boundary) is not _VerifierAuthorityBoundary:
        raise ValueError("generation_verifier_boundary_invalid")
    return boundary.require(authority)


del _lookup_verifier_authority, _lookup_verifier_target
del _issue_verifier_authority, _issue_verifier_target


__all__ = [
    "SignerRuntimeGenerationVerifierAuthorityBoundary",
    "create_signer_runtime_generation_verifier_authority",
    "require_signer_runtime_generation_verifier_authority",
]
