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
from modules.foundups.agent.src.foundup_manifest_validator import (
    _canonicalize_manifest_path_for_compare,
    _canonicalize_module_path,
    _expected_module_path_matches,
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


# ---------------------------------------------------------------------------
# 17. EXACT MODULE_PATH MATCHING (PR #772 hardening)
# ---------------------------------------------------------------------------
# Predecessor PR #772 identified the prior _expected_module_path_matches
# suffix-match fallback (parent.endswith("/" + norm_module)) as latent today
# but mandatory to remove before any consumer derives allowed_source_roots
# from build_contract.module_path. The four classes below pin:
#   - direct exact-match helper behavior (positive + negative)
#   - the explicit suffix-collision rejections required by the W6 dispatch
#   - canonical path normalization (harmless equivalents accepted; absolute,
#     UNC, ".." traversal, and shadow-prefix collisions rejected)
#   - a regression that proves a path the OLD suffix fallback would have
#     accepted is now rejected
# ---------------------------------------------------------------------------


class TestExactMatchHelperDirect:
    """Mechanically pin the exact-match boundary by calling the helper directly.

    Touching the helper from full-manifest paths is fine for the integration
    surface, but the trust boundary itself must be unit-pinned so future
    refactors cannot weaken it silently.
    """

    @pytest.mark.parametrize(
        "manifest_path,module_path",
        [
            (
                "modules/foundups/gotjunk/foundup_manifest.json",
                "modules/foundups/gotjunk",
            ),
            (
                "modules/foundups/kosei/foundup_manifest.json",
                "modules/foundups/kosei",
            ),
            (
                "modules/gamification/whack_a_magat/foundup_manifest.json",
                "modules/gamification/whack_a_magat",
            ),
            (
                "modules/platform_integration/antifafm_broadcaster/foundup_manifest.json",
                "modules/platform_integration/antifafm_broadcaster",
            ),
            (
                "modules/foundups/voteballots/foundup_manifest.json",
                "modules/foundups/voteballots",
            ),
            (
                "modules/foundups/trade/foundup_manifest.json",
                "modules/foundups/trade",
            ),
        ],
    )
    def test_real_manifest_locations_match_exactly(self, manifest_path, module_path):
        assert _expected_module_path_matches(manifest_path, module_path)

    def test_canonical_module_path_strips_harmless_normalization(self):
        # leading "./", repeated "/", "." segment, backslashes -- all collapse.
        assert _canonicalize_module_path("./modules/foundups/gotjunk") == (
            "modules/foundups/gotjunk"
        )
        assert _canonicalize_module_path("modules//foundups/gotjunk") == (
            "modules/foundups/gotjunk"
        )
        assert _canonicalize_module_path("modules/foundups/./gotjunk") == (
            "modules/foundups/gotjunk"
        )
        assert _canonicalize_module_path("modules\\foundups\\gotjunk") == (
            "modules/foundups/gotjunk"
        )

    def test_canonical_module_path_rejects_unsafe_forms(self):
        # absolute drive / leading-slash / UNC after backslash-convert /
        # ".." traversal / empty / non-string -- all rejected.
        for bad in (
            "../modules/foundups/gotjunk",
            "O:/Foundups-Agent/modules/foundups/gotjunk",
            "/modules/foundups/gotjunk",
            "\\\\server\\share\\modules\\foundups\\gotjunk",
            "",
            "   ",  # whitespace-only segments are not a valid module path
            None,
        ):
            assert _canonicalize_module_path(bad) is None, f"accepted: {bad!r}"

    def test_canonical_module_path_rejects_internal_traversal(self):
        # ".." anywhere in the path, not just leading, must be rejected.
        for bad in (
            "modules/foundups/../foundups/gotjunk",
            "modules/foundups/gotjunk/..",
            "modules/../etc/passwd",
        ):
            assert _canonicalize_module_path(bad) is None, f"accepted: {bad!r}"

    def test_canonical_manifest_path_strips_known_repo_root(self):
        # When a manifest path is rooted under the validator's known repo root,
        # the prefix is stripped (case-insensitive on Windows-ish drive letter).
        repo = _REPO_ROOT_FOR_TEST.as_posix()
        assert _canonicalize_manifest_path_for_compare(
            repo + "/modules/foundups/gotjunk/foundup_manifest.json"
        ) == "modules/foundups/gotjunk/foundup_manifest.json"

    def test_helper_rejects_when_canonical_module_is_none(self):
        # If module_path canonicalizes to None, no match is possible.
        assert not _expected_module_path_matches(
            "modules/foundups/gotjunk/foundup_manifest.json", "../modules/foundups/gotjunk"
        )
        assert not _expected_module_path_matches(
            "modules/foundups/gotjunk/foundup_manifest.json", "/modules/foundups/gotjunk"
        )
        assert not _expected_module_path_matches(
            "modules/foundups/gotjunk/foundup_manifest.json", "O:/x/modules/foundups/gotjunk"
        )


class TestSuffixCollisionRejected:
    """Suffix-only path matches MUST be rejected (PR #772 hardening).

    Under the prior implementation, a parent path that ended with
    "/" + module_path would have passed. With exact-only matching, those
    cases must now fail. These are the explicit cases the W6 dispatch and
    Addendum A enumerate.
    """

    def test_shadow_prefix_collision_with_gotjunk(self):
        """A manifest at tmp/shadow/modules/foundups/gotjunk declaring
        module_path=modules/foundups/gotjunk must be rejected. The shadow
        prefix means the parent only suffix-matches the declared module."""
        assert not _expected_module_path_matches(
            "tmp/shadow/modules/foundups/gotjunk/foundup_manifest.json",
            "modules/foundups/gotjunk",
        )

    def test_cross_domain_suffix_with_whack_a_magat(self):
        """A manifest at tmp/modules/foundups/x/whack_a_magat declaring
        module_path=modules/gamification/whack_a_magat must be rejected
        (parent ends with the basename but not with the declared module)."""
        assert not _expected_module_path_matches(
            "tmp/modules/foundups/x/whack_a_magat/foundup_manifest.json",
            "modules/gamification/whack_a_magat",
        )

    def test_basename_only_match_rejected(self):
        """Declaring module_path as a bare basename that happens to match the
        manifest directory's last segment must be rejected; the entire
        repo-relative path must match."""
        assert not _expected_module_path_matches(
            "modules/foundups/gotjunk/foundup_manifest.json",
            "gotjunk",
        )

    def test_extra_suffix_segment_rejected(self):
        """A module_path with an extra trailing segment that the parent does
        not have must be rejected."""
        assert not _expected_module_path_matches(
            "modules/foundups/gotjunk/foundup_manifest.json",
            "modules/foundups/gotjunk_extra",
        )

    def test_shadow_directory_collision_rejected(self):
        """A module_path placed under a renamed parent (foundups_shadow) must
        not validate against a real foundups/<name> manifest."""
        assert not _expected_module_path_matches(
            "modules/foundups/gotjunk/foundup_manifest.json",
            "modules/foundups_shadow/gotjunk",
        )

    def test_suffix_collision_fails_through_full_validator(self):
        """End-to-end through validate_manifest: a shadow-prefixed manifest
        path with a clean module_path must fail validation with a clear
        module_path error message."""
        data = _valid_manifest()
        result = validate_manifest(
            data,
            manifest_path="tmp/shadow/modules/foundups/example/foundup_manifest.json",
        )
        assert not result.ok
        assert any("module_path" in e for e in result.errors)


class TestCanonicalPathNormalization:
    """Addendum A: harmless equivalents accepted; absolute, UNC, traversal,
    and shadow-prefix forms rejected."""

    @pytest.mark.parametrize(
        "module_variant",
        [
            "./modules/foundups/gotjunk",
            "modules//foundups/gotjunk",
            "modules/foundups/./gotjunk",
            "modules\\foundups\\gotjunk",
            "modules/foundups/gotjunk/",  # trailing slash
            "modules/foundups/gotjunk",   # baseline canonical
        ],
    )
    def test_harmless_module_path_normalizations_accepted(self, module_variant):
        assert _expected_module_path_matches(
            "modules/foundups/gotjunk/foundup_manifest.json", module_variant
        )

    @pytest.mark.parametrize(
        "bad_module_path",
        [
            "../modules/foundups/gotjunk",
            "../../modules/foundups/gotjunk",
            "O:/Foundups-Agent/modules/foundups/gotjunk",
            "C:/Foundups-Agent/modules/foundups/gotjunk",
            "/modules/foundups/gotjunk",
            "\\\\server\\share\\modules\\foundups\\gotjunk",
            "tmp/shadow/modules/foundups/gotjunk",
            "modules/foundups_shadow/gotjunk",
            "modules/foundups/gotjunk_extra",
            "modules/foundups/../foundups/gotjunk",
        ],
    )
    def test_unsafe_or_shadow_module_paths_rejected(self, bad_module_path):
        assert not _expected_module_path_matches(
            "modules/foundups/gotjunk/foundup_manifest.json", bad_module_path
        )

    def test_repo_root_absolute_manifest_with_clean_module_still_matches(self):
        """A manifest passed in as an absolute path under the known repo
        root must validate against a clean repo-relative module_path."""
        absolute_manifest = (
            _REPO_ROOT_FOR_TEST.as_posix()
            + "/modules/foundups/gotjunk/foundup_manifest.json"
        )
        assert _expected_module_path_matches(
            absolute_manifest, "modules/foundups/gotjunk"
        )


class TestOldSuffixBehaviorRegression:
    """Prove the OLD suffix fallback would have accepted these, and the NEW
    exact-only check rejects them. Mechanical regression pin."""

    @staticmethod
    def _old_suffix_match(manifest_path: str, module_path: str) -> bool:
        """Recompute the legacy logic locally so the assertion below is
        mechanical: we are not asking the validator about the old behavior
        (it no longer exists); we are asking the dispatch's regression
        guarantee directly."""
        from pathlib import PurePosixPath as _PP
        nm = manifest_path.replace("\\", "/")
        no = module_path.replace("\\", "/").rstrip("/")
        if not no:
            return False
        parent = _PP(nm).parent.as_posix()
        return parent == no or parent.endswith("/" + no)

    def test_suffix_match_that_old_validator_would_accept_is_rejected(self):
        """A shadow-prefixed manifest with a clean module_path: the OLD
        suffix fallback would have accepted; the NEW exact-only rule
        rejects."""
        manifest_path = "tmp/shadow/modules/foundups/gotjunk/foundup_manifest.json"
        module_path = "modules/foundups/gotjunk"
        # Old: would have accepted (parent ends with "/" + module_path).
        assert self._old_suffix_match(manifest_path, module_path)
        # New: rejected (exact-only).
        assert not _expected_module_path_matches(manifest_path, module_path)

    def test_deep_shadow_suffix_match_old_accepted_new_rejected(self):
        """Same property, deeper shadow nesting, to catch any partial fix."""
        manifest_path = (
            "tmp/x/y/z/modules/platform_integration/antifafm_broadcaster"
            "/foundup_manifest.json"
        )
        module_path = "modules/platform_integration/antifafm_broadcaster"
        assert self._old_suffix_match(manifest_path, module_path)
        assert not _expected_module_path_matches(manifest_path, module_path)

    def test_exact_match_still_accepted_under_new_rule(self):
        """Negative control: a clean exact-match path that BOTH old and new
        accept stays accepting -- prevents over-tightening."""
        manifest_path = "modules/foundups/kosei/foundup_manifest.json"
        module_path = "modules/foundups/kosei"
        assert self._old_suffix_match(manifest_path, module_path)
        assert _expected_module_path_matches(manifest_path, module_path)


# Repo root for tests that need to build an absolute manifest path. Computed
# the same way the validator computes its repo root so the two stay aligned.
_REPO_ROOT_FOR_TEST = REPO_ROOT
