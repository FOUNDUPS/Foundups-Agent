"""Corrective safety cases for configured-gateway output persistence."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_configured_gateway_runner_safety import (
    AttemptReceiptStore,
    Caller,
    Guard,
    ReceiptStore,
    SOURCE_PROMPT,
    _budget,
    _candidate,
    _policy,
    _runner,
    _task,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution import (
    REPO_ROOT,
)


class OutputStore:
    def __init__(self, *, error: Exception | None = None, wrong_id: bool = False):
        self.error = error
        self.wrong_id = wrong_id
        self.records = []

    def append(self, record):
        if self.error is not None:
            raise self.error
        self.records.append(record)
        return "wrong:evidence" if self.wrong_id else record.record_id


@pytest.mark.parametrize(
    "output_store",
    (
        OutputStore(error=RuntimeError("sensitive persistence detail")),
        OutputStore(wrong_id=True),
    ),
)
def test_output_evidence_failure_is_terminal_before_completed(output_store) -> None:
    attempts, successes, caller = AttemptReceiptStore(), ReceiptStore(), Caller()
    runner = _runner(
        caller=caller,
        output_store=output_store,
        receipt_store=successes,
        attempt_store=attempts,
    )
    with pytest.raises(ValueError) as raised:
        runner(_task(), _candidate())
    assert str(raised.value) == "configured_gateway_runner_output_evidence_failed"
    assert "sensitive" not in str(raised.value)
    assert [item.status for item in attempts.receipts] == [
        "ATTEMPTED",
        "EVIDENCE_FAILED",
    ]
    assert len(caller.calls) == 1
    assert successes.receipts == []


def test_forged_input_tokens_above_prepared_upper_bound_are_rejected() -> None:
    attempts, output_store = AttemptReceiptStore(), OutputStore()
    caller = Caller(input_tokens=1_000_000)
    runner = _runner(
        caller=caller,
        output_store=output_store,
        attempt_store=attempts,
    )
    with pytest.raises(ValueError, match="input_tokens_exceeded"):
        runner(_task(), _candidate())
    assert [item.status for item in attempts.receipts] == [
        "ATTEMPTED",
        "REJECTED_OUTPUT",
    ]
    assert output_store.records == []


def test_fully_wrapped_prompt_must_fit_prompt_character_cap() -> None:
    caller, guard = Caller(), Guard()
    policy = replace(_policy(), max_prompt_chars=len(SOURCE_PROMPT) + 1)
    with pytest.raises(ValueError, match="prompt_too_large"):
        _runner(caller=caller, guard=guard, policy=policy)(_task(), _candidate())
    assert guard.calls == []
    assert caller.calls == []


def test_public_budget_evidence_rejects_untrusted_route_alias() -> None:
    with pytest.raises(ValueError, match="assignment_route_mismatch"):
        _budget(api_model="provider-side-alias").normalized()


def _function_size(path: Path, name: str) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(
        item
        for item in ast.walk(tree)
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name == name
    )
    return node.end_lineno - node.lineno + 1


def test_corrective_slice_preserves_exact_wsp62_boundaries() -> None:
    main_path = REPO_ROOT / "main.py"
    assert len(main_path.read_text(encoding="utf-8").splitlines()) <= 4978
    assert _function_size(
        main_path, "run_reddog_architect_fix_promotion_preflight"
    ) <= 954
    source = REPO_ROOT / "modules" / "ai_intelligence" / "ai_gateway" / "src"
    assert _function_size(
        source / "model_autoresearch_configured_gateway_runner.py",
        "_execute_call",
    ) <= 50
    assert _function_size(
        source / "model_autoresearch_configured_gateway_evidence.py",
        "rehydrate_call_attempt_receipt",
    ) <= 50
    assert _function_size(
        source
        / "model_autoresearch_campaign_execution_artifact_supply_bootstrap.py",
        "_configured_runner_policy",
    ) <= 50
    assert _function_size(
        source / "model_autoresearch_semantic_verifier.py",
        "_v2_runner_digest_rejections",
    ) <= 50


def test_inherited_wsp62_exemptions_are_exact_no_growth_ceils() -> None:
    module = REPO_ROOT / "modules" / "ai_intelligence" / "ai_gateway"
    config = yaml.safe_load(
        (module / "wsp_62_exemptions.yaml").read_text(encoding="utf-8")
    )
    expected = {
        "run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap": 233,
        "build_model_autoresearch_output_evidence_semantic_verifier": 96,
        "_verifier": 83,
    }
    entries = {}
    for entry in config["exemptions"]:
        for name in entry.get("functions", []):
            if name in expected:
                entries[name] = entry
    assert set(entries) == set(expected)
    for name, ceiling in expected.items():
        entry = entries[name]
        target = module / entry["file"]
        assert _function_size(target, name) == ceiling
        no_growth = entry["no_growth_ceiling"]
        assert no_growth["file_lines"] == len(
            target.read_text(encoding="utf-8").splitlines()
        )
        assert no_growth["functions"][name] == ceiling
        assert set(no_growth["functions"]) == set(entry["functions"])
        assert entry["function_threshold_override"] == max(
            expected[item] for item in entry["functions"]
        )
