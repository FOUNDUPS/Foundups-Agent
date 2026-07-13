"""Verified outcome ratchet for RedDog/WRE autonomous work.

Slice: REDDOG_VERIFIED_OUTCOME_RATCHET_PHASE1

The ratchet persists request, execution, verification, cost, latency, acceptance,
and failure receipts. It may forward an outcome to an injected PatternMemory sink
only when the independent autonomous-slice verifier accepted the outcome. This
module does not import PatternMemory, run commands, publish PRs, merge, settle
rewards, call GitHub, or mutate HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Protocol

from modules.infrastructure.wre_core.src.reddog_verified_draft_pr_publish import (
    VERIFIED_DRAFT_PR_PUBLISH_ACCEPT,
)
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
)

OUTCOME_RATCHET_RECORDED = "OUTCOME_RATCHET_RECORDED"
OUTCOME_RATCHET_REJECT = "OUTCOME_RATCHET_REJECT"

FAIL_REQUIRED_FIELD = "FAIL_REQUIRED_FIELD"
FAIL_VERIFICATION_RECEIPT = "FAIL_VERIFICATION_RECEIPT"
FAIL_PUBLISH_RECEIPT = "FAIL_PUBLISH_RECEIPT"
FAIL_RECEIPT_SET = "FAIL_RECEIPT_SET"
FAIL_COST_LATENCY = "FAIL_COST_LATENCY"
FAIL_HOLOINDEX_EVIDENCE = "FAIL_HOLOINDEX_EVIDENCE"
FAIL_SECRET_IN_RECEIPT = "FAIL_SECRET_IN_RECEIPT"
FAIL_PATTERN_MEMORY_UNVERIFIED = "FAIL_PATTERN_MEMORY_UNVERIFIED"
FAIL_STORE_WRITE = "FAIL_STORE_WRITE"
FAIL_PATTERN_MEMORY_WRITE = "FAIL_PATTERN_MEMORY_WRITE"

SECRET_MARKERS = (
    "authorization:",
    "bearer ",
    "api_key",
    "apikey",
    "private_key",
    "begin private key",
    "secret=",
    "token=",
    "password=",
)


class OutcomeRatchetStore(Protocol):
    def append(self, record: Mapping[str, Any]) -> str:
        ...


class PatternMemorySink(Protocol):
    def store_verified_outcome(self, record: Mapping[str, Any]) -> str:
        ...


class InMemoryOutcomeRatchetStore:
    """Test/local store for ratchet records."""

    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []

    def append(self, record: Mapping[str, Any]) -> str:
        payload = dict(record)
        self.records.append(payload)
        return str(payload["ratchet_id"])


class JsonlOutcomeRatchetStore:
    """Append-only JSONL store for ratchet records."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def append(self, record: Mapping[str, Any]) -> str:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
        return str(record["ratchet_id"])


@dataclass(frozen=True)
class VerifiedOutcomeRatchetReceipt:
    ratchet_id: str
    work_order_id: str
    slice_name: str
    outcome_status: str
    verifier_receipt_id: str
    publish_receipt_id: Optional[str]
    request_digest: str
    execution_receipts_digest: str
    verification_digest: str
    cost_receipt_digest: str
    latency_receipt_digest: str
    acceptance_receipt_digest: str
    failure_receipt_digest: Optional[str]
    holoindex_freshness_receipt_digest: str
    pattern_memory_eligible: bool
    pattern_memory_write_performed: bool
    pattern_memory_record_id: Optional[str]
    rejection_reasons: List[str]
    no_command_execution_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerifiedOutcomeRatchetResult:
    decision: str
    accepted: bool
    receipt: VerifiedOutcomeRatchetReceipt
    rejection_reasons: List[str] = field(default_factory=list)
    store_record_id: Optional[str] = None
    no_command_execution_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict()
        return payload


def _digest(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return value
    return {}


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _dedupe(values: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def _contains_secret(value: Any) -> bool:
    text = json.dumps(value, sort_keys=True, default=str).lower()
    return any(marker in text for marker in SECRET_MARKERS)


def _receipt_digest(value: Any) -> str:
    return _digest(_mapping(value) if isinstance(value, Mapping) else value)


def _verification_accepted(verification_result: Mapping[str, Any]) -> bool:
    return (
        verification_result.get("accepted") is True
        and verification_result.get("decision") == AUTONOMOUS_SLICE_VERIFIER_ACCEPT
        and bool(_mapping(verification_result.get("receipt")).get("receipt_id"))
    )


def _publish_accepted(publish_result: Mapping[str, Any]) -> bool:
    if not publish_result:
        return False
    return (
        publish_result.get("accepted") is True
        and publish_result.get("decision") == VERIFIED_DRAFT_PR_PUBLISH_ACCEPT
        and bool(_mapping(publish_result.get("receipt")).get("receipt_id"))
    )


def _holoindex_ok(holoindex_evidence: Mapping[str, Any]) -> bool:
    if holoindex_evidence.get("index_gap_detected") is True:
        return False
    if str(holoindex_evidence.get("retrieval_quality") or "").upper() == "INDEX_GAP":
        return False
    return bool(str(holoindex_evidence.get("holoindex_freshness_receipt_digest") or ""))


def _cost_latency_ok(cost: Mapping[str, Any], latency: Mapping[str, Any]) -> bool:
    for key in ("total_tokens", "estimated_cost_usd"):
        if key not in cost:
            return False
        if float(cost.get(key) or 0) < 0:
            return False
    for key in ("wall_time_ms", "queue_time_ms"):
        if key not in latency:
            return False
        if int(latency.get(key) or 0) < 0:
            return False
    return True


def _build_receipt(
    *,
    request: Mapping[str, Any],
    reasons: List[str],
    pattern_memory_eligible: bool,
    pattern_memory_write_performed: bool,
    pattern_memory_record_id: Optional[str],
) -> VerifiedOutcomeRatchetReceipt:
    verification_result = _mapping(request.get("verification_result"))
    verification_receipt = _mapping(verification_result.get("receipt"))
    publish_result = _mapping(request.get("publish_result"))
    publish_receipt = _mapping(publish_result.get("receipt"))
    cost = _mapping(request.get("cost_receipt"))
    latency = _mapping(request.get("latency_receipt"))
    acceptance = _mapping(request.get("acceptance_receipt"))
    failure = _mapping(request.get("failure_receipt"))
    holoindex = _mapping(request.get("holoindex_evidence"))
    execution_receipts = _list(request.get("execution_receipts"))
    work_order_id = str(
        request.get("work_order_id") or verification_receipt.get("work_order_id") or ""
    )
    slice_name = str(
        request.get("slice_name") or verification_receipt.get("slice_name") or ""
    )
    outcome_status = str(request.get("outcome_status") or "")
    seed = {
        "work_order_id": work_order_id,
        "slice_name": slice_name,
        "outcome_status": outcome_status,
        "verifier_receipt_id": str(verification_receipt.get("receipt_id") or ""),
        "publish_receipt_id": str(publish_receipt.get("receipt_id") or ""),
        "request_digest": _receipt_digest(request.get("request_receipt")),
        "execution_receipts_digest": _digest(execution_receipts),
        "verification_digest": _receipt_digest(verification_result),
        "acceptance_receipt_digest": _receipt_digest(acceptance),
        "failure_receipt_digest": _receipt_digest(failure) if failure else None,
        "rejection_reasons": reasons,
    }
    return VerifiedOutcomeRatchetReceipt(
        ratchet_id="outcome_ratchet_" + _digest(seed).removeprefix("sha256:")[:16],
        work_order_id=work_order_id,
        slice_name=slice_name,
        outcome_status=outcome_status,
        verifier_receipt_id=str(verification_receipt.get("receipt_id") or ""),
        publish_receipt_id=str(publish_receipt.get("receipt_id") or "") or None,
        request_digest=_receipt_digest(request.get("request_receipt")),
        execution_receipts_digest=_digest(execution_receipts),
        verification_digest=_receipt_digest(verification_result),
        cost_receipt_digest=_receipt_digest(cost),
        latency_receipt_digest=_receipt_digest(latency),
        acceptance_receipt_digest=_receipt_digest(acceptance),
        failure_receipt_digest=_receipt_digest(failure) if failure else None,
        holoindex_freshness_receipt_digest=str(
            holoindex.get("holoindex_freshness_receipt_digest") or ""
        ),
        pattern_memory_eligible=pattern_memory_eligible,
        pattern_memory_write_performed=pattern_memory_write_performed,
        pattern_memory_record_id=pattern_memory_record_id,
        rejection_reasons=reasons,
    )


def ratchet_verified_outcome(
    request: Mapping[str, Any],
    *,
    store: OutcomeRatchetStore,
    pattern_memory_sink: Optional[PatternMemorySink] = None,
) -> VerifiedOutcomeRatchetResult:
    """Persist an autonomous-work outcome and gate PatternMemory admission."""
    req = _mapping(request)
    verification_result = _mapping(req.get("verification_result"))
    publish_result = _mapping(req.get("publish_result"))
    execution_receipts = _list(req.get("execution_receipts"))
    cost = _mapping(req.get("cost_receipt"))
    latency = _mapping(req.get("latency_receipt"))
    acceptance = _mapping(req.get("acceptance_receipt"))
    failure = _mapping(req.get("failure_receipt"))
    holoindex = _mapping(req.get("holoindex_evidence"))
    outcome_status = str(req.get("outcome_status") or "")
    reasons: List[str] = []

    if (
        not str(req.get("work_order_id") or "").strip()
        or not str(req.get("slice_name") or "").strip()
    ):
        reasons.append(FAIL_REQUIRED_FIELD)
    verified = _verification_accepted(verification_result)
    published = _publish_accepted(publish_result)
    if not verified:
        reasons.append(FAIL_VERIFICATION_RECEIPT)
    if outcome_status == "accepted" and not published:
        reasons.append(FAIL_PUBLISH_RECEIPT)
    if not execution_receipts or not _mapping(req.get("request_receipt")):
        reasons.append(FAIL_RECEIPT_SET)
    if not acceptance and not failure:
        reasons.append(FAIL_RECEIPT_SET)
    if not _cost_latency_ok(cost, latency):
        reasons.append(FAIL_COST_LATENCY)
    if not _holoindex_ok(holoindex):
        reasons.append(FAIL_HOLOINDEX_EVIDENCE)
    if _contains_secret(
        {
            "request": req.get("request_receipt"),
            "execution": execution_receipts,
            "acceptance": acceptance,
            "failure": failure,
        }
    ):
        reasons.append(FAIL_SECRET_IN_RECEIPT)

    pattern_requested = req.get("enable_pattern_memory_write") is True
    pattern_eligible = verified and published and outcome_status == "accepted"
    if pattern_requested and not pattern_eligible:
        reasons.append(FAIL_PATTERN_MEMORY_UNVERIFIED)

    deduped = _dedupe(reasons)
    pattern_memory_record_id: Optional[str] = None
    pattern_memory_write_performed = False
    receipt = _build_receipt(
        request=req,
        reasons=deduped,
        pattern_memory_eligible=pattern_eligible,
        pattern_memory_write_performed=False,
        pattern_memory_record_id=None,
    )
    if FAIL_SECRET_IN_RECEIPT in deduped:
        return VerifiedOutcomeRatchetResult(
            decision=OUTCOME_RATCHET_REJECT,
            accepted=False,
            receipt=receipt,
            rejection_reasons=deduped,
            store_record_id=None,
        )
    record = {
        "ratchet_id": receipt.ratchet_id,
        "ratchet_receipt": receipt.to_dict(),
        "request_receipt": _mapping(req.get("request_receipt")),
        "execution_receipts": execution_receipts,
        "verification_result": verification_result,
        "publish_result": publish_result,
        "cost_receipt": cost,
        "latency_receipt": latency,
        "acceptance_receipt": acceptance,
        "failure_receipt": failure,
    }

    try:
        store_record_id = store.append(record)
    except Exception:
        deduped = _dedupe([*deduped, FAIL_STORE_WRITE])
        receipt = _build_receipt(
            request=req,
            reasons=deduped,
            pattern_memory_eligible=pattern_eligible,
            pattern_memory_write_performed=False,
            pattern_memory_record_id=None,
        )
        return VerifiedOutcomeRatchetResult(
            decision=OUTCOME_RATCHET_REJECT,
            accepted=False,
            receipt=receipt,
            rejection_reasons=deduped,
            store_record_id=None,
        )

    if not deduped and pattern_requested and pattern_memory_sink is not None:
        try:
            pattern_memory_record_id = pattern_memory_sink.store_verified_outcome(record)
            pattern_memory_write_performed = True
        except Exception:
            deduped = [FAIL_PATTERN_MEMORY_WRITE]

    receipt = _build_receipt(
        request=req,
        reasons=deduped,
        pattern_memory_eligible=pattern_eligible,
        pattern_memory_write_performed=pattern_memory_write_performed,
        pattern_memory_record_id=pattern_memory_record_id,
    )
    return VerifiedOutcomeRatchetResult(
        decision=OUTCOME_RATCHET_RECORDED if not deduped else OUTCOME_RATCHET_REJECT,
        accepted=not deduped,
        receipt=receipt,
        rejection_reasons=deduped,
        store_record_id=store_record_id,
    )


__all__ = [
    "FAIL_COST_LATENCY",
    "FAIL_HOLOINDEX_EVIDENCE",
    "FAIL_PATTERN_MEMORY_UNVERIFIED",
    "FAIL_PATTERN_MEMORY_WRITE",
    "FAIL_PUBLISH_RECEIPT",
    "FAIL_RECEIPT_SET",
    "FAIL_REQUIRED_FIELD",
    "FAIL_SECRET_IN_RECEIPT",
    "FAIL_STORE_WRITE",
    "FAIL_VERIFICATION_RECEIPT",
    "InMemoryOutcomeRatchetStore",
    "JsonlOutcomeRatchetStore",
    "OUTCOME_RATCHET_RECORDED",
    "OUTCOME_RATCHET_REJECT",
    "VerifiedOutcomeRatchetReceipt",
    "VerifiedOutcomeRatchetResult",
    "ratchet_verified_outcome",
]
