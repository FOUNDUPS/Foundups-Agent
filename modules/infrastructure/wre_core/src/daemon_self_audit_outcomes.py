"""Local projections of legacy self-audit results, without effect authority.

SQLite verification is a structural diagnostic. Its legacy boolean does not
uniformly represent invocation or completion; only its exact positive tuple
qualifies diagnostic success. Existing non-SQLite markers retain legacy meaning.
"""

from __future__ import annotations


def classify_fix_outcome(fix_name: str, attempted: bool, result: str) -> str:
    if fix_name == "verify_dae_event_store":
        if attempted is True and result == "event_store_verified":
            return "diagnostic_success"
        return "diagnostic"
    if not attempted:
        return "not_attempted"
    markers = ("start_command_dispatched", "microphone_diagnostics_written")
    return "success" if any(marker in result for marker in markers) else "failure"


def record_fix_feedback(
    fix_stats: dict,
    fix_name: str,
    attempted: bool,
    result: str,
    *,
    attempted_at: float | None,
) -> None:
    stats = fix_stats.setdefault(
        fix_name,
        {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
            "last_result": "",
            "last_attempt_at": 0.0,
        },
    )
    outcome = classify_fix_outcome(fix_name, attempted, result)
    if attempted:
        if outcome in {"success", "failure"}:
            stats["attempts"] = int(stats.get("attempts", 0)) + 1
            field = "successes" if outcome == "success" else "failures"
            stats[field] = int(stats.get(field, 0)) + 1
        elif outcome == "diagnostic_success":
            stats["diagnostic_successes"] = int(stats.get("diagnostic_successes", 0)) + 1
        stats["last_attempt_at"] = attempted_at
    stats["last_result"] = result
