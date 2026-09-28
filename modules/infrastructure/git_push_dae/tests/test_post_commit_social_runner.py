import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

# Reuse the source-file loading pattern in the social scheduler evidence tests.
# Importing the GitPushDAE package would also import its daemon implementation.
_RUNNER_PATH = Path(__file__).resolve().parents[1] / "scripts/post_commit_social_runner.py"
_RUNNER_SPEC = importlib.util.spec_from_file_location("post_commit_runner_evidence", _RUNNER_PATH)
runner = importlib.util.module_from_spec(_RUNNER_SPEC)
_RUNNER_SPEC.loader.exec_module(runner)


def test_build_git_push_event(monkeypatch, tmp_path):
    responses = {
        ("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"): "a.py\nb.py\n",
        ("rev-parse", "--short", "HEAD"): "abc1234",
        ("log", "-1", "--pretty=%s"): "Fix hook latency",
        ("log", "-1", "--pretty=%B"): "Fix hook latency\n\nMore detail",
        ("branch", "--show-current"): "fix/test-branch",
    }

    def fake_run_git(repo_root: Path, *args: str) -> str:
        return responses[args]

    monkeypatch.setattr(runner, "_run_git", fake_run_git)

    event = runner.build_git_push_event(tmp_path / "Foundups-Agent")

    assert event["event"] == "git_push"
    assert event["payload"]["repository"] == "Foundups-Agent"
    assert event["payload"]["branch"] == "fix/test-branch"
    assert event["payload"]["commits"][0]["hash"] == "abc1234"
    assert event["payload"]["commits"][0]["files_changed"] == 2
    assert event["dedupe_key"] == "git_push:fix/test-branch:abc1234"


def test_append_jsonl_record(tmp_path):
    output = tmp_path / "memory" / "events.jsonl"
    runner.append_jsonl_record(output, {"event": "git_push", "payload": {"ok": True}})

    text = output.read_text(encoding="utf-8")
    assert '"event": "git_push"' in text
    assert '"ok": true' in text


def test_dispatch_git_push_event(monkeypatch):
    class FakeRouter:
        async def handle_event(self, event_type, payload):
            return {"event_type": event_type, "count": len(payload["commits"])}

    monkeypatch.setattr(runner, "_get_social_media_router_class", lambda: FakeRouter)

    result = asyncio.run(
        runner.dispatch_git_push_event(
            {
                "payload": {
                    "commits": [{"hash": "abc1234"}],
                    "repository": "Foundups-Agent",
                    "branch": "main",
                }
            }
        )
    )

    assert result == {"event_type": "git_push", "count": 1}


# This is a restricted Python entrypoint, not the ambient Windows shell hook.
# Missing-root evidence is a natural import error after an absence precondition.
# Positive cases supply an inert namespace before executing the unchanged getter.
_ENTRYPOINT = r'''
import builtins, hashlib, importlib.util, json, runpy, sys, types
from pathlib import Path
source, profile, repository = sys.argv[1:4]
arguments = sys.argv[4:]
source_sha256 = hashlib.sha256(Path(source).read_bytes()).hexdigest()
assert "modules" not in sys.modules
assert importlib.util.find_spec("modules") is None, "application package unexpectedly available"
calls, imports = [], []
if profile != "missing":
    names = ["modules", "modules.platform_integration",
             "modules.platform_integration.social_media_orchestrator",
             "modules.platform_integration.social_media_orchestrator.src",
             "modules.platform_integration.social_media_orchestrator.src.multi_account_manager"]
    for name in names:
        module = types.ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module
    class InertRouter:
        def __init__(self):
            calls.append({"kind": "construct"})
        async def handle_event(self, event_type, payload):
            calls.append({"kind": "dispatch", "event_type": event_type, "payload": payload})
            if profile == "failure":
                raise RuntimeError("fixture dispatch failure")
            return {"fixture": True, "delivered": False}
    module.SocialMediaEventRouter = InertRouter
original_import = builtins.__import__
def record_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name == "modules" or name.startswith("modules."):
        imports.append(name)
    return original_import(name, globals, locals, fromlist, level)
builtins.__import__ = record_import
sys.argv = [source, "--repo-root", repository, *arguments]
try:
    runpy.run_path(source, run_name="__main__")
finally:
    builtins.__import__ = original_import
    print("ENTRYPOINT_CONTEXT " + json.dumps({"profile": profile, "sys_path": sys.path,
          "safe_path": sys.flags.safe_path, "isolated": sys.flags.isolated,
          "argv": sys.argv, "source_sha256": source_sha256,
          "imports": imports, "calls": calls}, sort_keys=True))
'''


def _fixture_environment(root):
    """No inherited account/provider/Git configuration reaches a child."""
    home, hooks = root / "home", root / "empty-hooks"
    home.mkdir()
    hooks.mkdir()
    environment = {"PATH": os.environ["PATH"], "HOME": str(home), "XDG_CONFIG_HOME": str(home),
                   "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                   "GIT_TEMPLATE_DIR": str(hooks), "GIT_CONFIG_COUNT": "3",
                   "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": str(hooks),
                   "GIT_CONFIG_KEY_1": "commit.gpgsign", "GIT_CONFIG_VALUE_1": "false",
                   "GIT_CONFIG_KEY_2": "credential.helper", "GIT_CONFIG_VALUE_2": "",
                   "GIT_TERMINAL_PROMPT": "0", "GIT_AUTHOR_NAME": "Fixture",
                   "GIT_COMMITTER_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                   "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
                   "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+0000",
                   "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+0000",
                   "TMPDIR": str(root), "TMP": str(root), "TEMP": str(root), "TZ": "UTC"}
    if "SYSTEMROOT" in os.environ:
        environment["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    return environment


def _fixture_git(repository, environment, *arguments):
    return subprocess.run(["git", *arguments], cwd=repository, env=environment,
                          capture_output=True, text=True, check=True, timeout=10).stdout.strip()


def _fixture_repository(root, environment):
    repository = root / "fixture-repo"
    repository.mkdir()
    _fixture_git(repository, environment, "init", "--quiet", "--initial-branch=fixture")
    source = repository / "fixture.txt"
    for message, value in (("Fixture seed", "seed\n"), ("Fixture update", "update\n")):
        source.write_text(value, encoding="utf-8")
        _fixture_git(repository, environment, "add", "--", "fixture.txt")
        _fixture_git(repository, environment, "commit", "--quiet", "--no-gpg-sign", "-m", message)
    commit = _fixture_git(repository, environment, "rev-parse", "--short", "HEAD")
    payload = {"repository": "fixture-repo", "branch": "fixture", "commits": [
        {"hash": commit, "subject": "Fixture update", "message": "Fixture update",
         "files_changed": 1, "files": ["fixture.txt"]}]}
    return repository, payload


def _jsonl_rows(path):
    if not path.exists():
        return []
    raw = path.read_bytes()
    assert raw.endswith(b"\n")
    return [json.loads(line) for line in raw.decode("utf-8").splitlines()]


class TestEntrypointEvidence(unittest.TestCase):
    """Six fixed source-entry controls; no real router or social delivery."""

    def _exercise(self, profile, arguments, exit_code, event_count, result_count,
                  import_count, dispatch_count, error=None):
        with tempfile.TemporaryDirectory(prefix="git-hook-evidence-") as temporary:
            root = Path(temporary).resolve()
            environment = _fixture_environment(root)
            repository, payload = _fixture_repository(root, environment)
            before = _fixture_git(repository, environment, "rev-parse", "HEAD")
            completed = subprocess.run(
                [sys.executable, "-I", "-B", "-c", _ENTRYPOINT, str(_RUNNER_PATH),
                 profile, str(repository), *arguments], cwd=repository, env=environment,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(completed.returncode, exit_code, completed.stderr + completed.stdout)
            lines = [line for line in completed.stdout.splitlines() if line.startswith("ENTRYPOINT_CONTEXT ")]
            self.assertEqual(len(lines), 1, completed.stdout)
            context = json.loads(lines[0].removeprefix("ENTRYPOINT_CONTEXT "))
            self.assertTrue(context["safe_path"])
            self.assertEqual(context["isolated"], 1)
            self.assertNotIn(str(repository), context["sys_path"])
            self.assertNotIn(str(_RUNNER_PATH.parents[4]), context["sys_path"])
            self.assertEqual(context["argv"], [str(_RUNNER_PATH), "--repo-root", str(repository), *arguments])
            self.assertEqual(context["source_sha256"], hashlib.sha256(_RUNNER_PATH.read_bytes()).hexdigest())
            events = _jsonl_rows(repository / "memory/git_push_events.jsonl")
            results = _jsonl_rows(repository / "memory/git_push_dispatch_results.jsonl")
            self.assertEqual(len(events), event_count)
            self.assertEqual(len(results), result_count)
            self._check_payload(events, results, payload, error)
            self._check_handoff(context, payload, import_count, dispatch_count)
            if exit_code == 2:
                self.assertIn("unrecognized arguments: --dispatch-direct", completed.stderr)
                self.assertFalse((repository / "memory").exists())
            self.assertEqual(_fixture_git(repository, environment, "rev-parse", "HEAD"), before)
            self.assertEqual(_fixture_git(repository, environment, "diff", "--name-only", "HEAD"), "")
            expected_files = (["memory/git_push_events.jsonl"] if event_count else [])
            if result_count:
                expected_files.append("memory/git_push_dispatch_results.jsonl")
            self.assertEqual(_fixture_git(repository, environment, "ls-files", "--others",
                                          "--exclude-standard").splitlines(), sorted(expected_files))
            self._record(repository, events, results, payload, context, exit_code)
        self.assertFalse(root.exists())

    def _check_payload(self, events, results, payload, error):
        if events:
            event = events[0]
            self.assertEqual(set(event), {"event", "event_type", "source_daemon", "timestamp",
                                         "priority", "dedupe_key", "payload"})
            self.assertEqual(event["event"], "git_push")
            self.assertEqual(event["event_type"], "git_push")
            self.assertEqual(event["source_daemon"], "git_hook")
            self.assertEqual(event["priority"], 1)
            runner.datetime.fromisoformat(event["timestamp"])
            self.assertEqual(event["payload"], payload)
            self.assertEqual(event["dedupe_key"], "git_push:fixture:" + payload["commits"][0]["hash"])
        if results:
            result = results[0]
            self.assertEqual(set(result), {"timestamp", "dedupe_key", "error" if error else "result"})
            runner.datetime.fromisoformat(result["timestamp"])
            self.assertEqual(result["dedupe_key"], events[0]["dedupe_key"])
            if error:
                self.assertEqual(result["error"], error)
            else:
                self.assertEqual(result["result"], {"fixture": True, "delivered": False})

    def _check_handoff(self, context, payload, import_count, dispatch_count):
        target = "modules.platform_integration.social_media_orchestrator.src.multi_account_manager"
        self.assertEqual(context["imports"], [target] * import_count)
        expected = ([{"kind": "construct"}, {"kind": "dispatch", "event_type": "git_push",
                                              "payload": payload}] if dispatch_count else [])
        self.assertEqual(context["calls"], expected)

    def _record(self, repository, events, results, payload, context, exit_code):
        files = {}
        for label, name in (("events", "git_push_events.jsonl"), ("results", "git_push_dispatch_results.jsonl")):
            path = repository / "memory" / name
            raw = path.read_bytes() if path.exists() else None
            files[label] = {"utf8": raw.decode("utf-8") if raw is not None else None,
                            "sha256": hashlib.sha256(raw).hexdigest() if raw is not None else None}
        print("HOOK_EVIDENCE " + json.dumps({
            "case": self._testMethodName, "source_sha256": context["source_sha256"],
            "argv": context["argv"], "expected_payload": payload, "files": files,
            "profile": context["profile"], "exit_code": exit_code, "event_count": len(events),
            "result_count": len(results), "router_imports": context["imports"],
            "constructs": sum(call["kind"] == "construct" for call in context["calls"]),
            "dispatches": sum(call["kind"] == "dispatch" for call in context["calls"]),
            "error": results[0].get("error") if results else None,
            "result": results[0].get("result") if results else None,
            "sys_path": context["sys_path"], "isolated": context["isolated"],
            "scope": "isolated hosted runner entrypoint; inert router; no delivery"
        }, sort_keys=True))

    def test_missing_root_default(self):
        self._exercise("missing", [], 1, 1, 1, 1, 0, "No module named 'modules'")

    def test_missing_root_enqueue_only(self):
        self._exercise("missing", ["--enqueue-only"], 0, 1, 0, 0, 0)

    def test_inert_default(self):
        self._exercise("inert", [], 0, 1, 1, 1, 1)

    def test_inert_enqueue_only(self):
        self._exercise("inert", ["--enqueue-only"], 0, 1, 0, 0, 0)

    def test_inert_failure(self):
        self._exercise("failure", [], 1, 1, 1, 1, 1, "fixture dispatch failure")

    def test_unsupported_direct(self):
        self._exercise("inert", ["--dispatch-direct"], 2, 0, 0, 0, 0)


if __name__ == "__main__":
    unittest.main()
