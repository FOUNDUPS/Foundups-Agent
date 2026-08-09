"""RedDog signer and delegated-authority runtime.

This module produces signed RedDogPrincipalIdentity and
RedDogDelegatedWorkAuthority records through injected boundaries only. It does
not implement cryptography, generate keys, load vault secrets, execute work,
enqueue OpenClaw, invoke Hermes, mutate HoloIndex, or call the extension
runtime. The default signer and principal resolver fail closed.

The purpose is to bridge the gap after the E0/E1 contracts:

* E0 specified the isolated signer boundary.
* E1 verifies signed work authority.
* This module prepares authority records by validating scope, freshness,
  revocation, nonce uniqueness, and high-authority co-sign evidence before
  requesting signatures from an injected signer client.

The signer response is treated as authority only when it carries the boundary
attestations required by E0. All emitted receipts are evidence for later gates;
they do not execute work by themselves.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping, Optional, Protocol, Sequence, Tuple

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PermissionSnapshot,
    PermissionSnapshotResolver,
    PREFIX_IDENTITY,
    PREFIX_WORKAUTH,
    canonical_signing_input,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_work_order_base_ref,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
    AuthorityRuntimeStore,
    FailClosedPrincipalAuthorityResolver,
    InMemoryAuthorityRuntimeStore,
    PrincipalAuthorityRecord,
    PrincipalAuthorityResolver,
)
from modules.communication.moltbot_bridge.src.reddog_signer_authority_store_commit import (
    commit_issued_authority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_optional_authority_bindings import (
    attach_optional_authority_bindings,
    is_sha256_digest,
    optional_authority_bindings_valid,
    runtime_binding_request_valid,
)
from modules.communication.moltbot_bridge.src.reddog_work_authority_digest import (
    canonical_work_authority_digest,
)

AUTHORITY_ISSUED = "DELEGATED_AUTHORITY_ISSUED"
AUTHORITY_REJECTED = "DELEGATED_AUTHORITY_REJECTED"
AUTHORITY_SCHEMA_VERSION = "reddog_delegated_authority_runtime.v1"

LOW_AUTHORITY_TIER = "LOW"
HIGH_AUTHORITY_TIER = "HIGH"

HIGH_AUTHORITY_OPERATIONS = frozenset(
    {
        "create_foundup",
        "live_enqueue",
        "worktree_create",
        "write_repo",
        "run_shell",
        "publish_draft_pr",
        "merge_pr",
        "promote",
        "manage_permissions",
        "delete_repo",
        "force_push",
    }
)
HIGH_AUTHORITY_VALVE_STATES = frozenset(
    {"VALVE_OPEN_LIVE_ENQUEUE", "VALVE_OPEN_WORKTREE_CREATE"}
)

_FOUNDUP_PATH_PREFIX = "modules/foundups/"


class RuntimeRejectCode:
    MALFORMED_REQUEST = "REJECT_MALFORMED_REQUEST"
    NON_ASCII = "REJECT_NON_ASCII_FIELD"
    PRINCIPAL_NOT_VERIFIED = "REJECT_PRINCIPAL_NOT_VERIFIED"
    PRINCIPAL_KEY_MISMATCH = "REJECT_PRINCIPAL_KEY_MISMATCH"
    SCOPE_EXCEEDED = "REJECT_SCOPE_EXCEEDED"
    SNAPSHOT_STALE_OR_MISSING = "REJECT_SNAPSHOT_STALE_OR_MISSING"
    SNAPSHOT_DIGEST_MISMATCH = "REJECT_SNAPSHOT_DIGEST_MISMATCH"
    SNAPSHOT_INSUFFICIENT = "REJECT_SNAPSHOT_DOES_NOT_GRANT_OP"
    PATH_OUT_OF_SCOPE = "REJECT_PATH_OUT_OF_FOUNDUP_SCOPE"
    NONCE_REPLAY = "REJECT_NONCE_REPLAY"
    REVOKED = "REJECT_REVOKED"
    HIGH_AUTHORITY_NEEDS_COSIGN = "REJECT_HIGH_AUTHORITY_NEEDS_COSIGN"
    SIGNER_NOT_CONFIGURED = "REJECT_SIGNER_NOT_CONFIGURED"
    SIGNER_BOUNDARY_NOT_ATTESTED = "REJECT_SIGNER_BOUNDARY_NOT_ATTESTED"
    SIGNER_KEY_MISMATCH = "REJECT_SIGNER_KEY_MISMATCH"
    SIGNER_RESPONSE_INVALID = "REJECT_SIGNER_RESPONSE_INVALID"
    STORE_COMMIT_FAILED = "REJECT_STORE_COMMIT_FAILED"


def _is_ascii(value: Any) -> bool:
    return isinstance(value, str) and all(ord(char) < 128 for char in value)


def _assert_ascii_deep(value: Any) -> bool:
    if isinstance(value, str):
        return _is_ascii(value)
    if isinstance(value, Mapping):
        return all(_is_ascii(key) and _assert_ascii_deep(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_assert_ascii_deep(item) for item in value)
    return True


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def public_key_fingerprint(public_key: str) -> str:
    """Derive a public-only fingerprint. Never pass signing material here."""

    if not _is_ascii(public_key):
        raise ValueError("public key must be ASCII")
    return "sha256:" + hashlib.sha256(public_key.encode("utf-8")).hexdigest()


def _path_within_foundup(path: str, foundup_id: str) -> bool:
    if not isinstance(path, str) or not path or not _is_ascii(path):
        return False
    if "\x00" in path or "\\" in path or ":" in path or path.startswith("/"):
        return False
    if path.startswith("//?/") or path.startswith("//./"):
        return False
    prefix = f"{_FOUNDUP_PATH_PREFIX}{foundup_id}/"
    if not path.startswith(prefix):
        return False
    for segment in path.split("/"):
        if segment.strip(" \t") == ".." or segment.strip(" .\t") == "":
            return False
    return True


@dataclass(frozen=True)
class SigningRequest:
    """Request sent to an isolated signer. The body id is audit-only."""

    signing_input: str
    payload_digest: str
    signer_role: str
    signer_public_key: str
    requester_principal_id: str
    nonce: str
    key_epoch: str
    requested_operation: str
    authority_tier: str
    consensus_receipt_digest: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SigningResponse:
    """Response from an isolated signer. It must not include signing material."""

    accepted: bool
    signature: str = ""
    signer_public_key: str = ""
    key_fingerprint: str = ""
    key_epoch: str = ""
    audit_mac: str = ""
    audit_attestation_signature: str = ""
    rejection_code: str = ""
    boundary_attested: bool = False
    requester_identity_attested: bool = False
    signer_loads_no_untrusted_code: bool = False
    no_secret_material_returned: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class IsolatedSignerClient(Protocol):
    def sign(self, request: SigningRequest) -> SigningResponse:
        """Return a signature over request.signing_input, or reject fail-closed."""


class FailClosedSignerClient:
    def sign(self, request: SigningRequest) -> SigningResponse:
        return SigningResponse(
            accepted=False,
            rejection_code=RuntimeRejectCode.SIGNER_NOT_CONFIGURED,
            no_secret_material_returned=True,
        )


@dataclass(frozen=True)
class DelegatedAuthorityRuntimeRequest:
    work_order_id: str
    work_order_digest: str
    base_ref: str
    principal_id: str
    principal_provider: str
    principal_public_key: str
    reddog_id: str
    reddog_public_key: str
    repo_full_name: str
    foundup_id: str
    allowed_paths: Tuple[str, ...]
    denied_paths: Tuple[str, ...]
    requested_operation: str
    permission_snapshot_digest: str
    queue_consumer_receipt_digest: str
    wsp15_allocation_receipt_id: str
    wsp15_allocation_digest: str
    wsp15_priority: str
    wsp15_mps_total: int
    wsp15_reasoning_tier: str
    progressive_policy_stage_receipt_id: str
    progressive_policy_stage_digest: str
    progressive_policy_stage_receipt: Mapping[str, Any]
    identity_nonce: str
    work_authority_nonce: str
    issued_at: int
    identity_expires_at: int
    work_authority_expires_at: int
    valve_state_required: str
    key_epoch: str
    consensus_receipt_digest: Optional[str] = None
    sovereign_authorization_digest: Optional[str] = None
    model_selection_receipt_id: Optional[str] = None
    model_selection_digest: Optional[str] = None
    model_runtime_binding_receipt_id: Optional[str] = None
    model_runtime_binding_digest: Optional[str] = None
    model_runtime_binding_verification_receipt_id: Optional[str] = None
    model_runtime_binding_verification_digest: Optional[str] = None
    memex_supply_receipt_id: Optional[str] = None
    memex_supply_digest: Optional[str] = None
    architect_fix_publication_receipt_id: Optional[str] = None
    architect_fix_publication_binding_digest: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DelegatedAuthorityRuntimeReceipt:
    receipt_id: str
    status: str
    generated_at: int
    work_order_id: Optional[str]
    principal_id: Optional[str]
    reddog_id: Optional[str]
    identity_digest: Optional[str]
    work_authority_digest: Optional[str]
    store_revision: Optional[str]
    signer_audit_macs: Tuple[str, ...]
    rejection_reasons: Tuple[str, ...]
    no_signing_material_observed: bool = True
    no_execution_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_holoindex_mutation_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DelegatedAuthorityRuntimeResult:
    accepted: bool
    receipt: DelegatedAuthorityRuntimeReceipt
    identity: Optional[Dict[str, Any]] = None
    work_authority: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accepted": self.accepted,
            "receipt": self.receipt.to_dict(),
            "identity": self.identity,
            "work_authority": self.work_authority,
        }


def _rejection_result(
    *,
    now: int,
    request: Optional[DelegatedAuthorityRuntimeRequest],
    reasons: Sequence[str],
) -> DelegatedAuthorityRuntimeResult:
    payload = {
        "status": AUTHORITY_REJECTED,
        "work_order_id": request.work_order_id if request else None,
        "reasons": list(reasons),
        "generated_at": now,
    }
    receipt = DelegatedAuthorityRuntimeReceipt(
        receipt_id="authority-runtime-" + _canonical_digest(payload)[:16],
        status=AUTHORITY_REJECTED,
        generated_at=now,
        work_order_id=request.work_order_id if request else None,
        principal_id=request.principal_id if request else None,
        reddog_id=request.reddog_id if request else None,
        identity_digest=None,
        work_authority_digest=None,
        store_revision=None,
        signer_audit_macs=(),
        rejection_reasons=tuple(reasons),
    )
    return DelegatedAuthorityRuntimeResult(accepted=False, receipt=receipt)


def _snapshot_fresh(snapshot: PermissionSnapshot, *, now: int, leeway_s: int) -> bool:
    try:
        return snapshot.is_fresh(now, leeway_s)
    except Exception:
        return False


def _store_nonce_used(state: Mapping[str, Any], nonce: str) -> bool:
    nonces = state.get("nonces", {})
    if not isinstance(nonces, Mapping):
        return False
    identity_nonces = set(map(str, nonces.get("identity", [])))
    work_nonces = set(map(str, nonces.get("work_authority", [])))
    return nonce in identity_nonces or nonce in work_nonces


def _store_revoked(
    state: Mapping[str, Any],
    *,
    principal_id: str,
    reddog_id: str,
    reddog_fingerprint: str,
    key_epoch: str,
) -> bool:
    revocations = state.get("revocations", {})
    if not isinstance(revocations, Mapping):
        return False
    return (
        principal_id in set(map(str, revocations.get("principal_ids", [])))
        or reddog_id in set(map(str, revocations.get("reddog_ids", [])))
        or reddog_fingerprint in set(map(str, revocations.get("reddog_fingerprints", [])))
        or key_epoch in set(map(str, revocations.get("key_epochs", [])))
    )


def _validate_signing_response(
    response: SigningResponse,
    *,
    expected_public_key: str,
    expected_fingerprint: str,
    expected_key_epoch: str,
) -> Optional[str]:
    if not response.accepted:
        return response.rejection_code or RuntimeRejectCode.SIGNER_NOT_CONFIGURED
    if not response.signature or not _is_ascii(response.signature):
        return RuntimeRejectCode.SIGNER_RESPONSE_INVALID
    if response.signer_public_key != expected_public_key:
        return RuntimeRejectCode.SIGNER_KEY_MISMATCH
    if response.key_fingerprint != expected_fingerprint or response.key_epoch != expected_key_epoch:
        return RuntimeRejectCode.SIGNER_KEY_MISMATCH
    if not (
        response.boundary_attested
        and response.requester_identity_attested
        and response.signer_loads_no_untrusted_code
        and response.no_secret_material_returned
    ):
        return RuntimeRejectCode.SIGNER_BOUNDARY_NOT_ATTESTED
    if not response.audit_mac or not _is_ascii(response.audit_mac):
        return RuntimeRejectCode.SIGNER_RESPONSE_INVALID
    return None


def _progressive_stage_valid(request: DelegatedAuthorityRuntimeRequest) -> bool:
    from modules.communication.moltbot_bridge.src.reddog_progressive_execution_stage_policy import (
        validate_signed_progressive_stage_binding,
    )

    receipt = request.progressive_policy_stage_receipt
    return validate_signed_progressive_stage_binding(
        receipt,
        expected_receipt_id=request.progressive_policy_stage_receipt_id,
        expected_digest=request.progressive_policy_stage_digest,
    ) and (
        receipt.get("requested_operation") == request.requested_operation
        and tuple(receipt.get("changed_paths") or ()) == tuple(request.allowed_paths)
        and receipt.get("wsp15_allocation_receipt_id") == request.wsp15_allocation_receipt_id
        and receipt.get("wsp15_allocation_digest") == request.wsp15_allocation_digest
    )


def _effective_paths_valid(request: DelegatedAuthorityRuntimeRequest) -> bool:
    from modules.communication.moltbot_bridge.src.reddog_progressive_execution_stage_policy import (
        STAGE_AUDIT,
    )

    paths = set(request.allowed_paths) - set(request.denied_paths)
    audit_only = request.progressive_policy_stage_receipt.get("stage") == STAGE_AUDIT
    if audit_only:
        return not paths
    return bool(paths and all(_path_within_foundup(path, request.foundup_id) for path in paths))


def _request_receipt_bindings_valid(request: DelegatedAuthorityRuntimeRequest) -> bool:
    return bool(
        is_sha256_digest(request.queue_consumer_receipt_digest)
        and request.wsp15_allocation_receipt_id.startswith("sha256:")
        and request.wsp15_allocation_digest.startswith("sha256:")
        and request.wsp15_priority in {"P0", "P1", "P2", "P3", "P4"}
        and type(request.wsp15_mps_total) is int
        and request.wsp15_reasoning_tier in {"REGULAR", "HIGH", "ULTRA"}
        and is_sha256_digest(request.progressive_policy_stage_receipt_id)
        and is_sha256_digest(request.progressive_policy_stage_digest)
    )


def issue_delegated_authority_runtime(
    *,
    request: DelegatedAuthorityRuntimeRequest,
    store: AuthorityRuntimeStore,
    signer: Optional[IsolatedSignerClient] = None,
    principal_resolver: Optional[PrincipalAuthorityResolver] = None,
    snapshot_resolver: PermissionSnapshotResolver,
    now: int,
    leeway_s: int = 60,
) -> DelegatedAuthorityRuntimeResult:
    """Issue signed authority records through an injected isolated signer.

    The function performs no execution. It writes only the issued-authority
    receipt and nonce reservation through the provided store after both signing
    responses pass the E0 boundary-attestation checks.
    """

    signer_client = signer or FailClosedSignerClient()
    principal_lookup = principal_resolver or FailClosedPrincipalAuthorityResolver()

    if not isinstance(request, DelegatedAuthorityRuntimeRequest):
        return _rejection_result(now=now, request=None, reasons=[RuntimeRejectCode.MALFORMED_REQUEST])
    if not _assert_ascii_deep(request.to_dict()):
        return _rejection_result(now=now, request=request, reasons=[RuntimeRejectCode.NON_ASCII])
    if request.issued_at > now + leeway_s:
        return _rejection_result(now=now, request=request, reasons=[RuntimeRejectCode.MALFORMED_REQUEST])
    if request.identity_expires_at <= now or request.work_authority_expires_at <= now:
        return _rejection_result(now=now, request=request, reasons=[RuntimeRejectCode.MALFORMED_REQUEST])
    try:
        canonical_work_order_base_ref({"base_ref": request.base_ref})
    except ValueError:
        return _rejection_result(
            now=now,
            request=request,
            reasons=[RuntimeRejectCode.MALFORMED_REQUEST],
        )
    if not (
        request.work_order_digest.startswith("sha256:")
        and len(request.work_order_digest) == 71
        and all(
            char in "0123456789abcdef"
            for char in request.work_order_digest.removeprefix("sha256:")
        )
    ):
        return _rejection_result(
            now=now,
            request=request,
            reasons=[RuntimeRejectCode.MALFORMED_REQUEST],
        )
    if request.principal_public_key == request.reddog_public_key:
        return _rejection_result(now=now, request=request, reasons=[RuntimeRejectCode.PRINCIPAL_KEY_MISMATCH])

    try:
        principal = principal_lookup.resolve(request.principal_id, request.principal_provider)
    except Exception:
        principal = None
    if principal is None:
        return _rejection_result(now=now, request=request, reasons=[RuntimeRejectCode.PRINCIPAL_NOT_VERIFIED])
    if principal.principal_public_key != request.principal_public_key:
        return _rejection_result(now=now, request=request, reasons=[RuntimeRejectCode.PRINCIPAL_KEY_MISMATCH])
    repo_out = request.repo_full_name not in set(principal.repo_scope)
    foundup_out = request.foundup_id not in set(principal.foundup_scope)
    if repo_out or foundup_out:
        return _rejection_result(now=now, request=request, reasons=[RuntimeRejectCode.SCOPE_EXCEEDED])

    try:
        snapshot = snapshot_resolver.resolve(request.permission_snapshot_digest)
    except Exception:
        snapshot = None
    if snapshot is None or not _snapshot_fresh(snapshot, now=now, leeway_s=leeway_s):
        return _rejection_result(now=now, request=request, reasons=[RuntimeRejectCode.SNAPSHOT_STALE_OR_MISSING])
    if snapshot.evidence_digest != request.permission_snapshot_digest:
        return _rejection_result(now=now, request=request, reasons=[RuntimeRejectCode.SNAPSHOT_DIGEST_MISMATCH])
    if not snapshot.grants(request.requested_operation, request.repo_full_name):
        return _rejection_result(now=now, request=request, reasons=[RuntimeRejectCode.SNAPSHOT_INSUFFICIENT])
    if not _request_receipt_bindings_valid(request):
        return _rejection_result(now=now, request=request, reasons=[RuntimeRejectCode.MALFORMED_REQUEST])
    if not _progressive_stage_valid(request):
        return _rejection_result(
            now=now, request=request, reasons=[RuntimeRejectCode.MALFORMED_REQUEST]
        )
    has_runtime_binding = runtime_binding_request_valid(request)
    if has_runtime_binding is None:
        return _rejection_result(now=now, request=request, reasons=[RuntimeRejectCode.MALFORMED_REQUEST])
    if not optional_authority_bindings_valid(request):
        return _rejection_result(
            now=now,
            request=request,
            reasons=[RuntimeRejectCode.MALFORMED_REQUEST],
        )

    if not _effective_paths_valid(request):
        return _rejection_result(now=now, request=request, reasons=[RuntimeRejectCode.PATH_OUT_OF_SCOPE])

    authority_tier = (
        HIGH_AUTHORITY_TIER
        if request.requested_operation in HIGH_AUTHORITY_OPERATIONS
        or request.valve_state_required in HIGH_AUTHORITY_VALVE_STATES
        else LOW_AUTHORITY_TIER
    )
    if authority_tier == HIGH_AUTHORITY_TIER and not (
        request.consensus_receipt_digest and request.sovereign_authorization_digest
    ):
        return _rejection_result(
            now=now,
            request=request,
            reasons=[RuntimeRejectCode.HIGH_AUTHORITY_NEEDS_COSIGN],
        )

    state = store.load()
    if _store_nonce_used(state, request.identity_nonce) or _store_nonce_used(state, request.work_authority_nonce):
        return _rejection_result(now=now, request=request, reasons=[RuntimeRejectCode.NONCE_REPLAY])

    reddog_fingerprint = public_key_fingerprint(request.reddog_public_key)
    principal_fingerprint = public_key_fingerprint(request.principal_public_key)
    if _store_revoked(
        state,
        principal_id=request.principal_id,
        reddog_id=request.reddog_id,
        reddog_fingerprint=reddog_fingerprint,
        key_epoch=request.key_epoch,
    ):
        return _rejection_result(now=now, request=request, reasons=[RuntimeRejectCode.REVOKED])

    identity = {
        "principal_id": request.principal_id,
        "principal_provider": request.principal_provider,
        "principal_public_key": request.principal_public_key,
        "principal_key_fingerprint": principal_fingerprint,
        "principal_wallet": principal.principal_wallet,
        "reddog_id": request.reddog_id,
        "reddog_public_key": request.reddog_public_key,
        "reddog_key_fingerprint": reddog_fingerprint,
        "repo_scope": list(principal.repo_scope),
        "foundup_scope": list(principal.foundup_scope),
        "reward_account": principal.reward_account,
        "owner_dae": principal.owner_dae,
        "revocation_policy": {
            "ttl_seconds": max(0, request.identity_expires_at - request.issued_at),
            "allowlist_bound": True,
            "kill_switch_ref": f"reddog_revocation:{request.reddog_id}",
        },
        "identity_nonce": request.identity_nonce,
        "issued_at": request.issued_at,
        "expires_at": request.identity_expires_at,
    }
    identity_input = canonical_signing_input(identity, PREFIX_IDENTITY)
    identity_sign = signer_client.sign(
        SigningRequest(
            signing_input=identity_input,
            payload_digest="sha256:" + _canonical_digest({"signing_input": identity_input}),
            signer_role="principal",
            signer_public_key=request.principal_public_key,
            requester_principal_id=request.principal_id,
            nonce=request.identity_nonce,
            key_epoch=request.key_epoch,
            requested_operation="delegate_reddog_identity",
            authority_tier=authority_tier,
            consensus_receipt_digest=request.consensus_receipt_digest,
        )
    )
    reject = _validate_signing_response(
        identity_sign,
        expected_public_key=request.principal_public_key,
        expected_fingerprint=principal_fingerprint,
        expected_key_epoch=request.key_epoch,
    )
    if reject:
        return _rejection_result(now=now, request=request, reasons=[reject])
    identity["signature"] = identity_sign.signature

    work_authority = {
        "work_order_id": request.work_order_id,
        "work_order_digest": request.work_order_digest,
        "base_ref": request.base_ref,
        "principal_id": request.principal_id,
        "reddog_id": request.reddog_id,
        "repo_full_name": request.repo_full_name,
        "foundup_id": request.foundup_id,
        "allowed_paths": list(request.allowed_paths),
        "denied_paths": list(request.denied_paths),
        "requested_operation": request.requested_operation,
        "permission_snapshot_digest": request.permission_snapshot_digest,
        "queue_consumer_receipt_digest": request.queue_consumer_receipt_digest,
        "wsp15_allocation_receipt_id": request.wsp15_allocation_receipt_id,
        "wsp15_allocation_digest": request.wsp15_allocation_digest,
        "wsp15_priority": request.wsp15_priority,
        "wsp15_mps_total": request.wsp15_mps_total,
        "wsp15_reasoning_tier": request.wsp15_reasoning_tier,
        "progressive_policy_stage_receipt_id": (
            request.progressive_policy_stage_receipt_id
        ),
        "progressive_policy_stage_digest": request.progressive_policy_stage_digest,
        "progressive_policy_stage_receipt": dict(
            request.progressive_policy_stage_receipt
        ),
        "nonce": request.work_authority_nonce,
        "issued_at": request.issued_at,
        "expires_at": request.work_authority_expires_at,
        "valve_state_required": request.valve_state_required,
        "key_epoch": request.key_epoch,
        "signer_public_key": request.reddog_public_key,
        "authority_tier": authority_tier,
        "consensus_receipt_digest": request.consensus_receipt_digest,
        "sovereign_authorization_digest": request.sovereign_authorization_digest,
        "receipt_chain": [],
    }
    if has_runtime_binding:
        work_authority["model_runtime_binding_receipt_id"] = str(request.model_runtime_binding_receipt_id)
        work_authority["model_runtime_binding_digest"] = str(request.model_runtime_binding_digest)
    attach_optional_authority_bindings(work_authority, request)
    workauth_input = canonical_signing_input(work_authority, PREFIX_WORKAUTH)
    workauth_sign = signer_client.sign(
        SigningRequest(
            signing_input=workauth_input,
            payload_digest="sha256:" + _canonical_digest({"signing_input": workauth_input}),
            signer_role="reddog",
            signer_public_key=request.reddog_public_key,
            requester_principal_id=request.principal_id,
            nonce=request.work_authority_nonce,
            key_epoch=request.key_epoch,
            requested_operation=request.requested_operation,
            authority_tier=authority_tier,
            consensus_receipt_digest=request.consensus_receipt_digest,
        )
    )
    reject = _validate_signing_response(
        workauth_sign,
        expected_public_key=request.reddog_public_key,
        expected_fingerprint=reddog_fingerprint,
        expected_key_epoch=request.key_epoch,
    )
    if reject:
        return _rejection_result(now=now, request=request, reasons=[reject])
    work_authority["signature"] = workauth_sign.signature

    identity_digest = "sha256:" + _canonical_digest(identity)
    workauth_digest = canonical_work_authority_digest(work_authority)
    receipt_payload = {
        "status": AUTHORITY_ISSUED,
        "work_order_id": request.work_order_id,
        "identity_digest": identity_digest,
        "work_authority_digest": workauth_digest,
        "generated_at": now,
    }
    receipt_id = "authority-runtime-" + _canonical_digest(receipt_payload)[:16]
    try:
        revision = commit_issued_authority(
            store,
            request=request,
            identity_digest=identity_digest,
            work_authority_digest=workauth_digest,
            receipt_id=receipt_id, schema_version=AUTHORITY_SCHEMA_VERSION, issued_status=AUTHORITY_ISSUED,
        )
    except Exception:
        return _rejection_result(now=now, request=request, reasons=[RuntimeRejectCode.STORE_COMMIT_FAILED])

    receipt = DelegatedAuthorityRuntimeReceipt(
        receipt_id=receipt_id,
        status=AUTHORITY_ISSUED,
        generated_at=now,
        work_order_id=request.work_order_id,
        principal_id=request.principal_id,
        reddog_id=request.reddog_id,
        identity_digest=identity_digest,
        work_authority_digest=workauth_digest,
        store_revision=revision,
        signer_audit_macs=(identity_sign.audit_mac, workauth_sign.audit_mac),
        rejection_reasons=(),
    )
    return DelegatedAuthorityRuntimeResult(
        accepted=True,
        receipt=receipt,
        identity=identity,
        work_authority=work_authority,
    )


__all__ = [
    "AUTHORITY_ISSUED",
    "AUTHORITY_REJECTED",
    "AUTHORITY_SCHEMA_VERSION",
    "AtomicJsonAuthorityRuntimeStore",
    "DelegatedAuthorityRuntimeReceipt",
    "DelegatedAuthorityRuntimeRequest",
    "DelegatedAuthorityRuntimeResult",
    "FailClosedPrincipalAuthorityResolver",
    "FailClosedSignerClient",
    "HIGH_AUTHORITY_OPERATIONS",
    "HIGH_AUTHORITY_VALVE_STATES",
    "InMemoryAuthorityRuntimeStore",
    "IsolatedSignerClient",
    "PrincipalAuthorityRecord",
    "PrincipalAuthorityResolver",
    "RuntimeRejectCode",
    "SigningRequest",
    "SigningResponse",
    "issue_delegated_authority_runtime",
    "public_key_fingerprint",
]
