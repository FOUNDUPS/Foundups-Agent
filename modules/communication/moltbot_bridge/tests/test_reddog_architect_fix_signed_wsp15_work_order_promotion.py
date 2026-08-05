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
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding import (
    ModelRuntimeBindingPolicy,
    RUNTIME_BINDING_SCHEMA_VERSION,
    _digest_prefixed,
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
from modules.communication.moltbot_bridge.src import (
    reddog_architect_proposal_executability_admission as proposal_admission,
)
from modules.communication.moltbot_bridge.src.reddog_architect_proposal_executability_admission import (
    LIVE_EXECUTION_CAPABILITIES,
)
from modules.communication.moltbot_bridge.tests.architect_proposal_promotion_test_helpers import (
    PRINCIPAL_PUBLIC_KEY as _PRINCIPAL_PUBLIC_KEY,
    REDDOG_PUBLIC_KEY as _REDDOG_PUBLIC_KEY,
    build_proposal_runtime_inputs,
    invoke_promotion_with_test_authority,
    seal_authority_profile,
)
from modules.communication.moltbot_bridge.tests.architect_proposal_test_helpers import ready_proposal_policy
from modules.communication.moltbot_bridge.tests.holoindex_freshness_receipt_test_helpers import (
    build_fresh_holoindex_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    verified_runtime_binding_receipt,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_runtime_binding_test_capability,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_consumer_dryrun import (
    WRE_QUEUE_CONSUMER_DRYRUN_READY,
    plan_reddog_wre_queue_consumer_dry_run,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
    canonical_reddog_wsp15_allocation_digest,
)
from modules.communication.moltbot_bridge.src.reddog_operational_memex_supply_receipt import (
    canonical_operational_memex_supply_digest,
    operational_memex_supply_receipt_id,
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
REPO_HEAD = "sha256:repo-head"
NOW_EPOCH = 1_784_160_000


def _holo_receipt():
    return build_fresh_holoindex_receipt(
        repo_root=REPO_ROOT,
        head_sha=REPO_HEAD,
        generated_at=NOW,
    )


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


def _proposal_admission(
    allocation: Mapping[str, Any],
    *,
    admissible: bool = True,
    readiness: str = "READY",
) -> dict[str, Any]:
    holo_receipt = _holo_receipt()
    policy = ready_proposal_policy()
    payload = {
        "schema_version": proposal_admission.PROPOSAL_ADMISSION_SCHEMA_VERSION,
        "accepted": True,
        "proposal_validity": "VALID",
        "execution_readiness": readiness,
        "admissible_to_authoritative_queue": admissible,
        "action": ACTION_FIX,
        "slice_id": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
        "task_summary_digest": "sha256:task-summary",
        "reuse_decision": "EXTEND_EXISTING",
        "requested_operation": "bounded_code_change",
        "target_runtime": "reddog_resident_queue",
        "target_effect_plane": "REPOSITORY_CODE_CHANGE",
        "allowed_paths": [
            "modules/communication/moltbot_bridge/src/reddog_next_operational_slice.py"
        ],
        "denied_paths": [".github/workflows/**", ".env"],
        "required_tests": [
            "pytest modules/communication/moltbot_bridge/tests/test_reddog_next_operational_slice.py"
        ],
        "required_policy_gates": ["WSP_50", "WSP_97"],
        "required_capabilities": list(LIVE_EXECUTION_CAPABILITIES),
        "produced_capabilities": [],
        "expected_evidence": ["exact_sha_test_receipt"],
        "stop_conditions": ["stop_before_merge"],
        "missing_preconditions": (
            [] if admissible else ["canonical_signer_client_peer_handshake_verifier_missing"]
        ),
        "decision_reasons": [],
        "supporting_finding_ids": ["repo-code-audit-finding"],
        "supporting_direct_read_paths": [],
        "snapshot_receipt_id": SNAPSHOT_ID,
        "snapshot_content_digest": "sha256:" + ("b" * 64),
        "repo_head_sha": REPO_HEAD,
        "work_state_revision": "sha256:work-state-rev-1",
        "holoindex_generation_id": holo_receipt.generation_id,
        "holoindex_freshness_receipt_digest": proposal_admission._digest(
            holo_receipt.to_dict()
        ),
        "index_gap_detected": False,
        "direct_read_grounded": False,
        "holoindex_maintenance_exception_applied": False,
        "report_bundle_id": "sha256:report-bundle",
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "wsp15_allocation_digest": canonical_reddog_wsp15_allocation_digest(
            allocation
        ),
        "policy_digest": proposal_admission._digest(policy.to_dict()),
        "conversation_binding_present": False,
        "conversation_binding_digest": "",
        "conversation_id": "",
        "conversation_revision": -1,
        "conversation_revision_receipt_id": "",
        "conversation_scope_record_digest": "",
        "authorized_foundup_id": "",
        "resident_intent_id": "",
        "resident_intent_digest": "",
        "conversation_grounding_receipt_id": "",
        "rejection_reasons": [],
        "no_queue_mutation_performed": True,
        "no_execution_performed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
    }
    payload["receipt_id"] = proposal_admission._digest(payload)
    return payload


def _determination(
    *,
    action: str = ACTION_FIX,
    allocation: Mapping[str, Any] | None = None,
    proposal_ready: bool = True,
) -> dict[str, Any]:
    allocation = allocation or _allocation()
    admission = _proposal_admission(
        allocation,
        admissible=proposal_ready,
        readiness="READY" if proposal_ready else "IMPLEMENTATION_BLOCKED",
    )
    next_slice = (
        "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1"
        if action == ACTION_FIX
        else None
    )
    base = {
        "schema_version": "reddog_architect_determination_receipt.v1",
        "cycle_id": "sha256:cycle-1",
        "accepted": True,
        "status": ARCHITECT_DETERMINATION_ACCEPT,
        "action": action,
        "next_slice_name": next_slice,
        "summary": "Promote one verified FIX slice.",
        "snapshot_receipt_id": SNAPSHOT_ID,
        "snapshot_content_digest": "sha256:" + ("b" * 64),
        "context_view_id": "sha256:context-view",
        "evidence_bundle_id": "sha256:evidence-bundle",
        "report_bundle_id": "sha256:report-bundle",
        "report_count": 5,
        "audit_report_digests": ["sha256:report-1"],
        "model_result_digest": "sha256:model-result",
        "model_receipt_id": "model-receipt-1",
        "model_selection_receipt_id": None,
        "model_selection_digest": None,
        "model_runtime_binding_receipt_id": None,
        "model_runtime_binding_digest": None,
        "provider_call_id": None,
        "provider_call_receipt_id": None,
        "provider_call_evidence_digest": None,
        "fusion_quorum_passed": True,
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "wsp15_allocation_digest": canonical_reddog_wsp15_allocation_digest(
            allocation
        ),
        "decision_reasons": ["FIX is the next verified bridge."],
        "rejection_reasons": [],
    }
    determination_id = proposal_admission._digest(
        {
            "cycle_id": base["cycle_id"],
            "action": base["action"],
            "next_slice_name": base["next_slice_name"],
            "model_result_digest": base["model_result_digest"],
            "model_selection_digest": base["model_selection_digest"],
            "provider_call_id": base["provider_call_id"],
            "provider_call_receipt_id": base["provider_call_receipt_id"],
            "provider_call_evidence_digest": base[
                "provider_call_evidence_digest"
            ],
            "proposal_admission_receipt_id": admission["receipt_id"],
        }
    )
    candidate_seed = {
        "source_determination_receipt_id": determination_id,
        "slice_id": next_slice,
        "snapshot_receipt_id": SNAPSHOT_ID,
        "report_bundle_id": base["report_bundle_id"],
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "proposal_admission_receipt_id": admission["receipt_id"],
    }
    candidate = {
        "schema_version": ARCHITECT_QUEUE_CANDIDATE_SCHEMA_VERSION,
        "queue_candidate_id": proposal_admission._digest(candidate_seed),
        "source_determination_receipt_id": determination_id,
        "slice_id": next_slice,
        "status": "CANDIDATE" if proposal_ready else "BLOCKED_CANDIDATE",
        "evidence_refs": ["file:docs/audit.md:1"],
        "wsp15_allocation_receipt": dict(allocation),
        "proposal_admission_receipt_id": admission["receipt_id"],
        "proposal_admission_digest": proposal_admission._digest(admission),
        "no_queue_mutation_performed": True,
        "no_execution_performed": True,
        "no_worker_spawn_performed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_repo_mutation_performed": True,
    }
    return {
        **base,
        "determination_receipt_id": determination_id,
        "proposal_admission": admission if action == ACTION_FIX else None,
        "queue_candidate": candidate if action == ACTION_FIX else None,
    }


def _rebind_determination_admission(
    determination: Mapping[str, Any],
    admission_updates: Mapping[str, Any],
) -> dict[str, Any]:
    rebound = json.loads(json.dumps(determination, sort_keys=True))
    admission = dict(rebound["proposal_admission"])
    admission.update(admission_updates)
    admission.pop("receipt_id", None)
    admission["receipt_id"] = proposal_admission._digest(admission)
    determination_seed = {
        "cycle_id": rebound.get("cycle_id"),
        "action": rebound.get("action"),
        "next_slice_name": rebound.get("next_slice_name"),
        "model_result_digest": rebound.get("model_result_digest"),
        "model_selection_digest": rebound.get("model_selection_digest"),
        "provider_call_id": rebound.get("provider_call_id"),
        "provider_call_receipt_id": rebound.get("provider_call_receipt_id"),
        "provider_call_evidence_digest": rebound.get(
            "provider_call_evidence_digest"
        ),
        "proposal_admission_receipt_id": admission["receipt_id"],
    }
    determination_id = proposal_admission._digest(determination_seed)
    candidate = dict(rebound["queue_candidate"])
    candidate["source_determination_receipt_id"] = determination_id
    candidate["proposal_admission_receipt_id"] = admission["receipt_id"]
    candidate["proposal_admission_digest"] = proposal_admission._digest(admission)
    candidate["queue_candidate_id"] = proposal_admission._digest(
        {
            "source_determination_receipt_id": determination_id,
            "slice_id": candidate["slice_id"],
            "snapshot_receipt_id": rebound["snapshot_receipt_id"],
            "report_bundle_id": rebound["report_bundle_id"],
            "wsp15_allocation_receipt_id": rebound[
                "wsp15_allocation_receipt_id"
            ],
            "proposal_admission_receipt_id": admission["receipt_id"],
        }
    )
    rebound["proposal_admission"] = admission
    rebound["determination_receipt_id"] = determination_id
    rebound["queue_candidate"] = candidate
    return rebound


def _authority_profile(**overrides: Any) -> dict[str, Any]:
    profile = {
        "principal_id": "github:mjtrout",
        "principal_provider": "github",
        "principal_public_key": _PRINCIPAL_PUBLIC_KEY,
        "reddog_id": "reddog:architect",
        "reddog_public_key": _REDDOG_PUBLIC_KEY,
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "foundup_id": "paccess_001",
        "base_ref": "main",
        "allowed_paths": ["modules/communication/moltbot_bridge/**"],
        "denied_paths": ["modules/communication/moltbot_bridge/secrets/**"],
        "requested_operation": "feature_slice",
        "permission_snapshot_digest": "sha256:" + ("a" * 64),
        "identity_nonce": "identity-nonce-1",
        "work_authority_nonce": "workauth-nonce-1",
        "issued_at": 1000,
        "identity_expires_at": 4600,
        "work_authority_expires_at": 1300,
        "valve_state_required": "VALVE_OPEN_WORKTREE_CREATE",
        "key_epoch": "epoch-1",
        "consensus_receipt_digest": "sha256:" + ("c" * 64),
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
    return seal_authority_profile(profile)


def _memex_supply(**overrides: Any) -> dict[str, Any]:
    payload = {
        "schema_version": "reddog_operational_memex_snapshot_supply_receipt.v1",
        "foundup_id": "paccess_001",
        "principal_id": "github:mjtrout",
        "snapshot_receipt_id": SNAPSHOT_ID,
        "snapshot_content_digest": "sha256:" + ("b" * 64),
        "memex_view_id": "memex-view-1",
        "holoindex_generation_id": _holo_receipt().generation_id,
        "source_revision": _work_state()["revision"],
        "policy_issued_at": "2026-07-15T23:59:50+00:00",
        "policy_expires_at": "2026-07-16T00:09:50+00:00",
        "assignment_count": 1,
        "assignment_ids": ["assignment-1"],
        "lane_ids": ["repo_code_audit"],
        "task_ids": ["task-1"],
        "assignment_receipt_ids": ["sha256:assignment-receipt-1"],
        "max_records": 32,
        "no_memex_write_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_repo_mutation_performed": True,
    }
    supplied_receipt_id = overrides.pop("receipt_id", None)
    payload.update(overrides)
    payload["receipt_id"] = supplied_receipt_id or operational_memex_supply_receipt_id(
        payload
    )
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


def _runtime_binding(
    model_selection: Mapping[str, Any] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    selection = dict(model_selection or _model_selection())
    requirements = dict(selection["requirements"])
    selected_models = tuple(str(model_id) for model_id in selection["selected_model_ids"])
    principal_model = selected_models[0]
    policy = ModelRuntimeBindingPolicy(
        task_family=str(requirements["task_family"]),
        runtime_surface="reddog_artifact_generation",
        min_verifier_pass_rate=0.8,
        required_task_set_digest="sha256:task-set",
        required_held_out_split_digest="sha256:held-out",
        required_verifier_digest="sha256:verifier",
        authority_receipt_id="runtime-authority:architect-fix",
    ).to_dict()
    body = {
        "schema_version": RUNTIME_BINDING_SCHEMA_VERSION,
        "decision": "bound",
        "runtime_surface": policy["runtime_surface"],
        "catalog_snapshot_id": str(selection["catalog_snapshot_id"]),
        "selection_receipt_id": str(selection["receipt_id"]),
        "task_family": str(requirements["task_family"]),
        "principal_model": principal_model,
        "panel_models": [],
        "role_bindings": [
            {
                "role": "principal",
                "model_id": principal_model,
                "provider": principal_model.split("/", 1)[0],
            }
        ],
        "benchmark_evidence_receipt_ids": ["model_benchmark_evidence:architect-fix"],
        "promotion_evidence_receipt_ids": ["model_promotion_evidence:architect-fix"],
        "signed_promotion_receipt_ids": ["signature:promotion"],
        "policy": policy,
        "rejection_reasons": [],
    }
    body.update(overrides)
    body["receipt_id"] = _digest_prefixed("reddog_model_runtime_binding", body)
    return json.loads(json.dumps(body, sort_keys=True))


def _promote(**overrides: Any):
    store = overrides.pop("store", InMemoryAuthoritativeWorkStateStore(_work_state()))
    test_now_epoch = overrides.pop("_test_now_epoch", NOW_EPOCH)

    def publish(request):
        return store.commit(
            request.updated_work_state,
            expected_revision=request.expected_work_state_revision,
        )

    args = {
        "architect_determination": _determination(),
        "work_state_store": store,
        "authority_profile": _authority_profile(),
        "model_selection_receipt": _model_selection(),
        "memex_supply_receipt": _memex_supply(),
        "worker_id": "reddog-worker-1",
        "now_iso": NOW,
        "current_repo_head_sha": REPO_HEAD,
        "current_holoindex_receipt": _holo_receipt(),
        "authority_profile_publication_publisher": publish,
    }
    runtime_binding = overrides.get("model_runtime_binding_receipt")
    selection = overrides.get("model_selection_receipt", args["model_selection_receipt"])
    verification = (
        verified_runtime_binding_receipt(runtime_binding)
        if isinstance(runtime_binding, Mapping)
        else None
    )
    if verification is not None:
        overrides["model_runtime_binding_verification_capability"] = (
            model_runtime_binding_test_capability(selection, runtime_binding)
        )
    result = invoke_promotion_with_test_authority(
        promotion.promote_reddog_architect_fix_to_signed_wsp15_work_order,
        args=args,
        overrides=overrides,
        now_epoch=test_now_epoch,
    )
    return result, store


def test_promotes_fix_determination_to_queue_item_and_authority_profile() -> None:
    result, store = _promote()

    assert result.accepted is True
    assert result.status == promotion.ARCHITECT_FIX_WSP15_PROMOTION_ACCEPT
    assert result.receipt is not None
    assert result.receipt.model_selection_receipt_id.startswith("model_selection_receipt:")
    assert result.receipt.memex_supply_receipt_id == _memex_supply()["receipt_id"]
    assert result.authority_profile is not None
    assert result.authority_profile["wsp15_allocation_receipt"]["receipt_id"] == _allocation()["receipt_id"]
    assert result.authority_profile["model_selection_receipt"]["receipt_id"] == (
        result.receipt.model_selection_receipt_id
    )
    assert result.authority_profile["operational_context_binding"]["model_selection_receipt_id"] == (
        result.receipt.model_selection_receipt_id
    )
    assert result.authority_profile["operational_context_binding"]["model_selection_receipt"]["receipt_id"] == (
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


def test_promotion_receipt_and_state_bind_agentdb_claim_fence() -> None:
    determination = _determination()
    fence = {
        "schema_version": "reddog_fix_promotion_claim_fence.v1",
        "agentdb_claim_id": "sha256:agentdb-claim",
        "lease_id": "lease:one",
        "lease_owner": "reddog-main",
        "claim_revision": 3,
        "determination_id": determination["determination_receipt_id"],
        "queue_candidate_id": determination["queue_candidate"]["queue_candidate_id"],
        "wsp15_allocation_receipt_id": _allocation()["receipt_id"],
    }

    result, store = _promote(
        architect_determination=determination,
        agentdb_fix_promotion_claim_fence=fence,
    )

    assert result.accepted is True
    assert result.receipt.agentdb_fix_promotion_claim_id == fence["agentdb_claim_id"]
    assert result.receipt.agentdb_fix_promotion_claim_revision == 3
    assert result.receipt.agentdb_fix_promotion_claim_fence_digest.startswith("sha256:")
    record = store.load()["architect_fix_promotions"][0]
    assert record["agentdb_fix_promotion_claim_id"] == fence["agentdb_claim_id"]
    assert (
        record["agentdb_fix_promotion_claim_fence_digest"]
        == result.receipt.agentdb_fix_promotion_claim_fence_digest
    )


def test_promotion_rejects_caller_supplied_work_order_id() -> None:
    result, _ = _promote(authority_profile=_authority_profile(work_order_id="caller-controlled"))

    assert result.accepted is False
    assert any(
        "unknown_field:work_order_id" in reason
        for reason in result.rejection_reasons
    )


def test_rejects_runtime_binding_for_different_model_selection_without_store_mutation() -> None:
    model_selection = _model_selection()
    runtime_binding = _runtime_binding(
        model_selection,
        selection_receipt_id="model_selection_receipt:different",
    )
    store = InMemoryAuthoritativeWorkStateStore(_work_state())

    result, _ = _promote(
        store=store,
        model_selection_receipt=model_selection,
        model_runtime_binding_receipt=runtime_binding,
    )

    assert result.accepted is False
    assert promotion.ArchitectFixPromotionReason.MODEL_RUNTIME_BINDING_MISMATCH in result.rejection_reasons
    assert store.load()["wre_queue_items"] == []


def test_rejects_unbound_runtime_binding_without_store_mutation() -> None:
    model_selection = _model_selection()
    runtime_binding = _runtime_binding(
        model_selection,
        decision="rejected",
        principal_model=None,
        role_bindings=[],
        rejection_reasons=["missing_verified_production_evidence"],
    )
    store = InMemoryAuthoritativeWorkStateStore(_work_state())

    result, _ = _promote(
        store=store,
        model_selection_receipt=model_selection,
        model_runtime_binding_receipt=runtime_binding,
    )

    assert result.accepted is False
    assert promotion.ArchitectFixPromotionReason.MODEL_RUNTIME_BINDING_NOT_BOUND in result.rejection_reasons
    assert store.load()["wre_queue_items"] == []


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


def _signed_inputs_for_memex(receipt: Mapping[str, Any]):
    determination = _determination()
    profile = _authority_profile()
    attestation, runtime_config, resolver = build_proposal_runtime_inputs(
        determination,
        profile,
        receipt,
        now_epoch=NOW_EPOCH,
    )
    return determination, profile, attestation, runtime_config, resolver


def test_fabricated_sha256_memex_id_rejects_before_state_mutation() -> None:
    original = _memex_supply()
    determination, profile, attestation, runtime_config, resolver = (
        _signed_inputs_for_memex(original)
    )
    forged = {**original, "receipt_id": "sha256:" + ("a" * 64)}
    store = InMemoryAuthoritativeWorkStateStore(_work_state())
    before = store.load()

    result, _ = _promote(
        store=store,
        architect_determination=determination,
        authority_profile=profile,
        memex_supply_receipt=forged,
        proposal_authenticity_attestation=attestation,
        signer_runtime_config=runtime_config,
        principal_key_resolver=resolver,
    )

    assert result.accepted is False
    assert promotion.ArchitectFixPromotionReason.MEMEX_SUPPLY_INVALID in (
        result.rejection_reasons
    )
    assert store.load() == before


def test_self_rehashed_memex_substitution_rejects_signed_digest_mismatch() -> None:
    original = _memex_supply()
    determination, profile, attestation, runtime_config, resolver = (
        _signed_inputs_for_memex(original)
    )
    substituted = _memex_supply(memex_view_id="attacker-selected-view")
    store = InMemoryAuthoritativeWorkStateStore(_work_state())
    before = store.load()

    result, _ = _promote(
        store=store,
        architect_determination=determination,
        authority_profile=profile,
        memex_supply_receipt=substituted,
        proposal_authenticity_attestation=attestation,
        signer_runtime_config=runtime_config,
        principal_key_resolver=resolver,
    )

    assert result.accepted is False
    assert promotion.ArchitectFixPromotionReason.PROPOSAL_AUTHENTICITY_INVALID in (
        result.rejection_reasons
    )
    assert store.load() == before


def test_promotion_binds_complete_memex_receipt_digest() -> None:
    memex = _memex_supply()
    result, store = _promote(memex_supply_receipt=memex)
    expected = canonical_operational_memex_supply_digest(memex)

    assert result.accepted is True
    assert result.receipt is not None
    assert result.receipt.memex_supply_digest == expected
    assert store.load()["wre_queue_items"][0]["memex_supply_digest"] == expected
    assert result.authority_profile is not None
    assert result.authority_profile["operational_context_binding"][
        "memex_supply_digest"
    ] == expected


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


def test_authenticates_then_promotes_valid_execution_blocked_candidate() -> None:
    store = InMemoryAuthoritativeWorkStateStore(_work_state())

    result, _ = _promote(
        store=store,
        architect_determination=_determination(proposal_ready=False),
    )

    assert result.accepted is True
    assert result.receipt is not None
    assert len(store.load()["wre_queue_items"]) == 1


def test_blocked_candidate_with_forged_authenticity_still_rejects() -> None:
    store = InMemoryAuthoritativeWorkStateStore(_work_state())
    determination = _determination(proposal_ready=False)
    profile = _authority_profile()
    attestation, runtime_config, resolver = build_proposal_runtime_inputs(
        determination,
        profile,
        _memex_supply(),
        now_epoch=NOW_EPOCH,
    )
    forged = dict(attestation)
    forged["signature"] = "forged"

    result, _ = _promote(
        store=store,
        architect_determination=determination,
        authority_profile=profile,
        proposal_authenticity_attestation=forged,
        signer_runtime_config=runtime_config,
        principal_key_resolver=resolver,
    )

    assert result.accepted is False
    assert (
        promotion.ArchitectFixPromotionReason.PROPOSAL_AUTHENTICITY_INVALID
        in result.rejection_reasons
    )
    assert store.load()["wre_queue_items"] == []


def test_rejects_tampered_proposal_admission_before_store_mutation() -> None:
    determination = _determination()
    determination["proposal_admission"]["allowed_paths"] = ["modules/other/**"]
    store = InMemoryAuthoritativeWorkStateStore(_work_state())

    result, _ = _promote(
        store=store,
        architect_determination=determination,
    )

    assert result.accepted is False
    assert (
        promotion.ArchitectFixPromotionReason.PROPOSAL_ADMISSION_INVALID
        in result.rejection_reasons
    )
    assert store.load()["wre_queue_items"] == []


def test_rejects_rehashed_underdeclared_effect_capabilities() -> None:
    determination = _rebind_determination_admission(
        _determination(),
        {"required_capabilities": []},
    )
    store = InMemoryAuthoritativeWorkStateStore(_work_state())

    result, _ = _promote(
        store=store,
        architect_determination=determination,
    )

    assert result.accepted is False
    assert (
        promotion.ArchitectFixPromotionReason.PROPOSAL_ADMISSION_INVALID
        in result.rejection_reasons
    )
    assert store.load()["wre_queue_items"] == []


def test_rejects_noncanonical_queue_candidate_id() -> None:
    determination = _determination()
    determination["queue_candidate"]["queue_candidate_id"] = "sha256:forged"
    store = InMemoryAuthoritativeWorkStateStore(_work_state())

    result, _ = _promote(
        store=store,
        architect_determination=determination,
    )

    assert result.accepted is False
    assert (
        promotion.ArchitectFixPromotionReason.QUEUE_CANDIDATE_MALFORMED
        in result.rejection_reasons
    )
    assert store.load()["wre_queue_items"] == []


def test_rejects_changed_holoindex_generation_before_store_mutation() -> None:
    current = _holo_receipt().to_dict()
    current["generation_id"] = "sha256:different-generation"
    store = InMemoryAuthoritativeWorkStateStore(_work_state())

    result, _ = _promote(
        store=store,
        current_holoindex_receipt=current,
    )

    assert result.accepted is False
    assert (
        promotion.ArchitectFixPromotionReason.HOLOINDEX_BINDING_MISMATCH
        in result.rejection_reasons
    )
    assert store.load()["wre_queue_items"] == []


def test_publication_failure_leaves_authoritative_queue_empty() -> None:
    store = InMemoryAuthoritativeWorkStateStore(_work_state())

    def fail_publication(_request) -> str:
        raise OSError("simulated profile write failure")

    result, _ = _promote(
        store=store,
        authority_profile_publication_publisher=fail_publication,
    )

    assert result.accepted is False
    assert (
        promotion.ArchitectFixPromotionReason.STORE_REJECTED
        in result.rejection_reasons
    )
    assert store.load()["wre_queue_items"] == []
    assert store.load()["worker_claims"] == []


def test_exact_authorized_base_sha_is_bound_across_promotion_outputs() -> None:
    result, store = _promote()

    assert result.accepted is True
    assert result.authority_profile is not None
    assert result.authority_profile["base_ref"] == REPO_HEAD
    assert result.authority_profile["authorized_base_sha"] == REPO_HEAD
    binding = result.authority_profile["operational_context_binding"]
    assert binding["authorized_base_sha"] == REPO_HEAD
    snapshot = store.load()
    assert snapshot["worker_claims"][0]["authorized_base_sha"] == REPO_HEAD
    assert snapshot["wre_queue_items"][0]["authorized_base_sha"] == REPO_HEAD


def test_rejects_changed_repository_head_before_store_mutation() -> None:
    store = InMemoryAuthoritativeWorkStateStore(_work_state())

    result, _ = _promote(
        store=store,
        current_repo_head_sha="sha256:different-head",
    )

    assert result.accepted is False
    assert (
        promotion.ArchitectFixPromotionReason.REPO_HEAD_MISMATCH
        in result.rejection_reasons
    )
    assert store.load()["wre_queue_items"] == []


def test_rejects_changed_work_state_revision_before_store_mutation() -> None:
    changed = _work_state()
    changed["revision"] = "sha256:different-work-state"
    store = InMemoryAuthoritativeWorkStateStore(changed)

    result, _ = _promote(store=store)

    assert result.accepted is False
    assert (
        promotion.ArchitectFixPromotionReason.PROPOSAL_ADMISSION_INVALID
        in result.rejection_reasons
    )
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
