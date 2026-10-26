"""Independent-assurance finalization and revocation regressions."""
# ruff: noqa: F405 - names are supplied by the shared split-test namespace.

from modules.infrastructure.database.tests.signed_worker_assurance_test_support import *  # noqa: F403, F405

def test_signed_worker_finalization_atomically_completes_assurance_and_ledger(
    agent_db: AgentDB,
) -> None:
    admitted, result_context = _prepare_assurance_finalization(agent_db)
    completion = result_context["signed_worker_task_last_result"][
        "assurance_completion_request"
    ]

    finalized = finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=result_context,
        assurance_completion=completion,
    )

    assert finalized is True
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None and task["status"] == "completed"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "VERIFIED"
    rows = agent_db.db.execute_query(
        "SELECT attempt_sequence FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        ("verifier-task",),
    )
    assert [row["attempt_sequence"] for row in rows] == [1]

def test_assurance_and_task_roll_back_when_result_ledger_rejects(
    agent_db: AgentDB,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admitted, result_context = _prepare_assurance_finalization(agent_db)
    completion = result_context["signed_worker_task_last_result"][
        "assurance_completion_request"
    ]
    monkeypatch.setattr(
        "modules.infrastructure.database.src.signed_worker_execution_commit."
        "persist_result_history_ledger",
        lambda *_args, **_kwargs: False,
    )

    finalized = finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=result_context,
        assurance_completion=completion,
    )

    assert finalized is False
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None and task["status"] == "executing"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"
    rows = agent_db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        ("verifier-task",),
    )
    assert rows == []

def test_assurance_task_rejects_missing_or_tampered_completion_request(
    agent_db: AgentDB,
) -> None:
    admitted, result_context = _prepare_assurance_finalization(agent_db)
    completion = dict(
        result_context["signed_worker_task_last_result"][
            "assurance_completion_request"
        ]
    )

    assert finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=result_context,
    ) is False
    completion["terminal_receipt_digest"] = "sha256:" + "f" * 64
    assert finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=result_context,
        assurance_completion=completion,
    ) is False
    exact = dict(
        result_context["signed_worker_task_last_result"][
            "assurance_completion_request"
        ]
    )
    assert agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations "
        "SET staged_completion_json = NULL, staged_completion_digest = NULL "
        "WHERE reservation_id = ?",
        ("assurance-1",),
    ) == 1
    assert finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=result_context,
        assurance_completion=exact,
    ) is False
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"

def test_attacker_recomputed_result_cannot_replace_staged_assurance(
    agent_db: AgentDB,
) -> None:
    admitted, legitimate_context = _prepare_assurance_finalization(agent_db)
    forged = dict(
        legitimate_context["signed_worker_task_last_result"][
            "assurance_completion_request"
        ]
    )
    forged["terminal_receipt_digest"] = "sha256:" + "f" * 64
    forged_receipt = build_signed_worker_task_result_receipt(
        base_context=admitted,
        claim_status="ACCEPT",
        result={
            "accepted": True,
            "decision": "VERIFIED",
            "receipt_id": "attacker-recomputed-result",
            "capability": "independent_slice_verification",
        },
        runner_result={
            "accepted": True,
            "bootstrap_result": {
                "assurance_completion_request": forged,
            },
        },
    )
    forged_context = append_signed_worker_result_history(
        admitted,
        forged_receipt,
    )

    finalized = finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=forged_context,
        assurance_completion=forged,
    )

    assert finalized is False
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None and task["status"] == "executing"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"

def test_finalizer_rejects_authenticated_capability_reclassification(
    agent_db: AgentDB,
) -> None:
    admitted, _legitimate_context = _prepare_assurance_finalization(agent_db)
    reclassified = {
        **admitted,
        "capability": "candidate_queue_review",
    }
    receipt = build_signed_worker_task_result_receipt(
        base_context=reclassified,
        claim_status="ACCEPT",
        result={
            "accepted": True,
            "decision": "COMPLETE",
            "receipt_id": "reclassified-result",
            "capability": "candidate_queue_review",
        },
    )
    result_context = append_signed_worker_result_history(
        reclassified,
        receipt,
    )

    assert finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=result_context,
    ) is False
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None and task["status"] == "executing"
    assert task["context"]["capability"] == "independent_slice_verification"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"
    rows = agent_db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        ("verifier-task",),
    )
    assert rows == []

def test_signed_envelope_assurance_cannot_be_hidden_by_top_level_context(
    agent_db: AgentDB,
) -> None:
    admitted, result_context = _prepare_assurance_finalization(
        agent_db,
        top_level_capability="candidate_queue_review",
        envelope_capability="independent_slice_verification",
    )

    assert finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=result_context,
    ) is False
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None and task["status"] == "executing"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"

@pytest.mark.parametrize(
    ("accepted", "target_status", "terminal_status"),
    (
        (True, "pending", "VERIFIED"),
        (False, "failed", "VERIFIED"),
        (True, "completed", "REJECT"),
    ),
)
def test_finalizer_rejects_contradictory_assurance_terminal_state(
    agent_db: AgentDB,
    accepted: bool,
    target_status: str,
    terminal_status: str,
) -> None:
    admitted, result_context = _prepare_assurance_finalization(agent_db)
    completion = dict(
        result_context["signed_worker_task_last_result"][
            "assurance_completion_request"
        ]
    )
    completion["terminal_status"] = terminal_status

    assert finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=accepted,
        result_context=result_context,
        target_status=target_status,
        assurance_completion=completion,
    ) is False
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None and task["status"] == "executing"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"

def test_finalizer_rejects_receipt_status_contradiction(
    agent_db: AgentDB,
) -> None:
    admitted, result_context = _prepare_assurance_finalization(agent_db)
    completion = result_context["signed_worker_task_last_result"][
        "assurance_completion_request"
    ]
    result_context["signed_worker_task_last_result"] = {
        **result_context["signed_worker_task_last_result"],
        "accepted": False,
        "claim_status": "REJECT",
    }

    assert finalize_signed_worker_execution(
        agent_db,
        "verifier-task",
        context=admitted,
        accepted=True,
        result_context=result_context,
        assurance_completion=completion,
    ) is False
    task = agent_db.get_autonomous_task_by_id("verifier-task")
    assert task is not None and task["status"] == "executing"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "RESERVED"

def test_revoked_reservation_is_terminal_and_verifier_is_cancelled(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    assert agent_db.reserve_independent_assurance(_request())["accepted"] is True

    revoked = agent_db.revoke_independent_assurance(
        "assurance-1",
        reason="authority_revoked",
        now_iso=_iso(),
    )
    loaded = agent_db.get_independent_assurance_reservation("assurance-1")

    assert revoked["accepted"] is True
    assert revoked["status"] == "REVOKED"
    assert loaded is not None
    assert loaded["accepted"] is False
    assert loaded["status"] == "REVOKED"
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "cancelled"

def test_revocation_cancels_an_executing_signed_verifier(
    agent_db: AgentDB,
) -> None:
    task_id, _ = _prepare_signed_verifier_recovery(
        agent_db,
        terminal_status="REJECT",
    )

    revoked = agent_db.revoke_independent_assurance(
        "assurance-1",
        reason="authority_revoked_during_execution",
        now_iso=_iso(),
    )

    assert revoked["accepted"] is True
    task = agent_db.get_autonomous_task_by_id(task_id)
    assert task is not None and task["status"] == "cancelled"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation is not None
    assert reservation["reservation"]["status"] == "REVOKED"
