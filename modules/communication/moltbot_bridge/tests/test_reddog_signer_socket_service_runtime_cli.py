"""Tests for REDDOG_SIGNER_SOCKET_SERVICE_RUNTIME_CLI_PHASE1."""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import sys
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
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
    SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_cli import (
    SIGNER_SOCKET_SERVICE_RUNTIME_CLI_ACCEPT,
    SIGNER_SOCKET_SERVICE_RUNTIME_CLI_REJECT,
    run_reddog_signer_socket_service_runtime_cli,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_bootstrap import (
    FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_run_packet_supply import (
    run_reddog_signer_socket_service_run_packet_supply,
)
from modules.infrastructure.secrets_mcp.src.vault_resolver import ResolveResult, hash_reference


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_signer_socket_service_runtime_cli.py"
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
            session_id="wsp71-session",
            _secret_value=value,
        )


class CapturingResolverFactory:
    def __init__(self, resolver: FakeResolver) -> None:
        self.resolver = resolver
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.resolver


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


class _ManifestSelection:
    pass


class _ManifestSelectionBoundary:
    def __init__(self, capability: object, values: dict[str, object]) -> None:
        self._capability = capability
        self._values = values

    def consume(self, value: object) -> dict[str, object]:
        if value is not self._capability:
            raise ValueError("manifest_selection_unverified")
        self._capability = None
        return dict(self._values)


def _manifest_selection_loader(
    *,
    repo_root: Path,
    config_path: Path,
    run_packet_path: Path,
) -> tuple[object, _ManifestSelectionBoundary]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    capability = _ManifestSelection()
    values = {
        "manifest_id": "sha256:" + ("a" * 64),
        "artifact_generation_digest": "sha256:" + ("b" * 64),
        "config_digest": _payload_digest(config),
        "config_raw_digest": _raw_digest(config_path),
        "run_packet_digest": _raw_digest(run_packet_path),
        "repo_root": str(repo_root.resolve()),
        "runtime_root": str(config_path.parent.resolve()),
        "config_path": str(config_path.resolve()),
        "run_packet_path": str(run_packet_path.resolve()),
    }
    return capability, _ManifestSelectionBoundary(capability, values)


def _payload_digest(value: object) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _raw_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


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


def _repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    return path


def _config(public_key: str, *, socket_path: Path) -> dict[str, object]:
    signer_runtime = (
        socket_path.parent.parent / f"{socket_path.parent.name}-signer-state"
    )
    return {
        "schema_version": SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
        "runtime_root": str(socket_path.parent),
        "signer_runtime_root": str(signer_runtime),
        "socket_path": str(socket_path),
        "control_loop_anchor_path": str(signer_runtime / "anchor.json"),
        "control_loop_authority_policy": {
            "issuer_principal_id": "github:012",
            "signer_public_key": public_key,
            "key_epoch": "epoch-1",
            "consensus_receipt_digest": "sha256:" + ("1" * 64),
            "authority_profile_digest": "sha256:" + ("2" * 64),
            "authority_profile_source_receipt_id": "sha256:" + ("3" * 64),
        },
        "provider_mode": PROVIDER_MODE_WSP71_PERMISSIONED,
        "allow_test_only_key_material": False,
        "permission_snapshot_fresh": True,
        "max_requests": 2,
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


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def test_cli_runs_signer_bootstrap_with_wsp71_resolver_and_emits_safe_receipt(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    private_key = _private_key()
    public_key = _public_text(private_key)
    config = _write_json(
        runtime / "signer-service.json",
        _config(public_key, socket_path=runtime / "signer.sock"),
    )
    resolver = FakeResolver(
        {
            "op://prod-vault/reddog-signing/private": _private_key_secret(private_key),
            "op://prod-vault/reddog-audit/mac": _audit_secret(),
        }
    )
    resolver_factory = CapturingResolverFactory(resolver)
    service = CapturingBoundedService()
    emitted: list[str] = []
    payload = json.loads(config.read_text(encoding="utf-8"))
    payload["key_provider_profiles"] = [payload.pop("key_provider_profile")]
    _write_json(config, payload)
    packet = runtime / "signer-run-packet.json"
    supplied = run_reddog_signer_socket_service_run_packet_supply(
        repo_root=repo,
        config_path=config,
        output_path=packet,
        op_executable="C:/Program Files/1Password/op.exe",
        op_timeout_s=7,
        ttl_seconds=61,
        session_id="session-prod",
        python_executable=sys.executable,
    )
    assert supplied.accepted is True

    code = run_reddog_signer_socket_service_runtime_cli(
        [
            "--repo-root",
            str(repo),
            "--config",
            str(config),
            "--expected-config-digest",
            str(supplied.config_digest),
            "--run-packet",
            str(packet),
            "--op-executable",
            "C:/Program Files/1Password/op.exe",
            "--op-timeout-s",
            "7",
            "--ttl-seconds",
            "61",
            "--session-id",
            "session-prod",
        ],
        resolver_factory=resolver_factory,
        serve_bounded=service,
        emit=emitted.append,
        manifest_selection_loader=_manifest_selection_loader,
    )

    assert code == 0
    payload = json.loads(emitted[0])
    assert payload["status"] == SIGNER_SOCKET_SERVICE_RUNTIME_CLI_ACCEPT
    assert payload["result"]["accepted"] is True
    assert payload["no_main_runtime_wiring"] is True
    assert payload["no_holoindex_reindex_performed"] is True
    assert resolver_factory.calls == [
        {
            "op_executable": "C:/Program Files/1Password/op.exe",
            "timeout_s": 7.0,
            "ttl_seconds": 61,
            "session_id": "session-prod",
        }
    ]
    assert resolver.calls == [
        ("op://prod-vault/reddog-signing/private", "signer:reddog-authority"),
        ("op://prod-vault/reddog-audit/mac", "signer:reddog-authority"),
    ]
    assert len(service.calls) == 1
    text = emitted[0]
    assert SIGNING_KEY_PREFIX not in text
    assert AUDIT_KEY_PREFIX not in text
    assert "0123456789abcdef" not in text


def test_cli_rejects_unsafe_config_before_service_call(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    inside = _write_json(repo / "signer-service.json", {})
    resolver_factory = CapturingResolverFactory(FakeResolver({}))
    service = CapturingBoundedService()
    emitted: list[str] = []

    code = run_reddog_signer_socket_service_runtime_cli(
        ["--repo-root", str(repo), "--config", str(inside)],
        resolver_factory=resolver_factory,
        serve_bounded=service,
        emit=emitted.append,
    )

    assert code == 2
    payload = json.loads(emitted[0])
    assert payload["status"] == SIGNER_SOCKET_SERVICE_RUNTIME_CLI_REJECT
    assert payload["result"]["accepted"] is False
    assert payload["result"]["rejection_reasons"] == [
        FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION
    ]
    assert resolver_factory.calls == []
    assert service.calls == []


def test_cli_module_has_no_main_openclaw_hermes_or_repo_mutation_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {"os", "subprocess", "holo_index", "git"}
    banned_import_fragments = {"openclaw", "hermes", "worktree", "github"}
    banned_name_calls = {"eval", "exec", "compile", "__import__", "open"}
    banned_attrs = {"system", "popen", "remove", "unlink", "rmdir", "replace"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = {alias.name.split(".", 1)[0] for alias in node.names}
            assert not roots & banned_import_roots
            assert all(
                fragment not in alias.name.lower()
                for alias in node.names
                for fragment in banned_import_fragments
            )
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            root = module.split(".", 1)[0]
            assert root not in banned_import_roots
            lowered = module.lower()
            assert all(fragment not in lowered for fragment in banned_import_fragments)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_name_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs
