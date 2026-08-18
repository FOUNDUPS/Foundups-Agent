"""Scientific Autonomous Self-Healing Operation Contract.

Governed by WSP_00, WSP_15, WSP_50, WSP_80, WSP_97, WSP_109 (Issue #1522).

Foundational Invariants:
1. The entity that proposes a repair must not be the sole authority that
   validates, verifies, or promotes that repair.
2. RedDog does not autonomously "fix errors"; it autonomously conducts
   bounded experiments against authenticated failures, and only
   independently verified experiments may become candidate repairs.
3. Self-healing != self-merging.
"""

from __future__ import annotations

import enum
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "scientific_repair_operation.v1"
BASELINE_RECEIPT_SCHEMA = "scientific_repair_baseline_receipt.v1"
COUNTEREXAMPLE_RECEIPT_SCHEMA = "scientific_repair_counterexample_receipt.v1"
RESEARCH_QUARANTINE_SCHEMA = "scientific_repair_research_quarantine.v1"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class RepairOperationState(str, enum.Enum):
    """Canonical explicit state machine for scientific autonomous self-healing."""

    OBSERVED = "OBSERVED"
    REPRODUCING = "REPRODUCING"
    NON_REPRODUCIBLE = "NON_REPRODUCIBLE"
    REPRODUCED = "REPRODUCED"
    BASELINED = "BASELINED"
    RESEARCHING = "RESEARCHING"
    HYPOTHESIS_DEFINED = "HYPOTHESIS_DEFINED"
    ADMISSION_PENDING = "ADMISSION_PENDING"
    ADMITTED = "ADMITTED"
    SANDBOX_PREPARING = "SANDBOX_PREPARING"
    EXPERIMENTING = "EXPERIMENTING"
    DETERMINISTIC_VERIFY = "DETERMINISTIC_VERIFY"
    INDEPENDENT_VERIFY = "INDEPENDENT_VERIFY"
    FUSION_REVIEW = "FUSION_REVIEW"
    ACCEPTED = "ACCEPTED"
    REVERTED = "REVERTED"
    ABANDONED = "ABANDONED"
    ESCALATED = "ESCALATED"
    LEARNED = "LEARNED"


class NonReproducibleClassification(str, enum.Enum):
    """Classification for observed failures that cannot be independently reproduced."""

    TRANSIENT = "transient"
    ENVIRONMENT_SKEW = "environment_skew"
    OBSERVER_DEFECT = "observer_defect"
    ALREADY_RESOLVED = "already_resolved"
    UNKNOWN_NON_REPRODUCIBLE = "unknown_non_reproducible"


class FinalDisposition(str, enum.Enum):
    """Final decision for an autonomous repair experiment."""

    ACCEPT = "ACCEPT"
    REVERT = "REVERT"
    ABANDON = "ABANDON"
    ESCALATE = "ESCALATE"


class AuthorityTier(str, enum.Enum):
    """Authority tiers controlling mutation and promotion boundaries."""

    TIER_0_PERCEPTION_ONLY = "TIER_0_PERCEPTION_ONLY"
    TIER_1_INTERNAL_MODULE = "TIER_1_INTERNAL_MODULE"
    TIER_2_CROSS_MODULE = "TIER_2_CROSS_MODULE"
    TIER_3_FRAMEWORK_GOVERNANCE = "TIER_3_FRAMEWORK_GOVERNANCE"
    TIER_4_PRODUCTION_EFFECT = "TIER_4_PRODUCTION_EFFECT"


# Explicit, fail-closed state transition table
VALID_STATE_TRANSITIONS: dict[RepairOperationState, frozenset[RepairOperationState]] = {
    RepairOperationState.OBSERVED: frozenset({
        RepairOperationState.REPRODUCING,
        RepairOperationState.ABANDONED,
        RepairOperationState.ESCALATED,
    }),
    RepairOperationState.REPRODUCING: frozenset({
        RepairOperationState.REPRODUCED,
        RepairOperationState.NON_REPRODUCIBLE,
        RepairOperationState.ABANDONED,
        RepairOperationState.ESCALATED,
    }),
    RepairOperationState.NON_REPRODUCIBLE: frozenset({
        RepairOperationState.LEARNED,
        RepairOperationState.ABANDONED,
        RepairOperationState.ESCALATED,
    }),
    RepairOperationState.REPRODUCED: frozenset({
        RepairOperationState.BASELINED,
        RepairOperationState.ABANDONED,
        RepairOperationState.ESCALATED,
    }),
    RepairOperationState.BASELINED: frozenset({
        RepairOperationState.RESEARCHING,
        RepairOperationState.HYPOTHESIS_DEFINED,
        RepairOperationState.ADMISSION_PENDING,
        RepairOperationState.ABANDONED,
        RepairOperationState.ESCALATED,
    }),
    RepairOperationState.RESEARCHING: frozenset({
        RepairOperationState.HYPOTHESIS_DEFINED,
        RepairOperationState.ADMISSION_PENDING,
        RepairOperationState.ABANDONED,
        RepairOperationState.ESCALATED,
    }),
    RepairOperationState.HYPOTHESIS_DEFINED: frozenset({
        RepairOperationState.ADMISSION_PENDING,
        RepairOperationState.ADMITTED,
        RepairOperationState.ABANDONED,
        RepairOperationState.ESCALATED,
    }),
    RepairOperationState.ADMISSION_PENDING: frozenset({
        RepairOperationState.ADMITTED,
        RepairOperationState.ABANDONED,
        RepairOperationState.ESCALATED,
    }),
    RepairOperationState.ADMITTED: frozenset({
        RepairOperationState.SANDBOX_PREPARING,
        RepairOperationState.EXPERIMENTING,
        RepairOperationState.ABANDONED,
        RepairOperationState.ESCALATED,
    }),
    RepairOperationState.SANDBOX_PREPARING: frozenset({
        RepairOperationState.EXPERIMENTING,
        RepairOperationState.ABANDONED,
        RepairOperationState.ESCALATED,
    }),
    RepairOperationState.EXPERIMENTING: frozenset({
        RepairOperationState.DETERMINISTIC_VERIFY,
        RepairOperationState.RESEARCHING,
        RepairOperationState.ABANDONED,
        RepairOperationState.ESCALATED,
    }),
    RepairOperationState.DETERMINISTIC_VERIFY: frozenset({
        RepairOperationState.INDEPENDENT_VERIFY,
        RepairOperationState.EXPERIMENTING,  # Retry on Tier 1 failure
        RepairOperationState.RESEARCHING,    # Targeted research on counterexample
        RepairOperationState.REVERTED,
        RepairOperationState.ABANDONED,
        RepairOperationState.ESCALATED,
    }),
    RepairOperationState.INDEPENDENT_VERIFY: frozenset({
        RepairOperationState.ACCEPTED,
        RepairOperationState.FUSION_REVIEW,  # High-impact tier escalation to jury
        RepairOperationState.EXPERIMENTING,  # Model A bounded revision on rejection
        RepairOperationState.RESEARCHING,    # Targeted research on Model B objection
        RepairOperationState.REVERTED,
        RepairOperationState.ABANDONED,
        RepairOperationState.ESCALATED,
    }),
    RepairOperationState.FUSION_REVIEW: frozenset({
        RepairOperationState.ACCEPTED,
        RepairOperationState.EXPERIMENTING,
        RepairOperationState.REVERTED,
        RepairOperationState.ABANDONED,
        RepairOperationState.ESCALATED,
    }),
    RepairOperationState.ACCEPTED: frozenset({
        RepairOperationState.LEARNED,
    }),
    RepairOperationState.REVERTED: frozenset({
        RepairOperationState.LEARNED,
        RepairOperationState.ABANDONED,
        RepairOperationState.ESCALATED,
    }),
    RepairOperationState.ABANDONED: frozenset({
        RepairOperationState.LEARNED,
    }),
    RepairOperationState.ESCALATED: frozenset({
        RepairOperationState.LEARNED,
    }),
    RepairOperationState.LEARNED: frozenset(),  # Terminal state
}


def _canonical_digest(data: Mapping[str, Any]) -> str:
    """Compute deterministic SHA-256 digest over canonical JSON."""
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


@dataclass(frozen=True)
class BaselineReceipt:
    """Tamper-evident receipt proving independent failure reproduction before mutation."""

    schema_version: str
    failure_id: str
    failing_invariant: str
    head_sha: str
    environment_digest: str
    reproduction_command: str
    exit_code: int
    bounded_log_evidence: str
    relevant_tests: tuple[str, ...]
    authority_declaration: str
    created_at: str
    receipt_digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "failure_id": self.failure_id,
            "failing_invariant": self.failing_invariant,
            "head_sha": self.head_sha,
            "environment_digest": self.environment_digest,
            "reproduction_command": self.reproduction_command,
            "exit_code": self.exit_code,
            "bounded_log_evidence": self.bounded_log_evidence,
            "relevant_tests": list(self.relevant_tests),
            "authority_declaration": self.authority_declaration,
            "created_at": self.created_at,
            "receipt_digest": self.receipt_digest,
        }

    @classmethod
    def create(
        cls,
        *,
        failure_id: str,
        failing_invariant: str,
        head_sha: str,
        environment_digest: str,
        reproduction_command: str,
        exit_code: int,
        bounded_log_evidence: str,
        relevant_tests: Sequence[str] = (),
        authority_declaration: str = "TIER_1_INTERNAL_MODULE",
        created_at: str | None = None,
    ) -> BaselineReceipt:
        timestamp = created_at or datetime.now(UTC).isoformat()
        unsigned = {
            "schema_version": BASELINE_RECEIPT_SCHEMA,
            "failure_id": str(failure_id).strip(),
            "failing_invariant": str(failing_invariant).strip(),
            "head_sha": str(head_sha).strip().lower(),
            "environment_digest": str(environment_digest).strip(),
            "reproduction_command": str(reproduction_command).strip(),
            "exit_code": int(exit_code),
            "bounded_log_evidence": str(bounded_log_evidence)[:16384],
            "relevant_tests": sorted(dict.fromkeys(str(t) for t in relevant_tests)),
            "authority_declaration": str(authority_declaration).strip(),
            "created_at": timestamp,
        }
        digest = _canonical_digest(unsigned)
        return cls(
            schema_version=unsigned["schema_version"],
            failure_id=unsigned["failure_id"],
            failing_invariant=unsigned["failing_invariant"],
            head_sha=unsigned["head_sha"],
            environment_digest=unsigned["environment_digest"],
            reproduction_command=unsigned["reproduction_command"],
            exit_code=unsigned["exit_code"],
            bounded_log_evidence=unsigned["bounded_log_evidence"],
            relevant_tests=tuple(unsigned["relevant_tests"]),
            authority_declaration=unsigned["authority_declaration"],
            created_at=timestamp,
            receipt_digest=digest,
        )

    def verify_integrity(self) -> bool:
        """Verify receipt digest matches canonical content."""
        if not self.receipt_digest or not _SHA256_RE.fullmatch(self.receipt_digest):
            return False
        if not _GIT_SHA_RE.fullmatch(self.head_sha):
            return False
        unsigned = self.to_dict()
        unsigned.pop("receipt_digest", None)
        return _canonical_digest(unsigned) == self.receipt_digest


@dataclass(frozen=True)
class ResearchQuarantineArtifact:
    """Quarantined external research evidence (strictly evidence, never authority)."""

    schema_version: str
    source: str
    retrieval_timestamp: str
    query: str
    content_digest: str
    relevance_score: float
    prompt_injection_isolated: bool
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        *,
        source: str,
        query: str,
        content: str,
        relevance_score: float = 1.0,
        summary: str = "",
        timestamp: str | None = None,
    ) -> ResearchQuarantineArtifact:
        content_bytes = content.encode("utf-8", errors="replace")
        digest = f"sha256:{hashlib.sha256(content_bytes).hexdigest()}"
        return cls(
            schema_version=RESEARCH_QUARANTINE_SCHEMA,
            source=str(source).strip(),
            retrieval_timestamp=timestamp or datetime.now(UTC).isoformat(),
            query=str(query).strip(),
            content_digest=digest,
            relevance_score=max(0.0, min(1.0, float(relevance_score))),
            prompt_injection_isolated=True,
            summary=str(summary)[:4096],
        )


@dataclass(frozen=True)
class CounterexampleReceipt:
    """Structured objection emitted upon Tier 1 or Tier 2 verification rejection."""

    schema_version: str
    objection_id: str
    category: str  # regression | correctness | security | wsp_boundary | complexity
    claim: str
    evidence: str
    failing_scenario: str
    requested_test: str
    severity: str  # low | medium | high | critical
    created_at: str
    receipt_digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "objection_id": self.objection_id,
            "category": self.category,
            "claim": self.claim,
            "evidence": self.evidence,
            "failing_scenario": self.failing_scenario,
            "requested_test": self.requested_test,
            "severity": self.severity,
            "created_at": self.created_at,
            "receipt_digest": self.receipt_digest,
        }

    @classmethod
    def create(
        cls,
        *,
        objection_id: str,
        category: str,
        claim: str,
        evidence: str,
        failing_scenario: str = "",
        requested_test: str = "",
        severity: str = "high",
        created_at: str | None = None,
    ) -> CounterexampleReceipt:
        timestamp = created_at or datetime.now(UTC).isoformat()
        unsigned = {
            "schema_version": COUNTEREXAMPLE_RECEIPT_SCHEMA,
            "objection_id": str(objection_id).strip(),
            "category": str(category).strip(),
            "claim": str(claim).strip(),
            "evidence": str(evidence).strip()[:8192],
            "failing_scenario": str(failing_scenario).strip()[:4096],
            "requested_test": str(requested_test).strip(),
            "severity": str(severity).strip(),
            "created_at": timestamp,
        }
        digest = _canonical_digest(unsigned)
        return cls(
            schema_version=unsigned["schema_version"],
            objection_id=unsigned["objection_id"],
            category=unsigned["category"],
            claim=unsigned["claim"],
            evidence=unsigned["evidence"],
            failing_scenario=unsigned["failing_scenario"],
            requested_test=unsigned["requested_test"],
            severity=unsigned["severity"],
            created_at=timestamp,
            receipt_digest=digest,
        )


@dataclass(frozen=True)
class ExperimentBudget:
    """WSP_15 multidimensional compute and mutation envelope."""

    max_iterations: int = 3
    max_builder_tokens: int = 16000
    max_verifier_tokens: int = 8000
    max_wallclock_seconds: float = 300.0
    max_research_queries: int = 5
    max_files_changed: int = 4
    max_loc_changed: int = 200
    allowed_paths: tuple[str, ...] = ()
    forbidden_paths: tuple[str, ...] = (".env*", "WSP_framework/src/*", "extensions/reddog/*")
    dependency_changes_allowed: bool = False
    network_access_allowed: bool = False
    authority_tier: AuthorityTier = AuthorityTier.TIER_1_INTERNAL_MODULE

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_iterations": self.max_iterations,
            "max_builder_tokens": self.max_builder_tokens,
            "max_verifier_tokens": self.max_verifier_tokens,
            "max_wallclock_seconds": self.max_wallclock_seconds,
            "max_research_queries": self.max_research_queries,
            "max_files_changed": self.max_files_changed,
            "max_loc_changed": self.max_loc_changed,
            "allowed_paths": list(self.allowed_paths),
            "forbidden_paths": list(self.forbidden_paths),
            "dependency_changes_allowed": self.dependency_changes_allowed,
            "network_access_allowed": self.network_access_allowed,
            "authority_tier": self.authority_tier.value,
        }


@dataclass
class ScientificRepairOperation:
    """Top-level durable scientific self-healing state ledger."""

    operation_id: str
    cycle_id: str
    dae_id: str
    failure_id: str
    state: RepairOperationState
    pain: str
    desired_outcome: str
    solution_hypothesis: str = ""
    head_sha: str = ""
    environment_digest: str = ""
    baseline_receipt: BaselineReceipt | None = None
    non_reproducible_classification: NonReproducibleClassification | None = None
    budget: ExperimentBudget = field(default_factory=ExperimentBudget)
    consumed_iterations: int = 0
    consumed_research_queries: int = 0
    selected_scaffold: str = "openclaw"
    selected_builder_model: str = "qwen-coder-7b"
    selected_verifier_model: str = "gemma-270m"
    sandbox_worktree_path: str = ""
    research_artifacts: list[ResearchQuarantineArtifact] = field(default_factory=list)
    counterexamples: list[CounterexampleReceipt] = field(default_factory=list)
    before_measurements: dict[str, Any] = field(default_factory=dict)
    after_measurements: dict[str, Any] = field(default_factory=dict)
    candidate_diff_digest: str = ""
    final_disposition: FinalDisposition | None = None
    disposition_reason: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def can_transition_to(self, new_state: RepairOperationState) -> bool:
        """Check if transition from current state to new_state is allowed."""
        return new_state in VALID_STATE_TRANSITIONS.get(self.state, frozenset())

    def transition_to(self, new_state: RepairOperationState, reason: str = "") -> None:
        """Explicit fail-closed state transition."""
        if not self.can_transition_to(new_state):
            raise ValueError(
                f"Invalid state transition: {self.state.value} -> {new_state.value} "
                f"for operation {self.operation_id}. Allowed: {[s.value for s in VALID_STATE_TRANSITIONS.get(self.state, set())]}"
            )
        self.state = new_state
        self.updated_at = datetime.now(UTC).isoformat()
        if reason:
            self.disposition_reason = reason

    def record_counterexample(self, counterexample: CounterexampleReceipt) -> None:
        """Record an objection and increment consumed iteration count."""
        self.counterexamples.append(counterexample)
        self.consumed_iterations += 1

    def budget_exhausted(self) -> bool:
        """Check if mutation or iteration budget is exhausted."""
        return (
            self.consumed_iterations >= self.budget.max_iterations
            or self.consumed_research_queries > self.budget.max_research_queries
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "operation_id": self.operation_id,
            "cycle_id": self.cycle_id,
            "dae_id": self.dae_id,
            "failure_id": self.failure_id,
            "state": self.state.value,
            "pain": self.pain,
            "desired_outcome": self.desired_outcome,
            "solution_hypothesis": self.solution_hypothesis,
            "head_sha": self.head_sha,
            "environment_digest": self.environment_digest,
            "baseline_receipt": self.baseline_receipt.to_dict() if self.baseline_receipt else None,
            "non_reproducible_classification": self.non_reproducible_classification.value if self.non_reproducible_classification else None,
            "budget": self.budget.to_dict(),
            "consumed_iterations": self.consumed_iterations,
            "consumed_research_queries": self.consumed_research_queries,
            "selected_scaffold": self.selected_scaffold,
            "selected_builder_model": self.selected_builder_model,
            "selected_verifier_model": self.selected_verifier_model,
            "sandbox_worktree_path": self.sandbox_worktree_path,
            "research_artifacts": [a.to_dict() for a in self.research_artifacts],
            "counterexamples": [c.to_dict() for c in self.counterexamples],
            "before_measurements": self.before_measurements,
            "after_measurements": self.after_measurements,
            "candidate_diff_digest": self.candidate_diff_digest,
            "final_disposition": self.final_disposition.value if self.final_disposition else None,
            "disposition_reason": self.disposition_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
