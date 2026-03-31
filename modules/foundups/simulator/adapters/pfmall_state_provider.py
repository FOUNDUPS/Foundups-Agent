#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
p.fMALL State Overlay Provider - Simulator PoC Implementation

Implements the StateOverlayProvider protocol backed by simulator state.
This is a PoC adapter - production will use pAVS services.

Architecture:
  - Consumes SimulatorState from StateStore
  - Translates to FoundUpStateOverlay per PFMALL_STATE_OVERLAY_CONTRACT.md
  - Single adapter boundary - simulator internals do not leak

WSP Compliance:
  WSP 11  : Interface contract (provider protocol)
  WSP 72  : Module independence (adapter pattern)
  WSP 84  : Code Reuse (reuses state_store)

Contract Reference:
  - modules/foundups/docs/PFMALL_STATE_OVERLAY_CONTRACT.md
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..state_store import StateStore, SimulatorState, FoundUpTile

logger = logging.getLogger("pfmall_state_provider")


# ---------------------------------------------------------------------------
# Stage Mapping (reverse of STAGE_TO_INT from state_contracts.py)
# ---------------------------------------------------------------------------

INT_TO_STAGE = {
    0: "Idea",
    1: "PoC",
    2: "Soft-Proto",
    3: "Proto",
    4: "MVP",
    5: "Launch",
}


# ---------------------------------------------------------------------------
# FoundUpStateOverlay (matches pfmall_catalog.py exactly)
# ---------------------------------------------------------------------------

@dataclass
class FoundUpStateOverlay:
    """Dynamic state overlay for a FoundUp.

    Per PFMALL_STATE_OVERLAY_CONTRACT.md Section 3.
    """

    foundup_id: str
    health_status: str = "unknown"  # healthy | degraded | offline | unknown
    availability: str = "unknown"   # online | maintenance | suspended
    cabr_score: float = 0.0
    cabr_trend: str = "unknown"     # rising | stable | falling | unknown
    lifecycle_progress: Dict[str, Any] = field(default_factory=dict)
    agent_activity: Dict[str, Any] = field(default_factory=dict)
    reserve_summary: Dict[str, Any] = field(default_factory=dict)
    last_updated_at: str = ""
    state_provider: str = "none"
    freshness_ttl: int = 0


# ---------------------------------------------------------------------------
# Simulator State Provider (PoC)
# ---------------------------------------------------------------------------

class SimulatorStateProvider:
    """
    StateOverlayProvider implementation backed by the FoundUps simulator.

    This is a PoC provider per PFMALL_STATE_OVERLAY_CONTRACT.md Section 4.3.
    Production deployments will use pAVS services instead.

    Design principles:
    - Single adapter boundary (simulator internals stay here)
    - Schema translation to overlay contract
    - Graceful degradation when state unavailable
    - Freshness tracking via last update time
    """

    # Default TTL for fresh state (seconds)
    DEFAULT_TTL = 60

    # Inactivity threshold before marking degraded (ticks)
    INACTIVITY_THRESHOLD = 50

    def __init__(
        self,
        state_store: Optional["StateStore"] = None,
        default_ttl: int = 60,
    ):
        """Initialize simulator state provider.

        Args:
            state_store: StateStore instance (lazy-loaded if None)
            default_ttl: Default freshness TTL in seconds
        """
        self._state_store = state_store
        self._default_ttl = default_ttl
        self._last_state_time = time.time()
        self._cabr_history: Dict[str, List[float]] = {}

    @property
    def provider_id(self) -> str:
        """Unique identifier for this provider."""
        return "simulator"

    def _get_state(self) -> Optional["SimulatorState"]:
        """Get current simulator state, if available."""
        if self._state_store is None:
            return None
        try:
            return self._state_store.get_state()
        except Exception as exc:
            logger.warning("[SIM-PROVIDER] Failed to get state: %s", exc)
            return None

    def _derive_health_status(
        self,
        tile: "FoundUpTile",
        sim_state: "SimulatorState",
    ) -> str:
        """Derive health status from simulator state.

        Returns:
            healthy | degraded | offline | unknown
        """
        # Check if daemon is running
        if not sim_state.daemon_running:
            return "offline"

        # Check activity recency
        ticks_since_activity = sim_state.tick - tile.last_activity_tick
        if ticks_since_activity > self.INACTIVITY_THRESHOLD:
            return "degraded"

        # Check CABR threshold
        if tile.cabr_score >= 0.618:
            return "healthy"
        elif tile.cabr_score >= 0.4:
            return "degraded"
        else:
            return "degraded"

    def _derive_availability(
        self,
        tile: "FoundUpTile",
        sim_state: "SimulatorState",
    ) -> str:
        """Derive availability from simulator state.

        Returns:
            online | maintenance | suspended
        """
        if not sim_state.daemon_running:
            return "suspended"

        # In simulation, all active FoundUps are online
        if tile.tasks_completed > 0 or tile.task_count > 0:
            return "online"

        return "online"

    def _derive_cabr_trend(self, foundup_id: str, current_score: float) -> str:
        """Track CABR score history and derive trend.

        Returns:
            rising | stable | falling | unknown
        """
        history = self._cabr_history.setdefault(foundup_id, [])
        history.append(current_score)

        # Keep last 10 samples
        if len(history) > 10:
            history.pop(0)

        if len(history) < 3:
            return "unknown"

        # Compare recent average to older average
        recent = sum(history[-3:]) / 3
        older = sum(history[:-3]) / max(1, len(history) - 3)

        delta = recent - older
        if delta > 0.05:
            return "rising"
        elif delta < -0.05:
            return "falling"
        else:
            return "stable"

    def _derive_reserve_health(self, tile: "FoundUpTile") -> str:
        """Derive abstract reserve health.

        Returns:
            strong | adequate | low | critical | unknown
        """
        # In simulation, derive from total staked
        if tile.total_staked >= 10000:
            return "strong"
        elif tile.total_staked >= 1000:
            return "adequate"
        elif tile.total_staked >= 100:
            return "low"
        elif tile.total_staked > 0:
            return "critical"
        else:
            return "unknown"

    def _translate_tile(
        self,
        tile: "FoundUpTile",
        sim_state: "SimulatorState",
    ) -> FoundUpStateOverlay:
        """Translate a simulator FoundUpTile to FoundUpStateOverlay.

        This is the single translation boundary - all schema adaptation
        happens here.
        """
        health = self._derive_health_status(tile, sim_state)
        availability = self._derive_availability(tile, sim_state)
        cabr_trend = self._derive_cabr_trend(tile.foundup_id, tile.cabr_score)
        reserve_health = self._derive_reserve_health(tile)

        # Count active agents for this FoundUp
        active_agents = sum(
            1 for a in sim_state.agents.values()
            if a.status == "active"
        )

        # Calculate tasks in flight
        tasks_in_flight = tile.task_count - tile.tasks_completed

        # Calculate freshness TTL
        ticks_since_update = sim_state.tick - tile.last_activity_tick
        # Assume ~1 tick/second for simplicity
        seconds_stale = ticks_since_update
        ttl = max(0, self._default_ttl - seconds_stale)

        return FoundUpStateOverlay(
            foundup_id=tile.foundup_id,
            health_status=health,
            availability=availability,
            cabr_score=tile.cabr_score,
            cabr_trend=cabr_trend,
            lifecycle_progress={
                "declared_stage": tile.lifecycle_stage,
                "observed_stage": tile.lifecycle_stage,
                "tasks_completed": tile.tasks_completed,
                "milestones_published": 0,  # Not tracked in basic tile
                "days_in_stage": 0,  # Would need creation time
            },
            agent_activity={
                "active_agents": active_agents,
                "tasks_in_flight": tasks_in_flight,
                "last_agent_action": None,  # Would need timestamp tracking
            },
            reserve_summary={
                "reserve_health": reserve_health,
                "reserve_trend": "unknown",  # Would need history
            },
            last_updated_at=datetime.now(timezone.utc).isoformat(),
            state_provider=self.provider_id,
            freshness_ttl=ttl,
        )

    def get_foundup_state(self, foundup_id: str) -> Optional[FoundUpStateOverlay]:
        """Get current state for one FoundUp.

        Returns None if FoundUp unknown or state unavailable.
        """
        sim_state = self._get_state()
        if sim_state is None:
            logger.debug("[SIM-PROVIDER] No state available for %s", foundup_id)
            return None

        tile = sim_state.foundups.get(foundup_id)
        if tile is None:
            logger.debug("[SIM-PROVIDER] FoundUp not found: %s", foundup_id)
            return None

        return self._translate_tile(tile, sim_state)

    def list_foundup_states(self) -> List[FoundUpStateOverlay]:
        """Get current state for all known FoundUps.

        Returns empty list if no state available.
        """
        sim_state = self._get_state()
        if sim_state is None:
            return []

        result = []
        for tile in sim_state.foundups.values():
            overlay = self._translate_tile(tile, sim_state)
            result.append(overlay)

        return result

    def get_state_freshness(self, foundup_id: str) -> Optional[int]:
        """Get seconds until state is considered stale.

        Returns None if FoundUp unknown.
        Returns 0 if already stale.
        """
        overlay = self.get_foundup_state(foundup_id)
        if overlay is None:
            return None
        return overlay.freshness_ttl


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def create_simulator_provider(
    state_store: Optional["StateStore"] = None,
) -> SimulatorStateProvider:
    """Create a simulator state provider.

    Args:
        state_store: StateStore instance (required for live state)

    Returns:
        SimulatorStateProvider instance
    """
    return SimulatorStateProvider(state_store=state_store)
