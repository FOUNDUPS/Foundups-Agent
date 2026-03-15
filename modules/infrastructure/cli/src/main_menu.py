"""
Main Menu - Core CLI dispatcher for FoundUps Agent.

Extracted from main.py per WSP 62 (file size enforcement).
Contains: argument parsing, switchboard, main loop, instance management.
"""

import os
import sys
import json
import time
import logging
import asyncio
import argparse
import threading
from pathlib import Path
from typing import Optional, Dict, Any

import psutil

from modules.infrastructure.cli.src.utilities import (
    env_truthy,
    env_flag,
    maybe_clear_screen,
    maybe_auto_index_holo,
    local_model_routing_menu,
)
from modules.infrastructure.cli.src.git_menu import handle_git_menu
from modules.infrastructure.cli.src.youtube_menu import handle_youtube_menu
from modules.infrastructure.cli.src.holodae_menu import handle_holodae_menu
from modules.infrastructure.cli.src.fam_menu import handle_fam_menu
from modules.infrastructure.cli.src.openclaw_menu import handle_openclaw_menu
from modules.infrastructure.cli.src.social_media_menu import handle_social_media_menu
from modules.infrastructure.cli.src.wsp_explainer_menu import run_wsp_explainer

logger = logging.getLogger(__name__)


def run_main_menu(
    monitor_youtube,
    monitor_all_platforms,
    search_with_holoindex,
    check_instance_status,
    launch_git_push_dae,
    view_git_post_history,
    run_holodae,
    run_amo_dae,
    run_social_media_dae,
    run_vision_dae,
    run_pqn_dae,
    run_evade_net,
    run_liberty_alert_dae,
    run_training_system,
    execute_training_command,
    show_mcp_services_menu,
    PATTERN_MEMORY_AVAILABLE: bool,
    PatternMemory,
    # antifaFM broadcaster (optional for backwards compat)
    run_antifafm_broadcaster=None,
    start_antifafm_background=None,
    stop_antifafm_background=None,
    get_antifafm_status=None,
    run_suno_sync_cli=None,
) -> None:
    """
    Main entry point for interactive CLI.
    
    This function receives all external dependencies as parameters to avoid
    circular imports and maintain clean module boundaries.
    """
    maybe_clear_screen()
    logger.info("0102 FoundUps Agent starting...")

    # Define parser for early argument parsing
    parser = argparse.ArgumentParser(description='0102 FoundUps Agent')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed diagnostic information')

    # Startup diagnostics (verbose mode shows details)
    args, remaining = parser.parse_known_args()

    # Essential startup diagnostics (always log for troubleshooting)
    if args.verbose:
        logger.info(f"[DIAG] Python {sys.version.split()[0]} on {sys.platform}")
        logger.info(f"[DIAG] Working directory: {os.getcwd()}")
        logger.info(f"[DIAG] UTF-8 stdout: {getattr(sys.stdout, 'encoding', 'unknown')}")
        logger.info(f"[DIAG] UTF-8 stderr: {getattr(sys.stderr, 'encoding', 'unknown')}")
    else:
        logger.debug(f"[DIAG] Python {sys.version.split()[0]} on {sys.platform}")
        logger.debug(f"[DIAG] Working directory: {os.getcwd()}")

    # Check critical systems
    try:
        import modules
        if args.verbose:
            logger.info("[DIAG] modules/ directory accessible")
        else:
            logger.debug("[DIAG] modules/ directory accessible")
    except ImportError as e:
        logger.error(f"[STARTUP] modules/ directory not accessible: {e}")

    try:
        from modules.infrastructure.instance_lock.src.instance_manager import get_instance_lock
        if args.verbose:
            logger.info("[DIAG] Instance lock system available")
        else:
            logger.debug("[DIAG] Instance lock system available")
    except ImportError as e:
        logger.warning(f"[STARTUP] Instance lock system unavailable: {e}")

    # UTF-8 encoding is critical for Windows CLI compatibility
    stdout_enc = getattr(sys.stdout, 'encoding', 'unknown')
    stderr_enc = getattr(sys.stderr, 'encoding', 'unknown')
    if stdout_enc != 'utf-8' or stderr_enc != 'utf-8':
        logger.warning(f"[STARTUP] UTF-8 encoding issue - stdout:{stdout_enc} stderr:{stderr_enc}")
    else:
        if args.verbose:
            logger.info("[DIAG] UTF-8 encoding confirmed")
        else:
            logger.debug("[DIAG] UTF-8 encoding confirmed")

    # Add remaining arguments to existing parser
    parser.add_argument('--git', action='store_true', help='Run GitPushDAE once (autonomous git push + social posting)')
    parser.add_argument('--git-daemon', action='store_true', help='Run GitPushDAE continuously (daemon mode)')
    parser.add_argument('--youtube', action='store_true', help='Monitor YouTube only')
    parser.add_argument('--holodae', '--holo', action='store_true', help='Run HoloDAE (Code Intelligence & Monitoring)')
    parser.add_argument('--amo', action='store_true', help='Run AMO DAE (Autonomous Moderation Operations)')
    parser.add_argument('--smd', action='store_true', help='Run Social Media DAE (0102 Autonomous)')
    parser.add_argument('--vision', action='store_true', help='Run FoundUps Vision DAE (Pattern Sensorium)')
    parser.add_argument('--pqn', action='store_true', help='Run PQN Orchestration (Research & Alignment)')
    parser.add_argument('--liberty', action='store_true', help='Run Liberty Alert Mesh Alert System (Community Protection)')
    parser.add_argument('--liberty-dae', action='store_true', help='Run Liberty Alert DAE (Community Protection Autonomous Entity)')
    parser.add_argument('--all', action='store_true', help='Monitor all platforms')
    parser.add_argument('--mcp', action='store_true', help='Launch MCP Services Gateway (Model Context Protocol)')
    parser.add_argument('--deps', action='store_true', help='Start/check local automation dependencies (Chrome + LM Studio)')
    parser.add_argument('--no-lock', action='store_true', help='Disable instance lock (allow multiple instances)')
    parser.add_argument('--status', action='store_true', help='Check instance status and health')
    parser.add_argument('--connect-wre', action='store_true', help='Connect WRE and report readiness state')
    parser.add_argument('--training-command', type=str, help='Execute training command via Holo (e.g., utf8_scan, batch)')
    parser.add_argument('--targets', type=str, help='Comma-separated target paths for training command')
    parser.add_argument('--json-output', action='store_true', help='Return training command result as JSON')
    parser.add_argument('--training-menu', action='store_true', help='Launch interactive training submenu (option 12)')
    parser.add_argument('--fam', action='store_true', help='FoundUps Ecosystem (FAM + Simulator + Deploy + Demo)')
    parser.add_argument('--follow-wsp', nargs='?', const='', type=str, help='Run follow-WSP orchestrator with optional task')
    parser.add_argument('--deploy-sse', action='store_true', help='Deploy SSE server to Cloud Run')
    parser.add_argument('--deploy-firebase', action='store_true', help='Deploy Firebase Hosting')
    parser.add_argument('--chat', action='store_true', help='OpenClaw Local Chat (talk to 0102 directly)')
    parser.add_argument('--voice', action='store_true', help='OpenClaw Voice Chat (talk to 0102 via headset)')
    parser.add_argument('--ironclaw-chat', action='store_true', help='IronClaw chat backend (no API keys)')
    parser.add_argument('--ironclaw-voice', action='store_true', help='IronClaw voice backend (no API keys)')
    parser.add_argument('--local-models', action='store_true', help='Open local model routing editor (LOCAL_MODEL_*)')
    parser.add_argument('--ln-action', type=str, help='Run LinkedIn action directly (agent API)')
    parser.add_argument('--ln-param', action='append', help='LinkedIn action parameter key=value (repeatable)')
    parser.add_argument('--agent-command', type=str, help='Run standalone action command (linkedin/x/social/youtube)')
    parser.add_argument('--agent-repeat', type=int, default=1, help='Repeat count for --agent-command')
    parser.add_argument('--agent-interval-sec', type=float, default=0.0, help='Delay between repeated agent commands')
    parser.add_argument('--agent-via-dae', action='store_true', help='Route --agent-command via OpenClawDAE')
    parser.add_argument('--agent-backend', choices=['openclaw', 'ironclaw'], default='openclaw', help='Backend for --agent-via-dae')
    parser.add_argument(
        '--agent-no-api-keys',
        choices=['auto', 'on', 'off'],
        default='auto',
        help='Key isolation for --agent-via-dae (auto/on/off)',
    )

    # Re-parse with all arguments now that they're defined
    args = parser.parse_args()

    # Switchboard (feature flags + key env toggles)
    enable_pattern_memory = env_flag("FOUNDUPS_ENABLE_PATTERN_MEMORY", True)
    enable_wre = env_flag("FOUNDUPS_ENABLE_WRE", True)
    enable_wre_monitor = env_flag("FOUNDUPS_ENABLE_WRE_MONITOR", True)
    enable_qwen = env_flag("FOUNDUPS_ENABLE_QWEN", True)
    enable_self_improvement = env_flag("FOUNDUPS_ENABLE_SELF_IMPROVEMENT", True)
    enable_shorts_commands = env_flag("FOUNDUPS_ENABLE_SHORTS_COMMANDS", True) and not env_flag("FOUNDUPS_DISABLE_SHORTS_COMMANDS", False)
    enable_key_hygiene = env_flag("FOUNDUPS_ENABLE_KEY_HYGIENE", True)
    holo_skip_model = env_flag("HOLO_SKIP_MODEL", False)
    holo_silent = env_flag("HOLO_SILENT", False)
    holo_verbose = env_flag("HOLO_VERBOSE", False)
    holo_auto_index = env_flag("FOUNDUPS_HOLO_AUTO_INDEX", False)
    ai_overseer_breadcrumbs = env_flag("AI_OVERSEER_BREADCRUMBS", True)
    holo_offline = env_flag("HOLO_OFFLINE", False)
    holo_disable_pip_install = env_flag("HOLO_DISABLE_PIP_INSTALL", False)
    holo_breadcrumbs = env_flag("HOLO_BREADCRUMB_ENABLED", True)
    holo_breadcrumb_logs = env_flag("HOLO_BREADCRUMB_LOGS", True)
    startup_switchboard = {
        "pattern_memory": bool(PATTERN_MEMORY_AVAILABLE and enable_pattern_memory),
        "wre": bool(enable_wre),
        "wre_monitor": bool(enable_wre and enable_wre_monitor),
        "qwen": bool(enable_qwen),
        "self_improvement": bool(enable_self_improvement),
        "shorts_commands": bool(enable_shorts_commands),
        "key_hygiene": bool(enable_key_hygiene),
        "holo_skip_model": bool(holo_skip_model),
        "holo_silent": bool(holo_silent),
        "holo_verbose": bool(holo_verbose),
        "holo_auto_index": bool(holo_auto_index),
        "holo_offline": bool(holo_offline),
        "holo_disable_pip_install": bool(holo_disable_pip_install),
        "holo_breadcrumbs": bool(holo_breadcrumbs),
        "holo_breadcrumb_logs": bool(holo_breadcrumb_logs),
        "ai_overseer_breadcrumbs": bool(ai_overseer_breadcrumbs),
        "verbose": bool(args.verbose),
    }
    logger.info(f"[SWITCHBOARD] {json.dumps(startup_switchboard, sort_keys=True)}")

    # Initialize PatternMemory once for false-positive gating (WSP 48/60)
    pm = PatternMemory() if (PATTERN_MEMORY_AVAILABLE and enable_pattern_memory) else None
    if PATTERN_MEMORY_AVAILABLE and not enable_pattern_memory:
        logger.info("[SWITCHBOARD] PatternMemory disabled (FOUNDUPS_ENABLE_PATTERN_MEMORY=0)")

    def should_skip(task_key: str, entity_type: str = "task") -> Optional[Dict[str, Any]]:
        if not pm:
            return None
        try:
            return pm.get_false_positive_reason(entity_type, task_key)
        except Exception:
            return None

    # Handle CLI dispatch (non-interactive mode)
    if args.training_command:
        execute_training_command(args.training_command, args.targets, args.json_output)
        return
    if args.agent_command:
        try:
            from modules.communication.moltbot_bridge.src.action_cli import run_action_command

            no_api_keys = None
            if args.agent_no_api_keys == "on":
                no_api_keys = True
            elif args.agent_no_api_keys == "off":
                no_api_keys = False

            result = run_action_command(
                command=args.agent_command,
                sender="@012",
                channel="cli",
                session_key="main_menu_agent_command",
                repeat=args.agent_repeat,
                interval_sec=args.agent_interval_sec,
                via_dae=bool(args.agent_via_dae),
                backend=args.agent_backend,
                no_api_keys=no_api_keys,
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({"success": False, "error": str(exc)}, indent=2))
        return
    if args.ln_action:
        try:
            from modules.communication.moltbot_bridge.src.linkedin_social_adapter import (
                execute_linkedin_action,
            )

            params: Dict[str, str] = {}
            for raw in args.ln_param or []:
                if "=" not in raw:
                    continue
                key, value = raw.split("=", 1)
                key = key.strip().lower()
                value = value.strip()
                if key:
                    params[key] = value

            result = asyncio.run(execute_linkedin_action(args.ln_action.strip().lower(), params))
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({"success": False, "error": str(exc)}, indent=2))
        return
    if args.training_menu:
        run_training_system()
        return
    if args.follow_wsp is not None:
        task = (args.follow_wsp or "").strip()
        if not task:
            task = input("Enter follow-WSP task: ").strip()
        _run_follow_wsp(task)
        return
    if args.chat:
        from modules.infrastructure.cli.src.openclaw_chat import run_chat_repl
        run_chat_repl()
        return
    if args.voice:
        from modules.infrastructure.cli.src.openclaw_voice import run_voice_repl
        run_voice_repl()
        return
    if args.ironclaw_chat:
        from modules.infrastructure.cli.src.openclaw_chat import run_chat_repl
        run_chat_repl(conversation_backend="ironclaw", no_api_keys=True)
        return
    if args.ironclaw_voice:
        from modules.infrastructure.cli.src.openclaw_voice import run_voice_repl
        run_voice_repl(conversation_backend="ironclaw", no_api_keys=True)
        return
    if args.local_models:
        local_model_routing_menu()
        return
    if args.connect_wre:
        _run_connect_wre(verbose=args.verbose)
        return

    if args.status:
        check_instance_status()
        return
    if args.deps:
        try:
            from modules.infrastructure.dependency_launcher.src.dae_dependencies import ensure_dependencies
            asyncio.run(ensure_dependencies(require_lm_studio=True))
        except Exception as e:
            print(f"[ERROR] Dependency launcher failed: {e}")
        return
    elif args.git_daemon:
        skip = should_skip("gitpush_dae")
        if skip:
            print(f"[SKIP] Known false positive: gitpush_dae :: {skip.get('reason','')}")
            return
        launch_git_push_dae(run_once=False)
        return
    elif args.git:
        skip = should_skip("gitpush_dae")
        if skip:
            print(f"[SKIP] Known false positive: gitpush_dae :: {skip.get('reason','')}")
            return
        launch_git_push_dae(run_once=True)
        return
    elif args.youtube:
        skip = should_skip("youtube_dae")
        if skip:
            print(f"[SKIP] Known false positive: youtube_dae :: {skip.get('reason','')}")
            return
        asyncio.run(monitor_youtube(disable_lock=args.no_lock))
    elif args.holodae:
        skip = should_skip("holodae")
        if skip:
            print(f"[SKIP] Known false positive: holodae :: {skip.get('reason','')}")
            return
        run_holodae()
    elif args.amo:
        skip = should_skip("amo_dae")
        if skip:
            print(f"[SKIP] Known false positive: amo_dae :: {skip.get('reason','')}")
            return
        run_amo_dae()
    elif args.smd:
        skip = should_skip("social_media_dae")
        if skip:
            print(f"[SKIP] Known false positive: social_media_dae :: {skip.get('reason','')}")
            return
        run_social_media_dae()
    elif args.vision:
        skip = should_skip("vision_dae")
        if skip:
            print(f"[SKIP] Known false positive: vision_dae :: {skip.get('reason','')}")
            return
        run_vision_dae()
    elif args.pqn:
        skip = should_skip("pqn_dae")
        if skip:
            print(f"[SKIP] Known false positive: pqn_dae :: {skip.get('reason','')}")
            return
        run_pqn_dae()
    elif args.liberty:
        skip = should_skip("liberty_alert_mesh")
        if skip:
            print(f"[SKIP] Known false positive: liberty_alert_mesh :: {skip.get('reason','')}")
            return
        run_evade_net()
    elif args.liberty_dae:
        skip = should_skip("liberty_alert_dae")
        if skip:
            print(f"[SKIP] Known false positive: liberty_alert_dae :: {skip.get('reason','')}")
            return
        run_liberty_alert_dae()
    elif args.all:
        skip = should_skip("monitor_all_platforms")
        if skip:
            print(f"[SKIP] Known false positive: monitor_all_platforms :: {skip.get('reason','')}")
            return
        asyncio.run(monitor_all_platforms())
    elif args.mcp:
        skip = should_skip("mcp_gateway")
        if skip:
            print(f"[SKIP] Known false positive: mcp_gateway :: {skip.get('reason','')}")
            return
        show_mcp_services_menu()
    elif args.fam:
        while True:
            if handle_fam_menu():
                break
        return
    elif args.deploy_sse:
        from modules.infrastructure.cli.src.fam_menu import _deploy_cloud_run
        _deploy_cloud_run()
        return
    elif args.deploy_firebase:
        from modules.infrastructure.cli.src.fam_menu import _deploy_firebase
        _deploy_firebase()
        return
    else:
        # Interactive menu mode
        _run_interactive_menu(
            args=args,
            should_skip=should_skip,
            pm=pm,
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
            show_mcp_services_menu=show_mcp_services_menu,
            enable_key_hygiene=enable_key_hygiene,
            # antifaFM broadcaster functions
            run_antifafm_broadcaster=run_antifafm_broadcaster,
            start_antifafm_background=start_antifafm_background,
            stop_antifafm_background=stop_antifafm_background,
            get_antifafm_status=get_antifafm_status,
            run_suno_sync_cli=run_suno_sync_cli,
        )


def _run_interactive_menu(
    args,
    should_skip,
    pm,
    monitor_youtube,
    monitor_all_platforms,
    search_with_holoindex,
    check_instance_status,
    launch_git_push_dae,
    view_git_post_history,
    run_holodae,
    run_amo_dae,
    run_social_media_dae,
    run_vision_dae,
    run_pqn_dae,
    run_evade_net,
    run_liberty_alert_dae,
    run_training_system,
    show_mcp_services_menu,
    enable_key_hygiene: bool,
    # antifaFM broadcaster (optional)
    run_antifafm_broadcaster=None,
    start_antifafm_background=None,
    stop_antifafm_background=None,
    get_antifafm_status=None,
    run_suno_sync_cli=None,
) -> None:
    """Run interactive menu loop."""
    # Initialize centralized DAEmon (cardiovascular system)
    _central_daemon = None
    try:
        from modules.infrastructure.dae_daemon.src.dae_daemon import get_central_daemon
        from modules.infrastructure.dae_daemon.src.schemas import DAERegistration
        _central_daemon = get_central_daemon()
        if _central_daemon.state != "running":
            _central_daemon.start()

        # Pre-register known DAEs
        _default_daes = [
            ("yt_livechat", "YouTube LiveChat", "communication"),
            ("fam_daemon", "FAM DAEmon", "foundups"),
            ("openclaw", "OpenClaw DAE", "communication"),
            ("git_push_dae", "GitPush DAE", "infrastructure"),
            ("sim", "Simulator", "foundups"),
            ("pqn_portal", "PQN Portal", "ai_intelligence"),
            ("social_media", "Social Media DAE", "communication"),
            ("liberty_alert", "Liberty Alert", "communication"),
            ("holodae", "HoloDAE", "ai_intelligence"),
            ("vision_dae", "Vision DAE", "infrastructure"),
        ]
        for dae_id, dae_name, domain in _default_daes:
            _central_daemon.register_dae(
                DAERegistration(dae_id=dae_id, dae_name=dae_name, domain=domain)
            )
        logger.info("[CENTRAL-DAEMON] Cardiovascular system active (%d DAEs registered)", len(_default_daes))
    except Exception as exc:
        logger.debug("[CENTRAL-DAEMON] Not available: %s", exc)

    maybe_auto_index_holo(args.verbose, logger)
    print("\n" + "=" * 60)
    print("0102 FoundUps Agent - DAE Test Menu")
    print("=" * 60)

    # Instance check with timeout protection
    duplicates = _check_instances_with_timeout()

    if duplicates:
        if not _handle_duplicate_instances(duplicates, check_instance_status):
            return  # User chose to exit

    logger.info("[DAEMON] Main menu loop starting")
    print("[DEBUG-MAIN] About to enter main menu loop")

    # Main menu loop
    while True:
        logger.debug("[DAEMON] Top of menu loop - displaying options")
        print("[DEBUG-MAIN] Top of menu loop - displaying options")

        # Show the main menu
        print("0. Git Operations (Push + Post + History)          | --git")
        print("1. YouTube DAEs (Live/Comments/Shorts/Indexing)    | --youtube")
        print("2. HoloDAE (Code Intelligence & Search)            | --holodae")
        print("3. AMO DAE (Autonomous Moderation Operations)      | --amo")
        print("4. Social Media DAE (0102 Autonomous)              | --smd")
        print("5. Liberty Alert DAE (Community Protection)        | --liberty-dae")
        print("6. PQN Orchestration (Research & Alignment)        | --pqn")
        print("7. Liberty Alert (Mesh Alert System)               | --liberty")
        print("8. FoundUps Vision DAE (Pattern Sensorium)         | --vision")
        print("9. All DAEs (Full System)                          | --all")
        print("10. Exit")
        print("-" * 60)
        print("00. Check Instance Status & Health                 | --status")
        print("11. Qwen/Gemma Training System (Pattern Learning)")
        print("12. MCP Services (Model Context Protocol Gateway)  | --mcp")
        print("13. Automation Dependencies (Chrome + LM Studio)  | --deps")
        print("14. FoundUps Ecosystem (FAM + Simulator + Demo)  | --fam")
        print("15. Follow WSP (WSP_00 gated orchestration)      | --follow-wsp")
        print("16. OpenClaw / IronClaw (Unified Chat/Voice + Server/Portal/Runtime) | --chat --voice --ironclaw-chat --ironclaw-voice")
        print("17. DAE Dashboard (Cardiovascular Monitor)        | Central switch")
        print("18. WSP & Vocabulary Explainer (Developer Onboarding)")
        print("19. Connect WRE (preflight + readiness check)     | --connect-wre")
        print("20. antifaFM Broadcaster (YouTube Live Radio)     | --antifafm")
        print("=" * 60)
        print("CLI: --youtube --no-lock | --ln-action <action> --ln-param key=value")
        print("CLI: --agent-command \"youtube action comments channel=move2japan ...\" [--agent-via-dae]")
        print("=" * 60)

        try:
            choice = input("\nSelect option: ").strip()
            logger.info(f"[DAEMON] User selected option: '{choice}'")
            print(f"[DEBUG-MAIN] User selected option: '{choice}'")
        except (EOFError, KeyboardInterrupt) as e:
            logger.warning(f"[DAEMON] Input interrupted: {e}")
            print(f"[DEBUG-MAIN] Input interrupted: {e}")
            choice = "10"  # Default to exit on interrupt

        if choice == "0":
            handle_git_menu(launch_git_push_dae, view_git_post_history)

        elif choice == "1":
            # YouTube DAEs Menu
            while True:
                exit_to_main = handle_youtube_menu(
                    args=args,
                    should_skip=should_skip,
                    pm=pm,
                    monitor_youtube=monitor_youtube,
                    enable_key_hygiene=enable_key_hygiene,
                )
                if exit_to_main:
                    break

        elif choice == "2":
            # HoloDAE
            handle_holodae_menu(search_with_holoindex, run_holodae)

        elif choice == "3":
            # AMO DAE
            print("[AMO] Starting AMO DAE (Autonomous Moderation)...")
            try:
                from modules.communication.livechat.src.auto_moderator_dae import AutoModeratorDAE
                dae = AutoModeratorDAE()
                asyncio.run(dae.run())
            except KeyboardInterrupt:
                print("\n[STOP] AMO DAE stopped by user")

        elif choice == "4":
            # Social Media DAE (0102 Autonomous) - LinkedIn Automation
            while True:
                if handle_social_media_menu():
                    break

        elif choice == "5":
            # Liberty Alert DAE
            try:
                run_liberty_alert_dae()
            except KeyboardInterrupt:
                print("\n[STOP] Liberty Alert DAE stopped by user")

        elif choice == "6":
            # PQN Orchestration
            print("[INFO] Starting PQN Research DAE...")
            run_pqn_dae()

        elif choice == "7":
            # Liberty Alert mesh alert system
            try:
                run_evade_net()
            except KeyboardInterrupt:
                print("\n[STOP] Liberty Mesh Alert stopped by user")

        elif choice == "8":
            # FoundUps Vision DAE
            try:
                run_vision_dae()
            except KeyboardInterrupt:
                print("\n[STOP] Vision DAE stopped by user")

        elif choice == "9":
            # All DAEs
            print("[ALL] Starting ALL DAEs...")
            try:
                asyncio.run(monitor_all_platforms())
            except KeyboardInterrupt:
                print("\n[STOP] All DAEs stopped by user")

        elif choice == "10":
            print("[EXIT] Exiting...")
            break

        elif choice in {"00", "status"}:
            check_instance_status()
            input("\nPress Enter to continue...")

        elif choice == "11":
            # Qwen/Gemma Training System
            run_training_system()

        elif choice == "12":
            # MCP Services Gateway
            print("[MCP] Launching MCP Services Gateway...")
            show_mcp_services_menu()

        elif choice == "13":
            # Automation Dependencies
            print("[DEPS] Checking/launching local automation dependencies (Chrome + LM Studio)...")
            try:
                from modules.infrastructure.dependency_launcher.src.dae_dependencies import ensure_dependencies
                asyncio.run(ensure_dependencies(require_lm_studio=True))
            except Exception as e:
                print(f"[ERROR] Dependency launcher failed: {e}")

        elif choice == "14":
            # FoundUps Ecosystem (FAM + Simulator + Demo)
            while True:
                if handle_fam_menu():
                    break

        elif choice == "15":
            task = input("\nEnter follow-WSP task: ").strip()
            _run_follow_wsp(task)

        elif choice == "16":
            while True:
                if handle_openclaw_menu():
                    break

        elif choice == "17":
            _run_dae_dashboard(_central_daemon)

        elif choice == "18":
            # WSP & Vocabulary Explainer (Developer Onboarding)
            run_wsp_explainer()

        elif choice == "19":
            _run_connect_wre(verbose=args.verbose)
            input("\nPress Enter to continue...")

        elif choice == "20":
            # antifaFM Broadcaster (YouTube Live Radio)
            _handle_antifafm_menu(
                run_antifafm_broadcaster=run_antifafm_broadcaster,
                start_antifafm_background=start_antifafm_background,
                stop_antifafm_background=stop_antifafm_background,
                get_antifafm_status=get_antifafm_status,
                run_suno_sync_cli=run_suno_sync_cli,
            )

        else:
            print("Invalid choice. Please try again.")


def _run_follow_wsp(task: str) -> None:
    """Execute follow-WSP workflow with WSP_00 gate enforcement."""
    user_task = (task or "").strip()
    if not user_task:
        print("[WARN] follow-WSP task is required.")
        return

    print("[WSP] Running WSP orchestrator...")
    try:
        from modules.infrastructure.wsp_orchestrator.src.wsp_orchestrator import WSPOrchestrator
    except Exception as exc:
        print(f"[ERROR] Could not import WSP orchestrator: {exc}")
        return

    orchestrator = WSPOrchestrator(Path.cwd())
    try:
        results = asyncio.run(orchestrator.follow_wsp(user_task))
    except Exception as exc:
        print(f"[ERROR] follow-WSP execution failed: {exc}")
        return
    finally:
        try:
            asyncio.run(orchestrator.shutdown())
        except Exception:
            pass

    gate = results.get("wsp00_gate", {})
    print(
        f"[WSP] Gate passed={gate.get('gate_passed')} "
        f"| attempted_awakening={gate.get('attempted_awakening', False)}"
    )
    if not results.get("success", False):
        print("[WSP] follow-WSP blocked/failed.")
        if gate.get("message"):
            print(f"[WSP] {gate['message']}")
        return

    print(
        f"[WSP] Complete: tasks_completed={results.get('tasks_completed', 0)} "
        f"tasks_failed={results.get('tasks_failed', 0)}"
    )


def _run_connect_wre(verbose: bool = False) -> bool:
    """Connect WRE and report runtime readiness/enforcement state."""
    print("[CONNECT-WRE] coded=YES | command=--connect-wre")

    preflight_ok = False
    health: Dict[str, Any] = {}
    in_watch = None
    errors = []

    try:
        from modules.infrastructure.wre_core.src.dae_preflight import run_dae_preflight
        preflight_ok = bool(run_dae_preflight("connect_wre", quiet=False))
    except Exception as exc:
        errors.append(f"preflight import/run failed: {exc}")

    try:
        from modules.infrastructure.wre_core.src.dashboard_alerts import (
            DashboardAlertMonitor,
            check_dashboard_health,
        )
        monitor = DashboardAlertMonitor()
        in_watch = monitor.is_in_watch_period()
        health = check_dashboard_health() or {}
    except Exception as exc:
        errors.append(f"dashboard alerts unavailable: {exc}")
        health = {}

    enabled = os.getenv("WRE_DASHBOARD_PREFLIGHT", "1") != "0"
    manual_enforced = os.getenv("WRE_DASHBOARD_PREFLIGHT_ENFORCED", "0") != "0"
    auto_enforce = os.getenv("WRE_DASHBOARD_AUTO_ENFORCE", "1") != "0"
    insufficient_data = bool(health.get("insufficient_data", False))
    total_executions = int(health.get("total_executions", 0))
    min_samples = int(health.get("min_samples", int(os.getenv("WRE_DASHBOARD_MIN_SAMPLES", "25"))))
    alerts = health.get("alerts", []) if isinstance(health.get("alerts", []), list) else []
    critical = sum(1 for alert in alerts if alert.get("severity") == "critical")
    warnings = sum(1 for alert in alerts if alert.get("severity") == "warning")

    auto_enforced = bool(
        auto_enforce
        and in_watch is not None
        and not in_watch
        and not insufficient_data
    )
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

    connection_state = "CONNECTED" if preflight_ok and not errors else "PARTIAL"

    print(f"[CONNECT-WRE] connection={connection_state} readiness={readiness}")
    print(
        f"[CONNECT-WRE] preflight_enabled={enabled} manual_enforced={manual_enforced} "
        f"auto_enforce={auto_enforce} auto_enforced_now={auto_enforced}"
    )
    if in_watch is not None:
        mode = "WATCH" if in_watch else "STABLE"
        print(f"[CONNECT-WRE] mode={mode} samples={total_executions}/{min_samples}")
    else:
        print(f"[CONNECT-WRE] mode=UNKNOWN samples={total_executions}/{min_samples}")
    print(f"[CONNECT-WRE] alerts critical={critical} warnings={warnings}")

    if errors:
        print("[CONNECT-WRE] issues detected:")
        for err in errors:
            print(f"  - {err}")
    elif verbose:
        print("[CONNECT-WRE] no import/runtime issues detected.")

    return readiness in {"READY", "INSUFFICIENT_DATA", "DEGRADED"} and preflight_ok


def _run_dae_dashboard(central_daemon) -> None:
    """DAE Dashboard — cardiovascular monitor with centralized switch."""
    if central_daemon is None:
        print("\n  [WARN] Central DAEmon not available.")
        print("  The cardiovascular system failed to initialize.")
        input("\n  Enter to continue...")
        return

    _STATE_ICONS = {
        "registered": "[--]",
        "starting": "[..]",
        "running": "[OK]",
        "degraded": "[!!]",
        "stopping": "[..]",
        "stopped": "[--]",
        "detached": "[XX]",
        "crashed": "[XX]",
    }

    while True:
        dashboard = central_daemon.get_dashboard()
        daes = dashboard.get("daes", {})
        reports = dashboard.get("killswitch_reports", [])
        store = dashboard.get("event_store", {})

        print("\n" + "=" * 60)
        print("  DAE Dashboard (Cardiovascular Monitor)")
        print("  " + "-" * 56)

        # DAE status table
        for dae_id, info in sorted(daes.items()):
            icon = _STATE_ICONS.get(info["state"], "[??]")
            enabled = "ON " if info["enabled"] else "OFF"
            name = info.get("name", dae_id)[:25]
            domain = info.get("domain", "?")[:12]
            print(f"  {icon} {enabled} {dae_id:<18} {name:<26} [{domain}]")

        # Stats
        print("  " + "-" * 56)
        print(f"  Events: {store.get('total_events', 0)} | Daemon: {dashboard['daemon_state']}")

        # Killswitch reports
        if reports:
            print(f"\n  KILLSWITCH REPORTS ({len(reports)}):")
            for r in reports[-3:]:  # Show last 3
                print(f"    [XX] {r['dae_id']}: {r['reason'][:50]}")

        # Commands
        print("\n  Commands: enable <id> | disable <id> | status | back")
        print("=" * 60)

        try:
            cmd = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if cmd in ("back", "0", "q", "quit", "exit"):
            break
        elif cmd == "status":
            continue  # Refresh
        elif cmd.startswith("enable "):
            dae_id = cmd.split(" ", 1)[1].strip()
            if central_daemon.enable_dae(dae_id):
                print(f"  [OK] Enabled: {dae_id}")
            else:
                print(f"  [WARN] Unknown DAE: {dae_id}")
        elif cmd.startswith("disable "):
            dae_id = cmd.split(" ", 1)[1].strip()
            if central_daemon.disable_dae(dae_id):
                print(f"  [OK] Disabled: {dae_id}")
            else:
                print(f"  [WARN] Unknown DAE: {dae_id}")
        elif cmd:
            print(f"  Unknown command: {cmd}")


def _check_instances_with_timeout() -> list:
    """Check for duplicate instances with timeout protection."""
    print("[INFO] Checking for duplicate instances (timeout: 10s)...")

    duplicates = []
    try:
        from modules.infrastructure.instance_lock.src.instance_manager import get_instance_lock
        lock = get_instance_lock("youtube_monitor")

        result_holder = []

        def check_with_timeout():
            try:
                result = lock.check_duplicates(quiet=True)
                result_holder.append(result)
            except Exception:
                result_holder.append(None)

        check_thread = threading.Thread(target=check_with_timeout, daemon=True)
        check_thread.start()
        check_thread.join(timeout=10.0)

        if check_thread.is_alive():
            print("[WARN] Instance check timed out (>10s) - skipping duplicate detection")
            print("   Use --status to manually check for running instances\n")
            duplicates = []
        elif result_holder and result_holder[0] is not None:
            duplicates = result_holder[0]
        else:
            duplicates = []

    except Exception as e:
        print(f"[WARN] Could not check instances: {e}")
        print("   Use --status to manually check for running instances\n")
        duplicates = []

    return duplicates


def _handle_duplicate_instances(duplicates: list, check_instance_status) -> bool:
    """
    Handle duplicate instances - returns True to continue, False to exit.
    """
    while True:
        print(f"[WARN] FOUND {len(duplicates)} RUNNING INSTANCE(S)")
        print("\nWhat would you like to do?")
        print("1. Kill all instances and continue")
        print("2. Show detailed status")
        print("3. Continue anyway (may cause conflicts)")
        print("4. Exit")
        print("-" * 40)

        try:
            choice = input("Select option (1-4): ").strip().lstrip(']').lstrip('[')
            print(f"[DEBUG] Received choice: '{choice}' (repr: {repr(choice)})")
        except (EOFError, KeyboardInterrupt) as e:
            print(f"[DEBUG] Input interrupted: {e}")
            choice = "4"

        if choice == "1":
            print("\n[INFO] Killing duplicate instances...")
            killed_pids = []
            failed_pids = []

            current_pid = os.getpid()

            for pid in duplicates:
                if pid == current_pid:
                    continue

                try:
                    print(f"   [INFO] Terminating PID {pid}...")
                    process = psutil.Process(pid)
                    process.terminate()

                    gone, alive = psutil.wait_procs([process], timeout=5)

                    if alive:
                        print(f"   [INFO] Force killing PID {pid}...")
                        process.kill()
                        gone, alive = psutil.wait_procs([process], timeout=2)

                    if not alive:
                        killed_pids.append(pid)
                        print(f"   [INFO]PID {pid} terminated successfully")
                    else:
                        failed_pids.append(pid)
                        print(f"   [ERROR]Failed to kill PID {pid}")

                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    print(f"   [WARN] Could not kill PID {pid}: {e}")
                    failed_pids.append(pid)

            if killed_pids:
                print(f"\n[INFO]Successfully killed {len(killed_pids)} instance(s): {killed_pids}")
            if failed_pids:
                print(f"[WARN] Failed to kill {len(failed_pids)} instance(s): {failed_pids}")

            print("   Proceeding to main menu...\n")
            return True

        elif choice == "2":
            print("\n" + "=" * 50)
            check_instance_status()
            print("=" * 50)
            input("\nPress Enter to continue...")

        elif choice == "3":
            print("[WARN] Continuing with potential conflicts...\n")
            return True

        elif choice == "4":
            print("[INFO] Exiting...")
            return False

        else:
            print(f"[ERROR]Invalid choice '{choice}'. Please enter 1, 2, 3, or 4.")
            print("   Try again...\n")
            continue


def _handle_antifafm_menu(
    run_antifafm_broadcaster=None,
    start_antifafm_background=None,
    stop_antifafm_background=None,
    get_antifafm_status=None,
    run_suno_sync_cli=None,
) -> None:
    """
    Handle antifaFM Broadcaster menu.

    Options:
    1. Start in foreground (blocking)
    2. Start in background (non-blocking)
    3. Stop background instance
    4. Show status
    5. Back to main menu
    """
    if run_antifafm_broadcaster is None:
        print("[RADIO] antifaFM broadcaster not available")
        print("[INFO] Check that the module is properly installed")
        input("\nPress Enter to continue...")
        return

    while True:
        print("\n" + "=" * 60)
        print("antifaFM YouTube Live Broadcaster")
        print("=" * 60)

        # Show current status
        if get_antifafm_status:
            status = get_antifafm_status()
            if status.get("running"):
                print(f"[STATUS] BROADCASTING - Uptime: {status.get('uptime_formatted', 'N/A')}")
            else:
                print("[STATUS] STOPPED")

        print("\n1. Start with OBS Mode (OBS streams, script handles chat)")
        print("2. Start with FFmpeg (script handles everything)")
        print("3. Start in Background (FFmpeg mode)")
        print("4. Stop Background Broadcaster")
        print("5. Show Detailed Status")
        print("6. Video Library (manage background videos)")
        print("7. Extract Lyrics via STT (FULLY AUTOMATED - 012's 238 songs)")
        print("0. Back to Main Menu")
        print("=" * 60)

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            # OBS Mode - OBS handles streaming, script handles chat/schemas
            print("\n[RADIO] Starting antifaFM in OBS MODE...")
            print("[INFO] OBS handles streaming - script handles chat commands + schemas")
            print("[INFO] Make sure OBS is streaming before continuing!")
            print("[INFO] Press Ctrl+C to stop")
            os.environ["ANTIFAFM_USE_OBS"] = "1"
            run_antifafm_broadcaster()

        elif choice == "2":
            print("\n[RADIO] Starting antifaFM in FFmpeg mode (foreground)...")
            print("[INFO] FFmpeg handles streaming to YouTube")
            print("[INFO] Press Ctrl+C to stop")
            os.environ.pop("ANTIFAFM_USE_OBS", None)  # Ensure OBS mode is off
            run_antifafm_broadcaster()

        elif choice == "3":
            if start_antifafm_background:
                print("\n[RADIO] Starting antifaFM in background (FFmpeg mode)...")
                os.environ.pop("ANTIFAFM_USE_OBS", None)  # Ensure OBS mode is off
                start_antifafm_background()
            else:
                print("[ERROR] Background start not available")

        elif choice == "4":
            if stop_antifafm_background:
                print("\n[RADIO] Stopping background broadcaster...")
                stop_antifafm_background()
            else:
                print("[ERROR] Background stop not available")

        elif choice == "5":
            if get_antifafm_status:
                import json
                status = get_antifafm_status()
                print("\n[STATUS] antifaFM Broadcaster Status:")
                print(json.dumps(status, indent=2, default=str))
            else:
                print("[ERROR] Status not available")
            input("\nPress Enter to continue...")

        elif choice == "6":
            _handle_video_library_menu()

        elif choice == "7":
            # Suno Lyrics STT Extraction - FULLY AUTOMATED (no browser needed)
            print("\n[SUNO-STT] Fully Automated Lyrics Extraction")
            print("=" * 60)
            print("Pipeline: Suno CDN → Download MP3 → faster-whisper STT → Dedup")
            print()
            print("This will:")
            print("  1. Download audio from Suno CDN (cdn1.suno.ai)")
            print("  2. Transcribe lyrics via Speech-to-Text (faster-whisper)")
            print("  3. Deduplicate using SHA256 hashing")
            print("  4. Store in SQLite for karaoke mode")
            print()
            print("NO MANUAL WORK NEEDED - fully automated!")
            print()
            limit = input("Limit songs (Enter for all 238, or number): ").strip()
            max_songs = int(limit) if limit.isdigit() else 0
            model = input("Model size (tiny/base/small, default=base): ").strip() or "base"
            print()
            print("[STARTING] This may take a while for full playlist...")
            print()
            try:
                from modules.platform_integration.antifafm_broadcaster.scripts.launch import run_suno_stt_extract
                run_suno_stt_extract(max_songs=max_songs, model_size=model)
            except ImportError as e:
                print(f"[ERROR] Could not import STT extractor: {e}")
                print("[FIX] Install: pip install faster-whisper librosa")
            except Exception as e:
                print(f"[ERROR] Extraction failed: {e}")
            input("\nPress Enter to continue...")

        elif choice == "0":
            break

        else:
            print(f"[ERROR] Invalid choice '{choice}'")


def _handle_video_library_menu() -> None:
    """Manage antifaFM video library."""
    try:
        from modules.platform_integration.antifafm_broadcaster.src.video_library import VideoLibrary
    except ImportError as e:
        print(f"[ERROR] Video library not available: {e}")
        input("\nPress Enter to continue...")
        return

    library = VideoLibrary()

    while True:
        print("\n" + "=" * 60)
        print("antifaFM Video Library")
        print("=" * 60)

        status = library.get_status()
        print(f"[LIBRARY] {status['total_videos']} videos ({status['ready']} ready, {status['pending']} pending)")
        print(f"[LIBRARY] Total size: {status['total_size_mb']:.1f} MB")

        print("\n1. List Videos")
        print("2. Scan for New Videos (register untracked)")
        print("3. Add Video (YouTube URL)")
        print("0. Back")
        print("=" * 60)

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            videos = library.list_videos()
            print(f"\n[VIDEOS] {len(videos)} total:")
            for v in videos:
                print(f"  - {v.filename} ({v.status.value}) - {v.title}")
            input("\nPress Enter to continue...")

        elif choice == "2":
            print("\n[SCAN] Scanning for unregistered videos...")
            result = library.scan_for_unregistered_videos("012")
            print(f"[SCAN] {result.get('message', 'Done')}")
            if result.get("new_videos"):
                for v in result["new_videos"]:
                    print(f"  + {v}")
            input("\nPress Enter to continue...")

        elif choice == "3":
            url = input("\nEnter YouTube URL: ").strip()
            if url:
                print(f"\n[ADD] Adding video: {url}")
                result = library.add_video(url, "012", download_now=True)
                if result.get("success"):
                    print(f"[OK] {result.get('message', 'Added')}")
                else:
                    print(f"[FAIL] {result.get('message', 'Failed')}")
                    if result.get("manual_instructions"):
                        print("\nManual download instructions:")
                        for step in result["manual_instructions"]:
                            print(f"  {step}")
            input("\nPress Enter to continue...")

        elif choice == "0":
            break

        else:
            print(f"[ERROR] Invalid choice '{choice}'")
