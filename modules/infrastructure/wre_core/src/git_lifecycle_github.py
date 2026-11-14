"""Read-only, bounded GitHub evidence for repository lifecycle reconciliation."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from urllib.parse import parse_qs, urlsplit


_REPOSITORY = "FOUNDUPS/Foundups-Agent"
_ENDPOINT = f"repos/{_REPOSITORY}"
_REMOTE = re.compile(
    r"(?:https://(?i:github\.com)/|git@(?i:github\.com):|ssh://git@(?i:github\.com)/)"
    r"(?i:foundups/foundups-agent)(?:\.git)?",
    re.ASCII,
)
_SHA = re.compile(r"[0-9a-f]{40}")
_REPO_NAME = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
_LINK = re.compile(r'<([^<>]+)>;\s*rel="(next|prev|first|last)"')
_PAGE_LIMIT = 10
_PAGE_SIZE = 100
_TRACKED_LIMIT = 12
_MAX_OUTPUT = 512_000
_PR_FIELDS = """{
    number, state, draft, merged, merge_commit_sha,
    head: {ref: .head.ref, sha: .head.sha, repo: .head.repo.full_name},
    base: {ref: .base.ref, sha: .base.sha, repo: .base.repo.full_name}
}"""
_BRANCH_FIELDS = "[.[] | {name, sha: .commit.sha, protected}]"
_RULE_FIELDS = '[.[] | select(.type == "required_status_checks") | .parameters.required_status_checks[]]'
_CHECK_FIELDS = "[.check_runs[] | {name, head_sha, status, conclusion, app_id: .app.id}]"


def _run(runner, root, args):
    try:
        result = runner(args, cwd=root, timeout=10)
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return None
    if result.returncode != 0 or not isinstance(result.stdout, str):
        return None
    return result.stdout if len(result.stdout) <= _MAX_OUTPUT else None


def _get(runner, root, path, fields, *, page=None):
    command = ["gh", "api", "--hostname", "github.com", "--method", "GET"]
    if page is not None:
        command.append("--include")
        separator = "&" if "?" in path else "?"
        path = f"{path}{separator}per_page={_PAGE_SIZE}&page={page}"
    output = _run(runner, root, [*command, f"{_ENDPOINT}/{path}", "--jq", fields])
    if output is None:
        return None, False
    try:
        if page is None:
            return json.loads(output), False
        headers, separator, body = output.replace("\r\n", "\n").partition("\n\n")
        if not separator or not re.match(r"HTTP/\S+ 200(?:\s|$)", headers):
            return None, False
        return json.loads(body), _has_next_page(headers, page)
    except ValueError:
        return None, False


def _has_next_page(headers, page):
    next_found = False
    for line in headers.splitlines()[1:]:
        name, _, value = line.partition(":")
        if name.lower() != "link":
            continue
        for entry in re.split(r",\s*(?=<)", value.strip()):
            match = _LINK.fullmatch(entry)
            if match is None:
                raise ValueError("malformed pagination")
            if match[2] == "next":
                url = urlsplit(match[1])
                if (
                    next_found
                    or url.scheme != "https"
                    or url.netloc != "api.github.com"
                    or parse_qs(url.query).get("page") != [str(page + 1)]
                ):
                    raise ValueError("unexpected pagination")
                next_found = True
    return next_found


def _pages(runner, root, path, fields):
    rows = []
    for page in range(1, _PAGE_LIMIT + 1):
        batch, has_next = _get(runner, root, path, fields, page=page)
        if not isinstance(batch, list) or len(batch) > _PAGE_SIZE:
            return rows, page - 1, "page_unavailable"
        rows.extend(batch)
        if not has_next:
            return rows, page, None
    return rows, _PAGE_LIMIT, "page_limit"


def _sha(value):
    return isinstance(value, str) and value != "0" * 40 and _SHA.fullmatch(value) is not None


def _text(value, limit):
    return isinstance(value, str) and 0 < len(value) <= limit and value.isprintable()


def _pr_number(value):
    return type(value) is int and 0 < value <= 2_147_483_647


def _pr_row(value, expected_number=None):
    if not isinstance(value, dict) or not _pr_number(value.get("number")):
        return None
    number = value["number"]
    state = value.get("state")
    head, base = value.get("head"), value.get("base")
    if (
        (expected_number is not None and number != expected_number)
        or state not in ("open", "closed")
        or type(value.get("draft")) is not bool
        or not all(isinstance(ref, dict) and _text(ref.get("ref"), 1024)
                   and _sha(ref.get("sha")) for ref in (head, base))
        or not isinstance(base.get("repo"), str)
        or base["repo"].casefold() != _REPOSITORY.casefold()
    ):
        return None
    head_repo = head.get("repo")
    if head_repo is not None and (
        not _text(head_repo, 256) or _REPO_NAME.fullmatch(head_repo) is None
    ):
        return None

    merged = value.get("merged")
    if state == "open" and merged is None:
        merged = False
    if type(merged) is not bool or (merged and state != "closed"):
        return None
    merge_sha = value.get("merge_commit_sha") if merged else None
    if merged and not _sha(merge_sha):
        return None
    return {
        "number": number, "state": state, "draft": value["draft"],
        "head_ref": head["ref"], "head_sha": head["sha"], "head_repository": head_repo,
        "base_ref": base["ref"], "base_sha": base["sha"], "merged": merged,
        "merge_sha": merge_sha,
    }


def _open_pr_row(value):
    row = _pr_row(value)
    return row if row and row["state"] == "open" else None


def _branch_row(value):
    if (
        not isinstance(value, dict)
        or not _text(value.get("name"), 1024)
        or not _sha(value.get("sha"))
        or type(value.get("protected")) is not bool
    ):
        return None
    return {"ref": value["name"], "sha": value["sha"], "protected": value["protected"]}


def _inventory(raw, transform, key):
    rows = {}
    invalid = False
    for entry in raw:
        row = transform(entry)
        if row is None or row[key] in rows:
            invalid = True
        else:
            rows[row[key]] = row
    return [rows[value] for value in sorted(rows)], invalid


def _main_sha(runner, root):
    data, _ = _get(runner, root, "git/ref/heads/main", "{ref, object: {type: .object.type, sha: .object.sha}}")
    if not isinstance(data, dict) or data.get("ref") != "refs/heads/main":
        return None
    target = data.get("object")
    if isinstance(target, dict) and target.get("type") == "commit" and _sha(target.get("sha")):
        return target["sha"]
    return None


def _required_checks(runner, root):
    rows, _, error = _pages(runner, root, "rules/branches/main", _RULE_FIELDS)
    if error:
        return {}, "required_checks_unavailable"
    contexts = {}
    for row in rows:
        if not isinstance(row, dict):
            return {}, "invalid_required_check"
        context, app = row.get("context"), row.get("integration_id")
        if not _text(context, 256) or type(app) is not int or app <= 0 or context in contexts:
            return {}, "invalid_required_check"
        contexts[context] = app
    return contexts, None if contexts else "no_required_checks"


def _verify_checks(runner, root, sha, contexts):
    rows, _, error = _pages(runner, root, f"commits/{sha}/check-runs?filter=latest", _CHECK_FIELDS)
    if error:
        return "check_runs_unavailable"
    observed = set()
    for row in rows:
        if not isinstance(row, dict) or not _text(row.get("name"), 256):
            return "invalid_check_run"
        name = row["name"]
        if name not in contexts:
            continue
        if name in observed:
            return "duplicate_required_check"
        if row.get("head_sha") != sha or row.get("app_id") != contexts[name]:
            return "required_check_source_mismatch"
        if row.get("status") != "completed" or row.get("conclusion") != "success":
            return "required_check_not_successful"
        observed.add(name)
    return "verified" if observed == contexts.keys() else "required_check_missing"


def _record_inventory(result, runner, root, *, source, path, fields, transform, key):
    raw, pages, error = _pages(runner, root, path, fields)
    rows, invalid = _inventory(raw, transform, key)
    result[source] = rows
    result["pages"][source] = pages
    if error or invalid:
        result["errors"].append(f"{source}_{error or 'invalid_row'}")
        result["coverage_by_source"][source] = "partial" if rows or pages else "unavailable"
    else:
        result["coverage_by_source"][source] = "complete"


def observe_github(repo_root: Path, *, runner, tracked_prs: tuple[int, ...] = ()) -> dict:
    """Observe canonical GitHub refs, PRs and checks using only injected reads.

    Branch and PR inventories have independent coverage. Check proof is separate
    from inventory coverage and describes only the specified commit revision.
    """
    sources = ("main", "pull_requests", "branches", "tracked_pull_requests")
    result = {
        "repository": None, "main_sha": None, "coverage": "unavailable",
        "pull_requests": [], "branches": [], "tracked_pull_requests": [], "tracked_lookups": [],
        "coverage_by_source": dict.fromkeys(sources, "unavailable"),
        "pages": dict.fromkeys(sources, 0), "errors": [],
        "main_checks": {"verified": False, "reason": "main_unavailable"},
    }
    remotes = _run(runner, repo_root, ["git", "remote", "get-url", "--all", "origin"])
    urls = remotes.splitlines() if remotes is not None else []
    if len(urls) != 1 or _REMOTE.fullmatch(urls[0]) is None:
        result["errors"].append("origin_unavailable" if remotes is None else "origin_not_canonical")
        return result
    result["repository"] = _REPOSITORY

    main_sha = _main_sha(runner, repo_root)
    result["main_sha"] = main_sha
    if main_sha is None:
        result["errors"].append("main_unavailable")
    else:
        result["coverage_by_source"]["main"] = "complete"
        result["pages"]["main"] = 1

    _record_inventory(
        result, runner, repo_root, source="pull_requests",
        path="pulls?state=open&sort=created&direction=asc",
        fields=f"[.[] | {_PR_FIELDS}]", transform=_open_pr_row, key="number",
    )
    _record_inventory(
        result, runner, repo_root, source="branches", path="branches",
        fields=_BRANCH_FIELDS, transform=_branch_row, key="ref",
    )
    branch_main = next((branch for branch in result["branches"] if branch["ref"] == "main"), None)
    if main_sha and result["coverage_by_source"]["branches"] == "complete" and (
        branch_main is None or branch_main["sha"] != main_sha
    ):
        result["errors"].append("main_branch_mismatch")
        result["coverage_by_source"]["branches"] = "partial"

    contexts, rules_error = _required_checks(runner, repo_root) if main_sha else ({}, "main_unavailable")
    reason = rules_error or _verify_checks(runner, repo_root, main_sha, contexts)
    if reason == "verified" and _main_sha(runner, repo_root) != main_sha:
        reason = "main_changed_during_observation"
        result["coverage_by_source"]["main"] = "partial"
        result["errors"].append(reason)
    result["main_checks"] = {"verified": reason == "verified", "reason": reason}

    tracked = result["tracked_pull_requests"]
    if all(map(_pr_number, tracked_prs)):
        requested = tuple(dict.fromkeys(tracked_prs))
        known_open = (
            {row["number"]: row for row in result["pull_requests"]}
            if result["coverage_by_source"]["pull_requests"] == "complete" else {}
        )
        tracked.extend(dict(known_open[number]) for number in requested if number in known_open)
        missing_from_open = [number for number in requested if number not in known_open]
        if len(missing_from_open) > _TRACKED_LIMIT:
            result["errors"].append("tracked_pull_request_lookup_limit")
        check_proof = {main_sha: reason} if main_sha else {}
        for number in missing_from_open[:_TRACKED_LIMIT]:
            result["tracked_lookups"].append(number)
            data, _ = _get(runner, repo_root, f"pulls/{number}", _PR_FIELDS)
            row = _pr_row(data, expected_number=number)
            if row is None:
                result["errors"].append("tracked_pull_request_unavailable")
                continue
            result["pages"]["tracked_pull_requests"] += 1
            if row["merged"]:
                sha = row["merge_sha"]
                if sha not in check_proof:
                    check_proof[sha] = rules_error or _verify_checks(runner, repo_root, sha, contexts)
                row["checks_verified"] = check_proof[sha] == "verified"
            tracked.append(row)
        tracked.sort(key=lambda row: row["number"])
        result["coverage_by_source"]["tracked_pull_requests"] = (
            "complete" if len(tracked) == len(requested) else
            "partial" if tracked else "unavailable"
        )
    else:
        result["errors"].append("tracked_pull_request_invalid")

    coverage = result["coverage_by_source"]
    if all(value == "complete" for value in coverage.values()):
        result["coverage"] = "complete"
    elif any(coverage[source] != "unavailable" for source in sources[:3]) or tracked:
        result["coverage"] = "partial"
    return result
