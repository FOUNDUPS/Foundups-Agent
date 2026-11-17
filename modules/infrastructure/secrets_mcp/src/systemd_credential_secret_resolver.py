"""Read manager-delivered credentials after explicit, bounded custody checks.

The binding describes OS custody, not permission or a secret-access grant.
Callers must enforce those existing authority gates before calling resolve.
No environment discovery, decryption, provisioning, or secret cache lives here.
"""

from __future__ import annotations

import math
import os
import re
import stat
import struct
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from modules.infrastructure.secrets_mcp.src.vault_resolver import (
    AuditEvent, ResolveErrorCode, ResolveResult, hash_reference,
)

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z", re.ASCII)
_DIRECTORY = re.compile(
    r"/run/credentials/[A-Za-z0-9][A-Za-z0-9_.@:-]{0,240}\.service\Z", re.ASCII
)
_PREFIX = "systemd-creds://"


def parse_systemd_credential_reference(reference: str) -> str | None:
    """Return a single credential ID; never reinterpret another backend's URI."""
    if type(reference) is not str or not reference.startswith(_PREFIX):
        return None
    identifier = reference[len(_PREFIX):]
    return identifier if _ID.fullmatch(identifier) else None


def _finite(value: object) -> bool:
    try:
        return (type(value) is int or type(value) is float) and math.isfinite(value)
    except OverflowError:
        return False


@dataclass(frozen=True, slots=True)
class SystemdCredentialBinding:
    credential_directory: str
    expected_uid: int
    expected_gid: int
    expected_requester: str
    issued_at: int | float
    expires_at: int | float
    credential_ids: frozenset[str]
    max_secret_bytes: int = 65536

    def __post_init__(self) -> None:
        valid = (
            type(self.credential_directory) is str
            and _DIRECTORY.fullmatch(self.credential_directory)
            and type(self.expected_uid) is int and 0 < self.expected_uid < 2**32 - 1
            and type(self.expected_gid) is int and 0 < self.expected_gid < 2**32 - 1
            and type(self.expected_requester) is str
            and 0 < len(self.expected_requester) <= 128
            and self.expected_requester.isascii()
            and all(33 <= ord(c) <= 126 for c in self.expected_requester)
            and _finite(self.issued_at) and _finite(self.expires_at)
            and 0 <= self.issued_at < self.expires_at
            and self.expires_at - self.issued_at <= 300
            and type(self.credential_ids) is frozenset
            and 0 < len(self.credential_ids) <= 32
            and all(type(i) is str and _ID.fullmatch(i) for i in self.credential_ids)
            and type(self.max_secret_bytes) is int and 0 < self.max_secret_bytes <= 65536
        )
        if not valid:
            raise ValueError("systemd_credential_binding_invalid")


class _CredentialRejected(Exception):
    def __init__(self, code: ResolveErrorCode) -> None:
        self.code = code


def _identity_matches(binding: SystemdCredentialBinding) -> bool:
    return bool(
        sys.platform == "linux"
        and os.getuid() == os.geteuid() == binding.expected_uid
        and os.getgid() == os.getegid() == binding.expected_gid
    )


def _require_directory(fd: int, binding: SystemdCredentialBinding, *, credential: bool) -> None:
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise _CredentialRejected(ResolveErrorCode.RESOLVER_UNAVAILABLE)
    if credential and (info.st_gid != 0 or stat.S_IMODE(info.st_mode) != 0o550):
        raise _CredentialRejected(ResolveErrorCode.RESOLVER_UNAVAILABLE)
    if credential and not os.fstatvfs(fd).f_flag & os.ST_RDONLY:
        raise _CredentialRejected(ResolveErrorCode.RESOLVER_UNAVAILABLE)
    if credential:
        _require_credential_acl(fd, binding.expected_uid, directory=True)


def _require_credential_acl(fd: int, expected_uid: int, *, directory: bool) -> None:
    """Accept only the observed manager ACLv2 profile on the opened descriptor."""
    raw = os.getxattr(fd, "system.posix_acl_access")
    if type(raw) is not bytes or len(raw) != 44 or struct.unpack_from("<I", raw)[0] != 2:
        raise _CredentialRejected(ResolveErrorCode.RESOLVER_UNAVAILABLE)
    permission, undefined = (5 if directory else 4), 0xFFFFFFFF
    expected = ((1, permission, undefined), (2, permission, expected_uid),
                (4, 0, undefined), (16, permission, undefined), (32, 0, undefined))
    if tuple(struct.iter_unpack("<HHI", raw[4:])) != expected:
        raise _CredentialRejected(ResolveErrorCode.RESOLVER_UNAVAILABLE)


def _file_identity(info: os.stat_result) -> tuple:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read_file(directory_fd: int, identifier: str, binding: SystemdCredentialBinding) -> str:
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
    fd = os.open(identifier, flags, dir_fd=directory_fd)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
                or info.st_gid != 0 or stat.S_IMODE(info.st_mode) != 0o440
                or info.st_nlink != 1 or not os.fstatvfs(fd).f_flag & os.ST_RDONLY):
            raise _CredentialRejected(ResolveErrorCode.RESOLVER_UNAVAILABLE)
        _require_credential_acl(fd, binding.expected_uid, directory=False)
        if info.st_size > binding.max_secret_bytes:
            raise _CredentialRejected(ResolveErrorCode.OUTPUT_TOO_LARGE)
        if info.st_size <= 0:
            raise _CredentialRejected(ResolveErrorCode.UNKNOWN_REFERENCE)
        value = bytearray()
        while len(value) <= binding.max_secret_bytes:
            chunk = os.read(fd, min(4096, binding.max_secret_bytes + 1 - len(value)))
            if not chunk:
                break
            value.extend(chunk)
        if len(value) > binding.max_secret_bytes:
            raise _CredentialRejected(ResolveErrorCode.OUTPUT_TOO_LARGE)
        if len(value) != info.st_size or _file_identity(info) != _file_identity(os.fstat(fd)):
            raise _CredentialRejected(ResolveErrorCode.RESOLVER_UNAVAILABLE)
        return value.decode("utf-8", errors="strict")
    finally:
        os.close(fd)


def _read_credential(binding: SystemdCredentialBinding, identifier: str) -> str:
    """Walk from / with openat and retain descriptors, never follow path links."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptors = []
    try:
        descriptors.append(os.open("/", flags))
        _require_directory(descriptors[-1], binding, credential=False)
        parts = binding.credential_directory.split("/")[1:]
        for index, part in enumerate(parts):
            descriptors.append(os.open(part, flags, dir_fd=descriptors[-1]))
            _require_directory(descriptors[-1], binding, credential=index == len(parts) - 1)
        return _read_file(descriptors[-1], identifier, binding)
    finally:
        for fd in reversed(descriptors):
            os.close(fd)


class SystemdCredentialSecretResolver:
    """Read one explicitly selected manager credential; retain no secret value."""

    def __init__(
        self, binding: SystemdCredentialBinding, *,
        clock: Callable[[], float] = time.time,
        monotonic: Callable[[], float] = time.monotonic,
        audit_callback: Callable[[AuditEvent], None] | None = None,
    ) -> None:
        if type(binding) is not SystemdCredentialBinding:
            raise ValueError("systemd_credential_binding_invalid")
        self._binding = binding
        self._clock, self._monotonic = clock, monotonic
        self._audit_callback = audit_callback
        self._wall_start, self._mono_start = clock(), monotonic()
        if not _finite(self._wall_start) or not _finite(self._mono_start):
            raise ValueError("systemd_credential_clock_invalid")
        self._deadline = self._mono_start + min(
            binding.expires_at - self._wall_start, binding.expires_at - binding.issued_at
        )

    def _remaining(self) -> tuple[float, float, float]:
        wall, mono = self._clock(), self._monotonic()
        b = self._binding
        if (not _finite(wall) or not _finite(mono) or wall < self._wall_start
                or mono < self._mono_start or not b.issued_at <= wall < b.expires_at):
            raise _CredentialRejected(ResolveErrorCode.TTL_EXPIRED)
        remaining = min(b.expires_at - wall, self._deadline - mono)
        if remaining < 1:
            raise _CredentialRejected(ResolveErrorCode.TTL_EXPIRED)
        return wall, mono, remaining

    def resolve(self, reference: str, requester_id: str | None = None) -> ResolveResult:
        identifier = parse_systemd_credential_reference(reference)
        safe_reference = reference if identifier in self._binding.credential_ids else ""
        requester = (requester_id if type(requester_id) is str
                     and requester_id == self._binding.expected_requester else None)
        try:
            if identifier is None:
                raise _CredentialRejected(ResolveErrorCode.INVALID_REFERENCE)
            if identifier not in self._binding.credential_ids:
                raise _CredentialRejected(ResolveErrorCode.UNKNOWN_REFERENCE)
            if requester is None:
                raise _CredentialRejected(ResolveErrorCode.SESSION_INVALID)
            start_wall, start_mono, _ = self._remaining()
            if not _identity_matches(self._binding):
                raise _CredentialRejected(ResolveErrorCode.RESOLVER_UNAVAILABLE)
            value = _read_credential(self._binding, identifier)
            wall, mono, remaining = self._remaining()
            if wall < start_wall or mono < start_mono:
                raise _CredentialRejected(ResolveErrorCode.TTL_EXPIRED)
            if not _identity_matches(self._binding):
                raise _CredentialRejected(ResolveErrorCode.RESOLVER_UNAVAILABLE)
            return self._result(safe_reference, None, requester, int(remaining), value)
        except _CredentialRejected as exc:
            return self._result(safe_reference, exc.code, requester)
        except Exception:
            return self._result(safe_reference, ResolveErrorCode.RESOLVER_UNAVAILABLE, requester)

    def _result(self, reference: str, code: ResolveErrorCode | None,
                requester: str | None, ttl: int = 0, value: str | None = None) -> ResolveResult:
        """Audit pre-delivery validation; the returned result decides delivery."""
        event = AuditEvent(
            event_type="credential_pre_delivery_validation", reference=reference,
            reference_hash=hash_reference(reference), session_id=None,
            success=code is None, error_code=code.value if code else None,
            timestamp=datetime.now(timezone.utc).isoformat(),
            ttl_applied=ttl if code is None else None,
            requester_id=requester,
        )
        if self._audit_callback is not None:
            try:
                self._audit_callback(event)
            except Exception:
                code, ttl, value = ResolveErrorCode.RESOLVER_UNAVAILABLE, 0, None
        if code is None:
            try:
                _, _, remaining = self._remaining()
                if not _identity_matches(self._binding):
                    raise _CredentialRejected(ResolveErrorCode.RESOLVER_UNAVAILABLE)
                ttl = min(ttl, int(remaining))
            except _CredentialRejected as exc:
                code, ttl, value = exc.code, 0, None
            except Exception:
                code, ttl, value = ResolveErrorCode.RESOLVER_UNAVAILABLE, 0, None
        return ResolveResult(
            success=code is None, reference=reference, reference_hash=event.reference_hash,
            error_code=code, error_message=code.value if code else None,
            ttl_remaining=ttl, session_id=None, _secret_value=value,
        )


__all__ = ["SystemdCredentialBinding", "SystemdCredentialSecretResolver",
           "parse_systemd_credential_reference"]
