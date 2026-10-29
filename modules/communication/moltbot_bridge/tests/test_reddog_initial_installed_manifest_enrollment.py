"""Initial installed enrollment with real signatures/IO; OS custody is synthetic."""
from dataclasses import replace
from pathlib import Path
import json

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_initial_runtime_manifest_authority as authority,
    reddog_current_generation_manifest_launch_selection as selection,
    reddog_signer_runtime_atomic_provisioning as provision,
    reddog_runtime_artifact_manifest_contract as contract,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_artifact_contract import (
    compose_installed_grant_service_artifacts,
)
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    produce_signed_runtime_artifact_manifest, verify_signed_runtime_artifact_manifest,
    _signing_request, validate_runtime_artifact_manifest_signing_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning_contract import (
    create_signer_runtime_atomic_provisioning_context,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    signer_runtime_generation_binding_from_manifest,
)
from modules.communication.moltbot_bridge.tests.test_reddog_initial_runtime_manifest_authority import (
    installed, _open, _produce,
)
from modules.communication.moltbot_bridge.tests.test_reddog_grant_installed_source_contract import _descriptor, _profile
from modules.communication.moltbot_bridge.tests.test_reddog_current_generation_manifest_launch_selection import (
    OWNER_CONFIG_ID, _owner_authority,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import NOW


@pytest.fixture
def enrolled(installed, monkeypatch):
    descriptor = _descriptor()
    bundle = compose_installed_grant_service_artifacts(profile=_profile(), owner_config_id=OWNER_CONFIG_ID,
        repo_root_digest=installed.value["repo_root_digest"], source_descriptor=descriptor)
    for name, body in bundle.items():
        (installed.harness.runtime_root / name).write_bytes(body)
    spec = installed.value["manifest_spec"]
    spec.update(runtime_profile=contract.RUNTIME_PROFILE_GRANT_AUTHORITY_INSTALLED_SOURCE,
        owner_config_id=OWNER_CONFIG_ID,
        grant_authority_installed_runtime_descriptor_digest=contract.raw_digest(bundle[contract.GRANT_AUTHORITY_INSTALLED_SOURCE]),
        signer_service_config_digest=contract.raw_digest(bundle[contract.GRANT_AUTHORITY_SERVICE_CONFIG]),
        artifacts=[dict(filename=name, byte_count=len(bundle[name]), content_digest=contract.raw_digest(bundle[name]))
                   for name in contract.REQUIRED_INSTALLED_GRANT_RUNTIME_ARTIFACTS])
    installed.value.update(schema_version=authority.SCHEMA_VERSION_V2,
        source_commit_sha=descriptor["source_commit_sha"], source_files=descriptor["source_files"])
    installed.path.write_text(contract.canonical_json(installed.value), encoding="ascii")
    monkeypatch.setattr(selection, "_now_epoch", lambda: int(installed.clock["wall"]))
    monkeypatch.setattr(provision, "_trusted_now", lambda: int(installed.clock["wall"]))
    return installed


def _reader(state):
    from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water import (
        AtomicSignerRuntimeGenerationHighWaterReader,
    )
    from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_reader import (
        DurableSignerRuntimeGenerationReader, create_signer_runtime_generation_high_water_reader_authority,
        create_signer_runtime_generation_reader_authority,
    )
    anchor, repo = state.anchor, state.harness.repo_root
    high, signer = anchor._high_water_store, anchor._signer
    high_reader = AtomicSignerRuntimeGenerationHighWaterReader(high._store.path,
        allowed_root=high.rollback_domain_root, repo_root=repo, store_id=high.store_id,
        durability_receipt_id=high.durability_receipt_id, verifier_authority=signer.verifier_authority,
        verifier_authority_boundary=signer.verifier_boundary, generation_witness_reader=high._witness.reader(),
        generation_witness_binding=high._witness_binding)
    high_cap, high_boundary = create_signer_runtime_generation_high_water_reader_authority(high_reader)
    reader = DurableSignerRuntimeGenerationReader(anchor.path, allowed_root=anchor.authority_root,
        repo_root=repo, anchor_id=anchor.load().anchor_id, verifier_authority=signer.verifier_authority,
        verifier_authority_boundary=signer.verifier_boundary, high_water_authority=high_cap,
        high_water_authority_boundary=high_boundary)
    cap, boundary = create_signer_runtime_generation_reader_authority(reader)
    owner, owner_boundary = _owner_authority(state.harness, reader.load())
    return selection.create_current_generation_manifest_launch_selection_boundary(owner_authority=owner,
        owner_authority_boundary=owner_boundary, generation_reader_authority=cap,
        generation_reader_authority_boundary=boundary)


def _activate(state):
    context = _open(state)
    produced = _produce(state, context)
    assert produced.accepted, produced
    atomic = create_signer_runtime_atomic_provisioning_context(manifest_signing=context,
        generation_anchor=state.anchor)
    result = provision.provision_signer_runtime_generation(nonce=state.value["manifest_spec"]["nonce"],
        ttl_seconds=120, context=atomic)
    assert result.accepted, result.rejection_reasons
    return context, json.loads(Path(produced.output_path).read_text()), atomic


def test_real_publication_generation_recovery_and_public_reader(enrolled):
    context, manifest, atomic = _activate(enrolled)
    assert manifest["schema_version"] == contract.SCHEMA_VERSION_INITIAL_V2
    assert "publication_receipt_id" not in manifest and "signer_audit_mac" not in manifest
    boundary = _reader(enrolled)
    current = boundary.consume(boundary.select({}, now_epoch=NOW))
    assert current["config_path"].endswith(contract.GRANT_AUTHORITY_SERVICE_CONFIG)
    assert current["run_packet_path"].endswith(contract.GRANT_AUTHORITY_SERVICE_RUN_PACKET)
    assert "principal_authority_records_path" not in current
    assert current["config_digest"] == current["config_raw_digest"] == manifest["signer_service_config_digest"]
    repeated = provision.provision_signer_runtime_generation(nonce=manifest["nonce"], ttl_seconds=120, context=atomic)
    assert repeated.accepted and repeated.generation == 1 and repeated.recovered_existing_activation
    assert len(list(enrolled.harness.manifest_directory.glob("*.json"))) == 1


def test_read_only_approval_verification_never_constructs_secret_resolver(enrolled, monkeypatch):
    _, manifest, _ = _activate(enrolled)
    monkeypatch.setattr(authority, "SystemdCredentialSecretResolver", lambda *a: pytest.fail("custody touched"))
    result = authority.verify_initial_runtime_manifest_approval(approval_path=enrolled.path,
        repo_root=enrolled.harness.repo_root, expected_approval_digest=contract.raw_digest(enrolled.path.read_bytes()),
        manifest=manifest)
    assert result["owner_config_id"] == OWNER_CONFIG_ID
    with pytest.raises(ValueError, match="approval_binding"):
        authority.verify_initial_runtime_manifest_approval(approval_path=enrolled.path,
            repo_root=enrolled.harness.repo_root, expected_approval_digest=contract.raw_digest(b"other"), manifest=manifest)


@pytest.mark.parametrize("field,value", [
    ("runtime_profile", "grant_authority_service"), ("owner_config_id", "sha256:" + "0" * 64),
    ("grant_authority_installed_runtime_descriptor_digest", "sha256:" + "0" * 64),
    ("signer_service_config_digest", "sha256:" + "0" * 64),
])
def test_approval_rejects_descriptor_owner_profile_and_target_config_substitution(enrolled, field, value):
    enrolled.value["manifest_spec"][field] = value
    enrolled.path.write_text(contract.canonical_json(enrolled.value))
    with pytest.raises(ValueError): _open(enrolled)
    assert not enrolled.calls


@pytest.mark.parametrize("kind", ["source_commit", "source_map", "self_key", "downgrade", "extra_work_field"])
def test_installation_identity_cannot_be_swapped_before_custody(enrolled, kind):
    value = enrolled.value
    if kind == "source_commit": value["source_commit_sha"] = "b" * 40
    elif kind == "source_map": value["source_files"]["modules/__init__.py"] = contract.raw_digest(b"bad")
    elif kind == "self_key": value["manifest_spec"]["signer_public_key"] = _profile()["public_key"]
    elif kind == "downgrade": value["schema_version"] = authority.SCHEMA_VERSION
    else: value["manifest_spec"]["publication_receipt_id"] = contract.raw_digest(b"fake")
    enrolled.path.write_text(contract.canonical_json(value))
    with pytest.raises(ValueError): _open(enrolled)
    assert not enrolled.calls


def test_initial_installed_is_not_legacy_work_authority(enrolled):
    context, manifest, _ = _activate(enrolled)
    old = enrolled.harness.context
    with pytest.raises(ValueError, match="initial_manifest_binding_mismatch"):
        verify_signed_runtime_artifact_manifest(manifest, authority=old.authority,
            authority_boundary=old.authority_boundary, now_epoch=NOW, signature_verifier=old.signature_verifier)
    request = _signing_request(manifest, contract.canonical_signing_input(manifest), context)
    assert validate_runtime_artifact_manifest_signing_request(request, old.authority,
        old.authority_boundary, now_epoch=NOW) is None
    assert contract.canonical_signing_input(manifest).startswith(contract.SIGNING_PREFIX_INITIAL_V2)


@pytest.mark.parametrize("generation", [0, 2, True, 1.0])
def test_installed_initial_generation_is_exactly_one(enrolled, generation):
    context = _open(enrolled)
    manifest = context.authority_boundary.require(context.authority)["initial_manifest"]
    with pytest.raises(ValueError, match="generation_invalid"):
        signer_runtime_generation_binding_from_manifest(manifest, generation=generation)


@pytest.mark.parametrize("kind", ["bundle", "approval", "expiry"])
def test_current_publication_revalidates_before_signing(enrolled, kind):
    context = _open(enrolled)
    if kind == "bundle":
        (enrolled.harness.runtime_root / contract.GRANT_AUTHORITY_INSTALLED_SOURCE).write_bytes(b"{}")
    elif kind == "approval": enrolled.path.write_text(enrolled.path.read_text() + " ")
    else: enrolled.clock["mono"] += 121
    assert not _produce(enrolled, context).accepted
    assert not list(enrolled.harness.manifest_directory.glob("*.json"))


def test_public_reader_rejects_after_artifact_mutation(enrolled):
    _activate(enrolled)
    boundary = _reader(enrolled)
    (enrolled.harness.runtime_root / contract.GRANT_AUTHORITY_SERVICE_CONFIG).write_bytes(b"{}")
    with pytest.raises(ValueError, match="manifest_artifacts_changed"):
        boundary.select({}, now_epoch=NOW)


def test_public_reader_rejects_even_authenticated_generation_two(enrolled):
    produced = _produce(enrolled, _open(enrolled))
    assert produced.accepted
    manifest = json.loads(Path(produced.output_path).read_text())
    binding = signer_runtime_generation_binding_from_manifest(manifest, generation=1)
    foreign = replace(binding, manifest_id=contract.raw_digest(b"foreign manifest"),
        artifact_generation_digest=contract.raw_digest(b"foreign artifacts"))
    current = enrolled.anchor.activate(foreign, expected_revision=None)
    enrolled.anchor.activate(replace(binding, generation=2), expected_revision=current.revision)
    boundary = _reader(enrolled)
    with pytest.raises(ValueError, match="initial_manifest_generation_invalid"):
        boundary.select({}, now_epoch=NOW)


@pytest.mark.parametrize("kind", ["signature", "expiry", "permission", "owner"])
def test_readonly_trusted_approval_still_requires_signature_scope_and_freshness(enrolled, kind):
    _, manifest, _ = _activate(enrolled)
    pin = contract.raw_digest(enrolled.path.read_bytes())
    if kind == "signature": manifest["signature"] = "not-a-signature"
    elif kind == "expiry": enrolled.clock["wall"] += 121
    elif kind == "owner": manifest["owner_config_id"] = contract.raw_digest(b"another owner")
    else:
        enrolled.value["permission"]["purpose"] = "write_repo"
        enrolled.path.write_text(contract.canonical_json(enrolled.value))
    with pytest.raises(ValueError):
        authority.verify_initial_runtime_manifest_approval(approval_path=enrolled.path,
            repo_root=enrolled.harness.repo_root, expected_approval_digest=pin, manifest=manifest)


def test_work_context_produces_distinct_work_manifest_not_initial_enrollment(enrolled):
    spec = enrolled.value["manifest_spec"]
    result = produce_signed_runtime_artifact_manifest(manifest_directory=enrolled.harness.manifest_directory,
        nonce=spec["nonce"], issued_at=NOW, expires_at=NOW + 120, context=enrolled.harness.context,
        runtime_profile=contract.RUNTIME_PROFILE_GRANT_AUTHORITY_INSTALLED_SOURCE)
    assert result.accepted
    manifest = json.loads(Path(result.output_path).read_text())
    assert manifest["schema_version"] == contract.SCHEMA_VERSION_V2
    assert "publication_receipt_id" in manifest and "enrollment_approval_digest" not in manifest
    with pytest.raises(ValueError):
        authority.verify_initial_runtime_manifest_approval(approval_path=enrolled.path,
            repo_root=enrolled.harness.repo_root,
            expected_approval_digest=contract.raw_digest(enrolled.path.read_bytes()), manifest=manifest)


def test_same_initial_nonce_cannot_advance_to_foreign_existing_generation(enrolled):
    context = _open(enrolled)
    produced = _produce(enrolled, context)
    assert produced.accepted
    manifest = json.loads(Path(produced.output_path).read_text())
    binding = signer_runtime_generation_binding_from_manifest(manifest, generation=1)
    current = enrolled.anchor.activate(replace(binding, manifest_id=contract.raw_digest(b"foreign")), expected_revision=None)
    atomic = create_signer_runtime_atomic_provisioning_context(manifest_signing=context, generation_anchor=enrolled.anchor)
    result = provision.provision_signer_runtime_generation(nonce=manifest["nonce"], ttl_seconds=120, context=atomic)
    assert not result.accepted
    assert enrolled.anchor.load() == current
