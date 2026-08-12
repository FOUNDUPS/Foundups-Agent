"""Opaque elevated-consensus capabilities consumed at signer key release."""

from __future__ import annotations

import copy
import hmac
import threading
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_contract import (
    canonical_authority_request_digest,
    canonical_elevated_signing_request_digest,
)


class ConsensusNonceAuthority(Protocol):
    def reserve(self, nonce: str, *, expires_at: int, subject: str) -> str | None: ...

    def commit(self, reservation: str) -> None: ...

    def rollback(self, reservation: str) -> None: ...


class _OpaqueCapability:
    __slots__ = ("__weakref__",)

    def __new__(cls, *_args: Any, **_kwargs: Any):
        raise TypeError("elevated_consensus_direct_construction_forbidden")

    def __copy__(self) -> Any:
        raise TypeError("elevated_consensus_copy_forbidden")

    def __deepcopy__(self, _memo: Any) -> Any:
        raise TypeError("elevated_consensus_copy_forbidden")

    def __reduce__(self) -> Any:
        raise TypeError("elevated_consensus_pickle_forbidden")


class VerifiedElevatedAuthorityConsensusCapability(_OpaqueCapability):
    """Verified aggregate awaiting exact signing-request binding."""


class VerifiedElevatedAuthoritySigningPermit(_OpaqueCapability):
    """Two-use permit bound to exact identity and work-authority requests."""


@dataclass(frozen=True)
class _CapabilitySeal:
    authority_request_digest: str
    consensus_receipt_digest: str
    expires_at: int
    authorized_signing_request_digests: frozenset[str]
    consensus_proof: Mapping[str, Any]


@dataclass
class _PermitSeal:
    signing_request_digests: set[str]
    consensus_receipt_digest: str
    expires_at: int
    consensus_proof: Mapping[str, Any]


_LOCK = threading.Lock()
_CAPABILITIES: WeakKeyDictionary[
    VerifiedElevatedAuthorityConsensusCapability, _CapabilitySeal
] = WeakKeyDictionary()
_PERMITS: WeakKeyDictionary[
    VerifiedElevatedAuthoritySigningPermit, _PermitSeal
] = WeakKeyDictionary()


def _mint_elevated_authority_consensus_capability(
    *, authority_request_digest: str, consensus_receipt_digest: str,
    expires_at: int,
    authorized_signing_request_digests: frozenset[str],
    consensus_proof: Mapping[str, Any],
) -> VerifiedElevatedAuthorityConsensusCapability:
    capability = object.__new__(VerifiedElevatedAuthorityConsensusCapability)
    with _LOCK:
        _CAPABILITIES[capability] = _CapabilitySeal(
            authority_request_digest=authority_request_digest,
            consensus_receipt_digest=consensus_receipt_digest,
            expires_at=expires_at,
            authorized_signing_request_digests=authorized_signing_request_digests,
            consensus_proof=copy.deepcopy(dict(consensus_proof)),
        )
    return capability


def prepare_elevated_authority_signing_permit(
    capability: Any, *, authority_request: Any,
    signing_requests: Sequence[Any], now: int,
) -> VerifiedElevatedAuthoritySigningPermit | None:
    """Move one aggregate capability onto exactly two signer requests."""

    if type(capability) is not VerifiedElevatedAuthorityConsensusCapability:
        return None
    try:
        request_digest = canonical_authority_request_digest(authority_request)
        expected_consensus = str(authority_request.consensus_receipt_digest or "")
        requests = tuple(signing_requests)
        request_digests = {_signing_request_digest(item) for item in requests}
        if not _signing_requests_match(requests, authority_request):
            return None
    except Exception:
        return None
    with _LOCK:
        seal = _CAPABILITIES.get(capability)
        if seal is None or seal.expires_at <= now:
            return None
        if not (
            hmac.compare_digest(seal.authority_request_digest, request_digest)
            and hmac.compare_digest(seal.consensus_receipt_digest, expected_consensus)
            and request_digests == seal.authorized_signing_request_digests
        ):
            return None
        _CAPABILITIES.pop(capability, None)
        permit = object.__new__(VerifiedElevatedAuthoritySigningPermit)
        _PERMITS[permit] = _PermitSeal(
            signing_request_digests=request_digests,
            consensus_receipt_digest=seal.consensus_receipt_digest,
            expires_at=seal.expires_at,
            consensus_proof=copy.deepcopy(dict(seal.consensus_proof)),
        )
    return permit


def consume_elevated_authority_signing_permit(
    permit: Any, *, signing_request: Any, now: int,
) -> Mapping[str, Any] | None:
    """Consume one exact child request and durably commit nonce on first use."""

    if type(permit) is not VerifiedElevatedAuthoritySigningPermit:
        return None
    try:
        request_digest = _signing_request_digest(signing_request)
    except Exception:
        return None
    with _LOCK:
        seal = _PERMITS.get(permit)
        if seal is None or seal.expires_at <= now:
            return None
        if request_digest not in seal.signing_request_digests:
            return None
        seal.signing_request_digests.remove(request_digest)
        if not seal.signing_request_digests:
            _PERMITS.pop(permit, None)
        return {
            **copy.deepcopy(dict(seal.consensus_proof)),
            "target_signing_request": signing_request.to_dict(),
        }


def discard_elevated_authority_signing_permit(permit: Any) -> None:
    if type(permit) is VerifiedElevatedAuthoritySigningPermit:
        with _LOCK:
            _PERMITS.pop(permit, None)


def _signing_request_digest(request: Any) -> str:
    return canonical_elevated_signing_request_digest(request)


def _signing_requests_match(requests: tuple[Any, ...], authority: Any) -> bool:
    if len(requests) != 2:
        return False
    expected = {
        ("principal", authority.principal_public_key, authority.identity_nonce, "delegate_reddog_identity"),
        ("reddog", authority.reddog_public_key, authority.work_authority_nonce, authority.requested_operation),
    }
    actual = {
        (item.signer_role, item.signer_public_key, item.nonce, item.requested_operation)
        for item in requests
        if getattr(item, "authority_tier", None) == "HIGH"
        and getattr(item, "key_epoch", None) == authority.key_epoch
        and getattr(item, "requester_principal_id", None) == authority.principal_id
        and getattr(item, "consensus_receipt_digest", None)
        == authority.consensus_receipt_digest
    }
    return actual == expected and len(actual) == len(requests)


__all__ = [
    "ConsensusNonceAuthority",
    "VerifiedElevatedAuthorityConsensusCapability",
    "VerifiedElevatedAuthoritySigningPermit",
    "consume_elevated_authority_signing_permit",
    "discard_elevated_authority_signing_permit",
    "prepare_elevated_authority_signing_permit",
]
