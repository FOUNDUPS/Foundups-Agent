"""Plan WRE work items from HoloIndex INDEX_GAP evidence.

This module does not enqueue tasks or run HoloIndex indexing. It turns an
already-observed gap into a deterministic work-item envelope that a later WRE/CI
owner can consume under its own gate.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

from holo_index.freshness_receipt import collections_for_changed_paths


GAP_TOOL_CLASSIFIER_UNAVAILABLE = "TOOL_CLASSIFIER_UNAVAILABLE"
GAP_HOLOINDEX_LOW_SIGNAL = "HOLOINDEX_LOW_SIGNAL"
GAP_HOLOINDEX_STALE_INDEX = "HOLOINDEX_STALE_INDEX"
GAP_HOLOINDEX_RUNTIME_FAILURE = "HOLOINDEX_RUNTIME_FAILURE"

ACTION_TARGETED_REINDEX = "targeted_reindex"
ACTION_RETRIEVAL_QUALITY_SLICE = "retrieval_quality_slice"
ACTION_RUNTIME_REPAIR = "runtime_repair"
ACTION_TOOL_CLASSIFIER_REPAIR = "tool_classifier_repair"

WORKITEM_PLANNED = "WORKITEM_PLANNED"
NO_INDEX_GAP = "NO_INDEX_GAP"
WORKITEM_REJECTED = "WORKITEM_REJECTED"

WRE_OWNER = "WRE_CI_INDEX_MAINTENANCE"


@dataclass(frozen=True)
class HoloIndexIndexGapWorkItem:
    """Typed, non-mutating WRE intake envelope for an INDEX_GAP."""

    work_item_id: str
    gap_class: str
    recommended_action: str
    owner: str
    query: str
    target_paths: list[str] = field(default_factory=list)
    target_collections: list[str] = field(default_factory=list)
    required_targets_missing: list[str] = field(default_factory=list)
    observed_hits: list[str] = field(default_factory=list)
    priority: str = "P2"
    freshness_receipt_digest: str | None = None
    scorecard_digest: str = ""
    live_wre_enqueue_performed: bool = False
    no_reindex_performed: bool = True
    no_agentdb_mutation_performed: bool = True
    no_runtime_reindex_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HoloIndexIndexGapWorkItemResult:
    decision: str
    gap_class: str | None = None
    work_item: HoloIndexIndexGapWorkItem | None = None
    rejection_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.work_item is not None:
            payload["work_item"] = self.work_item.to_dict()
        return payload


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _dedupe_str(values: Iterable[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, Mapping):
            value = value.get("path") or value.get("location") or value.get("target")
        text = str(value or "").strip()
        if not text:
            continue
        key = text.replace("\\", "/").lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text.replace("\\", "/"))
    return out


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _scorecard_digest(scorecard: Mapping[str, Any]) -> str:
    return _canonical_digest(dict(scorecard))


def _receipt_digest(receipt: Mapping[str, Any] | None) -> str | None:
    if not receipt:
        return None
    return _canonical_digest(dict(receipt))


def _observed_hit_paths(scorecard: Mapping[str, Any]) -> list[str]:
    hits: list[Any] = []
    for key in ("code_hits", "wsp_hits", "skill_hits", "docs_hits", "symbol_hits", "work_ledger_hits"):
        hits.extend(_as_list(scorecard.get(key)))
    return _dedupe_str(hits)


def _target_paths(scorecard: Mapping[str, Any], index_gap_event: Mapping[str, Any] | None) -> list[str]:
    values: list[Any] = []
    values.extend(_as_list(scorecard.get("direct_read_paths")))
    values.extend(_as_list(scorecard.get("required_targets_missing")))
    values.extend(_as_list(scorecard.get("required_targets_context_missing")))
    if index_gap_event:
        values.extend(_as_list(index_gap_event.get("stale_targets")))
    return _dedupe_str(values)


def index_gap_detected(scorecard: Mapping[str, Any]) -> bool:
    return (
        bool(scorecard.get("index_gap_detected"))
        or str(scorecard.get("retrieval_quality") or "").upper() == "INDEX_GAP"
        or bool(scorecard.get("direct_read_fallback_used"))
    )


def classify_index_gap(scorecard: Mapping[str, Any]) -> str | None:
    """Classify an INDEX_GAP into the governance taxonomy."""

    if not isinstance(scorecard, Mapping):
        return None

    tool_status = str(scorecard.get("tool_classifier_status") or "").lower()
    if tool_status in {"unavailable", "missing", "failed"} or scorecard.get("tool_classifier_unavailable") is True:
        return GAP_TOOL_CLASSIFIER_UNAVAILABLE

    fetch_error = str(scorecard.get("direct_read_fetch_error") or "").strip()
    holo_status = str(scorecard.get("holoindex_status") or "").lower()
    if fetch_error not in {"", "(none)", "none"} or holo_status in {"error", "runtime_failure", "failed"}:
        return GAP_HOLOINDEX_RUNTIME_FAILURE

    if not index_gap_detected(scorecard):
        return None

    direct_paths = _dedupe_str(_as_list(scorecard.get("direct_read_paths")))
    if direct_paths and (scorecard.get("direct_read_fallback_used") is True or scorecard.get("target_recall_ok") is True):
        return GAP_HOLOINDEX_STALE_INDEX

    if direct_paths and str(scorecard.get("retrieval_quality") or "").upper() == "INDEX_GAP":
        return GAP_HOLOINDEX_STALE_INDEX

    return GAP_HOLOINDEX_LOW_SIGNAL


def _action_for_gap(gap_class: str) -> str:
    if gap_class == GAP_HOLOINDEX_STALE_INDEX:
        return ACTION_TARGETED_REINDEX
    if gap_class == GAP_HOLOINDEX_RUNTIME_FAILURE:
        return ACTION_RUNTIME_REPAIR
    if gap_class == GAP_TOOL_CLASSIFIER_UNAVAILABLE:
        return ACTION_TOOL_CLASSIFIER_REPAIR
    return ACTION_RETRIEVAL_QUALITY_SLICE


def _priority_for_gap(gap_class: str) -> str:
    if gap_class in {GAP_HOLOINDEX_STALE_INDEX, GAP_HOLOINDEX_RUNTIME_FAILURE}:
        return "P1"
    return "P2"


def plan_index_gap_work_item(
    scorecard: Mapping[str, Any] | None,
    *,
    index_gap_event: Mapping[str, Any] | None = None,
    freshness_receipt: Mapping[str, Any] | None = None,
) -> HoloIndexIndexGapWorkItemResult:
    """Plan a non-mutating WRE work item for a HoloIndex gap."""

    if not isinstance(scorecard, Mapping):
        return HoloIndexIndexGapWorkItemResult(
            decision=WORKITEM_REJECTED,
            rejection_reasons=["malformed_scorecard"],
        )

    gap_class = classify_index_gap(scorecard)
    if not gap_class:
        return HoloIndexIndexGapWorkItemResult(decision=NO_INDEX_GAP)

    target_paths = _target_paths(scorecard, index_gap_event)
    target_collections = collections_for_changed_paths(target_paths)
    required_missing = _dedupe_str(_as_list(scorecard.get("required_targets_missing")))
    observed_hits = _observed_hit_paths(scorecard)
    action = _action_for_gap(gap_class)
    query = str(scorecard.get("query") or scorecard.get("task") or "")
    score_digest = _scorecard_digest(scorecard)
    seed = {
        "gap_class": gap_class,
        "recommended_action": action,
        "query": query,
        "target_paths": target_paths,
        "target_collections": target_collections,
        "scorecard_digest": score_digest,
    }
    item_id = "holoindex-gap-" + _canonical_digest(seed)[:16]

    item = HoloIndexIndexGapWorkItem(
        work_item_id=item_id,
        gap_class=gap_class,
        recommended_action=action,
        owner=WRE_OWNER,
        query=query,
        target_paths=target_paths,
        target_collections=target_collections,
        required_targets_missing=required_missing,
        observed_hits=observed_hits,
        priority=_priority_for_gap(gap_class),
        freshness_receipt_digest=_receipt_digest(freshness_receipt),
        scorecard_digest=score_digest,
    )
    return HoloIndexIndexGapWorkItemResult(
        decision=WORKITEM_PLANNED,
        gap_class=gap_class,
        work_item=item,
    )


__all__ = [
    "ACTION_RETRIEVAL_QUALITY_SLICE",
    "ACTION_RUNTIME_REPAIR",
    "ACTION_TARGETED_REINDEX",
    "ACTION_TOOL_CLASSIFIER_REPAIR",
    "GAP_HOLOINDEX_LOW_SIGNAL",
    "GAP_HOLOINDEX_RUNTIME_FAILURE",
    "GAP_HOLOINDEX_STALE_INDEX",
    "GAP_TOOL_CLASSIFIER_UNAVAILABLE",
    "HoloIndexIndexGapWorkItem",
    "HoloIndexIndexGapWorkItemResult",
    "NO_INDEX_GAP",
    "WORKITEM_PLANNED",
    "WORKITEM_REJECTED",
    "WRE_OWNER",
    "classify_index_gap",
    "index_gap_detected",
    "plan_index_gap_work_item",
]
