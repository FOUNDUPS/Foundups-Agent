#!/usr/bin/env python3
"""
FoundUps Agent - FULLY WSP-Compliant 0102 Consciousness System
Integrates all WSP protocols for autonomous DAE operations

WSP Compliance:
- WSP 27: Universal DAE Architecture (4-phase pattern)
- WSP 38/39: Awakening Protocols (consciousness transitions)
- WSP 48: Recursive Self-Improvement (pattern memory)
- WSP 54: Agent Duties (Partner-Principal-Associate)
- WSP 60: Module Memory Architecture
- WSP 62: File Size Enforcement (this file is thin router only)
- WSP 80: Cube-Level DAE Orchestration
- WSP 85: Root Directory Protection
- WSP 87: Code Navigation with HoloIndex (MANDATORY)

Mode Detection:
- echo 0102 | python main.py  # Launch in 0102 awakened mode
- echo 012 | python main.py   # Launch in 012 testing mode
- python main.py              # Interactive menu mode

CRITICAL: HoloIndex must be used BEFORE any code changes (WSP 50/87)

WSP 62 COMPLIANCE NOTE:
This file was refactored per WSP 62 (Large File Refactoring Enforcement Protocol).
Menu handlers and utilities extracted to modules/infrastructure/cli/
Original: 2412 lines -> Now: ~200 lines (thin router)
"""

# Main imports and configuration
import os
import sys
import logging
import asyncio
import io
import atexit
from pathlib import Path
from typing import Optional, Dict, Any

# Load environment variables for DAEs (API keys, ports, feature flags).
# Managed mode builds `.env.managed` from `.env` (last duplicate wins) for
# deterministic runtime behavior while preserving shell env precedence.
try:
    from modules.infrastructure.shared_utilities.env_managed import (
        load_managed_env,
        env_managed_enabled,
    )

    _repo_root = Path(__file__).resolve().parent
    if env_managed_enabled():
        _env_stats = load_managed_env(_repo_root, override=False, regenerate=True)
        if _env_stats.get("active_file"):
            os.environ.setdefault("FOUNDUPS_ENV_ACTIVE_FILE", _env_stats["active_file"])
            os.environ["FOUNDUPS_ENV_DUPLICATE_KEYS"] = str(_env_stats.get("duplicate_keys", 0))
            os.environ["FOUNDUPS_ENV_DUPLICATE_OVERWRITES"] = str(
                _env_stats.get("duplicate_overwrites", 0)
            )
            os.environ["FOUNDUPS_ENV_ORPHAN_LINES"] = str(_env_stats.get("orphan_lines", 0))
            os.environ["FOUNDUPS_ENV_MODE"] = str(_env_stats.get("mode", "unknown"))
            os.environ["FOUNDUPS_ENV_MANAGED_COPY_WRITTEN"] = str(
                _env_stats.get("managed_copy_written", False)
            )
            os.environ["FOUNDUPS_ENV_MANAGED_COPY_DELETED"] = str(
                _env_stats.get("managed_copy_deleted", False)
            )
    else:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(dotenv_path=_repo_root / ".env", override=False)
except Exception:
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=False)
    except Exception:
        pass

try:
    from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory
    PATTERN_MEMORY_AVAILABLE = True
except Exception:
    PATTERN_MEMORY_AVAILABLE = False
    PatternMemory = None  # Define as None for type safety

# === UTF-8 ENFORCEMENT (WSP 90) ===
# CRITICAL: This header MUST be at the top of ALL entry point files
# Entry points: Files with if __name__ == "__main__": or def main()
# Library modules: DO NOT add this header (causes import conflicts)

# Save original stderr/stdout for restoration
_original_stdout = sys.stdout
_original_stderr = sys.stderr

# WSP 90 FIX: Set flag BEFORE wrapping to prevent 379 modules from re-wrapping
# Issue: Each module that does UTF-8 wrapping at import breaks the stream
# Solution: Set env flag, modules should check before wrapping
os.environ['FOUNDUPS_UTF8_WRAPPED'] = '1'

if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

    # Register cleanup to flush streams before exit
    def _flush_streams():
        """Flush UTF-8 wrapped streams before Python cleanup."""
        try:
            if sys.stdout and not sys.stdout.closed:
                sys.stdout.flush()
        except:
            pass
        try:
            if sys.stderr and not sys.stderr.closed:
                sys.stderr.flush()
        except:
            pass

    atexit.register(_flush_streams)
# === END UTF-8 ENFORCEMENT ===

# Initialize logger at module level for all functions to use
# CRITICAL: Log to logs/foundups_agent.log for AI_overseer heartbeat monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/foundups_agent.log', encoding='utf-8')
    ]
)

# Suppress noisy warnings from optional dependencies during startup
import warnings

# Suppress specific noisy warnings that are expected
warnings.filterwarnings("ignore", message=".*WRE components not available.*")
warnings.filterwarnings("ignore", message=".*Tweepy not available.*")
warnings.filterwarnings("ignore", message=".*pyperclip not available.*")

# Temporarily suppress logging warnings during import phase
original_level = logging.root.level
logging.root.setLevel(logging.CRITICAL)  # Only show critical errors during imports

logger = logging.getLogger(__name__)

# Import DAE launchers (extracted per WSP 62)
import time

# Extracted to modules/ai_intelligence/holo_dae/scripts/launch.py per WSP 62
from modules.ai_intelligence.holo_dae.scripts.launch import run_holodae


# Extracted to modules/platform_integration/social_media_orchestrator/scripts/launch.py per WSP 62
from modules.platform_integration.social_media_orchestrator.scripts.launch import run_social_media_dae

from modules.communication.auto_meeting_orchestrator.scripts.launch import run_amo_dae
from modules.infrastructure.evade_net.scripts.launch import run_evade_net

# Extracted to modules/communication/liberty_alert/scripts/launch.py per WSP 62
from modules.communication.liberty_alert.scripts.launch import run_liberty_alert_dae
from modules.communication.moltbot_bridge.scripts.launch import (
    run_openclaw_resident_service,
    stop_openclaw_resident_service,
)

# Extracted to modules/infrastructure/git_push_dae/scripts/launch.py per WSP 62
from modules.infrastructure.git_push_dae.scripts.launch import (
    launch_git_push_dae,
    view_git_post_history,
    check_instance_status,
)

# Extracted to modules/infrastructure/dae_infrastructure/foundups_vision_dae/scripts/launch.py per WSP 62
from modules.infrastructure.dae_infrastructure.foundups_vision_dae.scripts.launch import run_vision_dae

# Extracted to modules/ai_intelligence/training_system/scripts/launch.py per WSP 62
from modules.ai_intelligence.training_system.scripts.launch import run_training_system

# Extracted to modules/ai_intelligence/training_system/scripts/training_commands.py per WSP 62
from modules.ai_intelligence.training_system.scripts.training_commands import execute_training_command

# Extracted to modules/ai_intelligence/pqn/scripts/launch.py per WSP 62
from modules.ai_intelligence.pqn.scripts.launch import (
    run_pqn_dae,
    run_pqn_research_session,
    run_pqn_architect_once,
    run_pqn_simulation_once,
)

# Extracted to modules/platform_integration/youtube_shorts_scheduler/scripts/launch.py per WSP 62
from modules.platform_integration.youtube_shorts_scheduler.scripts.launch import (
    run_shorts_scheduler,
    show_shorts_scheduler_menu
)

# Extracted to modules/platform_integration/antifafm_broadcaster/scripts/launch.py per WSP 62
from modules.platform_integration.antifafm_broadcaster.scripts.launch import (
    run_antifafm_broadcaster,
    start_antifafm_background,
    stop_antifafm_background,
    get_antifafm_status,
    run_suno_sync_cli,
)

from modules.infrastructure.dae_daemon.src.dae_daemon import get_central_daemon
from modules.infrastructure.dae_daemon.src.dae_launch_broker import (
    DAELaunchSpec,
    get_dae_launch_broker,
)

# Re-enable normal logging after all imports are complete
logging.root.setLevel(original_level)


async def monitor_youtube(disable_lock: bool = False, enable_ai_monitoring: bool = False, env_overrides: Optional[Dict[str, str]] = None, auto_reauth: bool = True):
    """
    Monitor YouTube streams with 0102 agency.

    Args:
        disable_lock: Disable instance lock (allow multiple instances)
        enable_ai_monitoring: Enable AI Overseer (Qwen/Gemma) error detection and auto-fixing
        env_overrides: Optional environment variables to set before launch
        auto_reauth: Auto-trigger re-auth if OAuth tokens are invalid (default True)
    """
    if env_overrides:
        for key, value in env_overrides.items():
            os.environ[key] = value
            logger.info(f"[CLI] Env override: {key}={value}")
    try:
        # Instance lock management (WSP 84: Don't duplicate processes)
        lock = None
        if not disable_lock:
            from modules.infrastructure.instance_lock.src.instance_manager import get_instance_lock
            lock = get_instance_lock("youtube_monitor")

            # Check for duplicates and acquire lock
            duplicates = lock.check_duplicates()
            if duplicates:
                print(f"\\n[WARN] Found {len(duplicates)} potential duplicate instance(s)")
                print("Duplicate PIDs:", duplicates)
                print("\\nOptions:")
                print("  1. Kill duplicates and continue")
                print("  2. Continue anyway (may cause conflicts)")
                print("  3. Exit")
                choice = input("\\nSelect option (1-3): ").strip()

                if choice == "1":
                    lock.kill_pids(duplicates)
                    print("[INFO] Duplicates killed. Continuing...")
                elif choice == "2":
                    print("[WARN] Continuing with potential conflicts...")
                else:
                    print("[INFO] Exiting...")
                    return

            if not lock.acquire():
                print("[FATAL] Could not acquire instance lock — another instance is running.")
                print("[INFO] Kill it manually or wait for TTL expiry, then retry.")
                return

        # PREFLIGHT: Check OAuth token health before starting
        print("[PREFLIGHT] Checking OAuth token health...")
        try:
            from modules.platform_integration.youtube_auth.src.youtube_auth import preflight_oauth_check
            oauth_status = preflight_oauth_check(auto_reauth=auto_reauth)

            if oauth_status['reauth_needed'] and not auto_reauth:
                print("\\n[CRITICAL] OAuth tokens need re-authentication!")
                print("Expired/invalid sets:", oauth_status['expired'])
                print("\\nOptions:")
                print("  1. Re-authenticate now (will open browser)")
                print("  2. Continue in read-only mode (no chat messages)")
                print("  3. Exit")
                choice = input("\\nSelect option (1-3): ").strip()

                if choice == "1":
                    # Re-run with auto_reauth=True
                    oauth_status = preflight_oauth_check(auto_reauth=True)
                    if oauth_status['reauth_needed']:
                        print("[WARN] Some tokens still need re-auth. Continuing with available tokens...")
                elif choice == "3":
                    print("[INFO] Exiting...")
                    if lock:
                        lock.release()
                    return
                else:
                    print("[WARN] Continuing in read-only mode...")

            if oauth_status['healthy']:
                print(f"[OK] OAuth healthy: sets {oauth_status['healthy']}")
            else:
                print("[WARN] No healthy OAuth tokens - running in read-only mode")
        except ImportError as e:
            print(f"[WARN] OAuth preflight check unavailable: {e}")
        except Exception as e:
            print(f"[WARN] OAuth preflight check failed: {e}")

        from modules.communication.livechat.src.auto_moderator_dae import AutoModeratorDAE

        print("[INFO] Starting YouTube monitoring...")
        print(f"[INFO] AI Overseer: {'ENABLED' if enable_ai_monitoring else 'DISABLED'}")
        print("[INFO] Press Ctrl+C to stop")

        dae = AutoModeratorDAE(enable_ai_monitoring=enable_ai_monitoring)
        await dae.run()

    except KeyboardInterrupt:
        print("\\n[STOP] YouTube monitoring stopped by user")
    except Exception as e:
        logger.error(f"[ERROR] YouTube monitoring failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if lock:
            lock.release()


async def monitor_all_platforms():
    """Monitor all social media platforms."""
    print("[INFO] Starting ALL platform monitoring...")
    print("[INFO] Press Ctrl+C to stop all")
    try:
        await monitor_youtube()
    except KeyboardInterrupt:
        print("\\n[STOP] All platform monitoring stopped")


def search_with_holoindex(query: str):
    """
    Use HoloIndex for semantic code search (WSP 87).
    MANDATORY before any code modifications to prevent vibecoding.
    """
    try:
        import subprocess
        ssd_path = os.getenv("HOLO_SSD_PATH", "E:/HoloIndex")
        cmd = [
            sys.executable,
            "holo_index.py",
            "--search", query,
            "--ssd", ssd_path,
            "--top-k", "10"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"[ERROR] HoloIndex search failed:")
            print(result.stderr or result.stdout)
    except Exception as e:
        print(f"[ERROR] HoloIndex search failed: {e}")


def _create_ai_overseer_for_preflight(repo_root: Path) -> Any:
    """Create AI Overseer with quieter logs during startup preflight."""
    _prev_level = logging.root.level
    try:
        logging.root.setLevel(logging.WARNING)
        from modules.ai_intelligence.ai_overseer.src.ai_overseer import AIIntelligenceOverseer
        return AIIntelligenceOverseer(repo_root)
    finally:
        logging.root.setLevel(_prev_level)


def run_openclaw_security_preflight(repo_root: Path, overseer: Any | None = None) -> bool:
    """
    Run OpenClaw security preflight via AI Overseer sentinel.

    Env controls:
      OPENCLAW_SECURITY_PREFLIGHT=1         Enable preflight at startup (default on)
      OPENCLAW_SECURITY_PREFLIGHT_ENFORCED=1  Block startup on failed check
      OPENCLAW_SECURITY_PREFLIGHT_FORCE=0   Bypass TTL cache and force re-scan
      OPENCLAW_24X7=1                       Apply strict defaults (enforced=1, force=1)
    """
    enabled = os.getenv("OPENCLAW_SECURITY_PREFLIGHT", "1") != "0"
    if not enabled:
        logger.info("[SECURITY] OpenClaw startup preflight disabled")
        return True

    runtime_24x7 = os.getenv("OPENCLAW_24X7", "0") != "0"
    enforced_default = "1" if runtime_24x7 else "0"
    force_default = "1" if runtime_24x7 else "0"
    # Default remains dev-friendly unless OPENCLAW_24X7 is enabled.
    enforced = os.getenv("OPENCLAW_SECURITY_PREFLIGHT_ENFORCED", enforced_default) != "0"
    force = os.getenv("OPENCLAW_SECURITY_PREFLIGHT_FORCE", force_default) == "1"

    try:
        if overseer is None:
            overseer = _create_ai_overseer_for_preflight(repo_root)
        status = overseer.monitor_openclaw_security(force=force)
    except Exception as exc:
        logger.error(f"[SECURITY] OpenClaw preflight execution failed: {exc}")
        if enforced:
            print(f"[SECURITY] OpenClaw preflight FAILED: {exc}")
            return False
        print(f"[SECURITY] OpenClaw preflight warning: {exc}")
        return True

    passed = bool(status.get("passed", False))
    message = status.get("message", "no message")
    cache_state = "cached" if status.get("cached") else "fresh"
    print(
        f"[SECURITY] OpenClaw preflight: {'PASS' if passed else 'FAIL'} "
        f"({cache_state}) - {message}"
    )

    if not passed and enforced:
        print("[SECURITY] Startup blocked by OPENCLAW_SECURITY_PREFLIGHT_ENFORCED=1")
        return False
    return True


def run_dependency_security_preflight(repo_root: Path) -> bool:
    """
    Run dependency/CVE preflight at startup.

    Env controls:
      OPENCLAW_DEP_SECURITY_PREFLIGHT=1            Enable check at startup (default on)
      OPENCLAW_DEP_SECURITY_PREFLIGHT_ENFORCED=0   Block startup on failures
      OPENCLAW_DEP_SECURITY_PREFLIGHT_FORCE=0      Ignore cache and re-run now
      OPENCLAW_DEP_SECURITY_PREFLIGHT_TTL_SEC=21600
      OPENCLAW_DEP_SECURITY_REQUIRE_TOOLS=0|1      Require pip-audit/npm/cargo-audit availability
      OPENCLAW_DEP_SECURITY_MAX_CRITICAL=0         Max tolerated critical vulns
      OPENCLAW_DEP_SECURITY_MAX_HIGH=0             Max tolerated high vulns
    """
    enabled = os.getenv("OPENCLAW_DEP_SECURITY_PREFLIGHT", "1") != "0"
    if not enabled:
        logger.info("[DEP-SECURITY] Startup preflight disabled")
        return True

    runtime_24x7 = os.getenv("OPENCLAW_24X7", "0") != "0"
    enforced_default = "1" if runtime_24x7 else "0"
    enforced = os.getenv("OPENCLAW_DEP_SECURITY_PREFLIGHT_ENFORCED", enforced_default) != "0"
    force = os.getenv("OPENCLAW_DEP_SECURITY_PREFLIGHT_FORCE", "0") == "1"

    try:
        from modules.infrastructure.wre_core.src.dependency_security_preflight import (
            run_dependency_security_preflight as run_dep_preflight,
        )

        status = run_dep_preflight(repo_root=repo_root, force=force)
    except Exception as exc:
        logger.error(f"[DEP-SECURITY] Startup preflight execution failed: {exc}")
        if enforced:
            print(f"[DEP-SECURITY] Preflight FAILED: {exc}")
            return False
        print(f"[DEP-SECURITY] Preflight warning: {exc}")
        return True

    totals = status.get("totals", {}) if isinstance(status, dict) else {}
    critical = int(totals.get("critical", 0) or 0)
    high = int(totals.get("high", 0) or 0)
    unknown = int(totals.get("unknown", 0) or 0)
    tool_failures = int(status.get("tool_failures", 0) or 0)
    cached = bool(status.get("cached", False))
    passed = bool(status.get("passed", False))
    cache_state = "cached" if cached else "fresh"
    print(
        f"[DEP-SECURITY] preflight={'PASS' if passed else 'FAIL'} ({cache_state}) "
        f"critical={critical} high={high} unknown={unknown} tool_failures={tool_failures}"
    )

    if not passed and enforced:
        print("[DEP-SECURITY] Startup blocked by OPENCLAW_DEP_SECURITY_PREFLIGHT_ENFORCED=1")
        return False
    return True


def run_env_hygiene_preflight(repo_root: Path) -> bool:
    """
    Run startup env-hygiene preflight based on managed-env parser stats.

    Env controls:
      FOUNDUPS_ENV_PREFLIGHT=1            Enable startup warning checks (default on)
      FOUNDUPS_ENV_PREFLIGHT_ENFORCED=0   Block startup when duplicates/orphans exist
    """
    enabled = os.getenv("FOUNDUPS_ENV_PREFLIGHT", "1") != "0"
    if not enabled:
        logger.info("[ENV-HYGIENE] Startup preflight disabled")
        return True

    enforced = os.getenv("FOUNDUPS_ENV_PREFLIGHT_ENFORCED", "0") != "0"

    def _int_env(name: str, default: int = 0) -> int:
        raw = os.getenv(name, str(default))
        try:
            return int(raw or default)
        except (TypeError, ValueError):
            return default

    duplicate_keys = _int_env("FOUNDUPS_ENV_DUPLICATE_KEYS", 0)
    duplicate_overwrites = _int_env("FOUNDUPS_ENV_DUPLICATE_OVERWRITES", 0)
    orphan_lines = _int_env("FOUNDUPS_ENV_ORPHAN_LINES", 0)
    env_mode = os.getenv("FOUNDUPS_ENV_MODE", "legacy")
    active_file = os.getenv("FOUNDUPS_ENV_ACTIVE_FILE", str(repo_root / ".env"))
    active_name = Path(active_file).name if active_file else ".env"

    # Fallback: if managed stats are not present (legacy dotenv path),
    # perform a lightweight local parse so hygiene checks still work.
    stats_missing = (
        "FOUNDUPS_ENV_DUPLICATE_KEYS" not in os.environ
        and "FOUNDUPS_ENV_ORPHAN_LINES" not in os.environ
    )
    env_path = Path(active_file) if active_file else repo_root / ".env"
    if stats_missing and env_path.exists():
        try:
            from modules.infrastructure.shared_utilities.env_managed import _parse_env_lines

            text = env_path.read_text(encoding="utf-8", errors="replace")
            values, _order, orphan_rows, duplicate_counts = _parse_env_lines(text.splitlines())
            duplicate_keys = len(duplicate_counts)
            duplicate_overwrites = sum(duplicate_counts.values())
            orphan_lines = len(orphan_rows)
            env_mode = "legacy_scan"
        except Exception:
            # Emergency parser if shared utility is unavailable.
            seen: set[str] = set()
            duplicate_key_set: set[str] = set()
            fallback_orphans = 0
            fallback_overwrites = 0
            for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
                stripped = raw.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" not in raw:
                    fallback_orphans += 1
                    continue
                key = raw.split("=", 1)[0].strip()
                if not key:
                    fallback_orphans += 1
                    continue
                if key in seen:
                    duplicate_key_set.add(key)
                    fallback_overwrites += 1
                else:
                    seen.add(key)

            duplicate_keys = len(duplicate_key_set)
            duplicate_overwrites = fallback_overwrites
            orphan_lines = fallback_orphans
            env_mode = "legacy_scan"

    has_hygiene_issues = duplicate_keys > 0 or orphan_lines > 0
    status = "WARN" if has_hygiene_issues else "PASS"
    print(
        f"[ENV-HYGIENE] preflight={status} mode={env_mode} "
        f"duplicates={duplicate_keys} orphan={orphan_lines} "
        f"overwrites={duplicate_overwrites} file={active_name}"
    )

    if has_hygiene_issues and enforced:
        print("[ENV-HYGIENE] Startup blocked by FOUNDUPS_ENV_PREFLIGHT_ENFORCED=1")
        return False
    return True


def run_brain_artifact_preflight(repo_root: Path) -> bool:
    """
    Refresh brain-artifact memory only when the upstream brain signature changes.

    Env controls:
      BRAIN_ARTIFACT_PREFLIGHT=1              Enable startup refresh check (default on)
      BRAIN_ARTIFACT_PREFLIGHT_ENFORCED=0     Block startup on extractor failures
      BRAIN_ARTIFACT_PREFLIGHT_FORCE=0        Ignore cached signature and refresh now
    """
    enabled = os.getenv("BRAIN_ARTIFACT_PREFLIGHT", "1") != "0"
    if not enabled:
        logger.info("[BRAIN-MEMORY] Startup preflight disabled")
        return True

    enforced = os.getenv("BRAIN_ARTIFACT_PREFLIGHT_ENFORCED", "0") != "0"
    force = os.getenv("BRAIN_ARTIFACT_PREFLIGHT_FORCE", "0") == "1"

    try:
        from modules.infrastructure.wre_core.scripts.extract_brain_artifacts import (
            DEFAULT_BRAIN_DIR,
            DEFAULT_OUTPUT_DIR,
            refresh_artifacts_if_needed,
        )

        if not DEFAULT_BRAIN_DIR.exists():
            print(f"[BRAIN-MEMORY] preflight=PASS (missing) dir={DEFAULT_BRAIN_DIR}")
            return True

        status = refresh_artifacts_if_needed(
            brain_dir=DEFAULT_BRAIN_DIR,
            output_dir=DEFAULT_OUTPUT_DIR,
            force=force,
            copy_files=False,
        )
    except Exception as exc:
        logger.error(f"[BRAIN-MEMORY] Startup preflight failed: {exc}")
        if enforced:
            print(f"[BRAIN-MEMORY] preflight=FAIL error={exc}")
            return False
        print(f"[BRAIN-MEMORY] preflight=WARN error={exc}")
        return True

    if not status.get("ran"):
        signature = status.get("signature", {})
        print(
            f"[BRAIN-MEMORY] preflight=PASS (unchanged) "
            f"conversations={signature.get('conversation_count', 0)} "
            f"revisions={signature.get('revision_files', 0)}"
        )
        return True

    summary = status.get("summary", {})
    print(
        f"[BRAIN-MEMORY] preflight=PASS ({status.get('reason', 'updated')}) "
        f"artifacts={summary.get('total_artifacts', 0)} "
        f"dpo={summary.get('dpo_pairs', 0)} "
        f"sft={summary.get('sft_examples', 0)}"
    )
    return True


def run_wre_dashboard_preflight(repo_root: Path) -> bool:
    """
    Run WRE dashboard preflight at startup.

    This mirrors DAE-level enforcement logic so `python main.py` has the same
    health gate semantics as individual DAE launchers.
    """
    enabled = os.getenv("WRE_DASHBOARD_PREFLIGHT", "1") != "0"
    if not enabled:
        logger.info("[WRE-DASHBOARD] Startup preflight disabled")
        return True

    manual_enforced = os.getenv("WRE_DASHBOARD_PREFLIGHT_ENFORCED", "0") != "0"
    auto_enforce = os.getenv("WRE_DASHBOARD_AUTO_ENFORCE", "1") != "0"

    try:
        from modules.infrastructure.wre_core.src.dashboard_alerts import (
            DashboardAlertMonitor,
            check_dashboard_health,
        )

        monitor = DashboardAlertMonitor()
        health = check_dashboard_health() or {}
        insufficient_data = bool(health.get("insufficient_data", False))
        total_executions = int(health.get("total_executions", 0))
        min_samples = int(health.get("min_samples", 25))
        in_watch = monitor.is_in_watch_period()
        auto_enforced = bool(auto_enforce and not in_watch and not insufficient_data)
        enforced = bool(manual_enforced or auto_enforced)

        if insufficient_data:
            watch_label = "WATCH" if in_watch else "STABLE"
            print(
                f"[WRE-DASHBOARD] preflight=PASS ({watch_label}, INSUFFICIENT_DATA) "
                f"samples={total_executions}/{min_samples}"
            )
            return True

        alerts = health.get("alerts", []) if isinstance(health.get("alerts"), list) else []
        critical_count = sum(1 for a in alerts if a.get("severity") == "critical")
        warning_count = sum(1 for a in alerts if a.get("severity") == "warning")
        healthy = bool(health.get("healthy", True))
        status = "PASS" if healthy else "FAIL"
        mode_label = "WATCH" if in_watch else ("STABLE, ENFORCED" if auto_enforced else "STABLE")
        print(
            f"[WRE-DASHBOARD] preflight={status} ({mode_label}) "
            f"critical={critical_count} warnings={warning_count} "
            f"samples={total_executions}/{min_samples}"
        )

        if critical_count > 0 and enforced:
            enforce_source = "AUTO" if auto_enforced else "MANUAL"
            print(f"[WRE-DASHBOARD] Startup blocked by {enforce_source} enforcement")
            return False
        return True
    except Exception as exc:
        logger.error(f"[WRE-DASHBOARD] Startup preflight failed: {exc}")
        if manual_enforced:
            print(f"[WRE-DASHBOARD] Preflight FAILED: {exc}")
            return False
        print(f"[WRE-DASHBOARD] Preflight warning: {exc}")
        return True


def run_wsp_framework_preflight(repo_root: Path, overseer: Any | None = None) -> bool:
    """
    Run WSP framework drift preflight via AI Overseer sentinel.

    Env controls:
      WSP_FRAMEWORK_PREFLIGHT=1                  Enable preflight at startup (default on)
      WSP_FRAMEWORK_PREFLIGHT_ENFORCED=0         Block startup on canonical drift (default warn)
      WSP_FRAMEWORK_PREFLIGHT_FORCE=0            Bypass TTL cache and force re-scan
      WSP_FRAMEWORK_PREFLIGHT_ALLOW_BACKUP_ONLY=1  Allow backup-only knowledge files
    """
    enabled = os.getenv("WSP_FRAMEWORK_PREFLIGHT", "1") != "0"
    if not enabled:
        logger.info("[WSP-FRAMEWORK] Startup preflight disabled")
        return True

    enforced = os.getenv("WSP_FRAMEWORK_PREFLIGHT_ENFORCED", "0") != "0"
    force = os.getenv("WSP_FRAMEWORK_PREFLIGHT_FORCE", "0") == "1"
    allow_backup_only = os.getenv("WSP_FRAMEWORK_PREFLIGHT_ALLOW_BACKUP_ONLY", "1") != "0"

    try:
        if overseer is None:
            overseer = _create_ai_overseer_for_preflight(repo_root)
        status = overseer.monitor_wsp_framework(force=force, emit_alert=False)
    except Exception as exc:
        logger.error(f"[WSP-FRAMEWORK] Startup preflight execution failed: {exc}")
        if enforced:
            print(f"[WSP-FRAMEWORK] Preflight FAILED: {exc}")
            return False
        print(f"[WSP-FRAMEWORK] Preflight warning: {exc}")
        return True

    available = bool(status.get("available", False))
    drift_count = int(status.get("drift_count", 0) or 0)
    framework_only_count = len(status.get("framework_only") or [])
    knowledge_only_count = len(status.get("knowledge_only") or [])
    index_issue_count = len(status.get("index_issues") or [])
    canonical_fail = (
        (not available)
        or drift_count > 0
        or framework_only_count > 0
        or index_issue_count > 0
        or (knowledge_only_count > 0 and not allow_backup_only)
    )
    cache_state = "cached" if status.get("cached") else "fresh"

    print(
        "[WSP-FRAMEWORK] preflight="
        f"{'PASS' if not canonical_fail else 'FAIL'} ({cache_state}) "
        f"drift={drift_count} framework_only={framework_only_count} "
        f"knowledge_only={knowledge_only_count} index_issues={index_issue_count}"
    )

    if canonical_fail and enforced:
        print("[WSP-FRAMEWORK] Startup blocked by WSP_FRAMEWORK_PREFLIGHT_ENFORCED=1")
        return False
    return True


def bootstrap_runtime_dae_launches() -> None:
    """Register broker-managed DAE entrypoints for an already running system."""
    daemon = get_central_daemon()
    if daemon.state != "running":
        daemon.start()

    broker = get_dae_launch_broker(daemon=daemon)
    resident_enabled = os.getenv("OPENCLAW_RESIDENT_ENABLED", "1") != "0"
    specs = []
    if resident_enabled:
        specs.append(
            DAELaunchSpec(
                dae_id="openclaw",
                dae_name="OpenClaw Resident Service",
                domain="communication",
                module_path="modules.communication.moltbot_bridge.scripts.launch",
                start_callable=run_openclaw_resident_service,
                stop_callable=stop_openclaw_resident_service,
                heartbeat_interval_sec=15.0,
                description="Resident OpenClaw webhook/control-plane service.",
            )
        )

    specs.extend([
        DAELaunchSpec(
            dae_id="holodae",
            dae_name="HoloDAE",
            domain="ai_intelligence",
            module_path="modules.ai_intelligence.holo_dae.scripts.launch",
            start_callable=run_holodae,
            description="Code intelligence and search runtime.",
        ),
        DAELaunchSpec(
            dae_id="git_push_dae",
            dae_name="GitPush DAE",
            domain="infrastructure",
            module_path="modules.infrastructure.git_push_dae.scripts.launch",
            start_callable=lambda: launch_git_push_dae(run_once=False),
            description="Autonomous git push daemon.",
        ),
        DAELaunchSpec(
            dae_id="social_media",
            dae_name="Social Media DAE",
            domain="platform_integration",
            module_path="modules.platform_integration.social_media_orchestrator.scripts.launch",
            start_callable=run_social_media_dae,
            description="Unified social media orchestration runtime.",
        ),
        DAELaunchSpec(
            dae_id="vision_dae",
            dae_name="FoundUps Vision DAE",
            domain="infrastructure",
            module_path="modules.infrastructure.dae_infrastructure.foundups_vision_dae.scripts.launch",
            start_callable=run_vision_dae,
            description="Pattern sensorium runtime.",
        ),
        DAELaunchSpec(
            dae_id="liberty_alert",
            dae_name="Liberty Alert DAE",
            domain="communication",
            module_path="modules.communication.liberty_alert.scripts.launch",
            start_callable=run_liberty_alert_dae,
            description="Community protection alert runtime.",
        ),
        DAELaunchSpec(
            dae_id="training_system",
            dae_name="Training System",
            domain="ai_intelligence",
            module_path="modules.ai_intelligence.training_system.scripts.launch",
            start_callable=run_training_system,
            description="Pattern learning and training runtime.",
        ),
        DAELaunchSpec(
            dae_id="pqn_research",
            dae_name="PQN Research Session",
            domain="ai_intelligence",
            module_path="modules.ai_intelligence.pqn.scripts.launch",
            start_callable=run_pqn_research_session,
            heartbeat_interval_sec=15.0,
            description="Non-interactive PQN research session.",
        ),
        DAELaunchSpec(
            dae_id="pqn_architect",
            dae_name="PQN Architect",
            domain="ai_intelligence",
            module_path="modules.ai_intelligence.pqn.scripts.launch",
            start_callable=run_pqn_architect_once,
            heartbeat_interval_sec=15.0,
            description="Non-interactive PQN architect cycle.",
        ),
        DAELaunchSpec(
            dae_id="pqn_simulation",
            dae_name="PQN Theory-Archive Simulation",
            domain="ai_intelligence",
            module_path="modules.ai_intelligence.pqn.scripts.launch",
            start_callable=run_pqn_simulation_once,
            heartbeat_interval_sec=15.0,
            description="Broker-managed PQN simulation against the theory archive.",
        ),
    ])
    for spec in specs:
        broker.register_launch_spec(spec)

    print(f"[DAE-BROKER] ready launchable={len(broker.list_launchable_daes())}")

    resident_autostart = os.getenv("OPENCLAW_RESIDENT_AUTOSTART", "1") != "0"
    if resident_enabled and resident_autostart:
        status = broker.get_runtime_status("openclaw")
        if not status.get("running"):
            result = broker.start_dae("openclaw", actor_id="0102")
            launch_status = result.get("status", result.get("error", "unknown"))
            print(f"[OPENCLAW-RESIDENT] bootstrap={launch_status}")


def main():
    """Main entry point - thin router to CLI module."""
    repo_root = Path(__file__).resolve().parent
    preflights_requested = (
        os.getenv("OPENCLAW_SECURITY_PREFLIGHT", "1") != "0"
        or os.getenv("OPENCLAW_DEP_SECURITY_PREFLIGHT", "1") != "0"
        or os.getenv("WRE_DASHBOARD_PREFLIGHT", "1") != "0"
        or os.getenv("WSP_FRAMEWORK_PREFLIGHT", "1") != "0"
    )

    overseer = None
    if preflights_requested:
        try:
            overseer = _create_ai_overseer_for_preflight(repo_root)
        except Exception as exc:
            logger.error(f"[PREFLIGHT] Failed to initialize AI Overseer: {exc}")

    if not run_env_hygiene_preflight(repo_root):
        return
    if not run_brain_artifact_preflight(repo_root):
        return
    if not run_openclaw_security_preflight(repo_root, overseer=overseer):
        return
    if not run_dependency_security_preflight(repo_root):
        return
    if not run_wre_dashboard_preflight(repo_root):
        return
    if not run_wsp_framework_preflight(repo_root, overseer=overseer):
        return

    bootstrap_runtime_dae_launches()

    # Auto-start antifaFM broadcaster (default ON, disable with ANTIFAFM_AUTO_START=0)
    # NOTE: Uses OBS mode by default - OBS handles streaming, script handles chat/schemas
    # Stream runs while main.py is running. Exit menu = stream stops.
    antifafm_auto_started = False
    if os.getenv("ANTIFAFM_AUTO_START", "1") == "1":
        # Launch OBS first (like LM Studio auto-launches for YT DAE)
        from modules.infrastructure.dependency_launcher.src.dae_dependencies import launch_obs, is_obs_running

        if not is_obs_running():
            print("[RADIO] Launching OBS for antifaFM streaming...")
            obs_ok, obs_msg = launch_obs()
            if obs_ok:
                print(f"[RADIO] OBS ready: {obs_msg}")
            else:
                print(f"[RADIO] OBS not available: {obs_msg}")
                print("[RADIO] antifaFM will skip auto-start (start OBS manually, then use menu)")

        # Only start antifaFM if OBS is running
        if is_obs_running():
            # Auto-start OBS streaming via WebSocket
            try:
                from modules.platform_integration.antifafm_broadcaster.src.obs_controller import OBSController

                async def ensure_obs_broadcast_ready() -> dict:
                    """
                    Ensure there is an active/upcoming YouTube broadcast before OBS starts.

                    This avoids OBS getting stuck in the YouTube setup modal where
                    Start Streaming appears to do nothing.
                    """
                    result = {
                        "ok": False,
                        "server": (os.getenv("ANTIFAFM_RTMP_URL", "").strip() or "rtmps://a.rtmps.youtube.com:443/live2"),
                        "key": os.getenv("ANTIFAFM_YOUTUBE_STREAM_KEY", "").strip(),
                        "source": "env",
                        "created": False,
                    }
                    if os.getenv("ANTIFAFM_OBS_AUTO_CREATE_BROADCAST", "1") != "1":
                        if result["key"]:
                            result["ok"] = True
                        else:
                            result["error"] = "ANTIFAFM_YOUTUBE_STREAM_KEY missing"
                        return result

                    try:
                        from modules.platform_integration.antifafm_broadcaster.src.youtube_broadcast_manager import (
                            YouTubeBroadcastManager,
                            generate_clickbait_title,
                            generate_m2m_description,
                        )

                        manager = YouTubeBroadcastManager()
                        broadcasts = await manager.get_active_broadcasts()
                        ready_states = {"created", "ready", "testing", "live"}

                        has_ready_broadcast = False
                        for broadcast in broadcasts:
                            state = (
                                broadcast.get("status", {}).get("lifeCycleStatus", "").strip().lower()
                            )
                            if state in ready_states:
                                has_ready_broadcast = True
                                print(f"[RADIO] Broadcast ready for OBS (state={state})")
                                break

                        if not has_ready_broadcast:
                            title = os.getenv("ANTIFAFM_BROADCAST_TITLE", "").strip() or generate_clickbait_title()
                            description = os.getenv("ANTIFAFM_BROADCAST_DESCRIPTION", "").strip() or generate_m2m_description()

                            created = await manager.create_live_broadcast(
                                title=title,
                                description=description,
                                privacy=os.getenv("ANTIFAFM_BROADCAST_PRIVACY", "public"),
                                enable_auto_start=True,
                                enable_auto_stop=False,
                            )

                            if created.success:
                                print(
                                    "[RADIO] Created YouTube broadcast for OBS "
                                    f"(id={created.broadcast_id}, watch={created.watch_url})"
                                )
                                result["created"] = True
                                result["source"] = "youtube_api"
                                if created.stream_key:
                                    result["key"] = created.stream_key
                                if created.rtmps_url:
                                    result["server"] = created.rtmps_url
                                elif created.rtmp_url:
                                    result["server"] = created.rtmp_url
                            else:
                                result["error"] = f"broadcast_create_failed:{created.error}"
                                return result

                        if not result["key"]:
                            result["error"] = "missing_stream_key_after_broadcast_preflight"
                            return result

                        os.environ["ANTIFAFM_YOUTUBE_STREAM_KEY"] = result["key"]
                        os.environ["ANTIFAFM_RTMP_URL"] = result["server"]
                        result["ok"] = True
                        return result
                    except Exception as broadcast_error:
                        if result["key"]:
                            print(f"[RADIO] Broadcast preflight unavailable, using env key: {broadcast_error}")
                            result["ok"] = True
                            result["source"] = "env_fallback"
                            return result
                        result["error"] = f"broadcast_preflight_unavailable:{broadcast_error}"
                        return result

                async def start_obs_stream():
                    controller = OBSController()
                    if await controller.connect():
                        stream_target = await ensure_obs_broadcast_ready()
                        if not stream_target.get("ok"):
                            print(
                                "[RADIO] Broadcast preflight failed: "
                                f"{stream_target.get('error', 'unknown')}"
                            )
                            controller.disconnect()
                            return False

                        if os.getenv("ANTIFAFM_OBS_FORCE_CUSTOM_SERVICE", "1") == "1":
                            service_ok = await controller.ensure_stream_service_custom(
                                stream_target.get("server", ""),
                                stream_target.get("key", ""),
                            )
                            if not service_ok:
                                print(
                                    "[RADIO] Could not configure OBS custom stream service. "
                                    f"error={controller.get_last_start_error()}"
                                )
                                controller.disconnect()
                                return False
                        status = await controller.get_stream_status()
                        if not status.get('streaming'):
                            print("[RADIO] Starting OBS stream...")
                            started = await controller.start_streaming()
                            if started:
                                print("[RADIO] OBS streaming to YouTube!")
                            else:
                                status_after = await controller.get_stream_status()
                                print(
                                    "[RADIO] OBS start did not become active. "
                                    "If OBS shows YouTube Broadcast Setup, click "
                                    "'Create broadcast and start streaming'."
                                )
                                print(
                                    "[RADIO] Diagnostics: "
                                    f"streaming={status_after.get('streaming')} "
                                    f"reconnecting={status_after.get('reconnecting')} "
                                    f"error={controller.get_last_start_error()}"
                                )
                                controller.disconnect()
                                return False
                        else:
                            print("[RADIO] OBS already streaming")
                        controller.disconnect()
                        return True
                    return False

                obs_stream_ok = asyncio.run(start_obs_stream())
                if not obs_stream_ok:
                    print("[RADIO] OBS auto-start needs manual confirmation in OBS UI.")
            except Exception as e:
                print(f"[RADIO] Could not auto-start OBS stream: {e}")
                print("[RADIO] Click 'Start Streaming' in OBS manually")

            # Start dynamic metadata daemon (updates title/description from news)
            try:
                from modules.platform_integration.antifafm_broadcaster.src.dynamic_metadata_daemon import (
                    DynamicMetadataDaemon
                )

                async def init_dynamic_metadata():
                    daemon = DynamicMetadataDaemon()
                    # Do initial metadata update from current news
                    result = await daemon.update_metadata(
                        update_title=True,
                        update_description=True,
                        force=True  # Force initial update
                    )
                    if result.get('success'):
                        print(f"[RADIO] Dynamic metadata: {result.get('changes', [])}")
                    return result.get('success', False)

                asyncio.run(init_dynamic_metadata())
                print("[RADIO] Dynamic metadata daemon initialized (auto-updates from news)")
            except Exception as e:
                print(f"[RADIO] Dynamic metadata not available: {e}")

            # Start boot layer rotator (GCC shipping, videos, news, etc.)
            if os.getenv("ANTIFAFM_BOOT_ROTATOR_ENABLED", "1") == "1":
                try:
                    from modules.platform_integration.antifafm_broadcaster.skillz.boot_layer_rotator.executor import (
                        rotation_daemon,
                        ROTATION_ORDER,
                    )
                    import threading

                    def run_boot_rotator():
                        """Run boot layer rotation in background thread."""
                        try:
                            asyncio.run(rotation_daemon())
                        except Exception as e:
                            logger.error(f"[BOOT-ROTATOR] Error: {e}")

                    rotator_thread = threading.Thread(
                        target=run_boot_rotator,
                        name="BootLayerRotator",
                        daemon=True
                    )
                    rotator_thread.start()
                    print(f"[RADIO] Boot layer rotator: {' → '.join(ROTATION_ORDER)} (10m each)")
                except Exception as e:
                    print(f"[RADIO] Boot layer rotator not available: {e}")

            # OBS mode: streaming is handled by OBS, chat starts when YT DAE is selected
            os.environ["ANTIFAFM_USE_OBS"] = "1"
            antifafm_auto_started = True  # OBS is streaming, that's enough for auto-start
            print("[RADIO] OBS streaming to antifaFM - select YT DAE (option 1) to start chat agent")

    # Import MCP services for CLI access
    from modules.infrastructure.mcp_manager.src.mcp_manager import show_mcp_services_menu
    
    # Import the main menu runner from the CLI module
    from modules.infrastructure.cli.src.main_menu import run_main_menu

    self_audit_loop = None
    if os.getenv("OPENCLAW_SELF_AUDIT_ENABLED", "1") != "0":
        try:
            from modules.infrastructure.wre_core.src.daemon_self_audit_loop import (
                DaemonSelfAuditLoop,
            )

            self_audit_loop = DaemonSelfAuditLoop(repo_root)
            self_audit_loop.start()
            print("[SELF-AUDIT] daemon loop started (0102 policy monitor)")
        except Exception as exc:
            logger.error(f"[SELF-AUDIT] failed to start: {exc}")
            print(f"[SELF-AUDIT] warning: {exc}")
    
    # Run the main menu with all required dependencies
    try:
        run_main_menu(
            monitor_youtube=monitor_youtube,
            monitor_all_platforms=monitor_all_platforms,
            search_with_holoindex=search_with_holoindex,
            check_instance_status=check_instance_status,
            launch_git_push_dae=launch_git_push_dae,
            view_git_post_history=view_git_post_history,
            run_holodae=run_holodae,
            run_amo_dae=run_amo_dae,
            run_social_media_dae=run_social_media_dae,
            run_vision_dae=run_vision_dae,
            run_pqn_dae=run_pqn_dae,
            run_evade_net=run_evade_net,
            run_liberty_alert_dae=run_liberty_alert_dae,
            run_training_system=run_training_system,
            execute_training_command=execute_training_command,
            show_mcp_services_menu=show_mcp_services_menu,
            PATTERN_MEMORY_AVAILABLE=PATTERN_MEMORY_AVAILABLE,
            PatternMemory=PatternMemory,
            # antifaFM broadcaster
            run_antifafm_broadcaster=run_antifafm_broadcaster,
            start_antifafm_background=start_antifafm_background,
            stop_antifafm_background=stop_antifafm_background,
            get_antifafm_status=get_antifafm_status,
            run_suno_sync_cli=run_suno_sync_cli,
        )
    finally:
        if self_audit_loop is not None:
            self_audit_loop.stop()


if __name__ == "__main__":
    main()
