"""Tests for REDDOG_SIGNER_SERVICE_HEALTHCHECK_PREFLIGHT_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_mutual_peer_handshake import (
    canonical_signer_peer_response_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_WSP71_PERMISSIONED,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
    SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_healthcheck import (
    FAIL_SIGNER_HEALTHCHECK_MANIFEST_BINDING_REQUIRED,
    FAIL_SIGNER_HEALTHCHECK_CLIENT_REJECTED,
    FAIL_SIGNER_HEALTHCHECK_CONFIG_MISMATCH,
    FAIL_SIGNER_HEALTHCHECK_PROFILE_MISSING,
    FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED,
    FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_PATH_INVALID,
    FAIL_SIGNER_HEALTHCHECK_SIGNER_REJECTED,
    SIGNER_SERVICE_HEALTHCHECK_READY,
    run_reddog_signer_socket_service_healthcheck,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_run_packet_supply import (
    run_reddog_signer_socket_service_run_packet_supply,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_signer_socket_service_healthcheck.py"
)
_PRINCIPAL_PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
_REDDOG_PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))


def _public_key(private_key: Ed25519PrivateKey) -> str:
    return encode_ed25519_public_key(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )


_PRINCIPAL_PUBLIC_KEY = _public_key(_PRINCIPAL_PRIVATE_KEY)
_REDDOG_PUBLIC_KEY = _public_key(_REDDOG_PRIVATE_KEY)


def _repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    return path


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _config(socket_path: Path, **overrides: object) -> dict[str, object]:
    runtime_root = socket_path.parent.resolve()
    signer_runtime_root = (
        runtime_root.parent / f"{runtime_root.name}-signer-state"
    ).resolve()
    payload: dict[str, object] = {
        "schema_version": SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
        "runtime_root": str(runtime_root),
        "signer_runtime_root": str(signer_runtime_root),
        "socket_path": str(socket_path.resolve()),
        "control_loop_anchor_path": str(
            signer_runtime_root / "signer_control_loop_anchor.json"
        ),
        "control_loop_authority_policy": {
            "issuer_principal_id": "github:mjtrout",
            "signer_public_key": _REDDOG_PUBLIC_KEY,
            "key_epoch": "epoch-1",
            "consensus_receipt_digest": "sha256:" + "1" * 64,
            "authority_profile_digest": "sha256:" + "2" * 64,
            "authority_profile_source_receipt_id": "sha256:" + "3" * 64,
        },
        "provider_mode": PROVIDER_MODE_WSP71_PERMISSIONED,
        "allow_test_only_key_material": False,
        "permission_snapshot_fresh": True,
        "max_requests": 3,
        "timeout_s": 2.5,
        "max_request_bytes": 4096,
        "max_response_bytes": 8192,
        "key_provider_profiles": _key_provider_profiles(),
        "peer_policy": {
            "uid_to_principal": {"1001": "github:mjtrout"},
            "allowed_gids": [1002],
            "transport": "unix_socket",
            "credential_source_prefix": "kernel_peer_credential",
        },
    }
    payload.update(overrides)
    return payload


def _key_provider_profiles() -> list[dict[str, object]]:
    return [
        {
            "signer_profile_id": "principal-identity",
            "signer_agent_id": "signer:principal",
            "signing_key_ref": "op://prod-vault/principal/private",
            "audit_mac_key_ref": "op://prod-vault/principal/audit",
            "expected_public_key": _PRINCIPAL_PUBLIC_KEY,
            "expected_key_fingerprint": public_key_fingerprint(
                _PRINCIPAL_PUBLIC_KEY
            ),
            "expected_key_epoch": "epoch-1",
            "permission_snapshot_digest": "sha256:" + "4" * 64,
            "ttl_seconds": 60,
        },
        {
            "signer_profile_id": "reddog-work-authority",
            "signer_agent_id": "signer:reddog",
            "signing_key_ref": "op://prod-vault/reddog/private",
            "audit_mac_key_ref": "op://prod-vault/reddog/audit",
            "expected_public_key": _REDDOG_PUBLIC_KEY,
            "expected_key_fingerprint": public_key_fingerprint(
                _REDDOG_PUBLIC_KEY
            ),
            "expected_key_epoch": "epoch-1",
            "permission_snapshot_digest": "sha256:" + "4" * 64,
            "ttl_seconds": 60,
        },
    ]


def _packet(repo: Path, runtime: Path, *, config_payload: dict[str, object] | None = None) -> Path:
    config_path = _write_json(
        runtime / "signer-service.json",
        config_payload or _config(runtime / "signer.sock"),
    )
    packet_path = runtime / "signer-run-packet.json"
    result = run_reddog_signer_socket_service_run_packet_supply(
        repo_root=repo,
        config_path=config_path,
        output_path=packet_path,
        owner_authority_config_path=(
            runtime.parent / "signer-owner" / "owner.json"
        ),
        python_executable="python",
    )
    assert result.accepted is True
    return packet_path


def _accepted_connector(_path: Path, request: bytes, _timeout: float, _max_bytes: int) -> bytes:
    decoded = json.loads(request.decode("utf-8"))
    signing_request = SigningRequest(**decoded["request"])
    public_key = signing_request.signer_public_key
    signature = encode_ed25519_signature(
        _REDDOG_PRIVATE_KEY.sign(
            signing_request.signing_input.encode("utf-8")
        )
    )
    response = SigningResponse(
        accepted=True,
        signature=signature,
        signer_public_key=public_key,
        key_fingerprint=public_key_fingerprint(public_key),
        key_epoch="epoch-1",
        audit_mac="audit:healthcheck",
        boundary_attested=True,
        requester_identity_attested=True,
        signer_loads_no_untrusted_code=True,
        no_secret_material_returned=True,
    )
    response = SigningResponse(
        **{
            **response.to_dict(),
            "audit_attestation_signature": encode_ed25519_signature(
                _REDDOG_PRIVATE_KEY.sign(
                    canonical_signer_peer_response_attestation_input(
                        signing_request, response
                    ).encode("utf-8")
                )
            ),
        }
    )
    return (
        json.dumps(response.to_dict(), sort_keys=True)
        + "\n"
    ).encode("utf-8")


MANIFEST_ID = "sha256:" + "1" * 64
ARTIFACT_GENERATION_DIGEST = "sha256:" + "2" * 64


def _manifest_bindings() -> dict[str, str]:
    return {
        "manifest_id": MANIFEST_ID,
        "artifact_generation_digest": ARTIFACT_GENERATION_DIGEST,
    }


def test_healthcheck_validates_run_packet_config_and_returns_digests_only(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    packet_path = _packet(repo, runtime)

    result = run_reddog_signer_socket_service_healthcheck(
        repo_root=repo,
        run_packet_path=packet_path,
        connector=_accepted_connector,
        **_manifest_bindings(),
    )

    assert result.accepted is True
    assert result.status == SIGNER_SERVICE_HEALTHCHECK_READY
    assert result.run_packet_path == str(packet_path.resolve())
    assert result.run_packet_id and result.run_packet_id.startswith("sha256:")
    assert result.config_digest and result.config_digest.startswith("sha256:")
    assert result.socket_path == str((runtime / "signer.sock").resolve())
    assert result.signer_profile_id == "reddog-work-authority"
    assert result.signer_public_key == _REDDOG_PUBLIC_KEY
    assert result.requester_principal_id == "github:mjtrout"
    assert result.request_digest and result.request_digest.startswith("sha256:")
    assert result.response_digest and result.response_digest.startswith("sha256:")
    assert result.peer_handshake_verified is True
    assert result.manifest_id == MANIFEST_ID
    assert result.artifact_generation_digest == ARTIFACT_GENERATION_DIGEST
    assert result.peer_handshake_expires_at is not None
    assert result.no_signature_value_returned is True
    serialized = json.dumps(result.to_dict(), sort_keys=True)
    assert "sig:healthcheck" not in serialized


def test_healthcheck_rejects_missing_malformed_or_tampered_packets(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    missing = run_reddog_signer_socket_service_healthcheck(
        repo_root=repo,
        run_packet_path=runtime / "missing.json",
        connector=_accepted_connector,
    )
    malformed = run_reddog_signer_socket_service_healthcheck(
        repo_root=repo,
        run_packet_path=_write_json(runtime / "bad-packet.json", {"schema_version": "wrong"}),
        connector=_accepted_connector,
    )
    packet_path = _packet(repo, runtime)
    packet_payload = json.loads(packet_path.read_text(encoding="utf-8"))
    packet_payload["shell_required"] = True
    tampered_packet_path = _write_json(runtime / "tampered-packet.json", packet_payload)
    tampered_packet = run_reddog_signer_socket_service_healthcheck(
        repo_root=repo,
        run_packet_path=tampered_packet_path,
        connector=_accepted_connector,
    )
    config_path = Path(json.loads(packet_path.read_text(encoding="utf-8"))["config_path"])
    config_payload = json.loads(config_path.read_text(encoding="utf-8"))
    config_payload["max_requests"] = 99
    _write_json(config_path, config_payload)
    tampered_config = run_reddog_signer_socket_service_healthcheck(
        repo_root=repo,
        run_packet_path=packet_path,
        connector=_accepted_connector,
    )

    assert FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_PATH_INVALID in missing.rejection_reasons
    assert FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED in malformed.rejection_reasons
    assert FAIL_SIGNER_HEALTHCHECK_RUN_PACKET_MALFORMED in tampered_packet.rejection_reasons
    assert FAIL_SIGNER_HEALTHCHECK_CONFIG_MISMATCH in tampered_config.rejection_reasons


def test_healthcheck_rejects_missing_profile_and_signer_rejection(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    no_reddog = _config(runtime / "signer.sock")
    no_reddog["key_provider_profiles"] = [no_reddog["key_provider_profiles"][0]]
    no_reddog["control_loop_authority_policy"]["signer_public_key"] = (
        _PRINCIPAL_PUBLIC_KEY
    )
    missing_profile = run_reddog_signer_socket_service_healthcheck(
        repo_root=repo,
        run_packet_path=_packet(repo, runtime, config_payload=no_reddog),
        connector=_accepted_connector,
    )

    reject_packet = _packet(repo, tmp_path / "runtime2")
    signer_reject = run_reddog_signer_socket_service_healthcheck(
        repo_root=repo,
        run_packet_path=reject_packet,
        connector=lambda *_: b'{"accepted":false,"rejection_code":"REJECT_TEST"}\n',
        **_manifest_bindings(),
    )

    assert FAIL_SIGNER_HEALTHCHECK_PROFILE_MISSING in missing_profile.rejection_reasons
    assert FAIL_SIGNER_HEALTHCHECK_SIGNER_REJECTED in signer_reject.rejection_reasons
    assert "REJECT_TEST" in signer_reject.rejection_reasons


def test_healthcheck_rejects_unavailable_socket_without_connector(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    packet_path = _packet(repo, runtime)

    result = run_reddog_signer_socket_service_healthcheck(
        repo_root=repo,
        run_packet_path=packet_path,
        **_manifest_bindings(),
    )

    assert result.accepted is False
    assert FAIL_SIGNER_HEALTHCHECK_CLIENT_REJECTED in result.rejection_reasons


def test_healthcheck_never_accepts_an_unbound_manifest(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    packet_path = _packet(repo, tmp_path / "runtime")
    called = False

    def connector(*_args):
        nonlocal called
        called = True
        return _accepted_connector(*_args)

    result = run_reddog_signer_socket_service_healthcheck(
        repo_root=repo,
        run_packet_path=packet_path,
        connector=connector,
    )

    assert result.accepted is False
    assert FAIL_SIGNER_HEALTHCHECK_MANIFEST_BINDING_REQUIRED in (
        result.rejection_reasons
    )
    assert called is False


def test_healthcheck_rejects_all_zero_manifest_binding_before_connect(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    packet_path = _packet(repo, tmp_path / "runtime")
    called = False

    def connector(*_args):
        nonlocal called
        called = True
        return _accepted_connector(*_args)

    result = run_reddog_signer_socket_service_healthcheck(
        repo_root=repo,
        run_packet_path=packet_path,
        connector=connector,
        manifest_id="sha256:" + "0" * 64,
        artifact_generation_digest=ARTIFACT_GENERATION_DIGEST,
    )

    assert result.accepted is False
    assert FAIL_SIGNER_HEALTHCHECK_MANIFEST_BINDING_REQUIRED in (
        result.rejection_reasons
    )
    assert called is False


def test_healthcheck_module_has_no_spawn_secret_resolution_or_runtime_authority_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
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
    }
    banned_name_fragments = ("openclaw", "hermes", "holoindex")

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
