"""Root-owned mirrored CAS state for verified-outcome authority."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VERIFIED_OUTCOME_SIGNING_PREFIX, VerifiedOutcomeResponseBinding,
    parse_verified_outcome_response_record,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import (
    validate_root_verified_outcome_descriptor_public,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_wire_codec import (
    decode_message, PENDING_RESPONSE_SCHEMA, MAX_PENDING_RESPONSE_RECORDS,
    MAX_PENDING_RESPONSE_STORE_BYTES, pending_response_records as _pending_response_records,
    pending_response_snapshot as _pending_response_snapshot,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
)


GENERATION_BINDING = "sha256:" + hashlib.sha256(
    b"foundup-verified-outcome-root-authority-generation.v1"
).hexdigest()
INSTALLATION_BINDING = "sha256:" + hashlib.sha256(
    b"foundup-verified-outcome-root-authority-installation.v1"
).hexdigest()
PROTECTED_USE_BINDING = "sha256:" + hashlib.sha256(
    b"foundup-root-signer-protected-use.v1"
).hexdigest()
_STATE_BINDING_NAMES = ("state", "state_witness", "installation")
_STATE_BINDING_FIELDS = ("root", "path", "store_id", "durability_receipt_id")


class RootVerifiedOutcomeAuthorityState:
    """Three-domain root-owned monotonic state with deterministic repair."""

    def __init__(
        self,
        primary: SqliteMonotonicAuthorityStore,
        witness: SqliteMonotonicAuthorityStore,
        installation: SqliteMonotonicAuthorityStore,
        *,
        repo_root: Path | str,
        require_root_ownership: bool = True,
    ) -> None:
        if any(
            type(item) is not SqliteMonotonicAuthorityStore
            for item in (primary, witness, installation)
        ):
            raise ValueError("root_authority_state_store_invalid")
        first = primary.rollback_domain_root.resolve()
        second = witness.rollback_domain_root.resolve()
        third = installation.rollback_domain_root.resolve()
        if any(
            _overlap(left, right)
            for left, right in ((first, second), (first, third), (second, third))
        ):
            raise ValueError("root_authority_state_domain_overlap")
        if require_root_ownership:
            _require_root_owned(first, second, third)
        self._primary = primary
        self._witness = witness
        self._installation = installation
        self._repo_root = Path(repo_root).resolve()
        self._require_ownership = require_root_ownership
        self._lock_path = first / ".verified-outcome-root-authority.lock"
        self._state_binding_digest = root_authority_state_binding_digest(
            {
                name: _store_binding(store)
                for name, store in zip(
                    _STATE_BINDING_NAMES,
                    (primary, witness, installation),
                    strict=True,
                )
            }
        )

    @property
    def store_id(self) -> str:
        return self._primary.store_id

    @property
    def durability_receipt_id(self) -> str:
        return self._primary.durability_receipt_id

    @property
    def durable(self) -> bool:
        return True

    @property
    def rollback_domain_root(self) -> Path:
        return self._primary.rollback_domain_root

    @property
    def witness_store_id(self) -> str:
        return self._witness.store_id

    @property
    def witness_durability_receipt_id(self) -> str:
        return self._witness.durability_receipt_id

    @property
    def state_binding_digest(self) -> str:
        return self._state_binding_digest

    @property
    def rollback_domain_roots(self) -> tuple[Path, Path, Path]:
        return tuple(
            store.rollback_domain_root
            for store in (self._primary, self._witness, self._installation)
        )

    def load(self, binding_digest: str) -> ProposalReplayHighWater | None:
        with self._lock():
            self._require_installed()
            return self._current(binding_digest)

    def persist_pending_response(
        self, raw: bytes, *, expected_binding: VerifiedOutcomeResponseBinding,
        expected_record_digest: str, now_epoch: int,
    ) -> str:
        """Persist selected bytes while leaving the exact grant reserved."""
        return self._persist_response(
            raw, expected_binding=expected_binding, expected_record_digest=expected_record_digest,
            now_epoch=now_epoch, terminal=False,
        )

    def commit_pending_response(
        self, raw: bytes, *, expected_binding: VerifiedOutcomeResponseBinding,
        expected_record_digest: str, expected_reservation: ProposalReplayHighWater,
        now_epoch: int,
    ) -> str:
        """Commit the full record only after durable exact-byte readback."""
        return self._persist_response(
            raw, expected_binding=expected_binding, expected_record_digest=expected_record_digest,
            now_epoch=now_epoch, terminal=True, expected_reservation=expected_reservation,
        )

    def _persist_response(
        self, raw: bytes, *, expected_binding: VerifiedOutcomeResponseBinding,
        expected_record_digest: str, now_epoch: int, terminal: bool,
        expected_reservation: ProposalReplayHighWater | None = None,
    ) -> str:
        generation, reserved = _pending_response_context(
            raw, expected_binding, expected_record_digest, now_epoch,
        )
        if terminal and reserved != expected_reservation:
            raise ValueError("root_record_commit_reservation_mismatch")
        authorization_id = expected_binding.authorization_id
        selection = pending_response_binding(authorization_id)
        wanted = ProposalReplayHighWater(1, expected_record_digest[7:])
        committed = ProposalReplayHighWater(2, expected_record_digest[7:])
        with self._lock():
            self._require_installed()
            current_grant = self._current(authorization_binding(authorization_id))
            if (self._current(GENERATION_BINDING) != generation
                or current_grant not in ({reserved, committed} if terminal else {reserved})):
                raise RuntimeError("root_pending_response_context_conflict")
            store = AtomicJsonAuthorityRuntimeStore(
                self._primary.rollback_domain_root / "verified-outcome-pending-responses.json",
                allowed_root=self._primary.rollback_domain_root, repo_root=self._repo_root,
            )
            self._require_pending_file_ownership(store)
            current = store.load()
            records = _pending_response_records(current)
            self._validate_pending_records(records)
            previous = records.get(authorization_id)
            marker = self._current(selection)
            if (previous is not None and previous != raw.decode("ascii")) or (
                marker is not None and marker != wanted
            ) or ((previous is not None or current_grant == committed) and marker is None):
                raise RuntimeError("root_pending_response_conflict")
            snapshot = _pending_response_snapshot({**records, authorization_id: raw.decode("ascii")})
            if marker is None:
                self._advance_pair(selection, None, wanted)
            if previous is None:
                _commit_pending_response(store, snapshot, current.get("revision"))
            self._require_pending_file_ownership(store)
            persisted = _pending_response_records(store.load())
            self._validate_pending_records(persisted)
            if persisted.get(authorization_id) != raw.decode("ascii"):
                raise RuntimeError("root_pending_response_write_unverified")
            if terminal and current_grant != committed:
                self._advance_pair(authorization_binding(authorization_id), reserved, committed)
            return expected_record_digest

    def load_committed_response_for_root(self, *, expected_binding: VerifiedOutcomeResponseBinding,
        expected_record_digest: str, expected_generation: ProposalReplayHighWater,
        now_epoch: int) -> bytes:
        """Root storage only; the caller must separately authorize any disclosure."""
        with self._lock():
            self._require_installed()
            store = AtomicJsonAuthorityRuntimeStore(
                self._primary.rollback_domain_root / "verified-outcome-pending-responses.json",
                allowed_root=self._primary.rollback_domain_root, repo_root=self._repo_root,
            )
            self._require_pending_file_ownership(store)
            records = _pending_response_records(store.load())
            self._validate_pending_records(records)
            raw = records.get(expected_binding.authorization_id, "").encode("ascii")
            generation, _ = _pending_response_context(raw, expected_binding, expected_record_digest, now_epoch)
            if (type(expected_generation) is not ProposalReplayHighWater
                or type(expected_generation.sequence) is not int or generation != expected_generation
                or self._current(GENERATION_BINDING) != generation
                or self._current(authorization_binding(expected_binding.authorization_id))
                != ProposalReplayHighWater(2, expected_record_digest[7:])):
                raise RuntimeError("root_committed_response_context_conflict")
            return raw

    def _validate_pending_records(self, records: Mapping[str, str]) -> None:
        for authorization_id, text in records.items():
            marker = self._current(pending_response_binding(authorization_id))
            if marker is None or marker.sequence != 1:
                raise ValueError("root_pending_response_selection_missing")
            raw = text.encode("ascii")
            try:
                binding = VerifiedOutcomeResponseBinding(**decode_message(raw)["binding"])
            except (KeyError, TypeError, RecursionError) as exc:
                raise ValueError("root_pending_response_record_invalid") from exc
            if binding.authorization_id != authorization_id:
                raise ValueError("root_pending_response_record_scope_invalid")
            parse_verified_outcome_response_record(
                raw, expected_binding=binding,
                expected_record_digest="sha256:" + marker.state_revision,
                signature_verifier=Ed25519SignatureVerifier(),
            )

    def _require_pending_file_ownership(self, store: AtomicJsonAuthorityRuntimeStore) -> None:
        self._require_current_ownership()
        if self._require_ownership:
            _require_root_files(store.path)

    def advance(
        self,
        binding_digest: str,
        *,
        expected: ProposalReplayHighWater | None,
        next_value: ProposalReplayHighWater,
    ) -> None:
        with self._lock():
            self._require_installed()
            current = self._current(binding_digest)
            if current != expected:
                raise RuntimeError("root_authority_state_conflict")
            self._advance_pair(binding_digest, expected, next_value)

    def acquire_protected_use(
        self,
        *,
        expected_generation: ProposalReplayHighWater,
        revocation_binding: str,
        expected_revocation: ProposalReplayHighWater,
        protected_use_binding: str,
        use_revision: str,
    ) -> ProposalReplayHighWater:
        """Atomically linearize one signer use after exact revocation state."""

        _require_revision(use_revision)
        with self._lock():
            self._require_installed()
            if self._current(GENERATION_BINDING) != expected_generation:
                raise RuntimeError("root_protected_use_generation_conflict")
            if self._current(revocation_binding) != expected_revocation:
                raise RuntimeError("root_protected_use_revocation_conflict")
            marker = self._current(protected_use_binding)
            current = self._current(PROTECTED_USE_BINDING)
            wanted_marker = ProposalReplayHighWater(1, use_revision)
            if marker is not None:
                return self._resume_protected_use(
                    protected_use_binding, use_revision,
                    marker=marker, current=current,
                )
            if current is not None and current.sequence % 2 == 1:
                raise RuntimeError("root_protected_use_active")
            if current is not None and current.sequence % 2 != 0:
                raise RuntimeError("root_protected_use_state_invalid")
            sequence = 1 if current is None else current.sequence + 1
            wanted = ProposalReplayHighWater(sequence, use_revision)
            self._advance_pair(protected_use_binding, None, wanted_marker)
            self._advance_pair(PROTECTED_USE_BINDING, current, wanted)
            self._advance_pair(
                protected_use_binding,
                wanted_marker,
                ProposalReplayHighWater(2, use_revision),
            )
            return wanted

    def _resume_protected_use(
        self, binding: str, revision: str, *,
        marker: ProposalReplayHighWater,
        current: ProposalReplayHighWater | None,
    ) -> ProposalReplayHighWater:
        prepared = ProposalReplayHighWater(1, revision)
        active = ProposalReplayHighWater(2, revision)
        if marker not in {prepared, active}:
            raise RuntimeError("root_protected_use_replay")
        if current is not None and current.sequence % 2 == 1:
            if current.state_revision != revision:
                raise RuntimeError("root_protected_use_active")
            if marker == prepared:
                self._advance_pair(binding, prepared, active)
            return current
        if marker == active:
            raise RuntimeError("root_protected_use_replay")
        sequence = 1 if current is None else current.sequence + 1
        wanted = ProposalReplayHighWater(sequence, revision)
        self._advance_pair(PROTECTED_USE_BINDING, current, wanted)
        self._advance_pair(binding, prepared, active)
        return wanted

    def finish_protected_use(
        self,
        *,
        expected: ProposalReplayHighWater,
        finish_revision: str,
    ) -> ProposalReplayHighWater:
        """Close one exact active use; repeated completion is idempotent."""

        _require_revision(finish_revision)
        with self._lock():
            self._require_installed()
            current = self._current(PROTECTED_USE_BINDING)
            finished = ProposalReplayHighWater(expected.sequence + 1, finish_revision)
            if current == finished:
                return current
            if current != expected or expected.sequence % 2 != 1:
                raise RuntimeError("root_protected_use_finish_conflict")
            self._advance_pair(PROTECTED_USE_BINDING, expected, finished)
            return finished

    def advance_revocation(
        self,
        binding_digest: str,
        *,
        expected: ProposalReplayHighWater | None,
        next_value: ProposalReplayHighWater,
    ) -> None:
        """Advance revocation only when no protected signing use is active."""

        with self._lock():
            self._require_installed()
            active = self._current(PROTECTED_USE_BINDING)
            if active is not None and active.sequence % 2 == 1:
                raise RuntimeError("root_protected_use_active")
            if self._current(binding_digest) != expected:
                raise RuntimeError("root_authority_state_conflict")
            self._advance_pair(binding_digest, expected, next_value)

    def observe_generation(self, sequence: int, owner_config_id: str) -> None:
        if type(sequence) is not int or sequence < 1 or not _sha256(owner_config_id):
            raise ValueError("root_authority_generation_invalid")
        wanted = ProposalReplayHighWater(sequence, owner_config_id[7:])
        with self._lock():
            self._require_installed()
            current = self._current(GENERATION_BINDING)
            if current == wanted:
                return
            expected_sequence = 1 if current is None else current.sequence + 1
            if sequence != expected_sequence:
                raise ValueError("root_authority_generation_rollback")
            self._advance_pair(GENERATION_BINDING, current, wanted)

    def initialize(
        self,
        *,
        generation: ProposalReplayHighWater,
        replay_binding: str,
        replay_anchor: ProposalReplayHighWater,
        installation_revision: str,
    ) -> None:
        """Provision once; a committed third-domain witness forbids reset."""

        prepared = ProposalReplayHighWater(1, installation_revision)
        committed = ProposalReplayHighWater(2, installation_revision)
        with self._lock():
            self._require_current_ownership()
            marker = self._installation.load(INSTALLATION_BINDING)
            if marker == committed:
                raise ValueError("root_authority_state_already_initialized")
            if marker is None:
                if any(
                    value is not None
                    for value in (
                        self._primary.load(GENERATION_BINDING),
                        self._witness.load(GENERATION_BINDING),
                        self._primary.load(replay_binding),
                        self._witness.load(replay_binding),
                    )
                ):
                    raise ValueError("root_authority_state_preexisting_data")
                self._installation.advance(
                    INSTALLATION_BINDING,
                    expected=None,
                    next_value=prepared,
                )
            elif marker != prepared:
                raise ValueError("root_authority_installation_conflict")
            self._ensure_pair(GENERATION_BINDING, generation)
            self._ensure_pair(replay_binding, replay_anchor)
            self._installation.advance(
                INSTALLATION_BINDING,
                expected=prepared,
                next_value=committed,
            )

    def _current(self, binding: str) -> ProposalReplayHighWater | None:
        self._require_current_ownership()
        primary = self._primary.load(binding)
        witness = self._witness.load(binding)
        if primary == witness:
            return primary
        if primary is None and witness is not None:
            self._primary.restore_missing_from_witness(
                binding, witness=self._witness.reader(), expected=witness,
            )
            return witness
        if witness is None and primary is not None:
            self._witness.restore_missing_from_witness(
                binding, witness=self._primary.reader(), expected=primary,
            )
            return primary
        if primary is not None and witness is not None:
            if primary.sequence == witness.sequence + 1:
                self._witness.advance(binding, expected=witness, next_value=primary)
                return primary
            if witness.sequence == primary.sequence + 1:
                self._primary.advance(binding, expected=primary, next_value=witness)
                return witness
        raise RuntimeError("root_authority_state_witness_mismatch")

    def _advance_pair(
        self,
        binding: str,
        expected: ProposalReplayHighWater | None,
        next_value: ProposalReplayHighWater,
    ) -> None:
        self._require_current_ownership()
        self._primary.advance(binding, expected=expected, next_value=next_value)
        try:
            self._witness.advance(binding, expected=expected, next_value=next_value)
        except Exception:
            if self._witness.load(binding) != next_value:
                raise
        if self._current(binding) != next_value:
            raise RuntimeError("root_authority_state_commit_unverified")

    def _ensure_pair(
        self, binding: str, wanted: ProposalReplayHighWater
    ) -> None:
        current = self._current(binding)
        if current is None:
            self._advance_pair(binding, None, wanted)
        elif current != wanted:
            raise ValueError("root_authority_installation_state_conflict")

    def _require_installed(self) -> None:
        marker = self._installation.load(INSTALLATION_BINDING)
        if marker is None or marker.sequence != 2:
            raise ValueError("root_authority_state_not_initialized")

    def _require_current_ownership(self) -> None:
        if not self._require_ownership:
            return
        _require_root_owned(
            self._primary.rollback_domain_root,
            self._witness.rollback_domain_root,
            self._installation.rollback_domain_root,
        )
        _require_root_files(
            self._primary.path,
            self._witness.path,
            self._installation.path,
        )

    def _lock(self):
        return confined_runtime_operation_lock(
            self._lock_path,
            repo_root=self._repo_root,
            allowed_root=self._primary.rollback_domain_root,
        )


def _pending_response_context(raw, binding, record_digest, now_epoch):
    request, _response = parse_verified_outcome_response_record(
        raw, expected_binding=binding, expected_record_digest=record_digest,
        signature_verifier=Ed25519SignatureVerifier(),
    )
    descriptor = validate_root_verified_outcome_descriptor_public(
        decode_message(raw)["authority_descriptor"], now_epoch=now_epoch,
    )
    payload = json.loads(request.signing_input[len(VERIFIED_OUTCOME_SIGNING_PREFIX):])
    reservation = {
        **asdict(binding), "receipt_id": payload["receipt_id"],
        "work_order_id": payload["work_order_id"],
        "evidence_digest": payload["covered_action_digest"], "issued_at": payload["issued_at"],
    }
    return (
        ProposalReplayHighWater(descriptor["authority_generation_sequence"], binding.owner_config_id[7:]),
        ProposalReplayHighWater(1, state_revision(reservation)),
    )


def _commit_pending_response(store, snapshot, expected_revision):
    try:
        store.commit(snapshot, expected_revision=expected_revision)
    except (OSError, RuntimeError, ValueError):
        if _pending_response_records(store.load()) != snapshot["records"]:
            raise


def pending_response_binding(authorization_id: str) -> str:
    return "sha256:" + state_revision({
        "schema_version": PENDING_RESPONSE_SCHEMA,
        "authorization_binding": authorization_binding(authorization_id),
    })


def state_revision(value: Mapping[str, Any]) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def authorization_binding(authorization_id: str) -> str:
    if not isinstance(authorization_id, str) or not authorization_id.isascii():
        raise ValueError("root_authority_authorization_id_invalid")
    return "sha256:" + hashlib.sha256(
        ("foundup-verified-outcome:" + authorization_id).encode("ascii")
    ).hexdigest()


def root_authority_state_binding_digest(
    values: Mapping[str, Mapping[str, object]],
) -> str:
    """Bind the exact three-store identity used by one running service."""

    if set(values) != set(_STATE_BINDING_NAMES):
        raise ValueError("root_authority_state_binding_invalid")
    normalized: dict[str, dict[str, str]] = {}
    for name in _STATE_BINDING_NAMES:
        item = values[name]
        if not isinstance(item, Mapping) or set(item) != set(_STATE_BINDING_FIELDS):
            raise ValueError("root_authority_state_binding_invalid")
        root = Path(str(item["root"])).resolve()
        path = Path(str(item["path"])).resolve()
        store_id = str(item["store_id"])
        receipt_id = str(item["durability_receipt_id"])
        if path.parent != root or not store_id or not store_id.isascii() or not _sha256(receipt_id):
            raise ValueError("root_authority_state_binding_invalid")
        normalized[name] = {
            "root": str(root),
            "path": str(path),
            "store_id": store_id,
            "durability_receipt_id": receipt_id,
        }
    return "sha256:" + state_revision(
        {"schema_version": "root_authority_state_binding.v1", "stores": normalized}
    )


def _store_binding(store: SqliteMonotonicAuthorityStore) -> dict[str, object]:
    return {
        "root": store.rollback_domain_root,
        "path": store.path,
        "store_id": store.store_id,
        "durability_receipt_id": store.durability_receipt_id,
    }


def validate_root_authority_state_paths(
    *roots: Path | str,
    files: tuple[Path | str, ...] = (),
) -> None:
    """Authenticate immutable root-owned ancestry before SQLite opens."""

    resolved_roots = tuple(Path(item).resolve() for item in roots)
    _require_root_owned(*resolved_roots)
    _require_root_files(*(Path(item).resolve() for item in files))


def _require_root_owned(*roots: Path) -> None:
    if os.name != "posix" or not hasattr(os, "geteuid") or os.geteuid() != 0:
        raise ValueError("root_authority_service_principal_invalid")
    checked: set[Path] = set()
    for root in roots:
        for directory in (root, *root.parents):
            if directory in checked:
                continue
            checked.add(directory)
            _require_root_directory(directory)


def _require_root_directory(root: Path) -> None:
    try:
        metadata = root.lstat()
    except OSError as exc:
        raise ValueError("root_authority_state_root_invalid") from exc
    if (
        root.is_symlink()
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != 0
        or stat.S_IMODE(metadata.st_mode) & 0o022
    ):
        raise ValueError("root_authority_state_root_invalid")


def _require_root_files(*paths: Path) -> None:
    for path in paths:
        if not path.exists():
            continue
        metadata = path.lstat()
        if (
            path.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != 0
            or stat.S_IMODE(metadata.st_mode) & 0o022
        ):
            raise ValueError("root_authority_state_file_invalid")


def _overlap(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents


def _sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


def _require_revision(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError("root_protected_use_revision_invalid")


__all__ = [
    "GENERATION_BINDING",
    "INSTALLATION_BINDING",
    "PROTECTED_USE_BINDING",
    "PENDING_RESPONSE_SCHEMA",
    "MAX_PENDING_RESPONSE_RECORDS",
    "MAX_PENDING_RESPONSE_STORE_BYTES",
    "RootVerifiedOutcomeAuthorityState",
    "authorization_binding",
    "pending_response_binding",
    "root_authority_state_binding_digest",
    "state_revision",
    "validate_root_authority_state_paths",
]
