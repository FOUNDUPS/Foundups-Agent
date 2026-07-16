"""Resident RedDog queue binding profile helpers.

Slice: REDDOG_RESIDENT_QUEUE_BINDING_PROFILE_PHASE1

The profile defaults only derivation/request-binding controls. It does not
enable model execution, shell execution, worktree runners, draft PR publishing,
PatternMemory writes, reward settlement, or HoloIndex re-indexing.
"""

from __future__ import annotations

from typing import Mapping


ENV_REDDOG_RESIDENT_QUEUE_BINDING_PROFILE = "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE"
PROFILE_SIGNED_0102_BOUNDED_CODE = "signed_0102_bounded_code"

PROFILE_BINDING_FLAGS = frozenset(
    {
        "REDDOG_PILOT_DRYRUN_BINDING",
        "REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING",
        "REDDOG_SLICE_VERIFIER_REQUEST_BINDING",
        "REDDOG_DRAFT_PR_PUBLISH_REQUEST_BINDING",
        "REDDOG_OUTCOME_RATCHET_REQUEST_BINDING",
        "REDDOG_HELD_OUT_GATE_REQUEST_BINDING",
        "REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_BINDING",
    }
)

PROFILE_RUNTIME_FLAGS = frozenset(
    {
        "OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED",
        "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP",
        "REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER",
    }
)


def resident_queue_binding_profile(env: Mapping[str, str]) -> str:
    """Return the normalized resident queue binding profile."""

    value = str(env.get(ENV_REDDOG_RESIDENT_QUEUE_BINDING_PROFILE) or "").strip().lower()
    return value if value == PROFILE_SIGNED_0102_BOUNDED_CODE else ""


def resident_queue_binding_enabled(env: Mapping[str, str], env_name: str) -> bool:
    """Return whether a derivation binding flag is enabled.

    Explicit environment values win. The profile only enables the known binding
    flags and only when the flag is absent.
    """

    raw = str(env.get(env_name) or "").strip()
    if raw:
        return raw == "1"
    return (
        env_name in PROFILE_BINDING_FLAGS
        and resident_queue_binding_profile(env) == PROFILE_SIGNED_0102_BOUNDED_CODE
    )


def resident_queue_runtime_flag_enabled(env: Mapping[str, str], env_name: str) -> bool:
    """Return whether a safe resident runtime control-plane flag is enabled.

    Explicit environment values win. The profile only enables known
    control-plane flags that start existing gated loops; it never enables
    model, shell, worktree, draft-PR, PatternMemory, HoloIndex, merge, or
    reward-settlement effect modes.
    """

    raw = str(env.get(env_name) or "").strip()
    if raw:
        return raw == "1"
    return (
        env_name in PROFILE_RUNTIME_FLAGS
        and resident_queue_binding_profile(env) == PROFILE_SIGNED_0102_BOUNDED_CODE
    )


def resident_queue_materializer_mode(env: Mapping[str, str]) -> str:
    """Return explicit/default work-order materializer mode for the profile."""

    raw = str(env.get("REDDOG_WORK_ORDER_MATERIALIZER_MODE") or "").strip()
    if raw:
        return raw
    if resident_queue_binding_profile(env) == PROFILE_SIGNED_0102_BOUNDED_CODE:
        return "authority_profile"
    return ""


__all__ = [
    "ENV_REDDOG_RESIDENT_QUEUE_BINDING_PROFILE",
    "PROFILE_BINDING_FLAGS",
    "PROFILE_RUNTIME_FLAGS",
    "PROFILE_SIGNED_0102_BOUNDED_CODE",
    "resident_queue_binding_enabled",
    "resident_queue_binding_profile",
    "resident_queue_materializer_mode",
    "resident_queue_runtime_flag_enabled",
]
