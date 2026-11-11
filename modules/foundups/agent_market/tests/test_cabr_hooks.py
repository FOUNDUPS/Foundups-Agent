"""Tests for PersistentCABRHooks evidence chain.

WSP References:
- WSP 29: CABR Engine integration
- WSP 26: FoundUPS tokenization metrics
"""

import pytest

from modules.foundups.agent_market.src.authorization import CallerAuthorization
from modules.foundups.agent_market.src.cabr_hooks import (
    CABRInput,
    CABROutput,
    PersistentCABRHooks,
)
from modules.foundups.agent_market.src.in_memory import InMemoryAgentMarket
from modules.foundups.agent_market.src.models import (
    Foundup,
    Proof,
    Task,
    TaskStatus,
    Verification,
)

VERIFIER_AUTHORIZATION = CallerAuthorization("verifier_1", frozenset({("f_test", "verifier")}))
TREASURY_AUTHORIZATION = CallerAuthorization("treasury_1", frozenset({("f_test", "treasury")}))


class TestCABRInput:
    """Tests for CABRInput dataclass."""

    def test_cabr_input_to_dict(self):
        """CABRInput serializes to dict correctly."""
        cabr_input = CABRInput(
            foundup_id="f_test",
            window="24h",
            tasks_total=10,
            tasks_claimed=3,
            tasks_submitted=2,
            tasks_verified=1,
            tasks_paid=1,
            completion_rate=0.1,
            verification_rate=0.5,
            avg_cycle_time_hours=4.5,
            active_agents=5,
            events_total=50,
        )

        result = cabr_input.to_dict()

        assert result["foundup_id"] == "f_test"
        assert result["window"] == "24h"
        assert result["tasks_total"] == 10
        assert result["completion_rate"] == 0.1
        assert "collected_at" in result  # Auto-generated timestamp


class TestCABROutput:
    """Tests for CABROutput dataclass."""

    def test_cabr_output_to_dict(self):
        """CABROutput serializes to dict correctly."""
        cabr_output = CABROutput(
            foundup_id="f_test",
            score=0.85,
            confidence=0.92,
            factors={"activity": 0.8, "completion": 0.9},
            window="24h",
        )

        result = cabr_output.to_dict()

        assert result["foundup_id"] == "f_test"
        assert result["score"] == 0.85
        assert result["confidence"] == 0.92
        assert result["factors"]["activity"] == 0.8
        assert "computed_at" in result


class TestPersistentCABRHooks:
    """Tests for PersistentCABRHooks evidence chain."""

    def test_build_cabr_input_no_sources(self):
        """build_cabr_input returns zeros when no sources configured."""
        hooks = PersistentCABRHooks()

        result = hooks.build_cabr_input("f_test", "24h")

        assert result["foundup_id"] == "f_test"
        assert result["window"] == "24h"
        assert result["tasks_total"] == 0
        assert result["completion_rate"] == 0.0
        assert result["events_total"] == 0

    def test_build_cabr_input_with_task_source(self):
        """build_cabr_input collects metrics from task source."""
        # Create market as task source
        market = InMemoryAgentMarket(
            actor_roles={
                "verifier_1": "verifier",
                "treasury_1": "treasury",
            },
            deterministic=True,
        )
        market.create_foundup(
            Foundup(
                foundup_id="f_test",
                name="Test",
                owner_id="owner_1",
                token_symbol="TEST",
                immutable_metadata={},
                mutable_metadata={},
            )
        )

        # Create tasks in various states
        market.create_task(
            Task(
                task_id="t1",
                foundup_id="f_test",
                title="Open task",
                description="Test",
                acceptance_criteria=["done"],
                reward_amount=100,
                creator_id="owner_1",
            )
        )
        market.create_task(
            Task(
                task_id="t2",
                foundup_id="f_test",
                title="Claimed task",
                description="Test",
                acceptance_criteria=["done"],
                reward_amount=100,
                creator_id="owner_1",
            )
        )
        market.claim_task("t2", "agent_1")

        market.create_task(
            Task(
                task_id="t3",
                foundup_id="f_test",
                title="Paid task",
                description="Test",
                acceptance_criteria=["done"],
                reward_amount=100,
                creator_id="owner_1",
            )
        )
        market.claim_task("t3", "agent_1")
        market.submit_proof(
            Proof(
                proof_id="p3",
                task_id="t3",
                submitter_id="agent_1",
                artifact_uri="ipfs://test",
                artifact_hash="sha256:test",
            )
        )
        market.verify_proof(
            "t3",
            Verification(
                verification_id="v3",
                task_id="t3",
                verifier_id="verifier_1",
                approved=True,
                reason="ok",
            ),
            authorization=VERIFIER_AUTHORIZATION,
        )
        market.trigger_payout("t3", "treasury_1", authorization=TREASURY_AUTHORIZATION)

        # Create hooks with market as task source
        hooks = PersistentCABRHooks(task_source=market)

        result = hooks.build_cabr_input("f_test", "24h")

        assert result["tasks_total"] == 3
        assert result["tasks_claimed"] == 1  # t2 is claimed
        assert result["tasks_paid"] == 1  # t3 is paid
        # completion_rate = paid/total = 1/3
        assert abs(result["completion_rate"] - 1 / 3) < 0.01

    def test_record_cabr_output_stores_in_evidence_chain(self):
        """record_cabr_output stores output for audit trail."""
        hooks = PersistentCABRHooks()

        hooks.record_cabr_output(
            "f_test",
            {"score": 0.75, "confidence": 0.85, "factors": {"activity": 0.8}},
        )

        history = hooks.get_score_history("f_test")
        assert len(history) == 1
        assert history[0]["score"] == 0.75
        assert history[0]["confidence"] == 0.85

    def test_get_latest_score_returns_most_recent(self):
        """get_latest_score returns most recent CABR score."""
        hooks = PersistentCABRHooks()

        hooks.record_cabr_output("f_test", {"score": 0.5})
        hooks.record_cabr_output("f_test", {"score": 0.6})
        hooks.record_cabr_output("f_test", {"score": 0.75})

        latest = hooks.get_latest_score("f_test")
        assert latest == 0.75

    def test_get_latest_score_returns_none_when_empty(self):
        """get_latest_score returns None when no scores recorded."""
        hooks = PersistentCABRHooks()

        latest = hooks.get_latest_score("f_nonexistent")
        assert latest is None

    def test_get_score_history_respects_limit(self):
        """get_score_history respects limit parameter."""
        hooks = PersistentCABRHooks()

        for i in range(20):
            hooks.record_cabr_output("f_test", {"score": i * 0.05})

        history = hooks.get_score_history("f_test", limit=5)
        assert len(history) == 5
        # Should be last 5 entries (most recent)
        assert history[-1]["score"] == 0.95

    def test_get_input_history_tracks_evidence(self):
        """get_input_history tracks all CABR inputs for audit."""
        hooks = PersistentCABRHooks()

        hooks.build_cabr_input("f_test", "24h")
        hooks.build_cabr_input("f_test", "7d")
        hooks.build_cabr_input("f_test", "30d")

        history = hooks.get_input_history("f_test")
        assert len(history) == 3
        windows = [h["window"] for h in history]
        assert windows == ["24h", "7d", "30d"]

    def test_evidence_chain_isolated_per_foundup(self):
        """Evidence chain is isolated per foundup."""
        hooks = PersistentCABRHooks()

        hooks.record_cabr_output("f_a", {"score": 0.5})
        hooks.record_cabr_output("f_a", {"score": 0.6})
        hooks.record_cabr_output("f_b", {"score": 0.9})

        assert hooks.get_latest_score("f_a") == 0.6
        assert hooks.get_latest_score("f_b") == 0.9
        assert len(hooks.get_score_history("f_a")) == 2
        assert len(hooks.get_score_history("f_b")) == 1
