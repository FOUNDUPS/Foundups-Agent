# -*- coding: utf-8 -*-
"""
Tests for WRE_CONTEXT_BUNDLE_DRYRUN_RUNTIME_WIRING_PHASE2 (W6).

Proves the standalone #786 ContextBundle dry-run consumer is wired into the
EXISTING #774 dispatch seam (``FoundUpJobConsumer`` -> ``ConsumerResult``)
on the seam's PRE-EXISTING dry-run branch ONLY (Hermes execution status
SIMULATED, ``real_execution_performed`` False, HERMES_DELEGATE_ENABLED
unset/0). The real-exec / Hermes real-delegation boundary stays BLOCKED and
is never touched by this wiring.

No skip / no xfail on any boundary assertion; negatives prove the boundary.

Boundaries proven here (all through the live seam ``consume_one``):
  1. A valid monorepo_poc job on the dry-run branch -> the EXISTING
     ConsumerResult carries the #786 DryRunResult evidence
     (resolved_module_path = validated canonical, source_authority =
     monorepo_poc, gates as recheck-NAMES, readiness all False,
     evidence_refs = refs + sha256 only, dry_run True / real exec False).
  2. Real executor sink / Hermes real delegation / subprocess
     (Popen/run/call) are MOCKED and assert_not_called THROUGH the seam's
     dry-run path.
  3. HERMES_DELEGATE_ENABLED=0 keeps real delegation BLOCKED; the
     real-exec branch is NOT taken in dry-run (status stays SIMULATED).
  4. A forged payload module_path / source_module -> rejected via the
     SHARED resolver; the rejected value is observable in the receipt and
     is never used as the resolved path.
  5. A non-monorepo_poc bundle -> refused by the consumer the seam calls;
     no gate-pass boolean is asserted / serialized.
  6. ContextBundle stays refs + sha256 only (no file bodies) end-to-end.
  7. AST: the seam introduces NO second resolver and NO new orchestrator
     import; ``_resolve_validated_module_path`` has exactly one definition
     repo-wide.

WSP Compliance:
  WSP 11 : Interface contract (typed ConsumerResult + DryRunResult).
  WSP 50 : Pre-action validation (shared resolver gate before any build).
  WSP 77 : Agent coordination (WRE consumer owns dispatch; no new loop).
  WSP 97 : Truth boundaries (dry-run only, no overclaim, no real exec).
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
from modules.foundups.agent.src.context_bundle_dry_run_consumer import (
    consume_context_bundle_dry_run,
)
from modules.foundups.agent.src.context_bundle_builder import (
    build_context_bundle,
)
from modules.infrastructure.wre_core.src.foundup_job_consumer import (
    ConsumerResult,
    FoundUpJobConsumer,
)

# Repo root: tests/ -> wre_core/ -> infrastructure/ -> modules/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[4]

CONSUMER_SEAM_SOURCE = (
    Path(__file__).resolve().parents[1] / "src" / "foundup_job_consumer.py"
)

FIXED_T0 = "2026-06-12T00:00:00Z"

# A real monorepo_poc FoundUp whose manifest passes the #773 validator.
# validate_foundup reaches the PRE-EXISTING dry-run (SIMULATED) branch;
# build/extract are blocked earlier by the destructive-action guard and so
# do NOT exercise the dry-run wiring (asserted in TestBranchSelection).
GOTJUNK_FOUNDUP_ID = "gotjunk_001"
GOTJUNK_MODULE_PATH = "modules/foundups/gotjunk"
GOTJUNK_MANIFEST = "modules/foundups/gotjunk/foundup_manifest.json"

# A second real FoundUp used to prove cross-FoundUp payload substitution
# is rejected by the shared resolver.
KOSEI_MODULE_PATH = "modules/foundups/kosei"

# Authority / gate-pass keys that must NEVER appear in the serialized
# context_bundle_dry_run evidence (they would imply pass-state / promotion).
_FORBIDDEN_SERIALIZED_KEYS = frozenset({
    "gate_passed", "gates_passed", "passed", "all_gates_passed",
    "security_passed", "permission_passed", "dry_run_passed", "build_passed",
    "verification_complete", "cabr_ready", "cabr_passed", "payout_ready",
    "payout_approved", "dao_ready", "dao_approved", "dao_passed",
})


@pytest.fixture(autouse=True)
def _force_dry_run_branch(monkeypatch):
    """Every test in this module runs with HERMES_DELEGATE_ENABLED unset.

    This pins the seam onto its PRE-EXISTING dry-run branch (SIMULATED)
    and keeps real Hermes delegation BLOCKED for the whole module.
    """
    monkeypatch.delenv("HERMES_DELEGATE_ENABLED", raising=False)


def _valid_job(payload=None):
    return create_job(
        tenant_id="tenant_w6",
        requested_action="validate_foundup",
        foundup_id=GOTJUNK_FOUNDUP_ID,
        payload=payload if payload is not None else {"module_path": GOTJUNK_MODULE_PATH},
    )


# ===========================================================================
# 1. Happy path: DryRunResult reaches the EXISTING ConsumerResult receipt
# ===========================================================================


class TestDryRunResultReachesConsumerResult:
    def test_valid_job_attaches_context_bundle_dry_run(self):
        job = _valid_job()
        consumer = FoundUpJobConsumer(dry_run=True)
        result = consumer.consume_one(job)

        assert isinstance(result, ConsumerResult)
        assert result.dispatched is True
        # The seam took its PRE-EXISTING dry-run branch.
        assert result.checkpoint_state == "SIMULATED"
        assert result.real_execution_performed is False

        cb = result.context_bundle_dry_run
        assert cb is not None, "dry-run evidence must be attached on dry-run branch"
        assert cb["dry_run"] is True
        assert cb["real_execution_performed"] is False

    def test_resolved_module_path_is_validated_canonical(self):
        # Forged-looking payload with the CORRECT module is still resolved
        # through the shared resolver, not trusted blindly.
        job = _valid_job(payload={"module_path": GOTJUNK_MODULE_PATH})
        result = FoundUpJobConsumer(dry_run=True).consume_one(job)
        cb = result.context_bundle_dry_run
        assert cb is not None
        assert cb["resolved_module_path"] == GOTJUNK_MODULE_PATH

    def test_source_authority_monorepo_poc_visible(self):
        result = FoundUpJobConsumer(dry_run=True).consume_one(_valid_job())
        cb = result.context_bundle_dry_run
        assert cb is not None
        assert cb["source_authority"] == "monorepo_poc"

    def test_gates_are_recheck_names_not_pass_state(self):
        result = FoundUpJobConsumer(dry_run=True).consume_one(_valid_job())
        cb = result.context_bundle_dry_run
        assert cb is not None
        gates = cb["gates_to_recheck"]
        assert isinstance(gates, list)
        assert len(gates) >= 1
        # Every gate entry is a NAME string, never a pass-state boolean.
        for g in gates:
            assert isinstance(g, str)
            assert not isinstance(g, bool)

    def test_no_gate_pass_boolean_serialized(self):
        result = FoundUpJobConsumer(dry_run=True).consume_one(_valid_job())
        cb = result.context_bundle_dry_run
        assert cb is not None
        blob = json.dumps(cb)
        for forbidden in _FORBIDDEN_SERIALIZED_KEYS:
            assert ('"' + forbidden + '"') not in blob, (
                "forbidden pass-state key leaked into receipt: " + forbidden
            )

    def test_readiness_remains_false(self):
        result = FoundUpJobConsumer(dry_run=True).consume_one(_valid_job())
        cb = result.context_bundle_dry_run
        assert cb is not None
        for k, v in cb["readiness_flags"].items():
            assert v is False, "readiness flag promoted: " + k

    def test_evidence_refs_are_refs_and_hashes_only_no_bodies(self):
        result = FoundUpJobConsumer(dry_run=True).consume_one(_valid_job())
        cb = result.context_bundle_dry_run
        assert cb is not None
        refs = cb["evidence_refs"]
        assert len(refs) >= 1
        allowed = {"path", "sha256", "size_bytes", "role"}
        for ref in refs:
            assert set(ref.keys()) <= allowed, (
                "evidence ref carries an unexpected key (possible body leak): "
                + repr(set(ref.keys()) - allowed)
            )
            assert isinstance(ref["sha256"], str) and len(ref["sha256"]) == 64
        # Defense-in-depth: no body / content / source-text key anywhere.
        blob = json.dumps(cb)
        for body_key in ('"body"', '"content"', '"source_text"', '"file_body"'):
            assert body_key not in blob

    def test_dry_run_evidence_survives_consumerresult_to_dict(self):
        result = FoundUpJobConsumer(dry_run=True).consume_one(_valid_job())
        d = result.to_dict()
        assert "context_bundle_dry_run" in d
        assert d["context_bundle_dry_run"] is not None
        assert d["context_bundle_dry_run"]["source_authority"] == "monorepo_poc"
        # The EXISTING WSP 97 truth fields are still present and False.
        assert d["real_execution_performed"] is False
        assert d["verification_complete"] is False
        assert d["cabr_ready"] is False
        assert d["payout_ready"] is False


# ===========================================================================
# 2. Real-exec sinks asserted NOT called through the seam's dry-run path
# ===========================================================================


class TestRealExecSinksNotCalled:
    def test_subprocess_sinks_not_called_through_seam(self):
        job = _valid_job()
        with mock.patch("subprocess.Popen") as m_popen, \
                mock.patch("subprocess.run") as m_run, \
                mock.patch("subprocess.call") as m_call:
            result = FoundUpJobConsumer(dry_run=True).consume_one(job)

        # The dry-run wiring must have run...
        assert result.context_bundle_dry_run is not None
        assert result.context_bundle_dry_run["source_authority"] == "monorepo_poc"
        # ...without ever invoking a subprocess sink.
        m_popen.assert_not_called()
        m_run.assert_not_called()
        m_call.assert_not_called()

    def test_hermes_real_delegate_loader_not_called_through_seam(self):
        # The executor's real-delegation loader must never be reached on the
        # dry-run branch. Patch it to explode if called; the seam must still
        # produce dry-run evidence.
        job = _valid_job()
        with mock.patch(
            "modules.infrastructure.wre_core.src.hermes_job_executor."
            "HermesJobExecutor._lazy_import_delegate_task",
            side_effect=AssertionError("real delegate loader must not run in dry-run"),
        ) as m_delegate:
            result = FoundUpJobConsumer(dry_run=True).consume_one(job)

        assert result.checkpoint_state == "SIMULATED"
        assert result.real_execution_performed is False
        assert result.context_bundle_dry_run is not None
        m_delegate.assert_not_called()


# ===========================================================================
# 3. Flag boundary: HERMES_DELEGATE_ENABLED=0 keeps real delegation BLOCKED
# ===========================================================================


class TestDelegateFlagBoundary:
    def test_flag_zero_keeps_real_delegation_blocked(self, monkeypatch):
        monkeypatch.setenv("HERMES_DELEGATE_ENABLED", "0")
        job = _valid_job()
        result = FoundUpJobConsumer(dry_run=True).consume_one(job)
        # Real-exec branch (BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED) is NOT
        # taken; the dry-run (SIMULATED) branch is.
        assert result.checkpoint_state == "SIMULATED"
        assert result.real_execution_performed is False
        assert result.context_bundle_dry_run is not None

    def test_real_exec_branch_attaches_no_bundle(self):
        # When the executor returns a non-SIMULATED (real-exec/blocked) status,
        # the wiring helper attaches NO bundle evidence. Drive this directly
        # through the helper with a stand-in result so the gate is proven
        # without enabling any real delegation.
        consumer = FoundUpJobConsumer(dry_run=True)

        class _RealExecResult:
            status = type("S", (), {"value": "BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED"})()
            real_execution_performed = False

        cb = consumer._attach_context_bundle_dry_run(
            _valid_job(), _RealExecResult(), "job_real"
        )
        assert cb is None, "real-exec/BLOCKED branch must attach no bundle evidence"

    def test_real_execution_performed_true_attaches_no_bundle(self):
        # Defense-in-depth: even a SIMULATED-labelled result that claims real
        # execution must not attach bundle evidence.
        consumer = FoundUpJobConsumer(dry_run=True)

        class _LyingResult:
            status = type("S", (), {"value": "SIMULATED"})()
            real_execution_performed = True

        cb = consumer._attach_context_bundle_dry_run(
            _valid_job(), _LyingResult(), "job_lie"
        )
        assert cb is None


# ===========================================================================
# 4. Forged payload rejected via the SHARED resolver (observable, never used)
# ===========================================================================


class TestForgedPayloadRejected:
    def test_cross_foundup_payload_rejected_and_observable(self):
        # foundup_id gotjunk_001 but payload points at kosei's module.
        job = _valid_job(payload={"module_path": KOSEI_MODULE_PATH})
        result = FoundUpJobConsumer(dry_run=True).consume_one(job)
        cb = result.context_bundle_dry_run
        assert cb is not None
        # No preview produced; the forged value is observable but never used.
        assert cb.get("resolved_module_path") is None
        assert cb["context_bundle_error"] == "module_path_resolution_failed"
        assert cb["fail_token"] == "cross_foundup_mismatch"
        assert cb["payload_module_path_ignored"] == KOSEI_MODULE_PATH

    def test_backslash_payload_syntactically_rejected(self):
        job = _valid_job(payload={"module_path": "modules\\foundups\\gotjunk"})
        result = FoundUpJobConsumer(dry_run=True).consume_one(job)
        cb = result.context_bundle_dry_run
        assert cb is not None
        assert cb.get("resolved_module_path") is None
        assert cb["context_bundle_error"] == "module_path_resolution_failed"
        assert cb["fail_token"] == "syntactic_reject"

    def test_source_module_alias_forgery_rejected(self):
        # No module_path, but a forged source_module alias pointing elsewhere.
        job = _valid_job(payload={"source_module": KOSEI_MODULE_PATH})
        result = FoundUpJobConsumer(dry_run=True).consume_one(job)
        cb = result.context_bundle_dry_run
        assert cb is not None
        assert cb.get("resolved_module_path") is None
        assert cb["fail_token"] == "cross_foundup_mismatch"
        assert cb["payload_module_path_ignored"] == KOSEI_MODULE_PATH


# ===========================================================================
# 5. Non-monorepo_poc bundle refused by the consumer the seam calls
# ===========================================================================


class TestNonMonorepoRefused:
    def test_non_monorepo_bundle_is_refused_by_consumer(self):
        # The builder always sets monorepo_poc, so tamper a built bundle to a
        # deferred stage and prove the consumer the seam relies on REFUSES it
        # (no DryRunResult, no gate-pass boolean).
        from modules.foundups.agent.src.context_bundle_dry_run_consumer import (
            DryRunConsumerRejected,
        )

        bundle = build_context_bundle(
            REPO_ROOT / GOTJUNK_MANIFEST, REPO_ROOT, created_at=FIXED_T0
        )
        tampered = dataclasses.replace(bundle, source_authority="dao_managed")
        with pytest.raises(DryRunConsumerRejected):
            consume_context_bundle_dry_run(tampered)

    def test_seam_only_ever_emits_monorepo_poc(self):
        # Whatever real job reaches the dry-run branch, the seam's attached
        # source_authority is monorepo_poc (the builder constant); the seam
        # cannot promote a stage.
        result = FoundUpJobConsumer(dry_run=True).consume_one(_valid_job())
        cb = result.context_bundle_dry_run
        assert cb is not None
        assert cb["source_authority"] == "monorepo_poc"


# ===========================================================================
# 6. Branch selection: only SIMULATED dry-run branch is wired
# ===========================================================================


class TestBranchSelection:
    def test_guard_blocked_action_attaches_no_bundle(self):
        # build_foundup is blocked by the destructive-action guard inside the
        # executor (BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD), NOT the SIMULATED
        # dry-run branch -> no bundle evidence attached.
        job = create_job(
            tenant_id="tenant_w6",
            requested_action="build_foundup",
            foundup_id=GOTJUNK_FOUNDUP_ID,
            payload={"module_path": GOTJUNK_MODULE_PATH},
        )
        result = FoundUpJobConsumer(dry_run=True).consume_one(job)
        assert result.checkpoint_state == "BLOCKED"
        assert result.real_execution_performed is False
        assert result.context_bundle_dry_run is None

    def test_non_dispatched_route_attaches_no_bundle(self):
        # A non-routed action never dispatches to Hermes and so never reaches
        # the wiring helper.
        job = create_job(
            tenant_id="tenant_w6",
            requested_action="queue_foundup_job",
            foundup_id=GOTJUNK_FOUNDUP_ID,
            payload={"module_path": GOTJUNK_MODULE_PATH},
        )
        result = FoundUpJobConsumer(dry_run=True).consume_one(job)
        assert result.dispatched is False
        assert result.context_bundle_dry_run is None


# ===========================================================================
# 7. AST guards: no second resolver, no new orchestrator import in the seam
# ===========================================================================


class TestStaticBoundaries:
    def _seam_tree(self):
        src = CONSUMER_SEAM_SOURCE.read_text(encoding="utf-8")
        return ast.parse(src), src

    def test_seam_defines_no_module_path_resolver(self):
        tree, _ = self._seam_tree()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.name != "_resolve_validated_module_path", (
                    "seam must import the shared resolver, never define one"
                )

    def test_exactly_one_resolver_definition_repo_wide(self):
        # The single source of truth lives in module_path_resolution.py.
        resolver_def_count = 0
        for path in REPO_ROOT.rglob("*.py"):
            # Skip virtualenvs / vendored trees / caches.
            parts = set(path.parts)
            if parts & {".venv", "venv", "vendor", "node_modules", "__pycache__", ".git"}:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == "_resolve_validated_module_path":
                        resolver_def_count += 1
        assert resolver_def_count == 1, (
            "expected exactly one _resolve_validated_module_path definition; "
            "found " + str(resolver_def_count)
        )

    def test_seam_imports_no_new_orchestrator(self):
        _, src = self._seam_tree()
        # NOTE: the consumer legitimately imports get_job_queue/remove_jobs_by_id
        # from openclaw_foundup_orchestrator for the PRE-EXISTING drain path;
        # that is not the wiring. Assert the wiring added no NEW orchestrator
        # class / loop import.
        assert "WREMasterOrchestrator" not in src
        assert "openclaw_orchestrator import" not in src

    def test_wiring_additions_are_ascii_clean(self):
        # The W6 wiring additions must be ASCII-clean. The seam file carries
        # ONE pre-existing non-ASCII char in its original module header (an
        # em-dash) that predates this slice and is out of scope to mutate;
        # this test asserts the wiring marker lines and the new method body
        # introduced ZERO additional non-ASCII characters.
        raw = CONSUMER_SEAM_SOURCE.read_text(encoding="utf-8")
        # Every line that belongs to the W6 wiring must be pure ASCII.
        wiring_markers = (
            "WRE_CONTEXT_BUNDLE_DRYRUN_RUNTIME_WIRING_PHASE2",
            "_attach_context_bundle_dry_run",
            "context_bundle_dry_run",
        )
        wiring_lines = [
            line for line in raw.splitlines()
            if any(marker in line for marker in wiring_markers)
        ]
        assert wiring_lines, "wiring markers must be present in the seam"
        for line in wiring_lines:
            non_ascii = [ch for ch in line if ord(ch) > 127]
            assert non_ascii == [], (
                "W6 wiring line is not ASCII-clean: " + repr(line)
            )
        # And the wiring did not increase the file's non-ASCII count beyond
        # the single pre-existing header char.
        total_non_ascii = sum(1 for ch in raw if ord(ch) > 127)
        assert total_non_ascii <= 1, (
            "wiring introduced non-ASCII characters into the seam (count="
            + str(total_non_ascii) + ")"
        )
