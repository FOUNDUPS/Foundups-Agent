"""
Tests for preflight_resolution dispatch contract (DJ Phase 1).

Acceptance:
- on_preflight_fail() returns a structured dispatched/escalated event.
- Artifact written to alerts_root provided by caller (no repo pollution).
- AI-unavailable path still returns a valid event (skipped state).
- No fix is auto-applied.
- Two main.py emitters (DEP-SECURITY, WSP-FRAMEWORK) call the dispatcher.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from modules.ai_intelligence.ai_overseer.src import preflight_resolution as pr


def test_dispatch_returns_structured_event(tmp_path):
    result = pr.on_preflight_fail(
        component="dep_security",
        severity="critical",
        payload={"critical": 4, "high": 4, "unknown": 3},
        source="test",
        alerts_root=tmp_path,
        skip_ai=True,
    )

    assert result["component"] == "dep_security"
    assert result["severity"] == "critical"
    assert result["state"] in {"escalated", "dispatched", "skipped"}
    assert result["requires_012"] is True
    assert "artifact_path" in result


def test_critical_severity_escalates_to_012(tmp_path):
    result = pr.on_preflight_fail(
        component="dep_security",
        severity="critical",
        payload={"critical": 1},
        alerts_root=tmp_path,
        skip_ai=True,
    )
    assert result["requires_012"] is True
    assert result["state"] == "escalated"


def test_medium_severity_does_not_auto_escalate(tmp_path):
    result = pr.on_preflight_fail(
        component="wsp_framework",
        severity="medium",
        payload={"drift_count": 0, "framework_only_count": 0},
        alerts_root=tmp_path,
        skip_ai=True,
    )
    assert result["requires_012"] is False
    assert result["state"] == "skipped"


def test_automation_candidate_flag_passes_through(tmp_path):
    result = pr.on_preflight_fail(
        component="obs_start",
        severity="high",
        payload={"automation_candidate": True, "requires_012": True},
        alerts_root=tmp_path,
        skip_ai=True,
    )
    assert result["automation_candidate"] is True
    assert result["requires_012"] is True


def test_artifact_written_to_alerts_root(tmp_path):
    result = pr.on_preflight_fail(
        component="dep_security",
        severity="high",
        payload={"high": 4},
        alerts_root=tmp_path,
        skip_ai=True,
    )
    path = Path(result["artifact_path"])
    assert path.exists()
    assert path.parent == tmp_path
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["component"] == "dep_security"
    assert data["severity"] == "high"


def test_ai_unavailable_path_returns_valid_event(tmp_path):
    with patch.object(pr, "_try_ai_proposal", return_value=None):
        result = pr.on_preflight_fail(
            component="dep_security",
            severity="high",
            payload={"high": 4},
            alerts_root=tmp_path,
        )
    assert result["state"] in {"escalated", "skipped", "dispatched"}
    assert result["proposal"] is None
    assert any("ai_proposal_unavailable" in n for n in result["notes"])


def test_pattern_memory_unavailable_path_is_graceful(tmp_path):
    with patch.object(pr, "_try_pattern_recall", return_value=None):
        result = pr.on_preflight_fail(
            component="dep_security",
            severity="high",
            payload={"high": 4},
            alerts_root=tmp_path,
            skip_ai=True,
        )
    assert result["pattern_recall"] is None


def test_dispatch_never_raises_even_on_internal_error(tmp_path, monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("simulated artifact write failure")

    monkeypatch.setattr(pr, "_write_event_artifact", _boom)

    result = pr.on_preflight_fail(
        component="dep_security",
        severity="high",
        payload={},
        alerts_root=tmp_path,
        skip_ai=True,
    )
    assert result["state"] == "detected"
    assert "dispatch_internal_error" in result.get("notes", [])


def test_no_fix_is_auto_applied(tmp_path, monkeypatch):
    side_effects = {"called": False}

    def _spy_proposal(event):
        side_effects["called"] = True
        return {"engine": "qwen", "proposal": "upgrade foo==2.0.0", "available": True}

    monkeypatch.setattr(pr, "_try_ai_proposal", _spy_proposal)

    result = pr.on_preflight_fail(
        component="dep_security",
        severity="high",
        payload={"high": 4},
        alerts_root=tmp_path,
    )

    assert side_effects["called"] is True
    assert result["state"] in {"proposed", "escalated"}
    assert result["proposal"]["proposal"] == "upgrade foo==2.0.0"
    data = json.loads(Path(result["artifact_path"]).read_text(encoding="utf-8"))
    assert "applied" not in data
    assert "fixed" not in data


def test_component_name_is_sanitised(tmp_path):
    result = pr.on_preflight_fail(
        component="dep security / critical",
        severity="high",
        payload={},
        alerts_root=tmp_path,
        skip_ai=True,
    )
    path = Path(result["artifact_path"])
    assert "/" not in path.name
    assert " " not in path.name


def test_main_py_dep_security_calls_dispatcher():
    import main

    with patch(
        "modules.ai_intelligence.ai_overseer.src.preflight_resolution.on_preflight_fail"
    ) as mock_dispatch:
        fake_status = {
            "totals": {"critical": 4, "high": 4, "unknown": 3},
            "tool_failures": 0,
            "cached": False,
            "passed": False,
        }
        with patch(
            "modules.infrastructure.wre_core.src.dependency_security_preflight.run_dependency_security_preflight",
            return_value=fake_status,
        ):
            with patch.dict("os.environ", {"OPENCLAW_DEP_SECURITY_PREFLIGHT": "1",
                                           "OPENCLAW_DEP_SECURITY_PREFLIGHT_ENFORCED": "0",
                                           "OPENCLAW_24X7": "0"}, clear=False):
                main.run_dependency_security_preflight(Path("."))

    assert mock_dispatch.called
    call_kwargs = mock_dispatch.call_args.kwargs
    assert call_kwargs["component"] == "dep_security"
    assert call_kwargs["severity"] in {"critical", "high", "medium"}
    assert call_kwargs["payload"]["critical"] == 4


def test_main_py_wsp_framework_calls_dispatcher():
    import main

    class _FakeOverseer:
        def monitor_wsp_framework(self, force=False, emit_alert=False):
            return {
                "available": True,
                "drift_count": 0,
                "framework_only": ["WSP_XX"],
                "knowledge_only": [],
                "index_issues": ["dup"],
                "cached": False,
            }

    with patch(
        "modules.ai_intelligence.ai_overseer.src.preflight_resolution.on_preflight_fail"
    ) as mock_dispatch:
        with patch.dict("os.environ", {"WSP_FRAMEWORK_PREFLIGHT": "1",
                                       "WSP_FRAMEWORK_PREFLIGHT_ENFORCED": "0"}, clear=False):
            main.run_wsp_framework_preflight(Path("."), overseer=_FakeOverseer())

    assert mock_dispatch.called
    call_kwargs = mock_dispatch.call_args.kwargs
    assert call_kwargs["component"] == "wsp_framework"
    assert call_kwargs["payload"]["framework_only_count"] == 1
    assert call_kwargs["payload"]["index_issue_count"] == 1
