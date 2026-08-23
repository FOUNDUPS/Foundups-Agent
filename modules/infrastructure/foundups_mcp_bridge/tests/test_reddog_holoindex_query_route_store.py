from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_query_route_store as route_store_module,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_route_contract import (
    JOURNAL_SCHEMA_VERSION,
    QueryRouteJournal,
    encode_route_journal,
    empty_route_record,
    parse_route_journal_bytes,
    prove_route_record,
    route_record_from_mapping,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_route_store import (
    QueryRouteStore,
    QueryRouteStoreError,
)
from modules.infrastructure.shared_utilities.runtime_atomic_replace import (
    atomic_replace_runtime_text,
)


def _digest(character: str) -> str:
    return "sha256:" + character * 64


_DIGEST_9 = "sha256:9999999999999999999999999999999999999999999999999999999999999999"


def _file_state(path: Path) -> tuple[int, int, int, int, int, int]:
    metadata = os.lstat(path)
    return (
        int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_mode),
        int(metadata.st_nlink), int(metadata.st_size), int(metadata.st_mtime_ns),
    )


def _tree(tmp_path: Path):
    repo = tmp_path / "repo"
    canonical = tmp_path / "canonical"
    runtime = tmp_path / "runtime"
    replica_a = tmp_path / "replica-a"
    replica_b = tmp_path / "replica-b"
    for path in (repo, canonical, replica_a, replica_b):
        path.mkdir()
    route = runtime / "active-route.json"
    store = QueryRouteStore(
        route, runtime_root=runtime, canonical_store=canonical,
        repo_roots=(repo,), lock_timeout_seconds=5.0,
    )
    return store, repo, canonical, runtime, replica_a, replica_b


def _candidate(
    authority: Path, replica: Path, previous_digest: str, *, revision: int = 1,
    activation: str = "a",
):
    return route_record_from_mapping({
        "schema_version": "reddog_holoindex_query_route.v1",
        "status": "CURRENT",
        "revision": revision,
        "activation_id": _digest(activation),
        "previous_route_digest": previous_digest,
        "activated_at": "2026-08-23T00:00:00Z",
        "authority_repo_root": str(authority),
        "replica_root": str(replica),
        "canonical": {
            "repo_head_sha": "b" * 40,
            "repo_root_digest": _digest("c"),
            "generation_id": _digest("d"),
            "receipt_digest": _digest("e"),
        },
        "replica": {
            "query_replica_descriptor_digest": _digest("f"),
            "query_replica_generation_id": _digest("d"),
            "query_replica_id": _digest("1"),
            "query_replica_path_identity_digest": _digest("2"),
        },
    })


def _prepared(previous, candidate):
    return QueryRouteJournal(
        JOURNAL_SCHEMA_VERSION, "PREPARED", candidate.record.activation_id,
        previous.digest, candidate.digest, previous.record, candidate.record,
    )


def test_initialize_is_no_replace_idempotent_and_private(tmp_path: Path) -> None:
    store, *_rest = _tree(tmp_path)
    first = store.initialize_empty()
    second = store.initialize_empty()
    assert first == second == store.load()
    assert first.record == empty_route_record()
    if os.name != "nt":
        assert os.stat(store.route_path).st_mode & 0o077 == 0


def test_commit_advances_exact_revision_and_digest(tmp_path: Path) -> None:
    store, repo, _canonical, _runtime, replica, _other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidate = _candidate(repo, replica, previous.digest)
    with store.transition(
        candidate, expected_revision=0, expected_route_digest=previous.digest
    ) as transition:
        assert store._read_route_required().record == candidate
        transition.commit()
    current = store.load()
    assert current.record == candidate
    journal = parse_route_journal_bytes(store.journal_path.read_bytes())
    assert journal.status == "COMMITTED"


def test_exit_without_commit_and_exception_both_rollback(tmp_path: Path) -> None:
    store, repo, _canonical, _runtime, replica, other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidate = _candidate(repo, replica, previous.digest)
    with store.transition(candidate, expected_revision=0, expected_route_digest=previous.digest):
        pass
    assert store.load().digest == previous.digest
    journal = parse_route_journal_bytes(store.journal_path.read_bytes())
    assert journal.status == "ROLLED_BACK"
    second = _candidate(repo, other, previous.digest, activation="3")
    with pytest.raises(RuntimeError, match="canary_failed"):
        with store.transition(second, expected_revision=0, expected_route_digest=previous.digest):
            raise RuntimeError("canary_failed")
    assert store.load().digest == previous.digest


def test_exception_after_commit_request_still_rolls_back(tmp_path: Path) -> None:
    store, repo, _canonical, _runtime, replica, _other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidate = _candidate(repo, replica, previous.digest)
    with pytest.raises(RuntimeError, match="late_failure"):
        with store.transition(
            candidate, expected_revision=0, expected_route_digest=previous.digest
        ) as transition:
            transition.commit()
            raise RuntimeError("late_failure")
    assert store.load().digest == previous.digest
    assert parse_route_journal_bytes(store.journal_path.read_bytes()).status == "ROLLED_BACK"


@pytest.mark.parametrize(
    ("revision", "digest"), [(1, None), (0, _DIGEST_9), (True, None)],
)
def test_stale_or_hostile_cas_expectation_fails_before_route_swap(
    tmp_path: Path, revision: object, digest: str | None,
) -> None:
    store, repo, _canonical, _runtime, replica, _other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidate = _candidate(repo, replica, previous.digest)
    with pytest.raises(QueryRouteStoreError):
        with store.transition(
            candidate, expected_revision=revision,
            expected_route_digest=digest or previous.digest,
        ):
            pass
    assert store.load().digest == previous.digest


def test_candidate_sequence_and_selected_paths_fail_closed(tmp_path: Path) -> None:
    store, repo, _canonical, _runtime, replica, _other = _tree(tmp_path)
    previous = store.initialize_empty()
    wrong_revision = _candidate(repo, replica, previous.digest, revision=2)
    with pytest.raises(QueryRouteStoreError, match="REVISION_SEQUENCE"):
        with store.transition(wrong_revision, expected_revision=0, expected_route_digest=previous.digest):
            pass
    missing = _candidate(repo, tmp_path / "missing", previous.digest)
    with pytest.raises(QueryRouteStoreError, match="SELECTED_ROOT_INVALID"):
        with store.transition(missing, expected_revision=0, expected_route_digest=previous.digest):
            pass
    aliased = _candidate(repo, replica / ".." / replica.name, previous.digest)
    with pytest.raises(QueryRouteStoreError, match="SELECTED_ROOT_INVALID"):
        with store.transition(aliased, expected_revision=0, expected_route_digest=previous.digest):
            pass


@pytest.mark.parametrize("swap_before_recovery", [False, True])
def test_prepared_crash_recovers_previous_route(
    tmp_path: Path, swap_before_recovery: bool,
) -> None:
    store, repo, _canonical, _runtime, replica, _other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidate = prove_route_record(_candidate(repo, replica, previous.digest))
    journal = _prepared(previous, candidate)
    atomic_replace_runtime_text(store.journal_path, encode_route_journal(journal).decode("ascii"))
    if swap_before_recovery:
        atomic_replace_runtime_text(store.route_path, candidate.encoded.decode("ascii"))
    recovered = store.load()
    assert recovered.digest == previous.digest
    assert parse_route_journal_bytes(store.journal_path.read_bytes()).status == "ROLLED_BACK"


@pytest.mark.parametrize("use_candidate", [False, True])
def test_readonly_load_rejects_both_prepared_windows_without_mutation(
    tmp_path: Path, use_candidate: bool,
) -> None:
    store, repo, _canonical, _runtime, replica, _other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidate = prove_route_record(_candidate(repo, replica, previous.digest))
    journal = _prepared(previous, candidate)
    atomic_replace_runtime_text(
        store.journal_path, encode_route_journal(journal).decode("ascii")
    )
    if use_candidate:
        atomic_replace_runtime_text(store.route_path, candidate.encoded.decode("ascii"))
    before_route = store.route_path.read_bytes()
    before_journal = store.journal_path.read_bytes()
    before_identities = (_file_state(store.route_path), _file_state(store.journal_path))

    with pytest.raises(QueryRouteStoreError, match="QUERY_ROUTE_TRANSITION_PENDING"):
        store.load_readonly()

    assert store.route_path.read_bytes() == before_route
    assert store.journal_path.read_bytes() == before_journal
    assert (_file_state(store.route_path), _file_state(store.journal_path)) == before_identities


def test_readonly_load_accepts_only_empty_no_journal_state_without_mutation(
    tmp_path: Path,
) -> None:
    store, _repo, _canonical, _runtime, _replica, _other = _tree(tmp_path)
    previous = store.initialize_empty()
    before = (store.route_path.read_bytes(), _file_state(store.route_path))
    assert store.load_readonly().digest == previous.digest
    assert (store.route_path.read_bytes(), _file_state(store.route_path)) == before


@pytest.mark.parametrize("readonly", [False, True])
def test_current_without_journal_is_rejected_and_preserved(
    tmp_path: Path, readonly: bool,
) -> None:
    store, repo, _canonical, _runtime, replica, _other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidate = prove_route_record(_candidate(repo, replica, previous.digest))
    atomic_replace_runtime_text(store.route_path, candidate.encoded.decode("ascii"))
    before = (store.route_path.read_bytes(), _file_state(store.route_path))

    load = store.load_readonly if readonly else store.load
    with pytest.raises(QueryRouteStoreError, match="QUERY_ROUTE_JOURNAL_REQUIRED"):
        load()

    assert (store.route_path.read_bytes(), _file_state(store.route_path)) == before
    assert not store.journal_path.exists()


@pytest.mark.parametrize("status,use_candidate", [("COMMITTED", True), ("ROLLED_BACK", False)])
def test_readonly_load_accepts_only_digest_bound_terminal_state_without_mutation(
    tmp_path: Path, status: str, use_candidate: bool,
) -> None:
    store, repo, _canonical, _runtime, replica, _other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidate = prove_route_record(_candidate(repo, replica, previous.digest))
    prepared = _prepared(previous, candidate)
    journal = QueryRouteJournal(
        prepared.schema_version, status, prepared.transition_id,
        prepared.previous_route_digest, prepared.candidate_route_digest,
        prepared.previous_record, prepared.candidate_record,
    )
    selected = candidate if use_candidate else previous
    atomic_replace_runtime_text(
        store.journal_path, encode_route_journal(journal).decode("ascii")
    )
    atomic_replace_runtime_text(store.route_path, selected.encoded.decode("ascii"))
    before_route = store.route_path.read_bytes()
    before_journal = store.journal_path.read_bytes()
    before_identities = (_file_state(store.route_path), _file_state(store.journal_path))

    assert store.load_readonly().digest == selected.digest
    assert store.route_path.read_bytes() == before_route
    assert store.journal_path.read_bytes() == before_journal
    assert (_file_state(store.route_path), _file_state(store.journal_path)) == before_identities


def test_readonly_load_rejects_terminal_digest_mismatch_without_mutation(
    tmp_path: Path,
) -> None:
    store, repo, _canonical, _runtime, replica, _other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidate = prove_route_record(_candidate(repo, replica, previous.digest))
    prepared = _prepared(previous, candidate)
    committed = QueryRouteJournal(
        prepared.schema_version, "COMMITTED", prepared.transition_id,
        prepared.previous_route_digest, prepared.candidate_route_digest,
        prepared.previous_record, prepared.candidate_record,
    )
    atomic_replace_runtime_text(
        store.journal_path, encode_route_journal(committed).decode("ascii")
    )
    before = (
        store.route_path.read_bytes(), store.journal_path.read_bytes(),
        _file_state(store.route_path), _file_state(store.journal_path),
    )
    with pytest.raises(QueryRouteStoreError, match="JOURNAL_STATE_MISMATCH"):
        store.load_readonly()
    assert (
        store.route_path.read_bytes(), store.journal_path.read_bytes(),
        _file_state(store.route_path), _file_state(store.journal_path),
    ) == before


def test_readonly_load_rejects_unknown_journal_without_mutation(tmp_path: Path) -> None:
    store, repo, _canonical, _runtime, replica, _other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidate = prove_route_record(_candidate(repo, replica, previous.digest))
    payload = encode_route_journal(_prepared(previous, candidate)).replace(
        b'"PREPARED"', b'"UNKNOWN"'
    )
    atomic_replace_runtime_text(store.journal_path, payload.decode("ascii"))
    before = (
        store.route_path.read_bytes(), store.journal_path.read_bytes(),
        _file_state(store.route_path), _file_state(store.journal_path),
    )
    with pytest.raises(QueryRouteStoreError, match="JOURNAL_INVALID"):
        store.load_readonly()
    assert (
        store.route_path.read_bytes(), store.journal_path.read_bytes(),
        _file_state(store.route_path), _file_state(store.journal_path),
    ) == before


def test_prepared_unknown_route_is_terminal_and_preserved(tmp_path: Path) -> None:
    store, repo, _canonical, _runtime, replica, other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidate = prove_route_record(_candidate(repo, replica, previous.digest))
    unknown = prove_route_record(_candidate(repo, other, previous.digest, activation="3"))
    atomic_replace_runtime_text(
        store.journal_path, encode_route_journal(_prepared(previous, candidate)).decode("ascii")
    )
    atomic_replace_runtime_text(store.route_path, unknown.encoded.decode("ascii"))
    with pytest.raises(QueryRouteStoreError, match="ROLLBACK_UNPROVEN"):
        store.load()
    assert store.route_path.read_bytes() == unknown.encoded


def test_prepared_candidate_with_missing_root_restores_previous(tmp_path: Path) -> None:
    store, repo, _canonical, _runtime, replica, _other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidate = prove_route_record(_candidate(repo, replica, previous.digest))
    atomic_replace_runtime_text(
        store.journal_path, encode_route_journal(_prepared(previous, candidate)).decode("ascii")
    )
    atomic_replace_runtime_text(store.route_path, candidate.encoded.decode("ascii"))
    replica.rmdir()
    recovered = store.load()
    assert recovered.digest == previous.digest
    assert parse_route_journal_bytes(store.journal_path.read_bytes()).status == "ROLLED_BACK"


def test_candidate_disappearing_after_swap_rolls_back_before_yield(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, repo, _canonical, _runtime, replica, _other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidate = _candidate(repo, replica, previous.digest)
    original = route_store_module.atomic_replace_runtime_text

    def remove_after_candidate_swap(path: Path, text: str) -> None:
        original(path, text)
        if path == store.route_path and '"status":"CURRENT"' in text:
            replica.rmdir()

    monkeypatch.setattr(
        route_store_module, "atomic_replace_runtime_text", remove_after_candidate_swap
    )
    with pytest.raises(QueryRouteStoreError, match="SELECTED_ROOT_INVALID"):
        with store.transition(candidate, expected_revision=0, expected_route_digest=previous.digest):
            pytest.fail("candidate must not be yielded")
    monkeypatch.setattr(route_store_module, "atomic_replace_runtime_text", original)
    assert store.load().digest == previous.digest
    assert parse_route_journal_bytes(store.journal_path.read_bytes()).status == "ROLLED_BACK"


def test_candidate_is_revalidated_inside_activation_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, repo, _canonical, _runtime, replica, _other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidate = _candidate(repo, replica, previous.digest)
    original_lock = store._lock

    @contextmanager
    def removing_lock():
        with original_lock():
            replica.rmdir()
            yield

    monkeypatch.setattr(store, "_lock", removing_lock)
    with pytest.raises(QueryRouteStoreError, match="SELECTED_ROOT_INVALID"):
        with store.transition(candidate, expected_revision=0, expected_route_digest=previous.digest):
            pytest.fail("candidate must not be yielded")
    assert store.route_path.read_bytes() == previous.encoded
    assert not store.journal_path.exists()


def test_atomic_swap_failure_is_recovered_on_next_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, repo, _canonical, _runtime, replica, _other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidate = _candidate(repo, replica, previous.digest)
    original = route_store_module.atomic_replace_runtime_text

    def fail_route(path: Path, text: str) -> None:
        if path == store.route_path:
            raise OSError("replace failed")
        original(path, text)

    monkeypatch.setattr(route_store_module, "atomic_replace_runtime_text", fail_route)
    with pytest.raises(QueryRouteStoreError, match="ATOMIC_REPLACE_FAILED"):
        with store.transition(candidate, expected_revision=0, expected_route_digest=previous.digest):
            pass
    monkeypatch.setattr(route_store_module, "atomic_replace_runtime_text", original)
    assert store.load().digest == previous.digest


def test_rollback_failure_is_terminal_then_recoverable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, repo, _canonical, _runtime, replica, _other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidate = _candidate(repo, replica, previous.digest)
    original = route_store_module.atomic_replace_runtime_text
    armed = False

    def fail_rollback(path: Path, text: str) -> None:
        if armed and path == store.route_path:
            raise OSError("rollback failed")
        original(path, text)

    monkeypatch.setattr(route_store_module, "atomic_replace_runtime_text", fail_rollback)
    with pytest.raises(QueryRouteStoreError, match="ROLLBACK_UNPROVEN"):
        with store.transition(candidate, expected_revision=0, expected_route_digest=previous.digest):
            armed = True
            raise RuntimeError("post-route failed")
    monkeypatch.setattr(route_store_module, "atomic_replace_runtime_text", original)
    assert store.load().digest == previous.digest


def test_two_concurrent_activators_have_one_winner(tmp_path: Path) -> None:
    store, repo, _canonical, _runtime, replica, other = _tree(tmp_path)
    previous = store.initialize_empty()
    candidates = (
        _candidate(repo, replica, previous.digest, activation="3"),
        _candidate(repo, other, previous.digest, activation="4"),
    )
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def worker(candidate) -> None:
        barrier.wait()
        try:
            with store.transition(candidate, expected_revision=0, expected_route_digest=previous.digest) as tx:
                tx.commit()
            outcomes.append("committed")
        except QueryRouteStoreError as exc:
            outcomes.append(str(exc))

    threads = [threading.Thread(target=worker, args=(item,)) for item in candidates]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert not any(thread.is_alive() for thread in threads)
    assert outcomes.count("committed") == 1
    assert outcomes.count("QUERY_ROUTE_CAS_MISMATCH") == 1


def test_route_link_or_junction_is_rejected(tmp_path: Path) -> None:
    store, *_rest = _tree(tmp_path)
    store.runtime_root.mkdir(exist_ok=True)
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    try:
        os.symlink(outside, store.route_path)
    except OSError:
        pytest.skip("file symlink unavailable")
    with pytest.raises(Exception):
        store.initialize_empty()
    assert outside.read_text(encoding="utf-8") == "{}"
