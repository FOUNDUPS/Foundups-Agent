"""
PQN Swarm Hub - Contribution Reporter

ROC-style contribution measurement for accepted rESP submissions.
Writes durable artifact to disk.
Phase 0: JSON report file.
Phase 1: Optional SQLite persistence via store injection.

WSP 91: Observability — every accepted contribution emits a durable artifact.
WSP 72: Module independence
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from .contracts import ContributionRecord, utc_now
from .verification import VerificationEngine

if TYPE_CHECKING:
    from .persistence import SQLiteStore


DEFAULT_ARTIFACT_DIR = Path("data/pqn_swarm_hub/contributions")


class ContributionReporter:
    """
    Records ROC-style contribution scores for accepted VerificationDecisions.

    On record(), writes a JSON artifact to DEFAULT_ARTIFACT_DIR.
    Supports both in-memory (Phase 0) and SQLite (Phase 1) storage.
    """

    def __init__(
        self,
        engine: VerificationEngine,
        artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
        store: Optional[SQLiteStore] = None,
    ) -> None:
        """
        Initialize contribution reporter.

        Args:
            engine: VerificationEngine for decision lookup
            artifact_dir: Directory for JSON artifacts
            store: Optional SQLiteStore for persistence. If None, in-memory only.
        """
        self._engine = engine
        self._artifact_dir = artifact_dir
        self._memory: Dict[str, ContributionRecord] = {}
        self._store = store

    def record(
        self,
        work_unit_id: str,
        submission_id: str,
        decision_id: str,
        contributor_id: str,
        score: float,
    ) -> ContributionRecord:
        """
        Record a contribution for an accepted decision.

        Raises ValueError if decision does not exist or was rejected.
        Writes a durable JSON artifact to disk.
        """
        decision = self._engine.get(decision_id)
        if decision is None:
            raise ValueError(f"VerificationDecision not found: {decision_id}")
        if decision.decision != "accept":
            raise ValueError(
                f"Cannot record contribution for rejected decision {decision_id}"
            )

        cr = ContributionRecord(
            work_unit_id=work_unit_id,
            submission_id=submission_id,
            decision_id=decision_id,
            contributor_id=contributor_id,
            score=score,
        )
        self._memory[cr.contribution_id] = cr
        if self._store:
            self._store.save_contribution(cr)
        self._write_artifact(cr)
        return cr

    def get(self, contribution_id: str) -> Optional[ContributionRecord]:
        """Get contribution by ID. Checks memory first, then store."""
        cr = self._memory.get(contribution_id)
        if cr is None and self._store:
            cr = self._store.get_contribution(contribution_id)
            if cr:
                self._memory[contribution_id] = cr  # Cache in memory
        return cr

    def list(
        self,
        contributor_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ContributionRecord]:
        """List contributions. Uses store if available, else memory."""
        if self._store:
            return self._store.list_contributions(
                contributor_id=contributor_id,
                limit=limit,
            )
        items = list(self._memory.values())
        if contributor_id is not None:
            items = [c for c in items if c.contributor_id == contributor_id]
        return sorted(items, key=lambda c: c.recorded_at, reverse=True)[:limit]

    def get_stats(self, contributor_id: str) -> Dict:
        """Return aggregate contribution stats for a contributor."""
        records = self.list(contributor_id=contributor_id)
        if not records:
            return {"contributor_id": contributor_id, "total": 0, "avg_score": 0.0}
        scores = [r.score for r in records]
        return {
            "contributor_id": contributor_id,
            "total": len(scores),
            "avg_score": sum(scores) / len(scores),
            "max_score": max(scores),
        }

    def _write_artifact(self, cr: ContributionRecord) -> Path:
        """Write durable JSON artifact. Returns artifact path."""
        self._artifact_dir.mkdir(parents=True, exist_ok=True)
        path = self._artifact_dir / f"{cr.contribution_id}.json"
        payload = {
            "contribution_id": cr.contribution_id,
            "work_unit_id": cr.work_unit_id,
            "submission_id": cr.submission_id,
            "decision_id": cr.decision_id,
            "contributor_id": cr.contributor_id,
            "score": cr.score,
            "recorded_at": cr.recorded_at.isoformat(),
        }
        path.write_text(json.dumps(payload, indent=2))
        return path
