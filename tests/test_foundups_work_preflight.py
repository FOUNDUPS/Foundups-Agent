"""Tests for the read-only FoundUps work admission inventory."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import foundups_work_preflight as preflight  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=True,
        text=True,
    )
    return completed.stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    linked = tmp_path / "linked"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "preflight@example.invalid")
    _git(repo, "config", "user.name", "Preflight Test")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    _git(repo, "worktree", "add", "-b", "agent/test-lane", str(linked), "main")
    return repo, linked


def test_clean_current_lane_is_ready_and_linked_lane_is_retire_candidate(tmp_path: Path) -> None:
    repo, linked = _repository(tmp_path)

    report = preflight.build_report(repo)

    assert report["admission"] == "READY"
    assert report["destructive_action_authorized"] is False
    by_path = {Path(item["path"]): item for item in report["worktrees"]}
    assert by_path[repo.resolve()]["disposition"] == "READY"
    assert by_path[linked.resolve()]["disposition"] == "RETIRE_CANDIDATE"


def test_dirty_lanes_require_reconciliation_without_mutation(tmp_path: Path) -> None:
    repo, linked = _repository(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    (repo / "new.txt").write_text("new\n", encoding="utf-8")
    (linked / "linked.txt").write_text("linked\n", encoding="utf-8")

    report = preflight.build_report(repo)

    assert report["admission"] == "RECONCILE"
    by_path = {Path(item["path"]): item for item in report["worktrees"]}
    current = by_path[repo.resolve()]
    other = by_path[linked.resolve()]
    assert current["disposition"] == "RECONCILE_CURRENT_DIRT"
    assert current["dirt"] == {
        "staged": 0,
        "tracked_modified": 1,
        "untracked": 1,
        "conflicts": 0,
        "total": 2,
    }
    assert other["disposition"] == "REVIEW_OWNERSHIP"
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "changed\n"
    assert (linked / "linked.txt").exists()


def test_unreadable_linked_lane_is_reported_without_blocking_current_inventory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo, linked = _repository(tmp_path)
    real_status = preflight._status

    def fail_linked(path: Path):
        if path == linked.resolve():
            raise preflight.GitError("unavailable")
        return real_status(path)

    monkeypatch.setattr(preflight, "_status", fail_linked)

    report = preflight.build_report(repo)

    assert report["admission"] == "READY"
    by_path = {Path(item["path"]): item for item in report["worktrees"]}
    assert by_path[linked.resolve()]["disposition"] == "EVIDENCE_UNAVAILABLE"
    assert by_path[linked.resolve()]["scan_error"] == "GitError"


def test_json_cli_reconfigures_windows_stdout_for_unicode(monkeypatch) -> None:
    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding="cp932")
    monkeypatch.setattr(preflight.sys, "stdout", stream)
    monkeypatch.setattr(
        preflight,
        "build_report",
        lambda _repo: {"schema_version": preflight.SCHEMA_VERSION, "path": "Ç"},
    )

    assert preflight.main(["--json"]) == 0
    stream.flush()

    assert json.loads(buffer.getvalue().decode("utf-8"))["path"] == "Ç"
