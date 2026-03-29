"""
PQN Swarm Hub - rESP Submission Sink

Accepts structured rESP results for registered work units.
Phase 0: in-memory only.
Phase 1: Optional SQLite persistence via store injection.

WSP 72: Module independence
WSP 84: Idempotency pattern from moltbook_distribution_adapter
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from .contracts import (
    SubmissionStatus,
    WorkUnitStatus,
    rESPSubmission,
    utc_now,
)
from .registry import WorkUnitNotFoundError, WorkUnitRegistry

if TYPE_CHECKING:
    from .persistence import SQLiteStore


class DuplicateSubmissionError(Exception):
    """Raised when a submission with same ID already exists (idempotent: returns existing)."""


class SubmissionSink:
    """
    Intake point for rESP results against registered work units.

    Validates work unit exists before accepting submission.
    Marks the work unit IN_PROGRESS → COMPLETED on accepted submission.
    Supports both in-memory (Phase 0) and SQLite (Phase 1) storage.
    """

    def __init__(
        self,
        registry: WorkUnitRegistry,
        store: Optional[SQLiteStore] = None,
    ) -> None:
        """
        Initialize submission sink.

        Args:
            registry: WorkUnitRegistry for work unit validation
            store: Optional SQLiteStore for persistence. If None, in-memory only.
        """
        self._registry = registry
        self._memory: Dict[str, rESPSubmission] = {}
        self._store = store

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

        # Idempotency: check memory then store
        existing = self.get(submission.submission_id)
        if existing:
            return existing

        self._memory[submission.submission_id] = submission
        if self._store:
            self._store.save_submission(submission)

        # Advance work unit status if still pending
        if unit.status == WorkUnitStatus.PENDING:
            self._registry.transition(work_unit_id, WorkUnitStatus.IN_PROGRESS)

        return submission

    def get(self, submission_id: str) -> Optional[rESPSubmission]:
        """Get submission by ID. Checks memory first, then store."""
        sub = self._memory.get(submission_id)
        if sub is None and self._store:
            sub = self._store.get_submission(submission_id)
            if sub:
                self._memory[submission_id] = sub  # Cache in memory
        return sub

    def list(
        self,
        work_unit_id: Optional[str] = None,
        status_filter: Optional[SubmissionStatus] = None,
        limit: int = 100,
    ) -> List[rESPSubmission]:
        """List submissions. Uses store if available, else memory."""
        if self._store:
            return self._store.list_submissions(
                work_unit_id=work_unit_id,
                status_filter=status_filter,
                limit=limit,
            )
        items = list(self._memory.values())
        if work_unit_id is not None:
            items = [s for s in items if s.work_unit_id == work_unit_id]
        if status_filter is not None:
            items = [s for s in items if s.status == status_filter]
        return items[:limit]

    def submit_from_detector(
        self,
        work_unit_id: str,
        bridge_result: dict,
        submitter_id: str,
    ) -> rESPSubmission:
        """
        Accept an rESP submission from DetectorBridge output.

        Extracts metrics and artifact paths from bridge_result.
        Phase 1: Bridges detector output to submission flow.

        Args:
            work_unit_id: ID of the work unit
            bridge_result: Dict from DetectorBridge.run() containing:
                - metrics: {coherence, pqn_rate, paradox_rate, resonance_hz, ...}
                - events_path: str path to JSONL
                - metrics_csv: str path to CSV
            submitter_id: ID of the submitting agent

        Returns:
            rESPSubmission with metrics and artifact paths
        """
        metrics = bridge_result.get("metrics", {})
        artifacts = []
        if bridge_result.get("events_path"):
            artifacts.append(bridge_result["events_path"])
        if bridge_result.get("metrics_csv"):
            artifacts.append(bridge_result["metrics_csv"])

        return self.submit(
            work_unit_id=work_unit_id,
            submitter_id=submitter_id,
            metrics=metrics,
            artifacts=artifacts,
        )

    def update_status(
        self,
        submission_id: str,
        new_status: SubmissionStatus,
    ) -> rESPSubmission:
        """Update submission status (called by verification layer)."""
        sub = self.get(submission_id)
        if sub is None:
            raise KeyError(f"Submission not found: {submission_id}")
        sub.status = new_status
        self._memory[submission_id] = sub
        if self._store:
            self._store.save_submission(sub)
        return sub
