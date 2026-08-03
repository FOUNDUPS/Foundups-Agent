"""Verify the complete upstream Hermes per-run SSE event history."""

from __future__ import annotations

from typing import Mapping

from .reddog_hermes_api_confinement import (
    hermes_tool_surface_is_closed,
    strict_json_mapping,
)

_ALLOWED_EVENTS = {
    "message.delta",
    "reasoning.available",
    "run.cancelled",
    "run.completed",
    "run.failed",
}
_TERMINAL_EVENT = {
    "cancelled": "run.cancelled",
    "completed": "run.completed",
    "failed": "run.failed",
}


def verify_hermes_run_event_log(
    transport,
    headers: Mapping[str, str],
    run_id: str,
    timeout_seconds: int,
    terminal_status: Mapping[str, object],
) -> bool:
    try:
        response = transport.request(
            "GET",
            f"/v1/runs/{run_id}/events",
            headers=headers,
            payload=None,
            timeout_seconds=timeout_seconds,
        )
    except Exception:
        return False
    if response.status != 200 or response.output_limit_exceeded:
        return False
    events = _parse_sse_events(response.body, run_id)
    if events is None:
        return False
    expected = _TERMINAL_EVENT.get(str(terminal_status.get("status") or ""))
    terminals = [event for event in events if event.get("event") in _TERMINAL_EVENT.values()]
    if expected is None or len(terminals) != 1 or terminals[0].get("event") != expected:
        return False
    if expected == "run.completed":
        return terminals[0].get("output") == terminal_status.get("output")
    return True


def verify_hermes_postflight(transport, headers, timeout_seconds: int) -> bool:
    values = []
    for path in ("/v1/toolsets", "/v1/skills"):
        response = transport.request(
            "GET", path, headers=headers, payload=None, timeout_seconds=timeout_seconds
        )
        if response.status != 200 or response.output_limit_exceeded:
            return False
        values.append(strict_json_mapping(response.body))
    return hermes_tool_surface_is_closed(values[0], values[1])


def _parse_sse_events(raw: str, run_id: str):
    events = []
    for line in raw.splitlines():
        if not line or line.startswith(":"):
            continue
        if not line.startswith("data: "):
            return None
        event = strict_json_mapping(line[6:])
        if not _event_is_confined(event, run_id):
            return None
        events.append(event)
    return events or None


def _event_is_confined(event: object, run_id: str) -> bool:
    if not isinstance(event, Mapping) or event.get("run_id") != run_id:
        return False
    event_name = str(event.get("event") or "")
    if event_name.startswith(("tool", "approval", "subagent")):
        return False
    return event_name in _ALLOWED_EVENTS


__all__ = ["verify_hermes_postflight", "verify_hermes_run_event_log"]
