"""Main-startup bootstrap for model AutoResearch campaign execution artifacts.

Slice: REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1

This adapter reads outside-repo runtime JSON inputs and materializes a
``ModelAutoResearchCampaignExecutionReceipt`` using the bounded campaign
executor and either deterministic fixture seams or an explicitly configured
gateway runner.

It does not import provider SDKs directly, execute commands, promote models,
mutate catalogs, write PatternMemory, re-index HoloIndex, bind runtime defaults,
spawn workers, or write inside the repository. Configured gateway mode may call
the existing AIGateway provider seam only when explicitly selected.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_configured_gateway_runner import (
    ConfiguredGatewayRunnerPolicy,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_canonical_prompt_guard import (
    CANONICAL_PROMPT_GUARD_CONTRACT_DIGEST,
    CANONICAL_PROMPT_GUARD_PROFILE,
    CANONICAL_PROMPT_GUARD_PROFILE_DIGEST,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_configured_gateway_evidence import (
    ConfiguredGatewayModelBudgetEvidenceBundle,
    canonical_decimal,
    rehydrate_model_budget_evidence_bundle,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_configured_runtime import (
    configured_runner_and_verifier,
    digest_receipt,
    preflight_candidate,
    preflight_tasks,
    prepare_configured_campaign,
    runtime_path,
)
from modules.ai_intelligence.ai_gateway.src.model_champion_challenger_autoresearch import (
    ModelAutoResearchAction,
    rehydrate_model_autoresearch_plan_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution import (
    MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ACCEPT,
    run_reddog_model_autoresearch_campaign_execution,
)
from modules.ai_intelligence.ai_gateway.src.model_combination_benchmark_harness import (
    ModelBenchmarkCandidate,
    ModelBenchmarkTask,
    ModelBenchmarkTaskOutput,
    ModelBenchmarkVerifierResult,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    ModelOutcomeMetrics,
    VerifierDecision,
)


MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_APPLIED = (
    "MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_APPLIED"
)
MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_NOT_READY = (
    "MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_NOT_READY"
)
MODEL_AUTORESEARCH_CAMPAIGN_FIXTURE_RUNNER = "deterministic_fixture"
MODEL_AUTORESEARCH_CAMPAIGN_FIXTURE_VERIFIER = "deterministic_fixture"
MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER = "configured_gateway"
MODEL_AUTORESEARCH_CAMPAIGN_EXACT_OUTPUT_DIGEST_VERIFIER = "exact_output_digest"
MODEL_AUTORESEARCH_CAMPAIGN_OUTPUT_EVIDENCE_SEMANTIC_VERIFIER = "output_evidence_semantic"
MAX_RUNTIME_JSON_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True)
class ModelAutoResearchCampaignExecutionBootstrapResult:
    accepted: bool
    status: str
    execution_receipt_id: Optional[str]
    source_plan_receipt_id: Optional[str]
    benchmark_run_receipt_id: Optional[str]
    output_path: Optional[str]
    output_evidence_path: Optional[str]
    executed_candidate_ids: tuple[str, ...]
    task_count: int
    rejection_reasons: tuple[str, ...]
    no_direct_provider_call_performed: bool = True
    no_model_promotion_performed: bool = True
    no_catalog_mutation_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_runtime_binding_performed: bool = True
    no_command_execution_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_extension_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
    *,
    repo_root: Path | str,
    plan_receipt_path: Path | str | None,
    candidate_pool_path: Path | str | None,
    tasks_path: Path | str | None,
    output_path: Path | str | None,
    verifier_digest: str,
    held_out_split_id: str,
    runner_mode: str = MODEL_AUTORESEARCH_CAMPAIGN_FIXTURE_RUNNER,
    verifier_mode: str = MODEL_AUTORESEARCH_CAMPAIGN_FIXTURE_VERIFIER,
    prompt_records_path: Path | str | None = None,
    output_evidence_path: Path | str | None = None,
    runner_allowed_providers: str | Sequence[str] | None = None,
    runner_max_prompt_chars: int | str = 20000,
    runner_max_calls_per_sample: int | str = 4,
    runner_max_total_calls: int | str | None = None,
    runner_max_cost_estimate_usd_per_sample: str | None = None,
    model_budget_evidence_path: Path | str | None = None,
    call_attempt_evidence_path: Path | str | None = None,
    runner_success_receipt_path: Path | str | None = None,
    runner_prompt_guard_profile: str = CANONICAL_PROMPT_GUARD_PROFILE,
    gateway: object | None = None,
    lm_studio_backend_factory: Callable[[str], Any] | None = None,
) -> ModelAutoResearchCampaignExecutionBootstrapResult:
    """Materialize an AutoResearch campaign execution artifact from runtime files."""

    root = Path(repo_root).resolve()
    runner_mode_text = str(runner_mode or "").strip()
    verifier_mode_text = str(verifier_mode or "").strip()
    plan_payload, plan_reasons = _read_json_outside_repo(
        root,
        plan_receipt_path,
        missing_reason="missing_model_autoresearch_plan_receipt_path",
        inside_reason="model_autoresearch_plan_receipt_path_inside_repo",
        malformed_reason="malformed_model_autoresearch_plan_receipt",
    )
    candidate_payload, candidate_reasons = _read_json_outside_repo(
        root,
        candidate_pool_path,
        missing_reason="missing_model_autoresearch_campaign_candidate_pool_path",
        inside_reason="model_autoresearch_campaign_candidate_pool_path_inside_repo",
        malformed_reason="malformed_model_autoresearch_campaign_candidate_pool",
    )
    task_payload, task_reasons = _read_json_outside_repo(
        root,
        tasks_path,
        missing_reason="missing_model_autoresearch_campaign_tasks_path",
        inside_reason="model_autoresearch_campaign_tasks_path_inside_repo",
        malformed_reason="malformed_model_autoresearch_campaign_tasks",
    )
    prompt_payload: Any | None = None
    prompt_reasons: tuple[str, ...] = ()
    budget_payload: Any | None = None
    budget_reasons: tuple[str, ...] = ()
    if runner_mode_text == MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER:
        prompt_payload, prompt_reasons = _read_json_outside_repo(
            root,
            prompt_records_path,
            missing_reason="missing_model_autoresearch_campaign_prompt_records_path",
            inside_reason="model_autoresearch_campaign_prompt_records_path_inside_repo",
            malformed_reason="malformed_model_autoresearch_campaign_prompt_records",
        )
        budget_payload, budget_reasons = _read_json_outside_repo(
            root,
            model_budget_evidence_path,
            missing_reason="missing_model_autoresearch_campaign_model_budget_evidence_path",
            inside_reason="model_autoresearch_campaign_model_budget_evidence_path_inside_repo",
            malformed_reason="malformed_model_autoresearch_campaign_model_budget_evidence",
        )
    reasons = [
        *plan_reasons,
        *candidate_reasons,
        *task_reasons,
        *prompt_reasons,
        *budget_reasons,
        *_output_path_reasons(root, output_path),
        *_configured_output_evidence_path_reasons(
            root,
            output_evidence_path,
            runner_mode=runner_mode_text,
        ),
        *_configured_receipt_path_reasons(
            root,
            call_attempt_evidence_path,
            runner_mode=runner_mode_text,
            label="call_attempt_evidence",
        ),
        *_configured_receipt_path_reasons(
            root,
            runner_success_receipt_path,
            runner_mode=runner_mode_text,
            label="runner_success_receipt",
        ),
        *_configured_artifact_state_reasons(
            root,
            runner_mode=runner_mode_text,
            output_evidence_path=output_evidence_path,
            call_attempt_evidence_path=call_attempt_evidence_path,
            runner_success_receipt_path=runner_success_receipt_path,
            output_path=output_path,
            model_budget_evidence_path=model_budget_evidence_path,
            prompt_records_path=prompt_records_path,
            plan_receipt_path=plan_receipt_path,
            candidate_pool_path=candidate_pool_path,
            tasks_path=tasks_path,
        ),
        *_mode_reasons(runner_mode_text, verifier_mode_text),
    ]
    verifier_text = str(verifier_digest or "").strip()
    held_out_text = str(held_out_split_id or "").strip()
    if not verifier_text:
        reasons.append("missing_model_autoresearch_campaign_verifier_digest")
    if not held_out_text:
        reasons.append("missing_model_autoresearch_campaign_held_out_split_id")

    candidate_pool = _mapping_list(candidate_payload, "candidate_pool")
    tasks = _mapping_list(task_payload, "tasks")
    if plan_payload is not None and not isinstance(plan_payload, Mapping):
        reasons.append("malformed_model_autoresearch_plan_receipt")
    if candidate_payload is not None and candidate_pool is None:
        reasons.append("malformed_model_autoresearch_campaign_candidate_pool")
    if task_payload is not None and tasks is None:
        reasons.append("malformed_model_autoresearch_campaign_tasks")
    prompts: Mapping[str, str] | None = None
    if runner_mode_text == MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER:
        prompts = _prompt_records(prompt_payload)
        if prompts is None:
            reasons.append("malformed_model_autoresearch_campaign_prompt_records")
    budget_bundle, bundle_reasons = _configured_budget_bundle(
        runner_mode=runner_mode_text,
        payload=budget_payload,
        runner_allowed_providers=runner_allowed_providers,
    )
    reasons.extend(bundle_reasons)
    policy, policy_reasons = _configured_runner_policy(
        runner_mode=runner_mode_text,
        runner_allowed_providers=runner_allowed_providers,
        budget_bundle=budget_bundle,
        runner_max_prompt_chars=runner_max_prompt_chars,
        runner_max_calls_per_sample=runner_max_calls_per_sample,
        runner_max_total_calls=runner_max_total_calls,
        runner_max_cost_estimate_usd_per_sample=runner_max_cost_estimate_usd_per_sample,
    )
    reasons.extend(policy_reasons)
    reasons.extend(
        _configured_campaign_call_reasons(
            runner_mode=runner_mode_text,
            plan_payload=plan_payload,
            candidate_pool=candidate_pool,
            tasks=tasks,
            budget_bundle=budget_bundle,
            policy=policy,
        )
    )
    if (
        runner_mode_text == MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER
        and runner_prompt_guard_profile != CANONICAL_PROMPT_GUARD_PROFILE
    ):
        reasons.append("unsupported_model_autoresearch_campaign_prompt_guard_profile")
    if reasons:
        return _not_ready(reasons)

    assert isinstance(plan_payload, Mapping)
    assert candidate_pool is not None
    assert tasks is not None
    runner = _fixture_runner
    verifier = _fixture_verifier
    no_provider_call = True
    resolved_output_evidence_path: Optional[str] = None
    if runner_mode_text == MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER:
        assert prompts is not None
        assert policy is not None
        runner, verifier, evidence_path = configured_runner_and_verifier(
            root=root,
            prompts=prompts,
            policy=policy,
            semantic_verifier=(
                verifier_mode_text
                == MODEL_AUTORESEARCH_CAMPAIGN_OUTPUT_EVIDENCE_SEMANTIC_VERIFIER
            ),
            exact_verifier=_exact_output_digest_verifier,
            output_evidence_path=output_evidence_path,
            call_attempt_evidence_path=call_attempt_evidence_path,
            runner_success_receipt_path=runner_success_receipt_path,
            gateway=gateway,
            lm_studio_backend_factory=lm_studio_backend_factory,
        )
        resolved_output_evidence_path = str(evidence_path)
        if not prepare_configured_campaign(
            runner=runner,
            root=root,
            plan_payload=plan_payload,
            candidate_pool=candidate_pool,
            tasks=tasks,
            output_paths=(
                output_evidence_path,
                call_attempt_evidence_path,
                runner_success_receipt_path,
                output_path,
            ),
        ):
            return _not_ready(("model_autoresearch_campaign_atomic_admission_failed",))
        no_provider_call = False
    execution = run_reddog_model_autoresearch_campaign_execution(
        repo_root=root,
        plan_receipt=plan_payload,
        candidate_pool=candidate_pool,
        tasks=tasks,
        runner=runner,
        verifier=verifier,
        verifier_digest=verifier_text,
        held_out_split_id=held_out_text,
        output_path=output_path,
    )
    if not execution.accepted or execution.status != MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ACCEPT:
        return _not_ready(
            execution.rejection_reasons or ("model_autoresearch_campaign_execution_rejected",),
            no_provider_call_performed=no_provider_call,
        )
    return ModelAutoResearchCampaignExecutionBootstrapResult(
        accepted=True,
        status=MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_APPLIED,
        execution_receipt_id=execution.execution_receipt_id,
        source_plan_receipt_id=execution.source_plan_receipt_id,
        benchmark_run_receipt_id=execution.benchmark_run_receipt_id,
        output_path=execution.output_path,
        output_evidence_path=resolved_output_evidence_path,
        executed_candidate_ids=execution.executed_candidate_ids,
        task_count=execution.task_count,
        rejection_reasons=(),
        no_direct_provider_call_performed=no_provider_call,
    )


def _fixture_runner(
    task: ModelBenchmarkTask,
    candidate: ModelBenchmarkCandidate,
) -> ModelBenchmarkTaskOutput:
    output_digest = digest_receipt(
        "model_autoresearch_fixture_output",
        {
            "candidate_id": candidate.candidate_id,
            "task_id": task.task_id,
            "prompt_digest": task.prompt_digest,
            "expected_output_digest": task.expected_output_digest,
        },
    )
    return ModelBenchmarkTaskOutput(
        output_digest=output_digest,
        runner_receipt_id=digest_receipt(
            "model_autoresearch_fixture_runner",
            {"candidate_id": candidate.candidate_id, "task_id": task.task_id},
        ),
        metrics=ModelOutcomeMetrics(
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
            cost_estimate_usd=0.0,
        ),
    )


def _fixture_verifier(
    task: ModelBenchmarkTask,
    candidate: ModelBenchmarkCandidate,
    output: ModelBenchmarkTaskOutput,
) -> ModelBenchmarkVerifierResult:
    expected = digest_receipt(
        "model_autoresearch_fixture_output",
        {
            "candidate_id": candidate.candidate_id,
            "task_id": task.task_id,
            "prompt_digest": task.prompt_digest,
            "expected_output_digest": task.expected_output_digest,
        },
    )
    accepted = output.output_digest == expected
    return ModelBenchmarkVerifierResult(
        decision=VerifierDecision.ACCEPT if accepted else VerifierDecision.REJECT,
        verifier_receipt_id=digest_receipt(
            "model_autoresearch_fixture_verifier",
            {
                "candidate_id": candidate.candidate_id,
                "task_id": task.task_id,
                "output_digest": output.output_digest,
                "accepted": accepted,
            },
        ),
        evidence_correct=accepted,
    )


def _exact_output_digest_verifier(
    task: ModelBenchmarkTask,
    candidate: ModelBenchmarkCandidate,
    output: ModelBenchmarkTaskOutput,
) -> ModelBenchmarkVerifierResult:
    accepted = hmac.compare_digest(str(output.output_digest), str(task.expected_output_digest))
    return ModelBenchmarkVerifierResult(
        decision=VerifierDecision.ACCEPT if accepted else VerifierDecision.REJECT,
        verifier_receipt_id=digest_receipt(
            "model_autoresearch_exact_output_digest_verifier",
            {
                "candidate_id": candidate.candidate_id,
                "task_id": task.task_id,
                "output_digest": output.output_digest,
                "expected_output_digest": task.expected_output_digest,
                "accepted": accepted,
            },
        ),
        evidence_correct=accepted,
        rejection_reasons=() if accepted else ("output_digest_mismatch",),
    )


def _read_json_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
    malformed_reason: str,
) -> tuple[Any | None, tuple[str, ...]]:
    if not value:
        return None, (missing_reason,)
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    resolved = path.resolve()
    if _is_inside(resolved, repo_root):
        return None, (inside_reason,)
    if not resolved.exists() or not resolved.is_file():
        return None, (missing_reason,)
    try:
        size = resolved.stat().st_size
        if not 1 <= size <= MAX_RUNTIME_JSON_BYTES:
            return None, (malformed_reason,)
        raw = resolved.read_bytes()
        if len(raw) != size:
            return None, (malformed_reason,)
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        return None, (malformed_reason,)
    if not isinstance(payload, (Mapping, list)):
        return None, (malformed_reason,)
    return payload, ()


def _mapping_list(value: Any, key: str) -> tuple[Mapping[str, Any], ...] | None:
    raw = value
    if isinstance(value, Mapping):
        raw = value.get(key)
    if not isinstance(raw, list):
        return None
    records: list[Mapping[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            return None
        records.append(item)
    return tuple(records)


def _prompt_records(value: Any) -> Mapping[str, str] | None:
    if isinstance(value, Mapping) and "prompts" in value:
        raw = value.get("prompts")
    else:
        raw = value
    prompts: dict[str, str] = {}
    if isinstance(raw, Mapping):
        for task_id, prompt in raw.items():
            if not str(task_id).strip() or not isinstance(prompt, str):
                return None
            prompts[str(task_id).strip()] = prompt
        return prompts if prompts else None
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, Mapping):
                return None
            task_id = str(item.get("task_id") or "").strip()
            prompt = item.get("prompt")
            prompt_digest = str(item.get("prompt_digest") or "").strip()
            if not task_id or not isinstance(prompt, str) or not prompt_digest:
                return None
            if not hmac.compare_digest(_content_digest(prompt), prompt_digest):
                return None
            prompts[task_id] = prompt
        return prompts if prompts else None
    return None


def _output_path_reasons(repo_root: Path, value: Path | str | None) -> tuple[str, ...]:
    if not value:
        return ("model_autoresearch_campaign_execution_output_path_invalid",)
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    resolved = path.resolve()
    if _is_inside(resolved, repo_root):
        return ("model_autoresearch_campaign_execution_output_path_invalid",)
    return ()


def _configured_output_evidence_path_reasons(
    repo_root: Path,
    value: Path | str | None,
    *,
    runner_mode: str,
) -> tuple[str, ...]:
    if runner_mode != MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER:
        return ()
    if not value:
        return ("missing_model_autoresearch_campaign_output_evidence_path",)
    resolved = runtime_path(repo_root, value)
    if _is_inside(resolved, repo_root):
        return ("model_autoresearch_campaign_output_evidence_path_inside_repo",)
    return ()


def _configured_receipt_path_reasons(
    repo_root: Path,
    value: Path | str | None,
    *,
    runner_mode: str,
    label: str,
) -> tuple[str, ...]:
    if runner_mode != MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER:
        return ()
    if not value:
        return (f"missing_model_autoresearch_campaign_{label}_path",)
    if _is_inside(runtime_path(repo_root, value), repo_root):
        return (f"model_autoresearch_campaign_{label}_path_inside_repo",)
    return ()


def _configured_artifact_state_reasons(
    repo_root: Path,
    *,
    runner_mode: str,
    output_evidence_path: Path | str | None,
    call_attempt_evidence_path: Path | str | None,
    runner_success_receipt_path: Path | str | None,
    output_path: Path | str | None,
    model_budget_evidence_path: Path | str | None,
    prompt_records_path: Path | str | None,
    plan_receipt_path: Path | str | None,
    candidate_pool_path: Path | str | None,
    tasks_path: Path | str | None,
) -> tuple[str, ...]:
    if runner_mode != MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER:
        return ()
    values = (
        ("output_evidence", output_evidence_path),
        ("call_attempt_evidence", call_attempt_evidence_path),
        ("runner_success_receipt", runner_success_receipt_path),
        ("campaign_output", output_path),
        ("model_budget_evidence", model_budget_evidence_path),
        ("prompt_records", prompt_records_path),
        ("plan_receipt", plan_receipt_path),
        ("candidate_pool", candidate_pool_path),
        ("tasks", tasks_path),
    )
    paths = [_canonical_path(repo_root, value) for _, value in values if value]
    reasons: list[str] = []
    if len(paths) != len(set(paths)):
        reasons.append("model_autoresearch_campaign_artifact_path_alias")
    for label, value in values[:4]:
        if value and not _is_absent_or_empty_file(runtime_path(repo_root, value)):
            reasons.append(f"model_autoresearch_campaign_{label}_path_not_empty")
    return tuple(reasons)


def _canonical_path(repo_root: Path, value: Path | str | None) -> str:
    path = runtime_path(repo_root, value)
    return os.path.normcase(os.path.normpath(str(path)))


def _is_absent_or_empty_file(path: Path) -> bool:
    try:
        return not path.exists() or (path.is_file() and path.stat().st_size == 0)
    except OSError:
        return False


def _configured_budget_bundle(
    *,
    runner_mode: str,
    payload: Any,
    runner_allowed_providers: str | Sequence[str] | None,
) -> tuple[ConfiguredGatewayModelBudgetEvidenceBundle | None, tuple[str, ...]]:
    if runner_mode != MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER:
        return None, ()
    if not isinstance(payload, Mapping):
        return None, ()
    try:
        bundle = rehydrate_model_budget_evidence_bundle(payload)
    except ValueError as exc:
        reason = str(exc)
        if reason == "model_budget_evidence_digest_mismatch":
            return None, ("tampered_model_autoresearch_campaign_model_budget_evidence",)
        if "provider_set_mismatch" in reason:
            return None, (
                "model_autoresearch_campaign_model_budget_provider_set_mismatch",
            )
        if "assignment_route_mismatch" in reason:
            return None, ("model_autoresearch_campaign_assignment_route_mismatch",)
        return None, ("malformed_model_autoresearch_campaign_model_budget_evidence",)
    providers = _split_providers(runner_allowed_providers)
    if tuple(bundle.allowed_providers) != providers:
        return None, ("model_autoresearch_campaign_model_budget_provider_set_mismatch",)
    for budget in bundle.model_budgets:
        _provider, separator, api_model = budget.assignment_model_id.partition("/")
        if not separator or budget.api_model != api_model:
            return None, ("model_autoresearch_campaign_assignment_route_mismatch",)
    return bundle, ()


def _configured_campaign_call_reasons(
    *,
    runner_mode: str,
    plan_payload: Any,
    candidate_pool: tuple[Mapping[str, Any], ...] | None,
    tasks: tuple[Mapping[str, Any], ...] | None,
    budget_bundle: ConfiguredGatewayModelBudgetEvidenceBundle | None,
    policy: ConfiguredGatewayRunnerPolicy | None,
) -> tuple[str, ...]:
    if runner_mode != MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER:
        return ()
    facts = _configured_campaign_call_facts(plan_payload, candidate_pool, tasks)
    if facts is None or budget_bundle is None or policy is None:
        return ()
    assignments, planned_calls = facts
    admitted = {item.assignment_model_id for item in budget_bundle.model_budgets}
    reasons: list[str] = []
    if any(model_id not in admitted for model_id in assignments):
        reasons.append("model_autoresearch_campaign_assignment_not_in_model_budget")
    if planned_calls > policy.max_total_calls:
        reasons.append("model_autoresearch_campaign_total_call_budget_exceeded")
    return tuple(reasons)


def _configured_campaign_call_facts(
    plan_payload: Any,
    candidate_pool: tuple[Mapping[str, Any], ...] | None,
    tasks: tuple[Mapping[str, Any], ...] | None,
) -> tuple[tuple[str, ...], int] | None:
    if not isinstance(plan_payload, Mapping) or not candidate_pool or not tasks:
        return None
    try:
        plan = rehydrate_model_autoresearch_plan_receipt(plan_payload)
        candidates = tuple(preflight_candidate(item) for item in candidate_pool)
        task_count = _normalized_task_count(tasks)
    except (TypeError, ValueError):
        return None
    candidate_digest = digest_receipt(
        "model_autoresearch_candidate_pool",
        {
            "candidates": [
                item.to_dict()
                for item in sorted(candidates, key=lambda value: value.candidate_id)
            ]
        },
    )
    if candidate_digest != plan.candidate_pool_digest or plan.rejection_reasons:
        return None
    by_id = {item.candidate_id: item for item in candidates}
    selected = [
        by_id.get(item.candidate_id)
        for item in plan.campaign_items
        if item.action != ModelAutoResearchAction.STOP
        and item.requires_independent_verifier
    ]
    if not selected or any(item is None for item in selected):
        return None
    assignments = tuple(
        role.model_id
        for candidate in selected
        if candidate is not None
        for role in candidate.role_assignments
    )
    return assignments, len(assignments) * task_count


def _normalized_task_count(tasks: Sequence[Mapping[str, Any]]) -> int:
    normalized = preflight_tasks(tasks)
    return len(normalized)


def _mode_reasons(runner_mode: str, verifier_mode: str) -> tuple[str, ...]:
    reasons: list[str] = []
    runner = str(runner_mode or "").strip()
    verifier = str(verifier_mode or "").strip()
    valid_pairs = {
        (MODEL_AUTORESEARCH_CAMPAIGN_FIXTURE_RUNNER, MODEL_AUTORESEARCH_CAMPAIGN_FIXTURE_VERIFIER),
        (
            MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER,
            MODEL_AUTORESEARCH_CAMPAIGN_EXACT_OUTPUT_DIGEST_VERIFIER,
        ),
        (
            MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER,
            MODEL_AUTORESEARCH_CAMPAIGN_OUTPUT_EVIDENCE_SEMANTIC_VERIFIER,
        ),
    }
    if runner not in {
        MODEL_AUTORESEARCH_CAMPAIGN_FIXTURE_RUNNER,
        MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER,
    }:
        reasons.append("unsupported_model_autoresearch_campaign_runner_mode")
    if verifier not in {
        MODEL_AUTORESEARCH_CAMPAIGN_FIXTURE_VERIFIER,
        MODEL_AUTORESEARCH_CAMPAIGN_EXACT_OUTPUT_DIGEST_VERIFIER,
        MODEL_AUTORESEARCH_CAMPAIGN_OUTPUT_EVIDENCE_SEMANTIC_VERIFIER,
    }:
        reasons.append("unsupported_model_autoresearch_campaign_verifier_mode")
    if not reasons and (runner, verifier) not in valid_pairs:
        reasons.append("unsupported_model_autoresearch_campaign_runner_verifier_pair")
    return tuple(reasons)


def _configured_runner_policy(
    *,
    runner_mode: str,
    runner_allowed_providers: str | Sequence[str] | None,
    budget_bundle: ConfiguredGatewayModelBudgetEvidenceBundle | None,
    runner_max_prompt_chars: int | str,
    runner_max_calls_per_sample: int | str,
    runner_max_total_calls: int | str | None,
    runner_max_cost_estimate_usd_per_sample: str | None,
) -> tuple[ConfiguredGatewayRunnerPolicy | None, tuple[str, ...]]:
    if runner_mode != MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER:
        return None, ()
    providers = _split_providers(runner_allowed_providers)
    reasons: list[str] = []
    if not providers:
        reasons.append("missing_model_autoresearch_campaign_runner_allowed_providers")
    if budget_bundle is None:
        reasons.append("missing_model_autoresearch_campaign_model_budget_evidence")
    prompt_chars, prompt_reason = _positive_int(
        runner_max_prompt_chars,
        "invalid_model_autoresearch_campaign_runner_max_prompt_chars",
    )
    calls, calls_reason = _positive_int(
        runner_max_calls_per_sample,
        "invalid_model_autoresearch_campaign_runner_max_calls_per_sample",
    )
    total_calls, total_reason = _configured_total_calls(runner_max_total_calls)
    cost, cost_reason = _configured_cost(runner_max_cost_estimate_usd_per_sample)
    reasons.extend(
        reason
        for reason in (prompt_reason, calls_reason, total_reason, cost_reason)
        if reason
    )
    if reasons:
        return None, tuple(reasons)
    assert budget_bundle is not None
    return (
        ConfiguredGatewayRunnerPolicy(
            allowed_providers=providers,
            model_budgets=budget_bundle.model_budgets,
            max_prompt_chars=prompt_chars,
            max_calls_per_sample=calls,
            max_total_calls=total_calls,
            max_cost_estimate_usd_per_sample=cost,
            allow_panel_candidates=calls > 1,
            required_prompt_guard_contract_digest=CANONICAL_PROMPT_GUARD_CONTRACT_DIGEST,
            required_prompt_guard_profile_digest=CANONICAL_PROMPT_GUARD_PROFILE_DIGEST,
        ),
        (),
    )


def _configured_cost(value: str | None) -> tuple[str, str | None]:
    try:
        cost = canonical_decimal(
            "runner_max_cost_estimate_usd_per_sample",
            value,
        )
    except ValueError:
        return "", (
            "invalid_model_autoresearch_campaign_runner_max_cost_estimate_usd_per_sample"
        )
    return cost, None


def _split_providers(value: str | Sequence[str] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw = value.replace(";", ",").split(",")
    else:
        raw = [str(item) for item in value]
    return tuple(dict.fromkeys(item.strip() for item in raw if item.strip()))


def _positive_int(value: int | str, reason: str) -> tuple[int, str | None]:
    if type(value) is int:
        parsed = value
    elif (
        isinstance(value, str)
        and value.isascii()
        and value.isdigit()
        and not value.startswith("0")
    ):
        parsed = int(value)
    else:
        return 0, reason
    if parsed <= 0:
        return 0, reason
    return parsed, None


def _configured_total_calls(value: int | str | None) -> tuple[int, str | None]:
    if value is None:
        return 0, "missing_model_autoresearch_campaign_runner_max_total_calls"
    return _positive_int(
        value,
        "invalid_model_autoresearch_campaign_runner_max_total_calls",
    )


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _content_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _not_ready(
    reasons: tuple[str, ...] | list[str],
    *,
    no_provider_call_performed: bool = True,
) -> ModelAutoResearchCampaignExecutionBootstrapResult:
    return ModelAutoResearchCampaignExecutionBootstrapResult(
        accepted=False,
        status=MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_NOT_READY,
        execution_receipt_id=None,
        source_plan_receipt_id=None,
        benchmark_run_receipt_id=None,
        output_path=None,
        output_evidence_path=None,
        executed_candidate_ids=(),
        task_count=0,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason))),
        no_direct_provider_call_performed=no_provider_call_performed,
    )


__all__ = [
    "MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_APPLIED",
    "MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_NOT_READY",
    "MODEL_AUTORESEARCH_CAMPAIGN_CONFIGURED_GATEWAY_RUNNER",
    "MODEL_AUTORESEARCH_CAMPAIGN_EXACT_OUTPUT_DIGEST_VERIFIER",
    "MODEL_AUTORESEARCH_CAMPAIGN_FIXTURE_RUNNER",
    "MODEL_AUTORESEARCH_CAMPAIGN_FIXTURE_VERIFIER",
    "MODEL_AUTORESEARCH_CAMPAIGN_OUTPUT_EVIDENCE_SEMANTIC_VERIFIER",
    "ModelAutoResearchCampaignExecutionBootstrapResult",
    "run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap",
]
