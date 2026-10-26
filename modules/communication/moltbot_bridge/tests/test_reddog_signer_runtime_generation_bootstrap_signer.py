"""Bounded initial-anchor signer; OS custody is qualified separately on Linux."""
import base64
import copy
import hashlib
import json
from types import SimpleNamespace
from dataclasses import FrozenInstanceError

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src import reddog_signer_runtime_generation_bootstrap_signer as subject
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import encode_ed25519_public_key
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_verifier_authority import create_signer_runtime_generation_verifier_authority
from modules.infrastructure.secrets_mcp.src.vault_resolver import ResolveResult, hash_reference


@pytest.fixture
def installed(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    path = tmp_path / "owner" / "bootstrap.json"
    path.parent.mkdir()
    key = Ed25519PrivateKey.generate()
    public = encode_ed25519_public_key(key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))
    raw = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    credential = "ed25519-private-raw-b64-v1:" + base64.b64encode(raw).decode("ascii")
    permission = dict(operation="SECRETS_READ", purpose=subject.PURPOSE, requester_id="installer",
                      reference="systemd-creds://generation", public_key=public, key_epoch="enrollment-1",
                      issued_at=1000, expires_at=1100)
    binding = dict(credential_directory="/run/credentials/enrollment.service", expected_uid=2001,
                   expected_gid=2001, expected_requester="installer", issued_at=1000,
                   expires_at=1100, credential_ids=["generation"])
    value = dict(schema_version=subject.SCHEMA_VERSION,
                 repo_root_digest="sha256:" + hashlib.sha256(str(repo.resolve()).encode()).hexdigest(),
                 identity=dict(public_key=public, key_epoch="enrollment-1"), credential_binding=binding,
                 permission=permission, consumer_uids=[2002], anchor_id="anchor-1", high_water_store_id="high-1",
                 high_water_durability_receipt_id="sha256:" + "a"*64,
                 generation_binding=dict(generation=1, **{field: "sha256:" + "b"*64 for field in (
                     "manifest_id", "artifact_generation_digest", "config_digest", "config_raw_digest", "run_packet_digest")}))
    path.write_bytes(subject._canonical(value))
    clock = {"wall": 1001., "mono": 50.}
    monkeypatch.setattr(subject.time, "time", lambda: clock["wall"])
    monkeypatch.setattr(subject.time, "monotonic", lambda: clock["mono"])
    monkeypatch.setattr(subject, "_read_root_owned_bytes", lambda target, root: target.read_bytes())
    monkeypatch.setattr(subject, "enforce_signer_process_isolation", lambda *a, **k: SimpleNamespace(accepted=True))
    resolutions = []
    class Resolver:
        def __init__(self, binding):
            pass
        def resolve(self, reference, requester_id):
            resolutions.append((reference, requester_id))
            return ResolveResult(success=True, reference=reference, reference_hash=hash_reference(reference),
                                 _secret_value=state.credential)
    monkeypatch.setattr(subject, "SystemdCredentialSecretResolver", Resolver)
    state = SimpleNamespace(repo=repo, path=path, value=value, clock=clock, resolutions=resolutions,
                            credential=credential, public=public)
    return state


def _open(state):
    return subject.load_initial_generation_anchor_signer(bootstrap_path=state.path, repo_root=state.repo)


def test_exact_anchor_signature_uses_existing_public_verifier(installed):
    signer = _open(installed)
    payload = subject._load(installed.path, installed.repo)[4]
    signature = signer.authenticate(payload)
    authority, boundary = create_signer_runtime_generation_verifier_authority(installed.public)
    verifier = boundary.require(authority)
    assert verifier.authenticator_id == signer.authenticator_id
    assert verifier.verify(payload, signature)
    assert not verifier.verify(payload + b" ", signature)
    assert signer.authenticate(payload) == signature
    assert len(installed.resolutions) == 2  # Fresh resolution; no retained private key.


@pytest.mark.parametrize("change", [
    {"anchor_id": "other"}, {"generation": 2}, {"config_digest": "sha256:" + "c"*64},
    {"high_water_store_id": "other"}, {"previous_revision": "a"*64},
    {"schema_version": "work_order.v1"},
])
def test_substituted_payload_rejected_before_resolution(installed, change):
    signer = _open(installed)
    value = json.loads(subject._load(installed.path, installed.repo)[4])
    value.update(change)
    with pytest.raises(ValueError, match="payload_not_authorized"):
        signer.authenticate(subject._canonical(value))
    assert installed.resolutions == []


@pytest.mark.parametrize("payload", [b"{}", b"arbitrary", "text", None, b'{"schema_version":"reddog_signer_runtime_generation_high_water.v2"}'])
def test_arbitrary_signing_rejected(installed, payload):
    with pytest.raises(ValueError, match="payload_not_authorized"):
        _open(installed).authenticate(payload)
    assert not installed.resolutions


@pytest.mark.parametrize("field,value", [("wall", 1100.), ("wall", 1000.), ("mono", 149.), ("mono", 49.)])
def test_time_change_rejected_before_resolution(installed, field, value):
    signer = _open(installed)
    payload = subject._load(installed.path, installed.repo)[4]
    installed.clock[field] = value
    with pytest.raises(ValueError, match="expired"):
        signer.authenticate(payload)
    assert not installed.resolutions


def test_replaced_policy_rejected_before_resolution(installed):
    signer = _open(installed)
    payload = subject._load(installed.path, installed.repo)[4]
    changed = copy.deepcopy(installed.value)
    changed["anchor_id"] = "other"
    installed.path.write_bytes(subject._canonical(changed))
    with pytest.raises(ValueError, match="config_changed"):
        signer.authenticate(payload)
    assert not installed.resolutions


def test_wrong_credential_key_rejected(installed):
    signer = _open(installed)
    key = Ed25519PrivateKey.generate().private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    installed.credential = "ed25519-private-raw-b64-v1:" + base64.b64encode(key).decode()
    with pytest.raises(ValueError, match="key_mismatch"):
        signer.authenticate(subject._load(installed.path, installed.repo)[4])


@pytest.mark.parametrize("mutation", [
    lambda v: v.update(extra=True),
    lambda v: v.update(repo_root_digest="sha256:" + "0"*64),
    lambda v: v["generation_binding"].update(generation=True),
    lambda v: v["generation_binding"].update(generation=2),
    lambda v: v["permission"].update(purpose="work_order"),
    lambda v: v["permission"].update(requester_id="other"),
    lambda v: v["permission"].update(expires_at=1200),
    lambda v: v["permission"].update(public_key="other"),
    lambda v: v["credential_binding"].update(credential_ids=["generation", "other"]),
    lambda v: v.update(consumer_uids=[2001]),
    lambda v: v.update(consumer_uids=[True]),
])
def test_policy_rejects_invalid_scope(installed, mutation):
    mutation(installed.value)
    installed.path.write_bytes(subject._canonical(installed.value))
    with pytest.raises((ValueError, TypeError)):
        _open(installed)
    assert not installed.resolutions


def test_duplicate_key_rejected(installed):
    raw = installed.path.read_text()
    installed.path.write_text(raw[:-1] + ',"anchor_id":"another"}')
    with pytest.raises(ValueError, match="duplicate_key"):
        _open(installed)


def test_isolation_rejection_prevents_resolver_construction(installed, monkeypatch):
    monkeypatch.setattr(subject, "enforce_signer_process_isolation", lambda *a, **k: SimpleNamespace(accepted=False))
    monkeypatch.setattr(subject, "SystemdCredentialSecretResolver", lambda *a: pytest.fail("must not construct resolver"))
    with pytest.raises(ValueError, match="isolation_rejected"):
        _open(installed)


def test_policy_expired_during_signing_is_not_returned(installed, monkeypatch):
    signer = _open(installed)
    original = subject.encode_ed25519_signature
    def expire(raw):
        installed.clock["wall"] = 1100.
        return original(raw)
    monkeypatch.setattr(subject, "encode_ed25519_signature", expire)
    with pytest.raises(ValueError, match="expired"):
        signer.authenticate(subject._load(installed.path, installed.repo)[4])


def test_signer_scope_is_immutable_and_rechecked_against_policy(installed):
    signer = _open(installed)
    with pytest.raises(FrozenInstanceError):
        signer._payload = b"arbitrary"
    with pytest.raises(TypeError):
        signer._permission["expires_at"] = 1200
    # Even an explicit Python object override cannot substitute the approved payload.
    object.__setattr__(signer, "_payload", b"arbitrary")
    with pytest.raises(ValueError, match="config_changed"):
        signer.authenticate(b"arbitrary")
    assert not installed.resolutions


@pytest.mark.parametrize("read_number", [1, 3])
def test_expiry_during_policy_read_rejected(installed, monkeypatch, read_number):
    signer = _open(installed)
    payload = subject._load(installed.path, installed.repo)[4]
    reads = []
    def read(target, root):
        reads.append(1)
        if len(reads) == read_number:
            installed.clock["wall"] = 1100.
        return target.read_bytes()
    monkeypatch.setattr(subject, "_read_root_owned_bytes", read)
    with pytest.raises(ValueError, match="expired"):
        signer.authenticate(payload)
    assert len(installed.resolutions) == (0 if read_number == 1 else 1)


def test_narrow_permission_expiry_during_resolution_prevents_signing(installed, monkeypatch):
    installed.value["credential_binding"]["expires_at"] = 1200
    installed.path.write_bytes(subject._canonical(installed.value))
    signer = _open(installed)
    original = signer._resolver.resolve
    def resolve(reference, requester_id):
        result = original(reference, requester_id)
        installed.clock["wall"] = 1100.
        return result
    monkeypatch.setattr(signer._resolver, "resolve", resolve)
    monkeypatch.setattr(subject, "_decode_ed25519_private_key", lambda *a: pytest.fail("expired authority must not decode key"))
    with pytest.raises(ValueError, match="expired"):
        signer.authenticate(subject._load(installed.path, installed.repo)[4])


def test_custody_denial_is_not_silently_accepted(installed, monkeypatch):
    signer = _open(installed)
    monkeypatch.setattr(signer._resolver, "resolve", lambda *a, **k: SimpleNamespace(success=False))
    with pytest.raises(ValueError, match="custody_rejected"):
        signer.authenticate(subject._load(installed.path, installed.repo)[4])


@pytest.fixture
def bootstrap(installed):
    """Synthetic owner policy and custody; no runtime permission or durability claim."""
    installed.value.update(schema_version=subject.BOOTSTRAP_SCHEMA_VERSION,
                           high_water_binding=dict(rollback_domain_digest="sha256:" + "c"*64,
                           witness_store_id="witness-1", witness_durability_receipt_id="sha256:" + "d"*64,
                           witness_binding_context_digest="sha256:" + "e"*64))
    installed.value["permission"]["purpose"] = subject.BOOTSTRAP_PURPOSE
    installed.path.write_bytes(subject._canonical(installed.value))
    return installed


def _open_bootstrap(state):
    return subject.load_initial_generation_bootstrap_signer(bootstrap_path=state.path, repo_root=state.repo)


def _high_water(state, form="committed"):
    signer = _open_bootstrap(state)
    payload = subject._load(state.path, state.repo, bootstrap=True)[4]
    anchor = json.loads(payload)
    tag = signer.authenticate(payload)
    # Independent canonical hash calculation includes the real verified signature.
    revision = hashlib.sha256(subject._canonical({**anchor, "authentication_tag": tag})).hexdigest()
    next_value = dict(generation=1, revision=revision)
    pending = dict(transaction_id="sha256:" + "f"*64, expected=None,
                   next_value=next_value, previous_anchor_state_json="{}")
    entries = {} if form == "abort" else {state.value["anchor_id"]: dict(
        current=next_value if form == "committed" else None,
        pending=pending if form == "prepared" else None)}
    value = dict(schema_version="reddog_signer_runtime_generation_high_water.v2",
                 store_id=state.value["high_water_store_id"],
                 durability_receipt_id=state.value["high_water_durability_receipt_id"],
                 authenticator_id=signer.authenticator_id, entries=entries,
                 **state.value["high_water_binding"])
    state.resolutions.clear()
    return signer, value


@pytest.mark.parametrize("form", ["prepared", "committed", "abort"])
def test_v2_exact_high_water_forms_verify_with_fresh_custody(bootstrap, form):
    signer, value = _high_water(bootstrap, form)
    payload = subject._canonical(value)
    signature = signer.authenticate(payload)
    authority, boundary = create_signer_runtime_generation_verifier_authority(bootstrap.public)
    assert boundary.require(authority).verify(payload, signature)
    assert len(bootstrap.resolutions) == (1 if form == "abort" else 2)


def test_loaders_reject_cross_schema_and_purpose(installed, bootstrap):
    with pytest.raises(ValueError, match="shape_invalid"):
        _open(bootstrap)
    bootstrap.value["permission"]["purpose"] = subject.PURPOSE
    bootstrap.path.write_bytes(subject._canonical(bootstrap.value))
    with pytest.raises(ValueError):
        _open_bootstrap(bootstrap)
    bootstrap.value.pop("high_water_binding")
    bootstrap.value["schema_version"] = subject.SCHEMA_VERSION
    bootstrap.path.write_bytes(subject._canonical(bootstrap.value))
    with pytest.raises(ValueError, match="shape_invalid"):
        _open_bootstrap(bootstrap)
    assert not installed.resolutions


@pytest.mark.parametrize("field", ["schema_version", "store_id", "durability_receipt_id", "authenticator_id",
                                 "rollback_domain_digest", "witness_store_id",
                                 "witness_durability_receipt_id", "witness_binding_context_digest", "extra"])
def test_v2_header_substitution_rejected_before_custody(bootstrap, field):
    signer, value = _high_water(bootstrap)
    value[field] = "different"
    with pytest.raises(ValueError):
        signer.authenticate(subject._canonical(value))
    assert not bootstrap.resolutions


@pytest.mark.parametrize("mutation", [
    lambda e: e.update(extra=None), lambda e: e["anchor-1"].update(extra=None),
    lambda e: e["anchor-1"]["pending"].update(expected=dict(generation=1, revision="a"*64)),
    lambda e: e["anchor-1"]["pending"].update(previous_anchor_state_json='{"extra":1}'),
    lambda e: e["anchor-1"]["pending"].update(transaction_id="sha256:" + "0"*64),
    lambda e: e["anchor-1"]["pending"].update(extra=None),
    lambda e: e["anchor-1"]["pending"]["next_value"].update(generation=True),
    lambda e: e["anchor-1"]["pending"]["next_value"].update(generation=2),
    lambda e: e["anchor-1"].update(pending=None),
])
def test_v2_invalid_initial_entry_rejected_before_custody(bootstrap, mutation):
    signer, value = _high_water(bootstrap, "prepared")
    mutation(value["entries"])
    with pytest.raises(ValueError):
        signer.authenticate(subject._canonical(value))
    assert not bootstrap.resolutions


@pytest.mark.parametrize("change", [lambda b: b+b" ", lambda b: b[:-1]+b',"entries":{}}',
                                  lambda b: b" "*16385, lambda b: b"[]"])
def test_v2_noncanonical_duplicate_oversize_or_wrong_shape_rejected(bootstrap, change):
    signer, value = _high_water(bootstrap)
    with pytest.raises(ValueError):
        signer.authenticate(change(subject._canonical(value)))
    assert not bootstrap.resolutions


def test_v2_wrong_revision_does_not_sign_high_water(bootstrap):
    signer, value = _high_water(bootstrap)
    value["entries"]["anchor-1"]["current"]["revision"] = "a"*64
    with pytest.raises(ValueError, match="revision_invalid"):
        signer.authenticate(subject._canonical(value))
    assert len(bootstrap.resolutions) == 1  # Only the approved anchor was signed.


def test_v2_header_override_and_policy_replacement_rejected(bootstrap):
    signer, value = _high_water(bootstrap)
    with pytest.raises(TypeError):
        signer._high_water_header["store_id"] = "different"
    object.__setattr__(signer, "_high_water_header", {**signer._high_water_header, "store_id": "different"})
    value["store_id"] = "different"
    with pytest.raises(ValueError, match="config_changed"):
        signer.authenticate(subject._canonical(value))
    signer, value = _high_water(bootstrap)
    bootstrap.value["high_water_binding"]["witness_store_id"] = "different"
    bootstrap.path.write_bytes(subject._canonical(bootstrap.value))
    with pytest.raises(ValueError, match="config_changed"):
        signer.authenticate(subject._canonical(value))
    assert not bootstrap.resolutions


@pytest.mark.parametrize("sign_number", [1, 2])
def test_v2_expiry_during_either_signature_returns_no_high_water(bootstrap, monkeypatch, sign_number):
    signer, value = _high_water(bootstrap)
    original = subject.encode_ed25519_signature
    calls = []
    def expire(raw):
        calls.append(1)
        if len(calls) == sign_number:
            bootstrap.clock["wall"] = 1100.
        return original(raw)
    monkeypatch.setattr(subject, "encode_ed25519_signature", expire)
    with pytest.raises(ValueError, match="expired"):
        signer.authenticate(subject._canonical(value))
    assert len(calls) == sign_number


def test_v2_existing_writer_prepares_aborts_and_commits_disposable_state(bootstrap, tmp_path):
    """Real local persistence, with explicitly synthetic policy and custody."""
    from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water import AtomicSignerRuntimeGenerationHighWaterStore
    from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import SqliteMonotonicAuthorityStore
    from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_witness_binding import SignerRuntimeGenerationWitnessBinding
    from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import SignerRuntimeGenerationHighWater
    high_root, witness_root = tmp_path / "high", tmp_path / "witness"
    metadata = bootstrap.value["high_water_binding"]
    witness = SqliteMonotonicAuthorityStore(witness_root / "witness.sqlite", allowed_root=witness_root,
        repo_root=bootstrap.repo, store_id=metadata["witness_store_id"], durability_receipt_id=metadata["witness_durability_receipt_id"])
    binding = SignerRuntimeGenerationWitnessBinding(authenticator_id=_open_bootstrap(bootstrap).authenticator_id,
        signer_public_key_fingerprint="sha256:" + hashlib.sha256(subject.decode_ed25519_public_key(bootstrap.public)).hexdigest(),
        key_epoch="enrollment-1", runtime_root_digest="sha256:" + "b"*64,
        high_water_store_id=bootstrap.value["high_water_store_id"], high_water_durability_receipt_id=bootstrap.value["high_water_durability_receipt_id"],
        witness_store_id=witness.store_id, witness_durability_receipt_id=witness.durability_receipt_id)
    metadata.update(rollback_domain_digest="sha256:" + hashlib.sha256(str(high_root.resolve()).encode()).hexdigest(),
                    witness_binding_context_digest=binding.context_digest())
    bootstrap.path.write_bytes(subject._canonical(bootstrap.value))
    signer, value = _high_water(bootstrap)
    authority, boundary = create_signer_runtime_generation_verifier_authority(bootstrap.public)
    store = AtomicSignerRuntimeGenerationHighWaterStore(high_root / "high.json", allowed_root=high_root,
        repo_root=bootstrap.repo, store_id=bootstrap.value["high_water_store_id"], durability_receipt_id=bootstrap.value["high_water_durability_receipt_id"],
        signer=signer, verifier=boundary.require(authority), generation_witness_store=witness, generation_witness_binding=binding)
    next_value = SignerRuntimeGenerationHighWater(**value["entries"]["anchor-1"]["current"])
    pending = store.prepare("anchor-1", expected=None, next_value=next_value)
    store.abort_prepared("anchor-1", pending.transaction_id)
    assert store.load("anchor-1") is None and store.pending("anchor-1") is None
    pending = store.prepare("anchor-1", expected=None, next_value=next_value)
    store.witness_advance("anchor-1", expected=None, next_value=next_value)
    store.commit_prepared("anchor-1", pending.transaction_id)
    assert store.load("anchor-1") == store.witness_load("anchor-1") == next_value
    assert store.pending("anchor-1") is None


@pytest.mark.parametrize('value', [True, 1.0, '1'])
def test_committed_generation_requires_actual_integer(bootstrap, value):
    signer, record = _high_water(bootstrap)
    record['entries']['anchor-1']['current']['generation'] = value
    with pytest.raises(ValueError):
        signer.authenticate(subject._canonical(record))
    assert not bootstrap.resolutions

@pytest.mark.parametrize('entries', [[], None, False])
def test_abort_requires_an_actual_mapping(bootstrap, entries):
    signer, record = _high_water(bootstrap, 'abort')
    record['entries'] = entries
    with pytest.raises(ValueError):
        signer.authenticate(subject._canonical(record))
    assert not bootstrap.resolutions

def test_second_resolution_custody_failure_cannot_return_high_water(bootstrap, monkeypatch):
    signer, record = _high_water(bootstrap)
    original = signer._resolver.resolve
    def revoke(reference, requester_id):
        result = original(reference, requester_id)
        if len(bootstrap.resolutions) == 2:
            result.success = False
        return result
    monkeypatch.setattr(signer._resolver, 'resolve', revoke)
    with pytest.raises(ValueError, match='custody_rejected'):
        signer.authenticate(subject._canonical(record))
    assert len(bootstrap.resolutions) == 2

def test_v1_cannot_gain_v2_scope_by_header_override(installed):
    signer = _open(installed)
    object.__setattr__(signer, '_high_water_header', {'schema_version': 'invented'})
    with pytest.raises(ValueError, match='config_changed'):
        signer.authenticate(b'{}')
    assert not installed.resolutions
