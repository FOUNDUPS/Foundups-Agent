"""In-memory adapter for FoundUps Agent Market PoC.

Provides deterministic ID generation for repeatable tests when
DETERMINISTIC_IDS=1 environment variable is set.

WSP References:
- WSP 5: Testing standards - deterministic behavior for tests
- WSP 11: Interface contract stability
"""

from __future__ import annotations

import os
from dataclasses import asdict
from typing import Dict, List, Optional

from .authorization import (
    CallerAuthorization, require_authorization, require_bound_independent_verification,
    require_verification_authorization,
)
from uuid import uuid4

from .exceptions import (
    CABRGateError,
    ImmutableFieldError,
    InvalidStateTransitionError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from .interfaces import (
    AgentJoinService,
    CABRHookService,
    ComputeAccessService,
    DistributionService,
    FoundupRegistryService,
    MvpOfferingService,
    ObservabilityService,
    RepoProvisioningAdapter,
    TaskPipelineService,
    TokenFactoryAdapter,
    TreasuryGovernanceService,
)
from .models import (
    AgentProfile,
    DistributionPost,
    EventRecord,
    Foundup,
    Payout,
    PayoutStatus,
    Proof,
    Task,
    TaskStatus,
    TokenTerms,
    Verification,
)


class DeterministicIdGenerator:
    """Counter-based ID generator for repeatable tests.

    When DETERMINISTIC_IDS=1, generates sequential IDs instead of UUIDs.
    This enables deterministic test assertions on generated IDs.
    """

    def __init__(self, deterministic: bool = False) -> None:
        self._deterministic = deterministic
        self._counters: Dict[str, int] = {}

    def next_id(self, prefix: str, length: int = 10) -> str:
        """Generate next ID with given prefix.

        Args:
            prefix: ID prefix (e.g., "ev", "join", "pay")
            length: Hex suffix length (ignored in deterministic mode)

        Returns:
            ID string like "ev_0001" (deterministic) or "ev_a1b2c3d4" (uuid)
        """
        if self._deterministic:
            self._counters.setdefault(prefix, 0)
            self._counters[prefix] += 1
            return f"{prefix}_{self._counters[prefix]:04d}"
        else:
            return f"{prefix}_{uuid4().hex[:length]}"

    def reset(self) -> None:
        """Reset all counters for test isolation."""
        self._counters.clear()


class InMemoryAgentMarket(
    FoundupRegistryService,
    TokenFactoryAdapter,
    AgentJoinService,
    TaskPipelineService,
    TreasuryGovernanceService,
    CABRHookService,
    ObservabilityService,
    DistributionService,
    RepoProvisioningAdapter,
    MvpOfferingService,
    ComputeAccessService,
):
    """Single-process PoC adapter with deterministic behavior for tests.

    Set DETERMINISTIC_IDS=1 or pass deterministic=True for repeatable test IDs.
    """

    def __init__(
        self,
        actor_roles: Optional[Dict[str, str]] = None,
        deterministic: bool = False,
        compute_access_enforced: bool = False,
        compute_default_credits: int = 0,
        capability_costs: Optional[Dict[str, int]] = None,
    ):
        # Check env var for deterministic mode (useful for pytest fixtures)
        use_deterministic = deterministic or os.getenv("DETERMINISTIC_IDS", "0") == "1"
        self._id_gen = DeterministicIdGenerator(deterministic=use_deterministic)

        self.actor_roles = actor_roles or {}
        self.foundups: Dict[str, Foundup] = {}
        self.tasks: Dict[str, Task] = {}
        self.proofs: Dict[str, Proof] = {}
        self.verifications: Dict[str, Verification] = {}
        self.payouts: Dict[str, Payout] = {}
        self.events: List[EventRecord] = []
        self.join_requests: Dict[str, tuple[str, AgentProfile]] = {}
        self.agents_by_foundup: Dict[str, List[AgentProfile]] = {}
        self.token_addresses: Dict[str, str] = {}
        self.treasury_accounts: Dict[str, str] = {}
        self.transfer_proposals: Dict[str, Dict[str, object]] = {}
        self.cabr_outputs: Dict[str, List[Dict[str, object]]] = {}
        self.distributions_by_task: Dict[str, DistributionPost] = {}
        self.repos: Dict[str, Dict[str, object]] = {}
        self.mvp_investor_terms: Dict[str, Dict[str, int]] = {}
        self.mvp_bids_by_foundup: Dict[str, List[Dict[str, object]]] = {}
        self.mvp_allocations_by_foundup: Dict[str, List[Dict[str, object]]] = {}
        self.mvp_treasury_injections: Dict[str, int] = {}

        # Investor program is anchored to F_0 only.
        self.investor_source_foundup_id = "F_0"
        self.investor_term_ups_default = 200
        self.investor_max_terms_default = 5
        self.compute_access_enforced = compute_access_enforced or (
            os.getenv("FAM_COMPUTE_ACCESS_ENFORCED", "0") == "1"
        )
        self.compute_default_credits = max(
            0,
            int(os.getenv("FAM_COMPUTE_DEFAULT_CREDITS", str(compute_default_credits))),
        )
        self.compute_plans: Dict[str, Dict[str, object]] = {}
        self.compute_wallets: Dict[str, Dict[str, int]] = {}
        self.compute_ledger: List[Dict[str, object]] = []
        self.compute_sessions: Dict[str, Dict[str, object]] = {}
        self.compute_meter_costs: Dict[str, int] = capability_costs or {
            "foundup.launch": 10,
            "task.create": 2,
            "task.claim": 1,
            "proof.submit": 2,
            "proof.verify": 2,
            "payout.trigger": 1,
            "distribution.publish": 1,
            "treasury.transfer_propose": 1,
        }

    def _role(self, actor_id: str) -> str:
        return self.actor_roles.get(actor_id, "advisory")

    def _require_role(self, actor_id: str, role: str) -> None:
        if self._role(actor_id) != role:
            raise PermissionDeniedError(f"actor '{actor_id}' requires role '{role}'")

    def _emit(
        self,
        event_type: str,
        actor_id: str,
        payload: Dict[str, object],
        foundup_id: Optional[str] = None,
        task_id: Optional[str] = None,
        proof_id: Optional[str] = None,
        payout_id: Optional[str] = None,
    ) -> None:
        event = EventRecord(
            event_id=self._id_gen.next_id("ev", 12),
            event_type=event_type,
            actor_id=actor_id,
            payload=payload,
            foundup_id=foundup_id,
            task_id=task_id,
            proof_id=proof_id,
            payout_id=payout_id,
        )
        self.events.append(event)

    def _ensure_compute_wallet(self, actor_id: str) -> Dict[str, int]:
        wallet = self.compute_wallets.get(actor_id)
        if wallet is None:
            wallet = {
                "credit_balance": self.compute_default_credits,
                "reserved_credits": 0,
            }
            self.compute_wallets[actor_id] = wallet
        return wallet

    def _compute_cost(self, capability: str) -> int:
        return max(0, int(self.compute_meter_costs.get(capability, 0)))

    def _enforce_compute_access(
        self,
        actor_id: str,
        capability: str,
        foundup_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        if not self.compute_access_enforced:
            return
        decision = self.ensure_access(actor_id, capability, foundup_id=foundup_id)
        if not bool(decision.get("allowed")):
            raise PermissionDeniedError(str(decision.get("reason", "access denied")))
        required = int(decision.get("required_credits", 0))
        if required > 0:
            self.debit_credits(
                actor_id=actor_id,
                amount=required,
                reason=reason or capability,
                foundup_id=foundup_id,
            )

    def activate_compute_plan(
        self,
        actor_id: str,
        tier: str = "builder",
        monthly_credit_allocation: int = 0,
    ) -> Dict[str, object]:
        if not actor_id:
            raise PermissionDeniedError("actor_id is required")
        if tier not in {"scout", "builder", "swarm", "sovereign"}:
            raise InvalidStateTransitionError(f"unsupported tier '{tier}'")
        allocation = max(0, int(monthly_credit_allocation))
        plan = {
            "plan_id": self._id_gen.next_id("plan", 10),
            "actor_id": actor_id,
            "tier": tier,
            "status": "active",
            "monthly_credit_allocation": allocation,
        }
        self.compute_plans[actor_id] = plan
        if allocation:
            wallet = self._ensure_compute_wallet(actor_id)
            wallet["credit_balance"] += allocation
        self._emit(
            "compute_plan_activated",
            actor_id,
            {
                "plan_id": plan["plan_id"],
                "tier": tier,
                "monthly_credit_allocation": allocation,
            },
        )
        return dict(plan)

    # FoundupRegistryService
    def create_foundup(self, foundup: Foundup) -> Foundup:
        self._enforce_compute_access(
            actor_id=foundup.owner_id,
            capability="foundup.launch",
            foundup_id=foundup.foundup_id,
            reason="create_foundup",
        )
        for existing in self.foundups.values():
            if existing.token_symbol.lower() == foundup.token_symbol.lower():
                raise ValidationError(
                    f"token_symbol '{foundup.token_symbol}' already exists"
                )
        self.foundups[foundup.foundup_id] = foundup
        self.agents_by_foundup.setdefault(foundup.foundup_id, [])
        self._emit(
            "foundup.created",
            foundup.owner_id,
            {"name": foundup.name, "token_symbol": foundup.token_symbol},
            foundup_id=foundup.foundup_id,
        )
        return foundup

    def update_foundup(self, foundup_id: str, updates: Dict[str, str]) -> Foundup:
        foundup = self.get_foundup(foundup_id)
        immutable_keys = set(foundup.immutable_metadata.keys())
        for key in updates:
            if key in immutable_keys:
                raise ImmutableFieldError(f"cannot modify immutable key '{key}'")
        foundup.mutable_metadata.update(updates)
        self._emit(
            "foundup.updated",
            foundup.owner_id,
            {"updated_keys": list(updates.keys())},
            foundup_id=foundup_id,
        )
        return foundup

    def get_foundup(self, foundup_id: str) -> Foundup:
        foundup = self.foundups.get(foundup_id)
        if not foundup:
            raise NotFoundError(f"foundup '{foundup_id}' not found")
        return foundup

    # TokenFactoryAdapter
    def deploy_token(self, foundup: Foundup, terms: TokenTerms) -> str:
        token_address = f"token_{foundup.foundup_id}_{terms.token_symbol}".lower()
        self.token_addresses[foundup.foundup_id] = token_address
        self.treasury_accounts[foundup.foundup_id] = terms.treasury_account
        self._emit(
            "token.deployed",
            foundup.owner_id,
            {"token_address": token_address, "max_supply": terms.max_supply},
            foundup_id=foundup.foundup_id,
        )
        return token_address

    def configure_vesting(self, token_address: str, terms: TokenTerms) -> None:
        self._emit(
            "token.vesting_configured",
            "system",
            {"token_address": token_address, "policy": terms.vesting_policy},
        )

    def get_treasury_account(self, foundup_id: str) -> str:
        if foundup_id not in self.treasury_accounts:
            raise NotFoundError(f"treasury account missing for foundup '{foundup_id}'")
        return self.treasury_accounts[foundup_id]

    # AgentJoinService
    def submit_join_request(self, foundup_id: str, profile: AgentProfile) -> str:
        self.get_foundup(foundup_id)
        request_id = self._id_gen.next_id("join", 10)
        self.join_requests[request_id] = (foundup_id, profile)
        self._emit(
            "agent.join_requested",
            profile.agent_id,
            {"request_id": request_id, "capability_tags": profile.capability_tags},
            foundup_id=foundup_id,
        )
        return request_id

    def approve_join_request(self, request_id: str, approver_id: str) -> AgentProfile:
        if request_id not in self.join_requests:
            raise NotFoundError(f"join request '{request_id}' not found")
        foundup_id, profile = self.join_requests.pop(request_id)
        self.agents_by_foundup.setdefault(foundup_id, []).append(profile)
        self._emit(
            "agent.join_approved",
            approver_id,
            {"request_id": request_id, "agent_id": profile.agent_id},
            foundup_id=foundup_id,
        )
        return profile

    def list_agents(self, foundup_id: str) -> List[AgentProfile]:
        self.get_foundup(foundup_id)
        return list(self.agents_by_foundup.get(foundup_id, []))

    # TaskPipelineService
    def create_task(self, task: Task) -> Task:
        self.get_foundup(task.foundup_id)
        self._enforce_compute_access(
            actor_id=task.creator_id,
            capability="task.create",
            foundup_id=task.foundup_id,
            reason="create_task",
        )
        self.tasks[task.task_id] = task
        self._emit(
            "task.created",
            task.creator_id,
            {"title": task.title, "reward_amount": task.reward_amount},
            foundup_id=task.foundup_id,
            task_id=task.task_id,
        )
        return task

    def get_task(self, task_id: str) -> Task:
        task = self.tasks.get(task_id)
        if not task:
            raise NotFoundError(f"task '{task_id}' not found")
        return task

    def claim_task(self, task_id: str, agent_id: str) -> Task:
        task = self.get_task(task_id)
        if task.status != TaskStatus.OPEN:
            raise InvalidStateTransitionError("task can only be claimed from open state")
        self._enforce_compute_access(
            actor_id=agent_id,
            capability="task.claim",
            foundup_id=task.foundup_id,
            reason="claim_task",
        )
        task.status = TaskStatus.CLAIMED
        task.assignee_id = agent_id
        self._emit(
            "task.claimed",
            agent_id,
            {},
            foundup_id=task.foundup_id,
            task_id=task.task_id,
        )
        return task

    def submit_proof(self, proof: Proof) -> Task:
        task = self.get_task(proof.task_id)
        if task.status != TaskStatus.CLAIMED:
            raise InvalidStateTransitionError("proof can only be submitted from claimed state")
        if task.assignee_id and task.assignee_id != proof.submitter_id:
            raise PermissionDeniedError("proof submitter must match task assignee")
        self._enforce_compute_access(
            actor_id=proof.submitter_id,
            capability="proof.submit",
            foundup_id=task.foundup_id,
            reason="submit_proof",
        )
        self.proofs[proof.proof_id] = proof
        task.proof_id = proof.proof_id
        task.status = TaskStatus.SUBMITTED
        self._emit(
            "proof.submitted",
            proof.submitter_id,
            {"artifact_uri": proof.artifact_uri},
            foundup_id=task.foundup_id,
            task_id=task.task_id,
            proof_id=proof.proof_id,
        )
        return task

    def verify_proof(
        self, task_id: str, verification: Verification, *,
        authorization: Optional[CallerAuthorization] = None,
    ) -> Task:
        task = self.get_task(task_id)
        proof = self.proofs.get(task.proof_id) if task.proof_id else None
        require_verification_authorization(authorization, task_id, task, proof, verification)
        if task.status != TaskStatus.SUBMITTED:
            raise InvalidStateTransitionError("verification requires submitted state")
        if not task.proof_id:
            raise InvalidStateTransitionError("verification requires proof")
        if not verification.approved:
            raise InvalidStateTransitionError("PoC supports approved verification only")
        self._enforce_compute_access(
            actor_id=verification.verifier_id,
            capability="proof.verify",
            foundup_id=task.foundup_id,
            reason="verify_proof",
        )
        self.verifications[verification.verification_id] = verification
        task.verification_id = verification.verification_id
        task.status = TaskStatus.VERIFIED
        self._emit(
            "proof.verified",
            verification.verifier_id,
            {"approved": verification.approved, "reason": verification.reason},
            foundup_id=task.foundup_id,
            task_id=task.task_id,
            proof_id=task.proof_id,
        )
        return task

    def trigger_payout(
        self, task_id: str, actor_id: str, *,
        authorization: Optional[CallerAuthorization] = None,
    ) -> Payout:
        task = self.get_task(task_id)
        require_authorization(authorization, actor_id, task.foundup_id, "treasury")
        if task.status != TaskStatus.VERIFIED:
            raise InvalidStateTransitionError("payout requires verified state")
        proof = self.proofs.get(task.proof_id) if task.proof_id else None
        decision = self.verifications.get(task.verification_id) if task.verification_id else None
        require_bound_independent_verification(task_id, task, proof, decision)
        if decision.verification_id != task.verification_id or decision.approved is not True:
            raise ValidationError("Payout requires the linked approved verification")
        self._enforce_compute_access(
            actor_id=actor_id,
            capability="payout.trigger",
            foundup_id=task.foundup_id,
            reason="trigger_payout",
        )
        payout = Payout(
            payout_id=self._id_gen.next_id("pay", 10),
            task_id=task.task_id,
            recipient_id=task.assignee_id or "unknown",
            amount=task.reward_amount,
            status=PayoutStatus.COMPLETED,
            reference=self._id_gen.next_id("inmem", 8),
            paid_at=task.created_at,
        )
        self.payouts[payout.payout_id] = payout
        task.payout_id = payout.payout_id
        task.status = TaskStatus.PAID
        self._emit(
            "payout.completed",
            actor_id,
            {"amount": payout.amount, "reference": payout.reference},
            foundup_id=task.foundup_id,
            task_id=task.task_id,
            proof_id=task.proof_id,
            payout_id=payout.payout_id,
        )
        return payout

    def get_trace(self, task_id: str) -> Dict[str, object]:
        task = self.get_task(task_id)
        foundup = self.get_foundup(task.foundup_id)
        proof = self.proofs.get(task.proof_id) if task.proof_id else None
        verification = self.verifications.get(task.verification_id) if task.verification_id else None
        payout = self.payouts.get(task.payout_id) if task.payout_id else None
        distribution = self.distributions_by_task.get(task_id)
        events = [
            asdict(e)
            for e in self.events
            if e.task_id == task_id or (e.foundup_id == foundup.foundup_id and e.task_id is None)
        ]
        return {
            "foundup": asdict(foundup),
            "task": asdict(task),
            "proof": asdict(proof) if proof else None,
            "verification": asdict(verification) if verification else None,
            "payout": asdict(payout) if payout else None,
            "distribution": asdict(distribution) if distribution else None,
            "events": events,
        }

    # TreasuryGovernanceService
    def propose_transfer(self, foundup_id: str, amount: int, reason: str, proposer_id: str) -> str:
        self.get_foundup(foundup_id)
        self._enforce_compute_access(
            actor_id=proposer_id,
            capability="treasury.transfer_propose",
            foundup_id=foundup_id,
            reason="propose_transfer",
        )
        proposal_id = self._id_gen.next_id("prop", 10)
        self.transfer_proposals[proposal_id] = {
            "foundup_id": foundup_id,
            "amount": amount,
            "reason": reason,
            "proposer_id": proposer_id,
            "approved": False,
        }
        self._emit(
            "treasury.transfer_proposed",
            proposer_id,
            {"proposal_id": proposal_id, "amount": amount, "reason": reason},
            foundup_id=foundup_id,
        )
        return proposal_id

    def approve_transfer(self, proposal_id: str, approver_id: str) -> None:
        proposal = self.transfer_proposals.get(proposal_id)
        if not proposal:
            raise NotFoundError(f"proposal '{proposal_id}' not found")
        proposal["approved"] = True
        proposal["approver_id"] = approver_id
        self._emit(
            "treasury.transfer_approved",
            approver_id,
            {"proposal_id": proposal_id},
            foundup_id=str(proposal["foundup_id"]),
        )

    def execute_transfer(self, proposal_id: str, executor_id: str) -> str:
        proposal = self.transfer_proposals.get(proposal_id)
        if not proposal:
            raise NotFoundError(f"proposal '{proposal_id}' not found")
        if not proposal.get("approved"):
            raise InvalidStateTransitionError("proposal must be approved before execution")
        reference = self._id_gen.next_id("xfer", 8)
        self._emit(
            "treasury.transfer_executed",
            executor_id,
            {"proposal_id": proposal_id, "reference": reference},
            foundup_id=str(proposal["foundup_id"]),
        )
        return reference

    def get_treasury_state(self, foundup_id: str) -> Dict[str, object]:
        self.get_foundup(foundup_id)
        proposals = [
            {"proposal_id": pid, **payload}
            for pid, payload in self.transfer_proposals.items()
            if payload["foundup_id"] == foundup_id
        ]
        return {
            "foundup_id": foundup_id,
            "treasury_account": self.treasury_accounts.get(foundup_id),
            "proposals": proposals,
        }

    # CABRHookService
    def build_cabr_input(self, foundup_id: str, window: str) -> Dict[str, object]:
        self.get_foundup(foundup_id)
        return {
            "foundup_id": foundup_id,
            "window": window,
            "tasks_total": len([t for t in self.tasks.values() if t.foundup_id == foundup_id]),
            "tasks_paid": len(
                [t for t in self.tasks.values() if t.foundup_id == foundup_id and t.status == TaskStatus.PAID]
            ),
            "events_total": len([e for e in self.events if e.foundup_id == foundup_id]),
        }

    def record_cabr_output(self, foundup_id: str, payload: Dict[str, object]) -> None:
        self.get_foundup(foundup_id)
        self.cabr_outputs.setdefault(foundup_id, []).append(payload)
        self._emit(
            "cabr.output_recorded",
            "system",
            payload,
            foundup_id=foundup_id,
        )

    # ObservabilityService
    def emit_event(self, event_type: str, actor_id: str, payload: Dict[str, object]) -> None:
        # Extract foundup_id and task_id from payload if present
        foundup_id = payload.get("foundup_id") if isinstance(payload.get("foundup_id"), str) else None
        task_id = payload.get("task_id") if isinstance(payload.get("task_id"), str) else None
        self._emit(event_type, actor_id, payload, foundup_id=foundup_id, task_id=task_id)

    def query_events(
        self,
        foundup_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[Dict[str, object]]:
        out: List[Dict[str, object]] = []
        for event in self.events:
            if foundup_id and event.foundup_id != foundup_id:
                continue
            if task_id and event.task_id != task_id:
                continue
            out.append(asdict(event))
        return out

    # DistributionService
    def build_milestone_payload(self, task_id: str) -> Dict[str, object]:
        task = self.get_task(task_id)
        foundup = self.get_foundup(task.foundup_id)
        verification = self.verifications.get(task.verification_id) if task.verification_id else None
        return {
            "foundup_id": foundup.foundup_id,
            "foundup_name": foundup.name,
            "task_id": task.task_id,
            "task_title": task.title,
            "task_status": task.status.value,
            "proof_id": task.proof_id,
            "verification_id": task.verification_id,
            "verification_reason": verification.reason if verification else None,
            "assignee_id": task.assignee_id,
            "reward_amount": task.reward_amount,
        }

    def get_latest_cabr_score(self, foundup_id: str) -> Optional[float]:
        """Get latest CABR score for foundup. Returns None if no CABR output recorded."""
        self.get_foundup(foundup_id)
        outputs = self.cabr_outputs.get(foundup_id, [])
        if not outputs:
            return None
        latest = outputs[-1]
        return float(latest.get("score", 0.0))

    def publish_verified_milestone(
        self,
        task_id: str,
        actor_id: str,
        channel: str = "moltbook",
        cabr_threshold: float = 0.0,
    ) -> DistributionPost:
        task = self.get_task(task_id)
        self._require_role(actor_id, "distribution")
        if task.status not in {TaskStatus.VERIFIED, TaskStatus.PAID}:
            raise InvalidStateTransitionError("distribution requires verified or paid state")
        self._enforce_compute_access(
            actor_id=actor_id,
            capability="distribution.publish",
            foundup_id=task.foundup_id,
            reason="publish_verified_milestone",
        )

        # CABR gate check
        if cabr_threshold > 0.0:
            cabr_score = self.get_latest_cabr_score(task.foundup_id)
            if cabr_score is None:
                raise CABRGateError(
                    f"CABR score missing for foundup '{task.foundup_id}' - distribution blocked"
                )
            if cabr_score < cabr_threshold:
                raise CABRGateError(
                    f"CABR score {cabr_score:.2f} below threshold {cabr_threshold:.2f} - distribution blocked"
                )

        existing = self.distributions_by_task.get(task_id)
        if existing:
            return existing

        payload = self.build_milestone_payload(task_id)
        distribution = DistributionPost(
            distribution_id=self._id_gen.next_id("dist", 10),
            foundup_id=task.foundup_id,
            task_id=task.task_id,
            channel=channel,
            content=f"[{payload['foundup_name']}] Milestone verified: {payload['task_title']}",
            actor_id=actor_id,
            dedupe_key=f"{task.task_id}:{channel}:verified",
        )
        self.distributions_by_task[task_id] = distribution
        self._emit(
            "milestone.verified_published",
            actor_id,
            {
                "distribution_id": distribution.distribution_id,
                "channel": channel,
                "dedupe_key": distribution.dedupe_key,
                "cabr_threshold": cabr_threshold,
            },
            foundup_id=task.foundup_id,
            task_id=task.task_id,
            proof_id=task.proof_id,
            payout_id=task.payout_id,
        )
        return distribution

    def get_distribution(self, task_id: str) -> Optional[DistributionPost]:
        self.get_task(task_id)
        return self.distributions_by_task.get(task_id)

    # RepoProvisioningAdapter
    def provision_repo(
        self,
        foundup_id: str,
        repo_name: str,
        provider: str = "github",
        default_branch: str = "main",
    ) -> str:
        """Provision a repository for the foundup. Returns repo URL (in-memory stub)."""
        self.get_foundup(foundup_id)
        repo_url = f"https://{provider}.com/foundups/{repo_name}"
        self.repos[foundup_id] = {
            "foundup_id": foundup_id,
            "repo_name": repo_name,
            "repo_url": repo_url,
            "provider": provider,
            "default_branch": default_branch,
        }
        self._emit(
            "repo.provisioned",
            "system",
            {
                "repo_name": repo_name,
                "repo_url": repo_url,
                "provider": provider,
                "default_branch": default_branch,
            },
            foundup_id=foundup_id,
        )
        return repo_url

    def get_repo_metadata(self, foundup_id: str) -> Optional[Dict[str, object]]:
        """Get repository metadata for a foundup."""
        self.get_foundup(foundup_id)
        return self.repos.get(foundup_id)

    # MvpOfferingService
    def accrue_investor_terms(
        self,
        investor_id: str,
        terms: int = 1,
        term_ups: int = 200,
        max_terms: int = 5,
    ) -> Dict[str, int]:
        if not investor_id:
            raise PermissionDeniedError("investor_id is required")
        if terms <= 0:
            raise InvalidStateTransitionError("terms must be positive")
        if term_ups <= 0:
            raise InvalidStateTransitionError("term_ups must be positive")
        if max_terms <= 0:
            raise InvalidStateTransitionError("max_terms must be positive")

        entry = self.mvp_investor_terms.setdefault(
            investor_id,
            {"terms": 0, "available_ups": 0, "spent_ups": 0},
        )
        previous_terms = entry["terms"]
        next_terms = min(max_terms, previous_terms + terms)
        added_terms = next_terms - previous_terms
        added_ups = added_terms * term_ups

        entry["terms"] = next_terms
        entry["available_ups"] += added_ups

        result = {
            "terms": entry["terms"],
            "available_ups": entry["available_ups"],
            "spent_ups": entry["spent_ups"],
            "added_terms": added_terms,
            "added_ups": added_ups,
        }
        self._emit(
            "mvp.subscription_accrued",
            investor_id,
            {
                "source_foundup_id": self.investor_source_foundup_id,
                "terms": result["terms"],
                "available_ups": result["available_ups"],
                "added_terms": result["added_terms"],
                "added_ups": result["added_ups"],
            },
            foundup_id=self.investor_source_foundup_id,
        )
        return result

    def place_mvp_bid(
        self,
        foundup_id: str,
        investor_id: str,
        bid_ups: int,
    ) -> str:
        self.get_foundup(foundup_id)
        if not investor_id:
            raise PermissionDeniedError("investor_id is required")
        if bid_ups <= 0:
            raise InvalidStateTransitionError("bid_ups must be positive")

        entry = self.mvp_investor_terms.setdefault(
            investor_id,
            {"terms": 0, "available_ups": 0, "spent_ups": 0},
        )
        if entry["available_ups"] < bid_ups:
            raise PermissionDeniedError(
                f"insufficient UPS balance for investor '{investor_id}' "
                f"(available={entry['available_ups']}, requested={bid_ups})"
            )

        entry["available_ups"] -= bid_ups
        entry["spent_ups"] += bid_ups

        bid = {
            "bid_id": self._id_gen.next_id("bid", 10),
            "foundup_id": foundup_id,
            "investor_id": investor_id,
            "bid_ups": bid_ups,
        }
        self.mvp_bids_by_foundup.setdefault(foundup_id, []).append(bid)
        self._emit(
            "mvp.bid_submitted",
            investor_id,
            {
                "bid_id": bid["bid_id"],
                "source_foundup_id": self.investor_source_foundup_id,
                "bid_ups": bid_ups,
                "remaining_ups": entry["available_ups"],
            },
            foundup_id=foundup_id,
        )
        return str(bid["bid_id"])

    def get_mvp_bids(self, foundup_id: str) -> List[Dict[str, object]]:
        self.get_foundup(foundup_id)
        return [dict(item) for item in self.mvp_bids_by_foundup.get(foundup_id, [])]

    def resolve_mvp_offering(
        self,
        foundup_id: str,
        actor_id: str,
        token_amount: int,
        top_n: int = 1,
    ) -> List[Dict[str, object]]:
        self.get_foundup(foundup_id)
        self._require_role(actor_id, "treasury")
        if token_amount <= 0:
            raise InvalidStateTransitionError("token_amount must be positive")
        if top_n <= 0:
            raise InvalidStateTransitionError("top_n must be positive")

        bids = self.mvp_bids_by_foundup.get(foundup_id, [])
        if not bids:
            return []

        sorted_bids = sorted(
            bids,
            key=lambda item: (int(item["bid_ups"]), str(item["bid_id"])),
            reverse=True,
        )
        winners = sorted_bids[:top_n]
        winner_ids = {str(item["bid_id"]) for item in winners}

        # Refund non-winning bids.
        for bid in sorted_bids[top_n:]:
            investor_id = str(bid["investor_id"])
            entry = self.mvp_investor_terms.setdefault(
                investor_id,
                {"terms": 0, "available_ups": 0, "spent_ups": 0},
            )
            refund_ups = int(bid["bid_ups"])
            entry["available_ups"] += refund_ups
            entry["spent_ups"] = max(0, entry["spent_ups"] - refund_ups)

        winner_count = len(winners)
        per_winner_tokens = token_amount // winner_count
        remainder_tokens = token_amount % winner_count
        total_injection_ups = 0
        allocations: List[Dict[str, object]] = []

        for idx, bid in enumerate(winners):
            bid_id = str(bid["bid_id"])
            bid_ups = int(bid["bid_ups"])
            token_slice = per_winner_tokens + (1 if idx < remainder_tokens else 0)
            total_injection_ups += bid_ups
            allocations.append(
                {
                    "allocation_id": self._id_gen.next_id("alloc", 10),
                    "foundup_id": foundup_id,
                    "bid_id": bid_id,
                    "investor_id": str(bid["investor_id"]),
                    "bid_ups": bid_ups,
                    "token_amount": token_slice,
                    "allocation_rank": idx + 1,
                }
            )

        self.mvp_bids_by_foundup[foundup_id] = [b for b in bids if str(b["bid_id"]) not in winner_ids]
        self.mvp_allocations_by_foundup.setdefault(foundup_id, []).extend(allocations)
        self.mvp_treasury_injections[foundup_id] = (
            self.mvp_treasury_injections.get(foundup_id, 0) + total_injection_ups
        )
        self._emit(
            "mvp.offering_resolved",
            actor_id,
            {
                "source_foundup_id": self.investor_source_foundup_id,
                "winner_count": winner_count,
                "token_amount": token_amount,
                "total_injection_ups": total_injection_ups,
                "allocations": allocations,
            },
            foundup_id=foundup_id,
        )
        return allocations

    # Convenience helpers for simulator/testing
    def get_investor_subscription_state(self, investor_id: str) -> Dict[str, int]:
        entry = self.mvp_investor_terms.get(investor_id)
        if not entry:
            return {"terms": 0, "available_ups": 0, "spent_ups": 0}
        return dict(entry)

    def get_mvp_treasury_injection(self, foundup_id: str) -> int:
        return self.mvp_treasury_injections.get(foundup_id, 0)

    # ComputeAccessService
    def ensure_access(
        self,
        actor_id: str,
        capability: str,
        foundup_id: Optional[str] = None,
    ) -> Dict[str, object]:
        required = self._compute_cost(capability)
        wallet = self._ensure_compute_wallet(actor_id)
        available = int(wallet["credit_balance"])
        plan = self.compute_plans.get(actor_id)
        tier = str(plan["tier"]) if plan else "scout"

        if not self.compute_access_enforced or required <= 0:
            return {
                "allowed": True,
                "reason": "access not enforced" if not self.compute_access_enforced else "unmetered capability",
                "required_credits": required,
                "available_credits": available,
                "tier": tier,
                "capability": capability,
            }

        if plan is None or str(plan.get("status")) != "active":
            reason = "active compute plan required"
            self._emit(
                "paywall_access_denied",
                actor_id,
                {"capability": capability, "reason": reason, "required_credits": required, "available_credits": available},
                foundup_id=foundup_id,
            )
            return {
                "allowed": False,
                "reason": reason,
                "required_credits": required,
                "available_credits": available,
                "tier": tier,
                "capability": capability,
            }

        if tier == "scout":
            reason = "tier 'scout' cannot execute metered capabilities"
            self._emit(
                "paywall_access_denied",
                actor_id,
                {"capability": capability, "reason": reason, "required_credits": required, "available_credits": available},
                foundup_id=foundup_id,
            )
            return {
                "allowed": False,
                "reason": reason,
                "required_credits": required,
                "available_credits": available,
                "tier": tier,
                "capability": capability,
            }

        if available < required:
            reason = "insufficient compute credits"
            self._emit(
                "paywall_access_denied",
                actor_id,
                {"capability": capability, "reason": reason, "required_credits": required, "available_credits": available},
                foundup_id=foundup_id,
            )
            return {
                "allowed": False,
                "reason": reason,
                "required_credits": required,
                "available_credits": available,
                "tier": tier,
                "capability": capability,
            }

        return {
            "allowed": True,
            "reason": "ok",
            "required_credits": required,
            "available_credits": available,
            "tier": tier,
            "capability": capability,
        }

    def get_wallet(self, actor_id: str) -> Dict[str, object]:
        wallet = self._ensure_compute_wallet(actor_id)
        plan = self.compute_plans.get(actor_id)
        return {
            "actor_id": actor_id,
            "credit_balance": int(wallet["credit_balance"]),
            "reserved_credits": int(wallet["reserved_credits"]),
            "tier": str(plan["tier"]) if plan else "scout",
            "plan_status": str(plan["status"]) if plan else "none",
        }

    def purchase_credits(
        self,
        actor_id: str,
        amount: int,
        rail: str,
        payment_ref: str,
    ) -> Dict[str, object]:
        if amount <= 0:
            raise InvalidStateTransitionError("amount must be positive")
        if not rail:
            raise InvalidStateTransitionError("rail is required")
        if not payment_ref:
            raise InvalidStateTransitionError("payment_ref is required")

        wallet = self._ensure_compute_wallet(actor_id)
        wallet["credit_balance"] += amount
        entry = {
            "entry_id": self._id_gen.next_id("cc", 10),
            "actor_id": actor_id,
            "entry_type": "purchase",
            "amount": int(amount),
            "rail": rail,
            "reason": "purchase_credits",
            "payment_ref": payment_ref,
            "foundup_id": None,
        }
        self.compute_ledger.append(entry)
        self._emit(
            "compute_credits_purchased",
            actor_id,
            {
                "entry_id": entry["entry_id"],
                "amount": amount,
                "rail": rail,
                "payment_ref": payment_ref,
                "credit_balance": int(wallet["credit_balance"]),
            },
        )
        return dict(entry)

    def debit_credits(
        self,
        actor_id: str,
        amount: int,
        reason: str,
        foundup_id: Optional[str] = None,
    ) -> Dict[str, object]:
        if amount <= 0:
            raise InvalidStateTransitionError("amount must be positive")
        if not reason:
            raise InvalidStateTransitionError("reason is required")
        wallet = self._ensure_compute_wallet(actor_id)
        available = int(wallet["credit_balance"])
        if available < amount:
            self._emit(
                "paywall_access_denied",
                actor_id,
                {
                    "capability": reason,
                    "reason": "insufficient compute credits",
                    "required_credits": amount,
                    "available_credits": available,
                },
                foundup_id=foundup_id,
            )
            raise PermissionDeniedError(
                f"insufficient compute credits (available={available}, requested={amount})"
            )

        wallet["credit_balance"] -= amount
        entry = {
            "entry_id": self._id_gen.next_id("cc", 10),
            "actor_id": actor_id,
            "entry_type": "debit",
            "amount": int(amount),
            "rail": "metered_execution",
            "reason": reason,
            "payment_ref": None,
            "foundup_id": foundup_id,
        }
        self.compute_ledger.append(entry)
        self._emit(
            "compute_credits_debited",
            actor_id,
            {
                "entry_id": entry["entry_id"],
                "amount": amount,
                "reason": reason,
                "credit_balance": int(wallet["credit_balance"]),
            },
            foundup_id=foundup_id,
        )
        return dict(entry)

    def record_compute_session(
        self,
        actor_id: str,
        foundup_id: str,
        workload: Dict[str, object],
    ) -> str:
        if not foundup_id:
            raise InvalidStateTransitionError("foundup_id is required")
        self.get_foundup(foundup_id)
        session_id = self._id_gen.next_id("ccsess", 10)
        self.compute_sessions[session_id] = {
            "session_id": session_id,
            "actor_id": actor_id,
            "foundup_id": foundup_id,
            "workload": dict(workload),
        }
        self._emit(
            "compute_session_recorded",
            actor_id,
            {
                "session_id": session_id,
                "workload": dict(workload),
            },
            foundup_id=foundup_id,
        )
        return session_id

    def rebate_credits(
        self,
        actor_id: str,
        amount: int,
        reason: str,
    ) -> Dict[str, object]:
        if amount <= 0:
            raise InvalidStateTransitionError("amount must be positive")
        if not reason:
            raise InvalidStateTransitionError("reason is required")
        wallet = self._ensure_compute_wallet(actor_id)
        wallet["credit_balance"] += amount
        entry = {
            "entry_id": self._id_gen.next_id("cc", 10),
            "actor_id": actor_id,
            "entry_type": "rebate",
            "amount": int(amount),
            "rail": "rebate",
            "reason": reason,
            "payment_ref": None,
            "foundup_id": None,
        }
        self.compute_ledger.append(entry)
        self._emit(
            "compute_credits_rebated",
            actor_id,
            {
                "entry_id": entry["entry_id"],
                "amount": amount,
                "reason": reason,
                "credit_balance": int(wallet["credit_balance"]),
            },
        )
        return dict(entry)

    # Test isolation helpers
    def reset(self) -> None:
        """Reset all state for test isolation.

        Clears all stored data and resets ID counters.
        Call between tests for deterministic behavior.
        """
        self.foundups.clear()
        self.tasks.clear()
        self.proofs.clear()
        self.verifications.clear()
        self.payouts.clear()
        self.events.clear()
        self.join_requests.clear()
        self.agents_by_foundup.clear()
        self.token_addresses.clear()
        self.treasury_accounts.clear()
        self.transfer_proposals.clear()
        self.cabr_outputs.clear()
        self.distributions_by_task.clear()
        self.repos.clear()
        self.mvp_investor_terms.clear()
        self.mvp_bids_by_foundup.clear()
        self.mvp_allocations_by_foundup.clear()
        self.mvp_treasury_injections.clear()
        self.compute_plans.clear()
        self.compute_wallets.clear()
        self.compute_ledger.clear()
        self.compute_sessions.clear()
        self._id_gen.reset()

    def get_tasks_by_foundup(self, foundup_id: str) -> List[Task]:
        """Get all tasks for a FoundUp. Used by CABR hooks."""
        return [t for t in self.tasks.values() if t.foundup_id == foundup_id]
