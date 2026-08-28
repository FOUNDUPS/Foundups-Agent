"""Governed Grok Bot tool-provider boundary for RedDog.

Grok Bot is an external worker/tool surface, never RedDog authority. This module
intentionally contains no Grok Bot network client, token loading, subprocess,
shell, or repository mutation. A hosting integration must inject a dispatcher
only after RedDog/WRE has admitted the work order and scoped its authority.

The first-party xAI Grok Bot product currently documents persistent cloud
computers, plugins/MCP, approvals, skills, and routines, but not a stable public
execution API. Keeping transport injected prevents the FoundUps core from
binding itself to an undocumented local gateway or third-party SDK contract.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping


GROKBOT_TOOL_REQUEST_SCHEMA = "reddog_grokbot_tool_request.v1"
GROKBOT_TOOL_RECEIPT_SCHEMA = "reddog_grokbot_tool_receipt.v1"
ALLOWED_OPERATIONS = frozenset({"health", "execute", "status", "cancel"})
RESERVED_AUTHORITY_FIELDS = frozenset(
    {
        "principal_id",
        "principal_ref",
        "origin_principal",
        "authority",
        "authority_token",
        "credential",
        "credentials",
        "token",
        "api_key",
    }
)

Dispatcher = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True)
class GrokBotToolReceipt:
    schema_version: str
    receipt_id: str
    accepted: bool
    request_id: str
    operation: str
    provider: str
    result: Mapping[str, Any]
    reddog_authority_retained: bool = True
    grokbot_is_external_tool_only: bool = True
    transport_injected: bool = True
    no_credential_material_accepted: bool = True
    no_provider_authority_minted: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["result"] = dict(self.result)
        return payload


class GrokBotRedDogToolProvider:
    """Fail-closed RedDog tool adapter for a separately hosted Grok Bot transport."""

    def __init__(self, *, dispatcher: Dispatcher | None, enabled: bool = False) -> None:
        self._dispatcher = dispatcher
        self._enabled = bool(enabled)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def capabilities(self) -> dict[str, Any]:
        return {
            "provider": "grokbot",
            "enabled": self._enabled,
            "operations": tuple(sorted(ALLOWED_OPERATIONS)),
            "persistent_computer": True,
            "browser_computer_use": True,
            "plugins_mcp": True,
            "skills_routines": True,
            "shared_account_computer_boundary": True,
            "public_execution_api_assumed": False,
        }

    def handle(self, request: Mapping[str, Any] | None) -> GrokBotToolReceipt:
        data = dict(request) if isinstance(request, Mapping) else {}
        request_id = str(data.get("request_id") or "").strip()
        operation = str(data.get("operation") or "").strip().lower()

        if (
            data.get("schema_version") != GROKBOT_TOOL_REQUEST_SCHEMA
            or not request_id
            or operation not in ALLOWED_OPERATIONS
        ):
            return self._reject(request_id, operation, "REJECT_GROKBOT_REQUEST_INVALID")
        if RESERVED_AUTHORITY_FIELDS.intersection(data):
            return self._reject(request_id, operation, "REJECT_GROKBOT_AUTHORITY_INJECTION")
        if not self._enabled:
            return self._reject(request_id, operation, "REJECT_GROKBOT_PROVIDER_DISABLED")
        if self._dispatcher is None:
            return self._reject(request_id, operation, "REJECT_GROKBOT_TRANSPORT_UNAVAILABLE")

        if operation == "execute":
            work_order = data.get("work_order")
            if not isinstance(work_order, Mapping):
                return self._reject(request_id, operation, "REJECT_GROKBOT_WORK_ORDER_REQUIRED")
            if RESERVED_AUTHORITY_FIELDS.intersection(work_order):
                return self._reject(request_id, operation, "REJECT_GROKBOT_WORK_ORDER_AUTHORITY_INJECTION")
            admitted = work_order.get("admitted") is True
            work_order_id = str(work_order.get("work_order_id") or "").strip()
            if not admitted or not work_order_id:
                return self._reject(request_id, operation, "REJECT_GROKBOT_WORK_ORDER_NOT_ADMITTED")

        outbound = {
            "schema_version": GROKBOT_TOOL_REQUEST_SCHEMA,
            "request_id": request_id,
            "operation": operation,
        }
        for key in ("work_order", "job_id"):
            if key in data:
                outbound[key] = data[key]

        try:
            raw = self._dispatcher(outbound)
        except Exception:
            return self._reject(request_id, operation, "REJECT_GROKBOT_TRANSPORT_FAILURE")
        if not isinstance(raw, Mapping):
            return self._reject(request_id, operation, "REJECT_GROKBOT_RESULT_INVALID")

        result = dict(raw)
        accepted = result.get("accepted") is True
        if not accepted and "rejection_reason" not in result:
            result["rejection_reason"] = "REJECT_GROKBOT_PROVIDER_RESULT"
        return self._receipt(request_id=request_id, operation=operation, accepted=accepted, result=result)

    def _reject(self, request_id: str, operation: str, reason: str) -> GrokBotToolReceipt:
        return self._receipt(
            request_id=request_id,
            operation=operation,
            accepted=False,
            result={"accepted": False, "rejection_reason": reason},
        )

    @staticmethod
    def _receipt(
        *,
        request_id: str,
        operation: str,
        accepted: bool,
        result: Mapping[str, Any],
    ) -> GrokBotToolReceipt:
        payload = {
            "schema_version": GROKBOT_TOOL_RECEIPT_SCHEMA,
            "accepted": accepted,
            "request_id": request_id,
            "operation": operation,
            "provider": "grokbot",
            "result": dict(result),
            "reddog_authority_retained": True,
            "grokbot_is_external_tool_only": True,
            "transport_injected": True,
            "no_credential_material_accepted": True,
            "no_provider_authority_minted": True,
        }
        return GrokBotToolReceipt(receipt_id=_digest(payload), **payload)


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
    "ALLOWED_OPERATIONS",
    "GROKBOT_TOOL_RECEIPT_SCHEMA",
    "GROKBOT_TOOL_REQUEST_SCHEMA",
    "GrokBotRedDogToolProvider",
    "GrokBotToolReceipt",
]
