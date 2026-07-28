"""Tests for RedDog authoritative work-state refresh runtime."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_refresh_runtime import (
    AUTHORITATIVE_REFRESH_APPLIED,
    AUTHORITATIVE_REFRESH_REJECTED,
    WRE_QUEUE_SYNCED,
    AtomicJsonAuthoritativeWorkStateStore,
    InMemoryAuthoritativeWorkStateStore,
    build_runtime_source_snapshot,
    refresh_authoritative_work_state_runtime,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_authoritative_work_state_refresh_runtime.py"
)
NOW = "2026-07-14T00:00:00+00:00"


ACTIVE_LEDGER = """# Active Slice Ledger

**Updated**: 2026-07-14T00:00:00+00:00

## Open Slices

| Slice | Priority | Blocked By | Notes |
|-------|----------|------------|-------|
| `REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_RUNTIME_PHASE1` | P0 | - | runtime refresh |

## Next Priority Order

1. **REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_RUNTIME_PHASE1** - runtime refresh
"""


WORK_LEDGER = {
    "schema_version": "1.0.0",
    "last_updated": NOW,
    "slices": [
        {
            "slice_id": "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_RUNTIME_PHASE1",
            "title": "Authoritative work-state refresh runtime",
            "status": "IN_PROGRESS",
            "priority": "P0",
            "source": "audit",
            "lane": "A",
            "created_at": NOW,
            "evidence_docs": ["docs/audits/architecture/REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_RUNTIME_PHASE1.md"],
            "wsp15_score": {"total": 18},
        },
        {
            "slice_id": "REDDOG_SIGNER_AND_DELEGATED_AUTHORITY_RUNTIME_PHASE1",
            "title": "Signer runtime",
            "status": "BLOCKED",
            "priority": "P0",
            "source": "audit",
            "created_at": NOW,
            "blocked_by": ["REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_RUNTIME_PHASE1"],
            "wsp15_score": {"total": 17},
        },
    ],
}


GITHUB_RECORDS = [
    {
        "slice_id": "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_RUNTIME_PHASE1",
        "status": "PR_OPEN",
        "priority": "P0",
        "lane": "A",
        "pr_number": 1001,
        "head_commit": "73637fef2f4e540f032760c67c4dc334aaee16af",
        "evidence_refs": ["github:pr:1001"],
        "wsp15_score": {"total": 18},
    }
]


W10_RECORDS = [
    {
        "slice_id": "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_RUNTIME_PHASE1",
        "status": "STAGED_FOR_W10",
        "priority": "P0",
        "lane": "A",
        "evidence_refs": ["w10:gate:clean"],
        "wsp15_score": {"total": 18},
    }
]


def _refresh(
    store: InMemoryAuthoritativeWorkStateStore,
    **overrides: object,
):
    kwargs = {
        "active_slice_ledger_markdown": ACTIVE_LEDGER,
        "work_ledger_json": json.dumps(WORK_LEDGER),
        "github_pr_records": GITHUB_RECORDS,
        "w10_report_records": W10_RECORDS,
        "store": store,
        "worker_id": "reddog-0102",
        "now_iso": NOW,
    }
    kwargs.update(overrides)
    return refresh_authoritative_work_state_runtime(**kwargs)  # type: ignore[arg-type]


def test_runtime_refresh_commits_authoritative_snapshot_claim_and_wre_queue_item() -> None:
    store = InMemoryAuthoritativeWorkStateStore()

    result = _refresh(store)

    assert result.accepted is True
    assert result.receipt.status == AUTHORITATIVE_REFRESH_APPLIED
    assert result.freshness_receipt is not None and result.freshness_receipt.fresh is True
    assert result.queue_sync_receipt is not None
    assert result.queue_sync_receipt.status == WRE_QUEUE_SYNCED
    snapshot = store.load()
    assert snapshot["schema_version"] == "reddog_authoritative_work_state.v1"
    assert snapshot["selected_slice"] == "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_RUNTIME_PHASE1"
    assert snapshot["worker_claims"][0]["slice_id"] == "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_RUNTIME_PHASE1"
    assert snapshot["worker_claims"][0]["worker_id"] == "reddog-0102"
    assert snapshot["wre_queue_items"][0]["claim_id"] == snapshot["worker_claims"][0]["claim_id"]
    assert snapshot["wre_queue_items"][0]["no_execution_performed"] is True
    allocation = snapshot["wre_queue_items"][0]["wsp15_allocation_receipt"]
    assert allocation["schema_version"] == "reddog_wsp15_allocation_receipt.v1"
    assert allocation["receipt_id"].startswith("sha256:")
    assert allocation["mps_total"] >= 16
    assert allocation["priority"] == "P0"
    assert allocation["reasoning_tier"] == "ULTRA"
    assert f"wsp15_allocation:{allocation['receipt_id']}" in snapshot["wre_queue_items"][0]["evidence_refs"]
    assert snapshot["no_holoindex_mutation_performed"] is True
    assert snapshot["no_worker_spawn_performed"] is True
    assert snapshot["no_execution_performed"] is True


def test_refresh_receipt_and_revision_are_deterministic_for_same_inputs() -> None:
    first = _refresh(InMemoryAuthoritativeWorkStateStore())
    second = _refresh(InMemoryAuthoritativeWorkStateStore())

    assert first.receipt.refresh_id == second.receipt.refresh_id
    assert first.receipt.committed_revision == second.receipt.committed_revision


def test_stale_observed_sources_reject_before_commit() -> None:
    store = InMemoryAuthoritativeWorkStateStore()

    result = _refresh(
        store,
        source_observed_at={
            "ACTIVE_SLICE_LEDGER": "2026-07-13T22:00:00+00:00",
            "work_ledger.example.json": NOW,
            "GITHUB_PULL_REQUESTS": NOW,
            "W10_GATE_REPORTS": NOW,
        },
        max_source_age_seconds=60,
    )

    assert result.accepted is False
    assert result.receipt.status == AUTHORITATIVE_REFRESH_REJECTED
    assert any(reason.startswith("stale_source:ACTIVE_SLICE_LEDGER") for reason in result.receipt.rejection_reasons)
    assert store.load() == {}


def test_closed_open_conflict_rejects_before_durable_claim() -> None:
    store = InMemoryAuthoritativeWorkStateStore()
    github_closed = [{**GITHUB_RECORDS[0], "status": "MERGED"}]

    result = _refresh(store, github_pr_records=github_closed)

    assert result.accepted is False
    assert "lane_state_conflict" in result.receipt.rejection_reasons
    assert (
        "conflict:REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_RUNTIME_PHASE1"
        in result.receipt.rejection_reasons
    )
    assert store.load() == {}


def test_duplicate_active_claim_rejects_without_appending_queue_item() -> None:
    initial = {
        "revision": "rev-1",
        "worker_claims": [
            {
                "claim_id": "existing",
                "slice_id": "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_RUNTIME_PHASE1",
                "worker_id": "worker-a",
                "status": "ACTIVE",
            }
        ],
        "wre_queue_items": [],
    }
    store = InMemoryAuthoritativeWorkStateStore(initial)

    result = _refresh(store)

    assert result.accepted is False
    assert "durable_worker_claim_already_exists" in result.receipt.rejection_reasons
    assert store.load()["worker_claims"][0]["claim_id"] == "existing"
    assert store.load()["wre_queue_items"] == []


def test_refresh_preserves_architect_fix_replay_and_publication_history() -> None:
    promotion = {
        "publication_id": "sha256:" + "a" * 64,
        "proposal_authenticity_attestation_id": "attestation:1",
    }
    publication = {
        "publication_id": promotion["publication_id"],
        "state": "COMMITTED",
    }
    store = InMemoryAuthoritativeWorkStateStore(
        {
            "revision": "rev-1",
            "worker_claims": [],
            "wre_queue_items": [],
            "architect_fix_promotions": [promotion],
            "architect_fix_publications": [publication],
        }
    )

    result = _refresh(store)

    assert result.accepted is True
    snapshot = store.load()
    assert snapshot["architect_fix_promotions"] == [promotion]
    assert snapshot["architect_fix_publications"] == [publication]


def test_refresh_rejects_while_architect_fix_publication_is_pending() -> None:
    store = InMemoryAuthoritativeWorkStateStore(
        {
            "revision": "rev-1",
            "worker_claims": [],
            "wre_queue_items": [],
            "architect_fix_publications": [
                {
                    "publication_id": "sha256:" + "a" * 64,
                    "state": "STATE_PREPARED",
                }
            ],
        }
    )

    result = _refresh(store)

    assert result.accepted is False
    assert "architect_fix_publication_pending" in result.receipt.rejection_reasons
    assert store.load()["revision"] == "rev-1"


def test_commit_failure_is_fail_closed_and_returns_no_authority() -> None:
    store = InMemoryAuthoritativeWorkStateStore(fail_commit=True)

    result = _refresh(store)

    assert result.accepted is False
    assert "atomic_commit_failed" in result.receipt.rejection_reasons
    assert result.receipt.durable_claim_id is None
    assert result.receipt.committed_revision is None


def test_atomic_json_store_writes_single_authoritative_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "authoritative_work_state.json"
    store = AtomicJsonAuthoritativeWorkStateStore(
        path,
        allowed_root=tmp_path,
        repo_root=tmp_path.parent / f"{tmp_path.name}-repo",
    )

    result = _refresh(store)

    assert result.accepted is True
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["revision"] == result.receipt.committed_revision
    assert data["worker_claims"][0]["slice_id"] == "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_RUNTIME_PHASE1"
    assert not list(tmp_path.glob("*.tmp"))


def test_runtime_source_snapshot_rejects_malformed_records_in_freshness() -> None:
    bundle = build_runtime_source_snapshot(
        source_id="GITHUB_PULL_REQUESTS",
        source_type="github_pr",
        records=[{"slice_id": "../../bad", "status": "PR_OPEN"}],
        observed_at=NOW,
    )

    assert bundle.snapshot.records == ()
    assert "record_0_missing_or_invalid_slice_id" in bundle.snapshot.parse_warnings


def test_module_has_no_network_shell_github_holoindex_or_execution_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "holo_index",
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned_import_roots
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in banned_import_roots
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                assert func.id not in banned_calls
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                assert func.value.id not in banned_import_roots
