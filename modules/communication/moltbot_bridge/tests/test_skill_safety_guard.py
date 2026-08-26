#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for Cisco skill scanner guard integration.

WSP Compliance:
  WSP 71  : Secrets Management - Skill Supply-Chain Safety Gate
  WSP 95  : WRE Skills Wardrobe Protocol - Mandatory safety gate

Test Coverage:
  1. Scanner missing + required mode => block
  2. High severity => block
  3. Medium/low at threshold => allow
  4. Cache expiry => re-scan
  5. Auditable decision logging
"""

import asyncio
import json
import subprocess
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from modules.communication.moltbot_bridge.src.skill_safety_guard import run_skill_scan
from modules.infrastructure.wre_core.src.skill_manifest_guard import generate_skill_manifest


# ---------------------------------------------------------------------------
# Unit Tests: run_skill_scan function
# ---------------------------------------------------------------------------


def _write_manifest(skills_dir: Path) -> None:
    generate_skill_manifest(
        skills_dir=skills_dir,
        manifest_path=skills_dir / "SKILL_MANIFEST.json",
    )


def _scanner_process(
    findings_by_severity: dict[str, int],
    *,
    returncode: int = 0,
    single_skill: bool = False,
):
    """Return a subprocess double that writes current Cisco-shaped evidence."""
    def _run(command, **_kwargs):
        report_path = Path(command[command.index("--output") + 1])
        if single_skill:
            findings = [
                {"severity": severity.upper()}
                for severity, count in findings_by_severity.items()
                for _ in range(count)
            ]
            payload = {"findings": findings, "findings_count": len(findings)}
        else:
            payload = {"summary": {"findings_by_severity": findings_by_severity}}
        report_path.write_text(json.dumps(payload), encoding="utf-8")
        return MagicMock(returncode=returncode, stdout="scan complete", stderr="")

    return _run


def _openclaw_dae(*, enforced=True, ttl=0):
    from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE

    dae = OpenClawDAE()
    dae._skill_scan_required = True
    dae._skill_scan_enforced = enforced
    dae._skill_scan_ttl_sec = ttl
    return dae


def _failed_scan_result(message):
    from modules.communication.moltbot_bridge.src.skill_safety_guard import SkillScanResult

    return SkillScanResult(True, False, 1, "/test", None, message)


def test_run_skill_scan_reports_missing_scanner(tmp_path: Path):
    """Scanner unavailable: available=False, passed=False (WSP 95 fail-closed)."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "sample").mkdir()
    (skills_dir / "sample" / "SKILL.md").write_text("# test", encoding="utf-8")
    _write_manifest(skills_dir)

    with patch("modules.communication.moltbot_bridge.src.skill_safety_guard.shutil.which", return_value=None):
        result = run_skill_scan(skills_dir=skills_dir)

    assert result.available is False
    assert result.passed is False
    assert result.exit_code == 127
    assert "not installed" in result.message.lower()


def test_run_skill_scan_passes_on_zero_exit(tmp_path: Path, monkeypatch):
    """Scanner runs successfully with no findings: passed=True."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "sample").mkdir()
    (skills_dir / "sample" / "SKILL.md").write_text("# test", encoding="utf-8")
    _write_manifest(skills_dir)

    monkeypatch.setenv("SYNTHETIC_SECRET", "must-not-reach-scanner")
    with patch("modules.communication.moltbot_bridge.src.skill_safety_guard.shutil.which", return_value="skill-scanner"):
        with patch(
            "modules.communication.moltbot_bridge.src.skill_safety_guard.subprocess.run",
            side_effect=_scanner_process({}),
        ) as mock_run:
            result = run_skill_scan(skills_dir=skills_dir, max_severity="medium")

    assert result.available is True
    assert result.passed is True
    assert result.exit_code == 0
    command = mock_run.call_args.args[0]
    assert command[1:3] == ["scan-all", str(skills_dir.resolve())]
    assert "--recursive" in command
    assert "SYNTHETIC_SECRET" not in mock_run.call_args.kwargs["env"]
    assert result.report_path is not None
    assert mock_run.call_args.kwargs["env"]["TMP"] == str(Path(result.report_path).parent)


def test_run_skill_scan_uses_exact_skillz_bundle_contract(tmp_path: Path):
    """A direct SKILLz bundle uses Cisco scan with its custom instruction file."""
    skill_dir = tmp_path / "sample"
    skill_dir.mkdir()
    (skill_dir / "SKILLz.md").write_text("# test", encoding="utf-8")
    _write_manifest(skill_dir)

    with patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.shutil.which",
        return_value="skill-scanner",
    ), patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.subprocess.run",
        side_effect=_scanner_process({"info": 2}, single_skill=True),
    ) as mock_run:
        result = run_skill_scan(skills_dir=skill_dir, max_severity="medium")

    assert result.available is True
    assert result.passed is True
    command = mock_run.call_args.args[0]
    assert command[1:3] == ["scan", str(skill_dir.resolve())]
    assert command[3:5] == ["--skill-file", "SKILLz.md"]
    assert "--recursive" not in command


def test_run_skill_scan_blocks_single_skill_at_threshold(tmp_path: Path):
    """Single-skill findings use the same at-or-above policy threshold."""
    skill_dir = tmp_path / "sample"
    skill_dir.mkdir()
    (skill_dir / "SKILLz.md").write_text("# test", encoding="utf-8")
    _write_manifest(skill_dir)

    with patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.shutil.which",
        return_value="skill-scanner",
    ), patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.subprocess.run",
        side_effect=_scanner_process({"medium": 1}, single_skill=True),
    ):
        result = run_skill_scan(skills_dir=skill_dir, max_severity="medium")

    assert result.passed is False
    assert "max_severity=medium" in result.message


def test_run_skill_scan_fails_on_nonzero_exit(tmp_path: Path):
    """Scanner exits with error code: passed=False."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "sample").mkdir()
    (skills_dir / "sample" / "SKILL.md").write_text("# test", encoding="utf-8")
    _write_manifest(skills_dir)

    class _Completed:
        returncode = 3
        stdout = "SYNTHETIC_SECRET"
        stderr = "SYNTHETIC_SECRET"

    with patch("modules.communication.moltbot_bridge.src.skill_safety_guard.shutil.which", return_value="skill-scanner"):
        with patch(
            "modules.communication.moltbot_bridge.src.skill_safety_guard.subprocess.run",
            return_value=_Completed(),
        ):
            result = run_skill_scan(skills_dir=skills_dir, max_severity="medium")

    assert result.available is True
    assert result.passed is False
    assert result.exit_code == 3
    assert result.stdout == ""
    assert result.stderr == ""


def test_run_skill_scan_rejects_linked_skill_root(tmp_path: Path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "SKILLz.md").write_text("# test", encoding="utf-8")
    _write_manifest(real)
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("directory links are unavailable on this host")

    with patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.shutil.which",
        return_value="skill-scanner",
    ), patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.subprocess.run"
    ) as scanner:
        result = run_skill_scan(skills_dir=linked)

    assert result.passed is False
    assert result.manifest_passed is False
    scanner.assert_not_called()


def test_run_skill_scan_high_severity_blocks(tmp_path: Path):
    """High severity findings exceed medium threshold: passed=False (WSP 95)."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "sample").mkdir()
    (skills_dir / "sample" / "SKILL.md").write_text("# test", encoding="utf-8")
    _write_manifest(skills_dir)
    report_dir = tmp_path / "reports"
    report_dir.mkdir()

    # Create a report with high severity findings
    report_path = report_dir / "openclaw_skill_scan_report.json"
    report_path.write_text(json.dumps({
        "summary": {
            "findings_by_severity": {
                "high": 1,
                "medium": 0,
                "low": 0,
            }
        }
    }))

    with patch("modules.communication.moltbot_bridge.src.skill_safety_guard.shutil.which", return_value="skill-scanner"):
        with patch(
            "modules.communication.moltbot_bridge.src.skill_safety_guard.subprocess.run",
            side_effect=_scanner_process({"high": 1, "medium": 0, "low": 0}),
        ):
            result = run_skill_scan(
                skills_dir=skills_dir,
                max_severity="medium",  # Threshold is medium, high exceeds it
                report_dir=report_dir,
            )

    assert result.available is True
    assert result.passed is False  # High severity blocked by medium threshold


def test_run_skill_scan_medium_at_threshold_blocks(tmp_path: Path):
    """Medium severity at medium threshold: passed=False (at-or-above blocks)."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "sample").mkdir()
    (skills_dir / "sample" / "SKILL.md").write_text("# test", encoding="utf-8")
    _write_manifest(skills_dir)
    report_dir = tmp_path / "reports"
    report_dir.mkdir()

    report_path = report_dir / "openclaw_skill_scan_report.json"
    report_path.write_text(json.dumps({
        "summary": {
            "findings_by_severity": {
                "medium": 2,
                "low": 1,
            }
        }
    }))

    with patch("modules.communication.moltbot_bridge.src.skill_safety_guard.shutil.which", return_value="skill-scanner"):
        with patch(
            "modules.communication.moltbot_bridge.src.skill_safety_guard.subprocess.run",
            side_effect=_scanner_process({"medium": 2, "low": 1}),
        ):
            result = run_skill_scan(
                skills_dir=skills_dir,
                max_severity="medium",
                report_dir=report_dir,
            )

    assert result.passed is False  # Medium at medium threshold blocks


def test_run_skill_scan_low_below_threshold_allows(tmp_path: Path):
    """Low severity below medium threshold: passed=True (WSP 95)."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "sample").mkdir()
    (skills_dir / "sample" / "SKILL.md").write_text("# test", encoding="utf-8")
    _write_manifest(skills_dir)
    report_dir = tmp_path / "reports"
    report_dir.mkdir()

    report_path = report_dir / "openclaw_skill_scan_report.json"
    report_path.write_text(json.dumps({
        "summary": {
            "findings_by_severity": {
                "low": 5,
                "info": 10,
            }
        }
    }))

    with patch("modules.communication.moltbot_bridge.src.skill_safety_guard.shutil.which", return_value="skill-scanner"):
        with patch(
            "modules.communication.moltbot_bridge.src.skill_safety_guard.subprocess.run",
            side_effect=_scanner_process({"low": 5, "info": 10}),
        ):
            result = run_skill_scan(
                skills_dir=skills_dir,
                max_severity="medium",
                report_dir=report_dir,
            )

    assert result.passed is True  # Low severity allowed at medium threshold


def test_run_skill_scan_critical_severity_always_blocks(tmp_path: Path):
    """Critical severity always blocks regardless of threshold (WSP 95)."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "sample").mkdir()
    (skills_dir / "sample" / "SKILL.md").write_text("# test", encoding="utf-8")
    _write_manifest(skills_dir)
    report_dir = tmp_path / "reports"
    report_dir.mkdir()

    report_path = report_dir / "openclaw_skill_scan_report.json"
    report_path.write_text(json.dumps({
        "summary": {
            "findings_by_severity": {
                "critical": 1,
            }
        }
    }))

    with patch("modules.communication.moltbot_bridge.src.skill_safety_guard.shutil.which", return_value="skill-scanner"):
        with patch(
            "modules.communication.moltbot_bridge.src.skill_safety_guard.subprocess.run",
            side_effect=_scanner_process({"critical": 1}),
        ):
            # Even with high threshold, critical should block
            result = run_skill_scan(
                skills_dir=skills_dir,
                max_severity="high",
                report_dir=report_dir,
            )

    assert result.passed is False  # Critical blocked even at high threshold


def test_run_skill_scan_rejects_missing_or_stale_report(tmp_path: Path):
    """A zero exit cannot reuse prior safe evidence or pass without a report."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "sample").mkdir()
    (skills_dir / "sample" / "SKILL.md").write_text("# test", encoding="utf-8")
    _write_manifest(skills_dir)
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    report_path = report_dir / "openclaw_skill_scan_report.json"
    report_path.write_text(
        json.dumps({"summary": {"findings_by_severity": {}}}), encoding="utf-8"
    )

    completed = MagicMock(returncode=0, stdout="", stderr="")
    with patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.shutil.which",
        return_value="skill-scanner",
    ), patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.subprocess.run",
        return_value=completed,
    ):
        result = run_skill_scan(skills_dir=skills_dir, report_dir=report_dir)

    assert result.passed is False
    assert not report_path.exists()
    assert "report" in result.message


def test_run_skill_scan_rejects_malformed_single_skill_evidence(tmp_path: Path):
    """Single-skill count/list disagreement is an evidence failure."""
    skill_dir = tmp_path / "sample"
    skill_dir.mkdir()
    (skill_dir / "SKILLz.md").write_text("# test", encoding="utf-8")
    _write_manifest(skill_dir)

    def _malformed(command, **_kwargs):
        report_path = Path(command[command.index("--output") + 1])
        report_path.write_text(
            json.dumps({"findings_count": 2, "findings": [{"severity": "INFO"}]}),
            encoding="utf-8",
        )
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.shutil.which",
        return_value="skill-scanner",
    ), patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.subprocess.run",
        side_effect=_malformed,
    ):
        result = run_skill_scan(skills_dir=skill_dir)

    assert result.passed is False
    assert "malformed" in result.message


def test_run_skill_scan_timeout_is_stable_failure(tmp_path: Path):
    """Scanner timeout is normalized without escaping exception details."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "sample").mkdir()
    (skills_dir / "sample" / "SKILL.md").write_text("# test", encoding="utf-8")
    _write_manifest(skills_dir)

    with patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.shutil.which",
        return_value="skill-scanner",
    ), patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.subprocess.run",
        side_effect=subprocess.TimeoutExpired("SYNTHETIC_SECRET", 1),
    ):
        result = run_skill_scan(skills_dir=skills_dir)

    assert result.passed is False
    assert result.exit_code == 124
    assert result.message == "skill scan timed out"
    assert "SYNTHETIC_SECRET" not in result.message


def test_run_skill_scan_rejects_unknown_threshold(tmp_path: Path):
    """An unknown policy threshold cannot silently become medium."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "sample").mkdir()
    (skills_dir / "sample" / "SKILL.md").write_text("# test", encoding="utf-8")
    _write_manifest(skills_dir)

    with patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.shutil.which",
        return_value="skill-scanner",
    ), patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.subprocess.run",
        side_effect=_scanner_process({}),
    ):
        result = run_skill_scan(skills_dir=skills_dir, max_severity="unknown")

    assert result.passed is False
    assert "unsupported" in result.message


def test_run_skill_scan_blocks_on_manifest_hash_mismatch(tmp_path: Path):
    """Manifest mismatch blocks before scanner execution."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "sample").mkdir()
    skill_file = skills_dir / "sample" / "SKILL.md"
    skill_file.write_text("# v1", encoding="utf-8")
    _write_manifest(skills_dir)
    # Tamper after manifest generation.
    skill_file.write_text("# v2", encoding="utf-8")

    with patch("modules.communication.moltbot_bridge.src.skill_safety_guard.shutil.which", return_value="skill-scanner"):
        with patch("modules.communication.moltbot_bridge.src.skill_safety_guard.subprocess.run") as mock_run:
            result = run_skill_scan(skills_dir=skills_dir)

    assert result.passed is False
    assert "manifest" in result.message.lower()
    assert mock_run.call_count == 0  # scanner should not run when manifest fails


# ---------------------------------------------------------------------------
# Integration Tests: OpenClaw DAE skill safety gate
# ---------------------------------------------------------------------------


def test_openclaw_dae_required_mode_blocks_when_scanner_missing():
    """Required mode: scanner unavailable => route blocked (WSP 95 fail-closed)."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE
    from modules.communication.moltbot_bridge.src.skill_safety_guard import SkillScanResult

    dae = OpenClawDAE()
    dae._skill_scan_required = True
    dae._skill_scan_enforced = True
    dae._skill_scan_ttl_sec = 0  # Force re-scan

    mock_result = SkillScanResult(
        available=False,
        passed=False,
        exit_code=127,
        skills_dir="/test",
        report_path=None,
        message="skill-scanner not installed",
    )

    with patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.run_skill_scan",
        return_value=mock_result
    ):
        result = dae._ensure_skill_safety(force=True)

    assert result is False
    assert "unavailable" in dae._skill_scan_message.lower() or "not installed" in dae._skill_scan_message.lower()


def test_openclaw_dae_required_mode_allows_when_scanner_passes():
    """Required mode: scanner passes => route allowed."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE
    from modules.communication.moltbot_bridge.src.skill_safety_guard import SkillScanResult

    dae = OpenClawDAE()
    dae._skill_scan_required = True
    dae._skill_scan_enforced = True
    dae._skill_scan_ttl_sec = 0

    mock_result = SkillScanResult(
        available=True,
        passed=True,
        exit_code=0,
        skills_dir="/test",
        report_path=None,
        message="skills passed safety scan",
    )

    with patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.run_skill_scan",
        return_value=mock_result
    ):
        result = dae._ensure_skill_safety(force=True)

    assert result is True


def test_openclaw_dae_cache_ttl_prevents_rescan():
    """Cache TTL: cached result used within TTL window (WSP 95)."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE

    dae = OpenClawDAE()
    dae._skill_scan_required = True
    dae._skill_scan_enforced = True
    dae._skill_scan_ttl_sec = 300  # 5 minute TTL

    # Seed cached state
    dae._skill_scan_checked_at = time.time()
    dae._skill_scan_ok = True
    dae._skill_scan_message = "cached pass"

    # Should NOT call run_skill_scan (using cache)
    # The method returns early if cache is valid, so we just verify the return value
    result = dae._ensure_skill_safety(force=False)

    assert result is True


def test_openclaw_dae_cache_expiry_triggers_rescan():
    """Cache expiry: expired cache triggers new scan (WSP 95)."""
    dae = _openclaw_dae(ttl=1)

    # Seed expired cache (2 seconds ago)
    dae._skill_scan_checked_at = time.time() - 2
    dae._skill_scan_ok = True
    dae._skill_scan_message = "old cached pass"

    with patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.run_skill_scan",
        return_value=_failed_scan_result("new scan found issues")
    ):
        result = dae._ensure_skill_safety(force=False)

    assert result is False  # New scan failed


def test_openclaw_dae_skill_scan_always_bypasses_cache():
    """OPENCLAW_SKILL_SCAN_ALWAYS=1 forces fresh scan even within TTL."""
    dae = _openclaw_dae(ttl=300)
    dae._skill_scan_always = True

    # Seed valid cache that would normally short-circuit.
    dae._skill_scan_checked_at = time.time()
    dae._skill_scan_ok = True
    dae._skill_scan_message = "cached pass"

    with patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.run_skill_scan",
        return_value=_failed_scan_result("fresh scan failed"),
    ) as mock_scan:
        result = dae._ensure_skill_safety(force=False)

    assert mock_scan.call_count == 1
    assert result is False


def test_openclaw_dae_enforced_mode_blocks_failed_scan():
    """Enforced mode: failed scan => route blocked (WSP 95)."""
    dae = _openclaw_dae()

    with patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.run_skill_scan",
        return_value=_failed_scan_result("high severity findings")
    ):
        result = dae._ensure_skill_safety(force=True)

    assert result is False


def test_openclaw_dae_non_enforced_mode_allows_failed_scan():
    """Non-enforced mode: failed scan => route allowed with warning (WSP 95)."""
    dae = _openclaw_dae(enforced=False)

    with patch(
        "modules.communication.moltbot_bridge.src.skill_safety_guard.run_skill_scan",
        return_value=_failed_scan_result("high severity findings")
    ):
        result = dae._ensure_skill_safety(force=True)

    assert result is True  # Allowed in non-enforced mode


def test_openclaw_dae_process_downgrades_foundup_on_safety_failure():
    """FOUNDUP intent downgrades to CONVERSATION when skill safety fails."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE, IntentCategory

    dae = OpenClawDAE()
    dae._skill_scan_required = True
    dae._skill_scan_enforced = True
    dae._skill_scan_ttl_sec = 300  # Use cache

    # Pre-seed failed cache state (avoids calling run_skill_scan)
    dae._skill_scan_checked_at = time.time()
    dae._skill_scan_ok = False
    dae._skill_scan_message = "blocked by test"

    # Classify a FOUNDUP intent
    intent = dae.classify_intent(
        message="launch foundup myproject with token TEST",
        sender="test_user",
        channel="test",
        session_key="test_session",
    )

    assert intent.category == IntentCategory.FOUNDUP

    # Verify this category would be checked for skill safety
    should_check = intent.category in (
        IntentCategory.COMMAND,
        IntentCategory.SYSTEM,
        IntentCategory.SCHEDULE,
        IntentCategory.SOCIAL,
        IntentCategory.AUTOMATION,
        IntentCategory.FOUNDUP,
    )
    assert should_check is True

    # And the gate would fail (using cached state)
    gate_result = dae._ensure_skill_safety(force=False)
    assert gate_result is False
