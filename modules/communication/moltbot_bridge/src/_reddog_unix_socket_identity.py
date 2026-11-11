"""Private Linux socket/VFS association for the existing OS observer.

Exact local-kernel queries only. These bounded snapshots are not supervision,
an atomic lifetime guarantee, or authority to use the observed process.
"""

from __future__ import annotations

import errno
import math
import os
import re
import socket
import struct
import time
from dataclasses import dataclass

NO_COOKIE = (0xFFFFFFFF, 0xFFFFFFFF)
FD_LIMIT = 256
CANDIDATE_LIMIT = 16
BUDGET_SECONDS = 2.0
_SEQUENCE = 0x52534931
_U32 = 0xFFFFFFFF


class SocketDiagnosticError(OSError):
    """Correlated negative kernel response, distinct from procfs read failure."""


@dataclass(frozen=True)
class SocketIdentity:
    socket_inode: int
    cookie: tuple[int, int]
    vfs_inode: int | None
    vfs_device: int | None
    socket_type: int
    state: int


@dataclass(frozen=True)
class SocketOwnership:
    fd: str
    identity: SocketIdentity
    view: tuple[str, ...]
    deadline: float


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError("socket_identity_unqualified")


def _u32(value: object) -> bool:
    return type(value) is int and 0 < value <= _U32


def _request(inode: int, cookie: tuple[int, int]) -> bytes:
    _require(_u32(inode) and type(cookie) is tuple and len(cookie) == 2)
    _require(all(type(n) is int and 0 <= n <= _U32 for n in cookie))
    body = struct.pack("=BBHIIIII", socket.AF_UNIX, 0, 0, 0, inode, 2, *cookie)
    return struct.pack("=IHHII", 16 + len(body), 20, 1, _SEQUENCE, 0) + body


def _attributes(payload: bytes) -> dict[int, bytes]:
    result = {}
    offset = 16
    while offset < len(payload):
        _require(offset + 4 <= len(payload))
        size, kind = struct.unpack_from("=HH", payload, offset)
        end, aligned = offset + size, offset + ((size + 3) & ~3)
        _require(size >= 4 and end <= aligned <= len(payload))
        _require(kind in (1, 6) and kind not in result)
        _require(not any(payload[end:aligned]))
        result[kind] = payload[offset + 4:end]
        offset = aligned
    _require(offset == len(payload))
    _require(1 not in result or len(result[1]) == 8)
    _require(6 not in result or len(result[6]) == 1)
    return result


def _decode(payload: bytes, inode: int, cookie: tuple[int, int]) -> SocketIdentity:
    _require(len(payload) >= 16)
    family, kind, state, pad, found, c0, c1 = struct.unpack_from("=BBBBIII", payload)
    _require(family == socket.AF_UNIX and pad == 0 and found == inode)
    _require(kind in (1, 2, 5) and 1 <= state <= 12)
    _require((c0, c1) != NO_COOKIE and (cookie == NO_COOKIE or cookie == (c0, c1)))
    attrs = _attributes(payload)
    vfs = struct.unpack("=II", attrs[1]) if 1 in attrs else (None, None)
    return SocketIdentity(inode, (c0, c1), *vfs, kind, state)


def _reply(raw, ancillary, flags, sender, port, request, inode, cookie):
    _require(sender == (0, 0) and not ancillary and flags == 0)
    _require(16 <= len(raw) <= 4096)
    size, kind, reply_flags, sequence, reply_port = struct.unpack_from("=IHHII", raw)
    _require(size == len(raw) and size % 4 == 0 and reply_flags == 0)
    _require(sequence == _SEQUENCE and reply_port == port and kind in (2, 20))
    payload = raw[16:]
    if kind == 2:
        _require(len(payload) == 4 + len(request) and payload[4:] == request)
        error = struct.unpack_from("=i", payload)[0]
        _require(-4095 <= error < 0)
        raise SocketDiagnosticError(-error, "socket_diagnostic_rejected")
    return _decode(payload, inode, cookie)


def query_unix_socket(inode: int, cookie: tuple[int, int], timeout: float) -> SocketIdentity:
    """One exact query; finite datagram, kernel address, no dump or retry."""
    _require(math.isfinite(timeout) and 0 < timeout <= BUDGET_SECONDS)
    request = _request(inode, cookie)
    deadline = time.monotonic() + timeout
    with socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, 4) as channel:
        channel.settimeout(_transport_remaining(deadline))
        channel.bind((0, 0))
        port = channel.getsockname()[0]
        _require(_u32(port))
        channel.settimeout(_transport_remaining(deadline))
        _require(channel.sendto(request, (0, 0)) == len(request))
        channel.settimeout(_transport_remaining(deadline))
        raw, ancillary, flags, sender = channel.recvmsg(4096)
        _transport_remaining(deadline)
    return _reply(raw, ancillary, flags, sender, port, request, inode, cookie)


def _transport_remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    _require(math.isfinite(remaining) and 0 < remaining <= BUDGET_SECONDS)
    return remaining


def _remaining(backend, deadline: float) -> float:
    now = backend.monotonic()
    _require(math.isfinite(now) and math.isfinite(deadline))
    remaining = deadline - now
    _require(0 < remaining <= BUDGET_SECONDS)
    return remaining


def _status_pid(payload: bytes, expected: int) -> None:
    _require(type(payload) is bytes and len(payload) <= 65536)
    fields = {}
    for line in payload.decode("ascii").splitlines():
        if line.startswith(("Pid:", "NSpid:")):
            key, value = line.split(":", 1)
            _require(key not in fields)
            fields[key] = value.split()
    _require(fields == {"Pid": [str(expected)], "NSpid": [str(expected)]})


def _view(backend, pid: int, deadline: float) -> tuple[str, ...]:
    _remaining(backend, deadline)
    current = backend.current_pid()
    _require(type(current) is int and current > 0)
    _require(backend.readlink("/proc/self") == str(current))
    _status_pid(backend.read_bytes("/proc/self/status"), current)
    _status_pid(backend.read_bytes(f"/proc/{pid}/status"), pid)
    values = [str(current), str(pid)]
    for name in ("pid", "net", "mnt", "user"):
        _remaining(backend, deadline)
        own = backend.readlink(f"/proc/self/ns/{name}")
        other = backend.readlink(f"/proc/{pid}/ns/{name}")
        _require(re.fullmatch(name + r":\[[1-9][0-9]*\]", own) is not None)
        _require(own == other)
        values.append(own)
    _remaining(backend, deadline)
    return tuple(values)


def _matches(identity: SocketIdentity, metadata) -> bool:
    _require(type(identity) is SocketIdentity)
    if (identity.vfs_inode, identity.vfs_device) != (
        metadata.st_ino, (os.major(metadata.st_dev) << 20) | os.minor(metadata.st_dev)
    ):
        return False
    _require(identity.socket_type == socket.SOCK_STREAM and identity.state == 10)
    return True


def _query_fd(backend, pid, fd, inode, cookie, deadline):
    path, link = f"/proc/{pid}/fd/{fd}", f"socket:[{inode}]"
    _remaining(backend, deadline)
    _require(backend.readlink(path) == link)
    result = backend.query_unix_socket(inode, cookie, _remaining(backend, deadline))
    _remaining(backend, deadline)
    _require(backend.readlink(path) == link)
    _remaining(backend, deadline)
    _require(type(result) is SocketIdentity and result.socket_inode == inode)
    _require(result.cookie != NO_COOKIE)
    _require(cookie == NO_COOKIE or result.cookie == cookie)
    return result


def _candidates(backend, pid, deadline):
    _remaining(backend, deadline)
    names = backend.listdir(f"/proc/{pid}/fd")
    _remaining(backend, deadline)
    _require(type(names) is list and len(names) <= FD_LIMIT and len(set(names)) == len(names))
    seen = set()
    for fd in names:
        _remaining(backend, deadline)
        _require(type(fd) is str and re.fullmatch(r"0|[1-9][0-9]{0,9}", fd) is not None)
        link = backend.readlink(f"/proc/{pid}/fd/{fd}")
        _remaining(backend, deadline)
        if not link.startswith("socket:["):
            continue
        match = re.fullmatch(r"socket:\[([1-9][0-9]*)\]", link)
        _require(match is not None)
        inode = int(match.group(1))
        _require(_u32(inode))
        if inode in seen:
            continue
        seen.add(inode)
        _require(len(seen) <= CANDIDATE_LIMIT)
        yield fd, inode


def _discover(backend, pid, metadata, deadline):
    found = None
    for fd, inode in _candidates(backend, pid, deadline):
        try:
            identity = _query_fd(backend, pid, fd, inode, NO_COOKIE, deadline)
        except SocketDiagnosticError as error:
            if error.errno != errno.ENOENT:
                raise
            _remaining(backend, deadline)
            continue
        if _matches(identity, metadata):
            _require(found is None)
            found = (fd, identity)
    _require(found is not None)
    return found


def require_socket_owner(backend, pid: int, metadata, previous=None) -> SocketOwnership:
    """Associate one bounded process FD snapshot, then recheck its cookie."""
    _require(_u32(metadata.st_ino))
    _require(0 <= os.major(metadata.st_dev) < 4096 and 0 <= os.minor(metadata.st_dev) < 1048576)
    deadline = backend.monotonic() + BUDGET_SECONDS if previous is None else previous.deadline
    view = _view(backend, pid, deadline)
    if previous is None:
        fd, identity = _discover(backend, pid, metadata, deadline)
    else:
        _require(type(previous) is SocketOwnership and view == previous.view)
        fd = previous.fd
        identity = _query_fd(backend, pid, fd, previous.identity.socket_inode,
                             previous.identity.cookie, deadline)
        _require(identity == previous.identity and _matches(identity, metadata))
    _require(_view(backend, pid, deadline) == view)
    _remaining(backend, deadline)
    return SocketOwnership(fd, identity, view, deadline)
