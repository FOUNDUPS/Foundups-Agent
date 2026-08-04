"""No-growth enforcement for focused RedDog security-repair exemptions."""

from __future__ import annotations

import ast
from datetime import date
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_ROOT = Path(__file__).resolve().parents[1]
DATABASE_ROOT = REPO_ROOT / "modules/infrastructure/database"
SHARED_UTILITIES_ROOT = REPO_ROOT / "modules/infrastructure/shared_utilities"
SLICE_DATE = date(2026, 7, 18)
ROOT_AUTHORITY_EXACT_HOSTS = {
    "src/reddog_signer_key_provider_dryrun.py",
    "src/reddog_signer_socket_service_runtime_bootstrap.py",
    "src/reddog_signer_socket_service_runtime_wiring.py",
}
EXPECTED_MODULE_FILES = {
    "src/foundup_job_contract.py",
    "src/reddog_authoritative_work_state_refresh_runtime.py",
    "src/reddog_main_resident_queue_next_stage_dispatch_bootstrap.py",
    "src/reddog_main_resident_queue_runtime_dependency_bundle.py",
    "src/reddog_main_resident_queue_serial_loop_bootstrap.py",
    "src/openclaw_supervisor.py",
    "src/reddog_openclaw_live_enqueue.py",
    "src/reddog_resident_live_canary.py",
    "src/reddog_resident_queue_slice_verifier_request_binding.py",
    "src/reddog_signed_authority_worker_dispatch_dryrun.py",
    "src/reddog_signed_worker_0102_readonly_review_binding.py",
    "src/reddog_signed_worker_openclaw_queue_loop_runtime_binding.py",
    "src/reddog_signed_worker_queue_serial_loop_runner.py",
    "src/reddog_signer_delegated_authority_runtime.py",
    "src/reddog_signer_key_provider_dryrun.py",
    "src/reddog_signer_socket_service_runtime_bootstrap.py",
    "src/reddog_signer_socket_service_runtime_wiring.py",
    "src/reddog_wre_queue_authority_request_dryrun.py",
    "src/reddog_wre_queue_consumer_dryrun.py",
    "src/reddog_wre_worktree_create.py",
    "src/reddog_backend_architect_determination_runtime.py",
    "src/reddog_fusion_progress_validation.py",
    "src/reddog_provider_call_evidence.py",
    "src/reddog_readonly_0102_audit_worker_runtime.py",
    "src/reddog_readonly_audit_task_executor.py",
    "tests/test_reddog_governed_execution_valve_production_wiring.py",
    "tests/test_reddog_backend_architect_determination_runtime.py",
    "tests/test_reddog_fusion_progress_receipt.py",
    "tests/test_reddog_main_openclaw_signed_worker_claim_loop_preflight.py",
    "tests/test_reddog_main_readonly_operational_bootstrap.py",
    "tests/test_reddog_main_resident_queue_serial_loop_bootstrap.py",
    "tests/test_reddog_provider_call_evidence.py",
    "tests/test_reddog_readonly_audit_research_decision_e2e_runtime.py",
    "tests/test_reddog_readonly_audit_task_executor.py",
    "tests/test_reddog_resident_architect_durable_agentdb_cycle.py",
    "tests/test_reddog_signed_worker_dispatch_task_executor.py",
}
PROVIDER_EVIDENCE_EXACT_FILES = {
    "INTERFACE.md",
    "ModLog.md",
    "src/reddog_backend_architect_determination_runtime.py",
    "src/reddog_fusion_progress_validation.py",
    "src/reddog_provider_call_evidence.py",
    "src/reddog_readonly_0102_audit_worker_runtime.py",
    "src/reddog_readonly_audit_task_executor.py",
    "tests/TestModLog.md",
    "tests/test_reddog_backend_architect_determination_runtime.py",
    "tests/test_reddog_fusion_progress_receipt.py",
    "tests/test_reddog_main_readonly_operational_bootstrap.py",
    "tests/test_reddog_provider_call_evidence.py",
    "tests/test_reddog_readonly_audit_research_decision_e2e_runtime.py",
    "tests/test_reddog_readonly_audit_task_executor.py",
    "tests/test_reddog_resident_architect_durable_agentdb_cycle.py",
    "wsp_62_exemptions.yaml",
}
PUBLICATION_MODULE_FILES = {
    "src/reddog_architect_fix_promotion_publication.py",
    "src/reddog_architect_fix_promotion_publication_validation.py",
}
BOUNDED_AUTHORITY_BINDING_FILES = {
    "src/reddog_worker_dispatch_authority_binding.py",
}
ROOT_OUTCOME_AUTHORITY_FILES = {
    "src/foundup_verified_outcome_root_authority.py",
    "src/foundup_verified_outcome_root_authority_client.py",
    "src/foundup_verified_outcome_root_authority_dependency.py",
    "src/foundup_verified_outcome_root_authority_protocol.py",
    "src/foundup_verified_outcome_root_authority_provision_entrypoint.py",
    "src/foundup_verified_outcome_root_authority_service.py",
    "src/foundup_verified_outcome_root_authority_service_entrypoint.py",
    "src/foundup_verified_outcome_root_authority_socket_service.py",
    "src/foundup_verified_outcome_root_authority_state.py",
    "src/reddog_isolated_signer_process_entrypoint.py",
    "src/reddog_signer_process_isolation_gate.py",
    "src/reddog_signer_socket_peer_credential_attestor.py",
    "src/reddog_signer_socket_service_bootstrap_admission.py",
}
CURRENT_SECURITY_RUNTIME_FILES = {
    "scripts/run_task.py",
    "src/reddog_run_task_support.py",
    "src/reddog_work_authority_nonce_store.py",
    "src/reddog_work_order_signature_verifier.py",
}
BOUNDED_DATABASE_SECURITY_FILES = {
    "modules/infrastructure/database/src/signed_worker_assurance_completion.py",
    "modules/infrastructure/database/src/signed_worker_assurance_request.py",
    "modules/infrastructure/database/src/signed_worker_assurance_staging.py",
    "modules/infrastructure/database/src/signed_worker_assignment.py",
    "modules/infrastructure/database/src/signed_worker_execution_binding.py",
    "modules/infrastructure/database/src/signed_worker_execution_commit.py",
    "modules/infrastructure/database/src/signed_worker_execution_lease.py",
    "modules/infrastructure/database/src/signed_worker_execution_lease_fence.py",
    "modules/infrastructure/database/src/signed_worker_execution_lease_schema.py",
    "modules/infrastructure/database/src/signed_worker_execution_lease_time.py",
    "modules/infrastructure/database/src/signed_worker_execution_quarantine.py",
    "modules/infrastructure/database/src/signed_worker_execution_quarantine_receipt.py",
    "modules/infrastructure/database/src/signed_worker_execution_row.py",
    "modules/infrastructure/database/src/signed_worker_execution_store.py",
    "modules/infrastructure/database/src/signed_worker_finalization_status.py",
    "modules/infrastructure/database/src/signed_worker_result_history.py",
    "modules/infrastructure/database/src/signed_worker_result_ledger.py",
}
BOUNDED_SIGNED_WORKER_RESULT_FILES = {
    "src/reddog_signed_worker_execution_heartbeat.py",
    "src/reddog_signed_worker_queue_state_reader.py",
    "src/reddog_signed_worker_result_receipt.py",
}
TOUCHED_SIGNED_WORKER_RUNTIME_FILES = {
    "src/reddog_signed_worker_execution_claim.py",
    "src/reddog_signed_worker_execution_recovery.py",
    "src/reddog_signed_worker_run_task_runtime.py",
    "src/reddog_signed_worker_supervisor_admission.py",
}
BOUNDED_SECURITY_TEST_FILES = {
    "modules/communication/moltbot_bridge/tests/reddog_signed_worker_agentdb_test_support.py",
    "modules/communication/moltbot_bridge/tests/test_reddog_signed_worker_agentdb_admission.py",
    "modules/communication/moltbot_bridge/tests/test_reddog_signed_worker_agentdb_authority.py",
    "modules/communication/moltbot_bridge/tests/test_reddog_signed_worker_agentdb_history.py",
    "modules/communication/moltbot_bridge/tests/test_reddog_signed_worker_agentdb_runtime.py",
    "modules/communication/moltbot_bridge/tests/test_reddog_signed_worker_execution_security.py",
    "modules/infrastructure/database/tests/signed_worker_assurance_test_support.py",
    "modules/infrastructure/database/tests/test_signed_worker_assurance_finalization.py",
    "modules/infrastructure/database/tests/test_signed_worker_assurance_lease_schema.py",
    "modules/infrastructure/database/tests/test_signed_worker_assurance_recovery.py",
    "modules/infrastructure/database/tests/test_signed_worker_assurance_reservation.py",
    "modules/infrastructure/database/tests/test_signed_worker_quarantine_security.py",
}


def _exemptions(path: Path) -> list[dict]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict) and isinstance(payload.get("exemptions"), list)
    return [item for item in payload["exemptions"] if "no_growth_ceiling" in item]


def _named_sizes(path: Path) -> dict[str, int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name: node.end_lineno - node.lineno + 1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.end_lineno is not None
    }


def _oversized_function_sizes(
    path: Path,
    *,
    threshold: int = 60,
) -> dict[str, int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name: node.end_lineno - node.lineno + 1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.end_lineno is not None
        and node.end_lineno - node.lineno + 1 > threshold
    }


def _assert_exact_temporary_exemption(item: dict, root: Path) -> None:
    assert item["owner"] and item["architect_reviewer"] == "0102 Technical Architect"
    expiry = date.fromisoformat(item["expires_on"])
    assert SLICE_DATE < expiry <= date(2026, 9, 30)
    assert date.today() < expiry
    assert item["temporary"] is True and item["remediation"]
    target = root / item["file"]
    ceiling = item["no_growth_ceiling"]
    assert len(target.read_text(encoding="utf-8").splitlines()) <= ceiling["file_lines"]
    sizes = _named_sizes(target) if target.suffix == ".py" else {}
    for name, limit in ceiling.get("functions", {}).items():
        assert name in sizes and sizes[name] <= limit


def test_module_security_repair_exemptions_are_exact_and_do_not_grow() -> None:
    items = _exemptions(MODULE_ROOT / "wsp_62_exemptions.yaml")
    assert {item["file"] for item in items} == EXPECTED_MODULE_FILES
    for item in items:
        _assert_exact_temporary_exemption(item, MODULE_ROOT)
        if item["file"] in ROOT_AUTHORITY_EXACT_HOSTS:
            target = MODULE_ROOT / item["file"]
            assert len(target.read_text(encoding="utf-8").splitlines()) == (
                item["no_growth_ceiling"]["file_lines"]
            )


def test_root_main_exemption_has_an_exact_security_repair_ceiling() -> None:
    items = _exemptions(REPO_ROOT / "wsp_62_exemptions.yaml")
    main_item = next(item for item in items if item["file"] == "main.py")
    _assert_exact_temporary_exemption(main_item, REPO_ROOT)


def test_provider_evidence_exemptions_match_exact_touched_file_sizes() -> None:
    payload = yaml.safe_load(
        (MODULE_ROOT / "wsp_62_exemptions.yaml").read_text(encoding="utf-8")
    )
    items = {
        item["file"]: item
        for item in payload["exemptions"]
        if item.get("file") in PROVIDER_EVIDENCE_EXACT_FILES
    }

    assert set(items) == PROVIDER_EVIDENCE_EXACT_FILES
    for relative_path, item in items.items():
        target = MODULE_ROOT / relative_path
        assert item["temporary"] is True
        assert item["reviewer"] == "0102 Technical Architect"
        assert item["remediation"]
        assert item["threshold_override"] == len(
            target.read_text(encoding="utf-8").splitlines()
        )
        if target.suffix == ".py" and "no_growth_ceiling" in item:
            assert item["no_growth_ceiling"]["file_lines"] == len(
                target.read_text(encoding="utf-8").splitlines()
            )
            assert item["no_growth_ceiling"].get("functions", {}) == (
                _oversized_function_sizes(target)
            )


def test_architect_publication_modules_need_no_wsp62_exemption() -> None:
    for relative_path in PUBLICATION_MODULE_FILES:
        target = MODULE_ROOT / relative_path
        assert len(target.read_text(encoding="utf-8").splitlines()) <= 675
        for name, size in _named_sizes(target).items():
            assert size <= (200 if name == "AtomicArchitectFixPromotionPublisher" else 50)


def test_new_authority_binding_modules_are_bounded_without_exemption() -> None:
    for relative_path in BOUNDED_AUTHORITY_BINDING_FILES:
        target = MODULE_ROOT / relative_path
        assert len(target.read_text(encoding="utf-8").splitlines()) <= 200
        assert all(size <= 50 for size in _named_sizes(target).values())


def test_root_outcome_authority_modules_stay_within_domain_limits() -> None:
    for relative_path in ROOT_OUTCOME_AUTHORITY_FILES:
        target = MODULE_ROOT / relative_path
        assert len(target.read_text(encoding="utf-8").splitlines()) <= 675
        assert _oversized_function_sizes(target) == {}


def test_current_security_runtime_files_stay_under_domain_limit() -> None:
    for relative_path in CURRENT_SECURITY_RUNTIME_FILES:
        target = MODULE_ROOT / relative_path
        assert len(target.read_text(encoding="utf-8").splitlines()) <= 675
        oversized = _oversized_function_sizes(target)
        if relative_path == "scripts/run_task.py":
            assert oversized == {"_try_wre_dispatch": 66}
        else:
            assert oversized == {}


def test_new_database_security_files_are_bounded_without_exemption() -> None:
    for relative_path in BOUNDED_DATABASE_SECURITY_FILES:
        target = REPO_ROOT / relative_path
        assert len(target.read_text(encoding="utf-8").splitlines()) <= 200
        assert all(size <= 50 for size in _named_sizes(target).values())


def test_inherited_agent_db_monolith_has_exact_no_growth_remediation() -> None:
    items = _exemptions(DATABASE_ROOT / "wsp_62_exemptions.yaml")
    assert len(items) == 1
    item = items[0]
    assert item["file"] == "src/agent_db.py"
    assert item["temporary"] is True
    assert item["architect_reviewer"] == "0102 Technical Architect"
    assert date.fromisoformat(item["expires_on"]) == date(2026, 9, 30)
    assert item["remediation"].endswith("#agentdb-decomposition-plan")
    _assert_exact_temporary_exemption(item, DATABASE_ROOT)
    target = DATABASE_ROOT / item["file"]
    assert item["threshold_override"] == len(
        target.read_text(encoding="utf-8").splitlines()
    )
    assert item["no_growth_ceiling"]["functions"] == (
        _oversized_function_sizes(target, threshold=50)
    )
    assert item["no_growth_ceiling"]["classes"] == {
        name: size
        for name, size in _named_sizes(target).items()
        if name in item["classes"]
    }


def test_runtime_artifact_safety_has_exact_no_growth_remediation() -> None:
    items = _exemptions(SHARED_UTILITIES_ROOT / "wsp_62_exemptions.yaml")
    assert len(items) == 1
    item = items[0]
    assert item["file"] == "runtime_artifact_safety.py"
    assert item["temporary"] is True
    assert item["architect_reviewer"] == "0102 Technical Architect"
    assert date.fromisoformat(item["expires_on"]) == date(2026, 9, 30)
    assert item["remediation"].endswith(
        "#runtime-artifact-safety-decomposition"
    )
    _assert_exact_temporary_exemption(item, SHARED_UTILITIES_ROOT)
    target = SHARED_UTILITIES_ROOT / item["file"]
    assert item["threshold_override"] == len(
        target.read_text(encoding="utf-8").splitlines()
    )
    assert item["no_growth_ceiling"]["functions"] == (
        _oversized_function_sizes(target, threshold=50)
    )


def test_new_signed_worker_result_modules_are_bounded_without_exemption() -> None:
    for relative_path in BOUNDED_SIGNED_WORKER_RESULT_FILES:
        target = MODULE_ROOT / relative_path
        assert len(target.read_text(encoding="utf-8").splitlines()) <= 200
        assert all(size <= 50 for size in _named_sizes(target).values())


def test_touched_signed_worker_runtime_stays_under_domain_limit() -> None:
    for relative_path in TOUCHED_SIGNED_WORKER_RUNTIME_FILES:
        target = MODULE_ROOT / relative_path
        assert len(target.read_text(encoding="utf-8").splitlines()) <= 675
        assert _oversized_function_sizes(target) == {}


def test_signed_worker_security_suites_stay_bounded() -> None:
    for relative_path in BOUNDED_SECURITY_TEST_FILES:
        target = REPO_ROOT / relative_path
        assert len(target.read_text(encoding="utf-8").splitlines()) <= 600
