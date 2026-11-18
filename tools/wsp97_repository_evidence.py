#!/usr/bin/env python3
"""Bounded repository validation for WSP 97 ``retrieve_wsps`` evidence."""

from __future__ import annotations

import os
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Callable, Mapping, Sequence


WSP_PATH_PATTERN = re.compile(
    r"^WSP_framework/src/(WSP_(?P<number>[0-9]+)_[A-Za-z0-9][A-Za-z0-9_-]*\.md)$"
)
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
WSP_ID_PATTERN = re.compile(r"^WSP_[0-9]+$")
MAX_GIT_CALLS = 72
GIT_TIMEOUT_SECONDS = 5.0
MAX_ACCEPTED_GIT_OUTPUT_BYTES = 65_536
Lstat = Callable[[Path], Any]


class RepositoryOperationalError(ValueError):
    """Raised when bounded repository inspection cannot be established."""


@dataclass
class GitQueryBudget:
    """Shared per-validation process-call budget."""

    max_calls: int = MAX_GIT_CALLS
    calls: int = 0

    def claim(self) -> None:
        """Claim one Git process call or fail before spawning it."""
        if self.calls >= self.max_calls:
            raise RepositoryOperationalError("Git query budget exceeded")
        self.calls += 1


@dataclass(frozen=True)
class GitResult:
    """Bounded Git process result."""

    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class RepositoryEvidenceResult:
    """Deterministic result for the repository-resolved receipt slice."""

    violations: tuple[str, ...]
    retrieved_wsp_ids: tuple[str, ...]
    base_commit: str
    head_commit: str


def _read_bounded_output(stream: Any, label: str) -> str:
    """Read one seekable process stream only after enforcing its byte cap."""
    stream.flush()
    size = stream.tell()
    if size > MAX_ACCEPTED_GIT_OUTPUT_BYTES:
        raise RepositoryOperationalError(
            f"Git {label} accepted output limit exceeded"
        )
    stream.seek(0)
    return stream.read(MAX_ACCEPTED_GIT_OUTPUT_BYTES + 1).decode(
        "utf-8", errors="replace"
    )


def _run_git(
    repo_root: Path,
    *args: str,
    budget: GitQueryBudget | None = None,
) -> GitResult:
    """Run one shell-free Git query with call, time, and output bounds."""
    active_budget = budget if budget is not None else GitQueryBudget()
    active_budget.claim()
    try:
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            completed = subprocess.run(
                ["git", "-C", str(repo_root), *args],
                stdout=stdout,
                stderr=stderr,
                timeout=GIT_TIMEOUT_SECONDS,
                check=False,
            )
            output = _read_bounded_output(stdout, "stdout")
            error = _read_bounded_output(stderr, "stderr")
    except subprocess.TimeoutExpired as exc:
        raise RepositoryOperationalError("Git query timed out") from exc
    except OSError as exc:
        raise RepositoryOperationalError("Git process could not be started") from exc
    return GitResult(completed.returncode, output, error)


def _is_reparse_or_symlink(path: Path, *, lstat: Lstat = os.lstat) -> bool:
    """Return whether one path component redirects filesystem resolution."""
    metadata = lstat(path)
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)


def _components_from_anchor(path: Path) -> tuple[Path, ...]:
    """Return all absolute path components, including anchor and final path."""
    anchor = Path(path.anchor)
    current = anchor
    components: list[Path] = [anchor] if path.anchor else []
    for part in path.parts[1:] if path.anchor else path.parts:
        current = current / part
        components.append(current)
    return tuple(components)


def _preflight_root_components(path: Path, *, lstat: Lstat) -> None:
    """lstat every supplied root component before any following operation."""
    try:
        for component in _components_from_anchor(path.absolute()):
            if _is_reparse_or_symlink(component, lstat=lstat):
                raise RepositoryOperationalError(
                    "repository root crosses a symlink, junction, or reparse point"
                )
    except OSError as exc:
        raise RepositoryOperationalError("repository root component is unreadable") from exc


def _portable_absolute(path: Path) -> str:
    """Return a slash-normalized absolute spelling without resolving links."""
    value = path.absolute().as_posix()
    return value.removeprefix("//?/")


def resolve_git_toplevel(
    repo_root: Path | str,
    *,
    lstat: Lstat = os.lstat,
    git_runner: Callable[..., GitResult] = _run_git,
    budget: GitQueryBudget | None = None,
) -> Path:
    """Validate and return an exact, non-redirecting Git worktree root."""
    supplied = Path(repo_root).expanduser()
    _preflight_root_components(supplied, lstat=lstat)
    if not supplied.exists() or not supplied.is_dir():
        raise RepositoryOperationalError(
            f"repository root is not a readable directory: {supplied}"
        )
    active_budget = budget if budget is not None else GitQueryBudget()
    completed = git_runner(
        supplied, "rev-parse", "--show-toplevel", budget=active_budget
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise RepositoryOperationalError("repository root is not a Git worktree")
    git_spelling = completed.stdout.strip().replace("\\", "/").removeprefix("//?/")
    if _portable_absolute(supplied) != git_spelling:
        raise RepositoryOperationalError(
            "repository root must be the exact-case Git top-level"
        )
    return supplied.resolve(strict=True)


def _base_violations(
    receipt: Mapping[str, Any],
    repo_root: Path,
    expected_base: str | None,
    budget: GitQueryBudget,
) -> tuple[list[str], str, str]:
    """Validate receipt base binding and ancestry against the invoking worktree."""
    violations: list[str] = []
    context = receipt.get("repository_context")
    base = context.get("base_commit") if isinstance(context, Mapping) else None
    if expected_base is not None and not COMMIT_PATTERN.fullmatch(expected_base):
        raise RepositoryOperationalError(
            "expected_base must be an exact lowercase 40-character commit"
        )
    if not isinstance(base, str) or not COMMIT_PATTERN.fullmatch(base):
        violations.append("invalid_repository_context")
        base = ""
    head_result = _run_git(repo_root, "rev-parse", "HEAD", budget=budget)
    if head_result.returncode != 0:
        raise RepositoryOperationalError("unable to resolve repository HEAD")
    head = head_result.stdout.strip()
    if expected_base is not None and base != expected_base:
        violations.append("expected_base_mismatch")
    if not base:
        return violations, base, head
    exists = _run_git(repo_root, "cat-file", "-e", f"{base}^{{commit}}", budget=budget)
    if exists.returncode != 0:
        violations.append("base_commit_not_found")
        return violations, base, head
    ancestor = _run_git(repo_root, "merge-base", "--is-ancestor", base, head, budget=budget)
    if ancestor.returncode == 1:
        violations.append("base_commit_not_ancestor")
    elif ancestor.returncode != 0:
        raise RepositoryOperationalError("unable to establish base ancestry")
    return violations, base, head


def lexical_wsp_id(reference: str) -> tuple[str | None, str | None]:
    """Validate canonical POSIX WSP path form and return its WSP identifier."""
    if reference != reference.strip():
        return None, "not_exact_posix_path"
    windows = PureWindowsPath(reference)
    posix = PurePosixPath(reference)
    if windows.drive or windows.root or posix.is_absolute():
        return None, "absolute_or_drive_path"
    if "\\" in reference or ".." in posix.parts or "." in posix.parts:
        return None, "noncanonical_or_traversal_path"
    if any(marker in reference for marker in ("#", "?", "://")):
        return None, "fragment_query_or_url"
    match = WSP_PATH_PATTERN.fullmatch(reference)
    if match is None:
        return None, "not_canonical_framework_wsp"
    return f"WSP_{match.group('number')}", None


def _tracked_case_violation(
    repo_root: Path,
    reference: str,
    budget: GitQueryBudget,
) -> str | None:
    """Return a violation when Git does not track the exact path spelling."""
    result = _run_git(
        repo_root,
        "ls-files",
        "--error-unmatch",
        "--full-name",
        "--",
        f":(literal){reference}",
        budget=budget,
    )
    if result.returncode == 0 and result.stdout.strip() == reference:
        return None
    if result.returncode in (0, 1):
        return "not_tracked"
    raise RepositoryOperationalError("unable to query tracked WSP path")


def _filesystem_violation(repo_root: Path, reference: str) -> str | None:
    """Return a confinement violation for the tracked filesystem path."""
    candidate = repo_root.joinpath(*PurePosixPath(reference).parts)
    try:
        for component in _components_from_anchor(candidate.absolute()):
            if _is_reparse_or_symlink(component):
                return "reparse_or_symlink"
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        return "missing_or_unreadable"
    try:
        if os.path.commonpath((str(repo_root), str(resolved))) != str(repo_root):
            return "outside_repository"
    except ValueError:
        return "outside_repository"
    return None if resolved.is_file() else "not_regular_file"


def _validate_retrieved_wsps(
    repo_root: Path,
    references: Sequence[str],
    budget: GitQueryBudget,
) -> tuple[list[str], set[str]]:
    """Validate each retrieved WSP and collect canonical identifiers."""
    violations: list[str] = []
    identifiers: set[str] = set()
    seen: set[str] = set()
    for index, reference in enumerate(references):
        if reference in seen:
            violations.append(f"invalid_retrieve_wsp:{index}:duplicate_path")
            continue
        seen.add(reference)
        wsp_id, reason = lexical_wsp_id(reference)
        if reason is None:
            reason = _tracked_case_violation(repo_root, reference, budget)
        if reason is None:
            reason = _filesystem_violation(repo_root, reference)
        if reason is not None:
            violations.append(f"invalid_retrieve_wsp:{index}:{reason}")
        elif wsp_id is not None:
            identifiers.add(wsp_id)
    return violations, identifiers


def validate_repository_evidence(
    receipt: Mapping[str, Any],
    *,
    repo_root: Path | str,
    retrieve_wsps: Sequence[str],
    wsps_applied: Sequence[str],
    expected_base: str | None = None,
) -> RepositoryEvidenceResult:
    """Resolve only canonical WSP retrieval evidence inside one Git worktree."""
    budget = GitQueryBudget()
    root = resolve_git_toplevel(repo_root, budget=budget)
    violations, base, head = _base_violations(receipt, root, expected_base, budget)
    path_violations, retrieved_ids = _validate_retrieved_wsps(
        root, retrieve_wsps, budget
    )
    violations.extend(path_violations)
    for wsp_id in wsps_applied:
        if not WSP_ID_PATTERN.fullmatch(wsp_id):
            violations.append(f"invalid_wsp_identifier:{wsp_id}")
        elif wsp_id not in retrieved_ids:
            violations.append(f"wsp_not_retrieved:{wsp_id}")
    return RepositoryEvidenceResult(
        violations=tuple(violations),
        retrieved_wsp_ids=tuple(sorted(retrieved_ids)),
        base_commit=base,
        head_commit=head,
    )
