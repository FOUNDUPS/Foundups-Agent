"""Signed-worker envelope authority and supervisor admission regressions."""
# ruff: noqa: F405 - names are supplied by the shared split-test namespace.

from modules.communication.moltbot_bridge.tests.reddog_signed_worker_agentdb_test_support import *  # noqa: F403, F405

@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("signed_worker_agentdb_envelope",), {}),
        (
            ("signed_worker_agentdb_envelope", "schema_version"),
            "reddog_signed_worker_agentdb_envelope.v999",
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "worker_dispatch_intent",
                "capability",
            ),
            "unbounded_repo_write",
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "worker_dispatch_intent",
                "intent_id",
            ),
            "worker_dispatch_intent_attacker",
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "signed_authority_worker_dispatch_receipt",
                "receipt_id",
            ),
            "signed_authority_worker_dispatch_attacker",
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "signed_authority_worker_dispatch_receipt",
                "architect_fix_publication_binding_digest",
            ),
            "sha256:attacker-publication",
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "signed_authority_worker_dispatch_receipt",
                "memex_supply_digest",
            ),
            "sha256:attacker-memex",
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "queue_authority_runtime_result",
                "authority_result",
                "work_authority",
                "memex_supply_receipt_id",
            ),
            "sha256:attacker-memex",
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "wsp15_allocation_receipt",
                "mps_total",
            ),
            1,
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "queue_consumer_receipt",
                "operational_snapshot_id",
            ),
            "sha256:" + ("f" * 64),
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "agentdb_task_binding",
                "task_id",
            ),
            "reddog-worker-dispatch-attacker",
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "queue_authority_runtime_result",
                "authority_result",
                "identity",
                "principal_public_key",
            ),
            "pub:attacker",
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "queue_authority_runtime_result",
                "authority_result",
                "work_authority",
                "requested_operation",
            ),
            "unbounded_repo_write",
        ),
    ),
)
def test_claim_rejects_tampered_envelope_before_runner_selection(
    tmp_path: Path,
    path: tuple[object, ...],
    value: object,
) -> None:
    task_id = _publish_agentdb_task()
    _rewrite_context(
        task_id,
        lambda context: _set_nested(context, path, value),
    )
    runner = _FakeRunner()

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REJECT
    assert set(result["rejection_reasons"]) & {
        SignedWorkerOpenClawClaimReason.AGENTDB_ENVELOPE_REJECTED,
        SignedWorkerOpenClawClaimReason.CLAIM_RACE_LOST,
    }
    assert runner.calls == []
    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert stored["status"] in {"failed", "quarantined"}
    if stored["status"] == "quarantined":
        quarantine = (
            stored["context"].get("signed_worker_assignment_quarantine")
            or stored["context"]["signed_worker_execution_quarantine"]
        )
        assert quarantine["reason"] in {
            "invalid_signed_worker_assignment",
            "signed_worker_agentdb_envelope_rejected",
        }
        assert (
            quarantine.get("no_worker_effect_performed") is True
            or quarantine.get("no_worker_effect_replayed") is True
        )
        assert quarantine["receipt_id"].startswith("sha256:")

def test_quarantined_invalid_task_does_not_block_next_valid_task(
    tmp_path: Path,
) -> None:
    invalid_task_id = _publish_agentdb_task()
    _rewrite_context(
        invalid_task_id,
        lambda context: context.update(source="attacker"),
    )
    valid_task_id = _publish_agentdb_task(
        intent_id="worker_dispatch_intent_openclaw_candidate_2"
    )
    runner = _FakeRunner()
    db = AgentDB()

    assert not db.assign_signed_worker_task(invalid_task_id)
    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    assert db.get_autonomous_task_by_id(invalid_task_id)[
        "status"
    ] == "quarantined"
    assert result["accepted"] is True
    assert db.get_autonomous_task_by_id(valid_task_id)[
        "status"
    ] == "completed"

def test_claim_time_preflight_is_restart_safe_and_non_consuming() -> None:
    task_id = _publish_agentdb_task()
    task = AgentDB().get_autonomous_task_by_id(task_id)
    assert task is not None
    envelope = task["context"]["signed_worker_agentdb_envelope"]
    authority = worker_dispatch_authority_verification_context()

    first = verify_reddog_signed_worker_agentdb_envelope(
        envelope=envelope,
        task_id=task_id,
        authority_context=authority,
    )
    second = verify_reddog_signed_worker_agentdb_envelope(
        envelope=envelope,
        task_id=task_id,
        authority_context=authority,
    )

    assert first.task_id == task_id
    assert second.canonical_context == first.canonical_context

def test_supervisor_execution_runs_inside_lease_heartbeat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modules.communication.moltbot_bridge.src import (
        reddog_signed_worker_execution_heartbeat as heartbeat_module,
    )

    task_id = _publish_agentdb_task()
    calls: list[str] = []

    @contextmanager
    def observed_heartbeat(**kwargs):
        calls.append(str(kwargs["task_id"]))
        yield SimpleNamespace(healthy=True, renewal_count=1)

    monkeypatch.setattr(
        heartbeat_module,
        "signed_worker_execution_heartbeat",
        observed_heartbeat,
    )
    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    assert result["accepted"] is True
    assert calls == [task_id]

def test_supervisor_lease_renewal_failure_is_indeterminate_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modules.communication.moltbot_bridge.src import (
        reddog_signed_worker_execution_heartbeat as heartbeat_module,
    )

    task_id = _publish_agentdb_task()

    @contextmanager
    def failed_heartbeat(**_):
        yield SimpleNamespace(healthy=False, renewal_count=0)

    monkeypatch.setattr(
        heartbeat_module,
        "signed_worker_execution_heartbeat",
        failed_heartbeat,
    )
    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    assert result["accepted"] is False
    assert (
        SignedWorkerOpenClawClaimReason.EXECUTION_LEASE_RENEWAL_FAILED
        in result["rejection_reasons"]
    )
    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "failed"
    assert stored["context"]["signed_worker_task_last_result"][
        "effect_commit_state"
    ] == "INDETERMINATE"

def test_supervisor_verifies_exact_claimed_database_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    original_admit = execution_claim_module.admit_signed_worker_execution_once

    def replace_then_admit(*, db, task_id, authority_context):
        assert db.db.execute_write(
            "UPDATE agents_autonomous_tasks "
            "SET context = ?, required_skills = ?, discovered_by = ? "
            "WHERE task_id = ? AND status = 'assigned'",
            (json.dumps({}), json.dumps(["attacker_skill"]), "attacker", task_id),
        ) == 1
        return original_admit(
            db=db, task_id=task_id, authority_context=authority_context
        )

    monkeypatch.setattr(
        supervisor_admission_module,
        "admit_signed_worker_execution_once",
        replace_then_admit,
    )
    runner = _FakeRunner()
    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REJECT
    assert runner.calls == []
    assert stored is not None and stored["status"] == "quarantined"
