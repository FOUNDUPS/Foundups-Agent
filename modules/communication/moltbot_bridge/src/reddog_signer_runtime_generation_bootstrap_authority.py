"""Protected initial-generation writer composition, not manifest admission.

Receipts are installer-trusted recorded filesystem qualifications. Their stored
observations do not independently prove fsync execution or power-loss durability.
Existing stores own persistence; this adapter confines their authority and order.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from . import reddog_signer_runtime_generation_bootstrap_signer as bootstrap
from . import reddog_signer_system_service_manifest_selection_loader as owner_loader
from .reddog_atomic_signer_runtime_generation_high_water import AtomicSignerRuntimeGenerationHighWaterStore, _load_store_state
from .reddog_signer_runtime_generation_contract import (
    SignerRuntimeGenerationHighWater, VerifiedSignerRuntimeGenerationHighWater, _build_process_local_registry,
)
from .reddog_signer_runtime_generation_verifier_authority import create_signer_runtime_generation_verifier_authority
from .reddog_sqlite_monotonic_authority_store import SqliteMonotonicAuthorityReader, SqliteMonotonicAuthorityStore
from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    confined_file_identity, secure_digest_confined_file_impl,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock, validate_runtime_artifact_path, validate_runtime_root_path,
)

RECEIPT_SCHEMA = "reddog_generation_store_qualification.v1"
_RECEIPT_FIELDS = {"schema_version", "store_kind", "repo_root_digest", "root", "path", "store_id",
    "device", "root_inode", "owner_uid", "owner_gid", "evidence_scope", "probe_path",
    "probe_content_sha256", "probe_size_bytes", "file_fsynced", "directory_fsynced",
    "reopened_equal", "power_loss_tested"}


def _digest(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _protected(path, repo):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("generation_writer_policy_path_invalid")
    root = validate_runtime_root_path(path.parent, repo_root=repo)
    target = validate_runtime_artifact_path(path, allowed_root=root, repo_root=repo)
    raw = owner_loader._read_root_owned_bytes(target, root)
    value = json.loads(raw.decode("ascii"), object_pairs_hook=bootstrap._unique)
    if type(value) is not dict:
        raise ValueError("generation_writer_policy_shape_invalid")
    return target, raw, value


def _current_identity():
    return os.geteuid(), os.getegid()


def _stat(path):
    return path.lstat()


def _private_metadata(path, uid, gid, *, directory=False):
    metadata = _stat(path)
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if (not kind(metadata.st_mode) or metadata.st_mode & 0o022
            or metadata.st_uid != uid or metadata.st_gid != gid
            or (not directory and metadata.st_nlink != 1)):
        raise ValueError("generation_writer_path_ownership_invalid")
    return metadata


def _receipt(path, *, kind, owner, repo, uid, gid):
    target, raw, value = _protected(path, repo)
    if (set(value) != _RECEIPT_FIELDS or value["schema_version"] != RECEIPT_SCHEMA
            or value["store_kind"] != kind or value["evidence_scope"] != "filesystem_fsync_reopen"
            or any(value[name] is not True for name in ("file_fsynced", "directory_fsynced", "reopened_equal"))
            or value["power_loss_tested"] is not False):
        raise ValueError("generation_writer_receipt_shape_invalid")
    if (any(type(value[name]) is not int or value[name] < 0 for name in
            ("device", "root_inode", "owner_uid", "owner_gid", "probe_size_bytes"))
            or not 1 <= value["probe_size_bytes"] <= 65536):
        raise ValueError("generation_writer_receipt_metadata_invalid")
    root = validate_runtime_root_path(owner[kind + "_root"], repo_root=repo)
    store_path = validate_runtime_artifact_path(owner[kind + "_path"], allowed_root=root, repo_root=repo)
    expected = dict(root=str(root), path=str(store_path), store_id=owner[kind + "_store_id"],
                    repo_root_digest=_digest(str(repo).encode()), owner_uid=uid, owner_gid=gid)
    if (any(value[name] != item for name, item in expected.items())
            or _digest(raw) != owner[kind + "_durability_receipt_id"]):
        raise ValueError("generation_writer_receipt_binding_invalid")
    metadata = _private_metadata(root, uid, gid, directory=True)
    if (metadata.st_dev, metadata.st_ino) != (value["device"], value["root_inode"]):
        raise ValueError("generation_writer_root_identity_changed")
    if store_path.exists():
        if _private_metadata(store_path, uid, gid).st_dev != value["device"]:
            raise ValueError("generation_writer_store_device_changed")
    probe = validate_runtime_artifact_path(value["probe_path"], allowed_root=root, repo_root=repo)
    if (probe.parent != root or probe == store_path or probe.name.endswith(".lock")
            or probe.name.startswith(store_path.name + "-")):
        raise ValueError("generation_writer_probe_path_invalid")
    observed = _private_metadata(probe, uid, gid)
    if observed.st_dev != value["device"] or observed.st_size != value["probe_size_bytes"]:
        raise ValueError("generation_writer_probe_identity_invalid")
    proof = secure_digest_confined_file_impl(probe, allowed_root=root,
        expected_identity=confined_file_identity(probe.lstat()), max_bytes=value["probe_size_bytes"])
    if "sha256:" + proof.digest.removeprefix("sha256:") != value["probe_content_sha256"]:
        raise ValueError("generation_writer_probe_digest_invalid")
    _private_metadata(probe, uid, gid)
    return target, raw


def _inputs(owner_path, bootstrap_path, receipt_paths, repo):
    owner_target, owner_raw, owner = _protected(owner_path, repo)
    checked = owner_loader._load_owner_config(owner_target, repo=repo)
    if checked != owner:
        raise ValueError("generation_writer_owner_changed")
    boot_target, boot_raw, _ = _protected(bootstrap_path, repo)
    loaded = bootstrap._load(boot_target, repo, bootstrap=True)
    if loaded[0] != boot_raw:
        raise ValueError("generation_writer_bootstrap_changed")
    _, policy, credentials, authenticator, _ = loaded
    if _current_identity() != (credentials.expected_uid, credentials.expected_gid):
        raise ValueError("generation_writer_process_identity_invalid")
    witness_binding = owner_loader._witness_binding(owner, runtime=Path(owner["runtime_root"]).resolve())
    public = bootstrap.decode_ed25519_public_key(owner["generation_public_key"])
    expected = {"generation_public_key": policy["identity"]["public_key"],
        "generation_key_epoch": policy["identity"]["key_epoch"], "generation_authenticator_id": authenticator,
        "generation_signer_public_key_fingerprint": _digest(public) if public is not None else None,
        "anchor_id": policy["anchor_id"], "high_water_store_id": policy["high_water_store_id"],
        "high_water_durability_receipt_id": policy["high_water_durability_receipt_id"]}
    header = dict(rollback_domain_digest=_digest(str(Path(owner["high_water_root"]).resolve()).encode()),
        witness_store_id=owner["witness_store_id"], witness_durability_receipt_id=owner["witness_durability_receipt_id"],
        witness_binding_context_digest=witness_binding.context_digest())
    if any(owner[name] != value for name, value in expected.items()) or policy["high_water_binding"] != header:
        raise ValueError("generation_writer_bootstrap_owner_mismatch")
    receipts = tuple(_receipt(p, kind=k, owner=owner, repo=repo, uid=credentials.expected_uid,
        gid=credentials.expected_gid) for p, k in zip(receipt_paths, ("high_water", "witness")))
    paths = (owner_target, boot_target, *(p for p, _ in receipts))
    roots = tuple(Path(owner[name]).resolve() for name in ("runtime_root", "high_water_root", "witness_root"))
    if len(set(paths)) != 4 or any(p == r or r in p.parents for p in paths for r in roots):
        raise ValueError("generation_writer_policy_domain_invalid")
    _private_metadata(roots[0], credentials.expected_uid, credentials.expected_gid, directory=True)
    return owner, loaded, witness_binding, (owner_raw, boot_raw, *(raw for _, raw in receipts))


def _check_policy(repo, paths, snapshots, signer):
    signer._check()
    owner, _, binding, current = _inputs(paths[0], paths[1], paths[2:], repo)
    if current != snapshots:
        raise ValueError("generation_writer_policy_changed")
    signer._check()
    return owner, binding


@dataclass(frozen=True)
class _State:
    repo: Path
    paths: tuple
    snapshots: tuple
    signer: object
    store: AtomicSignerRuntimeGenerationHighWaterStore
    anchor_id: str
    revision: str
    lock_path: Path

    def check(self):
        owner, binding = _check_policy(self.repo, self.paths, self.snapshots, self.signer)
        # Reopen validates preprovisioned witness identity on every use; never silently recreate it.
        reader = SqliteMonotonicAuthorityReader(owner["witness_path"], allowed_root=owner["witness_root"],
            repo_root=self.repo, store_id=owner["witness_store_id"], durability_receipt_id=owner["witness_durability_receipt_id"])
        witnessed = reader.load(binding.anchor_binding_digest(self.anchor_id))
        persisted = _load_store_state(self.store)
        entry = {}
        if persisted:
            unsigned = {k: v for k, v in persisted.items() if k not in {"authentication_tag", "revision"}}
            revision = bootstrap._initial_high_water_revision(bootstrap._canonical(unsigned),
                self.signer._high_water_header, self.anchor_id)
            if revision is not None and revision != self.revision:
                raise ValueError("generation_writer_persisted_scope_invalid")
            entry = persisted["entries"].get(self.anchor_id, {})
        if (witnessed is not None and (witnessed.sequence != 1 or witnessed.state_revision != self.revision or not entry)
                or entry.get("current") is not None and witnessed is None):
            raise ValueError("generation_writer_persisted_witness_invalid")
        self.signer._check()

    @contextmanager
    def operation(self, anchor):
        if type(anchor) is not str or anchor != self.anchor_id:
            raise ValueError("generation_writer_anchor_scope_invalid")
        self.check()
        with confined_runtime_operation_lock(self.lock_path, repo_root=self.repo,
                                             allowed_root=self.store.rollback_domain_root):
            self.check()
            yield
            self.check()

    def pending(self, transaction=None):
        if transaction is not None and type(transaction) is not str:
            raise ValueError("generation_writer_transaction_scope_invalid")
        pending = self.store.pending(self.anchor_id)
        if (pending is None or pending.expected is not None or pending.next_value.generation != 1
                or pending.next_value.revision != self.revision or pending.previous_anchor_state_json != "{}"
                or (transaction is not None and pending.transaction_id != transaction)):
            raise ValueError("generation_writer_pending_scope_invalid")
        return pending


def _approved_next(value, revision):
    return (type(value) is SignerRuntimeGenerationHighWater and type(value.generation) is int
            and value.generation == 1 and type(value.revision) is str and value.revision == revision)


def _methods(lookup):
    def load(self, anchor_id):
        state = lookup(self)
        with state.operation(anchor_id):
            return state.store.load(anchor_id)
    def pending(self, anchor_id):
        state = lookup(self)
        with state.operation(anchor_id):
            return state.store.pending(anchor_id)
    def witness_load(self, anchor_id):
        state = lookup(self)
        with state.operation(anchor_id):
            return state.store.witness_load(anchor_id)
    def prepare(self, anchor_id, *, expected, next_value, previous_anchor_state_json="{}"):
        state = lookup(self)
        with state.operation(anchor_id):
            if (expected is not None or not _approved_next(next_value, state.revision)
                    or type(previous_anchor_state_json) is not str or previous_anchor_state_json != "{}"
                    or state.store.witness_load(anchor_id) is not None):
                raise ValueError("generation_writer_prepare_scope_invalid")
            state.check()
            return state.store.prepare(anchor_id, expected=expected, next_value=next_value,
                                       previous_anchor_state_json=previous_anchor_state_json)
    def witness_advance(self, anchor_id, *, expected, next_value):
        state = lookup(self)
        with state.operation(anchor_id):
            p = state.pending()
            if (expected is not None or not _approved_next(next_value, state.revision)
                    or next_value != p.next_value):
                raise ValueError("generation_writer_witness_scope_invalid")
            state.check()
            state.store.witness_advance(anchor_id, expected=expected, next_value=next_value)
    def finish(self, anchor_id, transaction_id, *, commit):
        if type(transaction_id) is not str:
            raise ValueError("generation_writer_transaction_scope_invalid")
        state = lookup(self)
        with state.operation(anchor_id):
            p = state.pending(transaction_id)
            if state.store.witness_load(anchor_id) != (p.next_value if commit else p.expected):
                raise ValueError("generation_writer_witness_order_invalid")
            method = state.store.commit_prepared if commit else state.store.abort_prepared
            state.check()
            method(anchor_id, transaction_id)
    def commit(self, anchor_id, transaction_id):
        return finish(self, anchor_id, transaction_id, commit=True)
    def abort(self, anchor_id, transaction_id):
        return finish(self, anchor_id, transaction_id, commit=False)
    def advance(self, anchor_id, *, expected, next_value):
        raise ValueError("generation_writer_transaction_required")
    def property_for(name):
        return property(lambda self: getattr(lookup(self).store, name))
    return dict(load=load, pending=pending, witness_load=witness_load, prepare=prepare,
        witness_advance=witness_advance, commit_prepared=commit, abort_prepared=abort, advance=advance,
        **{name: property_for(name) for name in ("store_id", "durability_receipt_id", "rollback_domain_root", "witness_rollback_domain_root")})


def _capabilities():
    issue_handle, lookup_handle = _build_process_local_registry("generation_writer_handle_unverified")
    issue_boundary, lookup_boundary = _build_process_local_registry("generation_writer_boundary_unverified")
    handle_type = type("_WriterHandle", (), {"__slots__": ("__weakref__",), **_methods(lookup_handle)})
    class Boundary:
        __slots__ = ("__weakref__",)
        def require(self, value):
            authority, handle = lookup_boundary(self)
            if value is not authority:
                raise ValueError("generation_writer_authority_unverified")
            lookup_handle(handle).check()
            return VerifiedSignerRuntimeGenerationHighWater(handle, handle.store_id, handle.durability_receipt_id)
    def issue(state):
        handle, boundary, authority = handle_type(), Boundary(), object()
        issue_handle(handle, state)
        issue_boundary(boundary, (authority, handle))
        return authority, boundary
    def require(authority, boundary):
        if type(boundary) is not Boundary:
            raise ValueError("generation_writer_boundary_invalid")
        return boundary.require(authority)
    return issue, require


_issue, require_initial_generation_high_water_authority = _capabilities()


def _load_authority(*, owner_config_path, bootstrap_path,
        high_water_receipt_path, witness_receipt_path, repo_root, issue):
    """Load installer-qualified stores; return initial-only guarded writer authority.

    Derives one approved public anchor revision through fresh credential signing.
    Does not activate an anchor, install policy, or authorize manifest admission.
    """
    repo = Path(repo_root).resolve()
    paths = tuple(Path(p) for p in (owner_config_path, bootstrap_path, high_water_receipt_path, witness_receipt_path))
    owner, loaded, binding, snapshots = _inputs(paths[0], paths[1], paths[2:], repo)
    signer = bootstrap.load_initial_generation_bootstrap_signer(bootstrap_path=paths[1], repo_root=repo)
    witness_args = dict(allowed_root=owner["witness_root"], repo_root=repo, store_id=owner["witness_store_id"],
                        durability_receipt_id=owner["witness_durability_receipt_id"])
    reader = SqliteMonotonicAuthorityReader(owner["witness_path"], **witness_args)
    reader.load(binding.anchor_binding_digest(owner["anchor_id"]))
    witness = SqliteMonotonicAuthorityStore(owner["witness_path"], require_existing=True,
        mutation_guard=lambda: _check_policy(repo, paths, snapshots, signer), **witness_args)
    public_authority, public_boundary = create_signer_runtime_generation_verifier_authority(owner["generation_public_key"])
    store = AtomicSignerRuntimeGenerationHighWaterStore(owner["high_water_path"], allowed_root=owner["high_water_root"],
        repo_root=repo, store_id=owner["high_water_store_id"], durability_receipt_id=owner["high_water_durability_receipt_id"],
        signer=signer, verifier=public_boundary.require(public_authority), generation_witness_store=witness,
        generation_witness_binding=binding)
    tag = signer.authenticate(loaded[4])
    revision = bootstrap._state_revision({**json.loads(loaded[4]), "authentication_tag": tag})
    state = _State(repo, paths, snapshots, signer, store, owner["anchor_id"], revision,
                   Path(owner["high_water_path"]).with_name("high-water.bootstrap-authority.lock"))
    state.check()
    return issue(state)


def _loader(issue, load):
    def load_initial_generation_high_water_authority(*, owner_config_path, bootstrap_path,
            high_water_receipt_path, witness_receipt_path, repo_root):
        return load(owner_config_path=owner_config_path, bootstrap_path=bootstrap_path,
            high_water_receipt_path=high_water_receipt_path, witness_receipt_path=witness_receipt_path,
            repo_root=repo_root, issue=issue)
    return load_initial_generation_high_water_authority


load_initial_generation_high_water_authority = _loader(_issue, _load_authority)
del _issue, _loader, _load_authority, _capabilities, _methods


__all__ = ["load_initial_generation_high_water_authority", "require_initial_generation_high_water_authority"]
