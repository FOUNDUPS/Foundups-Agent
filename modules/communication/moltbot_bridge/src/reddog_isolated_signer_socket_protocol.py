"""Fail-closed protocol core for an isolated RedDog signer socket service.

Slice: REDDOG_ISOLATED_SIGNER_SOCKET_PROTOCOL_PHASE1

This module implements the signer-side JSON protocol used by
``reddog_isolated_signer_socket_client``. It parses one request, binds it to an
already-attested peer identity, calls an injected signing backend, and serializes
a bounded ``SigningResponse``.

It does not bind a socket, discover kernel peer credentials, spawn a process,
load private keys or vault secrets, execute shell commands, mutate repository
files, enqueue OpenClaw, dispatch Hermes, or re-index HoloIndex. The default
backend fails closed.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Optional, Protocol

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    FailClosedSignerClient,
    RuntimeRejectCode,
    SigningRequest,
    SigningResponse,
)


SIGNER_SOCKET_REQUEST_SCHEMA_VERSION = "reddog_signer_socket_request.v1"

REJECT_SIGNER_SOCKET_REQUEST_TOO_LARGE = "REJECT_SIGNER_SOCKET_REQUEST_TOO_LARGE"
REJECT_SIGNER_SOCKET_REQUEST_INVALID = "REJECT_SIGNER_SOCKET_REQUEST_INVALID"
REJECT_SIGNER_SOCKET_SCHEMA_INVALID = "REJECT_SIGNER_SOCKET_SCHEMA_INVALID"
REJECT_SIGNER_SOCKET_PEER_MISMATCH = "REJECT_SIGNER_SOCKET_PEER_MISMATCH"
REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED = "REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED"
REJECT_SIGNER_SOCKET_BACKEND_EXCEPTION = "REJECT_SIGNER_SOCKET_BACKEND_EXCEPTION"
REJECT_SIGNER_SOCKET_RESPONSE_INVALID = "REJECT_SIGNER_SOCKET_RESPONSE_INVALID"
REJECT_SIGNER_SOCKET_NON_ASCII = "REJECT_SIGNER_SOCKET_NON_ASCII"

DEFAULT_SIGNER_SOCKET_MAX_REQUEST_BYTES = 16384


@dataclass(frozen=True)
class SignerPeerAttestation:
    """Peer identity supplied by the future socket daemon boundary."""

    peer_principal_id: str
    transport: str
    credential_source: str
    boundary_attested: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IsolatedSignerBackend(Protocol):
    """Injected signer backend used by the protocol core."""

    def sign(self, request: SigningRequest, peer: SignerPeerAttestation) -> SigningResponse:
        """Sign a validated request or reject fail-closed."""


class FailClosedSignerBackend:
    """Default backend: never signs."""

    def __init__(self) -> None:
        self._client = FailClosedSignerClient()

    def sign(self, request: SigningRequest, peer: SignerPeerAttestation) -> SigningResponse:
        return self._client.sign(request)


def handle_reddog_isolated_signer_socket_request(
    request_bytes: bytes,
    *,
    peer: SignerPeerAttestation,
    backend: Optional[IsolatedSignerBackend] = None,
    max_request_bytes: int = DEFAULT_SIGNER_SOCKET_MAX_REQUEST_BYTES,
) -> bytes:
    """Handle one signer-socket request payload.

    The peer identity is intentionally supplied out-of-band. Request-body
    ``requester_principal_id`` is audit-only and must match the attested peer.
    """

    if not isinstance(request_bytes, bytes) or len(request_bytes) > max_request_bytes:
        return _response_bytes(_reject(REJECT_SIGNER_SOCKET_REQUEST_TOO_LARGE))
    if not isinstance(peer, SignerPeerAttestation) or not peer.boundary_attested:
        return _response_bytes(_reject(REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED))
    if not _assert_ascii_deep(peer.to_dict()):
        return _response_bytes(_reject(REJECT_SIGNER_SOCKET_NON_ASCII))

    request = _parse_request(request_bytes)
    if not isinstance(request, SigningRequest):
        return _response_bytes(request)
    if not _assert_ascii_deep(request.to_dict()):
        return _response_bytes(_reject(REJECT_SIGNER_SOCKET_NON_ASCII))
    if request.requester_principal_id != peer.peer_principal_id:
        return _response_bytes(_reject(REJECT_SIGNER_SOCKET_PEER_MISMATCH))

    signer = backend or FailClosedSignerBackend()
    try:
        response = signer.sign(request, peer)
    except Exception:
        return _response_bytes(_reject(REJECT_SIGNER_SOCKET_BACKEND_EXCEPTION))
    if not isinstance(response, SigningResponse):
        return _response_bytes(_reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID))
    checked = _validate_response(response)
    return _response_bytes(checked)


def _parse_request(request_bytes: bytes) -> SigningRequest | SigningResponse:
    try:
        payload = json.loads(request_bytes.decode("utf-8").strip())
    except Exception:
        return _reject(REJECT_SIGNER_SOCKET_REQUEST_INVALID)
    if not isinstance(payload, Mapping):
        return _reject(REJECT_SIGNER_SOCKET_REQUEST_INVALID)
    if payload.get("schema_version") != SIGNER_SOCKET_REQUEST_SCHEMA_VERSION:
        return _reject(REJECT_SIGNER_SOCKET_SCHEMA_INVALID)
    raw = payload.get("request")
    if not isinstance(raw, Mapping):
        return _reject(REJECT_SIGNER_SOCKET_REQUEST_INVALID)
    try:
        return SigningRequest(
            signing_input=str(raw["signing_input"]),
            payload_digest=str(raw["payload_digest"]),
            signer_role=str(raw["signer_role"]),
            signer_public_key=str(raw["signer_public_key"]),
            requester_principal_id=str(raw["requester_principal_id"]),
            nonce=str(raw["nonce"]),
            key_epoch=str(raw["key_epoch"]),
            requested_operation=str(raw["requested_operation"]),
            authority_tier=str(raw["authority_tier"]),
            consensus_receipt_digest=(
                str(raw["consensus_receipt_digest"])
                if raw.get("consensus_receipt_digest")
                else None
            ),
        )
    except Exception:
        return _reject(REJECT_SIGNER_SOCKET_REQUEST_INVALID)


def _validate_response(response: SigningResponse) -> SigningResponse:
    payload = response.to_dict()
    if not _assert_ascii_deep(payload):
        return _reject(REJECT_SIGNER_SOCKET_NON_ASCII)
    if response.no_secret_material_returned is not True:
        return _reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID)
    if response.accepted is not True:
        return response
    required = (
        response.signature,
        response.signer_public_key,
        response.key_fingerprint,
        response.key_epoch,
        response.audit_mac,
    )
    if not all(isinstance(value, str) and value for value in required):
        return _reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID)
    if not (
        response.boundary_attested
        and response.requester_identity_attested
        and response.signer_loads_no_untrusted_code
    ):
        return _reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID)
    return response


def _response_bytes(response: SigningResponse) -> bytes:
    payload = response.to_dict()
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _reject(code: str) -> SigningResponse:
    return SigningResponse(
        accepted=False,
        rejection_code=str(code),
        no_secret_material_returned=True,
    )


def _assert_ascii_deep(value: Any) -> bool:
    if isinstance(value, str):
        return all(ord(char) < 128 for char in value)
    if isinstance(value, Mapping):
        return all(
            isinstance(key, str)
            and all(ord(char) < 128 for char in key)
            and _assert_ascii_deep(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return all(_assert_ascii_deep(item) for item in value)
    if value is None or isinstance(value, (bool, int, float)):
        return True
    return False


__all__ = [
    "DEFAULT_SIGNER_SOCKET_MAX_REQUEST_BYTES",
    "FailClosedSignerBackend",
    "IsolatedSignerBackend",
    "REJECT_SIGNER_SOCKET_BACKEND_EXCEPTION",
    "REJECT_SIGNER_SOCKET_NON_ASCII",
    "REJECT_SIGNER_SOCKET_PEER_MISMATCH",
    "REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED",
    "REJECT_SIGNER_SOCKET_REQUEST_INVALID",
    "REJECT_SIGNER_SOCKET_REQUEST_TOO_LARGE",
    "REJECT_SIGNER_SOCKET_RESPONSE_INVALID",
    "REJECT_SIGNER_SOCKET_SCHEMA_INVALID",
    "SIGNER_SOCKET_REQUEST_SCHEMA_VERSION",
    "SignerPeerAttestation",
    "handle_reddog_isolated_signer_socket_request",
]
