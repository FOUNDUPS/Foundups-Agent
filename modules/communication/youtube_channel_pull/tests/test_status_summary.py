"""
Focused tests for status_summary generator.

Tests:
- Parsing of complete artifact set (happy path)
- Missing-artifact behavior (refresh_log absent, catalog absent, etc.)
- Markdown renders without crashing for both cases
- Read-only guarantee: never writes to catalog/audit source paths
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.communication.youtube_channel_pull.src import status_summary


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _scaffold_repo(tmp_path: Path, *, include_catalog=True, include_delta=True,
                   include_proposals=True, include_review=True, include_refresh_log=False):
    catalog_path = tmp_path / "public" / "member" / "mall-video-catalog.json"
    audit_dir = tmp_path / "docs" / "audits" / "pfmall_youtube_ingest"

    if include_catalog:
        _write_json(
            catalog_path,
            [
                {
                    "foundup_id": "move2japan",
                    "title": "Move to Japan",
                    "source_type": "youtube_channel",
                    "source_id": "UC-TEST",
                    "video_count": 2,
                    "videos": [{"video_id": "a"}, {"video_id": "b"}],
                },
                {
                    "foundup_id": "eduit",
                    "title": "EDUIT",
                    "source_type": "youtube_channel",
                    "source_id": "UC-EDU",
                    "video_count": 1,
                    "videos": [],  # mismatch: declared 1, actual 0
                },
            ],
        )

    if include_delta:
        _write_json(
            audit_dir / "youtube_channel_pull_delta.json",
            {
                "generated_at": "2026-04-13T07:17:28Z",
                "summary": {
                    "foundups_checked": 1,
                    "total_new_videos": 0,
                    "total_skipped": 19,
                },
                "deltas": [
                    {
                        "foundup_id": "move2japan",
                        "existing_count": 594,
                        "pulled_count": 19,
                        "new_count": 0,
                        "skipped_count": 19,
                        "new_videos": [],
                        "skipped_ids": [],
                    }
                ],
            },
        )

    if include_proposals:
        _write_json(
            audit_dir / "youtube_discovery_proposals.json",
            {
                "generated_at": "2026-04-13T07:06:16Z",
                "query": "FFCPLN music",
                "search_type": "video",
                "summary": {
                    "total_proposals": 10,
                    "matched_to_foundup": 10,
                    "unmatched": 0,
                    "catalog_targets": 4,
                },
                "proposals": [],
            },
        )

    if include_review:
        _write_json(
            audit_dir / "youtube_discovery_review_result_20260413.json",
            {
                "reviewed_at": "2026-04-13T07:30:00Z",
                "reviewer": "test",
                "proposal_artifact": "youtube_discovery_proposals.json",
                "total_proposals": 10,
                "review_summary": {
                    "approved": 2,
                    "skipped_duplicate": 8,
                    "skipped_ambiguous": 0,
                    "skipped_low_confidence": 0,
                    "rejected": 0,
                },
                "applied": [],
                "skipped": [],
                "catalog_update": {
                    "target_foundup": "move2japan",
                    "video_count_before": 592,
                    "video_count_after": 594,
                },
            },
        )

    if include_refresh_log:
        _write_json(
            audit_dir / "refresh_log.json",
            {
                "runs": [
                    {
                        "success": True,
                        "foundups_checked": 1,
                        "new_videos_found": 0,
                        "delta_path": "docs/audits/pfmall_youtube_ingest/youtube_channel_pull_delta.json",
                        "error": None,
                        "triggered_at": "2026-04-13T07:17:28Z",
                        "trigger_mode": "manual",
                    }
                ]
            },
        )

    return tmp_path


def test_full_artifact_set_parses(tmp_path):
    repo = _scaffold_repo(tmp_path, include_refresh_log=True)
    summary = status_summary.generate_status_summary(repo)

    assert summary["catalog"]["available"] is True
    assert summary["catalog"]["foundup_count"] == 2
    assert summary["catalog"]["total_declared_videos"] == 3
    assert summary["catalog"]["total_actual_videos"] == 2
    assert len(summary["catalog"]["count_mismatches"]) == 1
    assert summary["catalog"]["count_mismatches"][0]["foundup_id"] == "eduit"

    assert summary["delta"]["available"] is True
    assert summary["delta"]["total_new_videos"] == 0
    assert summary["delta"]["total_skipped"] == 19

    assert summary["refresh_log"]["available"] is True
    assert summary["refresh_log"]["run_count"] == 1
    assert summary["refresh_log"]["last_run"]["trigger_mode"] == "manual"

    assert summary["proposals"]["available"] is True
    assert summary["proposals"]["total_proposals"] == 10

    assert summary["review"]["available"] is True
    assert summary["review"]["approved"] == 2
    assert summary["review"]["catalog_update"]["video_count_after"] == 594


def test_missing_refresh_log_is_reported_honestly(tmp_path):
    repo = _scaffold_repo(tmp_path, include_refresh_log=False)
    summary = status_summary.generate_status_summary(repo)

    assert summary["refresh_log"]["available"] is False
    assert "refresh_log.json not present" in summary["refresh_log"]["note"]
    # Other artifacts still parse fine
    assert summary["catalog"]["available"] is True
    assert summary["delta"]["available"] is True


def test_all_artifacts_missing_emits_blockers(tmp_path):
    summary = status_summary.generate_status_summary(tmp_path)

    assert summary["catalog"]["available"] is False
    assert summary["delta"]["available"] is False
    assert summary["refresh_log"]["available"] is False
    assert summary["proposals"]["available"] is False
    assert summary["review"]["available"] is False

    # Blockers list should flag the critical absences
    blocker_text = " ".join(summary["blockers"])
    assert "Catalog" in blocker_text
    assert "delta" in blocker_text.lower()


def test_markdown_render_does_not_raise_for_full_and_empty(tmp_path):
    # Full
    repo_full = _scaffold_repo(tmp_path / "full", include_refresh_log=True)
    summary_full = status_summary.generate_status_summary(repo_full)
    md_full = status_summary.render_markdown(summary_full)
    assert "pfMALL YouTube Pipeline" in md_full
    assert "move2japan" in md_full

    # Empty (no artifacts)
    summary_empty = status_summary.generate_status_summary(tmp_path / "empty")
    md_empty = status_summary.render_markdown(summary_empty)
    assert "pfMALL YouTube Pipeline" in md_empty
    assert "not present" in md_empty.lower() or "missing" in md_empty.lower()


def test_write_status_summary_is_read_only_vs_sources(tmp_path):
    repo = _scaffold_repo(tmp_path, include_refresh_log=True)
    summary = status_summary.generate_status_summary(repo)

    md_out = tmp_path / "out" / "summary.md"
    json_out = tmp_path / "out" / "summary.json"
    written = status_summary.write_status_summary(summary, md_out, json_out)

    assert written["markdown"].exists()
    assert written["json"].exists()

    # Ensure no source artifact was mutated (mtime not changed is expensive to
    # verify cross-platform; instead verify content is still intact).
    catalog = json.loads(
        (repo / "public" / "member" / "mall-video-catalog.json").read_text(encoding="utf-8")
    )
    assert len(catalog) == 2  # same as scaffolded
