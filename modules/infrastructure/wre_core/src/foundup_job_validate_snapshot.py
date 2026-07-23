# -*- coding: utf-8 -*-
"""Detached execution snapshot for routed validate_foundup jobs."""

from __future__ import annotations

from typing import Any, Optional

from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
)

from .foundup_job_model_capability_receipt import (
    normalize_canonical_json_mapping,
)


_INGRESS_AUTHORITY_FIELDS = {
    "model_runtime_binding_receipt",
    "model_runtime_binding_digest",
}


def freeze_validate_foundup_job(job: Any) -> Optional[FoundUpJob]:
    """Reconstruct a detached canonical job with ingress authority removed."""
    try:
        payload = getattr(job, "payload", None)
        if payload is None:
            payload = {}
        if type(payload) is not dict:
            return None
        clean_payload = {
            key: value
            for key, value in payload.items()
            if key not in _INGRESS_AUTHORITY_FIELDS
        }
        if isinstance(job, FoundUpJob):
            data = job.to_dict()
        else:
            flags = getattr(job, "policy_flags", None)
            data = {
                "job_id": getattr(job, "job_id", ""),
                "tenant_id": getattr(job, "tenant_id", ""),
                "foundup_id": getattr(job, "foundup_id", None),
                "requested_action": getattr(job, "requested_action", ""),
                "status": _enum_value(getattr(job, "status", "queued")),
                "policy_flags": flags.to_dict() if flags else {},
            }
        data["payload"] = clean_payload
        normalized = normalize_canonical_json_mapping(data)
        return FoundUpJob.from_dict(normalized) if normalized is not None else None
    except Exception:
        return None


def _enum_value(value: Any) -> str:
    return str(value.value if hasattr(value, "value") else value)


__all__ = ["freeze_validate_foundup_job"]
