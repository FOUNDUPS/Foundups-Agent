"""Single-model authenticated AutoResearch promotion-to-runtime contracts."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import ast

import pytest

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_authenticated_promotion_authority import (
    AuthenticatedCampaignPromotionSupplyResult,
    CampaignPromotionAuthorityRequest,
    VerifiedCampaignPromotionAuthority,
    build_signed_campaign_promotion_authority_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution import (
    _execution_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_promotion_gate_supply import (
    run_reddog_model_autoresearch_campaign_promotion_gate_supply,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_configured_gateway_evidence import (
    digest_payload,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_single_model_production_binding import (
    bind_authenticated_single_model_promotion_to_runtime,
    build_authenticated_single_model_production_selection_preview,
)
from modules.ai_intelligence.ai_gateway.src.model_combination_benchmark_harness import (
    ModelBenchmarkRoleAssignment,
    ModelBenchmarkTask,
    ModelBenchmarkTaskOutput,
    ModelBenchmarkVerifierResult,
    build_model_benchmark_candidate,
    run_model_combination_benchmark,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_catalog import (
    Availability,
    ModelCapabilityCard,
    PromotionState,
    build_model_catalog_snapshot,
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
from modules.ai_intelligence.ai_gateway.src.model_promotion_gate import (
    ModelPromotionPolicy,
)
from modules.ai_intelligence.ai_gateway.src.model_selection_artifact_supply import (
    EVIDENCE_BUNDLE_SCHEMA_VERSION,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    InMemoryEvidenceNonceStore,
    ModelEvidenceSignerRole,
    StaticModelEvidenceKeyResolver,
)
from modules.ai_intelligence.ai_gateway.tests.model_signed_evidence_test_helpers import (
    BENCHMARK_FINGERPRINT,
    BENCHMARK_PUBLIC_KEY,
    KEY_EPOCH,
    NOW,
    PROMOTION_FINGERPRINT,
    PROMOTION_PUBLIC_KEY,
    DeterministicSignatureVerifier,
    make_signed_evidence_receipt,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "ai_intelligence"
    / "ai_gateway"
    / "src"
    / "model_autoresearch_single_model_production_binding.py"
)
MODEL_ID = "openrouter/z-ai/glm-5.2"
TASK_FAMILY = "architecture"


def _authenticated_gate(tmp_path: Path):
    candidate = build_model_benchmark_candidate(
        (
            ModelBenchmarkRoleAssignment(
                role="principal",
                model_id=MODEL_ID,
                provider="openrouter",
            ),
        )
    )
    task = ModelBenchmarkTask(
        task_id="heldout-001",
        task_family=TASK_FAMILY,
        prompt_digest="sha256:prompt",
        expected_output_digest="sha256:expected",
        verifier_contract_digest="sha256:verifier-contract",
    )
    benchmark_run = run_model_combination_benchmark(
        tasks=(task,),
        candidates=(candidate,),
        runner=lambda _task, _candidate: ModelBenchmarkTaskOutput(
            output_digest="sha256:output",
            runner_receipt_id="runner:1",
            metrics=ModelOutcomeMetrics(latency_ms=10),
        ),
        verifier=lambda _task, _candidate, _output: ModelBenchmarkVerifierResult(
            decision=VerifierDecision.ACCEPT,
            verifier_receipt_id="verifier:1",
            evidence_correct=True,
        ),
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )
    execution = _execution_receipt(
        plan=SimpleNamespace(receipt_id="model_autoresearch_plan:single"),
        benchmark=benchmark_run,
        executed_candidate_ids=(MODEL_ID,),
        skipped_campaign_candidate_ids=(),
    )
    policy = ModelPromotionPolicy(
        task_family=TASK_FAMILY,
        candidate_id=MODEL_ID,
        min_verifier_pass_rate=1.0,
        min_sample_count=1,
        required_task_set_digest=benchmark_run.task_set_digest,
        required_held_out_split_digest=benchmark_run.held_out_split_digest,
        required_verifier_digest=benchmark_run.verifier_digest,
    ).normalized()
    policy_digest = digest_payload([policy.to_dict()])
    request = CampaignPromotionAuthorityRequest(
        request_id="model_autoresearch_promotion_authority_request:single",
        source_execution_receipt_id=execution.receipt_id,
        source_execution_digest=digest_payload(execution.to_dict()),
        proposer_provenance_receipt_id="proposer-provenance:single",
        proposer_provenance_digest="sha256:" + "1" * 64,
        promotion_policy_digest=policy_digest,
        candidate_ids=(MODEL_ID,),
    )
    signed = build_signed_campaign_promotion_authority_receipt(
        request=request,
        signer_public_key="external-public-key:campaign-promotion",
        signer_key_fingerprint="fingerprint:campaign-promotion",
        key_epoch="epoch-1",
        issued_at=NOW - 10,
        expires_at=NOW + 300,
        nonce="nonce:campaign-promotion:single",
        signature="external-signature:campaign-promotion",
    )
    authority = VerifiedCampaignPromotionAuthority(
        request=request,
        receipt=signed,
        durable_store_receipt_id=signed.receipt_id,
    )
    gate_path = tmp_path / "runtime" / "promotion-gate.json"
    supply = run_reddog_model_autoresearch_campaign_promotion_gate_supply(
        repo_root=REPO_ROOT,
        campaign_execution_receipt=execution,
        promotion_policies=(policy,),
        output_path=gate_path,
        promotion_authority_receipt_id=request.request_id,
        signed_promotion_receipt_id=signed.receipt_id,
    )
    assert supply.accepted
    return (
        AuthenticatedCampaignPromotionSupplyResult(authority=authority, supply=supply),
        benchmark_run.benchmark_evidence_receipts[0],
        policy,
    )


def _snapshot():
    return build_model_catalog_snapshot(
        (
            ModelCapabilityCard(
                provider="openrouter",
                model_id=MODEL_ID,
                canonical_model_id=MODEL_ID,
                source="authenticated_autoresearch_promotion",
                availability=Availability.AVAILABLE,
                promotion_state=PromotionState.CHAMPION,
                task_families=(TASK_FAMILY,),
                supports_structured_output=True,
                supports_reasoning=True,
                verifier_pass_rate=1.0,
                benchmark_scores={TASK_FAMILY: 1.0},
            ),
        ),
        generated_at="2026-08-21T00:00:00+00:00",
    )


def _requirements(**overrides):
    values = {
        "task_family": TASK_FAMILY,
        "selection_mode": SelectionMode.SINGLE,
        "purpose": SelectionPurpose.PRODUCTION,
        "require_structured_output": True,
        "require_reasoning": True,
        "min_verifier_pass_rate": 1.0,
    }
    values.update(overrides)
    return ModelTaskRequirements(**values)


def _resolver():
    return StaticModelEvidenceKeyResolver(
        {
            (
                ModelEvidenceSignerRole.BENCHMARK_VERIFIER.value,
                BENCHMARK_FINGERPRINT,
                KEY_EPOCH,
            ): BENCHMARK_PUBLIC_KEY,
            (
                ModelEvidenceSignerRole.PROMOTION_AUTHORITY.value,
                PROMOTION_FINGERPRINT,
                KEY_EPOCH,
            ): PROMOTION_PUBLIC_KEY,
        }
    )


def _trusted_keys():
    return {
        "trusted_public_keys": [
            {
                "signer_role": role,
                "signer_key_fingerprint": fingerprint,
                "key_epoch": KEY_EPOCH,
                "public_key": public_key,
            }
            for role, fingerprint, public_key in (
                (
                    ModelEvidenceSignerRole.BENCHMARK_VERIFIER.value,
                    BENCHMARK_FINGERPRINT,
                    BENCHMARK_PUBLIC_KEY,
                ),
                (
                    ModelEvidenceSignerRole.PROMOTION_AUTHORITY.value,
                    PROMOTION_FINGERPRINT,
                    PROMOTION_PUBLIC_KEY,
                ),
            )
        ]
    }


def _runtime_policy(benchmark):
    return {
        "task_family": TASK_FAMILY,
        "runtime_surface": "reddog_backend_architect",
        "min_verifier_pass_rate": 1.0,
        "required_task_set_digest": benchmark.task_set_digest,
        "required_held_out_split_digest": benchmark.held_out_split_digest,
        "required_verifier_digest": benchmark.verifier_digest,
        "authority_receipt_id": "runtime-authority:external",
    }


def _external_bundle(
    preview,
    authenticated,
    benchmark,
    policy,
    *,
    signed_policy_digest=None,
    **overrides,
):
    gate_payload = __import__("json").loads(
        Path(authenticated.supply.output_path).read_text(encoding="utf-8")
    )
    promotion = gate_payload["promotion_gate_receipts"][0]["promotion_evidence_receipt"]
    from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
        rehydrate_model_promotion_evidence_receipt,
    )

    promotion_receipt = rehydrate_model_promotion_evidence_receipt(
        promotion, benchmark_receipt=benchmark
    )
    benchmark_signature = make_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.BENCHMARK_VERIFIER,
        public_key=BENCHMARK_PUBLIC_KEY,
        fingerprint=BENCHMARK_FINGERPRINT,
        model_id=MODEL_ID,
        catalog_snapshot_id=preview.catalog_snapshot_id,
        selection_receipt_id=preview.selection_receipt_id,
        benchmark_run_receipt_id="model_combination_benchmark_run:single",
        benchmark_receipt=benchmark,
        nonce="nonce:benchmark:single-production",
    )
    promotion_signature = make_signed_evidence_receipt(
        signer_role=ModelEvidenceSignerRole.PROMOTION_AUTHORITY,
        public_key=PROMOTION_PUBLIC_KEY,
        fingerprint=PROMOTION_FINGERPRINT,
        model_id=MODEL_ID,
        catalog_snapshot_id=preview.catalog_snapshot_id,
        selection_receipt_id=preview.selection_receipt_id,
        benchmark_run_receipt_id="model_combination_benchmark_run:single",
        benchmark_receipt=benchmark,
        promotion_receipt=promotion_receipt,
        promotion_policy_digest=(
            signed_policy_digest or preview.promotion_policy_digest
        ),
        nonce="nonce:promotion:single-production",
    )
    bundle = {
        "schema_version": EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "catalog_snapshot_id": preview.catalog_snapshot_id,
        "selection_receipt_id": preview.selection_receipt_id,
        "benchmark_run_receipt_id": "model_combination_benchmark_run:single",
        "entries": [
            {
                "benchmark_receipt": benchmark.to_dict(),
                "promotion_receipt": promotion_receipt.to_dict(),
                "benchmark_signature_receipt": benchmark_signature.to_dict(),
                "promotion_signature_receipt": promotion_signature.to_dict(),
            }
        ],
    }
    bundle.update(overrides)
    return bundle


def test_authenticated_single_model_chain_reproduces_preview_and_binds_runtime(tmp_path):
    authenticated, benchmark, policy = _authenticated_gate(tmp_path)
    snapshot = _snapshot()
    selection_path = tmp_path / "runtime" / "selection.json"
    runtime_path = tmp_path / "runtime" / "binding.json"

    result = bind_authenticated_single_model_promotion_to_runtime(
        repo_root=REPO_ROOT,
        authenticated_promotion=authenticated,
        catalog_snapshot=snapshot.to_dict(),
        requirements=_requirements(),
        signed_evidence_provider=lambda preview: _external_bundle(
            preview, authenticated, benchmark, policy
        ),
        evidence_key_resolver=_resolver(),
        evidence_signature_verifier=DeterministicSignatureVerifier(),
        evidence_nonce_store=InMemoryEvidenceNonceStore(),
        trusted_keys_payload=_trusted_keys(),
        runtime_policy=_runtime_policy(benchmark),
        selection_output_path=selection_path,
        runtime_binding_output_path=runtime_path,
        now=NOW,
    )

    assert result.selection.accepted
    assert result.runtime_binding.accepted
    assert result.preview.selection_receipt_id == result.selection.selection_receipt_id
    assert result.preview.selection_receipt_id == result.runtime_binding.selection_receipt_id
    assert result.runtime_binding.principal_model == MODEL_ID
    assert selection_path.is_file() and runtime_path.is_file()


def test_panel_and_evidence_splices_fail_closed_before_runtime_output(tmp_path):
    authenticated, benchmark, policy = _authenticated_gate(tmp_path)
    snapshot = _snapshot()
    calls = []
    panel_requirements = _requirements(
        selection_mode=SelectionMode.PANEL,
        max_candidates=2,
        panel_roles=("principal", "critic"),
    )
    with pytest.raises(ValueError, match="shadow_only"):
        bind_authenticated_single_model_promotion_to_runtime(
            repo_root=REPO_ROOT,
            authenticated_promotion=authenticated,
            catalog_snapshot=snapshot.to_dict(),
            requirements=panel_requirements,
            signed_evidence_provider=lambda preview: calls.append(preview),
            evidence_key_resolver=_resolver(),
            evidence_signature_verifier=DeterministicSignatureVerifier(),
            evidence_nonce_store=InMemoryEvidenceNonceStore(),
            trusted_keys_payload=_trusted_keys(),
            runtime_policy=_runtime_policy(benchmark),
            selection_output_path=tmp_path / "panel-selection.json",
            runtime_binding_output_path=tmp_path / "panel-binding.json",
            now=NOW,
        )
    assert calls == []

    preview = build_authenticated_single_model_production_selection_preview(
        repo_root=REPO_ROOT,
        authenticated_promotion=authenticated,
        catalog_snapshot=snapshot.to_dict(),
        requirements=_requirements(),
    )
    spliced = _external_bundle(
        preview,
        authenticated,
        benchmark,
        policy,
        selection_receipt_id="model_selection_receipt:spliced",
    )
    runtime_path = tmp_path / "splice-binding.json"
    with pytest.raises(ValueError, match="preview_mismatch"):
        bind_authenticated_single_model_promotion_to_runtime(
            repo_root=REPO_ROOT,
            authenticated_promotion=authenticated,
            catalog_snapshot=snapshot.to_dict(),
            requirements=_requirements(),
            signed_evidence_provider=lambda _preview: spliced,
            evidence_key_resolver=_resolver(),
            evidence_signature_verifier=DeterministicSignatureVerifier(),
            evidence_nonce_store=InMemoryEvidenceNonceStore(),
            trusted_keys_payload=_trusted_keys(),
            runtime_policy=_runtime_policy(benchmark),
            selection_output_path=tmp_path / "splice-selection.json",
            runtime_binding_output_path=runtime_path,
            now=NOW,
        )
    assert not runtime_path.exists()

    policy_spliced = _external_bundle(
        preview,
        authenticated,
        benchmark,
        policy,
        signed_policy_digest="sha256:" + "2" * 64,
    )
    policy_runtime_path = tmp_path / "policy-splice-binding.json"
    with pytest.raises(ValueError, match="policy_signature_mismatch"):
        bind_authenticated_single_model_promotion_to_runtime(
            repo_root=REPO_ROOT,
            authenticated_promotion=authenticated,
            catalog_snapshot=snapshot.to_dict(),
            requirements=_requirements(),
            signed_evidence_provider=lambda _preview: policy_spliced,
            evidence_key_resolver=_resolver(),
            evidence_signature_verifier=DeterministicSignatureVerifier(),
            evidence_nonce_store=InMemoryEvidenceNonceStore(),
            trusted_keys_payload=_trusted_keys(),
            runtime_policy=_runtime_policy(benchmark),
            selection_output_path=tmp_path / "policy-splice-selection.json",
            runtime_binding_output_path=policy_runtime_path,
            now=NOW,
        )
    assert not policy_runtime_path.exists()


def test_tampered_authenticated_result_and_inside_repo_outputs_reject(tmp_path):
    authenticated, benchmark, _policy = _authenticated_gate(tmp_path)
    forged = replace(
        authenticated,
        authority=replace(
            authenticated.authority,
            durable_store_receipt_id="other:receipt",
        ),
    )
    with pytest.raises(ValueError, match="authority_invalid"):
        build_authenticated_single_model_production_selection_preview(
            repo_root=REPO_ROOT,
            authenticated_promotion=forged,
            catalog_snapshot=_snapshot().to_dict(),
            requirements=_requirements(),
        )

    with pytest.raises(ValueError, match="inside_repo"):
        bind_authenticated_single_model_promotion_to_runtime(
            repo_root=REPO_ROOT,
            authenticated_promotion=authenticated,
            catalog_snapshot=_snapshot().to_dict(),
            requirements=_requirements(),
            signed_evidence_provider=lambda _preview: {},
            evidence_key_resolver=_resolver(),
            evidence_signature_verifier=DeterministicSignatureVerifier(),
            evidence_nonce_store=InMemoryEvidenceNonceStore(),
            trusted_keys_payload=_trusted_keys(),
            runtime_policy=_runtime_policy(benchmark),
            selection_output_path=REPO_ROOT / "selection.json",
            runtime_binding_output_path=tmp_path / "binding.json",
            now=NOW,
        )


def test_adapter_contains_no_signer_key_provider_or_process_boundary():
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "requests" not in imports
    assert "subprocess" not in imports
    assert "build_model_signed_evidence_receipt" not in source
    assert "private_key" not in source
    assert "signed_evidence_provider" in source
