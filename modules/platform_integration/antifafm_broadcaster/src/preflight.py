"""antifaFM Preflight Module

Side-effect-free preflight checks for antifaFM/OBS readiness.
Per ANTIFAFM_PREFLIGHT_RELOCATION_AUDIT_20260516.

WSP References:
- WSP 97: Truth Boundaries (no false claims)
- WSP 50: Pre-Action Verification
"""

import os
import socket
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class AntifaFMPreflightResult:
    """Result of preflight check - NO SIDE EFFECTS."""

    # Overall status
    ready: bool = False

    # Component status
    obs_available: bool = False
    obs_websocket_reachable: bool = False
    stream_config_valid: bool = False
    youtube_api_configured: bool = False
    ffmpeg_available: bool = False

    # Runtime state (read-only checks)
    broadcaster_running: bool = False
    active_stream_id: Optional[str] = None

    # Diagnostics
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize for logging/display."""
        return {
            "ready": self.ready,
            "obs_available": self.obs_available,
            "obs_websocket_reachable": self.obs_websocket_reachable,
            "stream_config_valid": self.stream_config_valid,
            "youtube_api_configured": self.youtube_api_configured,
            "ffmpeg_available": self.ffmpeg_available,
            "broadcaster_running": self.broadcaster_running,
            "active_stream_id": self.active_stream_id,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _check_obs_websocket_reachable(
    host: str = "localhost",
    port: int = 4455,
    timeout: float = 1.0
) -> bool:
    """Check if OBS WebSocket port is reachable (TCP connect only).

    NO SIDE EFFECTS - just checks if port accepts connections.
    Does NOT authenticate or send commands.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _check_ffmpeg_available() -> bool:
    """Check if ffmpeg is in PATH.

    NO SIDE EFFECTS - just checks PATH/existence.
    """
    import shutil
    return shutil.which("ffmpeg") is not None


def _check_youtube_api_configured() -> bool:
    """Check if YouTube API credentials are configured.

    NO SIDE EFFECTS - checks file existence and env vars.
    """
    # Check for client secrets file
    secrets_paths = [
        Path("client_secrets.json"),
        Path("modules/platform_integration/video_comments/client_secrets.json"),
        Path.home() / ".config" / "youtube" / "client_secrets.json",
    ]
    has_secrets = any(p.exists() for p in secrets_paths)

    # Check for API key in environment
    has_api_key = bool(os.environ.get("YOUTUBE_API_KEY"))

    return has_secrets or has_api_key


def _check_stream_config_valid() -> bool:
    """Check if stream configuration exists and is valid.

    NO SIDE EFFECTS - reads config files only.
    """
    config_paths = [
        Path("antifafm_config.json"),
        Path("modules/platform_integration/antifafm_broadcaster/config/stream_config.json"),
    ]

    for path in config_paths:
        if path.exists():
            try:
                import json
                with open(path, "r") as f:
                    config = json.load(f)
                # Minimal validation - has required keys
                if "stream_key" in config or "broadcast_id" in config:
                    return True
            except (json.JSONDecodeError, IOError):
                continue

    # Also check environment for stream key
    return bool(os.environ.get("YOUTUBE_STREAM_KEY"))


def _check_broadcaster_running() -> tuple[bool, Optional[str]]:
    """Check if antifaFM broadcaster is currently running.

    NO SIDE EFFECTS - reads state files only.

    Returns:
        (is_running, active_stream_id)
    """
    state_file = Path("antifafm_state.json")
    if state_file.exists():
        try:
            import json
            with open(state_file, "r") as f:
                state = json.load(f)
            is_running = state.get("running", False)
            stream_id = state.get("broadcast_id") or state.get("stream_id")
            return is_running, stream_id
        except (json.JSONDecodeError, IOError):
            pass
    return False, None


def run_preflight(
    obs_host: str = "localhost",
    obs_port: int = 4455,
    require_obs: bool = True,
    require_youtube: bool = True,
) -> AntifaFMPreflightResult:
    """Run preflight checks for antifaFM readiness.

    THIS FUNCTION HAS NO SIDE EFFECTS.
    - Does NOT start OBS
    - Does NOT spawn FFmpeg processes
    - Does NOT create YouTube broadcasts
    - Does NOT connect to WebSocket (only TCP probe)

    Args:
        obs_host: OBS WebSocket host
        obs_port: OBS WebSocket port
        require_obs: If True, OBS must be available for ready=True
        require_youtube: If True, YouTube API must be configured for ready=True

    Returns:
        AntifaFMPreflightResult with status and diagnostics
    """
    result = AntifaFMPreflightResult()

    # Check OBS WebSocket
    result.obs_websocket_reachable = _check_obs_websocket_reachable(obs_host, obs_port)
    if result.obs_websocket_reachable:
        result.obs_available = True
    else:
        if require_obs:
            result.errors.append(f"OBS WebSocket not reachable at {obs_host}:{obs_port}")
        else:
            result.warnings.append(f"OBS WebSocket not reachable at {obs_host}:{obs_port}")

    # Check FFmpeg
    result.ffmpeg_available = _check_ffmpeg_available()
    if not result.ffmpeg_available:
        result.warnings.append("FFmpeg not found in PATH")

    # Check YouTube API
    result.youtube_api_configured = _check_youtube_api_configured()
    if not result.youtube_api_configured:
        if require_youtube:
            result.errors.append("YouTube API not configured (no client_secrets.json or YOUTUBE_API_KEY)")
        else:
            result.warnings.append("YouTube API not configured")

    # Check stream config
    result.stream_config_valid = _check_stream_config_valid()
    if not result.stream_config_valid:
        result.warnings.append("No stream configuration found")

    # Check broadcaster state
    result.broadcaster_running, result.active_stream_id = _check_broadcaster_running()
    if result.broadcaster_running:
        result.warnings.append(f"Broadcaster already running (stream: {result.active_stream_id})")

    # Determine overall readiness
    result.ready = (
        (not require_obs or result.obs_available) and
        (not require_youtube or result.youtube_api_configured) and
        not result.broadcaster_running and
        len(result.errors) == 0
    )

    return result


def format_preflight_status(result: AntifaFMPreflightResult) -> str:
    """Format preflight result for display.

    Returns human-readable status string.
    """
    lines = []

    status = "READY" if result.ready else "NOT READY"
    lines.append(f"antifaFM Preflight: {status}")
    lines.append("-" * 40)

    lines.append(f"  OBS WebSocket:     {'OK' if result.obs_websocket_reachable else 'NOT REACHABLE'}")
    lines.append(f"  YouTube API:       {'CONFIGURED' if result.youtube_api_configured else 'NOT CONFIGURED'}")
    lines.append(f"  FFmpeg:            {'AVAILABLE' if result.ffmpeg_available else 'NOT FOUND'}")
    lines.append(f"  Stream Config:     {'VALID' if result.stream_config_valid else 'NOT FOUND'}")
    lines.append(f"  Broadcaster:       {'RUNNING' if result.broadcaster_running else 'STOPPED'}")

    if result.active_stream_id:
        lines.append(f"  Active Stream:     {result.active_stream_id}")

    if result.errors:
        lines.append("")
        lines.append("Errors:")
        for err in result.errors:
            lines.append(f"  - {err}")

    if result.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warn in result.warnings:
            lines.append(f"  - {warn}")

    return "\n".join(lines)


# Convenience function for menu integration
def preflight_check_for_menu(
    require_obs: bool = False,
    require_youtube: bool = False,
) -> tuple[bool, str]:
    """Run preflight and return (ready, status_message) for menu display.

    Default: non-strict mode (warnings instead of errors).
    Call with require_obs=True for strict OBS checks.
    """
    result = run_preflight(
        require_obs=require_obs,
        require_youtube=require_youtube,
    )
    return result.ready, format_preflight_status(result)
