#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io

"""
# === UTF-8 ENFORCEMENT (WSP 90) ===
# Prevent UnicodeEncodeError on Windows systems
# Only apply when running as main script, not during import
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===

WRE Monitor Dashboard
Real-time display of system performance and improvements

0102 Architect: Run this alongside YouTube DAE to monitor performance
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from modules.infrastructure.wre_core.wre_monitor import get_monitor  # type: ignore


def clear_screen():
    """Clear console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def format_time(seconds):
    """Format seconds to human readable"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def load_registry() -> dict:
    """Load skills registry (permissions + metadata)"""
    registry_path = project_root / "modules" / "infrastructure" / "wre_core" / "skillz" / "skills_registry.json"
    if not registry_path.exists():
        return {"skills": {}}
    try:
        return json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"skills": {}}


def read_last_metric(path: Path) -> dict:
    """Read the last JSON line from metrics file."""
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in reversed(lines):
            line = line.strip()
            if line:
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
    except Exception:
        return {}
    return {}


def load_skill_snapshot(metrics_dir: Path, skill_name: str) -> dict:
    """Aggregate latest metrics for a given skill."""
    fidelity = read_last_metric(metrics_dir / f"{skill_name}_fidelity.json")
    outcome = read_last_metric(metrics_dir / f"{skill_name}_outcomes.json")
    performance = read_last_metric(metrics_dir / f"{skill_name}_performance.json")
    promotion = read_last_metric(metrics_dir / f"{skill_name}_promotion_log.json")

    last_timestamp = max(
        [
            fidelity.get("timestamp"),
            outcome.get("timestamp"),
            performance.get("timestamp"),
            promotion.get("timestamp"),
        ],
        default=None,
    )

    return {
        "skill": skill_name,
        "last_run": last_timestamp,
        "pattern_fidelity": fidelity.get("pattern_fidelity"),
        "patterns_followed": fidelity.get("patterns_followed"),
        "patterns_missed": fidelity.get("patterns_missed"),
        "outcome_correct": outcome.get("correct"),
        "outcome_confidence": outcome.get("confidence"),
        "last_decision": outcome.get("decision"),
        "execution_time_ms": performance.get("execution_time_ms"),
        "exception": performance.get("exception_occurred"),
        "promotion_event": promotion.get("event_type"),
    }


def _verification_status(snapshot: dict) -> str:
    """Summarize verification status for display."""
    decision = snapshot.get("last_decision")
    if decision == "verify_unicode_patch":
        return "verified" if snapshot.get("outcome_correct") else "failed"
    if decision:
        return "ok" if snapshot.get("outcome_correct") else "error"
    return "pending"


def format_time_ago(timestamp: float | None) -> str:
    if not timestamp:
        return "N/A"
    delta = time.time() - timestamp
    if delta < 60:
        return f"{delta:.0f}s ago"
    if delta < 3600:
        return f"{delta/60:.1f}m ago"
    return f"{delta/3600:.1f}h ago"


def _activity_indicators(status: dict) -> list[str]:
    """Build indicators without treating absent telemetry as measured data."""
    indicators = []
    runtime = status["runtime_minutes"] + 0.01
    if status["messages_processed"] > 0:
        message_rate = status["messages_processed"] / runtime
        indicators.append("[HIGH ACTIVITY]" if message_rate > 5 else "[ACTIVE]" if message_rate > 1 else "[LOW ACTIVITY]")
    if status["learning_events"] > 0:
        learning_rate = status["learning_events"] / runtime
        if learning_rate > 1:
            indicators.append("[LEARNING FAST]")
        elif learning_rate > 0.2:
            indicators.append("[LEARNING]")
    efficiency = status.get("token_efficiency")
    if isinstance(efficiency, (int, float)):
        if efficiency > 90:
            indicators.append("[OPTIMAL]")
        elif efficiency > 80:
            indicators.append("[EFFICIENT]")
    return indicators


def display_dashboard(filter_skill: str | None, refresh_interval: float):
    """Display real-time dashboard"""
    monitor = get_monitor()
    metrics_dir = project_root / "modules" / "infrastructure" / "wre_core" / "recursive_improvement" / "metrics"
    registry = load_registry()
    registry_skills = registry.get("skills", {})
    
    while True:
        try:
            clear_screen()
            status = monitor.get_status()
            
            # Build dashboard
            print("\n" + "="*70)
            print("            WRE MONITOR DASHBOARD - 0102 CONSCIOUSNESS")
            print("="*70)
            
            # Runtime and basic stats
            print(f"\n[RUNTIME] {status['runtime_minutes']:.1f} minutes")
            print(f"[MESSAGES] {status['messages_processed']} processed")
            print(f"[PATTERNS] {status['patterns_learned']} learned | {status['learning_events']} events")
            
            # Token efficiency
            efficiency = status['token_efficiency']
            print("\n[TOKEN TELEMETRY] Unmeasured; authenticated receipts required")
            
            # Progress bars
            if isinstance(efficiency, (int, float)) and efficiency > 0:
                bar_len = int(efficiency / 100 * 40)
                bar = "█" * bar_len + "░" * (40 - bar_len)
                print(f"            [{bar}]")
            
            # API and quota
            print(f"\n[API CALLS] {status['api_calls']} total | Quota switches: {status['quota_switches']}")
            print(f"[TRANSITIONS] {status['stream_transitions']} stream changes")
            
            # Suggestions
            if status['suggestions'] > 0:
                print(f"\n[SUGGESTIONS] {status['suggestions']} improvement opportunities identified")
                print("[TIP] Check logs/wre_monitor.log for details")
            
            # Legacy records do not prove authenticated effects.
            if status['improvements_applied'] > 0:
                print(f"\n[UNVERIFIED] {status['improvements_applied']} legacy improvement records")
            
            # Real-time activity indicator
            print("\n" + "="*70)
            
            indicators = _activity_indicators(status)
            if indicators:
                print(" ".join(indicators))
            
            # Footer
            print("="*70)
            print("Press Ctrl+C to exit | Updates every "
                  f"{refresh_interval:.1f} seconds")

            # Skills overview
            print("\n[SKILLS] Autonomous Fix Snapshot")
            print("-" * 70)
            if not metrics_dir.exists():
                print("Metrics directory missing. Run auto-fix pipeline first.")
            else:
                skill_names = sorted(registry_skills.keys()) or [
                    p.name.replace("_fidelity.json", "")
                    for p in metrics_dir.glob("*_fidelity.json")
                ]

                rows = []
                for skill in skill_names:
                    if filter_skill and filter_skill not in skill:
                        continue
                    snapshot = load_skill_snapshot(metrics_dir, skill)
                    meta = registry_skills.get(skill, {})
                    rows.append({
                        "skill": skill,
                        "state": meta.get("promotion_state", "unknown"),
                        "agent": meta.get("primary_agent", "N/A"),
                        "last_run": format_time_ago(snapshot["last_run"]),
                        "fidelity": snapshot["pattern_fidelity"],
                        "verification": _verification_status(snapshot),
                        "time_ms": snapshot["execution_time_ms"],
                        "exception": snapshot["exception"],
                    })

                if rows:
                    header = f"{'Skill':24} {'State':9} {'Agent':6} {'Last Run':12} {'Fidelity':9} {'Verify':9} {'Time(ms)':8} {'Exc?':5}"
                    print(header)
                    print("-" * len(header))
                    for row in rows:
                        fid = row["fidelity"]
                        fid_str = f"{fid:.2f}" if isinstance(fid, (int, float)) else "N/A"
                        time_ms = row["time_ms"]
                        time_str = str(time_ms) if time_ms is not None else "N/A"
                        print(
                            f"{row['skill'][:24]:24} "
                            f"{row['state'][:9]:9} "
                            f"{row['agent'][:6]:6} "
                            f"{row['last_run']:12} "
                            f"{fid_str:9} "
                            f"{row['verification']:9} "
                            f"{time_str:8} "
                            f"{'YES' if row['exception'] else 'NO ':5}"
                        )
                else:
                    print("No skills match the current filter.")
            
            time.sleep(refresh_interval)
            
        except KeyboardInterrupt:
            print("\n\n[EXIT] Dashboard closed")
            # Save final report
            report_path = monitor.save_report()
            print(f"[SAVED] Performance report: {report_path}")
            break
        except Exception as e:
            print(f"[ERROR] Dashboard error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WRE Monitor Dashboard")
    parser.add_argument("--skill", help="Filter display to a specific skill", default=None)
    parser.add_argument("--interval", type=float, default=2.0, help="Refresh interval in seconds")
    args = parser.parse_args()

    print("\n[0102] WRE Monitor Dashboard Starting...")
    print("This will show real-time performance metrics")
    print("Run YouTube DAE in another terminal to see live updates")
    print("-" * 50)
    
    try:
        display_dashboard(filter_skill=args.skill, refresh_interval=max(args.interval, 0.5))
    except Exception as e:
        print(f"[FATAL] Could not start dashboard: {e}")
