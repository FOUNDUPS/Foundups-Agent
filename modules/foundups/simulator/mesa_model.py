"""Mesa model wrapper for FoundUps simulation.

Coordinates agent stepping and integrates with FAM modules.

Token Economics (WSP 26 Section 6.8):
- UPS: Universal fuel (humans RECEIVE distributions, agents SPEND allocated budgets)
- F_i: FoundUp-specific tokens (agents EARN through PoUW, humans OWN)
"""

from __future__ import annotations

import logging
import random
import time
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from .config import SimulatorConfig, DEFAULT_CONFIG
from .event_bus import EventBus
from .state_store import StateStore
from .adapters.fam_bridge import FAMBridge
from .adapters.phantom_plugs import PhantomTokenEconomy, PhantomSocialActions
from .agents.base_agent import BaseSimAgent
from .agents.founder_agent import FounderAgent
from .agents.user_agent import UserAgent
from .economics.token_economics import (
    TokenEconomicsEngine,
    FeeConfig,
    SubscriptionTier,
    adoption_curve,
)
from .economics.fi_orderbook import OrderBookManager
from .economics.investor_staking import InvestorPool
from .economics.btc_reserve import BTCReserve, get_btc_reserve, reset_btc_reserve
from .economics.demurrage import DemurrageEngine, DecayConfig
from .economics.pool_distribution import (
    PoolDistributor, FoundUpTokenDistributor,
    ParticipantType, ActivityLevel,
)
from .economics.epoch_ledger import EpochLedger
from .economics.btc_anchor_connector import AnchorMode, BTCAnchorConnector
from .economics.fi_rating import FiRatingEngine, get_rating_engine
from .economics.allocation_engine import AllocationEngine
from .economics.fee_revenue_tracker import (
    FeeRevenueTracker, FeeType, FeeEvent, FeeDistribution,
    get_fee_tracker, reset_fee_tracker,
)
from .economics.tide_economics import (
    TideEconomicsEngine, TreasuryHealth, NetworkHealth,
    TideEvent, TideEpochResult,
    get_tide_engine, reset_tide_engine,
)
from .economics.smartdao_spawning import (
    SmartDAOSpawningEngine,
    DAOTier,
    TIER_THRESHOLDS,
    SMARTDAO_RESERVE_SPLIT,
)
from .economics.cabr_flow_router import CABRFlowInputs, route_cabr_ups_flow
from .ai.cabr_estimator import CABREstimator, CABRScore, FoundUpIdea, CABR_THRESHOLD
from .step_pipeline import run_step

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class FoundUpsModel:
    """Mesa-like model for FoundUps simulation.

    This is a simplified Mesa model that coordinates agents
    without requiring the full Mesa dependency. If Mesa is
    needed later, this can be subclassed from mesa.Model.

    Key responsibilities:
    - Initialize FAM components (bridge, token economy)
    - Create and manage agents
    - Step through simulation ticks
    - Maintain SSoT via StateStore
    """

    def __init__(
        self,
        config: Optional[SimulatorConfig] = None,
        fam_daemon: Optional["Any"] = None,
    ) -> None:
        """Initialize the model.

        Args:
            config: Simulation configuration
            fam_daemon: Optional FAMDaemon instance for event SSoT
        """
        self._config = config or DEFAULT_CONFIG
        self._seed = self._config.seed
        random.seed(self._seed)

        # Current tick
        self._tick: int = 0
        self._start_time: float = 0.0
        self._running: bool = False

        # FAM bridge (thin wrapper around FAM modules) with shared daemon if provided.
        self._fam_bridge = FAMBridge(fam_daemon=fam_daemon)

        # Event system (SSoT) - connect to FAMBridge's daemon
        self._event_bus = EventBus()
        daemon = self._fam_bridge.get_daemon()
        if daemon:
            self._event_bus.connect_fam_daemon(daemon)

        # State store (derived from events)
        self._state_store = StateStore(
            event_bus=self._event_bus,
            grid_width=self._config.grid_width,
            grid_height=self._config.grid_height,
        )

        # Phantom plugs (simulated token/social systems)
        self._token_economy = PhantomTokenEconomy(
            initial_balance=self._config.initial_agent_tokens,
        )
        self._social_actions = PhantomSocialActions(
            like_cost=self._config.like_cost,
            follow_cost=self._config.follow_cost,
            token_economy=self._token_economy,
        )

        # WSP 26 Section 6.8: Human vs Agent token economics
        # UPS (humans earn), F_i (agents earn for human owners)
        self._token_econ_engine = TokenEconomicsEngine(fee_config=FeeConfig())
        self._orderbook = OrderBookManager(trading_fee_rate=0.02)
        self._investor_pool = InvestorPool()

        # BTC Reserve + Demurrage + Pool Distribution (wired for BTC-F_i mirror)
        reset_btc_reserve()  # Fresh reserve per simulation run
        self._btc_reserve = get_btc_reserve()
        self._demurrage = DemurrageEngine(
            config=DecayConfig(), btc_reserve=self._btc_reserve,
        )
        self._pool_distributor = PoolDistributor()
        self._fi_distributors: Dict[str, FoundUpTokenDistributor] = {}

        # BTC-F_i ratio tracking (key metric from 012)
        self._btc_fi_ratio_history: List[Dict] = []
        self._epoch_counter: int = 0

        # F_i Rating Engine (color temperature gradient for animation)
        self._rating_engine = get_rating_engine()
        self._rating_update_interval = 10  # Every 10 ticks, emit rating updates
        self._demurrage_interval: int = 10  # Apply demurrage every N ticks
        self._subscription_refresh_interval: int = 30
        self._subscription_month_reset_interval: int = 300

        # Allocation Engine (0102 digital twin UPS→F_i routing per WSP 26 Section 17)
        self._allocation_engine = AllocationEngine(
            token_engine=self._token_econ_engine,
            orderbook_manager=self._orderbook,
            rating_engine=self._rating_engine,
        )

        # CABR Score Estimator (3V engine: Validation -> Verification -> Valuation)
        self._cabr_estimator = CABREstimator(use_ai=False)  # Heuristic for simulation
        self._cabr_scores: Dict[str, CABRScore] = {}  # Cache per foundup
        self._cabr_release_rate: float = 0.02  # At most 2% of pAVS treasury per PoB event.
        self._cabr_worker_share: float = 0.70
        self._cabr_foundup_treasury_share: float = 0.20
        self._cabr_network_share: float = 0.10
        self._cabr_routed_ups_total: float = 0.0

        # Fee Revenue + Tide Economics (Full Tide - 012-approved 2026-02-17)
        # pump.fun validated: $3.5M/day at 1.25% → pAVS projects 1.8x at 2%+exit+creation
        reset_fee_tracker()
        reset_tide_engine()
        self._fee_tracker = FeeRevenueTracker(
            on_fee_collected=self._on_fee_collected,
        )
        self._tide_engine = TideEconomicsEngine(
            initial_network_pool_sats=500_000_000,  # 5 BTC initial
            on_tide_event=self._on_tide_event,
        )
        self._tide_epoch_interval = 100  # Process tide every 100 ticks
        self._sustainability_reached = False
        self._network_pool_fees_synced_sats = 0
        self._creation_fee_notional_sats = 0  # Conservative: no synthetic creation volume by default.
        self._creation_fee_recorded_foundups: set[str] = set()
        self._autonomous_trading_event_probability = 0.12
        self._autonomous_trading_profit_min_ups = 25.0
        self._autonomous_trading_profit_max_ups = 180.0
        self._autonomous_trading_cost_ratio_min = 0.20
        self._autonomous_trading_cost_ratio_max = 0.65
        self._autonomous_trading_keywords = (
            "trade",
            "trader",
            "trading",
            "bot",
            "arb",
            "market",
            "alpha",
        )

        # SmartDAO escalation runtime (WSP 100 event wiring)
        self._smartdao_engine = SmartDAOSpawningEngine()
        self._smartdao_epoch_interval = 50
        self._smartdao_threshold_scale = 5e-5  # Time-compressed simulator thresholds.
        self._smartdao_min_funding_transfer_ups = 100.0
        self._smartdao_autonomy_announced: set[str] = set()
        self._smartdao_last_phase_command: Optional[str] = None

        self._f0_seed_btc = 10.0
        self._f0_seeded = False
        self._f0_source_foundup_id = "F_0"
        self._epoch_ledger = EpochLedger(foundup_id=self._f0_source_foundup_id)
        self._anchor_connector: Optional[BTCAnchorConnector] = self._build_anchor_connector()
        self._f0_investor_ids: List[str] = [f"f0_investor_{idx:03d}" for idx in range(8)]
        self._mvp_offerings_resolved = 0
        self._total_dex_trades = 0
        self._total_dex_volume_ups = 0.0

        # Agents
        self._agents: Dict[str, BaseSimAgent] = {}
        self._agent_order: List[str] = []

        # Agent lifecycle tracking (01(02) → 0102 → 01/02 state machine)
        self._agent_awakened: set = set()  # Agents in 0102 zen state
        self._agent_last_activity_tick: Dict[str, int] = {}  # Last activity per agent
        self._agent_rank: Dict[str, int] = {}  # Current rank 1-7 per agent
        self._agent_idle_threshold: int = 100  # Ticks before emitting idle event

        # Pure-step shadow parity counters (refactor safety telemetry)
        self._pure_step_shadow_checks: int = 0
        self._pure_step_shadow_failures: int = 0
        self._pure_step_shadow_last: Dict[str, float | int | bool] = {}

        # Initialize agents
        self._create_agents()
        self._bootstrap_012_accounts()

        logger.info(
            f"[MODEL] Initialized with {len(self._agents)} agents, "
            f"seed={self._seed}"
        )

    def _build_anchor_connector(self) -> Optional[BTCAnchorConnector]:
        """Build optional Layer-D anchor connector from simulator config."""
        if not self._config.layer_d_anchor_enabled:
            return None

        mode_name = self._config.layer_d_anchor_mode
        if type(mode_name) is not str:
            raise ValueError("Selected Layer-D mode must be a supported name")
        try:
            mode = AnchorMode(mode_name.strip().lower())
        except ValueError as exc:
            raise ValueError("Selected Layer-D mode is unsupported") from exc

        db_path = None
        if self._config.layer_d_anchor_db_path:
            db_path = Path(self._config.layer_d_anchor_db_path)

        return BTCAnchorConnector(mode=mode, db_path=db_path)

    def _create_agents(self) -> None:
        """Create initial agent population."""
        use_ai = self._config.use_ai

        # Create founder agents (Qwen-powered if AI enabled)
        for i in range(self._config.num_founder_agents):
            agent_id = f"founder_{i:03d}"
            agent = FounderAgent(
                agent_id=agent_id,
                fam_bridge=self._fam_bridge,
                token_economy=self._token_economy,
                social_actions=self._social_actions,
                state_store=self._state_store,
                creation_cost=self._config.foundup_creation_cost,
                max_foundups=self._config.founder_max_foundups,
                action_probability=self._config.agent_action_probability,
                cooldown_ticks=self._config.agent_cooldown_ticks,
                use_ai=use_ai,
            )
            self._agents[agent_id] = agent
            self._agent_order.append(agent_id)

            # Register with state store and token economy
            self._state_store.register_agent(
                agent_id, "founder", self._config.initial_agent_tokens
            )
            self._token_economy.register_agent(agent_id)

            # Emit agent_joins event - 01(02) dormant state
            self._fam_bridge.emit_agent_joins(
                agent_id=agent_id,
                agent_type="founder",
                foundup_id="F_0",  # Ecosystem-level until assigned
                rank=1,  # Apprentice
            )

        # Create user agents (Gemma-powered if AI enabled)
        for i in range(self._config.num_user_agents):
            agent_id = f"user_{i:03d}"
            # Vary risk tolerance across users
            risk_tolerance = self._config.ai_risk_tolerance + (i % 5 - 2) * 0.1
            risk_tolerance = max(0.1, min(0.9, risk_tolerance))

            agent = UserAgent(
                agent_id=agent_id,
                fam_bridge=self._fam_bridge,
                token_economy=self._token_economy,
                social_actions=self._social_actions,
                state_store=self._state_store,
                like_cost=self._config.like_cost,
                follow_cost=self._config.follow_cost,
                stake_min=self._config.stake_min,
                stake_max=self._config.stake_max,
                action_probability=self._config.agent_action_probability,
                cooldown_ticks=self._config.agent_cooldown_ticks,
                use_ai=use_ai,
                risk_tolerance=risk_tolerance,
            )
            self._agents[agent_id] = agent
            self._agent_order.append(agent_id)

            # Register with state store and token economy
            self._state_store.register_agent(
                agent_id, "user", self._config.initial_agent_tokens
            )
            self._token_economy.register_agent(agent_id)

            # Emit agent_joins event - 01(02) dormant state
            self._fam_bridge.emit_agent_joins(
                agent_id=agent_id,
                agent_type="user",
                foundup_id="F_0",  # Ecosystem-level until assigned
                rank=1,  # Apprentice
            )

        logger.info(
            f"[MODEL] Created {self._config.num_founder_agents} founders, "
            f"{self._config.num_user_agents} users"
        )

    def _bootstrap_012_accounts(self) -> None:
        """Initialize 012 subscription accounts + pool participants.

        This wires the intended flow so allocation engine and pAVS distribution
        both operate from tick 1:
        - user_* -> 012 accounts with subscription allocation budgets
        - all agents -> participant registry for pool distribution
        - all agents -> token-econ wallets for future F_i mining hooks
        """
        tiers = [
            SubscriptionTier.SPARK,
            SubscriptionTier.EXPLORER,
            SubscriptionTier.BUILDER,
            SubscriptionTier.FOUNDER,
        ]
        daemon = self._fam_bridge.get_daemon()

        for idx, agent_id in enumerate(self._agent_order):
            if agent_id not in self._token_econ_engine.agent_wallets:
                self._token_econ_engine.register_agent(agent_id, allocator_id=agent_id)

            if agent_id.startswith("founder_"):
                if agent_id not in self._pool_distributor.participants:
                    self._pool_distributor.register_participant(
                        participant_id=agent_id,
                        p_type=ParticipantType.DAO,
                        activity=ActivityLevel.DAO,
                    )
                continue

            # Users act as 012 subscription accounts in simulator economics.
            account = self._token_econ_engine.human_accounts.get(agent_id)
            if account is None:
                account = self._token_econ_engine.register_human(agent_id, initial_ups=0.0)

            target_tier = tiers[idx % len(tiers)]
            account.upgrade_subscription(target_tier)
            refreshed = account.refresh_allocation()
            if refreshed > 0:
                account.ups_balance += refreshed
                if daemon:
                    daemon.emit(
                        event_type="subscription_allocation_refreshed",
                        payload={
                            "human_id": agent_id,
                            "tier": account.subscription_tier.value,
                            "allocation_ups": round(refreshed, 2),
                            "remaining_allocation_ups": round(account.remaining_allocation, 2),
                            "wallet_ups": round(account.ups_balance, 2),
                        },
                        actor_id=agent_id,
                        foundup_id="F_0",
                    )

            if agent_id not in self._pool_distributor.participants:
                self._pool_distributor.register_participant(
                    participant_id=agent_id,
                    p_type=ParticipantType.UN,
                    activity=ActivityLevel.UN,
                    has_active_membership=True,
                )

    def _sync_token_econ_foundup_pools(self) -> None:
        """Ensure token-econ pool state tracks FoundUps created via FAM bridge."""
        for foundup_id in self._state_store.get_foundup_ids():
            if foundup_id not in self._token_econ_engine.foundup_pools:
                self._token_econ_engine.register_foundup(foundup_id)
            if foundup_id not in self._fi_distributors:
                self._fi_distributors[foundup_id] = FoundUpTokenDistributor(foundup_id)

    def _refresh_subscription_allocations(self) -> None:
        """Refresh periodic 012 subscription allocations."""
        daemon = self._fam_bridge.get_daemon()
        for human_id, account in self._token_econ_engine.human_accounts.items():
            added = account.refresh_allocation()
            if added <= 0:
                continue
            account.ups_balance += added
            if daemon:
                daemon.emit(
                    event_type="subscription_allocation_refreshed",
                    payload={
                        "human_id": human_id,
                        "tier": account.subscription_tier.value,
                        "allocation_ups": round(added, 2),
                        "remaining_allocation_ups": round(account.remaining_allocation, 2),
                        "wallet_ups": round(account.ups_balance, 2),
                    },
                    actor_id=human_id,
                    foundup_id="F_0",
                )

    def _reset_subscription_cycles(self) -> None:
        """Reset monthly cycle counters for all subscription accounts."""
        daemon = self._fam_bridge.get_daemon()
        for human_id, account in self._token_econ_engine.human_accounts.items():
            account.reset_monthly_cycles()
            if daemon:
                daemon.emit(
                    event_type="subscription_cycle_reset",
                    payload={
                        "human_id": human_id,
                        "tier": account.subscription_tier.value,
                        "cycles_per_month": account.get_subscription_config().cycles_per_month,
                    },
                    actor_id=human_id,
                    foundup_id="F_0",
                )

    def step(self) -> None:
        """Execute one simulation tick.

        Mesa convention: model.step() advances simulation by one tick.
        """
        run_step(self)

        if self._config.verbose:
            logger.debug(f"[MODEL] Tick {self._tick} complete")

    def _track_agent_lifecycle(self) -> None:
        """Track agent state transitions: 01(02) → 0102 → 01/02.

        Emits:
        - agent_awakened: When agent first performs successful action
        - agent_idle: When agent inactive for threshold ticks
        - agent_ranked: When agent earns enough to rank up
        """
        for agent_id in self._agent_order:
            agent = self._agents[agent_id]
            state = self._state_store.get_state().agents.get(agent_id)
            if not state:
                continue

            # Initialize rank if not set
            if agent_id not in self._agent_rank:
                self._agent_rank[agent_id] = 1

            # Check for activity via state store (likes, follows, stakes, foundups)
            has_activity = (
                state.likes_given > 0 or
                state.follows_given > 0 or
                state.stakes_made > 0 or
                state.foundups_created > 0
            )

            # Awakening: first activity transitions 01(02) → 0102
            if has_activity and agent_id not in self._agent_awakened:
                self._agent_awakened.add(agent_id)
                self._agent_last_activity_tick[agent_id] = self._tick
                coherence = 0.62 + random.uniform(0, 0.20)  # 0.62-0.82
                self._fam_bridge.emit_agent_awakened(
                    agent_id=agent_id,
                    coherence=round(coherence, 2),
                    foundup_id="F_0",
                )
                logger.debug(f"[LIFECYCLE] {agent_id} awakened to 0102 (coherence: {coherence:.2f})")

            # Track last activity tick
            if has_activity:
                total_actions = state.likes_given + state.follows_given + state.stakes_made + state.foundups_created
                if agent_id not in self._agent_last_activity_tick:
                    self._agent_last_activity_tick[agent_id] = self._tick
                # Simple heuristic: if total actions increased, mark active
                # (In real impl, would track previous tick values)

            # Idle detection: 01/02 decayed state
            last_tick = self._agent_last_activity_tick.get(agent_id, 0)
            inactive_ticks = self._tick - last_tick
            if inactive_ticks >= self._agent_idle_threshold and agent_id in self._agent_awakened:
                # Emit idle event once per threshold window
                if inactive_ticks % self._agent_idle_threshold == 0:
                    self._fam_bridge.emit_agent_idle(
                        agent_id=agent_id,
                        foundup_id="F_0",
                        inactive_ticks=inactive_ticks,
                        current_tick=self._tick,
                    )
                    logger.debug(f"[LIFECYCLE] {agent_id} IDLE ({inactive_ticks} ticks)")

            # Rank progression based on earnings (simplified)
            current_rank = self._agent_rank.get(agent_id, 1)
            earned = state.tokens - self._config.initial_agent_tokens
            # Rank thresholds: 100, 500, 2000, 5000, 10000, 20000
            thresholds = [0, 100, 500, 2000, 5000, 10000, 20000]
            new_rank = 1
            for r, threshold in enumerate(thresholds[1:], start=2):
                if earned >= threshold:
                    new_rank = min(r, 7)

            if new_rank > current_rank:
                self._agent_rank[agent_id] = new_rank
                self._fam_bridge.emit_agent_ranked(
                    agent_id=agent_id,
                    old_rank=current_rank,
                    new_rank=new_rank,
                    foundup_id="F_0",
                )
                logger.debug(f"[LIFECYCLE] {agent_id} ranked up: {current_rank} → {new_rank}")

    def _advance_task_pipeline(self) -> None:
        """Progress task states through submit -> verify -> payout -> publish.

        Snapshot lists are used so a task only advances one stage per tick.
        """
        daemon = self._fam_bridge.get_daemon()
        claimed_tasks = list(self._fam_bridge.get_claimed_tasks())
        submitted_tasks = list(self._fam_bridge.get_submitted_tasks())
        verified_tasks = list(self._fam_bridge.get_verified_tasks())
        paid_tasks = list(self._fam_bridge.get_paid_tasks_pending_publication())

        if claimed_tasks:
            task = random.choice(claimed_tasks)
            submitter_id = task.assignee_id or "user_000"
            ok, msg, _ = self._fam_bridge.submit_proof(task.task_id, submitter_id=submitter_id)
            if not ok and self._config.verbose:
                logger.debug("[MODEL] submit_proof failed for %s: %s", task.task_id, msg)

        if submitted_tasks:
            task = random.choice(submitted_tasks)
            ok, msg, _ = self._fam_bridge.verify_task(task.task_id, verifier_id="verifier_0")
            if not ok and self._config.verbose:
                logger.debug("[MODEL] verify_task failed for %s: %s", task.task_id, msg)

        if verified_tasks:
            task = random.choice(verified_tasks)
            ok, msg, _ = self._fam_bridge.trigger_payout(task.task_id, treasury_actor_id="treasury_0")
            if ok:
                # PoB valve opened by verified payout -> CABR sizes the UPS flow pipe.
                self._route_cabr_ups_for_task(task)
                # Emit agent earning event for ticker
                agent_id = task.assignee_id or "agent_000"
                _, fi_earned = self._token_econ_engine.agent_completes_task(
                    agent_id=agent_id,
                    foundup_id=task.foundup_id,
                    task_cost_ups=0.0,
                    work_reward_fi=float(getattr(task, "reward_amount", 0.0)),
                )
                proxy_owner_id = self._token_econ_engine.resolve_proxy_owner(agent_id)
                if daemon and fi_earned > 0:
                    daemon.emit(
                        event_type="fi_mined_for_work",
                        payload={
                            "task_id": task.task_id,
                            "agent_id": agent_id,
                            "proxy_owner_id": proxy_owner_id,
                            "foundup_id": task.foundup_id,
                            "fi_earned": round(fi_earned, 6),
                        },
                        actor_id=agent_id,
                        foundup_id=task.foundup_id,
                        task_id=task.task_id,
                    )
                self._fam_bridge.emit_agent_earning(
                    agent_id=agent_id,
                    foundup_id=task.foundup_id,
                    amount=task.reward_amount,
                    task_id=task.task_id,
                )
            elif self._config.verbose:
                logger.debug("[MODEL] trigger_payout failed for %s: %s", task.task_id, msg)

        if paid_tasks:
            task = random.choice(paid_tasks)
            ok, msg, _ = self._fam_bridge.publish_milestone(task.task_id, distributor_id="distribution_0")
            if not ok and self._config.verbose:
                logger.debug("[MODEL] publish_milestone failed for %s: %s", task.task_id, msg)

    def _route_cabr_ups_for_task(self, task: object) -> None:
        """Route existing UPS from treasury via CABR pipe-size semantics.

        CABR/PoB model:
        - Treasury holds UPS (sats-backed)
        - PoB-validated payout opens valve
        - CABR score controls pipe size (flow rate)
        - No UPS minting occurs in this path
        """
        foundup_id = getattr(task, "foundup_id", None)
        if not foundup_id:
            return

        requested_ups = float(getattr(task, "reward_amount", 0.0) or 0.0)
        if requested_ups <= 0:
            return

        cabr_score = float(self._cabr_scores.get(foundup_id).total) if foundup_id in self._cabr_scores else CABR_THRESHOLD
        flow = route_cabr_ups_flow(
            CABRFlowInputs(
                treasury_ups_available=float(self._demurrage.pavs_treasury_balance),
                cabr_pipe_size=cabr_score,
                pob_validated=True,
                requested_ups=requested_ups,
                release_rate=self._cabr_release_rate,
            )
        )
        if flow.routed_ups <= 0:
            return

        worker_ups = flow.routed_ups * self._cabr_worker_share
        foundup_treasury_ups = flow.routed_ups * self._cabr_foundup_treasury_share
        network_ups = flow.routed_ups - worker_ups - foundup_treasury_ups

        assignee_id = getattr(task, "assignee_id", None) or "user_000"
        proxy_owner_id = self._token_econ_engine.resolve_proxy_owner(assignee_id)
        if proxy_owner_id not in self._token_econ_engine.human_accounts:
            self._token_econ_engine.register_human(proxy_owner_id, initial_ups=0.0)
        self._token_econ_engine.credit_012_distribution_ups(
            proxy_owner_id,
            worker_ups,
            source="cabr_pipe_flow_distribution",
        )

        foundup_pool = self._token_econ_engine.foundup_pools.get(foundup_id)
        if foundup_pool is None:
            foundup_pool = self._token_econ_engine.register_foundup(foundup_id)
        foundup_pool.ups_treasury += foundup_treasury_ups

        self._demurrage.total_to_network_pool += network_ups
        self._demurrage.update_pavs_treasury_balance(flow.treasury_ups_after)
        self._cabr_routed_ups_total += flow.routed_ups

        daemon = self._fam_bridge.get_daemon()
        if daemon:
            daemon.emit(
                event_type="cabr_pipe_flow_routed",
                payload={
                    "task_id": getattr(task, "task_id", ""),
                    "foundup_id": foundup_id,
                    "assignee_id": assignee_id,
                    "proxy_owner_id": proxy_owner_id,
                    "pob_validated": flow.valve_open,
                    "cabr_pipe_size": round(flow.cabr_pipe_size, 6),
                    "requested_ups": round(flow.requested_ups, 6),
                    "epoch_release_budget_ups": round(flow.epoch_release_budget_ups, 6),
                    "routed_ups": round(flow.routed_ups, 6),
                    "worker_ups": round(worker_ups, 6),
                    "foundup_treasury_ups": round(foundup_treasury_ups, 6),
                    "network_pool_ups": round(network_ups, 6),
                    "pavs_treasury_before_ups": round(flow.treasury_ups_before, 6),
                    "pavs_treasury_after_ups": round(flow.treasury_ups_after, 6),
                },
                actor_id="cabr_flow_router",
                foundup_id=foundup_id,
                task_id=getattr(task, "task_id", None),
            )
            daemon.emit(
                event_type="pavs_treasury_updated",
                payload={
                    "pavs_treasury_balance_ups": round(self._demurrage.pavs_treasury_balance, 6),
                    "network_pool_balance_ups": round(self._demurrage.total_to_network_pool, 6),
                    "treasury_health": round(self._demurrage.get_stats()["treasury_health"], 6),
                },
                actor_id="cabr_flow_router",
                foundup_id=foundup_id,
            )

    def _is_autonomous_trading_foundup(self, foundup_id: str) -> bool:
        """Heuristic classifier for FoundUps that run autonomous trading bots."""
        tile = self._state_store.get_state().foundups.get(foundup_id)
        if tile is None:
            return False
        marker_text = f"{tile.name} {tile.token_symbol}".lower()
        return any(keyword in marker_text for keyword in self._autonomous_trading_keywords)

    def _simulate_autonomous_trading_profits(self) -> None:
        """Simulate external trading PnL and route it through proxy economics.

        This is intentionally separate from DEX fee flow. It models business
        profit produced by autonomous trading FoundUps.
        """
        daemon = self._fam_bridge.get_daemon()
        for foundup_id in self._state_store.get_foundup_ids():
            if not self._is_autonomous_trading_foundup(foundup_id):
                continue
            if random.random() >= self._autonomous_trading_event_probability:
                continue

            tile = self._state_store.get_state().foundups.get(foundup_id)
            if tile is None:
                continue

            operator_agent_id = tile.owner_id or "user_000"
            gross_profit = random.uniform(
                self._autonomous_trading_profit_min_ups,
                self._autonomous_trading_profit_max_ups,
            )
            cost_ratio = random.uniform(
                self._autonomous_trading_cost_ratio_min,
                self._autonomous_trading_cost_ratio_max,
            )
            operating_cost = gross_profit * cost_ratio

            result = self._token_econ_engine.distribute_operational_profit(
                foundup_id=foundup_id,
                operator_agent_id=operator_agent_id,
                gross_profit_ups=gross_profit,
                operating_cost_ups=operating_cost,
                stake_target_foundup_id=foundup_id,
            )
            if result.net_profit_ups <= 0:
                continue

            self._demurrage.total_to_network_pool += result.network_pool_ups
            if result.proxy_exit_fee_ups > 0:
                self._demurrage.update_pavs_treasury_balance(
                    self._demurrage.pavs_treasury_balance + result.proxy_exit_fee_ups
                )

            if daemon:
                daemon.emit(
                    event_type="operational_profit_distributed",
                    payload={
                        "foundup_id": foundup_id,
                        "operator_agent_id": operator_agent_id,
                        "proxy_owner_id": result.proxy_owner_id,
                        "gross_profit_ups": round(result.gross_profit_ups, 6),
                        "operating_cost_ups": round(result.operating_cost_ups, 6),
                        "net_profit_ups": round(result.net_profit_ups, 6),
                        "proxy_distribution_ups": round(result.proxy_distribution_ups, 6),
                        "foundup_treasury_ups": round(result.foundup_treasury_ups, 6),
                        "network_pool_ups": round(result.network_pool_ups, 6),
                        "proxy_staked_ups": round(result.proxy_staked_ups, 6),
                        "proxy_exit_gross_ups": round(result.proxy_exit_gross_ups, 6),
                        "proxy_exit_fee_ups": round(result.proxy_exit_fee_ups, 6),
                        "stake_target_foundup_id": result.stake_target_foundup_id,
                    },
                    actor_id=operator_agent_id,
                    foundup_id=foundup_id,
                )

    def _simulate_market_activity(self) -> None:
        """Simulate decentralized F_i exchange activity for active FoundUps."""
        foundup_ids = self._state_store.get_foundup_ids()
        user_ids = [agent_id for agent_id in self._agent_order if agent_id.startswith("user_")]
        if not foundup_ids or len(user_ids) < 2:
            return

        # Trade activity is continuous but not every tick.
        if random.random() >= 0.35:
            return

        foundup_id = random.choice(foundup_ids)
        tile = self._state_store.get_state().foundups.get(foundup_id)
        if tile is None:
            return

        base_price = 1.0 + (tile.tasks_completed * 0.12) + (tile.likes * 0.01) + (tile.stakes * 0.02)
        spread = max(0.02, base_price * 0.03)
        sell_price = max(0.01, base_price - spread * random.uniform(0.2, 1.0))
        buy_price = base_price + spread * random.uniform(0.2, 1.2)
        quantity = round(random.uniform(3.0, 20.0), 2)
        adoption_rate = min(
            1.0,
            float(tile.customer_count) / float(max(1, self._config.num_user_agents)),
        )
        liquidity_hint_ups = float(max(0, tile.total_staked))

        seller_id = random.choice(user_ids)
        buyer_pool = [uid for uid in user_ids if uid != seller_id]
        if not buyer_pool:
            return
        buyer_id = random.choice(buyer_pool)

        sell_order, _ = self._orderbook.place_sell(
            foundup_id=foundup_id,
            human_id=seller_id,
            price=round(sell_price, 4),
            quantity=quantity,
            adoption_rate=adoption_rate,
            liquidity_hint_ups=liquidity_hint_ups,
        )
        buy_order, trades = self._orderbook.place_buy(
            foundup_id=foundup_id,
            human_id=buyer_id,
            price=round(buy_price, 4),
            quantity=quantity,
            adoption_rate=adoption_rate,
            liquidity_hint_ups=liquidity_hint_ups,
        )
        daemon = self._fam_bridge.get_daemon()
        book = self._orderbook.get_or_create_book(foundup_id)

        if daemon:
            daemon.emit(
                event_type="order_placed",
                payload={
                    "order_id": sell_order.order_id,
                    "side": "sell",
                    "owner_id": seller_id,
                    "price": round(sell_order.price, 4),
                    "quantity": round(sell_order.quantity, 2),
                    "status": sell_order.status.value,
                },
                actor_id=seller_id,
                foundup_id=foundup_id,
            )
            daemon.emit(
                event_type="order_placed",
                payload={
                    "order_id": buy_order.order_id,
                    "side": "buy",
                    "owner_id": buyer_id,
                    "price": round(buy_order.price, 4),
                    "quantity": round(buy_order.quantity, 2),
                    "status": buy_order.status.value,
                },
                actor_id=buyer_id,
                foundup_id=foundup_id,
            )

        if not trades:
            if daemon:
                depth = book.get_order_book_depth(levels=3)
                daemon.emit(
                    event_type="orderbook_snapshot",
                    payload={
                        "best_bid": depth.get("best_bid"),
                        "best_ask": depth.get("best_ask"),
                        "spread": depth.get("spread"),
                        "mid_price": depth.get("mid_price"),
                        "bids": depth.get("bids", []),
                        "asks": depth.get("asks", []),
                    },
                    actor_id="dex",
                    foundup_id=foundup_id,
                )
            return

        for trade in trades:
            self._total_dex_trades += 1
            self._total_dex_volume_ups += trade.ups_total

            # Record fee for Full Tide economics (2% DEX fee)
            self._record_fee_from_trade(
                trade.foundup_id,
                trade.ups_total,
                source_ref=trade.trade_id,
                metadata={
                    "buyer_id": trade.buyer_id,
                    "seller_id": trade.seller_id,
                },
            )

            if daemon:
                daemon.emit(
                    event_type="order_matched",
                    payload={
                        "trade_id": trade.trade_id,
                        "buyer_id": trade.buyer_id,
                        "seller_id": trade.seller_id,
                        "price": round(trade.price, 4),
                        "quantity": round(trade.quantity, 2),
                        "ups_total": round(trade.ups_total, 4),
                    },
                    actor_id="dex",
                    foundup_id=trade.foundup_id,
                )
                daemon.emit(
                    event_type="fi_trade_executed",
                    payload={
                        "trade_id": trade.trade_id,
                        "buyer_id": trade.buyer_id,
                        "seller_id": trade.seller_id,
                        "price": round(trade.price, 4),
                        "quantity": round(trade.quantity, 2),
                        "ups_total": round(trade.ups_total, 4),
                        "fee_ups": round(trade.fee_ups, 4),
                    },
                    actor_id=trade.buyer_id,
                    foundup_id=trade.foundup_id,
                )

        if daemon and trades:
            last_trade = trades[-1]
            depth = book.get_order_book_depth(levels=3)
            daemon.emit(
                event_type="price_tick",
                payload={
                    "last_price": round(last_trade.price, 4),
                    "best_bid": depth.get("best_bid"),
                    "best_ask": depth.get("best_ask"),
                    "spread": depth.get("spread"),
                    "mid_price": depth.get("mid_price"),
                    "total_volume_ups": round(book.total_volume_ups, 4),
                },
                actor_id="dex",
                foundup_id=foundup_id,
            )
            daemon.emit(
                event_type="orderbook_snapshot",
                payload={
                    "best_bid": depth.get("best_bid"),
                    "best_ask": depth.get("best_ask"),
                    "spread": depth.get("spread"),
                    "mid_price": depth.get("mid_price"),
                    "bids": depth.get("bids", []),
                    "asks": depth.get("asks", []),
                },
                actor_id="dex",
                foundup_id=foundup_id,
            )

    def _seed_f0_investor_pool_once(self) -> None:
        """Seed the ecosystem once from F_0 BTC principal."""
        if self._f0_seeded:
            return

        ii_tokens, tier = self._investor_pool.invest_btc(
            investor_id="f0_seed",
            btc_amount=self._f0_seed_btc,
        )
        self._f0_seeded = True
        if ii_tokens <= 0:
            return

        # Seed is anchored to F_0, not individual FoundUps.
        self._fam_bridge.get_daemon().emit(
            event_type="investor_funding_received",
            payload={
                "investor_id": "f0_seed",
                "source_foundup_id": self._f0_source_foundup_id,
                "btc_amount": self._f0_seed_btc,
                "ii_tokens": round(ii_tokens, 6),
                "tier": tier.value,
                "seeded": True,
            },
            actor_id="f0_seed",
            foundup_id=self._f0_source_foundup_id,
        )

    def _simulate_f0_investor_program(self) -> None:
        """F_0-only investor flow: subscriptions hoard UPS, then bid on Proto FoundUps."""
        self._seed_f0_investor_pool_once()
        foundup_ids = self._state_store.get_foundup_ids()
        if not foundup_ids:
            return

        state = self._state_store.get_state()
        proto_targets = [
            foundup_id
            for foundup_id in foundup_ids
            if state.foundups.get(foundup_id) and state.foundups[foundup_id].lifecycle_stage == "Proto"
        ]
        if not proto_targets:
            return

        # Subscription accrual (UPS hoarding) happens from the F_0 investor program.
        for investor_id in self._f0_investor_ids:
            if random.random() < 0.08:
                self._fam_bridge.accrue_investor_terms(
                    investor_id=investor_id,
                    terms=1,
                    term_ups=200,
                    max_terms=5,
                )

        if random.random() >= 0.25:
            return

        target_foundup = random.choice(proto_targets)
        bidder_id = random.choice(self._f0_investor_ids)
        bidder_state = self._fam_bridge.get_investor_subscription_state(bidder_id)
        available_ups = int(bidder_state.get("available_ups", 0))
        if available_ups <= 0:
            return

        bid_ups = max(50, min(available_ups, random.randint(50, 250)))
        ok, _, _ = self._fam_bridge.place_mvp_bid(
            foundup_id=target_foundup,
            investor_id=bidder_id,
            bid_ups=bid_ups,
        )
        if not ok:
            return

        bids = self._fam_bridge.get_mvp_bids(target_foundup)
        if len(bids) < 3:
            return

        ok, _, allocations = self._fam_bridge.resolve_mvp_offering(
            foundup_id=target_foundup,
            actor_id="treasury_0",
            token_amount=1_000,
            top_n=1,
        )
        if ok and allocations:
            self._mvp_offerings_resolved += 1

        self._investor_pool.update_network_adoption(
            foundups_count=state.total_foundups,
            total_revenue=float(state.total_stakes),
        )
        self._investor_pool.vest_tokens()

    def _apply_demurrage_cycle(self) -> None:
        """Apply bio-decay to all registered wallets.

        Decayed UPS is redistributed across network and pAVS treasury lanes.
        Active participants get decay relief via pool rewards.
        """
        daemon = self._fam_bridge.get_daemon()
        network_before = self._demurrage.total_to_network_pool
        pavs_before = self._demurrage.total_to_pavs_treasury

        # Register any new agents as wallets if not already tracked
        for agent_id in self._agent_order:
            if agent_id not in self._demurrage.wallets:
                balance = self._token_economy.get_balance(agent_id)
                if balance > 0:
                    self._demurrage.register_wallet(agent_id, float(balance))

        # Apply decay (1 day per interval for simulation speed)
        decay_results = self._demurrage.apply_decay_all(time_elapsed_days=1.0)

        if decay_results:
            total_decay = sum(decay_results.values())
            network_delta = self._demurrage.total_to_network_pool - network_before
            pavs_delta = self._demurrage.total_to_pavs_treasury - pavs_before
            self._demurrage.update_pavs_treasury_balance(
                self._demurrage.pavs_treasury_balance + pavs_delta
            )
            logger.debug(
                f"[MODEL] Demurrage tick {self._tick}: "
                f"{total_decay:.2f} UPS decayed from {len(decay_results)} wallets"
            )
            if daemon:
                daemon.emit(
                    event_type="demurrage_cycle_completed",
                    payload={
                        "wallets_affected": len(decay_results),
                        "total_decay_ups": round(total_decay, 4),
                        "network_pool_delta_ups": round(network_delta, 4),
                        "pavs_treasury_delta_ups": round(pavs_delta, 4),
                    },
                    actor_id="demurrage_engine",
                    foundup_id="F_0",
                )
                daemon.emit(
                    event_type="pavs_treasury_updated",
                    payload={
                        "pavs_treasury_balance_ups": round(self._demurrage.pavs_treasury_balance, 4),
                        "network_pool_balance_ups": round(self._demurrage.total_to_network_pool, 4),
                        "treasury_health": round(self._demurrage.get_stats()["treasury_health"], 4),
                    },
                    actor_id="demurrage_engine",
                    foundup_id="F_0",
                )

        if daemon:
            daemon.emit(
                event_type="treasury_separation_snapshot",
                payload={
                    "pavs_treasury_ups": round(self._demurrage.pavs_treasury_balance, 4),
                    "network_pool_ups": round(self._demurrage.total_to_network_pool, 4),
                    "fund_pool_ups": round(self._pool_distributor.accumulated_fund, 4),
                    "foundup_ups_treasury": {
                        fid: round(pool.ups_treasury, 4)
                        for fid, pool in self._token_econ_engine.foundup_pools.items()
                    },
                },
                actor_id="demurrage_engine",
                foundup_id="F_0",
            )

        # Distribute epoch rewards via pool structure
        self._epoch_counter += 1
        state = self._state_store.get_state()
        epoch_rewards = float(state.total_stakes) * 0.01  # 1% of total stakes per epoch
        if epoch_rewards > 0 and self._pool_distributor.participants:
            distribution = self._pool_distributor.distribute_epoch(
                epoch=self._epoch_counter,
                total_ups_rewards=epoch_rewards,
            )
            self._record_epoch_distribution(distribution)

    def _record_epoch_distribution(self, distribution: object) -> None:
        """Record epoch distribution to ledger and optionally publish Layer-D anchor."""
        entry = self._epoch_ledger.record_from_distribution(distribution)
        daemon = self._fam_bridge.get_daemon()
        if daemon:
            daemon.emit(
                event_type="epoch_ledger_recorded",
                payload={
                    "epoch": entry.epoch_number,
                    "entry_hash": entry.entry_hash,
                    "participant_count": len(entry.participant_rewards),
                    "total_distributed": round(float(entry.total_fi_distributed), 6),
                },
                actor_id="epoch_ledger",
                foundup_id=self._f0_source_foundup_id,
            )

        if not self._anchor_connector:
            return

        every = max(1, int(self._config.layer_d_anchor_every_n_epochs))
        if entry.epoch_number % every != 0:
            return

        commitment = self._epoch_ledger.prepare_settlement_commitment(entry.epoch_number)
        if commitment is None:
            return

        result = self._anchor_connector.publish_commitment(
            commitment,
            force=bool(self._config.layer_d_anchor_force_republish),
        )
        if daemon:
            daemon.emit(
                event_type="settlement_anchor_published",
                payload={
                    "epoch": entry.epoch_number,
                    "success": bool(result.get("success", False)),
                    "status": result.get("status"),
                    "tx_ref": result.get("tx_ref"),
                    "idempotent_hit": bool(result.get("idempotent_hit", False)),
                    "error": result.get("error"),
                },
                actor_id="btc_anchor_connector",
                foundup_id=self._f0_source_foundup_id,
            )

    def _simulate_012_allocations(self) -> None:
        """Simulate 012 participants allocating UPS to FoundUps via 0102 digital twin.

        Per WSP 26 Section 17: AllocationEngine routes to direct stake or DEX.
        """
        daemon = self._fam_bridge.get_daemon()

        # Get humans with UPS balance
        humans_with_ups = [
            (hid, account)
            for hid, account in self._token_econ_engine.human_accounts.items()
            if account.ups_balance > 10.0  # Minimum for allocation
        ]

        if not humans_with_ups:
            return

        # Get available FoundUps
        foundup_ids = list(self._token_econ_engine.foundup_pools.keys())
        if not foundup_ids:
            return

        # Random 012 decides to allocate (10% chance per tick)
        for human_id, account in humans_with_ups:
            if random.random() > 0.10:
                continue

            allocatable = min(account.ups_balance, account.remaining_allocation)
            if allocatable <= self._allocation_engine.min_allocation_ups:
                continue

            # Allocate 20-50% of available budget
            allocation_pct = random.uniform(0.20, 0.50)
            ups_to_allocate = allocatable * allocation_pct
            if not account.use_allocated_ups(ups_to_allocate):
                continue

            # 50% chance: fixed allocation, 50% chance: autonomous
            if random.random() < 0.50:
                # Fixed: pick 1-3 random FoundUps
                num_targets = min(len(foundup_ids), random.randint(1, 3))
                targets = random.sample(foundup_ids, num_targets)
                pct_each = 1.0 / num_targets
                target_dict = {fid: pct_each for fid in targets}

                batch = self._allocation_engine.allocate_fixed(
                    human_id=human_id,
                    total_ups=ups_to_allocate,
                    targets=target_dict,
                )
            else:
                # Autonomous: let 0102 decide
                batch = self._allocation_engine.allocate_autonomous(
                    human_id=human_id,
                    total_ups=ups_to_allocate,
                    candidate_foundups=foundup_ids,
                    max_targets=3,
                )

            successful_ups = sum(result.ups_allocated for result in batch.results)
            if successful_ups < ups_to_allocate:
                # Refund unused allocation budget so failed routing is not punitive.
                account.remaining_allocation += (ups_to_allocate - successful_ups)

            if daemon:
                daemon.emit(
                    event_type="ups_allocation_executed",
                    payload={
                        "human_id": human_id,
                        "strategy": batch.strategy.value,
                        "ups_requested": round(ups_to_allocate, 4),
                        "ups_executed": round(successful_ups, 4),
                        "fi_received": round(batch.total_fi_received, 4),
                        "success_count": batch.success_count,
                        "pending_count": len(batch.pending_orders),
                        "remaining_allocation_ups": round(account.remaining_allocation, 4),
                    },
                    actor_id=human_id,
                    foundup_id="F_0",
                )
                for result in batch.results:
                    daemon.emit(
                        event_type="ups_allocation_result",
                        payload={
                            "human_id": human_id,
                            "strategy": batch.strategy.value,
                            "path": result.path.value,
                            "ups_allocated": round(result.ups_allocated, 4),
                            "fi_received": round(result.fi_received, 4),
                            "fee_paid": round(result.fee_paid, 4),
                            "order_id": result.order_id,
                        },
                        actor_id=human_id,
                        foundup_id=result.foundup_id,
                    )

            if batch.success_count > 0:
                logger.debug(
                    f"[MODEL] 012 allocation: {human_id} allocated "
                    f"{ups_to_allocate:.2f} UPS -> {batch.total_fi_received:.2f} F_i "
                    f"({batch.strategy.value}, {batch.success_count} targets)"
                )

    def _record_btc_fi_ratio(self) -> None:
        """Record BTC-per-F_i ratio for tracking the mirror dynamic.

        Key metric: btc_per_fi = btc_reserve / fi_released
        Should increase over time (early cheap, late expensive).
        """
        btc_total = self._btc_reserve.total_btc
        econ_stats = self._token_econ_engine.get_system_stats()
        fi_outstanding = econ_stats.get("total_fi_outstanding", 0.0)

        # Calculate adoption score from simulation state
        state = self._state_store.get_state()
        # Simple adoption proxy: foundups created / target capacity
        adoption_score = min(1.0, state.total_foundups / max(1, 100))
        s_curve_release = adoption_curve(adoption_score)

        btc_per_fi = btc_total / max(1.0, fi_outstanding) if fi_outstanding > 0 else 0.0

        snapshot = {
            "tick": self._tick,
            "epoch": self._epoch_counter,
            "btc_reserve": round(btc_total, 8),
            "fi_outstanding": round(fi_outstanding, 2),
            "btc_per_fi": round(btc_per_fi, 8),
            "adoption_score": round(adoption_score, 4),
            "s_curve_release": round(s_curve_release, 4),
            "ups_minted": round(self._btc_reserve.total_ups_circulating, 2),  # legacy key
            "ups_circulating": round(self._btc_reserve.total_ups_circulating, 2),
            "ups_value_btc": round(self._btc_reserve.ups_value_btc, 8),
            "total_decayed": round(self._demurrage.total_decayed, 2),
        }
        self._btc_fi_ratio_history.append(snapshot)

        if self._config.verbose:
            logger.info(
                f"[MODEL] BTC/F_i ratio @ tick {self._tick}: "
                f"{btc_per_fi:.8f} BTC/F_i "
                f"(reserve={btc_total:.4f}, fi={fi_outstanding:.0f}, "
                f"adoption={adoption_score:.2%})"
            )

    # =========================================================================
    # Fee Revenue + Tide Economics (Full Tide Integration)
    # =========================================================================

    def _on_fee_collected(self, event: FeeEvent, dist: FeeDistribution) -> None:
        """Callback when fee is collected - emit FAM event."""
        daemon = self._fam_bridge.get_daemon()
        if not daemon:
            return
        daemon.emit(
            event_type="fee_collected",
            payload={
                "fee_type": event.fee_type.value,
                "foundup_id": event.foundup_id,
                "amount_sats": event.amount_sats,
                "volume_sats": event.volume_sats,
                "tick": event.tick,
                "source_ref": event.metadata.get("source_ref"),
                "distribution": {
                    "fi_treasury": dist.fi_treasury_sats,
                    "network_pool": dist.network_pool_sats,
                    "pavs_treasury": dist.pavs_treasury_sats,
                    "btc_reserve": dist.btc_reserve_sats,
                },
            },
            actor_id="fee_tracker",
            foundup_id=event.foundup_id,
        )

    def _on_tide_event(self, event: TideEvent) -> None:
        """Callback when tide flows - emit FAM event."""
        daemon = self._fam_bridge.get_daemon()
        if not daemon:
            return
        payload = {
            "foundup_id": event.foundup_id,
            "amount_sats": event.amount_sats,
            "from": event.from_source,
            "to": event.to_destination,
            "tick": event.tick,
            "reason": event.reason,
        }
        daemon.emit(
            event_type=event.event_type,  # "tide_in" or "tide_out"
            payload=payload,
            actor_id="tide_engine",
            foundup_id=event.foundup_id,
        )

        # Emit explicit support aliases for downstream consumers.
        if event.event_type == "tide_out":
            daemon.emit(
                event_type="tide_support_sent",
                payload=payload,
                actor_id="tide_engine",
                foundup_id=event.foundup_id,
            )
        elif event.event_type == "tide_in":
            daemon.emit(
                event_type="tide_support_received",
                payload=payload,
                actor_id="tide_engine",
                foundup_id=event.foundup_id,
            )

    def _process_tide_epoch(self) -> None:
        """Process tide economics (IMF-like ecosystem balancing).

        Called every tide_epoch_interval ticks (default: 100).
        - Syncs FoundUp states to tide engine
        - Processes TIDE OUT (overflow drips to Network Pool)
        - Processes TIDE IN (Network Pool supports CRITICAL F_i)
        - Checks for sustainability milestone
        """
        state = self._state_store.get_state()

        # Sync foundup states to tide engine
        for foundup_id, tile in state.foundups.items():
            # Conservative treasury signal:
            # - explicit MVP treasury injection (UPS)
            # - actually tracked fee treasury from FeeRevenueTracker (sats)
            fee_state_for_foundup = self._fee_tracker.get_foundup_state(foundup_id)
            fee_treasury_sats = fee_state_for_foundup.treasury_sats if fee_state_for_foundup else 0
            mvp_treasury_sats = int(max(0.0, tile.mvp_treasury_injection_ups))
            treasury_sats = max(0, fee_treasury_sats + mvp_treasury_sats)

            # Optional creation fee hook (kept conservative by default via zero notional).
            if foundup_id not in self._creation_fee_recorded_foundups:
                if self._creation_fee_notional_sats > 0:
                    self._fee_tracker.record_creation(
                        tick=self._tick,
                        foundup_id=foundup_id,
                        amount_sats=self._creation_fee_notional_sats,
                        is_mined=True,
                        metadata={"source_ref": f"foundup:{foundup_id}:creation"},
                    )
                self._creation_fee_recorded_foundups.add(foundup_id)

            # Derive tier from treasury size with a conservative non-zero floor for FoundUps.
            if foundup_id == self._f0_source_foundup_id:
                tier = "F2_GROWTH"
            else:
                tier = "F1_OPO"
            if treasury_sats >= 1_000_000_000_000:
                tier = "F5_SYSTEMIC"
            elif treasury_sats >= 100_000_000_000:
                tier = "F4_MEGA"
            elif treasury_sats >= 10_000_000_000:
                tier = "F3_INFRA"
            elif treasury_sats >= 1_000_000_000:
                tier = "F2_GROWTH"
            elif treasury_sats >= 100_000_000:
                tier = "F1_OPO"

            # Update existing state instead of recreating each epoch.
            current = self._tide_engine.get_foundup_state(foundup_id)
            if current is None:
                self._tide_engine.register_foundup(
                    foundup_id=foundup_id,
                    tier=tier,
                    treasury_sats=treasury_sats,
                )
            else:
                self._tide_engine.update_tier(foundup_id, tier)
                self._tide_engine.update_treasury(foundup_id, treasury_sats)

        # Add only NEW network fee inflows from fee tracker (delta sync).
        fee_state = self._fee_tracker.get_ecosystem_state()
        new_fees = fee_state.network_pool_sats - self._network_pool_fees_synced_sats
        if new_fees > 0:
            self._tide_engine.add_to_network_pool(new_fees)
            self._network_pool_fees_synced_sats += new_fees
        elif new_fees < 0:
            # Fee tracker reset or rewind: realign sync cursor safely.
            self._network_pool_fees_synced_sats = fee_state.network_pool_sats

        # Process tide
        result = self._tide_engine.process_epoch(tick=self._tick)

        # Log tide activity
        if result.tide_in_total_sats > 0 or result.tide_out_total_sats > 0:
            logger.info(
                f"[TIDE] Epoch {self._tick}: "
                f"OUT={result.tide_out_total_sats/100_000_000:.4f} BTC from {result.overflow_foundups} F_i, "
                f"IN={result.tide_in_total_sats/100_000_000:.4f} BTC to {result.critical_foundups} F_i"
            )

        # Check sustainability milestone
        metrics = self._fee_tracker.get_sustainability_metrics()
        if metrics["is_self_sustaining_claim"] and not self._sustainability_reached:
            self._sustainability_reached = True
            daemon = self._fam_bridge.get_daemon()
            if daemon:
                daemon.emit(
                    event_type="sustainability_reached",
                    payload={
                        "tick": self._tick,
                        "foundup_count": metrics["foundup_count"],
                        "daily_revenue_btc": metrics["daily_revenue_btc"],
                        "revenue_cost_ratio": metrics["revenue_cost_ratio"],
                        "downside_revenue_cost_ratio_p10": metrics["downside_revenue_cost_ratio_p10"],
                    },
                    actor_id="fee_tracker",
                    foundup_id="F_0",
                )
            logger.info(
                f"[MILESTONE] Ecosystem SELF-SUSTAINING at tick {self._tick}! "
                f"Revenue: {metrics['daily_revenue_btc']:.4f} BTC/day "
                f"(downside p10 ratio={metrics['downside_revenue_cost_ratio_p10']:.2f}x)"
            )

    def _sync_smartdao_registry(self) -> None:
        """Register newly created FoundUps with SmartDAO runtime state."""
        for foundup_id in self._state_store.get_foundup_ids():
            if foundup_id not in self._smartdao_engine.daos:
                self._smartdao_engine.register_foundup(foundup_id)

    def _estimate_foundup_treasury_ups(self, foundup_id: str) -> float:
        """Estimate total treasury balance using canonical UPS==sat accounting."""
        state = self._state_store.get_state()
        tile = state.foundups.get(foundup_id)
        mvp_treasury_ups = float(tile.mvp_treasury_injection_ups) if tile else 0.0

        fee_state = self._fee_tracker.get_foundup_state(foundup_id)
        fee_treasury_ups = float(fee_state.treasury_sats) if fee_state else 0.0

        pool = self._token_econ_engine.foundup_pools.get(foundup_id)
        pool_treasury_ups = float(pool.ups_treasury) if pool else 0.0

        return max(0.0, fee_treasury_ups + mvp_treasury_ups + pool_treasury_ups)

    def _estimate_foundup_active_agents(self, foundup_id: str) -> int:
        """Estimate active operator load from customer + task throughput."""
        state = self._state_store.get_state()
        tile = state.foundups.get(foundup_id)
        if tile is None:
            return 0
        customer_load = int(round(max(0, tile.customer_count)))
        task_load = int(max(0, tile.tasks_completed))
        founder_floor = 1
        return max(founder_floor, founder_floor + customer_load + task_load)

    def _emit_phase_command(self, target_phase: str, force: bool = False) -> None:
        """Emit phase command only when phase changes (or force is requested)."""
        if not force and self._smartdao_last_phase_command == target_phase:
            return
        daemon = self._fam_bridge.get_daemon()
        if not daemon:
            return
        daemon.emit(
            event_type="phase_command",
            payload={
                "target_phase": target_phase,
                "force": force,
            },
            actor_id="smartdao_engine",
            foundup_id="F_0",
        )
        self._smartdao_last_phase_command = target_phase

    def _attempt_scaled_tier_escalation(self, foundup_id: str) -> Optional[DAOTier]:
        """Attempt tier promotion with simulator-timescale threshold compression."""
        dao = self._smartdao_engine.daos.get(foundup_id)
        if dao is None:
            return None

        next_tier_value = dao.tier.value + 1
        if next_tier_value > DAOTier.F5_SYSTEMIC.value:
            return None

        next_tier = DAOTier(next_tier_value)
        thresholds = TIER_THRESHOLDS[next_tier]
        scaled_treasury_threshold = float(thresholds["treasury_ups"]) * self._smartdao_threshold_scale

        if (
            dao.adoption_ratio >= float(thresholds["adoption_ratio"])
            and dao.treasury_ups >= scaled_treasury_threshold
            and dao.active_agents >= int(thresholds["active_agents"])
        ):
            dao.tier = next_tier
            return next_tier

        return None

    def _process_smartdao_epoch(self) -> None:
        """Process SmartDAO tier progression + inter-DAO funding events."""
        state = self._state_store.get_state()
        if not state.foundups:
            return

        self._sync_smartdao_registry()

        # Refresh measurable signals before escalation checks.
        user_denom = max(1, self._config.num_user_agents)
        for foundup_id in state.foundups.keys():
            dao = self._smartdao_engine.daos.get(foundup_id)
            if dao is None:
                continue
            tile = state.foundups[foundup_id]
            dao.adoption_ratio = max(0.0, min(1.0, float(tile.customer_count) / float(user_denom)))
            dao.active_agents = self._estimate_foundup_active_agents(foundup_id)
            dao.treasury_ups = self._estimate_foundup_treasury_ups(foundup_id)

            # Feed spawning fund from sustained surplus, not principal treasury.
            tier_floor = float(TIER_THRESHOLDS[dao.tier]["treasury_ups"]) * self._smartdao_threshold_scale
            if dao.tier != DAOTier.F0_DAE and dao.treasury_ups > tier_floor:
                overflow = dao.treasury_ups - tier_floor
                dao.spawning_fund_ups += overflow * SMARTDAO_RESERVE_SPLIT["spawning_fund"] * 0.05

        daemon = self._fam_bridge.get_daemon()
        if not daemon:
            return

        escalations = 0
        emerged = 0

        for foundup_id in state.foundups.keys():
            dao = self._smartdao_engine.daos.get(foundup_id)
            if dao is None:
                continue
            old_tier = dao.tier
            new_tier = self._attempt_scaled_tier_escalation(foundup_id)
            if new_tier is None:
                continue

            escalations += 1
            payload = {
                "foundup_id": foundup_id,
                "old_tier": old_tier.name,
                "new_tier": new_tier.name,
                "adoption_ratio": round(dao.adoption_ratio, 4),
                "treasury_ups": round(dao.treasury_ups, 2),
                "active_agents": dao.active_agents,
                "tick": self._tick,
            }
            daemon.emit(
                event_type="tier_escalation",
                payload=payload,
                actor_id="smartdao_engine",
                foundup_id=foundup_id,
            )

            if old_tier == DAOTier.F0_DAE and new_tier.value >= DAOTier.F1_OPO.value:
                emerged += 1
                daemon.emit(
                    event_type="smartdao_emergence",
                    payload={
                        "foundup_id": foundup_id,
                        "old_tier": old_tier.name,
                        "new_tier": new_tier.name,
                        "adoption_ratio": round(dao.adoption_ratio, 4),
                        "tick": self._tick,
                    },
                    actor_id="smartdao_engine",
                    foundup_id=foundup_id,
                )

            if new_tier.value >= DAOTier.F2_GROWTH.value and foundup_id not in self._smartdao_autonomy_announced:
                self._smartdao_autonomy_announced.add(foundup_id)
                daemon.emit(
                    event_type="treasury_autonomy",
                    payload={
                        "foundup_id": foundup_id,
                        "tier": new_tier.name,
                        "treasury_ups": round(dao.treasury_ups, 2),
                        "spawning_fund_ups": round(dao.spawning_fund_ups, 2),
                        "tick": self._tick,
                        "timestamp": f"tick-{self._tick:010d}",
                    },
                    actor_id="smartdao_engine",
                    foundup_id=foundup_id,
                )

        # Funding flows: higher-tier DAOs seed lower-tier DAOs from spawning fund.
        donors = sorted(
            [
                dao for dao in self._smartdao_engine.daos.values()
                if dao.tier.value >= DAOTier.F2_GROWTH.value
                and dao.spawning_fund_ups >= self._smartdao_min_funding_transfer_ups
            ],
            key=lambda dao: (-dao.tier.value, -dao.spawning_fund_ups, dao.foundup_id),
        )
        receivers = sorted(
            [
                dao for dao in self._smartdao_engine.daos.values()
                if dao.tier.value <= DAOTier.F1_OPO.value
            ],
            key=lambda dao: (dao.treasury_ups, dao.foundup_id),
        )
        for donor in donors:
            if not receivers:
                break
            receiver = next(
                (candidate for candidate in receivers if candidate.foundup_id != donor.foundup_id),
                None,
            )
            if receiver is None:
                break

            transfer_ups = min(
                donor.spawning_fund_ups * 0.10,
                self._smartdao_min_funding_transfer_ups * 2.0,
            )
            if transfer_ups < self._smartdao_min_funding_transfer_ups:
                continue

            donor.spawning_fund_ups -= transfer_ups
            receiver.treasury_ups += transfer_ups

            daemon.emit(
                event_type="cross_dao_funding",
                payload={
                    "source_dao": donor.foundup_id,
                    "target_dao": receiver.foundup_id,
                    "amount": int(round(transfer_ups)),
                    "source_tier": donor.tier.name,
                    "target_tier": receiver.tier.name,
                    "tick": self._tick,
                },
                actor_id="smartdao_engine",
                foundup_id=receiver.foundup_id,
            )
            receivers.sort(key=lambda dao: (dao.treasury_ups, dao.foundup_id))

        if emerged > 0:
            # Keep DRIVEN_MODE phase transitions deterministic and sparse.
            self._emit_phase_command("CELEBRATE", force=True)

        if escalations > 0 and self._config.verbose:
            logger.info(
                "[SMARTDAO] tick=%s escalations=%s emergences=%s",
                self._tick,
                escalations,
                emerged,
            )

    def _record_fee_from_trade(
        self,
        foundup_id: str,
        volume_ups: float,
        source_ref: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record DEX trade fee from market activity."""
        # Convert UPS volume to sats (1 UPS == 1 sat accounting unit).
        # Keep float precision so sub-sat fee carry can accumulate correctly.
        volume_sats = max(0.0, float(volume_ups))
        if volume_sats > 0:
            self._fee_tracker.record_dex_trade(
                tick=self._tick,
                foundup_id=foundup_id,
                volume_sats=volume_sats,
                source_ref=source_ref,
                metadata=metadata,
            )

    def get_fee_metrics(self) -> Dict:
        """Get current fee revenue metrics."""
        return self._fee_tracker.get_sustainability_metrics()

    def get_tide_metrics(self) -> Dict:
        """Get current tide economics metrics."""
        return self._tide_engine.get_ecosystem_metrics()

    def _emit_rating_updates(self) -> None:
        """Emit F_i rating updates for animation (color temperature gradient).

        Calculates rating dimensions from simulation state:
        - velocity: Task completion rate
        - traction: Customer/engagement counts
        - health: Lifecycle stage progress
        - potential: Founder track record (simulated)

        Emits 'fi_rating_updated' events for SSE streaming.
        """
        state = self._state_store.get_state()
        daemon = self._fam_bridge.get_daemon()
        if not daemon:
            return

        for foundup_id, tile in state.foundups.items():
            # Calculate velocity from task completion rate
            task_ratio = tile.tasks_completed / max(1, tile.task_count)
            velocity = min(1.0, task_ratio * 2)  # Scale to 0-1

            # Calculate traction from engagement
            engagement = tile.likes + tile.customer_count * 10
            traction = min(1.0, engagement / 100)

            # Calculate health from lifecycle stage
            stage_health = {
                "Idea": 0.1,
                "PoC": 0.3,
                "Soft-Proto": 0.4,
                "Proto": 0.6,
                "MVP": 0.9,
                "Launch": 1.0,
            }
            health = stage_health.get(tile.lifecycle_stage, 0.2)

            # Potential: simulate founder track record (random for now)
            # In production, this comes from FounderTrackRecord
            potential = 0.5 + (hash(foundup_id) % 30) / 100  # 0.5-0.8 range

            # Update rating engine
            rating = self._rating_engine.get_or_create_rating(foundup_id)
            rating.velocity = velocity
            rating.traction = traction
            rating.health = health
            rating.potential = potential

            # Emit event for SSE
            rating_data = self._rating_engine.get_animation_data(foundup_id)
            daemon.emit(
                event_type="fi_rating_updated",
                payload=rating_data,
                actor_id="rating_engine",
                foundup_id=foundup_id,
            )

    def _emit_cabr_updates(self) -> None:
        """Emit CABR score updates for animation.

        Calculates CABR (Consensus-Driven Autonomous Benefit Rate, also referred to
        as Collective Autonomous Benefit Rate) from simulation state to power PoB:
        - env_score: Environmental impact (heuristic from category)
        - soc_score: Social impact (heuristic from category)
        - part_score: Participation metrics (task completion, verifications)

        Emits 'cabr_score_updated' events for SSE streaming.
        """
        state = self._state_store.get_state()
        daemon = self._fam_bridge.get_daemon()
        if not daemon:
            return

        for foundup_id, tile in state.foundups.items():
            # Initialize CABR score for new FoundUps
            if foundup_id not in self._cabr_scores:
                # Create FoundUpIdea from tile data for initial estimate
                idea = FoundUpIdea(
                    name=tile.name,
                    token_symbol=tile.token_symbol,
                    pain_point="simulation_default",  # Would come from FoundUp metadata
                    outcome="simulation_default",
                    category=self._get_foundup_category(tile.name),
                    team_size=3,
                    total_supply=tile.token_supply or 1_000_000,
                    initial_allocation={"treasury": 0.5, "team": 0.2, "community": 0.3},
                )
                self._cabr_scores[foundup_id] = self._cabr_estimator.estimate_idea_cabr(idea)

            # Update with live participation metrics
            cabr = self._cabr_scores[foundup_id]
            # Count active agents (simplified - all agents potentially contribute)
            active_agents = len([
                a for a in state.agents.values()
                if a.status == "active"
            ])
            cabr = self._cabr_estimator.update_participation(
                score=cabr,
                tasks_completed=tile.tasks_completed,
                tasks_total=tile.task_count,
                active_agents=active_agents,
                verifications=tile.tasks_completed,  # Proxy: completed = verified
            )
            self._cabr_scores[foundup_id] = cabr

            # Emit event for SSE
            daemon.emit(
                event_type="cabr_score_updated",
                payload={
                    "env_score": cabr.env_score,
                    "soc_score": cabr.soc_score,
                    "part_score": cabr.part_score,
                    "total": cabr.total,
                    "threshold": CABR_THRESHOLD,
                    "threshold_met": cabr.total >= CABR_THRESHOLD,
                    "confidence": cabr.confidence,
                },
                actor_id="cabr_engine",
                foundup_id=foundup_id,
            )

    def _get_foundup_category(self, name: str) -> str:
        """Infer category from FoundUp name for CABR heuristics."""
        name_lower = name.lower()
        if "junk" in name_lower or "waste" in name_lower:
            return "waste"
        elif "cloud" in name_lower or "kitchen" in name_lower or "food" in name_lower:
            return "food"
        elif "space" in name_lower or "rocket" in name_lower:
            return "infrastructure"
        elif "health" in name_lower or "med" in name_lower:
            return "healthcare"
        elif "solar" in name_lower or "energy" in name_lower:
            return "energy"
        elif "edu" in name_lower or "learn" in name_lower:
            return "education"
        elif "social" in name_lower or "twitter" in name_lower:
            return "social"
        elif "defi" in name_lower or "finance" in name_lower:
            return "defi"
        else:
            return "infrastructure"  # Default

    def start(self) -> None:
        """Start the simulation."""
        self._running = True
        self._start_time = time.time()
        logger.info("[MODEL] Simulation started")

    def stop(self) -> None:
        """Stop the simulation."""
        self._running = False
        logger.info(f"[MODEL] Simulation stopped at tick {self._tick}")

    @property
    def tick(self) -> int:
        """Current simulation tick."""
        return self._tick

    @property
    def running(self) -> bool:
        """Whether simulation is running."""
        return self._running

    @property
    def state_store(self) -> StateStore:
        """Get state store for rendering."""
        return self._state_store

    @property
    def event_bus(self) -> EventBus:
        """Get event bus."""
        return self._event_bus

    @property
    def config(self) -> SimulatorConfig:
        """Get simulation config."""
        return self._config

    @property
    def token_economics(self) -> TokenEconomicsEngine:
        """Get WSP 26 token economics engine."""
        return self._token_econ_engine

    @property
    def btc_reserve(self) -> BTCReserve:
        """Get BTC Reserve (Hotel California)."""
        return self._btc_reserve

    @property
    def demurrage(self) -> DemurrageEngine:
        """Get demurrage engine (bio-decay for LIQUID UPS)."""
        return self._demurrage

    @property
    def pool_distributor(self) -> PoolDistributor:
        """Get pool distributor (Un/Dao/Du)."""
        return self._pool_distributor

    @property
    def btc_fi_ratio_history(self) -> List[Dict]:
        """Get BTC-per-F_i ratio history for analysis."""
        return self._btc_fi_ratio_history

    @property
    def allocation_engine(self) -> AllocationEngine:
        """Get allocation engine (0102 digital twin UPS→F_i routing)."""
        return self._allocation_engine

    def get_agent(self, agent_id: str) -> Optional[BaseSimAgent]:
        """Get agent by ID."""
        return self._agents.get(agent_id)

    def get_agents_by_type(self, agent_type: str) -> List[BaseSimAgent]:
        """Get all agents of a given type."""
        return [a for a in self._agents.values() if a.agent_type == agent_type]

    def get_stats(self) -> Dict:
        """Get simulation statistics."""
        state = self._state_store.get_state()
        econ_stats = self._token_econ_engine.get_system_stats()
        fee_metrics = self._fee_tracker.get_sustainability_metrics()
        tide_metrics = self._tide_engine.get_ecosystem_metrics()
        anchor_stats = self._anchor_connector.get_stats() if self._anchor_connector else {}
        scenario_pack = fee_metrics.get("scenario_pack", {})
        downside = scenario_pack.get("downside", {})
        base = scenario_pack.get("base", {})
        upside = scenario_pack.get("upside", {})
        smartdao_tier_distribution: Dict[str, int] = {tier.name: 0 for tier in DAOTier}
        smartdao_autonomous_foundups = 0
        smartdao_spawning_fund_ups = 0.0
        for dao in self._smartdao_engine.daos.values():
            smartdao_tier_distribution[dao.tier.name] += 1
            smartdao_spawning_fund_ups += float(dao.spawning_fund_ups)
            if dao.tier.value >= DAOTier.F2_GROWTH.value:
                smartdao_autonomous_foundups += 1

        return {
            "tick": self._tick,
            "elapsed_seconds": state.elapsed_seconds,
            "total_foundups": state.total_foundups,
            "total_likes": state.total_likes,
            "total_stakes": state.total_stakes,
            "total_tokens": state.total_tokens_circulating,
            "total_dex_trades": state.total_dex_trades,
            "total_dex_volume_ups": state.total_dex_volume_ups,
            "total_operational_profit_ups": state.total_operational_profit_ups,
            "agent_count": len(self._agents),
            "founders": len([a for a in self._agents.values() if a.agent_type == "founder"]),
            "users": len([a for a in self._agents.values() if a.agent_type == "user"]),
            # WSP 26 token economics stats
            "ups_circulation": econ_stats["total_ups_circulation"],
            "fi_outstanding": econ_stats["total_fi_outstanding"],
            "btc_vault_total": econ_stats["total_btc_vault"],
            "fees_collected": econ_stats["total_fees_ops"] + econ_stats["total_fees_insurance"],
            "operational_profit_gross_ups": econ_stats["operational_profit_gross_ups"],
            "operational_cost_ups": econ_stats["operational_cost_ups"],
            "operational_profit_net_ups": econ_stats["operational_profit_net_ups"],
            "operational_proxy_distributions_ups": econ_stats["operational_proxy_distributions_ups"],
            "operational_foundup_treasury_ups": econ_stats["operational_foundup_treasury_ups"],
            "operational_network_pool_ups": econ_stats["operational_network_pool_ups"],
            "proxy_exit_volume_ups": econ_stats["proxy_exit_volume_ups"],
            "proxy_exit_fees_ups": econ_stats["proxy_exit_fees_ups"],
            "investor_pool_rate": self._investor_pool.founder_share_per_foundup,
            "investor_hurdle_met": self._investor_pool.return_hurdle_met,
            "f0_seed_btc": self._f0_seed_btc,
            "f0_investor_count": len(self._f0_investor_ids),
            "mvp_offerings_resolved": self._mvp_offerings_resolved,
            "active_012_accounts": len(self._token_econ_engine.human_accounts),
            # BTC Reserve + Demurrage (wired economics)
            "btc_reserve_total": self._btc_reserve.total_btc,
            "btc_reserve_usd": self._btc_reserve.reserve_usd_value,
            "ups_value_btc": self._btc_reserve.ups_value_btc,
            "total_demurrage_decayed": self._demurrage.total_decayed,
            "total_btc_from_decay": getattr(self._demurrage, "total_btc_from_decay", 0.0),
            "pool_participants": len(self._pool_distributor.participants),
            "pavs_treasury_ups": self._demurrage.pavs_treasury_balance,
            "network_pool_ups": self._demurrage.total_to_network_pool,
            "fund_pool_ups": self._pool_distributor.accumulated_fund,
            "foundup_treasury_ups_total": sum(
                pool.ups_treasury for pool in self._token_econ_engine.foundup_pools.values()
            ),
            "cabr_routed_ups_total": self._cabr_routed_ups_total,
            "allocation_batches": self._allocation_engine.allocation_count,
            "allocation_ups_total": self._allocation_engine.total_allocated_ups,
            "allocation_fi_total": self._allocation_engine.total_fi_acquired,
            "epochs_completed": self._epoch_counter,
            "layer_d_anchor_enabled": bool(self._anchor_connector),
            "layer_d_anchor_mode": anchor_stats.get("mode", "disabled"),
            "layer_d_anchor_total_published": int(anchor_stats.get("total_published", 0)),
            "layer_d_anchor_total_confirmed": int(anchor_stats.get("total_confirmed", 0)),
            "layer_d_anchor_total_failed": int(anchor_stats.get("total_failed", 0)),
            "layer_d_anchor_replay_guards_triggered": int(anchor_stats.get("replay_guards_triggered", 0)),
            "pure_step_shadow_checks": self._pure_step_shadow_checks,
            "pure_step_shadow_failures": self._pure_step_shadow_failures,
            "pure_step_shadow_last_tick": int(self._pure_step_shadow_last.get("tick", 0)),
            "pure_step_shadow_last_ok": bool(self._pure_step_shadow_last.get("ok", True)),
            # Full Tide economics (conservative, defendable metrics)
            "fee_gross_daily_btc": fee_metrics["gross_daily_revenue_btc"],
            "fee_pavs_daily_btc": fee_metrics["daily_revenue_btc"],
            "fee_protocol_capture_daily_btc": fee_metrics["protocol_capture_daily_btc"],
            "fee_daily_burn_btc": fee_metrics["daily_burn_btc"],
            "fee_revenue_cost_ratio": fee_metrics["revenue_cost_ratio"],
            "fee_protocol_capture_ratio": fee_metrics["protocol_capture_ratio"],
            "fee_has_min_sample_window": fee_metrics["has_min_sample_window"],
            "fee_observation_days": fee_metrics["observation_days"],
            "fee_self_sustaining": fee_metrics["is_self_sustaining"],
            "fee_self_sustaining_raw": fee_metrics["is_self_sustaining_raw"],
            "fee_self_sustaining_base_gate": fee_metrics["is_self_sustaining_base_gate"],
            "fee_self_sustaining_downside": fee_metrics["is_self_sustaining_downside"],
            "fee_downside_revenue_cost_ratio_p10": fee_metrics["downside_revenue_cost_ratio_p10"],
            "fee_self_sustaining_protocol_capture": fee_metrics["is_self_sustaining_protocol_capture"],
            "fee_self_sustaining_protocol_capture_raw": fee_metrics["is_self_sustaining_protocol_capture_raw"],
            "fee_estimated_break_even_fi": fee_metrics["estimated_break_even_fi"],
            "fee_scenario_downside_ratio_p10": float(downside.get("revenue_cost_ratio_p10", 0.0)),
            "fee_scenario_base_ratio_p50": float(base.get("revenue_cost_ratio_p50", 0.0)),
            "fee_scenario_upside_ratio_p90": float(upside.get("revenue_cost_ratio_p90", 0.0)),
            "tide_network_pool_btc": tide_metrics["network_pool_btc"],
            "tide_network_health": tide_metrics["network_health"],
            "tide_epochs_processed": tide_metrics["tide_epochs_processed"],
            "smartdao_registered_foundups": len(self._smartdao_engine.daos),
            "smartdao_autonomous_foundups": smartdao_autonomous_foundups,
            "smartdao_spawning_fund_ups": smartdao_spawning_fund_ups,
            "smartdao_tier_distribution": smartdao_tier_distribution,
            # BTC-F_i mirror ratio (key metric)
            "btc_per_fi_latest": (
                self._btc_fi_ratio_history[-1]["btc_per_fi"]
                if self._btc_fi_ratio_history else 0.0
            ),
            "btc_fi_ratio_snapshots": len(self._btc_fi_ratio_history),
        }
