"""Main-startup bootstrap for model AutoResearch cycle feedback admission.

Slice: REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_MAIN_PREFLIGHT_PHASE1

This adapter reads an outside-repo AutoResearch cycle receipt and appends a
feedback record to an outside-repo AutoResearch cycle feedback ledger.

It does not call providers, run benchmarks, promote models, mutate catalogs,
write PatternMemory, re-index HoloIndex, bind runtime defaults, spawn workers,
execute commands, or write inside the repository.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_feedback_ledger import (
    MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_ACCEPT,
    JsonlModelAutoResearchCycleFeedbackLedgerStore,
    admit_model_autoresearch_cycle_feedback,
)


MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_BOOTSTRAP_APPLIED = (
    "MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_BOOTSTRAP_APPLIED"
)
MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_BOOTSTRAP_NOT_READY = (
    "MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_BOOTSTRAP_NOT_READY"
)


@dataclass(frozen=True)
class ModelAutoResearchCycleFeedbackLedgerBootstrapResult:
    accepted: bool
    status: str
    admission_id: Optional[str]
    cycle_receipt_id: Optional[str]
    feedback_record_id: Optional[str]
    output_path: Optional[str]
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


def run_reddog_model_autoresearch_cycle_feedback_ledger_admission_bootstrap(
    *,
    repo_root: Path | str,
    cycle_receipt_path: Path | str | None,
    output_path: Path | str | None,
) -> ModelAutoResearchCycleFeedbackLedgerBootstrapResult:
    """Append a verified AutoResearch cycle receipt into an outside-repo ledger."""

    root = Path(repo_root).resolve()
    cycle_payload, cycle_reasons = _read_json_outside_repo(
        root,
        cycle_receipt_path,
        missing_reason="missing_model_autoresearch_cycle_receipt_path",
        inside_reason="model_autoresearch_cycle_receipt_path_inside_repo",
        malformed_reason="malformed_model_autoresearch_cycle_receipt",
    )
    reasons = [
        *cycle_reasons,
        *_output_path_reasons(root, output_path),
    ]
    if cycle_payload is not None and not isinstance(cycle_payload, Mapping):
        reasons.append("malformed_model_autoresearch_cycle_receipt")
    if reasons:
        return _not_ready(reasons)

    assert isinstance(cycle_payload, Mapping)
    output = _resolve_output_path(root, output_path)
    assert output is not None
    try:
        admission = admit_model_autoresearch_cycle_feedback(
            explicit_autoresearch_cycle_feedback_ledger_admission_requested=True,
            cycle_receipt=cycle_payload,
            store=JsonlModelAutoResearchCycleFeedbackLedgerStore(output),
        )
    except Exception as exc:
        return _not_ready(("model_autoresearch_cycle_feedback_admission_invalid", f"admission_error:{type(exc).__name__}"))

    if admission.decision != MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_ACCEPT or not admission.receipt:
        return _not_ready(
            tuple(admission.rejection_reasons)
            or ("model_autoresearch_cycle_feedback_admission_rejected",)
        )
    return ModelAutoResearchCycleFeedbackLedgerBootstrapResult(
        accepted=True,
        status=MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_BOOTSTRAP_APPLIED,
        admission_id=admission.receipt.admission_id,
        cycle_receipt_id=admission.receipt.cycle_receipt_id,
        feedback_record_id=admission.receipt.feedback_record_id,
        output_path=str(output),
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


def _output_path_reasons(repo_root: Path, value: Path | str | None) -> tuple[str, ...]:
    if not value:
        return ("model_autoresearch_cycle_feedback_ledger_output_path_invalid",)
    resolved = _resolve_output_path(repo_root, value)
    if resolved is None or _is_inside(resolved, repo_root):
        return ("model_autoresearch_cycle_feedback_ledger_output_path_invalid",)
    return ()


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
    reasons: tuple[str, ...] | list[str],
) -> ModelAutoResearchCycleFeedbackLedgerBootstrapResult:
    return ModelAutoResearchCycleFeedbackLedgerBootstrapResult(
        accepted=False,
        status=MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_BOOTSTRAP_NOT_READY,
        admission_id=None,
        cycle_receipt_id=None,
        feedback_record_id=None,
        output_path=None,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason))),
    )


__all__ = [
    "MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_BOOTSTRAP_APPLIED",
    "MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_BOOTSTRAP_NOT_READY",
    "ModelAutoResearchCycleFeedbackLedgerBootstrapResult",
    "run_reddog_model_autoresearch_cycle_feedback_ledger_admission_bootstrap",
]
