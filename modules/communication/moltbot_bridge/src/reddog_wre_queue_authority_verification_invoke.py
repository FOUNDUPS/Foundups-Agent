"""RedDog WRE queue authority verification explicit invoke guard.

Slice: REDDOG_WRE_QUEUE_AUTHORITY_VERIFICATION_INVOKE_PHASE1

This module verifies a signed authority result emitted by the queue authority
runtime. It calls the existing RedDog work-order signature verifier only behind
an explicit invoke flag and injected verifier/resolver/nonce/revocation
boundaries. It does not issue signatures, spawn workers, create worktrees, run
shell commands, enqueue OpenClaw, dispatch Hermes, mutate repository files,
publish PRs, settle rewards, or re-index HoloIndex.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    AUTHORITY_ISSUED,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_runtime_invoke import (
    QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    NonceStore,
    PermissionSnapshotResolver,
    PrincipalKeyResolver,
    RevocationOracle,
    SignatureVerifier,
    VerificationResult,
    WorkAuthorityVerificationPhase,
    verify_delegated_work_authority,
)


QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT = "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT"
QUEUE_AUTHORITY_VERIFICATION_INVOKE_REJECT = "QUEUE_AUTHORITY_VERIFICATION_INVOKE_REJECT"


class QueueAuthorityVerificationInvokeReason:
    EXPLICIT_INVOKE_MISSING = "REJECT_EXPLICIT_QUEUE_AUTHORITY_VERIFICATION_INVOKE_MISSING"
    AUTHORITY_RUNTIME_NOT_ACCEPTED = "REJECT_QUEUE_AUTHORITY_RUNTIME_NOT_ACCEPTED"
    AUTHORITY_PAYLOAD_MISSING = "REJECT_AUTHORITY_PAYLOAD_MISSING"
    SIGNATURE_VERIFIER_REJECTED = "REJECT_SIGNATURE_VERIFIER_REJECTED"


@dataclass(frozen=True)
class QueueAuthorityVerificationInvokeResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    verification_result: Optional[VerificationResult] = None
    explicit_queue_authority_verification_requested: bool = False
    no_signing_performed: bool = True
    no_authority_issued: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["verification_result"] = (
            self.verification_result.to_dict() if self.verification_result else None
        )
        return payload


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return value
    return {}


def _reject(
    reasons: Sequence[str],
    *,
    explicit_requested: bool,
    verification_result: Optional[VerificationResult] = None,
) -> QueueAuthorityVerificationInvokeResult:
    return QueueAuthorityVerificationInvokeResult(
        decision=QUEUE_AUTHORITY_VERIFICATION_INVOKE_REJECT,
        rejection_reasons=list(dict.fromkeys(reasons)),
        verification_result=verification_result,
        explicit_queue_authority_verification_requested=explicit_requested,
    )


def invoke_reddog_wre_queue_authority_verification(
    *,
    explicit_queue_authority_verification_requested: bool,
    queue_authority_runtime_result: Mapping[str, Any],
    signature_verifier: SignatureVerifier,
    principal_key_resolver: PrincipalKeyResolver,
    nonce_store: NonceStore,
    snapshot_resolver: PermissionSnapshotResolver,
    revocation_oracle: RevocationOracle,
    now: int,
    required_valve_state: str,
    forbidden_operations: Sequence[str] = (),
    revoked_key_epochs: Sequence[str] = (),
    leeway_s: int = 60,
) -> QueueAuthorityVerificationInvokeResult:
    """Verify queue-derived authority without executing the authorized work."""

    if explicit_queue_authority_verification_requested is not True:
        return _reject(
            [QueueAuthorityVerificationInvokeReason.EXPLICIT_INVOKE_MISSING],
            explicit_requested=False,
        )

    runtime = _mapping(queue_authority_runtime_result)
    authority = _mapping(runtime.get("authority_result"))
    receipt = _mapping(authority.get("receipt"))
    if (
        runtime.get("decision") != QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT
        or not authority.get("accepted")
        or receipt.get("status") != AUTHORITY_ISSUED
    ):
        return _reject(
            [QueueAuthorityVerificationInvokeReason.AUTHORITY_RUNTIME_NOT_ACCEPTED],
            explicit_requested=True,
        )

    identity = _mapping(authority.get("identity"))
    work_authority = _mapping(authority.get("work_authority"))
    if not identity or not work_authority:
        return _reject(
            [QueueAuthorityVerificationInvokeReason.AUTHORITY_PAYLOAD_MISSING],
            explicit_requested=True,
        )

    verification = verify_delegated_work_authority(
        work_authority=work_authority,
        identity=identity,
        signature_verifier=signature_verifier,
        principal_key_resolver=principal_key_resolver,
        nonce_store=nonce_store,
        snapshot_resolver=snapshot_resolver,
        revocation_oracle=revocation_oracle,
        now=now,
        required_valve_state=required_valve_state,
        forbidden_operations=forbidden_operations,
        revoked_key_epochs=revoked_key_epochs,
        leeway_s=leeway_s,
        verification_phase=WorkAuthorityVerificationPhase.PREFLIGHT_NON_CONSUMING,
    )
    if verification.accepted is not True:
        return _reject(
            [
                QueueAuthorityVerificationInvokeReason.SIGNATURE_VERIFIER_REJECTED,
                *verification.reason_codes,
            ],
            explicit_requested=True,
            verification_result=verification,
        )

    return QueueAuthorityVerificationInvokeResult(
        decision=QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
        rejection_reasons=[],
        verification_result=verification,
        explicit_queue_authority_verification_requested=True,
    )


__all__ = [
    "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT",
    "QUEUE_AUTHORITY_VERIFICATION_INVOKE_REJECT",
    "QueueAuthorityVerificationInvokeReason",
    "QueueAuthorityVerificationInvokeResult",
    "invoke_reddog_wre_queue_authority_verification",
]
