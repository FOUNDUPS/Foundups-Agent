"""Adversarial tests for signed aggregate PANEL evidence."""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from model_signed_evidence_test_helpers import (
    BENCHMARK_PUBLIC_KEY,
    PROMOTION_PUBLIC_KEY,
    DeterministicSignatureVerifier,
    InMemoryEvidenceNonceStore,
    ModelEvidenceSignerRole,
    StaticModelEvidenceKeyResolver,
    deterministic_signature,
    make_verified_production_evidence,
)

from modules.ai_intelligence.ai_gateway.src.model_intelligence_catalog import (
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
from modules.ai_intelligence.ai_gateway.src.model_panel_signed_evidence import (
    PanelEvidenceSignerRole,
    PanelMemberEvidenceInput,
    build_model_panel_signed_evidence_receipt,
    build_panel_member_evidence_binding,
    build_verified_model_panel_evidence,
    model_panel_signed_evidence_signing_input,
    rehydrate_model_panel_signed_evidence_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding import (
    ModelRuntimeBindingDecision,
    ModelRuntimeBindingPolicy,
    bind_reddog_runtime_models,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import VerifiedModelProductionEvidence


TASK = "architecture"
TASK_SET = "sha256:task-set"
HELD_OUT = "sha256:held-out"
TOPOLOGY = "sha256:panel-topology"
VERIFIER = "sha256:verifier"
BENCHMARK_RUN = "model_combination_benchmark_run:panel"
TASK_RECEIPT = "model_task_set:architecture-held-out"
TOPOLOGY_RECEIPT = "model_panel_topology:architecture-v1"
POLICY_RECEIPT = "model_runtime_binding_policy:architecture-v1"
SURFACE_RECEIPT = "model_runtime_surface:reddog-fusion"
PANEL_PUBLIC_KEY = "ed25519-pub-v1:panel"
PANEL_FINGERPRINT = "fingerprint:panel"
KEY_EPOCH = "epoch-1"
NOW = 1_800_000_000


def _digest(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _card(model_id: str, provider: str) -> ModelCapabilityCard:
    return ModelCapabilityCard(
        provider=provider,
        model_id=model_id,
        canonical_model_id=model_id,
        source="test",
        promotion_state=PromotionState.CHAMPION,
        task_families=(TASK,),
        benchmark_scores={TASK: 0.9},
        verifier_pass_rate=0.95,
    ).normalized()


def _benchmark(model_id: str, *, topology: str = TOPOLOGY):
    return build_model_benchmark_evidence_receipt(
        model_id=model_id,
        task_family=TASK,
        task_set_digest=TASK_SET,
        held_out_split_digest=HELD_OUT,
        prompt_topology_digest=topology,
        verifier_digest=VERIFIER,
        verifier_receipt_id=f"verifier:{model_id}",
        sample_count=20,
        accepted_count=19,
        metrics=ModelOutcomeMetrics(latency_ms=1000, input_tokens=500, output_tokens=200),
    )


def _promotion(benchmark):
    return build_model_promotion_evidence_receipt(
        benchmark_receipt=benchmark,
        promotion_state=PromotionState.CHAMPION,
        promotion_authority_receipt_id=f"authority:{benchmark.model_id}",
        signed_promotion_receipt_id=f"signed:{benchmark.model_id}",
        min_verifier_pass_rate=0.9,
    )


def _policy() -> ModelRuntimeBindingPolicy:
    return ModelRuntimeBindingPolicy(
        task_family=TASK,
        runtime_surface="reddog_fusion",
        min_verifier_pass_rate=0.9,
        required_task_set_digest=TASK_SET,
        required_held_out_split_digest=HELD_OUT,
        required_verifier_digest=VERIFIER,
        max_panel_models=4,
        required_panel_topology_digest=TOPOLOGY,
        authority_receipt_id="runtime-authority:1",
    )


def _member_resolver() -> StaticModelEvidenceKeyResolver:
    return StaticModelEvidenceKeyResolver(
        {
            ModelEvidenceSignerRole.BENCHMARK_VERIFIER.value: BENCHMARK_PUBLIC_KEY,
            ModelEvidenceSignerRole.PROMOTION_AUTHORITY.value: PROMOTION_PUBLIC_KEY,
        }
    )


def _panel_resolver(public_key: str = PANEL_PUBLIC_KEY) -> StaticModelEvidenceKeyResolver:
    return StaticModelEvidenceKeyResolver({PanelEvidenceSignerRole.PANEL_AUTHORITY.value: public_key})


def _signed_panel(case: dict, **overrides):
    selection = case["selection"]
    snapshot = case["snapshot"]
    policy = case["policy"]
    values = {
        "members": case["bindings"],
        "required_roles": selection.requirements.panel_roles,
        "synthesizer_model_id": selection.role_assignments[0].canonical_model_id,
        "synthesizer_role": "principal",
        "catalog_snapshot_id": snapshot.snapshot_id,
        "catalog_snapshot_digest": _digest(snapshot.to_dict()),
        "selection_receipt_id": selection.receipt_id,
        "selection_receipt_digest": _digest(selection.to_dict()),
        "task_receipt_id": TASK_RECEIPT,
        "task_receipt_digest": TASK_SET,
        "topology_receipt_id": TOPOLOGY_RECEIPT,
        "topology_receipt_digest": TOPOLOGY,
        "policy_receipt_id": POLICY_RECEIPT,
        "policy_receipt_digest": _digest(policy.normalized().to_dict()),
        "runtime_surface_receipt_id": SURFACE_RECEIPT,
        "runtime_surface_receipt_digest": _digest({"runtime_surface": policy.normalized().runtime_surface}),
        "benchmark_run_receipt_id": BENCHMARK_RUN,
        "signer_role": PanelEvidenceSignerRole.PANEL_AUTHORITY,
        "signer_public_key": PANEL_PUBLIC_KEY,
        "signer_key_fingerprint": PANEL_FINGERPRINT,
        "key_epoch": KEY_EPOCH,
        "issued_at": NOW - 10,
        "expires_at": NOW + 3600,
        "nonce": "nonce:panel:1",
    }
    values.update(overrides)
    placeholder = build_model_panel_signed_evidence_receipt(signature="placeholder", **values)
    signature = deterministic_signature(PANEL_PUBLIC_KEY, model_panel_signed_evidence_signing_input(placeholder))
    return build_model_panel_signed_evidence_receipt(signature=signature, **values)


def _case() -> dict:
    snapshot, benchmarks, promotions, selection = _selection_case()
    verified_singles, member_inputs, bindings = _member_case(
        snapshot, benchmarks, promotions, selection
    )
    case = {
        "snapshot": snapshot,
        "selection": selection,
        "benchmarks": benchmarks,
        "promotions": promotions,
        "verified_singles": verified_singles,
        "member_inputs": member_inputs,
        "bindings": bindings,
        "policy": _policy(),
    }
    case["aggregate"] = _signed_panel(case)
    return case


def _selection_case():
    cards = (
        _card("provider/principal", "a"),
        _card("provider/researcher", "b"),
        _card("provider/critic", "c"),
    )
    snapshot = build_model_catalog_snapshot(cards, generated_at="2026-07-18T00:00:00+00:00")
    benchmarks = tuple(_benchmark(card.canonical_model_id) for card in cards)
    promotions = tuple(_promotion(value) for value in benchmarks)
    requirements = ModelTaskRequirements(
        task_family=TASK,
        purpose=SelectionPurpose.PRODUCTION,
        selection_mode=SelectionMode.PANEL,
        max_candidates=3,
        min_verifier_pass_rate=0.9,
        panel_roles=("principal", "researcher", "critic"),
        panel_topology_digest=TOPOLOGY,
    )
    provisional_entries = []
    for benchmark, promotion in zip(benchmarks, promotions):
        provisional_entries.extend(
            make_verified_production_evidence(
                benchmark,
                promotion,
                catalog_snapshot_id=snapshot.snapshot_id,
            ).entries
        )
    selection = select_models_for_task(
        snapshot,
        requirements,
        production_evidence=VerifiedModelProductionEvidence(entries=tuple(provisional_entries)),
    )
    return snapshot, benchmarks, promotions, selection


def _member_case(snapshot, benchmarks, promotions, selection):
    verified_singles = tuple(
        make_verified_production_evidence(
            benchmark,
            promotion,
            catalog_snapshot_id=snapshot.snapshot_id,
            selection_receipt_id=selection.receipt_id,
            benchmark_run_receipt_id=BENCHMARK_RUN,
        )
        for benchmark, promotion in zip(benchmarks, promotions)
    )
    assignments = selection.role_assignments
    member_inputs = tuple(
        PanelMemberEvidenceInput(
            role=assignment.role,
            model_id=assignment.canonical_model_id,
            provider=assignment.provider,
            benchmark_receipt=verified.entries[0].benchmark_receipt,
            promotion_receipt=verified.entries[0].promotion_receipt,
            benchmark_signature_receipt=verified.entries[0].benchmark_signature_receipt,
            promotion_signature_receipt=verified.entries[0].promotion_signature_receipt,
        )
        for assignment, verified in zip(assignments, verified_singles)
    )
    bindings = tuple(
        build_panel_member_evidence_binding(
            ordinal=index,
            role=source.role,
            model_id=source.model_id,
            provider=source.provider,
            verified_evidence=verified,
        )
        for index, (source, verified) in enumerate(zip(member_inputs, verified_singles))
    )
    return verified_singles, member_inputs, bindings


def _verify(case: dict, *, aggregate=None, member_inputs=None, **overrides):
    values = {
        "catalog_snapshot": case["snapshot"],
        "selection_receipt": case["selection"],
        "member_inputs": member_inputs or case["member_inputs"],
        "aggregate_receipt": aggregate or case["aggregate"],
        "runtime_policy": case["policy"],
        "task_receipt_id": TASK_RECEIPT,
        "topology_receipt_id": TOPOLOGY_RECEIPT,
        "policy_receipt_id": POLICY_RECEIPT,
        "runtime_surface_receipt_id": SURFACE_RECEIPT,
        "member_key_resolver": _member_resolver(),
        "member_signature_verifier": DeterministicSignatureVerifier(),
        "panel_key_resolver": _panel_resolver(),
        "panel_signature_verifier": DeterministicSignatureVerifier(),
        "now": NOW,
    }
    values.update(overrides)
    return build_verified_model_panel_evidence(**values)


def test_verified_panel_binds_runtime_and_round_trips():
    case = _case()
    assert rehydrate_model_panel_signed_evidence_receipt(case["aggregate"].to_dict()) == case["aggregate"]
    verified = _verify(case)
    receipt = bind_reddog_runtime_models(
        catalog_snapshot=case["snapshot"],
        selection_receipt=case["selection"],
        benchmark_evidence_receipts=case["benchmarks"],
        promotion_evidence_receipts=case["promotions"],
        policy=case["policy"],
        verified_production_evidence=verified,
    )
    assert receipt.decision == ModelRuntimeBindingDecision.BOUND
    assert receipt.principal_model == "provider/principal"
    assert receipt.panel_models == ("provider/researcher", "provider/critic")


def test_panel_runtime_rejects_verified_single_collection_without_aggregate():
    case = _case()
    singles = VerifiedModelProductionEvidence(
        entries=tuple(entry for value in case["verified_singles"] for entry in value.entries)
    )
    receipt = bind_reddog_runtime_models(
        catalog_snapshot=case["snapshot"],
        selection_receipt=case["selection"],
        benchmark_evidence_receipts=case["benchmarks"],
        promotion_evidence_receipts=case["promotions"],
        policy=case["policy"],
        verified_production_evidence=singles,
    )
    assert receipt.decision == ModelRuntimeBindingDecision.REJECTED
    assert "missing_verified_panel_evidence" in receipt.rejection_reasons


def test_member_chain_is_verified_before_aggregate_signature():
    case = _case()
    first = case["member_inputs"][0]
    forged_signature = replace(first.benchmark_signature_receipt, signature="test-sig:forged")
    forged_inputs = (replace(first, benchmark_signature_receipt=forged_signature), *case["member_inputs"][1:])
    forged_aggregate = replace(case["aggregate"], signature="test-sig:also-forged")
    with pytest.raises(ValueError, match="benchmark_signed_evidence_rejected:signature_invalid"):
        _verify(case, aggregate=forged_aggregate, member_inputs=forged_inputs)


def test_rejects_independently_signed_member_with_spliced_topology():
    case = _case()
    first = case["member_inputs"][0]
    benchmark = _benchmark(first.model_id, topology="sha256:other-topology")
    promotion = _promotion(benchmark)
    verified = make_verified_production_evidence(
        benchmark,
        promotion,
        catalog_snapshot_id=case["snapshot"].snapshot_id,
        selection_receipt_id=case["selection"].receipt_id,
        benchmark_run_receipt_id=BENCHMARK_RUN,
    )
    source = PanelMemberEvidenceInput(
        first.role,
        first.model_id,
        first.provider,
        benchmark,
        promotion,
        verified.entries[0].benchmark_signature_receipt,
        verified.entries[0].promotion_signature_receipt,
    )
    binding = build_panel_member_evidence_binding(
        ordinal=0,
        role=source.role,
        model_id=source.model_id,
        provider=source.provider,
        verified_evidence=verified,
    )
    with pytest.raises(ValueError, match="panel_member_topology_mismatch"):
        _verify(
            case,
            member_inputs=(source, *case["member_inputs"][1:]),
            aggregate=_signed_panel(case, members=(binding, *case["bindings"][1:])),
        )


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    (
        ("catalog_snapshot_id", "model_catalog_snapshot:other", "panel_context_splice"),
        ("selection_receipt_digest", "sha256:other", "panel_context_splice"),
        ("task_receipt_digest", "sha256:other", "panel_task_digest_splice"),
        ("topology_receipt_digest", "sha256:other", "panel_context_splice"),
        ("policy_receipt_digest", "sha256:other", "panel_context_splice"),
        ("runtime_surface_receipt_digest", "sha256:other", "panel_context_splice"),
    ),
)
def test_rejects_signed_context_splices(field, value, reason):
    case = _case()
    with pytest.raises(ValueError, match=reason):
        _verify(case, aggregate=_signed_panel(case, **{field: value}))


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("task_receipt_id", "model_task_set:other"),
        ("topology_receipt_id", "model_panel_topology:other"),
        ("policy_receipt_id", "model_runtime_binding_policy:other"),
        ("runtime_surface_receipt_id", "model_runtime_surface:other"),
    ),
)
def test_rejects_signed_context_id_splices(field, value):
    case = _case()
    with pytest.raises(ValueError, match="panel_context_id_splice"):
        _verify(case, aggregate=_signed_panel(case, **{field: value}))


def test_rejects_member_reorder_substitution_and_synthesizer_substitution():
    case = _case()
    reordered = (case["bindings"][1], case["bindings"][0], case["bindings"][2])
    with pytest.raises(ValueError, match="panel_member_evidence_substitution"):
        _verify(case, aggregate=_signed_panel(case, members=reordered))
    substituted = replace(case["bindings"][0], member_evidence_digest="sha256:substituted")
    with pytest.raises(ValueError, match="panel_member_evidence_substitution"):
        _verify(case, aggregate=_signed_panel(case, members=(substituted, *case["bindings"][1:])))
    with pytest.raises(ValueError, match="panel_synthesizer_substitution"):
        _verify(
            case,
            aggregate=_signed_panel(
                case,
                synthesizer_model_id="provider/critic",
                synthesizer_role="principal",
            ),
        )


def test_rejects_duplicate_members_roles_and_missing_required_role():
    case = _case()
    sources = case["member_inputs"]
    duplicate_model = (sources[0], replace(sources[1], model_id=sources[0].model_id, benchmark_receipt=sources[0].benchmark_receipt,
                                            promotion_receipt=sources[0].promotion_receipt,
                                            benchmark_signature_receipt=sources[0].benchmark_signature_receipt,
                                            promotion_signature_receipt=sources[0].promotion_signature_receipt), sources[2])
    duplicate_model_bindings = (case["bindings"][0], replace(case["bindings"][0], ordinal=1, role="researcher"), case["bindings"][2])
    with pytest.raises(ValueError, match="duplicate_panel_members"):
        _verify(case, member_inputs=duplicate_model, aggregate=_signed_panel(case, members=duplicate_model_bindings))

    duplicate_role = (sources[0], replace(sources[1], role="principal"), sources[2])
    duplicate_role_bindings = (case["bindings"][0], replace(case["bindings"][1], role="principal"), case["bindings"][2])
    with pytest.raises(ValueError, match="duplicate_panel_roles"):
        _verify(case, member_inputs=duplicate_role, aggregate=_signed_panel(case, members=duplicate_role_bindings))
    with pytest.raises(ValueError, match="panel_required_roles_mismatch"):
        _verify(case, aggregate=_signed_panel(case, required_roles=("principal", "researcher")))


def test_rejects_expiry_untrusted_revoked_and_replay():
    case = _case()
    expired = _signed_panel(case, issued_at=NOW - 7200, expires_at=NOW - 3600)
    with pytest.raises(ValueError, match="panel_evidence_expired"):
        _verify(case, aggregate=expired)
    with pytest.raises(ValueError, match="panel_signer_key_untrusted"):
        _verify(case, panel_key_resolver=_panel_resolver("ed25519-pub-v1:other"))
    with pytest.raises(ValueError, match="panel_key_epoch_revoked"):
        _verify(case, revoked_panel_key_epochs=(KEY_EPOCH,))
    forged = replace(case["aggregate"], signature="test-sig:forged")
    with pytest.raises(ValueError, match="panel_signature_invalid"):
        _verify(case, aggregate=forged)

    store = InMemoryEvidenceNonceStore()
    assert _verify(case, nonce_store=store, consume_nonce=True).panel_signed_evidence_verified
    with pytest.raises(ValueError, match="panel_nonce_replay"):
        _verify(case, nonce_store=store, consume_nonce=True)


def test_runtime_rechecks_verified_member_projection():
    case = _case()
    verified = _verify(case)
    tampered = replace(verified, member_entries=tuple(reversed(verified.member_entries)))
    receipt = bind_reddog_runtime_models(
        catalog_snapshot=case["snapshot"],
        selection_receipt=case["selection"],
        benchmark_evidence_receipts=case["benchmarks"],
        promotion_evidence_receipts=case["promotions"],
        policy=case["policy"],
        verified_production_evidence=tampered,
    )
    assert receipt.decision == ModelRuntimeBindingDecision.REJECTED
    assert "panel_signed_evidence_member_projection_mismatch" in receipt.rejection_reasons


def test_panel_evidence_module_has_no_network_command_signer_or_runtime_mutation_imports():
    source = Path("modules/ai_intelligence/ai_gateway/src/model_panel_signed_evidence.py").read_text()
    tree = ast.parse(source)
    imported: set[str] = set()
    banned_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id in {
                "os", "subprocess", "requests", "urllib", "socket"
            }:
                banned_calls.append(f"{node.func.value.id}.{node.func.attr}")
    assert {"subprocess", "requests", "urllib", "socket", "cryptography"}.isdisjoint(imported)
    assert banned_calls == []
