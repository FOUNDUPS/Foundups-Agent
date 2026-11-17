"""FoundUps Agent Swarm Simulator.

MECHANICAL MODEL:

TYPE (set at entry - simple):
  2 (Du) = You STARTED the project (Founder)
  1 (Dao) = You JOINED the project (Team Member)
  0 (Un) = You USE the product (Customer)

ACTIVITY (dynamic - based on WORK done by your digital twin):
  2 = Doing the most work (active)
  1 = Regular contribution
  0 = Agent stopped working → DEGRADED (project abandoned by you)

Key Insight: ENGAGEMENT determines reward, NOT title.
- Inactive Founder "20": 3.20% (accesses all pools, but 4% of each)
- Active Team Member "12": 60.80% (0+1 pools at 80% each)
- Active team member earns 19x more than inactive founder!

DEGRADATION (mechanical):
- No agent work for X epochs → Activity drops automatically
- Founder who abandons earns almost nothing

ELEVATION (governance):
- Digital twin observes work patterns
- Suggests: "Agent X should be upgraded to Founder"
- Current founder(s) approve → Type upgrade happens
- Both active founders share top tier rewards

SIMULATOR TESTS:
1. Activity degradation curve
2. Elevation threshold mechanics
3. Multi-founder reward splitting
4. Abandoned project scenarios
5. Pool math verification

Sources:
- MetaGPT: https://github.com/FoundationAgents/MetaGPT (swarm patterns)
- ChatDev: https://github.com/OpenBMB/ChatDev (team coordination)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from ..economics.pool_distribution import (
    ParticipantType,
    ActivityLevel,
    Participant,
    PoolDistributor,
)
from ..economics.token_economics import (
    TokenEconomicsEngine,
    AgentExecutionWallet,
    HumanUPSAccount,
)

logger = logging.getLogger(__name__)


class AgentSpecialization(Enum):
    """Agent specializations in the worker swarm (0102).

    NO HIERARCHY - these are equal team members with different skills.
    The swarm coordinates without a "boss" - all agents work together.
    """

    # Work specializations (all equal, no hierarchy)
    STRATEGY = "strategy"      # Vision, planning, roadmap
    ARCHITECTURE = "architecture"  # System design, structure
    CODE = "code"              # Implementation, features
    QUALITY = "quality"        # Testing, validation
    DESIGN = "design"          # UX, visual, branding
    GROWTH = "growth"          # Marketing, community
    OPS = "ops"                # DevOps, infrastructure
    DATA = "data"              # Analytics, ML, insights
    SUPPORT = "support"        # Customer help, docs


# NOTE: Agent specialization does NOT determine pool access!
# Pool access (Type 0/1/2) is for HUMANS (012), not agents (0102).
# Agents earn FoundUp Tokens for their human owners.
# The HUMAN's type determines which pools they access.

# Agent specialization affects WHAT WORK they do, not token distribution.
# All agents are equal workers earning F_i for their human owner.


@dataclass
class TaskCompletion:
    """Result of an agent completing a task."""

    agent_id: str
    specialization: AgentSpecialization
    task_id: str
    task_type: str  # e.g., "code_commit", "review", "design", "test"

    # Work metrics (determines human's activity score via CABR)
    lines_changed: int = 0
    files_touched: int = 0
    review_comments: int = 0
    tests_passed: int = 0
    quality_score: float = 0.0  # 0-1 scale

    # Token economics
    ups_cost: float = 0.0  # UPS spent on execution
    fi_reward: float = 0.0  # FoundUp Tokens earned for human owner


@dataclass
class ElevationRecommendation:
    """Digital twin's recommendation to elevate a participant."""

    participant_id: str
    current_type: ParticipantType
    recommended_type: ParticipantType
    reason: str
    work_score: float  # Total work contribution


@dataclass
class SwarmFoundUp:
    """A FoundUp with agent swarm (0102) as digital twins.

    MECHANICAL MODEL:
    - Type (0/1/2) = Set at entry (Customer/Team/Founder)
    - Activity (0/1/2) = Dynamic, based on WORK done by digital twin
    - Degradation = No work → Activity drops automatically
    - Elevation = Digital twin recommends → Founder approves → Type upgrade

    The "human" in the system is represented by their digital twin (0102).
    Human provides feedback; digital twin acts in the system.
    """

    foundup_id: str
    name: str
    domain: str  # e.g., "waste" for GotJunk

    # Participants (represented by their digital twins)
    human_participants: Dict[str, HumanUPSAccount] = field(default_factory=dict)
    human_types: Dict[str, ParticipantType] = field(default_factory=dict)

    # Agent swarm (0102 digital twins)
    agent_wallets: Dict[str, AgentExecutionWallet] = field(default_factory=dict)
    agent_specializations: Dict[str, AgentSpecialization] = field(default_factory=dict)

    # Pool distribution
    pool_distributor: PoolDistributor = field(default_factory=PoolDistributor)

    # Task history
    completed_tasks: List[TaskCompletion] = field(default_factory=list)

    # Epoch tracking
    current_epoch: int = 0
    epoch_ups_rewards: float = 1000.0

    # === DEGRADATION MECHANICS ===
    # Track work per participant for degradation/elevation
    work_this_epoch: Dict[str, float] = field(default_factory=dict)
    total_work: Dict[str, float] = field(default_factory=dict)
    epochs_since_work: Dict[str, int] = field(default_factory=dict)

    # Degradation config (tunable via simulator)
    degradation_threshold: int = 3  # Epochs without work before degradation
    elevation_work_threshold: float = 100.0  # Total work to recommend elevation

    # Pending elevation recommendations
    elevation_queue: List[ElevationRecommendation] = field(default_factory=list)

    def register_human(
        self,
        human_id: str,
        participant_type: ParticipantType,
        initial_activity: ActivityLevel = ActivityLevel.UN,
        initial_ups: float = 100.0,
    ) -> HumanUPSAccount:
        """Register a human participant (012) in this FoundUp.

        Args:
            human_id: Unique identifier
            participant_type: Du(2)=Founder, Dao(1)=Partner, Un(0)=Customer
            initial_activity: Starting activity level (updates based on engagement)
            initial_ups: Starting UPS balance
        """
        account = HumanUPSAccount(human_id=human_id, ups_balance=initial_ups)
        self.human_participants[human_id] = account
        self.human_types[human_id] = participant_type

        # Register in pool distributor (HUMANS get pool rewards)
        self.pool_distributor.register_participant(
            participant_id=human_id,
            p_type=participant_type,
            activity=initial_activity,
        )

        logger.info(
            f"[{self.foundup_id}] Registered human {human_id} "
            f"(type={participant_type.name}, activity={initial_activity.name})"
        )
        return account

    def register_agent(
        self,
        agent_id: str,
        specialization: AgentSpecialization,
        owner_id: str,
        initial_budget: float = 50.0,
    ) -> AgentExecutionWallet:
        """Register an agent (0102) in the swarm.

        Agents are equal team members - no hierarchy.
        They earn FoundUp Tokens for their human owner.
        """
        if owner_id not in self.human_participants:
            raise ValueError(f"Owner {owner_id} not registered")

        # Prepare the allocation before publishing the agent registration.
        wallet = AgentExecutionWallet(agent_id=agent_id, allocator_id=owner_id)
        owner = self.human_participants[owner_id]
        owner.allocate_to_agent(initial_budget, wallet)
        self.agent_wallets[agent_id] = wallet
        self.agent_specializations[agent_id] = specialization

        # NOTE: Agents do NOT participate in pools - only HUMANS do!
        # The agent earns F_i for the human owner.

        logger.info(
            f"[{self.foundup_id}] Registered {specialization.value} agent {agent_id} "
            f"(owner={owner_id})"
        )
        return wallet

    def agent_completes_task(
        self,
        agent_id: str,
        task: TaskCompletion,
    ) -> Tuple[bool, float]:
        """Agent (digital twin) completes a task.

        This updates:
        1. Owner's activity level (for pool distribution)
        2. Owner's work counters (for degradation/elevation)
        3. Owner's F_i balance (earned tokens)

        Returns:
            (success, fi_earned) tuple
        """
        wallet = self.agent_wallets.get(agent_id)
        if not wallet:
            return (False, 0.0)

        # Agent spends UPS on task execution
        success, fee = wallet.spend(task.ups_cost, f"task:{task.task_type}")
        if not success:
            logger.warning(f"[{self.foundup_id}] Agent {agent_id} failed to spend UPS")
            return (False, 0.0)

        owner_id = wallet.allocator_id

        # Calculate work score from task metrics
        work_score = self._calculate_work_score(task)

        # Track work for degradation/elevation
        self.work_this_epoch[owner_id] = self.work_this_epoch.get(owner_id, 0.0) + work_score
        self.total_work[owner_id] = self.total_work.get(owner_id, 0.0) + work_score

        # Calculate activity level from work quality
        activity_level = self._calculate_activity_level(task)

        # Update owner's activity in pool distributor
        self.pool_distributor.update_activity(owner_id, activity_level)

        # Record task completion
        task.fi_reward = self._calculate_fi_reward(task)
        self.completed_tasks.append(task)

        # Transfer F_i to human owner
        owner = self.human_participants.get(owner_id)
        if owner and task.fi_reward > 0:
            owner.receive_fi(self.foundup_id, task.fi_reward)

        logger.info(
            f"[{self.foundup_id}] {agent_id} completed {task.task_type} "
            f"(owner {owner_id} activity={activity_level.name}, F_i={task.fi_reward:.2f})"
        )

        return (True, task.fi_reward)

    def _calculate_work_score(self, task: TaskCompletion) -> float:
        """Calculate work score for degradation/elevation tracking.

        This is a simple metric combining quantity and quality of work.
        Used for:
        - Resetting degradation counter (any work > 0)
        - Elevation threshold (accumulated total work)
        """
        # Base score from contribution size
        size_score = task.lines_changed * 0.1 + task.files_touched * 1.0

        # Quality multiplier
        quality_mult = 0.5 + task.quality_score

        # Test bonus
        test_bonus = task.tests_passed * 0.5

        return (size_score * quality_mult) + test_bonus

    def _calculate_activity_level(self, task: TaskCompletion) -> ActivityLevel:
        """Calculate activity level from task metrics (CABR-style).

        Activity determines share within pools:
        - du (2): 80% - high quality, substantial contribution
        - dao (1): 16% - regular contribution
        - un (0): 4% - minimal contribution
        """
        # Simple scoring based on task metrics
        score = 0.0

        # Code contributions
        if task.lines_changed > 100:
            score += 0.3
        elif task.lines_changed > 20:
            score += 0.15

        # Quality
        score += task.quality_score * 0.4

        # Test coverage
        if task.tests_passed > 10:
            score += 0.2
        elif task.tests_passed > 3:
            score += 0.1

        # Review activity
        if task.review_comments > 5:
            score += 0.1

        # Map score to activity level
        if score >= 0.6:
            return ActivityLevel.DU  # 80% of pool
        elif score >= 0.3:
            return ActivityLevel.DAO  # 16% of pool
        else:
            return ActivityLevel.UN  # 4% of pool

    def _calculate_fi_reward(self, task: TaskCompletion) -> float:
        """Calculate FoundUp Token reward for verified work.

        Tokens are scarce (21M cap) so rewards are conservative.
        """
        base_reward = 10.0  # Base tokens per task

        # Scale by quality
        quality_multiplier = 0.5 + (task.quality_score * 1.5)

        # Scale by contribution size
        size_multiplier = min(2.0, 1.0 + (task.lines_changed / 200))

        return base_reward * quality_multiplier * size_multiplier

    def run_epoch(self) -> Dict:
        """Run an epoch of pool distribution.

        Includes DEGRADATION mechanics:
        - Participants who did no work this epoch → epochs_since_work++
        - If epochs_since_work >= threshold → Activity degrades

        Includes ELEVATION checks:
        - If participant's total_work >= threshold → recommend elevation
        """
        self.current_epoch += 1

        # === DEGRADATION CHECK ===
        degraded = []
        for pid in self.human_participants:
            work = self.work_this_epoch.get(pid, 0.0)

            if work > 0:
                # Did work this epoch - reset counter
                self.epochs_since_work[pid] = 0
            else:
                # No work - increment counter
                self.epochs_since_work[pid] = self.epochs_since_work.get(pid, 0) + 1

                # Check for degradation
                if self.epochs_since_work[pid] >= self.degradation_threshold:
                    current = self.pool_distributor.participants[pid].activity_level
                    if current.value > 0:  # Can still degrade
                        new_level = ActivityLevel(current.value - 1)
                        self.pool_distributor.update_activity(pid, new_level)
                        degraded.append((pid, current.name, new_level.name))
                        logger.warning(
                            f"[{self.foundup_id}] DEGRADATION: {pid} "
                            f"{current.name} → {new_level.name} (no work for {self.epochs_since_work[pid]} epochs)"
                        )

        # === ELEVATION CHECK ===
        self._check_elevation_recommendations()

        # Reset work counters for next epoch
        self.work_this_epoch = {pid: 0.0 for pid in self.human_participants}

        # Calculate epoch rewards
        total_rewards = self.epoch_ups_rewards

        # Distribute via pool structure
        result = self.pool_distributor.distribute_epoch(
            epoch=self.current_epoch,
            total_ups_rewards=total_rewards,
            foundup_id=self.foundup_id,
        )

        logger.info(
            f"[{self.foundup_id}] Epoch {self.current_epoch}: "
            f"distributed {total_rewards:.2f} UPS to {len(result.participant_rewards)} participants"
        )

        return {
            "epoch": self.current_epoch,
            "total_distributed": sum(result.participant_rewards.values()),
            "drip_distributed": result.drip_distributed,
            "fund_accumulated": result.fund_accumulated,
            "participant_rewards": result.participant_rewards,
            "degraded": degraded,
            "elevation_queue": [e.participant_id for e in self.elevation_queue],
        }

    def _check_elevation_recommendations(self) -> None:
        """Digital twin checks if anyone should be elevated.

        Elevation logic:
        - Team member (Type 1) with high work → recommend to Founder (Type 2)
        - Customer (Type 0) with high work → recommend to Team member (Type 1)
        """
        for pid, total in self.total_work.items():
            if total < self.elevation_work_threshold:
                continue

            current_type = self.human_types.get(pid, ParticipantType.UN)

            # Already a founder - no elevation needed
            if current_type == ParticipantType.DU:
                continue

            # Check if already in queue
            if any(e.participant_id == pid for e in self.elevation_queue):
                continue

            # Recommend elevation
            if current_type == ParticipantType.DAO:
                recommended = ParticipantType.DU
                reason = f"Team member {pid} has done {total:.0f} work units - recommend Founder status"
            else:
                recommended = ParticipantType.DAO
                reason = f"Customer {pid} has done {total:.0f} work units - recommend Team member status"

            rec = ElevationRecommendation(
                participant_id=pid,
                current_type=current_type,
                recommended_type=recommended,
                reason=reason,
                work_score=total,
            )
            self.elevation_queue.append(rec)
            logger.info(f"[{self.foundup_id}] ELEVATION RECOMMENDED: {reason}")

    def approve_elevation(self, participant_id: str, approver_id: str) -> bool:
        """Founder approves an elevation recommendation.

        Args:
            participant_id: Who is being elevated
            approver_id: Founder approving (must be Type 2)

        Returns:
            True if elevation approved and applied
        """
        # Check approver is a founder
        approver_type = self.human_types.get(approver_id)
        if approver_type != ParticipantType.DU:
            logger.warning(f"[{self.foundup_id}] Elevation denied - {approver_id} is not a Founder")
            return False

        # Find the recommendation
        rec = None
        for r in self.elevation_queue:
            if r.participant_id == participant_id:
                rec = r
                break

        if not rec:
            logger.warning(f"[{self.foundup_id}] No elevation pending for {participant_id}")
            return False

        # Apply elevation
        old_type = self.human_types[participant_id]
        new_type = rec.recommended_type
        self.human_types[participant_id] = new_type

        # Update pool distributor
        participant = self.pool_distributor.participants[participant_id]
        self.pool_distributor.register_participant(
            participant_id=participant_id,
            p_type=new_type,
            activity=participant.activity_level,
        )

        # Remove from queue
        self.elevation_queue.remove(rec)

        logger.info(
            f"[{self.foundup_id}] ELEVATION APPROVED: {participant_id} "
            f"{old_type.name} → {new_type.name} (approved by {approver_id})"
        )
        return True

    def get_stats(self) -> Dict:
        """Get FoundUp statistics."""
        pool_stats = self.pool_distributor.get_distribution_stats()

        return {
            "foundup_id": self.foundup_id,
            "name": self.name,
            "domain": self.domain,
            "epoch": self.current_epoch,
            "humans": len(self.human_participants),
            "agents": len(self.agent_wallets),
            "tasks_completed": len(self.completed_tasks),
            "total_ups_distributed": pool_stats["total_ups_distributed"],
            "total_drip": pool_stats["total_drip_distributed"],
            "accumulated_fund": pool_stats["accumulated_fund"],
            "by_type": pool_stats["by_type"],
            "by_activity": pool_stats["by_activity"],
        }


def create_gotjunk_foundup() -> SwarmFoundUp:
    """Create a GotJunk FoundUp with agent swarm.

    GotJunk = Waste domain where:
    - People have difficulty getting rid of stuff (especially in Japan)
    - App lets you snap photo → AI prices → instant listing
    - Browse 50km radius for affordable used items

    Key model:
    - HUMANS (012) are founders/partners/customers with Type+Activity
    - AGENTS (0102) are equal swarm workers with specializations
    - Engagement determines reward, NOT title
    """
    foundup = SwarmFoundUp(
        foundup_id="gotjunk_001",
        name="GotJunk",
        domain="waste",
    )

    # Register HUMANS (012) with Type and Activity
    # Founder (Type 2) - initiated the project, starts with low activity
    foundup.register_human(
        "alice_founder",
        participant_type=ParticipantType.DU,  # Type 2 = Founder
        initial_activity=ActivityLevel.UN,     # Starts inactive (engagement will change this)
        initial_ups=1000.0,
    )

    # Partner (Type 1) - building the product
    foundup.register_human(
        "bob_partner",
        participant_type=ParticipantType.DAO,  # Type 1 = Partner
        initial_activity=ActivityLevel.UN,
        initial_ups=500.0,
    )

    # Customer (Type 0) - using the product
    foundup.register_human(
        "carol_customer",
        participant_type=ParticipantType.UN,  # Type 0 = Customer
        initial_activity=ActivityLevel.UN,
        initial_ups=100.0,
    )

    # Register agent swarm (0102) - NO HIERARCHY, just specializations
    # Alice's agents
    foundup.register_agent("strategy_agent", AgentSpecialization.STRATEGY, "alice_founder", 100.0)
    foundup.register_agent("arch_agent", AgentSpecialization.ARCHITECTURE, "alice_founder", 100.0)

    # Bob's agents
    foundup.register_agent("code_agent_1", AgentSpecialization.CODE, "bob_partner", 50.0)
    foundup.register_agent("code_agent_2", AgentSpecialization.CODE, "bob_partner", 50.0)
    foundup.register_agent("qa_agent", AgentSpecialization.QUALITY, "bob_partner", 30.0)
    foundup.register_agent("design_agent", AgentSpecialization.DESIGN, "bob_partner", 30.0)

    # Carol's agent (even customers can have agents helping them)
    foundup.register_agent("support_agent", AgentSpecialization.SUPPORT, "carol_customer", 20.0)

    logger.info(f"[GotJunk] Created FoundUp with {len(foundup.human_participants)} humans, {len(foundup.agent_wallets)} agents")

    return foundup


def run_simulation_epoch(foundup: SwarmFoundUp, num_tasks: int = 10) -> Dict:
    """Run one epoch of simulation with random task completions.

    Simulates agent work and updates human activity levels.
    """
    import random

    agents = list(foundup.agent_wallets.keys())
    task_types = ["code_commit", "review", "design", "test", "deploy"]

    for i in range(num_tasks):
        agent_id = random.choice(agents)
        spec = foundup.agent_specializations[agent_id]

        # Create task based on specialization
        task = TaskCompletion(
            agent_id=agent_id,
            specialization=spec,
            task_id=f"task_{foundup.current_epoch}_{i}",
            task_type=random.choice(task_types),
            lines_changed=random.randint(5, 200),
            files_touched=random.randint(1, 10),
            review_comments=random.randint(0, 10),
            tests_passed=random.randint(0, 20),
            quality_score=random.uniform(0.3, 1.0),
            ups_cost=random.uniform(1.0, 10.0),
        )

        foundup.agent_completes_task(agent_id, task)

    # Run epoch distribution
    epoch_result = foundup.run_epoch()

    return {
        "tasks_completed": num_tasks,
        "epoch_result": epoch_result,
        "stats": foundup.get_stats(),
    }
