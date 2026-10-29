import pytest

from modules.foundups.agent_market.src.authorization import CallerAuthorization
from modules.foundups.agent_market.src.exceptions import ValidationError
from modules.foundups.agent_market.src.in_memory import InMemoryAgentMarket
from modules.foundups.agent_market.src.models import (
    Foundup,
    Proof,
    Task,
    TaskStatus,
    Verification,
)

VERIFIER_AUTHORIZATION = CallerAuthorization("verifier_1", frozenset({("f_1", "verifier")}))
TREASURY_AUTHORIZATION = CallerAuthorization("treasury_1", frozenset({("f_1", "treasury")}))


def test_token_symbol_uniqueness_in_memory():
    market = InMemoryAgentMarket()
    market.create_foundup(
        Foundup(
            foundup_id="f_a",
            name="alpha",
            owner_id="owner_a",
            token_symbol="ALPHA",
            immutable_metadata={},
            mutable_metadata={},
        )
    )
    with pytest.raises(ValidationError):
        market.create_foundup(
            Foundup(
                foundup_id="f_b",
                name="beta",
                owner_id="owner_b",
                token_symbol="alpha",
                immutable_metadata={},
                mutable_metadata={},
            )
        )


def test_task_lifecycle_open_to_paid():
    market = InMemoryAgentMarket(
        actor_roles={
            "verifier_1": "verifier",
            "treasury_1": "treasury",
            "distribution_1": "distribution",
        }
    )

    foundup = Foundup(
        foundup_id="f_1",
        name="foundup launchpad",
        owner_id="owner_1",
        token_symbol="FUP",
        immutable_metadata={"launch_model": "tokenized"},
        mutable_metadata={},
    )
    market.create_foundup(foundup)

    task = Task(
        task_id="t_1",
        foundup_id="f_1",
        title="design payout schema",
        description="create payout JSON schema",
        acceptance_criteria=["schema committed", "tests pass"],
        reward_amount=250,
        creator_id="owner_1",
    )
    market.create_task(task)
    assert market.get_task("t_1").status == TaskStatus.OPEN

    market.claim_task("t_1", "agent_1")
    assert market.get_task("t_1").status == TaskStatus.CLAIMED

    market.submit_proof(
        Proof(
            proof_id="proof_1",
            task_id="t_1",
            submitter_id="agent_1",
            artifact_uri="ipfs://proof",
            artifact_hash="sha256:def",
        )
    )
    assert market.get_task("t_1").status == TaskStatus.SUBMITTED

    market.verify_proof(
        "t_1",
        Verification(
            verification_id="ver_1",
            task_id="t_1",
            verifier_id="verifier_1",
            approved=True,
            reason="acceptance criteria met",
        ),
        authorization=VERIFIER_AUTHORIZATION,
    )
    assert market.get_task("t_1").status == TaskStatus.VERIFIED

    distribution = market.publish_verified_milestone("t_1", "distribution_1")
    assert distribution.task_id == "t_1"

    payout = market.trigger_payout("t_1", "treasury_1", authorization=TREASURY_AUTHORIZATION)
    assert payout.amount == 250
    assert market.get_task("t_1").status == TaskStatus.PAID

    trace = market.get_trace("t_1")
    assert trace["foundup"]["foundup_id"] == "f_1"
    assert trace["proof"]["proof_id"] == "proof_1"
    assert trace["verification"]["verification_id"] == "ver_1"
    assert trace["payout"]["payout_id"] == payout.payout_id
