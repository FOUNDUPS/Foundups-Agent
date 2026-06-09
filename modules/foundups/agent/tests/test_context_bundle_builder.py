#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ContextBundle Builder Tests -- Read-Only Provenance Envelope.

Covers WRE_CONTEXT_BUNDLE_BUILDER_PHASE1 (W6) requirements:

  1. Valid bundle builds for the validated declarative manifests.
  2. Bundle contains refs+sha256 only; no file bodies.
  3. Bundle includes manifest ref.
  4. Bundle includes safe declared test refs where present.
  5. Bundle excludes forbidden paths.
  6. Bundle rejects an invalid manifest validation.
  7. Bundle rejects readiness promotion.
  8. Bundle rejects external_agent_allowed=true.
  9. Bundle rejects can_self_authorize=true.
 10. Bundle rejects missing required gates.
 11. Bundle rejects module_path mismatch via #773 validator.
 12. Bundle never serializes gate-pass booleans.
 13. Bundle never includes CABR / payout / DAO readiness.
 14. max_context_bytes cap is enforced (over-cap -> exclusions recorded).
 15. File outside module_path is excluded unless explicitly allowed as
     provenance (the manifest).
 16. Path traversal is rejected.
 17. Symlink escaping module_path is rejected.
 18. Builder does not import Hermes / OpenClaw / WRE consumer / AI Overseer.
 19. Builder does not call subprocess, Popen, os.system, eval, exec,
     importlib dynamic loading, network, or runtime command exec.
 20. bundle_id is deterministic (sha256-derived; not wall-clock or random).
 21. sha256 is stream-computed; oversized files are recorded as excluded.
 22. voteballots and trade build at the declarative level but
     readiness_flags stay False (NEEDS_LABEL_RECONCILIATION not promoted).
 23. No consumer wiring; no build command executed.

Plus the #774 carry-forward special test: a legacy job-payload module_path
must NEVER be the authority; the bundle's module_path comes from the
validated manifest only.

WSP 97 TRUTH BOUNDARIES:
  - These tests EXECUTE nothing in the builder beyond pure construction.
  - No skip / no xfail on any security assertion.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import json
import os
import sys
from pathlib import Path

import pytest

from modules.foundups.agent.src.context_bundle_builder import (
    BUNDLE_VERSION,
    BUILDER_VERSION,
    DEFAULT_MAX_CONTEXT_BYTES,
    PER_FILE_READ_CAP_BYTES,
    ContextBundle,
    ContextBundleRejected,
    FileRef,
    ProvenanceRecord,
    build_context_bundle,
)

# Repo root: tests/ -> agent/ -> foundups/ -> modules/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[4]
BUILDER_SOURCE = (
    Path(__file__).resolve().parents[1] / "src" / "context_bundle_builder.py"
)

# Real manifests (declarative). All 6 referenced in TARGET_MANIFESTS.
TARGET_MANIFESTS = [
    ("gotjunk_001", "modules/foundups/gotjunk/foundup_manifest.json", "BASELINE_DECLARATIVE_ONLY"),
    ("kosei", "modules/foundups/kosei/foundup_manifest.json", "BASELINE_DECLARATIVE_ONLY"),
    ("magadoom_001", "modules/gamification/whack_a_magat/foundup_manifest.json", "BASELINE_DECLARATIVE_ONLY"),
    ("antifafm_001", "modules/platform_integration/antifafm_broadcaster/foundup_manifest.json", "BASELINE_DECLARATIVE_ONLY"),
    ("voteballots", "modules/foundups/voteballots/foundup_manifest.json", "NEEDS_LABEL_RECONCILIATION"),
    ("trade", "modules/foundups/trade/foundup_manifest.json", "NEEDS_LABEL_RECONCILIATION"),
]
RECONCILIATION_IDS = {"voteballots", "trade"}

FIXED_T0 = "2026-06-09T00:00:00Z"


@pytest.fixture
def tmp_repo_root(tmp_path, monkeypatch):
    """Repoint the validator's repo-root constant at ``tmp_path`` so
    manifests written under ``tmp_path/modules/...`` pass the validator's
    canonical exact-match check. Restored automatically by monkeypatch.
    """
    from modules.foundups.agent.src import foundup_manifest_validator as v
    monkeypatch.setattr(v, "_REPO_ROOT_POSIX", tmp_path.resolve().as_posix())
    return tmp_path


def _real_manifest(rel_path: str) -> Path:
    return REPO_ROOT / rel_path


def _load_manifest_data(rel_path: str) -> dict:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


def _write_tmp_manifest(tmp_dir: Path, foundup_id: str, module_rel: str, mutator=None) -> Path:
    """Create a tmp manifest derived from gotjunk with optional mutation.

    The manifest is placed under ``tmp_dir / module_rel / foundup_manifest.json``
    so the validator's exact-match path check passes (or fails, if the
    test intentionally breaks it via ``mutator``).
    """
    base = _load_manifest_data("modules/foundups/gotjunk/foundup_manifest.json")
    base["foundup_id"] = foundup_id
    base["build_contract"]["foundup_id"] = foundup_id
    base["build_contract"]["module_path"] = module_rel
    # No safe_mutation_surface change needed; doesn't affect builder.
    if mutator is not None:
        mutator(base)
    target_dir = tmp_dir / module_rel
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = target_dir / "foundup_manifest.json"
    manifest_path.write_text(json.dumps(base, indent=2), encoding="utf-8")
    return manifest_path


# ===========================================================================
# 1, 2, 3, 4. Positive: real manifests build; refs+sha256 only; manifest ref
# ===========================================================================


class TestRealManifestsBuild:
    """Real declarative manifests build into bundles."""

    @pytest.mark.parametrize("foundup_id,rel_path,status", TARGET_MANIFESTS)
    def test_each_manifest_builds(self, foundup_id, rel_path, status):
        bundle = build_context_bundle(
            _real_manifest(rel_path), REPO_ROOT, created_at=FIXED_T0
        )
        assert isinstance(bundle, ContextBundle)
        assert bundle.foundup_id == foundup_id
        assert bundle.build_contract_status == status

    @pytest.mark.parametrize("foundup_id,rel_path,status", TARGET_MANIFESTS)
    def test_bundle_carries_only_refs_no_file_bodies(self, foundup_id, rel_path, status):
        bundle = build_context_bundle(
            _real_manifest(rel_path), REPO_ROOT, created_at=FIXED_T0
        )
        for ref in bundle.included_file_refs:
            allowed_attrs = {"path", "sha256", "size_bytes", "role"}
            actual_attrs = {f.name for f in ref.__dataclass_fields__.values()}
            assert actual_attrs == allowed_attrs, (
                f"FileRef carries forbidden attributes: {actual_attrs - allowed_attrs}"
            )
            assert isinstance(ref.sha256, str) and len(ref.sha256) == 64
            assert ref.size_bytes >= 0
            # Round-trip via to_dict: no "body" or "content" key may appear.
        d = bundle.to_dict()
        for r in d["included_file_refs"]:
            assert set(r.keys()) == {"path", "sha256", "size_bytes", "role"}
            assert "body" not in r and "content" not in r

    @pytest.mark.parametrize("foundup_id,rel_path,status", TARGET_MANIFESTS)
    def test_bundle_includes_manifest_ref(self, foundup_id, rel_path, status):
        bundle = build_context_bundle(
            _real_manifest(rel_path), REPO_ROOT, created_at=FIXED_T0
        )
        manifest_refs = [r for r in bundle.included_file_refs if r.role == "manifest"]
        assert len(manifest_refs) == 1
        assert manifest_refs[0].path == rel_path

    def test_bundle_includes_test_refs_when_declared(self):
        """gotjunk's test.command points at modules/foundups/gotjunk/tests.
        The walker collects test_*.py files inside module_path."""
        bundle = build_context_bundle(
            _real_manifest("modules/foundups/gotjunk/foundup_manifest.json"),
            REPO_ROOT,
            created_at=FIXED_T0,
        )
        test_refs = [r for r in bundle.included_file_refs if r.role == "test"]
        # At least one test ref under module_path/tests/
        assert any(
            r.path.startswith("modules/foundups/gotjunk/tests/") for r in test_refs
        ), "expected at least one declared test ref under gotjunk/tests"


# ===========================================================================
# 5, 14. Forbidden-path exclusion + total-cap fail-closed
# ===========================================================================


class TestForbiddenPathsAndCap:
    """Forbidden paths excluded; over-cap files recorded, not silently dropped."""

    def test_forbidden_path_screen_excludes_secrets_like_paths(self, tmp_repo_root):
        """Plant a synthetic module containing a credentials* file. The
        bundle's path screen excludes it. (The validator allows
        forbidden_paths in the manifest declaration; this test pins the
        BUILDER's path screen as the second line of defense.)"""
        manifest_rel = "modules/foundups/example"
        manifest_path = _write_tmp_manifest(tmp_repo_root, "example_001", manifest_rel)
        mod_dir = tmp_repo_root / manifest_rel
        (mod_dir / "credentials.json").write_text("{}", encoding="utf-8")
        bundle = build_context_bundle(
            manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
        )
        for r in bundle.included_file_refs:
            assert "credentials" not in r.path.lower()

    def test_max_context_bytes_cap_records_exclusion(self, tmp_repo_root):
        """A 1-byte cap forces every non-trivial file to be excluded under
        ``over_total_cap``. The manifest itself is bigger than 1 byte
        and is the first candidate; it should be the first
        over-cap exclusion."""
        manifest_rel = "modules/foundups/example"
        manifest_path = _write_tmp_manifest(tmp_repo_root, "example_001", manifest_rel)
        bundle = build_context_bundle(
            manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0, max_context_bytes=1
        )
        # The cap is fail-closed: total_referenced_bytes <= max_context_bytes.
        assert bundle.total_referenced_bytes <= 1
        # At least one exclusion was recorded under over_total_cap.
        assert bundle.excluded_paths_summary.get("over_total_cap", 0) >= 1

    def test_cap_never_exceeded_even_when_close(self, tmp_repo_root):
        """Property: included_file_refs sizes sum to <= max_context_bytes."""
        manifest_rel = "modules/foundups/example"
        manifest_path = _write_tmp_manifest(tmp_repo_root, "example_001", manifest_rel)
        bundle = build_context_bundle(
            manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0, max_context_bytes=4096
        )
        total = sum(r.size_bytes for r in bundle.included_file_refs)
        assert total == bundle.total_referenced_bytes
        assert total <= 4096


# ===========================================================================
# 6 - 11. Validator rejection paths
# ===========================================================================


class TestValidatorRejectionsPropagate:
    """Builder calls the #773 validator and refuses to build on failure."""

    def test_invalid_manifest_rejected(self, tmp_repo_root):
        """Mutate the manifest to break a required gate -> validator
        fails -> builder rejects with ContextBundleRejected."""
        def mutate(data):
            gates = list(data["build_contract"]["required_gates"])
            gates.remove("genesis_gate")
            data["build_contract"]["required_gates"] = gates

        manifest_rel = "modules/foundups/example"
        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", manifest_rel, mutator=mutate
        )
        with pytest.raises(ContextBundleRejected):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    def test_readiness_build_ready_true_rejected(self, tmp_repo_root):
        def mutate(d):
            d["build_contract"]["readiness"]["build_ready"] = True

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    def test_readiness_autonomous_execution_ready_true_rejected(self, tmp_repo_root):
        def mutate(d):
            d["build_contract"]["readiness"]["autonomous_execution_ready"] = True

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    def test_readiness_manifest_ready_true_rejected(self, tmp_repo_root):
        def mutate(d):
            d["build_contract"]["readiness"]["manifest_ready"] = True

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    def test_external_agent_allowed_true_rejected(self, tmp_repo_root):
        def mutate(d):
            d["execution_routing"]["external_agent_allowed"] = True

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    def test_can_self_authorize_true_rejected(self, tmp_repo_root):
        def mutate(d):
            d["execution_routing"]["can_self_authorize"] = True

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    def test_module_path_mismatch_rejected_via_773_validator(self, tmp_repo_root):
        """Manifest at one location declares a DIFFERENT module_path.
        The #773 validator's exact-match check fails; builder rejects."""
        target_dir = tmp_repo_root / "modules" / "foundups" / "actual"
        target_dir.mkdir(parents=True, exist_ok=True)
        base = _load_manifest_data("modules/foundups/gotjunk/foundup_manifest.json")
        base["foundup_id"] = "example_001"
        base["build_contract"]["foundup_id"] = "example_001"
        base["build_contract"]["module_path"] = "modules/foundups/different"
        manifest_path = target_dir / "foundup_manifest.json"
        manifest_path.write_text(json.dumps(base, indent=2), encoding="utf-8")
        with pytest.raises(ContextBundleRejected):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )


# ===========================================================================
# 12, 13. Bundle never serializes gate-pass authority / CABR / payout / DAO
# ===========================================================================


class TestNoGatePassNoCabrNoPayoutNoDao:
    """Truth-field guards: the bundle MUST NOT contain authority booleans."""

    def test_bundle_to_dict_has_no_gate_pass_keys(self):
        bundle = build_context_bundle(
            _real_manifest("modules/foundups/gotjunk/foundup_manifest.json"),
            REPO_ROOT,
            created_at=FIXED_T0,
        )
        d = bundle.to_dict()
        forbidden_keys = {
            "gate_passed", "gates_passed", "security_passed", "permission_passed",
            "dry_run_passed", "build_passed", "verification_complete",
            "real_execution_performed",
            "cabr_ready", "cabr_passed",
            "payout_ready", "payout_passed",
            "dao_ready", "dao_passed",
        }
        # Recurse the dict and ensure no key matches the forbidden set.
        stack = [d]
        offenders = []
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                for k, v in node.items():
                    if k in forbidden_keys:
                        offenders.append(k)
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(node, list):
                stack.extend(node)
        assert offenders == [], f"forbidden authority keys present: {offenders}"

    def test_required_gates_to_recheck_carries_names_not_booleans(self):
        """The bundle lists gate NAMES for downstream re-checking. None of
        those names may appear as ``True``-valued keys anywhere else."""
        bundle = build_context_bundle(
            _real_manifest("modules/foundups/gotjunk/foundup_manifest.json"),
            REPO_ROOT,
            created_at=FIXED_T0,
        )
        gate_names = list(bundle.required_gates_to_recheck)
        assert len(gate_names) > 0
        # All elements are strings (gate names), never booleans.
        for n in gate_names:
            assert isinstance(n, str)


# ===========================================================================
# 15. File outside module_path excluded (except manifest provenance)
# ===========================================================================


class TestOutsideModulePathExcluded:
    """Symlinks / paths outside module_path do not enter the bundle as
    source/test/doc refs; only the manifest itself is provenance-allowed
    if it lives elsewhere."""

    def test_doc_outside_module_dir_is_not_included(self, tmp_repo_root):
        """Plant a README OUTSIDE the module dir and confirm it is not
        present in included_file_refs. The builder only looks at
        ``module_root / README.md``; an unrelated README anywhere else
        is invisible to it."""
        manifest_rel = "modules/foundups/example"
        manifest_path = _write_tmp_manifest(tmp_repo_root, "example_001", manifest_rel)
        outside_readme = tmp_repo_root / "OUTSIDE_README.md"
        outside_readme.write_text("# not part of module", encoding="utf-8")
        bundle = build_context_bundle(
            manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
        )
        for r in bundle.included_file_refs:
            assert "OUTSIDE_README" not in r.path


# ===========================================================================
# 16. Path traversal rejected
# ===========================================================================


class TestPathTraversalRejected:
    """Manifest paths or module_path values containing ``..`` must not
    produce a bundle. The validator already rejects ``..`` in
    module_path; this test pins the rejection at the builder level too."""

    def test_module_path_with_parent_traversal_rejected(self, tmp_repo_root):
        """Plant a manifest whose build_contract.module_path contains
        ``..``. The validator rejects -> builder raises."""
        target_dir = tmp_repo_root / "modules" / "foundups" / "example"
        target_dir.mkdir(parents=True, exist_ok=True)
        base = _load_manifest_data("modules/foundups/gotjunk/foundup_manifest.json")
        base["foundup_id"] = "example_001"
        base["build_contract"]["foundup_id"] = "example_001"
        base["build_contract"]["module_path"] = "modules/foundups/../foundups/example"
        manifest_path = target_dir / "foundup_manifest.json"
        manifest_path.write_text(json.dumps(base, indent=2), encoding="utf-8")
        with pytest.raises(ContextBundleRejected):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )


# ===========================================================================
# 17. Symlink escape rejected
# ===========================================================================


class TestSymlinkEscapeRejected:
    """A symlink under the module that points outside module_root must
    not be hashed/included. This test is gated on platform symlink
    support (Windows may require admin; we use os.symlink and
    skip-on-OSError but assert if support exists)."""

    def _try_create_symlink(self, link: Path, target: Path) -> bool:
        try:
            os.symlink(target, link)
            return True
        except (OSError, NotImplementedError):
            return False

    def test_symlink_pointing_outside_module_is_excluded(self, tmp_repo_root):
        """Environment-gated integration: on systems that support symlinks
        the README symlink resolving outside the module is excluded.
        The boundary itself is mechanically pinned in
        ``test_is_path_within_helper_rejects_path_outside_base`` below;
        this integration test exercises the resolve()+is_relative_to
        path through the builder end-to-end where supported."""
        manifest_rel = "modules/foundups/example"
        manifest_path = _write_tmp_manifest(tmp_repo_root, "example_001", manifest_rel)
        outside = tmp_repo_root / "OUTSIDE.txt"
        outside.write_text("forbidden body", encoding="utf-8")
        link = tmp_repo_root / manifest_rel / "README.md"
        if not self._try_create_symlink(link, outside):
            # Environment cannot create symlinks. The mechanical
            # boundary is pinned by the helper-level test below; this
            # path through the builder simply has nothing to do.
            return
        bundle = build_context_bundle(
            manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
        )
        for r in bundle.included_file_refs:
            assert r.role != "readme", (
                f"symlink-escaping README was included: {r.path}"
            )

    def test_is_path_within_helper_rejects_path_outside_base(self):
        """Helper-level pin (no symlink creation needed): the
        ``_is_path_within`` boundary returns False for a path that does
        not sit under the base. This is what the symlink-escape rejection
        rides on; if this helper ever regresses, the integration test
        above will also break in environments that support symlinks."""
        from modules.foundups.agent.src.context_bundle_builder import _is_path_within
        base = REPO_ROOT / "modules" / "foundups" / "gotjunk"
        child_inside = base / "INTERFACE.md"
        child_outside = REPO_ROOT / "modules" / "foundups" / "kosei" / "INTERFACE.md"
        assert _is_path_within(child_inside, base) is True
        assert _is_path_within(child_outside, base) is False
        assert _is_path_within(REPO_ROOT, base) is False


# ===========================================================================
# 18, 19. Import-safety / no-execution AST self-check
# ===========================================================================


class TestBuilderImportAndExecutionSafety:
    """Static AST scan: builder must not import runtime executors and must
    not call any process-spawn / network / dynamic-import / file-write API."""

    def _builder_tree(self):
        return ast.parse(BUILDER_SOURCE.read_text(encoding="utf-8"))

    def _imported_modules(self, tree):
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mods.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mods.add(node.module)
        return mods

    def test_builder_imports_no_runtime_executors(self):
        mods = self._imported_modules(self._builder_tree())
        forbidden = (
            "hermes",
            "openclaw",
            "ai_overseer",
            "job_consumer",
            "foundup_job_consumer",
            "build_plan_executor",
            "wre_core",
            "wre_master_orchestrator",
            "build_plan_swarm",
        )
        hits = [m for m in mods if any(f in m for f in forbidden)]
        assert hits == [], f"builder imports runtime executors/consumers: {hits}"

    def test_builder_no_subprocess_network_dynamic_import_or_write(self):
        tree = self._builder_tree()
        mods = self._imported_modules(tree)
        banned_top = {
            "subprocess", "socket", "ssl", "urllib", "requests", "http",
            "ftplib", "telnetlib", "ctypes", "importlib", "multiprocessing",
            "pty", "pickle", "marshal",
        }
        bad = {m for m in mods if m.split(".")[0] in banned_top}
        assert not bad, f"builder imports banned modules: {bad}"

        banned_names = {"eval", "exec", "compile", "__import__", "input", "execfile"}
        banned_attrs = {
            "system", "popen", "Popen", "run", "call", "check_call", "check_output",
            "getoutput", "write_text", "write_bytes", "writelines",
            "urlopen", "urlretrieve", "connect", "spawn", "fork", "execv", "execve",
            "remove", "unlink", "rmdir", "makedirs", "chmod", "kill",
        }
        name_off = []
        attr_off = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                if isinstance(f, ast.Name) and f.id in banned_names:
                    name_off.append(f.id)
                elif isinstance(f, ast.Attribute) and f.attr in banned_attrs:
                    attr_off.append(f.attr)
        assert not name_off, f"builder calls banned names: {name_off}"
        assert not attr_off, f"builder calls banned attrs: {attr_off}"


# ===========================================================================
# 20. bundle_id deterministic (no wall-clock, no random)
# ===========================================================================


class TestBundleIdDeterministic:
    """Identical inputs (manifest + created_at + max_context_bytes) must
    produce the SAME bundle_id. Different created_at does NOT change
    bundle_id (created_at is recorded but not part of the bundle_id
    fingerprint). Different manifest content -> different bundle_id."""

    def test_same_inputs_yield_same_bundle_id(self):
        a = build_context_bundle(
            _real_manifest("modules/foundups/gotjunk/foundup_manifest.json"),
            REPO_ROOT,
            created_at=FIXED_T0,
        )
        b = build_context_bundle(
            _real_manifest("modules/foundups/gotjunk/foundup_manifest.json"),
            REPO_ROOT,
            created_at=FIXED_T0,
        )
        assert a.bundle_id == b.bundle_id

    def test_bundle_id_is_sha256_of_documented_components(self):
        b = build_context_bundle(
            _real_manifest("modules/foundups/gotjunk/foundup_manifest.json"),
            REPO_ROOT,
            created_at=FIXED_T0,
        )
        expected = hashlib.sha256(
            (b.source_manifest_sha256 + "|" + b.module_path + "|" + BUNDLE_VERSION).encode("utf-8")
        ).hexdigest()
        assert b.bundle_id == expected

    def test_bundle_id_not_affected_by_created_at(self):
        """created_at is recorded for provenance but NOT part of the
        bundle_id fingerprint, so caller-injected timestamps do not
        cause bundle_id drift."""
        a = build_context_bundle(
            _real_manifest("modules/foundups/gotjunk/foundup_manifest.json"),
            REPO_ROOT,
            created_at="2026-01-01T00:00:00Z",
        )
        b = build_context_bundle(
            _real_manifest("modules/foundups/gotjunk/foundup_manifest.json"),
            REPO_ROOT,
            created_at="2099-12-31T23:59:59Z",
        )
        assert a.bundle_id == b.bundle_id
        # But created_at IS recorded distinctly.
        assert a.created_at != b.created_at

    def test_different_manifests_yield_different_bundle_ids(self):
        a = build_context_bundle(
            _real_manifest("modules/foundups/gotjunk/foundup_manifest.json"),
            REPO_ROOT,
            created_at=FIXED_T0,
        )
        b = build_context_bundle(
            _real_manifest("modules/foundups/kosei/foundup_manifest.json"),
            REPO_ROOT,
            created_at=FIXED_T0,
        )
        assert a.bundle_id != b.bundle_id

    def test_required_created_at_argument(self):
        """``created_at`` is required and rejects empty string."""
        with pytest.raises(TypeError):
            # missing required keyword argument
            build_context_bundle(  # type: ignore[call-arg]
                _real_manifest("modules/foundups/gotjunk/foundup_manifest.json"),
                REPO_ROOT,
            )
        with pytest.raises(ContextBundleRejected):
            build_context_bundle(
                _real_manifest("modules/foundups/gotjunk/foundup_manifest.json"),
                REPO_ROOT,
                created_at="",
            )
        with pytest.raises(ContextBundleRejected):
            build_context_bundle(
                _real_manifest("modules/foundups/gotjunk/foundup_manifest.json"),
                REPO_ROOT,
                created_at="   ",
            )

    def test_builder_does_not_call_time_or_random(self):
        """Static check: builder source must not import time / datetime
        for identity-field population, nor random."""
        tree = ast.parse(BUILDER_SOURCE.read_text(encoding="utf-8"))
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    mods.add(a.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mods.add(node.module)
        for forbidden in ("time", "datetime", "random", "secrets", "uuid"):
            assert forbidden not in mods, (
                f"builder imports nondeterministic module: {forbidden}"
            )


# ===========================================================================
# 21. sha256 streamed; oversized excluded
# ===========================================================================


class TestStreamHashAndOversized:
    """The hash helper must use streaming reads. Files larger than the
    per-file read cap are recorded as excluded (oversized) without ever
    opening the full body."""

    def test_oversized_file_is_excluded_not_full_loaded(self, tmp_repo_root, monkeypatch):
        """Patch PER_FILE_READ_CAP_BYTES to a value that fits the manifest
        and the validator-provenance file but not an outsized README.
        The builder must record an ``oversized`` exclusion for the README
        and must NOT include it."""
        from modules.foundups.agent.src import context_bundle_builder as cbb

        manifest_rel = "modules/foundups/example"
        manifest_path = _write_tmp_manifest(tmp_repo_root, "example_001", manifest_rel)

        # Cap must fit both the manifest and the validator source (the
        # builder hashes the validator for provenance), but be smaller
        # than the outsized README we plant below.
        validator_size = (
            Path(__file__).resolve().parents[1] / "src" / "foundup_manifest_validator.py"
        ).stat().st_size
        manifest_size = manifest_path.stat().st_size
        cap = max(manifest_size, validator_size) + 1024
        monkeypatch.setattr(cbb, "PER_FILE_READ_CAP_BYTES", cap)

        big_readme = tmp_repo_root / manifest_rel / "README.md"
        big_readme.write_text("x" * (cap + 4096), encoding="utf-8")  # > cap

        bundle = build_context_bundle(
            manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
        )
        for r in bundle.included_file_refs:
            assert r.role != "readme"
        assert bundle.excluded_paths_summary.get("oversized", 0) >= 1

    def test_stream_hash_function_uses_chunked_reads(self):
        """AST scan: _stream_sha256 uses f.read(chunk) inside a while loop
        (no full-body read in one shot via read() without arg)."""
        tree = ast.parse(BUILDER_SOURCE.read_text(encoding="utf-8"))
        found_stream_hash = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_stream_sha256":
                found_stream_hash = True
                # Inspect: must contain a While loop with f.read(...) inside.
                has_while_with_chunked_read = False
                for sub in ast.walk(node):
                    if isinstance(sub, ast.While):
                        for inner in ast.walk(sub):
                            if (
                                isinstance(inner, ast.Call)
                                and isinstance(inner.func, ast.Attribute)
                                and inner.func.attr == "read"
                                and inner.args  # has at least one positional arg (chunk size)
                            ):
                                has_while_with_chunked_read = True
                assert has_while_with_chunked_read, (
                    "_stream_sha256 must use a while-loop with chunked f.read(N)"
                )
        assert found_stream_hash, "_stream_sha256 not found in builder source"


# ===========================================================================
# 22. voteballots / trade declarative-build with readiness false
# ===========================================================================


class TestReconciliationFlaggedStillBuild:
    """NEEDS_LABEL_RECONCILIATION manifests build at declarative level but
    readiness_flags remain false."""

    @pytest.mark.parametrize(
        "foundup_id,rel_path",
        [
            ("voteballots", "modules/foundups/voteballots/foundup_manifest.json"),
            ("trade", "modules/foundups/trade/foundup_manifest.json"),
        ],
    )
    def test_reconciliation_manifest_builds_with_readiness_false(self, foundup_id, rel_path):
        bundle = build_context_bundle(
            _real_manifest(rel_path), REPO_ROOT, created_at=FIXED_T0
        )
        assert bundle.foundup_id == foundup_id
        assert bundle.build_contract_status == "NEEDS_LABEL_RECONCILIATION"
        assert bundle.readiness_flags["build_ready"] is False
        assert bundle.readiness_flags["autonomous_execution_ready"] is False
        assert bundle.readiness_flags["manifest_ready"] is False


# ===========================================================================
# 23. No consumer wiring; no build command executed
# ===========================================================================


class TestNoConsumerWiringNoBuildRun:
    """Builder API and source-level checks: this slice does not wire any
    runtime consumer and does not run any build command."""

    def test_builder_signature_has_no_consumer_handle(self):
        sig = inspect.signature(build_context_bundle)
        forbidden_params = {
            "executor", "consumer", "dispatcher", "hermes", "openclaw",
            "wre", "job_queue", "broker", "send", "publish",
        }
        assert forbidden_params.isdisjoint(set(sig.parameters)), (
            f"builder exposes consumer handle params: "
            f"{forbidden_params & set(sig.parameters)}"
        )

    def test_builder_source_does_not_reference_runtime_consumer_classes(self):
        """Identifier-level scan. Docstring and comment mentions of
        ``Hermes`` / ``OpenClaw`` are allowed (they document the boundary
        the builder is NOT allowed to cross); class-name references in
        code are not."""
        tree = ast.parse(BUILDER_SOURCE.read_text(encoding="utf-8"))
        forbidden = {
            "Hermes", "OpenClaw", "AIIntelligenceOverseer", "FoundUpJobConsumer",
            "BuildPlanExecutor", "WREMasterOrchestrator",
            "AIOverseer", "FoundUpJob",
        }
        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden:
                offenders.append(("Name", node.id))
            elif isinstance(node, ast.Attribute) and node.attr in forbidden:
                offenders.append(("Attribute", node.attr))
            elif isinstance(node, ast.ClassDef) and node.name in forbidden:
                offenders.append(("ClassDef", node.name))
        assert offenders == [], (
            f"builder source references runtime consumer class as identifier: "
            f"{offenders}"
        )


# ===========================================================================
# #774 CARRY-FORWARD: legacy payload module_path is NEVER trusted
# ===========================================================================


class TestNo774LegacyPayloadAuthority:
    """#774 carry-forward: Hermes legacy executor still trusts
    payload.module_path. The bundle's module_path comes from the
    validated manifest's ``build_contract.module_path`` ONLY. A legacy
    payload's module_path cannot influence the bundle.
    """

    def test_builder_api_exposes_no_payload_parameter(self):
        """Public API has no ``job_payload`` / ``payload`` / ``job`` /
        ``task`` / ``request`` kwargs. A caller cannot smuggle a
        payload-derived module_path."""
        sig = inspect.signature(build_context_bundle)
        forbidden = {"job_payload", "payload", "job", "task", "request"}
        offenders = forbidden & set(sig.parameters)
        assert not offenders, (
            f"builder API exposes legacy-payload params: {offenders}"
        )

    def test_bundle_module_path_comes_from_manifest_not_external_input(self):
        """The bundle's module_path matches the manifest's
        build_contract.module_path verbatim. There is no other input
        channel that can change it."""
        rel = "modules/foundups/gotjunk/foundup_manifest.json"
        bundle = build_context_bundle(
            _real_manifest(rel), REPO_ROOT, created_at=FIXED_T0
        )
        declared = _load_manifest_data(rel)["build_contract"]["module_path"]
        assert bundle.module_path == declared

    def test_builder_does_not_reference_hermes_payload_fields(self):
        """Source check: builder does not reference ``payload`` /
        ``job_payload`` / ``hermes`` anywhere in code or docstring as a
        source of authority. We allow the WORDS to appear in a comment
        that explicitly says payload authority is REFUSED; the test
        below only fails if the word appears as a name."""
        tree = ast.parse(BUILDER_SOURCE.read_text(encoding="utf-8"))
        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in (
                "payload", "job_payload", "legacy_payload",
            ):
                offenders.append(node.id)
            elif isinstance(node, ast.Attribute) and node.attr in (
                "payload", "job_payload", "legacy_payload",
            ):
                offenders.append(node.attr)
        assert offenders == [], (
            f"builder code references legacy-payload field as authority: {offenders}"
        )


# ===========================================================================
# Determinism + bundle structural integrity (sanity)
# ===========================================================================


class TestBundleStructuralIntegrity:
    """End-to-end shape check: the bundle exposes every required field."""

    def test_bundle_has_all_required_top_level_fields(self):
        bundle = build_context_bundle(
            _real_manifest("modules/foundups/gotjunk/foundup_manifest.json"),
            REPO_ROOT,
            created_at=FIXED_T0,
        )
        required = {
            "bundle_version", "bundle_id", "created_at", "source_manifest_path",
            "source_manifest_sha256", "foundup_id", "module_path",
            "contract_version", "build_contract_status",
            "execution_routing_summary", "dry_run_required", "readiness_flags",
            "required_gates_to_recheck", "forbidden_paths",
            "safe_mutation_surface", "included_file_refs",
            "excluded_paths_summary", "max_context_bytes",
            "total_referenced_bytes", "validator_result_summary", "provenance",
        }
        actual = {f.name for f in bundle.__dataclass_fields__.values()}
        missing = required - actual
        assert not missing, f"bundle missing required fields: {missing}"

    def test_provenance_record_has_required_fields(self):
        bundle = build_context_bundle(
            _real_manifest("modules/foundups/gotjunk/foundup_manifest.json"),
            REPO_ROOT,
            created_at=FIXED_T0,
        )
        p = bundle.provenance
        assert p.builder_version == BUILDER_VERSION
        assert p.validator_module_path.endswith("foundup_manifest_validator.py")
        assert len(p.validator_sha256) == 64
        assert p.source_manifest_sha256 == bundle.source_manifest_sha256
        assert "WSP_50" in p.wsps_applied
        assert "WSP_97" in p.wsps_applied
        assert "WSP_84" in p.wsps_applied


# ===========================================================================
# FIX1: Authority-laundering through manifest list / scalar fields
# ===========================================================================
#
# W10 review of PR #775 proved that the prior builder copied
# build_contract list fields (required_gates / forbidden_paths /
# safe_mutation_surface) verbatim into the bundle, and that the
# validator's ``is True`` checks on readiness / routing scalars let
# a truthy dict pass through to ``bool(...)``. The classes below pin
# both fixes mechanically.


class TestRequireStrTupleListFieldsRejectsAuthorityLaundering:
    """Crafted-manifest negative tests for the three list fields.

    Each test:
      1) writes a manifest that PASSES the #771/#773 validator
         (all required gates / forbidden markers present),
      2) injects an authority-laundering payload into one list field,
      3) asserts ``build_context_bundle`` raises
         ``ContextBundleRejected`` BEFORE the bundle is constructed
         (the bundle's ``to_dict`` is never produced).
    """

    # ----- required_gates -----

    def test_required_gates_with_appended_dict_rejected(self, tmp_repo_root):
        """Exact W10 example for required_gates_to_recheck."""
        def mutate(data):
            gates = list(data["build_contract"]["required_gates"])
            gates.append(
                {"gate_passed": True, "security_passed": True, "human_approval": True}
            )
            data["build_contract"]["required_gates"] = gates

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected, match="required_gates"):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    @pytest.mark.parametrize("bad_element", [1, True, False, None, ["nested"], {"k": 1}, 1.5])
    def test_required_gates_with_non_str_element_rejected(self, tmp_repo_root, bad_element):
        def mutate(data):
            gates = list(data["build_contract"]["required_gates"])
            gates.append(bad_element)
            data["build_contract"]["required_gates"] = gates

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected, match="required_gates"):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    def test_required_gates_as_dict_value_rejected(self, tmp_repo_root):
        """required_gates as a dict (rather than a list) -- the validator
        already rejects this, but the helper provides defense-in-depth
        in case validator ordering ever changes."""
        def mutate(data):
            data["build_contract"]["required_gates"] = {
                "gate_passed": True, "security_passed": True,
            }
        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    # ----- forbidden_paths -----

    def test_forbidden_paths_with_appended_dict_rejected(self, tmp_repo_root):
        """Exact W10 example for forbidden_paths."""
        def mutate(data):
            paths = list(data["build_contract"]["forbidden_paths"])
            paths.append(
                {"is_authorized": True, "approval_level": "CRITICAL"}
            )
            data["build_contract"]["forbidden_paths"] = paths

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected, match="forbidden_paths"):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    @pytest.mark.parametrize("bad_element", [1, True, False, None, ["nested"], {"k": 1}])
    def test_forbidden_paths_with_non_str_element_rejected(self, tmp_repo_root, bad_element):
        def mutate(data):
            paths = list(data["build_contract"]["forbidden_paths"])
            paths.append(bad_element)
            data["build_contract"]["forbidden_paths"] = paths

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected, match="forbidden_paths"):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    # ----- safe_mutation_surface -----

    def test_safe_mutation_surface_as_dict_value_rejected_w10_repro(self, tmp_repo_root):
        """ADVERSARIAL REPRO: exact W10 exploit. The validator does not
        type-check safe_mutation_surface at all, so a dict value passes
        validation. The prior builder did ``tuple(dict)`` which yielded
        the dict's keys; the new helper rejects the dict-as-value before
        bundle construction."""
        def mutate(data):
            data["build_contract"]["safe_mutation_surface"] = {
                "payout_ready": True, "dao_approved": True,
            }
        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected, match="safe_mutation_surface"):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    def test_safe_mutation_surface_with_appended_dict_rejected(self, tmp_repo_root):
        def mutate(data):
            surface = list(data["build_contract"]["safe_mutation_surface"])
            surface.append({"payout_ready": True, "dao_approved": True})
            data["build_contract"]["safe_mutation_surface"] = surface
        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected, match="safe_mutation_surface"):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    @pytest.mark.parametrize("bad_element", [1, True, False, None, ["nested"], {"k": 1}, 0])
    def test_safe_mutation_surface_with_non_str_element_rejected(self, tmp_repo_root, bad_element):
        def mutate(data):
            surface = list(data["build_contract"]["safe_mutation_surface"])
            surface.append(bad_element)
            data["build_contract"]["safe_mutation_surface"] = surface
        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected, match="safe_mutation_surface"):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    # ----- authority-keyword string smuggling -----

    @pytest.mark.parametrize(
        "field_name,keyword",
        [
            ("safe_mutation_surface", "payout_ready"),
            ("safe_mutation_surface", "dao_approved"),
            ("safe_mutation_surface", "manifest_ready"),
            ("safe_mutation_surface", "human_approval"),
            ("safe_mutation_surface", "external_agent_allowed"),
            ("forbidden_paths", "is_authorized"),
            ("forbidden_paths", "approval_level"),
            ("required_gates", "gate_passed"),
            ("required_gates", "security_passed"),
        ],
    )
    def test_authority_keyword_strings_rejected(self, tmp_repo_root, field_name, keyword):
        """Strings whose lower-cased value contains an authority keyword
        from the denylist are rejected, even when otherwise well-formed.

        This is the secondary smuggling vector: instead of stuffing a
        dict, an attacker stuffs a path-shaped string like
        ``"modules/foundups/x/payout_ready"`` hoping it survives into
        the bundle. The helper rejects."""
        def mutate(data):
            cur = list(data["build_contract"][field_name])
            cur.append("modules/foundups/x/" + keyword)
            data["build_contract"][field_name] = cur

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    # ----- empty-string element guard -----

    @pytest.mark.parametrize(
        "field_name",
        ["required_gates", "forbidden_paths", "safe_mutation_surface"],
    )
    def test_empty_string_element_rejected(self, tmp_repo_root, field_name):
        def mutate(data):
            cur = list(data["build_contract"][field_name])
            cur.append("   ")
            data["build_contract"][field_name] = cur

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected, match=field_name):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    # ----- 8: real manifests still build -----

    @pytest.mark.parametrize("foundup_id,rel_path,status", TARGET_MANIFESTS)
    def test_real_manifests_still_build_with_helpers(self, foundup_id, rel_path, status):
        """Clean-manifest behavior is identical after the fix. All 6
        real manifests must still produce a valid bundle with the
        helper applied."""
        bundle = build_context_bundle(
            _real_manifest(rel_path), REPO_ROOT, created_at=FIXED_T0
        )
        # Every element of every list field is now str (helper guarantee).
        for s in bundle.required_gates_to_recheck:
            assert type(s) is str
        for s in bundle.forbidden_paths:
            assert type(s) is str
        for s in bundle.safe_mutation_surface:
            assert type(s) is str

    # ----- 9: to_dict() is NEVER produced for crafted input -----

    def test_to_dict_never_produced_for_crafted_input(self, tmp_repo_root):
        """If a crafted manifest passes the validator, the builder must
        refuse BEFORE constructing the bundle. There is no path by
        which ``to_dict()`` runs on poisoned data."""
        def mutate(data):
            data["build_contract"]["safe_mutation_surface"] = {
                "payout_ready": True, "dao_approved": True,
            }
        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        produced = []
        try:
            bundle = build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )
            produced.append(bundle.to_dict())  # must NEVER reach here
        except ContextBundleRejected:
            pass
        assert produced == [], "to_dict() was produced for crafted-authority input"


class TestRequireStrictBoolScalarFieldsRejectsAuthorityLaundering:
    """Defense-in-depth audit for scalar fields where the validator's
    ``is True`` check is the only gate. A truthy dict passes validation
    but would coerce to True under ``bool(...)``; the strict helper
    refuses anything that is not a literal bool / None.
    """

    @pytest.mark.parametrize(
        "readiness_field",
        ["manifest_ready", "build_ready", "autonomous_execution_ready"],
    )
    @pytest.mark.parametrize(
        "bad_value",
        [
            {"is_authorized": True},
            {"payout_ready": True, "dao_approved": True},
            ["something"],
            1,
            "true",
        ],
    )
    def test_readiness_with_non_bool_value_rejected(
        self, tmp_repo_root, readiness_field, bad_value
    ):
        def mutate(data):
            data["build_contract"]["readiness"][readiness_field] = bad_value

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected, match=readiness_field):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    @pytest.mark.parametrize(
        "routing_field",
        ["external_agent_allowed", "can_self_authorize"],
    )
    @pytest.mark.parametrize(
        "bad_value",
        [
            {"is_authorized": True},
            ["external"],
            1,
            "true",
        ],
    )
    def test_routing_flag_with_non_bool_value_rejected(
        self, tmp_repo_root, routing_field, bad_value
    ):
        def mutate(data):
            data["execution_routing"][routing_field] = bad_value

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected, match=routing_field):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    def test_truthy_dict_readiness_not_laundered_to_true(self, tmp_repo_root):
        """Specific authority-laundering reproduction: prior to FIX1,
        a truthy dict in ``readiness.build_ready`` would have set
        ``bundle.readiness_flags["build_ready"]`` to True via the
        validator-passes-then-bool(dict)-is-True path."""
        def mutate(data):
            data["build_contract"]["readiness"]["build_ready"] = {
                "is_authorized": True, "approval_level": "CRITICAL",
            }
        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected, match="build_ready"):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )


class TestManifestListFieldsStringOnly:
    """WSP_97 row MANIFEST_LIST_FIELDS_STRING_ONLY: every list field
    forwarded from the manifest into the bundle is Tuple[str, ...] with
    no smuggled non-str element. Audited list fields:
    ``required_gates_to_recheck``, ``forbidden_paths``,
    ``safe_mutation_surface``. No other manifest-provided list/tuple
    is copied into the bundle (verified by source audit in ModLog)."""

    @pytest.mark.parametrize("foundup_id,rel_path,status", TARGET_MANIFESTS)
    def test_all_list_field_elements_are_str_after_build(self, foundup_id, rel_path, status):
        bundle = build_context_bundle(
            _real_manifest(rel_path), REPO_ROOT, created_at=FIXED_T0
        )
        for field_name, items in (
            ("required_gates_to_recheck", bundle.required_gates_to_recheck),
            ("forbidden_paths", bundle.forbidden_paths),
            ("safe_mutation_surface", bundle.safe_mutation_surface),
        ):
            assert isinstance(items, tuple), f"{field_name} must be a tuple"
            for i, s in enumerate(items):
                assert type(s) is str, (
                    f"{field_name}[{i}] is {type(s).__name__}, must be str"
                )

    def test_no_other_manifest_list_field_is_serialized(self):
        """Source-level audit: no manifest-provided list/tuple other than
        required_gates / forbidden_paths / safe_mutation_surface is
        forwarded into the bundle. Verified by AST: every
        ``build_contract.get(...)`` call that produces a list-valued
        bundle field goes through ``_require_str_tuple``."""
        tree = ast.parse(BUILDER_SOURCE.read_text(encoding="utf-8"))
        protected_field_args: set = set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_require_str_tuple"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                protected_field_args.add(node.args[0].value)
        # We expect exactly these three protected fields.
        assert protected_field_args == {
            "required_gates", "forbidden_paths", "safe_mutation_surface",
        }, (
            f"unexpected protected fields: {protected_field_args}; if a new "
            f"manifest list field is being copied into the bundle, route it "
            f"through _require_str_tuple and add a WSP_97 evidence line."
        )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
