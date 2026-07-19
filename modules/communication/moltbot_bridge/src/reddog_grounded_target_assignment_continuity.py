"""Validate immutable RedDog grounding receipts across thin-client assignments.

Slice: REDDOG_GROUNDED_TARGET_ASSIGNMENT_CONTINUITY_PHASE1

The receipt binds the work focus, typed target universe, semantic evidence
coverage, and generation-bound HoloIndex proof used by the thin client. It is
integrity evidence, not execution authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "reddog_grounded_target_receipt.v1"
SOURCE_SURFACES = frozenset({"editor_thin_client", "hermes_thin_client", "api_thin_client"})
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class GroundingReason:
    MISSING = "grounding_receipt_missing"
    SCHEMA = "grounding_receipt_schema_invalid"
    RECEIPT_ID = "grounding_receipt_id_invalid"
    SOURCE = "grounding_source_surface_invalid"
    WORK_FOCUS = "grounding_work_focus_mismatch"
    TARGET_DIGEST = "grounding_typed_targets_digest_invalid"
    PREFLIGHT = "grounding_preflight_not_passed"
    TARGET_UNIVERSE = "grounding_target_universe_empty"
    SEMANTIC_COVERAGE = "grounding_semantic_coverage_invalid"
    SEMANTIC_GENERATION = "grounding_semantic_generation_invalid"
    REPO_RECALL = "grounding_repo_recall_invalid"
    COUNTS = "grounding_target_counts_invalid"


@dataclass(frozen=True)
class VerifiedGroundedTargetReceipt:
    receipt: Mapping[str, Any]
    receipt_id: str
    work_focus_digest: str
    typed_targets_digest: str
    repo_file_targets: tuple[str, ...]
    semantic_targets: tuple[str, ...]
    external_research_targets: tuple[str, ...]
    holoindex_generation_id: str
    holoindex_query_receipt_id: str

    def to_dict(self) -> dict[str, Any]:
        return dict(self.receipt)


@dataclass(frozen=True)
class GroundedTargetReceiptValidation:
    accepted: bool
    verified: VerifiedGroundedTargetReceipt | None
    rejection_reasons: tuple[str, ...]


def canonical_digest(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def validate_grounded_target_receipt(
    receipt: Mapping[str, Any] | None,
    *,
    work_focus: str,
    expected_source_surface: str | None = None,
) -> GroundedTargetReceiptValidation:
    reasons: list[str] = []
    if not isinstance(receipt, Mapping):
        return _rejected(GroundingReason.MISSING)
    data = dict(receipt)
    if data.get("schema_version") != SCHEMA_VERSION:
        reasons.append(GroundingReason.SCHEMA)
    source = str(data.get("source_surface") or "").strip()
    if source not in SOURCE_SURFACES or (expected_source_surface and source != expected_source_surface):
        reasons.append(GroundingReason.SOURCE)
    receipt_id = str(data.get("receipt_id") or "")
    payload = dict(data)
    payload.pop("receipt_id", None)
    if not SHA256_RE.fullmatch(receipt_id) or receipt_id != canonical_digest(payload):
        reasons.append(GroundingReason.RECEIPT_ID)
    expected_focus_digest = canonical_digest({"work_focus": str(work_focus or "")})
    if data.get("work_focus_digest") != expected_focus_digest:
        reasons.append(GroundingReason.WORK_FOCUS)

    typed = data.get("typed_targets")
    typed_mapping = dict(typed) if isinstance(typed, Mapping) else {}
    typed_digest = str(data.get("typed_targets_digest") or "")
    if not typed_mapping or typed_digest != canonical_digest(typed_mapping):
        reasons.append(GroundingReason.TARGET_DIGEST)
    targets = _targets(typed_mapping)
    _validate_counts(data, typed_mapping, reasons)
    if data.get("grounding_preflight_applied") is not True or data.get("grounding_preflight_passed") is not True:
        reasons.append(GroundingReason.PREFLIGHT)
    if _strings(data.get("grounding_preflight_rejection_reasons")):
        reasons.append(GroundingReason.PREFLIGHT)
    if data.get("grounding_target_universe_required") is True and not any(targets):
        reasons.append(GroundingReason.TARGET_UNIVERSE)
    _validate_semantic(data, targets[1], reasons)
    _validate_repo(data, targets[0], reasons)
    reasons = list(dict.fromkeys(reasons))
    if reasons:
        return GroundedTargetReceiptValidation(False, None, tuple(reasons))
    verified = VerifiedGroundedTargetReceipt(
        receipt=data,
        receipt_id=receipt_id,
        work_focus_digest=expected_focus_digest,
        typed_targets_digest=typed_digest,
        repo_file_targets=targets[0],
        semantic_targets=targets[1],
        external_research_targets=targets[2],
        holoindex_generation_id=str(data.get("holoindex_generation_id") or ""),
        holoindex_query_receipt_id=str(data.get("holoindex_query_receipt_id") or ""),
    )
    return GroundedTargetReceiptValidation(True, verified, ())


def _targets(typed: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    return (
        _strings(typed.get("repo_file_targets")),
        _strings(typed.get("semantic_targets")),
        _strings(typed.get("external_research_targets")),
    )


def _validate_counts(data: Mapping[str, Any], typed: Mapping[str, Any], reasons: list[str]) -> None:
    expected = {
        "repo_file_targets_count": len(_strings(typed.get("repo_file_targets"))),
        "semantic_targets_count": len(_strings(typed.get("semantic_targets"))),
        "external_research_targets_count": len(_strings(typed.get("external_research_targets"))),
        "quoted_reference_blocks_count": int(typed.get("quoted_reference_blocks_count") or 0),
    }
    if any(_integer(data.get(key)) != value for key, value in expected.items()):
        reasons.append(GroundingReason.COUNTS)


def _validate_semantic(data: Mapping[str, Any], targets: Sequence[str], reasons: list[str]) -> None:
    coverage = data.get("semantic_target_coverage")
    records = tuple(item for item in coverage if isinstance(item, Mapping)) if _sequence(coverage) else ()
    digest = str(data.get("semantic_target_coverage_digest") or "")
    if digest != canonical_digest({"semantic_target_coverage": list(records)}):
        reasons.append(GroundingReason.SEMANTIC_COVERAGE)
    covered = tuple(str(item.get("target") or "") for item in records)
    if tuple(targets) != covered or any(item.get("verdict") != "SUFFICIENT" for item in records):
        reasons.append(GroundingReason.SEMANTIC_COVERAGE)
    if not targets:
        return
    required = (
        data.get("holoindex_owner_query_ok") is True,
        data.get("holoindex_freshness") == "CURRENT",
        data.get("holoindex_index_gap_detected") is False,
        data.get("no_holoindex_reindex_performed") is True,
        SHA256_RE.fullmatch(str(data.get("holoindex_generation_id") or "")) is not None,
        SHA256_RE.fullmatch(str(data.get("holoindex_query_receipt_id") or "")) is not None,
        SHA256_RE.fullmatch(str(data.get("holoindex_freshness_receipt_digest") or "")) is not None,
        bool(str(data.get("holoindex_repo_head_sha") or "").strip()),
    )
    if not all(required):
        reasons.append(GroundingReason.SEMANTIC_GENERATION)


def _validate_repo(data: Mapping[str, Any], targets: Sequence[str], reasons: list[str]) -> None:
    if not targets:
        return
    if data.get("target_recall_ok") is not True or _strings(data.get("required_targets_missing")):
        reasons.append(GroundingReason.REPO_RECALL)


def _strings(value: Any) -> tuple[str, ...]:
    if not _sequence(value):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _integer(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def _rejected(reason: str) -> GroundedTargetReceiptValidation:
    return GroundedTargetReceiptValidation(False, None, (reason,))


__all__ = [
    "GroundedTargetReceiptValidation",
    "GroundingReason",
    "SCHEMA_VERSION",
    "VerifiedGroundedTargetReceipt",
    "canonical_digest",
    "validate_grounded_target_receipt",
]
