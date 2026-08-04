"""Runtime trust tests for durable, one-use FoundUp Memex outcomes."""

from __future__ import annotations

import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_authenticity import (
    consume_verified_foundup_memex_outcome,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_publisher import (
    SignedVerifiedOutcomeEvidencePublisher,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_runtime_authority import (
    VERIFIED_OUTCOME_RUNTIME_REFERENCE_SCHEMA,
    VerifiedOutcomeRuntimeAuthority,
    VerifiedOutcomeRuntimeReference,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_runtime_store import (
    AuthorityRuntimeVerifiedOutcomeStore,
    build_outcome_evidence_envelope,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX,
    VERIFIED_OUTCOME_SIGNER_ROLE,
    VERIFIED_OUTCOME_SIGNING_OPERATION,
    VerifiedOutcomeSignerPolicy,
    validate_verified_outcome_signing_request,
)
from modules.communication.moltbot_bridge.src.foundup_brain_current_state import (
    assemble_foundup_brain_current_state,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    ReadOnlyAuditTaskSpec,
)
from modules.communication.moltbot_bridge.src.reddog_operational_memex_snapshot_supplier import (
    enrich_readonly_audit_tasks_with_operational_memex,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    canonical_signer_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signed_receipt_chain import (
    build_receipt_payload_for_signing,
)
from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
    reddog_verified_pattern_memory_record_digest,
    reddog_verified_pattern_memory_record_id,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PREFIX_RECEIPT,
    canonical_signing_input,
)
from modules.communication.moltbot_bridge.tests.test_foundup_memex_verified_outcome_authenticity import (
    FOUNDUP,
    NOW,
    PUBLIC_KEY,
    REDDOG_ID,
    _held_out_receipt,
    _brain_snapshot,
    _record,
    _verifier_receipt,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
PRINCIPAL_ID = "principal-012"
PRINCIPAL_PROVIDER = "intake-auth"
KEY_EPOCH = "epoch-1"
AUTHORITY_TIER = "HIGH"
CONSENSUS_DIGEST = "sha256:" + "9" * 64


class _DigestSignatureVerifier:
    def verify(self, public_key: str, signing_input: str, signature: str) -> bool:
        return signature == _signature(public_key, signing_input)


class _Signer:
    def sign(self, request: SigningRequest) -> SigningResponse:
        signature = _signature(request.signer_public_key, request.signing_input)
        audit_mac = "audit-mac"
        audit_input = canonical_signer_audit_attestation_input(
            signing_input=request.signing_input,
            signature=signature,
            audit_mac=audit_mac,
            signer_public_key=request.signer_public_key,
            key_epoch=request.key_epoch,
            requester_principal_id=request.requester_principal_id,
            domain_prefix=VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX,
        )
        return SigningResponse(
            accepted=True,
            signature=signature,
            signer_public_key=request.signer_public_key,
            key_fingerprint=public_key_fingerprint(request.signer_public_key),
            key_epoch=request.key_epoch,
            audit_mac=audit_mac,
            audit_attestation_signature=_signature(
                request.signer_public_key,
                audit_input,
            ),
            boundary_attested=True,
            requester_identity_attested=True,
            signer_loads_no_untrusted_code=True,
            no_secret_material_returned=True,
        )


class _KeyResolver:
    def __init__(self, public_key: str | None = PUBLIC_KEY) -> None:
        self.public_key = public_key

    def resolve(self, reddog_id: str, key_epoch: str) -> str | None:
        if reddog_id != REDDOG_ID or key_epoch != KEY_EPOCH:
            return None
        return self.public_key


class _RevocationOracle:
    def __init__(self, revoked: bool = False) -> None:
        self.revoked = revoked

    def is_revoked(self, **_bindings: str) -> bool:
        return self.revoked


def _signature(public_key: str, signing_input: str) -> str:
    return hashlib.sha256(f"{public_key}|{signing_input}".encode()).hexdigest()


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def _store(tmp_path: Path) -> AuthorityRuntimeVerifiedOutcomeStore:
    tmp_path.mkdir(parents=True, exist_ok=True)
    return AuthorityRuntimeVerifiedOutcomeStore(
        AtomicJsonAuthorityRuntimeStore(
            tmp_path / "authority.json",
            allowed_root=tmp_path,
            repo_root=REPO_ROOT,
        )
    )


def _reference(record: dict) -> VerifiedOutcomeRuntimeReference:
    binding = record["admission_metadata"]
    return VerifiedOutcomeRuntimeReference(
        schema_version=VERIFIED_OUTCOME_RUNTIME_REFERENCE_SCHEMA,
        record_id=reddog_verified_pattern_memory_record_id(record),
        foundup_id=binding["foundup_id"],
        snapshot_id=binding["snapshot_id"],
        snapshot_content_digest=binding["snapshot_content_digest"],
        work_order_id=binding["work_order_id"],
        slice_id=binding["slice_id"],
        job_id=binding["job_id"],
        head_sha=binding["head_sha"],
        content_digest=reddog_verified_pattern_memory_record_digest(record),
        worker_id=binding["worker_id"],
        verifier_id=binding["verifier_id"],
        runtime_binding_receipt_id=binding["runtime_binding_receipt_id"],
        runtime_binding_digest=binding["runtime_binding_digest"],
    )


def _authority(
    store: AuthorityRuntimeVerifiedOutcomeStore,
    *,
    key_resolver: object | None = None,
    revocation_oracle: object | None = None,
    now_epoch: int = NOW,
) -> VerifiedOutcomeRuntimeAuthority:
    return VerifiedOutcomeRuntimeAuthority(
        store=store,
        outcome_signer_key_resolver=key_resolver or _KeyResolver(),
        signature_verifier=_DigestSignatureVerifier(),
        revocation_oracle=revocation_oracle or _RevocationOracle(),
        issuer_principal_id=PRINCIPAL_ID,
        issuer_principal_provider=PRINCIPAL_PROVIDER,
        reddog_id=REDDOG_ID,
        trusted_now_epoch=lambda: now_epoch,
    )


def _publish(
    tmp_path: Path, *, record: dict | None = None, activate: bool = True
) -> tuple[
    AuthorityRuntimeVerifiedOutcomeStore,
    dict,
    dict,
    dict,
    VerifiedOutcomeRuntimeReference,
]:
    store = _store(tmp_path)
    record = record or _record()
    verifier = _verifier_receipt()
    held_out = _held_out_receipt(verifier)
    publisher = SignedVerifiedOutcomeEvidencePublisher(
        store=store,
        signer=_Signer(),
        signature_verifier=_DigestSignatureVerifier(),
        issuer_principal_id=PRINCIPAL_ID,
        issuer_principal_provider=PRINCIPAL_PROVIDER,
        reddog_id=REDDOG_ID,
        signer_public_key=PUBLIC_KEY,
        key_epoch=KEY_EPOCH,
        authority_tier=AUTHORITY_TIER,
        consensus_receipt_digest=CONSENSUS_DIGEST,
        trusted_now_epoch=lambda: NOW,
    )
    record_id = reddog_verified_pattern_memory_record_id(record)
    assert (
        publisher.publish(
            record_id=record_id,
            record=record,
            verification_receipt=verifier,
            held_out_receipt=held_out,
        )
        == record_id
    )
    assert store.load_envelope(record_id) is None
    if activate:
        assert publisher.activate(record_id) == record_id
    return store, record, verifier, held_out, _reference(record)


def test_staged_evidence_is_not_consumable_before_activation(tmp_path: Path) -> None:
    store, _record_value, _verifier, _held_out, reference = _publish(
        tmp_path,
        activate=False,
    )

    with pytest.raises(ValueError, match="durable_source_missing"):
        _authority(store).issue(reference)

    assert store.activate(reference.record_id) == reference.record_id
    assert _authority(store).issue(reference) is not None


def _consume(capability: object, store: AuthorityRuntimeVerifiedOutcomeStore) -> object:
    reference = _reference(_record())
    return consume_verified_foundup_memex_outcome(
        capability,
        expected_foundup_id=reference.foundup_id,
        expected_snapshot_id=reference.snapshot_id,
        expected_snapshot_content_digest=reference.snapshot_content_digest,
        now_epoch=NOW,
    )


def test_durable_source_issues_and_cross_process_replay_is_one_use(
    tmp_path: Path,
) -> None:
    store, _record_value, _verifier, _held_out, reference = _publish(tmp_path)
    second_store = _store(tmp_path)
    first = _authority(store).issue(reference)
    second = _authority(second_store).issue(reference)

    assert _consume(first, store) is not None
    assert _consume(second, second_store) is None


def test_durable_batch_replay_consumption_is_all_or_nothing(tmp_path: Path) -> None:
    store = _store(tmp_path)

    assert store.consume_once("receipt-a") is True
    assert store.consume_many_once(("receipt-a", "receipt-b")) is False
    assert store.consume_once("receipt-b") is True
    assert store.consume_many_once(("receipt-c", "receipt-d")) is True
    assert store.consume_once("receipt-c") is False
    assert store.consume_once("receipt-d") is False


def test_durable_authority_capability_is_consumed_by_resident_brain(
    tmp_path: Path,
) -> None:
    snapshot = _brain_snapshot()
    record = _record(
        binding={
            "snapshot_id": snapshot.snapshot_receipt_id,
            "snapshot_content_digest": snapshot.snapshot_content_digest,
        }
    )
    store, _record_value, _verifier, _held_out, reference = _publish(
        tmp_path,
        record=record,
    )
    capability = _authority(store).issue(reference)

    assembled = assemble_foundup_brain_current_state(
        foundup_id=FOUNDUP,
        snapshot=snapshot,
        identity={"foundup_id": FOUNDUP, "name": "Foundups Agent"},
        roadmap_state={
            "foundup_id": FOUNDUP,
            "roadmap_id": "runtime-authority-roadmap",
            "version": "phase1",
            "content_digest": "sha256:roadmap",
        },
        verified_outcomes=(capability,),
        now_iso="2027-01-15T08:01:00+00:00",
        policy_foundup_scope=(FOUNDUP,),
    )

    assert assembled.accepted is True
    assert assembled.view is not None
    assert assembled.view.verified_outcomes[0]["outcome_id"] == reference.record_id


def test_supplier_consumes_with_authority_clock_not_policy_timestamp(
    tmp_path: Path,
) -> None:
    snapshot = _brain_snapshot()
    record = _record(
        binding={
            "snapshot_id": snapshot.snapshot_receipt_id,
            "snapshot_content_digest": snapshot.snapshot_content_digest,
        }
    )
    store, _record_value, _verifier, _held_out, reference = _publish(
        tmp_path,
        record=record,
    )
    authority = _authority(store, now_epoch=NOW)
    task = ReadOnlyAuditTaskSpec(
        task_id="task-1",
        description="Read-only Memex clock regression",
        required_skills=("reddog_readonly_audit",),
        estimated_complexity=0.2,
        priority_score=0.9,
        context={
            "assignment": {
                "assignment_id": "assignment-1",
                "lane_id": "repo_code_audit",
                "snapshot_receipt_id": snapshot.snapshot_receipt_id,
                "snapshot_content_digest": snapshot.snapshot_content_digest,
            }
        },
        origin_continuity_id="determination-1",
    )

    result = enrich_readonly_audit_tasks_with_operational_memex(
        tasks=(task,),
        snapshot=snapshot,
        config={
            "foundup_id": FOUNDUP,
            "principal_id": PRINCIPAL_ID,
            "identity": {"foundup_id": FOUNDUP, "name": "Foundups Agent"},
            "roadmap_state": {
                "foundup_id": FOUNDUP,
                "roadmap_id": "runtime-authority-roadmap",
                "version": "phase1",
                "content_digest": "sha256:roadmap",
            },
            "verified_outcome_references": (reference.to_dict(),),
            "policy_issued_at": "2027-01-15T07:00:00+00:00",
            "policy_expires_at": "2027-01-15T08:09:00+00:00",
            "holoindex_generation_id": "generation-1",
            "source_revision": "revision-1",
        },
        verified_outcome_runtime_authority=authority,
        now_iso="2027-01-15T07:30:00+00:00",
    )

    assert result.accepted is True
    assert result.tasks[0].context["memex_now_iso"] == "2027-01-15T08:00:00+00:00"
    assert result.tasks[0].context["memex_policy_issued_at"] == "2027-01-15T07:00:00+00:00"


def test_concurrent_consumers_cannot_both_admit(tmp_path: Path) -> None:
    store, _record_value, _verifier, _held_out, reference = _publish(tmp_path)
    capabilities = (
        _authority(store).issue(reference),
        _authority(_store(tmp_path)).issue(reference),
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(
            pool.map(lambda capability: _consume(capability, store), capabilities)
        )

    assert sum(result is not None for result in results) == 1


def test_missing_source_wrong_key_revocation_and_staleness_fail(tmp_path: Path) -> None:
    empty = _store(tmp_path / "empty")
    missing_reference = _reference(_record())
    with pytest.raises(ValueError, match="durable_source_missing"):
        _authority(empty).issue(missing_reference)

    store, _record_value, _verifier, _held_out, reference = _publish(tmp_path / "valid")
    with pytest.raises(ValueError, match="authoritative_key_unavailable"):
        _authority(store, key_resolver=_KeyResolver("wrong-key")).issue(reference)
    with pytest.raises(ValueError, match="signer_revoked"):
        _authority(store, revocation_oracle=_RevocationOracle(True)).issue(reference)
    with pytest.raises(ValueError, match="expired"):
        _authority(store, now_epoch=NOW + 601).issue(reference)


@pytest.mark.parametrize(
    "field,value",
    [
        ("foundup_id", "other-foundup"),
        ("snapshot_id", "sha256:" + "a" * 64),
        ("snapshot_content_digest", "sha256:" + "b" * 64),
        ("work_order_id", "other-work-order"),
        ("slice_id", "OTHER_SLICE"),
        ("job_id", "other-job"),
        ("head_sha", "f" * 40),
        ("content_digest", "sha256:" + "c" * 64),
        ("worker_id", "other-worker"),
        ("verifier_id", "other-verifier"),
        ("runtime_binding_receipt_id", "reddog_model_runtime_binding:other"),
        ("runtime_binding_digest", "sha256:" + "d" * 64),
    ],
)
def test_reference_substitution_fails_closed(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    store, _record_value, _verifier, _held_out, reference = _publish(tmp_path)
    with pytest.raises(ValueError, match="reference_mismatch|content_digest_mismatch"):
        _authority(store).issue(replace(reference, **{field: value}))


def test_attacker_rehashed_record_and_envelope_cannot_reuse_signature(
    tmp_path: Path,
) -> None:
    store, record, verifier, held_out, reference = _publish(tmp_path)
    authentic = store.load_envelope(reference.record_id)
    assert authentic is not None
    forged_record = copy.deepcopy(record)
    forged_record["gate_result_digest"] = "sha256:" + "e" * 64
    forged_id = reddog_verified_pattern_memory_record_id(forged_record)
    forged = build_outcome_evidence_envelope(
        record_id=forged_id,
        record=forged_record,
        verification_receipt=verifier,
        held_out_receipt=held_out,
        signed_receipt=authentic["signed_receipts"][0],
        issuer_principal_id=PRINCIPAL_ID,
        issuer_principal_provider=PRINCIPAL_PROVIDER,
        reddog_id=REDDOG_ID,
        signer_key_fingerprint=public_key_fingerprint(PUBLIC_KEY),
        key_epoch=KEY_EPOCH,
    )
    store.publish(forged)
    store.activate(forged_id)

    with pytest.raises(ValueError, match="signed_digest_mismatch"):
        _authority(store).issue(_reference(forged_record))


def test_signer_policy_binds_exact_canonical_payload() -> None:
    payload = build_receipt_payload_for_signing(
        receipt_id="verified-outcome-test",
        work_order_id="work-order-1",
        reddog_id=REDDOG_ID,
        prev_receipt_hash=None,
        covered_action_digest="sha256:" + "a" * 64,
        reward_account=None,
        issued_at=NOW,
    )
    signing_input = canonical_signing_input(payload, PREFIX_RECEIPT)
    request = SigningRequest(
        signing_input=signing_input,
        payload_digest=_digest({"signing_input": signing_input}),
        signer_role=VERIFIED_OUTCOME_SIGNER_ROLE,
        signer_public_key=PUBLIC_KEY,
        requester_principal_id=PRINCIPAL_ID,
        nonce=payload["receipt_id"],
        key_epoch=KEY_EPOCH,
        requested_operation=VERIFIED_OUTCOME_SIGNING_OPERATION,
        authority_tier=AUTHORITY_TIER,
        consensus_receipt_digest=CONSENSUS_DIGEST,
    )
    policy = VerifiedOutcomeSignerPolicy(
        issuer_principal_id=PRINCIPAL_ID,
        reddog_id=REDDOG_ID,
        signer_public_key=PUBLIC_KEY,
        key_epoch=KEY_EPOCH,
        authority_tier=AUTHORITY_TIER,
        consensus_receipt_digest=CONSENSUS_DIGEST,
    )

    assert (
        validate_verified_outcome_signing_request(request, policy, now_epoch=NOW)
        == payload
    )
    for forged in (
        replace(request, payload_digest="sha256:" + "0" * 64),
        replace(request, requested_operation="sign_generic_receipt"),
        replace(request, requester_principal_id="attacker"),
        replace(request, signer_public_key="attacker-key"),
        replace(request, nonce="generic-receipt"),
    ):
        assert (
            validate_verified_outcome_signing_request(
                forged,
                policy,
                now_epoch=NOW,
            )
            is None
        )
