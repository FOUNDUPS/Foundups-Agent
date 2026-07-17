"""Tests for REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY_PHASE1 main preflight."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_WSP71_PERMISSIONED,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
    SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
    PROFILE_SIGNED_0102_BOUNDED_CODE,
    resident_queue_runtime_file_path,
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


@pytest.fixture(autouse=True)
def clean_signer_supply_env(monkeypatch) -> None:
    for name in (
        "REDDOG_SIGNER_SERVICE_CONFIG_PATH",
        "REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY",
        "REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY_ENFORCED",
        "REDDOG_SIGNER_SERVICE_RUN_PACKET_PATH",
        "REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY",
        "REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY_ENFORCED",
        "REDDOG_SIGNER_SERVICE_HEALTHCHECK",
        "REDDOG_SIGNER_SERVICE_HEALTHCHECK_ENFORCED",
        "REDDOG_SIGNER_HEALTHCHECK_REQUESTER_PRINCIPAL_ID",
        "REDDOG_SIGNER_HEALTHCHECK_PROFILE_ID",
        "REDDOG_SIGNER_HEALTHCHECK_TIMEOUT_S",
        "REDDOG_SIGNER_HEALTHCHECK_MAX_RESPONSE_BYTES",
        "REDDOG_SIGNER_PRINCIPAL_SIGNING_KEY_REF",
        "REDDOG_SIGNER_PRINCIPAL_AUDIT_MAC_KEY_REF",
        "REDDOG_SIGNER_REDDOG_SIGNING_KEY_REF",
        "REDDOG_SIGNER_REDDOG_AUDIT_MAC_KEY_REF",
        "REDDOG_SIGNER_PEER_UID_TO_PRINCIPAL",
        "REDDOG_SIGNER_ALLOWED_GIDS",
        "REDDOG_SIGNER_SERVICE_OP_EXECUTABLE",
        "REDDOG_SIGNER_SERVICE_OP_TIMEOUT_S",
        "REDDOG_SIGNER_SERVICE_TTL_SECONDS",
        "REDDOG_SIGNER_SERVICE_SESSION_ID",
        "REDDOG_SIGNER_SERVICE_PYTHON_EXECUTABLE",
    ):
        monkeypatch.delenv(name, raising=False)


def _authority_profile(**overrides: object) -> dict[str, object]:
    profile: dict[str, object] = {
        "principal_id": "github:mjtrout",
        "principal_public_key": "ed25519-pub-v1:principal",
        "reddog_id": "reddog:foundups-agent",
        "reddog_public_key": "ed25519-pub-v1:reddog",
        "permission_snapshot_digest": "sha256:permission",
        "key_epoch": "epoch-1",
        "identity_ttl_seconds": 600,
        "work_authority_ttl_seconds": 300,
    }
    profile.update(overrides)
    return profile


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _signer_config(socket_path: Path) -> dict[str, object]:
    return {
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


def _serial_loop_result() -> SimpleNamespace:
    return SimpleNamespace(
        accepted=True,
        status="SERIAL_LOOP_TEST_ACCEPT",
        queue_item_id=None,
        selected_slice=None,
        steps_run=0,
        dispatched_stages=(),
        next_action="STOP_TEST",
        rejection_reasons=(),
        chain_results_path=None,
        store_revision=None,
    )


def test_main_signer_config_supply_writes_outside_repo_config_without_socket_consumption(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    profile_env = {
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": PROFILE_SIGNED_0102_BOUNDED_CODE,
        "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
    }
    authority_profile_path = Path(
        resident_queue_runtime_file_path(
            profile_env,
            repo,
            "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH",
        )
    )
    config_path = Path(
        resident_queue_runtime_file_path(profile_env, repo, "REDDOG_SIGNER_SERVICE_CONFIG_PATH")
    )
    socket_path = Path(
        resident_queue_runtime_file_path(profile_env, repo, "REDDOG_SIGNER_SOCKET_PATH")
    )
    _write_json(authority_profile_path, _authority_profile())

    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_ENFORCED", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", PROFILE_SIGNED_0102_BOUNDED_CODE)
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(authority_profile_path))
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY", "1")
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY_ENFORCED", "1")
    monkeypatch.setenv("REDDOG_SIGNER_PRINCIPAL_SIGNING_KEY_REF", "op://prod-vault/principal/private")
    monkeypatch.setenv("REDDOG_SIGNER_PRINCIPAL_AUDIT_MAC_KEY_REF", "op://prod-vault/principal/audit")
    monkeypatch.setenv("REDDOG_SIGNER_REDDOG_SIGNING_KEY_REF", "op://prod-vault/reddog/private")
    monkeypatch.setenv("REDDOG_SIGNER_REDDOG_AUDIT_MAC_KEY_REF", "op://prod-vault/reddog/audit")
    monkeypatch.setenv(
        "REDDOG_SIGNER_PEER_UID_TO_PRINCIPAL",
        json.dumps({"1001": "github:mjtrout"}, sort_keys=True),
    )

    with patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_main_resident_queue_serial_loop_bootstrap."
        "run_reddog_main_resident_queue_serial_loop_bootstrap",
        return_value=_serial_loop_result(),
    ) as mocked_bootstrap:
        assert main.run_reddog_resident_queue_serial_loop_preflight(repo) is True

    captured = capsys.readouterr().out
    assert "[REDDOG-SIGNER-CONFIG] preflight=PASS" in captured
    assert config_path.exists()
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["socket_path"] == str(socket_path.resolve())
    assert payload["key_provider_profiles"][0]["signing_key_ref"] == (
        "op://prod-vault/principal/private"
    )
    assert payload["key_provider_profiles"][1]["signing_key_ref"] == (
        "op://prod-vault/reddog/private"
    )
    assert payload["peer_policy"]["uid_to_principal"] == {"1001": "github:mjtrout"}
    assert mocked_bootstrap.call_args.kwargs["signer_socket_path"] is None


def test_main_signer_config_supply_enforced_failure_blocks_before_serial_bootstrap(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    profile_env = {
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": PROFILE_SIGNED_0102_BOUNDED_CODE,
        "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
    }
    authority_profile_path = Path(
        resident_queue_runtime_file_path(
            profile_env,
            repo,
            "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH",
        )
    )
    _write_json(authority_profile_path, _authority_profile())

    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_ENFORCED", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", PROFILE_SIGNED_0102_BOUNDED_CODE)
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(authority_profile_path))
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY", "1")
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY_ENFORCED", "1")
    monkeypatch.setenv(
        "REDDOG_SIGNER_PEER_UID_TO_PRINCIPAL",
        json.dumps({"1001": "github:mjtrout"}, sort_keys=True),
    )

    with patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_main_resident_queue_serial_loop_bootstrap."
        "run_reddog_main_resident_queue_serial_loop_bootstrap",
        side_effect=AssertionError("serial bootstrap must not run after signer config reject"),
    ):
        assert main.run_reddog_resident_queue_serial_loop_preflight(repo) is False

    captured = capsys.readouterr().out
    assert "[REDDOG-SIGNER-CONFIG] preflight=WARN" in captured
    assert "signer_config_op_ref_invalid" in captured
    assert "Startup blocked by REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY_ENFORCED=1" in captured


def test_profile_does_not_auto_enable_signer_config_supply(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_ENFORCED", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", PROFILE_SIGNED_0102_BOUNDED_CODE)
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))

    with patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_main_resident_queue_serial_loop_bootstrap."
        "run_reddog_main_resident_queue_serial_loop_bootstrap",
        return_value=_serial_loop_result(),
    ):
        assert main.run_reddog_resident_queue_serial_loop_preflight(repo) is True

    captured = capsys.readouterr().out
    assert "[REDDOG-SIGNER-CONFIG]" not in captured
    assert not (runtime_root / "signer_service_config.json").exists()


def test_main_signer_run_packet_supply_writes_packet_without_socket_consumption(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    profile_env = {
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": PROFILE_SIGNED_0102_BOUNDED_CODE,
        "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
    }
    config_path = Path(
        resident_queue_runtime_file_path(profile_env, repo, "REDDOG_SIGNER_SERVICE_CONFIG_PATH")
    )
    run_packet_path = Path(
        resident_queue_runtime_file_path(
            profile_env,
            repo,
            "REDDOG_SIGNER_SERVICE_RUN_PACKET_PATH",
        )
    )
    socket_path = Path(
        resident_queue_runtime_file_path(profile_env, repo, "REDDOG_SIGNER_SOCKET_PATH")
    )
    _write_json(config_path, _signer_config(socket_path))

    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_ENFORCED", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", PROFILE_SIGNED_0102_BOUNDED_CODE)
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY", "1")
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY_ENFORCED", "1")
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_PYTHON_EXECUTABLE", "python")
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_SESSION_ID", "signer-main-run-packet")

    with patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_main_resident_queue_serial_loop_bootstrap."
        "run_reddog_main_resident_queue_serial_loop_bootstrap",
        return_value=_serial_loop_result(),
    ) as mocked_bootstrap:
        assert main.run_reddog_resident_queue_serial_loop_preflight(repo) is True

    captured = capsys.readouterr().out
    assert "[REDDOG-SIGNER-RUN-PACKET] preflight=PASS" in captured
    assert run_packet_path.exists()
    packet = json.loads(run_packet_path.read_text(encoding="utf-8"))
    assert packet["config_path"] == str(config_path.resolve())
    assert packet["socket_path"] == str(socket_path.resolve())
    assert packet["shell_command"] is None
    assert packet["argv"][:3] == [
        "python",
        "-m",
        "modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_cli",
    ]
    assert mocked_bootstrap.call_args.kwargs["signer_socket_path"] is None


def test_main_signer_config_supply_can_feed_run_packet_supply_in_same_preflight(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    profile_env = {
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": PROFILE_SIGNED_0102_BOUNDED_CODE,
        "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
    }
    authority_profile_path = Path(
        resident_queue_runtime_file_path(
            profile_env,
            repo,
            "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH",
        )
    )
    config_path = Path(
        resident_queue_runtime_file_path(profile_env, repo, "REDDOG_SIGNER_SERVICE_CONFIG_PATH")
    )
    run_packet_path = Path(
        resident_queue_runtime_file_path(
            profile_env,
            repo,
            "REDDOG_SIGNER_SERVICE_RUN_PACKET_PATH",
        )
    )
    _write_json(authority_profile_path, _authority_profile())

    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_ENFORCED", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", PROFILE_SIGNED_0102_BOUNDED_CODE)
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(authority_profile_path))
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY", "1")
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY_ENFORCED", "1")
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY", "1")
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY_ENFORCED", "1")
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_PYTHON_EXECUTABLE", "python")
    monkeypatch.setenv("REDDOG_SIGNER_PRINCIPAL_SIGNING_KEY_REF", "op://prod-vault/principal/private")
    monkeypatch.setenv("REDDOG_SIGNER_PRINCIPAL_AUDIT_MAC_KEY_REF", "op://prod-vault/principal/audit")
    monkeypatch.setenv("REDDOG_SIGNER_REDDOG_SIGNING_KEY_REF", "op://prod-vault/reddog/private")
    monkeypatch.setenv("REDDOG_SIGNER_REDDOG_AUDIT_MAC_KEY_REF", "op://prod-vault/reddog/audit")
    monkeypatch.setenv(
        "REDDOG_SIGNER_PEER_UID_TO_PRINCIPAL",
        json.dumps({"1001": "github:mjtrout"}, sort_keys=True),
    )

    with patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_main_resident_queue_serial_loop_bootstrap."
        "run_reddog_main_resident_queue_serial_loop_bootstrap",
        return_value=_serial_loop_result(),
    ):
        assert main.run_reddog_resident_queue_serial_loop_preflight(repo) is True

    captured = capsys.readouterr().out
    assert "[REDDOG-SIGNER-CONFIG] preflight=PASS" in captured
    assert "[REDDOG-SIGNER-RUN-PACKET] preflight=PASS" in captured
    assert config_path.exists()
    assert run_packet_path.exists()


def test_main_signer_run_packet_supply_enforced_failure_blocks_before_serial_bootstrap(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_ENFORCED", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", PROFILE_SIGNED_0102_BOUNDED_CODE)
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY", "1")
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY_ENFORCED", "1")

    with patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_main_resident_queue_serial_loop_bootstrap."
        "run_reddog_main_resident_queue_serial_loop_bootstrap",
        side_effect=AssertionError("serial bootstrap must not run after run-packet reject"),
    ):
        assert main.run_reddog_resident_queue_serial_loop_preflight(repo) is False

    captured = capsys.readouterr().out
    assert "[REDDOG-SIGNER-RUN-PACKET] preflight=WARN" in captured
    assert "signer_run_packet_config_path_invalid" in captured
    assert "Startup blocked by REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY_ENFORCED=1" in captured


def test_main_signer_healthcheck_enforced_failure_blocks_before_serial_bootstrap(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_ENFORCED", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", PROFILE_SIGNED_0102_BOUNDED_CODE)
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_HEALTHCHECK", "1")
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_HEALTHCHECK_ENFORCED", "1")

    with patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_main_resident_queue_serial_loop_bootstrap."
        "run_reddog_main_resident_queue_serial_loop_bootstrap",
        side_effect=AssertionError("serial bootstrap must not run after healthcheck reject"),
    ):
        assert main.run_reddog_resident_queue_serial_loop_preflight(repo) is False

    captured = capsys.readouterr().out
    assert "[REDDOG-SIGNER-HEALTHCHECK] preflight=WARN" in captured
    assert "signer_healthcheck_run_packet_path_invalid" in captured
    assert "Startup blocked by REDDOG_SIGNER_SERVICE_HEALTHCHECK_ENFORCED=1" in captured


def test_main_signer_healthcheck_passes_without_implicit_socket_consumption(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main
    from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_healthcheck import (
        SIGNER_SERVICE_HEALTHCHECK_READY,
        SignerServiceHealthcheckResult,
    )

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    run_packet_path = runtime_root / "signer_service_run_packet.json"
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_ENFORCED", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", PROFILE_SIGNED_0102_BOUNDED_CODE)
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_HEALTHCHECK", "1")
    monkeypatch.setenv("REDDOG_SIGNER_SERVICE_HEALTHCHECK_ENFORCED", "1")
    monkeypatch.setenv("REDDOG_SIGNER_HEALTHCHECK_REQUESTER_PRINCIPAL_ID", "github:mjtrout")
    monkeypatch.setenv("REDDOG_SIGNER_HEALTHCHECK_PROFILE_ID", "reddog-work-authority")

    accepted = SignerServiceHealthcheckResult(
        accepted=True,
        status=SIGNER_SERVICE_HEALTHCHECK_READY,
        run_packet_path=str(run_packet_path),
        run_packet_id="sha256:packet",
        config_path=str(runtime_root / "signer_service_config.json"),
        config_digest="sha256:config",
        socket_path=str(runtime_root / "reddog_signer.sock"),
        signer_profile_id="reddog-work-authority",
        signer_public_key="ed25519-pub-v1:reddog",
        requester_principal_id="github:mjtrout",
        request_digest="sha256:request",
        response_digest="sha256:response",
        rejection_reasons=(),
    )

    with patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_signer_socket_service_healthcheck."
        "run_reddog_signer_socket_service_healthcheck",
        return_value=accepted,
    ) as mocked_healthcheck, patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_main_resident_queue_serial_loop_bootstrap."
        "run_reddog_main_resident_queue_serial_loop_bootstrap",
        return_value=_serial_loop_result(),
    ) as mocked_bootstrap:
        assert main.run_reddog_resident_queue_serial_loop_preflight(repo) is True

    captured = capsys.readouterr().out
    assert "[REDDOG-SIGNER-HEALTHCHECK] preflight=PASS" in captured
    assert "response=sha256:response" in captured
    assert mocked_healthcheck.call_args.kwargs["run_packet_path"] == str(run_packet_path)
    assert mocked_healthcheck.call_args.kwargs["requester_principal_id"] == "github:mjtrout"
    assert mocked_healthcheck.call_args.kwargs["signer_profile_id"] == "reddog-work-authority"
    assert mocked_bootstrap.call_args.kwargs["signer_socket_path"] is None
