"""
Channel Configuration for YouTube Shorts Scheduler

Multi-channel support driven by the shared YouTube channel registry.

FLUID DUAL-BROWSER ARCHITECTURE (2026-01-29):
Both browsers have BOTH Google accounts logged in, so any browser can access any channel.
- Chrome (9222): Can access ALL channels via account picker
- Edge (9223): Can access ALL channels via account picker

Account Picker Structure (same on both browsers):
- Section 0 (Google Account A): UnDaoDu, Move2Japan
- Section 1 (Google Account B): FoundUps, antifaFM

The `preferred_port` is for optimization (minimize account switches).
The `available_ports` shows all browsers that can access the channel.
"""

from typing import Dict, Any, Optional, List
from urllib.parse import quote
import json
import socket

from modules.infrastructure.shared_utilities.youtube_channel_registry import get_channels

# Browser ports
CHROME_PORT = 9222
EDGE_PORT = 9223
ALL_PORTS = [CHROME_PORT, EDGE_PORT]


def _build_channel_config() -> Dict[str, Dict[str, Any]]:
    """Build channel config dict from shared registry."""
    channels: Dict[str, Dict[str, Any]] = {}
    for ch in get_channels(role="shorts"):
        key = ch.get("key")
        if not key:
            continue
        browser = ch.get("browser") or {}
        shorts = ch.get("shorts") or {}
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
        }
    return channels


# Channel configurations (registry-driven)
CHANNELS: Dict[str, Dict[str, Any]] = _build_channel_config()


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
    Select the best browser port for a channel.

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

    # Strategy 1: Reuse current browser if it can access this channel
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
