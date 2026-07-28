"""RedDog WRE queue authority runtime explicit invoke guard.

Slice: REDDOG_WRE_QUEUE_AUTHORITY_RUNTIME_INVOKE_PHASE1

This module invokes the existing delegated-authority signer runtime from an
accepted queue-authority request dry-run. It requires an explicit invoke flag
and injected signer, principal resolver, snapshot resolver, and authority
store. It may issue signed authority records through that injected signer
boundary, but it never executes work, creates worktrees, runs shell commands,
enqueues OpenClaw, dispatches Hermes, publishes PRs, settles rewards, or
re-indexes HoloIndex.
"""

from __future__ import annotations

import hmac
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    AUTHORITY_ISSUED,
    AUTHORITY_REJECTED,
    AuthorityRuntimeStore,
    DelegatedAuthorityRuntimeResult,
    IsolatedSignerClient,
    PermissionSnapshotResolver,
    PrincipalAuthorityResolver,
    issue_delegated_authority_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_request_dryrun import (
    QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_request_integrity import (
    canonical_delegated_authority_request_digest,
    rehydrate_delegated_authority_request,
)


QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT = "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT"
QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT = "QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT"


class QueueAuthorityRuntimeInvokeReason:
    EXPLICIT_INVOKE_MISSING = "REJECT_EXPLICIT_QUEUE_AUTHORITY_RUNTIME_INVOKE_MISSING"
    REQUEST_DRYRUN_NOT_ACCEPTED = "REJECT_QUEUE_AUTHORITY_REQUEST_DRYRUN_NOT_ACCEPTED"
    REQUEST_PAYLOAD_MISSING = "REJECT_DELEGATED_AUTHORITY_REQUEST_MISSING"
    REQUEST_PAYLOAD_INVALID = "REJECT_DELEGATED_AUTHORITY_REQUEST_INVALID"
    REQUEST_DIGEST_MISMATCH = "REJECT_DELEGATED_AUTHORITY_REQUEST_DIGEST_MISMATCH"
    AUTHORITY_RUNTIME_REJECTED = "REJECT_DELEGATED_AUTHORITY_RUNTIME_REJECTED"


@dataclass(frozen=True)
class QueueAuthorityRuntimeInvokeResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    authority_result: Optional[DelegatedAuthorityRuntimeResult] = None
    explicit_queue_authority_runtime_requested: bool = False
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
        payload["authority_result"] = (
            self.authority_result.to_dict() if self.authority_result else None
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
    authority_result: Optional[DelegatedAuthorityRuntimeResult] = None,
) -> QueueAuthorityRuntimeInvokeResult:
    return QueueAuthorityRuntimeInvokeResult(
        decision=QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT,
        rejection_reasons=list(dict.fromkeys(reasons)),
        authority_result=authority_result,
        explicit_queue_authority_runtime_requested=explicit_requested,
    )


def invoke_reddog_wre_queue_authority_runtime(
    *,
    explicit_queue_authority_runtime_requested: bool,
    queue_authority_request_dryrun: Mapping[str, Any],
    store: AuthorityRuntimeStore,
    signer: Optional[IsolatedSignerClient],
    principal_resolver: Optional[PrincipalAuthorityResolver],
    snapshot_resolver: PermissionSnapshotResolver,
    now: int,
    leeway_s: int = 60,
) -> QueueAuthorityRuntimeInvokeResult:
    """Invoke delegated authority issuance for a queue-derived request."""

    if explicit_queue_authority_runtime_requested is not True:
        return _reject(
            [QueueAuthorityRuntimeInvokeReason.EXPLICIT_INVOKE_MISSING],
            explicit_requested=False,
        )

    dryrun = _mapping(queue_authority_request_dryrun)
    if dryrun.get("accepted") is not True or dryrun.get("status") != QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT:
        return _reject(
            [QueueAuthorityRuntimeInvokeReason.REQUEST_DRYRUN_NOT_ACCEPTED],
            explicit_requested=True,
        )
    request_payload = _mapping(dryrun.get("delegated_authority_request"))
    if not request_payload:
        return _reject(
            [QueueAuthorityRuntimeInvokeReason.REQUEST_PAYLOAD_MISSING],
            explicit_requested=True,
        )
    receipt = _mapping(dryrun.get("receipt"))
    recorded_digest = receipt.get("delegated_authority_request_digest")
    try:
        current_digest = canonical_delegated_authority_request_digest(
            request_payload
        )
        request = rehydrate_delegated_authority_request(request_payload)
    except Exception:
        return _reject(
            [QueueAuthorityRuntimeInvokeReason.REQUEST_PAYLOAD_INVALID],
            explicit_requested=True,
        )
    if not isinstance(recorded_digest, str) or not hmac.compare_digest(
        current_digest,
        recorded_digest,
    ):
        return _reject(
            [QueueAuthorityRuntimeInvokeReason.REQUEST_DIGEST_MISMATCH],
            explicit_requested=True,
        )

    authority = issue_delegated_authority_runtime(
        request=request,
        store=store,
        signer=signer,
        principal_resolver=principal_resolver,
        snapshot_resolver=snapshot_resolver,
        now=now,
        leeway_s=leeway_s,
    )
    if not authority.accepted or authority.receipt.status != AUTHORITY_ISSUED:
        reasons = [QueueAuthorityRuntimeInvokeReason.AUTHORITY_RUNTIME_REJECTED]
        if authority.receipt.status == AUTHORITY_REJECTED:
            reasons.extend(authority.receipt.rejection_reasons)
        return _reject(
            reasons,
            explicit_requested=True,
            authority_result=authority,
        )

    return QueueAuthorityRuntimeInvokeResult(
        decision=QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
        rejection_reasons=[],
        authority_result=authority,
        explicit_queue_authority_runtime_requested=True,
    )


__all__ = [
    "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT",
    "QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT",
    "QueueAuthorityRuntimeInvokeReason",
    "QueueAuthorityRuntimeInvokeResult",
    "invoke_reddog_wre_queue_authority_runtime",
]
