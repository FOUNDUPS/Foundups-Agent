"""Main-startup bootstrap for model AutoResearch promotion-gate supply.

Slice: REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_MAIN_PREFLIGHT_PHASE1

This adapter reads an outside-repo campaign execution receipt plus explicit
promotion policies, then materializes promotion-gate receipts for the next
AutoResearch planning cycle.

It does not call providers, run benchmarks, promote models, mutate catalogs,
write PatternMemory, re-index HoloIndex, bind runtime defaults, spawn workers,
execute commands, or write inside the repository.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_promotion_gate_supply import (
    MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_ACCEPT,
    run_reddog_model_autoresearch_campaign_promotion_gate_supply,
)


MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_BOOTSTRAP_APPLIED = (
    "MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_BOOTSTRAP_APPLIED"
)
MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_BOOTSTRAP_NOT_READY = (
    "MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_BOOTSTRAP_NOT_READY"
)


@dataclass(frozen=True)
class ModelAutoResearchCampaignPromotionGateBootstrapResult:
    accepted: bool
    status: str
    supply_receipt_id: Optional[str]
    source_execution_receipt_id: Optional[str]
    output_path: Optional[str]
    promotion_gate_receipt_ids: tuple[str, ...]
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


def run_reddog_model_autoresearch_campaign_promotion_gate_supply_bootstrap(
    *,
    repo_root: Path | str,
    campaign_execution_receipt_path: Path | str | None,
    promotion_policies_path: Path | str | None,
    output_path: Path | str | None,
    promotion_authority_receipt_id: str | None = None,
    signed_promotion_receipt_id: str | None = None,
) -> ModelAutoResearchCampaignPromotionGateBootstrapResult:
    """Materialize promotion-gate receipts from outside-repo runtime files."""

    root = Path(repo_root).resolve()
    execution_payload, execution_reasons = _read_json_outside_repo(
        root,
        campaign_execution_receipt_path,
        missing_reason="missing_model_autoresearch_campaign_execution_receipt_path",
        inside_reason="model_autoresearch_campaign_execution_receipt_path_inside_repo",
        malformed_reason="malformed_model_autoresearch_campaign_execution_receipt",
    )
    policy_payload, policy_reasons = _read_json_outside_repo(
        root,
        promotion_policies_path,
        missing_reason="missing_model_autoresearch_campaign_promotion_policies_path",
        inside_reason="model_autoresearch_campaign_promotion_policies_path_inside_repo",
        malformed_reason="malformed_model_autoresearch_campaign_promotion_policies",
    )
    reasons = [
        *execution_reasons,
        *policy_reasons,
        *_output_path_reasons(root, output_path),
    ]
    promotion_policies = _mapping_list(policy_payload, "promotion_policies")
    if execution_payload is not None and not isinstance(execution_payload, Mapping):
        reasons.append("malformed_model_autoresearch_campaign_execution_receipt")
    if policy_payload is not None and promotion_policies is None:
        reasons.append("malformed_model_autoresearch_campaign_promotion_policies")
    if reasons:
        return _not_ready(reasons)

    assert isinstance(execution_payload, Mapping)
    assert promotion_policies is not None
    supply = run_reddog_model_autoresearch_campaign_promotion_gate_supply(
        repo_root=root,
        campaign_execution_receipt=execution_payload,
        promotion_policies=promotion_policies,
        output_path=output_path,
        promotion_authority_receipt_id=promotion_authority_receipt_id,
        signed_promotion_receipt_id=signed_promotion_receipt_id,
    )
    if not supply.accepted or supply.status != MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_ACCEPT:
        return _not_ready(supply.rejection_reasons or ("model_autoresearch_campaign_promotion_gate_rejected",))
    return ModelAutoResearchCampaignPromotionGateBootstrapResult(
        accepted=True,
        status=MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_BOOTSTRAP_APPLIED,
        supply_receipt_id=supply.supply_receipt_id,
        source_execution_receipt_id=supply.source_execution_receipt_id,
        output_path=supply.output_path,
        promotion_gate_receipt_ids=supply.promotion_gate_receipt_ids,
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
        return ("model_autoresearch_campaign_promotion_gate_output_path_invalid",)
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    resolved = path.resolve()
    if _is_inside(resolved, repo_root):
        return ("model_autoresearch_campaign_promotion_gate_output_path_invalid",)
    return ()


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _not_ready(
    reasons: tuple[str, ...] | list[str],
) -> ModelAutoResearchCampaignPromotionGateBootstrapResult:
    return ModelAutoResearchCampaignPromotionGateBootstrapResult(
        accepted=False,
        status=MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_BOOTSTRAP_NOT_READY,
        supply_receipt_id=None,
        source_execution_receipt_id=None,
        output_path=None,
        promotion_gate_receipt_ids=(),
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason))),
    )


__all__ = [
    "MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_BOOTSTRAP_APPLIED",
    "MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_BOOTSTRAP_NOT_READY",
    "ModelAutoResearchCampaignPromotionGateBootstrapResult",
    "run_reddog_model_autoresearch_campaign_promotion_gate_supply_bootstrap",
]
