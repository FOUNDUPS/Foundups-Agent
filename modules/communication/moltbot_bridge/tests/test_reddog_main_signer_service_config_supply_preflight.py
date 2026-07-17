"""Tests for REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY_PHASE1 main preflight."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
    PROFILE_SIGNED_0102_BOUNDED_CODE,
    resident_queue_runtime_file_path,
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


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
