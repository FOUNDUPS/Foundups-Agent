"""
antifaFM DJ - Autonomous audio health monitoring for antifaFM stream.

Monitors OBS audio source health and auto-restarts if needed.

Audio Stream: https://a12.asurahosting.com/listen/antifafm/radio.mp3
OBS Source: antifaFM Radio (Media Source)

Usage:
    python executor.py --check     # Check audio health
    python executor.py --restart   # Restart audio source
    python executor.py --daemon    # Run health daemon
    python executor.py --status    # Show current status

WSP 27: Universal DAE Architecture
WSP 91: Observability
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Audio configuration
STREAM_URL = "https://a12.asurahosting.com/listen/antifafm/radio.mp3"
OBS_AUDIO_SOURCE = os.getenv("OBS_AUDIO_SOURCE", "antifaFM Radio")

# Health check interval (seconds)
HEALTH_CHECK_INTERVAL = int(os.getenv("ANTIFAFM_DJ_INTERVAL", "30"))

# Telemetry
TELEMETRY_DIR = Path(__file__).parent.parent.parent.parent.parent / "platform_integration" / "antifafm_broadcaster" / "telemetry"
TELEMETRY_FILE = TELEMETRY_DIR / "dj_events.jsonl"


def emit_event(event_type: str, **data: Any) -> None:
    """Emit DJ event to JSONL telemetry log."""
    try:
        TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            **data
        }
        with open(TELEMETRY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        logger.debug(f"[DJ] Event: {event_type} {data}")
    except Exception as e:
        logger.warning(f"[DJ] Failed to emit event: {e}")


def _get_obs_client():
    """Get OBS WebSocket client."""
    import obsws_python as obs

    host = os.getenv("OBS_WEBSOCKET_HOST", "localhost")
    port = int(os.getenv("OBS_WEBSOCKET_PORT", 4455))
    password = os.getenv("OBS_WEBSOCKET_PASSWORD", "")

    return obs.ReqClient(host=host, port=port, password=password)


def check_audio_health() -> Dict[str, Any]:
    """
    Check antifaFM Radio audio source health.

    Returns:
        Dict with health status, state, volume, and any issues.
    """
    result = {
        "source": OBS_AUDIO_SOURCE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "healthy": False,
        "state": None,
        "volume_db": None,
        "muted": None,
        "issues": [],
    }

    try:
        client = _get_obs_client()

        # Check media state
        try:
            state = client.get_media_input_status(name=OBS_AUDIO_SOURCE)
            result["state"] = state.media_state
            result["cursor_ms"] = state.media_cursor

            if state.media_state != "OBS_MEDIA_STATE_PLAYING":
                result["issues"].append(f"Not playing: {state.media_state}")
        except Exception as e:
            result["issues"].append(f"State check failed: {e}")

        # Check mute status
        try:
            muted = client.get_input_mute(name=OBS_AUDIO_SOURCE)
            result["muted"] = muted.input_muted
            if muted.input_muted:
                result["issues"].append("Source is muted")
        except Exception as e:
            result["issues"].append(f"Mute check failed: {e}")

        # Check volume
        try:
            vol = client.get_input_volume(name=OBS_AUDIO_SOURCE)
            result["volume_db"] = vol.input_volume_db
            if vol.input_volume_db < -30:
                result["issues"].append(f"Volume very low: {vol.input_volume_db} dB")
        except Exception as e:
            result["issues"].append(f"Volume check failed: {e}")

        # Determine health
        result["healthy"] = len(result["issues"]) == 0

        # Emit telemetry
        if result["healthy"]:
            emit_event("audio_health_ok",
                      source=OBS_AUDIO_SOURCE,
                      state=result["state"],
                      volume_db=result["volume_db"])
        else:
            emit_event("audio_health_issue",
                      source=OBS_AUDIO_SOURCE,
                      issues=result["issues"])

        return result

    except Exception as e:
        result["issues"].append(f"OBS connection failed: {e}")
        emit_event("audio_error", source=OBS_AUDIO_SOURCE, error=str(e))
        return result


def restart_audio_source() -> Dict[str, Any]:
    """
    Restart antifaFM Radio media source.

    Returns:
        Dict with restart status.
    """
    result = {
        "source": OBS_AUDIO_SOURCE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": False,
        "previous_state": None,
        "new_state": None,
    }

    try:
        client = _get_obs_client()

        # Get previous state
        try:
            state = client.get_media_input_status(name=OBS_AUDIO_SOURCE)
            result["previous_state"] = state.media_state
        except:
            pass

        # Restart media
        client.trigger_media_input_action(
            name=OBS_AUDIO_SOURCE,
            action="OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART"
        )

        # Ensure not muted
        client.set_input_mute(name=OBS_AUDIO_SOURCE, muted=False)

        # Wait and check new state
        time.sleep(1)
        try:
            state = client.get_media_input_status(name=OBS_AUDIO_SOURCE)
            result["new_state"] = state.media_state
            result["success"] = state.media_state == "OBS_MEDIA_STATE_PLAYING"
        except:
            pass

        emit_event("audio_restarted",
                  source=OBS_AUDIO_SOURCE,
                  previous_state=result["previous_state"],
                  new_state=result["new_state"],
                  success=result["success"])

        return result

    except Exception as e:
        result["error"] = str(e)
        emit_event("audio_error", source=OBS_AUDIO_SOURCE, error=str(e))
        return result


def check_stream_reachable() -> Dict[str, Any]:
    """
    Check if stream URL is reachable.

    Returns:
        Dict with reachability status.
    """
    result = {
        "url": STREAM_URL,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reachable": False,
    }

    try:
        import urllib.request
        req = urllib.request.Request(STREAM_URL, method="HEAD")
        req.add_header("User-Agent", "antifaFM-DJ/1.0")

        with urllib.request.urlopen(req, timeout=5) as response:
            result["reachable"] = response.status < 400
            result["status_code"] = response.status
            result["content_type"] = response.headers.get("Content-Type")
    except Exception as e:
        # Streaming URLs often reject HEAD, try GET with range
        try:
            req = urllib.request.Request(STREAM_URL)
            req.add_header("User-Agent", "antifaFM-DJ/1.0")
            req.add_header("Range", "bytes=0-1")

            with urllib.request.urlopen(req, timeout=5) as response:
                result["reachable"] = True
                result["status_code"] = response.status
        except Exception as e2:
            result["error"] = str(e2)
            emit_event("stream_unreachable", url=STREAM_URL, error=str(e2))

    return result


async def health_daemon():
    """
    Run health monitoring daemon.

    Checks audio health every HEALTH_CHECK_INTERVAL seconds.
    Auto-restarts if audio stops playing.
    """
    logger.info(f"[DJ] Starting health daemon (interval: {HEALTH_CHECK_INTERVAL}s)")
    emit_event("daemon_started", interval_sec=HEALTH_CHECK_INTERVAL)

    running = True
    restart_count = 0

    def signal_handler(sig, frame):
        nonlocal running
        logger.info("[DJ] Shutdown signal received")
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while running:
        try:
            health = check_audio_health()

            if health["healthy"]:
                logger.debug(f"[DJ] Audio healthy: {health['state']}")
            else:
                logger.warning(f"[DJ] Audio issues: {health['issues']}")

                # Auto-restart if not playing
                if health["state"] and health["state"] != "OBS_MEDIA_STATE_PLAYING":
                    logger.info("[DJ] Attempting auto-restart...")
                    restart_result = restart_audio_source()
                    restart_count += 1

                    if restart_result["success"]:
                        logger.info("[DJ] Audio restarted successfully")
                    else:
                        logger.error(f"[DJ] Restart failed: {restart_result}")

                # Unmute if muted
                if health["muted"]:
                    try:
                        client = _get_obs_client()
                        client.set_input_mute(name=OBS_AUDIO_SOURCE, muted=False)
                        logger.info("[DJ] Unmuted audio source")
                    except Exception as e:
                        logger.error(f"[DJ] Unmute failed: {e}")

        except Exception as e:
            logger.error(f"[DJ] Health check error: {e}")

        await asyncio.sleep(HEALTH_CHECK_INTERVAL)

    emit_event("daemon_stopped", restart_count=restart_count)
    logger.info(f"[DJ] Daemon stopped (restarts: {restart_count})")


def get_status() -> Dict[str, Any]:
    """Get comprehensive status."""
    return {
        "audio_health": check_audio_health(),
        "stream_reachable": check_stream_reachable(),
        "config": {
            "stream_url": STREAM_URL,
            "obs_source": OBS_AUDIO_SOURCE,
            "check_interval": HEALTH_CHECK_INTERVAL,
        }
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="antifaFM DJ - Audio health monitoring"
    )
    parser.add_argument("--check", action="store_true", help="Check audio health")
    parser.add_argument("--restart", action="store_true", help="Restart audio source")
    parser.add_argument("--daemon", action="store_true", help="Run health daemon")
    parser.add_argument("--status", action="store_true", help="Show full status")
    parser.add_argument("--stream", action="store_true", help="Check stream URL")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.check:
        result = check_audio_health()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n=== antifaFM DJ - Audio Health ===")
            print(f"Source: {result['source']}")
            print(f"State: {result['state']}")
            print(f"Volume: {result['volume_db']} dB")
            print(f"Muted: {result['muted']}")
            print(f"Healthy: {'YES' if result['healthy'] else 'NO'}")
            if result['issues']:
                print(f"Issues: {', '.join(result['issues'])}")
        return

    if args.restart:
        result = restart_audio_source()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n=== antifaFM DJ - Restart ===")
            print(f"Source: {result['source']}")
            print(f"Previous state: {result['previous_state']}")
            print(f"New state: {result['new_state']}")
            print(f"Success: {'YES' if result['success'] else 'NO'}")
        return

    if args.stream:
        result = check_stream_reachable()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n=== antifaFM DJ - Stream Check ===")
            print(f"URL: {result['url']}")
            print(f"Reachable: {'YES' if result['reachable'] else 'NO'}")
            if result.get('error'):
                print(f"Error: {result['error']}")
        return

    if args.status:
        result = get_status()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n=== antifaFM DJ - Full Status ===")
            health = result['audio_health']
            print(f"\nAudio Health:")
            print(f"  State: {health['state']}")
            print(f"  Volume: {health['volume_db']} dB")
            print(f"  Muted: {health['muted']}")
            print(f"  Healthy: {'YES' if health['healthy'] else 'NO'}")

            stream = result['stream_reachable']
            print(f"\nStream:")
            print(f"  URL: {stream['url']}")
            print(f"  Reachable: {'YES' if stream['reachable'] else 'NO'}")

            config = result['config']
            print(f"\nConfig:")
            print(f"  OBS Source: {config['obs_source']}")
            print(f"  Check Interval: {config['check_interval']}s")
        return

    if args.daemon:
        print("[DJ] Starting antifaFM DJ health daemon...")
        print(f"[DJ] Monitoring: {OBS_AUDIO_SOURCE}")
        print(f"[DJ] Interval: {HEALTH_CHECK_INTERVAL}s")
        print("[DJ] Press Ctrl+C to stop")
        asyncio.run(health_daemon())
        return

    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
