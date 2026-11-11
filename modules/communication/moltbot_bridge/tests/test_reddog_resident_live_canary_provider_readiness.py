"""Provider-specific canary prerequisites; no service/model/provider calls."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from modules.communication.moltbot_bridge.src import reddog_resident_live_canary as canary
from modules.communication.moltbot_bridge.src.reddog_resident_live_canary_environment import (
    build_live_canary_environment,
)
from modules.communication.moltbot_bridge.src.reddog_resident_live_canary_provider_readiness import (
    live_canary_provider_requirements,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_live_canary_test_support import (
    _kwargs, _roots,
)


def _hermes_key(runtime: Path) -> str:
    value = "synthetic-fixture-never-serialize-1234567890"
    path = runtime / "hermes-api" / "api-key"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return value


@pytest.mark.parametrize("mode", ["hermes_api", "openclaw_gateway"])
def test_environment_keeps_explicit_supported_provider_mode(tmp_path: Path, mode: str) -> None:
    env = build_live_canary_environment(
        runtime_root=tmp_path, environ={"REDDOG_ARTIFACT_GENERATOR_MODE": mode},
        queue_item_id="queue-test", max_rounds=1,
    )
    assert env["REDDOG_ARTIFACT_GENERATOR_MODE"] == mode


def test_hermes_readiness_uses_its_runtime_credential_not_openrouter(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    secret = _hermes_key(runtime)
    args = _kwargs(repo, runtime)
    args["environ"].pop("OPENROUTER_API_KEY")
    args["environ"].update({
        "REDDOG_ARTIFACT_GENERATOR_MODE": "hermes_api",
        "REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS": "lmstudio",
    })
    runner = Mock(side_effect=AssertionError("readiness must not invoke control loop"))
    receipt = canary.run_reddog_resident_live_canary(**args, control_loop_runner=runner)
    assert "openrouter_api_key_missing" not in receipt.blockers
    checks = {item.name: item for item in receipt.readiness_checks}
    assert checks["hermes_api_key_reference"].passed
    assert not receipt.execution_invoked
    assert not receipt.live_proof_complete
    assert "canonical_signed_runtime_artifact_manifest_selection_verifier_missing" in receipt.blockers
    assert secret not in json.dumps(receipt.to_dict())
    runner.assert_not_called()


def _requirements(tmp_path: Path, environ: dict[str, str], *, executable=True):
    repo, runtime = tmp_path / "repo", tmp_path / "runtime"
    repo.mkdir(exist_ok=True)
    runtime.mkdir(exist_ok=True)
    checks = live_canary_provider_requirements(
        repo_root=repo, runtime_root=runtime, environ=environ,
        command_resolver=lambda name: f"/usr/bin/{name}" if executable else None,
    )
    return {name: (passed, reason) for name, passed, reason in checks}


@pytest.mark.parametrize("mode", ["not-supported", "local", "", " "])
def test_unsupported_or_empty_explicit_mode_never_falls_back(tmp_path: Path, mode: str) -> None:
    env = {"REDDOG_ARTIFACT_GENERATOR_MODE": mode}
    assert _requirements(tmp_path, env) == {
        "artifact_generator_mode": (False, "unsupported_artifact_generator_mode")
    }
    with pytest.raises(ValueError, match="^unsupported_artifact_generator_mode$"):
        build_live_canary_environment(runtime_root=tmp_path, environ=env, queue_item_id="q", max_rounds=1)


@pytest.mark.parametrize("mode", [None, "foundups_fusion", "fusion"])
def test_default_and_alias_fusion_retain_key_and_route_requirements(tmp_path: Path, mode) -> None:
    env = {"REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS": "openrouter"}
    if mode is not None:
        env["REDDOG_ARTIFACT_GENERATOR_MODE"] = mode
    overlay = build_live_canary_environment(runtime_root=tmp_path, environ=env, queue_item_id="q", max_rounds=1)
    assert overlay["REDDOG_ARTIFACT_GENERATOR_MODE"] == "foundups_fusion"
    assert _requirements(tmp_path, env)["openrouter_key_reference"][0] is False
    env["OPENROUTER_API_KEY"] = "non-secret-fixture"
    assert all(passed for passed, _ in _requirements(tmp_path, env).values())
    env["REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS"] = "lmstudio"
    assert _requirements(tmp_path, env)["fusion_model_provider"][0] is False


@pytest.mark.parametrize("mode", ["foundups_fusion", "hermes_api", "openclaw_gateway"])
@pytest.mark.parametrize("identity", ["", " , , "])
def test_missing_required_model_provider_identity_blocks(tmp_path: Path, mode: str, identity: str) -> None:
    env = {"REDDOG_ARTIFACT_GENERATOR_MODE": mode, "REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS": identity}
    assert _requirements(tmp_path, env)["model_provider_identity"] == (False, "model_provider_identity_missing")


@pytest.mark.parametrize("key", [None, "too-short", "k" * 257, "k" * 40 + " white-space"])
def test_hermes_key_validation_reuses_runtime_owner_and_not_env_alias(tmp_path: Path, key) -> None:
    runtime = tmp_path / "runtime"
    _hermes_key(runtime)
    path = runtime / "hermes-api" / "api-key"
    if key is None:
        path.unlink()
    else:
        path.write_text(key, encoding="utf-8")
    env = {"REDDOG_ARTIFACT_GENERATOR_MODE": "hermes_api", "REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS": "lmstudio", "HERMES_API_KEY": "k" * 48, "OPENROUTER_API_KEY": "k" * 48}
    checks = _requirements(tmp_path, env)
    assert checks["hermes_api_key_reference"] == (False, "hermes_api_key_missing_or_invalid")
    assert "openrouter_key_reference" not in checks


def test_openclaw_requires_executable_but_not_fabricated_service_credentials(tmp_path: Path) -> None:
    env = {"REDDOG_ARTIFACT_GENERATOR_MODE": "openclaw_gateway", "REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS": "lmstudio"}
    assert all(passed for passed, _ in _requirements(tmp_path, env).values())
    assert _requirements(tmp_path, env, executable=False)["openclaw_available"] == (False, "openclaw_not_available")


@pytest.mark.parametrize("mode", ["hermes_api", "openclaw_gateway", "not-supported"])
def test_provider_selection_cannot_bypass_authority_or_invoke_worker(tmp_path: Path, mode: str, monkeypatch) -> None:
    repo, runtime = _roots(tmp_path)
    _hermes_key(runtime)
    args = _kwargs(repo, runtime)
    args["environ"]["REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS"] = "lmstudio"
    args["environ"]["REDDOG_ARTIFACT_GENERATOR_MODE"] = "foundups_fusion"
    runner = Mock(side_effect=AssertionError("authority gate must block runner"))
    # No provider transport, subprocess, signed capability issuance or model call is permitted.
    monkeypatch.setattr("http.client.HTTPConnection", Mock(side_effect=AssertionError("no HTTP")))
    monkeypatch.setattr("subprocess.run", Mock(side_effect=AssertionError("no subprocess")))
    before = {str(p.relative_to(runtime)): p.read_bytes() for p in runtime.rglob("*") if p.is_file()}
    environment_before = dict(os.environ)
    receipt = canary.run_reddog_resident_live_canary(
        **args, artifact_generator_mode=mode, execute=True,
        confirmation=canary.LIVE_CANARY_CONFIRMATION, control_loop_runner=runner,
    )
    assert not receipt.execution_invoked and not receipt.live_proof_complete
    assert "canonical_signed_runtime_artifact_manifest_selection_verifier_missing" in receipt.blockers
    assert receipt.artifact_generator_mode == (mode if mode != "not-supported" else None)
    for relative, contents in before.items():
        assert (runtime / relative).read_bytes() == contents
    after = {str(p.relative_to(runtime)) for p in runtime.rglob("*") if p.is_file()}
    # Existing readiness bookkeeping persists its receipt and operation lock;
    # it must not create work, chain results, model evidence or learning state.
    assert after - set(before) <= {"live_canary_receipt.json", "authority_runtime_state.json.operation.lock"}
    assert dict(os.environ) == environment_before
    assert args["environ"]["REDDOG_ARTIFACT_GENERATOR_MODE"] == "foundups_fusion"
    runner.assert_not_called()


def test_cli_selection_is_supported_explicit_and_default_preserves_environment() -> None:
    parser = canary.build_reddog_resident_live_canary_parser()
    base = ["--repo-root", "repo", "--runtime-root", "runtime"]
    assert parser.parse_args(base).artifact_generator_mode is None
    assert parser.parse_args(base + ["--artifact-generator-mode", "hermes_api"]).artifact_generator_mode == "hermes_api"
    with pytest.raises(SystemExit):
        parser.parse_args(base + ["--artifact-generator-mode", "local"])


def test_execution_overlay_carries_selected_mode_and_provider_identities_without_leaking_context(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATOR_MODE", "foundups_fusion")
    monkeypatch.setenv("REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS", "openrouter")
    supplied = {"REDDOG_ARTIFACT_GENERATOR_MODE": "hermes_api", "REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS": "lmstudio"}
    context = canary._canary_context(tmp_path / "repo", tmp_path / "runtime", None, supplied, "linux")
    observed = {}
    def runner(_):
        observed.update({key: os.environ[key] for key in supplied})
        return {}
    canary._invoke_control_runner(context, runner, "queue-test", 1, True)
    assert observed == supplied
    assert os.environ["REDDOG_ARTIFACT_GENERATOR_MODE"] == "foundups_fusion"
    assert os.environ["REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS"] == "openrouter"
