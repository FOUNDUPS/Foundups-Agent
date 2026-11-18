"""Exercise lifecycle inventory with deterministic Git and GitHub responses."""

from __future__ import annotations

import json
from subprocess import CompletedProcess, TimeoutExpired

import pytest

from modules.infrastructure.wre_core.src import git_lifecycle_github as inventory


_REPO = "FOUNDUPS/Foundups-Agent"
_MAIN = "a" * 40
_HEAD = "b" * 40
_MERGE = "c" * 40
_RULES = "rules/branches/main?per_page=100&page=1"
_BRANCHES = "branches?per_page=100&page=1"
_PULLS = "pulls?state=open&sort=created&direction=asc&per_page=100&page=1"
_MAIN_CHECKS = f"commits/{_MAIN}/check-runs?filter=latest&per_page=100&page=1"


def _pr(number, *, state="open", merged=None, merge_sha=None):
    return {
        "number": number, "state": state, "draft": False, "merged": merged,
        "merge_commit_sha": merge_sha,
        "head": {"ref": f"docs/{number}", "sha": _HEAD, "repo": _REPO},
        "base": {"ref": "main", "sha": _MAIN, "repo": _REPO},
    }


def _check(sha=_MAIN, **changes):
    return {
        "name": "test (3.12)", "head_sha": sha, "app_id": 15368,
        "status": "completed", "conclusion": "success", **changes,
    }


def _page(rows, *, next_page=None):
    headers = ["HTTP/2.0 200 OK", "Content-Type: application/json"]
    if next_page is not None:
        headers.append(f'Link: <https://api.github.com/repositories/10/item?page={next_page}>; rel="next"')
    return "\r\n".join(headers) + "\r\n\r\n" + json.dumps(rows)


class _Runner:
    def __init__(self, root, *, remote="https://github.com/FOUNDUPS/Foundups-Agent.git"):
        self.root = root
        self.remote = remote
        self.calls = []
        self.answers = {
            "git/ref/heads/main": json.dumps({
                "ref": "refs/heads/main", "object": {"type": "commit", "sha": _MAIN}
            }),
            _PULLS: _page([_pr(1)]),
            _BRANCHES: _page([{"name": "main", "sha": _MAIN, "protected": True}]),
            _RULES: _page([{"context": "test (3.12)", "integration_id": 15368}]),
            _MAIN_CHECKS: _page([_check()]),
        }

    def __call__(self, args, *, cwd, timeout):
        assert cwd == self.root and timeout <= 10
        if args == ["git", "remote", "get-url", "--all", "origin"]:
            self.calls.append("origin")
            return CompletedProcess(args, 0, self.remote + "\n", "")
        assert args[:6] == ["gh", "api", "--hostname", "github.com", "--method", "GET"]
        assert args[-2] == "--jq"
        assert args[-3].startswith(f"repos/{_REPO}/")
        path = args[-3].split(f"repos/{_REPO}/", 1)[1]
        self.calls.append(path)
        answer = self.answers[path]
        if answer is None:
            raise TimeoutExpired(args, timeout)
        return CompletedProcess(args, 0, answer, "")


@pytest.mark.parametrize("remote", [
    "https://github.com/FOUNDUPS/Foundups-Agent.git",
    "https://GITHUB.COM/foundups/foundups-agent",
    "git@github.com:FOUNDUPS/Foundups-Agent.git",
    "ssh://git@github.com/FOUNDUPS/Foundups-Agent.git",
])
def test_recognizes_canonical_origin(tmp_path, remote):
    runner = _Runner(tmp_path, remote=remote)

    result = inventory.observe_github(tmp_path, runner=runner)

    assert result["repository"] == _REPO
    assert result["main_sha"] == _MAIN
    assert result["coverage"] == "complete"
    assert result["main_checks"] == {"verified": True, "reason": "verified"}


@pytest.mark.parametrize("remote", [
    "https://sample-user@github.com/FOUNDUPS/Foundups-Agent",
    "https://github.com/FOUNDUPS/Foundups-Agent?extra",
    "https://github.com.invalid/FOUNDUPS/Foundups-Agent",
    "https://github.com/another/Foundups-Agent",
    "https://github.com/FOUNDUPS/Foundups-Agent\nhttps://github.com/other/repo",
])
def test_rejects_unrecognized_origin_without_network(tmp_path, remote):
    runner = _Runner(tmp_path, remote=remote)

    result = inventory.observe_github(tmp_path, runner=runner)

    assert runner.calls == ["origin"]
    assert result["repository"] is None
    assert result["coverage"] == "unavailable"
    assert result["errors"] == ["origin_not_canonical"]


def test_paginates_each_inventory_and_reads_only_vanished_tracked_pr(tmp_path):
    runner = _Runner(tmp_path)
    runner.answers.update({
        _PULLS: _page([_pr(1)], next_page=2),
        _PULLS.replace("&page=1", "&page=2"): _page([_pr(2)]),
        _BRANCHES: _page([{"name": "main", "sha": _MAIN, "protected": True}], next_page=2),
        _BRANCHES.replace("&page=1", "&page=2"): _page([
            {"name": "docs/2", "sha": _HEAD, "protected": False}
        ]),
        "pulls/3": json.dumps(_pr(3, state="closed", merged=True, merge_sha=_MERGE)),
        f"commits/{_MERGE}/check-runs?filter=latest&per_page=100&page=1": _page([_check(_MERGE)]),
    })

    result = inventory.observe_github(tmp_path, runner=runner, tracked_prs=(2, 3))

    assert result["coverage"] == "complete"
    assert result["pages"] == {"main": 1, "pull_requests": 2, "branches": 2, "tracked_pull_requests": 1}
    assert [pr["number"] for pr in result["pull_requests"]] == [1, 2]
    assert [branch["ref"] for branch in result["branches"]] == ["docs/2", "main"]
    assert "pulls/2" not in runner.calls
    merged = result["tracked_pull_requests"][1]
    assert merged["number"] == 3 and merged["merge_sha"] == _MERGE
    assert merged["checks_verified"] is True
    assert "verified_main" not in merged


def test_incomplete_and_unavailable_sources_do_not_look_empty(tmp_path):
    runner = _Runner(tmp_path)
    runner.answers.update({
        _PULLS: _page([_pr(1)], next_page=2),
        _PULLS.replace("&page=1", "&page=2"): None,
        _BRANCHES: None,
    })

    result = inventory.observe_github(tmp_path, runner=runner)

    assert result["coverage"] == "partial"
    assert result["coverage_by_source"]["pull_requests"] == "partial"
    assert result["coverage_by_source"]["branches"] == "unavailable"
    assert [pr["number"] for pr in result["pull_requests"]] == [1]
    assert result["branches"] == []


def test_duplicate_inventory_and_unexpected_link_fail_closed(tmp_path):
    runner = _Runner(tmp_path)
    runner.answers[_PULLS] = _page([_pr(1), _pr(1)])
    runner.answers[_BRANCHES] = _page([], next_page=3)

    result = inventory.observe_github(tmp_path, runner=runner)

    assert result["coverage_by_source"]["pull_requests"] == "partial"
    assert result["coverage_by_source"]["branches"] == "unavailable"
    assert result["errors"] == ["pull_requests_invalid_row", "branches_page_unavailable"]


@pytest.mark.parametrize(("rows", "expected"), [
    ([], "required_check_missing"),
    ([_check(status="queued", conclusion=None)], "required_check_not_successful"),
    ([_check(conclusion="skipped")], "required_check_not_successful"),
    ([_check(app_id=57789)], "required_check_source_mismatch"),
    ([_check(_HEAD)], "required_check_source_mismatch"),
    ([_check(), _check()], "duplicate_required_check"),
])
def test_refuses_unproven_main_checks(tmp_path, rows, expected):
    runner = _Runner(tmp_path)
    runner.answers[_MAIN_CHECKS] = _page(rows)

    result = inventory.observe_github(tmp_path, runner=runner)

    assert result["coverage"] == "complete"
    assert result["main_checks"] == {"verified": False, "reason": expected}


def test_main_check_proof_needs_a_complete_pinned_rule_set(tmp_path):
    runner = _Runner(tmp_path)
    runner.answers[_RULES] = _page([], next_page=2)
    runner.answers[_RULES.replace("&page=1", "&page=2")] = None

    result = inventory.observe_github(tmp_path, runner=runner)

    assert result["main_checks"] == {"verified": False, "reason": "required_checks_unavailable"}
    assert _MAIN_CHECKS not in runner.calls


def test_main_check_proof_reads_all_pages_and_rechecks_main(tmp_path):
    runner = _Runner(tmp_path)
    runner.answers[_MAIN_CHECKS] = _page([], next_page=2)
    runner.answers[_MAIN_CHECKS.replace("&page=1", "&page=2")] = _page([_check()])

    result = inventory.observe_github(tmp_path, runner=runner)

    assert result["main_checks"]["verified"] is True
    assert runner.calls.count("git/ref/heads/main") == 2


def test_wrong_state_in_open_inventory_is_incomplete(tmp_path):
    runner = _Runner(tmp_path)
    runner.answers[_PULLS] = _page([_pr(1, state="closed", merged=False)])

    result = inventory.observe_github(tmp_path, runner=runner)

    assert result["coverage_by_source"]["pull_requests"] == "partial"
    assert result["pull_requests"] == []


def test_main_check_proof_rejects_moved_main(tmp_path):
    runner = _Runner(tmp_path)

    def moving_runner(args, **kwargs):
        if "repos/FOUNDUPS/Foundups-Agent/git/ref/heads/main" in args and "git/ref/heads/main" in runner.calls:
            runner.answers["git/ref/heads/main"] = json.dumps({
                "ref": "refs/heads/main", "object": {"type": "commit", "sha": _HEAD}
            })
        return runner(args, **kwargs)

    result = inventory.observe_github(tmp_path, runner=moving_runner)

    assert result["main_checks"] == {"verified": False, "reason": "main_changed_during_observation"}
    assert result["coverage"] == "partial"



def test_reuses_open_inventory_when_many_persisted_numbers_are_tracked(tmp_path):
    numbers = tuple(range(1, 45))
    first_runner = _Runner(tmp_path)
    first_runner.answers[_PULLS] = _page([_pr(number) for number in numbers])
    first = inventory.observe_github(tmp_path, runner=first_runner)
    previous_pending = tuple(pr["number"] for pr in first["pull_requests"])

    next_runner = _Runner(tmp_path)
    next_runner.answers[_PULLS] = _page([_pr(number) for number in numbers if number != 2])
    next_runner.answers["pulls/2"] = json.dumps(_pr(2, state="closed", merged=False))
    resumed = inventory.observe_github(tmp_path, runner=next_runner, tracked_prs=previous_pending)

    assert resumed["coverage"] == "complete"
    assert resumed["pages"]["tracked_pull_requests"] == 1
    assert [path for path in next_runner.calls if path.startswith("pulls/")] == ["pulls/2"]
    assert [pr["number"] for pr in resumed["tracked_pull_requests"]] == list(numbers)


def test_limits_details_for_vanished_numbers_in_request_order(tmp_path):
    runner = _Runner(tmp_path)
    for number in range(2, 14):
        runner.answers[f"pulls/{number}"] = json.dumps(_pr(number, state="closed", merged=False))

    result = inventory.observe_github(
        tmp_path, runner=runner, tracked_prs=tuple(range(1, 16)),
    )

    assert result["coverage"] == "partial"
    assert result["coverage_by_source"]["tracked_pull_requests"] == "partial"
    assert result["errors"] == ["tracked_pull_request_lookup_limit"]
    assert result["pages"]["tracked_pull_requests"] == 12
    assert [path for path in runner.calls if path.startswith("pulls/")] == [
        f"pulls/{number}" for number in range(2, 14)
    ]
