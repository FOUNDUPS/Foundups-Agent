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

    assert completed.output_read_failed is False
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

# Optional aggregate Job memory contract. These cases are frozen before source changes.
_MEMORY_LIMIT = 128 * 1024 * 1024


def _memory_api():
    validate = getattr(job_module, "validate_job_memory_limit", None)
    assert callable(validate), "job_memory_api_missing"
    return validate


def _memory_windows(monkeypatch):
    monkeypatch.setattr(job_module, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(runner_module, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200, raising=False)
    monkeypatch.setattr(job_module.ctypes, "get_last_error", lambda: 5, raising=False)
    monkeypatch.setattr(job_module.ctypes, "WinError", lambda _code: OSError("win32 failure"), raising=False)


def _memory_value(value):
    maximum = (1 << (8 * job_module.ctypes.sizeof(job_module.ctypes.c_size_t))) - 1
    return maximum if value == "maximum" else maximum + 1 if value == "overflow" else value


def _memory_kwargs():
    return dict(stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, shell=False, timeout=1)


class _MemoryLibrary:
    def __init__(self, configure_ok=True, assign_ok=True):
        self.events, self.limits = [], None
        self.configure_ok, self.assign_ok = configure_ok, assign_ok

    def CreateJobObjectW(self, *_args):
        self.events.append("create")
        return 91

    def SetInformationJobObject(self, handle, kind, pointer, size):
        self.events.append("configure")
        assert handle == 91 and kind == 9
        assert size == job_module.ctypes.sizeof(job_module._ExtendedLimitInformation)
        self.limits = job_module.ctypes.cast(
            pointer, job_module.ctypes.POINTER(job_module._ExtendedLimitInformation)
        ).contents
        self.observed = (self.limits.basic_limit_information.limit_flags,
                         self.limits.job_memory_limit, self.limits.process_memory_limit)
        return self.configure_ok

    def AssignProcessToJobObject(self, _job, _process):
        self.events.append("assign")
        return self.assign_ok

    def TerminateJobObject(self, _handle, _code):
        self.events.append("terminate")
        return True

    def CloseHandle(self, _handle):
        self.events.append("close")
        return True


@pytest.mark.parametrize("value", (None, 1, "maximum"), ids=("none", "one", "size-t-max"))
def test_job_memory_valid_values(monkeypatch, value):
    validate = _memory_api()
    _memory_windows(monkeypatch)
    value = _memory_value(value)
    assert validate(value) == value


@pytest.mark.parametrize("value", (True, False, 0, -1, 1.0, "128", "overflow"),
                         ids=("true", "false", "zero", "negative", "float", "string", "overflow"))
def test_job_memory_invalid_values(monkeypatch, value):
    validate = _memory_api()
    _memory_windows(monkeypatch)
    with pytest.raises(ValueError):
        validate(_memory_value(value))


@pytest.mark.parametrize("entry", ("runner", "configured"))
@pytest.mark.parametrize("value", (True, 0, "overflow"), ids=("bool", "zero", "overflow"))
def test_job_memory_invalid_before_effect(monkeypatch, entry, value):
    _memory_api()
    _memory_windows(monkeypatch)
    calls = []

    def unexpected(*_args, **_kwargs):
        calls.append("effect")
        raise AssertionError("unexpected effect")

    monkeypatch.setattr(runner_module.subprocess, "Popen", unexpected)
    library = SimpleNamespace(CreateJobObjectW=unexpected)
    with pytest.raises(ValueError):
        if entry == "runner":
            bounded_child_runner(["never"], job_memory_limit_bytes=_memory_value(value), **_memory_kwargs())
        else:
            job_module._configured_job(library, job_memory_limit_bytes=_memory_value(value))
    assert calls == []


@pytest.mark.parametrize("entry", ("runner", "attach", "configured"))
def test_job_memory_non_windows_rejects_before_effect(monkeypatch, entry):
    _memory_api()
    monkeypatch.setattr(job_module, "os", SimpleNamespace(name="posix"))
    monkeypatch.setattr(runner_module, "os", SimpleNamespace(name="posix"))
    calls = []

    def unexpected(*_args, **_kwargs):
        calls.append("effect")
        raise AssertionError("unexpected effect")

    monkeypatch.setattr(runner_module.subprocess, "Popen", unexpected)
    monkeypatch.setattr(job_module, "_kernel32", unexpected)
    with pytest.raises(ValueError):
        if entry == "runner":
            bounded_child_runner(["never"], job_memory_limit_bytes=1, **_memory_kwargs())
        elif entry == "attach":
            job_module.attach_windows_kill_on_close_job(SimpleNamespace(_handle=81), job_memory_limit_bytes=1)
        else:
            job_module._configured_job(SimpleNamespace(CreateJobObjectW=unexpected), job_memory_limit_bytes=1)
    assert calls == []


def test_job_memory_non_windows_none_preserves_default(monkeypatch):
    validate = _memory_api()
    monkeypatch.setattr(job_module, "os", SimpleNamespace(name="posix"))
    assert validate(None) is None
    assert job_module.attach_windows_kill_on_close_job(SimpleNamespace()) is None


@pytest.mark.parametrize("limit", (None, _MEMORY_LIMIT), ids=("default", "bounded"))
def test_job_memory_configures_only_aggregate_limit(monkeypatch, limit):
    _memory_api()
    _memory_windows(monkeypatch)
    library = _MemoryLibrary()
    job = job_module._configured_job(library, job_memory_limit_bytes=limit)
    assert library.observed == (0x2000 | (0x200 if limit is not None else 0), limit or 0, 0)
    job.close()
    assert library.events == ["create", "configure", "terminate", "close"]


def test_job_memory_configuration_failure_attempts_handle_cleanup(monkeypatch):
    _memory_api()
    _memory_windows(monkeypatch)
    library = _MemoryLibrary(configure_ok=False)
    monkeypatch.setattr(job_module, "_kernel32", lambda: library)
    monkeypatch.setattr(job_module, "_only_suspended_thread", lambda *_args: 13)
    monkeypatch.setattr(job_module, "_resume_only_thread", lambda *_args: library.events.append("resume"))
    process = SimpleNamespace(
        _handle=81, pid=7, stdout=object(), poll=lambda: None,
        kill=lambda: library.events.append("kill"),
        wait=lambda **_kwargs: library.events.append("wait"),
    )
    monkeypatch.setattr(runner_module.subprocess, "Popen", lambda *_args, **_kwargs: process)
    with pytest.raises(OSError):
        runner_module._start_bounded_child(
            ["inert"], _memory_kwargs(), job_memory_limit_bytes=_MEMORY_LIMIT,
        )
    # This observes the existing cleanup attempt, not every CloseHandle failure mode.
    assert library.events == ["create", "configure", "close", "kill", "wait"]


@pytest.mark.parametrize("assign_ok", (True, False), ids=("success", "assignment-failure"))
def test_job_memory_configuration_precedes_assignment_and_resume(monkeypatch, assign_ok):
    _memory_api()
    _memory_windows(monkeypatch)
    library = _MemoryLibrary(assign_ok=assign_ok)
    monkeypatch.setattr(job_module, "_kernel32", lambda: library)
    monkeypatch.setattr(job_module, "_only_suspended_thread", lambda *_args: 13)
    monkeypatch.setattr(job_module, "_resume_only_thread", lambda *_args: library.events.append("resume"))
    process = SimpleNamespace(_handle=81, pid=7)
    if assign_ok:
        job = job_module.attach_windows_kill_on_close_job(process, job_memory_limit_bytes=_MEMORY_LIMIT)
        assert library.events == ["create", "configure", "assign", "resume"]
        job.close()
    else:
        with pytest.raises(OSError):
            job_module.attach_windows_kill_on_close_job(process, job_memory_limit_bytes=_MEMORY_LIMIT)
        assert library.events == ["create", "configure", "assign", "terminate", "close"]
    assert library.observed == (0x2200, _MEMORY_LIMIT, 0)


@pytest.mark.parametrize("limit", (None, _MEMORY_LIMIT), ids=("default", "bounded"))
def test_job_memory_start_forwards_without_popen_keyword(monkeypatch, limit):
    _memory_api()
    _memory_windows(monkeypatch)
    observed = []
    process = SimpleNamespace(stdout=object())
    guard = object()

    def popen(command, **kwargs):
        observed.append(("popen", command, kwargs))
        return process

    def attach(*args, **kwargs):
        observed.append(("attach", args, kwargs))
        return guard

    monkeypatch.setattr(runner_module.subprocess, "Popen", popen)
    monkeypatch.setattr(runner_module, "attach_windows_kill_on_close_job", attach)
    result, timeout, _name = runner_module._start_bounded_child(["inert"], _memory_kwargs(), job_memory_limit_bytes=limit)
    assert result is process and timeout == 1 and process._reddog_tree_guard is guard
    assert "job_memory_limit_bytes" not in observed[0][2]
    assert observed[0][2]["creationflags"] & 0x4
    assert observed[1] == ("attach", (process,), {} if limit is None else {"job_memory_limit_bytes": limit})


@pytest.mark.parametrize("limit", (None, _MEMORY_LIMIT), ids=("default", "bounded"))
def test_job_memory_public_runner_preserves_default_call_shape(monkeypatch, limit):
    _memory_api()
    _memory_windows(monkeypatch)
    calls = []
    process = SimpleNamespace()
    reader = SimpleNamespace(join=lambda **_kw: None, is_alive=lambda: False)

    def start(*args, **kwargs):
        calls.append((args, kwargs))
        return process, 1.0, "inert"

    monkeypatch.setattr(runner_module, "_start_bounded_child", start)
    monkeypatch.setattr(runner_module, "_start_capture_reader", lambda *_args: reader)
    monkeypatch.setattr(runner_module, "_wait_for_child", lambda *_args: 0)
    monkeypatch.setattr(runner_module, "_close_child_tree_guard", lambda p: calls.append(p))
    result = bounded_child_runner(["inert"], job_memory_limit_bytes=limit, **_memory_kwargs())
    assert result.returncode == 0 and result.stdout == b""
    assert calls[0][1] == ({} if limit is None else {"job_memory_limit_bytes": limit})
    assert "job_memory_limit_bytes" not in calls[0][0][1]
    assert calls[1] is process


# Real Windows controls: selected separately, never in the missing-API baseline.
_MEMORY_CHILD_SOURCE = r'''
import json, sys
stage='imports'
def report_failure(kind, _value, trace):
    while trace.tb_next:
        trace=trace.tb_next
    info=globals().get('info')
    print(json.dumps({'error_type':kind.__name__,'line':trace.tb_lineno,'stage':stage,
        'flags':None if info is None else info.basic.flags,
        'job_memory':None if info is None else info.job_memory,
        'process_memory':None if info is None else info.process_memory}),flush=True)
sys.excepthook=report_failure
import ctypes
from ctypes import wintypes
class Basic(ctypes.Structure):
    _fields_=[('process_time',ctypes.c_longlong),('job_time',ctypes.c_longlong),
              ('flags',wintypes.DWORD),('min_ws',ctypes.c_size_t),('max_ws',ctypes.c_size_t),
              ('active',wintypes.DWORD),('affinity',ctypes.c_size_t),
              ('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
class Extended(ctypes.Structure):
    _fields_=[('basic',Basic),('io',ctypes.c_ulonglong*6),('process_memory',ctypes.c_size_t),
              ('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.QueryInformationJobObject.argtypes=(wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p)
k.QueryInformationJobObject.restype=wintypes.BOOL
k.VirtualAlloc.argtypes=(ctypes.c_void_p,ctypes.c_size_t,wintypes.DWORD,wintypes.DWORD)
k.VirtualAlloc.restype=ctypes.c_void_p
k.VirtualFree.argtypes=(ctypes.c_void_p,ctypes.c_size_t,wintypes.DWORD)
k.VirtualFree.restype=wintypes.BOOL
requested,limit=map(int,sys.argv[1:])
assert limit==128*1024*1024 and requested in (1024*1024,256*1024*1024)
info=Extended()
stage='query'
assert k.QueryInformationJobObject(None,9,ctypes.byref(info),ctypes.sizeof(info),None)
assert info.basic.flags & 0x2200 == 0x2200 and info.job_memory==limit and info.process_memory==0
# Query precedes commit: absent/wrong configured limit never attempts the large allocation.
ctypes.set_last_error(0)
stage='allocate'
ptr=k.VirtualAlloc(None,requested,0x3000,0x04)
error=ctypes.get_last_error()
freed=False
try:
    if requested < limit:
        assert ptr
        ctypes.memset(ptr,0,requested)
    else:
        assert not ptr and error!=0
finally:
    stage='free'
    if ptr:
        freed=bool(k.VirtualFree(ptr,0,0x8000))
        assert freed
print(json.dumps({'requested':requested,'limit':info.job_memory,'flags':info.basic.flags,
                  'allocated':bool(ptr),'error':error,'freed':freed}))
'''


@pytest.mark.parametrize("requested", (1024 * 1024, 256 * 1024 * 1024), ids=("small", "overlimit"))
@pytest.mark.skipif(os.name != "nt", reason="Actual Windows aggregate Job memory control")
def test_job_memory_real_windows_commit(tmp_path: Path, requested: int):
    _memory_api()
    import json
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_process_image import (
        current_process_image_path,
    )
    environment = {k: os.environ[k] for k in ("SystemRoot", "WINDIR") if k in os.environ}
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = bounded_child_runner(
        [str(current_process_image_path()), "-I", "-S", "-B", "-c", _MEMORY_CHILD_SOURCE, str(requested), str(_MEMORY_LIMIT)],
        job_memory_limit_bytes=_MEMORY_LIMIT, cwd=str(tmp_path), env=environment,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        shell=False, timeout=10,
    )
    assert result.returncode == 0 and not result.output_oversized and not result.output_read_failed, (
        result.returncode, result.output_oversized, result.output_read_failed, result.stdout[:2048],
    )
    report = json.loads(result.stdout)
    assert report["requested"] == requested and report["limit"] == _MEMORY_LIMIT
    assert report["flags"] & 0x2200 == 0x2200
    assert report["allocated"] is (requested < _MEMORY_LIMIT)
    assert report["freed"] is (requested < _MEMORY_LIMIT)
