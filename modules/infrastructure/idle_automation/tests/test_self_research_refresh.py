from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from modules.infrastructure.idle_automation.src.self_research_refresh import (
    SelfResearchRefresher,
    group_wsp_violations,
)
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_maintenance_handshake as handshake,
)


def test_group_wsp_violations_aggregates_and_orders_by_severity():
    violations = [
        {
            "violation_type": "WSP 22 - ModLog Documentation",
            "description": "Missing ModLog.md file",
            "severity": "medium",
            "wsp_protocol": 22,
            "affected_files": ["modules/a"],
        },
        {
            "violation_type": "WSP 62 - File Size Limit",
            "description": "File exceeds 500 lines",
            "severity": "high",
            "wsp_protocol": 62,
            "affected_files": ["modules/b/src.py"],
        },
        {
            "violation_type": "WSP 62 - File Size Limit",
            "description": "Another file exceeds 500 lines",
            "severity": "medium",
            "wsp_protocol": 62,
            "affected_files": ["modules/c/src.py"],
        },
    ]

    grouped = group_wsp_violations(violations)

    assert grouped[0]["violation_type"] == "WSP 62 - File Size Limit"
    assert grouped[0]["count"] == 2
    assert grouped[0]["issue_type"] == "SIZE_VIOLATION"
    assert grouped[0]["affected_files"] == ["modules/b/src.py", "modules/c/src.py"]


def test_holo_refresh_uses_exact_head_operational_handshake(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(
        handshake,
        "ensure_reddog_holoindex_operational",
        lambda **kwargs: calls.append(kwargs)
        or SimpleNamespace(
            ready=True,
            refreshed=True,
            status="REFRESHED",
            error="",
            generation_id="sha256:generation",
        ),
    )
    refresher = SelfResearchRefresher(repo_root=tmp_path)
    result = refresher.refresh_holo_index()
    assert result["refresh_success"] is True
    assert result["freshness_generation_id"] == "sha256:generation"
    assert calls[0]["auto_maintenance"] is True


def test_holo_refresh_never_converts_handshake_rejection_to_success(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        handshake,
        "ensure_reddog_holoindex_operational",
        lambda **_kwargs: SimpleNamespace(
            ready=False,
            refreshed=False,
            status="FAILED",
            error="HOLOINDEX_MAINTENANCE_REPOSITORY_DIRTY",
            generation_id="",
        ),
    )
    result = SelfResearchRefresher(repo_root=tmp_path).refresh_holo_index()
    assert result["refresh_success"] is False
    assert result["code_stale"] is True


def test_build_update_candidates_ranks_holo_failure_above_watchlist_noise(tmp_path: Path):
    refresher = SelfResearchRefresher(report_path=tmp_path / "report.json")

    candidates = refresher.build_update_candidates(
        holo_index={
            "refresh_attempted": True,
            "refresh_success": False,
            "stderr_tail": "import failure",
        },
        compliance={
            "top_violation_groups": [
                {
                    "violation_type": "WSP 62 - File Size Limit",
                    "issue_type": "SIZE_VIOLATION",
                    "severity": "high",
                    "count": 2,
                    "descriptions": ["File exceeds 500 lines"],
                    "affected_files": ["modules/x/src/large.py"],
                }
            ]
        },
        self_audit={
            "top_signatures": [
                {
                    "signature": "connectionerror health endpoint unavailable",
                    "count": 3,
                    "recommended_fix": "start_ironclaw_gateway",
                    "last_fix_result": "failed",
                }
            ]
        },
        grant_watchlist={
            "status": {
                "changed_count": 0,
                "error_count": 2,
                "error_items": ["Optimism Grants", "Filecoin Grants"],
            }
        },
    )

    assert candidates
    assert candidates[0]["source"] in {"holo_index", "self_audit"}
    assert any(item["source"] == "external_watchlist" for item in candidates)
    assert any(item["mps"]["priority"] == "P1" for item in candidates)


def test_build_update_candidates_includes_pqn_external_watchlist(tmp_path: Path):
    refresher = SelfResearchRefresher(report_path=tmp_path / "report.json")

    candidates = refresher.build_update_candidates(
        holo_index={},
        compliance={"top_violation_groups": []},
        self_audit={"top_signatures": []},
        grant_watchlist={"status": {}},
        pqn_research_watchlist={
            "status": {
                "changed_count": 1,
                "changed_items": ["Get Physics Done"],
                "error_count": 0,
            }
        },
    )

    assert any(item["source"] == "pqn_external_watchlist" for item in candidates)
    assert any("PQN external research" in item["title"] for item in candidates)


def test_build_update_candidates_includes_openclaw_ecosystem_watchlist(tmp_path: Path):
    refresher = SelfResearchRefresher(report_path=tmp_path / "report.json")

    candidates = refresher.build_update_candidates(
        holo_index={},
        compliance={"top_violation_groups": []},
        self_audit={"top_signatures": []},
        grant_watchlist={"status": {}},
        pqn_research_watchlist={"status": {}},
        openclaw_ecosystem_watchlist={
            "status": {
                "changed_count": 1,
                "changed_items": ["OpenViking"],
                "error_count": 0,
            }
        },
    )

    assert any(item["source"] == "openclaw_ecosystem_watchlist" for item in candidates)
    assert any("OpenClaw ecosystem" in item["title"] for item in candidates)


def test_run_reuses_cached_compliance_section(tmp_path: Path, monkeypatch):
    report_path = tmp_path / "self_research.json"
    cached_report = {
        "wsp_compliance": {
            "checked_on": datetime.now(UTC).isoformat(),
            "violation_count": 1,
            "top_violation_groups": [
                {
                    "violation_type": "WSP 22 - ModLog Documentation",
                    "issue_type": "WSP_VIOLATION",
                    "severity": "medium",
                    "count": 1,
                    "descriptions": ["Missing ModLog.md file"],
                    "affected_files": ["modules/sample"],
                }
            ],
            "cached": False,
        }
    }
    report_path.write_text(json.dumps(cached_report), encoding="utf-8")

    refresher = SelfResearchRefresher(report_path=report_path)

    def fail_scan():
        raise AssertionError("full compliance scan should not run when cache is fresh")

    monkeypatch.setattr(refresher, "scan_wsp_compliance", fail_scan)
    monkeypatch.setattr(refresher, "refresh_holo_index", lambda: {"skipped": True})
    monkeypatch.setattr(refresher, "scan_self_audit", lambda: {"top_signatures": []})
    monkeypatch.setattr(refresher, "refresh_grant_watchlist", lambda: {"status": {}})
    monkeypatch.setattr(refresher, "refresh_pqn_research_watchlist", lambda: {"status": {}})
    monkeypatch.setattr(refresher, "refresh_openclaw_ecosystem_watchlist", lambda: {"status": {}})
    monkeypatch.setattr(refresher, "publish_autonomous_tasks", lambda candidates: [])
    monkeypatch.setattr(refresher, "remember_outcome", lambda report, duration_ms: None)

    report = refresher.run(write_tasks=False, remember_outcome=False, emit_nudges=False)

    assert report["wsp_compliance"]["cached"] is True
    assert report["wsp_compliance"]["violation_count"] == 1


def _stub_self_research_dependencies(
    refresher: SelfResearchRefresher,
    monkeypatch,
) -> None:
    monkeypatch.setattr(refresher, "refresh_holo_index", lambda: {"skipped": True})
    monkeypatch.setattr(
        refresher,
        "scan_wsp_compliance",
        lambda: {"top_violation_groups": []},
    )
    monkeypatch.setattr(refresher, "scan_self_audit", lambda: {"top_signatures": []})
    monkeypatch.setattr(refresher, "refresh_grant_watchlist", lambda: {"status": {}})
    monkeypatch.setattr(
        refresher,
        "refresh_pqn_research_watchlist",
        lambda: {"status": {}},
    )
    monkeypatch.setattr(
        refresher,
        "refresh_openclaw_ecosystem_watchlist",
        lambda: {"status": {}},
    )
    monkeypatch.setattr(refresher, "publish_autonomous_tasks", lambda candidates: [])
    monkeypatch.setattr(
        refresher,
        "remember_outcome",
        lambda report, duration_ms: None,
    )


def test_run_emits_memory_nudges_when_high_value_events_detected(tmp_path: Path, monkeypatch):
    """Verify runtime wiring: emit_nudges=True calls memory nudge engine."""
    report_path = tmp_path / "reports" / "openclaw_self_research_status.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # Create workspace structure for nudge engine
    memory_dir = tmp_path / "modules/communication/moltbot_bridge/workspace/memory"
    reports_dir = tmp_path / "modules/communication/moltbot_bridge/workspace/reports"
    memory_dir.mkdir(parents=True)
    reports_dir.mkdir(parents=True)

    # Create wre_core reports dir for escalations scanner
    wre_reports = tmp_path / "modules/infrastructure/wre_core/reports"
    wre_reports.mkdir(parents=True)

    # Create self-research status with high-priority update candidate
    status = {
        "update_candidates": [
            {"title": "Critical update", "mps": {"priority": "P0", "reasoning": "Security fix"}},
        ]
    }
    (reports_dir / "openclaw_self_research_status.json").write_text(
        json.dumps(status), encoding="utf-8"
    )

    refresher = SelfResearchRefresher(report_path=report_path)
    # Override repo_root so nudge engine finds the test structure
    refresher.repo_root = tmp_path

    # Stub out all scan methods to skip external dependencies
    _stub_self_research_dependencies(refresher, monkeypatch)

    report = refresher.run(
        write_tasks=False,
        remember_outcome=False,
        emit_nudges=True,
    )

    # Verify nudges were emitted
    assert "memory_nudges_emitted" in report
    assert report["memory_nudges_emitted"] >= 1

    # Verify note files created
    nudge_notes = list(memory_dir.glob("*-nudge-*.md"))
    assert len(nudge_notes) >= 1

    # Verify memory_nudges_emitted is persisted to disk (not just in-memory)
    persisted_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert "memory_nudges_emitted" in persisted_report
    assert persisted_report["memory_nudges_emitted"] >= 1


def test_run_skips_nudges_when_emit_nudges_false(tmp_path: Path, monkeypatch):
    """Verify emit_nudges=False skips memory nudge emission."""
    report_path = tmp_path / "reports" / "openclaw_self_research_status.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    refresher = SelfResearchRefresher(report_path=report_path)

    # Stub out all scan methods
    _stub_self_research_dependencies(refresher, monkeypatch)

    report = refresher.run(
        write_tasks=False,
        remember_outcome=False,
        emit_nudges=False,
    )

    # Verify nudges not emitted when disabled
    assert "memory_nudges_emitted" not in report
