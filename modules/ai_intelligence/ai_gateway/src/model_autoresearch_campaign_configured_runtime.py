"""Bounded configured-runtime assembly for AutoResearch campaigns.

Construction and preflight happen here without invoking a provider. The
campaign executor receives the prepared runner only after atomic path claims.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .ai_gateway import AIGateway
from .model_autoresearch_canonical_prompt_guard import (
    build_canonical_local_autoresearch_prompt_guard,
)
from .model_autoresearch_configured_gateway_evidence import (
    JsonlConfiguredGatewayReceiptStore,
    read_runner_receipts_jsonl,
)
from .model_autoresearch_configured_gateway_runner import (
    AIGatewayConfiguredModelCaller,
    ConfiguredGatewayRunnerPolicy,
    LMStudioConfiguredModelCaller,
    MappingPromptSource,
    RoutedConfiguredModelCaller,
    build_configured_gateway_benchmark_runner,
)
from .model_autoresearch_output_evidence_bundle import (
    JsonlModelAutoResearchOutputEvidenceStore,
    read_model_autoresearch_output_evidence_jsonl,
)
from .model_autoresearch_semantic_verifier import (
    build_model_autoresearch_output_evidence_semantic_verifier,
)
from .model_champion_challenger_autoresearch import (
    ModelAutoResearchAction,
    rehydrate_model_autoresearch_plan_receipt,
)
from .model_combination_benchmark_harness import (
    ModelBenchmarkCandidate,
    ModelBenchmarkRoleAssignment,
    ModelBenchmarkTask,
    build_model_benchmark_candidate,
)


def configured_runner_and_verifier(
    *,
    root: Path,
    prompts: Mapping[str, str],
    policy: ConfiguredGatewayRunnerPolicy,
    semantic_verifier: bool,
    exact_verifier: Callable[..., Any],
    output_evidence_path: Path | str | None,
    call_attempt_evidence_path: Path | str | None,
    runner_success_receipt_path: Path | str | None,
    gateway: object | None,
    lm_studio_backend_factory: Callable[[str], Any] | None,
) -> tuple[Callable[..., Any], Callable[..., Any], Path]:
    evidence_path = runtime_path(root, output_evidence_path)
    local_caller = (
        LMStudioConfiguredModelCaller(lm_studio_backend_factory)
        if lm_studio_backend_factory is not None
        else LMStudioConfiguredModelCaller()
    )
    trusted_prompt_guard = build_canonical_local_autoresearch_prompt_guard()
    runner = build_configured_gateway_benchmark_runner(
        caller=RoutedConfiguredModelCaller(
            AIGatewayConfiguredModelCaller(gateway if gateway is not None else AIGateway()),
            local_caller,
        ),
        prompt_source=MappingPromptSource(prompts),
        policy=policy,
        prompt_guard=trusted_prompt_guard,
        output_evidence_store=JsonlModelAutoResearchOutputEvidenceStore(
            evidence_path, repo_root=root
        ),
        call_attempt_receipt_store=JsonlConfiguredGatewayReceiptStore(
            runtime_path(root, call_attempt_evidence_path)
        ),
        runner_receipt_store=JsonlConfiguredGatewayReceiptStore(
            runtime_path(root, runner_success_receipt_path)
        ),
    )
    if not semantic_verifier:
        return runner, exact_verifier, evidence_path
    verifier = build_model_autoresearch_output_evidence_semantic_verifier(
        evidence_records=lambda: read_model_autoresearch_output_evidence_jsonl(
            evidence_path, repo_root=root
        ),
        runner_receipts=lambda: read_runner_receipts_jsonl(
            runtime_path(root, runner_success_receipt_path)
        ),
    )
    return runner, verifier, evidence_path


def prepare_configured_campaign(
    *,
    runner: Callable[..., Any],
    root: Path,
    plan_payload: Mapping[str, Any],
    candidate_pool: Sequence[Mapping[str, Any]],
    tasks: Sequence[Mapping[str, Any]],
    output_paths: Sequence[Path | str | None],
) -> bool:
    members = configured_campaign_members(plan_payload, candidate_pool, tasks)
    prepare_campaign = getattr(runner, "prepare_campaign", None)
    if members is None or not callable(prepare_campaign):
        return False
    try:
        selected_candidates, prepared_tasks = members
        prepare_campaign(tasks=prepared_tasks, candidates=selected_candidates)
        claim_configured_output_paths(root, *output_paths)
    except Exception:
        return False
    return True


def configured_campaign_members(
    plan_payload: Mapping[str, Any],
    candidate_pool: Sequence[Mapping[str, Any]],
    tasks: Sequence[Mapping[str, Any]],
) -> tuple[tuple[ModelBenchmarkCandidate, ...], tuple[ModelBenchmarkTask, ...]] | None:
    try:
        plan = rehydrate_model_autoresearch_plan_receipt(plan_payload)
        candidates = tuple(preflight_candidate(item) for item in candidate_pool)
        normalized_tasks = preflight_tasks(tasks)
        digest = digest_receipt(
            "model_autoresearch_candidate_pool",
            {"candidates": [
                item.to_dict()
                for item in sorted(candidates, key=lambda value: value.candidate_id)
            ]},
        )
        if digest != plan.candidate_pool_digest or plan.rejection_reasons:
            return None
        by_id = {item.candidate_id: item for item in candidates}
        selected = tuple(
            by_id[item.candidate_id]
            for item in plan.campaign_items
            if item.action != ModelAutoResearchAction.STOP
            and item.requires_independent_verifier
        )
    except (KeyError, TypeError, ValueError):
        return None
    return (selected, normalized_tasks) if selected else None


def preflight_candidate(payload: Mapping[str, Any]) -> ModelBenchmarkCandidate:
    raw_roles = payload.get("role_assignments")
    if not isinstance(raw_roles, list) or not raw_roles:
        raise ValueError("invalid_candidate_roles")
    if any(not isinstance(item, Mapping) for item in raw_roles):
        raise ValueError("invalid_candidate_role")
    roles = tuple(
        ModelBenchmarkRoleAssignment(
            role=item.get("role"),  # type: ignore[arg-type]
            model_id=item.get("model_id"),  # type: ignore[arg-type]
            provider=item.get("provider"),  # type: ignore[arg-type]
        )
        for item in raw_roles
    )
    candidate = build_model_benchmark_candidate(roles)
    if (
        candidate.candidate_id != payload.get("candidate_id")
        or candidate.topology_digest != payload.get("topology_digest")
    ):
        raise ValueError("candidate_binding_mismatch")
    return candidate


def preflight_tasks(
    tasks: Sequence[Mapping[str, Any]],
) -> tuple[ModelBenchmarkTask, ...]:
    normalized = tuple(
        ModelBenchmarkTask(
            task_id=item.get("task_id"),  # type: ignore[arg-type]
            task_family=item.get("task_family"),  # type: ignore[arg-type]
            prompt_digest=item.get("prompt_digest"),  # type: ignore[arg-type]
            expected_output_digest=item.get("expected_output_digest"),  # type: ignore[arg-type]
            verifier_contract_digest=item.get("verifier_contract_digest"),  # type: ignore[arg-type]
            metadata=item.get("metadata") or {},  # type: ignore[arg-type]
        ).normalized()
        for item in tasks
    )
    if not normalized:
        raise ValueError("missing_tasks")
    return normalized


def claim_configured_output_paths(repo_root: Path, *values: Path | str | None) -> None:
    claimed: list[Path] = []
    try:
        for value in values:
            path = runtime_path(repo_root, value)
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
            claimed.append(path)
    except Exception:
        for path in claimed:
            try:
                path.unlink()
            except OSError:
                pass
        raise


def runtime_path(repo_root: Path, value: Path | str | None) -> Path:
    path = Path(value or "")
    if not path.is_absolute():
        path = repo_root.parent / path
    return path.resolve()


def digest_receipt(prefix: str, value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


__all__ = [
    "configured_runner_and_verifier",
    "digest_receipt",
    "preflight_candidate",
    "preflight_tasks",
    "prepare_configured_campaign",
    "runtime_path",
]
