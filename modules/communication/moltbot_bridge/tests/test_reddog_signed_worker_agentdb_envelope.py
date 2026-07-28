"""Security regressions for persisted signed-worker AgentDB envelopes."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.scripts.run_task import execute_task
from modules.communication.moltbot_bridge.src import (
    openclaw_supervisor as supervisor_module,
    reddog_openclaw_hermes_0102_worker_dispatch_runtime as runtime,
)
from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
    SIGNED_WORKER_OPENCLAW_CLAIM_REJECT,
    SignedWorkerOpenClawClaimReason,
    claim_reddog_signed_worker_dispatch_task_once,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_agentdb_envelope import (
    verify_reddog_signed_worker_agentdb_envelope,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    worker_dispatch_authority_verification_context,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_worker_dispatch_task_executor import (
    _FakeRunner,
    _publish_agentdb_task,
)
from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager


@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    monkeypatch.setenv("OPENCLAW_SIGNED_QUEUE_STAGE_TASKS_ENABLED", "1")
    DatabaseManager.reset_for_tests()
    from modules.communication.moltbot_bridge.src import (
        reddog_signed_worker_agentdb_envelope as envelope_module,
    )

    monkeypatch.setattr(
        envelope_module,
        "build_worker_dispatch_authority_context_from_env",
        lambda **_: worker_dispatch_authority_verification_context(),
    )
    yield
    DatabaseManager.reset_for_tests()


def _rewrite_context(task_id: str, mutate) -> dict[str, object]:
    db = AgentDB()
    task = db.get_autonomous_task_by_id(task_id)
    assert task is not None
    context = json.loads(json.dumps(task["context"]))
    mutate(context)
    assert db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET context = ? WHERE task_id = ?",
        (json.dumps(context, sort_keys=True), task_id),
    ) == 1
    return context


def _set_nested(
    mapping: dict[str, object],
    path: tuple[object, ...],
    value: object,
) -> None:
    cursor: object = mapping
    for key in path[:-1]:
        cursor = cursor[key]  # type: ignore[index]
    cursor[path[-1]] = value  # type: ignore[index]


def test_run_task_rebuilds_canonical_context_before_runner_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    _rewrite_context(
        task_id,
        lambda context: context.update(
            {
                "worker_runtime": "hermes",
                "worker_role": "attacker",
                "capability": "unbounded_repo_write",
                "worker_dispatch_intent": {
                    **dict(context["worker_dispatch_intent"]),
                    "worker_runtime": "hermes",
                    "role": "attacker",
                    "capability": "unbounded_repo_write",
                },
            }
        ),
    )
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    runner = _FakeRunner()

    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=runner,
    )

    assert result["ok"] is True
    assert len(runner.calls) == 1
    canonical = runner.calls[0]["task_context"]
    assert canonical["worker_runtime"] == "openclaw"
    assert canonical["worker_role"] == "openclaw_candidate"
    assert canonical["capability"] == "candidate_queue_review"


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
    assert (
        SignedWorkerOpenClawClaimReason.AGENTDB_ENVELOPE_REJECTED
        in result["rejection_reasons"]
    )
    assert runner.calls == []
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "failed"


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


@pytest.mark.parametrize("authority_failure", ("expired", "revoked"))
def test_claim_rejects_invalid_use_time_authority_before_runner_selection(
    tmp_path: Path,
    authority_failure: str,
) -> None:
    task_id = _publish_agentdb_task()
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
            "UPDATE agents_autonomous_tasks SET required_skills = ? WHERE task_id = ?",
            (json.dumps(["attacker_skill"]), task_id),
        ) == 1
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
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
    assert result["executor"] == "reddog:signed_worker_dispatch"
    assert "routing_binding_mismatch" in result["detail"]
    assert runner.calls == []


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

    supervisor_module._renew_expired_independent_verifier_for_ready_stage(
        db=db,
        source=runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        env={"REDDOG_RESIDENT_QUEUE_NOW_ISO": "2026-07-16T00:00:00+00:00"},
        repo_root=tmp_path,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    assert effects == []
    assert db.get_autonomous_task_by_id(task_id)["status"] == "expired"
