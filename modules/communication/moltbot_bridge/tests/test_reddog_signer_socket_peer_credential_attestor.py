"""Tests for REDDOG_SIGNER_SOCKET_PEER_CREDENTIAL_ATTESTOR_PHASE1."""

from __future__ import annotations

import ast
import struct
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_signer_socket_peer_credential_attestor as attestor_module,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    FAIL_PEER_CREDENTIAL_GID_NOT_ALLOWED,
    FAIL_PEER_CREDENTIAL_MALFORMED,
    FAIL_PEER_CREDENTIAL_POLICY_INVALID,
    FAIL_PEER_CREDENTIAL_UID_NOT_ALLOWED,
    FAIL_PEER_CREDENTIAL_UNAVAILABLE,
    KernelPeerCredentialAttestor,
    PEER_CREDENTIAL_SOURCE_GETPEEREID,
    PEER_CREDENTIAL_SOURCE_SO_PEERCRED,
    PeerCredentialPolicy,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_signer_socket_peer_credential_attestor.py"
)


class FakePeerCredSocket:
    def __init__(self, *, pid: int = 123, uid: int = 1001, gid: int = 1002) -> None:
        self.pid = pid
        self.uid = uid
        self.gid = gid
        self.calls: list[tuple[int, int, int]] = []

    def getsockopt(self, level: int, optname: int, buflen: int) -> bytes:
        self.calls.append((level, optname, buflen))
        return struct.pack("3i", self.pid, self.uid, self.gid)


class ShortPeerCredSocket:
    def getsockopt(self, level: int, optname: int, buflen: int) -> bytes:
        return b"bad"


class RaisingPeerCredSocket:
    def getsockopt(self, level: int, optname: int, buflen: int) -> bytes:
        raise OSError("unavailable")


class GetPeerEidSocket:
    def __init__(self, *, uid: int = 1001, gid: int = 1002, fail: bool = False) -> None:
        self.uid = uid
        self.gid = gid
        self.fail = fail

    def getpeereid(self) -> tuple[int, int]:
        if self.fail:
            raise OSError("unavailable")
        return (self.uid, self.gid)


@pytest.fixture(autouse=True)
def restore_so_peercred(monkeypatch: pytest.MonkeyPatch):
    original = attestor_module._SO_PEERCRED
    yield
    monkeypatch.setattr(attestor_module, "_SO_PEERCRED", original)


def _policy(**overrides: object) -> PeerCredentialPolicy:
    values = {
        "uid_to_principal": {1001: "github:mjtrout"},
        "allowed_gids": (1002,),
        "transport": "unix_socket",
        "credential_source_prefix": "kernel_peer_credential",
    }
    values.update(overrides)
    return PeerCredentialPolicy(**values)


def test_so_peercred_success_maps_uid_to_principal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(attestor_module, "_SO_PEERCRED", 17)
    fake = FakePeerCredSocket()

    result = KernelPeerCredentialAttestor(_policy()).attest(fake)

    assert result.boundary_attested is True
    assert result.peer_principal_id == "github:mjtrout"
    assert PEER_CREDENTIAL_SOURCE_SO_PEERCRED in result.credential_source
    assert "uid=1001" in result.credential_source
    assert "gid=1002" in result.credential_source
    assert fake.calls == [(attestor_module.socket.SOL_SOCKET, 17, struct.calcsize("3i"))]


def test_getpeereid_fallback_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(attestor_module, "_SO_PEERCRED", None)

    result = KernelPeerCredentialAttestor(_policy()).attest(GetPeerEidSocket())

    assert result.boundary_attested is True
    assert result.peer_principal_id == "github:mjtrout"
    assert PEER_CREDENTIAL_SOURCE_GETPEEREID in result.credential_source
    assert "pid=0" in result.credential_source


def test_unsupported_platform_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(attestor_module, "_SO_PEERCRED", None)

    result = KernelPeerCredentialAttestor(_policy()).attest(object())

    assert result.boundary_attested is False
    assert result.peer_principal_id == ""
    assert result.credential_source == FAIL_PEER_CREDENTIAL_UNAVAILABLE


def test_malformed_or_exception_credentials_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(attestor_module, "_SO_PEERCRED", 17)

    short = KernelPeerCredentialAttestor(_policy()).attest(ShortPeerCredSocket())
    raised = KernelPeerCredentialAttestor(_policy()).attest(RaisingPeerCredSocket())
    negative = KernelPeerCredentialAttestor(_policy()).attest(FakePeerCredSocket(uid=-1))

    assert short.boundary_attested is False
    assert short.credential_source == FAIL_PEER_CREDENTIAL_UNAVAILABLE
    assert raised.boundary_attested is False
    assert raised.credential_source == FAIL_PEER_CREDENTIAL_UNAVAILABLE
    assert negative.boundary_attested is False
    assert negative.credential_source == FAIL_PEER_CREDENTIAL_MALFORMED


def test_unmapped_uid_and_wrong_gid_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(attestor_module, "_SO_PEERCRED", 17)

    uid = KernelPeerCredentialAttestor(_policy()).attest(FakePeerCredSocket(uid=2000))
    gid = KernelPeerCredentialAttestor(_policy()).attest(FakePeerCredSocket(gid=3000))

    assert uid.boundary_attested is False
    assert uid.credential_source == FAIL_PEER_CREDENTIAL_UID_NOT_ALLOWED
    assert gid.boundary_attested is False
    assert gid.credential_source == FAIL_PEER_CREDENTIAL_GID_NOT_ALLOWED


def test_policy_must_be_complete_ascii_and_non_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(attestor_module, "_SO_PEERCRED", 17)
    cases = (
        PeerCredentialPolicy({}),
        PeerCredentialPolicy({1001: ""}),
        PeerCredentialPolicy({1001: "github:\u2603"}),
        PeerCredentialPolicy({-1: "github:mjtrout"}),
        PeerCredentialPolicy({1001: "github:mjtrout"}, allowed_gids=(-1,)),
        PeerCredentialPolicy({1001: "github:mjtrout"}, transport="sock-\u2603"),
    )

    for policy in cases:
        result = KernelPeerCredentialAttestor(policy).attest(FakePeerCredSocket())
        assert result.boundary_attested is False
        assert result.credential_source == FAIL_PEER_CREDENTIAL_POLICY_INVALID


def test_attestor_has_no_request_body_input() -> None:
    import inspect

    signature = inspect.signature(KernelPeerCredentialAttestor.attest)
    assert list(signature.parameters) == ["self", "connection"]


def test_module_has_no_shell_file_repo_openclaw_hermes_or_holoindex_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "os",
        "subprocess",
        "pwd",
        "grp",
        "psutil",
        "requests",
        "urllib",
        "http",
        "git",
        "holo_index",
    }
    banned_name_calls = {"eval", "exec", "compile", "__import__", "open"}
    banned_attrs = {
        "getenv",
        "environ",
        "system",
        "popen",
        "run",
        "Popen",
        "check_call",
        "check_output",
        "spawn",
        "read_text",
        "read_bytes",
        "write_text",
        "write_bytes",
    }
    banned_name_fragments = ("openclaw", "hermes", "worktree", "holoindex")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
            assert not any(fragment in node.module.lower() for fragment in banned_name_fragments)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_name_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs
