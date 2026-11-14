"""Serialized private route CAS with deterministic crash rollback."""

from __future__ import annotations

import hmac
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterator

from modules.infrastructure.shared_utilities.runtime_atomic_replace import (
    atomic_replace_runtime_text,
)

from .reddog_holoindex_acceptance_guards import (
    _normalized,
    _reject_link_components,
    _reject_overlap,
    _relative_to,
    _same_path,
)
from .reddog_holoindex_query_route_contract import (
    JOURNAL_SCHEMA_VERSION,
    QueryRouteJournal,
    QueryRouteRecord,
    QueryRouteStateProof,
    empty_route_record,
    prove_route_record,
)
from .reddog_holoindex_query_route_io import (
    QueryRouteRuntimeIO,
    QueryRouteStoreError,
)


def _fail(code: str) -> None:
    raise QueryRouteStoreError(code)


@dataclass
class QueryRouteTransition:
    """One selected route held under the store's machine-wide lock."""

    _store: "QueryRouteStore"
    previous: QueryRouteStateProof
    candidate: QueryRouteStateProof
    journal: QueryRouteJournal
    committed: bool = False
    rollback_proven: bool = False
    _commit_requested: bool = False
    _closed: bool = False

    def commit(self) -> None:
        if self._closed or self._commit_requested:
            _fail("QUERY_ROUTE_TRANSITION_INVALID")
        self._commit_requested = True


def _admit_transition(
    current: QueryRouteStateProof, candidate: QueryRouteStateProof,
    expected_revision: int, expected_digest: str,
) -> None:
    if type(expected_revision) is not int or type(expected_digest) is not str:
        _fail("QUERY_ROUTE_CAS_EXPECTATION_INVALID")
    if current.record.revision != expected_revision or not hmac.compare_digest(
        current.digest, expected_digest
    ):
        _fail("QUERY_ROUTE_CAS_MISMATCH")
    if candidate.record.status != "CURRENT":
        _fail("QUERY_ROUTE_CANDIDATE_INVALID")
    if candidate.record.revision != current.record.revision + 1:
        _fail("QUERY_ROUTE_REVISION_SEQUENCE_INVALID")
    if not hmac.compare_digest(candidate.record.previous_route_digest, current.digest):
        _fail("QUERY_ROUTE_PREVIOUS_DIGEST_MISMATCH")


def _validate_selected_paths(
    record: QueryRouteRecord, *, canonical_store: Path,
    repo_roots: tuple[Path, ...], runtime_root: Path,
) -> None:
    if record.status == "EMPTY":
        return
    authority = _normalized(record.authority_repo_root)
    replica = _normalized(record.replica_root)
    if str(authority) != record.authority_repo_root or str(replica) != record.replica_root:
        _fail("QUERY_ROUTE_SELECTED_ROOT_INVALID")
    for path in (authority, replica):
        _reject_link_components(path)
        if not path.is_dir():
            _fail("QUERY_ROUTE_SELECTED_ROOT_INVALID")
    if _same_path(authority, replica):
        _fail("QUERY_ROUTE_SELECTED_ROOT_INVALID")
    if _relative_to(authority, replica) or _relative_to(replica, authority):
        _fail("QUERY_ROUTE_SELECTED_ROOT_INVALID")
    _reject_overlap(replica, (canonical_store, *repo_roots, runtime_root))
    _reject_overlap(authority, (canonical_store, runtime_root))


def _journal(
    status: str, previous: QueryRouteStateProof,
    candidate: QueryRouteStateProof,
) -> QueryRouteJournal:
    return QueryRouteJournal(
        JOURNAL_SCHEMA_VERSION, status, candidate.record.activation_id,
        previous.digest, candidate.digest, previous.record, candidate.record,
    )


def _admit_unjournaled_state(current: QueryRouteStateProof) -> None:
    if current.record.status != "EMPTY":
        _fail("QUERY_ROUTE_JOURNAL_REQUIRED")


class QueryRouteStore:
    """Private stable-route file with revision+digest CAS and recovery journal."""

    def __init__(
        self, route_path: Path | str, *, runtime_root: Path | str,
        canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
        lock_timeout_seconds: float = 300.0,
        create_runtime_root: bool = True,
    ) -> None:
        self._io = QueryRouteRuntimeIO(
            route_path, runtime_root=runtime_root, canonical_store=canonical_store,
            repo_roots=repo_roots, lock_timeout_seconds=lock_timeout_seconds,
            replace_text=lambda path, text: atomic_replace_runtime_text(path, text),
            create_runtime_root=create_runtime_root,
        )
        self.repo_roots = self._io.repo_roots
        self.canonical_store = self._io.canonical_store
        self.runtime_root = self._io.runtime_root
        self.route_path = self._io.route_path
        self.journal_path = self._io.journal_path
        self.lock_path = self._io.lock_path
        self.lock_timeout_seconds = self._io.lock_timeout_seconds

    def initialize_empty(self) -> QueryRouteStateProof:
        """No-replace initialize the stable route; existing valid state is idempotent."""

        with self._lock():
            if self.route_path.exists():
                return self._recover_and_load()
            if self.journal_path.exists():
                _fail("QUERY_ROUTE_ROLLBACK_UNPROVEN")
            payload = prove_route_record(empty_route_record())
            self._io.publish_initial(payload)
            return self._read_route_required()

    def load(self) -> QueryRouteStateProof:
        with self._lock():
            return self._recover_and_load()

    def load_readonly(self) -> QueryRouteStateProof:
        """Read one terminal route state without crash recovery or publication."""

        with self._lock():
            journal = self._read_journal()
            current = self._read_route_required(validate_selected=False)
            if journal is None:
                _admit_unjournaled_state(current)
                self._validate_selected(current.record)
                return current
            if journal.status == "PREPARED":
                _fail("QUERY_ROUTE_TRANSITION_PENDING")
            expected = (
                journal.candidate_route_digest
                if journal.status == "COMMITTED"
                else journal.previous_route_digest
            )
            if not hmac.compare_digest(current.digest, expected):
                _fail("QUERY_ROUTE_JOURNAL_STATE_MISMATCH")
            self._validate_selected(current.record)
            return current

    @contextmanager
    def transition(
        self, candidate: QueryRouteRecord, *, expected_revision: int,
        expected_route_digest: str,
    ) -> Iterator[QueryRouteTransition]:
        candidate_proof = prove_route_record(candidate)
        self._validate_selected(candidate_proof.record)
        with self._lock():
            current = self._recover_and_load()
            self._validate_selected(candidate_proof.record)
            _admit_transition(
                current, candidate_proof, expected_revision, expected_route_digest
            )
            journal = _journal("PREPARED", current, candidate_proof)
            self._write_journal(journal)
            transition = QueryRouteTransition(self, current, candidate_proof, journal)
            try:
                self._write_route(candidate_proof)
            except BaseException as cause:
                self._rollback_transition(transition, cause=cause)
                raise
            try:
                yield transition
            except BaseException as cause:
                self._rollback_transition(transition, cause=cause)
                raise
            if transition._commit_requested:
                try:
                    self._commit_transition(transition)
                except BaseException as cause:
                    self._rollback_transition(transition, cause=cause)
                    raise
            else:
                self._rollback_transition(transition)

    def _lock(self):
        return self._io.lock()

    def _read_route_required(
        self, *, validate_selected: bool = True,
    ) -> QueryRouteStateProof:
        state = self._io.read_route()
        if validate_selected:
            self._validate_selected(state.record)
        return state

    def _read_journal(self) -> QueryRouteJournal | None:
        return self._io.read_journal()

    def _recover_and_load(self) -> QueryRouteStateProof:
        journal = self._read_journal()
        try:
            current = self._read_route_required(validate_selected=False)
        except QueryRouteStoreError:
            if journal is not None and journal.status == "PREPARED":
                _fail("QUERY_ROUTE_ROLLBACK_UNPROVEN")
            raise
        if journal is None:
            _admit_unjournaled_state(current)
            self._validate_selected(current.record)
            return current
        expected = (
            journal.candidate_route_digest
            if journal.status == "COMMITTED" else journal.previous_route_digest
        )
        if journal.status != "PREPARED":
            if not hmac.compare_digest(current.digest, expected):
                _fail("QUERY_ROUTE_JOURNAL_STATE_MISMATCH")
            self._validate_selected(current.record)
            return current
        transition = QueryRouteTransition(
            self, prove_route_record(journal.previous_record),
            prove_route_record(journal.candidate_record), journal,
        )
        self._rollback_transition(transition)
        return self._read_route_required()

    def _validate_selected(self, record: QueryRouteRecord) -> None:
        _validate_selected_paths(
            record, canonical_store=self.canonical_store,
            repo_roots=self.repo_roots, runtime_root=self.runtime_root,
        )

    def _write_route(
        self, proof: QueryRouteStateProof, *, validate_selected: bool = True,
    ) -> None:
        observed = self._io.write_route(proof)
        if validate_selected:
            self._validate_selected(observed.record)

    def _write_journal(self, journal: QueryRouteJournal) -> None:
        self._io.write_journal(journal)

    def _rollback_transition(
        self, transition: QueryRouteTransition, *, cause: BaseException | None = None,
    ) -> None:
        if transition._closed:
            return
        try:
            current = self._read_route_required(validate_selected=False)
            if hmac.compare_digest(current.digest, transition.candidate.digest):
                self._write_route(transition.previous, validate_selected=False)
            elif not hmac.compare_digest(current.digest, transition.previous.digest):
                _fail("QUERY_ROUTE_ROLLBACK_UNPROVEN")
            rolled_back = replace(transition.journal, status="ROLLED_BACK")
            self._write_journal(rolled_back)
            transition.rollback_proven = True
            transition._closed = True
        except BaseException as rollback_error:
            error = QueryRouteStoreError("QUERY_ROUTE_ROLLBACK_UNPROVEN")
            error.__cause__ = rollback_error if cause is None else cause
            raise error

    def _commit_transition(self, transition: QueryRouteTransition) -> None:
        if transition._store is not self or transition._closed:
            _fail("QUERY_ROUTE_TRANSITION_INVALID")
        current = self._read_route_required()
        if not hmac.compare_digest(current.digest, transition.candidate.digest):
            _fail("QUERY_ROUTE_SELECTED_STATE_CHANGED")
        self._write_journal(replace(transition.journal, status="COMMITTED"))
        transition.committed = True
        transition._closed = True

__all__ = [
    "QueryRouteStore", "QueryRouteStoreError", "QueryRouteTransition",
]
