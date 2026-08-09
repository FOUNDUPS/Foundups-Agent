"""Authenticated restart envelope for RedDog signed AgentDB worker tasks."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_runtime_dependency_bundle import (
    load_reddog_main_resident_queue_runtime_dependency_bundle,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
    resident_queue_runtime_file_path,
    resident_queue_runtime_root_path,
)
from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
    WORKER_DISPATCH_INTENT_FIELDS,
    WORKER_DISPATCH_RECEIPT_FIELDS,
    plan_reddog_signed_authority_worker_dispatch_dry_run,
)
from modules.communication.moltbot_bridge.src.reddog_worker_dispatch_authority_binding import (
    WorkerDispatchAuthorityVerificationContext,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_WORKTREE_CREATE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_verification_invoke import (
    invoke_reddog_wre_queue_authority_verification,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_consumer_dryrun import (
    WREQueueConsumerDryRunReceipt,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    WORK_ORDER_MATERIALIZATION_BINDING_FIELDS,
    WORK_ORDER_MATERIALIZATION_BINDING_SCHEMA,
    build_work_order_materialization_binding,
    canonical_full_work_order_digest,
)


SIGNED_WORKER_AGENTDB_ENVELOPE_SCHEMA = "reddog_signed_worker_agentdb_envelope.v1"
SIGNED_WORKER_DISPATCH_TASK_SOURCE = "reddog_signed_worker_dispatch_runtime"
SIGNED_WORKER_DISPATCH_TASK_SKILL = "reddog_signed_worker_dispatch"
WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION = "reddog_worker_dispatch_runtime.v1"

_ENVELOPE_FIELDS = frozenset(
    {
        "schema_version",
        "queue_authority_runtime_result",
        "wsp15_allocation_receipt",
        "signed_authority_worker_dispatch_receipt",
        "worker_dispatch_intent",
        "queue_consumer_receipt",
        "work_order_materialization_binding",
        "agentdb_task_binding",
    }
)
_RUNTIME_FIELDS = frozenset({"decision", "authority_result"})
_AUTHORITY_FIELDS = frozenset(
    {"accepted", "receipt", "identity", "work_authority"}
)
_QUEUE_CONSUMER_RECEIPT_FIELDS = frozenset(
    WREQueueConsumerDryRunReceipt.__dataclass_fields__
)
_TASK_BINDING_FIELDS = frozenset(
    {
        "source",
        "task_id",
        "queue_item_id",
        "source_dispatch_receipt_id",
        "description",
        "required_skills",
        "estimated_complexity",
        "priority_score",
        "origin_continuity_id",
        "operational_snapshot_id",
        "selected_slice",
    }
)
_DOWNSTREAM_STAGES = (
    "work_order_invocation",
    "executor_plan",
    "execution_valve",
    "worktree_create",
    "assurance_capacity_admission",
    "bounded_worker_pilot",
    "slice_verifier",
)
class SignedWorkerAgentDbEnvelopeError(ValueError):
    """Fail-closed AgentDB envelope rejection."""


@dataclass(frozen=True)
class VerifiedSignedWorkerAgentDbEnvelope:
    """Evidence returned after fresh authority and task-plan verification."""

    task_id: str
    canonical_context: Mapping[str, Any]
    dispatch_receipt: Mapping[str, Any]
    dispatch_intent: Mapping[str, Any]
    authority_verification_result: Mapping[str, Any]


@dataclass(frozen=True)
class WorkerDispatchAuthorityVerificationConfig:
    """Process-local inputs needed to rehydrate claim-time authority."""

    repo_root: str
    runtime_allowed_root: str
    authority_state_path: str
    permission_snapshots_path: str
    principal_authority_records_path: str
    signature_verifier_backend: str


def capture_worker_dispatch_authority_verification_config(
    *,
    repo_root: Path | str,
    runtime_allowed_root: Path | str,
    authority_state_path: Path | str | None,
    permission_snapshots_path: Path | str | None,
    principal_authority_records_path: Path | str | None,
    signature_verifier_backend: str | None,
) -> WorkerDispatchAuthorityVerificationConfig | None:
    """Capture startup-resolved public verifier inputs for the claim stage."""

    if not authority_state_path:
        return None
    return WorkerDispatchAuthorityVerificationConfig(
        repo_root=str(Path(repo_root).resolve()),
        runtime_allowed_root=str(runtime_allowed_root or ""),
        authority_state_path=str(authority_state_path),
        permission_snapshots_path=str(permission_snapshots_path or ""),
        principal_authority_records_path=str(
            principal_authority_records_path or ""
        ),
        signature_verifier_backend=str(signature_verifier_backend or ""),
    )


def canonical_reddog_signed_worker_task_id(
    *, source_dispatch_receipt_id: str, queue_item_id: str, intent_id: str
) -> str:
    seed = {
        "source_dispatch_receipt_id": source_dispatch_receipt_id,
        "queue_item_id": queue_item_id,
        "intent_id": intent_id,
    }
    return "reddog-worker-dispatch-" + _digest(seed)[7:23]


def build_reddog_signed_worker_agentdb_envelope(
    *,
    task_id: str,
    queue_authority_runtime_result: Mapping[str, Any],
    wsp15_allocation_receipt: Mapping[str, Any],
    dispatch_receipt: Mapping[str, Any],
    dispatch_intent: Mapping[str, Any],
    queue_consumer_receipt: Mapping[str, Any],
    work_order_materialization_binding: Mapping[str, Any],
    task_binding: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Build the restart envelope without inventing a second trust primitive."""

    binding = dict(task_binding)
    binding["task_id"] = task_id
    return {
        "schema_version": SIGNED_WORKER_AGENTDB_ENVELOPE_SCHEMA,
        "queue_authority_runtime_result": _canonical_runtime(
            queue_authority_runtime_result
        ),
        "wsp15_allocation_receipt": dict(wsp15_allocation_receipt),
        "signed_authority_worker_dispatch_receipt": _canonical_receipt(
            dispatch_receipt
        ),
        "worker_dispatch_intent": _canonical_intent(dispatch_intent),
        "queue_consumer_receipt": _exact_mapping(
            queue_consumer_receipt,
            _QUEUE_CONSUMER_RECEIPT_FIELDS,
            "queue_consumer_receipt",
        ),
        "work_order_materialization_binding": _exact_mapping(
            work_order_materialization_binding,
            WORK_ORDER_MATERIALIZATION_BINDING_FIELDS,
            "work_order_materialization_binding",
        ),
        "agentdb_task_binding": binding,
    }


def verify_reddog_signed_worker_agentdb_envelope(
    *,
    envelope: Mapping[str, Any],
    task_id: str,
    authority_context: WorkerDispatchAuthorityVerificationContext,
) -> VerifiedSignedWorkerAgentDbEnvelope:
    """Reverify persisted signed authority and regenerate the exact task plan."""

    (
        payload,
        runtime,
        allocation,
        recorded_receipt,
        recorded_intent,
        queue_receipt,
        work_order_binding,
        binding,
    ) = _envelope_components(envelope)
    verification = _fresh_verification(runtime, authority_context)
    planned_receipt = _regenerated_receipt(runtime, verification, allocation)
    if not _constant_mapping_equal(recorded_receipt, planned_receipt):
        raise SignedWorkerAgentDbEnvelopeError("dispatch_receipt_mismatch")
    planned_intent = _selected_intent(planned_receipt, recorded_intent)
    _verify_work_order_binding(
        runtime=runtime,
        queue_receipt=queue_receipt,
        work_order_binding=work_order_binding,
    )
    _verify_task_binding(
        task_id,
        binding,
        planned_receipt,
        planned_intent,
        queue_receipt,
    )
    context = _canonical_context(
        envelope=payload,
        binding=binding,
        runtime=runtime,
        allocation=allocation,
        receipt=planned_receipt,
        intent=planned_intent,
        queue_receipt=queue_receipt,
    )
    return VerifiedSignedWorkerAgentDbEnvelope(
        task_id=task_id,
        canonical_context=context,
        dispatch_receipt=planned_receipt,
        dispatch_intent=planned_intent,
        authority_verification_result=verification,
    )


def _envelope_components(
    envelope: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    payload = _exact_mapping(envelope, _ENVELOPE_FIELDS, "envelope")
    if payload.get("schema_version") != SIGNED_WORKER_AGENTDB_ENVELOPE_SCHEMA:
        raise SignedWorkerAgentDbEnvelopeError("envelope_schema_mismatch")
    return (
        payload,
        _exact_runtime(payload.get("queue_authority_runtime_result")),
        _mapping(payload.get("wsp15_allocation_receipt")),
        _exact_mapping(
            payload.get("signed_authority_worker_dispatch_receipt"),
            WORKER_DISPATCH_RECEIPT_FIELDS,
            "dispatch_receipt",
        ),
        _exact_mapping(
            payload.get("worker_dispatch_intent"),
            WORKER_DISPATCH_INTENT_FIELDS,
            "dispatch_intent",
        ),
        _exact_mapping(
            payload.get("queue_consumer_receipt"),
            _QUEUE_CONSUMER_RECEIPT_FIELDS,
            "queue_consumer_receipt",
        ),
        _exact_mapping(
            payload.get("work_order_materialization_binding"),
            WORK_ORDER_MATERIALIZATION_BINDING_FIELDS,
            "work_order_materialization_binding",
        ),
        _exact_mapping(
            payload.get("agentdb_task_binding"),
            _TASK_BINDING_FIELDS,
            "task_binding",
        ),
    )


def build_worker_dispatch_authority_context(
    *,
    config: WorkerDispatchAuthorityVerificationConfig,
    trusted_now_epoch: Callable[[], int] | None = None,
) -> WorkerDispatchAuthorityVerificationContext:
    """Rehydrate verifier dependencies from explicit startup-resolved inputs."""

    clock = trusted_now_epoch or (lambda: int(time.time()))
    bundle = load_reddog_main_resident_queue_runtime_dependency_bundle(
        repo_root=config.repo_root,
        runtime_allowed_root=config.runtime_allowed_root or None,
        authority_state_path=config.authority_state_path or None,
        permission_snapshots_path=config.permission_snapshots_path or None,
        principal_authority_records_path=config.principal_authority_records_path
        or None,
        signature_verifier_backend=config.signature_verifier_backend or None,
        now_epoch=int(clock()),
    )
    if bundle.accepted is not True or not bundle.requested:
        raise SignedWorkerAgentDbEnvelopeError(
            "authority_verification_dependencies_unavailable"
        )
    return WorkerDispatchAuthorityVerificationContext(
        signature_verifier=bundle.signature_verifier,
        principal_key_resolver=bundle.principal_key_resolver,
        nonce_store=bundle.nonce_store,
        snapshot_resolver=bundle.snapshot_resolver,
        revocation_oracle=bundle.revocation_oracle,
        trusted_now_epoch=clock,
        required_valve_state=VALVE_OPEN_WORKTREE_CREATE,
    )


def build_worker_dispatch_authority_context_from_env(
    *, repo_root: Path | str, env: Mapping[str, str]
) -> WorkerDispatchAuthorityVerificationContext:
    """Compatibility adapter for non-startup callers without explicit context."""

    root = Path(repo_root).resolve()
    config = WorkerDispatchAuthorityVerificationConfig(
        repo_root=str(root),
        runtime_allowed_root=resident_queue_runtime_root_path(env, root),
        authority_state_path=resident_queue_runtime_file_path(
            env, root, "REDDOG_AUTHORITY_RUNTIME_STATE_PATH"
        ),
        permission_snapshots_path=resident_queue_runtime_file_path(
            env, root, "REDDOG_PERMISSION_SNAPSHOTS_PATH"
        ),
        principal_authority_records_path=resident_queue_runtime_file_path(
            env, root, "REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH"
        ),
        signature_verifier_backend=str(
            env.get("REDDOG_SIGNATURE_VERIFIER_BACKEND") or ""
        ),
    )
    return build_worker_dispatch_authority_context(config=config)


def _fresh_verification(
    runtime: Mapping[str, Any],
    context: WorkerDispatchAuthorityVerificationContext,
) -> Mapping[str, Any]:
    result = invoke_reddog_wre_queue_authority_verification(
        explicit_queue_authority_verification_requested=True,
        queue_authority_runtime_result=runtime,
        signature_verifier=context.signature_verifier,
        principal_key_resolver=context.principal_key_resolver,
        nonce_store=context.nonce_store,
        snapshot_resolver=context.snapshot_resolver,
        revocation_oracle=context.revocation_oracle,
        now=int(context.trusted_now_epoch()),
        required_valve_state=context.required_valve_state,
        forbidden_operations=context.forbidden_operations,
        revoked_key_epochs=context.revoked_key_epochs,
        leeway_s=context.leeway_s,
    ).to_dict()
    if result.get("decision") != "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT":
        reasons = ",".join(
            str(value)
            for value in _sequence(result.get("rejection_reasons"))
        )
        raise SignedWorkerAgentDbEnvelopeError(
            "authority_reverification_rejected:" + reasons[:120]
        )
    return result


def _regenerated_receipt(
    runtime: Mapping[str, Any],
    verification: Mapping[str, Any],
    allocation: Mapping[str, Any],
) -> Mapping[str, Any]:
    result = plan_reddog_signed_authority_worker_dispatch_dry_run(
        explicit_signed_authority_worker_dispatch_dryrun_requested=True,
        queue_authority_verification_result=verification,
        queue_authority_runtime_result=runtime,
        wsp15_allocation_receipt=allocation,
    ).to_dict()
    receipt = _mapping(result.get("receipt"))
    if result.get("accepted") is not True or not receipt:
        raise SignedWorkerAgentDbEnvelopeError("dispatch_plan_regeneration_rejected")
    return _exact_mapping(receipt, WORKER_DISPATCH_RECEIPT_FIELDS, "dispatch_receipt")


def _selected_intent(
    receipt: Mapping[str, Any], recorded_intent: Mapping[str, Any]
) -> Mapping[str, Any]:
    intent_id = str(recorded_intent.get("intent_id") or "")
    matches = [
        _mapping(value)
        for value in _sequence(receipt.get("dispatch_intents"))
        if str(_mapping(value).get("intent_id") or "") == intent_id
    ]
    if len(matches) != 1 or not _constant_mapping_equal(
        matches[0], recorded_intent
    ):
        raise SignedWorkerAgentDbEnvelopeError("dispatch_intent_mismatch")
    return _exact_mapping(matches[0], WORKER_DISPATCH_INTENT_FIELDS, "dispatch_intent")


def _verify_task_binding(
    task_id: str,
    binding: Mapping[str, Any],
    receipt: Mapping[str, Any],
    intent: Mapping[str, Any],
    queue_receipt: Mapping[str, Any],
) -> None:
    expected = canonical_reddog_signed_worker_task_id(
        source_dispatch_receipt_id=str(receipt.get("receipt_id") or ""),
        queue_item_id=str(queue_receipt.get("queue_item_id") or ""),
        intent_id=str(intent.get("intent_id") or ""),
    )
    if not hmac.compare_digest(task_id, expected):
        raise SignedWorkerAgentDbEnvelopeError("task_id_mismatch")
    required = (
        binding.get("source") == SIGNED_WORKER_DISPATCH_TASK_SOURCE
        and binding.get("task_id") == task_id
        and binding.get("source_dispatch_receipt_id") == receipt.get("receipt_id")
        and binding.get("origin_continuity_id") == receipt.get("work_order_id")
        and binding.get("queue_item_id") == queue_receipt.get("queue_item_id")
        and binding.get("selected_slice") == queue_receipt.get("slice_id")
        and binding.get("operational_snapshot_id")
        == queue_receipt.get("operational_snapshot_id")
    )
    if not required:
        raise SignedWorkerAgentDbEnvelopeError("task_binding_mismatch")


def _verify_work_order_binding(
    *,
    runtime: Mapping[str, Any],
    queue_receipt: Mapping[str, Any],
    work_order_binding: Mapping[str, Any],
) -> None:
    authority = _mapping(runtime.get("authority_result"))
    work_authority = _mapping(authority.get("work_authority"))
    expected = build_work_order_materialization_binding(
        work_order_id=str(work_authority.get("work_order_id") or ""),
        base_ref=str(work_authority.get("base_ref") or ""),
        queue_consumer_receipt=queue_receipt,
    )
    if (
        work_order_binding.get("schema_version")
        != WORK_ORDER_MATERIALIZATION_BINDING_SCHEMA
        or not _constant_mapping_equal(work_order_binding, expected)
        or not hmac.compare_digest(
            canonical_full_work_order_digest(queue_receipt),
            str(work_authority.get("queue_consumer_receipt_digest") or ""),
        )
        or str(queue_receipt.get("queue_item_id") or "") == ""
        or str(queue_receipt.get("slice_id") or "") == ""
        or str(queue_receipt.get("freshness_receipt_id") or "") == ""
    ):
        raise SignedWorkerAgentDbEnvelopeError(
            "work_order_materialization_binding_mismatch"
        )


def _canonical_context(
    *,
    envelope: Mapping[str, Any],
    binding: Mapping[str, Any],
    runtime: Mapping[str, Any],
    allocation: Mapping[str, Any],
    receipt: Mapping[str, Any],
    intent: Mapping[str, Any],
    queue_receipt: Mapping[str, Any],
) -> Mapping[str, Any]:
    authority = _mapping(runtime.get("authority_result"))
    work_authority = _mapping(authority.get("work_authority"))
    task_id = str(binding["task_id"])
    return {
        "source": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        "schema_version": WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION,
        "slice_name": "REDDOG_OPENCLAW_HERMES_0102_WORKER_DISPATCH_RUNTIME_PHASE1",
        "queue_item_id": str(queue_receipt["queue_item_id"]),
        "work_order_id": str(receipt["work_order_id"]),
        "operational_snapshot_id": str(queue_receipt["operational_snapshot_id"]),
        "wsp15_allocation_receipt_id": str(receipt["wsp15_allocation_receipt_id"]),
        "progressive_policy_stage_receipt_id": str(
            receipt["progressive_policy_stage_receipt_id"]
        ),
        "progressive_policy_stage_digest": str(
            receipt["progressive_policy_stage_digest"]
        ),
        "selected_slice": str(queue_receipt["slice_id"]),
        "worker_runtime": str(intent["worker_runtime"]),
        "worker_role": str(intent["role"]),
        "worker_principal_id": f"agentdb-task:{task_id}",
        "capability": str(intent["capability"]),
        "signed_authority_worker_dispatch_receipt": dict(receipt),
        "worker_dispatch_intent": dict(intent),
        "authorized_principal_id": str(work_authority["principal_id"]),
        "authorized_reddog_id": str(work_authority["reddog_id"]),
        "wsp15_allocation_receipt": dict(allocation),
        "model_runtime_binding_receipt_id": str(receipt["model_runtime_binding_receipt_id"]),
        "model_runtime_binding_digest": str(receipt["model_runtime_binding_digest"]),
        **_memex_context(receipt),
        "architect_fix_publication_receipt_id": str(
            receipt["architect_fix_publication_receipt_id"]
        ),
        "architect_fix_publication_binding_digest": str(
            receipt["architect_fix_publication_binding_digest"]
        ),
        "verified_work_authority_digest": str(
            receipt["verified_work_authority_digest"]
        ),
        "authority_verification_receipt_id": str(
            receipt["authority_verification_receipt_id"]
        ),
        "authority_verification_receipt_digest": str(
            receipt["authority_verification_receipt_digest"]
        ),
        "signed_worker_agentdb_envelope": dict(envelope),
        "execution_allowed_by_dispatch_runtime": False,
        "requires_downstream_stages": list(_DOWNSTREAM_STAGES),
        "report_contract": {
            "worker_process_started": False,
            "repo_mutation_performed": False,
            "hermes_execution_performed": False,
            "requires_signed_authority": True,
        },
    }


def _memex_context(receipt: Mapping[str, Any]) -> Mapping[str, str]:
    return {
        "memex_supply_receipt_id": str(receipt["memex_supply_receipt_id"]),
        "memex_supply_digest": str(receipt["memex_supply_digest"]),
    }


def _canonical_runtime(value: Any) -> Mapping[str, Any]:
    runtime = _mapping(value)
    authority = _mapping(runtime.get("authority_result"))
    return {
        "decision": runtime.get("decision"),
        "authority_result": {
            "accepted": authority.get("accepted"),
            "receipt": dict(_mapping(authority.get("receipt"))),
            "identity": dict(_mapping(authority.get("identity"))),
            "work_authority": dict(_mapping(authority.get("work_authority"))),
        },
    }


def _exact_runtime(value: Any) -> Mapping[str, Any]:
    runtime = _exact_mapping(value, _RUNTIME_FIELDS, "authority_runtime")
    _exact_mapping(runtime.get("authority_result"), _AUTHORITY_FIELDS, "authority_result")
    canonical = _canonical_runtime(runtime)
    if not _constant_mapping_equal(runtime, canonical):
        raise SignedWorkerAgentDbEnvelopeError("authority_runtime_mismatch")
    return canonical


def _canonical_receipt(value: Any) -> Mapping[str, Any]:
    receipt = _exact_mapping(value, WORKER_DISPATCH_RECEIPT_FIELDS, "dispatch_receipt")
    payload = {
        field: receipt[field]
        for field in WORKER_DISPATCH_RECEIPT_FIELDS
        if field != "dispatch_intents"
    }
    payload["dispatch_intents"] = [
        _canonical_intent(item) for item in _sequence(receipt["dispatch_intents"])
    ]
    return payload


def _canonical_intent(value: Any) -> Mapping[str, Any]:
    intent = _exact_mapping(value, WORKER_DISPATCH_INTENT_FIELDS, "dispatch_intent")
    return {field: intent[field] for field in WORKER_DISPATCH_INTENT_FIELDS}


def _exact_mapping(value: Any, fields: frozenset[str], label: str) -> Mapping[str, Any]:
    payload = _mapping(value)
    if set(payload) != fields:
        raise SignedWorkerAgentDbEnvelopeError(f"{label}_schema_mismatch")
    return payload


def _constant_mapping_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return hmac.compare_digest(_canonical_json(left), _canonical_json(right))


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, (list, tuple)) else ()


__all__ = [
    "SIGNED_WORKER_AGENTDB_ENVELOPE_SCHEMA",
    "SIGNED_WORKER_DISPATCH_TASK_SKILL",
    "SIGNED_WORKER_DISPATCH_TASK_SOURCE",
    "WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION",
    "SignedWorkerAgentDbEnvelopeError",
    "VerifiedSignedWorkerAgentDbEnvelope",
    "WorkerDispatchAuthorityVerificationConfig",
    "build_reddog_signed_worker_agentdb_envelope",
    "build_worker_dispatch_authority_context",
    "build_worker_dispatch_authority_context_from_env",
    "capture_worker_dispatch_authority_verification_config",
    "canonical_reddog_signed_worker_task_id",
    "verify_reddog_signed_worker_agentdb_envelope",
]
