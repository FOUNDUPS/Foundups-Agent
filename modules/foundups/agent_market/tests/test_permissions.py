import pytest

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

from modules.foundups.agent_market.src.exceptions import AgentMarketError, PermissionDeniedError, ValidationError
from modules.foundups.agent_market.src.in_memory import InMemoryAgentMarket
from modules.foundups.agent_market.src.models import AgentProfile, Foundup, Proof, Task, TaskStatus, Verification


def _seed_market() -> InMemoryAgentMarket:
    market = InMemoryAgentMarket(actor_roles={"verifier_1": "verifier", "treasury_1": "treasury"})
    market.create_foundup(
        Foundup(
            foundup_id="f_1",
            name="outer layer launch",
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
            title="proof pipeline",
            description="implement proof pipeline",
            acceptance_criteria=["proof submitted"],
            reward_amount=100,
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
            artifact_hash="sha256:123",
        )
    )
    return market


def test_only_verifier_can_verify():
    market = _seed_market()
    with pytest.raises(PermissionDeniedError):
        market.verify_proof(
            "t_1",
            Verification(
                verification_id="ver_fail",
                task_id="t_1",
                verifier_id="random_actor",
                approved=True,
                reason="trying to bypass role gate",
            ),
        )


def test_only_treasury_can_trigger_payout():
    market = _seed_market()
    market.verify_proof(
        "t_1",
        Verification(
            verification_id="ver_1",
            task_id="t_1",
            verifier_id="verifier_1",
            approved=True,
            reason="approved",
        ),
        authorization=_context("verifier_1", {("f_1", "verifier")}),
    )

    with pytest.raises(PermissionDeniedError):
        market.trigger_payout("t_1", "random_actor")


def test_only_distribution_role_can_publish_verified_milestone():
    market = _seed_market()
    market.verify_proof(
        "t_1",
        Verification(
            verification_id="ver_2",
            task_id="t_1",
            verifier_id="verifier_1",
            approved=True,
            reason="approved",
        ),
        authorization=_context("verifier_1", {("f_1", "verifier")}),
    )

    with pytest.raises(PermissionDeniedError):
        market.publish_verified_milestone("t_1", "random_actor")


@pytest.fixture(params=["memory", "persistent"])
def admission(request, tmp_path):
    """Trusted test host seeds one task; profiles and compute grant no authority."""
    memory = _seed_market()
    task = deepcopy(memory.get_task("t_1"))
    decision = Verification("decision_1", "t_1", "verifier_1", True, "fixture approval")
    if request.param == "persistent":
        from modules.foundups.agent_market.src.persistence.sqlite_adapter import SQLiteAdapter
        from modules.foundups.agent_market.src.task_pipeline import PersistentTaskPipeline
        store = SQLiteAdapter(tmp_path / "permissions.db")
        store.create_foundup(memory.get_foundup("f_1"))
        store.create_task(task)
        store.create_proof(memory.proofs["proof_1"])
        service = PersistentTaskPipeline(store)
    else:
        store = service = memory
    store.compute_access_enforced = True
    for principal in ("verifier_1", "treasury_1", "agent_1"):
        store.activate_compute_plan(principal, tier="builder", monthly_credit_allocation=20)
    case = SimpleNamespace(kind=request.param, store=store, service=service, task=task, decision=decision)
    try:
        yield case
    finally:
        if request.param == "persistent":
            store.close()


def _snapshot(case):
    if case.kind == "persistent":
        from modules.foundups.agent_market.tests.test_persistent_compute_wiring import _database_snapshot
        return _database_snapshot(case.store)
    return deepcopy({name: getattr(case.store, name) for name in (
        "tasks", "proofs", "verifications", "payouts", "events", "compute_wallets", "compute_ledger",
    )})


def _approved_fixture(case):
    """Synthetic storage setup for payout admission; this does not verify work."""
    if case.kind == "persistent":
        case.store.create_verification(case.decision)
        task = case.store.get_task("t_1")
        task.status, task.verification_id = TaskStatus.VERIFIED, "decision_1"
        case.store.update_task(task)
    else:
        case.store.verifications["decision_1"] = case.decision
        case.store.tasks["t_1"].status = TaskStatus.VERIFIED
        case.store.tasks["t_1"].verification_id = "decision_1"


def _context(principal, grants):
    from modules.foundups.agent_market.src.authorization import CallerAuthorization
    return CallerAuthorization(principal, frozenset(grants))


@pytest.mark.parametrize("action", ["verify", "payout"])
def test_missing_host_authorization_denies_without_effects(admission, action):
    if action == "payout":
        _approved_fixture(admission)
    before = _snapshot(admission)
    with pytest.raises(PermissionDeniedError):
        if action == "verify":
            admission.service.verify_proof("t_1", admission.decision)
        else:
            admission.service.trigger_payout("t_1", "treasury_1")
    assert _snapshot(admission) == before


@pytest.mark.parametrize("action", ["verify", "payout"])
@pytest.mark.parametrize("invalid", ["principal", "scope", "role", "admin", "wildcard", "empty", "payload"])
def test_exact_host_principal_scope_and_role_required(admission, action, invalid):
    principal, role = ("verifier_1", "verifier") if action == "verify" else ("treasury_1", "treasury")
    if action == "payout":
        _approved_fixture(admission)
    contexts = {
        "principal": _context("someone_else", {("f_1", role)}),
        "scope": _context(principal, {("other_foundup", role)}),
        "role": _context(principal, {("f_1", "advisory")}),
        "admin": _context(principal, {("f_1", "admin")}),
        "wildcard": _context(principal, {("*", role)}),
        "empty": _context(principal, set()),
        "payload": {"principal_id": principal, "role_grants": [("f_1", role)]},
    }
    before = _snapshot(admission)
    with pytest.raises(PermissionDeniedError):
        if action == "verify":
            admission.service.verify_proof("t_1", admission.decision, authorization=contexts[invalid])
        else:
            admission.service.trigger_payout("t_1", "treasury_1", authorization=contexts[invalid])
    assert _snapshot(admission) == before


def test_explicit_host_grants_work_without_legacy_actor_roles(admission):
    if admission.kind == "memory":
        admission.store.actor_roles.clear()
    task = admission.service.verify_proof(
        "t_1", admission.decision, authorization=_context("verifier_1", {("f_1", "verifier")}),
    )
    assert task.status is TaskStatus.VERIFIED
    payout = admission.service.trigger_payout(
        "t_1", "treasury_1", authorization=_context("treasury_1", {("f_1", "treasury")}),
    )
    assert payout.recipient_id == "agent_1"
    if admission.kind == "persistent":
        assert payout.reference is None and payout.paid_at is None
        assert admission.service.get_task("t_1").status is TaskStatus.VERIFIED
    else:
        assert admission.service.get_task("t_1").status is TaskStatus.PAID


def test_self_verification_denied_despite_explicit_role_and_compute(admission):
    before = _snapshot(admission)
    with pytest.raises(PermissionDeniedError):
        admission.service.verify_proof(
            "t_1", replace(admission.decision, verifier_id="agent_1"),
            authorization=_context("agent_1", {("f_1", "verifier")}),
        )
    assert _snapshot(admission) == before


@pytest.mark.parametrize("mismatch", ["decision_task", "proof_task", "submitter", "proof_pointer"])
def test_verification_requires_bound_task_and_proof(admission, mismatch):
    decision = admission.decision
    if mismatch == "decision_task":
        decision = replace(decision, task_id="different")
    elif admission.kind == "persistent":
        from sqlalchemy import update
        from modules.foundups.agent_market.src.persistence.sqlite_adapter import Base
        table = Base.metadata.tables["tasks" if mismatch == "proof_pointer" else "proofs"]
        changes = {"proof_id": "missing"} if mismatch == "proof_pointer" else {
            "task_id" if mismatch == "proof_task" else "submitter_id": "different",
        }
        with admission.store.engine.begin() as conn:
            conn.execute(update(table).values(**changes))
    elif mismatch == "proof_pointer":
        admission.store.tasks["t_1"].proof_id = "missing"
    else:
        setattr(admission.store.proofs["proof_1"], "task_id" if mismatch == "proof_task" else "submitter_id", "different")
    before = _snapshot(admission)
    with pytest.raises(AgentMarketError):
        admission.service.verify_proof(
            "t_1", decision, authorization=_context("verifier_1", {("f_1", "verifier")}),
        )
    assert _snapshot(admission) == before


@pytest.mark.parametrize("role", ["verifier", "treasury", "admin"])
def test_self_declared_profile_is_not_authority(admission, role):
    profile = AgentProfile("verifier_1", "self declared", [], role)
    if admission.kind == "persistent":
        admission.store.create_agent_profile("f_1", profile)
    else:
        request = admission.store.submit_join_request("f_1", profile)
        admission.store.approve_join_request(request, "owner_1")
    before = _snapshot(admission)
    with pytest.raises(PermissionDeniedError):
        admission.service.verify_proof("t_1", admission.decision)
    assert _snapshot(admission) == before


@pytest.mark.parametrize("action", ["verify", "payout"])
@pytest.mark.parametrize("admission", ["persistent"], indirect=True)
def test_persistent_retry_requires_explicit_call_authorization(admission, action):
    if action == "verify":
        admission.service.verify_proof("t_1", admission.decision, authorization=_context("verifier_1", {("f_1", "verifier")}))
    else:
        _approved_fixture(admission)
        admission.service.trigger_payout("t_1", "treasury_1", authorization=_context("treasury_1", {("f_1", "treasury")}))
    before = _snapshot(admission)
    principal, role = ("verifier_1", "verifier") if action == "verify" else ("treasury_1", "treasury")
    for context in (
        None, _context("someone_else", {("f_1", role)}),
        _context(principal, {("other_foundup", role)}), _context(principal, {("f_1", "admin")}),
    ):
        with pytest.raises(PermissionDeniedError):
            if action == "verify":
                admission.service.verify_proof("t_1", admission.decision, authorization=context)
            else:
                admission.service.trigger_payout("t_1", "treasury_1", authorization=context)
        assert _snapshot(admission) == before


@pytest.mark.parametrize("admission", ["persistent"], indirect=True)
def test_direct_adapter_payout_cannot_bypass_authorization(admission):
    _approved_fixture(admission)
    before = _snapshot(admission)
    with pytest.raises(PermissionDeniedError):
        admission.store.initiate_payout("t_1", "treasury_1")
    assert _snapshot(admission) == before
    payout = admission.store.initiate_payout(
        "t_1", "treasury_1", authorization=_context("treasury_1", {("f_1", "treasury")}),
    )
    assert payout.reference is None and payout.paid_at is None
    before = _snapshot(admission)
    for context in (None, _context("treasury_1", {("different", "treasury")})):
        with pytest.raises(PermissionDeniedError):
            admission.store.initiate_payout("t_1", "treasury_1", authorization=context)
        assert _snapshot(admission) == before


@pytest.mark.parametrize("admission,entrypoint", [
    ("memory", "pipeline"), ("persistent", "pipeline"), ("persistent", "direct"),
], indirect=["admission"])
@pytest.mark.parametrize("corruption", ["self_verifier", "proof_task", "submitter", "decision_task", "proof_pointer"])
def test_payout_requires_bound_independent_stored_verification(admission, entrypoint, corruption):
    _approved_fixture(admission)
    if admission.kind == "persistent":
        from sqlalchemy import update
        from modules.foundups.agent_market.src.persistence.sqlite_adapter import Base
        table_name, changes = {
            "self_verifier": ("verifications", {"verifier_id": "agent_1"}),
            "proof_task": ("proofs", {"task_id": "different"}),
            "submitter": ("proofs", {"submitter_id": "different"}),
            "decision_task": ("verifications", {"task_id": "different"}),
            "proof_pointer": ("tasks", {"proof_id": "missing"}),
        }[corruption]
        with admission.store.engine.begin() as conn:
            conn.execute(update(Base.metadata.tables[table_name]).values(**changes))
    elif corruption == "self_verifier":
        admission.store.verifications["decision_1"].verifier_id = "agent_1"
    elif corruption == "decision_task":
        admission.store.verifications["decision_1"].task_id = "different"
    elif corruption == "proof_pointer":
        admission.store.tasks["t_1"].proof_id = "missing"
    else:
        setattr(admission.store.proofs["proof_1"], "task_id" if corruption == "proof_task" else "submitter_id", "different")
    before = _snapshot(admission)
    operation = admission.store.initiate_payout if entrypoint == "direct" else admission.service.trigger_payout
    expected = PermissionDeniedError if corruption == "self_verifier" else AgentMarketError
    with pytest.raises(expected):
        operation("t_1", "treasury_1", authorization=_context("treasury_1", {("f_1", "treasury")}))
    assert _snapshot(admission) == before


@pytest.mark.parametrize("principal,grants", [
    ("", frozenset()), (None, frozenset()), ("actor", []),
    ("actor", frozenset({"f_1"})), ("actor", frozenset({("f_1",)})),
    ("actor", frozenset({("f_1", "")})), ("actor", frozenset({(1, "verifier")})),
])
def test_authorization_context_rejects_malformed_content(principal, grants):
    from modules.foundups.agent_market.src.authorization import CallerAuthorization
    with pytest.raises(ValidationError):
        CallerAuthorization(principal, grants)


def test_authorization_context_is_deeply_immutable():
    context = _context("verifier_1", {("f_1", "verifier")})
    with pytest.raises(FrozenInstanceError):
        context.principal_id = "different"
    with pytest.raises(AttributeError):
        context.role_grants.add(("other", "verifier"))
