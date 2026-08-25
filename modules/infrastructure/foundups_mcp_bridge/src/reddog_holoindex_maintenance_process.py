"""Bounded process execution for governed RedDog HoloIndex maintenance."""

from __future__ import annotations

import os
import signal
import subprocess
import threading
from dataclasses import dataclass, field


REFRESH_STDOUT_MAX_BYTES = 16 * 1024
REFRESH_STDOUT_CHUNK_BYTES = 4096
REFRESH_CAPTURE_CLEANUP_SECONDS = 1.0


@dataclass
class BoundedRefreshCapture:
    """Bounded secret-bearing output retained only for local parsing."""

    stdout: bytearray = field(default_factory=bytearray)
    oversized: bool = False
    read_failed: bool = False


@dataclass(frozen=True)
class BoundedRefreshResult:
    returncode: int
    stdout: bytes
    output_oversized: bool = False
    output_read_failed: bool = False


def _drain_refresh_stdout(stream, capture: BoundedRefreshCapture) -> None:
    try:
        while True:
            chunk = stream.read(REFRESH_STDOUT_CHUNK_BYTES)
            if not chunk:
                return
            remaining = REFRESH_STDOUT_MAX_BYTES - len(capture.stdout)
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


def _terminate_refresh_tree(process) -> None:
    """Boundedly terminate only the exact refresh PID and its descendants."""

    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(int(process.pid)), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
                timeout=REFRESH_CAPTURE_CLEANUP_SECONDS,
                check=False,
            )
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    else:
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
        process.wait(timeout=REFRESH_CAPTURE_CLEANUP_SECONDS)
    except subprocess.TimeoutExpired:
        pass


def bounded_refresh_runner(command, **kwargs) -> BoundedRefreshResult:
    """Run one child with bounded memory/time and no stderr or disk capture."""

    timeout = float(kwargs.pop("timeout"))
    kwargs.pop("check", None)
    if kwargs.get("stdout") is not subprocess.PIPE:
        raise ValueError("bounded refresh requires stdout=PIPE")
    kwargs["bufsize"] = 0
    if os.name == "nt":
        kwargs["creationflags"] = int(kwargs.get("creationflags", 0)) | int(
            subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen(command, **kwargs)
    if process.stdout is None:
        _terminate_refresh_tree(process)
        raise OSError("bounded refresh stdout unavailable")
    capture = BoundedRefreshCapture()
    reader = threading.Thread(
        target=_drain_refresh_stdout,
        args=(process.stdout, capture),
        name="reddog-holo-refresh-output",
        daemon=True,
    )
    reader.start()
    try:
        returncode = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        _terminate_refresh_tree(process)
        reader.join(timeout=REFRESH_CAPTURE_CLEANUP_SECONDS)
        raise
    reader.join(timeout=REFRESH_CAPTURE_CLEANUP_SECONDS)
    if reader.is_alive():
        capture.read_failed = True
    return BoundedRefreshResult(
        returncode=returncode,
        stdout=bytes(capture.stdout),
        output_oversized=capture.oversized,
        output_read_failed=capture.read_failed or reader.is_alive(),
    )


__all__ = ["BoundedRefreshResult", "bounded_refresh_runner"]
