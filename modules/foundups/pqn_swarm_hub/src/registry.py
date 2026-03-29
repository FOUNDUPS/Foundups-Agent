"""
PQN Swarm Hub - Work Unit Registry

Registry for PQNWorkUnit lifecycle management.
Phase 0: in-memory only.
Phase 1: Optional SQLite persistence via store injection.

WSP 72: Module independence (no circular imports)
WSP 84: Code reuse (deterministic IDs from contracts.py)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from .contracts import PQNWorkUnit, WorkUnitStatus, generate_id, utc_now

if TYPE_CHECKING:
    from .persistence import SQLiteStore


class WorkUnitNotFoundError(Exception):
    pass


class InvalidStatusTransitionError(Exception):
    pass


# Valid status transitions
_TRANSITIONS: Dict[WorkUnitStatus, List[WorkUnitStatus]] = {
    WorkUnitStatus.PENDING: [WorkUnitStatus.IN_PROGRESS, WorkUnitStatus.CANCELLED],
    WorkUnitStatus.IN_PROGRESS: [WorkUnitStatus.COMPLETED, WorkUnitStatus.CANCELLED],
    WorkUnitStatus.COMPLETED: [],
    WorkUnitStatus.CANCELLED: [],
}


class WorkUnitRegistry:
    """
    Registry for PQN work units.

    Supports both in-memory (Phase 0) and SQLite (Phase 1) storage.
    Pass store parameter for persistence; omit for in-memory only.
    """

    def __init__(self, store: Optional[SQLiteStore] = None) -> None:
        """
        Initialize registry.

        Args:
            store: Optional SQLiteStore for persistence. If None, in-memory only.
        """
        self._memory: Dict[str, PQNWorkUnit] = {}
        self._store = store

    def register(
        self,
        description: str,
        config: dict,
        creator_id: str,
        source: str = "internal",
    ) -> PQNWorkUnit:
        """
        Register a new bounded PQN work unit.

        Args:
            description: Human-readable work unit description
            config: Configuration dict (detector config, external params, etc.)
            creator_id: ID of the creating agent/participant
            source: Origin of work unit ("internal" for detector, "external" for external)
        """
        unit = PQNWorkUnit(
            description=description,
            config=config,
            creator_id=creator_id,
            source=source,
        )
        self._memory[unit.work_unit_id] = unit
        if self._store:
            self._store.save_work_unit(unit)
        return unit

    def register_external(
        self,
        description: str,
        config: dict,
        creator_id: str,
    ) -> PQNWorkUnit:
        """
        Register an externally-sourced work unit.

        Convenience method for external submissions (non-detector).
        Sets source="external" automatically.

        Args:
            description: Human-readable work unit description
            config: Configuration dict from external source
            creator_id: ID of the external contributor

        Returns:
            PQNWorkUnit with source="external"
        """
        return self.register(
            description=description,
            config=config,
            creator_id=creator_id,
            source="external",
        )

    def get(self, work_unit_id: str) -> PQNWorkUnit:
        """Get work unit by ID. Checks memory first, then store."""
        unit = self._memory.get(work_unit_id)
        if unit is None and self._store:
            unit = self._store.get_work_unit(work_unit_id)
            if unit:
                self._memory[work_unit_id] = unit  # Cache in memory
        if unit is None:
            raise WorkUnitNotFoundError(work_unit_id)
        return unit

    def list(
        self,
        status_filter: Optional[WorkUnitStatus] = None,
        limit: int = 100,
    ) -> List[PQNWorkUnit]:
        """List work units. Uses store if available, else memory."""
        if self._store:
            return self._store.list_work_units(status_filter=status_filter, limit=limit)
        units = list(self._memory.values())
        if status_filter is not None:
            units = [u for u in units if u.status == status_filter]
        return units[:limit]

    def transition(
        self,
        work_unit_id: str,
        new_status: WorkUnitStatus,
    ) -> PQNWorkUnit:
        """Advance work unit to new_status if transition is valid."""
        unit = self.get(work_unit_id)
        allowed = _TRANSITIONS.get(unit.status, [])
        if new_status not in allowed:
            raise InvalidStatusTransitionError(
                f"{unit.status} -> {new_status} is not a valid transition"
            )
        unit.status = new_status
        unit.updated_at = utc_now()
        if self._store:
            self._store.save_work_unit(unit)
        return unit
