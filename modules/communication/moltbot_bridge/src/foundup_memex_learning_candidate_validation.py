"""Fail-closed validation for FoundUp Memex learning candidates."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.foundup_memex_current_state import (
    FoundUpMemexView,
)
from modules.communication.moltbot_bridge.src.foundup_memex_learning_candidate_contract import (
    CATEGORIES,
    EVIDENCE_SCHEMA_VERSION,
    MAX_EVIDENCE,
    MAX_PROPOSALS,
    MAX_STATEMENT_CHARS,
    POLARITIES,
    PROPOSAL_SCHEMA_VERSION,
    SOURCE_CLASSES,
    FoundUpMemexLearningEvidence,
    FoundUpMemexLearningProposal,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    redact_runtime_text,
)


_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")


def sha256_valid(value: Any) -> bool:
    return type(value) is str and bool(_SHA256.fullmatch(value))


def gate_input_reasons(
    view: Any, evidence: Any, proposals: Any, created_at: Any,
) -> list[str]:
    reasons: list[str] = []
    if type(view) is not FoundUpMemexView or not view_identity_valid(view):
        reasons.append("learning_gate_view_invalid")
    if type(evidence) not in (list, tuple) or not 0 < len(evidence) <= MAX_EVIDENCE:
        reasons.append("learning_gate_evidence_count_invalid")
    elif any(type(item) is not FoundUpMemexLearningEvidence for item in evidence):
        reasons.append("learning_gate_evidence_type_invalid")
    elif any(type(item.evidence_id) is not str for item in evidence):
        reasons.append("learning_gate_evidence_id_type_invalid")
    elif len({item.evidence_id for item in evidence}) != len(evidence):
        reasons.append("learning_gate_duplicate_evidence")
    if type(proposals) not in (list, tuple) or not 0 < len(proposals) <= MAX_PROPOSALS:
        reasons.append("learning_gate_proposal_count_invalid")
    elif any(type(item) is not FoundUpMemexLearningProposal for item in proposals):
        reasons.append("learning_gate_proposal_type_invalid")
    elif any(type(item.proposal_id) is not str for item in proposals):
        reasons.append("learning_gate_proposal_id_type_invalid")
    elif len({item.proposal_id for item in proposals}) != len(proposals):
        reasons.append("learning_gate_duplicate_proposal")
    if not valid_time(created_at):
        reasons.append("learning_gate_created_at_invalid")
    return reasons


def view_identity_valid(view: Any) -> bool:
    try:
        if (
            type(view) is not FoundUpMemexView
            or not isinstance(view.invariants, Mapping)
            or not view.invariants
            or any(type(value) is not bool or value is not True for value in view.invariants.values())
            or not isinstance(view.assembly_receipt, Mapping)
            or not isinstance(view.source_receipts, Mapping)
        ):
            return False
        content = {
            "schema_version": view.schema_version,
            "foundup_id": view.foundup_id,
            "snapshot_id": view.snapshot_id,
            "snapshot_content_digest": view.snapshot_content_digest,
            "identity": view.identity,
            "current_state": view.current_state,
            "source_receipts": view.source_receipts,
            "roadmap_state": view.roadmap_state,
            "verified_outcomes": view.verified_outcomes,
            "learning_candidates": view.learning_candidates,
            "roadmap_signals": view.roadmap_signals,
            "assembly_receipt": view.assembly_receipt,
        }
        return (
            view.foundup_brain_view_id == _digest(content)
            and view.assembly_receipt.get("foundup_id") == view.foundup_id
            and view.assembly_receipt.get("snapshot_id") == view.snapshot_id
            and view.assembly_receipt.get("snapshot_content_digest") == view.snapshot_content_digest
        )
    except (AttributeError, TypeError, ValueError):
        return False


def evidence_scope_reasons(
    item: FoundUpMemexLearningEvidence, view: FoundUpMemexView,
    research_receipts: tuple[str, ...],
) -> list[str]:
    if item.foundup_id != view.foundup_id or item.snapshot_id != view.snapshot_id:
        return ["learning_evidence_scope_mismatch"]
    if item.source_class == "breadcrumbs":
        receipt = view.source_receipts.get("breadcrumbs")
        if not isinstance(receipt, Mapping):
            return ["learning_evidence_receipt_not_bound"]
        reasons = []
        if item.source_receipt_id != receipt.get("content_digest"):
            reasons.append("learning_evidence_receipt_not_bound")
        if item.source_revision != receipt.get("source_version"):
            reasons.append("learning_evidence_source_revision_mismatch")
        return reasons
    if item.source_class == "governed_research":
        return [] if item.source_receipt_id in research_receipts else [
            "learning_evidence_receipt_not_bound"
        ]
    if item.source_class == "verified_outcome":
        matches = [
            outcome for outcome in view.verified_outcomes
            if isinstance(outcome, Mapping) and item.source_receipt_id in {
                str(outcome.get(name) or "")
                for name in (
                    "content_digest", "evidence_bundle_digest",
                    "verification_receipt_id", "held_out_receipt_id",
                    "signed_receipt_id",
                )
            }
        ]
        if not matches:
            return ["learning_evidence_receipt_not_bound"]
        if all(item.source_revision != str(outcome.get("head_sha") or "") for outcome in matches):
            return ["learning_evidence_source_revision_mismatch"]
        return []
    return ["learning_evidence_source_class_invalid"]


def proposal_scope_reasons(
    proposal: FoundUpMemexLearningProposal, view: FoundUpMemexView,
    evidence_by_id: Mapping[str, FoundUpMemexLearningEvidence],
    gate_created_at: str,
) -> list[str]:
    reasons: list[str] = []
    if proposal.foundup_id != view.foundup_id or proposal.snapshot_id != view.snapshot_id:
        reasons.append("learning_proposal_scope_mismatch")
    support = set(proposal.supporting_evidence_ids)
    contradict = set(proposal.contradicting_evidence_ids)
    if not support or support.intersection(contradict):
        reasons.append("learning_proposal_evidence_partition_invalid")
    if any(item not in evidence_by_id for item in support | contradict):
        reasons.append("learning_proposal_evidence_missing")
    elif any(evidence_by_id[item].polarity != "supporting" for item in support):
        reasons.append("learning_proposal_support_polarity_invalid")
    elif any(evidence_by_id[item].polarity != "contradicting" for item in contradict):
        reasons.append("learning_proposal_contradiction_polarity_invalid")
    if time_after(proposal.created_at, gate_created_at):
        reasons.append("learning_proposal_created_in_future")
    return reasons


def evidence_reasons(item: Any) -> tuple[str, ...]:
    if type(item) is not FoundUpMemexLearningEvidence:
        return ("learning_evidence_type_invalid",)
    values = item.to_dict()
    if any(type(value) is not str for value in values.values()):
        return ("learning_evidence_type_invalid",)
    reasons: list[str] = []
    if item.schema_version != EVIDENCE_SCHEMA_VERSION:
        reasons.append("learning_evidence_schema_invalid")
    if item.source_class not in SOURCE_CLASSES or item.polarity not in POLARITIES:
        reasons.append("learning_evidence_enum_invalid")
    if not all((item.foundup_id, item.snapshot_id, item.source_revision, item.statement.strip())):
        reasons.append("learning_evidence_required_value_missing")
    if not sha256_valid(item.source_receipt_id) or not valid_time(item.observed_at):
        reasons.append("learning_evidence_binding_invalid")
    reasons.extend(_safe_text_reasons(item.statement, "evidence_statement"))
    payload = values
    payload.pop("evidence_id")
    expected_content = _digest({"statement": item.statement})
    payload["content_digest"] = expected_content
    if item.content_digest != expected_content or item.evidence_id != _digest(payload):
        reasons.append("learning_evidence_digest_mismatch")
    return tuple(reasons)


def proposal_reasons(item: Any) -> tuple[str, ...]:
    if type(item) is not FoundUpMemexLearningProposal:
        return ("learning_proposal_type_invalid",)
    string_values = (item.schema_version, item.proposal_id, item.foundup_id, item.snapshot_id,
                     item.category, item.statement, item.created_at)
    if any(type(value) is not str for value in string_values):
        return ("learning_proposal_type_invalid",)
    reasons: list[str] = []
    if item.schema_version != PROPOSAL_SCHEMA_VERSION or item.category not in CATEGORIES:
        reasons.append("learning_proposal_schema_or_category_invalid")
    if not all((item.foundup_id, item.snapshot_id, item.statement.strip())) or not valid_time(item.created_at):
        reasons.append("learning_proposal_required_value_invalid")
    reasons.extend(_safe_text_reasons(item.statement, "proposal_statement"))
    for value, label in (
        (item.supporting_evidence_ids, "support"),
        (item.contradicting_evidence_ids, "contradiction"),
        (item.supersedes_memory_ids, "supersession"),
    ):
        if (
            type(value) is not tuple
            or any(type(entry) is not str for entry in value)
            or value != tuple(sorted(set(value)))
            or any(not sha256_valid(entry) for entry in value)
        ):
            reasons.append(f"learning_proposal_{label}_ids_invalid")
    for value, label in ((item.proposed_salience, "salience"), (item.proposed_confidence, "confidence")):
        if type(value) not in (int, float) or not math.isfinite(value) or not 0.0 <= value <= 1.0:
            reasons.append(f"learning_proposal_{label}_invalid")
    payload = item.to_dict()
    payload.pop("proposal_id")
    if item.proposal_id != _digest(payload):
        reasons.append("learning_proposal_digest_mismatch")
    return tuple(reasons)


def valid_time(value: Any) -> bool:
    if type(value) is not str:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return bool(parsed.tzinfo is not None and parsed.utcoffset() is not None)


def time_after(left: Any, right: Any) -> bool:
    if not valid_time(left) or not valid_time(right):
        return False
    return datetime.fromisoformat(left.replace("Z", "+00:00")) > datetime.fromisoformat(
        right.replace("Z", "+00:00")
    )


def _safe_text_reasons(value: str, field: str) -> list[str]:
    redaction = redact_runtime_text(value, max_chars=MAX_STATEMENT_CHARS)
    reasons: list[str] = []
    if redaction.replacements:
        reasons.append(f"learning_{field}_secret_material_forbidden")
    if redaction.truncated:
        reasons.append(f"learning_{field}_too_long")
    if not redaction.replacements and redaction.text != value:
        reasons.append(f"learning_{field}_not_canonical")
    return reasons


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "evidence_reasons",
    "evidence_scope_reasons",
    "gate_input_reasons",
    "proposal_reasons",
    "proposal_scope_reasons",
    "sha256_valid",
    "time_after",
    "view_identity_valid",
]
