"""Authority, profile, budget, and grounding bindings for start operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_operations_skill import (
    RedDogOperationsSkill, load_reddog_operations_skill, skill_receipt_dict,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_control_authority import (
    StartOperationsRejected, budgets, load_bindings, runtime_defaults,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_profile import (
    StartOperationsProfile,
    start_operations_profile,
)

CONTROL_SCHEMA = "reddog_start_operations_control.v1"
CONTROL_REQUEST_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

@dataclass(frozen=True)
class PreparedSubmission:
    intent: Mapping[str, Any]
    runtime_defaults: Mapping[str, Any]

def validated_request(
    request: Mapping[str, Any], allowed_actions: frozenset[str]
) -> tuple[str, StartOperationsProfile, str, str]:
    if request.get("schema_version") != CONTROL_SCHEMA:
        raise StartOperationsRejected(("start_operations_control_schema_invalid",))
    action = str(request.get("action") or "").strip()
    if action not in allowed_actions:
        raise StartOperationsRejected(("start_operations_control_action_invalid",))
    try:
        profile = start_operations_profile(
            str(request.get("operations_profile_id") or "")
        )
    except ValueError as exc:
        raise StartOperationsRejected(("start_operations_profile_invalid",)) from exc
    intent_id = str(request.get("intent_id") or "").strip()
    if action != "submit" and not intent_id.startswith("sha256:"):
        raise StartOperationsRejected(("start_operations_control_intent_id_invalid",))
    control_request_id = str(request.get("control_request_id") or "").strip()
    if not CONTROL_REQUEST_ID_RE.fullmatch(control_request_id):
        raise StartOperationsRejected(("start_operations_control_request_id_invalid",))
    return action, profile, intent_id, control_request_id

def prepare_submission(
    *,
    repo_root: Path, profile: StartOperationsProfile,
    scope: tuple[str, tuple[str, ...], str], repo_state: Mapping[str, Any],
    env: Mapping[str, str], operations_skill_root: Path,
    operations_skill_reader: Callable[[Path], str] | None,
    grounding_runner: Callable[..., Any],
) -> PreparedSubmission:
    operations_skill = _operations_skill(
        operations_skill_root, operations_skill_reader
    )
    audit, architect = load_bindings(repo_root, env)
    max_claims, timeout = budgets(profile, env)
    request_id = _client_request_id(
        profile, scope, repo_state, audit, architect, operations_skill,
        max_claims, timeout
    )
    grounding = grounding_runner(
        repo_root=repo_root,
        work_focus=profile.work_focus,
        foundup_id=scope[2],
        authenticated_principal_id=scope[0],
        source_surface="editor_thin_client",
        client_request_id=request_id,
    )
    if not grounding.accepted:
        raise StartOperationsRejected(grounding.rejection_reasons)
    intent = bound_intent(
        grounding.intent,
        profile=profile,
        repo_state=repo_state,
        audit=audit,
        architect=architect,
        operations_skill=operations_skill,
        max_claims=max_claims,
        timeout_seconds=timeout,
    )
    return PreparedSubmission(
        intent=intent,
        runtime_defaults=runtime_defaults(
            env,
            audit,
            architect,
            max_claims,
            timeout,
            profile,
            prompt_text=operations_skill.prompt_for(profile.work_focus),
            operations_skill_receipt=skill_receipt_dict(operations_skill),
        ),
    )

def runtime_defaults_for_resume(
    repo_root: Path, operations_skill_root: Path,
    operations_skill_reader: Callable[[Path], str] | None,
    profile: StartOperationsProfile,
    env: Mapping[str, str],
) -> Mapping[str, Any]:
    operations_skill = _operations_skill(
        operations_skill_root, operations_skill_reader
    )
    audit, architect = load_bindings(repo_root, env)
    max_claims, timeout = budgets(profile, env)
    return runtime_defaults(
        env,
        audit,
        architect,
        max_claims,
        timeout,
        profile,
        prompt_text=operations_skill.prompt_for(profile.work_focus),
        operations_skill_receipt=skill_receipt_dict(operations_skill),
    )

def _client_request_id(
    profile: StartOperationsProfile,
    scope: tuple[str, tuple[str, ...], str],
    repo_state: Mapping[str, Any],
    audit: Mapping[str, Any],
    architect: Mapping[str, Any],
    operations_skill: RedDogOperationsSkill,
    max_claims: int,
    timeout_seconds: int,
) -> str:
    return canonical_digest(
        {
            "profile_id": profile.profile_id,
            "repo_head_sha": repo_state.get("head_sha"),
            "principal_id": scope[0],
            "foundup_id": scope[2],
            "audit_binding_digest": canonical_digest(audit),
            "architect_binding_digest": canonical_digest(architect),
            "operations_skill_receipt_id": operations_skill.receipt["receipt_id"],
            "max_claims": max_claims,
            "timeout_seconds": timeout_seconds,
        }
    )

def bound_intent(
    intent: Mapping[str, Any],
    *,
    profile: StartOperationsProfile,
    repo_state: Mapping[str, Any],
    audit: Mapping[str, Any],
    architect: Mapping[str, Any],
    operations_skill: RedDogOperationsSkill,
    max_claims: int,
    timeout_seconds: int,
) -> Mapping[str, Any]:
    value = {
        **dict(intent),
        "operations_profile_id": profile.profile_id,
        "operations_profile_schema": profile.schema_version,
        "repo_head_sha": str(repo_state.get("head_sha") or ""),
        "audit_model_runtime_binding_receipt_id": str(audit.get("receipt_id") or ""),
        "audit_model_runtime_binding_digest": canonical_digest(audit),
        "architect_model_runtime_binding_receipt_id": str(
            architect.get("receipt_id") or ""
        ),
        "architect_model_runtime_binding_digest": canonical_digest(architect),
        "operations_skill_receipt": skill_receipt_dict(operations_skill),
        "operations_skill_receipt_id": operations_skill.receipt["receipt_id"],
        "operations_skill_content_digest": operations_skill.receipt["content_digest"],
        "operations_skill_registry_entry_digest": operations_skill.receipt[
            "registry_entry_digest"
        ],
        "max_claims": max_claims,
        "timeout_seconds": timeout_seconds,
    }
    value.pop("intent_id", None)
    return {**value, "intent_id": canonical_digest(value)}

def _operations_skill(
    repo_root: Path,
    reader: Callable[[Path], str] | None,
) -> RedDogOperationsSkill:
    try:
        return load_reddog_operations_skill(
            repo_root, verified_text_reader=reader
        )
    except (ImportError, OSError, TypeError, ValueError) as exc:
        raise StartOperationsRejected(
            ("start_operations_skill_binding_invalid",)
        ) from exc

__all__ = ["CONTROL_SCHEMA", "PreparedSubmission", "StartOperationsRejected", "bound_intent", "budgets", "prepare_submission", "runtime_defaults", "runtime_defaults_for_resume", "validated_request"]
