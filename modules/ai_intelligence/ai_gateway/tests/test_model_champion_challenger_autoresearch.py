"""Tests for model champion/challenger AutoResearch campaign planner."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_champion_challenger_autoresearch import (
    ModelAutoResearchAction,
    ModelAutoResearchPolicy,
    plan_model_champion_challenger_autoresearch,
    rehydrate_model_autoresearch_plan_receipt,
    rehydrate_model_autoresearch_policy,
)
from modules.ai_intelligence.ai_gateway.src.model_combination_benchmark_harness import (
    ModelBenchmarkRoleAssignment,
    ModelBenchmarkTask,
    ModelBenchmarkTaskOutput,
    ModelBenchmarkVerifierResult,
    build_model_benchmark_candidate,
    run_model_combination_benchmark,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    ModelOutcomeMetrics,
    VerifierDecision,
)
from modules.ai_intelligence.ai_gateway.src.model_promotion_gate import (
    ModelPromotionGateDecision,
    ModelPromotionPolicy,
    evaluate_model_promotion_gate,
)


def _candidate(model_id: str):
    return build_model_benchmark_candidate(
        (ModelBenchmarkRoleAssignment(role="principal", model_id=model_id, provider="provider"),)
    )


def _tasks():
    return (
        ModelBenchmarkTask(
            task_id="task-001",
            task_family="architecture",
            prompt_digest="sha256:prompt-a",
            expected_output_digest="sha256:expected-a",
            verifier_contract_digest="sha256:verifier-contract",
        ),
        ModelBenchmarkTask(
            task_id="task-002",
            task_family="architecture",
            prompt_digest="sha256:prompt-b",
            expected_output_digest="sha256:expected-b",
            verifier_contract_digest="sha256:verifier-contract",
        ),
    )


def _runner(task, candidate):
    return ModelBenchmarkTaskOutput(
        output_digest=f"sha256:output:{candidate.candidate_id}:{task.task_id}",
        runner_receipt_id=f"runner:{candidate.candidate_id}:{task.task_id}",
        metrics=ModelOutcomeMetrics(latency_ms=100, input_tokens=10, output_tokens=5, cost_estimate_usd=0.01),
    )


def _verifier(pass_all: bool):
    def verifier(task, candidate, output):
        if pass_all or task.task_id == "task-001":
            return ModelBenchmarkVerifierResult(
                decision=VerifierDecision.ACCEPT,
                verifier_receipt_id=f"verify:{candidate.candidate_id}:{task.task_id}",
                evidence_correct=True,
            )
        return ModelBenchmarkVerifierResult(
            decision=VerifierDecision.REJECT,
            verifier_receipt_id=f"verify:{candidate.candidate_id}:{task.task_id}",
            evidence_correct=False,
            rejection_reasons=("bad_claim",),
        )

    return verifier


def _gate(candidate_id: str, *, pass_all: bool):
    candidate = _candidate(candidate_id)
    run = run_model_combination_benchmark(
        tasks=_tasks(),
        candidates=(candidate,),
        runner=_runner,
        verifier=_verifier(pass_all),
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )
    policy = ModelPromotionPolicy(
        task_family="architecture",
        candidate_id=candidate_id,
        min_verifier_pass_rate=0.9,
        min_sample_count=2,
        required_task_set_digest=run.task_set_digest,
        required_held_out_split_digest=run.held_out_split_digest,
        required_verifier_digest=run.verifier_digest,
    )
    return evaluate_model_promotion_gate(
        benchmark_run_receipt=run,
        policy=policy,
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signed:1",
    )


def _policy():
    return ModelAutoResearchPolicy(
        task_family="architecture",
        catalog_snapshot_id="model_catalog_snapshot:1",
        max_campaign_items=3,
        required_verifier_digest="sha256:verifier",
        cost_budget_receipt_id="cost_budget:1",
    )


def _feedback_record(model_id: str, *, suffix: str = "1") -> dict:
    return {
        "record_type": "model_selection_outcome_feedback",
        "schema_version": "model_feedback_ledger_record.v1",
        "feedback_record_id": f"model_feedback_{suffix}",
        "outcome_receipt_id": f"model_selection_outcome_receipt:{suffix}",
        "selection_receipt_id": f"model_selection_receipt:{suffix}",
        "catalog_snapshot_id": "model_catalog_snapshot:1",
        "task_family": "architecture",
        "selected_model_ids": [model_id],
        "verification_receipt_ids": [f"verify:{suffix}"],
        "source_ratchet_id": f"outcome_ratchet_{suffix}",
        "source_ratchet_digest": "sha256:" + suffix[0].rjust(64, "0"),
    }


def test_autoresearch_plans_new_candidate_and_rebenchmark_challenger():
    champion_gate = _gate("provider/champion", pass_all=True)
    challenger_gate = _gate("provider/challenger", pass_all=False)
    new_candidate = _candidate("provider/new")

    receipt = plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(champion_gate, challenger_gate),
        candidate_pool=(_candidate("provider/champion"), _candidate("provider/challenger"), new_candidate),
        policy=_policy(),
    )

    assert champion_gate.decision == ModelPromotionGateDecision.PROMOTE_CHAMPION
    assert receipt.rejection_reasons == ()
    assert receipt.receipt_id.startswith("model_autoresearch_plan:")
    assert [item.action for item in receipt.campaign_items] == [
        ModelAutoResearchAction.REBENCHMARK_CHALLENGER,
        ModelAutoResearchAction.BENCHMARK_NEW_CANDIDATE,
    ]
    assert [item.candidate_id for item in receipt.campaign_items] == [
        "provider/challenger",
        "provider/new",
    ]
    assert all(item.requires_independent_verifier for item in receipt.campaign_items)


def test_autoresearch_uses_feedback_records_as_bounded_priority_signal():
    challenger_gate = _gate("provider/challenger", pass_all=False)
    feedback = _feedback_record("provider/new", suffix="2")

    receipt = plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(challenger_gate,),
        candidate_pool=(
            _candidate("provider/challenger"),
            _candidate("provider/new"),
        ),
        policy=_policy(),
        feedback_records=(feedback,),
    )

    assert receipt.rejection_reasons == ()
    assert receipt.source_feedback_record_ids == ("model_feedback_2",)
    assert receipt.feedback_ledger_digest.startswith("model_autoresearch_feedback_ledger:")
    assert [item.candidate_id for item in receipt.campaign_items] == [
        "provider/new",
        "provider/challenger",
    ]
    assert receipt.campaign_items[0].priority == "P0"
    assert receipt.campaign_items[0].reason == "verified_runtime_feedback_unbenchmarked_candidate"


def test_autoresearch_plan_receipt_rehydrates_with_digest_verification():
    challenger_gate = _gate("provider/challenger", pass_all=False)
    feedback = _feedback_record("provider/new", suffix="2")
    receipt = plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(challenger_gate,),
        candidate_pool=(
            _candidate("provider/challenger"),
            _candidate("provider/new"),
        ),
        policy=_policy(),
        feedback_records=(feedback,),
    )

    rehydrated = rehydrate_model_autoresearch_plan_receipt(receipt.to_dict())

    assert rehydrated == receipt
    assert rehydrate_model_autoresearch_policy(receipt.policy.to_dict()) == receipt.policy


def test_autoresearch_plan_receipt_rejects_tampered_security_fields():
    challenger_gate = _gate("provider/challenger", pass_all=False)
    receipt = plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(challenger_gate,),
        candidate_pool=(
            _candidate("provider/challenger"),
            _candidate("provider/new"),
        ),
        policy=_policy(),
    )
    mutations = []

    policy_tamper = receipt.to_dict()
    policy_tamper["policy"]["catalog_snapshot_id"] = "model_catalog_snapshot:tampered"
    mutations.append(policy_tamper)

    source_gate_tamper = receipt.to_dict()
    source_gate_tamper["source_gate_receipt_ids"] = ["model_promotion_gate:tampered"]
    mutations.append(source_gate_tamper)

    pool_tamper = receipt.to_dict()
    pool_tamper["candidate_pool_digest"] = "model_autoresearch_candidate_pool:tampered"
    mutations.append(pool_tamper)

    feedback_tamper = receipt.to_dict()
    feedback_tamper["feedback_ledger_digest"] = "model_autoresearch_feedback_ledger:tampered"
    mutations.append(feedback_tamper)

    campaign_tamper = receipt.to_dict()
    campaign_tamper["campaign_items"][0]["candidate_id"] = "provider/tampered"
    mutations.append(campaign_tamper)

    rejection_tamper = receipt.to_dict()
    rejection_tamper["rejection_reasons"] = ["invented_reason"]
    mutations.append(rejection_tamper)

    for payload in mutations:
        try:
            rehydrate_model_autoresearch_plan_receipt(payload)
        except ValueError as exc:
            assert str(exc) == "model_autoresearch_plan_receipt_id_mismatch"
        else:
            raise AssertionError("tampered AutoResearch plan receipt was accepted")


def test_autoresearch_plan_receipt_rejects_malformed_shape_before_digest_check():
    receipt = plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(_gate("provider/challenger", pass_all=False),),
        candidate_pool=(_candidate("provider/challenger"),),
        policy=_policy(),
    )
    bad_schema = receipt.to_dict()
    bad_schema["schema_version"] = "other"
    bad_action = receipt.to_dict()
    bad_action["campaign_items"][0]["action"] = "run_provider_live"
    bad_verifier_flag = receipt.to_dict()
    bad_verifier_flag["campaign_items"][0]["requires_independent_verifier"] = "true"

    for payload, expected in (
        (bad_schema, "invalid_autoresearch_plan_schema"),
        (bad_action, "invalid_autoresearch_campaign_action"),
        (bad_verifier_flag, "invalid_autoresearch_campaign_verifier_flag"),
    ):
        try:
            rehydrate_model_autoresearch_plan_receipt(payload)
        except ValueError as exc:
            assert str(exc) == expected
        else:
            raise AssertionError(f"expected {expected}")


def test_autoresearch_rejects_malformed_or_mismatched_feedback_records():
    challenger_gate = _gate("provider/challenger", pass_all=False)
    malformed = _feedback_record("provider/new")
    malformed["source_ratchet_digest"] = "not-a-digest"
    mismatched = _feedback_record("provider/new")
    mismatched["task_family"] = "security"

    for record, expected in (
        (malformed, "feedback_source_ratchet_digest_invalid"),
        (mismatched, "feedback_task_family_mismatch"),
    ):
        try:
            plan_model_champion_challenger_autoresearch(
                promotion_gate_receipts=(challenger_gate,),
                candidate_pool=(_candidate("provider/new"),),
                policy=_policy(),
                feedback_records=(record,),
            )
        except ValueError as exc:
            assert str(exc) == expected
        else:
            raise AssertionError("feedback record was accepted")


def test_autoresearch_feedback_cannot_invent_candidate():
    challenger_gate = _gate("provider/challenger", pass_all=False)

    receipt = plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(challenger_gate,),
        candidate_pool=(_candidate("provider/challenger"),),
        policy=_policy(),
        feedback_records=(_feedback_record("provider/unlisted"),),
    )

    assert [item.candidate_id for item in receipt.campaign_items] == ["provider/challenger"]
    assert all(item.candidate_id != "provider/unlisted" for item in receipt.campaign_items)


def test_autoresearch_stops_when_no_candidates_need_work():
    champion_gate = _gate("provider/champion", pass_all=True)

    receipt = plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(champion_gate,),
        candidate_pool=(_candidate("provider/champion"),),
        policy=_policy(),
    )

    assert receipt.rejection_reasons == ()
    assert len(receipt.campaign_items) == 1
    assert receipt.campaign_items[0].action == ModelAutoResearchAction.STOP
    assert receipt.campaign_items[0].requires_independent_verifier is False


def test_autoresearch_requires_gate_receipts_and_cost_budget():
    receipt = plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(),
        candidate_pool=(_candidate("provider/new"),),
        policy=ModelAutoResearchPolicy(
            task_family="architecture",
            catalog_snapshot_id="model_catalog_snapshot:1",
            required_verifier_digest="sha256:verifier",
        ),
    )

    assert receipt.campaign_items == ()
    assert receipt.rejection_reasons == (
        "missing_cost_budget_receipt",
        "missing_promotion_gate_receipts",
    )


def test_autoresearch_rejects_verifier_digest_mismatch():
    champion_gate = _gate("provider/champion", pass_all=True)

    receipt = plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(champion_gate,),
        candidate_pool=(_candidate("provider/new"),),
        policy=ModelAutoResearchPolicy(
            task_family="architecture",
            catalog_snapshot_id="model_catalog_snapshot:1",
            required_verifier_digest="sha256:wrong",
            cost_budget_receipt_id="cost_budget:1",
        ),
    )

    assert receipt.campaign_items == ()
    assert receipt.rejection_reasons == ("verifier_digest_mismatch",)


def test_autoresearch_max_campaign_items_caps_output():
    challenger = _gate("provider/challenger", pass_all=False)
    receipt = plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(challenger,),
        candidate_pool=(
            _candidate("provider/a"),
            _candidate("provider/b"),
            _candidate("provider/c"),
            _candidate("provider/challenger"),
        ),
        policy=ModelAutoResearchPolicy(
            task_family="architecture",
            catalog_snapshot_id="model_catalog_snapshot:1",
            max_campaign_items=2,
            required_verifier_digest="sha256:verifier",
            cost_budget_receipt_id="cost_budget:1",
        ),
    )

    assert len(receipt.campaign_items) == 2
    assert receipt.campaign_items[0].action == ModelAutoResearchAction.REBENCHMARK_CHALLENGER


def test_autoresearch_digest_is_stable_and_binds_candidate_pool():
    champion_gate = _gate("provider/champion", pass_all=True)
    first = plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(champion_gate,),
        candidate_pool=(_candidate("provider/new"),),
        policy=_policy(),
    )
    second = plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(champion_gate,),
        candidate_pool=(_candidate("provider/new"),),
        policy=_policy(),
    )
    changed = plan_model_champion_challenger_autoresearch(
        promotion_gate_receipts=(champion_gate,),
        candidate_pool=(_candidate("provider/other"),),
        policy=_policy(),
    )

    assert first.receipt_id == second.receipt_id
    assert first.receipt_id != changed.receipt_id


def test_autoresearch_module_has_no_network_command_or_pattern_memory_imports():
    source = Path(
        "modules/ai_intelligence/ai_gateway/src/model_champion_challenger_autoresearch.py"
    ).read_text()
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert not (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id in {"os", "subprocess", "requests", "urllib", "openai"}
            )

    assert "subprocess" not in imported
    assert "requests" not in imported
    assert "urllib" not in imported
    assert "openai" not in imported
