"""Tests for REDDOG_SIGNER_SOCKET_SERVICE_RUNTIME_WIRING_PHASE1."""

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
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import (
    SIGNER_SOCKET_RESIDENT_SERVICE_REJECT,
    SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
    IsolatedSignerSocketResidentServiceResult,
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
    PROVIDER_MODE_TEST_ONLY_DRYRUN,
    SIGNING_KEY_PREFIX,
    SignerKeyProviderProfile,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    PeerCredentialPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    FAIL_SIGNER_RUNTIME_CONFIG_INVALID,
    FAIL_SIGNER_RUNTIME_KEY_PROVIDER_REJECTED,
    FAIL_SIGNER_RUNTIME_PEER_POLICY_INVALID,
    FAIL_SIGNER_RUNTIME_PROFILE_INVALID,
    FAIL_SIGNER_RUNTIME_SERVICE_INVALID,
    FAIL_SIGNER_RUNTIME_SERVICE_REJECTED,
    SIGNER_SOCKET_RUNTIME_WIRING_REJECT,
    SIGNER_SOCKET_RUNTIME_WIRING_SERVED,
    SignerSocketServiceRuntimeWiringConfig,
    run_reddog_signer_socket_service_runtime_wiring,
)
from modules.infrastructure.secrets_mcp.src.vault_resolver import ResolveResult, hash_reference


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_signer_socket_service_runtime_wiring.py"
)


pytest.importorskip("cryptography")


class FakeResolver:
    def __init__(self, values: dict[str, str], ttl: int = 60) -> None:
        self.values = values
        self.ttl = ttl
        self.calls: list[tuple[str, str | None]] = []

    def resolve(self, reference: str, requester_id: str | None = None) -> ResolveResult:
        self.calls.append((reference, requester_id))
        value = self.values[reference]
        return ResolveResult(
            success=True,
            reference=reference,
            reference_hash=hash_reference(reference),
            ttl_remaining=self.ttl,
            session_id="test-session",
            _secret_value=value,
        )


class CapturingBoundedService:
    def __init__(self, result: IsolatedSignerSocketResidentServiceResult | object | None = None) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.result is not None:
            return self.result
        return IsolatedSignerSocketResidentServiceResult(
            accepted=True,
            status=SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
            rejection_reasons=(),
            socket_path=str(kwargs["socket_path"]),
            requests_handled=int(kwargs["max_requests"]),
            response_digests=("sha256:response",),
            socket_removed=True,
        )


class RaisingBoundedService:
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


def _config(public_key: str, **overrides: object) -> SignerSocketServiceRuntimeWiringConfig:
    values = {
        "repo_root": "O:/Foundups-Agent",
        "socket_path": "O:/tmp/reddog-signer.sock",
        "key_provider_profile": _profile(public_key),
        "peer_policy": _policy(),
        "provider_mode": PROVIDER_MODE_TEST_ONLY_DRYRUN,
        "allow_test_only_key_material": True,
        "permission_snapshot_fresh": True,
        "max_requests": 3,
        "timeout_s": 2.5,
        "max_request_bytes": 4096,
        "max_response_bytes": 8192,
    }
    values.update(overrides)
    return SignerSocketServiceRuntimeWiringConfig(**values)


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
        credential_source="test_peer_credential",
        boundary_attested=True,
    )


def test_runtime_wiring_composes_provider_attestor_and_bounded_service() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(public_key),
        _resolver(private_key),
        serve_bounded=service,
    )

    assert result.accepted is True
    assert result.status == SIGNER_SOCKET_RUNTIME_WIRING_SERVED
    assert result.key_provider_receipt["ok"] is True
    assert result.service_result["status"] == SIGNER_SOCKET_RESIDENT_SERVICE_SERVED
    assert result.max_requests == 3
    assert result.no_env_parsed is True
    assert result.no_process_spawned is True
    assert len(service.calls) == 1
    assert service.calls[0]["max_requests"] == 3
    assert service.calls[0]["timeout_s"] == 2.5
    backend = service.calls[0]["backend"]
    response = backend.sign(_request(public_key), _peer())
    assert response.accepted is True
    assert Ed25519SignatureVerifier().verify(public_key, _request(public_key).signing_input, response.signature) is True


def test_mapping_config_normalizes_profile_and_peer_policy() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    profile = _profile(public_key).__dict__
    policy = {
        "uid_to_principal": {"1001": "github:mjtrout"},
        "allowed_gids": ["1002"],
        "transport": "unix_socket",
        "credential_source_prefix": "kernel_peer_credential",
    }
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(public_key, key_provider_profile=profile, peer_policy=policy),
        _resolver(private_key),
        serve_bounded=service,
    )

    assert result.accepted is True
    attestor = service.calls[0]["peer_attestor"]
    assert attestor.policy.uid_to_principal == {1001: "github:mjtrout"}
    assert attestor.policy.allowed_gids == (1002,)


def test_default_provider_mode_rejects_before_service_call() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(public_key, allow_test_only_key_material=False),
        _resolver(private_key),
        serve_bounded=service,
    )

    assert result.accepted is False
    assert result.status == SIGNER_SOCKET_RUNTIME_WIRING_REJECT
    assert FAIL_SIGNER_RUNTIME_KEY_PROVIDER_REJECTED in result.rejection_reasons
    assert service.calls == []


def test_invalid_config_profile_or_peer_policy_rejects() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    resolver = _resolver(private_key)
    service = CapturingBoundedService()

    bad_config = run_reddog_signer_socket_service_runtime_wiring(
        "not-config",  # type: ignore[arg-type]
        resolver,
        serve_bounded=service,
    )
    bad_profile = run_reddog_signer_socket_service_runtime_wiring(
        _config(public_key, key_provider_profile={"signer_profile_id": "only-one-field"}),
        resolver,
        serve_bounded=service,
    )
    bad_policy = run_reddog_signer_socket_service_runtime_wiring(
        _config(public_key, peer_policy={"uid_to_principal": {}}),
        resolver,
        serve_bounded=service,
    )

    assert FAIL_SIGNER_RUNTIME_CONFIG_INVALID in bad_config.rejection_reasons
    assert FAIL_SIGNER_RUNTIME_PROFILE_INVALID in bad_profile.rejection_reasons
    assert FAIL_SIGNER_RUNTIME_PEER_POLICY_INVALID in bad_policy.rejection_reasons
    assert service.calls == []


def test_service_reject_exception_or_wrong_type_rejects() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    config = _config(public_key)
    resolver = _resolver(private_key)

    rejected = run_reddog_signer_socket_service_runtime_wiring(
        config,
        resolver,
        serve_bounded=CapturingBoundedService(
            IsolatedSignerSocketResidentServiceResult(
                accepted=False,
                status=SIGNER_SOCKET_RESIDENT_SERVICE_REJECT,
                rejection_reasons=("FAIL_SOCKET",),
            )
        ),
    )
    raised = run_reddog_signer_socket_service_runtime_wiring(
        config,
        resolver,
        serve_bounded=RaisingBoundedService(),
    )
    wrong = run_reddog_signer_socket_service_runtime_wiring(
        config,
        resolver,
        serve_bounded=CapturingBoundedService(result={"not": "service-result"}),
    )

    assert FAIL_SIGNER_RUNTIME_SERVICE_REJECTED in rejected.rejection_reasons
    assert rejected.service_result["status"] == SIGNER_SOCKET_RESIDENT_SERVICE_REJECT
    assert FAIL_SIGNER_RUNTIME_SERVICE_REJECTED in raised.rejection_reasons
    assert FAIL_SIGNER_RUNTIME_SERVICE_INVALID in wrong.rejection_reasons


def test_result_serialization_contains_no_secret_material_or_backend() -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(public_key),
        _resolver(private_key),
        serve_bounded=CapturingBoundedService(),
    )

    text = json.dumps(result.to_dict(), sort_keys=True)

    assert "backend" not in text
    assert SIGNING_KEY_PREFIX not in text
    assert AUDIT_KEY_PREFIX not in text
    assert "0123456789abcdef" not in text
    assert result.no_file_io_performed is True
    assert result.no_holoindex_reindex_performed is True


def test_module_has_no_env_shell_file_repo_openclaw_hermes_or_holoindex_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "os",
        "subprocess",
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
