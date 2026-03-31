"""Pool Distribution - WSP 26 Section 6.3-6.4 Token Pool Model.

Implements the Un/Dao/Du (0/1/2) participant pools + Network drip mechanism.

Pool Structure (100% total):
- Stakeholders: 80%
  - Un (0-Pool):  60% - 012 stakeholders (engagement-based, ACTIVE)
  - Dao (1-Pool): 16% - 0102 agents (3V work-based, ACTIVE)
  - Du (2-Pool):   4% - Protocol participants (CABR/PoB economics)
- Network: 20%
  - Network:      16% - Drip rewards (F_i → exchange → BTC → UPS)
  - Fund:          4% - Treasury fund (pAVS operations)

CRITICAL SEPARATION (012-confirmed 2026-02-14):
- Members (subscription) = Build UPs through WORK → Dao/Un pools ONLY
- BTC Stakers (anonymous) = Protocol participants → Du pool distributions

This separation prevents dilution:
- Unlimited subscribers → doesn't dilute Du pool
- Du pool capped at ~100-500 stakers for viable distributions
- Stakers provide LIQUIDITY (BTC commitment)

Earning Modes:
- Du (4%):  PASSIVE - Protocol participants receive epoch distributions
- Dao (16%): ACTIVE - 0102 agents earn per 3V task completion
- Un (60%):  ACTIVE - 012 stakeholders earn per engagement (FoundUpCube)

CANONICAL DU POOL PARTITION (2026-03-31):
  DuPool (4% of epoch distribution)
  ├── ActiveFounderPool (80% of Du = 3.2% of total)
  │   └── Active founders with degressive tier progression
  └── PassiveParticipationPool (20% of Du = 0.8% of total)
      ├── BTCStakerPool (weighted by deterministic formula)
      └── ChannelPartnerPool (equal split, max 21, genesis only)

Degressive Tier Model (WITHIN ActiveFounderPool):
- du (2): 80% of ActiveFounderPool - <10x allocation ratio (new participants)
- dao (1): 16% of ActiveFounderPool - 10x-100x allocation ratio
- un (0): 4% of ActiveFounderPool - >100x allocation ratio (lifetime floor)

The degressive model rewards early participants:
- Early stakers (low ratio) get the lion's share (80%)
- As they earn more, share decreases (degressive)
- Lifetime floor ensures ALL stakers always earn something (0.16% total)

Genesis Member Special Class:
- Earns on ALL FoundUps (ecosystem-wide)
- Class closes at mainnet launch (creates scarcity)
- Future stakers only earn on FoundUps they stake into

Staker Pool Economics (dilution_scenario.py analysis):
- 10-25 stakers: 10x distribution ratio in 10-26 months
- 50-100 stakers: 10x distribution ratio in 1-3 years
- 500+ stakers: diminishing allocations
- RECOMMENDATION: Cap genesis cohort at 100 stakers

PARADIGM: CABR/PoB (not CAGR/ROI)
- Stakers provide LIQUIDITY (energy for UPS capacity)
- BTC → Reserve → Backs UPS → Protocol runs
- Stakers receive F_i DISTRIBUTIONS (protocol mechanics)
- This is PROTOCOL PARTICIPATION, not investment

BOUNDARY NOTE (2026-03-31):
- Du pool stakers = CABR/PoB participation lane (this file)
- I_i holders in investor_staking.py = SEPARATE bonding-curve lane
- Do NOT conflate these two models
- See: memory/terminology.md for canonical distinction

Token Naming (STANDARDIZED):
- UPS = Universal participation token (bio-decaying)
- F_i = FoundUp Token (21M cap, Bitcoin-like, non-decaying)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ParticipantType(IntEnum):
    """Participant type determines which pools you access."""
    UN = 0   # 012 stakeholder - Un pool only (engagement-based)
    DAO = 1  # 0102 agent - Un + Dao pools (3V work-based)
    DU = 2   # Founding member/staker - Un + Dao + Du pools (passive)


class ActivityLevel(IntEnum):
    """Activity level determines share within each pool (divided by count at tier)."""
    UN = 0   # Tier 0: 4% of pool ÷ count_at_tier (degressive: >100x earned)
    DAO = 1  # Tier 1: 16% of pool ÷ count_at_tier (degressive: 10x-100x earned)
    DU = 2   # Tier 2: 80% of pool ÷ count_at_tier (degressive: <10x earned)


# Pool percentages (of total epoch rewards)
POOL_PERCENTAGES = {
    "stakeholder_un": 0.60,   # 60% - 012 stakeholders (ACTIVE, engagement)
    "stakeholder_dao": 0.16,  # 16% - 0102 agents (ACTIVE, 3V work)
    "stakeholder_du": 0.04,   # 4%  - Founding Members + Stakers (PASSIVE)
    "network": 0.16,          # 16% - Drip (F_i → BTC → UPS)
    "fund": 0.04,             # 4%  - Treasury (pAVS operations)
}

# Agent compute weight tiers (expensive models = more F_i)
COMPUTE_TIER_WEIGHTS = {
    "opus": 10.0,    # Heavy compute (Claude Opus)
    "sonnet": 3.0,   # Medium compute (Claude Sonnet)
    "haiku": 1.0,    # Light compute (Claude Haiku) - baseline
    "gemma": 0.5,    # Local inference (Gemma)
    "qwen": 0.5,     # Local inference (Qwen)
}

# Degressive staker tier thresholds (earned/staked ratio)
STAKER_TIER_THRESHOLDS = {
    "du": 10.0,      # <10x earned → du tier (80% share)
    "dao": 100.0,    # 10x-100x earned → dao tier (16% share)
    # >100x earned → un tier (4% share = lifetime floor)
}

# Staker pool controls (prevents dilution)
# Based on dilution_scenario.py analysis:
# - 10-25 stakers: 10x distribution ratio in 10-26 months
# - 50-100 stakers: 10x distribution ratio in 1-3 years
# - 500+ stakers: diminishing allocations
STAKER_CAP_GENESIS = 100      # Genesis cohort cap (best distributions)
STAKER_CAP_EARLY = 500        # Early cohort cap (good distributions)
STAKER_MIN_BTC = 0.001        # Minimum stake (~$100 at $100k BTC)
STAKER_RECOMMENDED_BTC = 0.01  # Recommended stake (~$1k at $100k BTC)

# Activity level shares (within each pool)
ACTIVITY_SHARES = {
    ActivityLevel.DU: 0.80,   # 80% of pool
    ActivityLevel.DAO: 0.16,  # 16% of pool
    ActivityLevel.UN: 0.04,   # 4% of pool
}

# Pool access by participant type (cumulative)
POOL_ACCESS = {
    ParticipantType.UN: ["stakeholder_un"],
    ParticipantType.DAO: ["stakeholder_un", "stakeholder_dao"],
    ParticipantType.DU: ["stakeholder_un", "stakeholder_dao", "stakeholder_du"],
}


@dataclass
class ComputeMetrics:
    """Metrics for agent compute cost (affects F_i payout)."""
    tokens_used: int = 0           # Total tokens consumed
    model_tier: str = "haiku"      # opus/sonnet/haiku/gemma/qwen
    wall_time_ms: int = 0          # Execution time
    api_calls: int = 0             # Number of API round-trips

    def compute_weight(self) -> float:
        """Calculate compute weight for F_i payout scaling.

        Formula: (tokens_used / 1000) * tier_weight
        More compute = more F_i earned
        """
        tier_weight = COMPUTE_TIER_WEIGHTS.get(self.model_tier, 1.0)
        token_factor = self.tokens_used / 1000.0 if self.tokens_used > 0 else 0.1
        return token_factor * tier_weight


@dataclass
class StakerPosition:
    """Tracks a staker's position for degressive tier calculation."""
    original_stake_btc: float = 0.0   # Initial BTC staked
    total_earned_fi: float = 0.0      # Total F_i earned lifetime
    stake_timestamp: str = ""          # When they staked

    @property
    def earned_ratio(self) -> float:
        """Ratio of earned to staked (for tier calculation)."""
        if self.original_stake_btc <= 0:
            return 0.0
        # Convert F_i to BTC equivalent (simplified: assume 1 F_i = 0.00001 BTC)
        fi_in_btc = self.total_earned_fi * 0.00001
        return fi_in_btc / self.original_stake_btc

    def get_degressive_tier(self) -> ActivityLevel:
        """Get activity tier based on degressive model.

        - <10x earned: du tier (80% share)
        - 10x-100x earned: dao tier (16% share)
        - >100x earned: un tier (4% share = lifetime floor)
        """
        ratio = self.earned_ratio
        if ratio >= STAKER_TIER_THRESHOLDS["dao"]:  # >100x
            return ActivityLevel.UN
        elif ratio >= STAKER_TIER_THRESHOLDS["du"]:  # 10x-100x
            return ActivityLevel.DAO
        else:  # <10x
            return ActivityLevel.DU


@dataclass
class Participant:
    """A participant in a FoundUp (or ecosystem-wide for genesis members)."""

    participant_id: str
    participant_type: ParticipantType
    activity_level: ActivityLevel
    ups_balance: float = 0.0
    foundup_tokens: Dict[str, float] = field(default_factory=dict)

    # Founding member / staker flags
    has_active_membership: bool = False   # Active subscription = Du pool access
    is_genesis_member: bool = False       # Earns on ALL FoundUps (class closes at launch)
    staker_position: Optional[StakerPosition] = None  # For degressive tier tracking

    @property
    def classification(self) -> str:
        """Return 2-digit classification (e.g., '22' for founder with max activity)."""
        return f"{self.participant_type.value}{self.activity_level.value}"

    @property
    def is_founding_member(self) -> bool:
        """True if participant has Du pool access (membership or staker)."""
        return self.has_active_membership or (self.staker_position is not None)

    def get_accessible_pools(self) -> List[str]:
        """Get list of pools this participant can earn from."""
        return POOL_ACCESS[self.participant_type]

    def update_staker_tier(self) -> None:
        """Update activity level based on degressive staker model."""
        if self.staker_position is not None:
            self.activity_level = self.staker_position.get_degressive_tier()

    def calculate_share(self, pool_name: str, pool_amount: float) -> float:
        """Calculate this participant's share of a pool.

        NOTE: This returns the TIER share (80%/16%/4%), which must then
        be divided by count_at_tier in the distributor.

        Args:
            pool_name: Name of the pool
            pool_amount: Total amount in the pool

        Returns:
            This participant's tier share (0 if not accessible)
        """
        if pool_name not in self.get_accessible_pools():
            return 0.0

        return pool_amount * ACTIVITY_SHARES[self.activity_level]


@dataclass
class EpochDistribution:
    """Result of distributing an epoch's rewards."""

    epoch: int
    total_rewards: float

    # Pool allocations
    un_pool: float = 0.0      # 60%
    dao_pool: float = 0.0     # 16%
    du_pool: float = 0.0      # 4%
    network_pool: float = 0.0  # 16% - drip source
    fund_pool: float = 0.0     # 4% - held

    # Participant distributions
    participant_rewards: Dict[str, float] = field(default_factory=dict)

    # Network drip tracking
    drip_distributed: float = 0.0
    fund_accumulated: float = 0.0


class PoolDistributor:
    """Distributes epoch rewards according to WSP 26 pool structure.

    Network 16% = Drip rewards re-injected into the system
    Fund 4% = Ecosystem fund held for sustainability
    """

    def __init__(self):
        self.participants: Dict[str, Participant] = {}
        self.accumulated_fund: float = 0.0
        self.total_drip_distributed: float = 0.0

    def register_participant(
        self,
        participant_id: str,
        p_type: ParticipantType,
        activity: ActivityLevel,
        has_active_membership: bool = False,
        is_genesis_member: bool = False,
        staker_position: Optional[StakerPosition] = None,
    ) -> Participant:
        """Register a new participant.

        Args:
            participant_id: Unique identifier
            p_type: UN (012), DAO (0102 agent), or DU (founding member/staker)
            activity: Initial activity tier (may change via degressive model)
            has_active_membership: Active subscription grants Du pool access
            is_genesis_member: Earns on ALL FoundUps (special class, closes at launch)
            staker_position: For anonymous stakers with degressive tier tracking
        """
        participant = Participant(
            participant_id=participant_id,
            participant_type=p_type,
            activity_level=activity,
            has_active_membership=has_active_membership,
            is_genesis_member=is_genesis_member,
            staker_position=staker_position,
        )
        self.participants[participant_id] = participant

        member_status = ""
        if is_genesis_member:
            member_status = " [GENESIS - ecosystem-wide]"
        elif has_active_membership:
            member_status = " [MEMBER]"
        elif staker_position:
            member_status = f" [STAKER: {staker_position.original_stake_btc:.4f} BTC]"

        logger.info(
            f"[Pool] Registered {participant_id} as {participant.classification} "
            f"(type={p_type.name}, activity={activity.name}){member_status}"
        )
        return participant

    def update_activity(self, participant_id: str, new_activity: ActivityLevel) -> None:
        """Update a participant's activity level (CABR-driven)."""
        if participant_id in self.participants:
            old = self.participants[participant_id].activity_level
            self.participants[participant_id].activity_level = new_activity
            logger.info(f"[Pool] {participant_id} activity: {old.name} -> {new_activity.name}")

    def distribute_epoch(
        self,
        epoch: int,
        total_ups_rewards: float,
        foundup_id: Optional[str] = None,
    ) -> EpochDistribution:
        """Distribute an epoch's UPS rewards according to pool structure.

        Args:
            epoch: Epoch number
            total_ups_rewards: Total UPS to distribute this epoch
            foundup_id: Optional FoundUp context (for FoundUp Token distribution)

        Returns:
            EpochDistribution with all allocations
        """
        result = EpochDistribution(epoch=epoch, total_rewards=total_ups_rewards)

        # Calculate pool amounts
        result.un_pool = total_ups_rewards * POOL_PERCENTAGES["stakeholder_un"]
        result.dao_pool = total_ups_rewards * POOL_PERCENTAGES["stakeholder_dao"]
        result.du_pool = total_ups_rewards * POOL_PERCENTAGES["stakeholder_du"]
        result.network_pool = total_ups_rewards * POOL_PERCENTAGES["network"]
        result.fund_pool = total_ups_rewards * POOL_PERCENTAGES["fund"]

        # Fund 4% is accumulated (held)
        self.accumulated_fund += result.fund_pool
        result.fund_accumulated = self.accumulated_fund

        # Distribute stakeholder pools (80%)
        self._distribute_stakeholder_pools(result)

        # Network 16% is the drip - re-inject as additional rewards
        self._distribute_network_drip(result)

        logger.info(
            f"[Pool] Epoch {epoch}: {total_ups_rewards:.2f} UPS distributed, "
            f"drip={result.drip_distributed:.2f}, fund_total={self.accumulated_fund:.2f}"
        )

        return result

    def _distribute_stakeholder_pools(self, result: EpochDistribution) -> None:
        """Distribute the 80% stakeholder pools to participants.

        CRITICAL: Pool shares are divided by count at each tier.
        Example: 10 people at du tier share the 80% → each gets 8%
        """
        pools = {
            "stakeholder_un": result.un_pool,
            "stakeholder_dao": result.dao_pool,
            "stakeholder_du": result.du_pool,
        }

        # Update staker tiers based on degressive model
        for p in self.participants.values():
            p.update_staker_tier()

        # Count participants at each activity level for each pool
        # This enables proper shared-pool division
        pool_tier_counts: Dict[str, Dict[ActivityLevel, int]] = {
            pool_name: {level: 0 for level in ActivityLevel}
            for pool_name in pools.keys()
        }

        for p in self.participants.values():
            for pool_name in p.get_accessible_pools():
                pool_tier_counts[pool_name][p.activity_level] += 1

        # Distribute pools with proper tier sharing
        for participant in self.participants.values():
            total_reward = 0.0

            for pool_name in participant.get_accessible_pools():
                pool_amount = pools.get(pool_name, 0.0)

                # Get tier share (80%/16%/4% of pool)
                tier_share = pool_amount * ACTIVITY_SHARES[participant.activity_level]

                # Divide by count at this tier (critical: shared pool!)
                count_at_tier = pool_tier_counts[pool_name][participant.activity_level]
                if count_at_tier > 0:
                    individual_share = tier_share / count_at_tier
                    total_reward += individual_share

            if total_reward > 0:
                participant.ups_balance += total_reward
                result.participant_rewards[participant.participant_id] = (
                    result.participant_rewards.get(participant.participant_id, 0.0) + total_reward
                )

    def _distribute_network_drip(self, result: EpochDistribution) -> None:
        """Distribute Network 16% as drip rewards (re-injected).

        The Network pool is distributed proportionally to activity level:
        - du (2): 80% of network pool = 12.8% of total
        - dao (1): 16% of network pool = 2.56% of total
        - un (0): 4% of network pool = 0.64% of total

        This is the "drip" mechanism that keeps UPS flowing.
        """
        network_amount = result.network_pool

        # Group participants by activity level
        by_activity: Dict[ActivityLevel, List[Participant]] = {
            ActivityLevel.UN: [],
            ActivityLevel.DAO: [],
            ActivityLevel.DU: [],
        }

        for p in self.participants.values():
            by_activity[p.activity_level].append(p)

        # Distribute network pool by activity level
        for activity_level, participants in by_activity.items():
            if not participants:
                continue

            # Total share for this activity level
            level_share = network_amount * ACTIVITY_SHARES[activity_level]

            # Divide equally among participants at this level
            per_participant = level_share / len(participants)

            for p in participants:
                p.ups_balance += per_participant
                result.participant_rewards[p.participant_id] = (
                    result.participant_rewards.get(p.participant_id, 0.0) + per_participant
                )
                result.drip_distributed += per_participant

        self.total_drip_distributed += result.drip_distributed

    def get_distribution_stats(self) -> Dict:
        """Get overall distribution statistics."""
        type_counts = {t: 0 for t in ParticipantType}
        activity_counts = {a: 0 for a in ActivityLevel}
        total_ups = 0.0
        genesis_count = 0
        member_count = 0
        staker_count = 0

        for p in self.participants.values():
            type_counts[p.participant_type] += 1
            activity_counts[p.activity_level] += 1
            total_ups += p.ups_balance
            if p.is_genesis_member:
                genesis_count += 1
            if p.has_active_membership:
                member_count += 1
            if p.staker_position is not None:
                staker_count += 1

        return {
            "participants": len(self.participants),
            "by_type": {t.name: c for t, c in type_counts.items()},
            "by_activity": {a.name: c for a, c in activity_counts.items()},
            "genesis_members": genesis_count,
            "active_members": member_count,
            "anonymous_stakers": staker_count,
            "total_ups_distributed": total_ups,
            "total_drip_distributed": self.total_drip_distributed,
            "accumulated_fund": self.accumulated_fund,
        }


class FoundUpTokenDistributor:
    """Distributes FoundUp Tokens (the Bitcoin-like asset).

    Each FoundUp has 21M tokens with tier-based release.
    Agents earn FoundUp Tokens through verified work (PoUW).
    Humans own the tokens earned by their agents.

    This is SEPARATE from UPS distribution - FoundUp Tokens are:
    - Scarce (21M cap per FoundUp)
    - Non-decaying (unlike UPS)
    - Earned through work (not participation)
    """

    # 21 million tokens per FoundUp (Bitcoin model)
    TOTAL_SUPPLY = 21_000_000

    # Tier release percentages (cumulative)
    TIER_RELEASE = {
        7: 0.00,   # Genesis - no tokens
        6: 0.05,   # Seeded - 5% (1.05M)
        5: 0.10,   # Active - 10% (2.1M)
        4: 0.20,   # Growing - 20% (4.2M)
        3: 0.35,   # Established - 35% (7.35M)
        2: 0.55,   # Thriving - 55% (11.55M)
        1: 1.00,   # Sovereign - 100% (21M)
    }

    def __init__(self, foundup_id: str):
        self.foundup_id = foundup_id
        self.current_tier: int = 7
        self.minted: float = 0.0
        self.btc_vault: float = 0.0

    @property
    def available_supply(self) -> float:
        """Tokens available at current tier."""
        return self.TOTAL_SUPPLY * self.TIER_RELEASE[self.current_tier]

    @property
    def remaining(self) -> float:
        """Tokens that can still be minted."""
        return max(0.0, self.available_supply - self.minted)

    def mint_for_work(
        self,
        base_amount: float,
        worker_id: str,
        v3_score: float = 1.0,
        compute_metrics: Optional[ComputeMetrics] = None,
    ) -> float:
        """Mint FoundUp Tokens for verified 3V work.

        Formula: fi_earned = base_amount × v3_score × compute_weight

        Args:
            base_amount: Base F_i reward for this task type
            worker_id: ID of agent/worker who completed work
            v3_score: CABR V3 valuation score (0-1), default 1.0
            compute_metrics: Agent compute cost (affects payout scaling)

        Returns:
            Actual amount minted (may be less if supply exhausted)
        """
        # Calculate weighted amount
        compute_weight = 1.0
        if compute_metrics is not None:
            compute_weight = compute_metrics.compute_weight()

        weighted_amount = base_amount * v3_score * compute_weight

        # Mint up to remaining supply
        mintable = min(weighted_amount, self.remaining)
        if mintable <= 0:
            logger.warning(f"[{self.foundup_id}] No tokens available at tier {self.current_tier}")
            return 0.0

        self.minted += mintable
        logger.info(
            f"[{self.foundup_id}] Minted {mintable:.2f} F_i for {worker_id} "
            f"(base={base_amount:.2f}, v3={v3_score:.2f}, compute={compute_weight:.2f})"
        )
        return mintable

    def progress_tier(self) -> bool:
        """Progress to next tier (unlocks more tokens)."""
        if self.current_tier <= 1:
            return False

        old_tier = self.current_tier
        self.current_tier -= 1
        new_supply = self.available_supply

        logger.info(
            f"[{self.foundup_id}] Tier {old_tier} -> {self.current_tier}, "
            f"supply now {new_supply:,.0f}"
        )
        return True

    def receive_vault_deposit(self, btc_amount: float) -> None:
        """Receive BTC into vault (Hotel California - never leaves)."""
        self.btc_vault += btc_amount
        logger.info(f"[{self.foundup_id}] Vault: +{btc_amount:.6f} BTC (total: {self.btc_vault:.6f})")
