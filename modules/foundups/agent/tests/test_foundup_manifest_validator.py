#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FoundUp Manifest Validator Tests -- Read-Only Contract Validation

Covers FOUNDUP_MANIFEST_BASELINE_IMPL_PHASE1 requirements:
  - The 6 real manifests validate (positive).
  - foundup_id <-> build_contract.foundup_id match.
  - Forbidden-path coverage (.env, main.py, *_dae.py, vendor).
  - Negative controls: unknown/privileged executor, missing gate,
    dry_run.default=false, external_agent_allowed=true, build_ready=true,
    autonomous_execution_ready=true, shell-string command, shell metacharacters.
  - execution_routing is declarative only.
  - voteballots / trade flagged NEEDS_LABEL_RECONCILIATION.
  - Validator source imports no runtime executor/consumer.
  - Validator source performs no exec / process / network / file-write calls.

WSP 97 TRUTH BOUNDARIES:
  - These tests EXECUTE nothing in the validator beyond pure validation.
  - No skip / xfail on any security assertion.
"""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from modules.foundups.agent.src.foundup_manifest_validator import (
    REQUIRED_GATES,
    ManifestValidationResult,
    validate_manifest,
    validate_manifest_file,
)

# Repo root: tests/ -> agent/ -> foundups/ -> modules/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[4]
VALIDATOR_SOURCE = (
    Path(__file__).resolve().parents[1] / "src" / "foundup_manifest_validator.py"
)

# (foundup_id, manifest relative path, expected build_contract.status)
TARGET_MANIFESTS = [
    ("gotjunk_001", "modules/foundups/gotjunk/foundup_manifest.json", "BASELINE_DECLARATIVE_ONLY"),
    ("kosei", "modules/foundups/kosei/foundup_manifest.json", "BASELINE_DECLARATIVE_ONLY"),
    ("magadoom_001", "modules/gamification/whack_a_magat/foundup_manifest.json", "BASELINE_DECLARATIVE_ONLY"),
    ("antifafm_001", "modules/platform_integration/antifafm_broadcaster/foundup_manifest.json", "BASELINE_DECLARATIVE_ONLY"),
    ("voteballots", "modules/foundups/voteballots/foundup_manifest.json", "NEEDS_LABEL_RECONCILIATION"),
    ("trade", "modules/foundups/trade/foundup_manifest.json", "NEEDS_LABEL_RECONCILIATION"),
]

LABEL_RECONCILIATION_IDS = {"voteballots", "trade"}


def _load(rel_path: str) -> dict:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


def _valid_manifest() -> dict:
    """An in-memory manifest that PASSES validation; mutate one field per test."""
    module_path = "modules/foundups/example"
    return {
        "foundup_id": "example",
        "build_contract": {
            "contract_version": "0.1.0",
            "foundup_id": "example",
            "module_path": module_path,
            "owner_lane": "WRE",
            "status": "BASELINE_DECLARATIVE_ONLY",
            "build": {"mode": "no_build", "command": None, "notes": "x"},
            "test": {
                "command": ["python", "-m", "pytest", module_path + "/tests"],
                "required": True,
                "notes": "x",
            },
            "dry_run": {"required": True, "default": True, "command": None, "notes": "x"},
            "safe_mutation_surface": [module_path + "/**"],
            "forbidden_paths": [
                ".env",
                ".env.*",
                "main.py",
                "**/*_dae.py",
                "**/vendor/**",
                "**/credentials*",
                "**/secrets*",
            ],
            "required_gates": list(REQUIRED_GATES),
            "evidence_output": {
                "path": module_path + "/evidence/",
                "redaction_required": True,
                "notes": "x",
            },
            "readiness": {
                "manifest_ready": False,
                "build_ready": False,
                "autonomous_execution_ready": False,
                "reason": "x",
            },
        },
        "execution_routing": {
            "orchestrator": "openclaw",
            "executor": "hermes",
            "auditor": "ai_overseer",
            "wre_coordinator": True,
            "external_agent_allowed": False,
            "external_agent_contract_required": True,
            "declarative_only": True,
            "can_self_authorize": False,
            "build_plan_source": "modules/foundups/agent/src/build_plan_generator.py",
            "job_contract_source": "modules/communication/moltbot_bridge/src/foundup_job_contract.py",
            "notes": "x",
        },
    }


_EXAMPLE_PATH = "modules/foundups/example/foundup_manifest.json"


def _validate_mutated(mutator) -> ManifestValidationResult:
    data = _valid_manifest()
    mutator(data)
    return validate_manifest(data, manifest_path=_EXAMPLE_PATH)


# ---------------------------------------------------------------------------
# Sanity: the in-memory baseline is genuinely valid
# ---------------------------------------------------------------------------

def test_baseline_in_memory_manifest_is_valid():
    result = validate_manifest(_valid_manifest(), manifest_path=_EXAMPLE_PATH)
    assert result.ok, result.errors


# ---------------------------------------------------------------------------
# 1. All 6 updated manifests validate
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("foundup_id,rel_path,status", TARGET_MANIFESTS)
def test_all_six_manifests_validate(foundup_id, rel_path, status):
    result = validate_manifest_file(REPO_ROOT / rel_path)
    assert result.ok, f"{foundup_id} failed: {result.errors}"


# ---------------------------------------------------------------------------
# 2. foundup_id must match build_contract.foundup_id
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("foundup_id,rel_path,status", TARGET_MANIFESTS)
def test_foundup_id_matches_build_contract(foundup_id, rel_path, status):
    data = _load(rel_path)
    assert data["foundup_id"] == data["build_contract"]["foundup_id"] == foundup_id


def test_reject_foundup_id_mismatch():
    result = _validate_mutated(
        lambda d: d["build_contract"].__setitem__("foundup_id", "other")
    )
    assert not result.ok
    assert any("foundup_id" in e for e in result.errors)


# ---------------------------------------------------------------------------
# 3. Every manifest includes forbidden paths for .env, main.py, *_dae.py, vendor
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("foundup_id,rel_path,status", TARGET_MANIFESTS)
def test_forbidden_paths_coverage(foundup_id, rel_path, status):
    forbidden = _load(rel_path)["build_contract"]["forbidden_paths"]
    assert ".env" in forbidden
    assert "main.py" in forbidden
    assert any("_dae.py" in p for p in forbidden)
    assert any("vendor" in p for p in forbidden)


# ---------------------------------------------------------------------------
# 4-12. Negative controls
# ---------------------------------------------------------------------------

def test_reject_unknown_executor():
    result = _validate_mutated(
        lambda d: d["execution_routing"].__setitem__("executor", "totally_unknown")
    )
    assert not result.ok
    assert any("executor" in e for e in result.errors)


def test_reject_privileged_self_authorizing_executor():
    def mutate(d):
        d["execution_routing"]["executor"] = "root"
        d["execution_routing"]["can_self_authorize"] = True
    result = _validate_mutated(mutate)
    assert not result.ok
    assert any("executor" in e for e in result.errors)
    assert any("self_authorize" in e or "self-authorize" in e for e in result.errors)


def test_reject_missing_required_gate():
    def mutate(d):
        gates = list(d["build_contract"]["required_gates"])
        gates.remove("genesis_gate")
        d["build_contract"]["required_gates"] = gates
    result = _validate_mutated(mutate)
    assert not result.ok
    assert any("genesis_gate" in e for e in result.errors)


def test_reject_dry_run_default_false():
    result = _validate_mutated(
        lambda d: d["build_contract"]["dry_run"].__setitem__("default", False)
    )
    assert not result.ok
    assert any("dry_run.default" in e for e in result.errors)


def test_reject_external_agent_allowed_true():
    result = _validate_mutated(
        lambda d: d["execution_routing"].__setitem__("external_agent_allowed", True)
    )
    assert not result.ok
    assert any("external_agent_allowed" in e for e in result.errors)


def test_reject_build_ready_true():
    result = _validate_mutated(
        lambda d: d["build_contract"]["readiness"].__setitem__("build_ready", True)
    )
    assert not result.ok
    assert any("build_ready" in e for e in result.errors)


def test_reject_autonomous_execution_ready_true():
    result = _validate_mutated(
        lambda d: d["build_contract"]["readiness"].__setitem__(
            "autonomous_execution_ready", True
        )
    )
    assert not result.ok
    assert any("autonomous_execution_ready" in e for e in result.errors)


def test_reject_manifest_ready_true_without_promotion():
    data = _valid_manifest()
    data["build_contract"]["readiness"]["manifest_ready"] = True
    result = validate_manifest(data, manifest_path=_EXAMPLE_PATH)
    assert not result.ok
    assert any("manifest_ready" in e for e in result.errors)


@pytest.mark.parametrize("field_name", ["build", "test", "dry_run"])
def test_reject_shell_string_command(field_name):
    result = _validate_mutated(
        lambda d: d["build_contract"][field_name].__setitem__(
            "command", "python -m pytest && rm -rf /"
        )
    )
    assert not result.ok
    assert any(field_name in e and "shell string" in e for e in result.errors)


@pytest.mark.parametrize(
    "bad_argv",
    [
        ["python", "-m", "pytest", "x; rm -rf /"],
        ["python", "-c", "import os; os.system('id')"],
        ["python", "-m", "pytest", "$(whoami)"],
        ["sh", "-c", "echo hi && echo bye"],
    ],
)
def test_reject_shell_metacharacters_in_argv(bad_argv):
    result = _validate_mutated(
        lambda d: d["build_contract"]["test"].__setitem__("command", bad_argv)
    )
    assert not result.ok
    assert any("metacharacter" in e for e in result.errors)


def test_reject_gate_bypass_flag():
    result = _validate_mutated(
        lambda d: d["execution_routing"].__setitem__("allow_gate_bypass", True)
    )
    assert not result.ok
    assert any("bypass" in e for e in result.errors)


# ---------------------------------------------------------------------------
# 13. execution_routing is declarative only
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("foundup_id,rel_path,status", TARGET_MANIFESTS)
def test_execution_routing_declarative_only(foundup_id, rel_path, status):
    routing = _load(rel_path)["execution_routing"]
    assert routing["declarative_only"] is True
    assert routing["can_self_authorize"] is False
    assert routing["external_agent_allowed"] is False
    assert routing["orchestrator"] == "openclaw"
    assert routing["executor"] == "hermes"
    assert routing["auditor"] == "ai_overseer"


# ---------------------------------------------------------------------------
# 14. voteballots / trade flagged NEEDS_LABEL_RECONCILIATION
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("foundup_id,rel_path,status", TARGET_MANIFESTS)
def test_status_matches_expected(foundup_id, rel_path, status):
    actual = _load(rel_path)["build_contract"]["status"]
    assert actual == status
    if foundup_id in LABEL_RECONCILIATION_IDS:
        assert actual == "NEEDS_LABEL_RECONCILIATION"
        # Label conflict must NOT be smuggled into build trust.
        readiness = _load(rel_path)["build_contract"]["readiness"]
        assert readiness["build_ready"] is False
        assert readiness["autonomous_execution_ready"] is False


# ---------------------------------------------------------------------------
# 15-16. Validator source is read-only: no runtime imports, no exec/IO calls
# ---------------------------------------------------------------------------

def _validator_ast():
    return ast.parse(VALIDATOR_SOURCE.read_text(encoding="utf-8"))


def _imported_modules(tree):
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mods.add(node.module)
    return mods


def test_validator_imports_no_runtime_executors():
    mods = _imported_modules(_validator_ast())
    forbidden_markers = (
        "hermes",
        "openclaw",
        "ai_overseer",
        "job_consumer",
        "foundup_job_consumer",
        "build_plan_executor",
        "wre_core",
    )
    offenders = [
        m for m in mods if any(marker in m for marker in forbidden_markers)
    ]
    assert not offenders, f"validator imports runtime executors/consumers: {offenders}"


def test_validator_no_exec_process_network_or_write():
    tree = _validator_ast()

    # No banned module imports.
    banned_modules = {
        "subprocess", "socket", "ssl", "urllib", "requests", "http",
        "ftplib", "telnetlib", "ctypes", "importlib", "multiprocessing",
        "os", "sys", "shutil", "pty", "pickle", "marshal",
    }
    mods = _imported_modules(tree)
    bad_mods = {m for m in mods if m.split(".")[0] in banned_modules}
    assert not bad_mods, f"validator imports banned modules: {bad_mods}"

    # No banned builtin calls and no banned attribute calls.
    banned_names = {"open", "eval", "exec", "compile", "__import__", "input", "execfile"}
    banned_attrs = {
        "system", "popen", "Popen", "run", "call", "check_call", "check_output",
        "getoutput", "write", "writelines", "write_text", "write_bytes",
        "urlopen", "urlretrieve", "connect", "spawn", "fork", "execv", "execve",
        "remove", "unlink", "rmdir", "makedirs", "mkdir", "chmod", "kill",
    }
    name_offenders = []
    attr_offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in banned_names:
                name_offenders.append(func.id)
            elif isinstance(func, ast.Attribute) and func.attr in banned_attrs:
                attr_offenders.append(func.attr)
    assert not name_offenders, f"validator calls banned builtins: {name_offenders}"
    assert not attr_offenders, f"validator makes banned attr calls: {attr_offenders}"


def test_validator_result_is_pure_dataclass():
    # Re-validating the same manifest twice yields identical results (no state).
    data = _valid_manifest()
    snapshot = copy.deepcopy(data)
    first = validate_manifest(data, manifest_path=_EXAMPLE_PATH)
    second = validate_manifest(data, manifest_path=_EXAMPLE_PATH)
    assert first.ok and second.ok
    assert data == snapshot  # validation did not mutate input
