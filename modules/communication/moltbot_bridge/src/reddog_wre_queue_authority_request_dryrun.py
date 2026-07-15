"""RedDog WRE queue to delegated-authority request dry-run.

Slice: REDDOG_WRE_QUEUE_AUTHORITY_REQUEST_DRYRUN_PHASE1

This module bridges the accepted WRE queue consumer dry-run to the existing
RedDog delegated-authority signer runtime by constructing a
DelegatedAuthorityRuntimeRequest from an explicit FoundUp authority profile. It
does not sign, verify signatures, mutate signer state, spawn workers, create
worktrees, execute shell commands, enqueue OpenClaw, dispatch Hermes, publish
PRs, settle rewards, or re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    DelegatedAuthorityRuntimeRequest,
    HIGH_AUTHORITY_OPERATIONS,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_consumer_dryrun import (
    NEXT_GATE_SIGNED_AUTHORITY_REQUIRED,
    WRE_QUEUE_CONSUMER_DRYRUN_READY,
)


QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT = "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT"
QUEUE_AUTHORITY_REQUEST_DRYRUN_REJECT = "QUEUE_AUTHORITY_REQUEST_DRYRUN_REJECT"

FAIL_QUEUE_CONSUMER_NOT_READY = "FAIL_QUEUE_CONSUMER_NOT_READY"
FAIL_PROFILE_MISSING = "FAIL_PROFILE_MISSING"
FAIL_PROFILE_NON_ASCII = "FAIL_PROFILE_NON_ASCII"
FAIL_REQUIRED_FIELD = "FAIL_REQUIRED_FIELD"
FAIL_ALLOWED_PATH_SCOPE = "FAIL_ALLOWED_PATH_SCOPE"
FAIL_DENIED_PATH_SCOPE = "FAIL_DENIED_PATH_SCOPE"
FAIL_HIGH_AUTHORITY_COSIGN = "FAIL_HIGH_AUTHORITY_COSIGN"
FAIL_UNSUPPORTED_REPO_WIDE_AUTHORITY = "FAIL_UNSUPPORTED_REPO_WIDE_AUTHORITY"
FAIL_WSP15_ALLOCATION_BINDING = "FAIL_WSP15_ALLOCATION_BINDING"

_REQUIRED_PROFILE_FIELDS = (
    "principal_id",
    "principal_provider",
    "principal_public_key",
    "reddog_id",
    "reddog_public_key",
    "repo_full_name",
    "foundup_id",
    "allowed_paths",
    "requested_operation",
    "permission_snapshot_digest",
    "identity_nonce",
    "work_authority_nonce",
    "issued_at",
    "identity_expires_at",
    "work_authority_expires_at",
    "valve_state_required",
    "key_epoch",
)


@dataclass(frozen=True)
class QueueAuthorityRequestDryRunReceipt:
    receipt_id: str
    queue_consumer_receipt_digest: str
    queue_item_id: str
    slice_id: str
    work_order_id: str
    requested_operation: str
    foundup_id: str
    allowed_paths: Tuple[str, ...]
    denied_paths: Tuple[str, ...]
    wsp15_allocation_receipt_id: str
    wsp15_priority: str
    wsp15_mps_total: int
    reasoning_tier: str
    delegated_authority_request_digest: str
    signer_invoked: bool = False
    signature_verified: bool = False
    execution_ready: bool = False
    no_signing_performed: bool = True
    no_signer_state_mutation_performed: bool = True
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
        return asdict(self)


@dataclass(frozen=True)
class QueueAuthorityRequestDryRunResult:
    accepted: bool
    status: str
    rejection_reasons: List[str]
    receipt: Optional[QueueAuthorityRequestDryRunReceipt]
    delegated_authority_request: Optional[Dict[str, Any]]
    execution_ready: bool = False
    signer_invoked: bool = False
    no_signing_performed: bool = True
    no_signer_state_mutation_performed: bool = True
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
        payload["receipt"] = self.receipt.to_dict() if self.receipt else None
        return payload


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _dedupe(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return value
    return {}


def _is_ascii_deep(value: Any) -> bool:
    if isinstance(value, str):
        return all(ord(char) < 128 for char in value)
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and _is_ascii_deep(key) and _is_ascii_deep(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_is_ascii_deep(item) for item in value)
    return True


def _string_tuple(value: Any) -> Tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    return ()


def _valid_queue_wsp15_binding(queue_receipt: Mapping[str, Any], profile: Mapping[str, Any]) -> bool:
    receipt_id = str(queue_receipt.get("wsp15_allocation_receipt_id") or "")
    priority = str(queue_receipt.get("wsp15_priority") or "")
    tier = str(queue_receipt.get("reasoning_tier") or "")
    mps_total = queue_receipt.get("wsp15_mps_total")
    if not receipt_id.startswith("sha256:") or not priority or not tier or not isinstance(mps_total, int):
        return False
    profile_receipt = _mapping(profile.get("wsp15_allocation_receipt"))
    if not profile_receipt:
        return True
    profile_receipt_id = str(profile_receipt.get("receipt_id") or "")
    if profile_receipt_id and profile_receipt_id != receipt_id:
        return False
    profile_priority = str(profile_receipt.get("priority") or "")
    if profile_priority and profile_priority != priority:
        return False
    profile_tier = str(profile_receipt.get("reasoning_tier") or "")
    if profile_tier and profile_tier != tier:
        return False
    profile_total = profile_receipt.get("mps_total")
    if isinstance(profile_total, int) and profile_total != mps_total:
        return False
    return True


def _path_within_foundup(path: str, foundup_id: str) -> bool:
    if not path or "\\" in path or ":" in path or path.startswith("/") or "\x00" in path:
        return False
    if path.startswith("//?/") or path.startswith("//./"):
        return False
    prefix = f"modules/foundups/{foundup_id}/"
    if not path.startswith(prefix):
        return False
    for segment in path.split("/"):
        if segment.strip(" \t") == ".." or segment.strip(" .\t") == "":
            return False
    return True


def _work_order_id(queue_item_id: str) -> str:
    return "wre-queue-" + hashlib.sha256(queue_item_id.encode("utf-8")).hexdigest()[:16]


def _reject(reasons: Iterable[str]) -> QueueAuthorityRequestDryRunResult:
    return QueueAuthorityRequestDryRunResult(
        accepted=False,
        status=QUEUE_AUTHORITY_REQUEST_DRYRUN_REJECT,
        rejection_reasons=_dedupe(reasons),
        receipt=None,
        delegated_authority_request=None,
    )


def plan_reddog_wre_queue_authority_request_dry_run(
    *,
    queue_consumer_result: Mapping[str, Any],
    authority_profile: Mapping[str, Any] | None,
) -> QueueAuthorityRequestDryRunResult:
    """Build a signer-runtime request from a validated queue-consumer receipt."""

    queue = _mapping(queue_consumer_result)
    queue_receipt = _mapping(queue.get("receipt"))
    reasons: List[str] = []
    if (
        queue.get("accepted") is not True
        or queue.get("status") != WRE_QUEUE_CONSUMER_DRYRUN_READY
        or queue.get("next_required_gate") != NEXT_GATE_SIGNED_AUTHORITY_REQUIRED
        or queue.get("execution_ready") is not False
        or not queue_receipt
    ):
        reasons.append(FAIL_QUEUE_CONSUMER_NOT_READY)
    profile = _mapping(authority_profile)
    if not profile:
        reasons.append(FAIL_PROFILE_MISSING)
    elif not _is_ascii_deep(profile):
        reasons.append(FAIL_PROFILE_NON_ASCII)

    if queue_receipt and profile and not _valid_queue_wsp15_binding(queue_receipt, profile):
        reasons.append(FAIL_WSP15_ALLOCATION_BINDING)

    missing = [field for field in _REQUIRED_PROFILE_FIELDS if field not in profile or profile.get(field) in (None, "", ())]
    if missing:
        reasons.extend(f"{FAIL_REQUIRED_FIELD}:{field}" for field in missing)

    foundup_id = str(profile.get("foundup_id") or "")
    allowed_paths = _string_tuple(profile.get("allowed_paths"))
    denied_paths = _string_tuple(profile.get("denied_paths"))
    if allowed_paths and foundup_id and not all(_path_within_foundup(path, foundup_id) for path in allowed_paths):
        reasons.append(FAIL_ALLOWED_PATH_SCOPE)
    if denied_paths and foundup_id and not all(_path_within_foundup(path, foundup_id) for path in denied_paths):
        reasons.append(FAIL_DENIED_PATH_SCOPE)
    if not foundup_id or foundup_id in {"*", "repo", "root", "all"}:
        reasons.append(FAIL_UNSUPPORTED_REPO_WIDE_AUTHORITY)

    operation = str(profile.get("requested_operation") or "")
    if operation in HIGH_AUTHORITY_OPERATIONS and not (
        profile.get("consensus_receipt_digest") and profile.get("sovereign_authorization_digest")
    ):
        reasons.append(FAIL_HIGH_AUTHORITY_COSIGN)

    deduped = _dedupe(reasons)
    if deduped:
        return _reject(deduped)

    queue_item_id = str(queue_receipt.get("queue_item_id") or queue.get("selected_queue_item_id") or "")
    request = DelegatedAuthorityRuntimeRequest(
        work_order_id=str(profile.get("work_order_id") or _work_order_id(queue_item_id)),
        principal_id=str(profile["principal_id"]),
        principal_provider=str(profile["principal_provider"]),
        principal_public_key=str(profile["principal_public_key"]),
        reddog_id=str(profile["reddog_id"]),
        reddog_public_key=str(profile["reddog_public_key"]),
        repo_full_name=str(profile["repo_full_name"]),
        foundup_id=foundup_id,
        allowed_paths=allowed_paths,
        denied_paths=denied_paths,
        requested_operation=operation,
        permission_snapshot_digest=str(profile["permission_snapshot_digest"]),
        identity_nonce=str(profile["identity_nonce"]),
        work_authority_nonce=str(profile["work_authority_nonce"]),
        issued_at=int(profile["issued_at"]),
        identity_expires_at=int(profile["identity_expires_at"]),
        work_authority_expires_at=int(profile["work_authority_expires_at"]),
        valve_state_required=str(profile["valve_state_required"]),
        key_epoch=str(profile["key_epoch"]),
        consensus_receipt_digest=(
            str(profile["consensus_receipt_digest"]) if profile.get("consensus_receipt_digest") else None
        ),
        sovereign_authorization_digest=(
            str(profile["sovereign_authorization_digest"]) if profile.get("sovereign_authorization_digest") else None
        ),
    )
    request_dict = request.to_dict()
    request_digest = _digest(request_dict)
    receipt = QueueAuthorityRequestDryRunReceipt(
        receipt_id="queue_auth_req_" + _digest(
            {
                "queue_receipt": queue_receipt,
                "request_digest": request_digest,
            }
        ).removeprefix("sha256:")[:16],
        queue_consumer_receipt_digest=_digest(queue_receipt),
        queue_item_id=queue_item_id,
        slice_id=str(queue_receipt.get("slice_id") or queue.get("selected_slice") or ""),
        work_order_id=request.work_order_id,
        requested_operation=request.requested_operation,
        foundup_id=request.foundup_id,
        allowed_paths=request.allowed_paths,
        denied_paths=request.denied_paths,
        wsp15_allocation_receipt_id=str(queue_receipt.get("wsp15_allocation_receipt_id") or ""),
        wsp15_priority=str(queue_receipt.get("wsp15_priority") or ""),
        wsp15_mps_total=int(queue_receipt.get("wsp15_mps_total")),
        reasoning_tier=str(queue_receipt.get("reasoning_tier") or ""),
        delegated_authority_request_digest=request_digest,
    )
    return QueueAuthorityRequestDryRunResult(
        accepted=True,
        status=QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT,
        rejection_reasons=[],
        receipt=receipt,
        delegated_authority_request=request_dict,
        execution_ready=False,
    )


__all__ = [
    "FAIL_ALLOWED_PATH_SCOPE",
    "FAIL_DENIED_PATH_SCOPE",
    "FAIL_HIGH_AUTHORITY_COSIGN",
    "FAIL_PROFILE_MISSING",
    "FAIL_PROFILE_NON_ASCII",
    "FAIL_QUEUE_CONSUMER_NOT_READY",
    "FAIL_REQUIRED_FIELD",
    "FAIL_UNSUPPORTED_REPO_WIDE_AUTHORITY",
    "FAIL_WSP15_ALLOCATION_BINDING",
    "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT",
    "QUEUE_AUTHORITY_REQUEST_DRYRUN_REJECT",
    "QueueAuthorityRequestDryRunReceipt",
    "QueueAuthorityRequestDryRunResult",
    "plan_reddog_wre_queue_authority_request_dry_run",
]
