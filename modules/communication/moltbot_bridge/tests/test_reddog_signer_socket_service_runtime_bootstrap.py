"""Tests for REDDOG_SIGNER_SOCKET_SERVICE_RUNTIME_BOOTSTRAP_PHASE1."""

from __future__ import annotations

import ast
import base64
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import (
    SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
    IsolatedSignerSocketResidentServiceResult,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    AUDIT_KEY_PREFIX,
    PROVIDER_MODE_WSP71_PERMISSIONED,
    SIGNING_KEY_PREFIX,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_bootstrap import (
    FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED,
    FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_INSIDE_REPO,
    FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_MISSING,
    FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_RELATIVE,
    FAIL_SIGNER_BOOTSTRAP_CONFIG_UNREADABLE,
    FAIL_SIGNER_BOOTSTRAP_RUNTIME_REJECTED,
    SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT,
    SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED,
    run_reddog_signer_socket_service_runtime_bootstrap,
)
from modules.infrastructure.secrets_mcp.src.vault_resolver import ResolveResult, hash_reference


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_signer_socket_service_runtime_bootstrap.py"
)


pytest.importorskip("cryptography")


class FakeResolver:
    def __init__(self, values: dict[str, str], ttl: int = 60) -> None:
        self.values = values
        self.ttl = ttl
        self.calls: list[tuple[str, str | None]] = []

    def resolve(self, reference: str, requester_id: str | None = None) -> ResolveResult:
        self.calls.append((reference, requester_id))
        return ResolveResult(
            success=True,
            reference=reference,
            reference_hash=hash_reference(reference),
            ttl_remaining=self.ttl,
            session_id="wsp71-session",
            _secret_value=self.values[reference],
        )


class CapturingBoundedService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return IsolatedSignerSocketResidentServiceResult(
            accepted=True,
            status=SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
            rejection_reasons=(),
            socket_path=str(kwargs["socket_path"]),
            requests_handled=int(kwargs["max_requests"]),
            response_digests=("sha256:response",),
            socket_removed=True,
        )


def _repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    return path


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
            "op://prod-vault/reddog-signing/private": _private_key_secret(private_key),
            "op://prod-vault/reddog-audit/mac": _audit_secret(),
        }
    )


def _config(public_key: str, *, socket_path: Path, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "socket_path": str(socket_path),
        "provider_mode": PROVIDER_MODE_WSP71_PERMISSIONED,
        "allow_test_only_key_material": False,
        "permission_snapshot_fresh": True,
        "max_requests": 3,
        "timeout_s": 2.5,
        "max_request_bytes": 4096,
        "max_response_bytes": 8192,
        "key_provider_profile": {
            "signer_profile_id": "signer-profile-1",
            "signer_agent_id": "signer:reddog-authority",
            "signing_key_ref": "op://prod-vault/reddog-signing/private",
            "audit_mac_key_ref": "op://prod-vault/reddog-audit/mac",
            "expected_public_key": public_key,
            "expected_key_fingerprint": public_key_fingerprint(public_key),
            "expected_key_epoch": "epoch-1",
            "permission_snapshot_digest": "sha256:permission",
            "ttl_seconds": 60,
        },
        "peer_policy": {
            "uid_to_principal": {"1001": "github:mjtrout"},
            "allowed_gids": [1002],
            "transport": "unix_socket",
            "credential_source_prefix": "kernel_peer_credential",
        },
    }
    values.update(overrides)
    return values


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def test_bootstrap_reads_outside_repo_config_and_runs_runtime_wiring(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    private_key = _private_key()
    public_key = _public_text(private_key)
    config_path = _write_json(
        runtime / "signer-service.json",
        _config(public_key, socket_path=runtime / "signer.sock"),
    )
    resolver = _resolver(private_key)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=config_path,
        resolver=resolver,
        serve_bounded=service,
    )

    assert result.accepted is True
    assert result.status == SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED
    assert result.config_path == str(config_path.resolve())
    assert result.config_digest and result.config_digest.startswith("sha256:")
    assert result.runtime_result is not None
    assert result.runtime_result["status"] == "SIGNER_SOCKET_RUNTIME_WIRING_SERVED"
    assert len(service.calls) == 1
    assert service.calls[0]["max_requests"] == 3
    assert resolver.calls == [
        ("op://prod-vault/reddog-signing/private", "signer:reddog-authority"),
        ("op://prod-vault/reddog-audit/mac", "signer:reddog-authority"),
    ]
    assert result.no_env_parsed is True
    assert result.no_holoindex_reindex_performed is True


def test_bootstrap_rejects_missing_relative_inside_and_unreadable_config(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    inside = _write_json(repo / "signer-service.json", {})
    malformed = tmp_path / "runtime" / "bad.json"
    malformed.parent.mkdir(parents=True, exist_ok=True)
    malformed.write_text("{not-json", encoding="utf-8")

    missing = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=None,
        resolver=object(),  # type: ignore[arg-type]
        serve_bounded=CapturingBoundedService(),
    )
    relative = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path="signer.json",
        resolver=object(),  # type: ignore[arg-type]
        serve_bounded=CapturingBoundedService(),
    )
    inside_repo = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=inside,
        resolver=object(),  # type: ignore[arg-type]
        serve_bounded=CapturingBoundedService(),
    )
    unreadable = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=malformed,
        resolver=object(),  # type: ignore[arg-type]
        serve_bounded=CapturingBoundedService(),
    )

    assert missing.status == SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT
    assert FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_MISSING in missing.rejection_reasons
    assert FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_RELATIVE in relative.rejection_reasons
    assert FAIL_SIGNER_BOOTSTRAP_CONFIG_PATH_INSIDE_REPO in inside_repo.rejection_reasons
    assert FAIL_SIGNER_BOOTSTRAP_CONFIG_UNREADABLE in unreadable.rejection_reasons


def test_bootstrap_rejects_malformed_runtime_shape_and_preserves_runtime_reject(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    private_key = _private_key()
    public_key = _public_text(private_key)
    malformed = _write_json(runtime / "malformed.json", {"key_provider_profile": []})
    rejected = _write_json(
        runtime / "rejected.json",
        _config(
            public_key,
            socket_path=runtime / "signer.sock",
            allow_test_only_key_material=True,
        ),
    )

    malformed_result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=malformed,
        resolver=_resolver(private_key),
        serve_bounded=CapturingBoundedService(),
    )
    rejected_result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=rejected,
        resolver=_resolver(private_key),
        serve_bounded=CapturingBoundedService(),
    )

    assert FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED in malformed_result.rejection_reasons
    assert FAIL_SIGNER_BOOTSTRAP_RUNTIME_REJECTED in rejected_result.rejection_reasons
    assert rejected_result.runtime_result is not None
    assert rejected_result.runtime_result["accepted"] is False


def test_bootstrap_module_has_no_env_shell_repo_openclaw_hermes_or_holoindex_surface() -> None:
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
