"""Main-startup bootstrap for model AutoResearch cycle receipt supply.

Slice: REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_SUPPLY_MAIN_PREFLIGHT_PHASE1

This adapter reads outside-repo plan, campaign execution, and promotion-gate
supply artifacts, then materializes a digest-bound AutoResearch cycle receipt.

It does not call providers, run benchmarks, promote models, mutate catalogs,
write PatternMemory, re-index HoloIndex, bind runtime defaults, spawn workers,
execute commands, or write inside the repository.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_receipt import (
    build_model_autoresearch_cycle_receipt,
)


MODEL_AUTORESEARCH_CYCLE_RECEIPT_BOOTSTRAP_APPLIED = (
    "MODEL_AUTORESEARCH_CYCLE_RECEIPT_BOOTSTRAP_APPLIED"
)
MODEL_AUTORESEARCH_CYCLE_RECEIPT_BOOTSTRAP_NOT_READY = (
    "MODEL_AUTORESEARCH_CYCLE_RECEIPT_BOOTSTRAP_NOT_READY"
)


@dataclass(frozen=True)
class ModelAutoResearchCycleReceiptBootstrapResult:
    accepted: bool
    status: str
    cycle_receipt_id: Optional[str]
    output_path: Optional[str]
    source_plan_receipt_id: Optional[str]
    campaign_execution_receipt_id: Optional[str]
    promotion_gate_supply_receipt_id: Optional[str]
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


def run_reddog_model_autoresearch_cycle_receipt_supply_bootstrap(
    *,
    repo_root: Path | str,
    plan_receipt_path: Path | str | None,
    campaign_execution_receipt_path: Path | str | None,
    promotion_gate_supply_receipt_path: Path | str | None,
    output_path: Path | str | None,
) -> ModelAutoResearchCycleReceiptBootstrapResult:
    """Materialize an AutoResearch cycle receipt from configured runtime files."""

    root = Path(repo_root).resolve()
    plan_payload, plan_reasons = _read_json_outside_repo(
        root,
        plan_receipt_path,
        missing_reason="missing_model_autoresearch_cycle_plan_receipt_path",
        inside_reason="model_autoresearch_cycle_plan_receipt_path_inside_repo",
        malformed_reason="malformed_model_autoresearch_cycle_plan_receipt",
    )
    execution_payload, execution_reasons = _read_json_outside_repo(
        root,
        campaign_execution_receipt_path,
        missing_reason="missing_model_autoresearch_cycle_execution_receipt_path",
        inside_reason="model_autoresearch_cycle_execution_receipt_path_inside_repo",
        malformed_reason="malformed_model_autoresearch_cycle_execution_receipt",
    )
    gate_payload, gate_reasons = _read_json_outside_repo(
        root,
        promotion_gate_supply_receipt_path,
        missing_reason="missing_model_autoresearch_cycle_gate_supply_receipt_path",
        inside_reason="model_autoresearch_cycle_gate_supply_receipt_path_inside_repo",
        malformed_reason="malformed_model_autoresearch_cycle_gate_supply_receipt",
    )
    reasons = [
        *plan_reasons,
        *execution_reasons,
        *gate_reasons,
        *_output_path_reasons(root, output_path),
    ]
    if plan_payload is not None and not isinstance(plan_payload, Mapping):
        reasons.append("malformed_model_autoresearch_cycle_plan_receipt")
    if execution_payload is not None and not isinstance(execution_payload, Mapping):
        reasons.append("malformed_model_autoresearch_cycle_execution_receipt")
    if gate_payload is not None and not isinstance(gate_payload, Mapping):
        reasons.append("malformed_model_autoresearch_cycle_gate_supply_receipt")
    if reasons:
        return _not_ready(reasons)

    assert isinstance(plan_payload, Mapping)
    assert isinstance(execution_payload, Mapping)
    assert isinstance(gate_payload, Mapping)
    try:
        receipt = build_model_autoresearch_cycle_receipt(
            plan_receipt=plan_payload,
            campaign_execution_receipt=execution_payload,
            promotion_gate_supply_receipt=gate_payload,
        )
    except Exception as exc:
        return _not_ready(("model_autoresearch_cycle_receipt_invalid", f"cycle_error:{type(exc).__name__}"))

    output = _resolve_output_path(root, output_path)
    assert output is not None
    try:
        _write_json_atomic(output, receipt.to_dict())
    except Exception:
        return _not_ready(("model_autoresearch_cycle_receipt_output_write_failed",))
    return ModelAutoResearchCycleReceiptBootstrapResult(
        accepted=True,
        status=MODEL_AUTORESEARCH_CYCLE_RECEIPT_BOOTSTRAP_APPLIED,
        cycle_receipt_id=receipt.receipt_id,
        output_path=str(output),
        source_plan_receipt_id=receipt.source_plan_receipt_id,
        campaign_execution_receipt_id=receipt.campaign_execution_receipt_id,
        promotion_gate_supply_receipt_id=receipt.promotion_gate_supply_receipt_id,
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
        return ("model_autoresearch_cycle_receipt_output_path_invalid",)
    resolved = _resolve_output_path(repo_root, value)
    if resolved is None or _is_inside(resolved, repo_root):
        return ("model_autoresearch_cycle_receipt_output_path_invalid",)
    return ()


def _resolve_output_path(repo_root: Path, value: Path | str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    return path.resolve()


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


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _not_ready(
    reasons: tuple[str, ...] | list[str],
) -> ModelAutoResearchCycleReceiptBootstrapResult:
    return ModelAutoResearchCycleReceiptBootstrapResult(
        accepted=False,
        status=MODEL_AUTORESEARCH_CYCLE_RECEIPT_BOOTSTRAP_NOT_READY,
        cycle_receipt_id=None,
        output_path=None,
        source_plan_receipt_id=None,
        campaign_execution_receipt_id=None,
        promotion_gate_supply_receipt_id=None,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason))),
    )


__all__ = [
    "MODEL_AUTORESEARCH_CYCLE_RECEIPT_BOOTSTRAP_APPLIED",
    "MODEL_AUTORESEARCH_CYCLE_RECEIPT_BOOTSTRAP_NOT_READY",
    "ModelAutoResearchCycleReceiptBootstrapResult",
    "run_reddog_model_autoresearch_cycle_receipt_supply_bootstrap",
]
