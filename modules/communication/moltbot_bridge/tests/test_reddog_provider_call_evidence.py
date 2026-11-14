from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_provider_call_evidence import (
    AtomicJsonProviderCallEvidenceStore,
    InMemoryProviderCallEvidenceStore,
    ProviderCallOutcome,
    ProviderCallReason,
    arm_provider_call,
    create_precall_evidence,
    execute_evidenced_provider_call,
    terminalize_provider_call,
    validate_provider_call_evidence,
)
from modules.communication.moltbot_bridge.src import (
    reddog_backend_architect_determination_runtime as architect_runtime,
    reddog_readonly_0102_audit_worker_runtime as audit_runtime,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_runtime_binding_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_fusion_progress_receipt import (
    FusionProgressRecorder,
    validate_fusion_progress_receipt,
)

DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64


def _precall(
    *,
    started_at_ms: int = 100,
    requested_provider: str = "openrouter",
    requested_model: str = "test/model",
):
    return create_precall_evidence(
        surface="governed_repo_audit",
        task_id="task-1",
        work_order_id="work-1",
        queue_item_id="queue-1",
        run_id="run-1",
        cycle_id=None,
        requested_provider=requested_provider,
        requested_model=requested_model,
        redacted_input_digest=DIGEST_A,
        model_runtime_binding_receipt_id="binding-1",
        model_runtime_binding_digest=DIGEST_B,
        request_metadata={"timeout_seconds": 30, "max_tokens": 100},
        started_at_ms=started_at_ms,
    )


def _metadata():
    return {
        "served_provider": "synthetic-provider",
        "served_model": "synthetic/model",
        "usage": {"input_tokens": 3, "output_tokens": 5, "total_tokens": 8},
    }


@pytest.mark.parametrize(
    ("field", "identity"),
    [
        ("requested_provider", "sk-" + "a" * 24),
        ("requested_provider", "https://openrouter.ai"),
        ("requested_provider", "raw provider sentence"),
        ("requested_provider", "Ab3Cd5Ef7Gh9Jk2Lm4Np6Qr8St"),
        ("requested_model", "sk-" + "b" * 24),
        ("requested_model", "vendor/raw model sentence"),
        ("requested_model", "../vendor/model"),
        ("requested_model", "vendor/Ab3Cd5Ef7Gh9Jk2Lm4Np6Qr8St"),
    ],
)
def test_requested_identity_rejects_secret_and_raw_shapes_at_creation_and_validation(
    field: str,
    identity: str,
) -> None:
    kwargs = {field: identity}
    with pytest.raises(ValueError, match=field):
        _precall(**kwargs)

    payload = _precall().to_dict()
    payload[field] = identity
    with pytest.raises(ValueError, match=field):
        validate_provider_call_evidence(payload)


@pytest.mark.parametrize(
    "identity",
    [
        "s" "k-" + "a" * 24,
        "github" "_pat_" + "b" * 24,
        "Bearer " + "c" * 24,
        "https://provider.example",
        "C:/provider",
        "../provider",
        "provider/..",
        "provider?region=us",
        "provider#fragment",
        "Ab3Cd5Ef7Gh9Jk2Lm4Np6Qr8St",
        "Ab3Cd5Ef7Gh9Jk2Lm4Np6Qr8St-route",
        "model output sentence",
        "model\noutput",
        '{"model":"raw-content"}',
    ],
)
def test_served_identity_rejects_secret_and_raw_content_shapes(identity: str) -> None:
    metadata = _metadata()
    metadata["served_provider"] = identity

    with pytest.raises(ValueError, match="served_provider"):
        terminalize_provider_call(
            arm_provider_call(_precall()),
            outcome=ProviderCallOutcome.COMPLETED,
            reason=ProviderCallReason.PROVIDER_RETURNED,
            completed_at_ms=101,
            served_metadata=metadata,
        )


@pytest.mark.parametrize(
    "model",
    [
        "https://example/model",
        "C:/model",
        "../model",
        "vendor/../model",
        "vendor/.",
        "vendor/model?route=fast",
        "vendor/model#fragment",
        "Bearer " + "d" * 24,
        "raw model sentence",
        "vendor/Ab3Cd5Ef7Gh9Jk2Lm4Np6Qr8St",
        "vendor/Ab3Cd5Ef7Gh9Jk2Lm4Np6Qr8St:online",
    ],
)
def test_served_model_rejects_noncanonical_and_high_entropy_shapes(
    model: str,
) -> None:
    metadata = _metadata()
    metadata["served_model"] = model

    with pytest.raises(ValueError, match="served_model"):
        terminalize_provider_call(
            arm_provider_call(_precall()),
            outcome=ProviderCallOutcome.COMPLETED,
            reason=ProviderCallReason.PROVIDER_RETURNED,
            completed_at_ms=101,
            served_metadata=metadata,
        )


@pytest.mark.parametrize(
    ("provider", "model"),
    [
        ("openrouter", "moonshotai/kimi-k3"),
        ("openai", "openai/gpt-5.2-chat:online"),
        ("synthetic-provider", "vendor/model_name-v1.2+fast"),
    ],
)
def test_served_identity_accepts_canonical_provider_model_ids(
    provider: str, model: str
) -> None:
    metadata = _metadata()
    metadata["served_provider"] = provider
    metadata["served_model"] = model

    terminal = terminalize_provider_call(
        arm_provider_call(_precall()),
        outcome=ProviderCallOutcome.COMPLETED,
        reason=ProviderCallReason.PROVIDER_RETURNED,
        completed_at_ms=101,
        served_metadata=metadata,
    )

    assert terminal.served_provider == provider
    assert terminal.served_model == model
    assert validate_provider_call_evidence(terminal) == terminal


def test_contract_is_content_free_and_exact() -> None:
    terminal = terminalize_provider_call(
        arm_provider_call(_precall()),
        outcome=ProviderCallOutcome.COMPLETED,
        reason=ProviderCallReason.PROVIDER_RETURNED,
        completed_at_ms=101,
        content="secret response body",
        served_metadata=_metadata(),
    )
    payload = terminal.to_dict()

    assert "secret response body" not in json.dumps(payload)
    assert payload["response_byte_count"] == len("secret response body".encode())
    assert payload["served_provider"] == "synthetic-provider"
    assert validate_provider_call_evidence(payload) == terminal


@pytest.mark.parametrize(
    "smuggled", ["content", "headers", "error", "api_key", "prompt"]
)
def test_validator_rejects_content_smuggling(smuggled: str) -> None:
    payload = _precall().to_dict()
    payload[smuggled] = "must-not-persist"

    with pytest.raises(ValueError, match="receipt_schema"):
        validate_provider_call_evidence(payload)


def test_validator_rejects_tampering_and_incomplete_served_identity() -> None:
    payload = _precall().to_dict()
    payload["task_id"] = "different"
    with pytest.raises(ValueError, match="call_id_mismatch"):
        validate_provider_call_evidence(payload)

    terminal = terminalize_provider_call(
        arm_provider_call(_precall()),
        outcome=ProviderCallOutcome.COMPLETED,
        reason=ProviderCallReason.PROVIDER_RETURNED,
        completed_at_ms=101,
        served_metadata=_metadata(),
    ).to_dict()
    terminal["served_model"] = None
    with pytest.raises(ValueError, match="served_identity_incomplete"):
        validate_provider_call_evidence(terminal)


def test_ids_are_stable_per_call_and_change_per_state() -> None:
    precall = _precall()
    replay = _precall()
    armed = arm_provider_call(precall)
    terminal = terminalize_provider_call(
        armed,
        outcome=ProviderCallOutcome.COMPLETED,
        reason=ProviderCallReason.PROVIDER_RETURNED,
        completed_at_ms=101,
    )

    assert replay == precall
    assert len({precall.receipt_id, armed.receipt_id, terminal.receipt_id}) == 3
    assert {precall.call_id, armed.call_id, terminal.call_id} == {precall.call_id}


def test_store_accepts_exact_replay_and_rejects_divergence() -> None:
    store = InMemoryProviderCallEvidenceStore()
    precall = _precall()
    assert store.start(precall) == precall
    assert store.start(precall) == precall

    with pytest.raises(RuntimeError, match="divergent_replay"):
        store.start(_precall(started_at_ms=101))


def test_completed_call_accepts_exact_receipt_replay_but_cannot_retry() -> None:
    store = InMemoryProviderCallEvidenceStore()
    precall = _precall()
    armed = arm_provider_call(precall)
    terminal = terminalize_provider_call(
        armed,
        outcome=ProviderCallOutcome.COMPLETED,
        reason=ProviderCallReason.PROVIDER_RETURNED,
        completed_at_ms=101,
    )
    store.start(precall)
    store.transition(armed)
    store.transition(terminal)

    assert store.start(precall) == precall
    with pytest.raises(RuntimeError, match="invalid_transition"):
        store.transition(armed)


def test_atomic_store_keeps_validated_transition_history(tmp_path: Path) -> None:
    path = tmp_path / "provider_calls.json"
    store = AtomicJsonProviderCallEvidenceStore(path, allowed_root=tmp_path)
    precall = _precall()
    armed = arm_provider_call(precall)
    terminal = terminalize_provider_call(
        armed,
        outcome=ProviderCallOutcome.FAILED,
        reason=ProviderCallReason.PROVIDER_FAILED,
        completed_at_ms=105,
    )

    store.start(precall)
    store.transition(armed)
    store.transition(terminal)
    raw = json.loads(path.read_text(encoding="utf-8"))

    assert store.load(precall.call_id) == terminal
    assert len(raw["receipts"]) == 3
    assert not list(tmp_path.glob("*.tmp"))


def test_precall_store_failure_makes_zero_provider_calls() -> None:
    store = InMemoryProviderCallEvidenceStore(fail_on_transition=1)
    calls = 0

    def invoke():
        nonlocal calls
        calls += 1
        return {"ok": True}

    with pytest.raises(RuntimeError, match="store_transition_failed"):
        execute_evidenced_provider_call(
            store=store,
            precall=_precall(),
            invoke=invoke,
            content_from_result=lambda result: "",
            metadata_from_result=lambda result: None,
            now_ms=lambda: 101,
        )
    assert calls == 0
    assert (
        store.load(_precall().call_id).outcome
        == ProviderCallOutcome.BLOCKED_PRECALL.value
    )


def test_terminal_store_failure_leaves_indeterminate_and_blocks_promotion() -> None:
    store = InMemoryProviderCallEvidenceStore(fail_on_transition=2)
    result, receipt, promotable = execute_evidenced_provider_call(
        store=store,
        precall=_precall(),
        invoke=lambda: {
            "ok": True,
            "content": "exact response",
            "provider_call_metadata": _metadata(),
        },
        content_from_result=lambda result: result["content"],
        metadata_from_result=lambda result: result["provider_call_metadata"],
        now_ms=lambda: 101,
    )

    assert result is None
    assert not promotable
    assert receipt.outcome == ProviderCallOutcome.INDETERMINATE.value
    assert (
        store.load(receipt.call_id).outcome == ProviderCallOutcome.INDETERMINATE.value
    )


def test_base_exception_crash_leaves_durable_indeterminate() -> None:
    store = InMemoryProviderCallEvidenceStore()

    with pytest.raises(KeyboardInterrupt):
        execute_evidenced_provider_call(
            store=store,
            precall=_precall(),
            invoke=lambda: (_ for _ in ()).throw(KeyboardInterrupt()),
            content_from_result=lambda result: None,
            metadata_from_result=lambda result: None,
        )

    assert (
        store.load(_precall().call_id).outcome
        == ProviderCallOutcome.INDETERMINATE.value
    )


def test_explicit_synthetic_served_metadata_only() -> None:
    store = InMemoryProviderCallEvidenceStore()
    _, terminal, promotable = execute_evidenced_provider_call(
        store=store,
        precall=_precall(),
        invoke=lambda: {"ok": True, "content": "ok"},
        content_from_result=lambda result: result["content"],
        metadata_from_result=lambda result: result.get("provider_call_metadata"),
        now_ms=lambda: 101,
    )

    assert promotable
    assert terminal.served_provider is None
    assert terminal.served_model is None


def test_direct_fusion_surfaces_emit_same_canonical_evidence(monkeypatch) -> None:
    metadata = _metadata()

    def fake_fusion(*args):
        return {"ok": True, "content": "{}", "provider_call_metadata": metadata}

    monkeypatch.setenv("REDDOG_READONLY_AUDIT_RUNTIME_MODE", "foundups_fusion")
    monkeypatch.setenv("REDDOG_BACKEND_ARCHITECT_RUNTIME_MODE", "foundups_fusion")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(audit_runtime, "_load_foundups_fusion_runner", lambda: fake_fusion)
    monkeypatch.setattr(
        architect_runtime, "_load_foundups_fusion_runner", lambda: fake_fusion
    )
    audit_binding = model_runtime_binding_receipt(
        runtime_surface=audit_runtime.RUNTIME_SURFACE_READONLY_AUDIT
    )
    architect_binding = model_runtime_binding_receipt(
        runtime_surface=architect_runtime.RUNTIME_SURFACE_BACKEND_ARCHITECT
    )
    audit_reasons: list[str] = []
    architect_reasons: list[str] = []
    audit_topology = audit_runtime._model_runtime_binding(
        audit_binding,
        audit_reasons,
        expected_surface=audit_runtime.RUNTIME_SURFACE_READONLY_AUDIT,
    )
    architect_topology = architect_runtime._model_runtime_binding(
        architect_binding,
        architect_reasons,
        expected_surface=architect_runtime.RUNTIME_SURFACE_BACKEND_ARCHITECT,
    )

    audit_result = audit_runtime.FoundupsFusionRepoAuditModelRunner(
        provider_call_evidence_store=InMemoryProviderCallEvidenceStore()
    ).run_repo_code_audit(
        prompt="Return JSON.",
        context="public evidence",
        binding={"task_id": "task-parity", "model_selection": audit_topology},
        timeout_seconds=1,
    )
    architect_result = architect_runtime.FoundupsFusionArchitectModelRunner(
        provider_call_evidence_store=InMemoryProviderCallEvidenceStore()
    ).run_architect_determination(
        prompt="Return JSON.",
        context="public evidence",
        binding={"cycle_id": "cycle-parity", "model_selection": architect_topology},
        timeout_seconds=1,
    )

    assert audit_reasons == architect_reasons == []
    assert audit_result.ok and architect_result.ok
    for evidence in (
        audit_result.provider_call_evidence,
        architect_result.provider_call_evidence,
    ):
        assert evidence["schema_version"] == "reddog_provider_call_evidence.v1"
        assert evidence["outcome"] == "COMPLETED"
        assert evidence["served_model"] == "synthetic/model"


def test_direct_audit_surface_without_store_makes_zero_provider_calls(monkeypatch) -> None:
    calls = []
    monkeypatch.setenv("REDDOG_READONLY_AUDIT_RUNTIME_MODE", "foundups_fusion")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("REDDOG_PROVIDER_CALL_EVIDENCE_STORE_PATH", raising=False)
    monkeypatch.setattr(
        audit_runtime,
        "_load_foundups_fusion_runner",
        lambda: lambda *args: calls.append(args),
    )
    binding_receipt = model_runtime_binding_receipt(
        runtime_surface=audit_runtime.RUNTIME_SURFACE_READONLY_AUDIT
    )
    reasons: list[str] = []
    topology = audit_runtime._model_runtime_binding(
        binding_receipt,
        reasons,
        expected_surface=audit_runtime.RUNTIME_SURFACE_READONLY_AUDIT,
    )

    result = audit_runtime.FoundupsFusionRepoAuditModelRunner().run_repo_code_audit(
        prompt="Return JSON.",
        context="public evidence",
        binding={"task_id": "task-no-store", "model_selection": topology},
        timeout_seconds=1,
    )

    assert not result.ok
    assert result.rejection_reasons == ("provider_call_evidence_store_unavailable",)
    assert calls == []


def test_direct_architect_terminal_store_failure_blocks_result(monkeypatch) -> None:
    calls = []

    def fake_fusion(*args):
        calls.append(args)
        return {"ok": True, "content": "{}"}

    monkeypatch.setenv("REDDOG_BACKEND_ARCHITECT_RUNTIME_MODE", "foundups_fusion")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        architect_runtime, "_load_foundups_fusion_runner", lambda: fake_fusion
    )
    binding_receipt = model_runtime_binding_receipt(
        runtime_surface=architect_runtime.RUNTIME_SURFACE_BACKEND_ARCHITECT
    )
    reasons: list[str] = []
    topology = architect_runtime._model_runtime_binding(
        binding_receipt,
        reasons,
        expected_surface=architect_runtime.RUNTIME_SURFACE_BACKEND_ARCHITECT,
    )
    result = architect_runtime.FoundupsFusionArchitectModelRunner(
        provider_call_evidence_store=InMemoryProviderCallEvidenceStore(
            fail_on_transition=2
        )
    ).run_architect_determination(
        prompt="Return JSON.",
        context="public evidence",
        binding={"cycle_id": "cycle-terminal", "model_selection": topology},
        timeout_seconds=1,
    )

    assert not result.ok
    assert result.made_network_call
    assert result.provider_call_evidence["outcome"] == "INDETERMINATE"
    assert len(calls) == 1


class _TerminalWriteAndRecoveryReadFailureStore(
    InMemoryProviderCallEvidenceStore
):
    def __init__(self) -> None:
        super().__init__(fail_on_transition=2)
        self.load_calls = 0

    def load(self, call_id: str):
        self.load_calls += 1
        raise RuntimeError("store_load_failed")


class _RaisingText:
    def __str__(self) -> str:
        raise RuntimeError("synthetic_extraction_failure")


def test_direct_audit_preserves_attempted_lineage_when_terminal_and_load_fail(
    monkeypatch,
) -> None:
    calls = []

    def failing_fusion(*args):
        calls.append(args)
        raise RuntimeError("synthetic_provider_failure")

    monkeypatch.setenv("REDDOG_READONLY_AUDIT_RUNTIME_MODE", "foundups_fusion")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        audit_runtime, "_load_foundups_fusion_runner", lambda: failing_fusion
    )
    binding_receipt = model_runtime_binding_receipt(
        runtime_surface=audit_runtime.RUNTIME_SURFACE_READONLY_AUDIT
    )
    reasons: list[str] = []
    topology = audit_runtime._model_runtime_binding(
        binding_receipt,
        reasons,
        expected_surface=audit_runtime.RUNTIME_SURFACE_READONLY_AUDIT,
    )
    store = _TerminalWriteAndRecoveryReadFailureStore()

    result = audit_runtime.FoundupsFusionRepoAuditModelRunner(
        provider_call_evidence_store=store
    ).run_repo_code_audit(
        prompt="Return JSON.",
        context="public evidence",
        binding={"task_id": "task-double-failure", "model_selection": topology},
        timeout_seconds=1,
    )

    assert not result.ok
    assert result.made_network_call
    assert result.provider_call_evidence["attempted"] is True
    assert result.provider_call_evidence["outcome"] == "INDETERMINATE"
    assert result.provider_call_evidence["call_id"].startswith(
        "reddog_provider_call:"
    )
    assert len(calls) == 1


def test_direct_architect_preserves_attempted_lineage_when_terminal_and_load_fail(
    monkeypatch,
) -> None:
    calls = []

    def failing_fusion(*args):
        calls.append(args)
        raise RuntimeError("synthetic_provider_failure")

    monkeypatch.setenv("REDDOG_BACKEND_ARCHITECT_RUNTIME_MODE", "foundups_fusion")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        architect_runtime, "_load_foundups_fusion_runner", lambda: failing_fusion
    )
    binding_receipt = model_runtime_binding_receipt(
        runtime_surface=architect_runtime.RUNTIME_SURFACE_BACKEND_ARCHITECT
    )
    reasons: list[str] = []
    topology = architect_runtime._model_runtime_binding(
        binding_receipt,
        reasons,
        expected_surface=architect_runtime.RUNTIME_SURFACE_BACKEND_ARCHITECT,
    )
    store = _TerminalWriteAndRecoveryReadFailureStore()

    result = architect_runtime.FoundupsFusionArchitectModelRunner(
        provider_call_evidence_store=store
    ).run_architect_determination(
        prompt="Return JSON.",
        context="public evidence",
        binding={"cycle_id": "cycle-double-failure", "model_selection": topology},
        timeout_seconds=1,
    )

    assert not result.ok
    assert result.made_network_call
    assert result.provider_call_evidence["attempted"] is True
    assert result.provider_call_evidence["outcome"] == "INDETERMINATE"
    assert result.provider_call_evidence["call_id"].startswith(
        "reddog_provider_call:"
    )
    assert len(calls) == 1


def test_direct_audit_preserves_lineage_when_response_extraction_raises(
    monkeypatch,
) -> None:
    monkeypatch.setenv("REDDOG_READONLY_AUDIT_RUNTIME_MODE", "foundups_fusion")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        audit_runtime,
        "_load_foundups_fusion_runner",
        lambda: lambda *args: {"ok": True, "content": _RaisingText()},
    )
    binding_receipt = model_runtime_binding_receipt(
        runtime_surface=audit_runtime.RUNTIME_SURFACE_READONLY_AUDIT
    )
    reasons: list[str] = []
    topology = audit_runtime._model_runtime_binding(
        binding_receipt,
        reasons,
        expected_surface=audit_runtime.RUNTIME_SURFACE_READONLY_AUDIT,
    )

    result = audit_runtime.FoundupsFusionRepoAuditModelRunner(
        provider_call_evidence_store=_TerminalWriteAndRecoveryReadFailureStore()
    ).run_repo_code_audit(
        prompt="Return JSON.",
        context="public evidence",
        binding={"task_id": "task-extraction-failure", "model_selection": topology},
        timeout_seconds=1,
    )

    assert not result.ok
    assert result.made_network_call
    assert result.provider_call_evidence["attempted"] is True
    assert result.provider_call_evidence["outcome"] == "INDETERMINATE"


def test_direct_architect_preserves_lineage_when_response_extraction_raises(
    monkeypatch,
) -> None:
    monkeypatch.setenv("REDDOG_BACKEND_ARCHITECT_RUNTIME_MODE", "foundups_fusion")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        architect_runtime,
        "_load_foundups_fusion_runner",
        lambda: lambda *args: {"ok": True, "content": _RaisingText()},
    )
    binding_receipt = model_runtime_binding_receipt(
        runtime_surface=architect_runtime.RUNTIME_SURFACE_BACKEND_ARCHITECT
    )
    reasons: list[str] = []
    topology = architect_runtime._model_runtime_binding(
        binding_receipt,
        reasons,
        expected_surface=architect_runtime.RUNTIME_SURFACE_BACKEND_ARCHITECT,
    )

    result = architect_runtime.FoundupsFusionArchitectModelRunner(
        provider_call_evidence_store=_TerminalWriteAndRecoveryReadFailureStore()
    ).run_architect_determination(
        prompt="Return JSON.",
        context="public evidence",
        binding={"cycle_id": "cycle-extraction-failure", "model_selection": topology},
        timeout_seconds=1,
    )

    assert not result.ok
    assert result.made_network_call
    assert result.provider_call_evidence["attempted"] is True
    assert result.provider_call_evidence["outcome"] == "INDETERMINATE"


def test_fusion_progress_embeds_canonical_receipt_without_parallel_truth() -> None:
    terminal = terminalize_provider_call(
        arm_provider_call(
            create_precall_evidence(
                surface="test_surface",
                task_id="task-1",
                work_order_id=None,
                queue_item_id=None,
                run_id="run-1",
                cycle_id=None,
                requested_provider="test-provider",
                requested_model="test/model",
                redacted_input_digest=DIGEST_A,
                model_runtime_binding_receipt_id="binding-1",
                model_runtime_binding_digest=DIGEST_B,
                request_metadata={"timeout_seconds": 1},
                started_at_ms=100,
            )
        ),
        outcome=ProviderCallOutcome.COMPLETED,
        reason=ProviderCallReason.PROVIDER_RETURNED,
        completed_at_ms=101,
        content="not embedded",
    )
    recorder = FusionProgressRecorder("run-1")
    recorder.record_provider_call_evidence(terminal)
    receipt = recorder.receipt()

    assert receipt["provider_call_evidence"] == [terminal.to_dict()]
    assert receipt["provider_call_evidence_count"] == 1
    assert "not embedded" not in str(receipt)
    assert validate_fusion_progress_receipt(receipt) == (True, ())
