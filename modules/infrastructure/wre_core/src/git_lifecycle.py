"""Reconcile GitHub and the selected PC worktree through one WRE pass."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from modules.infrastructure.shared_utilities.runtime_operation_locking import (
    exclusive_runtime_lock,
)

from .git_lifecycle_github import observe_github
from .git_lifecycle_pc import reconcile_pc_main


_PC_WORKTREE_CONFIG = "foundups.lifecyclePCWorktree"
_RECEIPT_NAME = "foundups-git-lifecycle.json"


def lifecycle_environment(environ):
    """Run Git against the selected checkout even from a caller's Git hook."""
    ignored = {
        "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_SHALLOW_FILE",
        "GIT_CONFIG", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT", "GIT_NAMESPACE",
        "GIT_GRAFT_FILE", "GIT_REPLACE_REF_BASE",
    }
    result = {key: value for key, value in environ.items() if key.upper() not in ignored}
    return {**result, "GIT_TERMINAL_PROMPT": "0", "GH_PROMPT_DISABLED": "1"}


def run_command(args, *, cwd, timeout):
    return subprocess.run(
        args, cwd=cwd, timeout=timeout, check=False, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        env=lifecycle_environment(os.environ),
    )


def _git_text(runner, root, *args):
    try:
        result = runner(("git", *args), cwd=root, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _common_dir(runner, root):
    value = _git_text(runner, root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(value).resolve() if value else None


def _pc_worktree(root, common, runner):
    configured = _git_text(runner, root, "config", "--local", "--get", _PC_WORKTREE_CONFIG)
    if configured:
        target = Path(configured)
        if not target.is_absolute() or not target.is_dir():
            return None
        target = target.resolve()
        if _common_dir(runner, target) != common:
            return None
        source_url = _git_text(runner, root, "remote", "get-url", "origin")
        if not source_url or _git_text(runner, target, "remote", "get-url", "origin") != source_url:
            return None
        return target
    return root if common == root / ".git" else None


def _read_previous(path):
    if path.is_symlink():
        raise ValueError("receipt_path_is_link")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if (
        not isinstance(record, dict)
        or record.get("schema_version") != 1
        or record.get("repository") != "FOUNDUPS/Foundups-Agent"
        or not isinstance(record.get("pending_prs"), list)
        or not isinstance(record.get("completed_prs"), list)
    ):
        raise ValueError("invalid_lifecycle_receipt")
    return record


def _valid_pr_number(value):
    return type(value) is int and value > 0


def _write_receipt(path, report):
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _empty_report(reason):
    return {
        "coverage": "unavailable",
        "reason": reason,
        "main_sha": None,
        "pull_requests": [],
        "pending_prs": [],
        "pc": {"status": "PC_SYNC_PENDING", "head_sha": None, "reason": reason, "updated": False},
    }


def _pr_dispositions(github, pc, pending, previous, target, runner):
    rows = {item["number"]: item for item in github["tracked_pull_requests"]}
    rows.update({item["number"]: item for item in github["pull_requests"]})
    previous_completed = previous.get("completed_prs", [])
    completed = {
        item["number"]: item for item in previous_completed
        if isinstance(item, dict) and _valid_pr_number(item.get("number"))
    }
    dispositions = []
    for number in sorted(set(rows) | pending):
        item = rows.get(number, {})
        state = item.get("state")
        merge_sha = item.get("merge_sha")
        stage = "PR_OBSERVATION_PENDING"
        action = "refresh_pull_request_evidence"
        if state == "open":
            stage = "PR_OPEN"
            if item.get("draft") is True:
                action = "verify_draft_owner_and_resume"
            elif item.get("base_ref") != "main":
                action = "reconcile_stacked_dependency"
            elif item.get("base_sha") != github["main_sha"]:
                action = "revalidate_against_current_main"
            else:
                action = "verify_owner_and_merge_authority"
        elif item.get("merged") is True and merge_sha:
            stage = "MAIN_VERIFICATION_PENDING"
            action = "verify_resulting_main_checks"
            if item.get("checks_verified") is True and github["main_checks"]["verified"]:
                stage = "PC_SYNC_PENDING"
                action = "synchronize_selected_pc_worktree"
                if target is not None and pc["status"] == "PC_SYNC_VERIFIED":
                    try:
                        ancestry = runner(
                            ("git", "--no-replace-objects", "merge-base", "--is-ancestor", merge_sha, github["main_sha"]),
                            cwd=target, timeout=5,
                        )
                    except (OSError, subprocess.SubprocessError):
                        ancestry = None
                    if ancestry is not None and ancestry.returncode == 0:
                        stage = "COMPLETE"
                        action = None
        elif state == "closed":
            stage = "CLOSED_UNMERGED"
            action = "reconcile_unique_work_and_owner"
        disposition = {
            "number": number, "stage": stage, "next_action": action,
            "head_ref": item.get("head_ref"), "head_sha": item.get("head_sha"),
            "head_repository": item.get("head_repository"),
            "base_ref": item.get("base_ref"), "base_sha": item.get("base_sha"),
            "draft": item.get("draft"), "merge_sha": merge_sha,
        }
        if stage == "COMPLETE":
            disposition["verified_main_sha"] = github["main_sha"]
            disposition["verified_pc_sha"] = pc["head_sha"]
            completed[number] = disposition
        dispositions.append(disposition)
    return dispositions, [completed[key] for key in sorted(completed)[-100:]]


def _reconcile(repo_root, common, path, synchronize_pc, tracked_prs, runner):
    previous = _read_previous(path)
    pending = tuple(dict.fromkeys(
        number for number in (*previous.get("pending_prs", []), *tracked_prs)
        if _valid_pr_number(number)
    ))
    github = observe_github(repo_root, runner=runner, tracked_prs=pending)
    if github["repository"] is None:
        return _empty_report("github_repository_unverified")

    target = _pc_worktree(repo_root, common, runner)
    pc = _empty_report("pc_worktree_unselected")["pc"]
    if target is not None and github["main_sha"]:
        pc = reconcile_pc_main(
            target, github["main_sha"], runner=runner,
            allow_update=synchronize_pc and github["main_checks"]["verified"],
        )

    dispositions, completed = _pr_dispositions(github, pc, set(pending), previous, target, runner)
    unresolved = {item["number"] for item in dispositions if item["stage"] != "COMPLETE"}
    ordered = [number for number in pending if number in unresolved]
    ordered.extend(sorted(unresolved - set(pending)))
    attempted = set(github.get("tracked_lookups", []))
    ordered.sort(key=attempted.__contains__)
    report = {
        "schema_version": 1,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "repository": github["repository"],
        "coverage": github["coverage"],
        "coverage_by_source": github["coverage_by_source"],
        "pages": github["pages"],
        "reason": None if github["coverage"] == "complete" else "github_evidence_incomplete",
        "errors": github["errors"],
        "main_sha": github["main_sha"],
        "main_checks": github["main_checks"],
        "branches": github["branches"],
        "remote_promotion": "ADMITTED_AUTHORITY_REQUIRED",
        "pull_requests": dispositions,
        "pending_prs": ordered,
        "completed_prs": completed,
        "pc": pc,
    }
    try:
        _write_receipt(path, report)
    except OSError:
        report["coverage"] = "partial"
        report["reason"] = "lifecycle_receipt_write_failed"
    return report


def reconcile_git_lifecycle(
    repo_root: Path, *, synchronize_pc: bool = False,
    tracked_prs: tuple[int, ...] = (), runner=run_command,
):
    """Inventory work and resume local convergence without model or GitHub writes."""
    repo_root = Path(repo_root).resolve()
    deadline = time.monotonic() + 40

    def bounded_runner(args, *, cwd, timeout):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(args, 40)
        return runner(args, cwd=cwd, timeout=min(timeout, remaining))

    common = _common_dir(bounded_runner, repo_root)
    if common is None or not common.is_dir():
        return _empty_report("git_common_directory_unavailable")
    path = common / _RECEIPT_NAME
    try:
        with exclusive_runtime_lock(path, timeout_seconds=0.1):
            return _reconcile(
                repo_root, common, path, synchronize_pc, tracked_prs, bounded_runner,
            )
    except TimeoutError:
        return _empty_report("lifecycle_lock_unavailable")
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        return _empty_report("lifecycle_evidence_or_receipt_unavailable")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--sync-pc", action="store_true")
    parser.add_argument("--track-pr", type=int, action="append", default=[])
    args = parser.parse_args()
    report = reconcile_git_lifecycle(
        args.repo_root, synchronize_pc=args.sync_pc, tracked_prs=tuple(args.track_pr),
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if report["coverage"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
