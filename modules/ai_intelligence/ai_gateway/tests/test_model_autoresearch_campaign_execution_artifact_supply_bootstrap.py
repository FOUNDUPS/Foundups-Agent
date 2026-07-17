"""Tests for REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import replace
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.ai_gateway import ProviderConfig
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_configured_gateway_runner import (
    AIGatewayConfiguredModelCaller,
    ConfiguredGatewayRunnerPolicy,
    MappingPromptSource,
    build_configured_gateway_benchmark_runner,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_output_evidence_bundle import (
    InMemoryModelAutoResearchOutputEvidenceStore,
    read_model_autoresearch_output_evidence_jsonl,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution import (
    rehydrate_model_autoresearch_campaign_execution_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution_artifact_supply_bootstrap import (
    MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER,
    MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_APPLIED,
    MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_NOT_READY,
    MODEL_AUTORESEARCH_CAMPAIGN_EXACT_OUTPUT_DIGEST_VERIFIER,
    run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap,
)
from modules.ai_intelligence.ai_gateway.src.model_champion_challenger_autoresearch import (
    ModelAutoResearchPolicy,
    plan_model_champion_challenger_autoresearch,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution import (
    REPO_ROOT,
    _plan,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_champion_challenger_autoresearch import (
    _candidate,
    _feedback_record,
    _gate,
    _tasks,
)


MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "ai_intelligence"
    / "ai_gateway"
    / "src"
    / "model_autoresearch_campaign_execution_artifact_supply_bootstrap.py"
)


def _write_json(root: Path, name: str, payload: object) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _inputs(tmp_path: Path) -> dict[str, Path]:
    runtime = tmp_path / "runtime"
    return {
        "plan": _write_json(runtime, "autoresearch_plan.json", _plan().to_dict()),
        "candidates": _write_json(
            runtime,
            "candidate_pool.json",
            {
                "candidate_pool": [
                    _candidate("provider/challenger").to_dict(),
                    _candidate("provider/new").to_dict(),
                ]
            },
        ),
        "tasks": _write_json(runtime, "tasks.json", {"tasks": [task.to_dict() for task in _tasks()]}),
        "output": runtime / "campaign_execution.json",
    }


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


class FakeGateway:
    def __init__(self) -> None:
        self.providers = {
            "provider": ProviderConfig(
                name="provider",
                api_key="test-key",
                base_url="https://example.invalid",
                models={"quick": "wrong-default"},
                cost_per_token=0.001,
                rate_limit=1,
            )
        }
        self.calls: list[dict[str, str]] = []

    def _call_provider(self, provider: ProviderConfig, prompt: str, task_type: str) -> str:
        self.calls.append(
            {
                "provider": provider.name,
                "model": provider.models[task_type],
                "prompt": prompt,
                "task_type": task_type,
            }
        )
        return "configured gateway answer"


def _configured_inputs(tmp_path: Path) -> tuple[dict[str, Path], FakeGateway]:
    runtime = tmp_path / "runtime"
    prompt = "Audit the model AutoResearch gateway path."
    candidate = _candidate("provider/new")
    base_task = replace(
        _tasks()[0],
        prompt_digest=_sha256(prompt),
        expected_output_digest="sha256:placeholder",
    )
    precompute_gateway = FakeGateway()
    precompute_runner = build_configured_gateway_benchmark_runner(
        caller=AIGatewayConfiguredModelCaller(precompute_gateway),
        prompt_source=MappingPromptSource({base_task.task_id: prompt}),
        policy=ConfiguredGatewayRunnerPolicy(
            allowed_providers=("provider",),
            max_prompt_chars=2000,
            max_calls_per_sample=1,
            max_cost_estimate_usd_per_sample=1.0,
        ),
        output_evidence_store=InMemoryModelAutoResearchOutputEvidenceStore(),
    )
    expected = precompute_runner(base_task, candidate).output_digest
    task = replace(base_task, expected_output_digest=expected)
    plan = plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(_gate("provider/challenger", pass_all=False),),
        candidate_pool=(_candidate("provider/challenger"), candidate),
        policy=ModelAutoResearchPolicy(
            task_family="architecture",
            catalog_snapshot_id="model_catalog_snapshot:1",
            max_campaign_items=1,
            required_verifier_digest="sha256:verifier",
            cost_budget_receipt_id="cost_budget:1",
        ),
        feedback_records=(_feedback_record("provider/new", suffix="2"),),
    )
    return (
        {
            "plan": _write_json(runtime, "autoresearch_plan.json", plan.to_dict()),
            "candidates": _write_json(
                runtime,
                "candidate_pool.json",
                {
                    "candidate_pool": [
                        _candidate("provider/challenger").to_dict(),
                        candidate.to_dict(),
                    ]
                },
            ),
            "tasks": _write_json(runtime, "tasks.json", {"tasks": [task.to_dict()]}),
            "prompts": _write_json(
                runtime,
                "prompt_records.json",
                {"prompts": [{"task_id": task.task_id, "prompt": prompt, "prompt_digest": _sha256(prompt)}]},
            ),
            "evidence": runtime / "output_evidence.jsonl",
            "output": runtime / "campaign_execution.json",
        },
        FakeGateway(),
    )


def test_campaign_execution_bootstrap_materializes_rehydratable_receipt(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        candidate_pool_path=files["candidates"],
        tasks_path=files["tasks"],
        output_path=files["output"],
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )

    assert result.accepted is True
    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_APPLIED
    assert result.execution_receipt_id
    assert result.execution_receipt_id.startswith("model_autoresearch_campaign_execution:")
    assert result.executed_candidate_ids == ("provider/new", "provider/challenger")
    assert result.task_count == 2
    assert result.no_direct_provider_call_performed is True
    assert result.no_holoindex_reindex_performed is True
    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    receipt = rehydrate_model_autoresearch_campaign_execution_receipt(payload)
    assert receipt.receipt_id == result.execution_receipt_id


def test_campaign_execution_bootstrap_configured_gateway_mode_materializes_receipt(tmp_path: Path) -> None:
    files, gateway = _configured_inputs(tmp_path)

    result = run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        candidate_pool_path=files["candidates"],
        tasks_path=files["tasks"],
        prompt_records_path=files["prompts"],
        output_evidence_path=files["evidence"],
        output_path=files["output"],
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
        runner_mode=MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER,
        verifier_mode=MODEL_AUTORESEARCH_CAMPAIGN_EXACT_OUTPUT_DIGEST_VERIFIER,
        runner_allowed_providers="provider",
        runner_max_prompt_chars=2000,
        runner_max_calls_per_sample=1,
        runner_max_cost_estimate_usd_per_sample=1.0,
        gateway=gateway,
    )

    assert result.accepted is True
    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_APPLIED
    assert result.executed_candidate_ids == ("provider/new",)
    assert result.task_count == 1
    assert result.no_direct_provider_call_performed is False
    assert result.output_evidence_path == str(files["evidence"].resolve())
    assert len(gateway.calls) == 1
    assert gateway.calls[0]["provider"] == "provider"
    assert gateway.calls[0]["model"] == "new"
    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    receipt = rehydrate_model_autoresearch_campaign_execution_receipt(payload)
    assert receipt.receipt_id == result.execution_receipt_id
    assert receipt.benchmark_run_receipt.samples[0].accepted is True
    evidence_records = read_model_autoresearch_output_evidence_jsonl(
        files["evidence"],
        repo_root=REPO_ROOT,
    )
    assert len(evidence_records) == 1
    assert evidence_records[0].response_text == "configured gateway answer"
    assert evidence_records[0].task_id == receipt.benchmark_run_receipt.samples[0].task_id


def test_campaign_execution_bootstrap_configured_gateway_requires_prompt_records(tmp_path: Path) -> None:
    files, gateway = _configured_inputs(tmp_path)

    result = run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        candidate_pool_path=files["candidates"],
        tasks_path=files["tasks"],
        output_path=files["output"],
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
        runner_mode=MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER,
        verifier_mode=MODEL_AUTORESEARCH_CAMPAIGN_EXACT_OUTPUT_DIGEST_VERIFIER,
        runner_allowed_providers="provider",
        gateway=gateway,
    )

    assert result.accepted is False
    assert "missing_model_autoresearch_campaign_prompt_records_path" in result.rejection_reasons
    assert "missing_model_autoresearch_campaign_output_evidence_path" in result.rejection_reasons
    assert not files["output"].exists()
    assert gateway.calls == []


def test_campaign_execution_bootstrap_configured_gateway_requires_output_evidence_path(tmp_path: Path) -> None:
    files, gateway = _configured_inputs(tmp_path)

    result = run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        candidate_pool_path=files["candidates"],
        tasks_path=files["tasks"],
        prompt_records_path=files["prompts"],
        output_path=files["output"],
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
        runner_mode=MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER,
        verifier_mode=MODEL_AUTORESEARCH_CAMPAIGN_EXACT_OUTPUT_DIGEST_VERIFIER,
        runner_allowed_providers="provider",
        gateway=gateway,
    )

    assert result.accepted is False
    assert "missing_model_autoresearch_campaign_output_evidence_path" in result.rejection_reasons
    assert not files["output"].exists()
    assert not files["evidence"].exists()
    assert gateway.calls == []


def test_campaign_execution_bootstrap_configured_gateway_rejects_inside_repo_output_evidence(
    tmp_path: Path,
) -> None:
    files, gateway = _configured_inputs(tmp_path)
    inside = REPO_ROOT / "model_autoresearch_output_evidence.jsonl"

    result = run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        candidate_pool_path=files["candidates"],
        tasks_path=files["tasks"],
        prompt_records_path=files["prompts"],
        output_evidence_path=inside,
        output_path=files["output"],
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
        runner_mode=MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER,
        verifier_mode=MODEL_AUTORESEARCH_CAMPAIGN_EXACT_OUTPUT_DIGEST_VERIFIER,
        runner_allowed_providers="provider",
        gateway=gateway,
    )

    assert result.accepted is False
    assert "model_autoresearch_campaign_output_evidence_path_inside_repo" in result.rejection_reasons
    assert not files["output"].exists()
    assert not inside.exists()
    assert gateway.calls == []


def test_campaign_execution_bootstrap_rejects_inside_repo_inputs_and_output(tmp_path: Path) -> None:
    files = _inputs(tmp_path)
    repo_plan = REPO_ROOT / "model_autoresearch_plan_receipt.json"
    repo_output = REPO_ROOT / "model_autoresearch_campaign_execution.json"
    repo_plan.write_text("{}", encoding="utf-8")
    try:
        result = run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
            repo_root=REPO_ROOT,
            plan_receipt_path=repo_plan,
            candidate_pool_path=files["candidates"],
            tasks_path=files["tasks"],
            output_path=repo_output,
            verifier_digest="sha256:verifier",
            held_out_split_id="heldout-v1",
        )
    finally:
        repo_plan.unlink(missing_ok=True)
        repo_output.unlink(missing_ok=True)

    assert result.accepted is False
    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_NOT_READY
    assert "model_autoresearch_plan_receipt_path_inside_repo" in result.rejection_reasons
    assert "model_autoresearch_campaign_execution_output_path_invalid" in result.rejection_reasons


def test_campaign_execution_bootstrap_rejects_malformed_tasks_before_execution(tmp_path: Path) -> None:
    files = _inputs(tmp_path)
    bad_tasks = _write_json(tmp_path / "runtime", "bad_tasks.json", {"tasks": [{"task_id": "missing"}]})

    result = run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        candidate_pool_path=files["candidates"],
        tasks_path=bad_tasks,
        output_path=files["output"],
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )

    assert result.accepted is False
    assert "model_autoresearch_execution_tasks_invalid" in result.rejection_reasons
    assert not files["output"].exists()


def test_campaign_execution_bootstrap_rejects_verifier_mismatch(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        candidate_pool_path=files["candidates"],
        tasks_path=files["tasks"],
        output_path=files["output"],
        verifier_digest="sha256:wrong",
        held_out_split_id="heldout-v1",
    )

    assert result.accepted is False
    assert "model_autoresearch_execution_verifier_digest_mismatch" in result.rejection_reasons
    assert not files["output"].exists()


def test_campaign_execution_bootstrap_rejects_non_fixture_modes(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
        repo_root=REPO_ROOT,
        plan_receipt_path=files["plan"],
        candidate_pool_path=files["candidates"],
        tasks_path=files["tasks"],
        output_path=files["output"],
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
        runner_mode="provider",
        verifier_mode="remote",
    )

    assert result.accepted is False
    assert "unsupported_model_autoresearch_campaign_runner_mode" in result.rejection_reasons
    assert "unsupported_model_autoresearch_campaign_verifier_mode" in result.rejection_reasons
    assert not files["output"].exists()


def test_campaign_execution_bootstrap_module_has_no_direct_network_command_runtime_or_holoindex_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "openai",
        "holo_index",
        "pattern_memory",
        "git",
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls
