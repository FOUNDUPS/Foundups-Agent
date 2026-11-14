"""Tests for kernel-derived external signer process/socket observation."""

from __future__ import annotations

import ast
import errno
import json
import os
import socket
import stat
import struct
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest
from modules.communication.moltbot_bridge.src import _reddog_unix_socket_identity as diag
from modules.communication.moltbot_bridge.src import reddog_external_signer_os_observer as observer
from modules.communication.moltbot_bridge.tests.reddog_unix_socket_test_support import (
    install_wire, mutate_backend, qualify_process_visibility,
)

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
        self.socket_inode = 303
        self.diagnostic = diag.SocketIdentity(303, (11, 12), 202, 9, 1, 10)
        self.queries = []

    def platform(self) -> str:
        return self.platform_name

    def read_bytes(self, path: str) -> bytes:
        if path == "/proc/self/status":
            return b"Pid:\t1000\nNSpid:\t1000\n"
        if path == f"/proc/{PID}/stat":
            self.stat_reads += 1
            ticks = START_TICKS if self.stat_reads == 1 else self.second_start_ticks
            return _proc_stat(self.state, ticks, pid=self.reported_pid)
        if path == f"/proc/{PID}/status":
            return (
                f"Pid:\t{PID}\nNSpid:\t{PID}\nName:\tsigner\nUid:\t{self.uid}\t{self.uid}\t{self.uid}\t{self.uid}\n"
                f"Gid:\t{self.gid}\t{self.gid}\t{self.gid}\t{self.gid}\n"
            ).encode("ascii")
        if path == "/proc/sys/kernel/random/boot_id":
            return (BOOT_ID + "\n").encode("ascii")
        if path == f"/proc/{PID}/cmdline":
            return self.cmdline
        raise FileNotFoundError(path)

    def readlink(self, path: str) -> str:
        if path == "/proc/self":
            return "1000"
        if "/ns/" in path:
            return path.rsplit("/", 1)[1] + ":[123]"
        if path == f"/proc/{PID}/exe":
            return self.executable
        if path == f"/proc/{PID}/fd/7" and self.process_owns_socket:
            inode = self.socket_inode
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

    def current_pid(self):
        return 1000

    def monotonic(self):
        return 0.0

    def query_unix_socket(self, inode, cookie, timeout):
        self.queries.append((inode, cookie, timeout))
        return self.diagnostic


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
    root = Path(__file__).parents[1] / "src"
    for name in ("reddog_external_signer_os_observer.py", "_reddog_unix_socket_identity.py"):
        tree = ast.parse((root / name).read_text(encoding="utf-8"))
        imports = {alias.name.split(".")[0] for node in ast.walk(tree)
                   if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
        forbidden = {"subprocess", "requests", "urllib", "httpx", "ctypes"}
        assert imports.isdisjoint(forbidden)
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        assert not {n.func.attr for n in calls if isinstance(n.func, ast.Attribute)} & {
            "system", "popen", "spawn", "fork", "execv", "execve", "kill", "connect", "accept", "listen"}
        socket_calls = [n for n in calls if isinstance(n.func, ast.Attribute) and n.func.attr == "socket"]
        assert len(socket_calls) == int(name.startswith("_"))
        for node in socket_calls:
            assert ast.unparse(node) == "socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, 4)"
        for node in calls:
            if isinstance(node.func, ast.Attribute) and node.func.attr == "sendto":
                assert ast.literal_eval(node.args[1]) == (0, 0)


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






def _query_held_socket(held, cookie=diag.NO_COOKIE, *, expected_error=None):
    inode = os.fstat(held.fileno()).st_ino
    if expected_error is not None:
        with pytest.raises(diag.SocketDiagnosticError) as raised:
            diag.query_unix_socket(inode, cookie, 2.0)
        assert raised.value.errno == expected_error
        return {"error": -raised.value.errno}
    result = diag.query_unix_socket(inode, cookie, 2.0)
    return {"socket_inode": result.socket_inode, "cookie": result.cookie,
            "vfs_inode": result.vfs_inode, "vfs_device": result.vfs_device}


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


def _legacy_held_fd_result(held, metadata):
    # Historical PR1921 integer-comparison replay, NOT the repaired observer.
    old_target = f"socket:[{metadata.st_ino}]"
    link = os.readlink(f"/proc/{os.getpid()}/fd/{held.fileno()}")
    return "accepted_inode_comparison" if link == old_target else "rejected_inode_comparison"


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


@pytest.mark.parametrize("inode", [303, 202])
def test_distinct_and_coincident_numbers_require_vfs_mapping(inode):
    backend = FakeBackend()
    backend.socket_inode = inode
    backend.diagnostic = replace(backend.diagnostic, socket_inode=inode)
    receipt = observe_external_signer_os_state(_policy(), backend=backend)
    assert receipt.socket_inode == 202 and not receipt.authority_granted
    assert [q[1] for q in backend.queries] == [diag.NO_COOKIE, (11, 12)]
    backend.diagnostic = replace(backend.diagnostic, vfs_inode=999)
    _assert_rejected(FAIL_OS_OBSERVER_PROCESS_SOCKET_NOT_OWNED, _policy(), backend)


@pytest.mark.parametrize("scenario", [
    "vfs_inode", "vfs_device", "missing_vfs", "socket_type", "state", "nan", "deadline",
    "fd_limit", "invalid_fd", "socket_limit", "ambiguous", "timeout", "unsupported", "cookie_change",
    "self_pid", "namespace", "namespace_change", "fd_change", "self_status_missing",
    "self_status_multiple", "self_status_duplicate", "target_status",
    "target_status_missing", "target_status_multiple", "target_status_duplicate",
    "second_enoent", "late_deadline", "fd_disappears",
])
def test_production_ownership_adversarial_backend_controls(scenario):
    backend = FakeBackend()
    mutate_backend(backend, scenario, PID)
    _assert_rejected(FAIL_OS_OBSERVER_PROCESS_SOCKET_NOT_OWNED, _policy(), backend)


@pytest.mark.parametrize("change", [
    {"family": 2}, {"pad": 1}, {"inode": 304}, {"kind": 99}, {"state": 0},
    {"c0": 99}, {"c0": 0xffffffff, "c1": 0xffffffff}, {"short_attr": True},
    {"duplicate_vfs": True}, {"unknown_attr": True}, {"length_delta": 4},
    {"flags": 2}, {"sequence": 1}, {"port": 0}, {"message_kind": 3},
    {"truncate": True}, {"recv_flags": 32}, {"ancillary": [1]}, {"sender": (1, 0)},
    {"short_send": True}, {"timeout": True}, {"error": 0},
    {"error": errno.ENOENT, "wrong_echo": True}, {"error": errno.EOPNOTSUPP},
])
def test_exact_kernel_protocol_rejects_uncorrelated_or_malformed_data(monkeypatch, change):
    channel = install_wire(monkeypatch, change)
    with pytest.raises((OSError, ValueError)):
        diag.query_unix_socket(303, (11, 12), 1.0)
    assert channel.closed


def test_exact_kernel_query_and_default_observer_wiring(monkeypatch):
    channel = install_wire(monkeypatch, {})
    result = diag.query_unix_socket(303, diag.NO_COOKIE, 1.0)
    assert result == diag.SocketIdentity(303, (11, 12), 202, 9, 1, 10)
    assert channel.request == struct.pack("=IHHIIBBHIIIII",
        40, 20, 1, 0x52534931, 0, 1, 0, 0, 0, 303, 2, *diag.NO_COOKIE)
    assert [c[1] for c in channel.calls if c[0] == "timeout"] == [1.0, 1.0, 1.0]
    assert ("recvmsg", 4096) in channel.calls and channel.closed
    backend = FakeBackend()
    monkeypatch.setattr(observer, "LinuxProcExternalSignerOsBackend", lambda: backend)
    assert observe_external_signer_os_state(_policy()).socket_owned_by_process
    assert len(backend.queries) == 2


@pytest.mark.parametrize("unrelated", ["absent", "foreign_vfs", "unbound", "connected"])
def test_duplicate_fds_and_unrelated_socket_are_bounded(unrelated):
    backend = FakeBackend()
    link = backend.readlink
    backend.listdir = lambda p: ["7", "8", "9", "10"]
    backend.readlink = lambda p: {f"/proc/{PID}/fd/8": "socket:[303]",
        f"/proc/{PID}/fd/9": "socket:[404]", f"/proc/{PID}/fd/10": "/tmp/ordinary"}.get(p) or link(p)
    query = backend.query_unix_socket
    def with_unrelated(inode, cookie, timeout):
        if inode == 404:
            if unrelated == "absent":
                raise diag.SocketDiagnosticError(errno.ENOENT, "fixture")
            return replace(backend.diagnostic, socket_inode=404,
                           vfs_inode=999 if unrelated == "foreign_vfs" else None,
                           state=1 if unrelated == "connected" else 10)
        return query(inode, cookie, timeout)
    backend.query_unix_socket = with_unrelated
    assert observe_external_signer_os_state(_policy(), backend=backend).socket_owned_by_process
    assert len(backend.queries) == 2  # duplicate FD never issues another query


@pytest.mark.parametrize("inode", [0, 0x100000000])
def test_unrepresentable_inode_rejects_before_query(inode):
    backend = FakeBackend()
    metadata = _stat_result(stat.S_IFSOCK | 0o600, SIGNER_UID, SIGNER_GID, 9, inode)
    with pytest.raises(ExternalSignerOsObservationError):
        _require_process_socket_owner(backend, PID, metadata)
    assert not backend.queries


@pytest.mark.parametrize("limit", [256, 257])
def test_default_fd_scan_stops_at_budget(monkeypatch, limit):
    from types import SimpleNamespace
    class Entries:
        def __enter__(self):
            return iter(SimpleNamespace(name=str(i)) for i in range(limit))
        def __exit__(self, *_args):
            self.closed = True
    entries = Entries()
    monkeypatch.setattr(observer, "os", SimpleNamespace(scandir=lambda p: entries))
    backend = observer.LinuxProcExternalSignerOsBackend()
    if limit == 257:
        with pytest.raises(ValueError):
            backend.listdir("/proc/4242/fd")
    else:
        assert len(backend.listdir("/proc/4242/fd")) == 256
    assert entries.closed


def test_production_owned_socket_seam(record_property):
    root = _require_hosted_kernel_characterization()
    with tempfile.TemporaryDirectory(prefix="rsi-map-", dir=root) as directory:
        path = Path(directory) / "socket"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as held:
            held.bind(str(path))
            held.listen(1)
            class HeldBackend(observer.LinuxProcExternalSignerOsBackend):
                def listdir(self, requested):
                    assert requested == f"/proc/{os.getpid()}/fd"
                    return [str(held.fileno())]
            backend = HeldBackend()
            metadata = path.lstat()
            held_metadata = os.fstat(held.fileno())
            first = _require_process_socket_owner(backend, os.getpid(), metadata)
            second = _require_process_socket_owner(backend, os.getpid(), path.lstat(), previous=first)
            assert first == second and first.identity.socket_inode == os.fstat(held.fileno()).st_ino
            path.unlink()
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as replacement:
                replacement.bind(str(path))
                replacement.listen(1)
                with pytest.raises(ExternalSignerOsObservationError):
                    _require_process_socket_owner(backend, os.getpid(), path.lstat(), previous=first)
            record_property("production_socket_association", json.dumps({
                "socket_inode": first.identity.socket_inode, "vfs_inode": first.identity.vfs_inode,
                "cookie": first.identity.cookie, "path_inode": metadata.st_ino,
                "fd_inode": held_metadata.st_ino, "vfs_device": first.identity.vfs_device,
                "path_device_major": os.major(metadata.st_dev), "path_device_minor": os.minor(metadata.st_dev),
                "scope": "own held FD; namespace and production association seam; no authority",
                "rebind_rejected": True, "production_supervision_qualified": False}))


@pytest.mark.parametrize('dumpable', [1, 0])
def test_hosted_child_process_visibility(dumpable, record_property):
    root = _require_hosted_kernel_characterization()
    report = qualify_process_visibility(root, dumpable, popen=subprocess.Popen)
    record_property('process_socket_visibility', json.dumps(report, sort_keys=True))
