"""Independent-assurance lease and schema migration regressions."""
# ruff: noqa: F405 - names are supplied by the shared split-test namespace.

from modules.infrastructure.database.tests.signed_worker_assurance_test_support import *  # noqa: F403, F405

def test_get_expires_elapsed_reservation_and_verifier_task(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    assert agent_db.reserve_independent_assurance(
        _request(expires_at=_iso(1))
    )["accepted"] is True
    agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations SET expires_at = ? "
        "WHERE reservation_id = ?",
        (_iso(-1), "assurance-1"),
    )

    loaded = agent_db.get_independent_assurance_reservation("assurance-1")

    assert loaded is not None
    assert loaded["accepted"] is False
    assert loaded["status"] == "EXPIRED"
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "expired"

def test_expired_reservation_renews_after_author_completes(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    admitted = agent_db.reserve_independent_assurance(_request())
    assert admitted["accepted"] is True
    admission_digest = admitted["reservation"]["reservation_digest"]
    assert agent_db.complete_autonomous_task("author-task")
    agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations SET expires_at = ? "
        "WHERE reservation_id = ?",
        (_iso(-1), "assurance-1"),
    )
    expired = agent_db.get_independent_assurance_reservation("assurance-1")
    assert expired is not None
    assert expired["status"] == "EXPIRED"

    renewal = build_assurance_renewal_request(
        expired["reservation"],
        now=datetime.now(timezone.utc),
    )
    renewed = agent_db.renew_independent_assurance(renewal)

    assert renewed["accepted"] is True
    reservation = renewed["reservation"]
    assert reservation["status"] == "RESERVED"
    assert reservation["renewal_count"] == 1
    assert reservation["admission_reservation_digest"] == admission_digest
    assert reservation["reservation_digest"] != admission_digest
    verifier = agent_db.get_autonomous_task_by_id("verifier-task")
    assert verifier is not None
    assert verifier["status"] == "assigned"
    assert verifier["completed_at"] is None

def test_renewal_cannot_extend_beyond_total_admission_horizon(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    assert agent_db.reserve_independent_assurance(_request())["accepted"] is True
    assert agent_db.complete_autonomous_task("author-task")
    agent_db.db.execute_write(
        """
        UPDATE agents_independent_assurance_reservations
        SET expires_at = ?, admission_reserved_at = ?
        WHERE reservation_id = ?
        """,
        (_iso(-1), _iso(-7201), "assurance-1"),
    )
    expired = agent_db.get_independent_assurance_reservation("assurance-1")
    assert expired is not None

    renewed = agent_db.renew_independent_assurance(
        build_assurance_renewal_request(
            expired["reservation"],
            now=datetime.now(timezone.utc),
        )
    )

    assert renewed["accepted"] is False
    assert renewed["rejection_reasons"] == [
        "renewal_horizon_exceeds_maximum"
    ]
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "expired"

def test_expired_reservation_cannot_renew_before_author_completes(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    assert agent_db.reserve_independent_assurance(_request())["accepted"] is True
    agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations SET expires_at = ? "
        "WHERE reservation_id = ?",
        (_iso(-1), "assurance-1"),
    )
    expired = agent_db.get_independent_assurance_reservation("assurance-1")
    assert expired is not None

    renewed = agent_db.renew_independent_assurance(
        build_assurance_renewal_request(
            expired["reservation"],
            now=datetime.now(timezone.utc),
        )
    )

    assert renewed["accepted"] is False
    assert renewed["rejection_reasons"] == ["author_task_not_completed"]
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "expired"

def test_renewal_rejects_forged_digest(agent_db: AgentDB) -> None:
    _seed_tasks(agent_db)
    assert agent_db.reserve_independent_assurance(_request())["accepted"] is True
    assert agent_db.complete_autonomous_task("author-task")
    agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations SET expires_at = ? "
        "WHERE reservation_id = ?",
        (_iso(-1), "assurance-1"),
    )
    expired = agent_db.get_independent_assurance_reservation("assurance-1")
    assert expired is not None
    request = build_assurance_renewal_request(
        expired["reservation"],
        now=datetime.now(timezone.utc),
    )
    request["reservation_digest"] = "sha256:" + "0" * 64

    renewed = agent_db.renew_independent_assurance(request)

    assert renewed["accepted"] is False
    assert renewed["rejection_reasons"] == ["reservation_digest_mismatch"]

def test_reservation_rejects_lease_longer_than_six_hours(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)

    result = agent_db.reserve_independent_assurance(
        _request(expires_at=_iso((6 * 60 * 60) + 60))
    )

    assert result["accepted"] is False
    assert result["rejection_reasons"] == [
        "reservation_window_exceeds_maximum"
    ]

def test_expiry_rolls_back_if_verifier_task_state_was_tampered(
    agent_db: AgentDB,
) -> None:
    _seed_tasks(agent_db)
    assert agent_db.reserve_independent_assurance(_request())["accepted"] is True
    agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations SET expires_at = ? "
        "WHERE reservation_id = ?",
        (_iso(-1), "assurance-1"),
    )
    agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'completed' WHERE task_id = ?",
        ("verifier-task",),
    )

    loaded = agent_db.get_independent_assurance_reservation("assurance-1")

    assert loaded is not None
    assert loaded["accepted"] is False
    assert loaded["rejection_reasons"] == [
        "verifier_task_expiration_transition_failed"
    ]
    row = agent_db.db.execute_query(
        "SELECT status FROM agents_independent_assurance_reservations "
        "WHERE reservation_id = ?",
        ("assurance-1",),
    )
    assert row[0]["status"] == "RESERVED"

def test_legacy_autonomous_tasks_gain_nullable_retry_not_before(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "legacy-assurance.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE agents_autonomous_tasks (
            task_id TEXT PRIMARY KEY,
            description TEXT,
            required_skills JSON,
            estimated_complexity REAL,
            priority_score REAL,
            discovered_by TEXT DEFAULT 'autonomous_discovery',
            discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            context JSON,
            assigned_to TEXT,
            assigned_at DATETIME
        )
        """
    )
    connection.execute(
        """
        INSERT INTO agents_autonomous_tasks (
            task_id, description, required_skills, estimated_complexity, priority_score
        ) VALUES ('legacy-task', 'legacy', '[]', 0.1, 1.0)
        """
    )
    connection.commit()
    connection.close()

    monkeypatch.setenv("FOUNDUPS_DB_ENGINE", "sqlite")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(db_path))
    DatabaseManager.reset_for_tests()
    migrated = AgentDB()

    column_info = migrated.db.get_table_info("agents_autonomous_tasks")
    columns = {row["name"] for row in column_info}
    assert "retry_not_before" in columns
    retry_column = next(
        row for row in column_info if row["name"] == "retry_not_before"
    )
    assert retry_column["type"].upper() == "TIMESTAMP"
    task = migrated.get_autonomous_task_by_id("legacy-task")
    assert task is not None
    assert task["retry_not_before"] is None

def test_legacy_assurance_table_gains_staging_columns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "legacy-assurance-staging.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE agents_independent_assurance_reservations (
            reservation_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            reservation_digest TEXT NOT NULL,
            reserved_at TIMESTAMP NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()

    monkeypatch.setenv("FOUNDUPS_DB_ENGINE", "sqlite")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(db_path))
    DatabaseManager.reset_for_tests()
    migrated = AgentDB()

    columns = {
        row["name"]
        for row in migrated.db.get_table_info(
            "agents_independent_assurance_reservations"
        )
    }
    assert {
        "admission_reservation_digest",
        "admission_reserved_at",
        "renewal_count",
        "staged_completion_json",
        "staged_completion_digest",
        "staged_at",
    } <= columns

def test_fresh_schema_contains_dedicated_assurance_table(agent_db: AgentDB) -> None:
    columns = {
        row["name"]
        for row in agent_db.db.get_table_info(
            "agents_independent_assurance_reservations"
        )
    }
    assert {
        "reservation_id",
        "request_schema_version",
        "work_order_id",
        "queue_item_id",
        "author_task_id",
        "author_principal_id",
        "verifier_task_id",
        "verifier_principal_id",
        "capability",
        "worker_runtime",
        "operational_snapshot_id",
        "wsp15_allocation_receipt_id",
        "lease_id",
        "reserved_at",
        "expires_at",
        "reservation_digest",
        "admission_reservation_digest",
        "admission_reserved_at",
        "renewal_count",
        "status",
        "terminal_receipt_id",
        "terminal_receipt_digest",
        "terminal_status",
        "staged_completion_json",
        "staged_completion_digest",
        "staged_at",
        "completed_at",
        "revoked_at",
        "revocation_reason",
    } <= columns
    autonomous_columns = agent_db.db.get_table_info("agents_autonomous_tasks")
    retry_column = next(
        row for row in autonomous_columns if row["name"] == "retry_not_before"
    )
    assert retry_column["type"].upper() == "TIMESTAMP"
