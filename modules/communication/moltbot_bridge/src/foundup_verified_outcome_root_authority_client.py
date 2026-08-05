"""Signer-side client capability for the root outcome authority service."""

from __future__ import annotations

import socket
import stat
import struct
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import (
    RootVerifiedOutcomeSigningAuthority,
    validate_root_verified_outcome_descriptor_public,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_protocol import (
    MAX_MESSAGE_BYTES,
    OP_COMMIT,
    OP_RESERVE,
    RootAuthorityRequest,
    canonical_signer_instance_input,
    request_id_for,
    response_from_bytes,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    _build_process_local_registry,
)


@dataclass(frozen=True)
class _SocketExchangeState:
    path: Path
    expected_uid: int
    timeout_s: float


_issue_exchange, _lookup_exchange = _build_process_local_registry(
    "verified_outcome_root_socket_exchange_unverified"
)


class RootAuthorityExchange:
    """Opaque root-authenticated transport capability."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "RootAuthorityExchange":
        raise TypeError("root_authority_socket_exchange_factory_required")

    def exchange(self, payload: bytes) -> bytes:
        state = _lookup_exchange(self)
        return _root_socket_roundtrip(
            state.path, payload, state.expected_uid, state.timeout_s
        )


@dataclass(frozen=True)
class _ClientState:
    descriptor: Mapping[str, Any]
    owner_config_id: str
    exchange: RootAuthorityExchange
    seal: object


@dataclass(frozen=True)
class _ClientReservation:
    request: RootAuthorityRequest
    reservation_id: str
    seal: object


_issue_client, _lookup_client = _build_process_local_registry(
    "verified_outcome_root_service_client_unverified"
)
del _build_process_local_registry


def _create_service_backed_outcome_authority(
    descriptor: Mapping[str, Any],
    *,
    owner_config_id: str,
    exchange: RootAuthorityExchange,
    now_epoch: int,
) -> RootVerifiedOutcomeSigningAuthority:
    """Mint the existing opaque signer capability from a root-authenticated RPC."""

    if not _sha256(owner_config_id) or type(exchange) is not RootAuthorityExchange:
        raise ValueError("verified_outcome_root_service_client_invalid")
    exchange_state = _lookup_exchange(exchange)
    if exchange_state.expected_uid != 0:
        raise ValueError("verified_outcome_root_service_uid_invalid")
    checked = validate_root_verified_outcome_descriptor_public(
        descriptor, now_epoch=now_epoch
    )
    authority = object.__new__(RootVerifiedOutcomeSigningAuthority)
    _issue_client(
        authority,
        _ClientState(
            descriptor=checked,
            owner_config_id=owner_config_id,
            exchange=exchange,
            seal=object(),
        ),
    )
    return authority


def client_authority_bindings(authority: object) -> Mapping[str, str]:
    state = _lookup_client(authority)
    descriptor = state.descriptor
    return {
        "descriptor_id": str(descriptor["descriptor_id"]),
        "owner_config_id": state.owner_config_id,
        "issuer_principal_id": str(descriptor["issuer_principal_id"]),
        "reddog_id": str(descriptor["reddog_id"]),
        "foundup_id": str(descriptor["foundup_id"]),
        "authority_tier": str(descriptor["authority_tier"]),
        "consensus_receipt_digest": str(descriptor["consensus_receipt_digest"]),
        "signer_public_key": str(descriptor["signer_public_key"]),
        "signer_key_epoch": str(descriptor["signer_key_epoch"]),
        "signer_run_packet_id": str(descriptor["signer_run_packet_id"]),
        "signer_config_digest": str(descriptor["signer_config_digest"]),
        "signer_session_id": str(descriptor["signer_session_id"]),
        "signer_manifest_id": str(descriptor["signer_manifest_id"]),
        "signer_artifact_generation_digest": str(
            descriptor["signer_artifact_generation_digest"]
        ),
    }


def reserve_service_authority(
    authority: object,
    *,
    receipt_id: str,
    work_order_id: str,
    evidence_digest: str,
    issued_at: int,
    signer_instance_signature: str,
) -> object | None:
    try:
        state = _lookup_client(authority)
        grant = next(
            item
            for item in state.descriptor["grants"]
            if item["evidence_digest"] == evidence_digest
        )
        request = _request(
            state,
            grant,
            operation=OP_RESERVE,
            receipt_id=receipt_id,
            work_order_id=work_order_id,
            evidence_digest=evidence_digest,
            issued_at=issued_at,
            signer_instance_signature=signer_instance_signature,
        )
        response = response_from_bytes(state.exchange.exchange(request.to_bytes()))
        if not _response_matches(
            response, request, expected_state="RESERVED_BURNED"
        ):
            return None
        return _ClientReservation(request, str(response.reservation_id), state.seal)
    except Exception:
        return None


def commit_service_authority(
    authority: object,
    reservation: object,
    signature_digest: str,
    signer_instance_signature: str,
) -> None:
    state = _lookup_client(authority)
    if (
        not isinstance(reservation, _ClientReservation)
        or reservation.seal is not state.seal
        or not _sha256(signature_digest)
        or not _signature(signer_instance_signature)
    ):
        raise ValueError("verified_outcome_root_service_reservation_invalid")
    request = replace(
        reservation.request,
        operation=OP_COMMIT,
        reservation_id=reservation.reservation_id,
        signature_digest=signature_digest,
        signer_instance_signature=signer_instance_signature,
        request_id="sha256:" + ("0" * 64),
    )
    request = replace(request, request_id=request_id_for(asdict(request)))
    response = response_from_bytes(state.exchange.exchange(request.to_bytes()))
    if not _response_matches(
        response,
        request,
        expected_state="COMMITTED",
        expected_reservation_id=reservation.reservation_id,
    ):
        raise ValueError("verified_outcome_root_service_commit_rejected")


def rollback_service_authority(authority: object, reservation: object) -> None:
    state = _lookup_client(authority)
    if not isinstance(reservation, _ClientReservation) or reservation.seal is not state.seal:
        raise ValueError("verified_outcome_root_service_reservation_invalid")
    # Reserve is deliberately burned at the root before the signer sees it.


def reserve_service_proof_input(
    authority: object,
    *,
    receipt_id: str,
    work_order_id: str,
    evidence_digest: str,
    issued_at: int,
) -> str:
    state = _lookup_client(authority)
    grant = next(
        item
        for item in state.descriptor["grants"]
        if item["evidence_digest"] == evidence_digest
    )
    return canonical_signer_instance_input(
        _request(
            state,
            grant,
            operation=OP_RESERVE,
            receipt_id=receipt_id,
            work_order_id=work_order_id,
            evidence_digest=evidence_digest,
            issued_at=issued_at,
            signer_instance_signature=_placeholder_signature(),
        )
    )


def commit_service_proof_input(
    authority: object, reservation: object, signature_digest: str
) -> str:
    state = _lookup_client(authority)
    if (
        not isinstance(reservation, _ClientReservation)
        or reservation.seal is not state.seal
        or not _sha256(signature_digest)
    ):
        raise ValueError("verified_outcome_root_service_reservation_invalid")
    request = replace(
        reservation.request,
        operation=OP_COMMIT,
        reservation_id=reservation.reservation_id,
        signature_digest=signature_digest,
        signer_instance_signature=_placeholder_signature(),
        request_id="sha256:" + ("0" * 64),
    )
    return canonical_signer_instance_input(request)


def build_root_authority_socket_exchange(
    *,
    repo_root: Path | str,
    socket_path: Path | str,
    expected_server_uid: int = 0,
    timeout_s: float = 5.0,
) -> RootAuthorityExchange:
    """Build a client that verifies the root service through SO_PEERCRED."""

    root = Path(repo_root).resolve()
    target = Path(socket_path)
    if (
        not target.is_absolute()
        or root == target.resolve()
        or root in target.resolve().parents
        or type(expected_server_uid) is not int
        or expected_server_uid < 0
        or not 0 < timeout_s <= 30
    ):
        raise ValueError("root_authority_socket_path_invalid")
    resolved = target.resolve()
    _require_protected_socket(resolved, expected_server_uid)

    exchange = object.__new__(RootAuthorityExchange)
    _issue_exchange(
        exchange,
        _SocketExchangeState(resolved, expected_server_uid, timeout_s),
    )
    return exchange


def _request(
    state: _ClientState,
    grant: Mapping[str, Any],
    *,
    operation: str,
    receipt_id: str,
    work_order_id: str,
    evidence_digest: str,
    issued_at: int,
    signer_instance_signature: str,
) -> RootAuthorityRequest:
    request = RootAuthorityRequest(
        operation=operation,
        request_id="sha256:" + ("0" * 64),
        descriptor_id=str(state.descriptor["descriptor_id"]),
        owner_config_id=state.owner_config_id,
        authorization_id=str(grant["authorization_id"]),
        receipt_id=receipt_id,
        work_order_id=work_order_id,
        evidence_digest=evidence_digest,
        issued_at=issued_at,
        signer_instance_signature=signer_instance_signature,
    )
    return replace(request, request_id=request_id_for(asdict(request)))


def _response_matches(
    response: Any,
    request: RootAuthorityRequest,
    *,
    expected_state: str,
    expected_reservation_id: str | None = None,
) -> bool:
    return bool(
        response.accepted
        and response.request_id == request.request_id
        and response.descriptor_id == request.descriptor_id
        and response.owner_config_id == request.owner_config_id
        and response.authorization_id == request.authorization_id
        and response.state == expected_state
        and (
            expected_reservation_id is None
            or response.reservation_id == expected_reservation_id
        )
    )


def _root_socket_roundtrip(
    path: Path, payload: bytes, expected_uid: int, timeout_s: float
) -> bytes:
    if not hasattr(socket, "AF_UNIX") or not hasattr(socket, "SO_PEERCRED"):
        raise OSError("root_authority_peer_credential_unavailable")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as handle:
        handle.settimeout(timeout_s)
        handle.connect(str(path))
        raw = handle.getsockopt(
            socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")
        )
        _pid, uid, _gid = struct.unpack("3i", raw)
        if uid != expected_uid:
            raise OSError("root_authority_server_uid_mismatch")
        handle.sendall(payload)
        handle.shutdown(socket.SHUT_WR)
        chunks: list[bytes] = []
        total = 0
        while total <= MAX_MESSAGE_BYTES:
            chunk = handle.recv(min(8192, MAX_MESSAGE_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        if total == 0 or total > MAX_MESSAGE_BYTES:
            raise OSError("root_authority_response_size_invalid")
        return b"".join(chunks)


def _require_protected_socket(path: Path, expected_uid: int) -> None:
    if not path.exists():
        raise ValueError("root_authority_socket_unavailable")
    current = path.lstat()
    parent = path.parent.lstat()
    if (
        path.is_symlink()
        or path.parent.is_symlink()
        or not stat.S_ISSOCK(current.st_mode)
        or current.st_uid != expected_uid
        or parent.st_uid != expected_uid
        or stat.S_IMODE(parent.st_mode) & 0o022
    ):
        raise ValueError("root_authority_socket_ownership_invalid")


def _sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


def _signature(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("ed25519-sig-v1:") and value.isascii()


def _placeholder_signature() -> str:
    return "ed25519-sig-v1:" + ("A" * 86)


__all__ = [
    "RootAuthorityExchange",
    "build_root_authority_socket_exchange",
    "client_authority_bindings",
    "commit_service_proof_input",
    "commit_service_authority",
    "reserve_service_authority",
    "reserve_service_proof_input",
    "rollback_service_authority",
]
