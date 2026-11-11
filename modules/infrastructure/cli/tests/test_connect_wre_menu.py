"""Exercise the actual readiness command without unrelated CLI startup effects."""
import ast
import os
from pathlib import Path
from typing import Any, Dict

import pytest

from modules.infrastructure.wre_core.src import dashboard_alerts, dae_preflight


def command():
    path = Path(__file__).resolve().parents[1] / "src/main_menu.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "_run_connect_wre")
    namespace = {"os": os, "Dict": Dict, "Any": Any}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[function.name]


@pytest.mark.parametrize("health,preflight,expected,result", [
    ({"healthy": True, "alerts": []}, True, "READY", True),
    ({"healthy": False, "alerts": [], "insufficient_data": True}, True, "UNKNOWN", False),
    ({"healthy": True, "alerts": []}, False, "BLOCKED", False),
])
def test_readiness_does_not_conflate_check_execution_with_readiness(
        monkeypatch, capsys, health, preflight, expected, result):
    monkeypatch.setenv("WRE_DASHBOARD_PREFLIGHT", "1")
    monkeypatch.setenv("WRE_DASHBOARD_AUTO_ENFORCE", "1")
    monkeypatch.setattr(dae_preflight, "run_dae_preflight", lambda *a, **k: preflight)
    monkeypatch.setattr(dashboard_alerts.DashboardAlertMonitor, "is_in_watch_period", lambda self: False)
    monkeypatch.setattr(dashboard_alerts, "check_dashboard_health", lambda: health)
    assert command()() is result
    output = capsys.readouterr().out
    assert f"readiness={expected}" in output
    assert "connection=CONNECTED" not in output


def test_unavailable_checker_cannot_report_ready(monkeypatch, capsys):
    monkeypatch.setattr(dae_preflight, "run_dae_preflight", lambda *a, **k: True)
    def fail():
        raise RuntimeError("fixture checker unavailable")
    monkeypatch.setattr(dashboard_alerts, "check_dashboard_health", fail)
    assert command()() is False
    assert "readiness=UNKNOWN" in capsys.readouterr().out


def test_advisory_unknown_is_not_ready(monkeypatch, capsys):
    monkeypatch.setenv("WRE_DASHBOARD_PREFLIGHT", "1")
    monkeypatch.setenv("WRE_DASHBOARD_AUTO_ENFORCE", "0")
    monkeypatch.setenv("WRE_DASHBOARD_PREFLIGHT_ENFORCED", "0")
    monkeypatch.setattr(dae_preflight, "run_dae_preflight", lambda *a, **k: True)
    monkeypatch.setattr(dashboard_alerts, "check_dashboard_health", lambda: {
        "healthy": False, "alerts": [], "insufficient_data": True})
    assert command()() is False
    assert "readiness=UNKNOWN" in capsys.readouterr().out


def test_invalid_minimum_does_not_crash_diagnostics(monkeypatch, capsys):
    monkeypatch.setenv("WRE_DASHBOARD_MIN_SAMPLES", "invalid")
    monkeypatch.setattr(dae_preflight, "run_dae_preflight", lambda *a, **k: False)
    assert command()() is False
    assert "readiness=UNKNOWN" in capsys.readouterr().out
