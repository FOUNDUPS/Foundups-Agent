"""OpenClaw status/reporting helpers for operator-facing surfaces."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("openclaw_dae")


def build_connect_wre_status(dae: Any, verbose: bool = False) -> str:
    """Deterministic Connect-WRE status response for operator prompts."""
    preflight_ok = False
    health: Dict[str, Any] = {}
    in_watch: Optional[bool] = None
    issues: List[str] = []

    try:
        from modules.infrastructure.wre_core.src.dae_preflight import run_dae_preflight

        preflight_ok = bool(run_dae_preflight("connect_wre", quiet=True))
    except Exception as exc:
        issues.append(f"preflight_unavailable:{type(exc).__name__}")

    try:
        from modules.infrastructure.wre_core.src.dashboard_alerts import (
            DashboardAlertMonitor,
            check_dashboard_health,
        )

        monitor = DashboardAlertMonitor()
        in_watch = monitor.is_in_watch_period()
        health = check_dashboard_health() or {}
    except Exception as exc:
        issues.append(f"dashboard_unavailable:{type(exc).__name__}")

    enabled = os.getenv("WRE_DASHBOARD_PREFLIGHT", "1") != "0"
    manual_enforced = os.getenv("WRE_DASHBOARD_PREFLIGHT_ENFORCED", "0") != "0"
    auto_enforce = os.getenv("WRE_DASHBOARD_AUTO_ENFORCE", "1") != "0"
    insufficient_data = bool(health.get("insufficient_data", False))
    total_executions = int(health.get("total_executions", 0))
    min_samples = int(
        health.get("min_samples", int(os.getenv("WRE_DASHBOARD_MIN_SAMPLES", "25")))
    )
    alerts = health.get("alerts", []) if isinstance(health.get("alerts"), list) else []
    critical = sum(1 for alert in alerts if alert.get("severity") == "critical")
    warnings = sum(1 for alert in alerts if alert.get("severity") == "warning")

    auto_enforced = bool(auto_enforce and in_watch is not None and not in_watch and not insufficient_data)
    effective_enforced = bool(manual_enforced or auto_enforced)

    if not enabled:
        readiness = "DISABLED"
    elif insufficient_data:
        readiness = "INSUFFICIENT_DATA"
    elif critical > 0 and effective_enforced:
        readiness = "BLOCKED"
    elif critical > 0:
        readiness = "DEGRADED"
    else:
        readiness = "READY"

    connection_state = "CONNECTED" if preflight_ok and not issues else "PARTIAL"
    mode = "WATCH" if in_watch else "STABLE"
    if in_watch is None:
        mode = "UNKNOWN"

    response = (
        "0102: connect_wre "
        f"connection={connection_state} "
        f"readiness={readiness} "
        f"mode={mode} "
        f"samples={total_executions}/{min_samples} "
        f"critical={critical} warnings={warnings} "
        f"enforced={'ON' if effective_enforced else 'OFF'}"
    )
    if issues:
        if verbose:
            response += f" issues={';'.join(issues)}"
        else:
            response += " (say 'connect wre details' for diagnostics)"
    return response


def push_status(dae: Any, message: str, to_discord: bool = True) -> bool:
    """Push status update via AI Overseer or direct Discord fallback."""
    if not to_discord:
        return True

    if dae.overseer and hasattr(dae.overseer, "push_status"):
        try:
            result = dae.overseer.push_status(message, to_discord=True, to_chat=False)
            return result.get("discord", False)
        except Exception as exc:
            logger.warning("[OPENCLAW-DAE] Push status failed: %s", exc)

    try:
        from modules.communication.livechat.src.discord_status_pusher import (
            push_status as direct_push,
        )

        return direct_push(message, to_discord=True, to_log=False)
    except ImportError:
        logger.debug("[OPENCLAW-DAE] Discord pusher not available")
        return True
