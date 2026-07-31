"""Factory-issued public-key verifier authority for signer generations."""

from __future__ import annotations

import hashlib
from typing import Protocol
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
    def authenticator_id(self) -> str:
        return _VERIFIER_TARGETS[self].authenticator_id

    def verify(self, payload: bytes, authentication_tag: str) -> bool:
        return _VERIFIER_TARGETS[self].verify(payload, authentication_tag)


class _VerifierAuthorityBoundary:
    __slots__ = ("__weakref__",)

    def require(self, value: object) -> SignerRuntimeGenerationVerifier:
        authority, verifier = _VERIFIER_AUTHORITIES[self]
        if value is not authority:
            raise ValueError("generation_verifier_authority_unverified")
        return verifier


_VERIFIER_TARGETS: WeakKeyDictionary[
    _VerifierHandle, SignerRuntimeGenerationVerifier
] = WeakKeyDictionary()
_VERIFIER_AUTHORITIES: WeakKeyDictionary[
    _VerifierAuthorityBoundary, tuple[object, _VerifierHandle]
] = WeakKeyDictionary()


def create_signer_runtime_generation_verifier_authority(
    public_key: str,
) -> tuple[object, SignerRuntimeGenerationVerifierAuthorityBoundary]:
    """Mint one process-local authority around public verification material."""

    target = _PublicGenerationVerifier(public_key)
    verifier = _VerifierHandle()
    _VERIFIER_TARGETS[verifier] = target
    authority = object()
    boundary = _VerifierAuthorityBoundary()
    _VERIFIER_AUTHORITIES[boundary] = (authority, verifier)
    return authority, boundary


def require_signer_runtime_generation_verifier_authority(
    authority: object,
    boundary: SignerRuntimeGenerationVerifierAuthorityBoundary,
) -> SignerRuntimeGenerationVerifier:
    if type(boundary) is not _VerifierAuthorityBoundary:
        raise ValueError("generation_verifier_boundary_invalid")
    return boundary.require(authority)


__all__ = [
    "SignerRuntimeGenerationVerifierAuthorityBoundary",
    "create_signer_runtime_generation_verifier_authority",
    "require_signer_runtime_generation_verifier_authority",
]
