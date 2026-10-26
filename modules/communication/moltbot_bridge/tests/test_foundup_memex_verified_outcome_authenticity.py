"""Security tests for authenticated resident FoundUp Memex outcomes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_authenticity import (
    VERIFIED_OUTCOME_BINDING_SCHEMA,
    VERIFIED_OUTCOME_RECORD_SCHEMA,
    consume_verified_foundup_memex_outcome,
    verify_and_issue_foundup_memex_outcome,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_receipt_rehydration import (
    verified_outcome_evidence_bundle_digest,
)
from modules.communication.moltbot_bridge.src.foundup_brain_current_state import (
    assemble_foundup_brain_current_state,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    build_operational_context_snapshot,
)
from modules.communication.moltbot_bridge.src.reddog_signed_receipt_chain import SignedReceipt
from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
    reddog_verified_pattern_memory_record_id,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_pattern_memory_admission_invoke import (
    build_queue_authorized_verified_outcome_record,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PREFIX_RECEIPT,
    canonical_signing_input,
)
from modules.communication.moltbot_bridge.tests.holoindex_freshness_receipt_test_helpers import (
    build_fresh_holoindex_receipt,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
FOUNDUP = "foundups-agent"
SNAPSHOT = "sha256:" + "1" * 64
SNAPSHOT_DIGEST = "sha256:" + "2" * 64
HEAD = "3" * 40
NOW = 1_800_000_000
VERIFIED_AT = "2027-01-15T07:59:55+00:00"
PUBLIC_KEY = "test-public-key"
REDDOG_ID = "reddog-0102"
RUNTIME_RECEIPT_ID = "reddog_model_runtime_binding:test"
RUNTIME_DIGEST = "sha256:" + "8" * 64


class _Source:
    def __init__(self, record):
        self.record = record
        self.calls = []

    def load_verified_outcome(self, record_id):
        self.calls.append(record_id)
        return dict(self.record)


class _ReplayStore:
    def __init__(self):
        self.seen = set()
        self.batches = []

    def consume_once(self, receipt_id):
        return self.consume_many_once((receipt_id,))

    def consume_many_once(self, receipt_ids):
        candidates = tuple(receipt_ids)
        self.batches.append(candidates)
        if not candidates or len(set(candidates)) != len(candidates):
            return False
        if self.seen.intersection(candidates):
            return False
        self.seen.update(candidates)
        return True


class _SignatureVerifier:
    def verify(self, public_key, signing_input, signature):
        expected = hashlib.sha256(f"{public_key}|{signing_input}".encode()).hexdigest()
        return signature == expected


def _record(**record_overrides):
    verifier = _verifier_receipt()
    held_out = _held_out_receipt(verifier)
    binding = {
        "schema_version": VERIFIED_OUTCOME_BINDING_SCHEMA,
        "foundup_id": FOUNDUP,
        "snapshot_id": SNAPSHOT,
        "snapshot_content_digest": SNAPSHOT_DIGEST,
        "work_order_id": "work-order-1",
        "slice_id": "FOUNDUP_MEMEX_VERIFIED_OUTCOME_AUTHENTICITY_GATE_PHASE1",
        "job_id": "improvement-job-1",
        "worker_id": "author-worker",
        "verifier_id": "independent-verifier",
        "head_sha": HEAD,
        "runtime_binding_receipt_id": RUNTIME_RECEIPT_ID,
        "runtime_binding_digest": RUNTIME_DIGEST,
        "verification_receipt_digest": _digest(verifier),
        "held_out_receipt_digest": _digest(held_out),
        "verified_at": VERIFIED_AT,
    }
    binding.update(record_overrides.pop("binding", {}))
    gate_receipt = {
        "work_order_id": "work-order-1",
        "slice_name": "FOUNDUP_MEMEX_VERIFIED_OUTCOME_AUTHENTICITY_GATE_PHASE1",
        "gate_id": held_out["gate_id"],
        "ratchet_id": "outcome_ratchet_1234",
        "verifier_receipt_id": verifier["receipt_id"],
        "improvement_job_id": "improvement-job-1",
        "held_out_suite_id": held_out["held_out_suite_id"],
        "held_out_suite_digest": held_out["held_out_suite_digest"],
        "model_runtime_binding_receipt_id": held_out["model_runtime_binding_receipt_id"],
        "model_runtime_binding_digest": held_out["model_runtime_binding_digest"],
        "candidate_head_sha": HEAD,
        "regression_test_count": 7,
        "pattern_memory_admission_allowed": True,
    }
    record = build_queue_authorized_verified_outcome_record(
        gate_result={"accepted": True, "receipt": gate_receipt},
        gate_receipt=gate_receipt,
        admission_request={
            "work_order_id": "work-order-1",
            "admission_metadata": binding,
        },
    )
    assert record["schema_version"] == VERIFIED_OUTCOME_RECORD_SCHEMA
    record.update(record_overrides)
    return record


def _verifier_receipt(**overrides):
    seed = {
        "work_order_id": "work-order-1",
        "slice_name": "FOUNDUP_MEMEX_VERIFIED_OUTCOME_AUTHENTICITY_GATE_PHASE1",
        "verifier_id": "independent-verifier",
        "worker_id": "author-worker",
        "assurance_reservation_id": "reservation-1",
        "assurance_reservation_digest": "sha256:" + "a" * 64,
        "verifier_task_id": "verifier-task-1",
        "base_sha": "b" * 40,
        "head_sha": HEAD,
        "changed_paths": ["modules/communication/moltbot_bridge/src/example.py"],
        "diff_digest": "sha256:" + "c" * 64,
        "test_evidence_digest": "sha256:" + "d" * 64,
        "signed_authority_digest": "sha256:" + "e" * 64,
        "receipt_chain_terminal_hash": "sha256:" + "f" * 64,
        "worktree_receipt_digest": "sha256:" + "1" * 64,
        "holoindex_freshness_receipt_digest": "sha256:" + "2" * 64,
        "model_runtime_binding_receipt_id": RUNTIME_RECEIPT_ID,
        "model_runtime_binding_digest": RUNTIME_DIGEST,
        "memex_supply_receipt_id": None,
        "memex_supply_digest": "",
        "rejection_reasons": [],
    }
    seed.update(overrides)
    receipt_seed = dict(seed)
    receipt_seed["changed_paths"] = sorted(seed["changed_paths"])
    receipt_seed["model_runtime_binding_receipt_id"] = (
        seed["model_runtime_binding_receipt_id"] or ""
    )
    receipt_seed["memex_supply_receipt_id"] = seed["memex_supply_receipt_id"] or ""
    return {
        "receipt_id": "wre_slice_verify_"
        + _digest(receipt_seed).removeprefix("sha256:")[:16],
        **seed,
        "accepted": True,
        "no_command_execution_performed": True,
        "no_pr_publish_performed": True,
        "no_merge_performed": True,
        "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
        "no_holoindex_reindex_performed": True,
    }


def _held_out_receipt(verifier, **overrides):
    seed = {
        "work_order_id": verifier["work_order_id"],
        "slice_name": verifier["slice_name"],
        "improvement_job_id": "improvement-job-1",
        "verifier_receipt_id": verifier["receipt_id"],
        "ratchet_id": "outcome_ratchet_1234",
        "held_out_suite_id": "held-out-suite-1",
        "held_out_suite_digest": "sha256:" + "4" * 64,
        "baseline_digest": "sha256:" + "5" * 64,
        "candidate_digest": "sha256:" + "6" * 64,
        "candidate_head_sha": verifier["head_sha"],
        "holoindex_freshness_receipt_digest": "sha256:" + "7" * 64,
        "model_runtime_binding_receipt_id": RUNTIME_RECEIPT_ID,
        "model_runtime_binding_digest": RUNTIME_DIGEST,
        "pattern_memory_admission_requested": True,
        "pattern_memory_admission_allowed": True,
        "rejection_reasons": [],
    }
    seed.update(overrides)
    receipt_seed = dict(seed)
    receipt_seed["model_runtime_binding_receipt_id"] = (
        seed["model_runtime_binding_receipt_id"] or ""
    )
    return {
        "gate_id": "held_out_recursive_gate_"
        + _digest(receipt_seed).removeprefix("sha256:")[:16],
        **seed,
        "regression_test_count": 7,
        "no_command_execution_performed": True,
        "no_test_execution_performed": True,
        "no_pattern_memory_write_performed": True,
        "no_pr_publish_performed": True,
        "no_merge_performed": True,
        "no_holoindex_reindex_performed": True,
    }


def _rehash_verifier(payload):
    seed = dict(payload)
    for key in (
        "receipt_id",
        "accepted",
        "no_command_execution_performed",
        "no_pr_publish_performed",
        "no_merge_performed",
        "no_pattern_memory_write_performed",
        "no_reward_settlement_performed",
        "no_holoindex_reindex_performed",
    ):
        seed.pop(key, None)
    seed["changed_paths"] = sorted(seed["changed_paths"])
    seed["model_runtime_binding_receipt_id"] = (
        seed["model_runtime_binding_receipt_id"] or ""
    )
    seed["memex_supply_receipt_id"] = seed["memex_supply_receipt_id"] or ""
    payload["receipt_id"] = "wre_slice_verify_" + _digest(seed).removeprefix("sha256:")[:16]
    return payload


def _rehash_held_out(payload):
    seed = dict(payload)
    for key in (
        "gate_id",
        "regression_test_count",
        "no_command_execution_performed",
        "no_test_execution_performed",
        "no_pattern_memory_write_performed",
        "no_pr_publish_performed",
        "no_merge_performed",
        "no_holoindex_reindex_performed",
    ):
        seed.pop(key, None)
    seed["model_runtime_binding_receipt_id"] = (
        seed["model_runtime_binding_receipt_id"] or ""
    )
    payload["gate_id"] = "held_out_recursive_gate_" + _digest(seed).removeprefix("sha256:")[:16]
    return payload


def _signed_receipt(
    record,
    *,
    verification_receipt=None,
    held_out_receipt=None,
    issued_at=NOW - 5,
    signature_ok=True,
    receipt_id="signed-outcome-1",
):
    verifier = verification_receipt if verification_receipt is not None else _verifier_receipt()
    held_out = held_out_receipt if held_out_receipt is not None else _held_out_receipt(verifier)
    payload = {
        "receipt_id": receipt_id,
        "work_order_id": record["work_order_id"],
        "reddog_id": REDDOG_ID,
        "prev_receipt_hash": None,
        "covered_action_digest": verified_outcome_evidence_bundle_digest(
            record=record,
            verifier_receipt=verifier,
            held_out_receipt=held_out,
        ),
        "reward_account": None,
        "issued_at": issued_at,
        "signature": "",
    }
    signing_input = canonical_signing_input(payload, PREFIX_RECEIPT)
    payload["signature"] = hashlib.sha256(
        f"{PUBLIC_KEY}|{signing_input}".encode()
    ).hexdigest()
    if not signature_ok:
        payload["signature"] = "bad-signature"
    return SignedReceipt(**payload)


def _issue(
    record=None,
    *,
    source=None,
    replay_store=None,
    receipt=None,
    verification_receipt=None,
    held_out_receipt=None,
    **overrides,
):
    value = record or _record()
    verifier = verification_receipt if verification_receipt is not None else _verifier_receipt()
    held_out = held_out_receipt if held_out_receipt is not None else _held_out_receipt(verifier)
    return verify_and_issue_foundup_memex_outcome(
        source=source or _Source(value),
        record_id=reddog_verified_pattern_memory_record_id(value),
        verification_receipt=verifier,
        held_out_receipt=held_out,
        signed_receipts=(receipt or _signed_receipt(
            value,
            verification_receipt=verifier,
            held_out_receipt=held_out,
        ),),
        reddog_public_key=PUBLIC_KEY,
        signature_verifier=_SignatureVerifier(),
        reddog_id=REDDOG_ID,
        expected_foundup_id=FOUNDUP,
        expected_snapshot_id=SNAPSHOT,
        expected_snapshot_content_digest=SNAPSHOT_DIGEST,
        replay_store=replay_store or _ReplayStore(),
        now_epoch=NOW,
        **overrides,
    )


def _digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def test_valid_authoritative_record_issues_one_shot_capability() -> None:
    record = _record()
    source = _Source(record)
    capability = _issue(record, source=source)
    projected = consume_verified_foundup_memex_outcome(
        capability,
        expected_foundup_id=FOUNDUP,
        expected_snapshot_id=SNAPSHOT,
        expected_snapshot_content_digest=SNAPSHOT_DIGEST,
        now_epoch=NOW,
    )
    assert source.calls == [reddog_verified_pattern_memory_record_id(record)]
    assert projected is not None
    assert projected["accepted"] is True
    assert projected["held_out_passed"] is True
    assert projected["verification_receipt_id"] == record["verifier_receipt_id"]
    assert projected["held_out_receipt_id"] == record["gate_id"]
    assert consume_verified_foundup_memex_outcome(
        capability,
        expected_foundup_id=FOUNDUP,
        expected_snapshot_id=SNAPSHOT,
        expected_snapshot_content_digest=SNAPSHOT_DIGEST,
        now_epoch=NOW,
    ) is None


def _brain_snapshot():
    created_at = "2027-01-15T08:00:00+00:00"
    snapshot_result = build_operational_context_snapshot(
        repo_state={
            "head_sha": HEAD,
            "dirty_paths": (),
            "dirty_digest": "sha256:clean",
            "worktree_digest": "sha256:worktrees",
        },
        work_state_snapshot={
            "schema_version": "reddog_authoritative_work_state.v1",
            "revision": "sha256:resident-work-state",
            "selected_slice": "FOUNDUP_MEMEX_VERIFIED_OUTCOME_AUTHENTICITY_GATE_PHASE1",
            "worker_claims": (),
            "wre_queue_items": (),
        },
        holoindex_receipt=build_fresh_holoindex_receipt(
            repo_root=REPO_ROOT,
            head_sha=HEAD,
            generated_at=created_at,
        ),
        changed_paths=(),
        now_iso=created_at,
        breadcrumbs=[{"breadcrumb_id": "b1", "continuity_id": FOUNDUP}],
        breadcrumb_scope=FOUNDUP,
        brain_state={
            "available": True,
            "signature_digest": "sha256:brain",
            "repo_head_sha": HEAD,
            "work_state_revision": "sha256:resident-work-state",
            "record_count": 1,
        },
    )
    assert snapshot_result.accepted and snapshot_result.snapshot is not None
    return snapshot_result.snapshot


def test_resident_brain_consumes_authoritatively_bound_capability() -> None:
    snapshot = _brain_snapshot()
    record = _record(
        binding={
            "snapshot_id": snapshot.snapshot_receipt_id,
            "snapshot_content_digest": snapshot.snapshot_content_digest,
        }
    )
    verifier = _verifier_receipt()
    held_out = _held_out_receipt(verifier)
    capability = verify_and_issue_foundup_memex_outcome(
        source=_Source(record),
        record_id=reddog_verified_pattern_memory_record_id(record),
        verification_receipt=verifier,
        held_out_receipt=held_out,
        signed_receipts=(_signed_receipt(
            record,
            verification_receipt=verifier,
            held_out_receipt=held_out,
        ),),
        reddog_public_key=PUBLIC_KEY,
        signature_verifier=_SignatureVerifier(),
        reddog_id=REDDOG_ID,
        expected_foundup_id=FOUNDUP,
        expected_snapshot_id=snapshot.snapshot_receipt_id,
        expected_snapshot_content_digest=snapshot.snapshot_content_digest,
        replay_store=_ReplayStore(),
        now_epoch=NOW,
    )
    assembled = assemble_foundup_brain_current_state(
        foundup_id=FOUNDUP,
        snapshot=snapshot,
        identity={"foundup_id": FOUNDUP, "name": "Foundups Agent"},
        roadmap_state={
            "foundup_id": FOUNDUP,
            "roadmap_id": "foundups-agent-roadmap",
            "version": "phase1",
            "content_digest": "sha256:roadmap",
        },
        verified_outcomes=(capability,),
        now_iso="2027-01-15T08:01:00+00:00",
        policy_foundup_scope=(FOUNDUP,),
    )
    assert assembled.accepted is True
    assert assembled.view is not None
    assert assembled.rejection_reasons == ()
    assert len(assembled.view.verified_outcomes) == 1
    assert assembled.view.verified_outcomes[0]["scope_origin"] == "verified_capability"
    assert consume_verified_foundup_memex_outcome(
        capability,
        expected_foundup_id=FOUNDUP,
        expected_snapshot_id=snapshot.snapshot_receipt_id,
        expected_snapshot_content_digest=snapshot.snapshot_content_digest,
        now_epoch=NOW + 60,
    ) is None


def _brain_capability(snapshot, replay, *, receipt_id="signed-outcome-1"):
    record = _record(
        binding={
            "snapshot_id": snapshot.snapshot_receipt_id,
            "snapshot_content_digest": snapshot.snapshot_content_digest,
        }
    )
    verifier = _verifier_receipt()
    held_out = _held_out_receipt(verifier)
    return verify_and_issue_foundup_memex_outcome(
        source=_Source(record),
        record_id=reddog_verified_pattern_memory_record_id(record),
        verification_receipt=verifier,
        held_out_receipt=held_out,
        signed_receipts=(_signed_receipt(
            record,
            verification_receipt=verifier,
            held_out_receipt=held_out,
            receipt_id=receipt_id,
        ),),
        reddog_public_key=PUBLIC_KEY,
        signature_verifier=_SignatureVerifier(),
        reddog_id=REDDOG_ID,
        expected_foundup_id=FOUNDUP,
        expected_snapshot_id=snapshot.snapshot_receipt_id,
        expected_snapshot_content_digest=snapshot.snapshot_content_digest,
        replay_store=replay,
        now_epoch=NOW,
    )


def _assemble_brain(snapshot, capabilities, **overrides):
    values = {
        "foundup_id": FOUNDUP,
        "snapshot": snapshot,
        "identity": {"foundup_id": FOUNDUP, "name": "Foundups Agent"},
        "roadmap_state": {
            "foundup_id": FOUNDUP,
            "roadmap_id": "foundups-agent-roadmap",
            "version": "phase1",
            "content_digest": "sha256:roadmap",
        },
        "verified_outcomes": capabilities,
        "now_iso": "2027-01-15T08:01:00+00:00",
        "policy_foundup_scope": (FOUNDUP,),
    }
    values.update(overrides)
    return assemble_foundup_brain_current_state(**values)


def test_later_invalid_outcome_does_not_partially_burn_valid_capability() -> None:
    snapshot = _brain_snapshot()
    replay = _ReplayStore()
    capability = _brain_capability(snapshot, replay)

    rejected = _assemble_brain(snapshot, (capability, object()))

    assert rejected.accepted is False
    assert "verified_outcome_runtime_binding_required" in rejected.rejection_reasons
    assert replay.seen == set()
    assert replay.batches == []
    assert _assemble_brain(snapshot, (capability,)).accepted is True


def test_brain_admits_all_outcomes_through_one_durable_batch() -> None:
    snapshot = _brain_snapshot()
    replay = _ReplayStore()
    first = _brain_capability(snapshot, replay, receipt_id="signed-outcome-1")
    second = _brain_capability(snapshot, replay, receipt_id="signed-outcome-2")

    accepted = _assemble_brain(snapshot, (first, second))

    assert accepted.accepted is True
    assert replay.batches == [("signed-outcome-1", "signed-outcome-2")]
    assert consume_verified_foundup_memex_outcome(
        first,
        expected_foundup_id=FOUNDUP,
        expected_snapshot_id=snapshot.snapshot_receipt_id,
        expected_snapshot_content_digest=snapshot.snapshot_content_digest,
        now_epoch=NOW,
    ) is None
    assert consume_verified_foundup_memex_outcome(
        second,
        expected_foundup_id=FOUNDUP,
        expected_snapshot_id=snapshot.snapshot_receipt_id,
        expected_snapshot_content_digest=snapshot.snapshot_content_digest,
        now_epoch=NOW,
    ) is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"roadmap_state": {"foundup_id": FOUNDUP}},
        {"policy_foundup_scope": ("other-foundup",)},
        {
            "identity": {
                "foundup_id": FOUNDUP,
                "name": "Foundups Agent",
                "purpose": "Use sk-example-secret in runtime",
            }
        },
    ],
)
def test_late_brain_rejection_does_not_burn_outcome(overrides) -> None:
    snapshot = _brain_snapshot()
    replay = _ReplayStore()
    capability = _brain_capability(snapshot, replay)

    rejected = _assemble_brain(snapshot, (capability,), **overrides)

    assert rejected.accepted is False
    assert replay.seen == set()
    assert replay.batches == []
    assert _assemble_brain(snapshot, (capability,)).accepted is True


@pytest.mark.parametrize(
    "mutator,error",
    [
        (lambda value: value.update(schema_version="wrong"), "record_schema_invalid"),
        (lambda value: value.update(pattern_memory_admission_allowed=False), "not_admitted"),
        (lambda value: value.update(candidate_head_sha="bad"), "head_sha_invalid"),
        (lambda value: value.update(extra="forged"), "record_schema_invalid"),
        (lambda value: value["admission_metadata"].update(foundup_id="other"), "foundup_id_mismatch"),
        (lambda value: value["admission_metadata"].update(snapshot_id="other"), "snapshot_id_mismatch"),
        (lambda value: value["admission_metadata"].update(verifier_id="author-worker"), "verifier_not_independent"),
    ],
)
def test_malformed_scoped_or_nonindependent_records_fail(mutator, error) -> None:
    record = _record()
    mutator(record)
    with pytest.raises(ValueError, match=error):
        _issue(record)


def test_tampered_record_with_old_record_id_fails() -> None:
    original = _record()
    tampered = _record(candidate_head_sha="7" * 40)
    source = _Source(tampered)
    with pytest.raises(ValueError, match="record_id_mismatch"):
        verify_and_issue_foundup_memex_outcome(
            source=source,
            record_id=reddog_verified_pattern_memory_record_id(original),
            verification_receipt=_verifier_receipt(),
            held_out_receipt=_held_out_receipt(_verifier_receipt()),
            signed_receipts=(_signed_receipt(tampered),),
            reddog_public_key=PUBLIC_KEY,
            signature_verifier=_SignatureVerifier(),
            reddog_id=REDDOG_ID,
            expected_foundup_id=FOUNDUP,
            expected_snapshot_id=SNAPSHOT,
            expected_snapshot_content_digest=SNAPSHOT_DIGEST,
            replay_store=_ReplayStore(),
            now_epoch=NOW,
        )
