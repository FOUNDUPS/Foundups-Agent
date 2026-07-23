"""Offline adversarial tests for scheduled provider discovery replay control."""

from __future__ import annotations

import asyncio
import json
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_gateway.src import (
    model_openrouter_scheduled_discovery as scheduled_guard,
)
from modules.ai_intelligence.ai_gateway.src.model_openrouter_direct_discovery import (
    HTTPResponse,
    discover_openrouter_model_catalog,
)
from modules.ai_intelligence.ai_gateway.src.model_openrouter_scheduled_discovery import (
    discover_scheduled_openrouter_model_catalog,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_artifact_store import (
    AtomicArtifactOps,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_replay_state import (
    derive_scheduled_discovery_paths,
    load_replay_ledger,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_snapshot import (
    build_discovery_invocation,
)

FIXTURES = Path(__file__).parent / "fixtures"
NOW = 10_000


class _CountingTransport:
    def __init__(
        self,
        *,
        status: int = 200,
        pause: float = 0.0,
        body: bytes | None = None,
    ) -> None:
        self.status = status
        self.pause = pause
        self.body = body
        self.calls = 0
        self._lock = threading.Lock()

    async def fetch(self, _request):
        with self._lock:
            self.calls += 1
        if self.pause:
            await asyncio.sleep(self.pause)
        return HTTPResponse(
            self.status,
            {"Content-Type": "application/json"},
            self.body
            or (FIXTURES / "openrouter_models_success.json").read_bytes(),
        )


class _EventBlockingTransport(_CountingTransport):
    def __init__(self) -> None:
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()

    async def fetch(self, _request):
        with self._lock:
            self.calls += 1
        self.started.set()
        if not self.release.wait(timeout=5):
            raise TimeoutError("test_transport_release_timeout")
        return HTTPResponse(
            200,
            {"Content-Type": "application/json"},
            (FIXTURES / "openrouter_models_success.json").read_bytes(),
        )


async def _wait_thread_event(event: threading.Event) -> None:
    observed = await asyncio.wait_for(
        asyncio.to_thread(event.wait, 5),
        timeout=6,
    )
    assert observed


def _invocation(*, schedule: str = "daily", offset: int = 0):
    return build_discovery_invocation(
        mode="scheduled",
        schedule_id=schedule,
        scheduled_for_ms=NOW - 10 + offset,
        expires_at_ms=NOW + 100_000 + offset,
    )


def _roots(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo, tmp_path / "runtime"


async def _scheduled(
    tmp_path: Path,
    transport,
    *,
    invocation=None,
    artifact_ops=None,
    now: int = NOW,
):
    repo, runtime = _roots(tmp_path) if not (tmp_path / "repo").exists() else (
        tmp_path / "repo",
        tmp_path / "runtime",
    )
    return await discover_scheduled_openrouter_model_catalog(
        invocation or _invocation(),
        repo_root=repo,
        runtime_root=runtime,
        transport=transport,
        clock_ms=lambda: now,
        artifact_ops=artifact_ops,
    )


def test_same_event_loop_concurrency_calls_transport_once_without_deadlock(
    tmp_path: Path,
) -> None:
    transport = _CountingTransport(pause=0.05)

    async def exercise():
        return await asyncio.wait_for(
            asyncio.gather(
                _scheduled(tmp_path, transport),
                _scheduled(tmp_path, transport),
            ),
            timeout=5,
        )

    first, second = asyncio.run(exercise())
    assert transport.calls == 1
    assert {first.status, second.status} == {"COMPLETED"}
    assert sorted((first.replayed, second.replayed)) == [False, True]


def test_cancelled_active_caller_worker_finishes_without_duplicate(
    tmp_path: Path,
) -> None:
    transport = _EventBlockingTransport()

    async def exercise():
        first = asyncio.create_task(_scheduled(tmp_path, transport))
        try:
            await _wait_thread_event(transport.started)
            first.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first
            retry = asyncio.create_task(_scheduled(tmp_path, transport))
            transport.release.set()
            return await asyncio.wait_for(retry, timeout=5)
        finally:
            transport.release.set()

    replay = asyncio.run(exercise())
    assert replay.status == "COMPLETED"
    assert replay.replayed is True
    assert transport.calls == 1


def test_cancelled_lock_waiter_worker_cannot_duplicate_or_deadlock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = _EventBlockingTransport()
    waiter_started = threading.Event()
    waiter_finished = threading.Event()
    call_lock = threading.Lock()
    lock_calls = 0
    real_lock = scheduled_guard.runtime_operation_lock

    @contextmanager
    def observed_lock(identity):
        nonlocal lock_calls
        with call_lock:
            lock_calls += 1
            ordinal = lock_calls
        if ordinal == 2:
            waiter_started.set()
        try:
            with real_lock(identity):
                yield
        finally:
            if ordinal == 2:
                waiter_finished.set()

    monkeypatch.setattr(
        scheduled_guard, "runtime_operation_lock", observed_lock
    )

    async def exercise():
        first = asyncio.create_task(_scheduled(tmp_path, transport))
        try:
            await _wait_thread_event(transport.started)
            waiter = asyncio.create_task(_scheduled(tmp_path, transport))
            await _wait_thread_event(waiter_started)
            waiter.cancel()
            with pytest.raises(asyncio.CancelledError):
                await waiter
            transport.release.set()
            completed = await asyncio.wait_for(first, timeout=5)
            await _wait_thread_event(waiter_finished)
            retry = await asyncio.wait_for(
                _scheduled(tmp_path, transport),
                timeout=5,
            )
            return completed, retry
        finally:
            transport.release.set()

    completed, replay = asyncio.run(exercise())
    assert completed.status == "COMPLETED"
    assert completed.replayed is False
    assert replay.status == "COMPLETED" and replay.replayed is True
    assert transport.calls == 1


def test_completed_same_window_replays_without_transport(tmp_path: Path) -> None:
    transport = _CountingTransport()
    first = asyncio.run(_scheduled(tmp_path, transport))
    second = asyncio.run(_scheduled(tmp_path, transport))

    assert first.status == second.status == "COMPLETED"
    assert first.replayed is False
    assert second.replayed is True
    assert second.receipt == first.receipt
    assert transport.calls == 1


def test_different_windows_each_allow_one_transport(tmp_path: Path) -> None:
    transport = _CountingTransport()
    first = asyncio.run(_scheduled(tmp_path, transport))
    second = asyncio.run(
        _scheduled(
            tmp_path,
            transport,
            invocation=_invocation(schedule="next", offset=20),
            now=NOW + 20,
        )
    )
    assert first.status == second.status == "COMPLETED"
    assert transport.calls == 2


def test_admission_is_rechecked_after_operation_lock(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    invocation = build_discovery_invocation(
        mode="scheduled",
        schedule_id="expires-at-lock",
        scheduled_for_ms=NOW,
        expires_at_ms=NOW,
    )
    ticks = iter((NOW, NOW + 1))
    transport = _CountingTransport()
    result = asyncio.run(
        discover_scheduled_openrouter_model_catalog(
            invocation,
            repo_root=repo,
            runtime_root=runtime,
            transport=transport,
            clock_ms=lambda: next(ticks),
        )
    )
    assert result.status == "BLOCKED_PRECALL"
    assert result.reason == "scheduled_invocation_expired"
    assert transport.calls == 0


def test_failed_attempt_is_terminal_for_same_invocation(tmp_path: Path) -> None:
    transport = _CountingTransport(status=503)
    first = asyncio.run(_scheduled(tmp_path, transport))
    second = asyncio.run(_scheduled(tmp_path, transport))

    assert first.status == second.status == "FAILED"
    assert second.replayed is True
    assert transport.calls == 1


def test_blocked_precall_attempted_false_may_retry(tmp_path: Path) -> None:
    transport = _CountingTransport()
    failed_once = False

    def fail_attempt(source: Path, target: Path) -> None:
        nonlocal failed_once
        if target.name.endswith("attempt.json") and not failed_once:
            failed_once = True
            raise OSError("simulated_attempt_write_failure")
        source.replace(target)

    first = asyncio.run(
        _scheduled(
            tmp_path,
            transport,
            artifact_ops=AtomicArtifactOps(replacer=fail_attempt),
        )
    )
    second = asyncio.run(_scheduled(tmp_path, transport))

    assert first.status == "BLOCKED_PRECALL"
    assert first.receipt is not None and first.receipt.attempted is False
    assert second.status == "COMPLETED"
    assert transport.calls == 1


def test_terminal_ledger_failure_leaves_armed_then_recovers_exact_attempt(
    tmp_path: Path,
) -> None:
    transport = _CountingTransport()
    ledger_writes = 0
    prior_armed_bytes = None

    def fail_terminal(source: Path, target: Path) -> None:
        nonlocal ledger_writes, prior_armed_bytes
        if target.name.endswith("ledger.json"):
            ledger_writes += 1
            if ledger_writes == 2:
                prior_armed_bytes = target.read_bytes()
                raise OSError("simulated_terminal_ledger_failure")
        source.replace(target)

    first = asyncio.run(
        _scheduled(
            tmp_path,
            transport,
            artifact_ops=AtomicArtifactOps(replacer=fail_terminal),
        )
    )
    repo, runtime = _roots(tmp_path) if not (tmp_path / "repo").exists() else (
        tmp_path / "repo",
        tmp_path / "runtime",
    )
    paths = derive_scheduled_discovery_paths(
        repo_root=repo, runtime_root=runtime
    )
    armed = load_replay_ledger(paths, now_ms=NOW)
    armed_bytes = paths.ledger_path.read_bytes()
    assert armed_bytes == prior_armed_bytes
    second = asyncio.run(_scheduled(tmp_path, transport))

    assert first.status == "INDETERMINATE"
    assert next(iter(armed["entries"].values()))["status"] == "ARMED"
    assert second.status == "COMPLETED" and second.replayed is True
    assert transport.calls == 1


def test_preledger_exact_completed_attempt_is_adopted_without_transport(
    tmp_path: Path,
) -> None:
    repo, runtime = _roots(tmp_path)
    paths = derive_scheduled_discovery_paths(
        repo_root=repo, runtime_root=runtime
    )
    invocation = _invocation()
    source_transport = _CountingTransport()
    seeded = asyncio.run(
        discover_openrouter_model_catalog(
            invocation,
            repo_root=repo,
            runtime_root=runtime,
            attempt_path=paths.attempt_path,
            candidate_path=paths.candidate_path,
            transport=source_transport,
            clock_ms=lambda: NOW,
        )
    )
    replay_transport = _CountingTransport()
    adopted = asyncio.run(
        discover_scheduled_openrouter_model_catalog(
            invocation,
            repo_root=repo,
            runtime_root=runtime,
            transport=replay_transport,
            clock_ms=lambda: NOW,
        )
    )
    assert seeded.receipt.outcome == "COMPLETED"
    assert adopted.status == "COMPLETED" and adopted.replayed is True
    assert replay_transport.calls == 0


def test_candidate_alone_for_same_invocation_never_promotes(
    tmp_path: Path,
) -> None:
    repo, runtime = _roots(tmp_path)
    paths = derive_scheduled_discovery_paths(
        repo_root=repo, runtime_root=runtime
    )
    invocation = _invocation()
    asyncio.run(
        discover_openrouter_model_catalog(
            invocation,
            repo_root=repo,
            runtime_root=runtime,
            attempt_path=paths.attempt_path,
            candidate_path=paths.candidate_path,
            transport=_CountingTransport(),
            clock_ms=lambda: NOW,
        )
    )
    paths.attempt_path.unlink()
    transport = _CountingTransport()
    result = asyncio.run(
        discover_scheduled_openrouter_model_catalog(
            invocation,
            repo_root=repo,
            runtime_root=runtime,
            transport=transport,
            clock_ms=lambda: NOW,
        )
    )
    assert result.status == "INDETERMINATE"
    assert result.reason == "candidate_without_terminal_attempt"
    assert transport.calls == 0


def test_completed_replay_missing_or_corrupt_candidate_fails_closed(
    tmp_path: Path,
) -> None:
    transport = _CountingTransport()
    completed = asyncio.run(_scheduled(tmp_path, transport))
    assert completed.candidate_path is not None
    completed.candidate_path.unlink()
    missing = asyncio.run(_scheduled(tmp_path, transport))
    completed.candidate_path.write_text("{", encoding="utf-8")
    corrupt = asyncio.run(_scheduled(tmp_path, transport))

    assert missing.status == corrupt.status == "INDETERMINATE"
    assert transport.calls == 1


def test_completed_candidate_larger_than_one_mib_replays(
    tmp_path: Path,
) -> None:
    parameters = [
        f"capability_{index:02d}_{'x' * 40}" for index in range(16)
    ]
    records = [
        {
            "id": f"provider/model-{index:04d}",
            "supported_parameters": parameters,
        }
        for index in range(2048)
    ]
    body = json.dumps(
        {"data": records}, separators=(",", ":")
    ).encode("utf-8")
    transport = _CountingTransport(body=body)
    first = asyncio.run(_scheduled(tmp_path, transport))
    second = asyncio.run(_scheduled(tmp_path, transport))

    assert first.status == second.status == "COMPLETED"
    assert first.candidate_path is not None
    assert first.candidate_path.stat().st_size > 1024 * 1024
    assert second.replayed is True
    assert transport.calls == 1
