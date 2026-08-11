"""Bounded Git stdout capture and exact commit resolution."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import threading
from typing import Sequence

_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
_CHUNK_BYTES = 64 * 1024


def resolve_exact_commit(repo: Path, sha: str) -> str:
    """Require a full lowercase SHA that resolves to that exact commit object."""
    validate_commit_sha(sha)
    raw = run_bounded_stdout(
        ("git", "-C", str(repo), "rev-parse", "--verify", "--end-of-options",
         f"{sha}^{{commit}}"),
        cwd=repo, max_bytes=128, timeout_s=30,
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


def run_bounded_stdout(
    argv: Sequence[str], *, cwd: Path, max_bytes: int, timeout_s: int,
) -> bytes:
    """Capture stdout while terminating the process at the byte ceiling."""
    chunks: list[bytes] = []
    _run_bounded(argv, cwd=cwd, max_bytes=max_bytes, timeout_s=timeout_s,
                 chunks=chunks, output_path=None)
    return b"".join(chunks)


def run_bounded_stdout_file(
    argv: Sequence[str], *, cwd: Path, output_path: Path,
    max_bytes: int, timeout_s: int,
) -> None:
    """Write stdout to a new file while enforcing the byte ceiling."""
    _run_bounded(argv, cwd=cwd, max_bytes=max_bytes, timeout_s=timeout_s,
                 chunks=None, output_path=output_path)


def _run_bounded(
    argv: Sequence[str], *, cwd: Path, max_bytes: int, timeout_s: int,
    chunks: list[bytes] | None, output_path: Path | None,
) -> None:
    if max_bytes < 1 or timeout_s < 1 or bool(chunks is None) != bool(output_path):
        raise ValueError("bounded_git_output_configuration_invalid")
    process = subprocess.Popen(
        list(argv), cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        shell=False,
    )
    state: dict[str, BaseException | bool] = {"exceeded": False}
    thread = threading.Thread(
        target=_copy_stdout,
        args=(process, max_bytes, chunks, output_path, state), daemon=True,
    )
    thread.start()
    try:
        returncode = process.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        _terminate_reader(process, thread)
        raise
    thread.join(timeout=5)
    if thread.is_alive():
        process.kill()
        raise RuntimeError("bounded_git_output_reader_stalled")
    error = state.get("error")
    if isinstance(error, BaseException):
        raise error
    if state["exceeded"] is True:
        raise ValueError("bounded_git_output_exceeded")
    if returncode != 0:
        raise subprocess.CalledProcessError(returncode, list(argv))


def _terminate_reader(
    process: subprocess.Popen[bytes], thread: threading.Thread,
) -> None:
    if process.poll() is None:
        process.kill()
    process.wait(timeout=30)
    if process.stdout is not None:
        process.stdout.close()
    thread.join(timeout=5)
    if thread.is_alive():
        raise RuntimeError("bounded_git_output_reader_stalled")


def _copy_stdout(
    process: subprocess.Popen[bytes], max_bytes: int, chunks: list[bytes] | None,
    output_path: Path | None, state: dict[str, BaseException | bool],
) -> None:
    total = 0
    output = None
    try:
        output = output_path.open("xb") if output_path is not None else None
        assert process.stdout is not None
        while chunk := process.stdout.read(_CHUNK_BYTES):
            total += len(chunk)
            if total > max_bytes:
                state["exceeded"] = True
                process.kill()
                return
            if output is not None:
                output.write(chunk)
            else:
                assert chunks is not None
                chunks.append(chunk)
    except BaseException as exc:
        state["error"] = exc
        process.kill()
    finally:
        if output is not None:
            output.close()


__all__ = [
    "resolve_exact_commit", "run_bounded_stdout", "run_bounded_stdout_file",
    "validate_commit_sha",
]
