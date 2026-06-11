"""
CLI Utilities - Common helper functions for FoundUps Agent CLI.

Extracted from main.py per WSP 62 (file size enforcement).
Contains: environment helpers, Holo controls menus, channel selection.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from modules.infrastructure.shared_utilities.local_model_selection import (
    get_local_model_root,
    resolve_code_model_path,
    resolve_model_selection,
)
from modules.infrastructure.shared_utilities.youtube_channel_registry import get_channels


def env_truthy(name: str, default: str = "false") -> bool:
    """Check if environment variable is truthy."""
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")


def env_flag(name: str, default_on: bool = True) -> bool:
    """Get boolean flag from environment with default."""
    default = "true" if default_on else "false"
    return env_truthy(name, default)


def maybe_clear_screen() -> None:
    """Clear screen if FOUNDUPS_CLEAR_SCREEN is enabled."""
    if not env_flag("FOUNDUPS_CLEAR_SCREEN", False):
        return
    try:
        if not sys.stdout.isatty():
            return
    except Exception:
        return
    os.system("cls" if os.name == "nt" else "clear")


def parse_index_timestamp(value: str) -> Optional[datetime]:
    """Parse ISO timestamp from index state."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def should_auto_index_holo(state_path: Path, max_age_hours: int) -> bool:
    """Determine if HoloIndex auto-indexing should run."""
    if max_age_hours <= 0:
        return True
    if not state_path.exists():
        return True
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        last_value = str(payload.get("last_indexed_at", ""))
        last_ts = parse_index_timestamp(last_value)
        if not last_ts:
            return True
        now = datetime.now(timezone.utc)
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)
        age_hours = (now - last_ts).total_seconds() / 3600.0
        return age_hours >= max_age_hours
    except Exception:
        return True


def maybe_auto_index_holo(verbose: bool, logger) -> None:
    """Run HoloIndex auto-indexing if enabled and stale."""
    if not env_flag("FOUNDUPS_HOLO_AUTO_INDEX", False):
        return
    try:
        max_age_hours = int(os.getenv("FOUNDUPS_HOLO_AUTO_INDEX_MAX_HOURS", "6").strip())
    except ValueError:
        max_age_hours = 6
    ssd_path = os.getenv("HOLO_SSD_PATH", "E:/HoloIndex")
    state_path = Path(ssd_path) / "indexes" / "index_state.json"
    if not should_auto_index_holo(state_path, max_age_hours):
        return
    try:
        import subprocess

        env = os.environ.copy()
        if not verbose:
            env.setdefault("HOLO_SILENT", "1")
        cmd = [sys.executable, "holo_index.py", "--index-all", "--ssd", ssd_path]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
        if result.returncode != 0:
            logger.warning(f"[HOLO] Auto-index failed: {result.stderr.strip() or result.stdout.strip()}")
        elif verbose:
            logger.info("[HOLO] Auto-index complete")
    except Exception as e:
        logger.warning(f"[HOLO] Auto-index failed: {e}")


def format_env_value(value: str) -> str:
    """Format environment value for .env file (quote if spaces)."""
    if any(ch.isspace() for ch in value):
        return f'"{value}"'
    return value


def mask_secret(value: str) -> str:
    """Mask secret value for display."""
    if not value:
        return "unset"
    tail = value[-4:] if len(value) > 4 else value
    return f"set (len={len(value)} tail=...{tail})"


def update_env_file(key: str, value: str) -> None:
    """Update a key in the .env file."""
    env_path = Path(__file__).resolve().parents[4] / ".env"  # Go up to repo root
    new_line = f"{key}={format_env_value(value)}"

    if not env_path.exists():
        env_path.write_text(new_line + "\n", encoding="utf-8")
        return

    lines = env_path.read_text(encoding="utf-8").splitlines()
    updated = False
    next_lines: list[str] = []

    for line in lines:
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            next_lines.append(line)
            continue
        key_part = stripped.split("=", 1)[0].strip()
        if key_part.startswith("export "):
            key_part = key_part[len("export "):].strip()
        if key_part == key:
            if not updated:
                next_lines.append(new_line)
                updated = True
            continue
        next_lines.append(line)

    if not updated:
        next_lines.append(new_line)

    env_path.write_text("\n".join(next_lines) + "\n", encoding="utf-8")


def set_env_bool(key: str, enabled: bool) -> None:
    """Set boolean environment variable and update .env file."""
    value = "true" if enabled else "false"
    os.environ[key] = value
    update_env_file(key, value)


def select_channel() -> str:
    """Display numbered channel selection menu and return channel name."""
    print("\nSelect channel:")
    channels = get_channels()
    if not channels:
        print("[WARN] No channels found in registry; defaulting to undaodu")
        return "undaodu"
    for idx, ch in enumerate(channels, start=1):
        print(f"  {idx}. {ch.get('name', ch.get('key'))}")
    choice = input("Channel [1]: ").strip() or "1"
    try:
        selected = channels[int(choice) - 1]
        return str(selected.get("key", "undaodu")).lower()
    except Exception:
        return str(channels[0].get("key", "undaodu")).lower()


def holo_controls_menu() -> None:
    """Display and handle Holo Controls submenu."""
    while True:
        auto_index_on = env_flag("FOUNDUPS_HOLO_AUTO_INDEX", False)
        max_hours_raw = os.getenv("FOUNDUPS_HOLO_AUTO_INDEX_MAX_HOURS", "6").strip() or "6"
        ssd_path = os.getenv("HOLO_SSD_PATH", "E:/HoloIndex")
        cache_path = os.getenv("HOLO_CACHE_PATH", "E:/HoloIndex/cache")
        reward_variant = os.getenv("HOLO_REWARD_VARIANT", "A").strip() or "A"
        reward_variant = reward_variant.upper()
        clear_screen_on = env_flag("FOUNDUPS_CLEAR_SCREEN", False)
        holo_silent_on = env_truthy("HOLO_SILENT", "false")
        holo_skip_model_on = env_truthy("HOLO_SKIP_MODEL", "false")
        holo_verbose_on = env_truthy("HOLO_VERBOSE", "false")
        holo_offline_on = env_truthy("HOLO_OFFLINE", "false")
        holo_disable_pip_on = env_truthy("HOLO_DISABLE_PIP_INSTALL", "false")
        holo_breadcrumbs_on = env_truthy("HOLO_BREADCRUMB_ENABLED", "true")
        holo_breadcrumb_logs_on = env_truthy("HOLO_BREADCRUMB_LOGS", "true")
        overseer_breadcrumbs_on = env_truthy("AI_OVERSEER_BREADCRUMBS", "true")

        print("\n[MENU] Holo Controls (012)")
        print("=" * 60)
        print(f"Auto-index: {'ON' if auto_index_on else 'OFF'} | Max age hours: {max_hours_raw} (0=always)")
        print(f"SSD path: {ssd_path}")
        print(f"Cache path: {cache_path}")
        print(f"Reward variant: {reward_variant}")
        print(f"Clear screen on startup: {'ON' if clear_screen_on else 'OFF'}")
        print(
            "Holo: "
            f"silent={'ON' if holo_silent_on else 'OFF'} | "
            f"verbose={'ON' if holo_verbose_on else 'OFF'} | "
            f"skip_model={'ON' if holo_skip_model_on else 'OFF'} | "
            f"offline={'ON' if holo_offline_on else 'OFF'}"
        )
        print(
            "Breadcrumbs: "
            f"holo={'ON' if holo_breadcrumbs_on else 'OFF'} | "
            f"logs={'ON' if holo_breadcrumb_logs_on else 'OFF'} | "
            f"overseer={'ON' if overseer_breadcrumbs_on else 'OFF'}"
        )
        print("-" * 60)
        print("1) Toggle auto-index")
        print("2) Set max age hours (0=always)")
        print("3) Set SSD path")
        print("4) Set cache path (HOLO_CACHE_PATH)")
        print("5) Set reward variant (HOLO_REWARD_VARIANT)")
        print("6) Toggle clear screen")
        print("7) Toggle Holo verbose output (HOLO_VERBOSE)")
        print("8) Toggle Holo silent output (HOLO_SILENT)")
        print("9) Toggle skip model load (HOLO_SKIP_MODEL)")
        print("10) Toggle offline mode (HOLO_OFFLINE)")
        print("11) Toggle disable pip auto-install (HOLO_DISABLE_PIP_INSTALL)")
        print("12) Toggle Holo breadcrumbs (HOLO_BREADCRUMB_ENABLED)")
        print("13) Toggle breadcrumb logs (HOLO_BREADCRUMB_LOGS)")
        print("14) Toggle AI Overseer breadcrumbs")
        print("15) Advanced Holo controls")
        print("16) Back")

        choice = input("holo-controls> ").strip()

        if choice == "1":
            new_value = "0" if auto_index_on else "1"
            os.environ["FOUNDUPS_HOLO_AUTO_INDEX"] = new_value
            update_env_file("FOUNDUPS_HOLO_AUTO_INDEX", new_value)
        elif choice == "2":
            raw = input("Enter max age hours (0=always): ").strip()
            if not raw:
                continue
            try:
                hours = int(raw)
                if hours < 0:
                    raise ValueError
            except ValueError:
                print("[ERROR] Enter a non-negative integer.")
                continue
            os.environ["FOUNDUPS_HOLO_AUTO_INDEX_MAX_HOURS"] = str(hours)
            update_env_file("FOUNDUPS_HOLO_AUTO_INDEX_MAX_HOURS", str(hours))
        elif choice == "3":
            raw = input("Enter SSD path (blank=cancel): ").strip()
            if not raw:
                continue
            os.environ["HOLO_SSD_PATH"] = raw
            update_env_file("HOLO_SSD_PATH", raw)
        elif choice == "4":
            raw = input("Enter cache path (blank=cancel): ").strip()
            if not raw:
                continue
            os.environ["HOLO_CACHE_PATH"] = raw
            update_env_file("HOLO_CACHE_PATH", raw)
        elif choice == "5":
            raw = input("Enter reward variant (A/B): ").strip().upper()
            if not raw:
                continue
            if raw not in {"A", "B"}:
                print("[ERROR] Reward variant must be A or B.")
                continue
            os.environ["HOLO_REWARD_VARIANT"] = raw
            update_env_file("HOLO_REWARD_VARIANT", raw)
        elif choice == "6":
            new_value = "0" if clear_screen_on else "1"
            os.environ["FOUNDUPS_CLEAR_SCREEN"] = new_value
            update_env_file("FOUNDUPS_CLEAR_SCREEN", new_value)
        elif choice == "7":
            new_value = "false" if holo_verbose_on else "true"
            os.environ["HOLO_VERBOSE"] = new_value
            update_env_file("HOLO_VERBOSE", new_value)
        elif choice == "8":
            new_value = "false" if holo_silent_on else "true"
            os.environ["HOLO_SILENT"] = new_value
            update_env_file("HOLO_SILENT", new_value)
        elif choice == "9":
            new_value = "false" if holo_skip_model_on else "true"
            os.environ["HOLO_SKIP_MODEL"] = new_value
            update_env_file("HOLO_SKIP_MODEL", new_value)
        elif choice == "10":
            new_value = "false" if holo_offline_on else "true"
            os.environ["HOLO_OFFLINE"] = new_value
            update_env_file("HOLO_OFFLINE", new_value)
        elif choice == "11":
            new_value = "false" if holo_disable_pip_on else "true"
            os.environ["HOLO_DISABLE_PIP_INSTALL"] = new_value
            update_env_file("HOLO_DISABLE_PIP_INSTALL", new_value)
        elif choice == "12":
            new_value = "false" if holo_breadcrumbs_on else "true"
            os.environ["HOLO_BREADCRUMB_ENABLED"] = new_value
            update_env_file("HOLO_BREADCRUMB_ENABLED", new_value)
        elif choice == "13":
            new_value = "false" if holo_breadcrumb_logs_on else "true"
            os.environ["HOLO_BREADCRUMB_LOGS"] = new_value
            update_env_file("HOLO_BREADCRUMB_LOGS", new_value)
        elif choice == "14":
            new_value = "false" if overseer_breadcrumbs_on else "true"
            os.environ["AI_OVERSEER_BREADCRUMBS"] = new_value
            update_env_file("AI_OVERSEER_BREADCRUMBS", new_value)
        elif choice == "15":
            holo_advanced_controls_menu()
        elif choice == "16":
            break
        else:
            print("[ERROR] Invalid choice.")


def holo_advanced_controls_menu() -> None:
    """Display and handle Advanced Holo Controls submenu."""
    while True:
        qwen_model = os.getenv("HOLO_QWEN_MODEL", str(resolve_code_model_path()))
        triage_selection = resolve_model_selection("triage")
        general_selection = resolve_model_selection("general")
        code_selection = resolve_model_selection("code")
        qwen_tokens = os.getenv("HOLO_QWEN_MAX_TOKENS", "512").strip() or "512"
        qwen_temp = os.getenv("HOLO_QWEN_TEMPERATURE", "0.2").strip() or "0.2"
        qwen_cache_on = env_truthy("HOLO_QWEN_CACHE", "true")
        qwen_telemetry = os.getenv("HOLO_QWEN_TELEMETRY", "E:/HoloIndex/indexes/holo_usage.json")
        base_url = os.getenv("HOLO_LLM_BASE_URL", "").strip()
        api_key_masked = mask_secret(os.getenv("HOLO_LLM_API_KEY", "").strip())
        agent_id = os.getenv("HOLO_AGENT_ID", "").strip() or "unset"
        holo_id = (os.getenv("HOLO_ID_0102") or os.getenv("0102_HOLO_ID") or "").strip() or "unset"
        mcp_enabled_on = env_truthy("HOLO_MCP_ENABLED", "true")
        mcp_warn_on = env_truthy("HOLO_MCP_WARNINGS", "true")
        pattern_logs_on = env_truthy("HOLO_PATTERN_MEMORY_LOGS", "true")
        monitor_interval = os.getenv("HOLO_MONITOR_INTERVAL", "5.0").strip() or "5.0"
        monitor_heartbeat = os.getenv("HOLO_MONITOR_HEARTBEAT", "60.0").strip() or "60.0"

        print("\n[MENU] Advanced Holo Controls (012)")
        print("=" * 60)
        print(f"Qwen model: {qwen_model}")
        print(f"Qwen max tokens: {qwen_tokens} | temp: {qwen_temp} | cache: {'ON' if qwen_cache_on else 'OFF'}")
        print(f"Qwen telemetry: {qwen_telemetry}")
        print(f"Overseer URL: {base_url or 'unset'} | API key: {api_key_masked}")
        print(f"Agent IDs: HOLO_AGENT_ID={agent_id} | 0102_HOLO_ID={holo_id}")
        print(f"MCP: enabled={'ON' if mcp_enabled_on else 'OFF'} | warnings={'ON' if mcp_warn_on else 'OFF'}")
        print(f"Monitor: interval={monitor_interval}s | heartbeat={monitor_heartbeat}s")
        print(f"Pattern memory logs: {'ON' if pattern_logs_on else 'OFF'}")
        print(
            "Local model routing: "
            f"triage={'OK' if triage_selection.exists else 'MISSING'} | "
            f"general={'OK' if general_selection.exists else 'MISSING'} | "
            f"code={'OK' if code_selection.exists else 'MISSING'}"
        )
        print("-" * 60)
        print("1) Set code model path/dir (HOLO_QWEN_MODEL legacy alias)")
        print("2) Set Qwen max tokens (HOLO_QWEN_MAX_TOKENS)")
        print("3) Set Qwen temperature (HOLO_QWEN_TEMPERATURE)")
        print("4) Toggle Qwen cache (HOLO_QWEN_CACHE)")
        print("5) Set Qwen telemetry path (HOLO_QWEN_TELEMETRY)")
        print("6) Set Overseer base URL (HOLO_LLM_BASE_URL)")
        print("7) Set Overseer API key (HOLO_LLM_API_KEY)")
        print("8) Clear Overseer API key")
        print("9) Set HOLO_AGENT_ID")
        print("10) Set 0102_HOLO_ID")
        print("11) Toggle MCP enabled (HOLO_MCP_ENABLED)")
        print("12) Toggle MCP warnings (HOLO_MCP_WARNINGS)")
        print("13) Set monitor interval seconds (HOLO_MONITOR_INTERVAL)")
        print("14) Set monitor heartbeat seconds (HOLO_MONITOR_HEARTBEAT)")
        print("15) Toggle pattern memory logs (HOLO_PATTERN_MEMORY_LOGS)")
        print("16) Local model routing editor (LOCAL_MODEL_*)")
        print("17) Back")

        choice = input("holo-advanced> ").strip()

        if choice == "1":
            raw = input("Enter code model file or directory path (blank=cancel): ").strip()
            if not raw:
                continue
            os.environ["HOLO_QWEN_MODEL"] = raw
            update_env_file("HOLO_QWEN_MODEL", raw)
            os.environ["LOCAL_MODEL_CODE_PATH"] = raw
            update_env_file("LOCAL_MODEL_CODE_PATH", raw)
        elif choice == "2":
            raw = input("Enter max tokens (positive int): ").strip()
            if not raw:
                continue
            try:
                value = int(raw)
                if value <= 0:
                    raise ValueError
            except ValueError:
                print("[ERROR] Enter a positive integer.")
                continue
            os.environ["HOLO_QWEN_MAX_TOKENS"] = str(value)
            update_env_file("HOLO_QWEN_MAX_TOKENS", str(value))
        elif choice == "3":
            raw = input("Enter temperature (0.0-2.0): ").strip()
            if not raw:
                continue
            try:
                value = float(raw)
                if value < 0 or value > 2:
                    raise ValueError
            except ValueError:
                print("[ERROR] Enter a number between 0 and 2.")
                continue
            os.environ["HOLO_QWEN_TEMPERATURE"] = str(value)
            update_env_file("HOLO_QWEN_TEMPERATURE", str(value))
        elif choice == "4":
            new_value = "0" if qwen_cache_on else "1"
            os.environ["HOLO_QWEN_CACHE"] = new_value
            update_env_file("HOLO_QWEN_CACHE", new_value)
        elif choice == "5":
            raw = input("Enter telemetry path (blank=cancel): ").strip()
            if not raw:
                continue
            os.environ["HOLO_QWEN_TELEMETRY"] = raw
            update_env_file("HOLO_QWEN_TELEMETRY", raw)
        elif choice == "6":
            raw = input("Enter base URL (blank=cancel): ").strip()
            if not raw:
                continue
            os.environ["HOLO_LLM_BASE_URL"] = raw
            update_env_file("HOLO_LLM_BASE_URL", raw)
        elif choice == "7":
            raw = input("Enter API key (blank=cancel): ").strip()
            if not raw:
                continue
            os.environ["HOLO_LLM_API_KEY"] = raw
            update_env_file("HOLO_LLM_API_KEY", raw)
        elif choice == "8":
            os.environ["HOLO_LLM_API_KEY"] = ""
            update_env_file("HOLO_LLM_API_KEY", "")
        elif choice == "9":
            raw = input("Enter HOLO_AGENT_ID (blank=clear): ").strip()
            os.environ["HOLO_AGENT_ID"] = raw
            update_env_file("HOLO_AGENT_ID", raw)
        elif choice == "10":
            raw = input("Enter 0102_HOLO_ID (blank=clear): ").strip()
            os.environ["0102_HOLO_ID"] = raw
            update_env_file("0102_HOLO_ID", raw)
        elif choice == "11":
            new_value = "false" if mcp_enabled_on else "true"
            os.environ["HOLO_MCP_ENABLED"] = new_value
            update_env_file("HOLO_MCP_ENABLED", new_value)
        elif choice == "12":
            new_value = "false" if mcp_warn_on else "true"
            os.environ["HOLO_MCP_WARNINGS"] = new_value
            update_env_file("HOLO_MCP_WARNINGS", new_value)
        elif choice == "13":
            raw = input("Enter monitor interval seconds (positive number): ").strip()
            if not raw:
                continue
            try:
                value = float(raw)
                if value <= 0:
                    raise ValueError
            except ValueError:
                print("[ERROR] Enter a positive number.")
                continue
            os.environ["HOLO_MONITOR_INTERVAL"] = str(value)
            update_env_file("HOLO_MONITOR_INTERVAL", str(value))
        elif choice == "14":
            raw = input("Enter heartbeat seconds (positive number): ").strip()
            if not raw:
                continue
            try:
                value = float(raw)
                if value <= 0:
                    raise ValueError
            except ValueError:
                print("[ERROR] Enter a positive number.")
                continue
            os.environ["HOLO_MONITOR_HEARTBEAT"] = str(value)
            update_env_file("HOLO_MONITOR_HEARTBEAT", str(value))
        elif choice == "15":
            new_value = "false" if pattern_logs_on else "true"
            os.environ["HOLO_PATTERN_MEMORY_LOGS"] = new_value
            update_env_file("HOLO_PATTERN_MEMORY_LOGS", new_value)
        elif choice == "16":
            local_model_routing_menu()
        elif choice == "17":
            break
        else:
            print("[ERROR] Invalid choice.")


def local_model_routing_menu() -> None:
    """Display and handle centralized local model routing controls."""
    while True:
        triage = resolve_model_selection("triage")
        general = resolve_model_selection("general")
        code = resolve_model_selection("code")

        local_root = os.getenv("LOCAL_MODEL_ROOT", "").strip()
        triage_dir = os.getenv("LOCAL_MODEL_TRIAGE_DIR", "").strip()
        general_dir = os.getenv("LOCAL_MODEL_GENERAL_DIR", "").strip()
        code_dir = os.getenv("LOCAL_MODEL_CODE_DIR", "").strip()
        triage_path = os.getenv("LOCAL_MODEL_TRIAGE_PATH", "").strip()
        general_path = os.getenv("LOCAL_MODEL_GENERAL_PATH", "").strip()
        code_path = os.getenv("LOCAL_MODEL_CODE_PATH", "").strip()
        holo_qwen_alias = os.getenv("HOLO_QWEN_MODEL", "").strip()

        print("\n[MENU] Local Model Routing (012)")
        print("=" * 60)
        print(f"LOCAL_MODEL_ROOT: {local_root or f'(default: {get_local_model_root()})'}")
        print(
            "Resolved triage: "
            f"{triage.path} ({'OK' if triage.exists else 'MISSING'}, source={triage.source})"
        )
        print(
            "Resolved general: "
            f"{general.path} ({'OK' if general.exists else 'MISSING'}, source={general.source})"
        )
        print(
            "Resolved code: "
            f"{code.path} ({'OK' if code.exists else 'MISSING'}, source={code.source})"
        )
        print("-" * 60)
        print(f"LOCAL_MODEL_TRIAGE_DIR={triage_dir or 'unset'}")
        print(f"LOCAL_MODEL_GENERAL_DIR={general_dir or 'unset'}")
        print(f"LOCAL_MODEL_CODE_DIR={code_dir or 'unset'}")
        print(f"LOCAL_MODEL_TRIAGE_PATH={triage_path or 'unset'}")
        print(f"LOCAL_MODEL_GENERAL_PATH={general_path or 'unset'}")
        print(f"LOCAL_MODEL_CODE_PATH={code_path or 'unset'}")
        print(f"HOLO_QWEN_MODEL (alias)={holo_qwen_alias or 'unset'}")
        print("-" * 60)
        print("1) Set LOCAL_MODEL_ROOT")
        print("2) Set LOCAL_MODEL_TRIAGE_DIR")
        print("3) Set LOCAL_MODEL_GENERAL_DIR")
        print("4) Set LOCAL_MODEL_CODE_DIR")
        print("5) Set LOCAL_MODEL_TRIAGE_PATH")
        print("6) Set LOCAL_MODEL_GENERAL_PATH")
        print("7) Set LOCAL_MODEL_CODE_PATH")
        print("8) Clear TRIAGE overrides (DIR+PATH)")
        print("9) Clear GENERAL overrides (DIR+PATH)")
        print("10) Clear CODE overrides (DIR+PATH)")
        print("11) Sync HOLO_QWEN_MODEL from resolved code model")
        print("12) Back")

        choice = input("local-models> ").strip()

        if choice == "1":
            raw = input("Enter LOCAL_MODEL_ROOT (blank=clear): ").strip()
            os.environ["LOCAL_MODEL_ROOT"] = raw
            update_env_file("LOCAL_MODEL_ROOT", raw)
        elif choice == "2":
            raw = input("Enter LOCAL_MODEL_TRIAGE_DIR (blank=clear): ").strip()
            os.environ["LOCAL_MODEL_TRIAGE_DIR"] = raw
            update_env_file("LOCAL_MODEL_TRIAGE_DIR", raw)
        elif choice == "3":
            raw = input("Enter LOCAL_MODEL_GENERAL_DIR (blank=clear): ").strip()
            os.environ["LOCAL_MODEL_GENERAL_DIR"] = raw
            update_env_file("LOCAL_MODEL_GENERAL_DIR", raw)
        elif choice == "4":
            raw = input("Enter LOCAL_MODEL_CODE_DIR (blank=clear): ").strip()
            os.environ["LOCAL_MODEL_CODE_DIR"] = raw
            update_env_file("LOCAL_MODEL_CODE_DIR", raw)
        elif choice == "5":
            raw = input("Enter LOCAL_MODEL_TRIAGE_PATH (blank=clear): ").strip()
            os.environ["LOCAL_MODEL_TRIAGE_PATH"] = raw
            update_env_file("LOCAL_MODEL_TRIAGE_PATH", raw)
        elif choice == "6":
            raw = input("Enter LOCAL_MODEL_GENERAL_PATH (blank=clear): ").strip()
            os.environ["LOCAL_MODEL_GENERAL_PATH"] = raw
            update_env_file("LOCAL_MODEL_GENERAL_PATH", raw)
        elif choice == "7":
            raw = input("Enter LOCAL_MODEL_CODE_PATH (blank=clear): ").strip()
            os.environ["LOCAL_MODEL_CODE_PATH"] = raw
            update_env_file("LOCAL_MODEL_CODE_PATH", raw)
        elif choice == "8":
            os.environ["LOCAL_MODEL_TRIAGE_DIR"] = ""
            os.environ["LOCAL_MODEL_TRIAGE_PATH"] = ""
            update_env_file("LOCAL_MODEL_TRIAGE_DIR", "")
            update_env_file("LOCAL_MODEL_TRIAGE_PATH", "")
        elif choice == "9":
            os.environ["LOCAL_MODEL_GENERAL_DIR"] = ""
            os.environ["LOCAL_MODEL_GENERAL_PATH"] = ""
            update_env_file("LOCAL_MODEL_GENERAL_DIR", "")
            update_env_file("LOCAL_MODEL_GENERAL_PATH", "")
        elif choice == "10":
            os.environ["LOCAL_MODEL_CODE_DIR"] = ""
            os.environ["LOCAL_MODEL_CODE_PATH"] = ""
            update_env_file("LOCAL_MODEL_CODE_DIR", "")
            update_env_file("LOCAL_MODEL_CODE_PATH", "")
        elif choice == "11":
            alias_value = os.getenv("LOCAL_MODEL_CODE_PATH", "").strip() or str(code.path)
            os.environ["HOLO_QWEN_MODEL"] = alias_value
            update_env_file("HOLO_QWEN_MODEL", alias_value)
        elif choice == "12":
            break
        else:
            print("[ERROR] Invalid choice.")
