"""Signed integrity boundary for backend architect proposal admissions.

The signer enforces an exact, domain-separated proposal policy before signing.
The verifier rehydrates and validates the serialized attestation against an
exact expected payload.  The result is integrity evidence only: this module
does not authenticate the verification context or grant runtime authority.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    IsolatedSignerClient,
    SigningRequest,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)


PROPOSAL_AUTHENTICITY_SCHEMA_VERSION = (
    "reddog_architect_proposal_authenticity_attestation.v1"
)
PROPOSAL_AUTHENTICITY_SIGNING_OPERATION = "attest_architect_proposal"
PROPOSAL_AUTHENTICITY_SIGNING_PREFIX = "reddog-architect-proposal.v1."
PROPOSAL_AUTHENTICITY_SIGNER_ROLE = "reddog_architect"
PROPOSAL_POLICY_AUTHORIZATION_SCHEMA_VERSION = (
    "reddog_architect_proposal_policy_authorization.v1"
)
PROPOSAL_POLICY_AUTHORIZATION_PREFIX = (
    "reddog-architect-proposal-policy-authorization.v1."
)
DEFAULT_PROPOSAL_AUTHENTICITY_MAX_TTL_SECONDS = 300


@dataclass(frozen=True)
class ArchitectProposalAuthenticityPayload:
    schema_version: str
    attestation_id: str
    proposal_admission_receipt_id: str
    proposal_admission_digest: str
    determination_receipt_id: str
    determination_digest: str
    queue_candidate_id: str
    queue_candidate_digest: str
    snapshot_receipt_id: str
    snapshot_content_digest: str
    repo_head_sha: str
    work_state_revision: str
    report_bundle_id: str
    wsp15_allocation_receipt_id: str
    wsp15_allocation_digest: str
    holoindex_generation_id: str
    holoindex_freshness_receipt_digest: str
    policy_digest: str
    allowed_paths_digest: str
    denied_paths_digest: str
    required_tests_digest: str
    required_policy_gates_digest: str
    target_effect_plane: str
    requester_principal_id: str
    reddog_id: str
    signer_public_key: str
    signer_key_fingerprint: str
    key_epoch: str
    consensus_receipt_digest: str
    authority_profile_source_receipt_id: str
    nonce: str
    issued_at: int
    expires_at: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArchitectProposalAuthenticityAttestation:
    payload: ArchitectProposalAuthenticityPayload
    signature: str

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.payload.to_dict(),
            "signature": self.signature,
        }


@dataclass(frozen=True)
class ArchitectProposalSignerPolicy:
    """Signer-owned exact authorization for one proposal attestation."""

    expected_payload: ArchitectProposalAuthenticityPayload
    max_ttl_seconds: int = DEFAULT_PROPOSAL_AUTHENTICITY_MAX_TTL_SECONDS


@dataclass(frozen=True)
class ArchitectProposalPolicyAuthorization:
    """Principal-signed authorization for one exact signer policy."""

    schema_version: str
    authorization_id: str
    proposal_policy_digest: str
    principal_id: str
    principal_provider: str
    principal_public_key: str
    reddog_id: str
    reddog_public_key: str
    key_epoch: str
    authority_profile_source_receipt_id: str
    signer_instance_id: str
    replay_store_binding_digest: str
    security_context_digest: str
    nonce: str
    issued_at: int
    expires_at: int
    signature: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArchitectProposalIntegrityContext:
    """Complete comparison input for cryptographic integrity verification.

    This context does not authenticate its own origin and therefore cannot
    grant queue or execution authority.
    """

    expected_payload: ArchitectProposalAuthenticityPayload
    now_epoch: int
    revoked_key_epochs: frozenset[str] = frozenset()
    max_ttl_seconds: int = DEFAULT_PROPOSAL_AUTHENTICITY_MAX_TTL_SECONDS


@dataclass(frozen=True)
class ArchitectProposalSigningContext:
    signer: IsolatedSignerClient
    signature_verifier: SignatureVerifier
    requester_principal_id: str
    signer_public_key: str
    key_epoch: str
    authority_tier: str
    consensus_receipt_digest: str


class ProposalAuthenticityNonceStore(Protocol):
    def reserve(self, nonce: str, *, expires_at: int, subject: str) -> str | None: ...

    def commit(self, reservation: str) -> None: ...

    def rollback(self, reservation: str) -> None: ...


class InMemoryProposalAuthenticityNonceStore:
    """Process-local nonce store for tests; production must inject durability."""

    def __init__(self) -> None:
        self._seen: set[tuple[str, str]] = set()
        self._reserved: dict[str, tuple[str, str]] = {}
        self._lock = threading.Lock()

    def reserve(self, nonce: str, *, expires_at: int, subject: str) -> str | None:
        if not nonce or not subject or expires_at <= 0:
            return None
        key = (subject, nonce)
        with self._lock:
            if key in self._seen or key in self._reserved.values():
                return None
            reservation = _digest(
                {"expires_at": expires_at, "nonce": nonce, "subject": subject}
            )
            self._reserved[reservation] = key
            return reservation

    def commit(self, reservation: str) -> None:
        with self._lock:
            key = self._reserved.pop(reservation, None)
            if key is None or key in self._seen:
                raise ValueError("proposal_authenticity_nonce_reservation_invalid")
            self._seen.add(key)

    def rollback(self, reservation: str) -> None:
        with self._lock:
            self._reserved.pop(reservation, None)


def build_architect_proposal_authenticity_payload(
    *,
    proposal_admission: Mapping[str, Any],
    determination: Mapping[str, Any],
    queue_candidate: Mapping[str, Any],
    requester_principal_id: str,
    reddog_id: str,
    signer_public_key: str,
    key_epoch: str,
    consensus_receipt_digest: str,
    authority_profile_source_receipt_id: str,
    nonce: str,
    issued_at: int,
    expires_at: int,
) -> ArchitectProposalAuthenticityPayload:
    """Build the complete canonical proposal payload from existing receipts."""

    proposal = _mapping(proposal_admission)
    candidate = _mapping(queue_candidate)
    values = {
        "schema_version": PROPOSAL_AUTHENTICITY_SCHEMA_VERSION,
        **_proposal_binding_values(proposal, determination, candidate),
        **_proposal_identity_values(
            requester_principal_id=requester_principal_id,
            reddog_id=reddog_id,
            signer_public_key=signer_public_key,
            key_epoch=key_epoch,
            consensus_receipt_digest=consensus_receipt_digest,
            authority_profile_source_receipt_id=(
                authority_profile_source_receipt_id
            ),
            nonce=nonce,
            issued_at=issued_at,
            expires_at=expires_at,
        ),
    }
    attestation_id = "reddog_architect_proposal_attestation_" + _digest(values)[
        7:39
    ]
    payload = ArchitectProposalAuthenticityPayload(
        attestation_id=attestation_id, **values
    )
    _validate_payload_shape(payload.to_dict())
    return payload


def _proposal_binding_values(
    proposal: Mapping[str, Any],
    determination: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    determination_body = {
        key: value
        for key, value in _mapping(determination).items()
        if key != "proposal_authenticity_attestation"
    }
    return {
        "proposal_admission_receipt_id": _text(proposal.get("receipt_id")),
        "proposal_admission_digest": _digest(proposal),
        "determination_receipt_id": _text(
            determination_body.get("determination_receipt_id")
        ),
        "determination_digest": _digest(determination_body),
        "queue_candidate_id": _text(candidate.get("queue_candidate_id")),
        "queue_candidate_digest": _digest(candidate),
        "snapshot_receipt_id": _text(proposal.get("snapshot_receipt_id")),
        "snapshot_content_digest": _text(proposal.get("snapshot_content_digest")),
        "repo_head_sha": _text(proposal.get("repo_head_sha")),
        "work_state_revision": _text(proposal.get("work_state_revision")),
        "report_bundle_id": _text(proposal.get("report_bundle_id")),
        "wsp15_allocation_receipt_id": _text(
            proposal.get("wsp15_allocation_receipt_id")
        ),
        "wsp15_allocation_digest": _text(
            proposal.get("wsp15_allocation_digest")
        ),
        "holoindex_generation_id": _text(
            proposal.get("holoindex_generation_id")
        ),
        "holoindex_freshness_receipt_digest": _text(
            proposal.get("holoindex_freshness_receipt_digest")
        ),
        "policy_digest": _text(proposal.get("policy_digest")),
        "allowed_paths_digest": _digest(proposal.get("allowed_paths")),
        "denied_paths_digest": _digest(proposal.get("denied_paths")),
        "required_tests_digest": _digest(proposal.get("required_tests")),
        "required_policy_gates_digest": _digest(
            proposal.get("required_policy_gates")
        ),
        "target_effect_plane": _text(proposal.get("target_effect_plane")),
    }


def _proposal_identity_values(
    *,
    requester_principal_id: str,
    reddog_id: str,
    signer_public_key: str,
    key_epoch: str,
    consensus_receipt_digest: str,
    authority_profile_source_receipt_id: str,
    nonce: str,
    issued_at: int,
    expires_at: int,
) -> dict[str, Any]:
    return {
        "requester_principal_id": _text(requester_principal_id),
        "reddog_id": _text(reddog_id),
        "signer_public_key": _text(signer_public_key),
        "signer_key_fingerprint": public_key_fingerprint(signer_public_key),
        "key_epoch": _text(key_epoch),
        "consensus_receipt_digest": _text(consensus_receipt_digest),
        "authority_profile_source_receipt_id": _text(
            authority_profile_source_receipt_id
        ),
        "nonce": _text(nonce),
        "issued_at": int(issued_at),
        "expires_at": int(expires_at),
    }


def canonical_architect_proposal_signing_input(
    payload: ArchitectProposalAuthenticityPayload | Mapping[str, Any],
) -> str:
    raw = payload.to_dict() if hasattr(payload, "to_dict") else dict(payload)
    return PROPOSAL_AUTHENTICITY_SIGNING_PREFIX + _canonical_json(raw)


def architect_proposal_signer_policy_digest(
    policy: ArchitectProposalSignerPolicy,
) -> str:
    """Return the canonical digest of one exact proposal signer policy."""

    if not _proposal_policy_valid(policy):
        raise ValueError("architect_proposal_signer_policy_invalid")
    return _digest(
        {
            "expected_payload": policy.expected_payload.to_dict(),
            "max_ttl_seconds": int(policy.max_ttl_seconds),
        }
    )


def architect_proposal_signer_instance_id(
    signer_runtime_root: Path | str,
    reddog_public_key: str,
    key_epoch: str,
) -> str:
    """Bind one proposal signer instance to its key and runtime root."""

    root = Path(signer_runtime_root).resolve()
    return "reddog-proposal-signer:" + _digest(
        {
            "key_epoch": _text(key_epoch),
            "reddog_public_key": _text(reddog_public_key),
            "signer_runtime_root": str(root),
        }
    )[7:39]


def architect_proposal_replay_store_binding_digest(
    signer_instance_id: str,
    nonce_store_path: Path | str,
    high_water_store_id: str,
) -> str:
    """Bind authorization replay to state plus an independent high-water authority."""

    return _digest(
        {
            "high_water_store_id": _text(high_water_store_id),
            "nonce_store_path": str(Path(nonce_store_path).resolve()),
            "signer_instance_id": _text(signer_instance_id),
        }
    )


def build_architect_proposal_policy_authorization_payload(
    policy: ArchitectProposalSignerPolicy,
    *,
    principal_id: str,
    principal_provider: str,
    principal_public_key: str,
    reddog_id: str,
    reddog_public_key: str,
    key_epoch: str,
    authority_profile_source_receipt_id: str,
    signer_instance_id: str,
    replay_store_binding_digest: str,
    security_context_digest: str,
    nonce: str,
    issued_at: int,
    expires_at: int,
) -> dict[str, Any]:
    """Build the unsigned, principal-authorized policy payload."""

    values = {
        "schema_version": PROPOSAL_POLICY_AUTHORIZATION_SCHEMA_VERSION,
        "proposal_policy_digest": architect_proposal_signer_policy_digest(
            policy
        ),
        "principal_id": _text(principal_id),
        "principal_provider": _text(principal_provider),
        "principal_public_key": _text(principal_public_key),
        "reddog_id": _text(reddog_id),
        "reddog_public_key": _text(reddog_public_key),
        "key_epoch": _text(key_epoch),
        "authority_profile_source_receipt_id": _text(
            authority_profile_source_receipt_id
        ),
        "signer_instance_id": _text(signer_instance_id),
        "replay_store_binding_digest": _text(
            replay_store_binding_digest
        ),
        "security_context_digest": _text(security_context_digest),
        "nonce": _text(nonce),
        "issued_at": int(issued_at),
        "expires_at": int(expires_at),
    }
    values["authorization_id"] = (
        "reddog_architect_proposal_policy_authorization_"
        + _digest(values)[7:39]
    )
    _validate_policy_authorization_payload(values)
    return values


def canonical_architect_proposal_policy_authorization_input(
    value: Mapping[str, Any],
) -> str:
    """Return the domain-separated principal-signing input."""

    payload = dict(value)
    payload.pop("signature", None)
    _validate_policy_authorization_payload(payload)
    return PROPOSAL_POLICY_AUTHORIZATION_PREFIX + _canonical_json(payload)


def verify_architect_proposal_policy_authorization(
    value: Mapping[str, Any],
    *,
    policy: ArchitectProposalSignerPolicy,
    authority_profile: Mapping[str, Any],
    trusted_principal_public_key: str,
    expected_signer_instance_id: str,
    expected_replay_store_binding_digest: str,
    expected_security_context_digest: str,
    now_epoch: int,
) -> ArchitectProposalPolicyAuthorization:
    """Verify a principal signature over one exact signer policy."""

    if not isinstance(value, Mapping):
        raise ValueError("architect_proposal_policy_authorization_invalid")
    raw = dict(value)
    expected_fields = {
        "schema_version",
        "authorization_id",
        "proposal_policy_digest",
        "principal_id",
        "principal_provider",
        "principal_public_key",
        "reddog_id",
        "reddog_public_key",
        "key_epoch",
        "authority_profile_source_receipt_id",
        "signer_instance_id",
        "replay_store_binding_digest",
        "security_context_digest",
        "nonce",
        "issued_at",
        "expires_at",
        "signature",
    }
    if set(raw) != expected_fields:
        raise ValueError(
            "architect_proposal_policy_authorization_fields_invalid"
        )
    signature = _text(raw.pop("signature"))
    _validate_policy_authorization_payload(raw)
    expected_bindings = {
        "proposal_policy_digest": architect_proposal_signer_policy_digest(
            policy
        ),
        "principal_id": _text(authority_profile.get("principal_id")),
        "principal_provider": _text(
            authority_profile.get("principal_provider")
        ),
        "principal_public_key": _text(
            authority_profile.get("principal_public_key")
        ),
        "reddog_id": _text(authority_profile.get("reddog_id")),
        "reddog_public_key": _text(
            authority_profile.get("reddog_public_key")
        ),
        "key_epoch": _text(authority_profile.get("key_epoch")),
        "authority_profile_source_receipt_id": _text(
            authority_profile.get("authority_profile_source_receipt_id")
        ),
        "signer_instance_id": _text(expected_signer_instance_id),
        "replay_store_binding_digest": _text(
            expected_replay_store_binding_digest
        ),
        "security_context_digest": _text(
            expected_security_context_digest
        ),
    }
    if any(raw.get(key) != expected for key, expected in expected_bindings.items()):
        raise ValueError(
            "architect_proposal_policy_authorization_binding_mismatch"
        )
    if raw["principal_public_key"] != _text(
        trusted_principal_public_key
    ):
        raise ValueError(
            "architect_proposal_policy_authorization_principal_untrusted"
        )
    ttl = int(raw["expires_at"]) - int(raw["issued_at"])
    if (
        int(raw["issued_at"]) > int(now_epoch)
        or int(raw["expires_at"]) <= int(now_epoch)
        or ttl <= 0
        or ttl > DEFAULT_PROPOSAL_AUTHENTICITY_MAX_TTL_SECONDS
    ):
        raise ValueError(
            "architect_proposal_policy_authorization_expired"
        )
    signing_input = (
        canonical_architect_proposal_policy_authorization_input(raw)
    )
    if not Ed25519SignatureVerifier().verify(
        str(raw["principal_public_key"]),
        signing_input,
        signature,
    ):
        raise ValueError(
            "architect_proposal_policy_authorization_signature_invalid"
        )
    return ArchitectProposalPolicyAuthorization(
        **raw,
        signature=signature,
    )


def rehydrate_architect_proposal_authenticity_payload(
    value: Mapping[str, Any],
) -> ArchitectProposalAuthenticityPayload:
    """Rehydrate one exact proposal payload without accepting an attestation."""

    if not isinstance(value, Mapping):
        raise ValueError("architect_proposal_authenticity_payload_invalid")
    payload = dict(value)
    _validate_payload_shape(payload)
    return ArchitectProposalAuthenticityPayload(**payload)


def _validate_policy_authorization_payload(
    payload: Mapping[str, Any],
) -> None:
    fields = {
        "schema_version",
        "authorization_id",
        "proposal_policy_digest",
        "principal_id",
        "principal_provider",
        "principal_public_key",
        "reddog_id",
        "reddog_public_key",
        "key_epoch",
        "authority_profile_source_receipt_id",
        "signer_instance_id",
        "replay_store_binding_digest",
        "security_context_digest",
        "nonce",
        "issued_at",
        "expires_at",
    }
    if set(payload) != fields:
        raise ValueError(
            "architect_proposal_policy_authorization_fields_invalid"
        )
    if payload.get("schema_version") != (
        PROPOSAL_POLICY_AUTHORIZATION_SCHEMA_VERSION
    ):
        raise ValueError(
            "architect_proposal_policy_authorization_schema_invalid"
        )
    for field in (
        "proposal_policy_digest",
        "authority_profile_source_receipt_id",
        "replay_store_binding_digest",
        "security_context_digest",
    ):
        if not _sha256(payload.get(field)):
            raise ValueError(
                "architect_proposal_policy_authorization_digest_invalid"
            )
    for field in (
        "authorization_id",
        "principal_id",
        "principal_provider",
        "principal_public_key",
        "reddog_id",
        "reddog_public_key",
        "key_epoch",
        "signer_instance_id",
        "nonce",
    ):
        if not isinstance(payload.get(field), str) or not _text(
            payload.get(field)
        ):
            raise ValueError(
                "architect_proposal_policy_authorization_value_missing"
            )
    if not _ascii_deep(payload):
        raise ValueError(
            "architect_proposal_policy_authorization_non_ascii"
        )
    unsigned = dict(payload)
    supplied_id = str(unsigned.pop("authorization_id"))
    expected_id = (
        "reddog_architect_proposal_policy_authorization_"
        + _digest(unsigned)[7:39]
    )
    if supplied_id != expected_id:
        raise ValueError(
            "architect_proposal_policy_authorization_id_invalid"
        )
    if (
        type(payload.get("issued_at")) is not int
        or type(payload.get("expires_at")) is not int
    ):
        raise ValueError(
            "architect_proposal_policy_authorization_time_invalid"
        )


def attest_architect_proposal(
    payload: ArchitectProposalAuthenticityPayload,
    context: ArchitectProposalSigningContext,
) -> ArchitectProposalAuthenticityAttestation:
    """Request signing and independently verify the signer response."""

    _validate_payload_shape(payload.to_dict())
    if (
        payload.requester_principal_id != context.requester_principal_id
        or payload.signer_public_key != context.signer_public_key
        or payload.key_epoch != context.key_epoch
        or payload.consensus_receipt_digest != context.consensus_receipt_digest
    ):
        raise ValueError("architect_proposal_signing_context_mismatch")
    signing_input = canonical_architect_proposal_signing_input(payload)
    response = context.signer.sign(_proposal_signing_request(
        payload, context, signing_input
    ))
    if not _proposal_signing_response_valid(response, context, signing_input):
        raise ValueError("architect_proposal_signing_rejected")
    return ArchitectProposalAuthenticityAttestation(
        payload=payload,
        signature=response.signature,
    )


def _proposal_signing_request(
    payload: ArchitectProposalAuthenticityPayload,
    context: ArchitectProposalSigningContext,
    signing_input: str,
) -> SigningRequest:
    return SigningRequest(
        signing_input=signing_input,
        payload_digest=_digest({"signing_input": signing_input}),
        signer_role=PROPOSAL_AUTHENTICITY_SIGNER_ROLE,
        signer_public_key=context.signer_public_key,
        requester_principal_id=context.requester_principal_id,
        nonce=payload.nonce,
        key_epoch=context.key_epoch,
        requested_operation=PROPOSAL_AUTHENTICITY_SIGNING_OPERATION,
        authority_tier=context.authority_tier,
        consensus_receipt_digest=context.consensus_receipt_digest,
    )


def _proposal_signing_response_valid(
    response: Any,
    context: ArchitectProposalSigningContext,
    signing_input: str,
) -> bool:
    return bool(
        response.accepted
        and response.signer_public_key == context.signer_public_key
        and response.key_fingerprint
        == public_key_fingerprint(context.signer_public_key)
        and response.key_epoch == context.key_epoch
        and response.signature
        and response.audit_mac
        and response.boundary_attested
        and response.requester_identity_attested
        and response.signer_loads_no_untrusted_code
        and response.no_secret_material_returned
        and context.signature_verifier.verify(
            context.signer_public_key, signing_input, response.signature
        )
    )


def verify_architect_proposal_attestation_integrity(
    value: Mapping[str, Any],
    *,
    context: ArchitectProposalIntegrityContext,
) -> ArchitectProposalAuthenticityAttestation:
    """Verify exact payload equality, freshness, revocation, and signature.

    The returned typed attestation is integrity evidence only.  It is not an
    opaque authority proof and is intentionally not accepted by proposal
    admission or promotion.
    """

    if (
        not isinstance(context, ArchitectProposalIntegrityContext)
        or not isinstance(
            context.expected_payload, ArchitectProposalAuthenticityPayload
        )
    ):
        raise ValueError("architect_proposal_authenticity_trust_context_invalid")
    attestation = _rehydrate_attestation(value)
    payload = attestation.payload.to_dict()
    _validate_payload_shape(payload)
    if payload != context.expected_payload.to_dict():
        raise ValueError("architect_proposal_authenticity_binding_mismatch")
    now = int(context.now_epoch)
    ttl = int(payload["expires_at"]) - int(payload["issued_at"])
    if (
        payload["issued_at"] > now
        or payload["expires_at"] <= now
        or ttl <= 0
        or ttl > int(context.max_ttl_seconds)
    ):
        raise ValueError("architect_proposal_authenticity_expired")
    if payload["key_epoch"] in context.revoked_key_epochs:
        raise ValueError("architect_proposal_authenticity_key_revoked")
    if not Ed25519SignatureVerifier().verify(
        payload["signer_public_key"],
        canonical_architect_proposal_signing_input(payload),
        attestation.signature,
    ):
        raise ValueError("architect_proposal_authenticity_signature_invalid")
    return attestation


def validate_proposal_signing_request(
    request: SigningRequest,
    policy: ArchitectProposalSignerPolicy,
    *,
    now_epoch: int,
) -> Mapping[str, Any] | None:
    """Signer-side exact-domain and exact-policy validation."""

    if not _proposal_policy_valid(policy):
        return None
    payload = _parse_proposal_signing_payload(request)
    if payload is None:
        return None
    if not _proposal_request_bindings_match(request, payload):
        return None
    if payload != policy.expected_payload.to_dict():
        return None
    if not _proposal_time_window_valid(payload, now_epoch, policy.max_ttl_seconds):
        return None
    return payload


def _proposal_policy_valid(policy: Any) -> bool:
    return isinstance(policy, ArchitectProposalSignerPolicy) and isinstance(
        policy.expected_payload, ArchitectProposalAuthenticityPayload
    )


def _parse_proposal_signing_payload(
    request: SigningRequest,
) -> Mapping[str, Any] | None:
    if (
        request.requested_operation != PROPOSAL_AUTHENTICITY_SIGNING_OPERATION
        or request.signer_role != PROPOSAL_AUTHENTICITY_SIGNER_ROLE
        or request.authority_tier not in {"HIGH", "ULTRA"}
        or not request.signing_input.startswith(PROPOSAL_AUTHENTICITY_SIGNING_PREFIX)
    ):
        return None
    raw = request.signing_input[len(PROPOSAL_AUTHENTICITY_SIGNING_PREFIX) :]
    try:
        payload = json.loads(raw)
        if not isinstance(payload, Mapping) or raw != _canonical_json(payload):
            return None
        _validate_payload_shape(payload)
    except (TypeError, json.JSONDecodeError, ValueError):
        return None
    return payload


def _proposal_request_bindings_match(
    request: SigningRequest,
    payload: Mapping[str, Any],
) -> bool:
    return not (
        request.payload_digest != _digest({"signing_input": request.signing_input})
        or request.requester_principal_id != payload["requester_principal_id"]
        or request.signer_public_key != payload["signer_public_key"]
        or request.key_epoch != payload["key_epoch"]
        or request.nonce != payload["nonce"]
        or request.consensus_receipt_digest != payload["consensus_receipt_digest"]
    )


def _proposal_time_window_valid(
    payload: Mapping[str, Any],
    now_epoch: int,
    max_ttl_seconds: int,
) -> bool:
    ttl = int(payload["expires_at"]) - int(payload["issued_at"])
    return not (
        int(payload["issued_at"]) > now_epoch
        or int(payload["expires_at"]) <= now_epoch
        or ttl <= 0
        or ttl > int(max_ttl_seconds)
    )


def _rehydrate_attestation(
    value: Mapping[str, Any],
) -> ArchitectProposalAuthenticityAttestation:
    expected = set(ArchitectProposalAuthenticityPayload.__dataclass_fields__) | {
        "signature",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("architect_proposal_authenticity_field_set_invalid")
    payload = ArchitectProposalAuthenticityPayload(
        **{
            key: value[key]
            for key in ArchitectProposalAuthenticityPayload.__dataclass_fields__
        }
    )
    return ArchitectProposalAuthenticityAttestation(
        payload=payload,
        signature=_text(value.get("signature")),
    )


def _validate_payload_shape(payload: Mapping[str, Any]) -> None:
    expected = set(ArchitectProposalAuthenticityPayload.__dataclass_fields__)
    if set(payload) != expected:
        raise ValueError("architect_proposal_authenticity_payload_fields_invalid")
    if payload.get("schema_version") != PROPOSAL_AUTHENTICITY_SCHEMA_VERSION:
        raise ValueError("architect_proposal_authenticity_schema_invalid")
    unsigned = {
        key: value for key, value in payload.items() if key != "attestation_id"
    }
    expected_id = "reddog_architect_proposal_attestation_" + _digest(unsigned)[7:39]
    if payload.get("attestation_id") != expected_id:
        raise ValueError("architect_proposal_authenticity_id_invalid")
    if not _ascii_deep(payload):
        raise ValueError("architect_proposal_authenticity_non_ascii")
    required_text = expected.difference({"issued_at", "expires_at"})
    if any(
        not isinstance(payload.get(key), str) or not payload.get(key)
        for key in required_text
    ):
        raise ValueError("architect_proposal_authenticity_value_missing")
    if not _proposal_digests_valid(payload):
        raise ValueError("architect_proposal_authenticity_digest_invalid")
    _validate_proposal_key_and_time(payload)


def _proposal_digests_valid(payload: Mapping[str, Any]) -> bool:
    return all(
        _sha256(payload.get(key))
        for key in (
            "proposal_admission_digest",
            "determination_digest",
            "queue_candidate_digest",
            "snapshot_content_digest",
            "wsp15_allocation_digest",
            "holoindex_freshness_receipt_digest",
            "policy_digest",
            "allowed_paths_digest",
            "denied_paths_digest",
            "required_tests_digest",
            "required_policy_gates_digest",
            "consensus_receipt_digest",
            "authority_profile_source_receipt_id",
        )
    )


def _validate_proposal_key_and_time(payload: Mapping[str, Any]) -> None:
    if payload.get("signer_key_fingerprint") != public_key_fingerprint(
        _text(payload.get("signer_public_key"))
    ):
        raise ValueError("architect_proposal_authenticity_fingerprint_invalid")
    issued_at = payload.get("issued_at")
    expires_at = payload.get("expires_at")
    if (
        isinstance(issued_at, bool)
        or not isinstance(issued_at, int)
        or isinstance(expires_at, bool)
        or not isinstance(expires_at, int)
    ):
        raise ValueError("architect_proposal_authenticity_time_invalid")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        dict(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sha256(value: Any) -> bool:
    text = _text(value)
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


def _ascii_deep(value: Any) -> bool:
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


__all__ = [
    "ArchitectProposalPolicyAuthorization",
    "ArchitectProposalAuthenticityAttestation",
    "ArchitectProposalAuthenticityPayload",
    "ArchitectProposalSignerPolicy",
    "ArchitectProposalSigningContext",
    "ArchitectProposalIntegrityContext",
    "DEFAULT_PROPOSAL_AUTHENTICITY_MAX_TTL_SECONDS",
    "InMemoryProposalAuthenticityNonceStore",
    "PROPOSAL_AUTHENTICITY_SCHEMA_VERSION",
    "PROPOSAL_AUTHENTICITY_SIGNER_ROLE",
    "PROPOSAL_AUTHENTICITY_SIGNING_OPERATION",
    "PROPOSAL_AUTHENTICITY_SIGNING_PREFIX",
    "PROPOSAL_POLICY_AUTHORIZATION_PREFIX",
    "PROPOSAL_POLICY_AUTHORIZATION_SCHEMA_VERSION",
    "ProposalAuthenticityNonceStore",
    "attest_architect_proposal",
    "architect_proposal_signer_policy_digest",
    "architect_proposal_signer_instance_id",
    "architect_proposal_replay_store_binding_digest",
    "build_architect_proposal_policy_authorization_payload",
    "build_architect_proposal_authenticity_payload",
    "canonical_architect_proposal_signing_input",
    "canonical_architect_proposal_policy_authorization_input",
    "rehydrate_architect_proposal_authenticity_payload",
    "validate_proposal_signing_request",
    "verify_architect_proposal_policy_authorization",
    "verify_architect_proposal_attestation_integrity",
]
