"""Real v6 validation and explicit inert seams at OS/service boundaries."""

from contextlib import contextmanager
from copy import deepcopy
import importlib
import time
from types import SimpleNamespace
import pytest

from modules.communication.moltbot_bridge.tests.reddog_effect_consent_test_support import (
    ROOT, api, canonical, digest, materials,
)
from modules.communication.moltbot_bridge.tests.test_reddog_reviewer_owner_versions import owner_data
from modules.communication.moltbot_bridge.tests.reddog_reviewer_composition_test_support import (
    assert_closed, setup as reviewer_setup,
)


def owner_fixture(monkeypatch, tmp_path):
    api()
    loader = importlib.import_module(ROOT + "reddog_signer_system_service_manifest_selection_loader")
    assert getattr(loader, "SCHEMA_VERSION_V6", None) == "reddog_signer_system_service_owner_config.v6", "effect_owner_v6_api_missing"
    repo, root, owner, additions, _ = owner_data(tmp_path)
    keys = ("verified_outcome_authority", "independent_grant_authority", "grant_authority_source_policy", "reviewer_designation_authority")
    owner.update(dict(zip(keys, additions)))
    owner.update(schema_version=loader.SCHEMA_VERSION_V6, effect_consent_authority=materials(monkeypatch).authority)
    owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
    raw = [canonical(owner).encode("ascii")]
    monkeypatch.setattr(loader, "_read_root_owned_bytes", lambda *args: raw[0])
    return loader, repo, root / "owner.json", owner, raw


OWNER_CASES = ["valid", "missing", "extra", "duplicate", "config_digest", "outcome", "grant", "source_policy", "reviewer", "consent"]


@pytest.mark.parametrize("case", OWNER_CASES)
def test_effect_consent_owner_v6_inherits_every_validator(monkeypatch, tmp_path, case):
    loader, repo, path, owner, raw = owner_fixture(monkeypatch, tmp_path)
    assert loader._load_owner_config(path, repo=repo) == owner
    assert loader.V6_FIELDS == loader.V5_FIELDS | {"effect_consent_authority"}
    if case == "missing":
        owner.pop("effect_consent_authority")
    elif case == "extra":
        owner["effect_granted"] = True
    elif case == "outcome":
        owner["verified_outcome_authority"]["authority_service_uid"] = 1
    elif case == "grant":
        owner["independent_grant_authority"]["authority_service_uid"] = 0
    elif case == "source_policy":
        owner["grant_authority_source_policy"]["source_policy_digest"] = "sha256:" + "0" * 64
    elif case == "reviewer":
        owner["reviewer_designation_authority"]["privilege"] = "authorize_exact_high_worktree_effect"
    elif case == "consent":
        owner["effect_consent_authority"]["privilege"] = "designate_effect_reviewers"
    owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
    if case == "config_digest":
        owner["config_id"] = "sha256:" + "0" * 64
    text = canonical(owner)
    if case == "duplicate":
        text = text[:-1] + ',"config_id":' + canonical(owner["config_id"]) + '}'
    raw[0] = text.encode("ascii")
    if case == "valid":
        assert loader._load_owner_config(path, repo=repo) == owner
    else:
        with pytest.raises(loader.RuntimeArtifactManifestError):
            loader._load_owner_config(path, repo=repo)


def test_effect_consent_v6_startup_policy_and_grant_owner_edges(monkeypatch, tmp_path):
    loader, repo, path, owner, raw = owner_fixture(monkeypatch, tmp_path)
    selected, boundary = object(), object()
    monkeypatch.setattr(loader, "_manifest_selection_from_owner", lambda *args, **kwargs: (selected, boundary))
    def forbidden(*args, **kwargs):
        raise AssertionError("startup selection must not resolve signing authority")
    monkeypatch.setattr(loader, "_verified_outcome_authority_from_owner", forbidden)
    result = loader.load_system_service_startup_selection(owner_config_path=path, repo_root=repo)
    assert result.owner_config_id == owner["config_id"] and result.manifest_selection is selected
    assert result.manifest_selection_boundary is boundary
    binding = importlib.import_module(ROOT + "reddog_grant_authority_service_owner_binding")
    policy_api = importlib.import_module(ROOT + "reddog_grant_authority_source_policy_authority")
    assert binding.grant_authority_owner_runtime_root(path, repo, owner["config_id"]) == (tmp_path / "grant").resolve()
    token, current = policy_api.load_grant_authority_source_policy_authority(owner_config_path=path, repo_root=repo)
    assert current.revalidate(token)["owner_config_id"] == owner["config_id"]
    with pytest.raises(loader.RuntimeArtifactManifestError):
        binding.grant_authority_owner_runtime_root(path, repo, "sha256:" + "0" * 64)
    owner["anchor_id"] = "changed"
    owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
    raw[0] = canonical(owner).encode("ascii")
    with pytest.raises(loader.RuntimeArtifactManifestError):
        current.revalidate(token)


def test_effect_consent_v6_grant_supply_schema_edge_only(monkeypatch, tmp_path):
    _, repo, path, owner, _ = owner_fixture(monkeypatch, tmp_path)
    supply = importlib.import_module(ROOT + "reddog_signer_independent_grant_authority_client_supply")
    calls, sentinel = [], object()
    policy = {"owner_config_id": owner["config_id"]}
    @contextmanager
    def admission(**kwargs):
        calls.append("enter")
        try:
            yield SimpleNamespace(policy=policy)
        finally:
            calls.append("exit")
    def build(**kwargs):
        assert kwargs["owner"] == owner and kwargs["policy"] is policy
        assert owner["schema_version"] in kwargs["required_schemas"]
        assert {"reddog_signer_system_service_owner_config.v3", "reddog_signer_system_service_owner_config.v4",
                "reddog_signer_system_service_owner_config.v5"}.issubset(kwargs["required_schemas"])
        calls.append("build")
        return sentinel
    monkeypatch.setattr(supply, "lease_validated_owner_e0_current_admission", admission)
    monkeypatch.setattr(supply, "_build_authenticated_supply", build)
    assert supply.load_system_service_independent_grant_authority_client(
        owner_config_path=path, repo_root=repo, owner_policy=policy) is sentinel
    assert calls == ["enter", "build", "exit"]


def test_effect_consent_v6_retains_reviewer_verification(monkeypatch, tmp_path):
    api()
    verify, state = reviewer_setup(monkeypatch, tmp_path)
    assert verify(**state.call) is True
    assert_closed(state)
    state.reads = 0
    state.crypto.clear()
    state.lease.selected = state.lease.entered = state.lease.exited = 0
    state.owner["schema_version"] = "reddog_signer_system_service_owner_config.v6"
    state.owner["effect_consent_authority"] = materials(monkeypatch).authority
    assert verify(**state.call) is True
    assert len(state.crypto) == 2 and all(c[3] is True for c in state.crypto)
    assert state.reads == 2
    assert_closed(state)


def test_effect_consent_windows_does_not_bypass_linux_owner_guard(monkeypatch, tmp_path):
    api()
    loader = importlib.import_module(ROOT + "reddog_signer_system_service_manifest_selection_loader")
    monkeypatch.setattr(loader.sys, "platform", "win32")
    with pytest.raises(loader.RuntimeArtifactManifestError, match="signer_owner_linux_service_required"):
        loader._read_root_owned_bytes(tmp_path / "not-created.json", tmp_path)


def startup_owner_fixture(monkeypatch, tmp_path, base_fixture=owner_fixture):
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
    module = importlib.import_module(__name__)
    monkeypatch.setattr(module, "owner_fixture", startup_owner_fixture)
    test_effect_consent_v6_startup_policy_and_grant_owner_edges(monkeypatch, tmp_path)


def test_startup_custody_v7_grant_supply_edge(monkeypatch, tmp_path):
    module = importlib.import_module(__name__)
    monkeypatch.setattr(module, "owner_fixture", startup_owner_fixture)
    test_effect_consent_v6_grant_supply_schema_edge_only(monkeypatch, tmp_path)


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
