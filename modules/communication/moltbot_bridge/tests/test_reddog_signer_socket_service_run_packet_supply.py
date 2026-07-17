"""Tests for REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_WSP71_PERMISSIONED,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
    SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_run_packet_supply import (
    FAIL_SIGNER_RUN_PACKET_CONFIG_MALFORMED,
    FAIL_SIGNER_RUN_PACKET_CONFIG_PATH_INVALID,
    FAIL_SIGNER_RUN_PACKET_LIMITS_INVALID,
    FAIL_SIGNER_RUN_PACKET_OP_EXECUTABLE_INVALID,
    FAIL_SIGNER_RUN_PACKET_OUTPUT_PATH_INVALID,
    SIGNER_SERVICE_RUN_PACKET_SCHEMA_VERSION,
    SIGNER_SERVICE_RUN_PACKET_SUPPLY_ACCEPT,
    run_reddog_signer_socket_service_run_packet_supply,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_signer_socket_service_run_packet_supply.py"
)


def _repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    return path


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _config(socket_path: Path, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
        "socket_path": str(socket_path),
        "provider_mode": PROVIDER_MODE_WSP71_PERMISSIONED,
        "allow_test_only_key_material": False,
        "permission_snapshot_fresh": True,
        "max_requests": 3,
        "timeout_s": 2.5,
        "max_request_bytes": 4096,
        "max_response_bytes": 8192,
        "key_provider_profiles": [
            {
                "signer_profile_id": "principal-profile",
                "signer_agent_id": "signer:principal",
                "signing_key_ref": "op://prod-vault/principal/private",
                "audit_mac_key_ref": "op://prod-vault/principal/audit",
                "expected_public_key": "ed25519-pub-v1:principal",
                "expected_key_fingerprint": "sha256:principal",
                "expected_key_epoch": "epoch-1",
                "permission_snapshot_digest": "sha256:permission",
                "ttl_seconds": 60,
            },
            {
                "signer_profile_id": "reddog-profile",
                "signer_agent_id": "signer:reddog",
                "signing_key_ref": "op://prod-vault/reddog/private",
                "audit_mac_key_ref": "op://prod-vault/reddog/audit",
                "expected_public_key": "ed25519-pub-v1:reddog",
                "expected_key_fingerprint": "sha256:reddog",
                "expected_key_epoch": "epoch-1",
                "permission_snapshot_digest": "sha256:permission",
                "ttl_seconds": 60,
            },
        ],
        "peer_policy": {
            "uid_to_principal": {"1001": "github:mjtrout"},
            "allowed_gids": [1002],
            "transport": "unix_socket",
            "credential_source_prefix": "kernel_peer_credential",
        },
    }
    payload.update(overrides)
    return payload


def test_run_packet_supply_writes_shell_free_signer_cli_argv(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    socket_path = runtime / "reddog-signer.sock"
    config_path = _write_json(runtime / "signer-service.json", _config(socket_path))
    packet_path = runtime / "signer-run-packet.json"

    result = run_reddog_signer_socket_service_run_packet_supply(
        repo_root=repo,
        config_path=config_path,
        output_path=packet_path,
        op_executable="op",
        op_timeout_s=11.5,
        ttl_seconds=300,
        session_id="signer-run-test",
        python_executable="python",
    )

    assert result.accepted is True
    assert result.status == SIGNER_SERVICE_RUN_PACKET_SUPPLY_ACCEPT
    assert result.run_packet_id and result.run_packet_id.startswith("sha256:")
    assert result.run_packet_digest and result.run_packet_digest.startswith("sha256:")
    assert result.config_digest and result.config_digest.startswith("sha256:")
    assert result.profile_count == 2
    assert result.no_process_spawned is True
    assert result.no_shell_command_emitted is True
    assert result.no_holoindex_reindex_performed is True
    assert packet_path.exists()

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["schema_version"] == SIGNER_SERVICE_RUN_PACKET_SCHEMA_VERSION
    assert packet["run_mode"] == "signer_owned_cli_sidecar"
    assert packet["config_path"] == str(config_path.resolve())
    assert packet["socket_path"] == str(socket_path.resolve())
    assert packet["profile_count"] == 2
    assert packet["shell_required"] is False
    assert packet["shell_command"] is None
    assert packet["redDog_must_not_spawn"] is True
    assert packet["main_py_must_not_spawn"] is True
    argv = packet["argv"]
    assert isinstance(argv, list)
    assert argv[:3] == [
        "python",
        "-m",
        "modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_cli",
    ]
    assert "--config" in argv
    assert argv[argv.index("--config") + 1] == str(config_path.resolve())
    assert "--op-executable" in argv
    assert argv[argv.index("--op-executable") + 1] == "op"
    assert "--op-timeout-s" in argv
    assert argv[argv.index("--op-timeout-s") + 1] == "11.5"
    serialized = json.dumps(packet, sort_keys=True)
    assert "ed25519-private-raw-b64-v1" not in serialized
    assert "audit-mac-test-key-b64-v1" not in serialized


def test_run_packet_supply_rejects_config_inside_repo_missing_or_malformed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    output = runtime / "run-packet.json"
    missing = run_reddog_signer_socket_service_run_packet_supply(
        repo_root=repo,
        config_path=runtime / "missing.json",
        output_path=output,
    )
    inside = run_reddog_signer_socket_service_run_packet_supply(
        repo_root=repo,
        config_path=_write_json(repo / "signer-service.json", _config(runtime / "socket.sock")),
        output_path=output,
    )
    wrong_schema = _config(runtime / "socket.sock", schema_version="wrong")
    malformed = run_reddog_signer_socket_service_run_packet_supply(
        repo_root=repo,
        config_path=_write_json(runtime / "bad-config.json", wrong_schema),
        output_path=output,
    )

    assert FAIL_SIGNER_RUN_PACKET_CONFIG_PATH_INVALID in missing.rejection_reasons
    assert FAIL_SIGNER_RUN_PACKET_CONFIG_PATH_INVALID in inside.rejection_reasons
    assert FAIL_SIGNER_RUN_PACKET_CONFIG_MALFORMED in malformed.rejection_reasons


def test_run_packet_supply_rejects_bad_output_op_and_limits(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    config_path = _write_json(runtime / "signer-service.json", _config(runtime / "socket.sock"))

    inside_output = run_reddog_signer_socket_service_run_packet_supply(
        repo_root=repo,
        config_path=config_path,
        output_path=repo / "run-packet.json",
    )
    bad_op = run_reddog_signer_socket_service_run_packet_supply(
        repo_root=repo,
        config_path=config_path,
        output_path=runtime / "run-packet.json",
        op_executable="powershell",
    )
    bad_limits = run_reddog_signer_socket_service_run_packet_supply(
        repo_root=repo,
        config_path=config_path,
        output_path=runtime / "run-packet.json",
        ttl_seconds=0,
    )

    assert FAIL_SIGNER_RUN_PACKET_OUTPUT_PATH_INVALID in inside_output.rejection_reasons
    assert FAIL_SIGNER_RUN_PACKET_OP_EXECUTABLE_INVALID in bad_op.rejection_reasons
    assert FAIL_SIGNER_RUN_PACKET_LIMITS_INVALID in bad_limits.rejection_reasons


def test_run_packet_supply_module_has_no_spawn_shell_or_runtime_authority_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
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
