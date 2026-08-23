"""Read-only FoundUp Memex learning-candidate gate.

This module distills scoped evidence into immutable candidate projections. It
does not persist memory, authorize a Brain write, mutate HoloIndex, or grant
work authority. Source authorities retain the evidence needed to reconstruct
each candidate.
"""

from __future__ import annotations

import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.foundup_memex_current_state import (
    FoundUpMemexView,
)
from modules.communication.moltbot_bridge.src.foundup_memex_learning_candidate_contract import (
    CANDIDATE_SCHEMA_VERSION,
    EVIDENCE_SCHEMA_VERSION,
    GATE_ACCEPTED,
    GATE_RECEIPT_SCHEMA_VERSION,
    GATE_REJECTED,
    MAX_GOVERNED_RESEARCH_RECEIPTS,
    MAX_REFERENCES_PER_PROPOSAL,
    MAX_SUPERSEDED_MEMORIES,
    PROPOSAL_SCHEMA_VERSION,
    STRUCTURAL_VERIFICATION,
    FoundUpMemexLearningCandidate,
    FoundUpMemexLearningCandidateGateResult,
    FoundUpMemexLearningEvidence,
    FoundUpMemexLearningProposal,
)
from modules.communication.moltbot_bridge.src.foundup_memex_learning_candidate_validation import (
    candidate_reasons as _candidate_reasons,
    canonical_identifier as _canonical_identifier,
    canonical_text as _canonical_text,
    canonical_time as _canonical_time,
    evidence_reasons as _evidence_reasons,
    evidence_scope_reasons as _evidence_scope_reasons,
    gate_input_reasons as _gate_input_reasons,
    proposal_reasons as _proposal_reasons,
    proposal_scope_reasons as _proposal_scope_reasons,
    sha256_valid,
    time_after as _time_after,
    view_identity_valid as _view_identity_valid,
)


def build_foundup_memex_learning_evidence(
    *, foundup_id: str, snapshot_id: str, source_class: str,
    source_receipt_id: str, source_revision: str, observed_at: str,
    statement: str, polarity: str,
) -> FoundUpMemexLearningEvidence:
    """Build one content-addressed evidence projection."""

    values = (
        foundup_id, snapshot_id, source_class, source_receipt_id,
        source_revision, observed_at, statement, polarity,
    )
    if any(type(value) is not str for value in values):
        raise ValueError("learning_evidence_type_invalid")
    for value in (
        foundup_id, snapshot_id, source_class, source_receipt_id,
        source_revision, polarity,
    ):
        _canonical_identifier(value)
    canonical_statement = _canonical_text(statement)
    payload = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "foundup_id": foundup_id,
        "snapshot_id": snapshot_id,
        "source_class": source_class,
        "source_receipt_id": source_receipt_id,
        "source_revision": source_revision,
        "observed_at": _canonical_time(observed_at),
        "statement": canonical_statement,
        "polarity": polarity,
        "content_digest": _digest({"statement": canonical_statement}),
    }
    evidence = FoundUpMemexLearningEvidence(
        evidence_id=_digest(payload), **payload
    )
    reasons = _evidence_reasons(evidence)
    if reasons:
        raise ValueError(",".join(reasons))
    return evidence


def build_foundup_memex_learning_proposal(
    *, foundup_id: str, snapshot_id: str, category: str, statement: str,
    supporting_evidence_ids: Sequence[str],
    contradicting_evidence_ids: Sequence[str] = (),
    supersedes_memory_ids: Sequence[str] = (),
    proposed_salience: float, proposed_confidence: float, created_at: str,
) -> FoundUpMemexLearningProposal:
    """Build a non-authoritative proposal for the candidate gate."""

    if any(type(value) is not str for value in (foundup_id, snapshot_id, category, statement, created_at)):
        raise ValueError("learning_proposal_type_invalid")
    for value in (foundup_id, snapshot_id, category):
        _canonical_identifier(value)
    support = _bounded_sorted_unique_strings(
        supporting_evidence_ids, MAX_REFERENCES_PER_PROPOSAL
    )
    contradiction = _bounded_sorted_unique_strings(
        contradicting_evidence_ids, MAX_REFERENCES_PER_PROPOSAL
    )
    if len(support) + len(contradiction) > MAX_REFERENCES_PER_PROPOSAL:
        raise ValueError("learning_sequence_count_invalid")
    payload = {
        "schema_version": PROPOSAL_SCHEMA_VERSION,
        "foundup_id": foundup_id,
        "snapshot_id": snapshot_id,
        "category": category,
        "statement": _canonical_text(statement),
        "supporting_evidence_ids": support,
        "contradicting_evidence_ids": contradiction,
        "supersedes_memory_ids": _bounded_sorted_unique_strings(
            supersedes_memory_ids, MAX_SUPERSEDED_MEMORIES
        ),
        "proposed_salience": _canonical_score(proposed_salience),
        "proposed_confidence": _canonical_score(proposed_confidence),
        "created_at": _canonical_time(created_at),
    }
    proposal = FoundUpMemexLearningProposal(
        proposal_id=_digest(payload), **payload
    )
    reasons = _proposal_reasons(proposal)
    if reasons:
        raise ValueError(",".join(reasons))
    return proposal


def gate_foundup_memex_learning_candidates(
    *, view: FoundUpMemexView,
    evidence: Sequence[FoundUpMemexLearningEvidence],
    proposals: Sequence[FoundUpMemexLearningProposal],
    created_at: str,
    governed_research_receipt_ids: Sequence[str] = (),
) -> FoundUpMemexLearningCandidateGateResult:
    """Emit projections; caller research digests never establish authority."""

    try:
        gate_created_at = _canonical_time(created_at)
    except ValueError:
        gate_created_at = created_at
    reasons = _gate_input_reasons(view, evidence, proposals, gate_created_at)
    evidence_items = tuple(evidence) if type(evidence) in (list, tuple) else ()
    proposal_items = tuple(proposals) if type(proposals) in (list, tuple) else ()
    evidence_by_id = {
        item.evidence_id: item
        for item in evidence_items
        if type(item) is FoundUpMemexLearningEvidence
        and type(item.evidence_id) is str
    }
    try:
        research_receipts = _bounded_sorted_unique_strings(
            governed_research_receipt_ids, MAX_GOVERNED_RESEARCH_RECEIPTS
        )
    except ValueError:
        research_receipts = ()
        reasons.append("learning_gate_research_receipt_invalid")
    if any(not sha256_valid(item) for item in research_receipts):
        reasons.append("learning_gate_research_receipt_invalid")
    reasons.extend(_batch_reasons(
        view, evidence_by_id, proposal_items, gate_created_at, research_receipts
    ))
    valid_evidence = tuple(
        item for item in evidence_by_id.values() if not _evidence_reasons(item)
    )
    if reasons:
        return _gate_result(False, view, (), valid_evidence, gate_created_at, reasons)

    candidate_pairs = tuple(
        (proposal, _candidate_from(proposal, evidence_by_id))
        for proposal in proposal_items
    )
    if any(
        not verify_foundup_memex_learning_candidate_reconstruction(
            candidate, proposal, valid_evidence
        )
        for proposal, candidate in candidate_pairs
    ):
        return _gate_result(
            False, view, (), valid_evidence, gate_created_at,
            ["learning_candidate_reconstruction_failed"],
        )
    candidates = tuple(sorted(
        (candidate for _, candidate in candidate_pairs), key=lambda item: item.candidate_id
    ))
    return _gate_result(True, view, candidates, valid_evidence, gate_created_at, [])


def _batch_reasons(
    view: Any,
    evidence_by_id: Mapping[str, FoundUpMemexLearningEvidence],
    proposals: Sequence[Any], gate_created_at: Any,
    research_receipts: tuple[str, ...],
) -> list[str]:
    reasons: list[str] = []
    if type(view) is not FoundUpMemexView or not _view_identity_valid(view):
        return reasons
    for item in evidence_by_id.values():
        item_reasons = _evidence_reasons(item)
        reasons.extend(item_reasons)
        if not item_reasons:
            reasons.extend(_evidence_scope_reasons(item, view, research_receipts))
        if not item_reasons and _time_after(item.observed_at, gate_created_at):
            reasons.append("learning_evidence_observed_in_future")
    for proposal in proposals:
        if type(proposal) is not FoundUpMemexLearningProposal:
            continue
        proposal_reasons = _proposal_reasons(proposal)
        reasons.extend(proposal_reasons)
        if not proposal_reasons:
            reasons.extend(_proposal_scope_reasons(
                proposal, view, evidence_by_id, gate_created_at
            ))
    return reasons


def verify_foundup_memex_learning_candidate_reconstruction(
    candidate: FoundUpMemexLearningCandidate,
    proposal: FoundUpMemexLearningProposal,
    evidence: Sequence[FoundUpMemexLearningEvidence],
) -> bool:
    """Recompute a candidate from its proposal and complete evidence closure."""

    if (
        _candidate_reasons(candidate)
        or _proposal_reasons(proposal)
        or type(evidence) not in (list, tuple)
        or not 0 < len(evidence) <= MAX_REFERENCES_PER_PROPOSAL
        or any(type(item) is not FoundUpMemexLearningEvidence for item in evidence)
    ):
        return False
    valid = tuple(item for item in evidence if not _evidence_reasons(item))
    if len(valid) != len(evidence):
        return False
    by_id = {item.evidence_id: item for item in valid}
    if len(by_id) != len(valid):
        return False
    referenced = proposal.supporting_evidence_ids + proposal.contradicting_evidence_ids
    if any(item not in by_id for item in referenced):
        return False
    if any(by_id[item].polarity != "supporting" for item in proposal.supporting_evidence_ids):
        return False
    if any(by_id[item].polarity != "contradicting" for item in proposal.contradicting_evidence_ids):
        return False
    return candidate == _candidate_from(proposal, by_id)


def _candidate_from(
    proposal: FoundUpMemexLearningProposal,
    evidence_by_id: Mapping[str, FoundUpMemexLearningEvidence],
) -> FoundUpMemexLearningCandidate:
    selected = tuple(
        evidence_by_id[item]
        for item in proposal.supporting_evidence_ids + proposal.contradicting_evidence_ids
    )
    payload = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "proposal_id": proposal.proposal_id,
        "foundup_id": proposal.foundup_id,
        "snapshot_id": proposal.snapshot_id,
        "category": proposal.category,
        "statement": proposal.statement,
        "supporting_evidence_ids": proposal.supporting_evidence_ids,
        "contradicting_evidence_ids": proposal.contradicting_evidence_ids,
        "supersedes_memory_ids": proposal.supersedes_memory_ids,
        "source_receipt_ids": tuple(sorted({item.source_receipt_id for item in selected})),
        "evidence_manifest_digest": _evidence_manifest(selected),
        "proposed_salience": proposal.proposed_salience,
        "proposed_confidence": proposal.proposed_confidence,
        "created_at": proposal.created_at,
        "verification": STRUCTURAL_VERIFICATION,
        "runtime_admissible": False,
        "brain_write_authorized": False,
        "no_persistence_performed": True,
        "no_brain_write_performed": True,
        "no_breadcrumb_write_performed": True,
        "no_holoindex_mutation_performed": True,
        "no_roadmap_mutation_performed": True,
        "no_work_authority_granted": True,
    }
    return FoundUpMemexLearningCandidate(candidate_id=_digest(payload), **payload)


def _gate_result(
    accepted: bool, view: Any,
    candidates: Sequence[FoundUpMemexLearningCandidate],
    evidence: Sequence[FoundUpMemexLearningEvidence], created_at: Any,
    reasons: Sequence[str],
) -> FoundUpMemexLearningCandidateGateResult:
    clean_reasons = tuple(sorted(set(reason for reason in reasons if reason)))
    candidate_values = tuple(candidates)
    evidence_values = tuple(sorted(evidence, key=lambda item: item.evidence_id))
    payload = {
        "schema_version": GATE_RECEIPT_SCHEMA_VERSION,
        "status": GATE_ACCEPTED if accepted else GATE_REJECTED,
        "foundup_id": _strict_string_attr(view, "foundup_id"),
        "snapshot_id": _strict_string_attr(view, "snapshot_id"),
        "snapshot_content_digest": _strict_string_attr(view, "snapshot_content_digest"),
        "memex_view_id": _strict_string_attr(view, "foundup_brain_view_id"),
        "created_at": created_at if type(created_at) is str else "",
        "verification": STRUCTURAL_VERIFICATION,
        "evidence_manifest_digest": _evidence_manifest(evidence_values),
        "candidate_manifest_digest": _digest([item.candidate_id for item in candidate_values]),
        "candidate_count": len(candidate_values),
        "rejection_reasons": clean_reasons,
        "runtime_admissible": False,
        "brain_write_authorized": False,
        "no_persistence_performed": True,
        "no_brain_write_performed": True,
        "no_breadcrumb_write_performed": True,
        "no_holoindex_mutation_performed": True,
        "no_roadmap_mutation_performed": True,
        "no_work_authority_granted": True,
    }
    receipt = {**payload, "receipt_id": _digest(payload)}
    return FoundUpMemexLearningCandidateGateResult(
        accepted=accepted,
        status=payload["status"],
        candidates=candidate_values,
        receipt=MappingProxyType(receipt),
        rejection_reasons=clean_reasons,
    )


def _evidence_manifest(evidence: Sequence[FoundUpMemexLearningEvidence]) -> str:
    return _digest(
        [
            {
                "evidence_id": item.evidence_id,
                "content_digest": item.content_digest,
                "polarity": item.polarity,
                "source_receipt_id": item.source_receipt_id,
            }
            for item in sorted(evidence, key=lambda value: value.evidence_id)
        ]
    )


def _bounded_sorted_unique_strings(
    values: Sequence[str], limit: int,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValueError("learning_sequence_type_invalid")
    if len(values) > limit:
        raise ValueError("learning_sequence_count_invalid")
    if any(type(value) is not str for value in values):
        raise ValueError("learning_sequence_type_invalid")
    return tuple(sorted(set(values)))


def _canonical_score(value: Any) -> float:
    if type(value) not in (int, float):
        raise ValueError("learning_score_type_invalid")
    try:
        return float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError("learning_score_invalid") from exc


def _strict_string_attr(value: Any, name: str) -> str:
    selected = getattr(value, name, "")
    return selected if type(selected) is str else ""


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "CANDIDATE_SCHEMA_VERSION",
    "EVIDENCE_SCHEMA_VERSION",
    "GATE_ACCEPTED",
    "GATE_REJECTED",
    "PROPOSAL_SCHEMA_VERSION",
    "FoundUpMemexLearningCandidate",
    "FoundUpMemexLearningCandidateGateResult",
    "FoundUpMemexLearningEvidence",
    "FoundUpMemexLearningProposal",
    "build_foundup_memex_learning_evidence",
    "build_foundup_memex_learning_proposal",
    "gate_foundup_memex_learning_candidates",
    "verify_foundup_memex_learning_candidate_reconstruction",
]
