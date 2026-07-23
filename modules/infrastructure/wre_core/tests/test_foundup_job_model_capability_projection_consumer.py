"""Validate-only consumer integration tests for model-capability projection."""

from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from modules.infrastructure.wre_core.src.foundup_job_consumer import (
    FoundUpJobConsumer,
)
from modules.infrastructure.wre_core.src.foundup_job_model_capability_consumer import (
    TrustedModelRuntimeBindingArtifact,
)
from modules.infrastructure.wre_core.src.foundup_job_model_capability_projection import (
    canonical_artifact_digest,
)
from modules.infrastructure.wre_core.src.foundup_job_router import RouteStatus
from modules.infrastructure.wre_core.tests.test_foundup_job_model_capability_projection import (
    _binding,
    _job,
    _simulated_result,
    _trusted,
)


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
    job = _job()
    result = FoundUpJobConsumer(
        dry_run=True,
        model_runtime_binding_resolver=_trusted(binding),
    ).consume_one(job)
    assert result.dispatched is True
    assert result.checkpoint_state == "SIMULATED"
    assert result.real_execution_performed is False
    assert result.model_capability_projection["decision"] == "bound"
    assert result.to_dict()["model_capability_projection"] == (
        result.model_capability_projection
    )
    execution_job = execute.call_args.args[0]
    assert execution_job is not job
    assert execution_job.to_dict() == job.to_dict()


@patch(
    "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
)
def test_self_consistent_trusted_artifact_relies_on_injected_trust_anchor(
    execute: MagicMock,
) -> None:
    binding = _binding(catalog_snapshot_id="forged-but-self-consistent")
    execute.return_value = _simulated_result()
    result = FoundUpJobConsumer(
        dry_run=True,
        model_runtime_binding_resolver=_trusted(binding),
    ).consume_one(_job())
    assert result.model_capability_projection["decision"] == "bound"
    assert result.model_capability_projection["catalog_snapshot_id"] == (
        "forged-but-self-consistent"
    )
    execute.assert_called_once()


@patch(
    "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
)
def test_consumer_rejects_invalid_and_live_absent_before_hermes(
    execute: MagicMock,
) -> None:
    invalid_result = FoundUpJobConsumer(
        dry_run=True,
        model_runtime_binding_resolver=_trusted(
            {"schema_version": "bad"},
            "sha256:" + ("0" * 64),
        ),
    ).consume_one(_job())
    live_result = FoundUpJobConsumer(dry_run=False).consume_one(_job())
    assert invalid_result.route_status == RouteStatus.BLOCKED
    assert invalid_result.checkpoint_blocker == "binding_schema_invalid"
    assert live_result.route_status == RouteStatus.BLOCKED
    assert live_result.checkpoint_blocker == "live_binding_required"
    execute.assert_not_called()


@patch(
    "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
)
def test_self_consistent_forged_job_payload_is_ignored(
    execute: MagicMock,
) -> None:
    binding = _binding()
    execute.return_value = _simulated_result()
    job = _job(
        payload={
            "model_runtime_binding_receipt": binding,
            "model_runtime_binding_digest": canonical_artifact_digest(binding),
            "validation_input": {"mode": "readonly"},
        }
    )
    result = FoundUpJobConsumer(dry_run=True).consume_one(job)
    execution_job = execute.call_args.args[0]
    assert result.model_capability_projection["decision"] == "unbound_dry_run"
    assert execution_job.payload == {"validation_input": {"mode": "readonly"}}


@pytest.mark.parametrize(
    ("mutation", "digest_mismatch", "reason"),
    [
        ({"schema_version": "bad"}, False, "binding_schema_invalid"),
        (
            {"runtime_surface": "reddog_artifact_generation"},
            False,
            "binding_surface_mismatch",
        ),
        ({"task_family": "other_task"}, False, "binding_task_family_mismatch"),
        ({}, True, "binding_digest_mismatch"),
    ],
)
@patch(
    "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
)
def test_trusted_injected_artifact_mismatches_block_before_hermes(
    execute: MagicMock,
    mutation: dict,
    digest_mismatch: bool,
    reason: str,
) -> None:
    binding = _binding(**mutation)
    digest = "sha256:" + ("0" * 64) if digest_mismatch else None
    result = FoundUpJobConsumer(
        dry_run=True,
        model_runtime_binding_resolver=_trusted(binding, digest),
    ).consume_one(_job())
    assert result.checkpoint_blocker == reason
    execute.assert_not_called()


@patch(
    "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
)
def test_validate_snapshot_prevents_mutation_between_admission_and_hermes(
    execute: MagicMock,
) -> None:
    binding = _binding()
    job = _job(payload={"validation_input": {"value": "before"}})
    execute.return_value = _simulated_result()

    def mutating_supply(lookup):
        assert lookup.requested_action == "validate_foundup"
        job.requested_action = "build_foundup"
        job.payload["validation_input"]["value"] = "after"
        return TrustedModelRuntimeBindingArtifact(
            artifact=binding,
            artifact_digest=canonical_artifact_digest(binding),
            provenance="outside_repo_confined_artifact_supply",
        )

    result = FoundUpJobConsumer(
        dry_run=True,
        model_runtime_binding_resolver=mutating_supply,
    ).consume_one(job)
    execution_job = execute.call_args.args[0]
    assert result.model_capability_projection["decision"] == "bound"
    assert execution_job is not job
    assert execution_job.requested_action == "validate_foundup"
    assert execution_job.payload["validation_input"]["value"] == "before"


@patch(
    "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
)
def test_raising_trusted_resolver_is_redacted_and_blocks(
    execute: MagicMock,
) -> None:
    secret = "DO_NOT_EXPOSE_SUPPLY_SECRET"

    def raising_resolver(lookup):
        del lookup
        raise RuntimeError(secret)

    result = FoundUpJobConsumer(
        dry_run=True,
        model_runtime_binding_resolver=raising_resolver,
    ).consume_one(_job())
    assert result.checkpoint_blocker == "binding_schema_invalid"
    assert secret not in json.dumps(result.to_dict(), sort_keys=True)
    execute.assert_not_called()


@patch(
    "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
)
def test_trusted_boundary_never_touches_hostile_digest_or_artifact(
    execute: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "DO_NOT_EXPOSE_TRUSTED_BOUNDARY_SECRET"
    digest_touched = False
    artifact_touched = False

    class HostileDigest:
        def __eq__(self, other):
            del other
            nonlocal digest_touched
            digest_touched = True
            raise RuntimeError(secret)

        def __str__(self):
            nonlocal digest_touched
            digest_touched = True
            raise RuntimeError(secret)

        def __repr__(self):
            nonlocal digest_touched
            digest_touched = True
            raise RuntimeError(secret)

    class HostileArtifact(dict):
        def get(self, *args, **kwargs):
            nonlocal artifact_touched
            artifact_touched = True
            raise RuntimeError(secret)

    binding = _binding()

    def hostile_digest_supply(lookup):
        del lookup
        return TrustedModelRuntimeBindingArtifact(
            artifact=binding,
            artifact_digest=HostileDigest(),
            provenance="outside_repo_confined_artifact_supply",
        )

    def hostile_artifact_supply(lookup):
        del lookup
        return TrustedModelRuntimeBindingArtifact(
            artifact=HostileArtifact(binding),
            artifact_digest=canonical_artifact_digest(binding),
            provenance="outside_repo_confined_artifact_supply",
        )
    with caplog.at_level(logging.DEBUG):
        digest_result = FoundUpJobConsumer(
            model_runtime_binding_resolver=hostile_digest_supply
        ).consume_one(_job())
        artifact_result = FoundUpJobConsumer(
            model_runtime_binding_resolver=hostile_artifact_supply
        ).consume_one(_job())
        malformed_results = [
            FoundUpJobConsumer(
                model_runtime_binding_resolver=_trusted(binding, digest)
            ).consume_one(_job())
            for digest in (
                "sha256:" + ("A" * 64),
                "SHA256:" + ("0" * 64),
                "sha256:" + ("0" * 63),
                "0" * 64,
            )
        ]
    serialized = json.dumps(
        [
            digest_result.to_dict(),
            artifact_result.to_dict(),
            *(result.to_dict() for result in malformed_results),
        ],
        sort_keys=True,
    )
    assert digest_result.checkpoint_blocker == "binding_schema_invalid"
    assert artifact_result.checkpoint_blocker == "binding_schema_invalid"
    assert all(
        result.checkpoint_blocker == "binding_schema_invalid"
        for result in malformed_results
    )
    assert digest_touched is False
    assert artifact_touched is False
    assert secret not in serialized
    assert secret not in caplog.text
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
    execute.assert_called_once_with(job)
