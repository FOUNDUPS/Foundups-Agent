"""
PQN Swarm Hub - Contribution Reporter

ROC-style contribution measurement for accepted rESP submissions.
Writes durable artifact to disk. Phase 0: JSON report file.

WSP 91: Observability — every accepted contribution emits a durable artifact.
WSP 72: Module independence
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from .contracts import ContributionRecord, utc_now
from .verification import VerificationEngine


DEFAULT_ARTIFACT_DIR = Path("data/pqn_swarm_hub/contributions")


class ContributionReporter:
    """
    Records ROC-style contribution scores for accepted VerificationDecisions.

    On record(), writes a JSON artifact to DEFAULT_ARTIFACT_DIR.
    Phase 0: in-memory + JSON file. Phase 1 will migrate to SQLite.
    """

    def __init__(
        self,
        engine: VerificationEngine,
        artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
    ) -> None:
        self._engine = engine
        self._artifact_dir = artifact_dir
        self._store: Dict[str, ContributionRecord] = {}

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
        self._store[cr.contribution_id] = cr
        self._write_artifact(cr)
        return cr

    def get(self, contribution_id: str) -> Optional[ContributionRecord]:
        return self._store.get(contribution_id)

    def list(
        self,
        contributor_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ContributionRecord]:
        items = list(self._store.values())
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
