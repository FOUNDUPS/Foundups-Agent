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
    "tool.started",
    "tool.completed",
    "subagent.start",
    "subagent.complete",
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
        return (
            terminals[0].get("output") == terminal_status.get("output")
            and _has_exact_native_leaf_delegation(events)
        )
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
    if event_name.startswith("approval"):
        return False
    return event_name in _ALLOWED_EVENTS


def _has_exact_native_leaf_delegation(events: list[Mapping[str, object]]) -> bool:
    names = [str(event.get("event") or "") for event in events]
    child_starts = [event for event in events if event.get("event") == "subagent.start"]
    child_completes = [event for event in events if event.get("event") == "subagent.complete"]
    tool_events = [event for event in events if str(event.get("event") or "").startswith("tool.")]
    tool_names = [str(event.get("event") or "") for event in tool_events]
    paired_tool_names = [
        name
        for _pair in range(len(tool_events) // 2)
        for name in ("tool.started", "tool.completed")
    ]
    if (
        len(child_starts) != 1
        or len(child_completes) != 1
        or not tool_events
        or tool_names != paired_tool_names
    ):
        return False
    child_started, child_done = child_starts[0], child_completes[0]
    if not _closed_child_lifecycle(child_started, child_done):
        return False
    child_start_index = events.index(child_started)
    child_done_index = events.index(child_done)
    terminal_index = names.index("run.completed")
    return (
        terminal_index == len(events) - 1
        and child_start_index < child_done_index < terminal_index
        and _closed_delegate_telemetry(
            events, tool_events, child_start_index, child_done_index, terminal_index
        )
    )


def _closed_child_lifecycle(
    child_started: Mapping[str, object], child_done: Mapping[str, object]
) -> bool:
    started_id = str(child_started.get("subagent_id") or "")
    completed_id = str(child_done.get("subagent_id") or "")
    started_session = str(child_started.get("child_session_id") or "")
    completed_session = str(child_done.get("child_session_id") or "")
    if (
        not started_id
        or started_id != completed_id
        or not started_session
        or started_session != completed_session
        or child_started.get("status") != "running"
        or child_started.get("depth") != 0
        or child_done.get("status") != "completed"
        or child_done.get("files_read") != []
        or child_done.get("files_written") != []
    ):
        return False
    return True


def _closed_delegate_telemetry(events, tool_events, child_start, child_done, terminal) -> bool:
    if any(event.get("tool") != "delegate_task" for event in tool_events):
        return False
    starts = [index for index, event in enumerate(events) if event.get("event") == "tool.started"]
    completes = [index for index, event in enumerate(events) if event.get("event") == "tool.completed"]
    successful = [index for index in completes if events[index].get("error") is False]
    return (
        bool(starts) and starts[0] < child_start
        and bool(successful) and successful[-1] > child_done
        and successful[-1] < terminal
        and tool_events[-1].get("event") == "tool.completed"
        and tool_events[-1].get("error") is False
    )


__all__ = ["verify_hermes_postflight", "verify_hermes_run_event_log"]
