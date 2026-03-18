import builtins
import threading
import time
import types

from modules.infrastructure.git_push_dae.scripts import launch as git_launch


def test_stop_git_push_dae_returns_not_running():
    git_launch._git_push_instance = None
    git_launch._git_push_status.clear()

    result = git_launch.stop_git_push_dae()

    assert result["status"] == "not_running"


def test_launch_git_push_dae_supports_stop_hook(monkeypatch):
    instances = []

    class FakeGitPushDAE:
        def __init__(self, domain, check_interval):
            self.domain = domain
            self.check_interval = check_interval
            self.active = False
            instances.append(self)

        def start(self):
            self.active = True

        def stop(self):
            self.active = False

        def run_once(self):
            return types.SimpleNamespace(status="healthy")

    fake_module = types.ModuleType("git_push_dae")
    fake_module.GitPushDAE = FakeGitPushDAE

    git_launch._git_push_instance = None
    git_launch._git_push_status.clear()
    original_sleep = time.sleep
    monkeypatch.setattr(git_launch.time, "sleep", lambda _: original_sleep(0.01))
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "modules.infrastructure.git_push_dae.src.git_push_dae":
            return fake_module
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    thread = threading.Thread(
        target=git_launch.launch_git_push_dae.__wrapped__,
        kwargs={"run_once": False},
        daemon=True,
    )
    thread.start()

    deadline = time.time() + 2.0
    while time.time() < deadline and git_launch._git_push_instance is None:
        time.sleep(0.01)

    assert git_launch._git_push_instance is not None
    result = git_launch.stop_git_push_dae()
    assert result["status"] == "stopping"

    thread.join(timeout=2.0)
    assert not thread.is_alive()
    assert instances[0].active is False
    assert git_launch._git_push_instance is None
