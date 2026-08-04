"""Security tests for the signer pre-key process-isolation gate."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from modules.communication.moltbot_bridge.src.reddog_signer_process_isolation_gate import (
    FAIL_ISOLATION_BOUNDARY,
    enforce_signer_process_isolation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    PeerCredentialPolicy,
)


@dataclass
class FakeIsolationBackend:
    platform_name: str = "linux"
    uid: int = 1201
    gid: int = 1201
    ptrace_scope: str = "1\n"
    cap_eff: str = "0000000000000000"
    tracer_pid: int = 0
    core_ok: bool = True
    dumpable_ok: bool = True
    environment_ok: bool = True

    def platform(self) -> str:
        return self.platform_name

    def current_uid(self) -> int:
        return self.uid

    def current_gid(self) -> int:
        return self.gid

    def read_text(self, path: str) -> str:
        if path.endswith("ptrace_scope"):
            return self.ptrace_scope
        return (
            f"CapEff:\t{self.cap_eff}\n"
            f"CapPrm:\t{self.cap_eff}\n"
            f"CapAmb:\t{self.cap_eff}\n"
            f"TracerPid:\t{self.tracer_pid}\n"
        )

    def disable_core_dumps(self) -> bool:
        return self.core_ok

    def disable_dumpable(self) -> bool:
        return self.dumpable_ok

    def clear_environment(self) -> bool:
        return self.environment_ok


def _policy() -> PeerCredentialPolicy:
    return PeerCredentialPolicy({1001: "runtime-principal"}, allowed_gids=(1002,))


def test_linux_distinct_principal_hardening_passes() -> None:
    result = enforce_signer_process_isolation(
        _policy(),
        expected_signer_uid=1201,
        expected_signer_gid=1201,
        backend=FakeIsolationBackend(),
    )

    assert result.accepted is True
    assert result.signer_uid == 1201
    assert result.distinct_consumer_uid is True
    assert result.ptrace_scope_enforced is True
    assert result.cap_sys_ptrace_absent is True
    assert result.tracer_absent is True
    assert result.core_dumps_disabled is True
    assert result.dumpable_disabled is True
    assert result.environment_cleared is True


@pytest.mark.parametrize(
    "backend",
    (
        FakeIsolationBackend(platform_name="win32"),
        FakeIsolationBackend(uid=0),
        FakeIsolationBackend(uid=1001),
        FakeIsolationBackend(ptrace_scope="0\n"),
        FakeIsolationBackend(cap_eff=f"{1 << 19:x}"),
        FakeIsolationBackend(tracer_pid=22),
        FakeIsolationBackend(core_ok=False),
        FakeIsolationBackend(dumpable_ok=False),
        FakeIsolationBackend(environment_ok=False),
    ),
)
def test_missing_isolation_invariant_fails_closed(backend: FakeIsolationBackend) -> None:
    result = enforce_signer_process_isolation(
        _policy(),
        expected_signer_uid=1201,
        expected_signer_gid=1201,
        backend=backend,
    )

    assert result.accepted is False
    assert result.rejection_reasons == (FAIL_ISOLATION_BOUNDARY,)


def test_malformed_proc_evidence_fails_closed() -> None:
    result = enforce_signer_process_isolation(
        _policy(),
        expected_signer_uid=1201,
        expected_signer_gid=1201,
        backend=FakeIsolationBackend(ptrace_scope="unknown"),
    )

    assert result.accepted is False


@pytest.mark.parametrize(
    ("uid", "gid"),
    ((1202, 1201), (1201, 1202), (0, 1201), (1201, 0)),
)
def test_process_must_match_exact_root_owned_signer_identity(
    uid: int, gid: int
) -> None:
    result = enforce_signer_process_isolation(
        _policy(),
        expected_signer_uid=uid,
        expected_signer_gid=gid,
        backend=FakeIsolationBackend(),
    )

    assert result.accepted is False
