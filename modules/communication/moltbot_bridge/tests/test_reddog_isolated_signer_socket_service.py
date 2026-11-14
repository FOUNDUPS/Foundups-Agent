"""Tests for REDDOG_ISOLATED_SIGNER_SOCKET_SERVICE_ONCE_PHASE1."""

from __future__ import annotations

import ast
import socket
import tempfile
import threading
import uuid
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    Ed25519SignerBackend,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    RedDogIsolatedSignerSocketClient,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED,
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_service import (
    FAIL_SIGNER_SERVICE_REQUEST_LIMIT_INVALID,
    FAIL_SIGNER_SERVICE_SOCKET_PARENT_MISSING,
    FAIL_SIGNER_SERVICE_SOCKET_PATH_EXISTS,
    FAIL_SIGNER_SERVICE_SOCKET_PATH_INSIDE_REPO,
    FAIL_SIGNER_SERVICE_SOCKET_PATH_MISSING,
    FAIL_SIGNER_SERVICE_SOCKET_PATH_RELATIVE,
    SIGNER_SOCKET_SERVICE_REJECT,
    SIGNER_SOCKET_SERVICE_SERVED,
    serve_reddog_isolated_signer_socket_once,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    RuntimeRejectCode,
    SigningRequest,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_isolated_signer_socket_service.py"
)


class _AuditMacBuilder:
    def build(self, request: SigningRequest, signature: str, peer: SignerPeerAttestation) -> str:
        return "audit:" + request.payload_digest


class _StaticPeerAttestor:
    def __init__(self, principal_id: str = "github:mjtrout", *, attested: bool = True) -> None:
        self.principal_id = principal_id
        self.attested = attested

    def attest(self, connection):
        return SignerPeerAttestation(
            peer_principal_id=self.principal_id,
            transport="unix_socket",
            credential_source="test_peer_credential",
            boundary_attested=self.attested,
        )


def _repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    return path


def _socket_path(tmp_path: Path) -> Path:
    return Path(tempfile.gettempdir()) / f"rdog-{uuid.uuid4().hex}.sock"


def _public_key(private_key) -> str:
    from cryptography.hazmat.primitives import serialization

    return encode_ed25519_public_key(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )


def _backend():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.generate()
    public_key = _public_key(private_key)
    return (
        public_key,
        Ed25519SignerBackend(
            private_key=private_key,
            public_key=public_key,
            key_epoch="epoch-1",
            audit_mac_builder=_AuditMacBuilder(),
        ),
    )


def _request(public_key: str, **overrides: object) -> SigningRequest:
    payload = {
        "signing_input": 'reddog-workauth.v1.{"work_order_id":"wo-1"}',
        "payload_digest": "sha256:payload",
        "signer_role": "reddog",
        "signer_public_key": public_key,
        "requester_principal_id": "github:mjtrout",
        "nonce": "nonce-1",
        "key_epoch": "epoch-1",
        "requested_operation": "create_foundup",
        "authority_tier": "HIGH",
        "consensus_receipt_digest": "sha256:consensus",
    }
    payload.update(overrides)
    return SigningRequest(**payload)


def _serve_async(*, repo: Path, socket_path: Path, backend, peer_attestor=None):
    if not hasattr(socket, "AF_UNIX"):
        pytest.skip("AF_UNIX sockets are unavailable in this Python build")
    ready = threading.Event()
    result_box = {}

    def target() -> None:
        result_box["result"] = serve_reddog_isolated_signer_socket_once(
            repo_root=repo,
            socket_path=socket_path,
            backend=backend,
            peer_attestor=peer_attestor,
            timeout_s=5.0,
            ready_callback=ready.set,
        )

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    assert ready.wait(5.0)
    return thread, result_box


def test_socket_service_round_trips_real_client_and_ed25519_backend(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    socket_path = _socket_path(tmp_path)
    public_key, backend = _backend()
    thread, result_box = _serve_async(
        repo=repo,
        socket_path=socket_path,
        backend=backend,
        peer_attestor=_StaticPeerAttestor(),
    )

    response = RedDogIsolatedSignerSocketClient(
        socket_path=socket_path,
        timeout_s=5.0,
    ).sign(_request(public_key))
    thread.join(5.0)

    assert response.accepted is True
    assert Ed25519SignatureVerifier().verify(
        public_key,
        _request(public_key).signing_input,
        response.signature,
    ) is True
    result = result_box["result"]
    assert result.accepted is True
    assert result.status == SIGNER_SOCKET_SERVICE_SERVED
    assert result.request_handled is True
    assert result.response_digest.startswith("sha256:")
    assert result.socket_removed is True
    assert not socket_path.exists()
    assert result.no_private_key_loaded is True
    assert result.no_repo_mutation_performed is True
    assert result.no_holoindex_reindex_performed is True


def test_socket_service_default_peer_attestor_fails_closed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    socket_path = _socket_path(tmp_path)
    public_key, backend = _backend()
    thread, result_box = _serve_async(repo=repo, socket_path=socket_path, backend=backend)

    response = RedDogIsolatedSignerSocketClient(
        socket_path=socket_path,
        timeout_s=5.0,
    ).sign(_request(public_key))
    thread.join(5.0)

    assert response.accepted is False
    assert response.rejection_code == REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED
    assert result_box["result"].accepted is True
    assert result_box["result"].request_handled is True


def test_socket_service_default_backend_fails_closed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    socket_path = _socket_path(tmp_path)
    public_key, _backend_obj = _backend()
    thread, result_box = _serve_async(
        repo=repo,
        socket_path=socket_path,
        backend=None,
        peer_attestor=_StaticPeerAttestor(),
    )

    response = RedDogIsolatedSignerSocketClient(
        socket_path=socket_path,
        timeout_s=5.0,
    ).sign(_request(public_key))
    thread.join(5.0)

    assert response.accepted is False
    assert response.rejection_code == RuntimeRejectCode.SIGNER_NOT_CONFIGURED
    assert result_box["result"].accepted is True


def test_socket_service_path_guards_fail_before_binding(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    parent_missing = tmp_path / "missing" / "signer.sock"
    existing = _socket_path(tmp_path)
    existing.write_text("occupied", encoding="utf-8")

    cases = (
        (None, FAIL_SIGNER_SERVICE_SOCKET_PATH_MISSING),
        ("relative.sock", FAIL_SIGNER_SERVICE_SOCKET_PATH_RELATIVE),
        (repo / "signer.sock", FAIL_SIGNER_SERVICE_SOCKET_PATH_INSIDE_REPO),
        (parent_missing, FAIL_SIGNER_SERVICE_SOCKET_PARENT_MISSING),
        (existing, FAIL_SIGNER_SERVICE_SOCKET_PATH_EXISTS),
    )

    for value, reason in cases:
        result = serve_reddog_isolated_signer_socket_once(
            repo_root=repo,
            socket_path=value,
            timeout_s=0.01,
        )
        assert result.accepted is False
        assert result.status == SIGNER_SOCKET_SERVICE_REJECT
        assert reason in result.rejection_reasons


def test_socket_service_rejects_invalid_limits(tmp_path: Path) -> None:
    result = serve_reddog_isolated_signer_socket_once(
        repo_root=_repo(tmp_path),
        socket_path=_socket_path(tmp_path),
        max_request_bytes=16,
    )

    assert result.accepted is False
    assert FAIL_SIGNER_SERVICE_REQUEST_LIMIT_INVALID in result.rejection_reasons


def test_socket_service_module_has_no_spawn_repo_holoindex_or_key_loading_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "holo_index",
        "git",
        "hmac",
        "secrets",
    }
    banned_import_fragments = {
        "openclaw_supervisor",
        "hermes_job_executor",
        "vault_resolver",
        "reddog_wre_worktree_runner",
        "worktree_pr_runner",
        "cryptography",
        "ed25519_signer_backend",
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}
    banned_attrs = {
        "system",
        "popen",
        "spawn",
        "run",
        "Popen",
        "check_call",
        "check_output",
        "rmdir",
        "replace",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
                assert all(fragment not in alias.name for fragment in banned_import_fragments)
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
            assert all(fragment not in node.module for fragment in banned_import_fragments)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs
