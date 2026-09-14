"""Production Skillz metadata, content, manifest, and scanner admission."""

from __future__ import annotations

from pathlib import Path
import threading
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


_CACHE_LOCK = threading.RLock()
_MAX_CACHE_ENTRIES = 128


def ensure_runtime_skill_safety(
    *, skills_loader: Any, skill_name: str, repo_root: Path,
    cache: MutableMapping[str, dict[str, Any]],
    required: bool, enforced: bool, always_scan: bool,
    ttl_seconds: int, max_severity: str, force: bool = False,
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

    cache_key = f"{scan_dir}:{fingerprint}:{max_severity}"
    now = time.time()
    with _CACHE_LOCK:
        cached = cache.get(cache_key)
        if _cache_is_current(cached, now, ttl_seconds, always_scan, force):
            message = cached.get("message")
            stable_message = message if isinstance(message, str) else "cached scan failed"
            return cached.get("ok") is True, stable_message
        reservation = _reserve_scan(cache, cache_key, f"{scan_dir}:")
    if reservation is None:
        return False, "production Skillz scan pending or admission cache at capacity"

    return _scan_and_cache(
        scan_dir=scan_dir,
        repo_root=repo_root,
        fingerprint=fingerprint,
        cache=cache,
        cache_key=cache_key,
        reservation=reservation,
        checked_at=now,
        required=required,
        enforced=enforced,
        max_severity=max_severity,
    )


def _reserve_scan(cache: MutableMapping, cache_key: str, prefix: str) -> dict | None:
    """Reserve under _CACHE_LOCK; never evict another active scanner."""
    def pending(value):
        return isinstance(value, dict) and value.get("_pending") is True
    if any(key.startswith(prefix) and pending(value) for key, value in cache.items()):
        return None
    for key in [key for key in cache if key.startswith(prefix)]:
        cache.pop(key, None)
    while len(cache) >= _MAX_CACHE_ENTRIES:
        oldest = next((key for key, value in cache.items() if not pending(value)), None)
        if oldest is None:
            return None
        cache.pop(oldest, None)
    reservation = {"_pending": True}
    cache[cache_key] = reservation
    return reservation


def _scan_and_cache(
    *, scan_dir: Path, repo_root: Path, fingerprint: str,
    cache: MutableMapping[str, dict[str, Any]], cache_key: str,
    reservation: dict,
    checked_at: float, required: bool, enforced: bool, max_severity: str,
) -> tuple[bool, str]:
    try:
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
        with _CACHE_LOCK:
            if cache.get(cache_key) is not reservation:
                return False, "production Skillz scan reservation is no longer current"
            cache[cache_key] = {
                "checked_at": checked_at, "ok": ok, "message": scan_message
            }
        return ok, scan_message
    finally:
        with _CACHE_LOCK:
            if cache.get(cache_key) is reservation:
                cache.pop(cache_key, None)


def _scan_report_dir(repo_root: Path, fingerprint: str) -> Path:
    return (
        repo_root
        / "modules/infrastructure/wre_core/reports/skill_scans"
        / fingerprint
    )


def admitted_runtime_fingerprint(
    *, skills_loader: Any, skill_name: str, cache: MutableMapping[str, dict[str, Any]],
    max_severity: str = "medium",
) -> str | None:
    """Read matching policy/content after ensure_runtime_skill_safety succeeds."""
    try:
        scan_dir = skills_loader.resolve_skill_file(skill_name).parent.resolve()
        fingerprint = skill_bundle_fingerprint(scan_dir)
    except Exception:
        return None
    with _CACHE_LOCK:
        cached = cache.get(f"{scan_dir}:{fingerprint}:{max_severity}")
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
    if not isinstance(cached, dict) or cached.get("_pending") is True or force or always_scan:
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
