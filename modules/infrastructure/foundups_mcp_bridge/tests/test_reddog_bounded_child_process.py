"""Falsifiers for the shared bounded one-shot child runner."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_bounded_child_process import (
    BoundedChildCapture,
    CHILD_STDOUT_MAX_BYTES,
    _wait_for_child,
    _terminate_child_tree,
    bounded_child_runner,
)
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_bounded_child_process as runner_module,
    reddog_windows_job_object as job_module,
)


def test_runner_bounds_stdout_without_retaining_stderr(tmp_path: Path) -> None:
    completed = bounded_child_runner(
        [
            sys.executable,
            "-B",
            "-c",
            "import sys;sys.stdout.buffer.write(b'x'*"
            f"{CHILD_STDOUT_MAX_BYTES + 1})",
        ],
        cwd=str(tmp_path),
        env=os.environ.copy(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        shell=False,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.output_oversized is True
    assert len(completed.stdout) == CHILD_STDOUT_MAX_BYTES


def test_runner_terminates_live_child_after_stdout_overflow(tmp_path: Path) -> None:
    started = time.monotonic()
    completed = bounded_child_runner(
        [
            sys.executable, "-B", "-c",
            "import sys,time;sys.stdout.buffer.write(b'x'*"
            f"{CHILD_STDOUT_MAX_BYTES + 1});sys.stdout.flush();time.sleep(15)",
        ],
        cwd=str(tmp_path), env=os.environ.copy(),
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, shell=False, timeout=10, check=False,
    )

    assert completed.output_oversized is True
    assert time.monotonic() - started < 3


def test_overflow_never_enters_unbounded_wait(monkeypatch) -> None:
    class UnstoppableProcess:
        args = ("child",)

        @staticmethod
        def poll():
            return None

    process = UnstoppableProcess()
    capture = BoundedChildCapture(oversized=True)
    monkeypatch.setattr(
        "modules.infrastructure.foundups_mcp_bridge.src."
        "reddog_bounded_child_process._terminate_child_tree",
        lambda _process: None,
    )

    with pytest.raises(subprocess.TimeoutExpired):
        _wait_for_child(process, capture, 1)


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-handle cleanup")
def test_windows_cleanup_never_resolves_ambient_taskkill(monkeypatch) -> None:
    events: list[str] = []

    class Guard:
        def close(self) -> None:
            events.append("guard")

    class Process:
        pid = 17
        args = ("child",)
        _reddog_tree_guard = Guard()
        returncode = None

        def poll(self):
            return self.returncode

        def kill(self) -> None:
            events.append("kill")
            self.returncode = -9

        def wait(self, timeout):
            events.append("wait")
            return self.returncode

    monkeypatch.setattr(
        subprocess, "run",
        lambda *_args, **_kwargs: events.append("ambient-taskkill"),
    )

    _terminate_child_tree(Process())

    assert events == ["guard", "kill", "wait"]


def test_reader_start_failure_terminates_resumed_child(monkeypatch) -> None:
    events: list[str] = []

    class Guard:
        def close(self) -> None:
            events.append("guard")

    class Stream:
        def close(self) -> None:
            events.append("stream")

    class Process:
        args = ("child",)
        pid = 23
        stdout = Stream()
        _reddog_tree_guard = Guard()
        returncode = None

        def poll(self):
            return self.returncode

        def kill(self) -> None:
            events.append("kill")
            self.returncode = -9

        def wait(self, timeout):
            events.append("wait")
            return self.returncode

    class FailingThread:
        def __init__(self, **_kwargs) -> None:
            pass

        def start(self) -> None:
            raise RuntimeError("reader start failed")

    process = Process()
    monkeypatch.setattr(
        runner_module, "_start_bounded_child",
        lambda _command, _kwargs: (process, 1.0, "reader"),
    )
    monkeypatch.setattr(runner_module.threading, "Thread", FailingThread)

    with pytest.raises(RuntimeError, match="reader start failed"):
        bounded_child_runner(["child"])

    assert events == ["guard", "kill", "wait", "stream"]


def test_job_close_terminates_before_releasing_handle() -> None:
    events: list[tuple[str, int]] = []
    job = job_module.WindowsKillOnCloseJob(
        73,
        lambda handle: events.append(("close", int(handle))) or True,
        lambda handle, code: events.append(("terminate", int(handle))) or True,
    )

    job.close()

    assert events == [("terminate", 73), ("close", 73)]


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object error contract")
@pytest.mark.parametrize(
    ("terminate_ok", "close_ok", "retained_handle"),
    ((False, True, 0), (True, False, 73)),
)
def test_job_terminate_or_close_failure_surfaces_without_losing_ownership(
    terminate_ok: bool, close_ok: bool, retained_handle: int,
) -> None:
    job = job_module.WindowsKillOnCloseJob(
        73, lambda _handle: close_ok,
        lambda _handle, _code: terminate_ok,
    )

    with pytest.raises(OSError):
        job.close()

    assert job._handle == retained_handle


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object attach contract")
@pytest.mark.parametrize("failure", ("setup", "assign", "enumerate", "resume"))
def test_windows_job_attach_failures_close_before_escape(
    monkeypatch, failure: str,
) -> None:
    events: list[str] = []

    class Guard:
        _handle = 91

        def close(self) -> None:
            events.append("close")

    class Library:
        def AssignProcessToJobObject(self, _job, _process):
            events.append("assign")
            return failure != "assign"

    guard = Guard()
    monkeypatch.setattr(job_module, "_kernel32", lambda: Library())
    monkeypatch.setattr(
        job_module, "_configured_job",
        lambda _library: (
            (_ for _ in ()).throw(OSError("setup failed"))
            if failure == "setup" else guard
        ),
    )
    monkeypatch.setattr(
        job_module, "_only_suspended_thread",
        lambda _library, _pid: (
            (_ for _ in ()).throw(OSError("enumeration failed"))
            if failure == "enumerate" else 13
        ),
    )
    monkeypatch.setattr(
        job_module, "_resume_only_thread",
        lambda _library, _thread: (
            (_ for _ in ()).throw(OSError("resume failed"))
            if failure == "resume" else events.append("resume")
        ),
    )

    with pytest.raises(OSError):
        job_module.attach_windows_kill_on_close_job(
            SimpleNamespace(_handle=81, pid=7)
        )

    expected = [] if failure == "setup" else ["assign", "close"]
    assert events == expected


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object containment")
def test_parent_exit_cannot_leave_stdout_descendant_running(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "escaped-descendant.txt"
    descendant = (
        "from pathlib import Path;import time;time.sleep(2);"
        f"Path({str(marker)!r}).write_text('escaped',encoding='ascii')"
    )
    parent = (
        "import subprocess,sys;"
        "child=subprocess.Popen([sys.executable,'-B','-c',"
        f"{descendant!r}],stdin=subprocess.DEVNULL,stdout=sys.stdout,"
        "stderr=subprocess.DEVNULL,close_fds=True);"
        "print(child.pid,flush=True)"
    )

    completed = bounded_child_runner(
        [sys.executable, "-B", "-c", parent],
        cwd=str(tmp_path), env=os.environ.copy(),
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, shell=False, timeout=10, check=False,
    )

    assert completed.returncode == 0
    assert completed.output_read_failed is True
    time.sleep(2.5)
    assert not marker.exists()


@pytest.mark.parametrize(
    "override",
    (
        {"stdin": None},
        {"stdout": subprocess.DEVNULL},
        {"stderr": subprocess.PIPE},
        {"shell": True},
    ),
)
def test_runner_rejects_unbounded_or_shell_process_shape(
    tmp_path: Path, override: dict[str, object],
) -> None:
    kwargs = {
        "cwd": str(tmp_path),
        "env": os.environ.copy(),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.DEVNULL,
        "shell": False,
        "timeout": 10,
        "check": False,
    }
    kwargs.update(override)
    with pytest.raises(ValueError, match="bounded child process shape invalid"):
        bounded_child_runner([sys.executable, "-B", "-c", "pass"], **kwargs)


@pytest.mark.parametrize("timeout", (0, -1, float("inf"), float("nan"), True))
def test_runner_rejects_invalid_timeout(tmp_path: Path, timeout: object) -> None:
    with pytest.raises(ValueError, match="bounded child timeout invalid"):
        bounded_child_runner(
            [sys.executable, "-B", "-c", "pass"],
            cwd=str(tmp_path),
            env=os.environ.copy(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False,
            timeout=timeout,
            check=False,
        )
