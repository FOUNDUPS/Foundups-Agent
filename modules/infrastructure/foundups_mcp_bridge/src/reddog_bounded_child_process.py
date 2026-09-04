"""Shared bounded execution for one RedDog-owned child process."""

from __future__ import annotations

import math
import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field

from .reddog_windows_job_object import (
    CREATE_SUSPENDED,
    attach_windows_kill_on_close_job,
)


CHILD_STDOUT_MAX_BYTES = 16 * 1024
CHILD_STDOUT_CHUNK_BYTES = 4096
CHILD_CAPTURE_CLEANUP_SECONDS = 1.0


@dataclass
class BoundedChildCapture:
    """Bounded output retained only until its caller validates it."""

    stdout: bytearray = field(default_factory=bytearray)
    oversized: bool = False
    read_failed: bool = False


@dataclass(frozen=True)
class BoundedChildResult:
    returncode: int
    stdout: bytes
    output_oversized: bool = False
    output_read_failed: bool = False


def _drain_child_stdout(stream, capture: BoundedChildCapture) -> None:
    try:
        while True:
            chunk = stream.read(CHILD_STDOUT_CHUNK_BYTES)
            if not chunk:
                return
            remaining = CHILD_STDOUT_MAX_BYTES - len(capture.stdout)
            if remaining > 0:
                capture.stdout.extend(chunk[:remaining])
            if len(chunk) > remaining:
                capture.oversized = True
    except (OSError, ValueError):
        capture.read_failed = True
    finally:
        try:
            stream.close()
        except (OSError, ValueError):
            pass


def _close_child_tree_guard(process) -> None:
    guard = getattr(process, "_reddog_tree_guard", None)
    if guard is not None:
        guard.close()
        process._reddog_tree_guard = None


def _terminate_child_tree(process) -> None:
    cleanup_error = None
    try:
        _close_child_tree_guard(process)
    except OSError as exc:
        cleanup_error = exc
    if os.name != "nt":
        try:
            os.killpg(int(process.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError, ValueError):
            pass
    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.wait(timeout=CHILD_CAPTURE_CLEANUP_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    if cleanup_error is not None:
        raise OSError("bounded child Job termination failed") from cleanup_error


def _runner_settings(kwargs: dict[str, object]) -> tuple[float, str]:
    timeout = kwargs.pop("timeout", None)
    reader_name = str(
        kwargs.pop("_reader_name", "reddog-bounded-child-output")
    )
    kwargs.pop("check", None)
    if (
        type(timeout) not in {int, float}
        or not math.isfinite(float(timeout))
        or float(timeout) <= 0
    ):
        raise ValueError("bounded child timeout invalid")
    if (
        kwargs.get("stdin") is not subprocess.DEVNULL
        or kwargs.get("stdout") is not subprocess.PIPE
        or kwargs.get("stderr") is not subprocess.DEVNULL
        or kwargs.get("shell") is not False
    ):
        raise ValueError("bounded child process shape invalid")
    return float(timeout), reader_name


def _wait_for_child(
    process, capture: BoundedChildCapture, timeout: float,
) -> int:
    deadline = time.monotonic() + timeout
    while True:
        if capture.oversized:
            _terminate_child_tree(process)
            returncode = process.poll()
            if returncode is None:
                raise subprocess.TimeoutExpired(process.args, timeout)
            return int(returncode)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _terminate_child_tree(process)
            raise subprocess.TimeoutExpired(process.args, timeout)
        try:
            return int(process.wait(timeout=min(remaining, 0.05)))
        except subprocess.TimeoutExpired:
            continue


def _start_bounded_child(command, kwargs):
    timeout, reader_name = _runner_settings(kwargs)
    kwargs["bufsize"] = 0
    if os.name == "nt":
        kwargs["creationflags"] = int(kwargs.get("creationflags", 0)) | int(
            subprocess.CREATE_NEW_PROCESS_GROUP | CREATE_SUSPENDED
        )
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen(command, **kwargs)
    try:
        process._reddog_tree_guard = attach_windows_kill_on_close_job(process)
    except (OSError, ValueError):
        _terminate_child_tree(process)
        raise OSError("bounded child tree guard unavailable") from None
    if process.stdout is None:
        _terminate_child_tree(process)
        raise OSError("bounded child stdout unavailable")
    return process, timeout, reader_name


def _start_capture_reader(process, capture, reader_name):
    try:
        reader = threading.Thread(
            target=_drain_child_stdout,
            args=(process.stdout, capture),
            name=reader_name,
            daemon=True,
        )
        reader.start()
        return reader
    except BaseException:
        cleanup_error = None
        try:
            _terminate_child_tree(process)
        except OSError as exc:
            cleanup_error = exc
        try:
            process.stdout.close()
        except (OSError, ValueError):
            pass
        if cleanup_error is not None:
            raise OSError("bounded child reader startup cleanup failed") from cleanup_error
        raise


def bounded_child_runner(command, **kwargs) -> BoundedChildResult:
    """Run one child with bounded memory/time and no stderr or disk capture."""

    process, timeout, reader_name = _start_bounded_child(command, kwargs)
    capture = BoundedChildCapture()
    reader = _start_capture_reader(process, capture, reader_name)
    try:
        try:
            returncode = _wait_for_child(process, capture, timeout)
        except subprocess.TimeoutExpired:
            reader.join(timeout=CHILD_CAPTURE_CLEANUP_SECONDS)
            raise
        reader.join(timeout=CHILD_CAPTURE_CLEANUP_SECONDS)
        if reader.is_alive():
            capture.read_failed = True
            _terminate_child_tree(process)
            try:
                process.stdout.close()
            except (OSError, ValueError):
                pass
            reader.join(timeout=CHILD_CAPTURE_CLEANUP_SECONDS)
        return BoundedChildResult(
            returncode=returncode,
            stdout=bytes(capture.stdout),
            output_oversized=capture.oversized,
            output_read_failed=capture.read_failed or reader.is_alive(),
        )
    finally:
        _close_child_tree_guard(process)


__all__ = [
    "BoundedChildResult", "CHILD_STDOUT_MAX_BYTES", "bounded_child_runner",
]
