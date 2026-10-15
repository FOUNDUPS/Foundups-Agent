"""Real disposable persistence; synthetic root installation, UID and custody.

These fixtures do not qualify a production filesystem or issue runtime grants.
"""
import copy
import hashlib
import json
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src import reddog_signer_runtime_generation_bootstrap_authority as subject
from modules.communication.moltbot_bridge.tests.test_reddog_signer_runtime_generation_bootstrap_signer import installed
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import SignerRuntimeGenerationHighWater, SignerRuntimeGenerationBinding
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import DurableSignerRuntimeGenerationAnchor


def _sha(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _write(path, value):
    path.write_bytes(subject.bootstrap._canonical(value))


def _refresh(state):
    owner, boot = state.owner, state.installed.value
    for kind, path in zip(("high_water", "witness"), state.receipts):
        owner[kind + "_durability_receipt_id"] = _sha(path.read_bytes())
    boot["high_water_durability_receipt_id"] = owner["high_water_durability_receipt_id"]
    boot["high_water_binding"] = dict(rollback_domain_digest=_sha(str(state.high).encode()),
        witness_store_id=owner["witness_store_id"], witness_durability_receipt_id=owner["witness_durability_receipt_id"],
        witness_binding_context_digest=subject.owner_loader._witness_binding(owner, runtime=state.runtime).context_digest())
    owner["config_id"] = subject.owner_loader.digest({k: v for k, v in owner.items() if k != "config_id"})
    _write(state.owner_path, owner)
    _write(state.installed.path, boot)


@pytest.fixture
def configured(installed, tmp_path, monkeypatch):
    runtime, high, witness_root = (tmp_path / name for name in ("runtime", "high", "witness"))
    for root in (runtime, high, witness_root):
        root.mkdir()
    def observed(path):
        actual = path.lstat()
        values = {name: getattr(actual, name) for name in ("st_dev", "st_ino", "st_nlink", "st_size")}
        values.update(st_uid=2001, st_gid=2001, st_mode=stat.S_IFMT(actual.st_mode) | (0o700 if path.is_dir() else 0o600))
        values.update(overrides.get(str(path), {}))
        return SimpleNamespace(**values)
    overrides = {}
    monkeypatch.setattr(subject, "_stat", observed)
    monkeypatch.setattr(subject, "_current_identity", lambda: (2001, 2001))
    monkeypatch.setattr(subject.owner_loader, "_read_root_owned_bytes", lambda target, root: target.read_bytes())
    boot = installed.value
    boot["schema_version"] = subject.bootstrap.BOOTSTRAP_SCHEMA_VERSION
    boot["permission"]["purpose"] = subject.bootstrap.BOOTSTRAP_PURPOSE
    owner = dict(schema_version=subject.owner_loader.SCHEMA_VERSION, repo_root_digest=boot["repo_root_digest"],
        runtime_root=str(runtime), anchor_path=str(runtime / "generation-anchor.json"), anchor_id=boot["anchor_id"],
        generation_public_key=installed.public, generation_key_epoch=boot["identity"]["key_epoch"],
        generation_authenticator_id="ed25519-generation:" + hashlib.sha256(subject.bootstrap.decode_ed25519_public_key(installed.public)).hexdigest(),
        generation_signer_public_key_fingerprint=_sha(subject.bootstrap.decode_ed25519_public_key(installed.public)),
        high_water_root=str(high), high_water_path=str(high / "high-water.json"), high_water_store_id=boot["high_water_store_id"],
        witness_root=str(witness_root), witness_path=str(witness_root / "generation.sqlite3"), witness_store_id="witness-1")
    receipts = []
    for kind, root in (("high_water", high), ("witness", witness_root)):
        probe = root / "qualification-probe.bin"
        probe.write_bytes(b"Synthetic retained fixture; not real fsync qualification.")
        receipt = dict(schema_version=subject.RECEIPT_SCHEMA, store_kind=kind, root=str(root), path=owner[kind + "_path"],
            store_id=owner[kind + "_store_id"], repo_root_digest=boot["repo_root_digest"], device=root.stat().st_dev,
            root_inode=root.stat().st_ino, owner_uid=2001, owner_gid=2001, evidence_scope="filesystem_fsync_reopen",
            probe_path=str(probe), probe_content_sha256=_sha(probe.read_bytes()), probe_size_bytes=probe.stat().st_size,
            file_fsynced=True, directory_fsynced=True, reopened_equal=True, power_loss_tested=False)
        path = installed.path.parent / (kind + "-receipt.json")
        _write(path, receipt)
        receipts.append(path)
    state = SimpleNamespace(installed=installed, owner=owner, owner_path=installed.path.parent / "owner.json",
        runtime=runtime, high=high, receipts=tuple(receipts), overrides=overrides)
    _refresh(state)
    state.witness = subject.SqliteMonotonicAuthorityStore(owner["witness_path"], allowed_root=witness_root,
        repo_root=installed.repo, store_id=owner["witness_store_id"], durability_receipt_id=owner["witness_durability_receipt_id"])
    state.arguments = dict(owner_config_path=state.owner_path, bootstrap_path=installed.path,
        high_water_receipt_path=receipts[0], witness_receipt_path=receipts[1], repo_root=installed.repo)
    return state


def _open(state):
    authority, boundary = subject.load_initial_generation_high_water_authority(**state.arguments)
    verified = subject.require_initial_generation_high_water_authority(authority, boundary)
    return authority, boundary, verified.store


def _next(state):
    payload = subject.bootstrap._load(state.installed.path, state.installed.repo, bootstrap=True)[4]
    signer = subject.bootstrap.load_initial_generation_bootstrap_signer(bootstrap_path=state.installed.path, repo_root=state.installed.repo)
    signed = {**json.loads(payload), "authentication_tag": signer.authenticate(payload)}
    return SignerRuntimeGenerationHighWater(1, hashlib.sha256(subject.bootstrap._canonical(signed)).hexdigest())


def _witness(state):
    binding = subject.owner_loader._witness_binding(state.owner, runtime=state.runtime)
    return state.witness.load(binding.anchor_binding_digest(state.owner["anchor_id"]))


def test_existing_stores_support_guarded_initial_transaction(configured):
    _, _, writer = _open(configured)
    value = _next(configured)
    p = writer.prepare("anchor-1", expected=None, next_value=value)
    with pytest.raises(ValueError, match="witness_order"):
        writer.commit_prepared("anchor-1", p.transaction_id)
    writer.abort_prepared("anchor-1", p.transaction_id)
    assert writer.load("anchor-1") is None
    p = writer.prepare("anchor-1", expected=None, next_value=value)
    writer.witness_advance("anchor-1", expected=None, next_value=value)
    with pytest.raises(ValueError, match="witness_order"):
        writer.abort_prepared("anchor-1", p.transaction_id)
    writer.commit_prepared("anchor-1", p.transaction_id)
    assert writer.load("anchor-1") == writer.witness_load("anchor-1") == value
    assert writer.pending("anchor-1") is None


def test_forged_foreign_and_mutable_capabilities_rejected(configured):
    authority, boundary, writer = _open(configured)
    other, _, _ = _open(configured)
    for invalid in (object(), other):
        with pytest.raises(ValueError):
            boundary.require(invalid)
    for invalid in (SimpleNamespace(require=lambda a: writer), type(boundary)()):
        with pytest.raises(ValueError):
            subject.require_initial_generation_high_water_authority(authority, invalid)
    with pytest.raises(AttributeError):
        writer.store_id = "foreign"
    with pytest.raises(ValueError, match="transaction_required"):
        writer.advance("anchor-1", expected=None, next_value=_next(configured))
    assert all(not hasattr(subject, name) for name in ("_issue", "_load_authority", "_loader"))


@pytest.mark.parametrize("field,value", [("device", True), ("root_inode", True), ("owner_uid", True),
    ("owner_gid", True), ("probe_size_bytes", True), ("probe_size_bytes", 65537), ("probe_size_bytes", 0),
    ("file_fsynced", 1), ("directory_fsynced", False), ("reopened_equal", "true"), ("power_loss_tested", 0),
    ("evidence_scope", "power_loss"), ("store_kind", "witness"), ("extra", "unapproved"),
    ("probe_content_sha256", "sha256:" + "f"*64), ("store_id", "other"), ("path", "elsewhere")])
def test_false_or_substituted_qualification_rejected(configured, field, value):
    receipt = json.loads(configured.receipts[0].read_bytes())
    receipt[field] = value
    _write(configured.receipts[0], receipt)
    _refresh(configured)
    with pytest.raises(ValueError):
        _open(configured)


@pytest.mark.parametrize("field,value", [("st_uid", 2002), ("st_gid", 2002),
    ("st_mode", stat.S_IFDIR | 0o722), ("st_ino", 12345), ("st_dev", 12345)])
def test_real_root_metadata_must_match_receipt(configured, field, value):
    configured.overrides[str(configured.high)] = {field: value}
    with pytest.raises(ValueError):
        _open(configured)


@pytest.mark.parametrize("field,value", [("generation_key_epoch", "other"), ("generation_authenticator_id", "other"),
    ("generation_signer_public_key_fingerprint", "sha256:" + "f"*64), ("anchor_id", "other")])
def test_owner_bootstrap_cross_binding_rejected(configured, field, value):
    configured.owner[field] = value
    _refresh(configured)
    with pytest.raises(ValueError, match="bootstrap_owner"):
        _open(configured)


def test_duplicate_owner_and_unprovisioned_witness_rejected(configured):
    raw = configured.owner_path.read_bytes()
    configured.owner_path.write_bytes(raw[:-1] + b',"anchor_id":"anchor-1"}')
    with pytest.raises(ValueError, match="duplicate"):
        _open(configured)
    configured.owner_path.write_bytes(raw)
    from pathlib import Path
    Path(configured.owner["witness_path"]).unlink()
    with pytest.raises(Exception):
        _open(configured)
    assert not Path(configured.owner["witness_path"]).exists()


def test_witness_requires_exact_authenticated_pending(configured):
    _, _, writer = _open(configured)
    value = _next(configured)
    with pytest.raises(ValueError, match="pending_scope"):
        writer.witness_advance("anchor-1", expected=None, next_value=value)
    p = writer.prepare("anchor-1", expected=None, next_value=value)
    for anchor, expected, candidate in (("foreign", None, value), ("anchor-1", value, value),
            ("anchor-1", None, SignerRuntimeGenerationHighWater(1, "f"*64))):
        with pytest.raises(ValueError):
            writer.witness_advance(anchor, expected=expected, next_value=candidate)
    assert _witness(configured) is None
    with pytest.raises(ValueError):
        writer.abort_prepared("anchor-1", "sha256:" + "f"*64)
    assert writer.pending("anchor-1") == p


@pytest.mark.parametrize("operation", ["prepare", "witness_advance", "commit_prepared", "abort_prepared"])
@pytest.mark.parametrize("change", ["expiry", "owner", "probe", "uid"])
def test_every_mutation_rechecks_authority(configured, monkeypatch, operation, change):
    _, _, writer = _open(configured)
    value = _next(configured)
    p = writer.prepare("anchor-1", expected=None, next_value=value)
    if operation == "commit_prepared":
        writer.witness_advance("anchor-1", expected=None, next_value=value)
    if change == "expiry":
        configured.installed.clock["wall"] = 1100.
    elif change == "owner":
        configured.owner_path.write_bytes(configured.owner_path.read_bytes() + b" ")
    elif change == "probe":
        (configured.high / "qualification-probe.bin").write_bytes(b"changed")
    else:
        monkeypatch.setattr(subject, "_current_identity", lambda: (2002, 2001))
    before = (configured.high / "high-water.json").read_bytes()
    witness_before = _witness(configured)
    with pytest.raises(ValueError):
        if operation in ("prepare", "witness_advance"):
            getattr(writer, operation)("anchor-1", expected=None, next_value=value)
        else:
            getattr(writer, operation)("anchor-1", p.transaction_id)
    assert (configured.high / "high-water.json").read_bytes() == before
    assert _witness(configured) == witness_before


def _anchor(state, authority, boundary):
    signer = subject.bootstrap.load_initial_generation_bootstrap_signer(bootstrap_path=state.installed.path, repo_root=state.installed.repo)
    va, vb = subject.create_signer_runtime_generation_verifier_authority(state.installed.public)
    return DurableSignerRuntimeGenerationAnchor(state.owner["anchor_path"],
        allowed_root=subject.owner_loader._owner_anchor_root(state.owner, repo=state.installed.repo),
        repo_root=state.installed.repo, anchor_id="anchor-1", signer=signer, verifier=vb.require(va),
        high_water_authority=authority, high_water_authority_boundary=boundary)


def _separate_anchor(state):
    root = state.runtime.parent / "anchor"
    root.mkdir()
    state.owner["anchor_path"] = str(root / "generation-anchor.json")
    _refresh(state)
    return root


def test_separate_private_anchor_accepts_protected_artifact_runtime(configured):
    root = _separate_anchor(configured)
    configured.overrides[str(configured.runtime)] = {
        "st_uid": 0, "st_gid": 0, "st_mode": stat.S_IFDIR | 0o755,
    }
    authority, boundary, writer = _open(configured)
    anchor = _anchor(configured, authority, boundary)
    activation = anchor.activate(
        SignerRuntimeGenerationBinding(**configured.installed.value["generation_binding"]),
        expected_revision=None, commit_guard=lambda candidate: None,
    )
    assert activation.generation == 1
    assert (root / "generation-anchor.json").is_file()
    assert not (configured.runtime / "generation-anchor.json").exists()
    assert writer.load("anchor-1") == writer.witness_load("anchor-1")


@pytest.mark.parametrize("field,value", (
    ("st_uid", 0), ("st_gid", 0), ("st_mode", stat.S_IFDIR | 0o722),
))
def test_separate_anchor_retains_private_ownership_checks(configured, field, value):
    root = _separate_anchor(configured)
    configured.overrides[str(root)] = {field: value}
    with pytest.raises(ValueError, match="path_ownership"):
        _open(configured)


def test_separate_anchor_ownership_rechecked_before_mutation(configured):
    root = _separate_anchor(configured)
    _, _, writer = _open(configured)
    value = _next(configured)
    configured.overrides[str(root)] = {"st_uid": 0}
    with pytest.raises(ValueError, match="path_ownership"):
        writer.prepare("anchor-1", expected=None, next_value=value)
    assert not (configured.high / "high-water.json").exists()


@pytest.mark.parametrize("kind", ("bootstrap", "receipt"))
def test_separate_anchor_cannot_contain_root_policy_or_receipt(configured, kind):
    root = _separate_anchor(configured)
    original = configured.installed.path if kind == "bootstrap" else configured.receipts[0]
    target = root / original.name
    target.write_bytes(original.read_bytes())
    argument = "bootstrap_path" if kind == "bootstrap" else "high_water_receipt_path"
    configured.arguments[argument] = target
    with pytest.raises(ValueError, match="policy_domain"):
        _open(configured)


def test_existing_anchor_rolls_back_before_witness_when_guard_rejects(configured):
    authority, boundary, writer = _open(configured)
    anchor = _anchor(configured, authority, boundary)
    def reject(candidate):
        raise ValueError("synthetic_manifest_rejection")
    with pytest.raises(ValueError, match="synthetic_manifest_rejection"):
        anchor.activate(SignerRuntimeGenerationBinding(**configured.installed.value["generation_binding"]),
                        expected_revision=None, commit_guard=reject)
    assert anchor.load() is None and writer.pending("anchor-1") is None
    assert writer.witness_load("anchor-1") is None


def test_existing_anchor_recovers_after_witness_advance(configured, monkeypatch):
    authority, boundary, writer = _open(configured)
    anchor = _anchor(configured, authority, boundary)
    original = type(writer).commit_prepared
    def interrupted(*args):
        raise RuntimeError("synthetic_interruption_after_witness")
    monkeypatch.setattr(type(writer), "commit_prepared", interrupted)
    with pytest.raises(RuntimeError, match="synthetic_interruption"):
        anchor.activate(SignerRuntimeGenerationBinding(**configured.installed.value["generation_binding"]),
                        expected_revision=None, commit_guard=lambda candidate: None)
    assert writer.pending("anchor-1") is not None and writer.witness_load("anchor-1") is not None
    monkeypatch.setattr(type(writer), "commit_prepared", original)
    # Recovery uses a newly loaded authority in the same process, never a fabricated pending record.
    authority, boundary, fresh = _open(configured)
    recovered = _anchor(configured, authority, boundary).recover(commit_guard=lambda candidate: None)
    assert recovered.generation == 1 and fresh.pending("anchor-1") is None
    assert fresh.load("anchor-1") == fresh.witness_load("anchor-1")


def test_changed_persisted_high_water_rejected_before_witness(configured):
    _, _, writer = _open(configured)
    value = _next(configured)
    writer.prepare("anchor-1", expected=None, next_value=value)
    path = configured.high / "high-water.json"
    record = json.loads(path.read_bytes())
    record["entries"]["anchor-1"]["pending"]["next_value"]["revision"] = "f"*64
    _write(path, record)
    with pytest.raises(ValueError):
        writer.witness_advance("anchor-1", expected=None, next_value=value)
    assert _witness(configured) is None


def test_wrong_persisted_witness_identity_rejected(configured):
    import sqlite3
    with sqlite3.connect(configured.owner["witness_path"]) as connection:
        connection.execute("UPDATE metadata SET store_id = ?", ("foreign",))
    with pytest.raises(ValueError, match="identity_mismatch"):
        _open(configured)


def test_receipt_must_be_outside_mutable_roots(configured):
    moved = configured.high / "receipt.json"
    moved.write_bytes(configured.receipts[0].read_bytes())
    configured.arguments["high_water_receipt_path"] = moved
    with pytest.raises(ValueError, match="policy_domain"):
        _open(configured)


def test_wrong_revision_and_linked_probe_rejected(configured):
    _, _, writer = _open(configured)
    with pytest.raises(ValueError, match="prepare_scope"):
        writer.prepare("anchor-1", expected=None, next_value=SignerRuntimeGenerationHighWater(1, "f"*64))
    assert writer.pending("anchor-1") is None
    configured.overrides[str(configured.high / "qualification-probe.bin")] = {"st_nlink": 2}
    with pytest.raises(ValueError, match="ownership"):
        _open(configured)


def test_expiry_during_receipt_read_prevents_witness_mutation(configured, monkeypatch):
    _, _, writer = _open(configured)
    value = _next(configured)
    writer.prepare("anchor-1", expected=None, next_value=value)
    original = subject._receipt
    def expire(*args, **kwargs):
        result = original(*args, **kwargs)
        configured.installed.clock["wall"] = 1100.
        return result
    monkeypatch.setattr(subject, "_receipt", expire)
    with pytest.raises(ValueError, match="expired"):
        writer.witness_advance("anchor-1", expected=None, next_value=value)
    assert _witness(configured) is None


def test_concurrent_abort_and_witness_are_serialized(configured):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    _, _, writer = _open(configured)
    _, _, second = _open(configured)
    value = _next(configured)
    p = writer.prepare("anchor-1", expected=None, next_value=value)
    ready = Barrier(2)
    def attempt(abort):
        ready.wait(timeout=10)
        try:
            if abort:
                writer.abort_prepared("anchor-1", p.transaction_id)
            else:
                second.witness_advance("anchor-1", expected=None, next_value=value)
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, (True, False)))
    assert sum(results) == 1
    if _witness(configured) is None:
        assert writer.pending("anchor-1") is None
    else:
        assert writer.pending("anchor-1") == p


@pytest.mark.parametrize("field", ["anchor", "value", "generation", "revision", "transaction", "snapshot"])
def test_equality_overrides_cannot_authorize_mutation(configured, field):
    class Equal:
        def __eq__(self, other):
            return True
        def __ne__(self, other):
            return False
    class EqualString(Equal, str):
        pass
    class EqualInteger(Equal, int):
        pass
    class EqualHighWater(Equal, SignerRuntimeGenerationHighWater):
        pass
    _, _, writer = _open(configured)
    value = _next(configured)
    if field == "snapshot":
        with pytest.raises(ValueError, match="prepare_scope"):
            writer.prepare("anchor-1", expected=None, next_value=value,
                           previous_anchor_state_json=EqualString("foreign"))
        assert writer.pending("anchor-1") is None
    else:
        pending = writer.prepare("anchor-1", expected=None, next_value=value)
        before = (configured.high / "high-water.json").read_bytes()
        anchor = EqualString("foreign-anchor") if field == "anchor" else "anchor-1"
        if field == "value":
            value = EqualHighWater(1, "f"*64)
        elif field == "generation":
            value = SignerRuntimeGenerationHighWater(EqualInteger(2), value.revision)
        elif field == "revision":
            value = SignerRuntimeGenerationHighWater(1, EqualString("f"*64))
        with pytest.raises(ValueError):
            if field == "transaction":
                writer.abort_prepared(anchor, EqualString("foreign-transaction"))
            else:
                writer.witness_advance(anchor, expected=None, next_value=value)
        assert (configured.high / "high-water.json").read_bytes() == before
        assert writer.pending("anchor-1") == pending
    binding = subject.owner_loader._witness_binding(configured.owner, runtime=configured.runtime)
    for anchor in ("anchor-1", "foreign-anchor"):
        assert configured.witness.load(binding.anchor_binding_digest(anchor)) is None


@pytest.mark.parametrize("read", ["pending", "sqlite_current"])
def test_expiry_after_transaction_read_prevents_witness_write(configured, monkeypatch, read):
    _, _, writer = _open(configured)
    value = _next(configured)
    writer.prepare("anchor-1", expected=None, next_value=value)
    from modules.communication.moltbot_bridge.src import reddog_sqlite_monotonic_authority_store as sqlite_owner
    target, name = (subject._State, "pending") if read == "pending" else (sqlite_owner, "_read_current")
    original = getattr(target, name)
    def delayed(*args, **kwargs):
        result = original(*args, **kwargs)
        configured.installed.clock["wall"] = 1100.
        return result
    monkeypatch.setattr(target, name, delayed)
    with pytest.raises(ValueError, match="expired"):
        writer.witness_advance("anchor-1", expected=None, next_value=value)
    assert _witness(configured) is None


def test_witness_removed_after_reader_is_not_recreated(configured, monkeypatch):
    import sqlite3
    from pathlib import Path
    original = subject.SqliteMonotonicAuthorityReader.load
    target = Path(configured.owner["witness_path"])
    def removed(self, digest):
        result = original(self, digest)
        target.unlink()
        return result
    monkeypatch.setattr(subject.SqliteMonotonicAuthorityReader, "load", removed)
    with pytest.raises(sqlite3.OperationalError, match="unable to open"):
        _open(configured)
    assert not target.exists()
