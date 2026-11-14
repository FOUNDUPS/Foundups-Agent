"""One-request socket service for the isolated RedDog signer boundary.

Slice: REDDOG_ISOLATED_SIGNER_SOCKET_SERVICE_ONCE_PHASE1

This module binds a caller-provided local socket path outside the repository,
serves exactly one bounded signer request through the existing signer protocol,
and closes the socket. It does not load private keys, resolve vault secrets,
spawn processes, execute shell commands, mutate repository files, enqueue
OpenClaw, dispatch Hermes, publish PRs, settle rewards, or re-index HoloIndex.

The signing backend and peer attestor are injected by the isolated signer
process owner. Defaults fail closed.
"""

from __future__ import annotations

import hashlib
import json
import socket
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Protocol

from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    DEFAULT_SIGNER_SOCKET_MAX_REQUEST_BYTES,
    FailClosedSignerBackend,
    IsolatedSignerBackend,
    SignerPeerAttestation,
    handle_reddog_isolated_signer_socket_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    RuntimeRejectCode,
    SigningResponse,
)


SIGNER_SOCKET_SERVICE_SERVED = "SIGNER_SOCKET_SERVICE_SERVED"
SIGNER_SOCKET_SERVICE_REJECT = "SIGNER_SOCKET_SERVICE_REJECT"

FAIL_SIGNER_SERVICE_SOCKET_PATH_MISSING = "FAIL_SIGNER_SERVICE_SOCKET_PATH_MISSING"
FAIL_SIGNER_SERVICE_SOCKET_PATH_RELATIVE = "FAIL_SIGNER_SERVICE_SOCKET_PATH_RELATIVE"
FAIL_SIGNER_SERVICE_SOCKET_PATH_INSIDE_REPO = "FAIL_SIGNER_SERVICE_SOCKET_PATH_INSIDE_REPO"
FAIL_SIGNER_SERVICE_SOCKET_DEVICE_PREFIX = "FAIL_SIGNER_SERVICE_SOCKET_DEVICE_PREFIX"
FAIL_SIGNER_SERVICE_SOCKET_PARENT_MISSING = "FAIL_SIGNER_SERVICE_SOCKET_PARENT_MISSING"
FAIL_SIGNER_SERVICE_SOCKET_PATH_EXISTS = "FAIL_SIGNER_SERVICE_SOCKET_PATH_EXISTS"
FAIL_SIGNER_SERVICE_TIMEOUT_INVALID = "FAIL_SIGNER_SERVICE_TIMEOUT_INVALID"
FAIL_SIGNER_SERVICE_REQUEST_LIMIT_INVALID = "FAIL_SIGNER_SERVICE_REQUEST_LIMIT_INVALID"
FAIL_SIGNER_SERVICE_RESPONSE_LIMIT_INVALID = "FAIL_SIGNER_SERVICE_RESPONSE_LIMIT_INVALID"
FAIL_SIGNER_SERVICE_SOCKET_UNAVAILABLE = "FAIL_SIGNER_SERVICE_SOCKET_UNAVAILABLE"
FAIL_SIGNER_SERVICE_RUNTIME_ERROR = "FAIL_SIGNER_SERVICE_RUNTIME_ERROR"
FAIL_SIGNER_SERVICE_RESPONSE_TOO_LARGE = "FAIL_SIGNER_SERVICE_RESPONSE_TOO_LARGE"

DEFAULT_SIGNER_SOCKET_SERVICE_TIMEOUT_S = 5.0
DEFAULT_SIGNER_SOCKET_SERVICE_MAX_RESPONSE_BYTES = 16384


class SignerSocketPeerAttestor(Protocol):
    """Injected peer attestor owned by the isolated signer process."""

    def attest(self, connection: socket.socket) -> SignerPeerAttestation:
        """Return peer identity from the socket boundary, or fail closed."""


class FailClosedSignerSocketPeerAttestor:
    """Default peer attestor: never attests a requester."""

    def attest(self, connection: socket.socket) -> SignerPeerAttestation:
        return SignerPeerAttestation(
            peer_principal_id="",
            transport="local_socket",
            credential_source="fail_closed",
            boundary_attested=False,
        )


@dataclass(frozen=True)
class IsolatedSignerSocketServiceResult:
    """Audit-safe result for one signer service request."""

    accepted: bool
    status: str
    rejection_reasons: tuple[str, ...]
    socket_path: Optional[str] = None
    request_bytes: int = 0
    response_bytes: int = 0
    response_digest: Optional[str] = None
    request_handled: bool = False
    socket_removed: bool = False
    no_private_key_loaded: bool = True
    no_vault_secret_resolved: bool = True
    no_signer_spawned: bool = True
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def serve_reddog_isolated_signer_socket_once(
    *,
    repo_root: Path | str,
    socket_path: Path | str | None,
    backend: Optional[IsolatedSignerBackend] = None,
    peer_attestor: Optional[SignerSocketPeerAttestor] = None,
    timeout_s: float = DEFAULT_SIGNER_SOCKET_SERVICE_TIMEOUT_S,
    max_request_bytes: int = DEFAULT_SIGNER_SOCKET_MAX_REQUEST_BYTES,
    max_response_bytes: int = DEFAULT_SIGNER_SOCKET_SERVICE_MAX_RESPONSE_BYTES,
    ready_callback: Optional[Callable[[], None]] = None,
) -> IsolatedSignerSocketServiceResult:
    """Serve exactly one signer request on a guarded local socket."""

    resolved, reasons = _resolve_socket_path(repo_root=repo_root, socket_path=socket_path)
    if reasons:
        return _reject(*reasons)
    assert resolved is not None
    limit_reasons = _validate_limits(timeout_s, max_request_bytes, max_response_bytes)
    if limit_reasons:
        return _reject(*limit_reasons, socket_path=str(resolved))
    if not hasattr(socket, "AF_UNIX"):
        return _reject(FAIL_SIGNER_SERVICE_SOCKET_UNAVAILABLE, socket_path=str(resolved))

    server: Optional[socket.socket] = None
    socket_removed = False
    try:
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.settimeout(float(timeout_s))
        server.bind(str(resolved))
        server.listen(1)
        if ready_callback:
            ready_callback()
        connection, _ = server.accept()
        with connection:
            connection.settimeout(float(timeout_s))
            request_bytes = _read_bounded(connection, max_request_bytes)
            peer = (peer_attestor or FailClosedSignerSocketPeerAttestor()).attest(connection)
            response = handle_reddog_isolated_signer_socket_request(
                request_bytes,
                peer=peer,
                backend=backend or FailClosedSignerBackend(),
                max_request_bytes=max_request_bytes,
            )
            if len(response) > max_response_bytes:
                response = _response_bytes(RuntimeRejectCode.MALFORMED_REQUEST)
                if len(response) > max_response_bytes:
                    return _reject(FAIL_SIGNER_SERVICE_RESPONSE_TOO_LARGE, socket_path=str(resolved))
            connection.sendall(response)
        server.close()
        server = None
        socket_removed = _cleanup_socket(resolved)
        return IsolatedSignerSocketServiceResult(
            accepted=True,
            status=SIGNER_SOCKET_SERVICE_SERVED,
            rejection_reasons=(),
            socket_path=str(resolved),
            request_bytes=len(request_bytes),
            response_bytes=len(response),
            response_digest=_digest(response),
            request_handled=True,
            socket_removed=socket_removed,
        )
    except Exception:
        return _reject(FAIL_SIGNER_SERVICE_RUNTIME_ERROR, socket_path=str(resolved))
    finally:
        if server is not None:
            server.close()
        if not socket_removed:
            _cleanup_socket(resolved)


def _resolve_socket_path(
    *, repo_root: Path | str, socket_path: Path | str | None
) -> tuple[Optional[Path], tuple[str, ...]]:
    root = Path(repo_root).resolve()
    if not socket_path:
        return None, (FAIL_SIGNER_SERVICE_SOCKET_PATH_MISSING,)
    path_text = str(socket_path)
    if "\x00" in path_text or path_text.startswith("\\\\?\\") or path_text.startswith("//?/"):
        return None, (FAIL_SIGNER_SERVICE_SOCKET_DEVICE_PREFIX,)
    path = Path(socket_path)
    if not path.is_absolute():
        return None, (FAIL_SIGNER_SERVICE_SOCKET_PATH_RELATIVE,)
    resolved = path.resolve()
    if _is_inside(resolved, root):
        return None, (FAIL_SIGNER_SERVICE_SOCKET_PATH_INSIDE_REPO,)
    if not resolved.parent.exists() or not resolved.parent.is_dir():
        return None, (FAIL_SIGNER_SERVICE_SOCKET_PARENT_MISSING,)
    if resolved.exists():
        return None, (FAIL_SIGNER_SERVICE_SOCKET_PATH_EXISTS,)
    return resolved, ()


def _validate_limits(
    timeout_s: float, max_request_bytes: int, max_response_bytes: int
) -> tuple[str, ...]:
    reasons: list[str] = []
    if timeout_s <= 0 or timeout_s > 30:
        reasons.append(FAIL_SIGNER_SERVICE_TIMEOUT_INVALID)
    if max_request_bytes < 1024 or max_request_bytes > 262144:
        reasons.append(FAIL_SIGNER_SERVICE_REQUEST_LIMIT_INVALID)
    if max_response_bytes < 1024 or max_response_bytes > 262144:
        reasons.append(FAIL_SIGNER_SERVICE_RESPONSE_LIMIT_INVALID)
    return tuple(reasons)


def _read_bounded(connection: socket.socket, max_request_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = connection.recv(4096)
        if not chunk:
            break
        total += len(chunk)
        if total > max_request_bytes:
            raise ValueError(FAIL_SIGNER_SERVICE_REQUEST_LIMIT_INVALID)
        chunks.append(chunk)
    return b"".join(chunks)


def _response_bytes(code: str) -> bytes:
    response = SigningResponse(
        accepted=False,
        rejection_code=str(code),
        no_secret_material_returned=True,
    )
    return (
        json.dumps(response.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _cleanup_socket(path: Path) -> bool:
    try:
        path.unlink(missing_ok=True)
        return not path.exists()
    except Exception:
        return False


def _reject(*reasons: str, socket_path: Optional[str] = None) -> IsolatedSignerSocketServiceResult:
    return IsolatedSignerSocketServiceResult(
        accepted=False,
        status=SIGNER_SOCKET_SERVICE_REJECT,
        rejection_reasons=tuple(dict.fromkeys(reason for reason in reasons if reason)),
        socket_path=socket_path,
    )


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


__all__ = [
    "DEFAULT_SIGNER_SOCKET_SERVICE_MAX_RESPONSE_BYTES",
    "DEFAULT_SIGNER_SOCKET_SERVICE_TIMEOUT_S",
    "FAIL_SIGNER_SERVICE_REQUEST_LIMIT_INVALID",
    "FAIL_SIGNER_SERVICE_RESPONSE_LIMIT_INVALID",
    "FAIL_SIGNER_SERVICE_RESPONSE_TOO_LARGE",
    "FAIL_SIGNER_SERVICE_RUNTIME_ERROR",
    "FAIL_SIGNER_SERVICE_SOCKET_DEVICE_PREFIX",
    "FAIL_SIGNER_SERVICE_SOCKET_PARENT_MISSING",
    "FAIL_SIGNER_SERVICE_SOCKET_PATH_EXISTS",
    "FAIL_SIGNER_SERVICE_SOCKET_PATH_INSIDE_REPO",
    "FAIL_SIGNER_SERVICE_SOCKET_PATH_MISSING",
    "FAIL_SIGNER_SERVICE_SOCKET_PATH_RELATIVE",
    "FAIL_SIGNER_SERVICE_SOCKET_UNAVAILABLE",
    "FAIL_SIGNER_SERVICE_TIMEOUT_INVALID",
    "FailClosedSignerSocketPeerAttestor",
    "IsolatedSignerSocketServiceResult",
    "SIGNER_SOCKET_SERVICE_REJECT",
    "SIGNER_SOCKET_SERVICE_SERVED",
    "SignerSocketPeerAttestor",
    "serve_reddog_isolated_signer_socket_once",
]
