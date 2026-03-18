"""
Boot Layer Rotator - Master schema rotation for antifaFM stream

Cycles through visual schemas every 10 minutes:
  GCC Shipping → Chess → Karaoke → Video → (repeat)

Each schema has its own 2-minute internal view rotation.
Stakeholder/Delegate can override to pause or skip schemas.

Usage:
    python executor.py --daemon        # Start full rotation
    python executor.py --skip-to chess # Skip to specific schema
    python executor.py --list          # List available schemas

WSP 27: Universal DAE Architecture
"""

import argparse
import asyncio
import json
import logging
import os
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)

# Telemetry path for event logging
TELEMETRY_DIR = Path(__file__).parent.parent.parent / "telemetry"
TELEMETRY_FILE = TELEMETRY_DIR / "rotator_events.jsonl"


def emit_event(event_type: str, **data: Any) -> None:
    """Emit rotator event to JSONL telemetry log."""
    try:
        TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            **data
        }
        with open(TELEMETRY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        logger.debug(f"[ROTATOR] Event: {event_type} {data}")
    except Exception as e:
        logger.warning(f"[ROTATOR] Failed to emit event: {e}")


# Schema rotation interval (10 minutes per schema)
SCHEMA_DURATION_SEC = 600

# Override signal file
OVERRIDE_SIGNAL_FILE = Path(__file__).parent / "rotator_override.signal"
SKIP_TO_SIGNAL_FILE = Path(__file__).parent / "skip_to_schema.signal"

# Coming Soon fallback for schemas not yet implemented
COMING_SOON_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<style>
body {{
    margin: 0;
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    font-family: 'Segoe UI', Arial, sans-serif;
    color: white;
    text-align: center;
}}
.title {{
    font-size: 4em;
    font-weight: bold;
    text-shadow: 0 0 20px rgba(255,100,100,0.5);
    margin-bottom: 20px;
}}
.subtitle {{
    font-size: 2.5em;
    color: #ff6b6b;
    animation: pulse 2s infinite;
}}
.signature {{
    font-size: 3em;
    margin-top: 40px;
}}
@keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.5; }}
}}
</style>
</head>
<body>
<div class="title">{name}</div>
<div class="subtitle">Coming Soon</div>
<div class="signature">0102🦞</div>
</body>
</html>
"""

import base64


def get_coming_soon_uri(name: str) -> str:
    """Generate Coming Soon data URI for a schema."""
    html = COMING_SOON_TEMPLATE.format(name=name)
    return "data:text/html;base64," + base64.b64encode(html.encode()).decode()


# Schema registry - all antifaFM visual schemas
SCHEMAS: Dict[str, Dict[str, Any]] = {
    "gcc": {
        "name": "GCC Shipping Tracker",
        "description": "Strait of Hormuz vessel tracking",
        "executor": "gcc_shipping_tracker",
        "implemented": True,
    },
    "chess": {
        "name": "Chess Arena",
        "description": "Live chess matches and puzzles",
        "executor": None,
        "implemented": False,
    },
    "checkers": {
        "name": "Checkers",
        "description": "Classic checkers gameplay",
        "executor": None,
        "implemented": False,
    },
    "video": {
        "name": "Video Rotation",
        "description": "Curated video playlist (current default)",
        "executor": "video_layer",
        "implemented": True,  # Existing functionality
    },
    "news": {
        "name": "News Ticker",
        "description": "Live news headlines and updates",
        "executor": "news_ticker",
        "implemented": True,  # Existing functionality
    },
    "cams": {
        "name": "Live Cams",
        "description": "Global webcam feeds",
        "executor": None,
        "implemented": False,
    },
    "karaoke": {
        "name": "Karaoke Mode",
        "description": "Song lyrics and sing-along",
        "executor": None,
        "implemented": False,
    },
    "weather": {
        "name": "Weather Map",
        "description": "Global weather visualization",
        "executor": None,
        "implemented": False,
    },
    "crypto": {
        "name": "Crypto Ticker",
        "description": "BTC/ETH price charts",
        "executor": None,
        "implemented": False,
    },
}

# Default rotation order (10 min each schema)
# NOTE: Only include IMPLEMENTED schemas. Coming Soon schemas removed 2026-03-18.
# Add schema back when executor is wired (see run_schema() imports)
ROTATION_ORDER = ["gcc", "video", "news"]


# OBS source names that need visibility control
# Video grid sources to hide during non-video schemas
VIDEO_SOURCES = ["video1", "video2", "video3", "video4", "video5", "video6", "video7", "video8", "video9"]
BROWSER_SOURCE = os.getenv("OBS_BROWSER_SOURCE", "antifaFM Website")


def _get_obs_client():
    """Get OBS WebSocket client."""
    import obsws_python as obs

    host = os.getenv("OBS_WEBSOCKET_HOST", "localhost")
    port = int(os.getenv("OBS_WEBSOCKET_PORT", 4455))
    password = os.getenv("OBS_WEBSOCKET_PASSWORD", "")

    return obs.ReqClient(host=host, port=port, password=password)


async def set_source_visibility(source_name: str, visible: bool, scene_name: str = None) -> Dict[str, Any]:
    """
    Set OBS scene item visibility.

    Args:
        source_name: Name of the source in OBS
        visible: True to show, False to hide
        scene_name: Scene containing the source (default: current scene)
    """
    try:
        client = _get_obs_client()

        # Get current scene if not specified
        if not scene_name:
            current = client.get_current_program_scene()
            scene_name = current.scene_name

        # Get scene item ID
        items = client.get_scene_item_list(scene_name)
        item_id = None
        for item in items.scene_items:
            if item.get("sourceName") == source_name:
                item_id = item.get("sceneItemId")
                break

        if item_id is None:
            return {"success": False, "error": f"Source '{source_name}' not found in scene"}

        # Set visibility
        client.set_scene_item_enabled(
            scene_name=scene_name,
            item_id=item_id,
            enabled=visible
        )

        logger.debug(f"[ROTATOR] Set {source_name} visibility={visible}")
        return {"success": True, "source": source_name, "visible": visible}

    except Exception as e:
        logger.warning(f"[ROTATOR] Visibility control failed for {source_name}: {e}")
        return {"success": False, "error": str(e)}


async def configure_schema_visibility(schema_id: str) -> Dict[str, Any]:
    """
    Configure OBS source visibility for a schema.

    - GCC/news/chess schemas: Hide video grid, show browser
    - Video schema: Show video grid, hide browser
    """
    results = {"schema": schema_id, "visibility_changes": []}

    if schema_id == "video":
        # VIDEO schema: Show video grid, hide browser
        for src in VIDEO_SOURCES:
            r = await set_source_visibility(src, True)
            results["visibility_changes"].append(r)
        r = await set_source_visibility(BROWSER_SOURCE, False)
        results["visibility_changes"].append(r)
        logger.info(f"[ROTATOR] Video schema: showing video grid, hiding browser")
    else:
        # Non-video schemas (GCC, news, chess, etc): Hide video grid, show browser
        for src in VIDEO_SOURCES:
            r = await set_source_visibility(src, False)
            results["visibility_changes"].append(r)
        r = await set_source_visibility(BROWSER_SOURCE, True)
        results["visibility_changes"].append(r)
        logger.info(f"[ROTATOR] {schema_id} schema: hiding video grid, showing browser")

    return results


async def update_obs_source(url: str) -> Dict[str, Any]:
    """Update OBS browser source."""
    try:
        client = _get_obs_client()
        # Browser source name (env var or default to existing)
        source_name = os.getenv("OBS_BROWSER_SOURCE", "antifaFM Website")
        client.set_input_settings(
            name=source_name,
            settings={"url": url},
            overlay=True
        )
        return {"success": True, "url": url}
    except Exception as e:
        logger.error(f"[ROTATOR] OBS update failed: {e}")
        return {"success": False, "error": str(e)}


async def run_schema(schema_id: str) -> Dict[str, Any]:
    """
    Run a single schema for its duration.

    Returns when schema completes or is overridden.
    """
    schema = SCHEMAS.get(schema_id)
    if not schema:
        logger.error(f"[ROTATOR] Unknown schema: {schema_id}")
        return {"error": f"Unknown schema: {schema_id}"}

    start_time = datetime.now(timezone.utc)
    logger.info(f"[ROTATOR] Starting schema: {schema['name']}")
    emit_event("schema_started", schema_id=schema_id, name=schema["name"])

    # Configure OBS source visibility for this schema
    visibility_result = await configure_schema_visibility(schema_id)
    if visibility_result.get("visibility_changes"):
        logger.info(f"[ROTATOR] Visibility configured for {schema_id}")

    if schema["implemented"] and schema["executor"]:
        # Import and run the schema's executor
        try:
            if schema_id == "gcc":
                from modules.platform_integration.antifafm_broadcaster.skillz.gcc_shipping_tracker.executor import (
                    rotation_daemon as gcc_daemon
                )
                result = await gcc_daemon(standalone=False)
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                emit_event("schema_completed", schema_id=schema_id, duration_sec=duration, success=True)
                return result
            # Add other schema imports here as they're implemented
        except ImportError as e:
            logger.error(f"[ROTATOR] Failed to import {schema_id}: {e}")
            emit_event("fallback_shown", schema_id=schema_id, reason=f"import_error: {e}")
            # Fall through to Coming Soon

    # Not implemented - show Coming Soon
    logger.info(f"[ROTATOR] Schema '{schema_id}' not implemented - showing Coming Soon")
    emit_event("fallback_shown", schema_id=schema_id, reason="not_implemented")
    coming_soon_url = get_coming_soon_uri(schema["name"])
    await update_obs_source(coming_soon_url)

    # Wait for schema duration
    await asyncio.sleep(SCHEMA_DURATION_SEC)

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    emit_event("schema_completed", schema_id=schema_id, duration_sec=duration, success=True, fallback=True)

    return {
        "schema": schema_id,
        "elapsed_sec": SCHEMA_DURATION_SEC,
        "fallback": True
    }


async def ensure_audio_playing() -> Dict[str, Any]:
    """
    Ensure antifaFM audio source is playing.

    Uses antifafm_dj skill for audio health check and restart.
    Audio URL: https://a12.asurahosting.com/listen/antifafm/radio.mp3
    """
    try:
        # Try to use antifafm_dj skill
        from modules.ai_intelligence.ai_overseer.skillz.antifafm_dj import (
            check_audio_health,
            restart_audio_source,
        )

        # Check current health
        health = check_audio_health()
        if health["healthy"]:
            logger.info(f"[ROTATOR] Audio healthy: {health['state']}")
            return {"success": True, "source": health["source"], "action": "verified"}

        # Not healthy - restart
        logger.info(f"[ROTATOR] Audio issues: {health['issues']} - restarting...")
        result = restart_audio_source()
        return result

    except ImportError:
        # Fallback: direct OBS control
        logger.debug("[ROTATOR] antifafm_dj skill not available, using direct OBS")
        audio_source = os.getenv("OBS_AUDIO_SOURCE", "antifaFM Radio")
        try:
            client = _get_obs_client()
            client.trigger_media_input_action(
                name=audio_source,
                action="OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART"
            )
            client.set_input_mute(name=audio_source, muted=False)
            logger.info(f"[ROTATOR] Audio source '{audio_source}' restarted")
            return {"success": True, "source": audio_source}
        except Exception as e:
            logger.warning(f"[ROTATOR] Audio restart failed: {e}")
            return {"success": False, "error": str(e)}


def check_override() -> bool:
    """Check if rotation should pause."""
    return OVERRIDE_SIGNAL_FILE.exists()


def check_skip_to() -> Optional[str]:
    """Check if should skip to a specific schema."""
    if SKIP_TO_SIGNAL_FILE.exists():
        try:
            schema_id = SKIP_TO_SIGNAL_FILE.read_text().strip()
            SKIP_TO_SIGNAL_FILE.unlink()
            if schema_id in SCHEMAS:
                return schema_id
        except Exception:
            pass
    return None


async def rotation_daemon():
    """
    Master rotation daemon - cycles through all schemas.

    Each schema runs for ~10 minutes, then switches to next.
    Stakeholder can override to pause or skip.
    """
    logger.info("[ROTATOR] Starting boot layer rotation daemon")
    logger.info(f"[ROTATOR] Schemas: {' → '.join(ROTATION_ORDER)}")
    logger.info(f"[ROTATOR] Schema duration: {SCHEMA_DURATION_SEC}s each")
    emit_event("rotation_started", schemas=ROTATION_ORDER, duration_sec=SCHEMA_DURATION_SEC)

    # Ensure audio is playing at startup
    audio_result = await ensure_audio_playing()
    if audio_result.get("success"):
        logger.info("[ROTATOR] Audio source verified and restarted")
    else:
        logger.warning(f"[ROTATOR] Audio check failed: {audio_result.get('error')}")

    schema_index = 0
    running = True
    was_paused = False

    def signal_handler(sig, frame):
        nonlocal running
        logger.info("[ROTATOR] Shutdown signal received")
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while running:
        # Check for override
        if check_override():
            if not was_paused:
                logger.info("[ROTATOR] Override active - pausing rotation")
                emit_event("rotation_paused", reason="stakeholder_override")
                was_paused = True
            await asyncio.sleep(60)
            continue
        elif was_paused:
            logger.info("[ROTATOR] Override cleared - resuming rotation")
            emit_event("rotation_resumed")
            was_paused = False

        # Check for skip-to
        skip_to = check_skip_to()
        if skip_to:
            logger.info(f"[ROTATOR] Skipping to schema: {skip_to}")
            emit_event("rotation_skip", target_schema=skip_to)
            schema_index = ROTATION_ORDER.index(skip_to)

        # Get current schema
        schema_id = ROTATION_ORDER[schema_index]

        # Run schema
        result = await run_schema(schema_id)
        logger.info(f"[ROTATOR] Schema '{schema_id}' completed: {result}")

        # Check if override was set during schema
        if result.get("override"):
            logger.info("[ROTATOR] Schema reported override - pausing")
            continue

        # Move to next schema
        schema_index = (schema_index + 1) % len(ROTATION_ORDER)

    emit_event("rotation_stopped")
    logger.info("[ROTATOR] Rotation daemon stopped")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Boot Layer Rotator - Master schema rotation for antifaFM"
    )
    parser.add_argument("--daemon", action="store_true", help="Start rotation daemon")
    parser.add_argument("--list", action="store_true", help="List available schemas")
    parser.add_argument("--skip-to", type=str, help="Skip to specific schema")
    parser.add_argument("--override", action="store_true", help="Pause rotation")
    parser.add_argument("--clear", action="store_true", help="Clear override")

    args = parser.parse_args()

    if args.list:
        print("\n=== Available Schemas ===")
        for sid, schema in SCHEMAS.items():
            status = "✓" if schema["implemented"] else "○"
            print(f"  {status} {sid}: {schema['name']}")
            print(f"      {schema['description']}")
        print(f"\nRotation order: {' → '.join(ROTATION_ORDER)}")
        print(f"Schema duration: {SCHEMA_DURATION_SEC}s each")
        return

    if args.override:
        OVERRIDE_SIGNAL_FILE.touch()
        print("[ROTATOR] Override set - rotation paused")
        return

    if args.clear:
        if OVERRIDE_SIGNAL_FILE.exists():
            OVERRIDE_SIGNAL_FILE.unlink()
        print("[ROTATOR] Override cleared")
        return

    if args.skip_to:
        if args.skip_to not in SCHEMAS:
            print(f"[ERROR] Unknown schema: {args.skip_to}")
            print(f"Available: {', '.join(SCHEMAS.keys())}")
            return
        SKIP_TO_SIGNAL_FILE.write_text(args.skip_to)
        print(f"[ROTATOR] Will skip to: {args.skip_to}")
        return

    if args.daemon:
        print("[ROTATOR] Starting boot layer rotation...")
        print("[ROTATOR] Press Ctrl+C to stop")
        asyncio.run(rotation_daemon())
        return

    # Default: show status
    parser.print_help()


if __name__ == "__main__":
    main()
