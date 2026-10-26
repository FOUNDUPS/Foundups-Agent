"""Canonical read-only profile selected by the ``start operations`` control."""

from __future__ import annotations

from dataclasses import dataclass

from modules.communication.moltbot_bridge.src.reddog_operations_skill import (
    LOGICAL_ROLES,
    SKILL_NAME,
)


PROFILE_SCHEMA = "reddog_start_operations_profile.v1"
PROFILE_ID = "reddog_readonly_architect_operations.v1"
DEFAULT_MAX_CLAIMS = 5
MAX_MAX_CLAIMS = 5
DEFAULT_TIMEOUT_SECONDS = 180
MAX_TIMEOUT_SECONDS = 600
SEMANTIC_READINESS_TARGET = (
    "RedDog resident operations current implementation and HoloIndex owner readiness"
)

READ_TARGETS = (
    "WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md",
    "WSP_framework/src/WSP_15_Module_Prioritization_Scoring_System.md",
    "WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md",
    "docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md",
    "docs/0102_session_briefings/work_ledger.schema.json",
    "modules/communication/moltbot_bridge/src/reddog_resident_architect_durable_agentdb_cycle.py",
    "modules/communication/moltbot_bridge/src/openclaw_supervisor.py",
    "modules/infrastructure/foundups_mcp_bridge/src/reddog_holoindex_maintenance_handshake.py",
)

WORK_FOCUS = "\n".join(
    (
        "Audit current RedDog operational truth before selecting any work.",
        "Operate under WSP_00, retrieve and verify under WSP_97, then apply WSP_15.",
        "Read first:",
        *(f"- {path}" for path in READ_TARGETS),
        f"Semantic target: {SEMANTIC_READINESS_TARGET}",
        "Determine the highest-priority bounded next task.",
        "This cycle is read-only and grants no source, shell, worktree, PR, merge, or reindex authority.",
    )
)


@dataclass(frozen=True)
class StartOperationsProfile:
    schema_version: str = PROFILE_SCHEMA
    profile_id: str = PROFILE_ID
    work_focus: str = WORK_FOCUS
    read_targets: tuple[str, ...] = READ_TARGETS
    audit_lanes: tuple[str, ...] = (
        "repo_code_audit",
        "external_research_audit",
        "runtime_freshness_audit",
        "skill_gap_audit",
        "security_governance_audit",
    )
    default_max_claims: int = DEFAULT_MAX_CLAIMS
    max_max_claims: int = MAX_MAX_CLAIMS
    default_timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_timeout_seconds: int = MAX_TIMEOUT_SECONDS
    read_only_authority_only: bool = True
    operations_skill_name: str = SKILL_NAME
    operations_logical_roles: tuple[str, ...] = LOGICAL_ROLES


def start_operations_profile(profile_id: str) -> StartOperationsProfile:
    if str(profile_id or "").strip() != PROFILE_ID:
        raise ValueError("start_operations_profile_invalid")
    return StartOperationsProfile()


__all__ = [
    "DEFAULT_MAX_CLAIMS",
    "DEFAULT_TIMEOUT_SECONDS",
    "MAX_MAX_CLAIMS",
    "MAX_TIMEOUT_SECONDS",
    "PROFILE_ID",
    "PROFILE_SCHEMA",
    "READ_TARGETS",
    "SEMANTIC_READINESS_TARGET",
    "StartOperationsProfile",
    "WORK_FOCUS",
    "start_operations_profile",
]
