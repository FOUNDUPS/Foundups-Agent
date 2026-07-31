"""Kernel-derived process and socket observation for the external RedDog signer.

Slice: REDDOG_EXTERNAL_SIGNER_OS_OBSERVER_PHASE1

This module observes an already-running Linux signer. It does not trust a
caller health DTO, start or stop services, execute commands, read secrets,
unlock a valve, or grant authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import re
import stat
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol


EXTERNAL_SIGNER_OS_OBSERVATION_SCHEMA_VERSION = (
    "reddog_external_signer_os_observation.v1"
)

FAIL_OS_OBSERVER_UNSUPPORTED_PLATFORM = "external_signer_os_unsupported_platform"
FAIL_OS_OBSERVER_POLICY_INVALID = "external_signer_os_policy_invalid"
FAIL_OS_OBSERVER_PROCESS_UNAVAILABLE = "external_signer_os_process_unavailable"
FAIL_OS_OBSERVER_PROCESS_NOT_LIVE = "external_signer_os_process_not_live"
FAIL_OS_OBSERVER_PROCESS_OWNER_MISMATCH = "external_signer_os_process_owner_mismatch"
FAIL_OS_OBSERVER_PROCESS_IDENTITY_MISMATCH = (
    "external_signer_os_process_identity_mismatch"
)
FAIL_OS_OBSERVER_PROCESS_CHANGED = "external_signer_os_process_changed"
FAIL_OS_OBSERVER_EXECUTABLE_MISMATCH = "external_signer_os_executable_mismatch"
FAIL_OS_OBSERVER_EXECUTABLE_IDENTITY_MISMATCH = (
    "external_signer_os_executable_identity_mismatch"
)
FAIL_OS_OBSERVER_REQUESTER_IDENTITY_MISMATCH = (
    "external_signer_os_requester_identity_mismatch"
)
FAIL_OS_OBSERVER_PROCESS_SOCKET_NOT_OWNED = (
    "external_signer_os_process_socket_not_owned"
)
FAIL_OS_OBSERVER_SOCKET_UNAVAILABLE = "external_signer_os_socket_unavailable"
FAIL_OS_OBSERVER_SOCKET_TYPE_MISMATCH = "external_signer_os_socket_type_mismatch"
FAIL_OS_OBSERVER_SOCKET_OWNER_MISMATCH = "external_signer_os_socket_owner_mismatch"
FAIL_OS_OBSERVER_SOCKET_MODE_MISMATCH = "external_signer_os_socket_mode_mismatch"
FAIL_OS_OBSERVER_SOCKET_CHANGED = "external_signer_os_socket_changed"
FAIL_OS_OBSERVER_RECEIPT_INVALID = "external_signer_os_receipt_invalid"

_BOOT_ID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_DEAD_PROCESS_STATES = frozenset({"X", "x", "Z"})


class ExternalSignerOsObservationError(RuntimeError):
    """Fail-closed observation error with one stable rejection code."""


class ExternalSignerOsObserverBackend(Protocol):
    """Narrow kernel-read interface used by deterministic tests."""

    def platform(self) -> str:
        """Return the running platform identifier."""

    def read_bytes(self, path: str) -> bytes:
        """Read one procfs payload."""

    def readlink(self, path: str) -> str:
        """Read one kernel-maintained symbolic link."""

    def stat(self, path: str, *, follow_symlinks: bool) -> os.stat_result:
        """Return kernel metadata for one path."""

    def listdir(self, path: str) -> list[str]:
        """List one procfs directory."""

    def current_uid(self) -> int:
        """Return the kernel identity of the observing process."""

    def current_gid(self) -> int:
        """Return the kernel group identity of the observing process."""


class ExternalSignerOsPolicyAuthorityBoundary(Protocol):
    """Rehydrate an opaque policy issued by external supervision."""

    def require(self, value: object) -> "VerifiedExternalSignerOsPolicy":
        """Return a verified policy or fail closed."""


@dataclass(frozen=True)
class ExternalSignerOsObservationPolicy:
    """Expected lifecycle identity supplied by the external service owner."""

    pid: int
    expected_signer_uid: int
    expected_signer_gid: int
    requester_uid: int
    requester_gid: int
    expected_executable: str
    expected_executable_device: int
    expected_executable_inode: int
    socket_path: str
    expected_socket_uid: int
    expected_socket_gid: int
    expected_socket_mode: int
    expected_process_start_identity: str


@dataclass(frozen=True)
class VerifiedExternalSignerOsPolicy:
    """Policy material admitted by an independent supervision boundary."""

    policy: ExternalSignerOsObservationPolicy
    authority_receipt_id: str
    authority_source_id: str


@dataclass(frozen=True)
class ExternalSignerOsObservationReceipt:
    """Immutable, audit-safe kernel observation with no raw command line."""

    schema_version: str
    pid: int
    process_uid: int
    process_gid: int
    process_state: str
    process_start_ticks: int
    boot_id: str
    process_start_identity: str
    executable_path: str
    executable_device: int
    executable_inode: int
    cmdline_digest: str
    cmdline_size_bytes: int
    socket_path: str
    socket_uid: int
    socket_gid: int
    socket_mode: int
    socket_device: int
    socket_inode: int
    socket_owned_by_process: bool
    observed_at_epoch: int
    receipt_id: str
    kernel_observed: bool = True
    raw_cmdline_persisted: bool = False
    authority_granted: bool = False
    valve_unlocked: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class _ProcessObservation:
    pid: int
    state: str
    start_ticks: int
    uid: int
    gid: int
    boot_id: str
    executable: str
    executable_stat: os.stat_result
    cmdline: bytes

    @property
    def start_identity(self) -> str:
        return f"{self.boot_id}:{self.start_ticks}"


class LinuxProcExternalSignerOsBackend:
    """Default read-only Linux kernel observation backend."""

    def platform(self) -> str:
        return sys.platform

    def read_bytes(self, path: str) -> bytes:
        return Path(path).read_bytes()

    def readlink(self, path: str) -> str:
        return os.readlink(path)

    def stat(self, path: str, *, follow_symlinks: bool) -> os.stat_result:
        return os.stat(path, follow_symlinks=follow_symlinks)

    def listdir(self, path: str) -> list[str]:
        return os.listdir(path)

    def current_uid(self) -> int:
        return os.geteuid()

    def current_gid(self) -> int:
        return os.getegid()


def observe_external_signer_os_state(
    policy: ExternalSignerOsObservationPolicy,
    *,
    backend: ExternalSignerOsObserverBackend | None = None,
    observed_at_epoch: int | None = None,
) -> ExternalSignerOsObservationReceipt:
    """Observe and validate one already-running external signer."""

    source = backend or LinuxProcExternalSignerOsBackend()
    _require_linux(source)
    _validate_policy(policy, source)
    before = _read_process(source, policy.pid)
    _validate_process(policy, before)
    socket_before = _read_socket(source, policy)
    _require_process_socket_owner(source, policy.pid, socket_before)
    after = _read_process(source, policy.pid)
    socket_after = _read_socket(source, policy)
    _require_process_socket_owner(source, policy.pid, socket_after)
    if not _same_process(before, after):
        _fail(FAIL_OS_OBSERVER_PROCESS_CHANGED)
    if _socket_identity(socket_before) != _socket_identity(socket_after):
        _fail(FAIL_OS_OBSERVER_SOCKET_CHANGED)
    payload = _receipt_payload(
        policy,
        after,
        socket_after,
        _observation_time(observed_at_epoch),
    )
    return ExternalSignerOsObservationReceipt(
        **payload,
        receipt_id=_digest(payload),
    )


def verify_external_signer_os_observation_receipt(
    receipt: ExternalSignerOsObservationReceipt,
) -> None:
    """Recompute one receipt digest and reject altered observations."""

    if not isinstance(receipt, ExternalSignerOsObservationReceipt):
        _fail(FAIL_OS_OBSERVER_RECEIPT_INVALID)
    payload = receipt.to_dict()
    receipt_id = str(payload.pop("receipt_id", ""))
    if (
        receipt.schema_version != EXTERNAL_SIGNER_OS_OBSERVATION_SCHEMA_VERSION
        or receipt_id != _digest(payload)
        or not receipt.kernel_observed
        or receipt.raw_cmdline_persisted
        or receipt.authority_granted
        or receipt.valve_unlocked
        or receipt.socket_owned_by_process is not True
    ):
        _fail(FAIL_OS_OBSERVER_RECEIPT_INVALID)


def _require_linux(backend: ExternalSignerOsObserverBackend) -> None:
    if not str(backend.platform()).startswith("linux"):
        _fail(FAIL_OS_OBSERVER_UNSUPPORTED_PLATFORM)


def _validate_policy(
    policy: ExternalSignerOsObservationPolicy,
    backend: ExternalSignerOsObserverBackend,
) -> None:
    if not isinstance(policy, ExternalSignerOsObservationPolicy):
        _fail(FAIL_OS_OBSERVER_POLICY_INVALID)
    values = (
        policy.pid,
        policy.expected_signer_uid,
        policy.expected_signer_gid,
        policy.requester_uid,
        policy.requester_gid,
        policy.expected_socket_uid,
        policy.expected_socket_gid,
        policy.expected_executable_device,
        policy.expected_executable_inode,
    )
    paths = (policy.expected_executable, policy.socket_path)
    invalid = (
        policy.pid <= 0
        or any(not isinstance(value, int) or value < 0 for value in values)
        or policy.expected_signer_uid == policy.requester_uid
        or policy.expected_signer_gid == policy.requester_gid
        or policy.expected_socket_mode not in range(0, 0o1000)
        or any(not _absolute_ascii_path(value) for value in paths)
        or not _start_identity_valid(policy.expected_process_start_identity)
    )
    if invalid:
        _fail(FAIL_OS_OBSERVER_POLICY_INVALID)
    try:
        requester = (backend.current_uid(), backend.current_gid())
    except (AttributeError, OSError, TypeError, ValueError):
        _fail(FAIL_OS_OBSERVER_REQUESTER_IDENTITY_MISMATCH)
    if requester != (policy.requester_uid, policy.requester_gid):
        _fail(FAIL_OS_OBSERVER_REQUESTER_IDENTITY_MISMATCH)


def _read_process(
    backend: ExternalSignerOsObserverBackend,
    pid: int,
) -> _ProcessObservation:
    root = f"/proc/{pid}"
    try:
        observed_pid, state, start_ticks = _parse_proc_stat(
            backend.read_bytes(f"{root}/stat")
        )
        uid, gid = _parse_proc_status(backend.read_bytes(f"{root}/status"))
        boot_id = backend.read_bytes("/proc/sys/kernel/random/boot_id").decode().strip()
        executable = backend.readlink(f"{root}/exe")
        executable_stat = backend.stat(f"{root}/exe", follow_symlinks=True)
        cmdline = backend.read_bytes(f"{root}/cmdline")
    except (AttributeError, OSError, TypeError, UnicodeError, ValueError):
        _fail(FAIL_OS_OBSERVER_PROCESS_UNAVAILABLE)
    if (
        observed_pid != pid
        or not _BOOT_ID.fullmatch(boot_id)
        or not stat.S_ISREG(executable_stat.st_mode)
    ):
        _fail(FAIL_OS_OBSERVER_PROCESS_UNAVAILABLE)
    return _ProcessObservation(
        observed_pid, state, start_ticks, uid, gid, boot_id,
        executable, executable_stat, cmdline,
    )


def _validate_process(
    policy: ExternalSignerOsObservationPolicy,
    observed: _ProcessObservation,
) -> None:
    if observed.state in _DEAD_PROCESS_STATES:
        _fail(FAIL_OS_OBSERVER_PROCESS_NOT_LIVE)
    if (observed.uid, observed.gid) != (
        policy.expected_signer_uid,
        policy.expected_signer_gid,
    ):
        _fail(FAIL_OS_OBSERVER_PROCESS_OWNER_MISMATCH)
    if observed.start_identity != policy.expected_process_start_identity:
        _fail(FAIL_OS_OBSERVER_PROCESS_IDENTITY_MISMATCH)
    if posixpath.normpath(observed.executable) != posixpath.normpath(
        policy.expected_executable
    ):
        _fail(FAIL_OS_OBSERVER_EXECUTABLE_MISMATCH)
    if _file_identity(observed.executable_stat) != (
        policy.expected_executable_device,
        policy.expected_executable_inode,
    ):
        _fail(FAIL_OS_OBSERVER_EXECUTABLE_IDENTITY_MISMATCH)


def _read_socket(
    backend: ExternalSignerOsObserverBackend,
    policy: ExternalSignerOsObservationPolicy,
) -> os.stat_result:
    try:
        metadata = backend.stat(policy.socket_path, follow_symlinks=False)
    except OSError:
        _fail(FAIL_OS_OBSERVER_SOCKET_UNAVAILABLE)
    if not stat.S_ISSOCK(metadata.st_mode):
        _fail(FAIL_OS_OBSERVER_SOCKET_TYPE_MISMATCH)
    if (metadata.st_uid, metadata.st_gid) != (
        policy.expected_socket_uid,
        policy.expected_socket_gid,
    ):
        _fail(FAIL_OS_OBSERVER_SOCKET_OWNER_MISMATCH)
    if stat.S_IMODE(metadata.st_mode) != policy.expected_socket_mode:
        _fail(FAIL_OS_OBSERVER_SOCKET_MODE_MISMATCH)
    return metadata


def _same_process(
    before: _ProcessObservation,
    after: _ProcessObservation,
) -> bool:
    return (
        before.start_identity == after.start_identity
        and before.pid == after.pid
        and (before.uid, before.gid) == (after.uid, after.gid)
        and before.executable == after.executable
        and _file_identity(before.executable_stat)
        == _file_identity(after.executable_stat)
        and _bytes_digest(before.cmdline) == _bytes_digest(after.cmdline)
        and after.state not in _DEAD_PROCESS_STATES
    )


def _require_process_socket_owner(
    backend: ExternalSignerOsObserverBackend,
    pid: int,
    metadata: os.stat_result,
) -> None:
    target = f"socket:[{int(metadata.st_ino)}]"
    root = f"/proc/{pid}/fd"
    try:
        links = (
            backend.readlink(f"{root}/{name}")
            for name in backend.listdir(root)
        )
        if target not in links:
            _fail(FAIL_OS_OBSERVER_PROCESS_SOCKET_NOT_OWNED)
    except ExternalSignerOsObservationError:
        raise
    except (AttributeError, OSError, TypeError, ValueError):
        _fail(FAIL_OS_OBSERVER_PROCESS_SOCKET_NOT_OWNED)


def _file_identity(metadata: os.stat_result) -> tuple[int, int]:
    return int(metadata.st_dev), int(metadata.st_ino)


def _socket_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        int(metadata.st_dev),
        int(metadata.st_ino),
        int(metadata.st_uid),
        int(metadata.st_gid),
        int(metadata.st_mode),
    )


def _parse_proc_stat(payload: bytes) -> tuple[int, str, int]:
    text = payload.decode("ascii")
    opening = text.find(" (")
    closing = text.rfind(")")
    if opening < 1 or closing <= opening:
        raise ValueError("proc_stat_malformed")
    pid = int(text[:opening])
    fields = text[closing + 1 :].strip().split()
    if len(fields) < 20:
        raise ValueError("proc_stat_malformed")
    state = fields[0]
    start_ticks = int(fields[19])
    if len(state) != 1 or start_ticks <= 0:
        raise ValueError("proc_stat_malformed")
    return pid, state, start_ticks


def _parse_proc_status(payload: bytes) -> tuple[int, int]:
    fields: dict[str, tuple[int, ...]] = {}
    for line in payload.decode("ascii").splitlines():
        if line.startswith(("Uid:", "Gid:")):
            name, raw = line.split(":", 1)
            fields[name] = tuple(int(value) for value in raw.split())
    uids, gids = fields.get("Uid", ()), fields.get("Gid", ())
    if len(uids) != 4 or len(gids) != 4:
        raise ValueError("proc_status_malformed")
    if len(set(uids)) != 1 or len(set(gids)) != 1:
        raise ValueError("proc_credentials_transitioning")
    return uids[0], gids[0]


def _receipt_payload(
    policy: ExternalSignerOsObservationPolicy,
    process: _ProcessObservation,
    socket_metadata: os.stat_result,
    observed_at_epoch: int,
) -> dict[str, object]:
    if observed_at_epoch <= 0:
        _fail(FAIL_OS_OBSERVER_POLICY_INVALID)
    return {
        "schema_version": EXTERNAL_SIGNER_OS_OBSERVATION_SCHEMA_VERSION,
        "pid": process.pid,
        "process_uid": process.uid,
        "process_gid": process.gid,
        "process_state": process.state,
        "process_start_ticks": process.start_ticks,
        "boot_id": process.boot_id,
        "process_start_identity": process.start_identity,
        "executable_path": posixpath.normpath(process.executable),
        "executable_device": int(process.executable_stat.st_dev),
        "executable_inode": int(process.executable_stat.st_ino),
        "cmdline_digest": _bytes_digest(process.cmdline),
        "cmdline_size_bytes": len(process.cmdline),
        "socket_path": posixpath.normpath(policy.socket_path),
        "socket_uid": int(socket_metadata.st_uid),
        "socket_gid": int(socket_metadata.st_gid),
        "socket_mode": stat.S_IMODE(socket_metadata.st_mode),
        "socket_device": int(socket_metadata.st_dev),
        "socket_inode": int(socket_metadata.st_ino),
        "socket_owned_by_process": True,
        "observed_at_epoch": observed_at_epoch,
        "kernel_observed": True,
        "raw_cmdline_persisted": False,
        "authority_granted": False,
        "valve_unlocked": False,
    }


def _observation_time(value: int | None) -> int:
    try:
        observed_at = int(time.time() if value is None else value)
    except (TypeError, ValueError):
        _fail(FAIL_OS_OBSERVER_POLICY_INVALID)
    if observed_at <= 0:
        _fail(FAIL_OS_OBSERVER_POLICY_INVALID)
    return observed_at


def _start_identity_valid(value: object) -> bool:
    if not isinstance(value, str) or ":" not in value:
        return False
    boot_id, ticks = value.rsplit(":", 1)
    return bool(_BOOT_ID.fullmatch(boot_id)) and ticks.isdigit() and int(ticks) > 0


def _absolute_ascii_path(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and "\x00" not in value
        and all(ord(char) < 128 for char in value)
        and PurePosixPath(value).is_absolute()
    )


def _bytes_digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _digest(payload: dict[str, object]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return _bytes_digest(canonical.encode("ascii"))


def _fail(code: str) -> None:
    raise ExternalSignerOsObservationError(code)


__all__ = [
    "EXTERNAL_SIGNER_OS_OBSERVATION_SCHEMA_VERSION",
    "ExternalSignerOsObservationError",
    "ExternalSignerOsObservationPolicy",
    "ExternalSignerOsObservationReceipt",
    "ExternalSignerOsObserverBackend",
    "ExternalSignerOsPolicyAuthorityBoundary",
    "LinuxProcExternalSignerOsBackend",
    "VerifiedExternalSignerOsPolicy",
    "observe_external_signer_os_state",
    "verify_external_signer_os_observation_receipt",
]
