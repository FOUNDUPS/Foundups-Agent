"""Tests for kernel-derived external signer process/socket observation."""

from __future__ import annotations

import ast
import errno
import json
import os
import socket
import stat
import struct
import sys
import tempfile
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
    _require_process_socket_owner,
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


# Characterization only: Linux v6.12 unix_diag.h, diag.c and kdev_t.h.
# These helpers are not a production observer or a general netlink client.
_DIAG_NO_COOKIE = (0xFFFFFFFF, 0xFFFFFFFF)


def _require_hosted_kernel_characterization() -> Path:
    if os.environ.get("FOUNDUPS_SOCKET_KERNEL_CHARACTERIZATION") != "1":
        pytest.skip("Explicitly reviewed hosted kernel characterization required")
    assert sys.platform == "linux", "Incomplete qualification: Linux required"
    assert hasattr(socket, "AF_NETLINK"), "Incomplete qualification: netlink absent"
    root = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    assert root.is_dir()
    return root


def _kernel_diag_exchange(body: bytes) -> tuple[int, bytes, bytes]:
    sequence = 0x52534931
    request = struct.pack("=IHHII", 16 + len(body), 20, 1, sequence, 0) + body
    # NETLINK_SOCK_DIAG=4; exactly one request for our held socket inode, no dump.
    with socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, 4) as channel:
        channel.settimeout(2.0)
        channel.bind((0, 0))
        port = channel.getsockname()[0]
        assert channel.sendto(request, (0, 0)) == len(request)
        raw, ancillary, flags, sender = channel.recvmsg(4096)
    assert sender == (0, 0) and not ancillary and flags == 0
    assert len(raw) >= 16
    size, kind, reply_flags, reply_sequence, reply_port = struct.unpack_from(
        "=IHHII", raw
    )
    assert size == len(raw) and size % 4 == 0 and reply_flags == 0
    assert reply_sequence == sequence and reply_port == port
    assert kind in (2, 20)  # NLMSG_ERROR or SOCK_DIAG_BY_FAMILY, never multipart.
    return kind, raw[16:], request


def _parse_own_socket_vfs(
    payload: bytes, inode: int, cookie: tuple[int, int]
) -> dict[str, object]:
    assert len(payload) >= 16
    family, kind, state, pad, reply_inode, c0, c1 = struct.unpack_from(
        "=BBBBIII", payload
    )
    assert (family, kind, state, pad) == (socket.AF_UNIX, socket.SOCK_STREAM, 10, 0)
    assert reply_inode == inode and (c0, c1) != _DIAG_NO_COOKIE
    assert cookie == _DIAG_NO_COOKIE or cookie == (c0, c1)
    attributes = {}
    offset = 16
    while offset < len(payload):
        assert offset + 4 <= len(payload)
        length, attr_type = struct.unpack_from("=HH", payload, offset)
        end = offset + length
        aligned_end = offset + ((length + 3) & ~3)
        assert length >= 4 and end <= aligned_end <= len(payload)
        assert attr_type not in attributes
        attributes[attr_type] = payload[offset + 4:end]
        offset = aligned_end
    assert offset == len(payload) and 1 in attributes
    assert len(attributes[1]) == 8  # UNIX_DIAG_VFS=1; request SHOW_VFS bit is2.
    vfs_inode, vfs_device = struct.unpack("=II", attributes[1])
    return {"socket_inode": inode, "cookie": (c0, c1),
            "vfs_inode": vfs_inode, "vfs_device": vfs_device}


def _query_held_socket(
    held: socket.socket, cookie: tuple[int, int] = _DIAG_NO_COOKIE,
    *, expected_error: int | None = None,
) -> dict[str, object]:
    inode = os.fstat(held.fileno()).st_ino
    assert 0 < inode <= 0xFFFFFFFF, "Incomplete qualification: socket inode width"
    body = struct.pack("=BBHIIIII", socket.AF_UNIX, 0, 0, 0, inode, 2, *cookie)
    kind, payload, request = _kernel_diag_exchange(body)
    if expected_error is not None:
        assert kind == 2 and len(payload) == 4 + len(request)
        error = struct.unpack_from("=i", payload)[0]
        assert error == -expected_error and payload[4:] == request
        return {"error": error}
    assert kind == 20, "Incomplete qualification: diagnostic request rejected"
    return _parse_own_socket_vfs(payload, inode, cookie)


def _assert_vfs_association(
    observation: dict[str, object], metadata: os.stat_result, held: socket.socket
) -> None:
    assert stat.S_ISSOCK(metadata.st_mode)
    assert 0 < metadata.st_ino <= 0xFFFFFFFF, "Incomplete qualification: VFS inode width"
    assert observation["socket_inode"] == os.fstat(held.fileno()).st_ino
    assert observation["vfs_inode"] == metadata.st_ino
    # Kernel dev_t is major:12/minor:20, unlike userspace st_dev encoding.
    raw_device = observation["vfs_device"]
    assert (raw_device >> 20, raw_device & 0xFFFFF) == (
        os.major(metadata.st_dev), os.minor(metadata.st_dev)
    )


def _legacy_held_fd_result(held: socket.socket, metadata: os.stat_result) -> str:
    root = f"/proc/{os.getpid()}/fd"
    descriptor = str(held.fileno())

    class HeldFdOnly:
        def listdir(self, path: str) -> list[str]:
            assert path == root
            return [descriptor]

        def readlink(self, path: str) -> str:
            assert path == f"{root}/{descriptor}"
            return os.readlink(path)

    try:
        _require_process_socket_owner(HeldFdOnly(), os.getpid(), metadata)
    except ExternalSignerOsObservationError as error:
        assert str(error) == FAIL_OS_OBSERVER_PROCESS_SOCKET_NOT_OWNED
        return "rejected_inode_comparison"
    return "accepted_inode_comparison"


def _record_kernel_characterization(record_property, **observations: object) -> None:
    report = {
        "kernel_release": os.uname().release,
        "machine": os.uname().machine,
        "namespaces": {name: os.readlink(f"/proc/self/ns/{name}")
                       for name in ("pid", "user", "net", "mnt")},
        "scope": "same-process test-owned sockets; not external signer authority",
        "production_bridge_qualified": False,
        **observations,
    }
    record_property("socket_kernel_characterization", json.dumps(report, sort_keys=True))


def _held_stat_evidence(held: socket.socket, metadata: os.stat_result) -> dict[str, int]:
    return {
        "fd_inode": os.fstat(held.fileno()).st_ino,
        "path_inode": metadata.st_ino,
        "path_device_major": os.major(metadata.st_dev),
        "path_device_minor": os.minor(metadata.st_dev),
    }


def test_hosted_kernel_vfs_identity_survives_unlink_rebind(record_property) -> None:
    root = _require_hosted_kernel_characterization()
    with tempfile.TemporaryDirectory(prefix="rsi-sock-", dir=root) as directory:
        assert Path(directory).resolve().parent == root
        path = Path(directory) / "signer.sock"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as old:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as new:
                old.bind(str(path))
                old.listen(1)
                old_stat = path.lstat()
                first = _query_held_socket(old)
                _assert_vfs_association(first, old_stat, old)
                legacy = _legacy_held_fd_result(old, old_stat)
                path.unlink()  # Only our exact temporary pathname; old FD stays open.
                new.bind(str(path))
                new.listen(1)
                new_stat = path.lstat()
                second = _query_held_socket(new)
                repeated = _query_held_socket(old, first["cookie"])
                _assert_vfs_association(second, new_stat, new)
                _assert_vfs_association(repeated, old_stat, old)
                assert first == repeated
                assert (old_stat.st_dev, old_stat.st_ino) != (new_stat.st_dev, new_stat.st_ino)
                assert first["socket_inode"] != second["socket_inode"]
                _record_kernel_characterization(
                    record_property, before=first, replacement=second,
                    old_after_rebind=repeated, old_helper_result=legacy,
                    before_stat=_held_stat_evidence(old, old_stat),
                    replacement_stat=_held_stat_evidence(new, new_stat),
                    numeric_domains_happen_to_match=first["socket_inode"] == old_stat.st_ino,
                    pathname_rebound=True,
                )


def test_hosted_kernel_rejects_changed_socket_cookie(record_property) -> None:
    root = _require_hosted_kernel_characterization()
    with tempfile.TemporaryDirectory(prefix="rsi-sock-", dir=root) as directory:
        assert Path(directory).resolve().parent == root
        path = Path(directory) / "signer.sock"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as held:
            held.bind(str(path))
            held.listen(1)
            metadata = path.lstat()
            first = _query_held_socket(held)
            _assert_vfs_association(first, metadata, held)
            cookie = first["cookie"]
            changed = (cookie[0] ^ 1, cookie[1])
            if changed == _DIAG_NO_COOKIE:
                changed = (cookie[0] ^ 2, cookie[1])
            assert changed not in (cookie, _DIAG_NO_COOKIE)
            rejection = _query_held_socket(held, changed, expected_error=errno.ESTALE)
            repeated = _query_held_socket(held, cookie)
            assert repeated == first
            _record_kernel_characterization(
                record_property, before=first, wrong_cookie=rejection,
                before_stat=_held_stat_evidence(held, metadata),
                authentic_cookie_after_rejection=repeated,
            )
