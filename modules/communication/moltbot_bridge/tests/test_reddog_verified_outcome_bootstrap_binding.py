"""Focused bootstrap binding regression for verified-outcome authority."""

from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_bootstrap import (
    _load_bound_runtime_config,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_socket_service_runtime_bootstrap import (
    _config,
    _launch_binding,
    _private_key,
    _public_text,
    _repo,
    _write_json,
)


def test_bootstrap_attaches_authenticated_owner_config_id(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    private_key = _private_key()
    config_path = _write_json(
        runtime / "signer-service.json",
        _config(_public_text(private_key), socket_path=runtime / "signer.sock"),
    )
    launch = _launch_binding(repo, config_path)

    config, _path, _digest, rejected = _load_bound_runtime_config(
        repo,
        config_path,
        launch["expected_config_digest"],
        launch["run_packet_path"],
        launch["expected_session_id"],
        launch["expected_owner_authority_config_path"],
        launch["manifest_selection"],
        launch["manifest_selection_boundary"],
    )

    assert rejected is None
    assert config is not None
    assert config.system_service_owner_config_id == "sha256:" + ("c" * 64)
