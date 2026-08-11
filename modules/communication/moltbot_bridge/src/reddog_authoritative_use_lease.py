"""Opaque one-shot capability rehydrated from an external signer response."""

from __future__ import annotations

import secrets
import threading
from typing import Any, Callable

from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease_contract import (
    digest_mapping,
    validate_authoritative_use_lease_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    AUTHORITATIVE_USE_LEASE_AUDIT_ATTESTATION_PREFIX,
    canonical_signer_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
    constant_time_compare,
)


class AuthoritativeUseLease:
    """Unforgeable process-local handle; signed evidence remains registry-owned."""

    __slots__ = ("__token",)

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "AuthoritativeUseLease":
        raise TypeError("external_authoritative_use_lease_issuer_required")

    @property
    def expires_at_epoch(self) -> int:
        return _expires_at(self)

    def consume(self, *, effect_kind: str, effect_request_digest: str) -> bool:
        return consume_authoritative_use_lease(
            self,
            effect_kind=effect_kind,
            effect_request_digest=effect_request_digest,
        )

    def __copy__(self) -> "AuthoritativeUseLease":
        raise TypeError("authoritative_use_lease_copy_forbidden")

    def __deepcopy__(self, _memo: dict[int, Any]) -> "AuthoritativeUseLease":
        raise TypeError("authoritative_use_lease_copy_forbidden")

    def __reduce_ex__(self, _protocol: int) -> Any:
        raise TypeError("authoritative_use_lease_pickle_forbidden")


class _LeaseRegistry:
    """Process-local owner for opaque lease state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[
            str,
            tuple[
                AuthoritativeUseLease,
                int,
                str,
                str,
                Callable[[], bool],
                Callable[[], int],
            ],
        ] = {}

    def issue(
        self,
        expires_at: int,
        effect_kind: str,
        effect_request_digest: str,
        consume_authority: Callable[[], bool],
        trusted_now_epoch: Callable[[], int],
    ) -> AuthoritativeUseLease:
        token = secrets.token_urlsafe(32)
        capability = object.__new__(AuthoritativeUseLease)
        object.__setattr__(capability, "_AuthoritativeUseLease__token", token)
        with self._lock:
            self._records[token] = (
                capability,
                expires_at,
                effect_kind,
                effect_request_digest,
                consume_authority,
                trusted_now_epoch,
            )
        return capability

    def inspect(self, capability: object) -> tuple[int, str, str] | None:
        if type(capability) is not AuthoritativeUseLease:
            return None
        try:
            token = _token(capability)
        except AttributeError:
            return None
        with self._lock:
            record = self._records.get(token)
        if record is None or record[0] is not capability:
            return None
        try:
            return (record[1], record[2], record[3]) if record[5]() < record[1] else None
        except Exception:
            return None

    def consume(
        self,
        capability: object,
        *,
        effect_kind: str,
        effect_request_digest: str,
    ) -> bool:
        if type(capability) is not AuthoritativeUseLease:
            return False
        try:
            token = _token(capability)
        except AttributeError:
            return False
        with self._lock:
            record = self._records.get(token)
            if not _record_matches(
                record, capability, effect_kind, effect_request_digest
            ):
                return False
            self._records.pop(token, None)
        try:
            return record[5]() < record[1] and record[4]() is True
        except Exception:
            return False


_LEASES = _LeaseRegistry()


def rehydrate_external_authoritative_use_lease(
    *,
    request: SigningRequest,
    response: SigningResponse,
    signature_verifier: SignatureVerifier,
    consume_evidence_once: Callable[[str], bool],
    consume_authority_once: Callable[[], bool],
    trusted_now_epoch: Callable[[], int],
) -> AuthoritativeUseLease | None:
    """Verify external evidence and release one non-serializable capability."""

    try:
        now_epoch = trusted_now_epoch()
    except Exception:
        return None
    payload = validate_authoritative_use_lease_request(request, now_epoch=now_epoch)
    if payload is None or not _response_valid(request, response, signature_verifier):
        return None
    evidence_digest = digest_mapping(
        {"request": request.to_dict(), "response": response.to_dict()}
    )
    try:
        if consume_evidence_once(evidence_digest) is not True:
            return None
    except Exception:
        return None
    return _LEASES.issue(
        int(payload["expires_at"]),
        str(payload["effect_kind"]),
        str(payload["effect_request_digest"]),
        consume_authority_once,
        trusted_now_epoch,
    )


def _response_valid(
    request: SigningRequest,
    response: SigningResponse,
    verifier: SignatureVerifier,
) -> bool:
    if type(response) is not SigningResponse or response.accepted is not True:
        return False
    expected_fingerprint = public_key_fingerprint(request.signer_public_key)
    public_bindings = all(
        (
            constant_time_compare(
                response.signer_public_key, request.signer_public_key
            ),
            constant_time_compare(response.key_epoch, request.key_epoch),
            constant_time_compare(response.key_fingerprint, expected_fingerprint),
            bool(response.audit_mac),
            bool(response.audit_attestation_signature),
            response.boundary_attested is True,
            response.requester_identity_attested is True,
            response.signer_loads_no_untrusted_code is True,
            response.no_secret_material_returned is True,
        )
    )
    if not public_bindings:
        return False
    try:
        attestation = canonical_signer_audit_attestation_input(
            signing_input=request.signing_input,
            signature=response.signature,
            audit_mac=response.audit_mac,
            signer_public_key=response.signer_public_key,
            key_epoch=response.key_epoch,
            requester_principal_id=request.requester_principal_id,
            domain_prefix=AUTHORITATIVE_USE_LEASE_AUDIT_ATTESTATION_PREFIX,
        )
        return bool(
            verifier.verify(
                response.signer_public_key, request.signing_input, response.signature
            )
            and verifier.verify(
                response.signer_public_key,
                attestation,
                response.audit_attestation_signature,
            )
        )
    except Exception:
        return False


def is_authoritative_use_lease(
    value: Any, *, effect_kind: str = "", effect_request_digest: str = ""
) -> bool:
    record = _LEASES.inspect(value)
    return bool(
        record is not None
        and constant_time_compare(record[1], effect_kind)
        and constant_time_compare(record[2], effect_request_digest)
    )


def consume_authoritative_use_lease(
    value: Any, *, effect_kind: str = "", effect_request_digest: str = ""
) -> bool:
    return _LEASES.consume(
        value,
        effect_kind=effect_kind,
        effect_request_digest=effect_request_digest,
    )


def _expires_at(value: Any) -> int:
    record = _LEASES.inspect(value)
    if record is None:
        raise ValueError("external_authoritative_use_lease_unavailable")
    return record[0]


def _token(capability: AuthoritativeUseLease) -> str:
    return object.__getattribute__(capability, "_AuthoritativeUseLease__token")


def _record_matches(
    record: tuple[Any, ...] | None,
    capability: object,
    effect_kind: str,
    effect_request_digest: str,
) -> bool:
    return bool(
        record is not None
        and record[0] is capability
        and constant_time_compare(record[2], effect_kind)
        and constant_time_compare(record[3], effect_request_digest)
    )


__all__ = [
    "AuthoritativeUseLease",
    "consume_authoritative_use_lease",
    "is_authoritative_use_lease",
    "rehydrate_external_authoritative_use_lease",
]
