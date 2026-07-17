"""Bounded AutoResearch campaign execution for model intelligence.

This module consumes a verified ``ModelAutoResearchPlanReceipt`` and executes
the selected benchmark candidates through injected runner/verifier seams. It
does not import provider SDKs, execute commands, promote models, mutate
catalogs, write PatternMemory, re-index HoloIndex, or bind runtime defaults.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .model_champion_challenger_autoresearch import (
    ModelAutoResearchAction,
    ModelAutoResearchPlanReceipt,
    rehydrate_model_autoresearch_plan_receipt,
)
from .model_combination_benchmark_harness import (
    BenchmarkRunner,
    BenchmarkVerifier,
    ModelBenchmarkCandidate,
    ModelBenchmarkRoleAssignment,
    ModelBenchmarkTask,
    ModelCombinationBenchmarkRunReceipt,
    build_model_benchmark_candidate,
    run_model_combination_benchmark,
)


MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ACCEPT = "MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ACCEPT"
MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_REJECT = "MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_REJECT"
MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_SCHEMA_VERSION = "model_autoresearch_campaign_execution.v1"


class ModelAutoResearchCampaignExecutionReason:
    PLAN_INVALID = "model_autoresearch_execution_plan_invalid"
    CANDIDATE_POOL_INVALID = "model_autoresearch_execution_candidate_pool_invalid"
    CANDIDATE_POOL_DIGEST_MISMATCH = "model_autoresearch_execution_candidate_pool_digest_mismatch"
    TASKS_INVALID = "model_autoresearch_execution_tasks_invalid"
    VERIFIER_DIGEST_MISMATCH = "model_autoresearch_execution_verifier_digest_mismatch"
    NO_EXECUTABLE_CAMPAIGN_ITEMS = "model_autoresearch_execution_no_executable_campaign_items"
    CAMPAIGN_CANDIDATE_MISSING = "model_autoresearch_execution_campaign_candidate_missing"
    CAMPAIGN_VERIFIER_REQUIRED = "model_autoresearch_execution_campaign_verifier_required"
    OUTPUT_PATH_INVALID = "model_autoresearch_execution_output_path_invalid"
    OUTPUT_WRITE_FAILED = "model_autoresearch_execution_output_write_failed"
    BENCHMARK_RUN_FAILED = "model_autoresearch_execution_benchmark_run_failed"


@dataclass(frozen=True)
class ModelAutoResearchCampaignExecutionReceipt:
    receipt_id: str
    source_plan_receipt_id: str
    benchmark_run_receipt: ModelCombinationBenchmarkRunReceipt
    executed_candidate_ids: tuple[str, ...]
    skipped_campaign_candidate_ids: tuple[str, ...]
    schema_version: str = MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "source_plan_receipt_id": self.source_plan_receipt_id,
            "benchmark_run_receipt": self.benchmark_run_receipt.to_dict(),
            "executed_candidate_ids": list(self.executed_candidate_ids),
            "skipped_campaign_candidate_ids": list(self.skipped_campaign_candidate_ids),
        }


@dataclass(frozen=True)
class ModelAutoResearchCampaignExecutionResult:
    accepted: bool
    status: str
    execution_receipt_id: str | None
    source_plan_receipt_id: str | None
    benchmark_run_receipt_id: str | None
    output_path: str | None
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_model_autoresearch_campaign_execution(
    *,
    repo_root: Path | str,
    plan_receipt: Mapping[str, Any] | ModelAutoResearchPlanReceipt,
    candidate_pool: Sequence[Mapping[str, Any] | ModelBenchmarkCandidate],
    tasks: Sequence[Mapping[str, Any] | ModelBenchmarkTask],
    runner: BenchmarkRunner,
    verifier: BenchmarkVerifier,
    verifier_digest: str,
    held_out_split_id: str,
    output_path: Path | str | None,
) -> ModelAutoResearchCampaignExecutionResult:
    """Execute one verified AutoResearch benchmark campaign with injected seams."""

    root = Path(repo_root).resolve()
    reasons: list[str] = []
    try:
        plan = _plan(plan_receipt)
    except Exception:
        plan = None
        reasons.append(ModelAutoResearchCampaignExecutionReason.PLAN_INVALID)
    try:
        candidates = _candidate_pool(candidate_pool)
    except Exception:
        candidates = ()
        reasons.append(ModelAutoResearchCampaignExecutionReason.CANDIDATE_POOL_INVALID)
    try:
        normalized_tasks = _tasks(tasks)
    except Exception:
        normalized_tasks = ()
        reasons.append(ModelAutoResearchCampaignExecutionReason.TASKS_INVALID)
    output, output_reasons = _runtime_output_path(
        output_path,
        root,
        ModelAutoResearchCampaignExecutionReason.OUTPUT_PATH_INVALID,
    )
    reasons.extend(output_reasons)

    selected_candidates: tuple[ModelBenchmarkCandidate, ...] = ()
    skipped_candidate_ids: tuple[str, ...] = ()
    if plan is not None and candidates:
        candidate_digest = _candidate_pool_digest(candidates)
        if candidate_digest != plan.candidate_pool_digest:
            reasons.append(ModelAutoResearchCampaignExecutionReason.CANDIDATE_POOL_DIGEST_MISMATCH)
        selected_candidates, skipped_candidate_ids, selection_reasons = _select_campaign_candidates(plan, candidates)
        reasons.extend(selection_reasons)
    if plan is not None:
        required_verifier = plan.policy.required_verifier_digest
        if required_verifier and required_verifier != str(verifier_digest or "").strip():
            reasons.append(ModelAutoResearchCampaignExecutionReason.VERIFIER_DIGEST_MISMATCH)

    deduped = _dedupe(reasons)
    if deduped:
        return _reject(deduped)

    assert plan is not None
    assert output is not None
    try:
        benchmark = run_model_combination_benchmark(
            tasks=normalized_tasks,
            candidates=selected_candidates,
            runner=runner,
            verifier=verifier,
            verifier_digest=verifier_digest,
            held_out_split_id=held_out_split_id,
        )
    except Exception:
        return _reject((ModelAutoResearchCampaignExecutionReason.BENCHMARK_RUN_FAILED,))
    receipt = _execution_receipt(
        plan=plan,
        benchmark=benchmark,
        executed_candidate_ids=tuple(candidate.candidate_id for candidate in selected_candidates),
        skipped_campaign_candidate_ids=skipped_candidate_ids,
    )
    try:
        _write_json_atomic(output, receipt.to_dict())
    except Exception:
        return _reject((ModelAutoResearchCampaignExecutionReason.OUTPUT_WRITE_FAILED,))
    return ModelAutoResearchCampaignExecutionResult(
        accepted=True,
        status=MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ACCEPT,
        execution_receipt_id=receipt.receipt_id,
        source_plan_receipt_id=plan.receipt_id,
        benchmark_run_receipt_id=benchmark.receipt_id,
        output_path=str(output),
        executed_candidate_ids=receipt.executed_candidate_ids,
        task_count=len(normalized_tasks),
        rejection_reasons=(),
    )


def _plan(value: Mapping[str, Any] | ModelAutoResearchPlanReceipt) -> ModelAutoResearchPlanReceipt:
    if isinstance(value, ModelAutoResearchPlanReceipt):
        return value
    if isinstance(value, Mapping):
        return rehydrate_model_autoresearch_plan_receipt(value)
    raise ValueError("invalid_plan")


def _candidate_pool(
    values: Sequence[Mapping[str, Any] | ModelBenchmarkCandidate],
) -> tuple[ModelBenchmarkCandidate, ...]:
    candidates: list[ModelBenchmarkCandidate] = []
    for value in values:
        if isinstance(value, ModelBenchmarkCandidate):
            candidates.append(value)
        elif isinstance(value, Mapping):
            candidates.append(_candidate(value))
        else:
            raise ValueError("invalid_candidate")
    if not candidates:
        raise ValueError("missing_candidate_pool")
    candidate_ids = [candidate.candidate_id for candidate in candidates]
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("duplicate_candidates")
    return tuple(sorted(candidates, key=lambda candidate: candidate.candidate_id))


def _candidate(value: Mapping[str, Any]) -> ModelBenchmarkCandidate:
    if value.get("schema_version") != "model_benchmark_candidate.v1":
        raise ValueError("invalid_candidate_schema")
    role_values = value.get("role_assignments")
    if not isinstance(role_values, list) or not role_values:
        raise ValueError("missing_candidate_roles")
    roles: list[ModelBenchmarkRoleAssignment] = []
    for item in role_values:
        if not isinstance(item, Mapping):
            raise ValueError("invalid_candidate_role")
        roles.append(
            ModelBenchmarkRoleAssignment(
                role=_required(item.get("role"), "role"),
                model_id=_required(item.get("model_id"), "model_id"),
                provider=_required(item.get("provider"), "provider"),
            )
        )
    candidate = build_model_benchmark_candidate(roles)
    if candidate.candidate_id != _required(value.get("candidate_id"), "candidate_id"):
        raise ValueError("candidate_id_mismatch")
    if candidate.topology_digest != _required(value.get("topology_digest"), "topology_digest"):
        raise ValueError("candidate_topology_digest_mismatch")
    return candidate


def _tasks(values: Sequence[Mapping[str, Any] | ModelBenchmarkTask]) -> tuple[ModelBenchmarkTask, ...]:
    tasks: list[ModelBenchmarkTask] = []
    for value in values:
        if isinstance(value, ModelBenchmarkTask):
            tasks.append(value.normalized())
        elif isinstance(value, Mapping):
            tasks.append(
                ModelBenchmarkTask(
                    task_id=_required(value.get("task_id"), "task_id"),
                    task_family=_required(value.get("task_family"), "task_family"),
                    prompt_digest=_required(value.get("prompt_digest"), "prompt_digest"),
                    expected_output_digest=_required(value.get("expected_output_digest"), "expected_output_digest"),
                    verifier_contract_digest=_required(value.get("verifier_contract_digest"), "verifier_contract_digest"),
                    metadata=_metadata(value.get("metadata")),
                ).normalized()
            )
        else:
            raise ValueError("invalid_task")
    if not tasks:
        raise ValueError("missing_tasks")
    return tuple(tasks)


def _metadata(value: Any) -> Mapping[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("invalid_task_metadata")
    return {str(key): str(item) for key, item in value.items()}


def _select_campaign_candidates(
    plan: ModelAutoResearchPlanReceipt,
    candidates: tuple[ModelBenchmarkCandidate, ...],
) -> tuple[tuple[ModelBenchmarkCandidate, ...], tuple[str, ...], tuple[str, ...]]:
    by_id = {candidate.candidate_id: candidate for candidate in candidates}
    selected: list[ModelBenchmarkCandidate] = []
    skipped: list[str] = []
    reasons: list[str] = []
    for item in plan.campaign_items:
        if item.action == ModelAutoResearchAction.STOP:
            skipped.append(item.candidate_id)
            continue
        if not item.requires_independent_verifier:
            reasons.append(ModelAutoResearchCampaignExecutionReason.CAMPAIGN_VERIFIER_REQUIRED)
            continue
        candidate = by_id.get(item.candidate_id)
        if candidate is None:
            reasons.append(ModelAutoResearchCampaignExecutionReason.CAMPAIGN_CANDIDATE_MISSING)
            continue
        selected.append(candidate)
    if not selected:
        reasons.append(ModelAutoResearchCampaignExecutionReason.NO_EXECUTABLE_CAMPAIGN_ITEMS)
    return tuple(selected), tuple(skipped), _dedupe(reasons)


def _candidate_pool_digest(candidates: Sequence[ModelBenchmarkCandidate]) -> str:
    return _digest_prefixed(
        "model_autoresearch_candidate_pool",
        {"candidates": [candidate.to_dict() for candidate in sorted(candidates, key=lambda item: item.candidate_id)]},
    )


def _execution_receipt(
    *,
    plan: ModelAutoResearchPlanReceipt,
    benchmark: ModelCombinationBenchmarkRunReceipt,
    executed_candidate_ids: tuple[str, ...],
    skipped_campaign_candidate_ids: tuple[str, ...],
) -> ModelAutoResearchCampaignExecutionReceipt:
    body = {
        "schema_version": MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_SCHEMA_VERSION,
        "source_plan_receipt_id": plan.receipt_id,
        "benchmark_run_receipt_id": benchmark.receipt_id,
        "executed_candidate_ids": list(executed_candidate_ids),
        "skipped_campaign_candidate_ids": list(skipped_campaign_candidate_ids),
        "benchmark_evidence_receipt_ids": [
            receipt.receipt_id for receipt in benchmark.benchmark_evidence_receipts
        ],
    }
    return ModelAutoResearchCampaignExecutionReceipt(
        receipt_id=_digest_prefixed("model_autoresearch_campaign_execution", body),
        source_plan_receipt_id=plan.receipt_id,
        benchmark_run_receipt=benchmark,
        executed_candidate_ids=executed_candidate_ids,
        skipped_campaign_candidate_ids=skipped_campaign_candidate_ids,
    )


def _runtime_output_path(
    value: Path | str | None,
    repo_root: Path,
    reason: str,
) -> tuple[Path | None, list[str]]:
    if not value:
        return None, [reason]
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    resolved = path.resolve()
    try:
        resolved.relative_to(repo_root)
        return None, [reason]
    except ValueError:
        pass
    return resolved, []


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, sort_keys=True, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _required(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(name + "_missing")
    return text


def _digest_prefixed(prefix: str, value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value).strip()))


def _reject(reasons: Sequence[str]) -> ModelAutoResearchCampaignExecutionResult:
    return ModelAutoResearchCampaignExecutionResult(
        accepted=False,
        status=MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_REJECT,
        execution_receipt_id=None,
        source_plan_receipt_id=None,
        benchmark_run_receipt_id=None,
        output_path=None,
        executed_candidate_ids=(),
        task_count=0,
        rejection_reasons=_dedupe(reasons),
    )


__all__ = [
    "MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ACCEPT",
    "MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_REJECT",
    "MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_SCHEMA_VERSION",
    "ModelAutoResearchCampaignExecutionReason",
    "ModelAutoResearchCampaignExecutionReceipt",
    "ModelAutoResearchCampaignExecutionResult",
    "run_reddog_model_autoresearch_campaign_execution",
]
