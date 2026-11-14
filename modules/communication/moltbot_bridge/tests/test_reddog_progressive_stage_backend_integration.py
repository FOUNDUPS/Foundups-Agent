"""Focused backend integration tests for progressive execution stages."""

from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ACTION_FIX,
    InMemoryArchitectDeterminationStore,
    run_reddog_backend_architect_determination_runtime,
)
from modules.communication.moltbot_bridge.tests.test_reddog_backend_architect_determination_runtime import (
    NOW,
    FakeArchitectRunner,
    _build_inputs,
    _model_output,
    _runtime_kwargs,
)


def test_audit_stage_persists_fix_determination_without_queue_candidate() -> None:
    inputs = _build_inputs()
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    kwargs = _runtime_kwargs(inputs)
    kwargs["progressive_execution_stage_ceiling"] = "AUDIT_NO_EFFECT"

    result = run_reddog_backend_architect_determination_runtime(
        **kwargs,
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=FakeArchitectRunner(
            _model_output(inputs["allocation"], evidence_ref)
        ),
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.receipt.action == ACTION_FIX
    assert result.receipt.queue_candidate is None
    assert result.queue_candidate_count == 0
