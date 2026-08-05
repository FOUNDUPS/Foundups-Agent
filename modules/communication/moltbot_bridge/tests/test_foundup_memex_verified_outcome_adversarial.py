"""Adversarial receipt, replay, and capability tests for verified outcomes."""

from __future__ import annotations

import ast
import copy
import hashlib
import pickle

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
