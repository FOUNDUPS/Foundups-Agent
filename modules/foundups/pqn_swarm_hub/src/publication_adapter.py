"""
PQN Swarm Hub - Publication Adapter

Bounded adapter for publishing verified contributions to MoltBook.
Wraps moltbook_distribution_adapter.publish_research() without duplicating logic.

WSP 72: Module independence
WSP 91: Observability — publication events are traceable

HARD BOUNDARY:
- Owns: formatting PQN contribution data for MoltBook
- Does NOT own: retry logic, Discord webhooks (moltbook_distribution_adapter)
- Stub-safe: graceful fallback if MoltBook unavailable
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from .contracts import (
    ContributionRecord,
    PQNWorkUnit,
    VerificationDecision,
    rESPSubmission,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger("pqn_swarm_hub.publication_adapter")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PublicationResult:
    """Result of a publication attempt."""

    success: bool
    post_id: Optional[str]
    channel: Optional[str]
    status: str  # "published", "failed", "rejected_decision", "stub"
    message: str
    timestamp: datetime
    duplicate: bool = False


class PublicationAdapterError(Exception):
    """Raised when publication adapter operation fails."""

    pass


class PublicationAdapter:
    """
    Bounded adapter for publishing verified PQN contributions to MoltBook.

    Wraps moltbook_distribution_adapter without duplicating distribution logic.
    Provides stub-safe fallback if MoltBook is unavailable.

    Phase 1: publish_research() via MoltBook adapter
    Proto+: Stable interface for exfoliated repo
    """

    def __init__(
        self,
        moltbook_module_path: str = "modules.communication.moltbot_bridge.src.moltbook_distribution_adapter",
        auto_connect: bool = False,
    ) -> None:
        """
        Initialize publication adapter.

        Args:
            moltbook_module_path: Import path to moltbook_distribution_adapter
            auto_connect: If True, attempt connection on init
        """
        self._moltbook_module_path = moltbook_module_path
        self._moltbook_adapter = None
        self._connected = False
        self._stub_publications: List[Dict[str, Any]] = []

        if auto_connect:
            self.connect()

    def connect(self) -> bool:
        """
        Connect to MoltBook distribution adapter.

        Returns True if connected, False if stub mode.
        Does not raise — caller decides how to handle.
        """
        if self._connected:
            return True

        try:
            from modules.communication.moltbot_bridge.src.moltbook_distribution_adapter import (
                get_moltbook_adapter,
            )

            self._moltbook_adapter = get_moltbook_adapter()
            self._connected = True
            logger.info("[PQN-PUB] Connected to MoltBook adapter")
            return True
        except ImportError as e:
            logger.warning("[PQN-PUB] MoltBook adapter not available: %s", e)
            self._connected = False
            return False
        except Exception as e:
            logger.warning("[PQN-PUB] MoltBook connection failed: %s", e)
            self._connected = False
            return False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def publish(
        self,
        work_unit: PQNWorkUnit,
        submission: rESPSubmission,
        decision: VerificationDecision,
        contribution: ContributionRecord,
        actor_id: str = "pqn_swarm_hub",
    ) -> PublicationResult:
        """
        Publish a verified contribution to MoltBook.

        Only publishes if decision is "accept". Rejected decisions
        return immediately with status="rejected_decision".

        Args:
            work_unit: The PQNWorkUnit that was worked on
            submission: The rESPSubmission with metrics/artifacts
            decision: The VerificationDecision (must be "accept")
            contribution: The ContributionRecord to publish
            actor_id: Actor performing the publication

        Returns:
            PublicationResult with success/failure info
        """
        timestamp = utc_now()

        # Gate: only publish accepted decisions
        if decision.decision != "accept":
            logger.info(
                "[PQN-PUB] Skipping publication for rejected decision: %s",
                decision.decision_id,
            )
            return PublicationResult(
                success=False,
                post_id=None,
                channel=None,
                status="rejected_decision",
                message=f"Decision was '{decision.decision}', not 'accept'",
                timestamp=timestamp,
            )

        # Format payload for MoltBook
        payload = self._format_payload(work_unit, submission, decision, contribution)

        # Attempt connection if not connected
        if not self._connected:
            self.connect()

        # Publish via MoltBook or stub
        if self._connected and self._moltbook_adapter:
            return self._publish_via_moltbook(payload, actor_id, timestamp)
        else:
            return self._stub_publish(payload, actor_id, timestamp)

    def _format_payload(
        self,
        work_unit: PQNWorkUnit,
        submission: rESPSubmission,
        decision: VerificationDecision,
        contribution: ContributionRecord,
    ) -> Dict[str, Any]:
        """
        Format PQN data for MoltBook publish_research().

        Maps:
            research_id <- contribution_id
            topic <- work_unit description
            content <- formatted markdown
            metadata <- submission metrics + score + artifacts
        """
        # Extract key metrics for display
        coherence = submission.metrics.get("coherence", 0.0)
        pqn_rate = submission.metrics.get("pqn_rate", 0.0)
        resonance_hz = submission.metrics.get("resonance_hz", 7.05)

        # Format markdown content
        content = f"""## PQN Swarm Hub Contribution

**Work Unit**: {work_unit.work_unit_id}
**Contributor**: {contribution.contributor_id}
**Score**: {contribution.score:.3f}

### Metrics
- Coherence: {coherence:.4f}
- PQN Rate: {pqn_rate:.4f}
- Resonance: {resonance_hz:.2f} Hz

### Verification
- Decision: {decision.decision}
- Verifier: {decision.verifier_id}
- Rationale: {decision.rationale}
"""

        # Add artifacts if present
        if submission.artifacts:
            content += "\n### Artifacts\n"
            for artifact in submission.artifacts[:5]:  # Limit to 5
                content += f"- `{artifact}`\n"

        return {
            "research_id": contribution.contribution_id,
            "topic": f"PQN: {work_unit.description[:80]}",
            "content": content,
            "metadata": {
                "work_unit_id": work_unit.work_unit_id,
                "submission_id": submission.submission_id,
                "decision_id": decision.decision_id,
                "contribution_id": contribution.contribution_id,
                "contributor_id": contribution.contributor_id,
                "score": contribution.score,
                "coherence": coherence,
                "pqn_rate": pqn_rate,
                "resonance_hz": resonance_hz,
                "artifacts": submission.artifacts[:5] if submission.artifacts else [],
                "source": "pqn_swarm_hub",
            },
        }

    def _publish_via_moltbook(
        self,
        payload: Dict[str, Any],
        actor_id: str,
        timestamp: datetime,
    ) -> PublicationResult:
        """Publish via MoltBook adapter."""
        try:
            result = self._moltbook_adapter.publish_research(
                research_id=payload["research_id"],
                topic=payload["topic"],
                content=payload["content"],
                metadata=payload["metadata"],
                actor_id=actor_id,
            )

            success = result.get("status") in ("published", "pending")
            duplicate = result.get("duplicate", False)

            logger.info(
                "[PQN-PUB] MoltBook publish %s | post_id=%s duplicate=%s",
                "success" if success else "failed",
                result.get("post_id"),
                duplicate,
            )

            return PublicationResult(
                success=success,
                post_id=result.get("post_id"),
                channel=result.get("channel"),
                status=result.get("status", "unknown"),
                message="Published to MoltBook" if success else "MoltBook publish failed",
                timestamp=timestamp,
                duplicate=duplicate,
            )

        except Exception as e:
            logger.error("[PQN-PUB] MoltBook publish error: %s", e)
            return PublicationResult(
                success=False,
                post_id=None,
                channel=None,
                status="failed",
                message=f"MoltBook error: {e}",
                timestamp=timestamp,
            )

    def _stub_publish(
        self,
        payload: Dict[str, Any],
        actor_id: str,
        timestamp: datetime,
    ) -> PublicationResult:
        """
        Stub publish when MoltBook is unavailable.

        Records publication locally for later sync.
        Returns deterministic success (no crash).
        """
        stub_record = {
            "payload": payload,
            "actor_id": actor_id,
            "timestamp": timestamp.isoformat(),
            "stub": True,
        }
        self._stub_publications.append(stub_record)

        logger.info(
            "[PQN-PUB] STUB publish for contribution %s (MoltBook unavailable)",
            payload["research_id"],
        )

        return PublicationResult(
            success=True,
            post_id=f"stub_{payload['research_id']}",
            channel="stub",
            status="stub",
            message="Recorded locally (MoltBook unavailable)",
            timestamp=timestamp,
        )

    def get_stub_publications(self) -> List[Dict[str, Any]]:
        """Return list of stub publications (for later sync)."""
        return list(self._stub_publications)

    def clear_stub_publications(self) -> int:
        """Clear stub publications after sync. Returns count cleared."""
        count = len(self._stub_publications)
        self._stub_publications.clear()
        return count

    def get_status(self) -> Dict[str, Any]:
        """Return adapter status."""
        return {
            "connected": self._connected,
            "moltbook_module_path": self._moltbook_module_path,
            "stub_publications_pending": len(self._stub_publications),
        }


# Singleton instance
_publication_adapter: Optional[PublicationAdapter] = None


def get_publication_adapter(auto_connect: bool = False) -> PublicationAdapter:
    """
    Get singleton PublicationAdapter instance.

    Args:
        auto_connect: If True, attempt MoltBook connection on first access

    Returns:
        PublicationAdapter singleton
    """
    global _publication_adapter
    if _publication_adapter is None:
        _publication_adapter = PublicationAdapter(auto_connect=auto_connect)
    return _publication_adapter


def reset_publication_adapter() -> None:
    """Reset singleton for testing."""
    global _publication_adapter
    _publication_adapter = None
