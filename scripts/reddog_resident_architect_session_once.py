"""One-shot bridge for RedDog thin client -> durable resident architect cycle.

Slice: REDDOG_EXTENSION_TO_RESIDENT_ARCHITECT_SESSION_RUNTIME_PHASE1

The editor runtime may call this script only when the resident architect
session is explicitly enabled. It delegates through the canonical
host-authenticated resident client to the durable AgentDB cycle and returns a
bounded status packet. It does not perform source
mutation, shell work, worktree creation, PR creation, HoloIndex re-index,
Hermes dispatch, live FoundUp enqueue, or direct inline task execution.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.communication.moltbot_bridge.src.reddog_resident_architect_client import (  # noqa: E402
    RedDogResidentArchitectClient,
)
from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (  # noqa: E402
    validate_grounded_target_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_resident_model_runtime_bindings import (  # noqa: E402
    load_resident_model_runtime_bindings,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_runtime_authority import (  # noqa: E402
    CommittedAuthorityProfileOutcomeKeyResolver,
    VerifiedOutcomeRuntimeAuthority,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_runtime_store import (  # noqa: E402
    AuthorityRuntimeVerifiedOutcomeStore,
)
from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_runtime_dependency_bundle import (  # noqa: E402
    load_reddog_main_resident_queue_runtime_dependency_bundle,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_session_authority_source import (  # noqa: E402
    ConversationSessionAuthoritySourceError,
    VerifiedResidentConversationSession,
    lease_current_generation_conversation_session,
    owner_config_from_environment,
)
from modules.communication.moltbot_bridge.src.reddog_principal_memex_live_resident_source_supply import (  # noqa: E402
    DeferredPrincipalMemexResidentSource,
    PrincipalMemexLiveResidentSourceSupply,
    defer_principal_memex_live_resident_source,
    discard_principal_memex_live_resident_source,
    parse_principal_memex_live_resident_source_supply,
    principal_memex_live_resident_source_pending,
    principal_memex_session_runtime_root,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (  # noqa: E402
    read_reddog_runtime_json_mapping,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (  # noqa: E402
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)

RESIDENT_ARCHITECT_SESSION_ACCEPT = "RESIDENT_ARCHITECT_SESSION_ACCEPT"
RESIDENT_ARCHITECT_SESSION_REJECT = "RESIDENT_ARCHITECT_SESSION_REJECT"


class _ResidentSessionRequest:
    __slots__ = (
        "payload", "intent", "serialized_credential", "principal_memex_supply",
        "work_focus", "grounding_receipt_id", "repo_root", "audit_binding",
        "architect_binding",
    )

    def __init__(
        self, payload: Mapping[str, Any], intent: Mapping[str, Any],
        serialized_credential: str,
        principal_memex_supply: PrincipalMemexLiveResidentSourceSupply | None,
        work_focus: str, grounding_receipt_id: str, repo_root: Path,
        audit_binding: Mapping[str, Any], architect_binding: Mapping[str, Any],
    ) -> None:
        self.payload = payload
        self.intent = intent
        self.serialized_credential = serialized_credential
        self.principal_memex_supply = principal_memex_supply
        self.work_focus = work_focus
        self.grounding_receipt_id = grounding_receipt_id
        self.repo_root = repo_root
        self.audit_binding = audit_binding
        self.architect_binding = architect_binding

    def __repr__(self) -> str:
        return "_ResidentSessionRequest(<redacted>)"


def _read_payload() -> Dict[str, Any]:
    try:
        raw = sys.stdin.buffer.read()
        payload = json.loads(raw.decode("utf-8") if raw else "{}")
    except Exception as exc:
        return {"_bridge_error": "invalid_json", "_bridge_error_class": type(exc).__name__}
    return payload if isinstance(payload, dict) else {"_bridge_error": "payload_not_object"}


def _string(value: Any) -> str:
    return str(value) if value is not None else ""


def _int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _reject(reason: str, *, bridge_error_class: str | None = None) -> Dict[str, Any]:
    output: Dict[str, Any] = {
        "decision": RESIDENT_ARCHITECT_SESSION_REJECT,
        "accepted": False,
        "status": "REJECT",
        "resident_backend_invoked": False,
        "python_invocation_performed": True,
        "snapshot_id": "",
        "swarm_id": "",
        "task_count": 0,
        "reports_persisted": 0,
        "architect_action": "",
        "architect_next_slice": "",
        "architect_determination_id": "",
        "queue_candidate_count": 0,
        "rejection_reasons": [reason],
        "no_shell_command_executed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_worktree_operation_performed": True,
        "no_pr_created": True,
        "no_pattern_memory_promotion_performed": True,
        "no_live_foundup_enqueue_performed": True,
        "coding_worker_spawned": False,
    }
    if bridge_error_class:
        output["bridge_error_class"] = bridge_error_class
    return output


class _ConfiguredExternalResearchRetriever:
    """File-backed approved external research snapshot retriever.

    The resident bridge requires a configured retriever. A JSON snapshot file
    path is supplied through REDDOG_EXTERNAL_RESEARCH_SNAPSHOT_PATH. The file is
    treated as untrusted data by downstream grounding; this bridge only returns
    it to the governed adapter.
    """

    def __init__(self, snapshot_path: Path) -> None:
        self.snapshot_path = snapshot_path

    def fetch(self, target: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if isinstance(payload, dict) and isinstance(payload.get("snapshots"), list):
            url = str(target.get("url") or target.get("target") or "")
            for item in payload["snapshots"]:
                if isinstance(item, dict) and str(item.get("source_url") or item.get("url") or "") == url:
                    return item
        return payload if isinstance(payload, dict) else {}


def _external_retriever_from_env() -> Any | None:
    raw_path = os.getenv("REDDOG_EXTERNAL_RESEARCH_SNAPSHOT_PATH", "").strip()
    if not raw_path:
        return None
    path = Path(raw_path)
    return _ConfiguredExternalResearchRetriever(path) if path.is_file() else None


def _mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _sequence_of_mappings(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _summarize_result(
    result: Any, *, principal_memex_source_consumed: bool = False,
) -> Dict[str, Any]:
    task_ids = tuple(str(item) for item in result.task_ids if str(item))
    completed = int(result.task_status_counts.get("completed", 0))
    return {
        "decision": RESIDENT_ARCHITECT_SESSION_ACCEPT if result.accepted else RESIDENT_ARCHITECT_SESSION_REJECT,
        "accepted": bool(result.accepted),
        "status": str(result.status),
        "resident_backend_invoked": True,
        "red_dog_intent_submitted": True,
        "durable_agentdb_cycle": True,
        "canonical_resident_client_used": bool(result.canonical_resident_cycle_used),
        "python_invocation_performed": True,
        "snapshot_id": _string(result.snapshot_id),
        "final_snapshot_id": _string(result.snapshot_id),
        "swarm_id": _string(result.swarm_id),
        "cycle_id": _string(result.cycle_id),
        "intent_id": _string(result.intent_id),
        "initial_status": _string(result.status),
        "final_status": _string(result.status),
        "task_count": len(task_ids),
        "task_status_counts": dict(result.task_status_counts),
        "reports_persisted": completed,
        "readonly_audit_tasks_enqueued": bool(task_ids),
        "readonly_audit_tasks_executed": completed == len(task_ids) and bool(task_ids),
        "openclaw_claim_count": int(result.openclaw_claim_count),
        "recovered_existing_cycle": bool(result.recovered_existing_cycle),
        "duplicate_intent_reused": bool(result.duplicate_intent_reused),
        "principal_memex_source_consumed": bool(principal_memex_source_consumed),
        "architect_action": _string(result.architect_action),
        "architect_next_slice": _string(result.architect_next_slice),
        "architect_determination_id": _string(result.determination_id),
        "queue_candidate_count": int(result.queue_candidate_count),
        "record_revision": int(result.record_revision),
        "intent_digest": _string(result.intent_digest),
        "rejection_reasons": list(result.rejection_reasons),
        "no_shell_command_executed": bool(result.client_no_shell_command_executed),
        "no_repo_mutation_performed": bool(result.client_no_repo_mutation_performed),
        "no_holoindex_reindex_performed": bool(result.client_no_holoindex_reindex_performed),
        "no_hermes_dispatch_performed": bool(result.client_no_hermes_execution_performed),
        "no_worktree_operation_performed": bool(result.client_no_worktree_operation_performed),
        "no_pr_created": bool(result.client_no_pr_created),
        "no_pattern_memory_promotion_performed": True,
        "no_live_foundup_enqueue_performed": True,
        "coding_worker_spawned": False,
    }


def _result(payload: Mapping[str, Any]) -> Dict[str, Any]:
    request, rejection = _validated_session_request(payload)
    if request is None:
        return rejection or _reject("resident_architect_session_request_invalid")
    now_epoch = int(time.time())
    try:
        owner_config_path = owner_config_from_environment(os.environ)
        with lease_current_generation_conversation_session(
            repo_root=request.repo_root,
            intent=request.intent,
            grounding_receipt_id=request.grounding_receipt_id,
            serialized_credential=request.serialized_credential,
            owner_config_path=owner_config_path,
            now_epoch=now_epoch,
            include_principal_scope_capability=(
                request.principal_memex_supply is not None
            ),
        ) as verified_session:
            result, principal_memex_source_consumed = _submit_authenticated_session(
                payload=request.payload, intent=request.intent,
                work_focus=request.work_focus, repo_root=request.repo_root,
                verified_session=verified_session,
                audit_binding=request.audit_binding,
                architect_binding=request.architect_binding,
                principal_memex_supply=request.principal_memex_supply,
                now_epoch=now_epoch,
            )
    except ConversationSessionAuthoritySourceError as exc:
        return _reject(exc.reason)
    except Exception as exc:
        output = _reject(
            "resident_architect_session_bridge_failed",
            bridge_error_class=type(exc).__name__,
        )
        output["resident_backend_invoked"] = True
        return output
    return _summarize_result(
        result,
        principal_memex_source_consumed=principal_memex_source_consumed,
    )


def _validated_session_request(
    payload_input: Mapping[str, Any],
) -> tuple[_ResidentSessionRequest | None, Dict[str, Any] | None]:
    payload = dict(payload_input)
    if payload.get("_bridge_error"):
        return None, _reject(
            str(payload["_bridge_error"]),
            bridge_error_class=str(payload.get("_bridge_error_class") or "Error"),
        )
    if payload.get("explicit_resident_architect_session_requested") is not True:
        return None, _reject("explicit_resident_architect_session_request_missing")
    intent = payload.get("red_dog_intent")
    if not isinstance(intent, dict) or intent.get("schema_version") != "reddog_intent.v2":
        return None, _reject("reddog_intent_missing_or_invalid")
    if intent.get("submits_executable_authority") is not False:
        return None, _reject("reddog_intent_must_not_submit_executable_authority")
    serialized_credential = _string(
        payload.pop("conversation_session_credential", "")
    )
    if not serialized_credential:
        return None, _reject("conversation_session_authority_source_missing")
    principal_memex_supply, supply_reasons = _principal_memex_supply(payload)
    if supply_reasons:
        return None, _reject(supply_reasons[0])
    work_focus = _string(payload.get("work_focus") or intent.get("work_focus"))
    grounding = validate_grounded_target_receipt(
        intent.get("grounding_receipt") if isinstance(intent.get("grounding_receipt"), Mapping) else None,
        work_focus=work_focus,
        expected_source_surface="editor_thin_client",
    )
    if not grounding.accepted:
        return None, _reject(
            (grounding.rejection_reasons or ("grounding_receipt_rejected",))[0]
        )
    if payload.get("grounding_receipt_id") != grounding.verified.receipt_id:
        return None, _reject("grounding_receipt_id_mismatch")

    repo_root_text = payload.get("repo_root")
    repo_root = Path(str(repo_root_text)).resolve() if repo_root_text else REPO_ROOT
    audit_binding, architect_binding, rejection = _runtime_bindings(repo_root)
    if rejection is not None:
        return None, rejection
    assert audit_binding is not None and architect_binding is not None
    return _ResidentSessionRequest(
        payload, intent, serialized_credential, principal_memex_supply,
        work_focus, str(grounding.verified.receipt_id), repo_root,
        audit_binding, architect_binding,
    ), None


def _principal_memex_supply(
    payload: dict[str, Any],
) -> tuple[PrincipalMemexLiveResidentSourceSupply | None, tuple[str, ...]]:
    return parse_principal_memex_live_resident_source_supply(
        payload.pop("principal_memex_source_supply", None)
    )


def _runtime_bindings(
    repo_root: Path,
) -> tuple[Mapping[str, Any] | None, Mapping[str, Any] | None, Dict[str, Any] | None]:
    try:
        audit, architect, reason = load_resident_model_runtime_bindings(repo_root)
    except Exception:
        return None, None, _reject("model_runtime_binding_artifact_invalid")
    if reason or audit is None or architect is None:
        return None, None, _reject(
            reason or "model_runtime_binding_artifact_invalid"
        )
    return audit, architect, None


def _submit_authenticated_session(
    *, payload: Mapping[str, Any], intent: Mapping[str, Any], work_focus: str,
    repo_root: Path, verified_session: VerifiedResidentConversationSession,
    audit_binding: Mapping[str, Any], architect_binding: Mapping[str, Any],
    principal_memex_supply: PrincipalMemexLiveResidentSourceSupply | None,
    now_epoch: int,
) -> tuple[Any, bool]:
    memex_config = _mapping(payload.get("memex_snapshot_supply")) or {}
    verified_outcome_authority = _verified_outcome_authority_from_env(
        repo_root, memex_config
    )
    principal_memex_source = _defer_principal_memex_source(
        repo_root=repo_root,
        verified_session=verified_session,
        principal_memex_supply=principal_memex_supply,
        architect_binding=architect_binding,
        now_epoch=now_epoch,
    )
    client = RedDogResidentArchitectClient(
        repo_root=repo_root,
        authenticated_principal_id=verified_session.principal_id,
        authorized_foundup_ids=verified_session.foundup_scope,
        transport="editor",
        runtime_defaults=_runtime_defaults(
            payload, work_focus, memex_config, verified_outcome_authority,
            audit_binding, architect_binding,
            principal_memex_source,
        ),
    )
    bound_intent = dict(intent)
    bound_intent["conversation_session_authority_receipt"] = dict(
        verified_session.authority_receipt
    )
    try:
        result = client.submit(bound_intent)
        consumed = bool(
            principal_memex_source is not None
            and not principal_memex_live_resident_source_pending(principal_memex_source)
        )
        return result, consumed
    finally:
        discard_principal_memex_live_resident_source(principal_memex_source)


def _runtime_defaults(
    payload: Mapping[str, Any], work_focus: str,
    memex_config: Mapping[str, Any], verified_outcome_authority: Any,
    audit_binding: Mapping[str, Any], architect_binding: Mapping[str, Any],
    principal_memex_source: Any = None,
) -> dict[str, Any]:
    defaults = {
        "work_state_path": _string(payload.get("work_state_path") or os.getenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", "")),
        "holoindex_receipt_path": _string(payload.get("holoindex_receipt_path") or os.getenv("HOLOINDEX_FRESHNESS_RECEIPT", "")),
        "holoindex_ssd_path": _string(payload.get("holoindex_ssd_path") or os.getenv("HOLOINDEX_SSD_PATH", "")),
        "requested_operation": "extension_resident_architect_session",
        "prompt_text": work_focus,
        "breadcrumbs": _sequence_of_mappings(payload.get("breadcrumbs")),
        "brain_state": _mapping(payload.get("brain_state")),
        "workspace_memory_notes": _sequence_of_mappings(payload.get("workspace_memory_notes")),
        "memex_snapshot_supply_config": memex_config,
        "verified_outcome_runtime_authority": verified_outcome_authority,
        "external_research_retriever": _external_retriever_from_env(),
        "timeout_seconds": _int(payload.get("timeout_seconds"), 60),
        "audit_model_runtime_binding_receipt": audit_binding,
        "architect_model_runtime_binding_receipt": architect_binding,
    }
    if principal_memex_source is not None:
        defaults["principal_memex_source"] = principal_memex_source
    return defaults


def _defer_principal_memex_source(
    *, repo_root: Path, verified_session: VerifiedResidentConversationSession,
    principal_memex_supply: PrincipalMemexLiveResidentSourceSupply | None,
    architect_binding: Mapping[str, Any], now_epoch: int,
) -> DeferredPrincipalMemexResidentSource | None:
    if principal_memex_supply is None:
        return None
    if (
        verified_session.principal_memex_authorization is None
    ):
        raise ConversationSessionAuthoritySourceError(
            "principal_memex_session_scope_unavailable"
        )
    expected_runtime_root = principal_memex_session_runtime_root(
        verified_session.principal_memex_authorization
    )
    if expected_runtime_root is None:
        raise ConversationSessionAuthoritySourceError(
            "principal_memex_session_scope_unavailable"
        )
    authority_store = _principal_memex_authority_store_from_env(
        repo_root, expected_runtime_root=expected_runtime_root,
        now_epoch=now_epoch,
    )
    source = defer_principal_memex_live_resident_source(
        supply=principal_memex_supply,
        authorization=verified_session.principal_memex_authorization,
        authority_store=authority_store,
        model_runtime_binding_receipt=architect_binding,
        now_epoch=lambda: int(time.time()),
    )
    if source is None:
        raise ConversationSessionAuthoritySourceError(
            "principal_memex_source_rejected"
        )
    return source


def _principal_memex_authority_store_from_env(
    repo_root: Path, *, expected_runtime_root: Path, now_epoch: int,
) -> Any:
    runtime_root_value = os.getenv("REDDOG_RUNTIME_ARTIFACT_ROOT", "").strip()
    authority_state_value = os.getenv(
        "REDDOG_AUTHORITY_RUNTIME_STATE_PATH", ""
    ).strip()
    if not runtime_root_value or not authority_state_value:
        raise ConversationSessionAuthoritySourceError(
            "principal_memex_authority_store_config_missing"
        )
    runtime_root = validate_runtime_root_path(runtime_root_value, repo_root=repo_root)
    if runtime_root != expected_runtime_root.resolve():
        raise ConversationSessionAuthoritySourceError(
            "principal_memex_authority_generation_mismatch"
        )
    authority_path = validate_runtime_artifact_path(
        authority_state_value, repo_root=repo_root, allowed_root=runtime_root
    )
    if authority_path != runtime_root / "authority_runtime_state.json":
        raise ConversationSessionAuthoritySourceError(
            "principal_memex_authority_state_path_not_canonical"
        )
    bundle = load_reddog_main_resident_queue_runtime_dependency_bundle(
        repo_root=repo_root,
        runtime_allowed_root=runtime_root,
        authority_state_path=authority_path,
        signature_verifier_backend="ed25519",
        now_epoch=int(now_epoch),
    )
    if not bundle.accepted or bundle.authority_store is None:
        raise ConversationSessionAuthoritySourceError(
            "principal_memex_authority_store_unavailable"
        )
    return bundle.authority_store


def _verified_outcome_authority_from_env(
    repo_root: Path,
    memex_config: Mapping[str, Any],
) -> VerifiedOutcomeRuntimeAuthority | None:
    if not memex_config.get("verified_outcome_references"):
        return None
    runtime_root_value = os.getenv("REDDOG_RUNTIME_ARTIFACT_ROOT", "").strip()
    authority_state_value = os.getenv(
        "REDDOG_AUTHORITY_RUNTIME_STATE_PATH", ""
    ).strip()
    work_state_value = os.getenv(
        "REDDOG_AUTHORITATIVE_WORK_STATE_PATH", ""
    ).strip()
    profile_value = os.getenv("REDDOG_AUTHORITY_PROFILE_PATH", "").strip()
    if not all(
        (runtime_root_value, authority_state_value, work_state_value, profile_value)
    ):
        raise ValueError("verified_outcome_runtime_authority_config_missing")
    runtime_root = validate_runtime_root_path(
        runtime_root_value,
        repo_root=repo_root,
    )
    now_epoch = int(time.time())
    bundle = load_reddog_main_resident_queue_runtime_dependency_bundle(
        repo_root=repo_root,
        runtime_allowed_root=runtime_root,
        authority_state_path=authority_state_value,
        signature_verifier_backend="ed25519",
        now_epoch=now_epoch,
    )
    if not bundle.accepted or bundle.authority_store is None:
        raise ValueError("verified_outcome_runtime_dependency_bundle_rejected")
    work_state = _runtime_mapping(
        repo_root, runtime_root, work_state_value
    )
    profile = _runtime_mapping(repo_root, runtime_root, profile_value)
    return VerifiedOutcomeRuntimeAuthority(
        store=AuthorityRuntimeVerifiedOutcomeStore(bundle.authority_store),
        outcome_signer_key_resolver=CommittedAuthorityProfileOutcomeKeyResolver(
            work_state_snapshot=work_state,
            authority_profile=profile,
        ),
        signature_verifier=bundle.signature_verifier,
        revocation_oracle=bundle.revocation_oracle,
        issuer_principal_id=str(profile.get("principal_id") or ""),
        issuer_principal_provider=str(profile.get("principal_provider") or ""),
        reddog_id=str(profile.get("reddog_id") or ""),
        trusted_now_epoch=lambda: int(time.time()),
    )


def _runtime_mapping(
    repo_root: Path,
    runtime_root: Path,
    path_value: str,
) -> Mapping[str, Any]:
    path = validate_runtime_artifact_path(
        path_value,
        repo_root=repo_root,
        allowed_root=runtime_root,
    )
    return read_reddog_runtime_json_mapping(path, allowed_root=runtime_root)


def main() -> int:
    try:
        output = _result(_read_payload())
    except Exception as exc:
        output = _reject("resident_architect_session_bridge_failed", bridge_error_class=type(exc).__name__)
        output["resident_backend_invoked"] = True
    sys.stdout.write(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
