"""Startup v7 schema inheritance; explicit inert OS/service boundary seams."""

import importlib
import time
import pytest

from modules.communication.moltbot_bridge.tests import test_reddog_effect_consent_owner_versions as legacy
from modules.communication.moltbot_bridge.tests.reddog_effect_consent_test_support import ROOT, canonical, digest
from modules.communication.moltbot_bridge.tests.reddog_reviewer_composition_test_support import assert_closed, setup as reviewer_setup


def startup_owner_fixture(monkeypatch, tmp_path, base_fixture=legacy.owner_fixture):
    """Real schema validators; root byte provenance and keys are synthetic."""
    from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import _descriptor
    from modules.communication.moltbot_bridge.tests.test_reddog_signer_owner_controlled_e0_admission import _keypair
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import descriptor_id_for
    loader, repo, path, owner, raw = base_fixture(monkeypatch, tmp_path)
    now = int(time.time())
    descriptor, _, _ = _descriptor(tmp_path / "descriptor", descriptor_overrides={"issued_at": now - 1, "expires_at": now + 120})
    _, control_public = _keypair()
    descriptor.update(schema_version="foundup_verified_outcome_root_authority.v2",
        root_control_authentication={"purpose": "protected-use-acquire-finish.v1", "public_key": control_public, "key_epoch": "control-1"})
    descriptor["descriptor_id"] = descriptor_id_for(descriptor)
    owner["verified_outcome_authority"]["descriptor"] = descriptor
    binding = dict(credential_directory="/run/credentials/reddog-signer.service", expected_uid=1201,
        expected_gid=1201, expected_requester="signer:test", issued_at=now - 1, expires_at=now + 60,
        credential_ids=["control", "integrity", "work"], max_secret_bytes=65536)
    permissions = {}
    for purpose, reference, public, epoch in (
        ("revocation-anchor-load.v1", "work", descriptor["signer_public_key"], descriptor["signer_key_epoch"]),
        ("protected-use-acquire-finish.v1", "control", control_public, "control-1"),
    ):
        permissions[purpose] = dict(operation="SECRETS_READ", reference="systemd-creds://" + reference,
            requester_id="signer:test", purpose=purpose, public_key=public, key_epoch=epoch,
            issued_at=now - 1, expires_at=now + 30)
    owner.update(schema_version=loader.SCHEMA_VERSION_V7, startup_custody=dict(
        policy_path=str(path.parent / "e0-policy.json"), credential_binding=binding,
        root_request_permissions=permissions, proposal_replay_store=None,
        replay_store=dict(high_water_root=str(tmp_path / "grant-high"),
            high_water_path=str(tmp_path / "grant-high" / "high.sqlite3"), replay_store_binding_digest="sha256:" + "e" * 64),
        replay_integrity_permission=dict(operation="SECRETS_READ", reference="systemd-creds://integrity",
            requester_id="signer:test", purpose="signer-grant-replay-integrity.v1", encoding="utf8",
            issued_at=now - 1, expires_at=now + 30)))
    owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
    raw[0] = canonical(owner).encode("ascii")
    return loader, repo, path, owner, raw


@pytest.mark.parametrize("case", ["valid", "valid_proposal", "duplicate", "missing", "extra", "digest", "policy_path", "policy_nested",
    "credential_ids", "credential_uid", "credential_requester", "permission_operation", "permission_reference",
    "permission_identity", "permission_expiry", "permission_time_type", "integrity_encoding", "integrity_purpose",
    "replay_path", "replay_nested", "replay_digest", "proposal_extra", "proposal_nested", "outcome", "grant", "source_policy", "reviewer", "consent"])
def test_startup_custody_v7_exact_shape_and_inherited_validators(monkeypatch, tmp_path, case):
    loader, repo, path, owner, raw = startup_owner_fixture(monkeypatch, tmp_path)
    assert loader._load_owner_config(path, repo=repo) == owner
    assert loader.V7_FIELDS == loader.V6_FIELDS | {"startup_custody"}
    custody = owner["startup_custody"]
    permission = custody["root_request_permissions"]["revocation-anchor-load.v1"]
    if case == "valid_proposal": custody["proposal_replay_store"] = dict(
        high_water_root=str(tmp_path / "proposal-high"), high_water_path=str(tmp_path / "proposal-high" / "high.sqlite3"))
    elif case == "missing": custody.pop("proposal_replay_store")
    elif case == "extra": custody["authority"] = True
    elif case == "policy_path": custody["policy_path"] = str(repo / "policy.json")
    elif case == "policy_nested": custody["policy_path"] = str(path.parent / "nested" / "policy.json")
    elif case == "credential_ids": custody["credential_binding"]["credential_ids"] = ["work", "control", "integrity"]
    elif case == "credential_uid": custody["credential_binding"]["expected_uid"] = 0
    elif case == "credential_requester": custody["credential_binding"]["expected_requester"] = "other"
    elif case == "permission_operation": permission["operation"] = "read"
    elif case == "permission_reference": permission["reference"] = "systemd-creds://unknown"
    elif case == "permission_identity": permission["public_key"] = custody["root_request_permissions"]["protected-use-acquire-finish.v1"]["public_key"]
    elif case == "permission_expiry": permission["expires_at"] += 100
    elif case == "permission_time_type": permission["issued_at"] = True
    elif case == "integrity_encoding": custody["replay_integrity_permission"]["encoding"] = "base64"
    elif case == "integrity_purpose": custody["replay_integrity_permission"]["purpose"] = "sign"
    elif case == "replay_path": custody["replay_store"]["high_water_path"] = str(repo / "bad.sqlite3")
    elif case == "replay_nested": custody["replay_store"]["high_water_path"] = str(tmp_path / "grant-high" / "nested" / "high.sqlite3")
    elif case == "replay_digest": custody["replay_store"]["replay_store_binding_digest"] = "fake"
    elif case == "proposal_extra": custody["proposal_replay_store"] = {"authority": True}
    elif case == "proposal_nested": custody["proposal_replay_store"] = dict(
        high_water_root=str(tmp_path / "proposal-high"), high_water_path=str(tmp_path / "proposal-high" / "nested" / "high.sqlite3"))
    elif case == "outcome": owner["verified_outcome_authority"]["authority_service_uid"] = 1
    elif case == "grant": owner["independent_grant_authority"]["authority_service_uid"] = 0
    elif case == "source_policy": owner["grant_authority_source_policy"]["source_policy_digest"] = "sha256:" + "0" * 64
    elif case == "reviewer": owner["reviewer_designation_authority"]["privilege"] = "authorize_exact_high_worktree_effect"
    elif case == "consent": owner["effect_consent_authority"]["privilege"] = "designate_effect_reviewers"
    owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
    if case == "digest": owner["config_id"] = "sha256:" + "0" * 64
    text = canonical(owner)
    if case == "duplicate": text = text.replace('"startup_custody":{', '"startup_custody":{"policy_path":"duplicate",', 1)
    raw[0] = text.encode("ascii")
    if case in {"valid", "valid_proposal"}: assert loader._load_owner_config(path, repo=repo) == owner
    else:
        with pytest.raises(loader.RuntimeArtifactManifestError): loader._load_owner_config(path, repo=repo)


def test_startup_custody_v7_keeps_existing_policy_and_grant_edges(monkeypatch, tmp_path):
    module = legacy
    monkeypatch.setattr(module, "owner_fixture", startup_owner_fixture)
    legacy.test_effect_consent_v6_startup_policy_and_grant_owner_edges(monkeypatch, tmp_path)


def test_startup_custody_v7_grant_supply_edge(monkeypatch, tmp_path):
    module = legacy
    monkeypatch.setattr(module, "owner_fixture", startup_owner_fixture)
    legacy.test_effect_consent_v6_grant_supply_schema_edge_only(monkeypatch, tmp_path)


def test_startup_custody_v7_defers_runtime_materialization(monkeypatch, tmp_path):
    loader, repo, path, owner, _ = startup_owner_fixture(monkeypatch, tmp_path)
    module = importlib.import_module(ROOT + "foundup_verified_outcome_root_runtime_materializer")
    calls, sentinel = [], object()
    def materialize(**kwargs):
        calls.append(kwargs)
        return sentinel
    monkeypatch.setattr(module, "materialize_system_service_runtime_dependencies", materialize, raising=False)
    monkeypatch.setattr(loader, "_manifest_selection_from_owner", lambda *a, **k: (object(), object()))
    result = loader.load_system_service_startup_selection(owner_config_path=path, repo_root=repo)
    assert calls == []
    assert callable(result.runtime_dependencies_supplier)
    assert result.runtime_dependencies_supplier() is sentinel
    assert calls == [dict(owner_config_path=path, repo=repo, expected_owner_config_id=owner["config_id"])]


def test_startup_custody_v7_retains_current_consent_verification(monkeypatch, tmp_path):
    from modules.communication.moltbot_bridge.tests.reddog_effect_consent_test_support import setup, positive
    resolve, state = setup(monkeypatch, tmp_path)
    state.owner["schema_version"] = "reddog_signer_system_service_owner_config.v7"
    positive(resolve, state)


def test_startup_custody_v7_retains_current_reviewer_verification(monkeypatch, tmp_path):
    verify, state = reviewer_setup(monkeypatch, tmp_path)
    state.owner["schema_version"] = "reddog_signer_system_service_owner_config.v7"
    assert verify(**state.call) is True
    assert len(state.crypto) == 2 and state.reads == 2
    assert_closed(state)
