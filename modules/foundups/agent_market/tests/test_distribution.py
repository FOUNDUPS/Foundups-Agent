import pytest

from modules.foundups.agent_market.src.authorization import CallerAuthorization
from modules.foundups.agent_market.src.exceptions import InvalidStateTransitionError
from modules.foundups.agent_market.src.in_memory import InMemoryAgentMarket
from modules.foundups.agent_market.src.models import Foundup, Proof, Task, Verification

VERIFIER_AUTHORIZATION = CallerAuthorization("verifier_1", frozenset({("f_1", "verifier")}))


def _seed_market() -> InMemoryAgentMarket:
    market = InMemoryAgentMarket(
        actor_roles={
            "verifier_1": "verifier",
            "distribution_1": "distribution",
        }
    )
    market.create_foundup(
        Foundup(
            foundup_id="f_1",
            name="distribution flow",
            owner_id="owner_1",
            token_symbol="FAM",
            immutable_metadata={"launch_model": "tokenized"},
            mutable_metadata={},
        )
    )
    market.create_task(
        Task(
            task_id="t_1",
            foundup_id="f_1",
            title="ship verified milestone",
            description="verify milestone then publish",
            acceptance_criteria=["proof submitted", "verification approved"],
            reward_amount=120,
            creator_id="owner_1",
        )
    )
    market.claim_task("t_1", "agent_1")
    market.submit_proof(
        Proof(
            proof_id="proof_1",
            task_id="t_1",
            submitter_id="agent_1",
            artifact_uri="ipfs://proof",
            artifact_hash="sha256:dist",
        )
    )
    return market


def test_unverified_task_cannot_publish_distribution():
    market = _seed_market()
    with pytest.raises(InvalidStateTransitionError):
        market.publish_verified_milestone("t_1", "distribution_1", channel="moltbook")


def test_verified_task_publish_is_idempotent():
    market = _seed_market()
    market.verify_proof(
        "t_1",
        Verification(
            verification_id="ver_1",
            task_id="t_1",
            verifier_id="verifier_1",
            approved=True,
            reason="meets criteria",
        ),
        authorization=VERIFIER_AUTHORIZATION,
    )

    first = market.publish_verified_milestone("t_1", "distribution_1", channel="moltbook")
    second = market.publish_verified_milestone("t_1", "distribution_1", channel="moltbook")

    assert first.distribution_id == second.distribution_id
    assert market.get_distribution("t_1").distribution_id == first.distribution_id
    events = market.query_events(task_id="t_1")
    publish_events = [e for e in events if e["event_type"] == "milestone.verified_published"]
    assert len(publish_events) == 1
