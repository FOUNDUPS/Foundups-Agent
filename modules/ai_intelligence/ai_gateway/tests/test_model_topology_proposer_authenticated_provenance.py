"""Authenticated durable provenance contracts for topology proposer calls."""

from __future__ import annotations

import json
import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_configured_gateway_evidence import (
    DirectoryConfiguredGatewayReceiptStore,
    digest_payload,
)
from modules.ai_intelligence.ai_gateway.src.model_topology_proposal_lm_studio import (
    propose_lm_studio_shadow_topologies,
)
from modules.ai_intelligence.ai_gateway.src.model_topology_proposer_authenticated_provenance import (
    build_signed_topology_proposer_provenance_receipt,
    propose_authenticated_lm_studio_shadow_topologies,
    consume_verified_topology_proposer_provenance,
    release_verified_topology_proposer_provenance_use,
    reload_verified_topology_proposer_provenance,
    reserve_verified_topology_proposer_provenance_use,
    verify_and_store_topology_proposer_provenance,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_topology_proposal_admission import (
    _proposal,
    _requirements,
    _snapshot,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_topology_proposal_lm_studio import (
    _FakeLMStudioBackend,
)


class _Keys:
    def resolve(self, signer_role, fingerprint, epoch):
        if (signer_role, fingerprint, epoch) == (
            "autoresearch_proposer", "fingerprint:proposer", "epoch-1"
        ):
            return "public-key:proposer"
        return None


class _Verifier:
    def verify(self, public_key, signing_input, signature):
        return (
            public_key == "public-key:proposer"
            and signing_input.startswith("reddog-topology-proposer-provenance.v1.")
            and signature == "signature:valid"
        )


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


def _proposal_result():
    snapshot, requirements = _snapshot(), _requirements()
    proposal = _proposal(snapshot, requirements)
    choices = {
        "topologies": [
            [item["model_id"] for item in candidate["role_assignments"]]
            for candidate in proposal["candidates"][:2]
        ]
    }
    result = propose_lm_studio_shadow_topologies(
        catalog_snapshot=snapshot,
        requirements=requirements,
        proposer_model_id="nvidia/nemotron-3.5-lightning",
        backend_factory=lambda _model: _FakeLMStudioBackend(json.dumps(choices)),
    )
    return result


def _call_receipt():
    return _proposal_result().call_receipt


def _signed(proposal):
    return build_signed_topology_proposer_provenance_receipt(
        call_receipt=proposal.call_receipt,
        admission_receipt=proposal.admission_receipt,
        signer_public_key="public-key:proposer",
        signer_key_fingerprint="fingerprint:proposer",
        key_epoch="epoch-1",
        issued_at=1_800_000_000,
        expires_at=1_800_000_300,
        nonce="nonce:proposer:1",
        signature="signature:valid",
    )


REPO_ROOT = Path(__file__).resolve().parents[4]


def _durable_store(tmp_path, name="authority"):
    return DirectoryConfiguredGatewayReceiptStore(
        tmp_path / name,
        repo_root=REPO_ROOT,
    )


def _rehash_signed(receipt):
    body = {key: value for key, value in receipt.to_dict().items() if key != "receipt_id"}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return replace(
        receipt,
        receipt_id="topology_proposer_provenance:"
        + hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    )


def test_directory_receipt_store_rejects_repo_root_and_persists_publication(tmp_path):
    with pytest.raises(ValueError, match="inside_repo"):
        DirectoryConfiguredGatewayReceiptStore(
            REPO_ROOT / "runtime" / "forbidden",
            repo_root=REPO_ROOT,
        )
    store = _durable_store(tmp_path, "publication")
    binding = digest_payload({"exact": "binding"})
    assert store.advance_publication("nonce:one", binding, "RESERVED") == "RESERVED"
    restarted = _durable_store(tmp_path, "publication")
    assert restarted.advance_publication("nonce:one", binding, "AUTHORIZED") == "AUTHORIZED"
    with pytest.raises(ValueError, match="binding_conflict"):
        restarted.advance_publication(
            "nonce:one", digest_payload({"exact": "other"}), "RESERVED"
        )


def test_proposer_receipt_and_publication_store_identity_must_match(tmp_path):
    proposal = _proposal_result()
    publication_store = _durable_store(tmp_path, "publication-store")
    receipt_store = _durable_store(tmp_path, "receipt-store")
    with pytest.raises(ValueError, match="store_identity_mismatch"):
        verify_and_store_topology_proposer_provenance(
            call_receipt=proposal.call_receipt,
            admission_receipt=proposal.admission_receipt,
            signed_receipt=_signed(proposal),
            key_resolver=_Keys(),
            signature_verifier=_Verifier(),
            publication_store=publication_store,
            receipt_store=receipt_store,
            now=1_800_000_010,
        )


def test_authenticated_proposer_provenance_is_persisted_before_return(tmp_path):
    proposal, store = _proposal_result(), _durable_store(tmp_path)
    verified = verify_and_store_topology_proposer_provenance(
        call_receipt=proposal.call_receipt,
        admission_receipt=proposal.admission_receipt,
        signed_receipt=_signed(proposal),
        key_resolver=_Keys(),
        signature_verifier=_Verifier(),
        publication_store=store,
        receipt_store=store,
        now=1_800_000_010,
    )

    assert verified.authenticated and verified.nonce_consumed
    assert verified.durable_store_receipt_id == verified.receipt.receipt_id
    assert store.load(verified.receipt.receipt_id) == verified.receipt.to_dict()


def test_provenance_replay_or_call_substitution_never_persists(tmp_path):
    proposal, store = _proposal_result(), _durable_store(tmp_path)
    call = proposal.call_receipt
    signed = _signed(proposal)
    verify_and_store_topology_proposer_provenance(
        call_receipt=call,
        admission_receipt=proposal.admission_receipt,
        signed_receipt=signed,
        key_resolver=_Keys(),
        signature_verifier=_Verifier(),
        publication_store=store,
        receipt_store=store,
        now=1_800_000_010,
    )
    with pytest.raises(ValueError, match="capability_already_live"):
        verify_and_store_topology_proposer_provenance(
            call_receipt=call,
            admission_receipt=proposal.admission_receipt,
            signed_receipt=signed,
            key_resolver=_Keys(),
            signature_verifier=_Verifier(),
            publication_store=store,
            receipt_store=store,
            now=1_800_000_011,
        )
    tampered = dict(call.to_dict())
    tampered["proposer_model_id"] = "attacker/model"
    with pytest.raises(ValueError):
        verify_and_store_topology_proposer_provenance(
            call_receipt=tampered,
            admission_receipt=proposal.admission_receipt,
            signed_receipt=signed,
            key_resolver=_Keys(),
            signature_verifier=_Verifier(),
            publication_store=store,
            receipt_store=store,
            now=1_800_000_011,
        )
    assert store.load(signed.receipt_id) == signed.to_dict()

    conflicting = _rehash_signed(
        replace(signed, issued_at=signed.issued_at + 1, expires_at=signed.expires_at + 1)
    )
    with pytest.raises(ValueError, match="nonce_replay"):
        verify_and_store_topology_proposer_provenance(
            call_receipt=call,
            admission_receipt=proposal.admission_receipt,
            signed_receipt=conflicting,
            key_resolver=_Keys(),
            signature_verifier=_Verifier(),
            publication_store=store,
            receipt_store=store,
            now=1_800_000_011,
        )


def test_authenticated_proposal_wrapper_returns_only_after_durable_store(tmp_path):
    snapshot, requirements, store = _snapshot(), _requirements(), _durable_store(tmp_path)
    proposal = _proposal(snapshot, requirements)
    choices = {
        "topologies": [
            [item["model_id"] for item in candidate["role_assignments"]]
            for candidate in proposal["candidates"][:2]
        ]
    }
    result = propose_authenticated_lm_studio_shadow_topologies(
        catalog_snapshot=snapshot,
        requirements=requirements,
        proposer_model_id="nvidia/nemotron-3.5-lightning",
        signed_receipt_provider=_signed,
        key_resolver=_Keys(),
        signature_verifier=_Verifier(),
        publication_store=store,
        receipt_store=store,
        now=1_800_000_010,
        backend_factory=lambda _model: _FakeLMStudioBackend(json.dumps(choices)),
    )
    assert result.provenance.durable_store_receipt_id == result.provenance.receipt.receipt_id
    assert store.load(result.provenance.receipt.receipt_id) == result.provenance.receipt.to_dict()


def test_completed_proposer_use_cannot_replay_after_restart(tmp_path):
    proposal = _proposal_result()
    store = _durable_store(tmp_path, "provenance")
    verified = verify_and_store_topology_proposer_provenance(
        call_receipt=proposal.call_receipt,
        admission_receipt=proposal.admission_receipt,
        signed_receipt=_signed(proposal),
        key_resolver=_Keys(),
        signature_verifier=_Verifier(),
        publication_store=store,
        receipt_store=store,
        now=1_800_000_010,
    )
    with pytest.raises(ValueError, match="capability_already_live"):
        reload_verified_topology_proposer_provenance(
            call_receipt=proposal.call_receipt,
            admission_receipt=proposal.admission_receipt,
            signed_receipt=verified.receipt,
            key_resolver=_Keys(),
            signature_verifier=_Verifier(),
            durable_receipt_store=store,
            now=1_800_000_011,
        )
    binding = digest_payload({"campaign_request_id": "campaign:one"})
    assert consume_verified_topology_proposer_provenance(
        verified,
        publication_store=store,
        use_binding_digest=binding,
        now=1_800_000_011,
    ) is not None
    restarted_store = _durable_store(tmp_path, "provenance")
    reloaded = reload_verified_topology_proposer_provenance(
        call_receipt=proposal.call_receipt,
        admission_receipt=proposal.admission_receipt,
        signed_receipt=verified.receipt,
        key_resolver=_Keys(),
        signature_verifier=_Verifier(),
        durable_receipt_store=restarted_store,
        now=1_800_000_012,
    )
    with pytest.raises(ValueError, match="durable_use_replay"):
        consume_verified_topology_proposer_provenance(
            reloaded,
            publication_store=restarted_store,
            use_binding_digest=binding,
            now=1_800_000_012,
        )
    with pytest.raises(ValueError, match="durable_use_replay"):
        consume_verified_topology_proposer_provenance(
            reloaded,
            publication_store=restarted_store,
            use_binding_digest=digest_payload({"campaign_request_id": "campaign:two"}),
            now=1_800_000_013,
        )


def test_proposer_capability_has_one_in_flight_exact_use(tmp_path):
    proposal = _proposal_result()
    store = _durable_store(tmp_path, "in-flight")
    verified = verify_and_store_topology_proposer_provenance(
        call_receipt=proposal.call_receipt,
        admission_receipt=proposal.admission_receipt,
        signed_receipt=_signed(proposal),
        key_resolver=_Keys(),
        signature_verifier=_Verifier(),
        publication_store=store,
        receipt_store=store,
        now=1_800_000_010,
    )
    binding = digest_payload({"campaign_request_id": "campaign:one"})
    assert reserve_verified_topology_proposer_provenance_use(
        verified,
        publication_store=store,
        use_binding_digest=binding,
        now=1_800_000_011,
    ) is not None
    with pytest.raises(ValueError, match="capability_in_use"):
        reserve_verified_topology_proposer_provenance_use(
            verified,
            publication_store=store,
            use_binding_digest=binding,
            now=1_800_000_011,
        )
    assert release_verified_topology_proposer_provenance_use(
        verified,
        use_binding_digest=binding,
    ) is True
    assert consume_verified_topology_proposer_provenance(
        verified,
        publication_store=store,
        use_binding_digest=binding,
        now=1_800_000_011,
    ) is not None


def test_proposer_trust_time_revocation_and_admission_splice_fail_closed(tmp_path):
    proposal = _proposal_result()
    cases = (
        {"signature_verifier": type("Bad", (), {"verify": lambda *_: False})()},
        {"key_resolver": type("NoKeys", (), {"resolve": lambda *_: None})()},
        {"revoked_key_epochs": ("epoch-1",)},
        {"now": 1_800_001_000},
        {"leeway_seconds": 61},
    )
    for index, overrides in enumerate(cases):
        store = _durable_store(tmp_path, f"failure-{index}")
        values = {
            "call_receipt": proposal.call_receipt,
            "admission_receipt": proposal.admission_receipt,
            "signed_receipt": _signed(proposal),
            "key_resolver": _Keys(),
            "signature_verifier": _Verifier(),
            "publication_store": store,
            "receipt_store": store,
            "now": 1_800_000_010,
            **overrides,
        }
        with pytest.raises(ValueError):
            verify_and_store_topology_proposer_provenance(**values)
    spliced = replace(proposal.admission_receipt, proposer_output_digest="sha256:" + "0" * 64)
    with pytest.raises(ValueError):
        build_signed_topology_proposer_provenance_receipt(
            call_receipt=proposal.call_receipt,
            admission_receipt=spliced,
            signer_public_key="public-key:proposer",
            signer_key_fingerprint="fingerprint:proposer",
            key_epoch="epoch-1",
            issued_at=1_800_000_000,
            expires_at=1_800_000_300,
            nonce="nonce:splice",
            signature="signature:valid",
        )


def test_nonpositive_ttl_mapping_and_store_failure_retry_are_safe(tmp_path):
    proposal = _proposal_result()
    invalid = _rehash_signed(
        replace(
            _signed(proposal),
            issued_at=1_800_000_100,
            expires_at=1_800_000_050,
            nonce="nonce:negative-ttl",
        )
    )
    store = _durable_store(tmp_path, "negative-ttl")
    with pytest.raises(ValueError, match="ttl_invalid"):
        verify_and_store_topology_proposer_provenance(
            call_receipt=proposal.call_receipt,
            admission_receipt=proposal.admission_receipt,
            signed_receipt=invalid.to_dict(),
            key_resolver=_Keys(),
            signature_verifier=_Verifier(),
            publication_store=store,
            receipt_store=store,
            now=1_800_000_075,
        )

    publication_store = _durable_store(tmp_path, "retry-publication")
    receipt_store = _FailOnceDurableStore(publication_store)
    signed = _signed(proposal)
    with pytest.raises(ValueError, match="store_failed"):
        verify_and_store_topology_proposer_provenance(
            call_receipt=proposal.call_receipt,
            admission_receipt=proposal.admission_receipt,
            signed_receipt=signed,
            key_resolver=_Keys(),
            signature_verifier=_Verifier(),
            publication_store=publication_store,
            receipt_store=receipt_store,
            now=1_800_000_010,
        )
    retried = verify_and_store_topology_proposer_provenance(
        call_receipt=proposal.call_receipt,
        admission_receipt=proposal.admission_receipt,
        signed_receipt=signed,
        key_resolver=_Keys(),
        signature_verifier=_Verifier(),
        publication_store=publication_store,
        receipt_store=receipt_store,
        now=1_800_000_010,
    )
    assert retried.receipt.receipt_id == signed.receipt_id
