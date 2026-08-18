"""Independent Repair Verifier & Context Firewall.

Governed by WSP_00, WSP_50, WSP_80, WSP_97 (Issue #1522 / Slice 2).

Foundational Invariants:
1. The entity that proposes a repair must not be the sole authority that
   validates, verifies, or promotes that repair.
2. Verifier Context Firewall: Model B receives canonical observable evidence,
   shielded from Model A's persuasive narrative, rationale, or scratchpad conclusions.
3. Model Independence: Builder identity != Verifier identity.
"""

from __future__ import annotations

import enum
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from modules.infrastructure.wre_core.src.repair_operation_contract import (
    CounterexampleReceipt,
    FinalDisposition,
)

SCHEMA_VERSION = "independent_repair_verifier_receipt.v1"
EVIDENCE_PACKET_SCHEMA = "verifier_evidence_packet.v1"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

# Disallowed persuasive builder patterns that must be stripped by VerifierContextFirewall
_PERSUASIVE_PATTERNS = [
    re.compile(r"(?i)model\s+a\s+(believes|concluded|thinks|explains|found|suggests)"),
    re.compile(r"(?i)i\s+am\s+confident\s+that"),
    re.compile(r"(?i)this\s+fix\s+is\s+obviously\s+correct"),
    re.compile(r"(?i)<scratchpad>.*?</scratchpad>", re.DOTALL),
    re.compile(r"(?i)<thought>.*?</thought>", re.DOTALL),
    re.compile(r"(?i)<rationale>.*?</rationale>", re.DOTALL),
]


class IndependenceTier(str, enum.Enum):
    """Level of independence achieved between builder and verifier."""

    SAME_FAMILY_SEPARATE_SESSION = "SAME_FAMILY_SEPARATE_SESSION"
    DIFFERENT_MODEL_FAMILY = "DIFFERENT_MODEL_FAMILY"
    MULTI_MODEL_ADVERSARIAL_JURY = "MULTI_MODEL_ADVERSARIAL_JURY"


class VerifierDisposition(str, enum.Enum):
    """Permitted outcomes from an independent verifier evaluation."""

    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
    ESCALATE = "ESCALATE"


def _canonical_digest(data: Mapping[str, Any]) -> str:
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


@dataclass(frozen=True)
class VerifierEvidencePacket:
    """Canonical evidence bundle provided to Model B behind the context firewall."""

    schema_version: str
    pain: str
    desired_outcome: str
    baseline_receipt_id: str
    candidate_diff: str
    changed_files: tuple[str, ...]
    before_measurements: dict[str, Any]
    after_measurements: dict[str, Any]
    required_tests: tuple[str, ...]
    test_results: dict[str, Any]
    research_evidence: tuple[str, ...]
    prior_failed_hypotheses: tuple[str, ...]
    wsp_constraints: tuple[str, ...]
    mutation_budget_consumed: dict[str, Any]
    builder_identity: str = "builder_agent"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "pain": self.pain,
            "desired_outcome": self.desired_outcome,
            "baseline_receipt_id": self.baseline_receipt_id,
            "candidate_diff": self.candidate_diff,
            "changed_files": list(self.changed_files),
            "before_measurements": self.before_measurements,
            "after_measurements": self.after_measurements,
            "required_tests": list(self.required_tests),
            "test_results": self.test_results,
            "research_evidence": list(self.research_evidence),
            "prior_failed_hypotheses": list(self.prior_failed_hypotheses),
            "wsp_constraints": list(self.wsp_constraints),
            "mutation_budget_consumed": self.mutation_budget_consumed,
            "builder_identity": self.builder_identity,
        }


class VerifierContextFirewall:
    """Sanitizes builder output and ensures Model B receives only neutral evidence."""

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Strip builder reasoning, thoughts, and persuasive phrases."""
        sanitized = text
        for pattern in _PERSUASIVE_PATTERNS:
            sanitized = pattern.sub("", sanitized)
        return sanitized.strip()

    @classmethod
    def build_evidence_packet(
        cls,
        *,
        pain: str,
        desired_outcome: str,
        baseline_receipt_id: str,
        candidate_diff: str,
        changed_files: Sequence[str],
        before_measurements: Mapping[str, Any] = None,
        after_measurements: Mapping[str, Any] = None,
        required_tests: Sequence[str] = (),
        test_results: Mapping[str, Any] = None,
        research_evidence: Sequence[str] = (),
        prior_failed_hypotheses: Sequence[str] = (),
        wsp_constraints: Sequence[str] = (),
        mutation_budget_consumed: Mapping[str, Any] = None,
        raw_builder_narrative: str = "",
    ) -> VerifierEvidencePacket:
        """Create sanitized evidence packet, strictly rejecting un-sanitized builder reasoning."""
        return VerifierEvidencePacket(
            schema_version=EVIDENCE_PACKET_SCHEMA,
            pain=cls.sanitize_text(str(pain)),
            desired_outcome=cls.sanitize_text(str(desired_outcome)),
            baseline_receipt_id=str(baseline_receipt_id).strip(),
            candidate_diff=str(candidate_diff),
            changed_files=tuple(sorted(dict.fromkeys(str(f) for f in changed_files))),
            before_measurements=dict(before_measurements or {}),
            after_measurements=dict(after_measurements or {}),
            required_tests=tuple(sorted(dict.fromkeys(str(t) for t in required_tests))),
            test_results=dict(test_results or {}),
            research_evidence=tuple(cls.sanitize_text(str(r)) for r in research_evidence),
            prior_failed_hypotheses=tuple(cls.sanitize_text(str(h)) for h in prior_failed_hypotheses),
            wsp_constraints=tuple(str(w) for w in wsp_constraints),
            mutation_budget_consumed=dict(mutation_budget_consumed or {}),
            builder_identity="builder_model_a",
        )


@dataclass(frozen=True)
class IndependentVerifierReceipt:
    """Tamper-evident receipt proving independent falsification evaluation."""

    schema_version: str
    receipt_id: str
    operation_id: str
    disposition: VerifierDisposition
    verifier_identity: str
    builder_identity: str
    independence_tier: IndependenceTier
    evidence_summary: str
    counterexample: CounterexampleReceipt | None = None
    missing_evidence: str = ""
    evaluated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    receipt_digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "operation_id": self.operation_id,
            "disposition": self.disposition.value,
            "verifier_identity": self.verifier_identity,
            "builder_identity": self.builder_identity,
            "independence_tier": self.independence_tier.value,
            "evidence_summary": self.evidence_summary,
            "counterexample": self.counterexample.to_dict() if self.counterexample else None,
            "missing_evidence": self.missing_evidence,
            "evaluated_at": self.evaluated_at,
            "receipt_digest": self.receipt_digest,
        }

    @classmethod
    def create(
        cls,
        *,
        receipt_id: str,
        operation_id: str,
        disposition: VerifierDisposition,
        verifier_identity: str,
        builder_identity: str,
        independence_tier: IndependenceTier,
        evidence_summary: str,
        counterexample: CounterexampleReceipt | None = None,
        missing_evidence: str = "",
        evaluated_at: str | None = None,
    ) -> IndependentVerifierReceipt:
        timestamp = evaluated_at or datetime.now(UTC).isoformat()
        unsigned = {
            "schema_version": SCHEMA_VERSION,
            "receipt_id": str(receipt_id).strip(),
            "operation_id": str(operation_id).strip(),
            "disposition": disposition.value,
            "verifier_identity": str(verifier_identity).strip(),
            "builder_identity": str(builder_identity).strip(),
            "independence_tier": independence_tier.value,
            "evidence_summary": str(evidence_summary).strip()[:8192],
            "counterexample": counterexample.to_dict() if counterexample else None,
            "missing_evidence": str(missing_evidence).strip()[:4096],
            "evaluated_at": timestamp,
        }
        digest = _canonical_digest(unsigned)
        return cls(
            schema_version=unsigned["schema_version"],
            receipt_id=unsigned["receipt_id"],
            operation_id=unsigned["operation_id"],
            disposition=disposition,
            verifier_identity=unsigned["verifier_identity"],
            builder_identity=unsigned["builder_identity"],
            independence_tier=independence_tier,
            evidence_summary=unsigned["evidence_summary"],
            counterexample=counterexample,
            missing_evidence=unsigned["missing_evidence"],
            evaluated_at=timestamp,
            receipt_digest=digest,
        )

    def verify_integrity(self) -> bool:
        if not self.receipt_digest or not _SHA256_RE.fullmatch(self.receipt_digest):
            return False
        unsigned = self.to_dict()
        unsigned.pop("receipt_digest", None)
        return _canonical_digest(unsigned) == self.receipt_digest


class ModelIndependencePolicy:
    """Enforces builder != verifier separation rules."""

    @classmethod
    def evaluate_independence(
        cls,
        builder_identity: str,
        verifier_identity: str,
        risk_tier: str = "STANDARD",
    ) -> tuple[bool, IndependenceTier, str]:
        """
        Evaluate if proposed verifier satisfies independence policy for given risk tier.

        Returns: (admitted, tier, reason)
        """
        b = str(builder_identity).strip().lower()
        v = str(verifier_identity).strip().lower()

        if b == v:
            return False, IndependenceTier.SAME_FAMILY_SEPARATE_SESSION, "Builder and verifier identities are identical (forbidden)"

        # Check model families
        b_family = b.split("-")[0] if "-" in b else b.split(":")[0]
        v_family = v.split("-")[0] if "-" in v else v.split(":")[0]

        if b_family != v_family:
            tier = IndependenceTier.DIFFERENT_MODEL_FAMILY
            return True, tier, f"Different model families: {b_family} vs {v_family}"

        tier = IndependenceTier.SAME_FAMILY_SEPARATE_SESSION
        if risk_tier in ("HIGH", "CRITICAL", "TIER_3_FRAMEWORK_GOVERNANCE"):
            return False, tier, f"Risk tier {risk_tier} requires DIFFERENT_MODEL_FAMILY (got same family {b_family})"

        return True, tier, f"Same family separate session admitted for risk tier {risk_tier}"
