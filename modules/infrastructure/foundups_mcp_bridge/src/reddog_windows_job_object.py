"""Windows kill-on-close Job Object guard for one bounded child tree."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os


JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
CREATE_SUSPENDED = 0x00000004
TH32CS_SNAPTHREAD = 0x00000004
THREAD_SUSPEND_RESUME = 0x0002
_DWORD_FAILURE = 0xFFFFFFFF
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("read_operation_count", ctypes.c_ulonglong),
        ("write_operation_count", ctypes.c_ulonglong),
        ("other_operation_count", ctypes.c_ulonglong),
        ("read_transfer_count", ctypes.c_ulonglong),
        ("write_transfer_count", ctypes.c_ulonglong),
        ("other_transfer_count", ctypes.c_ulonglong),
    ]


class _BasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("per_process_user_time_limit", ctypes.c_longlong),
        ("per_job_user_time_limit", ctypes.c_longlong),
        ("limit_flags", wintypes.DWORD),
        ("minimum_working_set_size", ctypes.c_size_t),
        ("maximum_working_set_size", ctypes.c_size_t),
        ("active_process_limit", wintypes.DWORD),
        ("affinity", ctypes.c_size_t),
        ("priority_class", wintypes.DWORD),
        ("scheduling_class", wintypes.DWORD),
    ]


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("basic_limit_information", _BasicLimitInformation),
        ("io_info", _IoCounters),
        ("process_memory_limit", ctypes.c_size_t),
        ("job_memory_limit", ctypes.c_size_t),
        ("peak_process_memory_used", ctypes.c_size_t),
        ("peak_job_memory_used", ctypes.c_size_t),
    ]


class _ThreadEntry(ctypes.Structure):
    _fields_ = [
        ("size", wintypes.DWORD),
        ("usage_count", wintypes.DWORD),
        ("thread_id", wintypes.DWORD),
        ("owner_process_id", wintypes.DWORD),
        ("base_priority", wintypes.LONG),
        ("priority_delta", wintypes.LONG),
        ("flags", wintypes.DWORD),
    ]


def _kernel32():
    library = ctypes.WinDLL("kernel32", use_last_error=True)
    library.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    library.CreateJobObjectW.restype = wintypes.HANDLE
    library.SetInformationJobObject.argtypes = (
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    )
    library.SetInformationJobObject.restype = wintypes.BOOL
    library.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    library.AssignProcessToJobObject.restype = wintypes.BOOL
    library.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    library.TerminateJobObject.restype = wintypes.BOOL
    library.CloseHandle.argtypes = (wintypes.HANDLE,)
    library.CloseHandle.restype = wintypes.BOOL
    library.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    library.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    library.Thread32First.argtypes = (
        wintypes.HANDLE, ctypes.POINTER(_ThreadEntry),
    )
    library.Thread32First.restype = wintypes.BOOL
    library.Thread32Next.argtypes = (
        wintypes.HANDLE, ctypes.POINTER(_ThreadEntry),
    )
    library.Thread32Next.restype = wintypes.BOOL
    library.OpenThread.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    library.OpenThread.restype = wintypes.HANDLE
    library.ResumeThread.argtypes = (wintypes.HANDLE,)
    library.ResumeThread.restype = wintypes.DWORD
    return library


class WindowsKillOnCloseJob:
    """Terminate one child Job explicitly, then release its final handle."""

    def __init__(self, handle: int, close_handle, terminate_job) -> None:
        self._handle = int(handle)
        self._close_handle = close_handle
        self._terminate_job = terminate_job

    def close(self) -> None:
        handle = self._handle
        if not handle:
            return
        terminated = bool(self._terminate_job(handle, 1))
        terminate_error = 0 if terminated else ctypes.get_last_error()
        closed = bool(self._close_handle(handle))
        close_error = 0 if closed else ctypes.get_last_error()
        if closed:
            self._handle = 0
        error = terminate_error or close_error
        if error or not terminated or not closed:
            raise ctypes.WinError(error)


def _configured_job(library) -> WindowsKillOnCloseJob:
    handle = library.CreateJobObjectW(None, None)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    limits = _ExtendedLimitInformation()
    limits.basic_limit_information.limit_flags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not library.SetInformationJobObject(
        handle, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
        ctypes.byref(limits), ctypes.sizeof(limits),
    ):
        error = ctypes.get_last_error()
        library.CloseHandle(handle)
        raise ctypes.WinError(error)
    return WindowsKillOnCloseJob(
        int(handle), library.CloseHandle, library.TerminateJobObject,
    )


def _only_suspended_thread(library, process_id: int) -> int:
    snapshot = library.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    if int(snapshot or 0) == _INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    owned: list[int] = []
    try:
        entry = _ThreadEntry()
        entry.size = ctypes.sizeof(entry)
        present = library.Thread32First(snapshot, ctypes.byref(entry))
        while present:
            if int(entry.owner_process_id) == process_id:
                owned.append(int(entry.thread_id))
            entry.size = ctypes.sizeof(entry)
            present = library.Thread32Next(snapshot, ctypes.byref(entry))
    finally:
        library.CloseHandle(snapshot)
    if len(owned) != 1:
        raise OSError("bounded child suspended thread is not unique")
    return owned[0]


def _resume_only_thread(library, thread_id: int) -> None:
    thread = library.OpenThread(THREAD_SUSPEND_RESUME, False, thread_id)
    if not thread:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        previous = int(library.ResumeThread(thread))
    finally:
        library.CloseHandle(thread)
    if previous != 1:
        raise OSError("bounded child suspended thread state invalid")


def attach_windows_kill_on_close_job(process) -> WindowsKillOnCloseJob | None:
    """Attach a suspended Windows child to a kill-on-close job, then resume."""

    if os.name != "nt":
        return None
    process_handle = int(getattr(process, "_handle", 0) or 0)
    if process_handle <= 0:
        raise OSError("bounded child process handle unavailable")
    library = _kernel32()
    job = _configured_job(library)
    try:
        if not library.AssignProcessToJobObject(
            wintypes.HANDLE(job._handle), wintypes.HANDLE(process_handle),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        thread_id = _only_suspended_thread(library, int(process.pid))
        _resume_only_thread(library, thread_id)
    except (OSError, ValueError):
        job.close()
        raise
    return job


__all__ = [
    "attach_windows_kill_on_close_job", "CREATE_SUSPENDED",
    "WindowsKillOnCloseJob",
]
