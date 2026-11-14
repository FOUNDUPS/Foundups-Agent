"""Offline persistence and process tests for scheduled discovery replay state."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_gateway.src.model_openrouter_direct_discovery import (
    discover_openrouter_model_catalog,
)
from modules.ai_intelligence.ai_gateway.src.model_openrouter_scheduled_discovery import (
    discover_scheduled_openrouter_model_catalog,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_artifact_store import (
    ProviderCatalogArtifactStore,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_replay_state import (
    MAX_LEDGER_ENTRIES,
    armed_entry,
    derive_scheduled_discovery_paths,
    empty_replay_ledger,
    load_replay_ledger,
    receipt_entry,
    save_replay_ledger,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_snapshot import (
    build_discovery_invocation,
    build_discovery_receipt,
    sha256_bytes,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_openrouter_scheduled_discovery import (
    NOW,
    _CountingTransport,
    _invocation,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _roots(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    return repo, tmp_path / "runtime"


def _call(
    invocation,
    repo: Path,
    runtime: Path,
    transport,
    *,
    now: int = NOW,
):
    return asyncio.run(
        discover_scheduled_openrouter_model_catalog(
            invocation,
            repo_root=repo,
            runtime_root=runtime,
            transport=transport,
            clock_ms=lambda: now,
        )
    )


def _seed_direct(
    invocation,
    repo: Path,
    runtime: Path,
    transport,
    *,
    now: int,
):
    paths = derive_scheduled_discovery_paths(
        repo_root=repo, runtime_root=runtime
    )
    return asyncio.run(
        discover_openrouter_model_catalog(
            invocation,
            repo_root=repo,
            runtime_root=runtime,
            attempt_path=paths.attempt_path,
            candidate_path=paths.candidate_path,
            transport=transport,
            clock_ms=lambda: now,
        )
    )


def _indeterminate_receipt(invocation):
    return build_discovery_receipt(
        invocation=invocation,
        call_id="scheduled-test-call",
        request_envelope_digest=f"sha256:{'a' * 64}",
        attempted=True,
        outcome="INDETERMINATE",
        reason="transport_pending",
        started_at_ms=NOW,
        completed_at_ms=NOW,
    )


def test_two_subprocesses_share_one_transport_call(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    counter = tmp_path / "transport-count.txt"
    fixture = FIXTURES / "openrouter_models_success.json"
    script = """
import asyncio, sys
from pathlib import Path
from modules.ai_intelligence.ai_gateway.src.model_openrouter_direct_discovery import HTTPResponse
from modules.ai_intelligence.ai_gateway.src.model_openrouter_scheduled_discovery import discover_scheduled_openrouter_model_catalog
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_snapshot import build_discovery_invocation
class T:
    async def fetch(self, _request):
        with Path(sys.argv[3]).open("a", encoding="utf-8") as stream:
            stream.write("1\\n")
        await asyncio.sleep(0.1)
        return HTTPResponse(200, {"Content-Type": "application/json"}, Path(sys.argv[4]).read_bytes())
inv = build_discovery_invocation(mode="scheduled", schedule_id="daily", scheduled_for_ms=9990, expires_at_ms=110000)
result = asyncio.run(discover_scheduled_openrouter_model_catalog(inv, repo_root=Path(sys.argv[1]), runtime_root=Path(sys.argv[2]), transport=T(), clock_ms=lambda: 10000))
print(result.status)
"""
    args = [sys.executable, "-c", script, str(repo), str(runtime), str(counter), str(fixture)]
    first = subprocess.Popen(
        args, cwd=Path.cwd(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    second = subprocess.Popen(
        args, cwd=Path.cwd(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    outputs = [process.communicate(timeout=15) for process in (first, second)]
    assert [first.returncode, second.returncode] == [0, 0], outputs
    assert counter.read_text(encoding="utf-8").splitlines() == ["1"]
    assert [stdout.strip() for stdout, _stderr in outputs] == [
        "COMPLETED",
        "COMPLETED",
    ]


@pytest.mark.parametrize("status", ["ARMED", "INDETERMINATE"])
def test_armed_or_indeterminate_ledger_replay_never_calls_transport(
    tmp_path: Path, status: str
) -> None:
    repo, runtime = _roots(tmp_path)
    paths = derive_scheduled_discovery_paths(
        repo_root=repo, runtime_root=runtime
    )
    invocation = _invocation()
    state = empty_replay_ledger()
    state["entries"][invocation.invocation_id] = (
        armed_entry(invocation)
        if status == "ARMED"
        else receipt_entry(_indeterminate_receipt(invocation))
    )
    store = ProviderCatalogArtifactStore.create(
        repo_root=repo, runtime_root=runtime
    )
    save_replay_ledger(paths, state, now_ms=NOW, store=store)
    transport = _CountingTransport()

    result = _call(invocation, repo, runtime, transport)
    assert result.status == "INDETERMINATE"
    assert transport.calls == 0


def test_preledger_indeterminate_attempt_blocks_transport(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    paths = derive_scheduled_discovery_paths(
        repo_root=repo, runtime_root=runtime
    )
    invocation = _invocation()
    store = ProviderCatalogArtifactStore.create(
        repo_root=repo, runtime_root=runtime
    )
    store.replace_text(
        paths.attempt_path,
        json.dumps(_indeterminate_receipt(invocation).to_dict()) + "\n",
    )
    transport = _CountingTransport()
    result = _call(invocation, repo, runtime, transport)
    assert result.status == "INDETERMINATE"
    assert transport.calls == 0


def test_preledger_exact_blocked_attempt_never_retries(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    paths = derive_scheduled_discovery_paths(
        repo_root=repo, runtime_root=runtime
    )
    invocation = _invocation()
    completed = _seed_direct(
        invocation,
        repo,
        runtime,
        _CountingTransport(),
        now=NOW,
    )
    assert completed.receipt.outcome == "COMPLETED"
    blocked = build_discovery_receipt(
        invocation=invocation,
        call_id="preledger-blocked",
        request_envelope_digest=sha256_bytes(b"request"),
        attempted=False,
        outcome="BLOCKED_PRECALL",
        reason="precall_write_failed",
        started_at_ms=NOW,
        completed_at_ms=NOW,
    )
    store = ProviderCatalogArtifactStore.create(
        repo_root=repo, runtime_root=runtime
    )
    store.replace_text(
        paths.attempt_path, json.dumps(blocked.to_dict()) + "\n"
    )
    transport = _CountingTransport()
    result = _call(invocation, repo, runtime, transport)

    assert result.status == "INDETERMINATE"
    assert result.reason == "preledger_nonterminal_attempt"
    assert paths.candidate_path.exists()
    assert transport.calls == 0


def test_preledger_newer_direct_evidence_blocks_older_invocation(
    tmp_path: Path,
) -> None:
    repo, runtime = _roots(tmp_path)
    older = _invocation(schedule="older")
    _seed_direct(
        older, repo, runtime, _CountingTransport(), now=NOW
    )
    newer = _invocation(schedule="newer", offset=20)
    _seed_direct(
        newer, repo, runtime, _CountingTransport(), now=NOW + 20
    )
    transport = _CountingTransport()
    result = _call(
        older, repo, runtime, transport, now=NOW + 20
    )

    assert result.status == "INDETERMINATE"
    assert result.reason == "preledger_evidence_not_prior"
    assert transport.calls == 0


def test_preledger_coherent_older_evidence_allows_strictly_newer_window(
    tmp_path: Path,
) -> None:
    repo, runtime = _roots(tmp_path)
    _seed_direct(
        _invocation(schedule="older"),
        repo,
        runtime,
        _CountingTransport(),
        now=NOW,
    )
    current = _invocation(schedule="current", offset=20)
    transport = _CountingTransport()
    result = _call(
        current, repo, runtime, transport, now=NOW + 20
    )

    assert result.status == "COMPLETED"
    assert result.replayed is False
    assert transport.calls == 1


def test_missing_ledger_entry_still_checks_newer_fixed_evidence(
    tmp_path: Path,
) -> None:
    repo, runtime = _roots(tmp_path)
    older = _invocation(schedule="older")
    newer = _invocation(schedule="newer", offset=20)
    _seed_direct(
        older, repo, runtime, _CountingTransport(), now=NOW
    )
    _seed_direct(
        newer, repo, runtime, _CountingTransport(), now=NOW + 20
    )
    adopt_transport = _CountingTransport()
    adopted = _call(
        newer, repo, runtime, adopt_transport, now=NOW + 20
    )
    replay_transport = _CountingTransport()
    replay = _call(
        older, repo, runtime, replay_transport, now=NOW + 20
    )

    assert adopted.status == "COMPLETED" and adopted.replayed is True
    assert adopt_transport.calls == 0
    assert replay.status == "INDETERMINATE"
    assert replay.reason == "preledger_evidence_not_prior"
    assert replay_transport.calls == 0


def test_missing_entry_strictly_after_initialized_ledger_calls_once(
    tmp_path: Path,
) -> None:
    repo, runtime = _roots(tmp_path)
    older = _invocation(schedule="older")
    _seed_direct(
        older, repo, runtime, _CountingTransport(), now=NOW
    )
    adopted = _call(
        older, repo, runtime, _CountingTransport(), now=NOW
    )
    current = _invocation(schedule="current", offset=20)
    transport = _CountingTransport()
    result = _call(
        current, repo, runtime, transport, now=NOW + 20
    )

    assert adopted.status == "COMPLETED" and adopted.replayed is True
    assert result.status == "COMPLETED" and result.replayed is False
    assert transport.calls == 1


def test_newer_valid_candidate_reuses_completed_ledger(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    first = _invocation()
    scheduled_transport = _CountingTransport()
    completed = _call(first, repo, runtime, scheduled_transport)
    newer = _invocation(schedule="newer", offset=10)
    _seed_direct(
        newer,
        repo,
        runtime,
        _CountingTransport(),
        now=NOW + 10,
    )
    replay_transport = _CountingTransport()
    replay = _call(
        first, repo, runtime, replay_transport, now=NOW + 10
    )
    paths = derive_scheduled_discovery_paths(
        repo_root=repo, runtime_root=runtime
    )
    ledger = load_replay_ledger(paths, now_ms=NOW + 10)

    assert completed.status == replay.status == "COMPLETED"
    assert replay.candidate.observed_at_ms == NOW + 10
    assert replay_transport.calls == 0
    assert first.invocation_id in ledger["entries"]


def test_older_candidate_cannot_satisfy_completed_replay(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    first = _invocation(schedule="first", offset=10)
    completed = _call(
        first, repo, runtime, _CountingTransport(), now=NOW + 10
    )
    older = _invocation(schedule="older")
    _seed_direct(
        older, repo, runtime, _CountingTransport(), now=NOW
    )
    replay_transport = _CountingTransport()
    replay = _call(
        first, repo, runtime, replay_transport, now=NOW + 10
    )

    assert completed.status == "COMPLETED"
    assert replay.status == "INDETERMINATE"
    assert replay.reason == "completed_candidate_invalid"
    assert replay_transport.calls == 0


@pytest.mark.parametrize(
    "artifact,payload",
    [
        ("ledger", b"{"),
        (
            "ledger",
            b'{"schema_version":"model_provider_catalog_scheduled_replay_ledger.v1",'
            b'"updated_at_ms":0,"entries":{},"entries":{}}',
        ),
        ("attempt", b"{"),
        ("candidate", b"{"),
    ],
)
def test_malformed_or_duplicate_artifact_fails_closed(
    tmp_path: Path, artifact: str, payload: bytes
) -> None:
    repo, runtime = _roots(tmp_path)
    paths = derive_scheduled_discovery_paths(
        repo_root=repo, runtime_root=runtime
    )
    getattr(paths, f"{artifact}_path").write_bytes(payload)
    transport = _CountingTransport()
    result = _call(_invocation(), repo, runtime, transport)
    assert result.status == "INDETERMINATE"
    assert transport.calls == 0
    assert getattr(paths, f"{artifact}_path").read_bytes() == payload


@pytest.mark.parametrize("artifact", ["ledger", "attempt", "candidate"])
def test_deeply_nested_json_artifact_fails_closed(
    tmp_path: Path, artifact: str
) -> None:
    repo, runtime = _roots(tmp_path)
    paths = derive_scheduled_discovery_paths(
        repo_root=repo, runtime_root=runtime
    )
    payload = b'{"nested":' + (b"[" * 2_000) + b"0" + (
        b"]" * 2_000
    ) + b"}"
    getattr(paths, f"{artifact}_path").write_bytes(payload)
    transport = _CountingTransport()
    result = _call(_invocation(), repo, runtime, transport)

    assert result.status == "INDETERMINATE"
    assert transport.calls == 0


def test_capacity_exhaustion_blocks_before_transport(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    paths = derive_scheduled_discovery_paths(
        repo_root=repo, runtime_root=runtime
    )
    state = empty_replay_ledger()
    for index in range(MAX_LEDGER_ENTRIES):
        invocation = build_discovery_invocation(
            mode="scheduled",
            schedule_id=f"filled-{index}",
            scheduled_for_ms=NOW - 10,
            expires_at_ms=NOW + 100_000,
        )
        state["entries"][invocation.invocation_id] = armed_entry(invocation)
    store = ProviderCatalogArtifactStore.create(
        repo_root=repo, runtime_root=runtime
    )
    save_replay_ledger(paths, state, now_ms=NOW, store=store)
    transport = _CountingTransport()
    result = _call(_invocation(schedule="overflow"), repo, runtime, transport)
    assert result.status == "BLOCKED_PRECALL"
    assert result.reason == "replay_ledger_capacity_exhausted"
    assert transport.calls == 0


def test_repo_contained_runtime_root_blocks_before_transport(
    tmp_path: Path,
) -> None:
    repo, _runtime = _roots(tmp_path)
    transport = _CountingTransport()
    result = _call(_invocation(), repo, repo / "runtime", transport)
    assert result.status == "BLOCKED_PRECALL"
    assert transport.calls == 0


@pytest.mark.parametrize("link_kind", ["symlink", "hardlink"])
def test_linked_ledger_fails_closed(
    tmp_path: Path, link_kind: str
) -> None:
    repo, runtime = _roots(tmp_path)
    paths = derive_scheduled_discovery_paths(
        repo_root=repo, runtime_root=runtime
    )
    source = runtime / "source.json"
    source.write_text("{}", encoding="utf-8")
    try:
        if link_kind == "symlink":
            paths.ledger_path.symlink_to(source)
        else:
            os.link(source, paths.ledger_path)
    except OSError as error:
        pytest.skip(f"{link_kind} unavailable: {error}")
    transport = _CountingTransport()
    result = _call(_invocation(), repo, runtime, transport)
    assert result.status == "INDETERMINATE"
    assert transport.calls == 0


def test_expired_entries_prune_but_expired_invocation_cannot_run(
    tmp_path: Path,
) -> None:
    repo, runtime = _roots(tmp_path)
    paths = derive_scheduled_discovery_paths(
        repo_root=repo, runtime_root=runtime
    )
    expired = build_discovery_invocation(
        mode="scheduled",
        schedule_id="expired",
        scheduled_for_ms=1,
        expires_at_ms=2,
    )
    state = empty_replay_ledger()
    state["entries"][expired.invocation_id] = armed_entry(expired)
    store = ProviderCatalogArtifactStore.create(
        repo_root=repo, runtime_root=runtime
    )
    save_replay_ledger(paths, state, now_ms=1, store=store)
    current = _call(
        _invocation(schedule="current"), repo, runtime, _CountingTransport()
    )
    blocked_transport = _CountingTransport()
    blocked = _call(expired, repo, runtime, blocked_transport)
    ledger = load_replay_ledger(paths, now_ms=NOW)

    assert current.status == "COMPLETED"
    assert expired.invocation_id not in ledger["entries"]
    assert blocked.status == "BLOCKED_PRECALL"
    assert blocked.reason == "scheduled_invocation_expired"
    assert blocked_transport.calls == 0


def test_pruned_ledger_high_water_rejects_wall_clock_rollback(
    tmp_path: Path,
) -> None:
    repo, runtime = _roots(tmp_path)
    paths = derive_scheduled_discovery_paths(
        repo_root=repo, runtime_root=runtime
    )
    expired = build_discovery_invocation(
        mode="scheduled",
        schedule_id="expired-before-prune",
        scheduled_for_ms=1,
        expires_at_ms=2,
    )
    state = empty_replay_ledger()
    state["entries"][expired.invocation_id] = armed_entry(expired)
    store = ProviderCatalogArtifactStore.create(
        repo_root=repo, runtime_root=runtime
    )
    save_replay_ledger(paths, state, now_ms=1, store=store)

    pruned = _call(
        _invocation(schedule="pruner"),
        repo,
        runtime,
        _CountingTransport(),
        now=NOW,
    )
    assert pruned.status == "COMPLETED"
    paths.attempt_path.unlink()
    paths.candidate_path.unlink()

    rollback = build_discovery_invocation(
        mode="scheduled",
        schedule_id="rollback",
        scheduled_for_ms=NOW - 10,
        expires_at_ms=NOW + 100,
    )
    transport = _CountingTransport()
    result = _call(
        rollback, repo, runtime, transport, now=NOW - 1
    )

    assert result.status == "INDETERMINATE"
    assert result.reason == "replay_state_invalid"
    assert transport.calls == 0


def test_ledger_never_persists_raw_provider_secret(tmp_path: Path) -> None:
    class SecretErrorTransport:
        async def fetch(self, _request):
            raise RuntimeError("Bearer sk-secret-should-not-persist")

    repo, runtime = _roots(tmp_path)
    result = _call(_invocation(), repo, runtime, SecretErrorTransport())
    assert result.status == "FAILED"
    paths = derive_scheduled_discovery_paths(
        repo_root=repo, runtime_root=runtime
    )
    text = paths.ledger_path.read_text(encoding="utf-8")
    assert "sk-secret-should-not-persist" not in text
    assert "Bearer" not in text
