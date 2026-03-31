#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for p.fMALL State Overlay Provider (Simulator PoC).

Tests the SimulatorStateProvider implementation per
PFMALL_STATE_OVERLAY_CONTRACT.md.
"""

import pytest
from unittest.mock import MagicMock, PropertyMock
from dataclasses import dataclass

from modules.foundups.simulator.adapters.pfmall_state_provider import (
    SimulatorStateProvider,
    FoundUpStateOverlay,
    create_simulator_provider,
    INT_TO_STAGE,
)


# ---------------------------------------------------------------------------
# Mock Simulator State
# ---------------------------------------------------------------------------

@dataclass
class MockFoundUpTile:
    """Mock FoundUpTile for testing."""
    foundup_id: str
    name: str = "TestFoundUp"
    token_symbol: str = "TEST"
    owner_id: str = "012"
    lifecycle_stage: str = "PoC"
    cabr_score: float = 0.72
    task_count: int = 5
    tasks_completed: int = 3
    last_activity_tick: int = 100
    total_staked: int = 5000
    status: str = "active"


@dataclass
class MockAgentState:
    """Mock AgentState for testing."""
    agent_id: str
    status: str = "active"


@dataclass
class MockSimulatorState:
    """Mock SimulatorState for testing."""
    tick: int = 105
    daemon_running: bool = True
    foundups: dict = None
    agents: dict = None

    def __post_init__(self):
        if self.foundups is None:
            self.foundups = {}
        if self.agents is None:
            self.agents = {}


class MockStateStore:
    """Mock StateStore for testing."""
    def __init__(self, state: MockSimulatorState = None):
        self._state = state or MockSimulatorState()

    def get_state(self):
        return self._state


# ---------------------------------------------------------------------------
# Provider Tests
# ---------------------------------------------------------------------------

class TestSimulatorStateProvider:
    """Tests for SimulatorStateProvider."""

    def test_provider_id(self):
        """Provider has correct ID."""
        provider = SimulatorStateProvider()
        assert provider.provider_id == "simulator"

    def test_get_state_no_store(self):
        """Returns None when no state store configured."""
        provider = SimulatorStateProvider(state_store=None)
        result = provider.get_foundup_state("test_001")
        assert result is None

    def test_get_state_unknown_foundup(self):
        """Returns None for unknown FoundUp."""
        store = MockStateStore(MockSimulatorState(foundups={}))
        provider = SimulatorStateProvider(state_store=store)
        result = provider.get_foundup_state("nonexistent")
        assert result is None

    def test_get_state_returns_overlay(self):
        """Returns overlay for known FoundUp."""
        tile = MockFoundUpTile(foundup_id="test_001", cabr_score=0.75)
        state = MockSimulatorState(
            tick=110,
            daemon_running=True,
            foundups={"test_001": tile},
            agents={"agent_1": MockAgentState("agent_1")},
        )
        store = MockStateStore(state)
        provider = SimulatorStateProvider(state_store=store)

        result = provider.get_foundup_state("test_001")

        assert result is not None
        assert isinstance(result, FoundUpStateOverlay)
        assert result.foundup_id == "test_001"
        assert result.cabr_score == 0.75
        assert result.state_provider == "simulator"

    def test_health_status_healthy(self):
        """Health status is healthy when CABR >= 0.618 and active."""
        tile = MockFoundUpTile(
            foundup_id="test_001",
            cabr_score=0.72,
            last_activity_tick=105,
        )
        state = MockSimulatorState(
            tick=110,
            daemon_running=True,
            foundups={"test_001": tile},
        )
        store = MockStateStore(state)
        provider = SimulatorStateProvider(state_store=store)

        result = provider.get_foundup_state("test_001")
        assert result.health_status == "healthy"

    def test_health_status_degraded_low_cabr(self):
        """Health status is degraded when CABR < 0.618."""
        tile = MockFoundUpTile(
            foundup_id="test_001",
            cabr_score=0.5,
            last_activity_tick=105,
        )
        state = MockSimulatorState(
            tick=110,
            daemon_running=True,
            foundups={"test_001": tile},
        )
        store = MockStateStore(state)
        provider = SimulatorStateProvider(state_store=store)

        result = provider.get_foundup_state("test_001")
        assert result.health_status == "degraded"

    def test_health_status_degraded_inactive(self):
        """Health status is degraded when inactive too long."""
        tile = MockFoundUpTile(
            foundup_id="test_001",
            cabr_score=0.72,
            last_activity_tick=10,  # Long ago
        )
        state = MockSimulatorState(
            tick=110,
            daemon_running=True,
            foundups={"test_001": tile},
        )
        store = MockStateStore(state)
        provider = SimulatorStateProvider(state_store=store)

        result = provider.get_foundup_state("test_001")
        assert result.health_status == "degraded"

    def test_health_status_offline(self):
        """Health status is offline when daemon not running."""
        tile = MockFoundUpTile(foundup_id="test_001")
        state = MockSimulatorState(
            tick=110,
            daemon_running=False,
            foundups={"test_001": tile},
        )
        store = MockStateStore(state)
        provider = SimulatorStateProvider(state_store=store)

        result = provider.get_foundup_state("test_001")
        assert result.health_status == "offline"

    def test_availability_online(self):
        """Availability is online when daemon running."""
        tile = MockFoundUpTile(foundup_id="test_001", task_count=5)
        state = MockSimulatorState(
            tick=110,
            daemon_running=True,
            foundups={"test_001": tile},
        )
        store = MockStateStore(state)
        provider = SimulatorStateProvider(state_store=store)

        result = provider.get_foundup_state("test_001")
        assert result.availability == "online"

    def test_availability_suspended(self):
        """Availability is suspended when daemon not running."""
        tile = MockFoundUpTile(foundup_id="test_001")
        state = MockSimulatorState(
            tick=110,
            daemon_running=False,
            foundups={"test_001": tile},
        )
        store = MockStateStore(state)
        provider = SimulatorStateProvider(state_store=store)

        result = provider.get_foundup_state("test_001")
        assert result.availability == "suspended"

    def test_lifecycle_progress_populated(self):
        """Lifecycle progress fields are populated."""
        tile = MockFoundUpTile(
            foundup_id="test_001",
            lifecycle_stage="Proto",
            tasks_completed=7,
        )
        state = MockSimulatorState(
            tick=110,
            daemon_running=True,
            foundups={"test_001": tile},
        )
        store = MockStateStore(state)
        provider = SimulatorStateProvider(state_store=store)

        result = provider.get_foundup_state("test_001")
        assert result.lifecycle_progress["observed_stage"] == "Proto"
        assert result.lifecycle_progress["tasks_completed"] == 7

    def test_agent_activity_populated(self):
        """Agent activity fields are populated."""
        tile = MockFoundUpTile(
            foundup_id="test_001",
            task_count=10,
            tasks_completed=6,
        )
        state = MockSimulatorState(
            tick=110,
            daemon_running=True,
            foundups={"test_001": tile},
            agents={
                "agent_1": MockAgentState("agent_1", "active"),
                "agent_2": MockAgentState("agent_2", "active"),
                "agent_3": MockAgentState("agent_3", "idle"),
            },
        )
        store = MockStateStore(state)
        provider = SimulatorStateProvider(state_store=store)

        result = provider.get_foundup_state("test_001")
        assert result.agent_activity["active_agents"] == 2
        assert result.agent_activity["tasks_in_flight"] == 4

    def test_reserve_summary_populated(self):
        """Reserve summary is derived from stake."""
        tile = MockFoundUpTile(foundup_id="test_001", total_staked=5000)
        state = MockSimulatorState(
            tick=110,
            daemon_running=True,
            foundups={"test_001": tile},
        )
        store = MockStateStore(state)
        provider = SimulatorStateProvider(state_store=store)

        result = provider.get_foundup_state("test_001")
        assert result.reserve_summary["reserve_health"] == "adequate"

    def test_reserve_health_strong(self):
        """Reserve health is strong when stake >= 10000."""
        tile = MockFoundUpTile(foundup_id="test_001", total_staked=15000)
        state = MockSimulatorState(
            daemon_running=True,
            foundups={"test_001": tile},
        )
        provider = SimulatorStateProvider(state_store=MockStateStore(state))
        result = provider.get_foundup_state("test_001")
        assert result.reserve_summary["reserve_health"] == "strong"

    def test_reserve_health_low(self):
        """Reserve health is low when stake < 1000."""
        tile = MockFoundUpTile(foundup_id="test_001", total_staked=500)
        state = MockSimulatorState(
            daemon_running=True,
            foundups={"test_001": tile},
        )
        provider = SimulatorStateProvider(state_store=MockStateStore(state))
        result = provider.get_foundup_state("test_001")
        assert result.reserve_summary["reserve_health"] == "low"

    def test_freshness_ttl(self):
        """Freshness TTL is calculated from activity."""
        tile = MockFoundUpTile(foundup_id="test_001", last_activity_tick=100)
        state = MockSimulatorState(
            tick=110,
            daemon_running=True,
            foundups={"test_001": tile},
        )
        store = MockStateStore(state)
        provider = SimulatorStateProvider(state_store=store, default_ttl=60)

        result = provider.get_foundup_state("test_001")
        # 60 - (110 - 100) = 50
        assert result.freshness_ttl == 50

    def test_freshness_ttl_zero_when_stale(self):
        """Freshness TTL is 0 when stale."""
        tile = MockFoundUpTile(foundup_id="test_001", last_activity_tick=10)
        state = MockSimulatorState(
            tick=110,
            daemon_running=True,
            foundups={"test_001": tile},
        )
        store = MockStateStore(state)
        provider = SimulatorStateProvider(state_store=store, default_ttl=60)

        result = provider.get_foundup_state("test_001")
        # 60 - (110 - 10) = 60 - 100 = -40, clamped to 0
        assert result.freshness_ttl == 0

    def test_list_foundup_states(self):
        """List returns all FoundUp states."""
        state = MockSimulatorState(
            tick=110,
            daemon_running=True,
            foundups={
                "test_001": MockFoundUpTile(foundup_id="test_001"),
                "test_002": MockFoundUpTile(foundup_id="test_002"),
                "test_003": MockFoundUpTile(foundup_id="test_003"),
            },
        )
        store = MockStateStore(state)
        provider = SimulatorStateProvider(state_store=store)

        result = provider.list_foundup_states()
        assert len(result) == 3
        ids = {r.foundup_id for r in result}
        assert ids == {"test_001", "test_002", "test_003"}

    def test_list_foundup_states_empty(self):
        """List returns empty when no FoundUps."""
        state = MockSimulatorState(foundups={})
        store = MockStateStore(state)
        provider = SimulatorStateProvider(state_store=store)

        result = provider.list_foundup_states()
        assert result == []

    def test_list_foundup_states_no_store(self):
        """List returns empty when no store."""
        provider = SimulatorStateProvider(state_store=None)
        result = provider.list_foundup_states()
        assert result == []

    def test_get_state_freshness(self):
        """Get freshness returns TTL."""
        tile = MockFoundUpTile(foundup_id="test_001", last_activity_tick=100)
        state = MockSimulatorState(
            tick=110,
            daemon_running=True,
            foundups={"test_001": tile},
        )
        store = MockStateStore(state)
        provider = SimulatorStateProvider(state_store=store, default_ttl=60)

        result = provider.get_state_freshness("test_001")
        assert result == 50

    def test_get_state_freshness_unknown(self):
        """Get freshness returns None for unknown FoundUp."""
        store = MockStateStore(MockSimulatorState(foundups={}))
        provider = SimulatorStateProvider(state_store=store)

        result = provider.get_state_freshness("nonexistent")
        assert result is None

    def test_cabr_trend_unknown_initially(self):
        """CABR trend is unknown with insufficient history."""
        tile = MockFoundUpTile(foundup_id="test_001", cabr_score=0.72)
        state = MockSimulatorState(
            daemon_running=True,
            foundups={"test_001": tile},
        )
        provider = SimulatorStateProvider(state_store=MockStateStore(state))

        result = provider.get_foundup_state("test_001")
        assert result.cabr_trend == "unknown"

    def test_cabr_trend_rising(self):
        """CABR trend is rising when score increases."""
        tile = MockFoundUpTile(foundup_id="test_001", cabr_score=0.5)
        state = MockSimulatorState(
            daemon_running=True,
            foundups={"test_001": tile},
        )
        provider = SimulatorStateProvider(state_store=MockStateStore(state))

        # Build history with low scores
        for _ in range(5):
            tile.cabr_score = 0.5
            provider.get_foundup_state("test_001")

        # Now increase score
        for _ in range(3):
            tile.cabr_score = 0.8
            result = provider.get_foundup_state("test_001")

        assert result.cabr_trend == "rising"

    def test_cabr_trend_stable(self):
        """CABR trend is stable when score unchanged."""
        tile = MockFoundUpTile(foundup_id="test_001", cabr_score=0.72)
        state = MockSimulatorState(
            daemon_running=True,
            foundups={"test_001": tile},
        )
        provider = SimulatorStateProvider(state_store=MockStateStore(state))

        # Build history with same score
        for _ in range(10):
            result = provider.get_foundup_state("test_001")

        assert result.cabr_trend == "stable"


# ---------------------------------------------------------------------------
# Factory Tests
# ---------------------------------------------------------------------------

class TestFactory:
    """Tests for create_simulator_provider factory."""

    def test_create_without_store(self):
        """Factory creates provider without store."""
        provider = create_simulator_provider()
        assert provider is not None
        assert provider.provider_id == "simulator"

    def test_create_with_store(self):
        """Factory creates provider with store."""
        store = MockStateStore()
        provider = create_simulator_provider(state_store=store)
        assert provider is not None


# ---------------------------------------------------------------------------
# Integration with pfmall_catalog Protocol
# ---------------------------------------------------------------------------

class TestProtocolCompliance:
    """Tests that provider satisfies StateOverlayProvider protocol."""

    def test_has_get_foundup_state(self):
        """Provider has get_foundup_state method."""
        provider = SimulatorStateProvider()
        assert hasattr(provider, "get_foundup_state")
        assert callable(provider.get_foundup_state)

    def test_has_list_foundup_states(self):
        """Provider has list_foundup_states method."""
        provider = SimulatorStateProvider()
        assert hasattr(provider, "list_foundup_states")
        assert callable(provider.list_foundup_states)

    def test_has_get_state_freshness(self):
        """Provider has get_state_freshness method."""
        provider = SimulatorStateProvider()
        assert hasattr(provider, "get_state_freshness")
        assert callable(provider.get_state_freshness)

    def test_has_provider_id(self):
        """Provider has provider_id property."""
        provider = SimulatorStateProvider()
        assert hasattr(provider, "provider_id")
        assert provider.provider_id == "simulator"

    def test_overlay_has_required_fields(self):
        """Overlay has all required contract fields."""
        tile = MockFoundUpTile(foundup_id="test_001")
        state = MockSimulatorState(
            daemon_running=True,
            foundups={"test_001": tile},
        )
        provider = SimulatorStateProvider(state_store=MockStateStore(state))

        result = provider.get_foundup_state("test_001")

        # Required fields per PFMALL_STATE_OVERLAY_CONTRACT.md
        assert hasattr(result, "foundup_id")
        assert hasattr(result, "health_status")
        assert hasattr(result, "availability")
        assert hasattr(result, "cabr_score")
        assert hasattr(result, "lifecycle_progress")
        assert hasattr(result, "agent_activity")
        assert hasattr(result, "last_updated_at")
        assert hasattr(result, "state_provider")
        assert hasattr(result, "freshness_ttl")
