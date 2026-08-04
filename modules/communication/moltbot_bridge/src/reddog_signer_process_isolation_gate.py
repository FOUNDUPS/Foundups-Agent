"""Executable E0 isolation gate applied before signer key resolution."""

from __future__ import annotations

import ctypes
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    PeerCredentialPolicy,
)


FAIL_ISOLATION_BOUNDARY = "FAIL_SIGNER_PROCESS_ISOLATION_BOUNDARY"
_CAP_SYS_PTRACE = 19
_PR_GET_DUMPABLE = 3
_PR_SET_DUMPABLE = 4


class SignerProcessIsolationBackend(Protocol):
    def platform(self) -> str: ...
    def current_uid(self) -> int: ...
    def current_gid(self) -> int: ...
    def read_text(self, path: str) -> str: ...
    def disable_core_dumps(self) -> bool: ...
    def disable_dumpable(self) -> bool: ...
    def clear_environment(self) -> bool: ...


@dataclass(frozen=True)
class SignerProcessIsolationReceipt:
    accepted: bool
    rejection_reasons: tuple[str, ...]
    signer_uid: int | None
    signer_gid: int | None
    distinct_consumer_uid: bool
    ptrace_scope_enforced: bool
    cap_sys_ptrace_absent: bool
    tracer_absent: bool
    core_dumps_disabled: bool
    dumpable_disabled: bool
    environment_cleared: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class LinuxSignerProcessIsolationBackend:
    def platform(self) -> str:
        return sys.platform

    def current_uid(self) -> int:
        return os.geteuid()

    def current_gid(self) -> int:
        return os.getegid()

    def read_text(self, path: str) -> str:
        return Path(path).read_text(encoding="ascii")

    def disable_core_dumps(self) -> bool:
        import resource

        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        return resource.getrlimit(resource.RLIMIT_CORE) == (0, 0)

    def disable_dumpable(self) -> bool:
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(_PR_SET_DUMPABLE, 0, 0, 0, 0) != 0:
            return False
        return libc.prctl(_PR_GET_DUMPABLE, 0, 0, 0, 0) == 0

    def clear_environment(self) -> bool:
        os.environ.clear()
        return not os.environ


def enforce_signer_process_isolation(
    policy: PeerCredentialPolicy,
    *,
    backend: SignerProcessIsolationBackend | None = None,
) -> SignerProcessIsolationReceipt:
    """Apply and verify the signer boundary before any key resolver is called."""

    source = backend or LinuxSignerProcessIsolationBackend()
    try:
        uid, gid = source.current_uid(), source.current_gid()
        identity_ok = _identity_valid(source.platform(), policy, uid, gid)
        ptrace_ok = _ptrace_scope(source) >= 1
        capability_ok, tracer_ok = _process_status_safe(source)
        if not identity_ok or not ptrace_ok or not capability_ok or not tracer_ok:
            return _reject(uid, gid)
        core_ok = source.disable_core_dumps() is True
        dumpable_ok = source.disable_dumpable() is True
        environment_ok = source.clear_environment() is True
        if not core_ok or not dumpable_ok or not environment_ok:
            return _reject(uid, gid)
    except Exception:
        return _reject(None, None)
    return SignerProcessIsolationReceipt(
        accepted=True,
        rejection_reasons=(),
        signer_uid=uid,
        signer_gid=gid,
        distinct_consumer_uid=True,
        ptrace_scope_enforced=True,
        cap_sys_ptrace_absent=True,
        tracer_absent=True,
        core_dumps_disabled=True,
        dumpable_disabled=True,
        environment_cleared=True,
    )


def _identity_valid(
    platform: str, policy: PeerCredentialPolicy, uid: int, gid: int
) -> bool:
    return (
        str(platform).startswith("linux")
        and isinstance(policy, PeerCredentialPolicy)
        and type(uid) is int
        and uid > 0
        and type(gid) is int
        and gid > 0
        and uid not in policy.uid_to_principal
    )


def _ptrace_scope(source: SignerProcessIsolationBackend) -> int:
    value = source.read_text("/proc/sys/kernel/yama/ptrace_scope").strip()
    return int(value) if value.isdigit() else -1


def _process_status_safe(
    source: SignerProcessIsolationBackend,
) -> tuple[bool, bool]:
    status = source.read_text("/proc/self/status")
    fields = dict(
        line.partition(":")[::2]
        for line in status.splitlines()
        if ":" in line
    )
    capabilities = tuple(fields.get(name, "").strip() for name in ("CapEff", "CapPrm", "CapAmb"))
    if any(not value for value in capabilities):
        return False, False
    cap_absent = not any(int(value, 16) & (1 << _CAP_SYS_PTRACE) for value in capabilities)
    return cap_absent, fields.get("TracerPid", "").strip() == "0"


def _reject(uid: int | None, gid: int | None) -> SignerProcessIsolationReceipt:
    return SignerProcessIsolationReceipt(
        accepted=False,
        rejection_reasons=(FAIL_ISOLATION_BOUNDARY,),
        signer_uid=uid,
        signer_gid=gid,
        distinct_consumer_uid=False,
        ptrace_scope_enforced=False,
        cap_sys_ptrace_absent=False,
        tracer_absent=False,
        core_dumps_disabled=False,
        dumpable_disabled=False,
        environment_cleared=False,
    )


__all__ = [
    "FAIL_ISOLATION_BOUNDARY",
    "LinuxSignerProcessIsolationBackend",
    "SignerProcessIsolationBackend",
    "SignerProcessIsolationReceipt",
    "enforce_signer_process_isolation",
]
