"""Immutable contracts for FoundUp Memex learning-candidate projections."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


EVIDENCE_SCHEMA_VERSION = "foundup_memex_learning_evidence.v1"
PROPOSAL_SCHEMA_VERSION = "foundup_memex_learning_proposal.v1"
CANDIDATE_SCHEMA_VERSION = "foundup_memex_learning_candidate.v1"
GATE_RECEIPT_SCHEMA_VERSION = "foundup_memex_learning_candidate_gate_receipt.v1"
GATE_ACCEPTED = "FOUNDUP_MEMEX_LEARNING_CANDIDATE_GATE_ACCEPTED"
GATE_REJECTED = "FOUNDUP_MEMEX_LEARNING_CANDIDATE_GATE_REJECTED"
STRUCTURAL_VERIFICATION = "STRUCTURAL_ONLY"

SOURCE_CLASSES = frozenset({"breadcrumbs", "verified_outcome", "governed_research"})
POLARITIES = frozenset({"supporting", "contradicting"})
CATEGORIES = frozenset(
    {
        "architectural_principle",
        "decision_history",
        "learned_outcome",
        "observed_pattern",
        "rejected_strategy",
        "unresolved_hypothesis",
    }
)
MAX_EVIDENCE = 256
MAX_PROPOSALS = 64
MAX_REFERENCES_PER_PROPOSAL = 256
MAX_SUPERSEDED_MEMORIES = 64
MAX_GOVERNED_RESEARCH_RECEIPTS = 64
MAX_IDENTIFIER_CHARS = 512
MAX_STATEMENT_CHARS = 4096


@dataclass(frozen=True)
class FoundUpMemexLearningEvidence:
    schema_version: str
    evidence_id: str
    foundup_id: str
    snapshot_id: str
    source_class: str
    source_receipt_id: str
    source_revision: str
    observed_at: str
    statement: str
    polarity: str
    content_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FoundUpMemexLearningProposal:
    schema_version: str
    proposal_id: str
    foundup_id: str
    snapshot_id: str
    category: str
    statement: str
    supporting_evidence_ids: tuple[str, ...]
    contradicting_evidence_ids: tuple[str, ...]
    supersedes_memory_ids: tuple[str, ...]
    proposed_salience: float
    proposed_confidence: float
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FoundUpMemexLearningCandidate:
    schema_version: str
    candidate_id: str
    proposal_id: str
    foundup_id: str
    snapshot_id: str
    category: str
    statement: str
    supporting_evidence_ids: tuple[str, ...]
    contradicting_evidence_ids: tuple[str, ...]
    supersedes_memory_ids: tuple[str, ...]
    source_receipt_ids: tuple[str, ...]
    evidence_manifest_digest: str
    proposed_salience: float
    proposed_confidence: float
    created_at: str
    verification: str = STRUCTURAL_VERIFICATION
    runtime_admissible: bool = False
    brain_write_authorized: bool = False
    no_persistence_performed: bool = True
    no_brain_write_performed: bool = True
    no_breadcrumb_write_performed: bool = True
    no_holoindex_mutation_performed: bool = True
    no_roadmap_mutation_performed: bool = True
    no_work_authority_granted: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FoundUpMemexLearningCandidateGateResult:
    accepted: bool
    status: str
    candidates: tuple[FoundUpMemexLearningCandidate, ...]
    receipt: Mapping[str, Any]
    rejection_reasons: tuple[str, ...]
    no_persistence_performed: bool = True
    no_brain_write_performed: bool = True
    no_breadcrumb_write_performed: bool = True
    no_holoindex_mutation_performed: bool = True
    no_roadmap_mutation_performed: bool = True
    no_work_authority_granted: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "receipt": dict(self.receipt),
            "rejection_reasons": list(self.rejection_reasons),
            "no_persistence_performed": self.no_persistence_performed,
            "no_brain_write_performed": self.no_brain_write_performed,
            "no_breadcrumb_write_performed": self.no_breadcrumb_write_performed,
            "no_holoindex_mutation_performed": self.no_holoindex_mutation_performed,
            "no_roadmap_mutation_performed": self.no_roadmap_mutation_performed,
            "no_work_authority_granted": self.no_work_authority_granted,
        }


__all__ = [
    "CANDIDATE_SCHEMA_VERSION",
    "EVIDENCE_SCHEMA_VERSION",
    "GATE_ACCEPTED",
    "GATE_REJECTED",
    "MAX_GOVERNED_RESEARCH_RECEIPTS",
    "MAX_IDENTIFIER_CHARS",
    "MAX_REFERENCES_PER_PROPOSAL",
    "MAX_SUPERSEDED_MEMORIES",
    "PROPOSAL_SCHEMA_VERSION",
    "FoundUpMemexLearningCandidate",
    "FoundUpMemexLearningCandidateGateResult",
    "FoundUpMemexLearningEvidence",
    "FoundUpMemexLearningProposal",
]
