"""Backend architect integration tests for authenticated Principal Memex context."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_digest import (
    canonical_model_runtime_binding_digest,
)
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ArchitectDeterminationReason,
    InMemoryArchitectDeterminationStore,
    run_reddog_backend_architect_determination_runtime,
)
from modules.communication.moltbot_bridge.src import (
    reddog_backend_architect_context_projection as context_projection,
)
from modules.communication.moltbot_bridge.src.reddog_principal_memex_resident_admission import (
    ADMISSION_ACCEPT,
    PrincipalMemexAdmissionResult,
    consume_authenticated_principal_memex_context,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    canonical_digest,
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


def _prepared_runtime(
    tmp_path: Path, *, expires_at: int | None = None, **disclosure_overrides,
):
    tmp_path.mkdir(parents=True, exist_ok=True)
    inputs = _build_inputs(now_iso=RUNTIME_NOW)
    runtime_binding = inputs["architect_runtime_binding"]
    if expires_at is not None:
        disclosure_overrides["expires_at"] = expires_at
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


def test_tampered_admitted_context_blocks_backend_model_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, prepared = _prepared_runtime(tmp_path / "tamper")
    admitted = consume_authenticated_principal_memex_context(
        prepared.context,
        model_runtime_binding_receipt_id=str(inputs["architect_runtime_binding"]["receipt_id"]),
        model_runtime_binding_digest=canonical_model_runtime_binding_digest(
            inputs["architect_runtime_binding"]
        ),
        now_epoch=1_800_000_001,
    )
    context_view = dict(admitted.context_view)
    context_view["items"] = [dict(item) for item in context_view["items"]]
    context_view["items"][0]["statement"] = "FORGED_AFTER_ADMISSION"
    forged = PrincipalMemexAdmissionResult(
        True, ADMISSION_ACCEPT, admission_receipt=admitted.admission_receipt,
        context_view=context_view,
    )
    monkeypatch.setattr(
        context_projection, "consume_authenticated_principal_memex_context",
        lambda *args, **kwargs: forged,
    )
    runner = FakeArchitectRunner({})

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs), wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(), model_runner=runner,
        now_iso=RUNTIME_NOW, principal_memex_context=object(),
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.PRINCIPAL_MEMEX_CONTEXT_INVALID in result.rejection_reasons
    assert runner.calls == []


def test_fresh_admissions_for_same_cognition_share_duplicate_cycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, prepared = _prepared_runtime(tmp_path / "stable-cycle")
    binding = inputs["architect_runtime_binding"]
    admitted = consume_authenticated_principal_memex_context(
        prepared.context, model_runtime_binding_receipt_id=str(binding["receipt_id"]),
        model_runtime_binding_digest=canonical_model_runtime_binding_digest(binding),
        now_epoch=1_800_000_001,
    )
    first_receipt = dict(admitted.admission_receipt)
    first_context = dict(admitted.context_view)
    second_receipt = dict(first_receipt)
    second_receipt["disclosure_id"] = "sha256:" + "9" * 64
    second_receipt["admitted_at"] = int(first_receipt["admitted_at"]) + 1
    second_payload = {
        key: value for key, value in second_receipt.items() if key != "receipt_id"
    }
    second_receipt["receipt_id"] = canonical_digest(second_payload)
    second_context = dict(first_context)
    second_context["admission_receipt_id"] = second_receipt["receipt_id"]
    admissions = iter((
        PrincipalMemexAdmissionResult(
            True, ADMISSION_ACCEPT, admission_receipt=first_receipt,
            context_view=first_context,
        ),
        PrincipalMemexAdmissionResult(
            True, ADMISSION_ACCEPT, admission_receipt=second_receipt,
            context_view=second_context,
        ),
    ))
    monkeypatch.setattr(
        context_projection, "consume_authenticated_principal_memex_context",
        lambda *args, **kwargs: next(admissions),
    )
    store = InMemoryArchitectDeterminationStore()
    first_evidence = inputs["reports"][0]["evidence_refs"][0]
    first_runner = FakeArchitectRunner(
        _model_output(inputs["allocation"], first_evidence)
    )
    first_result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs), wsp15_allocation_receipt=inputs["allocation"],
        store=store, model_runner=first_runner, now_iso=RUNTIME_NOW,
        principal_memex_context=object(),
    )
    second_runner = FakeArchitectRunner({})
    second_result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs), wsp15_allocation_receipt=inputs["allocation"],
        store=store, model_runner=second_runner, now_iso=RUNTIME_NOW,
        principal_memex_context=object(),
    )

    assert first_result.accepted is True
    assert second_result.accepted is False
    assert ArchitectDeterminationReason.DUPLICATE_CYCLE in second_result.rejection_reasons
    assert second_runner.calls == []
