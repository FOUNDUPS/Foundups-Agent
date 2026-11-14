"""Tests for deterministic ID generation in InMemoryAgentMarket.

WSP References:
- WSP 5: Testing standards - deterministic behavior for repeatable tests
"""

import pytest

from modules.foundups.agent_market.src.authorization import CallerAuthorization
from modules.foundups.agent_market.src.in_memory import (
    DeterministicIdGenerator,
    InMemoryAgentMarket,
)
from modules.foundups.agent_market.src.models import (
    Foundup,
    Proof,
    Task,
    Verification,
)

VERIFIER_AUTHORIZATION = CallerAuthorization("verifier_1", frozenset({("f_det", "verifier")}))
TREASURY_AUTHORIZATION = CallerAuthorization("treasury_1", frozenset({("f_det", "treasury")}))


class TestDeterministicIdGenerator:
    """Tests for the DeterministicIdGenerator class."""

    def test_deterministic_mode_generates_sequential_ids(self):
        """In deterministic mode, IDs are sequential."""
        gen = DeterministicIdGenerator(deterministic=True)

        id1 = gen.next_id("ev", 12)
        id2 = gen.next_id("ev", 12)
        id3 = gen.next_id("ev", 12)

        assert id1 == "ev_0001"
        assert id2 == "ev_0002"
        assert id3 == "ev_0003"

    def test_deterministic_mode_separate_counters_per_prefix(self):
        """Each prefix has its own counter in deterministic mode."""
        gen = DeterministicIdGenerator(deterministic=True)

        ev1 = gen.next_id("ev", 12)
        join1 = gen.next_id("join", 10)
        ev2 = gen.next_id("ev", 12)
        join2 = gen.next_id("join", 10)

        assert ev1 == "ev_0001"
        assert join1 == "join_0001"
        assert ev2 == "ev_0002"
        assert join2 == "join_0002"

    def test_non_deterministic_mode_generates_uuid_ids(self):
        """In non-deterministic mode, IDs use uuid4 hex."""
        gen = DeterministicIdGenerator(deterministic=False)

        id1 = gen.next_id("ev", 12)
        id2 = gen.next_id("ev", 12)

        # UUIDs should be different
        assert id1 != id2
        # Should have prefix and hex suffix
        assert id1.startswith("ev_")
        assert len(id1) == 3 + 12  # "ev_" + 12 hex chars

    def test_reset_clears_all_counters(self):
        """Reset clears all counters for test isolation."""
        gen = DeterministicIdGenerator(deterministic=True)

        gen.next_id("ev", 12)
        gen.next_id("ev", 12)
        gen.next_id("join", 10)

        gen.reset()

        # After reset, counters should start from 1 again
        assert gen.next_id("ev", 12) == "ev_0001"
        assert gen.next_id("join", 10) == "join_0001"


class TestInMemoryMarketDeterminism:
    """Tests for deterministic behavior of InMemoryAgentMarket."""

    def test_deterministic_flag_enables_sequential_ids(self):
        """When deterministic=True, generated IDs are sequential."""
        market = InMemoryAgentMarket(deterministic=True)

        market.create_foundup(
            Foundup(
                foundup_id="f_test",
                name="Test Foundup",
                owner_id="owner_1",
                token_symbol="TEST",
                immutable_metadata={},
                mutable_metadata={},
            )
        )

        # Events should have deterministic IDs
        events = market.query_events(foundup_id="f_test")
        assert len(events) == 1
        assert events[0]["event_id"] == "ev_0001"

    def test_reset_clears_all_state(self):
        """Market reset clears all stored data."""
        market = InMemoryAgentMarket(deterministic=True)

        market.create_foundup(
            Foundup(
                foundup_id="f_test",
                name="Test Foundup",
                owner_id="owner_1",
                token_symbol="TEST",
                immutable_metadata={},
                mutable_metadata={},
            )
        )
        market.create_task(
            Task(
                task_id="t_test",
                foundup_id="f_test",
                title="Test Task",
                description="Test",
                acceptance_criteria=["done"],
                reward_amount=100,
                creator_id="owner_1",
            )
        )

        market.reset()

        # All state should be cleared
        assert len(market.foundups) == 0
        assert len(market.tasks) == 0
        assert len(market.events) == 0

    def test_reset_resets_id_counters(self):
        """Market reset also resets ID counters."""
        market = InMemoryAgentMarket(deterministic=True)

        # Create some events
        market.create_foundup(
            Foundup(
                foundup_id="f1",
                name="Foundup 1",
                owner_id="owner_1",
                token_symbol="F1",
                immutable_metadata={},
                mutable_metadata={},
            )
        )
        events_before = market.query_events(foundup_id="f1")
        assert events_before[0]["event_id"] == "ev_0001"

        market.reset()

        # After reset, ID counter should start from 1 again
        market.create_foundup(
            Foundup(
                foundup_id="f2",
                name="Foundup 2",
                owner_id="owner_1",
                token_symbol="F2",
                immutable_metadata={},
                mutable_metadata={},
            )
        )
        events_after = market.query_events(foundup_id="f2")
        assert events_after[0]["event_id"] == "ev_0001"

    def test_full_lifecycle_deterministic_ids(self):
        """Full task lifecycle produces deterministic IDs."""
        market = InMemoryAgentMarket(
            actor_roles={
                "verifier_1": "verifier",
                "treasury_1": "treasury",
            },
            deterministic=True,
        )

        market.create_foundup(
            Foundup(
                foundup_id="f_det",
                name="Deterministic Test",
                owner_id="owner_1",
                token_symbol="DET",
                immutable_metadata={},
                mutable_metadata={},
            )
        )

        market.create_task(
            Task(
                task_id="t_det",
                foundup_id="f_det",
                title="Deterministic Task",
                description="Test",
                acceptance_criteria=["done"],
                reward_amount=100,
                creator_id="owner_1",
            )
        )

        market.claim_task("t_det", "agent_1")

        market.submit_proof(
            Proof(
                proof_id="proof_det",
                task_id="t_det",
                submitter_id="agent_1",
                artifact_uri="ipfs://test",
                artifact_hash="sha256:test",
            )
        )

        market.verify_proof(
            "t_det",
            Verification(
                verification_id="ver_det",
                task_id="t_det",
                verifier_id="verifier_1",
                approved=True,
                reason="approved",
            ),
            authorization=VERIFIER_AUTHORIZATION,
        )

        payout = market.trigger_payout("t_det", "treasury_1", authorization=TREASURY_AUTHORIZATION)

        # Payout ID should be deterministic
        assert payout.payout_id == "pay_0001"
        # Reference should also be deterministic
        assert payout.reference == "inmem_0001"

    def test_get_tasks_by_foundup(self):
        """get_tasks_by_foundup returns tasks for given foundup."""
        market = InMemoryAgentMarket(deterministic=True)

        market.create_foundup(
            Foundup(
                foundup_id="f_a",
                name="Foundup A",
                owner_id="owner_1",
                token_symbol="A",
                immutable_metadata={},
                mutable_metadata={},
            )
        )
        market.create_foundup(
            Foundup(
                foundup_id="f_b",
                name="Foundup B",
                owner_id="owner_1",
                token_symbol="B",
                immutable_metadata={},
                mutable_metadata={},
            )
        )

        market.create_task(
            Task(
                task_id="t_a1",
                foundup_id="f_a",
                title="Task A1",
                description="Test",
                acceptance_criteria=["done"],
                reward_amount=100,
                creator_id="owner_1",
            )
        )
        market.create_task(
            Task(
                task_id="t_a2",
                foundup_id="f_a",
                title="Task A2",
                description="Test",
                acceptance_criteria=["done"],
                reward_amount=200,
                creator_id="owner_1",
            )
        )
        market.create_task(
            Task(
                task_id="t_b1",
                foundup_id="f_b",
                title="Task B1",
                description="Test",
                acceptance_criteria=["done"],
                reward_amount=300,
                creator_id="owner_1",
            )
        )

        tasks_a = market.get_tasks_by_foundup("f_a")
        tasks_b = market.get_tasks_by_foundup("f_b")

        assert len(tasks_a) == 2
        assert {t.task_id for t in tasks_a} == {"t_a1", "t_a2"}
        assert len(tasks_b) == 1
        assert tasks_b[0].task_id == "t_b1"
