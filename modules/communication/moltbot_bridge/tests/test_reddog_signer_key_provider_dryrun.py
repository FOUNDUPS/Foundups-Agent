"""Tests for REDDOG_SIGNER_KEY_PROVIDER_DRYRUN_PHASE1."""

from __future__ import annotations

import ast
import base64
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    AUDIT_KEY_PREFIX,
    FAIL_PROVIDER_AUDIT_KEY_MISSING,
    FAIL_PROVIDER_FINGERPRINT_MISMATCH,
    FAIL_PROVIDER_KEY_FORMAT,
    FAIL_PROVIDER_MOCK_IN_PRODUCTION,
    FAIL_PROVIDER_PERMISSION_DENIED,
    FAIL_PROVIDER_PROFILE_INVALID,
    FAIL_PROVIDER_PUBLIC_KEY_MISMATCH,
    FAIL_PROVIDER_REFERENCE_FORBIDDEN,
    FAIL_PROVIDER_REFERENCE_INVALID,
    FAIL_PROVIDER_RESOLVER_UNAVAILABLE,
    FAIL_PROVIDER_TTL_EXPIRED,
    PROVIDER_MODE_TEST_ONLY_DRYRUN,
    SIGNING_KEY_PREFIX,
    SignerKeyProviderProfile,
    build_test_only_signer_backend_from_provider,
)
from modules.infrastructure.secrets_mcp.src.vault_resolver import (
    ResolveErrorCode,
    ResolveResult,
    hash_reference,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_signer_key_provider_dryrun.py"
)


pytest.importorskip("cryptography")


class FakeResolver:
    def __init__(self, values: dict[str, str], ttl: int = 60) -> None:
        self.values = values
        self.ttl = ttl
        self.calls: list[tuple[str, str | None]] = []

    def resolve(self, reference: str, requester_id: str | None = None) -> ResolveResult:
        self.calls.append((reference, requester_id))
        value = self.values.get(reference)
        if value is None:
            return ResolveResult(
                success=False,
                reference=reference,
                reference_hash=hash_reference(reference),
                error_code=ResolveErrorCode.UNKNOWN_REFERENCE,
                error_message="unknown",
            )
        return ResolveResult(
            success=True,
            reference=reference,
            reference_hash=hash_reference(reference),
            ttl_remaining=self.ttl,
            session_id="test-session",
            _secret_value=value,
        )


class RaisingResolver:
    def resolve(self, reference: str, requester_id: str | None = None) -> ResolveResult:
        raise RuntimeError("resolver down")


class WrongTypeResolver:
    def resolve(self, reference: str, requester_id: str | None = None) -> object:
        return {"success": True}


def _private_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    return Ed25519PrivateKey.generate()


def _private_key_secret(private_key) -> str:
    from cryptography.hazmat.primitives import serialization

    raw = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return SIGNING_KEY_PREFIX + base64.b64encode(raw).decode("ascii")


def _public_text(private_key) -> str:
    from cryptography.hazmat.primitives import serialization

    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return encode_ed25519_public_key(public_bytes)


def _audit_secret(raw: bytes = b"0123456789abcdef0123456789abcdef") -> str:
    return AUDIT_KEY_PREFIX + base64.b64encode(raw).decode("ascii")


def _profile(public_key: str, **overrides: object) -> SignerKeyProviderProfile:
    values = {
        "signer_profile_id": "signer-profile-1",
        "signer_agent_id": "signer:reddog-authority",
        "signing_key_ref": "op://test-vault/reddog-signing/private",
        "audit_mac_key_ref": "op://test-vault/reddog-audit/mac",
        "expected_public_key": public_key,
        "expected_key_fingerprint": public_key_fingerprint(public_key),
        "expected_key_epoch": "epoch-1",
        "permission_snapshot_digest": "sha256:permission",
        "ttl_seconds": 60,
    }
    values.update(overrides)
    return SignerKeyProviderProfile(**values)


def _resolver(private_key, audit_secret: str | None = None, ttl: int = 60) -> FakeResolver:
    return FakeResolver(
        {
            "op://test-vault/reddog-signing/private": _private_key_secret(private_key),
            "op://test-vault/reddog-audit/mac": audit_secret or _audit_secret(),
        },
        ttl=ttl,
    )


def _request(public_key: str) -> SigningRequest:
    return SigningRequest(
        signing_input='reddog-workauth.v1.{"work_order_id":"wo-1"}',
        payload_digest="sha256:payload",
        signer_role="reddog",
        signer_public_key=public_key,
        requester_principal_id="github:mjtrout",
        nonce="nonce-1",
        key_epoch="epoch-1",
        requested_operation="create_foundup",
        authority_tier="HIGH",
        consensus_receipt_digest="sha256:consensus",
    )


def _peer() -> SignerPeerAttestation:
    return SignerPeerAttestation(
        peer_principal_id="github:mjtrout",
        transport="unix_socket",
        credential_source="kernel_peer_credential",
        boundary_attested=True,
    )


def _build(profile: SignerKeyProviderProfile, resolver: object):
    return build_test_only_signer_backend_from_provider(
        profile,
        resolver,  # type: ignore[arg-type]
        provider_mode=PROVIDER_MODE_TEST_ONLY_DRYRUN,
        allow_test_only_key_material=True,
        permission_snapshot_fresh=True,
    )


def test_default_path_rejects_without_explicit_test_only_mode() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)

    result = build_test_only_signer_backend_from_provider(_profile(public_key), _resolver(private_key))

    assert result.ok is False
    assert result.rejection_code == FAIL_PROVIDER_MOCK_IN_PRODUCTION
    assert result.backend is None


def test_acceptance_builds_backend_and_receipt_excludes_secret_values() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    resolver = _resolver(private_key)

    result = _build(_profile(public_key), resolver)

    assert result.ok is True
    assert result.backend is not None
    receipt = result.to_receipt()
    assert receipt["secret_values_returned"] is False
    assert "backend" not in receipt
    dumped = json.dumps(receipt, sort_keys=True)
    assert SIGNING_KEY_PREFIX not in dumped
    assert AUDIT_KEY_PREFIX not in dumped
    assert "0123456789abcdef" not in dumped
    assert resolver.calls == [
        ("op://test-vault/reddog-signing/private", "signer:reddog-authority"),
        ("op://test-vault/reddog-audit/mac", "signer:reddog-authority"),
    ]


def test_backend_signs_and_public_verifier_accepts() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    result = _build(_profile(public_key), _resolver(private_key))

    response = result.backend.sign(_request(public_key), _peer())  # type: ignore[union-attr]

    assert response.accepted is True
    assert response.audit_mac.startswith("audit-mac-v1:")
    assert response.no_secret_material_returned is True
    assert Ed25519SignatureVerifier().verify(public_key, _request(public_key).signing_input, response.signature) is True


def test_permission_snapshot_must_be_fresh() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    result = build_test_only_signer_backend_from_provider(
        _profile(public_key),
        _resolver(private_key),
        provider_mode=PROVIDER_MODE_TEST_ONLY_DRYRUN,
        allow_test_only_key_material=True,
        permission_snapshot_fresh=False,
    )

    assert result.ok is False
    assert result.rejection_code == FAIL_PROVIDER_PERMISSION_DENIED


def test_signing_and_audit_reference_must_differ() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    profile = _profile(public_key, audit_mac_key_ref="op://test-vault/reddog-signing/private")

    result = _build(profile, _resolver(private_key))

    assert result.ok is False
    assert result.rejection_code == FAIL_PROVIDER_REFERENCE_FORBIDDEN


def test_invalid_reference_rejects_before_resolver_call() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    resolver = _resolver(private_key)
    profile = _profile(public_key, signing_key_ref="../bad")

    result = _build(profile, resolver)

    assert result.ok is False
    assert result.rejection_code == FAIL_PROVIDER_REFERENCE_INVALID
    assert resolver.calls == []


def test_resolver_exception_or_wrong_type_rejects() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)

    raised = _build(_profile(public_key), RaisingResolver())
    wrong_type = _build(_profile(public_key), WrongTypeResolver())

    assert raised.ok is False
    assert raised.rejection_code == FAIL_PROVIDER_RESOLVER_UNAVAILABLE
    assert wrong_type.ok is False
    assert wrong_type.rejection_code == FAIL_PROVIDER_RESOLVER_UNAVAILABLE


def test_missing_resolved_value_rejects_as_reference_invalid() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    result = _build(_profile(public_key), FakeResolver({}))

    assert result.ok is False
    assert result.rejection_code == FAIL_PROVIDER_REFERENCE_INVALID


def test_ttl_expired_or_too_large_rejects() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    expired = _build(_profile(public_key), _resolver(private_key, ttl=0))
    stale = _build(_profile(public_key, ttl_seconds=30), _resolver(private_key, ttl=31))

    assert expired.ok is False
    assert expired.rejection_code == FAIL_PROVIDER_TTL_EXPIRED
    assert stale.ok is False
    assert stale.rejection_code == FAIL_PROVIDER_TTL_EXPIRED


def test_bad_signing_key_format_rejects() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    resolver = FakeResolver(
        {
            "op://test-vault/reddog-signing/private": SIGNING_KEY_PREFIX + "not-base64",
            "op://test-vault/reddog-audit/mac": _audit_secret(),
        }
    )

    result = _build(_profile(public_key), resolver)

    assert result.ok is False
    assert result.rejection_code == FAIL_PROVIDER_KEY_FORMAT


def test_missing_or_short_audit_key_rejects() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)

    missing = _build(_profile(public_key), _resolver(private_key, audit_secret="wrong-prefix"))
    short = _build(_profile(public_key), _resolver(private_key, audit_secret=_audit_secret(b"short")))

    assert missing.ok is False
    assert missing.rejection_code == FAIL_PROVIDER_AUDIT_KEY_MISSING
    assert short.ok is False
    assert short.rejection_code == FAIL_PROVIDER_AUDIT_KEY_MISSING


def test_public_key_and_fingerprint_mismatches_reject() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    other_public = _public_text(_private_key())

    wrong_public = _build(_profile(other_public), _resolver(private_key))
    wrong_fingerprint = _build(
        _profile(public_key, expected_key_fingerprint=public_key_fingerprint(other_public)),
        _resolver(private_key),
    )

    assert wrong_public.ok is False
    assert wrong_public.rejection_code == FAIL_PROVIDER_PUBLIC_KEY_MISMATCH
    assert wrong_fingerprint.ok is False
    assert wrong_fingerprint.rejection_code == FAIL_PROVIDER_FINGERPRINT_MISMATCH


def test_non_ascii_or_incomplete_profile_rejects() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    non_ascii = _build(_profile(public_key, signer_profile_id="bad-\u2603"), _resolver(private_key))
    incomplete = _build(_profile(public_key, expected_key_epoch=""), _resolver(private_key))

    assert non_ascii.ok is False
    assert non_ascii.rejection_code == FAIL_PROVIDER_PROFILE_INVALID
    assert incomplete.ok is False
    assert incomplete.rejection_code == FAIL_PROVIDER_PROFILE_INVALID


def test_result_repr_and_receipt_do_not_expose_secret_material() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    result = _build(_profile(public_key), _resolver(private_key))
    text = repr(result) + json.dumps(result.to_receipt(), sort_keys=True)

    assert SIGNING_KEY_PREFIX not in text
    assert AUDIT_KEY_PREFIX not in text
    assert "PRIVATE KEY" not in text.upper()
    assert "0123456789abcdef" not in text


def test_module_has_no_repo_shell_socket_openclaw_hermes_or_holoindex_runtime_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "os",
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "http",
        "git",
        "holo_index",
    }
    banned_name_calls = {"eval", "exec", "compile", "__import__"}
    banned_attrs = {
        "getenv",
        "environ",
        "system",
        "popen",
        "run",
        "Popen",
        "check_call",
        "check_output",
        "spawn",
        "bind",
        "connect",
        "read_text",
        "read_bytes",
        "write_text",
        "write_bytes",
        "private_bytes",
    }
    banned_name_fragments = ("openclaw", "hermes", "worktree", "holoindex")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
            assert not any(fragment in node.module.lower() for fragment in banned_name_fragments)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_name_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs
