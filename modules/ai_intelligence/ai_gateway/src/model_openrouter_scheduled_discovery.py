"""Scheduled-only replay guard for direct OpenRouter catalog discovery."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from modules.ai_intelligence.ai_gateway.src.model_openrouter_direct_discovery import (
    AsyncHTTPProtocol,
    DiscoveryRunResult,
    discover_openrouter_model_catalog,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_artifact_store import (
    AtomicArtifactOps,
    ProviderCatalogArtifactStore,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_replay_state import (
    MAX_LEDGER_ENTRIES,
    ReplayStateError,
    ScheduledDiscoveryPaths,
    armed_entry,
    derive_scheduled_discovery_paths,
    load_replay_ledger,
    prune_expired_entries,
    read_attempt_receipt,
    read_candidate_snapshot,
    receipt_entry,
    save_replay_ledger,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_snapshot import (
    DiscoveryInvocation,
    DiscoveryReceipt,
    ProviderCatalogCandidateSnapshot,
    admit_discovery_invocation,
    rehydrate_discovery_invocation,
    rehydrate_discovery_receipt,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)


@dataclass(frozen=True)
class ScheduledDiscoveryResult:
    """Truthful scheduled admission/replay result."""

    status: str
    reason: str
    replayed: bool
    receipt: DiscoveryReceipt | None
    candidate: ProviderCatalogCandidateSnapshot | None
    attempt_path: Path | None
    candidate_path: Path | None
    ledger_path: Path | None


async def discover_scheduled_openrouter_model_catalog(
    invocation: DiscoveryInvocation,
    *,
    repo_root: Path | str,
    runtime_root: Path | str,
    transport: AsyncHTTPProtocol | None = None,
    clock_ms: Callable[[], int] | None = None,
    artifact_ops: AtomicArtifactOps | None = None,
) -> ScheduledDiscoveryResult:
    """Run the entire synchronous cross-process section in one worker thread."""

    return await asyncio.to_thread(
        _run_scheduled_discovery,
        invocation,
        repo_root,
        runtime_root,
        transport,
        clock_ms or _clock_ms,
        artifact_ops,
    )


def _run_scheduled_discovery(
    invocation: DiscoveryInvocation,
    repo_root: Path | str,
    runtime_root: Path | str,
    transport: AsyncHTTPProtocol | None,
    clock: Callable[[], int],
    artifact_ops: AtomicArtifactOps | None,
) -> ScheduledDiscoveryResult:
    try:
        paths = derive_scheduled_discovery_paths(
            repo_root=repo_root, runtime_root=runtime_root
        )
    except (OSError, ValueError):
        return _result("BLOCKED_PRECALL", "runtime_path_invalid")
    now = clock()
    try:
        item = _scheduled_invocation(invocation, now)
    except ValueError as error:
        return _result(
            "BLOCKED_PRECALL", _admission_reason(error), paths=paths
        )
    try:
        store = ProviderCatalogArtifactStore.create(
            repo_root=repo_root,
            runtime_root=paths.runtime_root,
            ops=artifact_ops,
        )
        with runtime_operation_lock(paths.guard_identity):
            locked_now = clock()
            try:
                item = _scheduled_invocation(item, locked_now)
            except ValueError as error:
                return _result(
                    "BLOCKED_PRECALL",
                    _admission_reason(error),
                    paths=paths,
                )
            return _run_under_lock(
                item,
                locked_now,
                paths,
                store,
                transport,
                clock,
                artifact_ops,
            )
    except (OSError, ReplayStateError, ValueError):
        return _result("INDETERMINATE", "replay_state_invalid", paths=paths)


def _run_under_lock(
    invocation: DiscoveryInvocation,
    now: int,
    paths: ScheduledDiscoveryPaths,
    store: ProviderCatalogArtifactStore,
    transport: AsyncHTTPProtocol | None,
    clock: Callable[[], int],
    artifact_ops: AtomicArtifactOps | None,
) -> ScheduledDiscoveryResult:
    state = load_replay_ledger(paths, now_ms=now)
    if prune_expired_entries(state, now_ms=now):
        try:
            save_replay_ledger(paths, state, now_ms=now, store=store)
        except (OSError, ValueError):
            return _result(
                "INDETERMINATE", "pruned_ledger_write_failed", paths=paths
            )
    attempt = read_attempt_receipt(paths)
    candidate = read_candidate_snapshot(
        paths, now_ms=now, require_fresh=False
    )
    entry = state["entries"].get(invocation.invocation_id)
    decision = _existing_decision(
        invocation,
        entry,
        attempt,
        candidate,
        now,
        paths,
        state,
        store,
    )
    if decision is not None:
        return decision
    if entry is None and len(state["entries"]) >= MAX_LEDGER_ENTRIES:
        return _result(
            "BLOCKED_PRECALL", "replay_ledger_capacity_exhausted", paths=paths
        )
    return _arm_and_execute(
        invocation, now, paths, state, store, transport, clock, artifact_ops
    )


def _existing_decision(
    invocation: DiscoveryInvocation,
    entry: dict | None,
    attempt: DiscoveryReceipt | None,
    candidate: ProviderCatalogCandidateSnapshot | None,
    now: int,
    paths: ScheduledDiscoveryPaths,
    state: dict,
    store: ProviderCatalogArtifactStore,
) -> ScheduledDiscoveryResult | None:
    if entry is not None and entry["status"] != "ARMED":
        receipt = _entry_receipt(entry)
        if entry["status"] == "BLOCKED_PRECALL":
            return None
        return _terminal_replay(receipt, candidate, now, paths)
    if entry is not None:
        return _recover_armed(
            invocation, attempt, candidate, now, paths, state, store
        )
    return _preledger_decision(
        invocation, attempt, candidate, now, paths, state, store
    )


def _preledger_decision(
    invocation: DiscoveryInvocation,
    attempt: DiscoveryReceipt | None,
    candidate: ProviderCatalogCandidateSnapshot | None,
    now: int,
    paths: ScheduledDiscoveryPaths,
    state: dict,
    store: ProviderCatalogArtifactStore,
) -> ScheduledDiscoveryResult | None:
    exact_attempt = (
        attempt is not None
        and attempt.invocation.invocation_id == invocation.invocation_id
    )
    if exact_attempt:
        if attempt.outcome in {"COMPLETED", "FAILED"}:
            return _adopt_attempt(
                attempt, candidate, now, paths, state, store
            )
        return _result(
            "INDETERMINATE",
            "preledger_nonterminal_attempt",
            paths=paths,
        )
    if attempt is None and candidate is None:
        return None
    if attempt is None:
        return _result(
            "INDETERMINATE",
            "candidate_without_terminal_attempt",
            paths=paths,
        )
    if not _legacy_evidence_precedes(invocation, attempt, candidate):
        return _result(
            "INDETERMINATE",
            "preledger_evidence_not_prior",
            paths=paths,
        )
    return None


def _legacy_evidence_precedes(
    invocation: DiscoveryInvocation,
    attempt: DiscoveryReceipt | None,
    candidate: ProviderCatalogCandidateSnapshot | None,
) -> bool:
    """Prove fixed pre-guard evidence predates this invocation's window."""

    scheduled_for = invocation.scheduled_for_ms
    if scheduled_for is None or attempt is None:
        return False
    if attempt.completed_at_ms >= scheduled_for:
        return False
    if candidate is not None and candidate.observed_at_ms >= scheduled_for:
        return False
    if attempt.outcome == "COMPLETED":
        return _candidate_follows_receipt(attempt, candidate)
    return True


def _recover_armed(
    invocation: DiscoveryInvocation,
    attempt: DiscoveryReceipt | None,
    candidate: ProviderCatalogCandidateSnapshot | None,
    now: int,
    paths: ScheduledDiscoveryPaths,
    state: dict,
    store: ProviderCatalogArtifactStore,
) -> ScheduledDiscoveryResult | None:
    if (
        attempt is None
        or attempt.invocation.invocation_id != invocation.invocation_id
    ):
        return _result("INDETERMINATE", "armed_without_terminal", paths=paths)
    if attempt.outcome == "BLOCKED_PRECALL" and not attempt.attempted:
        return None
    return _adopt_attempt(attempt, candidate, now, paths, state, store)


def _adopt_attempt(
    receipt: DiscoveryReceipt,
    candidate: ProviderCatalogCandidateSnapshot | None,
    now: int,
    paths: ScheduledDiscoveryPaths,
    state: dict,
    store: ProviderCatalogArtifactStore,
) -> ScheduledDiscoveryResult:
    if receipt.outcome == "COMPLETED" and not _reusable_candidate(
        receipt, candidate, now
    ):
        return _result(
            "INDETERMINATE", "completed_candidate_invalid", paths=paths
        )
    state["entries"][receipt.invocation.invocation_id] = receipt_entry(receipt)
    try:
        save_replay_ledger(paths, state, now_ms=now, store=store)
    except (OSError, ValueError):
        return _result(
            "INDETERMINATE", "terminal_ledger_write_failed", paths=paths
        )
    return _terminal_replay(receipt, candidate, now, paths)


def _terminal_replay(
    receipt: DiscoveryReceipt,
    candidate: ProviderCatalogCandidateSnapshot | None,
    now: int,
    paths: ScheduledDiscoveryPaths,
) -> ScheduledDiscoveryResult:
    if receipt.outcome == "COMPLETED":
        if not _reusable_candidate(receipt, candidate, now):
            return _result(
                "INDETERMINATE", "completed_candidate_invalid", paths=paths
            )
        return _result(
            "COMPLETED",
            "completed_replay",
            paths=paths,
            replayed=True,
            receipt=receipt,
            candidate=candidate,
        )
    return _result(
        receipt.outcome,
        "terminal_replay",
        paths=paths,
        replayed=True,
        receipt=receipt,
    )


def _arm_and_execute(
    invocation: DiscoveryInvocation,
    now: int,
    paths: ScheduledDiscoveryPaths,
    state: dict,
    store: ProviderCatalogArtifactStore,
    transport: AsyncHTTPProtocol | None,
    clock: Callable[[], int],
    artifact_ops: AtomicArtifactOps | None,
) -> ScheduledDiscoveryResult:
    state["entries"][invocation.invocation_id] = armed_entry(invocation)
    try:
        save_replay_ledger(paths, state, now_ms=now, store=store)
    except (OSError, ValueError):
        return _result(
            "BLOCKED_PRECALL", "armed_ledger_write_failed", paths=paths
        )
    direct = asyncio.run(
        discover_openrouter_model_catalog(
            invocation,
            repo_root=store.repo_root,
            runtime_root=paths.runtime_root,
            attempt_path=paths.attempt_path,
            candidate_path=paths.candidate_path,
            transport=transport,
            clock_ms=clock,
            artifact_ops=artifact_ops,
        )
    )
    return _publish_terminal(direct, now, paths, state, store)


def _publish_terminal(
    direct: DiscoveryRunResult,
    now: int,
    paths: ScheduledDiscoveryPaths,
    state: dict,
    store: ProviderCatalogArtifactStore,
) -> ScheduledDiscoveryResult:
    receipt = rehydrate_discovery_receipt(direct.receipt.to_dict())
    state["entries"][receipt.invocation.invocation_id] = receipt_entry(receipt)
    try:
        save_replay_ledger(paths, state, now_ms=now, store=store)
    except (OSError, ValueError):
        return _result(
            "INDETERMINATE",
            "terminal_ledger_write_failed",
            paths=paths,
            receipt=receipt,
        )
    return _result(
        receipt.outcome,
        receipt.reason,
        paths=paths,
        receipt=receipt,
        candidate=direct.candidate,
    )


def _reusable_candidate(
    receipt: DiscoveryReceipt,
    candidate: ProviderCatalogCandidateSnapshot | None,
    now: int,
) -> bool:
    if candidate is None or now > candidate.fresh_until_ms:
        return False
    return _candidate_follows_receipt(receipt, candidate)


def _candidate_follows_receipt(
    receipt: DiscoveryReceipt,
    candidate: ProviderCatalogCandidateSnapshot | None,
) -> bool:
    if candidate is None:
        return False
    observation = candidate.observation_receipt
    if observation.receipt_id == receipt.receipt_id:
        return (
            observation.invocation.invocation_id
            == receipt.invocation.invocation_id
        )
    return candidate.observed_at_ms > receipt.completed_at_ms


def _entry_receipt(entry: dict) -> DiscoveryReceipt:
    try:
        return rehydrate_discovery_receipt(entry["receipt"])
    except (TypeError, ValueError) as error:
        raise ReplayStateError("scheduled_replay_entry_invalid") from error


def _scheduled_invocation(
    invocation: DiscoveryInvocation, now: int
) -> DiscoveryInvocation:
    if type(invocation) is not DiscoveryInvocation:
        raise ValueError("scheduled_invocation_invalid")
    item = rehydrate_discovery_invocation(invocation.to_dict())
    if item.mode != "scheduled":
        raise ValueError("scheduled_invocation_required")
    admit_discovery_invocation(item, now_ms=now)
    return item


def _admission_reason(error: ValueError) -> str:
    reason = str(error)
    if reason in {
        "scheduled_invocation_not_due",
        "scheduled_invocation_expired",
        "scheduled_invocation_required",
    }:
        return reason
    return "scheduled_invocation_invalid"


def _result(
    status: str,
    reason: str,
    *,
    paths: ScheduledDiscoveryPaths | None = None,
    replayed: bool = False,
    receipt: DiscoveryReceipt | None = None,
    candidate: ProviderCatalogCandidateSnapshot | None = None,
) -> ScheduledDiscoveryResult:
    return ScheduledDiscoveryResult(
        status,
        reason,
        replayed,
        receipt,
        candidate,
        paths.attempt_path if paths else None,
        paths.candidate_path if paths else None,
        paths.ledger_path if paths else None,
    )


def _clock_ms() -> int:
    return time.time_ns() // 1_000_000


__all__ = [
    "ScheduledDiscoveryResult",
    "discover_scheduled_openrouter_model_catalog",
]
