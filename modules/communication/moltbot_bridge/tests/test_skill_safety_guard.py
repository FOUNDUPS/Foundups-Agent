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
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from modules.communication.moltbot_bridge.src.skill_safety_guard import run_skill_scan
from modules.communication.moltbot_bridge.src import skill_safety_guard as guard
from modules.infrastructure.wre_core.src.skill_manifest_guard import generate_skill_manifest


# ---------------------------------------------------------------------------
# Unit Tests: run_skill_scan function
# ---------------------------------------------------------------------------


def _write_manifest(skills_dir: Path) -> None:
    generate_skill_manifest(
        skills_dir=skills_dir,
        manifest_path=skills_dir / "SKILL_MANIFEST.json",
    )


def _wardrobe(tmp_path):
    skills_dir = tmp_path / "skills"
    instruction = skills_dir / "sample" / "SKILL.md"
    instruction.parent.mkdir(parents=True)
    instruction.write_text("# test", encoding="utf-8")
    _write_manifest(skills_dir)
    return skills_dir


def _threshold_scan(tmp_path, counts, max_severity="medium"):
    skills_dir = _wardrobe(tmp_path)
    reports = tmp_path / "reports"
    reports.mkdir()
    # Seed old evidence as well as emitting a current report.
    (reports / "openclaw_skill_scan_report.json").write_text(
        json.dumps({"summary": {"findings_by_severity": counts}}), encoding="utf-8"
    )
    with patch.object(guard, "_locate_scanner", return_value="skill-scanner"), patch.object(
        guard.subprocess, "run", side_effect=_scanner_process(counts)
    ):
        return run_skill_scan(skills_dir, max_severity=max_severity, report_dir=reports)


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


@pytest.fixture(params=[False, True], ids=["wardrobe", "bundle"])
def scan_subject(tmp_path, monkeypatch, request):
    skills = tmp_path / "skills"
    instruction = skills / "SKILLz.md" if request.param else skills / "sample" / "SKILL.md"
    instruction.parent.mkdir(parents=True)
    instruction.write_text("# test", encoding="utf-8")
    _write_manifest(skills)
    monkeypatch.setattr(guard, "_locate_scanner", lambda _: "skill-scanner")
    return skills, tmp_path / "reports", request.param


@pytest.mark.parametrize("first,second", [({"high": 1}, {}), ({}, {"high": 1}), (None, {})])
def test_overlapping_scans_keep_own_verdict(scan_subject, monkeypatch, first, second):
    skills, reports, single = scan_subject
    paths, nested = [], []

    def scan(command, **kwargs):
        path = Path(command[command.index("--output") + 1])
        paths.append(path)
        assert kwargs["env"]["TMP"] == kwargs["env"]["TEMP"] == str(path.parent)
        counts = first if len(paths) == 1 else second
        completed = MagicMock(returncode=0, stdout="", stderr="")
        if counts is not None:
            completed = _scanner_process(counts, single_skill=single)(command, **kwargs)
        if len(paths) == 1:
            nested.append(run_skill_scan(skills, report_dir=reports))
        return completed

    monkeypatch.setattr(guard.subprocess, "run", scan)
    result = run_skill_scan(skills, report_dir=reports)
    assert result.passed is (first == {})
    assert nested[0].passed is (second == {})
    assert paths[0].parent != paths[1].parent
    assert all(not path.parent.exists() for path in paths)
    assert result.report_path == str(reports / "openclaw_skill_scan_report.json")


@pytest.mark.parametrize("error", [subprocess.TimeoutExpired("synthetic", 1), OSError("synthetic"), KeyboardInterrupt()])
def test_interrupted_scan_cleans_only_its_workspace(scan_subject, monkeypatch, error):
    skills, reports, single = scan_subject
    paths = []

    def scan(command, **kwargs):
        paths.append(Path(command[command.index("--output") + 1]))
        _scanner_process({}, single_skill=single)(command, **kwargs)
        raise error

    monkeypatch.setattr(guard.subprocess, "run", scan)
    if isinstance(error, KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            run_skill_scan(skills, report_dir=reports)
    else:
        result = run_skill_scan(skills, report_dir=reports)
        assert result.passed is False
        assert result.exit_code == (124 if isinstance(error, subprocess.TimeoutExpired) else 126)
    assert not paths[0].exists()
    assert reports.is_dir() and not list(reports.iterdir())


@pytest.mark.parametrize("operation", ["TemporaryDirectory", "replace"])
def test_report_storage_failure_cannot_admit(scan_subject, monkeypatch, operation):
    skills, reports, single = scan_subject
    monkeypatch.setattr(guard.subprocess, "run", _scanner_process({}, single_skill=single))
    owner = guard.tempfile if operation == "TemporaryDirectory" else guard.os
    with patch.object(owner, operation, side_effect=OSError("synthetic detail")):
        result = run_skill_scan(skills, report_dir=reports)
    assert result.passed is False and result.exit_code == 4
    assert "synthetic detail" not in result.message
    assert reports.is_dir() and not list(reports.iterdir())


_SCAN_PROCESS = '''
import json, sys, time
from pathlib import Path
from modules.communication.moltbot_bridge.src import skill_safety_guard as guard
from modules.communication.moltbot_bridge.tests.test_skill_safety_guard import _scanner_process
skills, reports, kind = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
ready, done = reports.parent / "ready", reports.parent / "done"
def wait_for(path):
    deadline = time.monotonic() + 10
    while not path.exists():
        if time.monotonic() > deadline: raise TimeoutError("peer scan did not finish")
        time.sleep(0.01)
def scan(command, **kwargs):
    global private
    private = Path(command[command.index("--output") + 1])
    if kind == "clean": wait_for(ready)
    completed = _scanner_process({} if kind == "clean" else {"high": 1})(command, **kwargs)
    if kind != "clean":
        ready.touch()
        wait_for(done)
    return completed
guard._locate_scanner = lambda _: "skill-scanner"
guard.subprocess.run = scan
result = guard.run_skill_scan(skills, report_dir=reports)
if kind == "clean": done.touch()
print(json.dumps({"passed": result.passed, "private": str(private.parent)}))
'''


def test_independent_processes_keep_own_scan_evidence(scan_subject):
    skills, reports, _ = scan_subject
    workers = []
    try:
        for kind in ("unsafe", "clean"):
            workers.append(subprocess.Popen(
                [sys.executable, "-B", "-c", _SCAN_PROCESS, str(skills), str(reports), kind],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
            ))
        results = []
        for worker in workers:
            stdout, stderr = worker.communicate(timeout=20)
            assert worker.returncode == 0, stderr
            results.append(json.loads(stdout))
    finally:
        for worker in workers:
            if worker.poll() is None:
                worker.kill()
            worker.wait(timeout=5)
    assert [result["passed"] for result in results] == [False, True]
    assert results[0]["private"] != results[1]["private"]
    assert all(not Path(result["private"]).exists() for result in results)
    assert [path.name for path in reports.iterdir()] == ["openclaw_skill_scan_report.json"]


def test_run_skill_scan_reports_missing_scanner(tmp_path: Path):
    """Scanner unavailable: available=False, passed=False (WSP 95 fail-closed)."""
    skills_dir = _wardrobe(tmp_path)

    with patch("modules.communication.moltbot_bridge.src.skill_safety_guard.shutil.which", return_value=None):
        result = run_skill_scan(skills_dir=skills_dir)

    assert result.available is False
    assert result.passed is False
    assert result.exit_code == 127
    assert "not installed" in result.message.lower()


def test_run_skill_scan_passes_on_zero_exit(tmp_path: Path, monkeypatch):
    """Scanner runs successfully with no findings: passed=True."""
    skills_dir = _wardrobe(tmp_path)

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
    private_report = Path(command[command.index("--output") + 1])
    assert mock_run.call_args.kwargs["env"]["TMP"] == str(private_report.parent)
    assert private_report.parent.parent == Path(result.report_path).parent
    assert not private_report.parent.exists()


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
    skills_dir = _wardrobe(tmp_path)

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
    result = _threshold_scan(tmp_path, {'high': 1, 'medium': 0, 'low': 0}, 'medium')
    assert result.available is True
    assert result.passed is False


def test_run_skill_scan_medium_at_threshold_blocks(tmp_path: Path):
    """Medium severity at medium threshold: passed=False (at-or-above blocks)."""
    result = _threshold_scan(tmp_path, {'medium': 2, 'low': 1}, 'medium')
    assert result.passed is False


def test_run_skill_scan_low_below_threshold_allows(tmp_path: Path):
    """Low severity below medium threshold: passed=True (WSP 95)."""
    result = _threshold_scan(tmp_path, {'low': 5, 'info': 10}, 'medium')
    assert result.passed is True


def test_run_skill_scan_critical_severity_always_blocks(tmp_path: Path):
    """Critical severity always blocks regardless of threshold (WSP 95)."""
    result = _threshold_scan(tmp_path, {'critical': 1}, 'high')
    assert result.passed is False


def test_run_skill_scan_rejects_missing_or_stale_report(tmp_path: Path):
    """A zero exit cannot reuse prior safe evidence or pass without a report."""
    skills_dir = _wardrobe(tmp_path)
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
    skills_dir = _wardrobe(tmp_path)

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
    skills_dir = _wardrobe(tmp_path)

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


@pytest.mark.parametrize("available", [False, True])
def test_openclaw_dae_required_mode_uses_current_scanner(available):
    dae = _openclaw_dae()
    message = "skills passed safety scan" if available else "skill-scanner not installed"
    result = guard.SkillScanResult(available, available, 0 if available else 127,
                                  "/test", None, message)
    with patch.object(guard, "run_skill_scan", return_value=result):
        assert dae._ensure_skill_safety(force=True) is available
    assert dae._skill_scan_message == message


@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize("age", [-30, 1])
@pytest.mark.parametrize("severity", ["low", "high"])
@pytest.mark.parametrize("force", [False, True])
def test_openclaw_dae_cached_verdict_never_skips_current_scan(cached, age, severity, force):
    dae = _openclaw_dae(ttl=300)
    dae._skill_scan_always = False
    dae._skill_scan_checked_at = time.time() - age
    dae._skill_scan_ok = cached
    dae._skill_scan_max_severity = severity
    result = guard.SkillScanResult(True, not cached, int(cached), "/test", None, "current")
    with patch.object(guard, "run_skill_scan", return_value=result) as scan:
        assert dae._ensure_skill_safety(force=force) is (not cached)
    scan.assert_called_once()
    assert scan.call_args.kwargs["max_severity"] == severity
    assert dae._skill_scan_message == "current"


@pytest.mark.parametrize("change", ["edit", "add", "delete", "manifest"])
def test_openclaw_dae_rechecks_changed_wardrobe(tmp_path, change):
    dae = _openclaw_dae(ttl=300)
    dae.repo_root = tmp_path
    dae._skill_scan_always = False
    parent = tmp_path / "modules/communication/moltbot_bridge/workspace"
    skills = _wardrobe(parent)
    instruction = skills / "sample/SKILL.md"
    with patch.object(guard, "_locate_scanner", return_value="scanner"), patch.object(
        guard.subprocess, "run", side_effect=_scanner_process({})
    ) as scan:
        assert dae._ensure_skill_safety(force=True) is True
        if change == "edit":
            instruction.write_text("changed", encoding="utf-8")
        elif change == "add":
            (skills / "SKILLz.md").write_text("unlisted", encoding="utf-8")
        elif change == "delete":
            instruction.unlink()
        else:
            (skills / "SKILL_MANIFEST.json").write_text("{}", encoding="utf-8")
        assert dae._ensure_skill_safety(force=False) is False
    assert scan.call_count == 1  # Current manifest rejection precedes the scanner.
    assert "manifest verification failed" in dae._skill_scan_message


@pytest.mark.parametrize("ttl,age,always", [(1, 2, False), (300, 0, True)])
def test_openclaw_dae_legacy_cache_controls_rescan(ttl, age, always):
    dae = _openclaw_dae(ttl=ttl)
    dae._skill_scan_always = always
    dae._skill_scan_checked_at = time.time() - age
    dae._skill_scan_ok = True
    with patch.object(guard, "run_skill_scan", return_value=_failed_scan_result("fresh")) as scan:
        assert dae._ensure_skill_safety(force=False) is False
    scan.assert_called_once()


@pytest.mark.parametrize("mode", ["scan", "unavailable", "import_error"])
@pytest.mark.parametrize("passed", [False, True])
def test_openclaw_dae_returns_own_verdict(monkeypatch, mode, passed):
    dae = _openclaw_dae()
    dae._skill_scan_required = not passed
    first = guard.SkillScanResult(mode == "scan", passed, 0, "/test", None, "first")
    second = guard.SkillScanResult(True, not passed, 0, "/test", None, "second")
    results = [] if mode == "import_error" else [first]
    results.append(second)
    later = []

    def publish(self, name, value):
        object.__setattr__(self, name, value)
        if self is dae and name == "_skill_scan_message" and not later:
            later.append(None)
            monkeypatch.setitem(sys.modules, guard.__name__, guard)
            later[0] = dae._ensure_skill_safety()

    monkeypatch.setattr(type(dae), "__setattr__", publish)
    if mode == "import_error":
        monkeypatch.setitem(sys.modules, guard.__name__, None)
    with patch.object(guard, "run_skill_scan", side_effect=results) as scan:
        assert dae._ensure_skill_safety() is passed
    assert later == [not passed]
    assert dae._skill_scan_ok is (not passed)  # Latest diagnostics are not this call's verdict.
    assert scan.call_count == len(results)


@pytest.mark.parametrize("available", [False, True])
@pytest.mark.parametrize("field,before,after", [
    ("required", False, True), ("required", True, False),
    ("enforced", False, True), ("enforced", True, False),
    ("max_severity", "medium", "low"), ("max_severity", "medium", "high"),
    (None, None, None),
])
def test_openclaw_dae_rejects_policy_drift(available, field, before, after):
    dae = _openclaw_dae()
    if field:
        setattr(dae, "_skill_scan_" + field, before)
    threshold = dae._skill_scan_max_severity

    def scan(**kwargs):
        assert kwargs["max_severity"] == threshold
        if field:
            setattr(dae, "_skill_scan_" + field, after)
        return guard.SkillScanResult(available, True, 0, "/test", None, "current")

    with patch.object(guard, "run_skill_scan", side_effect=scan) as call:
        assert dae._ensure_skill_safety() is (available and field is None)
    call.assert_called_once()
    if field:
        assert dae._skill_scan_message == "skill scan policy changed during scan"


@pytest.mark.parametrize("enforced", [False, True])
def test_openclaw_dae_enforced_mode_decides_failed_scan(enforced):
    dae = _openclaw_dae(enforced=enforced)
    with patch.object(guard, "run_skill_scan", return_value=_failed_scan_result("high severity")):
        assert dae._ensure_skill_safety(force=True) is (not enforced)


def test_openclaw_dae_process_downgrades_foundup_on_safety_failure():
    """FOUNDUP intent downgrades to CONVERSATION when skill safety fails."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE, IntentCategory

    dae = OpenClawDAE()
    dae._skill_scan_required = True
    dae._skill_scan_enforced = True

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

    with patch.object(guard, "run_skill_scan", return_value=_failed_scan_result("blocked by test")):
        gate_result = dae._ensure_skill_safety(force=False)
    assert gate_result is False
