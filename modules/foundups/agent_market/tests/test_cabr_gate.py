"""Tests for CABR-gated distribution publish."""

import pytest

from modules.foundups.agent_market.src.authorization import CallerAuthorization
from modules.foundups.agent_market.src.exceptions import CABRGateError, InvalidStateTransitionError
from modules.foundups.agent_market.src.in_memory import InMemoryAgentMarket
from modules.foundups.agent_market.src.models import Foundup, Proof, Task, Verification

VERIFIER_AUTHORIZATION = CallerAuthorization("verifier_1", frozenset({("f_cabr", "verifier")}))


def _seed_verified_task() -> InMemoryAgentMarket:
    """Create market with a verified task ready for distribution."""
    market = InMemoryAgentMarket(
        actor_roles={
            "verifier_1": "verifier",
            "distribution_1": "distribution",
        }
    )
    market.create_foundup(
        Foundup(
            foundup_id="f_cabr",
            name="CABR Test Foundup",
            owner_id="owner_1",
            token_symbol="CABR",
            immutable_metadata={"launch_model": "tokenized"},
            mutable_metadata={},
        )
    )
    market.create_task(
        Task(
            task_id="t_cabr",
            foundup_id="f_cabr",
            title="CABR gated milestone",
            description="Test CABR gating on distribution",
            acceptance_criteria=["CABR score meets threshold"],
            reward_amount=100,
            creator_id="owner_1",
        )
    )
    market.claim_task("t_cabr", "agent_1")
    market.submit_proof(
        Proof(
            proof_id="proof_cabr",
            task_id="t_cabr",
            submitter_id="agent_1",
            artifact_uri="ipfs://cabr_proof",
            artifact_hash="sha256:cabr",
        )
    )
    market.verify_proof(
        "t_cabr",
        Verification(
            verification_id="ver_cabr",
            task_id="t_cabr",
            verifier_id="verifier_1",
            approved=True,
            reason="meets CABR requirements",
        ),
        authorization=VERIFIER_AUTHORIZATION,
    )
    return market


def test_cabr_gate_blocks_when_score_missing():
    """CABR gate blocks publish when no CABR score recorded."""
    market = _seed_verified_task()

    # No CABR output recorded - should block with threshold > 0
    with pytest.raises(CABRGateError) as exc_info:
        market.publish_verified_milestone(
            "t_cabr",
            "distribution_1",
            channel="moltbook",
            cabr_threshold=0.5,
        )

    assert "CABR score missing" in str(exc_info.value)
    assert "f_cabr" in str(exc_info.value)


def test_cabr_gate_blocks_when_score_below_threshold():
    """CABR gate blocks publish when score below threshold."""
    market = _seed_verified_task()

    # Record CABR output with low score
    market.record_cabr_output("f_cabr", {"score": 0.3, "reason": "low activity"})

    with pytest.raises(CABRGateError) as exc_info:
        market.publish_verified_milestone(
            "t_cabr",
            "distribution_1",
            channel="moltbook",
            cabr_threshold=0.5,
        )

    assert "0.30" in str(exc_info.value)
    assert "0.50" in str(exc_info.value)
    assert "below threshold" in str(exc_info.value)


def test_cabr_gate_allows_when_score_meets_threshold():
    """CABR gate allows publish when score meets or exceeds threshold."""
    market = _seed_verified_task()

    # Record CABR output with sufficient score
    market.record_cabr_output("f_cabr", {"score": 0.75, "reason": "healthy activity"})

    distribution = market.publish_verified_milestone(
        "t_cabr",
        "distribution_1",
        channel="moltbook",
        cabr_threshold=0.5,
    )

    assert distribution is not None
    assert distribution.foundup_id == "f_cabr"
    assert distribution.task_id == "t_cabr"


def test_cabr_gate_allows_when_threshold_zero():
    """CABR gate is bypassed when threshold is 0 (default)."""
    market = _seed_verified_task()

    # No CABR output recorded, but threshold is 0 - should allow
    distribution = market.publish_verified_milestone(
        "t_cabr",
        "distribution_1",
        channel="moltbook",
        cabr_threshold=0.0,
    )

    assert distribution is not None
    assert distribution.task_id == "t_cabr"


def test_cabr_gate_uses_latest_score():
    """CABR gate uses the most recent CABR score."""
    market = _seed_verified_task()

    # Record multiple CABR outputs - latest should be used
    market.record_cabr_output("f_cabr", {"score": 0.3, "reason": "early low"})
    market.record_cabr_output("f_cabr", {"score": 0.4, "reason": "improving"})
    market.record_cabr_output("f_cabr", {"score": 0.8, "reason": "healthy now"})

    # Should pass with threshold 0.5 because latest is 0.8
    distribution = market.publish_verified_milestone(
        "t_cabr",
        "distribution_1",
        channel="moltbook",
        cabr_threshold=0.5,
    )

    assert distribution is not None
    assert market.get_latest_cabr_score("f_cabr") == 0.8


def test_cabr_gate_event_includes_threshold():
    """Published milestone event includes CABR threshold used."""
    market = _seed_verified_task()
    market.record_cabr_output("f_cabr", {"score": 0.9, "reason": "excellent"})

    market.publish_verified_milestone(
        "t_cabr",
        "distribution_1",
        channel="moltbook",
        cabr_threshold=0.7,
    )

    events = market.query_events(task_id="t_cabr")
    publish_events = [e for e in events if e["event_type"] == "milestone.verified_published"]
    assert len(publish_events) == 1
    assert publish_events[0]["payload"]["cabr_threshold"] == 0.7
