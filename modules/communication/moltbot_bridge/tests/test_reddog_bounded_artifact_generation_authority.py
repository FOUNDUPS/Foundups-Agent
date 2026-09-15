"""Authority-bound model tests for bounded artifact generation."""

from __future__ import annotations

import copy
import pickle
from types import SimpleNamespace

import pytest
from prompt.swarm.m2m_compiler import encode_m2m_envelope

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
    reddog_foundups_fusion_artifact_provider as fusion_provider,
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
    _m2m_context,
    _m2m_envelope,
    _mapping_digest,
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
        trusted_now_epoch=lambda: 1_800_000_000,
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
        trusted_now_epoch=lambda: 1_800_000_000,
    )
    accepted = generate_bounded_artifact_contents(
        request,
        runner=runner,
        authority_capability=original,
        model_runtime_binding_capability=model_runtime_binding_test_capability(
            request["model_selection_receipt"],
            request["model_runtime_binding_receipt"],
        ),
        trusted_now_epoch=lambda: 1_800_000_000,
    )
    replayed = generate_bounded_artifact_contents(
        request,
        runner=runner,
        authority_capability=original,
        model_runtime_binding_capability=model_runtime_binding_test_capability(
            request["model_selection_receipt"],
            request["model_runtime_binding_receipt"],
        ),
        trusted_now_epoch=lambda: 1_800_000_000,
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


def test_unavailable_resolved_provider_rejects_before_runner() -> None:
    class OpenAiOnlyRunner(FakeRunner):
        available_model_providers = ("openai",)

    runner = OpenAiOnlyRunner()
    result = _generate(_request(), runner=runner)

    assert FAIL_MODEL_RUNTIME_BINDING_RECEIPT in result.rejection_reasons
    assert runner.calls == []


def test_expired_resolved_topology_rejects_before_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request()
    authority = _issue_artifact_generation_authority(request)
    capability = model_runtime_binding_test_capability(
        request["model_selection_receipt"], request["model_runtime_binding_receipt"]
    )
    ticks = iter((1_800_000_000, 1_800_000_061))
    network_calls: list[dict[str, object]] = []
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        reddog_bounded_artifact_generation_runtime,
        "_load_foundups_fusion_runner",
        lambda: _successful_fusion(network_calls),
    )

    result = generate_bounded_artifact_contents(
        request,
        runner=reddog_bounded_artifact_generation_runtime.
        FoundupsFusionArtifactGenerationRunner(runtime_mode="foundups_fusion"),
        authority_capability=authority,
        model_runtime_binding_capability=capability,
        trusted_now_epoch=lambda: next(ticks),
    )

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
    available_model_providers = ("openai", "openrouter")

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


@pytest.mark.parametrize("canonical", [False, True])
def test_model_capability_is_one_shot_and_cannot_be_copied(
    monkeypatch: pytest.MonkeyPatch,
    canonical: bool,
) -> None:
    request = _request()
    if canonical:
        request["m2m_envelope"] = _m2m_envelope()
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
        available_model_providers = ("openai", "openrouter")

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


@pytest.mark.parametrize("envelope", [
    None, {}, [], False, "", {"ROLE": "worker"}, "invalid_ref", "opaque_input",
])
def test_m2m_malformed_request_rejects_before_model_capability(monkeypatch, envelope):
    if envelope == "invalid_ref":
        envelope = _m2m_envelope() | {"R": [True]}
    elif envelope == "opaque_input":
        envelope = _m2m_envelope() | {"I": {"opaque": object()}}
    effects, runner = [], FakeRunner()

    def forbidden_issue(**kwargs):
        effects.append("model_capability")
        pytest.fail("malformed envelope reached model capability issuance")

    monkeypatch.setattr(reddog_bounded_artifact_generation_runtime, "_issue_artifact_generation_model", forbidden_issue)
    result = _generate(_request(m2m_envelope=envelope), runner=runner)
    assert result.accepted is False
    assert "FAIL_ARTIFACT_GENERATION_M2M_ENVELOPE" in result.rejection_reasons
    assert runner.calls == effects == []


@pytest.mark.parametrize("payload_field,offset", [
    ("evidence_context", -1), ("evidence_context", 0), ("evidence_context", 1), ("packet_action", 1000),
])
def test_m2m_combined_prompt_context_budget_is_exact(monkeypatch, payload_field, offset):
    request = _request(m2m_envelope=_m2m_envelope(), evidence_context="")
    wire = encode_m2m_envelope(request["m2m_envelope"])
    padding = "x" * (24_000 - len(wire) - len(_m2m_context(request)) + offset)
    if payload_field == "packet_action":
        request["m2m_envelope"]["A"] += padding
        wire = encode_m2m_envelope(request["m2m_envelope"])
        assert len(wire) > 24_000  # Codec-valid packet alone exceeds the transport budget.
    else:
        request["evidence_context"] = padding
    assert len(wire) + len(_m2m_context(request)) == 24_000 + offset
    runner, effects = FakeRunner(), []

    def forbidden_issue(**kwargs):
        effects.append("model_capability")
        pytest.fail("oversized canonical prompt/context reached model capability issuance")

    if offset > 0:
        monkeypatch.setattr(reddog_bounded_artifact_generation_runtime, "_issue_artifact_generation_model", forbidden_issue)
    result = _generate(request, runner=runner)
    assert result.accepted is (offset <= 0), result.rejection_reasons
    if offset <= 0:
        assert runner.calls[0]["prompt"] == wire
        assert len(runner.calls[0]["prompt"]) + len(runner.calls[0]["context"]) == 24_000 + offset
    else:
        assert "FAIL_ARTIFACT_GENERATION_MODEL_OUTPUT" in result.rejection_reasons
        assert runner.calls == effects == []


@pytest.mark.parametrize("mutation", ["add", "remove", "action", "nested_type", "tuple_repair"])
def test_m2m_request_mutation_invalidates_existing_authority(mutation):
    request = _request()
    if mutation != "add":
        request["m2m_envelope"] = _m2m_envelope()
    if mutation == "tuple_repair":
        request["m2m_envelope"]["I"]["values"] = (True, 1)
    authority = _issue_artifact_generation_authority(request)
    if mutation == "tuple_repair":
        digest = _mapping_digest(request)
        rejected = generate_bounded_artifact_contents(request, runner=FakeRunner(), authority_capability=authority)
        assert "FAIL_ARTIFACT_GENERATION_M2M_ENVELOPE" in rejected.rejection_reasons
        request["m2m_envelope"]["I"]["values"] = [True, 1]
        assert _mapping_digest(request) == digest
    elif mutation == "add":
        request["m2m_envelope"] = _m2m_envelope()
    elif mutation == "remove":
        del request["m2m_envelope"]
    elif mutation == "action":
        request["m2m_envelope"]["A"] = "Changed after request authority issuance"
    else:
        request["m2m_envelope"]["I"]["context"]["checks"][0] = 1
    runner = FakeRunner()
    capability = model_runtime_binding_test_capability(request["model_selection_receipt"], request["model_runtime_binding_receipt"])
    try:
        result = generate_bounded_artifact_contents(
            request, runner=runner, authority_capability=authority,
            model_runtime_binding_capability=capability, trusted_now_epoch=lambda: 1_800_000_000,
        )
    finally:
        discard_verified_runtime_binding_capability(capability)
    assert FAIL_AUTHORITY in result.rejection_reasons
    assert result.accepted is False and runner.calls == []


@pytest.mark.parametrize("mutation_point", ["validation", "provider_inventory"])
def test_m2m_request_snapshot_survives_validation_and_inventory_callbacks(mutation_point):
    class ChangingRequest(dict):
        def get(self, key, default=None):
            if key == "signed_authority":
                self["m2m_envelope"]["A"] = "Changed after request authority consumption"
            return super().get(key, default)

    request = _request(m2m_envelope=_m2m_envelope())
    if mutation_point == "validation":
        request = ChangingRequest(request)
    admitted_wire = encode_m2m_envelope(request["m2m_envelope"])

    class InventoryCallbackRunner(FakeRunner):
        @property
        def available_model_providers(self):
            if mutation_point == "provider_inventory":
                request.pop("m2m_envelope", None)
            return ("openai", "openrouter")

    runner = InventoryCallbackRunner()
    result = _generate(request, runner=runner)
    assert result.accepted is True, result.rejection_reasons
    assert len(runner.calls) == 1
    assert runner.calls[0]["prompt"] == admitted_wire
    assert runner.calls[0]["binding"]["prompt_schema"] == "0102_m2m_v1"
    assert runner.calls[0]["binding"]["m2m_prompt_digest"] == _mapping_digest(admitted_wire)


class _M2MFusionForwarder:
    available_model_providers = ("openai", "openrouter")

    def __init__(self, wire, variant):
        self.wire, self.variant = wire, variant

    def generate_artifacts(self, *, prompt, context, binding, timeout_seconds):
        supplied = self.wire
        if self.variant in {"supplied", "restored"}:
            supplied = encode_m2m_envelope(_m2m_envelope() | {"A": "Changed in transit"})
        elif self.variant in {"noncanonical", "noncanonical_bound"}:
            supplied += " "
        return fusion_provider.FoundupsFusionArtifactGenerationRunner(
            runtime_mode="foundups_fusion", available_model_providers=("openrouter",),
        ).generate_artifacts(prompt=supplied, context=context, binding=binding, timeout_seconds=timeout_seconds)


def _m2m_fusion_contract_probe(monkeypatch, wire, variant, effects):
    issue = reddog_bounded_artifact_generation_runtime._issue_artifact_generation_model

    def sealed_issue(**kwargs):
        # Isolate provider validation with a real disposable opaque capability.
        bound = dict(kwargs["invocation_binding"], prompt_schema="0102_m2m_v1", m2m_prompt_digest=_mapping_digest(wire))
        if variant in {"missing_schema", "missing_both"}:
            del bound["prompt_schema"]
        if variant in {"missing_digest", "missing_both"}:
            del bound["m2m_prompt_digest"]
        if variant == "noncanonical_bound":
            bound["m2m_prompt_digest"] = _mapping_digest(wire + " ")
        kwargs["invocation_binding"] = bound
        return issue(**kwargs)

    def gate(prompt, context, **kwargs):
        redacted = prompt.replace("Update only", "Changed only") if variant == "redacted" else prompt
        if variant == "restored":
            redacted = wire
        return SimpleNamespace(status=fusion_provider.REDACTION_GATE_PASSED, redacted_prompt=redacted, redacted_context=context)

    def loader():
        effects.append("loader")
        return _successful_fusion(effects)

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(reddog_bounded_artifact_generation_runtime, "_issue_artifact_generation_model", sealed_issue)
    monkeypatch.setattr(reddog_bounded_artifact_generation_runtime, "_load_foundups_fusion_runner", loader)
    monkeypatch.setattr(fusion_provider, "evaluate_redaction_gate", gate)


@pytest.mark.parametrize("variant", [
    "intact", "supplied", "redacted", "restored", "noncanonical", "noncanonical_bound",
    "missing_schema", "missing_digest", "missing_both",
])
def test_m2m_fusion_preservation_rejects_before_loader_or_provider(monkeypatch, variant):
    envelope, effects = _m2m_envelope(), []
    wire = encode_m2m_envelope(envelope)
    _m2m_fusion_contract_probe(monkeypatch, wire, variant, effects)
    result = _generate(_request(m2m_envelope=envelope), runner=_M2MFusionForwarder(wire, variant))
    assert result.accepted is (variant == "intact"), result.rejection_reasons
    if variant == "intact":
        assert effects[0] == "loader" and len(effects) == 2
    else:
        assert "FAIL_ARTIFACT_GENERATION_M2M_PROMPT_BINDING" in result.rejection_reasons
        assert effects == []
        assert result.model_result.made_network_call is False
        assert result.provider_invocation_performed is False
