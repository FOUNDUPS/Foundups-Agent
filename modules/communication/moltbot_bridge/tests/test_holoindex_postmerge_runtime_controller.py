import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from modules.communication.moltbot_bridge.src import (
    holoindex_postmerge_runtime_controller as controller,
)
from modules.communication.moltbot_bridge.src.reddog_holoindex_incident_repair_contract import (
    HoloIndexIncidentRepairReceipt,
    seal_receipt,
)


HEAD = "a" * 40
TASK_ID = "holoindex_postmerge_refresh:" + HEAD
GENERATION = "sha256:" + ("b" * 64)
FRESHNESS = "sha256:" + ("c" * 64)

def _git_runner(*, dirty=False):
    def run(argv, _cwd):
        args = tuple(argv[1:])
        if args[0] == "status":
            return SimpleNamespace(returncode=0, stdout=" M changed.py\n" if dirty else "")
        if args == ("rev-parse", "HEAD") or args == (
            "rev-parse", "refs/remotes/origin/main"
        ):
            return SimpleNamespace(returncode=0, stdout=HEAD + "\n")
        raise AssertionError(args)

    return run


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class FakeBroker:
    def __init__(self, *, already_running=False, stop_works=True):
        self.state = {
            runtime_id: {
                "registered": True,
                "running": already_running,
                "thread_alive": already_running,
                "state": "running" if already_running else "stopped",
                "last_error": "",
            }
            for runtime_id in ("openclaw", "openclaw_supervisor")
        }
        self.started = []
        self.stopped = []
        self.start_launch_kwargs = []
        self.stop_works = stop_works

    def get_runtime_status(self, runtime_id):
        return dict(self.state[runtime_id])

    def start_dae(self, runtime_id, *, actor_id, launch_kwargs=None):
        assert actor_id == "0102"
        self.started.append(runtime_id)
        self.start_launch_kwargs.append(launch_kwargs)
        self.state[runtime_id].update(
            running=True, thread_alive=True, state="running"
        )
        return {"success": True, "status": "starting"}

    def stop_dae(self, runtime_id, *, actor_id):
        assert actor_id == "0102"
        self.stopped.append(runtime_id)
        self.state[runtime_id]["running"] = False
        if self.stop_works:
            self.state[runtime_id]["thread_alive"] = False
        return {"success": True, "status": "stopped"}


def _repair_receipt():
    return seal_receipt(
        HoloIndexIncidentRepairReceipt(
            True,
            "QUEUED",
            incident_kind="HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH",
            incident_id="sha256:" + ("d" * 64),
            task_id=TASK_ID,
            request_event_id="holoindex_postmerge_requested:" + HEAD,
            target_repo_head_sha=HEAD,
            workspace_repo_head_sha=HEAD,
            observed_authority_head_sha="e" * 40,
            authority_root_digest="sha256:" + ("f" * 64),
            maintenance_enqueued=True,
        )
    )


def _selection(_root):
    return SimpleNamespace(accepted=True)


def _run(
    monkeypatch, tmp_path, *, broker=None, clock=None, bootstrap=None,
    completion_validator=None, owner_result=None, git_runner=None,
):
    broker = broker or FakeBroker()
    clock = clock or FakeClock()
    monkeypatch.setattr(controller, "classify_verified_owner_result", lambda *_a, **_k: "INVALID")
    monkeypatch.setattr(
        controller,
        "query_and_classify_owner_result",
        lambda **_kwargs: (
            controller.CURRENT,
            owner_result or {
                "freshness_generation_id": GENERATION,
                "freshness_receipt_digest": FRESHNESS,
            },
        ),
    )
    monkeypatch.setattr(
        controller,
        "validate_supervisor_holoindex_postmerge_completion",
        completion_validator
        or (
            lambda _db, _task_id: {
                "generation_id": GENERATION,
                "freshness_receipt_digest": FRESHNESS,
            }
        ),
    )
    return controller._run_holoindex_postmerge_runtime_for_test(
        repo_root=tmp_path,
        query="runtime closure",
        timeout_seconds=10.0,
        poll_interval_seconds=0.1,
        git_runner=git_runner or _git_runner(),
        query_runner=lambda *_a, **_k: {"ok": False},
        select_authority=_selection,
        coordinator=lambda **_kwargs: _repair_receipt(),
        bootstrap=bootstrap or (lambda: None),
        broker_provider=lambda: broker,
        database_provider=lambda: object(),
        clock=clock,
        sleeper=clock.sleep,
    )


def test_runtime_controller_rejects_dirty_workspace_before_query(tmp_path):
    query = MagicMock()

    result = controller._run_holoindex_postmerge_runtime_for_test(
        repo_root=tmp_path,
        query="runtime closure",
        timeout_seconds=10.0,
        poll_interval_seconds=0.1,
        git_runner=_git_runner(dirty=True),
        query_runner=query,
        select_authority=_selection,
        coordinator=MagicMock(),
        bootstrap=MagicMock(),
        broker_provider=MagicMock(),
        database_provider=MagicMock(),
        clock=FakeClock(),
        sleeper=lambda _seconds: None,
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("workspace_not_clean",)
    query.assert_not_called()


def test_runtime_controller_rejects_head_origin_main_mismatch(tmp_path):
    base = _git_runner()

    def mismatched(argv, cwd):
        if tuple(argv[1:]) == ("rev-parse", "refs/remotes/origin/main"):
            return SimpleNamespace(returncode=0, stdout=("8" * 40) + "\n")
        return base(argv, cwd)

    result = controller._run_holoindex_postmerge_runtime_for_test(
        repo_root=tmp_path, query="runtime closure", timeout_seconds=10.0,
        poll_interval_seconds=0.1, git_runner=mismatched,
        query_runner=MagicMock(), select_authority=_selection,
        coordinator=MagicMock(), bootstrap=MagicMock(),
        broker_provider=MagicMock(), database_provider=MagicMock(),
        clock=FakeClock(), sleeper=lambda _seconds: None,
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("workspace_not_exact_origin_main",)


def test_runtime_controller_current_owner_starts_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        controller, "classify_verified_owner_result", lambda *_a, **_k: controller.CURRENT
    )
    bootstrap = MagicMock()

    result = controller._run_holoindex_postmerge_runtime_for_test(
        repo_root=tmp_path,
        query="runtime closure",
        timeout_seconds=10.0,
        poll_interval_seconds=0.1,
        git_runner=_git_runner(),
        query_runner=lambda *_a, **_k: {
            "freshness_generation_id": GENERATION,
            "freshness_receipt_digest": FRESHNESS,
        },
        select_authority=_selection,
        coordinator=MagicMock(),
        bootstrap=bootstrap,
        broker_provider=MagicMock(),
        database_provider=MagicMock(),
        clock=FakeClock(),
        sleeper=lambda _seconds: None,
    )

    assert result.accepted is True
    assert result.status == "OWNER_READY"
    assert result.started_runtime_ids == ()
    bootstrap.assert_not_called()


def test_runtime_controller_owns_exact_lifecycle_with_holo_only_supervisor(
    monkeypatch, tmp_path,
):
    broker = FakeBroker()
    result = _run(monkeypatch, tmp_path, broker=broker)

    assert result.accepted is True
    assert result.status == "COMPLETED"
    assert result.started_runtime_ids == ("openclaw", "openclaw_supervisor")
    assert result.stopped_runtime_ids == ("openclaw_supervisor", "openclaw")
    assert broker.started == ["openclaw", "openclaw_supervisor"]
    assert broker.stopped == ["openclaw_supervisor", "openclaw"]
    assert broker.start_launch_kwargs == [
        None,
        {"runtime_mode": controller.HOLOINDEX_POSTMERGE_ONLY_MODE},
    ]


def test_runtime_controller_preserves_preexisting_broker_runtimes(monkeypatch, tmp_path):
    broker = FakeBroker(already_running=True)

    result = _run(monkeypatch, tmp_path, broker=broker)

    assert result.accepted is True
    assert result.started_runtime_ids == ()
    assert result.stopped_runtime_ids == ()
    assert broker.started == []
    assert broker.stopped == []


def test_runtime_controller_fails_when_owned_thread_does_not_stop(monkeypatch, tmp_path):
    broker = FakeBroker(stop_works=False)

    result = _run(monkeypatch, tmp_path, broker=broker)

    assert result.accepted is False
    assert result.status == "REJECTED"
    assert result.rejection_reasons == (
        "openclaw_supervisor_stop_timeout",
        "openclaw_stop_timeout",
    )


def test_runtime_controller_does_not_own_already_running_race(monkeypatch, tmp_path):
    class RaceBroker(FakeBroker):
        def start_dae(self, runtime_id, *, actor_id, launch_kwargs=None):
            if runtime_id == "openclaw":
                self.state[runtime_id].update(
                    running=True, thread_alive=True, state="running"
                )
                return {"success": True, "status": "already_running"}
            return super().start_dae(
                runtime_id, actor_id=actor_id, launch_kwargs=launch_kwargs
            )

    broker = RaceBroker()
    result = _run(monkeypatch, tmp_path, broker=broker)

    assert result.accepted is False
    assert result.rejection_reasons == ("runtime_ownership_race",)
    assert result.started_runtime_ids == ("openclaw_supervisor",)
    assert broker.stopped == ["openclaw_supervisor"]


def test_runtime_controller_rejects_start_then_crash(monkeypatch, tmp_path):
    class CrashBroker(FakeBroker):
        def __init__(self):
            super().__init__()
            self.ready_reads = 0

        def get_runtime_status(self, runtime_id):
            status = super().get_runtime_status(runtime_id)
            if runtime_id == "openclaw" and runtime_id in self.started:
                self.ready_reads += 1
                if self.ready_reads >= 2:
                    status.update(
                        running=False, thread_alive=False, state="crashed",
                        last_error="launch_failed",
                    )
            return status

    result = _run(monkeypatch, tmp_path, broker=CrashBroker())

    assert result.accepted is False
    assert result.rejection_reasons == ("openclaw_start_timeout",)
    assert result.stopped_runtime_ids == ("openclaw",)


def test_runtime_controller_interrupt_still_cleans_owned_threads(monkeypatch, tmp_path):
    broker = FakeBroker()

    def interrupted(_database, _task_id):
        raise KeyboardInterrupt("must not leak")

    result = _run(
        monkeypatch, tmp_path, broker=broker, completion_validator=interrupted
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("runtime_exception",)
    assert result.stopped_runtime_ids == ("openclaw_supervisor", "openclaw")


def test_runtime_controller_rejects_owner_completion_mismatch(monkeypatch, tmp_path):
    result = _run(
        monkeypatch,
        tmp_path,
        owner_result={
            "freshness_generation_id": "sha256:" + ("9" * 64),
            "freshness_receipt_digest": FRESHNESS,
        },
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("owner_completion_binding_mismatch",)


def test_runtime_controller_rejects_workspace_drift_and_cleans(monkeypatch, tmp_path):
    clean_runner = _git_runner()
    status_reads = 0

    def drift_runner(argv, cwd):
        nonlocal status_reads
        if tuple(argv[1:])[0] == "status":
            status_reads += 1
            if status_reads >= 2:
                return SimpleNamespace(returncode=0, stdout=" M drift.py\n")
        return clean_runner(argv, cwd)

    broker = FakeBroker()
    result = _run(
        monkeypatch, tmp_path, broker=broker, git_runner=drift_runner
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("workspace_changed_during_transaction",)
    assert result.stopped_runtime_ids == ("openclaw_supervisor", "openclaw")


def test_runtime_controller_accepts_exact_sealed_owner_ready_receipt(
    monkeypatch, tmp_path,
):
    receipt = seal_receipt(
        HoloIndexIncidentRepairReceipt(
            True,
            "OWNER_READY",
            incident_kind="OWNER_CURRENT",
            incident_id="sha256:" + ("d" * 64),
            target_repo_head_sha=HEAD,
            workspace_repo_head_sha=HEAD,
            observed_authority_head_sha=HEAD,
            authority_root_digest="sha256:" + ("f" * 64),
            generation_id=GENERATION,
            freshness_receipt_digest=FRESHNESS,
            owner_requery_performed=True,
        )
    )
    monkeypatch.setattr(controller, "classify_verified_owner_result", lambda *_a, **_k: "INVALID")
    bootstrap = MagicMock()

    result = controller._run_holoindex_postmerge_runtime_for_test(
        repo_root=tmp_path, query="runtime closure", timeout_seconds=10.0,
        poll_interval_seconds=0.1, git_runner=_git_runner(),
        query_runner=lambda *_a, **_k: {"ok": False},
        select_authority=_selection, coordinator=lambda **_kwargs: receipt,
        bootstrap=bootstrap, broker_provider=MagicMock(),
        database_provider=MagicMock(), clock=FakeClock(),
        sleeper=lambda _seconds: None,
    )

    assert result.accepted is True
    assert result.status == "OWNER_READY"
    assert result.generation_id == GENERATION
    bootstrap.assert_not_called()


def test_runtime_controller_rejects_wrong_sha_owner_ready_receipt(
    monkeypatch, tmp_path,
):
    other = "9" * 40
    receipt = seal_receipt(
        HoloIndexIncidentRepairReceipt(
            True,
            "OWNER_READY",
            incident_kind="OWNER_CURRENT",
            incident_id="sha256:" + ("d" * 64),
            target_repo_head_sha=other,
            workspace_repo_head_sha=other,
            observed_authority_head_sha=other,
            authority_root_digest="sha256:" + ("f" * 64),
            generation_id=GENERATION,
            freshness_receipt_digest=FRESHNESS,
            owner_requery_performed=True,
        )
    )
    monkeypatch.setattr(controller, "classify_verified_owner_result", lambda *_a, **_k: "INVALID")
    bootstrap = MagicMock()

    result = controller._run_holoindex_postmerge_runtime_for_test(
        repo_root=tmp_path, query="runtime closure", timeout_seconds=10.0,
        poll_interval_seconds=0.1, git_runner=_git_runner(),
        query_runner=lambda *_a, **_k: {"ok": False},
        select_authority=_selection,
        coordinator=lambda **_kwargs: receipt,
        bootstrap=bootstrap, broker_provider=MagicMock(),
        database_provider=MagicMock(), clock=FakeClock(),
        sleeper=lambda _seconds: None,
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("owner_ready_receipt_not_exact_head",)
    bootstrap.assert_not_called()


def test_runtime_controller_rejects_suffix_only_task_id(monkeypatch, tmp_path):
    forged = seal_receipt(
        HoloIndexIncidentRepairReceipt(
            True,
            "QUEUED",
            incident_kind="HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH",
            incident_id="sha256:" + ("d" * 64),
            task_id="attacker:" + HEAD,
            request_event_id="holoindex_postmerge_requested:" + HEAD,
            target_repo_head_sha=HEAD,
            workspace_repo_head_sha=HEAD,
            observed_authority_head_sha="e" * 40,
            authority_root_digest="sha256:" + ("f" * 64),
            maintenance_enqueued=True,
        )
    )
    monkeypatch.setattr(controller, "classify_verified_owner_result", lambda *_a, **_k: "INVALID")

    result = controller._run_holoindex_postmerge_runtime_for_test(
        repo_root=tmp_path, query="runtime closure", timeout_seconds=10.0,
        poll_interval_seconds=0.1, git_runner=_git_runner(),
        query_runner=lambda *_a, **_k: {"ok": False},
        select_authority=_selection, coordinator=lambda **_kwargs: forged,
        bootstrap=MagicMock(), broker_provider=MagicMock(),
        database_provider=MagicMock(), clock=FakeClock(),
        sleeper=lambda _seconds: None,
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("repair_task_not_exact_head",)


def test_runtime_controller_preexisting_runtime_does_not_receive_env_override(
    monkeypatch, tmp_path,
):
    observed = []
    monkeypatch.setenv("OPENCLAW_AUTO_TASKS_ENABLED", "preserved")

    def completion(_database, _task_id):
        observed.append(os.environ["OPENCLAW_AUTO_TASKS_ENABLED"])
        return {
            "generation_id": GENERATION,
            "freshness_receipt_digest": FRESHNESS,
        }

    result = _run(
        monkeypatch, tmp_path, broker=FakeBroker(already_running=True),
        completion_validator=completion,
    )

    assert result.accepted is True
    assert observed == ["preserved"]


def test_runtime_controller_rejects_when_both_runtime_starts_lose_race(
    monkeypatch, tmp_path,
):
    class BothRaceBroker(FakeBroker):
        def start_dae(self, runtime_id, *, actor_id, launch_kwargs=None):
            assert actor_id == "0102"
            self.state[runtime_id].update(
                running=True, thread_alive=True, state="running"
            )
            return {"success": True, "status": "already_running"}

    completion = MagicMock()
    result = _run(
        monkeypatch, tmp_path, broker=BothRaceBroker(),
        completion_validator=completion,
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("runtime_ownership_race",)
    assert result.started_runtime_ids == ()
    completion.assert_not_called()


def test_current_owner_revalidates_git_before_accepting(monkeypatch, tmp_path):
    monkeypatch.setattr(
        controller, "classify_verified_owner_result", lambda *_a, **_k: controller.CURRENT
    )
    clean = _git_runner()
    status_reads = 0

    def drift(argv, cwd):
        nonlocal status_reads
        if tuple(argv[1:])[0] == "status":
            status_reads += 1
            if status_reads == 2:
                return SimpleNamespace(returncode=0, stdout=" M drift.py\n")
        return clean(argv, cwd)

    result = controller._run_holoindex_postmerge_runtime_for_test(
        repo_root=tmp_path, query="runtime closure", timeout_seconds=10.0,
        poll_interval_seconds=0.1, git_runner=drift,
        query_runner=lambda *_a, **_k: {
            "freshness_generation_id": GENERATION,
            "freshness_receipt_digest": FRESHNESS,
        },
        select_authority=_selection, coordinator=MagicMock(),
        bootstrap=MagicMock(), broker_provider=MagicMock(),
        database_provider=MagicMock(), clock=FakeClock(),
        sleeper=lambda _seconds: None,
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("workspace_changed_before_return",)
    assert status_reads == 2


def test_coordinator_owner_ready_revalidates_git_before_accepting(
    monkeypatch, tmp_path,
):
    receipt = seal_receipt(
        HoloIndexIncidentRepairReceipt(
            True, "OWNER_READY", incident_kind="OWNER_CURRENT",
            incident_id="sha256:" + ("d" * 64), target_repo_head_sha=HEAD,
            workspace_repo_head_sha=HEAD, observed_authority_head_sha=HEAD,
            authority_root_digest="sha256:" + ("f" * 64),
            generation_id=GENERATION, freshness_receipt_digest=FRESHNESS,
            owner_requery_performed=True,
        )
    )
    monkeypatch.setattr(
        controller, "classify_verified_owner_result", lambda *_a, **_k: "INVALID"
    )
    clean = _git_runner()
    status_reads = 0

    def drift(argv, cwd):
        nonlocal status_reads
        if tuple(argv[1:])[0] == "status":
            status_reads += 1
            if status_reads == 2:
                return SimpleNamespace(returncode=0, stdout=" M drift.py\n")
        return clean(argv, cwd)

    result = controller._run_holoindex_postmerge_runtime_for_test(
        repo_root=tmp_path, query="runtime closure", timeout_seconds=10.0,
        poll_interval_seconds=0.1, git_runner=drift,
        query_runner=lambda *_a, **_k: {"ok": False},
        select_authority=_selection, coordinator=lambda **_kwargs: receipt,
        bootstrap=MagicMock(), broker_provider=MagicMock(),
        database_provider=MagicMock(), clock=FakeClock(),
        sleeper=lambda _seconds: None,
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("workspace_changed_before_return",)
    assert status_reads == 2


def test_final_git_interrupt_rejects_after_owned_cleanup(monkeypatch, tmp_path):
    clean = _git_runner()
    status_reads = 0

    def interrupted(argv, cwd):
        nonlocal status_reads
        if tuple(argv[1:])[0] == "status":
            status_reads += 1
            if status_reads == 3:
                raise KeyboardInterrupt("must not escape")
        return clean(argv, cwd)

    broker = FakeBroker()
    result = _run(monkeypatch, tmp_path, broker=broker, git_runner=interrupted)

    assert result.accepted is False
    assert result.rejection_reasons == ("workspace_changed_before_return",)
    assert result.stopped_runtime_ids == ("openclaw_supervisor", "openclaw")


def test_runtime_controller_lease_failure_is_fixed_and_effect_free(
    monkeypatch, tmp_path,
):
    query = MagicMock()

    def unavailable():
        raise RuntimeError("private lease failure")

    result = controller._run_holoindex_postmerge_runtime_for_test(
        repo_root=tmp_path, query="runtime closure", timeout_seconds=10.0,
        poll_interval_seconds=0.1, git_runner=_git_runner(), query_runner=query,
        select_authority=_selection, coordinator=MagicMock(),
        bootstrap=MagicMock(), broker_provider=MagicMock(),
        database_provider=MagicMock(), clock=FakeClock(),
        sleeper=lambda _seconds: None, lease_factory=unavailable,
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("runtime_controller_unavailable",)
    query.assert_not_called()


def test_production_runtime_lease_serializes_controller_processes(
    monkeypatch, tmp_path,
):
    from holo_index.maintenance_lock import MaintenanceLeaseBusy

    monkeypatch.setenv("HOLOINDEX_SSD_PATH", str(tmp_path / "holo-store"))
    with controller._production_runtime_lease():
        with pytest.raises(MaintenanceLeaseBusy):
            with controller._production_runtime_lease():
                raise AssertionError("second controller lease must not enter")


def test_runtime_controller_cli_rejection_is_nonzero_and_secret_free(
    monkeypatch, capsys,
):
    script_path = (
        Path(__file__).resolve().parents[4]
        / "scripts"
        / "reddog_holoindex_postmerge_runtime_once.py"
    )
    spec = importlib.util.spec_from_file_location("holo_postmerge_cli_test", script_path)
    assert spec and spec.loader
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    monkeypatch.setattr(cli, "_read_payload", lambda: {"query": "runtime closure"})
    monkeypatch.setattr(
        cli,
        "run_holoindex_postmerge_runtime_once",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("secret-value")),
    )

    assert cli.main() == 1
    output = capsys.readouterr().out
    assert "secret-value" not in output
    assert '"accepted": false' in output
    assert "invalid_or_interrupted_request" in output
