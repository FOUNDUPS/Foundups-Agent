"""Bounded Git stdout capture and exact commit resolution."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
from typing import Mapping, Sequence

from .wre_git_process_io import run_bounded_process

_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")


def resolve_exact_commit(repo: Path, sha: str) -> str:
    """Require a full lowercase SHA that resolves to that exact commit object."""
    validate_commit_sha(sha)
    raw = run_bounded_stdout(
        ("git", "--no-replace-objects", "-C", str(repo), "rev-parse",
         "--verify", "--end-of-options",
         f"{sha}^{{commit}}"),
        cwd=repo, max_bytes=128, timeout_s=30,
        environment=git_read_environment(),
    )
    resolved = raw.decode("ascii", errors="strict").strip()
    if resolved != sha:
        raise ValueError("git_commit_identity_mismatch")
    return resolved


def validate_commit_sha(sha: str) -> str:
    """Validate exact commit syntax without starting a Git process."""
    if not isinstance(sha, str) or _SHA.fullmatch(sha) is None:
        raise ValueError("git_commit_sha_invalid")
    return sha


def read_exact_git_blob(
    repo: Path, object_id: str, *, object_format: str, max_bytes: int,
) -> bytes:
    """Read one exact blob and independently verify its Git object ID."""
    expected_length = 40 if object_format == "sha1" else 64
    if (
        object_format not in {"sha1", "sha256"}
        or not isinstance(object_id, str) or len(object_id) != expected_length
        or any(char not in "0123456789abcdef" for char in object_id)
    ):
        raise ValueError("git_blob_identity_invalid")
    body = run_bounded_stdout(
        ("git", "--no-replace-objects", "-C", str(repo), "cat-file",
         "blob", object_id),
        cwd=repo, max_bytes=max_bytes, timeout_s=30,
        environment=git_read_environment(),
    )
    calculated = hashlib.new(object_format)
    calculated.update(f"blob {len(body)}\0".encode("ascii"))
    calculated.update(body)
    if calculated.hexdigest() != object_id:
        raise ValueError("git_blob_digest_mismatch")
    return body


def git_read_environment(
    environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Remove caller-controlled Git authority overrides for object reads."""
    source = os.environ if environment is None else environment
    result = {
        str(key): str(value) for key, value in source.items()
        if not str(key).upper().startswith("GIT_")
    }
    result["GIT_CONFIG_NOSYSTEM"] = "1"
    result["GIT_CONFIG_GLOBAL"] = os.devnull
    return result


def run_bounded_stdout(
    argv: Sequence[str], *, cwd: Path, max_bytes: int, timeout_s: int,
    environment: Mapping[str, str] | None = None,
    stdin_bytes: bytes | None = None,
) -> bytes:
    """Capture stdout while terminating the process at the byte ceiling."""
    chunks: list[bytes] = []
    run_bounded_process(
        argv, cwd=cwd, max_bytes=max_bytes, timeout_s=timeout_s,
        chunks=chunks, output_path=None, environment=environment,
        stdin_bytes=stdin_bytes,
    )
    return b"".join(chunks)


def run_bounded_stdout_file(
    argv: Sequence[str], *, cwd: Path, output_path: Path,
    max_bytes: int, timeout_s: int,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Write stdout to a new file while enforcing the byte ceiling."""
    run_bounded_process(
        argv, cwd=cwd, max_bytes=max_bytes, timeout_s=timeout_s,
        chunks=None, output_path=output_path, environment=environment,
        stdin_bytes=None,
    )


__all__ = [
    "git_read_environment", "read_exact_git_blob", "resolve_exact_commit",
    "run_bounded_stdout", "run_bounded_stdout_file", "validate_commit_sha",
]
