"""Fail-closed client for an isolated RedDog signer service.

Slice: REDDOG_ISOLATED_SIGNER_SOCKET_CLIENT_PHASE1

This module implements the client side of the E0 signing-key isolation
boundary. RedDog may connect to an already-running signer over a caller-provided
local socket path, send a ``SigningRequest``, and receive a ``SigningResponse``.

It never spawns the signer, never loads a private key or vault secret, never
executes shell commands, never mutates repository files, and never treats a
socket reply as execution authority by itself.
"""

from __future__ import annotations

import json
import socket
import stat
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    IsolatedSignerClient,
    RuntimeRejectCode,
    SigningRequest,
    SigningResponse,
)


SIGNER_SOCKET_CLIENT_READY = "SIGNER_SOCKET_CLIENT_READY"
SIGNER_SOCKET_CLIENT_REJECT = "SIGNER_SOCKET_CLIENT_REJECT"

FAIL_SIGNER_SOCKET_PATH_MISSING = "FAIL_SIGNER_SOCKET_PATH_MISSING"
FAIL_SIGNER_SOCKET_PATH_RELATIVE = "FAIL_SIGNER_SOCKET_PATH_RELATIVE"
FAIL_SIGNER_SOCKET_PATH_INSIDE_REPO = "FAIL_SIGNER_SOCKET_PATH_INSIDE_REPO"
FAIL_SIGNER_SOCKET_DEVICE_PREFIX = "FAIL_SIGNER_SOCKET_DEVICE_PREFIX"
FAIL_SIGNER_SOCKET_PATH_UNAVAILABLE = "FAIL_SIGNER_SOCKET_PATH_UNAVAILABLE"
FAIL_SIGNER_SOCKET_TIMEOUT_INVALID = "FAIL_SIGNER_SOCKET_TIMEOUT_INVALID"
FAIL_SIGNER_SOCKET_RESPONSE_LIMIT_INVALID = "FAIL_SIGNER_SOCKET_RESPONSE_LIMIT_INVALID"
FAIL_SIGNER_SOCKET_SERVER_IDENTITY_INVALID = (
    "FAIL_SIGNER_SOCKET_SERVER_IDENTITY_INVALID"
)
FAIL_SIGNER_SOCKET_CONNECTOR_UNATTESTED = "FAIL_SIGNER_SOCKET_CONNECTOR_UNATTESTED"
FAIL_SIGNER_SOCKET_OWNERSHIP_INVALID = "FAIL_SIGNER_SOCKET_OWNERSHIP_INVALID"
FAIL_SIGNER_SOCKET_LINK_COMPONENT = "FAIL_SIGNER_SOCKET_LINK_COMPONENT"

REJECT_SIGNER_SOCKET_CONNECT_FAILED = "REJECT_SIGNER_SOCKET_CONNECT_FAILED"
REJECT_SIGNER_SOCKET_RESPONSE_TOO_LARGE = "REJECT_SIGNER_SOCKET_RESPONSE_TOO_LARGE"
REJECT_SIGNER_SOCKET_RESPONSE_INVALID = "REJECT_SIGNER_SOCKET_RESPONSE_INVALID"

DEFAULT_SIGNER_SOCKET_TIMEOUT_S = 5.0
DEFAULT_SIGNER_SOCKET_MAX_RESPONSE_BYTES = 32768

SignerSocketConnector = Callable[[Path, bytes, float, int], bytes]


@dataclass(frozen=True)
class SignerSocketClientBuildResult:
    """Result from guarded signer-socket client construction."""

    accepted: bool
    status: str
    rejection_reasons: tuple[str, ...]
    client: Optional["RedDogIsolatedSignerSocketClient"] = None
    socket_path: Optional[str] = None
    no_private_key_loaded: bool = True
    no_signer_spawned: bool = True
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True


@dataclass(frozen=True)
class RedDogIsolatedSignerSocketClient(IsolatedSignerClient):
    """Client for an already-running isolated signer service."""

    socket_path: Path
    timeout_s: float = DEFAULT_SIGNER_SOCKET_TIMEOUT_S
    max_response_bytes: int = DEFAULT_SIGNER_SOCKET_MAX_RESPONSE_BYTES
    connector: Optional[SignerSocketConnector] = None
    expected_server_uid: Optional[int] = None
    expected_server_gid: Optional[int] = None
    trusted_socket_root: Optional[Path] = None
    socket_identity: Optional[tuple[int, int]] = None

    def sign(self, request: SigningRequest) -> SigningResponse:
        """Send request to the isolated signer and return its response."""

        if not isinstance(request, SigningRequest):
            return _reject(RuntimeRejectCode.MALFORMED_REQUEST)
        elevated = request.elevated_consensus_proof is not None
        payload = {
            "schema_version": (
                "reddog_signer_socket_request.v2"
                if elevated
                else "reddog_signer_socket_request.v1"
            ),
            "request": request.to_dict(),
        }
        if elevated:
            payload["secret_access_grant"] = None
        return self._roundtrip(payload)

    def sign_with_secret_grant(
        self, request: SigningRequest, secret_access_grant: Mapping[str, Any]
    ) -> SigningResponse:
        """Send one strict v2 request carrying an externally signed grant."""

        if not isinstance(request, SigningRequest) or not isinstance(
            secret_access_grant, Mapping
        ):
            return _reject(RuntimeRejectCode.MALFORMED_REQUEST)
        return self._roundtrip(
            {
                "schema_version": "reddog_signer_socket_request.v2",
                "request": request.to_dict(),
                "secret_access_grant": dict(secret_access_grant),
            }
        )

    def _roundtrip(self, payload: Mapping[str, Any]) -> SigningResponse:
        try:
            request_bytes = (
                json.dumps(
                    payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
                )
                + "\n"
            ).encode("utf-8")
            raw = (
                self.connector(
                    self.socket_path,
                    request_bytes,
                    self.timeout_s,
                    self.max_response_bytes,
                )
                if self.connector
                else _unix_socket_roundtrip(
                    self.socket_path,
                    request_bytes,
                    self.timeout_s,
                    self.max_response_bytes,
                    self.expected_server_uid,
                    self.expected_server_gid,
                    self.trusted_socket_root,
                    self.socket_identity,
                )
            )
        except Exception:
            return _reject(REJECT_SIGNER_SOCKET_CONNECT_FAILED)
        if len(raw) > self.max_response_bytes:
            return _reject(REJECT_SIGNER_SOCKET_RESPONSE_TOO_LARGE)
        try:
            decoded = json.loads(raw.decode("utf-8").strip())
        except Exception:
            return _reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID)
        return _response_from_mapping(decoded)


def build_reddog_isolated_signer_socket_client(
    *,
    repo_root: Path | str,
    socket_path: Path | str | None,
    timeout_s: float = DEFAULT_SIGNER_SOCKET_TIMEOUT_S,
    max_response_bytes: int = DEFAULT_SIGNER_SOCKET_MAX_RESPONSE_BYTES,
    connector: Optional[SignerSocketConnector] = None,
    expected_server_uid: Optional[int] = None,
    expected_server_gid: Optional[int] = None,
    trusted_socket_root: Path | str | None = None,
) -> SignerSocketClientBuildResult:
    """Validate socket path and construct a fail-closed signer client."""
    paths = _validated_socket_paths(repo_root, socket_path, trusted_socket_root)
    if isinstance(paths, str):
        return _build_reject(paths)
    path, resolved, trusted_root = paths
    if connector is None and not resolved.exists():
        return _build_reject(FAIL_SIGNER_SOCKET_PATH_UNAVAILABLE)
    if timeout_s <= 0 or timeout_s > 30:
        return _build_reject(FAIL_SIGNER_SOCKET_TIMEOUT_INVALID)
    if max_response_bytes < 1024 or max_response_bytes > 262144:
        return _build_reject(FAIL_SIGNER_SOCKET_RESPONSE_LIMIT_INVALID)
    peer_error, socket_identity = _peer_authentication(
        path, connector, expected_server_uid, expected_server_gid, trusted_root
    )
    if peer_error:
        return _build_reject(peer_error)
    return SignerSocketClientBuildResult(
        accepted=True,
        status=SIGNER_SOCKET_CLIENT_READY,
        rejection_reasons=(),
        client=RedDogIsolatedSignerSocketClient(
            socket_path=resolved,
            timeout_s=float(timeout_s),
            max_response_bytes=int(max_response_bytes),
            connector=connector,
            expected_server_uid=expected_server_uid,
            expected_server_gid=expected_server_gid,
            trusted_socket_root=trusted_root,
            socket_identity=socket_identity,
        ),
        socket_path=str(resolved),
    )


def _validated_socket_paths(
    repo_root: Path | str,
    socket_path: Path | str | None,
    trusted_socket_root: Path | str | None,
) -> tuple[Path, Path, Optional[Path]] | str:
    if not socket_path:
        return FAIL_SIGNER_SOCKET_PATH_MISSING
    path_text = str(socket_path)
    if (
        "\x00" in path_text
        or path_text.startswith("\\\\?\\")
        or path_text.startswith("//?/")
    ):
        return FAIL_SIGNER_SOCKET_DEVICE_PREFIX
    path = Path(socket_path)
    if not path.is_absolute():
        return FAIL_SIGNER_SOCKET_PATH_RELATIVE
    trusted_root = Path(trusted_socket_root) if trusted_socket_root else None
    if _has_link_component(path) or (
        trusted_root is not None and _has_link_component(trusted_root)
    ):
        return FAIL_SIGNER_SOCKET_LINK_COMPONENT
    resolved = path.resolve()
    if _is_inside(resolved, Path(repo_root).resolve()):
        return FAIL_SIGNER_SOCKET_PATH_INSIDE_REPO
    if trusted_root is not None:
        if not trusted_root.is_absolute() or not _is_inside(resolved, trusted_root):
            return FAIL_SIGNER_SOCKET_OWNERSHIP_INVALID
        trusted_root = trusted_root.resolve()
    return path, resolved, trusted_root


def _peer_authentication(
    socket_path: Path,
    connector: Optional[SignerSocketConnector],
    expected_uid: Optional[int],
    expected_gid: Optional[int],
    trusted_root: Optional[Path],
) -> tuple[str, Optional[tuple[int, int]]]:
    if expected_uid is None and expected_gid is None:
        return "", None
    if (
        type(expected_uid) is not int
        or expected_uid < 0
        or type(expected_gid) is not int
        or expected_gid < 0
    ):
        return FAIL_SIGNER_SOCKET_SERVER_IDENTITY_INVALID, None
    if connector is not None:
        return FAIL_SIGNER_SOCKET_CONNECTOR_UNATTESTED, None
    try:
        identity = _require_protected_socket(
            socket_path, expected_uid, expected_gid, trusted_root=trusted_root
        )
    except (OSError, ValueError):
        return FAIL_SIGNER_SOCKET_OWNERSHIP_INVALID, None
    return "", identity


def _unix_socket_roundtrip(
    socket_path: Path,
    request_bytes: bytes,
    timeout_s: float,
    max_response_bytes: int,
    expected_server_uid: Optional[int],
    expected_server_gid: Optional[int],
    trusted_socket_root: Optional[Path],
    expected_socket_identity: Optional[tuple[int, int]],
) -> bytes:
    if expected_server_uid is not None:
        assert expected_server_gid is not None
        _require_protected_socket(
            socket_path,
            expected_server_uid,
            expected_server_gid,
            trusted_root=trusted_socket_root,
            expected_identity=expected_socket_identity,
        )
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as handle:
        handle.settimeout(timeout_s)
        handle.connect(str(socket_path))
        if expected_server_uid is not None:
            assert expected_server_gid is not None
            _require_connected_peer_identity(
                handle, expected_server_uid, expected_server_gid
            )
            _require_protected_socket(
                socket_path,
                expected_server_uid,
                expected_server_gid,
                trusted_root=trusted_socket_root,
                expected_identity=expected_socket_identity,
            )
        handle.sendall(request_bytes)
        handle.shutdown(socket.SHUT_WR)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = handle.recv(4096)
            if not chunk:
                break
            total += len(chunk)
            if total > max_response_bytes:
                raise ValueError(REJECT_SIGNER_SOCKET_RESPONSE_TOO_LARGE)
            chunks.append(chunk)
        return b"".join(chunks)


def _require_connected_peer_identity(
    handle: socket.socket, expected_uid: int, expected_gid: int
) -> None:
    if not hasattr(socket, "SO_PEERCRED"):
        raise OSError("signer_socket_peer_credential_unavailable")
    raw = handle.getsockopt(
        socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")
    )
    _pid, uid, gid = struct.unpack("3i", raw)
    if uid != expected_uid or gid != expected_gid:
        raise OSError("signer_socket_server_identity_mismatch")


def _require_protected_socket(
    path: Path,
    expected_uid: int,
    expected_gid: int,
    *,
    trusted_root: Optional[Path],
    expected_identity: Optional[tuple[int, int]] = None,
) -> tuple[int, int]:
    if _has_link_component(path):
        raise ValueError("signer_socket_link_component")
    current = path.lstat()
    parent = path.parent.lstat()
    identity = (current.st_dev, current.st_ino)
    if (
        path.is_symlink()
        or path.parent.is_symlink()
        or not stat.S_ISSOCK(current.st_mode)
        or current.st_uid != expected_uid
        or current.st_gid != expected_gid
        or parent.st_uid != expected_uid
        or parent.st_gid != expected_gid
        or stat.S_IMODE(parent.st_mode) & 0o022
        or (expected_identity is not None and identity != expected_identity)
    ):
        raise ValueError("signer_socket_ownership_invalid")
    if trusted_root is not None:
        _require_protected_ancestry(path.parent, trusted_root, expected_uid, expected_gid)
    return identity


def _require_protected_ancestry(
    parent: Path, trusted_root: Path, expected_uid: int, expected_gid: int
) -> None:
    root = trusted_root.resolve()
    if not _is_inside(parent, root):
        raise ValueError("signer_socket_root_invalid")
    current = parent
    while True:
        info = current.lstat()
        if (
            current.is_symlink()
            or info.st_uid != expected_uid
            or info.st_gid != expected_gid
            or stat.S_IMODE(info.st_mode) & 0o022
        ):
            raise ValueError("signer_socket_ancestry_invalid")
        if current == root:
            return
        current = current.parent


def _has_link_component(path: Path) -> bool:
    current = path
    while True:
        try:
            info = current.lstat()
        except FileNotFoundError:
            pass
        else:
            reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
            attributes = getattr(info, "st_file_attributes", 0)
            if stat.S_ISLNK(info.st_mode) or (reparse and attributes & reparse):
                return True
        if current.parent == current:
            return False
        current = current.parent


def _response_from_mapping(value: object) -> SigningResponse:
    if not isinstance(value, dict):
        return _reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID)
    accepted = value.get("accepted")
    if not isinstance(accepted, bool):
        return _reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID)
    if accepted is not True:
        return SigningResponse(
            accepted=False,
            rejection_code=str(
                value.get("rejection_code") or REJECT_SIGNER_SOCKET_RESPONSE_INVALID
            ),
            no_secret_material_returned=True,
        )
    required = (
        "signature",
        "signer_public_key",
        "key_fingerprint",
        "key_epoch",
        "audit_mac",
    )
    if any(
        not isinstance(value.get(field), str) or not value.get(field)
        for field in required
    ):
        return _reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID)
    return SigningResponse(
        accepted=True,
        signature=str(value["signature"]),
        signer_public_key=str(value["signer_public_key"]),
        key_fingerprint=str(value["key_fingerprint"]),
        key_epoch=str(value["key_epoch"]),
        audit_mac=str(value["audit_mac"]),
        audit_attestation_signature=str(value.get("audit_attestation_signature") or ""),
        boundary_attested=value.get("boundary_attested") is True,
        requester_identity_attested=value.get("requester_identity_attested") is True,
        signer_loads_no_untrusted_code=value.get("signer_loads_no_untrusted_code")
        is True,
        no_secret_material_returned=value.get("no_secret_material_returned")
        is not False,
    )


def _reject(code: str) -> SigningResponse:
    return SigningResponse(
        accepted=False,
        rejection_code=str(code),
        no_secret_material_returned=True,
    )


def _build_reject(*reasons: str) -> SignerSocketClientBuildResult:
    return SignerSocketClientBuildResult(
        accepted=False,
        status=SIGNER_SOCKET_CLIENT_REJECT,
        rejection_reasons=tuple(dict.fromkeys(reason for reason in reasons if reason)),
    )


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


__all__ = [
    "DEFAULT_SIGNER_SOCKET_MAX_RESPONSE_BYTES",
    "DEFAULT_SIGNER_SOCKET_TIMEOUT_S",
    "FAIL_SIGNER_SOCKET_DEVICE_PREFIX",
    "FAIL_SIGNER_SOCKET_PATH_INSIDE_REPO",
    "FAIL_SIGNER_SOCKET_PATH_MISSING",
    "FAIL_SIGNER_SOCKET_PATH_RELATIVE",
    "FAIL_SIGNER_SOCKET_PATH_UNAVAILABLE",
    "FAIL_SIGNER_SOCKET_RESPONSE_LIMIT_INVALID",
    "FAIL_SIGNER_SOCKET_TIMEOUT_INVALID",
    "FAIL_SIGNER_SOCKET_SERVER_IDENTITY_INVALID",
    "FAIL_SIGNER_SOCKET_CONNECTOR_UNATTESTED",
    "FAIL_SIGNER_SOCKET_OWNERSHIP_INVALID",
    "FAIL_SIGNER_SOCKET_LINK_COMPONENT",
    "REJECT_SIGNER_SOCKET_CONNECT_FAILED",
    "REJECT_SIGNER_SOCKET_RESPONSE_INVALID",
    "REJECT_SIGNER_SOCKET_RESPONSE_TOO_LARGE",
    "SIGNER_SOCKET_CLIENT_READY",
    "SIGNER_SOCKET_CLIENT_REJECT",
    "RedDogIsolatedSignerSocketClient",
    "SignerSocketClientBuildResult",
    "build_reddog_isolated_signer_socket_client",
]
