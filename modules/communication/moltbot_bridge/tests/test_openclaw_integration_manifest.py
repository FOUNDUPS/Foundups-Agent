#!/usr/bin/env python3
"""Integration manifest drift check.

Verifies that the canonical machine-readable ledger
(openclaw_integration_manifest.json) stays aligned with
env surfaces documented in main.py and wre_defaults.env.

Slice: OPENCLAW_INTEGRATION_MANIFEST_LINT_PHASE1
"""

import ast
import json
import re
import subprocess
from copy import deepcopy
from pathlib import Path
from pathlib import PurePosixPath

import pytest

from modules.communication.moltbot_bridge.src.reddog_artifact_generation_provider_modes import (
    RUNTIME_MODE_HERMES_API,
    RUNTIME_MODE_OPENCLAW_GATEWAY,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MANIFEST_PATH = REPO_ROOT / "modules" / "communication" / "moltbot_bridge" / "config" / "openclaw_integration_manifest.json"
MAIN_PY = REPO_ROOT / "main.py"
WRE_DEFAULTS = REPO_ROOT / "modules" / "infrastructure" / "wre_core" / "config" / "wre_defaults.env"


def _tracked_repo_paths():
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        shell=False,
    )
    return frozenset(result.stdout.decode("utf-8").split("\0")) - {""}


TRACKED_PATHS = _tracked_repo_paths()


@pytest.fixture(scope="module")
def manifest():
    assert MANIFEST_PATH.exists(), f"Manifest not found: {MANIFEST_PATH}"
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return data


@pytest.fixture(scope="module")
def integrations(manifest):
    return manifest["integrations"]


@pytest.fixture(scope="module")
def all_manifest_env_keys(integrations):
    """Collect every env key declared across all manifest entries."""
    keys = set()
    for entry in integrations:
        keys.update(entry.get("env_keys", []))
        keys.update(entry.get("secret_keys", []))
    return keys


# -- 1. Schema validity --


class TestManifestSchema:
    """Manifest is valid JSON with expected top-level shape."""

    def test_manifest_is_valid_json(self, manifest):
        assert isinstance(manifest, dict)

    def test_has_schema_version(self, manifest):
        assert "$schema" in manifest

    def test_has_integrations_list(self, manifest):
        assert "integrations" in manifest
        assert isinstance(manifest["integrations"], list)

    def test_integration_count_nonzero(self, integrations):
        assert len(integrations) > 0, "Manifest has zero integrations"


# -- 2. Entry completeness --


REQUIRED_FIELDS = {
    "integration_id",
    "name",
    "type",
    "owner_module",
    "runtime_origin",
    "implementation_paths",
    "capability_boundary",
    "upstream_identity",
    "status",
    "default",
    "env_keys",
    "secret_keys",
    "external_service",
    "fail_mode",
    "consumers",
}
TOP_LEVEL_FIELDS = {
    "$schema",
    "description",
    "coverage_scope",
    "truth_scope",
    "generated",
    "runtime_origin_values",
    "runtime_origin_definitions",
    "upstream_hook_status",
    "maintenance",
    "integrations",
}
ENTRY_FIELDS = REQUIRED_FIELDS | {
    "notes",
    "provider_runtime",
    "upstream_invocation_surface",
    "evidence_paths",
    "alias_of",
}
RUNTIME_ORIGINS = frozenset(
    {"UPSTREAM_CLI", "UPSTREAM_API", "UPSTREAM_HOOK", "FOUNDUPS_LOCAL", "LEGACY_ALIAS"}
)
RUNTIME_ORIGIN_DEFINITIONS = {
    "UPSTREAM_CLI": "Foundups directly invokes an installed upstream executable.",
    "UPSTREAM_API": "Foundups directly invokes an installed upstream service API.",
    "UPSTREAM_HOOK": "Checked-in upstream hook configuration proves upstream dispatch into Foundups.",
    "FOUNDUPS_LOCAL": "The implementation is owned by this repository, even when it calls an external model or service.",
    "LEGACY_ALIAS": "A deprecated or compatibility identifier with a required canonical alias_of target; it never proves upstream execution.",
}
UPSTREAM_ORIGINS = frozenset({"UPSTREAM_CLI", "UPSTREAM_API", "UPSTREAM_HOOK"})
EXPECTED_ORIGINS = {
    "ironclaw_gateway": "FOUNDUPS_LOCAL",
    "local_ollama_qwen": "FOUNDUPS_LOCAL",
    "openclaw_gateway_artifact_provider": "UPSTREAM_CLI",
    "hermes_api_artifact_provider": "UPSTREAM_API",
    "ai_gateway_openai": "FOUNDUPS_LOCAL",
    "ai_gateway_anthropic": "FOUNDUPS_LOCAL",
    "ai_gateway_grok_xai": "FOUNDUPS_LOCAL",
    "ai_gateway_google_gemini": "FOUNDUPS_LOCAL",
    "openrouter": "FOUNDUPS_LOCAL",
    "resident_openclaw": "FOUNDUPS_LOCAL",
    "openclaw_supervisor": "FOUNDUPS_LOCAL",
    "wre_orchestrator": "FOUNDUPS_LOCAL",
    "skill_safety_gate": "FOUNDUPS_LOCAL",
    "permission_manager": "FOUNDUPS_LOCAL",
    "key_isolation": "FOUNDUPS_LOCAL",
    "dependency_security_preflight": "FOUNDUPS_LOCAL",
    "self_audit_loop": "FOUNDUPS_LOCAL",
    "foundups_hermes_wre_job_executor": "FOUNDUPS_LOCAL",
    "foundups_hermes_foundup_builder": "FOUNDUPS_LOCAL",
    "foundups_hermes_resident_client_transport": "FOUNDUPS_LOCAL",
}
EXPECTED_OWNERS = {
    "ironclaw_gateway": "modules/communication/moltbot_bridge",
    "local_ollama_qwen": "modules/communication/moltbot_bridge",
    "openclaw_gateway_artifact_provider": "modules/communication/moltbot_bridge",
    "hermes_api_artifact_provider": "modules/communication/moltbot_bridge",
    "ai_gateway_openai": "modules/communication/moltbot_bridge",
    "ai_gateway_anthropic": "modules/communication/moltbot_bridge",
    "ai_gateway_grok_xai": "modules/communication/moltbot_bridge",
    "ai_gateway_google_gemini": "modules/communication/moltbot_bridge",
    "openrouter": "modules/infrastructure/openrouter_client",
    "resident_openclaw": "modules/communication/moltbot_bridge",
    "openclaw_supervisor": "modules/communication/moltbot_bridge",
    "wre_orchestrator": "modules/infrastructure/wre_core",
    "skill_safety_gate": "modules/communication/moltbot_bridge",
    "permission_manager": "modules/ai_intelligence/agent_permissions",
    "key_isolation": "modules/communication/moltbot_bridge",
    "dependency_security_preflight": "modules/communication/moltbot_bridge",
    "self_audit_loop": "modules/infrastructure/wre_core",
    "foundups_hermes_wre_job_executor": "modules/infrastructure/wre_core",
    "foundups_hermes_foundup_builder": "modules/foundups/agent",
    "foundups_hermes_resident_client_transport": "modules/foundups/agent",
}
ALLOWED_DEFAULTS = frozenset({"on", "off"})
ALLOWED_FAIL_MODES = frozenset(
    {"fail_closed", "fail_open", "fail_closed_strict_or_fail_open_fallback"}
)
ALLOWED_EXTERNAL_SERVICES = frozenset({None, "local_service", "external_service"})
EXECUTABLE_SUFFIXES = frozenset({".py", ".js", ".ts", ".mjs", ".cjs", ".rs", ".ps1", ".sh"})
EXPECTED_LOCAL_HERMES = {
    "foundups_hermes_wre_job_executor": ("dryrun_worker_adapter", "foundups_local_dryrun_delegation_seam", "off", ("HERMES_DELEGATE_ENABLED",), ("foundup_job_consumer",), ("modules/infrastructure/wre_core/src/hermes_job_executor.py", "modules/infrastructure/wre_core/src/foundup_job_consumer.py")),
    "foundups_hermes_foundup_builder": ("bounded_foundup_builder_adapter", "foundups_local_foundup_builder_dryrun_default_double_opt_in_writes", "on", ("HERMES_BUILDER_ENABLED", "HERMES_BUILDER_ALLOW_REAL_WRITES", "HERMES_BUILDER_DRY_RUN", "HERMES_BUILDER_SECURITY_GATE"), ("hermes_foundup_job_executor",), ("modules/foundups/agent/src/hermes_adapter.py", "modules/foundups/agent/src/hermes_foundup_job_executor.py")),
    "foundups_hermes_resident_client_transport": ("resident_client_transport", "foundups_transport_only_no_model_no_execution", "off", (), ("hermes_reddog_resident_client_once",), ("modules/foundups/agent/src/hermes_reddog_resident_client_adapter.py", "scripts/hermes_reddog_resident_client_once.py")),
}
EXPECTED_UPSTREAM = {
    "openclaw_gateway_artifact_provider": {
        "name": "OpenClaw Gateway Artifact Provider",
        "type": "artifact_generation_provider",
        "owner_module": "modules/communication/moltbot_bridge",
        "origin": "UPSTREAM_CLI",
        "provider_runtime": RUNTIME_MODE_OPENCLAW_GATEWAY,
        "implementation_paths": [
            "modules/communication/moltbot_bridge/src/reddog_artifact_generation_provider_bootstrap.py",
            "modules/communication/moltbot_bridge/src/reddog_openclaw_gateway_artifact_provider.py",
            "modules/communication/moltbot_bridge/src/reddog_openclaw_gateway_command_runner.py",
            "modules/communication/moltbot_bridge/src/reddog_openclaw_gateway_confinement.py",
        ],
        "evidence_paths": [
            "modules/communication/moltbot_bridge/tests/test_reddog_openclaw_gateway_artifact_provider.py",
            "modules/communication/moltbot_bridge/tests/test_reddog_upstream_artifact_provider_bootstrap.py",
        ],
        "invocation_surface": "openclaw agent via the version-matched loopback Gateway",
        "project": "openclaw/openclaw",
        "runtime_interface": "CLI",
        "entrypoint": "/usr/local/bin/openclaw",
        "runtime_operation": "agent",
        "provider_path": "modules/communication/moltbot_bridge/src/reddog_openclaw_gateway_artifact_provider.py",
        "confinement_path": "modules/communication/moltbot_bridge/src/reddog_openclaw_gateway_confinement.py",
        "consumers": ["reddog_artifact_generation_provider_bootstrap"],
    },
    "hermes_api_artifact_provider": {
        "name": "Hermes API Artifact Provider",
        "type": "artifact_generation_provider",
        "owner_module": "modules/communication/moltbot_bridge",
        "origin": "UPSTREAM_API",
        "provider_runtime": RUNTIME_MODE_HERMES_API,
        "implementation_paths": [
            "modules/communication/moltbot_bridge/src/reddog_artifact_generation_provider_bootstrap.py",
            "modules/communication/moltbot_bridge/src/reddog_hermes_api_artifact_provider.py",
            "modules/communication/moltbot_bridge/src/reddog_hermes_api_transport.py",
            "modules/communication/moltbot_bridge/src/reddog_hermes_api_confinement.py",
            "modules/communication/moltbot_bridge/src/reddog_hermes_api_run_lifecycle.py",
            "modules/communication/moltbot_bridge/src/reddog_hermes_api_event_log.py",
        ],
        "evidence_paths": [
            "modules/communication/moltbot_bridge/tests/test_reddog_hermes_api_artifact_provider.py",
            "modules/communication/moltbot_bridge/tests/test_reddog_upstream_artifact_provider_bootstrap.py",
        ],
        "invocation_surface": "authenticated loopback POST /v1/runs",
        "project": "NousResearch/hermes-agent",
        "runtime_interface": "API",
        "entrypoint": "http://127.0.0.1:8642/v1/runs",
        "runtime_operation": "POST /v1/runs",
        "provider_path": "modules/communication/moltbot_bridge/src/reddog_hermes_api_artifact_provider.py",
        "confinement_path": "modules/communication/moltbot_bridge/src/reddog_hermes_api_confinement.py",
        "consumers": ["reddog_artifact_generation_provider_bootstrap"],
    },
}


class TestEntryCompleteness:
    """Every integration entry has all required fields."""

    def test_all_entries_have_required_fields(self, integrations):
        for entry in integrations:
            missing = REQUIRED_FIELDS - set(entry.keys())
            assert not missing, f"{entry.get('name', '???')}: missing fields {missing}"

    def test_all_entries_have_string_name(self, integrations):
        for entry in integrations:
            assert isinstance(entry["name"], str) and len(entry["name"]) > 0

    def test_all_entries_have_stable_ids(self, integrations):
        ids = [entry["integration_id"] for entry in integrations]
        assert len(ids) == len(set(ids))
        assert all(re.fullmatch(r"[a-z][a-z0-9_]{2,63}", value) for value in ids)

    def test_env_keys_are_lists(self, integrations):
        for entry in integrations:
            assert isinstance(entry["env_keys"], list), f"{entry['name']}: env_keys not a list"
            assert isinstance(entry["secret_keys"], list), f"{entry['name']}: secret_keys not a list"

    def test_status_is_known(self, integrations):
        allowed = {"landed", "planned", "parked", "removed"}
        for entry in integrations:
            assert entry["status"] in allowed, f"{entry['name']}: unknown status '{entry['status']}'"


# -- 3. Runtime provenance truth --


def _repo_file_error(value, tracked_paths=TRACKED_PATHS):
    if not isinstance(value, str) or not value or "\\" in value:
        return "path_not_normalized"
    if re.match(r"^[A-Za-z]:/", value) or value.startswith("//"):
        return "path_not_confined"
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        return "path_not_confined"
    candidate = REPO_ROOT.joinpath(*path.parts)
    try:
        candidate.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        return "path_escapes_repo"
    if not candidate.is_file() or candidate.is_symlink():
        return "path_not_checked_in_file"
    if value not in tracked_paths:
        return "path_not_tracked"
    return ""


def _upstream_semantic_errors(entry, expected):
    exact = {
        "name": expected["name"],
        "type": expected["type"],
        "owner_module": expected["owner_module"],
        "status": "landed",
        "default": "off",
        "fail_mode": "fail_closed",
        "capability_boundary": "text_artifact_only_no_tools",
        "provider_runtime": expected["provider_runtime"],
        "upstream_invocation_surface": expected["invocation_surface"],
        "env_keys": ["REDDOG_ARTIFACT_GENERATOR_MODE"],
        "secret_keys": [],
        "external_service": "local_service",
        "consumers": expected["consumers"],
    }
    return [
        f"upstream_semantic_mismatch:{key}"
        for key, value in exact.items()
        if entry.get(key) != value
    ]


def _upstream_errors(entry, expected, paths):
    errors = []
    if expected is None:
        errors.append("upstream_entry_not_allowlisted")
    identity = entry.get("upstream_identity")
    evidence = entry.get("evidence_paths")
    if not isinstance(identity, dict) or not isinstance(evidence, list) or not evidence:
        errors.append("upstream_evidence_invalid")
    else:
        errors.extend(filter(None, (_repo_file_error(value) for value in evidence)))
        if any("/tests/" not in value or not value.endswith(".py") for value in evidence):
            errors.append("upstream_evidence_not_test")
    if expected is not None and isinstance(identity, dict):
        if paths != expected["implementation_paths"]:
            errors.append("upstream_implementation_paths_mismatch")
        if evidence != expected["evidence_paths"]:
            errors.append("upstream_evidence_paths_mismatch")
        exact = {
            "project": expected["project"],
            "runtime_interface": expected["runtime_interface"],
            "runtime_entrypoint": expected["entrypoint"],
            "runtime_operation": expected["runtime_operation"],
            "canonical_provider_path": expected["provider_path"],
            "confinement_path": expected["confinement_path"],
        }
        if identity != exact:
            errors.append("upstream_identity_mismatch")
        errors.extend(_upstream_semantic_errors(entry, expected))
    return errors


def _common_entry_errors(entry):
    errors = []
    string_fields = ("integration_id", "name", "type", "owner_module", "capability_boundary")
    list_fields = ("implementation_paths", "env_keys", "secret_keys", "consumers")
    for key in string_fields:
        if not isinstance(entry.get(key), str) or not entry[key]:
            errors.append(f"entry_string_invalid:{key}")
    for key in list_fields:
        value = entry.get(key)
        if not isinstance(value, list) or len(value) != len(set(value)):
            errors.append(f"entry_list_invalid:{key}")
        elif any(not isinstance(item, str) or not item for item in value):
            errors.append(f"entry_list_item_invalid:{key}")
    if EXPECTED_OWNERS.get(entry.get("integration_id")) != entry.get("owner_module"):
        errors.append("owner_module_mismatch")
    if entry.get("default") not in ALLOWED_DEFAULTS:
        errors.append("default_invalid")
    if entry.get("fail_mode") not in ALLOWED_FAIL_MODES:
        errors.append("fail_mode_invalid")
    if entry.get("external_service") not in ALLOWED_EXTERNAL_SERVICES:
        errors.append("external_service_invalid")
    return errors


def _provenance_errors(entry):
    errors = _common_entry_errors(entry)
    integration_id = entry.get("integration_id")
    origin = entry.get("runtime_origin")
    if set(entry) - ENTRY_FIELDS:
        errors.append("entry_fields_invalid")
    if origin not in RUNTIME_ORIGINS:
        errors.append("runtime_origin_invalid")
    if EXPECTED_ORIGINS.get(integration_id) != origin:
        errors.append("runtime_origin_mismatch")
    paths = entry.get("implementation_paths")
    if not isinstance(paths, list) or not paths or len(paths) != len(set(paths)):
        errors.append("implementation_paths_invalid")
    else:
        errors.extend(filter(None, (_repo_file_error(value) for value in paths)))
    if not isinstance(entry.get("capability_boundary"), str) or not entry["capability_boundary"]:
        errors.append("capability_boundary_invalid")
    if origin in UPSTREAM_ORIGINS:
        errors.extend(_upstream_errors(entry, EXPECTED_UPSTREAM.get(integration_id), paths))
    elif any(key in entry for key in ("provider_runtime", "evidence_paths", "upstream_invocation_surface")) or entry.get("upstream_identity") is not None:
        errors.append("local_entry_claims_upstream_identity")
    if origin != "LEGACY_ALIAS" and "alias_of" in entry:
        errors.append("alias_not_allowed")
    if origin == "LEGACY_ALIAS" and entry.get("alias_of") not in set(EXPECTED_ORIGINS) - {integration_id}:
        errors.append("legacy_alias_target_invalid")
    return errors


def _source_tree(relative_path):
    return ast.parse((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def _has_literal_sequence(tree, expected):
    for node in ast.walk(tree):
        values = node.elts if isinstance(node, (ast.Tuple, ast.List)) else ()
        literals = tuple(item.value for item in values if isinstance(item, ast.Constant))
        if literals[: len(expected)] == expected:
            return True
    return False


def _has_call_prefix(tree, expected):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        values = tuple(item.value for item in node.args if isinstance(item, ast.Constant))
        if values[: len(expected)] == expected:
            return True
    return False


def _has_named_constant(tree, name, expected):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = (node.target,)
        else:
            continue
        if any(isinstance(item, ast.Name) and item.id == name for item in targets):
            if isinstance(node.value, ast.Constant) and node.value.value == expected:
                return True
    return False


class TestRuntimeProvenance:
    def test_schema_v2_and_origin_contract(self, manifest):
        assert set(manifest) == TOP_LEVEL_FIELDS
        assert manifest["$schema"] == "openclaw_integration_manifest/v2"
        assert manifest["truth_scope"] == "STATIC_IMPLEMENTATION_PROVENANCE_ONLY"
        assert set(manifest["runtime_origin_values"]) == RUNTIME_ORIGINS
        assert manifest["runtime_origin_definitions"] == RUNTIME_ORIGIN_DEFINITIONS
        assert manifest["upstream_hook_status"] == "NO_PROVEN_UPSTREAM_HOOK"

    def test_every_entry_has_exact_expected_classification(self, integrations):
        assert {entry["integration_id"] for entry in integrations} == set(EXPECTED_ORIGINS)
        for entry in integrations:
            assert not _provenance_errors(entry), entry["integration_id"]

    def test_local_hermes_surfaces_keep_distinct_controls(self, integrations):
        by_id = {entry["integration_id"]: entry for entry in integrations}
        for key, expected in EXPECTED_LOCAL_HERMES.items():
            entry = by_id[key]
            actual = (entry["type"], entry["capability_boundary"], entry["default"], tuple(entry["env_keys"]), tuple(entry["consumers"]), tuple(entry["implementation_paths"]))
            assert actual == expected
    def test_exact_upstream_provider_set_and_runtime_values(self, integrations):
        upstream = [entry for entry in integrations if entry["runtime_origin"] in UPSTREAM_ORIGINS]
        assert {entry["integration_id"] for entry in upstream} == set(EXPECTED_UPSTREAM)
        assert {entry["provider_runtime"] for entry in upstream} == {
            RUNTIME_MODE_OPENCLAW_GATEWAY,
            RUNTIME_MODE_HERMES_API,
        }
        assert not any(entry["runtime_origin"] == "UPSTREAM_HOOK" for entry in integrations)

    def test_runtime_mode_vocabulary_and_default_remain_code_owned(self):
        assert RUNTIME_MODE_OPENCLAW_GATEWAY == "openclaw_gateway"
        assert RUNTIME_MODE_HERMES_API == "hermes_api"
        profile = (
            REPO_ROOT
            / "modules/communication/moltbot_bridge/src/reddog_resident_queue_binding_profile.py"
        ).read_text(encoding="utf-8")
        assert 'return "foundups_fusion"' in profile

    @pytest.mark.parametrize(
        ("mutation", "reason"),
        [
            ({"runtime_origin": "UNKNOWN"}, "runtime_origin_invalid"),
            ({"runtime_origin": "UPSTREAM_CLI"}, "runtime_origin_mismatch"),
            ({"implementation_paths": ["../escape.py"]}, "path_not_confined"),
            ({"implementation_paths": ["C:/private/runtime.py"]}, "path_not_confined"),
            ({"implementation_paths": ["modules/not-present.py"]}, "path_not_checked_in_file"),
            ({"owner_module": "modules/untrusted"}, "owner_module_mismatch"),
            ({"fail_mode": "allow_all"}, "fail_mode_invalid"),
            ({"consumers": "shell"}, "entry_list_invalid:consumers"),
            ({"external_service": "untrusted_service"}, "external_service_invalid"),
        ],
    )
    def test_local_entry_cannot_be_relabelled_or_supply_bad_paths(self, integrations, mutation, reason):
        entry = deepcopy(next(item for item in integrations if item["integration_id"] == "openclaw_supervisor"))
        entry.update(mutation)
        assert reason in _provenance_errors(entry)

    def test_fabricated_or_substituted_upstream_claim_rejects(self, integrations):
        source = deepcopy(next(item for item in integrations if item["integration_id"] == "openclaw_gateway_artifact_provider"))
        fabricated = {**source, "integration_id": "fabricated_upstream"}
        substituted = {**source, "provider_runtime": RUNTIME_MODE_HERMES_API}
        assert "upstream_entry_not_allowlisted" in _provenance_errors(fabricated)
        assert "upstream_semantic_mismatch:provider_runtime" in _provenance_errors(substituted)

    def test_upstream_evidence_and_implementation_substitution_rejects(self, integrations):
        source = deepcopy(next(item for item in integrations if item["integration_id"] == "openclaw_gateway_artifact_provider"))
        unrelated = {**source, "evidence_paths": ["modules/communication/moltbot_bridge/tests/test_openclaw_dae.py"]}
        incomplete = {**source, "implementation_paths": source["implementation_paths"][1:]}
        assert "upstream_evidence_paths_mismatch" in _provenance_errors(unrelated)
        assert "upstream_implementation_paths_mismatch" in _provenance_errors(incomplete)

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("upstream_invocation_surface", "shell tools subagents merge"),
            ("type", "security_gate"),
            ("owner_module", "modules/untrusted"),
            ("status", "removed"),
            ("consumers", ["shell", "merge"]),
            ("alias_of", "hermes_api_artifact_provider"),
        ],
    )
    def test_upstream_security_semantics_are_exact(self, integrations, field, value):
        source = deepcopy(next(item for item in integrations if item["integration_id"] == "openclaw_gateway_artifact_provider"))
        source[field] = value
        assert _provenance_errors(source)

    def test_unknown_fields_and_documentation_only_evidence_reject(self, integrations):
        source = deepcopy(next(item for item in integrations if item["integration_id"] == "hermes_api_artifact_provider"))
        unknown = {**source, "unreviewed_claim": True}
        docs_only = {**source, "evidence_paths": ["modules/communication/moltbot_bridge/README.md"]}
        assert "entry_fields_invalid" in _provenance_errors(unknown)
        assert "upstream_evidence_not_test" in _provenance_errors(docs_only)

    def test_untracked_file_cannot_support_provenance(self):
        path = "modules/communication/moltbot_bridge/src/openclaw_supervisor.py"
        assert _repo_file_error(path, frozenset()) == "path_not_tracked"

    def test_static_manifest_has_no_runtime_authority_consumer(self):
        consumers = []
        for value in TRACKED_PATHS:
            if PurePosixPath(value).suffix.lower() not in EXECUTABLE_SUFFIXES:
                continue
            if "/tests/" in value or value.startswith("tests/"):
                continue
            if b"openclaw_integration_manifest.json" in (REPO_ROOT / value).read_bytes():
                consumers.append(value)
        assert not consumers, f"runtime sources consume static manifest: {consumers}"

    def test_provenance_lint_stays_wsp62_bounded(self):
        source = Path(__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert len(source.splitlines()) <= 675
        manifest_text = MANIFEST_PATH.read_text(encoding="utf-8")
        assert len(manifest_text) <= 18_000
        assert len(manifest_text.splitlines()) <= 200 and max(map(len, manifest_text.splitlines())) <= 600
        oversized = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and (node.end_lineno or node.lineno) - node.lineno + 1 > 50
        ]
        assert not oversized

    def test_upstream_source_markers_match_registered_invocation(self):
        openclaw_provider = _source_tree(EXPECTED_UPSTREAM["openclaw_gateway_artifact_provider"]["provider_path"])
        openclaw_runner = _source_tree("modules/communication/moltbot_bridge/src/reddog_openclaw_gateway_command_runner.py")
        hermes_lifecycle = _source_tree("modules/communication/moltbot_bridge/src/reddog_hermes_api_run_lifecycle.py")
        hermes_transport = _source_tree("modules/communication/moltbot_bridge/src/reddog_hermes_api_transport.py")
        assert _has_literal_sequence(openclaw_provider, ("openclaw", "agent"))
        assert _has_named_constant(openclaw_runner, "executable", "/usr/local/bin/openclaw")
        assert _has_call_prefix(hermes_lifecycle, ("POST", "/v1/runs"))
        assert _has_named_constant(hermes_transport, "HERMES_API_HOST", "127.0.0.1")


# -- 4. Critical env key coverage --
#    These keys are read by main.py at startup via os.getenv().
#    If they exist in main.py, they must appear in the manifest
#    so operators know which integration owns them.

CRITICAL_MAIN_PY_KEYS = {
    "OPENCLAW_CONVERSATION_BACKEND",
    "OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK",
    "OPENCLAW_RESIDENT_ENABLED",
    "OPENCLAW_RESIDENT_AUTOSTART",
    "OPENCLAW_SUPERVISOR_ENABLED",
    "OPENCLAW_DEP_SECURITY_PREFLIGHT",
    "OPENCLAW_DEP_SECURITY_PREFLIGHT_ENFORCED",
    "OPENCLAW_SELF_AUDIT_ENABLED",
    "OPENCLAW_SELF_AUDIT_INTERVAL_SEC",
}

class TestCriticalEnvCoverage:
    """Critical env keys from main.py appear in the manifest."""

    @pytest.mark.parametrize("key", sorted(CRITICAL_MAIN_PY_KEYS))
    def test_critical_key_in_manifest(self, key, all_manifest_env_keys):
        assert key in all_manifest_env_keys, (
            f"main.py reads os.getenv(\"{key}\") but it is not declared "
            f"in any manifest integration entry"
        )


# -- 5. WRE defaults coverage --
#    Keys in wre_defaults.env that start with OPENCLAW_ should
#    have a corresponding manifest entry.


class TestWreDefaultsCoverage:
    """OPENCLAW_* keys in wre_defaults.env appear in the manifest."""

    @pytest.fixture(scope="class")
    def wre_openclaw_keys(self):
        if not WRE_DEFAULTS.exists():
            pytest.skip("wre_defaults.env not found")
        keys = set()
        for line in WRE_DEFAULTS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k = line.split("=", 1)[0].strip()
            if k.startswith("OPENCLAW_"):
                keys.add(k)
        return keys

    def test_wre_openclaw_keys_in_manifest(self, wre_openclaw_keys, all_manifest_env_keys):
        # Only check the core keys, not every granular sub-flag.
        # Granular flags (TTL, cooldown, etc.) are owned by the same
        # integration as their parent key.
        core_prefixes = {
            "OPENCLAW_DEP_SECURITY_PREFLIGHT",
            "OPENCLAW_SELF_AUDIT_ENABLED",
            "OPENCLAW_SELF_AUDIT_AUTO_FIX",
            "OPENCLAW_SELF_AUDIT_INTERVAL_SEC",
        }
        missing = []
        for k in sorted(wre_openclaw_keys):
            if k in core_prefixes and k not in all_manifest_env_keys:
                missing.append(k)
        assert not missing, f"wre_defaults.env keys not in manifest: {missing}"


# -- 6. OpenRouter module coverage --


class TestOpenRouterCoverage:
    """OpenRouter integration is tracked in manifest."""

    def test_openrouter_entry_exists(self, integrations):
        names = [e["name"] for e in integrations]
        assert "OpenRouter" in names, "OpenRouter integration missing from manifest"

    def test_openrouter_has_key_envs(self, integrations):
        entry = next(e for e in integrations if e["name"] == "OpenRouter")
        expected = {"OPENROUTER_BASE_URL", "OPENROUTER_DEFAULT_MODEL"}
        actual = set(entry["env_keys"])
        missing = expected - actual
        assert not missing, f"OpenRouter missing env_keys: {missing}"

    def test_openrouter_secret_key(self, integrations):
        entry = next(e for e in integrations if e["name"] == "OpenRouter")
        assert "OPENROUTER_API_KEY" in entry["secret_keys"]


# -- 7. No duplicate integration names --


class TestNoDuplicates:

    def test_unique_names(self, integrations):
        names = [e["name"] for e in integrations]
        dupes = [n for n in names if names.count(n) > 1]
        assert not dupes, f"Duplicate integration names: {set(dupes)}"
