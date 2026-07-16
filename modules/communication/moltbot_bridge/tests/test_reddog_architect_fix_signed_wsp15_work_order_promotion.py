"""Tests for REDDOG_ARCHITECT_FIX_TO_SIGNED_WSP15_WORK_ORDER_PROMOTION_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Mapping

from modules.ai_intelligence.ai_gateway.src.model_intelligence_catalog import (
    Availability,
    ModelCapabilityCard,
    PromotionState,
    build_model_catalog_snapshot,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    ModelOutcomeMetrics,
    build_model_benchmark_evidence_receipt,
    build_model_promotion_evidence_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import (
    ModelTaskRequirements,
    SelectionMode,
    SelectionPurpose,
    select_models_for_task,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    ModelEvidenceSignerRole,
    ModelEvidenceSubjectType,
    VerifiedModelEvidenceEntry,
    VerifiedModelProductionEvidence,
    build_model_signed_evidence_receipt,
)
from modules.communication.moltbot_bridge.src import (
    reddog_architect_fix_signed_wsp15_work_order_promotion as promotion,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_refresh_runtime import (
    InMemoryAuthoritativeWorkStateStore,
)
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ACTION_FIX,
    ACTION_RESEARCH_MORE,
    ARCHITECT_DETERMINATION_ACCEPT,
    ARCHITECT_QUEUE_CANDIDATE_SCHEMA_VERSION,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_consumer_dryrun import (
    WRE_QUEUE_CONSUMER_DRYRUN_READY,
    plan_reddog_wre_queue_consumer_dry_run,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
    canonical_reddog_wsp15_allocation_digest,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_architect_fix_signed_wsp15_work_order_promotion.py"
)
NOW = "2026-07-16T00:00:00+00:00"
SNAPSHOT_ID = "sha256:snapshot-1"


def _allocation() -> dict[str, Any]:
    return allocate_reddog_wsp15_receipt(
        requested_operation="architect_fix_promotion",
        prompt_text="RedDog architect FIX promotion runtime authority",
        changed_paths=("modules/communication/moltbot_bridge/src/reddog_backend_architect_determination_runtime.py",),
        allowed_read_targets=(
            "modules/communication/moltbot_bridge/src/reddog_backend_architect_determination_runtime.py",
        ),
    ).to_dict()


def _work_state() -> dict[str, Any]:
    return {
        "schema_version": "reddog_authoritative_work_state.v1",
        "revision": "sha256:work-state-rev-1",
        "refresh_receipt_id": "sha256:fresh-1",
        "reconciliation_report_id": "sha256:reconcile-1",
        "freshness_receipts": [{"receipt_id": "sha256:fresh-1", "fresh": True}],
        "worker_claims": [],
        "wre_queue_items": [],
        "queue_sync_receipts": [],
    }


def _determination(*, action: str = ACTION_FIX, allocation: Mapping[str, Any] | None = None) -> dict[str, Any]:
    allocation = allocation or _allocation()
    determination_id = "sha256:architect-determination-1"
    candidate = {
        "schema_version": ARCHITECT_QUEUE_CANDIDATE_SCHEMA_VERSION,
        "queue_candidate_id": "sha256:queue-candidate-1",
        "source_determination_receipt_id": determination_id,
        "slice_id": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
        "status": "CANDIDATE",
        "evidence_refs": ["file:docs/audit.md:1"],
        "wsp15_allocation_receipt": dict(allocation),
        "no_queue_mutation_performed": True,
        "no_execution_performed": True,
        "no_worker_spawn_performed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_repo_mutation_performed": True,
    }
    return {
        "schema_version": "reddog_architect_determination_receipt.v1",
        "determination_receipt_id": determination_id,
        "cycle_id": "sha256:cycle-1",
        "accepted": True,
        "status": ARCHITECT_DETERMINATION_ACCEPT,
        "action": action,
        "next_slice_name": candidate["slice_id"] if action == ACTION_FIX else None,
        "summary": "Promote one verified FIX slice.",
        "snapshot_receipt_id": SNAPSHOT_ID,
        "snapshot_content_digest": "sha256:snapshot-content",
        "context_view_id": "sha256:context-view",
        "evidence_bundle_id": "sha256:evidence-bundle",
        "report_bundle_id": "sha256:report-bundle",
        "report_count": 5,
        "audit_report_digests": ["sha256:report-1"],
        "model_result_digest": "sha256:model-result",
        "model_receipt_id": "model-receipt-1",
        "fusion_quorum_passed": True,
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "wsp15_allocation_digest": canonical_reddog_wsp15_allocation_digest(allocation),
        "queue_candidate": candidate if action == ACTION_FIX else None,
        "decision_reasons": ["FIX is the next verified bridge."],
        "rejection_reasons": [],
    }


def _authority_profile(**overrides: Any) -> dict[str, Any]:
    profile = {
        "principal_id": "github:mjtrout",
        "principal_provider": "github",
        "principal_public_key": "pub:principal",
        "reddog_id": "reddog:architect",
        "reddog_public_key": "pub:reddog",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "foundup_id": "paccess_001",
        "allowed_paths": ["modules/communication/moltbot_bridge/**"],
        "denied_paths": ["modules/communication/moltbot_bridge/secrets/**"],
        "requested_operation": "feature_slice",
        "permission_snapshot_digest": "sha256:permission",
        "identity_nonce": "identity-nonce-1",
        "work_authority_nonce": "workauth-nonce-1",
        "issued_at": 1000,
        "identity_expires_at": 4600,
        "work_authority_expires_at": 1300,
        "valve_state_required": "VALVE_OPEN_WORKTREE_CREATE",
        "key_epoch": "epoch-1",
        "required_tests": ["pytest modules/communication/moltbot_bridge/tests"],
        "required_policy_gates": ["signed_work_order_authority", "execution_valve"],
        "holoindex_evidence": {
            "holoindex_query": "RedDog architect FIX promotion",
            "holoindex_status": "bundle_json_ok",
            "index_gap_detected": False,
            "retrieval_quality": "HIGH",
            "applicable_wsps": ["WSP_15", "WSP_97"],
            "evidence_refs": [
                "modules/communication/moltbot_bridge/src/reddog_backend_architect_determination_runtime.py"
            ],
        },
    }
    profile.update(overrides)
    return profile


def _memex_supply(**overrides: Any) -> dict[str, Any]:
    payload = {
        "schema_version": "reddog_operational_memex_snapshot_supply_receipt.v1",
        "foundup_id": "paccess_001",
        "principal_id": "github:mjtrout",
        "snapshot_receipt_id": SNAPSHOT_ID,
        "snapshot_content_digest": "sha256:snapshot-content",
        "memex_view_id": "memex-view-1",
        "holoindex_generation_id": "sha256:holo-generation",
        "source_revision": "sha256:memex-source",
        "policy_issued_at": NOW,
        "policy_expires_at": "2026-07-16T01:00:00+00:00",
        "assignment_id": "assignment-1",
        "lane_id": "repo_code_audit",
        "receipt_id": "sha256:memex-supply",
        "no_memex_write_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_repo_mutation_performed": True,
    }
    payload.update(overrides)
    return payload


def _model_selection(*, purpose: SelectionPurpose = SelectionPurpose.PRODUCTION) -> dict[str, Any]:
    model_id = "openai/gpt-5.6-code"
    task_family = "reddog_architect_fix_promotion"
    benchmark = build_model_benchmark_evidence_receipt(
        model_id=model_id,
        task_family=task_family,
        task_set_digest="sha256:task-set",
        held_out_split_digest="sha256:held-out",
        prompt_topology_digest="sha256:topology",
        verifier_digest="sha256:verifier",
        verifier_receipt_id="sha256:verifier-receipt",
        sample_count=10,
        accepted_count=10,
        metrics=ModelOutcomeMetrics(latency_ms=100, input_tokens=10, output_tokens=20),
    )
    promotion_receipt = build_model_promotion_evidence_receipt(
        benchmark_receipt=benchmark,
        promotion_state=PromotionState.CHAMPION,
        promotion_authority_receipt_id="sha256:promotion-authority",
        signed_promotion_receipt_id="signature:promotion",
        min_verifier_pass_rate=0.8,
    )
    benchmark_sig = build_model_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.BENCHMARK_VERIFIER,
        signer_public_key="pub:benchmark",
        signer_key_fingerprint="fingerprint:benchmark",
        key_epoch="epoch-1",
        subject_type=ModelEvidenceSubjectType.MODEL,
        model_or_panel_subject=model_id,
        catalog_snapshot_id="model_catalog_snapshot:pending",
        selection_receipt_id="model_selection_receipt:pending",
        benchmark_run_receipt_id="model_combination_benchmark_run:1",
        benchmark_evidence_receipt_id=benchmark.receipt_id,
        task_family=task_family,
        task_set_digest=benchmark.task_set_digest,
        held_out_split_digest=benchmark.held_out_split_digest,
        verifier_digest=benchmark.verifier_digest,
        prompt_topology_digest=benchmark.prompt_topology_digest,
        issued_at=1000,
        expires_at=2000,
        nonce="nonce:benchmark",
        signature="signature:benchmark",
    )
    promotion_sig = build_model_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.PROMOTION_AUTHORITY,
        signer_public_key="pub:promotion",
        signer_key_fingerprint="fingerprint:promotion",
        key_epoch="epoch-1",
        subject_type=ModelEvidenceSubjectType.MODEL,
        model_or_panel_subject=model_id,
        catalog_snapshot_id="model_catalog_snapshot:pending",
        selection_receipt_id="model_selection_receipt:pending",
        benchmark_run_receipt_id="model_combination_benchmark_run:1",
        benchmark_evidence_receipt_id=benchmark.receipt_id,
        task_family=task_family,
        task_set_digest=benchmark.task_set_digest,
        held_out_split_digest=benchmark.held_out_split_digest,
        verifier_digest=benchmark.verifier_digest,
        prompt_topology_digest=benchmark.prompt_topology_digest,
        promotion_evidence_receipt_id=promotion_receipt.receipt_id,
        promotion_policy_digest="sha256:promotion-policy",
        issued_at=1000,
        expires_at=2000,
        nonce="nonce:promotion",
        signature="signature:promotion",
    )
    evidence = VerifiedModelProductionEvidence(
        entries=(
            VerifiedModelEvidenceEntry(
                model_id=model_id,
                benchmark_receipt=benchmark,
                promotion_receipt=promotion_receipt,
                benchmark_signature_receipt=benchmark_sig,
                promotion_signature_receipt=promotion_sig,
            ),
        )
    )
    snapshot = build_model_catalog_snapshot(
        (
            ModelCapabilityCard(
                provider="openai",
                model_id=model_id,
                canonical_model_id=model_id,
                source="test",
                availability=Availability.AVAILABLE,
                promotion_state=PromotionState.CHAMPION,
                task_families=(task_family,),
                supports_structured_output=True,
                supports_reasoning=True,
                verifier_pass_rate=1.0,
                benchmark_scores={task_family: 1.0},
            ),
        ),
        generated_at=NOW,
    )
    receipt = select_models_for_task(
        snapshot,
        ModelTaskRequirements(
            task_family=task_family,
            purpose=purpose,
            selection_mode=SelectionMode.SINGLE,
            require_structured_output=True,
            require_reasoning=True,
            min_verifier_pass_rate=0.8,
        ),
        production_evidence=evidence if purpose == SelectionPurpose.PRODUCTION else None,
    )
    assert receipt.decision.value == "selected"
    return json.loads(json.dumps(receipt.to_dict(), sort_keys=True))


def _promote(**overrides: Any):
    store = overrides.pop("store", InMemoryAuthoritativeWorkStateStore(_work_state()))
    args = {
        "architect_determination": _determination(),
        "work_state_store": store,
        "authority_profile": _authority_profile(),
        "model_selection_receipt": _model_selection(),
        "memex_supply_receipt": _memex_supply(),
        "worker_id": "reddog-worker-1",
        "now_iso": NOW,
    }
    args.update(overrides)
    return promotion.promote_reddog_architect_fix_to_signed_wsp15_work_order(**args), store


def test_promotes_fix_determination_to_queue_item_and_authority_profile() -> None:
    result, store = _promote()

    assert result.accepted is True
    assert result.status == promotion.ARCHITECT_FIX_WSP15_PROMOTION_ACCEPT
    assert result.receipt is not None
    assert result.receipt.model_selection_receipt_id.startswith("model_selection_receipt:")
    assert result.receipt.memex_supply_receipt_id == "sha256:memex-supply"
    assert result.authority_profile is not None
    assert result.authority_profile["wsp15_allocation_receipt"]["receipt_id"] == _allocation()["receipt_id"]
    assert result.authority_profile["operational_context_binding"]["model_selection_receipt_id"] == (
        result.receipt.model_selection_receipt_id
    )
    assert result.authority_profile["operational_context_binding"]["memex_supply_receipt_id"] == (
        result.receipt.memex_supply_receipt_id
    )

    snapshot = store.load()
    assert len(snapshot["worker_claims"]) == 1
    assert len(snapshot["wre_queue_items"]) == 1
    queue_result = plan_reddog_wre_queue_consumer_dry_run(
        snapshot,
        now_iso="2026-07-16T00:10:00+00:00",
    )
    assert queue_result.accepted is True
    assert queue_result.status == WRE_QUEUE_CONSUMER_DRYRUN_READY
    assert queue_result.selected_slice == "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1"


def test_rejects_non_fix_determination_without_store_mutation() -> None:
    store = InMemoryAuthoritativeWorkStateStore(_work_state())
    before = store.load()

    result, _ = _promote(
        store=store,
        architect_determination=_determination(action=ACTION_RESEARCH_MORE),
    )

    assert result.accepted is False
    assert promotion.ArchitectFixPromotionReason.DETERMINATION_NOT_FIX in result.rejection_reasons
    assert store.load() == before


def test_rejects_missing_model_selection_before_store_mutation() -> None:
    store = InMemoryAuthoritativeWorkStateStore(_work_state())

    result, _ = _promote(store=store, model_selection_receipt={})

    assert result.accepted is False
    assert promotion.ArchitectFixPromotionReason.MODEL_SELECTION_MISSING in result.rejection_reasons
    assert store.load()["wre_queue_items"] == []


def test_rejects_evaluation_model_selection_for_signed_work_order_promotion() -> None:
    result, _ = _promote(model_selection_receipt=_model_selection(purpose=SelectionPurpose.EVALUATION))

    assert result.accepted is False
    assert promotion.ArchitectFixPromotionReason.MODEL_SELECTION_NOT_PRODUCTION in result.rejection_reasons


def test_rejects_missing_memex_supply_receipt() -> None:
    result, _ = _promote(memex_supply_receipt={})

    assert result.accepted is False
    assert promotion.ArchitectFixPromotionReason.MEMEX_SUPPLY_MISSING in result.rejection_reasons


def test_rejects_duplicate_active_queue_item_for_same_determination() -> None:
    first, store = _promote()
    assert first.accepted is True

    second, _ = _promote(store=store)

    assert second.accepted is False
    assert promotion.ArchitectFixPromotionReason.DUPLICATE_QUEUE_ITEM in second.rejection_reasons
    assert len(store.load()["wre_queue_items"]) == 1


def test_rejects_conflicting_wsp15_allocation_before_store_mutation() -> None:
    allocation = _allocation()
    determination = _determination(allocation=allocation)
    tampered = dict(determination)
    tampered["wsp15_allocation_digest"] = "sha256:wrong"

    result, store = _promote(architect_determination=tampered)

    assert result.accepted is False
    assert promotion.ArchitectFixPromotionReason.WSP15_ALLOCATION_MISMATCH in result.rejection_reasons
    assert store.load()["wre_queue_items"] == []


def test_store_commit_failure_fails_closed() -> None:
    store = InMemoryAuthoritativeWorkStateStore(_work_state(), fail_commit=True)

    result, _ = _promote(store=store)

    assert result.accepted is False
    assert promotion.ArchitectFixPromotionReason.STORE_REJECTED in result.rejection_reasons


def test_module_has_no_shell_execution_worker_spawn_or_network_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "os",
        "requests",
        "urllib",
        "http",
        "socket",
        "git",
        "gh",
    }
    banned_fragments = {
        "openclaw_supervisor",
        "hermes",
        "worktree",
        "draft_pr",
        "pattern_memory",
        "holo_indexer",
    }
    banned_calls = {"eval", "exec", "compile", "__import__", "open"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned_import_roots
                assert not any(fragment in alias.name for fragment in banned_fragments)
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert module.split(".")[0] not in banned_import_roots
            assert not any(fragment in module for fragment in banned_fragments)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls


def test_result_is_json_serializable() -> None:
    result, _ = _promote()

    json.dumps(result.to_dict(), sort_keys=True)
    assert result.no_worker_spawn_performed is True
    assert result.no_worktree_created is True
    assert result.no_shell_command_executed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_holoindex_reindex_performed is True
    assert result.receipt is not None
    assert result.receipt.no_repo_mutation_performed is True
    assert result.receipt.authoritative_work_state_mutation_performed is True
