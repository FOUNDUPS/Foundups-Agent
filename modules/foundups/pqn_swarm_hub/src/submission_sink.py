"""
PQN Swarm Hub - rESP Submission Sink

Accepts structured rESP results for registered work units.
Phase 0: in-memory only. Idempotent via deterministic IDs.

WSP 72: Module independence
WSP 84: Idempotency pattern from moltbook_distribution_adapter
"""

from typing import Dict, List, Optional

from .contracts import (
    SubmissionStatus,
    WorkUnitStatus,
    rESPSubmission,
    utc_now,
)
from .registry import WorkUnitNotFoundError, WorkUnitRegistry


class DuplicateSubmissionError(Exception):
    """Raised when a submission with same ID already exists (idempotent: returns existing)."""


class SubmissionSink:
    """
    Intake point for rESP results against registered work units.

    Validates work unit exists before accepting submission.
    Marks the work unit IN_PROGRESS → COMPLETED on accepted submission.
    """

    def __init__(self, registry: WorkUnitRegistry) -> None:
        self._registry = registry
        self._store: Dict[str, rESPSubmission] = {}

    def submit(
        self,
        work_unit_id: str,
        submitter_id: str,
        metrics: dict,
        artifacts: Optional[List[str]] = None,
    ) -> rESPSubmission:
        """
        Accept an rESP submission for a registered work unit.

        Idempotent: returns existing submission if same IDs would be generated.
        """
        # Validate work unit exists
        unit = self._registry.get(work_unit_id)  # raises WorkUnitNotFoundError

        submission = rESPSubmission(
            work_unit_id=work_unit_id,
            submitter_id=submitter_id,
            metrics=metrics,
            artifacts=artifacts or [],
        )

        # Idempotency: if same ID already exists, return existing
        if submission.submission_id in self._store:
            return self._store[submission.submission_id]

        self._store[submission.submission_id] = submission

        # Advance work unit status if still pending
        if unit.status == WorkUnitStatus.PENDING:
            self._registry.transition(work_unit_id, WorkUnitStatus.IN_PROGRESS)

        return submission

    def get(self, submission_id: str) -> Optional[rESPSubmission]:
        return self._store.get(submission_id)

    def list(
        self,
        work_unit_id: Optional[str] = None,
        status_filter: Optional[SubmissionStatus] = None,
        limit: int = 100,
    ) -> List[rESPSubmission]:
        items = list(self._store.values())
        if work_unit_id is not None:
            items = [s for s in items if s.work_unit_id == work_unit_id]
        if status_filter is not None:
            items = [s for s in items if s.status == status_filter]
        return items[:limit]

    def update_status(
        self,
        submission_id: str,
        new_status: SubmissionStatus,
    ) -> rESPSubmission:
        """Update submission status (called by verification layer)."""
        sub = self._store.get(submission_id)
        if sub is None:
            raise KeyError(f"Submission not found: {submission_id}")
        sub.status = new_status
        return sub
