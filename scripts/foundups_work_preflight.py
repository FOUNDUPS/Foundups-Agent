#!/usr/bin/env python3
"""Read-only Git lane inventory for FoundUps task admission and closure."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


SCHEMA_VERSION = "foundups_work_preflight.v1"


class GitError(RuntimeError):
    """Raised when repository evidence cannot be read truthfully."""


@dataclass(frozen=True)
class DirtSummary:
    staged: int
    tracked_modified: int
    untracked: int
    conflicts: int
    total: int


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", "-c", "core.quotepath=false", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=5,
        check=False,
    )
    if check and completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
        raise GitError(detail)
    return completed


def _status(path: Path) -> tuple[DirtSummary, tuple[str, ...]]:
    lines = tuple(
        line
        for line in _git(path, "status", "--porcelain=v1", "--untracked-files=all").stdout.splitlines()
        if line
    )
    staged = tracked_modified = untracked = conflicts = 0
    conflict_codes = {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}
    for line in lines:
        code = line[:2]
        if code == "??":
            untracked += 1
            continue
        if code in conflict_codes:
            conflicts += 1
        if code[0] not in {" ", "?"}:
            staged += 1
        if code[1] not in {" ", "?"}:
            tracked_modified += 1
    return (
        DirtSummary(
            staged=staged,
            tracked_modified=tracked_modified,
            untracked=untracked,
            conflicts=conflicts,
            total=len(lines),
        ),
        lines,
    )


def _parse_worktrees(repo: Path) -> list[dict[str, object]]:
    blocks = _git(repo, "worktree", "list", "--porcelain").stdout.strip().split("\n\n")
    parsed: list[dict[str, object]] = []
    for block in blocks:
        record: dict[str, object] = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            if key in {"detached", "bare"}:
                record[key] = True
            elif key in {"locked", "prunable"}:
                record[key] = value or True
            elif key == "branch":
                record[key] = value.removeprefix("refs/heads/")
            elif key:
                record[key] = value
        if record.get("worktree"):
            parsed.append(record)
    return parsed


def _default_ref(repo: Path) -> str | None:
    for candidate in ("origin/main", "main"):
        if _git(repo, "rev-parse", "--verify", "--quiet", candidate, check=False).returncode == 0:
            return candidate
    return None


def _divergence(path: Path, default_ref: str | None) -> tuple[int | None, int | None, bool | None]:
    if default_ref is None:
        return None, None, None
    counts = _git(path, "rev-list", "--left-right", "--count", f"{default_ref}...HEAD")
    behind_text, ahead_text = counts.stdout.strip().split()
    merged = _git(path, "merge-base", "--is-ancestor", "HEAD", default_ref, check=False).returncode == 0
    return int(ahead_text), int(behind_text), merged


def _disposition(*, current: bool, dirt: DirtSummary, ahead: int | None, merged: bool | None) -> str:
    if dirt.total:
        return "RECONCILE_CURRENT_DIRT" if current else "REVIEW_OWNERSHIP"
    if current:
        return "READY"
    if merged is True:
        return "RETIRE_CANDIDATE"
    if ahead:
        return "ACTIVE_OR_SALVAGE_REVIEW"
    return "KEEP_REVIEW"


def _inspect_worktree(
    raw: dict[str, object],
    *,
    current_root: Path,
    default_ref: str | None,
) -> dict[str, object]:
    path = Path(str(raw["worktree"])).resolve()
    current = path == current_root
    try:
        dirt, entries = _status(path)
        ahead, behind, merged = _divergence(path, default_ref)
        disposition = _disposition(current=current, dirt=dirt, ahead=ahead, merged=merged)
        scan_error = None
    except (GitError, OSError, subprocess.TimeoutExpired, ValueError) as error:
        dirt = DirtSummary(0, 0, 0, 0, 0)
        entries = ()
        ahead = behind = None
        merged = None
        disposition = "EVIDENCE_UNAVAILABLE"
        scan_error = type(error).__name__
    return {
        "path": str(path),
        "branch": raw.get("branch"),
        "head": raw.get("HEAD"),
        "current": current,
        "locked": raw.get("locked", False),
        "prunable": raw.get("prunable", False),
        "ahead_of_default": ahead,
        "behind_default": behind,
        "merged_into_default": merged,
        "dirt": asdict(dirt),
        "entries": list(entries),
        "scan_error": scan_error,
        "disposition": disposition,
    }


def build_report(repo: Path) -> dict[str, object]:
    current_root = Path(_git(repo, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    common_dir = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()).resolve()
    primary_root = common_dir.parent.resolve()
    default_ref = _default_ref(current_root)
    raw_worktrees = _parse_worktrees(current_root)
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(raw_worktrees)))) as executor:
        worktrees = list(
            executor.map(
                lambda raw: _inspect_worktree(
                    raw,
                    current_root=current_root,
                    default_ref=default_ref,
                ),
                raw_worktrees,
            )
        )
    current_record = next(item for item in worktrees if item["current"])
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": str(primary_root),
        "current_worktree": str(current_root),
        "default_ref": default_ref,
        "admission": "READY" if current_record["disposition"] == "READY" else "RECONCILE",
        "destructive_action_authorized": False,
        "worktrees": worktrees,
    }


def _render_text(report: dict[str, object]) -> str:
    rows = [
        f"FoundUps work preflight: {report['admission']}",
        f"Current: {report['current_worktree']}",
        f"Default: {report['default_ref'] or 'unavailable'}",
        "",
    ]
    for item in report["worktrees"]:
        dirt = item["dirt"]
        marker = "*" if item["current"] else "-"
        rows.append(
            f"{marker} {item['disposition']}: {item['path']} "
            f"[{item['branch'] or 'detached'}] dirt={dirt['total']} "
            f"ahead={item['ahead_of_default']} behind={item['behind_default']}"
        )
    rows.append("")
    rows.append("Read-only evidence: no cleanup, stash, reset, commit, branch, or ledger mutation performed.")
    return "\n".join(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    try:
        report = build_report(args.repo_root)
    except (GitError, OSError, subprocess.TimeoutExpired, ValueError) as error:
        parser.exit(2, f"preflight failed: {error}\n")
    if args.as_json:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(_render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
