"""Authenticated durable provenance for RedDog topology-proposer calls.

This verifier never signs or creates keys.  It binds an externally signed,
short-lived authority record to one exact content-addressed proposer call,
consumes its nonce once, and persists the accepted receipt before returning a
typed verified result.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping, Protocol, Sequence

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
    canonical_signing_input,
    constant_time_compare,
)

from .model_autoresearch_configured_gateway_evidence import (
    ConfiguredGatewayReceiptStore,
    DurableExactPublicationStore,
    digest_payload,
)
from .model_topology_proposal_lm_studio import (
    LMStudioTopologyProposalCallReceipt,
    LMStudioTopologyProposalResult,
    propose_lm_studio_shadow_topologies,
    rehydrate_lm_studio_topology_proposal_call_receipt,
)
from .model_topology_proposal_admission import (
    ModelTopologyProposalAdmissionReceipt,
    rehydrate_model_topology_proposal_admission_receipt,
)


SCHEMA_VERSION = "model_topology_proposer_authenticated_provenance.v1"
SIGNING_PREFIX = "reddog-topology-proposer-provenance.v1"
SIGNER_ROLE = "autoresearch_proposer"
MAX_RECEIPT_TTL_SECONDS = 900
MAX_VERIFICATION_LEEWAY_SECONDS = 60
MAX_LIVE_CAPABILITIES = 1_024


class TopologyProposerKeyResolver(Protocol):
    def resolve(
        self, signer_role: str, signer_key_fingerprint: str, key_epoch: str
    ) -> str | None: ...


class DurableProvenanceReceiptStore(Protocol):
    def append(self, receipt: object) -> str: ...
    def load(self, receipt_id: str) -> Mapping[str, Any]: ...


class VerifiedTopologyProposerProvenanceCapability:
    """Opaque, process-local one-shot authority for campaign composition."""

    __slots__ = ("__token",)

    def __init__(self, token: str) -> None:
        object.__setattr__(self, "_VerifiedTopologyProposerProvenanceCapability__token", token)

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("verified_topology_proposer_provenance_capability_immutable")

    def __copy__(self):
        raise TypeError("verified_topology_proposer_provenance_capability_copy_forbidden")

    def __deepcopy__(self, _memo):
        raise TypeError("verified_topology_proposer_provenance_capability_copy_forbidden")

    def __reduce_ex__(self, _protocol):
        raise TypeError("verified_topology_proposer_provenance_capability_pickle_forbidden")


@dataclass(frozen=True)
class SignedTopologyProposerProvenanceReceipt:
    receipt_id: str
    proposer_call_receipt_id: str
    proposer_call_digest: str
    proposal_admission_receipt_id: str
    proposal_admission_digest: str
    proposer_model_id: str
    provider: str
    signer_role: str
    signer_public_key: str
    signer_key_fingerprint: str
    key_epoch: str
    issued_at: int
    expires_at: int
    nonce: str
    signature: str
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def signing_input(self) -> str:
        return canonical_signing_input(
            {
                key: value
                for key, value in self.to_dict().items()
                if key != "receipt_id"
            },
            SIGNING_PREFIX,
        )


@dataclass(frozen=True)
class VerifiedTopologyProposerProvenance:
    receipt: SignedTopologyProposerProvenanceReceipt
    admission_receipt: ModelTopologyProposalAdmissionReceipt
    durable_store_receipt_id: str
    publication_store_id: str
    capability: VerifiedTopologyProposerProvenanceCapability
    authenticated: bool = True
    nonce_consumed: bool = True


@dataclass(frozen=True)
class AuthenticatedTopologyProposalResult:
    proposal: LMStudioTopologyProposalResult
    provenance: VerifiedTopologyProposerProvenance


_CAPABILITY_LOCK = threading.Lock()
_CAPABILITIES: dict[str, tuple[str, str, str, str, int]] = {}
_ACTIVE_RECEIPT_CAPABILITIES: dict[str, str] = {}
_IN_FLIGHT_CAPABILITIES: dict[str, str] = {}


def propose_authenticated_lm_studio_shadow_topologies(
    *,
    catalog_snapshot: Any,
    requirements: Any,
    proposer_model_id: str,
    signed_receipt_provider: Callable[
        [LMStudioTopologyProposalResult],
        SignedTopologyProposerProvenanceReceipt | Mapping[str, Any],
    ],
    key_resolver: TopologyProposerKeyResolver,
    signature_verifier: SignatureVerifier,
    publication_store: DurableExactPublicationStore,
    receipt_store: ConfiguredGatewayReceiptStore,
    now: int,
    backend_factory: Callable[[str], Any],
    max_completion_tokens: int = 2_048,
    revoked_key_epochs: Sequence[str] = (),
) -> AuthenticatedTopologyProposalResult:
    """Call, externally authorize, verify, and durably store one proposal."""

    proposal = propose_lm_studio_shadow_topologies(
        catalog_snapshot=catalog_snapshot,
        requirements=requirements,
        proposer_model_id=proposer_model_id,
        max_completion_tokens=max_completion_tokens,
        backend_factory=backend_factory,
    )
    signed = signed_receipt_provider(proposal)
    provenance = verify_and_store_topology_proposer_provenance(
        call_receipt=proposal.call_receipt,
        admission_receipt=proposal.admission_receipt,
        signed_receipt=signed,
        key_resolver=key_resolver,
        signature_verifier=signature_verifier,
        publication_store=publication_store,
        receipt_store=receipt_store,
        now=now,
        revoked_key_epochs=revoked_key_epochs,
    )
    return AuthenticatedTopologyProposalResult(proposal, provenance)


def build_signed_topology_proposer_provenance_receipt(
    *,
    call_receipt: LMStudioTopologyProposalCallReceipt,
    admission_receipt: ModelTopologyProposalAdmissionReceipt,
    signer_public_key: str,
    signer_key_fingerprint: str,
    key_epoch: str,
    issued_at: int,
    expires_at: int,
    nonce: str,
    signature: str,
) -> SignedTopologyProposerProvenanceReceipt:
    call = _call(call_receipt)
    admission = _admission(admission_receipt)
    _assert_call_admission(call, admission)
    body = {
        "schema_version": SCHEMA_VERSION,
        "proposer_call_receipt_id": call.receipt_id,
        "proposer_call_digest": digest_payload(call.to_dict()),
        "proposal_admission_receipt_id": admission.receipt_id,
        "proposal_admission_digest": digest_payload(admission.to_dict()),
        "proposer_model_id": call.proposer_model_id,
        "provider": call.provider,
        "signer_role": SIGNER_ROLE,
        "signer_public_key": _required(signer_public_key),
        "signer_key_fingerprint": _required(signer_key_fingerprint),
        "key_epoch": _required(key_epoch),
        "issued_at": _epoch(issued_at),
        "expires_at": _epoch(expires_at),
        "nonce": _required(nonce),
        "signature": _required(signature),
    }
    if body["expires_at"] <= body["issued_at"]:
        raise ValueError("topology_proposer_provenance_ttl_invalid")
    if body["expires_at"] - body["issued_at"] > MAX_RECEIPT_TTL_SECONDS:
        raise ValueError("topology_proposer_provenance_ttl_invalid")
    return SignedTopologyProposerProvenanceReceipt(
        receipt_id="topology_proposer_provenance:" + _sha256(body), **body
    )


def rehydrate_signed_topology_proposer_provenance_receipt(
    payload: Mapping[str, Any],
) -> SignedTopologyProposerProvenanceReceipt:
    if not isinstance(payload, Mapping) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("topology_proposer_provenance_schema_invalid")
    receipt = SignedTopologyProposerProvenanceReceipt(
        receipt_id=_required(payload.get("receipt_id")),
        proposer_call_receipt_id=_required(payload.get("proposer_call_receipt_id")),
        proposer_call_digest=_required(payload.get("proposer_call_digest")),
        proposal_admission_receipt_id=_required(payload.get("proposal_admission_receipt_id")),
        proposal_admission_digest=_required(payload.get("proposal_admission_digest")),
        proposer_model_id=_required(payload.get("proposer_model_id")),
        provider=_required(payload.get("provider")),
        signer_role=_required(payload.get("signer_role")),
        signer_public_key=_required(payload.get("signer_public_key")),
        signer_key_fingerprint=_required(payload.get("signer_key_fingerprint")),
        key_epoch=_required(payload.get("key_epoch")),
        issued_at=_epoch(payload.get("issued_at")),
        expires_at=_epoch(payload.get("expires_at")),
        nonce=_required(payload.get("nonce")),
        signature=_required(payload.get("signature")),
    )
    expected = "topology_proposer_provenance:" + _sha256(
        {key: value for key, value in receipt.to_dict().items() if key != "receipt_id"}
    )
    if not hmac.compare_digest(receipt.receipt_id, expected):
        raise ValueError("topology_proposer_provenance_receipt_id_invalid")
    if receipt.expires_at <= receipt.issued_at:
        raise ValueError("topology_proposer_provenance_ttl_invalid")
    if receipt.expires_at - receipt.issued_at > MAX_RECEIPT_TTL_SECONDS:
        raise ValueError("topology_proposer_provenance_ttl_invalid")
    return receipt


def verify_and_store_topology_proposer_provenance(
    *,
    call_receipt: LMStudioTopologyProposalCallReceipt | Mapping[str, Any],
    admission_receipt: ModelTopologyProposalAdmissionReceipt | Mapping[str, Any],
    signed_receipt: SignedTopologyProposerProvenanceReceipt | Mapping[str, Any],
    key_resolver: TopologyProposerKeyResolver,
    signature_verifier: SignatureVerifier,
    publication_store: DurableExactPublicationStore,
    receipt_store: ConfiguredGatewayReceiptStore,
    now: int,
    revoked_key_epochs: Sequence[str] = (),
    leeway_seconds: int = 60,
) -> VerifiedTopologyProposerProvenance:
    call = _call(call_receipt)
    admission = _admission(admission_receipt)
    _assert_call_admission(call, admission)
    receipt = rehydrate_signed_topology_proposer_provenance_receipt(
        signed_receipt.to_dict()
        if isinstance(signed_receipt, SignedTopologyProposerProvenanceReceipt)
        else signed_receipt
    )
    if not 0 <= int(leeway_seconds) <= MAX_VERIFICATION_LEEWAY_SECONDS:
        raise ValueError("topology_proposer_provenance_leeway_invalid")
    reasons = _verification_reasons(
        call, admission, receipt, key_resolver, signature_verifier, int(now),
        revoked_key_epochs, int(leeway_seconds)
    )
    if reasons:
        raise ValueError("topology_proposer_provenance_rejected:" + ",".join(reasons))
    publication_store_id = _matching_durable_store_id(
        publication_store,
        receipt_store,
    )
    publication_binding = _proposer_signature_publication_binding(receipt)
    _advance_exact_publication(
        publication_store,
        nonce="topology-proposer-signature:" + receipt.nonce,
        binding_digest=publication_binding,
        target_status="RESERVED",
        error="topology_proposer_provenance_nonce_replay",
    )
    try:
        stored = receipt_store.append(receipt)
    except Exception:
        raise ValueError("topology_proposer_provenance_store_failed") from None
    if stored != receipt.receipt_id:
        raise ValueError("topology_proposer_provenance_store_mismatch")
    _advance_exact_publication(
        publication_store,
        nonce="topology-proposer-signature:" + receipt.nonce,
        binding_digest=publication_binding,
        target_status="AUTHORIZED",
        error="topology_proposer_provenance_publication_failed",
    )
    _advance_exact_publication(
        publication_store,
        nonce="topology-proposer-signature:" + receipt.nonce,
        binding_digest=publication_binding,
        target_status="APPLIED",
        error="topology_proposer_provenance_publication_failed",
    )
    capability = _mint_capability(
        receipt, admission, int(now), publication_store_id
    )
    return VerifiedTopologyProposerProvenance(
        receipt, admission, stored, publication_store_id, capability
    )


def _mint_capability(receipt, admission, now, publication_store_id):
    capability = VerifiedTopologyProposerProvenanceCapability(secrets.token_urlsafe(32))
    token = object.__getattribute__(
        capability,
        "_VerifiedTopologyProposerProvenanceCapability__token",
    )
    with _CAPABILITY_LOCK:
        _expire_capabilities_locked(now)
        active_key = publication_store_id + "|" + receipt.receipt_id
        if active_key in _ACTIVE_RECEIPT_CAPABILITIES:
            raise ValueError("topology_proposer_provenance_capability_already_live")
        if len(_CAPABILITIES) >= MAX_LIVE_CAPABILITIES:
            raise ValueError("topology_proposer_provenance_capability_capacity_exceeded")
        _CAPABILITIES[token] = (
            publication_store_id,
            receipt.receipt_id,
            digest_payload(receipt.to_dict()),
            digest_payload(admission.to_dict()),
            receipt.expires_at,
        )
        _ACTIVE_RECEIPT_CAPABILITIES[active_key] = token
    return capability


def validate_verified_topology_proposer_provenance(
    value: VerifiedTopologyProposerProvenance,
    *,
    now: int,
) -> tuple[SignedTopologyProposerProvenanceReceipt, ModelTopologyProposalAdmissionReceipt] | None:
    """Validate without consuming so signer/store failures remain retryable."""
    if type(value) is not VerifiedTopologyProposerProvenance:
        return None
    capability = value.capability
    if type(capability) is not VerifiedTopologyProposerProvenanceCapability:
        return None
    token = object.__getattribute__(
        capability,
        "_VerifiedTopologyProposerProvenanceCapability__token",
    )
    with _CAPABILITY_LOCK:
        _expire_capabilities_locked(int(now))
        expected = _CAPABILITIES.get(token)
        active_token = _ACTIVE_RECEIPT_CAPABILITIES.get(
            value.publication_store_id + "|" + value.receipt.receipt_id
        )
    actual = (
        value.publication_store_id,
        value.receipt.receipt_id,
        digest_payload(value.receipt.to_dict()),
        digest_payload(value.admission_receipt.to_dict()),
        value.receipt.expires_at,
    )
    if (
        expected is None
        or expected != actual
        or active_token != token
        or not value.receipt.issued_at <= int(now) <= value.receipt.expires_at
        or value.authenticated is not True
        or value.nonce_consumed is not True
        or value.durable_store_receipt_id != value.receipt.receipt_id
    ):
        return None
    return value.receipt, value.admission_receipt


def reserve_verified_topology_proposer_provenance_use(
    value: VerifiedTopologyProposerProvenance,
    *,
    publication_store: DurableExactPublicationStore,
    use_binding_digest: str,
    now: int,
) -> tuple[SignedTopologyProposerProvenanceReceipt, ModelTopologyProposalAdmissionReceipt] | None:
    """Durably reserve one exact campaign use without burning local retry state."""

    accepted = validate_verified_topology_proposer_provenance(value, now=now)
    if accepted is None:
        return None
    if _durable_publication_store_id(publication_store) != value.publication_store_id:
        raise ValueError("topology_proposer_provenance_publication_store_mismatch")
    status = _advance_exact_publication(
        publication_store,
        nonce="topology-proposer-use:" + value.receipt.receipt_id,
        binding_digest=use_binding_digest,
        target_status="RESERVED",
        error="topology_proposer_provenance_durable_use_replay",
    )
    if status == "APPLIED":
        raise ValueError("topology_proposer_provenance_durable_use_replay")
    _advance_exact_publication(
        publication_store,
        nonce="topology-proposer-use:" + value.receipt.receipt_id,
        binding_digest=use_binding_digest,
        target_status="AUTHORIZED",
        error="topology_proposer_provenance_durable_use_replay",
    )
    token = _capability_token(value.capability)
    with _CAPABILITY_LOCK:
        if token not in _CAPABILITIES:
            return None
        if token in _IN_FLIGHT_CAPABILITIES:
            raise ValueError("topology_proposer_provenance_capability_in_use")
        _IN_FLIGHT_CAPABILITIES[token] = use_binding_digest
    return accepted


def complete_verified_topology_proposer_provenance_use(
    value: VerifiedTopologyProposerProvenance,
    *,
    publication_store: DurableExactPublicationStore,
    use_binding_digest: str,
    now: int,
) -> tuple[SignedTopologyProposerProvenanceReceipt, ModelTopologyProposalAdmissionReceipt] | None:
    """Mark the exact durable campaign use applied and retire its local capability."""

    accepted = validate_verified_topology_proposer_provenance(value, now=now)
    if accepted is None:
        return None
    if _durable_publication_store_id(publication_store) != value.publication_store_id:
        raise ValueError("topology_proposer_provenance_publication_store_mismatch")
    token = _capability_token(value.capability)
    with _CAPABILITY_LOCK:
        if _IN_FLIGHT_CAPABILITIES.get(token) != use_binding_digest:
            return None
    _advance_exact_publication(
        publication_store,
        nonce="topology-proposer-use:" + value.receipt.receipt_id,
        binding_digest=use_binding_digest,
        target_status="APPLIED",
        error="topology_proposer_provenance_durable_use_replay",
    )
    with _CAPABILITY_LOCK:
        if _IN_FLIGHT_CAPABILITIES.get(token) != use_binding_digest:
            return None
        _IN_FLIGHT_CAPABILITIES.pop(token, None)
        expected = _CAPABILITIES.pop(token, None)
        active_key = value.publication_store_id + "|" + value.receipt.receipt_id
        if _ACTIVE_RECEIPT_CAPABILITIES.get(active_key) == token:
            _ACTIVE_RECEIPT_CAPABILITIES.pop(active_key, None)
    if expected is None:
        return None
    return accepted


def release_verified_topology_proposer_provenance_use(
    value: VerifiedTopologyProposerProvenance,
    *,
    use_binding_digest: str,
) -> bool:
    """Release only local in-flight state after a retryable output failure."""

    if type(value) is not VerifiedTopologyProposerProvenance:
        return False
    token = _capability_token(value.capability)
    with _CAPABILITY_LOCK:
        if _IN_FLIGHT_CAPABILITIES.get(token) != use_binding_digest:
            return False
        _IN_FLIGHT_CAPABILITIES.pop(token, None)
    return True


def consume_verified_topology_proposer_provenance(
    value: VerifiedTopologyProposerProvenance,
    *,
    publication_store: DurableExactPublicationStore,
    use_binding_digest: str,
    now: int,
) -> tuple[SignedTopologyProposerProvenanceReceipt, ModelTopologyProposalAdmissionReceipt] | None:
    """Reserve and complete one exact durable use in a single local operation."""

    if reserve_verified_topology_proposer_provenance_use(
        value,
        publication_store=publication_store,
        use_binding_digest=use_binding_digest,
        now=now,
    ) is None:
        return None
    return complete_verified_topology_proposer_provenance_use(
        value,
        publication_store=publication_store,
        use_binding_digest=use_binding_digest,
        now=now,
    )


def reload_verified_topology_proposer_provenance(
    *,
    call_receipt: LMStudioTopologyProposalCallReceipt | Mapping[str, Any],
    admission_receipt: ModelTopologyProposalAdmissionReceipt | Mapping[str, Any],
    signed_receipt: SignedTopologyProposerProvenanceReceipt | Mapping[str, Any],
    key_resolver: TopologyProposerKeyResolver,
    signature_verifier: SignatureVerifier,
    durable_receipt_store: DurableProvenanceReceiptStore,
    now: int,
    revoked_key_epochs: Sequence[str] = (),
    leeway_seconds: int = 60,
) -> VerifiedTopologyProposerProvenance:
    """Reverify a durably stored receipt after restart and mint one use."""
    call = _call(call_receipt)
    admission = _admission(admission_receipt)
    _assert_call_admission(call, admission)
    receipt = rehydrate_signed_topology_proposer_provenance_receipt(
        signed_receipt.to_dict()
        if isinstance(signed_receipt, SignedTopologyProposerProvenanceReceipt)
        else signed_receipt
    )
    if not 0 <= int(leeway_seconds) <= MAX_VERIFICATION_LEEWAY_SECONDS:
        raise ValueError("topology_proposer_provenance_leeway_invalid")
    reasons = _verification_reasons(
        call, admission, receipt, key_resolver, signature_verifier, int(now),
        revoked_key_epochs, int(leeway_seconds)
    )
    if reasons:
        raise ValueError("topology_proposer_provenance_rejected:" + ",".join(reasons))
    if getattr(durable_receipt_store, "durable", None) is not True:
        raise ValueError("topology_proposer_provenance_durable_store_required")
    try:
        stored = durable_receipt_store.load(receipt.receipt_id)
    except Exception:
        raise ValueError("topology_proposer_provenance_durable_receipt_missing") from None
    if digest_payload(stored) != digest_payload(receipt.to_dict()):
        raise ValueError("topology_proposer_provenance_durable_receipt_mismatch")
    publication_store_id = str(getattr(durable_receipt_store, "store_id", "") or "")
    if not publication_store_id:
        raise ValueError("topology_proposer_provenance_durable_store_required")
    capability = _mint_capability(
        receipt, admission, int(now), publication_store_id
    )
    return VerifiedTopologyProposerProvenance(
        receipt, admission, receipt.receipt_id, publication_store_id, capability
    )


def _verification_reasons(call, admission, receipt, resolver, verifier, now, revoked, leeway):
    reasons: list[str] = []
    if receipt.signer_role != SIGNER_ROLE:
        reasons.append("signer_role_mismatch")
    if receipt.key_epoch in {str(item) for item in revoked}:
        reasons.append("key_epoch_revoked")
    if receipt.expires_at <= receipt.issued_at:
        reasons.append("ttl_invalid")
    elif receipt.expires_at - receipt.issued_at > MAX_RECEIPT_TTL_SECONDS:
        reasons.append("ttl_exceeded")
    expected_call = (
        call.receipt_id,
        digest_payload(call.to_dict()),
        call.proposer_model_id,
        call.provider,
    )
    actual_call = (
        receipt.proposer_call_receipt_id,
        receipt.proposer_call_digest,
        receipt.proposer_model_id,
        receipt.provider,
    )
    if expected_call != actual_call:
        reasons.append("proposer_call_mismatch")
    expected_admission = (
        admission.receipt_id,
        digest_payload(admission.to_dict()),
    )
    actual_admission = (
        receipt.proposal_admission_receipt_id,
        receipt.proposal_admission_digest,
    )
    if expected_admission != actual_admission:
        reasons.append("proposal_admission_mismatch")
    try:
        trusted = resolver.resolve(
            SIGNER_ROLE, receipt.signer_key_fingerprint, receipt.key_epoch
        )
    except Exception:
        trusted = None
    if not trusted or not constant_time_compare(str(trusted), receipt.signer_public_key):
        reasons.append("signer_key_untrusted")
    if now + leeway < receipt.issued_at:
        reasons.append("issued_in_future")
    if now > receipt.expires_at + leeway:
        reasons.append("provenance_expired")
    try:
        signature_ok = verifier.verify(
            receipt.signer_public_key, receipt.signing_input(), receipt.signature
        ) is True
    except Exception:
        signature_ok = False
    if not signature_ok:
        reasons.append("signature_invalid")
    return tuple(sorted(set(reasons)))


def _proposer_signature_publication_binding(
    receipt: SignedTopologyProposerProvenanceReceipt,
) -> str:
    return digest_payload(
        {
            "kind": "topology_proposer_signature_publication.v1",
            "receipt_id": receipt.receipt_id,
            "receipt_digest": digest_payload(receipt.to_dict()),
        }
    )


def _advance_exact_publication(
    store: DurableExactPublicationStore,
    *,
    nonce: str,
    binding_digest: str,
    target_status: str,
    error: str,
) -> str:
    if getattr(store, "durable", None) is not True:
        raise ValueError("durable_exact_publication_store_required")
    operation = getattr(store, "advance_publication", None)
    if not callable(operation):
        raise ValueError("durable_exact_publication_store_required")
    try:
        status = str(operation(nonce, binding_digest, target_status) or "")
    except Exception:
        raise ValueError(error) from None
    allowed = {
        "RESERVED": {"RESERVED", "AUTHORIZED", "APPLIED"},
        "AUTHORIZED": {"AUTHORIZED", "APPLIED"},
        "APPLIED": {"APPLIED"},
    }
    if status not in allowed[target_status]:
        raise ValueError(error)
    return status


def _durable_publication_store_id(store: DurableExactPublicationStore) -> str:
    if getattr(store, "durable", None) is not True:
        raise ValueError("durable_exact_publication_store_required")
    store_id = str(getattr(store, "store_id", "") or "")
    if not store_id:
        raise ValueError("durable_exact_publication_store_required")
    return store_id


def _matching_durable_store_id(
    publication_store: DurableExactPublicationStore,
    receipt_store: ConfiguredGatewayReceiptStore,
) -> str:
    publication_store_id = _durable_publication_store_id(publication_store)
    if getattr(receipt_store, "durable", None) is not True:
        raise ValueError("topology_proposer_provenance_durable_receipt_store_required")
    receipt_store_id = str(getattr(receipt_store, "store_id", "") or "")
    if not receipt_store_id:
        raise ValueError("topology_proposer_provenance_durable_receipt_store_required")
    if not hmac.compare_digest(publication_store_id, receipt_store_id):
        raise ValueError("topology_proposer_provenance_store_identity_mismatch")
    return publication_store_id


def _expire_capabilities_locked(now: int) -> None:
    expired = [key for key, value in _CAPABILITIES.items() if value[4] < now]
    for key in expired:
        publication_store_id, receipt_id = _CAPABILITIES[key][0:2]
        _CAPABILITIES.pop(key, None)
        _IN_FLIGHT_CAPABILITIES.pop(key, None)
        active_key = publication_store_id + "|" + receipt_id
        if _ACTIVE_RECEIPT_CAPABILITIES.get(active_key) == key:
            _ACTIVE_RECEIPT_CAPABILITIES.pop(active_key, None)


def _capability_token(
    capability: VerifiedTopologyProposerProvenanceCapability,
) -> str:
    if type(capability) is not VerifiedTopologyProposerProvenanceCapability:
        raise ValueError("verified_topology_proposer_provenance_capability_invalid")
    return object.__getattribute__(
        capability,
        "_VerifiedTopologyProposerProvenanceCapability__token",
    )


def _call(value):
    if isinstance(value, LMStudioTopologyProposalCallReceipt):
        return value
    if isinstance(value, Mapping):
        return rehydrate_lm_studio_topology_proposal_call_receipt(value)
    raise ValueError("topology_proposer_call_receipt_invalid")


def _admission(value):
    if isinstance(value, ModelTopologyProposalAdmissionReceipt):
        return rehydrate_model_topology_proposal_admission_receipt(value.to_dict())
    if isinstance(value, Mapping):
        return rehydrate_model_topology_proposal_admission_receipt(value)
    raise ValueError("topology_proposer_admission_receipt_invalid")


def _assert_call_admission(call, admission) -> None:
    if admission.accepted is not True or admission.shadow_only is not True:
        raise ValueError("topology_proposer_admission_not_accepted")
    if (
        admission.proposer_call_receipt_id != call.receipt_id
        or admission.proposer_output_digest != call.output_digest
        or admission.proposer_model_id != call.proposer_model_id
        or admission.catalog_snapshot_id != call.catalog_snapshot_id
        or admission.requirements_digest != call.requirements_digest
    ):
        raise ValueError("topology_proposer_call_admission_mismatch")


def _sha256(value: Mapping[str, Any]) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _required(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("topology_proposer_provenance_field_invalid")
    return text


def _epoch(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("topology_proposer_provenance_epoch_invalid")
    return value


__all__ = [
    "SignedTopologyProposerProvenanceReceipt",
    "AuthenticatedTopologyProposalResult",
    "TopologyProposerKeyResolver",
    "DurableProvenanceReceiptStore",
    "VerifiedTopologyProposerProvenance",
    "VerifiedTopologyProposerProvenanceCapability",
    "build_signed_topology_proposer_provenance_receipt",
    "complete_verified_topology_proposer_provenance_use",
    "consume_verified_topology_proposer_provenance",
    "release_verified_topology_proposer_provenance_use",
    "validate_verified_topology_proposer_provenance",
    "propose_authenticated_lm_studio_shadow_topologies",
    "rehydrate_signed_topology_proposer_provenance_receipt",
    "reload_verified_topology_proposer_provenance",
    "reserve_verified_topology_proposer_provenance_use",
    "verify_and_store_topology_proposer_provenance",
]
