"""DAE observer read-surface tests."""

from modules.infrastructure.dae_daemon.src.dae_daemon import (
    get_central_daemon,
    reset_central_daemon,
)
from modules.infrastructure.dae_daemon.src.dae_launch_broker import (
    get_dae_launch_broker,
    reset_dae_launch_broker,
)
from modules.infrastructure.dae_daemon.src.dae_observer import (
    get_dae_observer,
    reset_dae_observer,
)
from modules.infrastructure.dae_daemon.src.schemas import DAERegistration, DAEEventType


class TestDAEObserver:
    def setup_method(self):
        reset_dae_observer()
        reset_dae_launch_broker()
        reset_central_daemon()

    def teardown_method(self):
        reset_dae_observer()
        reset_dae_launch_broker()
        reset_central_daemon()

    def test_tail_events_returns_recent_activity(self, tmp_path):
        daemon = get_central_daemon(data_dir=tmp_path / "dae_daemon")
        daemon.start()
        daemon.register_dae(
            DAERegistration(
                dae_id="openclaw",
                dae_name="OpenClaw DAE",
                domain="communication",
            )
        )
        daemon.registry.report_event(
            "openclaw",
            DAEEventType.ACTION_PERFORMED,
            {"action_type": "pqn_simulation", "target": "pqn_theory_archive", "result": "started"},
        )

        observer = get_dae_observer(daemon=daemon)
        events = observer.tail_events(dae_id="openclaw", limit=5)

        assert events
        assert events[-1]["event_type"] == "action_performed"
        assert events[-1]["payload"]["action_type"] == "pqn_simulation"

    def test_live_status_combines_registry_and_recent_events(self, tmp_path):
        daemon = get_central_daemon(data_dir=tmp_path / "dae_daemon")
        daemon.start()
        daemon.register_dae(
            DAERegistration(
                dae_id="openclaw",
                dae_name="OpenClaw DAE",
                domain="communication",
            )
        )
        daemon.registry.report_heartbeat("openclaw", {"healthy": True})
        daemon.registry.report_event(
            "openclaw",
            DAEEventType.MESSAGE_IN,
            {"source": "012", "summary": "tail openclaw"},
        )

        observer = get_dae_observer(daemon=daemon)
        snapshot = observer.get_live_status("openclaw", limit=5)

        assert snapshot["registered"] is True
        assert snapshot["dae_id"] == "openclaw"
        assert snapshot["state"] in {"registered", "running"}
        assert snapshot["recent_events"]
        assert snapshot["last_event"]["event_type"] == "message_in"
