"""Configured-gateway bootstrap safety artifact contract."""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_gateway.src import (
    model_autoresearch_campaign_execution_artifact_supply_bootstrap as bootstrap_module,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution_artifact_supply_bootstrap import (
    MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER,
    MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_APPLIED,
    MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_NOT_READY,
    MODEL_AUTORESEARCH_CAMPAIGN_EXACT_OUTPUT_DIGEST_VERIFIER,
    run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_configured_gateway_evidence import (
    read_call_attempt_receipts_jsonl,
    read_runner_receipts_jsonl,
    rehydrate_runner_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_champion_challenger_autoresearch import (
    ModelAutoResearchPolicy,
    plan_model_champion_challenger_autoresearch,
)
from modules.ai_intelligence.ai_gateway.src.model_combination_benchmark_harness import (
    ModelBenchmarkRoleAssignment,
    build_model_benchmark_candidate,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution import (
    REPO_ROOT,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution_artifact_supply_bootstrap import (
    FakeGateway,
    _configured_inputs,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_champion_challenger_autoresearch import (
    _candidate,
    _feedback_record,
    _gate,
)


def _digest_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _budget_payload(
    *,
    assignment_model_id: str = "provider/new",
    allowed_providers: tuple[str, ...] = ("provider",),
) -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": "configured_gateway_model_budget_evidence.v1",
        "allowed_providers": list(allowed_providers),
        "model_budgets": [
            {
                "assignment_model_id": assignment_model_id,
                "provider": "provider",
                "api_model": assignment_model_id.split("/", 1)[-1],
                "input_cost_per_million": "1",
                "output_cost_per_million": "1",
                "request_overhead_input_tokens": 11,
                "max_completion_tokens": 32,
                "reasoning_control": {
                    "mode": "effort",
                    "effort": "high",
                    "supported_efforts": ["high"],
                    "catalog_evidence_digest": (
                        "sha256:"
                        + hashlib.sha256(b"provider-catalog-evidence").hexdigest()
                    ),
                },
            }
        ],
    }
    return {**body, "evidence_digest": _digest_payload(body)}


def _configured_call(files, gateway, **overrides):
    values = {
        "repo_root": REPO_ROOT,
        "plan_receipt_path": files["plan"],
        "candidate_pool_path": files["candidates"],
        "tasks_path": files["tasks"],
        "prompt_records_path": files["prompts"],
        "output_evidence_path": files["evidence"],
        "output_path": files["output"],
        "model_budget_evidence_path": files["budgets"],
        "call_attempt_evidence_path": files["attempts"],
        "runner_success_receipt_path": files["successes"],
        "verifier_digest": "sha256:verifier",
        "held_out_split_id": "heldout-v1",
        "runner_mode": MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER,
        "verifier_mode": MODEL_AUTORESEARCH_CAMPAIGN_EXACT_OUTPUT_DIGEST_VERIFIER,
        "runner_allowed_providers": "provider",
        "runner_max_prompt_chars": 2000,
        "runner_max_calls_per_sample": 1,
        "runner_max_cost_estimate_usd_per_sample": "1",
        "gateway": gateway,
    }
    if "runner_max_total_calls" in inspect.signature(
        run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap
    ).parameters:
        values["runner_max_total_calls"] = 1
    values.update(overrides)
    return run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
        **values
    )


def _safety_inputs(tmp_path: Path):
    files, gateway = _configured_inputs(tmp_path)
    runtime = tmp_path / "runtime"
    files.update(
        {
            "budgets": _write_json(
                runtime / "model_budgets.json",
                _budget_payload(),
            ),
            "attempts": runtime / "call_attempts.jsonl",
            "successes": runtime / "runner_successes.jsonl",
        }
    )
    return files, gateway


def _set_two_tasks(files) -> None:
    payload = json.loads(files["tasks"].read_text(encoding="utf-8"))
    second = {**payload["tasks"][0], "task_id": "task-002"}
    payload["tasks"].append(second)
    _write_json(files["tasks"], payload)
    prompts = json.loads(files["prompts"].read_text(encoding="utf-8"))
    prompts["prompts"].append({**prompts["prompts"][0], "task_id": "task-002"})
    _write_json(files["prompts"], prompts)


def _set_panel_candidate(files, *, include_critic_budget: bool) -> None:
    panel = build_model_benchmark_candidate(
        (
            ModelBenchmarkRoleAssignment(
                role="principal", model_id="provider/new", provider="provider"
            ),
            ModelBenchmarkRoleAssignment(
                role="critic", model_id="provider/critic", provider="provider"
            ),
        )
    )
    challenger = _candidate("provider/challenger")
    plan = plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(_gate("provider/challenger", pass_all=False),),
        candidate_pool=(challenger, panel),
        policy=ModelAutoResearchPolicy(
            task_family="architecture",
            catalog_snapshot_id="model_catalog_snapshot:1",
            max_campaign_items=1,
            required_verifier_digest="sha256:verifier",
            cost_budget_receipt_id="cost_budget:1",
        ),
        feedback_records=(_feedback_record(panel.candidate_id, suffix="3"),),
    )
    _write_json(
        files["candidates"],
        {"candidate_pool": [challenger.to_dict(), panel.to_dict()]},
    )
    _write_json(files["plan"], plan.to_dict())
    first = _budget_payload()
    budgets = list(first["model_budgets"])
    if include_critic_budget:
        budgets.extend(_budget_payload(assignment_model_id="provider/critic")["model_budgets"])
    body = {
        "schema_version": first["schema_version"],
        "allowed_providers": first["allowed_providers"],
        "model_budgets": budgets,
    }
    _write_json(files["budgets"], {**body, "evidence_digest": _digest_payload(body)})


@pytest.mark.parametrize(
    ("argument", "reason"),
    (
        (
            "model_budget_evidence_path",
            "missing_model_autoresearch_campaign_model_budget_evidence_path",
        ),
        (
            "call_attempt_evidence_path",
            "missing_model_autoresearch_campaign_call_attempt_evidence_path",
        ),
        (
            "runner_success_receipt_path",
            "missing_model_autoresearch_campaign_runner_success_receipt_path",
        ),
    ),
)
def test_configured_bootstrap_requires_each_safety_artifact(
    tmp_path: Path,
    argument: str,
    reason: str,
) -> None:
    files, gateway = _safety_inputs(tmp_path)
    result = _configured_call(files, gateway, **{argument: None})
    assert result.accepted is False
    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_NOT_READY
    assert reason in result.rejection_reasons
    assert gateway.calls == []
    assert not files["output"].exists()


def test_configured_bootstrap_requires_explicit_campaign_total_call_cap(
    tmp_path: Path,
) -> None:
    files, gateway = _safety_inputs(tmp_path)
    result = _configured_call(files, gateway, runner_max_total_calls=None)
    assert result.accepted is False
    assert "missing_model_autoresearch_campaign_runner_max_total_calls" in (
        result.rejection_reasons
    )
    assert gateway.calls == []


@pytest.mark.parametrize("value", (True, 1.5, "1.0", "01", 0))
def test_configured_bootstrap_rejects_invalid_campaign_total_call_cap(
    tmp_path: Path,
    value,
) -> None:
    files, gateway = _safety_inputs(tmp_path)
    result = _configured_call(files, gateway, runner_max_total_calls=value)
    assert result.accepted is False
    assert "invalid_model_autoresearch_campaign_runner_max_total_calls" in (
        result.rejection_reasons
    )
    assert gateway.calls == []


@pytest.mark.parametrize("value", (1.0, True, 0, "0", "1.0", "1e0", "01", None))
def test_configured_bootstrap_rejects_noncanonical_cost_before_call(
    tmp_path: Path,
    value,
) -> None:
    files, gateway = _safety_inputs(tmp_path)
    result = _configured_call(
        files,
        gateway,
        runner_max_cost_estimate_usd_per_sample=value,
    )
    assert result.accepted is False
    assert (
        "invalid_model_autoresearch_campaign_runner_max_cost_estimate_usd_per_sample"
        in result.rejection_reasons
    )
    assert gateway.calls == []


@pytest.mark.parametrize(
    ("argument", "reason"),
    (
        (
            "model_budget_evidence_path",
            "model_autoresearch_campaign_model_budget_evidence_path_inside_repo",
        ),
        (
            "call_attempt_evidence_path",
            "model_autoresearch_campaign_call_attempt_evidence_path_inside_repo",
        ),
        (
            "runner_success_receipt_path",
            "model_autoresearch_campaign_runner_success_receipt_path_inside_repo",
        ),
    ),
)
def test_configured_bootstrap_rejects_inside_repo_safety_artifacts(
    tmp_path: Path,
    argument: str,
    reason: str,
) -> None:
    files, gateway = _safety_inputs(tmp_path)
    inside = REPO_ROOT / f"forbidden-{argument}.json"
    result = _configured_call(files, gateway, **{argument: inside})
    assert result.accepted is False
    assert reason in result.rejection_reasons
    assert gateway.calls == []
    assert not files["output"].exists()
    assert not files["attempts"].exists()
    assert not files["successes"].exists()


@pytest.mark.parametrize(
    ("payload", "reason"),
    (
        (
            "{",
            "malformed_model_autoresearch_campaign_model_budget_evidence",
        ),
        (
            {**_budget_payload(), "evidence_digest": "sha256:" + "0" * 64},
            "tampered_model_autoresearch_campaign_model_budget_evidence",
        ),
        (
            _budget_payload(assignment_model_id="provider/other"),
            "model_autoresearch_campaign_assignment_not_in_model_budget",
        ),
        (
            _budget_payload(allowed_providers=("provider", "openrouter")),
            "model_autoresearch_campaign_model_budget_provider_set_mismatch",
        ),
    ),
)
def test_configured_bootstrap_rejects_invalid_budget_evidence_precall(
    tmp_path: Path,
    payload,
    reason: str,
) -> None:
    files, gateway = _safety_inputs(tmp_path)
    if isinstance(payload, str):
        files["budgets"].write_text(payload, encoding="utf-8")
    else:
        _write_json(files["budgets"], payload)
    result = _configured_call(files, gateway)
    assert result.accepted is False
    assert reason in result.rejection_reasons
    assert gateway.calls == []
    assert not files["output"].exists()
    assert not files["attempts"].exists()
    assert not files["successes"].exists()


def test_configured_bootstrap_rejects_untrusted_assignment_route_alias(
    tmp_path: Path,
) -> None:
    files, gateway = _safety_inputs(tmp_path)
    payload = _budget_payload()
    payload["model_budgets"][0]["api_model"] = "provider-side-alias"
    body = {key: value for key, value in payload.items() if key != "evidence_digest"}
    _write_json(files["budgets"], {**body, "evidence_digest": _digest_payload(body)})
    result = _configured_call(files, gateway)
    assert result.accepted is False
    assert "model_autoresearch_campaign_assignment_route_mismatch" in (
        result.rejection_reasons
    )
    assert gateway.calls == []


def test_falsey_injected_gateway_is_used_without_live_fallback(tmp_path: Path) -> None:
    class FalseyGateway(FakeGateway):
        def __bool__(self) -> bool:
            return False

    files, _gateway = _safety_inputs(tmp_path)
    gateway = FalseyGateway()
    result = _configured_call(files, gateway)
    assert result.accepted is True
    assert len(gateway.calls) == 1


def test_configured_execution_rejection_keeps_provider_call_truth_conservative(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class RejectedExecution:
        accepted = False
        status = "REJECT"
        rejection_reasons = ("forced_post_runner_rejection",)

    files, gateway = _safety_inputs(tmp_path)
    monkeypatch.setattr(
        bootstrap_module,
        "run_reddog_model_autoresearch_campaign_execution",
        lambda **kwargs: RejectedExecution(),
    )
    result = _configured_call(files, gateway)
    assert result.accepted is False
    assert result.no_direct_provider_call_performed is False


def test_two_tasks_exceed_campaign_total_cap_before_first_call(tmp_path: Path) -> None:
    files, gateway = _safety_inputs(tmp_path)
    _set_two_tasks(files)
    result = _configured_call(files, gateway, runner_max_total_calls=1)
    assert result.accepted is False
    assert "model_autoresearch_campaign_total_call_budget_exceeded" in (
        result.rejection_reasons
    )
    assert gateway.calls == []
    assert not files["attempts"].exists()
    assert not files["evidence"].exists()


def test_two_task_configured_campaign_is_phase1_no_go_even_with_exact_cap(
    tmp_path: Path,
) -> None:
    files, gateway = _safety_inputs(tmp_path)
    _set_two_tasks(files)
    result = _configured_call(files, gateway, runner_max_total_calls=2)
    assert result.accepted is False
    assert "model_autoresearch_campaign_multi_call_not_supported" in (
        result.rejection_reasons
    )
    assert gateway.calls == []


def test_multi_role_candidate_exceeds_campaign_total_cap_precall(tmp_path: Path) -> None:
    files, gateway = _safety_inputs(tmp_path)
    _set_panel_candidate(files, include_critic_budget=True)
    result = _configured_call(
        files,
        gateway,
        runner_max_calls_per_sample=2,
        runner_max_total_calls=1,
    )
    assert result.accepted is False
    assert "model_autoresearch_campaign_total_call_budget_exceeded" in (
        result.rejection_reasons
    )
    assert gateway.calls == []
    assert not files["attempts"].exists()


def test_panel_configured_campaign_is_phase1_no_go_even_with_exact_cap(
    tmp_path: Path,
) -> None:
    files, gateway = _safety_inputs(tmp_path)
    _set_panel_candidate(files, include_critic_budget=True)
    result = _configured_call(
        files,
        gateway,
        runner_max_calls_per_sample=2,
        runner_max_total_calls=2,
    )
    assert result.accepted is False
    assert "model_autoresearch_campaign_multi_call_not_supported" in (
        result.rejection_reasons
    )
    assert gateway.calls == []


def test_all_selected_panel_assignments_require_exact_budget(tmp_path: Path) -> None:
    files, gateway = _safety_inputs(tmp_path)
    _set_panel_candidate(files, include_critic_budget=False)
    result = _configured_call(
        files,
        gateway,
        runner_max_calls_per_sample=2,
        runner_max_total_calls=2,
    )
    assert result.accepted is False
    assert "model_autoresearch_campaign_assignment_not_in_model_budget" in (
        result.rejection_reasons
    )
    assert gateway.calls == []


@pytest.mark.parametrize(
    ("left", "right"),
    (
        ("output_evidence_path", "call_attempt_evidence_path"),
        ("output_evidence_path", "runner_success_receipt_path"),
        ("output_evidence_path", "output_path"),
        ("output_evidence_path", "model_budget_evidence_path"),
        ("call_attempt_evidence_path", "runner_success_receipt_path"),
        ("call_attempt_evidence_path", "output_path"),
        ("call_attempt_evidence_path", "model_budget_evidence_path"),
        ("runner_success_receipt_path", "output_path"),
        ("runner_success_receipt_path", "model_budget_evidence_path"),
        ("output_path", "model_budget_evidence_path"),
    ),
)
def test_configured_bootstrap_rejects_artifact_path_aliases(
    tmp_path: Path,
    left: str,
    right: str,
) -> None:
    files, gateway = _safety_inputs(tmp_path)
    shared = files["budgets"]
    result = _configured_call(files, gateway, **{left: shared, right: shared})
    assert result.accepted is False
    assert "model_autoresearch_campaign_artifact_path_alias" in result.rejection_reasons
    assert gateway.calls == []


@pytest.mark.parametrize(
    ("write_argument", "read_argument", "read_key"),
    tuple(
        (write_argument, read_argument, read_key)
        for write_argument in (
            "output_evidence_path",
            "call_attempt_evidence_path",
            "runner_success_receipt_path",
            "output_path",
        )
        for read_argument, read_key in (
            ("prompt_records_path", "prompts"),
            ("plan_receipt_path", "plan"),
            ("candidate_pool_path", "candidates"),
            ("tasks_path", "tasks"),
        )
    ),
)
def test_configured_bootstrap_rejects_every_write_to_read_input_alias(
    tmp_path: Path,
    write_argument: str,
    read_argument: str,
    read_key: str,
) -> None:
    files, gateway = _safety_inputs(tmp_path)
    shared = files[read_key]
    result = _configured_call(
        files,
        gateway,
        **{write_argument: shared, read_argument: shared},
    )
    assert result.accepted is False
    assert "model_autoresearch_campaign_artifact_path_alias" in result.rejection_reasons
    assert gateway.calls == []


@pytest.mark.parametrize(
    ("argument", "reason"),
    (
        (
            "output_evidence_path",
            "model_autoresearch_campaign_output_evidence_path_not_empty",
        ),
        (
            "call_attempt_evidence_path",
            "model_autoresearch_campaign_call_attempt_evidence_path_not_empty",
        ),
        (
            "runner_success_receipt_path",
            "model_autoresearch_campaign_runner_success_receipt_path_not_empty",
        ),
        (
            "output_path",
            "model_autoresearch_campaign_campaign_output_path_not_empty",
        ),
    ),
)
def test_configured_bootstrap_rejects_nonempty_append_targets(
    tmp_path: Path,
    argument: str,
    reason: str,
) -> None:
    files, gateway = _safety_inputs(tmp_path)
    path_by_argument = {
        "output_evidence_path": files["evidence"],
        "call_attempt_evidence_path": files["attempts"],
        "runner_success_receipt_path": files["successes"],
        "output_path": files["output"],
    }
    path_by_argument[argument].write_text("stale\n", encoding="utf-8")
    result = _configured_call(files, gateway)
    assert result.accepted is False
    assert reason in result.rejection_reasons
    assert gateway.calls == []


def test_configured_bootstrap_writes_attempt_success_and_campaign_receipts(
    tmp_path: Path,
) -> None:
    files, gateway = _safety_inputs(tmp_path)
    result = _configured_call(files, gateway)
    assert result.accepted is True
    assert result.status == MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_APPLIED
    assert len(gateway.calls) == 1
    assert files["output"].is_file()
    attempt_records = [
        json.loads(line)
        for line in files["attempts"].read_text(encoding="utf-8").splitlines()
    ]
    success_records = [
        json.loads(line)
        for line in files["successes"].read_text(encoding="utf-8").splitlines()
    ]
    assert [record["status"] for record in attempt_records] == [
        "ATTEMPTED",
        "COMPLETED",
    ]
    assert len(success_records) == 1
    assert [item.status for item in read_call_attempt_receipts_jsonl(files["attempts"])] == [
        "ATTEMPTED",
        "COMPLETED",
    ]
    assert read_runner_receipts_jsonl(files["successes"])[0].receipt_id == (
        success_records[0]["receipt_id"]
    )
    assert success_records[0]["receipt_id"] == result.benchmark_run_receipt_id or (
        success_records[0]["receipt_id"].startswith("configured_gateway_runner:")
    )


def test_runner_receipt_rehydration_rejects_tampered_call_route(tmp_path: Path) -> None:
    files, gateway = _safety_inputs(tmp_path)
    assert _configured_call(files, gateway).accepted is True
    payload = json.loads(files["successes"].read_text(encoding="utf-8").splitlines()[0])
    payload["calls"][0]["api_model"] = "substituted/model"
    with pytest.raises(ValueError, match="runner_receipt_id_mismatch"):
        rehydrate_runner_receipt(payload)
