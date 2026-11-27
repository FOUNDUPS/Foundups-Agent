"""Offline unit tests for Lego scaffolding benchmark protocol (mocks only)."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import pytest

from modules.ai_intelligence.ai_gateway.src.lego_scaffolding_benchmark_protocol import (
    AGI_SCAFFOLDING_HYPOTHESIS_STATUS, LEGO_TASK_FAMILIES, AuthorTaskRunResult,
    AuthorVisibleTaskSpec, BenchmarkExperimentArm, FreshSessionTransferReceipt,
    LegoStratifiedBenchmarkSummaryReceipt, MatchedAggregateBudget, MemberCallUsage,
    StratifiedBenchmarkCorpus, build_benchmark_cost_summary, build_lego_benchmark_task,
    evaluate_fresh_session_transfer, run_stratified_lego_benchmark,
    validate_controlled_ablation, verify_rollback_restore,
)
from modules.ai_intelligence.ai_gateway.src.model_combination_benchmark_harness import (
    ModelBenchmarkRoleAssignment, ModelBenchmarkVerifierResult, build_model_benchmark_candidate,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import VerifierDecision


def _dig(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _sha1_like(label: str) -> str:
    return hashlib.sha1(label.encode("utf-8")).hexdigest()


def _make_split_tasks(split_tag: str, per_family: int):
    ctx, vc = _dig("shared-bounded-context-v1"), _dig("verifier-contract-v1")
    return tuple(
        build_lego_benchmark_task(
            task_id=f"{split_tag}-{fam}-{idx}", task_family=fam,
            prompt_digest=_dig(f"prompt:{split_tag}-{fam}-{idx}"),
            expected_output_digest=_dig(f"expected:{split_tag}-{fam}-{idx}"),
            verifier_contract_digest=vc, bounded_context_digest=ctx,
        )
        for fam in LEGO_TASK_FAMILIES
        for idx in range(per_family)
    )


def _make_corpus() -> StratifiedBenchmarkCorpus:
    return StratifiedBenchmarkCorpus(
        corpus_id="lego-slice1-v1",
        dev_tasks=_make_split_tasks("dev", 2),
        held_out_a_tasks=_make_split_tasks("hoa", 3),
        held_out_b_tasks=_make_split_tasks("hob", 3),
    )


def _default_budget() -> MatchedAggregateBudget:
    return MatchedAggregateBudget(1200, 600, 2000, 4)


def test_stratified_corpus_validates_balanced_8_12_12_and_rejects_skew_or_overlap():
    corpus = _make_corpus()
    assert (len(corpus.dev_tasks), len(corpus.held_out_a_tasks), len(corpus.held_out_b_tasks)) == (8, 12, 12)
    assert corpus.corpus_digest.startswith("lego_stratified_corpus:")

    ctx, vc = _dig("ctx"), _dig("vc")
    skewed_dev = tuple(
        build_lego_benchmark_task(
            task_id=f"s-{fam}-{i}", task_family=fam, prompt_digest=_dig(f"sp-{fam}-{i}"),
            expected_output_digest=_dig(f"se-{fam}-{i}"), verifier_contract_digest=vc, bounded_context_digest=ctx,
        )
        for fam, count in zip(LEGO_TASK_FAMILIES, (3, 3, 1, 1))
        for i in range(count)
    )
    assert len(skewed_dev) == 8
    with pytest.raises(ValueError, match="unbalanced_stratified_split:dev"):
        StratifiedBenchmarkCorpus("skewed", skewed_dev, corpus.held_out_a_tasks, corpus.held_out_b_tasks)

    dup_id_hoa = list(corpus.held_out_a_tasks)
    dup_id_hoa[0] = build_lego_benchmark_task(
        task_id=corpus.dev_tasks[0].task_id, task_family=dup_id_hoa[0].task_family,
        prompt_digest=_dig("unique-p"), expected_output_digest=_dig("unique-e"),
        verifier_contract_digest=vc, bounded_context_digest=ctx,
    )
    with pytest.raises(ValueError, match="overlapping_benchmark_task_ids"):
        StratifiedBenchmarkCorpus("dup-id", corpus.dev_tasks, tuple(dup_id_hoa), corpus.held_out_b_tasks)

    dup_prompt_hob = list(corpus.held_out_b_tasks)
    dup_prompt_hob[0] = build_lego_benchmark_task(
        task_id="distinct-hob-id", task_family=dup_prompt_hob[0].task_family,
        prompt_digest=corpus.dev_tasks[0].prompt_digest, expected_output_digest=_dig("unique-e2"),
        verifier_contract_digest=vc, bounded_context_digest=ctx,
    )
    with pytest.raises(ValueError, match="overlapping_benchmark_prompt_digests"):
        StratifiedBenchmarkCorpus("dup-p", corpus.dev_tasks, corpus.held_out_a_tasks, tuple(dup_prompt_hob))


def test_author_runner_receives_sealed_spec_only_and_verifier_role_stays_reserved():
    corpus = _make_corpus()
    cand = build_model_benchmark_candidate(
        (ModelBenchmarkRoleAssignment(role="principal", model_id="mock/author-a", provider="mock"),)
    )
    seen: list[AuthorVisibleTaskSpec] = []

    def author(spec, c, _budget):
        assert isinstance(spec, AuthorVisibleTaskSpec)
        assert not hasattr(spec, "expected_output_digest")
        assert not hasattr(spec, "verifier_contract_digest")
        assert not hasattr(spec, "metadata") and not hasattr(spec, "__dict__")
        seen.append(spec)
        return AuthorTaskRunResult(_dig(f"expected:{spec.task_id}"), f"run:{c.candidate_id}:{spec.task_id}", 200, 100, 50, 1, 0.01)

    def verifier(task, c, out):
        ok = out.output_digest == task.expected_output_digest
        return ModelBenchmarkVerifierResult(VerifierDecision.ACCEPT if ok else VerifierDecision.REJECT, f"ver:{c.candidate_id}:{task.task_id}", ok)

    summary = run_stratified_lego_benchmark(
        corpus=corpus, split="held_out_a", candidates=(cand,), author_runner=author, verifier=verifier,
        verifier_digest=_dig("verifier-v1"), aggregate_budget=_default_budget(), context_bundle_digest=_dig("shared-bounded-context-v1"),
    )
    assert len(seen) == 12 and len(summary.family_run_receipts) == 4
    assert summary.candidate_summaries[0].accepted_count == 12
    assert summary.agi_scaffolding_hypothesis_status == AGI_SCAFFOLDING_HYPOTHESIS_STATUS

    with pytest.raises(ValueError, match="verifier_role_reserved_for_independent_verifier"):
        build_model_benchmark_candidate((
            ModelBenchmarkRoleAssignment(role="principal", model_id="mock/lead", provider="mock"),
            ModelBenchmarkRoleAssignment(role="verifier", model_id="mock/self", provider="mock"),
        ))


def test_matched_aggregate_budget_enforced_across_swarm_members():
    corpus, budget = _make_corpus(), _default_budget()
    solo = build_model_benchmark_candidate((ModelBenchmarkRoleAssignment("principal", "mock/solo", "mock"),))
    swarm_tok = build_model_benchmark_candidate(tuple(
        ModelBenchmarkRoleAssignment(r, f"mock/{r}", "mock") for r in ("principal", "planner", "coder", "critic")
    ))
    swarm_inv = build_model_benchmark_candidate((
        ModelBenchmarkRoleAssignment("principal", "mock/l2", "mock"),
        ModelBenchmarkRoleAssignment("critic", "mock/c2", "mock"),
    ))

    def runner(spec, cand, _b):
        if cand.candidate_id == solo.candidate_id:
            return AuthorTaskRunResult(_dig(f"o:{spec.task_id}"), f"r:{cand.candidate_id}:{spec.task_id}", 900, 300, 400, 1, 0.02)
        if cand.candidate_id == swarm_tok.candidate_id:
            return AuthorTaskRunResult.from_member_usages(
                output_digest=_dig(f"o:{spec.task_id}"), runner_receipt_id=f"r:{cand.candidate_id}:{spec.task_id}",
                member_usages=tuple(MemberCallUsage(ra.role, 400, 80, 100) for ra in cand.role_assignments), provider_billed_usd=0.08,
            )
        return AuthorTaskRunResult.from_member_usages(
            output_digest=_dig(f"o:{spec.task_id}"), runner_receipt_id=f"r:{cand.candidate_id}:{spec.task_id}",
            member_usages=(MemberCallUsage("principal", 300, 100, 100, 3), MemberCallUsage("critic", 300, 100, 100, 2)),
            provider_billed_usd=0.05,
        )

    summary = run_stratified_lego_benchmark(
        corpus=corpus, split="dev", candidates=(solo, swarm_tok, swarm_inv), author_runner=runner,
        verifier=lambda t, c, _o: ModelBenchmarkVerifierResult(VerifierDecision.ACCEPT, f"v:{c.candidate_id}:{t.task_id}", True),
        verifier_digest=_dig("ver"), aggregate_budget=budget, context_bundle_digest=_dig("shared-bounded-context-v1"),
    )
    by_id = {c.candidate_id: c for c in summary.candidate_summaries}
    assert by_id[solo.candidate_id].accepted_count == 8
    assert by_id[swarm_tok.candidate_id].accepted_count == 0 and by_id[swarm_tok.candidate_id].budget_exceeded_count == 8
    assert by_id[swarm_inv.candidate_id].accepted_count == 0 and by_id[swarm_inv.candidate_id].budget_exceeded_count == 8
    over_samples = [
        s for r in summary.family_run_receipts for s in r.samples if s.candidate_id == swarm_tok.candidate_id
    ]
    assert all(s.decision == VerifierDecision.REJECT and "aggregate_budget_exceeded" in s.rejection_reasons for s in over_samples)


def test_controlled_ablation_accepts_single_axis_and_rejects_confounds():
    corpus, budget = _make_corpus(), _default_budget()
    base = BenchmarkExperimentArm("a1", "solo", "prose_v1", "tier_mid", "gate_v1", corpus.corpus_digest, _dig("v"), _dig("c"), budget)
    m2m = BenchmarkExperimentArm("a2", "solo", "m2m_v1", "tier_mid", "gate_v1", corpus.corpus_digest, _dig("v"), _dig("c"), budget)
    assert validate_controlled_ablation(base, m2m, "prompt_format").varied_axis == "prompt_format"

    confounded = BenchmarkExperimentArm("a3", "panel_4", "m2m_v1", "tier_max", "gate_v1", corpus.corpus_digest, _dig("v"), _dig("c"), budget)
    with pytest.raises(ValueError, match="confounded_ablation_axes:topology,prompt_format,model_tier"):
        validate_controlled_ablation(base, confounded, "topology")

    bad_budget = BenchmarkExperimentArm("a4", "panel_4", "prose_v1", "tier_mid", "gate_v1", corpus.corpus_digest, _dig("v"), _dig("c"), MatchedAggregateBudget(2400, 600, 2000, 8))
    with pytest.raises(ValueError, match="ablation_invariant_mismatch:aggregate_budget"):
        validate_controlled_ablation(base, bad_budget, "topology")


def test_honest_cost_accounting_separates_usd_subscription_quota_and_unknowns():
    zero_acc = build_benchmark_cost_summary(sample_count=12, accepted_count=0, provider_billed_usd=0.36)
    assert zero_acc.cost_per_accepted_usd is None and zero_acc.provider_billed_usd == 0.36

    sub_run = build_benchmark_cost_summary(
        sample_count=12, accepted_count=9, provider_billed_usd=None,
        subscription_quota_delta_pct=7.5, local_compute_wall_ms=1450,
    )
    assert sub_run.provider_billed_usd is None and sub_run.cost_per_accepted_usd is None
    assert sub_run.subscription_quota_delta_pct == 7.5
    assert {"subscription_quota_usd_rate_unknown", "host_power_unmeasured"}.issubset(sub_run.unmeasured_unknowns)

    with pytest.raises(ValueError, match="subscription_quota_burn_cannot_claim_zero_usd"):
        build_benchmark_cost_summary(sample_count=4, accepted_count=4, provider_billed_usd=0.0, subscription_quota_delta_pct=2.0)


def test_fresh_session_transfer_rejects_warm_session_leakage_regression_and_bad_rollback():
    corpus = _make_corpus()
    prior_bytes = b"prompt_template: prose_v1\ngate: strict\n"
    prior_sha, work_sha = hashlib.sha256(prior_bytes).hexdigest(), _sha1_like("clean-worktree")
    rb_fail = verify_rollback_restore(prior_sha, prior_bytes + b"x")
    rb_ok = verify_rollback_restore(f"sha256:{prior_sha}", prior_bytes)
    assert (not rb_fail) and rb_fail.failure_reason == "ROLLBACK_SHA256_MISMATCH" and bool(rb_ok)

    base_kw = dict(
        corpus=corpus, fresh_session_cold_start=True, inherited_session_history=False,
        baseline_worktree_sha=work_sha, clean_worktree_sha=work_sha,
        refinement_source_task_ids=(corpus.dev_tasks[0].task_id,),
        refinement_source_digests=(corpus.dev_tasks[0].prompt_digest,),
        baseline_pass_rate_a=0.666667, refined_pass_rate_a=0.75,
        baseline_pass_rate_b=0.5, refined_pass_rate_b=0.75, rollback_receipt=rb_ok,
    )
    assert "WARM_SESSION_HISTORY_INHERITED" in evaluate_fresh_session_transfer(**{**base_kw, "inherited_session_history": True}).rejection_reasons
    assert "HELD_OUT_LEAKAGE_DETECTED" in evaluate_fresh_session_transfer(
        **{**base_kw, "refinement_source_digests": (corpus.held_out_b_tasks[0].expected_output_digest,)}
    ).rejection_reasons
    assert "HELD_OUT_LEAKAGE_DETECTED" in evaluate_fresh_session_transfer(
        **{**base_kw, "refinement_source_task_ids": (corpus.held_out_a_tasks[0].task_id,)}
    ).rejection_reasons
    assert "HELD_OUT_A_REGRESSION" in evaluate_fresh_session_transfer(**{**base_kw, "refined_pass_rate_a": 0.5}).rejection_reasons
    assert "ROLLBACK_RESTORE_UNVERIFIED" in evaluate_fresh_session_transfer(**{**base_kw, "rollback_receipt": rb_fail}).rejection_reasons

    ok = evaluate_fresh_session_transfer(**base_kw)
    assert ok.accepted and ok.decision == "TRANSFER_GAIN_RECORDED"
    assert ok.agi_scaffolding_hypothesis_status == "HYPOTHESIS_UNDER_TEST"
    with pytest.raises(ValueError, match="invalid_agi_scaffolding_hypothesis_status"):
        FreshSessionTransferReceipt(
            ok.receipt_id, True, ok.decision, corpus.corpus_digest, True, False, work_sha, work_sha,
            0.5, 0.5, 0.5, 0.75, 0.0, 0.25, True, rb_ok.receipt_id, (), "DEMONSTRATED",
        )


def test_deterministic_receipts_and_static_import_confinement():
    c1, c2 = _make_corpus(), _make_corpus()
    assert c1.corpus_digest == c2.corpus_digest
    cand = build_model_benchmark_candidate((ModelBenchmarkRoleAssignment("principal", "mock/det", "mock"),))
    runner = lambda spec, c, _b: AuthorTaskRunResult(_dig(f"d:{spec.task_id}"), f"r:{c.candidate_id}:{spec.task_id}", 100, 50, 25, 1, None, 0.25, 25)
    ver = lambda t, c, _o: ModelBenchmarkVerifierResult(VerifierDecision.ACCEPT, f"v:{c.candidate_id}:{t.task_id}", True)
    r1 = run_stratified_lego_benchmark(corpus=c1, split="held_out_b", candidates=(cand,), author_runner=runner, verifier=ver, verifier_digest=_dig("vd"), aggregate_budget=_default_budget(), context_bundle_digest=_dig("shared-bounded-context-v1"))
    r2 = run_stratified_lego_benchmark(corpus=c2, split="held_out_b", candidates=(cand,), author_runner=runner, verifier=ver, verifier_digest=_dig("vd"), aggregate_budget=_default_budget(), context_bundle_digest=_dig("shared-bounded-context-v1"))
    assert isinstance(r1, LegoStratifiedBenchmarkSummaryReceipt) and r1.receipt_id == r2.receipt_id
    assert json.dumps(r1.to_dict(), sort_keys=True) == json.dumps(r2.to_dict(), sort_keys=True)

    protocol_path = Path(__file__).resolve().parents[1] / "src" / "lego_scaffolding_benchmark_protocol.py"
    tree = ast.parse(protocol_path.read_text(encoding="utf-8"))
    imported = {
        (alias.name if isinstance(node, ast.Import) else node.module).split(".")[0]
        for node in ast.walk(tree)
        if (isinstance(node, ast.Import) and (aliases := node.names)) or (isinstance(node, ast.ImportFrom) and node.module and (aliases := [node]))
        for alias in (node.names if isinstance(node, ast.Import) else [node])
    }
    assert imported.isdisjoint({"os", "subprocess", "requests", "urllib", "httpx", "openai", "importlib", "socket"})
