"""FAM lifecycle flow tests for simulator integration."""

from __future__ import annotations

from copy import deepcopy

from modules.foundups.agent_market.src.fam_daemon import FAMDaemon
from modules.foundups.agent_market.src.models import TaskStatus
from modules.foundups.simulator.adapters.fam_bridge import FAMBridge
from modules.foundups.simulator.config import SimulatorConfig
from modules.foundups.simulator.mesa_model import FoundUpsModel


def test_bridge_supports_full_task_lifecycle(tmp_path) -> None:
    """Bridge should expose proof -> verify -> payout -> milestone wrappers."""
    daemon = FAMDaemon(data_dir=tmp_path, heartbeat_interval_sec=60.0, auto_start=False)
    bridge = FAMBridge(deterministic=True, fam_daemon=daemon)

    ok, msg, foundup_id = bridge.create_foundup(
        name="Lifecycle Test",
        owner_id="founder_0",
        token_symbol="LIFE",
    )
    assert ok, msg
    assert foundup_id is not None

    ok, msg, task_id = bridge.create_task(
        foundup_id=foundup_id,
        title="Implement API",
        description="Ship API endpoint",
        reward_amount=100,
        creator_id="founder_0",
    )
    assert ok, msg
    assert task_id is not None

    ok, msg = bridge.claim_task(task_id, "worker_0")
    assert ok, msg

    ok, msg, proof_id = bridge.submit_proof(task_id, submitter_id="worker_0")
    assert ok, msg
    assert proof_id is not None

    # A payload ID, including a legacy role-map entry, gains no host authority.
    bridge.get_market().actor_roles["imposter"] = "verifier"
    before = deepcopy(bridge.get_market().get_trace(task_id))
    ok, msg, verification_id = bridge.verify_task(task_id, verifier_id="imposter")
    assert not ok and verification_id is None
    assert bridge.get_market().get_trace(task_id) == before

    ok, msg, verification_id = bridge.verify_task(task_id)
    assert ok, msg
    assert verification_id is not None

    bridge.get_market().actor_roles["imposter"] = "treasury"
    before = deepcopy(bridge.get_market().get_trace(task_id))
    ok, msg, payout_id = bridge.trigger_payout(task_id, treasury_actor_id="imposter")
    assert not ok and payout_id is None
    assert bridge.get_market().get_trace(task_id) == before

    ok, msg, payout_id = bridge.trigger_payout(task_id)
    assert ok, msg
    assert payout_id is not None

    ok, msg, distribution_id = bridge.publish_milestone(task_id)
    assert ok, msg
    assert distribution_id is not None

    task = bridge.get_task(task_id)
    assert task is not None
    assert task.status == TaskStatus.PAID

    events = daemon.query_events(limit=200)
    event_types = [event.event_type for event in events]
    assert "proof_submitted" in event_types
    assert "verification_recorded" in event_types
    assert "payout_triggered" in event_types
    assert "milestone_published" in event_types


def test_model_advances_claimed_task_to_paid_and_published(tmp_path) -> None:
    """Model tick loop should advance claimed tasks through the full pipeline."""
    daemon = FAMDaemon(data_dir=tmp_path, heartbeat_interval_sec=60.0, auto_start=False)
    model = FoundUpsModel(
        config=SimulatorConfig(
            num_founder_agents=0,
            num_user_agents=0,
            seed=101,
            agent_action_probability=1.0,
            agent_cooldown_ticks=0,
        ),
        fam_daemon=daemon,
    )
    bridge = model._fam_bridge

    ok, msg, foundup_id = bridge.create_foundup(
        name="Model Pipeline",
        owner_id="founder_0",
        token_symbol="PIPE",
    )
    assert ok, msg
    assert foundup_id is not None

    ok, msg, task_id = bridge.create_task(
        foundup_id=foundup_id,
        title="Build Module",
        description="Implement module",
        reward_amount=75,
        creator_id="founder_0",
    )
    assert ok, msg
    assert task_id is not None

    ok, msg = bridge.claim_task(task_id, "worker_0")
    assert ok, msg

    # Snapshot pipeline means one stage per tick.
    for _ in range(4):
        model.step()

    task = bridge.get_task(task_id)
    assert task is not None
    assert task.status == TaskStatus.PAID
    assert bridge.get_market().get_distribution(task_id) is not None

    # Additional ticks should not duplicate milestone publication.
    for _ in range(6):
        model.step()

    milestone_events = daemon.query_events(event_type="milestone_published", limit=50)
    assert len(milestone_events) == 1
    fi_mined_events = daemon.query_events(event_type="fi_mined_for_work", limit=50)
    assert fi_mined_events

    state = model.state_store.get_state()
    assert state.foundups[foundup_id].tasks_completed >= 1

    worker = model.token_economics.human_accounts.get("worker_0")
    assert worker is not None
    assert worker.foundup_tokens.get(foundup_id, 0.0) > 0

