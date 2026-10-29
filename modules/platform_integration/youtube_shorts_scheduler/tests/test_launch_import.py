"""Offline import boundary for launcher users that do not run a browser."""

import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap


def test_launcher_import_does_not_load_browser_dependencies(tmp_path: Path) -> None:
    """Use real package parents; never call a launcher or load a browser backend."""
    repo_root = Path(__file__).resolve().parents[4]
    registry_path = tmp_path / "youtube_channels.json"
    registry_path.write_text(
        json.dumps({"version": 1, "channels": [{"key": "import_fixture"}]}),
        encoding="utf-8",
    )
    child_code = textwrap.dedent(
        """
        import importlib
        import importlib.abc
        from pathlib import Path
        import sys

        sys.path.insert(0, sys.argv[1])
        blocked_prefixes = (
            "selenium",
            "playwright",
            "modules.infrastructure.foundups_selenium",
            "modules.platform_integration.youtube_shorts_scheduler.src.scheduler",
            "modules.platform_integration.youtube_shorts_scheduler.src.dom_automation",
        )

        def is_browser_dependency(name):
            return any(name == prefix or name.startswith(prefix + ".")
                       for prefix in blocked_prefixes)

        class DenyBrowserDependencies(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if is_browser_dependency(fullname):
                    raise AssertionError("launcher loaded browser dependency: " + fullname)
                return None

        def deny_external_actions(event, args):
            if event.startswith("socket.") or event in ("subprocess.Popen", "os.system"):
                raise AssertionError("launcher attempted external action: " + event)

        sys.meta_path.insert(0, DenyBrowserDependencies())
        sys.addaudithook(deny_external_actions)

        # Keep the real registry loader, with all fixture data/writes in tmp_path.
        from modules.infrastructure.shared_utilities import youtube_channel_registry
        youtube_channel_registry._REGISTRY_PATH = Path(sys.argv[2])

        launcher = importlib.import_module(
            "modules.platform_integration.youtube_shorts_scheduler.scripts.launch"
        )
        for name in ("run_shorts_scheduler", "show_shorts_scheduler_menu",
                     "run_multi_channel_scheduler"):
            assert callable(getattr(launcher, name)), name
        assert "main" not in sys.modules
        assert not any(is_browser_dependency(name) for name in sys.modules)
        print("launcher import passed without browser dependencies")
        """
    )
    # Do not pass station credentials or operator configuration to the child.
    child_env = {
        key: value
        for key, value in os.environ.items()
        if key.lower() in ("systemroot", "windir")
    }
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", child_code, str(repo_root), str(registry_path)],
        cwd=tmp_path,
        env=child_env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "launcher import passed without browser dependencies"
