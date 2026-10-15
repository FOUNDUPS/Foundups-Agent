"""Real enrollment/IO/signatures; owner, E0 lease, OS custody are synthetic."""
from contextlib import contextmanager
import json
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_grant_authority_service_manifest_verifier as subject,
    reddog_grant_authority_service_authenticated_manifest_binding as binding,
    reddog_grant_authority_service_owner_binding as owner_binding,
    reddog_signer_system_service_manifest_selection_loader as owner_loader,
    reddog_grant_authority_wsp71_permission_rehydration as permission,
    reddog_grant_authority_wsp71_permission_contract as receipt_contract,
    reddog_signer_independent_secret_grant_verification as grant_verification,
    reddog_initial_runtime_manifest_authority as approval,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_source_policy import (
    SOURCE_POLICY_SCHEMA, grant_service_git_source_policy_digest,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import canonical_json, raw_digest
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import POLICY_SCHEMA_V10
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_artifact_contract import compose_installed_grant_service_artifacts
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import REQUIRED_INSTALLED_GRANT_RUNTIME_ARTIFACTS
from modules.communication.moltbot_bridge.tests.test_reddog_initial_installed_manifest_enrollment import enrolled
from modules.communication.moltbot_bridge.tests.test_reddog_initial_runtime_manifest_authority import installed, _open, _produce


def test_legacy_missing_archive_evidence_remains_rejected(tmp_path, monkeypatch):
    from modules.communication.moltbot_bridge.tests.test_reddog_grant_authority_service_authenticated_manifest_binding import _setup, _bind

    state = _setup(tmp_path, monkeypatch)
    original = binding.verify_current_grant_service_artifacts

    def missing(**kwargs):
        value = dict(original(**kwargs))
        value.pop("service_archive_digest")
        return value

    monkeypatch.setattr(binding, "verify_current_grant_service_artifacts", missing)
    with pytest.raises((KeyError, ValueError)):
        _bind(state)


@pytest.fixture
def current(enrolled, monkeypatch):
    state = enrolled
    state.path = state.harness.runtime_root / "initial-approval.json"
    state.path.write_text(canonical_json(state.value))
    produced = _produce(state, _open(state))
    assert produced.accepted
    manifest = json.loads(state.harness.manifest_directory.joinpath(produced.manifest_id[7:] + ".json").read_text())
    config = json.loads((state.harness.runtime_root / "grant_authority_service_config.json").read_text())
    sources = {"reddog_grant_authority_service.py": "modules/communication/moltbot_bridge/src/reddog_grant_authority_service.py"}
    source_policy = dict(schema_version=SOURCE_POLICY_SCHEMA, sources=sources,
        source_policy_digest=grant_service_git_source_policy_digest(sources), repo_root_digest=state.value["repo_root_digest"])
    owner = dict(config_id=manifest["owner_config_id"], grant_authority_source_policy=source_policy)
    policy = dict(schema_version=POLICY_SCHEMA_V10, owner_config_id=owner["config_id"], policy_id=raw_digest(b"synthetic policy"),
        grant_authority_manifest_id=manifest["manifest_id"], grant_authority_artifact_generation_digest=manifest["artifact_generation_digest"],
        grant_authority_config_digest=manifest["signer_service_config_digest"],
        grant_authority_run_packet_digest=raw_digest((state.harness.runtime_root / "grant_authority_service_run_packet.json").read_bytes()),
        grant_authority_source_repo_root_digest=state.value["repo_root_digest"], grant_authority_source_commit_sha=state.value["source_commit_sha"],
        grant_authority_source_object_format="sha1", grant_authority_source_policy_digest=source_policy["source_policy_digest"],
        grant_authority_installed_runtime_descriptor_digest=manifest["grant_authority_installed_runtime_descriptor_digest"],
        generation=1, allowed_operations=["signer_socket_peer_handshake"], allowed_authority_tiers=["LOW"], consensus_required_tiers=[])
    for key in ("signer_agent_id", "signer_profile_id", "public_key", "key_fingerprint", "key_epoch",
                "signing_key_ref_hash", "audit_mac_key_ref_hash", "permission_snapshot_digest", "permission_snapshot_receipt_id"):
        policy["grant_authority_" + key] = config[key]
    monkeypatch.setattr(owner_loader, "_load_owner_config", lambda *a, **k: dict(owner))
    monkeypatch.setattr(owner_binding, "grant_authority_owner_runtime_root", lambda *a: state.harness.runtime_root)
    monkeypatch.setattr(binding, "grant_authority_owner_runtime_root", lambda *a: state.harness.runtime_root)
    monkeypatch.setattr(permission, "grant_authority_owner_runtime_root", lambda *a: state.harness.runtime_root)
    state.owner, state.policy, state.manifest = owner, policy, manifest
    state.owner_path = state.path.parent / "owner.json"
    return state


def _verify(state, **kwargs):
    return subject.verify_current_grant_service_artifacts(repo_root=state.harness.repo_root,
        grant_root=state.harness.runtime_root, policy=state.policy, owner_config_path=state.owner_path, **kwargs)


def test_production_enrollment_to_generic_consumer_is_metadata_only(current):
    calls = len(current.calls)
    result = _verify(current)
    assert result["manifest_id"] == current.manifest["manifest_id"]
    assert result["installed_runtime_descriptor_digest"] == current.policy["grant_authority_installed_runtime_descriptor_digest"]
    assert result["source_descriptor"]["source_commit_sha"] == current.policy["grant_authority_source_commit_sha"]
    assert "service_archive_digest" not in result and len(current.calls) == calls


def test_generic_consumer_requires_separately_selected_owner(current):
    with pytest.raises(ValueError, match="not_enrolled"):
        subject.verify_current_grant_service_artifacts(repo_root=current.harness.repo_root,
            grant_root=current.harness.runtime_root, policy=current.policy)


@pytest.mark.parametrize("field", ["grant_authority_manifest_id", "grant_authority_artifact_generation_digest",
    "grant_authority_config_digest", "grant_authority_run_packet_digest", "owner_config_id",
    "grant_authority_source_commit_sha", "grant_authority_source_repo_root_digest", "grant_authority_source_object_format",
    "grant_authority_source_policy_digest", "grant_authority_installed_runtime_descriptor_digest", "grant_authority_public_key",
    "grant_authority_permission_snapshot_digest", "grant_authority_signing_key_ref_hash"])
def test_e0_identity_substitutions_rejected(current, field):
    current.policy[field] = raw_digest(b"substitution")
    with pytest.raises((ValueError, FileNotFoundError)):
        _verify(current)


@pytest.mark.parametrize("mutation", ["missing", "alternate", "corrupt", "expiry", "owner", "source_policy"])
def test_protected_approval_and_owner_fail_closed(current, mutation):
    if mutation == "missing": current.path.unlink()
    elif mutation == "alternate": current.path.rename(current.path.with_name("candidate-chosen.json"))
    elif mutation == "corrupt": current.path.write_text("{}")
    elif mutation == "expiry": current.clock["wall"] += 121
    elif mutation == "owner": current.owner["config_id"] = raw_digest(b"different owner")
    else: current.owner["grant_authority_source_policy"]["source_policy_digest"] = raw_digest(b"wrong policy")
    with pytest.raises((ValueError, FileNotFoundError)):
        _verify(current)


@pytest.mark.parametrize("field,value", [("generation", True), ("generation", 2),
    ("allowed_operations", ["sign_work"]), ("allowed_authority_tiers", ["HIGH"]), ("consensus_required_tiers", ["LOW"])])
def test_initial_scope_never_becomes_work_authority(current, field, value):
    current.policy[field] = value
    with pytest.raises(ValueError): _verify(current)


def test_authenticated_binding_preserves_distinct_installed_field(current, monkeypatch):
    @contextmanager
    def synthetic_lease(**kwargs):
        yield SimpleNamespace(policy=current.policy)
    monkeypatch.setattr(binding, "lease_validated_owner_e0_current_admission", synthetic_lease)
    result = binding.bind_grant_authority_service_manifest(owner_config_path=current.owner_path,
        repo_root=current.harness.repo_root, owner_policy=current.policy).to_dict()
    assert result["installed_runtime_descriptor_digest"] == current.policy["grant_authority_installed_runtime_descriptor_digest"]
    assert result["service_archive_digest"] == result["archive_source_descriptor_digest"] == ""


def test_expiry_during_verification_rejected(current, monkeypatch):
    original = subject._read_installed_artifacts
    def slow(*args):
        result = original(*args)
        current.clock["wall"] += 121
        return result
    monkeypatch.setattr(subject, "_read_installed_artifacts", slow)
    with pytest.raises(ValueError): _verify(current)


@pytest.mark.parametrize("mutation", ["approval", "owner", "artifact"])
def test_late_protected_input_change_rejects_before_result(current, monkeypatch, mutation):
    original = subject._installed_source_policy
    def changed(*args):
        result = original(*args)
        if mutation == "approval": current.path.write_text("{}")
        elif mutation == "owner": current.owner["config_id"] = raw_digest(b"rotated owner")
        else: (current.harness.runtime_root / "grant_authority_service_config.json").write_text("{}")
        return result
    monkeypatch.setattr(subject, "_installed_source_policy", changed)
    with pytest.raises(ValueError): _verify(current)


@pytest.mark.parametrize("mutation", ["uncovered", "wrong_entrypoint"])
def test_rehashed_owner_source_policy_cannot_substitute_installed_sources(current, mutation):
    source = current.owner["grant_authority_source_policy"]
    if mutation == "uncovered": source["sources"]["other.py"] = "modules/other.py"
    else: source["sources"]["reddog_grant_authority_service.py"] = "modules/communication/moltbot_bridge/src/reddog_grant_authority_runtime_dependencies.py"
    source["source_policy_digest"] = grant_service_git_source_policy_digest(source["sources"])
    current.policy["grant_authority_source_policy_digest"] = source["source_policy_digest"]
    with pytest.raises(ValueError, match="source_policy_mismatch"): _verify(current)


def _permission_enrollment(state):
    policy = state.policy
    policy.update(manifest_id=raw_digest(b"synthetic target manifest"),
        artifact_generation_digest=raw_digest(b"synthetic target artifacts"), generation_revision="target-revision",
        grant_authority_principal_id="local:grant-owner", grant_authority_principal_provider="local",
        issued_at=int(state.clock["wall"]), expires_at=int(state.clock["wall"])+120)
    config = json.loads((state.harness.runtime_root / "grant_authority_service_config.json").read_text())
    receipt = receipt_contract.expected_permission_bindings(policy, {}, config)
    receipt.update(schema_version=receipt_contract.SCHEMA_VERSION, permission="SECRETS_READ",
        allowed_operations=["get_secret"], issued_at=policy["issued_at"], expires_at=policy["expires_at"], revoked=False)
    receipt["receipt_id"] = receipt_contract.permission_receipt_id(receipt)
    raw = canonical_json(receipt).encode()
    (state.harness.runtime_root / receipt_contract.PERMISSION_FILENAME).write_bytes(raw)
    config.update(permission_snapshot_digest=raw_digest(raw), permission_snapshot_receipt_id=receipt["receipt_id"])
    descriptor = json.loads((state.harness.runtime_root / "grant_authority_installed_source.json").read_text())
    names = ("signer_agent_id", "signer_profile_id", "public_key", "key_fingerprint", "key_epoch",
        "signing_key_ref_hash", "audit_mac_key_ref_hash", "permission_snapshot_digest", "permission_snapshot_receipt_id")
    bundle = compose_installed_grant_service_artifacts(profile={k:config[k] for k in names},
        owner_config_id=policy["owner_config_id"], repo_root_digest=state.value["repo_root_digest"], source_descriptor=descriptor)
    for name, body in bundle.items(): (state.harness.runtime_root / name).write_bytes(body)
    spec=state.value["manifest_spec"]
    spec["signer_service_config_digest"] = raw_digest(bundle["grant_authority_service_config.json"])
    spec["artifacts"]=[dict(filename=name, byte_count=len(bundle[name]), content_digest=raw_digest(bundle[name]))
        for name in REQUIRED_INSTALLED_GRANT_RUNTIME_ARTIFACTS]
    state.path.write_text(canonical_json(state.value))
    produced = _produce(state, _open(state))
    assert produced.accepted
    state.manifest=json.loads(state.harness.manifest_directory.joinpath(produced.manifest_id[7:]+".json").read_text())
    policy.update(grant_authority_manifest_id=state.manifest["manifest_id"],
        grant_authority_artifact_generation_digest=state.manifest["artifact_generation_digest"],
        grant_authority_config_digest=spec["signer_service_config_digest"],
        grant_authority_run_packet_digest=raw_digest(bundle["grant_authority_service_run_packet.json"]),
        grant_authority_permission_snapshot_digest=config["permission_snapshot_digest"],
        grant_authority_permission_snapshot_receipt_id=receipt["receipt_id"])


@pytest.mark.parametrize("mutation", [None, "expiry", "permission", "policy"])
def test_permission_consumption_rechecks_real_enrollment_around_synthetic_root_rpc(current, monkeypatch, mutation):
    _permission_enrollment(current)
    lease_depth = [0]
    @contextmanager
    def synthetic_lease(**kwargs):
        lease_depth[0] += 1
        try: yield SimpleNamespace(policy=current.policy, revocation_binding="synthetic-binding")
        finally: lease_depth[0] -= 1
    class SyntheticOracle:
        binding = "synthetic-binding"
        def authorize_current_key_epoch_use(self, *, action, **kwargs):
            assert lease_depth[0] == 0
            if mutation == "expiry": current.clock["wall"] += 121
            elif mutation == "permission":
                (current.harness.runtime_root / receipt_contract.PERMISSION_FILENAME).write_text("{}")
            elif mutation == "policy": current.policy["grant_authority_public_key"] = "changed"
            return action()
    monkeypatch.setattr(permission, "lease_validated_owner_e0_current_admission", synthetic_lease)
    monkeypatch.setattr(permission, "RootAuthorizedSignerGrantRevocationOracle", SyntheticOracle)
    monkeypatch.setattr(grant_verification, "_owner_authority_snapshot", lambda selected: "synthetic-owner-snapshot")
    calls=[]
    def action():
        assert lease_depth[0] == 1
        calls.append("effect")
        return "accepted"
    def run():
        return permission.authorize_current_grant_authority_wsp71_use(owner_config_path=current.owner_path,
            repo_root=current.harness.repo_root, owner_policy=current.policy, now_epoch=int(current.clock["wall"]),
            revocation_oracle=SyntheticOracle(), action=action)
    if mutation is None:
        assert run() == "accepted" and calls == ["effect"]
    else:
        with pytest.raises(ValueError): run()
        assert calls == []
