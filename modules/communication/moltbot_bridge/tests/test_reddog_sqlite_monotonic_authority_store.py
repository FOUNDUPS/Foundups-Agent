"""Focused tests for the SQLite monotonic authority store."""

from __future__ import annotations

import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityReader,
    SqliteMonotonicAuthorityStore,
)


BINDING = "sha256:" + "a" * 64
DURABILITY_RECEIPT = "sha256:" + "d" * 64
STORE_ID = "signer-generation-witness:test"


@pytest.fixture()
def roots(tmp_path: Path) -> tuple[Path, Path]:
    repo_root = tmp_path / "repo"
    authority_root = tmp_path / "signer-authority"
    repo_root.mkdir()
    authority_root.mkdir()
    return repo_root, authority_root


def _store(
    roots: tuple[Path, Path],
    *,
    store_id: str = STORE_ID,
    durability_receipt_id: str = DURABILITY_RECEIPT,
) -> SqliteMonotonicAuthorityStore:
    repo_root, authority_root = roots
    return SqliteMonotonicAuthorityStore(
        authority_root / "generation-witness.sqlite3",
        allowed_root=authority_root,
        repo_root=repo_root,
        store_id=store_id,
        durability_receipt_id=durability_receipt_id,
    )


def _value(sequence: int, revision_char: str) -> ProposalReplayHighWater:
    return ProposalReplayHighWater(
        sequence=sequence,
        state_revision=revision_char * 64,
    )


def test_restart_roundtrip_preserves_committed_high_water(roots) -> None:
    store = _store(roots)
    first = _value(1, "1")
    second = _value(2, "2")

    store.advance(BINDING, expected=None, next_value=first)
    restarted = _store(roots)
    assert restarted.load(BINDING) == first

    restarted.advance(BINDING, expected=first, next_value=second)
    assert _store(roots).load(BINDING) == second


def test_reader_observes_commits_without_mutation_capability(roots) -> None:
    store = _store(roots)
    reader = store.reader()
    first = _value(1, "1")

    assert type(reader) is SqliteMonotonicAuthorityReader
    assert not hasattr(reader, "advance")
    assert reader.load(BINDING) is None

    store.advance(BINDING, expected=None, next_value=first)

    assert reader.load(BINDING) == first


def test_reader_revalidates_metadata_on_every_open(roots) -> None:
    store = _store(roots)
    reader = store.reader()
    path = roots[1] / "generation-witness.sqlite3"

    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE metadata SET durability_receipt_id = ?",
            ("sha256:" + "e" * 64,),
        )

    with pytest.raises(
        ValueError, match="monotonic_authority_identity_mismatch"
    ):
        reader.load(BINDING)


def test_compare_and_swap_rejects_stale_expected_value(roots) -> None:
    store = _store(roots)
    first = _value(1, "1")
    store.advance(BINDING, expected=None, next_value=first)

    with pytest.raises(RuntimeError, match="monotonic_authority_conflict"):
        store.advance(
            BINDING,
            expected=None,
            next_value=_value(1, "2"),
        )

    assert store.load(BINDING) == first


def test_non_monotonic_sequence_is_rejected(roots) -> None:
    store = _store(roots)
    first = _value(1, "1")
    store.advance(BINDING, expected=None, next_value=first)

    with pytest.raises(ValueError, match="monotonic_authority_not_monotonic"):
        store.advance(
            BINDING,
            expected=first,
            next_value=_value(3, "3"),
        )

    assert store.load(BINDING) == first


@pytest.mark.parametrize(
    ("store_id", "durability_receipt_id"),
    [
        ("different-store", DURABILITY_RECEIPT),
        (STORE_ID, "sha256:" + "e" * 64),
    ],
)
def test_existing_database_rejects_metadata_identity_mismatch(
    roots,
    store_id: str,
    durability_receipt_id: str,
) -> None:
    _store(roots)

    with pytest.raises(
        ValueError,
        match="monotonic_authority_identity_mismatch",
    ):
        _store(
            roots,
            store_id=store_id,
            durability_receipt_id=durability_receipt_id,
        )


def test_concurrent_compare_and_swap_has_exactly_one_winner(roots) -> None:
    stores = (_store(roots), _store(roots))

    def advance(candidate_and_revision: tuple[SqliteMonotonicAuthorityStore, str]) -> str:
        candidate, revision_char = candidate_and_revision
        try:
            candidate.advance(
                BINDING,
                expected=None,
                next_value=_value(1, revision_char),
            )
        except RuntimeError as exc:
            assert str(exc) == "monotonic_authority_conflict"
            return "conflict"
        return "committed"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(advance, zip(stores, ("1", "2"))))

    assert sorted(outcomes) == ["committed", "conflict"]
    assert _store(roots).load(BINDING) in {_value(1, "1"), _value(1, "2")}


def test_concurrent_first_open_initializes_one_consistent_store(roots) -> None:
    ready = Barrier(4)

    def construct(_: int) -> tuple[str, str]:
        ready.wait()
        store = _store(roots)
        return store.store_id, store.durability_receipt_id

    with ThreadPoolExecutor(max_workers=4) as executor:
        outcomes = list(executor.map(construct, range(4)))

    assert outcomes == [(STORE_ID, DURABILITY_RECEIPT)] * 4
    assert _store(roots).load(BINDING) is None


def test_store_is_confined_outside_repository(roots) -> None:
    repo_root, authority_root = roots
    store = _store(roots)

    assert store.durable is True
    assert (authority_root / "generation-witness.sqlite3").is_file()
    assert not (repo_root / "generation-witness.sqlite3").exists()

    with pytest.raises(ValueError):
        SqliteMonotonicAuthorityStore(
            repo_root / "generation-witness.sqlite3",
            allowed_root=repo_root,
            repo_root=repo_root,
            store_id=STORE_ID,
            durability_receipt_id=DURABILITY_RECEIPT,
        )

    nested_root = authority_root / "nested"
    with pytest.raises(ValueError, match="monotonic_authority_path_invalid"):
        SqliteMonotonicAuthorityStore(
            nested_root / "generation-witness.sqlite3",
            allowed_root=authority_root,
            repo_root=repo_root,
            store_id=STORE_ID,
            durability_receipt_id=DURABILITY_RECEIPT,
        )


@pytest.mark.parametrize(
    ("binding", "expected", "next_value", "error"),
    [
        (
            "not-a-digest",
            None,
            ProposalReplayHighWater(1, "1" * 64),
            "monotonic_authority_binding_invalid",
        ),
        (
            BINDING,
            object(),
            ProposalReplayHighWater(1, "1" * 64),
            "monotonic_authority_value_invalid",
        ),
        (
            BINDING,
            None,
            ProposalReplayHighWater(True, "1" * 64),
            "monotonic_authority_value_invalid",
        ),
        (
            BINDING,
            None,
            ProposalReplayHighWater(1, "G" * 64),
            "monotonic_authority_value_invalid",
        ),
        (
            BINDING,
            None,
            ProposalReplayHighWater(0, "1" * 64),
            "monotonic_authority_value_invalid",
        ),
    ],
)
def test_malformed_values_fail_closed(
    roots,
    binding,
    expected,
    next_value,
    error: str,
) -> None:
    store = _store(roots)

    with pytest.raises(ValueError, match=error):
        store.advance(
            binding,
            expected=expected,
            next_value=next_value,
        )

    assert store.load(BINDING) is None


@pytest.fixture()
def mirrors(roots):
    destination = _store(roots)
    witness_root = roots[1].with_name("mirror-witness")
    witness_root.mkdir()
    witness = _store((roots[0], witness_root), store_id="witness:recovery")
    return destination, witness


def _advance_to(store, sequence):
    current = None
    for number in range(1, sequence + 1):
        wanted = _value(number, str(number))
        store.advance(BINDING, expected=current, next_value=wanted)
        current = wanted
    return current


@pytest.mark.parametrize("sequence", [1, 2, 5])
def test_missing_checkpoint_restore_is_exact_durable_and_idempotent(mirrors, roots, sequence):
    destination, source = mirrors
    expected = _advance_to(source, sequence)
    witness = source.reader()
    assert not hasattr(witness, "restore_missing_from_witness")
    for _ in range(2):
        destination.restore_missing_from_witness(BINDING, witness=witness, expected=expected)
        assert _store(roots).reader().load(BINDING) == expected
        assert witness.load(BINDING) == expected
    if sequence > 1:
        with pytest.raises(ValueError, match="monotonic_authority_not_monotonic"):
            destination.advance("sha256:" + "f" * 64, expected=None, next_value=expected)
        assert destination.load("sha256:" + "f" * 64) is None


@pytest.mark.parametrize("side", ["destination", "witness"])
def test_restore_rechecks_both_store_identities_before_writing(mirrors, side):
    destination, source = mirrors
    expected = _advance_to(source, 3)
    witness = source.reader()
    changed = destination if side == "destination" else source
    with sqlite3.connect(changed.path) as connection:
        connection.execute("UPDATE metadata SET store_id = 'substituted'")
    with pytest.raises(ValueError, match="monotonic_authority_identity_mismatch"):
        destination.restore_missing_from_witness(BINDING, witness=witness, expected=expected)
    assert destination.load(BINDING) is None
    assert source.load(BINDING) == expected


@pytest.mark.parametrize("bad", ["object", "writer", "same-root", "nested-root", "foreign-repo"])
def test_restore_rejects_unqualified_or_overlapping_witness(mirrors, roots, bad):
    destination, source = mirrors
    expected = _advance_to(source, 3)
    witness = source.reader()
    error = "monotonic_authority_restore_domain_invalid"
    if bad in {"object", "writer"}:
        witness = object() if bad == "object" else source
        error = "monotonic_authority_restore_witness_invalid"
    elif bad == "same-root":
        witness = destination.reader()
    elif bad == "nested-root":
        nested = destination.rollback_domain_root / "nested-witness"
        nested.mkdir()
        witness = _store((roots[0], nested), store_id="nested:recovery").reader()
    else:
        other_repo = roots[0].with_name("other-repo")
        other_repo.mkdir()
        witness = SqliteMonotonicAuthorityReader(
            source.path, allowed_root=source.rollback_domain_root,
            repo_root=other_repo, store_id=source.store_id,
            durability_receipt_id=source.durability_receipt_id,
        )
    with pytest.raises(ValueError, match=error):
        destination.restore_missing_from_witness(BINDING, witness=witness, expected=expected)
    assert destination.load(BINDING) is None


@pytest.mark.parametrize("mismatch", ["missing", "behind", "revision", "binding"])
def test_restore_requires_the_exact_current_witness_checkpoint(mirrors, mismatch):
    destination, source = mirrors
    actual = None if mismatch == "missing" else _advance_to(source, 3)
    expected = _value(2, "2") if mismatch == "behind" else _value(3, "3")
    if mismatch == "revision":
        expected = _value(3, "f")
    binding = "sha256:" + "b" * 64 if mismatch == "binding" else BINDING
    with pytest.raises(RuntimeError, match="monotonic_authority_restore_witness_changed"):
        destination.restore_missing_from_witness(binding, witness=source.reader(), expected=expected)
    assert destination.load(binding) is None
    assert source.load(BINDING) == actual


@pytest.mark.parametrize("current_sequence", [1, 3, 4])
def test_restore_never_replaces_conflicting_existing_destination(mirrors, current_sequence):
    destination, source = mirrors
    current = _advance_to(destination, current_sequence)
    if current_sequence == 3:
        prior = _advance_to(source, 2)
        expected = _value(3, "f")
        source.advance(BINDING, expected=prior, next_value=expected)
    else:
        expected = _advance_to(source, 3)
    with pytest.raises(RuntimeError, match="monotonic_authority_conflict"):
        destination.restore_missing_from_witness(BINDING, witness=source.reader(), expected=expected)
    assert destination.load(BINDING) == current
    assert source.load(BINDING) == expected


@pytest.mark.parametrize("change_on_call", [2, 3])
def test_restore_source_change_is_not_acknowledged(mirrors, monkeypatch, change_on_call):
    destination, source = mirrors
    expected = _advance_to(source, 3)
    witness = source.reader()
    load = SqliteMonotonicAuthorityReader.load
    calls = 0

    def changing_load(self, binding):
        nonlocal calls
        if self.path == source.path:
            calls += 1
            if calls == change_on_call:
                source.advance(BINDING, expected=expected, next_value=_value(4, "4"))
        return load(self, binding)

    # Exact reader type is retained; slots prevent attaching replacement methods.
    monkeypatch.setattr(SqliteMonotonicAuthorityReader, "load", changing_load)
    error = "witness_changed" if change_on_call == 2 else "restore_unverified"
    with pytest.raises(RuntimeError, match=error):
        destination.restore_missing_from_witness(BINDING, witness=witness, expected=expected)
    assert destination.load(BINDING) == (None if change_on_call == 2 else expected)
    assert source.load(BINDING) == _value(4, "4")


def test_restore_cancellation_before_copy_preserves_missing_destination(mirrors, monkeypatch):
    destination, source = mirrors
    expected = _advance_to(source, 3)
    original = SqliteMonotonicAuthorityReader.load
    calls = 0

    def cancel(self, binding):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise asyncio.CancelledError()
        return original(self, binding)

    monkeypatch.setattr(SqliteMonotonicAuthorityReader, "load", cancel)
    with pytest.raises(asyncio.CancelledError):
        destination.restore_missing_from_witness(BINDING, witness=source.reader(), expected=expected)
    assert destination.load(BINDING) is None
    assert source.load(BINDING) == expected


def test_concurrent_exact_restorations_share_one_checkpoint(mirrors):
    destination, source = mirrors
    expected = _advance_to(source, 3)
    barrier = Barrier(2)

    def recover(_index):
        barrier.wait()
        destination.restore_missing_from_witness(BINDING, witness=source.reader(), expected=expected)
        return destination.load(BINDING)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(recover, range(2)))
    assert results == [expected, expected]
    assert source.load(BINDING) == expected


def test_competing_restore_checkpoints_preserve_one_exact_winner(mirrors, roots):
    destination, first = mirrors
    other_root = roots[1].with_name("other-witness")
    other_root.mkdir()
    second = _store((roots[0], other_root), store_id="other:recovery")
    candidates = [(first, _advance_to(first, 3)), (second, _advance_to(second, 2))]
    barrier = Barrier(2)

    def recover(index):
        source, expected = candidates[index]
        barrier.wait()
        try:
            destination.restore_missing_from_witness(
                BINDING, witness=source.reader(), expected=expected,
            )
        except RuntimeError as exc:
            assert str(exc) == "monotonic_authority_conflict"
            return False
        return True

    with ThreadPoolExecutor(max_workers=2) as executor:
        accepted = list(executor.map(recover, range(2)))
    assert sum(accepted) == 1
    assert destination.load(BINDING) == candidates[accepted.index(True)][1]
    assert all(source.load(BINDING) == expected for source, expected in candidates)
