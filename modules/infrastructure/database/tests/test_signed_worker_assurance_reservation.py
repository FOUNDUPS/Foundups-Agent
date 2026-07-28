"""Independent-assurance reservation and admission regressions."""
# ruff: noqa: F405 - names are supplied by the shared split-test namespace.

from modules.infrastructure.database.tests.signed_worker_assurance_test_support import *  # noqa: F403, F405

def test_reserve_claims_pending_verifier_and_rehydrates_after_restart(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)

    result = agent_db.reserve_independent_assurance(_request())

    assert result["accepted"] is True
    assert result["status"] == "RESERVED"
    reservation = result["reservation"]
    assert reservation["reservation_id"] == "assurance-1"
    assert reservation["reservation_digest"].startswith("sha256:")
    assert len(reservation["reservation_digest"]) == 71
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None
    assert task["status"] == "assigned"
    assert task["assigned_to"] == "verifier-0201"

    DatabaseManager.reset_for_tests()
    restarted = AgentDB()
    rehydrated = restarted.get_independent_assurance_reservation("assurance-1")
    assert rehydrated is not None
    assert rehydrated["accepted"] is True
    assert rehydrated["reservation"]["reservation_digest"] == reservation["reservation_digest"]

def test_concurrent_reservations_allow_exactly_one_winner(agent_db: AgentDB) -> None:
    _seed_tasks(agent_db)

    first = _request(reservation_id="assurance-a", lease_id="lease-a")
    second = _request(reservation_id="assurance-b", lease_id="lease-b")
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(agent_db.reserve_independent_assurance, (first, second))
        )

    assert sum(result["accepted"] is True for result in results) == 1
    assert sum(result["accepted"] is False for result in results) == 1
    rows = agent_db.db.execute_query(
        "SELECT reservation_id FROM agents_independent_assurance_reservations"
    )
    assert len(rows) == 1

def test_concurrent_author_work_order_reservations_rollback_losing_verifier_claim(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    _create_task(
        agent_db,
        task_id="verifier-task-2",
        role="independent_slice_verifier",
        principal_id="verifier-0302",
    )
    first = _request(reservation_id="assurance-a", lease_id="lease-a")
    second = _request(
        reservation_id="assurance-b",
        verifier_task_id="verifier-task-2",
        verifier_principal_id="verifier-0302",
        lease_id="lease-b",
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(agent_db.reserve_independent_assurance, (first, second))
        )

    accepted = [result for result in results if result["accepted"] is True]
    rejected = [result for result in results if result["accepted"] is False]
    assert len(accepted) == 1
    assert len(rejected) == 1
    winner_task_id = accepted[0]["reservation"]["verifier_task_id"]
    loser_task_id = (
        "verifier-task-2" if winner_task_id == "verifier-task" else "verifier-task"
    )
    assert agent_db.get_autonomous_task_by_id(winner_task_id)["status"] == "assigned"
    assert agent_db.get_autonomous_task_by_id(loser_task_id)["status"] == "pending"

@pytest.mark.parametrize(
    ("request_changes", "expected_reason"),
    [
        (
            {
                "verifier_task_id": "author-task",
                "verifier_principal_id": "verifier-0201",
            },
            "author_verifier_task_equality",
        ),
        (
            {"verifier_principal_id": "author-0102"},
            "author_verifier_principal_equality",
        ),
    ],
)
def test_reserve_rejects_author_or_principal_equality(
    agent_db: AgentDB,
    request_changes: dict[str, str],
    expected_reason: str,
) -> None:
    _seed_tasks(agent_db)

    result = agent_db.reserve_independent_assurance(_request(**request_changes))

    assert result["accepted"] is False
    assert expected_reason in result["rejection_reasons"]
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "pending"

@pytest.mark.parametrize(
    ("task_override", "request_override", "expected_reason"),
    [
        ({"role": "coding_worker"}, {}, "verifier_task_role_mismatch"),
        ({"capability": "other"}, {}, "verifier_task_capability_mismatch"),
        ({"worker_runtime": "hermes"}, {}, "verifier_task_worker_runtime_mismatch"),
        (
            {"operational_snapshot_id": "snapshot-other"},
            {},
            "verifier_task_operational_snapshot_id_mismatch",
        ),
        (
            {"wsp15_allocation_receipt_id": "wsp15-other"},
            {},
            "verifier_task_wsp15_allocation_receipt_id_mismatch",
        ),
        ({}, {"expires_at": _iso(-10)}, "reservation_expired"),
        ({}, {"reserved_at": _iso(600)}, "reserved_at_in_future"),
    ],
)
def test_reserve_rejects_malformed_expired_or_mismatched_requests(
    agent_db: AgentDB,
    task_override: dict[str, str],
    request_override: dict[str, str],
    expected_reason: str,
) -> None:
    _create_task(
        agent_db,
        task_id="author-task",
        role="coding_worker",
        principal_id="author-0102",
    )
    verifier = {
        "role": "independent_slice_verifier",
        "capability": "independent_diff_verification",
        "worker_runtime": "openclaw",
        "operational_snapshot_id": "snapshot-1",
        "wsp15_allocation_receipt_id": "wsp15-1",
    }
    verifier.update(task_override)
    _create_task(
        agent_db,
        task_id="verifier-task",
        role=verifier["role"],
        principal_id="verifier-0201",
        capability=verifier["capability"],
        worker_runtime=verifier["worker_runtime"],
        operational_snapshot_id=verifier["operational_snapshot_id"],
        wsp15_allocation_receipt_id=verifier["wsp15_allocation_receipt_id"],
    )

    result = agent_db.reserve_independent_assurance(
        _request(**request_override)
    )

    assert result["accepted"] is False
    assert expected_reason in result["rejection_reasons"]
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "pending"

def test_reserve_rejects_forged_digest(agent_db: AgentDB) -> None:
    _seed_tasks(agent_db)

    result = agent_db.reserve_independent_assurance(
        _request(reservation_digest="0" * 64)
    )

    assert result["accepted"] is False
    assert result["rejection_reasons"] == ["reservation_digest_mismatch"]

def test_reserve_accepts_bridge_canonical_prefixed_digest(agent_db: AgentDB) -> None:
    _seed_tasks(agent_db)
    request = _request()

    result = agent_db.reserve_independent_assurance(request)

    assert result["accepted"] is True
    assert (
        result["reservation"]["reservation_digest"]
        == request["reservation_digest"]
    )

def test_reserve_rejects_author_snapshot_mismatch(agent_db: AgentDB) -> None:
    _create_task(
        agent_db,
        task_id="author-task",
        role="coding_worker",
        principal_id="author-0102",
        operational_snapshot_id="snapshot-other",
    )
    _create_task(
        agent_db,
        task_id="verifier-task",
        role="independent_slice_verifier",
        principal_id="verifier-0201",
    )

    result = agent_db.reserve_independent_assurance(_request())

    assert result["accepted"] is False
    assert result["rejection_reasons"] == [
        "author_task_operational_snapshot_id_mismatch"
    ]

def test_reserve_rejects_terminal_author_task(agent_db: AgentDB) -> None:
    _seed_tasks(agent_db)
    assert agent_db.complete_autonomous_task("author-task")

    result = agent_db.reserve_independent_assurance(_request())

    assert result["accepted"] is False
    assert result["rejection_reasons"] == ["author_task_not_pending"]
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "pending"

def test_reserve_rejects_author_already_claimed_before_assurance(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    updated = agent_db.db.execute_write(
        """
        UPDATE agents_autonomous_tasks
        SET status = 'assigned', assigned_to = 'worker:unexpected'
        WHERE task_id = 'author-task'
        """
    )
    assert updated == 1

    result = agent_db.reserve_independent_assurance(_request())

    assert result["accepted"] is False
    assert result["rejection_reasons"] == ["author_task_not_pending"]
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "pending"

def test_detached_terminal_completion_is_rejected_without_mutation(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    assert agent_db.reserve_independent_assurance(_request())["accepted"] is True
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")[
        "reservation"
    ]

    completed = agent_db.complete_independent_assurance(
        "assurance-1",
        admission_reservation_digest=reservation[
            "admission_reservation_digest"
        ],
        terminal_receipt_id="verification-1",
        terminal_receipt_digest="sha256:" + "a" * 64,
        status="VERIFIED",
        now_iso=_iso(),
    )
    assert completed["accepted"] is False
    assert completed["rejection_reasons"] == [
        "completion_owned_by_signed_worker_finalizer"
    ]
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "assigned"
    persisted = agent_db.get_independent_assurance_reservation("assurance-1")
    assert persisted is not None
    assert persisted["reservation"]["status"] == "RESERVED"

def test_detached_completion_rejects_before_digest_interpretation(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    assert agent_db.reserve_independent_assurance(_request())["accepted"] is True

    completed = agent_db.complete_independent_assurance(
        "assurance-1",
        admission_reservation_digest="sha256:" + "f" * 64,
        terminal_receipt_id="verification-1",
        terminal_receipt_digest="sha256:" + "a" * 64,
        status="VERIFIED",
        now_iso=_iso(),
    )

    assert completed["accepted"] is False
    assert completed["rejection_reasons"] == [
        "completion_owned_by_signed_worker_finalizer"
    ]
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation["reservation"]["status"] == "RESERVED"
