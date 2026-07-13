"""Held-out regression gate for recursive RedDog/WRE improvement.

Slice: REDDOG_HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_PHASE1

This gate is the last retention check before a recursive improvement outcome
may be admitted to PatternMemory. It does not run tests, write PatternMemory,
execute commands, publish PRs, merge, or re-index HoloIndex. It consumes
receipts produced by earlier independent layers and emits a deterministic
receipt.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional

from modules.infrastructure.wre_core.src.reddog_verified_outcome_ratchet import (
    OUTCOME_RATCHET_RECORDED,
)
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
)

HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT = (
    "HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT"
)
HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_REJECT = (
    "HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_REJECT"
)

FAIL_REQUIRED_FIELD = "FAIL_REQUIRED_FIELD"
FAIL_IMPROVEMENT_JOB_NOT_DRY_RUN_PENDING = "FAIL_IMPROVEMENT_JOB_NOT_DRY_RUN_PENDING"
FAIL_VERIFICATION_RECEIPT = "FAIL_VERIFICATION_RECEIPT"
FAIL_RATCHET_RECEIPT = "FAIL_RATCHET_RECEIPT"
FAIL_HELD_OUT_SUITE = "FAIL_HELD_OUT_SUITE"
FAIL_AUTHOR_GENERATED_SUITE = "FAIL_AUTHOR_GENERATED_SUITE"
FAIL_REGRESSION_FAILED = "FAIL_REGRESSION_FAILED"
FAIL_DIGEST_BINDING = "FAIL_DIGEST_BINDING"
FAIL_HOLOINDEX_EVIDENCE = "FAIL_HOLOINDEX_EVIDENCE"
FAIL_PATTERN_MEMORY_ALREADY_WRITTEN = "FAIL_PATTERN_MEMORY_ALREADY_WRITTEN"
FAIL_SECRET_IN_EVIDENCE = "FAIL_SECRET_IN_EVIDENCE"

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


@dataclass(frozen=True)
class HeldOutRecursiveImprovementRegressionReceipt:
    gate_id: str
    work_order_id: str
    slice_name: str
    improvement_job_id: str
    verifier_receipt_id: str
    ratchet_id: str
    held_out_suite_id: str
    held_out_suite_digest: str
    baseline_digest: str
    candidate_digest: str
    candidate_head_sha: str
    holoindex_freshness_receipt_digest: str
    regression_test_count: int
    pattern_memory_admission_requested: bool
    pattern_memory_admission_allowed: bool
    rejection_reasons: List[str]
    no_command_execution_performed: bool = True
    no_test_execution_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HeldOutRecursiveImprovementRegressionResult:
    decision: str
    accepted: bool
    receipt: HeldOutRecursiveImprovementRegressionReceipt
    rejection_reasons: List[str] = field(default_factory=list)
    pattern_memory_admission_allowed: bool = False
    no_command_execution_performed: bool = True
    no_test_execution_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
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


def _dedupe(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _is_digest(value: Any) -> bool:
    text = str(value or "")
    return (
        text.startswith("sha256:")
        and len(text) == 71
        and all(ch in "0123456789abcdef" for ch in text.removeprefix("sha256:"))
    )


def _is_head_sha(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 40 and all(ch in "0123456789abcdef" for ch in text.lower())


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _contains_secret(value: Any) -> bool:
    text = json.dumps(value, sort_keys=True, default=str).lower()
    return any(marker in text for marker in SECRET_MARKERS)


def _verification_accepted(verification_result: Mapping[str, Any]) -> bool:
    receipt = _mapping(verification_result.get("receipt"))
    return (
        verification_result.get("accepted") is True
        and verification_result.get("decision") == AUTONOMOUS_SLICE_VERIFIER_ACCEPT
        and bool(str(receipt.get("receipt_id") or ""))
        and _is_head_sha(receipt.get("head_sha"))
    )


def _ratchet_recorded_without_pattern_memory(ratchet_result: Mapping[str, Any]) -> bool:
    receipt = _mapping(ratchet_result.get("receipt"))
    return (
        ratchet_result.get("accepted") is True
        and ratchet_result.get("decision") == OUTCOME_RATCHET_RECORDED
        and bool(str(receipt.get("ratchet_id") or ""))
        and receipt.get("pattern_memory_write_performed") is not True
    )


def _holoindex_ok(holoindex_evidence: Mapping[str, Any]) -> bool:
    if holoindex_evidence.get("index_gap_detected") is True:
        return False
    return _is_digest(holoindex_evidence.get("holoindex_freshness_receipt_digest"))


def _job_is_pending_dry_run(improvement_job: Mapping[str, Any]) -> bool:
    return (
        str(improvement_job.get("job_id") or "").strip() != ""
        and str(improvement_job.get("status") or "").lower() == "pending"
        and improvement_job.get("dry_run") is True
    )


def _held_out_suite_ok(
    suite: Mapping[str, Any],
    *,
    verifier_head_sha: str,
    worker_id: str,
) -> tuple[bool, List[str]]:
    reasons: List[str] = []
    test_count = _int(suite.get("test_count"))
    if (
        not str(suite.get("suite_id") or "").strip()
        or suite.get("is_held_out") is not True
        or suite.get("independent") is not True
        or test_count <= 0
    ):
        reasons.append(FAIL_HELD_OUT_SUITE)

    evidence_author = str(suite.get("evidence_author_id") or "")
    if suite.get("generated_by_author") is True or (
        evidence_author and worker_id and evidence_author == worker_id
    ):
        reasons.append(FAIL_AUTHOR_GENERATED_SUITE)

    if suite.get("passed") is not True or _int(suite.get("failure_count")) != 0:
        reasons.append(FAIL_REGRESSION_FAILED)

    if (
        not _is_digest(suite.get("suite_digest"))
        or not _is_digest(suite.get("baseline_digest"))
        or not _is_digest(suite.get("candidate_digest"))
    ):
        reasons.append(FAIL_DIGEST_BINDING)

    candidate_head = str(suite.get("candidate_head_sha") or "")
    if not _is_head_sha(candidate_head) or candidate_head != verifier_head_sha:
        reasons.append(FAIL_DIGEST_BINDING)

    return not reasons, _dedupe(reasons)


def evaluate_held_out_recursive_improvement_regression_gate(
    request: Mapping[str, Any],
) -> HeldOutRecursiveImprovementRegressionResult:
    """Evaluate whether a recursive improvement outcome may be retained.

    The request must contain an `improvement_job`, accepted verifier result,
    accepted outcome-ratchet result, held-out regression evidence, and HoloIndex
    freshness evidence. Acceptance allows a later caller to admit the result to
    PatternMemory. This function never performs that write.
    """
    req = _mapping(request)
    improvement_job = _mapping(req.get("improvement_job"))
    verification_result = _mapping(req.get("verification_result"))
    verification_receipt = _mapping(verification_result.get("receipt"))
    ratchet_result = _mapping(req.get("ratchet_result"))
    ratchet_receipt = _mapping(ratchet_result.get("receipt"))
    held_out_suite = _mapping(req.get("held_out_regression"))
    holoindex_evidence = _mapping(req.get("holoindex_evidence"))

    work_order_id = str(
        req.get("work_order_id")
        or verification_receipt.get("work_order_id")
        or ratchet_receipt.get("work_order_id")
        or ""
    )
    slice_name = str(
        req.get("slice_name")
        or verification_receipt.get("slice_name")
        or ratchet_receipt.get("slice_name")
        or ""
    )
    worker_id = str(
        req.get("worker_id")
        or verification_receipt.get("worker_id")
        or held_out_suite.get("worker_id")
        or ""
    )
    verifier_receipt_id = str(verification_receipt.get("receipt_id") or "")
    verifier_head_sha = str(verification_receipt.get("head_sha") or "")
    ratchet_id = str(ratchet_receipt.get("ratchet_id") or "")
    improvement_job_id = str(improvement_job.get("job_id") or "")
    pattern_requested = req.get("enable_pattern_memory_admission") is True

    reasons: List[str] = []
    if not all([work_order_id, slice_name, improvement_job_id]):
        reasons.append(FAIL_REQUIRED_FIELD)
    if not _job_is_pending_dry_run(improvement_job):
        reasons.append(FAIL_IMPROVEMENT_JOB_NOT_DRY_RUN_PENDING)
    if not _verification_accepted(verification_result):
        reasons.append(FAIL_VERIFICATION_RECEIPT)
    if not _ratchet_recorded_without_pattern_memory(ratchet_result):
        reasons.append(FAIL_RATCHET_RECEIPT)
    if ratchet_receipt.get("pattern_memory_write_performed") is True:
        reasons.append(FAIL_PATTERN_MEMORY_ALREADY_WRITTEN)
    if req.get("pattern_memory_write_performed") is True:
        reasons.append(FAIL_PATTERN_MEMORY_ALREADY_WRITTEN)

    _, suite_reasons = _held_out_suite_ok(
        held_out_suite,
        verifier_head_sha=verifier_head_sha,
        worker_id=worker_id,
    )
    reasons.extend(suite_reasons)

    if not _holoindex_ok(holoindex_evidence):
        reasons.append(FAIL_HOLOINDEX_EVIDENCE)
    if _contains_secret(
        {
            "improvement_job": improvement_job,
            "held_out_regression": held_out_suite,
            "holoindex_evidence": holoindex_evidence,
        }
    ):
        reasons.append(FAIL_SECRET_IN_EVIDENCE)

    deduped = _dedupe(reasons)
    accepted = not deduped
    pattern_allowed = accepted and pattern_requested
    seed = {
        "work_order_id": work_order_id,
        "slice_name": slice_name,
        "improvement_job_id": improvement_job_id,
        "verifier_receipt_id": verifier_receipt_id,
        "ratchet_id": ratchet_id,
        "held_out_suite_id": str(held_out_suite.get("suite_id") or ""),
        "held_out_suite_digest": str(held_out_suite.get("suite_digest") or ""),
        "baseline_digest": str(held_out_suite.get("baseline_digest") or ""),
        "candidate_digest": str(held_out_suite.get("candidate_digest") or ""),
        "candidate_head_sha": str(held_out_suite.get("candidate_head_sha") or ""),
        "holoindex_freshness_receipt_digest": str(
            holoindex_evidence.get("holoindex_freshness_receipt_digest") or ""
        ),
        "pattern_memory_admission_requested": pattern_requested,
        "pattern_memory_admission_allowed": pattern_allowed,
        "rejection_reasons": deduped,
    }
    receipt = HeldOutRecursiveImprovementRegressionReceipt(
        gate_id="held_out_recursive_gate_" + _digest(seed).removeprefix("sha256:")[:16],
        work_order_id=work_order_id,
        slice_name=slice_name,
        improvement_job_id=improvement_job_id,
        verifier_receipt_id=verifier_receipt_id,
        ratchet_id=ratchet_id,
        held_out_suite_id=str(held_out_suite.get("suite_id") or ""),
        held_out_suite_digest=str(held_out_suite.get("suite_digest") or ""),
        baseline_digest=str(held_out_suite.get("baseline_digest") or ""),
        candidate_digest=str(held_out_suite.get("candidate_digest") or ""),
        candidate_head_sha=str(held_out_suite.get("candidate_head_sha") or ""),
        holoindex_freshness_receipt_digest=str(
            holoindex_evidence.get("holoindex_freshness_receipt_digest") or ""
        ),
        regression_test_count=_int(held_out_suite.get("test_count")),
        pattern_memory_admission_requested=pattern_requested,
        pattern_memory_admission_allowed=pattern_allowed,
        rejection_reasons=deduped,
    )
    return HeldOutRecursiveImprovementRegressionResult(
        decision=(
            HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT
            if accepted
            else HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_REJECT
        ),
        accepted=accepted,
        receipt=receipt,
        rejection_reasons=deduped,
        pattern_memory_admission_allowed=pattern_allowed,
    )


__all__ = [
    "FAIL_AUTHOR_GENERATED_SUITE",
    "FAIL_DIGEST_BINDING",
    "FAIL_HELD_OUT_SUITE",
    "FAIL_HOLOINDEX_EVIDENCE",
    "FAIL_IMPROVEMENT_JOB_NOT_DRY_RUN_PENDING",
    "FAIL_PATTERN_MEMORY_ALREADY_WRITTEN",
    "FAIL_RATCHET_RECEIPT",
    "FAIL_REGRESSION_FAILED",
    "FAIL_REQUIRED_FIELD",
    "FAIL_SECRET_IN_EVIDENCE",
    "FAIL_VERIFICATION_RECEIPT",
    "HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT",
    "HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_REJECT",
    "HeldOutRecursiveImprovementRegressionReceipt",
    "HeldOutRecursiveImprovementRegressionResult",
    "evaluate_held_out_recursive_improvement_regression_gate",
]
