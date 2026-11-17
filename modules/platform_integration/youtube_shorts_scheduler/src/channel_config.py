"""
Channel Configuration for YouTube Shorts Scheduler

Multi-channel support driven by the shared YouTube channel registry.

The preferred and available ports describe transport candidates. Each prepared
browser's access depends on its current account and must be observed on the
requested Studio surface.
"""

from typing import Dict, Any, Optional, List
from urllib.parse import quote
import json
import os
import re
import socket

from modules.infrastructure.shared_utilities.youtube_channel_registry import get_channels

from .peak_window import get_peak_slots_et, is_move2japan

# Browser ports
CHROME_PORT = 9222
EDGE_PORT = 9223
ALL_PORTS = [CHROME_PORT, EDGE_PORT]


# Keep denial markers aligned with the existing Studio account access check.
# This probe has no recovery or account switching behavior.
_STUDIO_PERMISSION_OBSERVATION = r"""
const text = document.body && document.body.innerText;
const norm = typeof text === 'string' ? text.toLowerCase().replace(/\u2019/g, "'") : '';
if (document.querySelector('#selectaccount-link') || [
    "don't have permission", "dont have permission", "do not have permission",
    "permission to view this page", "switch account", "return to studio"
].some(phrase => norm.includes(phrase))) return {permission: 'denied'};
if (!norm.trim() || !document.querySelector('ytcp-app')) return {permission: 'unknown'};
"""


def verify_schedule_target_access(driver, channel_id: str, parent_video_id: str,
                                  *, expected_title: Optional[str] = None) -> Dict[str, Any]:
    """Observe the frozen parent editor on the caller's already locked driver."""
    from modules.infrastructure.foundups_selenium.src.youtube_verification import VerificationHandoff
    from .video_policy import DETAIL_SNAPSHOT_SCRIPT, detail_identity

    if (not isinstance(channel_id, str) or not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", channel_id)
            or not isinstance(parent_video_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", parent_video_id)):
        return {"verified": False, "reason": "invalid_schedule_target"}

    probe = (_STUDIO_PERMISSION_OBSERVATION + "\nconst detail = (() => {\n"
             + DETAIL_SNAPSHOT_SCRIPT + "\n})();\nreturn {...detail, permission: 'observed'};")
    try:
        snapshot = driver.execute_script(probe)
        permission = snapshot.get("permission") if isinstance(snapshot, dict) else None
        if permission == "denied":
            return {"verified": False, "reason": "studio_permission_denied"}
        if permission != "observed":
            return {"verified": False, "reason": "studio_permission_unobserved"}
        detail_identity(snapshot, channel_id, parent_video_id)
        if expected_title is not None and (
                not isinstance(expected_title, str) or not expected_title
                or snapshot.get('title') != expected_title):
            return {"verified": False, "reason": "studio_parent_title_changed"}
    except VerificationHandoff:
        raise
    except Exception:
        return {"verified": False, "reason": "studio_parent_access_unverified"}
    return {"verified": True, "reason": "studio_parent_access_verified"}


def _build_channel_config() -> Dict[str, Dict[str, Any]]:
    """Build channel config dict from shared registry."""
    channels: Dict[str, Dict[str, Any]] = {}
    for ch in get_channels(role="shorts"):
        key = ch.get("key")
        if not key:
            continue
        browser = ch.get("browser") or {}
        shorts = ch.get("shorts") or {}
        if is_move2japan(ch.get("id", "")):
            shorts = {**shorts, "time_slots": get_peak_slots_et(ch["id"]), "max_per_day": 8}
        channels[key] = {
            "id": ch.get("id"),
            "name": ch.get("name"),
            "handle": ch.get("handle"),
            "timezone": ch.get("timezone"),
            "time_slots": shorts.get("time_slots") or [],
            "max_per_day": shorts.get("max_per_day", 3),
            "chrome_port": browser.get("preferred_port", CHROME_PORT),
            "preferred_port": browser.get("preferred_port", CHROME_PORT),
            "available_ports": browser.get("available_ports", ALL_PORTS),
            "account_section": browser.get("account_section", 0),
            "description_template": shorts.get("description_template", "ffcpln"),
            "content_types": ch.get("content_types") or ["short"],
            "made_for_kids": shorts.get("made_for_kids"),
        }
    return channels


# Channel configurations (registry-driven)
CHANNELS: Dict[str, Dict[str, Any]] = _build_channel_config()


def configured_audience(channel_id: str) -> Optional[bool]:
    """Resolve explicit native-ID policy; this does not enable a channel's roles."""
    environment = {}
    for setting, target in (("YT_MADE_FOR_KIDS_CHANNEL_IDS", True),
                            ("YT_NOT_MADE_FOR_KIDS_CHANNEL_IDS", False)):
        raw = os.environ.get(setting, "").strip()
        if not raw:
            continue
        for value in raw.split(","):
            value = value.strip()
            if not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", value) or value in environment:
                raise ValueError("audience_environment_invalid_or_duplicate")
            environment[value] = target
    matches = [config for config in CHANNELS.values() if config.get("id") == channel_id]
    if len(matches) > 1:
        raise ValueError("audience_registry_ambiguous")
    registered = matches[0].get("made_for_kids") if matches else None
    if registered is not None and type(registered) is not bool:
        raise ValueError("audience_registry_invalid")
    if channel_id in environment:
        target = environment[channel_id]
        if registered is not None and registered is not target:
            raise ValueError("audience_configuration_conflict")
        return target
    return registered


def is_port_available(port: int) -> bool:
    """Check if a browser debug port is responding."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def get_available_browsers() -> List[int]:
    """Return list of browser ports that are currently running."""
    return [p for p in ALL_PORTS if is_port_available(p)]


def select_browser_for_channel(channel_key: str, current_port: Optional[int] = None) -> int:
    """
    Select a browser transport candidate by preference and TCP availability.

    Strategy:
    1. If current_port is provided and available, use it (minimize switching)
    2. Use preferred_port if available
    3. Fall back to any available port
    4. Return preferred_port even if unavailable (caller handles connection)

    Args:
        channel_key: Channel identifier
        current_port: Port of browser currently in use (if any)

    Returns:
        Browser port to use
    """
    config = CHANNELS.get(channel_key.lower(), {})
    preferred = config.get("preferred_port", CHROME_PORT)
    available = config.get("available_ports", ALL_PORTS)

    # Strategy 1: Reuse the current browser if it is a configured candidate.
    if current_port and current_port in available and is_port_available(current_port):
        return current_port

    # Strategy 2: Use preferred port if available
    if is_port_available(preferred):
        return preferred

    # Strategy 3: Try any available port
    for port in available:
        if is_port_available(port):
            return port

    # Fallback: return preferred (caller will handle connection failure)
    return preferred


def get_channel_config(channel_key: str) -> Optional[Dict[str, Any]]:
    """
    Get configuration for a channel.

    Args:
        channel_key: "move2japan", "undaodu", "foundups", or "antifafm"

    Returns:
        Channel config dict or None
    """
    return CHANNELS.get(channel_key.lower())


def get_channels_by_content_type(content_type: str) -> List[str]:
    """
    Get channel keys that support a specific content type.

    Args:
        content_type: "short" or "upload"

    Returns:
        List of channel keys supporting that content type
    """
    content_type = content_type.lower().strip()
    return [
        key for key, config in CHANNELS.items()
        if content_type in config.get("content_types", ["short"])
    ]


def channel_supports_content_type(channel_key: str, content_type: str) -> bool:
    """
    Check if a channel supports a specific content type.

    Args:
        channel_key: Channel identifier
        content_type: "short" or "upload"

    Returns:
        True if channel supports the content type
    """
    config = get_channel_config(channel_key)
    if not config:
        return False
    return content_type.lower().strip() in config.get("content_types", ["short"])


def build_studio_url(
    channel_id: str,
    content_type: str = "short",
    visibility: Optional[str] = None,
    sort_by: str = "date",
    sort_order: str = "DESCENDING"
) -> str:
    """
    Build YouTube Studio URL with filters.

    Args:
        channel_id: YouTube channel ID
        content_type: "short", "upload", "live"
        visibility: "UNLISTED", "SCHEDULED", "PUBLIC", "PRIVATE", or None
        sort_by: "date", "views", etc.
        sort_order: "DESCENDING" or "ASCENDING"

    Returns:
        Full YouTube Studio URL with encoded parameters
    """
    base_url = f"https://studio.youtube.com/channel/{channel_id}/videos/{content_type}"

    # Build filter
    if visibility:
        filter_obj = [{"name": "VISIBILITY", "value": [visibility]}]
    else:
        filter_obj = []

    # Build sort
    sort_obj = {"columnType": sort_by, "sortOrder": sort_order}

    # Encode parameters
    filter_param = quote(json.dumps(filter_obj))
    sort_param = quote(json.dumps(sort_obj))

    return f"{base_url}?filter={filter_param}&sort={sort_param}"


def get_studio_urls(channel_key: str) -> Dict[str, str]:
    """
    Get all pre-built Studio URLs for a channel.

    Args:
        channel_key: "move2japan", "undaodu", "foundups", or "antifafm"

    Returns:
        Dict with URL keys: unlisted_shorts, scheduled_shorts, all_shorts
    """
    config = get_channel_config(channel_key)
    if not config:
        raise ValueError(f"Unknown channel: {channel_key}")

    channel_id = config["id"]

    return {
        # Shorts URLs
        "unlisted_shorts": build_studio_url(channel_id, "short", "UNLISTED"),
        "scheduled_shorts": build_studio_url(channel_id, "short", "SCHEDULED"),
        "public_shorts": build_studio_url(channel_id, "short", "PUBLIC"),
        "all_shorts": build_studio_url(channel_id, "short"),
        # Video (upload) URLs - for channels with personal vlogs
        "unlisted_videos": build_studio_url(channel_id, "upload", "UNLISTED"),
        "scheduled_videos": build_studio_url(channel_id, "upload", "SCHEDULED"),
        "public_videos": build_studio_url(channel_id, "upload", "PUBLIC"),
        "all_videos": build_studio_url(channel_id, "upload"),
        # Base
        "base": f"https://studio.youtube.com/channel/{channel_id}",
    }
