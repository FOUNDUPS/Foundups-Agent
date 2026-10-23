"""Authenticated AutoResearch promotion authority and composition tests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from modules.ai_intelligence.ai_gateway.src import (
    model_autoresearch_authenticated_promotion_authority as authority_module,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_authenticated_promotion_authority import (
    authorize_and_supply_campaign_promotion_gates,
    build_campaign_promotion_authority_request,
    build_signed_campaign_promotion_authority_receipt,
    verify_and_store_campaign_promotion_authority,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_configured_gateway_evidence import (
    DirectoryConfiguredGatewayReceiptStore,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import SelectionMode
from modules.ai_intelligence.ai_gateway.src.model_topology_proposal_lm_studio import (
    propose_lm_studio_shadow_topologies,
)
from modules.ai_intelligence.ai_gateway.src.model_topology_proposer_authenticated_provenance import (
    build_signed_topology_proposer_provenance_receipt,
    verify_and_store_topology_proposer_provenance,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution import (
    REPO_ROOT,
    _runner,
    _tasks,
    _verifier,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution import (
    _execution_receipt,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_promotion_gate_supply import (
    _policies,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_topology_proposer_authenticated_provenance import (
    _proposal_result as _panel_proposal_result,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_topology_proposal_admission import (
    _proposal,
    _requirements,
    _snapshot,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_topology_proposal_lm_studio import (
    _FakeLMStudioBackend,
)
from modules.ai_intelligence.ai_gateway.src.model_combination_benchmark_harness import (
    run_model_combination_benchmark,
)
NOW = 1_800_000_010


class _Keys:
    def resolve(self, role, fingerprint, epoch):
        values = {
            ("autoresearch_proposer", "fingerprint:proposer", "epoch-1"): "public-key:proposer",
            ("promotion_authority", "fingerprint:promotion", "epoch-1"): "public-key:promotion",
        }
        return values.get((role, fingerprint, epoch))


class _Verifier:
    def verify(self, public_key, signing_input, signature):
        expected = {
            "public-key:proposer": "reddog-topology-proposer-provenance.v1.",
            "public-key:promotion": "reddog-autoresearch-promotion-authority.v1.",
        }
        return signing_input.startswith(expected.get(public_key, "!")) and signature == "signature:valid"


class _Store:
    def __init__(self, fail=False, fail_once=False):
        self.records = []
        self.fail = fail
        self.fail_once = fail_once

    def append(self, receipt):
        if self.fail or self.fail_once:
            self.fail_once = False
            raise OSError("store unavailable")
        self.records.append(receipt.to_dict())
        return receipt.receipt_id


class _FailOnceDurableStore:
    def __init__(self, delegate):
        self.delegate = delegate
        self.fail_once = True

    @property
    def durable(self):
        return self.delegate.durable

    @property
    def store_id(self):
        return self.delegate.store_id

    def append(self, receipt):
        if self.fail_once:
            self.fail_once = False
            raise OSError("store unavailable")
        return self.delegate.append(receipt)

    def load(self, receipt_id):
        return self.delegate.load(receipt_id)


def _durable_store(tmp_path, name="authority"):
    return DirectoryConfiguredGatewayReceiptStore(
        tmp_path / name,
        repo_root=REPO_ROOT,
    )


def _single_proposal_result():
    snapshot = _snapshot()
    requirements = replace(
        _requirements(),
        selection_mode=SelectionMode.SINGLE,
        max_candidates=1,
        panel_roles=("principal",),
    )
    proposal = _proposal(snapshot, requirements)
    choices = {
        "topologies": [
            [candidate["role_assignments"][0]["model_id"]]
            for candidate in proposal["candidates"][:2]
        ]
    }
    return propose_lm_studio_shadow_topologies(
        catalog_snapshot=snapshot,
        requirements=requirements,
        proposer_model_id="nvidia/nemotron-3.5-lightning",
        backend_factory=lambda _model: _FakeLMStudioBackend(json.dumps(choices)),
    )


def _verified_proposer(store, *, panel=False):
    proposal = _panel_proposal_result() if panel else _single_proposal_result()
    call = proposal.call_receipt
    signed = build_signed_topology_proposer_provenance_receipt(
        call_receipt=call,
        admission_receipt=proposal.admission_receipt,
        signer_public_key="public-key:proposer",
        signer_key_fingerprint="fingerprint:proposer",
        key_epoch="epoch-1",
        issued_at=NOW - 10,
        expires_at=NOW + 300,
        nonce="nonce:proposer:authority-chain",
        signature="signature:valid",
    )
    return verify_and_store_topology_proposer_provenance(
        call_receipt=call,
        admission_receipt=proposal.admission_receipt,
        signed_receipt=signed,
        key_resolver=_Keys(),
        signature_verifier=_Verifier(),
        publication_store=store,
        receipt_store=store,
        now=NOW,
    )


def _signed_authority(request):
    return build_signed_campaign_promotion_authority_receipt(
        request=request,
        signer_public_key="public-key:promotion",
        signer_key_fingerprint="fingerprint:promotion",
        key_epoch="epoch-1",
        issued_at=NOW - 5,
        expires_at=NOW + 300,
        nonce="nonce:promotion:campaign-1",
        signature="signature:valid",
    )


def _rehash_signed_authority(receipt):
    body = {key: value for key, value in receipt.to_dict().items() if key != "receipt_id"}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return replace(
        receipt,
        receipt_id="model_autoresearch_promotion_authority:"
        + hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    )


def _execution_for(provenance):
    candidates = tuple(
        sorted(
            provenance.admission_receipt.accepted_candidates,
            key=lambda item: item.candidate_id,
        )
    )
    benchmark = run_model_combination_benchmark(
        tasks=_tasks(),
        candidates=candidates,
        runner=_runner,
        verifier=_verifier,
        verifier_digest="sha256:verifier",
        held_out_split_id="heldout-v1",
    )
    return _execution_receipt(
        plan=SimpleNamespace(receipt_id="model_autoresearch_plan:admitted-topologies"),
        benchmark=benchmark,
        executed_candidate_ids=tuple(item.candidate_id for item in candidates),
        skipped_campaign_candidate_ids=(),
    ).to_dict()


def test_authenticated_authority_persists_before_gate_and_binds_exact_chain(tmp_path):
    store = _durable_store(tmp_path)
    provenance = _verified_proposer(store)
    execution = _execution_for(provenance)
    policies = _policies(execution)
    result = authorize_and_supply_campaign_promotion_gates(
        repo_root=REPO_ROOT,
        campaign_execution_receipt=execution,
        promotion_policies=policies,
        proposer_provenance=provenance,
        signed_receipt_provider=_signed_authority,
        key_resolver=_Keys(),
        signature_verifier=_Verifier(),
        publication_store=store,
        receipt_store=store,
        now=NOW,
        output_path=tmp_path / "runtime" / "gates.json",
    )

    assert result.supply.accepted is True
    assert store.load(provenance.receipt.receipt_id) == provenance.receipt.to_dict()
    assert store.load(result.authority.receipt.receipt_id) == result.authority.receipt.to_dict()
    assert result.authority.request.source_execution_receipt_id == execution["receipt_id"]
    assert result.authority.request.proposer_provenance_receipt_id == provenance.receipt.receipt_id
    payload = json.loads((tmp_path / "runtime" / "gates.json").read_text(encoding="utf-8"))
    for gate in payload["promotion_gate_receipts"]:
        evidence = gate["promotion_evidence_receipt"]
        assert evidence["promotion_authority_receipt_id"] == result.authority.request.request_id
        assert evidence["signed_promotion_receipt_id"] == result.authority.receipt.receipt_id


def test_request_substitution_or_store_failure_cannot_reach_gate(tmp_path):
    publication_store = _durable_store(tmp_path)
    provenance = _verified_proposer(publication_store)
    execution = _execution_for(provenance)
    policies = _policies(execution)
    request = build_campaign_promotion_authority_request(
        campaign_execution_receipt=execution,
        promotion_policies=policies,
        proposer_provenance=provenance,
        now=NOW,
    )
    other_execution = dict(execution)
    other_execution["receipt_id"] = "model_autoresearch_campaign_execution:other"
    with pytest.raises(ValueError):
        other_request = build_campaign_promotion_authority_request(
            campaign_execution_receipt=other_execution,
            promotion_policies=policies,
            proposer_provenance=provenance,
            now=NOW,
        )
        verify_and_store_campaign_promotion_authority(
            request=other_request,
            signed_receipt=_signed_authority(request),
            key_resolver=_Keys(),
            signature_verifier=_Verifier(),
            publication_store=publication_store,
            receipt_store=_Store(),
            now=NOW,
        )

    retry_store = _FailOnceDurableStore(publication_store)
    signed = _signed_authority(request)
    with pytest.raises(ValueError, match="store_failed"):
        verify_and_store_campaign_promotion_authority(
            request=request,
            signed_receipt=signed,
            key_resolver=_Keys(),
            signature_verifier=_Verifier(),
            publication_store=publication_store,
            receipt_store=retry_store,
            now=NOW,
        )
    retried = verify_and_store_campaign_promotion_authority(
        request=request,
        signed_receipt=signed,
        key_resolver=_Keys(),
        signature_verifier=_Verifier(),
        publication_store=publication_store,
        receipt_store=retry_store,
        now=NOW,
    )
    assert retried.receipt.receipt_id == signed.receipt_id


def test_authority_receipt_and_publication_store_identity_must_match(tmp_path):
    publication_store = _durable_store(tmp_path, "authority-publication")
    provenance = _verified_proposer(publication_store)
    execution = _execution_for(provenance)
    request = build_campaign_promotion_authority_request(
        campaign_execution_receipt=execution,
        promotion_policies=_policies(execution),
        proposer_provenance=provenance,
        now=NOW,
    )
    with pytest.raises(ValueError, match="store_identity_mismatch"):
        verify_and_store_campaign_promotion_authority(
            request=request,
            signed_receipt=_signed_authority(request),
            key_resolver=_Keys(),
            signature_verifier=_Verifier(),
            publication_store=publication_store,
            receipt_store=_durable_store(tmp_path, "authority-receipts"),
            now=NOW,
        )


def test_signer_failure_does_not_burn_proposer_and_retry_can_succeed(tmp_path):
    store = _durable_store(tmp_path)
    provenance = _verified_proposer(store)
    execution = _execution_for(provenance)
    policies = _policies(execution)

    with pytest.raises(OSError, match="signer unavailable"):
        authorize_and_supply_campaign_promotion_gates(
            repo_root=REPO_ROOT,
            campaign_execution_receipt=execution,
            promotion_policies=policies,
            proposer_provenance=provenance,
            signed_receipt_provider=lambda _request: (_ for _ in ()).throw(
                OSError("signer unavailable")
            ),
            key_resolver=_Keys(),
            signature_verifier=_Verifier(),
            publication_store=store,
            receipt_store=store,
            now=NOW,
            output_path=tmp_path / "runtime" / "first.json",
        )
    retried = authorize_and_supply_campaign_promotion_gates(
        repo_root=REPO_ROOT,
        campaign_execution_receipt=execution,
        promotion_policies=policies,
        proposer_provenance=provenance,
        signed_receipt_provider=_signed_authority,
        key_resolver=_Keys(),
        signature_verifier=_Verifier(),
        publication_store=store,
        receipt_store=store,
        now=NOW,
        output_path=tmp_path / "runtime" / "retry.json",
    )
    assert retried.supply.accepted is True


def test_authority_trust_time_revocation_policy_splice_and_store_mismatch_fail(tmp_path):
    proposer_store = _durable_store(tmp_path, "proposer")
    provenance = _verified_proposer(proposer_store)
    execution = _execution_for(provenance)
    policies = _policies(execution)
    request = build_campaign_promotion_authority_request(
        campaign_execution_receipt=execution,
        promotion_policies=policies,
        proposer_provenance=provenance,
        now=NOW,
    )
    class MismatchStore(_Store):
        def append(self, receipt):
            super().append(receipt)
            return "other:receipt"

    cases = (
        {"signature_verifier": type("Bad", (), {"verify": lambda *_: False})()},
        {"key_resolver": type("NoKeys", (), {"resolve": lambda *_: None})()},
        {"revoked_key_epochs": ("epoch-1",)},
        {"now": NOW + 1_000},
        {"leeway_seconds": 61},
        {"receipt_store": MismatchStore()},
    )
    for index, overrides in enumerate(cases):
        publication_store = _durable_store(tmp_path, f"authority-failure-{index}")
        values = {
            "request": request,
            "signed_receipt": _signed_authority(request),
            "key_resolver": _Keys(),
            "signature_verifier": _Verifier(),
            "publication_store": publication_store,
            "receipt_store": _Store(),
            "now": NOW,
            **overrides,
        }
        with pytest.raises(ValueError):
            verify_and_store_campaign_promotion_authority(**values)

    stricter = _policies(execution, min_pass_rate=0.95)
    other_request = build_campaign_promotion_authority_request(
        campaign_execution_receipt=execution,
        promotion_policies=stricter,
        proposer_provenance=provenance,
        now=NOW,
    )
    with pytest.raises(ValueError, match="authority_request_mismatch"):
        verify_and_store_campaign_promotion_authority(
            request=other_request,
            signed_receipt=_signed_authority(request),
            key_resolver=_Keys(),
            signature_verifier=_Verifier(),
            publication_store=_durable_store(tmp_path, "policy-splice"),
            receipt_store=_Store(),
            now=NOW,
        )


def test_preflight_and_output_failure_preserve_exact_retry(tmp_path, monkeypatch):
    store = _durable_store(tmp_path, "preflight")
    provenance = _verified_proposer(store)
    execution = _execution_for(provenance)
    policies = _policies(execution)
    signer_calls = []

    def signer(request):
        signer_calls.append(request.request_id)
        return _signed_authority(request)

    with pytest.raises(ValueError, match="gate_preflight_failed"):
        authorize_and_supply_campaign_promotion_gates(
            repo_root=REPO_ROOT,
            campaign_execution_receipt=execution,
            promotion_policies=policies,
            proposer_provenance=provenance,
            signed_receipt_provider=signer,
            key_resolver=_Keys(),
            signature_verifier=_Verifier(),
            publication_store=store,
            receipt_store=store,
            now=NOW,
            output_path=REPO_ROOT / "forbidden-gates.json",
        )
    assert signer_calls == []

    real_supply = authority_module.run_reddog_model_autoresearch_campaign_promotion_gate_supply
    attempts = 0

    def fail_first_output(**kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            kwargs["output_path"] = REPO_ROOT / "forbidden-after-preflight.json"
        return real_supply(**kwargs)

    monkeypatch.setattr(
        authority_module,
        "run_reddog_model_autoresearch_campaign_promotion_gate_supply",
        fail_first_output,
    )
    first = authorize_and_supply_campaign_promotion_gates(
        repo_root=REPO_ROOT,
        campaign_execution_receipt=execution,
        promotion_policies=policies,
        proposer_provenance=provenance,
        signed_receipt_provider=signer,
        key_resolver=_Keys(),
        signature_verifier=_Verifier(),
        publication_store=store,
        receipt_store=store,
        now=NOW,
        output_path=tmp_path / "runtime" / "retryable.json",
    )
    assert first.supply.accepted is False
    retried = authorize_and_supply_campaign_promotion_gates(
        repo_root=REPO_ROOT,
        campaign_execution_receipt=execution,
        promotion_policies=policies,
        proposer_provenance=provenance,
        signed_receipt_provider=signer,
        key_resolver=_Keys(),
        signature_verifier=_Verifier(),
        publication_store=store,
        receipt_store=store,
        now=NOW,
        output_path=tmp_path / "runtime" / "retryable.json",
    )
    assert retried.supply.accepted is True
    assert signer_calls == [
        retried.authority.request.request_id,
        retried.authority.request.request_id,
    ]


def test_panel_promotion_is_shadow_only_before_signer_or_authority_store(tmp_path):
    store = _durable_store(tmp_path, "panel")
    provenance = _verified_proposer(store, panel=True)
    execution = _execution_for(provenance)
    policies = _policies(execution)
    signer_calls = []
    with pytest.raises(ValueError, match="panel_shadow_only"):
        authorize_and_supply_campaign_promotion_gates(
            repo_root=REPO_ROOT,
            campaign_execution_receipt=execution,
            promotion_policies=policies,
            proposer_provenance=provenance,
            signed_receipt_provider=lambda request: signer_calls.append(request) or _signed_authority(request),
            key_resolver=_Keys(),
            signature_verifier=_Verifier(),
            publication_store=store,
            receipt_store=store,
            now=NOW,
            output_path=tmp_path / "runtime" / "panel.json",
        )
    assert signer_calls == []


def test_nonpositive_authority_ttl_and_conflicting_nonce_binding_fail(tmp_path):
    store = _durable_store(tmp_path, "ttl")
    provenance = _verified_proposer(store)
    execution = _execution_for(provenance)
    policies = _policies(execution)
    request = build_campaign_promotion_authority_request(
        campaign_execution_receipt=execution,
        promotion_policies=policies,
        proposer_provenance=provenance,
        now=NOW,
    )
    invalid = _rehash_signed_authority(
        replace(
            _signed_authority(request),
            issued_at=NOW + 100,
            expires_at=NOW + 50,
            nonce="nonce:negative-authority-ttl",
        )
    )
    with pytest.raises(ValueError, match="ttl_invalid"):
        verify_and_store_campaign_promotion_authority(
            request=request,
            signed_receipt=invalid.to_dict(),
            key_resolver=_Keys(),
            signature_verifier=_Verifier(),
            publication_store=store,
            receipt_store=store,
            now=NOW + 75,
        )

    accepted = _signed_authority(request)
    verify_and_store_campaign_promotion_authority(
        request=request,
        signed_receipt=accepted,
        key_resolver=_Keys(),
        signature_verifier=_Verifier(),
        publication_store=store,
        receipt_store=store,
        now=NOW,
    )
    conflicting = _rehash_signed_authority(
        replace(
            accepted,
            issued_at=accepted.issued_at + 1,
            expires_at=accepted.expires_at + 1,
        )
    )
    with pytest.raises(ValueError, match="nonce_replay"):
        verify_and_store_campaign_promotion_authority(
            request=request,
            signed_receipt=conflicting,
            key_resolver=_Keys(),
            signature_verifier=_Verifier(),
            publication_store=_durable_store(tmp_path, "ttl"),
            receipt_store=store,
            now=NOW,
        )
