"""Bounded subprocess byte pump for WRE Git reads."""

from __future__ import annotations

from pathlib import Path
import subprocess
import threading
from typing import Mapping, Sequence


_CHUNK_BYTES = 64 * 1024
_MAX_STDIN_BYTES = 8 * 1024 * 1024


def run_bounded_process(
    argv: Sequence[str], *, cwd: Path, max_bytes: int, timeout_s: int,
    chunks: list[bytes] | None, output_path: Path | None,
    environment: Mapping[str, str] | None, stdin_bytes: bytes | None,
) -> None:
    """Pump one process with bounded stdout and optional bounded stdin."""
    if (
        max_bytes < 1 or timeout_s < 1 or bool(chunks is None) != bool(output_path)
        or (stdin_bytes is not None and (
            type(stdin_bytes) is not bytes or len(stdin_bytes) > _MAX_STDIN_BYTES
        ))
    ):
        raise ValueError("bounded_git_output_configuration_invalid")
    process = subprocess.Popen(
        list(argv), cwd=cwd,
        stdin=subprocess.PIPE if stdin_bytes is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        shell=False, env=None if environment is None else dict(environment),
    )
    state: dict[str, BaseException | bool] = {"exceeded": False}
    reader = threading.Thread(
        target=_copy_stdout,
        args=(process, max_bytes, chunks, output_path, state),
        daemon=True, name="wre-git-stdout",
    )
    writer = _stdin_writer(process, stdin_bytes, state)
    reader.start()
    if writer is not None:
        writer.start()
    try:
        returncode = process.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        _terminate_threads(process, (reader, writer))
        raise
    for thread in (reader, writer):
        if thread is not None:
            thread.join(timeout=5)
    if reader.is_alive() or (writer is not None and writer.is_alive()):
        _terminate_threads(process, (reader, writer))
        raise RuntimeError("bounded_git_output_reader_stalled")
    _close_process_pipes(process)
    error = state.get("error")
    if isinstance(error, BaseException):
        raise error
    if state["exceeded"] is True:
        raise ValueError("bounded_git_output_exceeded")
    if returncode != 0:
        raise subprocess.CalledProcessError(returncode, list(argv))


def _stdin_writer(
    process: subprocess.Popen[bytes], payload: bytes | None,
    state: dict[str, BaseException | bool],
) -> threading.Thread | None:
    if payload is None:
        return None
    return threading.Thread(
        target=_copy_stdin, args=(process, payload, state),
        daemon=True, name="wre-git-stdin",
    )


def _copy_stdin(
    process: subprocess.Popen[bytes], payload: bytes,
    state: dict[str, BaseException | bool],
) -> None:
    try:
        assert process.stdin is not None
        process.stdin.write(payload)
    except BrokenPipeError:
        pass
    except BaseException as exc:
        state["error"] = exc
        process.kill()
    finally:
        if process.stdin is not None:
            process.stdin.close()


def _terminate_threads(
    process: subprocess.Popen[bytes],
    threads: Sequence[threading.Thread | None],
) -> None:
    if process.poll() is None:
        process.kill()
    process.wait(timeout=30)
    _close_process_pipes(process)
    for thread in threads:
        if thread is not None:
            thread.join(timeout=5)
            if thread.is_alive():
                raise RuntimeError("bounded_git_output_reader_stalled")


def _close_process_pipes(process: subprocess.Popen[bytes]) -> None:
    for pipe in (process.stdin, process.stdout):
        if pipe is not None and not pipe.closed:
            pipe.close()


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


__all__ = ["run_bounded_process"]
