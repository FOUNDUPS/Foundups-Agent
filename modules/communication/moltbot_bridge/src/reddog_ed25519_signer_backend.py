"""Ed25519 signer backend for the isolated RedDog signer process.

Slice: REDDOG_ED25519_SIGNER_BACKEND_PHASE1

This module signs ``SigningRequest`` records using an already-held Ed25519 key
object supplied by the isolated signer process. It does not generate keys, load
keys from disk, read vault secrets, inspect environment variables, bind sockets,
spawn processes, execute shell commands, mutate repository files, enqueue
OpenClaw, dispatch Hermes, or re-index HoloIndex.

The backend requires an injected audit-MAC builder. If the key object, public
key binding, key epoch, or audit-MAC boundary is missing, it rejects fail-closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    IsolatedSignerBackend,
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)


REJECT_ED25519_SIGNER_REQUEST_INVALID = "REJECT_ED25519_SIGNER_REQUEST_INVALID"
REJECT_ED25519_SIGNER_KEY_INVALID = "REJECT_ED25519_SIGNER_KEY_INVALID"
REJECT_ED25519_SIGNER_PUBLIC_KEY_MISMATCH = "REJECT_ED25519_SIGNER_PUBLIC_KEY_MISMATCH"
REJECT_ED25519_SIGNER_KEY_EPOCH_MISMATCH = "REJECT_ED25519_SIGNER_KEY_EPOCH_MISMATCH"
REJECT_ED25519_SIGNER_AUDIT_MAC_MISSING = "REJECT_ED25519_SIGNER_AUDIT_MAC_MISSING"
REJECT_ED25519_SIGNER_SIGN_FAILED = "REJECT_ED25519_SIGNER_SIGN_FAILED"


class SignerAuditMacBuilder(Protocol):
    """Injected audit-MAC boundary owned by the isolated signer process."""

    def build(self, request: SigningRequest, signature: str, peer: SignerPeerAttestation) -> str:
        """Return a signer-side audit MAC. Empty or non-ASCII values reject."""


@dataclass(frozen=True)
class Ed25519SignerBackend(IsolatedSignerBackend):
    """Sign requests with an already-held Ed25519 private key object."""

    private_key: Any
    public_key: str
    key_epoch: str
    audit_mac_builder: SignerAuditMacBuilder

    def sign(self, request: SigningRequest, peer: SignerPeerAttestation) -> SigningResponse:
        if not isinstance(request, SigningRequest) or not isinstance(peer, SignerPeerAttestation):
            return _reject(REJECT_ED25519_SIGNER_REQUEST_INVALID)
        if not _assert_ascii_deep(request.to_dict()) or not _assert_ascii_deep(peer.to_dict()):
            return _reject(REJECT_ED25519_SIGNER_REQUEST_INVALID)
        if not _is_ascii(self.public_key) or not _is_ascii(self.key_epoch):
            return _reject(REJECT_ED25519_SIGNER_KEY_INVALID)
        if request.signer_public_key != self.public_key:
            return _reject(REJECT_ED25519_SIGNER_PUBLIC_KEY_MISMATCH)
        if request.key_epoch != self.key_epoch:
            return _reject(REJECT_ED25519_SIGNER_KEY_EPOCH_MISMATCH)
        if not request.signing_input:
            return _reject(REJECT_ED25519_SIGNER_REQUEST_INVALID)

        try:
            derived_public_key = encode_ed25519_public_key(_public_bytes_from_private_key(self.private_key))
        except Exception:
            return _reject(REJECT_ED25519_SIGNER_KEY_INVALID)
        if derived_public_key != self.public_key:
            return _reject(REJECT_ED25519_SIGNER_PUBLIC_KEY_MISMATCH)

        try:
            signature = encode_ed25519_signature(
                self.private_key.sign(request.signing_input.encode("utf-8"))
            )
        except Exception:
            return _reject(REJECT_ED25519_SIGNER_SIGN_FAILED)
        try:
            audit_mac = self.audit_mac_builder.build(request, signature, peer)
        except Exception:
            return _reject(REJECT_ED25519_SIGNER_AUDIT_MAC_MISSING)
        if not _is_ascii(audit_mac) or not audit_mac:
            return _reject(REJECT_ED25519_SIGNER_AUDIT_MAC_MISSING)

        return SigningResponse(
            accepted=True,
            signature=signature,
            signer_public_key=self.public_key,
            key_fingerprint=public_key_fingerprint(self.public_key),
            key_epoch=self.key_epoch,
            audit_mac=audit_mac,
            boundary_attested=peer.boundary_attested,
            requester_identity_attested=True,
            signer_loads_no_untrusted_code=True,
            no_secret_material_returned=True,
        )


def _public_bytes_from_private_key(private_key: Any) -> bytes:
    from cryptography.hazmat.primitives import serialization

    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _reject(code: str) -> SigningResponse:
    return SigningResponse(
        accepted=False,
        rejection_code=str(code),
        no_secret_material_returned=True,
    )


def _is_ascii(value: object) -> bool:
    return isinstance(value, str) and all(ord(char) < 128 for char in value)


def _assert_ascii_deep(value: object) -> bool:
    if isinstance(value, str):
        return _is_ascii(value)
    if isinstance(value, dict):
        return all(_is_ascii(key) and _assert_ascii_deep(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_assert_ascii_deep(item) for item in value)
    if value is None or isinstance(value, (bool, int, float)):
        return True
    return False


__all__ = [
    "Ed25519SignerBackend",
    "REJECT_ED25519_SIGNER_AUDIT_MAC_MISSING",
    "REJECT_ED25519_SIGNER_KEY_EPOCH_MISMATCH",
    "REJECT_ED25519_SIGNER_KEY_INVALID",
    "REJECT_ED25519_SIGNER_PUBLIC_KEY_MISMATCH",
    "REJECT_ED25519_SIGNER_REQUEST_INVALID",
    "REJECT_ED25519_SIGNER_SIGN_FAILED",
    "SignerAuditMacBuilder",
]
