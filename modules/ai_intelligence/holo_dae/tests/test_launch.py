import threading
import time
import types
import builtins
from pathlib import Path

from modules.ai_intelligence.holo_dae.scripts import launch as holo_launch
from modules.infrastructure.wre_core.src import dae_preflight


def test_tier0_contract_docs_disclose_legacy_reindex_boundary():
    module_root = Path(__file__).resolve().parents[1]
    readme = (module_root / "README.md").read_text(encoding="utf-8")
    interface = (module_root / "INTERFACE.md").read_text(encoding="utf-8")

    assert "runtime_reindex_allowed=false" in readme
    assert "AutonomousHoloDAE" in readme
    assert "Retrieval RSI is therefore not operational" in readme
    assert "compatibility-only" in interface
    assert "performs no reindex" in interface


class _FakeLock:
    def __init__(self):
        self.released = False

    def check_duplicates(self):
        return []

    def acquire(self):
        return True

    def release(self):
        self.released = True

    def get_instance_summary(self):
        return {"total_instances": 1, "current_pid": 1234}


def test_stop_holodae_returns_not_running():
    holo_launch._holodae_instance = None
    holo_launch._holodae_status.clear()

    result = holo_launch.stop_holodae()

    assert result["status"] == "not_running"


def test_run_holodae_supports_stop_hook(monkeypatch):
    fake_lock = _FakeLock()
    instances = []

    class FakeHoloDAE:
        def __init__(self):
            self.active = False
            self.stop_calls = 0
            instances.append(self)

        def start_autonomous_monitoring(self):
            self.active = True

        def stop_autonomous_monitoring(self):
            self.stop_calls += 1
            self.active = False

    instance_module = types.ModuleType("instance_manager")
    instance_module.get_instance_lock = lambda name: fake_lock

    autonomous_module = types.ModuleType("autonomous_holodae")
    autonomous_module.AutonomousHoloDAE = FakeHoloDAE

    holo_launch._holodae_instance = None
    holo_launch._holodae_status.clear()
    monkeypatch.setattr(dae_preflight, "run_dae_preflight", lambda *_args, **_kwargs: True)
    original_sleep = time.sleep
    monkeypatch.setattr(holo_launch.time, "sleep", lambda _: original_sleep(0.01))
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "modules.infrastructure.instance_lock.src.instance_manager":
            return instance_module
        if name == "holo_index.qwen_advisor.autonomous_holodae":
            return autonomous_module
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    try:
        thread = threading.Thread(target=holo_launch.run_holodae, daemon=True)
        thread.start()

        deadline = time.time() + 2.0
        while time.time() < deadline and holo_launch._holodae_instance is None:
            time.sleep(0.01)

        assert holo_launch._holodae_instance is not None
        result = holo_launch.stop_holodae()
        assert result["status"] == "stopping"

        thread.join(timeout=2.0)
        assert not thread.is_alive()
        assert instances[0].stop_calls == 1
        assert fake_lock.released is True
        assert holo_launch._holodae_instance is None
    finally:
        holo_launch._holodae_instance = None
        holo_launch._holodae_status.clear()
