"""Digest-bound model AutoResearch cycle receipt.

Slice: MODEL_AUTORESEARCH_CYCLE_RECEIPT_PHASE1

This module binds one AutoResearch cycle:

plan receipt -> campaign execution receipt -> promotion-gate supply receipt

It does not call providers, run benchmarks, promote models, mutate catalogs,
write PatternMemory, re-index HoloIndex, bind runtime defaults, spawn workers,
execute commands, or write files.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .model_autoresearch_campaign_execution import (
    ModelAutoResearchCampaignExecutionReceipt,
    rehydrate_model_autoresearch_campaign_execution_receipt,
)
from .model_autoresearch_campaign_promotion_gate_supply import (
    ModelAutoResearchCampaignPromotionGateSupplyReceipt,
    rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt,
)
from .model_champion_challenger_autoresearch import (
    ModelAutoResearchPlanReceipt,
    rehydrate_model_autoresearch_plan_receipt,
)


MODEL_AUTORESEARCH_CYCLE_SCHEMA_VERSION = "model_autoresearch_cycle_receipt.v1"


@dataclass(frozen=True)
class ModelAutoResearchCycleReceipt:
    receipt_id: str
    source_plan_receipt_id: str
    campaign_execution_receipt_id: str
    promotion_gate_supply_receipt_id: str
    executed_candidate_ids: tuple[str, ...]
    promotion_gate_receipt_ids: tuple[str, ...]
    schema_version: str = MODEL_AUTORESEARCH_CYCLE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "source_plan_receipt_id": self.source_plan_receipt_id,
            "campaign_execution_receipt_id": self.campaign_execution_receipt_id,
            "promotion_gate_supply_receipt_id": self.promotion_gate_supply_receipt_id,
            "executed_candidate_ids": list(self.executed_candidate_ids),
            "promotion_gate_receipt_ids": list(self.promotion_gate_receipt_ids),
        }


def build_model_autoresearch_cycle_receipt(
    *,
    plan_receipt: Mapping[str, Any] | ModelAutoResearchPlanReceipt,
    campaign_execution_receipt: Mapping[str, Any] | ModelAutoResearchCampaignExecutionReceipt,
    promotion_gate_supply_receipt: Mapping[str, Any] | ModelAutoResearchCampaignPromotionGateSupplyReceipt,
) -> ModelAutoResearchCycleReceipt:
    """Build a receipt that binds one complete AutoResearch evidence cycle."""

    plan = _plan(plan_receipt)
    execution = _execution(campaign_execution_receipt)
    gate_supply = _gate_supply(promotion_gate_supply_receipt)
    if execution.source_plan_receipt_id != plan.receipt_id:
        raise ValueError("autoresearch_cycle_plan_execution_mismatch")
    if gate_supply.source_execution_receipt_id != execution.receipt_id:
        raise ValueError("autoresearch_cycle_execution_gate_mismatch")
    gate_candidate_ids = tuple(sorted(gate.candidate_id for gate in gate_supply.promotion_gate_receipts))
    executed_candidate_ids = tuple(sorted(execution.executed_candidate_ids))
    if gate_candidate_ids != executed_candidate_ids:
        raise ValueError("autoresearch_cycle_candidate_mismatch")
    promotion_gate_receipt_ids = tuple(gate.receipt_id for gate in gate_supply.promotion_gate_receipts)
    body = _cycle_digest_body(
        source_plan_receipt_id=plan.receipt_id,
        campaign_execution_receipt_id=execution.receipt_id,
        promotion_gate_supply_receipt_id=gate_supply.receipt_id,
        executed_candidate_ids=executed_candidate_ids,
        promotion_gate_receipt_ids=promotion_gate_receipt_ids,
    )
    return ModelAutoResearchCycleReceipt(
        receipt_id=_digest_prefixed("model_autoresearch_cycle", body),
        source_plan_receipt_id=plan.receipt_id,
        campaign_execution_receipt_id=execution.receipt_id,
        promotion_gate_supply_receipt_id=gate_supply.receipt_id,
        executed_candidate_ids=executed_candidate_ids,
        promotion_gate_receipt_ids=promotion_gate_receipt_ids,
    )


def rehydrate_model_autoresearch_cycle_receipt(
    payload: Mapping[str, Any],
) -> ModelAutoResearchCycleReceipt:
    """Rehydrate a serialized cycle receipt and verify its digest."""

    if not isinstance(payload, Mapping):
        raise ValueError("invalid_autoresearch_cycle_receipt")
    if payload.get("schema_version") != MODEL_AUTORESEARCH_CYCLE_SCHEMA_VERSION:
        raise ValueError("invalid_autoresearch_cycle_schema")
    source_plan_receipt_id = _required(payload.get("source_plan_receipt_id"), "source_plan_receipt_id")
    campaign_execution_receipt_id = _required(
        payload.get("campaign_execution_receipt_id"),
        "campaign_execution_receipt_id",
    )
    promotion_gate_supply_receipt_id = _required(
        payload.get("promotion_gate_supply_receipt_id"),
        "promotion_gate_supply_receipt_id",
    )
    executed_candidate_ids = _string_tuple(payload.get("executed_candidate_ids"), "executed_candidate_ids")
    promotion_gate_receipt_ids = _string_tuple(
        payload.get("promotion_gate_receipt_ids"),
        "promotion_gate_receipt_ids",
    )
    body = _cycle_digest_body(
        source_plan_receipt_id=source_plan_receipt_id,
        campaign_execution_receipt_id=campaign_execution_receipt_id,
        promotion_gate_supply_receipt_id=promotion_gate_supply_receipt_id,
        executed_candidate_ids=executed_candidate_ids,
        promotion_gate_receipt_ids=promotion_gate_receipt_ids,
    )
    receipt_id = _digest_prefixed("model_autoresearch_cycle", body)
    if not hmac.compare_digest(receipt_id, _required(payload.get("receipt_id"), "receipt_id")):
        raise ValueError("autoresearch_cycle_receipt_id_mismatch")
    return ModelAutoResearchCycleReceipt(
        receipt_id=receipt_id,
        source_plan_receipt_id=source_plan_receipt_id,
        campaign_execution_receipt_id=campaign_execution_receipt_id,
        promotion_gate_supply_receipt_id=promotion_gate_supply_receipt_id,
        executed_candidate_ids=executed_candidate_ids,
        promotion_gate_receipt_ids=promotion_gate_receipt_ids,
    )


def _plan(value: Mapping[str, Any] | ModelAutoResearchPlanReceipt) -> ModelAutoResearchPlanReceipt:
    if isinstance(value, ModelAutoResearchPlanReceipt):
        return value
    if isinstance(value, Mapping):
        return rehydrate_model_autoresearch_plan_receipt(value)
    raise ValueError("invalid_autoresearch_plan")


def _execution(
    value: Mapping[str, Any] | ModelAutoResearchCampaignExecutionReceipt,
) -> ModelAutoResearchCampaignExecutionReceipt:
    if isinstance(value, ModelAutoResearchCampaignExecutionReceipt):
        return value
    if isinstance(value, Mapping):
        return rehydrate_model_autoresearch_campaign_execution_receipt(value)
    raise ValueError("invalid_autoresearch_execution")


def _gate_supply(
    value: Mapping[str, Any] | ModelAutoResearchCampaignPromotionGateSupplyReceipt,
) -> ModelAutoResearchCampaignPromotionGateSupplyReceipt:
    if isinstance(value, ModelAutoResearchCampaignPromotionGateSupplyReceipt):
        return value
    if isinstance(value, Mapping):
        return rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt(value)
    raise ValueError("invalid_autoresearch_gate_supply")


def _cycle_digest_body(
    *,
    source_plan_receipt_id: str,
    campaign_execution_receipt_id: str,
    promotion_gate_supply_receipt_id: str,
    executed_candidate_ids: tuple[str, ...],
    promotion_gate_receipt_ids: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema_version": MODEL_AUTORESEARCH_CYCLE_SCHEMA_VERSION,
        "source_plan_receipt_id": source_plan_receipt_id,
        "campaign_execution_receipt_id": campaign_execution_receipt_id,
        "promotion_gate_supply_receipt_id": promotion_gate_supply_receipt_id,
        "executed_candidate_ids": list(executed_candidate_ids),
        "promotion_gate_receipt_ids": list(promotion_gate_receipt_ids),
    }


def _required(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(name + "_missing")
    return text


def _required_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(name + "_invalid")
    return value


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    records = tuple(_required(item, name) for item in _required_list(value, name))
    if len(set(records)) != len(records):
        raise ValueError(name + "_duplicate")
    return records


def _digest_prefixed(prefix: str, value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


__all__ = [
    "MODEL_AUTORESEARCH_CYCLE_SCHEMA_VERSION",
    "ModelAutoResearchCycleReceipt",
    "build_model_autoresearch_cycle_receipt",
    "rehydrate_model_autoresearch_cycle_receipt",
]
