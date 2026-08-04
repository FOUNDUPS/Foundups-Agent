"""Tests for REDDOG_ISOLATED_SIGNER_PROCESS_ENTRYPOINT_PHASE1."""

from __future__ import annotations

import ast
import base64
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_process_entrypoint import (
    FAIL_SIGNER_PROCESS_CONFIG_INVALID,
    FAIL_SIGNER_PROCESS_KEY_PROVIDER_REJECTED,
    FAIL_SIGNER_PROCESS_ISOLATION_REJECTED,
    FAIL_SIGNER_PROCESS_PEER_POLICY_INVALID,
    FAIL_SIGNER_PROCESS_SERVICE_INVALID,
    FAIL_SIGNER_PROCESS_SERVICE_REJECTED,
    SIGNER_PROCESS_ENTRYPOINT_REJECT,
    SIGNER_PROCESS_ENTRYPOINT_SERVED,
    IsolatedSignerProcessEntryPointConfig,
    run_reddog_isolated_signer_process_once,
)
from modules.communication.moltbot_bridge.src.reddog_signer_process_isolation_gate import (
    SignerProcessIsolationReceipt,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_service import (
    SIGNER_SOCKET_SERVICE_REJECT,
    SIGNER_SOCKET_SERVICE_SERVED,
    IsolatedSignerSocketServiceResult,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    AUDIT_KEY_PREFIX,
    PROVIDER_MODE_TEST_ONLY_DRYRUN,
    PROVIDER_MODE_WSP71_PERMISSIONED,
    SIGNING_KEY_PREFIX,
    SignerKeyProviderProfile,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    PeerCredentialPolicy,
)
from modules.infrastructure.secrets_mcp.src.vault_resolver import ResolveResult, hash_reference


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_isolated_signer_process_entrypoint.py"
)


pytest.importorskip("cryptography")


class FakeResolver:
    def __init__(self, values: dict[str, str], ttl: int = 60) -> None:
        self.values = values
        self.ttl = ttl

    def resolve(self, reference: str, requester_id: str | None = None) -> ResolveResult:
        value = self.values[reference]
        return ResolveResult(
            success=True,
            reference=reference,
            reference_hash=hash_reference(reference),
            ttl_remaining=self.ttl,
            session_id="test-session",
            _secret_value=value,
        )


class CapturingService:
    def __init__(self, result: IsolatedSignerSocketServiceResult | object | None = None) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.result is not None:
            return self.result
        return IsolatedSignerSocketServiceResult(
            accepted=True,
            status=SIGNER_SOCKET_SERVICE_SERVED,
            rejection_reasons=(),
            socket_path=str(kwargs["socket_path"]),
            request_handled=True,
            socket_removed=True,
        )


class RaisingService:
    def __call__(self, **kwargs):
        raise RuntimeError("service failed")


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


def _resolver(private_key) -> FakeResolver:
    return FakeResolver(
        {
            "op://test-vault/reddog-signing/private": _private_key_secret(private_key),
            "op://test-vault/reddog-audit/mac": _audit_secret(),
        }
    )


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


def _policy(**overrides: object) -> PeerCredentialPolicy:
    values = {
        "uid_to_principal": {1001: "github:mjtrout"},
        "allowed_gids": (1002,),
        "transport": "unix_socket",
        "credential_source_prefix": "kernel_peer_credential",
    }
    values.update(overrides)
    return PeerCredentialPolicy(**values)


def _config(public_key: str, **overrides: object) -> IsolatedSignerProcessEntryPointConfig:
    values = {
        "repo_root": "O:/Foundups-Agent",
        "socket_path": "O:/tmp/reddog-signer.sock",
        "key_provider_profile": _profile(public_key),
        "peer_policy": _policy(),
        "provider_mode": PROVIDER_MODE_TEST_ONLY_DRYRUN,
        "allow_test_only_key_material": True,
        "permission_snapshot_fresh": True,
    }
    values.update(overrides)
    return IsolatedSignerProcessEntryPointConfig(**values)


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


def _accepted_isolation(_policy: PeerCredentialPolicy) -> SignerProcessIsolationReceipt:
    return SignerProcessIsolationReceipt(
        True, (), 1201, 1201, True, True, True, True, True, True, True
    )


def test_entrypoint_composes_key_provider_attestor_and_service() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    service = CapturingService()

    result = run_reddog_isolated_signer_process_once(
        _config(public_key),
        _resolver(private_key),
        serve_once=service,
        enforce_isolation=_accepted_isolation,
    )

    assert result.accepted is True
    assert result.status == SIGNER_PROCESS_ENTRYPOINT_SERVED
    assert result.key_provider_receipt["ok"] is True
    assert result.service_result["status"] == SIGNER_SOCKET_SERVICE_SERVED
    assert result.no_env_parsed is True
    assert result.no_process_spawned is True
    assert len(service.calls) == 1
    backend = service.calls[0]["backend"]
    response = backend.sign(
        _request(public_key),
        service.calls[0]["peer_attestor"].attest(_FakePeerCredSocket()),
    )
    assert response.accepted is True
    assert Ed25519SignatureVerifier().verify(
        public_key, _request(public_key).signing_input, response.signature
    ) is True


def test_production_isolation_rejects_before_key_resolution() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    resolver = _resolver(private_key)
    resolver.resolve = lambda *_args, **_kwargs: pytest.fail("resolver called")  # type: ignore[method-assign]

    result = run_reddog_isolated_signer_process_once(
        _config(
            public_key,
            provider_mode=PROVIDER_MODE_WSP71_PERMISSIONED,
            allow_test_only_key_material=False,
        ),
        resolver,
        enforce_isolation=lambda _policy: SignerProcessIsolationReceipt(
            False, ("failed",), None, None,
            False, False, False, False, False, False, False,
        ),
    )

    assert result.accepted is False
    assert FAIL_SIGNER_PROCESS_ISOLATION_REJECTED in result.rejection_reasons
    assert result.key_provider_receipt == {}


def test_entrypoint_accepts_wsp71_permissioned_provider_mode_without_test_override() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    service = CapturingService()

    result = run_reddog_isolated_signer_process_once(
        _config(
            public_key,
            provider_mode=PROVIDER_MODE_WSP71_PERMISSIONED,
            allow_test_only_key_material=False,
            permission_snapshot_fresh=True,
        ),
        _resolver(private_key),
        serve_once=service,
        enforce_isolation=_accepted_isolation,
    )

    assert result.accepted is True
    assert result.status == SIGNER_PROCESS_ENTRYPOINT_SERVED
    assert result.key_provider_receipt["ok"] is True
    assert len(service.calls) == 1


class _FakePeerCredSocket:
    def getsockopt(self, level: int, optname: int, buflen: int) -> bytes:
        import struct

        return struct.pack("3i", 123, 1001, 1002)


def test_default_key_provider_mode_rejects_before_service_call() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    service = CapturingService()
    config = _config(public_key, allow_test_only_key_material=False)

    result = run_reddog_isolated_signer_process_once(config, _resolver(private_key), serve_once=service)

    assert result.accepted is False
    assert result.status == SIGNER_PROCESS_ENTRYPOINT_REJECT
    assert FAIL_SIGNER_PROCESS_KEY_PROVIDER_REJECTED in result.rejection_reasons
    assert service.calls == []


def test_invalid_peer_policy_rejects_before_key_provider_or_service() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    service = CapturingService()
    config = _config(public_key, peer_policy=PeerCredentialPolicy({}))

    result = run_reddog_isolated_signer_process_once(config, _resolver(private_key), serve_once=service)

    assert result.accepted is False
    assert FAIL_SIGNER_PROCESS_PEER_POLICY_INVALID in result.rejection_reasons
    assert result.key_provider_receipt == {}
    assert service.calls == []


def test_invalid_config_rejects() -> None:
    result = run_reddog_isolated_signer_process_once("not-config", object())  # type: ignore[arg-type]

    assert result.accepted is False
    assert FAIL_SIGNER_PROCESS_CONFIG_INVALID in result.rejection_reasons


def test_service_reject_or_exception_is_preserved() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    rejected_service = CapturingService(
        IsolatedSignerSocketServiceResult(
            accepted=False,
            status=SIGNER_SOCKET_SERVICE_REJECT,
            rejection_reasons=("FAIL_SOCKET",),
        )
    )

    rejected = run_reddog_isolated_signer_process_once(
        _config(public_key),
        _resolver(private_key),
        serve_once=rejected_service,
    )
    raised = run_reddog_isolated_signer_process_once(
        _config(public_key),
        _resolver(private_key),
        serve_once=RaisingService(),
    )

    assert rejected.accepted is False
    assert FAIL_SIGNER_PROCESS_SERVICE_REJECTED in rejected.rejection_reasons
    assert rejected.service_result["status"] == SIGNER_SOCKET_SERVICE_REJECT
    assert raised.accepted is False
    assert FAIL_SIGNER_PROCESS_SERVICE_REJECTED in raised.rejection_reasons


def test_service_return_type_must_be_service_result() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)

    result = run_reddog_isolated_signer_process_once(
        _config(public_key),
        _resolver(private_key),
        serve_once=CapturingService(result={"not": "service-result"}),
    )

    assert result.accepted is False
    assert FAIL_SIGNER_PROCESS_SERVICE_INVALID in result.rejection_reasons


def test_receipts_do_not_serialize_backend_or_secret_material() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)

    result = run_reddog_isolated_signer_process_once(
        _config(public_key),
        _resolver(private_key),
        serve_once=CapturingService(),
    )
    text = str(result.to_dict())

    assert "backend" not in text
    assert SIGNING_KEY_PREFIX not in text
    assert AUDIT_KEY_PREFIX not in text
    assert "0123456789abcdef" not in text


def test_module_has_no_env_shell_file_repo_openclaw_hermes_or_holoindex_surface() -> None:
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
    banned_name_calls = {"eval", "exec", "compile", "__import__", "open"}
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
        "read_text",
        "read_bytes",
        "write_text",
        "write_bytes",
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
