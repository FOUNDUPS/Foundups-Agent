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
import io
import atexit
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Mapping, Sequence

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

# Do not replace pytest's capture streams when tests import this entrypoint as a module.
if sys.platform.startswith('win') and "pytest" not in sys.modules:
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
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/foundups_agent.log', encoding='utf-8')
    ]
)

try:
    from modules.platform_integration.antifafm_broadcaster.src.obs_logging_guard import (
        install_obs_logging_guard,
    )

    install_obs_logging_guard()
except Exception:
    pass

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
from modules.ai_intelligence.holo_dae.scripts.launch import run_holodae, stop_holodae


# Extracted to modules/platform_integration/social_media_orchestrator/scripts/launch.py per WSP 62
from modules.platform_integration.social_media_orchestrator.scripts.launch import (
    run_social_media_dae,
    stop_social_media_dae,
)

from modules.communication.auto_meeting_orchestrator.scripts.launch import run_amo_dae
from modules.infrastructure.evade_net.scripts.launch import run_evade_net

# Extracted to modules/communication/liberty_alert/scripts/launch.py per WSP 62
from modules.communication.liberty_alert.scripts.launch import run_liberty_alert_dae
from modules.communication.moltbot_bridge.scripts.launch import (
    run_openclaw_resident_service,
    stop_openclaw_resident_service,
    run_openclaw_supervisor_service,
    stop_openclaw_supervisor_service,
)

# Extracted to modules/infrastructure/git_push_dae/scripts/launch.py per WSP 62
from modules.infrastructure.git_push_dae.scripts.launch import (
    launch_git_push_dae,
    stop_git_push_dae,
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

        # PREFLIGHT: Check OAuth token health before starting.
        # DUAL-SET CONTRACT (YT-OAUTH-DUAL-PREFLIGHT-MENU-PHASE1): pass
        # credential_sets=[1, 10] explicitly so BOTH the UnDaoDu/Move2Japan
        # (Set 1 / Chrome) and FoundUps/antifaFM (Set 10 / Edge) accounts are
        # checked and supervised-reauthed in order (Set 1 before Set 10). This is
        # the menu 1->1 ("Live Chat Monitor") entry path -- the menu launches
        # monitor_youtube(), which runs this single preflight; we do NOT run a
        # second preflight in the menu file to avoid double consent prompts.
        print("[PREFLIGHT] Checking OAuth token health (dual-set: Set 1 + Set 10)...")
        try:
            from modules.platform_integration.youtube_auth.src.youtube_auth import preflight_oauth_check
            oauth_status = preflight_oauth_check(auto_reauth=auto_reauth, credential_sets=[1, 10])

            # WSP 97 truthful dual-set summary (healthy / still-dead / missing).
            # Sanitize to fresh int set-id lists (non-secret) before logging so
            # CodeQL does not treat the oauth-status container as a clear-text
            # sensitive sink. These are credential-set IDs (1/10), never secrets.
            _ok_ids = sorted(int(s) for s in oauth_status.get('healthy', []))
            _dead_ids = sorted(int(s) for s in oauth_status.get('expired', []))
            _missing_ids = sorted(int(s) for s in oauth_status.get('missing', []))
            print(
                "[PREFLIGHT] Dual-set summary: "
                f"healthy={_ok_ids} still_dead={_dead_ids} missing={_missing_ids}"
            )
            # No false OK: if Set 1 is still dead, UnDaoDu/Move2Japan will fail.
            if 1 in oauth_status.get('expired', []) or 1 in oauth_status.get('missing', []):
                print(
                    "[WARN] Set 1 (UnDaoDu / Move2Japan, Chrome) is NOT healthy -- "
                    "those channels will FAIL. Fix: python modules/platform_integration/"
                    "youtube_auth/scripts/authorize_set1.py"
                )
            if 10 in oauth_status.get('expired', []) or 10 in oauth_status.get('missing', []):
                print(
                    "[WARN] Set 10 (FoundUps / antifaFM, Edge) is NOT healthy -- "
                    "those channels will FAIL. Fix: python modules/platform_integration/"
                    "youtube_auth/scripts/authorize_set10.py"
                )

            # SECTION C: reconciled quota headroom for BOTH sets (read-only) so
            # 012 sees Set 1 AND Set 10, not Set 1 only. Import function-locally.
            try:
                from modules.platform_integration.youtube_auth.src.quota_monitor import QuotaMonitor
                quota_summary = QuotaMonitor().get_usage_summary()
                for _set_id in (1, 10):
                    _s = quota_summary.get('sets', {}).get(_set_id)
                    if _s:
                        print(
                            f"[QUOTA] Set {_set_id}: {_s['used']}/{_s['limit']} used "
                            f"({_s['available']} headroom, {_s['status']})"
                        )
            except Exception as quota_exc:
                logger.debug(f"[QUOTA] dual-set headroom log skipped: {quota_exc}")

            if oauth_status['reauth_needed'] and not auto_reauth:
                print("\\n[CRITICAL] OAuth tokens need re-authentication!")
                print("Expired/invalid sets:", sorted(int(s) for s in oauth_status.get('expired', [])))
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
                print(f"[OK] OAuth healthy: sets {sorted(int(s) for s in oauth_status.get('healthy', []))}")
            else:
                print("[WARN] No healthy OAuth tokens - running in read-only mode")
                # DJ2-C: Dispatch OAuth no-healthy-tokens warning (WSP 97 truth distinction)
                try:
                    from modules.ai_intelligence.ai_overseer.src.preflight_resolution import (
                        on_preflight_fail,
                    )
                    on_preflight_fail(
                        component="oauth_youtube",
                        severity="high",
                        payload={
                            "warning": "no_healthy_oauth_tokens",
                            "auto_reauth": auto_reauth,
                            "reauth_needed": oauth_status.get('reauth_needed', False),
                            "expired_sets": oauth_status.get('expired', []),
                            "source_file": "main.py",
                            "source_function": "monitor_youtube",
                            "requires_012": True,
                            "automation_candidate": False,
                            "safe_autonomous_actions": ["read_oauth_health_artifact", "capacity_report", "identity_verify_if_token_valid"],
                            "unsafe_actions": ["credential_entry", "google_account_selection", "consent_approval"],
                            "remediation": ["read_oauth_credential_health", "run_supervised_reauth_if_012_approves", "verify_identity_after_reauth"],
                        },
                        source="main:monitor_youtube",
                    )
                except Exception as dispatch_exc:
                    logger.debug(f"[OAUTH] dispatch skipped: {dispatch_exc}")
        except ImportError as e:
            print(f"[WARN] OAuth preflight check unavailable: {e}")
            # DJ2-C: Dispatch OAuth import failure (may be intentional in minimal deploys)
            try:
                from modules.ai_intelligence.ai_overseer.src.preflight_resolution import (
                    on_preflight_fail,
                )
                on_preflight_fail(
                    component="oauth_youtube",
                    severity="medium",
                    payload={
                        "error": f"import_error: {e}",
                        "auto_reauth": auto_reauth,
                        "source_file": "main.py",
                        "source_function": "monitor_youtube",
                        "requires_012": False,
                        "automation_candidate": False,
                        "likely_cause": "youtube_auth_module_not_installed_or_minimal_deploy",
                    },
                    source="main:monitor_youtube",
                )
            except Exception:
                pass  # Best-effort dispatch
        except Exception as e:
            print(f"[WARN] OAuth preflight check failed: {e}")
            # DJ2-C: Dispatch OAuth preflight failure (unknown state)
            try:
                from modules.ai_intelligence.ai_overseer.src.preflight_resolution import (
                    on_preflight_fail,
                )
                on_preflight_fail(
                    component="oauth_youtube",
                    severity="high",
                    payload={
                        "error": f"preflight_exception: {e}",
                        "auto_reauth": auto_reauth,
                        "source_file": "main.py",
                        "source_function": "monitor_youtube",
                        "requires_012": True,
                        "automation_candidate": False,
                        "safe_autonomous_actions": ["read_oauth_health_artifact", "capacity_report"],
                        "unsafe_actions": ["credential_entry", "google_account_selection", "consent_approval"],
                        "remediation": ["read_oauth_credential_health", "diagnose_preflight_failure", "run_supervised_reauth_if_012_approves"],
                    },
                    source="main:monitor_youtube",
                )
            except Exception:
                pass  # Best-effort dispatch

        from modules.communication.livechat.src.auto_moderator_dae import AutoModeratorDAE

        print("[INFO] Starting YouTube monitoring...")
        print(f"[INFO] AI Overseer: {'ENABLED' if enable_ai_monitoring else 'DISABLED'}")
        print("[INFO] Press Ctrl+C to stop")

        # ANTIFAFM_AUTOSTART_AFTER_SELECT_PHASE1:
        # Opt-in, after-selection auto-launch of the 24/7 antifaFM broadcaster.
        # This is FUNCTION-SCOPE (only runs once 012 has selected the YouTube DAE
        # and the instance lock above is held) -- NOT the menu-boot autostart that
        # was deliberately removed (that broke the daemon; see
        # MAIN_MENU_ANTIFAFM_STARTUP_BOUNDARY_FIX_PHASE1 at module scope).
        #
        # Distinct flag name ANTIFAFM_AUTOSTART (the retired ANTIFAFM_AUTO_START is
        # still ignored). Default OFF -> merging never auto-broadcasts; 012 must opt
        # in via .env, and start_antifafm_background() itself returns False harmlessly
        # without ANTIFAFM_YOUTUBE_STREAM_KEY. start_antifafm_background() reuses the
        # antifafm_broadcaster instance lock and has blocking setup (FFmpeg cleanup +
        # ~5s settle + stream verification), so we dispatch it to a daemon thread to
        # avoid stalling the monitor. try/except guards: a broadcaster failure must
        # never break the YouTube daemon.
        if os.getenv("ANTIFAFM_AUTOSTART", "0") == "1":
            try:
                import threading as _threading
                _antifafm_thread = _threading.Thread(
                    target=start_antifafm_background,
                    daemon=True,
                    name="antifafm-autostart-after-select",
                )
                _antifafm_thread.start()
                print("[ANTIFAFM] ANTIFAFM_AUTOSTART=1 -> launching broadcaster (background, non-blocking)")
            except Exception as _antifafm_exc:
                logger.error(f"[ANTIFAFM] after-selection autostart failed (continuing daemon): {_antifafm_exc}")

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


def run_ironclaw_runtime_preflight(repo_root: Path) -> bool:
    """
    Validate IronClaw runtime readiness before startup when IronClaw is the active backend.

    Env controls:
      OPENCLAW_IRONCLAW_PREFLIGHT=1           Enable runtime readiness check (default on)
      OPENCLAW_IRONCLAW_PREFLIGHT_ALWAYS=0    Check even when backend is not `ironclaw`
      OPENCLAW_IRONCLAW_PREFLIGHT_ENFORCED    Explicitly block startup on failed readiness

    Default enforcement:
      - enabled automatically when `OPENCLAW_CONVERSATION_BACKEND=ironclaw`
      - and `OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK=0`
    """
    _ = repo_root  # kept for signature parity with other startup preflights

    enabled = os.getenv("OPENCLAW_IRONCLAW_PREFLIGHT", "1") != "0"
    if not enabled:
        logger.info("[IRONCLAW] Startup preflight disabled")
        return True

    backend = (os.getenv("OPENCLAW_CONVERSATION_BACKEND", "openclaw").strip().lower() or "openclaw")
    always = os.getenv("OPENCLAW_IRONCLAW_PREFLIGHT_ALWAYS", "0") != "0"
    if backend != "ironclaw" and not always:
        print(f"[IRONCLAW] preflight=SKIP backend={backend}")
        return True

    allow_local_fallback = os.getenv("OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK", "0") != "0"
    enforced_default = "1" if backend == "ironclaw" and not allow_local_fallback else "0"
    enforced = os.getenv("OPENCLAW_IRONCLAW_PREFLIGHT_ENFORCED", enforced_default) != "0"

    try:
        from modules.communication.moltbot_bridge.src.ironclaw_gateway_client import (
            IronClawGatewayClient,
        )

        status = IronClawGatewayClient().startup_probe()
    except Exception as exc:
        logger.error(f"[IRONCLAW] Startup preflight execution failed: {exc}")
        if enforced:
            print(f"[IRONCLAW] preflight=FAIL backend={backend} error={type(exc).__name__}")
            print("[IRONCLAW] Startup blocked by OPENCLAW_IRONCLAW_PREFLIGHT_ENFORCED=1")
            return False
        print(f"[IRONCLAW] preflight=WARN backend={backend} error={type(exc).__name__}")
        return True

    passed = bool(status.get("ok", False))
    runtime_backend = str(status.get("backend") or "none")
    detail = str(status.get("detail") or "no-detail")
    print(
        f"[IRONCLAW] preflight={'PASS' if passed else 'FAIL'} "
        f"backend={backend} resolved={runtime_backend} detail={detail}"
    )

    remediation = status.get("remediation") or []
    if remediation and not passed:
        print(f"[IRONCLAW] next={str(remediation[0])[:200]}")

    if not passed and enforced:
        print("[IRONCLAW] Startup blocked by OPENCLAW_IRONCLAW_PREFLIGHT_ENFORCED=1")
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

    if not passed:
        try:
            from modules.ai_intelligence.ai_overseer.src.preflight_resolution import (
                on_preflight_fail,
            )

            severity = "critical" if critical > 0 else ("high" if high > 0 else "medium")
            on_preflight_fail(
                component="dep_security",
                severity=severity,
                payload={
                    "critical": critical,
                    "high": high,
                    "unknown": unknown,
                    "tool_failures": tool_failures,
                    "cache_state": cache_state,
                    "enforced": enforced,
                },
                source="main.py:run_dep_security_preflight",
            )
        except Exception as exc:
            logger.debug(f"[DEP-SECURITY] preflight dispatch failed: {exc}")

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


def run_connect_wre(repo_root: Path) -> dict:
    """
    WSP 97 Section 4.6: --connect-wre CLI hook.

    Verify WRE preflight connection and enforcement mode.

    Returns structured status:
        coded: YES (command is wired in CLI)
        connection: CONNECTED | PARTIAL | DISCONNECTED
        readiness: READY | INSUFFICIENT_DATA | DEGRADED | BLOCKED | DISABLED
        manual_enforced: bool
        auto_enforced_now: bool
        sample_coverage: int (executions vs min_samples)
        alert_counts: {critical: int, warning: int}
    """
    result = {
        "coded": "YES",
        "connection": "DISCONNECTED",
        "readiness": "DISABLED",
        "manual_enforced": False,
        "auto_enforced_now": False,
        "sample_coverage": 0,
        "alert_counts": {"critical": 0, "warning": 0},
    }

    # Check WRE dashboard health
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

        manual_enforced = os.getenv("WRE_DASHBOARD_PREFLIGHT_ENFORCED", "0") != "0"
        auto_enforce = _wre_dashboard_auto_enforce_enabled()
        auto_enforced_now = bool(auto_enforce and not in_watch and not insufficient_data)

        alerts = health.get("alerts", []) if isinstance(health.get("alerts"), list) else []
        critical_count = sum(1 for a in alerts if a.get("severity") == "critical")
        warning_count = sum(1 for a in alerts if a.get("severity") == "warning")
        healthy = bool(health.get("healthy", True))

        result["connection"] = "CONNECTED"
        result["manual_enforced"] = manual_enforced
        result["auto_enforced_now"] = auto_enforced_now
        result["sample_coverage"] = total_executions
        result["alert_counts"] = {"critical": critical_count, "warning": warning_count}

        if insufficient_data:
            result["readiness"] = "INSUFFICIENT_DATA"
        elif critical_count > 0:
            result["readiness"] = "BLOCKED" if (manual_enforced or auto_enforced_now) else "DEGRADED"
        elif not healthy:
            result["readiness"] = "DEGRADED"
        else:
            result["readiness"] = "READY"

    except ImportError:
        result["connection"] = "PARTIAL"
        result["readiness"] = "DEGRADED"
    except Exception as exc:
        logger.error(f"[WRE] connect-wre check failed: {exc}")
        result["connection"] = "PARTIAL"
        result["readiness"] = "DEGRADED"

    return result


def _wre_dashboard_auto_enforce_enabled(*, interactive_menu: bool = False) -> bool:
    """Default dashboard auto-enforcement to autonomous runtimes, not menu startup."""

    explicit = os.getenv("WRE_DASHBOARD_AUTO_ENFORCE")
    if explicit is not None:
        return explicit != "0"
    if interactive_menu:
        return False
    return os.getenv("OPENCLAW_24X7", "0") != "0"


def run_wre_dashboard_preflight(repo_root: Path, *, interactive_menu: bool = True) -> bool:
    """
    Run WRE dashboard preflight at startup.

    This mirrors DAE-level enforcement logic so `python main.py` has the same
    health gate semantics as individual DAE launchers.

    Env controls:
      WRE_DASHBOARD_PREFLIGHT=1             Enable startup warning checks
      WRE_DASHBOARD_PREFLIGHT_ENFORCED=0    Manual override to block startup
      WRE_DASHBOARD_AUTO_ENFORCE            Explicit override to auto-block on criticals
      OPENCLAW_24X7=1                       Autonomous runtime defaults to enforced outside menu startup
    """
    enabled = os.getenv("WRE_DASHBOARD_PREFLIGHT", "1") != "0"
    if not enabled:
        logger.info("[WRE-DASHBOARD] Startup preflight disabled")
        return True

    manual_enforced = os.getenv("WRE_DASHBOARD_PREFLIGHT_ENFORCED", "0") != "0"
    auto_enforce = _wre_dashboard_auto_enforce_enabled(interactive_menu=interactive_menu)

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
                f"[WRE-DASHBOARD] preflight=WARN ({watch_label}, INSUFFICIENT_DATA) "
                f"samples={total_executions}/{min_samples}"
            )
            # DJ2-A: Dispatch insufficient_data as warning tier (WSP 97 truth distinction)
            try:
                from modules.ai_intelligence.ai_overseer.src.preflight_resolution import (
                    on_preflight_fail,
                )
                on_preflight_fail(
                    component="wre_dashboard",
                    severity="medium",
                    payload={
                        "samples": total_executions,
                        "min_samples": min_samples,
                        "insufficient_data": True,
                        "likely_cause": "cold_start_or_telemetry_drop",
                        "in_watch": in_watch,
                        "automation_candidate": True,
                    },
                    source="main:run_wre_dashboard_preflight",
                )
            except Exception as dispatch_exc:
                logger.debug(f"[WRE-DASHBOARD] dispatch skipped: {dispatch_exc}")
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
            try:
                from modules.ai_intelligence.ai_overseer.src.preflight_resolution import (
                    on_preflight_fail,
                )

                on_preflight_fail(
                    component="wre_dashboard",
                    severity="critical",
                    payload={
                        "critical": critical_count,
                        "warnings": warning_count,
                        "samples": total_executions,
                        "min_samples": min_samples,
                        "healthy": healthy,
                        "in_watch": in_watch,
                        "auto_enforced": auto_enforced,
                        "manual_enforced": manual_enforced,
                        "enforced": enforced,
                        "automation_candidate": True,
                    },
                    source="main:run_wre_dashboard_preflight",
                )
            except Exception as dispatch_exc:
                logger.debug(f"[WRE-DASHBOARD] dispatch skipped: {dispatch_exc}")
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

    if canonical_fail:
        try:
            from modules.ai_intelligence.ai_overseer.src.preflight_resolution import (
                on_preflight_fail,
            )

            severity = (
                "high" if (drift_count > 0 or framework_only_count > 0 or index_issue_count > 0) else "medium"
            )
            on_preflight_fail(
                component="wsp_framework",
                severity=severity,
                payload={
                    "available": available,
                    "drift_count": drift_count,
                    "framework_only_count": framework_only_count,
                    "knowledge_only_count": knowledge_only_count,
                    "index_issue_count": index_issue_count,
                    "cache_state": cache_state,
                    "enforced": enforced,
                    "allow_backup_only": allow_backup_only,
                },
                source="main.py:run_wsp_framework_preflight",
            )
        except Exception as exc:
            logger.debug(f"[WSP-FRAMEWORK] preflight dispatch failed: {exc}")

    if canonical_fail and enforced:
        print("[WSP-FRAMEWORK] Startup blocked by WSP_FRAMEWORK_PREFLIGHT_ENFORCED=1")
        return False
    return True


def run_git_main_merge_sentinel_preflight(repo_root: Path) -> bool:
    """
    Run git main-merge sentinel at startup.

    Optionally auto-merges feature branches to main to prevent drift.

    Env:
        GIT_MAIN_MERGE_SENTINEL=1           Enable sentinel (default OFF)
        GIT_MAIN_MERGE_SENTINEL_ENFORCED=0  If 1, block startup on failure
        GIT_MAIN_MERGE_SENTINEL_DELETE_BRANCH=1  Delete merged branch (default ON)
    """
    if os.getenv("GIT_MAIN_MERGE_SENTINEL", "0") != "1":
        logger.info("[GIT-MERGE-SENTINEL] Startup preflight disabled")
        return True

    try:
        from modules.infrastructure.wre_core.src.git_main_merge_sentinel import (
            run_main_merge_sentinel,
        )

        result = run_main_merge_sentinel(repo_root)

        # Build status line
        status = "PASS" if result["passed"] else "FAIL"
        merged = result.get("merged", False)
        branch = result.get("branch") or "main"
        actions_count = len(result.get("actions", []))

        if result["error"]:
            print(
                f"[GIT-MERGE-SENTINEL] preflight={status} branch={branch} "
                f"merged={merged} error={result['error']}"
            )
        else:
            print(
                f"[GIT-MERGE-SENTINEL] preflight={status} branch={branch} "
                f"merged={merged} actions={actions_count}"
            )

        # Log actions for debugging
        for action in result.get("actions", []):
            logger.debug(f"[GIT-MERGE-SENTINEL] {action}")

        return result["passed"]

    except ImportError as exc:
        logger.error(f"[GIT-MERGE-SENTINEL] Import failed: {exc}")
        print(f"[GIT-MERGE-SENTINEL] preflight=WARN import_error")
        return True  # Non-blocking import failure
    except Exception as exc:
        logger.error(f"[GIT-MERGE-SENTINEL] Startup preflight failed: {exc}")
        if os.getenv("GIT_MAIN_MERGE_SENTINEL_ENFORCED", "0") == "1":
            print(f"[GIT-MERGE-SENTINEL] preflight=FAIL error={exc}")
            return False
        print(f"[GIT-MERGE-SENTINEL] preflight=WARN error={exc}")
        return True


def run_reddog_readonly_operational_bootstrap_preflight(repo_root: Path) -> bool:
    """
    Run RedDog's read-only operational bootstrap before DAE autostart.

    This binds current work-state and HoloIndex freshness receipts to a
    read-only OpenClaw audit-swarm plan. It never spawns workers. It publishes
    read-only audit tasks to AgentDB only when the host explicitly enables
    the queue bridge. Missing receipts are warning-only by default so the menu
    still loads while the authoritative runtime wiring is incomplete.

    Env:
        REDDOG_READONLY_OPERATIONAL_BOOTSTRAP=1           Enable check (default ON)
        REDDOG_READONLY_OPERATIONAL_BOOTSTRAP_ENFORCED=0  Block startup if not ready
        REDDOG_READONLY_AUDIT_REPORT_COLLECTION_ENABLED   Override audit report collection bridge
        REDDOG_READONLY_AUDIT_DECISION_PERSIST_ENABLED    Override audit decision persistence bridge
        REDDOG_READONLY_AUDIT_SWARM_ENQUEUE_ENABLED       Override audit task enqueue bridge
        REDDOG_READONLY_AUDIT_RESEARCH_DECISION_E2E_ENABLED
                                                            Run one explicit read-only audit/research/decision cycle
        OPENCLAW_AUTO_TASKS_ENABLED                       Enables audit task enqueue if no override
        REDDOG_AUTHORITATIVE_WORK_STATE_PATH              Existing work-state JSON
        HOLOINDEX_FRESHNESS_RECEIPT                       Existing HoloIndex receipt
        HOLOINDEX_SSD_PATH                                Derive receipt path if set
    """

    if os.getenv("REDDOG_READONLY_OPERATIONAL_BOOTSTRAP", "1") == "0":
        logger.info("[REDDOG-BOOTSTRAP] Startup preflight disabled")
        return True

    enforced = os.getenv("REDDOG_READONLY_OPERATIONAL_BOOTSTRAP_ENFORCED", "0") != "0"
    enqueue_override = os.getenv("REDDOG_READONLY_AUDIT_SWARM_ENQUEUE_ENABLED")
    if enqueue_override is None:
        enqueue_requested = os.getenv("OPENCLAW_AUTO_TASKS_ENABLED", "0") != "0"
    else:
        enqueue_requested = enqueue_override != "0"
    collection_override = os.getenv("REDDOG_READONLY_AUDIT_REPORT_COLLECTION_ENABLED")
    if collection_override is None:
        collection_requested = os.getenv("OPENCLAW_AUTO_TASKS_ENABLED", "0") != "0"
    else:
        collection_requested = collection_override != "0"
    decision_persist_override = os.getenv("REDDOG_READONLY_AUDIT_DECISION_PERSIST_ENABLED")
    if decision_persist_override is None:
        decision_persist_requested = os.getenv("OPENCLAW_AUTO_TASKS_ENABLED", "0") != "0"
    else:
        decision_persist_requested = decision_persist_override != "0"
    e2e_requested = os.getenv("REDDOG_READONLY_AUDIT_RESEARCH_DECISION_E2E_ENABLED", "0") != "0"

    if e2e_requested:
        try:
            from modules.communication.moltbot_bridge.src.reddog_readonly_audit_research_decision_e2e_runtime import (
                run_reddog_readonly_audit_research_decision_e2e,
            )

            e2e_result = run_reddog_readonly_audit_research_decision_e2e(
                repo_root=repo_root,
                work_state_path=os.getenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", ""),
                holoindex_receipt_path=os.getenv("HOLOINDEX_FRESHNESS_RECEIPT", ""),
                holoindex_ssd_path=os.getenv("HOLOINDEX_SSD_PATH", ""),
            )
        except Exception as exc:
            logger.error(f"[REDDOG-BOOTSTRAP-E2E] Startup runtime failed: {exc}")
            if enforced:
                print(f"[REDDOG-BOOTSTRAP-E2E] preflight=FAIL error={type(exc).__name__}")
                return False
            print(f"[REDDOG-BOOTSTRAP-E2E] preflight=WARN error={type(exc).__name__}")
            return True

        e2e_status = "PASS" if e2e_result.accepted else "WARN"
        e2e_reasons = ",".join(e2e_result.rejection_reasons) if e2e_result.rejection_reasons else "(none)"
        final_bootstrap = e2e_result.final_bootstrap
        reports_persisted = sum(1 for task in e2e_result.task_runs if task.persist_accepted)
        print(
            f"[REDDOG-BOOTSTRAP-E2E] preflight={e2e_status} status={e2e_result.status} "
            f"accepted={e2e_result.accepted} initial_status={e2e_result.initial_bootstrap.status} "
            f"final_status={final_bootstrap.status if final_bootstrap else '(none)'} "
            f"tasks={len(e2e_result.task_runs)} reports_persisted={reports_persisted} "
            f"tasks_enqueued={e2e_result.readonly_audit_tasks_enqueued} "
            f"tasks_executed={e2e_result.readonly_audit_tasks_executed} "
            f"architect_action={(final_bootstrap.backend_architect_determination_action if final_bootstrap else None) or '(none)'} "
            f"architect_next_slice={(final_bootstrap.backend_architect_determination_next_slice if final_bootstrap else None) or '(none)'} "
            f"queue_candidates={(final_bootstrap.backend_architect_determination_queue_candidate_count if final_bootstrap else 0)} "
            f"reasons={e2e_reasons}"
        )
        print(
            "[REDDOG-BOOTSTRAP-E2E] "
            f"no_shell={e2e_result.no_shell_command_executed} "
            f"no_repo_mutation={e2e_result.no_repo_mutation_performed} "
            f"no_holoindex_reindex={e2e_result.no_holoindex_reindex_performed} "
            f"no_hermes_dispatch={e2e_result.no_hermes_dispatch_performed} "
            f"no_worktree={e2e_result.no_worktree_operation_performed} "
            f"no_pr={e2e_result.no_pr_created} "
            f"no_pattern_memory={e2e_result.no_pattern_memory_promotion_performed} "
            f"no_live_foundup_enqueue={e2e_result.no_live_foundup_enqueue_performed} "
            f"coding_worker_spawned={e2e_result.coding_worker_spawned}"
        )
        if e2e_result.accepted:
            return True
        if enforced:
            print(
                "[REDDOG-BOOTSTRAP-E2E] Startup blocked by "
                "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP_ENFORCED=1"
            )
            return False
        return True

    try:
        from modules.communication.moltbot_bridge.src.reddog_main_readonly_operational_bootstrap import (
            run_reddog_main_readonly_operational_bootstrap,
        )

        result = run_reddog_main_readonly_operational_bootstrap(
            repo_root=repo_root,
            work_state_path=os.getenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", ""),
            holoindex_receipt_path=os.getenv("HOLOINDEX_FRESHNESS_RECEIPT", ""),
            holoindex_ssd_path=os.getenv("HOLOINDEX_SSD_PATH", ""),
            collect_readonly_audit_reports=collection_requested,
            enqueue_readonly_audit_tasks=enqueue_requested,
            persist_readonly_audit_decision=decision_persist_requested,
        )
    except Exception as exc:
        logger.error(f"[REDDOG-BOOTSTRAP] Startup preflight failed: {exc}")
        if enforced:
            print(f"[REDDOG-BOOTSTRAP] preflight=FAIL error={type(exc).__name__}")
            return False
        print(f"[REDDOG-BOOTSTRAP] preflight=WARN error={type(exc).__name__}")
        return True

    status = "PASS" if result.ready else "WARN"
    reasons = ",".join(result.rejection_reasons) if result.rejection_reasons else "(none)"
    print(
        f"[REDDOG-BOOTSTRAP] preflight={status} status={result.status} "
        f"assignments={result.assignment_count} report_collection_attempted={result.report_collection_attempted} "
        f"report_collection_status={result.report_collection_status or '(none)'} "
        f"reports={result.report_collection_report_count} "
        f"decision_attempted={result.readonly_audit_decision_attempted} "
        f"decision_action={result.readonly_audit_decision_action or '(none)'} "
        f"decision_next_slice={result.readonly_audit_decision_next_slice or '(none)'} "
        f"decision_persist_attempted={result.readonly_audit_decision_persist_attempted} "
        f"decision_persist_status={result.readonly_audit_decision_persist_status or '(none)'} "
        f"enqueue_attempted={result.enqueue_attempted} "
        f"enqueue_decision={result.enqueue_decision or '(none)'} "
        f"enqueue_tasks={result.enqueue_task_count} reasons={reasons}"
    )
    if result.ready:
        print(
            f"[REDDOG-BOOTSTRAP] snapshot={result.snapshot_receipt_id} "
            f"swarm={result.swarm_id}"
        )
        return True

    if enforced:
        print("[REDDOG-BOOTSTRAP] Startup blocked by REDDOG_READONLY_OPERATIONAL_BOOTSTRAP_ENFORCED=1")
        return False
    return True


def run_reddog_authoritative_work_state_refresh_preflight(repo_root: Path) -> bool:
    """
    Refresh RedDog authoritative work state from already-observed source files.

    This is the producer for the read-only RedDog bootstrap. It performs no
    GitHub/W10 fetch itself; callers must provide existing source-record files.
    The output JSON is required to live outside the repo checkout.

    Env:
        REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH=1          Enable check (default ON)
        REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_ENFORCED=0 Block startup if not ready
        REDDOG_WORK_STATE_SOURCE_RECORD_SUPPLY=0           Materialize PR/W10 source records
        REDDOG_WORK_STATE_SOURCE_RECORD_SUPPLY_ENFORCED=0  Block startup if supply fails
        REDDOG_WORK_LEDGER_SOURCE_PROJECTION_SUPPLY=0      Materialize fresh runtime ledger projections
        REDDOG_WORK_LEDGER_SOURCE_PROJECTION_SUPPLY_ENFORCED=0 Block startup if projection fails
        REDDOG_AUTHORITATIVE_WORK_STATE_PATH               Output/read path for snapshot JSON
        REDDOG_ACTIVE_SLICE_LEDGER_PATH                    Optional active ledger source
        REDDOG_WORK_LEDGER_JSON_PATH                       Optional work ledger source
        REDDOG_GITHUB_PR_RECORDS_PATH                      Required existing PR records JSON
        REDDOG_W10_REPORT_RECORDS_PATH                     Required existing W10 records JSON
        REDDOG_WORK_STATE_USE_LATEST_READONLY_AUDIT_DECISION  Use persisted RedDog decision as requested slice
    """

    if os.getenv("REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH", "1") == "0":
        logger.info("[REDDOG-WORK-STATE] Startup refresh disabled")
        return True

    enforced = os.getenv("REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_ENFORCED", "0") != "0"
    use_decision_override = os.getenv("REDDOG_WORK_STATE_USE_LATEST_READONLY_AUDIT_DECISION")
    if use_decision_override is None:
        use_latest_decision = os.getenv("OPENCLAW_AUTO_TASKS_ENABLED", "0") != "0"
    else:
        use_latest_decision = use_decision_override != "0"

    try:
        from modules.communication.moltbot_bridge.src.reddog_main_authoritative_work_state_refresh_bootstrap import (
            run_reddog_main_authoritative_work_state_refresh_bootstrap,
        )
        from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
            resident_queue_runtime_flag_enabled,
            resident_queue_runtime_file_path,
        )

        active_slice_ledger_path = os.getenv("REDDOG_ACTIVE_SLICE_LEDGER_PATH", "")
        work_ledger_json_path = os.getenv("REDDOG_WORK_LEDGER_JSON_PATH", "")
        github_pr_records_path = resident_queue_runtime_file_path(
            os.environ,
            repo_root,
            "REDDOG_GITHUB_PR_RECORDS_PATH",
        )
        w10_report_records_path = resident_queue_runtime_file_path(
            os.environ,
            repo_root,
            "REDDOG_W10_REPORT_RECORDS_PATH",
        )
        source_supply_requested = resident_queue_runtime_flag_enabled(
            os.environ,
            "REDDOG_WORK_STATE_SOURCE_RECORD_SUPPLY",
        )
        source_supply_enforced = os.getenv("REDDOG_WORK_STATE_SOURCE_RECORD_SUPPLY_ENFORCED", "0") != "0"
        if source_supply_requested:
            from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_source_record_supply_bootstrap import (
                run_reddog_authoritative_work_state_source_record_supply_bootstrap,
            )

            supply = run_reddog_authoritative_work_state_source_record_supply_bootstrap(
                repo_root=repo_root,
                github_pr_records_output_path=github_pr_records_path,
                w10_report_records_output_path=w10_report_records_path,
                work_ledger_json_path=os.getenv("REDDOG_WORK_LEDGER_JSON_PATH", "") or None,
                github_repo_full_name=os.getenv("REDDOG_GITHUB_REPO_FULL_NAME", "FOUNDUPS/Foundups-Agent"),
                github_state=os.getenv("REDDOG_GITHUB_PR_SOURCE_STATE", "open"),
            )
            supply_status = "PASS" if supply.accepted else "WARN"
            supply_reasons = ",".join(supply.rejection_reasons) if supply.rejection_reasons else "(none)"
            print(
                f"[REDDOG-WORK-STATE-SOURCES] preflight={supply_status} status={supply.status} "
                f"github_records={supply.github_record_count} w10_records={supply.w10_record_count} "
                f"reasons={supply_reasons}"
            )
            if supply.accepted:
                if supply.github_pr_records_path:
                    github_pr_records_path = supply.github_pr_records_path
                    os.environ["REDDOG_GITHUB_PR_RECORDS_PATH"] = github_pr_records_path
                if supply.w10_report_records_path:
                    w10_report_records_path = supply.w10_report_records_path
                    os.environ["REDDOG_W10_REPORT_RECORDS_PATH"] = w10_report_records_path
            elif source_supply_enforced:
                print(
                    "[REDDOG-WORK-STATE-SOURCES] Startup blocked by "
                    "REDDOG_WORK_STATE_SOURCE_RECORD_SUPPLY_ENFORCED=1"
                )
                return False

        projection_requested = resident_queue_runtime_flag_enabled(
            os.environ,
            "REDDOG_WORK_LEDGER_SOURCE_PROJECTION_SUPPLY",
        )
        projection_enforced = os.getenv("REDDOG_WORK_LEDGER_SOURCE_PROJECTION_SUPPLY_ENFORCED", "0") != "0"
        if projection_requested:
            from modules.communication.moltbot_bridge.src.reddog_work_ledger_source_projection_supply_bootstrap import (
                run_reddog_work_ledger_source_projection_supply_bootstrap,
            )

            projection = run_reddog_work_ledger_source_projection_supply_bootstrap(
                repo_root=repo_root,
                github_pr_records_path=github_pr_records_path,
                w10_report_records_path=w10_report_records_path,
                active_slice_ledger_output_path=resident_queue_runtime_file_path(
                    os.environ,
                    repo_root,
                    "REDDOG_ACTIVE_SLICE_LEDGER_PATH",
                ),
                work_ledger_json_output_path=resident_queue_runtime_file_path(
                    os.environ,
                    repo_root,
                    "REDDOG_WORK_LEDGER_JSON_PATH",
                ),
            )
            projection_status = "PASS" if projection.accepted else "WARN"
            projection_reasons = ",".join(projection.rejection_reasons) if projection.rejection_reasons else "(none)"
            print(
                f"[REDDOG-WORK-LEDGER-PROJECTION] preflight={projection_status} status={projection.status} "
                f"projected_slices={projection.projected_slice_count} open_slices={projection.open_slice_count} "
                f"reasons={projection_reasons}"
            )
            if projection.accepted:
                if projection.active_slice_ledger_path:
                    active_slice_ledger_path = projection.active_slice_ledger_path
                    os.environ["REDDOG_ACTIVE_SLICE_LEDGER_PATH"] = active_slice_ledger_path
                if projection.work_ledger_json_path:
                    work_ledger_json_path = projection.work_ledger_json_path
                    os.environ["REDDOG_WORK_LEDGER_JSON_PATH"] = work_ledger_json_path
            elif projection_enforced:
                print(
                    "[REDDOG-WORK-LEDGER-PROJECTION] Startup blocked by "
                    "REDDOG_WORK_LEDGER_SOURCE_PROJECTION_SUPPLY_ENFORCED=1"
                )
                return False

        result = run_reddog_main_authoritative_work_state_refresh_bootstrap(
            repo_root=repo_root,
            active_slice_ledger_path=active_slice_ledger_path,
            work_ledger_json_path=work_ledger_json_path,
            github_pr_records_path=github_pr_records_path,
            w10_report_records_path=w10_report_records_path,
            work_state_output_path=resident_queue_runtime_file_path(
                os.environ,
                repo_root,
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH",
            ),
            worker_id=os.getenv("REDDOG_WORK_STATE_REFRESH_WORKER_ID", "reddog-main-bootstrap"),
            use_latest_readonly_audit_decision=use_latest_decision,
        )
    except Exception as exc:
        logger.error(f"[REDDOG-WORK-STATE] Startup refresh failed: {exc}")
        if enforced:
            print(f"[REDDOG-WORK-STATE] preflight=FAIL error={type(exc).__name__}")
            return False
        print(f"[REDDOG-WORK-STATE] preflight=WARN error={type(exc).__name__}")
        return True

    status = "PASS" if result.accepted else "WARN"
    reasons = ",".join(result.rejection_reasons) if result.rejection_reasons else "(none)"
    print(
        f"[REDDOG-WORK-STATE] preflight={status} status={result.status} "
        f"latest_decision_attempted={result.latest_decision_attempted} "
        f"latest_decision_next_slice={result.latest_decision_next_slice or '(none)'} "
        f"queue_items={result.queue_item_count} reasons={reasons}"
    )
    if result.accepted and result.work_state_path:
        os.environ["REDDOG_AUTHORITATIVE_WORK_STATE_PATH"] = result.work_state_path
        print(
            f"[REDDOG-WORK-STATE] refresh={result.refresh_id} "
            f"revision={result.committed_revision}"
        )
        return True

    if enforced:
        print("[REDDOG-WORK-STATE] Startup blocked by REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_ENFORCED=1")
        return False
    return True


def run_reddog_wre_queue_consumer_preflight(repo_root: Path) -> bool:
    """
    Dry-run consume the authoritative WRE queue item produced by work-state refresh.

    Env:
        REDDOG_WRE_QUEUE_CONSUMER_DRYRUN=1          Enable check (default ON)
        REDDOG_WRE_QUEUE_CONSUMER_DRYRUN_ENFORCED=0 Block startup if not ready
        REDDOG_AUTHORITATIVE_WORK_STATE_PATH         Existing work-state snapshot
        REDDOG_WRE_QUEUE_ITEM_ID                     Optional exact queue item id
    """

    if os.getenv("REDDOG_WRE_QUEUE_CONSUMER_DRYRUN", "1") == "0":
        logger.info("[REDDOG-WRE-QUEUE] Startup queue consumer dry-run disabled")
        return True

    enforced = os.getenv("REDDOG_WRE_QUEUE_CONSUMER_DRYRUN_ENFORCED", "0") != "0"

    try:
        from modules.communication.moltbot_bridge.src.reddog_main_wre_queue_consumer_bootstrap import (
            run_reddog_main_wre_queue_consumer_bootstrap,
        )
        from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
            resident_queue_runtime_file_path,
        )

        result = run_reddog_main_wre_queue_consumer_bootstrap(
            repo_root=repo_root,
            work_state_path=resident_queue_runtime_file_path(
                os.environ,
                repo_root,
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH",
            ),
            requested_queue_item_id=os.getenv("REDDOG_WRE_QUEUE_ITEM_ID", "") or None,
        )
    except Exception as exc:
        logger.error(f"[REDDOG-WRE-QUEUE] Startup queue consumer failed: {exc}")
        if enforced:
            print(f"[REDDOG-WRE-QUEUE] preflight=FAIL error={type(exc).__name__}")
            return False
        print(f"[REDDOG-WRE-QUEUE] preflight=WARN error={type(exc).__name__}")
        return True

    status = "PASS" if result.ready else "WARN"
    reasons = ",".join(result.rejection_reasons) if result.rejection_reasons else "(none)"
    print(
        f"[REDDOG-WRE-QUEUE] preflight={status} status={result.status} "
        f"queue_item={result.queue_item_id or '(none)'} "
        f"selected_slice={result.selected_slice or '(none)'} "
        f"next_gate={result.next_required_gate or '(none)'} "
        f"execution_ready={result.execution_ready} reasons={reasons}"
    )
    if result.ready:
        print(f"[REDDOG-WRE-QUEUE] receipt={result.receipt_id}")
        return True

    if enforced:
        print("[REDDOG-WRE-QUEUE] Startup blocked by REDDOG_WRE_QUEUE_CONSUMER_DRYRUN_ENFORCED=1")
        return False
    return True


def _reddog_env_sequence(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    if not raw.strip():
        return ()
    normalized = raw.replace("\n", ";").replace(",", ";")
    return tuple(item.strip() for item in normalized.split(";") if item.strip())


def _reddog_positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _reddog_float_env(name: str, default: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _reddog_truthy_env_value(value: str | None) -> bool:
    raw = str(value or "").strip().lower()
    return raw not in {"", "0", "false", "off", "no"}


def _reddog_digest_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _reddog_bounded_json_file(path: Path, *, max_bytes: int = 262_144) -> Any | None:
    try:
        if not path.is_file() or path.stat().st_size > max_bytes:
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _reddog_bounded_json_env(name: str, *, max_chars: int = 16384) -> Any | None:
    raw = os.getenv(name, "")
    if not raw.strip() or len(raw) > max_chars:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _reddog_mapping_sequence(payload: Any, keys: Sequence[str], *, limit: int) -> tuple[Mapping[str, Any], ...]:
    source: Any = payload
    if isinstance(payload, Mapping):
        for key in keys:
            candidate = payload.get(key)
            if isinstance(candidate, list):
                source = candidate
                break
    if not isinstance(source, list):
        return ()
    records: list[Mapping[str, Any]] = []
    for item in source:
        if isinstance(item, Mapping):
            records.append(dict(item))
            if len(records) >= limit:
                break
    return tuple(records)


def _reddog_resident_memory_limit() -> int:
    return _reddog_positive_int_env("REDDOG_RESIDENT_MEMORY_MAX_RECORDS", 20)


def _reddog_resident_brain_state_from_artifacts() -> Mapping[str, Any] | None:
    if not _reddog_truthy_env_value(os.getenv("REDDOG_RESIDENT_BRAIN_CONTEXT", "1")):
        return None

    raw_path = os.getenv("REDDOG_RESIDENT_BRAIN_STATE_PATH", "").strip()
    if raw_path:
        path = Path(raw_path)
    else:
        try:
            from modules.infrastructure.wre_core.scripts.extract_brain_artifacts import (
                DEFAULT_OUTPUT_DIR,
                DEFAULT_STATE_FILE,
            )

            path = DEFAULT_OUTPUT_DIR / DEFAULT_STATE_FILE
        except Exception:
            return None

    payload = _reddog_bounded_json_file(path)
    if not isinstance(payload, Mapping):
        return None

    signature = payload.get("signature") if isinstance(payload.get("signature"), Mapping) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    record_count = (
        payload.get("conversations")
        or signature.get("conversation_count", 0)
        or summary.get("total_artifacts", 0)
        or 0
    )
    try:
        normalized_count = int(record_count)
    except (TypeError, ValueError):
        normalized_count = 0

    return {
        "available": True,
        "signature_digest": _reddog_digest_payload(signature),
        "summary_digest": _reddog_digest_payload(summary),
        "record_count": normalized_count,
        "source": "brain_artifact_state",
        "updated_at": str(payload.get("updated_at", "")),
    }


def _reddog_resident_breadcrumbs_from_runtime(*, work_focus: str, foundup_id: str) -> tuple[Mapping[str, Any], ...]:
    if not _reddog_truthy_env_value(os.getenv("REDDOG_RESIDENT_BREADCRUMBS_CONTEXT", "1")):
        return ()

    limit = _reddog_resident_memory_limit()
    raw_path = os.getenv("REDDOG_RESIDENT_BREADCRUMBS_PATH", "").strip()
    if raw_path:
        payload = _reddog_bounded_json_file(Path(raw_path))
        return _reddog_mapping_sequence(payload, ("breadcrumbs", "records", "items"), limit=limit)

    try:
        from modules.communication.moltbot_bridge.src.openclaw_memory_queries import search_breadcrumbs

        topic = os.getenv("REDDOG_RESIDENT_MEMORY_QUERY", "").strip() or work_focus or foundup_id
        return tuple(dict(item) for item in search_breadcrumbs(topic, limit=limit) if isinstance(item, Mapping))
    except Exception:
        return ()


def _reddog_resident_workspace_memory_notes_from_env() -> tuple[Mapping[str, Any], ...]:
    raw_path = os.getenv("REDDOG_RESIDENT_WORKSPACE_MEMORY_NOTES_PATH", "").strip()
    if not raw_path:
        return ()
    payload = _reddog_bounded_json_file(Path(raw_path))
    return _reddog_mapping_sequence(
        payload,
        ("workspace_memory_notes", "notes", "records", "items"),
        limit=_reddog_resident_memory_limit(),
    )


def _reddog_resident_architect_cycle_requested() -> bool:
    explicit = os.getenv("REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE")
    if explicit is not None and str(explicit).strip():
        return _reddog_truthy_env_value(explicit)
    product_mode = os.getenv("REDDOG_RESIDENT_ARCHITECT_PRODUCT_MODE", "1")
    return _reddog_truthy_env_value(product_mode)


def _reddog_resident_architect_cycle_bucket() -> str:
    explicit = os.getenv("REDDOG_RESIDENT_ARCHITECT_CYCLE_BUCKET", "").strip()
    if explicit:
        return explicit
    raw_hours = os.getenv("REDDOG_RESIDENT_ARCHITECT_CADENCE_HOURS", "24").strip()
    try:
        hours = int(raw_hours)
    except (TypeError, ValueError):
        hours = 24
    if hours <= 0:
        return ""
    now = _reddog_resident_architect_now()
    bucket = int(now.timestamp()) // (hours * 60 * 60)
    return f"{hours}h:{bucket}"


def _reddog_resident_architect_now() -> datetime:
    raw = os.getenv("REDDOG_RESIDENT_ARCHITECT_NOW_ISO", "").strip()
    if raw:
        try:
            value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


class _RedDogConfiguredExternalResearchRetriever:
    """File-backed approved external research snapshot retriever for resident preflight."""

    def __init__(self, snapshot_path: Path) -> None:
        self.snapshot_path = snapshot_path

    def fetch(self, target: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if isinstance(payload, dict) and isinstance(payload.get("snapshots"), list):
            url = str(target.get("url") or target.get("target") or "")
            for item in payload["snapshots"]:
                if isinstance(item, dict) and str(item.get("source_url") or item.get("url") or "") == url:
                    return item
        return payload if isinstance(payload, dict) else {}


def _reddog_external_research_retriever_from_env() -> Any | None:
    raw_path = os.getenv("REDDOG_EXTERNAL_RESEARCH_SNAPSHOT_PATH", "").strip()
    if not raw_path:
        return None
    path = Path(raw_path)
    return _RedDogConfiguredExternalResearchRetriever(path) if path.is_file() else None


def _reddog_resident_architect_intent_id(
    *,
    principal_ref: str,
    foundup_id: str,
    work_focus: str,
    cycle_bucket: str = "",
) -> str:
    explicit = os.getenv("REDDOG_RESIDENT_ARCHITECT_INTENT_ID", "").strip()
    if explicit:
        return explicit
    payload = {
        "foundup_id": foundup_id,
        "principal_ref": principal_ref,
        "work_focus": work_focus,
    }
    if cycle_bucket:
        payload["cycle_bucket"] = cycle_bucket
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _reddog_resident_architect_auto_queue_profile(result: Any) -> str:
    if "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE" in os.environ:
        return ""
    if not getattr(result, "accepted", False):
        return ""
    if str(getattr(result, "architect_action", "") or "").strip().upper() != "FIX":
        return ""
    if int(getattr(result, "queue_candidate_count", 0) or 0) != 1:
        return ""

    try:
        from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
            PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR,
            RESIDENT_QUEUE_PROFILES,
        )
    except Exception:
        return ""

    raw = os.getenv(
        "REDDOG_RESIDENT_ARCHITECT_AUTO_QUEUE_PROFILE",
        PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR,
    ).strip().lower()
    if raw in {"0", "false", "off", "none"}:
        return ""
    if raw in {"", "1"}:
        raw = PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR
    return raw if raw in RESIDENT_QUEUE_PROFILES else ""


def run_reddog_resident_architect_durable_cycle_preflight(repo_root: Path) -> bool:
    """
    Optionally run one durable AgentDB resident RedDog architect cycle.

    This is the resident RedDog runtime bridge for main.py. It submits a
    reddog_intent.v1 request to the durable AgentDB cycle, lets OpenClaw claim
    read-only audit/research tasks, persists the backend architect
    determination, and exposes the intent ID for the downstream FIX promotion
    handoff. It performs no source mutation, shell work, worktree operations,
    PR creation, HoloIndex re-index, Hermes dispatch, PatternMemory promotion,
    or live FoundUp enqueue.

    Env:
        REDDOG_RESIDENT_ARCHITECT_PRODUCT_MODE=1           Auto-run resident cycle when low-level flag unset
        REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE            Explicit enable/disable override
        REDDOG_RESIDENT_ARCHITECT_CADENCE_HOURS=24         New intent cadence; 0 disables cadence
        REDDOG_RESIDENT_ARCHITECT_CYCLE_BUCKET             Optional explicit cadence bucket
        REDDOG_RESIDENT_ARCHITECT_NOW_ISO                  Optional deterministic runtime clock
        REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE_ENFORCED=0 Block startup if rejected
        REDDOG_RESIDENT_ARCHITECT_INTENT_ID                Optional stable intent ID
        REDDOG_RESIDENT_ARCHITECT_WORK_FOCUS               Work focus submitted to RedDog
        REDDOG_RESIDENT_ARCHITECT_PRINCIPAL_REF            Principal reference, default 012
        REDDOG_RESIDENT_ARCHITECT_FOUNDUP_ID               FoundUp scope, default foundups_agent
        REDDOG_RESIDENT_ARCHITECT_MAX_CLAIMS               Max OpenClaw claims, default 8
        REDDOG_RESIDENT_ARCHITECT_TIMEOUT_SECONDS          Cycle timeout, default 60
        REDDOG_RESIDENT_ARCHITECT_RETRY=0                  Retry failed/cancelled cycle
        REDDOG_RESIDENT_ARCHITECT_CANCEL=0                 Cancel running cycle
        REDDOG_RESIDENT_ARCHITECT_AUTO_FIX_HANDOFF=1        Auto-arm safe FIX handoff after accepted FIX
        REDDOG_RESIDENT_ARCHITECT_AUTO_QUEUE_PROFILE        Optional downstream queue profile, default draft-PR
        REDDOG_RESIDENT_BRAIN_CONTEXT=1                     Attach read-only Brain artifact state metadata
        REDDOG_RESIDENT_BRAIN_STATE_PATH                    Optional Brain artifact state JSON override
        REDDOG_RESIDENT_BREADCRUMBS_CONTEXT=1               Attach read-only AgentDB breadcrumb metadata
        REDDOG_RESIDENT_BREADCRUMBS_PATH                    Optional breadcrumb JSON override
        REDDOG_RESIDENT_WORKSPACE_MEMORY_NOTES_PATH         Optional workspace memory note JSON
        REDDOG_RESIDENT_MEMORY_MAX_RECORDS=20               Max breadcrumb/workspace records supplied
        REDDOG_EXTERNAL_RESEARCH_SNAPSHOT_PATH             Approved external snapshot JSON
        REDDOG_AUTHORITATIVE_WORK_STATE_PATH               Existing work-state JSON
        HOLOINDEX_FRESHNESS_RECEIPT                        Existing HoloIndex receipt
        HOLOINDEX_SSD_PATH                                 HoloIndex SSD path
    """

    if not _reddog_resident_architect_cycle_requested():
        logger.info("[REDDOG-RESIDENT-CYCLE] Startup preflight disabled")
        return True

    enforced = os.getenv("REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE_ENFORCED", "0") != "0"
    principal_ref = os.getenv("REDDOG_RESIDENT_ARCHITECT_PRINCIPAL_REF", "012").strip() or "012"
    foundup_id = os.getenv("REDDOG_RESIDENT_ARCHITECT_FOUNDUP_ID", "foundups_agent").strip() or "foundups_agent"
    work_focus = (
        os.getenv("REDDOG_RESIDENT_ARCHITECT_WORK_FOCUS", "").strip()
        or "main.py resident RedDog architect cycle"
    )
    explicit_intent_id = os.getenv("REDDOG_RESIDENT_ARCHITECT_INTENT_ID", "").strip()
    cycle_bucket = "" if explicit_intent_id else _reddog_resident_architect_cycle_bucket()
    intent_id = _reddog_resident_architect_intent_id(
        principal_ref=principal_ref,
        foundup_id=foundup_id,
        work_focus=work_focus,
        cycle_bucket=cycle_bucket,
    )
    brain_state = _reddog_resident_brain_state_from_artifacts()
    breadcrumbs = _reddog_resident_breadcrumbs_from_runtime(work_focus=work_focus, foundup_id=foundup_id)
    workspace_memory_notes = _reddog_resident_workspace_memory_notes_from_env()
    memory_context = {
        "brain_available": bool(brain_state),
        "brain_record_count": int(brain_state.get("record_count", 0)) if brain_state else 0,
        "breadcrumbs_count": len(breadcrumbs),
        "workspace_memory_notes_count": len(workspace_memory_notes),
    }
    memory_context["memory_context_digest"] = _reddog_digest_payload(memory_context)
    red_dog_intent = {
        "schema_version": "reddog_intent.v1",
        "intent_id": intent_id,
        "principal_ref": principal_ref,
        "foundup_id": foundup_id,
        "work_focus": work_focus,
        "cycle_bucket": cycle_bucket,
        "requested_authority": "read_only_audit",
        "origin": "main.py",
        "submits_executable_authority": False,
        "memory_context": memory_context,
    }

    try:
        from modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle import (
            run_reddog_resident_architect_durable_agentdb_cycle,
        )

        result = run_reddog_resident_architect_durable_agentdb_cycle(
            repo_root=repo_root,
            red_dog_intent=red_dog_intent,
            work_state_path=os.getenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", ""),
            holoindex_receipt_path=os.getenv("HOLOINDEX_FRESHNESS_RECEIPT", ""),
            holoindex_ssd_path=os.getenv("HOLOINDEX_SSD_PATH", ""),
            requested_operation="main_resident_architect_cycle",
            prompt_text=work_focus,
            breadcrumbs=breadcrumbs,
            brain_state=brain_state,
            workspace_memory_notes=workspace_memory_notes,
            external_research_retriever=_reddog_external_research_retriever_from_env(),
            max_claims=_reddog_positive_int_env("REDDOG_RESIDENT_ARCHITECT_MAX_CLAIMS", 8),
            timeout_seconds=_reddog_positive_int_env("REDDOG_RESIDENT_ARCHITECT_TIMEOUT_SECONDS", 60),
            cancel_requested=os.getenv("REDDOG_RESIDENT_ARCHITECT_CANCEL", "0") != "0",
            retry_requested=os.getenv("REDDOG_RESIDENT_ARCHITECT_RETRY", "0") != "0",
        )
    except Exception as exc:
        logger.error(f"[REDDOG-RESIDENT-CYCLE] Startup runtime failed: {exc}")
        if enforced:
            print(f"[REDDOG-RESIDENT-CYCLE] preflight=FAIL error={type(exc).__name__}")
            return False
        print(f"[REDDOG-RESIDENT-CYCLE] preflight=WARN error={type(exc).__name__}")
        return True

    status = "PASS" if result.accepted else "WARN"
    reasons = ",".join(result.rejection_reasons) if result.rejection_reasons else "(none)"
    completed = int(result.task_status_counts.get("completed", 0))
    auto_fix_handoff = (
        result.accepted
        and str(result.architect_action or "").strip().upper() == "FIX"
        and os.getenv("REDDOG_RESIDENT_ARCHITECT_AUTO_FIX_HANDOFF", "1") != "0"
        and "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF" not in os.environ
    )
    auto_queue_profile = _reddog_resident_architect_auto_queue_profile(result)
    print(
        f"[REDDOG-RESIDENT-CYCLE] preflight={status} status={result.status} "
        f"intent={result.intent_id} cycle={result.cycle_id} snapshot={result.snapshot_id or '(none)'} "
        f"swarm={result.swarm_id or '(none)'} tasks={len(result.task_ids)} completed={completed} "
        f"claims={len(result.openclaw_claims)} recovered={result.recovered_existing_cycle} "
        f"duplicate={result.duplicate_intent_reused} architect_action={result.architect_action or '(none)'} "
        f"architect_next_slice={result.architect_next_slice or '(none)'} "
        f"architect_determination={result.architect_determination_id or '(none)'} "
        f"queue_candidates={result.queue_candidate_count} auto_fix_handoff={auto_fix_handoff} "
        f"auto_queue_profile={auto_queue_profile or '(none)'} "
        f"brain_records={memory_context['brain_record_count']} "
        f"breadcrumbs={memory_context['breadcrumbs_count']} "
        f"workspace_memory={memory_context['workspace_memory_notes_count']} reasons={reasons}"
    )
    print(
        "[REDDOG-RESIDENT-CYCLE] "
        f"read_only_authority={result.read_only_authority_only} "
        f"no_shell={result.no_shell_command_executed} "
        f"no_repo_mutation={result.no_repo_mutation_performed} "
        f"no_holoindex_reindex={result.no_holoindex_reindex_performed} "
        f"no_hermes_dispatch={result.no_hermes_dispatch_performed} "
        f"no_worktree={result.no_worktree_operation_performed} "
        f"no_pr={result.no_pr_created} "
        f"no_pattern_memory={result.no_pattern_memory_promotion_performed} "
        f"no_live_foundup_enqueue={result.no_live_foundup_enqueue_performed}"
    )
    if result.accepted:
        os.environ["REDDOG_RESIDENT_ARCHITECT_INTENT_ID"] = result.intent_id
        if auto_fix_handoff:
            os.environ["REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF"] = "1"
        if auto_queue_profile:
            os.environ["REDDOG_RESIDENT_QUEUE_BINDING_PROFILE"] = auto_queue_profile
        return True

    if enforced:
        print("[REDDOG-RESIDENT-CYCLE] Startup blocked by REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE_ENFORCED=1")
        return False
    return True


def _reddog_startup_blocker_token(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in value.strip())
    return (cleaned or "unknown")[:64]


def _run_reddog_startup_blocker_diagnostic(repo_root: Path, *, component: str, stage: str) -> None:
    """
    Best-effort resident RedDog diagnostic for startup blockers.

    The blocker still blocks. This bridge only gives the resident architect a
    read-only opportunity to inspect preflight artifacts and queue a future
    governed repair path, with FIX handoff and queue profile disabled so a
    blocker diagnostic cannot advance the execution chain by itself.
    """
    if not _reddog_truthy_env_value(os.getenv("REDDOG_STARTUP_BLOCKER_DIAGNOSTIC", "1")):
        return
    if _reddog_truthy_env_value(os.getenv("REDDOG_STARTUP_BLOCKER_DIAGNOSTIC_ACTIVE", "0")):
        return

    component_token = _reddog_startup_blocker_token(component)
    stage_token = _reddog_startup_blocker_token(stage)
    work_focus = (
        f"Diagnose startup blocker {component_token} from {stage_token}. "
        "Read current alerts/preflight artifacts, Brain, Breadcrumbs, HoloIndex freshness, "
        "and authoritative work state. Apply WSP_15 and WSP_97. Recommend the next safe "
        "repair slice only. Do not mutate source, run shell commands, reindex HoloIndex, "
        "dispatch Hermes, create a worktree, open a PR, or enqueue live work."
    )

    override_keys = (
        "REDDOG_STARTUP_BLOCKER_DIAGNOSTIC_ACTIVE",
        "REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE",
        "REDDOG_RESIDENT_ARCHITECT_WORK_FOCUS",
        "REDDOG_RESIDENT_ARCHITECT_INTENT_ID",
        "REDDOG_RESIDENT_ARCHITECT_CYCLE_BUCKET",
        "REDDOG_RESIDENT_ARCHITECT_AUTO_FIX_HANDOFF",
        "REDDOG_RESIDENT_ARCHITECT_AUTO_QUEUE_PROFILE",
        "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF",
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE",
    )
    previous = {key: os.environ.get(key) for key in override_keys}
    try:
        os.environ["REDDOG_STARTUP_BLOCKER_DIAGNOSTIC_ACTIVE"] = "1"
        os.environ["REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE"] = "1"
        os.environ["REDDOG_RESIDENT_ARCHITECT_WORK_FOCUS"] = work_focus
        os.environ["REDDOG_RESIDENT_ARCHITECT_CYCLE_BUCKET"] = (
            f"startup_blocker:{component_token}:{stage_token}"
        )
        os.environ["REDDOG_RESIDENT_ARCHITECT_AUTO_FIX_HANDOFF"] = "0"
        os.environ["REDDOG_RESIDENT_ARCHITECT_AUTO_QUEUE_PROFILE"] = "0"
        os.environ.pop("REDDOG_RESIDENT_ARCHITECT_INTENT_ID", None)
        os.environ.pop("REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF", None)
        os.environ.pop("REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", None)
        result = run_reddog_resident_architect_durable_cycle_preflight(repo_root)
        print(
            "[REDDOG-STARTUP-BLOCKER] "
            f"diagnostic={'PASS' if result else 'WARN'} component={component_token} stage={stage_token}"
        )
    except Exception as exc:
        logger.debug(f"[REDDOG-STARTUP-BLOCKER] diagnostic skipped: {exc}")
        print(
            "[REDDOG-STARTUP-BLOCKER] "
            f"diagnostic=WARN component={component_token} stage={stage_token} error={type(exc).__name__}"
        )
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _handle_startup_blocker(repo_root: Path, *, component: str, stage: str) -> None:
    _run_reddog_startup_blocker_diagnostic(repo_root, component=component, stage=stage)


def run_reddog_architect_fix_promotion_preflight(repo_root: Path) -> bool:
    """
    Optionally promote a backend architect FIX determination into the resident queue.

    Env:
        REDDOG_ARCHITECT_FIX_PROMOTION_RUNTIME=0             Enable promotion bridge
        REDDOG_ARCHITECT_FIX_PROMOTION_ENFORCED=0            Block startup if rejected
        REDDOG_AUTHORITATIVE_WORK_STATE_PATH                 Existing work-state snapshot
        REDDOG_ARCHITECT_FIX_DETERMINATION_PATH              Outside-repo determination JSON
        REDDOG_MODEL_SELECTION_RECEIPT_PATH                  Outside-repo model receipt JSON
        REDDOG_MODEL_RUNTIME_BINDING_RECEIPT_PATH            Outside-repo runtime binding receipt JSON
        REDDOG_MEMEX_SUPPLY_RECEIPT_PATH                     Outside-repo Memex supply JSON
        REDDOG_AUTHORITY_PROFILE_SOURCE_PATH                 Outside-repo authority seed JSON
        REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH         Outside-repo promoted profile JSON
        REDDOG_RESIDENT_QUEUE_BINDING_PROFILE                Optional profile-derived output path
        REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF=0              Materialize determination/Memex from AgentDB cycle
        REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY=0             Materialize model selection receipt from signed evidence
        REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY=0       Materialize runtime binding receipt from signed evidence
        REDDOG_MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY=0     Materialize model AutoResearch plan from verified receipts
        REDDOG_MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_ENFORCED=0 Block startup if rejected
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY=0 Execute campaign fixture or configured gateway
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY_ENFORCED=0 Block startup if rejected
        REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN=0 Run gate->cycle->feedback chain
        REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_ENFORCED=0 Block startup if chain rejected
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY=0 Materialize campaign promotion-gate receipts
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_ENFORCED=0 Block startup if rejected
        REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_SUPPLY=0 Materialize campaign cycle receipt
        REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_SUPPLY_ENFORCED=0 Block startup if rejected
        REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION=0 Admit cycle receipt to feedback ledger
        REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_ENFORCED=0 Block startup if rejected
        REDDOG_MODEL_CATALOG_SNAPSHOT_PATH                   Outside-repo model catalog snapshot JSON
        REDDOG_MODEL_PRODUCTION_EVIDENCE_BUNDLE_PATH         Outside-repo signed production evidence bundle JSON
        REDDOG_MODEL_SELECTION_REQUIREMENTS_PATH             Outside-repo selection requirements JSON
        REDDOG_MODEL_BENCHMARK_EVIDENCE_RECEIPTS_PATH        Outside-repo benchmark evidence receipts JSON
        REDDOG_MODEL_PROMOTION_EVIDENCE_RECEIPTS_PATH        Outside-repo promotion evidence receipts JSON
        REDDOG_MODEL_RUNTIME_BINDING_POLICY_PATH             Outside-repo runtime binding policy JSON
        REDDOG_MODEL_AUTORESEARCH_PROMOTION_GATE_RECEIPTS_PATH Outside-repo promotion gate receipts JSON
        REDDOG_MODEL_AUTORESEARCH_CANDIDATE_POOL_PATH        Outside-repo benchmark candidate pool JSON
        REDDOG_MODEL_AUTORESEARCH_POLICY_PATH                Outside-repo AutoResearch policy JSON
        REDDOG_MODEL_AUTORESEARCH_FEEDBACK_RECORDS_PATH      Optional outside-repo feedback JSON/JSONL
        REDDOG_MODEL_AUTORESEARCH_PLAN_RECEIPT_PATH          Outside-repo AutoResearch plan output JSON
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_TASKS_PATH        Outside-repo held-out campaign tasks JSON
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMPTS_PATH      Outside-repo held-out prompt records JSON
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_OUTPUT_EVIDENCE_PATH Outside-repo raw output evidence JSONL for configured_gateway
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_RECEIPT_PATH Outside-repo campaign execution output JSON
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_VERIFIER_DIGEST   Verifier digest required by plan policy
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_HELD_OUT_SPLIT_ID Held-out split ID for benchmark receipt
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_RUNNER_MODE       deterministic_fixture or configured_gateway
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_VERIFIER_MODE     deterministic_fixture, exact_output_digest, or output_evidence_semantic
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_RUNNER_ALLOWED_PROVIDERS ; or , separated allowlist
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_RUNNER_MAX_PROMPT_CHARS Optional positive int
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_RUNNER_MAX_CALLS_PER_SAMPLE Optional positive int
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_RUNNER_MAX_COST_USD_PER_SAMPLE Optional positive float
        REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_POLICIES_PATH Outside-repo promotion policies JSON
        REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_PATH         Outside-repo AutoResearch cycle receipt JSON
        REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_PATH Outside-repo AutoResearch cycle feedback JSONL
        REDDOG_MODEL_AUTORESEARCH_PROMOTION_AUTHORITY_RECEIPT_ID Optional promotion authority receipt ID
        REDDOG_MODEL_AUTORESEARCH_SIGNED_PROMOTION_RECEIPT_ID Optional signed promotion receipt ID
        REDDOG_MODEL_EVIDENCE_TRUSTED_KEYS_PATH              Outside-repo trusted model evidence public keys JSON
        REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY=0 Materialize principal/snapshot from GitHub probe
        REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_ENFORCED=0 Block startup if rejected
        REDDOG_GITHUB_REPO_FULL_NAME                         GitHub repo full name for permission probe
        REDDOG_AUTHORITY_FOUNDUP_ID                          FoundUp scope for principal authority record
        REDDOG_PRINCIPAL_PUBLIC_KEY                          Principal public key, required; never inferred
        REDDOG_AUTHORITY_PROFILE_SEED_SUPPLY=0               Materialize authority seed from resident receipts
        REDDOG_AUTHORITY_PROFILE_SEED_SUPPLY_ENFORCED=0      Block startup if seed supply fails
        REDDOG_REDDOG_ID                                     Delegated RedDog id for authority seed
        REDDOG_REDDOG_PUBLIC_KEY                             RedDog public key for authority seed
        REDDOG_AUTHORITY_REQUESTED_OPERATION                  Authority operation, default feature_slice
        REDDOG_AUTHORITY_ALLOWED_PATHS                        ; or , separated path allowlist
        REDDOG_AUTHORITY_DENIED_PATHS                         ; or , separated path denylist
        REDDOG_AUTHORITY_REQUIRED_TESTS                       ; or , separated required tests
        REDDOG_AUTHORITY_REQUIRED_POLICY_GATES                ; or , separated policy gates
        REDDOG_AUTHORITY_CONSENSUS_RECEIPT_DIGEST             Required for high-authority operations
        REDDOG_AUTHORITY_SOVEREIGN_AUTHORIZATION_DIGEST       Required for high-authority operations
        REDDOG_AUTHORITY_PROFILE_SEED_NOW_EPOCH               Deterministic seed issue time for tests
        REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY=0    Materialize authority source from seed/principal/snapshot
        REDDOG_AUTHORITY_PROFILE_SEED_PATH                   Outside-repo authority seed input JSON
        REDDOG_PRINCIPAL_AUTHORITY_RECORD_PATH               Outside-repo principal authority record JSON
        REDDOG_PERMISSION_SNAPSHOT_PATH                      Outside-repo permission snapshot JSON
        REDDOG_RESIDENT_ARCHITECT_INTENT_ID                  Intent ID for the determined resident cycle
    """

    try:
        from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
            resident_queue_runtime_flag_enabled,
            resident_queue_runtime_file_path,
        )
    except Exception as exc:
        logger.error(f"[REDDOG-FIX-PROMOTION] profile helper import failed: {exc}")
        return True

    work_state_path = resident_queue_runtime_file_path(os.environ, repo_root, "REDDOG_AUTHORITATIVE_WORK_STATE_PATH")
    architect_determination_path = resident_queue_runtime_file_path(
        os.environ,
        repo_root,
        "REDDOG_ARCHITECT_FIX_DETERMINATION_PATH",
    )
    model_selection_receipt_path = resident_queue_runtime_file_path(
        os.environ,
        repo_root,
        "REDDOG_MODEL_SELECTION_RECEIPT_PATH",
    )
    model_runtime_binding_receipt_path = resident_queue_runtime_file_path(
        os.environ,
        repo_root,
        "REDDOG_MODEL_RUNTIME_BINDING_RECEIPT_PATH",
    )
    model_autoresearch_plan_receipt_path = resident_queue_runtime_file_path(
        os.environ,
        repo_root,
        "REDDOG_MODEL_AUTORESEARCH_PLAN_RECEIPT_PATH",
    )
    model_autoresearch_promotion_gate_receipts_path = resident_queue_runtime_file_path(
        os.environ,
        repo_root,
        "REDDOG_MODEL_AUTORESEARCH_PROMOTION_GATE_RECEIPTS_PATH",
    )
    model_autoresearch_campaign_execution_receipt_path = resident_queue_runtime_file_path(
        os.environ,
        repo_root,
        "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_RECEIPT_PATH",
    )
    model_autoresearch_campaign_promotion_policies_path = resident_queue_runtime_file_path(
        os.environ,
        repo_root,
        "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_POLICIES_PATH",
    )
    model_autoresearch_cycle_receipt_path = resident_queue_runtime_file_path(
        os.environ,
        repo_root,
        "REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_PATH",
    )
    model_autoresearch_cycle_feedback_ledger_path = resident_queue_runtime_file_path(
        os.environ,
        repo_root,
        "REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_PATH",
    )
    model_runtime_binding_receipt_path_supplied = bool(
        os.getenv("REDDOG_MODEL_RUNTIME_BINDING_RECEIPT_PATH", "").strip()
    )
    memex_supply_receipt_path = resident_queue_runtime_file_path(
        os.environ,
        repo_root,
        "REDDOG_MEMEX_SUPPLY_RECEIPT_PATH",
    )
    authority_profile_source_path = resident_queue_runtime_file_path(
        os.environ,
        repo_root,
        "REDDOG_AUTHORITY_PROFILE_SOURCE_PATH",
    )
    authority_profile_seed_path = resident_queue_runtime_file_path(
        os.environ,
        repo_root,
        "REDDOG_AUTHORITY_PROFILE_SEED_PATH",
    )
    authority_profile_path = resident_queue_runtime_file_path(
        os.environ,
        repo_root,
        "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH",
    )
    handoff_requested = resident_queue_runtime_flag_enabled(os.environ, "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF")
    handoff_enforced = os.getenv("REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF_ENFORCED", "0") != "0"
    if handoff_requested:
        try:
            from modules.communication.moltbot_bridge.src.reddog_resident_fix_promotion_artifact_handoff import (
                run_reddog_resident_fix_promotion_artifact_handoff,
            )

            handoff = run_reddog_resident_fix_promotion_artifact_handoff(
                repo_root=repo_root,
                intent_id=os.getenv("REDDOG_RESIDENT_ARCHITECT_INTENT_ID", ""),
                architect_determination_output_path=architect_determination_path,
                memex_supply_receipt_output_path=memex_supply_receipt_path,
            )
        except Exception as exc:
            logger.error(f"[REDDOG-FIX-HANDOFF] Startup handoff failed: {exc}")
            if handoff_enforced:
                print(f"[REDDOG-FIX-HANDOFF] preflight=FAIL error={type(exc).__name__}")
                return False
            print(f"[REDDOG-FIX-HANDOFF] preflight=WARN error={type(exc).__name__}")
            return True

        handoff_status = "PASS" if handoff.accepted else "WARN"
        handoff_reasons = ",".join(handoff.rejection_reasons) if handoff.rejection_reasons else "(none)"
        print(
            f"[REDDOG-FIX-HANDOFF] preflight={handoff_status} status={handoff.status} "
            f"architect_determination={handoff.architect_determination_id or '(none)'} "
            f"reasons={handoff_reasons}"
        )
        if handoff.accepted:
            if handoff.architect_determination_path:
                architect_determination_path = handoff.architect_determination_path
                os.environ["REDDOG_ARCHITECT_FIX_DETERMINATION_PATH"] = architect_determination_path
            if handoff.memex_supply_receipt_path:
                memex_supply_receipt_path = handoff.memex_supply_receipt_path
                os.environ["REDDOG_MEMEX_SUPPLY_RECEIPT_PATH"] = memex_supply_receipt_path
        elif handoff_enforced:
            print("[REDDOG-FIX-HANDOFF] Startup blocked by REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF_ENFORCED=1")
            return False

    model_supply_requested = resident_queue_runtime_flag_enabled(os.environ, "REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY")
    model_supply_enforced = os.getenv("REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY_ENFORCED", "0") != "0"
    if model_supply_requested:
        try:
            from modules.ai_intelligence.ai_gateway.src.model_selection_artifact_supply_bootstrap import (
                run_reddog_model_selection_artifact_supply_bootstrap,
            )

            raw_now = os.getenv("REDDOG_MODEL_SELECTION_EVIDENCE_NOW_EPOCH", "").strip()
            model_supply = run_reddog_model_selection_artifact_supply_bootstrap(
                repo_root=repo_root,
                catalog_snapshot_path=os.getenv("REDDOG_MODEL_CATALOG_SNAPSHOT_PATH", "") or None,
                evidence_bundle_path=os.getenv("REDDOG_MODEL_PRODUCTION_EVIDENCE_BUNDLE_PATH", "") or None,
                requirements_path=os.getenv("REDDOG_MODEL_SELECTION_REQUIREMENTS_PATH", "") or None,
                trusted_keys_path=os.getenv("REDDOG_MODEL_EVIDENCE_TRUSTED_KEYS_PATH", "") or None,
                output_path=model_selection_receipt_path,
                signature_verifier_backend=os.getenv(
                    "REDDOG_MODEL_EVIDENCE_SIGNATURE_VERIFIER_BACKEND",
                    "ed25519",
                ),
                now_epoch=(int(raw_now) if raw_now else None),
            )
        except Exception as exc:
            logger.error(f"[REDDOG-MODEL-SELECTION] Startup artifact supply failed: {exc}")
            if model_supply_enforced:
                print(f"[REDDOG-MODEL-SELECTION] preflight=FAIL error={type(exc).__name__}")
                return False
            print(f"[REDDOG-MODEL-SELECTION] preflight=WARN error={type(exc).__name__}")
            return True

        model_status = "PASS" if model_supply.accepted else "WARN"
        model_reasons = ",".join(model_supply.rejection_reasons) if model_supply.rejection_reasons else "(none)"
        print(
            f"[REDDOG-MODEL-SELECTION] preflight={model_status} status={model_supply.status} "
            f"receipt={model_supply.model_selection_receipt_id or '(none)'} reasons={model_reasons}"
        )
        if model_supply.accepted and model_supply.output_path:
            model_selection_receipt_path = model_supply.output_path
            os.environ["REDDOG_MODEL_SELECTION_RECEIPT_PATH"] = model_selection_receipt_path
        elif model_supply_enforced:
            print("[REDDOG-MODEL-SELECTION] Startup blocked by REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY_ENFORCED=1")
            return False

    runtime_binding_supply_requested = resident_queue_runtime_flag_enabled(
        os.environ,
        "REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY",
    )
    runtime_binding_supply_enforced = (
        os.getenv("REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_ENFORCED", "0") != "0"
    )
    if runtime_binding_supply_requested:
        try:
            from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_artifact_supply_bootstrap import (
                run_reddog_model_runtime_binding_artifact_supply_bootstrap,
            )

            raw_now = os.getenv(
                "REDDOG_MODEL_RUNTIME_BINDING_EVIDENCE_NOW_EPOCH",
                os.getenv("REDDOG_MODEL_SELECTION_EVIDENCE_NOW_EPOCH", ""),
            ).strip()
            runtime_binding_supply = run_reddog_model_runtime_binding_artifact_supply_bootstrap(
                repo_root=repo_root,
                catalog_snapshot_path=os.getenv("REDDOG_MODEL_CATALOG_SNAPSHOT_PATH", "") or None,
                model_selection_receipt_path=model_selection_receipt_path,
                benchmark_evidence_receipts_path=os.getenv(
                    "REDDOG_MODEL_BENCHMARK_EVIDENCE_RECEIPTS_PATH",
                    "",
                )
                or None,
                promotion_evidence_receipts_path=os.getenv(
                    "REDDOG_MODEL_PROMOTION_EVIDENCE_RECEIPTS_PATH",
                    "",
                )
                or None,
                evidence_bundle_path=os.getenv("REDDOG_MODEL_PRODUCTION_EVIDENCE_BUNDLE_PATH", "") or None,
                runtime_policy_path=os.getenv("REDDOG_MODEL_RUNTIME_BINDING_POLICY_PATH", "") or None,
                trusted_keys_path=os.getenv("REDDOG_MODEL_EVIDENCE_TRUSTED_KEYS_PATH", "") or None,
                output_path=model_runtime_binding_receipt_path,
                signature_verifier_backend=os.getenv(
                    "REDDOG_MODEL_EVIDENCE_SIGNATURE_VERIFIER_BACKEND",
                    "ed25519",
                ),
                now_epoch=(int(raw_now) if raw_now else None),
            )
        except Exception as exc:
            logger.error(f"[REDDOG-MODEL-RUNTIME-BINDING] Startup artifact supply failed: {exc}")
            if runtime_binding_supply_enforced:
                print(f"[REDDOG-MODEL-RUNTIME-BINDING] preflight=FAIL error={type(exc).__name__}")
                return False
            print(f"[REDDOG-MODEL-RUNTIME-BINDING] preflight=WARN error={type(exc).__name__}")
            return True

        runtime_binding_status = "PASS" if runtime_binding_supply.accepted else "WARN"
        runtime_binding_reasons = (
            ",".join(runtime_binding_supply.rejection_reasons)
            if runtime_binding_supply.rejection_reasons
            else "(none)"
        )
        print(
            f"[REDDOG-MODEL-RUNTIME-BINDING] preflight={runtime_binding_status} "
            f"status={runtime_binding_supply.status} "
            f"receipt={runtime_binding_supply.runtime_binding_receipt_id or '(none)'} "
            f"reasons={runtime_binding_reasons}"
        )
        if runtime_binding_supply.accepted and runtime_binding_supply.output_path:
            model_runtime_binding_receipt_path = runtime_binding_supply.output_path
            model_runtime_binding_receipt_path_supplied = True
            os.environ["REDDOG_MODEL_RUNTIME_BINDING_RECEIPT_PATH"] = model_runtime_binding_receipt_path
        elif runtime_binding_supply_enforced:
            print(
                "[REDDOG-MODEL-RUNTIME-BINDING] Startup blocked by "
                "REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_ENFORCED=1"
            )
            return False

    autoresearch_supply_requested = resident_queue_runtime_flag_enabled(
        os.environ,
        "REDDOG_MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY",
    )
    autoresearch_supply_enforced = (
        os.getenv("REDDOG_MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_ENFORCED", "0") != "0"
    )
    if autoresearch_supply_requested:
        try:
            from modules.ai_intelligence.ai_gateway.src.model_autoresearch_plan_artifact_supply_bootstrap import (
                run_reddog_model_autoresearch_plan_artifact_supply_bootstrap,
            )

            configured_feedback_path = os.getenv("REDDOG_MODEL_AUTORESEARCH_FEEDBACK_RECORDS_PATH", "").strip()
            model_autoresearch_feedback_records_path = configured_feedback_path or None
            if model_autoresearch_feedback_records_path is None:
                cycle_feedback_path = Path(model_autoresearch_cycle_feedback_ledger_path)
                if cycle_feedback_path.exists() and cycle_feedback_path.is_file():
                    model_autoresearch_feedback_records_path = str(cycle_feedback_path)

            autoresearch_supply = run_reddog_model_autoresearch_plan_artifact_supply_bootstrap(
                repo_root=repo_root,
                promotion_gate_receipts_path=model_autoresearch_promotion_gate_receipts_path or None,
                candidate_pool_path=os.getenv("REDDOG_MODEL_AUTORESEARCH_CANDIDATE_POOL_PATH", "") or None,
                policy_path=os.getenv("REDDOG_MODEL_AUTORESEARCH_POLICY_PATH", "") or None,
                feedback_records_path=model_autoresearch_feedback_records_path,
                output_path=model_autoresearch_plan_receipt_path,
            )
        except Exception as exc:
            logger.error(f"[REDDOG-MODEL-AUTORESEARCH] Startup artifact supply failed: {exc}")
            if autoresearch_supply_enforced:
                print(f"[REDDOG-MODEL-AUTORESEARCH] preflight=FAIL error={type(exc).__name__}")
                return False
            print(f"[REDDOG-MODEL-AUTORESEARCH] preflight=WARN error={type(exc).__name__}")
            return True

        autoresearch_status = "PASS" if autoresearch_supply.accepted else "WARN"
        autoresearch_reasons = (
            ",".join(autoresearch_supply.rejection_reasons)
            if autoresearch_supply.rejection_reasons
            else "(none)"
        )
        print(
            f"[REDDOG-MODEL-AUTORESEARCH] preflight={autoresearch_status} "
            f"status={autoresearch_supply.status} "
            f"receipt={autoresearch_supply.plan_receipt_id or '(none)'} "
            f"campaign_items={autoresearch_supply.campaign_item_count} "
            f"reasons={autoresearch_reasons}"
        )
        if autoresearch_supply.accepted and autoresearch_supply.output_path:
            model_autoresearch_plan_receipt_path = autoresearch_supply.output_path
            os.environ["REDDOG_MODEL_AUTORESEARCH_PLAN_RECEIPT_PATH"] = model_autoresearch_plan_receipt_path
        elif autoresearch_supply_enforced:
            print(
                "[REDDOG-MODEL-AUTORESEARCH] Startup blocked by "
                "REDDOG_MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_ENFORCED=1"
            )
            return False

    autoresearch_campaign_requested = resident_queue_runtime_flag_enabled(
        os.environ,
        "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY",
    )
    autoresearch_campaign_enforced = (
        os.getenv("REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY_ENFORCED", "0") != "0"
    )
    if autoresearch_campaign_requested:
        try:
            from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution_artifact_supply_bootstrap import (
                run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap,
            )

            autoresearch_campaign = (
                run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap(
                    repo_root=repo_root,
                    plan_receipt_path=model_autoresearch_plan_receipt_path,
                    candidate_pool_path=os.getenv("REDDOG_MODEL_AUTORESEARCH_CANDIDATE_POOL_PATH", "") or None,
                    tasks_path=os.getenv("REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_TASKS_PATH", "") or None,
                    prompt_records_path=os.getenv("REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMPTS_PATH", "") or None,
                    output_evidence_path=os.getenv(
                        "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_OUTPUT_EVIDENCE_PATH",
                        "",
                    )
                    or None,
                    output_path=model_autoresearch_campaign_execution_receipt_path,
                    verifier_digest=os.getenv("REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_VERIFIER_DIGEST", ""),
                    held_out_split_id=os.getenv("REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_HELD_OUT_SPLIT_ID", ""),
                    runner_mode=os.getenv(
                        "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_RUNNER_MODE",
                        "deterministic_fixture",
                    ),
                    verifier_mode=os.getenv(
                        "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_VERIFIER_MODE",
                        "deterministic_fixture",
                    ),
                    runner_allowed_providers=os.getenv(
                        "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_RUNNER_ALLOWED_PROVIDERS",
                        "",
                    ),
                    runner_max_prompt_chars=os.getenv(
                        "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_RUNNER_MAX_PROMPT_CHARS",
                        "20000",
                    ),
                    runner_max_calls_per_sample=os.getenv(
                        "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_RUNNER_MAX_CALLS_PER_SAMPLE",
                        "4",
                    ),
                    runner_max_cost_estimate_usd_per_sample=os.getenv(
                        "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_RUNNER_MAX_COST_USD_PER_SAMPLE",
                        "1.0",
                    ),
                )
            )
        except Exception as exc:
            logger.error(f"[REDDOG-MODEL-AUTORESEARCH-CAMPAIGN] Startup artifact supply failed: {exc}")
            if autoresearch_campaign_enforced:
                print(f"[REDDOG-MODEL-AUTORESEARCH-CAMPAIGN] preflight=FAIL error={type(exc).__name__}")
                return False
            print(f"[REDDOG-MODEL-AUTORESEARCH-CAMPAIGN] preflight=WARN error={type(exc).__name__}")
            return True

        campaign_status = "PASS" if autoresearch_campaign.accepted else "WARN"
        campaign_reasons = (
            ",".join(autoresearch_campaign.rejection_reasons)
            if autoresearch_campaign.rejection_reasons
            else "(none)"
        )
        print(
            f"[REDDOG-MODEL-AUTORESEARCH-CAMPAIGN] preflight={campaign_status} "
            f"status={autoresearch_campaign.status} "
            f"receipt={autoresearch_campaign.execution_receipt_id or '(none)'} "
            f"tasks={autoresearch_campaign.task_count} "
            f"reasons={campaign_reasons}"
        )
        if autoresearch_campaign.accepted and autoresearch_campaign.output_path:
            model_autoresearch_campaign_execution_receipt_path = autoresearch_campaign.output_path
            os.environ["REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_RECEIPT_PATH"] = (
                model_autoresearch_campaign_execution_receipt_path
            )
        elif autoresearch_campaign_enforced:
            print(
                "[REDDOG-MODEL-AUTORESEARCH-CAMPAIGN] Startup blocked by "
                "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY_ENFORCED=1"
            )
            return False

    autoresearch_chain_requested = resident_queue_runtime_flag_enabled(
        os.environ,
        "REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN",
    )
    autoresearch_chain_enforced = (
        os.getenv("REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_ENFORCED", "0") != "0"
    )
    if autoresearch_chain_requested:
        try:
            from modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_feedback_chain_bootstrap import (
                run_reddog_model_autoresearch_cycle_feedback_chain_bootstrap,
            )

            autoresearch_chain = run_reddog_model_autoresearch_cycle_feedback_chain_bootstrap(
                repo_root=repo_root,
                plan_receipt_path=model_autoresearch_plan_receipt_path,
                campaign_execution_receipt_path=model_autoresearch_campaign_execution_receipt_path,
                promotion_policies_path=model_autoresearch_campaign_promotion_policies_path or None,
                promotion_gate_output_path=model_autoresearch_promotion_gate_receipts_path,
                cycle_receipt_output_path=model_autoresearch_cycle_receipt_path,
                feedback_ledger_output_path=model_autoresearch_cycle_feedback_ledger_path,
                promotion_authority_receipt_id=os.getenv(
                    "REDDOG_MODEL_AUTORESEARCH_PROMOTION_AUTHORITY_RECEIPT_ID",
                    "",
                )
                or None,
                signed_promotion_receipt_id=os.getenv(
                    "REDDOG_MODEL_AUTORESEARCH_SIGNED_PROMOTION_RECEIPT_ID",
                    "",
                )
                or None,
            )
        except Exception as exc:
            logger.error(f"[REDDOG-MODEL-AUTORESEARCH-CHAIN] Startup chain failed: {exc}")
            if autoresearch_chain_enforced:
                print(f"[REDDOG-MODEL-AUTORESEARCH-CHAIN] preflight=FAIL error={type(exc).__name__}")
                return False
            print(f"[REDDOG-MODEL-AUTORESEARCH-CHAIN] preflight=WARN error={type(exc).__name__}")
            return True

        chain_status = "PASS" if autoresearch_chain.accepted else "WARN"
        chain_reasons = (
            ",".join(autoresearch_chain.rejection_reasons)
            if autoresearch_chain.rejection_reasons
            else "(none)"
        )
        print(
            f"[REDDOG-MODEL-AUTORESEARCH-CHAIN] preflight={chain_status} "
            f"status={autoresearch_chain.status} "
            f"gate={autoresearch_chain.promotion_gate_supply_receipt_id or '(none)'} "
            f"cycle={autoresearch_chain.cycle_receipt_id or '(none)'} "
            f"admission={autoresearch_chain.feedback_admission_id or '(none)'} "
            f"record={autoresearch_chain.feedback_record_id or '(none)'} "
            f"reasons={chain_reasons}"
        )
        if autoresearch_chain.accepted:
            if autoresearch_chain.promotion_gate_output_path:
                model_autoresearch_promotion_gate_receipts_path = autoresearch_chain.promotion_gate_output_path
                os.environ["REDDOG_MODEL_AUTORESEARCH_PROMOTION_GATE_RECEIPTS_PATH"] = (
                    model_autoresearch_promotion_gate_receipts_path
                )
            if autoresearch_chain.cycle_receipt_output_path:
                model_autoresearch_cycle_receipt_path = autoresearch_chain.cycle_receipt_output_path
                os.environ["REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_PATH"] = model_autoresearch_cycle_receipt_path
            if autoresearch_chain.feedback_ledger_output_path:
                model_autoresearch_cycle_feedback_ledger_path = autoresearch_chain.feedback_ledger_output_path
                os.environ["REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_PATH"] = (
                    model_autoresearch_cycle_feedback_ledger_path
                )
        elif autoresearch_chain_enforced:
            print(
                "[REDDOG-MODEL-AUTORESEARCH-CHAIN] Startup blocked by "
                "REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CHAIN_ENFORCED=1"
            )
            return False

    autoresearch_campaign_gate_requested = resident_queue_runtime_flag_enabled(
        os.environ,
        "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY",
    )
    autoresearch_campaign_gate_enforced = (
        os.getenv("REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_ENFORCED", "0") != "0"
    )
    if autoresearch_campaign_gate_requested:
        try:
            from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_promotion_gate_supply_bootstrap import (
                run_reddog_model_autoresearch_campaign_promotion_gate_supply_bootstrap,
            )

            autoresearch_campaign_gate = (
                run_reddog_model_autoresearch_campaign_promotion_gate_supply_bootstrap(
                    repo_root=repo_root,
                    campaign_execution_receipt_path=model_autoresearch_campaign_execution_receipt_path,
                    promotion_policies_path=model_autoresearch_campaign_promotion_policies_path or None,
                    output_path=model_autoresearch_promotion_gate_receipts_path,
                    promotion_authority_receipt_id=os.getenv(
                        "REDDOG_MODEL_AUTORESEARCH_PROMOTION_AUTHORITY_RECEIPT_ID",
                        "",
                    )
                    or None,
                    signed_promotion_receipt_id=os.getenv(
                        "REDDOG_MODEL_AUTORESEARCH_SIGNED_PROMOTION_RECEIPT_ID",
                        "",
                    )
                    or None,
                )
            )
        except Exception as exc:
            logger.error(f"[REDDOG-MODEL-AUTORESEARCH-GATE] Startup artifact supply failed: {exc}")
            if autoresearch_campaign_gate_enforced:
                print(f"[REDDOG-MODEL-AUTORESEARCH-GATE] preflight=FAIL error={type(exc).__name__}")
                return False
            print(f"[REDDOG-MODEL-AUTORESEARCH-GATE] preflight=WARN error={type(exc).__name__}")
            return True

        gate_status = "PASS" if autoresearch_campaign_gate.accepted else "WARN"
        gate_reasons = (
            ",".join(autoresearch_campaign_gate.rejection_reasons)
            if autoresearch_campaign_gate.rejection_reasons
            else "(none)"
        )
        print(
            f"[REDDOG-MODEL-AUTORESEARCH-GATE] preflight={gate_status} "
            f"status={autoresearch_campaign_gate.status} "
            f"receipt={autoresearch_campaign_gate.supply_receipt_id or '(none)'} "
            f"gates={len(autoresearch_campaign_gate.promotion_gate_receipt_ids)} "
            f"reasons={gate_reasons}"
        )
        if autoresearch_campaign_gate.accepted and autoresearch_campaign_gate.output_path:
            model_autoresearch_promotion_gate_receipts_path = autoresearch_campaign_gate.output_path
            os.environ["REDDOG_MODEL_AUTORESEARCH_PROMOTION_GATE_RECEIPTS_PATH"] = (
                model_autoresearch_promotion_gate_receipts_path
            )
        elif autoresearch_campaign_gate_enforced:
            print(
                "[REDDOG-MODEL-AUTORESEARCH-GATE] Startup blocked by "
                "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_ENFORCED=1"
            )
            return False

    autoresearch_cycle_requested = resident_queue_runtime_flag_enabled(
        os.environ,
        "REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_SUPPLY",
    )
    autoresearch_cycle_enforced = (
        os.getenv("REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_SUPPLY_ENFORCED", "0") != "0"
    )
    if autoresearch_cycle_requested:
        try:
            from modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_receipt_supply_bootstrap import (
                run_reddog_model_autoresearch_cycle_receipt_supply_bootstrap,
            )

            autoresearch_cycle = run_reddog_model_autoresearch_cycle_receipt_supply_bootstrap(
                repo_root=repo_root,
                plan_receipt_path=model_autoresearch_plan_receipt_path,
                campaign_execution_receipt_path=model_autoresearch_campaign_execution_receipt_path,
                promotion_gate_supply_receipt_path=model_autoresearch_promotion_gate_receipts_path,
                output_path=model_autoresearch_cycle_receipt_path,
            )
        except Exception as exc:
            logger.error(f"[REDDOG-MODEL-AUTORESEARCH-CYCLE] Startup artifact supply failed: {exc}")
            if autoresearch_cycle_enforced:
                print(f"[REDDOG-MODEL-AUTORESEARCH-CYCLE] preflight=FAIL error={type(exc).__name__}")
                return False
            print(f"[REDDOG-MODEL-AUTORESEARCH-CYCLE] preflight=WARN error={type(exc).__name__}")
            return True

        cycle_status = "PASS" if autoresearch_cycle.accepted else "WARN"
        cycle_reasons = (
            ",".join(autoresearch_cycle.rejection_reasons)
            if autoresearch_cycle.rejection_reasons
            else "(none)"
        )
        print(
            f"[REDDOG-MODEL-AUTORESEARCH-CYCLE] preflight={cycle_status} "
            f"status={autoresearch_cycle.status} "
            f"receipt={autoresearch_cycle.cycle_receipt_id or '(none)'} "
            f"plan={autoresearch_cycle.source_plan_receipt_id or '(none)'} "
            f"execution={autoresearch_cycle.campaign_execution_receipt_id or '(none)'} "
            f"gate={autoresearch_cycle.promotion_gate_supply_receipt_id or '(none)'} "
            f"reasons={cycle_reasons}"
        )
        if autoresearch_cycle.accepted and autoresearch_cycle.output_path:
            model_autoresearch_cycle_receipt_path = autoresearch_cycle.output_path
            os.environ["REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_PATH"] = model_autoresearch_cycle_receipt_path
        elif autoresearch_cycle_enforced:
            print(
                "[REDDOG-MODEL-AUTORESEARCH-CYCLE] Startup blocked by "
                "REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_SUPPLY_ENFORCED=1"
            )
            return False

    autoresearch_cycle_feedback_requested = resident_queue_runtime_flag_enabled(
        os.environ,
        "REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION",
    )
    autoresearch_cycle_feedback_enforced = (
        os.getenv("REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_ENFORCED", "0") != "0"
    )
    if autoresearch_cycle_feedback_requested:
        try:
            from modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_feedback_ledger_admission_bootstrap import (
                run_reddog_model_autoresearch_cycle_feedback_ledger_admission_bootstrap,
            )

            autoresearch_cycle_feedback = (
                run_reddog_model_autoresearch_cycle_feedback_ledger_admission_bootstrap(
                    repo_root=repo_root,
                    plan_receipt_path=model_autoresearch_plan_receipt_path,
                    cycle_receipt_path=model_autoresearch_cycle_receipt_path,
                    output_path=model_autoresearch_cycle_feedback_ledger_path,
                )
            )
        except Exception as exc:
            logger.error(f"[REDDOG-MODEL-AUTORESEARCH-CYCLE-FEEDBACK] Startup admission failed: {exc}")
            if autoresearch_cycle_feedback_enforced:
                print(f"[REDDOG-MODEL-AUTORESEARCH-CYCLE-FEEDBACK] preflight=FAIL error={type(exc).__name__}")
                return False
            print(f"[REDDOG-MODEL-AUTORESEARCH-CYCLE-FEEDBACK] preflight=WARN error={type(exc).__name__}")
            return True

        cycle_feedback_status = "PASS" if autoresearch_cycle_feedback.accepted else "WARN"
        cycle_feedback_reasons = (
            ",".join(autoresearch_cycle_feedback.rejection_reasons)
            if autoresearch_cycle_feedback.rejection_reasons
            else "(none)"
        )
        print(
            f"[REDDOG-MODEL-AUTORESEARCH-CYCLE-FEEDBACK] preflight={cycle_feedback_status} "
            f"status={autoresearch_cycle_feedback.status} "
            f"admission={autoresearch_cycle_feedback.admission_id or '(none)'} "
            f"cycle={autoresearch_cycle_feedback.cycle_receipt_id or '(none)'} "
            f"record={autoresearch_cycle_feedback.feedback_record_id or '(none)'} "
            f"reasons={cycle_feedback_reasons}"
        )
        if autoresearch_cycle_feedback.accepted and autoresearch_cycle_feedback.output_path:
            model_autoresearch_cycle_feedback_ledger_path = autoresearch_cycle_feedback.output_path
            os.environ["REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_PATH"] = (
                model_autoresearch_cycle_feedback_ledger_path
            )
        elif autoresearch_cycle_feedback_enforced:
            print(
                "[REDDOG-MODEL-AUTORESEARCH-CYCLE-FEEDBACK] Startup blocked by "
                "REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_ENFORCED=1"
            )
            return False

    principal_snapshot_supply_requested = resident_queue_runtime_flag_enabled(
        os.environ,
        "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY",
    )
    principal_snapshot_supply_enforced = (
        os.getenv("REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_ENFORCED", "0") != "0"
    )
    if principal_snapshot_supply_requested:
        try:
            from modules.communication.moltbot_bridge.src.reddog_github_principal_permission_snapshot_supply_bootstrap import (
                run_reddog_github_principal_permission_snapshot_supply_bootstrap,
            )

            ttl_raw = os.getenv("REDDOG_GITHUB_PERMISSION_SNAPSHOT_TTL_SECONDS", "").strip()
            principal_snapshot_supply = run_reddog_github_principal_permission_snapshot_supply_bootstrap(
                repo_root=repo_root,
                repo_full_name=os.getenv("REDDOG_GITHUB_REPO_FULL_NAME", "FOUNDUPS/Foundups-Agent"),
                foundup_id=os.getenv("REDDOG_AUTHORITY_FOUNDUP_ID", ""),
                principal_public_key=os.getenv("REDDOG_PRINCIPAL_PUBLIC_KEY", ""),
                principal_authority_record_output_path=resident_queue_runtime_file_path(
                    os.environ,
                    repo_root,
                    "REDDOG_PRINCIPAL_AUTHORITY_RECORD_PATH",
                ),
                permission_snapshot_output_path=resident_queue_runtime_file_path(
                    os.environ,
                    repo_root,
                    "REDDOG_PERMISSION_SNAPSHOT_PATH",
                ),
                principal_provider=os.getenv("REDDOG_PRINCIPAL_PROVIDER", "github"),
                reward_account=os.getenv("REDDOG_PRINCIPAL_REWARD_ACCOUNT", "") or None,
                owner_dae=os.getenv("REDDOG_PRINCIPAL_OWNER_DAE", "") or None,
                principal_wallet=os.getenv("REDDOG_PRINCIPAL_WALLET", "") or None,
                now_iso=os.getenv("REDDOG_GITHUB_PERMISSION_SNAPSHOT_NOW_ISO", "") or None,
                ttl_seconds=(int(ttl_raw) if ttl_raw else 300),
            )
        except Exception as exc:
            logger.error(f"[REDDOG-GITHUB-PRINCIPAL] Startup snapshot supply failed: {exc}")
            if principal_snapshot_supply_enforced:
                print(f"[REDDOG-GITHUB-PRINCIPAL] preflight=FAIL error={type(exc).__name__}")
                return False
            print(f"[REDDOG-GITHUB-PRINCIPAL] preflight=WARN error={type(exc).__name__}")
            return True

        principal_status = "PASS" if principal_snapshot_supply.accepted else "WARN"
        principal_reasons = (
            ",".join(principal_snapshot_supply.rejection_reasons)
            if principal_snapshot_supply.rejection_reasons
            else "(none)"
        )
        print(
            f"[REDDOG-GITHUB-PRINCIPAL] preflight={principal_status} "
            f"status={principal_snapshot_supply.status} "
            f"principal={principal_snapshot_supply.principal_id or '(none)'} "
            f"permission={principal_snapshot_supply.permission_snapshot_digest or '(none)'} "
            f"reasons={principal_reasons}"
        )
        if principal_snapshot_supply.accepted:
            if principal_snapshot_supply.principal_authority_record_path:
                os.environ["REDDOG_PRINCIPAL_AUTHORITY_RECORD_PATH"] = (
                    principal_snapshot_supply.principal_authority_record_path
                )
            if principal_snapshot_supply.permission_snapshot_path:
                os.environ["REDDOG_PERMISSION_SNAPSHOT_PATH"] = principal_snapshot_supply.permission_snapshot_path
        elif principal_snapshot_supply_enforced:
            print(
                "[REDDOG-GITHUB-PRINCIPAL] Startup blocked by "
                "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_ENFORCED=1"
            )
            return False

    seed_supply_requested = resident_queue_runtime_flag_enabled(
        os.environ,
        "REDDOG_AUTHORITY_PROFILE_SEED_SUPPLY",
    )
    seed_supply_enforced = os.getenv("REDDOG_AUTHORITY_PROFILE_SEED_SUPPLY_ENFORCED", "0") != "0"
    if seed_supply_requested:
        try:
            from modules.communication.moltbot_bridge.src.reddog_authority_profile_seed_supply_bootstrap import (
                run_reddog_authority_profile_seed_supply_bootstrap,
            )

            raw_now = os.getenv("REDDOG_AUTHORITY_PROFILE_SEED_NOW_EPOCH", "").strip()
            identity_ttl_raw = os.getenv("REDDOG_AUTHORITY_IDENTITY_TTL_SECONDS", "").strip()
            work_ttl_raw = os.getenv("REDDOG_AUTHORITY_WORK_TTL_SECONDS", "").strip()
            seed_supply = run_reddog_authority_profile_seed_supply_bootstrap(
                repo_root=repo_root,
                architect_determination_path=architect_determination_path,
                model_selection_receipt_path=model_selection_receipt_path,
                memex_supply_receipt_path=memex_supply_receipt_path,
                principal_authority_record_path=os.getenv("REDDOG_PRINCIPAL_AUTHORITY_RECORD_PATH", "") or None,
                permission_snapshot_path=os.getenv("REDDOG_PERMISSION_SNAPSHOT_PATH", "") or None,
                output_path=authority_profile_seed_path,
                reddog_id=os.getenv("REDDOG_REDDOG_ID", "reddog:architect"),
                reddog_public_key=os.getenv("REDDOG_REDDOG_PUBLIC_KEY", ""),
                now_epoch=(int(raw_now) if raw_now else None),
                foundup_id=os.getenv("REDDOG_AUTHORITY_FOUNDUP_ID", "") or None,
                requested_operation=os.getenv("REDDOG_AUTHORITY_REQUESTED_OPERATION", "feature_slice"),
                allowed_paths=_reddog_env_sequence("REDDOG_AUTHORITY_ALLOWED_PATHS"),
                denied_paths=_reddog_env_sequence("REDDOG_AUTHORITY_DENIED_PATHS"),
                valve_state_required=os.getenv("REDDOG_AUTHORITY_VALVE_STATE_REQUIRED", ""),
                key_epoch=os.getenv("REDDOG_AUTHORITY_KEY_EPOCH", "epoch-1"),
                required_tests=_reddog_env_sequence("REDDOG_AUTHORITY_REQUIRED_TESTS"),
                required_policy_gates=_reddog_env_sequence("REDDOG_AUTHORITY_REQUIRED_POLICY_GATES"),
                consensus_receipt_digest=os.getenv("REDDOG_AUTHORITY_CONSENSUS_RECEIPT_DIGEST", "") or None,
                sovereign_authorization_digest=(
                    os.getenv("REDDOG_AUTHORITY_SOVEREIGN_AUTHORIZATION_DIGEST", "") or None
                ),
                identity_ttl_seconds=(int(identity_ttl_raw) if identity_ttl_raw else 3600),
                work_authority_ttl_seconds=(int(work_ttl_raw) if work_ttl_raw else 900),
            )
        except Exception as exc:
            logger.error(f"[REDDOG-AUTHORITY-SEED] Startup seed supply failed: {exc}")
            if seed_supply_enforced:
                print(f"[REDDOG-AUTHORITY-SEED] preflight=FAIL error={type(exc).__name__}")
                return False
            print(f"[REDDOG-AUTHORITY-SEED] preflight=WARN error={type(exc).__name__}")
            return True

        seed_status = "PASS" if seed_supply.accepted else "WARN"
        seed_reasons = ",".join(seed_supply.rejection_reasons) if seed_supply.rejection_reasons else "(none)"
        print(
            f"[REDDOG-AUTHORITY-SEED] preflight={seed_status} status={seed_supply.status} "
            f"receipt={seed_supply.seed_supply_receipt_id or '(none)'} reasons={seed_reasons}"
        )
        if seed_supply.accepted and seed_supply.output_path:
            authority_profile_seed_path = seed_supply.output_path
            os.environ["REDDOG_AUTHORITY_PROFILE_SEED_PATH"] = authority_profile_seed_path
        elif seed_supply_enforced:
            print("[REDDOG-AUTHORITY-SEED] Startup blocked by REDDOG_AUTHORITY_PROFILE_SEED_SUPPLY_ENFORCED=1")
            return False

    authority_supply_requested = resident_queue_runtime_flag_enabled(
        os.environ,
        "REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY",
    )
    authority_supply_enforced = os.getenv("REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY_ENFORCED", "0") != "0"
    if authority_supply_requested:
        try:
            from modules.communication.moltbot_bridge.src.reddog_authority_profile_source_artifact_supply_bootstrap import (
                run_reddog_authority_profile_source_artifact_supply_bootstrap,
            )

            raw_now = os.getenv("REDDOG_AUTHORITY_PROFILE_SOURCE_NOW_EPOCH", "").strip()
            authority_supply = run_reddog_authority_profile_source_artifact_supply_bootstrap(
                repo_root=repo_root,
                authority_seed_path=authority_profile_seed_path or None,
                principal_authority_record_path=os.getenv("REDDOG_PRINCIPAL_AUTHORITY_RECORD_PATH", "") or None,
                permission_snapshot_path=os.getenv("REDDOG_PERMISSION_SNAPSHOT_PATH", "") or None,
                output_path=authority_profile_source_path,
                now_epoch=(int(raw_now) if raw_now else None),
            )
        except Exception as exc:
            logger.error(f"[REDDOG-AUTHORITY-SOURCE] Startup artifact supply failed: {exc}")
            if authority_supply_enforced:
                print(f"[REDDOG-AUTHORITY-SOURCE] preflight=FAIL error={type(exc).__name__}")
                return False
            print(f"[REDDOG-AUTHORITY-SOURCE] preflight=WARN error={type(exc).__name__}")
            return True

        authority_status = "PASS" if authority_supply.accepted else "WARN"
        authority_reasons = (
            ",".join(authority_supply.rejection_reasons) if authority_supply.rejection_reasons else "(none)"
        )
        print(
            f"[REDDOG-AUTHORITY-SOURCE] preflight={authority_status} status={authority_supply.status} "
            f"receipt={authority_supply.authority_profile_source_receipt_id or '(none)'} "
            f"reasons={authority_reasons}"
        )
        if authority_supply.accepted and authority_supply.output_path:
            authority_profile_source_path = authority_supply.output_path
            os.environ["REDDOG_AUTHORITY_PROFILE_SOURCE_PATH"] = authority_profile_source_path
        elif authority_supply_enforced:
            print(
                "[REDDOG-AUTHORITY-SOURCE] Startup blocked by "
                "REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY_ENFORCED=1"
            )
            return False

    required_inputs_present = all(
        str(value or "").strip()
        for value in (
            work_state_path,
            architect_determination_path,
            model_selection_receipt_path,
            memex_supply_receipt_path,
            authority_profile_source_path,
        )
    ) and bool(authority_profile_path)
    raw_requested = os.getenv("REDDOG_ARCHITECT_FIX_PROMOTION_RUNTIME")
    requested = raw_requested == "1" or (raw_requested is None and required_inputs_present)
    if not requested:
        logger.info("[REDDOG-FIX-PROMOTION] Startup promotion bridge disabled")
        return True

    enforced = os.getenv("REDDOG_ARCHITECT_FIX_PROMOTION_ENFORCED", "0") != "0"
    try:
        from modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap import (
            run_reddog_main_architect_fix_promotion_bootstrap,
        )

        result = run_reddog_main_architect_fix_promotion_bootstrap(
            repo_root=repo_root,
            work_state_path=work_state_path,
            architect_determination_path=architect_determination_path,
            model_selection_receipt_path=model_selection_receipt_path,
            model_runtime_binding_receipt_path=(
                model_runtime_binding_receipt_path if model_runtime_binding_receipt_path_supplied else None
            ),
            memex_supply_receipt_path=memex_supply_receipt_path,
            authority_profile_source_path=authority_profile_source_path,
            authority_profile_output_path=authority_profile_path,
            worker_id=os.getenv(
                "REDDOG_ARCHITECT_FIX_PROMOTION_WORKER_ID",
                "reddog-main-architect-fix-promotion",
            ),
        )
    except Exception as exc:
        logger.error(f"[REDDOG-FIX-PROMOTION] Startup promotion bridge failed: {exc}")
        if enforced:
            print(f"[REDDOG-FIX-PROMOTION] preflight=FAIL error={type(exc).__name__}")
            return False
        print(f"[REDDOG-FIX-PROMOTION] preflight=WARN error={type(exc).__name__}")
        return True

    status = "PASS" if result.accepted else "WARN"
    reasons = ",".join(result.rejection_reasons) if result.rejection_reasons else "(none)"
    print(
        f"[REDDOG-FIX-PROMOTION] preflight={status} status={result.status} "
        f"queue_item={result.queue_item_id or '(none)'} "
        f"selected_slice={result.selected_slice or '(none)'} reasons={reasons}"
    )
    if result.accepted and result.authority_profile_path:
        os.environ["REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH"] = result.authority_profile_path
        print(
            f"[REDDOG-FIX-PROMOTION] receipt={result.promotion_receipt_id} "
            f"revision={result.committed_revision}"
        )
        return True

    if enforced:
        print("[REDDOG-FIX-PROMOTION] Startup blocked by REDDOG_ARCHITECT_FIX_PROMOTION_ENFORCED=1")
        return False
    return True


def run_reddog_resident_queue_orchestration_plan_preflight(repo_root: Path) -> bool:
    """
    Plan the next resident RedDog queue bridge from the authoritative snapshot.

    Env:
        REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN=1          Enable check (default ON)
        REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN_ENFORCED=0 Block startup if not ready
        REDDOG_AUTHORITATIVE_WORK_STATE_PATH                Existing work-state snapshot
        REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH            Optional existing chain-results JSON
        REDDOG_WRE_QUEUE_ITEM_ID                            Optional exact queue item id
    """

    if os.getenv("REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN", "1") == "0":
        logger.info("[REDDOG-QUEUE-PLAN] Startup queue plan disabled")
        return True

    enforced = os.getenv("REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN_ENFORCED", "0") != "0"

    try:
        from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_orchestration_plan_bootstrap import (
            run_reddog_main_resident_queue_orchestration_plan_bootstrap,
        )
        from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
            resident_queue_runtime_file_path,
        )

        explicit_chain_results_path = str(
            os.getenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH") or ""
        ).strip()
        chain_results_path = resident_queue_runtime_file_path(
            os.environ,
            repo_root,
            "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH",
        )
        if not explicit_chain_results_path and chain_results_path:
            chain_results_path = chain_results_path if Path(chain_results_path).exists() else ""

        result = run_reddog_main_resident_queue_orchestration_plan_bootstrap(
            repo_root=repo_root,
            work_state_path=resident_queue_runtime_file_path(
                os.environ,
                repo_root,
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH",
            ),
            chain_results_path=chain_results_path or None,
            requested_queue_item_id=os.getenv("REDDOG_WRE_QUEUE_ITEM_ID", "") or None,
        )
    except Exception as exc:
        logger.error(f"[REDDOG-QUEUE-PLAN] Startup queue plan failed: {exc}")
        if enforced:
            print(f"[REDDOG-QUEUE-PLAN] preflight=FAIL error={type(exc).__name__}")
            return False
        print(f"[REDDOG-QUEUE-PLAN] preflight=WARN error={type(exc).__name__}")
        return True

    status = "PASS" if result.ready else "WARN"
    reasons = ",".join(result.rejection_reasons) if result.rejection_reasons else "(none)"
    print(
        f"[REDDOG-QUEUE-PLAN] preflight={status} status={result.status} "
        f"queue_item={result.queue_item_id or '(none)'} "
        f"selected_slice={result.selected_slice or '(none)'} "
        f"current_stage={result.current_stage or '(none)'} "
        f"next_action={result.next_action or '(none)'} "
        f"accepted_stages={result.accepted_stage_count} "
        f"chain_complete={result.chain_complete} reasons={reasons}"
    )
    if result.ready:
        print(f"[REDDOG-QUEUE-PLAN] plan={result.plan_id}")
        return True

    if enforced:
        print("[REDDOG-QUEUE-PLAN] Startup blocked by REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN_ENFORCED=1")
        return False
    return True


def run_reddog_resident_queue_next_stage_dispatch_preflight(repo_root: Path) -> bool:
    """
    Optionally dispatch the current resident queue stage through an injected handler.

    Env:
        REDDOG_RESIDENT_QUEUE_NEXT_STAGE_DISPATCH=0          Enable dispatch (default OFF)
        REDDOG_RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ENFORCED=0 Block startup if not applied
        REDDOG_AUTHORITATIVE_WORK_STATE_PATH                 Existing work-state snapshot
        REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH             Outside-repo chain-results JSON
        REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH         Outside-repo authority profile JSON
        REDDOG_AUTHORITY_RUNTIME_STATE_PATH                  Outside-repo authority-runtime JSON
        REDDOG_PERMISSION_SNAPSHOTS_PATH                     Outside-repo permission snapshot JSON
        REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH              Outside-repo principal authority JSON
        REDDOG_RESIDENT_QUEUE_NOW_EPOCH                      Optional runtime epoch for authority checks
        REDDOG_WRE_QUEUE_ITEM_ID                             Optional exact queue item id
    """

    if os.getenv("REDDOG_RESIDENT_QUEUE_NEXT_STAGE_DISPATCH", "0") == "0":
        logger.info("[REDDOG-QUEUE-DISPATCH] Startup next-stage dispatch disabled")
        return True

    enforced = os.getenv("REDDOG_RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ENFORCED", "0") != "0"

    try:
        from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_next_stage_dispatch_bootstrap import (
            run_reddog_main_resident_queue_next_stage_dispatch_bootstrap,
        )
        from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
            resident_queue_runtime_file_path,
        )

        result = run_reddog_main_resident_queue_next_stage_dispatch_bootstrap(
            repo_root=repo_root,
            work_state_path=resident_queue_runtime_file_path(
                os.environ,
                repo_root,
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH",
            ),
            chain_results_path=resident_queue_runtime_file_path(
                os.environ,
                repo_root,
                "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH",
            )
            or None,
            authority_profile_path=resident_queue_runtime_file_path(
                os.environ,
                repo_root,
                "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH",
            )
            or None,
            requested_queue_item_id=os.getenv("REDDOG_WRE_QUEUE_ITEM_ID", "") or None,
        )
    except Exception as exc:
        logger.error(f"[REDDOG-QUEUE-DISPATCH] Startup next-stage dispatch failed: {exc}")
        if enforced:
            print(f"[REDDOG-QUEUE-DISPATCH] preflight=FAIL error={type(exc).__name__}")
            return False
        print(f"[REDDOG-QUEUE-DISPATCH] preflight=WARN error={type(exc).__name__}")
        return True

    status = "PASS" if result.accepted else "WARN"
    reasons = ",".join(result.rejection_reasons) if result.rejection_reasons else "(none)"
    print(
        f"[REDDOG-QUEUE-DISPATCH] preflight={status} status={result.status} "
        f"queue_item={result.queue_item_id or '(none)'} "
        f"selected_slice={result.selected_slice or '(none)'} "
        f"dispatched_stage={result.dispatched_stage or '(none)'} "
        f"next_action={result.next_action or '(none)'} reasons={reasons}"
    )
    if result.accepted:
        print(
            f"[REDDOG-QUEUE-DISPATCH] chain_results={result.chain_results_path or '(none)'} "
            f"revision={result.store_revision or '(none)'}"
        )
        return True

    if enforced:
        print("[REDDOG-QUEUE-DISPATCH] Startup blocked by REDDOG_RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ENFORCED=1")
        return False
    return True


def run_reddog_resident_queue_serial_loop_preflight(repo_root: Path) -> bool:
    """
    Optionally run the bounded resident queue serial loop through injected handlers.

    Env:
        REDDOG_RESIDENT_QUEUE_SERIAL_LOOP=0                  Enable loop (profile may default ON)
        REDDOG_RESIDENT_QUEUE_BINDING_PROFILE                Optional `signed_0102_bounded_code`
        REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_ENFORCED=0         Block startup if not applied
        REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_MAX_STEPS=1        Bounded loop steps
        REDDOG_AUTHORITATIVE_WORK_STATE_PATH                 Existing work-state snapshot
        REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH             Outside-repo chain-results JSON
        REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH         Outside-repo authority profile JSON
        REDDOG_WORK_ORDERS_PATH                              Outside-repo work-order JSON snapshot
        REDDOG_WORK_ORDER_MATERIALIZER_MODE                  Optional `authority_profile` in-memory materializer
        REDDOG_EXECUTION_VALVE_ENV_PATH                      Outside-repo valve environment JSON
        REDDOG_PILOT_DRYRUN_BINDING                          Derive pilot dry-run receipts from queue chain state
        REDDOG_GENERIC_WRITER_DRYRUN_RESULT_PATH             Outside-repo generic writer dry-run JSON
        REDDOG_GOVERNED_SHELL_DRYRUN_RESULT_PATH             Outside-repo governed shell dry-run JSON
        REDDOG_ARTIFACT_CONTENTS_PATH                        Outside-repo artifact contents JSON
        REDDOG_ARTIFACT_GENERATION_REQUEST_PATH              Outside-repo artifact generation request JSON
        REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING           Derive artifact generation request from queue chain state
        REDDOG_ARTIFACT_GENERATOR_MODE                       Optional `foundups_fusion` generator mode
        REDDOG_HOLOINDEX_EVIDENCE_PATH                       Outside-repo HoloIndex evidence JSON
        REDDOG_SLICE_VERIFIER_REQUEST_PATH                   Outside-repo slice verifier request JSON
        REDDOG_EVIDENCE_PRODUCER_REQUEST_PATH                Outside-repo evidence producer request JSON
        REDDOG_SLICE_VERIFIER_REQUEST_BINDING                Derive verifier request from queue chain state
        REDDOG_EVIDENCE_COMMAND_RUNNER_MODE                  Optional `real` evidence command runner mode
        REDDOG_DRAFT_PR_PUBLISH_REQUEST_PATH                 Outside-repo draft PR publish request JSON
        REDDOG_DRAFT_PR_PUBLISH_REQUEST_BINDING              Derive draft PR publish request from queue chain state
        REDDOG_OUTCOME_RATCHET_REQUEST_BINDING               Derive outcome-ratchet request from queue chain state
        REDDOG_HELD_OUT_GATE_REQUEST_BINDING                 Derive held-out gate request from queue chain state
        REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_BINDING      Derive PatternMemory admission request from queue chain state
        REDDOG_AUTHORITY_RUNTIME_RESOLVER_ARTIFACT_SUPPLY=0 Materialize principal/snapshot resolver stores
        REDDOG_AUTHORITY_RUNTIME_RESOLVER_ARTIFACT_SUPPLY_ENFORCED=0 Block startup if resolver supply fails
        REDDOG_WRE_QUEUE_ITEM_ID                             Optional exact queue item id
        REDDOG_AUTHORITY_RUNTIME_STATE_PATH                  Outside-repo authority runtime state JSON
        REDDOG_PERMISSION_SNAPSHOTS_PATH                     Outside-repo permission resolver JSON
        REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH              Outside-repo principal resolver JSON
        REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY=0                Materialize signer-owned CLI config from authority profile
        REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY_ENFORCED=0       Block startup if signer config supply fails
        REDDOG_SIGNER_SERVICE_CONFIG_PATH                    Outside-repo signer CLI config JSON
        REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY=0            Materialize signer-owned CLI argv packet
        REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY_ENFORCED=0   Block startup if run-packet supply fails
        REDDOG_SIGNER_SERVICE_RUN_PACKET_PATH                Outside-repo signer CLI run-packet JSON
        REDDOG_SIGNER_SERVICE_HEALTHCHECK=0                  Validate signer run packet and probe existing socket
        REDDOG_SIGNER_SERVICE_HEALTHCHECK_ENFORCED=0         Block startup if signer healthcheck fails
        REDDOG_SIGNER_HEALTHCHECK_REQUESTER_PRINCIPAL_ID     Optional requester principal for healthcheck request
        REDDOG_SIGNER_HEALTHCHECK_PROFILE_ID                 Optional signer profile id for healthcheck request
        REDDOG_SIGNER_HEALTHCHECK_TIMEOUT_S                  Optional signer healthcheck timeout
        REDDOG_SIGNER_HEALTHCHECK_MAX_RESPONSE_BYTES         Optional signer healthcheck response cap
        REDDOG_SIGNER_SOCKET_PROFILE_BINDING=0              Derive signer socket path/backend when authority runtime is configured
        REDDOG_SIGNER_SOCKET_PATH                            Optional outside-repo isolated signer socket
        REDDOG_SIGNATURE_VERIFIER_BACKEND                    Optional verifier backend (`ed25519`)
        REDDOG_RESIDENT_QUEUE_WORKTREE_RUNNER_MODE           Optional `real` runner mode
        REDDOG_RESIDENT_QUEUE_WORKTREE_RUNNER_TIMEOUT_S      Optional runner timeout
        REDDOG_DRAFT_PR_RUNNER_MODE                          Optional `real` draft-PR runner mode
        REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S                     Optional draft-PR runner timeout
    """

    from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
        resident_queue_runtime_flag_enabled,
    )

    if not resident_queue_runtime_flag_enabled(os.environ, "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP"):
        logger.info("[REDDOG-QUEUE-LOOP] Startup serial loop disabled")
        run_reddog_resident_queue_serial_loop_preflight.last_result = {
            "accepted": True,
            "status": "DISABLED",
            "progress_count": 0,
            "steps_run": 0,
            "rejection_reasons": (),
        }
        return True

    enforced = os.getenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_ENFORCED", "0") != "0"
    try:
        max_steps = int(os.getenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_MAX_STEPS", "1"))
    except ValueError:
        max_steps = 0
    try:
        now_epoch_value = os.getenv("REDDOG_RESIDENT_QUEUE_NOW_EPOCH", "")
        now_epoch = int(now_epoch_value) if now_epoch_value else None
    except ValueError:
        now_epoch = None
    try:
        signer_socket_timeout_value = os.getenv("REDDOG_SIGNER_SOCKET_TIMEOUT_S", "")
        signer_socket_timeout_s = float(signer_socket_timeout_value) if signer_socket_timeout_value else 5.0
    except ValueError:
        signer_socket_timeout_s = 0.0
    try:
        signer_socket_max_value = os.getenv("REDDOG_SIGNER_SOCKET_MAX_RESPONSE_BYTES", "")
        signer_socket_max_response_bytes = int(signer_socket_max_value) if signer_socket_max_value else 16384
    except ValueError:
        signer_socket_max_response_bytes = 0
    try:
        worktree_runner_timeout_value = os.getenv("REDDOG_RESIDENT_QUEUE_WORKTREE_RUNNER_TIMEOUT_S", "")
        worktree_runner_timeout_s = int(worktree_runner_timeout_value) if worktree_runner_timeout_value else 120
    except ValueError:
        worktree_runner_timeout_s = 0
    try:
        draft_pr_runner_timeout_value = os.getenv("REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S", "")
        draft_pr_runner_timeout_s = int(draft_pr_runner_timeout_value) if draft_pr_runner_timeout_value else 120
    except ValueError:
        draft_pr_runner_timeout_s = 0

    try:
        from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap import (
            run_reddog_main_resident_queue_serial_loop_bootstrap,
        )
        from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
            resident_queue_binding_enabled,
            resident_queue_artifact_generator_mode,
            resident_queue_draft_pr_runner_mode,
            resident_queue_evidence_command_runner_mode,
            resident_queue_materializer_mode,
            resident_queue_model_feedback_ledger_store_path,
            resident_queue_outcome_ratchet_store_path,
            resident_queue_pattern_memory_admission_db_path,
            resident_queue_runtime_file_path,
            resident_queue_worktree_runner_mode,
        )
        from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
            build_reddog_verified_pattern_memory_sink,
        )

        pattern_memory_admission_sink = build_reddog_verified_pattern_memory_sink(
            repo_root=repo_root,
            db_path=resident_queue_pattern_memory_admission_db_path(os.environ, repo_root)
            or None,
        )
        draft_pr_runner = None
        draft_pr_runner_mode = resident_queue_draft_pr_runner_mode(os.environ).strip().lower()
        if draft_pr_runner_mode:
            if draft_pr_runner_mode != "real":
                raise ValueError("unsupported_draft_pr_runner_mode")
            if draft_pr_runner_timeout_s <= 0:
                raise ValueError("invalid_draft_pr_runner_timeout")
            from modules.foundups.agent.src.worktree_pr_runner import RealWorktreeRunner

            draft_pr_runner = RealWorktreeRunner(
                repo_root=repo_root,
                timeout_s=draft_pr_runner_timeout_s,
            )

        explicit_authority_state_path = str(os.getenv("REDDOG_AUTHORITY_RUNTIME_STATE_PATH") or "").strip()
        authority_state_path = explicit_authority_state_path
        explicit_permission_snapshots_path = str(os.getenv("REDDOG_PERMISSION_SNAPSHOTS_PATH") or "").strip()
        permission_snapshots_path = explicit_permission_snapshots_path
        explicit_principal_records_path = str(os.getenv("REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH") or "").strip()
        principal_authority_records_path = explicit_principal_records_path
        explicit_signer_socket_path = str(os.getenv("REDDOG_SIGNER_SOCKET_PATH") or "").strip()
        signer_socket_path = explicit_signer_socket_path
        explicit_signature_verifier_backend = str(os.getenv("REDDOG_SIGNATURE_VERIFIER_BACKEND") or "").strip()
        signature_verifier_backend = explicit_signature_verifier_backend
        authority_profile_path = resident_queue_runtime_file_path(
            os.environ,
            repo_root,
            "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH",
        )
        resolver_permission_snapshots_output_path = resident_queue_runtime_file_path(
            os.environ,
            repo_root,
            "REDDOG_PERMISSION_SNAPSHOTS_PATH",
        )
        resolver_principal_records_output_path = resident_queue_runtime_file_path(
            os.environ,
            repo_root,
            "REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH",
        )
        resolver_supply_requested = resident_queue_runtime_flag_enabled(
            os.environ,
            "REDDOG_AUTHORITY_RUNTIME_RESOLVER_ARTIFACT_SUPPLY",
        )
        resolver_supply_enforced = (
            os.getenv("REDDOG_AUTHORITY_RUNTIME_RESOLVER_ARTIFACT_SUPPLY_ENFORCED", "0") != "0"
        )
        if resolver_supply_requested:
            from modules.communication.moltbot_bridge.src.reddog_authority_runtime_resolver_artifact_supply_bootstrap import (
                run_reddog_authority_runtime_resolver_artifact_supply_bootstrap,
            )

            resolver_supply = run_reddog_authority_runtime_resolver_artifact_supply_bootstrap(
                repo_root=repo_root,
                principal_authority_record_path=resident_queue_runtime_file_path(
                    os.environ,
                    repo_root,
                    "REDDOG_PRINCIPAL_AUTHORITY_RECORD_PATH",
                )
                or None,
                permission_snapshot_path=resident_queue_runtime_file_path(
                    os.environ,
                    repo_root,
                    "REDDOG_PERMISSION_SNAPSHOT_PATH",
                )
                or None,
                principal_records_output_path=resolver_principal_records_output_path,
                permission_snapshots_output_path=resolver_permission_snapshots_output_path,
            )
            resolver_status = "PASS" if resolver_supply.accepted else "WARN"
            resolver_reasons = (
                ",".join(resolver_supply.rejection_reasons)
                if resolver_supply.rejection_reasons
                else "(none)"
            )
            print(
                f"[REDDOG-AUTHORITY-RESOLVERS] preflight={resolver_status} "
                f"status={resolver_supply.status} "
                f"receipt={resolver_supply.resolver_supply_receipt_id or '(none)'} "
                f"reasons={resolver_reasons}"
            )
            if resolver_supply.accepted:
                if not authority_state_path:
                    authority_state_path = resident_queue_runtime_file_path(
                        os.environ,
                        repo_root,
                        "REDDOG_AUTHORITY_RUNTIME_STATE_PATH",
                    )
                if resolver_supply.principal_records_path:
                    principal_authority_records_path = resolver_supply.principal_records_path
                    os.environ["REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH"] = principal_authority_records_path
                if resolver_supply.permission_snapshots_path:
                    permission_snapshots_path = resolver_supply.permission_snapshots_path
                    os.environ["REDDOG_PERMISSION_SNAPSHOTS_PATH"] = permission_snapshots_path
            elif resolver_supply_enforced:
                print(
                    "[REDDOG-AUTHORITY-RESOLVERS] Startup blocked by "
                    "REDDOG_AUTHORITY_RUNTIME_RESOLVER_ARTIFACT_SUPPLY_ENFORCED=1"
                )
                return False

        signer_config_supply_requested = str(
            os.getenv("REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY") or ""
        ).strip() == "1"
        signer_config_supply_enforced = (
            os.getenv("REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY_ENFORCED", "0") != "0"
        )
        if signer_config_supply_requested:
            from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
                run_reddog_signer_socket_service_config_supply,
            )

            authority_profile_payload = None
            if authority_profile_path:
                authority_profile_payload = _reddog_bounded_json_file(Path(authority_profile_path))
            peer_uid_to_principal = _reddog_bounded_json_env("REDDOG_SIGNER_PEER_UID_TO_PRINCIPAL")
            config_output_path = resident_queue_runtime_file_path(
                os.environ,
                repo_root,
                "REDDOG_SIGNER_SERVICE_CONFIG_PATH",
            )
            config_socket_path = signer_socket_path or resident_queue_runtime_file_path(
                os.environ,
                repo_root,
                "REDDOG_SIGNER_SOCKET_PATH",
            )
            signer_config = run_reddog_signer_socket_service_config_supply(
                repo_root=repo_root,
                authority_profile=(
                    authority_profile_payload
                    if isinstance(authority_profile_payload, Mapping)
                    else None
                ),
                output_path=config_output_path or None,
                socket_path=config_socket_path or None,
                principal_signing_key_ref=str(
                    os.getenv("REDDOG_SIGNER_PRINCIPAL_SIGNING_KEY_REF") or ""
                ),
                principal_audit_mac_key_ref=str(
                    os.getenv("REDDOG_SIGNER_PRINCIPAL_AUDIT_MAC_KEY_REF") or ""
                ),
                reddog_signing_key_ref=str(os.getenv("REDDOG_SIGNER_REDDOG_SIGNING_KEY_REF") or ""),
                reddog_audit_mac_key_ref=str(
                    os.getenv("REDDOG_SIGNER_REDDOG_AUDIT_MAC_KEY_REF") or ""
                ),
                peer_uid_to_principal=(
                    peer_uid_to_principal if isinstance(peer_uid_to_principal, Mapping) else {}
                ),
                allowed_gids=_reddog_env_sequence("REDDOG_SIGNER_ALLOWED_GIDS"),
                max_requests=_reddog_positive_int_env("REDDOG_SIGNER_CONFIG_MAX_REQUESTS", 16),
                timeout_s=_reddog_float_env("REDDOG_SIGNER_CONFIG_TIMEOUT_S", 5.0),
                max_request_bytes=_reddog_positive_int_env(
                    "REDDOG_SIGNER_CONFIG_MAX_REQUEST_BYTES",
                    16384,
                ),
                max_response_bytes=_reddog_positive_int_env(
                    "REDDOG_SIGNER_CONFIG_MAX_RESPONSE_BYTES",
                    16384,
                ),
            )
            signer_config_status = "PASS" if signer_config.accepted else "WARN"
            signer_config_reasons = (
                ",".join(signer_config.rejection_reasons)
                if signer_config.rejection_reasons
                else "(none)"
            )
            print(
                f"[REDDOG-SIGNER-CONFIG] preflight={signer_config_status} "
                f"status={signer_config.status} "
                f"receipt={signer_config.config_supply_receipt_id or '(none)'} "
                f"config={signer_config.config_path or '(none)'} "
                f"socket={signer_config.socket_path or '(none)'} "
                f"profiles={signer_config.profile_count} reasons={signer_config_reasons}"
            )
            if signer_config.accepted:
                if signer_config.config_path:
                    os.environ["REDDOG_SIGNER_SERVICE_CONFIG_PATH"] = signer_config.config_path
            elif signer_config_supply_enforced:
                print(
                    "[REDDOG-SIGNER-CONFIG] Startup blocked by "
                    "REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY_ENFORCED=1"
                )
                return False

        signer_run_packet_supply_requested = str(
            os.getenv("REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY") or ""
        ).strip() == "1"
        signer_run_packet_supply_enforced = (
            os.getenv("REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY_ENFORCED", "0") != "0"
        )
        if signer_run_packet_supply_requested:
            from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_run_packet_supply import (
                run_reddog_signer_socket_service_run_packet_supply,
            )

            signer_run_packet = run_reddog_signer_socket_service_run_packet_supply(
                repo_root=repo_root,
                config_path=resident_queue_runtime_file_path(
                    os.environ,
                    repo_root,
                    "REDDOG_SIGNER_SERVICE_CONFIG_PATH",
                )
                or None,
                output_path=resident_queue_runtime_file_path(
                    os.environ,
                    repo_root,
                    "REDDOG_SIGNER_SERVICE_RUN_PACKET_PATH",
                )
                or None,
                op_executable=str(os.getenv("REDDOG_SIGNER_SERVICE_OP_EXECUTABLE") or "op"),
                op_timeout_s=_reddog_float_env("REDDOG_SIGNER_SERVICE_OP_TIMEOUT_S", 10.0),
                ttl_seconds=_reddog_positive_int_env("REDDOG_SIGNER_SERVICE_TTL_SECONDS", 300),
                session_id=str(os.getenv("REDDOG_SIGNER_SERVICE_SESSION_ID") or "op-cli-session"),
                python_executable=str(os.getenv("REDDOG_SIGNER_SERVICE_PYTHON_EXECUTABLE") or "") or None,
            )
            signer_run_packet_status = "PASS" if signer_run_packet.accepted else "WARN"
            signer_run_packet_reasons = (
                ",".join(signer_run_packet.rejection_reasons)
                if signer_run_packet.rejection_reasons
                else "(none)"
            )
            print(
                f"[REDDOG-SIGNER-RUN-PACKET] preflight={signer_run_packet_status} "
                f"status={signer_run_packet.status} "
                f"packet={signer_run_packet.run_packet_id or '(none)'} "
                f"path={signer_run_packet.run_packet_path or '(none)'} "
                f"config={signer_run_packet.config_path or '(none)'} "
                f"socket={signer_run_packet.socket_path or '(none)'} "
                f"profiles={signer_run_packet.profile_count} reasons={signer_run_packet_reasons}"
            )
            if signer_run_packet.accepted:
                if signer_run_packet.run_packet_path:
                    os.environ["REDDOG_SIGNER_SERVICE_RUN_PACKET_PATH"] = (
                        signer_run_packet.run_packet_path
                    )
            elif signer_run_packet_supply_enforced:
                print(
                    "[REDDOG-SIGNER-RUN-PACKET] Startup blocked by "
                    "REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY_ENFORCED=1"
                )
                return False

        signer_healthcheck_requested = str(
            os.getenv("REDDOG_SIGNER_SERVICE_HEALTHCHECK") or ""
        ).strip() == "1"
        signer_healthcheck_enforced = (
            os.getenv("REDDOG_SIGNER_SERVICE_HEALTHCHECK_ENFORCED", "0") != "0"
        )
        if signer_healthcheck_requested:
            from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_healthcheck import (
                run_reddog_signer_socket_service_healthcheck,
            )

            signer_healthcheck = run_reddog_signer_socket_service_healthcheck(
                repo_root=repo_root,
                run_packet_path=resident_queue_runtime_file_path(
                    os.environ,
                    repo_root,
                    "REDDOG_SIGNER_SERVICE_RUN_PACKET_PATH",
                )
                or None,
                requester_principal_id=str(
                    os.getenv("REDDOG_SIGNER_HEALTHCHECK_REQUESTER_PRINCIPAL_ID") or ""
                )
                or None,
                signer_profile_id=str(
                    os.getenv("REDDOG_SIGNER_HEALTHCHECK_PROFILE_ID")
                    or "reddog-work-authority"
                ),
                timeout_s=_reddog_float_env("REDDOG_SIGNER_HEALTHCHECK_TIMEOUT_S", 5.0),
                max_response_bytes=_reddog_positive_int_env(
                    "REDDOG_SIGNER_HEALTHCHECK_MAX_RESPONSE_BYTES",
                    16384,
                ),
            )
            signer_healthcheck_status = "PASS" if signer_healthcheck.accepted else "WARN"
            signer_healthcheck_reasons = (
                ",".join(signer_healthcheck.rejection_reasons)
                if signer_healthcheck.rejection_reasons
                else "(none)"
            )
            print(
                f"[REDDOG-SIGNER-HEALTHCHECK] preflight={signer_healthcheck_status} "
                f"status={signer_healthcheck.status} "
                f"packet={signer_healthcheck.run_packet_id or '(none)'} "
                f"path={signer_healthcheck.run_packet_path or '(none)'} "
                f"socket={signer_healthcheck.socket_path or '(none)'} "
                f"profile={signer_healthcheck.signer_profile_id or '(none)'} "
                f"requester={signer_healthcheck.requester_principal_id or '(none)'} "
                f"request={signer_healthcheck.request_digest or '(none)'} "
                f"response={signer_healthcheck.response_digest or '(none)'} "
                f"reasons={signer_healthcheck_reasons}"
            )
            if not signer_healthcheck.accepted and signer_healthcheck_enforced:
                print(
                    "[REDDOG-SIGNER-HEALTHCHECK] Startup blocked by "
                    "REDDOG_SIGNER_SERVICE_HEALTHCHECK_ENFORCED=1"
                )
                return False

        signer_profile_binding_requested = resident_queue_runtime_flag_enabled(
            os.environ,
            "REDDOG_SIGNER_SOCKET_PROFILE_BINDING",
        )
        if signer_profile_binding_requested and authority_state_path and not signer_socket_path:
            signer_socket_path = resident_queue_runtime_file_path(
                os.environ,
                repo_root,
                "REDDOG_SIGNER_SOCKET_PATH",
            )
        if signer_socket_path and not signature_verifier_backend:
            signature_verifier_backend = "ed25519"

        worker_dispatch_writer = None
        if resident_queue_runtime_flag_enabled(
            os.environ,
            "REDDOG_WORKER_DISPATCH_AGENTDB_WRITER",
        ):
            from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
                AgentDbSignedWorkerDispatchTaskWriter,
            )

            worker_dispatch_writer = AgentDbSignedWorkerDispatchTaskWriter()

        explicit_valve_environment_path = str(
            os.getenv("REDDOG_EXECUTION_VALVE_ENV_PATH") or ""
        ).strip()
        profile_valve_environment_path = resident_queue_runtime_file_path(
            os.environ,
            repo_root,
            "REDDOG_EXECUTION_VALVE_ENV_PATH",
        )
        valve_environment_path = explicit_valve_environment_path
        if not valve_environment_path and profile_valve_environment_path:
            candidate_valve_path = Path(profile_valve_environment_path)
            if candidate_valve_path.exists():
                valve_environment_path = profile_valve_environment_path

        result = run_reddog_main_resident_queue_serial_loop_bootstrap(
            repo_root=repo_root,
            work_state_path=resident_queue_runtime_file_path(
                os.environ,
                repo_root,
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH",
            ),
            chain_results_path=resident_queue_runtime_file_path(
                os.environ,
                repo_root,
                "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH",
            )
            or None,
            authority_profile_path=resident_queue_runtime_file_path(
                os.environ,
                repo_root,
                "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH",
            )
            or None,
            work_orders_path=os.getenv("REDDOG_WORK_ORDERS_PATH", "") or None,
            work_order_materializer_mode=resident_queue_materializer_mode(os.environ) or None,
            valve_environment_path=valve_environment_path or None,
            generic_writer_dryrun_result_path=os.getenv(
                "REDDOG_GENERIC_WRITER_DRYRUN_RESULT_PATH", ""
            )
            or None,
            governed_shell_dryrun_result_path=os.getenv(
                "REDDOG_GOVERNED_SHELL_DRYRUN_RESULT_PATH", ""
            )
            or None,
            artifact_contents_path=os.getenv("REDDOG_ARTIFACT_CONTENTS_PATH", "") or None,
            artifact_generation_request_path=os.getenv("REDDOG_ARTIFACT_GENERATION_REQUEST_PATH", "") or None,
            artifact_generation_request_binding_enabled=resident_queue_binding_enabled(
                os.environ,
                "REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING",
            ),
            holoindex_evidence_path=os.getenv("REDDOG_HOLOINDEX_EVIDENCE_PATH", "") or None,
            verifier_request_path=os.getenv("REDDOG_SLICE_VERIFIER_REQUEST_PATH", "") or None,
            evidence_producer_request_path=os.getenv("REDDOG_EVIDENCE_PRODUCER_REQUEST_PATH", "") or None,
            publish_request_path=os.getenv("REDDOG_DRAFT_PR_PUBLISH_REQUEST_PATH", "") or None,
            ratchet_request_path=os.getenv("REDDOG_OUTCOME_RATCHET_REQUEST_PATH", "") or None,
            outcome_ratchet_store_path=resident_queue_outcome_ratchet_store_path(
                os.environ,
                repo_root,
            )
            or None,
            model_feedback_ledger_store_path=resident_queue_model_feedback_ledger_store_path(
                os.environ,
                repo_root,
            )
            or None,
            held_out_gate_request_path=os.getenv("REDDOG_HELD_OUT_GATE_REQUEST_PATH", "") or None,
            admission_request_path=os.getenv("REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_PATH", "") or None,
            authority_state_path=authority_state_path or None,
            permission_snapshots_path=permission_snapshots_path or None,
            principal_authority_records_path=principal_authority_records_path or None,
            signer_socket_path=signer_socket_path or None,
            signer_socket_timeout_s=signer_socket_timeout_s,
            signer_socket_max_response_bytes=signer_socket_max_response_bytes,
            signature_verifier_backend=signature_verifier_backend or None,
            pilot_dryrun_binding_enabled=resident_queue_binding_enabled(
                os.environ,
                "REDDOG_PILOT_DRYRUN_BINDING",
            ),
            worktree_runner_mode=resident_queue_worktree_runner_mode(os.environ) or None,
            worktree_runner_timeout_s=worktree_runner_timeout_s,
            artifact_generator_mode=resident_queue_artifact_generator_mode(os.environ) or None,
            slice_verifier_request_binding_enabled=resident_queue_binding_enabled(
                os.environ,
                "REDDOG_SLICE_VERIFIER_REQUEST_BINDING",
            ),
            evidence_command_runner_mode=resident_queue_evidence_command_runner_mode(os.environ)
            or None,
            draft_pr_publish_request_binding_enabled=resident_queue_binding_enabled(
                os.environ,
                "REDDOG_DRAFT_PR_PUBLISH_REQUEST_BINDING",
            ),
            outcome_ratchet_request_binding_enabled=resident_queue_binding_enabled(
                os.environ,
                "REDDOG_OUTCOME_RATCHET_REQUEST_BINDING",
            ),
            held_out_gate_request_binding_enabled=resident_queue_binding_enabled(
                os.environ,
                "REDDOG_HELD_OUT_GATE_REQUEST_BINDING",
            ),
            pattern_memory_admission_request_binding_enabled=resident_queue_binding_enabled(
                os.environ,
                "REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_BINDING",
            ),
            draft_pr_runner=draft_pr_runner,
            pattern_memory_admission_sink=pattern_memory_admission_sink,
            worker_dispatch_writer=worker_dispatch_writer,
            requested_queue_item_id=os.getenv("REDDOG_WRE_QUEUE_ITEM_ID", "") or None,
            now_epoch=now_epoch,
            max_steps=max_steps,
        )
    except Exception as exc:
        logger.error(f"[REDDOG-QUEUE-LOOP] Startup serial loop failed: {exc}")
        run_reddog_resident_queue_serial_loop_preflight.last_result = {
            "accepted": False,
            "status": "EXCEPTION",
            "progress_count": 0,
            "steps_run": 0,
            "rejection_reasons": (type(exc).__name__,),
        }
        if enforced:
            print(f"[REDDOG-QUEUE-LOOP] preflight=FAIL error={type(exc).__name__}")
            return False
        print(f"[REDDOG-QUEUE-LOOP] preflight=WARN error={type(exc).__name__}")
        return True

    status = "PASS" if result.accepted else "WARN"
    reasons = ",".join(result.rejection_reasons) if result.rejection_reasons else "(none)"
    progress_count = int(result.steps_run or 0)
    run_reddog_resident_queue_serial_loop_preflight.last_result = {
        "accepted": bool(result.accepted),
        "status": result.status,
        "progress_count": progress_count,
        "steps_run": int(result.steps_run or 0),
        "dispatched_stages": tuple(result.dispatched_stages or ()),
        "next_action": result.next_action or "",
        "rejection_reasons": tuple(result.rejection_reasons or ()),
    }
    print(
        f"[REDDOG-QUEUE-LOOP] preflight={status} status={result.status} "
        f"queue_item={result.queue_item_id or '(none)'} "
        f"selected_slice={result.selected_slice or '(none)'} "
        f"steps_run={result.steps_run} "
        f"dispatched_stages={','.join(result.dispatched_stages) or '(none)'} "
        f"next_action={result.next_action or '(none)'} reasons={reasons}"
    )
    if result.accepted:
        print(
            f"[REDDOG-QUEUE-LOOP] chain_results={result.chain_results_path or '(none)'} "
            f"revision={result.store_revision or '(none)'}"
        )
        return True

    if enforced:
        print("[REDDOG-QUEUE-LOOP] Startup blocked by REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_ENFORCED=1")
        return False
    return True


def _reddog_queue_stage_progress(stage_callable: Any, *, default_progress: int) -> int:
    """Return the last progress count recorded by a queue control stage."""

    raw = getattr(stage_callable, "last_result", None)
    if not isinstance(raw, Mapping):
        return max(int(default_progress), 0)
    try:
        return max(int(raw.get("progress_count") or 0), 0)
    except (TypeError, ValueError):
        return 0


def _reddog_queue_stage_rejected(stage_callable: Any) -> bool:
    """Return whether a queue control stage recorded an accepted-false result."""

    raw = getattr(stage_callable, "last_result", None)
    return isinstance(raw, Mapping) and raw.get("accepted") is False


def run_reddog_resident_queue_control_loop_preflight(repo_root: Path) -> bool:
    """
    Drive the resident queue through bounded serial/claim rounds.

    Env:
        REDDOG_RESIDENT_QUEUE_CONTROL_LOOP                 Enable bounded alternation (profile may default ON)
        REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_MAX_ROUNDS=8    Max serial/claim rounds
        REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_ENFORCED=0      Block startup if a round fails

    This function creates no authority, tasks, worktrees, shell commands,
    source mutations, PRs, PatternMemory writes, rewards, or HoloIndex re-index.
    It only repeats the already-governed serial-loop and OpenClaw signed-worker
    claim-loop preflights so one resident startup can advance more than one
    queue stage without requiring 012 to restart the host.
    """

    from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
        resident_queue_runtime_flag_enabled,
    )

    requested = resident_queue_runtime_flag_enabled(
        os.environ,
        "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP",
    )
    if not requested:
        if not run_reddog_resident_queue_serial_loop_preflight(repo_root):
            return False
        return run_reddog_openclaw_signed_worker_claim_loop_preflight(repo_root)

    enforced = os.getenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_ENFORCED", "0") != "0"
    raw_rounds = os.getenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_MAX_ROUNDS", "8").strip()
    try:
        max_rounds = int(raw_rounds or "8")
    except ValueError:
        max_rounds = 0
    if max_rounds < 1:
        print("[REDDOG-QUEUE-CONTROL] preflight=FAIL error=invalid_max_rounds")
        return not enforced

    completed_rounds = 0
    serial_progress_total = 0
    claim_progress_total = 0
    stopped_reason = "max_rounds"
    for round_index in range(1, max_rounds + 1):
        serial_ok = run_reddog_resident_queue_serial_loop_preflight(repo_root)
        serial_progress = _reddog_queue_stage_progress(
            run_reddog_resident_queue_serial_loop_preflight,
            default_progress=1 if serial_ok else 0,
        )
        serial_progress_total += serial_progress
        if not serial_ok or _reddog_queue_stage_rejected(
            run_reddog_resident_queue_serial_loop_preflight
        ):
            print(
                f"[REDDOG-QUEUE-CONTROL] preflight=FAIL round={round_index} "
                "stage=serial_loop"
            )
            return not enforced
        claim_ok = run_reddog_openclaw_signed_worker_claim_loop_preflight(repo_root)
        claim_progress = _reddog_queue_stage_progress(
            run_reddog_openclaw_signed_worker_claim_loop_preflight,
            default_progress=1 if claim_ok else 0,
        )
        claim_progress_total += claim_progress
        if not claim_ok or _reddog_queue_stage_rejected(
            run_reddog_openclaw_signed_worker_claim_loop_preflight
        ):
            print(
                f"[REDDOG-QUEUE-CONTROL] preflight=FAIL round={round_index} "
                "stage=openclaw_claim_loop"
            )
            return not enforced
        completed_rounds = round_index
        if serial_progress == 0 and claim_progress == 0:
            stopped_reason = "idle"
            break

    print(
        f"[REDDOG-QUEUE-CONTROL] preflight=PASS rounds={completed_rounds} "
        f"max_rounds={max_rounds} stopped_reason={stopped_reason} "
        f"serial_progress={serial_progress_total} claim_progress={claim_progress_total}"
    )
    return True


def run_reddog_openclaw_signed_worker_claim_loop_preflight(repo_root: Path) -> bool:
    """
    Optionally let OpenClaw claim signed RedDog worker-dispatch AgentDB tasks.

    Env:
        REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP=0           Enable loop (default OFF)
        REDDOG_RESIDENT_QUEUE_BINDING_PROFILE                Optional `signed_0102_bounded_code`
        REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP_ENFORCED=0  Block startup on reject
        OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS=1             Bounded claims
        OPENCLAW_SIGNED_WORKER_SIGNER_HEALTHCHECK=0          Validate signer before claiming tasks

    This preflight does not create tasks, sign authority, create worktrees,
    execute shell commands, publish PRs, dispatch Hermes, write PatternMemory,
    settle rewards, or re-index HoloIndex. It only invokes the existing
    OpenClaw signed-worker claim loop, whose per-task gates decide what can run.
    """

    from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
        resident_queue_runtime_flag_enabled,
    )

    if not resident_queue_runtime_flag_enabled(
        os.environ,
        "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP",
    ):
        logger.info("[REDDOG-OPENCLAW-CLAIM-LOOP] Startup claim loop disabled")
        run_reddog_openclaw_signed_worker_claim_loop_preflight.last_result = {
            "accepted": True,
            "status": "DISABLED",
            "progress_count": 0,
            "claimed_count": 0,
            "rejection_reasons": (),
        }
        return True

    enforced = os.getenv("REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP_ENFORCED", "0") != "0"
    max_claims_raw = os.getenv("OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS", "1").strip()
    try:
        max_claims = int(max_claims_raw)
    except ValueError:
        max_claims = 0
    if max_claims < 1:
        print("[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=FAIL error=invalid_max_claims")
        run_reddog_openclaw_signed_worker_claim_loop_preflight.last_result = {
            "accepted": False,
            "status": "INVALID_MAX_CLAIMS",
            "progress_count": 0,
            "claimed_count": 0,
            "rejection_reasons": ("invalid_max_claims",),
        }
        return not enforced

    try:
        from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
            claim_reddog_signed_worker_dispatch_tasks_until_idle,
        )

        result = claim_reddog_signed_worker_dispatch_tasks_until_idle(
            repo_root=repo_root,
            max_claims=max_claims,
        )
    except Exception as exc:
        logger.error(f"[REDDOG-OPENCLAW-CLAIM-LOOP] Startup claim loop failed: {exc}")
        run_reddog_openclaw_signed_worker_claim_loop_preflight.last_result = {
            "accepted": False,
            "status": "EXCEPTION",
            "progress_count": 0,
            "claimed_count": 0,
            "rejection_reasons": (type(exc).__name__,),
        }
        if enforced:
            print(f"[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=FAIL error={type(exc).__name__}")
            return False
        print(f"[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=WARN error={type(exc).__name__}")
        return True

    accepted = bool(result.get("accepted"))
    status = str(result.get("status") or "(unknown)")
    claimed_count = int(result.get("claimed_count") or 0)
    completed = ",".join(str(item) for item in result.get("completed_task_ids", ()) or ()) or "(none)"
    requeued = ",".join(str(item) for item in result.get("requeued_task_ids", ()) or ()) or "(none)"
    failed = ",".join(str(item) for item in result.get("failed_task_ids", ()) or ()) or "(none)"
    reasons = ",".join(str(reason) for reason in result.get("rejection_reasons", ()) or ()) or "(none)"
    status_label = "PASS" if accepted else "WARN"
    run_reddog_openclaw_signed_worker_claim_loop_preflight.last_result = {
        "accepted": accepted,
        "status": status,
        "progress_count": claimed_count,
        "claimed_count": claimed_count,
        "idle": bool(result.get("idle")),
        "max_claims_reached": bool(result.get("max_claims_reached")),
        "rejection_reasons": tuple(result.get("rejection_reasons", ()) or ()),
    }
    print(
        f"[REDDOG-OPENCLAW-CLAIM-LOOP] preflight={status_label} status={status} "
        f"claimed_count={claimed_count} max_claims={max_claims} "
        f"completed={completed} requeued={requeued} failed={failed} reasons={reasons}"
    )
    if accepted:
        return True

    if enforced:
        print("[REDDOG-OPENCLAW-CLAIM-LOOP] Startup blocked by REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP_ENFORCED=1")
        return False
    return True


def bootstrap_runtime_dae_launches() -> None:
    """Register broker-managed DAE entrypoints for an already running system."""
    daemon = get_central_daemon()
    if daemon.state != "running":
        daemon.start()

    broker = get_dae_launch_broker(daemon=daemon)
    resident_enabled = os.getenv("OPENCLAW_RESIDENT_ENABLED", "1") != "0"
    supervisor_enabled = os.getenv("OPENCLAW_SUPERVISOR_ENABLED", "1") != "0"
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
    if supervisor_enabled:
        specs.append(
            DAELaunchSpec(
                dae_id="openclaw_supervisor",
                dae_name="OpenClaw Supervisor",
                domain="communication",
                module_path="modules.communication.moltbot_bridge.scripts.launch",
                start_callable=run_openclaw_supervisor_service,
                stop_callable=stop_openclaw_supervisor_service,
                heartbeat_interval_sec=15.0,
                description="Canonical 0102 supervisor state machine.",
            )
        )

    specs.extend([
        DAELaunchSpec(
            dae_id="holodae",
            dae_name="HoloDAE",
            domain="ai_intelligence",
            module_path="modules.ai_intelligence.holo_dae.scripts.launch",
            start_callable=run_holodae,
            stop_callable=stop_holodae,
            description="Code intelligence and search runtime.",
            metadata={
                "resident_owner": "dae_launch_broker",
                "runtime_autostart": False,
                "runtime_reindex_allowed": False,
                "query_runtime": True,
            },
        ),
        DAELaunchSpec(
            dae_id="git_push_dae",
            dae_name="GitPush DAE",
            domain="infrastructure",
            module_path="modules.infrastructure.git_push_dae.scripts.launch",
            start_callable=lambda: launch_git_push_dae(run_once=False),
            stop_callable=stop_git_push_dae,
            description="Autonomous git push daemon.",
        ),
        DAELaunchSpec(
            dae_id="social_media",
            dae_name="Social Media DAE",
            domain="platform_integration",
            module_path="modules.platform_integration.social_media_orchestrator.scripts.launch",
            start_callable=run_social_media_dae,
            stop_callable=stop_social_media_dae,
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

    supervisor_autostart = os.getenv("OPENCLAW_SUPERVISOR_AUTOSTART", "1") != "0"
    if supervisor_enabled and supervisor_autostart:
        status = broker.get_runtime_status("openclaw_supervisor")
        if not status.get("running"):
            result = broker.start_dae("openclaw_supervisor", actor_id="0102")
            launch_status = result.get("status", result.get("error", "unknown"))
            print(f"[OPENCLAW-SUPERVISOR] bootstrap={launch_status}")


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
        _handle_startup_blocker(
            repo_root,
            component="env_hygiene",
            stage="run_env_hygiene_preflight",
        )
        return
    if not run_brain_artifact_preflight(repo_root):
        _handle_startup_blocker(
            repo_root,
            component="brain_artifact",
            stage="run_brain_artifact_preflight",
        )
        return
    if not run_ironclaw_runtime_preflight(repo_root):
        _handle_startup_blocker(
            repo_root,
            component="ironclaw_runtime",
            stage="run_ironclaw_runtime_preflight",
        )
        return
    if not run_openclaw_security_preflight(repo_root, overseer=overseer):
        _handle_startup_blocker(
            repo_root,
            component="openclaw_security",
            stage="run_openclaw_security_preflight",
        )
        return
    if not run_dependency_security_preflight(repo_root):
        _handle_startup_blocker(
            repo_root,
            component="dep_security",
            stage="run_dependency_security_preflight",
        )
        return
    if not run_wre_dashboard_preflight(repo_root):
        _handle_startup_blocker(
            repo_root,
            component="wre_dashboard",
            stage="run_wre_dashboard_preflight",
        )
        return
    if not run_wsp_framework_preflight(repo_root, overseer=overseer):
        _handle_startup_blocker(
            repo_root,
            component="wsp_framework",
            stage="run_wsp_framework_preflight",
        )
        return
    if not run_git_main_merge_sentinel_preflight(repo_root):
        _handle_startup_blocker(
            repo_root,
            component="git_main_merge_sentinel",
            stage="run_git_main_merge_sentinel_preflight",
        )
        return
    if not run_reddog_authoritative_work_state_refresh_preflight(repo_root):
        return
    if not run_reddog_resident_architect_durable_cycle_preflight(repo_root):
        return
    if not run_reddog_architect_fix_promotion_preflight(repo_root):
        return
    if not run_reddog_wre_queue_consumer_preflight(repo_root):
        return
    if not run_reddog_resident_queue_orchestration_plan_preflight(repo_root):
        return
    if not run_reddog_resident_queue_next_stage_dispatch_preflight(repo_root):
        return
    if not run_reddog_resident_queue_control_loop_preflight(repo_root):
        return
    if not run_reddog_readonly_operational_bootstrap_preflight(repo_root):
        return

    bootstrap_runtime_dae_launches()

    # MAIN_MENU_ANTIFAFM_STARTUP_BOUNDARY_FIX_PHASE1:
    # Legacy ANTIFAFM_AUTO_START block removed. The env var is now ignored at menu boot.
    # AntifaFM/OBS/broadcaster launch requires explicit user action via:
    #   - YouTube DAE menu option 1 (preflight)
    #   - YouTube DAE menu option 10 (broadcaster control)
    # See: ANTIFAFM_PREFLIGHT_RELOCATION_AUDIT_20260516.md
    #      OBS_WEBSOCKET_SECRET_LOGGING_FIX_PHASE1.md (PR #720)

    # Import MCP services for CLI access
    from modules.infrastructure.mcp_manager.src.mcp_manager import show_mcp_services_menu
    
    # Import the main menu runner from the CLI module
    from modules.infrastructure.cli.src.main_menu import run_main_menu

    self_audit_loop = None
    supervisor_enabled = os.getenv("OPENCLAW_SUPERVISOR_ENABLED", "1") != "0"
    if not supervisor_enabled and os.getenv("OPENCLAW_SELF_AUDIT_ENABLED", "1") != "0":
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


def run_headless() -> int:
    """
    WSP 97: Headless autonomous mode.

    Runs OpenClaw supervisor in a loop without interactive menu.
    FAIL-CLOSED: Exits with error if WRE is not READY.
    """
    repo_root = Path(__file__).resolve().parent

    # Fail-closed: check WRE readiness first
    wre_status = run_connect_wre(repo_root)
    if wre_status["readiness"] not in ("READY", "INSUFFICIENT_DATA"):
        print(
            f"[HEADLESS] FAIL-CLOSED: WRE not ready "
            f"(readiness={wre_status['readiness']}, "
            f"critical={wre_status['alert_counts']['critical']})"
        )
        return 1

    print(f"[HEADLESS] Starting autonomous mode (WRE={wre_status['readiness']})")

    try:
        from modules.communication.moltbot_bridge.src.openclaw_supervisor import OpenClawSupervisor
        from modules.infrastructure.dae_daemon.src.dae_observer import DAEObserver

        # WSP 97 headless bootstrap seam: register broker-managed DAE launch specs
        # BEFORE the supervisor cycle by reusing the existing bootstrap path (no
        # duplicated specs; shared singleton broker). Default the headless loop to a
        # BOUNDED, dry-run-safe posture so a one-cycle run performs no live launch:
        #   - suppress resident/supervisor DAE autostart (avoid duplicate runtimes)
        #   - suppress the supervisor's service-restart path so triage escalates
        #     ("resident_openclaw_down_restart_disabled") instead of live-starting
        #     the resident webhook service.
        # Autonomous task/maintenance execution is already off by default
        # (OPENCLAW_AUTO_TASKS_ENABLED / OPENCLAW_MAINTENANCE_ENABLED default "0").
        # An operator opts into live autonomy via these existing env flags.
        os.environ.setdefault("OPENCLAW_RESIDENT_AUTOSTART", "0")
        os.environ.setdefault("OPENCLAW_SUPERVISOR_AUTOSTART", "0")
        os.environ.setdefault("OPENCLAW_SUPERVISOR_ALLOW_RESTART", "0")
        bootstrap_runtime_dae_launches()
        broker = get_dae_launch_broker()
        observer = DAEObserver()

        supervisor = OpenClawSupervisor(
            repo_root=repo_root,
            broker=broker,
            observer=observer,
        )

        print("[HEADLESS] OpenClaw supervisor initialized, entering run loop...")

        cycle_interval = float(os.getenv("OPENCLAW_HEADLESS_INTERVAL", "30"))
        max_cycles = int(os.getenv("OPENCLAW_HEADLESS_MAX_CYCLES", "0"))  # 0 = infinite
        cycle_count = 0

        while True:
            try:
                result = supervisor.run_cycle()
                cycle_count += 1
                action = result.get("plan", {}).get("action", "idle")
                ok = result.get("verify", {}).get("ok", False)
                print(f"[HEADLESS] cycle={cycle_count} action={action} ok={ok}")

                if max_cycles > 0 and cycle_count >= max_cycles:
                    print(f"[HEADLESS] max_cycles={max_cycles} reached, exiting")
                    break

                time.sleep(cycle_interval)

            except KeyboardInterrupt:
                print("[HEADLESS] interrupted, exiting")
                break
            except Exception as exc:
                logger.error(f"[HEADLESS] cycle error: {exc}")
                time.sleep(cycle_interval)

        return 0

    except ImportError as exc:
        print(f"[HEADLESS] FAIL-CLOSED: missing dependency: {exc}")
        return 1
    except Exception as exc:
        print(f"[HEADLESS] FAIL-CLOSED: {exc}")
        return 1


if __name__ == "__main__":
    # WSP 97 Section 4.6: --connect-wre CLI hook
    if len(sys.argv) > 1 and sys.argv[1] == "--connect-wre":
        repo_root = Path(__file__).resolve().parent
        status = run_connect_wre(repo_root)
        print(
            f"coded={status['coded']} "
            f"connection={status['connection']} "
            f"readiness={status['readiness']} "
            f"manual_enforced={status['manual_enforced']} "
            f"auto_enforced_now={status['auto_enforced_now']} "
            f"samples={status['sample_coverage']} "
            f"critical={status['alert_counts']['critical']} "
            f"warnings={status['alert_counts']['warning']}"
        )
        sys.exit(0 if status["readiness"] == "READY" else 1)

    # WSP 97: --headless autonomous mode (fail-closed, no interactive menu)
    if len(sys.argv) > 1 and sys.argv[1] == "--headless":
        sys.exit(run_headless())

    main()
