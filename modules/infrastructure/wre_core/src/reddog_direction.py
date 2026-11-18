#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RedDog Direction - Observe -> Propose -> Direct (DRY-RUN ONLY)

The RedDog "Architect hat" coordination surface for the recursive
improvement loop (WAE-L1). It DIRECTS dry-run proposals; it executes,
mutates, dispatches, and merges NOTHING.

Pipeline (WAE-L1):
  OBSERVE  : FMAS / violation / low-fruit findings (parsed by fmas_improvement_bridge)
  PROPOSE  : dry-run ImprovementJobs; admitted findings are PENDING while
             malformed or untrusted WSP 62 inputs are BLOCKED
  DIRECT   : RedDog autonomously orders proposals by WSP-15 (low-lying fruit
             first) and assigns ONE direction per proposal - a RECOMMENDATION /
             priority / routing decision + status note. NOT execution.

This is NOT a new orchestrator and NOT a new DAE. It is the Architect hat
folding into the existing wre_core recursive_improvement +
improvement_job_contract surface. It composes the existing
fmas_improvement_bridge (which emits dry-run PENDING or BLOCKED proposals)
and adds the autonomous triage/direction + a fail-closed execution seam.

WSP Compliance:
  WSP 11  : Interface contract (typed API)
  WSP 15  : Low-lying fruit priority ordering (low-fruit first)
  WSP 50  : Pre-Action Verification (consumes already-scoped jobs)
  WSP 77  : Agent Coordination (Architect hat direction only)
  WSP 91  : Observability (direction notes + reason codes)
  WSP 97  : System Execution Prompting (dry_run=True, observe/propose/direct only)

WSP 97 TRUTH BOUNDARIES (WAE-L1 - all enforced + tested):
  - Emits dry_run=True jobs only: admissible normalized findings are PENDING;
    malformed or untrusted WSP 62 inputs are BLOCKED.
  - RedDog "direction" is a recommendation/priority/routing decision + status
    note - NOT execution, NOT mutation, NOT merge.
  - NO dispatch (no dispatch_foundup / Hermes execute / worker spawn).
  - NO queue mutation (no add/remove/drain of any job queue).
  - NO auto-fix execution; NO real source/repo/file mutation.
  - LOW-FRUIT FIRST: low_lying_fruit / LOW-risk may be prioritized, but direct
    FMAS parsing has no authenticated authority receipt and is never marked
    ready-to-advance; MEDIUM/HIGH or review-required proposals escalate.
  - EXECUTION SEAM FAILS CLOSED: advance_to_execution() is the interface L2
    will implement; in L1 it returns NOT_READY (no hard verifier exists yet).

AST DENYLIST (enforced by test_reddog_direction.py):
  This module is AST-forbidden from importing mutator/dispatch primitives:
  get_job_queue, remove_jobs_by_id, drain, dispatch_foundup, Hermes execute,
  or any auto-fix entrypoint.

NAVIGATION:
  -> Uses: improvement_job_contract.py (ImprovementJob, ImprovementStatus, ...)
  -> Uses: fmas_improvement_bridge.py (parse_fmas_findings - observe->propose)
  -> Called by: execute_improvement (openclaw_execution_routes.py) - emission point
  -> L2 attaches a hard verifier at advance_to_execution() (currently NOT_READY)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

from .improvement_job_contract import (
    ImprovementJob,
    ImprovementRiskLevel,
    ImprovementStatus,
)
from .fmas_improvement_bridge import parse_fmas_findings

logger = logging.getLogger("reddog_direction")


# ---------------------------------------------------------------------------
# Direction (RedDog recommendation - NOT execution)
# ---------------------------------------------------------------------------


class RedDogDirection(str, Enum):
    """
    The single direction RedDog assigns to a proposal.

    Each value is a RECOMMENDATION / routing decision, never an execution.
    """

    PRIORITIZE = "prioritize"
    """Low-lying fruit, LOW risk: surface first for downstream attention."""

    ROUTE = "route"
    """Route to a worker lane (recommendation only - no worker is spawned)."""

    REQUEST_CONTEXT = "request_context"
    """Insufficient scope/context to triage; recommend gathering more."""

    DEFER = "defer"
    """Valid but not low-fruit; recommend deferring behind higher-priority work."""

    MARK_READY_TO_ADVANCE = "mark_ready_to_advance"
    """Reserved compatibility value; WAE-L1 never emits readiness because no
    authenticated provenance and hard verifier are composed here."""

    ESCALATE_TO_012 = "escalate_to_012"
    """MEDIUM/HIGH risk or requires_architect_review: escalate to 012/architect.
    Never auto-advanced."""


# ---------------------------------------------------------------------------
# Execution seam outcome (fail-closed - L2 attaches here)
# ---------------------------------------------------------------------------


class AdvanceOutcome(str, Enum):
    """Outcome of an advance_to_execution() attempt."""

    NOT_READY = "NOT_READY"
    """Reserved fail-closed result if a future trusted caller supplies readiness."""

    BLOCKED = "BLOCKED"
    """Job not eligible to advance (not marked ready / not low-risk)."""


@dataclass
class AdvanceResult:
    """Result of the fail-closed execution seam (advance_to_execution)."""

    advanced: bool
    """Always False in L1 - nothing advances to execution."""

    outcome: AdvanceOutcome
    """NOT_READY when a hard verifier is required but absent (L1)."""

    reason: str
    """Human-readable explanation."""

    job_id: str = ""
    """The job that was (not) advanced."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "advanced": self.advanced,
            "outcome": self.outcome.value,
            "reason": self.reason,
            "job_id": self.job_id,
        }


# ---------------------------------------------------------------------------
# Directed proposal (a job + its RedDog direction)
# ---------------------------------------------------------------------------


@dataclass
class DirectedProposal:
    """An ImprovementJob proposal paired with RedDog's direction decision."""

    job: ImprovementJob
    """A dry-run ImprovementJob; inadmissible input may already be BLOCKED."""

    direction: RedDogDirection
    """The single direction RedDog assigned (recommendation only)."""

    ready_to_advance: bool = False
    """Compatibility field only; the WAE-L1 director always leaves it false."""

    priority_rank: int = 0
    """0-based ordering rank assigned by triage (lower = higher priority)."""

    note: str = ""
    """RedDog status note explaining the direction."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job.job_id,
            "finding_id": self.job.finding_id,
            "status": self.job.status.value,
            "dry_run": self.job.dry_run,
            "risk_level": self.job.risk_level.value,
            "low_lying_fruit": self.job.wsp15_priority.low_lying_fruit,
            "requires_architect_review": (
                self.job.wsp15_priority.requires_architect_review
            ),
            "direction": self.direction.value,
            "ready_to_advance": self.ready_to_advance,
            "priority_rank": self.priority_rank,
            "note": self.note,
        }


# ---------------------------------------------------------------------------
# WSP-15 ordering key (low-lying fruit first)
# ---------------------------------------------------------------------------

# Lower number = higher priority (sorts first).
_COMPLEXITY_ORDER = {
    "trivial": 0,
    "simple": 1,
    "moderate": 2,
    "complex": 3,
    "unknown": 4,
}

_BLAST_RADIUS_ORDER = {
    "single_file": 0,
    "single_module": 1,
    "cross_module": 2,
    "system_wide": 3,
    "unknown": 4,
}

_RISK_ORDER = {
    ImprovementRiskLevel.LOW: 0,
    ImprovementRiskLevel.MEDIUM: 1,
    ImprovementRiskLevel.HIGH: 2,
}


def _wsp15_order_key(job: ImprovementJob) -> tuple:
    """
    Build a WSP-15 ordering key so low-lying fruit sorts FIRST.

    Priority dimensions (most significant first):
      1. low_lying_fruit (True first)
      2. risk level (LOW first)
      3. complexity (trivial first)
      4. blast radius (single_file first)
    """
    prio = job.wsp15_priority
    return (
        0 if prio.low_lying_fruit else 1,
        _RISK_ORDER.get(job.risk_level, 9),
        _COMPLEXITY_ORDER.get(prio.estimated_complexity, 9),
        _BLAST_RADIUS_ORDER.get(prio.blast_radius, 9),
    )


# ---------------------------------------------------------------------------
# RedDog Director (Architect hat - observe/propose/direct, DRY-RUN ONLY)
# ---------------------------------------------------------------------------


class RedDogDirector:
    """
    RedDog-direction component (WAE-L1).

    Autonomously DIRECTS dry-run proposals by WSP-15 priority. It executes
    nothing: it orders proposals (low-fruit first) and assigns one direction
    each. The Architect hat folds here - it is not a new orchestrator.
    """

    def __init__(self, requested_by: str = "reddog_director") -> None:
        self.requested_by = requested_by

    # ------------------------------------------------------------------
    # OBSERVE -> PROPOSE
    # ------------------------------------------------------------------

    def observe_and_propose(
        self,
        findings: List[Dict[str, Any]],
    ) -> List[ImprovementJob]:
        """
        OBSERVE findings -> PROPOSE dry-run PENDING or BLOCKED jobs.

        Delegates to the existing bridge. Admissible normalized findings are
        PENDING; malformed or untrusted WSP 62 inputs are BLOCKED. This method
        does NOT execute or mutate anything.

        Args:
            findings: List of FMAS/violation/low-fruit finding dicts.

        Returns:
            Dry-run ImprovementJob proposals in PENDING or BLOCKED state.
        """
        jobs = parse_fmas_findings(findings)
        logger.info(
            "[REDDOG] OBSERVE->PROPOSE: %d findings -> %d dry-run proposals",
            len(findings),
            len(jobs),
        )
        return jobs

    # ------------------------------------------------------------------
    # DIRECT (triage + order + assign one direction per proposal)
    # ------------------------------------------------------------------

    def direct(self, jobs: List[ImprovementJob]) -> List[DirectedProposal]:
        """
        DIRECT proposals: order by WSP-15 (low-fruit first) and assign one
        direction per proposal. Recommendation only - executes nothing.

        Args:
            jobs: dry-run proposals; inadmissible jobs may already be BLOCKED.

        Returns:
            DirectedProposals ordered low-fruit first, each with one direction.
        """
        ordered = sorted(jobs, key=_wsp15_order_key)
        directed: List[DirectedProposal] = []
        for rank, job in enumerate(ordered):
            proposal = self._direct_one(job, rank)
            directed.append(proposal)
        logger.info(
            "[REDDOG] DIRECT: ordered %d proposals (low-fruit first), "
            "ready_to_advance=%d, escalated=%d",
            len(directed),
            sum(1 for p in directed if p.ready_to_advance),
            sum(
                1
                for p in directed
                if p.direction == RedDogDirection.ESCALATE_TO_012
            ),
        )
        return directed

    def _direct_one(self, job: ImprovementJob, rank: int) -> DirectedProposal:
        """Assign exactly one direction to a single proposal (no execution)."""
        inadmissible = self._inadmissible_direction(job, rank)
        if inadmissible is not None:
            return inadmissible
        review = self._review_direction(job, rank)
        if review is not None:
            return review
        return self._low_risk_direction(job, rank)

    def _inadmissible_direction(
        self, job: ImprovementJob, rank: int
    ) -> DirectedProposal | None:
        if job.status != ImprovementStatus.PENDING or not job.dry_run:
            return DirectedProposal(
                job=job,
                direction=RedDogDirection.DEFER,
                ready_to_advance=False,
                priority_rank=rank,
                note="Blocked/non-dry-run input is not an admissible L1 proposal.",
            )
        if not job.scope.is_well_formed():
            return DirectedProposal(
                job=job,
                direction=RedDogDirection.REQUEST_CONTEXT,
                ready_to_advance=False,
                priority_rank=rank,
                note="Scope is absent, non-canonical, or not confined.",
            )
        return None

    def _review_direction(
        self, job: ImprovementJob, rank: int
    ) -> DirectedProposal | None:
        prio = job.wsp15_priority
        if (
            job.risk_level in (ImprovementRiskLevel.MEDIUM, ImprovementRiskLevel.HIGH)
            or prio.requires_architect_review
        ):
            return DirectedProposal(
                job=job,
                direction=RedDogDirection.ESCALATE_TO_012,
                ready_to_advance=False,
                priority_rank=rank,
                note=(
                    f"Escalate to 012/architect: risk={job.risk_level.value}, "
                    f"requires_architect_review="
                    f"{prio.requires_architect_review}. Never auto-advanced."
                ),
            )
        return None

    def _low_risk_direction(
        self, job: ImprovementJob, rank: int
    ) -> DirectedProposal:
        prio = job.wsp15_priority
        if job.can_auto_approve():
            return DirectedProposal(
                job=job,
                direction=RedDogDirection.PRIORITIZE,
                ready_to_advance=False,
                priority_rank=rank,
                note=(
                    "Low-lying fruit and LOW risk, but direct FMAS provenance "
                    "is advisory; authenticated verification is still required."
                ),
            )
        if prio.low_lying_fruit:
            return DirectedProposal(
                job=job,
                direction=RedDogDirection.PRIORITIZE,
                ready_to_advance=False,
                priority_rank=rank,
                note="Low-lying fruit, LOW risk: surface first for attention.",
            )
        return DirectedProposal(
            job=job,
            direction=RedDogDirection.ROUTE,
            ready_to_advance=False,
            priority_rank=rank,
            note="LOW risk, scoped: route recommendation (no worker spawned).",
        )

    # ------------------------------------------------------------------
    # OBSERVE -> PROPOSE -> DIRECT (single entry point)
    # ------------------------------------------------------------------

    def observe_propose_direct(
        self,
        findings: List[Dict[str, Any]],
    ) -> List[DirectedProposal]:
        """
        Full WAE-L1 path: OBSERVE findings -> PROPOSE dry-run jobs ->
        DIRECT (order low-fruit first, assign one direction each).

        Executes nothing. Returns directed proposals only.
        """
        jobs = self.observe_and_propose(findings)
        return self.direct(jobs)

    # ------------------------------------------------------------------
    # FAIL-CLOSED EXECUTION SEAM (L2 attaches a hard verifier here)
    # ------------------------------------------------------------------

    def advance_to_execution(
        self,
        proposal: DirectedProposal,
    ) -> AdvanceResult:
        """
        Fail-closed execution seam. This is the interface L2 will implement
        (attach a hard verifier). In L1 it ALWAYS refuses to advance:

          - WAE-L1 emits no readiness authority, so normal proposals are BLOCKED.
          - A compatibility object carrying ready_to_advance=True still returns
            NOT_READY because no hard verifier (L2) is composed.

        Args:
            proposal: A DirectedProposal from direct().

        Returns:
            AdvanceResult with advanced=False (always, in L1).
        """
        if not proposal.ready_to_advance:
            return AdvanceResult(
                advanced=False,
                outcome=AdvanceOutcome.BLOCKED,
                reason=(
                    "Proposal not marked ready-to-advance "
                    f"(direction={proposal.direction.value}); not eligible."
                ),
                job_id=proposal.job.job_id,
            )

        # Marked ready, but the hard verifier (L2) does not exist yet.
        return AdvanceResult(
            advanced=False,
            outcome=AdvanceOutcome.NOT_READY,
            reason=(
                "EXECUTION_SEAM_FAILS_CLOSED: no L2 hard verifier is wired. "
                "Compatibility readiness cannot advance without an "
                "independent hard verifier (L2). Merge remains 012/DAO."
            ),
            job_id=proposal.job.job_id,
        )


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def observe_propose_direct(
    findings: List[Dict[str, Any]],
    requested_by: str = "reddog_director",
) -> List[DirectedProposal]:
    """Convenience wrapper: run the full WAE-L1 observe->propose->direct path."""
    return RedDogDirector(requested_by=requested_by).observe_propose_direct(findings)
