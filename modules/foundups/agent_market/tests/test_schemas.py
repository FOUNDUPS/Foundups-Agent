from modules.foundups.agent_market.src.exceptions import ValidationError
from modules.foundups.agent_market.src.models import DistributionPost, Foundup, Payout, Proof, Task

from decimal import Decimal
from fractions import Fraction
import pytest

from modules.foundups.agent_market.src.models import (
    ComputeLedgerEntry, ComputePlan, ComputeSession, ComputeWallet, TokenTerms,
)


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


class _DeceptiveInteger(int):
    def __lt__(self, other):
        return False

    def __le__(self, other):
        return False


_QUANTITY_CASES = (
    (TokenTerms, "max_supply", dict(token_name="test", token_symbol="TST",
        max_supply=1, treasury_account="treasury"), 1),
    (Task, "reward_amount", dict(task_id="task", foundup_id="foundup", title="task",
        description="work", acceptance_criteria=["proof"], reward_amount=1, creator_id="owner"), 1),
    (Payout, "amount", dict(payout_id="payout", task_id="task", recipient_id="agent", amount=1), 1),
    (ComputePlan, "monthly_credit_allocation", dict(plan_id="plan", actor_id="agent",
        tier="builder", status="active"), 0),
    (ComputeWallet, "credit_balance", dict(wallet_id="wallet", actor_id="agent"), 0),
    (ComputeWallet, "reserved_credits", dict(wallet_id="wallet", actor_id="agent"), 0),
    (ComputeLedgerEntry, "amount", dict(entry_id="entry", actor_id="agent",
        entry_type="credit", amount=1, reason="fixture"), 1),
    (ComputeSession, "credits_debited", dict(session_id="session", actor_id="agent",
        foundup_id="foundup", workload={}, credits_debited=0), 0),
)
_QUANTITY_IDS = tuple(model.__name__ + "." + field for model, field, _, _ in _QUANTITY_CASES)


@pytest.mark.parametrize("case", _QUANTITY_CASES, ids=_QUANTITY_IDS)
@pytest.mark.parametrize("kind", ["true", "false", "float", "decimal", "fraction", "string", "subclass"])
def test_quantity_requires_an_exact_builtin_integer(case, kind):
    model, field, kwargs, _ = case
    values = dict(true=True, false=False, float=1.0, decimal=Decimal(1),
                  fraction=Fraction(1, 1), string="1", subclass=_DeceptiveInteger(-1))
    with pytest.raises(ValidationError):
        model(**{**kwargs, field: values[kind]})


@pytest.mark.parametrize("case", _QUANTITY_CASES, ids=_QUANTITY_IDS)
@pytest.mark.parametrize("offset", [0, 1])
def test_quantity_preserves_exact_minimum_integer_boundaries(case, offset):
    model, field, kwargs, minimum = case
    value = minimum + offset
    record = model(**{**kwargs, field: value})
    assert type(getattr(record, field)) is int
    assert getattr(record, field) == value
