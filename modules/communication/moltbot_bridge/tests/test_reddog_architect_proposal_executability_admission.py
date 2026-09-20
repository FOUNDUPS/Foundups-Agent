"""Tests for architect proposal validity and execution-readiness admission."""

from __future__ import annotations

import ast
import copy
from dataclasses import replace
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_architect_proposal_admission_contract as proposal_admission,
)
from modules.communication.moltbot_bridge.src.reddog_architect_proposal_executability_admission import (
    ArchitectProposalAdmissionPolicy,
    EFFECT_LIVE_WORKTREE_CANARY,
    LIVE_EXECUTION_CAPABILITIES,
    READINESS_EVIDENCE_BLOCKED,
    READINESS_IMPLEMENTATION_BLOCKED,
    READINESS_PLATFORM_BLOCKED,
    READINESS_READY,
    VALIDITY_NEEDS_RESEARCH,
    VALIDITY_VALID,
    evaluate_architect_proposal_executability,
    reevaluate_architect_proposal_execution_readiness,
    validate_architect_proposal_executability_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ArchitectDeterminationReason,
)
from modules.communication.moltbot_bridge.src.reddog_progressive_execution_stage_policy import (
    DECISION_BOUNDED_EXECUTION_ADMITTED,
    DECISION_WOULD_BLOCK,
    STAGE_BOUNDED_EXECUTION,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)
from modules.communication.moltbot_bridge.tests.test_reddog_backend_architect_determination_runtime import (
    NOW,
    FakeArchitectRunner,
    InMemoryArchitectDeterminationStore,
    _build_inputs,
    _model_output,
    _runtime_kwargs,
    run_reddog_backend_architect_determination_runtime,
)


def _policy(
    *,
    platform: str = "linux",
    available: tuple[str, ...] = LIVE_EXECUTION_CAPABILITIES,
    missing: dict[str, str] | None = None,
) -> ArchitectProposalAdmissionPolicy:
    return ArchitectProposalAdmissionPolicy(
        platform=platform,
        available_capabilities=available,
        missing_capability_reasons=missing or {},
    )


def _evaluate(
    *,
    output_updates: dict | None = None,
    policy: ArchitectProposalAdmissionPolicy | None = None,
    index_gap: bool = False,
    allocation: dict | None = None,
    task_prompt_text: str = "Fix one bounded FoundUp module defect",
):
    inputs = _build_inputs()
    allocation = allocation or inputs["allocation"]
    output = _model_output(
        allocation,
        inputs["reports"][0]["evidence_refs"][0],
    )
    output.update(output_updates or {})
    snapshot = inputs["snapshot"]
    if index_gap:
        snapshot = replace(
            snapshot,
            holoindex_state={
                **snapshot.holoindex_state,
                "freshness_ok": False,
                "rejection_reasons": ("INDEX_GAP",),
            },
        )
    receipt = evaluate_architect_proposal_executability(
        model_output=output,
        snapshot=snapshot,
        reports=inputs["reports"],
        report_bundle_id=inputs["report_collection"].validation.bundle.bundle_id,
        wsp15_allocation_receipt=allocation,
        policy=policy,
        task_prompt_text=task_prompt_text,
        progressive_execution_stage_ceiling=STAGE_BOUNDED_EXECUTION,
    )
    return receipt, inputs, output


def test_production_policy_keeps_sha_only_proposal_receipts_blocked() -> None:
    policy = proposal_admission.current_architect_proposal_admission_policy()

    assert (
        proposal_admission.CAP_PROPOSAL_AUTHENTICITY
        not in policy.available_capabilities
    )
    assert policy.missing_capability_reasons[
        proposal_admission.CAP_PROPOSAL_AUTHENTICITY
    ] == proposal_admission.PROPOSAL_AUTHENTICITY_VERIFIER_MISSING


def test_manifest_trust_controls_are_independent_capabilities() -> None:
    policy = proposal_admission.current_architect_proposal_admission_policy()
    expected = {
        proposal_admission.CAP_MANIFEST_AUTHENTICATED_SELECTION:
            "canonical_signed_runtime_artifact_manifest_selection_verifier_missing",
        proposal_admission.CAP_MANIFEST_DURABLE_REPLAY:
            "canonical_runtime_artifact_manifest_replay_high_water_missing",
        proposal_admission.CAP_MANIFEST_CURRENT_GENERATION:
            "canonical_runtime_artifact_manifest_current_generation_verifier_missing",
    }

    assert {
        capability: policy.missing_capability_reasons[capability]
        for capability in expected
    } == expected
    assert len(expected) == 3


def test_missing_trust_anchor_keeps_proposal_valid_but_blocks_promotion() -> None:
    missing_capability = LIVE_EXECUTION_CAPABILITIES[0]
    receipt, _, _ = _evaluate(
        policy=_policy(
            available=tuple(
                item
                for item in LIVE_EXECUTION_CAPABILITIES
                if item != missing_capability
            ),
            missing={missing_capability: "canonical_trust_anchor_missing"},
        )
    )

    assert receipt.accepted is True
    assert receipt.proposal_validity == VALIDITY_VALID
    assert receipt.execution_readiness == READINESS_IMPLEMENTATION_BLOCKED
    assert receipt.admissible_to_authoritative_queue is False
    assert "canonical_trust_anchor_missing" in receipt.missing_preconditions


def test_slice_producing_missing_capability_does_not_self_authorize() -> None:
    missing_capability = LIVE_EXECUTION_CAPABILITIES[0]
    receipt, _, _ = _evaluate(
        output_updates={"produced_capabilities": [missing_capability]},
        policy=_policy(
            available=tuple(
                item
                for item in LIVE_EXECUTION_CAPABILITIES
                if item != missing_capability
            ),
            missing={missing_capability: "canonical_trust_anchor_missing"},
        ),
    )

    assert receipt.execution_readiness == READINESS_IMPLEMENTATION_BLOCKED
    assert receipt.admissible_to_authoritative_queue is False
    assert any(
        reason.startswith("produced_capability_is_output_not_current_authority:")
        for reason in receipt.decision_reasons
    )


def test_model_supplied_readiness_boolean_has_no_authority() -> None:
    missing_capability = LIVE_EXECUTION_CAPABILITIES[0]
    receipt, _, _ = _evaluate(
        output_updates={"execution_ready": True, "queue_admissible": True},
        policy=_policy(
            available=tuple(
                item
                for item in LIVE_EXECUTION_CAPABILITIES
                if item != missing_capability
            ),
            missing={missing_capability: "canonical_trust_anchor_missing"},
        ),
    )

    assert receipt.execution_readiness == READINESS_IMPLEMENTATION_BLOCKED
    assert receipt.admissible_to_authoritative_queue is False


def test_all_current_capabilities_do_not_override_complexity_ceiling() -> None:
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation="cross-module bounded fix",
        prompt_text="Repair one cross-module data flow.",
        changed_paths=(
            "modules/foundups/demo/src/a.py",
            "modules/foundups/demo/src/b.py",
            "modules/foundups/demo/src/c.py",
        ),
    ).to_dict()
    receipt, _, _ = _evaluate(
        policy=_policy(), allocation=allocation,
        task_prompt_text="Repair one cross-module data flow.",
    )

    assert receipt.proposal_validity == VALIDITY_VALID
    assert receipt.execution_readiness == READINESS_READY
    assert receipt.admissible_to_authoritative_queue is False
    assert receipt.progressive_policy_decision == DECISION_WOULD_BLOCK
    rehydrated = validate_architect_proposal_executability_receipt(
        receipt.to_dict()
    )
    assert (
        reevaluate_architect_proposal_execution_readiness(
            rehydrated,
            policy=_policy(),
        )
        == ()
    )
    assert validate_architect_proposal_executability_receipt(
        receipt.to_dict()
    ) == receipt


def test_index_gap_blocks_arbitrary_repository_change() -> None:
    receipt, _, _ = _evaluate(policy=_policy(), index_gap=True)

    assert receipt.accepted is True
    assert receipt.execution_readiness == READINESS_EVIDENCE_BLOCKED
    assert receipt.admissible_to_authoritative_queue is False
    assert "holoindex_index_gap" in receipt.missing_preconditions


def test_index_gap_allows_only_direct_read_grounded_holo_maintenance() -> None:
    inputs = _build_inputs()
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation="holoindex_maintenance",
        prompt_text="Repair one cross-module retrieval path.",
        changed_paths=("holo_index/query_owner.py",),
    ).to_dict()
    reports = [dict(report) for report in inputs["reports"]]
    reports[0] = {
        **reports[0],
        "evidence_refs": ["file:holo_index/query_owner.py:sha256:test:lines:1"],
        "findings": [
            {
                **reports[0]["findings"][0],
                "next_slice_name": "HOLOINDEX_OWNER_REPAIR_PHASE1",
                "evidence_refs": [
                    "file:holo_index/query_owner.py:sha256:test:lines:1"
                ],
            }
        ],
    }
    output = _model_output(
        allocation,
        reports[0]["evidence_refs"][0],
    )
    output.update(
        {
            "next_slice_name": "HOLOINDEX_OWNER_REPAIR_PHASE1",
            "requested_operation": "holoindex_maintenance",
            "allowed_paths": ["holo_index/query_owner.py"],
        }
    )
    snapshot = replace(
        inputs["snapshot"],
        holoindex_state={
            **inputs["snapshot"].holoindex_state,
            "freshness_ok": False,
        },
    )

    receipt = evaluate_architect_proposal_executability(
        model_output=output,
        snapshot=snapshot,
        reports=reports,
        report_bundle_id=inputs["report_collection"].validation.bundle.bundle_id,
        wsp15_allocation_receipt=allocation,
        policy=_policy(),
        task_prompt_text="Repair one cross-module retrieval path.",
        progressive_execution_stage_ceiling=STAGE_BOUNDED_EXECUTION,
    )

    assert receipt.proposal_validity == VALIDITY_VALID
    assert receipt.execution_readiness == READINESS_READY
    assert receipt.admissible_to_authoritative_queue is False
    assert receipt.progressive_policy_decision == DECISION_WOULD_BLOCK
    assert receipt.direct_read_grounded is True
    assert receipt.holoindex_maintenance_exception_applied is True


def test_complexity_two_low_risk_fix_is_admitted() -> None:
    inputs = _build_inputs()
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation="edit_foundup_module",
        prompt_text="Fix one bounded FoundUp module defect",
        changed_paths=("modules/foundups/demo/src/worker.py",),
        allowed_read_targets=("modules/foundups/demo/src/worker.py",),
    ).to_dict()
    output = _model_output(
        allocation, inputs["reports"][0]["evidence_refs"][0]
    )

    receipt = evaluate_architect_proposal_executability(
        model_output=output,
        snapshot=inputs["snapshot"],
        reports=inputs["reports"],
        report_bundle_id=inputs["report_collection"].validation.bundle.bundle_id,
        wsp15_allocation_receipt=allocation,
        policy=_policy(),
        task_prompt_text="Fix one bounded FoundUp module defect",
        progressive_execution_stage_ceiling=STAGE_BOUNDED_EXECUTION,
    )

    assert allocation["complexity"] == 2
    assert receipt.progressive_policy_decision == DECISION_BOUNDED_EXECUTION_ADMITTED
    assert receipt.admissible_to_authoritative_queue is True
    assert receipt.independent_verifier_required is True


def test_unrelated_holo_reference_does_not_unlock_maintenance_exception() -> None:
    inputs = _build_inputs()
    reports = [dict(report) for report in inputs["reports"]]
    reports[0] = {
        **reports[0],
        "evidence_refs": [
            *reports[0]["evidence_refs"],
            "file:holo_index/unrelated.py:sha256:test:lines:1",
        ],
        "findings": [
            {
                **reports[0]["findings"][0],
                "next_slice_name": "HOLOINDEX_OWNER_REPAIR_PHASE1",
            }
        ],
    }
    output = _model_output(
        inputs["allocation"],
        reports[0]["findings"][0]["evidence_refs"][0],
    )
    output.update(
        {
            "next_slice_name": "HOLOINDEX_OWNER_REPAIR_PHASE1",
            "requested_operation": "holoindex_maintenance",
            "allowed_paths": ["holo_index/query_owner.py"],
        }
    )
    snapshot = replace(
        inputs["snapshot"],
        holoindex_state={
            **inputs["snapshot"].holoindex_state,
            "freshness_ok": False,
        },
    )

    receipt = evaluate_architect_proposal_executability(
        model_output=output,
        snapshot=snapshot,
        reports=reports,
        report_bundle_id=inputs["report_collection"].validation.bundle.bundle_id,
        wsp15_allocation_receipt=inputs["allocation"],
        policy=_policy(),
        task_prompt_text="Fix one bounded FoundUp module defect",
        progressive_execution_stage_ceiling=STAGE_BOUNDED_EXECUTION,
    )

    assert receipt.proposal_validity == VALIDITY_VALID
    assert receipt.execution_readiness == READINESS_EVIDENCE_BLOCKED
    assert receipt.direct_read_grounded is False
    assert receipt.holoindex_maintenance_exception_applied is False


def test_holo_maintenance_direct_read_cannot_widen_to_directory_wildcard() -> None:
    inputs = _build_inputs()
    reports = [dict(report) for report in inputs["reports"]]
    reports[0] = {
        **reports[0],
        "evidence_refs": ["file:holo_index/query_owner.py:sha256:test:lines:1"],
        "findings": [
            {
                **reports[0]["findings"][0],
                "next_slice_name": "HOLOINDEX_OWNER_REPAIR_PHASE1",
                "evidence_refs": [
                    "file:holo_index/query_owner.py:sha256:test:lines:1"
                ],
            }
        ],
    }
    output = _model_output(
        inputs["allocation"],
        reports[0]["evidence_refs"][0],
    )
    output.update(
        {
            "next_slice_name": "HOLOINDEX_OWNER_REPAIR_PHASE1",
            "requested_operation": "holoindex_maintenance",
            "allowed_paths": ["holo_index/**"],
        }
    )
    snapshot = replace(
        inputs["snapshot"],
        holoindex_state={
            **inputs["snapshot"].holoindex_state,
            "freshness_ok": False,
        },
    )

    receipt = evaluate_architect_proposal_executability(
        model_output=output,
        snapshot=snapshot,
        reports=reports,
        report_bundle_id=inputs["report_collection"].validation.bundle.bundle_id,
        wsp15_allocation_receipt=inputs["allocation"],
        policy=_policy(),
        task_prompt_text="Fix one bounded FoundUp module defect",
        progressive_execution_stage_ceiling=STAGE_BOUNDED_EXECUTION,
    )

    assert receipt.proposal_validity == VALIDITY_VALID
    assert receipt.execution_readiness == READINESS_EVIDENCE_BLOCKED
    assert receipt.holoindex_maintenance_exception_applied is False


def test_windows_blocks_live_canary_but_not_readonly_reasoning() -> None:
    receipt, _, _ = _evaluate(
        output_updates={
            "target_effect_plane": EFFECT_LIVE_WORKTREE_CANARY,
            "requested_operation": "live_worktree_canary",
        },
        policy=_policy(platform="windows"),
    )

    assert receipt.proposal_validity == VALIDITY_VALID
    assert receipt.execution_readiness == READINESS_PLATFORM_BLOCKED
    assert receipt.admissible_to_authoritative_queue is False


def test_unsupported_fix_becomes_research_not_a_queue_authority() -> None:
    receipt, _, _ = _evaluate(
        output_updates={"next_slice_name": "UNOBSERVED_SLICE_PHASE1"},
        policy=_policy(),
    )

    assert receipt.accepted is False
    assert receipt.proposal_validity == VALIDITY_NEEDS_RESEARCH
    assert receipt.admissible_to_authoritative_queue is False


def test_mixed_valid_and_traversal_paths_fail_instead_of_silently_narrowing() -> None:
    receipt, _, _ = _evaluate(
        output_updates={
            "allowed_paths": [
                "modules/communication/moltbot_bridge/src/valid.py",
                "../outside.py",
            ]
        },
        policy=_policy(),
    )

    assert receipt.accepted is False
    assert "repository_path_token_invalid" in receipt.rejection_reasons


def test_tampered_serialized_receipt_fails_closed() -> None:
    receipt, _, _ = _evaluate(policy=_policy())
    tampered = receipt.to_dict()
    tampered["allowed_paths"] = ["modules/other/**"]

    with pytest.raises(ValueError, match="proposal_admission_receipt_invalid"):
        validate_architect_proposal_executability_receipt(tampered)


def test_holo_maintenance_exception_cannot_be_forged_by_receipt_rehash() -> None:
    receipt, _, _ = _evaluate(policy=_policy())
    forged = receipt.to_dict()
    forged["index_gap_detected"] = True
    forged["direct_read_grounded"] = False
    forged["holoindex_maintenance_exception_applied"] = True
    body = dict(forged)
    body.pop("receipt_id")
    forged["receipt_id"] = proposal_admission._digest(body)

    with pytest.raises(ValueError, match="proposal_admission_receipt_invalid"):
        validate_architect_proposal_executability_receipt(forged)


def test_backend_persists_valid_blocked_candidate_without_authoritative_admission() -> None:
    inputs = _build_inputs()
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    missing_capability = LIVE_EXECUTION_CAPABILITIES[0]
    policy = _policy(
        available=tuple(
            item
            for item in LIVE_EXECUTION_CAPABILITIES
            if item != missing_capability
        ),
        missing={missing_capability: "canonical_trust_anchor_missing"},
    )
    kwargs = _runtime_kwargs(inputs)
    kwargs["proposal_admission_policy"] = policy

    result = run_reddog_backend_architect_determination_runtime(
        **kwargs,
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=FakeArchitectRunner(
            _model_output(inputs["allocation"], evidence_ref)
        ),
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.receipt.proposal_admission is not None
    assert result.receipt.proposal_admission.accepted is True
    assert (
        result.receipt.proposal_admission.admissible_to_authoritative_queue
        is False
    )
    assert result.receipt.queue_candidate is not None
    assert result.receipt.queue_candidate.status == "BLOCKED_CANDIDATE"
    assert (
        ArchitectDeterminationReason.PROPOSAL_EXECUTABILITY_ADMISSION
        not in result.rejection_reasons
    )


def test_admission_modules_have_no_execution_network_or_index_mutation_imports() -> None:
    src = Path(__file__).resolve().parents[1] / "src"
    banned_imports = {
        "subprocess", "requests", "urllib", "http", "socket", "git", "gh"
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}
    for name in (
        "reddog_architect_proposal_admission_contract.py",
        "reddog_architect_proposal_executability_admission.py",
        "reddog_architect_proposal_prompt.py",
        "reddog_architect_fix_candidate_gate.py",
        "reddog_architect_fix_promotion_profile.py",
        "reddog_architect_fix_promotion_records.py",
    ):
        tree = ast.parse((src / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(
                    alias.name.split(".")[0] not in banned_imports
                    for alias in node.names
                )
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in banned_imports
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls


def _proposal_worker_plan():
    from modules.communication.moltbot_bridge.tests.test_reddog_authority_profile_exact_schema import _m2m_envelope
    receipt, _, _ = _evaluate(policy=_policy())
    packet = _m2m_envelope()
    packet["I"].update({key: list(getattr(receipt, key)) for key in (
        "allowed_paths", "denied_paths", "required_tests", "required_policy_gates",
        "expected_evidence", "stop_conditions",
    )})
    packet["I"]["wsp15"] = {"complexity": receipt.wsp15_complexity}
    return {"operation": receipt.requested_operation,
            "requested_allowed_paths": list(receipt.allowed_paths),
            "planned_artifacts": list(receipt.allowed_paths), "m2m_envelope": packet}


def test_proposal_plan_preserves_legacy_absence_and_explicit_empty() -> None:
    absent, _, _ = _evaluate(policy=_policy())
    none, _, _ = _evaluate(policy=_policy(), output_updates={"bounded_worker_plan": None})
    empty, _, _ = _evaluate(policy=_policy(), output_updates={"bounded_worker_plan": {}})
    assert none.to_dict() == absent.to_dict()
    assert "bounded_worker_plan" not in absent.to_dict()
    assert empty.to_dict()["bounded_worker_plan"] == {}
    assert empty.receipt_id != absent.receipt_id
    assert validate_architect_proposal_executability_receipt(empty.to_dict()) == empty


def test_proposal_plan_is_detached_and_binds_the_complete_receipt() -> None:
    plan = _proposal_worker_plan()
    expected = copy.deepcopy(plan)
    receipt, _, _ = _evaluate(policy=_policy(), output_updates={"bounded_worker_plan": plan})
    assert receipt.bounded_worker_plan == expected
    assert receipt.accepted is True
    plan["m2m_envelope"]["I"]["fixture"].append("caller mutation")
    public = receipt.to_dict()
    restored = validate_architect_proposal_executability_receipt(public)
    public["bounded_worker_plan"]["m2m_envelope"]["A"] = "public mutation"
    assert receipt.bounded_worker_plan == restored.bounded_worker_plan == expected
    changed = copy.deepcopy(expected)
    changed["m2m_envelope"]["I"]["fixture"][1] = 2
    other, _, _ = _evaluate(policy=_policy(), output_updates={"bounded_worker_plan": changed})
    assert other.receipt_id != receipt.receipt_id


@pytest.mark.parametrize("case", ("operation", "paths", "artifacts", "traversal", "glob_artifact",
                                  "domain_operation", "domain_tests", "mirror", "score", "score_type"))
@pytest.mark.parametrize("rehash", (False, True))
def test_proposal_plan_rejects_inconsistent_declared_bindings(case, rehash) -> None:
    plan = _proposal_worker_plan()
    receipt, _, _ = _evaluate(policy=_policy(), output_updates={"bounded_worker_plan": plan})
    if case == "operation": plan["operation"] = "different_operation"
    elif case == "paths": plan["requested_allowed_paths"] = ["modules/other/**"]
    elif case == "artifacts": plan["planned_artifacts"] = [".env"]
    elif case == "traversal": plan["planned_artifacts"] = ["modules/../outside.py"]
    elif case == "glob_artifact": plan["planned_artifacts"] = ["modules/**"]
    elif case == "domain_operation": plan["domain_profile"] = {"operation": "other"}
    elif case == "domain_tests": plan["domain_profile"] = {"required_tests": ["skip tests"]}
    elif case == "mirror": plan["m2m_envelope"]["I"]["allowed_paths"] = ["outside/**"]
    elif case == "score_type": plan["m2m_envelope"]["I"]["wsp15"] = "unscored"
    else: plan["m2m_envelope"]["I"]["wsp15"]["complexity"] = True
    with pytest.raises(ValueError):
        if rehash:
            payload = receipt.to_dict()
            payload["bounded_worker_plan"] = plan
            payload.pop("receipt_id")
            payload["receipt_id"] = proposal_admission._digest(payload)
            validate_architect_proposal_executability_receipt(payload)
        else:
            _evaluate(policy=_policy(), output_updates={"bounded_worker_plan": plan})


@pytest.mark.parametrize("requested,denied,valid", (
    ("modules/**", "modules/private/**", False),
    ("modules/**", "modules/private/config.py", False),
    ("modules/private/*.py", "modules/p?ivate/**", False),
    ("modules/p[ru]ivate/*.py", "modules/private/**", False),
    ("modules/public/**", "modules/private/**", True),
    ("modules/private/file.py", "modules/private/**", False),
    ("modules/public/file.py", "modules/private/**", True),
    ("modules/**", "**/credentials.json", False),
))
@pytest.mark.parametrize("rehash", (False, True))
def test_requested_plan_scope_rejects_unresolved_deny_overlap(requested, denied, valid, rehash) -> None:
    scope = {"allowed_paths": ["modules/**"], "denied_paths": [denied]}
    plan = {"requested_allowed_paths": [requested]}
    receipt, _, _ = _evaluate(output_updates=scope)
    def read():
        if rehash:
            payload = receipt.to_dict()
            payload["bounded_worker_plan"] = plan
            payload.pop("receipt_id")
            payload["receipt_id"] = proposal_admission._digest(payload)
            return validate_architect_proposal_executability_receipt(payload)
        return _evaluate(output_updates={**scope, "bounded_worker_plan": plan})[0]
    if valid:
        assert read().bounded_worker_plan == plan
    else:
        with pytest.raises(ValueError, match="proposal_admission_receipt_invalid"):
            read()


@pytest.mark.parametrize("field", ("allowed_paths", "denied_paths"))
@pytest.mark.parametrize("invalid", (None, "modules/**", [None]))
def test_plan_reader_rejects_malformed_outer_scope(field, invalid) -> None:
    receipt, _, _ = _evaluate(output_updates={"bounded_worker_plan": {}})
    payload = receipt.to_dict()
    payload[field] = invalid
    payload.pop("receipt_id")
    payload["receipt_id"] = proposal_admission._digest(payload)
    with pytest.raises(ValueError, match="proposal_admission_receipt_invalid"):
        validate_architect_proposal_executability_receipt(payload)


@pytest.mark.parametrize("field", ("planned_artifacts", "requested_allowed_paths"))
@pytest.mark.parametrize("path", ("modules/PRIVATE/secret.py", "modules/private./secret.py",
                                  "modules/private /secret.py", "modules/private/secret.py\t"))
def test_plan_rejects_case_and_noncanonical_path_aliases(field, path) -> None:
    with pytest.raises(ValueError, match="proposal_admission_receipt_invalid"):
        _evaluate(output_updates={"allowed_paths": ["modules/**"], "denied_paths": ["modules/private/**"],
                                  "bounded_worker_plan": {field: [path]}})


@pytest.mark.parametrize("case", ("null", "wire_string", "partial", "refs_bool", "tuple", "nan",
                                  "cycle", "depth", "nodes", "bytes", "secret", "digest",
                                  "env_value", "false_no_effect"))
def test_proposal_rejects_invalid_packet_before_readiness(case) -> None:
    from modules.communication.moltbot_bridge.tests.test_reddog_authority_profile_exact_schema import _invalid_m2m
    with pytest.raises(ValueError):
        _evaluate(output_updates={"bounded_worker_plan": {"m2m_envelope": _invalid_m2m(case)}})


@pytest.mark.parametrize("case", ("list", "cycle", "non_ascii", "serialized_null"))
def test_proposal_plan_rejects_noncanonical_outer_data(case) -> None:
    plan = {} if case != "list" else []
    if case == "cycle": plan["domain_profile"] = plan
    if case == "non_ascii": plan["domain_id"] = "\u00e9"
    with pytest.raises(ValueError):
        if case == "serialized_null":
            receipt, _, _ = _evaluate()
            payload = receipt.to_dict()
            payload["bounded_worker_plan"] = None
            validate_architect_proposal_executability_receipt(payload)
        else:
            _evaluate(output_updates={"bounded_worker_plan": plan})


def test_proposal_snapshots_plan_before_other_model_fields_are_read() -> None:
    _, inputs, output = _evaluate()
    plan = _proposal_worker_plan()
    expected = copy.deepcopy(plan)
    class MutatingOutput(dict):
        def get(self, key, default=None):
            if key == "action":
                plan["m2m_envelope"]["A"] = "changed during proposal parsing"
            return super().get(key, default)
    receipt = evaluate_architect_proposal_executability(
        model_output=MutatingOutput(output, bounded_worker_plan=plan),
        snapshot=inputs["snapshot"], reports=inputs["reports"],
        report_bundle_id=inputs["report_collection"].validation.bundle.bundle_id,
        wsp15_allocation_receipt=inputs["allocation"], policy=_policy(),
    )
    assert receipt.bounded_worker_plan == expected


@pytest.mark.parametrize("path", ("proposal_admission", "operational_context_binding.proposal_admission"))
def test_full_proposal_plan_receipt_survives_embedded_profile(path) -> None:
    from modules.communication.moltbot_bridge.src.reddog_authority_profile_rehydration import rehydrate_authority_profile_runtime
    receipt, _, _ = _evaluate(output_updates={"bounded_worker_plan": _proposal_worker_plan()})
    profile = {"proposal_admission": receipt.to_dict()}
    if path.startswith("operational_context_binding."):
        profile = {"operational_context_binding": profile}
    restored = rehydrate_authority_profile_runtime(profile)
    for part in path.split("."):
        restored = restored[part]
    restored_receipt = validate_architect_proposal_executability_receipt(restored)
    assert restored_receipt.receipt_id == receipt.receipt_id
    assert restored_receipt.bounded_worker_plan == receipt.bounded_worker_plan
    assert proposal_admission._digest(restored_receipt.to_dict()) == proposal_admission._digest(receipt.to_dict())
