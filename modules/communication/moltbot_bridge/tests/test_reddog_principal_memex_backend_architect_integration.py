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
    assert result.receipt.summary == (
        "Principal Memex informed an advisory determination; "
        "model-authored text was not persisted."
    )
    assert result.receipt.decision_reasons == ("principal_memex_advisory_only",)
    assert result.receipt.proposal_admission is None
    assert result.receipt.queue_candidate is None


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


def test_principal_memex_statement_cannot_escape_through_model_output(
    tmp_path: Path,
) -> None:
    inputs, prepared = _prepared_runtime(tmp_path / "output-noninterference")
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    output = _model_output(inputs["allocation"], evidence_ref)
    output["summary"] = "Audit carefully before any implementation."
    runner = FakeArchitectRunner(output)
    store = InMemoryArchitectDeterminationStore()

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs), wsp15_allocation_receipt=inputs["allocation"],
        store=store, model_runner=runner, now_iso=RUNTIME_NOW,
        principal_memex_context=prepared.context,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.PRINCIPAL_MEMEX_CONTEXT_INVALID in (
        result.rejection_reasons
    )
    assert store.records == []
    assert "Audit before implementation." not in json.dumps(result.receipt.to_dict())


def test_unicode_escaped_principal_memex_statement_is_rejected(
    tmp_path: Path,
) -> None:
    inputs, prepared = _prepared_runtime(tmp_path / "unicode-escape")
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    output = _model_output(inputs["allocation"], evidence_ref)
    output["summary"] = "Audit before implementation."
    serialized = json.dumps(output).replace("Audit", r"\u0041udit", 1)
    store = InMemoryArchitectDeterminationStore()

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs), wsp15_allocation_receipt=inputs["allocation"],
        store=store, model_runner=FakeArchitectRunner(serialized),
        now_iso=RUNTIME_NOW, principal_memex_context=prepared.context,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.PRINCIPAL_MEMEX_CONTEXT_INVALID in (
        result.rejection_reasons
    )
    assert store.records == []


def test_principal_memex_statement_split_across_output_fields_is_rejected(
    tmp_path: Path,
) -> None:
    inputs, prepared = _prepared_runtime(tmp_path / "split-fields")
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    output = _model_output(inputs["allocation"], evidence_ref)
    output["summary"] = "Audit"
    output["decision_reasons"] = ["before", "implementation"]
    store = InMemoryArchitectDeterminationStore()

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs), wsp15_allocation_receipt=inputs["allocation"],
        store=store, model_runner=FakeArchitectRunner(output),
        now_iso=RUNTIME_NOW, principal_memex_context=prepared.context,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.PRINCIPAL_MEMEX_CONTEXT_INVALID in (
        result.rejection_reasons
    )
    assert store.records == []


@pytest.mark.parametrize(
    "summary",
    (
        "Au\u200bdit before implementation.",
        "Au\u0301dit before implementation.",
        "\uff21udit before implementation.",
        "Au\tdit before implementation.",
    ),
)
def test_principal_memex_unicode_or_control_disguises_are_rejected(
    tmp_path: Path, summary: str,
) -> None:
    inputs, prepared = _prepared_runtime(tmp_path / "unicode-disguise")
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    output = _model_output(inputs["allocation"], evidence_ref)
    output["summary"] = summary
    store = InMemoryArchitectDeterminationStore()

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs), wsp15_allocation_receipt=inputs["allocation"],
        store=store, model_runner=FakeArchitectRunner(output),
        now_iso=RUNTIME_NOW, principal_memex_context=prepared.context,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.PRINCIPAL_MEMEX_CONTEXT_INVALID in (
        result.rejection_reasons
    )
    assert store.records == []


@pytest.mark.parametrize(
    "private_key",
    ("Audit before implementation.", "\uff21udit before implementation."),
)
def test_principal_memex_statement_in_output_key_is_rejected(
    tmp_path: Path, private_key: str,
) -> None:
    inputs, prepared = _prepared_runtime(tmp_path / "private-key")
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    output = _model_output(inputs["allocation"], evidence_ref)
    output[private_key] = "ignored"
    store = InMemoryArchitectDeterminationStore()

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs), wsp15_allocation_receipt=inputs["allocation"],
        store=store, model_runner=FakeArchitectRunner(output),
        now_iso=RUNTIME_NOW, principal_memex_context=prepared.context,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.PRINCIPAL_MEMEX_CONTEXT_INVALID in (
        result.rejection_reasons
    )
    assert store.records == []


def test_oversized_principal_memex_model_output_is_rejected(tmp_path: Path) -> None:
    inputs, prepared = _prepared_runtime(tmp_path / "oversized-output")
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    output = _model_output(inputs["allocation"], evidence_ref)
    output["summary"] = "x" * (
        context_projection.MAX_PRINCIPAL_MEMEX_MODEL_OUTPUT_CHARS + 1
    )
    store = InMemoryArchitectDeterminationStore()

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs), wsp15_allocation_receipt=inputs["allocation"],
        store=store, model_runner=FakeArchitectRunner(output),
        now_iso=RUNTIME_NOW, principal_memex_context=prepared.context,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.PRINCIPAL_MEMEX_CONTEXT_INVALID in (
        result.rejection_reasons
    )
    assert store.records == []


def test_principal_memex_paraphrase_is_never_persisted_or_queued(
    tmp_path: Path,
) -> None:
    inputs, prepared = _prepared_runtime(tmp_path / "paraphrase")
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    output = _model_output(inputs["allocation"], evidence_ref)
    output["summary"] = "Review each change prior to coding."
    output["decision_reasons"] = ["The principal prefers cautious delivery."]
    runner = FakeArchitectRunner(output)
    store = InMemoryArchitectDeterminationStore()

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs), wsp15_allocation_receipt=inputs["allocation"],
        store=store, model_runner=runner, now_iso=RUNTIME_NOW,
        principal_memex_context=prepared.context,
    )

    persisted = json.dumps([record.determination for record in store.records])
    assert result.accepted is True
    assert result.receipt.queue_candidate is None
    assert result.receipt.proposal_admission is None
    assert "Review each change" not in persisted
    assert "principal prefers" not in persisted
    assert result.receipt.decision_reasons == ("principal_memex_advisory_only",)


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
