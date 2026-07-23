"""Tests for REDDOG_BACKEND_ARCHITECT_DETERMINATION_RUNTIME_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Callable, Mapping

import pytest

from holo_index.freshness_receipt import HoloIndexFreshnessReceipt
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ACTION_FIX,
    ACTION_RESEARCH_MORE,
    ARCHITECT_DETERMINATION_ACCEPT,
    ARCHITECT_DETERMINATION_REJECT,
    ArchitectDeterminationReason,
    ArchitectModelResult,
    FoundupsFusionArchitectModelRunner,
    InMemoryArchitectDeterminationStore,
    RUNTIME_SURFACE_BACKEND_ARCHITECT,
    run_reddog_backend_architect_determination_runtime,
)
from modules.communication.moltbot_bridge.src import reddog_backend_architect_determination_runtime as backend_runtime
from modules.communication.moltbot_bridge.src.reddog_context_snapshot_fusion_assignment_gate import (
    evaluate_context_snapshot_fusion_assignment_gate,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_runtime import (
    DEFAULT_AUDIT_LANES,
    validate_reddog_openclaw_readonly_audit_reports,
    plan_reddog_openclaw_readonly_audit_swarm,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    build_evidence_bundle,
    build_operational_context_snapshot,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_report_collection import (
    READONLY_AUDIT_REPORT_COLLECTION_ACCEPT,
    ReadOnlyAuditReportCollectionResult,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_provider_call_evidence import (
    InMemoryProviderCallEvidenceStore,
    ProviderCallOutcome,
    ProviderCallReason,
    arm_provider_call,
    create_precall_evidence,
    terminalize_provider_call,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _model_selection,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_runtime_binding_receipt,
)
from modules.communication.moltbot_bridge.tests.holoindex_freshness_receipt_test_helpers import (
    build_fresh_holoindex_receipt,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_backend_architect_determination_runtime.py"
)
NOW = "2026-07-15T00:00:00+00:00"
HEAD = "283d07ae4c7ed7bd1c8d9f9c7a112fd75ef00aaa"
REVISION = "sha256:authoritative-work-state"


class FakeArchitectRunner:
    def __init__(
        self,
        output: Mapping[str, Any] | str,
        *,
        ok: bool = True,
        quorum: bool = True,
        raise_timeout: bool = False,
        provider_call_evidence: (
            Mapping[str, Any]
            | Callable[[Mapping[str, Any]], Mapping[str, Any]]
            | None
        ) = None,
    ) -> None:
        self.output = output
        self.ok = ok
        self.quorum = quorum
        self.raise_timeout = raise_timeout
        self.provider_call_evidence = provider_call_evidence
        self.calls: list[dict[str, Any]] = []

    def run_architect_determination(self, *, prompt: str, context: str, binding: Mapping[str, Any], timeout_seconds: int):
        self.calls.append(
            {
                "prompt": prompt,
                "context": context,
                "binding": dict(binding),
                "timeout_seconds": timeout_seconds,
            }
        )
        if self.raise_timeout:
            raise TimeoutError("model timeout")
        content = self.output if isinstance(self.output, str) else json.dumps(self.output, sort_keys=True)
        evidence = self.provider_call_evidence
        if evidence is None:
            evidence = _provider_call_evidence_from_binding(binding)
        elif callable(evidence):
            evidence = evidence(binding)
        return ArchitectModelResult(
            ok=self.ok,
            status="MODEL_OK" if self.ok else "MODEL_REJECT",
            content=content,
            model_receipt_id="model-receipt-1",
            model_result_digest="sha256:model-result",
            review_packet={"fusion_panel_quorum": {"passed": self.quorum}},
            made_network_call=True,
            rejection_reasons=() if self.ok else ("model_failed",),
            provider_call_evidence=dict(evidence),
        )


def _repo_state() -> dict[str, object]:
    return {
        "head_sha": HEAD,
        "dirty_paths": (),
        "dirty_digest": "sha256:clean",
        "worktree_digest": "sha256:worktrees",
    }


def _work_state() -> dict[str, object]:
    return {
        "schema_version": "reddog_authoritative_work_state.v1",
        "revision": REVISION,
        "selected_slice": "REDDOG_BACKEND_ARCHITECT_DETERMINATION_RUNTIME_PHASE1",
        "refresh_receipt_id": "sha256:refresh",
        "worker_claims": [
            {"claim_id": "claim-1", "slice_id": "REDDOG_BACKEND_ARCHITECT_DETERMINATION_RUNTIME_PHASE1"}
        ],
        "wre_queue_items": [{"queue_item_id": "queue-1", "claim_id": "claim-1"}],
    }


def _fresh_holo_receipt() -> HoloIndexFreshnessReceipt:
    return build_fresh_holoindex_receipt(
        repo_root=REPO_ROOT,
        head_sha=HEAD,
        generated_at=NOW,
    )


def _build_inputs(
    *,
    include_reports: bool = True,
    include_runtime_binding: bool = True,
    architect_runtime_binding: Mapping[str, Any] | None = None,
):
    if architect_runtime_binding is None:
        architect_runtime_binding = model_runtime_binding_receipt(
            runtime_surface=RUNTIME_SURFACE_BACKEND_ARCHITECT
        )
    snapshot_result = build_operational_context_snapshot(
        repo_state=_repo_state(),
        work_state_snapshot=_work_state(),
        holoindex_receipt=_fresh_holo_receipt(),
        changed_paths=("modules/communication/moltbot_bridge/src/reddog_backend_architect_determination_runtime.py",),
        now_iso=NOW,
        breadcrumb_scope="REDDOG_BACKEND_ARCHITECT_DETERMINATION_RUNTIME_PHASE1",
    )
    assert snapshot_result.accepted is True
    snapshot = snapshot_result.snapshot
    context_view = snapshot_result.context_view
    assert snapshot is not None and context_view is not None
    evidence_bundle = build_evidence_bundle(
        snapshot=snapshot,
        context_view=context_view,
        report_digests=("sha256:source-receipts",),
    )
    fusion_gate = evaluate_context_snapshot_fusion_assignment_gate(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        current_repo_head_sha=HEAD,
        current_work_state_revision=REVISION,
        requested_operation="backend_architect_determination",
        prompt_text="Produce backend architect determination",
        now_iso=NOW,
    )
    assert fusion_gate.accepted is True
    plan = plan_reddog_openclaw_readonly_audit_swarm(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        gate_decision=fusion_gate,
        audit_lanes=DEFAULT_AUDIT_LANES,
        allowed_read_targets=("modules/communication/moltbot_bridge/src/reddog_backend_architect_determination_runtime.py",),
    )
    assert plan.accepted is True
    reports = _reports(plan) if include_reports else ()
    validation = validate_reddog_openclaw_readonly_audit_reports(plan=plan, reports=reports)
    collection = ReadOnlyAuditReportCollectionResult(
        accepted=validation.accepted,
        status=READONLY_AUDIT_REPORT_COLLECTION_ACCEPT if validation.accepted else "REJECT",
        swarm_id=plan.receipt.swarm_id,
        report_count=len(reports),
        validation=validation,
        rejection_reasons=validation.rejection_reasons,
    )
    allocation_kwargs: dict[str, Any] = {}
    if include_runtime_binding:
        allocation_kwargs["architect_model_runtime_binding_receipt"] = architect_runtime_binding
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation="backend_architect_determination",
        prompt_text="RedDog backend architect determination runtime",
        changed_paths=("modules/communication/moltbot_bridge/src/reddog_backend_architect_determination_runtime.py",),
        allowed_read_targets=("modules/communication/moltbot_bridge/src/reddog_backend_architect_determination_runtime.py",),
        **allocation_kwargs,
    ).to_dict()
    return {
        "snapshot": snapshot,
        "context_view": context_view,
        "evidence_bundle": evidence_bundle,
        "fusion_gate": fusion_gate,
        "report_collection": collection,
        "reports": reports,
        "allocation": allocation,
        "architect_runtime_binding": architect_runtime_binding if include_runtime_binding else None,
    }


def _reports(plan) -> tuple[dict[str, Any], ...]:
    reports: list[dict[str, Any]] = []
    for assignment in plan.assignments:
        evidence_ref = f"file:docs/{assignment.lane_id}.md:sha256:{assignment.lane_id}:lines:1"
        reports.append(
            {
                "assignment_id": assignment.assignment_id,
                "lane_id": assignment.lane_id,
                "snapshot_receipt_id": assignment.snapshot_receipt_id,
                "summary": f"{assignment.lane_id} report supports backend architect determination.",
                "evidence_refs": [evidence_ref],
                "repo_mutation_performed": False,
                "execution_performed": False,
                "openclaw_enqueue_performed": False,
                "readonly_audit_performed": True,
                "report_digest": f"sha256:{assignment.lane_id}",
                "findings": [
                    {
                        "finding_id": f"{assignment.lane_id}-finding",
                        "claim": "Backend architect runtime needs one next implementation slice.",
                        "wsp97_label": "OBSERVED",
                        "recommended_action": "FIX",
                        "wsp15_priority": "P0",
                        "severity": "MAJOR",
                        "evidence_refs": [evidence_ref],
                        "next_slice_name": "REDDOG_NEXT_RUNTIME_SLICE_PHASE1",
                    }
                ],
            }
        )
    return tuple(reports)


def _model_output(allocation: Mapping[str, Any], evidence_ref: str, *, action: str = ACTION_FIX) -> dict[str, Any]:
    return {
        "action": action,
        "next_slice_name": "REDDOG_NEXT_RUNTIME_SLICE_PHASE1" if action != "STOP" else None,
        "summary": "Verified reports support one next backend runtime slice.",
        "decision_reasons": ["selected verified P0 runtime gap"],
        "evidence_refs": [evidence_ref],
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
    }


def _runtime_kwargs(inputs: Mapping[str, Any]) -> dict[str, Any]:
    kwargs = {
        "snapshot": inputs["snapshot"],
        "context_view": inputs["context_view"],
        "evidence_bundle": inputs["evidence_bundle"],
        "fusion_gate": inputs["fusion_gate"],
        "report_collection": inputs["report_collection"],
        "reports": inputs["reports"],
    }
    if inputs["architect_runtime_binding"] is not None:
        kwargs["model_runtime_binding_receipt"] = inputs["architect_runtime_binding"]
    return kwargs


def _provider_call_evidence_from_binding(
    binding: Mapping[str, Any],
    *,
    task_id: str | None = None,
    work_order_id: str | None = None,
    queue_item_id: str | None = None,
    run_id: str | None = None,
    surface: str = RUNTIME_SURFACE_BACKEND_ARCHITECT,
    cycle_id: str | None = None,
    runtime_receipt_id: str | None = None,
    runtime_digest: str | None = None,
    requested_provider: str = "openrouter",
    requested_model: str | None = None,
    outcome: ProviderCallOutcome = ProviderCallOutcome.COMPLETED,
) -> dict[str, Any]:
    model_selection = binding.get("model_selection")
    topology = model_selection if isinstance(model_selection, Mapping) else {}
    precall = create_precall_evidence(
        surface=surface,
        task_id=task_id,
        work_order_id=work_order_id,
        queue_item_id=queue_item_id,
        run_id=run_id,
        cycle_id=cycle_id or str(binding.get("cycle_id") or ""),
        requested_provider=requested_provider,
        requested_model=requested_model
        or str(topology.get("lead_model") or ""),
        redacted_input_digest="sha256:" + "a" * 64,
        model_runtime_binding_receipt_id=runtime_receipt_id
        or str(topology.get("model_runtime_binding_receipt_id") or ""),
        model_runtime_binding_digest=runtime_digest
        or str(topology.get("model_runtime_binding_digest") or ""),
        request_metadata={"timeout_seconds": 1},
        started_at_ms=100,
    )
    return terminalize_provider_call(
        arm_provider_call(precall),
        outcome=outcome,
        reason=(
            ProviderCallReason.PROVIDER_RETURNED
            if outcome == ProviderCallOutcome.COMPLETED
            else ProviderCallReason.PROVIDER_FAILED
        ),
        completed_at_ms=101,
    ).to_dict()


def test_backend_architect_runtime_accepts_fix_persists_and_emits_one_queue_candidate() -> None:
    inputs = _build_inputs()
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    store = InMemoryArchitectDeterminationStore()
    runner = FakeArchitectRunner(_model_output(inputs["allocation"], evidence_ref))

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=store,
        model_runner=runner,
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.status == ARCHITECT_DETERMINATION_ACCEPT
    assert result.receipt.action == ACTION_FIX
    assert result.receipt.fusion_quorum_passed is True
    assert result.receipt.wsp15_allocation_receipt_id == inputs["allocation"]["receipt_id"]
    assert result.receipt.queue_candidate is not None
    assert result.queue_candidate_count == 1
    assert result.receipt.queue_candidate.slice_id == "REDDOG_NEXT_RUNTIME_SLICE_PHASE1"
    assert result.receipt.queue_candidate.status == "CANDIDATE"
    assert result.persist_result.accepted is True
    assert result.persist_result.stored is True
    assert len(store.records) == 1
    assert len(runner.calls) == 1
    assert result.no_repo_mutation_performed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_holoindex_reindex_performed is True


def test_accepted_receipt_and_queue_parent_bind_provider_evidence_lineage() -> None:
    inputs = _build_inputs()
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    output = _model_output(inputs["allocation"], evidence_ref)
    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=FakeArchitectRunner(output),
        now_iso=NOW,
    )

    assert result.accepted
    assert result.receipt.provider_call_id
    assert result.receipt.provider_call_receipt_id
    assert result.receipt.provider_call_evidence_digest
    assert result.receipt.queue_candidate is not None
    assert (
        result.receipt.queue_candidate.source_determination_receipt_id
        == result.receipt.determination_receipt_id
    )


@pytest.mark.parametrize(
    "evidence_factory",
    [
        lambda binding: {},
        lambda binding: _provider_call_evidence_from_binding(
            binding, surface="wrong_architect_surface"
        ),
        lambda binding: _provider_call_evidence_from_binding(
            binding, cycle_id="wrong-cycle"
        ),
        lambda binding: _provider_call_evidence_from_binding(
            binding, task_id="forged-task"
        ),
        lambda binding: _provider_call_evidence_from_binding(
            binding, work_order_id="forged-work"
        ),
        lambda binding: _provider_call_evidence_from_binding(
            binding, queue_item_id="forged-queue"
        ),
        lambda binding: _provider_call_evidence_from_binding(
            binding, run_id="forged-run"
        ),
        lambda binding: _provider_call_evidence_from_binding(
            binding, runtime_receipt_id="wrong-binding"
        ),
        lambda binding: _provider_call_evidence_from_binding(
            binding, runtime_digest="sha256:" + "f" * 64
        ),
        lambda binding: _provider_call_evidence_from_binding(
            binding, outcome=ProviderCallOutcome.FAILED
        ),
        lambda binding: _provider_call_evidence_from_binding(
            binding, requested_provider="other-provider"
        ),
        lambda binding: _provider_call_evidence_from_binding(
            binding, requested_model="other/model"
        ),
        lambda binding: {
            **_provider_call_evidence_from_binding(binding),
            "attempted": False,
        },
    ],
)
def test_architect_rejects_missing_or_mismatched_provider_evidence_before_queue(
    evidence_factory,
) -> None:
    inputs = _build_inputs()
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=FakeArchitectRunner(
            _model_output(inputs["allocation"], evidence_ref),
            provider_call_evidence=evidence_factory,
        ),
        now_iso=NOW,
    )

    assert result.accepted is False
    assert result.queue_candidate_count == 0
    assert result.receipt.queue_candidate is None
    assert (
        ArchitectDeterminationReason.PROVIDER_CALL_EVIDENCE
        in result.rejection_reasons
    )


def test_research_more_persists_without_queue_candidate() -> None:
    inputs = _build_inputs()
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    output = _model_output(inputs["allocation"], evidence_ref, action=ACTION_RESEARCH_MORE)
    runner = FakeArchitectRunner(output)

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=runner,
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.receipt.action == ACTION_RESEARCH_MORE
    assert result.receipt.queue_candidate is None
    assert result.queue_candidate_count == 0


def test_runtime_binding_is_authoritative_over_model_selection_metadata() -> None:
    inputs = _build_inputs()
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    selection = _model_selection()
    runner = FakeArchitectRunner(_model_output(inputs["allocation"], evidence_ref))

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=runner,
        model_selection_receipt=selection,
        now_iso=NOW,
    )

    assert result.accepted is True
    runtime_binding = inputs["architect_runtime_binding"]
    assert result.receipt.model_selection_receipt_id == runtime_binding["selection_receipt_id"]
    assert result.receipt.model_selection_digest
    binding = runner.calls[0]["binding"]["model_selection"]
    assert binding["receipt_id"] == runtime_binding["selection_receipt_id"]
    assert binding["model_runtime_binding_receipt_id"] == runtime_binding["receipt_id"]
    assert binding["purpose"] == "production"


def test_model_runtime_binding_receipt_is_bound_to_backend_runner_and_receipt() -> None:
    runtime_binding = model_runtime_binding_receipt(
        runtime_surface=RUNTIME_SURFACE_BACKEND_ARCHITECT,
        model_id="z-ai/glm-5.2",
        panel_model_ids=("moonshotai/kimi-k3",),
    )
    inputs = _build_inputs(architect_runtime_binding=runtime_binding)
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    runner = FakeArchitectRunner(_model_output(inputs["allocation"], evidence_ref))

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=runner,
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.receipt.model_runtime_binding_receipt_id == runtime_binding["receipt_id"]
    assert result.receipt.model_runtime_binding_digest
    binding = runner.calls[0]["binding"]["model_selection"]
    assert binding["model_runtime_binding_receipt_id"] == runtime_binding["receipt_id"]
    assert binding["lead_model"] == "z-ai/glm-5.2"
    assert binding["panel_models"] == ["moonshotai/kimi-k3"]


def test_mismatched_model_runtime_binding_receipt_rejects_before_backend_model_call() -> None:
    inputs = _build_inputs()
    runtime_binding = model_runtime_binding_receipt(runtime_surface="wrong_surface")
    runner = FakeArchitectRunner({})
    store = InMemoryArchitectDeterminationStore()
    runtime_kwargs = _runtime_kwargs(inputs)
    runtime_kwargs["model_runtime_binding_receipt"] = runtime_binding

    result = run_reddog_backend_architect_determination_runtime(
        **runtime_kwargs,
        wsp15_allocation_receipt=inputs["allocation"],
        store=store,
        model_runner=runner,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.MODEL_RUNTIME_BINDING_RECEIPT in result.rejection_reasons
    assert runner.calls == []
    assert store.records == []


def test_same_surface_runtime_binding_substitution_rejects_before_backend_calls() -> None:
    inputs = _build_inputs()
    substituted = model_runtime_binding_receipt(
        runtime_surface=RUNTIME_SURFACE_BACKEND_ARCHITECT,
        model_id="moonshotai/kimi-k3",
    )
    runner = FakeArchitectRunner({})
    store = InMemoryArchitectDeterminationStore()
    runtime_kwargs = _runtime_kwargs(inputs)
    runtime_kwargs["model_runtime_binding_receipt"] = substituted

    result = run_reddog_backend_architect_determination_runtime(
        **runtime_kwargs,
        wsp15_allocation_receipt=inputs["allocation"],
        store=store,
        model_runner=runner,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.MODEL_RUNTIME_BINDING_RECEIPT in result.rejection_reasons
    assert runner.calls == []
    assert store.records == []


def test_production_architect_rejects_selection_only_before_provider_call() -> None:
    inputs = _build_inputs(include_runtime_binding=False)
    store = InMemoryArchitectDeterminationStore()

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=store,
        model_runner=None,
        model_selection_receipt=_model_selection(),
        now_iso=NOW,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.MODEL_RUNTIME_BINDING_RECEIPT in result.rejection_reasons
    assert result.receipt.model_result_digest is None
    assert store.records == []


def test_tampered_selection_metadata_cannot_override_valid_runtime_binding() -> None:
    inputs = _build_inputs()
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    selection = _model_selection()
    selection["selected_model_ids"] = ["attacker/model"]
    runner = FakeArchitectRunner(_model_output(inputs["allocation"], evidence_ref))

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=runner,
        model_selection_receipt=selection,
        now_iso=NOW,
    )

    assert result.accepted is True
    assert len(runner.calls) == 1
    binding = runner.calls[0]["binding"]["model_selection"]
    assert binding["model_runtime_binding_receipt_id"] == inputs["architect_runtime_binding"][
        "receipt_id"
    ]
    assert binding["selected_model_ids"] != ["attacker/model"]


def test_missing_reports_fail_before_model_call() -> None:
    inputs = _build_inputs(include_reports=False)
    runner = FakeArchitectRunner({})

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=runner,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert result.status == ARCHITECT_DETERMINATION_REJECT
    assert ArchitectDeterminationReason.REPORT_COLLECTION_NOT_ACCEPTED in result.rejection_reasons
    assert ArchitectDeterminationReason.MISSING_AUDIT_REPORTS in result.rejection_reasons
    assert runner.calls == []


def test_failed_fusion_quorum_rejects_after_model_call() -> None:
    inputs = _build_inputs()
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    runner = FakeArchitectRunner(_model_output(inputs["allocation"], evidence_ref), quorum=False)

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=runner,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.FUSION_QUORUM_NOT_PASSED in result.rejection_reasons
    assert result.persist_result.stored is False


def test_invented_evidence_ref_rejects_invalid_output() -> None:
    inputs = _build_inputs()
    output = _model_output(inputs["allocation"], "file:not-in-report.md:1")
    runner = FakeArchitectRunner(output)

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=runner,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.INVALID_MODEL_OUTPUT in result.rejection_reasons


def test_wsp15_receipt_mismatch_rejects() -> None:
    inputs = _build_inputs()
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    output = _model_output(inputs["allocation"], evidence_ref)
    output["wsp15_allocation_receipt_id"] = "sha256:not-the-allocation"
    runner = FakeArchitectRunner(output)

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=runner,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.WSP15_RECEIPT_MISMATCH in result.rejection_reasons


def test_malformed_wsp15_bool_score_rejects_before_model_call() -> None:
    inputs = _build_inputs()
    allocation = dict(inputs["allocation"])
    allocation["importance"] = True
    runner = FakeArchitectRunner({})

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=allocation,
        store=InMemoryArchitectDeterminationStore(),
        model_runner=runner,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.MALFORMED_WSP15_ALLOCATION in result.rejection_reasons
    assert runner.calls == []


def test_priority_mps_total_mismatch_rejects_before_model_call() -> None:
    inputs = _build_inputs()
    allocation = dict(inputs["allocation"])
    allocation["priority"] = "P4"
    runner = FakeArchitectRunner({})

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=allocation,
        store=InMemoryArchitectDeterminationStore(),
        model_runner=runner,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.MALFORMED_WSP15_ALLOCATION in result.rejection_reasons
    assert runner.calls == []


def test_prompt_budget_exceeded_rejects_without_malformed_json(monkeypatch) -> None:
    inputs = _build_inputs()
    runner = FakeArchitectRunner({})
    monkeypatch.setattr(backend_runtime, "DEFAULT_MAX_PROMPT_CHARS", 40)

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=runner,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.PROMPT_BUDGET_EXCEEDED in result.rejection_reasons
    assert runner.calls == []


def test_duplicate_cycle_fails_closed_before_model_call() -> None:
    inputs = _build_inputs()
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    store = InMemoryArchitectDeterminationStore()

    first = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=store,
        model_runner=FakeArchitectRunner(_model_output(inputs["allocation"], evidence_ref)),
        now_iso=NOW,
    )
    assert first.accepted is True
    second_runner = FakeArchitectRunner(_model_output(inputs["allocation"], evidence_ref))
    second = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=store,
        model_runner=second_runner,
        now_iso=NOW,
    )

    assert second.accepted is False
    assert ArchitectDeterminationReason.DUPLICATE_CYCLE in second.rejection_reasons
    assert second_runner.calls == []


def test_expired_snapshot_fails_closed_before_model_call() -> None:
    inputs = _build_inputs()
    runner = FakeArchitectRunner({})

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=runner,
        now_iso="2026-07-15T01:00:00+00:00",
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.SNAPSHOT_EXPIRED in result.rejection_reasons
    assert runner.calls == []


def test_model_timeout_rejects_without_persistence() -> None:
    inputs = _build_inputs()
    runner = FakeArchitectRunner({}, raise_timeout=True)

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=runner,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.MODEL_TIMEOUT in result.rejection_reasons
    assert result.persist_result.stored is False


def test_model_failure_rejects_without_persistence() -> None:
    inputs = _build_inputs()
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    runner = FakeArchitectRunner(_model_output(inputs["allocation"], evidence_ref), ok=False)

    result = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=runner,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert ArchitectDeterminationReason.MODEL_FAILURE in result.rejection_reasons
    assert result.persist_result.stored is False


def test_production_runner_is_explicit_mode_only_without_network(monkeypatch) -> None:
    monkeypatch.delenv("REDDOG_BACKEND_ARCHITECT_RUNTIME_MODE", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    result = FoundupsFusionArchitectModelRunner(
        provider_call_evidence_store=InMemoryProviderCallEvidenceStore()
    ).run_architect_determination(
        prompt="Return JSON.",
        context="{}",
        binding={"binding": "test"},
        timeout_seconds=1,
    )

    assert result.ok is False
    assert result.made_network_call is False
    assert result.rejection_reasons == ("runtime_mode_not_enabled",)


def test_production_runner_uses_model_selection_topology(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_fusion(api_key, user_payload, messages, payload):
        calls.append(dict(payload))
        return {
            "ok": True,
            "content": json.dumps(
                {
                    "action": ACTION_RESEARCH_MORE,
                    "next_slice_name": "REDDOG_NEXT_RUNTIME_SLICE_PHASE1",
                    "summary": "ok",
                    "decision_reasons": ["test"],
                    "evidence_refs": ["file:test.md:1"],
                    "wsp15_allocation_receipt_id": "wsp15:test",
                },
                sort_keys=True,
            ),
            "review_packet": {"receipt_id": "fusion-receipt-1"},
        }

    monkeypatch.setenv("REDDOG_BACKEND_ARCHITECT_RUNTIME_MODE", "foundups_fusion")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(backend_runtime, "_load_foundups_fusion_runner", lambda: fake_fusion)

    runtime_binding = model_runtime_binding_receipt(
        runtime_surface=RUNTIME_SURFACE_BACKEND_ARCHITECT,
        model_id="z-ai/glm-5.2",
        panel_model_ids=("moonshotai/kimi-k3",),
    )
    topology_reasons: list[str] = []
    topology = backend_runtime._model_runtime_binding(
        runtime_binding,
        topology_reasons,
        expected_surface=RUNTIME_SURFACE_BACKEND_ARCHITECT,
    )
    assert topology_reasons == []
    result = FoundupsFusionArchitectModelRunner(
        provider_call_evidence_store=InMemoryProviderCallEvidenceStore()
    ).run_architect_determination(
        prompt="Return JSON.",
        context="public evidence",
            binding={"cycle_id": "cycle-direct-1", "model_selection": topology},
        timeout_seconds=1,
    )

    assert result.ok is True
    assert calls[0]["lead_model"] == "z-ai/glm-5.2"
    assert calls[0]["panel_models"] == ["moonshotai/kimi-k3"]
    assert calls[0]["bridge_meta"]["model_runtime_binding_receipt_id"] == runtime_binding["receipt_id"]


def test_module_ast_denies_execution_and_mutation_surfaces() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_imports = {"subprocess", "shutil"}
    banned_attrs = {
        ("os", "system"),
        ("os", "popen"),
        ("os", "spawn"),
        ("os", "replace"),
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in banned_imports
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in banned_imports
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            assert (node.value.id, node.attr) not in banned_attrs
