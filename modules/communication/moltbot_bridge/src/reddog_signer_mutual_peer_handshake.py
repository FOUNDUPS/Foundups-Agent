"""Mutual peer authentication for the isolated RedDog signer socket.

The socket server already authenticates the client with kernel peer
credentials. This module supplies the reverse proof: the client sends a fresh,
short-lived challenge and verifies an Ed25519 response from the configured
signer key.

It does not load private keys, connect sockets, start processes, execute work,
mutate the repository, or re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_peer_instance_packet_validator import (
    signer_profile_bindings_valid,
    signer_run_packet_bindings_valid,
    signer_run_packet_selection_valid,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_text,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


SIGNER_PEER_HANDSHAKE_SCHEMA_VERSION = "reddog_signer_peer_handshake.v2"
SIGNER_PEER_HANDSHAKE_SIGNING_PREFIX = "reddog-signer-peer-handshake.v2."
SIGNER_PEER_HANDSHAKE_RESPONSE_ATTESTATION_PREFIX = (
    "reddog-signer-peer-response-attestation.v2."
)
SIGNER_PEER_HANDSHAKE_SIGNING_OPERATION = "signer_socket_peer_handshake"
SIGNER_PEER_HANDSHAKE_SIGNER_ROLE = "signer_peer_handshake"
DEFAULT_HANDSHAKE_TTL_SECONDS = 30
MAX_HANDSHAKE_TTL_SECONDS = 60
MAX_HANDSHAKE_CLOCK_SKEW_SECONDS = 5

FAIL_HANDSHAKE_REQUEST_INVALID = "signer_peer_handshake_request_invalid"
FAIL_HANDSHAKE_RESPONSE_REJECTED = "signer_peer_handshake_response_rejected"
FAIL_HANDSHAKE_SIGNER_BINDING = "signer_peer_handshake_signer_binding_mismatch"
FAIL_HANDSHAKE_SIGNATURE_INVALID = "signer_peer_handshake_signature_invalid"

_CHALLENGE_RE = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_PAYLOAD_FIELDS = frozenset(
    {
        "schema_version",
        "challenge",
        "manifest_id",
        "artifact_generation_digest",
        "run_packet_id",
        "config_digest",
        "session_id",
        "socket_path_digest",
        "signer_profile_id",
        "signer_public_key",
        "key_epoch",
        "requester_principal_id",
        "issued_at",
        "expires_at",
    }
)
class SignatureVerifier(Protocol):
    def verify(self, public_key: str, signing_input: str, signature: str) -> bool:
        """Return True only for a valid signature."""


@dataclass(frozen=True)
class SignerPeerProfileBinding:
    signer_profile_id: str
    signer_public_key: str
    key_epoch: str


@dataclass(frozen=True)
class SignerPeerInstanceBinding:
    """Signer-owned immutable binding loaded from the exact launch packet."""

    run_packet_id: str
    config_digest: str
    session_id: str
    socket_path: str
    signer_profiles: tuple[SignerPeerProfileBinding, ...]
    manifest_id: str
    artifact_generation_digest: str
    generation: int | None = None
    generation_revision: str | None = None
    owner_config_id: str | None = None


@dataclass(frozen=True)
class VerifiedSignerPeerHandshake:
    """Audit-safe result derived from a verified fresh challenge."""

    accepted: bool
    request_digest: str
    response_digest: str
    challenge_digest: str
    manifest_id: str
    artifact_generation_digest: str
    run_packet_id: str
    config_digest: str
    session_id: str
    signer_profile_id: str
    signer_public_key: str
    signer_key_fingerprint: str
    key_epoch: str
    requester_principal_id: str
    issued_at: int
    expires_at: int
    rejection_reasons: tuple[str, ...]
    no_signature_value_returned: bool = True
    no_secret_material_returned: bool = True
    no_runtime_effect_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_signer_peer_handshake_request(
    *,
    run_packet_id: str,
    config_digest: str,
    session_id: str,
    socket_path: str,
    signer_profile_id: str,
    signer_public_key: str,
    key_epoch: str,
    requester_principal_id: str,
    manifest_id: str,
    artifact_generation_digest: str,
    now_epoch: int | None = None,
    ttl_seconds: int = DEFAULT_HANDSHAKE_TTL_SECONDS,
    challenge_factory: Callable[[], str] | None = None,
) -> SigningRequest:
    """Build a fresh, domain-separated signer authentication challenge."""
    issued_at = int(time.time() if now_epoch is None else now_epoch)
    challenge = (challenge_factory or (lambda: secrets.token_hex(32)))()
    payload = {
        "schema_version": SIGNER_PEER_HANDSHAKE_SCHEMA_VERSION,
        "challenge": challenge,
        "manifest_id": manifest_id,
        "artifact_generation_digest": artifact_generation_digest,
        "run_packet_id": run_packet_id,
        "config_digest": config_digest,
        "session_id": session_id,
        "socket_path_digest": _text_digest(socket_path),
        "signer_profile_id": signer_profile_id,
        "signer_public_key": signer_public_key,
        "key_epoch": key_epoch,
        "requester_principal_id": requester_principal_id,
        "issued_at": issued_at,
        "expires_at": issued_at + int(ttl_seconds),
    }
    request = SigningRequest(
        signing_input=SIGNER_PEER_HANDSHAKE_SIGNING_PREFIX + _canonical(payload),
        payload_digest=_digest(payload),
        signer_role=SIGNER_PEER_HANDSHAKE_SIGNER_ROLE,
        signer_public_key=signer_public_key,
        requester_principal_id=requester_principal_id,
        nonce="signer-peer-handshake:" + str(challenge),
        key_epoch=key_epoch,
        requested_operation=SIGNER_PEER_HANDSHAKE_SIGNING_OPERATION,
        authority_tier="LOW",
        consensus_receipt_digest=None,
    )
    if validate_signer_peer_handshake_request(request, now_epoch=issued_at) is None:
        raise ValueError(FAIL_HANDSHAKE_REQUEST_INVALID)
    return request


def validate_signer_peer_handshake_request(
    request: SigningRequest,
    *,
    now_epoch: int | None = None,
    expected_binding: SignerPeerInstanceBinding | None = None,
) -> dict[str, Any] | None:
    """Validate the complete request at the signer-side trust boundary."""

    if not isinstance(request, SigningRequest):
        return None
    prefix = SIGNER_PEER_HANDSHAKE_SIGNING_PREFIX
    if not request.signing_input.startswith(prefix):
        return None
    try:
        payload = json.loads(request.signing_input[len(prefix) :])
    except Exception:
        return None
    if not _payload_shape_valid(payload):
        return None
    if not _request_bindings_valid(request, payload):
        return None
    if expected_binding is not None and not _instance_binding_matches(
        payload, expected_binding
    ):
        return None
    now = int(time.time() if now_epoch is None else now_epoch)
    if not _fresh(payload, now):
        return None
    return dict(payload)


def signer_handshake_request_matches_instance(
    request: SigningRequest,
    binding: SignerPeerInstanceBinding | None,
    *,
    now_epoch: int,
) -> bool:
    return binding is not None and validate_signer_peer_handshake_request(
        request,
        now_epoch=now_epoch,
        expected_binding=binding,
    ) is not None


def load_signer_peer_instance_binding(
    *,
    repo_root: Path | str,
    config_path: Path | str,
    expected_config_digest: str,
    run_packet_path: Path | str,
    expected_session_id: str | None,
    expected_socket_path: Path | str,
    signer_profiles: tuple[SignerPeerProfileBinding, ...],
    manifest_selection: Mapping[str, Any],
    python_executable: Path | str,
    owner_authority_config_path: Path | str,
) -> SignerPeerInstanceBinding | None:
    """Read and validate the signer launch packet at the signer boundary."""

    root = Path(repo_root).resolve()
    packet_data = _read_selected_run_packet(
        manifest_selection,
        repo_root=root,
        run_packet_path=run_packet_path,
    )
    if packet_data is None:
        return None
    packet_path, raw, packet = packet_data
    config = Path(config_path).resolve()
    actual_session_id = str(packet.get("session_id") or "")
    if expected_session_id is not None and (
        expected_session_id != actual_session_id
    ):
        return None
    if not signer_run_packet_selection_valid(
        manifest_selection,
        packet,
        root=root,
        config_path=config,
        run_packet_path=packet_path,
        config_digest=expected_config_digest,
        run_packet_raw=raw,
    ):
        return None
    if not signer_run_packet_bindings_valid(
        packet,
        root=root,
        config_path=config,
        config_digest=expected_config_digest,
        session_id=actual_session_id,
        run_packet_path=packet_path,
        socket_path=Path(expected_socket_path).resolve(),
        python_executable=Path(python_executable).resolve(),
        owner_authority_config_path=Path(
            owner_authority_config_path
        ).resolve(),
    ) or not signer_profile_bindings_valid(
        signer_profiles, packet.get("profile_count")
    ):
        return None
    return _peer_instance_binding(packet, signer_profiles, manifest_selection)


def _read_selected_run_packet(
    selection: Mapping[str, Any],
    *,
    repo_root: Path,
    run_packet_path: Path | str,
) -> tuple[Path, str, Mapping[str, Any]] | None:
    try:
        runtime_root = validate_runtime_root_path(
            selection["runtime_root"],
            repo_root=repo_root,
        )
        packet_path = validate_runtime_artifact_path(
            run_packet_path,
            repo_root=repo_root,
            allowed_root=runtime_root,
        )
        raw = secure_read_confined_text(
            packet_path,
            allowed_root=runtime_root,
            max_bytes=256 * 1024,
        )
        packet = json.loads(raw)
    except Exception:
        return None
    return (
        (packet_path, raw, packet)
        if isinstance(packet, Mapping)
        else None
    )


def _peer_instance_binding(
    packet: Mapping[str, Any],
    signer_profiles: tuple[SignerPeerProfileBinding, ...],
    selection: Mapping[str, Any],
) -> SignerPeerInstanceBinding:
    return SignerPeerInstanceBinding(
        run_packet_id=str(packet["run_packet_id"]),
        config_digest=str(packet["config_digest"]),
        session_id=str(packet["session_id"]),
        socket_path=str(Path(str(packet["socket_path"])).resolve()),
        signer_profiles=tuple(
            sorted(signer_profiles, key=lambda item: item.signer_profile_id)
        ),
        manifest_id=str(selection["manifest_id"]),
        artifact_generation_digest=str(selection["artifact_generation_digest"]),
        generation=int(selection["generation"]),
        generation_revision=str(selection["generation_revision"]),
        owner_config_id=str(selection["owner_config_id"]),
    )


def verify_signer_peer_handshake_response(
    request: SigningRequest,
    response: SigningResponse,
    *,
    now_epoch: int | None = None,
    verifier: SignatureVerifier | None = None,
) -> VerifiedSignerPeerHandshake:
    """Verify signer possession and all configured request bindings."""

    payload = validate_signer_peer_handshake_request(request, now_epoch=now_epoch)
    reasons: list[str] = []
    if payload is None:
        reasons.append(FAIL_HANDSHAKE_REQUEST_INVALID)
        return _verification_result(request, response, {}, reasons)
    if not isinstance(response, SigningResponse) or response.accepted is not True:
        reasons.append(FAIL_HANDSHAKE_RESPONSE_REJECTED)
    elif not _response_bindings_valid(request, response):
        reasons.append(FAIL_HANDSHAKE_SIGNER_BINDING)
    else:
        signature_verifier = verifier or Ed25519SignatureVerifier()
        if not signature_verifier.verify(
            request.signer_public_key,
            request.signing_input,
            response.signature,
        ):
            reasons.append(FAIL_HANDSHAKE_SIGNATURE_INVALID)
        elif not signature_verifier.verify(
            request.signer_public_key,
            canonical_signer_peer_response_attestation_input(
                request, response
            ),
            response.audit_attestation_signature,
        ):
            reasons.append(FAIL_HANDSHAKE_SIGNATURE_INVALID)
    return _verification_result(request, response, payload, reasons)


def canonical_signer_peer_response_attestation_input(
    request: SigningRequest,
    response: SigningResponse,
) -> str:
    """Bind all accepted handshake response evidence to the signer key."""

    payload = {
        "request_digest": _digest(request.to_dict()),
        "signature": response.signature,
        "signer_public_key": response.signer_public_key,
        "key_fingerprint": response.key_fingerprint,
        "key_epoch": response.key_epoch,
        "audit_mac": response.audit_mac,
        "accepted": response.accepted,
        "rejection_code": response.rejection_code,
        "boundary_attested": response.boundary_attested,
        "requester_identity_attested": response.requester_identity_attested,
        "signer_loads_no_untrusted_code": (
            response.signer_loads_no_untrusted_code
        ),
        "no_secret_material_returned": response.no_secret_material_returned,
    }
    return SIGNER_PEER_HANDSHAKE_RESPONSE_ATTESTATION_PREFIX + _canonical(
        payload
    )


def _payload_shape_valid(payload: object) -> bool:
    if not isinstance(payload, Mapping) or set(payload) != _PAYLOAD_FIELDS:
        return False
    if payload.get("schema_version") != SIGNER_PEER_HANDSHAKE_SCHEMA_VERSION:
        return False
    text_fields = _PAYLOAD_FIELDS - {"issued_at", "expires_at"}
    if any(not _ascii_text(payload.get(field)) for field in text_fields):
        return False
    return all(
        (
            bool(_CHALLENGE_RE.fullmatch(str(payload["challenge"]))),
            _sha256_digest(payload["manifest_id"]),
            _sha256_digest(payload["artifact_generation_digest"]),
        )
    )


def _request_bindings_valid(
    request: SigningRequest,
    payload: Mapping[str, Any],
) -> bool:
    return all(
        (
            request.requested_operation == SIGNER_PEER_HANDSHAKE_SIGNING_OPERATION,
            request.signer_role == SIGNER_PEER_HANDSHAKE_SIGNER_ROLE,
            request.authority_tier == "LOW",
            request.consensus_receipt_digest is None,
            request.signer_public_key == payload["signer_public_key"],
            request.key_epoch == payload["key_epoch"],
            request.requester_principal_id == payload["requester_principal_id"],
            request.nonce == "signer-peer-handshake:" + str(payload["challenge"]),
            request.payload_digest == _digest(payload),
            request.signing_input
            == SIGNER_PEER_HANDSHAKE_SIGNING_PREFIX + _canonical(payload),
        )
    )


def _fresh(payload: Mapping[str, Any], now_epoch: int) -> bool:
    issued_at = payload.get("issued_at")
    expires_at = payload.get("expires_at")
    if type(issued_at) is not int or type(expires_at) is not int:
        return False
    ttl = expires_at - issued_at
    return (
        0 < ttl <= MAX_HANDSHAKE_TTL_SECONDS
        and issued_at <= now_epoch + MAX_HANDSHAKE_CLOCK_SKEW_SECONDS
        and now_epoch < expires_at
    )


def _instance_binding_matches(
    payload: Mapping[str, Any],
    binding: SignerPeerInstanceBinding,
) -> bool:
    profile = next(
        (
            item
            for item in binding.signer_profiles
            if item.signer_profile_id == payload.get("signer_profile_id")
        ),
        None,
    )
    return profile is not None and all(
        (
            payload.get("run_packet_id") == binding.run_packet_id,
            payload.get("manifest_id") == binding.manifest_id,
            payload.get("artifact_generation_digest")
            == binding.artifact_generation_digest,
            payload.get("config_digest") == binding.config_digest,
            payload.get("session_id") == binding.session_id,
            payload.get("socket_path_digest")
            == _text_digest(binding.socket_path),
            payload.get("signer_public_key") == profile.signer_public_key,
            payload.get("key_epoch") == profile.key_epoch,
        )
    )


def _response_bindings_valid(
    request: SigningRequest,
    response: SigningResponse,
) -> bool:
    return all(
        (
            response.signer_public_key == request.signer_public_key,
            response.key_fingerprint
            == public_key_fingerprint(request.signer_public_key),
            response.key_epoch == request.key_epoch,
            bool(response.audit_mac),
            bool(response.audit_attestation_signature),
            response.boundary_attested is True,
            response.requester_identity_attested is True,
            response.signer_loads_no_untrusted_code is True,
            response.no_secret_material_returned is True,
        )
    )


def _verification_result(
    request: SigningRequest,
    response: SigningResponse,
    payload: Mapping[str, Any],
    reasons: list[str],
) -> VerifiedSignerPeerHandshake:
    return VerifiedSignerPeerHandshake(
        accepted=not reasons,
        request_digest=_digest(request.to_dict()) if isinstance(request, SigningRequest) else "",
        response_digest=(
            _digest(response.to_dict())
            if isinstance(response, SigningResponse)
            else ""
        ),
        challenge_digest=_text_digest(str(payload.get("challenge") or "")),
        manifest_id=str(payload.get("manifest_id") or ""),
        artifact_generation_digest=str(
            payload.get("artifact_generation_digest") or ""
        ),
        run_packet_id=str(payload.get("run_packet_id") or ""),
        config_digest=str(payload.get("config_digest") or ""),
        session_id=str(payload.get("session_id") or ""),
        signer_profile_id=str(payload.get("signer_profile_id") or ""),
        signer_public_key=str(payload.get("signer_public_key") or ""),
        signer_key_fingerprint=(
            public_key_fingerprint(str(payload["signer_public_key"]))
            if payload.get("signer_public_key")
            else ""
        ),
        key_epoch=str(payload.get("key_epoch") or ""),
        requester_principal_id=str(payload.get("requester_principal_id") or ""),
        issued_at=int(payload.get("issued_at") or 0),
        expires_at=int(payload.get("expires_at") or 0),
        rejection_reasons=tuple(dict.fromkeys(reasons)),
    )


def _canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Mapping[str, Any]) -> str:
    return _text_digest(_canonical(payload))


def _text_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _ascii_text(value: object) -> bool:
    return isinstance(value, str) and bool(value) and all(ord(char) < 128 for char in value)


def _sha256_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 71
        and value.startswith("sha256:")
        and all(char in "0123456789abcdef" for char in value[7:])
        and value[7:] != "0" * 64
    )


__all__ = [
    "DEFAULT_HANDSHAKE_TTL_SECONDS",
    "FAIL_HANDSHAKE_REQUEST_INVALID",
    "FAIL_HANDSHAKE_RESPONSE_REJECTED",
    "FAIL_HANDSHAKE_SIGNATURE_INVALID",
    "FAIL_HANDSHAKE_SIGNER_BINDING",
    "MAX_HANDSHAKE_TTL_SECONDS",
    "SIGNER_PEER_HANDSHAKE_SCHEMA_VERSION",
    "SIGNER_PEER_HANDSHAKE_RESPONSE_ATTESTATION_PREFIX",
    "SIGNER_PEER_HANDSHAKE_SIGNING_OPERATION",
    "SIGNER_PEER_HANDSHAKE_SIGNING_PREFIX",
    "SIGNER_PEER_HANDSHAKE_SIGNER_ROLE",
    "SignerPeerInstanceBinding",
    "SignerPeerProfileBinding",
    "VerifiedSignerPeerHandshake",
    "build_signer_peer_handshake_request",
    "canonical_signer_peer_response_attestation_input",
    "load_signer_peer_instance_binding",
    "signer_handshake_request_matches_instance",
    "validate_signer_peer_handshake_request",
    "verify_signer_peer_handshake_response",
]
