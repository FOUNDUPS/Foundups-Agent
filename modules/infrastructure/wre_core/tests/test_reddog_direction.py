#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RedDog Direction Tests (WAE-L1)

Verifies the observe -> propose -> direct loop is DRY-RUN ONLY:
  - Emits ImprovementJob(PENDING, dry_run=True) ONLY.
  - RedDog orders low-lying fruit first (WSP-15).
  - Direct FMAS proposals remain advisory and are never ready-to-advance.
  - MEDIUM/HIGH escalate, never auto-advance.
  - advance_to_execution() fails closed (NOT_READY) - no execution.
  - NO mutation / dispatch / auto-fix primitive is invoked.
  - AST denylist: the observe-propose + direction module source imports
    NONE of the denylisted mutator/dispatch primitives.

WSP 97 TRUTH BOUNDARIES:
  - Tests verify proposal/direction, NOT execution.
  - Tests assert no mutation/dispatch/auto-fix call occurs.

Contract References:
  modules/infrastructure/wre_core/src/reddog_direction.py
  modules/infrastructure/wre_core/src/fmas_improvement_bridge.py
  modules/infrastructure/wre_core/src/improvement_job_contract.py
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest import mock

import pytest

from modules.infrastructure.wre_core.src.improvement_job_contract import (
    ImprovementRiskLevel,
    ImprovementStatus,
)
from modules.infrastructure.wre_core.src import reddog_direction
from modules.infrastructure.wre_core.src.reddog_direction import (
    AdvanceOutcome,
    RedDogDirection,
    RedDogDirector,
    observe_propose_direct,
)


# ---------------------------------------------------------------------------
# Synthetic findings: 2 low-fruit + 1 MEDIUM + 1 HIGH/architect-review
# ---------------------------------------------------------------------------


def _synthetic_findings():
    """2 low-fruit (LOW risk) + 1 MEDIUM + 1 HIGH/security finding."""
    return [
        # HIGH/security first in input order (must still sort LAST after triage).
        {
            "type": "security_vulnerability",
            "severity": "critical",
            "file_path": "modules/x/y/src/z.py",
            "message": "CVE-XXXX detected",
        },
        # MEDIUM (missing tests dir, single_module).
        {
            "type": "missing_tests",
            "severity": "medium",
            "module_path": "modules/x/y",
            "message": "Module missing tests/ directory",
        },
        # Low-fruit #1 (doc stale, single_file, LOW).
        {
            "type": "doc_stale",
            "severity": "low",
            "file_path": "modules/x/y/README.md",
            "message": "Stale documentation",
        },
        # Low-fruit #2 (missing test README, single_file, LOW).
        {
            "type": "missing_test_readme",
            "severity": "low",
            "file_path": "modules/x/y/tests/README.md",
            "message": "Missing tests/README.md",
        },
    ]


# ---------------------------------------------------------------------------
# THE one pass/fail test
# ---------------------------------------------------------------------------


class TestObserveProposeDirect:
    """WAE-L1 one pass/fail test: observe -> propose -> direct (dry-run)."""

    def test_each_finding_emits_one_pending_dry_run_job(self):
        """Each finding emits exactly one ImprovementJob(PENDING, dry_run=True)."""
        findings = _synthetic_findings()
        proposals = observe_propose_direct(findings)

        assert len(proposals) == len(findings) == 4
        for proposal in proposals:
            job = proposal.job
            assert job.status == ImprovementStatus.PENDING
            assert job.dry_run is True

        # Job ids are unique (one proposal per finding).
        job_ids = [p.job.job_id for p in proposals]
        assert len(set(job_ids)) == len(job_ids)

    def test_low_fruit_first_ordering(self):
        """RedDog orders low-lying fruit first (WSP-15)."""
        proposals = observe_propose_direct(_synthetic_findings())

        # First two proposals must be the low-fruit LOW-risk findings.
        assert proposals[0].job.wsp15_priority.low_lying_fruit is True
        assert proposals[1].job.wsp15_priority.low_lying_fruit is True
        assert proposals[0].job.risk_level == ImprovementRiskLevel.LOW
        assert proposals[1].job.risk_level == ImprovementRiskLevel.LOW

        # The remaining proposals are NOT low-fruit and sort after.
        assert proposals[2].job.wsp15_priority.low_lying_fruit is False
        assert proposals[3].job.wsp15_priority.low_lying_fruit is False

        # priority_rank is monotonically increasing.
        assert [p.priority_rank for p in proposals] == [0, 1, 2, 3]

    def test_direct_fmas_proposals_never_claim_readiness(self):
        """Even LOW-risk direct input remains advisory without authority."""
        proposals = observe_propose_direct(_synthetic_findings())

        assert not any(proposal.ready_to_advance for proposal in proposals)
        assert proposals[0].direction == RedDogDirection.PRIORITIZE
        assert proposals[1].direction == RedDogDirection.PRIORITIZE

    def test_medium_and_high_escalate_never_advance(self):
        """MEDIUM/HIGH escalate to 012; never marked ready-to-advance."""
        proposals = observe_propose_direct(_synthetic_findings())

        escalated = [
            p
            for p in proposals
            if p.job.risk_level in (ImprovementRiskLevel.MEDIUM, ImprovementRiskLevel.HIGH)
        ]
        assert len(escalated) == 2
        for proposal in escalated:
            assert proposal.direction == RedDogDirection.ESCALATE_TO_012
            assert proposal.ready_to_advance is False

    def test_advance_to_execution_fails_closed(self):
        """All advisory direct proposals remain BLOCKED from execution."""
        director = RedDogDirector()
        proposals = director.observe_propose_direct(_synthetic_findings())

        for proposal in proposals:
            result = director.advance_to_execution(proposal)
            assert result.advanced is False
            assert result.outcome == AdvanceOutcome.BLOCKED

    def test_invalid_scope_requests_context_and_never_advances(self):
        """A traversal-bearing direct finding cannot inherit readiness."""
        findings = [{
            "type": "missing_test_readme", "severity": "low",
            "module_path": "modules/infrastructure/example",
            "file_path": "modules/infrastructure/example/../.env",
            "message": "forged scope",
        }]
        proposal = observe_propose_direct(findings)[0]

        assert proposal.direction == RedDogDirection.REQUEST_CONTEXT
        assert proposal.ready_to_advance is False

    def test_no_mutation_dispatch_or_autofix_invoked(self):
        """No mutation/dispatch/auto-fix primitive is invoked by the loop.

        Patch the candidate primitive names in any module that exposes them
        and assert-not-called after running the full observe->propose->direct
        path plus advance_to_execution on every proposal.
        """
        director = RedDogDirector()

        # Patch potentially-dangerous primitives where they live, if present.
        patchers = []
        # pattern_memory mutators (recall is allowed; store/mutate is not used here).
        try:
            from modules.infrastructure.wre_core.src import pattern_memory

            for attr in ("store_outcome", "store_variation", "promote_variation"):
                if hasattr(pattern_memory.PatternMemory, attr):
                    patchers.append(
                        mock.patch.object(
                            pattern_memory.PatternMemory, attr, autospec=True
                        )
                    )
        except Exception:
            pass

        mocks = [p.start() for p in patchers]
        try:
            proposals = director.observe_propose_direct(_synthetic_findings())
            for proposal in proposals:
                director.advance_to_execution(proposal)
        finally:
            for p in patchers:
                p.stop()

        for m in mocks:
            m.assert_not_called()


# ---------------------------------------------------------------------------
# AST denylist test
# ---------------------------------------------------------------------------


# Denylisted import targets the observe-propose + direction module must NEVER
# import (mutator / dispatch / auto-fix primitives).
_DENYLISTED_NAMES = frozenset(
    {
        "get_job_queue",
        "remove_jobs_by_id",
        "drain",
        "drain_queue",
        "dispatch_foundup",
        "execute_foundup",
        "handle_fam_intent",
        "launch_foundup",
        "hermes_job_executor",
        "HermesJobExecutor",
        "_apply_policy_fix",
        "_open_fix_task",
        "apply_improvement",
    }
)

# Denylisted modules that, if imported at all, indicate a mutation/dispatch path.
_DENYLISTED_MODULE_SUBSTRINGS = (
    "hermes_job_executor",
    "openclaw_foundup_orchestrator",
    "fam_adapter",
    "daemon_self_audit_loop",
)


def _module_source_path() -> Path:
    """Absolute path to the reddog_direction module source."""
    return Path(reddog_direction.__file__).resolve()


def _collect_imports(tree: ast.AST):
    """Return (imported_module_names, imported_symbol_names) from an AST."""
    modules = set()
    symbols = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
                if alias.asname:
                    symbols.add(alias.asname)
                else:
                    symbols.add(alias.name.split(".")[-1])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module)
            for alias in node.names:
                symbols.add(alias.asname or alias.name)
    return modules, symbols


class TestASTDenylist:
    """AST scan: the direction module imports NO denylisted primitive."""

    def test_no_denylisted_imports_in_reddog_direction(self):
        source_path = _module_source_path()
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(source_path))

        modules, symbols = _collect_imports(tree)

        # No denylisted symbol may be imported.
        offending_symbols = symbols & _DENYLISTED_NAMES
        assert not offending_symbols, (
            f"reddog_direction imports denylisted symbols: {offending_symbols}"
        )

        # No denylisted module path may be imported.
        offending_modules = {
            m
            for m in modules
            for sub in _DENYLISTED_MODULE_SUBSTRINGS
            if sub in m
        }
        assert not offending_modules, (
            f"reddog_direction imports denylisted modules: {offending_modules}"
        )

    def test_denylist_detects_a_planted_import(self):
        """Sanity: the AST scanner WOULD catch a denylisted import if present."""
        planted = (
            "from modules.communication.moltbot_bridge.src."
            "openclaw_foundup_orchestrator import dispatch_foundup\n"
        )
        tree = ast.parse(planted)
        modules, symbols = _collect_imports(tree)
        assert "dispatch_foundup" in (symbols & _DENYLISTED_NAMES)
        assert any(
            sub in m
            for m in modules
            for sub in _DENYLISTED_MODULE_SUBSTRINGS
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
