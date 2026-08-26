"""Production Skillz metadata, content, manifest, and scanner admission."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any, MutableMapping

from modules.infrastructure.wre_core.src.registered_skill_executor import (
    skill_bundle_fingerprint,
    validate_runtime_skill_admission,
)

try:
    from modules.communication.moltbot_bridge.src.skill_safety_guard import (
        run_skill_scan,
    )

    SKILL_SCANNER_AVAILABLE = True
except ImportError:
    run_skill_scan = None
    SKILL_SCANNER_AVAILABLE = False


def ensure_runtime_skill_safety(
    *,
    skills_loader: Any,
    skill_name: str,
    repo_root: Path,
    cache: MutableMapping[str, dict[str, Any]],
    required: bool,
    enforced: bool,
    always_scan: bool,
    ttl_seconds: int,
    max_severity: str,
    force: bool = False,
) -> tuple[bool, str]:
    """Admit exact production metadata and a content-bound scanner result."""
    if required is not True or enforced is not True:
        return False, "production Skillz scanner must be required and enforced"
    admitted, message = validate_runtime_skill_admission(
        skills_loader=skills_loader, skill_name=skill_name
    )
    if not admitted:
        return False, message
    try:
        skill_file = skills_loader.resolve_skill_file(skill_name)
        scan_dir = skill_file.parent.resolve()
        fingerprint = skill_bundle_fingerprint(scan_dir)
    except Exception:
        return False, "registered production Skillz source is unavailable"

    cache_key = f"{scan_dir}:{fingerprint}"
    now = time.time()
    cached = cache.get(cache_key)
    if _cache_is_current(cached, now, ttl_seconds, always_scan, force):
        message = cached.get("message")
        stable_message = message if isinstance(message, str) else "cached scan failed"
        return cached.get("ok") is True, stable_message

    return _scan_and_cache(
        scan_dir=scan_dir,
        repo_root=repo_root,
        fingerprint=fingerprint,
        cache=cache,
        cache_key=cache_key,
        checked_at=now,
        required=required,
        enforced=enforced,
        max_severity=max_severity,
    )


def _scan_and_cache(
    *, scan_dir: Path, repo_root: Path, fingerprint: str,
    cache: MutableMapping[str, dict[str, Any]], cache_key: str,
    checked_at: float, required: bool, enforced: bool, max_severity: str,
) -> tuple[bool, str]:
    ok, scan_message = _scan_bundle(
        scan_dir=scan_dir,
        report_dir=_scan_report_dir(repo_root, fingerprint),
        required=required,
        enforced=enforced,
        max_severity=max_severity,
    )
    if ok:
        try:
            if skill_bundle_fingerprint(scan_dir) != fingerprint:
                ok = False
                scan_message = "production Skillz bundle changed during safety scan"
        except Exception:
            ok = False
            scan_message = "production Skillz bundle became unavailable after safety scan"
    cache_prefix = f"{scan_dir}:"
    for stale_key in [key for key in cache if key.startswith(cache_prefix)]:
        cache.pop(stale_key, None)
    cache[cache_key] = {
        "checked_at": checked_at, "ok": ok, "message": scan_message
    }
    return ok, scan_message


def _scan_report_dir(repo_root: Path, fingerprint: str) -> Path:
    return (
        repo_root
        / "modules/infrastructure/wre_core/reports/skill_scans"
        / fingerprint
    )


def admitted_runtime_fingerprint(
    *, skills_loader: Any, skill_name: str, cache: MutableMapping[str, dict[str, Any]]
) -> str | None:
    """Return the exact current fingerprint only when its scan cache passed."""
    try:
        scan_dir = skills_loader.resolve_skill_file(skill_name).parent.resolve()
        fingerprint = skill_bundle_fingerprint(scan_dir)
    except Exception:
        return None
    cached = cache.get(f"{scan_dir}:{fingerprint}")
    return fingerprint if isinstance(cached, dict) and cached.get("ok") is True else None


def _bundle_fingerprint(skill_dir: Path) -> str:
    """Compatibility alias for the shared canonical bundle fingerprint."""
    return skill_bundle_fingerprint(skill_dir)


def _cache_is_current(
    cached: Any,
    now: float,
    ttl_seconds: int,
    always_scan: bool,
    force: bool,
) -> bool:
    if not isinstance(cached, dict) or force or always_scan:
        return False
    try:
        checked_at = float(cached.get("checked_at", 0))
    except (TypeError, ValueError):
        return False
    age = now - checked_at
    return ttl_seconds >= 0 and 0 <= age < ttl_seconds


def _scan_bundle(
    *,
    scan_dir: Path,
    report_dir: Path,
    required: bool,
    enforced: bool,
    max_severity: str,
) -> tuple[bool, str]:
    if not SKILL_SCANNER_AVAILABLE or run_skill_scan is None:
        return (not required), "production Skillz scanner is unavailable"
    result = run_skill_scan(
        skills_dir=scan_dir,
        max_severity=max_severity,
        report_dir=report_dir,
        manifest_required=True,
        manifest_enforced=True,
    )
    if getattr(result, "manifest_passed", False) is not True:
        return False, "production Skillz manifest verification failed"
    ok = (not required) if getattr(result, "available", False) is not True else (
        getattr(result, "passed", False) is True or not enforced
    )
    return ok, "production Skillz supply-chain scan passed" if ok else "production Skillz supply-chain scan failed"
