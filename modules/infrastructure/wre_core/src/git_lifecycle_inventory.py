"""Bounded, read-only Git evidence for the FoundUps PC checkout."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .git_lifecycle import _common_dir, _pc_worktree, run_command
from .git_lifecycle_github import _REMOTE, _REPOSITORY


_SCHEMA = "foundups_git_inventory.v1"
_REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{8,80}")
_SHA = re.compile(r"[0-9a-f]{40}")
_REF_PREFIX = "refs/heads/"
_ORIGIN = f"https://github.com/{_REPOSITORY}.git"
_MAX_ROWS = 2048
_MAX_OUTPUT = 512_000
_MAX_RECEIPT = 256 * 1024
_PAGE_SIZE = 20
_BACKLOG_KEYS = frozenset({
    "local_head_count", "attached_worktree_branch_count",
    "merged_into_github_main_count", "unmerged_unattached_head_count",
    "stash_count",
})
_WORKTREE_SUMMARY_KEYS = frozenset({
    "total", "attached", "detached", "bare", "locked", "prunable",
})


class _InventoryError(ValueError):
    pass


def _canonical(value: dict) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _valid_request_id(value: object) -> bool:
    return isinstance(value, str) and _REQUEST_ID.fullmatch(value) is not None


def _valid_branch(ref: str) -> bool:
    name = ref.removeprefix(_REF_PREFIX)
    return (
        ref.startswith(_REF_PREFIX)
        and 0 < len(name) <= 512
        and name.isprintable()
        and "\ufffd" not in name
    )


def _parse_branches(output: str, *, remote: bool) -> dict[str, str]:
    branches = {}
    for line in output.split("\n"):
        if not line:
            continue
        if remote:
            sha, separator, ref = line.partition("\t")
        else:
            ref, separator, sha = line.partition("\0")
        if (
            not separator or not _valid_branch(ref) or _SHA.fullmatch(sha) is None
            or ref in branches or len(branches) >= _MAX_ROWS
        ):
            raise _InventoryError("branch_inventory_invalid_or_too_large")
        branches[ref] = sha
    return branches


def _parse_worktrees(output: str, selected: Path) -> list[dict]:
    rows = []
    selected_count = 0
    for record in output.rstrip("\0").split("\0\0"):
        path, *fields = record.split("\0")
        if not path.startswith("worktree ") or len(rows) >= _MAX_ROWS:
            raise _InventoryError("worktree_inventory_invalid_or_too_large")
        fields_by_key = {}
        for field in fields:
            key, _, value = field.partition(" ")
            if key in fields_by_key or key not in {
                "HEAD", "branch", "bare", "detached", "locked", "prunable",
            }:
                raise _InventoryError("worktree_inventory_invalid_or_too_large")
            fields_by_key[key] = value
        head = fields_by_key.get("HEAD")
        branch = fields_by_key.get("branch")
        bare = "bare" in fields_by_key
        detached = "detached" in fields_by_key
        if (
            (not bare and (head is None or _SHA.fullmatch(head) is None))
            or (bare and (head is not None or branch is not None or detached))
            or (not bare and (branch is None) != detached)
            or (branch is not None and not _valid_branch(branch))
        ):
            raise _InventoryError("worktree_inventory_invalid_or_too_large")
        is_selected = Path(path.removeprefix("worktree ")) == selected
        selected_count += int(is_selected)
        rows.append({
            "head": head, "branch": branch, "bare": bare, "detached": detached,
            "locked": "locked" in fields_by_key, "prunable": "prunable" in fields_by_key,
            "selected": is_selected,
        })
    if selected_count != 1:
        raise _InventoryError("selected_worktree_unverified")
    return rows


def _read_stashes(git_fn, root: Path) -> list[dict]:
    tip = git_fn(
        root, "for-each-ref", "--format=%(objectname)", "refs/stash",
        reason="stash_inventory_unavailable",
    ).removesuffix("\n")
    if not tip.strip():
        return []
    if _SHA.fullmatch(tip) is None:
        raise _InventoryError("stash_inventory_invalid_or_too_large")
    output = git_fn(
        root, "rev-list", "--walk-reflogs", "refs/stash",
        reason="stash_inventory_unavailable",
    )
    shas = output.removesuffix("\n").split("\n") if output else []
    if not 1 <= len(shas) <= _MAX_ROWS or any(_SHA.fullmatch(sha) is None for sha in shas):
        raise _InventoryError("stash_inventory_invalid_or_too_large")
    return [{"sha": sha} for sha in shas]


def _observe(root: Path, runner) -> dict:
    deadline = time.monotonic() + 25

    def bounded_runner(args, *, cwd, timeout):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(args, 25)
        return runner(args, cwd=cwd, timeout=min(timeout, remaining))

    def git(cwd: Path, *args: str, reason: str, timeout: int = 6) -> str:
        try:
            result = bounded_runner(
                ("git", "--no-replace-objects", "--no-optional-locks",
                 "-c", "core.fsmonitor=false", *args),
                cwd=cwd, timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError, UnicodeError):
            raise _InventoryError(reason) from None
        if result.returncode or not isinstance(result.stdout, str) or len(result.stdout) > _MAX_OUTPUT:
            raise _InventoryError(reason)
        return result.stdout

    def origin() -> str:
        value = git(root, "remote", "get-url", "--all", "origin", reason="origin_unverified")
        value = value.removesuffix("\n")
        if _REMOTE.fullmatch(value) is None:
            raise _InventoryError("origin_unverified")
        return value

    expected_origin = origin()
    common = _common_dir(bounded_runner, root)
    selected = _pc_worktree(root, common, bounded_runner) if common is not None else None
    if selected is None:
        raise _InventoryError("selected_worktree_unverified")

    def local() -> tuple[dict, list, list, bool]:
        branches = _parse_branches(git(
            root, "for-each-ref", "--format=%(refname)%00%(objectname)", "refs/heads",
            reason="local_branches_unavailable",
        ), remote=False)
        worktrees = _parse_worktrees(git(
            root, "worktree", "list", "--porcelain", "-z", reason="worktrees_unavailable",
        ), selected)
        stashes = _read_stashes(git, root)
        status = git(
            selected, "status", "--porcelain=v1", "-z", "--untracked-files=normal",
            "--ignore-submodules=none", reason="selected_status_unavailable",
        )
        return branches, worktrees, stashes, not status

    before = local()
    if git(
        root, "ls-remote", "--get-url", _ORIGIN, reason="github_route_unverified",
    ).removesuffix("\n") != _ORIGIN:
        raise _InventoryError("github_route_unverified")
    remote = _parse_branches(git(
        root, "-c", "credential.helper=", "-c", "protocol.allow=never",
        "-c", "protocol.https.allow=always", "-c", "http.followRedirects=false",
        "-c", "http.sslVerify=true", "ls-remote", "--exit-code", "--refs", "--heads", _ORIGIN,
        reason="github_branches_unavailable", timeout=10,
    ), remote=True)
    github_main = remote.get("refs/heads/main")
    if github_main is None:
        raise _InventoryError("github_main_unverified")

    if (
        local() != before or origin() != expected_origin
        or _pc_worktree(root, common, bounded_runner) != selected
    ):
        raise _InventoryError("pc_state_changed_during_observation")
    local_branches, worktrees, stashes, clean = before
    current = next(row for row in worktrees if row["selected"])
    if current["head"] is None:
        raise _InventoryError("selected_head_unverified")
    try:
        cat_result = bounded_runner(
            ("git", "--no-replace-objects", "--no-optional-locks",
             "-c", "core.fsmonitor=false", "cat-file", "-t", f"{github_main}^{{commit}}"),
            cwd=root, timeout=6,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise _InventoryError("github_main_local_check_unavailable") from None
    github_main_present_on_pc = (
        cat_result.returncode == 0
        and isinstance(cat_result.stdout, str)
        and cat_result.stdout.strip() == "commit"
    )
    merged_refs = (
        _parse_branches(git(
            root, "for-each-ref", f"--merged={github_main}",
            "--format=%(refname)%00%(objectname)", "refs/heads",
            reason="merged_branches_unavailable",
        ), remote=False)
        if github_main_present_on_pc
        else None
    )
    attached_branches = {row["branch"] for row in worktrees if row["branch"] is not None}
    return {
        "repository": _REPOSITORY,
        "observed_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "selected_pc": {"head": current["head"], "branch": current["branch"], "clean": clean},
        "github_main": github_main,
        "github_main_present_on_pc": github_main_present_on_pc,
        "branches": [
            {"ref": ref, "pc": local_branches.get(ref), "github": remote.get(ref)}
            for ref in sorted(local_branches.keys() | remote.keys())
        ],
        "worktrees": worktrees,
        "stashes": stashes,
        "pc_backlog_summary": {
            "local_head_count": len(local_branches),
            "attached_worktree_branch_count": len(attached_branches),
            "merged_into_github_main_count": len(merged_refs) if merged_refs is not None else None,
            "unmerged_unattached_head_count": (
                sum(
                    ref not in merged_refs and ref not in attached_branches
                    for ref in local_branches
                )
                if merged_refs is not None
                else None
            ),
            "stash_count": len(stashes),
        },
        "worktree_summary": {
            "total": len(worktrees),
            "attached": sum(not row["bare"] and not row["detached"] for row in worktrees),
            "detached": sum(row["detached"] for row in worktrees),
            "bare": sum(row["bare"] for row in worktrees),
            "locked": sum(row["locked"] for row in worktrees),
            "prunable": sum(row["prunable"] for row in worktrees),
        },
    }


def _inventory_page(observation: dict, section: str, offset: int) -> dict:
    branches = observation["branches"]
    worktrees = observation["worktrees"]
    stashes = observation["stashes"]
    snapshot = {key: value for key, value in observation.items() if key != "observed_at"}
    rows = observation.get(section, [])
    end = offset + _PAGE_SIZE
    return {
        **observation,
        "inventory_sha256": hashlib.sha256(_canonical(snapshot)).hexdigest(),
        "branch_count": len(branches),
        "worktree_count": len(worktrees),
        "stash_count": len(stashes),
        "branch_comparison": {
            "same_tip": sum(row["pc"] == row["github"] for row in branches),
            "different_tip": sum(
                row["pc"] is not None and row["github"] is not None and row["pc"] != row["github"]
                for row in branches
            ),
            "pc_only": sum(row["github"] is None for row in branches),
            "github_only": sum(row["pc"] is None for row in branches),
        },
        "section": section,
        "offset": offset,
        "next_offset": end if end < len(rows) else None,
        "branches": rows[offset:end] if section == "branches" else [],
        "worktrees": rows[offset:end] if section == "worktrees" else [],
        "stashes": rows[offset:end] if section == "stashes" else [],
    }


def get_git_inventory(
    repo_root: Path, request_id: str, *, section: str | None = None, offset: int = 0,
    runner=run_command,
) -> dict:
    """Return fresh PC and GitHub branch IDs for the configured repository."""
    if not _valid_request_id(request_id):
        return {"status": "blocked", "reason": "request_id_invalid"}
    if (
        section not in (None, "summary", "branches", "worktrees", "stashes")
        or type(offset) is not int or not 0 <= offset <= 2 * _MAX_ROWS
        or (section in (None, "summary") and offset != 0)
    ):
        return {"status": "blocked", "reason": "page_invalid"}
    try:
        observation = _observe(Path(repo_root).resolve(), runner)
        if section is not None:
            observation = _inventory_page(observation, section, offset)
        receipt = {
            "schema_version": _SCHEMA, "request_id": request_id,
            **observation,
        }
        encoded = _canonical(receipt)
        if len(encoded) > _MAX_RECEIPT:
            raise _InventoryError("receipt_too_large")
    except _InventoryError as error:
        return {"status": "blocked", "reason": str(error)}
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
        return {"status": "blocked", "reason": "inventory_unavailable"}
    return {"status": "ok", "receipt": receipt, "sha256": hashlib.sha256(encoded).hexdigest()}


def _nonneg_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _valid_stashes(stashes: object) -> bool:
    return (
        isinstance(stashes, list)
        and len(stashes) <= _MAX_ROWS
        and all(
            isinstance(row, dict)
            and set(row) == {"sha"}
            and isinstance(row["sha"], str)
            and _SHA.fullmatch(row["sha"]) is not None
            for row in stashes
        )
    )


def _valid_summaries(receipt: dict) -> bool:
    present = receipt.get("github_main_present_on_pc")
    backlog = receipt.get("pc_backlog_summary")
    worktree_summary = receipt.get("worktree_summary")
    if (
        type(present) is not bool
        or not isinstance(backlog, dict) or set(backlog) != _BACKLOG_KEYS
        or not isinstance(worktree_summary, dict) or set(worktree_summary) != _WORKTREE_SUMMARY_KEYS
    ):
        return False
    if not all(_nonneg_int(backlog[k]) for k in (
        "local_head_count", "attached_worktree_branch_count", "stash_count",
    )):
        return False
    merged = backlog["merged_into_github_main_count"]
    unmerged = backlog["unmerged_unattached_head_count"]
    if present:
        if not (_nonneg_int(merged) and _nonneg_int(unmerged)):
            return False
        if merged > backlog["local_head_count"] or unmerged > backlog["local_head_count"]:
            return False
    elif merged is not None or unmerged is not None:
        return False
    if backlog["attached_worktree_branch_count"] > backlog["local_head_count"]:
        return False
    if not all(_nonneg_int(worktree_summary[k]) for k in _WORKTREE_SUMMARY_KEYS):
        return False
    if (
        worktree_summary["attached"] + worktree_summary["detached"] + worktree_summary["bare"]
        != worktree_summary["total"]
        or worktree_summary["locked"] > worktree_summary["total"]
        or worktree_summary["prunable"] > worktree_summary["total"]
    ):
        return False
    if "section" in receipt:
        return (
            receipt.get("stash_count") == backlog["stash_count"]
            and receipt.get("worktree_count") == worktree_summary["total"]
        )
    return (
        len(receipt["stashes"]) == backlog["stash_count"]
        and len(receipt["worktrees"]) == worktree_summary["total"]
    )


def verify_git_inventory_receipt(
    result: object, request_id: str, *, now: datetime | None = None,
) -> bool:
    """Verify receipt integrity and request binding for a trusted MCP response."""
    if not _valid_request_id(request_id) or not isinstance(result, dict) or result.get("status") != "ok":
        return False
    receipt = result.get("receipt")
    if (
        not isinstance(receipt, dict) or receipt.get("schema_version") != _SCHEMA
        or receipt.get("repository") != _REPOSITORY or receipt.get("request_id") != request_id
        or not isinstance(receipt.get("github_main"), str)
        or _SHA.fullmatch(receipt["github_main"]) is None
        or not isinstance(receipt.get("selected_pc"), dict)
        or not isinstance(receipt.get("branches"), list)
        or not isinstance(receipt.get("worktrees"), list)
        or not _valid_stashes(receipt.get("stashes"))
        or not _valid_summaries(receipt)
    ):
        return False
    try:
        observed = datetime.fromisoformat(receipt.get("observed_at"))
        if observed.tzinfo is None:
            return False
        age = ((now or datetime.now(timezone.utc)) - observed).total_seconds()
        if not -5 <= age <= 120:
            return False
        encoded = _canonical(receipt)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False
    return len(encoded) <= _MAX_RECEIPT and hashlib.sha256(encoded).hexdigest() == result.get("sha256")
