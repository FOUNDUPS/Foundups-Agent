"""Hermes transport adapter for the canonical resident RedDog client.

Hermes is a communication surface here, not a second RedDog authority. The
hosting instrument supplies the authenticated principal. Request text, role
labels, and payload principal fields never grant authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_resident_architect_client import (
    RedDogResidentArchitectClient,
    ResidentClientResponse,
)


HERMES_REQUEST_SCHEMA = "hermes_reddog_resident_request.v1"
HERMES_RECEIPT_SCHEMA = "hermes_reddog_resident_receipt.v1"
OPERATIONS = frozenset({"submit", "status", "cancel", "resume"})


@dataclass(frozen=True)
class HermesRedDogResidentReceipt:
    schema_version: str
    receipt_id: str
    accepted: bool
    request_id: str
    operation: str
    resident_response: Mapping[str, Any]
    canonical_reddog_authority_used: bool = True
    hermes_is_transport_only: bool = True
    no_hermes_model_invoked: bool = True
    no_hermes_execution_performed: bool = True
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_worktree_operation_performed: bool = True
    no_pr_created: bool = True
    no_merge_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["resident_response"] = dict(self.resident_response)
        return payload


class HermesRedDogResidentClientAdapter:
    """Translate a Hermes instrument request into one resident client call."""

    def __init__(
        self,
        *,
        repo_root: Path | str,
        authenticated_principal_id: str,
        resident_client: RedDogResidentArchitectClient | None = None,
        runtime_defaults: Mapping[str, Any] | None = None,
    ) -> None:
        self._client = resident_client or RedDogResidentArchitectClient(
            repo_root=repo_root,
            authenticated_principal_id=authenticated_principal_id,
            transport="hermes",
            runtime_defaults=runtime_defaults,
        )

    def handle(self, request: Mapping[str, Any] | None) -> HermesRedDogResidentReceipt:
        data = dict(request) if isinstance(request, Mapping) else {}
        request_id = str(data.get("request_id") or "").strip()
        operation = str(data.get("operation") or "").strip().lower()
        if data.get("schema_version") != HERMES_REQUEST_SCHEMA or not request_id or operation not in OPERATIONS:
            return self._receipt(
                request_id=request_id,
                operation=operation,
                response=_rejected_response(operation, "REJECT_HERMES_REDDOG_REQUEST_INVALID"),
            )
        if operation == "submit":
            intent = data.get("red_dog_intent")
            response = self._client.submit(intent if isinstance(intent, Mapping) else None)
        else:
            if data.get("red_dog_intent") is not None:
                response = _rejected_response(operation, "REJECT_HERMES_REDDOG_INTENT_SUBSTITUTION")
            else:
                intent_id = str(data.get("intent_id") or "").strip()
                response = {
                    "status": self._client.status,
                    "cancel": self._client.cancel,
                    "resume": self._client.resume,
                }[operation](intent_id)
        return self._receipt(request_id=request_id, operation=operation, response=response)

    @staticmethod
    def _receipt(
        *,
        request_id: str,
        operation: str,
        response: ResidentClientResponse,
    ) -> HermesRedDogResidentReceipt:
        response_data = response.to_dict()
        payload = {
            "schema_version": HERMES_RECEIPT_SCHEMA,
            "accepted": response.accepted,
            "request_id": request_id,
            "operation": operation,
            "resident_response": response_data,
            "canonical_reddog_authority_used": response.canonical_resident_cycle_used,
            "hermes_is_transport_only": True,
            "no_hermes_model_invoked": True,
            "no_hermes_execution_performed": True,
            "no_shell_command_executed": True,
            "no_repo_mutation_performed": True,
            "no_holoindex_reindex_performed": True,
            "no_worktree_operation_performed": True,
            "no_pr_created": True,
            "no_merge_performed": True,
        }
        return HermesRedDogResidentReceipt(receipt_id=_digest(payload), **payload)


def _rejected_response(operation: str, reason: str) -> ResidentClientResponse:
    payload = {
        "operation": operation,
        "transport": "hermes",
        "intent_id": "",
        "cycle_id": "",
        "status": "REJECTED",
        "snapshot_id": "",
        "determination_id": "",
        "architect_action": "",
        "architect_next_slice": "",
        "task_status_counts": {},
        "rejection_reasons": (reason,),
    }
    return ResidentClientResponse(
        schema_version="reddog_resident_client_response.v1",
        response_id=_digest(payload),
        accepted=False,
        canonical_resident_cycle_used=False,
        **payload,
    )


def _digest(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


__all__ = [
    "HERMES_RECEIPT_SCHEMA",
    "HERMES_REQUEST_SCHEMA",
    "HermesRedDogResidentClientAdapter",
    "HermesRedDogResidentReceipt",
]
