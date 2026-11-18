"""AutoResearch plan artifact supplier for model intelligence.

This module materializes a ``ModelAutoResearchPlanReceipt`` from already-built
promotion-gate receipts, benchmark candidates, policy, and optional
model-feedback ledger records. It does not call providers, run benchmarks,
promote models, mutate catalogs, write PatternMemory, re-index HoloIndex, or
bind runtime defaults.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .model_champion_challenger_autoresearch import (
    ModelAutoResearchPolicy,
    ModelAutoResearchPlanReceipt,
    plan_model_champion_challenger_autoresearch,
)
from .model_combination_benchmark_harness import (
    ModelBenchmarkCandidate,
    ModelBenchmarkRoleAssignment,
    build_model_benchmark_candidate,
)
from .model_promotion_gate import (
    ModelPromotionGateReceipt,
    rehydrate_model_promotion_gate_receipt,
)


MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_ACCEPT = "MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_ACCEPT"
MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_REJECT = "MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_REJECT"


class ModelAutoResearchPlanArtifactSupplyReason:
    PROMOTION_GATES_MISSING = "model_autoresearch_promotion_gates_missing"
    PROMOTION_GATES_INVALID = "model_autoresearch_promotion_gates_invalid"
    CANDIDATE_POOL_MISSING = "model_autoresearch_candidate_pool_missing"
    CANDIDATE_POOL_INVALID = "model_autoresearch_candidate_pool_invalid"
    POLICY_INVALID = "model_autoresearch_policy_invalid"
    FEEDBACK_RECORDS_INVALID = "model_autoresearch_feedback_records_invalid"
    OUTPUT_PATH_INVALID = "model_autoresearch_output_path_invalid"
    OUTPUT_WRITE_FAILED = "model_autoresearch_output_write_failed"


@dataclass(frozen=True)
class ModelAutoResearchPlanArtifactSupplyResult:
    accepted: bool
    status: str
    plan_receipt_id: str | None
    output_path: str | None
    source_gate_receipt_ids: tuple[str, ...]
    source_feedback_record_ids: tuple[str, ...]
    campaign_item_count: int
    rejection_reasons: tuple[str, ...]
    no_model_call_performed: bool = True
    no_benchmark_run_performed: bool = True
    no_model_promotion_performed: bool = True
    no_catalog_mutation_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_runtime_binding_performed: bool = True
    no_command_execution_performed: bool = True
    no_repo_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_model_autoresearch_plan_artifact_supply(
    *,
    repo_root: Path | str,
    promotion_gate_receipts: Sequence[Mapping[str, Any] | ModelPromotionGateReceipt],
    candidate_pool: Sequence[Mapping[str, Any] | ModelBenchmarkCandidate],
    policy: Mapping[str, Any] | ModelAutoResearchPolicy,
    output_path: Path | str | None,
    feedback_records: Sequence[Mapping[str, Any]] = (),
) -> ModelAutoResearchPlanArtifactSupplyResult:
    """Verify inputs, plan AutoResearch campaigns, and write one plan receipt."""

    root = Path(repo_root).resolve()
    reasons: list[str] = []
    gates: tuple[ModelPromotionGateReceipt, ...] = ()
    candidates: tuple[ModelBenchmarkCandidate, ...] = ()
    normalized_policy: ModelAutoResearchPolicy | None = None

    try:
        gates = _promotion_gate_receipts(promotion_gate_receipts)
    except Exception:
        reasons.append(ModelAutoResearchPlanArtifactSupplyReason.PROMOTION_GATES_INVALID)
    if not promotion_gate_receipts:
        reasons.append(ModelAutoResearchPlanArtifactSupplyReason.PROMOTION_GATES_MISSING)

    try:
        candidates = _candidate_pool(candidate_pool)
    except Exception:
        reasons.append(ModelAutoResearchPlanArtifactSupplyReason.CANDIDATE_POOL_INVALID)
    if not candidate_pool:
        reasons.append(ModelAutoResearchPlanArtifactSupplyReason.CANDIDATE_POOL_MISSING)

    try:
        normalized_policy = _policy(policy)
    except Exception:
        reasons.append(ModelAutoResearchPlanArtifactSupplyReason.POLICY_INVALID)

    resolved_output, output_reasons = _runtime_output_path(
        output_path,
        root,
        ModelAutoResearchPlanArtifactSupplyReason.OUTPUT_PATH_INVALID,
    )
    reasons.extend(output_reasons)

    if not reasons:
        assert normalized_policy is not None
        try:
            plan = plan_model_champion_challenger_autoresearch(
                promotion_gate_receipts=gates,
                candidate_pool=candidates,
                policy=normalized_policy,
                feedback_records=feedback_records,
            )
        except Exception:
            reasons.append(ModelAutoResearchPlanArtifactSupplyReason.FEEDBACK_RECORDS_INVALID)
            plan = None
    else:
        plan = None

    deduped = _dedupe(reasons)
    if deduped:
        return _reject(deduped)

    assert plan is not None
    assert resolved_output is not None
    try:
        _write_json_atomic(resolved_output, plan.to_dict())
    except Exception:
        return _reject((ModelAutoResearchPlanArtifactSupplyReason.OUTPUT_WRITE_FAILED,))
    return ModelAutoResearchPlanArtifactSupplyResult(
        accepted=True,
        status=MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_ACCEPT,
        plan_receipt_id=plan.receipt_id,
        output_path=str(resolved_output),
        source_gate_receipt_ids=plan.source_gate_receipt_ids,
        source_feedback_record_ids=plan.source_feedback_record_ids,
        campaign_item_count=len(plan.campaign_items),
        rejection_reasons=(),
    )


def _promotion_gate_receipts(
    values: Sequence[Mapping[str, Any] | ModelPromotionGateReceipt],
) -> tuple[ModelPromotionGateReceipt, ...]:
    receipts: list[ModelPromotionGateReceipt] = []
    for value in values:
        if isinstance(value, ModelPromotionGateReceipt):
            receipts.append(value)
        elif isinstance(value, Mapping):
            receipts.append(rehydrate_model_promotion_gate_receipt(value))
        else:
            raise ValueError("invalid_promotion_gate_receipt")
    return tuple(receipts)


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
    return tuple(candidates)


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


def _policy(value: Mapping[str, Any] | ModelAutoResearchPolicy) -> ModelAutoResearchPolicy:
    if isinstance(value, ModelAutoResearchPolicy):
        return value.normalized()
    if not isinstance(value, Mapping):
        raise ValueError("policy_not_mapping")
    if value.get("schema_version") not in (None, "model_autoresearch_policy.v1"):
        raise ValueError("invalid_policy_schema")
    return ModelAutoResearchPolicy(
        task_family=_required(value.get("task_family"), "task_family"),
        catalog_snapshot_id=_required(value.get("catalog_snapshot_id"), "catalog_snapshot_id"),
        max_campaign_items=int(value.get("max_campaign_items") or 3),
        rebenchmark_challengers=bool(value.get("rebenchmark_challengers", True)),
        required_verifier_digest=_optional(value.get("required_verifier_digest")),
        cost_budget_receipt_id=_optional(value.get("cost_budget_receipt_id")),
    ).normalized()


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


def _optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value).strip()))


def _reject(reasons: Sequence[str]) -> ModelAutoResearchPlanArtifactSupplyResult:
    return ModelAutoResearchPlanArtifactSupplyResult(
        accepted=False,
        status=MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_REJECT,
        plan_receipt_id=None,
        output_path=None,
        source_gate_receipt_ids=(),
        source_feedback_record_ids=(),
        campaign_item_count=0,
        rejection_reasons=_dedupe(reasons),
    )


__all__ = [
    "MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_ACCEPT",
    "MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_REJECT",
    "ModelAutoResearchPlanArtifactSupplyReason",
    "ModelAutoResearchPlanArtifactSupplyResult",
    "run_reddog_model_autoresearch_plan_artifact_supply",
]
