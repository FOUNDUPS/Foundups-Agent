"""Installed issuer policy bindings; disposable data is never runtime authority."""
import pytest

from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_policy_contract as pc
from modules.communication.moltbot_bridge.tests.test_reddog_signer_owner_e0_static_contract import (
    _v9_signed_fixture,
)


SCHEMA = "reddog-signer-owner-e0-policy.v10"
INSTALLED = "grant_authority_installed_runtime_descriptor_digest"
ARCHIVE = "grant_authority_archive_source_descriptor_digest"


def _installed():
    value = _v9_signed_fixture()
    value["schema_version"] = SCHEMA
    value[INSTALLED] = value.pop(ARCHIVE)
    # Signature is deliberately not reissued: this is shape/hash validation only.
    value["policy_id"] = pc.signer_owner_e0_policy_id(value)
    return value


def test_installed_policy_shape_requires_its_distinct_descriptor():
    value = _installed()
    assert pc.validated_signer_owner_e0_policy(value, now_epoch=1100) == value
    assert pc.POLICY_SCHEMA == pc.POLICY_SCHEMA_V6
    for changed in (dict(value, **{ARCHIVE: value[INSTALLED]}),
                    {k: v for k, v in value.items() if k != INSTALLED}):
        with pytest.raises(ValueError, match="malformed"):
            pc.validated_signer_owner_e0_policy(changed, now_epoch=1100)


@pytest.mark.parametrize("bad", [None, True, 7, "", "sha256:bad", "sha256:" + "G" * 64])
def test_installed_descriptor_digest_is_strict(bad):
    value = dict(_installed(), **{INSTALLED: bad})
    value["policy_id"] = pc.signer_owner_e0_policy_id(value)
    with pytest.raises(ValueError):
        pc.validated_signer_owner_e0_policy(value, now_epoch=1100)


@pytest.mark.parametrize("field", [INSTALLED, "grant_authority_source_commit_sha",
    "grant_authority_source_repo_root_digest", "grant_authority_source_policy_digest",
    "grant_authority_signing_key_ref_hash", "grant_authority_public_key"])
def test_installed_code_and_identity_remain_in_stable_binding(field):
    value = _installed()
    changed = dict(value, **{field: value[field] + "-changed"})
    assert pc.signer_owner_e0_authority_binding_digest(changed) != pc.signer_owner_e0_authority_binding_digest(value)


@pytest.mark.parametrize("field", ["target_signer_generation_id",
    "grant_authority_manifest_id", "grant_authority_artifact_generation_digest",
    "grant_authority_config_digest", "grant_authority_run_packet_digest",
    "grant_authority_permission_snapshot_digest", "grant_authority_permission_snapshot_receipt_id"])
def test_future_artifacts_are_acyclic_but_still_in_final_policy(field):
    value = _installed()
    changed = dict(value, **{field: "sha256:" + "e" * 64})
    assert pc.signer_owner_e0_authority_binding_digest(changed) == pc.signer_owner_e0_authority_binding_digest(value)
    assert pc.signer_owner_e0_policy_id(changed) != value["policy_id"]
    assert pc.canonical_signer_owner_e0_policy_input(changed) != pc.canonical_signer_owner_e0_policy_input(value)
    changed.pop(field)
    with pytest.raises(ValueError, match="malformed"):
        pc.validated_signer_owner_e0_policy(changed, now_epoch=1100)


@pytest.mark.parametrize("change", [
    {"generation": 2}, {"allowed_operations": ["sign_work_order"]},
    {"allowed_authority_tiers": ["HIGH"]}, {"consensus_required_tiers": ["LOW"]},
    {"grant_authority_source_object_format": "unknown"},
    {"grant_authority_source_commit_sha": "a" * 39},
])
def test_installed_initial_policy_cannot_expand_scope(change):
    value = dict(_installed(), **change)
    value["policy_id"] = pc.signer_owner_e0_policy_id(value)
    with pytest.raises(ValueError):
        pc.validated_signer_owner_e0_policy(value, now_epoch=1100)


def test_installed_policy_does_not_downgrade_into_archive_schema():
    value = _installed()
    for schema in (pc.POLICY_SCHEMA_V7, pc.POLICY_SCHEMA_V8, pc.POLICY_SCHEMA_V9):
        with pytest.raises(ValueError, match="malformed"):
            pc.validated_signer_owner_e0_policy(dict(value, schema_version=schema), now_epoch=1100)
    for schema in (None, True, [], "reddog-signer-owner-e0-policy.v11"):
        with pytest.raises(ValueError):
            pc.canonical_signer_owner_e0_policy_input(dict(value, schema_version=schema))


def test_new_policy_signature_domain_does_not_reuse_v9_signature():
    from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import Ed25519SignatureVerifier
    old = _v9_signed_fixture()
    new = _installed()
    verifier = Ed25519SignatureVerifier()
    assert verifier.verify(old["grant_authority_public_key"], pc.canonical_signer_owner_e0_policy_input(old), old["signature"])
    assert not verifier.verify(new["grant_authority_public_key"], pc.canonical_signer_owner_e0_policy_input(new), old["signature"])


def test_sha256_source_object_identity_is_supported():
    value = dict(_installed(), grant_authority_source_object_format="sha256",
                 grant_authority_source_commit_sha="a" * 64)
    value["policy_id"] = pc.signer_owner_e0_policy_id(value)
    assert pc.validated_signer_owner_e0_policy(value, now_epoch=1100) == value


def test_shape_support_cannot_enter_legacy_runtime_or_credential_path(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from modules.communication.moltbot_bridge.src import (
        reddog_grant_authority_service_manifest_verifier as manifest,
        reddog_grant_authority_wsp71_permission_rehydration as permission,
    )
    def forbidden(*args, **kwargs):
        pytest.fail("unadmitted installed profile reached runtime I/O")
    monkeypatch.setattr(manifest, "reddog_runtime_artifact_generation_lock", forbidden)
    monkeypatch.setattr(permission, "grant_authority_owner_runtime_root", forbidden)
    policy = _installed()
    with pytest.raises(ValueError, match="grant_installed_profile_not_enrolled"):
        manifest.verify_current_grant_service_artifacts(repo_root=tmp_path,
            grant_root=tmp_path, policy=policy)
    with pytest.raises(ValueError, match="grant_permission_e0_schema_invalid"):
        permission._permission_state(SimpleNamespace(policy=policy), tmp_path,
            tmp_path / "owner.json", None, 1100)
