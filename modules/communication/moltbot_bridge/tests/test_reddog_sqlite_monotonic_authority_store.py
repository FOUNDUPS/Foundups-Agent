"""Focused tests for the SQLite monotonic authority store."""

from __future__ import annotations

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
