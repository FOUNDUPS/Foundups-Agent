"""Authority-bound model tests for bounded artifact generation."""

from __future__ import annotations

import copy
import pickle

import pytest

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    canonical_model_runtime_binding_digest,
    discard_verified_runtime_binding_capability,
    verification_receipt_digest,
    verified_runtime_binding_receipt,
)
from modules.communication.moltbot_bridge.src import (
    reddog_artifact_generation_admission_capability as admission_capability,
)
from modules.communication.moltbot_bridge.src import (
    reddog_bounded_artifact_generation_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_artifact_generation_admission_capability import (
    ArtifactGenerationAuthorityCapability,
    ArtifactGenerationModelCapability,
    _issue_artifact_generation_authority,
    consume_artifact_generation_authority,
)
from modules.communication.moltbot_bridge.src.reddog_bounded_artifact_generation_runtime import (
    FAIL_AUTHORITY,
    FAIL_MODEL_RUNTIME_BINDING_RECEIPT,
    ArtifactGenerationModelResult,
    RUNTIME_SURFACE_ARTIFACT_GENERATION,
    generate_bounded_artifact_contents,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_runtime_binding_test_capability,
    model_selection_and_runtime_binding_receipts,
)
from modules.communication.moltbot_bridge.tests.test_reddog_bounded_artifact_generation_runtime import (
    ARTIFACT,
    TASK_FAMILY,
    FakeRunner,
    _generate,
    _request,
    _runtime_receipt_id,
)


@pytest.mark.parametrize(
    "field",
    (
        "model_selection_receipt_id",
        "model_selection_digest",
        "model_runtime_binding_receipt_id",
        "model_runtime_binding_digest",
        "model_runtime_binding_verification_receipt_id",
        "model_runtime_binding_verification_digest",
    ),
)
def test_signed_authority_model_lineage_mismatch_rejects_before_runner(
    field: str,
) -> None:
    request = _request()
    request["signed_authority"] = {
        **dict(request["signed_authority"]),
        field: "attacker-value",
    }
    runner = FakeRunner()

    result = _generate(request, runner=runner)

    assert result.accepted is False
    assert FAIL_MODEL_RUNTIME_BINDING_RECEIPT in result.rejection_reasons
    assert runner.calls == []


def test_self_rehashed_runtime_binding_without_evidence_rejects_before_runner() -> None:
    request = _request()
    runtime_binding = dict(request["model_runtime_binding_receipt"])
    runtime_binding["benchmark_evidence_receipt_ids"] = []
    runtime_binding["promotion_evidence_receipt_ids"] = []
    runtime_binding["signed_promotion_receipt_ids"] = []
    runtime_binding["receipt_id"] = _runtime_receipt_id(runtime_binding)
    request["model_runtime_binding_receipt"] = runtime_binding
    request["signed_authority"] = {
        **dict(request["signed_authority"]),
        "model_runtime_binding_receipt_id": runtime_binding["receipt_id"],
        "model_runtime_binding_digest": canonical_model_runtime_binding_digest(
            runtime_binding
        ),
    }
    runner = FakeRunner()

    result = _generate(request, runner=runner)

    assert result.accepted is False
    assert FAIL_MODEL_RUNTIME_BINDING_RECEIPT in result.rejection_reasons
    assert runner.calls == []


def test_self_rehashed_runtime_model_substitution_rejects_before_runner() -> None:
    request = _request()
    runtime_binding = dict(request["model_runtime_binding_receipt"])
    runtime_binding["principal_model"] = "attacker/substitute-model"
    runtime_binding["role_bindings"] = [
        {
            "role": "principal",
            "model_id": "attacker/substitute-model",
            "provider": "attacker",
        }
    ]
    runtime_binding["receipt_id"] = _runtime_receipt_id(runtime_binding)
    request["model_runtime_binding_receipt"] = runtime_binding
    request["signed_authority"] = {
        **dict(request["signed_authority"]),
        "model_runtime_binding_receipt_id": runtime_binding["receipt_id"],
        "model_runtime_binding_digest": canonical_model_runtime_binding_digest(
            runtime_binding
        ),
    }
    runner = FakeRunner()

    result = _generate(request, runner=runner)

    assert result.accepted is False
    assert FAIL_MODEL_RUNTIME_BINDING_RECEIPT in result.rejection_reasons
    assert runner.calls == []


def test_artifact_generation_requires_one_shot_authority_capability() -> None:
    request = _request()
    runner = FakeRunner()

    missing = generate_bounded_artifact_contents(request, runner=runner)
    forged = ArtifactGenerationAuthorityCapability("attacker-token")
    forged_result = generate_bounded_artifact_contents(
        request,
        runner=runner,
        authority_capability=forged,
    )

    assert FAIL_AUTHORITY in missing.rejection_reasons
    assert FAIL_AUTHORITY in forged_result.rejection_reasons
    assert runner.calls == []


def test_copied_authority_token_cannot_replace_original_identity() -> None:
    request = _request()
    original = _issue_artifact_generation_authority(request)
    assert original is not None
    token = object.__getattribute__(
        original, "_ArtifactGenerationAuthorityCapability__token"
    )
    candidate = ArtifactGenerationAuthorityCapability(token)
    runner = FakeRunner()

    rejected = generate_bounded_artifact_contents(
        request,
        runner=runner,
        authority_capability=candidate,
        model_runtime_binding_capability=model_runtime_binding_test_capability(
            request["model_selection_receipt"],
            request["model_runtime_binding_receipt"],
        ),
    )
    accepted = generate_bounded_artifact_contents(
        request,
        runner=runner,
        authority_capability=original,
        model_runtime_binding_capability=model_runtime_binding_test_capability(
            request["model_selection_receipt"],
            request["model_runtime_binding_receipt"],
        ),
    )
    replayed = generate_bounded_artifact_contents(
        request,
        runner=runner,
        authority_capability=original,
        model_runtime_binding_capability=model_runtime_binding_test_capability(
            request["model_selection_receipt"],
            request["model_runtime_binding_receipt"],
        ),
    )

    assert FAIL_AUTHORITY in rejected.rejection_reasons
    assert accepted.accepted is True
    assert FAIL_AUTHORITY in replayed.rejection_reasons
    assert len(runner.calls) == 1


@pytest.mark.parametrize("transform", (copy.copy, copy.deepcopy, pickle.dumps))
def test_authority_capability_copy_and_pickle_are_forbidden(transform) -> None:
    capability = _issue_artifact_generation_authority(_request())
    assert capability is not None
    with pytest.raises(TypeError):
        transform(capability)


def test_foundups_fusion_runner_has_no_hardcoded_model_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    network_calls: list[object] = []
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        reddog_bounded_artifact_generation_runtime,
        "_load_foundups_fusion_runner",
        lambda: network_calls.append,
    )

    result = reddog_bounded_artifact_generation_runtime.FoundupsFusionArtifactGenerationRunner(
        runtime_mode="foundups_fusion",
    ).generate_artifacts(
        prompt="Produce one bounded artifact.",
        context="",
        binding={
            "model_selection": {
                "lead_model": "attacker/model",
                "panel_models": ["attacker/panel"],
                "receipt_id": "forged-selection",
                "model_runtime_binding_receipt_id": "forged-runtime",
            }
        },
        timeout_seconds=30,
    )

    assert result.ok is False
    assert FAIL_MODEL_RUNTIME_BINDING_RECEIPT in result.rejection_reasons
    assert network_calls == []


def _retargeted_model_capability():
    selection, runtime_binding = model_selection_and_runtime_binding_receipts(
        runtime_surface=RUNTIME_SURFACE_ARTIFACT_GENERATION,
        task_family=TASK_FAMILY,
    )
    verification = verified_runtime_binding_receipt(runtime_binding)
    assert verification is not None
    invocation_binding = {
        "model_selection": {
            "lead_model": "attacker/unverified-model",
            "panel_models": [],
            "receipt_id": selection["receipt_id"],
            "model_runtime_binding_receipt_id": runtime_binding["receipt_id"],
            "model_runtime_binding_verification_receipt_id": (
                verification.receipt_id
            ),
            "model_runtime_binding_verification_digest": (
                verification_receipt_digest(verification)
            ),
        }
    }
    verified_capability = model_runtime_binding_test_capability(
        selection,
        runtime_binding,
    )
    assert verified_capability is not None
    forged = admission_capability._issue_artifact_generation_model(
        invocation_binding=invocation_binding,
        runtime_binding=runtime_binding,
        selection=selection,
        verification=verification,
        verified_capability=verified_capability,
    )
    return forged, verified_capability


def test_verified_capability_cannot_retarget_provider_topology(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forged, verified_capability = _retargeted_model_capability()
    network_calls: list[object] = []
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        reddog_bounded_artifact_generation_runtime,
        "_load_foundups_fusion_runner",
        lambda: network_calls.append,
    )

    result = reddog_bounded_artifact_generation_runtime.FoundupsFusionArtifactGenerationRunner(
        runtime_mode="foundups_fusion",
    ).generate_artifacts(
        prompt="Produce one bounded artifact.",
        context="",
        binding=forged,
        timeout_seconds=30,
    )

    assert result.ok is False
    assert FAIL_MODEL_RUNTIME_BINDING_RECEIPT in result.rejection_reasons
    assert network_calls == []
    discard_verified_runtime_binding_capability(verified_capability)
    assert not hasattr(admission_capability, "REGISTRY")


class _ReplayRunner:
    def __init__(self) -> None:
        self.results: list[ArtifactGenerationModelResult] = []

    def generate_artifacts(
        self,
        *,
        prompt: str,
        context: str,
        binding: ArtifactGenerationModelCapability,
        timeout_seconds: int,
    ) -> ArtifactGenerationModelResult:
        runner = (
            reddog_bounded_artifact_generation_runtime.
            FoundupsFusionArtifactGenerationRunner(
                runtime_mode="foundups_fusion",
            )
        )
        token = object.__getattribute__(
            binding, "_ArtifactGenerationModelCapability__token"
        )
        copied = ArtifactGenerationModelCapability(token)
        for candidate in (copied, binding, binding):
            self.results.append(
                runner.generate_artifacts(
                    prompt=prompt,
                    context=context,
                    binding=candidate,
                    timeout_seconds=timeout_seconds,
                )
            )
        return self.results[1]


def test_model_capability_is_one_shot_and_cannot_be_copied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request()
    network_calls: list[dict[str, object]] = []

    def fake_fusion(api_key, user_payload, messages, payload):
        network_calls.append(dict(payload))
        return {
            "ok": True,
            "content": (
                '{"artifact_contents":{'
                '"modules/foundups/paccess_001/README.md":"# pAccess\\n"}}'
            ),
        }

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        reddog_bounded_artifact_generation_runtime,
        "_load_foundups_fusion_runner",
        lambda: fake_fusion,
    )
    runner = _ReplayRunner()
    result = _generate(request, runner=runner)
    copied_result, accepted, replayed = runner.results

    assert result.accepted is True
    assert copied_result.ok is False
    assert accepted.ok is True
    assert replayed.ok is False
    assert len(network_calls) == 1


def test_artifact_capabilities_keep_trusted_state_in_registry() -> None:
    request = _request()
    authority = _issue_artifact_generation_authority(request)
    assert authority is not None
    assert not hasattr(authority, "request_digest")
    with pytest.raises(AttributeError):
        object.__setattr__(authority, "request_digest", "sha256:changed")
    assert consume_artifact_generation_authority(authority, request) is True


def test_model_handle_has_no_mutable_provider_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_calls: list[dict[str, object]] = []

    class ForwardingRunner:
        def generate_artifacts(self, *, prompt, context, binding, timeout_seconds):
            assert not hasattr(binding, "binding_json")
            with pytest.raises(AttributeError):
                object.__setattr__(binding, "binding_json", '{"model_selection":{}}')
            return (
                reddog_bounded_artifact_generation_runtime.
                FoundupsFusionArtifactGenerationRunner(
                    runtime_mode="foundups_fusion",
                ).generate_artifacts(
                    prompt=prompt,
                    context=context,
                    binding=binding,
                    timeout_seconds=timeout_seconds,
                )
            )

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        reddog_bounded_artifact_generation_runtime,
        "_load_foundups_fusion_runner",
        lambda: _successful_fusion(provider_calls),
    )
    result = _generate(_request(), runner=ForwardingRunner())
    assert result.accepted is True, result.rejection_reasons
    assert len(provider_calls) == 1
    assert provider_calls[0]["lead_model"] == "openai/gpt-5.6-code"


def _successful_fusion(calls):
    def run(_api_key, _payload, _messages, options):
        calls.append(dict(options))
        return {
            "ok": True,
            "content": (
                '{"artifact_contents":{'
                f'"{ARTIFACT}":"# generated\\n"'
                "}}"
            ),
            "review_packet": {"receipt_id": "review:identity"},
        }

    return run
