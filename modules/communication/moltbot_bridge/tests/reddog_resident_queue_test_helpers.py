"""Shared resident queue test fixtures."""

from __future__ import annotations

import hashlib
import hmac
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


def worker_dispatch_authority_stages(
    allocation: dict[str, Any],
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
    work_authority = {
        "work_order_id": "wo-1",
        "work_order_digest": _TEST_WORK_ORDER_DIGEST,
        "base_ref": "main",
        "principal_id": "github:mjtrout",
        "reddog_id": "reddog:worker-dispatch",
        "repo_full_name": _TEST_REPO,
        "foundup_id": _TEST_FOUNDUP,
        "allowed_paths": [f"modules/foundups/{_TEST_FOUNDUP}/**"],
        "denied_paths": [],
        "requested_operation": "create_foundup",
        "permission_snapshot_digest": _TEST_PERMISSION_SNAPSHOT_DIGEST,
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
    dryrun = dict(call_args.pop("worker_dispatch_dryrun_result"))
    receipt = dict(dryrun["receipt"])
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
        **signed_optional,
    )
    refs = {
        key: authority_verification[key]
        for key in (
            "verified_work_authority_digest",
            "authority_verification_receipt_id",
            "authority_verification_receipt_digest",
        )
    }
    receipt["dispatch_intents"] = [
        {**dict(intent), **refs} for intent in receipt["dispatch_intents"]
    ]
    dryrun["receipt"] = {**receipt, **refs}
    return runtime.publish_reddog_signed_worker_dispatch_runtime(
        **call_args,
        worker_dispatch_dryrun_result=dryrun,
        queue_authority_runtime_result=authority_runtime,
        queue_authority_verification_result=authority_verification,
        authority_verification_context=worker_dispatch_authority_verification_context(),
    )


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
