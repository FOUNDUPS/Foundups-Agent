"""Tests for REDDOG_ISOLATED_SIGNER_SOCKET_CLIENT_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    FAIL_SIGNER_SOCKET_DEVICE_PREFIX,
    FAIL_SIGNER_SOCKET_PATH_INSIDE_REPO,
    FAIL_SIGNER_SOCKET_PATH_MISSING,
    FAIL_SIGNER_SOCKET_PATH_RELATIVE,
    REJECT_SIGNER_SOCKET_CONNECT_FAILED,
    REJECT_SIGNER_SOCKET_RESPONSE_INVALID,
    REJECT_SIGNER_SOCKET_RESPONSE_TOO_LARGE,
    SIGNER_SOCKET_CLIENT_READY,
    SIGNER_SOCKET_CLIENT_REJECT,
    build_reddog_isolated_signer_socket_client,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_isolated_signer_socket_client.py"
)


def _repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    return path


def _socket_path(tmp_path: Path) -> Path:
    path = tmp_path / "runtime" / "signer.sock"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _request() -> SigningRequest:
    return SigningRequest(
        signing_input='reddog-workauth.v1.{"work_order_id":"wo-1"}',
        payload_digest="sha256:payload",
        signer_role="reddog",
        signer_public_key="pub:reddog",
        requester_principal_id="github:mjtrout",
        nonce="nonce-1",
        key_epoch="epoch-1",
        requested_operation="create_foundup",
        authority_tier="HIGH",
        consensus_receipt_digest="sha256:consensus",
    )


def _accepted_response() -> bytes:
    return (
        json.dumps(
            {
                "accepted": True,
                "signature": "sig:abc",
                "signer_public_key": "pub:reddog",
                "key_fingerprint": "sha256:fingerprint",
                "key_epoch": "epoch-1",
                "audit_mac": "audit:mac",
                "boundary_attested": True,
                "requester_identity_attested": True,
                "signer_loads_no_untrusted_code": True,
                "no_secret_material_returned": True,
            },
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def test_build_rejects_missing_relative_inside_repo_and_device_paths(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    missing = build_reddog_isolated_signer_socket_client(repo_root=repo, socket_path=None)
    assert missing.accepted is False
    assert missing.status == SIGNER_SOCKET_CLIENT_REJECT
    assert FAIL_SIGNER_SOCKET_PATH_MISSING in missing.rejection_reasons

    relative = build_reddog_isolated_signer_socket_client(repo_root=repo, socket_path="signer.sock")
    assert relative.accepted is False
    assert FAIL_SIGNER_SOCKET_PATH_RELATIVE in relative.rejection_reasons

    inside = build_reddog_isolated_signer_socket_client(repo_root=repo, socket_path=repo / "signer.sock")
    assert inside.accepted is False
    assert FAIL_SIGNER_SOCKET_PATH_INSIDE_REPO in inside.rejection_reasons

    device = build_reddog_isolated_signer_socket_client(repo_root=repo, socket_path="\\\\?\\C:\\tmp\\signer.sock")
    assert device.accepted is False
    assert FAIL_SIGNER_SOCKET_DEVICE_PREFIX in device.rejection_reasons


def test_client_sends_signing_request_and_returns_attested_response(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    socket_path = _socket_path(tmp_path)
    observed: dict[str, object] = {}

    def connector(path: Path, payload: bytes, timeout_s: float, max_response_bytes: int) -> bytes:
        observed["path"] = str(path)
        observed["timeout_s"] = timeout_s
        observed["max_response_bytes"] = max_response_bytes
        observed["payload"] = json.loads(payload.decode("utf-8"))
        return _accepted_response()

    built = build_reddog_isolated_signer_socket_client(
        repo_root=repo,
        socket_path=socket_path,
        connector=connector,
    )
    assert built.accepted is True
    assert built.status == SIGNER_SOCKET_CLIENT_READY
    assert built.client is not None
    response = built.client.sign(_request())

    assert response.accepted is True
    assert response.signature == "sig:abc"
    assert response.boundary_attested is True
    assert response.requester_identity_attested is True
    assert response.signer_loads_no_untrusted_code is True
    assert response.no_secret_material_returned is True
    assert observed["path"] == str(socket_path.resolve())
    payload = observed["payload"]
    assert isinstance(payload, dict)
    assert payload["schema_version"] == "reddog_signer_socket_request.v1"
    assert payload["request"]["signer_role"] == "reddog"


def test_client_rejects_malformed_oversized_and_connector_failures(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    socket_path = _socket_path(tmp_path)

    malformed = build_reddog_isolated_signer_socket_client(
        repo_root=repo,
        socket_path=socket_path,
        connector=lambda *_: b"not-json",
    )
    assert malformed.client is not None
    assert malformed.client.sign(_request()).rejection_code == REJECT_SIGNER_SOCKET_RESPONSE_INVALID

    oversized = build_reddog_isolated_signer_socket_client(
        repo_root=repo,
        socket_path=socket_path,
        max_response_bytes=1024,
        connector=lambda *_: b"{" + (b" " * 2048) + b"}",
    )
    assert oversized.client is not None
    assert oversized.client.sign(_request()).rejection_code == REJECT_SIGNER_SOCKET_RESPONSE_TOO_LARGE

    def failing_connector(*_: object) -> bytes:
        raise OSError("connect failed")

    failed = build_reddog_isolated_signer_socket_client(
        repo_root=repo,
        socket_path=socket_path,
        connector=failing_connector,
    )
    assert failed.client is not None
    assert failed.client.sign(_request()).rejection_code == REJECT_SIGNER_SOCKET_CONNECT_FAILED


def test_client_preserves_signer_rejection_without_secret_material(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    socket_path = _socket_path(tmp_path)

    built = build_reddog_isolated_signer_socket_client(
        repo_root=repo,
        socket_path=socket_path,
        connector=lambda *_: b'{"accepted":false,"rejection_code":"REJECT_RATE_LIMIT"}\n',
    )

    assert built.client is not None
    response = built.client.sign(_request())
    assert response.accepted is False
    assert response.rejection_code == "REJECT_RATE_LIMIT"
    assert response.no_secret_material_returned is True


def test_module_has_no_shell_env_holoindex_openclaw_hermes_or_key_loading() -> None:
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
        "os",
    }
    banned_import_fragments = {
        "openclaw_supervisor",
        "hermes_job_executor",
        "worktree_pr_runner",
        "reddog_wre_worktree_runner",
        "pattern_memory",
        "vault_resolver",
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
        "getenv",
        "environ",
        "unlink",
        "remove",
        "rmdir",
        "rename",
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
