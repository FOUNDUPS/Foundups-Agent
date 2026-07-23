"""Audited FoundUp job model-capability projection contract tests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
    PolicyFlags,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_runtime_binding_receipt,
)
from modules.infrastructure.wre_core.src.foundup_job_consumer import (
    FoundUpJobConsumer,
)
from modules.infrastructure.wre_core.src.foundup_job_model_capability_projection import (
    FOUNDUP_JOB_MODEL_CAPABILITY_PROFILES,
    PROFILE_SCHEMA_VERSION,
    PROJECTION_REJECTION_REASONS,
    PROJECTION_SCHEMA_VERSION,
    canonical_artifact_digest,
    resolve_foundup_job_model_capability_projection,
)
from modules.infrastructure.wre_core.src.foundup_job_router import (
    RouteStatus,
    TargetBackend,
    route_foundup_job,
)


RUNTIME_SURFACE = "reddog_readonly_audit_worker"
TASK_FAMILY = "foundup_validation"
PROFILE_FIELDS = {
    "schema_version",
    "profile_id",
    "requested_action",
    "target_backend",
    "runtime_surface",
    "task_family",
    "destructive_action_class",
    "provider_policy",
    "required_modalities",
    "require_tools",
    "require_structured_output",
    "require_reasoning",
    "allowed_selection_modes",
    "max_panel_models",
}
PROJECTION_FIELDS = {
    "schema_version",
    "projection_id",
    "profile_id",
    "decision",
    "rejection_reasons",
    "job_id",
    "tenant_id",
    "foundup_id",
    "requested_action",
    "target_backend",
    "runtime_surface",
    "task_family",
    "dry_run_mode",
    "compute_tier",
    "compute_budget",
    "compute_used",
    "cost_class_preference",
    "catalog_snapshot_id",
    "selection_receipt_id",
    "model_runtime_binding_receipt_id",
    "model_runtime_binding_digest",
    "principal_model",
    "panel_models",
    "role_bindings",
    "benchmark_evidence_receipt_ids",
    "promotion_evidence_receipt_ids",
    "signed_promotion_receipt_ids",
    "runtime_policy_digest",
    "runtime_authority_receipt_id",
    "provider_call_admission",
}


def _job(
    action: str = "validate_foundup",
    *,
    payload: dict | None = None,
    foundup_id: str = "demo",
    model_preference: str = "standard",
) -> FoundUpJob:
    return FoundUpJob(
        job_id=f"job-{action}",
        tenant_id="tenant-a",
        foundup_id=foundup_id,
        requested_action=action,
        payload=payload or {},
        policy_flags=PolicyFlags(dry_run_mode=True),
        compute_tier="basic",
        compute_budget=50,
        compute_used=3,
        model_preference=model_preference,
    )


def _binding(**overrides) -> dict:
    binding = model_runtime_binding_receipt(
        runtime_surface=RUNTIME_SURFACE,
        task_family=TASK_FAMILY,
    )
    binding.update(overrides)
    if overrides:
        _refresh_receipt_id(binding)
    return binding


def _refresh_receipt_id(binding: dict) -> None:
    body = {key: value for key, value in binding.items() if key != "receipt_id"}
    encoded = json.dumps(
        body, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    binding["receipt_id"] = (
        "reddog_model_runtime_binding:" + hashlib.sha256(encoded).hexdigest()
    )


def _project(job: FoundUpJob, *, dry_run: bool = True):
    envelope = route_foundup_job(job)
    return resolve_foundup_job_model_capability_projection(
        job=job,
        route_envelope=envelope,
        dry_run_mode=dry_run,
        model_runtime_binding_receipt=job.payload.get(
            "model_runtime_binding_receipt"
        ),
        model_runtime_binding_digest=job.payload.get(
            "model_runtime_binding_digest"
        ),
    )


def _payload(binding: dict) -> dict:
    return {
        "model_runtime_binding_receipt": binding,
        "model_runtime_binding_digest": canonical_artifact_digest(binding),
    }


def _simulated_result() -> MagicMock:
    result = MagicMock()
    result.status.value = "SIMULATED"
    result.checkpoint_state = "SIMULATED"
    result.checkpoint_result = "Read-only validation simulated"
    result.checkpoint_blocker = None
    result.checkpoint_next_action = None
    result.evidence_path = ".hermes_evidence/job-validate_foundup"
    result.real_execution_performed = False
    return result


def test_canonical_five_action_profiles_are_exact_and_deterministic() -> None:
    expected = {
        "create_foundup": (
            "hermes_scaffold",
            None,
            None,
            "D2",
            "forbidden",
        ),
        "queue_foundup_job": (
            "openclaw_queue",
            None,
            None,
            "deferred",
            "forbidden",
        ),
        "build_foundup": (
            "hermes_builder",
            "reddog_artifact_generation",
            "foundup_artifact_generation",
            "D3",
            "receipt_bound",
        ),
        "extract_foundup": (
            "hermes_builder",
            "reddog_artifact_generation",
            "foundup_artifact_generation",
            "D3",
            "receipt_bound",
        ),
        "validate_foundup": (
            "hermes_validator",
            RUNTIME_SURFACE,
            TASK_FAMILY,
            "D0",
            "receipt_bound",
        ),
    }
    assert set(FOUNDUP_JOB_MODEL_CAPABILITY_PROFILES) == set(expected)
    for action, values in expected.items():
        profile = FOUNDUP_JOB_MODEL_CAPABILITY_PROFILES[action]
        assert (
            profile.target_backend,
            profile.runtime_surface,
            profile.task_family,
            profile.destructive_action_class,
            profile.provider_policy,
        ) == values
        artifact = profile.to_dict()
        assert set(artifact) == PROFILE_FIELDS
        assert artifact["schema_version"] == PROFILE_SCHEMA_VERSION
        body = {key: value for key, value in artifact.items() if key != "profile_id"}
        assert profile.profile_id == canonical_artifact_digest(body)


def test_provider_capable_profile_requirements_remain_explicitly_unspecified() -> None:
    for action in ("build_foundup", "extract_foundup", "validate_foundup"):
        profile = FOUNDUP_JOB_MODEL_CAPABILITY_PROFILES[action]
        assert profile.required_modalities is None
        assert profile.require_tools is None
        assert profile.require_structured_output is None
        assert profile.require_reasoning is None
        assert profile.allowed_selection_modes is None
        assert profile.max_panel_models is None
    for action in ("create_foundup", "queue_foundup_job"):
        profile = FOUNDUP_JOB_MODEL_CAPABILITY_PROFILES[action]
        assert profile.required_modalities == ()
        assert profile.require_tools is False
        assert profile.require_structured_output is False
        assert profile.require_reasoning is False
        assert profile.allowed_selection_modes == ()
        assert profile.max_panel_models == 0


def test_validate_dry_run_without_binding_is_truthfully_unbound() -> None:
    projection = _project(_job())
    artifact = projection.to_dict()
    assert set(artifact) == PROJECTION_FIELDS
    assert artifact["schema_version"] == PROJECTION_SCHEMA_VERSION
    assert projection.decision == "unbound_dry_run"
    assert projection.rejection_reasons == ()
    assert projection.model_runtime_binding_receipt_id is None
    assert projection.model_runtime_binding_digest is None
    assert projection.runtime_policy_digest is None
    assert projection.provider_call_admission == "not_evaluated"
    assert projection.cost_class_preference == "standard"


@pytest.mark.parametrize(
    ("action", "decision"),
    [
        ("create_foundup", "not_applicable"),
        ("queue_foundup_job", "not_applicable"),
        ("build_foundup", "unbound_dry_run"),
        ("extract_foundup", "unbound_dry_run"),
        ("validate_foundup", "unbound_dry_run"),
    ],
)
def test_all_five_profiles_resolve_without_silent_binding(
    action: str,
    decision: str,
) -> None:
    job = _job(action)
    if action == "create_foundup":
        job.payload = {"genesis_envelope": {"foundup_id": "demo"}}
        job.creation_mode = "new_scaffold"
        job.genesis_envelope_digest = "sha256:" + ("a" * 64)
        job.scaffold_contract_digest = "sha256:" + ("b" * 64)
    assert _project(job).decision == decision


def test_live_validate_without_binding_rejects_before_execution() -> None:
    projection = _project(_job(), dry_run=False)
    assert projection.decision == "rejected"
    assert projection.rejection_reasons == ("live_binding_required",)


def test_valid_validate_binding_projects_exact_receipt_lineage() -> None:
    binding = _binding()
    projection = _project(_job(payload=_payload(binding)))
    assert projection.decision == "bound"
    assert projection.model_runtime_binding_receipt_id == binding["receipt_id"]
    assert projection.model_runtime_binding_digest == canonical_artifact_digest(
        binding
    )
    assert projection.catalog_snapshot_id == binding["catalog_snapshot_id"]
    assert projection.selection_receipt_id == binding["selection_receipt_id"]
    assert projection.principal_model == binding["principal_model"]
    assert projection.panel_models == tuple(binding["panel_models"])
    assert projection.benchmark_evidence_receipt_ids == tuple(
        binding["benchmark_evidence_receipt_ids"]
    )
    assert projection.runtime_authority_receipt_id == (
        binding["policy"]["authority_receipt_id"]
    )
    assert projection.to_dict() == _project(
        _job(payload=_payload(binding))
    ).to_dict()


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ({"schema_version": "wrong.v1"}, "binding_schema_invalid"),
        ({"unexpected": "field"}, "binding_schema_invalid"),
        ({"decision": "rejected"}, "binding_decision_not_bound"),
        ({"runtime_surface": "reddog_artifact_generation"}, "binding_surface_mismatch"),
        ({"task_family": "other_task"}, "binding_task_family_mismatch"),
    ],
)
def test_invalid_or_mismatched_binding_rejects(
    mutation: dict,
    reason: str,
) -> None:
    binding = _binding(**mutation)
    projection = _project(_job(payload=_payload(binding)))
    assert projection.decision == "rejected"
    assert projection.rejection_reasons == (reason,)


def test_binding_digest_and_lineage_mismatch_reject_stably() -> None:
    binding = _binding()
    bad_digest = _payload(binding)
    bad_digest["model_runtime_binding_digest"] = "sha256:" + ("0" * 64)
    assert _project(_job(payload=bad_digest)).rejection_reasons == (
        "binding_digest_mismatch",
    )
    binding["policy"]["authority_receipt_id"] = None
    _refresh_receipt_id(binding)
    lineage = _project(_job(payload=_payload(binding)))
    assert lineage.rejection_reasons == ("binding_lineage_invalid",)


def test_one_sided_binding_lineage_rejects_without_raw_exception() -> None:
    binding = _binding()
    projection = _project(
        _job(payload={"model_runtime_binding_receipt": binding})
    )
    assert projection.rejection_reasons == ("binding_lineage_invalid",)
    assert set(projection.rejection_reasons) <= set(PROJECTION_REJECTION_REASONS)


def test_job_route_identity_and_profile_backend_mismatch_are_rejected() -> None:
    job = _job()
    envelope = replace(
        route_foundup_job(job),
        job_id="other-job",
        target_backend=TargetBackend.HERMES_BUILDER,
    )
    projection = resolve_foundup_job_model_capability_projection(
        job=job,
        route_envelope=envelope,
        dry_run_mode=True,
    )
    assert projection.rejection_reasons == (
        "job_route_identity_mismatch",
        "profile_backend_mismatch",
    )


@pytest.mark.parametrize("action", ["create_foundup", "queue_foundup_job"])
def test_provider_forbidden_action_rejects_supplied_binding(action: str) -> None:
    binding = _binding()
    if action == "create_foundup":
        payload = {
            **_payload(binding),
            "genesis_envelope": {"foundup_id": "demo"},
        }
        job = _job(action, payload=payload)
        job.creation_mode = "new_scaffold"
        job.genesis_envelope_digest = "sha256:" + ("a" * 64)
        job.scaffold_contract_digest = "sha256:" + ("b" * 64)
    else:
        job = _job(action, payload=_payload(binding))
    projection = _project(job)
    assert projection.decision == "rejected"
    assert projection.rejection_reasons == ("binding_not_applicable",)


@patch(
    "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
)
def test_consumer_dry_validate_without_binding_dispatches_unbound(
    execute: MagicMock,
) -> None:
    execute.return_value = _simulated_result()
    result = FoundUpJobConsumer(dry_run=True).consume_one(_job())
    assert result.dispatched is True
    assert result.model_capability_projection["decision"] == "unbound_dry_run"
    execute.assert_called_once()


@patch(
    "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
)
def test_consumer_bound_validate_preserves_simulation_and_serializes_projection(
    execute: MagicMock,
) -> None:
    binding = _binding()
    execute.return_value = _simulated_result()
    job = _job(payload=_payload(binding))
    result = FoundUpJobConsumer(dry_run=True).consume_one(job)
    assert result.dispatched is True
    assert result.checkpoint_state == "SIMULATED"
    assert result.real_execution_performed is False
    assert result.model_capability_projection["decision"] == "bound"
    assert result.to_dict()["model_capability_projection"] == (
        result.model_capability_projection
    )
    execute.assert_called_once_with(job)


@patch(
    "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
)
def test_consumer_rejects_invalid_and_live_absent_before_hermes(
    execute: MagicMock,
) -> None:
    invalid = _job(
        payload={
            "model_runtime_binding_receipt": {"schema_version": "bad"},
            "model_runtime_binding_digest": "sha256:" + ("0" * 64),
        }
    )
    invalid_result = FoundUpJobConsumer(dry_run=True).consume_one(invalid)
    live_result = FoundUpJobConsumer(dry_run=False).consume_one(_job())
    assert invalid_result.route_status == RouteStatus.BLOCKED
    assert invalid_result.checkpoint_blocker == "binding_schema_invalid"
    assert live_result.route_status == RouteStatus.BLOCKED
    assert live_result.checkpoint_blocker == "live_binding_required"
    execute.assert_not_called()


@patch(
    "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
)
def test_consumer_leaves_other_action_projection_absent(
    execute: MagicMock,
) -> None:
    execute.return_value = _simulated_result()
    job = _job("build_foundup")
    result = FoundUpJobConsumer(dry_run=True).consume_one(job)
    assert result.model_capability_projection is None


def test_projection_source_has_no_selection_binding_or_provider_calls() -> None:
    source = (
        Path(__file__).parents[1]
        / "src"
        / "foundup_job_model_capability_projection.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "select_models_for_task(",
        "bind_reddog_runtime_models(",
        "build_model_catalog_snapshot(",
        "requests.",
        "httpx.",
        "subprocess.",
    )
    assert not any(token in source for token in forbidden)
