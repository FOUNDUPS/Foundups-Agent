"""Tests for REDDOG_BOUNDED_ARTIFACT_GENERATION_BINDING_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_gateway.src.model_intelligence_catalog import (
    Availability,
    ModelCapabilityCard,
    PromotionState,
    build_model_catalog_snapshot,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    build_model_benchmark_evidence_receipt,
    build_model_promotion_evidence_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import (
    ModelTaskRequirements,
    SelectionMode,
    SelectionPurpose,
    select_models_for_task,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    VerifiedModelProductionEvidence,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    canonical_model_runtime_binding_digest,
    verification_receipt_digest,
    verified_runtime_binding_receipt,
)
from modules.ai_intelligence.ai_gateway.tests.model_signed_evidence_test_helpers import (
    make_verified_production_evidence,
)
from modules.communication.moltbot_bridge.src.reddog_bounded_artifact_generation_runtime import (
    ARTIFACT_GENERATION_ACCEPT,
    ARTIFACT_GENERATION_REJECT,
    FAIL_ARTIFACTS_MISMATCH,
    FAIL_AUTHORITY,
    FAIL_CONTENT_INVALID,
    FAIL_EXPLICIT_REQUEST,
    FAIL_HOLOINDEX_EVIDENCE,
    FAIL_MODEL_RUNTIME_BINDING_RECEIPT,
    FAIL_PLANNED_ARTIFACTS,
    FAIL_RECEIPT_CHAIN,
    FAIL_RUNNER_MISSING,
    FAIL_RUNNER_REJECTED,
    FAIL_SECRET_IN_CONTENT,
    ArtifactGenerationModelResult,
    RUNTIME_SURFACE_ARTIFACT_GENERATION,
    generate_bounded_artifact_contents,
)
from modules.communication.moltbot_bridge.src import reddog_bounded_artifact_generation_runtime
from modules.communication.moltbot_bridge.src.reddog_artifact_generation_admission_capability import (
    ArtifactGenerationModelCapability,
    _issue_artifact_generation_authority,
    consume_artifact_generation_model,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_runtime_binding_test_capability,
    model_selection_and_runtime_binding_receipts,
    model_runtime_binding_receipt,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_bounded_artifact_generation_runtime.py"
)
ARTIFACT = "modules/foundups/paccess_001/README.md"
TASK_FAMILY = "artifact_generation"


class FakeRunner:
    def __init__(
        self,
        *,
        artifact_contents: dict[str, str] | None = None,
        ok: bool = True,
        rejection_reasons: tuple[str, ...] = (),
    ) -> None:
        self.artifact_contents = artifact_contents or {ARTIFACT: "# pAccess\n"}
        self.ok = ok
        self.rejection_reasons = rejection_reasons
        self.calls: list[dict[str, object]] = []

    def generate_artifacts(
        self,
        *,
        prompt: str,
        context: str,
        binding: ArtifactGenerationModelCapability,
        timeout_seconds: int,
    ) -> ArtifactGenerationModelResult:
        verified_binding = consume_artifact_generation_model(binding)
        self.calls.append(
            {
                "prompt": prompt,
                "context": context,
                "binding": verified_binding or {},
                "timeout_seconds": timeout_seconds,
            }
        )
        return ArtifactGenerationModelResult(
            ok=self.ok,
            status="MODEL_OK" if self.ok else "MODEL_REJECTED",
            artifact_contents=self.artifact_contents,
            model_receipt_id="model-receipt-1" if self.ok else None,
            model_result_digest="sha256:" + ("1" * 64),
            made_network_call=False,
            rejection_reasons=self.rejection_reasons,
        )


def _request(**overrides: object) -> dict[str, object]:
    selection, runtime_binding = model_selection_and_runtime_binding_receipts(
        runtime_surface=RUNTIME_SURFACE_ARTIFACT_GENERATION,
        task_family=TASK_FAMILY,
    )
    verification = verified_runtime_binding_receipt(runtime_binding)
    assert verification is not None
    payload = {
        "explicit_artifact_generation_requested": True,
        "work_order_id": "work-order-1",
        "slice_name": "REDDOG_TEST_ARTIFACT_GENERATION_PHASE1",
        "task_summary": "Generate one bounded README artifact.",
        "planned_artifacts": [ARTIFACT],
        "evidence_context": "Direct-read evidence says create a README only.",
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
            "model_runtime_binding_verification_receipt_id": (
                verification.receipt_id
            ),
            "model_runtime_binding_verification_digest": (
                verification_receipt_digest(verification)
            ),
        },
        "signed_receipt_chain": {"accepted": True, "terminal_receipt_hash": "sha256:chain"},
        "model_selection_receipt": selection,
        "model_runtime_binding_receipt": runtime_binding,
        "timeout_seconds": 30,
    }
    payload.update(overrides)
    return payload


def _mapping_digest(value: dict[str, object]) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _generate(
    request: dict[str, object],
    *,
    runner: FakeRunner | None,
):
    authority = _issue_artifact_generation_authority(request)
    capability = model_runtime_binding_test_capability(
        request.get("model_selection_receipt") or {},
        request.get("model_runtime_binding_receipt") or {},
    )
    return generate_bounded_artifact_contents(
        request,
        runner=runner,
        authority_capability=authority,
        model_runtime_binding_capability=capability,
    )


def _runtime_receipt_id(value: dict[str, object]) -> str:
    body = {
        key: item
        for key, item in value.items()
        if key not in {"receipt_id", "verification_receipt"}
    }
    encoded = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "reddog_model_runtime_binding:" + hashlib.sha256(encoded).hexdigest()


def _model_selection_receipt(
    *,
    selection_mode: SelectionMode = SelectionMode.SINGLE,
    model_ids: tuple[str, ...] = ("openai/gpt-5.6-code",),
) -> dict[str, object]:
    entries = []
    snapshot = build_model_catalog_snapshot(
        tuple(
            ModelCapabilityCard(
                provider=model_id.split("/", 1)[0],
                model_id=model_id,
                canonical_model_id=model_id,
                source="test",
                availability=Availability.AVAILABLE,
                promotion_state=PromotionState.CHAMPION,
                task_families=(TASK_FAMILY,),
                supports_structured_output=True,
                supports_reasoning=True,
                verifier_pass_rate=1.0,
                benchmark_scores={TASK_FAMILY: 1.0 - (index * 0.1)},
            ).normalized()
            for index, model_id in enumerate(model_ids)
        ),
        generated_at="2026-07-16T00:00:00+00:00",
    )
    for index, model_id in enumerate(model_ids):
        benchmark = build_model_benchmark_evidence_receipt(
            model_id=model_id,
            task_family=TASK_FAMILY,
            task_set_digest=f"sha256:task-set-{index}",
            held_out_split_digest=f"sha256:held-out-{index}",
            prompt_topology_digest=f"sha256:topology-{index}",
            verifier_digest=f"sha256:verifier-{index}",
            verifier_receipt_id=f"sha256:verifier-receipt-{index}",
            sample_count=10,
            accepted_count=10,
        )
        promotion = build_model_promotion_evidence_receipt(
            benchmark_receipt=benchmark,
            promotion_state=PromotionState.CHAMPION,
            promotion_authority_receipt_id=f"sha256:promotion-authority-{index}",
            signed_promotion_receipt_id=f"signature:promotion-{index}",
            min_verifier_pass_rate=0.8,
        )
        entries.extend(
            make_verified_production_evidence(
                benchmark,
                promotion,
                catalog_snapshot_id=snapshot.snapshot_id,
            ).entries
        )
    receipt = select_models_for_task(
        snapshot,
        ModelTaskRequirements(
            task_family=TASK_FAMILY,
            purpose=SelectionPurpose.PRODUCTION,
            selection_mode=selection_mode,
            max_candidates=len(model_ids),
            require_structured_output=True,
            require_reasoning=True,
            min_verifier_pass_rate=0.8,
            panel_roles=("principal", "critic", "implementer", "researcher"),
        ),
        production_evidence=VerifiedModelProductionEvidence(entries=tuple(entries)),
    )
    assert receipt.selected_model_ids
    return receipt.to_dict()


def test_valid_generation_returns_exact_bounded_artifacts() -> None:
    runner = FakeRunner()
    request = _request()

    result = _generate(request, runner=runner)

    assert result.decision == ARTIFACT_GENERATION_ACCEPT
    assert result.accepted is True
    assert result.rejection_reasons == []
    assert result.artifact_contents == {ARTIFACT: "# pAccess\n"}
    assert result.receipt.accepted is True
    assert result.receipt.planned_artifacts == [ARTIFACT]
    assert result.receipt.no_file_write_performed is True
    assert result.no_shell_command_executed is True
    assert result.receipt.model_selection_digest == _mapping_digest(
        request["model_selection_receipt"]
    )
    assert result.receipt.model_runtime_binding_digest == canonical_model_runtime_binding_digest(
        request["model_runtime_binding_receipt"]
    )
    assert runner.calls
    assert runner.calls[0]["binding"]["work_order_id"] == "work-order-1"


def test_raw_model_selection_without_runtime_binding_rejects_before_runner() -> None:
    selection = _model_selection_receipt()
    runner = FakeRunner()

    result = _generate(
        _request(
            model_runtime_binding_receipt=None,
            model_selection_receipt=selection,
        ),
        runner=runner,
    )

    assert result.accepted is False
    assert FAIL_MODEL_RUNTIME_BINDING_RECEIPT in result.rejection_reasons
    assert runner.calls == []


def test_model_runtime_binding_receipt_is_bound_into_artifact_runner_call() -> None:
    request = _request()
    runtime_binding = request["model_runtime_binding_receipt"]
    runner = FakeRunner()

    result = _generate(
        request,
        runner=runner,
    )

    assert result.accepted is True
    binding = runner.calls[0]["binding"]["model_selection"]
    assert binding["model_runtime_binding_receipt_id"] == runtime_binding["receipt_id"]
    assert binding["lead_model"] == "openai/gpt-5.6-code"
    assert result.receipt.model_runtime_binding_receipt_id == runtime_binding["receipt_id"]
    assert result.receipt.model_runtime_binding_digest


def test_mismatched_model_runtime_binding_receipt_rejects_before_artifact_runner() -> None:
    runtime_binding = model_runtime_binding_receipt(runtime_surface="wrong_surface")
    runner = FakeRunner()

    result = _generate(
        _request(model_runtime_binding_receipt=runtime_binding),
        runner=runner,
    )

    assert result.decision == ARTIFACT_GENERATION_REJECT
    assert FAIL_MODEL_RUNTIME_BINDING_RECEIPT in result.rejection_reasons
    assert runner.calls == []


def test_tampered_model_selection_lineage_rejects_before_runner() -> None:
    selection = dict(_request()["model_selection_receipt"])
    selection["selected_model_ids"] = ["attacker/model"]
    runner = FakeRunner()

    result = _generate(
        _request(model_selection_receipt=selection),
        runner=runner,
    )

    assert result.decision == ARTIFACT_GENERATION_REJECT
    assert FAIL_MODEL_RUNTIME_BINDING_RECEIPT in result.rejection_reasons
    assert runner.calls == []


def test_foundups_fusion_runner_loader_resolves_repo_bridge() -> None:
    runner = reddog_bounded_artifact_generation_runtime._load_foundups_fusion_runner()

    assert callable(runner)
    assert runner.__name__ == "_run_foundups_fusion"


def test_foundups_fusion_runner_uses_model_selection_topology(monkeypatch: pytest.MonkeyPatch) -> None:
    selection, runtime_binding = model_selection_and_runtime_binding_receipts(
        runtime_surface=RUNTIME_SURFACE_ARTIFACT_GENERATION,
        task_family=TASK_FAMILY,
        panel_model_ids=("anthropic/claude-opus-5",),
    )
    request = _request()
    verification = verified_runtime_binding_receipt(runtime_binding)
    assert verification is not None
    request["model_selection_receipt"] = selection
    request["model_runtime_binding_receipt"] = runtime_binding
    request["signed_authority"] = {
        **dict(request["signed_authority"]),
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
        }
    calls: list[dict[str, object]] = []

    def fake_fusion(api_key, user_payload, messages, payload):
        calls.append(dict(payload))
        return {
            "ok": True,
            "content": '{"artifact_contents":{"modules/foundups/paccess_001/README.md":"# pAccess\\n"}}',
            "review_packet": {"receipt_id": "fusion-receipt-1"},
        }

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(reddog_bounded_artifact_generation_runtime, "_load_foundups_fusion_runner", lambda: fake_fusion)

    gate = _generate(
        request,
        runner=reddog_bounded_artifact_generation_runtime.FoundupsFusionArtifactGenerationRunner(
            runtime_mode="foundups_fusion",
        ),
    )

    assert gate.accepted is True
    assert gate.model_result is not None and gate.model_result.ok is True
    assert calls[0]["lead_model"] == "openai/gpt-5.6-code"
    assert calls[0]["panel_models"] == ["anthropic/claude-opus-5"]
    assert calls[0]["bridge_meta"]["model_selection_receipt_id"] == selection["receipt_id"]
    assert (
        calls[0]["bridge_meta"][
            "model_runtime_binding_verification_receipt_id"
        ]
        == verification.receipt_id
    )
    assert (
        gate.receipt.model_runtime_binding_verification_receipt_id
        == verification.receipt_id
    )


def test_missing_explicit_request_rejects_before_runner() -> None:
    runner = FakeRunner()

    result = _generate(
        _request(explicit_artifact_generation_requested=False),
        runner=runner,
    )

    assert result.decision == ARTIFACT_GENERATION_REJECT
    assert FAIL_EXPLICIT_REQUEST in result.rejection_reasons
    assert runner.calls == []


def test_missing_runner_rejects_fail_closed() -> None:
    result = _generate(_request(), runner=None)

    assert result.decision == ARTIFACT_GENERATION_REJECT
    assert FAIL_RUNNER_MISSING in result.rejection_reasons


def test_holoindex_index_gap_blocks_generation_before_runner() -> None:
    runner = FakeRunner()

    result = _generate(
        _request(holoindex_evidence={"index_gap_detected": True, "retrieval_quality": "INDEX_GAP"}),
        runner=runner,
    )

    assert FAIL_HOLOINDEX_EVIDENCE in result.rejection_reasons
    assert runner.calls == []


def test_authority_and_receipt_chain_are_required_before_runner() -> None:
    runner = FakeRunner()

    result = _generate(
        _request(signed_authority={"accepted": False}, signed_receipt_chain={}),
        runner=runner,
    )

    assert FAIL_AUTHORITY in result.rejection_reasons
    assert FAIL_RECEIPT_CHAIN in result.rejection_reasons
    assert runner.calls == []


def test_runner_rejection_blocks_artifacts() -> None:
    result = _generate(
        _request(),
        runner=FakeRunner(ok=False, rejection_reasons=("model_quorum_failed",)),
    )

    assert result.decision == ARTIFACT_GENERATION_REJECT
    assert FAIL_RUNNER_REJECTED in result.rejection_reasons
    assert "model_quorum_failed" in result.rejection_reasons
    assert result.artifact_contents == {}


def test_extra_or_missing_artifact_path_rejects() -> None:
    result = _generate(
        _request(),
        runner=FakeRunner(artifact_contents={ARTIFACT: "ok", "modules/foundups/paccess_001/EXTRA.md": "bad"}),
    )

    assert FAIL_ARTIFACTS_MISMATCH in result.rejection_reasons
    assert result.accepted is False


def test_invalid_planned_artifact_path_rejects_before_runner() -> None:
    runner = FakeRunner()

    result = _generate(
        _request(planned_artifacts=[ARTIFACT, "../escape.md"]),
        runner=runner,
    )

    assert FAIL_PLANNED_ARTIFACTS in result.rejection_reasons
    assert runner.calls == []


def test_secret_marker_and_nul_content_reject() -> None:
    result = _generate(
        _request(),
        runner=FakeRunner(artifact_contents={ARTIFACT: "token=abc\x00"}),
    )

    assert FAIL_SECRET_IN_CONTENT in result.rejection_reasons
    assert FAIL_CONTENT_INVALID in result.rejection_reasons


def test_module_has_no_filesystem_shell_github_pr_or_holoindex_mutation() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "holo_index",
        "git",
    }
    banned_import_fragments = {
        "worktree_pr_runner",
        "reddog_wre_worktree_runner",
        "openclaw_supervisor",
        "hermes_job_executor",
        "pattern_memory",
    }
    banned_calls = {"eval", "exec", "compile", "__import__", "open"}
    banned_attrs = {
        "write_text",
        "write_bytes",
        "unlink",
        "remove",
        "rmdir",
        "rename",
        "system",
        "popen",
        "spawn",
        "run",
        "Popen",
        "check_call",
        "check_output",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
                assert all(fragment not in alias.name for fragment in banned_import_fragments)
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
            assert all(fragment not in node.module for fragment in banned_import_fragments)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs

    for token in (
        "holo_index.py --index",
        "create_pull_request",
        "merge_performed=True",
        "settle_reward",
        "PatternMemory(",
    ):
        assert token not in source
