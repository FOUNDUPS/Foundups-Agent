from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from modules.infrastructure.idle_automation.src.self_research_refresh import (
    SelfResearchRefresher,
    group_wsp_violations,
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

    report = refresher.run(write_tasks=False, remember_outcome=False)

    assert report["wsp_compliance"]["cached"] is True
    assert report["wsp_compliance"]["violation_count"] == 1
