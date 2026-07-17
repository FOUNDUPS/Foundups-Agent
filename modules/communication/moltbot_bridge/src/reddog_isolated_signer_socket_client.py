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
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

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

REJECT_SIGNER_SOCKET_CONNECT_FAILED = "REJECT_SIGNER_SOCKET_CONNECT_FAILED"
REJECT_SIGNER_SOCKET_RESPONSE_TOO_LARGE = "REJECT_SIGNER_SOCKET_RESPONSE_TOO_LARGE"
REJECT_SIGNER_SOCKET_RESPONSE_INVALID = "REJECT_SIGNER_SOCKET_RESPONSE_INVALID"

DEFAULT_SIGNER_SOCKET_TIMEOUT_S = 5.0
DEFAULT_SIGNER_SOCKET_MAX_RESPONSE_BYTES = 16384

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

    def sign(self, request: SigningRequest) -> SigningResponse:
        """Send request to the isolated signer and return its response."""

        if not isinstance(request, SigningRequest):
            return _reject(RuntimeRejectCode.MALFORMED_REQUEST)
        try:
            payload = {
                "schema_version": "reddog_signer_socket_request.v1",
                "request": request.to_dict(),
            }
            request_bytes = (
                json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                + "\n"
            ).encode("utf-8")
            raw = (
                self.connector(self.socket_path, request_bytes, self.timeout_s, self.max_response_bytes)
                if self.connector
                else _unix_socket_roundtrip(
                    self.socket_path,
                    request_bytes,
                    self.timeout_s,
                    self.max_response_bytes,
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
) -> SignerSocketClientBuildResult:
    """Validate socket path and construct a fail-closed signer client."""

    root = Path(repo_root).resolve()
    if not socket_path:
        return _build_reject(FAIL_SIGNER_SOCKET_PATH_MISSING)
    path_text = str(socket_path)
    if "\x00" in path_text or path_text.startswith("\\\\?\\") or path_text.startswith("//?/"):
        return _build_reject(FAIL_SIGNER_SOCKET_DEVICE_PREFIX)
    path = Path(socket_path)
    if not path.is_absolute():
        return _build_reject(FAIL_SIGNER_SOCKET_PATH_RELATIVE)
    resolved = path.resolve()
    if _is_inside(resolved, root):
        return _build_reject(FAIL_SIGNER_SOCKET_PATH_INSIDE_REPO)
    if connector is None and not resolved.exists():
        return _build_reject(FAIL_SIGNER_SOCKET_PATH_UNAVAILABLE)
    if timeout_s <= 0 or timeout_s > 30:
        return _build_reject(FAIL_SIGNER_SOCKET_TIMEOUT_INVALID)
    if max_response_bytes < 1024 or max_response_bytes > 262144:
        return _build_reject(FAIL_SIGNER_SOCKET_RESPONSE_LIMIT_INVALID)
    return SignerSocketClientBuildResult(
        accepted=True,
        status=SIGNER_SOCKET_CLIENT_READY,
        rejection_reasons=(),
        client=RedDogIsolatedSignerSocketClient(
            socket_path=resolved,
            timeout_s=float(timeout_s),
            max_response_bytes=int(max_response_bytes),
            connector=connector,
        ),
        socket_path=str(resolved),
    )


def _unix_socket_roundtrip(
    socket_path: Path,
    request_bytes: bytes,
    timeout_s: float,
    max_response_bytes: int,
) -> bytes:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as handle:
        handle.settimeout(timeout_s)
        handle.connect(str(socket_path))
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


def _response_from_mapping(value: object) -> SigningResponse:
    if not isinstance(value, dict):
        return _reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID)
    accepted = value.get("accepted")
    if not isinstance(accepted, bool):
        return _reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID)
    if accepted is not True:
        return SigningResponse(
            accepted=False,
            rejection_code=str(value.get("rejection_code") or REJECT_SIGNER_SOCKET_RESPONSE_INVALID),
            no_secret_material_returned=True,
        )
    required = (
        "signature",
        "signer_public_key",
        "key_fingerprint",
        "key_epoch",
        "audit_mac",
    )
    if any(not isinstance(value.get(field), str) or not value.get(field) for field in required):
        return _reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID)
    return SigningResponse(
        accepted=True,
        signature=str(value["signature"]),
        signer_public_key=str(value["signer_public_key"]),
        key_fingerprint=str(value["key_fingerprint"]),
        key_epoch=str(value["key_epoch"]),
        audit_mac=str(value["audit_mac"]),
        boundary_attested=value.get("boundary_attested") is True,
        requester_identity_attested=value.get("requester_identity_attested") is True,
        signer_loads_no_untrusted_code=value.get("signer_loads_no_untrusted_code") is True,
        no_secret_material_returned=value.get("no_secret_material_returned") is not False,
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
    "REJECT_SIGNER_SOCKET_CONNECT_FAILED",
    "REJECT_SIGNER_SOCKET_RESPONSE_INVALID",
    "REJECT_SIGNER_SOCKET_RESPONSE_TOO_LARGE",
    "SIGNER_SOCKET_CLIENT_READY",
    "SIGNER_SOCKET_CLIENT_REJECT",
    "RedDogIsolatedSignerSocketClient",
    "SignerSocketClientBuildResult",
    "build_reddog_isolated_signer_socket_client",
]
