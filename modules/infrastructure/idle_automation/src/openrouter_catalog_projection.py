"""Fail-closed projection of provider catalog evidence into claim finalization."""

from __future__ import annotations

from typing import Any

_RESULT_KEYS = frozenset(
    (
        "success",
        "status",
        "reason",
        "replayed",
        "receipt_id",
        "candidate_snapshot_id",
    )
)


def project_openrouter_catalog_dispatch_outcome(
    response: object,
) -> dict[str, Any]:
    """Admit only one exact evidence-bearing completion projection."""

    if (
        type(response) is dict
        and set(response) == _RESULT_KEYS
        and response["success"] is True
        and response["status"] == "COMPLETED"
        and response["reason"] == "completed"
        and type(response["replayed"]) is bool
        and _evidence_id(
            response["receipt_id"],
            "model_provider_catalog_discovery_receipt:",
        )
        and _evidence_id(
            response["candidate_snapshot_id"],
            "model_provider_catalog_candidate_snapshot:",
        )
    ):
        return {"success": True, "outcome": "routine_failed", "error": None}
    return {
        "success": False,
        "outcome": "routine_failed",
        "error": "Provider catalog refresh failed",
    }


def _evidence_id(value: object, prefix: str) -> bool:
    return (
        type(value) is str
        and value.startswith(prefix)
        and len(value) == len(prefix) + 64
        and all(character in "0123456789abcdef" for character in value[len(prefix):])
    )


__all__ = ["project_openrouter_catalog_dispatch_outcome"]
