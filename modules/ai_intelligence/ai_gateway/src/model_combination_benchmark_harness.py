"""Deterministic benchmark harness for model and panel candidates.

The harness evaluates candidate model combinations against held-out tasks using
injected runner and verifier callables. It does not call model providers,
execute commands, promote champions, write PatternMemory, or bind RedDog
runtime defaults.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Mapping, Sequence

from .model_intelligence_outcomes import (
    ModelBenchmarkEvidenceReceipt,
    ModelOutcomeMetrics,
    VerifierDecision,
    build_model_benchmark_evidence_receipt,
)
from .model_intelligence_selection import RESERVED_PANEL_ROLES
from .model_signed_evidence import rehydrate_model_benchmark_evidence_receipt


BENCHMARK_RUN_SCHEMA_VERSION = "model_combination_benchmark_run_receipt.v1"
TASK_SCHEMA_VERSION = "model_benchmark_task.v1"
CANDIDATE_SCHEMA_VERSION = "model_benchmark_candidate.v1"


@dataclass(frozen=True)
class ModelBenchmarkTask:
    """One held-out benchmark task.

    The prompt body is not stored here. The harness binds only deterministic
    digests and task metadata so benchmark receipts can be audited without
    leaking raw prompts into downstream promotion records.
    """

    task_id: str
    task_family: str
    prompt_digest: str
    expected_output_digest: str
    verifier_contract_digest: str
    metadata: Mapping[str, str] = field(default_factory=dict)
    schema_version: str = TASK_SCHEMA_VERSION

    def normalized(self) -> "ModelBenchmarkTask":
        return ModelBenchmarkTask(
            task_id=_required("task_id", self.task_id),
            task_family=_clean_token(_required("task_family", self.task_family)),
            prompt_digest=_required("prompt_digest", self.prompt_digest),
            expected_output_digest=_required("expected_output_digest", self.expected_output_digest),
            verifier_contract_digest=_required("verifier_contract_digest", self.verifier_contract_digest),
            metadata=dict(sorted((str(k), str(v)) for k, v in self.metadata.items())),
        )

    def to_dict(self) -> dict[str, Any]:
        task = self.normalized()
        return {
            "schema_version": task.schema_version,
            "task_id": task.task_id,
            "task_family": task.task_family,
            "prompt_digest": task.prompt_digest,
            "expected_output_digest": task.expected_output_digest,
            "verifier_contract_digest": task.verifier_contract_digest,
            "metadata": dict(task.metadata),
        }


@dataclass(frozen=True)
class ModelBenchmarkRoleAssignment:
    """Role assignment for a benchmark candidate."""

    role: str
    model_id: str
    provider: str

    def normalized(self) -> "ModelBenchmarkRoleAssignment":
        role = _clean_token(_required("role", self.role))
        if role in RESERVED_PANEL_ROLES:
            raise ValueError("verifier_role_reserved_for_independent_verifier")
        return ModelBenchmarkRoleAssignment(
            role=role,
            model_id=_required("model_id", self.model_id),
            provider=_clean_token(_required("provider", self.provider)),
        )


@dataclass(frozen=True)
class ModelBenchmarkCandidate:
    """Single-model or panel candidate to benchmark."""

    candidate_id: str
    role_assignments: tuple[ModelBenchmarkRoleAssignment, ...]
    topology_digest: str
    schema_version: str = CANDIDATE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "candidate_id": self.candidate_id,
            "topology_digest": self.topology_digest,
            "role_assignments": [asdict(item.normalized()) for item in self.role_assignments],
        }


@dataclass(frozen=True)
class ModelBenchmarkTaskOutput:
    """Output receipt returned by an injected candidate runner."""

    output_digest: str
    runner_receipt_id: str
    metrics: ModelOutcomeMetrics = field(default_factory=ModelOutcomeMetrics)

    def normalized(self) -> "ModelBenchmarkTaskOutput":
        return ModelBenchmarkTaskOutput(
            output_digest=_required("output_digest", self.output_digest),
            runner_receipt_id=_required("runner_receipt_id", self.runner_receipt_id),
            metrics=self.metrics.normalized(),
        )


@dataclass(frozen=True)
class ModelBenchmarkVerifierResult:
    """Independent verifier result for one candidate/task output."""

    decision: VerifierDecision
    verifier_receipt_id: str
    evidence_correct: bool
    rejection_reasons: tuple[str, ...] = ()

    def normalized(self) -> "ModelBenchmarkVerifierResult":
        return ModelBenchmarkVerifierResult(
            decision=_coerce_verifier_decision(self.decision),
            verifier_receipt_id=_required("verifier_receipt_id", self.verifier_receipt_id),
            evidence_correct=bool(self.evidence_correct),
            rejection_reasons=tuple(sorted(_clean_token(v) for v in self.rejection_reasons if str(v).strip())),
        )


@dataclass(frozen=True)
class ModelBenchmarkSampleReceipt:
    """Fail-closed result for one candidate on one held-out task."""

    task_id: str
    candidate_id: str
    decision: VerifierDecision
    accepted: bool
    output_digest: str | None = None
    runner_receipt_id: str | None = None
    verifier_receipt_id: str | None = None
    metrics: ModelOutcomeMetrics = field(default_factory=ModelOutcomeMetrics)
    rejection_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "candidate_id": self.candidate_id,
            "decision": self.decision.value,
            "accepted": self.accepted,
            "output_digest": self.output_digest,
            "runner_receipt_id": self.runner_receipt_id,
            "verifier_receipt_id": self.verifier_receipt_id,
            "metrics": asdict(self.metrics.normalized()),
            "rejection_reasons": list(self.rejection_reasons),
        }


@dataclass(frozen=True)
class ModelCombinationBenchmarkRunReceipt:
    """Digest-bound benchmark run over one held-out task set."""

    receipt_id: str
    task_family: str
    task_set_digest: str
    held_out_split_digest: str
    verifier_digest: str
    candidates: tuple[ModelBenchmarkCandidate, ...]
    samples: tuple[ModelBenchmarkSampleReceipt, ...]
    benchmark_evidence_receipts: tuple[ModelBenchmarkEvidenceReceipt, ...]
    schema_version: str = BENCHMARK_RUN_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "task_family": self.task_family,
            "task_set_digest": self.task_set_digest,
            "held_out_split_digest": self.held_out_split_digest,
            "verifier_digest": self.verifier_digest,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "samples": [sample.to_dict() for sample in self.samples],
            "benchmark_evidence_receipts": [
                receipt.to_dict() for receipt in self.benchmark_evidence_receipts
            ],
        }


BenchmarkRunner = Callable[[ModelBenchmarkTask, ModelBenchmarkCandidate], ModelBenchmarkTaskOutput]
BenchmarkVerifier = Callable[
    [ModelBenchmarkTask, ModelBenchmarkCandidate, ModelBenchmarkTaskOutput],
    ModelBenchmarkVerifierResult,
]


def build_model_benchmark_candidate(
    role_assignments: Sequence[ModelBenchmarkRoleAssignment],
) -> ModelBenchmarkCandidate:
    """Build a deterministic single-model or panel benchmark candidate."""

    normalized = tuple(item.normalized() for item in role_assignments)
    if not normalized:
        raise ValueError("missing_role_assignments")
    roles = [item.role for item in normalized]
    if len(set(roles)) != len(roles):
        raise ValueError("duplicate_candidate_roles")
    body = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "role_assignments": [asdict(item) for item in normalized],
    }
    topology_digest = _digest_prefixed("model_panel_topology", body)
    if len(normalized) == 1 and normalized[0].role == "principal":
        candidate_id = normalized[0].model_id
    else:
        candidate_id = _digest_prefixed("model_panel_candidate", body)
    return ModelBenchmarkCandidate(
        candidate_id=candidate_id,
        role_assignments=normalized,
        topology_digest=topology_digest,
    )


def run_model_combination_benchmark(
    *,
    tasks: Sequence[ModelBenchmarkTask],
    candidates: Sequence[ModelBenchmarkCandidate],
    runner: BenchmarkRunner,
    verifier: BenchmarkVerifier,
    verifier_digest: str,
    held_out_split_id: str,
) -> ModelCombinationBenchmarkRunReceipt:
    """Run a deterministic benchmark over injected runner/verifier seams."""

    normalized_tasks = _normalize_tasks(tasks)
    normalized_candidates = _normalize_candidates(candidates)
    verifier_digest_value = _required("verifier_digest", verifier_digest)
    held_out_split_digest = _digest_prefixed(
        "held_out_split",
        {
            "held_out_split_id": _required("held_out_split_id", held_out_split_id),
            "task_ids": [task.task_id for task in normalized_tasks],
            "prompt_digests": [task.prompt_digest for task in normalized_tasks],
        },
    )
    task_set_digest = _digest_prefixed(
        "model_benchmark_task_set",
        {"tasks": [task.to_dict() for task in normalized_tasks]},
    )
    task_family = normalized_tasks[0].task_family
    samples: list[ModelBenchmarkSampleReceipt] = []
    benchmark_receipts: list[ModelBenchmarkEvidenceReceipt] = []
    for candidate in normalized_candidates:
        candidate_samples = [
            _run_one_sample(
                task=task,
                candidate=candidate,
                runner=runner,
                verifier=verifier,
            )
            for task in normalized_tasks
        ]
        samples.extend(candidate_samples)
        benchmark_receipts.append(
            build_model_benchmark_evidence_receipt(
                model_id=candidate.candidate_id,
                task_family=task_family,
                task_set_digest=task_set_digest,
                held_out_split_digest=held_out_split_digest,
                prompt_topology_digest=candidate.topology_digest,
                verifier_digest=verifier_digest_value,
                verifier_receipt_id=_digest_prefixed(
                    "model_combination_verifier_receipts",
                    {
                        "candidate_id": candidate.candidate_id,
                        "verifier_receipt_ids": [
                            sample.verifier_receipt_id
                            for sample in candidate_samples
                            if sample.verifier_receipt_id
                        ],
                    },
                ),
                sample_count=len(candidate_samples),
                accepted_count=sum(1 for sample in candidate_samples if sample.accepted),
                metrics=_aggregate_metrics(tuple(sample.metrics for sample in candidate_samples)),
            )
        )
    body = _benchmark_run_digest_body(
        task_family=task_family,
        task_set_digest=task_set_digest,
        held_out_split_digest=held_out_split_digest,
        verifier_digest=verifier_digest_value,
        candidates=normalized_candidates,
        samples=tuple(samples),
        benchmark_evidence_receipts=tuple(benchmark_receipts),
    )
    return ModelCombinationBenchmarkRunReceipt(
        receipt_id=_digest_prefixed("model_combination_benchmark_run", body),
        task_family=task_family,
        task_set_digest=task_set_digest,
        held_out_split_digest=held_out_split_digest,
        verifier_digest=verifier_digest_value,
        candidates=normalized_candidates,
        samples=tuple(samples),
        benchmark_evidence_receipts=tuple(benchmark_receipts),
    )


def rehydrate_model_combination_benchmark_run_receipt(
    payload: Mapping[str, Any],
) -> ModelCombinationBenchmarkRunReceipt:
    """Rehydrate a serialized benchmark run and verify its digest and evidence."""

    if not isinstance(payload, Mapping):
        raise ValueError("invalid_benchmark_run_receipt")
    if payload.get("schema_version") != BENCHMARK_RUN_SCHEMA_VERSION:
        raise ValueError("invalid_benchmark_run_schema")
    receipt_id = _required("receipt_id", payload.get("receipt_id"))
    task_family = _clean_token(_required("task_family", payload.get("task_family")))
    task_set_digest = _required("task_set_digest", payload.get("task_set_digest"))
    held_out_split_digest = _required("held_out_split_digest", payload.get("held_out_split_digest"))
    verifier_digest = _required("verifier_digest", payload.get("verifier_digest"))
    candidates = _rehydrate_candidates(payload.get("candidates"))
    samples = _rehydrate_samples(payload.get("samples"))
    benchmark_receipts = _rehydrate_benchmark_evidence_receipts(
        payload.get("benchmark_evidence_receipts")
    )
    _validate_benchmark_run_consistency(
        task_family=task_family,
        task_set_digest=task_set_digest,
        held_out_split_digest=held_out_split_digest,
        verifier_digest=verifier_digest,
        candidates=candidates,
        samples=samples,
        benchmark_evidence_receipts=benchmark_receipts,
    )
    body = _benchmark_run_digest_body(
        task_family=task_family,
        task_set_digest=task_set_digest,
        held_out_split_digest=held_out_split_digest,
        verifier_digest=verifier_digest,
        candidates=candidates,
        samples=samples,
        benchmark_evidence_receipts=benchmark_receipts,
    )
    expected = _digest_prefixed("model_combination_benchmark_run", body)
    if not hmac.compare_digest(receipt_id, expected):
        raise ValueError("model_combination_benchmark_run_receipt_id_mismatch")
    return ModelCombinationBenchmarkRunReceipt(
        receipt_id=receipt_id,
        task_family=task_family,
        task_set_digest=task_set_digest,
        held_out_split_digest=held_out_split_digest,
        verifier_digest=verifier_digest,
        candidates=candidates,
        samples=samples,
        benchmark_evidence_receipts=benchmark_receipts,
    )


def _benchmark_run_digest_body(
    *,
    task_family: str,
    task_set_digest: str,
    held_out_split_digest: str,
    verifier_digest: str,
    candidates: Sequence[ModelBenchmarkCandidate],
    samples: Sequence[ModelBenchmarkSampleReceipt],
    benchmark_evidence_receipts: Sequence[ModelBenchmarkEvidenceReceipt],
) -> dict[str, Any]:
    return {
        "schema_version": BENCHMARK_RUN_SCHEMA_VERSION,
        "task_family": task_family,
        "task_set_digest": task_set_digest,
        "held_out_split_digest": held_out_split_digest,
        "verifier_digest": verifier_digest,
        "candidates": [candidate.to_dict() for candidate in candidates],
        "samples": [sample.to_dict() for sample in samples],
        "benchmark_evidence_receipt_ids": [
            receipt.receipt_id for receipt in benchmark_evidence_receipts
        ],
    }


def _rehydrate_candidates(value: Any) -> tuple[ModelBenchmarkCandidate, ...]:
    raw = _required_list("candidates", value)
    candidates: list[ModelBenchmarkCandidate] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise ValueError("invalid_benchmark_candidate")
        if item.get("schema_version") != CANDIDATE_SCHEMA_VERSION:
            raise ValueError("invalid_benchmark_candidate_schema")
        role_values = _required_list("candidate_role_assignments", item.get("role_assignments"))
        roles: list[ModelBenchmarkRoleAssignment] = []
        for role_item in role_values:
            if not isinstance(role_item, Mapping):
                raise ValueError("invalid_benchmark_candidate_role")
            roles.append(
                ModelBenchmarkRoleAssignment(
                    role=_required("role", role_item.get("role")),
                    model_id=_required("model_id", role_item.get("model_id")),
                    provider=_required("provider", role_item.get("provider")),
                )
            )
        candidate = build_model_benchmark_candidate(roles)
        if candidate.candidate_id != _required("candidate_id", item.get("candidate_id")):
            raise ValueError("benchmark_candidate_id_mismatch")
        if candidate.topology_digest != _required("topology_digest", item.get("topology_digest")):
            raise ValueError("benchmark_candidate_topology_digest_mismatch")
        candidates.append(candidate)
    return _normalize_candidates(candidates)


def _rehydrate_samples(value: Any) -> tuple[ModelBenchmarkSampleReceipt, ...]:
    raw = _required_list("samples", value)
    samples: list[ModelBenchmarkSampleReceipt] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise ValueError("invalid_benchmark_sample")
        samples.append(
            ModelBenchmarkSampleReceipt(
                task_id=_required("task_id", item.get("task_id")),
                candidate_id=_required("candidate_id", item.get("candidate_id")),
                decision=_coerce_verifier_decision(_required("decision", item.get("decision"))),
                accepted=_required_bool("accepted", item.get("accepted")),
                output_digest=_optional(item.get("output_digest")),
                runner_receipt_id=_optional(item.get("runner_receipt_id")),
                verifier_receipt_id=_optional(item.get("verifier_receipt_id")),
                metrics=_rehydrate_metrics(item.get("metrics")),
                rejection_reasons=tuple(
                    sorted(_clean_token(reason) for reason in _required_list("rejection_reasons", item.get("rejection_reasons")))
                ),
            )
        )
    return tuple(sorted(samples, key=lambda sample: (sample.candidate_id, sample.task_id)))


def _rehydrate_metrics(value: Any) -> ModelOutcomeMetrics:
    if not isinstance(value, Mapping):
        raise ValueError("invalid_benchmark_sample_metrics")
    return ModelOutcomeMetrics(
        latency_ms=_optional_int(value.get("latency_ms")),
        input_tokens=_optional_int(value.get("input_tokens")),
        output_tokens=_optional_int(value.get("output_tokens")),
        cost_estimate_usd=_optional_float(value.get("cost_estimate_usd")),
    ).normalized()


def _rehydrate_benchmark_evidence_receipts(value: Any) -> tuple[ModelBenchmarkEvidenceReceipt, ...]:
    raw = _required_list("benchmark_evidence_receipts", value)
    receipts = tuple(
        rehydrate_model_benchmark_evidence_receipt(item)
        for item in raw
        if isinstance(item, Mapping)
    )
    if len(receipts) != len(raw):
        raise ValueError("invalid_benchmark_evidence_receipt")
    receipt_ids = [receipt.receipt_id for receipt in receipts]
    if len(set(receipt_ids)) != len(receipt_ids):
        raise ValueError("duplicate_benchmark_evidence_receipts")
    return tuple(sorted(receipts, key=lambda receipt: receipt.receipt_id))


def _validate_benchmark_run_consistency(
    *,
    task_family: str,
    task_set_digest: str,
    held_out_split_digest: str,
    verifier_digest: str,
    candidates: tuple[ModelBenchmarkCandidate, ...],
    samples: tuple[ModelBenchmarkSampleReceipt, ...],
    benchmark_evidence_receipts: tuple[ModelBenchmarkEvidenceReceipt, ...],
) -> None:
    candidate_ids = {candidate.candidate_id for candidate in candidates}
    sample_candidate_ids = {sample.candidate_id for sample in samples}
    evidence_model_ids = {receipt.model_id for receipt in benchmark_evidence_receipts}
    if not sample_candidate_ids.issubset(candidate_ids):
        raise ValueError("benchmark_sample_candidate_mismatch")
    if evidence_model_ids != candidate_ids:
        raise ValueError("benchmark_evidence_candidate_mismatch")
    for receipt in benchmark_evidence_receipts:
        if receipt.task_family != task_family:
            raise ValueError("benchmark_evidence_task_family_mismatch")
        if receipt.task_set_digest != task_set_digest:
            raise ValueError("benchmark_evidence_task_set_digest_mismatch")
        if receipt.held_out_split_digest != held_out_split_digest:
            raise ValueError("benchmark_evidence_held_out_split_digest_mismatch")
        if receipt.verifier_digest != verifier_digest:
            raise ValueError("benchmark_evidence_verifier_digest_mismatch")
        candidate_samples = [sample for sample in samples if sample.candidate_id == receipt.model_id]
        if receipt.sample_count != len(candidate_samples):
            raise ValueError("benchmark_evidence_sample_count_mismatch")
        if receipt.accepted_count != sum(1 for sample in candidate_samples if sample.accepted):
            raise ValueError("benchmark_evidence_accepted_count_mismatch")


def _run_one_sample(
    *,
    task: ModelBenchmarkTask,
    candidate: ModelBenchmarkCandidate,
    runner: BenchmarkRunner,
    verifier: BenchmarkVerifier,
) -> ModelBenchmarkSampleReceipt:
    try:
        output = runner(task, candidate).normalized()
    except Exception:
        return ModelBenchmarkSampleReceipt(
            task_id=task.task_id,
            candidate_id=candidate.candidate_id,
            decision=VerifierDecision.ERROR,
            accepted=False,
            rejection_reasons=("runner_error",),
        )
    try:
        verifier_result = verifier(task, candidate, output).normalized()
    except Exception:
        return ModelBenchmarkSampleReceipt(
            task_id=task.task_id,
            candidate_id=candidate.candidate_id,
            decision=VerifierDecision.ERROR,
            accepted=False,
            output_digest=output.output_digest,
            runner_receipt_id=output.runner_receipt_id,
            metrics=output.metrics,
            rejection_reasons=("verifier_error",),
        )
    accepted = verifier_result.decision == VerifierDecision.ACCEPT and verifier_result.evidence_correct
    rejection_reasons = list(verifier_result.rejection_reasons)
    if verifier_result.decision != VerifierDecision.ACCEPT:
        rejection_reasons.append("verifier_not_accept")
    if not verifier_result.evidence_correct:
        rejection_reasons.append("evidence_not_verified")
    return ModelBenchmarkSampleReceipt(
        task_id=task.task_id,
        candidate_id=candidate.candidate_id,
        decision=verifier_result.decision,
        accepted=accepted,
        output_digest=output.output_digest,
        runner_receipt_id=output.runner_receipt_id,
        verifier_receipt_id=verifier_result.verifier_receipt_id,
        metrics=output.metrics,
        rejection_reasons=tuple(sorted(set(rejection_reasons))),
    )


def _normalize_tasks(tasks: Sequence[ModelBenchmarkTask]) -> tuple[ModelBenchmarkTask, ...]:
    normalized = tuple(task.normalized() for task in tasks)
    if not normalized:
        raise ValueError("missing_benchmark_tasks")
    task_ids = [task.task_id for task in normalized]
    if len(set(task_ids)) != len(task_ids):
        raise ValueError("duplicate_benchmark_task_ids")
    task_families = {task.task_family for task in normalized}
    if len(task_families) != 1:
        raise ValueError("mixed_task_families")
    return tuple(sorted(normalized, key=lambda task: task.task_id))


def _normalize_candidates(candidates: Sequence[ModelBenchmarkCandidate]) -> tuple[ModelBenchmarkCandidate, ...]:
    normalized = tuple(candidates)
    if not normalized:
        raise ValueError("missing_benchmark_candidates")
    candidate_ids = [candidate.candidate_id for candidate in normalized]
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("duplicate_benchmark_candidate_ids")
    return tuple(sorted(normalized, key=lambda candidate: candidate.candidate_id))


def _aggregate_metrics(metrics: tuple[ModelOutcomeMetrics, ...]) -> ModelOutcomeMetrics:
    if not metrics:
        return ModelOutcomeMetrics()
    normalized = tuple(item.normalized() for item in metrics)
    return ModelOutcomeMetrics(
        latency_ms=_mean_int(item.latency_ms for item in normalized),
        input_tokens=_sum_int(item.input_tokens for item in normalized),
        output_tokens=_sum_int(item.output_tokens for item in normalized),
        cost_estimate_usd=_sum_float(item.cost_estimate_usd for item in normalized),
    )


def _mean_int(values: Sequence[int | None]) -> int | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return round(sum(present) / len(present))


def _sum_int(values: Sequence[int | None]) -> int | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present)


def _sum_float(values: Sequence[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return round(sum(present), 8)


def _coerce_verifier_decision(value: VerifierDecision | str) -> VerifierDecision:
    if isinstance(value, VerifierDecision):
        return value
    try:
        return VerifierDecision(str(value).strip().lower())
    except ValueError as exc:
        raise ValueError("invalid_verifier_decision") from exc


def _required(name: str, value: Any) -> str:
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"missing_{name}")
    return cleaned


def _required_list(name: str, value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"invalid_{name}")
    return value


def _required_bool(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"invalid_{name}")
    return value


def _optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _clean_token(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _digest_prefixed(prefix: str, value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"
