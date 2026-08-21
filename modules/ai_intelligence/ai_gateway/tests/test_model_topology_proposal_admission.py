from __future__ import annotations

import copy

import pytest

from modules.ai_intelligence.ai_gateway.src.model_intelligence_catalog import (
    Availability,
    ModelCapabilityCard,
    PromotionState,
    build_model_catalog_snapshot,
)
from modules.ai_intelligence.ai_gateway.src.model_combination_benchmark_harness import (
    ModelBenchmarkTask,
    ModelBenchmarkTaskOutput,
    ModelBenchmarkVerifierResult,
    run_model_combination_benchmark,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    ModelOutcomeMetrics,
    VerifierDecision,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import (
    ModelTaskRequirements,
    SelectionMode,
    SelectionPurpose,
)
from modules.ai_intelligence.ai_gateway.src.model_topology_proposal_admission import (
    PROPOSAL_SCHEMA_VERSION,
    ModelTopologyProposalReason,
    admit_model_topology_proposal,
    model_task_requirements_digest,
    rehydrate_model_topology_proposal_admission_receipt,
)


MODELS = (
    "z-ai/glm-5.2",
    "qwen/qwen3.8-max",
    "deepseek/deepseek-v4-pro",
    "moonshotai/kimi-k3",
    "nvidia/nemotron-3.5-lightning",
)
ROLES = ("principal", "critic_1", "critic_2", "critic_3")


def _snapshot():
    return build_model_catalog_snapshot(
        [
            ModelCapabilityCard(
                provider="openrouter",
                model_id=model_id,
                canonical_model_id=model_id,
                source="test_live_catalog",
                availability=Availability.AVAILABLE,
                promotion_state=PromotionState.CANDIDATE,
                task_families=("architecture",),
                context_window=1_000_000,
                supports_tools=True,
                supports_structured_output=True,
                supports_reasoning=True,
            )
            for model_id in MODELS
        ],
        generated_at="2026-08-21T00:00:00+00:00",
    )


def _requirements(*, purpose=SelectionPurpose.EVALUATION):
    return ModelTaskRequirements(
        task_family="architecture",
        selection_mode=SelectionMode.PANEL,
        purpose=purpose,
        min_context_window=200_000,
        require_tools=True,
        require_structured_output=True,
        require_reasoning=True,
        allowed_providers=("openrouter",),
        max_candidates=4,
        panel_roles=ROLES,
    )


def _proposal(snapshot, requirements):
    topologies = (
        MODELS[:4],
        (MODELS[1], MODELS[0], MODELS[2], MODELS[3]),
        (MODELS[4], MODELS[0], MODELS[1], MODELS[2]),
    )
    return {
        "schema_version": PROPOSAL_SCHEMA_VERSION,
        "catalog_snapshot_id": snapshot.snapshot_id,
        "requirements_digest": model_task_requirements_digest(requirements),
        "candidates": [
            {
                "role_assignments": [
                    {"role": role, "model_id": model_id, "provider": "openrouter"}
                    for role, model_id in zip(ROLES, topology)
                ]
            }
            for topology in topologies
        ],
    }


def test_admits_only_shadow_candidates_for_autoresearch():
    snapshot = _snapshot()
    requirements = _requirements()
    receipt = admit_model_topology_proposal(
        catalog_snapshot=snapshot,
        requirements=requirements,
        proposer_model_id="nvidia/nemotron-3.5-lightning",
        proposal=_proposal(snapshot, requirements),
    )

    assert receipt.accepted is True
    assert receipt.shadow_only is True
    assert receipt.rejection_reasons == ()
    assert len(receipt.accepted_candidates) == 4
    assert receipt.deterministic_selection_receipt_id.startswith("model_selection_receipt:")
    assert tuple(
        assignment.model_id for assignment in receipt.accepted_candidates[0].role_assignments
    ) == receipt.deterministic_selected_model_ids
    assert all(candidate.topology_digest for candidate in receipt.accepted_candidates)

    restored = rehydrate_model_topology_proposal_admission_receipt(receipt.to_dict())
    assert restored == receipt


def test_admitted_candidates_feed_existing_held_out_benchmark_harness():
    snapshot = _snapshot()
    requirements = _requirements()
    admission = admit_model_topology_proposal(
        catalog_snapshot=snapshot,
        requirements=requirements,
        proposer_model_id="nvidia/nemotron-3.5-lightning",
        proposal=_proposal(snapshot, requirements),
    )
    tasks = (
        ModelBenchmarkTask(
            task_id="architecture-heldout-001",
            task_family="architecture",
            prompt_digest="sha256:prompt-a",
            expected_output_digest="sha256:expected-a",
            verifier_contract_digest="sha256:verifier-contract",
        ),
        ModelBenchmarkTask(
            task_id="architecture-heldout-002",
            task_family="architecture",
            prompt_digest="sha256:prompt-b",
            expected_output_digest="sha256:expected-b",
            verifier_contract_digest="sha256:verifier-contract",
        ),
    )

    def runner(task, candidate):
        return ModelBenchmarkTaskOutput(
            output_digest=f"sha256:{candidate.candidate_id}:{task.task_id}",
            runner_receipt_id=f"runner:{candidate.candidate_id}:{task.task_id}",
            metrics=ModelOutcomeMetrics(
                latency_ms=100,
                input_tokens=10,
                output_tokens=5,
                cost_estimate_usd=0.01,
            ),
        )

    def verifier(task, candidate, output):
        return ModelBenchmarkVerifierResult(
            decision=VerifierDecision.ACCEPT,
            verifier_receipt_id=f"verifier:{candidate.candidate_id}:{task.task_id}",
            evidence_correct=bool(output.output_digest),
        )

    run = run_model_combination_benchmark(
        tasks=tasks,
        candidates=admission.accepted_candidates,
        runner=runner,
        verifier=verifier,
        verifier_digest="sha256:independent-verifier",
        held_out_split_id="reddog-topology-heldout-v1",
    )

    assert admission.accepted is True
    assert len(run.benchmark_evidence_receipts) == len(admission.accepted_candidates)
    incumbent = next(
        item
        for item in run.candidates
        if item.candidate_id == admission.accepted_candidates[0].candidate_id
    )
    assert tuple(
        item.model_id for item in incumbent.role_assignments
    ) == admission.deterministic_selected_model_ids
    assert all(item.sample_count == len(tasks) for item in run.benchmark_evidence_receipts)


def test_rejects_model_not_in_gateway_eligible_set():
    snapshot = _snapshot()
    requirements = _requirements()
    proposal = _proposal(snapshot, requirements)
    proposal["candidates"][0]["role_assignments"][1]["model_id"] = "invented/model"

    receipt = admit_model_topology_proposal(
        catalog_snapshot=snapshot,
        requirements=requirements,
        proposer_model_id=MODELS[-1],
        proposal=proposal,
    )

    assert receipt.accepted is False
    assert receipt.accepted_candidates == ()
    assert ModelTopologyProposalReason.MODEL_NOT_ELIGIBLE in receipt.rejection_reasons


def test_rejects_provider_or_role_substitution():
    snapshot = _snapshot()
    requirements = _requirements()
    proposal = _proposal(snapshot, requirements)
    proposal["candidates"][0]["role_assignments"][0]["provider"] = "lm_studio"
    proposal["candidates"][1]["role_assignments"][1]["role"] = "verifier"

    receipt = admit_model_topology_proposal(
        catalog_snapshot=snapshot,
        requirements=requirements,
        proposer_model_id=MODELS[-1],
        proposal=proposal,
    )

    assert receipt.accepted is False
    assert ModelTopologyProposalReason.PROVIDER_MISMATCH in receipt.rejection_reasons
    assert ModelTopologyProposalReason.ROLE_TOPOLOGY_MISMATCH in receipt.rejection_reasons


def test_rejects_direct_production_proposal():
    snapshot = _snapshot()
    requirements = _requirements(purpose=SelectionPurpose.PRODUCTION)
    proposal = _proposal(snapshot, requirements)

    receipt = admit_model_topology_proposal(
        catalog_snapshot=snapshot,
        requirements=requirements,
        proposer_model_id=MODELS[-1],
        proposal=proposal,
    )

    assert receipt.accepted is False
    assert ModelTopologyProposalReason.PRODUCTION_NOT_ALLOWED in receipt.rejection_reasons


def test_rejects_catalog_requirements_tamper_and_oversize():
    snapshot = _snapshot()
    requirements = _requirements()
    proposal = _proposal(snapshot, requirements)
    proposal["catalog_snapshot_id"] = "model_catalog_snapshot:wrong"
    proposal["requirements_digest"] = "model_task_requirements:wrong"
    proposal["ignored_prose"] = "x" * 70_000

    receipt = admit_model_topology_proposal(
        catalog_snapshot=snapshot,
        requirements=requirements,
        proposer_model_id=MODELS[-1],
        proposal=proposal,
    )

    assert receipt.accepted is False
    assert ModelTopologyProposalReason.PAYLOAD_TOO_LARGE in receipt.rejection_reasons
    assert ModelTopologyProposalReason.CATALOG_MISMATCH in receipt.rejection_reasons
    assert ModelTopologyProposalReason.REQUIREMENTS_MISMATCH in receipt.rejection_reasons


def test_rehydration_rejects_tampered_receipt():
    snapshot = _snapshot()
    requirements = _requirements()
    receipt = admit_model_topology_proposal(
        catalog_snapshot=snapshot,
        requirements=requirements,
        proposer_model_id=MODELS[-1],
        proposal=_proposal(snapshot, requirements),
    )
    payload = copy.deepcopy(receipt.to_dict())
    payload["deterministic_selected_model_ids"].reverse()

    with pytest.raises(
        ValueError,
        match="model_topology_proposal_admission_receipt_id_mismatch",
    ):
        rehydrate_model_topology_proposal_admission_receipt(payload)
