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

Git Push DAE Launch Script
Extracted from main.py per WSP 62 Large File Refactoring Protocol

Purpose: Launch GitPushDAE daemon with WSP 91 full observability
Domain: infrastructure
Module: git_push_dae
"""

import sys
import time
import traceback
import threading
from typing import Any, Dict

_git_push_lock = threading.RLock()
_git_push_instance: Any = None
_git_push_status: Dict[str, Any] = {}

# WRE CoT preflight - recursive enforcement after watch period
try:
    from modules.infrastructure.wre_core.src.dae_preflight import preflight_guard
except ImportError:
    def preflight_guard(name, quiet=True):
        def decorator(func):
            return func
        return decorator


@preflight_guard("git_push_dae")
def launch_git_push_dae(run_once: bool = False):
    """
    Launch GitPushDAE daemon with WSP 91 full observability.
    Transforms git push from human-triggered action to autonomous DAE.

    Args:
        run_once: Run a single monitoring cycle and return to caller (menu-safe).
    """
    global _git_push_instance
    print("\n" + "="*60)
    print("[MENU] GIT PUSH DAE - AUTONOMOUS DEVELOPMENT")
    print("="*60)
    print("WSP 91 DAEMON: Fully autonomous git push with observability")
    print("No human decision required - agentic parameters drive decisions")
    print("="*60)

    try:
        # Import and launch the GitPushDAE
        print("[DEBUG-MAIN] About to import GitPushDAE module...")
        from modules.infrastructure.git_push_dae.src.git_push_dae import GitPushDAE
        print("[DEBUG-MAIN] GitPushDAE module imported successfully")

        # Create and start the daemon
        print("[DEBUG-MAIN] Creating GitPushDAE instance...")
        dae = GitPushDAE(domain="foundups_development", check_interval=300)  # 5-minute checks
        print("[DEBUG-MAIN] GitPushDAE instance created")
        with _git_push_lock:
            _git_push_instance = dae
            _git_push_status.clear()
            _git_push_status.update({"status": "starting", "run_once": run_once})

        if run_once:
            print("[INFO] Running one GitPushDAE monitoring cycle (run-once mode)...")
            health = dae.run_once()
            with _git_push_lock:
                _git_push_status["status"] = health.status
            print(f"[INFO] GitPushDAE run-once complete (health: {health.status})")
        else:
            print("[DEBUG-MAIN] Starting GitPushDAE daemon...")
            dae.start()
            with _git_push_lock:
                _git_push_status["status"] = "running"
            print("[DEBUG-MAIN] GitPushDAE daemon started")

            print("\n[INFO]GitPushDAE launched successfully!")
            print("[INFO] Monitor logs at: logs/git_push_dae.log")
            print("[INFO] Press Ctrl+C to stop the daemon")

            try:
                # Keep running until interrupted
                while dae.active:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n[INFO] Stopping GitPushDAE...")
                dae.stop()
                with _git_push_lock:
                    _git_push_status["status"] = "stopped"

    except ImportError as e:
        with _git_push_lock:
            _git_push_status["status"] = "failed"
        print(f"[ERROR]Failed to import GitPushDAE: {e}")
        print("GitPushDAE module not available")
        traceback.print_exc()

    except Exception as e:
        with _git_push_lock:
            _git_push_status["status"] = "failed"
        print(f"[ERROR]GitPushDAE failed: {e}")
        traceback.print_exc()
        input("\nPress Enter to continue...")

    finally:
        with _git_push_lock:
            _git_push_instance = None
            if "status" not in _git_push_status or _git_push_status["status"] == "running":
                _git_push_status["status"] = "stopped"
        # Flush stdout/stderr to prevent "lost sys.stderr" errors
        # when returning to menu (WSP 90 UTF-8 enforcement cleanup)
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except:
            pass


def view_git_post_history():
    """View git push history from logs."""
    print("\n[INFO] Git Push History")
    print("=" * 60)
    try:
        from pathlib import Path
        log_path = Path("logs/git_push_dae.log")
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8").strip().split("\n")
            # Show last 20 relevant lines
            push_lines = [l for l in lines if "push" in l.lower() or "commit" in l.lower()][-20:]
            for line in push_lines:
                print(line)
            if not push_lines:
                print("[INFO] No git push entries in log")
        else:
            print("[INFO] No git push log found")
    except Exception as e:
        print(f"[ERROR] Failed to read history: {e}")


def check_instance_status():
    """Check if GitPushDAE is currently running."""
    print("\n[INFO] GitPushDAE Instance Status")
    print("=" * 60)
    try:
        from modules.infrastructure.instance_lock.src.instance_manager import get_instance_lock
        lock = get_instance_lock("git_push_dae")
        duplicates = lock.check_duplicates(quiet=True)
        if duplicates:
            print(f"[RUNNING] GitPushDAE active with PID(s): {duplicates}")
        else:
            print("[STOPPED] GitPushDAE not running")
    except Exception as e:
        print(f"[UNKNOWN] Could not check status: {e}")


def stop_git_push_dae() -> Dict[str, Any]:
    """Request shutdown for the broker-managed GitPushDAE runtime."""
    with _git_push_lock:
        dae = _git_push_instance
        if dae is None:
            return {"status": "not_running"}

        dae.stop()
        _git_push_status["status"] = "stopping"
        return {"status": "stopping"}


if __name__ == "__main__":
    launch_git_push_dae()
