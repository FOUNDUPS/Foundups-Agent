"""Main-startup bootstrap for model AutoResearch plan artifact supply.

Slice: REDDOG_MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1

This adapter reads outside-repo runtime JSON inputs and materializes a
``ModelAutoResearchPlanReceipt`` from already verified promotion-gate receipts,
benchmark candidates, policy, and optional model-feedback records.

It does not call models, run benchmarks, promote models, mutate catalogs, write
PatternMemory, re-index HoloIndex, bind runtime defaults, spawn workers, execute
commands, or write inside the repository.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_plan_artifact_supply import (
    MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_ACCEPT,
    run_reddog_model_autoresearch_plan_artifact_supply,
)


MODEL_AUTORESEARCH_PLAN_ARTIFACT_BOOTSTRAP_APPLIED = (
    "MODEL_AUTORESEARCH_PLAN_ARTIFACT_BOOTSTRAP_APPLIED"
)
MODEL_AUTORESEARCH_PLAN_ARTIFACT_BOOTSTRAP_NOT_READY = (
    "MODEL_AUTORESEARCH_PLAN_ARTIFACT_BOOTSTRAP_NOT_READY"
)


@dataclass(frozen=True)
class ModelAutoResearchPlanArtifactBootstrapResult:
    accepted: bool
    status: str
    plan_receipt_id: Optional[str]
    output_path: Optional[str]
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
    no_worker_spawn_performed: bool = True
    no_extension_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_model_autoresearch_plan_artifact_supply_bootstrap(
    *,
    repo_root: Path | str,
    promotion_gate_receipts_path: Path | str | None,
    candidate_pool_path: Path | str | None,
    policy_path: Path | str | None,
    output_path: Path | str | None,
    feedback_records_path: Path | str | None = None,
) -> ModelAutoResearchPlanArtifactBootstrapResult:
    """Materialize an AutoResearch plan artifact from configured runtime files."""

    root = Path(repo_root).resolve()
    promotion_payload, promotion_reasons = _read_json_outside_repo(
        root,
        promotion_gate_receipts_path,
        missing_reason="missing_model_autoresearch_promotion_gate_receipts_path",
        inside_reason="model_autoresearch_promotion_gate_receipts_path_inside_repo",
        malformed_reason="malformed_model_autoresearch_promotion_gate_receipts",
    )
    candidate_payload, candidate_reasons = _read_json_outside_repo(
        root,
        candidate_pool_path,
        missing_reason="missing_model_autoresearch_candidate_pool_path",
        inside_reason="model_autoresearch_candidate_pool_path_inside_repo",
        malformed_reason="malformed_model_autoresearch_candidate_pool",
    )
    policy, policy_reasons = _read_json_outside_repo(
        root,
        policy_path,
        missing_reason="missing_model_autoresearch_policy_path",
        inside_reason="model_autoresearch_policy_path_inside_repo",
        malformed_reason="malformed_model_autoresearch_policy",
    )
    feedback_records, feedback_reasons = _read_feedback_records_outside_repo(
        root,
        feedback_records_path,
        inside_reason="model_autoresearch_feedback_records_path_inside_repo",
        malformed_reason="malformed_model_autoresearch_feedback_records",
    )
    reasons = [
        *promotion_reasons,
        *candidate_reasons,
        *policy_reasons,
        *feedback_reasons,
        *_output_path_reasons(root, output_path),
    ]

    promotion_gate_receipts = _mapping_list(promotion_payload, "promotion_gate_receipts")
    candidate_pool = _mapping_list(candidate_payload, "candidate_pool")
    if promotion_payload is not None and promotion_gate_receipts is None:
        reasons.append("malformed_model_autoresearch_promotion_gate_receipts")
    if candidate_payload is not None and candidate_pool is None:
        reasons.append("malformed_model_autoresearch_candidate_pool")
    if policy is not None and not isinstance(policy, Mapping):
        reasons.append("malformed_model_autoresearch_policy")
    if reasons:
        return _not_ready(reasons)

    assert promotion_gate_receipts is not None
    assert candidate_pool is not None
    assert policy is not None
    supply = run_reddog_model_autoresearch_plan_artifact_supply(
        repo_root=root,
        promotion_gate_receipts=promotion_gate_receipts,
        candidate_pool=candidate_pool,
        policy=policy,
        output_path=output_path,
        feedback_records=feedback_records,
    )
    if not supply.accepted or supply.status != MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_ACCEPT:
        return _not_ready(supply.rejection_reasons or ("model_autoresearch_plan_artifact_supply_rejected",))
    return ModelAutoResearchPlanArtifactBootstrapResult(
        accepted=True,
        status=MODEL_AUTORESEARCH_PLAN_ARTIFACT_BOOTSTRAP_APPLIED,
        plan_receipt_id=supply.plan_receipt_id,
        output_path=supply.output_path,
        source_gate_receipt_ids=supply.source_gate_receipt_ids,
        source_feedback_record_ids=supply.source_feedback_record_ids,
        campaign_item_count=supply.campaign_item_count,
        rejection_reasons=(),
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


def _read_feedback_records_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    inside_reason: str,
    malformed_reason: str,
) -> tuple[tuple[Mapping[str, Any], ...], tuple[str, ...]]:
    if not value:
        return (), ()
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    resolved = path.resolve()
    if _is_inside(resolved, repo_root):
        return (), (inside_reason,)
    if not resolved.exists() or not resolved.is_file():
        return (), ("missing_model_autoresearch_feedback_records_path",)
    try:
        if resolved.suffix.lower() == ".jsonl":
            records = []
            for raw_line in resolved.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                item = json.loads(line)
                if not isinstance(item, Mapping):
                    return (), (malformed_reason,)
                records.append(item)
            return tuple(records), ()
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except Exception:
        return (), (malformed_reason,)
    records = _mapping_list(payload, "feedback_records")
    if records is None:
        return (), (malformed_reason,)
    return records, ()


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
        return ("model_autoresearch_output_path_invalid",)
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    resolved = path.resolve()
    if _is_inside(resolved, repo_root):
        return ("model_autoresearch_output_path_invalid",)
    return ()


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _not_ready(
    reasons: tuple[str, ...] | list[str],
) -> ModelAutoResearchPlanArtifactBootstrapResult:
    return ModelAutoResearchPlanArtifactBootstrapResult(
        accepted=False,
        status=MODEL_AUTORESEARCH_PLAN_ARTIFACT_BOOTSTRAP_NOT_READY,
        plan_receipt_id=None,
        output_path=None,
        source_gate_receipt_ids=(),
        source_feedback_record_ids=(),
        campaign_item_count=0,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason))),
    )


__all__ = [
    "MODEL_AUTORESEARCH_PLAN_ARTIFACT_BOOTSTRAP_APPLIED",
    "MODEL_AUTORESEARCH_PLAN_ARTIFACT_BOOTSTRAP_NOT_READY",
    "ModelAutoResearchPlanArtifactBootstrapResult",
    "run_reddog_model_autoresearch_plan_artifact_supply_bootstrap",
]
