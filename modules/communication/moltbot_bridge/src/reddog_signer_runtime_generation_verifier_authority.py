"""Factory-issued public-key verifier authority for signer generations."""

from __future__ import annotations

import hashlib
from typing import Any, Protocol

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    decode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    SignerRuntimeGenerationVerifier,
    _build_process_local_registry,
)


class SignerRuntimeGenerationVerifierAuthorityBoundary(Protocol):
    def require(self, value: object) -> SignerRuntimeGenerationVerifier: ...


_issue_verifier_target, _lookup_verifier_target = (
    _build_process_local_registry("generation_verifier_handle_unverified")
)
_issue_verifier_authority, _lookup_verifier_authority = (
    _build_process_local_registry("generation_verifier_authority_unverified")
)
del _build_process_local_registry


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


def _handle_authenticator_id(lookup: Any):
    def authenticator_id(self: object) -> str:
        return lookup(self).authenticator_id

    return authenticator_id


def _handle_verify(lookup: Any):
    def verify(
        self: object, payload: bytes, authentication_tag: str
    ) -> bool:
        return lookup(self).verify(payload, authentication_tag)

    return verify


class _VerifierHandle:
    __slots__ = ("__weakref__",)

    authenticator_id = property(
        _handle_authenticator_id(_lookup_verifier_target)
    )
    verify = _handle_verify(_lookup_verifier_target)


def _boundary_require(lookup: Any):
    def require(
        self: object, value: object
    ) -> SignerRuntimeGenerationVerifier:
        authority, verifier = lookup(self)
        if value is not authority:
            raise ValueError("generation_verifier_authority_unverified")
        return verifier

    return require


class _VerifierAuthorityBoundary:
    __slots__ = ("__weakref__",)

    require = _boundary_require(_lookup_verifier_authority)


def _build_authority_factory(issue_target: Any, issue_authority: Any):
    def create(
        public_key: str,
    ) -> tuple[object, SignerRuntimeGenerationVerifierAuthorityBoundary]:
        """Mint one process-local authority around public verification material."""

        target = _PublicGenerationVerifier(public_key)
        verifier = _VerifierHandle()
        issue_target(verifier, target)
        authority = object()
        boundary = _VerifierAuthorityBoundary()
        issue_authority(boundary, (authority, verifier))
        return authority, boundary

    return create


create_signer_runtime_generation_verifier_authority = (
    _build_authority_factory(
        _issue_verifier_target,
        _issue_verifier_authority,
    )
)


def require_signer_runtime_generation_verifier_authority(
    authority: object,
    boundary: SignerRuntimeGenerationVerifierAuthorityBoundary,
) -> SignerRuntimeGenerationVerifier:
    if type(boundary) is not _VerifierAuthorityBoundary:
        raise ValueError("generation_verifier_boundary_invalid")
    return boundary.require(authority)


del _lookup_verifier_authority, _lookup_verifier_target
del _issue_verifier_authority, _issue_verifier_target
del _boundary_require, _build_authority_factory
del _handle_authenticator_id, _handle_verify


__all__ = [
    "SignerRuntimeGenerationVerifierAuthorityBoundary",
    "create_signer_runtime_generation_verifier_authority",
    "require_signer_runtime_generation_verifier_authority",
]
