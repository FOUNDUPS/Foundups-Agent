"""Configured runtime chain for model AutoResearch feedback admission.

Slice: MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_BOOTSTRAP_PHASE1

This adapter chains existing outside-repo artifacts:

plan + campaign execution + promotion policies
-> promotion-gate supply
-> cycle receipt
-> cycle feedback ledger admission

It does not call providers, run benchmarks, promote models, mutate catalogs,
write PatternMemory, re-index HoloIndex, bind runtime defaults, spawn workers,
execute commands, or write inside the repository.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_promotion_gate_supply import (
    MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_ACCEPT,
    run_reddog_model_autoresearch_campaign_promotion_gate_supply,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_feedback_ledger_admission_bootstrap import (
    MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_BOOTSTRAP_APPLIED,
    run_reddog_model_autoresearch_cycle_feedback_ledger_admission_bootstrap,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_receipt_supply_bootstrap import (
    MODEL_AUTORESEARCH_CYCLE_RECEIPT_BOOTSTRAP_APPLIED,
    run_reddog_model_autoresearch_cycle_receipt_supply_bootstrap,
)


MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_BOOTSTRAP_APPLIED = (
    "MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_BOOTSTRAP_APPLIED"
)
MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_BOOTSTRAP_NOT_READY = (
    "MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_BOOTSTRAP_NOT_READY"
)


@dataclass(frozen=True)
class ModelAutoResearchCycleFeedbackChainBootstrapResult:
    accepted: bool
    status: str
    promotion_gate_supply_receipt_id: Optional[str]
    cycle_receipt_id: Optional[str]
    feedback_admission_id: Optional[str]
    feedback_record_id: Optional[str]
    promotion_gate_output_path: Optional[str]
    cycle_receipt_output_path: Optional[str]
    feedback_ledger_output_path: Optional[str]
    rejection_reasons: tuple[str, ...]
    no_direct_provider_call_performed: bool = True
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


def run_reddog_model_autoresearch_cycle_feedback_chain_bootstrap(
    *,
    repo_root: Path | str,
    plan_receipt_path: Path | str | None,
    campaign_execution_receipt_path: Path | str | None,
    promotion_policies_path: Path | str | None,
    promotion_gate_output_path: Path | str | None,
    cycle_receipt_output_path: Path | str | None,
    feedback_ledger_output_path: Path | str | None,
    promotion_authority_receipt_id: str | None = None,
    signed_promotion_receipt_id: str | None = None,
) -> ModelAutoResearchCycleFeedbackChainBootstrapResult:
    """Run the post-execution AutoResearch feedback chain."""

    root = Path(repo_root).resolve()
    plan_payload, plan_reasons = _read_json_outside_repo(
        root,
        plan_receipt_path,
        missing_reason="missing_model_autoresearch_chain_plan_receipt_path",
        inside_reason="model_autoresearch_chain_plan_receipt_path_inside_repo",
        malformed_reason="malformed_model_autoresearch_chain_plan_receipt",
    )
    execution_payload, execution_reasons = _read_json_outside_repo(
        root,
        campaign_execution_receipt_path,
        missing_reason="missing_model_autoresearch_chain_execution_receipt_path",
        inside_reason="model_autoresearch_chain_execution_receipt_path_inside_repo",
        malformed_reason="malformed_model_autoresearch_chain_execution_receipt",
    )
    policies_payload, policy_reasons = _read_json_outside_repo(
        root,
        promotion_policies_path,
        missing_reason="missing_model_autoresearch_chain_promotion_policies_path",
        inside_reason="model_autoresearch_chain_promotion_policies_path_inside_repo",
        malformed_reason="malformed_model_autoresearch_chain_promotion_policies",
    )
    reasons = [
        *plan_reasons,
        *execution_reasons,
        *policy_reasons,
        *_output_path_reasons(root, promotion_gate_output_path, "model_autoresearch_chain_promotion_gate_output_path_invalid"),
        *_output_path_reasons(root, cycle_receipt_output_path, "model_autoresearch_chain_cycle_receipt_output_path_invalid"),
        *_output_path_reasons(root, feedback_ledger_output_path, "model_autoresearch_chain_feedback_ledger_output_path_invalid"),
    ]
    output_paths = _resolved_output_paths(
        root,
        promotion_gate_output_path,
        cycle_receipt_output_path,
        feedback_ledger_output_path,
    )
    if output_paths is not None and len(set(output_paths)) != len(output_paths):
        reasons.append("model_autoresearch_chain_output_paths_must_be_distinct")
    policies = _promotion_policy_list(policies_payload)
    if policies_payload is not None and policies is None:
        reasons.append("malformed_model_autoresearch_chain_promotion_policies")
    if plan_payload is not None and not isinstance(plan_payload, Mapping):
        reasons.append("malformed_model_autoresearch_chain_plan_receipt")
    if execution_payload is not None and not isinstance(execution_payload, Mapping):
        reasons.append("malformed_model_autoresearch_chain_execution_receipt")
    deduped = _dedupe(reasons)
    if deduped:
        return _not_ready(deduped)

    assert isinstance(plan_payload, Mapping)
    assert isinstance(execution_payload, Mapping)
    assert policies is not None
    assert output_paths is not None
    gate_output, cycle_output, feedback_output = output_paths

    gate = run_reddog_model_autoresearch_campaign_promotion_gate_supply(
        repo_root=root,
        campaign_execution_receipt=execution_payload,
        promotion_policies=policies,
        output_path=gate_output,
        promotion_authority_receipt_id=promotion_authority_receipt_id,
        signed_promotion_receipt_id=signed_promotion_receipt_id,
    )
    if gate.status != MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_ACCEPT:
        return _not_ready(gate.rejection_reasons or ("model_autoresearch_chain_promotion_gate_rejected",))

    cycle = run_reddog_model_autoresearch_cycle_receipt_supply_bootstrap(
        repo_root=root,
        plan_receipt_path=plan_receipt_path,
        campaign_execution_receipt_path=campaign_execution_receipt_path,
        promotion_gate_supply_receipt_path=gate_output,
        output_path=cycle_output,
    )
    if cycle.status != MODEL_AUTORESEARCH_CYCLE_RECEIPT_BOOTSTRAP_APPLIED:
        return _not_ready(cycle.rejection_reasons or ("model_autoresearch_chain_cycle_receipt_rejected",))

    feedback = run_reddog_model_autoresearch_cycle_feedback_ledger_admission_bootstrap(
        repo_root=root,
        plan_receipt_path=plan_receipt_path,
        cycle_receipt_path=cycle_output,
        output_path=feedback_output,
    )
    if feedback.status != MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_BOOTSTRAP_APPLIED:
        return _not_ready(feedback.rejection_reasons or ("model_autoresearch_chain_feedback_admission_rejected",))

    return ModelAutoResearchCycleFeedbackChainBootstrapResult(
        accepted=True,
        status=MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_BOOTSTRAP_APPLIED,
        promotion_gate_supply_receipt_id=gate.supply_receipt_id,
        cycle_receipt_id=cycle.cycle_receipt_id,
        feedback_admission_id=feedback.admission_id,
        feedback_record_id=feedback.feedback_record_id,
        promotion_gate_output_path=str(gate_output),
        cycle_receipt_output_path=str(cycle_output),
        feedback_ledger_output_path=str(feedback_output),
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


def _promotion_policy_list(payload: Any | None) -> list[Mapping[str, Any]] | None:
    if payload is None:
        return None
    if isinstance(payload, list) and all(isinstance(item, Mapping) for item in payload):
        return list(payload)
    if isinstance(payload, Mapping):
        values = payload.get("promotion_policies")
        if isinstance(values, list) and all(isinstance(item, Mapping) for item in values):
            return list(values)
    return None


def _output_path_reasons(repo_root: Path, value: Path | str | None, reason: str) -> tuple[str, ...]:
    resolved = _resolve_output_path(repo_root, value)
    if resolved is None or _is_inside(resolved, repo_root):
        return (reason,)
    return ()


def _resolved_output_paths(
    repo_root: Path,
    promotion_gate_output_path: Path | str | None,
    cycle_receipt_output_path: Path | str | None,
    feedback_ledger_output_path: Path | str | None,
) -> tuple[Path, Path, Path] | None:
    paths = (
        _resolve_output_path(repo_root, promotion_gate_output_path),
        _resolve_output_path(repo_root, cycle_receipt_output_path),
        _resolve_output_path(repo_root, feedback_ledger_output_path),
    )
    if any(path is None for path in paths):
        return None
    gate, cycle, feedback = paths
    assert gate is not None
    assert cycle is not None
    assert feedback is not None
    return gate, cycle, feedback


def _resolve_output_path(repo_root: Path, value: Path | str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    return path.resolve()


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _not_ready(
    reasons: Sequence[str],
) -> ModelAutoResearchCycleFeedbackChainBootstrapResult:
    return ModelAutoResearchCycleFeedbackChainBootstrapResult(
        accepted=False,
        status=MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_BOOTSTRAP_NOT_READY,
        promotion_gate_supply_receipt_id=None,
        cycle_receipt_id=None,
        feedback_admission_id=None,
        feedback_record_id=None,
        promotion_gate_output_path=None,
        cycle_receipt_output_path=None,
        feedback_ledger_output_path=None,
        rejection_reasons=_dedupe(reasons),
    )


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value or "").strip()))


__all__ = [
    "MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_BOOTSTRAP_APPLIED",
    "MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_BOOTSTRAP_NOT_READY",
    "ModelAutoResearchCycleFeedbackChainBootstrapResult",
    "run_reddog_model_autoresearch_cycle_feedback_chain_bootstrap",
]
