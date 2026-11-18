"""Promotion-gate supply from model AutoResearch campaign execution receipts.

Slice: MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_PHASE1

This module turns one verified ``ModelAutoResearchCampaignExecutionReceipt``
into digest-bound promotion-gate receipts that the next AutoResearch planning
cycle can consume.

It does not call providers, run benchmarks, promote models, mutate catalogs,
write PatternMemory, re-index HoloIndex, bind runtime defaults, spawn workers,
execute commands, or write inside the repository.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from .model_autoresearch_campaign_execution import (
    ModelAutoResearchCampaignExecutionReceipt,
    rehydrate_model_autoresearch_campaign_execution_receipt,
)
from .model_promotion_gate import (
    ModelPromotionGateReceipt,
    ModelPromotionPolicy,
    evaluate_model_promotion_gate,
    rehydrate_model_promotion_gate_receipt,
    rehydrate_model_promotion_policy,
)


MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_ACCEPT = (
    "MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_ACCEPT"
)
MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_REJECT = (
    "MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_REJECT"
)
MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_SCHEMA_VERSION = (
    "model_autoresearch_campaign_promotion_gate_supply.v1"
)


class ModelAutoResearchCampaignPromotionGateSupplyReason:
    EXECUTION_RECEIPT_INVALID = "model_autoresearch_campaign_gate_execution_receipt_invalid"
    POLICIES_INVALID = "model_autoresearch_campaign_gate_policies_invalid"
    POLICY_CANDIDATE_MISMATCH = "model_autoresearch_campaign_gate_policy_candidate_mismatch"
    OUTPUT_PATH_INVALID = "model_autoresearch_campaign_gate_output_path_invalid"
    OUTPUT_WRITE_FAILED = "model_autoresearch_campaign_gate_output_write_failed"


@dataclass(frozen=True)
class ModelAutoResearchCampaignPromotionGateSupplyReceipt:
    receipt_id: str
    source_execution_receipt_id: str
    promotion_gate_receipts: tuple[ModelPromotionGateReceipt, ...]
    schema_version: str = MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "source_execution_receipt_id": self.source_execution_receipt_id,
            "promotion_gate_receipt_ids": [receipt.receipt_id for receipt in self.promotion_gate_receipts],
            "promotion_gate_receipts": [receipt.to_dict() for receipt in self.promotion_gate_receipts],
        }


@dataclass(frozen=True)
class ModelAutoResearchCampaignPromotionGateSupplyResult:
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_model_autoresearch_campaign_promotion_gate_supply(
    *,
    repo_root: Path | str,
    campaign_execution_receipt: Mapping[str, Any] | ModelAutoResearchCampaignExecutionReceipt,
    promotion_policies: Sequence[Mapping[str, Any] | ModelPromotionPolicy],
    output_path: Path | str | None,
    promotion_authority_receipt_id: str | None = None,
    signed_promotion_receipt_id: str | None = None,
) -> ModelAutoResearchCampaignPromotionGateSupplyResult:
    """Evaluate promotion gates for every executed campaign candidate."""

    root = Path(repo_root).resolve()
    reasons: list[str] = []
    try:
        execution = _execution_receipt(campaign_execution_receipt)
    except Exception:
        execution = None
        reasons.append(ModelAutoResearchCampaignPromotionGateSupplyReason.EXECUTION_RECEIPT_INVALID)
    try:
        policies = _promotion_policies(promotion_policies)
    except Exception:
        policies = ()
        reasons.append(ModelAutoResearchCampaignPromotionGateSupplyReason.POLICIES_INVALID)
    output, output_reasons = _runtime_output_path(
        output_path,
        root,
        ModelAutoResearchCampaignPromotionGateSupplyReason.OUTPUT_PATH_INVALID,
    )
    reasons.extend(output_reasons)

    if execution is not None and policies:
        policy_candidate_ids = tuple(sorted(policy.candidate_id for policy in policies))
        executed_candidate_ids = tuple(sorted(execution.executed_candidate_ids))
        if policy_candidate_ids != executed_candidate_ids:
            reasons.append(ModelAutoResearchCampaignPromotionGateSupplyReason.POLICY_CANDIDATE_MISMATCH)

    deduped = _dedupe(reasons)
    if deduped:
        return _reject(deduped)

    assert execution is not None
    assert output is not None
    gates = tuple(
        evaluate_model_promotion_gate(
            benchmark_run_receipt=execution.benchmark_run_receipt,
            policy=policy,
            promotion_authority_receipt_id=_optional(promotion_authority_receipt_id),
            signed_promotion_receipt_id=_optional(signed_promotion_receipt_id),
        )
        for policy in policies
    )
    receipt = _supply_receipt(source_execution_receipt_id=execution.receipt_id, promotion_gate_receipts=gates)
    try:
        _write_json_atomic(output, receipt.to_dict())
    except Exception:
        return _reject((ModelAutoResearchCampaignPromotionGateSupplyReason.OUTPUT_WRITE_FAILED,))
    return ModelAutoResearchCampaignPromotionGateSupplyResult(
        accepted=True,
        status=MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_ACCEPT,
        supply_receipt_id=receipt.receipt_id,
        source_execution_receipt_id=execution.receipt_id,
        output_path=str(output),
        promotion_gate_receipt_ids=tuple(gate.receipt_id for gate in gates),
        rejection_reasons=(),
    )


def rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt(
    payload: Mapping[str, Any],
) -> ModelAutoResearchCampaignPromotionGateSupplyReceipt:
    """Rehydrate a serialized promotion-gate supply receipt and verify its ID."""

    if not isinstance(payload, Mapping):
        raise ValueError("invalid_autoresearch_campaign_promotion_gate_supply")
    if payload.get("schema_version") != MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_SCHEMA_VERSION:
        raise ValueError("invalid_autoresearch_campaign_promotion_gate_supply_schema")
    source_execution_receipt_id = _required(
        payload.get("source_execution_receipt_id"),
        "source_execution_receipt_id",
    )
    gate_payloads = _required_list(payload.get("promotion_gate_receipts"), "promotion_gate_receipts")
    gate_receipts = tuple(
        rehydrate_model_promotion_gate_receipt(_required_mapping(item, "promotion_gate_receipt"))
        for item in gate_payloads
    )
    listed_ids = tuple(
        _required(item, "promotion_gate_receipt_id")
        for item in _required_list(payload.get("promotion_gate_receipt_ids"), "promotion_gate_receipt_ids")
    )
    actual_ids = tuple(receipt.receipt_id for receipt in gate_receipts)
    if listed_ids != actual_ids:
        raise ValueError("promotion_gate_supply_receipt_ids_mismatch")
    if len(set(actual_ids)) != len(actual_ids):
        raise ValueError("duplicate_promotion_gate_receipts")
    receipt = _supply_receipt(
        source_execution_receipt_id=source_execution_receipt_id,
        promotion_gate_receipts=gate_receipts,
    )
    if not hmac.compare_digest(receipt.receipt_id, _required(payload.get("receipt_id"), "receipt_id")):
        raise ValueError("promotion_gate_supply_receipt_id_mismatch")
    return receipt


def _execution_receipt(
    value: Mapping[str, Any] | ModelAutoResearchCampaignExecutionReceipt,
) -> ModelAutoResearchCampaignExecutionReceipt:
    if isinstance(value, ModelAutoResearchCampaignExecutionReceipt):
        return value
    if isinstance(value, Mapping):
        return rehydrate_model_autoresearch_campaign_execution_receipt(value)
    raise ValueError("invalid_execution_receipt")


def _promotion_policies(
    values: Sequence[Mapping[str, Any] | ModelPromotionPolicy],
) -> tuple[ModelPromotionPolicy, ...]:
    policies: list[ModelPromotionPolicy] = []
    for value in values:
        if isinstance(value, ModelPromotionPolicy):
            policies.append(value.normalized())
        elif isinstance(value, Mapping):
            policies.append(rehydrate_model_promotion_policy(value))
        else:
            raise ValueError("invalid_promotion_policy")
    if not policies:
        raise ValueError("missing_promotion_policies")
    candidate_ids = [policy.candidate_id for policy in policies]
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("duplicate_promotion_policy_candidates")
    return tuple(sorted(policies, key=lambda policy: policy.candidate_id))


def _supply_receipt(
    *,
    source_execution_receipt_id: str,
    promotion_gate_receipts: tuple[ModelPromotionGateReceipt, ...],
) -> ModelAutoResearchCampaignPromotionGateSupplyReceipt:
    body = {
        "schema_version": MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_SCHEMA_VERSION,
        "source_execution_receipt_id": source_execution_receipt_id,
        "promotion_gate_receipt_ids": [receipt.receipt_id for receipt in promotion_gate_receipts],
    }
    return ModelAutoResearchCampaignPromotionGateSupplyReceipt(
        receipt_id=_digest_prefixed("model_autoresearch_campaign_promotion_gate_supply", body),
        source_execution_receipt_id=source_execution_receipt_id,
        promotion_gate_receipts=promotion_gate_receipts,
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


def _optional(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _required_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(name + "_invalid")
    return value


def _required_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(name + "_invalid")
    return value


def _digest_prefixed(prefix: str, value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value).strip()))


def _reject(reasons: Sequence[str]) -> ModelAutoResearchCampaignPromotionGateSupplyResult:
    return ModelAutoResearchCampaignPromotionGateSupplyResult(
        accepted=False,
        status=MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_REJECT,
        supply_receipt_id=None,
        source_execution_receipt_id=None,
        output_path=None,
        promotion_gate_receipt_ids=(),
        rejection_reasons=_dedupe(reasons),
    )


__all__ = [
    "MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_ACCEPT",
    "MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_REJECT",
    "MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_SCHEMA_VERSION",
    "ModelAutoResearchCampaignPromotionGateSupplyReason",
    "ModelAutoResearchCampaignPromotionGateSupplyReceipt",
    "ModelAutoResearchCampaignPromotionGateSupplyResult",
    "rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt",
    "run_reddog_model_autoresearch_campaign_promotion_gate_supply",
]
