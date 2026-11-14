"""Test resumable GitHub-to-PC completion through the WRE lifecycle owner."""

from pathlib import Path
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


def _github(*, open_prs=(), tracked=(), verified=True):
    return {
        "repository": "FOUNDUPS/Foundups-Agent", "main_sha": MAIN_SHA,
        "coverage": "complete", "coverage_by_source": {}, "pages": {},
        "errors": [], "branches": [], "pull_requests": list(open_prs),
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
