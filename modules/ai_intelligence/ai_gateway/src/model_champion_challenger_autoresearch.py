"""AutoResearch campaign planner for champion/challenger model intelligence.

This module plans benchmark campaigns from promotion-gate receipts. It does not
run benchmarks, call providers, mutate model catalogs, write PatternMemory, or
bind RedDog runtime defaults.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from .model_combination_benchmark_harness import ModelBenchmarkCandidate
from .model_promotion_gate import ModelPromotionGateDecision, ModelPromotionGateReceipt


AUTORESEARCH_SCHEMA_VERSION = "model_champion_challenger_autoresearch_plan.v1"
AUTORESEARCH_POLICY_SCHEMA_VERSION = "model_autoresearch_policy.v1"
MODEL_SELECTION_FEEDBACK_RECORD_TYPE = "model_selection_outcome_feedback"
MODEL_SELECTION_FEEDBACK_RECORD_SCHEMA = "model_feedback_ledger_record.v1"
MODEL_AUTORESEARCH_CYCLE_FEEDBACK_RECORD_TYPE = "model_autoresearch_cycle_feedback"
MODEL_AUTORESEARCH_CYCLE_FEEDBACK_RECORD_SCHEMA = "model_autoresearch_cycle_feedback_record.v1"


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
    source_feedback_record_ids: tuple[str, ...]
    candidate_pool_digest: str
    feedback_ledger_digest: str
    campaign_items: tuple[ModelAutoResearchCampaignItem, ...]
    rejection_reasons: tuple[str, ...] = ()
    schema_version: str = AUTORESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "policy": self.policy.to_dict(),
            "source_gate_receipt_ids": list(self.source_gate_receipt_ids),
            "source_feedback_record_ids": list(self.source_feedback_record_ids),
            "candidate_pool_digest": self.candidate_pool_digest,
            "feedback_ledger_digest": self.feedback_ledger_digest,
            "campaign_items": [item.to_dict() for item in self.campaign_items],
            "rejection_reasons": list(self.rejection_reasons),
        }


def plan_model_champion_challenger_autoresearch(
    *,
    promotion_gate_receipts: Sequence[ModelPromotionGateReceipt],
    candidate_pool: Sequence[ModelBenchmarkCandidate],
    policy: ModelAutoResearchPolicy,
    feedback_records: Sequence[Mapping[str, Any]] = (),
) -> ModelAutoResearchPlanReceipt:
    """Plan the next benchmark campaigns from gate receipts and candidates."""

    normalized_policy = policy.normalized()
    normalized_candidates = _normalize_candidates(candidate_pool)
    normalized_gates = _normalize_gate_receipts(promotion_gate_receipts, normalized_policy.task_family)
    normalized_feedback = _normalize_feedback_records(feedback_records, normalized_policy)
    feedback_model_ids = _feedback_model_ids(normalized_feedback)
    candidate_pool_digest = _digest_prefixed(
        "model_autoresearch_candidate_pool",
        {"candidates": [candidate.to_dict() for candidate in normalized_candidates]},
    )
    feedback_ledger_digest = _digest_prefixed(
        "model_autoresearch_feedback_ledger",
        {"feedback_records": list(normalized_feedback)},
    )
    source_gate_ids = tuple(sorted(receipt.receipt_id for receipt in normalized_gates))
    source_feedback_record_ids = tuple(
        sorted(str(record["feedback_record_id"]) for record in normalized_feedback)
    )
    rejection_reasons = _policy_rejections(normalized_policy, normalized_gates)
    campaign_items: list[ModelAutoResearchCampaignItem] = []
    seen_gate_candidate_ids = {receipt.candidate_id for receipt in normalized_gates}

    if not rejection_reasons:
        for receipt in normalized_gates:
            if (
                receipt.decision == ModelPromotionGateDecision.KEEP_CHALLENGER
                and normalized_policy.rebenchmark_challengers
            ):
                has_feedback = receipt.candidate_id in feedback_model_ids
                campaign_items.append(
                    ModelAutoResearchCampaignItem(
                        candidate_id=receipt.candidate_id,
                        action=ModelAutoResearchAction.REBENCHMARK_CHALLENGER,
                        priority="P1" if has_feedback else "P2",
                        reason=(
                            "verified_runtime_feedback_rebenchmark_challenger"
                            if has_feedback
                            else "challenger_below_champion_threshold"
                        ),
                        source_gate_receipt_id=receipt.receipt_id,
                    )
                )
        for candidate in normalized_candidates:
            if candidate.candidate_id in seen_gate_candidate_ids:
                continue
            has_feedback = candidate.candidate_id in feedback_model_ids
            campaign_items.append(
                ModelAutoResearchCampaignItem(
                    candidate_id=candidate.candidate_id,
                    action=ModelAutoResearchAction.BENCHMARK_NEW_CANDIDATE,
                    priority="P0" if has_feedback else "P1",
                    reason=(
                        "verified_runtime_feedback_unbenchmarked_candidate"
                        if has_feedback
                        else "candidate_not_yet_benchmarked"
                    ),
                )
            )
        if normalized_feedback:
            campaign_items = list(
                sorted(campaign_items, key=lambda item: (_priority_rank(item.priority), item.candidate_id))
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
    body = _plan_digest_body(
        policy=normalized_policy,
        source_gate_receipt_ids=source_gate_ids,
        source_feedback_record_ids=source_feedback_record_ids,
        candidate_pool_digest=candidate_pool_digest,
        feedback_ledger_digest=feedback_ledger_digest,
        campaign_items=tuple(campaign_items),
        rejection_reasons=tuple(sorted(set(rejection_reasons))),
    )
    return ModelAutoResearchPlanReceipt(
        receipt_id=_digest_prefixed("model_autoresearch_plan", body),
        policy=normalized_policy,
        source_gate_receipt_ids=source_gate_ids,
        source_feedback_record_ids=source_feedback_record_ids,
        candidate_pool_digest=candidate_pool_digest,
        feedback_ledger_digest=feedback_ledger_digest,
        campaign_items=tuple(campaign_items),
        rejection_reasons=tuple(sorted(set(rejection_reasons))),
    )


def rehydrate_model_autoresearch_policy(payload: Mapping[str, Any]) -> ModelAutoResearchPolicy:
    """Rehydrate and normalize a serialized AutoResearch policy."""

    if not isinstance(payload, Mapping):
        raise ValueError("invalid_autoresearch_policy")
    if payload.get("schema_version") != AUTORESEARCH_POLICY_SCHEMA_VERSION:
        raise ValueError("invalid_autoresearch_policy_schema")
    return ModelAutoResearchPolicy(
        task_family=_required("task_family", payload.get("task_family")),
        catalog_snapshot_id=_required("catalog_snapshot_id", payload.get("catalog_snapshot_id")),
        max_campaign_items=int(payload.get("max_campaign_items") or 3),
        rebenchmark_challengers=bool(payload.get("rebenchmark_challengers", True)),
        required_verifier_digest=_optional(payload.get("required_verifier_digest")),
        cost_budget_receipt_id=_optional(payload.get("cost_budget_receipt_id")),
    ).normalized()


def rehydrate_model_autoresearch_plan_receipt(
    payload: Mapping[str, Any],
) -> ModelAutoResearchPlanReceipt:
    """Rehydrate a serialized AutoResearch plan and verify its receipt digest."""

    if not isinstance(payload, Mapping):
        raise ValueError("invalid_autoresearch_plan")
    if payload.get("schema_version") != AUTORESEARCH_SCHEMA_VERSION:
        raise ValueError("invalid_autoresearch_plan_schema")
    receipt_id = _required("receipt_id", payload.get("receipt_id"))
    policy = rehydrate_model_autoresearch_policy(_required_mapping("policy", payload.get("policy")))
    source_gate_receipt_ids = _string_tuple("source_gate_receipt_ids", payload.get("source_gate_receipt_ids"))
    source_feedback_record_ids = _string_tuple(
        "source_feedback_record_ids",
        payload.get("source_feedback_record_ids"),
    )
    candidate_pool_digest = _required("candidate_pool_digest", payload.get("candidate_pool_digest"))
    feedback_ledger_digest = _required("feedback_ledger_digest", payload.get("feedback_ledger_digest"))
    campaign_items = tuple(
        _rehydrate_campaign_item(item)
        for item in _required_list("campaign_items", payload.get("campaign_items"))
    )
    rejection_reasons = tuple(
        sorted(set(_clean_token(item) for item in _required_list("rejection_reasons", payload.get("rejection_reasons"))))
    )
    body = _plan_digest_body(
        policy=policy,
        source_gate_receipt_ids=source_gate_receipt_ids,
        source_feedback_record_ids=source_feedback_record_ids,
        candidate_pool_digest=candidate_pool_digest,
        feedback_ledger_digest=feedback_ledger_digest,
        campaign_items=campaign_items,
        rejection_reasons=rejection_reasons,
    )
    expected = _digest_prefixed("model_autoresearch_plan", body)
    if not hmac.compare_digest(receipt_id, expected):
        raise ValueError("model_autoresearch_plan_receipt_id_mismatch")
    return ModelAutoResearchPlanReceipt(
        receipt_id=receipt_id,
        policy=policy,
        source_gate_receipt_ids=source_gate_receipt_ids,
        source_feedback_record_ids=source_feedback_record_ids,
        candidate_pool_digest=candidate_pool_digest,
        feedback_ledger_digest=feedback_ledger_digest,
        campaign_items=campaign_items,
        rejection_reasons=rejection_reasons,
    )


def _plan_digest_body(
    *,
    policy: ModelAutoResearchPolicy,
    source_gate_receipt_ids: Sequence[str],
    source_feedback_record_ids: Sequence[str],
    candidate_pool_digest: str,
    feedback_ledger_digest: str,
    campaign_items: Sequence[ModelAutoResearchCampaignItem],
    rejection_reasons: Sequence[str],
) -> dict[str, Any]:
    return {
        "schema_version": AUTORESEARCH_SCHEMA_VERSION,
        "policy": policy.to_dict(),
        "source_gate_receipt_ids": list(source_gate_receipt_ids),
        "source_feedback_record_ids": list(source_feedback_record_ids),
        "candidate_pool_digest": candidate_pool_digest,
        "feedback_ledger_digest": feedback_ledger_digest,
        "campaign_items": [item.to_dict() for item in campaign_items],
        "rejection_reasons": list(rejection_reasons),
    }


def _rehydrate_campaign_item(payload: Any) -> ModelAutoResearchCampaignItem:
    item = _required_mapping("campaign_item", payload)
    raw_action = _required("action", item.get("action"))
    try:
        action = ModelAutoResearchAction(raw_action)
    except ValueError as exc:
        raise ValueError("invalid_autoresearch_campaign_action") from exc
    priority = _required("priority", item.get("priority"))
    if priority not in {"P0", "P1", "P2", "P3"}:
        raise ValueError("invalid_autoresearch_campaign_priority")
    raw_requires = item.get("requires_independent_verifier")
    if not isinstance(raw_requires, bool):
        raise ValueError("invalid_autoresearch_campaign_verifier_flag")
    return ModelAutoResearchCampaignItem(
        candidate_id=_required("candidate_id", item.get("candidate_id")),
        action=action,
        priority=priority,
        reason=_clean_token(_required("reason", item.get("reason"))),
        source_gate_receipt_id=_optional(item.get("source_gate_receipt_id")),
        requires_independent_verifier=raw_requires,
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


def _normalize_feedback_records(
    feedback_records: Sequence[Mapping[str, Any]],
    policy: ModelAutoResearchPolicy,
) -> tuple[dict[str, Any], ...]:
    normalized: list[dict[str, Any]] = []
    record_ids: list[str] = []
    for record in feedback_records:
        if not isinstance(record, Mapping):
            raise ValueError("invalid_feedback_record")
        candidate = dict(record)
        record_type = candidate.get("record_type")
        if record_type == MODEL_SELECTION_FEEDBACK_RECORD_TYPE:
            normalized_record = _normalize_model_selection_feedback_record(candidate, policy)
        elif record_type == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_RECORD_TYPE:
            normalized_record = _normalize_autoresearch_cycle_feedback_record(candidate, policy)
        else:
            raise ValueError("invalid_feedback_record_type")
        normalized.append(normalized_record)
        record_id = str(normalized_record["feedback_record_id"])
        record_ids.append(record_id)
    if len(set(record_ids)) != len(record_ids):
        raise ValueError("duplicate_feedback_record_ids")
    return tuple(sorted(normalized, key=lambda item: item["feedback_record_id"]))


def _normalize_model_selection_feedback_record(
    candidate: Mapping[str, Any],
    policy: ModelAutoResearchPolicy,
) -> dict[str, Any]:
    if candidate.get("schema_version") != MODEL_SELECTION_FEEDBACK_RECORD_SCHEMA:
        raise ValueError("invalid_feedback_record_schema")
    record_id = _required("feedback_record_id", candidate.get("feedback_record_id"))
    if not record_id.startswith("model_feedback_"):
        raise ValueError("invalid_feedback_record_id")
    for field in (
        "outcome_receipt_id",
        "selection_receipt_id",
        "catalog_snapshot_id",
        "task_family",
        "source_ratchet_id",
        "source_ratchet_digest",
    ):
        _required(field, candidate.get(field))
    if candidate["task_family"] != policy.task_family:
        raise ValueError("feedback_task_family_mismatch")
    if candidate["catalog_snapshot_id"] != policy.catalog_snapshot_id:
        raise ValueError("feedback_catalog_snapshot_mismatch")
    selected_model_ids = _nonempty_string_tuple("selected_model_ids", candidate.get("selected_model_ids"))
    verification_receipt_ids = _nonempty_string_tuple(
        "verification_receipt_ids",
        candidate.get("verification_receipt_ids"),
    )
    if not _is_digest(candidate.get("source_ratchet_digest")):
        raise ValueError("feedback_source_ratchet_digest_invalid")
    return {
        "feedback_record_id": record_id,
        "record_type": MODEL_SELECTION_FEEDBACK_RECORD_TYPE,
        "schema_version": MODEL_SELECTION_FEEDBACK_RECORD_SCHEMA,
        "outcome_receipt_id": str(candidate["outcome_receipt_id"]),
        "selection_receipt_id": str(candidate["selection_receipt_id"]),
        "catalog_snapshot_id": str(candidate["catalog_snapshot_id"]),
        "task_family": str(candidate["task_family"]),
        "selected_model_ids": list(selected_model_ids),
        "verification_receipt_ids": list(verification_receipt_ids),
        "source_ratchet_id": str(candidate["source_ratchet_id"]),
        "source_ratchet_digest": str(candidate["source_ratchet_digest"]),
    }


def _normalize_autoresearch_cycle_feedback_record(
    candidate: Mapping[str, Any],
    policy: ModelAutoResearchPolicy,
) -> dict[str, Any]:
    if candidate.get("schema_version") != MODEL_AUTORESEARCH_CYCLE_FEEDBACK_RECORD_SCHEMA:
        raise ValueError("invalid_feedback_record_schema")
    record_id = _required("feedback_record_id", candidate.get("feedback_record_id"))
    if not record_id.startswith("model_autoresearch_cycle_feedback_"):
        raise ValueError("invalid_feedback_record_id")
    if candidate.get("source_plan_context_bound") is not True:
        raise ValueError("feedback_source_plan_context_unbound")
    for field in (
        "cycle_receipt_id",
        "source_plan_receipt_id",
        "campaign_execution_receipt_id",
        "promotion_gate_supply_receipt_id",
        "catalog_snapshot_id",
        "task_family",
        "source_plan_receipt_digest",
    ):
        _required(field, candidate.get(field))
    if candidate["task_family"] != policy.task_family:
        raise ValueError("feedback_task_family_mismatch")
    if candidate["catalog_snapshot_id"] != policy.catalog_snapshot_id:
        raise ValueError("feedback_catalog_snapshot_mismatch")
    executed_candidate_ids = _nonempty_string_tuple("executed_candidate_ids", candidate.get("executed_candidate_ids"))
    promotion_gate_receipt_ids = _nonempty_string_tuple(
        "promotion_gate_receipt_ids",
        candidate.get("promotion_gate_receipt_ids"),
    )
    if not _is_digest(candidate.get("source_plan_receipt_digest")):
        raise ValueError("feedback_source_plan_receipt_digest_invalid")
    return {
        "feedback_record_id": record_id,
        "record_type": MODEL_AUTORESEARCH_CYCLE_FEEDBACK_RECORD_TYPE,
        "schema_version": MODEL_AUTORESEARCH_CYCLE_FEEDBACK_RECORD_SCHEMA,
        "cycle_receipt_id": str(candidate["cycle_receipt_id"]),
        "source_plan_receipt_id": str(candidate["source_plan_receipt_id"]),
        "source_plan_context_bound": True,
        "campaign_execution_receipt_id": str(candidate["campaign_execution_receipt_id"]),
        "promotion_gate_supply_receipt_id": str(candidate["promotion_gate_supply_receipt_id"]),
        "catalog_snapshot_id": str(candidate["catalog_snapshot_id"]),
        "task_family": str(candidate["task_family"]),
        "selected_model_ids": list(executed_candidate_ids),
        "verification_receipt_ids": list(promotion_gate_receipt_ids),
        "source_plan_receipt_digest": str(candidate["source_plan_receipt_digest"]),
    }


def _feedback_model_ids(feedback_records: tuple[dict[str, Any], ...]) -> set[str]:
    model_ids: set[str] = set()
    for record in feedback_records:
        model_ids.update(str(value) for value in record["selected_model_ids"])
    return model_ids


def _priority_rank(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(priority, 9)


def _required(name: str, value: Any) -> str:
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"missing_{name}")
    return cleaned


def _required_mapping(name: str, value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"invalid_{name}")
    return value


def _required_list(name: str, value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"invalid_{name}")
    return value


def _string_tuple(name: str, value: Any) -> tuple[str, ...]:
    raw = _required_list(name, value)
    records = tuple(_required(name, item) for item in raw)
    if len(set(records)) != len(records):
        raise ValueError(f"duplicate_{name}")
    return records


def _nonempty_string_tuple(name: str, value: Any) -> tuple[str, ...]:
    records = _string_tuple(name, value)
    if not records:
        raise ValueError(f"invalid_{name}")
    return records


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _clean_token(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _is_digest(value: Any) -> bool:
    text = str(value or "")
    return (
        text.startswith("sha256:")
        and len(text) == 71
        and all(ch in "0123456789abcdef" for ch in text.removeprefix("sha256:"))
    )


def _digest_prefixed(prefix: str, value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"
