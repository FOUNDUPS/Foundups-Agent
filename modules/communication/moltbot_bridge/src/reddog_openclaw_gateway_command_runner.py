"""Shell-free command transport for the installed upstream OpenClaw CLI."""

from __future__ import annotations

import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from modules.infrastructure.dependency_launcher.src.wsl_agent_runtime import (
    DEFAULT_DISTRO,
    resolve_trusted_wsl_executable,
)


@dataclass(frozen=True)
class OpenClawCommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    process_started: bool = False
    termination_confirmed: bool = True
    output_limit_exceeded: bool = False


@dataclass(frozen=True)
class SystemOpenClawCommandRunner:
    """Invoke the canonical OpenClaw binary directly or through trusted WSL."""

    distro: str = DEFAULT_DISTRO
    executable: str = "/usr/local/bin/openclaw"
    max_output_bytes: int = 1_000_000

    def run(
        self, argv: Sequence[str], *, timeout_seconds: int
    ) -> OpenClawCommandResult:
        command = self._command(argv)
        if not command:
            return OpenClawCommandResult(127)
        if type(timeout_seconds) is not int or timeout_seconds < 1:
            return OpenClawCommandResult(127)
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )
        except (OSError, ValueError):
            return OpenClawCommandResult(127)
        stdout, stderr, overflow = bytearray(), bytearray(), threading.Event()
        threads = (
            threading.Thread(
                target=_read_bounded,
                args=(process.stdout, stdout, self.max_output_bytes, overflow),
                daemon=True,
            ),
            threading.Thread(
                target=_read_bounded,
                args=(process.stderr, stderr, self.max_output_bytes, overflow),
                daemon=True,
            ),
        )
        for thread in threads:
            thread.start()
        deadline = time.monotonic() + timeout_seconds
        while process.poll() is None and not overflow.is_set() and time.monotonic() < deadline:
            time.sleep(0.02)
        timed_out = process.poll() is None and time.monotonic() >= deadline
        exceeded = overflow.is_set()
        terminated = True
        if timed_out or exceeded:
            terminated = _stop_process(process)
        for thread in threads:
            thread.join(timeout=1)
        return OpenClawCommandResult(
            process.returncode if process.returncode is not None else 124,
            bytes(stdout).decode("utf-8", errors="replace"),
            bytes(stderr).decode("utf-8", errors="replace"),
            timed_out=timed_out,
            process_started=True,
            termination_confirmed=terminated,
            output_limit_exceeded=exceeded,
        )

    def _command(self, argv: Sequence[str]) -> list[str]:
        if not argv or argv[0] != "openclaw":
            return []
        arguments = list(argv[1:])
        if os.name != "nt":
            return [self.executable, *arguments]
        wsl = resolve_trusted_wsl_executable()
        if wsl is None or not _valid_distro(self.distro):
            return []
        had_message_file = "--message-file" in arguments
        arguments = _translate_message_file(arguments)
        if had_message_file and not arguments:
            return []
        return [
            str(wsl),
            "--distribution",
            self.distro,
            "--exec",
            self.executable,
            *arguments,
        ]


def _translate_message_file(arguments: list[str]) -> list[str]:
    if "--message-file" not in arguments:
        return arguments
    index = arguments.index("--message-file") + 1
    if index >= len(arguments):
        return []
    translated = _windows_path_to_wsl(arguments[index])
    if not translated:
        return []
    copy = list(arguments)
    copy[index] = translated
    return copy


def _windows_path_to_wsl(value: str) -> str:
    path = Path(value)
    drive = path.drive.rstrip(":").lower()
    if len(drive) != 1 or not drive.isalpha() or not path.is_absolute():
        return ""
    suffix = path.as_posix().split(":", 1)[-1].lstrip("/")
    return f"/mnt/{drive}/{suffix}"


def _valid_distro(value: str) -> bool:
    return bool(value) and len(value) <= 64 and all(
        char.isalnum() or char in "._-" for char in value
    )


def _read_bounded(stream, target: bytearray, limit: int, overflow: threading.Event) -> None:
    if stream is None:
        return
    try:
        while not overflow.is_set():
            chunk = stream.read(min(65536, limit + 1 - len(target)))
            if not chunk:
                break
            target.extend(chunk)
            if len(target) > limit:
                overflow.set()
    finally:
        stream.close()


def _stop_process(process: subprocess.Popen) -> bool:
    try:
        process.terminate()
        process.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
            process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            return False
    return process.poll() is not None


__all__ = ["OpenClawCommandResult", "SystemOpenClawCommandRunner"]
