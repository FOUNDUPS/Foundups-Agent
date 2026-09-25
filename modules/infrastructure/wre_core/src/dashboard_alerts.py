#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WRE Dashboard Regression Alerts

Post-release monitoring for 7-day watch period.
Alerts on metric regression vs production baselines.

Usage:
    python -m modules.infrastructure.wre_core.src.dashboard_alerts

Or programmatically:
    from modules.infrastructure.wre_core.src.dashboard_alerts import DashboardAlertMonitor
    monitor = DashboardAlertMonitor()
    alerts = monitor.check_all()
"""

import logging
import json
import math
import os
import re
import stat
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Minimum samples required before evaluating thresholds
# Below this, report UNKNOWN/INSUFFICIENT_DATA instead of CRITICAL
MIN_SAMPLES_DEFAULT = 25


@dataclass
class AlertThreshold:
    """Alert threshold configuration."""
    metric: str
    operator: str  # 'lt' (less than) or 'gt' (greater than)
    threshold: float
    severity: str  # 'warning' or 'critical'
    description: str


@dataclass
class Alert:
    """Triggered alert."""
    metric: str
    current_value: float
    threshold: float
    severity: str
    message: str
    timestamp: str


# Production baselines from gate evidence
PRODUCTION_BASELINES = {
    "tot_confidence_rate": 0.70,
    "codeact_success_rate": 0.90,
    "retrieval_coverage": 0.80,
    "variation_win_rate": 0.50,
    "fidelity_delta_baseline": 0.20,  # +20% from outcome gate
    "repeat_failure_rate_baseline": 0.30,  # Baseline for comparison
}

# Alert thresholds
ALERT_THRESHOLDS = [
    AlertThreshold(
        metric="tot_confidence_rate",
        operator="lt",
        threshold=0.50,
        severity="critical",
        description="ToT selection confidence below 50%"
    ),
    AlertThreshold(
        metric="tot_confidence_rate",
        operator="lt",
        threshold=0.60,
        severity="warning",
        description="ToT selection confidence below 60%"
    ),
    AlertThreshold(
        metric="codeact_success_rate",
        operator="lt",
        threshold=0.80,
        severity="critical",
        description="CodeAct success rate below 80%"
    ),
    AlertThreshold(
        metric="codeact_success_rate",
        operator="lt",
        threshold=0.85,
        severity="warning",
        description="CodeAct success rate below 85%"
    ),
    AlertThreshold(
        metric="retrieval_coverage",
        operator="lt",
        threshold=0.60,
        severity="critical",
        description="RAG retrieval coverage below 60%"
    ),
    AlertThreshold(
        metric="retrieval_coverage",
        operator="lt",
        threshold=0.70,
        severity="warning",
        description="RAG retrieval coverage below 70%"
    ),
    AlertThreshold(
        metric="variation_win_rate",
        operator="lt",
        threshold=0.30,
        severity="critical",
        description="TT-SI variation win rate below 30%"
    ),
    AlertThreshold(
        metric="variation_win_rate",
        operator="lt",
        threshold=0.40,
        severity="warning",
        description="TT-SI variation win rate below 40%"
    ),
    AlertThreshold(
        metric="codeact_gate_trigger_rate",
        operator="gt",
        threshold=0.10,
        severity="warning",
        description="CodeAct safety gate triggers above 10%"
    ),
    AlertThreshold(
        metric="codeact_gate_trigger_rate",
        operator="gt",
        threshold=0.20,
        severity="critical",
        description="CodeAct safety gate triggers above 20%"
    ),
]


class DashboardAlertMonitor:
    """
    Monitor WRE dashboard for metric regressions.

    Checks against production baselines and triggers alerts
    when thresholds are breached.
    """

    def __init__(self, pattern_memory=None):
        """
        Initialize monitor.

        Args:
            pattern_memory: Optional PatternMemory instance.
                           If None, will create one.

        Env controls:
            WRE_DASHBOARD_MIN_SAMPLES: Minimum executions before alerting (default 25)
            WRE_DASHBOARD_UNKNOWN_MODE: If "1", treat insufficient data as UNKNOWN (default on)
        """
        self.pattern_memory = pattern_memory
        self.thresholds = ALERT_THRESHOLDS
        self.baselines = PRODUCTION_BASELINES
        self.watch_period_start = datetime(2026, 2, 24)
        self.watch_period_end = self.watch_period_start + timedelta(days=7)

        # Minimum sample threshold
        self.min_samples = int(os.getenv("WRE_DASHBOARD_MIN_SAMPLES", str(MIN_SAMPLES_DEFAULT)))
        self.unknown_mode = os.getenv("WRE_DASHBOARD_UNKNOWN_MODE", "1") != "0"

    def _get_memory(self):
        """Lazy-load pattern memory."""
        if self.pattern_memory is None:
            from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory
            self.pattern_memory = PatternMemory()
        return self.pattern_memory

    def get_dashboard(self) -> Dict:
        """Get current dashboard metrics."""
        memory = self._get_memory()
        return memory.get_telemetry_dashboard()

    def get_total_executions(self, dashboard: Optional[Dict] = None) -> int:
        """Get total skill executions from dashboard."""
        if dashboard is None:
            dashboard = self.get_dashboard()
        return int(dashboard.get("total_executions", 0))

    def has_sufficient_data(self, dashboard: Optional[Dict] = None) -> bool:
        """Check if we have enough data to evaluate thresholds."""
        return self.get_total_executions(dashboard) >= self.min_samples

    def check_threshold(self, metric: str, value: float, threshold: AlertThreshold) -> Optional[Alert]:
        """Check if metric breaches threshold."""
        breached = False

        if threshold.operator == "lt" and value < threshold.threshold:
            breached = True
        elif threshold.operator == "gt" and value > threshold.threshold:
            breached = True

        if breached:
            return Alert(
                metric=metric,
                current_value=value,
                threshold=threshold.threshold,
                severity=threshold.severity,
                message=threshold.description,
                timestamp=datetime.now().isoformat()
            )
        return None

    def check_all(self, skip_if_insufficient: bool = True) -> List[Alert]:
        """
        Check all metrics against thresholds.

        Args:
            skip_if_insufficient: If True and unknown_mode enabled, skip threshold
                                  evaluation when below min_samples (default True)

        Returns:
            List of triggered alerts (empty if healthy or insufficient data)
        """
        alerts = []
        dashboard = self.get_dashboard()

        # Check for insufficient data - don't alert on zero-data startup
        if skip_if_insufficient and self.unknown_mode:
            if not self.has_sufficient_data(dashboard):
                logger.debug(
                    f"[WRE-DASHBOARD] Insufficient data: "
                    f"{self.get_total_executions(dashboard)}/{self.min_samples} samples"
                )
                return []  # No alerts when data is insufficient

        # Add computed metrics
        codeact_total = dashboard.get("codeact_executions", 0)
        codeact_triggers = dashboard.get("codeact_gate_triggers", 0)
        if codeact_total > 0:
            dashboard["codeact_gate_trigger_rate"] = codeact_triggers / codeact_total
        else:
            dashboard["codeact_gate_trigger_rate"] = 0.0

        # Check each threshold
        for threshold in self.thresholds:
            if threshold.metric in dashboard:
                value = dashboard[threshold.metric]
                alert = self.check_threshold(threshold.metric, value, threshold)
                if alert:
                    alerts.append(alert)

        # Deduplicate: keep only highest severity per metric
        deduped = {}
        for alert in alerts:
            key = alert.metric
            if key not in deduped:
                deduped[key] = alert
            elif alert.severity == "critical" and deduped[key].severity == "warning":
                deduped[key] = alert

        return list(deduped.values())

    def is_in_watch_period(self) -> bool:
        """Check if currently in 7-day watch period."""
        now = datetime.now()
        return self.watch_period_start <= now <= self.watch_period_end

    def format_alerts(self, alerts: List[Alert]) -> str:
        """Format alerts for display."""
        if not alerts:
            return "[OK] All metrics healthy"

        lines = []
        critical = [a for a in alerts if a.severity == "critical"]
        warnings = [a for a in alerts if a.severity == "warning"]

        if critical:
            lines.append(f"[CRITICAL] {len(critical)} critical alert(s):")
            for a in critical:
                lines.append(f"  - {a.metric}: {a.current_value:.3f} (threshold: {a.threshold:.3f})")
                lines.append(f"    {a.message}")

        if warnings:
            lines.append(f"[WARNING] {len(warnings)} warning(s):")
            for a in warnings:
                lines.append(f"  - {a.metric}: {a.current_value:.3f} (threshold: {a.threshold:.3f})")
                lines.append(f"    {a.message}")

        return "\n".join(lines)

    def run_check(self, verbose: bool = True) -> bool:
        """
        Run full alert check.

        Args:
            verbose: Print results to stdout

        Returns:
            True if all healthy, False if any alerts
        """
        alerts = self.check_all()

        if verbose:
            print("=" * 60)
            print("WRE Dashboard Alert Check")
            print(f"Timestamp: {datetime.now().isoformat()}")
            print(f"Watch period: {self.watch_period_start.date()} to {self.watch_period_end.date()}")
            print(f"In watch period: {self.is_in_watch_period()}")
            print("=" * 60)
            print(self.format_alerts(alerts))
            print("=" * 60)

        return len(alerts) == 0


def check_dashboard_health() -> Dict:
    """
    Quick health check function.

    Returns:
        {
            "healthy": bool,
            "alerts": [...],
            "dashboard": {...},
            "insufficient_data": bool,
            "total_executions": int,
            "min_samples": int,
            "timestamp": str
        }
    """
    monitor = DashboardAlertMonitor()
    dashboard = monitor.get_dashboard()
    total_executions = monitor.get_total_executions(dashboard)
    insufficient_data = not monitor.has_sufficient_data(dashboard)

    # check_all will return empty list if insufficient data
    alerts = monitor.check_all()

    return {
        "healthy": len(alerts) == 0,
        "alerts": [
            {
                "metric": a.metric,
                "value": a.current_value,
                "threshold": a.threshold,
                "severity": a.severity,
                "message": a.message
            }
            for a in alerts
        ],
        "dashboard": dashboard,
        "insufficient_data": insufficient_data,
        "total_executions": total_executions,
        "min_samples": monitor.min_samples,
        "timestamp": datetime.now().isoformat()
    }


def _local_research_report_path(value):
    """Check the selected/embedded path lexically, never resolve a network path."""
    text = os.fspath(value)
    if not isinstance(text, str) or text.startswith(("\\\\", "//")):
        raise ValueError("local path required")
    path = Path(text)
    if (not path.is_absolute() or path.drive.startswith("\\\\")
            or ".." in path.parts or path.name != "report.json"
            or not re.fullmatch(r"invocation-[A-Za-z0-9_-]+", path.parent.name)):
        raise ValueError("final invocation report required")
    return path


def _research_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate report field")
        result[key] = value
    return result


def _research_report_numbers(report):
    """Check only displayed accounting, not economic validity or authority."""
    keys = ("attempts_requested", "attempts_started", "attempts_finished",
            "iterations_run", "baseline_evaluations", "candidate_evaluations")
    if any(type(report.get(k)) is not int or report[k] < 0 for k in keys):
        raise ValueError("invalid counters")
    attempts = report["attempts_requested"]
    if any(report[k] != attempts for k in keys[1:4]) or report["baseline_evaluations"] != 1:
        raise ValueError("inconsistent counters")
    counts = dict.fromkeys(("accepted", "rejected", "crashed", "failed_validation", "no_proposal"), 0)
    history = report.get("history")
    if not isinstance(history, list) or len(history) != attempts:
        raise ValueError("inconsistent history")
    for iteration, row in enumerate(history, 1):
        if (not isinstance(row, dict) or type(row.get("iteration")) is not int
                or row["iteration"] != iteration or row.get("status") not in counts):
            raise ValueError("invalid outcome")
        counts[row["status"]] += 1
    supplied = report.get("outcome_counts")
    if (not isinstance(supplied, dict) or any(type(v) is not int for v in supplied.values())
            or supplied != counts or report["candidate_evaluations"] != attempts - counts["no_proposal"]):
        raise ValueError("inconsistent outcomes")
    metrics = [report.get(k) for k in ("baseline", "optimized")]
    if any(not isinstance(m, dict) for m in metrics):
        raise ValueError("missing metrics")
    baseline, best = (m.get("fitness") for m in metrics)
    improvement = report.get("improvement")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in (baseline, best, improvement)):
        raise ValueError("invalid metrics")
    if (improvement < 0 or improvement != best - baseline
            or (counts["accepted"] > 0) != (improvement > 0)):
        raise ValueError("inconsistent improvement")

    rsi = report.get("rsi_measurements")
    if not isinstance(rsi, dict):
        raise ValueError("missing RSI measurements")
    required_rsi = {
        "schema": "wre_rsi_measurements.v1",
        "verification_signal_class": "execution_feedback",
        "research_direction_judgment": "human_not_substituted",
        "verification_signal_independent": False,
        "held_out_evaluation": False,
        "production_rsi_eligible": False,
        "baseline_fitness": baseline,
        "best_fitness": best,
        "absolute_gain": improvement,
        "candidate_evaluations": report["candidate_evaluations"],
        "accepted_candidates": counts["accepted"],
        "rejected_candidates": counts["rejected"] + counts["failed_validation"] + counts["crashed"],
    }
    if any(rsi.get(k) != v for k, v in required_rsi.items()):
        raise ValueError("inconsistent RSI measurements")
    hierarchy = rsi.get("verification_hierarchy_weak_to_strong")
    if hierarchy != ["intrinsic_signal", "learned_judge", "execution_feedback", "formal_verifier"]:
        raise ValueError("invalid verification hierarchy")
    relative_gain = rsi.get("relative_gain")
    expected_relative = improvement / abs(baseline) if baseline != 0 else None
    if relative_gain != expected_relative:
        raise ValueError("inconsistent relative gain")
    if any(rsi.get(k) is not None for k in (
            "independently_verified", "retained_improvements", "resource_usage",
            "activation_rollback_verified", "successive_generation_gain")):
        raise ValueError("self-asserted RSI authority")

    return {
        "attempts": attempts,
        "outcome_counts": counts,
        "improvement": improvement,
        "verification_signal_class": rsi["verification_signal_class"],
        "rsi_absolute_gain": rsi["absolute_gain"],
        "rsi_relative_gain": relative_gain,
        "production_rsi_eligible": False,
    }


def read_research_report_summary(report_path, expected_baseline_sha256, *, max_age_seconds=86400):
    """Read one explicitly selected local diagnostic; no execution/retention grant.

    Caller supplies a trusted local regular-file location. Size is bounded; local
    filesystem latency and hostile path replacement are not sandboxed. File mtime
    is an unauthenticated age hint, never proof of current execution or benefit.
    """
    result = {"state": "unknown", "reason": "not_configured", "file_age_seconds": None,
              "independently_verified": None, "retained_improvements": None, "resource_usage": None,
              "verification_signal_class": None, "rsi_absolute_gain": None,
              "rsi_relative_gain": None, "production_rsi_eligible": None}
    if not report_path:
        return result
    try:
        result["reason"] = "invalid_selection"
        if (not isinstance(expected_baseline_sha256, str)
                or not re.fullmatch(r"[0-9a-f]{64}", expected_baseline_sha256)
                or type(max_age_seconds) not in (int, float)
                or not math.isfinite(max_age_seconds) or max_age_seconds <= 0):
            return result
        path = _local_research_report_path(report_path)
        result["reason"] = "unavailable"
        if not stat.S_ISREG(path.lstat().st_mode):
            return result
        with path.open("rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                return result
            data = stream.read(1024 * 1024 + 1)
        result["reason"] = "invalid_report"
        if len(data) > 1024 * 1024:
            return result
        report = json.loads(data.decode("utf-8"), object_pairs_hook=_research_json_object)
        if not isinstance(report, dict) or not _research_report_matches(report, path, expected_baseline_sha256):
            return result
        numbers = _research_report_numbers(report)
        age = datetime.now().timestamp() - info.st_mtime
        if not math.isfinite(age) or not 0 <= age <= max_age_seconds:
            result["reason"] = "stale_file"
            return result
        result.update(numbers, state="unverified_diagnostic", reason="reported_completed", file_age_seconds=age)
    except (OSError, ValueError, TypeError, OverflowError, RecursionError):
        pass
    return result


def _research_report_matches(report, path, expected_digest):
    required = {"schema": "wre_auto_research_report.v1", "status": "completed",
                "stop_reason": "attempt_limit", "cleanup": "restored", "failure": None,
                "cleanup_failure": None, "baseline_input_sha256": expected_digest,
                "invocation_id": path.parent.name}
    if any(k not in report or report[k] != v for k, v in required.items()) or report.get("dry_run") is not True:
        return False
    embedded = _local_research_report_path(report.get("report_path"))
    return os.path.normcase(str(embedded)) == os.path.normcase(str(path))


def print_research_report_summary():
    """Advisory startup output; never let a diagnostic failure change health gates."""
    try:
        summary = read_research_report_summary(
            os.getenv("WRE_RESEARCH_REPORT_PATH"), os.getenv("WRE_RESEARCH_BASELINE_SHA256"))
        if summary["state"] == "unverified_diagnostic":
            counts = summary["outcome_counts"]
            detail = (f"attempts={summary['attempts']} accepted={counts['accepted']} "
                      f"crashed={counts['crashed']} invalid={counts['failed_validation']} "
                      f"signal={summary['verification_signal_class']} "
                      f"reported_fitness_delta={summary['rsi_absolute_gain']:.6g} "
                      f"production_rsi_eligible={str(summary['production_rsi_eligible']).lower()} "
                      f"file_age_seconds={summary['file_age_seconds']:.0f}")
        else:
            detail = "reason=" + summary["reason"]
        print(f"[WRE-RESEARCH] {summary['state']} {detail} "
              "source=explicit_selection baseline=caller_expected "
              "execution_freshness=unknown verified=unknown retained=unknown resource_usage=unknown")
    except Exception:
        print("[WRE-RESEARCH] unknown reason=diagnostic_unavailable")


# CLI entry point
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    monitor = DashboardAlertMonitor()
    healthy = monitor.run_check(verbose=True)

    sys.exit(0 if healthy else 1)
