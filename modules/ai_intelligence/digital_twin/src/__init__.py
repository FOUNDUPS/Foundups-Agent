# -*- coding: utf-8 -*-
"""
Digital Twin Module - 012's Autonomous Comment Engagement System

WSP Compliance:
    WSP 49: Module Structure
    WSP 77: Agent Coordination
    WSP 91: DAE Observability
"""

from .trajectory_logger import (
    TrajectoryLogger,
    DraftLog,
    DecisionLog,
    ActionLog,
)
from .schemas import (
    CommentAction,
    CommentDecision,
    CommentDraft,
    Platform,
    StyleViolation,
    ToolPlan,
    ToolStep,
    TrajectoryEvent,
    VoiceMemoryResult,
)
from .voice_memory import VoiceMemory
from .decision_policy import DecisionPolicy
from .comment_drafter import CommentDrafter, LocalLLM
from .style_guardrails import StyleGuardrails, get_nemo_guardrails
from .twin_boot import boot_digital_twin, DigitalTwinBoot, ActivatedTwin

__all__ = [
    # Trajectory logging
    "TrajectoryLogger",
    "DraftLog",
    "DecisionLog",
    "ActionLog",
    # Schemas
    "CommentAction",
    "CommentDecision",
    "CommentDraft",
    "Platform",
    "StyleViolation",
    "ToolPlan",
    "ToolStep",
    "TrajectoryEvent",
    "VoiceMemoryResult",
    # Core components
    "VoiceMemory",
    "DecisionPolicy",
    "CommentDrafter",
    "LocalLLM",
    "StyleGuardrails",
    "get_nemo_guardrails",
    # WSP_00 Boot (v0.5.0)
    "boot_digital_twin",
    "DigitalTwinBoot",
    "ActivatedTwin",
]

__version__ = "0.5.0"
