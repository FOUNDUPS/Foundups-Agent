"""WSP 62 boundaries for durable conversation-scope authentication."""

import ast
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE_FILES = {
    "src/reddog_authenticated_conversation_scope_state.py",
    "src/reddog_authority_profile_rehydration.py",
    "src/reddog_conversation_scope_advance.py",
    "src/reddog_conversation_scope_authentication.py",
    "src/reddog_conversation_scope_capability.py",
    "src/reddog_conversation_scope_contract.py",
    "src/reddog_conversation_scope_kind.py",
    "src/reddog_conversation_scope_mac.py",
    "src/reddog_conversation_scope_pending_store.py",
    "src/reddog_conversation_scope_persistence.py",
    "src/reddog_conversation_scope_record.py",
    "src/reddog_conversation_scope_request.py",
    "src/reddog_conversation_scope_revision.py",
    "src/reddog_conversation_scope_signing.py",
    "src/reddog_conversation_scope_signing_contract.py",
    "src/reddog_conversation_scope_signing_validation.py",
    "src/reddog_conversation_scope_store.py",
    "src/reddog_conversation_session_authority_source.py",
    "src/reddog_principal_memex_live_resident_source_supply.py",
    "src/reddog_conversation_work_promotion.py",
    "src/reddog_ed25519_conversation_scope_backend.py",
    "src/reddog_ed25519_signer_backend.py",
    "src/reddog_ed25519_signer_validation.py",
    "src/reddog_isolated_signer_socket_protocol.py",
    "src/reddog_signer_audit_attestation.py",
    "src/reddog_signer_conversation_scope_anchor.py",
    "src/reddog_signer_current_generation_config_loader.py",
    "src/reddog_signer_current_principal_authority_resolver.py",
    "src/reddog_signer_owner_e0_admission_validation.py",
    "src/reddog_signer_owner_e0_principal_authority.py",
    "src/reddog_signer_owner_e0_principal_records.py",
    "src/reddog_signer_socket_service_authority_policy_runtime.py",
    "src/reddog_signer_socket_service_config_composition.py",
    "src/reddog_signer_socket_service_config_materialization.py",
    "src/reddog_signer_socket_service_config_rehydration.py",
    "src/reddog_signer_socket_service_config_supply.py",
    "src/reddog_signer_socket_service_config_supply_contract.py",
    "src/reddog_signer_socket_service_policy_runtime.py",
    "src/reddog_signer_socket_service_runtime_bootstrap.py",
    "src/reddog_signer_system_service_entrypoint.py",
    "src/reddog_signer_system_service_manifest_selection_loader.py",
}
TEST_FILES = {
    "tests/reddog_conversation_scope_signing_test_support.py",
    "tests/test_reddog_architect_fix_promotion_exact_schema.py",
    "tests/test_reddog_authority_profile_exact_schema.py",
    "tests/test_reddog_conversation_scope_hmac_persistence.py",
    "tests/test_reddog_conversation_scope_revision_anchor.py",
    "tests/test_reddog_conversation_scope_security_boundaries.py",
    "tests/test_reddog_conversation_scope_signing.py",
    "tests/test_reddog_authenticated_conversation_scope_state.py",
    "tests/test_reddog_conversation_session_authority_source.py",
    "tests/test_reddog_principal_memex_live_resident_source_supply.py",
    "tests/test_reddog_conversation_work_promotion_crash_recovery.py",
    "tests/test_reddog_isolated_signer_socket_protocol.py",
    "tests/test_reddog_signer_owner_controlled_e0_admission.py",
    "tests/test_reddog_signer_owner_e0_admission_hardening.py",
    "tests/test_reddog_signer_socket_service_config_supply.py",
    "tests/test_reddog_signer_socket_service_config_supply_profiles.py",
    "tests/test_reddog_signer_socket_service_conversation_wiring.py",
    "tests/test_reddog_signer_system_service_manifest_selection_loader.py",
}
LEGACY_NO_GROWTH_FILES = {
    MODULE_ROOT / "src/reddog_main_readonly_operational_bootstrap.py": 857,
    REPO_ROOT / "extensions/reddog/tests/verify_extension_contract.js": 5893,
}


def _assert_ast_bounds(path: Path, *, file_limit: int) -> None:
    source = path.read_text(encoding="utf-8")
    assert len(source.splitlines()) <= file_limit, path
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert node.end_lineno - node.lineno + 1 <= 60, (path, node.name)
        elif isinstance(node, ast.ClassDef):
            assert node.end_lineno - node.lineno + 1 <= 200, (path, node.name)


def test_conversation_authentication_sources_stay_bounded() -> None:
    for relative_path in SOURCE_FILES:
        _assert_ast_bounds(MODULE_ROOT / relative_path, file_limit=675)


def test_conversation_authentication_security_tests_stay_bounded() -> None:
    for relative_path in TEST_FILES:
        _assert_ast_bounds(MODULE_ROOT / relative_path, file_limit=675)


def test_manifest_contract_test_stays_bounded() -> None:
    _assert_ast_bounds(
        REPO_ROOT / "scripts/tests/test_generate_reddog_backend_manifest.py",
        file_limit=675,
    )


def test_touched_legacy_hosts_do_not_grow() -> None:
    for path, ceiling in LEGACY_NO_GROWTH_FILES.items():
        assert len(path.read_text(encoding="utf-8").splitlines()) <= ceiling, path
