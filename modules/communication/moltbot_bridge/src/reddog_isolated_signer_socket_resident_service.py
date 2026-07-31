"""Bounded resident service for the isolated RedDog signer socket.

Slice: REDDOG_ISOLATED_SIGNER_SOCKET_RESIDENT_SERVICE_PHASE1

This module keeps the signer boundary alive for a bounded number of local
socket requests. The signer backend and peer attestor remain injected by the
isolated signer owner; this module does not load private keys, resolve vault
secrets, spawn processes, execute shell commands, mutate repository files,
enqueue OpenClaw, dispatch Hermes, publish PRs, settle rewards, or re-index
HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import socket
import stat
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional

from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    DEFAULT_SIGNER_SOCKET_MAX_REQUEST_BYTES,
    FailClosedSignerBackend,
    IsolatedSignerBackend,
    handle_reddog_isolated_signer_socket_request,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_service import (
    DEFAULT_SIGNER_SOCKET_SERVICE_MAX_RESPONSE_BYTES,
    DEFAULT_SIGNER_SOCKET_SERVICE_TIMEOUT_S,
    FAIL_SIGNER_SERVICE_REQUEST_LIMIT_INVALID,
    FAIL_SIGNER_SERVICE_RESPONSE_LIMIT_INVALID,
    FAIL_SIGNER_SERVICE_RUNTIME_ERROR,
    FAIL_SIGNER_SERVICE_SOCKET_DEVICE_PREFIX,
    FAIL_SIGNER_SERVICE_SOCKET_PARENT_MISSING,
    FAIL_SIGNER_SERVICE_SOCKET_PATH_EXISTS,
    FAIL_SIGNER_SERVICE_SOCKET_PATH_INSIDE_REPO,
    FAIL_SIGNER_SERVICE_SOCKET_PATH_MISSING,
    FAIL_SIGNER_SERVICE_SOCKET_PATH_RELATIVE,
    FAIL_SIGNER_SERVICE_SOCKET_UNAVAILABLE,
    FAIL_SIGNER_SERVICE_TIMEOUT_INVALID,
    FailClosedSignerSocketPeerAttestor,
    SignerSocketPeerAttestor,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    RuntimeRejectCode,
    SigningResponse,
)


SIGNER_SOCKET_RESIDENT_SERVICE_SERVED = "SIGNER_SOCKET_RESIDENT_SERVICE_SERVED"
SIGNER_SOCKET_RESIDENT_SERVICE_REJECT = "SIGNER_SOCKET_RESIDENT_SERVICE_REJECT"

FAIL_SIGNER_RESIDENT_SERVICE_MAX_REQUESTS_INVALID = (
    "FAIL_SIGNER_RESIDENT_SERVICE_MAX_REQUESTS_INVALID"
)
FAIL_SIGNER_SERVICE_SOCKET_PARENT_UNSAFE = (
    "FAIL_SIGNER_SERVICE_SOCKET_PARENT_UNSAFE"
)

DEFAULT_SIGNER_SOCKET_RESIDENT_MAX_REQUESTS = 16


@dataclass(frozen=True)
class _BoundSocketIdentity:
    device: int
    inode: int
    uid: int
    gid: int


@dataclass(frozen=True)
class IsolatedSignerSocketResidentServiceResult:
    """Audit-safe result for a bounded signer socket service run."""

    accepted: bool
    status: str
    rejection_reasons: tuple[str, ...]
    socket_path: Optional[str] = None
    requests_handled: int = 0
    response_digests: tuple[str, ...] = field(default_factory=tuple)
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

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def serve_reddog_isolated_signer_socket_bounded(
    *,
    repo_root: Path | str,
    socket_path: Path | str | None,
    backend: Optional[IsolatedSignerBackend] = None,
    peer_attestor: Optional[SignerSocketPeerAttestor] = None,
    max_requests: int = DEFAULT_SIGNER_SOCKET_RESIDENT_MAX_REQUESTS,
    timeout_s: float = DEFAULT_SIGNER_SOCKET_SERVICE_TIMEOUT_S,
    max_request_bytes: int = DEFAULT_SIGNER_SOCKET_MAX_REQUEST_BYTES,
    max_response_bytes: int = DEFAULT_SIGNER_SOCKET_SERVICE_MAX_RESPONSE_BYTES,
    ready_callback: Optional[Callable[[], None]] = None,
) -> IsolatedSignerSocketResidentServiceResult:
    """Serve up to ``max_requests`` signer requests on one guarded socket."""

    resolved, reasons = _resolve_socket_path(repo_root=repo_root, socket_path=socket_path)
    if reasons:
        return _reject(*reasons)
    assert resolved is not None
    limit_reasons = validate_resident_signer_socket_limits(
        max_requests=max_requests,
        timeout_s=timeout_s,
        max_request_bytes=max_request_bytes,
        max_response_bytes=max_response_bytes,
    )
    if limit_reasons:
        return _reject(*limit_reasons, socket_path=str(resolved))
    if not hasattr(socket, "AF_UNIX"):
        return _reject(FAIL_SIGNER_SERVICE_SOCKET_UNAVAILABLE, socket_path=str(resolved))
    return _serve_validated(
        resolved=resolved,
        backend=backend or FailClosedSignerBackend(),
        peer_attestor=peer_attestor or FailClosedSignerSocketPeerAttestor(),
        max_requests=max_requests,
        timeout_s=timeout_s,
        max_request_bytes=max_request_bytes,
        max_response_bytes=max_response_bytes,
        ready_callback=ready_callback,
    )


def _serve_validated(
    *,
    resolved: Path,
    backend: IsolatedSignerBackend,
    peer_attestor: SignerSocketPeerAttestor,
    max_requests: int,
    timeout_s: float,
    max_request_bytes: int,
    max_response_bytes: int,
    ready_callback: Optional[Callable[[], None]],
) -> IsolatedSignerSocketResidentServiceResult:
    server: Optional[socket.socket] = None
    bound_identity: Optional[_BoundSocketIdentity] = None
    socket_removed = False
    requests_handled = 0
    response_digests: tuple[str, ...] = ()
    try:
        server, bound_identity = _bound_server(resolved, timeout_s)
        if ready_callback:
            ready_callback()
        requests_handled, response_digests = _serve_requests(
            server, backend, peer_attestor, max_requests,
            timeout_s, max_request_bytes, max_response_bytes,
        )
        server.close()
        server = None
        socket_removed = _cleanup_socket(resolved, bound_identity)
        return IsolatedSignerSocketResidentServiceResult(
            accepted=True,
            status=SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
            rejection_reasons=(),
            socket_path=str(resolved),
            requests_handled=requests_handled,
            response_digests=response_digests,
            socket_removed=socket_removed,
        )
    except Exception:
        return _reject(
            FAIL_SIGNER_SERVICE_RUNTIME_ERROR,
            socket_path=str(resolved),
            requests_handled=requests_handled,
            response_digests=response_digests,
        )
    finally:
        if server is not None:
            server.close()
        if not socket_removed and resolved is not None and bound_identity is not None:
            _cleanup_socket(resolved, bound_identity)


def _bound_server(
    path: Path, timeout_s: float
) -> tuple[socket.socket, _BoundSocketIdentity]:
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.settimeout(float(timeout_s))
    server.bind(str(path))
    identity = _socket_identity(path)
    if identity is None:
        server.close()
        raise OSError(FAIL_SIGNER_SERVICE_RUNTIME_ERROR)
    server.listen(1)
    return server, identity


def _serve_requests(
    server: socket.socket,
    backend: IsolatedSignerBackend,
    peer_attestor: SignerSocketPeerAttestor,
    max_requests: int,
    timeout_s: float,
    max_request_bytes: int,
    max_response_bytes: int,
) -> tuple[int, tuple[str, ...]]:
    digests: list[str] = []
    for _ in range(max_requests):
        connection, _ = server.accept()
        with connection:
            connection.settimeout(float(timeout_s))
            request = _read_bounded(connection, max_request_bytes)
            peer = peer_attestor.attest(connection)
            response = handle_reddog_isolated_signer_socket_request(
                request, peer=peer, backend=backend,
                max_request_bytes=max_request_bytes,
            )
            response = _bounded_response(response, max_response_bytes)
            connection.sendall(response)
            digests.append(_digest(response))
    return max_requests, tuple(digests)


def _bounded_response(value: bytes, maximum: int) -> bytes:
    if len(value) <= maximum:
        return value
    rejected = _response_bytes(RuntimeRejectCode.MALFORMED_REQUEST)
    if len(rejected) > maximum:
        raise ValueError(FAIL_SIGNER_SERVICE_RESPONSE_LIMIT_INVALID)
    return rejected


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
    if not _socket_parent_protected(resolved.parent):
        return None, (FAIL_SIGNER_SERVICE_SOCKET_PARENT_UNSAFE,)
    if resolved.exists():
        return None, (FAIL_SIGNER_SERVICE_SOCKET_PATH_EXISTS,)
    return resolved, ()


def _socket_parent_protected(parent: Path) -> bool:
    if os.name != "posix" or not hasattr(os, "geteuid"):
        return True
    try:
        metadata = parent.lstat()
    except OSError:
        return False
    return not parent.is_symlink() and _protected_parent_metadata(metadata)


def _protected_parent_metadata(metadata: os.stat_result) -> bool:
    return all(
        (
            stat.S_ISDIR(metadata.st_mode),
            int(metadata.st_uid) == int(os.geteuid()),
            stat.S_IMODE(metadata.st_mode) & 0o022 == 0,
        )
    )


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


def validate_resident_signer_socket_limits(
    *,
    max_requests: object,
    timeout_s: object,
    max_request_bytes: object,
    max_response_bytes: object,
) -> tuple[str, ...]:
    """Validate the exact bounded-service limits without opening a socket."""

    reasons: list[str] = []
    if type(max_requests) is not int or not 1 <= max_requests <= 128:
        reasons.append(FAIL_SIGNER_RESIDENT_SERVICE_MAX_REQUESTS_INVALID)
    if (
        isinstance(timeout_s, bool)
        or not isinstance(timeout_s, (int, float))
        or not math.isfinite(float(timeout_s))
    ):
        reasons.append(FAIL_SIGNER_SERVICE_TIMEOUT_INVALID)
    if type(max_request_bytes) is not int:
        reasons.append(FAIL_SIGNER_SERVICE_REQUEST_LIMIT_INVALID)
    if type(max_response_bytes) is not int:
        reasons.append(FAIL_SIGNER_SERVICE_RESPONSE_LIMIT_INVALID)
    if reasons:
        return tuple(dict.fromkeys(reasons))
    return _validate_limits(
        float(timeout_s),
        max_request_bytes,
        max_response_bytes,
    )


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


def _socket_identity(path: Path) -> Optional[_BoundSocketIdentity]:
    try:
        current = path.lstat()
    except OSError:
        return None
    return _identity_from_metadata(current)


def _identity_from_metadata(
    current: os.stat_result,
) -> Optional[_BoundSocketIdentity]:
    if not stat.S_ISSOCK(current.st_mode):
        return None
    return _BoundSocketIdentity(
        device=int(current.st_dev),
        inode=int(current.st_ino),
        uid=int(getattr(current, "st_uid", -1)),
        gid=int(getattr(current, "st_gid", -1)),
    )


def _cleanup_socket(path: Path, expected: _BoundSocketIdentity) -> bool:
    if os.name == "posix":
        return _cleanup_socket_from_protected_parent(path, expected)
    try:
        current = _socket_identity(path)
        if current is None or current != expected:
            return False
        path.unlink()
        return not os.path.lexists(path)
    except OSError:
        return False


def _cleanup_socket_from_protected_parent(
    path: Path,
    expected: _BoundSocketIdentity,
) -> bool:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    directory_fd: int | None = None
    try:
        directory_fd = os.open(path.parent, flags)
        parent = os.fstat(directory_fd)
        if not _protected_parent_metadata(parent):
            return False
        current = os.stat(
            path.name, dir_fd=directory_fd, follow_symlinks=False
        )
        if _identity_from_metadata(current) != expected:
            return False
        os.unlink(path.name, dir_fd=directory_fd)
        return not os.path.lexists(path)
    except OSError:
        return False
    finally:
        if directory_fd is not None:
            os.close(directory_fd)


def _reject(
    *reasons: str,
    socket_path: Optional[str] = None,
    requests_handled: int = 0,
    response_digests: tuple[str, ...] = (),
) -> IsolatedSignerSocketResidentServiceResult:
    return IsolatedSignerSocketResidentServiceResult(
        accepted=False,
        status=SIGNER_SOCKET_RESIDENT_SERVICE_REJECT,
        rejection_reasons=tuple(dict.fromkeys(reason for reason in reasons if reason)),
        socket_path=socket_path,
        requests_handled=requests_handled,
        response_digests=response_digests,
    )


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


__all__ = [
    "DEFAULT_SIGNER_SOCKET_RESIDENT_MAX_REQUESTS",
    "FAIL_SIGNER_RESIDENT_SERVICE_MAX_REQUESTS_INVALID",
    "IsolatedSignerSocketResidentServiceResult",
    "SIGNER_SOCKET_RESIDENT_SERVICE_REJECT",
    "SIGNER_SOCKET_RESIDENT_SERVICE_SERVED",
    "serve_reddog_isolated_signer_socket_bounded",
    "validate_resident_signer_socket_limits",
]
