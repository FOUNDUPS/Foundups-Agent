"""Offline verification contracts. All browser/model/memory evidence is synthetic."""

import asyncio
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


# Load this dependency-free owner directly, avoiding browser package startup.
SOURCE = Path(__file__).resolve().parents[1] / "src" / "wre_visual_runner.py"
SPEC = importlib.util.spec_from_file_location("offline_wre_visual_runner", SOURCE)
runner_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner_module
SPEC.loader.exec_module(runner_module)


class Driver:
    current_url = "https://name:secret@example.test/review?token=private#secret"
    capabilities = {"browserName": "synthetic", "browserVersion": "0", "platformName": "test"}

    def save_screenshot(self, path):
        Path(path).write_bytes(b"synthetic test evidence, not a browser screenshot")
        return True


class Bridge:
    def __init__(self, *answers):
        self.answers = iter(answers)
        self.calls = []

    async def verify(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        answer = next(self.answers)
        if isinstance(answer, Exception):
            raise answer
        return SimpleNamespace(success=answer, error=None)


@pytest.fixture
def runner(tmp_path, monkeypatch):
    monkeypatch.setattr(runner_module, "SCREENSHOT_DIR", tmp_path)
    return runner_module.WREVisualTestRunner(
        Driver(), use_uitars=False, use_pattern_memory=False
    )


def step(runner, action=lambda: None, **kwargs):
    return runner.step("synthetic step", action, "visible review panel", wait_after_action=0, **kwargs)


@pytest.mark.parametrize("enabled", [False, True])
def test_unavailable_vision_never_passes_or_invents_dom_evidence(runner, enabled):
    runner.use_uitars = enabled
    assert step(runner) is False
    result = runner.get_summary()
    assert result["passed"] == 0
    assert result["failed"] == 1
    assert result["steps"][0]["verification"]["status"] == "unavailable"
    assert result["steps"][0]["verification"]["method"] == "none"


def test_initialization_error_remains_unavailable(runner, monkeypatch):
    import builtins
    original_import = builtins.__import__

    def unavailable(name, *args, **kwargs):
        if name == "modules.infrastructure.foundups_vision.src.ui_tars_bridge":
            raise ImportError("synthetic unavailable bridge")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", unavailable)
    runner.use_uitars = True
    runner._init_uitars()
    assert step(runner) is False
    assert "synthetic unavailable bridge" in runner.steps[-1].error


@pytest.mark.parametrize("answers, expected, status, observations", [
    ((True,), True, "passed", 1),
    ((False, True), True, "passed", 2),
    ((False, False), False, "failed", 2),
    ((RuntimeError("synthetic inference failure"),), False, "error", 1),
    (("true", "true"), False, "failed", 2),
])
def test_visual_observations_receive_driver_and_never_replay_action(
    runner, answers, expected, status, observations
):
    outcomes = []
    runner.use_pattern_memory = True
    runner.memory = SimpleNamespace(store_outcome=outcomes.append)
    runner.SkillOutcome = lambda **fields: SimpleNamespace(**fields)
    runner.use_uitars = True
    runner.uitars = Bridge(*answers)
    actions = []
    assert step(runner, lambda: actions.append("effect")) is expected
    assert actions == ["effect"]
    assert len(runner.uitars.calls) == observations
    assert all(kwargs["driver"] is runner.driver for _, kwargs in runner.uitars.calls)
    evidence = runner.steps[-1].verification
    assert evidence["status"] == status
    assert evidence["method"] == "visual_localization"
    assert runner.steps[-1].attempts == observations
    assert outcomes[-1].agent == "ui-tars"  # Preserve existing agent-filter consumers.
    assert outcomes[-1].success is expected


@pytest.mark.parametrize("answer", [True, False, None, "true"])
def test_dom_check_is_explicit_strict_and_distinct_from_vision(runner, answer):
    runner.use_uitars = True
    runner.uitars = Bridge(RuntimeError("vision must not run"))
    assert step(runner, dom_verify=lambda: answer) is (answer is True)
    assert runner.steps[-1].verification["method"] == "dom"
    assert runner.uitars.calls == []


@pytest.mark.parametrize("error, status", [
    (AssertionError("synthetic assertion failed"), "failed"),
    (RuntimeError("synthetic observation error"), "error"),
])
def test_dom_exceptions_never_pass(runner, error, status):
    def check():
        raise error
    assert step(runner, dom_verify=check) is False
    assert runner.steps[-1].verification["status"] == status


@pytest.mark.parametrize("raises", [False, True])
def test_failed_or_uncertain_action_is_not_replayed_or_verified(runner, raises):
    calls = []
    def action():
        calls.append("effect")
        if raises:
            raise RuntimeError("synthetic uncertain transport failure")
        return False
    assert step(runner, action, dom_verify=lambda: pytest.fail("must not verify")) is False
    assert calls == ["effect"]
    assert runner.steps[-1].attempts == 0
    assert runner.steps[-1].verification["status"] == "error"


@pytest.mark.parametrize("capture_result", [False, True])
def test_missing_screenshot_never_passes(runner, capture_result):
    runner.driver.save_screenshot = lambda path: capture_result
    assert step(runner, dom_verify=lambda: True) is False
    assert runner.steps[-1].verification["status"] == "error"
    assert runner.steps[-1].screenshot_path is None


def test_provenance_and_failure_survive_summary_and_memory(runner):
    outcomes = []
    runner.use_pattern_memory = True
    runner.memory = SimpleNamespace(store_outcome=outcomes.append)
    runner.SkillOutcome = lambda **fields: SimpleNamespace(**fields)
    assert step(runner, dom_verify=lambda: True) is True
    assert step(runner) is False
    summary = runner.get_summary()
    assert (summary["passed"], summary["failed"]) == (1, 1)
    for index, outcome in enumerate(outcomes):
        evidence = summary["steps"][index]["verification"]
        assert evidence["url"] == "https://example.test/review"
        assert evidence["observed_at"].endswith("+00:00")
        assert evidence["environment"]["browserName"] == "synthetic"
        assert evidence["assertion"] == "visible review panel"
        assert json.loads(outcome.output_result)["verification"] == evidence
        assert outcome.success is (index == 0)
        assert outcome.agent == ("dom" if index == 0 else "none")
    assert summary["steps"][1]["screenshot_path"]
    assert outcomes[-1].pattern_fidelity == 0
    assert outcomes[-1].outcome_quality == 0


@pytest.mark.parametrize("count", [0, -1, False, 1.5])
def test_invalid_observation_count_refuses_before_action(runner, count):
    with pytest.raises(ValueError):
        step(runner, lambda: pytest.fail("must not execute"), max_retries=count)
    assert runner.steps == []


def test_unrun_summary_never_reports_success(runner):
    assert runner.get_summary()["total_steps"] == 0
    assert runner.get_summary()["success_rate"] == 0


def test_active_event_loop_fails_closed_without_creating_coroutine(runner, monkeypatch):
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: object())
    runner.use_uitars = True
    runner.uitars = Bridge(True)
    assert step(runner) is False
    assert runner.uitars.calls == []
    assert runner.steps[-1].verification["status"] == "error"
