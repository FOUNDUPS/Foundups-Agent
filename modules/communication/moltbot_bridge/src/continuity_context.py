#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gateway Continuity Context - Cross-Surface Session Identity.

Provides a unified continuity model across:
- CLI / terminal invocations
- Resident OpenClaw / webhook runtime
- Messaging/social surfaces

WSP Compliance:
- WSP 60: Memory Architecture (shared context across surfaces)
- WSP 91: Observability (continuity metadata in breadcrumbs)
- WSP 97: Autonomy Boundaries (FoundUps-controlled identity)

Architecture:
- ContinuityContext is the shared envelope for cross-surface tracking
- RuntimeSurface enum normalizes surface types
- Continuity ID is stable within a logical work session
- Breadcrumbs record surface + continuity metadata for coherent recall
"""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class RuntimeSurface(str, Enum):
    """Normalized runtime surface types under FoundUps control."""

    CLI = "cli"  # Terminal invocations, scripts
    OPENCLAW = "openclaw"  # Resident webhook/DAE runtime
    MESSAGING = "messaging"  # WhatsApp, Telegram, Discord via MoltBot
    SOCIAL = "social"  # LinkedIn, X adapters
    SUPERVISOR = "supervisor"  # OpenClawSupervisor cycles
    IDLE = "idle"  # IdleAutomationDAE background work
    WRE = "wre"  # WRE skill execution
    INTERNAL = "internal"  # Internal cross-module calls
    UNKNOWN = "unknown"


def _utc_now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(UTC).isoformat()


def _generate_continuity_id() -> str:
    """Generate a unique continuity ID (12-char hex)."""
    return uuid.uuid4().hex[:12]


def _derive_session_signature(
    sender: str, channel: str, surface: RuntimeSurface
) -> str:
    """Derive a session signature for deduplication."""
    raw = f"{sender}:{channel}:{surface.value}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _derive_continuity_from_session(session_key: str) -> str:
    """
    Derive a stable continuity ID from session_key.

    Same session_key always produces the same continuity_id,
    ensuring stability within a logical session.
    """
    raw = f"session:{session_key}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


@dataclass
class ContinuityContext:
    """
    Shared context envelope for cross-surface continuity.

    Carries enough metadata to:
    - Identify the runtime surface (CLI, OpenClaw, messaging, etc.)
    - Track a stable continuity_id across surface transitions
    - Normalize sender/channel for consistent breadcrumb recording
    - Link related work items via parent_continuity_id
    """

    # Core identity
    continuity_id: str = field(default_factory=_generate_continuity_id)
    surface: RuntimeSurface = RuntimeSurface.UNKNOWN
    session_id: str = ""  # Per-surface session (e.g., session_key from OpenClaw)

    # Sender/channel normalization
    sender: str = ""
    channel: str = ""
    sender_normalized: str = ""  # Canonical sender identity

    # Lineage tracking
    parent_continuity_id: Optional[str] = None  # For chained work items
    related_continuity_ids: List[str] = field(default_factory=list)

    # Timestamps
    created_at: str = field(default_factory=_utc_now_iso)
    last_activity_at: str = field(default_factory=_utc_now_iso)

    # Surface-specific metadata
    surface_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize sender identity if not provided."""
        if not self.sender_normalized:
            self.sender_normalized = self._normalize_sender(self.sender)

    @staticmethod
    def _normalize_sender(sender: str) -> str:
        """
        Normalize sender identity to canonical form.

        Strips platform prefixes, normalizes case, handles common variations.
        """
        if not sender:
            return "anonymous"

        normalized = sender.lower().strip()

        # Strip common platform prefixes
        prefixes = ["wa:", "tg:", "discord:", "slack:", "x:", "linkedin:"]
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :]
                break

        # Strip phone number formatting
        if normalized.startswith("+"):
            normalized = normalized.replace(" ", "").replace("-", "")

        return normalized or "anonymous"

    def touch(self) -> None:
        """Update last_activity_at timestamp."""
        self.last_activity_at = _utc_now_iso()

    def fork(
        self,
        new_surface: Optional[RuntimeSurface] = None,
        new_session_id: Optional[str] = None,
    ) -> "ContinuityContext":
        """
        Fork a new continuity context for a related work item.

        The new context has a fresh continuity_id but links back to this one
        via parent_continuity_id for lineage tracking.
        """
        return ContinuityContext(
            continuity_id=_generate_continuity_id(),
            surface=new_surface or self.surface,
            session_id=new_session_id or self.session_id,
            sender=self.sender,
            channel=self.channel,
            sender_normalized=self.sender_normalized,
            parent_continuity_id=self.continuity_id,
            related_continuity_ids=[],
            surface_metadata={},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["surface"] = self.surface.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContinuityContext":
        """Create from dictionary."""
        data = dict(data)  # Copy to avoid mutation
        if "surface" in data:
            data["surface"] = RuntimeSurface(data["surface"])
        return cls(**data)

    def to_breadcrumb_metadata(self) -> Dict[str, Any]:
        """
        Extract metadata suitable for breadcrumb recording.

        Returns a compact dict with the essential continuity fields
        for inclusion in AgentDB breadcrumbs.
        """
        return {
            "continuity_id": self.continuity_id,
            "surface": self.surface.value,
            "sender_normalized": self.sender_normalized,
            "parent_continuity_id": self.parent_continuity_id,
        }


class ContinuityManager:
    """
    Manages continuity context creation and propagation.

    Provides factory methods for creating contexts from various entry points
    and helper methods for context propagation across surfaces.
    """

    # Environment variable for continuity ID propagation
    ENV_CONTINUITY_ID = "OPENCLAW_CONTINUITY_ID"
    ENV_PARENT_CONTINUITY_ID = "OPENCLAW_PARENT_CONTINUITY_ID"

    @classmethod
    def from_openclaw(
        cls,
        sender: str,
        channel: str,
        session_key: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContinuityContext:
        """
        Create context from OpenClaw process() entry point.

        Continuity ID resolution order:
        1. Explicit metadata["continuity_id"] (e.g., from webhook payload)
        2. Environment variable OPENCLAW_CONTINUITY_ID (subprocess propagation)
        3. Derived from session_key (stable per logical session)
        """
        metadata = metadata or {}

        # 1. Check metadata first (explicit propagation)
        continuity_id = metadata.get("continuity_id")

        # 2. Check environment (subprocess propagation)
        if not continuity_id:
            continuity_id = os.getenv(cls.ENV_CONTINUITY_ID)

        # 3. Derive from session_key for stable session identity
        if not continuity_id:
            # Same session_key always produces same continuity_id
            continuity_id = _derive_continuity_from_session(session_key)

        # Parent ID: metadata first, then env
        parent_id = metadata.get("parent_continuity_id") or os.getenv(cls.ENV_PARENT_CONTINUITY_ID) or None

        return ContinuityContext(
            continuity_id=continuity_id,
            surface=RuntimeSurface.OPENCLAW,
            session_id=session_key,
            sender=sender,
            channel=channel,
            parent_continuity_id=parent_id,
            surface_metadata={
                "entry_point": "openclaw_dae.process",
                "channel_raw": channel,
            },
        )

    @classmethod
    def from_cli(
        cls,
        command: str = "",
        script_name: str = "",
    ) -> ContinuityContext:
        """Create context from CLI/script invocation."""
        # Check environment for propagated continuity
        continuity_id = os.getenv(cls.ENV_CONTINUITY_ID) or _generate_continuity_id()
        parent_id = os.getenv(cls.ENV_PARENT_CONTINUITY_ID)

        return ContinuityContext(
            continuity_id=continuity_id,
            surface=RuntimeSurface.CLI,
            session_id=f"cli_{os.getpid()}",
            sender="cli",
            channel="terminal",
            parent_continuity_id=parent_id,
            surface_metadata={
                "entry_point": "cli",
                "command": command[:200] if command else "",
                "script": script_name,
                "pid": os.getpid(),
            },
        )

    @classmethod
    def from_supervisor(
        cls,
        cycle_id: str = "",
        state: str = "",
        parent_context: Optional[ContinuityContext] = None,
    ) -> ContinuityContext:
        """Create context from OpenClawSupervisor cycle.

        If parent_context is provided (e.g., from an OpenClaw request that triggered
        the supervisor), the new context will be forked with parent lineage.
        """
        metadata = {
            "entry_point": "openclaw_supervisor",
            "cycle_id": cycle_id,
            "state": state,
        }

        if parent_context:
            ctx = parent_context.fork(new_surface=RuntimeSurface.SUPERVISOR)
            ctx.session_id = f"supervisor_{cycle_id}" if cycle_id else "supervisor"
            ctx.sender = "supervisor"
            ctx.channel = "internal"
            ctx.surface_metadata = metadata
            return ctx

        return ContinuityContext(
            continuity_id=_generate_continuity_id(),
            surface=RuntimeSurface.SUPERVISOR,
            session_id=f"supervisor_{cycle_id}" if cycle_id else "supervisor",
            sender="supervisor",
            channel="internal",
            surface_metadata=metadata,
        )

    @classmethod
    def from_idle(
        cls,
        task_type: str = "",
        parent_context: Optional[ContinuityContext] = None,
    ) -> ContinuityContext:
        """Create context from IdleAutomationDAE.

        If parent_context is provided (e.g., from a YouTube DAE that triggered
        idle automation), the new context will be forked with parent lineage.
        """
        metadata = {
            "entry_point": "idle_automation_dae",
            "task_type": task_type,
        }

        if parent_context:
            ctx = parent_context.fork(new_surface=RuntimeSurface.IDLE)
            ctx.session_id = "idle_automation"
            ctx.sender = "idle_dae"
            ctx.channel = "internal"
            ctx.surface_metadata = metadata
            return ctx

        return ContinuityContext(
            continuity_id=_generate_continuity_id(),
            surface=RuntimeSurface.IDLE,
            session_id="idle_automation",
            sender="idle_dae",
            channel="internal",
            surface_metadata=metadata,
        )

    @classmethod
    def from_wre(
        cls,
        skill_name: str = "",
        agent: str = "",
        parent_context: Optional[ContinuityContext] = None,
    ) -> ContinuityContext:
        """Create context from WRE skill execution."""
        if parent_context:
            ctx = parent_context.fork(new_surface=RuntimeSurface.WRE)
            ctx.surface_metadata = {
                "entry_point": "wre_skill",
                "skill_name": skill_name,
                "agent": agent,
            }
            return ctx

        return ContinuityContext(
            continuity_id=_generate_continuity_id(),
            surface=RuntimeSurface.WRE,
            session_id=f"wre_{skill_name}" if skill_name else "wre",
            sender="wre",
            channel="internal",
            surface_metadata={
                "entry_point": "wre_skill",
                "skill_name": skill_name,
                "agent": agent,
            },
        )

    @classmethod
    def from_messaging(
        cls,
        platform: str,
        sender: str,
        channel: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContinuityContext:
        """Create context from messaging platform (WhatsApp, Telegram, etc.)."""
        metadata = metadata or {}

        return ContinuityContext(
            continuity_id=metadata.get("continuity_id") or _generate_continuity_id(),
            surface=RuntimeSurface.MESSAGING,
            session_id=f"{platform}_{_derive_session_signature(sender, channel, RuntimeSurface.MESSAGING)}",
            sender=sender,
            channel=channel,
            parent_continuity_id=metadata.get("parent_continuity_id"),
            surface_metadata={
                "entry_point": "messaging",
                "platform": platform,
            },
        )

    @classmethod
    def propagate_to_env(cls, context: ContinuityContext) -> Dict[str, str]:
        """
        Return environment variables to propagate continuity to subprocesses.

        Usage:
            env_vars = ContinuityManager.propagate_to_env(context)
            subprocess.run(cmd, env={**os.environ, **env_vars})
        """
        return {
            cls.ENV_CONTINUITY_ID: context.continuity_id,
            cls.ENV_PARENT_CONTINUITY_ID: context.parent_continuity_id or "",
        }
