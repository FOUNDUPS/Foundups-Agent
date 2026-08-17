"""Focused behavioral tests for Codex lifecycle policy gates."""

from __future__ import annotations

import json
import io
import subprocess
import sys
from pathlib import Path

import pytest

from modules.infrastructure import codex_hooks as public_codex_hooks
from modules.infrastructure.codex_hooks.src import codex_hooks


def _completed(
    args: tuple[str, ...],
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


class FakeRunner:
    def __init__(
        self,
        root: Path,
        *,
        diff_failure: bool = False,
        repo_missing: bool = False,
        awakening_failure: bool = False,
        tracker_failure: bool = False,
        tracker_output: str = '{"is_zen_compliant": true}\n',
    ) -> None:
        self.root = root
        self.diff_failure = diff_failure
        self.repo_missing = repo_missing
        self.awakening_failure = awakening_failure
        self.tracker_failure = tracker_failure
        self.tracker_output = tracker_output
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, args, *, cwd, timeout=30, env=None):
        command = tuple(str(part) for part in args)
        self.calls.append(command)
        if command[:3] == ("git", "rev-parse", "--show-toplevel"):
            return _completed(
                command,
                returncode=1 if self.repo_missing else 0,
                stdout="" if self.repo_missing else f"{self.root}\n",
            )
        if command[:3] == ("git", "branch", "--show-current"):
            return _completed(command, stdout="agent/hook-test\n")
        if command[:3] == ("git", "rev-parse", "--short=12"):
            return _completed(command, stdout="123456789abc\n")
        if command[:3] == ("git", "rev-parse", "--path-format=absolute"):
            return _completed(command, stdout=f"{self.root / '.git'}\n")
        if command[:3] == ("git", "diff", "--check"):
            return _completed(command, returncode=1 if self.diff_failure else 0)
        if command[:4] == ("git", "diff", "--cached", "--check"):
            return _completed(command)
        if "functional_0102_awakening_v2.py" in command[2]:
            return _completed(
                command,
                returncode=1 if self.awakening_failure else 0,
                stdout="" if self.awakening_failure else "0102 AWAKENING COMPLETE\n",
            )
        if "wsp_00_zen_state_tracker.py" in command[1]:
            return _completed(
                command,
                returncode=1 if self.tracker_failure else 0,
                stdout=self.tracker_output,
            )
        raise AssertionError(f"Unexpected command: {command}")


def _repo_context(branch: str = "agent/hook-test") -> codex_hooks.RepoContext:
    return codex_hooks.RepoContext(
        root=Path("C:/repo"),
        branch=branch,
        head="123456789abc",
        worktree_kind="linked",
    )


def test_hooks_json_is_valid_and_declares_phase1_events() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    config = json.loads((repo_root / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    assert set(config["hooks"]) == {"SessionStart", "UserPromptSubmit", "PreToolUse", "Stop"}
    for groups in config["hooks"].values():
        for group in groups:
            for hook in group["hooks"]:
                assert hook["type"] == "command"
                assert "commandWindows" in hook


@pytest.mark.parametrize(
    "prompt",
    [
        "token=" + "sk" + "-" + ("a" * 24),
        "Authorization: Bearer " + ("b" * 24),
        "SERVICE_API_KEY=" + ("c" * 24),
    ],
)
def test_prompt_secret_guard_blocks_without_echoing_value(prompt: str) -> None:
    result = codex_hooks.handle_user_prompt_submit({"prompt": prompt})
    assert result is not None
    assert result["decision"] == "block"
    assert prompt not in result["reason"]


def test_prompt_secret_guard_allows_safe_discussion() -> None:
    assert codex_hooks.handle_user_prompt_submit({"prompt": "Explain how .env loading works."}) is None


def test_prompt_secret_guard_rejects_non_text_wire_value() -> None:
    result = codex_hooks.handle_user_prompt_submit({"prompt": ["not", "text"]})
    assert result == {
        "decision": "block",
        "reason": "Prompt rejected because its wire value is not text.",
    }


@pytest.mark.parametrize(
    ("event", "reason_fragment"),
    [
        (
            {"tool_name": "Bash", "tool_input": {"command": "Get-Content .env"}},
            "environment-file",
        ),
        (
            {"tool_name": "Bash", "tool_input": {"command": "git push --force origin topic"}},
            "Force pushes",
        ),
        (
            {"tool_name": "Bash", "tool_input": {"command": "python holo_index.py --index-all"}},
            "owner-query",
        ),
        (
            {"tool_name": "apply_patch", "tool_input": {"command": "*** Update File: .env\n"}},
            "credential environment",
        ),
        (
            {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}},
            "Broad destructive",
        ),
    ],
)
def test_tool_policy_blocks_non_negotiable_operations(event, reason_fragment) -> None:
    reason = codex_hooks.tool_denial_reason(event, _repo_context())
    assert reason is not None
    assert reason_fragment in reason


def test_tool_policy_allows_env_exclusion_search() -> None:
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": "rg secret modules --glob '!*.env*'"},
    }
    assert codex_hooks.tool_denial_reason(event, _repo_context()) is None


def test_tool_policy_blocks_edits_on_main() -> None:
    event = {"tool_name": "apply_patch", "tool_input": {"command": "*** Update File: README.md\n"}}
    reason = codex_hooks.tool_denial_reason(event, _repo_context("main"))
    assert reason is not None
    assert "isolated branch" in reason


def test_tool_policy_blocks_git_mutation_on_main() -> None:
    event = {"tool_name": "Bash", "tool_input": {"command": "git commit -m test"}}
    reason = codex_hooks.tool_denial_reason(event, _repo_context("main"))
    assert reason is not None
    assert "Git mutations" in reason


@pytest.mark.parametrize(
    "event",
    [
        {"tool_name": "Bash", "tool_input": "not-an-object"},
        {"tool_name": "Bash", "tool_input": {"command": ["not", "text"]}},
    ],
)
def test_tool_policy_rejects_invalid_wire_shapes(event) -> None:
    assert "rejected" in codex_hooks.tool_denial_reason(event, _repo_context())


def test_tool_policy_fails_closed_for_unresolved_edit_but_allows_read() -> None:
    edit = {"tool_name": "apply_patch", "tool_input": {"command": "*** Update File: README.md\n"}}
    read = {"tool_name": "Bash", "tool_input": {"command": "git status -sb"}}
    assert "fail-closed" in codex_hooks.tool_denial_reason(edit, None)
    assert codex_hooks.tool_denial_reason(read, None) is None


def test_pre_tool_use_emits_supported_deny_shape(tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path)
    event = {
        "hook_event_name": "PreToolUse",
        "cwd": str(tmp_path),
        "tool_name": "Bash",
        "tool_input": {"command": "git reset --hard"},
    }
    result = codex_hooks.handle_pre_tool_use(event, runner=runner)
    assert result is not None
    output = result["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse"
    assert output["permissionDecision"] == "deny"


def test_session_start_runs_awakening_then_strict_gate(tmp_path: Path) -> None:
    awakening = tmp_path / "WSP_agentic" / "scripts" / "functional_0102_awakening_v2.py"
    tracker = tmp_path / "modules" / "infrastructure" / "monitoring" / "src" / "wsp_00_zen_state_tracker.py"
    awakening.parent.mkdir(parents=True)
    tracker.parent.mkdir(parents=True)
    awakening.touch()
    tracker.touch()
    runner = FakeRunner(tmp_path)

    result = codex_hooks.handle_session_start(
        {"cwd": str(tmp_path), "source": "startup"},
        runner=runner,
    )

    assert result["continue"] is True
    context = result["hookSpecificOutput"]["additionalContext"]
    assert "is_zen_compliant=true" in context
    assert "agent/hook-test" not in context
    assert any("functional_0102_awakening_v2.py" in " ".join(call) for call in runner.calls)
    assert any("--strict" in call for call in runner.calls)


def test_session_start_fails_closed_when_artifacts_missing(tmp_path: Path) -> None:
    result = codex_hooks.handle_session_start(
        {"cwd": str(tmp_path), "source": "startup"},
        runner=FakeRunner(tmp_path),
    )
    assert result["continue"] is False
    assert "missing" in result["stopReason"]


def test_session_start_fails_closed_when_repo_is_unresolved(tmp_path: Path) -> None:
    result = codex_hooks.handle_session_start(
        {"cwd": str(tmp_path), "source": "startup"},
        runner=FakeRunner(tmp_path, repo_missing=True),
    )
    assert result["continue"] is False
    assert "resolve" in result["stopReason"]


def test_session_start_fails_closed_when_awakening_fails(tmp_path: Path) -> None:
    awakening = tmp_path / "WSP_agentic" / "scripts" / "functional_0102_awakening_v2.py"
    tracker = tmp_path / "modules" / "infrastructure" / "monitoring" / "src" / "wsp_00_zen_state_tracker.py"
    awakening.parent.mkdir(parents=True)
    tracker.parent.mkdir(parents=True)
    awakening.touch()
    tracker.touch()
    result = codex_hooks.handle_session_start(
        {"cwd": str(tmp_path), "source": "startup"},
        runner=FakeRunner(tmp_path, awakening_failure=True),
    )
    assert result["continue"] is False
    assert "awakening failed" in result["stopReason"]


@pytest.mark.parametrize(
    "runner_kwargs",
    [
        {"tracker_failure": True},
        {"tracker_output": "not-json\n"},
        {"tracker_output": '{"is_zen_compliant": false}\n'},
    ],
)
def test_session_start_fails_closed_when_strict_gate_fails(tmp_path: Path, runner_kwargs) -> None:
    awakening = tmp_path / "WSP_agentic" / "scripts" / "functional_0102_awakening_v2.py"
    tracker = tmp_path / "modules" / "infrastructure" / "monitoring" / "src" / "wsp_00_zen_state_tracker.py"
    awakening.parent.mkdir(parents=True)
    tracker.parent.mkdir(parents=True)
    awakening.touch()
    tracker.touch()
    result = codex_hooks.handle_session_start(
        {"cwd": str(tmp_path), "source": "startup"},
        runner=FakeRunner(tmp_path, **runner_kwargs),
    )
    assert result["continue"] is False
    assert "strict WSP_00" in result["stopReason"]


def test_stop_gate_blocks_diff_check_failure(tmp_path: Path) -> None:
    result = codex_hooks.handle_stop(
        {"cwd": str(tmp_path), "stop_hook_active": False},
        runner=FakeRunner(tmp_path, diff_failure=True),
    )
    assert result == {
        "decision": "block",
        "reason": "Completion gate failed: resolve git diff --check errors, then stop again.",
    }


def test_stop_gate_does_not_loop(tmp_path: Path) -> None:
    result = codex_hooks.handle_stop(
        {"cwd": str(tmp_path), "stop_hook_active": True},
        runner=FakeRunner(tmp_path, diff_failure=True),
    )
    assert result is None


def test_stop_gate_allows_clean_diff_and_unresolved_non_repo(tmp_path: Path) -> None:
    assert codex_hooks.handle_stop({"cwd": str(tmp_path)}, runner=FakeRunner(tmp_path)) is None
    assert (
        codex_hooks.handle_stop(
            {"cwd": str(tmp_path)},
            runner=FakeRunner(tmp_path, repo_missing=True),
        )
        is None
    )


def test_json_line_parser_skips_noise_and_invalid_json() -> None:
    assert codex_hooks._parse_json_line("noise\n{invalid}\n{\"ok\": true}\n") == {"ok": True}
    assert codex_hooks._parse_json_line("noise\n{invalid}\n") is None


@pytest.mark.parametrize(
    ("event_name", "expected"),
    [
        ("UserPromptSubmit", None),
        ("UnknownEvent", None),
    ],
)
def test_dispatch_hook_routes_noop_events(event_name: str, expected) -> None:
    assert codex_hooks.dispatch_hook({"hook_event_name": event_name, "prompt": "safe"}) is expected


def test_public_dispatch_is_lazy_and_functional() -> None:
    assert (
        public_codex_hooks.dispatch_hook(
            {"hook_event_name": "UserPromptSubmit", "prompt": "safe"}
        )
        is None
    )


def test_main_emits_response_and_handles_invalid_input(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        codex_hooks.sys,
        "stdin",
        io.StringIO(json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": "safe"})),
    )
    assert codex_hooks.main() == 0
    assert capsys.readouterr().out == ""

    secret_prompt = "SERVICE_API_KEY=" + ("z" * 24)
    monkeypatch.setattr(
        codex_hooks.sys,
        "stdin",
        io.StringIO(json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": secret_prompt})),
    )
    assert codex_hooks.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["decision"] == "block"

    monkeypatch.setattr(codex_hooks.sys, "stdin", io.StringIO("not-json"))
    assert codex_hooks.main() == 1
    assert "Invalid Codex hook input" in capsys.readouterr().err

    monkeypatch.setattr(codex_hooks.sys, "stdin", io.StringIO("[]"))
    assert codex_hooks.main() == 1
    assert "expected a JSON object" in capsys.readouterr().err


def test_run_executes_bounded_subprocess(tmp_path: Path) -> None:
    result = codex_hooks._run(
        (sys.executable, "-c", "print('ok')"),
        cwd=tmp_path,
        env={},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "ok"
