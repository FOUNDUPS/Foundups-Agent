#!/usr/bin/env python3
"""
YouTube Pipeline Status Summary Generator (Read-Only).

Parses existing artifacts and emits an operator-facing status summary so
humans can see what ran, what changed, and what needs review without
manually inspecting multiple JSON files.

Artifact sources (read-only):
- public/member/mall-video-catalog.json
- docs/audits/pfmall_youtube_ingest/youtube_channel_pull_delta.json
- docs/audits/pfmall_youtube_ingest/refresh_log.json            (optional)
- docs/audits/pfmall_youtube_ingest/youtube_discovery_proposals.json
- docs/audits/pfmall_youtube_ingest/youtube_discovery_review_result_*.json

Outputs (generated):
- docs/audits/pfmall_youtube_ingest/pipeline_status_summary.md
- docs/audits/pfmall_youtube_ingest/pipeline_status_summary.json

This module performs NO catalog mutation and requires NO live API access.

WSP References:
- WSP 3: Communication domain
- WSP 49: Module structure
- WSP 97: Truthful verification (report missing artifacts honestly)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
CATALOG_PATH = REPO_ROOT / "public" / "member" / "mall-video-catalog.json"
AUDIT_DIR = REPO_ROOT / "docs" / "audits" / "pfmall_youtube_ingest"
DELTA_PATH = AUDIT_DIR / "youtube_channel_pull_delta.json"
REFRESH_LOG_PATH = AUDIT_DIR / "refresh_log.json"
PROPOSALS_PATH = AUDIT_DIR / "youtube_discovery_proposals.json"
SUMMARY_MD_PATH = AUDIT_DIR / "pipeline_status_summary.md"
SUMMARY_JSON_PATH = AUDIT_DIR / "pipeline_status_summary.json"
REVIEW_RESULT_GLOB = "youtube_discovery_review_result_*.json"


def _load_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_parse_error": str(exc)}


def _find_latest_review_result(audit_dir: Path) -> Optional[Path]:
    candidates = sorted(audit_dir.glob(REVIEW_RESULT_GLOB))
    if not candidates:
        return None
    return candidates[-1]


def _catalog_counts(catalog: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    if not isinstance(catalog, list):
        return {"available": False, "error": "catalog missing or not a list"}

    entries: List[Dict[str, Any]] = []
    total_declared = 0
    total_actual = 0
    mismatches: List[Dict[str, Any]] = []
    for entry in catalog:
        fid = entry.get("foundup_id", "?")
        declared = int(entry.get("video_count", 0) or 0)
        videos = entry.get("videos", []) or []
        actual = len(videos)
        total_declared += declared
        total_actual += actual
        entries.append(
            {
                "foundup_id": fid,
                "title": entry.get("title", ""),
                "source_type": entry.get("source_type", ""),
                "source_id": entry.get("source_id", ""),
                "declared_video_count": declared,
                "actual_video_count": actual,
            }
        )
        if declared != actual:
            mismatches.append(
                {"foundup_id": fid, "declared": declared, "actual": actual}
            )

    return {
        "available": True,
        "foundup_count": len(entries),
        "total_declared_videos": total_declared,
        "total_actual_videos": total_actual,
        "count_mismatches": mismatches,
        "entries": entries,
    }


def _delta_status(delta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(delta, dict):
        return {"available": False}
    if "_parse_error" in delta:
        return {"available": False, "error": delta["_parse_error"]}

    summary = delta.get("summary", {}) or {}
    deltas = delta.get("deltas", []) or []
    per_foundup = [
        {
            "foundup_id": d.get("foundup_id"),
            "existing_count": d.get("existing_count"),
            "pulled_count": d.get("pulled_count"),
            "new_count": d.get("new_count"),
            "skipped_count": d.get("skipped_count"),
        }
        for d in deltas
    ]
    return {
        "available": True,
        "generated_at": delta.get("generated_at"),
        "foundups_checked": summary.get("foundups_checked"),
        "total_new_videos": summary.get("total_new_videos"),
        "total_skipped": summary.get("total_skipped"),
        "per_foundup": per_foundup,
    }


def _refresh_log_status(log: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(log, dict):
        return {
            "available": False,
            "note": (
                "refresh_log.json not present; refresh_scheduler has not run "
                "in logged mode yet, or all runs used --no-log."
            ),
        }
    runs = log.get("runs", []) or []
    if not runs:
        return {"available": True, "run_count": 0, "last_run": None}
    last = runs[-1]
    return {
        "available": True,
        "run_count": len(runs),
        "last_run": {
            "triggered_at": last.get("triggered_at"),
            "trigger_mode": last.get("trigger_mode"),
            "success": last.get("success"),
            "foundups_checked": last.get("foundups_checked"),
            "new_videos_found": last.get("new_videos_found"),
            "error": last.get("error"),
        },
    }


def _proposals_status(proposals: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(proposals, dict):
        return {"available": False}
    if "_parse_error" in proposals:
        return {"available": False, "error": proposals["_parse_error"]}

    summary = proposals.get("summary", {}) or {}
    return {
        "available": True,
        "generated_at": proposals.get("generated_at"),
        "query": proposals.get("query"),
        "search_type": proposals.get("search_type"),
        "total_proposals": summary.get("total_proposals"),
        "matched_to_foundup": summary.get("matched_to_foundup"),
        "unmatched": summary.get("unmatched"),
        "catalog_targets": summary.get("catalog_targets"),
    }


def _review_status(review: Optional[Dict[str, Any]], source: Optional[Path]) -> Dict[str, Any]:
    if not isinstance(review, dict):
        return {"available": False}
    if "_parse_error" in review:
        return {"available": False, "error": review["_parse_error"]}

    rs = review.get("review_summary", {}) or {}
    cu = review.get("catalog_update", {}) or {}
    return {
        "available": True,
        "source_file": source.name if source else None,
        "reviewed_at": review.get("reviewed_at"),
        "reviewer": review.get("reviewer"),
        "proposal_artifact": review.get("proposal_artifact"),
        "total_proposals": review.get("total_proposals"),
        "approved": rs.get("approved"),
        "skipped_duplicate": rs.get("skipped_duplicate"),
        "skipped_ambiguous": rs.get("skipped_ambiguous"),
        "skipped_low_confidence": rs.get("skipped_low_confidence"),
        "rejected": rs.get("rejected"),
        "catalog_update": {
            "target_foundup": cu.get("target_foundup"),
            "video_count_before": cu.get("video_count_before"),
            "video_count_after": cu.get("video_count_after"),
        },
    }


def _determine_blockers_and_next_action(summary: Dict[str, Any]) -> Dict[str, Any]:
    blockers: List[str] = []
    next_actions: List[str] = []

    if not summary["catalog"]["available"]:
        blockers.append("Catalog missing or unreadable.")
        next_actions.append("Restore public/member/mall-video-catalog.json.")

    if not summary["delta"]["available"]:
        blockers.append("Known-channel delta artifact missing.")
        next_actions.append(
            "Run: python -m modules.communication.youtube_channel_pull.src.refresh_scheduler"
        )
    else:
        total_new = summary["delta"].get("total_new_videos") or 0
        if total_new > 0:
            next_actions.append(
                f"Review {total_new} new known-channel candidate(s) in "
                "youtube_channel_pull_delta.json and apply if relevant."
            )
        else:
            next_actions.append(
                "Known-channel delta shows 0 new videos - no action required."
            )

    if not summary["refresh_log"]["available"]:
        next_actions.append(
            "Run refresh_scheduler at least once with logging enabled to "
            "populate refresh_log.json (drop --no-log)."
        )

    if summary["proposals"]["available"]:
        total_prop = summary["proposals"].get("total_proposals") or 0
        reviewed = summary["review"].get("total_proposals") if summary["review"]["available"] else None
        proposals_gen = summary["proposals"].get("generated_at")
        review_gen = summary["review"].get("reviewed_at") if summary["review"]["available"] else None
        if not summary["review"]["available"]:
            next_actions.append(
                f"{total_prop} discovery proposal(s) exist with no review artifact - operator review required."
            )
        elif reviewed != total_prop:
            next_actions.append(
                f"Latest review covers {reviewed}/{total_prop} proposals - verify pending items."
            )
        elif proposals_gen and review_gen and review_gen < proposals_gen:
            next_actions.append(
                "Latest review predates latest proposals - re-review required."
            )

    mismatches = summary["catalog"].get("count_mismatches") if summary["catalog"]["available"] else []
    if mismatches:
        blockers.append(
            f"{len(mismatches)} FoundUp(s) have declared video_count != actual videos[] length."
        )
        next_actions.append("Reconcile declared vs actual video counts in catalog.")

    return {"blockers": blockers, "next_actions": next_actions}


def generate_status_summary(repo_root: Path = REPO_ROOT) -> Dict[str, Any]:
    """Build the pipeline status summary dict from existing artifacts only.

    Read-only. No catalog mutation. No live API calls.
    """
    catalog_path = repo_root / "public" / "member" / "mall-video-catalog.json"
    audit_dir = repo_root / "docs" / "audits" / "pfmall_youtube_ingest"
    delta_path = audit_dir / "youtube_channel_pull_delta.json"
    refresh_log_path = audit_dir / "refresh_log.json"
    proposals_path = audit_dir / "youtube_discovery_proposals.json"

    catalog = _load_json(catalog_path)
    delta = _load_json(delta_path)
    refresh_log = _load_json(refresh_log_path)
    proposals = _load_json(proposals_path)
    latest_review_path = _find_latest_review_result(audit_dir)
    review = _load_json(latest_review_path) if latest_review_path else None

    summary: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "status_summary.generate_status_summary",
        "read_only": True,
        "sources": {
            "catalog": str(catalog_path.relative_to(repo_root)) if catalog_path.exists() else None,
            "delta": str(delta_path.relative_to(repo_root)) if delta_path.exists() else None,
            "refresh_log": str(refresh_log_path.relative_to(repo_root)) if refresh_log_path.exists() else None,
            "proposals": str(proposals_path.relative_to(repo_root)) if proposals_path.exists() else None,
            "latest_review": str(latest_review_path.relative_to(repo_root)) if latest_review_path else None,
        },
        "catalog": _catalog_counts(catalog),
        "delta": _delta_status(delta),
        "refresh_log": _refresh_log_status(refresh_log),
        "proposals": _proposals_status(proposals),
        "review": _review_status(review, latest_review_path),
    }
    summary.update(_determine_blockers_and_next_action(summary))
    return summary


def render_markdown(summary: Dict[str, Any]) -> str:
    """Render the summary dict as an operator-facing markdown document."""
    lines: List[str] = []
    lines.append("# pfMALL YouTube Pipeline - Status Summary")
    lines.append("")
    lines.append(f"- Generated: `{summary['generated_at']}`")
    lines.append("- Read-only: yes (no catalog mutation, no live API calls)")
    lines.append("- Generator: `modules/communication/youtube_channel_pull/src/status_summary.py`")
    lines.append("")

    # Sources
    lines.append("## Sources")
    lines.append("")
    lines.append("| Artifact | Path |")
    lines.append("|---|---|")
    for label, key in [
        ("Catalog", "catalog"),
        ("Known-channel delta", "delta"),
        ("Refresh log", "refresh_log"),
        ("Discovery proposals", "proposals"),
        ("Latest discovery review", "latest_review"),
    ]:
        path = summary["sources"].get(key)
        shown = f"`{path}`" if path else "_missing_"
        lines.append(f"| {label} | {shown} |")
    lines.append("")

    # Catalog
    lines.append("## 1. Catalog State")
    lines.append("")
    cat = summary["catalog"]
    if not cat["available"]:
        lines.append(f"Catalog unavailable: {cat.get('error', 'unknown error')}")
    else:
        lines.append(f"- FoundUps: **{cat['foundup_count']}**")
        lines.append(f"- Total declared videos: **{cat['total_declared_videos']}**")
        lines.append(f"- Total actual videos (sum of `videos[]`): **{cat['total_actual_videos']}**")
        if cat["count_mismatches"]:
            lines.append(
                f"- Count mismatches: **{len(cat['count_mismatches'])}** (declared != actual)"
            )
        else:
            lines.append("- Count mismatches: none")
        lines.append("")
        lines.append("| foundup_id | title | source_type | declared | actual |")
        lines.append("|---|---|---|---:|---:|")
        for e in cat["entries"]:
            lines.append(
                f"| {e['foundup_id']} | {e['title']} | {e['source_type']} | "
                f"{e['declared_video_count']} | {e['actual_video_count']} |"
            )
    lines.append("")

    # Delta
    lines.append("## 2. Latest Known-Channel Refresh (Delta)")
    lines.append("")
    delta = summary["delta"]
    if not delta["available"]:
        lines.append("Delta artifact not present - run `refresh_scheduler` to generate one.")
    else:
        lines.append(f"- Generated: `{delta.get('generated_at', 'unknown')}`")
        lines.append(f"- FoundUps checked: **{delta.get('foundups_checked', 0)}**")
        lines.append(f"- New videos: **{delta.get('total_new_videos', 0)}**")
        lines.append(f"- Skipped (already in catalog): **{delta.get('total_skipped', 0)}**")
        lines.append("")
        if delta.get("per_foundup"):
            lines.append("| foundup_id | existing | pulled | new | skipped |")
            lines.append("|---|---:|---:|---:|---:|")
            for row in delta["per_foundup"]:
                lines.append(
                    f"| {row.get('foundup_id')} | {row.get('existing_count')} | "
                    f"{row.get('pulled_count')} | {row.get('new_count')} | "
                    f"{row.get('skipped_count')} |"
                )
    lines.append("")

    # Refresh log
    lines.append("## 3. Refresh Scheduler Log")
    lines.append("")
    rl = summary["refresh_log"]
    if not rl["available"]:
        lines.append(f"_{rl.get('note', 'refresh_log.json not present')}_")
    else:
        lines.append(f"- Total logged runs: **{rl.get('run_count', 0)}**")
        last = rl.get("last_run")
        if last:
            lines.append(f"- Last run at: `{last.get('triggered_at')}`")
            lines.append(f"- Trigger mode: `{last.get('trigger_mode')}`")
            lines.append(f"- Success: `{last.get('success')}`")
            lines.append(f"- FoundUps checked: {last.get('foundups_checked')}")
            lines.append(f"- New videos found: {last.get('new_videos_found')}")
            if last.get("error"):
                lines.append(f"- Error: `{last['error']}`")
    lines.append("")

    # Proposals
    lines.append("## 4. Discovery Proposals")
    lines.append("")
    prop = summary["proposals"]
    if not prop["available"]:
        lines.append("No discovery proposals artifact present.")
    else:
        lines.append(f"- Generated: `{prop.get('generated_at', 'unknown')}`")
        lines.append(f"- Query: `{prop.get('query')}`")
        lines.append(f"- Search type: `{prop.get('search_type')}`")
        lines.append(f"- Total proposals: **{prop.get('total_proposals', 0)}**")
        lines.append(f"- Matched to a FoundUp: **{prop.get('matched_to_foundup', 0)}**")
        lines.append(f"- Unmatched: **{prop.get('unmatched', 0)}**")
        lines.append(f"- Distinct catalog targets: **{prop.get('catalog_targets', 0)}**")
    lines.append("")

    # Review
    lines.append("## 5. Latest Discovery Review")
    lines.append("")
    rev = summary["review"]
    if not rev["available"]:
        lines.append("No discovery review artifact found.")
    else:
        lines.append(f"- Source: `{rev.get('source_file')}`")
        lines.append(f"- Reviewed at: `{rev.get('reviewed_at')}`")
        lines.append(f"- Reviewer: `{rev.get('reviewer')}`")
        lines.append(f"- Proposal artifact reviewed: `{rev.get('proposal_artifact')}`")
        lines.append(f"- Total proposals covered: **{rev.get('total_proposals', 0)}**")
        lines.append(f"- Approved / applied: **{rev.get('approved', 0)}**")
        lines.append(f"- Skipped (duplicate): **{rev.get('skipped_duplicate', 0)}**")
        lines.append(f"- Skipped (ambiguous): **{rev.get('skipped_ambiguous', 0)}**")
        lines.append(f"- Skipped (low confidence): **{rev.get('skipped_low_confidence', 0)}**")
        lines.append(f"- Rejected: **{rev.get('rejected', 0)}**")
        cu = rev.get("catalog_update") or {}
        if cu.get("target_foundup") is not None:
            lines.append(
                f"- Catalog update: `{cu.get('target_foundup')}` "
                f"{cu.get('video_count_before')} -> {cu.get('video_count_after')}"
            )
    lines.append("")

    # Blockers & next actions
    lines.append("## 6. Blockers")
    lines.append("")
    if summary["blockers"]:
        for b in summary["blockers"]:
            lines.append(f"- {b}")
    else:
        lines.append("- None detected from artifacts.")
    lines.append("")

    lines.append("## 7. Operator Next Action")
    lines.append("")
    if summary["next_actions"]:
        for a in summary["next_actions"]:
            lines.append(f"- {a}")
    else:
        lines.append("- No action required.")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "_Summary is artifact-grounded. Missing artifacts are reported honestly; "
        "no fields are inferred from sources that do not exist._"
    )
    lines.append("")
    return "\n".join(lines)


def write_status_summary(
    summary: Dict[str, Any],
    markdown_path: Path = SUMMARY_MD_PATH,
    json_path: Path = SUMMARY_JSON_PATH,
) -> Dict[str, Path]:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(summary), encoding="utf-8")
    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"markdown": markdown_path, "json": json_path}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate read-only status summary for the pfMALL YouTube pipeline."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root (defaults to inferred path).",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=SUMMARY_MD_PATH,
        help="Path for markdown summary output.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=SUMMARY_JSON_PATH,
        help="Path for JSON summary output.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print markdown to stdout instead of writing files.",
    )
    args = parser.parse_args(argv)

    summary = generate_status_summary(args.repo_root)

    if args.stdout:
        sys.stdout.write(render_markdown(summary))
        return 0

    written = write_status_summary(summary, args.markdown_out, args.json_out)
    print(f"[OK] Wrote markdown: {written['markdown']}")
    print(f"[OK] Wrote JSON:     {written['json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
