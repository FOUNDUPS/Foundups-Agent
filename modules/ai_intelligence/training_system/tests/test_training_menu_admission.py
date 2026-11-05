"""Opening or refusing the menu must not load corpus, models or pattern memory."""
import importlib
import sys

import pytest


@pytest.fixture
def launch(monkeypatch):
    # An unavailable model stack must not prevent rendering the operator menu.
    monkeypatch.setitem(sys.modules, "holo_index.qwen_advisor.pattern_memory", None)
    sys.modules.pop("modules.ai_intelligence.training_system.scripts.launch", None)
    return importlib.import_module("modules.ai_intelligence.training_system.scripts.launch")


def test_menu_renders_and_returns_without_action_preflight(launch, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("Opening the menu must not admit or initialize an action")
    monkeypatch.setattr(launch, "run_dae_preflight", forbidden)
    monkeypatch.setattr("builtins.input", lambda prompt: "0")
    launch.run_training_system()
    output = capsys.readouterr().out
    assert "TRAINING" in output
    assert "diagnostic" in output.lower()


@pytest.mark.parametrize("choice", ["1", "2", "5", "6", "7", "8", "9"])
def test_refused_actions_stay_in_menu_without_loading_models(launch, monkeypatch, capsys, choice):
    seen = []
    def refuse(name, quiet=False):
        seen.append(name)
        return False
    monkeypatch.setattr(launch, "run_dae_preflight", refuse)
    inputs = iter([choice, "0"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    launch.run_training_system()
    assert seen == ["training_system_dae"]
    assert "BLOCKED" in capsys.readouterr().out


def test_diagnostics_then_back_never_admits_action(launch, monkeypatch, capsys):
    from modules.infrastructure.wre_core.src import dashboard_alerts
    def forbidden(*args, **kwargs):
        pytest.fail("Diagnostics must not admit an action")
    monkeypatch.setattr(launch, "run_dae_preflight", forbidden)
    monkeypatch.setattr(dashboard_alerts, "check_dashboard_health", lambda: {
        "status": "UNKNOWN", "dashboard": {}, "unknown_metrics": []})
    monkeypatch.setattr(dashboard_alerts, "print_research_report_summary", lambda: None)
    inputs = iter(["D", "0"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    launch.run_training_system()
    assert "WRE evidence=UNKNOWN" in capsys.readouterr().out
