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
    MAX_RECEIPT_TTL_SECONDS,
    SIGNING_PREFIX as CAMPAIGN_SIGNING_PREFIX,
    VerifiedCampaignPromotionAuthority,
    _campaign_authority_publication_binding,
    build_signed_campaign_promotion_authority_receipt,
    verify_and_store_campaign_promotion_authority,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution import (
    _execution_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_promotion_gate_supply import (
    run_reddog_model_autoresearch_campaign_promotion_gate_supply,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_configured_gateway_evidence import (
    DirectoryConfiguredGatewayReceiptStore,
    digest_payload,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_single_model_production_binding import (
    CampaignPromotionAuthorityUseContext,
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


REPO_ROOT = Path(__file__).absolute().parents[4]
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
CAMPAIGN_PUBLIC_KEY = "external-public-key:campaign-promotion"
CAMPAIGN_FINGERPRINT = "fingerprint:campaign-promotion"
CAMPAIGN_SIGNATURE = "external-signature:campaign-promotion"


class _CampaignKeys:
    def resolve(self, role, fingerprint, epoch):
        if (role, fingerprint, epoch) == (
            "promotion_authority",
            CAMPAIGN_FINGERPRINT,
            KEY_EPOCH,
        ):
            return CAMPAIGN_PUBLIC_KEY
        return None


class _CampaignVerifier:
    def verify(self, public_key, signing_input, signature):
        return (
            public_key == CAMPAIGN_PUBLIC_KEY
            and signing_input.startswith(CAMPAIGN_SIGNING_PREFIX + ".")
            and signature == CAMPAIGN_SIGNATURE
        )


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
        signer_public_key=CAMPAIGN_PUBLIC_KEY,
        signer_key_fingerprint=CAMPAIGN_FINGERPRINT,
        key_epoch=KEY_EPOCH,
        issued_at=NOW - 10,
        expires_at=NOW + 300,
        nonce="nonce:campaign-promotion:single",
        signature=CAMPAIGN_SIGNATURE,
    )
    store = DirectoryConfiguredGatewayReceiptStore(
        tmp_path / "authority-store", repo_root=REPO_ROOT
    )
    keys = _CampaignKeys()
    verifier = _CampaignVerifier()
    authority = verify_and_store_campaign_promotion_authority(
        request=request,
        signed_receipt=signed,
        key_resolver=keys,
        signature_verifier=verifier,
        publication_store=store,
        receipt_store=store,
        now=NOW,
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
    context = CampaignPromotionAuthorityUseContext(
        key_resolver=keys,
        signature_verifier=verifier,
        receipt_store=store,
        publication_store=store,
        trusted_now_epoch=lambda: NOW,
    )
    return (
        AuthenticatedCampaignPromotionSupplyResult(authority=authority, supply=supply),
        benchmark_run.benchmark_evidence_receipts[0],
        policy,
        context,
    )


def _authority_use_with_status(tmp_path, authenticated, status):
    store = DirectoryConfiguredGatewayReceiptStore(
        tmp_path / ("authority-use-" + str(status or "missing").lower()),
        repo_root=REPO_ROOT,
    )
    store.append(authenticated.authority.receipt)
    binding = _campaign_authority_publication_binding(
        authenticated.authority.request, authenticated.authority.receipt
    )
    nonce = "campaign-promotion-signature:" + authenticated.authority.receipt.nonce
    if status in {"RESERVED", "AUTHORIZED", "APPLIED"}:
        store.advance_publication(nonce, binding, "RESERVED")
    if status in {"AUTHORIZED", "APPLIED"}:
        store.advance_publication(nonce, binding, "AUTHORIZED")
    if status == "APPLIED":
        store.advance_publication(nonce, binding, "APPLIED")
    return CampaignPromotionAuthorityUseContext(
        key_resolver=_CampaignKeys(),
        signature_verifier=_CampaignVerifier(),
        receipt_store=store,
        publication_store=store,
        trusted_now_epoch=lambda: NOW,
    )


def _durable_files(store):
    return {
        str(path.relative_to(store.root)): path.read_bytes()
        for path in store.root.rglob("*")
        if path.is_file()
    }


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


def _runtime_policy(benchmark, authenticated):
    return {
        "task_family": TASK_FAMILY,
        "runtime_surface": "reddog_backend_architect",
        "min_verifier_pass_rate": 1.0,
        "required_task_set_digest": benchmark.task_set_digest,
        "required_held_out_split_digest": benchmark.held_out_split_digest,
        "required_verifier_digest": benchmark.verifier_digest,
        "authority_receipt_id": authenticated.authority.receipt.receipt_id,
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


def test_authenticated_single_model_chain_reproduces_preview_and_binds_runtime(
    tmp_path,
):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    snapshot = _snapshot()
    selection_path = tmp_path / "runtime" / "selection.json"
    runtime_path = tmp_path / "runtime" / "binding.json"

    result = bind_authenticated_single_model_promotion_to_runtime(
        repo_root=REPO_ROOT,
        authenticated_promotion=authenticated,
        catalog_snapshot=snapshot.to_dict(),
        requirements=_requirements(),
        authority_use=authority_use,
        signed_evidence_provider=lambda preview: _external_bundle(
            preview, authenticated, benchmark, policy
        ),
        evidence_key_resolver=_resolver(),
        evidence_signature_verifier=DeterministicSignatureVerifier(),
        trusted_keys_payload=_trusted_keys(),
        runtime_policy=_runtime_policy(benchmark, authenticated),
        selection_output_path=selection_path,
        runtime_binding_output_path=runtime_path,
    )

    assert result.selection.accepted
    assert result.runtime_binding.accepted
    assert result.preview.selection_receipt_id == result.selection.selection_receipt_id
    assert (
        result.preview.selection_receipt_id
        == result.runtime_binding.selection_receipt_id
    )
    assert result.runtime_binding.principal_model == MODEL_ID
    assert selection_path.is_file() and runtime_path.is_file()


def test_panel_and_evidence_splices_fail_closed_before_runtime_output(tmp_path):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
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
            authority_use=authority_use,
            signed_evidence_provider=lambda preview: calls.append(preview),
            evidence_key_resolver=_resolver(),
            evidence_signature_verifier=DeterministicSignatureVerifier(),
            trusted_keys_payload=_trusted_keys(),
            runtime_policy=_runtime_policy(benchmark, authenticated),
            selection_output_path=tmp_path / "panel-selection.json",
            runtime_binding_output_path=tmp_path / "panel-binding.json",
        )
    assert calls == []

    preview = build_authenticated_single_model_production_selection_preview(
        repo_root=REPO_ROOT,
        authenticated_promotion=authenticated,
        catalog_snapshot=snapshot.to_dict(),
        requirements=_requirements(),
        authority_use=authority_use,
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
            authority_use=authority_use,
            signed_evidence_provider=lambda _preview: spliced,
            evidence_key_resolver=_resolver(),
            evidence_signature_verifier=DeterministicSignatureVerifier(),
            trusted_keys_payload=_trusted_keys(),
            runtime_policy=_runtime_policy(benchmark, authenticated),
            selection_output_path=tmp_path / "splice-selection.json",
            runtime_binding_output_path=runtime_path,
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
            authority_use=authority_use,
            signed_evidence_provider=lambda _preview: policy_spliced,
            evidence_key_resolver=_resolver(),
            evidence_signature_verifier=DeterministicSignatureVerifier(),
            trusted_keys_payload=_trusted_keys(),
            runtime_policy=_runtime_policy(benchmark, authenticated),
            selection_output_path=tmp_path / "policy-splice-selection.json",
            runtime_binding_output_path=policy_runtime_path,
        )
    assert not policy_runtime_path.exists()


def test_tampered_authenticated_result_and_inside_repo_outputs_reject(tmp_path):
    authenticated, benchmark, _policy, authority_use = _authenticated_gate(tmp_path)
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
            authority_use=authority_use,
        )

    with pytest.raises(ValueError, match="inside_repo"):
        bind_authenticated_single_model_promotion_to_runtime(
            repo_root=REPO_ROOT,
            authenticated_promotion=authenticated,
            catalog_snapshot=_snapshot().to_dict(),
            requirements=_requirements(),
            authority_use=authority_use,
            signed_evidence_provider=lambda _preview: {},
            evidence_key_resolver=_resolver(),
            evidence_signature_verifier=DeterministicSignatureVerifier(),
            trusted_keys_payload=_trusted_keys(),
            runtime_policy=_runtime_policy(benchmark, authenticated),
            selection_output_path=REPO_ROOT / "selection.json",
            runtime_binding_output_path=tmp_path / "binding.json",
        )


@pytest.mark.parametrize("failure", ("malformed_policy", "invalid_trust"))
def test_deterministic_preflight_rejects_before_provider_or_artifacts(
    tmp_path, failure
):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    selection = tmp_path / failure / "selection.json"
    runtime = tmp_path / failure / "runtime.json"
    calls = []
    before = sorted(path.name for path in authority_use.receipt_store.root.iterdir())
    runtime_policy = _runtime_policy(benchmark, authenticated)
    trusted_keys = _trusted_keys()
    if failure == "malformed_policy":
        runtime_policy = {"task_family": TASK_FAMILY}
    else:
        trusted_keys = {"trusted_public_keys": [{"signer_role": "broken"}]}
    with pytest.raises(ValueError, match="runtime_policy|trusted_keys"):
        bind_authenticated_single_model_promotion_to_runtime(
            repo_root=REPO_ROOT,
            authenticated_promotion=authenticated,
            catalog_snapshot=_snapshot().to_dict(),
            requirements=_requirements(),
            authority_use=authority_use,
            signed_evidence_provider=lambda preview: calls.append(preview),
            evidence_key_resolver=_resolver(),
            evidence_signature_verifier=DeterministicSignatureVerifier(),
            trusted_keys_payload=trusted_keys,
            runtime_policy=runtime_policy,
            selection_output_path=selection,
            runtime_binding_output_path=runtime,
        )
    after = sorted(path.name for path in authority_use.receipt_store.root.iterdir())
    assert calls == []
    assert before == after
    assert not selection.exists() and not runtime.exists()


def test_preexisting_output_claim_rejects_before_provider(tmp_path):
    authenticated, benchmark, _policy, authority_use = _authenticated_gate(tmp_path)
    selection = tmp_path / "claimed" / "selection.json"
    runtime = tmp_path / "claimed" / "runtime.json"
    selection.parent.mkdir(parents=True)
    selection.write_text("operator-owned", encoding="utf-8")
    calls = []
    with pytest.raises(ValueError, match="output_claim_failed"):
        bind_authenticated_single_model_promotion_to_runtime(
            repo_root=REPO_ROOT,
            authenticated_promotion=authenticated,
            catalog_snapshot=_snapshot().to_dict(),
            requirements=_requirements(),
            authority_use=authority_use,
            signed_evidence_provider=lambda preview: calls.append(preview),
            evidence_key_resolver=_resolver(),
            evidence_signature_verifier=DeterministicSignatureVerifier(),
            trusted_keys_payload=_trusted_keys(),
            runtime_policy=_runtime_policy(benchmark, authenticated),
            selection_output_path=selection,
            runtime_binding_output_path=runtime,
        )
    assert calls == []
    assert selection.read_text(encoding="utf-8") == "operator-owned"
    assert not runtime.exists()


@pytest.mark.parametrize("failure", ("expired", "revoked", "forged"))
def test_authority_use_rejects_before_provider_or_artifacts(tmp_path, failure):
    authenticated, benchmark, _policy, authority_use = _authenticated_gate(tmp_path)
    durable_store = authority_use.receipt_store
    before = sorted(path.name for path in durable_store.root.iterdir())
    if failure == "expired":
        authority_use = replace(
            authority_use,
            trusted_now_epoch=lambda: authenticated.authority.receipt.expires_at + 1,
        )
    elif failure == "revoked":
        authority_use = replace(authority_use, revoked_key_epochs=(KEY_EPOCH,))
    else:
        forged_receipt = build_signed_campaign_promotion_authority_receipt(
            request=authenticated.authority.request,
            signer_public_key=CAMPAIGN_PUBLIC_KEY,
            signer_key_fingerprint=CAMPAIGN_FINGERPRINT,
            key_epoch=KEY_EPOCH,
            issued_at=NOW - 10,
            expires_at=NOW + 300,
            nonce="nonce:campaign-promotion:forged",
            signature="forged-signature",
        )
        forged = VerifiedCampaignPromotionAuthority(
            request=authenticated.authority.request,
            receipt=forged_receipt,
            durable_store_receipt_id=forged_receipt.receipt_id,
        )
        authenticated = replace(authenticated, authority=forged)
    selection = tmp_path / failure / "selection.json"
    runtime = tmp_path / failure / "runtime.json"
    calls = []
    with pytest.raises(ValueError, match="authority"):
        bind_authenticated_single_model_promotion_to_runtime(
            repo_root=REPO_ROOT,
            authenticated_promotion=authenticated,
            catalog_snapshot=_snapshot().to_dict(),
            requirements=_requirements(),
            authority_use=authority_use,
            signed_evidence_provider=lambda preview: calls.append(preview),
            evidence_key_resolver=_resolver(),
            evidence_signature_verifier=DeterministicSignatureVerifier(),
            trusted_keys_payload=_trusted_keys(),
            runtime_policy=_runtime_policy(benchmark, authenticated),
            selection_output_path=selection,
            runtime_binding_output_path=runtime,
        )
    assert calls == []
    assert before == sorted(path.name for path in durable_store.root.iterdir())
    assert not selection.exists() and not runtime.exists()


@pytest.mark.parametrize("status", (None, "RESERVED", "AUTHORIZED"))
def test_authority_use_requires_preexisting_applied_publication_without_mutation(
    tmp_path, status
):
    authenticated, benchmark, _policy, _context = _authenticated_gate(tmp_path)
    authority_use = _authority_use_with_status(tmp_path, authenticated, status)
    before = _durable_files(authority_use.publication_store)
    selection = tmp_path / "non-applied" / str(status) / "selection.json"
    runtime = tmp_path / "non-applied" / str(status) / "runtime.json"
    calls = []
    with pytest.raises(ValueError, match="publication_not_applied"):
        bind_authenticated_single_model_promotion_to_runtime(
            repo_root=REPO_ROOT,
            authenticated_promotion=authenticated,
            catalog_snapshot=_snapshot().to_dict(),
            requirements=_requirements(),
            authority_use=authority_use,
            signed_evidence_provider=lambda preview: calls.append(preview),
            evidence_key_resolver=_resolver(),
            evidence_signature_verifier=DeterministicSignatureVerifier(),
            trusted_keys_payload=_trusted_keys(),
            runtime_policy=_runtime_policy(benchmark, authenticated),
            selection_output_path=selection,
            runtime_binding_output_path=runtime,
        )
    assert calls == []
    assert _durable_files(authority_use.publication_store) == before
    assert not selection.exists() and not runtime.exists()


@pytest.mark.parametrize(
    ("expires_at", "reason"),
    (
        (NOW - 10, "ttl_invalid"),
        (NOW - 10 + MAX_RECEIPT_TTL_SECONDS + 1, "ttl_exceeded"),
    ),
)
def test_forged_signed_invalid_ttl_rejects_without_effects(
    tmp_path, expires_at, reason
):
    authenticated, benchmark, _policy, _context = _authenticated_gate(tmp_path)
    receipt = replace(authenticated.authority.receipt, expires_at=expires_at)
    forged_authority = replace(
        authenticated.authority,
        receipt=receipt,
        durable_store_receipt_id=receipt.receipt_id,
    )
    authenticated = replace(authenticated, authority=forged_authority)
    authority_use = _authority_use_with_status(tmp_path, authenticated, "APPLIED")
    before = _durable_files(authority_use.publication_store)
    selection = tmp_path / reason / "selection.json"
    runtime = tmp_path / reason / "runtime.json"
    calls = []
    with pytest.raises(ValueError, match=reason):
        bind_authenticated_single_model_promotion_to_runtime(
            repo_root=REPO_ROOT,
            authenticated_promotion=authenticated,
            catalog_snapshot=_snapshot().to_dict(),
            requirements=_requirements(),
            authority_use=authority_use,
            signed_evidence_provider=lambda preview: calls.append(preview),
            evidence_key_resolver=_resolver(),
            evidence_signature_verifier=DeterministicSignatureVerifier(),
            trusted_keys_payload=_trusted_keys(),
            runtime_policy=_runtime_policy(benchmark, authenticated),
            selection_output_path=selection,
            runtime_binding_output_path=runtime,
        )
    assert calls == []
    assert _durable_files(authority_use.publication_store) == before
    assert not selection.exists() and not runtime.exists()


def test_exact_retry_after_transient_runtime_supply_failure(tmp_path, monkeypatch):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_execution as execution

    original = execution.run_reddog_model_runtime_binding_artifact_supply
    attempts = []

    def fail_once(**values):
        attempts.append(values["output_path"])
        if len(attempts) == 1:
            raise OSError("transient-runtime-write")
        return original(**values)

    monkeypatch.setattr(
        execution, "run_reddog_model_runtime_binding_artifact_supply", fail_once
    )
    selection = tmp_path / "retry" / "selection.json"
    runtime = tmp_path / "retry" / "runtime.json"

    inputs = {
        "repo_root": REPO_ROOT,
        "authenticated_promotion": authenticated,
        "catalog_snapshot": _snapshot().to_dict(),
        "requirements": _requirements(),
        "authority_use": authority_use,
        "signed_evidence_provider": lambda preview: _external_bundle(
            preview, authenticated, benchmark, policy
        ),
        "evidence_key_resolver": _resolver(),
        "evidence_signature_verifier": DeterministicSignatureVerifier(),
        "trusted_keys_payload": _trusted_keys(),
        "runtime_policy": _runtime_policy(benchmark, authenticated),
        "selection_output_path": selection,
        "runtime_binding_output_path": runtime,
    }

    with pytest.raises(OSError, match="transient-runtime-write"):
        bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert not selection.exists() and not runtime.exists()
    result = bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert result.runtime_binding.accepted
    assert len(attempts) == 2
    assert selection.is_file() and runtime.is_file()


def test_applied_replay_and_conflicting_paths_are_zero_callback(tmp_path):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    calls = []

    def provider(preview):
        calls.append(preview.selection_receipt_id)
        return _external_bundle(preview, authenticated, benchmark, policy)

    inputs = _production_inputs(
        tmp_path, authenticated, benchmark, authority_use, provider
    )
    first = bind_authenticated_single_model_promotion_to_runtime(**inputs)
    second = bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert second.runtime_binding.runtime_binding_receipt_id == (
        first.runtime_binding.runtime_binding_receipt_id
    )
    assert calls == [first.preview.selection_receipt_id]

    conflicting = dict(inputs)
    conflicting["selection_output_path"] = tmp_path / "other" / "selection.json"
    conflicting["runtime_binding_output_path"] = tmp_path / "other" / "runtime.json"
    with pytest.raises(ValueError, match="authority_binding_conflict"):
        bind_authenticated_single_model_promotion_to_runtime(**conflicting)
    assert calls == [first.preview.selection_receipt_id]
    assert not Path(conflicting["selection_output_path"]).exists()
    assert not Path(conflicting["runtime_binding_output_path"]).exists()


def test_directory_fsync_ambiguity_recovers_without_provider_replay(
    tmp_path, monkeypatch
):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    store_type = type(authority_use.publication_store)
    original = store_type._write_publication_marker
    injected = []

    def ambiguous(self, nonce, binding, status):
        original(self, nonce, binding, status)
        if (
            not injected
            and nonce.startswith("single-model-production-authority-use:")
            and status == "APPLIED"
        ):
            injected.append(True)
            raise OSError("directory-fsync-ambiguous")

    monkeypatch.setattr(store_type, "_write_publication_marker", ambiguous)
    calls = []

    def provider(preview):
        calls.append(preview.selection_receipt_id)
        return _external_bundle(preview, authenticated, benchmark, policy)

    inputs = _production_inputs(
        tmp_path, authenticated, benchmark, authority_use, provider
    )
    first = bind_authenticated_single_model_promotion_to_runtime(**inputs)
    second = bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert injected == [True]
    assert calls == [first.preview.selection_receipt_id]
    assert second.runtime_binding.runtime_binding_receipt_id == (
        first.runtime_binding.runtime_binding_receipt_id
    )
    assert Path(inputs["selection_output_path"]).is_file()
    assert Path(inputs["runtime_binding_output_path"]).is_file()


def test_partial_final_publication_recovers_after_applied(tmp_path, monkeypatch):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_outputs as outputs

    original = outputs.os.replace
    injected = []

    def fail_runtime_publish(source, destination):
        source_path = Path(source)
        if (
            not injected
            and source_path.name.startswith(".binding.json.")
            and source_path.name.endswith(".staging")
        ):
            injected.append(True)
            raise OSError("runtime-final-publication-failed")
        return original(source, destination)

    monkeypatch.setattr(outputs.os, "replace", fail_runtime_publish)
    calls = []

    def provider(preview):
        calls.append(preview.selection_receipt_id)
        return _external_bundle(preview, authenticated, benchmark, policy)

    inputs = _production_inputs(
        tmp_path, authenticated, benchmark, authority_use, provider
    )
    result = bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert result.runtime_binding.accepted
    assert injected == [True]
    assert calls == [result.preview.selection_receipt_id]
    assert Path(inputs["selection_output_path"]).stat().st_size > 0
    assert Path(inputs["runtime_binding_output_path"]).stat().st_size > 0


def test_stage_fsync_failure_has_no_terminal_applied_or_final_artifact(
    tmp_path, monkeypatch
):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_artifact_durability as durability

    def fail_stage_fsync(_path):
        raise OSError("stage-fsync-failed")

    monkeypatch.setattr(durability, "_fsync_regular_file", fail_stage_fsync)
    calls = []

    def provider(preview):
        calls.append(preview.selection_receipt_id)
        return _external_bundle(preview, authenticated, benchmark, policy)

    inputs = _production_inputs(
        tmp_path, authenticated, benchmark, authority_use, provider
    )
    with pytest.raises(ValueError, match="stage_durability_failed"):
        bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert len(calls) == 1
    assert not Path(inputs["selection_output_path"]).exists()
    assert not Path(inputs["runtime_binding_output_path"]).exists()
    payloads = _stored_payloads(authority_use)
    assert not any(
        item.get("schema_version") == "single_model_production_terminal.v1"
        for item in payloads
    )
    assert not _production_applied(payloads)


def test_final_directory_fsync_failure_retries_without_provider_callback(
    tmp_path, monkeypatch
):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_artifact_durability as durability

    original = durability.fsync_published_parent

    def fail_final_directory(_path):
        raise ValueError("single_model_production_final_directory_durability_failed")

    monkeypatch.setattr(durability, "fsync_published_parent", fail_final_directory)
    calls = []

    def provider(preview):
        calls.append(preview.selection_receipt_id)
        return _external_bundle(preview, authenticated, benchmark, policy)

    inputs = _production_inputs(
        tmp_path, authenticated, benchmark, authority_use, provider
    )
    with pytest.raises(ValueError, match="final_directory_durability_failed"):
        bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert _production_applied(_stored_payloads(authority_use))
    assert Path(inputs["selection_output_path"]).stat().st_size > 0
    assert Path(inputs["runtime_binding_output_path"]).stat().st_size == 0

    monkeypatch.setattr(durability, "fsync_published_parent", original)
    recovered = bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert recovered.runtime_binding.accepted
    assert calls == [recovered.preview.selection_receipt_id]
    assert Path(inputs["runtime_binding_output_path"]).stat().st_size > 0


def test_authorized_terminal_retry_completes_without_provider_replay(
    tmp_path, monkeypatch
):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    store_type = type(authority_use.publication_store)
    original = store_type._write_publication_marker

    def deny_applied(self, nonce, binding, status):
        if (
            nonce.startswith("single-model-production-authority-use:")
            and status == "APPLIED"
        ):
            raise OSError("applied-write-denied")
        return original(self, nonce, binding, status)

    monkeypatch.setattr(store_type, "_write_publication_marker", deny_applied)
    calls = []

    def provider(preview):
        calls.append(preview.selection_receipt_id)
        return _external_bundle(preview, authenticated, benchmark, policy)

    inputs = _production_inputs(
        tmp_path, authenticated, benchmark, authority_use, provider
    )
    with pytest.raises(ValueError, match="publication_failed"):
        bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert Path(inputs["selection_output_path"]).is_file()
    assert Path(inputs["runtime_binding_output_path"]).is_file()

    monkeypatch.setattr(store_type, "_write_publication_marker", original)
    recovered = bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert recovered.runtime_binding.accepted
    assert calls == [recovered.preview.selection_receipt_id]


def test_unlink_denial_quarantines_partial_stage_and_surfaces_cleanup(
    tmp_path, monkeypatch
):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_execution as execution

    def fail_runtime(**_values):
        raise OSError("runtime-supply-failed")

    original_unlink = Path.unlink

    def deny_selection_stage(self, *args, **kwargs):
        if self.name.startswith(".selection.json.") and self.name.endswith(".staging"):
            raise PermissionError("unlink-denied")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(
        execution, "run_reddog_model_runtime_binding_artifact_supply", fail_runtime
    )
    monkeypatch.setattr(Path, "unlink", deny_selection_stage)
    inputs = _production_inputs(
        tmp_path,
        authenticated,
        benchmark,
        authority_use,
        lambda preview: _external_bundle(preview, authenticated, benchmark, policy),
    )
    with pytest.raises(ValueError, match="cleanup_quarantined"):
        bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert not Path(inputs["selection_output_path"]).exists()
    assert not Path(inputs["runtime_binding_output_path"]).exists()
    quarantined = list((tmp_path / "runtime").glob("*.invalid.*"))
    assert len(quarantined) == 1
    assert (
        __import__("json")
        .loads(quarantined[0].read_text(encoding="utf-8"))["receipt_id"]
        .startswith("model_selection_receipt:")
    )


def test_callback_time_advance_rejects_before_publication_or_artifacts(tmp_path):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    clock = [NOW]
    authority_use = replace(authority_use, trusted_now_epoch=lambda: clock[0])
    calls = []

    def provider(preview):
        calls.append(preview.selection_receipt_id)
        clock[0] = authenticated.authority.receipt.expires_at + 1
        return _external_bundle(preview, authenticated, benchmark, policy)

    inputs = _production_inputs(
        tmp_path, authenticated, benchmark, authority_use, provider
    )
    before = _durable_files(authority_use.publication_store)
    with pytest.raises(ValueError, match="authority_expired"):
        bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert len(calls) == 1
    assert _durable_files(authority_use.publication_store) == before
    assert not Path(inputs["selection_output_path"]).exists()
    assert not Path(inputs["runtime_binding_output_path"]).exists()


def test_authority_callback_time_advance_rechecks_pure_before_terminal(tmp_path):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    clock = [NOW]

    class AdvancingCampaignVerifier:
        calls = 0

        def verify(self, public_key, signing_input, signature):
            accepted = _CampaignVerifier().verify(public_key, signing_input, signature)
            self.calls += 1
            if self.calls == 4:
                clock[0] = authenticated.authority.receipt.expires_at + 1
            return accepted

    verifier = AdvancingCampaignVerifier()
    authority_use = replace(
        authority_use,
        signature_verifier=verifier,
        trusted_now_epoch=lambda: clock[0],
    )
    calls = []

    def provider(preview):
        calls.append(preview.selection_receipt_id)
        return _external_bundle(preview, authenticated, benchmark, policy)

    inputs = _production_inputs(
        tmp_path, authenticated, benchmark, authority_use, provider
    )
    with pytest.raises(ValueError, match="production_authority_expired"):
        bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert verifier.calls == 4
    assert len(calls) == 1
    assert not Path(inputs["selection_output_path"]).exists()
    assert not Path(inputs["runtime_binding_output_path"]).exists()
    payloads = _stored_payloads(authority_use)
    assert not any(
        item.get("schema_version") == "single_model_production_terminal.v1"
        for item in payloads
    )
    assert not _production_applied(payloads)


def test_second_refresh_expiry_keeps_final_artifacts_nonconsumable(
    tmp_path, monkeypatch
):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_finalization as finalization

    clock = [NOW]
    authority_use = replace(authority_use, trusted_now_epoch=lambda: clock[0])
    original = finalization.refresh_production_authority
    refreshes = []

    def expire_before_applied(inputs):
        refreshes.append(True)
        if len(refreshes) == 2:
            clock[0] = authenticated.authority.receipt.expires_at + 1
        return original(inputs)

    monkeypatch.setattr(
        finalization, "refresh_production_authority", expire_before_applied
    )
    inputs = _production_inputs(
        tmp_path,
        authenticated,
        benchmark,
        authority_use,
        lambda preview: _external_bundle(preview, authenticated, benchmark, policy),
    )
    with pytest.raises(ValueError, match="authority_expired"):
        bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert len(refreshes) == 2
    selection = Path(inputs["selection_output_path"])
    runtime = Path(inputs["runtime_binding_output_path"])
    assert selection.stat().st_size == 0
    assert runtime.stat().st_size == 0
    assert len(list(selection.parent.glob("*.staging"))) == 2
    payloads = []
    for path in authority_use.publication_store.root.rglob("*.json"):
        payloads.append(__import__("json").loads(path.read_text(encoding="utf-8")))
    assert not any(
        item.get("status") == "APPLIED"
        and str(item.get("nonce", "")).startswith(
            "single-model-production-authority-use:"
        )
        for item in payloads
    )


def test_applied_terminal_recovery_verifies_before_stage_publication(
    tmp_path, monkeypatch
):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    clock = [NOW]
    authority_use = replace(authority_use, trusted_now_epoch=lambda: clock[0])
    store_type = type(authority_use.publication_store)
    original = store_type._write_publication_marker

    def expire_after_applied(self, nonce, binding, status):
        original(self, nonce, binding, status)
        if (
            nonce.startswith("single-model-production-authority-use:")
            and status == "APPLIED"
        ):
            clock[0] = authenticated.authority.receipt.expires_at + 1
            raise OSError("applied-directory-flush-ambiguous")

    monkeypatch.setattr(store_type, "_write_publication_marker", expire_after_applied)
    inputs = _production_inputs(
        tmp_path,
        authenticated,
        benchmark,
        authority_use,
        lambda preview: _external_bundle(preview, authenticated, benchmark, policy),
    )
    with pytest.raises(ValueError, match="authority_expired"):
        bind_authenticated_single_model_promotion_to_runtime(**inputs)
    selection = Path(inputs["selection_output_path"])
    runtime = Path(inputs["runtime_binding_output_path"])
    assert selection.stat().st_size == 0 and runtime.stat().st_size == 0
    assert len(list(selection.parent.glob("*.staging"))) == 2
    markers = [
        __import__("json").loads(path.read_text(encoding="utf-8"))
        for path in authority_use.publication_store.root.rglob("*.json")
    ]
    assert any(
        item.get("status") == "APPLIED"
        and str(item.get("nonce", "")).startswith(
            "single-model-production-authority-use:"
        )
        for item in markers
    )


def test_recovery_evidence_callback_time_advance_blocks_zero_callback_publish(
    tmp_path, monkeypatch
):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_artifact_durability as durability

    original_sync = durability.fsync_published_parent

    def fail_final_directory(_path):
        raise ValueError("single_model_production_final_directory_durability_failed")

    monkeypatch.setattr(durability, "fsync_published_parent", fail_final_directory)
    provider_calls = []

    def provider(preview):
        provider_calls.append(preview.selection_receipt_id)
        return _external_bundle(preview, authenticated, benchmark, policy)

    inputs = _production_inputs(
        tmp_path, authenticated, benchmark, authority_use, provider
    )
    with pytest.raises(ValueError, match="final_directory_durability_failed"):
        bind_authenticated_single_model_promotion_to_runtime(**inputs)
    monkeypatch.setattr(durability, "fsync_published_parent", original_sync)

    clock = [NOW]

    class AdvancingEvidenceVerifier:
        calls = 0

        def verify(self, public_key, signing_input, signature):
            accepted = DeterministicSignatureVerifier().verify(
                public_key, signing_input, signature
            )
            self.calls += 1
            if self.calls == 1:
                clock[0] = authenticated.authority.receipt.expires_at + 1
            return accepted

    evidence_verifier = AdvancingEvidenceVerifier()
    retry = dict(inputs)
    retry["authority_use"] = replace(authority_use, trusted_now_epoch=lambda: clock[0])
    retry["evidence_signature_verifier"] = evidence_verifier
    with pytest.raises(ValueError, match="production_authority_expired"):
        bind_authenticated_single_model_promotion_to_runtime(**retry)
    assert evidence_verifier.calls >= 1
    assert len(provider_calls) == 1
    assert Path(inputs["selection_output_path"]).stat().st_size > 0
    assert Path(inputs["runtime_binding_output_path"]).stat().st_size == 0


def _production_inputs(tmp_path, authenticated, benchmark, authority_use, provider):
    return {
        "repo_root": REPO_ROOT,
        "authenticated_promotion": authenticated,
        "catalog_snapshot": _snapshot().to_dict(),
        "requirements": _requirements(),
        "authority_use": authority_use,
        "signed_evidence_provider": provider,
        "evidence_key_resolver": _resolver(),
        "evidence_signature_verifier": DeterministicSignatureVerifier(),
        "trusted_keys_payload": _trusted_keys(),
        "runtime_policy": _runtime_policy(benchmark, authenticated),
        "selection_output_path": tmp_path / "runtime" / "selection.json",
        "runtime_binding_output_path": tmp_path / "runtime" / "binding.json",
    }


def _stored_payloads(authority_use):
    return [
        __import__("json").loads(path.read_text(encoding="utf-8"))
        for path in authority_use.publication_store.root.rglob("*.json")
    ]


def _production_applied(payloads):
    return any(
        item.get("status") == "APPLIED"
        and str(item.get("nonce", "")).startswith(
            "single-model-production-authority-use:"
        )
        for item in payloads
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
