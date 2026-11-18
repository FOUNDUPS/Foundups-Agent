"""Append-only, signed receipts for the resident RedDog control loop.

Slice: REDDOG_RESIDENT_CONTROL_RECEIPT_TRUTH_AUTH_CONCURRENCY_PHASE1

Current v2 receipts derive effects from stage and OpenClaw claim evidence, bind
the preceding receipt, and can be attested by the isolated RedDog signer. Legacy
v1 receipts remain readable for migration, but cannot satisfy authenticated live
proof. This module records completed work; it never invokes a worker or command.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_receipt_auth import (
    CONTROL_LOOP_AUTHENTICATED,
    CONTROL_LOOP_DISPLAY_ONLY,
    ControlLoopReceiptSigningContext,
    attest_control_receipt,
    control_receipt_authentication_fields,
    validate_control_receipt_child_evidence,
    verify_control_receipt_authentication,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_receipt_validation import (
    strict_nonnegative_int,
    strict_string_tuple,
    validate_current_receipt_fields,
)
from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_chain_state import (
    validate_control_receipt_chain_state,
)
from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_outcomes import (
    derive_child_outcome_projections,
    strict_child_outcomes,
)
from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_effects import (
    derive_control_loop_effects,
    reject_contradictory_effect_claims,
)
from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_head_store import (
    commit_next_control_receipt_head,
    load_control_receipt_head,
    reconcile_control_receipt_head,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
    secure_append_runtime_text,
    secure_read_confined_bytes,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


CONTROL_LOOP_RECEIPT_SCHEMA_VERSION = "reddog_resident_control_loop_receipt.v2"
LEGACY_CONTROL_LOOP_RECEIPT_SCHEMA_VERSION = "reddog_resident_control_loop_receipt.v1"
MAX_CONTROL_RECEIPT_CHAIN_BYTES = 1024 * 1024
@dataclass(frozen=True)
class ResidentControlLoopReceipt:
    schema_version: str
    receipt_id: str
    sequence_number: int
    cycle_id: str
    nonce: str
    previous_receipt_id: str
    legacy_prefix_digest: str
    accepted: bool
    status: str
    rounds: int
    serial_progress: int
    claim_progress: int
    receipt_ids: tuple[str, ...]
    source_receipt_ids_digest: str
    child_execution_receipt_ids: tuple[str, ...]
    child_execution_evidence_digests: tuple[str, ...]
    child_execution_outcomes: tuple[dict[str, Any], ...]
    child_execution_evidence_digest: str
    child_execution_evidence_count: int
    rejection_reasons: tuple[str, ...]
    created_at: str
    repo_root_digest: str
    control_lock_acquired: bool
    dispatched_stages: tuple[str, ...]
    authority_issuance_count: int
    worker_claim_count: int
    worker_execution_count: int
    worker_completion_count: int
    worker_requeue_count: int
    worker_failure_count: int
    worktree_creation_count: int
    bounded_file_edit_count: int
    slice_verification_count: int
    draft_pr_publish_count: int
    pattern_memory_admission_count: int
    worker_process_spawn_count: int
    shell_command_count: int
    worker_effects_unverified_count: int
    authority_issued: bool
    worker_claim_performed: bool
    worker_execution_performed: bool
    worktree_creation_observed: bool
    bounded_file_edit_observed: bool
    slice_verification_observed: bool
    draft_pr_publish_observed: bool
    pattern_memory_admission_observed: bool
    worker_process_spawn_observed: bool
    shell_command_execution_observed: bool
    issuer_principal_id: str
    signer_public_key: str
    signer_key_fingerprint: str
    key_epoch: str
    consensus_receipt_digest: str
    authority_profile_digest: str
    authority_profile_source_receipt_id: str
    signature: str
    signer_audit_mac: str
    signer_audit_attestation_signature: str
    authentication_status: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["receipt_ids"] = list(self.receipt_ids)
        payload["child_execution_receipt_ids"] = list(
            self.child_execution_receipt_ids
        )
        payload["child_execution_evidence_digests"] = list(
            self.child_execution_evidence_digests
        )
        payload["child_execution_outcomes"] = [
            dict(outcome) for outcome in self.child_execution_outcomes
        ]
        payload["rejection_reasons"] = list(self.rejection_reasons)
        payload["dispatched_stages"] = list(self.dispatched_stages)
        return payload


def build_resident_control_loop_receipt(
    *,
    result: Mapping[str, Any],
    repo_root: Path | str,
    created_at: str,
    cycle_id: str | None = None, nonce: str | None = None,
    previous_receipt_id: str = "",
    legacy_prefix_digest: str | None = None,
    sequence_number: int = 1,
    signing_context: ControlLoopReceiptSigningContext | None = None,
) -> ResidentControlLoopReceipt:
    """Build one effect-derived receipt and optionally attest it."""
    dispatched_stages = _string_tuple(result.get("dispatched_stages"), max_chars=80)
    claim_progress = _int(result.get("claim_progress"))
    effects = derive_control_loop_effects(dispatched_stages, claim_progress, result)
    reject_contradictory_effect_claims(result, effects)
    receipt_ids = _string_tuple(result.get("receipt_ids"), max_chars=256)
    child_outcomes, child_receipt_ids, child_evidence_digests = derive_child_outcome_projections(result)
    payload: dict[str, Any] = {
        "schema_version": CONTROL_LOOP_RECEIPT_SCHEMA_VERSION,
        "sequence_number": sequence_number,
        "cycle_id": _bounded_text(cycle_id, 160) or _new_cycle_id(),
        "nonce": _bounded_text(nonce, 192) or _new_nonce(),
        "previous_receipt_id": _bounded_text(previous_receipt_id, 160),
        "legacy_prefix_digest": legacy_prefix_digest or _legacy_prefix_digest(()),
        "accepted": result.get("accepted") is True,
        "status": _bounded_text(result.get("status"), 80),
        "rounds": _int(result.get("rounds")),
        "serial_progress": _int(result.get("serial_progress")),
        "claim_progress": claim_progress,
        "receipt_ids": receipt_ids,
        "source_receipt_ids_digest": "sha256:" + _digest(list(receipt_ids)),
        "child_execution_receipt_ids": child_receipt_ids,
        "child_execution_evidence_digests": child_evidence_digests,
        "child_execution_outcomes": child_outcomes,
        "child_execution_evidence_digest": "sha256:" + _digest(list(child_evidence_digests)),
        "child_execution_evidence_count": len(child_evidence_digests),
        "rejection_reasons": _string_tuple(result.get("rejection_reasons"), max_chars=512),
        "created_at": _bounded_text(created_at, 80),
        "repo_root_digest": _digest(str(Path(repo_root).resolve())),
        "control_lock_acquired": result.get("control_lock_acquired") is True,
        "dispatched_stages": dispatched_stages,
        **effects,
        **control_receipt_authentication_fields(signing_context),
    }
    payload["receipt_id"] = _receipt_id(payload)
    if signing_context is not None:
        attest_control_receipt(payload, signing_context)
    return _verify_built_receipt(payload, signing_context)


def _verify_built_receipt(
    payload: Mapping[str, Any],
    signing_context: ControlLoopReceiptSigningContext | None,
) -> ResidentControlLoopReceipt:
    return verify_resident_control_loop_receipt(
        payload,
        expected_signer_public_key=(
            signing_context.signer_public_key if signing_context else None
        ),
        expected_key_epoch=signing_context.key_epoch if signing_context else None,
        expected_consensus_receipt_digest=(
            signing_context.consensus_receipt_digest if signing_context else None
        ),
        expected_authority_profile_digest=(
            signing_context.authority_profile_digest if signing_context else None
        ),
        expected_authority_profile_source_receipt_id=(
            signing_context.authority_profile_source_receipt_id
            if signing_context
            else None
        ),
        expected_issuer_principal_id=(
            signing_context.issuer_principal_id if signing_context else None
        ),
        require_authenticated=signing_context is not None,
        signature_verifier=(
            signing_context.signature_verifier if signing_context else None
        ),
    )


def verify_resident_control_loop_receipt(
    value: Mapping[str, Any],
    *,
    expected_repo_root: Path | str | None = None,
    expected_signer_public_key: str | None = None,
    expected_key_epoch: str | None = None,
    expected_consensus_receipt_digest: str | None = None,
    expected_authority_profile_digest: str | None = None,
    expected_authority_profile_source_receipt_id: str | None = None,
    expected_issuer_principal_id: str | None = None,
    require_authenticated: bool = False,
    signature_verifier: SignatureVerifier | None = None,
) -> ResidentControlLoopReceipt:
    """Rehydrate a current receipt after integrity, truth, and auth checks."""

    payload = dict(value)
    if payload.get("schema_version") != CONTROL_LOOP_RECEIPT_SCHEMA_VERSION:
        raise ValueError("resident_control_loop_receipt_schema_invalid")
    if set(payload) != set(ResidentControlLoopReceipt.__dataclass_fields__):
        raise ValueError("resident_control_loop_receipt_fields_invalid")
    if payload.get("receipt_id") != _receipt_id(payload):
        raise ValueError("resident_control_loop_receipt_digest_invalid")
    stages, receipt_ids, child_receipt_ids, child_evidence_digests, child_outcomes = (
        _verify_receipt_evidence(payload)
    )
    if expected_repo_root is not None:
        expected_digest = _digest(str(Path(expected_repo_root).resolve()))
        if payload.get("repo_root_digest") != expected_digest:
            raise ValueError("resident_control_loop_receipt_repo_root_invalid")
    verify_control_receipt_authentication(
        payload,
        expected_signer_public_key=expected_signer_public_key,
        expected_key_epoch=expected_key_epoch,
        expected_consensus_receipt_digest=expected_consensus_receipt_digest,
        expected_authority_profile_digest=expected_authority_profile_digest,
        expected_authority_profile_source_receipt_id=(
            expected_authority_profile_source_receipt_id
        ),
        expected_issuer_principal_id=expected_issuer_principal_id,
        require_authenticated=require_authenticated,
        signature_verifier=signature_verifier,
    )
    payload["receipt_ids"] = receipt_ids
    payload["child_execution_receipt_ids"] = child_receipt_ids
    payload["child_execution_evidence_digests"] = child_evidence_digests
    payload["child_execution_outcomes"] = child_outcomes
    payload["rejection_reasons"] = strict_string_tuple(payload.get("rejection_reasons"), 512)
    payload["dispatched_stages"] = stages
    return ResidentControlLoopReceipt(**payload)


def _verify_receipt_evidence(
    payload: Mapping[str, Any],
) -> tuple[
    tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...],
    tuple[dict[str, str], ...],
]:
    validate_current_receipt_fields(payload)
    stages = strict_string_tuple(payload.get("dispatched_stages"), 80)
    receipt_ids = strict_string_tuple(payload.get("receipt_ids"), 256)
    child_receipt_ids = strict_string_tuple(
        payload.get("child_execution_receipt_ids"), 256
    )
    child_digests = strict_string_tuple(
        payload.get("child_execution_evidence_digests"), 80
    )
    child_outcomes = strict_child_outcomes(payload.get("child_execution_outcomes"))
    effects = derive_control_loop_effects(
        stages,
        strict_nonnegative_int(payload.get("claim_progress")),
        payload,
    )
    if any(payload.get(key) != expected for key, expected in effects.items()):
        raise ValueError("resident_control_loop_receipt_effect_claim_invalid")
    if payload.get("source_receipt_ids_digest") != "sha256:" + _digest(
        list(receipt_ids)
    ):
        raise ValueError("resident_control_loop_receipt_source_digest_invalid")
    validate_control_receipt_child_evidence(
        payload, receipt_ids, child_receipt_ids, child_digests, child_outcomes
    )
    return stages, receipt_ids, child_receipt_ids, child_digests, child_outcomes


def append_resident_control_loop_receipt(
    *,
    path: Path | str,
    result: Mapping[str, Any],
    repo_root: Path | str,
    created_at: str,
    cycle_id: str | None = None,
    nonce: str | None = None,
    signing_context: ControlLoopReceiptSigningContext | None = None,
    require_authentication: bool = False,
    runtime_root: Path | str | None = None,
    head_state_path: Path | str | None = None,
) -> ResidentControlLoopReceipt:
    """CAS-append one chain-linked control-loop receipt."""

    if require_authentication and signing_context is None:
        raise ValueError("resident_control_loop_receipt_signer_required")
    target, confined_root, head_target = _control_runtime_paths(
        path=path, repo_root=repo_root, runtime_root=runtime_root,
        head_state_path=head_state_path, require_authentication=require_authentication,
    )
    resolved_cycle_id = _bounded_text(cycle_id, 160) or _new_cycle_id()
    resolved_nonce = _bounded_text(nonce, 192) or _new_nonce()
    operation_identity = str(target) + ".control-chain-operation"
    with runtime_operation_lock(operation_identity):
        chain, head_store, head_state = _load_control_chain_for_append(
            target, head_target, confined_root, repo_root,
            signing_context, require_authentication
        )
        return _build_commit_append_receipt(
            target=target, chain=chain, result=result, repo_root=repo_root,
            created_at=created_at, cycle_id=resolved_cycle_id,
            nonce=resolved_nonce, signing_context=signing_context,
            require_authentication=require_authentication,
            runtime_root=confined_root, head_store=head_store, head_state=head_state,
        )


def _control_runtime_paths(
    *,
    path: Path | str,
    repo_root: Path | str,
    runtime_root: Path | str | None,
    head_state_path: Path | str | None,
    require_authentication: bool,
) -> tuple[Path, Path | None, Path | None]:
    if require_authentication and runtime_root is None:
        raise ValueError("resident_control_loop_runtime_root_required")
    confined_root = (
        validate_runtime_root_path(runtime_root, repo_root=repo_root)
        if runtime_root is not None else None
    )
    target = validate_runtime_artifact_path(
        path, repo_root=repo_root, allowed_root=confined_root
    )
    head_path = head_state_path
    if head_path is None and require_authentication:
        head_path = target.parent / "authority_runtime_state.json"
    head_target = (
        validate_runtime_artifact_path(
            head_path, repo_root=repo_root, allowed_root=confined_root
        )
        if head_path is not None else None
    )
    return target, confined_root, head_target


def _build_commit_append_receipt(
    *, target: Path, chain: Mapping[str, Any], result: Mapping[str, Any],
    repo_root: Path | str, created_at: str, cycle_id: str, nonce: str,
    signing_context: ControlLoopReceiptSigningContext | None,
    require_authentication: bool, runtime_root: Path | None,
    head_store: Any, head_state: Any,
) -> ResidentControlLoopReceipt:
    receipt = build_resident_control_loop_receipt(
        result=result, repo_root=repo_root, created_at=created_at,
        cycle_id=cycle_id, nonce=nonce,
        previous_receipt_id=chain["last_receipt_id"],
        legacy_prefix_digest=chain["legacy_prefix_digest"],
        sequence_number=len(chain["current_receipt_ids"]) + 1,
        signing_context=signing_context,
    )
    _ensure_append_capacity(target, receipt)
    if head_store is not None and head_state is not None:
        commit_next_control_receipt_head(
            store=head_store, state=head_state, chain=chain, receipt=receipt
        )
    _append_receipt_once(
        target, receipt, repo_root, signing_context=signing_context,
        require_authentication=require_authentication, runtime_root=runtime_root,
    )
    return receipt


def _load_control_chain_for_append(
    target: Path,
    head_target: Path | None,
    runtime_root: Path | None,
    repo_root: Path | str,
    signing_context: ControlLoopReceiptSigningContext | None,
    require_authentication: bool,
) -> tuple[dict[str, Any], Any, Any]:
    chain = _validate_existing_receipts(
        _read_existing_chain(target, runtime_root),
        signing_context=signing_context,
        require_authenticated_current=require_authentication,
    )
    if not require_authentication or head_target is None:
        return chain, None, None
    if runtime_root is None:
        raise ValueError("resident_control_loop_runtime_root_required")
    store, state, head = load_control_receipt_head(
        head_target,
        runtime_root=runtime_root,
        repo_root=repo_root,
    )
    chain = reconcile_control_receipt_head(
        target=target, chain=chain, head=head, repo_root=repo_root,
        signing_context=signing_context,
        verify_receipt=verify_resident_control_loop_receipt,
        append_receipt=lambda *args, **kwargs: _append_receipt_once(
            *args, **kwargs, runtime_root=runtime_root
        ),
        validate_chain=_validate_existing_receipts,
        read_chain=lambda path: _read_existing_chain(path, runtime_root),
    )
    return chain, store, state


def _append_receipt_once(
    target: Path,
    receipt: ResidentControlLoopReceipt,
    repo_root: Path | str,
    *,
    signing_context: ControlLoopReceiptSigningContext | None,
    require_authentication: bool,
    runtime_root: Path | None,
) -> None:
    line = json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":")) + "\n"
    if len(line.encode("utf-8")) > 64 * 1024:
        raise ValueError("resident_control_loop_receipt_too_large")

    def validate_before_append(current: str) -> None:
        if len(current.encode("utf-8")) + len(line.encode("utf-8")) > MAX_CONTROL_RECEIPT_CHAIN_BYTES:
            raise ValueError("runtime_artifact_retention_limit_exceeded")
        chain = _validate_existing_receipts(
            current,
            signing_context=signing_context,
            require_authenticated_current=require_authentication,
        )
        if chain["last_receipt_id"] != receipt.previous_receipt_id:
            raise ValueError("resident_control_loop_receipt_chain_revision_conflict")
        if chain["legacy_prefix_digest"] != receipt.legacy_prefix_digest:
            raise ValueError("resident_control_loop_receipt_legacy_prefix_conflict")
        if receipt.cycle_id in chain["cycle_ids"]:
            raise ValueError("resident_control_loop_receipt_cycle_replay")
        if receipt.nonce in chain["nonces"]:
            raise ValueError("resident_control_loop_receipt_nonce_replay")
        if chain["child_receipt_ids"].intersection(
            receipt.child_execution_receipt_ids
        ):
            raise ValueError("resident_control_loop_receipt_child_receipt_replay")
        if chain["child_evidence_digests"].intersection(
            receipt.child_execution_evidence_digests
        ):
            raise ValueError("resident_control_loop_receipt_child_evidence_replay")

    secure_append_runtime_text(
        target,
        line,
        repo_root=repo_root,
        allowed_root=runtime_root,
        validate_existing=validate_before_append,
        max_existing_bytes=MAX_CONTROL_RECEIPT_CHAIN_BYTES,
    )


def _read_existing_chain(path: Path, runtime_root: Path | None) -> str:
    if not path.exists():
        return ""
    if path.stat().st_size > MAX_CONTROL_RECEIPT_CHAIN_BYTES:
        raise ValueError("runtime_artifact_retention_limit_exceeded")
    raw, offset = secure_read_confined_bytes(
        path,
        allowed_root=runtime_root or path.parent,
        max_bytes=MAX_CONTROL_RECEIPT_CHAIN_BYTES,
    )
    if offset != path.stat().st_size:
        raise ValueError("resident_control_loop_receipt_chain_read_incomplete")
    return raw.decode("utf-8")


def _validate_existing_receipts(
    existing: str,
    *,
    signing_context: ControlLoopReceiptSigningContext | None = None,
    require_authenticated_current: bool = False,
    expected_authentication: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    def verify(payload: Mapping[str, Any]) -> ResidentControlLoopReceipt:
        return _verify_existing_current_receipt(
            payload, signing_context=signing_context,
            require_authenticated=require_authenticated_current,
            expected_authentication=expected_authentication,
        )

    return validate_control_receipt_chain_state(
        existing, current_schema=CONTROL_LOOP_RECEIPT_SCHEMA_VERSION,
        legacy_schema=LEGACY_CONTROL_LOOP_RECEIPT_SCHEMA_VERSION,
        receipt_id_builder=_receipt_id, legacy_digest_builder=_legacy_prefix_digest,
        verify_current=verify,
    )


def _ensure_append_capacity(target: Path, receipt: ResidentControlLoopReceipt) -> None:
    line = json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":")) + "\n"
    line_size = len(line.encode("utf-8"))
    existing_size = target.stat().st_size if target.exists() else 0
    if line_size > 64 * 1024:
        raise ValueError("resident_control_loop_receipt_too_large")
    if existing_size + line_size > MAX_CONTROL_RECEIPT_CHAIN_BYTES:
        raise ValueError("runtime_artifact_retention_limit_exceeded")


def _verify_existing_current_receipt(
    payload: Mapping[str, Any],
    *,
    signing_context: ControlLoopReceiptSigningContext | None,
    require_authenticated: bool,
    expected_authentication: Mapping[str, Any] | None,
) -> ResidentControlLoopReceipt:
    context = signing_context
    expected = expected_authentication or {}
    return verify_resident_control_loop_receipt(
        payload,
        expected_signer_public_key=(
            context.signer_public_key if context else expected.get("signer_public_key")
        ),
        expected_key_epoch=context.key_epoch if context else expected.get("key_epoch"),
        expected_consensus_receipt_digest=(
            context.consensus_receipt_digest
            if context
            else expected.get("consensus_receipt_digest")
        ),
        expected_authority_profile_digest=(
            context.authority_profile_digest
            if context
            else expected.get("authority_profile_digest")
        ),
        expected_authority_profile_source_receipt_id=(
            context.authority_profile_source_receipt_id
            if context
            else expected.get("authority_profile_source_receipt_id")
        ),
        expected_issuer_principal_id=(
            context.issuer_principal_id
            if context
            else expected.get("issuer_principal_id")
        ),
        require_authenticated=require_authenticated,
        signature_verifier=(
            context.signature_verifier
            if context
            else expected.get("signature_verifier")
        ),
    )


def _receipt_id(payload: Mapping[str, Any]) -> str:
    excluded = {"receipt_id"}
    if payload.get("schema_version") == CONTROL_LOOP_RECEIPT_SCHEMA_VERSION:
        excluded.update(
            {
                "signature",
                "signer_audit_mac",
                "signer_audit_attestation_signature",
            }
        )
    canonical = {key: value for key, value in payload.items() if key not in excluded}
    digest = _digest(canonical)
    if payload.get("schema_version") == LEGACY_CONTROL_LOOP_RECEIPT_SCHEMA_VERSION:
        return "reddog_resident_control_loop_" + digest[:16]
    return "reddog_resident_control_loop_v2_" + digest


def _legacy_prefix_digest(payloads: Any) -> str:
    return "sha256:" + _digest(list(payloads))


def _new_cycle_id() -> str:
    return "reddog_control_cycle_" + secrets.token_hex(16)


def _new_nonce() -> str:
    return "reddog-control-loop:" + secrets.token_hex(32)


def _string_tuple(value: Any, *, max_chars: int) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(_bounded_text(item, max_chars) for item in value[:128] if str(item or "").strip())


def _bounded_text(value: Any, max_chars: int) -> str:
    return str(value or "").strip()[:max_chars]


def _int(value: Any) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "CONTROL_LOOP_AUTHENTICATED",
    "CONTROL_LOOP_DISPLAY_ONLY",
    "CONTROL_LOOP_RECEIPT_SCHEMA_VERSION",
    "ControlLoopReceiptSigningContext",
    "LEGACY_CONTROL_LOOP_RECEIPT_SCHEMA_VERSION",
    "ResidentControlLoopReceipt",
    "append_resident_control_loop_receipt",
    "build_resident_control_loop_receipt",
    "verify_resident_control_loop_receipt",
]
