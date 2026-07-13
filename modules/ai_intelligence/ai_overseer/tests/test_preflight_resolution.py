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


def test_main_py_wre_dashboard_insufficient_data_calls_dispatcher():
    """DJ2-A: WRE dashboard dispatches on INSUFFICIENT_DATA (WSP 97 truth distinction)."""
    import main

    with patch(
        "modules.ai_intelligence.ai_overseer.src.preflight_resolution.on_preflight_fail"
    ) as mock_dispatch:
        fake_health = {
            "insufficient_data": True,
            "total_executions": 3,
            "min_samples": 25,
            "healthy": True,
            "alerts": [],
        }
        with patch(
            "modules.infrastructure.wre_core.src.dashboard_alerts.check_dashboard_health",
            return_value=fake_health,
        ):
            with patch(
                "modules.infrastructure.wre_core.src.dashboard_alerts.DashboardAlertMonitor"
            ) as mock_monitor:
                mock_monitor.return_value.is_in_watch_period.return_value = False
                with patch.dict("os.environ", {"WRE_DASHBOARD_PREFLIGHT": "1"}, clear=False):
                    result = main.run_wre_dashboard_preflight(Path("."))

    assert result is True  # Should not block startup
    assert mock_dispatch.called
    call_kwargs = mock_dispatch.call_args.kwargs
    assert call_kwargs["component"] == "wre_dashboard"
    assert call_kwargs["severity"] == "medium"
    assert call_kwargs["payload"]["insufficient_data"] is True
    assert call_kwargs["payload"]["samples"] == 3
    assert call_kwargs["payload"]["min_samples"] == 25
    assert call_kwargs["payload"]["likely_cause"] == "cold_start_or_telemetry_drop"
    assert call_kwargs["payload"]["automation_candidate"] is True


def test_main_py_wre_dashboard_critical_alert_warns_by_default_for_menu_startup():
    """Interactive menu startup should keep dashboard signal but not auto-block by default."""
    import main

    fake_health = {
        "insufficient_data": False,
        "total_executions": 36,
        "min_samples": 25,
        "healthy": False,
        "alerts": [{"severity": "critical", "message": "critical sample"}],
    }
    with patch(
        "modules.infrastructure.wre_core.src.dashboard_alerts.check_dashboard_health",
        return_value=fake_health,
    ):
        with patch(
            "modules.infrastructure.wre_core.src.dashboard_alerts.DashboardAlertMonitor"
        ) as mock_monitor:
            mock_monitor.return_value.is_in_watch_period.return_value = False
            with patch("builtins.print") as mock_print:
                with patch.dict(
                    "os.environ",
                    {
                        "WRE_DASHBOARD_PREFLIGHT": "1",
                        "OPENCLAW_24X7": "0",
                    },
                    clear=True,
                ):
                    result = main.run_wre_dashboard_preflight(Path("."))

    assert result is True
    printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
    assert "preflight=FAIL (STABLE)" in printed
    assert "Startup blocked" not in printed


def test_main_py_wre_dashboard_critical_alert_blocks_for_24x7_runtime():
    """Autonomous 24x7 runtime preserves the fail-closed dashboard gate."""
    import main

    fake_health = {
        "insufficient_data": False,
        "total_executions": 36,
        "min_samples": 25,
        "healthy": False,
        "alerts": [{"severity": "critical", "message": "critical sample"}],
    }
    with patch(
        "modules.infrastructure.wre_core.src.dashboard_alerts.check_dashboard_health",
        return_value=fake_health,
    ):
        with patch(
            "modules.infrastructure.wre_core.src.dashboard_alerts.DashboardAlertMonitor"
        ) as mock_monitor:
            mock_monitor.return_value.is_in_watch_period.return_value = False
            with patch("builtins.print") as mock_print:
                with patch.dict(
                    "os.environ",
                    {
                        "WRE_DASHBOARD_PREFLIGHT": "1",
                        "OPENCLAW_24X7": "1",
                    },
                    clear=True,
                ):
                    result = main.run_wre_dashboard_preflight(Path("."))

    assert result is False
    printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
    assert "preflight=FAIL (STABLE, ENFORCED)" in printed
    assert "Startup blocked by AUTO enforcement" in printed


# === DJ2-C OAuth preflight dispatch tests ===


def test_main_py_oauth_no_healthy_tokens_calls_dispatcher():
    """DJ2-C: OAuth dispatches when no healthy tokens (WSP 97 truth distinction)."""
    import main
    import asyncio

    with patch(
        "modules.ai_intelligence.ai_overseer.src.preflight_resolution.on_preflight_fail"
    ) as mock_dispatch:
        fake_oauth_status = {
            "healthy": [],  # No healthy tokens
            "reauth_needed": False,  # Set False to skip interactive input prompt
            "expired": [1, 10],
        }
        with patch(
            "modules.platform_integration.youtube_auth.src.youtube_auth.preflight_oauth_check",
            return_value=fake_oauth_status,
        ):
            with patch(
                "modules.communication.livechat.src.auto_moderator_dae.AutoModeratorDAE",
                side_effect=KeyboardInterrupt,
            ):
                with patch("builtins.print"):  # Suppress output
                    try:
                        asyncio.run(main.monitor_youtube(disable_lock=True, auto_reauth=True))
                    except (KeyboardInterrupt, SystemExit):
                        pass

    assert mock_dispatch.called
    call_kwargs = mock_dispatch.call_args.kwargs
    assert call_kwargs["component"] == "oauth_youtube"
    assert call_kwargs["severity"] == "high"
    assert call_kwargs["payload"]["warning"] == "no_healthy_oauth_tokens"
    assert call_kwargs["payload"]["requires_012"] is True
    assert call_kwargs["payload"]["automation_candidate"] is False
    assert "safe_autonomous_actions" in call_kwargs["payload"]
    assert "unsafe_actions" in call_kwargs["payload"]


def test_main_py_oauth_import_error_calls_dispatcher():
    """DJ2-C: OAuth dispatches on ImportError (module unavailable)."""
    import main
    import asyncio

    with patch(
        "modules.ai_intelligence.ai_overseer.src.preflight_resolution.on_preflight_fail"
    ) as mock_dispatch:
        with patch(
            "modules.platform_integration.youtube_auth.src.youtube_auth.preflight_oauth_check",
            side_effect=ImportError("youtube_auth not installed"),
        ):
            with patch(
                "modules.communication.livechat.src.auto_moderator_dae.AutoModeratorDAE",
                side_effect=KeyboardInterrupt,
            ):
                with patch("builtins.print"):
                    try:
                        asyncio.run(main.monitor_youtube(disable_lock=True))
                    except (KeyboardInterrupt, SystemExit):
                        pass

    assert mock_dispatch.called
    call_kwargs = mock_dispatch.call_args.kwargs
    assert call_kwargs["component"] == "oauth_youtube"
    assert call_kwargs["severity"] == "medium"
    assert "import_error" in call_kwargs["payload"]["error"]
    assert call_kwargs["payload"]["requires_012"] is False


def test_main_py_oauth_exception_calls_dispatcher():
    """DJ2-C: OAuth dispatches on preflight exception (unknown state)."""
    import main
    import asyncio

    with patch(
        "modules.ai_intelligence.ai_overseer.src.preflight_resolution.on_preflight_fail"
    ) as mock_dispatch:
        with patch(
            "modules.platform_integration.youtube_auth.src.youtube_auth.preflight_oauth_check",
            side_effect=RuntimeError("preflight crashed"),
        ):
            with patch(
                "modules.communication.livechat.src.auto_moderator_dae.AutoModeratorDAE",
                side_effect=KeyboardInterrupt,
            ):
                with patch("builtins.print"):
                    try:
                        asyncio.run(main.monitor_youtube(disable_lock=True))
                    except (KeyboardInterrupt, SystemExit):
                        pass

    assert mock_dispatch.called
    call_kwargs = mock_dispatch.call_args.kwargs
    assert call_kwargs["component"] == "oauth_youtube"
    assert call_kwargs["severity"] == "high"
    assert "preflight_exception" in call_kwargs["payload"]["error"]
    assert call_kwargs["payload"]["requires_012"] is True


def test_main_py_oauth_healthy_does_not_dispatch():
    """DJ2-C: Healthy OAuth path does NOT dispatch (no false positives)."""
    import main
    import asyncio

    with patch(
        "modules.ai_intelligence.ai_overseer.src.preflight_resolution.on_preflight_fail"
    ) as mock_dispatch:
        fake_oauth_status = {
            "healthy": [1, 10],  # Healthy tokens
            "reauth_needed": False,
            "expired": [],
        }
        with patch(
            "modules.platform_integration.youtube_auth.src.youtube_auth.preflight_oauth_check",
            return_value=fake_oauth_status,
        ):
            with patch(
                "modules.communication.livechat.src.auto_moderator_dae.AutoModeratorDAE",
                side_effect=KeyboardInterrupt,
            ):
                with patch("builtins.print"):
                    try:
                        asyncio.run(main.monitor_youtube(disable_lock=True))
                    except (KeyboardInterrupt, SystemExit):
                        pass

    # Should NOT have dispatched for healthy OAuth
    assert not mock_dispatch.called


def test_main_py_oauth_dispatcher_exception_does_not_block():
    """DJ2-C: Dispatcher exception does not block existing return behavior."""
    import main
    import asyncio

    def _boom(*args, **kwargs):
        raise RuntimeError("dispatcher crashed")

    with patch(
        "modules.ai_intelligence.ai_overseer.src.preflight_resolution.on_preflight_fail",
        side_effect=_boom,
    ):
        fake_oauth_status = {
            "healthy": [],
            "reauth_needed": False,  # Set False to skip interactive input prompt
            "expired": ["set1"],
        }
        with patch(
            "modules.platform_integration.youtube_auth.src.youtube_auth.preflight_oauth_check",
            return_value=fake_oauth_status,
        ):
            with patch(
                "modules.communication.livechat.src.auto_moderator_dae.AutoModeratorDAE",
                side_effect=KeyboardInterrupt,
            ):
                with patch("builtins.print"):
                    # Should not raise even though dispatcher crashes
                    try:
                        asyncio.run(main.monitor_youtube(disable_lock=True, auto_reauth=True))
                    except (KeyboardInterrupt, SystemExit):
                        pass
    # If we got here without exception, the test passes
