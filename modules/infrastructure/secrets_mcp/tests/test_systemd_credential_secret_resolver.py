"""Controlled OS fixtures qualify checks, not actual systemd mount/provisioning."""
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
import stat
import struct

import pytest

from modules.infrastructure.secrets_mcp.src import systemd_credential_secret_resolver as subject


def binding(**changes):
    values = dict(credential_directory="/run/credentials/test.service", expected_uid=42,
                  expected_gid=42, expected_requester="signer:test", issued_at=100,
                  expires_at=160, credential_ids=frozenset({"signing", "audit"}))
    return subject.SystemdCredentialBinding(**(values | changes))


class Kernel:
    """Inert descriptor-relative OS model; never touches credentials or the host."""
    O_RDONLY, O_NOFOLLOW, O_CLOEXEC, O_NONBLOCK, O_DIRECTORY, ST_RDONLY = 0, 1, 2, 4, 8, 1

    def __init__(self):
        self.uid = self.gid = 42
        self.content = b"public-fixture-value"
        self.opened, self.closed, self.fds = [], [], {}
        self.reads, self.offset = 0, 0
        self.block = None
        self.modify = lambda name, value: value
        self.readonly = True
        self.after_read = lambda: None
        self.acl_calls = []
        self.acl_modify = lambda name, raw: raw

    def getuid(self): return self.uid
    def geteuid(self): return self.uid
    def getgid(self): return self.gid
    def getegid(self): return self.gid

    def open(self, name, flags, *, dir_fd=None):
        self.opened.append((name, flags, dir_fd))
        assert flags & self.O_NOFOLLOW and flags & self.O_CLOEXEC
        if name == self.block:
            raise OSError("inert blocked link")
        if name != "/":
            assert dir_fd in self.fds
        fd = len(self.opened) + 10
        self.fds[fd] = name
        return fd

    def fstat(self, fd):
        name = self.fds[fd]
        file = name in {"signing", "audit"}
        mode = stat.S_IFREG | 0o440 if file else stat.S_IFDIR | (0o550 if name == "test.service" else 0o755)
        info = SimpleNamespace(st_mode=mode, st_uid=0, st_gid=0,
                               st_nlink=1, st_dev=1, st_ino=fd, st_size=len(self.content), st_mtime_ns=1, st_ctime_ns=1)
        return self.modify(name, info)

    def fstatvfs(self, fd): return SimpleNamespace(f_flag=1 if self.readonly else 0)

    def getxattr(self, fd, attribute):
        assert type(fd) is int and fd in self.fds and attribute == "system.posix_acl_access"
        name = self.fds[fd]
        self.acl_calls.append((fd, attribute, name))
        p, u = (5 if name == "test.service" else 4), 0xFFFFFFFF
        entries = ((1, p, u), (2, p, 42), (4, 0, u), (16, p, u), (32, 0, u))
        raw = struct.pack("<I", 2) + b"".join(struct.pack("<HHI", *v) for v in entries)
        return self.acl_modify(name, raw)

    def read(self, fd, count):
        self.reads += 1
        value = self.content[self.offset:self.offset + count]
        self.offset += len(value)
        self.after_read()
        return value

    def close(self, fd):
        self.closed.append(fd)
        del self.fds[fd]


@pytest.fixture
def setup(monkeypatch):
    kernel = Kernel()
    clocks = [110.0, 10.0]
    monkeypatch.setattr(subject, "os", kernel)
    monkeypatch.setattr(subject, "sys", SimpleNamespace(platform="linux"))
    events = []
    resolver = subject.SystemdCredentialSecretResolver(
        binding(), clock=lambda: clocks[0], monotonic=lambda: clocks[1], audit_callback=events.append)
    return kernel, clocks, events, resolver


@pytest.mark.parametrize("value", [None, True, 3, "op://v/i/f", "systemd-creds://", "systemd-creds://../x",
                                    "systemd-creds://x/y", "systemd-creds://a?b", "systemd-creds://a%2Fb",
                                    "systemd-creds://ä", "systemd-creds://a\n", "systemd-creds://" + "a" * 129])
def test_parser_rejects_other_backend_or_unsafe_identifier(value):
    assert subject.parse_systemd_credential_reference(value) is None


def test_parser_is_pure_and_binding_is_frozen():
    assert subject.parse_systemd_credential_reference("systemd-creds://a.B_2-3") == "a.B_2-3"
    with pytest.raises(FrozenInstanceError):
        binding().expected_uid = 0


@pytest.mark.parametrize("change", [
    {"credential_directory": "/tmp/test.service"}, {"credential_directory": "/run/credentials/../x.service"},
    {"credential_directory": "/run/credentials/a.service/"}, {"expected_uid": 0}, {"expected_gid": True},
    {"expected_uid": 42.0}, {"expected_requester": " "}, {"expected_requester": "x\n"},
    {"issued_at": True}, {"issued_at": -1}, {"issued_at": float("nan")}, {"expires_at": float("inf")},
    {"expires_at": 401}, {"expires_at": 100}, {"expires_at": 10**1000},
    {"credential_ids": {"signing"}}, {"credential_ids": frozenset()}, {"credential_ids": frozenset({"../x"})},
    {"max_secret_bytes": True}, {"max_secret_bytes": 0}, {"max_secret_bytes": 65537},
])
def test_invalid_binding_metadata_rejected_without_io(change):
    with pytest.raises(ValueError, match="systemd_credential_binding_invalid"):
        binding(**change)


def test_constructor_no_io_and_success_reuses_safe_result_and_audit(setup):
    kernel, clocks, events, resolver = setup
    assert kernel.opened == []
    result = resolver.resolve("systemd-creds://signing", "signer:test")
    assert result.success and result.get_value() == "public-fixture-value" and result.ttl_remaining == 50
    assert [x[0] for x in kernel.opened] == ["/", "run", "credentials", "test.service", "signing"]
    assert not kernel.fds and len(kernel.closed) == 5
    assert [x[2] for x in kernel.acl_calls] == ["test.service", "signing"]
    assert events[0].event_type == "credential_pre_delivery_validation"
    assert "public-fixture-value" not in str(result) + str(result.to_audit_dict()) + str(events[0].to_dict())
    assert "public-fixture-value" not in repr(vars(resolver))
    kernel.content, kernel.offset = b"different-public-value", 0
    assert resolver.resolve("systemd-creds://signing", "signer:test").get_value() == "different-public-value"
    assert len(kernel.opened) == 10


@pytest.mark.parametrize("case", ["wrong_requester", "custom_requester", "wrong_id", "malformed", "early",
                                  "expired", "wall_rollback", "mono_expired", "mono_rollback", "uid", "gid", "platform"])
def test_preconditions_reject_before_any_file_open(setup, monkeypatch, case):
    kernel, clocks, events, resolver = setup
    ref, requester = "systemd-creds://signing", "signer:test"
    if case == "wrong_requester": requester = "worker"
    if case == "custom_requester": requester = SimpleNamespace()
    if case == "wrong_id": ref = "systemd-creds://not-allowed"
    if case == "malformed": ref = "op://v/i/SECRET"
    if case == "early": clocks[0] = 99
    if case == "expired": clocks[0] = 160
    if case == "wall_rollback": clocks[0] = 109
    if case == "mono_expired": clocks[:] = [111, 60]
    if case == "mono_rollback": clocks[1] = 9
    if case == "uid": kernel.uid = 0
    if case == "gid": kernel.gid = 43
    if case == "platform": monkeypatch.setattr(subject, "sys", SimpleNamespace(platform="win32"))
    result = resolver.resolve(ref, requester)
    assert not result.success and result.get_value() is None and kernel.opened == []
    assert "SECRET" not in str(result.to_audit_dict()) + str(events[0].to_dict())
    if case in {"wrong_requester", "custom_requester"}:
        assert events[0].requester_id is None


@pytest.mark.parametrize("component", ["/", "run", "credentials", "test.service", "signing"])
def test_nofollow_open_failure_closes_every_acquired_descriptor(setup, component):
    kernel, _, _, resolver = setup
    kernel.block = component
    assert not resolver.resolve("systemd-creds://signing", "signer:test").success
    assert kernel.reads == 0 and not kernel.fds


@pytest.mark.parametrize("case", ["ancestor_owner", "ancestor_writable", "directory_owner", "directory_group",
                                  "directory_other", "file_owner", "file_group", "file_writable", "file_other",
                                  "file_special", "file_fifo", "file_links", "writable_fs", "oversize", "empty"])
def test_unsafe_custody_metadata_rejects_before_read(setup, case):
    kernel, _, _, resolver = setup
    def change(name, info):
        if (case == "ancestor_owner" and name == "run") or (case == "directory_owner" and name == "test.service") or (case == "file_owner" and name == "signing"): info.st_uid = 42
        if case == "ancestor_writable" and name == "credentials": info.st_mode |= 0o020
        if (case == "directory_group" and name == "test.service") or (case == "file_group" and name == "signing"): info.st_gid = 43
        if case == "directory_other" and name == "test.service": info.st_mode |= 0o001
        if name == "signing":
            if case == "file_writable": info.st_mode |= 0o200
            if case == "file_other": info.st_mode |= 0o004
            if case == "file_special": info.st_mode |= 0o4000
            if case == "file_fifo": info.st_mode = stat.S_IFIFO | 0o440
            if case == "file_links": info.st_nlink = 2
            if case == "oversize": info.st_size = 65537
            if case == "empty": info.st_size = 0
        return info
    kernel.modify = change
    if case == "writable_fs": kernel.readonly = False
    assert not resolver.resolve("systemd-creds://signing", "signer:test").success
    assert kernel.reads == 0 and not kernel.fds


@pytest.mark.parametrize("case", ["utf8", "wall_expiry", "mono_expiry", "wall_rollback", "identity_drift", "size_drift"])
def test_read_result_rejected_if_encoding_identity_or_lifetime_changes(setup, case):
    kernel, clocks, events, resolver = setup
    if case == "utf8": kernel.content = b"\xff"
    def after_read():
        if case == "wall_expiry": clocks[0] = 160
        if case == "mono_expiry": clocks[:] = [111, 60]
        if case == "wall_rollback": clocks[0] = 109
        if case == "identity_drift": kernel.uid = 43
        if case == "size_drift": kernel.content = b"changed"
    kernel.after_read = after_read
    result = resolver.resolve("systemd-creds://signing", "signer:test")
    assert not result.success and result.get_value() is None and not kernel.fds
    assert not events[-1].success


@pytest.mark.parametrize("case", ["wall", "monotonic", "identity", "exception"])
def test_audit_callback_cannot_extend_delivery_lifetime_or_identity(setup, case):
    kernel, clocks, events, resolver = setup
    def callback(event):
        events.append(event)
        if case == "wall": clocks[0] = 160
        if case == "monotonic": clocks[1] = 60
        if case == "identity": kernel.uid = 0
        if case == "exception": raise RuntimeError("public-fixture-value")
    resolver._audit_callback = callback
    result = resolver.resolve("systemd-creds://signing", "signer:test")
    assert not result.success and result.get_value() is None and result.ttl_remaining == 0
    assert len(events) == 1 and events[0].success  # Validation, not delivery receipt.
    assert "public-fixture-value" not in str(result.to_audit_dict()) + str(events[0].to_dict())
    assert not kernel.fds


@pytest.mark.parametrize("target", ["test.service", "signing"])
@pytest.mark.parametrize("case", ["missing", "nonbytes", "short", "long", "version", "foreign_user",
                                  "owner_write", "user_write", "group_read", "mask_write", "other_read",
                                  "named_group", "duplicate_user", "reordered", "defined_owner_id"])
def test_exact_fd_bound_acl_rejects_nonselected_profiles_before_content(setup, target, case):
    kernel, _, _, resolver = setup
    def modify(name, raw):
        if name != target: return raw
        if case == "missing": raise OSError("No access ACL")
        if case == "nonbytes": return bytearray(raw)
        if case == "short": return raw[:-1]
        if case == "long": return raw + struct.pack("<HHI", 2, 4, 43)
        if case == "version": return struct.pack("<I", 1) + raw[4:]
        entries = [list(v) for v in struct.iter_unpack("<HHI", raw[4:])]
        if case == "foreign_user": entries[1][2] = 43
        if case == "owner_write": entries[0][1] |= 2
        if case == "user_write": entries[1][1] |= 2
        if case == "group_read": entries[2][1] = 4
        if case == "mask_write": entries[3][1] |= 2
        if case == "other_read": entries[4][1] = 4
        if case == "named_group": entries[1][0] = 8
        if case == "duplicate_user": entries[2] = list(entries[1])
        if case == "reordered": entries[0], entries[1] = entries[1], entries[0]
        if case == "defined_owner_id": entries[0][2] = 0
        return raw[:4] + b"".join(struct.pack("<HHI", *v) for v in entries)
    kernel.acl_modify = modify
    result = resolver.resolve("systemd-creds://signing", "signer:test")
    assert not result.success and result.get_value() is None
    assert kernel.reads == 0 and not kernel.fds


@pytest.mark.parametrize("target", ["test.service", "signing"])
def test_old_service_group_shape_is_not_a_fallback(setup, target):
    kernel, _, _, resolver = setup
    def modify(name, info):
        if name == target: info.st_gid = 42
        return info
    kernel.modify = modify
    assert not resolver.resolve("systemd-creds://signing", "signer:test").success
    assert kernel.reads == 0 and not kernel.fds
