"""Backend architect integration tests for authenticated Principal Memex context."""

from __future__ import annotations

import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_digest import (
    canonical_model_runtime_binding_digest,
)
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ArchitectDeterminationReason,
    InMemoryArchitectDeterminationStore,
    run_reddog_backend_architect_determination_runtime,
)
from modules.communication.moltbot_bridge.tests.architect_proposal_test_helpers import (
    architect_model_output as _model_output,
    runtime_kwargs as _runtime_kwargs,
)
from modules.communication.moltbot_bridge.tests.test_reddog_backend_architect_determination_runtime import (
    FakeArchitectRunner,
    _build_inputs,
)
from modules.communication.moltbot_bridge.tests.test_reddog_principal_memex_resident_admission import (
    _prepared as _prepared_principal_memex,
)


RUNTIME_NOW = "2027-01-15T08:00:01+00:00"


def _prepared_runtime(tmp_path: Path, *, expires_at: int | None = None):
    inputs = _build_inputs(now_iso=RUNTIME_NOW)
    runtime_binding = inputs["architect_runtime_binding"]
    disclosure_overrides = {"expires_at": expires_at} if expires_at is not None else {}
    prepared, _ = _prepared_principal_memex(
        tmp_path / "principal-memex-runtime.sqlite",
        model_receipt=str(runtime_binding["receipt_id"]),
        model_digest=canonical_model_runtime_binding_digest(runtime_binding),
        **disclosure_overrides,
    )
    assert prepared.accepted is True
    return inputs, prepared


def test_backend_architect_model_receives_only_authenticated_principal_memex(
    tmp_path: Path,
) -> None:
    inputs, prepared = _prepared_runtime(tmp_path)
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    runner = FakeArchitectRunner(_model_output(inputs["allocation"], evidence_ref))

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs), wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(), model_runner=runner,
        now_iso=RUNTIME_NOW, principal_memex_context=prepared.context,
    )

    assert result.accepted is True
    assert len(runner.calls) == 1
    context_payload = json.loads(runner.calls[0]["context"])
    memex = context_payload["principal_memex_context"]
    encoded = json.dumps(memex, sort_keys=True)
    assert memex["source_class"] == "principal_memex"
    assert memex["authority_effect"] == "none"
    assert "Audit before implementation." in encoded
    assert "Skip verification." not in encoded
    assert "Which FoundUp" not in encoded
    assert "objective canary" not in encoded
    assert runner.calls[0]["binding"]["principal_memex_admission_receipt_id"]


def test_expired_principal_memex_blocks_backend_model_call(tmp_path: Path) -> None:
    inputs, prepared = _prepared_runtime(tmp_path, expires_at=1_800_000_001)
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    runner = FakeArchitectRunner(_model_output(inputs["allocation"], evidence_ref))

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs), wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(), model_runner=runner,
        now_iso=RUNTIME_NOW, principal_memex_context=prepared.context,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.PRINCIPAL_MEMEX_CONTEXT_INVALID in (
        result.rejection_reasons
    )
    assert runner.calls == []
