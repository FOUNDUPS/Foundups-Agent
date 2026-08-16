"""Independent contract tests for the RedDog backend manifest generator."""

from __future__ import annotations

import importlib.util
import hashlib
import json
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = REPO_ROOT / "scripts" / "generate_reddog_backend_manifest.py"
SPEC = importlib.util.spec_from_file_location("reddog_backend_manifest_generator", GENERATOR_PATH)
assert SPEC and SPEC.loader
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


def test_package_initializers_resolve_relative_imports_from_their_package() -> None:
    initializer = REPO_ROOT / "modules" / "communication" / "moltbot_bridge" / "src" / "__init__.py"
    module = initializer.with_name("openclaw_dae.py")

    expected = ["modules", "communication", "moltbot_bridge", "src"]
    assert generator._package_parts(initializer) == expected
    assert generator._package_parts(module) == expected


def test_generated_closure_binds_executable_and_dynamic_load_sentinels() -> None:
    manifest = generator.build_manifest()
    runtime = set(manifest["required_runtime_files"])
    tracked = set(generator._tracked_files())

    assert runtime.issubset(tracked)
    assert set(generator.EXECUTABLE_FILES).issubset(runtime)
    assert "holo_index.py" in runtime
    assert "holo_index/docs/HOLO_INDEX_MACHINE_LANGUAGE_SPEC_0102.json" in runtime
    assert "holo_index/query_result_contract_schema.py" in runtime
    assert "scripts/reddog_authoritative_work_state_query_once.py" in runtime
    assert "scripts/reddog_holoindex_incident_repair_once.py" in runtime
    assert "scripts/reddog_start_operations_control_once.py" in runtime
    assert (
        "modules/communication/moltbot_bridge/src/"
        "reddog_start_operations_control.py"
    ) in runtime
    assert (
        "modules/communication/moltbot_bridge/src/"
        "reddog_start_operations_resident_client.py"
    ) in runtime
    assert (
        "modules/communication/moltbot_bridge/skillz/"
        "reddog_operations/SKILLz.md"
    ) in runtime
    assert "modules/communication/moltbot_bridge/src/reddog_authoritative_work_state_query.py" in runtime
    assert "modules/communication/moltbot_bridge/src/openclaw_dae.py" in runtime
    assert "modules/foundups/src/foundup_registry_loader.py" in runtime
    assert "modules/platform_integration/linkedin_agent/src/linkedin_agent.py" in runtime
    assert "holo_index/maintenance_lock.py" in runtime
    assert "holo_index/query_admission.py" in runtime
    assert "holo_index/vector_segment_durability.py" in runtime
    assert "modules/communication/moltbot_bridge/scripts/run_task.py" in runtime
    assert "modules/communication/moltbot_bridge/src/openclaw_supervisor.py" in runtime
    assert "modules/infrastructure/database/src/agent_db.py" in runtime
    assert (
        "modules/infrastructure/idle_automation/src/"
        "holoindex_postmerge_coordinator.py"
    ) in runtime
    assert "modules/infrastructure/database/src/Database.py" not in runtime
    assert "modules/infrastructure/database/src/database.py" in runtime
    assert (
        "modules/infrastructure/dependency_launcher/src/wsl_agent_runtime.py"
        in runtime
    )


def test_newly_tracked_imported_runtime_dependency_cannot_be_omitted() -> None:
    importer_relative = "holo_index/core/search_engine.py"
    dependency_relative = "holo_index/core/collection_injections.py"
    importer = REPO_ROOT / importer_relative
    dependency = REPO_ROOT / dependency_relative

    tree = generator._parse_source(importer, importer_relative)
    import_names, _ = generator._imports(tree, importer)
    resolved = generator._resolve_local_module(
        "holo_index.core.collection_injections"
    )
    generated = generator.build_manifest()

    assert "holo_index.core.collection_injections" in import_names
    assert dependency_relative in generator._tracked_file_set()
    assert resolved == dependency
    assert dependency_relative in generated["required_runtime_files"]
    assert (
        generated["required_runtime_sha256"][dependency_relative]
        == generator._digest(dependency)
    )
    assert "holo_index.core.collection_search" in import_names
    assert "holo_index/core/collection_search.py" in generated[
        "required_runtime_sha256"
    ]


def _assert_signer_and_memex_runtime_files(generated: dict) -> None:
    required = generated["required_runtime_sha256"]
    expected = (
        "modules/communication/moltbot_bridge/src/"
        "reddog_signer_mutual_peer_handshake.py",
        "modules/communication/moltbot_bridge/src/reddog_signer_socket_schema.py",
        "modules/communication/moltbot_bridge/src/"
        "reddog_signer_system_service_entrypoint.py",
        "modules/communication/moltbot_bridge/src/"
        "foundup_memex_verified_outcome_validation.py",
        "modules/communication/moltbot_bridge/src/"
        "foundup_verified_outcome_root_authority.py",
        "modules/communication/moltbot_bridge/src/"
        "reddog_signer_current_generation_runtime_binding.py",
        "modules/communication/moltbot_bridge/src/"
        "reddog_signer_current_generation_use_time_gate.py",
        "modules/communication/moltbot_bridge/src/"
        "reddog_authoritative_use_lease.py",
        "modules/ai_intelligence/digital_twin/src/"
        "principal_memex_contract.py",
        "modules/ai_intelligence/digital_twin/src/"
        "principal_memex_projection.py",
        "modules/communication/moltbot_bridge/src/"
        "reddog_principal_memex_disclosure.py",
        "modules/communication/moltbot_bridge/src/"
        "reddog_principal_memex_resident_admission.py",
        "modules/communication/moltbot_bridge/src/"
        "reddog_principal_memex_live_resident_source_supply.py",
    )
    assert all(path in required for path in expected)
    for filename in (
        "foundup_verified_outcome_root_authority_client.py",
        "foundup_verified_outcome_root_authority_protocol.py",
        "foundup_verified_outcome_root_authority_service.py",
        "foundup_verified_outcome_root_authority_service_entrypoint.py",
        "foundup_verified_outcome_root_authority_socket_service.py",
        "foundup_verified_outcome_root_authority_state.py",
    ):
        assert "modules/communication/moltbot_bridge/src/" + filename in required


def test_checked_in_manifest_matches_independent_generation() -> None:
    checked_in = json.loads(generator.MANIFEST_PATH.read_text(encoding="utf-8"))
    generated = generator.build_manifest()

    assert checked_in == generated
    assert generator.MANIFEST_PATH.stat().st_size <= 320 * 1024
    assert (
        "modules/infrastructure/wre_core/skillz/skills_registry_v2.json"
        in generated["required_runtime_files"]
    )
    assert (
        "modules/infrastructure/wre_core/skillz/skills_registry_v2.json"
        in generated["required_runtime_sha256"]
    )
    assert (
        "modules/infrastructure/wre_core/src/wre_pytest_exact_id_collector.py"
        in generated["required_runtime_sha256"]
    )
    for relative in (
        "modules/infrastructure/wre_core/skillz/auto_test_registry_audit/SKILLz.md",
        "modules/infrastructure/wre_core/src/wre_test_registry_differential_plan_runtime.py",
        "modules/infrastructure/wre_core/src/wre_git_bounded_io.py",
        "modules/infrastructure/wre_core/src/wre_git_tree_manifest.py",
        "modules/infrastructure/wre_core/src/wre_test_registry_git_binding.py",
        "modules/infrastructure/wre_core/src/wre_test_registry_impact_binding.py",
        "modules/infrastructure/wre_core/src/wre_test_registry_scope_plan.py",
        "modules/infrastructure/wre_core/src/wre_recognized_dependency_binding.py",
    ):
        assert relative in generated["required_runtime_sha256"]
    assert (
        "extensions/reddog/start_operations_python_bootstrap.py"
        in generated["required_runtime_sha256"]
    )
    assert (
        "scripts/reddog_holoindex_owner_service_once.py"
        in generated["required_runtime_sha256"]
    )
    assert (
        "modules/communication/moltbot_bridge/src/reddog_holoindex_task_dispatch.py"
        in generated["required_runtime_sha256"]
    )
    _assert_signer_and_memex_runtime_files(generated)
    digest = generator.canonical_manifest_digest(generated)
<<<<<<< HEAD
    assert digest == "8adb4037af3f187d7f44d40f1f5b84ea182a07999c5a14c00047fcc797612f61"
=======
    assert digest == "932c35752db3f99a84ca31ee3d90eb2508f8ccac0193ab67d208b8357364cb81"
>>>>>>> 8a77f0574 (fix(reddog): harden governed Holo and Git context)
    constants = (REPO_ROOT / "extensions/reddog/backend_compatibility_constants.js").read_text(encoding="utf-8")
    match = re.search(r"EXPECTED_MANIFEST_SHA256 = '([a-f0-9]{64})'", constants)
    assert match is not None and match.group(1) == digest


def _index_blob(relative: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f":{relative}"], cwd=REPO_ROOT
    )


def _index_blobs(relatives: list[str]) -> dict[str, bytes]:
    process = subprocess.Popen(
        ["git", "cat-file", "--batch"], cwd=REPO_ROOT,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    )
    request = b"".join(f":{relative}\n".encode("utf-8") for relative in relatives)
    output, _ = process.communicate(request)
    assert process.returncode == 0
    blobs = {}
    offset = 0
    for relative in relatives:
        header_end = output.index(b"\n", offset)
        header = output[offset:header_end].decode("ascii").split()
        assert len(header) == 3 and header[1] == "blob"
        size = int(header[2])
        start = header_end + 1
        blobs[relative] = output[start:start + size]
        offset = start + size + 1
    assert offset == len(output)
    return blobs


def test_staged_index_manifest_is_self_consistent() -> None:
    """Prove promotion closure from index blobs, independent of the worktree."""
    manifest_relative = "scripts/reddog_backend_manifest.json"
    manifest = json.loads(_index_blob(manifest_relative).decode("utf-8"))
    staged = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=REPO_ROOT
    ).decode("utf-8").split("\0")
    tracked = {path for path in staged if path}
    required = manifest["required_runtime_sha256"]

    assert set(required).issubset(tracked)
    assert "holo_index/core/collection_search.py" in required
    blobs = _index_blobs(list(required))
    for relative, expected in required.items():
        normalized = blobs[relative].replace(b"\r\n", b"\n")
        assert hashlib.sha256(normalized).hexdigest() == expected
    digest = generator.canonical_manifest_digest(manifest)
    constants = _index_blob(
        "extensions/reddog/backend_compatibility_constants.js"
    ).decode("utf-8")
    assert f"EXPECTED_MANIFEST_SHA256 = '{digest}'" in constants
