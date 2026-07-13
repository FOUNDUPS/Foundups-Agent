"""Gate verified research receipts before governed HoloIndex promotion.

Slice: REDDOG_RESEARCH_HOLOINDEX_PROMOTION_GATE_PHASE1

This module consumes the HoloIndex-first research grounding result and an
independent verification receipt, then emits a deterministic promotion plan for
a future governed indexer. It never mutates HoloIndex, fetches external
sources, writes PatternMemory, or executes commands.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

RESEARCH_HOLOINDEX_PROMOTION_ACCEPT = "RESEARCH_HOLOINDEX_PROMOTION_ACCEPT"
RESEARCH_HOLOINDEX_PROMOTION_REJECT = "RESEARCH_HOLOINDEX_PROMOTION_REJECT"

FAIL_GROUNDING_NOT_ACCEPTED = "FAIL_GROUNDING_NOT_ACCEPTED"
FAIL_GROUNDING_RECEIPT_MISSING = "FAIL_GROUNDING_RECEIPT_MISSING"
FAIL_VERIFICATION_NOT_ACCEPTED = "FAIL_VERIFICATION_NOT_ACCEPTED"
FAIL_HOLOINDEX_FRESHNESS_RECEIPT = "FAIL_HOLOINDEX_FRESHNESS_RECEIPT"
FAIL_HOLOINDEX_INDEX_GAP = "FAIL_HOLOINDEX_INDEX_GAP"
FAIL_NO_PROMOTABLE_RESEARCH_TARGET = "FAIL_NO_PROMOTABLE_RESEARCH_TARGET"
FAIL_SOURCE_HASH_MISSING = "FAIL_SOURCE_HASH_MISSING"
FAIL_PROVENANCE_MISSING = "FAIL_PROVENANCE_MISSING"
FAIL_UNTRUSTED_DATA_BOUNDARY = "FAIL_UNTRUSTED_DATA_BOUNDARY"
FAIL_UNSUPPORTED_FINDING_STATUS = "FAIL_UNSUPPORTED_FINDING_STATUS"
FAIL_NEGATIVE_RESULT_NOT_INDEXABLE = "FAIL_NEGATIVE_RESULT_NOT_INDEXABLE"
FAIL_SECRET_BEARING_EVIDENCE = "FAIL_SECRET_BEARING_EVIDENCE"

DESTINATION_COLLECTION = "navigation_knowledge"

POSITIVE_STATUSES = ("candidate", "confirmed", "verified", "replicated")
NEGATIVE_STATUSES = ("negative", "rejected", "null_result", "failed_experiment")
ALLOWED_STATUSES = POSITIVE_STATUSES + NEGATIVE_STATUSES

SECRET_MARKERS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer ",
    "client_secret",
    "password",
    "private_key",
    "secret",
    "token",
)


@dataclass(frozen=True)
class ResearchHoloIndexPromotionEntry:
    entry_id: str
    target: str
    target_digest: str
    source_url: str
    source_domain: str
    source_type: str
    content_digest: str
    external_snapshot_digest: str
    freshness_receipt_digest: str
    provenance_refs: List[str]
    finding_status: str
    destination_collection: str
    index_action: str
    untrusted_data_only: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchHoloIndexPromotionReceipt:
    receipt_id: str
    request_digest: str
    grounding_receipt_id: str
    grounding_receipt_digest: str
    verification_receipt_digest: str
    holoindex_freshness_receipt_digest: str
    entries_total: int
    entries_positive: int
    entries_negative: int
    rejected_negative_results_indexable: bool
    promotion_to_holoindex_performed: bool = False
    no_holoindex_reindex_performed: bool = True
    no_external_fetch_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_command_execution_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchHoloIndexPromotionResult:
    decision: str
    accepted: bool
    receipt: ResearchHoloIndexPromotionReceipt
    entries: List[ResearchHoloIndexPromotionEntry]
    rejection_reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict()
        payload["entries"] = [entry.to_dict() for entry in self.entries]
        return payload


def _mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        mapped = value.to_dict()
        return dict(mapped) if isinstance(mapped, Mapping) else {}
    return {}


def _digest(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _dedupe(values: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _is_digest(value: Any) -> bool:
    text = str(value or "")
    if text.startswith("sha256:"):
        text = text[len("sha256:") :]
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text.lower())


def _verification_accepted(verification_receipt: Mapping[str, Any]) -> bool:
    decision = str(verification_receipt.get("decision") or "").upper()
    return (
        verification_receipt.get("accepted") is True
        or verification_receipt.get("verified") is True
        or decision.endswith("_ACCEPT")
        or decision in {"ACCEPT", "VERIFIED", "PASS"}
    )


def _holoindex_freshness_digest(holoindex_evidence: Mapping[str, Any]) -> str:
    return str(
        holoindex_evidence.get("holoindex_freshness_receipt_digest")
        or holoindex_evidence.get("freshness_receipt_digest")
        or ""
    )


def _holoindex_has_gap(holoindex_evidence: Mapping[str, Any]) -> bool:
    return (
        holoindex_evidence.get("index_gap_detected") is True
        or str(holoindex_evidence.get("retrieval_quality") or "").upper() == "INDEX_GAP"
        or str(holoindex_evidence.get("holoindex_status") or "").upper() == "INDEX_GAP"
    )


def _contains_secret(value: Any) -> bool:
    text = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str).lower()
    return any(marker in text for marker in SECRET_MARKERS)


def _entry_action(status: str) -> str:
    if status in NEGATIVE_STATUSES:
        return "promote_negative_research_result"
    return "promote_verified_research_finding"


def _build_entry(target: Mapping[str, Any]) -> ResearchHoloIndexPromotionEntry:
    seed = {
        "target_digest": target.get("target_digest"),
        "snapshot": target.get("external_snapshot_digest"),
        "content": target.get("content_digest"),
        "status": target.get("finding_status"),
    }
    status = str(target.get("finding_status") or "").lower()
    return ResearchHoloIndexPromotionEntry(
        entry_id="research-index-" + _digest(seed).removeprefix("sha256:")[:16],
        target=str(target.get("target") or ""),
        target_digest=str(target.get("target_digest") or ""),
        source_url=str(target.get("source_url") or ""),
        source_domain=str(target.get("source_domain") or ""),
        source_type=str(target.get("source_type") or ""),
        content_digest=str(target.get("content_digest") or ""),
        external_snapshot_digest=str(target.get("external_snapshot_digest") or ""),
        freshness_receipt_digest=str(target.get("freshness_receipt_digest") or ""),
        provenance_refs=[str(ref) for ref in _as_list(target.get("provenance_refs"))],
        finding_status=status,
        destination_collection=DESTINATION_COLLECTION,
        index_action=_entry_action(status),
        untrusted_data_only=True,
    )


def _target_rejection_reasons(
    target: Mapping[str, Any],
    *,
    negative_indexable: bool,
) -> List[str]:
    reasons: List[str] = []
    status = str(target.get("finding_status") or "").lower()

    if not target.get("grounded"):
        reasons.append(FAIL_GROUNDING_NOT_ACCEPTED)
    if target.get("untrusted_data_only") is not True:
        reasons.append(FAIL_UNTRUSTED_DATA_BOUNDARY)
    if target.get("prompt_injection_markers_detected") and target.get("untrusted_data_only") is not True:
        reasons.append(FAIL_UNTRUSTED_DATA_BOUNDARY)
    if not _is_digest(target.get("content_digest")) or not _is_digest(
        target.get("external_snapshot_digest")
    ):
        reasons.append(FAIL_SOURCE_HASH_MISSING)
    if not _as_list(target.get("provenance_refs")):
        reasons.append(FAIL_PROVENANCE_MISSING)
    if status not in ALLOWED_STATUSES:
        reasons.append(FAIL_UNSUPPORTED_FINDING_STATUS)
    if status in NEGATIVE_STATUSES and not negative_indexable:
        reasons.append(FAIL_NEGATIVE_RESULT_NOT_INDEXABLE)
    if _contains_secret(target):
        reasons.append(FAIL_SECRET_BEARING_EVIDENCE)
    return _dedupe(reasons)


def plan_reddog_research_holoindex_promotion(
    grounding_result: Any,
    *,
    verification_receipt: Mapping[str, Any],
    holoindex_evidence: Mapping[str, Any],
) -> ResearchHoloIndexPromotionResult:
    """Plan HoloIndex promotion for independently verified research evidence."""

    grounding = _mapping(grounding_result)
    receipt = _mapping(grounding.get("receipt"))
    targets = [_mapping(target) for target in _as_list(grounding.get("grounded_targets"))]
    negative_indexable = receipt.get("rejected_negative_results_indexable") is True
    rejection_reasons: List[str] = []

    if grounding.get("accepted") is not True:
        rejection_reasons.append(FAIL_GROUNDING_NOT_ACCEPTED)
    if not receipt or not str(receipt.get("receipt_id") or ""):
        rejection_reasons.append(FAIL_GROUNDING_RECEIPT_MISSING)
    if not _verification_accepted(verification_receipt):
        rejection_reasons.append(FAIL_VERIFICATION_NOT_ACCEPTED)

    freshness_digest = _holoindex_freshness_digest(holoindex_evidence)
    if not _is_digest(freshness_digest):
        rejection_reasons.append(FAIL_HOLOINDEX_FRESHNESS_RECEIPT)
    if _holoindex_has_gap(holoindex_evidence):
        rejection_reasons.append(FAIL_HOLOINDEX_INDEX_GAP)

    entries: List[ResearchHoloIndexPromotionEntry] = []
    for target in targets:
        if not target.get("external_snapshot_digest"):
            continue
        target_reasons = _target_rejection_reasons(
            target,
            negative_indexable=negative_indexable,
        )
        rejection_reasons.extend(target_reasons)
        if not target_reasons:
            entries.append(_build_entry(target))

    if not entries:
        rejection_reasons.append(FAIL_NO_PROMOTABLE_RESEARCH_TARGET)

    rejection_reasons = _dedupe(rejection_reasons)
    accepted = not rejection_reasons
    receipt_seed = {
        "grounding_receipt": receipt,
        "verification_receipt": dict(verification_receipt),
        "holoindex_evidence": dict(holoindex_evidence),
        "entries": [entry.to_dict() for entry in entries],
        "rejection_reasons": rejection_reasons,
    }
    positive_count = len([entry for entry in entries if entry.finding_status in POSITIVE_STATUSES])
    negative_count = len([entry for entry in entries if entry.finding_status in NEGATIVE_STATUSES])
    promotion_receipt = ResearchHoloIndexPromotionReceipt(
        receipt_id="research_holoindex_promotion_"
        + _digest(receipt_seed).removeprefix("sha256:")[:16],
        request_digest=_digest(receipt_seed),
        grounding_receipt_id=str(receipt.get("receipt_id") or ""),
        grounding_receipt_digest=_digest(receipt),
        verification_receipt_digest=_digest(dict(verification_receipt)),
        holoindex_freshness_receipt_digest=freshness_digest,
        entries_total=len(entries),
        entries_positive=positive_count,
        entries_negative=negative_count,
        rejected_negative_results_indexable=negative_indexable,
    )
    return ResearchHoloIndexPromotionResult(
        decision=RESEARCH_HOLOINDEX_PROMOTION_ACCEPT
        if accepted
        else RESEARCH_HOLOINDEX_PROMOTION_REJECT,
        accepted=accepted,
        receipt=promotion_receipt,
        entries=entries,
        rejection_reasons=rejection_reasons,
    )


__all__ = [
    "DESTINATION_COLLECTION",
    "FAIL_GROUNDING_NOT_ACCEPTED",
    "FAIL_GROUNDING_RECEIPT_MISSING",
    "FAIL_HOLOINDEX_FRESHNESS_RECEIPT",
    "FAIL_HOLOINDEX_INDEX_GAP",
    "FAIL_NEGATIVE_RESULT_NOT_INDEXABLE",
    "FAIL_NO_PROMOTABLE_RESEARCH_TARGET",
    "FAIL_PROVENANCE_MISSING",
    "FAIL_SECRET_BEARING_EVIDENCE",
    "FAIL_SOURCE_HASH_MISSING",
    "FAIL_UNSUPPORTED_FINDING_STATUS",
    "FAIL_UNTRUSTED_DATA_BOUNDARY",
    "FAIL_VERIFICATION_NOT_ACCEPTED",
    "RESEARCH_HOLOINDEX_PROMOTION_ACCEPT",
    "RESEARCH_HOLOINDEX_PROMOTION_REJECT",
    "ResearchHoloIndexPromotionEntry",
    "ResearchHoloIndexPromotionReceipt",
    "ResearchHoloIndexPromotionResult",
    "plan_reddog_research_holoindex_promotion",
]
