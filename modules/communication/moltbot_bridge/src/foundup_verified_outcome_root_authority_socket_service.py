"""Bounded root-owned Unix service for verified-outcome authority."""

from __future__ import annotations

import os
import socket
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_protocol import (
    MAX_MESSAGE_BYTES,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service import (
    SnapshotSupplier,
    handle_root_authority_request,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_state import (
    RootVerifiedOutcomeAuthorityState,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import (
    _bound_server,
    _cleanup_socket,
    _read_bounded,
    _resolve_socket_path,
    _socket_identity,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    KernelPeerCredentialAttestor,
)


SERVICE_ACCEPT = "ROOT_AUTHORITY_SERVICE_ACCEPT"
SERVICE_REJECT = "ROOT_AUTHORITY_SERVICE_REJECT"


@dataclass(frozen=True)
class RootAuthoritySocketServiceResult:
    accepted: bool
    status: str
    rejection_reasons: tuple[str, ...]
    socket_path: str | None = None
    requests_handled: int = 0
    socket_removed: bool = False
    no_signing_key_loaded: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def serve_root_authority_bounded(
    *,
    repo_root: Path | str,
    socket_path: Path | str,
    signer_gid: int,
    state: RootVerifiedOutcomeAuthorityState,
    snapshot_supplier: SnapshotSupplier,
    peer_attestor: KernelPeerCredentialAttestor,
    max_requests: int = 128,
    timeout_s: float = 5.0,
) -> RootAuthoritySocketServiceResult:
    """Serve bounded authority requests as root; never load signing material."""

    resolved, reasons = _resolve_socket_path(
        repo_root=repo_root, socket_path=socket_path
    )
    if reasons:
        return _reject(*reasons)
    if (
        os.name != "posix"
        or not hasattr(os, "geteuid")
        or os.geteuid() != 0
        or type(signer_gid) is not int
        or signer_gid <= 0
        or type(max_requests) is not int
        or not 1 <= max_requests <= 1024
        or not 0 < timeout_s <= 30
    ):
        return _reject("root_authority_service_principal_invalid")
    if not isinstance(state, RootVerifiedOutcomeAuthorityState) or not isinstance(
        peer_attestor, KernelPeerCredentialAttestor
    ):
        return _reject("root_authority_service_dependency_invalid")
    assert resolved is not None
    return _serve_validated(
        resolved=resolved,
        signer_gid=signer_gid,
        state=state,
        snapshot_supplier=snapshot_supplier,
        peer_attestor=peer_attestor,
        max_requests=max_requests,
        timeout_s=timeout_s,
    )


def _serve_validated(
    *,
    resolved: Path,
    signer_gid: int,
    state: RootVerifiedOutcomeAuthorityState,
    snapshot_supplier: SnapshotSupplier,
    peer_attestor: KernelPeerCredentialAttestor,
    max_requests: int,
    timeout_s: float,
) -> RootAuthoritySocketServiceResult:
    server: socket.socket | None = None
    identity = None
    handled = 0
    removed = False
    try:
        server, identity = _bound_server(resolved, timeout_s)
        os.chown(resolved, 0, signer_gid, follow_symlinks=False)
        os.chmod(resolved, 0o660, follow_symlinks=False)
        _require_socket_identity(resolved, signer_gid)
        identity = _socket_identity(resolved)
        if identity is None:
            raise ValueError("root_authority_socket_identity_invalid")
        for _ in range(max_requests):
            connection, _address = server.accept()
            with connection:
                _serve_connection(
                    connection,
                    timeout_s=timeout_s,
                    state=state,
                    snapshot_supplier=snapshot_supplier,
                    peer_attestor=peer_attestor,
                )
                handled += 1
        server.close()
        server = None
        removed = _cleanup_socket(resolved, identity)
        return RootAuthoritySocketServiceResult(
            accepted=True,
            status=SERVICE_ACCEPT,
            rejection_reasons=(),
            socket_path=str(resolved),
            requests_handled=handled,
            socket_removed=removed,
        )
    except Exception:
        return _reject(
            "root_authority_service_runtime_error",
            socket_path=str(resolved),
            requests_handled=handled,
        )
    finally:
        if server is not None:
            server.close()
        if resolved is not None and identity is not None and not removed:
            _cleanup_socket(resolved, identity)


def _serve_connection(
    connection: socket.socket,
    *,
    timeout_s: float,
    state: RootVerifiedOutcomeAuthorityState,
    snapshot_supplier: SnapshotSupplier,
    peer_attestor: KernelPeerCredentialAttestor,
) -> None:
    try:
        peer = peer_attestor.attest_identity(connection)
        if peer is None:
            connection.sendall(b'{"status":"REJECT"}\n')
            return
        connection.settimeout(timeout_s)
        raw = _read_bounded(connection, MAX_MESSAGE_BYTES)
        response = handle_root_authority_request(
            raw,
            peer=peer,
            state=state,
            snapshot_supplier=snapshot_supplier,
            now_epoch=_now_epoch(),
        )
        connection.sendall(response)
    except Exception:
        try:
            connection.sendall(b'{"status":"REJECT"}\n')
        except Exception:
            return


def _require_socket_identity(path: Path, signer_gid: int) -> None:
    metadata = path.lstat()
    if (
        path.is_symlink()
        or not stat.S_ISSOCK(metadata.st_mode)
        or metadata.st_uid != 0
        or metadata.st_gid != signer_gid
        or stat.S_IMODE(metadata.st_mode) != 0o660
    ):
        raise ValueError("root_authority_socket_identity_invalid")


def _now_epoch() -> int:
    import time

    return int(time.time())


def _reject(
    *reasons: str,
    socket_path: str | None = None,
    requests_handled: int = 0,
) -> RootAuthoritySocketServiceResult:
    return RootAuthoritySocketServiceResult(
        accepted=False,
        status=SERVICE_REJECT,
        rejection_reasons=tuple(dict.fromkeys(reasons)),
        socket_path=socket_path,
        requests_handled=requests_handled,
    )


__all__ = [
    "RootAuthoritySocketServiceResult",
    "SERVICE_ACCEPT",
    "SERVICE_REJECT",
    "serve_root_authority_bounded",
]
