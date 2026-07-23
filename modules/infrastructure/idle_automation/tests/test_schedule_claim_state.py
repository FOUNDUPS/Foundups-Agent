"""Adversarial tests for durable scheduled-routine claim ownership."""

from __future__ import annotations

import ast
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from modules.infrastructure.idle_automation.src.schedule_claim_state import (
    LEASE_SECONDS,
    MAX_ATTEMPTS,
    RETRY_BACKOFF_SECONDS,
    ScheduleClaimOps,
    ScheduleClaimStore,
    ScheduleStateError,
    ScheduleWindow,
    build_execution_id,
)

NOW = datetime(2026, 7, 24, 1, 0, tzinfo=UTC)


def _window(
    *,
    schedule_id: str = "schedule-1",
    routine: str = "self_research",
    cadence: str = "daily",
    start: datetime = NOW.replace(hour=0),
    end: datetime = NOW.replace(hour=0) + timedelta(days=1),
) -> ScheduleWindow:
    start_text = start.isoformat()
    end_text = end.isoformat()
    return ScheduleWindow(
        schedule_id=schedule_id,
        routine=routine,
        cadence=cadence,
        window_start=start_text,
        window_end=end_text,
        execution_id=build_execution_id(
            schedule_id, routine, cadence, start_text, end_text
        ),
    )


def _store(tmp_path: Path, **kwargs: object) -> ScheduleClaimStore:
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    runtime = tmp_path / "runtime"
    return ScheduleClaimStore(
        repo_root=repo,
        runtime_root=runtime,
        **kwargs,
    )


def _claim(store: ScheduleClaimStore, now: datetime = NOW):
    return store.claim_window(_window(), now=now)


def test_two_independent_evaluators_cannot_double_claim(tmp_path: Path) -> None:
    first = _store(tmp_path)
    second = _store(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda store: _claim(store), (first, second)))
    assert sum(claim is not None for claim in claims) == 1


def test_lease_allows_only_one_expiry_recovery(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = _claim(store)
    assert first is not None
    assert _claim(store, NOW + timedelta(seconds=LEASE_SECONDS - 1)) is None

    recovered = _claim(store, NOW + timedelta(seconds=LEASE_SECONDS))
    assert recovered is not None
    assert recovered.token != first.token
    assert (
        _claim(
            store,
            NOW + timedelta(seconds=(LEASE_SECONDS * 2) + 1),
        )
        is None
    )


def test_stale_token_cannot_finalize_renewed_or_completed_claim(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    first = _claim(store)
    assert first is not None
    recovered_at = NOW + timedelta(seconds=LEASE_SECONDS)
    recovered = _claim(store, recovered_at)
    assert recovered is not None

    assert not store.finalize(
        first.token,
        success=True,
        outcome_code="success",
        now=recovered_at,
    )
    assert store.finalize(
        recovered.token,
        success=True,
        outcome_code="success",
        now=recovered_at + timedelta(seconds=1),
    )
    assert not store.finalize(
        recovered.token,
        success=True,
        outcome_code="success",
        now=recovered_at + timedelta(seconds=2),
    )


def test_expired_unreclaimed_token_can_still_finalize(tmp_path: Path) -> None:
    store = _store(tmp_path)
    claim = _claim(store)
    assert claim is not None
    assert store.finalize(
        claim.token,
        success=True,
        outcome_code="success",
        now=NOW + timedelta(seconds=LEASE_SECONDS + 1),
    )
    assert _claim(store, NOW + timedelta(seconds=LEASE_SECONDS + 2)) is None


def test_completed_window_is_idempotent_after_restart(tmp_path: Path) -> None:
    first_store = _store(tmp_path)
    claim = _claim(first_store)
    assert claim is not None
    assert first_store.finalize(
        claim.token,
        success=True,
        outcome_code="success",
        now=NOW + timedelta(seconds=1),
    )
    assert _claim(_store(tmp_path), NOW + timedelta(seconds=2)) is None


def test_failures_use_bounded_backoff_and_attempt_cap(tmp_path: Path) -> None:
    store = _store(tmp_path)
    now = NOW
    for attempt in range(1, MAX_ATTEMPTS + 1):
        claim = _claim(store, now)
        assert claim is not None
        assert claim.attempt == attempt
        assert store.finalize(
            claim.token,
            success=False,
            outcome_code="routine_failed",
            now=now,
        )
        if attempt < MAX_ATTEMPTS:
            delay = RETRY_BACKOFF_SECONDS[attempt - 1]
            assert _claim(store, now + timedelta(seconds=delay - 1)) is None
            now += timedelta(seconds=delay)
    assert _claim(store, now + timedelta(days=1)) is None


@pytest.mark.parametrize(
    "mutator",
    [
        lambda window: ScheduleWindow(
            **{**window.__dict__, "execution_id": "not-canonical"}
        ),
        lambda window: ScheduleWindow(
            **{
                **window.__dict__,
                "window_start": (
                    datetime.fromisoformat(window.window_end) + timedelta(hours=1)
                ).isoformat(),
            }
        ),
    ],
)
def test_noncanonical_or_invalid_window_fails_closed(
    tmp_path: Path, mutator
) -> None:
    store = _store(tmp_path)
    with pytest.raises(ScheduleStateError):
        store.claim_window(mutator(_window()), now=NOW)
    assert not store.state_path.exists()


def test_now_outside_window_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert (
        store.claim_window(
            _window(), now=NOW.replace(hour=0) - timedelta(seconds=1)
        )
        is None
    )
    assert store.claim_window(_window(), now=NOW + timedelta(days=1)) is None
    assert not store.state_path.exists()


def test_token_collision_fails_closed_without_mutating_lkg(tmp_path: Path) -> None:
    tokens = iter(("same-token", "same-token"))
    store = _store(tmp_path, token_factory=lambda: next(tokens))
    assert store.claim_window(_window(schedule_id="one"), now=NOW)
    before = store.state_path.read_bytes()
    with pytest.raises(ScheduleStateError):
        store.claim_window(_window(schedule_id="two"), now=NOW)
    assert store.state_path.read_bytes() == before


@pytest.mark.parametrize(
    "payload",
    [
        b"{",
        b'{"schema_version":"idle_automation_schedule_claim_state.v1"}',
        b'{"schema_version":"idle_automation_schedule_claim_state.v1",'
        b'"updated_at":"2026-07-24T00:00:00+00:00","executions":{},'
        b'"executions":{}}',
    ],
)
def test_malformed_or_partial_state_fails_closed(
    tmp_path: Path, payload: bytes
) -> None:
    store = _store(tmp_path)
    store.runtime_root.mkdir(parents=True, exist_ok=True)
    store.state_path.write_bytes(payload)
    with pytest.raises(ScheduleStateError):
        _claim(store)
    assert store.state_path.read_bytes() == payload


def test_write_failure_preserves_exact_prior_state(tmp_path: Path) -> None:
    store = _store(tmp_path)
    claim = _claim(store)
    assert claim is not None
    before = store.state_path.read_bytes()

    def broken_writer(stream, payload: bytes) -> None:
        stream.write(payload[:8])
        raise OSError("simulated")

    broken = _store(tmp_path, ops=ScheduleClaimOps(writer=broken_writer))
    with pytest.raises(OSError, match="simulated"):
        broken.finalize(
            claim.token,
            success=True,
            outcome_code="success",
            now=NOW + timedelta(seconds=1),
        )
    assert store.state_path.read_bytes() == before
    assert not list(store.runtime_root.glob(".schedule-claims.*.tmp"))


def test_bad_replacer_is_detected_and_exact_lkg_restored(tmp_path: Path) -> None:
    store = _store(tmp_path)
    claim = _claim(store)
    assert claim is not None
    before = store.state_path.read_bytes()

    def corrupt_replacer(source: Path, target: Path) -> None:
        target.write_bytes(b"corrupt")
        source.unlink()

    broken = _store(tmp_path, ops=ScheduleClaimOps(replacer=corrupt_replacer))
    with pytest.raises(OSError, match="post_replace"):
        broken.finalize(
            claim.token,
            success=True,
            outcome_code="success",
            now=NOW + timedelta(seconds=1),
        )
    assert store.state_path.read_bytes() == before
    assert not list(store.runtime_root.glob(".schedule-claims.*.tmp"))


def test_runtime_state_must_be_outside_repository(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(ValueError):
        ScheduleClaimStore(repo_root=repo, runtime_root=repo / "memory")


def test_arbitrary_dispatch_text_is_not_persisted(tmp_path: Path) -> None:
    store = _store(tmp_path)
    claim = _claim(store)
    assert claim is not None
    secret = "sk-live-should-never-be-in-claim-state"
    assert store.finalize(
        claim.token,
        success=False,
        outcome_code=secret,
        now=NOW + timedelta(seconds=1),
    )
    assert secret.encode() not in store.state_path.read_bytes()


def test_old_terminal_records_are_pruned_before_growth(tmp_path: Path) -> None:
    store = _store(tmp_path)
    old_now = NOW - timedelta(days=40)
    old_window = _window(
        start=old_now.replace(hour=0),
        end=old_now.replace(hour=0) + timedelta(days=1),
    )
    claim = store.claim_window(old_window, now=old_now)
    assert claim is not None
    assert store.finalize(
        claim.token,
        success=True,
        outcome_code="success",
        now=old_now + timedelta(seconds=1),
    )

    new_window = _window(
        schedule_id="new",
        start=NOW + timedelta(days=1),
        end=NOW + timedelta(days=2),
    )
    assert store.claim_window(new_window, now=NOW + timedelta(days=1))
    refreshed = json.loads(store.state_path.read_text(encoding="utf-8"))
    assert len(refreshed["executions"]) == 1


@pytest.mark.parametrize("field", ["lease_expires_at", "next_attempt_at"])
def test_timestamp_order_corruption_fails_closed(
    tmp_path: Path, field: str
) -> None:
    store = _store(tmp_path)
    claim = _claim(store)
    assert claim is not None
    if field == "next_attempt_at":
        assert store.finalize(
            claim.token,
            success=False,
            outcome_code="routine_failed",
            now=NOW + timedelta(seconds=1),
        )
    state = json.loads(store.state_path.read_text(encoding="utf-8"))
    record = next(iter(state["executions"].values()))
    record[field] = (NOW - timedelta(seconds=1)).isoformat()
    payload = json.dumps(state).encode()
    store.state_path.write_bytes(payload)

    with pytest.raises(ScheduleStateError, match="order"):
        _claim(store, NOW + timedelta(seconds=2))
    assert store.state_path.read_bytes() == payload


def test_claim_control_layer_has_no_provider_or_network_imports() -> None:
    source_root = Path(__file__).parents[1] / "src"
    forbidden = {"httpx", "openai", "requests", "urllib"}
    for filename in ("schedule_claim_codec.py", "schedule_claim_state.py"):
        tree = ast.parse((source_root / filename).read_text(encoding="utf-8"))
        direct_imports = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        from_imports = {
            node.module.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        imports = direct_imports | from_imports
        assert imports.isdisjoint(forbidden)
