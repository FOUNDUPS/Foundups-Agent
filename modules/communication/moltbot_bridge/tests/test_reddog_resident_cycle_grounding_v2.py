"""Resident-cycle admission regressions for exact-HEAD grounding v2."""

from __future__ import annotations

import pytest

from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle import (
    run_reddog_resident_architect_durable_agentdb_cycle,
)
from modules.communication.moltbot_bridge.tests.test_reddog_resident_architect_durable_agentdb_cycle import (
    _AuditModelRunner,
    _intent,
    _runtime_kwargs,
)


@pytest.mark.parametrize("field", ["repo_state_head_sha", "repo_state_root_digest"])
def test_cycle_rejects_rehashed_grounding_repository_state_substitution(field: str) -> None:
    intent = _intent()
    receipt = dict(intent["grounding_receipt"])
    receipt[field] = ("a" * 40) if field.endswith("head_sha") else ("sha256:" + "a" * 64)
    receipt["receipt_id"] = canonical_digest(
        {key: value for key, value in receipt.items() if key != "receipt_id"}
    )
    intent["grounding_receipt"] = receipt
    runner = _AuditModelRunner()

    result = run_reddog_resident_architect_durable_agentdb_cycle(
        **_runtime_kwargs(red_dog_intent=intent, audit_model_runner=runner)
    )

    assert result.accepted is False
    assert runner.calls == []
