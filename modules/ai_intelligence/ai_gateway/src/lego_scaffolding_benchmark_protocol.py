"""Offline stratified benchmark protocol for Lego scaffolding hypotheses.

Composes ``model_combination_benchmark_harness`` across the 4 Lego task families
with balanced 8/12/12 splits, sealed author views, matched swarm budgets,
single-axis ablations, honest cost accounting, cold transfer, and byte rollback.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib, hmac, json, math
from typing import Any, Callable, Mapping, Sequence

from .model_combination_benchmark_harness import (
    BenchmarkRunner, BenchmarkVerifier, ModelBenchmarkCandidate, ModelBenchmarkRoleAssignment,
    ModelBenchmarkTask, ModelBenchmarkTaskOutput, ModelBenchmarkVerifierResult,
    ModelCombinationBenchmarkRunReceipt, build_model_benchmark_candidate, run_model_combination_benchmark,
)
from .model_intelligence_outcomes import ModelOutcomeMetrics, VerifierDecision

AGI_SCAFFOLDING_HYPOTHESIS_STATUS = "HYPOTHESIS_UNDER_TEST"
LEGO_TASK_FAMILIES: tuple[str, ...] = ("f1_dead_dup_triage", "f2_manifest_contract", "f3_bounded_repair", "f4_lego_adapter")
SPLIT_PER_FAMILY_COUNTS: Mapping[str, int] = {"dev": 2, "held_out_a": 3, "held_out_b": 3}
CONTROLLED_ABLATION_AXES: tuple[str, ...] = ("topology", "prompt_format", "model_tier", "scaffolding_gate")
CORPUS_SCHEMA_VERSION = "lego_stratified_benchmark_corpus.v1"
SUMMARY_SCHEMA_VERSION = "lego_stratified_benchmark_summary.v1"
TRANSFER_SCHEMA_VERSION = "lego_fresh_session_transfer_receipt.v1"

def build_lego_benchmark_task(*, task_id: str, task_family: str, prompt_digest: str, expected_output_digest: str, verifier_contract_digest: str, bounded_context_digest: str, metadata: Mapping[str, str] | None = None) -> ModelBenchmarkTask:
    merged = {**(metadata or {}), "bounded_context_digest": _req("bounded_context_digest", bounded_context_digest)}
    return ModelBenchmarkTask(task_id=task_id, task_family=task_family, prompt_digest=prompt_digest, expected_output_digest=expected_output_digest, verifier_contract_digest=verifier_contract_digest, metadata=merged).normalized()

@dataclass(frozen=True, slots=True)
class AuthorVisibleTaskSpec:
    """Sealed task view exposed to candidate authors (never ground truth)."""
    task_id: str
    task_family: str
    prompt_digest: str
    bounded_context_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_id", _req("task_id", self.task_id))
        object.__setattr__(self, "task_family", _tok(_req("task_family", self.task_family)))
        object.__setattr__(self, "prompt_digest", _req("prompt_digest", self.prompt_digest))
        object.__setattr__(self, "bounded_context_digest", _req("bounded_context_digest", self.bounded_context_digest))

    @classmethod
    def from_benchmark_task(cls, task: ModelBenchmarkTask, *, fallback_context_digest: str | None = None) -> "AuthorVisibleTaskSpec":
        norm = task.normalized()
        ctx = norm.metadata.get("bounded_context_digest") or (fallback_context_digest or "")
        return cls(norm.task_id, norm.task_family, norm.prompt_digest, _req("bounded_context_digest", ctx))

@dataclass(frozen=True)
class StratifiedBenchmarkCorpus:
    """Balanced 8-dev (2x4) / 12-held-out-A (3x4) / 12-held-out-B (3x4) corpus."""
    corpus_id: str
    dev_tasks: tuple[ModelBenchmarkTask, ...]
    held_out_a_tasks: tuple[ModelBenchmarkTask, ...]
    held_out_b_tasks: tuple[ModelBenchmarkTask, ...]
    corpus_digest: str = ""
    dev_split_digest: str = ""
    held_out_a_digest: str = ""
    held_out_b_digest: str = ""
    schema_version: str = CORPUS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        cid = _req("corpus_id", self.corpus_id)
        dev = _validate_split("dev", self.dev_tasks, SPLIT_PER_FAMILY_COUNTS["dev"])
        hoa = _validate_split("held_out_a", self.held_out_a_tasks, SPLIT_PER_FAMILY_COUNTS["held_out_a"])
        hob = _validate_split("held_out_b", self.held_out_b_tasks, SPLIT_PER_FAMILY_COUNTS["held_out_b"])
        all_tasks = dev + hoa + hob
        if len({t.task_id for t in all_tasks}) != len(all_tasks):
            raise ValueError("overlapping_benchmark_task_ids")
        if len({t.prompt_digest for t in all_tasks}) != len(all_tasks):
            raise ValueError("overlapping_benchmark_prompt_digests")
        d_dig, a_dig, b_dig = _split_digest(cid, "dev", dev), _split_digest(cid, "held_out_a", hoa), _split_digest(cid, "held_out_b", hob)
        c_dig = _digest_prefixed("lego_stratified_corpus", {"schema_version": self.schema_version, "corpus_id": cid, "dev": d_dig, "a": a_dig, "b": b_dig})
        if self.corpus_digest and not hmac.compare_digest(self.corpus_digest, c_dig):
            raise ValueError("stratified_corpus_digest_mismatch")
        for k, v in (("corpus_id", cid), ("dev_tasks", dev), ("held_out_a_tasks", hoa), ("held_out_b_tasks", hob), ("dev_split_digest", d_dig), ("held_out_a_digest", a_dig), ("held_out_b_digest", b_dig), ("corpus_digest", c_dig)):
            object.__setattr__(self, k, v)

    def split_bundle(self, split: str) -> tuple[tuple[ModelBenchmarkTask, ...], str]:
        bundles = {"dev": (self.dev_tasks, self.dev_split_digest), "held_out_a": (self.held_out_a_tasks, self.held_out_a_digest), "held_out_b": (self.held_out_b_tasks, self.held_out_b_digest)}
        key = _tok(_req("split", split))
        if key not in bundles:
            raise ValueError("unknown_benchmark_split")
        return bundles[key]

@dataclass(frozen=True)
class MatchedAggregateBudget:
    """Matched aggregate budget across all members and turns of a candidate."""
    max_aggregate_input_tokens: int
    max_aggregate_output_tokens: int
    max_aggregate_wall_clock_ms: int
    max_member_invocations: int

    def __post_init__(self) -> None:
        for fn in ("max_aggregate_input_tokens", "max_aggregate_output_tokens", "max_aggregate_wall_clock_ms", "max_member_invocations"):
            object.__setattr__(self, fn, _int_bound(fn, getattr(self, fn), 1))

    def check_usage(self, usage: "AuthorTaskRunResult") -> tuple[str, tuple[str, ...]]:
        exceeded = tuple(code for failed, code in (
            (usage.aggregate_input_tokens > self.max_aggregate_input_tokens, "max_aggregate_input_tokens_exceeded"),
            (usage.aggregate_output_tokens > self.max_aggregate_output_tokens, "max_aggregate_output_tokens_exceeded"),
            (usage.aggregate_wall_clock_ms > self.max_aggregate_wall_clock_ms, "max_aggregate_wall_clock_ms_exceeded"),
            (usage.member_invocations > self.max_member_invocations, "max_member_invocations_exceeded"),
        ) if failed)
        return ("BUDGET_EXCEEDED" if exceeded else "WITHIN_BUDGET"), exceeded

@dataclass(frozen=True)
class MemberCallUsage:
    role: str
    input_tokens: int
    output_tokens: int
    wall_clock_ms: int
    invocations: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _tok(_req("role", self.role)))
        object.__setattr__(self, "input_tokens", _int_bound("input_tokens", self.input_tokens, 0))
        object.__setattr__(self, "output_tokens", _int_bound("output_tokens", self.output_tokens, 0))
        object.__setattr__(self, "wall_clock_ms", _int_bound("wall_clock_ms", self.wall_clock_ms, 0))
        object.__setattr__(self, "invocations", _int_bound("invocations", self.invocations, 1))

@dataclass(frozen=True)
class AuthorTaskRunResult:
    """Candidate execution telemetry summed across all member invocations."""
    output_digest: str
    runner_receipt_id: str
    aggregate_input_tokens: int
    aggregate_output_tokens: int
    aggregate_wall_clock_ms: int
    member_invocations: int = 1
    provider_billed_usd: float | None = None
    subscription_quota_delta_pct: float | None = None
    local_compute_wall_ms: int = 0
    unmeasured_unknowns: tuple[str, ...] = ()
    member_usages: tuple[MemberCallUsage, ...] = ()

    def __post_init__(self) -> None:
        in_t, out_t = _int_bound("aggregate_input_tokens", self.aggregate_input_tokens, 0), _int_bound("aggregate_output_tokens", self.aggregate_output_tokens, 0)
        wall_ms, inv = _int_bound("aggregate_wall_clock_ms", self.aggregate_wall_clock_ms, 0), _int_bound("member_invocations", self.member_invocations, 1)
        if self.member_usages and (in_t < sum(m.input_tokens for m in self.member_usages) or out_t < sum(m.output_tokens for m in self.member_usages) or wall_ms < sum(m.wall_clock_ms for m in self.member_usages) or inv < sum(m.invocations for m in self.member_usages)):
            raise ValueError("member_usage_underreported")
        usd, quota = _opt_float("provider_billed_usd", self.provider_billed_usd), _opt_float("subscription_quota_delta_pct", self.subscription_quota_delta_pct)
        if quota is not None and quota > 0.0 and usd == 0.0:
            raise ValueError("subscription_quota_burn_cannot_claim_zero_usd")
        unknowns = tuple(sorted({_tok(u) for u in self.unmeasured_unknowns if str(u).strip()}))
        for k, v in (("output_digest", _req("output_digest", self.output_digest)), ("runner_receipt_id", _req("runner_receipt_id", self.runner_receipt_id)), ("aggregate_input_tokens", in_t), ("aggregate_output_tokens", out_t), ("aggregate_wall_clock_ms", wall_ms), ("member_invocations", inv), ("provider_billed_usd", usd), ("subscription_quota_delta_pct", quota), ("local_compute_wall_ms", _int_bound("local_compute_wall_ms", self.local_compute_wall_ms, 0)), ("unmeasured_unknowns", unknowns)):
            object.__setattr__(self, k, v)

    @classmethod
    def from_member_usages(cls, *, output_digest: str, runner_receipt_id: str, member_usages: Sequence[MemberCallUsage], provider_billed_usd: float | None = None, subscription_quota_delta_pct: float | None = None, local_compute_wall_ms: int = 0, unmeasured_unknowns: Sequence[str] = ()) -> "AuthorTaskRunResult":
        usages = tuple(member_usages)
        if not usages:
            raise ValueError("missing_member_usages")
        return cls(output_digest, runner_receipt_id, sum(m.input_tokens for m in usages), sum(m.output_tokens for m in usages), sum(m.wall_clock_ms for m in usages), sum(m.invocations for m in usages), provider_billed_usd, subscription_quota_delta_pct, local_compute_wall_ms, tuple(unmeasured_unknowns), usages)

    def to_task_output(self) -> ModelBenchmarkTaskOutput:
        return ModelBenchmarkTaskOutput(self.output_digest, self.runner_receipt_id, ModelOutcomeMetrics(self.aggregate_wall_clock_ms, self.aggregate_input_tokens, self.aggregate_output_tokens, self.provider_billed_usd))

AuthorRunner = Callable[[AuthorVisibleTaskSpec, ModelBenchmarkCandidate, MatchedAggregateBudget], AuthorTaskRunResult | ModelBenchmarkTaskOutput]

@dataclass(frozen=True)
class BenchmarkExperimentArm:
    arm_id: str
    topology: str
    prompt_format: str
    model_tier: str
    scaffolding_gate: str
    corpus_digest: str
    verifier_digest: str
    context_bundle_digest: str
    aggregate_budget: MatchedAggregateBudget

    def normalized(self) -> "BenchmarkExperimentArm":
        if not isinstance(self.aggregate_budget, MatchedAggregateBudget):
            raise ValueError("invalid_aggregate_budget")
        return BenchmarkExperimentArm(_req("arm_id", self.arm_id), _req("topology", self.topology), _tok(_req("prompt_format", self.prompt_format)), _tok(_req("model_tier", self.model_tier)), _tok(_req("scaffolding_gate", self.scaffolding_gate)), _req("corpus_digest", self.corpus_digest), _req("verifier_digest", self.verifier_digest), _req("context_bundle_digest", self.context_bundle_digest), self.aggregate_budget)

@dataclass(frozen=True)
class ControlledAblationPair:
    pair_id: str
    varied_axis: str
    arm_a: BenchmarkExperimentArm
    arm_b: BenchmarkExperimentArm

def validate_controlled_ablation(arm_a: BenchmarkExperimentArm, arm_b: BenchmarkExperimentArm, varied_axis: str) -> ControlledAblationPair:
    axis = _tok(_req("varied_axis", varied_axis))
    if axis not in CONTROLLED_ABLATION_AXES:
        raise ValueError("invalid_ablation_axis")
    left, right = arm_a.normalized(), arm_b.normalized()
    for inv in ("corpus_digest", "verifier_digest", "context_bundle_digest", "aggregate_budget"):
        if getattr(left, inv) != getattr(right, inv):
            raise ValueError(f"ablation_invariant_mismatch:{inv}")
    differing = tuple(ax for ax in CONTROLLED_ABLATION_AXES if getattr(left, ax) != getattr(right, ax))
    if not differing:
        raise ValueError("ablation_varied_axis_unchanged")
    if differing != (axis,):
        raise ValueError(f"confounded_ablation_axes:{','.join(differing)}")
    return ControlledAblationPair(_digest_prefixed("lego_controlled_ablation", {"axis": axis, "a": left.arm_id, "b": right.arm_id, "c": left.corpus_digest}), axis, left, right)

@dataclass(frozen=True)
class BenchmarkCostSummary:
    sample_count: int
    accepted_count: int
    provider_billed_usd: float | None
    subscription_quota_delta_pct: float | None
    local_compute_wall_ms: int
    cost_per_accepted_usd: float | None
    unmeasured_unknowns: tuple[str, ...]

def build_benchmark_cost_summary(*, sample_count: int, accepted_count: int, provider_billed_usd: float | None, subscription_quota_delta_pct: float | None = None, local_compute_wall_ms: int = 0, unmeasured_unknowns: Sequence[str] = ()) -> BenchmarkCostSummary:
    samples, accepted = _int_bound("sample_count", sample_count, 0), _int_bound("accepted_count", accepted_count, 0)
    if accepted > samples:
        raise ValueError("accepted_exceeds_sample_count")
    usd, quota = _opt_float("provider_billed_usd", provider_billed_usd), _opt_float("subscription_quota_delta_pct", subscription_quota_delta_pct)
    wall_ms = _int_bound("local_compute_wall_ms", local_compute_wall_ms, 0)
    if quota is not None and quota > 0.0 and usd == 0.0:
        raise ValueError("subscription_quota_burn_cannot_claim_zero_usd")
    unknowns = {_tok(u) for u in unmeasured_unknowns if str(u).strip()}
    if quota is not None:
        unknowns.add("subscription_quota_usd_rate_unknown")
    if wall_ms > 0:
        unknowns.add("host_power_unmeasured")
    cpa = round(usd / accepted, 8) if (accepted > 0 and usd is not None) else None
    return BenchmarkCostSummary(samples, accepted, usd, quota, wall_ms, cpa, tuple(sorted(unknowns)))

@dataclass(frozen=True)
class CandidateStratifiedSummary:
    candidate_id: str
    sample_count: int
    accepted_count: int
    pass_rate: float
    budget_exceeded_count: int
    cost_summary: BenchmarkCostSummary

@dataclass(frozen=True)
class LegoStratifiedBenchmarkSummaryReceipt:
    receipt_id: str
    corpus_id: str
    corpus_digest: str
    split: str
    split_digest: str
    verifier_digest: str
    context_bundle_digest: str
    aggregate_budget: MatchedAggregateBudget
    family_run_receipts: tuple[ModelCombinationBenchmarkRunReceipt, ...]
    candidate_summaries: tuple[CandidateStratifiedSummary, ...]
    agi_scaffolding_hypothesis_status: str = AGI_SCAFFOLDING_HYPOTHESIS_STATUS
    schema_version: str = SUMMARY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.agi_scaffolding_hypothesis_status != AGI_SCAFFOLDING_HYPOTHESIS_STATUS:
            raise ValueError("invalid_agi_scaffolding_hypothesis_status")

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "family_run_receipts": [r.to_dict() for r in self.family_run_receipts]}

def adapt_author_runner(author_runner: AuthorRunner, aggregate_budget: MatchedAggregateBudget, *, default_bounded_context_digest: str | None = None, observation_log: dict[tuple[str, str], tuple[AuthorTaskRunResult, str, tuple[str, ...]]] | None = None) -> BenchmarkRunner:
    def _runner(task: ModelBenchmarkTask, candidate: ModelBenchmarkCandidate) -> ModelBenchmarkTaskOutput:
        spec = AuthorVisibleTaskSpec.from_benchmark_task(task, fallback_context_digest=default_bounded_context_digest)
        run_res = _coerce_author_result(author_runner(spec, candidate, aggregate_budget), candidate)
        status, exceeded = aggregate_budget.check_usage(run_res)
        if observation_log is not None:
            observation_log[(candidate.candidate_id, task.task_id)] = (run_res, status, exceeded)
        elif status == "BUDGET_EXCEEDED":
            raise ValueError("aggregate_budget_exceeded")
        return run_res.to_task_output()
    return _runner

def adapt_sealed_author_and_budget(*, author_runner: AuthorRunner, verifier: BenchmarkVerifier, aggregate_budget: MatchedAggregateBudget, default_bounded_context_digest: str | None = None, observation_log: dict[tuple[str, str], tuple[AuthorTaskRunResult, str, tuple[str, ...]]] | None = None) -> tuple[BenchmarkRunner, BenchmarkVerifier]:
    sink = observation_log if observation_log is not None else {}
    runner = adapt_author_runner(author_runner, aggregate_budget, default_bounded_context_digest=default_bounded_context_digest, observation_log=sink)
    def _verifier(task: ModelBenchmarkTask, candidate: ModelBenchmarkCandidate, out: ModelBenchmarkTaskOutput) -> ModelBenchmarkVerifierResult:
        observed = sink.get((candidate.candidate_id, task.task_id))
        if observed is not None and observed[1] == "BUDGET_EXCEEDED":
            return ModelBenchmarkVerifierResult(VerifierDecision.REJECT, f"budget_gate:{candidate.candidate_id}:{task.task_id}", False, ("aggregate_budget_exceeded", *observed[2]))
        return verifier(task, candidate, out)
    return runner, _verifier

def run_stratified_lego_benchmark(*, corpus: StratifiedBenchmarkCorpus, split: str, candidates: Sequence[ModelBenchmarkCandidate], author_runner: AuthorRunner, verifier: BenchmarkVerifier, verifier_digest: str, aggregate_budget: MatchedAggregateBudget, context_bundle_digest: str) -> LegoStratifiedBenchmarkSummaryReceipt:
    split_key = _tok(_req("split", split))
    split_tasks, split_dig = corpus.split_bundle(split_key)
    ctx_dig, ver_dig = _req("context_bundle_digest", context_bundle_digest), _req("verifier_digest", verifier_digest)
    obs: dict[tuple[str, str], tuple[AuthorTaskRunResult, str, tuple[str, ...]]] = {}
    w_runner, w_verifier = adapt_sealed_author_and_budget(author_runner=author_runner, verifier=verifier, aggregate_budget=aggregate_budget, default_bounded_context_digest=ctx_dig, observation_log=obs)
    family_receipts = tuple(
        run_model_combination_benchmark(tasks=tuple(t for t in split_tasks if t.task_family == fam), candidates=candidates, runner=w_runner, verifier=w_verifier, verifier_digest=ver_dig, held_out_split_id=f"{corpus.corpus_id}:{split_key}:{fam}")
        for fam in LEGO_TASK_FAMILIES
    )
    summaries = tuple(_summarize_candidate(c.candidate_id, family_receipts, obs) for c in family_receipts[0].candidates)
    body = {"schema_version": SUMMARY_SCHEMA_VERSION, "corpus_id": corpus.corpus_id, "corpus_digest": corpus.corpus_digest, "split": split_key, "split_digest": split_dig, "verifier_digest": ver_dig, "context_bundle_digest": ctx_dig, "aggregate_budget": asdict(aggregate_budget), "family_receipt_ids": [r.receipt_id for r in family_receipts], "candidate_summaries": [asdict(s) for s in summaries], "agi_scaffolding_hypothesis_status": AGI_SCAFFOLDING_HYPOTHESIS_STATUS}
    return LegoStratifiedBenchmarkSummaryReceipt(_digest_prefixed("lego_stratified_benchmark_summary", body), corpus.corpus_id, corpus.corpus_digest, split_key, split_dig, ver_dig, ctx_dig, aggregate_budget, family_receipts, summaries)

@dataclass(frozen=True)
class RollbackVerificationReceipt:
    receipt_id: str
    verified: bool
    expected_sha256: str
    restored_sha256: str
    restored_byte_length: int
    failure_reason: str | None = None

    def __bool__(self) -> bool:
        return self.verified

def verify_rollback_restore(prior_artifact_sha256: str, restored_bytes: bytes) -> RollbackVerificationReceipt:
    if not isinstance(restored_bytes, bytes):
        raise ValueError("invalid_restored_bytes")
    exp_hex, act_hex = _parse_sha256_hex(prior_artifact_sha256), hashlib.sha256(restored_bytes).hexdigest()
    matched = hmac.compare_digest(exp_hex, act_hex)
    reason = None if matched else "ROLLBACK_SHA256_MISMATCH"
    body = {"verified": matched, "expected_sha256": f"sha256:{exp_hex}", "restored_sha256": f"sha256:{act_hex}", "len": len(restored_bytes), "reason": reason}
    return RollbackVerificationReceipt(_digest_prefixed("lego_rollback_verification", body), matched, f"sha256:{exp_hex}", f"sha256:{act_hex}", len(restored_bytes), reason)

@dataclass(frozen=True)
class FreshSessionTransferReceipt:
    receipt_id: str
    accepted: bool
    decision: str
    corpus_digest: str
    fresh_session_cold_start: bool
    inherited_session_history: bool
    baseline_worktree_sha: str
    clean_worktree_sha: str
    baseline_pass_rate_a: float
    refined_pass_rate_a: float
    baseline_pass_rate_b: float
    refined_pass_rate_b: float
    held_out_a_delta: float
    held_out_b_delta: float
    rollback_verified: bool
    rollback_receipt_id: str | None
    rejection_reasons: tuple[str, ...]
    agi_scaffolding_hypothesis_status: str = AGI_SCAFFOLDING_HYPOTHESIS_STATUS
    schema_version: str = TRANSFER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.agi_scaffolding_hypothesis_status != AGI_SCAFFOLDING_HYPOTHESIS_STATUS:
            raise ValueError("invalid_agi_scaffolding_hypothesis_status")

def evaluate_fresh_session_transfer(*, corpus: StratifiedBenchmarkCorpus, fresh_session_cold_start: bool, inherited_session_history: bool, baseline_worktree_sha: str, clean_worktree_sha: str, refinement_source_task_ids: Sequence[str], refinement_source_digests: Sequence[str], baseline_pass_rate_a: float, refined_pass_rate_a: float, baseline_pass_rate_b: float, refined_pass_rate_b: float, rollback_receipt: RollbackVerificationReceipt | None = None, prior_artifact_sha256: str | None = None, restored_artifact_bytes: bytes | None = None, held_out_trace_digests: Sequence[str] = (), evaluation_stage_completed: bool = True, reuse_before_refine_attempted: bool = True) -> FreshSessionTransferReceipt:
    base_sha, clean_sha = _req("baseline_worktree_sha", baseline_worktree_sha), _req("clean_worktree_sha", clean_worktree_sha)
    b_a, r_a = _unit_rate("baseline_pass_rate_a", baseline_pass_rate_a), _unit_rate("refined_pass_rate_a", refined_pass_rate_a)
    b_b, r_b = _unit_rate("baseline_pass_rate_b", baseline_pass_rate_b), _unit_rate("refined_pass_rate_b", refined_pass_rate_b)
    rb = rollback_receipt or (verify_rollback_restore(prior_artifact_sha256, restored_artifact_bytes) if prior_artifact_sha256 is not None and restored_artifact_bytes is not None else None)
    reasons = _collect_transfer_rejections(corpus, fresh_session_cold_start, inherited_session_history, base_sha, clean_sha, refinement_source_task_ids, refinement_source_digests, held_out_trace_digests, b_a, r_a, b_b, r_b, rb, evaluation_stage_completed, reuse_before_refine_attempted)
    accepted, decision = not reasons, ("TRANSFER_GAIN_RECORDED" if not reasons else "TRANSFER_REJECTED")
    rb_ok, rb_id = bool(rb and rb.verified), (rb.receipt_id if rb else None)
    src_ids_norm = sorted({str(x).strip() for x in refinement_source_task_ids if str(x).strip()})
    src_digs_norm = sorted({str(x).strip() for x in refinement_source_digests if str(x).strip()})
    body = {"schema_version": TRANSFER_SCHEMA_VERSION, "accepted": accepted, "decision": decision, "corpus_digest": corpus.corpus_digest, "cold": bool(fresh_session_cold_start), "inherited": bool(inherited_session_history), "base_sha": base_sha, "clean_sha": clean_sha, "src_ids": src_ids_norm, "src_digs": src_digs_norm, "b_a": b_a, "r_a": r_a, "b_b": b_b, "r_b": r_b, "rb_ok": rb_ok, "rb_id": rb_id, "rejection_reasons": list(reasons)}
    return FreshSessionTransferReceipt(_digest_prefixed("lego_fresh_session_transfer", body), accepted, decision, corpus.corpus_digest, bool(fresh_session_cold_start), bool(inherited_session_history), base_sha, clean_sha, b_a, r_a, b_b, r_b, round(r_a - b_a, 6), round(r_b - b_b, 6), rb_ok, rb_id, reasons)

def _collect_transfer_rejections(corpus: StratifiedBenchmarkCorpus, cold: bool, inherited: bool, base_sha: str, clean_sha: str, src_ids: Sequence[str], src_digs: Sequence[str], trace_digs: Sequence[str], b_a: float, r_a: float, b_b: float, r_b: float, rb: RollbackVerificationReceipt | None, eval_done: bool, reuse_done: bool) -> tuple[str, ...]:
    reasons = [code for failed, code in ((eval_done is not True, "EVALUATE_STAGE_MISSING"), (reuse_done is not True, "REUSE_STAGE_SKIPPED"), (cold is not True or inherited is not False, "WARM_SESSION_HISTORY_INHERITED"), (clean_sha != base_sha, "WORKTREE_SHA_DRIFT")) if failed]
    ho = corpus.held_out_a_tasks + corpus.held_out_b_tasks
    ho_ids, dev_ids = {t.task_id for t in ho}, {t.task_id for t in corpus.dev_tasks}
    forbidden = {t.prompt_digest for t in ho} | {t.expected_output_digest for t in ho} | {corpus.held_out_a_digest, corpus.held_out_b_digest, *(str(d).strip() for d in trace_digs if str(d).strip())}
    ids, digs = tuple(str(x).strip() for x in src_ids if str(x).strip()), tuple(str(x).strip() for x in src_digs if str(x).strip())
    if any(t in ho_ids for t in ids) or any(d in forbidden for d in digs):
        reasons.append("HELD_OUT_LEAKAGE_DETECTED")
    if any(t not in dev_ids and t not in ho_ids for t in ids):
        reasons.append("UNREGISTERED_REFINEMENT_SOURCE_TASK")
    if r_a < b_a:
        reasons.append("HELD_OUT_A_REGRESSION")
    if r_b <= b_b:
        reasons.append("HELD_OUT_B_NO_STRICT_GAIN")
    if rb is None or not rb.verified:
        reasons.append("ROLLBACK_RESTORE_UNVERIFIED")
    return tuple(dict.fromkeys(reasons))

def _coerce_author_result(raw: Any, candidate: ModelBenchmarkCandidate) -> AuthorTaskRunResult:
    if isinstance(raw, AuthorTaskRunResult):
        return raw
    if isinstance(raw, ModelBenchmarkTaskOutput):
        norm = raw.normalized()
        if norm.metrics.input_tokens is None or norm.metrics.output_tokens is None or norm.metrics.latency_ms is None:
            raise ValueError("missing_aggregate_budget_metrics")
        return AuthorTaskRunResult(norm.output_digest, norm.runner_receipt_id, norm.metrics.input_tokens, norm.metrics.output_tokens, norm.metrics.latency_ms, max(1, len(candidate.role_assignments)), norm.metrics.cost_estimate_usd)
    raise ValueError("invalid_author_runner_result")

def _summarize_candidate(candidate_id: str, receipts: Sequence[ModelCombinationBenchmarkRunReceipt], obs: Mapping[tuple[str, str], tuple[AuthorTaskRunResult, str, tuple[str, ...]]]) -> CandidateStratifiedSummary:
    samples = [s for r in receipts for s in r.samples if s.candidate_id == candidate_id]
    n_samples, n_acc = len(samples), sum(1 for s in samples if s.accepted)
    n_over = sum(1 for s in samples if "aggregate_budget_exceeded" in s.rejection_reasons)
    runs = [obs[(candidate_id, s.task_id)][0] for s in samples if (candidate_id, s.task_id) in obs]
    unknowns = {u for r in runs for u in r.unmeasured_unknowns} | ({"runner_error_unmeasured_usage"} if len(runs) < n_samples else set())
    usds = [r.provider_billed_usd for r in runs if r.provider_billed_usd is not None]
    total_usd = round(sum(usds), 8) if (len(runs) == n_samples == len(usds)) else None
    if total_usd is None and usds:
        unknowns.add("partial_provider_usd_unmeasured")
    quotas = [r.subscription_quota_delta_pct for r in runs if r.subscription_quota_delta_pct is not None]
    total_quota = round(sum(quotas), 6) if quotas else None
    if total_quota is not None and total_quota > 0.0 and total_usd == 0.0:
        total_usd = None
    cost = build_benchmark_cost_summary(sample_count=n_samples, accepted_count=n_acc, provider_billed_usd=total_usd, subscription_quota_delta_pct=total_quota, local_compute_wall_ms=sum(r.local_compute_wall_ms for r in runs), unmeasured_unknowns=tuple(sorted(unknowns)))
    return CandidateStratifiedSummary(candidate_id, n_samples, n_acc, round(n_acc / n_samples, 6) if n_samples else 0.0, n_over, cost)

def _validate_split(name: str, tasks: Sequence[ModelBenchmarkTask], expected_per_family: int) -> tuple[ModelBenchmarkTask, ...]:
    norm = tuple(t.normalized() for t in tasks)
    counts = {fam: 0 for fam in LEGO_TASK_FAMILIES}
    for task in norm:
        if task.task_family not in counts:
            raise ValueError(f"unknown_lego_task_family:{task.task_family}")
        counts[task.task_family] += 1
    if any(c != expected_per_family for c in counts.values()):
        raise ValueError(f"unbalanced_stratified_split:{name}")
    return tuple(sorted(norm, key=lambda t: (t.task_family, t.task_id)))

def _split_digest(corpus_id: str, split: str, tasks: tuple[ModelBenchmarkTask, ...]) -> str:
    return _digest_prefixed("lego_benchmark_split", {"corpus_id": corpus_id, "split": split, "tasks": [t.to_dict() for t in tasks]})

def _parse_sha256_hex(value: str) -> str:
    cleaned = _req("prior_artifact_sha256", value).lower().removeprefix("sha256:")
    if len(cleaned) != 64 or any(ch not in "0123456789abcdef" for ch in cleaned):
        raise ValueError("invalid_prior_artifact_sha256")
    return cleaned

def _req(name: str, value: Any) -> str:
    if value is None or not str(value).strip():
        raise ValueError(f"missing_{name}")
    return str(value).strip()

def _tok(value: str) -> str: return value.strip().lower().replace(" ", "_")

def _int_bound(name: str, value: Any, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"invalid_{name}")
    return value

def _opt_float(name: str, value: Any, *, max_val: float | None = None) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) < 0.0:
        raise ValueError(f"invalid_{name}")
    if max_val is not None and float(value) > max_val:
        raise ValueError(f"invalid_{name}")
    return float(value)

def _unit_rate(name: str, value: Any) -> float:
    if value is None:
        raise ValueError(f"invalid_{name}")
    return _opt_float(name, value, max_val=1.0)  # type: ignore[return-value]

def _digest_prefixed(prefix: str, payload: Mapping[str, Any]) -> str:
    return f"{prefix}:{hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str).encode('utf-8')).hexdigest()}"
