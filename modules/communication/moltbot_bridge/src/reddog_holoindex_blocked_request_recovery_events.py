"""AgentDB event bindings for Holo blocked-request recovery."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_holoindex_incident_repair_contract import (
    canonical_digest,
)


STAGE_EVENT_PREFIX = "reddog_holoindex_blocked_retry_staged:"
STAGE_EVENT_TYPE = "holoindex_blocked_request_retry_staged"
CLAIM_EVENT_PREFIX = "reddog_holoindex_blocked_retry_claimed:"
CLAIM_EVENT_TYPE = "holoindex_blocked_request_retry_claimed"
INITIATOR = "reddog_recovery_bridge"
TARGETS = ["reddog_extension"]


def event_id(prefix: str, recovery_id: str) -> str:
    return prefix + recovery_id[7:]


def stage_event_id(payload: Mapping[str, Any]) -> str:
    return STAGE_EVENT_PREFIX + str(payload["payload_digest"])[7:]


def build_stage_payload(
    *, schema_version: str, recovery_id: str, request_digest: str,
    query_digest: str, incident_id: str, incident_receipt_id: str,
    task_id: str, target_repo_head_sha: str, authority_root_digest: str,
    created_at_epoch_ms: int, expires_at_epoch_ms: int,
) -> dict[str, Any]:
    payload = {
        "schema_version": schema_version, "status": "STAGED",
        "recovery_id": recovery_id, "request_digest": request_digest,
        "query_digest": query_digest, "incident_id": incident_id,
        "incident_receipt_id": incident_receipt_id, "task_id": task_id,
        "target_repo_head_sha": target_repo_head_sha,
        "authority_root_digest": authority_root_digest,
        "created_at_epoch_ms": created_at_epoch_ms,
        "expires_at_epoch_ms": expires_at_epoch_ms,
        "authority_effect": "none",
    }
    payload["payload_digest"] = canonical_digest(payload)
    return payload


def build_claim_payload(
    *, stage_payload: Mapping[str, Any], generation_id: str,
    freshness_receipt_digest: str,
) -> dict[str, Any]:
    payload = {
        **{key: stage_payload[key] for key in (
            "schema_version", "recovery_id", "request_digest", "query_digest",
            "incident_id", "incident_receipt_id", "task_id",
            "target_repo_head_sha", "authority_root_digest",
        )},
        "status": "ADMITTED",
        "stage_event_id": stage_event_id(stage_payload),
        "stage_payload_digest": stage_payload["payload_digest"],
        "generation_id": generation_id,
        "freshness_receipt_digest": freshness_receipt_digest,
        "authority_effect": "none",
    }
    payload["payload_digest"] = canonical_digest(payload)
    return payload


def _event_matches(event: Any, event_type: str, payload: Mapping[str, Any]) -> bool:
    return bool(
        isinstance(event, Mapping)
        and event.get("event_type") == event_type
        and event.get("initiator_agent") == INITIATOR
        and event.get("target_agents") == TARGETS
        and event.get("payload") == payload
    )


def stage_once(database: Any, payload: Mapping[str, Any]) -> tuple[str, str]:
    stage_id = stage_event_id(payload)
    created = database.create_coordination_event(
        stage_id, STAGE_EVENT_TYPE, INITIATOR, TARGETS, dict(payload)
    )
    if created:
        return "STAGED", stage_id
    existing = database.get_coordination_event_by_id(stage_id)
    return ("STAGED", stage_id) if _event_matches(
        existing, STAGE_EVENT_TYPE, payload
    ) else ("REJECTED", stage_id)


def stage_matches(database: Any, payload: Mapping[str, Any]) -> bool:
    stage_id = stage_event_id(payload)
    return _event_matches(
        database.get_coordination_event_by_id(stage_id), STAGE_EVENT_TYPE, payload
    )


def claim_once(
    database: Any, stage_payload: Mapping[str, Any], claim_payload: Mapping[str, Any],
    *, stage_verified: bool = False,
) -> tuple[str, str, str]:
    if not stage_verified and not stage_matches(database, stage_payload):
        return "REJECTED", "", "recovery_stage_binding_missing"
    claim_id = event_id(CLAIM_EVENT_PREFIX, claim_payload["recovery_id"])
    created = database.create_coordination_event(
        claim_id, CLAIM_EVENT_TYPE, INITIATOR, TARGETS, dict(claim_payload)
    )
    if created:
        return "READY", claim_id, ""
    if database.get_coordination_event_by_id(claim_id) is not None:
        return "REJECTED", claim_id, "recovery_already_claimed"
    return "WAITING", claim_id, "recovery_claim_store_unavailable"


def admit_ready(
    database: Any, receipt: Any, completion: Mapping[str, Any],
    stage_payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    payload = build_claim_payload(
        stage_payload=stage_payload, generation_id=completion["generation_id"],
        freshness_receipt_digest=completion["freshness_receipt_digest"],
    )
    status, claim_id, reason = claim_once(
        database, stage_payload, payload, stage_verified=True
    )
    if status != "READY":
        return {"ok": False, "status": status, "reason": reason}
    return {
        "ok": True, "status": "READY", "reason": "",
        "incident_id": receipt.incident_id,
        "incident_task_id": receipt.task_id,
        "incident_repair_receipt_id": receipt.receipt_id,
        "target_repo_head_sha": receipt.target_repo_head_sha,
        "authority_root_digest": receipt.authority_root_digest,
        "generation_id": completion["generation_id"],
        "freshness_receipt_digest": completion["freshness_receipt_digest"],
        "recovery_id": stage_payload["recovery_id"],
        "request_digest": stage_payload["request_digest"],
        "query_digest": stage_payload["query_digest"],
        "stage_event_id": payload["stage_event_id"],
        "stage_payload_digest": payload["stage_payload_digest"],
        "claim_event_id": claim_id,
        "claim_payload_digest": payload["payload_digest"],
        "no_holoindex_reindex_performed": True,
        "authority_effect": "none",
    }


__all__ = [
    "CLAIM_EVENT_PREFIX", "STAGE_EVENT_PREFIX", "admit_ready",
    "build_claim_payload", "build_stage_payload", "claim_once", "event_id",
    "stage_event_id", "stage_matches", "stage_once",
]
