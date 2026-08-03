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
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    constant_time_compare,
)


SIGNER_SOCKET_REQUEST_SCHEMA_VERSION = "reddog_signer_socket_request.v1"
SIGNER_SOCKET_REQUEST_SCHEMA_VERSION_V2 = "reddog_signer_socket_request.v2"

REJECT_SIGNER_SOCKET_REQUEST_TOO_LARGE = "REJECT_SIGNER_SOCKET_REQUEST_TOO_LARGE"
REJECT_SIGNER_SOCKET_REQUEST_INVALID = "REJECT_SIGNER_SOCKET_REQUEST_INVALID"
REJECT_SIGNER_SOCKET_SCHEMA_INVALID = "REJECT_SIGNER_SOCKET_SCHEMA_INVALID"
REJECT_SIGNER_SOCKET_PEER_MISMATCH = "REJECT_SIGNER_SOCKET_PEER_MISMATCH"
REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED = "REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED"
REJECT_SIGNER_SOCKET_BACKEND_EXCEPTION = "REJECT_SIGNER_SOCKET_BACKEND_EXCEPTION"
REJECT_SIGNER_SOCKET_RESPONSE_INVALID = "REJECT_SIGNER_SOCKET_RESPONSE_INVALID"
REJECT_SIGNER_SOCKET_NON_ASCII = "REJECT_SIGNER_SOCKET_NON_ASCII"
REJECT_SIGNER_SOCKET_SECRET_GRANT_UNSUPPORTED = (
    "REJECT_SIGNER_SOCKET_SECRET_GRANT_UNSUPPORTED"
)

DEFAULT_SIGNER_SOCKET_MAX_REQUEST_BYTES = 16384
_REQUEST_FIELDS = frozenset(SigningRequest.__dataclass_fields__)
_PUBLIC_REJECTION_CODES = frozenset(
    {
        REJECT_SIGNER_SOCKET_REQUEST_TOO_LARGE,
        REJECT_SIGNER_SOCKET_REQUEST_INVALID,
        REJECT_SIGNER_SOCKET_SCHEMA_INVALID,
        REJECT_SIGNER_SOCKET_PEER_MISMATCH,
        REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED,
        REJECT_SIGNER_SOCKET_BACKEND_EXCEPTION,
        REJECT_SIGNER_SOCKET_RESPONSE_INVALID,
        REJECT_SIGNER_SOCKET_NON_ASCII,
        REJECT_SIGNER_SOCKET_SECRET_GRANT_UNSUPPORTED,
        RuntimeRejectCode.SIGNER_NOT_CONFIGURED,
        RuntimeRejectCode.SIGNER_BOUNDARY_NOT_ATTESTED,
        RuntimeRejectCode.SIGNER_KEY_MISMATCH,
        RuntimeRejectCode.SIGNER_RESPONSE_INVALID,
    }
)


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


class GrantAwareSignerBackend(Protocol):
    """Signer backend that requires one authenticated secret-access grant."""

    def sign_with_secret_grant(
        self,
        request: SigningRequest,
        peer: SignerPeerAttestation,
        grant: Mapping[str, Any],
    ) -> SigningResponse:
        """Consume one grant and sign one exact request."""


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
    if not _valid_peer_attestation(peer):
        return _response_bytes(_reject(REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED))
    if not _assert_ascii_deep(asdict(peer)):
        return _response_bytes(_reject(REJECT_SIGNER_SOCKET_NON_ASCII))

    parsed = _parse_request(request_bytes)
    if isinstance(parsed, SigningResponse):
        return _response_bytes(parsed)
    request, secret_grant = parsed
    if not _assert_ascii_deep(request.to_dict()):
        return _response_bytes(_reject(REJECT_SIGNER_SOCKET_NON_ASCII))
    if not constant_time_compare(
        request.requester_principal_id, peer.peer_principal_id
    ):
        return _response_bytes(_reject(REJECT_SIGNER_SOCKET_PEER_MISMATCH))

    signer = backend or FailClosedSignerBackend()
    try:
        if secret_grant is None:
            response = signer.sign(request, peer)
        else:
            grant_signer = getattr(signer, "sign_with_secret_grant", None)
            if not callable(grant_signer):
                return _response_bytes(
                    _reject(REJECT_SIGNER_SOCKET_SECRET_GRANT_UNSUPPORTED)
                )
            response = grant_signer(request, peer, secret_grant)
    except Exception:
        return _response_bytes(_reject(REJECT_SIGNER_SOCKET_BACKEND_EXCEPTION))
    if type(response) is not SigningResponse:
        return _response_bytes(_reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID))
    checked = _validate_response(response, request)
    return _response_bytes(checked)


def _parse_request(
    request_bytes: bytes,
) -> tuple[SigningRequest, Mapping[str, Any] | None] | SigningResponse:
    payload = _decode_request_payload(request_bytes)
    if isinstance(payload, SigningResponse):
        return payload
    schema = payload.get("schema_version")
    if schema not in {
        SIGNER_SOCKET_REQUEST_SCHEMA_VERSION,
        SIGNER_SOCKET_REQUEST_SCHEMA_VERSION_V2,
    }:
        return _reject(REJECT_SIGNER_SOCKET_SCHEMA_INVALID)
    raw = payload.get("request")
    if not isinstance(raw, Mapping):
        return _reject(REJECT_SIGNER_SOCKET_REQUEST_INVALID)
    strict = schema == SIGNER_SOCKET_REQUEST_SCHEMA_VERSION_V2
    expected_envelope = {"schema_version", "request", "secret_access_grant"}
    if strict and (set(payload) != expected_envelope or set(raw) != _REQUEST_FIELDS):
        return _reject(REJECT_SIGNER_SOCKET_REQUEST_INVALID)
    request = _build_signing_request(raw, strict=strict)
    if isinstance(request, SigningResponse):
        return request
    return _parse_request_grant(payload, request, strict=strict)


def _decode_request_payload(
    request_bytes: bytes,
) -> Mapping[str, Any] | SigningResponse:
    try:
        payload = json.loads(
            request_bytes.decode("utf-8").strip(),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except Exception:
        return _reject(REJECT_SIGNER_SOCKET_REQUEST_INVALID)
    if not isinstance(payload, Mapping):
        return _reject(REJECT_SIGNER_SOCKET_REQUEST_INVALID)
    return payload


def _build_signing_request(
    raw: Mapping[str, Any], *, strict: bool
) -> SigningRequest | SigningResponse:
    try:
        if strict and not _strict_request_types(raw):
            raise TypeError("strict signer request types required")
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


def _parse_request_grant(
    payload: Mapping[str, Any],
    request: SigningRequest,
    *,
    strict: bool,
) -> tuple[SigningRequest, Mapping[str, Any] | None] | SigningResponse:
    grant = payload.get("secret_access_grant")
    if strict:
        if not isinstance(grant, Mapping) or not _assert_ascii_deep(grant):
            return _reject(REJECT_SIGNER_SOCKET_REQUEST_INVALID)
        return request, dict(grant)
    if grant is not None:
        return _reject(REJECT_SIGNER_SOCKET_REQUEST_INVALID)
    return request, None


def _validate_response(
    response: SigningResponse, request: SigningRequest
) -> SigningResponse:
    if type(response) is not SigningResponse:
        return _reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID)
    payload = asdict(response)
    if not _assert_ascii_deep(payload):
        return _reject(REJECT_SIGNER_SOCKET_NON_ASCII)
    if (
        type(response.accepted) is not bool
        or type(response.no_secret_material_returned) is not bool
        or response.no_secret_material_returned is not True
    ):
        return _reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID)
    if response.accepted is not True:
        return response if _rejected_response_is_public(response) else _reject(
            REJECT_SIGNER_SOCKET_RESPONSE_INVALID
        )
    required = (
        response.signature,
        response.signer_public_key,
        response.key_fingerprint,
        response.key_epoch,
        response.audit_mac,
    )
    if not all(type(value) is str and value for value in required):
        return _reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID)
    if not _accepted_response_fields_valid(response):
        return _reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID)
    if not (
        constant_time_compare(response.signer_public_key, request.signer_public_key)
        and constant_time_compare(response.key_epoch, request.key_epoch)
        and constant_time_compare(
            response.key_fingerprint,
            public_key_fingerprint(response.signer_public_key),
        )
    ):
        return _reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID)
    return response


def _accepted_response_fields_valid(response: SigningResponse) -> bool:
    bounded = (
        (response.signature, 512),
        (response.signer_public_key, 512),
        (response.key_fingerprint, 128),
        (response.key_epoch, 128),
        (response.audit_mac, 512),
        (response.audit_attestation_signature, 512),
        (response.rejection_code, 128),
    )
    return bool(
        all(type(value) is str and len(value) <= limit for value, limit in bounded)
        and response.rejection_code == ""
        and type(response.boundary_attested) is bool
        and response.boundary_attested is True
        and type(response.requester_identity_attested) is bool
        and response.requester_identity_attested is True
        and type(response.signer_loads_no_untrusted_code) is bool
        and response.signer_loads_no_untrusted_code is True
    )


def _rejected_response_is_public(response: SigningResponse) -> bool:
    secret_fields = (
        response.signature,
        response.signer_public_key,
        response.key_fingerprint,
        response.key_epoch,
        response.audit_mac,
        response.audit_attestation_signature,
    )
    return bool(
        all(type(value) is str and value == "" for value in secret_fields)
        and response.boundary_attested is False
        and response.requester_identity_attested is False
        and response.signer_loads_no_untrusted_code is False
        and type(response.rejection_code) is str
        and response.rejection_code in _PUBLIC_REJECTION_CODES
    )


def _valid_peer_attestation(peer: object) -> bool:
    if type(peer) is not SignerPeerAttestation:
        return False
    strings = (
        peer.peer_principal_id,
        peer.transport,
        peer.credential_source,
    )
    return bool(
        all(type(value) is str and value for value in strings)
        and peer.transport == "unix_socket"
        and peer.credential_source in {"kernel_peer_credential", "SO_PEERCRED"}
        and type(peer.boundary_attested) is bool
        and peer.boundary_attested is True
    )


def _response_bytes(response: SigningResponse) -> bytes:
    if type(response) is not SigningResponse:
        response = _reject(REJECT_SIGNER_SOCKET_RESPONSE_INVALID)
    payload = asdict(response)
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _strict_request_types(raw: Mapping[str, Any]) -> bool:
    return all(
        (key == "consensus_receipt_digest" and value is None)
        or isinstance(value, str)
        for key, value in raw.items()
    )


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
    "GrantAwareSignerBackend",
    "IsolatedSignerBackend",
    "REJECT_SIGNER_SOCKET_BACKEND_EXCEPTION",
    "REJECT_SIGNER_SOCKET_NON_ASCII",
    "REJECT_SIGNER_SOCKET_PEER_MISMATCH",
    "REJECT_SIGNER_SOCKET_PEER_NOT_ATTESTED",
    "REJECT_SIGNER_SOCKET_REQUEST_INVALID",
    "REJECT_SIGNER_SOCKET_REQUEST_TOO_LARGE",
    "REJECT_SIGNER_SOCKET_RESPONSE_INVALID",
    "REJECT_SIGNER_SOCKET_SCHEMA_INVALID",
    "REJECT_SIGNER_SOCKET_SECRET_GRANT_UNSUPPORTED",
    "SIGNER_SOCKET_REQUEST_SCHEMA_VERSION",
    "SIGNER_SOCKET_REQUEST_SCHEMA_VERSION_V2",
    "SignerPeerAttestation",
    "handle_reddog_isolated_signer_socket_request",
]
