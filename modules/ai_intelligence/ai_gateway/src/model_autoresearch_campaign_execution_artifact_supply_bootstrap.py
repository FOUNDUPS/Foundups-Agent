"""Main-startup bootstrap for model AutoResearch campaign execution artifacts.

Slice: REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1

This adapter reads outside-repo runtime JSON inputs and materializes a
``ModelAutoResearchCampaignExecutionReceipt`` using the bounded campaign
executor and deterministic fixture seams.

It does not call provider SDKs, execute commands, promote models, mutate
catalogs, write PatternMemory, re-index HoloIndex, bind runtime defaults, spawn
workers, or write inside the repository.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

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


@dataclass(frozen=True)
class ModelAutoResearchCampaignExecutionBootstrapResult:
    accepted: bool
    status: str
    execution_receipt_id: Optional[str]
    source_plan_receipt_id: Optional[str]
    benchmark_run_receipt_id: Optional[str]
    output_path: Optional[str]
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
) -> ModelAutoResearchCampaignExecutionBootstrapResult:
    """Materialize an AutoResearch campaign execution artifact from runtime files."""

    root = Path(repo_root).resolve()
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
    reasons = [
        *plan_reasons,
        *candidate_reasons,
        *task_reasons,
        *_output_path_reasons(root, output_path),
        *_mode_reasons(runner_mode, verifier_mode),
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
    if reasons:
        return _not_ready(reasons)

    assert isinstance(plan_payload, Mapping)
    assert candidate_pool is not None
    assert tasks is not None
    execution = run_reddog_model_autoresearch_campaign_execution(
        repo_root=root,
        plan_receipt=plan_payload,
        candidate_pool=candidate_pool,
        tasks=tasks,
        runner=_fixture_runner,
        verifier=_fixture_verifier,
        verifier_digest=verifier_text,
        held_out_split_id=held_out_text,
        output_path=output_path,
    )
    if not execution.accepted or execution.status != MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ACCEPT:
        return _not_ready(
            execution.rejection_reasons or ("model_autoresearch_campaign_execution_rejected",)
        )
    return ModelAutoResearchCampaignExecutionBootstrapResult(
        accepted=True,
        status=MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_APPLIED,
        execution_receipt_id=execution.execution_receipt_id,
        source_plan_receipt_id=execution.source_plan_receipt_id,
        benchmark_run_receipt_id=execution.benchmark_run_receipt_id,
        output_path=execution.output_path,
        executed_candidate_ids=execution.executed_candidate_ids,
        task_count=execution.task_count,
        rejection_reasons=(),
    )


def _fixture_runner(
    task: ModelBenchmarkTask,
    candidate: ModelBenchmarkCandidate,
) -> ModelBenchmarkTaskOutput:
    output_digest = _digest(
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
        runner_receipt_id=_digest(
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
    expected = _digest(
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
        verifier_receipt_id=_digest(
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
        payload = json.loads(resolved.read_text(encoding="utf-8"))
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


def _mode_reasons(runner_mode: str, verifier_mode: str) -> tuple[str, ...]:
    reasons: list[str] = []
    if str(runner_mode or "").strip() != MODEL_AUTORESEARCH_CAMPAIGN_FIXTURE_RUNNER:
        reasons.append("unsupported_model_autoresearch_campaign_runner_mode")
    if str(verifier_mode or "").strip() != MODEL_AUTORESEARCH_CAMPAIGN_FIXTURE_VERIFIER:
        reasons.append("unsupported_model_autoresearch_campaign_verifier_mode")
    return tuple(reasons)


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _digest(prefix: str, value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


def _not_ready(
    reasons: tuple[str, ...] | list[str],
) -> ModelAutoResearchCampaignExecutionBootstrapResult:
    return ModelAutoResearchCampaignExecutionBootstrapResult(
        accepted=False,
        status=MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_NOT_READY,
        execution_receipt_id=None,
        source_plan_receipt_id=None,
        benchmark_run_receipt_id=None,
        output_path=None,
        executed_candidate_ids=(),
        task_count=0,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason))),
    )


__all__ = [
    "MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_APPLIED",
    "MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_NOT_READY",
    "MODEL_AUTORESEARCH_CAMPAIGN_FIXTURE_RUNNER",
    "MODEL_AUTORESEARCH_CAMPAIGN_FIXTURE_VERIFIER",
    "ModelAutoResearchCampaignExecutionBootstrapResult",
    "run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap",
]
