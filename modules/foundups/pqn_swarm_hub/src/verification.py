"""
PQN Swarm Hub - Verification Engine

Accept/reject logic for rESP submissions.
Phase 0: rule-based auto-verifier + manual override path.

Rules (Phase 0 defaults, configurable):
  - coherence >= 0.618 (φ-floor, canonical threshold)
  - pqn_rate > 0.0 (at least one PQN event detected)

WSP 72: Module independence
"""

from typing import Dict, Optional

from .contracts import SubmissionStatus, VerificationDecision, utc_now
from .submission_sink import SubmissionSink


# Phase 0 auto-verification thresholds (012-configurable)
DEFAULT_COHERENCE_FLOOR = 0.618
DEFAULT_PQN_RATE_FLOOR = 0.0


class VerificationEngine:
    """
    Evaluates rESP submissions and emits VerificationDecisions.

    Two paths:
    - auto_verify(): rule-based decision using metric thresholds
    - manual_verify(): explicit accept/reject from a human/agent verifier
    """

    def __init__(
        self,
        sink: SubmissionSink,
        coherence_floor: float = DEFAULT_COHERENCE_FLOOR,
        pqn_rate_floor: float = DEFAULT_PQN_RATE_FLOOR,
    ) -> None:
        self._sink = sink
        self._coherence_floor = coherence_floor
        self._pqn_rate_floor = pqn_rate_floor
        self._store: Dict[str, VerificationDecision] = {}

    def auto_verify(self, submission_id: str) -> VerificationDecision:
        """
        Apply rule-based verification to a submission.

        Accepts if metrics meet thresholds, rejects otherwise.
        """
        sub = self._sink.get(submission_id)
        if sub is None:
            raise KeyError(f"Submission not found: {submission_id}")

        coherence = sub.metrics.get("coherence", 0.0)
        pqn_rate = sub.metrics.get("pqn_rate", 0.0)

        meets_threshold = (
            coherence >= self._coherence_floor
            and pqn_rate > self._pqn_rate_floor
        )

        verdict = "accept" if meets_threshold else "reject"
        rationale = (
            f"coherence={coherence:.3f} (floor={self._coherence_floor}), "
            f"pqn_rate={pqn_rate:.3f} (floor={self._pqn_rate_floor})"
        )
        confidence = min(coherence, 1.0)

        return self._record(
            submission_id=submission_id,
            decision=verdict,
            verifier_id="auto",
            rationale=rationale,
            confidence=confidence,
        )

    def manual_verify(
        self,
        submission_id: str,
        decision: str,
        verifier_id: str,
        rationale: str = "",
    ) -> VerificationDecision:
        """Explicit accept/reject from a human or agent verifier."""
        if decision not in ("accept", "reject"):
            raise ValueError(f"decision must be 'accept' or 'reject', got: {decision!r}")
        sub = self._sink.get(submission_id)
        if sub is None:
            raise KeyError(f"Submission not found: {submission_id}")
        return self._record(
            submission_id=submission_id,
            decision=decision,
            verifier_id=verifier_id,
            rationale=rationale,
        )

    def _record(
        self,
        submission_id: str,
        decision: str,
        verifier_id: str,
        rationale: str,
        confidence: Optional[float] = None,
    ) -> VerificationDecision:
        dec = VerificationDecision(
            submission_id=submission_id,
            decision=decision,
            verifier_id=verifier_id,
            rationale=rationale,
        )
        dec.confidence = confidence
        self._store[dec.decision_id] = dec

        # Update submission status to reflect verdict
        new_status = (
            SubmissionStatus.ACCEPTED
            if decision == "accept"
            else SubmissionStatus.REJECTED
        )
        self._sink.update_status(submission_id, new_status)

        return dec

    def get(self, decision_id: str) -> Optional[VerificationDecision]:
        return self._store.get(decision_id)
