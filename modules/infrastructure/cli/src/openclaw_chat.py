"""
OpenClaw Local Chat REPL - Talk to 0102 directly from terminal.

Bypasses the Node.js gateway + webhook stack entirely.
Calls OpenClawDAE.process() directly with commander authority.

Usage:
    python -m modules.infrastructure.cli.src.openclaw_chat
    python main.py --chat

WSP Compliance:
    WSP 73: Partner (012 terminal) -> Principal (OpenClawDAE) -> Associates (domain DAEs)
    WSP 72: No new dependencies — reuses existing OpenClawDAE
"""

import asyncio
import os
import re
import sys
from pathlib import Path
from typing import Optional, Dict, Any


def _ensure_repo_root():
    """Add repo root to sys.path if not already present."""
    repo = Path(__file__).resolve().parents[4]  # cli/src -> cli -> infrastructure -> modules -> repo
    root_str = str(repo)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return repo


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _parse_backend_switch_command(message: str) -> Optional[str]:
    """Parse local backend switch commands from chat input."""
    msg = _normalize_text(message).lower()
    if not msg:
        return None

    direct = re.search(r"\bbackend\s+(openclaw|ironclaw)\b", msg)
    if direct:
        return direct.group(1)

    switch = re.search(
        r"\b(?:switch|change|set|use|move)\s+(?:backend\s+)?(?:to\s+)?(openclaw|ironclaw)\b",
        msg,
    )
    if switch:
        return switch.group(1)

    mode = re.search(r"\b(openclaw|ironclaw)\s+mode\b", msg)
    if mode:
        return mode.group(1)

    return None


def _configure_backend_runtime(backend: str, announce: bool = True) -> bool:
    """Apply backend runtime env defaults and return no_api_keys mode."""
    backend = (backend or "openclaw").strip().lower()
    if backend not in {"openclaw", "ironclaw"}:
        backend = "openclaw"

    no_api_keys = backend == "ironclaw"
    if no_api_keys:
        os.environ["IRONCLAW_NO_API_KEYS"] = "1"
        os.environ["OPENCLAW_NO_API_KEYS"] = "1"
        if "OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK" not in os.environ:
            os.environ["OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK"] = "1"
            if announce:
                print("[MODE] ironclaw continuity: local fallback auto-enabled.")
        if "OPENCLAW_IRONCLAW_AUTOSTART_WAIT_SEC" not in os.environ:
            os.environ["OPENCLAW_IRONCLAW_AUTOSTART_WAIT_SEC"] = "2.0"
        if "OPENCLAW_IRONCLAW_AUTOSTART_COOLDOWN_SEC" not in os.environ:
            os.environ["OPENCLAW_IRONCLAW_AUTOSTART_COOLDOWN_SEC"] = "45"
    else:
        os.environ["IRONCLAW_NO_API_KEYS"] = "0"
        os.environ["OPENCLAW_NO_API_KEYS"] = "0"

    return no_api_keys


def run_chat_repl(
    conversation_backend: str = "openclaw",
    no_api_keys: bool | None = None,
) -> None:
    """Interactive REPL loop for OpenClaw."""
    repo_root = _ensure_repo_root()
    backend = (conversation_backend or "openclaw").strip().lower()
    if backend not in {"openclaw", "ironclaw"}:
        backend = "openclaw"

    if no_api_keys is None:
        no_api_keys = backend == "ironclaw"

    print("=" * 60)
    if backend == "ironclaw":
        print("  0102 IronClaw Local Chat (via OpenClaw DAE)")
    else:
        print("  0102 OpenClaw Local Chat")
    print("  Commander: @012 | Channel: local_repl")
    print("  Type 'exit' or Ctrl+C to quit")
    print("  Type 'backend ironclaw' or 'backend openclaw' to switch runtime mode")
    print(
        f"  Conversation backend: {backend} | "
        f"no_api_keys={'ON' if no_api_keys else 'OFF'}"
    )
    print("=" * 60)

    try:
        from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE
    except ImportError as exc:
        print(f"[ERROR] Cannot import OpenClawDAE: {exc}")
        print("  Ensure you are running from the repo root (O:/Foundups-Agent)")
        return

    no_api_keys = _configure_backend_runtime(backend, announce=True)

    dae = OpenClawDAE(repo_root=repo_root, conversation_backend=backend)
    print(f"[OK] OpenClawDAE initialized (state={dae.state}, coherence={dae.coherence})")
    print(f"[ID] 0102 taxonomy: {dae.get_identity_label_line(include_runtime_probe=(backend == 'ironclaw'))}")
    print("[ID] tip: ask `model details` for full diagnostics")
    print()

    # Gateway Continuity Layer: Create CLI continuity context for this session
    cli_continuity_ctx = None
    session_key = "local_repl_012"  # Default fallback

    try:
        from modules.communication.moltbot_bridge.src.continuity_context import (
            ContinuityManager,
        )
        cli_continuity_ctx = ContinuityManager.from_cli(
            command="chat_repl",
            script_name="openclaw_chat.py",
        )
        # Derive unique session_key from CLI continuity to avoid child ID collision
        session_key = f"cli_chat_{cli_continuity_ctx.continuity_id[:12]}"
        print(f"[CONTINUITY] CLI context: {cli_continuity_ctx.continuity_id[:12]}...")

        # Record CLI session start breadcrumb for cross-surface tracking
        try:
            from modules.infrastructure.database.src.agent_db import AgentDB
            db = AgentDB()
            db.add_breadcrumb(
                session_id=session_key,
                action="cli_session_start",
                agent_id="0102",
                data={
                    "backend": backend,
                    "command": "chat_repl",
                },
                continuity_id=cli_continuity_ctx.continuity_id,
                runtime_surface=cli_continuity_ctx.surface.value,
                sender_normalized=cli_continuity_ctx.sender_normalized,
            )
        except Exception:
            pass  # Breadcrumb recording is optional
    except Exception as ctx_exc:
        # Graceful degradation - continuity is optional
        pass

    while True:
        try:
            message = input("012> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[EXIT] Session ended.")
            break

        if not message:
            continue
        if message.lower() in ("exit", "quit", "q"):
            print("[EXIT] Session ended.")
            break

        switch_to = _parse_backend_switch_command(message)
        if switch_to:
            if switch_to == backend:
                print(f"[MODE] backend already {backend}.")
                continue
            backend = switch_to
            no_api_keys = _configure_backend_runtime(backend, announce=True)
            dae = OpenClawDAE(repo_root=repo_root, conversation_backend=backend)
            print(
                f"[MODE] backend switched to {backend} | "
                f"no_api_keys={'ON' if no_api_keys else 'OFF'}"
            )
            print(
                f"[ID] 0102 taxonomy: "
                f"{dae.get_identity_label_line(include_runtime_probe=(backend == 'ironclaw'))}"
            )
            continue

        try:
            # Gateway Continuity Layer: Propagate CLI context as parent for OpenClaw processing
            process_metadata: Dict[str, Any] = {"source_surface": "cli"}
            if cli_continuity_ctx is not None:
                process_metadata["parent_continuity_id"] = cli_continuity_ctx.continuity_id

            response = asyncio.run(
                dae.process(
                    message=message,
                    sender="@012",
                    channel="local_repl",
                    session_key=session_key,
                    metadata=process_metadata,
                )
            )
            print(f"\n0102> {response}\n")
        except Exception as exc:
            print(f"\n[ERROR] {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    run_chat_repl()
