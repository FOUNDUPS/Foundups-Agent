"""Inert binary-frame and backend mutations for the existing observer suite."""
import errno
import struct
from dataclasses import replace
from types import SimpleNamespace

from modules.communication.moltbot_bridge.src import _reddog_unix_socket_identity as diag


def frame(request, change):
    values = {"family": 1, "kind": 1, "state": 10, "pad": 0,
              "inode": 303, "c0": 11, "c1": 12, "vfs_inode": 202, "device": 9}
    values.update(change)
    payload = struct.pack("=BBBBIII", *(values[k] for k in
                          ("family", "kind", "state", "pad", "inode", "c0", "c1")))
    attr = struct.pack("=HHII", 12, 1, values["vfs_inode"], values["device"])
    if change.get("short_attr"):
        attr = struct.pack("=HH", 3, 1)
    if not change.get("missing_vfs"):
        payload += attr
    if change.get("duplicate_vfs"):
        payload += attr
    if change.get("unknown_attr"):
        payload += struct.pack("=HH", 4, 99)
    if change.get("error") is not None:
        echoed = request[:-1] + b"x" if change.get("wrong_echo") else request
        payload = struct.pack("=i", -change["error"]) + echoed
    kind = 2 if change.get("error") is not None else 20
    result = struct.pack("=IHHII", 16 + len(payload) + change.get("length_delta", 0),
                         change.get("message_kind", kind), change.get("flags", 0),
                         change.get("sequence", 0x52534931), change.get("port", 321)) + payload
    return result[:-1] if change.get("truncate") else result


class WireChannel:
    def __init__(self, change):
        self.change, self.calls, self.closed = change, [], False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.closed = True

    def settimeout(self, timeout):
        self.calls.append(("timeout", timeout))

    def bind(self, address):
        self.calls.append(("bind", address))

    def getsockname(self):
        return (321, 0)

    def sendto(self, request, address):
        self.request = request
        self.calls.append(("sendto", request, address))
        return len(request) - int(bool(self.change.get("short_send")))

    def recvmsg(self, limit):
        self.calls.append(("recvmsg", limit))
        if self.change.get("timeout"):
            raise TimeoutError("fixture")
        return (frame(self.request, self.change), self.change.get("ancillary", []),
                self.change.get("recv_flags", 0), self.change.get("sender", (0, 0)))


def install_wire(monkeypatch, change):
    channel = WireChannel(change)
    def make(family, kind, protocol):
        assert (family, kind, protocol) == (16, 3, 4)
        return channel
    monkeypatch.setattr(diag, "socket", SimpleNamespace(
        AF_NETLINK=16, SOCK_RAW=3, AF_UNIX=1, SOCK_STREAM=1, socket=make))
    monkeypatch.setattr(diag, "time", SimpleNamespace(monotonic=lambda: 100.0))
    return channel


def mutate_backend(backend, scenario, pid):
    if scenario in {"vfs_inode", "vfs_device", "socket_type", "state"}:
        value = {"vfs_inode": 999, "vfs_device": 10, "socket_type": 2, "state": 1}[scenario]
        backend.diagnostic = replace(backend.diagnostic, **{scenario: value})
    elif scenario == "missing_vfs":
        backend.diagnostic = replace(backend.diagnostic, vfs_inode=None, vfs_device=None)
    elif scenario in {"nan", "deadline"}:
        count = iter([0.0, 0.0, 3.0])
        backend.monotonic = (lambda: float("nan")) if scenario == "nan" else lambda: next(count, 3.0)
    elif scenario in {"fd_limit", "invalid_fd"}:
        backend.listdir = lambda _p: [str(i) for i in range(257)] if scenario == "fd_limit" else ["../7"]
    elif scenario in {"timeout", "unsupported", "cookie_change", "second_enoent", "late_deadline"}:
        query = backend.query_unix_socket
        def changed_query(inode, cookie, timeout):
            if scenario == "second_enoent":
                if cookie != diag.NO_COOKIE:
                    raise diag.SocketDiagnosticError(errno.ENOENT, "fixture")
                return query(inode, cookie, timeout)
            if scenario == "late_deadline":
                backend.monotonic = lambda: 3.0
                return query(inode, cookie, timeout)
            if scenario == "cookie_change":
                result = query(inode, cookie, timeout)
                return result if cookie == diag.NO_COOKIE else replace(result, cookie=(99, 12))
            raise OSError(errno.ETIMEDOUT if scenario == "timeout" else errno.EOPNOTSUPP, "fixture")
        backend.query_unix_socket = changed_query
    elif scenario in {"socket_limit", "ambiguous"}:
        backend.listdir = lambda _p: [str(i) for i in range(17 if scenario == "socket_limit" else 2)]
        original = backend.readlink
        backend.readlink = lambda p: f"socket:[{303 + int(p.rsplit('/', 1)[1])}]" if "/fd/" in p else original(p)
        backend.query_unix_socket = lambda inode, cookie, timeout: replace(
            backend.diagnostic, socket_inode=inode, vfs_inode=999 if scenario == "socket_limit" else 202)
    else:
        _mutate_view_or_fd(backend, scenario, pid)


def _mutate_view_or_fd(backend, scenario, pid):
    link, read = backend.readlink, backend.read_bytes
    def changed_link(path):
        value = link(path)
        if scenario == "self_pid" and path == "/proc/self":
            return "9999"
        if scenario == "namespace" and path == f"/proc/{pid}/ns/net":
            return "net:[999]"
        if scenario == "namespace_change" and "/ns/" in path and backend.queries:
            return value.replace("123", "124")
        if scenario == "fd_change" and "/fd/" in path and backend.queries:
            return "socket:[999]"
        if scenario == "fd_disappears" and "/fd/" in path and backend.queries:
            raise FileNotFoundError(path)
        return value
    def changed_read(path):
        value = read(path)
        if path == "/proc/self/status" and scenario.startswith("self_status_"):
            if scenario.endswith("missing"):
                return b"Pid:\t1000\n"
            if scenario.endswith("multiple"):
                return b"Pid:\t1000\nNSpid:\t1000\t1\n"
            return value + b"NSpid:\t1000\n"
        if path == f"/proc/{pid}/status" and scenario == "target_status":
            return value.replace(f"NSpid:\t{pid}".encode(), b"NSpid:\t9999")
        if path == f"/proc/{pid}/status" and scenario.startswith("target_status_"):
            marker = f"NSpid:\t{pid}\n".encode()
            if scenario.endswith("missing"):
                return value.replace(marker, b"")
            if scenario.endswith("multiple"):
                return value.replace(marker, f"NSpid:\t{pid}\t1\n".encode())
            return value + marker
        return value
    backend.readlink, backend.read_bytes = changed_link, changed_read
