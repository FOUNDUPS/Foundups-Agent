"""
OpenClaw Submenu - All ways to talk to 0102.

WSP 62 (separate file), WSP 72 (lazy imports), WSP 73 (Partner-Principal-Associate).
"""

import logging
import os
import shlex
import subprocess
import sys
import json
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]


def _get_openclaw_runtime_broker():
    """Return broker when the runtime control plane is available."""
    try:
        from modules.infrastructure.dae_daemon.src.dae_launch_broker import (
            get_dae_launch_broker,
        )

        return get_dae_launch_broker()
    except Exception:
        return None


def handle_openclaw_menu() -> bool:
    """OpenClaw engagement menu. Returns True to exit to main menu."""
    print("\n  OpenClaw / IronClaw (Talk to 0102)")
    print("  " + "-" * 40)
    print("  Backend switch is in-session: `backend ironclaw` / `backend openclaw`.")
    print("  1. Claw Chat (unified backend) | --chat / --ironclaw-chat")
    print("  2. Claw Voice (unified backend) | --voice / --ironclaw-voice")
    print("  3. OpenClaw Webhook Server (:18800)")
    print("  4. PQN Portal (:8080)")
    print("  5. IronClaw Runtime Status")
    print("  6. Start IronClaw Gateway (IRONCLAW_START_CMD)")
    print("  7. Local Model Routing Editor (LOCAL_MODEL_*)")
    print("  8. Action Command Runner (standalone test)")
    print("  9. OpenClaw/IronClaw Daily Audit (coverage + drift)")
    print("  10. External Stream Chat (engage in any YouTube Live)")
    print("  0. Back")
    print()

    try:
        choice = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        return True

    if choice == "0":
        return True
    elif choice == "1":
        _chat_repl()
    elif choice == "2":
        _voice_repl()
    elif choice == "3":
        _webhook_server()
    elif choice == "4":
        _pqn_portal()
    elif choice == "5":
        _ironclaw_status()
    elif choice == "6":
        _start_ironclaw_gateway()
    elif choice == "7":
        _local_model_routing_editor()
    elif choice == "8":
        _action_command_runner()
    elif choice == "9":
        _daily_openclaw_ironclaw_audit()
    elif choice == "10":
        _external_stream_chat()
    else:
        print("  Invalid choice")

    return False


def _default_backend() -> str:
    """Resolve default backend for unified chat/voice entry points."""
    backend = (os.getenv("OPENCLAW_DEFAULT_BACKEND", "openclaw") or "openclaw").strip().lower()
    if backend not in {"openclaw", "ironclaw"}:
        backend = "openclaw"
    return backend


def _chat_repl(backend: str | None = None, no_api_keys: bool | None = None) -> None:
    """Launch text chat REPL with OpenClawDAE."""
    backend = (backend or _default_backend()).strip().lower()
    mode = "IronClaw" if backend == "ironclaw" else "OpenClaw"
    print(f"\n  Starting {mode} Chat (text mode)...")
    print("  Type messages, 'exit' to quit\n")
    try:
        from modules.infrastructure.cli.src.openclaw_chat import run_chat_repl
        run_chat_repl(conversation_backend=backend, no_api_keys=no_api_keys)
    except KeyboardInterrupt:
        print("\n  Stopped")
    except Exception as e:
        print(f"  Failed: {e}")


def _voice_repl(backend: str | None = None, no_api_keys: bool | None = None) -> None:
    """Launch voice REPL with STT/TTS degradation chain."""
    backend = (backend or _default_backend()).strip().lower()
    mode = "IronClaw" if backend == "ironclaw" else "OpenClaw"
    print(f"\n  Starting {mode} Voice (headset mode)...")
    print("  STT: faster-whisper -> Google Speech -> keyboard")
    print("  TTS: Edge TTS -> pyttsx3 -> print-only")
    print("  Voice mode: auto-listen by default, cue '0102 ...' to barge-in")
    print("  Runtime switch: say 'backend ironclaw' or 'backend openclaw'\n")
    try:
        from modules.infrastructure.cli.src.openclaw_voice import run_voice_repl
        run_voice_repl(conversation_backend=backend, no_api_keys=no_api_keys)
    except KeyboardInterrupt:
        print("\n  Stopped")
    except Exception as e:
        print(f"  Failed: {e}")


def _webhook_server() -> None:
    """Start OpenClaw webhook receiver (FastAPI on :18800)."""
    broker = _get_openclaw_runtime_broker()
    if broker is not None:
        status = broker.get_runtime_status("openclaw")
        if status.get("registered"):
            if status.get("running"):
                print("\n  OpenClaw resident service is already running.")
                print(f"  state={status.get('state')} run_count={status.get('run_count')}")
            else:
                result = broker.start_dae("openclaw", actor_id="012")
                launch_status = result.get("status", result.get("error", "unknown"))
                print(f"\n  OpenClaw resident service -> {launch_status}")
            print("  POST http://127.0.0.1:18800/webhook/openclaw")
            print("  GET  http://127.0.0.1:18800/health")
            input("\n  Enter to continue...")
            return

    webhook_script = (
        REPO_ROOT / "modules" / "communication"
        / "moltbot_bridge" / "src" / "webhook_receiver.py"
    )
    if not webhook_script.exists():
        print(f"  Not found: {webhook_script}")
        input("\n  Enter to continue...")
        return

    port = os.getenv("OPENCLAW_BRIDGE_PORT", "18800")
    print(f"\n  OpenClaw webhook on :{port}")
    print(f"  POST http://localhost:{port}/webhook/openclaw")
    print("  GET  http://localhost:{port}/health")
    print("  Ctrl+C to stop\n")

    try:
        subprocess.run([sys.executable, str(webhook_script)], cwd=str(REPO_ROOT))
    except KeyboardInterrupt:
        print("\n  Stopped")
    except Exception as e:
        print(f"  Failed: {e}")

    input("\n  Enter to continue...")


def _pqn_portal() -> None:
    """Start PQN Portal (FastAPI on :8080)."""
    print("\n  Starting PQN Portal on :8080...")
    print("  POST http://localhost:8080/awaken")
    print("  GET  http://localhost:8080/gallery")
    print("  GET  http://localhost:8080/runs/{id}/stream  (SSE)")
    print("  Ctrl+C to stop\n")

    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn",
             "modules.foundups.pqn_portal.src.api:app",
             "--host", "127.0.0.1", "--port", "8080", "--reload"],
            cwd=str(REPO_ROOT),
        )
    except KeyboardInterrupt:
        print("\n  Stopped")
    except Exception as e:
        print(f"  Failed: {e}")

    input("\n  Enter to continue...")


def _ironclaw_status() -> None:
    """Show IronClaw gateway status/config."""
    print("\n  Checking IronClaw runtime...")
    try:
        from modules.communication.moltbot_bridge.src.ironclaw_gateway_client import (
            IronClawGatewayClient,
            env_truthy,
        )

        client = IronClawGatewayClient()
        cfg = client.config
        healthy, detail = client.health()
        models = client.list_models()

        print(f"  Base URL: {cfg.base_url}")
        print(f"  Model: {cfg.model}")
        print(f"  Key isolation: {'ON' if cfg.no_api_keys else 'OFF'}")
        print(
            "  IronClaw strict mode: "
            f"{'ON' if env_truthy('OPENCLAW_IRONCLAW_STRICT', '1') else 'OFF'}"
            " (local fallback="
            f"{'ON' if env_truthy('OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK', '0') else 'OFF'})"
        )
        try:
            from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE

            dae = OpenClawDAE(repo_root=REPO_ROOT, conversation_backend="ironclaw")
            identity = dae.get_identity_snapshot(include_runtime_probe=True)
            print(
                "  0102 taxonomy: "
                f"genus={identity['genus']} "
                f"lineage={identity['lineage']} "
                f"model_family={identity['model_family']} "
                f"model_name={identity['model_name']}"
            )
        except Exception:
            print(
                "  0102 taxonomy: "
                f"genus={'Ex.machina' if (os.getenv('OPENCLAW_IDENTITY_GENUS', 'Ex.machina').strip() or 'Ex.machina').lower() == 'ex.machina' else (os.getenv('OPENCLAW_IDENTITY_GENUS', 'Ex.machina').strip() or 'Ex.machina').lower()} "
                f"lineage={(os.getenv('OPENCLAW_IDENTITY_MODEL_FAMILY', 'davinci').strip() or 'davinci').lower()} "
                f"model_family={(os.getenv('OPENCLAW_IDENTITY_MODEL_FAMILY', 'davinci').strip() or 'davinci').lower()} "
                f"model_name={(os.getenv('OPENCLAW_IDENTITY_MODEL_NAME', '{{model}}').strip() or '{model}').lower()}"
            )
        print(f"  Protocol anchor: {(os.getenv('OPENCLAW_IDENTITY_PROTOCOL', 'wsp_00').strip() or 'wsp_00').lower()}")
        print(
            "  WSP_00 boot prompt: "
            f"{'ON' if env_truthy('OPENCLAW_WSP00_BOOT', '1') else 'OFF'} "
            f"(mode={(os.getenv('OPENCLAW_WSP00_BOOT_MODE', 'compact').strip() or 'compact').lower()}, "
            f"file_override={'YES' if bool((os.getenv('OPENCLAW_WSP00_PROMPT_FILE', '').strip())) else 'NO'})"
        )
        print(f"  Auth token configured: {'YES' if bool(cfg.auth_token) else 'NO'}")
        print(f"  Health: {'PASS' if healthy else 'FAIL'} ({detail})")
        if models:
            print(f"  Models: {', '.join(models[:5])}")
        else:
            print("  Models: none returned (or /v1/models unavailable)")

        try:
            from modules.infrastructure.shared_utilities.local_model_selection import (
                resolve_model_selection,
            )

            code = resolve_model_selection("code")
            state = "OK" if code.exists else "MISSING"
            print(f"  Local code model: {code.path} ({state}, source={code.source})")
        except Exception:
            pass

        try:
            from modules.ai_intelligence.ai_overseer.src.ai_overseer import (
                AIIntelligenceOverseer,
            )

            # Lightweight panel probe (avoid full Overseer boot in CLI status path).
            overseer = object.__new__(AIIntelligenceOverseer)
            overseer.ironclaw_runtime_last_status = None
            panel = AIIntelligenceOverseer.monitor_ironclaw_runtime(overseer, force=True)
            print("  AI Overseer panel:")
            print(
                "    healthy="
                f"{panel.get('healthy')} models={panel.get('models_count', 0)} "
                f"key_isolation={panel.get('key_isolation')}"
            )
        except Exception as exc:
            print(f"  AI Overseer panel unavailable: {exc}")
    except Exception as exc:
        print(f"  Failed to query IronClaw runtime: {exc}")

    input("\n  Enter to continue...")


def _start_ironclaw_gateway() -> None:
    """Start IronClaw gateway via env-configured command."""
    cmd = os.getenv("IRONCLAW_START_CMD", "").strip()
    if not cmd:
        print("\n  IRONCLAW_START_CMD is not set.")
        print("  Set it in .env with your preferred startup command.")
        print("  Example: IRONCLAW_START_CMD=ironclaw gateway")
        print("  Example: IRONCLAW_START_CMD=docker compose up ironclaw")
        input("\n  Enter to continue...")
        return

    try:
        from modules.communication.moltbot_bridge.src.ironclaw_gateway_client import (
            scrub_sensitive_env,
            env_truthy,
        )

        child_env = os.environ.copy()
        no_api_keys = env_truthy("IRONCLAW_NO_API_KEYS", "1")
        if no_api_keys:
            child_env = scrub_sensitive_env(child_env)

        print(f"\n  Starting IronClaw with command: {cmd}")
        print(f"  Key isolation: {'ON' if no_api_keys else 'OFF'}")
        subprocess.run(
            shlex.split(cmd),
            cwd=str(REPO_ROOT),
            env=child_env,
        )
    except KeyboardInterrupt:
        print("\n  Stopped")
    except Exception as exc:
        print(f"  Failed: {exc}")

    input("\n  Enter to continue...")


def _local_model_routing_editor() -> None:
    """Open centralized LOCAL_MODEL_* routing editor."""
    try:
        from modules.infrastructure.cli.src.utilities import local_model_routing_menu

        local_model_routing_menu()
    except Exception as exc:
        print(f"  Failed to open Local Model Routing editor: {exc}")


def _action_command_runner() -> None:
    """Run standalone action commands for LinkedIn/X/YouTube/social campaigns."""
    print("\n  Action Command Runner")
    print("  Examples:")
    print("    linkedin action read_feed max_posts=3")
    print("    x action post content=\"foundups update\" dry_run=true")
    print("    youtube action comments channel=move2japan max_comments=2 like=true heart=true reply=false")
    print("    social campaign research_x_to_ln_group content=\"new research summary\" dry_run=true")
    print("")
    try:
        command = input("  command> ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if not command:
        print("  No command entered.")
        return

    try:
        repeat_raw = input("  repeat (blank=1)> ").strip()
        repeat = int(repeat_raw) if repeat_raw else 1
    except Exception:
        repeat = 1

    try:
        interval_raw = input("  interval_sec (blank=0)> ").strip()
        interval_sec = float(interval_raw) if interval_raw else 0.0
    except Exception:
        interval_sec = 0.0

    via_dae = False
    backend = "openclaw"
    use_dae = input("  route via OpenClawDAE? [y/N]> ").strip().lower()
    if use_dae in {"y", "yes"}:
        via_dae = True
        backend_choice = input("  backend (openclaw/ironclaw, blank=openclaw)> ").strip().lower()
        if backend_choice in {"openclaw", "ironclaw"}:
            backend = backend_choice

    try:
        from modules.communication.moltbot_bridge.src.action_cli import run_action_command

        result = run_action_command(
            command=command,
            sender="@012",
            channel="menu16",
            session_key="openclaw_menu_action_runner",
            repeat=repeat,
            interval_sec=interval_sec,
            via_dae=via_dae,
            backend=backend,
        )
        print("\n" + json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(f"  Action command failed: {exc}")

    input("\n  Enter to continue...")


def _daily_openclaw_ironclaw_audit() -> None:
    """Run and print OpenClaw/IronClaw daily capability + drift audit."""
    print("\n  Running OpenClaw/IronClaw daily audit...")
    try:
        from modules.communication.moltbot_bridge.src.openclaw_capability_audit import (
            run_daily_audit,
        )

        report = run_daily_audit(repo_root=REPO_ROOT, write_files=True)
        coverage = report.get("cli_coverage", {})
        counts = coverage.get("counts", {})
        ratio = coverage.get("coverage_ratio", 0.0)
        switch_audit = report.get("switch_model_drift", {})
        runtime = report.get("ironclaw_runtime", {})

        print("  [SUMMARY]")
        print(
            "    CLI coverage: "
            f"direct={counts.get('direct', 0)} "
            f"partial={counts.get('partial', 0)} "
            f"unmapped={counts.get('unmapped', 0)} "
            f"(ratio={ratio:.2f})"
        )
        print(
            "    Switchable external models: "
            f"{len(switch_audit.get('switchable_external_models', []))}"
        )
        print(
            "    Quick models not switchable: "
            f"{len((switch_audit.get('provider_quick_models_not_switchable') or {}))}"
        )
        print(
            "    IronClaw runtime: "
            f"healthy={runtime.get('healthy', False)} "
            f"detail={runtime.get('detail', 'unknown')}"
        )

        recs = report.get("recommendations", []) or []
        print("\n  [RECOMMENDATIONS]")
        for idx, rec in enumerate(recs[:8], start=1):
            print(f"    {idx}. {rec}")

        artifacts = report.get("artifacts", {}) or {}
        latest = artifacts.get("latest")
        if latest:
            print(f"\n  Report saved: {latest}")
    except Exception as exc:
        print(f"  Audit failed: {exc}")

    input("\n  Enter to continue...")


def _external_stream_chat() -> None:
    """
    External Stream Chat - DOM-based engagement with public YouTube Live streams.

    Enables OpenClaw to engage in ANY YouTube Live chat, not just owned channels.
    Uses Selenium DOM automation (can't use API for streams we don't own).
    """
    import asyncio

    print("\n  External Stream Chat - Engage in any YouTube Live")
    print("  " + "-" * 50)
    print("  This uses DOM automation to interact with chat on streams you don't own.")
    print("  Requires Edge browser with debug port open (9223).")
    print()
    print("  1. Interactive Mode (!send, !party, !watch, !status)")
    print("  2. Quick Send (enter URL + message)")
    print("  3. Party Mode (click hearts on stream)")
    print("  4. Watch Only (navigate + show status)")
    print("  0. Back")
    print()

    try:
        choice = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice == "0":
        return

    # Get URL for all modes except interactive (which can set URL later)
    url = None
    if choice != "1":
        try:
            url = input("  YouTube Live URL: ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if not url:
            print("  No URL provided")
            input("\n  Enter to continue...")
            return

    try:
        from modules.ai_intelligence.ai_overseer.skillz.external_stream_chat.src.stream_chat_dae import (
            ExternalStreamChat,
        )

        if choice == "1":
            # Interactive mode - uses the DAE's built-in CLI
            print("\n  Starting interactive mode...")
            print("  Commands: !send <msg>, !party, !watch <url>, !status, !quit")
            print()

            async def run_interactive():
                chat = ExternalStreamChat(url=url)
                if not await chat.connect():
                    print("  [FAIL] Could not connect to browser")
                    return

                while True:
                    try:
                        cmd = input("\n  > ").strip()

                        if cmd.startswith("!send "):
                            msg = cmd[6:].strip()
                            await chat.send_message(msg)

                        elif cmd == "!party":
                            await chat.party()

                        elif cmd.startswith("!watch "):
                            new_url = cmd[7:].strip()
                            await chat.set_url(new_url)

                        elif cmd == "!status":
                            status = chat.get_status()
                            for k, v in status.items():
                                print(f"    {k}: {v}")

                        elif cmd == "!quit":
                            break

                        else:
                            print("  Unknown command. Try: !send, !party, !watch, !status, !quit")

                    except KeyboardInterrupt:
                        break

                chat.disconnect()

            asyncio.run(run_interactive())

        elif choice == "2":
            # Quick send
            try:
                message = input("  Message to send: ").strip()
            except (EOFError, KeyboardInterrupt):
                return

            if not message:
                print("  No message provided")
                input("\n  Enter to continue...")
                return

            async def run_send():
                chat = ExternalStreamChat(url=url)
                if not await chat.connect():
                    print("  [FAIL] Could not connect")
                    return
                success = await chat.send_message(message)
                print(f"  {'[OK] Sent' if success else '[FAIL] Failed'}: {message[:50]}...")
                chat.disconnect()

            asyncio.run(run_send())

        elif choice == "3":
            # Party mode
            try:
                count_str = input("  Number of heart clicks (default 10): ").strip()
                count = int(count_str) if count_str else 10
            except (ValueError, EOFError, KeyboardInterrupt):
                count = 10

            async def run_party():
                chat = ExternalStreamChat(url=url)
                if not await chat.connect():
                    print("  [FAIL] Could not connect")
                    return
                clicks = await chat.party_loop(count)
                print(f"  [PARTY] Completed: {clicks}/{count} clicks")
                chat.disconnect()

            asyncio.run(run_party())

        elif choice == "4":
            # Watch only
            async def run_watch():
                chat = ExternalStreamChat(url=url)
                if not await chat.connect():
                    print("  [FAIL] Could not connect")
                    return
                status = chat.get_status()
                print("\n  Stream Status:")
                for k, v in status.items():
                    print(f"    {k}: {v}")

                # Show recent messages
                messages = await chat.get_recent_messages(5)
                if messages:
                    print("\n  Recent Chat:")
                    for msg in messages:
                        print(f"    [{msg.author}]: {msg.text[:60]}...")

                chat.disconnect()

            asyncio.run(run_watch())

    except ImportError as e:
        print(f"  [FAIL] Module not available: {e}")
    except Exception as e:
        print(f"  [FAIL] Error: {e}")

    input("\n  Enter to continue...")
