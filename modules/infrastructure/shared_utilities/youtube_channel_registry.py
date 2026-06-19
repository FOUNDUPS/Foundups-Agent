"""
YouTube Channel Registry - Single source of truth for channel metadata.

Purpose:
- Centralize channel IDs, names, handles, browser grouping, and rotation roles.
- Eliminate hard-coded channel lists scattered across modules.
- Enable adding new channels via CLI without code changes.

WSP References:
- WSP 3: Functional Distribution (shared utilities for cross-domain config)
- WSP 60: Module Memory Architecture (registry stored in module memory)
- WSP 84: Code Reuse (uses linkedin_account_registry for company ID resolution)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from modules.infrastructure.shared_utilities.linkedin_account_registry import get_company_id


_REGISTRY_PATH = Path(__file__).resolve().parent / "memory" / "youtube_channels.json"

# Browser ports (legacy defaults used across the codebase)
_CHROME_PORT = 9222
_EDGE_PORT = 9223

_DEFAULT_TIME_SLOTS = [
    "12:00 AM", "3:00 AM", "6:00 AM", "9:00 AM",
    "12:00 PM", "3:00 PM", "6:00 PM", "9:00 PM",
]


def _default_channels() -> List[Dict[str, Any]]:
    """Build default channel registry from env + safe fallbacks."""
    return [
        {
            "key": "move2japan",
            "id": os.getenv("MOVE2JAPAN_CHANNEL_ID", "UC-LSSlOZwpGIRIYihaz8zCw"),
            "name": "Move2Japan",
            "handle": "@MOVE2JAPAN",
            "timezone": "Asia/Tokyo",
            "roles": {"live_check": True, "comments": True, "shorts": True, "indexing": True},
            "content_types": ["short", "upload"],  # vlogs + shorts
            "browser": {
                "comment_browser": "chrome",
                "preferred_port": _CHROME_PORT,
                "available_ports": [_CHROME_PORT, _EDGE_PORT],
                "account_section": 0,
            },
            "shorts": {"time_slots": _DEFAULT_TIME_SLOTS, "max_per_day": 3, "description_template": "ffcpln"},
            "social": {"linkedin_company": "move2japan", "x_account": "geozai", "enabled": True, "signature": "0102🦞"},
        },
        {
            "key": "undaodu",
            "id": os.getenv("UNDAODU_CHANNEL_ID", "UCfHM9Fw9HD-NwiS0seD_oIA"),
            "name": "UnDaoDu",
            "handle": "@UnDaoDu",
            "timezone": "Asia/Tokyo",
            "roles": {"live_check": True, "comments": True, "shorts": True, "indexing": True},
            "content_types": ["short", "upload"],  # vlogs + shorts (NOT FFCPLN)
            "browser": {
                "comment_browser": "chrome",
                "preferred_port": _CHROME_PORT,
                "available_ports": [_CHROME_PORT, _EDGE_PORT],
                "account_section": 0,
            },
            "shorts": {"time_slots": _DEFAULT_TIME_SLOTS, "max_per_day": 3, "description_template": "undaodu"},
            "social": {"linkedin_company": "undaodu", "x_account": "undaodu", "enabled": True, "signature": "0102🦞012🖐️"},  # wsp01: 012 co-signs
        },
        {
            "key": "foundups",
            "id": os.getenv("FOUNDUPS_CHANNEL_ID", "UCSNTUXjAgpd4sgWYP0xoJgw"),
            "name": "FoundUps",
            "handle": "@FoundUps",
            "timezone": "America/New_York",
            "roles": {"live_check": True, "comments": True, "shorts": True, "indexing": True},
            "content_types": ["short"],  # startup/pAVS content (NOT FFCPLN)
            "browser": {
                "comment_browser": "edge",
                "preferred_port": _EDGE_PORT,
                "available_ports": [_CHROME_PORT, _EDGE_PORT],
                "account_section": 1,
            },
            "shorts": {"time_slots": _DEFAULT_TIME_SLOTS, "max_per_day": 3, "description_template": "foundups"},
            "social": {"linkedin_company": "foundups", "x_account": "foundups", "enabled": True, "signature": "0102🦞"},
        },
        {
            "key": "antifafm",
            "id": os.getenv("ANTIFAFM_CHANNEL_ID", "UCVSmg5aOhP4tnQ9KFUg97qA"),
            "name": "antifaFM",
            "handle": "@antifaFM",
            "timezone": "America/New_York",
            "roles": {"live_check": True, "comments": True, "shorts": True, "indexing": True},
            "content_types": ["short"],  # music shorts only
            "browser": {
                "comment_browser": "edge",
                "preferred_port": _EDGE_PORT,
                "available_ports": [_CHROME_PORT, _EDGE_PORT],
                "account_section": 1,
            },
            "shorts": {"time_slots": _DEFAULT_TIME_SLOTS, "max_per_day": 3, "description_template": "ffcpln"},
            "social": {"linkedin_company": "move2japan", "x_account": "antifafm", "enabled": True, "signature": "0102🦞"},  # wsp01: antifaFM posts to move2japan
        },
    ]


def _normalize_channel(channel: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize and fill missing channel fields."""
    normalized = dict(channel or {})
    key = str(normalized.get("key", "")).strip().lower()
    if not key:
        raise ValueError("Channel key is required")
    normalized["key"] = key
    normalized["id"] = str(normalized.get("id", "")).strip()
    normalized["name"] = str(normalized.get("name", key)).strip() or key
    normalized["handle"] = str(normalized.get("handle", f"@{normalized['name']}")).strip() or f"@{normalized['name']}"
    normalized["timezone"] = str(normalized.get("timezone", "UTC")).strip() or "UTC"

    roles = normalized.get("roles") or {}
    normalized["roles"] = {
        "live_check": bool(roles.get("live_check", True)),
        "comments": bool(roles.get("comments", True)),
        "shorts": bool(roles.get("shorts", True)),
        "indexing": bool(roles.get("indexing", True)),
    }

    browser = normalized.get("browser") or {}
    comment_browser = str(browser.get("comment_browser", "")).strip().lower() or "chrome"
    preferred_port = int(browser.get("preferred_port", _CHROME_PORT if comment_browser == "chrome" else _EDGE_PORT))
    available_ports = browser.get("available_ports") or [_CHROME_PORT, _EDGE_PORT]
    normalized["browser"] = {
        "comment_browser": comment_browser,
        "preferred_port": preferred_port,
        "available_ports": list(available_ports),
        "account_section": int(browser.get("account_section", 0)),
    }

    shorts = normalized.get("shorts") or {}
    normalized["shorts"] = {
        "time_slots": list(shorts.get("time_slots") or _DEFAULT_TIME_SLOTS),
        "max_per_day": int(shorts.get("max_per_day", 3)),
        "description_template": str(shorts.get("description_template", "ffcpln")),
    }

    # Content types: what this channel produces (short, upload)
    content_types = normalized.get("content_types") or ["short"]
    normalized["content_types"] = [str(ct).strip().lower() for ct in content_types if str(ct).strip()]

    social = normalized.get("social") or {}
    # Resolve linkedin_company to linkedin_page_id via central registry
    linkedin_company = str(social.get("linkedin_company", "")).strip()
    linkedin_page_id = str(social.get("linkedin_page_id", "")).strip()
    if linkedin_company and not linkedin_page_id:
        linkedin_page_id = get_company_id(linkedin_company) or ""
    normalized["social"] = {
        "linkedin_company": linkedin_company,
        "linkedin_page_id": linkedin_page_id,
        "x_account": str(social.get("x_account", "")),
        "enabled": bool(social.get("enabled", False)),
        "signature": str(social.get("signature", "0102🦞")),  # default lobster, 012 co-signs on undaodu
    }

    return normalized


def _merge_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure default channels exist in registry (non-destructive)."""
    ordered: List[Dict[str, Any]] = []
    existing_map: Dict[str, Dict[str, Any]] = {}
    for ch in data.get("channels", []):
        key = str(ch.get("key", "")).strip().lower()
        if not key:
            continue
        existing_map[key] = ch
        ordered.append(ch)
    for default in _default_channels():
        key = str(default.get("key", "")).strip().lower()
        if key and key not in existing_map:
            ordered.append(default)
    data["channels"] = ordered
    return data


def _load_registry_raw() -> Dict[str, Any]:
    if _REGISTRY_PATH.exists():
        try:
            return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _write_registry(data: Dict[str, Any]) -> None:
    _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REGISTRY_PATH.write_text(json.dumps(data, indent=2, sort_keys=False), encoding="utf-8")


def load_registry() -> Dict[str, Any]:
    """Load registry (creates default if missing)."""
    data = _load_registry_raw()
    if not data.get("channels"):
        data = {"version": 1, "channels": _default_channels()}
        _write_registry(data)
    else:
        data = _merge_defaults(data)
    # Normalize before returning
    channels = [_normalize_channel(ch) for ch in data.get("channels", [])]
    data["channels"] = channels
    return data


def save_registry(data: Dict[str, Any]) -> None:
    """Persist registry data."""
    channels = [_normalize_channel(ch) for ch in data.get("channels", [])]
    payload = {"version": int(data.get("version", 1)), "channels": channels}
    _write_registry(payload)


def get_channels(role: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return channels, optionally filtered by role."""
    data = load_registry()
    channels = data.get("channels", [])
    if not role:
        return channels
    role_key = role.strip().lower()
    return [ch for ch in channels if ch.get("roles", {}).get(role_key, True)]


def get_channel_keys(role: Optional[str] = None) -> List[str]:
    """Return channel keys (optionally filtered)."""
    return [ch["key"] for ch in get_channels(role=role)]


def get_channel_ids(role: Optional[str] = None) -> List[str]:
    """Return channel IDs (optionally filtered)."""
    return [ch["id"] for ch in get_channels(role=role) if ch.get("id")]


def get_channel_by_key(key: str) -> Optional[Dict[str, Any]]:
    if not key:
        return None
    key = key.strip().lower()
    for ch in get_channels():
        if ch.get("key") == key:
            return ch
    return None


def get_channel_by_id(channel_id: str) -> Optional[Dict[str, Any]]:
    if not channel_id:
        return None
    for ch in get_channels():
        if ch.get("id") == channel_id:
            return ch
    return None


def get_rotation_order(role: Optional[str] = None) -> List[str]:
    """
    Determine rotation order using env override if present.

    Env format: "Move2Japan,UnDaoDu,FoundUps,antifaFM"
    Names are matched against channel name or key (case-insensitive).
    """
    channels = get_channels(role=role)
    name_map = {ch["name"].lower(): ch["key"] for ch in channels}
    key_map = {ch["key"].lower(): ch["key"] for ch in channels}

    env_order = os.getenv("YT_ROTATION_ORDER", "").strip()
    if env_order:
        ordered: List[str] = []
        for raw in env_order.split(","):
            token = raw.strip().lower()
            if not token:
                continue
            key = key_map.get(token) or name_map.get(token)
            if key and key not in ordered:
                ordered.append(key)
        if ordered:
            # Append any missing channels to preserve full coverage
            for ch in channels:
                if ch["key"] not in ordered:
                    ordered.append(ch["key"])
            return ordered

    return [ch["key"] for ch in channels]


def group_channels_by_browser(role: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Group channels by comment_browser (chrome/edge)."""
    grouped: Dict[str, List[Dict[str, Any]]] = {"chrome": [], "edge": []}
    for ch in get_channels(role=role):
        browser = (ch.get("browser") or {}).get("comment_browser", "chrome")
        grouped.setdefault(browser, []).append(ch)
    return grouped


def build_fallbacks(role: Optional[str] = None) -> Dict[str, str]:
    """
    Build fallback mapping by account_section within the same browser group.
    Returns mapping of channel name -> fallback channel name.
    """
    fallbacks: Dict[str, str] = {}
    grouped = group_channels_by_browser(role=role)
    for channels in grouped.values():
        # Group by account_section
        buckets: Dict[int, List[Dict[str, Any]]] = {}
        for ch in channels:
            section = int((ch.get("browser") or {}).get("account_section", 0))
            buckets.setdefault(section, []).append(ch)
        for bucket in buckets.values():
            if len(bucket) < 2:
                continue
            keys = [ch["name"] for ch in bucket]
            for i, name in enumerate(keys):
                fallbacks[name] = keys[(i + 1) % len(keys)]
    return fallbacks


def add_channel(channel: Dict[str, Any]) -> Tuple[bool, str]:
    """Add a channel to the registry. Returns (ok, message)."""
    data = load_registry()
    channels = data.get("channels", [])
    normalized = _normalize_channel(channel)
    key = normalized["key"]
    if any(ch.get("key") == key for ch in channels):
        return False, f"Channel key already exists: {key}"
    channels.append(normalized)
    data["channels"] = channels
    save_registry(data)
    return True, f"Added channel: {normalized['name']} ({normalized['key']})"
