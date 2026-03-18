#!/usr/bin/env python3
"""
HoloDAE Launch Script
Extracted from main.py per WSP 62 Large File Refactoring Protocol

Purpose: Launch HoloDAE - Code Intelligence & Monitoring System
Domain: ai_intelligence
Module: holo_dae
"""

import sys
import time
import logging
import threading
from typing import Any, Dict

logger = logging.getLogger(__name__)

_holodae_lock = threading.RLock()
_holodae_instance: Any = None
_holodae_status: Dict[str, Any] = {}

# WRE CoT preflight - recursive enforcement after watch period
try:
    from modules.infrastructure.wre_core.src.dae_preflight import preflight_guard
except ImportError:
    def preflight_guard(name, quiet=True):
        def decorator(func):
            return func
        return decorator


@preflight_guard("holo_dae")
def run_holodae():
    """Run HoloDAE (Code Intelligence & Monitoring)."""
    global _holodae_instance
    print("[HOLODAE] Starting HoloDAE - Code Intelligence & Monitoring System...")

    # HOLO-DAE INSTANCE LOCKING (First Principles: Resource Protection & Consistency)
    from modules.infrastructure.instance_lock.src.instance_manager import get_instance_lock
    lock = get_instance_lock("holodae_monitor")

    # Check for duplicates and acquire lock
    duplicates = lock.check_duplicates()
    if duplicates:
        logger.warning("[REC] Duplicate HoloDAE Instances Detected!")
        print("\n[REC] Duplicate HoloDAE Instances Detected!")
        print(f"\n  Found {len(duplicates)} instances of HoloDAE running:")
        for i, pid in enumerate(duplicates, 1):
            print(f"\n  {i}. PID {pid} - [Checking process details...]")
        print("\n  Current instance will exit to prevent conflicts.")
        print("  Use --no-lock to disable instance locking.")
        return  # Exit if duplicates found

    # Acquire lock for this instance
    if not lock.acquire():
        logger.error("*EFailed to acquire HoloDAE instance lock - another instance is running")
        print("\n*EFailed to acquire HoloDAE instance lock!")
        print("   Another HoloDAE instance is already running.")
        print("   Only one instance can run at a time to prevent index conflicts.")
        print("   Use --no-lock to disable instance locking.")
        return  # Exit if lock acquisition failed

    try:
        from holo_index.qwen_advisor.autonomous_holodae import AutonomousHoloDAE
        holodae = AutonomousHoloDAE()
        with _holodae_lock:
            _holodae_instance = holodae
            _holodae_status.clear()
            _holodae_status.update({"status": "starting"})

        # Log successful instance acquisition
        instance_summary = lock.get_instance_summary()
        total_instances = instance_summary["total_instances"]
        current_pid = instance_summary["current_pid"]
        logger.info(f"[INFO]HoloDAE SINGLE INSTANCE: PID {current_pid} - No other HoloDAEs detected")

        # WRE Skill Triggers (WSP 46/96: Fire code_intelligence skills each cycle)
        _skill_trigger = None
        try:
            from modules.infrastructure.wre_core.src.skill_trigger import SkillTriggerMixin
            _skill_trigger = SkillTriggerMixin()
            _skill_trigger.init_skill_triggers(
                domain="code_intelligence",
                cadence_minutes=10,
            )
            logger.info("[WRE-TRIGGER] Code intelligence skill triggers initialized")
        except Exception as trigger_exc:
            logger.debug(f"[WRE-TRIGGER] Skill triggers unavailable: {trigger_exc}")

        holodae.start_autonomous_monitoring()
        with _holodae_lock:
            _holodae_status.update({"status": "running"})

        print("[HOLODAE] Autonomous monitoring active. Press Ctrl+C to stop.")

        # Keep the process running
        try:
            while holodae.active:
                # Fire WRE code_intelligence skills on cadence
                if _skill_trigger:
                    try:
                        _skill_trigger.fire_pending_skills_sync()
                    except Exception as skill_exc:
                        logger.debug(f"[WRE-TRIGGER] Skill fire error: {skill_exc}")
                time.sleep(1)
        except KeyboardInterrupt:
            print("[HOLODAE] Stopping autonomous monitoring...")
            holodae.stop_autonomous_monitoring()
            print("[HOLODAE] HoloDAE stopped successfully")

    except Exception as e:
        with _holodae_lock:
            _holodae_status["status"] = "failed"
        print(f"[HOLODAE-ERROR] Failed to start: {e}")
        import traceback
        traceback.print_exc()

    finally:
        with _holodae_lock:
            if _holodae_instance is not None:
                _holodae_instance = None
            if "status" not in _holodae_status or _holodae_status["status"] == "running":
                _holodae_status["status"] = "stopped"
        # Release the instance lock when done
        lock.release()
        logger.info("[LOCK] HoloDAE monitor instance lock released")


def stop_holodae() -> Dict[str, Any]:
    """Request shutdown for the broker-managed HoloDAE runtime."""
    with _holodae_lock:
        holodae = _holodae_instance
        if holodae is None:
            return {"status": "not_running"}

        holodae.stop_autonomous_monitoring()
        _holodae_status["status"] = "stopping"
        return {"status": "stopping"}


if __name__ == "__main__":
    run_holodae()
