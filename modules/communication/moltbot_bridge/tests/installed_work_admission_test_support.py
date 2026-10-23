"""Real signed work manifests/E0; owner storage, selection and OS provenance synthetic."""
import time
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import encode_ed25519_signature

from modules.communication.moltbot_bridge.src import (
    reddog_runtime_artifact_manifest_contract as contract,
    reddog_grant_authority_service_manifest_verifier as verifier,
    reddog_signer_owner_e0_policy_contract as policy_contract,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_artifact_contract import compose_installed_grant_service_artifacts
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_source_policy import (
    SOURCE_POLICY_SCHEMA, grant_service_git_source_policy_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import produce_signed_runtime_artifact_manifest
from modules.communication.moltbot_bridge.tests import test_reddog_grant_authority_service_authenticated_manifest_binding as prior
from modules.communication.moltbot_bridge.tests.test_reddog_grant_installed_source_contract import _descriptor
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import NOW, _build_harness


def setup_installed_work(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "time", lambda: NOW)
    e0 = prior._fixture_at(tmp_path / "e0")
    grant = tmp_path / "grant"
    grant.mkdir()
    harness = _build_harness(grant, repo_root=e0["boundary"]._repo_root)
    source = source_policy(harness.repo_root)
    policy = e0["policy"]
    policy.update(schema_version=policy_contract.POLICY_SCHEMA_V11,
        allowed_operations=["worktree_create"], allowed_authority_tiers=["HIGH"],
        consensus_required_tiers=["HIGH"],
        grant_authority_source_repo_root_digest=source["repo_root_digest"],
        grant_authority_source_commit_sha=_descriptor()["source_commit_sha"],
        grant_authority_source_object_format="sha1",
        grant_authority_source_policy_digest=source["source_policy_digest"])
    bundle = installed_bundle(e0, harness.repo_root)
    policy["grant_authority_installed_runtime_descriptor_digest"] = contract.raw_digest(
        bundle[contract.GRANT_AUTHORITY_INSTALLED_SOURCE])
    for name, body in bundle.items():
        (harness.runtime_root / name).write_bytes(body)
    produced = produce_signed_runtime_artifact_manifest(manifest_directory=harness.manifest_directory,
        nonce="non-initial-installed-work", issued_at=NOW, expires_at=NOW + 120,
        context=harness.context, runtime_profile=contract.RUNTIME_PROFILE_GRANT_AUTHORITY_INSTALLED_SOURCE)
    assert produced.accepted, produced.rejection_reasons
    manifest = harness.read_manifest()
    prior._bind_target_signer(e0, manifest)
    prior._rebind_config_and_sign(e0, e0["grant_private"])
    prior._align_manifest_authority(e0, harness, manifest)
    prior._bind_policy(e0, manifest)
    prior._install_e0_selection(monkeypatch)
    monkeypatch.setattr(verifier, "_now_epoch", lambda: NOW)
    owner_root = tmp_path / "owner"
    owner_root.mkdir()
    owner = prior._owner(owner_root, config_id=policy["owner_config_id"])
    owner["independent_grant_authority"].update(authority_root=str(harness.runtime_root.resolve()),
        authority_socket_path=str((harness.runtime_root / "grant-authority.sock").resolve()))
    owner["grant_authority_source_policy"] = source
    prior._install_owner_config(monkeypatch, owner)
    return dict(e0=e0, harness=harness, manifest=manifest, owner=owner, produced=produced)


def source_policy(repo):
    sources = {"reddog_grant_authority_service.py":
        "modules/communication/moltbot_bridge/src/reddog_grant_authority_service.py"}
    return dict(schema_version=SOURCE_POLICY_SCHEMA, sources=sources,
        source_policy_digest=grant_service_git_source_policy_digest(sources),
        repo_root_digest=contract.raw_digest(str(repo.resolve()).encode()))


def installed_bundle(e0, repo):
    fields = ("signer_agent_id", "signer_profile_id", "public_key", "key_fingerprint", "key_epoch",
        "signing_key_ref_hash", "audit_mac_key_ref_hash", "permission_snapshot_digest", "permission_snapshot_receipt_id")
    profile = {key: e0["policy"]["grant_authority_" + key] for key in fields}
    return compose_installed_grant_service_artifacts(profile=profile,
        owner_config_id=e0["policy"]["owner_config_id"],
        repo_root_digest=contract.raw_digest(str(repo.resolve()).encode()), source_descriptor=_descriptor())


def verify(state):
    return prior._bind(state)


def write_manifest(state):
    manifest = state["manifest"]
    path = state["harness"].manifest_directory / (manifest["manifest_id"][7:] + ".json")
    path.write_text(contract.canonical_json(manifest), encoding="ascii")


def resign_policy(state):
    policy = state["e0"]["policy"]
    policy["policy_id"] = policy_contract.signer_owner_e0_policy_id(policy)
    policy["signature"] = encode_ed25519_signature(
        state["e0"]["grant_private"].sign(policy_contract.canonical_signer_owner_e0_policy_input(policy).encode()))
