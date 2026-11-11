"""Initial manifest contracts; OS isolation/root installation are test seams.

Real Ed25519, artifact IO and atomic generation stores run in disposable roots.
These tests are not native worker admission or deployment evidence.
"""
import base64
import copy
import json
import os
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization

from modules.communication.moltbot_bridge.src import reddog_initial_runtime_manifest_authority as subject
from modules.communication.moltbot_bridge.src import reddog_signer_runtime_atomic_provisioning as provision
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    REQUIRED_RUNTIME_ARTIFACTS, canonical_json, canonical_signing_input, digest, raw_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    _signing_request, produce_signed_runtime_artifact_manifest, verify_signed_runtime_artifact_manifest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning_contract import (
    create_signer_runtime_atomic_provisioning_context,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_runtime_atomic_provisioning import (
    _context, _test_only_activation_lease,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import NOW
from modules.infrastructure.secrets_mcp.src.vault_resolver import ResolveResult, hash_reference


@pytest.fixture
def installed(tmp_path, monkeypatch):
    harness, anchor, _ = _context(tmp_path)
    path = tmp_path / "owner" / "initial.json"
    path.parent.mkdir()
    # Initial byte attestation must not require invented work/publication fields.
    for name in ("authority_profile.json", "authoritative_work_state.json"):
        (harness.runtime_root / name).write_text("{}", encoding="ascii")
    descriptors = [{"filename": name, "byte_count": len((harness.runtime_root / name).read_bytes()),
                    "content_digest": raw_digest((harness.runtime_root / name).read_bytes())}
                   for name in REQUIRED_RUNTIME_ARTIFACTS]
    public = harness.reddog_public_key
    raw = harness.reddog_private_key.private_bytes(serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw, serialization.NoEncryption())
    credential = "ed25519-private-raw-b64-v1:" + base64.b64encode(raw).decode("ascii")
    permission = dict(operation="SECRETS_READ", purpose=subject.PURPOSE,
        requester_id="initial-installer", reference="systemd-creds://manifest",
        public_key=public, key_epoch="initial-1", issued_at=NOW, expires_at=NOW + 120)
    binding = dict(credential_directory="/run/credentials/initial.service", expected_uid=2001,
        expected_gid=2001, expected_requester="initial-installer", issued_at=NOW,
        expires_at=NOW + 120, credential_ids=["manifest"])
    spec = dict(issuer_principal_id="local:initial-owner", signer_public_key=public,
        key_epoch="initial-1", nonce="initial-manifest-1", issued_at=NOW, expires_at=NOW + 120,
        authority_profile_digest=digest({}), artifacts=descriptors,
        signer_service_config_digest=digest(json.loads((harness.runtime_root / "signer_service_config.json").read_text())))
    value = dict(schema_version=subject.SCHEMA_VERSION, repo_root_digest=raw_digest(str(harness.repo_root).encode()),
        runtime_root=str(harness.runtime_root), source_commit_sha="a" * 40,
        source_files={"installed.py": raw_digest(b"source")}, manifest_spec=spec,
        credential_binding=binding, permission=permission, consumer_uids=[2002])
    clock = {"wall": float(NOW), "mono": 50.0}
    calls = []
    state = SimpleNamespace(harness=harness, anchor=anchor, path=path, value=value,
                            clock=clock, calls=calls, credential=credential)
    path.write_text(canonical_json(value), encoding="ascii")
    monkeypatch.setattr(subject.time, "time", lambda: clock["wall"])
    monkeypatch.setattr(subject.time, "monotonic", lambda: clock["mono"])
    monkeypatch.setattr(subject, "_read_root_owned_bytes", lambda target, root, **kwargs: target.read_bytes())
    monkeypatch.setattr(subject, "_check_sources", lambda *args: None)
    monkeypatch.setattr(subject, "enforce_signer_process_isolation", lambda *a, **k: SimpleNamespace(accepted=True))
    if os.name != "nt":
        monkeypatch.setattr(provision, "runtime_artifact_activation_lease", _test_only_activation_lease)

    class Resolver:
        def __init__(self, binding):
            pass

        def resolve(self, reference, requester_id):
            calls.append((reference, requester_id))
            return ResolveResult(success=True, reference=reference, reference_hash=hash_reference(reference),
                                 _secret_value=state.credential)

    monkeypatch.setattr(subject, "SystemdCredentialSecretResolver", Resolver)
    return state


def _open(state):
    return subject.load_initial_runtime_manifest_signing_context(
        approval_path=state.path, repo_root=state.harness.repo_root)


def _produce(state, context):
    spec = state.value["manifest_spec"]
    return produce_signed_runtime_artifact_manifest(manifest_directory=state.harness.manifest_directory,
        nonce=spec["nonce"], issued_at=spec["issued_at"], expires_at=spec["expires_at"], context=context)


def test_initial_manifest_produces_verifies_and_activates_via_existing_recovery(installed):
    context = _open(installed)
    produced = _produce(installed, context)
    assert produced.accepted, produced
    payload = json.loads(Path(produced.output_path).read_text())
    assert "publication_receipt_id" not in payload
    assert "consensus_receipt_digest" not in payload
    verified = verify_signed_runtime_artifact_manifest(payload, authority=context.authority,
        authority_boundary=context.authority_boundary, now_epoch=NOW,
        signature_verifier=subject.Ed25519SignatureVerifier())
    assert verified["manifest_id"] == produced.manifest_id
    installed.clock["wall"] += 10
    atomic = create_signer_runtime_atomic_provisioning_context(manifest_signing=context,
                                                             generation_anchor=installed.anchor)
    result = provision.provision_signer_runtime_generation(nonce="initial-manifest-1", ttl_seconds=120, context=atomic)
    assert result.accepted, result.to_dict()
    assert result.generation == 1 and result.manifest_id == produced.manifest_id
    assert result.recovered_existing_activation
    assert len(list(installed.harness.manifest_directory.glob("*.json"))) == 1
    assert installed.anchor.load().manifest_id == produced.manifest_id


@pytest.mark.parametrize("mutation", [
    lambda v: v.update(extra=True),
    lambda v: v.update(repo_root_digest="sha256:" + "0" * 64),
    lambda v: v.update(source_commit_sha="invalid"),
    lambda v: v["manifest_spec"].update(issued_at=True),
    lambda v: v["manifest_spec"].update(consensus_receipt_digest="sha256:" + "0" * 64),
    lambda v: v["permission"].update(purpose="work_order"),
    lambda v: v["permission"].update(expires_at=NOW + 121),
    lambda v: v.update(consumer_uids=[2001]),
    lambda v: v.update(consumer_uids=[True]),
    lambda v: v["credential_binding"].update(credential_ids=["manifest", "other"]),
])
def test_invalid_installation_rejected_before_custody(installed, mutation):
    mutation(installed.value)
    installed.path.write_text(canonical_json(installed.value), encoding="ascii")
    with pytest.raises((TypeError, ValueError)):
        _open(installed)
    assert not installed.calls


@pytest.mark.parametrize("field,value", [
    ("nonce", "other"), ("requested_operation", "write_repo"),
    ("signer_role", "reddog_runtime_artifact_manifest"), ("authority_tier", "HIGH"),
    ("consensus_receipt_digest", "sha256:" + "0" * 64),
])
def test_signer_cannot_sign_other_scope(installed, field, value):
    context = _open(installed)
    payload = context.authority_boundary.require(context.authority)["initial_manifest"]
    request = _signing_request(payload, canonical_signing_input(payload), context)
    with pytest.raises(ValueError, match="scope_invalid"):
        context.signer.sign(replace(request, **{field: value}))
    assert not installed.calls


@pytest.mark.parametrize("kind", ["expiry", "rollback", "changed_policy", "artifact", "wrong_key"])
def test_change_before_production_rejects(installed, kind):
    context = _open(installed)
    if kind == "expiry":
        installed.clock["wall"] += 120
    elif kind == "rollback":
        installed.clock["wall"] -= 1
    elif kind == "changed_policy":
        installed.path.write_text(installed.path.read_text() + " ")
    elif kind == "artifact":
        (installed.harness.runtime_root / "execution_valve_env.json").write_text("{}")
    else:
        installed.credential = "not-a-key"
    produced = _produce(installed, context)
    assert not produced.accepted
    assert installed.anchor.load() is None


def test_isolation_rejects_before_resolver(installed, monkeypatch):
    monkeypatch.setattr(subject, "enforce_signer_process_isolation", lambda *a, **k: SimpleNamespace(accepted=False))
    monkeypatch.setattr(subject, "SystemdCredentialSecretResolver", lambda *a: pytest.fail("unexpected custody"))
    with pytest.raises(ValueError, match="isolation_rejected"):
        _open(installed)


def test_foreign_capability_and_mutated_returned_values_cannot_change_approval(installed):
    context = _open(installed)
    with pytest.raises(ValueError, match="authority_unverified"):
        context.authority_boundary.require(object())
    values = context.authority_boundary.require(context.authority)
    values["initial_manifest"]["nonce"] = "foreign"
    assert context.authority_boundary.require(context.authority)["initial_manifest"]["nonce"] == "initial-manifest-1"


def test_source_inventory_requires_current_authority_and_rejects_drift(tmp_path, monkeypatch):
    repo = tmp_path / "source"
    repo.mkdir()
    path = repo / "authority.py"
    path.write_bytes(b"approved")
    monkeypatch.setattr(subject, "__file__", str(path))
    monkeypatch.setattr(subject, "sys", SimpleNamespace(modules={"modules.authority": SimpleNamespace(__file__=str(path))}))
    monkeypatch.setattr(subject, "_read_root_owned_bytes", lambda target, root, **kwargs: target.read_bytes())
    sources = {"authority.py": raw_digest(b"approved")}
    subject._check_sources(repo, sources)
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="source_changed"):
        subject._check_sources(repo, sources)


# Independently discovered regressions retained in the canonical suite.
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import signer_runtime_generation_binding_from_manifest
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import validate_runtime_artifact_manifest_signing_request
SOURCE_CHECK = subject._check_sources

def test_expiry_while_waiting_to_publish_rejected(installed, monkeypatch):
    from modules.communication.moltbot_bridge.src import reddog_runtime_artifact_manifest_io as artifact_io
    actual = artifact_io.reddog_runtime_artifact_generation_lock
    entered = []

    @contextmanager
    def delayed(*args, **kwargs):
        with actual(*args, **kwargs):
            entered.append(True)
            # First lock verifies current artifacts; second publishes them.
            if len(entered) == 2:
                installed.clock['wall'] += 121
                installed.clock['mono'] += 121
            yield

    monkeypatch.setattr(artifact_io, 'reddog_runtime_artifact_generation_lock', delayed)
    result = _produce(installed, _open(installed))
    assert not result.accepted, result.to_dict()
    assert not list(installed.harness.manifest_directory.glob('*.json'))


def test_initial_recovery_rejects_generation_two(installed):
    context = _open(installed)
    produced = _produce(installed, context)
    assert produced.accepted
    manifest = json.loads(Path(produced.output_path).read_text())
    second = replace(signer_runtime_generation_binding_from_manifest(manifest, generation=1), generation=2)
    first = replace(second, generation=1, manifest_id='sha256:' + 'e' * 64,
                    artifact_generation_digest='sha256:' + 'd' * 64)
    previous = installed.anchor.activate(first, expected_revision=None)
    installed.anchor.activate(second, expected_revision=previous.revision)
    atomic = create_signer_runtime_atomic_provisioning_context(manifest_signing=context, generation_anchor=installed.anchor)
    result = provision.provision_signer_runtime_generation(nonce='initial-manifest-1', ttl_seconds=120, context=atomic)
    assert not result.accepted, result.to_dict()


def test_initial_rejects_foreign_existing_generation(installed):
    context = _open(installed)
    produced = _produce(installed, context)
    assert produced.accepted
    manifest = json.loads(Path(produced.output_path).read_text())
    binding = signer_runtime_generation_binding_from_manifest(manifest, generation=1)
    foreign = replace(binding, manifest_id='sha256:' + 'e' * 64,
                      artifact_generation_digest='sha256:' + 'd' * 64)
    existing = installed.anchor.activate(foreign, expected_revision=None)
    atomic = create_signer_runtime_atomic_provisioning_context(manifest_signing=context, generation_anchor=installed.anchor)
    result = provision.provision_signer_runtime_generation(nonce='initial-manifest-1', ttl_seconds=120, context=atomic)
    assert not result.accepted, result.to_dict()
    assert installed.anchor.load() == existing


def test_concurrent_identical_initial_calls_never_advance_beyond_one(installed):
    context = _open(installed)
    atomic = create_signer_runtime_atomic_provisioning_context(manifest_signing=context, generation_anchor=installed.anchor)

    def execute(_):
        return provision.provision_signer_runtime_generation(nonce='initial-manifest-1', ttl_seconds=120, context=atomic)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(execute, range(2)))
    assert any(result.accepted for result in results), [r.to_dict() for r in results]
    assert all(not result.accepted or result.generation == 1 for result in results)
    assert installed.anchor.load().generation == 1
    repeated = execute(None)
    assert repeated.accepted and repeated.generation == 1
    assert repeated.recovered_existing_activation
    assert len(list(installed.harness.manifest_directory.glob('*.json'))) == 1


def test_initial_cannot_verify_with_legacy_work_authority(installed):
    context = _open(installed)
    produced = _produce(installed, context)
    assert produced.accepted
    manifest = json.loads(Path(produced.output_path).read_text())
    legacy = installed.harness.context
    with pytest.raises(ValueError, match='initial_manifest_binding_mismatch'):
        verify_signed_runtime_artifact_manifest(manifest, authority=legacy.authority,
            authority_boundary=legacy.authority_boundary, now_epoch=NOW,
            signature_verifier=legacy.signature_verifier)


def test_initial_request_rejected_by_legacy_signing_validator(installed):
    context = _open(installed)
    manifest = context.authority_boundary.require(context.authority)['initial_manifest']
    request = _signing_request(manifest, canonical_signing_input(manifest), context)
    legacy = installed.harness.context
    assert validate_runtime_artifact_manifest_signing_request(request, legacy.authority, legacy.authority_boundary, now_epoch=NOW) is None


def test_expiry_during_resolution_rejected(installed, monkeypatch):
    real = subject.SystemdCredentialSecretResolver

    class Delayed(real):
        def resolve(self, *args, **kwargs):
            result = super().resolve(*args, **kwargs)
            installed.clock['mono'] += 121
            return result

    monkeypatch.setattr(subject, 'SystemdCredentialSecretResolver', Delayed)
    context = _open(installed)
    result = _produce(installed, context)
    assert not result.accepted
    assert installed.anchor.load() is None
    assert not list(installed.harness.manifest_directory.glob('*.json'))


def test_policy_change_during_resolution_rejected(installed, monkeypatch):
    real = subject.SystemdCredentialSecretResolver

    class Changed(real):
        def resolve(self, *args, **kwargs):
            result = super().resolve(*args, **kwargs)
            installed.path.write_text(installed.path.read_text() + ' ')
            return result

    monkeypatch.setattr(subject, 'SystemdCredentialSecretResolver', Changed)
    result = _produce(installed, _open(installed))
    assert not result.accepted
    assert installed.anchor.load() is None


def test_expiry_while_waiting_for_generation_lock_rejected(installed, monkeypatch):
    context = _open(installed)

    @contextmanager
    def delayed(*args, **kwargs):
        installed.clock['mono'] += 121
        yield

    monkeypatch.setattr(subject, 'reddog_runtime_artifact_generation_lock', delayed)
    with pytest.raises(ValueError, match='clock_or_expiry_invalid'):
        with context.authority_boundary.revalidation_fence(context.authority, now_epoch=NOW):
            pytest.fail('Expired boundary yielded authority')


@pytest.mark.parametrize('kind', ['missing_own', 'unbound_loaded', 'external_repo_module', 'bad_digest', 'parent_path'])
def test_real_inventory_rejects_missing_or_wrong_source(tmp_path, monkeypatch, kind):
    repo = tmp_path / 'bundle'
    repo.mkdir()
    own = repo / 'authority.py'
    own.write_bytes(b'approved')
    other = repo / 'other.py'
    other.write_bytes(b'other')
    sources = {'authority.py': raw_digest(b'approved')}
    modules = {'modules.authority': SimpleNamespace(__file__=str(own))}
    if kind == 'missing_own':
        sources = {'other.py': raw_digest(b'other')}
    elif kind == 'unbound_loaded':
        modules['unusual_alias'] = SimpleNamespace(__file__=str(other))
    elif kind == 'external_repo_module':
        modules['modules.foreign'] = SimpleNamespace(__file__=str(tmp_path / 'outside.py'))
    elif kind == 'bad_digest':
        sources['authority.py'] = raw_digest(b'wrong')
    else:
        sources['../outside.py'] = raw_digest(b'other')
    monkeypatch.setattr(subject, '__file__', str(own))
    monkeypatch.setattr(subject, 'sys', SimpleNamespace(modules=modules))
    monkeypatch.setattr(subject, '_read_root_owned_bytes', lambda path, root, **kwargs: path.read_bytes())
    with pytest.raises(ValueError):
        SOURCE_CHECK(repo, sources)
