"""Non-initial installed metadata; real crypto, synthetic owner/selection custody."""
from copy import deepcopy
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.tests.installed_work_admission_test_support import (
    setup_installed_work, verify, write_manifest, resign_policy, prior, contract, policy_contract, NOW,
)


@pytest.fixture
def current(tmp_path, monkeypatch):
    return setup_installed_work(tmp_path, monkeypatch)


def test_real_signed_work_manifest_and_current_e0_bind_installed_metadata(current):
    result = verify(current)
    assert result.manifest_id == current["manifest"]["manifest_id"]
    assert result.owner_policy_id == current["e0"]["policy"]["policy_id"]
    assert result.installed_runtime_descriptor_digest == current["e0"]["policy"]["grant_authority_installed_runtime_descriptor_digest"]
    assert result.service_archive_digest == result.archive_source_descriptor_digest == ""
    assert current["manifest"]["schema_version"] == contract.SCHEMA_VERSION_V2
    assert "publication_receipt_id" in current["manifest"]
    assert "enrollment_approval_digest" not in current["manifest"]


@pytest.mark.parametrize("field", ["signature", "signer_audit_attestation_signature"])
def test_manifest_signature_and_attestation_are_not_policy_endorsement_substitutes(current, field):
    current["manifest"][field] = "invalid"
    write_manifest(current)
    with pytest.raises(ValueError):
        verify(current)


def test_forged_e0_signature_is_rejected_before_manifest_read(current, monkeypatch):
    current["e0"]["policy"]["signature"] = "invalid"
    monkeypatch.setattr(prior.verifier_module, "_read_manifest", lambda *a: pytest.fail("artifact read before E0"))
    with pytest.raises(ValueError):
        verify(current)


@pytest.mark.parametrize("field,value", [
    ("generation", 1), ("generation", True), ("generation", 2.0),
    ("allowed_operations", ["signer_socket_peer_handshake"]),
    ("allowed_operations", ["worktree_create", "worktree_delete"]),
    ("allowed_authority_tiers", ["LOW"]), ("allowed_authority_tiers", ["ULTRA"]),
    ("consensus_required_tiers", []), ("issued_at", True),
    ("expires_at", NOW), ("expires_at", NOW + 901),
])
def test_new_policy_requires_non_initial_exact_work_scope_and_time(current, field, value):
    policy = current["e0"]["policy"]
    policy[field] = value
    resign_policy(current)
    with pytest.raises(ValueError):
        policy_contract.validated_signer_owner_e0_policy(policy, now_epoch=NOW)


@pytest.mark.parametrize("field", [
    "grant_authority_manifest_id", "grant_authority_artifact_generation_digest",
    "grant_authority_config_digest", "grant_authority_run_packet_digest",
    "grant_authority_source_repo_root_digest", "grant_authority_source_policy_digest",
    "grant_authority_installed_runtime_descriptor_digest", "owner_config_id",
    "grant_authority_permission_snapshot_digest", "target_signer_key_fingerprint",
])
def test_signed_policy_substitution_does_not_replace_current_bindings(current, field):
    current["e0"]["policy"][field] = contract.raw_digest(b"substitution")
    resign_policy(current)
    with pytest.raises((ValueError, FileNotFoundError)):
        verify(current)


@pytest.mark.parametrize("filename", contract.REQUIRED_INSTALLED_GRANT_RUNTIME_ARTIFACTS)
def test_changed_artifact_bytes_rejected(current, filename):
    path = current["harness"].runtime_root / filename
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="artifact_changed"):
        verify(current)


@pytest.mark.parametrize("field", ["runtime_profile", "schema_version", "signer_service_config_digest"])
def test_signed_cross_profile_or_issuer_config_manifest_is_not_target_authority(current, field):
    if field == "runtime_profile": value = contract.RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE
    elif field == "schema_version": value = contract.SCHEMA_VERSION_INITIAL_V2
    else: value = current["e0"]["policy"]["grant_authority_config_digest"]
    current["manifest"][field] = value
    write_manifest(current)
    with pytest.raises(ValueError):
        verify(current)


@pytest.mark.parametrize("kind", ["owner", "expiry", "rollback", "selection"])
def test_no_binding_returned_after_late_owner_clock_or_selection_failure(current, monkeypatch, kind):
    from modules.communication.moltbot_bridge.src import reddog_signer_system_service_manifest_selection_loader as loader
    monkeypatch.setattr(loader, "_load_owner_config", lambda *a, **k: deepcopy(current["owner"]))
    original = prior.verifier_module._installed_source_policy
    def change(*args):
        value = original(*args)
        if kind == "owner":
            current["owner"]["config_id"] = contract.raw_digest(b"changed owner")
        elif kind == "selection":
            prior._CURRENT_SELECTION["generation_revision"] = "changed-generation"
        else:
            moment = current["e0"]["policy"]["expires_at"] if kind == "expiry" else NOW - 1
            monkeypatch.setattr(prior.verifier_module, "_now_epoch", lambda: moment)
        return value
    monkeypatch.setattr(prior.verifier_module, "_installed_source_policy", change)
    with pytest.raises(ValueError):
        verify(current)


def test_new_schema_has_distinct_signature_domain_and_final_backref_coverage(current):
    policy = current["e0"]["policy"]
    assert policy_contract.canonical_signer_owner_e0_policy_input(policy).startswith(policy_contract.POLICY_SCHEMA_V11)
    original = policy_contract.signer_owner_e0_authority_binding_digest(policy)
    before = policy_contract.signer_owner_e0_policy_id(policy)
    changed = deepcopy(policy)
    changed["grant_authority_permission_snapshot_digest"] = contract.raw_digest(b"receipt")
    changed["target_signer_generation_id"] = contract.raw_digest(b"generation")
    assert policy_contract.signer_owner_e0_authority_binding_digest(changed) == original
    assert policy_contract.signer_owner_e0_policy_id(changed) != before


def test_installed_work_metadata_does_not_open_low_service_dispatch(current):
    from modules.communication.moltbot_bridge.src.reddog_grant_authority_service import _policy_scope
    with pytest.raises(ValueError):
        _policy_scope(current["e0"]["policy"])


def test_missing_owner_and_wrong_root_rejected(current):
    args = dict(repo_root=current["harness"].repo_root,
        grant_root=current["harness"].runtime_root, policy=current["e0"]["policy"])
    with pytest.raises(ValueError, match="owner_missing"):
        prior.verifier_module.verify_current_grant_service_artifacts(**args)
    args["grant_root"] = Path(args["grant_root"]) / "other"
    with pytest.raises(ValueError, match="root_mismatch"):
        prior.verifier_module.verify_current_grant_service_artifacts(**args,
            owner_config_path=current["e0"]["owner_config_path"])


@pytest.mark.parametrize("mutation", ["repo", "self_key"])
def test_producer_rejects_installed_bundle_repo_or_signer_alias(current, mutation):
    from modules.communication.moltbot_bridge.tests.installed_work_admission_test_support import installed_bundle
    from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import produce_signed_runtime_artifact_manifest
    e0, harness = current["e0"], current["harness"]
    if mutation == "self_key":
        e0["policy"]["grant_authority_public_key"] = current["manifest"]["signer_public_key"]
        e0["policy"]["grant_authority_key_fingerprint"] = current["manifest"]["signer_key_fingerprint"]
    repo = harness.repo_root if mutation == "self_key" else harness.repo_root / "other"
    for name, body in installed_bundle(e0, repo).items():
        (harness.runtime_root / name).write_bytes(body)
    result = produce_signed_runtime_artifact_manifest(manifest_directory=harness.manifest_directory,
        nonce="bad-bundle", issued_at=NOW, expires_at=NOW + 120, context=harness.context,
        runtime_profile=contract.RUNTIME_PROFILE_GRANT_AUTHORITY_INSTALLED_SOURCE)
    assert not result.accepted
    assert "installed_work_artifact_binding_invalid" in result.rejection_reasons
    assert len(list(harness.manifest_directory.glob("*.json"))) == 1


def test_policy_v10_does_not_gain_non_initial_work_scope(current):
    policy = current["e0"]["policy"]
    policy["schema_version"] = policy_contract.POLICY_SCHEMA_V10
    resign_policy(current)
    with pytest.raises(ValueError, match="installed_initial_scope_invalid"):
        policy_contract.validated_signer_owner_e0_policy(policy, now_epoch=NOW)


def test_shorter_policy_expiry_is_checked_after_artifact_verification(current, monkeypatch):
    current["e0"]["policy"]["expires_at"] = NOW + 10
    resign_policy(current)
    original = prior.verifier_module._installed_source_policy
    def delay(*args):
        result = original(*args)
        monkeypatch.setattr(prior.verifier_module, "_now_epoch", lambda: NOW + 11)
        return result
    monkeypatch.setattr(prior.verifier_module, "_installed_source_policy", delay)
    with pytest.raises(ValueError, match="installed_work_time_invalid"):
        verify(current)
