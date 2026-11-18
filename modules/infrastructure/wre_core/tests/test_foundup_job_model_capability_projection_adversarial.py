"""Adversarial model-capability projection boundary tests."""

from __future__ import annotations

import json

import pytest

from modules.infrastructure.wre_core.src.foundup_job_model_capability_projection import (
    canonical_artifact_digest,
)
from modules.infrastructure.wre_core.tests.test_foundup_job_model_capability_projection import (
    _binding,
    _job,
    _project,
    _project_binding,
    _refresh_receipt_id,
)


@pytest.mark.parametrize(
    "mutation",
    ["duplicate", "missing", "duplicate_role", "extra_model", "extra_role_model"],
)
def test_role_bindings_require_exact_unique_model_and_role_lineage(
    mutation: str,
) -> None:
    binding = _binding()
    if mutation == "duplicate":
        binding["role_bindings"].append(dict(binding["role_bindings"][0]))
    elif mutation == "missing":
        binding["role_bindings"].pop()
    elif mutation in ("duplicate_role", "extra_model"):
        panel_model = "anthropic/claude-reviewer"
        binding["panel_models"].append(panel_model)
        binding["benchmark_evidence_receipt_ids"].append("benchmark:reviewer")
        binding["promotion_evidence_receipt_ids"].append("promotion:reviewer")
        binding["signed_promotion_receipt_ids"].append("signed:reviewer")
        if mutation == "duplicate_role":
            binding["role_bindings"].append(
                {
                    "role": binding["role_bindings"][0]["role"],
                    "model_id": panel_model,
                    "provider": "anthropic",
                }
            )
    else:
        binding["role_bindings"][0]["model_id"] = "anthropic/unbound-reviewer"
        binding["role_bindings"][0]["provider"] = "anthropic"
    _refresh_receipt_id(binding)
    projection = _project_binding(_job(), binding)
    assert projection.rejection_reasons == ("binding_lineage_invalid",)


@pytest.mark.parametrize("nonfinite", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_binding_values_reject_before_rehydration(
    nonfinite: float,
) -> None:
    binding = _binding()
    binding["policy"]["min_verifier_pass_rate"] = nonfinite
    projection = _project(
        _job(),
        binding=binding,
        digest="sha256:" + ("0" * 64),
    )
    assert projection.rejection_reasons == ("binding_schema_invalid",)


def test_recursive_noncanonical_type_rejects_stably() -> None:
    binding = _binding()
    binding["panel_models"] = tuple(binding["panel_models"])
    projection = _project(
        _job(),
        binding=binding,
        digest="sha256:" + ("0" * 64),
    )
    assert projection.rejection_reasons == ("binding_schema_invalid",)


def test_canonical_digest_disallows_nonfinite_json() -> None:
    with pytest.raises(ValueError):
        canonical_artifact_digest({"value": float("nan")})


@pytest.mark.parametrize("method_name", ["get", "items"])
def test_hostile_mapping_exception_is_redacted_and_stable(
    method_name: str,
) -> None:
    secret = "DO_NOT_EXPOSE_BINDING_SECRET"

    class HostileMapping(dict):
        pass

    def explode(*args, **kwargs):
        del args, kwargs
        raise RuntimeError(secret)

    setattr(HostileMapping, method_name, explode)
    projection = _project(
        _job(),
        binding=HostileMapping(_binding()),
        digest="sha256:" + ("0" * 64),
    )
    serialized = json.dumps(projection.to_dict(), sort_keys=True)
    assert projection.rejection_reasons == ("binding_schema_invalid",)
    assert secret not in serialized


def test_hostile_mapping_iteration_is_redacted_and_stable() -> None:
    secret = "DO_NOT_EXPOSE_ITERATION_SECRET"

    class HostileIteration(dict):
        def items(self):
            yield from list(super().items())[:1]
            raise RuntimeError(secret)

    projection = _project(
        _job(),
        binding=HostileIteration(_binding()),
        digest="sha256:" + ("0" * 64),
    )
    serialized = json.dumps(projection.to_dict(), sort_keys=True)
    assert projection.rejection_reasons == ("binding_schema_invalid",)
    assert secret not in serialized
