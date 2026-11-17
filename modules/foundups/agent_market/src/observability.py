"""Persistent Observability Service for FoundUps Agent Market.

Implements ObservabilityService interface with SQLite persistence.
Provides structured event logging and querying for audit trail.

WSP References:
- WSP 11: Implements ObservabilityService interface contract
- WSP 30: Persistence layer integration
- WSP 83: Observability and logging standards
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .interfaces import ObservabilityService
from .models import EventRecord
from .persistence.sqlite_adapter import SQLiteAdapter

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_event_id() -> str:
    return f"evt_{uuid.uuid4().hex[:12]}"


class PersistentObservability(ObservabilityService):
    """Persistent implementation of ObservabilityService.

    Logs structured events to SQLite for audit trail and querying.

    Event Types:
        - foundup.created, foundup.updated
        - task.created, task.claimed
        - proof.submitted, proof.verified, proof.rejected
        - payout.initiated, payout.completed
        - cabr.input, cabr.output
        - distribution.published

    Example:
        adapter = SQLiteAdapter()
        obs = PersistentObservability(adapter)
        obs.emit_event("task.created", "user_123", {"task_id": "tsk_abc"})
    """

    def __init__(self, adapter: SQLiteAdapter) -> None:
        """Initialize with SQLite adapter.

        Args:
            adapter: SQLiteAdapter instance for persistence.
        """
        self._adapter = adapter

    def emit_event(
        self,
        event_type: str,
        actor_id: str,
        payload: Dict[str, Any],
        foundup_id: Optional[str] = None,
        task_id: Optional[str] = None,
        proof_id: Optional[str] = None,
        payout_id: Optional[str] = None,
    ) -> None:
        """Emit a structured event.

        Args:
            event_type: Type of event (e.g., "task.created").
            actor_id: ID of actor performing the action.
            payload: Event-specific data.
            foundup_id: Optional Foundup context.
            task_id: Optional Task context.
            proof_id: Optional Proof context.
            payout_id: Optional Payout context.
        """
        event = EventRecord(
            event_id=_generate_event_id(),
            event_type=event_type,
            actor_id=actor_id,
            payload=payload,
            foundup_id=foundup_id,
            task_id=task_id,
            proof_id=proof_id,
            payout_id=payout_id,
            timestamp=_utc_now(),
        )
        self._adapter.create_event(event)
        logger.debug(
            "Event emitted: %s by %s (foundup=%s, task=%s)",
            event_type,
            actor_id,
            foundup_id,
            task_id,
        )

    def query_events(
        self,
        foundup_id: Optional[str] = None,
        task_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, object]]:
        """Query events with optional filters.

        Args:
            foundup_id: Filter by Foundup.
            task_id: Filter by Task.
            event_type: Filter by event type.
            limit: Maximum events to return.

        Returns:
            List of event dicts.
        """
        events = self._adapter.query_events(
            foundup_id=foundup_id,
            task_id=task_id,
            event_type=event_type,
            limit=limit,
        )
        return [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "actor_id": e.actor_id,
                "payload": e.payload,
                "foundup_id": e.foundup_id,
                "task_id": e.task_id,
                "proof_id": e.proof_id,
                "payout_id": e.payout_id,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ]

    def get_audit_trail(self, foundup_id: str, limit: int = 100) -> List[Dict[str, object]]:
        """Get full audit trail for a Foundup.

        Args:
            foundup_id: Foundup to get audit trail for.
            limit: Maximum events to return.

        Returns:
            List of event dicts ordered by timestamp desc.
        """
        return self.query_events(foundup_id=foundup_id, limit=limit)


# Keep stub for backwards compatibility
class ObservabilityStub(ObservabilityService):
    """Stub implementation for testing (deprecated, use PersistentObservability)."""

    pass
