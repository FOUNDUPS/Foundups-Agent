"""Resident binding and effect-integrity tests for upstream providers."""
import json
from pathlib import Path
from modules.communication.moltbot_bridge.src.reddog_artifact_generation_provider_bootstrap import (
    ArtifactProviderDependencies, OPENCLAW_ARTIFACT_AGENT_ID,
)
from modules.communication.moltbot_bridge.src.reddog_artifact_generation_provider_contract import ArtifactGenerationModelResult
from modules.communication.moltbot_bridge.src.reddog_artifact_generation_result import (
    _receipt_id,
    build_generation_result,
    rehydrate_bounded_artifact_generation_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap import (
    _artifact_provider_effects as bootstrap_effects, _build_artifact_generator,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_gateway_artifact_provider import OpenClawGatewayArtifactGenerationRunner
from modules.communication.moltbot_bridge.src.reddog_hermes_api_artifact_provider import HermesApiArtifactGenerationRunner
from modules.communication.moltbot_bridge.src.reddog_resident_queue_bounded_worker_pilot_handler import _artifact_provider_effects as pilot_effects


class FakeOpenClawRunner:
    pass


def _roots(tmp_path):
    repo, runtime = tmp_path / "repo", tmp_path / "runtime"
    repo.mkdir(); runtime.mkdir()
    return repo, runtime


def _generation():
    model = ArtifactGenerationModelResult(
        True, "MODEL_OK", {"x.py": "ok"}, "run-1", "sha256:model", True,
        provider_runtime="openclaw_gateway", provider_invocation_performed=True,
        worker_process_started=True, worker_process_spawn_count=5,
        file_write_performed=True, external_side_effects_possible=True,
    )
    return build_generation_result(
        {"work_order_id": "wo-1", "slice_name": "slice-1"}, planned=["x.py"],
        model_selection={"receipt_id": "selection-1"}, model_result=model,
        artifacts={"x.py": "ok"}, reasons=[],
    ).to_dict()


def test_bootstrap_uses_fixed_openclaw_identity_and_ignores_environment(tmp_path, monkeypatch):
    repo, runtime = _roots(tmp_path)
    runner = FakeOpenClawRunner()
    monkeypatch.setenv("REDDOG_OPENCLAW_ARTIFACT_AGENT_ID", "attacker")
    built, reasons = _build_artifact_generator(
        injected_runner=None, mode="openclaw_gateway", repo_root=repo,
        runtime_root=runtime,
        dependencies=ArtifactProviderDependencies(openclaw_command_runner=runner),
    )
    assert reasons == () and isinstance(built, OpenClawGatewayArtifactGenerationRunner)
    assert built.agent_id == OPENCLAW_ARTIFACT_AGENT_ID
    assert built.command_runner is runner


def test_production_hermes_mode_builds_real_upstream_api_adapter(tmp_path):
    repo, runtime = _roots(tmp_path)
    transport, key_provider = object(), object()
    built, reasons = _build_artifact_generator(
        injected_runner=None, mode="hermes_api", repo_root=repo, runtime_root=runtime,
        dependencies=ArtifactProviderDependencies(
            hermes_api_transport=transport,
            hermes_api_key_provider=key_provider,
        ),
    )
    assert reasons == () and isinstance(built, HermesApiArtifactGenerationRunner)
    assert built.transport is transport and built.api_key_provider is key_provider


def test_unknown_provider_mode_rejects(tmp_path):
    repo, runtime = _roots(tmp_path)
    built, reasons = _build_artifact_generator(
        injected_runner=None, mode="named_wrapper_only", repo_root=repo, runtime_root=runtime,
    )
    assert built is None and reasons == ("unsupported_artifact_generator_mode",)


def test_effect_truth_requires_valid_digest_bound_generation_receipt(tmp_path):
    generation = _generation()
    assert pilot_effects(generation)["worker_process_spawn_count"] == 5
    chain = tmp_path / "chain.json"
    chain.write_text(json.dumps({"stage_results": {"bounded_worker_pilot": {
        "artifact_generation_result": generation}}}), encoding="utf-8")
    accepted = bootstrap_effects(chain)
    assert accepted == {
        "runtime": "openclaw_gateway", "invoked": True,
        "worker_process_started": True, "worker_process_spawn_count": 5,
        "hermes": False, "file_write_performed": True,
        "external_side_effects_possible": True,
        "effect_observation_complete": True, "run_abort_confirmed": True,
    }
    generation["receipt"]["worker_process_spawn_count"] = 0
    chain.write_text(json.dumps({"stage_results": {"bounded_worker_pilot": {
        "artifact_generation_result": generation}}}), encoding="utf-8")
    rejected = bootstrap_effects(chain)
    assert rejected["runtime"] == "none"
    assert rejected["effect_observation_complete"] is False
    assert rejected["run_abort_confirmed"] is False


def test_recomputed_receipt_cannot_forge_effect_semantics():
    receipt = dict(_generation()["receipt"])
    receipt["worker_process_started"] = False
    payload = dict(receipt)
    payload.pop("receipt_id")
    receipt["receipt_id"] = _receipt_id(payload)

    assert rehydrate_bounded_artifact_generation_receipt(receipt) is None


def test_recomputed_receipt_cannot_claim_abort_with_incomplete_observation():
    receipt = dict(_generation()["receipt"])
    receipt["effect_observation_complete"] = False
    receipt["run_abort_confirmed"] = True
    payload = dict(receipt)
    payload.pop("receipt_id")
    receipt["receipt_id"] = _receipt_id(payload)

    assert rehydrate_bounded_artifact_generation_receipt(receipt) is None
