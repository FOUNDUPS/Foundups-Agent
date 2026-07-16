"""AutoResearch campaign planner for champion/challenger model intelligence.

This module plans benchmark campaigns from promotion-gate receipts. It does not
run benchmarks, call providers, mutate model catalogs, write PatternMemory, or
bind RedDog runtime defaults.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from .model_combination_benchmark_harness import ModelBenchmarkCandidate
from .model_promotion_gate import ModelPromotionGateDecision, ModelPromotionGateReceipt


AUTORESEARCH_SCHEMA_VERSION = "model_champion_challenger_autoresearch_plan.v1"
AUTORESEARCH_POLICY_SCHEMA_VERSION = "model_autoresearch_policy.v1"


class ModelAutoResearchAction(str, Enum):
    """Action proposed by the model AutoResearch planner."""

    BENCHMARK_NEW_CANDIDATE = "benchmark_new_candidate"
    REBENCHMARK_CHALLENGER = "rebenchmark_challenger"
    STOP = "stop"


@dataclass(frozen=True)
class ModelAutoResearchPolicy:
    """Policy for selecting the next model benchmark campaigns."""

    task_family: str
    catalog_snapshot_id: str
    max_campaign_items: int = 3
    rebenchmark_challengers: bool = True
    required_verifier_digest: str | None = None
    cost_budget_receipt_id: str | None = None
    schema_version: str = AUTORESEARCH_POLICY_SCHEMA_VERSION

    def normalized(self) -> "ModelAutoResearchPolicy":
        return ModelAutoResearchPolicy(
            task_family=_clean_token(_required("task_family", self.task_family)),
            catalog_snapshot_id=_required("catalog_snapshot_id", self.catalog_snapshot_id),
            max_campaign_items=max(1, min(int(self.max_campaign_items), 10)),
            rebenchmark_challengers=bool(self.rebenchmark_challengers),
            required_verifier_digest=_optional(self.required_verifier_digest),
            cost_budget_receipt_id=_optional(self.cost_budget_receipt_id),
        )

    def to_dict(self) -> dict[str, Any]:
        policy = self.normalized()
        return {
            "schema_version": policy.schema_version,
            "task_family": policy.task_family,
            "catalog_snapshot_id": policy.catalog_snapshot_id,
            "max_campaign_items": policy.max_campaign_items,
            "rebenchmark_challengers": policy.rebenchmark_challengers,
            "required_verifier_digest": policy.required_verifier_digest,
            "cost_budget_receipt_id": policy.cost_budget_receipt_id,
        }


@dataclass(frozen=True)
class ModelAutoResearchCampaignItem:
    """One proposed benchmark campaign item."""

    candidate_id: str
    action: ModelAutoResearchAction
    priority: str
    reason: str
    source_gate_receipt_id: str | None = None
    requires_independent_verifier: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "action": self.action.value,
            "priority": self.priority,
            "reason": self.reason,
            "source_gate_receipt_id": self.source_gate_receipt_id,
            "requires_independent_verifier": self.requires_independent_verifier,
        }


@dataclass(frozen=True)
class ModelAutoResearchPlanReceipt:
    """Digest-bound campaign plan for model AutoResearch."""

    receipt_id: str
    policy: ModelAutoResearchPolicy
    source_gate_receipt_ids: tuple[str, ...]
    candidate_pool_digest: str
    campaign_items: tuple[ModelAutoResearchCampaignItem, ...]
    rejection_reasons: tuple[str, ...] = ()
    schema_version: str = AUTORESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "policy": self.policy.to_dict(),
            "source_gate_receipt_ids": list(self.source_gate_receipt_ids),
            "candidate_pool_digest": self.candidate_pool_digest,
            "campaign_items": [item.to_dict() for item in self.campaign_items],
            "rejection_reasons": list(self.rejection_reasons),
        }


def plan_model_champion_challenger_autoresearch(
    *,
    promotion_gate_receipts: Sequence[ModelPromotionGateReceipt],
    candidate_pool: Sequence[ModelBenchmarkCandidate],
    policy: ModelAutoResearchPolicy,
) -> ModelAutoResearchPlanReceipt:
    """Plan the next benchmark campaigns from gate receipts and candidates."""

    normalized_policy = policy.normalized()
    normalized_candidates = _normalize_candidates(candidate_pool)
    normalized_gates = _normalize_gate_receipts(promotion_gate_receipts, normalized_policy.task_family)
    candidate_pool_digest = _digest_prefixed(
        "model_autoresearch_candidate_pool",
        {"candidates": [candidate.to_dict() for candidate in normalized_candidates]},
    )
    source_gate_ids = tuple(sorted(receipt.receipt_id for receipt in normalized_gates))
    rejection_reasons = _policy_rejections(normalized_policy, normalized_gates)
    campaign_items: list[ModelAutoResearchCampaignItem] = []
    seen_gate_candidate_ids = {receipt.candidate_id for receipt in normalized_gates}

    if not rejection_reasons:
        for receipt in normalized_gates:
            if (
                receipt.decision == ModelPromotionGateDecision.KEEP_CHALLENGER
                and normalized_policy.rebenchmark_challengers
            ):
                campaign_items.append(
                    ModelAutoResearchCampaignItem(
                        candidate_id=receipt.candidate_id,
                        action=ModelAutoResearchAction.REBENCHMARK_CHALLENGER,
                        priority="P2",
                        reason="challenger_below_champion_threshold",
                        source_gate_receipt_id=receipt.receipt_id,
                    )
                )
        for candidate in normalized_candidates:
            if candidate.candidate_id in seen_gate_candidate_ids:
                continue
            campaign_items.append(
                ModelAutoResearchCampaignItem(
                    candidate_id=candidate.candidate_id,
                    action=ModelAutoResearchAction.BENCHMARK_NEW_CANDIDATE,
                    priority="P1",
                    reason="candidate_not_yet_benchmarked",
                )
            )
        campaign_items = campaign_items[: normalized_policy.max_campaign_items]
        if not campaign_items:
            campaign_items.append(
                ModelAutoResearchCampaignItem(
                    candidate_id="none",
                    action=ModelAutoResearchAction.STOP,
                    priority="P3",
                    reason="no_unbenchmarked_or_rebenchmarkable_candidates",
                    requires_independent_verifier=False,
                )
            )
    body = {
        "schema_version": AUTORESEARCH_SCHEMA_VERSION,
        "policy": normalized_policy.to_dict(),
        "source_gate_receipt_ids": list(source_gate_ids),
        "candidate_pool_digest": candidate_pool_digest,
        "campaign_items": [item.to_dict() for item in campaign_items],
        "rejection_reasons": sorted(set(rejection_reasons)),
    }
    return ModelAutoResearchPlanReceipt(
        receipt_id=_digest_prefixed("model_autoresearch_plan", body),
        policy=normalized_policy,
        source_gate_receipt_ids=source_gate_ids,
        candidate_pool_digest=candidate_pool_digest,
        campaign_items=tuple(campaign_items),
        rejection_reasons=tuple(sorted(set(rejection_reasons))),
    )


def _normalize_candidates(candidates: Sequence[ModelBenchmarkCandidate]) -> tuple[ModelBenchmarkCandidate, ...]:
    normalized = tuple(candidates)
    candidate_ids = [candidate.candidate_id for candidate in normalized]
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("duplicate_autoresearch_candidates")
    return tuple(sorted(normalized, key=lambda candidate: candidate.candidate_id))


def _normalize_gate_receipts(
    receipts: Sequence[ModelPromotionGateReceipt],
    task_family: str,
) -> tuple[ModelPromotionGateReceipt, ...]:
    normalized = tuple(receipts)
    receipt_ids = [receipt.receipt_id for receipt in normalized]
    if len(set(receipt_ids)) != len(receipt_ids):
        raise ValueError("duplicate_promotion_gate_receipts")
    if any(receipt.task_family != task_family for receipt in normalized):
        raise ValueError("promotion_gate_task_family_mismatch")
    return tuple(sorted(normalized, key=lambda receipt: receipt.receipt_id))


def _policy_rejections(
    policy: ModelAutoResearchPolicy,
    gate_receipts: tuple[ModelPromotionGateReceipt, ...],
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not gate_receipts:
        reasons.append("missing_promotion_gate_receipts")
    if policy.required_verifier_digest:
        for receipt in gate_receipts:
            gate_verifier = receipt.policy.required_verifier_digest
            if gate_verifier != policy.required_verifier_digest:
                reasons.append("verifier_digest_mismatch")
                break
    if policy.cost_budget_receipt_id is None:
        reasons.append("missing_cost_budget_receipt")
    return tuple(sorted(set(reasons)))


def _required(name: str, value: Any) -> str:
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"missing_{name}")
    return cleaned


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _clean_token(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _digest_prefixed(prefix: str, value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"
