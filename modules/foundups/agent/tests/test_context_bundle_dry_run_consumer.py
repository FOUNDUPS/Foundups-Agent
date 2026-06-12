#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ContextBundle Dry-Run Consumer Tests -- WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1.

Covers the first consumer wiring of the read-only #775 ContextBundle into the
EXISTING dry-run evidence path. Standalone (ruling A), return-value-only
(ruling B). No skip / no xfail on any boundary assertion; negatives prove the
boundary.

Test groups:

  1. Happy path: a valid monorepo_poc FoundUp dry-run consumes its
     ContextBundle and emits a DryRunResult; resolved_module_path equals the
     validated canonical (from the bundle / shared resolver), NOT a payload
     value.
  2. Forged payload module_path / source_module -> rejected via the shared
     resolver; rejected_input observable; never reaches build/dispatch.
  3. Non-monorepo_poc source_authority (e.g. dao_managed) -> refused.
  4. required_gates appear as gates_to_recheck; NO gate-pass boolean asserted
     / serialized.
  5. Dry-run emits evidence but performs NO real execution: the real-exec
     sink / Hermes real delegation / subprocess build is mock-asserted NOT
     called.
  6. No file bodies in evidence (refs + sha256 only); no repo-wide read.
  7. HERMES_DELEGATE_ENABLED unset / 0 keeps real delegation BLOCKED.
  8. AST: the consumer imports NO new orchestrator, adds NO second
     module_path resolver, and performs NO subprocess / network / file-write
     (DryRunResult is return-value-only; no FAM event; no file write).
  9. The 6 real manifests' dry-run consumption works.

WSP 97 TRUTH BOUNDARIES:
  - These tests execute nothing in the consumer beyond pure construction.
  - No skip / no xfail on any security assertion.
"""

from __future__ import annotations

import ast
import dataclasses
import json
from pathlib import Path
from unittest import mock

import pytest

from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    create_job,
)
from modules.foundups.agent.src.context_bundle_builder import (
    ContextBundle,
    build_context_bundle,
)
from modules.foundups.agent.src.context_bundle_dry_run_consumer import (
    CONSUMER_VERSION,
    REQUIRED_SOURCE_AUTHORITY,
    DryRunConsumerRejected,
    DryRunResult,
    PlannedAction,
    consume_context_bundle_dry_run,
)
from modules.foundups.agent.src.source_authority import SourceAuthority

# Repo root: tests/ -> agent/ -> foundups/ -> modules/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[4]
CONSUMER_SOURCE = (
    Path(__file__).resolve().parents[1] / "src" / "context_bundle_dry_run_consumer.py"
)

FIXED_T0 = "2026-06-12T00:00:00Z"

# The 6 real manifests that pass the #773 validator (Phase-0 confirmed).
# (foundup_id, manifest_rel_path, expected canonical module_path)
TARGET_MANIFESTS = [
    ("gotjunk_001", "modules/foundups/gotjunk/foundup_manifest.json", "modules/foundups/gotjunk"),
    ("kosei", "modules/foundups/kosei/foundup_manifest.json", "modules/foundups/kosei"),
    ("magadoom_001", "modules/gamification/whack_a_magat/foundup_manifest.json", "modules/gamification/whack_a_magat"),
    ("antifafm_001", "modules/platform_integration/antifafm_broadcaster/foundup_manifest.json", "modules/platform_integration/antifafm_broadcaster"),
    ("voteballots", "modules/foundups/voteballots/foundup_manifest.json", "modules/foundups/voteballots"),
    ("trade", "modules/foundups/trade/foundup_manifest.json", "modules/foundups/trade"),
]


def _real_manifest(rel_path: str) -> Path:
    return REPO_ROOT / rel_path


def _build_real_bundle(rel_path: str) -> ContextBundle:
    return build_context_bundle(
        _real_manifest(rel_path), REPO_ROOT, created_at=FIXED_T0
    )


# A canonical authority-key denylist: NONE of these may appear as a key in the
# serialized DryRunResult (they would imply gate pass-state / promotion).
_FORBIDDEN_SERIALIZED_KEYS = frozenset({
    "gate_passed", "gates_passed", "passed", "all_gates_passed",
    "security_passed", "permission_passed", "dry_run_passed", "build_passed",
    "verification_complete", "cabr_ready", "cabr_passed", "payout_ready",
    "payout_approved", "dao_ready", "dao_approved", "dao_passed",
    "manifest_ready_promoted", "build_ready_promoted",
})


# ===========================================================================
# 1. Happy path
# ===========================================================================


class TestHappyPath:
    def test_valid_monorepo_poc_returns_dry_run_result(self):
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        result = consume_context_bundle_dry_run(bundle)
        assert isinstance(result, DryRunResult)
        assert result.dry_run is True
        assert result.real_execution_performed is False
        assert result.consumer_version == CONSUMER_VERSION
        assert result.bundle_id == bundle.bundle_id
        assert result.foundup_id == bundle.foundup_id

    def test_resolved_module_path_equals_validated_canonical(self):
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        result = consume_context_bundle_dry_run(bundle)
        # The resolved path is the BUNDLE's validated canonical value.
        assert result.resolved_module_path == bundle.module_path
        assert result.resolved_module_path == "modules/foundups/gotjunk"

    def test_resolved_module_path_is_never_a_payload_value(self):
        """Even when a job carries a (correct) payload module_path, the
        resolved value is the bundle's validated canonical -- never copied
        from the payload string. The payload candidate is surfaced as
        observable-ignore only."""
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        job = create_job(
            tenant_id="t",
            requested_action="build_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": "modules/foundups/gotjunk"},
        )
        result = consume_context_bundle_dry_run(
            bundle, job=job, repo_root=REPO_ROOT
        )
        assert result.resolved_module_path == bundle.module_path
        # Observable-ignore: payload candidate surfaced even though it matched.
        assert (
            result.rejected_input["payload_module_path_ignored"]
            == "modules/foundups/gotjunk"
        )
        assert result.rejected_input["resolver_run"] is True
        assert result.rejected_input["resolver_failed"] is False

    def test_source_authority_is_monorepo_poc(self):
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        result = consume_context_bundle_dry_run(bundle)
        assert result.source_authority == "monorepo_poc"
        assert result.source_authority == REQUIRED_SOURCE_AUTHORITY
        assert result.source_authority == SourceAuthority.MONOREPO_POC.value

    def test_readiness_flags_echoed_all_false(self):
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        result = consume_context_bundle_dry_run(bundle)
        assert result.readiness_flags == bundle.readiness_flags
        assert all(v is False for v in result.readiness_flags.values())

    def test_planned_actions_are_declared_never_executed(self):
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        result = consume_context_bundle_dry_run(bundle)
        assert len(result.planned_actions) >= 1
        for action in result.planned_actions:
            assert isinstance(action, PlannedAction)
            assert action.executed is False
            # argv is None (bundle carries refs + sha256 only, no commands).
            assert action.argv is None

    def test_no_job_means_no_payload_trusted(self):
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        result = consume_context_bundle_dry_run(bundle)
        assert result.rejected_input["resolver_run"] is False
        assert result.rejected_input["payload_module_path_ignored"] is None


# ===========================================================================
# 2. Forged payload -> rejected via the shared resolver
# ===========================================================================


class TestForgedPayloadRejected:
    def test_forged_module_path_pointing_at_other_foundup_rejected(self):
        """A job for gotjunk carrying a payload module_path pointing at a
        DIFFERENT FoundUp's real module is rejected by the shared resolver
        (cross-FoundUp substitution defense)."""
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        job = create_job(
            tenant_id="t",
            requested_action="build_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": "modules/foundups/kosei"},
        )
        with pytest.raises(DryRunConsumerRejected) as exc:
            consume_context_bundle_dry_run(bundle, job=job, repo_root=REPO_ROOT)
        assert "shared resolver" in str(exc.value)

    def test_forged_source_module_alias_rejected(self):
        """``payload.source_module`` is the alias the resolver also screens;
        a forged alias pointing elsewhere is rejected."""
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        job = create_job(
            tenant_id="t",
            requested_action="build_foundup",
            foundup_id="gotjunk_001",
            payload={"source_module": "modules/foundups/trade"},
        )
        with pytest.raises(DryRunConsumerRejected):
            consume_context_bundle_dry_run(bundle, job=job, repo_root=REPO_ROOT)

    def test_syntactic_forgery_absolute_path_rejected(self):
        """An absolute / traversal payload is rejected at the syntactic
        layer of the shared resolver before any manifest contact."""
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        job = create_job(
            tenant_id="t",
            requested_action="build_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": "/etc/passwd"},
        )
        with pytest.raises(DryRunConsumerRejected):
            consume_context_bundle_dry_run(bundle, job=job, repo_root=REPO_ROOT)

    def test_forged_payload_value_observable_in_rejection_message(self):
        """The rejected payload value is surfaced (observable-ignore) in the
        rejection message; it is never silently swallowed."""
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        job = create_job(
            tenant_id="t",
            requested_action="build_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": "modules/foundups/kosei"},
        )
        with pytest.raises(DryRunConsumerRejected) as exc:
            consume_context_bundle_dry_run(bundle, job=job, repo_root=REPO_ROOT)
        assert "modules/foundups/kosei" in str(exc.value)


# ===========================================================================
# 3. Non-monorepo_poc source_authority -> refused
# ===========================================================================


class TestSourceAuthorityRefusal:
    def test_dao_managed_bundle_refused(self):
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        tampered = dataclasses.replace(bundle, source_authority="dao_managed")
        with pytest.raises(DryRunConsumerRejected) as exc:
            consume_context_bundle_dry_run(tampered)
        assert "dao_managed" in str(exc.value)
        assert "monorepo_poc" in str(exc.value)

    def test_mvp_runtime_bundle_refused(self):
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        tampered = dataclasses.replace(bundle, source_authority="mvp_runtime")
        with pytest.raises(DryRunConsumerRejected):
            consume_context_bundle_dry_run(tampered)

    def test_external_proto_bundle_refused(self):
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        tampered = dataclasses.replace(
            bundle, source_authority="external_proto"
        )
        with pytest.raises(DryRunConsumerRejected):
            consume_context_bundle_dry_run(tampered)

    def test_consumer_cannot_promote_stage(self):
        """No code path produces a DryRunResult whose source_authority is
        anything other than monorepo_poc; promotion is impossible."""
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        result = consume_context_bundle_dry_run(bundle)
        assert result.source_authority == "monorepo_poc"


# ===========================================================================
# 4. Gates are NAMES to re-check; never pass-state
# ===========================================================================


class TestGatesAreNamesNotPassState:
    def test_gates_to_recheck_are_the_bundle_gate_names(self):
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        result = consume_context_bundle_dry_run(bundle)
        assert result.gates_to_recheck == tuple(bundle.required_gates_to_recheck)
        # They are plain string names.
        assert all(isinstance(g, str) for g in result.gates_to_recheck)
        assert len(result.gates_to_recheck) >= 1

    def test_no_gate_pass_boolean_asserted_on_result(self):
        """The DryRunResult has no attribute implying a gate passed."""
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        result = consume_context_bundle_dry_run(bundle)
        attrs = set(vars(result).keys())
        for forbidden in (
            "all_gates_passed", "gates_passed", "gate_passed",
            "verification_complete", "cabr_ready", "payout_ready",
        ):
            assert forbidden not in attrs

    def test_no_gate_pass_boolean_in_serialized_result(self):
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        result = consume_context_bundle_dry_run(bundle)
        serialized = json.dumps(result.to_dict())

        def _walk_keys(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    yield k
                    yield from _walk_keys(v)
            elif isinstance(obj, list):
                for item in obj:
                    yield from _walk_keys(item)

        keys = set(_walk_keys(result.to_dict()))
        offenders = keys & _FORBIDDEN_SERIALIZED_KEYS
        assert not offenders, f"gate-pass / authority keys serialized: {offenders}"
        # The literal forbidden tokens also do not appear as substrings of keys.
        lowered = serialized.lower()
        for tok in ("gate_passed", "all_gates_passed", "cabr", "payout"):
            assert tok not in lowered, f"forbidden token {tok!r} in serialized result"

    def test_gate_names_carried_verbatim_no_truth_value(self):
        """Each gate name is carried as a string; none is paired with a
        boolean truth value in the serialized output."""
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        result = consume_context_bundle_dry_run(bundle)
        d = result.to_dict()
        assert isinstance(d["gates_to_recheck"], list)
        assert all(isinstance(g, str) for g in d["gates_to_recheck"])


# ===========================================================================
# 5. Dry-run emits evidence but performs NO real execution
# ===========================================================================


class TestNoRealExecution:
    def test_real_exec_sink_extract_foundup_not_called(self):
        """The Hermes real-exec sink ``HermesFoundUpBuilder.extract_foundup``
        is never invoked by the consumer."""
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        with mock.patch(
            "modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder.extract_foundup"
        ) as m_extract:
            result = consume_context_bundle_dry_run(bundle)
        m_extract.assert_not_called()
        assert result.real_execution_performed is False

    def test_hermes_real_delegation_sink_not_called(self):
        """The wre_core Hermes delegation entry point is never invoked."""
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        with mock.patch(
            "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
        ) as m_delegate:
            result = consume_context_bundle_dry_run(bundle)
        m_delegate.assert_not_called()
        assert result.dry_run is True

    def test_subprocess_build_not_invoked(self):
        """No subprocess of any kind is spawned during consumption."""
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        with mock.patch("subprocess.Popen") as m_popen, \
                mock.patch("subprocess.run") as m_run, \
                mock.patch("subprocess.call") as m_call:
            consume_context_bundle_dry_run(bundle)
        m_popen.assert_not_called()
        m_run.assert_not_called()
        m_call.assert_not_called()

    def test_with_job_real_exec_sink_still_not_called(self):
        """Even on the job-supplied (resolver-run) path, no real-exec sink
        is invoked."""
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        job = create_job(
            tenant_id="t",
            requested_action="build_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": "modules/foundups/gotjunk"},
        )
        with mock.patch(
            "modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder.extract_foundup"
        ) as m_extract:
            consume_context_bundle_dry_run(bundle, job=job, repo_root=REPO_ROOT)
        m_extract.assert_not_called()


# ===========================================================================
# 6. No file bodies in evidence (refs + sha256 only)
# ===========================================================================


class TestEvidenceRefsNoBodies:
    def test_evidence_refs_have_only_ref_metadata(self):
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        result = consume_context_bundle_dry_run(bundle)
        assert len(result.evidence_refs) >= 1
        allowed_keys = {"path", "sha256", "size_bytes", "role"}
        for ref in result.evidence_refs:
            assert set(ref.keys()) == allowed_keys
            # sha256 is a 64-hex digest, not a file body.
            assert len(ref["sha256"]) == 64
            assert isinstance(ref["size_bytes"], int)

    def test_evidence_refs_mirror_bundle_file_refs(self):
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        result = consume_context_bundle_dry_run(bundle)
        assert len(result.evidence_refs) == len(bundle.included_file_refs)
        bundle_paths = {r.path for r in bundle.included_file_refs}
        result_paths = {r["path"] for r in result.evidence_refs}
        assert bundle_paths == result_paths

    def test_no_manifest_body_text_in_serialized_result(self):
        """The serialized result must not contain a recognizable manifest
        body fragment (proves refs-only, no concatenation)."""
        rel = "modules/foundups/gotjunk/foundup_manifest.json"
        bundle = _build_real_bundle(rel)
        result = consume_context_bundle_dry_run(bundle)
        serialized = json.dumps(result.to_dict())
        manifest_text = _real_manifest(rel).read_text(encoding="utf-8")
        # Pick a distinctive long line from the manifest body and assert it
        # is NOT embedded in the result.
        distinctive = [
            ln.strip() for ln in manifest_text.splitlines()
            if len(ln.strip()) > 40
        ]
        assert distinctive, "manifest had no long lines to test against"
        for line in distinctive[:10]:
            assert line not in serialized


# ===========================================================================
# 7. HERMES_DELEGATE_ENABLED unset/0 keeps real delegation BLOCKED
# ===========================================================================


class TestHermesDelegateFlagRespected:
    def test_flag_unset_consumer_does_not_enable_delegation(self, monkeypatch):
        monkeypatch.delenv("HERMES_DELEGATE_ENABLED", raising=False)
        from modules.infrastructure.wre_core.src.hermes_job_executor import (
            is_hermes_delegation_enabled,
        )
        assert is_hermes_delegation_enabled() is False
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        result = consume_context_bundle_dry_run(bundle)
        # The consumer never flips the flag; delegation stays disabled.
        assert is_hermes_delegation_enabled() is False
        assert result.real_execution_performed is False

    def test_flag_zero_consumer_does_not_enable_delegation(self, monkeypatch):
        monkeypatch.setenv("HERMES_DELEGATE_ENABLED", "0")
        from modules.infrastructure.wre_core.src.hermes_job_executor import (
            is_hermes_delegation_enabled,
        )
        assert is_hermes_delegation_enabled() is False
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        consume_context_bundle_dry_run(bundle)
        assert is_hermes_delegation_enabled() is False

    def test_consumer_source_never_sets_delegate_env(self):
        """The consumer source never ASSIGNS HERMES_DELEGATE_ENABLED.

        The flag name may appear in a docstring (documenting that the
        consumer keeps delegation BLOCKED), but the consumer must never set
        it via os.environ / putenv / setenv. AST-scan for any assignment or
        env-mutation call rather than a documentary substring match.
        """
        tree = ast.parse(CONSUMER_SOURCE.read_text(encoding="utf-8"))

        def _mentions_delegate_flag(node) -> bool:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    if "HERMES_DELEGATE_ENABLED" in sub.value:
                        return True
                if isinstance(sub, ast.Attribute) and sub.attr == "HERMES_DELEGATE_ENABLED":
                    return True
            return False

        # No subscript assignment to os.environ that mentions the flag.
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript) and _mentions_delegate_flag(target):
                        raise AssertionError(
                            "consumer assigns into an env mapping keyed by the "
                            "delegate flag"
                        )
            # No putenv / setenv call that touches the flag.
            if isinstance(node, ast.Call):
                f = node.func
                if isinstance(f, ast.Attribute) and f.attr in ("putenv", "setenv"):
                    if _mentions_delegate_flag(node):
                        raise AssertionError(
                            "consumer calls putenv/setenv on the delegate flag"
                        )
        # The consumer also never even reads os.environ at all (no execution
        # coupling); assert the module does not import os.
        imported = {
            alias.name
            for n in ast.walk(tree)
            if isinstance(n, ast.Import)
            for alias in n.names
        }
        assert "os" not in imported, (
            "consumer should not import os (no env coupling needed)"
        )


# ===========================================================================
# 8. AST guards: no orchestrator, no second resolver, no exec / write
# ===========================================================================


class TestConsumerAstBoundaries:
    def _consumer_tree(self):
        return ast.parse(CONSUMER_SOURCE.read_text(encoding="utf-8"))

    @staticmethod
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

    def test_consumer_imports_no_orchestrator_or_runtime_loop(self):
        mods = self._imported_modules(self._consumer_tree())
        forbidden = (
            "openclaw",
            "openclaw_foundup_orchestrator",
            "wre_master_orchestrator",
            "build_plan_swarm",
            "ai_overseer",
            "fam_daemon",
            "cabr_hooks",
        )
        hits = [m for m in mods if any(f in m for f in forbidden)]
        assert hits == [], f"consumer imports an orchestrator / runtime loop: {hits}"

    def test_consumer_defines_no_second_resolver(self):
        """AST scan: the consumer does NOT define a function literally named
        ``_resolve_validated_module_path`` (or the sibling resolver helpers /
        the ResolvedModulePath dataclass). It only imports them from the
        shared single-source module."""
        tree = self._consumer_tree()
        local_funcs = [
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        ]
        assert "_resolve_validated_module_path" not in local_funcs
        assert "_find_manifest_for_foundup_id" not in local_funcs
        local_classes = [
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
        ]
        assert "ResolvedModulePath" not in local_classes

    def test_exactly_one_resolver_definition_repo_wide(self):
        """Confirm the shared resolver remains the SINGLE implementation:
        exactly one ``def _resolve_validated_module_path`` across the agent
        src tree."""
        src_dir = Path(__file__).resolve().parents[1] / "src"
        defs = 0
        for py in src_dir.glob("*.py"):
            tree = ast.parse(py.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.FunctionDef)
                    and node.name == "_resolve_validated_module_path"
                ):
                    defs += 1
        assert defs == 1, f"expected exactly 1 resolver def in agent/src, found {defs}"

    def test_consumer_uses_shared_resolver_object(self):
        """The consumer binds the SAME resolver object as the executor."""
        from modules.foundups.agent.src import (
            context_bundle_dry_run_consumer as c,
        )
        from modules.foundups.agent.src import hermes_foundup_job_executor as e
        assert (
            c._resolve_validated_module_path is e._resolve_validated_module_path
        )

    def test_consumer_no_subprocess_network_dynamic_import_or_write(self):
        tree = self._consumer_tree()
        mods = self._imported_modules(tree)
        banned_top = {
            "subprocess", "socket", "ssl", "urllib", "requests", "http",
            "ftplib", "telnetlib", "ctypes", "importlib", "multiprocessing",
            "pty", "pickle", "marshal",
        }
        bad = {m for m in mods if m.split(".")[0] in banned_top}
        assert not bad, f"consumer imports banned modules: {bad}"

        banned_names = {"eval", "exec", "compile", "__import__", "input", "execfile"}
        banned_attrs = {
            "system", "popen", "Popen", "run", "call", "check_call",
            "check_output", "getoutput",
            "write_text", "write_bytes", "writelines",
            "urlopen", "urlretrieve", "connect", "spawn", "fork",
            "execv", "execve", "remove", "unlink", "rmdir", "makedirs",
            "chmod", "kill",
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
        assert not name_off, f"consumer calls banned names: {name_off}"
        assert not attr_off, f"consumer calls banned attrs: {attr_off}"

    def test_consumer_does_not_mutate_producer_or_validator(self):
        """The consumer imports the producer / source_authority for READ
        only; it does not import or reference the validator or mutate any
        sibling. (Source-level: no assignment to imported sibling attrs.)"""
        mods = self._imported_modules(self._consumer_tree())
        # It is allowed to import the bundle dataclass + the shared resolver
        # + source_authority; it must NOT import the validator directly (it
        # consumes already-validated trust).
        assert not any(
            "foundup_manifest_validator" in m for m in mods
        ), "consumer must not import the validator (trust is pre-validated)"

    def test_consumer_source_is_ascii_clean(self):
        data = CONSUMER_SOURCE.read_text(encoding="utf-8")
        non_ascii = [(i, c) for i, c in enumerate(data) if ord(c) > 127]
        assert not non_ascii, f"consumer source has non-ASCII chars: {non_ascii[:5]}"


# ===========================================================================
# 9. The 6 real manifests' dry-run consumption works
# ===========================================================================


class TestAllSixRealManifests:
    @pytest.mark.parametrize(
        "foundup_id,manifest_rel,expected_module",
        TARGET_MANIFESTS,
        ids=[m[0] for m in TARGET_MANIFESTS],
    )
    def test_real_manifest_dry_run_consumes(
        self, foundup_id, manifest_rel, expected_module
    ):
        bundle = _build_real_bundle(manifest_rel)
        result = consume_context_bundle_dry_run(bundle)
        assert isinstance(result, DryRunResult)
        assert result.source_authority == "monorepo_poc"
        assert result.resolved_module_path == expected_module
        assert result.dry_run is True
        assert result.real_execution_performed is False
        # gates are names; readiness all False.
        assert all(isinstance(g, str) for g in result.gates_to_recheck)
        assert all(v is False for v in result.readiness_flags.values())
        # evidence refs are refs only.
        for ref in result.evidence_refs:
            assert set(ref.keys()) == {"path", "sha256", "size_bytes", "role"}

    @pytest.mark.parametrize(
        "foundup_id,manifest_rel,expected_module",
        TARGET_MANIFESTS,
        ids=[m[0] for m in TARGET_MANIFESTS],
    )
    def test_real_manifest_with_matching_job_resolves(
        self, foundup_id, manifest_rel, expected_module
    ):
        bundle = _build_real_bundle(manifest_rel)
        job = create_job(
            tenant_id="t",
            requested_action="build_foundup",
            foundup_id=foundup_id,
            payload={"module_path": expected_module},
        )
        result = consume_context_bundle_dry_run(
            bundle, job=job, repo_root=REPO_ROOT
        )
        assert result.resolved_module_path == expected_module
        assert (
            result.rejected_input["payload_module_path_ignored"]
            == expected_module
        )


# ===========================================================================
# 10. Return-value-only: no side effects
# ===========================================================================


class TestReturnValueOnlyNoSideEffects:
    def test_no_file_write_during_consumption(self, monkeypatch):
        """No file is written by the consumer. We sentinel-guard open() in
        write modes via a patched builtins.open."""
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        real_open = open
        writes = []

        def _guard_open(file, mode="r", *args, **kwargs):
            if any(c in mode for c in ("w", "a", "x", "+")):
                writes.append((file, mode))
            return real_open(file, mode, *args, **kwargs)

        monkeypatch.setattr("builtins.open", _guard_open)
        consume_context_bundle_dry_run(bundle)
        assert writes == [], f"consumer performed file writes: {writes}"

    def test_result_is_frozen_dataclass(self):
        bundle = _build_real_bundle(
            "modules/foundups/gotjunk/foundup_manifest.json"
        )
        result = consume_context_bundle_dry_run(bundle)
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.dry_run = False  # type: ignore[misc]

    def test_no_fam_event_module_imported(self):
        """The consumer never imports the FAM daemon / event surface."""
        tree = ast.parse(CONSUMER_SOURCE.read_text(encoding="utf-8"))
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    mods.add(alias.name)
        assert not any("fam_daemon" in m or "fam_event" in m for m in mods)
