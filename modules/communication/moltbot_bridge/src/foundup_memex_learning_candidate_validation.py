"""Fail-closed validation for FoundUp Memex learning candidates."""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.foundup_memex_current_state import (
    FOUNDUP_MEMEX_VIEW_SCHEMA_VERSION,
    FoundUpMemexView,
)
from modules.communication.moltbot_bridge.src.foundup_memex_learning_candidate_contract import (
    CANDIDATE_SCHEMA_VERSION,
    CATEGORIES,
    EVIDENCE_SCHEMA_VERSION,
    MAX_EVIDENCE,
    MAX_IDENTIFIER_CHARS,
    MAX_PROPOSALS,
    MAX_REFERENCES_PER_PROPOSAL,
    MAX_STATEMENT_CHARS,
    MAX_SUPERSEDED_MEMORIES,
    POLARITIES,
    PROPOSAL_SCHEMA_VERSION,
    SOURCE_CLASSES,
    STRUCTURAL_VERIFICATION,
    FoundUpMemexLearningCandidate,
    FoundUpMemexLearningEvidence,
    FoundUpMemexLearningProposal,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    redact_runtime_text,
)


_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
_EXPECTED_VIEW_INVARIANTS = {
    "read_only",
    "no_brain_write",
    "no_breadcrumb_write",
    "no_roadmap_mutation",
    "no_holoindex_mutation",
    "no_queue_mutation",
    "no_worker_spawn",
    "no_repo_mutation",
}
_ASSEMBLY_RECEIPT_FIELDS = {
    "schema_version",
    "foundup_id",
    "snapshot_id",
    "snapshot_content_digest",
    "resident_mode",
    "legacy_single_foundup_compatibility",
    "policy_foundup_scope",
    "included_worker_claims",
    "included_queue_items",
    "excluded_record_count",
    "excluded_record_digest",
    "no_brain_write_performed",
    "no_breadcrumb_write_performed",
    "no_holoindex_mutation_performed",
    "no_queue_mutation_performed",
}


def sha256_valid(value: Any) -> bool:
    return type(value) is str and bool(_SHA256.fullmatch(value))


def canonical_text(value: Any) -> str:
    """Return the one admitted representation for human-authored memory text."""

    if type(value) is not str:
        raise ValueError("learning_text_type_invalid")
    normalized = unicodedata.normalize("NFKC", value).strip()
    if "\x00" in normalized or any(
        ord(char) < 32 and char not in "\n\r\t" for char in normalized
    ):
        raise ValueError("learning_text_control_character_invalid")
    return normalized


def canonical_identifier(value: Any) -> str:
    """Require an authority identifier to already use its canonical form."""

    normalized = canonical_text(value)
    if not normalized or normalized != value or len(normalized) > MAX_IDENTIFIER_CHARS:
        raise ValueError("learning_identifier_not_canonical")
    return normalized


def canonical_time(value: Any) -> str:
    """Normalize an aware ISO timestamp to UTC seconds with a ``Z`` suffix."""

    if type(value) is not str:
        raise ValueError("learning_time_type_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("learning_time_invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None or parsed.microsecond:
        raise ValueError("learning_time_invalid")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


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
            or view.schema_version != FOUNDUP_MEMEX_VIEW_SCHEMA_VERSION
            or not isinstance(view.invariants, Mapping)
            or set(view.invariants) != _EXPECTED_VIEW_INVARIANTS
            or any(value is not True for value in view.invariants.values())
            or not isinstance(view.assembly_receipt, Mapping)
            or not isinstance(view.source_receipts, Mapping)
            or canonical_identifier(view.foundup_id) != view.foundup_id
            or not all(sha256_valid(value) for value in (
                view.foundup_brain_view_id, view.snapshot_id,
                view.snapshot_content_digest,
            ))
        ):
            return False
        receipt = dict(view.assembly_receipt)
        receipt_id = receipt.pop("receipt_id", None)
        if (
            set(receipt) != _ASSEMBLY_RECEIPT_FIELDS
            or receipt.get("schema_version") != "foundup_memex_assembly_receipt.v1"
            or receipt_id != _digest(receipt)
            or receipt.get("foundup_id") != view.foundup_id
            or receipt.get("snapshot_id") != view.snapshot_id
            or receipt.get("snapshot_content_digest") != view.snapshot_content_digest
            or any(
                receipt.get(name) is not True
                for name in (
                    "no_brain_write_performed",
                    "no_breadcrumb_write_performed",
                    "no_holoindex_mutation_performed",
                    "no_queue_mutation_performed",
                )
            )
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
        )
    except (AttributeError, TypeError, ValueError):
        return False


def evidence_scope_reasons(
    item: FoundUpMemexLearningEvidence, view: FoundUpMemexView,
    _research_receipts: tuple[str, ...] = (),
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
        return ["learning_evidence_governed_research_authority_unavailable"]
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
        if len(matches) != 1:
            return ["learning_evidence_receipt_ambiguous"]
        match = matches[0]
        if match.get("accepted") is not True or match.get("held_out_passed") is not True:
            return ["learning_evidence_outcome_not_verified"]
        if item.source_revision != str(match.get("head_sha") or ""):
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
    try:
        for value in (
            item.foundup_id, item.snapshot_id, item.source_class,
            item.source_receipt_id, item.source_revision, item.polarity,
        ):
            canonical_identifier(value)
    except ValueError:
        reasons.append("learning_evidence_identifier_not_canonical")
    if not all((item.foundup_id, item.snapshot_id, item.source_revision, item.statement)):
        reasons.append("learning_evidence_required_value_missing")
    if item.statement != canonical_text(item.statement):
        reasons.append("learning_evidence_statement_not_canonical")
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
    try:
        for value in (item.foundup_id, item.snapshot_id, item.category):
            canonical_identifier(value)
    except ValueError:
        reasons.append("learning_proposal_identifier_not_canonical")
    if not all((item.foundup_id, item.snapshot_id, item.statement)) or not valid_time(item.created_at):
        reasons.append("learning_proposal_required_value_invalid")
    if item.statement != canonical_text(item.statement):
        reasons.append("learning_proposal_statement_not_canonical")
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
    if (
        type(item.supporting_evidence_ids) is tuple
        and type(item.contradicting_evidence_ids) is tuple
        and len(item.supporting_evidence_ids) + len(item.contradicting_evidence_ids)
        > MAX_REFERENCES_PER_PROPOSAL
    ):
        reasons.append("learning_proposal_evidence_count_invalid")
    if (
        type(item.supersedes_memory_ids) is tuple
        and len(item.supersedes_memory_ids) > MAX_SUPERSEDED_MEMORIES
    ):
        reasons.append("learning_proposal_supersession_count_invalid")
    for value, label in ((item.proposed_salience, "salience"), (item.proposed_confidence, "confidence")):
        if type(value) is not float or not math.isfinite(value) or not 0.0 <= value <= 1.0:
            reasons.append(f"learning_proposal_{label}_invalid")
    payload = item.to_dict()
    payload.pop("proposal_id")
    if item.proposal_id != _digest(payload):
        reasons.append("learning_proposal_digest_mismatch")
    return tuple(reasons)


def candidate_reasons(item: Any) -> tuple[str, ...]:
    """Validate a rehydrated candidate before reconstruction comparison."""

    if type(item) is not FoundUpMemexLearningCandidate:
        return ("learning_candidate_type_invalid",)
    strings = (
        item.schema_version, item.candidate_id, item.proposal_id, item.foundup_id,
        item.snapshot_id, item.category, item.statement,
        item.evidence_manifest_digest, item.created_at, item.verification,
    )
    if any(type(value) is not str for value in strings):
        return ("learning_candidate_type_invalid",)
    reasons: list[str] = []
    if item.schema_version != CANDIDATE_SCHEMA_VERSION or item.category not in CATEGORIES:
        reasons.append("learning_candidate_schema_or_category_invalid")
    try:
        for value in (item.foundup_id, item.snapshot_id, item.category):
            canonical_identifier(value)
    except ValueError:
        reasons.append("learning_candidate_identifier_not_canonical")
    if item.verification != STRUCTURAL_VERIFICATION or not valid_time(item.created_at):
        reasons.append("learning_candidate_verification_invalid")
    if item.statement != canonical_text(item.statement):
        reasons.append("learning_candidate_statement_not_canonical")
    for value in (
        item.supporting_evidence_ids, item.contradicting_evidence_ids,
        item.supersedes_memory_ids, item.source_receipt_ids,
    ):
        if (
            type(value) is not tuple
            or value != tuple(sorted(set(value)))
            or any(not sha256_valid(entry) for entry in value)
        ):
            reasons.append("learning_candidate_reference_ids_invalid")
            break
    if not all(sha256_valid(value) for value in (
        item.candidate_id, item.proposal_id, item.evidence_manifest_digest,
    )):
        reasons.append("learning_candidate_digest_invalid")
    for value in (item.proposed_salience, item.proposed_confidence):
        if type(value) is not float or not math.isfinite(value) or not 0.0 <= value <= 1.0:
            reasons.append("learning_candidate_score_invalid")
            break
    if item.runtime_admissible is not False or item.brain_write_authorized is not False:
        reasons.append("learning_candidate_authority_flag_invalid")
    if any(value is not True for value in (
        item.no_persistence_performed, item.no_brain_write_performed,
        item.no_breadcrumb_write_performed, item.no_holoindex_mutation_performed,
        item.no_roadmap_mutation_performed, item.no_work_authority_granted,
    )):
        reasons.append("learning_candidate_read_only_flag_invalid")
    return tuple(reasons)


def valid_time(value: Any) -> bool:
    try:
        return value == canonical_time(value)
    except ValueError:
        return False


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
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "candidate_reasons",
    "canonical_identifier",
    "canonical_text",
    "canonical_time",
    "evidence_reasons",
    "evidence_scope_reasons",
    "gate_input_reasons",
    "proposal_reasons",
    "proposal_scope_reasons",
    "sha256_valid",
    "time_after",
    "view_identity_valid",
]
