"""Factory-issued public-key verifier authority for signer generations."""

from __future__ import annotations

import hashlib
from typing import Protocol

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


class _VerifierAuthorityBoundary:
    __slots__ = ("_authority", "_verifier")

    def __init__(
        self,
        authority: object,
        verifier: SignerRuntimeGenerationVerifier,
    ) -> None:
        self._authority = authority
        self._verifier = verifier

    def require(self, value: object) -> SignerRuntimeGenerationVerifier:
        if value is not self._authority:
            raise ValueError("generation_verifier_authority_unverified")
        return self._verifier


def create_signer_runtime_generation_verifier_authority(
    public_key: str,
) -> tuple[object, SignerRuntimeGenerationVerifierAuthorityBoundary]:
    """Mint one process-local authority around public verification material."""

    verifier = _PublicGenerationVerifier(public_key)
    authority = object()
    return authority, _VerifierAuthorityBoundary(authority, verifier)


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
