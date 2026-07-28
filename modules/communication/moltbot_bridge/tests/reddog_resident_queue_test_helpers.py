"""Shared resident queue test fixtures."""

from __future__ import annotations

import hashlib
import hmac
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_publication_validation import (
    architect_fix_publication_state_projection,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_records import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_worker_dispatch_authority_binding import (
    WorkerDispatchAuthorityVerificationContext,
    recorded_authority_verification_binding,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    InMemoryNonceStore,
    PermissionSnapshot,
    canonical_signing_input,
)
from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
    derive_worker_dispatch_roles,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    build_work_order_materialization_binding,
    canonical_full_work_order_digest,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_consumer_dryrun import (
    plan_reddog_wre_queue_consumer_dry_run,
)


WORKER_DISPATCH_DRYRUN_STAGE_RESULT = {
    "decision": "SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT",
}

WORKER_DISPATCH_RUNTIME_STAGE_RESULT = {
    "decision": "SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT",
}

ASSURANCE_RESERVATION = {
    "reservation_id": "assurance-reservation-" + "1" * 20,
    "reservation_digest": "sha256:" + "0" * 64,
    "status": "reserved",
    "work_order_id": "wo-resident-queue-1",
    "author_task_id": "reddog-worker-dispatch-" + "1" * 16,
    "author_principal_id": "worker:author",
    "verifier_task_id": "reddog-worker-dispatch-" + "2" * 16,
    "verifier_principal_id": "worker:verifier",
}

ASSURANCE_CAPACITY_ADMISSION_STAGE_RESULT = {
    "decision": "ASSURANCE_CAPACITY_ADMISSION_ACCEPT",
    "reservation": ASSURANCE_RESERVATION,
}

_TEST_NOW = 1000
_TEST_REPO = "FOUNDUPS/Foundups-Agent"
_TEST_FOUNDUP = "paccess_001"
_TEST_PRINCIPAL_SECRET = b"worker-dispatch-principal"
_TEST_REDDOG_SECRET = b"worker-dispatch-reddog"
_TEST_WORK_ORDER_DIGEST = "sha256:" + "1" * 64
_TEST_PERMISSION_SNAPSHOT_DIGEST = "sha256:" + "2" * 64
_TEST_FRESHNESS_RECEIPT_ID = "fresh-worker-dispatch-1"
_TEST_CLAIM_ID = "claim-worker-dispatch-1"
_TEST_WORKER_ID = "reddog-main-bootstrap"
_TEST_SLICE_ID = "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1"
_TEST_DETERMINATION_ID = "sha256:determination"
_TEST_MODEL_SELECTION_ID = "sha256:model-selection"
_TEST_MEMEX_SUPPLY_ID = "sha256:memex-supply"


class _WorkerDispatchSignatureVerifier:
    def verify(self, public_key: str, signing_input: str, signature: str) -> bool:
        secret = {
            "pub:worker-dispatch-principal": _TEST_PRINCIPAL_SECRET,
            "pub:worker-dispatch-reddog": _TEST_REDDOG_SECRET,
        }.get(public_key)
        if secret is None:
            return False
        expected = hmac.new(
            secret,
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


class _WorkerDispatchPrincipalResolver:
    def resolve(self, principal_id: str, principal_provider: str):
        if principal_id == "github:mjtrout" and principal_provider == "github":
            return "pub:worker-dispatch-principal"
        return None


class _WorkerDispatchSnapshotResolver:
    def resolve(self, digest: str):
        if digest != _TEST_PERMISSION_SNAPSHOT_DIGEST:
            return None
        return PermissionSnapshot(
            evidence_digest=digest,
            expires_at=_TEST_NOW + 600,
            can_write=True,
            repo_full_name=_TEST_REPO,
        )


class _WorkerDispatchNoRevocation:
    def is_revoked(self, **_kwargs: Any) -> bool:
        return False


class FakeAssuranceReservationStore:
    def __init__(self) -> None:
        self.reservation = dict(ASSURANCE_RESERVATION)
        self.reservations = {
            str(self.reservation["reservation_id"]): dict(self.reservation)
        }

    def reserve_independent_assurance(self, request):
        self.reservation = {**dict(request), "status": "reserved"}
        self.reservations[str(self.reservation["reservation_id"])] = dict(
            self.reservation
        )
        return {
            "accepted": True,
            "status": "ASSURANCE_CAPACITY_RESERVED",
            "reservation": dict(self.reservation),
        }

    def get_independent_assurance_reservation(self, reservation_id: str):
        value = self.reservations.get(reservation_id)
        return dict(value) if value is not None else None

    def complete_independent_assurance(self, reservation_id: str, **kwargs):
        if (
            reservation_id not in self.reservations
            or not kwargs.get("terminal_receipt_id")
        ):
            return {"accepted": False, "status": "rejected"}
        return {"accepted": True, "status": "completed"}


def queue_wsp15_allocation_receipt(*, prompt_text: str = "RedDog resident queue worktree authority") -> dict[str, Any]:
    return allocate_reddog_wsp15_receipt(
        requested_operation="create_foundup",
        prompt_text=prompt_text,
        changed_paths=("modules/communication/moltbot_bridge/src/reddog_resident_queue_orchestration_plan.py",),
        allowed_read_targets=("modules/communication/moltbot_bridge/src/reddog_resident_queue_orchestration_plan.py",),
    ).to_dict()


def with_queue_wsp15_allocation(queue_item: dict[str, Any], *, prompt_text: str = "RedDog resident queue worktree authority") -> dict[str, Any]:
    allocation = queue_wsp15_allocation_receipt(prompt_text=prompt_text)
    item = dict(queue_item)
    refs = [str(ref) for ref in item.get("evidence_refs") or ()]
    refs.extend(
        [
            f"wsp15_allocation:{allocation['receipt_id']}",
        ]
    )
    item["evidence_refs"] = list(dict.fromkeys(refs))
    item["wsp15_allocation_receipt"] = allocation
    return item


def governed_worker_dispatch_snapshot(
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Add the minimum real queue lineage required by the signed worker path."""

    governed = deepcopy(snapshot)
    queue_items = governed.get("wre_queue_items")
    if not isinstance(queue_items, list) or not queue_items:
        return governed
    queue = queue_items[0]
    queue.setdefault("slice_id", _TEST_SLICE_ID)
    queue.setdefault("claim_id", _TEST_CLAIM_ID)
    queue.setdefault("worker_id", _TEST_WORKER_ID)
    queue.setdefault("no_execution_performed", True)
    queue.setdefault("source_determination_receipt_id", _TEST_DETERMINATION_ID)
    queue.setdefault("model_selection_receipt_id", _TEST_MODEL_SELECTION_ID)
    queue.setdefault("model_selection_digest", "sha256:model-selection")
    queue.setdefault("memex_supply_receipt_id", _TEST_MEMEX_SUPPLY_ID)
    queue.setdefault("memex_supply_digest", "sha256:memex-supply")

    allocation = queue.get("wsp15_allocation_receipt") or {}
    allocation_id = str(allocation.get("receipt_id") or "")
    runtime_id = str(queue.get("model_runtime_binding_receipt_id") or "")
    refs = [
        str(ref)
        for ref in queue.get("evidence_refs") or ()
    ]
    refs.extend(
        [
            f"claim:{queue['claim_id']}",
            f"freshness:{_TEST_FRESHNESS_RECEIPT_ID}",
            f"wsp15_allocation:{allocation_id}",
            f"architect_determination:{queue['source_determination_receipt_id']}",
            f"model_selection:{queue['model_selection_receipt_id']}",
            f"memex_supply:{queue['memex_supply_receipt_id']}",
        ]
    )
    if runtime_id:
        refs.append(f"model_runtime_binding:{runtime_id}")
    queue["evidence_refs"] = list(dict.fromkeys(refs))

    governed.setdefault(
        "freshness_receipts",
        [{"receipt_id": _TEST_FRESHNESS_RECEIPT_ID, "fresh": True}],
    )
    governed.setdefault(
        "worker_claims",
        [
            {
                "claim_id": str(queue["claim_id"]),
                "slice_id": str(queue["slice_id"]),
                "worker_id": str(queue["worker_id"]),
                "status": "ACTIVE",
                "expires_at": "2030-01-01T00:00:00+00:00",
                "freshness_receipt_id": _TEST_FRESHNESS_RECEIPT_ID,
                "lane_id": "reddog_operational",
                "reconciliation_report_id": "sha256:reconciliation",
                "source_determination_receipt_id": str(
                    queue["source_determination_receipt_id"]
                ),
                "model_selection_receipt_id": str(
                    queue["model_selection_receipt_id"]
                ),
                "model_runtime_binding_receipt_id": runtime_id,
                "memex_supply_receipt_id": str(queue["memex_supply_receipt_id"]),
            }
        ],
    )
    return governed


def worker_dispatch_work_order_digest(
    snapshot: dict[str, Any],
    *,
    work_order_id: str = "wo-1",
    base_ref: str = "main",
    queue_item_id: str = "queue-1",
) -> str:
    """Derive the signed digest from the authoritative queue receipt."""

    result = plan_reddog_wre_queue_consumer_dry_run(
        snapshot,
        now_iso="2026-07-16T00:00:00+00:00",
        requested_queue_item_id=queue_item_id,
        require_governed_lineage=True,
    )
    if not result.accepted or result.receipt is None:
        raise AssertionError(result.rejection_reasons)
    binding = build_work_order_materialization_binding(
        work_order_id=work_order_id,
        base_ref=base_ref,
        queue_consumer_receipt=result.receipt.to_dict(),
    )
    return canonical_full_work_order_digest(binding)


def worker_dispatch_queue_receipt_digest(
    snapshot: dict[str, Any],
    *,
    queue_item_id: str = "queue-1",
) -> str:
    result = plan_reddog_wre_queue_consumer_dry_run(
        snapshot,
        now_iso="2026-07-16T00:00:00+00:00",
        requested_queue_item_id=queue_item_id,
        require_governed_lineage=True,
    )
    if not result.accepted or result.receipt is None:
        raise AssertionError(result.rejection_reasons)
    return canonical_full_work_order_digest(result.receipt.to_dict())


def worker_dispatch_authority_stages(
    allocation: dict[str, Any],
    *,
    work_state_snapshot: dict[str, Any] | None = None,
    queue_item_id: str = "queue-1",
    **work_authority_overrides: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build mutually bound authority/verification stages for runtime tests."""

    identity = {
        "principal_id": "github:mjtrout",
        "principal_provider": "github",
        "principal_public_key": "pub:worker-dispatch-principal",
        "reddog_id": "reddog:worker-dispatch",
        "reddog_public_key": "pub:worker-dispatch-reddog",
        "repo_scope": [_TEST_REPO],
        "foundup_scope": [_TEST_FOUNDUP],
        "issued_at": _TEST_NOW - 5,
        "expires_at": _TEST_NOW + 3600,
    }
    identity["signature"] = _sign(
        _TEST_PRINCIPAL_SECRET,
        canonical_signing_input(identity, "reddog-identity.v1"),
    )
    work_order_id = str(work_authority_overrides.get("work_order_id") or "wo-1")
    base_ref = str(work_authority_overrides.get("base_ref") or "main")
    work_order_digest = _TEST_WORK_ORDER_DIGEST
    queue_receipt_digest = "sha256:" + "4" * 64
    if work_state_snapshot is not None:
        work_order_digest = worker_dispatch_work_order_digest(
            work_state_snapshot,
            work_order_id=work_order_id,
            base_ref=base_ref,
            queue_item_id=queue_item_id,
        )
        queue_receipt_digest = worker_dispatch_queue_receipt_digest(
            work_state_snapshot,
            queue_item_id=queue_item_id,
        )
    work_authority = {
        "work_order_id": "wo-1",
        "work_order_digest": work_order_digest,
        "base_ref": "main",
        "principal_id": "github:mjtrout",
        "reddog_id": "reddog:worker-dispatch",
        "repo_full_name": _TEST_REPO,
        "foundup_id": _TEST_FOUNDUP,
        "allowed_paths": [f"modules/foundups/{_TEST_FOUNDUP}/**"],
        "denied_paths": [],
        "requested_operation": "create_foundup",
        "permission_snapshot_digest": _TEST_PERMISSION_SNAPSHOT_DIGEST,
        "queue_consumer_receipt_digest": queue_receipt_digest,
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "wsp15_allocation_digest": canonical_digest(allocation),
        "wsp15_priority": allocation["priority"],
        "wsp15_mps_total": allocation["mps_total"],
        "wsp15_reasoning_tier": allocation["reasoning_tier"],
        "nonce": "worker-dispatch-nonce-0001",
        "issued_at": _TEST_NOW - 5,
        "expires_at": _TEST_NOW + 300,
        "valve_state_required": "VALVE_OPEN_WORKTREE_CREATE",
        "key_epoch": "epoch-1",
        **work_authority_overrides,
    }
    work_authority["signature"] = _sign(
        _TEST_REDDOG_SECRET,
        canonical_signing_input(work_authority, "reddog-workauth.v1"),
    )
    authority_digest = canonical_digest(work_authority)
    authority_runtime = {
        "decision": "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT",
        "authority_result": {
            "accepted": True,
            "receipt": {
                "status": "DELEGATED_AUTHORITY_ISSUED",
                "receipt_id": "authority-runtime-receipt-1",
                "work_authority_digest": authority_digest,
            },
            "work_authority": work_authority,
            "identity": identity,
        },
    }
    authority_verification = {
        "decision": "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT",
        "verification_result": {
            "accepted": True,
            "reason_codes": [],
            "work_order_id": str(work_authority["work_order_id"]),
        },
        "verified_work_authority_digest": authority_digest,
    }
    authority_verification.update(
        recorded_authority_verification_binding(
            authority_runtime,
            authority_verification,
        )
    )
    return authority_runtime, authority_verification


def worker_dispatch_authority_verification_context():
    return WorkerDispatchAuthorityVerificationContext(
        signature_verifier=_WorkerDispatchSignatureVerifier(),
        principal_key_resolver=_WorkerDispatchPrincipalResolver(),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=_WorkerDispatchSnapshotResolver(),
        revocation_oracle=_WorkerDispatchNoRevocation(),
        trusted_now_epoch=lambda: _TEST_NOW,
        required_valve_state="VALVE_OPEN_WORKTREE_CREATE",
    )


def install_signed_worker_envelope_test_authority(monkeypatch: Any) -> None:
    """Use real runtime authority when configured, otherwise the HMAC fixture."""

    from modules.communication.moltbot_bridge.src import (
        reddog_signed_worker_agentdb_envelope as envelope_module,
    )

    original = envelope_module.build_worker_dispatch_authority_context_from_env

    def _context(**kwargs: Any):
        try:
            return replace(original(**kwargs), trusted_now_epoch=lambda: _TEST_NOW)
        except Exception:
            return worker_dispatch_authority_verification_context()

    monkeypatch.setattr(
        envelope_module,
        "build_worker_dispatch_authority_context_from_env",
        _context,
    )


def configure_signed_worker_claim_authority_env(
    monkeypatch: Any,
    *,
    chain_path: Path,
    signature_backend: str,
) -> None:
    """Bind restart authority files co-located with the queue chain."""

    root = chain_path.parent
    values = {
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code_fusion",
        "REDDOG_AUTHORITY_RUNTIME_STATE_PATH": str(root / "authority_state.json"),
        "REDDOG_PERMISSION_SNAPSHOTS_PATH": str(root / "snapshots.json"),
        "REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH": str(root / "principals.json"),
        "REDDOG_SIGNATURE_VERIFIER_BACKEND": signature_backend,
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def configure_signed_worker_claim_test_authority(
    monkeypatch: Any, *, chain_path: Path, signature_backend: str
) -> None:
    """Bind persisted authority files and a deterministic claim-time clock."""

    configure_signed_worker_claim_authority_env(
        monkeypatch,
        chain_path=chain_path,
        signature_backend=signature_backend,
    )
    install_signed_worker_envelope_test_authority(monkeypatch)


def worker_dispatch_dryrun_result(allocation: dict[str, Any]) -> dict[str, Any]:
    """Build a canonical synthetic dry-run from the authoritative worker plan."""

    model_refs = {
        "model_runtime_binding_receipt_id": str(
            allocation.get("model_runtime_binding_receipt_id") or ""
        ),
        "model_runtime_binding_digest": str(
            allocation.get("model_runtime_binding_digest") or ""
        ),
    }
    base = {
        "work_order_id": "wo-1",
        "foundup_id": _TEST_FOUNDUP,
        "requested_operation": "create_foundup",
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "wsp15_allocation_digest": canonical_digest(allocation),
        **model_refs,
        "architect_fix_publication_receipt_id": "",
        "architect_fix_publication_binding_digest": "",
    }
    intents = [
        {
            "intent_id": f"worker_dispatch_intent_{role}",
            "role": role,
            "worker_runtime": worker_runtime,
            "capability": capability,
            **base,
            "dry_run_only": True,
            "no_worker_spawn_performed": True,
            "no_openclaw_enqueue_performed": True,
            "no_hermes_dispatch_performed": True,
        }
        for role, worker_runtime, capability in derive_worker_dispatch_roles(allocation)
    ]
    return {
        "accepted": True,
        "decision": "SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT",
        "rejection_reasons": [],
        "receipt": {
            "receipt_id": "signed_authority_worker_dispatch_abc",
            **base,
            "wsp15_priority": allocation["priority"],
            "wsp15_mps_total": allocation["mps_total"],
            "wsp15_reasoning_tier": allocation["reasoning_tier"],
            "dispatch_intent_count": len(intents),
            "dispatch_intents": intents,
            "no_worker_spawn_performed": True,
            "no_queue_mutation_performed": True,
            "no_worktree_created": True,
            "no_shell_command_executed": True,
            "no_openclaw_enqueue_performed": True,
            "no_hermes_dispatch_performed": True,
            "no_repo_mutation_performed": True,
            "no_holoindex_reindex_performed": True,
            "no_pr_created": True,
            "no_reward_settlement_performed": True,
        },
    }


def _sign(secret: bytes, signing_input: str) -> str:
    return hmac.new(
        secret,
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def publish_bound_worker_dispatch(**kwargs: Any):
    """Call the runtime publisher with an independently built authority proof."""

    from modules.communication.moltbot_bridge.src import (
        reddog_openclaw_hermes_0102_worker_dispatch_runtime as runtime,
    )

    snapshot = kwargs.get("work_state_snapshot", {})
    queue_items = snapshot.get("wre_queue_items", [])
    allocation = queue_items[0]["wsp15_allocation_receipt"]
    call_args = dict(kwargs)
    supplied_dryrun = dict(call_args.pop("worker_dispatch_dryrun_result"))
    receipt = dict(supplied_dryrun["receipt"])
    signed_optional = {
        field: receipt[field]
        for field in (
            "model_runtime_binding_receipt_id",
            "model_runtime_binding_digest",
            "architect_fix_publication_receipt_id",
            "architect_fix_publication_binding_digest",
        )
        if receipt.get(field)
    }
    authority_runtime, authority_verification = worker_dispatch_authority_stages(
        allocation,
        work_state_snapshot=snapshot,
        queue_item_id=str(call_args.get("queue_item_id") or "queue-1"),
        **signed_optional,
    )
    from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
        plan_reddog_signed_authority_worker_dispatch_dry_run,
    )

    dryrun = plan_reddog_signed_authority_worker_dispatch_dry_run(
        explicit_signed_authority_worker_dispatch_dryrun_requested=True,
        queue_authority_verification_result=authority_verification,
        queue_authority_runtime_result=authority_runtime,
        wsp15_allocation_receipt=allocation,
    ).to_dict()
    assert dryrun["accepted"] is True
    return runtime.publish_reddog_signed_worker_dispatch_runtime(
        **call_args,
        worker_dispatch_dryrun_result=dryrun,
        queue_authority_runtime_result=authority_runtime,
        queue_authority_verification_result=authority_verification,
        authority_verification_context=worker_dispatch_authority_verification_context(),
    )


def publish_agentdb_task_for_intent(
    *,
    allocation: dict[str, Any],
    intent_overrides: dict[str, Any],
    dryrun_builder: Any,
    snapshot_builder: Any,
    context_override_builder: Any,
    digest_builder: Any,
):
    """Publish a real planned intent or a deliberately invalid outer fixture."""

    from modules.communication.moltbot_bridge.src import (
        reddog_openclaw_hermes_0102_worker_dispatch_runtime as runtime,
    )

    requested_role = str(intent_overrides.get("role") or "")
    requested_intent_id = str(intent_overrides.get("intent_id") or "")
    if requested_intent_id:
        allocation = {
            **allocation,
            "receipt_id": digest_builder(
                {
                    "base_receipt_id": allocation["receipt_id"],
                    "requested_intent_id": requested_intent_id,
                }
            ),
        }
    if requested_role == "openclaw_candidate":
        allocation = {
            **allocation,
            "worker_plan": {
                **dict(allocation["worker_plan"]),
                "coding_worker_count": 0,
                "independent_verifier_required": False,
                "openclaw_candidate": True,
            },
        }
    result = publish_bound_worker_dispatch(
        worker_dispatch_dryrun_result=dryrun_builder(allocation=allocation),
        work_state_snapshot=snapshot_builder(allocation),
        queue_item_id="queue-1",
        writer=_CollectingAgentDbSpecWriter(),
    )
    assert result.accepted is True and result.receipt is not None
    matching = [
        task
        for task in result.tasks
        if str(task.context.get("worker_role") or "") == requested_role
    ]
    base = matching[0] if matching else result.tasks[0]
    if matching:
        specs = (base,)
    else:
        context = context_override_builder(base.context, intent_overrides)
        intent = context["worker_dispatch_intent"]
        task_id = "reddog-worker-dispatch-" + digest_builder(
            {"intent_id": intent["intent_id"], "context": context}
        )[7:23]
        specs = (
            runtime.SignedWorkerDispatchTaskSpec(
                task_id=task_id,
                description=f"RedDog signed worker dispatch test fixture: {intent['role']}",
                required_skills=(
                    runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL,
                    f"runtime:{intent['worker_runtime']}",
                    f"capability:{intent['capability']}",
                ),
                estimated_complexity=base.estimated_complexity,
                priority_score=base.priority_score,
                context=context,
                origin_continuity_id=base.origin_continuity_id,
            ),
        )
    written = runtime.AgentDbSignedWorkerDispatchTaskWriter().enqueue_signed_worker_dispatch_tasks(
        specs,
        result.receipt,
    )
    assert written["ok"] is True
    return specs[0].task_id


class _CollectingAgentDbSpecWriter:
    def enqueue_signed_worker_dispatch_tasks(self, tasks: Any, receipt: Any):
        return {
            "ok": True,
            "created_task_ids": [task.task_id for task in tasks],
        }


def with_architect_fix_publication(
    snapshot: dict[str, Any],
    authority_profile: dict[str, Any],
    *,
    state: str = "COMMITTED",
) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    """Bind a resident queue fixture to one architect FIX publication."""

    publication_id = "sha256:" + "4" * 64
    queue_item_id = "sha256:" + "5" * 64
    claim_id = "sha256:" + "6" * 64
    attestation_id = "reddog_architect_proposal_attestation_" + "7" * 32
    profile = {
        **authority_profile,
        "promotion_publication_id": publication_id,
        "proposal_authenticity_attestation_id": attestation_id,
        "operational_context_binding": {
            "queue_item_id": queue_item_id,
            "claim_id": claim_id,
        },
    }
    current = _replace_queue_claim_ids(
        snapshot,
        queue_item_id=queue_item_id,
        claim_id=claim_id,
    )
    promotion = {
        "publication_id": publication_id,
        "queue_item_id": queue_item_id,
        "claim_id": claim_id,
        "authority_profile_digest": canonical_digest(profile),
        "proposal_authenticity_attestation_id": attestation_id,
    }
    current["architect_fix_promotions"] = [promotion]
    current["revision"] = "8" * 64
    projection = architect_fix_publication_state_projection(
        current,
        publication_id=publication_id,
    )
    current["architect_fix_publications"] = [{
        "schema_version": "reddog_architect_fix_promotion_publication.v1",
        "publication_id": publication_id,
        "state": state,
        "proposal_authenticity_attestation_id": attestation_id,
        "authority_profile_digest": canonical_digest(profile),
        "active_work_state_digest": canonical_digest(projection),
        "base_work_state_digest": (
            None if state == "COMMITTED" else "sha256:" + "9" * 64
        ),
    }]
    return current, profile, queue_item_id, claim_id


def _replace_queue_claim_ids(
    snapshot: dict[str, Any],
    *,
    queue_item_id: str,
    claim_id: str,
) -> dict[str, Any]:
    current = {**snapshot}
    claim = {**current["worker_claims"][0], "claim_id": claim_id}
    queue = {
        **current["wre_queue_items"][0],
        "queue_item_id": queue_item_id,
        "claim_id": claim_id,
    }
    refs = [
        ref
        for ref in queue.get("evidence_refs") or ()
        if not str(ref).startswith("claim:")
    ]
    queue["evidence_refs"] = [f"claim:{claim_id}", *refs]
    current["worker_claims"] = [claim]
    current["wre_queue_items"] = [queue]
    return current
