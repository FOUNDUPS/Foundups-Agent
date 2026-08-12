"""Startup boundary tests for the root verified-outcome authority service."""

from __future__ import annotations

import json
from types import SimpleNamespace

from modules.communication.moltbot_bridge.src import (
    foundup_verified_outcome_root_authority_service_entrypoint as entrypoint,
    foundup_verified_outcome_root_authority_socket_service as socket_service,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_socket_service import (
    RootAuthoritySocketServiceResult,
)
class _State:
    pass


class _Connection:
    def __init__(self, *, fail_read: bool) -> None:
        self.fail_read = fail_read
        self.sent: list[bytes] = []

    def settimeout(self, _value) -> None:
        return None

    def recv(self, _size: int) -> bytes:
        if self.fail_read:
            raise OSError("malformed-client")
        return b""

    def sendall(self, value: bytes) -> None:
        self.sent.append(value)


def _dependencies():
    revocation_authority = object()
    return SimpleNamespace(
        state=_State(),
        snapshot_supplier=lambda: "snapshot",
        socket_path="/run/reddog/outcome-authority.sock",
        signer_uid=1001,
        signer_gid=1002,
        signer_principal_id="reddog-e0-signer",
        revocation_authority=revocation_authority,
    )


def test_entrypoint_builds_single_signer_peer_policy_and_serves(
    monkeypatch,
) -> None:
    captured = {}
    monkeypatch.setattr(
        entrypoint,
        "load_root_authority_service_dependencies",
        lambda *_args, **_kwargs: _dependencies(),
    )

    def serve(**values):
        captured.update(values)
        return RootAuthoritySocketServiceResult(
            accepted=True,
            status="ROOT_AUTHORITY_SERVICE_ACCEPT",
            rejection_reasons=(),
            requests_handled=1,
        )

    monkeypatch.setattr(entrypoint, "serve_root_authority_bounded", serve)
    emitted: list[str] = []
    result = entrypoint.run_entrypoint(
        [
            "--repo-root",
            "O:/Foundups-Agent",
            "--owner-authority-config",
            "C:/ProgramData/Foundups/reddog-owner.json",
            "--max-requests",
            "7",
        ],
        emit=emitted.append,
    )

    policy = captured["peer_attestor"].policy
    assert result == 0
    assert policy.uid_to_principal == {1001: "reddog-e0-signer"}
    assert policy.allowed_gids == (1002,)
    assert captured["max_requests"] == 7
    assert captured["revocation_authority"] is not None
    assert json.loads(emitted[0])["accepted"] is True


def test_runtime_entrypoint_has_no_state_initialization_flag() -> None:
    parser = entrypoint.build_parser()
    options = {
        option
        for action in parser._actions
        for option in action.option_strings
    }
    assert "--initialize-state" not in options
    assert not hasattr(entrypoint, "initialize_root_authority_state")


def test_startup_failure_is_fail_closed_and_does_not_echo_exception(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        entrypoint,
        "load_root_authority_service_dependencies",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("secret-shaped attacker detail")
        ),
    )
    emitted: list[str] = []
    result = entrypoint.run_entrypoint(
        [
            "--repo-root",
            "O:/Foundups-Agent",
            "--owner-authority-config",
            "C:/ProgramData/Foundups/reddog-owner.json",
        ],
        emit=emitted.append,
    )
    payload = json.loads(emitted[0])
    assert result == 2
    assert payload["accepted"] is False
    assert payload["rejection_reasons"] == [
        "root_authority_service_startup_rejected"
    ]
    assert "secret-shaped" not in emitted[0]


def test_unauthorized_client_is_rejected_before_request_read() -> None:
    events: list[str] = []

    class RejectingAttestor:
        def attest_identity(self, _connection):
            events.append("attest")
            return None

    connection = _Connection(fail_read=True)
    socket_service._serve_connection(
        connection,
        timeout_s=1.0,
        state=_State(),
        snapshot_supplier=lambda: "snapshot",
        peer_attestor=RejectingAttestor(),
    )
    assert events == ["attest"]
    assert connection.sent == [b'{"status":"REJECT"}\n']


def test_malformed_authorized_client_does_not_prevent_next_client_handling(
    monkeypatch,
) -> None:
    class AcceptingAttestor:
        def attest_identity(self, _connection):
            return object()

    monkeypatch.setattr(
        socket_service,
        "handle_root_authority_request",
        lambda *_args, **_kwargs: b'{"status":"ACCEPT"}\n',
    )
    attestor = AcceptingAttestor()
    first = _Connection(fail_read=True)
    second = _Connection(fail_read=False)
    for connection in (first, second):
        socket_service._serve_connection(
            connection,
            timeout_s=1.0,
            state=_State(),
            snapshot_supplier=lambda: "snapshot",
            peer_attestor=attestor,
        )
    assert first.sent == [b'{"status":"REJECT"}\n']
    assert second.sent == [b'{"status":"ACCEPT"}\n']
