"""FAM Bridge - thin calls into existing FAM modules.

Primary goal is contract-preserving wrappers over FAM interfaces.
Small deterministic hardening logic is allowed for simulation stability.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


class _IdGenerator:
    """ID generator for simulation entities."""

    def __init__(self, deterministic: bool = True) -> None:
        self._deterministic = deterministic
        self._counters: Dict[str, int] = {}

    def next_id(self, prefix: str) -> str:
        """Generate next ID with prefix."""
        if self._deterministic:
            self._counters.setdefault(prefix, 0)
            self._counters[prefix] += 1
            return f"{prefix}_{self._counters[prefix]:04d}"
        return f"{prefix}_{uuid4().hex[:10]}"

    def reset(self) -> None:
        """Reset counters."""
        self._counters.clear()


class FAMBridge:
    """Bridge to FAM modules for simulator.

    Provides thin wrappers around:
    - InMemoryAgentMarket (registry, task pipeline)
    - FAMDaemon (event emission)
    - TokenFactory (phantom plug if not wired)
    - TreasuryGovernance (phantom plug if not wired)
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        deterministic: bool = True,
        fam_daemon: Optional[Any] = None,
    ) -> None:
        """Initialize FAM bridge.

        Args:
            data_dir: Directory for FAMDaemon persistence
            deterministic: Use deterministic ID generation
        """
        self._data_dir = data_dir or Path(__file__).parent.parent / "memory"
        self._deterministic = deterministic
        self._id_gen = _IdGenerator(deterministic=deterministic)
        self._external_daemon = fam_daemon

        # Lazy-loaded components
        self._market: Optional[Any] = None
        self._daemon: Optional[Any] = None

        self._initialize()

    def _initialize(self) -> None:
        """Initialize FAM components."""
        try:
            # Import FAM modules
            from modules.foundups.agent_market.src.in_memory import InMemoryAgentMarket
            from modules.foundups.agent_market.src.fam_daemon import FAMDaemon

            # Create in-memory market with verifier/treasury roles
            self._market = InMemoryAgentMarket(
                actor_roles={
                    "system": "admin",
                    "verifier_0": "verifier",
                    "treasury_0": "treasury",
                    "distribution_0": "distribution",
                },
                deterministic=self._deterministic,
            )

            # Simulation host configuration, separate from caller-supplied IDs.
            self._simulation_verifier = "verifier_0"
            self._simulation_treasury = "treasury_0"

            if self._external_daemon is not None:
                # Shared daemon preserves single-source-of-truth event flow.
                self._daemon = self._external_daemon
            else:
                # Create daemon (don't auto-start - simulator controls timing)
                self._daemon = FAMDaemon(
                    data_dir=self._data_dir,
                    heartbeat_interval_sec=60.0,  # Slow heartbeat
                    auto_start=False,
                )

            logger.info("[FAM-BRIDGE] Initialized with InMemoryAgentMarket + FAMDaemon")

        except ImportError as e:
            logger.error(f"[FAM-BRIDGE] Failed to import FAM modules: {e}")
            raise

    def get_daemon(self) -> Any:
        """Get FAMDaemon instance."""
        return self._daemon

    def get_market(self) -> Any:
        """Get InMemoryAgentMarket instance."""
        return self._market

    # =========================================================================
    # Foundup Operations (wraps InMemoryAgentMarket)
    # =========================================================================

    def create_foundup(
        self,
        name: str,
        owner_id: str,
        token_symbol: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """Create a new FoundUp.

        Args:
            name: FoundUp name
            owner_id: Owner agent ID
            token_symbol: Token symbol (e.g., "PROJ")
            metadata: Optional metadata dict

        Returns:
            (success, message, foundup_id or None)
        """
        try:
            from modules.foundups.agent_market.src.models import Foundup

            # Generate ID (InMemoryAgentMarket expects pre-filled ID)
            foundup_id = self._id_gen.next_id("fup")
            requested_symbol = (token_symbol or "").upper().strip()
            if not requested_symbol:
                requested_symbol = "FUP"
            symbol_attempt = requested_symbol
            result = None
            max_symbol_attempts = 25

            # Simulation hardening: auto-resolve symbol collisions deterministically so
            # founder throughput is not artificially capped by a tiny static symbol list.
            for attempt in range(max_symbol_attempts):
                foundup = Foundup(
                    foundup_id=foundup_id,
                    name=name,
                    owner_id=owner_id,
                    token_symbol=symbol_attempt,
                    immutable_metadata=metadata or {},
                    mutable_metadata={},
                )
                try:
                    result = self._market.create_foundup(foundup)
                    break
                except Exception as exc:
                    msg = str(exc).lower()
                    is_collision = "token_symbol" in msg and "already exists" in msg
                    if not is_collision or attempt == max_symbol_attempts - 1:
                        raise
                    symbol_attempt = f"{requested_symbol}{attempt + 1:02d}"
            assert result is not None

            # Emit event via daemon
            self._daemon.emit(
                event_type="foundup_created",
                payload={
                    "name": result.name,
                    "token_symbol": result.token_symbol,
                    "symbol_auto_resolved": result.token_symbol != requested_symbol,
                },
                actor_id=owner_id,
                foundup_id=result.foundup_id,
            )

            return (True, "ok", result.foundup_id)

        except Exception as e:
            logger.error(f"[FAM-BRIDGE] create_foundup failed: {e}")
            return (False, str(e), None)

    def get_foundup(self, foundup_id: str) -> Optional[Any]:
        """Get FoundUp by ID."""
        try:
            return self._market.get_foundup(foundup_id)
        except Exception:
            return None

    def list_foundups(self) -> List[Any]:
        """List all FoundUps."""
        # InMemoryAgentMarket stores foundups in .foundups dict
        return list(self._market.foundups.values())

    # =========================================================================
    # Task Operations (wraps InMemoryAgentMarket)
    # =========================================================================

    def create_task(
        self,
        foundup_id: str,
        title: str,
        description: str,
        reward_amount: int,
        creator_id: str,
    ) -> Tuple[bool, str, Optional[str]]:
        """Create a task for a FoundUp."""
        try:
            from modules.foundups.agent_market.src.models import Task

            # Generate ID (InMemoryAgentMarket expects pre-filled ID)
            task_id = self._id_gen.next_id("task")

            task = Task(
                task_id=task_id,
                foundup_id=foundup_id,
                title=title,
                description=description,
                acceptance_criteria=["Complete the task"],
                reward_amount=reward_amount,
                creator_id=creator_id,
            )

            result = self._market.create_task(task)

            # Emit event
            self._daemon.emit(
                event_type="task_state_changed",
                payload={
                    "task_id": result.task_id,
                    "old_status": None,
                    "new_status": "open",
                },
                actor_id=creator_id,
                foundup_id=foundup_id,
                task_id=result.task_id,
            )

            return (True, "ok", result.task_id)

        except Exception as e:
            logger.error(f"[FAM-BRIDGE] create_task failed: {e}")
            return (False, str(e), None)

    def claim_task(self, task_id: str, agent_id: str) -> Tuple[bool, str]:
        """Claim a task."""
        try:
            old_task = self._market.get_task(task_id)
            task = self._market.claim_task(task_id, agent_id)

            self._daemon.emit(
                event_type="task_state_changed",
                payload={
                    "task_id": task_id,
                    "old_status": old_task.status.value,
                    "new_status": task.status.value,
                    "claimer_id": agent_id,
                },
                actor_id=agent_id,
                foundup_id=task.foundup_id,
                task_id=task_id,
            )

            return (True, "ok")

        except Exception as e:
            return (False, str(e))

    def submit_proof(
        self,
        task_id: str,
        submitter_id: str,
        artifact_uri: Optional[str] = None,
        artifact_hash: Optional[str] = None,
        notes: str = "",
    ) -> Tuple[bool, str, Optional[str]]:
        """Submit proof for a claimed task."""
        try:
            from modules.foundups.agent_market.src.models import Proof

            old_task = self._market.get_task(task_id)
            proof_id = self._id_gen.next_id("proof")

            proof = Proof(
                proof_id=proof_id,
                task_id=task_id,
                submitter_id=submitter_id,
                artifact_uri=artifact_uri or f"sim://proof/{task_id}",
                artifact_hash=artifact_hash or self._id_gen.next_id("hash"),
                notes=notes or f"Simulated proof for {task_id}",
            )
            task = self._market.submit_proof(proof)

            self._daemon.emit(
                event_type="proof_submitted",
                payload={
                    "task_id": task_id,
                    "proof_id": proof_id,
                    "artifact_uri": proof.artifact_uri,
                },
                actor_id=submitter_id,
                foundup_id=task.foundup_id,
                task_id=task_id,
            )
            self._daemon.emit(
                event_type="task_state_changed",
                payload={
                    "task_id": task_id,
                    "old_status": old_task.status.value,
                    "new_status": task.status.value,
                    "proof_id": proof_id,
                },
                actor_id=submitter_id,
                foundup_id=task.foundup_id,
                task_id=task_id,
            )
            return (True, "ok", proof_id)
        except Exception as e:
            return (False, str(e), None)

    def verify_task(
        self,
        task_id: str,
        verifier_id: str = "verifier_0",
        reason: str = "Simulator auto-verification",
    ) -> Tuple[bool, str, Optional[str]]:
        """Verify submitted proof for a task."""
        try:
            from modules.foundups.agent_market.src.models import Verification
            from modules.foundups.agent_market.src.authorization import CallerAuthorization

            old_task = self._market.get_task(task_id)
            verification_id = self._id_gen.next_id("verif")
            verification = Verification(
                verification_id=verification_id,
                task_id=task_id,
                verifier_id=verifier_id,
                approved=True,
                reason=reason,
            )
            authorization = CallerAuthorization(
                self._simulation_verifier,
                frozenset({(old_task.foundup_id, "verifier")}),
            )
            task = self._market.verify_proof(task_id, verification, authorization=authorization)

            self._daemon.emit(
                event_type="verification_recorded",
                payload={
                    "task_id": task_id,
                    "verification_id": verification_id,
                    "approved": True,
                    "reason": reason,
                },
                actor_id=verifier_id,
                foundup_id=task.foundup_id,
                task_id=task_id,
            )
            self._daemon.emit(
                event_type="task_state_changed",
                payload={
                    "task_id": task_id,
                    "old_status": old_task.status.value,
                    "new_status": task.status.value,
                    "verification_id": verification_id,
                },
                actor_id=verifier_id,
                foundup_id=task.foundup_id,
                task_id=task_id,
            )
            return (True, "ok", verification_id)
        except Exception as e:
            return (False, str(e), None)

    def trigger_payout(
        self,
        task_id: str,
        treasury_actor_id: str = "treasury_0",
    ) -> Tuple[bool, str, Optional[str]]:
        """Trigger payout for a verified task."""
        try:
            from modules.foundups.agent_market.src.authorization import CallerAuthorization

            old_task = self._market.get_task(task_id)
            authorization = CallerAuthorization(
                self._simulation_treasury,
                frozenset({(old_task.foundup_id, "treasury")}),
            )
            payout = self._market.trigger_payout(
                task_id, actor_id=treasury_actor_id, authorization=authorization,
            )
            task = self._market.get_task(task_id)

            self._daemon.emit(
                event_type="payout_triggered",
                payload={
                    "task_id": task_id,
                    "payout_id": payout.payout_id,
                    "amount": payout.amount,
                    "recipient_id": payout.recipient_id,
                    "reference": payout.reference,
                },
                actor_id=treasury_actor_id,
                foundup_id=task.foundup_id,
                task_id=task_id,
            )
            self._daemon.emit(
                event_type="task_state_changed",
                payload={
                    "task_id": task_id,
                    "old_status": old_task.status.value,
                    "new_status": task.status.value,
                    "payout_id": payout.payout_id,
                },
                actor_id=treasury_actor_id,
                foundup_id=task.foundup_id,
                task_id=task_id,
            )
            return (True, "ok", payout.payout_id)
        except Exception as e:
            return (False, str(e), None)

    def publish_milestone(
        self,
        task_id: str,
        distributor_id: str = "distribution_0",
        channel: str = "moltbook",
        cabr_threshold: float = 0.0,
    ) -> Tuple[bool, str, Optional[str]]:
        """Publish verified milestone for a task."""
        try:
            distribution = self._market.publish_verified_milestone(
                task_id=task_id,
                actor_id=distributor_id,
                channel=channel,
                cabr_threshold=cabr_threshold,
            )
            task = self._market.get_task(task_id)

            self._daemon.emit(
                event_type="milestone_published",
                payload={
                    "task_id": task_id,
                    "distribution_id": distribution.distribution_id,
                    "channel": distribution.channel,
                    "dedupe_key": distribution.dedupe_key,
                },
                actor_id=distributor_id,
                foundup_id=task.foundup_id,
                task_id=task_id,
            )
            return (True, "ok", distribution.distribution_id)
        except Exception as e:
            return (False, str(e), None)

    def get_task(self, task_id: str) -> Optional[Any]:
        """Get task by ID."""
        try:
            return self._market.get_task(task_id)
        except Exception:
            return None

    def get_tasks_by_status(self, status: str, foundup_id: Optional[str] = None) -> List[Any]:
        """Get tasks by status, optionally filtered by foundup."""
        from modules.foundups.agent_market.src.models import TaskStatus

        try:
            wanted = TaskStatus(status)
        except ValueError:
            return []

        tasks: List[Any] = []
        for task in self._market.tasks.values():
            if task.status == wanted:
                if foundup_id is None or task.foundup_id == foundup_id:
                    tasks.append(task)
        return tasks

    def get_open_tasks(self, foundup_id: Optional[str] = None) -> List[Any]:
        """Get open tasks, optionally filtered by foundup."""
        return self.get_tasks_by_status("open", foundup_id)

    def get_claimed_tasks(self, foundup_id: Optional[str] = None) -> List[Any]:
        """Get claimed tasks, optionally filtered by foundup."""
        return self.get_tasks_by_status("claimed", foundup_id)

    def get_submitted_tasks(self, foundup_id: Optional[str] = None) -> List[Any]:
        """Get submitted tasks, optionally filtered by foundup."""
        return self.get_tasks_by_status("submitted", foundup_id)

    def get_verified_tasks(self, foundup_id: Optional[str] = None) -> List[Any]:
        """Get verified tasks, optionally filtered by foundup."""
        return self.get_tasks_by_status("verified", foundup_id)

    def get_paid_tasks_pending_publication(self, foundup_id: Optional[str] = None) -> List[Any]:
        """Get paid tasks that have not been published yet."""
        tasks = self.get_tasks_by_status("paid", foundup_id)
        return [task for task in tasks if self._market.get_distribution(task.task_id) is None]

    # =========================================================================
    # MVP Offering Operations (F_0 investor program)
    # =========================================================================

    def accrue_investor_terms(
        self,
        investor_id: str,
        terms: int = 1,
        term_ups: int = 200,
        max_terms: int = 5,
    ) -> Tuple[bool, str, Optional[Dict[str, int]]]:
        """Accrue investor subscription terms in the F_0 program."""
        try:
            result = self._market.accrue_investor_terms(
                investor_id=investor_id,
                terms=terms,
                term_ups=term_ups,
                max_terms=max_terms,
            )
            self._daemon.emit(
                event_type="mvp_subscription_accrued",
                payload={
                    "investor_id": investor_id,
                    "source_foundup_id": "F_0",
                    "terms": result.get("terms", 0),
                    "available_ups": result.get("available_ups", 0),
                    "added_terms": result.get("added_terms", 0),
                    "added_ups": result.get("added_ups", 0),
                },
                actor_id=investor_id,
                foundup_id="F_0",
            )
            return (True, "ok", result)
        except Exception as e:
            return (False, str(e), None)

    def place_mvp_bid(
        self,
        foundup_id: str,
        investor_id: str,
        bid_ups: int,
    ) -> Tuple[bool, str, Optional[str]]:
        """Place a MVP pre-launch bid for a target FoundUp."""
        try:
            bid_id = self._market.place_mvp_bid(
                foundup_id=foundup_id,
                investor_id=investor_id,
                bid_ups=bid_ups,
            )
            investor_state = self._market.get_investor_subscription_state(investor_id)
            self._daemon.emit(
                event_type="mvp_bid_submitted",
                payload={
                    "bid_id": bid_id,
                    "investor_id": investor_id,
                    "source_foundup_id": "F_0",
                    "bid_ups": bid_ups,
                    "remaining_ups": investor_state.get("available_ups", 0),
                },
                actor_id=investor_id,
                foundup_id=foundup_id,
            )
            return (True, "ok", bid_id)
        except Exception as e:
            return (False, str(e), None)

    def get_mvp_bids(self, foundup_id: str) -> List[Dict[str, object]]:
        """List outstanding MVP bids for a FoundUp."""
        try:
            return self._market.get_mvp_bids(foundup_id)
        except Exception:
            return []

    def resolve_mvp_offering(
        self,
        foundup_id: str,
        actor_id: str = "treasury_0",
        token_amount: int = 1_000,
        top_n: int = 1,
    ) -> Tuple[bool, str, Optional[List[Dict[str, object]]]]:
        """Resolve MVP offering and inject winning bids into FoundUp treasury."""
        try:
            allocations = self._market.resolve_mvp_offering(
                foundup_id=foundup_id,
                actor_id=actor_id,
                token_amount=token_amount,
                top_n=top_n,
            )
            total_injection_ups = int(sum(int(a.get("bid_ups", 0)) for a in allocations))
            self._daemon.emit(
                event_type="mvp_offering_resolved",
                payload={
                    "foundup_id": foundup_id,
                    "source_foundup_id": "F_0",
                    "winner_count": len(allocations),
                    "token_amount": token_amount,
                    "total_injection_ups": total_injection_ups,
                    "allocations": allocations,
                },
                actor_id=actor_id,
                foundup_id=foundup_id,
            )
            return (True, "ok", allocations)
        except Exception as e:
            return (False, str(e), None)

    def get_investor_subscription_state(self, investor_id: str) -> Dict[str, int]:
        """Get investor subscription/hoard balances."""
        try:
            return self._market.get_investor_subscription_state(investor_id)
        except Exception:
            return {"terms": 0, "available_ups": 0, "spent_ups": 0}

    # =========================================================================
    # Agent-ORCH Handshake Protocol (WSP 15 MPS Gatekeeping)
    # =========================================================================

    def request_work_handshake(
        self,
        agent_id: str,
        task_id: str,
        agent_reputation: float = 0.5,
        agent_skills: Optional[List[str]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Agent requests work approval from ORCH.

        WSP 15 MPS (Modified Priority Score) gates agent work assignments.
        Agents below threshold are routed to PROMOTER track instead.

        Args:
            agent_id: Requesting agent ID
            task_id: Target task ID
            agent_reputation: Agent's current reputation (0-1)
            agent_skills: Agent's skill list

        Returns:
            (decision, details) where decision is:
            - "APPROVED": Agent can claim task
            - "REJECTED": Agent cannot claim task
            - "PROMOTER_TRACK": Agent routed to promoter duties
        """
        # Calculate MPS score
        mps_score = self._calculate_mps(agent_reputation, agent_skills or [])

        task = self.get_task(task_id)
        if not task:
            return ("REJECTED", {"reason": "task_not_found", "mps_score": mps_score})

        foundup_id = task.foundup_id
        foundup_idx = self._extract_foundup_index(foundup_id)

        # Emit work_request event
        self._daemon.emit(
            event_type="work_request",
            payload={
                "task_id": task_id,
                "mps_score": mps_score,
                "skills": agent_skills or [],
            },
            actor_id=agent_id,
            foundup_id=foundup_id,
            task_id=task_id,
        )

        # WSP 15: MPS threshold gatekeeping (phi = 0.618)
        MPS_THRESHOLD = 0.618

        if mps_score >= MPS_THRESHOLD:
            # Approved - agent can claim
            self._daemon.emit(
                event_type="work_approved",
                payload={
                    "task_id": task_id,
                    "mps_score": round(mps_score, 3),
                },
                actor_id=agent_id,
                foundup_id=foundup_id,
                task_id=task_id,
            )

            self._daemon.emit(
                event_type="handshake_complete",
                payload={
                    "task_id": task_id,
                    "decision": "APPROVED",
                },
                actor_id=agent_id,
                foundup_id=foundup_id,
                task_id=task_id,
            )

            return ("APPROVED", {
                "mps_score": mps_score,
                "task_id": task_id,
                "foundup_idx": foundup_idx,
            })

        elif mps_score >= 0.4:
            # Promoter track - not ready for core work but can promote
            self._daemon.emit(
                event_type="promoter_assigned",
                payload={
                    "task_id": task_id,
                    "mps_score": round(mps_score, 3),
                    "reason": "mps_below_threshold",
                },
                actor_id=agent_id,
                foundup_id=foundup_id,
            )

            return ("PROMOTER_TRACK", {
                "mps_score": mps_score,
                "reason": "Build reputation through promotion",
            })

        else:
            # Rejected - MPS too low
            self._daemon.emit(
                event_type="work_rejected",
                payload={
                    "task_id": task_id,
                    "mps_score": round(mps_score, 3),
                    "reason": "mps_too_low",
                },
                actor_id=agent_id,
                foundup_id=foundup_id,
                task_id=task_id,
            )

            return ("REJECTED", {
                "mps_score": mps_score,
                "reason": "MPS below minimum threshold",
            })

    def emit_agent_earning(
        self,
        agent_id: str,
        foundup_id: str,
        amount: int,
        task_id: Optional[str] = None,
    ) -> None:
        """Emit agent earning event for ticker display.

        Args:
            agent_id: Agent that earned
            foundup_id: FoundUp context
            amount: Amount earned
            task_id: Optional task ID
        """
        foundup_idx = self._extract_foundup_index(foundup_id)

        self._daemon.emit(
            event_type="agent_earned",
            payload={
                "amount": amount,
                "foundup_idx": foundup_idx,
                "task_id": task_id,
            },
            actor_id=agent_id,
            foundup_id=foundup_id,
            task_id=task_id,
        )

    def emit_agent_joins(
        self,
        agent_id: str,
        agent_type: str,
        foundup_id: str = "F_0",
        public_key: Optional[str] = None,
        rank: int = 1,
    ) -> None:
        """Emit agent joining event - 01(02) state.

        Args:
            agent_id: Unique agent identifier
            agent_type: founder | user
            foundup_id: FoundUp context (F_0 for ecosystem-level)
            public_key: Wallet address (placeholder if not provided)
            rank: Initial rank (1=Apprentice)
        """
        foundup_idx = self._extract_foundup_index(foundup_id)
        wallet = public_key or f"0x{agent_id.replace('_', '')[:16]}"
        self._daemon.emit(
            event_type="agent_joins",
            payload={
                "agent_type": agent_type,
                "public_key": wallet,
                "rank": rank,
                "state": "01(02)",  # Dormant until awakened
                "foundup_idx": foundup_idx,
            },
            actor_id=agent_id,
            foundup_id=foundup_id,
        )

    def emit_agent_idle(
        self,
        agent_id: str,
        foundup_id: str,
        inactive_ticks: int = 0,
        current_tick: int = 0,
    ) -> None:
        """Emit agent IDLE event - 01/02 decayed state.

        Args:
            agent_id: Agent identifier
            foundup_id: FoundUp context
            inactive_ticks: Ticks since last activity
            current_tick: Current simulation tick
        """
        self._daemon.emit(
            event_type="agent_idle",
            payload={
                "inactive_ticks": inactive_ticks,
                "current_tick": current_tick,
                "state": "01/02",  # Decayed - awaiting ORCH
            },
            actor_id=agent_id,
            foundup_id=foundup_id,
        )

    def emit_agent_awakened(
        self,
        agent_id: str,
        coherence: float = 0.72,
        foundup_id: str = "F_0",
    ) -> None:
        """Emit agent awakened event - 0102 zen state.

        Args:
            agent_id: Agent identifier
            coherence: Coherence score (>= 0.618 for zen)
            foundup_id: FoundUp context
        """
        self._daemon.emit(
            event_type="agent_awakened",
            payload={
                "coherence": coherence,
                "state": "0102",  # Zen state - active
            },
            actor_id=agent_id,
            foundup_id=foundup_id,
        )

    def emit_agent_ranked(
        self,
        agent_id: str,
        old_rank: int,
        new_rank: int,
        foundup_id: str = "F_0",
    ) -> None:
        """Emit agent rank progression event.

        Args:
            agent_id: Agent identifier
            old_rank: Previous rank (1-7)
            new_rank: New rank (1-7)
            foundup_id: FoundUp context
        """
        rank_titles = {
            1: "Apprentice", 2: "Builder", 3: "Contributor",
            4: "Validator", 5: "Orchestrator", 6: "Architect", 7: "Principal"
        }
        self._daemon.emit(
            event_type="agent_ranked",
            payload={
                "old_rank": old_rank,
                "new_rank": new_rank,
                "old_title": rank_titles.get(old_rank, "Unknown"),
                "new_title": rank_titles.get(new_rank, "Unknown"),
            },
            actor_id=agent_id,
            foundup_id=foundup_id,
        )

    def emit_agent_leaves(
        self,
        agent_id: str,
        wallet_balance: float,
        public_key: Optional[str] = None,
        foundup_id: str = "F_0",
    ) -> None:
        """Emit agent leaving event - logs off with wallet.

        Args:
            agent_id: Agent identifier
            wallet_balance: Final F_i balance
            public_key: Wallet address
            foundup_id: FoundUp context
        """
        wallet = public_key or f"0x{agent_id.replace('_', '')[:16]}"
        self._daemon.emit(
            event_type="agent_leaves",
            payload={
                "public_key": wallet,
                "wallet_balance": wallet_balance,
            },
            actor_id=agent_id,
            foundup_id=foundup_id,
        )

    def emit_orch_handoff(
        self,
        agent_id: str,
        foundup_id: str,
        module: str,
    ) -> None:
        """Emit ORCH handoff event (assigning work to builder)."""
        self._daemon.emit(
            event_type="orch_handoff",
            payload={"module": module},
            actor_id=agent_id,
            foundup_id=foundup_id,
        )

    def emit_module_build(
        self,
        agent_id: str,
        foundup_id: str,
        module: str,
    ) -> None:
        """Emit FAM module building event."""
        module_events = {
            "REGISTRY": "build_registry",
            "TASK_PIPELINE": "build_task_pipeline",
            "TOKEN_ECON": "build_token_econ",
            "PERSISTENCE": "build_persistence",
            "EVENTS": "build_events",
            "GOVERNANCE": "build_governance",
            "API": "build_api",
        }
        event_type = module_events.get(module.upper(), f"build_{module.lower()}")
        self._daemon.emit(
            event_type=event_type,
            payload={"module": module},
            actor_id=agent_id,
            foundup_id=foundup_id,
        )

    def emit_fi_ups_exchange(
        self,
        foundup_id: str,
        foundup_idx: int,
        fi_amount: int,
        ups_amount: int,
    ) -> None:
        """Emit F_i ↔ UPS token exchange event."""
        self._daemon.emit(
            event_type="fi_ups_exchange",
            payload={
                "foundup_idx": foundup_idx,
                "fi_amount": fi_amount,
                "ups_amount": ups_amount,
            },
            actor_id="dex",
            foundup_id=foundup_id,
        )

    def _calculate_mps(
        self,
        reputation: float,
        skills: List[str],
    ) -> float:
        """Calculate Modified Priority Score (WSP 15).

        MPS = (reputation * 0.5) + (skill_match * 0.3) + (availability * 0.2)

        Args:
            reputation: Agent reputation (0-1)
            skills: Agent skills list

        Returns:
            MPS score (0-1)
        """
        # Reputation component (50%)
        rep_component = reputation * 0.5

        # Skill component (30%) - more skills = higher score
        skill_count = len(skills)
        skill_component = min(1.0, skill_count / 5) * 0.3

        # Availability component (20%) - assume available
        avail_component = 0.9 * 0.2

        return rep_component + skill_component + avail_component

    def _extract_foundup_index(self, foundup_id: str) -> int:
        """Extract numeric index from foundup_id (e.g., 'fup_0001' -> 1)."""
        import re
        match = re.search(r'(\d+)', foundup_id)
        return int(match.group(1)) if match else 0

    # =========================================================================
    # Reset (for test isolation)
    # =========================================================================

    def reset(self) -> None:
        """Reset all state for test isolation."""
        if hasattr(self._market, "reset"):
            self._market.reset()
        logger.info("[FAM-BRIDGE] State reset")
