#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Skill safety guard for OpenClaw workspace skills.

Runs Cisco Skill Scanner (`skill-scanner`) as a preflight safety check before
executing potentially mutating intents.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from modules.infrastructure.wre_core.src.skill_manifest_guard import (
    SkillManifestResult,
    verify_skill_manifest,
)
from modules.infrastructure.wre_core.src.skill_path_security import (
    absolute_unresolved,
    path_has_link_or_reparse,
)


@dataclass
class SkillScanResult:
    available: bool
    passed: bool
    exit_code: int
    skills_dir: str
    report_path: Optional[str]
    message: str
    stdout: str = ""
    stderr: str = ""
    manifest_available: bool = False
    manifest_passed: bool = False
    manifest_path: Optional[str] = None
    manifest_message: str = ""


_SEVERITY_ORDER = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def _normalize_severity_counts(raw: Any) -> Optional[dict[str, int]]:
    if not isinstance(raw, dict):
        return None
    counts: dict[str, int] = {}
    for severity, count in raw.items():
        normalized = str(severity).lower()
        if normalized not in _SEVERITY_ORDER:
            return None
        if type(count) is not int or count < 0:
            return None
        counts[normalized] = count
    return counts


def _report_severity_counts(payload: Any) -> Optional[dict[str, int]]:
    """Parse both Cisco single-skill and scan-all report schemas."""
    if not isinstance(payload, dict):
        return None
    if "summary" in payload:
        summary = payload.get("summary")
        if not isinstance(summary, dict):
            return None
        return _normalize_severity_counts(summary.get("findings_by_severity"))
    findings = payload.get("findings")
    expected = payload.get("findings_count")
    if not isinstance(findings, list) or type(expected) is not int:
        return None
    if expected < 0 or expected != len(findings):
        return None
    raw_counts: dict[str, int] = {}
    for finding in findings:
        if not isinstance(finding, dict) or not isinstance(finding.get("severity"), str):
            return None
        severity = finding["severity"].lower()
        raw_counts[severity] = raw_counts.get(severity, 0) + 1
    return _normalize_severity_counts(raw_counts)


def _threshold_exceeded(report_path: Path, max_severity: str) -> Optional[bool]:
    """Return True/False only for complete, recognized scanner evidence."""
    if path_has_link_or_reparse(report_path):
        return None
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    counts = _report_severity_counts(payload)
    allowed = _SEVERITY_ORDER.get(max_severity.lower())
    if counts is None or allowed is None:
        return None
    return any(
        _SEVERITY_ORDER[severity] >= allowed and count > 0
        for severity, count in counts.items()
    )


def _build_scanner_command(
    scanner_cmd: str,
    skills_dir: Path,
    report_path: Path,
) -> list[str]:
    """Select Cisco's exact-bundle or wardrobe scan contract."""
    skill_file = None
    if (skills_dir / "SKILLz.md").is_file():
        skill_file = "SKILLz.md"
    elif (skills_dir / "SKILL.md").is_file():
        skill_file = "SKILL.md"

    command = [scanner_cmd, "scan" if skill_file else "scan-all", str(skills_dir)]
    if skill_file == "SKILLz.md":
        command.extend(["--skill-file", skill_file])
    if skill_file is None:
        command.append("--recursive")
    command.extend(["--format", "json", "--output", str(report_path)])
    return command


def _configured_manifest_result(
    skills_dir: Path,
    *,
    required: Optional[bool],
    verify_signature: Optional[bool],
    allow_extra: Optional[bool],
    manifest_path: Optional[Path],
    hmac_key: Optional[str],
) -> SkillManifestResult:
    required = _env_flag(required, "OPENCLAW_SKILL_MANIFEST_REQUIRED", "1")
    verify_signature = _env_flag(
        verify_signature, "OPENCLAW_SKILL_MANIFEST_VERIFY_SIGNATURE", "0"
    )
    allow_extra = _env_flag(allow_extra, "OPENCLAW_SKILL_MANIFEST_ALLOW_EXTRA", "0")
    hmac_key = hmac_key or os.getenv("OPENCLAW_SKILL_MANIFEST_HMAC_KEY")
    if manifest_path is None:
        override = os.getenv("OPENCLAW_SKILL_MANIFEST_FILE")
        manifest_path = (
            absolute_unresolved(Path(override))
            if override
            else skills_dir / "SKILL_MANIFEST.json"
        )
    return verify_skill_manifest(
        skills_dir=skills_dir,
        manifest_path=manifest_path,
        required=required,
        verify_signature=verify_signature,
        hmac_key=hmac_key,
        allow_extra=allow_extra,
    )


def _env_flag(value: Optional[bool], name: str, default: str) -> bool:
    return value if value is not None else os.getenv(name, default).strip() == "1"


def _locate_scanner(skills_dir: Path) -> Optional[str]:
    scanner_cmd = os.getenv("OPENCLAW_SKILL_SCANNER_BIN") or shutil.which("skill-scanner")
    if scanner_cmd is not None:
        return scanner_cmd
    repo_root = skills_dir.parents[4] if len(skills_dir.parents) >= 5 else None
    if repo_root is None:
        return None
    candidates = (
        repo_root / ".venv" / "Scripts" / "skill-scanner.exe",
        repo_root / ".venv" / "bin" / "skill-scanner",
    )
    return next((str(path) for path in candidates if path.exists()), None)


def _result(
    *,
    skills_dir: Path,
    report_path: Path,
    manifest: SkillManifestResult,
    available: bool,
    passed: bool,
    exit_code: int,
    message: str,
    stdout: str = "",
    stderr: str = "",
) -> SkillScanResult:
    return SkillScanResult(
        available=available,
        passed=passed,
        exit_code=exit_code,
        skills_dir=str(skills_dir),
        report_path=str(report_path),
        message=message,
        stdout=stdout,
        stderr=stderr,
        manifest_available=manifest.available,
        manifest_passed=manifest.passed,
        manifest_path=manifest.manifest_path,
        manifest_message=manifest.message,
    )


def _invoke_scanner(
    command: list[str], report_path: Path, timeout_sec: int
) -> tuple[Optional[subprocess.CompletedProcess[str]], int, str]:
    try:
        report_path.unlink(missing_ok=True)
    except OSError:
        return None, 4, "skill scan report could not be reset"
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            env=_scanner_environment(report_path),
        )
    except subprocess.TimeoutExpired:
        return None, 124, "skill scan timed out"
    except OSError:
        return None, 126, "skill scanner process failed"
    return completed, completed.returncode, ""


def _scanner_environment(report_path: Path) -> dict[str, str]:
    """Pass only process-launch essentials, never ambient credentials."""
    allowed = (
        "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC",
        "LANG", "LC_ALL", "NO_COLOR",
    )
    environment = {name: os.environ[name] for name in allowed if name in os.environ}
    environment.update(
        TMP=str(report_path.parent),
        TEMP=str(report_path.parent),
        PYTHONIOENCODING="utf-8",
    )
    return environment


def _completed_scan_result(
    completed: subprocess.CompletedProcess[str],
    *,
    skills_dir: Path,
    report_path: Path,
    manifest: SkillManifestResult,
    max_severity: str,
) -> SkillScanResult:
    exceeds_threshold = _threshold_exceeded(report_path, max_severity)
    passed = completed.returncode == 0 and exceeds_threshold is False
    if exceeds_threshold is None:
        message = "skill scan report missing, malformed, or unsupported"
    elif passed:
        message = "skills passed safety scan"
    else:
        message = f"skill scan failed (exit={completed.returncode}) max_severity={max_severity}"
    return _result(
        skills_dir=skills_dir,
        report_path=report_path,
        manifest=manifest,
        available=True,
        passed=passed,
        exit_code=completed.returncode,
        message=message,
        stdout="",
        stderr="",
    )


def _scanner_preflight(
    *,
    skills_dir: Path,
    report_path: Path,
    manifest: SkillManifestResult,
    manifest_enforced: Optional[bool],
) -> tuple[Optional[str], Optional[SkillScanResult]]:
    enforced = _env_flag(manifest_enforced, "OPENCLAW_SKILL_MANIFEST_ENFORCED", "1")
    if not manifest.passed and enforced:
        failure = _result(
            skills_dir=skills_dir, report_path=report_path, manifest=manifest,
            available=True, passed=False, exit_code=3,
            message=f"manifest verification failed: {manifest.message}",
        )
        return None, failure
    scanner_cmd = _locate_scanner(skills_dir)
    if scanner_cmd is None:
        failure = _result(
            skills_dir=skills_dir, report_path=report_path, manifest=manifest,
            available=False, passed=False, exit_code=127,
            message="skill-scanner not installed (pip install cisco-ai-skill-scanner)",
        )
        return None, failure
    if not skills_dir.exists():
        failure = _result(
            skills_dir=skills_dir, report_path=report_path, manifest=manifest,
            available=True, passed=False, exit_code=2,
            message=f"skills directory not found: {skills_dir}",
        )
        return None, failure
    if path_has_link_or_reparse(report_path.parent):
        failure = _result(
            skills_dir=skills_dir, report_path=report_path, manifest=manifest,
            available=True, passed=False, exit_code=4,
            message="skill scan report directory is linked, reparsed, or inaccessible",
        )
        return None, failure
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        failure = _result(
            skills_dir=skills_dir, report_path=report_path, manifest=manifest,
            available=True, passed=False, exit_code=4,
            message="skill scan report directory is unavailable",
        )
        return None, failure
    return scanner_cmd, None


def run_skill_scan(
    skills_dir: Path,
    *,
    max_severity: str = "medium",
    timeout_sec: int = 90,
    report_dir: Optional[Path] = None,
    manifest_required: Optional[bool] = None,
    manifest_enforced: Optional[bool] = None,
    manifest_verify_signature: Optional[bool] = None,
    manifest_allow_extra: Optional[bool] = None,
    manifest_path: Optional[Path] = None,
    manifest_hmac_key: Optional[str] = None,
) -> SkillScanResult:
    """Run Cisco skill scanner with manifest and report evidence gates."""
    skills_dir = absolute_unresolved(skills_dir)
    report_dir = absolute_unresolved(report_dir or skills_dir.parent / "reports")
    report_path = report_dir / "openclaw_skill_scan_report.json"
    manifest = _configured_manifest_result(
        skills_dir,
        required=manifest_required,
        verify_signature=manifest_verify_signature,
        allow_extra=manifest_allow_extra,
        manifest_path=manifest_path,
        hmac_key=manifest_hmac_key,
    )
    scanner_cmd, failure = _scanner_preflight(
        skills_dir=skills_dir,
        report_path=report_path,
        manifest=manifest,
        manifest_enforced=manifest_enforced,
    )
    if failure is not None or scanner_cmd is None:
        return failure
    command = _build_scanner_command(scanner_cmd, skills_dir, report_path)
    completed, exit_code, process_error = _invoke_scanner(command, report_path, timeout_sec)
    if completed is None:
        return _result(
            skills_dir=skills_dir, report_path=report_path, manifest=manifest,
            available=True, passed=False, exit_code=exit_code, message=process_error,
        )
    return _completed_scan_result(
        completed,
        skills_dir=skills_dir,
        report_path=report_path,
        manifest=manifest,
        max_severity=max_severity,
    )
