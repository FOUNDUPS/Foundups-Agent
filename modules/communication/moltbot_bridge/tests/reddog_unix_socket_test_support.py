"""Binary fixtures and explicitly opted-in hosted child visibility support."""
import errno
import hashlib
import json
import os
import select
import subprocess
import sys
import tempfile
import time
import struct
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from modules.communication.moltbot_bridge.src import _reddog_unix_socket_identity as diag
from modules.communication.moltbot_bridge.src import reddog_external_signer_os_observer as observer


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


# Fixed child program: no repository imports, command dispatch or service access.
_VISIBILITY_CHILD = r'''
import ctypes, json, os, resource, select, socket, sys
from pathlib import Path
libc = ctypes.CDLL(None, use_errno=True)
libc.prctl.argtypes = [ctypes.c_int] + [ctypes.c_ulong] * 4
libc.prctl.restype = ctypes.c_int
mode = int(sys.argv[2])
assert mode in (0, 1)
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as held:
    held.bind(sys.argv[1])
    held.listen(1)
    assert libc.prctl(4, mode, 0, 0, 0) == 0
    def snapshot():
        status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
        metadata = Path(sys.argv[1]).lstat()
        report = dict(pid=os.getpid(), ppid=os.getppid(), resuid=os.getresuid(),
            resgid=os.getresgid(), fd=held.fileno(), fd_inode=os.fstat(held.fileno()).st_ino,
            path_inode=metadata.st_ino, device_major=os.major(metadata.st_dev),
            device_minor=os.minor(metadata.st_dev), dumpable=libc.prctl(3, 0, 0, 0, 0),
            capabilities={k: int(status[k], 16) for k in ('CapEff', 'CapPrm', 'CapAmb')},
            namespaces={k: os.readlink('/proc/self/ns/' + k) for k in ('pid', 'net', 'mnt', 'user')},
            nspid=status['NSpid'].split(), core_limit=resource.getrlimit(resource.RLIMIT_CORE))
        payload = (json.dumps(report, sort_keys=True) + '\n').encode('ascii')
        assert len(payload) <= 4096 and os.write(1, payload) == len(payload)
    snapshot()
    for expected in (b'CHECK\n', b'STOP\n'):
        assert select.select([0], [], [], 15.0)[0]
        assert os.read(0, 6) == expected
        if expected == b'CHECK\n':
            snapshot()
'''


def _observer_view():
    payload = Path('/proc/self/status').read_bytes()
    assert len(payload) <= 65536
    fields = dict(line.split(':', 1) for line in payload.decode('ascii').splitlines())
    caps = {k: int(fields[k], 16) for k in ('CapEff', 'CapPrm', 'CapAmb')}
    assert all(not value & (1 << 19) for value in caps.values())
    uids, gids = list(os.getresuid()), list(os.getresgid())
    assert len(set(uids)) == len(set(gids)) == 1 and uids[0] > 0 and gids[0] > 0
    assert fields['NSpid'].split() == [str(os.getpid())]
    return dict(pid=os.getpid(), resuid=uids, resgid=gids, capabilities=caps,
                namespaces={k: os.readlink('/proc/self/ns/' + k)
                            for k in ('pid', 'net', 'mnt', 'user')})


def _child_snapshot(child):
    deadline, raw = time.monotonic() + 10.0, b''
    while not raw.endswith(b'\n'):
        remaining = deadline - time.monotonic()
        assert remaining > 0 and len(raw) < 4096, 'Bounded child readiness failed'
        assert select.select([child.stdout], [], [], remaining)[0], 'Child readiness timeout'
        part = os.read(child.stdout.fileno(), 4096 - len(raw))
        assert part, 'Child exited before readiness'
        raw += part
    assert b'\n' not in raw[:-1]
    report = json.loads(raw.decode('ascii'))
    assert type(report) is dict and set(report) == {
        'pid', 'ppid', 'resuid', 'resgid', 'fd', 'fd_inode', 'path_inode',
        'device_major', 'device_minor', 'dumpable', 'capabilities', 'namespaces',
        'nspid', 'core_limit'}
    assert child.poll() is None
    return report


def _check_child(report, child, own, mode, metadata):
    assert report['pid'] == child.pid and report['ppid'] == own['pid']
    assert report['resuid'] == own['resuid'] and report['resgid'] == own['resgid']
    assert report['namespaces'] == own['namespaces']
    assert report['capabilities'] == own['capabilities']
    assert report['nspid'] == [str(child.pid)]
    assert report['dumpable'] == mode and report['core_limit'] == [0, 0]
    assert type(report['fd']) is int and report['fd'] >= 3
    assert type(report['fd_inode']) is int and 0 < report['fd_inode'] <= 0xffffffff
    assert report['path_inode'] == metadata.st_ino
    assert (report['device_major'], report['device_minor']) == (
        os.major(metadata.st_dev), os.minor(metadata.st_dev))


def _observe_readable_child(child, path, before):
    backend = observer.LinuxProcExternalSignerOsBackend()
    first = observer._require_process_socket_owner(backend, child.pid, path.lstat())
    second = observer._require_process_socket_owner(
        backend, child.pid, path.lstat(), previous=first)
    assert first == second and first.fd == str(before['fd'])
    identity = first.identity
    assert identity.socket_inode == before['fd_inode']
    assert identity.vfs_inode == before['path_inode']
    assert (identity.vfs_device >> 20, identity.vfs_device & 0xfffff) == (
        before['device_major'], before['device_minor'])
    assert identity.cookie != diag.NO_COOKIE
    return dict(accepted=True, socket_inode=identity.socket_inode,
                vfs_inode=identity.vfs_inode, vfs_device=identity.vfs_device,
                cookie=identity.cookie, concrete_cookie_rechecked=True)


def _observe_nondumpable_child(child, path, before):
    fd_path = f"/proc/{child.pid}/fd/{before['fd']}"
    try:
        os.readlink(fd_path)
    except PermissionError as error:
        fd_errno = error.errno
        assert fd_errno in (errno.EACCES, errno.EPERM)
    else:
        raise AssertionError('Nondumpable child FD unexpectedly readable')
    try:
        observer._require_process_socket_owner(
            observer.LinuxProcExternalSignerOsBackend(), child.pid, path.lstat())
    except observer.ExternalSignerOsObservationError as error:
        assert str(error) == observer.FAIL_OS_OBSERVER_PROCESS_SOCKET_NOT_OWNED
        cause = error.__context__
        assert isinstance(cause, PermissionError)
        assert cause.errno in (errno.EACCES, errno.EPERM)
        return dict(accepted=False, fd_errno=fd_errno, observer_errno=cause.errno,
                    rejection=str(error))
    raise AssertionError('Nondumpable child ownership unexpectedly accepted')


def _stop_owned_child(child):
    try:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=5)
    finally:
        for pipe in (child.stdin, child.stdout, child.stderr):
            pipe.close()


def _qualify_child(directory, mode, own, popen):
    path = Path(directory) / 'socket'
    child = popen([sys.executable, '-I', '-B', '-c', _VISIBILITY_CHILD, str(path), str(mode)],
                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                  cwd=directory, env={'LC_ALL': 'C'}, close_fds=True, shell=False, bufsize=0)
    try:
        before = _child_snapshot(child)
        metadata = path.lstat()
        _check_child(before, child, own, mode, metadata)
        observe = _observe_readable_child if mode else _observe_nondumpable_child
        result = observe(child, path, before)
        assert child.poll() is None
        assert os.write(child.stdin.fileno(), b'CHECK\n') == 6
        after = _child_snapshot(child)
        assert before == after and path.lstat() == metadata
        assert own == _observer_view()
        assert os.write(child.stdin.fileno(), b'STOP\n') == 5
        assert child.wait(timeout=5) == 0
        assert child.stdout.read(4097) == child.stderr.read(4097) == b''
        return dict(before=before, after=after, observation=result,
                    live_after_observation=True, child_exit_code=child.returncode,
                    path_inode=metadata.st_ino, device_major=os.major(metadata.st_dev),
                    device_minor=os.minor(metadata.st_dev))
    finally:
        _stop_owned_child(child)


def qualify_process_visibility(root, mode, *, popen):
    assert sys.platform == 'linux' and mode in (0, 1)
    assert os.environ.get('FOUNDUPS_SOCKET_KERNEL_CHARACTERIZATION') == '1'
    assert root == Path(os.environ['RUNNER_TEMP']).resolve(strict=True)
    own = _observer_view()
    with tempfile.TemporaryDirectory(prefix='rsi-proc-', dir=root) as directory:
        assert Path(directory).resolve().parent == root
        report = _qualify_child(directory, mode, own, popen)
    assert not Path(directory).exists()
    return dict(report, observer=own, requested_dumpable=mode, temporary_removed=True,
                kernel_release=os.uname().release, machine=os.uname().machine,
                child_source_sha256=hashlib.sha256(_VISIBILITY_CHILD.encode('utf-8')).hexdigest(),
                scope='same-UID disposable child; no external signer authority',
                production_supervision_qualified=False)
