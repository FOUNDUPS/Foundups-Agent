"""Adversarial receipt, replay, and capability tests for verified outcomes."""

from __future__ import annotations

import ast
import copy
import hashlib
import pickle
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_authenticity import (
    VerifiedFoundUpOutcomeCapability,
    consume_verified_foundup_memex_outcome,
)
from modules.communication.moltbot_bridge.src.reddog_operational_memex_snapshot_supplier import (
    OperationalMemexSnapshotSupplyConfig,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PREFIX_RECEIPT,
    canonical_signing_input,
)
from modules.communication.moltbot_bridge.tests.test_foundup_memex_verified_outcome_authenticity import (
    FOUNDUP,
    NOW,
    PUBLIC_KEY,
    REPO_ROOT,
    SNAPSHOT,
    SNAPSHOT_DIGEST,
    _ReplayStore,
    _held_out_receipt,
    _issue,
    _record,
    _rehash_held_out,
    _rehash_verifier,
    _signed_receipt,
    _verifier_receipt,
)
from modules.communication.moltbot_bridge.tests.test_foundup_memex_verified_outcome_runtime_authority import (
    _digest,
    _publication_attempt,
    _store,
)
from modules.communication.moltbot_bridge.tests.test_reddog_verified_pattern_memory_sink import (
    _seed_active,
)


def test_invalid_signature_wrong_covered_digest_expiry_and_replay_fail() -> None:
    record = _record()
    with pytest.raises(ValueError, match="signed_receipt_chain_rejected"):
        _issue(record, receipt=_signed_receipt(record, signature_ok=False))

    wrong = _signed_receipt(record)
    wrong.covered_action_digest = "sha256:" + "9" * 64
    wrong.signature = hashlib.sha256(
        f"{PUBLIC_KEY}|{canonical_signing_input(wrong.to_dict(), PREFIX_RECEIPT)}".encode()
    ).hexdigest()
    with pytest.raises(ValueError, match="signed_digest_mismatch"):
        _issue(record, receipt=wrong)

    with pytest.raises(ValueError, match="signature_expired"):
        _issue(record, receipt=_signed_receipt(record, issued_at=NOW - 601))

    replay = _ReplayStore()
    first = _issue(record, replay_store=replay)
    assert consume_verified_foundup_memex_outcome(
        first,
        expected_foundup_id=FOUNDUP,
        expected_snapshot_id=SNAPSHOT,
        expected_snapshot_content_digest=SNAPSHOT_DIGEST,
        now_epoch=NOW - 1,
    ) is None
    assert replay.seen == set()
    assert consume_verified_foundup_memex_outcome(
        first,
        expected_foundup_id=FOUNDUP,
        expected_snapshot_id=SNAPSHOT,
        expected_snapshot_content_digest=SNAPSHOT_DIGEST,
        now_epoch=NOW,
    ) is not None
    second = _issue(record, replay_store=replay)
    assert consume_verified_foundup_memex_outcome(
        second,
        expected_foundup_id=FOUNDUP,
        expected_snapshot_id=SNAPSHOT,
        expected_snapshot_content_digest=SNAPSHOT_DIGEST,
        now_epoch=NOW,
    ) is None

    stale_record = _record(binding={"verified_at": "2027-01-15T07:49:00+00:00"})
    with pytest.raises(ValueError, match="verification_expired"):
        _issue(stale_record)


@pytest.mark.parametrize(
    "receipt_name,mutator,error",
    [
        ("verifier", lambda value: value.update(extra="forged"), "verifier_receipt_schema_invalid"),
        ("verifier", lambda value: value.update(accepted=False), "verifier_receipt_not_accepted"),
        ("verifier", lambda value: value.update(receipt_id="wre_slice_verify_forged"), "verifier_receipt_id_mismatch"),
        ("verifier", lambda value: value.update(diff_digest="sha256:bad"), "verifier_digest_invalid"),
        ("verifier", lambda value: value.update(no_merge_performed=False), "verifier_safety_attestation_invalid"),
        ("held_out", lambda value: value.update(extra="forged"), "held_out_receipt_schema_invalid"),
        ("held_out", lambda value: value.update(pattern_memory_admission_allowed=False), "held_out_admission_not_allowed"),
        ("held_out", lambda value: value.update(gate_id="held_out_recursive_gate_forged"), "held_out_receipt_id_mismatch"),
        ("held_out", lambda value: value.update(held_out_suite_digest="sha256:bad"), "held_out_digest_invalid"),
        ("held_out", lambda value: value.update(regression_test_count=True), "held_out_test_count_invalid"),
        ("held_out", lambda value: value.update(no_test_execution_performed=False), "held_out_safety_attestation_invalid"),
    ],
)
def test_malformed_or_attacker_selected_source_receipts_fail(receipt_name, mutator, error) -> None:
    verifier = _verifier_receipt()
    held_out = _held_out_receipt(verifier)
    mutator(verifier if receipt_name == "verifier" else held_out)
    with pytest.raises(ValueError, match=error):
        _issue(verification_receipt=verifier, held_out_receipt=held_out)


def test_missing_source_receipts_fail_before_signature_admission() -> None:
    record = _record()
    verifier = _verifier_receipt()
    held_out = _held_out_receipt(verifier)
    signed = _signed_receipt(record, verification_receipt=verifier, held_out_receipt=held_out)
    with pytest.raises(ValueError, match="verifier_receipt_schema_invalid"):
        _issue(record, verification_receipt={}, held_out_receipt=held_out, receipt=signed)
    with pytest.raises(ValueError, match="held_out_receipt_schema_invalid"):
        _issue(record, verification_receipt=verifier, held_out_receipt={}, receipt=signed)


def test_substituted_held_out_and_verifier_identity_fail() -> None:
    verifier = _verifier_receipt()
    substituted = _held_out_receipt(verifier, held_out_suite_id="attacker-suite")
    with pytest.raises(ValueError, match="held_out_receipt_digest_mismatch"):
        _issue(verification_receipt=verifier, held_out_receipt=substituted)

    wrong_verifier = _verifier_receipt(verifier_id="other-verifier")
    wrong_held_out = _held_out_receipt(wrong_verifier)
    record = _record(verifier_receipt_id=wrong_verifier["receipt_id"], gate_id=wrong_held_out["gate_id"])
    with pytest.raises(ValueError, match="verification_receipt_digest_mismatch|verifier_identity_mismatch"):
        _issue(record, verification_receipt=wrong_verifier, held_out_receipt=wrong_held_out)


@pytest.mark.parametrize(
    "changes",
    [
        {"improvement_job_id": "other-job"},
        {"ratchet_id": "other-ratchet"},
        {"regression_test_count": 99},
        {
            "model_runtime_binding_receipt_id": "reddog_model_runtime_binding:other",
            "model_runtime_binding_digest": "sha256:" + "8" * 64,
        },
    ],
)
def test_signed_but_internally_conflicting_lineage_fails(changes) -> None:
    with pytest.raises(
        ValueError,
        match="held_out_lineage_mismatch|job_id_mismatch|runtime_binding_receipt_id_mismatch",
    ):
        _issue(_record(**changes))


def test_scope_mismatch_does_not_burn_capability_or_replay_state() -> None:
    replay = _ReplayStore()
    capability = _issue(replay_store=replay)
    assert consume_verified_foundup_memex_outcome(
        capability,
        expected_foundup_id="other-foundup",
        expected_snapshot_id=SNAPSHOT,
        expected_snapshot_content_digest=SNAPSHOT_DIGEST,
        now_epoch=NOW,
    ) is None
    assert replay.seen == set()
    assert consume_verified_foundup_memex_outcome(
        capability,
        expected_foundup_id=FOUNDUP,
        expected_snapshot_id=SNAPSHOT,
        expected_snapshot_content_digest=SNAPSHOT_DIGEST,
        now_epoch=NOW,
    ) is not None


def test_attacker_rehashed_receipts_cannot_reuse_authentic_bundle_signature() -> None:
    original_record = _record()
    original_verifier = _verifier_receipt()
    original_held_out = _held_out_receipt(original_verifier)
    authentic_signature = _signed_receipt(
        original_record,
        verification_receipt=original_verifier,
        held_out_receipt=original_held_out,
    )
    forged_verifier = dict(original_verifier)
    forged_verifier["diff_digest"] = "sha256:" + "8" * 64
    _rehash_verifier(forged_verifier)
    forged_held_out = dict(original_held_out)
    forged_held_out["verifier_receipt_id"] = forged_verifier["receipt_id"]
    _rehash_held_out(forged_held_out)
    forged_record = dict(original_record)
    forged_record["verifier_receipt_id"] = forged_verifier["receipt_id"]
    forged_record["gate_id"] = forged_held_out["gate_id"]
    with pytest.raises(ValueError, match="verification_receipt_digest_mismatch"):
        _issue(
            forged_record,
            receipt=authentic_signature,
            verification_receipt=forged_verifier,
            held_out_receipt=forged_held_out,
        )


def test_capability_cannot_be_constructed_copied_or_pickled() -> None:
    with pytest.raises(TypeError, match="factory_required"):
        VerifiedFoundUpOutcomeCapability()
    capability = _issue()
    with pytest.raises(TypeError, match="copy_forbidden"):
        copy.copy(capability)
    with pytest.raises(TypeError, match="copy_forbidden"):
        copy.deepcopy(capability)
    with pytest.raises(TypeError, match="pickle_forbidden"):
        pickle.dumps(capability)


def test_capability_is_omitted_from_serialized_supply_configuration() -> None:
    capability = _issue()
    payload = OperationalMemexSnapshotSupplyConfig(
        foundup_id=FOUNDUP,
        principal_id="principal-012",
        untrusted_verified_outcomes_supplied=True,
    ).to_dict()
    assert "verified_outcomes" not in payload
    assert payload["verified_outcome_references"] == []
    assert capability not in payload.values()


def test_authentication_modules_have_no_model_network_storage_or_holoindex_effects() -> None:
    paths = (
        REPO_ROOT / "modules" / "communication" / "moltbot_bridge" / "src" / "foundup_memex_verified_outcome_authenticity.py",
        REPO_ROOT / "modules" / "communication" / "moltbot_bridge" / "src" / "foundup_memex_verified_outcome_receipt_rehydration.py",
        REPO_ROOT / "modules" / "communication" / "moltbot_bridge" / "src" / "foundup_memex_verified_outcome_validation.py",
    )
    banned = {"subprocess", "socket", "requests", "sqlite3", "openai", "holo_index"}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert imports.isdisjoint(banned)


def _activation_attempt(tmp_path):
    store, publisher, signer, request = _publication_attempt(tmp_path)
    assert publisher.publish(**request) == request["record_id"]
    _seed_active(tmp_path / "memory.db", request["record_id"], request["record"])
    return store, publisher, signer, request


@pytest.mark.parametrize("error_type", [OSError, RuntimeError, ValueError])
def test_activation_reconciles_lost_commit_acknowledgment(tmp_path, monkeypatch, error_type):
    store, publisher, signer, request = _activation_attempt(tmp_path)
    envelope = store.load_publication(request["record_id"])
    commit, committed = store._store.commit, []
    def lost_ack(snapshot, *, expected_revision):
        commit(snapshot, expected_revision=expected_revision)
        committed.append((tmp_path / "authority.json").read_bytes())
        raise error_type("activation_ack_lost")
    monkeypatch.setattr(store._store, "commit", lost_ack)
    assert publisher.activate(request["record_id"]) == request["record_id"]
    assert len(committed) == len(signer.requests) == 1
    assert (tmp_path / "authority.json").read_bytes() == committed[0]
    assert _store(tmp_path).load_envelope(request["record_id"]) == envelope
    assert publisher.activate(request["record_id"]) == request["record_id"]
    assert len(committed) == 1


@pytest.mark.parametrize("conflicts", [1, 2, 3])
def test_activation_reconciles_unrelated_updates_without_replacing_them(tmp_path, monkeypatch, conflicts):
    store, publisher, signer, request = _activation_attempt(tmp_path)
    raw, attempts = store._store, []
    commit = raw.commit
    envelope = store.load_publication(request["record_id"])
    def other_writer(snapshot, *, expected_revision):
        attempts.append(snapshot)
        if len(attempts) <= conflicts:
            other = raw.load()
            other["unrelated_writer_sequence"] = len(attempts)
            commit(other, expected_revision=other.get("revision"))
        return commit(snapshot, expected_revision=expected_revision)
    monkeypatch.setattr(raw, "commit", other_writer)
    if conflicts == 3:
        with pytest.raises(RuntimeError, match="revision_conflict"):
            publisher.activate(request["record_id"])
        assert store.load_envelope(request["record_id"]) is None
    else:
        assert publisher.activate(request["record_id"]) == request["record_id"]
        assert store.load_envelope(request["record_id"]) == envelope
    assert len(attempts) == min(conflicts + 1, 3)
    assert raw.load()["unrelated_writer_sequence"] == conflicts
    assert store.load_publication(request["record_id"]) == envelope
    assert len(signer.requests) == 1


@pytest.mark.parametrize("winner", ["same-active", "changed-staged", "changed-active", "removed"])
def test_activation_recovery_preserves_a_competing_winner(tmp_path, monkeypatch, winner):
    store, publisher, signer, request = _activation_attempt(tmp_path)
    raw, commits = store._store, []
    commit = raw.commit
    def competing_writer(snapshot, *, expected_revision):
        other = _store(tmp_path)._store
        candidate = other.load()
        entries = candidate["foundup_memex_verified_outcome_authority"]["evidence"]
        if winner == "removed":
            del entries[request["record_id"]]
        else:
            entry = entries[request["record_id"]]
            entry["status"] = "STAGED" if winner == "changed-staged" else "ACTIVE"
            if winner.startswith("changed"):
                envelope = entry["envelope"]
                envelope["issuer_principal_id"] = "different-principal"
                envelope.pop("envelope_digest")
                envelope["envelope_digest"] = _digest(envelope)
        other.commit(candidate, expected_revision=candidate.get("revision"))
        commits.append((tmp_path / "authority.json").read_bytes())
        return commit(snapshot, expected_revision=expected_revision)
    monkeypatch.setattr(raw, "commit", competing_writer)
    if winner == "same-active":
        assert publisher.activate(request["record_id"]) == request["record_id"]
    else:
        with pytest.raises(ValueError, match="activation_(binding_mismatch|stage_missing)"):
            publisher.activate(request["record_id"])
    assert len(commits) == len(signer.requests) == 1
    assert (tmp_path / "authority.json").read_bytes() == commits[0]


@pytest.mark.parametrize("failure", ["io", "runtime", "value", "conflict", "false-ack"])
def test_activation_without_durable_commit_is_not_acknowledged(tmp_path, monkeypatch, failure):
    store, publisher, signer, request = _activation_attempt(tmp_path)
    original, attempts = (tmp_path / "authority.json").read_bytes(), []
    def failed_commit(snapshot, *, expected_revision):
        attempts.append(snapshot)
        if failure == "false-ack":
            return "uncommitted-revision"
        error = {"io": OSError, "runtime": RuntimeError, "value": ValueError, "conflict": RuntimeError}[failure]
        raise error("revision_conflict" if failure == "conflict" else "activation_failed")
    monkeypatch.setattr(store._store, "commit", failed_commit)
    with pytest.raises((OSError, RuntimeError, ValueError)):
        publisher.activate(request["record_id"])
    assert len(attempts) == (3 if failure == "conflict" else 1)
    assert (tmp_path / "authority.json").read_bytes() == original
    assert store.load_envelope(request["record_id"]) is None
    assert len(signer.requests) == 1


@pytest.mark.parametrize("after_commit", [False, True], ids=["conflict", "lost-ack"])
def test_activation_reconciliation_rechecks_current_memory(tmp_path, monkeypatch, after_commit):
    store, publisher, _signer, request = _activation_attempt(tmp_path)
    source, commit, attempts = store._accepted_outcome_source, store._store.commit, []
    def lose_memory(snapshot, *, expected_revision):
        attempts.append(snapshot)
        if after_commit:
            commit(snapshot, expected_revision=expected_revision)
        monkeypatch.setattr(store, "_accepted_outcome_source", SimpleNamespace(load_verified_outcome=lambda _id: None))
        raise RuntimeError("activation_ack_lost" if after_commit else "revision_conflict")
    with monkeypatch.context() as patch:
        patch.setattr(store._store, "commit", lose_memory)
        with pytest.raises(ValueError, match="accepted_record_mismatch"):
            publisher.activate(request["record_id"])
        assert len(attempts) == 1
        assert store.load_envelope(request["record_id"]) is None
    monkeypatch.setattr(store, "_accepted_outcome_source", source)
    assert publisher.activate(request["record_id"]) == request["record_id"]
    assert store.load_verified_outcome(request["record_id"]) == request["record"]


@pytest.mark.parametrize("signal", [KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize("after_commit", [False, True])
def test_activation_commit_cancellation_remains_visible(tmp_path, monkeypatch, signal, after_commit):
    store, publisher, signer, request = _activation_attempt(tmp_path)
    commit, attempts = store._store.commit, []
    def cancelled(snapshot, *, expected_revision):
        attempts.append(snapshot)
        if after_commit:
            commit(snapshot, expected_revision=expected_revision)
        raise signal("activation cancelled")
    with monkeypatch.context() as patch:
        patch.setattr(store._store, "commit", cancelled)
        with pytest.raises(signal):
            publisher.activate(request["record_id"])
    assert len(attempts) == len(signer.requests) == 1
    assert (_store(tmp_path).load_envelope(request["record_id"]) is not None) == after_commit
    assert publisher.activate(request["record_id"]) == request["record_id"]


@pytest.mark.parametrize("failure", ["unreadable", "malformed"])
def test_activation_recovery_does_not_trust_an_unreadable_committed_state(tmp_path, monkeypatch, failure):
    store, publisher, _signer, request = _activation_attempt(tmp_path)
    commit, committed = store._store.commit, []
    def unreadable():
        if failure == "unreadable":
            raise OSError("activation_read_failed")
        return {"foundup_memex_verified_outcome_authority": {"forged": True}}
    def commit_without_readback(snapshot, *, expected_revision):
        commit(snapshot, expected_revision=expected_revision)
        committed.append((tmp_path / "authority.json").read_bytes())
        monkeypatch.setattr(store._store, "load", unreadable)
        raise OSError("activation_ack_lost")
    with monkeypatch.context() as patch:
        patch.setattr(store._store, "commit", commit_without_readback)
        with pytest.raises((OSError, ValueError)):
            publisher.activate(request["record_id"])
    reopened = _store(tmp_path)
    assert reopened.activate(request["record_id"]) == request["record_id"]
    assert len(committed) == 1 and (tmp_path / "authority.json").read_bytes() == committed[0]
