"""Tests for kernel-derived external signer process/socket observation."""

from __future__ import annotations

import ast
import os
import stat
from dataclasses import replace
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_external_signer_os_observer import (
    FAIL_OS_OBSERVER_EXECUTABLE_MISMATCH,
    FAIL_OS_OBSERVER_EXECUTABLE_IDENTITY_MISMATCH,
    FAIL_OS_OBSERVER_POLICY_INVALID,
    FAIL_OS_OBSERVER_PROCESS_CHANGED,
    FAIL_OS_OBSERVER_PROCESS_IDENTITY_MISMATCH,
    FAIL_OS_OBSERVER_PROCESS_NOT_LIVE,
    FAIL_OS_OBSERVER_PROCESS_OWNER_MISMATCH,
    FAIL_OS_OBSERVER_PROCESS_SOCKET_NOT_OWNED,
    FAIL_OS_OBSERVER_PROCESS_UNAVAILABLE,
    FAIL_OS_OBSERVER_RECEIPT_INVALID,
    FAIL_OS_OBSERVER_REQUESTER_IDENTITY_MISMATCH,
    FAIL_OS_OBSERVER_SOCKET_MODE_MISMATCH,
    FAIL_OS_OBSERVER_SOCKET_CHANGED,
    FAIL_OS_OBSERVER_SOCKET_OWNER_MISMATCH,
    FAIL_OS_OBSERVER_SOCKET_TYPE_MISMATCH,
    FAIL_OS_OBSERVER_UNSUPPORTED_PLATFORM,
    ExternalSignerOsObservationError,
    ExternalSignerOsObservationPolicy,
    observe_external_signer_os_state,
    verify_external_signer_os_observation_receipt,
)


BOOT_ID = "11111111-2222-3333-4444-555555555555"
PID = 4242
START_TICKS = 987654
SIGNER_UID = 1201
SIGNER_GID = 1202
REQUESTER_UID = 1000
REQUESTER_GID = 1000
EXECUTABLE = "/usr/bin/python3.12"
SOCKET = "/run/foundups/reddog-signer.sock"


class FakeBackend:
    """Deterministic procfs/stat backend with mutation hooks."""

    def __init__(self) -> None:
        self.platform_name = "linux"
        self.state = "S"
        self.reported_pid = PID
        self.start_ticks = START_TICKS
        self.second_start_ticks = START_TICKS
        self.uid = SIGNER_UID
        self.gid = SIGNER_GID
        self.executable = EXECUTABLE
        self.executable_device = 8
        self.executable_inode = 101
        self.cmdline = b"python3.12\x00-m\x00reddog_signer\x00--config\x00hidden\x00"
        self.requester_uid = REQUESTER_UID
        self.requester_gid = REQUESTER_GID
        self.process_owns_socket = True
        self.socket_mode = stat.S_IFSOCK | 0o600
        self.socket_uid = SIGNER_UID
        self.socket_gid = SIGNER_GID
        self.stat_reads = 0
        self.socket_reads = 0
        self.second_socket_inode = 202

    def platform(self) -> str:
        return self.platform_name

    def read_bytes(self, path: str) -> bytes:
        if path == f"/proc/{PID}/stat":
            self.stat_reads += 1
            ticks = START_TICKS if self.stat_reads == 1 else self.second_start_ticks
            return _proc_stat(self.state, ticks, pid=self.reported_pid)
        if path == f"/proc/{PID}/status":
            return (
                f"Name:\tsigner\nUid:\t{self.uid}\t{self.uid}\t{self.uid}\t{self.uid}\n"
                f"Gid:\t{self.gid}\t{self.gid}\t{self.gid}\t{self.gid}\n"
            ).encode("ascii")
        if path == "/proc/sys/kernel/random/boot_id":
            return (BOOT_ID + "\n").encode("ascii")
        if path == f"/proc/{PID}/cmdline":
            return self.cmdline
        raise FileNotFoundError(path)

    def readlink(self, path: str) -> str:
        if path == f"/proc/{PID}/exe":
            return self.executable
        if path == f"/proc/{PID}/fd/7" and self.process_owns_socket:
            inode = 202 if self.socket_reads <= 1 else self.second_socket_inode
            return f"socket:[{inode}]"
        raise FileNotFoundError(path)

    def stat(self, path: str, *, follow_symlinks: bool) -> os.stat_result:
        if path == f"/proc/{PID}/exe" and follow_symlinks:
            return _stat_result(
                stat.S_IFREG | 0o755,
                SIGNER_UID,
                SIGNER_GID,
                self.executable_device,
                self.executable_inode,
            )
        if path == SOCKET and not follow_symlinks:
            self.socket_reads += 1
            inode = 202 if self.socket_reads == 1 else self.second_socket_inode
            return _stat_result(
                self.socket_mode, self.socket_uid, self.socket_gid, 9, inode
            )
        raise FileNotFoundError(path)

    def listdir(self, path: str) -> list[str]:
        if path == f"/proc/{PID}/fd":
            return ["7"]
        raise FileNotFoundError(path)

    def current_uid(self) -> int:
        return self.requester_uid

    def current_gid(self) -> int:
        return self.requester_gid


def _policy(**changes: object) -> ExternalSignerOsObservationPolicy:
    base = ExternalSignerOsObservationPolicy(
        pid=PID,
        expected_signer_uid=SIGNER_UID,
        expected_signer_gid=SIGNER_GID,
        requester_uid=REQUESTER_UID,
        requester_gid=REQUESTER_GID,
        expected_executable=EXECUTABLE,
        expected_executable_device=8,
        expected_executable_inode=101,
        socket_path=SOCKET,
        expected_socket_uid=SIGNER_UID,
        expected_socket_gid=SIGNER_GID,
        expected_socket_mode=0o600,
        expected_process_start_identity=f"{BOOT_ID}:{START_TICKS}",
    )
    return replace(base, **changes)


def _proc_stat(state: str, start_ticks: int, *, pid: int = PID) -> bytes:
    fields = [state] + ["0"] * 18 + [str(start_ticks)] + ["0"] * 4
    return f"{pid} (reddog signer) {' '.join(fields)}\n".encode("ascii")


def _stat_result(
    mode: int, uid: int, gid: int, device: int, inode: int
) -> os.stat_result:
    values = [mode, inode, device, 1, uid, gid, 0, 0, 0, 0]
    return os.stat_result(values)


def _assert_rejected(
    code: str,
    policy: ExternalSignerOsObservationPolicy,
    backend: FakeBackend,
) -> None:
    with pytest.raises(ExternalSignerOsObservationError, match=f"^{code}$"):
        observe_external_signer_os_state(
            policy, backend=backend, observed_at_epoch=1_800_000_000
        )


def test_valid_observation_is_kernel_derived_and_receipt_verifies() -> None:
    backend = FakeBackend()
    receipt = observe_external_signer_os_state(
        _policy(), backend=backend, observed_at_epoch=1_800_000_000
    )

    assert receipt.process_start_identity == f"{BOOT_ID}:{START_TICKS}"
    assert receipt.executable_path == EXECUTABLE
    assert receipt.executable_device == 8
    assert receipt.executable_inode == 101
    assert receipt.socket_mode == 0o600
    assert receipt.socket_device == 9
    assert receipt.socket_inode == 202
    assert receipt.socket_owned_by_process is True
    assert receipt.cmdline_digest.startswith("sha256:")
    assert receipt.cmdline_size_bytes == len(backend.cmdline)
    assert "hidden" not in repr(receipt)
    assert receipt.kernel_observed is True
    assert receipt.raw_cmdline_persisted is False
    assert receipt.authority_granted is False
    assert receipt.valve_unlocked is False
    verify_external_signer_os_observation_receipt(receipt)


def test_receipt_digest_is_deterministic_and_tampering_rejects() -> None:
    first = observe_external_signer_os_state(
        _policy(), backend=FakeBackend(), observed_at_epoch=1_800_000_000
    )
    second = observe_external_signer_os_state(
        _policy(), backend=FakeBackend(), observed_at_epoch=1_800_000_000
    )
    assert first.receipt_id == second.receipt_id

    altered = replace(first, socket_inode=999)
    with pytest.raises(
        ExternalSignerOsObservationError,
        match=f"^{FAIL_OS_OBSERVER_RECEIPT_INVALID}$",
    ):
        verify_external_signer_os_observation_receipt(altered)


@pytest.mark.parametrize("platform_name", ["win32", "darwin", "freebsd"])
def test_unsupported_platform_fails_closed(platform_name: str) -> None:
    backend = FakeBackend()
    backend.platform_name = platform_name
    _assert_rejected(FAIL_OS_OBSERVER_UNSUPPORTED_PLATFORM, _policy(), backend)


@pytest.mark.parametrize(
    "changes",
    [
        {"pid": 0},
        {"requester_uid": SIGNER_UID},
        {"requester_gid": SIGNER_GID},
        {"expected_executable": "python"},
        {"socket_path": "relative.sock"},
        {"expected_socket_mode": 0o1000},
        {"expected_process_start_identity": ""},
    ],
)
def test_invalid_or_non_distinct_policy_fails_closed(
    changes: dict[str, object],
) -> None:
    _assert_rejected(
        FAIL_OS_OBSERVER_POLICY_INVALID,
        _policy(**changes),
        FakeBackend(),
    )


def test_dead_process_fails_closed() -> None:
    backend = FakeBackend()
    backend.state = "Z"
    _assert_rejected(FAIL_OS_OBSERVER_PROCESS_NOT_LIVE, _policy(), backend)


def test_proc_reported_pid_mismatch_fails_closed() -> None:
    backend = FakeBackend()
    backend.reported_pid = PID + 1
    _assert_rejected(FAIL_OS_OBSERVER_PROCESS_UNAVAILABLE, _policy(), backend)


@pytest.mark.parametrize(
    ("field", "value"),
    [("uid", 999), ("gid", 999)],
)
def test_process_owner_mismatch_fails_closed(field: str, value: int) -> None:
    backend = FakeBackend()
    setattr(backend, field, value)
    _assert_rejected(FAIL_OS_OBSERVER_PROCESS_OWNER_MISMATCH, _policy(), backend)


def test_expected_start_identity_detects_pid_reuse() -> None:
    _assert_rejected(
        FAIL_OS_OBSERVER_PROCESS_IDENTITY_MISMATCH,
        _policy(expected_process_start_identity=f"{BOOT_ID}:123"),
        FakeBackend(),
    )


def test_process_change_during_observation_fails_closed() -> None:
    backend = FakeBackend()
    backend.second_start_ticks = START_TICKS + 1
    _assert_rejected(FAIL_OS_OBSERVER_PROCESS_CHANGED, _policy(), backend)


def test_executable_mismatch_fails_closed() -> None:
    backend = FakeBackend()
    backend.executable = "/usr/bin/python3.11"
    _assert_rejected(FAIL_OS_OBSERVER_EXECUTABLE_MISMATCH, _policy(), backend)


def test_executable_inode_substitution_fails_closed() -> None:
    backend = FakeBackend()
    backend.executable_inode = 102
    _assert_rejected(
        FAIL_OS_OBSERVER_EXECUTABLE_IDENTITY_MISMATCH, _policy(), backend
    )


def test_caller_cannot_forge_requester_kernel_identity() -> None:
    backend = FakeBackend()
    backend.requester_uid = REQUESTER_UID + 1
    _assert_rejected(
        FAIL_OS_OBSERVER_REQUESTER_IDENTITY_MISMATCH, _policy(), backend
    )


def test_process_must_own_the_observed_socket_inode() -> None:
    backend = FakeBackend()
    backend.process_owns_socket = False
    _assert_rejected(
        FAIL_OS_OBSERVER_PROCESS_SOCKET_NOT_OWNED, _policy(), backend
    )


def test_non_socket_path_fails_closed() -> None:
    backend = FakeBackend()
    backend.socket_mode = stat.S_IFREG | 0o600
    _assert_rejected(FAIL_OS_OBSERVER_SOCKET_TYPE_MISMATCH, _policy(), backend)


@pytest.mark.parametrize(
    ("field", "value"),
    [("socket_uid", 999), ("socket_gid", 999)],
)
def test_socket_owner_mismatch_fails_closed(field: str, value: int) -> None:
    backend = FakeBackend()
    setattr(backend, field, value)
    _assert_rejected(FAIL_OS_OBSERVER_SOCKET_OWNER_MISMATCH, _policy(), backend)


def test_socket_mode_mismatch_fails_closed() -> None:
    backend = FakeBackend()
    backend.socket_mode = stat.S_IFSOCK | 0o660
    _assert_rejected(FAIL_OS_OBSERVER_SOCKET_MODE_MISMATCH, _policy(), backend)


def test_socket_replacement_during_observation_fails_closed() -> None:
    backend = FakeBackend()
    backend.second_socket_inode = 203
    _assert_rejected(FAIL_OS_OBSERVER_SOCKET_CHANGED, _policy(), backend)


def test_module_has_no_execution_network_or_service_control_surface() -> None:
    source_path = (
        Path(__file__).parents[1]
        / "src"
        / "reddog_external_signer_os_observer.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert imports.isdisjoint(
        {"subprocess", "socket", "requests", "urllib", "httpx", "ctypes"}
    )
    assert calls.isdisjoint(
        {"system", "popen", "spawn", "fork", "execv", "execve", "kill", "connect"}
    )
