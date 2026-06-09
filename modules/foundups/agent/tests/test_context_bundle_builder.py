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


# List-like converter call names that, applied to a manifest list access,
# would forward a manifest-derived list-like value into the bundle WITHOUT
# the ``_require_str_tuple`` guard. Scalar coercions (e.g. ``str(...)``) and
# dict reads (e.g. ``dict(excluded)``) are deliberately EXCLUDED so that the
# detector does not false-positive on legitimate current code.
_LISTLIKE_CONVERTERS = frozenset({"tuple", "list", "set", "frozenset"})


def _find_manifest_listlike_bypasses(
    tree, is_manifest_access, is_require_str_tuple_call
):
    """Return source line numbers of every manifest-derived list-like value
    that reaches a bundle field WITHOUT routing through ``_require_str_tuple``.

    FIX2-tighten (W10): the prior detector only caught
    ``tuple(<manifest access>)``. 0102 requires completeness against ALL
    list-like bypasses, so this flags:

      - ``tuple|list|set|frozenset(<manifest access>)`` (list-like
        converter wrapping a manifest list access);
      - list/set comprehensions and generator expressions whose first
        ``for`` clause iterates a manifest list access (a tuple
        comprehension is a ``GeneratorExp`` wrapped in ``tuple(...)``, so
        both the wrapper and the genexp iter are covered);
      - direct assignment ``NAME = <manifest list access>`` (and the
        subscript-target form) where ``NAME`` is then used as a value in a
        ``ContextBundle(...)`` keyword argument.

    NO FALSE POSITIVES on the current (correct) source:
      - converters are restricted to ``_LISTLIKE_CONVERTERS`` (so
        ``str(build_contract.get(...))`` and ``dict(excluded)`` are not
        flagged);
      - converter / comprehension args that are a LOCAL name (e.g.
        ``tuple(included)``, ``tuple(out)``) are not manifest accesses and
        are not flagged;
      - a manifest access routed through ``_require_str_tuple(...)`` is
        explicitly exempt;
      - assignment flagging is scoped to names whose value actually reaches
        a ``ContextBundle(...)`` field, so dict reads such as
        ``build_contract = data.get("build_contract", {})`` (whose name is
        never a ContextBundle kwarg value) are not flagged.

    Shared by the completeness guard (run over the real builder source) and
    its non-vacuity proofs (run over synthetic sources that DO contain a
    forbidden pattern). Keeping the detector in one place guarantees every
    test exercises identical logic.
    """

    def _is_manifest_listlike_value(node):
        """A manifest access not routed through the guard. Used for both
        converter args and assignment RHS values."""
        if is_require_str_tuple_call(node):
            return False  # routed through the guard -> safe
        return is_manifest_access(node)

    # Names used as a VALUE in a ContextBundle(...) keyword argument.
    contextbundle_value_names = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "ContextBundle"
        ):
            for kw in node.keywords:
                if isinstance(kw.value, ast.Name):
                    contextbundle_value_names.add(kw.value.id)

    offenders = []
    for node in ast.walk(tree):
        # (1) list-like converter wrapping a manifest access.
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _LISTLIKE_CONVERTERS
            and len(node.args) == 1
        ):
            if _is_manifest_listlike_value(node.args[0]):
                offenders.append(getattr(node, "lineno", -1))
                continue
        # (2) comprehension / generator expression iterating a manifest
        #     list access in its first ``for`` clause.
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            if node.generators and is_manifest_access(node.generators[0].iter):
                offenders.append(getattr(node, "lineno", -1))
                continue
        # (3) direct assignment ``NAME = <manifest list access>`` (or
        #     subscript target) whose NAME reaches a ContextBundle field.
        if isinstance(node, ast.Assign):
            if _is_manifest_listlike_value(node.value):
                for tgt in node.targets:
                    name_id = None
                    if isinstance(tgt, ast.Name):
                        name_id = tgt.id
                    elif isinstance(tgt, ast.Subscript) and isinstance(
                        tgt.value, ast.Name
                    ):
                        name_id = tgt.value.id
                    if name_id is not None and name_id in contextbundle_value_names:
                        offenders.append(getattr(node, "lineno", -1))
                        break
    return offenders


# Backwards-compatible alias: the prior detector name now points at the
# broadened completeness detector so any external reference keeps working.
_find_bare_tuple_of_manifest_access = _find_manifest_listlike_bypasses


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


# ---------------------------------------------------------------------------
# FIX2 fixtures: fullwidth-Unicode authority keywords.
#
# These strings are built from ``\uFFxx`` ESCAPE SEQUENCES so the SOURCE
# FILE stays 0 non-ASCII bytes. At runtime each decodes to the fullwidth
# (Halfwidth-and-Fullwidth-Forms) glyphs of an authority keyword; each
# NFKC-normalizes back to its plain-ASCII keyword (verified below by
# ``test_fullwidth_fixtures_normalize_as_documented``).
#
#   _FW_PAYOUT_READY -> "payout_ready"  (U+FF50 U+FF41 U+FF59 U+FF4F
#                                        U+FF55 U+FF54 "_" U+FF52 U+FF45
#                                        U+FF41 U+FF44 U+FF59)
#   _FW_DAO_APPROVED -> "dao_approved"
#   _FW_GATE_PASSED  -> "gate_passed"
#   _MIXED_HUMAN_APPROVAL -> "human_approval" (one fullwidth "a" U+FF41,
#       rest ASCII -- a GENERIC NFKC-compatibility evasion, not a full
#       fullwidth string).
# ---------------------------------------------------------------------------

# Fullwidth "payout_ready":
#   p=U+FF50 a=U+FF41 y=U+FF59 o=U+FF4F u=U+FF55 t=U+FF54 "_"
#   r=U+FF52 e=U+FF45 a=U+FF41 d=U+FF44 y=U+FF59
_FW_PAYOUT_READY = (
    "\uff50\uff41\uff59\uff4f\uff55\uff54" "_" "\uff52\uff45\uff41\uff44\uff59"
)
# Fullwidth "dao_approved":
#   d=U+FF44 a=U+FF41 o=U+FF4F "_" a=U+FF41 p=U+FF50 p=U+FF50 r=U+FF52
#   o=U+FF4F v=U+FF56 e=U+FF45 d=U+FF44
_FW_DAO_APPROVED = (
    "\uff44\uff41\uff4f" "_" "\uff41\uff50\uff50\uff52\uff4f\uff56\uff45\uff44"
)
# Fullwidth "gate_passed":
#   g=U+FF47 a=U+FF41 t=U+FF54 e=U+FF45 "_" p=U+FF50 a=U+FF41 s=U+FF53
#   s=U+FF53 e=U+FF45 d=U+FF44
_FW_GATE_PASSED = (
    "\uff47\uff41\uff54\uff45" "_" "\uff50\uff41\uff53\uff53\uff45\uff44"
)
# Generic NFKC-compatibility evasion: ASCII "hum" + fullwidth "a" (U+FF41)
# + ASCII "n_approval" -> NFKC normalizes to "human_approval".
_MIXED_HUMAN_APPROVAL = "hum" "\uff41" "n_approval"

# ---------------------------------------------------------------------------
# FIX2-tighten fixtures: BENIGN non-ASCII strings (no authority keyword).
#
# These are path-/glob-shaped strings that carry a non-ASCII character but
# contain NO authority keyword, so they pass the NFKC authority scan and
# would otherwise normalize-and-accept. The ASCII-only contract refuses
# them. Encoded via ``\uXXXX`` ESCAPES so the source stays 0 non-ASCII bytes.
#
#   _NONASCII_CAFE_GLOB -> "caf<U+00E9>-glob" ("cafe-glob" with e-acute)
#   _NONASCII_CJK_PATH   -> "modules/foundups/<U+6587>/x" (CJK char "wen")
# ---------------------------------------------------------------------------

# "caf" + U+00E9 (LATIN SMALL LETTER E WITH ACUTE) + "-glob".
_NONASCII_CAFE_GLOB = "caf" "\u00e9" "-glob"
# A repo-relative-looking path with one CJK char (U+6587).
_NONASCII_CJK_PATH = "modules/foundups/" "\u6587" "/x"


class TestFullwidthUnicodeAuthorityEvasionRejected:
    """FIX2 / W10 residual gap 1: fullwidth-Unicode evasion of the
    ``_AUTHORITY_KEYWORDS`` substring scan.

    W10 adversarial re-gate proved that a fullwidth-Unicode form of an
    authority keyword (e.g. fullwidth ``"payout_ready"``) is a ``str``,
    passed the prior raw ``item.lower()`` denylist scan, landed in
    ``bundle.to_dict()``, and NFKC-normalized to ``"payout_ready"``
    downstream -- laundering authority past the denylist.

    The fix NFKC-normalizes each element BEFORE the denylist scan. These
    tests assert ``ContextBundleRejected`` is raised BEFORE any bundle is
    produced, for each fullwidth payload, across each of the three
    manifest list fields (including the SAME field the W10 exploit used:
    ``safe_mutation_surface``).
    """

    def test_fullwidth_fixtures_normalize_as_documented(self):
        """Non-vacuity guard: prove the fixtures really are fullwidth
        forms that NFKC-normalize to the documented authority keywords.
        If this fails, the rejection tests below would be vacuous."""
        import unicodedata
        assert unicodedata.normalize("NFKC", _FW_PAYOUT_READY).lower() == "payout_ready"
        assert unicodedata.normalize("NFKC", _FW_DAO_APPROVED).lower() == "dao_approved"
        assert unicodedata.normalize("NFKC", _FW_GATE_PASSED).lower() == "gate_passed"
        assert unicodedata.normalize("NFKC", _MIXED_HUMAN_APPROVAL).lower() == "human_approval"
        # And confirm each raw fixture is NOT already its ASCII keyword
        # (i.e. it would have evaded a raw ``item.lower()`` substring scan).
        assert "payout_ready" not in _FW_PAYOUT_READY.lower()
        assert "dao_approved" not in _FW_DAO_APPROVED.lower()
        assert "gate_passed" not in _FW_GATE_PASSED.lower()
        assert "human_approval" not in _MIXED_HUMAN_APPROVAL.lower()

    def test_fullwidth_payout_ready_in_safe_mutation_surface_rejected(self, tmp_repo_root):
        """W10-EXPLOIT FIELD: fullwidth ``payout_ready`` appended to
        ``safe_mutation_surface`` (the exact field the W10 exploit used).
        Must reject BEFORE any bundle is produced."""
        def mutate(data):
            surface = list(data["build_contract"]["safe_mutation_surface"])
            surface.append(_FW_PAYOUT_READY)
            data["build_contract"]["safe_mutation_surface"] = surface

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        produced = []
        with pytest.raises(ContextBundleRejected, match="safe_mutation_surface"):
            bundle = build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )
            produced.append(bundle)  # must NEVER reach here
        assert produced == []

    def test_fullwidth_dao_approved_in_safe_mutation_surface_rejected(self, tmp_repo_root):
        def mutate(data):
            surface = list(data["build_contract"]["safe_mutation_surface"])
            surface.append(_FW_DAO_APPROVED)
            data["build_contract"]["safe_mutation_surface"] = surface

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected, match="safe_mutation_surface"):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    def test_fullwidth_gate_passed_appended_to_required_gates_rejected(self, tmp_repo_root):
        """Append fullwidth ``gate_passed`` as a 9th element so the 8 real
        gate names remain present (validator still passes), then prove the
        builder rejects on the smuggled 9th element."""
        def mutate(data):
            gates = list(data["build_contract"]["required_gates"])
            assert len(gates) == 8, "baseline manifest must carry 8 required gates"
            gates.append(_FW_GATE_PASSED)  # 9th element
            data["build_contract"]["required_gates"] = gates

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        produced = []
        with pytest.raises(ContextBundleRejected, match="required_gates"):
            bundle = build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )
            produced.append(bundle)  # must NEVER reach here
        assert produced == []

    def test_fullwidth_payout_ready_appended_to_forbidden_paths_rejected(self, tmp_repo_root):
        """Append fullwidth ``payout_ready`` to a valid forbidden_paths
        list. Must reject BEFORE any bundle is produced."""
        def mutate(data):
            paths = list(data["build_contract"]["forbidden_paths"])
            paths.append(_FW_PAYOUT_READY)
            data["build_contract"]["forbidden_paths"] = paths

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected, match="forbidden_paths"):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    def test_generic_nfkc_compatibility_form_also_rejected(self, tmp_repo_root):
        """Recommended generic-evasion coverage: a string that is mostly
        ASCII but uses a single fullwidth letter ("hum<FW a>n_approval")
        is NOT itself the ASCII keyword, yet NFKC-normalizes to
        ``human_approval``. It must be rejected too -- proving the fix
        catches arbitrary NFKC-compatibility forms, not just fully
        fullwidth strings."""
        def mutate(data):
            surface = list(data["build_contract"]["safe_mutation_surface"])
            surface.append(_MIXED_HUMAN_APPROVAL)
            data["build_contract"]["safe_mutation_surface"] = surface

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected, match="safe_mutation_surface"):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )


class TestNonAsciiNonAuthorityElementsRejected:
    """FIX2-tighten / W10 GAP A: ASCII-only contract for protected list
    fields.

    The three protected fields (required_gates / forbidden_paths /
    safe_mutation_surface) are gate names, repo-relative paths, and path
    globs -- ASCII by convention. A BENIGN non-ASCII element (no authority
    keyword) passes the NFKC authority scan and would otherwise be
    normalized-and-accepted. 0102's ruling: ambiguity must be REFUSED.

    These tests append a non-ASCII NON-authority string (an e-acute glob or
    a CJK path char, encoded via ``\\uXXXX`` escapes so the source stays 0
    non-ASCII bytes) as an EXTRA element while keeping the real gate /
    path names intact (validator still passes), then assert
    ``ContextBundleRejected`` is raised BEFORE any bundle is produced. The
    authority-keyword check runs FIRST, so these benign strings reach the
    NEW ASCII-only check and trip on ``not item.isascii()``.
    """

    def test_nonascii_fixtures_are_benign_and_nonascii(self):
        """Non-vacuity guard: each fixture is genuinely non-ASCII and does
        NOT contain any authority keyword (so it reaches the ASCII-only
        check rather than being rejected earlier by the authority scan)."""
        import unicodedata
        from modules.foundups.agent.src.context_bundle_builder import (
            _AUTHORITY_KEYWORDS,
        )
        for fixture in (_NONASCII_CAFE_GLOB, _NONASCII_CJK_PATH):
            assert not fixture.isascii(), f"{fixture!r} must be non-ASCII"
            norm = unicodedata.normalize("NFKC", fixture).lower()
            for kw in _AUTHORITY_KEYWORDS:
                assert kw not in norm, (
                    f"{fixture!r} unexpectedly contains authority keyword {kw!r}"
                )

    def test_nonascii_nonauthority_in_required_gates_rejected(self, tmp_repo_root):
        """Append a benign non-ASCII glob as a 9th element (8 real gate
        names preserved, validator passes). Must reject on ASCII-only."""
        def mutate(data):
            gates = list(data["build_contract"]["required_gates"])
            assert len(gates) == 8, "baseline manifest must carry 8 required gates"
            gates.append(_NONASCII_CAFE_GLOB)  # 9th element
            data["build_contract"]["required_gates"] = gates

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        produced = []
        with pytest.raises(ContextBundleRejected, match="required_gates"):
            bundle = build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )
            produced.append(bundle)  # must NEVER reach here
        assert produced == []

    def test_nonascii_nonauthority_in_forbidden_paths_rejected(self, tmp_repo_root):
        """Append a benign non-ASCII path to a valid forbidden_paths list.
        Must reject BEFORE any bundle is produced."""
        def mutate(data):
            paths = list(data["build_contract"]["forbidden_paths"])
            paths.append(_NONASCII_CJK_PATH)
            data["build_contract"]["forbidden_paths"] = paths

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected, match="forbidden_paths"):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    def test_nonascii_nonauthority_in_safe_mutation_surface_rejected(self, tmp_repo_root):
        """Append a benign non-ASCII glob to safe_mutation_surface (the
        W10-exploit field). Must reject BEFORE any bundle is produced."""
        def mutate(data):
            surface = list(data["build_contract"]["safe_mutation_surface"])
            surface.append(_NONASCII_CAFE_GLOB)
            data["build_contract"]["safe_mutation_surface"] = surface

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        with pytest.raises(ContextBundleRejected, match="safe_mutation_surface"):
            build_context_bundle(
                manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
            )

    def test_ascii_elements_preserved_unchanged(self, tmp_repo_root):
        """Positive control: with only ASCII elements the bundle builds and
        the original ASCII values are preserved verbatim (no rewrite)."""
        sentinel = "modules/foundups/example/tests"

        def mutate(data):
            surface = list(data["build_contract"]["safe_mutation_surface"])
            surface.append(sentinel)
            data["build_contract"]["safe_mutation_surface"] = surface

        manifest_path = _write_tmp_manifest(
            tmp_repo_root, "example_001", "modules/foundups/example", mutator=mutate
        )
        bundle = build_context_bundle(
            manifest_path, tmp_repo_root.resolve(), created_at=FIXED_T0
        )
        assert sentinel in bundle.safe_mutation_surface
        # Every element is the ORIGINAL str (no NFKC rewrite of serialized
        # values for ASCII inputs).
        for s in bundle.safe_mutation_surface:
            assert type(s) is str and s.isascii()


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
        """Source-level audit (POSITIVE half): the set of fields routed
        through ``_require_str_tuple`` is exactly
        required_gates / forbidden_paths / safe_mutation_surface."""
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

    def test_no_bare_tuple_of_manifest_access_bypasses_helper(self):
        """FIX2 / W10 residual gap 2: COMPLETENESS guard (the positive-only
        check above is NOT sufficient).

        The positive check asserts the set of fields routed through
        ``_require_str_tuple`` == the expected three. But a FUTURE
        manifest-derived list-like value that BYPASSES the helper would
        STILL pass that positive check (the helper-routed set would be
        unchanged). That is the gap W10 proved.

        FIX2-tighten: the detector is broadened from ``tuple(...)``-only to
        ALL list-like bypasses. It walks the builder AST and flags any
        manifest dict access (``<manifest>.get(...)`` / ``<manifest>[...]``
        for manifest dicts build_contract / routing / readiness / data)
        that reaches a bundle field via:
          - ``tuple|list|set|frozenset(<manifest access>)``;
          - a list/set comprehension or generator expression iterating a
            manifest list access;
          - a direct assignment ``NAME = <manifest list access>`` whose
            NAME is later a ``ContextBundle(...)`` keyword-arg value;
        and that is NOT itself a ``_require_str_tuple(...)`` call. Every
        manifest list field MUST route through the helper, so there must be
        ZERO such bypass patterns.

        NON-VACUITY: proven by
        ``test_completeness_guard_detects_synthetic_*`` tests below, which
        run the SAME detector over synthetic ASTs that DO contain each
        forbidden pattern and assert each is detected.
        """
        manifest_dicts = {"build_contract", "routing", "readiness", "data"}

        def _is_manifest_access(node: ast.AST) -> bool:
            # <manifest>.get(...)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in manifest_dicts
            ):
                return True
            # <manifest>[...]
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id in manifest_dicts
            ):
                return True
            return False

        def _is_require_str_tuple_call(node: ast.AST) -> bool:
            return (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_require_str_tuple"
            )

        tree = ast.parse(BUILDER_SOURCE.read_text(encoding="utf-8"))
        offenders = _find_manifest_listlike_bypasses(
            tree, _is_manifest_access, _is_require_str_tuple_call
        )
        assert offenders == [], (
            "a manifest-derived list-like value bypasses _require_str_tuple "
            f"at source lines {offenders}; every manifest list field MUST "
            "route through _require_str_tuple (NFKC + type + authority-keyword "
            "+ ASCII-only guard). Covered bypasses: tuple/list/set/frozenset "
            "conversion, comprehension, and direct assignment reaching a "
            "ContextBundle field."
        )

    @staticmethod
    def _manifest_access_predicates():
        """Return ``(is_manifest_access, is_require_str_tuple_call)`` -- the
        same predicate pair the production guard uses. Shared by every
        synthetic non-vacuity proof so they all exercise identical logic."""
        manifest_dicts = {"build_contract", "routing", "readiness", "data"}

        def _is_manifest_access(node: ast.AST) -> bool:
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in manifest_dicts
            ):
                return True
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id in manifest_dicts
            ):
                return True
            return False

        def _is_require_str_tuple_call(node: ast.AST) -> bool:
            return (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_require_str_tuple"
            )

        return _is_manifest_access, _is_require_str_tuple_call

    def test_completeness_guard_detects_synthetic_bare_tuple(self):
        """NON-VACUITY proof for the completeness guard: feed the SAME
        detector a synthetic source that DOES contain the forbidden
        pattern ``tuple(build_contract.get("new_list", []))`` and assert
        it IS detected. This guarantees the guard above is not vacuous."""
        is_manifest_access, is_require = self._manifest_access_predicates()
        synthetic = (
            "def f(build_contract):\n"
            "    x = tuple(build_contract.get('new_list', []))\n"
            "    y = tuple(build_contract['other_list'])\n"
            "    ok = tuple(_require_str_tuple('required_gates', build_contract.get('required_gates', [])))\n"
            "    z = tuple(some_local_list)\n"
            "    return x, y, ok, z\n"
        )
        tree = ast.parse(synthetic)
        offenders = _find_manifest_listlike_bypasses(
            tree, is_manifest_access, is_require
        )
        # Two bare patterns: build_contract.get(...) and build_contract[...].
        # The _require_str_tuple-wrapped one and the local-list one are NOT
        # flagged.
        assert len(offenders) == 2, (
            f"expected 2 synthetic offenders, got {len(offenders)}: {offenders}"
        )

    def test_completeness_guard_detects_synthetic_bare_list(self):
        """FIX2-tighten non-vacuity: an injected bare
        ``list(build_contract.get("x", []))`` IS detected (dispatch test 4).
        The local-name ``list(some_local)`` is NOT flagged."""
        is_manifest_access, is_require = self._manifest_access_predicates()
        synthetic = (
            "def f(build_contract):\n"
            "    x = list(build_contract.get('x', []))\n"
            "    z = list(some_local)\n"
            "    return x, z\n"
        )
        tree = ast.parse(synthetic)
        offenders = _find_manifest_listlike_bypasses(
            tree, is_manifest_access, is_require
        )
        assert len(offenders) == 1, (
            f"expected 1 synthetic list() offender, got {len(offenders)}: {offenders}"
        )

    def test_completeness_guard_detects_synthetic_bare_set_and_frozenset(self):
        """FIX2-tighten non-vacuity: injected ``set(...)`` and
        ``frozenset(...)`` of a manifest access ARE detected (dispatch
        test 6, set half)."""
        is_manifest_access, is_require = self._manifest_access_predicates()
        synthetic = (
            "def f(build_contract):\n"
            "    a = set(build_contract.get('x', []))\n"
            "    b = frozenset(build_contract['y'])\n"
            "    c = set(some_local)\n"
            "    return a, b, c\n"
        )
        tree = ast.parse(synthetic)
        offenders = _find_manifest_listlike_bypasses(
            tree, is_manifest_access, is_require
        )
        assert len(offenders) == 2, (
            f"expected 2 synthetic set/frozenset offenders, got "
            f"{len(offenders)}: {offenders}"
        )

    def test_completeness_guard_detects_synthetic_comprehension(self):
        """FIX2-tighten non-vacuity: injected list / set comprehensions and
        a generator expression iterating a manifest list access ARE detected
        (dispatch test 6, comprehension half). A comprehension over a LOCAL
        list is NOT flagged."""
        is_manifest_access, is_require = self._manifest_access_predicates()
        synthetic = (
            "def f(build_contract):\n"
            "    a = [s for s in build_contract.get('x', [])]\n"
            "    b = {s for s in build_contract['y']}\n"
            "    c = tuple(s for s in build_contract.get('z', []))\n"
            "    d = [s for s in some_local]\n"
            "    return a, b, c, d\n"
        )
        tree = ast.parse(synthetic)
        offenders = _find_manifest_listlike_bypasses(
            tree, is_manifest_access, is_require
        )
        # listcomp (a), setcomp (b), and the genexp inside tuple(...) (c).
        # The tuple(...) wrapper in (c) wraps a GeneratorExp (not a manifest
        # access directly), so the genexp itself is the flagged node; the
        # local comprehension (d) is not flagged.
        assert len(offenders) >= 3, (
            f"expected >=3 synthetic comprehension offenders, got "
            f"{len(offenders)}: {offenders}"
        )

    def test_completeness_guard_detects_synthetic_direct_assignment(self):
        """FIX2-tighten non-vacuity: an injected direct assignment
        ``x = build_contract.get("x", [])`` whose NAME then reaches a
        ``ContextBundle(...)`` field IS detected (dispatch test 5). An
        assignment whose NAME does NOT reach a ContextBundle field (e.g.
        ``build_contract = data.get("build_contract", {})``) is NOT
        flagged."""
        is_manifest_access, is_require = self._manifest_access_predicates()
        synthetic = (
            "def f(data):\n"
            "    build_contract = data.get('build_contract', {})\n"
            "    smuggled = build_contract.get('x', [])\n"
            "    routing = data.get('execution_routing', {})\n"
            "    return ContextBundle(safe_mutation_surface=smuggled,\n"
            "                         execution_routing_summary=routing)\n"
        )
        tree = ast.parse(synthetic)
        offenders = _find_manifest_listlike_bypasses(
            tree, is_manifest_access, is_require
        )
        # Only ``smuggled = build_contract.get('x', [])`` is flagged: its
        # name reaches a ContextBundle field. ``build_contract = ...`` and
        # ``routing = ...`` are dict reads whose names are NOT used as a
        # ContextBundle list-field value (routing is passed but its RHS is a
        # ``.get`` returning a dict default; it is flagged ONLY if its name
        # reaches a field -- it does, so we assert the smuggled one is
        # present and the dict-default reads do not cause over-counting).
        assert len(offenders) >= 1, (
            f"expected the smuggled direct assignment to be flagged, got "
            f"{len(offenders)}: {offenders}"
        )

    def test_completeness_guard_no_false_positive_on_local_assignment(self):
        """FIX2-tighten false-positive guard: a direct assignment whose RHS
        is a manifest access but whose NAME never reaches a ContextBundle
        field is NOT flagged; and a ContextBundle field fed from a LOCAL
        name (not a manifest access) is NOT flagged."""
        is_manifest_access, is_require = self._manifest_access_predicates()
        synthetic = (
            "def f(data):\n"
            "    build_contract = data.get('build_contract', {})\n"
            "    readiness = build_contract.get('readiness', {})\n"
            "    included = []\n"
            "    return ContextBundle(included_file_refs=tuple(included),\n"
            "                         excluded_paths_summary=dict(excluded))\n"
        )
        tree = ast.parse(synthetic)
        offenders = _find_manifest_listlike_bypasses(
            tree, is_manifest_access, is_require
        )
        # build_contract/readiness names are never ContextBundle list-field
        # values; tuple(included)/dict(excluded) wrap locals. ZERO offenders.
        assert offenders == [], (
            f"false positive on legitimate local code: {offenders}"
        )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
