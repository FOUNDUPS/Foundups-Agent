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
from modules.communication.moltbot_bridge.src.reddog_signer_socket_schema import (
    SIGNER_SERVICE_RUN_PACKET_SCHEMA_VERSION,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_text,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


SIGNER_PEER_HANDSHAKE_SCHEMA_VERSION = "reddog_signer_peer_handshake.v1"
SIGNER_PEER_HANDSHAKE_SIGNING_PREFIX = "reddog-signer-peer-handshake.v1."
SIGNER_PEER_HANDSHAKE_RESPONSE_ATTESTATION_PREFIX = (
    "reddog-signer-peer-response-attestation.v1."
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
_RUN_PACKET_FIXED_FIELDS = {
    "run_mode": "signer_owned_cli_sidecar",
    "process_owner_requirement": "distinct_signer_os_principal",
    "redDog_must_not_spawn": True,
    "main_py_must_not_spawn": True,
    "shell_required": False,
    "shell_command": None,
    "no_secret_values_in_packet": True,
}
_RUN_PACKET_FIELDS = frozenset(
    {
        "schema_version", "run_mode", "repo_root", "working_directory",
        "python_module", "argv", "config_path", "config_digest", "socket_path",
        "profile_count", "provider_mode", "op_executable", "op_timeout_s",
        "ttl_seconds", "session_id", "process_owner_requirement",
        "redDog_must_not_spawn", "main_py_must_not_spawn", "shell_required",
        "shell_command", "no_secret_values_in_packet", "run_packet_id",
    }
)
_RUN_PACKET_CLI_MODULE = (
    "modules.communication.moltbot_bridge.src."
    "reddog_signer_socket_service_runtime_cli"
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


@dataclass(frozen=True)
class VerifiedSignerPeerHandshake:
    """Audit-safe result derived from a verified fresh challenge."""

    accepted: bool
    request_digest: str
    response_digest: str
    challenge_digest: str
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
    expected_session_id: str,
    expected_socket_path: Path | str,
    signer_profiles: tuple[SignerPeerProfileBinding, ...],
    manifest_selection: Mapping[str, Any],
    python_executable: Path | str,
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
    if not _selected_packet_valid(
        manifest_selection,
        packet,
        root=root,
        config_path=config,
        run_packet_path=packet_path,
        config_digest=expected_config_digest,
        run_packet_raw=raw,
    ):
        return None
    if not _run_packet_bindings_valid(
        packet,
        root=root,
        config_path=config,
        config_digest=expected_config_digest,
        session_id=expected_session_id,
        run_packet_path=packet_path,
        socket_path=Path(expected_socket_path).resolve(),
        python_executable=Path(python_executable).resolve(),
    ) or not _profile_bindings_valid(
        signer_profiles, packet.get("profile_count")
    ):
        return None
    return _peer_instance_binding(packet, signer_profiles)


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


def _selected_packet_valid(
    selection: Mapping[str, Any],
    packet: Mapping[str, Any],
    **bindings: Any,
) -> bool:
    return _selection_bindings_valid(
        selection,
        **bindings,
    ) and _run_packet_shape_valid(packet)


def _peer_instance_binding(
    packet: Mapping[str, Any],
    signer_profiles: tuple[SignerPeerProfileBinding, ...],
) -> SignerPeerInstanceBinding:
    return SignerPeerInstanceBinding(
        run_packet_id=str(packet["run_packet_id"]),
        config_digest=str(packet["config_digest"]),
        session_id=str(packet["session_id"]),
        socket_path=str(Path(str(packet["socket_path"])).resolve()),
        signer_profiles=tuple(
            sorted(signer_profiles, key=lambda item: item.signer_profile_id)
        ),
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
    return bool(_CHALLENGE_RE.fullmatch(str(payload["challenge"])))


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
            payload.get("config_digest") == binding.config_digest,
            payload.get("session_id") == binding.session_id,
            payload.get("socket_path_digest")
            == _text_digest(binding.socket_path),
            payload.get("signer_public_key") == profile.signer_public_key,
            payload.get("key_epoch") == profile.key_epoch,
        )
    )


def _run_packet_shape_valid(packet: object) -> bool:
    if not isinstance(packet, Mapping) or not _ascii_deep(packet):
        return False
    if set(packet) != _RUN_PACKET_FIELDS:
        return False
    if packet.get("schema_version") != SIGNER_SERVICE_RUN_PACKET_SCHEMA_VERSION:
        return False
    packet_id = packet.get("run_packet_id")
    if not _sha256_digest(packet_id):
        return False
    without_id = {key: value for key, value in packet.items() if key != "run_packet_id"}
    if packet_id != _digest(without_id):
        return False
    return all(packet.get(key) == value for key, value in _RUN_PACKET_FIXED_FIELDS.items())


def _run_packet_bindings_valid(
    packet: Mapping[str, Any],
    *,
    root: Path,
    config_path: Path,
    config_digest: str,
    session_id: str,
    run_packet_path: Path,
    socket_path: Path,
    python_executable: Path,
) -> bool:
    return all(
        (
            Path(str(packet.get("repo_root") or "")).resolve() == root,
            Path(str(packet.get("working_directory") or "")).resolve() == root,
            Path(str(packet.get("config_path") or "")).resolve() == config_path,
            packet.get("config_digest") == config_digest,
            packet.get("session_id") == session_id,
            Path(str(packet.get("socket_path") or "")).resolve() == socket_path,
            packet.get("python_module") == _RUN_PACKET_CLI_MODULE,
            _absolute_outside_repo(socket_path, root),
            _argv_bindings_valid(
                packet.get("argv"),
                root=root,
                config_path=config_path,
                config_digest=config_digest,
                session_id=session_id,
                run_packet_path=run_packet_path,
                op_executable=str(packet.get("op_executable") or ""),
                op_timeout_s=packet.get("op_timeout_s"),
                ttl_seconds=packet.get("ttl_seconds"),
                python_executable=python_executable,
            ),
        )
    )


def _argv_bindings_valid(
    value: object,
    *,
    root: Path,
    config_path: Path,
    config_digest: str,
    session_id: str,
    run_packet_path: Path,
    op_executable: str,
    op_timeout_s: object,
    ttl_seconds: object,
    python_executable: Path,
) -> bool:
    if (
        not isinstance(value, list)
        or len(value) != 19
        or not all(_ascii_text(item) for item in value)
        or value[1:3] != ["-m", _RUN_PACKET_CLI_MODULE]
        or Path(value[0]).resolve() != python_executable
    ):
        return False
    pairs: dict[str, str] = {}
    for index, item in enumerate(value[:-1]):
        if item.startswith("--"):
            if item in pairs:
                return False
            pairs[item] = str(value[index + 1])
    required = {
        "--repo-root": str(root),
        "--config": str(config_path),
        "--expected-config-digest": config_digest,
        "--run-packet": str(run_packet_path),
        "--op-executable": op_executable,
        "--op-timeout-s": _number_text(op_timeout_s),
        "--ttl-seconds": str(ttl_seconds),
        "--session-id": session_id,
    }
    return set(pairs) == set(required) and all(
        pairs.get(key) == expected for key, expected in required.items()
    )


def _selection_bindings_valid(
    value: object,
    *,
    root: Path,
    config_path: Path,
    run_packet_path: Path,
    config_digest: str,
    run_packet_raw: str,
) -> bool:
    if not isinstance(value, Mapping):
        return False
    required = {
        "manifest_id",
        "artifact_generation_digest",
        "config_digest",
        "config_raw_digest",
        "run_packet_digest",
        "repo_root",
        "runtime_root",
        "config_path",
        "run_packet_path",
    }
    return (
        set(value) == required
        and all(
            _sha256_digest(value.get(key))
            for key in (
                "manifest_id",
                "artifact_generation_digest",
                "config_digest",
                "config_raw_digest",
                "run_packet_digest",
            )
        )
        and value.get("config_digest") == config_digest
        and value.get("run_packet_digest") == _text_digest(run_packet_raw)
        and Path(str(value.get("repo_root") or "")).resolve() == root
        and Path(str(value.get("config_path") or "")).resolve() == config_path
        and Path(str(value.get("run_packet_path") or "")).resolve()
        == run_packet_path
    )


def _profile_bindings_valid(
    profiles: tuple[SignerPeerProfileBinding, ...],
    profile_count: object,
) -> bool:
    if not profiles or profile_count != len(profiles):
        return False
    ids = [item.signer_profile_id for item in profiles]
    if len(ids) != len(set(ids)):
        return False
    return all(
        _ascii_text(item.signer_profile_id)
        and _ascii_text(item.signer_public_key)
        and _ascii_text(item.key_epoch)
        for item in profiles
    )


def _absolute_outside_repo(value: object, root: Path) -> bool:
    text = str(value)
    if "\x00" in text or text.startswith("\\\\?\\") or text.startswith("//?/"):
        return False
    try:
        path = Path(text)
        resolved = path.resolve()
    except Exception:
        return False
    return path.is_absolute() and resolved != root and root not in resolved.parents


def _number_text(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return str(int(number)) if number.is_integer() else str(number)


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


def _ascii_deep(value: object) -> bool:
    if isinstance(value, str):
        return all(ord(char) < 128 for char in value)
    if isinstance(value, Mapping):
        return all(
            isinstance(key, str)
            and all(ord(char) < 128 for char in key)
            and _ascii_deep(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return all(_ascii_deep(item) for item in value)
    return value is None or isinstance(value, (bool, int, float))


def _sha256_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 71
        and value.startswith("sha256:")
        and all(char in "0123456789abcdef" for char in value[7:])
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
