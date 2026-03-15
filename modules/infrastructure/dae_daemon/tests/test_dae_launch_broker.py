"""Runtime launch broker tests."""

import threading
import time

from modules.infrastructure.dae_daemon.src.dae_daemon import (
    get_central_daemon,
    reset_central_daemon,
)
from modules.infrastructure.dae_daemon.src.dae_launch_broker import (
    DAELaunchSpec,
    get_dae_launch_broker,
    reset_dae_launch_broker,
)


class TestDAELaunchBroker:
    def setup_method(self):
        reset_dae_launch_broker()
        reset_central_daemon()

    def teardown_method(self):
        reset_dae_launch_broker()
        reset_central_daemon()

    def test_start_one_shot_dae(self, tmp_path):
        daemon = get_central_daemon(data_dir=tmp_path / "dae_daemon")
        daemon.start()
        broker = get_dae_launch_broker(daemon=daemon)

        calls = []

        def one_shot(result_text="ok"):
            calls.append(result_text)
            return {"status": "completed", "message": result_text}

        broker.register_launch_spec(
            DAELaunchSpec(
                dae_id="unit_test_dae",
                dae_name="Unit Test DAE",
                domain="tests",
                start_callable=one_shot,
            )
        )

        result = broker.start_dae(
            "unit_test_dae",
            actor_id="012",
            launch_kwargs={"result_text": "launched"},
        )
        assert result["status"] == "starting"

        deadline = time.time() + 2.0
        status = {}
        while time.time() < deadline:
            status = broker.get_status("unit_test_dae")
            if status["state"] == "stopped":
                break
            time.sleep(0.05)

        assert status["state"] == "stopped"
        assert status["running"] is False
        assert status["run_count"] == 1
        assert status["last_result_summary"] == "completed"
        assert calls == ["launched"]

    def test_launch_failure_sets_crashed_state(self, tmp_path):
        daemon = get_central_daemon(data_dir=tmp_path / "dae_daemon")
        daemon.start()
        broker = get_dae_launch_broker(daemon=daemon)

        def boom():
            raise RuntimeError("launch failure")

        broker.register_launch_spec(
            DAELaunchSpec(
                dae_id="crashy_dae",
                dae_name="Crashy DAE",
                domain="tests",
                start_callable=boom,
            )
        )

        broker.start_dae("crashy_dae", actor_id="012")

        deadline = time.time() + 2.0
        status = {}
        while time.time() < deadline:
            status = broker.get_status("crashy_dae")
            if status["state"] == "crashed":
                break
            time.sleep(0.05)

        assert status["state"] == "crashed"
        assert "launch failure" in status["last_error"]

    def test_list_and_stop_supported_dae(self, tmp_path):
        daemon = get_central_daemon(data_dir=tmp_path / "dae_daemon")
        daemon.start()
        broker = get_dae_launch_broker(daemon=daemon)

        stop_event = threading.Event()

        def long_running():
            while not stop_event.is_set():
                time.sleep(0.05)
            return {"status": "stopped"}

        def stop_callable():
            stop_event.set()

        broker.register_launch_spec(
            DAELaunchSpec(
                dae_id="loop_dae",
                dae_name="Loop DAE",
                domain="tests",
                start_callable=long_running,
                stop_callable=stop_callable,
            )
        )

        launchable = broker.list_launchable()
        assert "loop_dae" in launchable
        assert launchable["loop_dae"]["enabled"] is True

        broker.start_dae("loop_dae", actor_id="012")

        deadline = time.time() + 2.0
        while time.time() < deadline:
            if broker.get_status("loop_dae")["running"]:
                break
            time.sleep(0.05)

        second = broker.start_dae("loop_dae", actor_id="012")
        assert second["status"] == "already_running"

        stop_result = broker.stop_dae("loop_dae", actor_id="012")
        assert stop_result["status"] == "stopped"

