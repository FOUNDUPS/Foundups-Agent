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
from typing import Any, Callable, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_resident_architect_client import (
    RedDogResidentArchitectClient,
    ResidentClientResponse,
)
from modules.communication.moltbot_bridge.src.reddog_transport_neutral_grounding_service import (
    TransportGroundingResult,
    ground_transport_work_focus,
)


HERMES_REQUEST_SCHEMA = "hermes_reddog_resident_request.v1"
HERMES_TEXT_REQUEST_SCHEMA = "hermes_reddog_resident_request.v2"
HERMES_RECEIPT_SCHEMA = "hermes_reddog_resident_receipt.v1"
OPERATIONS = frozenset({"submit", "status", "cancel", "resume"})
RESERVED_IDENTITY_FIELDS = frozenset(
    {"principal_id", "principal_ref", "origin_principal", "source_surface", "origin"}
)

GroundingService = Callable[..., TransportGroundingResult]


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
        authorized_foundup_ids: Sequence[str],
        resident_client: RedDogResidentArchitectClient | None = None,
        grounding_service: GroundingService | None = None,
        runtime_defaults: Mapping[str, Any] | None = None,
    ) -> None:
        self._repo_root = Path(repo_root).resolve()
        self._principal = str(authenticated_principal_id or "").strip()
        scope_input_valid = not isinstance(authorized_foundup_ids, (str, bytes))
        self._authorized_foundup_ids = frozenset(
            str(item or "").strip() for item in authorized_foundup_ids if str(item or "").strip()
        ) if scope_input_valid else frozenset()
        if not self._principal or not self._authorized_foundup_ids:
            raise ValueError("REJECT_HERMES_REDDOG_RUNTIME_CONFIGURATION")
        self._grounding_service = grounding_service or ground_transport_work_focus
        self._client = resident_client or RedDogResidentArchitectClient(
            repo_root=self._repo_root,
            authenticated_principal_id=self._principal,
            authorized_foundup_ids=self._authorized_foundup_ids,
            transport="hermes",
            runtime_defaults=runtime_defaults,
        )

    def handle(self, request: Mapping[str, Any] | None) -> HermesRedDogResidentReceipt:
        data = dict(request) if isinstance(request, Mapping) else {}
        request_id = str(data.get("request_id") or "").strip()
        operation = str(data.get("operation") or "").strip().lower()
        schema = data.get("schema_version")
        if schema not in {HERMES_REQUEST_SCHEMA, HERMES_TEXT_REQUEST_SCHEMA} or not request_id or operation not in OPERATIONS:
            return self._receipt(
                request_id=request_id,
                operation=operation,
                response=_rejected_response(operation, "REJECT_HERMES_REDDOG_REQUEST_INVALID"),
            )
        if operation == "submit":
            if RESERVED_IDENTITY_FIELDS.intersection(data):
                response = _rejected_response(operation, "REJECT_HERMES_REDDOG_IDENTITY_INJECTION")
            elif schema == HERMES_TEXT_REQUEST_SCHEMA:
                response = self._submit_text(data, request_id)
            else:
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

    def _submit_text(self, data: Mapping[str, Any], request_id: str) -> ResidentClientResponse:
        if data.get("red_dog_intent") is not None or data.get("grounding_receipt") is not None:
            return _rejected_response("submit", "REJECT_HERMES_REDDOG_GROUNDING_SUBSTITUTION")
        foundup_id = str(data.get("foundup_id") or "").strip()
        if foundup_id not in self._authorized_foundup_ids:
            return _rejected_response("submit", "REJECT_HERMES_REDDOG_FOUNDUP_SCOPE_MISMATCH")
        try:
            grounded = self._grounding_service(
                repo_root=self._repo_root,
                work_focus=str(data.get("work_focus") or ""),
                foundup_id=foundup_id,
                authenticated_principal_id=self._principal,
                source_surface="hermes_thin_client",
                client_request_id=request_id,
            )
        except Exception:
            return _rejected_response("submit", "REJECT_HERMES_REDDOG_GROUNDING_FAILED")
        if not grounded.accepted:
            reason = ",".join(grounded.rejection_reasons) or "REJECT_HERMES_REDDOG_GROUNDING_FAILED"
            return _rejected_response("submit", reason)
        return self._client.submit(grounded.intent)

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
    "HERMES_TEXT_REQUEST_SCHEMA",
    "HermesRedDogResidentClientAdapter",
    "HermesRedDogResidentReceipt",
]
