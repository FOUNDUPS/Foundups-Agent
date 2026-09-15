"""Model-authority tests for the resident bounded-worker stage."""

from __future__ import annotations

from pathlib import Path
from copy import deepcopy

import pytest

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    canonical_model_runtime_binding_digest,
    verification_receipt_digest,
    verified_runtime_binding_receipt,
)
from modules.communication.moltbot_bridge.src import (
    reddog_resident_queue_bounded_worker_pilot_handler as pilot_handler_module,
)
from modules.communication.moltbot_bridge.src.reddog_artifact_generation_admission_capability import (
    ArtifactGenerationModelCapability,
)
from modules.communication.moltbot_bridge.src.reddog_bounded_artifact_generation_runtime import (
    ARTIFACT_GENERATION_REJECT,
    ArtifactGenerationModelResult,
    RUNTIME_SURFACE_ARTIFACT_GENERATION,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_bounded_worker_pilot_handler import (
    BOUNDED_WORKER_PILOT_STAGE_KEY,
    FAIL_ARTIFACT_GENERATION_REJECTED,
    FAIL_ARTIFACT_GENERATION_REQUEST_CONFLICT,
    FAIL_ARTIFACT_GENERATOR_MISSING,
    FAIL_MODEL_RUNTIME_VERIFICATION_REJECTED,
    FAIL_MODEL_RUNTIME_VERIFIER_MISSING,
    build_reddog_resident_queue_bounded_worker_pilot_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
    invoke_reddog_resident_queue_next_stage_dispatch,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_BOUNDED_WORKER_PILOT_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_bounded_worker_pilot_invoke import (
    QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_runtime_binding_test_capability,
    model_selection_and_runtime_binding_receipts,
)
from modules.communication.moltbot_bridge.tests.test_reddog_resident_queue_bounded_worker_pilot_handler import (
    ARTIFACT,
    NOW_ISO,
    WORK_ORDER_ID,
    _Resolver,
    _artifact_model_lineage,
    _binding_stage_overrides,
    _mapping_digest,
    _seeded_store,
    _snapshot,
    _valid_bundle,
    _work_order_with_plan,
)


class _ArtifactGenerator:
    available_model_providers = ("openai", "openrouter")

    def __init__(
        self,
        *,
        ok: bool = True,
        artifact_contents: dict[str, str] | None = None,
    ) -> None:
        self.ok = ok
        self.artifact_contents = artifact_contents or {ARTIFACT: "# generated\n"}
        self.calls: list[dict[str, object]] = []

    def generate_artifacts(
        self,
        *,
        prompt: str,
        context: str,
        binding: ArtifactGenerationModelCapability,
        timeout_seconds: int,
    ) -> ArtifactGenerationModelResult:
        self.calls.append(
            {
                "prompt": prompt,
                "context": context,
                "binding": binding,
                "timeout_seconds": timeout_seconds,
            }
        )
        return ArtifactGenerationModelResult(
            ok=self.ok,
            status="MODEL_OK" if self.ok else "MODEL_REJECT",
            artifact_contents=self.artifact_contents if self.ok else {},
            model_receipt_id="artifact-model-receipt-1" if self.ok else None,
            model_result_digest="sha256:" + ("5" * 64),
            made_network_call=False,
            rejection_reasons=() if self.ok else ("model_quorum_failed",),
        )


class _RuntimeBindingVerifier:
    trusted_now_epoch = staticmethod(lambda: 1_800_000_000)

    def __init__(self, *, reject: bool = False) -> None:
        self.reject = reject
        self.calls: list[dict[str, object]] = []

    def verify(self, *, binding: dict, selection: dict):
        self.calls.append({"binding": binding, "selection": selection})
        if self.reject:
            raise ValueError("current_model_authority_rejected")
        return model_runtime_binding_test_capability(selection, binding)


def _dispatch_request() -> ResidentQueueStageDispatchRequest:
    return ResidentQueueStageDispatchRequest(
        stage_key=BOUNDED_WORKER_PILOT_STAGE_KEY,
        next_action=NEXT_QUEUE_BOUNDED_WORKER_PILOT_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )


def _artifact_generation_request(bundle: dict) -> dict[str, object]:
    selection, runtime_binding = model_selection_and_runtime_binding_receipts(
        runtime_surface=RUNTIME_SURFACE_ARTIFACT_GENERATION,
    )
    verification = verified_runtime_binding_receipt(runtime_binding)
    assert verification is not None
    return {
        "explicit_artifact_generation_requested": True,
        "work_order_id": WORK_ORDER_ID,
        "slice_name": "REDDOG_TEST_SLICE_PHASE1",
        "task_summary": "Generate the bounded pilot artifact contents.",
        "planned_artifacts": [ARTIFACT],
        "evidence_context": (
            "The bounded pilot must materialize exactly one README fixture."
        ),
        "holoindex_evidence": {
            "index_gap_detected": False,
            "retrieval_quality": "HIGH",
            "holoindex_freshness_receipt_digest": "sha256:holo-fresh",
        },
        "signed_authority": {
            "accepted": True,
            "signature_gate_digest": "sha256:auth",
            "model_selection_receipt_id": selection["receipt_id"],
            "model_selection_digest": _mapping_digest(selection),
            "model_runtime_binding_receipt_id": runtime_binding["receipt_id"],
            "model_runtime_binding_digest": canonical_model_runtime_binding_digest(
                runtime_binding
            ),
            "model_runtime_binding_verification_receipt_id": verification.receipt_id,
            "model_runtime_binding_verification_digest": (
                verification_receipt_digest(verification)
            ),
        },
        "signed_receipt_chain": {
            "accepted": True,
            "terminal_receipt_hash": "sha256:chain",
        },
        "model_selection_receipt": selection,
        "model_runtime_binding_receipt": runtime_binding,
        "timeout_seconds": 30,
        "worktree_path": str(bundle["worktree"]),
    }


def test_dispatcher_generates_artifacts_before_bounded_worker_pilot(
    tmp_path: Path,
) -> None:
    bundle = _valid_bundle(tmp_path)
    work_order = _work_order_with_plan(bundle)
    chain_store = _seeded_store(bundle, **_binding_stage_overrides(work_order))
    generator = _ArtifactGenerator(
        artifact_contents={ARTIFACT: "# generated by RedDog\n"}
    )
    handler = build_reddog_resident_queue_bounded_worker_pilot_stage_handler(
        chain_results_store=chain_store,
        work_order_resolver=_Resolver(work_order),
        generic_writer_dryrun_result=bundle["generic_writer_dryrun_result"],
        governed_shell_dryrun_result=bundle["governed_shell_dryrun_result"],
        artifact_contents={},
        artifact_generation_request_binding_enabled=True,
        artifact_generator=generator,
        model_runtime_binding_verifier=_RuntimeBindingVerifier(),
        repo_root=bundle["repo_root"],
    )

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={BOUNDED_WORKER_PILOT_STAGE_KEY: handler},
        now_iso=NOW_ISO,
    )

    assert result.accepted is True
    assert generator.calls
    capability = generator.calls[0]["binding"]
    assert isinstance(capability, ArtifactGenerationModelCapability)
    assert not hasattr(capability, "to_dict")
    stage = chain_store.load()["stage_results"][BOUNDED_WORKER_PILOT_STAGE_KEY]
    assert stage["decision"] == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT
    assert stage["artifact_generation_result"]["decision"] != ARTIFACT_GENERATION_REJECT
    assert stage["artifact_generation_result"]["accepted"] is True
    assert (
        bundle["worktree"] / ARTIFACT
    ).read_text(encoding="utf-8") == "# generated by RedDog\n"
    assert not (bundle["repo_root"] / ARTIFACT).exists()


def test_artifact_generation_requires_use_time_model_verifier(
    tmp_path: Path,
) -> None:
    bundle = _valid_bundle(tmp_path)
    work_order = _work_order_with_plan(bundle)
    generator = _ArtifactGenerator()
    handler = build_reddog_resident_queue_bounded_worker_pilot_stage_handler(
        chain_results_store=_seeded_store(bundle, **_binding_stage_overrides(work_order)),
        work_order_resolver=_Resolver(work_order),
        generic_writer_dryrun_result=bundle["generic_writer_dryrun_result"],
        governed_shell_dryrun_result=bundle["governed_shell_dryrun_result"],
        artifact_contents={},
        artifact_generation_request_binding_enabled=True,
        artifact_generator=generator,
        repo_root=bundle["repo_root"],
    )

    result = dict(handler(_dispatch_request()))

    assert FAIL_MODEL_RUNTIME_VERIFIER_MISSING in result["rejection_reasons"]
    assert generator.calls == []


def test_current_model_authority_rejection_blocks_runner(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    work_order = _work_order_with_plan(bundle)
    generator = _ArtifactGenerator()
    handler = build_reddog_resident_queue_bounded_worker_pilot_stage_handler(
        chain_results_store=_seeded_store(bundle, **_binding_stage_overrides(work_order)),
        work_order_resolver=_Resolver(work_order),
        generic_writer_dryrun_result=bundle["generic_writer_dryrun_result"],
        governed_shell_dryrun_result=bundle["governed_shell_dryrun_result"],
        artifact_contents={},
        artifact_generation_request_binding_enabled=True,
        artifact_generator=generator,
        model_runtime_binding_verifier=_RuntimeBindingVerifier(reject=True),
        repo_root=bundle["repo_root"],
    )

    result = dict(handler(_dispatch_request()))

    assert FAIL_MODEL_RUNTIME_VERIFICATION_REJECTED in result["rejection_reasons"]
    assert generator.calls == []


def test_dispatcher_derives_pilot_dryruns_from_chain_state(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    work_order = _work_order_with_plan(bundle)
    chain_store = _seeded_store(bundle, **_binding_stage_overrides(work_order))
    handler = build_reddog_resident_queue_bounded_worker_pilot_stage_handler(
        chain_results_store=chain_store,
        work_order_resolver=_Resolver(work_order),
        generic_writer_dryrun_result=None,
        governed_shell_dryrun_result=None,
        artifact_contents=bundle["artifact_contents"],
        repo_root=bundle["repo_root"],
    )

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={BOUNDED_WORKER_PILOT_STAGE_KEY: handler},
        now_iso=NOW_ISO,
    )

    assert result.accepted is True
    stage = chain_store.load()["stage_results"][BOUNDED_WORKER_PILOT_STAGE_KEY]
    assert stage["decision"] == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT
    binding = stage["pilot_dryrun_binding_result"]
    assert binding["accepted"] is True
    assert binding["generic_writer_dryrun_result"]["accepted"] is True
    assert binding["governed_shell_dryrun_result"]["accepted"] is True
    assert stage["shell_command_executed"] is False
    assert stage["openclaw_enqueue_performed"] is False
    assert stage["hermes_dispatch_performed"] is False
    assert (bundle["worktree"] / ARTIFACT).exists()
    assert not (bundle["repo_root"] / ARTIFACT).exists()


def test_derived_artifact_generation_request_carries_model_selection_receipt(
    tmp_path: Path,
) -> None:
    bundle = _valid_bundle(tmp_path)
    work_order = _work_order_with_plan(bundle)
    model_selection, runtime_binding = _artifact_model_lineage()
    work_order["task_summary"] = "Generate the bounded pilot artifact contents."
    work_order["model_selection_receipt"] = dict(model_selection)
    work_order["model_runtime_binding_receipt"] = dict(runtime_binding)
    stage_results = _seeded_store(
        bundle, **_binding_stage_overrides(work_order)
    ).load()["stage_results"]

    request = pilot_handler_module._derive_artifact_generation_request(
        work_order=work_order,
        stage_results=stage_results,
        repo_root=bundle["repo_root"],
        holoindex_evidence=None,
    )

    assert request["model_selection_receipt"] == model_selection
    assert request["model_runtime_binding_receipt"] == runtime_binding
    assert request["work_order_id"] == WORK_ORDER_ID
    assert request["planned_artifacts"] == [ARTIFACT]


def test_rejected_artifact_generation_blocks_bounded_worker_pilot(
    tmp_path: Path,
) -> None:
    bundle = _valid_bundle(tmp_path)
    work_order = _work_order_with_plan(bundle)
    handler = build_reddog_resident_queue_bounded_worker_pilot_stage_handler(
        chain_results_store=_seeded_store(bundle, **_binding_stage_overrides(work_order)),
        work_order_resolver=_Resolver(work_order),
        generic_writer_dryrun_result=bundle["generic_writer_dryrun_result"],
        governed_shell_dryrun_result=bundle["governed_shell_dryrun_result"],
        artifact_contents={},
        artifact_generation_request_binding_enabled=True,
        artifact_generator=_ArtifactGenerator(ok=False),
        model_runtime_binding_verifier=_RuntimeBindingVerifier(),
        repo_root=bundle["repo_root"],
    )

    result = dict(handler(_dispatch_request()))

    assert result["decision"] == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
    assert FAIL_ARTIFACT_GENERATION_REJECTED in result["rejection_reasons"]
    assert "model_quorum_failed" in result["rejection_reasons"]
    assert result["artifact_generation_result"]["accepted"] is False
    assert not (bundle["worktree"] / ARTIFACT).exists()


def test_artifact_generation_request_requires_explicit_generator(
    tmp_path: Path,
) -> None:
    bundle = _valid_bundle(tmp_path)
    work_order = _work_order_with_plan(bundle)
    handler = build_reddog_resident_queue_bounded_worker_pilot_stage_handler(
        chain_results_store=_seeded_store(bundle, **_binding_stage_overrides(work_order)),
        work_order_resolver=_Resolver(work_order),
        generic_writer_dryrun_result=bundle["generic_writer_dryrun_result"],
        governed_shell_dryrun_result=bundle["governed_shell_dryrun_result"],
        artifact_contents={},
        artifact_generation_request_binding_enabled=True,
        artifact_generator=None,
        repo_root=bundle["repo_root"],
    )

    result = dict(handler(_dispatch_request()))

    assert result["decision"] == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
    assert FAIL_ARTIFACT_GENERATOR_MISSING in result["rejection_reasons"]
    assert not (bundle["worktree"] / ARTIFACT).exists()


def test_caller_supplied_artifact_authority_cannot_replace_durable_stage(
    tmp_path: Path,
) -> None:
    bundle = _valid_bundle(tmp_path)
    work_order = _work_order_with_plan(bundle)
    generator = _ArtifactGenerator()
    attacker_request = _artifact_generation_request(bundle)
    attacker_request["task_summary"] = "Attacker-selected artifact task."
    handler = build_reddog_resident_queue_bounded_worker_pilot_stage_handler(
        chain_results_store=_seeded_store(bundle, **_binding_stage_overrides(work_order)),
        work_order_resolver=_Resolver(work_order),
        generic_writer_dryrun_result=bundle["generic_writer_dryrun_result"],
        governed_shell_dryrun_result=bundle["governed_shell_dryrun_result"],
        artifact_contents={},
        artifact_generation_request=attacker_request,
        artifact_generator=generator,
        model_runtime_binding_verifier=_RuntimeBindingVerifier(),
        repo_root=bundle["repo_root"],
    )

    result = dict(handler(_dispatch_request()))

    assert result["decision"] == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
    assert result["rejection_reasons"] == [
        FAIL_ARTIFACT_GENERATION_REQUEST_CONFLICT
    ]
    assert generator.calls == []
    assert not (bundle["worktree"] / ARTIFACT).exists()


def _assert_generation_preflight_rejects(bundle, work_order, stages, monkeypatch):
    generator = _ArtifactGenerator()
    verifier = _RuntimeBindingVerifier()
    effects = []

    def forbidden_effect(*args, **kwargs):
        effects.append("called")
        raise AssertionError("generation authority or writer reached")

    monkeypatch.setattr(pilot_handler_module, "_issue_artifact_generation_authority", forbidden_effect)
    monkeypatch.setattr(
        pilot_handler_module,
        "invoke_reddog_wre_queue_authorized_bounded_worker_pilot",
        forbidden_effect,
    )
    handler = build_reddog_resident_queue_bounded_worker_pilot_stage_handler(
        chain_results_store=_seeded_store(bundle, **stages),
        work_order_resolver=_Resolver(work_order),
        generic_writer_dryrun_result=bundle["generic_writer_dryrun_result"],
        governed_shell_dryrun_result=bundle["governed_shell_dryrun_result"],
        artifact_contents={},
        artifact_generation_request_binding_enabled=True,
        artifact_generator=generator,
        model_runtime_binding_verifier=verifier,
        repo_root=bundle["repo_root"],
    )
    result = dict(handler(_dispatch_request()))
    assert result["rejection_reasons"] == ["FAIL_ARTIFACT_GENERATION_WORK_ORDER_BINDING"]
    assert verifier.calls == generator.calls == effects == []
    assert not (bundle["worktree"] / ARTIFACT).exists()


@pytest.mark.parametrize("path,value", [
    (("task_summary",), "Changed after admission"),
    (("base_ref",), "changed-base"),
    (("bounded_worker_plan", "planned_artifacts"), ["src/changed.py"]),
    (("bounded_worker_plan", "signed_receipt_chain", "terminal_receipt_hash"), "changed"),
    (("model_runtime_binding_receipt", "principal_model"), "changed-model"),
    (("extra_plan_metadata",), {"ROLE": "worker", "A": "unadmitted action"}),
    (("extra_plan_metadata",), object()),
    (("extra_plan_metadata",), float("nan")),
])
def test_generation_rejects_work_order_changed_after_admission(
    tmp_path, monkeypatch, path, value,
):
    bundle = _valid_bundle(tmp_path)
    work_order = _work_order_with_plan(bundle)
    stages = _binding_stage_overrides(work_order)
    target = work_order
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    _assert_generation_preflight_rejects(bundle, work_order, stages, monkeypatch)


@pytest.mark.parametrize("digest", [None, "", "sha256:invalid", "sha256:" + "0" * 64])
def test_generation_rejects_missing_or_invalid_signed_work_order_digest(
    tmp_path, monkeypatch, digest,
):
    bundle = _valid_bundle(tmp_path)
    work_order = _work_order_with_plan(bundle)
    stages = _binding_stage_overrides(work_order)
    authority = stages["authority_runtime"]["authority_result"]["work_authority"]
    if digest is None:
        del authority["work_order_digest"]
    else:
        authority["work_order_digest"] = digest
    _assert_generation_preflight_rejects(bundle, work_order, stages, monkeypatch)


def test_generation_rejects_cyclic_work_order_before_model_verification(tmp_path, monkeypatch):
    bundle = _valid_bundle(tmp_path)
    work_order = _work_order_with_plan(bundle)
    stages = _binding_stage_overrides(work_order)
    work_order["extra_plan_metadata"] = work_order
    _assert_generation_preflight_rejects(bundle, work_order, stages, monkeypatch)


def test_generation_request_preserves_admitted_nested_snapshot(tmp_path):
    bundle = _valid_bundle(tmp_path)
    work_order = _work_order_with_plan(bundle)
    chain = work_order["bounded_worker_plan"]["signed_receipt_chain"]
    chain["test_metadata"] = {"value": "admitted"}
    stages = _seeded_store(bundle, **_binding_stage_overrides(work_order)).load()["stage_results"]
    handler = build_reddog_resident_queue_bounded_worker_pilot_stage_handler(
        chain_results_store=_seeded_store(bundle),
        work_order_resolver=_Resolver(work_order),
        artifact_generation_request_binding_enabled=True,
        repo_root=bundle["repo_root"],
    )
    request = handler._generation_request(work_order, stages)
    expected = deepcopy(request)
    chain["test_metadata"]["value"] = "changed after derivation"
    assert request == expected
