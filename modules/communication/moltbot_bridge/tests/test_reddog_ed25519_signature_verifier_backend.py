"""Tests for REDDOG_ED25519_SIGNATURE_VERIFIER_BACKEND_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    ED25519_PUBLIC_KEY_PREFIX,
    ED25519_SIGNATURE_PREFIX,
    Ed25519SignatureVerifier,
    decode_ed25519_public_key,
    decode_ed25519_signature,
    encode_ed25519_public_key,
    encode_ed25519_signature,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_ed25519_signature_verifier_backend.py"
)


cryptography = pytest.importorskip("cryptography")


def _keypair() -> tuple[str, str, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    signing_input = 'reddog-workauth.v1.{"work_order_id":"wo-1"}'
    signature = private_key.sign(signing_input.encode("utf-8"))
    return (
        encode_ed25519_public_key(public_bytes),
        signing_input,
        encode_ed25519_signature(signature),
    )


def test_ed25519_verifier_accepts_valid_signature() -> None:
    public_key, signing_input, signature = _keypair()

    assert Ed25519SignatureVerifier().verify(public_key, signing_input, signature) is True
    assert public_key.startswith(ED25519_PUBLIC_KEY_PREFIX)
    assert signature.startswith(ED25519_SIGNATURE_PREFIX)


def test_ed25519_verifier_rejects_tampered_input_signature_or_key() -> None:
    public_key, signing_input, signature = _keypair()
    other_public_key, _, other_signature = _keypair()
    verifier = Ed25519SignatureVerifier()

    assert verifier.verify(public_key, signing_input + "x", signature) is False
    assert verifier.verify(public_key, signing_input, other_signature) is False
    assert verifier.verify(other_public_key, signing_input, signature) is False


def test_ed25519_verifier_rejects_malformed_or_non_ascii_inputs() -> None:
    public_key, signing_input, signature = _keypair()
    verifier = Ed25519SignatureVerifier()

    assert verifier.verify("not-a-key", signing_input, signature) is False
    assert verifier.verify(public_key, signing_input, "not-a-signature") is False
    assert verifier.verify(public_key + "\u2603", signing_input, signature) is False
    assert verifier.verify(public_key, signing_input + "\u2603", signature) is False


def test_ed25519_encode_decode_helpers_are_strict() -> None:
    public_key, _, signature = _keypair()

    assert decode_ed25519_public_key(public_key) is not None
    assert decode_ed25519_signature(signature) is not None
    assert decode_ed25519_public_key(public_key[:-2]) is None
    assert decode_ed25519_signature(signature[:-2]) is None

    with pytest.raises(ValueError):
        encode_ed25519_public_key(b"short")
    with pytest.raises(ValueError):
        encode_ed25519_signature(b"short")


def test_ed25519_verifier_rejects_oversized_signing_input() -> None:
    public_key, _, signature = _keypair()

    assert Ed25519SignatureVerifier().verify(public_key, "x" * 70000, signature) is False


def test_backend_module_does_not_sign_generate_keys_or_touch_runtime_surfaces() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "socket",
        "os",
        "requests",
        "urllib",
        "http",
        "holo_index",
        "git",
        "secrets",
    }
    banned_calls = {
        "eval",
        "exec",
        "compile",
        "__import__",
        "generate",
        "from_private_bytes",
    }
    banned_attrs = {
        "system",
        "popen",
        "spawn",
        "run",
        "Popen",
        "check_call",
        "check_output",
        "getenv",
        "environ",
        "sign",
        "private_bytes",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs
