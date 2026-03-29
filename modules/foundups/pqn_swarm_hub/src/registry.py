"""
PQN Swarm Hub - Work Unit Registry

In-memory registry for PQNWorkUnit lifecycle management.
Phase 0: in-memory only. Phase 1 will add SQLite persistence.

WSP 72: Module independence (no circular imports)
WSP 84: Code reuse (deterministic IDs from contracts.py)
"""

from typing import Dict, List, Optional

from .contracts import PQNWorkUnit, WorkUnitStatus, generate_id, utc_now


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
    In-memory registry for PQN work units.

    Single source of truth for work unit state within this PoC.
    Not thread-safe in Phase 0.
    """

    def __init__(self) -> None:
        self._store: Dict[str, PQNWorkUnit] = {}

    def register(
        self,
        description: str,
        config: dict,
        creator_id: str,
    ) -> PQNWorkUnit:
        """Register a new bounded PQN work unit."""
        unit = PQNWorkUnit(
            description=description,
            config=config,
            creator_id=creator_id,
        )
        self._store[unit.work_unit_id] = unit
        return unit

    def get(self, work_unit_id: str) -> PQNWorkUnit:
        unit = self._store.get(work_unit_id)
        if unit is None:
            raise WorkUnitNotFoundError(work_unit_id)
        return unit

    def list(
        self,
        status_filter: Optional[WorkUnitStatus] = None,
        limit: int = 100,
    ) -> List[PQNWorkUnit]:
        units = list(self._store.values())
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
        return unit
