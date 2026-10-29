from modules.foundups.agent_market.src.exceptions import ValidationError
from modules.foundups.agent_market.src.models import DistributionPost, Foundup, Payout, Proof, Task


def test_foundup_schema_validation_requires_name():
    try:
        Foundup(
            foundup_id="f_1",
            name="",
            owner_id="owner_1",
            token_symbol="FAM",
            immutable_metadata={"launch_model": "tokenized"},
            mutable_metadata={},
        )
        assert False, "expected ValidationError"
    except ValidationError:
        assert True


def test_task_schema_validation_requires_positive_reward():
    try:
        Task(
            task_id="t_1",
            foundup_id="f_1",
            title="draft launch docs",
            description="produce launch checklist",
            acceptance_criteria=["doc exists"],
            reward_amount=0,
            creator_id="owner_1",
        )
        assert False, "expected ValidationError"
    except ValidationError:
        assert True


def test_proof_and_payout_schema_validation():
    proof = Proof(
        proof_id="p_1",
        task_id="t_1",
        submitter_id="agent_1",
        artifact_uri="ipfs://artifact",
        artifact_hash="sha256:abc",
    )
    payout = Payout(
        payout_id="pay_1",
        task_id="t_1",
        recipient_id="agent_1",
        amount=100,
    )
    assert proof.task_id == "t_1"
    assert payout.amount == 100


def test_distribution_post_schema_validation():
    post = DistributionPost(
        distribution_id="dist_1",
        foundup_id="f_1",
        task_id="t_1",
        channel="moltbook",
        content="Milestone verified",
        actor_id="distribution_1",
        dedupe_key="t_1:moltbook:verified",
    )
    assert post.task_id == "t_1"
