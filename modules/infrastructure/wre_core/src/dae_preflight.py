#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WRE DAE Preflight - Shared health check for all DAE entry points.

This module provides a single function that any DAE can call at startup
to run the WRE dashboard health check with recursive enforcement.

Usage in any DAE launch.py:
    from modules.infrastructure.wre_core.src.dae_preflight import run_dae_preflight

    def main():
        if not run_dae_preflight("youtube_dae"):
            return
        # ... rest of DAE startup

Or as a decorator:
    from modules.infrastructure.wre_core.src.dae_preflight import preflight_guard

    @preflight_guard("social_media_dae")
    def run_social_media_dae():
        # ... DAE code here
"""

import os
import logging
import functools
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[4]


def _run_openclaw_security_preflight(dae_name: str, quiet: bool = False) -> bool:
    """
    Run OpenClaw security sentinel preflight.

    Env controls:
        OPENCLAW_SECURITY_PREFLIGHT=1            Enable preflight (default on)
        OPENCLAW_SECURITY_PREFLIGHT_ENFORCED=0   Block startup on failed check
        OPENCLAW_SECURITY_PREFLIGHT_FORCE=0      Bypass TTL cache and force re-scan
        OPENCLAW_24X7=1                          Apply strict defaults (enforced=1, force=1)
    """
    enabled = os.getenv("OPENCLAW_SECURITY_PREFLIGHT", "1") != "0"
    if not enabled:
        logger.debug(f"[{dae_name}] OpenClaw security preflight disabled")
        return True

    runtime_24x7 = os.getenv("OPENCLAW_24X7", "0") != "0"
    enforced_default = "1" if runtime_24x7 else "0"
    force_default = "1" if runtime_24x7 else "0"
    enforced = os.getenv("OPENCLAW_SECURITY_PREFLIGHT_ENFORCED", enforced_default) != "0"
    force = os.getenv("OPENCLAW_SECURITY_PREFLIGHT_FORCE", force_default) == "1"

    try:
        from modules.ai_intelligence.ai_overseer.src.openclaw_security_sentinel import (
            OpenClawSecuritySentinel,
        )

        sentinel = OpenClawSecuritySentinel(REPO_ROOT)
        status = sentinel.check(force=force) or {}
    except Exception as exc:
        logger.error(f"[{dae_name}] OpenClaw security preflight failed: {exc}")
        if enforced:
            print(f"[{dae_name}] SECURITY preflight FAILED: {exc}")
            return False
        if not quiet:
            print(f"[{dae_name}] SECURITY preflight warning: {exc}")
        return True

    passed = bool(status.get("passed", False))
    cache_state = "cached" if status.get("cached") else "fresh"
    message = str(status.get("message", "no message"))

    if not quiet or not passed:
        print(
            f"[{dae_name}] SECURITY preflight="
            f"{'PASS' if passed else 'FAIL'} ({cache_state}) - {message}"
        )

    if not passed and enforced:
        print(f"[{dae_name}] Startup blocked by OPENCLAW_SECURITY_PREFLIGHT_ENFORCED=1")
        return False
    return True


def dashboard_auto_enforce_enabled(*, interactive_menu: bool = False) -> bool:
    """Displaying a menu is advisory; action admission remains enforced by default."""
    explicit = os.getenv("WRE_DASHBOARD_AUTO_ENFORCE")
    return explicit != "0" if explicit is not None else not interactive_menu


def dashboard_readiness(health: dict, *, in_watch: bool, interactive_menu: bool = False) -> dict:
    """One policy for startup, DAE actions and the operator readiness display."""
    valid = isinstance(health, dict) and type(health.get("healthy")) is bool
    health = health if isinstance(health, dict) else {}
    alerts = health.get("alerts", [])
    if not isinstance(alerts, list) or any(
            not isinstance(alert, dict) or alert.get("severity") not in {"critical", "warning"}
            for alert in alerts):
        valid = False
        alerts = []
    coverage_unknown = health.get("insufficient_data") is True or bool(health.get("unknown_metrics"))
    if not alerts and health.get("healthy") is not True and not coverage_unknown:
        valid = False
    enabled = os.getenv("WRE_DASHBOARD_PREFLIGHT", "1") != "0"
    manual = os.getenv("WRE_DASHBOARD_PREFLIGHT_ENFORCED", "0") != "0"
    auto = dashboard_auto_enforce_enabled(interactive_menu=interactive_menu)
    auto_now = auto and not in_watch
    critical = sum(a.get("severity") == "critical" for a in alerts)
    warnings = sum(a.get("severity") == "warning" for a in alerts)
    unknown = coverage_unknown or not valid
    # Preserve cold-start admission: missing telemetry is not a measured failure.
    # A sampled critical still blocks even when other metric families are unknown.
    blocked = enabled and (manual or auto_now) and (critical > 0 or not valid)
    status = "UNKNOWN" if not valid else "FAIL" if alerts else ("UNKNOWN" if unknown else "PASS")
    readiness = ("UNKNOWN" if not valid else "DISABLED" if not enabled else "BLOCKED" if blocked else
                 "DEGRADED" if alerts else "UNKNOWN" if unknown else "READY")
    return dict(enabled=enabled, manual_enforced=manual, auto_enforce=auto,
                auto_enforced=auto_now, enforced=manual or auto_now,
                critical=critical, warnings=warnings, unknown=unknown,
                status=status, readiness=readiness, allowed=not blocked, evidence_valid=valid)


def run_dae_preflight(dae_name: str, quiet: bool = False) -> bool:
    """
    Run WRE dashboard preflight for any DAE.

    Args:
        dae_name: Name of the DAE (for logging)
        quiet: If True, suppress output on PASS (only show failures)

    Returns:
        True if startup should proceed, False if blocked

    Env controls (same as main.py):
        OPENCLAW_SECURITY_PREFLIGHT=1            Enable OpenClaw security preflight
        OPENCLAW_SECURITY_PREFLIGHT_ENFORCED=0   Block startup on security failure
        OPENCLAW_SECURITY_PREFLIGHT_FORCE=0      Force security re-scan (ignore TTL cache)
        OPENCLAW_24X7=1                          Strict default mode for unattended runtime
        WRE_DASHBOARD_PREFLIGHT=1           Enable preflight (default on)
        WRE_DASHBOARD_PREFLIGHT_ENFORCED=0  Manual override to force enforcement
        WRE_DASHBOARD_AUTO_ENFORCE=1        Recursive auto-enforcement
        WRE_DASHBOARD_MIN_SAMPLES=25        Min executions before alerting
        WRE_DASHBOARD_UNKNOWN_MODE=1        Treat insufficient data as UNKNOWN
    """
    if not _run_openclaw_security_preflight(dae_name, quiet=quiet):
        return False

    enabled = os.getenv("WRE_DASHBOARD_PREFLIGHT", "1") != "0"
    if not enabled:
        logger.debug(f"[{dae_name}] WRE preflight disabled")
        return True

    manual_enforced = os.getenv("WRE_DASHBOARD_PREFLIGHT_ENFORCED", "0") != "0"
    auto_enforce = dashboard_auto_enforce_enabled()

    try:
        from modules.infrastructure.wre_core.src.dashboard_alerts import (
            DashboardAlertMonitor,
            check_dashboard_health,
            print_dashboard_evidence,
        )

        monitor = DashboardAlertMonitor()
        health = check_dashboard_health()

        # Check for insufficient data first
        insufficient_data = health.get("insufficient_data", False)
        total_executions = health.get("total_executions", 0)
        min_samples = health.get("min_samples", 25)
        in_watch = monitor.is_in_watch_period()

        policy = dashboard_readiness(health, in_watch=in_watch)
        auto_enforced = policy["auto_enforced"]
        enforced = policy["enforced"]

        # Build status
        alerts = health.get("alerts", [])
        critical_count = sum(1 for a in alerts if a.get("severity") == "critical")
        warning_count = sum(1 for a in alerts if a.get("severity") == "warning")
        healthy = health.get("healthy", True)

        status = policy["status"]

        if in_watch:
            mode_label = "WATCH"
        elif auto_enforced:
            mode_label = "STABLE, ENFORCED"
        else:
            mode_label = "STABLE"

        # Only print on failure or if not quiet
        if not healthy or not quiet:
            print(
                f"[{dae_name}] WRE preflight={status} ({mode_label}) "
                f"critical={critical_count} warnings={warning_count}"
            )

        # Show alert details if any
        if alerts:
            for alert in alerts:
                severity = alert.get("severity", "info").upper()
                metric = alert.get("metric", "unknown")
                value = alert.get("value", 0)
                threshold = alert.get("threshold", 0)
                print(f"  [{severity}] {metric}: {value:.3f} (threshold: {threshold:.3f})")

        if insufficient_data or not quiet:
            print_dashboard_evidence(health)

        # Block on critical if enforced
        if not policy["allowed"]:
            enforce_source = "AUTO" if auto_enforced else "MANUAL"
            print(f"[{dae_name}] Startup blocked by {enforce_source} enforcement; readiness={status}")
            return False

        return True

    except ImportError as exc:
        logger.debug(f"[{dae_name}] WRE preflight not available: {exc}")
        print(f"[{dae_name}] WRE preflight=UNKNOWN; checker unavailable")
        return not (manual_enforced or auto_enforce)
    except Exception as exc:
        logger.error(f"[{dae_name}] WRE preflight failed: {exc}")
        if manual_enforced or auto_enforce:
            print(f"[{dae_name}] WRE preflight=UNKNOWN; startup blocked (checker error: {type(exc).__name__})")
            return False
        return True


def preflight_guard(dae_name: str, quiet: bool = True) -> Callable:
    """
    Decorator that runs WRE preflight before a DAE entry point.

    Usage:
        @preflight_guard("youtube_dae")
        def run_youtube_dae():
            # ... DAE code

    Args:
        dae_name: Name of the DAE for logging
        quiet: If True, suppress output on PASS

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not run_dae_preflight(dae_name, quiet=quiet):
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Convenience aliases for common DAEs
def youtube_preflight(quiet: bool = True) -> bool:
    """Preflight for YouTube DAE."""
    return run_dae_preflight("youtube_dae", quiet=quiet)


def social_media_preflight(quiet: bool = True) -> bool:
    """Preflight for Social Media DAE."""
    return run_dae_preflight("social_media_dae", quiet=quiet)


def holo_preflight(quiet: bool = True) -> bool:
    """Preflight for Holo DAE."""
    return run_dae_preflight("holo_dae", quiet=quiet)


def vision_preflight(quiet: bool = True) -> bool:
    """Preflight for Vision DAE."""
    return run_dae_preflight("vision_dae", quiet=quiet)
