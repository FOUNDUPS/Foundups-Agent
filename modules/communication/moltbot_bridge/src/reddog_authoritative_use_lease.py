"""Opaque one-shot capability rehydrated from an external signer response."""

from __future__ import annotations

import secrets
import threading
import time
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease_contract import (
    authoritative_use_replay_binding,
    digest_mapping,
    validate_authoritative_use_lease_request,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    AUTHORITATIVE_USE_LEASE_AUDIT_ATTESTATION_PREFIX,
    canonical_signer_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_runtime_binding import (
    SignerCurrentGenerationRuntimeAuthority,
    SignerCurrentGenerationRuntimeBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_nonce_store import (
    DurableSignerSecretGrantNonceStore,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
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
            str, tuple[AuthoritativeUseLease, int, float, str, str]
        ] = {}

    def issue(
        self, expires_at: int, effect_kind: str, effect_request_digest: str
    ) -> AuthoritativeUseLease:
        token = secrets.token_urlsafe(32)
        capability = object.__new__(AuthoritativeUseLease)
        object.__setattr__(capability, "_AuthoritativeUseLease__token", token)
        monotonic_deadline = time.monotonic() + max(
            0, expires_at - int(time.time())
        )
        with self._lock:
            self._records[token] = (
                capability,
                expires_at,
                monotonic_deadline,
                effect_kind,
                effect_request_digest,
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
            if _record_expired(record):
                self._records.pop(token, None)
                return None
            return record[1], record[3], record[4]

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
            if _record_expired(record):
                self._records.pop(token, None)
                return False
            self._records.pop(token, None)
        return True


_LEASES = _LeaseRegistry()


def _rehydrate_external_authoritative_use_lease(
    *,
    request: SigningRequest,
    response: SigningResponse,
    current_generation_authority: SignerCurrentGenerationRuntimeAuthority,
    replay_store: DurableSignerSecretGrantNonceStore,
    now_epoch: int,
) -> AuthoritativeUseLease | None:
    """Verify external evidence and release one non-serializable capability."""

    if (
        type(replay_store) is not DurableSignerSecretGrantNonceStore
        or type(current_generation_authority)
        is not SignerCurrentGenerationRuntimeAuthority
    ):
        return None
    payload = validate_authoritative_use_lease_request(request, now_epoch=now_epoch)
    if payload is None or not _replay_store_matches(payload, replay_store):
        return None
    try:
        current_generation = current_generation_authority.resolve(
            now_epoch=now_epoch,
            signer_profile_id=str(payload["signer_profile_id"]),
        )
    except Exception:
        return None
    if (
        not _current_generation_matches(payload, current_generation, now_epoch)
        or not _response_valid(request, response)
    ):
        return None
    evidence_digest = digest_mapping(
        {"request": request.to_dict(), "response": response.to_dict()}
    )
    if not replay_store.consume_authoritative_use_lease(
        evidence_digest=evidence_digest,
        lease_nonce=str(payload["lease_nonce"]),
        expires_at=int(payload["expires_at"]),
    ):
        return None
    return _LEASES.issue(
        int(payload["expires_at"]),
        str(payload["effect_kind"]),
        str(payload["effect_request_digest"]),
    )


def _current_generation_matches(
    payload: Mapping[str, Any],
    binding: SignerCurrentGenerationRuntimeBinding,
    now_epoch: int,
) -> bool:
    if (
        type(binding) is not SignerCurrentGenerationRuntimeBinding
        or binding.accepted is not True
        or binding.selection_expires_at is None
        or now_epoch >= binding.selection_expires_at
        or int(payload["expires_at"]) > binding.selection_expires_at
    ):
        return False
    expected = {
        "manifest_id": binding.manifest_id,
        "artifact_generation_digest": binding.artifact_generation_digest,
        "generation": binding.generation,
        "generation_revision": binding.generation_revision,
        "owner_config_id": binding.owner_config_id,
        "run_packet_id": binding.run_packet_id,
        "config_digest": binding.config_digest,
        "session_id": binding.session_id,
        "socket_path_digest": binding.socket_path_digest,
        "signer_profile_id": binding.signer_profile_id,
        "signer_public_key": binding.signer_public_key,
        "key_epoch": binding.key_epoch,
    }
    return all(payload.get(key) == value for key, value in expected.items())


def _replay_store_matches(
    payload: Mapping[str, Any], store: DurableSignerSecretGrantNonceStore
) -> bool:
    signed = authoritative_use_replay_binding(payload)
    expected = {
        "replay_store_binding_digest": store.replay_store_binding_digest,
        "replay_store_id": store.replay_store_id,
        "replay_store_durability_receipt_id": store.durability_receipt_id,
        "replay_store_instance_digest": store.replay_store_instance_digest,
    }
    return signed is not None and all(
        constant_time_compare(signed[key], value)
        for key, value in expected.items()
    )


def _response_valid(request: SigningRequest, response: SigningResponse) -> bool:
    if type(response) is not SigningResponse or response.accepted is not True:
        return False
    expected_fingerprint = public_key_fingerprint(request.signer_public_key)
    if not all(
        (
            constant_time_compare(response.signer_public_key, request.signer_public_key),
            constant_time_compare(response.key_epoch, request.key_epoch),
            constant_time_compare(response.key_fingerprint, expected_fingerprint),
            bool(response.audit_mac),
            bool(response.audit_attestation_signature),
            response.boundary_attested is True,
            response.requester_identity_attested is True,
            response.signer_loads_no_untrusted_code is True,
            response.no_secret_material_returned is True,
        )
    ):
        return False
    verifier = Ed25519SignatureVerifier()
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
        and constant_time_compare(record[3], effect_kind)
        and constant_time_compare(record[4], effect_request_digest)
    )


def _record_expired(record: tuple[Any, ...]) -> bool:
    return bool(
        int(time.time()) >= int(record[1])
        or time.monotonic() >= float(record[2])
    )


__all__ = [
    "AuthoritativeUseLease",
    "consume_authoritative_use_lease",
    "is_authoritative_use_lease",
]
