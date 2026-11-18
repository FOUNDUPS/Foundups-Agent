"""Test resumable GitHub-to-PC completion through the WRE lifecycle owner."""

import json
from pathlib import Path
import subprocess
from subprocess import CompletedProcess

from modules.infrastructure.wre_core.src import git_lifecycle as lifecycle


MAIN_SHA = "1" * 40
MERGE_SHA = "2" * 40
HEAD_SHA = "3" * 40


def _runner(args, *, cwd, timeout):
    if args[1:2] == ("rev-parse",):
        return CompletedProcess(args, 0, str(cwd / ".git"), "")
    if args[1:2] == ("config",):
        return CompletedProcess(args, 1, "", "")
    assert args == ("git", "--no-replace-objects", "merge-base", "--is-ancestor", MERGE_SHA, MAIN_SHA)
    return CompletedProcess(args, 0, "", "")


def _github(*, open_prs=(), tracked=(), verified=True, branches=(), coverage="complete", coverage_by_source=None):
    sources = (
        coverage_by_source
        if coverage_by_source is not None
        else {"pull_requests": "complete", "branches": "complete", "tracked_pull_requests": "complete"}
    )
    return {
        "repository": "FOUNDUPS/Foundups-Agent", "main_sha": MAIN_SHA,
        "coverage": coverage, "coverage_by_source": sources, "pages": {},
        "errors": [], "branches": list(branches), "pull_requests": list(open_prs),
        "tracked_pull_requests": list(tracked), "main_checks": {"verified": verified},
    }


def test_lifecycle_resumes_until_github_and_pc_are_both_verified(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    open_item = {"number": 42, "state": "open", "head_sha": HEAD_SHA}
    merged_item = {
        "number": 42, "state": "closed", "head_sha": HEAD_SHA,
        "merged": True, "merge_sha": MERGE_SHA, "checks_verified": True,
    }
    observations = iter([
        ((), _github(open_prs=[open_item])),
        ((42,), _github(tracked=[merged_item], verified=False)),
        ((42,), _github(tracked=[merged_item])),
        ((42,), _github(tracked=[merged_item])),
        ((), _github()),
    ])

    def observe(root, *, runner, tracked_prs):
        assert root == tmp_path
        expected, snapshot = next(observations)
        assert tracked_prs == expected
        return snapshot

    pc_results = iter([
        (True, "PC_SYNC_PENDING"),
        (False, "PC_SYNC_PENDING"),
        (True, "PC_SYNC_BLOCKED"),
        (True, "PC_SYNC_VERIFIED"),
        (True, "PC_SYNC_VERIFIED"),
    ])

    def reconcile(root, sha, *, runner, allow_update):
        assert root == tmp_path and sha == MAIN_SHA
        expected, status = next(pc_results)
        assert allow_update is expected
        return {"status": status, "head_sha": sha if status == "PC_SYNC_VERIFIED" else None}

    monkeypatch.setattr(lifecycle, "observe_github", observe)
    monkeypatch.setattr(lifecycle, "reconcile_pc_main", reconcile)
    reports = [
        lifecycle.reconcile_git_lifecycle(tmp_path, synchronize_pc=True, runner=_runner)
        for _ in range(5)
    ]
    assert [report["pull_requests"][0]["stage"] for report in reports[:4]] == [
        "PR_OPEN", "MAIN_VERIFICATION_PENDING", "PC_SYNC_PENDING", "COMPLETE",
    ]
    assert [report["pending_prs"] for report in reports] == [[42], [42], [42], [], []]
    assert reports[-1]["completed_prs"][0]["verified_main_sha"] == MAIN_SHA
    assert reports[-1]["completed_prs"][0]["verified_pc_sha"] == MAIN_SHA


def test_invalid_previous_receipt_is_preserved_before_any_external_work(tmp_path, monkeypatch):
    common = tmp_path / ".git"
    common.mkdir()
    receipt = common / lifecycle._RECEIPT_NAME
    receipt.write_text("invalid", encoding="utf-8")

    def unexpected(*args, **kwargs):
        raise AssertionError("unsafe external work")

    monkeypatch.setattr(lifecycle, "observe_github", unexpected)
    monkeypatch.setattr(lifecycle, "reconcile_pc_main", unexpected)
    result = lifecycle.reconcile_git_lifecycle(tmp_path, synchronize_pc=True, runner=_runner)
    assert result["coverage"] == "unavailable"
    assert receipt.read_text(encoding="utf-8") == "invalid"


def test_lifecycle_rotates_attempted_details_without_dropping_pending(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    calls = []

    def observe(root, *, runner, tracked_prs):
        calls.append(tracked_prs)
        result = _github()
        result["coverage"] = "partial"
        result["tracked_lookups"] = list(tracked_prs[:2])
        return result

    monkeypatch.setattr(lifecycle, "observe_github", observe)
    monkeypatch.setattr(
        lifecycle, "reconcile_pc_main",
        lambda *args, **kwargs: {"status": "PC_SYNC_PENDING", "head_sha": None},
    )
    first = lifecycle.reconcile_git_lifecycle(tmp_path, tracked_prs=(1, 2, 3), runner=_runner)
    second = lifecycle.reconcile_git_lifecycle(tmp_path, runner=_runner)
    assert calls == [(1, 2, 3), (3, 1, 2)]
    assert first["pending_prs"] == [3, 1, 2]
    assert second["pending_prs"] == [2, 3, 1]


def test_branch_dispositions_classify_tracked_and_untracked_branches_by_exact_sha(
    tmp_path, monkeypatch,
):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    reused_sha = "5" * 40
    orphan_sha = "6" * 40
    closed_sha = "7" * 40
    pc_pending_sha = "8" * 40
    newer_merged_sha = "9" * 40
    complete_merged_sha = "a" * 40
    repo = "FOUNDUPS/Foundups-Agent"
    (git_dir / lifecycle._RECEIPT_NAME).write_text(
        json.dumps({
            "schema_version": 1,
            "repository": repo,
            "pending_prs": [13, 14, 15],
            "completed_prs": [
                {
                    "number": 11, "stage": "COMPLETE", "head_ref": "docs/merged",
                    "head_sha": HEAD_SHA, "head_repository": repo,
                },
                {
                    "number": 12, "stage": "COMPLETE", "head_ref": "docs/reused",
                    "head_sha": HEAD_SHA, "head_repository": repo,
                },
                {
                    "number": 16, "stage": "COMPLETE", "head_ref": "docs/complete-merged",
                    "head_sha": complete_merged_sha, "head_repository": repo,
                },
            ],
        }),
        encoding="utf-8",
    )
    snapshot = _github(
        open_prs=[{
            "number": 10, "state": "open", "draft": False,
            "head_ref": "docs/open", "head_sha": HEAD_SHA, "head_repository": repo,
            "base_ref": "main", "base_sha": MAIN_SHA,
        }],
        tracked=[
            {
                "number": 13, "state": "closed", "merged": False,
                "head_ref": "docs/closed", "head_sha": closed_sha, "head_repository": repo,
            },
            {
                "number": 14, "state": "closed", "merged": True, "merge_sha": MERGE_SHA,
                "checks_verified": True, "head_ref": "docs/pc-pending", "head_sha": pc_pending_sha,
                "head_repository": repo,
            },
            {
                "number": 15, "state": "closed", "merged": True, "merge_sha": MERGE_SHA,
                "checks_verified": True, "head_ref": "docs/merged", "head_sha": newer_merged_sha,
                "head_repository": repo,
            },
        ],
        branches=[
            {"ref": "main", "sha": MAIN_SHA, "protected": True},
            {"ref": "docs/open", "sha": HEAD_SHA, "protected": False},
            {"ref": "docs/merged", "sha": newer_merged_sha, "protected": False},
            {"ref": "docs/complete-merged", "sha": complete_merged_sha, "protected": False},
            {"ref": "docs/reused", "sha": reused_sha, "protected": False},
            {"ref": "docs/closed", "sha": closed_sha, "protected": False},
            {"ref": "docs/pc-pending", "sha": pc_pending_sha, "protected": False},
            {"ref": "feat/orphan", "sha": orphan_sha, "protected": False},
        ],
    )

    monkeypatch.setattr(lifecycle, "observe_github", lambda *args, **kwargs: snapshot)
    monkeypatch.setattr(
        lifecycle, "reconcile_pc_main",
        lambda *args, **kwargs: {"status": "PC_SYNC_PENDING", "head_sha": None},
    )
    report = lifecycle.reconcile_git_lifecycle(tmp_path, runner=_runner)
    by_ref = {row["ref"]: row for row in report["branch_dispositions"]}

    assert by_ref["main"] == {
        "ref": "main", "sha": MAIN_SHA, "protected": True,
        "pr_number": None, "pr_numbers": [], "stage": "MAIN_BRANCH", "next_action": None,
    }
    assert by_ref["docs/open"] == {
        "ref": "docs/open", "sha": HEAD_SHA, "protected": False,
        "pr_number": 10, "pr_numbers": [10], "stage": "BRANCH_OPEN_PR",
        "next_action": "verify_owner_and_merge_authority",
    }
    assert by_ref["docs/merged"] == {
        "ref": "docs/merged", "sha": newer_merged_sha, "protected": False,
        "pr_number": 15, "pr_numbers": [11, 15], "stage": "BRANCH_MERGED_PR_RETAINED",
        "next_action": "synchronize_selected_pc_worktree",
    }
    assert by_ref["docs/complete-merged"] == {
        "ref": "docs/complete-merged", "sha": complete_merged_sha, "protected": False,
        "pr_number": 16, "pr_numbers": [16], "stage": "BRANCH_MERGED_PR_RETAINED",
        "next_action": "assess_retirement_diff_against_main",
    }
    assert by_ref["docs/reused"] == {
        "ref": "docs/reused", "sha": reused_sha, "protected": False,
        "pr_number": None, "pr_numbers": [12], "stage": "BRANCH_PR_HEAD_MISMATCH",
        "next_action": "assess_full_diff_and_owner",
    }
    assert by_ref["docs/closed"] == {
        "ref": "docs/closed", "sha": closed_sha, "protected": False,
        "pr_number": 13, "pr_numbers": [13], "stage": "BRANCH_CLOSED_PR_UNMERGED",
        "next_action": "reconcile_unique_work_and_owner",
    }
    assert by_ref["docs/pc-pending"] == {
        "ref": "docs/pc-pending", "sha": pc_pending_sha, "protected": False,
        "pr_number": 14, "pr_numbers": [14], "stage": "BRANCH_MERGED_PR_RETAINED",
        "next_action": "synchronize_selected_pc_worktree",
    }
    assert by_ref["feat/orphan"] == {
        "ref": "feat/orphan", "sha": orphan_sha, "protected": False,
        "pr_number": None, "pr_numbers": [], "stage": "BRANCH_UNTRACKED",
        "next_action": "assess_full_diff_and_owner",
    }


def test_branch_dispositions_hardening_guards(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    moved_branch_sha = "4" * 40
    protected_sha = "5" * 40
    unknown_repo_sha = "6" * 40
    fork_sha = "7" * 40
    case_sha = "8" * 40

    snapshot = _github(
        open_prs=[
            {
                "number": 20, "state": "open", "draft": False,
                "head_ref": "feat/moved", "head_sha": HEAD_SHA,
                "head_repository": "FOUNDUPS/Foundups-Agent",
                "base_ref": "main", "base_sha": MAIN_SHA,
            },
            {
                "number": 21, "state": "open", "draft": False,
                "head_ref": "feat/unknown-repo", "head_sha": unknown_repo_sha,
                "head_repository": None,
                "base_ref": "main", "base_sha": MAIN_SHA,
            },
            {
                "number": 22, "state": "open", "draft": False,
                "head_ref": "feat/fork-pr", "head_sha": fork_sha,
                "head_repository": "fork-contributor/Foundups-Agent",
                "base_ref": "main", "base_sha": MAIN_SHA,
            },
            {
                "number": 23, "state": "open", "draft": False,
                "head_ref": "docs/case-match", "head_sha": case_sha,
                "head_repository": "foundups/foundups-agent",
                "base_ref": "main", "base_sha": MAIN_SHA,
            },
        ],
        branches=[
            {"ref": "main", "sha": MAIN_SHA, "protected": True},
            {"ref": "release/v1", "sha": protected_sha, "protected": True},
            {"ref": "feat/moved", "sha": moved_branch_sha, "protected": False},
            {"ref": "feat/unknown-repo", "sha": unknown_repo_sha, "protected": False},
            {"ref": "feat/fork-pr", "sha": fork_sha, "protected": False},
            {"ref": "docs/case-match", "sha": case_sha, "protected": False},
        ],
    )

    monkeypatch.setattr(lifecycle, "observe_github", lambda *args, **kwargs: snapshot)
    monkeypatch.setattr(
        lifecycle, "reconcile_pc_main",
        lambda *args, **kwargs: {"status": "PC_SYNC_PENDING", "head_sha": None},
    )
    report = lifecycle.reconcile_git_lifecycle(tmp_path, runner=_runner)
    by_ref = {row["ref"]: row for row in report["branch_dispositions"]}

    assert by_ref["release/v1"] == {
        "ref": "release/v1", "sha": protected_sha, "protected": True,
        "pr_number": None, "pr_numbers": [], "stage": "PROTECTED_BRANCH",
        "next_action": "assess_protected_branch_policy",
    }
    assert by_ref["feat/moved"] == {
        "ref": "feat/moved", "sha": moved_branch_sha, "protected": False,
        "pr_number": 20, "pr_numbers": [20], "stage": "BRANCH_OPEN_PR_HEAD_MOVED",
        "next_action": "refresh_pull_request_evidence",
    }
    assert by_ref["feat/unknown-repo"]["stage"] == "BRANCH_UNTRACKED"
    assert by_ref["feat/unknown-repo"]["pr_numbers"] == []
    assert by_ref["feat/fork-pr"]["stage"] == "BRANCH_UNTRACKED"
    assert by_ref["feat/fork-pr"]["pr_numbers"] == []
    assert by_ref["docs/case-match"]["stage"] == "BRANCH_OPEN_PR"
    assert by_ref["docs/case-match"]["pr_number"] == 23


def test_branch_dispositions_partial_pr_coverage_blocks_untracked(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    partial_sha = "a" * 40
    snapshot = _github(
        coverage="partial",
        coverage_by_source={"pull_requests": "partial", "branches": "complete", "tracked_pull_requests": "complete"},
        branches=[
            {"ref": "main", "sha": MAIN_SHA, "protected": True},
            {"ref": "feat/maybe-has-pr", "sha": partial_sha, "protected": False},
        ],
    )

    monkeypatch.setattr(lifecycle, "observe_github", lambda *args, **kwargs: snapshot)
    monkeypatch.setattr(
        lifecycle, "reconcile_pc_main",
        lambda *args, **kwargs: {"status": "PC_SYNC_PENDING", "head_sha": None},
    )
    report = lifecycle.reconcile_git_lifecycle(tmp_path, runner=_runner)
    by_ref = {row["ref"]: row for row in report["branch_dispositions"]}

    assert by_ref["feat/maybe-has-pr"] == {
        "ref": "feat/maybe-has-pr", "sha": partial_sha, "protected": False,
        "pr_number": None, "pr_numbers": [],
        "stage": "BRANCH_PR_OBSERVATION_INCOMPLETE",
        "next_action": "refresh_pull_request_evidence",
    }


def test_disposable_repository_bundle_restores_committed_refs_only(tmp_path):
    source = tmp_path / "source"
    restored = tmp_path / "restored"
    hooks = tmp_path / "empty-hooks"
    bundle = tmp_path / "backup.bundle"
    source.mkdir()
    hooks.mkdir()

    def git(cwd, *args):
        return subprocess.run(
            ["git", *args],
            cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8",
        ).stdout.strip()

    git(source, "init", "--quiet", "--initial-branch=main")
    git(
        source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "-c", f"core.hooksPath={hooks}", "commit", "--quiet", "--allow-empty", "-m", "main base",
    )
    main_sha = git(source, "rev-parse", "HEAD")

    git(source, "switch", "--quiet", "-c", "feat/slice")
    (source / "committed.txt").write_text("committed slice work\n", encoding="utf-8")
    git(source, "add", "committed.txt")
    git(
        source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "-c", f"core.hooksPath={hooks}", "commit", "--quiet", "-m", "slice commit",
    )
    slice_sha = git(source, "rev-parse", "HEAD")
    git(source, "switch", "--quiet", "main")
    (source / "dirty.txt").write_text("uncommitted local work\n", encoding="utf-8")

    git(source, "bundle", "create", str(bundle), "--branches", "--tags", "HEAD")
    git(source, "bundle", "verify", str(bundle))
    git(tmp_path, "clone", "--quiet", str(bundle), str(restored))

    assert git(restored, "rev-parse", "refs/heads/main") == main_sha
    assert git(restored, "rev-parse", "refs/remotes/origin/feat/slice") == slice_sha
    assert not (restored / "dirty.txt").exists()
