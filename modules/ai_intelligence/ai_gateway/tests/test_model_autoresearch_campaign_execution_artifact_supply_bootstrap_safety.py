"""Configured-gateway bootstrap safety artifact contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

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
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution import (
    REPO_ROOT,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution_artifact_supply_bootstrap import (
    _configured_inputs,
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
