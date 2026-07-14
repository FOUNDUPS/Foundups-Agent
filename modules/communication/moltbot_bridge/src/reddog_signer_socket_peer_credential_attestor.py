"""Kernel peer-credential attestor for the isolated RedDog signer socket.

Slice: REDDOG_SIGNER_SOCKET_PEER_CREDENTIAL_ATTESTOR_PHASE1

This module converts local socket peer credentials into the existing
``SignerPeerAttestation`` record using an injected UID/GID policy. It never
reads request-body identity, spawns processes, shells out, reads files, mutates
the repository, enqueues OpenClaw, dispatches Hermes, or re-indexes HoloIndex.
Unsupported platforms fail closed.
"""

from __future__ import annotations

import socket
import struct
from dataclasses import dataclass, field
from typing import Mapping, Optional, Protocol

from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
)


PEER_CREDENTIAL_SOURCE_SO_PEERCRED = "kernel_so_peercred"
PEER_CREDENTIAL_SOURCE_GETPEEREID = "kernel_getpeereid"

FAIL_PEER_CREDENTIAL_POLICY_INVALID = "FAIL_PEER_CREDENTIAL_POLICY_INVALID"
FAIL_PEER_CREDENTIAL_UNAVAILABLE = "FAIL_PEER_CREDENTIAL_UNAVAILABLE"
FAIL_PEER_CREDENTIAL_READ_FAILED = "FAIL_PEER_CREDENTIAL_READ_FAILED"
FAIL_PEER_CREDENTIAL_MALFORMED = "FAIL_PEER_CREDENTIAL_MALFORMED"
FAIL_PEER_CREDENTIAL_UID_NOT_ALLOWED = "FAIL_PEER_CREDENTIAL_UID_NOT_ALLOWED"
FAIL_PEER_CREDENTIAL_GID_NOT_ALLOWED = "FAIL_PEER_CREDENTIAL_GID_NOT_ALLOWED"

_SO_PEERCRED: Optional[int] = getattr(socket, "SO_PEERCRED", None)
_PEERCRED_STRUCT = "3i"


class PeerCredentialSocket(Protocol):
    """Small subset of socket APIs needed for peer credential attestation."""

    def getsockopt(self, level: int, optname: int, buflen: int) -> bytes:
        """Return socket option bytes."""


@dataclass(frozen=True)
class PeerCredentialPolicy:
    """Signer-owned mapping from kernel UID/GID to RedDog principal id."""

    uid_to_principal: Mapping[int, str]
    allowed_gids: tuple[int, ...] = ()
    transport: str = "unix_socket"
    credential_source_prefix: str = "kernel_peer_credential"


@dataclass(frozen=True)
class KernelPeerCredentialAttestor:
    """Attest requester identity from kernel peer credentials."""

    policy: PeerCredentialPolicy = field(default_factory=lambda: PeerCredentialPolicy({}))

    def attest(self, connection: PeerCredentialSocket) -> SignerPeerAttestation:
        if not _policy_valid(self.policy):
            return _reject(FAIL_PEER_CREDENTIAL_POLICY_INVALID, self.policy)
        credential = _read_peer_credential(connection)
        if credential is None:
            return _reject(FAIL_PEER_CREDENTIAL_UNAVAILABLE, self.policy)
        source, pid, uid, gid = credential
        if uid < 0 or gid < 0 or pid < 0:
            return _reject(FAIL_PEER_CREDENTIAL_MALFORMED, self.policy)
        principal = self.policy.uid_to_principal.get(uid)
        if not principal:
            return _reject(FAIL_PEER_CREDENTIAL_UID_NOT_ALLOWED, self.policy)
        if self.policy.allowed_gids and gid not in self.policy.allowed_gids:
            return _reject(FAIL_PEER_CREDENTIAL_GID_NOT_ALLOWED, self.policy)
        if not _is_ascii(principal):
            return _reject(FAIL_PEER_CREDENTIAL_POLICY_INVALID, self.policy)
        return SignerPeerAttestation(
            peer_principal_id=principal,
            transport=self.policy.transport,
            credential_source=(
                f"{self.policy.credential_source_prefix}:{source}:pid={pid}:uid={uid}:gid={gid}"
            ),
            boundary_attested=True,
        )


def _read_peer_credential(connection: PeerCredentialSocket) -> tuple[str, int, int, int] | None:
    if _SO_PEERCRED is not None:
        try:
            raw = connection.getsockopt(
                socket.SOL_SOCKET,
                int(_SO_PEERCRED),
                struct.calcsize(_PEERCRED_STRUCT),
            )
            if not isinstance(raw, (bytes, bytearray)) or len(raw) != struct.calcsize(_PEERCRED_STRUCT):
                return None
            pid, uid, gid = struct.unpack(_PEERCRED_STRUCT, raw)
            return (PEER_CREDENTIAL_SOURCE_SO_PEERCRED, int(pid), int(uid), int(gid))
        except Exception:
            return None
    getpeereid = getattr(connection, "getpeereid", None)
    if callable(getpeereid):
        try:
            uid, gid = getpeereid()
            return (PEER_CREDENTIAL_SOURCE_GETPEEREID, 0, int(uid), int(gid))
        except Exception:
            return None
    return None


def _policy_valid(policy: PeerCredentialPolicy) -> bool:
    if not isinstance(policy, PeerCredentialPolicy) or not policy.uid_to_principal:
        return False
    if not _is_ascii(policy.transport) or not _is_ascii(policy.credential_source_prefix):
        return False
    for uid, principal in policy.uid_to_principal.items():
        if not isinstance(uid, int) or uid < 0 or not _is_ascii(principal) or not principal:
            return False
    return all(isinstance(gid, int) and gid >= 0 for gid in policy.allowed_gids)


def _reject(code: str, policy: PeerCredentialPolicy) -> SignerPeerAttestation:
    transport = (
        policy.transport
        if isinstance(policy, PeerCredentialPolicy) and _is_ascii(policy.transport)
        else "local_socket"
    )
    return SignerPeerAttestation(
        peer_principal_id="",
        transport=transport,
        credential_source=str(code),
        boundary_attested=False,
    )


def _is_ascii(value: object) -> bool:
    return isinstance(value, str) and all(ord(char) < 128 for char in value)


__all__ = [
    "FAIL_PEER_CREDENTIAL_GID_NOT_ALLOWED",
    "FAIL_PEER_CREDENTIAL_MALFORMED",
    "FAIL_PEER_CREDENTIAL_POLICY_INVALID",
    "FAIL_PEER_CREDENTIAL_READ_FAILED",
    "FAIL_PEER_CREDENTIAL_UID_NOT_ALLOWED",
    "FAIL_PEER_CREDENTIAL_UNAVAILABLE",
    "KernelPeerCredentialAttestor",
    "PEER_CREDENTIAL_SOURCE_GETPEEREID",
    "PEER_CREDENTIAL_SOURCE_SO_PEERCRED",
    "PeerCredentialPolicy",
]
