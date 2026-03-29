"""
Boot Layer Rotator - Master schema rotation for antifaFM stream

Cycles through visual schemas every 10 minutes:
  GCC Shipping -> Chess -> Karaoke -> Video -> (repeat)

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

# Suppress obsws_python password logging (security)
logging.getLogger("obsws_python.baseclient").setLevel(logging.WARNING)
logging.getLogger("obsws_python.reqs").setLevel(logging.WARNING)

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
        "name": "News Maps",
        "description": "Conflict maps + shipping tracker with ticker",
        "executor": "news_maps",
        "implemented": True,
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
}

# Default rotation order (10 min each schema)
# NOTE: Only include IMPLEMENTED schemas. Coming Soon schemas removed 2026-03-18.
# Schema names must match SCHEMAS registry keys
ROTATION_ORDER = ["gcc", "video", "news"]  # "video" and "news" are aliases


# OBS source names that need visibility control
# Video grid sources to hide during non-video schemas
# These are the ACTUAL source names in OBS (not generic video1,2,3...)
# Configure via env: OBS_VIDEO_SOURCES="France 24,Al Jazeera,Telaviv,BBC Straits,DW News"
_default_video_sources = "France 24,Al Jazeera,Telaviv,BBC Straits,DW News"
VIDEO_SOURCES = [s.strip() for s in os.getenv("OBS_VIDEO_SOURCES", _default_video_sources).split(",") if s.strip()]
BROWSER_SOURCE = os.getenv("OBS_BROWSER_SOURCE", "antifaFM Website")

# News map image source (for screenshot-based news maps)
NEWS_MAP_SOURCE = os.getenv("OBS_NEWS_MAP_SOURCE", "News Map")

# Connection singleton - reuse connection to avoid OBS WebSocket spam
_obs_client = None
_obs_client_lock = None  # Will be initialized on first use


def _get_obs_client():
    """Get OBS WebSocket client (singleton pattern to prevent connection spam)."""
    global _obs_client, _obs_client_lock
    import obsws_python as obs
    import threading

    # Initialize lock on first use (thread-safe lazy init)
    if _obs_client_lock is None:
        _obs_client_lock = threading.Lock()

    with _obs_client_lock:
        # Validate existing connection
        if _obs_client is not None:
            try:
                # Quick ping to verify connection is alive
                _obs_client.get_version()
                return _obs_client
            except Exception:
                # Connection dead, recreate
                logger.debug("[ROTATOR] OBS connection stale, reconnecting...")
                _obs_client = None

        # Create new connection
        host = os.getenv("OBS_WEBSOCKET_HOST", "localhost")
        port = int(os.getenv("OBS_WEBSOCKET_PORT", 4455))
        password = os.getenv("OBS_WEBSOCKET_PASSWORD", "")

        _obs_client = obs.ReqClient(host=host, port=port, password=password)
        logger.info(f"[ROTATOR] OBS WebSocket connected to {host}:{port}")
        return _obs_client


def _close_obs_client():
    """Close OBS WebSocket connection (call on shutdown)."""
    global _obs_client
    if _obs_client is not None:
        try:
            _obs_client.disconnect()
        except Exception:
            pass
        _obs_client = None
        logger.debug("[ROTATOR] OBS WebSocket disconnected")


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


async def set_source_mute(source_name: str, muted: bool, silent_fail: bool = True) -> Dict[str, Any]:
    """
    Set OBS input source mute state.

    Args:
        source_name: Name of the audio source in OBS
        muted: True to mute, False to unmute
        silent_fail: If True, don't log warning on missing source (graceful degradation)
    """
    try:
        client = _get_obs_client()
        client.set_input_mute(name=source_name, muted=muted)
        logger.debug(f"[ROTATOR] Set {source_name} muted={muted}")
        return {"success": True, "source": source_name, "muted": muted}
    except Exception as e:
        if not silent_fail:
            logger.warning(f"[ROTATOR] Mute control failed for {source_name}: {e}")
        return {"success": False, "error": str(e), "silent": silent_fail}


async def set_source_bounds_fullscreen(source_name: str) -> Dict[str, Any]:
    """
    Set OBS source to full screen bounds (1920x1080 at position 0,0).
    """
    try:
        client = _get_obs_client()
        scene_name = client.get_current_program_scene().scene_name

        # Get scene item ID
        items = client.get_scene_item_list(scene_name)
        item_id = None
        for item in items.scene_items:
            if item.get("sourceName") == source_name:
                item_id = item.get("sceneItemId")
                break

        if item_id is None:
            return {"success": False, "error": f"Source '{source_name}' not found"}

        # Set full screen transform
        transform = {
            "positionX": 0.0,
            "positionY": 0.0,
            "boundsWidth": 1920.0,
            "boundsHeight": 1080.0,
            "boundsType": "OBS_BOUNDS_STRETCH",  # Stretch to fill
        }
        client.set_scene_item_transform(scene_name, item_id, transform)
        logger.debug(f"[ROTATOR] Set {source_name} to fullscreen 1920x1080")
        return {"success": True, "source": source_name, "bounds": "1920x1080"}

    except Exception as e:
        logger.warning(f"[ROTATOR] Fullscreen bounds failed for {source_name}: {e}")
        return {"success": False, "error": str(e)}


async def configure_schema_visibility(schema_id: str) -> Dict[str, Any]:
    """
    Configure OBS source visibility AND audio for a schema.

    - GCC/news/chess schemas: Hide video grid, show browser FULLSCREEN, UNMUTE radio, MUTE videos
    - Video schema: Show video grid, hide browser, MUTE radio, UNMUTE videos

    CRITICAL: Audio muting prevents dual-audio playback (radio + video simultaneously)
    """
    results = {"schema": schema_id, "visibility_changes": [], "audio_changes": []}

    # Audio source names
    radio_source = os.getenv("OBS_AUDIO_SOURCE", "antifaFM Radio")

    if schema_id == "video":
        # VIDEO schema: Show video grid, hide browser, MUTE radio, UNMUTE videos
        for src in VIDEO_SOURCES:
            r = await set_source_visibility(src, True)
            results["visibility_changes"].append(r)
            # Unmute video sources so their audio plays
            r = await set_source_mute(src, False)
            results["audio_changes"].append(r)
        r = await set_source_visibility(BROWSER_SOURCE, False)
        results["visibility_changes"].append(r)
        # MUTE radio when videos are playing
        r = await set_source_mute(radio_source, True)
        results["audio_changes"].append(r)
        logger.info(f"[ROTATOR] Video schema: showing video grid, radio MUTED")
    else:
        # Non-video schemas (GCC, news, chess, etc): Hide video grid, show browser FULLSCREEN
        for src in VIDEO_SOURCES:
            r = await set_source_visibility(src, False)
            results["visibility_changes"].append(r)
            # Mute video sources when not visible
            r = await set_source_mute(src, True)
            results["audio_changes"].append(r)
        r = await set_source_visibility(BROWSER_SOURCE, True)
        results["visibility_changes"].append(r)
        # Set browser source to fullscreen bounds
        r = await set_source_bounds_fullscreen(BROWSER_SOURCE)
        results["bounds_change"] = r
        # UNMUTE radio when videos are hidden
        r = await set_source_mute(radio_source, False)
        results["audio_changes"].append(r)
        logger.info(f"[ROTATOR] {schema_id} schema: browser FULLSCREEN, radio UNMUTED")

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
                # use_screenshots=True for 012 behavior (anti-WAF pattern)
                result = await gcc_daemon(standalone=False, use_screenshots=True)
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                emit_event("schema_completed", schema_id=schema_id, duration_sec=duration, success=True)
                return result

            elif schema_id == "video":
                # VIDEO schema: Rotate through video sources (video1-9)
                # Each video shown for ~66 seconds (600s / 9 videos)
                logger.info("[ROTATOR] Video schema: starting video rotation")

                video_interval = SCHEMA_DURATION_SEC // len(VIDEO_SOURCES)  # ~66s per video
                elapsed = 0.0

                for i, video_src in enumerate(VIDEO_SOURCES):
                    # Check if schema time exceeded
                    if elapsed >= SCHEMA_DURATION_SEC:
                        break

                    # Hide all videos first
                    for src in VIDEO_SOURCES:
                        await set_source_visibility(src, False)
                        await set_source_mute(src, True)

                    # Show current video
                    await set_source_visibility(video_src, True)
                    await set_source_mute(video_src, False)

                    # Auto-fix layout if video is too small
                    try:
                        from modules.platform_integration.antifafm_broadcaster.skillz.visual_layout_validator.executor import (
                            validate_and_fix
                        )
                        layout_result = await validate_and_fix(auto_fix=True)
                        if layout_result.get("fixes_applied", 0) > 0:
                            logger.info(f"[ROTATOR] Layout auto-fixed: {layout_result['fixes_applied']} adjustments")
                    except ImportError:
                        pass  # Layout validator not available
                    except Exception as e:
                        logger.debug(f"[ROTATOR] Layout check skipped: {e}")

                    logger.info(f"[ROTATOR] Video {i+1}/{len(VIDEO_SOURCES)}: {video_src}")

                    # Wait for video interval
                    await asyncio.sleep(video_interval)
                    elapsed += video_interval

                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                emit_event("schema_completed", schema_id=schema_id, duration_sec=duration, success=True)
                return {"schema": schema_id, "elapsed_sec": duration, "videos_shown": len(VIDEO_SOURCES)}

            elif schema_id == "news":
                # NEWS schema: Conflict maps + shipping tracker with screenshot rotation
                from modules.platform_integration.antifafm_broadcaster.skillz.news_maps.executor import (
                    capture_screenshot,
                    get_all_ticker_events,
                    NEWS_ROTATION as NEWS_MAP_ROTATION,
                    VIEW_ROTATION_SEC,
                )

                logger.info("[ROTATOR] News schema: conflict/shipping maps rotation")

                # Update OBS image source with news map screenshots
                elapsed = 0.0
                map_index = 0

                while elapsed < SCHEMA_DURATION_SEC:
                    source_id = NEWS_MAP_ROTATION[map_index]

                    # Capture screenshot (uses cache if recent)
                    screenshot = await capture_screenshot(source_id)
                    if screenshot:
                        # Update OBS image source
                        try:
                            client = _get_obs_client()
                            client.set_input_settings(
                                name=NEWS_MAP_SOURCE,
                                settings={"file": str(screenshot.absolute())},
                                overlay=True
                            )
                            logger.info(f"[ROTATOR] News map: {source_id}")
                        except Exception as e:
                            logger.warning(f"[ROTATOR] Failed to update news map source: {e}")

                    # Wait for view rotation interval
                    await asyncio.sleep(VIEW_ROTATION_SEC)
                    elapsed += VIEW_ROTATION_SEC
                    map_index = (map_index + 1) % len(NEWS_MAP_ROTATION)

                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                emit_event("schema_completed", schema_id=schema_id, duration_sec=duration, success=True)
                return {"schema": schema_id, "elapsed_sec": duration, "maps_shown": len(NEWS_MAP_ROTATION)}

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
    logger.info(f"[ROTATOR] Schemas: {' -> '.join(ROTATION_ORDER)}")
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

    # Only register signal handlers if running in main thread
    # (avoids "signal only works in main thread" error when launched from menu)
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    except ValueError as e:
        logger.debug(f"[ROTATOR] Signal handlers not registered (non-main thread): {e}")

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
            status = "[x]" if schema["implemented"] else "[ ]"
            print(f"  {status} {sid}: {schema['name']}")
            print(f"      {schema['description']}")
        print(f"\nRotation order: {' -> '.join(ROTATION_ORDER)}")
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
