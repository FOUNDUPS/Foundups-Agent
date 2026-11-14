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
from modules.infrastructure.wre_core.src.foundup_job_router import RouteStatus, TargetBackend
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
    execute.assert_called_once_with(job, force_dry_run=True)


@pytest.fixture
def executor_capture(monkeypatch, tmp_path):
    from modules.infrastructure.wre_core.src import hermes_job_executor as hx

    observed = []
    monkeypatch.setenv("FOUNDUPS_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(hx, "_executor_singleton", None)
    validator = hx.get_default_validator()
    monkeypatch.setattr(validator, "used_nonces", {"already-used"})

    def capture(executor, job):
        observed.append((executor, job))
        return _simulated_result()

    monkeypatch.setattr(hx.HermesJobExecutor, "execute", capture)
    for name in ("_emit_receipt_for_hermes_result", "_attach_context_bundle_dry_run"):
        monkeypatch.setattr(FoundUpJobConsumer, name, lambda *args: None)
    return hx, observed, tmp_path, validator


@pytest.mark.parametrize("state", ["fresh", "dry", "non_dry", "controlled"])
@pytest.mark.parametrize("consumer_flag", [True, False])
@pytest.mark.parametrize("job_flag", [True, False])
def test_consumer_isolates_forced_dry_configuration(
    executor_capture, monkeypatch, state, consumer_flag, job_flag
):
    from modules.infrastructure.wre_core.src import foundup_job_consumer as fc

    hx, observed, root, validator = executor_capture
    warm = None if state == "fresh" else hx.HermesJobExecutor(
        dry_run=state != "non_dry", max_iterations=7,
        workspace_root=str(root / "warm"),
        controlled_harness=state == "controlled",
        real_delegate_adapter=state == "controlled",
        default_toolsets=["terminal"] if state == "controlled" else [],
    )
    hx._executor_singleton = warm
    warm_state = dict(vars(warm)) if warm else None
    job = _job("build_foundup")
    job.policy_flags.dry_run_mode = job_flag
    route = MagicMock(job_id=job.job_id, route_status=RouteStatus.ROUTED,
                      target_backend=TargetBackend.HERMES_BUILDER)
    monkeypatch.setattr(fc, "route_foundup_job", lambda job: route)
    result = FoundUpJobConsumer(dry_run=consumer_flag).consume_one(job)
    assert result.dispatched is True
    executor, actual_job = observed.pop()
    assert actual_job is job and job.policy_flags.dry_run_mode is job_flag
    if consumer_flag:
        assert executor is not warm and executor.dry_run is True
        assert executor.controlled_harness is False
        assert executor.real_delegate_adapter is False
        assert executor.default_toolsets == [] and executor.max_iterations == 50
        assert executor.workspace_root == str(root)
        assert hx._executor_singleton is warm
    else:
        assert executor is (warm if warm is not None else hx._executor_singleton)
    if warm:
        assert vars(warm) == warm_state
    assert executor.token_validator is validator
    assert validator.used_nonces == {"already-used"}
    assert validator.register_nonce("already-used") is False


@pytest.mark.parametrize("explicit_false", [False, True])
def test_convenience_legacy_calls_preserve_warmed_executor(
    executor_capture, explicit_false
):
    hx, observed, root, validator = executor_capture
    warm = hx.get_executor(dry_run=False, max_iterations=7, workspace_root=str(root))
    job = _job()
    options = {"force_dry_run": False} if explicit_false else {}
    hx.execute_foundup_job(job, **options)
    assert observed == [(warm, job)]
    assert hx.get_executor() is warm and warm.dry_run is False
    assert warm.max_iterations == 7 and warm.token_validator is validator


@pytest.mark.parametrize("value", [None, 0, 1, "true", "false", [], {}, object()])
def test_force_dry_requires_literal_boolean_before_executor_selection(value):
    from modules.infrastructure.wre_core.src import hermes_job_executor as hx

    with patch.object(hx, "get_executor") as singleton, patch.object(
        hx, "HermesJobExecutor"
    ) as constructor:
        with pytest.raises(TypeError, match="force_dry_run must be a boolean"):
            hx.execute_foundup_job(_job(), force_dry_run=value)
        singleton.assert_not_called()
        constructor.assert_not_called()


@pytest.mark.parametrize("site", ["route", "resolver"])
@pytest.mark.parametrize("initial", [True, False])
@pytest.mark.parametrize("bound", [True, False])
def test_consumer_mode_is_captured_before_callbacks(monkeypatch, site, initial, bound):
    from modules.infrastructure.wre_core.src import foundup_job_consumer as fc

    trusted = _trusted(_binding()) if bound else lambda lookup: None

    def resolver(lookup):
        if site == "resolver":
            consumer.dry_run = not initial
        return trusted(lookup)

    consumer = FoundUpJobConsumer(
        dry_run=initial, model_runtime_binding_resolver=resolver
    )
    original_route = fc.route_foundup_job

    def route(job):
        if site == "route":
            consumer.dry_run = not initial
        return original_route(job)

    monkeypatch.setattr(fc, "route_foundup_job", route)
    with patch(
        "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job",
        return_value=_simulated_result(),
    ) as execute:
        result = consumer.consume_one(_job())
    assert result.model_capability_projection["dry_run_mode"] is initial
    if not initial and not bound:
        assert result.checkpoint_blocker == "live_binding_required"
        execute.assert_not_called()
    else:
        assert result.dispatched is True
        assert execute.call_args.kwargs == {"force_dry_run": initial}


def test_forced_executor_uses_shared_validator_not_warmed_custom(executor_capture):
    hx, observed, root, shared = executor_capture
    custom = hx.LocalCapabilityTokenValidator()
    custom.register_nonce("custom-used")
    warm = hx.HermesJobExecutor(dry_run=False, token_validator=custom)
    hx._executor_singleton = warm
    hx.execute_foundup_job(_job(), force_dry_run=True)
    assert observed[0][0].token_validator is shared
    assert shared.used_nonces == {"already-used"}
    assert hx._executor_singleton is warm and warm.token_validator is custom
    assert custom.used_nonces == {"custom-used"}


@pytest.mark.parametrize("enabled", ["0", "1"])
@pytest.mark.parametrize(
    ("action", "token", "status"),
    [
        ("validate_foundup", False, "SIMULATED"),
        ("build_foundup", False, "BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD"),
        ("validate_foundup", True, "BLOCKED_BY_TOKEN_VALIDATION"),
    ],
)
def test_forced_dry_retains_real_guard_and_token_boundaries(
    monkeypatch, tmp_path, enabled, action, token, status
):
    from modules.infrastructure.wre_core.src import hermes_job_executor as hx

    monkeypatch.setenv("FOUNDUPS_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("HERMES_DELEGATE_ENABLED", enabled)
    warm = hx.HermesJobExecutor(
        dry_run=False, controlled_harness=True, real_delegate_adapter=True
    )
    monkeypatch.setattr(hx, "_executor_singleton", warm)
    job = _job(action)
    if token:
        job.payload["capability_token"] = {
            "token_id": "invalid", "issued_at": "2000-01-01T00:00:00+00:00",
            "expires_at": "2000-01-02T00:00:00+00:00",
        }
    with patch.object(hx.HermesJobExecutor, "_execute_controlled_delegate") as controlled, patch.object(
        hx.HermesJobExecutor, "_execute_real_delegate_adapter"
    ) as adapter, patch.object(hx.HermesJobExecutor, "_lazy_import_delegate_task") as loader:
        result = hx.execute_foundup_job(job, force_dry_run=True)
    assert result.status.value == status
    assert result.real_execution_performed is False
    assert hx._executor_singleton is warm
    controlled.assert_not_called()
    adapter.assert_not_called()
    loader.assert_not_called()
