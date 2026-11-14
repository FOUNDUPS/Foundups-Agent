"""Transport-neutral client for the canonical resident RedDog authority.

Slice: REDDOG_TRANSPORT_NEUTRAL_RESIDENT_CLIENT_AND_HERMES_ADAPTER_PHASE1

Editor, Hermes, and future API surfaces use this client to submit or reconnect
to the same durable AgentDB resident cycle. The client does not implement a
second architect, run a model, execute a shell, mutate a repository, or grant
authority. The authenticated principal is supplied by the hosting transport,
never trusted from request prose.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    validate_grounded_target_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_resident_legacy_main_control import (
    authorize_legacy_main_record,
    cancel_legacy_main_record,
)
from modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle import (
    AgentDbResidentArchitectCycleStore,
    RUNTIME_BOUNDARY_FIELDS,
    ResidentArchitectCycleStore,
    ResidentCycleReason,
    STATUS_CANCELLED,
    STATUS_FAILED,
    STATUS_TIMED_OUT,
    resident_intent_digest,
)


CLIENT_RESPONSE_SCHEMA = "reddog_resident_client_response.v1"
TRANSPORT_TO_SOURCE = {
    "editor": "editor_thin_client",
    "hermes": "hermes_thin_client",
    "api": "api_thin_client",
    "main": "main_resident_host",
}
TRANSPORT_TO_ORIGIN = {
    "editor": "extension",
    "hermes": "hermes_agent",
    "api": "api_client",
    "main": "main.py",
}
RESERVED_RUNTIME_KEYS = frozenset(
    {
        "repo_root",
        "red_dog_intent",
        "cycle_store",
        "cancel_requested",
        "retry_requested",
    }
)
class ResidentClientReason:
    REQUEST_INVALID = "REJECT_REDDOG_RESIDENT_CLIENT_REQUEST_INVALID"
    PRINCIPAL_MISMATCH = "REJECT_REDDOG_RESIDENT_CLIENT_PRINCIPAL_MISMATCH"
    SOURCE_MISMATCH = "REJECT_REDDOG_RESIDENT_CLIENT_SOURCE_MISMATCH"
    FOUNDUP_SCOPE_MISMATCH = "REJECT_REDDOG_RESIDENT_CLIENT_FOUNDUP_SCOPE_MISMATCH"
    GROUNDING_REJECTED = "REJECT_REDDOG_RESIDENT_CLIENT_GROUNDING_REJECTED"
    CYCLE_NOT_FOUND = "REJECT_REDDOG_RESIDENT_CLIENT_CYCLE_NOT_FOUND"
    RUNTIME_FAILED = "REJECT_REDDOG_RESIDENT_CLIENT_RUNTIME_FAILED"
    RUNTIME_CONFIGURATION = "REJECT_REDDOG_RESIDENT_CLIENT_RUNTIME_CONFIGURATION"


@dataclass(frozen=True)
class ResidentClientResponse:
    schema_version: str
    response_id: str
    accepted: bool
    operation: str
    transport: str
    intent_id: str
    cycle_id: str
    status: str
    snapshot_id: str
    determination_id: str
    architect_action: str
    architect_next_slice: str
    task_status_counts: Mapping[str, int]
    rejection_reasons: tuple[str, ...]
    record_revision: int = 0
    intent_digest: str = ""
    swarm_id: str = ""
    task_ids: tuple[str, ...] = ()
    openclaw_claim_count: int = 0
    queue_candidate_count: int = 0
    recovered_existing_cycle: bool = False
    duplicate_intent_reused: bool = False
    canonical_resident_cycle_used: bool = True
    read_only_authority_only: bool = True
    client_no_shell_command_executed: bool = True
    client_no_repo_mutation_performed: bool = True
    client_no_holoindex_reindex_performed: bool = True
    client_no_hermes_execution_performed: bool = True
    client_no_worktree_operation_performed: bool = True
    client_no_pr_created: bool = True
    client_no_merge_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["task_status_counts"] = dict(self.task_status_counts)
        payload["rejection_reasons"] = list(self.rejection_reasons)
        return payload


class RedDogResidentArchitectClient:
    """Thin client over the one canonical resident RedDog AgentDB cycle."""

    def __init__(
        self,
        *,
        repo_root: Path | str,
        authenticated_principal_id: str,
        authorized_foundup_ids: Sequence[str],
        transport: str,
        cycle_store: ResidentArchitectCycleStore | None = None,
        cycle_runner: Callable[..., Any] | None = None,
        runtime_defaults: Mapping[str, Any] | None = None,
    ) -> None:
        principal = str(authenticated_principal_id or "").strip()
        surface = TRANSPORT_TO_SOURCE.get(str(transport or "").strip())
        defaults = dict(runtime_defaults or {})
        scope_input_valid = not isinstance(authorized_foundup_ids, (str, bytes))
        foundup_scope = frozenset(
            str(item or "").strip() for item in authorized_foundup_ids if str(item or "").strip()
        ) if scope_input_valid else frozenset()
        if (
            not principal
            or len(principal) > 256
            or any(ord(character) < 32 for character in principal)
            or not foundup_scope
            or surface is None
            or RESERVED_RUNTIME_KEYS.intersection(defaults)
        ):
            raise ValueError(ResidentClientReason.RUNTIME_CONFIGURATION)
        self._repo_root = Path(repo_root).resolve()
        self._principal = principal
        self._authorized_foundup_ids = foundup_scope
        self._transport = str(transport).strip()
        self._source_surface = surface
        self._origin = TRANSPORT_TO_ORIGIN[self._transport]
        self._store = cycle_store or AgentDbResidentArchitectCycleStore()
        if cycle_runner is None:
            from modules.communication.moltbot_bridge.src import (
                reddog_resident_architect_durable_agentdb_cycle as cycle_module,
            )

            cycle_runner = cycle_module.run_reddog_resident_architect_durable_agentdb_cycle
        self._runner = cycle_runner
        self._runtime_defaults = defaults

    def submit(self, intent: Mapping[str, Any] | None) -> ResidentClientResponse:
        reasons = self._validate_submitted_intent(intent)
        if reasons:
            return self._reject("submit", _intent_id(intent), reasons)
        assert isinstance(intent, Mapping)
        return self._invoke("submit", dict(intent), cancel=False, retry=False)

    def status(self, intent_id: str) -> ResidentClientResponse:
        record, reasons = self._authorized_record(intent_id)
        legacy_main = False
        if reasons:
            record, legacy_reasons = authorize_legacy_main_record(
                self._store,
                intent_id,
                authenticated_principal_id=self._principal,
                authorized_foundup_ids=self._authorized_foundup_ids,
                transport=self._transport,
            )
            if legacy_reasons:
                return self._reject("status", str(intent_id or ""), reasons)
            legacy_main = True
        assert record is not None
        return self._from_record(
            "status",
            record,
            accepted=True,
            canonical_cycle_used=not legacy_main,
        )

    def cancel(self, intent_id: str) -> ResidentClientResponse:
        record, reasons = self._authorized_record(intent_id)
        legacy_cancel = False
        if reasons:
            record, legacy_main_reasons = authorize_legacy_main_record(
                self._store,
                intent_id,
                authenticated_principal_id=self._principal,
                authorized_foundup_ids=self._authorized_foundup_ids,
                transport=self._transport,
            )
            if not legacy_main_reasons:
                assert record is not None
                updated, cancel_reasons = cancel_legacy_main_record(
                    self._store,
                    record,
                    authorized_intent_id=str(intent_id or "").strip(),
                )
                if cancel_reasons or updated is None:
                    return self._reject(
                        "cancel",
                        str(intent_id or ""),
                        cancel_reasons or (ResidentClientReason.RUNTIME_FAILED,),
                    )
                return self._from_record(
                    "cancel",
                    updated,
                    accepted=False,
                    canonical_cycle_used=False,
                )
            record, legacy_reasons = self._authorized_legacy_cancel_record(intent_id)
            if legacy_reasons:
                return self._reject("cancel", str(intent_id or ""), reasons)
            legacy_cancel = True
        assert record is not None
        return self._invoke(
            "cancel",
            _record_intent(record),
            cancel=True,
            retry=False,
            legacy_cancel=legacy_cancel,
        )

    def resume(self, intent_id: str) -> ResidentClientResponse:
        record, reasons = self._authorized_record(intent_id)
        if reasons:
            return self._reject("resume", str(intent_id or ""), reasons)
        assert record is not None
        retry = str(record.get("status") or "") in {STATUS_FAILED, STATUS_TIMED_OUT}
        return self._invoke("resume", _record_intent(record), cancel=False, retry=retry)

    def _validate_submitted_intent(self, intent: Mapping[str, Any] | None) -> tuple[str, ...]:
        if not isinstance(intent, Mapping) or intent.get("schema_version") != "reddog_intent.v2":
            return (ResidentClientReason.REQUEST_INVALID,)
        reasons: list[str] = []
        if not _intent_id(intent) or not str(intent.get("foundup_id") or "").strip():
            reasons.append(ResidentClientReason.REQUEST_INVALID)
        if _principal_id(intent) != self._principal:
            reasons.append(ResidentClientReason.PRINCIPAL_MISMATCH)
        if str(intent.get("source_surface") or "") != self._source_surface:
            reasons.append(ResidentClientReason.SOURCE_MISMATCH)
        if str(intent.get("origin") or "") != self._origin:
            reasons.append(ResidentClientReason.SOURCE_MISMATCH)
        if str(intent.get("foundup_id") or "").strip() not in self._authorized_foundup_ids:
            reasons.append(ResidentClientReason.FOUNDUP_SCOPE_MISMATCH)
        if intent.get("submits_executable_authority") is not False:
            reasons.append(ResidentClientReason.REQUEST_INVALID)
        grounding = validate_grounded_target_receipt(
            intent.get("grounding_receipt") if isinstance(intent.get("grounding_receipt"), Mapping) else None,
            work_focus=str(intent.get("work_focus") or ""),
            expected_source_surface=self._source_surface,
        )
        if not grounding.accepted:
            reasons.append(ResidentClientReason.GROUNDING_REJECTED)
        return tuple(dict.fromkeys(reasons))

    def _authorized_record(self, intent_id: str) -> tuple[Optional[Mapping[str, Any]], tuple[str, ...]]:
        value = str(intent_id or "").strip()
        if not value:
            return None, (ResidentClientReason.REQUEST_INVALID,)
        record = self._store.load_cycle_by_intent(value)
        if not isinstance(record, Mapping):
            return None, (ResidentClientReason.CYCLE_NOT_FOUND,)
        intent = _record_intent(record)
        reasons = self._validate_submitted_intent(intent)
        if _intent_id(intent) != value:
            reasons = (*reasons, ResidentClientReason.REQUEST_INVALID)
        if str(record.get("intent_digest") or "") != resident_intent_digest(intent):
            reasons = (*reasons, ResidentClientReason.REQUEST_INVALID)
        if record.get("_store_integrity_valid") is not True:
            reasons = (*reasons, ResidentClientReason.RUNTIME_FAILED)
        if not _runtime_boundary_is_safe(record):
            reasons = (*reasons, ResidentClientReason.RUNTIME_FAILED)
        reasons = tuple(dict.fromkeys(reasons))
        return (None, reasons) if reasons else (record, ())

    def _authorized_legacy_cancel_record(
        self,
        intent_id: str,
    ) -> tuple[Optional[Mapping[str, Any]], tuple[str, ...]]:
        value = str(intent_id or "").strip()
        record = self._store.load_cycle_by_intent(value) if value else None
        if not isinstance(record, Mapping):
            return None, (ResidentClientReason.CYCLE_NOT_FOUND,)
        intent = _record_intent(record)
        reasons = list(self._validate_submitted_intent(intent))
        if (
            record.get("schema_version") != "reddog_resident_architect_cycle.v1"
            or str(record.get("intent_digest") or "")
            or _intent_id(intent) != value
            or (
                str(record.get("status") or "") != STATUS_CANCELLED
                and "record_revision" in record
            )
        ):
            reasons.append(ResidentClientReason.RUNTIME_FAILED)
        reasons = list(dict.fromkeys(reasons))
        return (None, tuple(reasons)) if reasons else (record, ())

    def _invoke(
        self,
        operation: str,
        intent: Mapping[str, Any],
        *,
        cancel: bool,
        retry: bool,
        legacy_cancel: bool = False,
    ) -> ResidentClientResponse:
        try:
            result = self._runner(
                repo_root=self._repo_root,
                red_dog_intent=dict(intent),
                cycle_store=self._store,
                cancel_requested=cancel,
                retry_requested=retry,
                **self._runtime_defaults,
            )
        except Exception:
            return self._reject(operation, _intent_id(intent), (ResidentClientReason.RUNTIME_FAILED,))
        if hasattr(result, "to_dict"):
            data = result.to_dict()
        elif isinstance(result, Mapping):
            data = dict(result)
        else:
            data = dict(vars(result))
        legacy_cancelled = bool(
            legacy_cancel
            and str(data.get("status") or "") == STATUS_CANCELLED
            and ResidentCycleReason.CANCELLED in tuple(data.get("rejection_reasons") or ())
        )
        runtime_boundary_failed = not _runtime_boundary_is_safe(data) and not legacy_cancelled
        if runtime_boundary_failed:
            data = dict(data)
            data["rejection_reasons"] = [
                *tuple(data.get("rejection_reasons") or ()),
                ResidentClientReason.RUNTIME_FAILED,
            ]
        return self._from_record(
            operation,
            data,
            accepted=bool(data.get("accepted")) and not runtime_boundary_failed,
            canonical_cycle_used=not legacy_cancel,
        )

    def _from_record(
        self,
        operation: str,
        record: Mapping[str, Any],
        *,
        accepted: bool,
        canonical_cycle_used: bool,
    ) -> ResidentClientResponse:
        payload = {
            "operation": operation,
            "transport": self._transport,
            "intent_id": str(record.get("intent_id") or ""),
            "cycle_id": str(record.get("cycle_id") or ""),
            "status": str(record.get("status") or ""),
            "snapshot_id": str(record.get("snapshot_id") or ""),
            "determination_id": str(
                record.get("architect_determination_id") or record.get("determination_id") or ""
            ),
            "architect_action": str(record.get("architect_action") or ""),
            "architect_next_slice": str(record.get("architect_next_slice") or ""),
            "task_status_counts": dict(record.get("task_status_counts") or {}),
            "record_revision": int(record.get("record_revision") or 0),
            "intent_digest": str(record.get("intent_digest") or ""),
            "swarm_id": str(record.get("swarm_id") or ""),
            "task_ids": tuple(str(item) for item in record.get("task_ids", ()) if str(item)),
            "openclaw_claim_count": len(record.get("openclaw_claims") or ()),
            "queue_candidate_count": int(record.get("queue_candidate_count") or 0),
            "recovered_existing_cycle": bool(record.get("recovered_existing_cycle")),
            "duplicate_intent_reused": bool(record.get("duplicate_intent_reused")),
            "rejection_reasons": tuple(str(item) for item in record.get("rejection_reasons", ()) if str(item)),
        }
        response_id = _digest(
            {
                "schema_version": CLIENT_RESPONSE_SCHEMA,
                "accepted": accepted,
                "canonical_resident_cycle_used": canonical_cycle_used,
                "read_only_authority_only": True,
                "client_no_shell_command_executed": True,
                "client_no_repo_mutation_performed": True,
                "client_no_holoindex_reindex_performed": True,
                "client_no_hermes_execution_performed": True,
                "client_no_worktree_operation_performed": True,
                "client_no_pr_created": True,
                "client_no_merge_performed": True,
                **payload,
            }
        )
        return ResidentClientResponse(
            schema_version=CLIENT_RESPONSE_SCHEMA,
            response_id=response_id,
            accepted=accepted,
            canonical_resident_cycle_used=canonical_cycle_used,
            **payload,
        )

    def _reject(
        self,
        operation: str,
        intent_id: str,
        reasons: tuple[str, ...],
    ) -> ResidentClientResponse:
        return self._from_record(
            operation,
            {
                "intent_id": intent_id,
                "status": "REJECTED",
                "rejection_reasons": reasons,
            },
            accepted=False,
            canonical_cycle_used=False,
        )


def _record_intent(record: Mapping[str, Any]) -> Mapping[str, Any]:
    intent = record.get("intent")
    return dict(intent) if isinstance(intent, Mapping) else {}


def _intent_id(intent: Mapping[str, Any] | None) -> str:
    return str(intent.get("intent_id") or "") if isinstance(intent, Mapping) else ""


def _principal_id(intent: Mapping[str, Any]) -> str:
    return str(
        intent.get("principal_id")
        or intent.get("principal_ref")
        or intent.get("origin_principal")
        or ""
    ).strip()


def _runtime_boundary_is_safe(record: Mapping[str, Any]) -> bool:
    return all(record.get(key) is True for key in RUNTIME_BOUNDARY_FIELDS)


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
    "CLIENT_RESPONSE_SCHEMA",
    "RedDogResidentArchitectClient",
    "ResidentClientReason",
    "ResidentClientResponse",
    "RUNTIME_BOUNDARY_FIELDS",
    "TRANSPORT_TO_SOURCE",
]
