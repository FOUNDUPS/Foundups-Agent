"""Exact-session confinement validation for the OpenClaw artifact agent."""
from __future__ import annotations
from typing import Mapping


def openclaw_artifact_session_is_confined(
    value: Mapping[str, object], *, agent_id: str, session_key: str
) -> bool:
    sandbox, elevated = value.get("sandbox"), value.get("elevated")
    if value.get("agentId") != agent_id or value.get("sessionKey") != session_key:
        return False
    if not isinstance(sandbox, Mapping) or not isinstance(elevated, Mapping):
        return False
    tools, mounts = sandbox.get("tools"), sandbox.get("workspaceMounts")
    return (
        sandbox.get("mode") == "all"
        and sandbox.get("sessionIsSandboxed") is True
        and sandbox.get("workspaceAccess") == "none"
        and sandbox.get("workspaceSource") == "sandbox"
        and sandbox.get("runtimeWorkdir") == "/workspace"
        and isinstance(tools, Mapping)
        and tools.get("allow") == []
        and isinstance(tools.get("deny"), list)
        and "*" in tools["deny"]
        and _safe_workspace_mounts(mounts, agent_id)
        and elevated.get("enabled") is False
    )


def _safe_workspace_mounts(value: object, agent_id: str) -> bool:
    if not isinstance(value, list) or len(value) != 1:
        return False
    mount = value[0]
    prefix = f"/home/user/.openclaw/sandboxes/agent-{agent_id}-"
    return (
        isinstance(mount, Mapping)
        and set(mount) == {"hostRoot", "containerRoot", "writable", "source"}
        and str(mount.get("hostRoot") or "").startswith(prefix)
        and mount.get("containerRoot") == "/workspace"
        and mount.get("writable") is False
        and mount.get("source") == "workspace"
    )


__all__ = ["openclaw_artifact_session_is_confined"]
