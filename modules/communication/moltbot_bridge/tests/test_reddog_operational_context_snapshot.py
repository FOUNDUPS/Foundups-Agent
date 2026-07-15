"""Tests for RedDog operational context snapshot runtime."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from holo_index.freshness_receipt import CollectionFreshness, HoloIndexFreshnessReceipt
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    ASSIGNMENT_CONTEXT_STALE,
    ASSIGNMENT_CONTEXT_VALID,
    AUTHORITY_AUTHORITATIVE,
    FRESH,
    MISSING,
    SOURCE_BRAIN,
    SOURCE_HOLOINDEX,
    SOURCE_REPO,
    SOURCE_WORK_STATE,
    SNAPSHOT_ACCEPTED,
    SNAPSHOT_REJECTED,
    build_evidence_bundle,
    build_operational_context_snapshot,
    load_authoritative_work_state,
    observe_repo_state,
    validate_context_before_assignment,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_operational_context_snapshot.py"
)
NOW = "2026-07-14T00:00:00+00:00"
HEAD = "9c31512a8b4d6e1f0a2b3c4d5e6f708192a3b4c5"
REVISION = "sha256:work-state-revision"


def _repo_state(head: str = HEAD):
    return {
        "head_sha": head,
        "dirty_paths": (),
        "dirty_digest": "sha256:clean",
        "worktree_digest": "sha256:worktrees",
    }


def _work_state(revision: str = REVISION):
    return {
        "schema_version": "reddog_authoritative_work_state.v1",
        "revision": revision,
        "selected_slice": "REDDOG_OPERATIONAL_CONTEXT_SNAPSHOT_RUNTIME_PHASE1",
        "refresh_receipt_id": "sha256:refresh",
        "worker_claims": [
            {
                "claim_id": "claim-1",
                "slice_id": "REDDOG_OPERATIONAL_CONTEXT_SNAPSHOT_RUNTIME_PHASE1",
                "worker_id": "reddog",
                "status": "ACTIVE",
            }
        ],
        "wre_queue_items": [
            {
                "queue_item_id": "queue-1",
                "slice_id": "REDDOG_OPERATIONAL_CONTEXT_SNAPSHOT_RUNTIME_PHASE1",
                "claim_id": "claim-1",
            }
        ],
    }


def _fresh_holo_receipt(head: str = HEAD):
    return HoloIndexFreshnessReceipt(
        schema_version="holoindex_freshness_receipt.v1",
        generated_at=NOW,
        repo_root=str(REPO_ROOT),
        repo_head_sha=head,
        ssd_path="E:/HoloIndex",
        source="ci_targeted_reindex",
        generation_id=(
            "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        ),
        collections=[
            CollectionFreshness(
                name="navigation_work_ledger",
                count=3,
                status="indexed",
                source="ci_targeted_reindex",
                repo_head_sha=head,
                last_indexed_at=NOW,
                source_manifest_digest=(
                    "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                ),
                indexed_paths_digest=(
                    "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
                ),
                removed_paths_digest=(
                    "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
                ),
                embedding_backend="test-embedding",
                verification="PASS",
            ),
            CollectionFreshness(
                name="navigation_symbols",
                count=4,
                status="indexed",
                source="ci_targeted_reindex",
                repo_head_sha=head,
                last_indexed_at=NOW,
                source_manifest_digest=(
                    "sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
                ),
                indexed_paths_digest=(
                    "sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
                ),
                removed_paths_digest=(
                    "sha256:9999999999999999999999999999999999999999999999999999999999999999"
                ),
                embedding_backend="test-embedding",
                verification="PASS",
            ),
        ],
    )


def _accepted_snapshot(**overrides):
    kwargs = {
        "repo_state": _repo_state(),
        "work_state_snapshot": _work_state(),
        "holoindex_receipt": _fresh_holo_receipt(),
        "changed_paths": [
            "docs/0102_session_briefings/work_ledger.schema.json",
            "holo_index/adaptive_learning/breadcrumb_tracer.py",
        ],
        "now_iso": NOW,
        "breadcrumbs": [
            {
                "breadcrumb_id": "b1",
                "continuity_id": "cont-1",
                "task_id": "task-1",
                "timestamp": NOW,
                "body": "raw breadcrumb body with C:/Users/user/secret.txt",
            },
            {
                "breadcrumb_id": "b2",
                "continuity_id": "other",
                "task_id": "other",
                "timestamp": NOW,
            },
        ],
        "breadcrumb_scope": "cont-1",
        "brain_state": {
            "available": True,
            "signature_digest": "sha256:brain",
            "summary": "raw brain transcript sk-test should never appear",
            "repo_head_sha": HEAD,
            "work_state_revision": REVISION,
        },
        "workspace_memory_notes": [
            {
                "note_id": "m1",
                "topic": "lane note",
                "body": "raw workspace note with O:/Foundups-Agent/.env",
            }
        ],
    }
    kwargs.update(overrides)
    return build_operational_context_snapshot(**kwargs)


def test_snapshot_builds_source_receipts_context_view_and_identity_chain() -> None:
    result = _accepted_snapshot()

    assert result.accepted is True
    assert result.status == SNAPSHOT_ACCEPTED
    assert result.snapshot is not None
    assert result.context_view is not None
    snapshot = result.snapshot
    context_view = result.context_view
    assert snapshot.snapshot_content_digest.startswith("sha256:")
    assert snapshot.snapshot_receipt_id.startswith("sha256:")
    assert context_view.snapshot_receipt_id == snapshot.snapshot_receipt_id
    assert context_view.snapshot_content_digest == snapshot.snapshot_content_digest
    assert context_view.context_view_id.startswith("sha256:")
    receipts = {receipt.source: receipt for receipt in snapshot.source_receipts}
    assert receipts[SOURCE_REPO].authority_class == AUTHORITY_AUTHORITATIVE
    assert receipts[SOURCE_REPO].freshness == FRESH
    assert receipts[SOURCE_WORK_STATE].source_version == REVISION
    assert receipts[SOURCE_HOLOINDEX].freshness == FRESH
    assert snapshot.breadcrumbs_state["record_count"] == 1


def test_missing_required_work_state_rejects_before_context_view() -> None:
    result = _accepted_snapshot(work_state_snapshot={"schema_version": "reddog_authoritative_work_state.v1"})

    assert result.accepted is False
    assert result.status == SNAPSHOT_REJECTED
    assert result.snapshot is None
    assert result.context_view is None
    assert "mandatory_source_not_fresh:work_state" in result.rejection_reasons
    assert "work_state:missing_work_state_revision" in result.rejection_reasons


def test_stale_holoindex_receipt_rejects_when_mandatory() -> None:
    result = _accepted_snapshot(holoindex_receipt=_fresh_holo_receipt(head="old-head"))

    assert result.accepted is False
    assert "mandatory_source_not_fresh:holoindex" in result.rejection_reasons
    assert "holoindex:stale_repo_head_sha" in result.rejection_reasons


def test_missing_brain_is_recorded_without_blocking_unrelated_work() -> None:
    result = _accepted_snapshot(brain_state=None)

    assert result.accepted is True
    assert result.snapshot is not None
    receipts = {receipt.source: receipt for receipt in result.snapshot.source_receipts}
    assert receipts[SOURCE_BRAIN].freshness == MISSING
    assert receipts[SOURCE_BRAIN].required is False


def test_bootstrap_and_brain_conflicts_do_not_override_current_authoritative_state() -> None:
    result = _accepted_snapshot(
        bootstrap_projection={
            "repo_head_sha": "stale-bootstrap-head",
            "work_state_revision": "stale-bootstrap-revision",
        },
        brain_state={
            "available": True,
            "signature_digest": "sha256:brain",
            "repo_head_sha": "historical-head",
            "work_state_revision": "historical-revision",
        },
    )

    assert result.accepted is True
    assert result.snapshot is not None
    assert result.snapshot.repo_state["head_sha"] == HEAD
    assert result.snapshot.work_state["revision"] == REVISION
    assert "bootstrap_head_stale" in result.conflicts
    assert "bootstrap_work_state_stale" in result.conflicts
    assert "brain_head_historical_conflict" in result.conflicts
    assert "brain_work_state_historical_conflict" in result.conflicts


def test_context_view_redacts_raw_memory_secrets_and_absolute_paths() -> None:
    result = _accepted_snapshot()

    assert result.context_view is not None
    text = result.context_view.text
    assert "raw breadcrumb body" not in text
    assert "raw brain transcript" not in text
    assert "raw workspace note" not in text
    assert "C:/Users/user" not in text
    assert "O:/Foundups-Agent" not in text
    assert "sk-test" not in text


def test_evidence_bundle_derives_from_snapshot_without_mutating_it() -> None:
    result = _accepted_snapshot()
    assert result.snapshot is not None and result.context_view is not None
    before = result.snapshot.to_dict()

    bundle = build_evidence_bundle(
        snapshot=result.snapshot,
        context_view=result.context_view,
        report_digests=["sha256:repo-audit", "sha256:external-research"],
        external_research_receipts=["sha256:external-source"],
    )

    assert bundle.evidence_bundle_id.startswith("sha256:")
    assert bundle.snapshot_receipt_id == result.snapshot.snapshot_receipt_id
    assert bundle.context_view_id == result.context_view.context_view_id
    assert result.snapshot.to_dict() == before


def test_assignment_gate_rejects_head_work_state_or_breadcrumb_changes() -> None:
    result = _accepted_snapshot()
    assert result.snapshot is not None and result.context_view is not None

    accepted = validate_context_before_assignment(
        snapshot=result.snapshot,
        context_view=result.context_view,
        current_repo_head_sha=HEAD,
        current_work_state_revision=REVISION,
        current_breadcrumb_high_watermark=result.snapshot.breadcrumbs_state["high_watermark"],
        now_iso="2026-07-14T00:01:00+00:00",
    )
    assert accepted.accepted is True
    assert accepted.status == ASSIGNMENT_CONTEXT_VALID

    stale = validate_context_before_assignment(
        snapshot=result.snapshot,
        context_view=result.context_view,
        current_repo_head_sha="new-head",
        current_work_state_revision="new-revision",
        current_breadcrumb_high_watermark="new-breadcrumb-mark",
        now_iso="2026-07-14T00:01:00+00:00",
    )
    assert stale.accepted is False
    assert stale.status == ASSIGNMENT_CONTEXT_STALE
    assert "repo_head_changed" in stale.rejection_reasons
    assert "work_state_revision_changed" in stale.rejection_reasons
    assert "breadcrumb_high_watermark_changed" in stale.rejection_reasons


def test_load_authoritative_work_state_uses_existing_snapshot_file(tmp_path: Path) -> None:
    path = tmp_path / "authoritative_work_state.json"
    path.write_text(json.dumps(_work_state(), sort_keys=True), encoding="utf-8")

    loaded = load_authoritative_work_state(path)

    assert loaded["revision"] == REVISION
    assert loaded["worker_claims"][0]["slice_id"] == "REDDOG_OPERATIONAL_CONTEXT_SNAPSHOT_RUNTIME_PHASE1"


def test_observe_repo_state_reads_head_without_repo_mutation() -> None:
    state = observe_repo_state(REPO_ROOT)

    assert state["head_sha"]
    assert "dirty_digest" in state
    assert "worktree_digest" in state


def test_snapshot_module_has_no_mutating_calls_or_runtime_authority() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_names = {
        "write_freshness_receipt",
        "refresh_authoritative_work_state_runtime",
        "create_autonomous_task",
        "openclaw_supervisor",
        "hermes_job_executor",
    }
    forbidden_attrs = {
        "write_text",
        "commit",
        "mkdir",
        "unlink",
        "remove",
    }
    forbidden_git_words = {"add", "commit", "push", "merge", "checkout", "reset", "restore"}
    source = MODULE_PATH.read_text(encoding="utf-8")
    for name in forbidden_names:
        assert name not in source
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in forbidden_attrs
            if node.func.attr == "replace" and isinstance(node.func.value, ast.Name):
                assert node.func.value.id != "os"
    assert "subprocess.run" in source
    for word in forbidden_git_words:
        assert f'"{word}"' not in source
        assert f"'{word}'" not in source
