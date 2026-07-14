"""Ed25519 public signature verifier backend for RedDog authority records.

Slice: REDDOG_ED25519_SIGNATURE_VERIFIER_BACKEND_PHASE1

This module supplies an optional injected ``SignatureVerifier`` backend for
``reddog_work_order_signature_verifier``. It verifies Ed25519 signatures using
public key material only. It does not sign, generate keys, load private keys or
vault secrets, execute work, mutate repository files, enqueue OpenClaw, dispatch
Hermes, or re-index HoloIndex.

The dependency on ``cryptography`` is imported lazily inside ``verify``. If the
package is unavailable, malformed, or verification fails, the backend returns
False fail-closed.
"""

from __future__ import annotations

import base64
import binascii
from typing import Optional

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)


ED25519_PUBLIC_KEY_PREFIX = "ed25519-pub-v1:"
ED25519_SIGNATURE_PREFIX = "ed25519-sig-v1:"
ED25519_PUBLIC_KEY_BYTES = 32
ED25519_SIGNATURE_BYTES = 64
MAX_SIGNING_INPUT_BYTES = 65536


class Ed25519SignatureVerifier(SignatureVerifier):
    """Verify Ed25519 signatures using public key material only."""

    def verify(self, public_key: str, signing_input: str, signature: str) -> bool:
        if not _is_ascii(public_key) or not _is_ascii(signing_input) or not _is_ascii(signature):
            return False
        if len(signing_input.encode("utf-8")) > MAX_SIGNING_INPUT_BYTES:
            return False
        public_key_bytes = decode_ed25519_public_key(public_key)
        signature_bytes = decode_ed25519_signature(signature)
        if public_key_bytes is None or signature_bytes is None:
            return False
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

            Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(
                signature_bytes,
                signing_input.encode("utf-8"),
            )
            return True
        except Exception:
            return False


def encode_ed25519_public_key(public_key_bytes: bytes) -> str:
    """Encode 32 public key bytes into the contract's self-describing text form."""

    if not isinstance(public_key_bytes, bytes) or len(public_key_bytes) != ED25519_PUBLIC_KEY_BYTES:
        raise ValueError("Ed25519 public key must be 32 bytes")
    return ED25519_PUBLIC_KEY_PREFIX + _b64url_no_padding(public_key_bytes)


def encode_ed25519_signature(signature_bytes: bytes) -> str:
    """Encode 64 signature bytes into the contract's self-describing text form."""

    if not isinstance(signature_bytes, bytes) or len(signature_bytes) != ED25519_SIGNATURE_BYTES:
        raise ValueError("Ed25519 signature must be 64 bytes")
    return ED25519_SIGNATURE_PREFIX + _b64url_no_padding(signature_bytes)


def decode_ed25519_public_key(value: str) -> Optional[bytes]:
    if not _is_ascii(value) or not value.startswith(ED25519_PUBLIC_KEY_PREFIX):
        return None
    return _decode_with_size(value[len(ED25519_PUBLIC_KEY_PREFIX) :], ED25519_PUBLIC_KEY_BYTES)


def decode_ed25519_signature(value: str) -> Optional[bytes]:
    if not _is_ascii(value) or not value.startswith(ED25519_SIGNATURE_PREFIX):
        return None
    return _decode_with_size(value[len(ED25519_SIGNATURE_PREFIX) :], ED25519_SIGNATURE_BYTES)


def _decode_with_size(value: str, expected_size: int) -> Optional[bytes]:
    if not value or not _is_ascii(value):
        return None
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (binascii.Error, ValueError):
        return None
    if len(decoded) != expected_size:
        return None
    return decoded


def _b64url_no_padding(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _is_ascii(value: object) -> bool:
    return isinstance(value, str) and all(ord(char) < 128 for char in value)


__all__ = [
    "ED25519_PUBLIC_KEY_BYTES",
    "ED25519_PUBLIC_KEY_PREFIX",
    "ED25519_SIGNATURE_BYTES",
    "ED25519_SIGNATURE_PREFIX",
    "Ed25519SignatureVerifier",
    "decode_ed25519_public_key",
    "decode_ed25519_signature",
    "encode_ed25519_public_key",
    "encode_ed25519_signature",
]
