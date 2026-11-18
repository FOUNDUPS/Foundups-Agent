"""Resident-runtime clamp for untrusted editor stage requests."""

from modules.communication.moltbot_bridge.src import (
    reddog_resident_architect_durable_agentdb_cycle as resident_cycle,
)


def test_editor_bounded_stage_request_is_clamped_to_runtime_audit() -> None:
    intent = {"progressive_execution_stage_ceiling": "boundedExecution"}

    assert resident_cycle._intent_stage_ceiling(intent) == "BOUNDED_EXECUTION"
    assert resident_cycle._runtime_stage_ceiling(intent) == "AUDIT_NO_EFFECT"
