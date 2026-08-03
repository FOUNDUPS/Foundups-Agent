"""Deterministic confinement checks for the upstream Hermes API surface."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

HERMES_ARTIFACT_PROFILE = "reddogartifact"
HERMES_EXPECTED_API_VERSION = "0.19.1"

_FEATURES = {
    "run_submission": True,
    "run_status": True,
    "run_events_sse": True,
    "run_stop": True,
    "run_approval_response": True,
    "tool_progress_events": True,
    "approval_events": True,
}
_ENDPOINTS = {
    "runs": ("POST", "/v1/runs"),
    "run_status": ("GET", "/v1/runs/{run_id}"),
    "run_events": ("GET", "/v1/runs/{run_id}/events"),
    "run_stop": ("POST", "/v1/runs/{run_id}/stop"),
    "skills": ("GET", "/v1/skills"),
    "toolsets": ("GET", "/v1/toolsets"),
}


@dataclass(frozen=True)
class HermesApiPreflight:
    accepted: bool
    version: str = ""
    rejection_reason: str = ""


def verify_hermes_api_preflight(
    *,
    unauthenticated_status: int,
    capabilities: object,
    health: object,
    toolsets: object,
    skills: object,
) -> HermesApiPreflight:
    if unauthenticated_status not in {401, 403}:
        return _reject("FAIL_HERMES_AUTH_NOT_REQUIRED")
    if not _capabilities_are_confined(capabilities):
        return _reject("FAIL_HERMES_CAPABILITY_CONFINEMENT")
    if not _health_is_exact(health):
        return _reject("FAIL_HERMES_RUNTIME_IDENTITY")
    if not hermes_tool_surface_is_closed(toolsets, skills):
        return _reject("FAIL_HERMES_TOOLSET_CONFINEMENT")
    return HermesApiPreflight(True, HERMES_EXPECTED_API_VERSION)


def hermes_tool_surface_is_closed(toolsets: object, skills: object) -> bool:
    """Require a complete disabled-toolset inventory and no visible skills."""
    return _toolsets_are_disabled(toolsets) and _skills_are_empty(skills)


def strict_json_mapping(raw: str) -> dict[str, Any] | None:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _capabilities_are_confined(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    runtime, auth = value.get("runtime"), value.get("auth")
    if (
        value.get("object") != "hermes.api_server.capabilities"
        or value.get("platform") != "hermes-agent"
        or value.get("model") != HERMES_ARTIFACT_PROFILE
        or auth != {"type": "bearer", "required": True}
        or runtime is None
    ):
        return False
    if not isinstance(runtime, Mapping) or any(
        (
            runtime.get("mode") != "server_agent",
            runtime.get("tool_execution") != "server",
            runtime.get("split_runtime") is not False,
        )
    ):
        return False
    features, endpoints = value.get("features"), value.get("endpoints")
    if not isinstance(features, Mapping) or not isinstance(endpoints, Mapping):
        return False
    if any(features.get(key) is not expected for key, expected in _FEATURES.items()):
        return False
    return all(
        isinstance(endpoints.get(key), Mapping)
        and endpoints[key].get("method") == method
        and endpoints[key].get("path") == path
        for key, (method, path) in _ENDPOINTS.items()
    )


def _health_is_exact(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("platform") == "hermes-agent"
        and value.get("version") == HERMES_EXPECTED_API_VERSION
        and value.get("status") == "ok"
    )


def _toolsets_are_disabled(value: object) -> bool:
    if not isinstance(value, Mapping) or value.get("object") != "list":
        return False
    if value.get("platform") != "api_server" or not isinstance(value.get("data"), list):
        return False
    rows = value["data"]
    return bool(rows) and all(
        isinstance(row, Mapping)
        and isinstance(row.get("name"), str)
        and bool(row.get("name"))
        and row.get("enabled") is False
        and type(row.get("configured")) is bool
        and isinstance(row.get("tools"), list)
        for row in rows
    )


def _skills_are_empty(value: object) -> bool:
    return isinstance(value, Mapping) and value == {"object": "list", "data": []}


def _reject(reason: str) -> HermesApiPreflight:
    return HermesApiPreflight(False, rejection_reason=reason)


__all__ = [
    "HERMES_ARTIFACT_PROFILE",
    "HERMES_EXPECTED_API_VERSION",
    "HermesApiPreflight",
    "hermes_tool_surface_is_closed",
    "strict_json_mapping",
    "verify_hermes_api_preflight",
]
