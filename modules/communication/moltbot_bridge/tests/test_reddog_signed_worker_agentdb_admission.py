"""Signed-worker use-time authority and competing-admission regressions."""
# ruff: noqa: F405 - names are supplied by the shared split-test namespace.

from modules.communication.moltbot_bridge.tests.reddog_signed_worker_agentdb_test_support import *  # noqa: F403, F405

@pytest.mark.parametrize("authority_failure", ("expired", "revoked"))
def test_claim_rejects_invalid_use_time_authority_before_runner_selection(
    tmp_path: Path,
    authority_failure: str,
) -> None:
    _publish_agentdb_task()
    authority = worker_dispatch_authority_verification_context()
    if authority_failure == "expired":
        authority = replace(authority, trusted_now_epoch=lambda: 2000)
    else:
        authority = replace(
            authority,
            revocation_oracle=SimpleNamespace(is_revoked=lambda **_: True),
        )
    runner = _FakeRunner()

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=authority,
    )

    assert result["accepted"] is False
    assert (
        SignedWorkerOpenClawClaimReason.AGENTDB_ENVELOPE_REJECTED
        in result["rejection_reasons"]
    )
    assert runner.calls == []

@pytest.mark.parametrize(
    "tamper",
    ("source", "required_skills", "all_mutable_markers"),
)
def test_run_task_signed_markers_never_fall_through_to_wre(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    if tamper == "source":
        _rewrite_context(task_id, lambda context: context.update(source="attacker"))
    elif tamper == "required_skills":
        assert db.db.execute_write(
            "UPDATE agents_autonomous_tasks SET required_skills = ? WHERE task_id = ?",
            (json.dumps(["attacker_skill"]), task_id),
        ) == 1
    else:
        _rewrite_context(task_id, lambda context: context.clear())
        assert db.db.execute_write(
            "UPDATE agents_autonomous_tasks "
            "SET required_skills = ?, discovered_by = ? WHERE task_id = ?",
            (json.dumps(["attacker_skill"]), "attacker", task_id),
        ) == 1
    assert not db.assign_signed_worker_task(task_id)
    monkeypatch.setenv(
        "WRE_MOCK_SKILLS",
        f"{runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL},attacker_skill",
    )
    runner = _FakeRunner()

    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=runner,
    )

    assert result["ok"] is False
    assert result["executor"] == "none"
    assert "not found in 'assigned' state" in result["detail"]
    assert runner.calls == []

def test_competing_preverification_claim_is_never_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)

    def competing_claim(*, db, task_id, verified_envelope):
        assert db.db.execute_write(
            "UPDATE agents_autonomous_tasks SET status = 'executing' "
            "WHERE task_id = ? AND status = 'assigned'",
            (task_id,),
        ) == 1
        return None

    monkeypatch.setattr(
        run_task_runtime,
        "admit_signed_worker_execution_once",
        competing_claim,
    )
    result = execute_task(task_id, repo_root=tmp_path)

    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert result["ok"] is False
    assert result["finalization_owned"] is True
    assert result["executor"] == "reddog:signed_worker_dispatch"
    assert stored is not None and stored["status"] == "executing"

def test_successful_admission_verifies_exact_claimed_database_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    original_admit = run_task_runtime.admit_signed_worker_execution_once

    def replace_then_admit(*, db, task_id, verified_envelope):
        assert db.db.execute_write(
            "UPDATE agents_autonomous_tasks "
            "SET context = ?, required_skills = ?, discovered_by = ? "
            "WHERE task_id = ? AND status = 'assigned'",
            (json.dumps({}), json.dumps(["attacker_skill"]), "attacker", task_id),
        ) == 1
        return original_admit(
            db=db, task_id=task_id, verified_envelope=verified_envelope
        )

    monkeypatch.setattr(
        run_task_runtime,
        "admit_signed_worker_execution_once",
        replace_then_admit,
    )
    runner = _FakeRunner()
    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=runner,
    )

    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert result["ok"] is False
    assert result["finalization_owned"] is True
    assert "execution_already_claimed" in result["detail"]
    assert runner.calls == []
    assert stored is not None and stored["status"] == "quarantined"

def test_tampered_expired_verifier_never_renews_assurance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task(
        intent_id="worker_dispatch_intent_independent_slice_verifier",
        role="independent_slice_verifier",
        worker_runtime="openclaw",
        capability="independent_slice_verification",
    )
    _rewrite_context(
        task_id,
        lambda context: _set_nested(
            context,
            (
                "signed_worker_agentdb_envelope",
                "worker_dispatch_intent",
                "capability",
            ),
            "attacker_capability",
        ),
    )
    db = AgentDB()
    assert db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'expired' WHERE task_id = ?",
        (task_id,),
    ) == 1
    effects: list[str] = []
    monkeypatch.setattr(
        db,
        "get_independent_assurance_reservation_for_task",
        lambda *_args, **_kwargs: effects.append("reservation-read"),
    )
    monkeypatch.setattr(
        db,
        "renew_independent_assurance",
        lambda *_args, **_kwargs: effects.append("renewal"),
    )
    monkeypatch.setattr(
        supervisor_module,
        "_openclaw_independent_verifier_ready_from_env",
        lambda *_args, **_kwargs: True,
    )

    from modules.communication.moltbot_bridge.src.reddog_signed_worker_claim_admission import (
        rehydrate_signed_worker_agentdb_context,
        renew_expired_verified_assurance,
    )
    from modules.communication.moltbot_bridge.src.reddog_signed_worker_openclaw_queue_loop_runtime_binding import (
        is_openclaw_independent_verifier_signed_worker_context,
    )

    env = {"REDDOG_RESIDENT_QUEUE_NOW_ISO": "2026-07-16T00:00:00+00:00"}
    renew_expired_verified_assurance(
        db=db,
        source=runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        env=env,
        repo_root=tmp_path,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
        rehydrate=lambda **kwargs: rehydrate_signed_worker_agentdb_context(
            **kwargs,
            env=env,
        ),
        is_verifier_context=(
            is_openclaw_independent_verifier_signed_worker_context
        ),
        is_stage_ready=(
            supervisor_module._openclaw_independent_verifier_ready_from_env
        ),
    )

    assert effects == []
    assert db.get_autonomous_task_by_id(task_id)["status"] == "expired"
