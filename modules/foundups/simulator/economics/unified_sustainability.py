"""Unified Sustainability Engine - Combines All Revenue Streams.

012-REQUEST (2026-02-21):
"is there an way to compute stat for compute? hard think..."

PROBLEM:
- sustainability_matrix.py only tracks DEX fees (0.0002 ratios)
- This ignores subscription revenue (~$112K/month at 25K users)
- This ignores angel revenue (~$39K/month at 200 angels)
- Gap appears ~5000ÁEbut closes when all streams combined

THREE REVENUE STREAMS:
1. Fee Revenue (DEX + exit + creation) - from fee_revenue_tracker.py
2. Subscription Revenue (ARPU ÁEsubscribers) - from subscription_tiers.py
3. Angel Revenue ($195 ÁEangels) - from subscription_tiers.py

PLUS: Compute Backing for Mined F_i
- Mined F_i has no BTC backing (unlike staked F_i)
- But compute HAS cost: $0.003 - $0.19 per task
- Accumulate compute spend ↁEbacking value for mined tokens

WSP References:
- WSP 26: Token economics
- WSP 29: CABR integration
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple

# Import from sibling modules
from .fee_revenue_tracker import (
    FEE_RATES,
    FeeType,
)
from .subscription_tiers import (
    TIERS,
    ANGEL_TIER,
)
from .agent_compute_costs import (
    AGENT_INFRASTRUCTURE_COSTS,
)


# ============================================================================
# CONFIGURATION
# ============================================================================

BTC_PRICE_USD = 100_000
SATS_PER_BTC = 100_000_000
SATS_PER_USD = SATS_PER_BTC / BTC_PRICE_USD  # 1000 sats/$1

# Monthly burn baseline (from ten_year_projection.py)
F0_MONTHLY_BURN_BTC = 0.27  # $27K/month
F0_MONTHLY_BURN_USD = F0_MONTHLY_BURN_BTC * BTC_PRICE_USD
F0_MONTHLY_BURN_SATS = int(F0_MONTHLY_BURN_BTC * SATS_PER_BTC)

# Subscription tier distribution (from ten_year_projection.py:206-213)
TIER_DISTRIBUTION = {
    "free": 0.40,
    "starter": 0.20,
    "basic": 0.18,
    "plus": 0.12,
    "pro": 0.07,
    "enterprise": 0.03,
}

# Gross margins
SUBSCRIPTION_GROSS_MARGIN = 0.85  # 85% after infra costs
COMPUTE_GROSS_MARGIN = 0.60       # 60% target margin on compute


# ============================================================================
# COMPUTE BACKING MODEL
# ============================================================================

@dataclass
class ComputeBackingState:
    """Tracks compute expenditure as backing for mined F_i.

    Mined F_i has no BTC backing (unlike staked F_i which is backed by UPS←BTC).
    But compute HAS real cost. This accumulator tracks:
    - Total compute spend (USD equivalent)
    - F_i issued against that compute
    - Effective "compute reserve" value
    """
    total_compute_usd: float = 0.0
    total_tasks_executed: int = 0
    total_fi_mined: float = 0.0

    # Per-agent breakdown
    compute_by_agent: Dict[str, float] = field(default_factory=dict)
    tasks_by_agent: Dict[str, int] = field(default_factory=dict)

    def record_task(
        self,
        agent_name: str,
        cost_usd: float,
        fi_earned: float,
        task_count: int = 1,
    ) -> None:
        """Record compute workload and associated F_i earnings."""
        normalized_tasks = max(0, int(task_count))
        self.total_compute_usd += cost_usd
        self.total_tasks_executed += normalized_tasks
        self.total_fi_mined += fi_earned

        self.compute_by_agent[agent_name] = (
            self.compute_by_agent.get(agent_name, 0.0) + cost_usd
        )
        self.tasks_by_agent[agent_name] = (
            self.tasks_by_agent.get(agent_name, 0) + normalized_tasks
        )

    @property
    def compute_per_fi(self) -> float:
        """USD of compute backing per mined F_i token."""
        if self.total_fi_mined <= 0:
            return 0.0
        return self.total_compute_usd / self.total_fi_mined

    @property
    def compute_reserve_sats(self) -> int:
        """Compute backing expressed in satoshis (for UPS parity)."""
        return int(self.total_compute_usd * SATS_PER_USD)


# ============================================================================
# UNIFIED REVENUE MODEL
# ============================================================================

@dataclass
class RevenueSnapshot:
    """Point-in-time revenue across all streams."""

    # Stream 1: Fee Revenue
    fee_dex_usd: float = 0.0
    fee_exit_usd: float = 0.0
    fee_creation_usd: float = 0.0

    # Stream 2: Subscription Revenue
    subscribers_total: int = 0
    subscribers_paying: int = 0
    subscription_revenue_usd: float = 0.0
    subscription_margin_usd: float = 0.0

    # Stream 3: Angel Revenue
    angels_total: int = 0
    angel_revenue_usd: float = 0.0
    angel_opo_fees_usd: float = 0.0  # 20% of OPO stakes

    # Compute Stats
    compute_spend_usd: float = 0.0
    compute_margin_usd: float = 0.0

    @property
    def total_fee_revenue_usd(self) -> float:
        return self.fee_dex_usd + self.fee_exit_usd + self.fee_creation_usd

    @property
    def total_revenue_usd(self) -> float:
        return (
            self.total_fee_revenue_usd +
            self.subscription_margin_usd +
            self.angel_revenue_usd +
            self.angel_opo_fees_usd +
            self.compute_margin_usd
        )

    @property
    def total_revenue_sats(self) -> int:
        return int(self.total_revenue_usd * SATS_PER_USD)

    @property
    def compute_generated_value_usd(self) -> float:
        """Gross value generated in compute lane before infra cost."""
        return self.compute_spend_usd + self.compute_margin_usd

    @property
    def return_on_compute_ratio(self) -> float:
        """RoC = (V_generated - C_compute) / C_compute = margin / spend."""
        if self.compute_spend_usd <= 0:
            return 0.0
        return self.compute_margin_usd / self.compute_spend_usd

    @property
    def return_on_compute_percent(self) -> float:
        return self.return_on_compute_ratio * 100.0

    @property
    def value_per_compute_dollar(self) -> float:
        """Gross value generated per $1 of compute spend."""
        if self.compute_spend_usd <= 0:
            return 0.0
        return self.compute_generated_value_usd / self.compute_spend_usd


@dataclass
class SustainabilityMetrics:
    """Unified sustainability metrics combining all streams."""

    # Revenue
    revenue: RevenueSnapshot

    # Burn
    monthly_burn_usd: float
    monthly_burn_sats: int

    # Ratios
    fee_only_ratio: float        # Old metric (DEX fees / burn)
    combined_ratio: float        # New metric (all revenue / burn)

    # Compute backing
    compute_backing: ComputeBackingState

    # ROC-FIRST: Primary sustainability gate (compute productivity)
    is_compute_positive: bool         # ROC > 0 = PRIMARY GATE

    # ROI-PATH: Secondary gate (traditional revenue breakeven)
    is_roi_sustainable: bool          # Revenue > Burn = SECONDARY

    # Combined
    is_sustainable: bool              # Both gates pass
    sustainability_margin_usd: float  # Revenue - Burn
    months_runway: float              # At current rates

    @property
    def compute_generated_value_usd(self) -> float:
        return self.revenue.compute_generated_value_usd

    @property
    def return_on_compute_ratio(self) -> float:
        return self.revenue.return_on_compute_ratio

    @property
    def return_on_compute_percent(self) -> float:
        return self.revenue.return_on_compute_percent

    @property
    def value_per_compute_dollar(self) -> float:
        return self.revenue.value_per_compute_dollar

    @property
    def roc_ratio(self) -> float:
        """ROC = (V_generated - C_compute) / C_compute - PRIMARY METRIC."""
        return self.return_on_compute_ratio

    @property
    def is_compute_profitable(self) -> bool:
        """Legacy alias for is_compute_positive."""
        return self.is_compute_positive

    def to_dict(self) -> Dict:
        """Export for JSON serialization."""
        return {
            # ROC-FIRST: Primary gate
            "roc_ratio": self.roc_ratio,
            "is_compute_positive": self.is_compute_positive,
            # ROI-PATH: Secondary gate
            "fee_only_ratio": self.fee_only_ratio,
            "combined_ratio": self.combined_ratio,
            "is_roi_sustainable": self.is_roi_sustainable,
            # Combined
            "is_sustainable": self.is_sustainable,
            "sustainability_margin_usd": self.sustainability_margin_usd,
            "months_runway": self.months_runway,
            "return_on_compute_ratio": self.return_on_compute_ratio,
            "return_on_compute_percent": self.return_on_compute_percent,
            "value_per_compute_dollar": self.value_per_compute_dollar,
            "compute_generated_value_usd": self.compute_generated_value_usd,
            "is_compute_profitable": self.is_compute_positive,  # Legacy alias
            "revenue": {
                "fee_dex_usd": self.revenue.fee_dex_usd,
                "fee_exit_usd": self.revenue.fee_exit_usd,
                "fee_creation_usd": self.revenue.fee_creation_usd,
                "subscription_revenue_usd": self.revenue.subscription_revenue_usd,
                "subscription_margin_usd": self.revenue.subscription_margin_usd,
                "angel_revenue_usd": self.revenue.angel_revenue_usd,
                "compute_spend_usd": self.revenue.compute_spend_usd,
                "compute_margin_usd": self.revenue.compute_margin_usd,
                "compute_generated_value_usd": self.revenue.compute_generated_value_usd,
                "return_on_compute_ratio": self.revenue.return_on_compute_ratio,
                "value_per_compute_dollar": self.revenue.value_per_compute_dollar,
                "total_revenue_usd": self.revenue.total_revenue_usd,
            },
            "burn": {
                "monthly_burn_usd": self.monthly_burn_usd,
                "monthly_burn_sats": self.monthly_burn_sats,
            },
            "compute_backing": {
                "total_compute_usd": self.compute_backing.total_compute_usd,
                "total_tasks": self.compute_backing.total_tasks_executed,
                "total_fi_mined": self.compute_backing.total_fi_mined,
                "compute_per_fi": self.compute_backing.compute_per_fi,
                "compute_reserve_sats": self.compute_backing.compute_reserve_sats,
            },
        }


# ============================================================================
# CALCULATOR
# ============================================================================

class UnifiedSustainabilityCalculator:
    """Calculates sustainability across all revenue streams."""

    def __init__(
        self,
        monthly_burn_usd: float = F0_MONTHLY_BURN_USD,
        btc_price: float = BTC_PRICE_USD,
    ):
        self.monthly_burn_usd = monthly_burn_usd
        self.monthly_burn_sats = int(monthly_burn_usd * SATS_PER_USD)
        self.btc_price = btc_price
        self.compute_backing = ComputeBackingState()

    def calculate_subscription_revenue(
        self,
        total_subscribers: int,
        tier_distribution: Dict[str, float] = None,
    ) -> Tuple[float, float, int]:
        """Calculate subscription revenue and margin.

        Returns:
            (gross_revenue_usd, margin_usd, paying_subscribers)
        """
        dist = tier_distribution or TIER_DISTRIBUTION

        gross_revenue = 0.0
        paying_count = 0

        for tier_name, pct in dist.items():
            count = int(total_subscribers * pct)
            tier = TIERS.get(tier_name)
            if tier and tier.price_usd > 0:
                gross_revenue += count * tier.price_usd
                paying_count += count

        margin = gross_revenue * SUBSCRIPTION_GROSS_MARGIN
        return gross_revenue, margin, paying_count

    def calculate_angel_revenue(
        self,
        total_angels: int,
        monthly_opos: int = 5,
        avg_opo_stake_usd: float = 10_000,
    ) -> Tuple[float, float]:
        """Calculate angel subscription + OPO fee revenue.

        Returns:
            (subscription_revenue_usd, opo_fee_revenue_usd)
        """
        # Base subscription
        sub_revenue = total_angels * ANGEL_TIER.price_usd

        # OPO fees (20% of stakes)
        opo_fee_revenue = (
            monthly_opos *
            min(total_angels, ANGEL_TIER.max_angels_per_opo) *
            avg_opo_stake_usd *
            ANGEL_TIER.opo_treasury_fee
        )

        return sub_revenue, opo_fee_revenue

    def calculate_compute_revenue(
        self,
        tasks_per_month: int,
        agent_mix: Dict[str, float] = None,
    ) -> Tuple[float, float]:
        """Calculate compute cost and margin.

        Args:
            tasks_per_month: Total tasks executed
            agent_mix: Fraction of tasks by agent type

        Returns:
            (total_cost_usd, margin_usd)
        """
        if agent_mix is None:
            # Default mix weighted toward common agents
            agent_mix = {
                "basic_search": 0.30,
                "openclaw_lite": 0.25,
                "openclaw": 0.25,
                "gotjunk_browse": 0.10,
                "gotjunk": 0.05,
                "cabr_validator": 0.05,
            }

        total_cost = 0.0
        for agent_name, fraction in agent_mix.items():
            task_count = int(tasks_per_month * fraction)
            infra = AGENT_INFRASTRUCTURE_COSTS.get(agent_name)
            if infra:
                cost = task_count * infra.total_usd
                total_cost += cost

                # Record for compute backing
                self.compute_backing.record_task(
                    agent_name=agent_name,
                    cost_usd=cost,
                    fi_earned=task_count * 0.01,  # Placeholder F_i rate
                    task_count=task_count,
                )

        margin = total_cost * COMPUTE_GROSS_MARGIN
        return total_cost, margin

    def calculate_fee_revenue(
        self,
        monthly_dex_volume_usd: float,
        monthly_exits_usd: float,
        monthly_creations_usd: float,
    ) -> Tuple[float, float, float]:
        """Calculate fee revenue from DEX/exit/creation.

        Returns:
            (dex_fee_usd, exit_fee_usd, creation_fee_usd)
        """
        dex_fee = monthly_dex_volume_usd * FEE_RATES[FeeType.DEX_TRADE]
        exit_fee = monthly_exits_usd * 0.07  # Average exit fee
        creation_fee = monthly_creations_usd * 0.07  # Average creation fee

        return dex_fee, exit_fee, creation_fee

    def calculate_sustainability(
        self,
        # Subscriber counts
        total_subscribers: int = 25_000,
        total_angels: int = 200,
        # Activity metrics
        tasks_per_month: int = 500_000,
        monthly_dex_volume_usd: float = 50_000,
        monthly_exits_usd: float = 10_000,
        monthly_creations_usd: float = 5_000,
        monthly_opos: int = 5,
        # Optional overrides
        tier_distribution: Dict[str, float] = None,
        agent_mix: Dict[str, float] = None,
    ) -> SustainabilityMetrics:
        """Calculate unified sustainability metrics.

        This combines ALL revenue streams vs burn, not just DEX fees.
        """
        # Stream 1: Fee revenue
        dex_fee, exit_fee, creation_fee = self.calculate_fee_revenue(
            monthly_dex_volume_usd, monthly_exits_usd, monthly_creations_usd
        )

        # Stream 2: Subscription revenue
        sub_gross, sub_margin, paying = self.calculate_subscription_revenue(
            total_subscribers, tier_distribution
        )

        # Stream 3: Angel revenue
        angel_sub, angel_opo = self.calculate_angel_revenue(
            total_angels, monthly_opos
        )

        # Compute revenue
        compute_cost, compute_margin = self.calculate_compute_revenue(
            tasks_per_month, agent_mix
        )

        # Build revenue snapshot
        revenue = RevenueSnapshot(
            fee_dex_usd=dex_fee,
            fee_exit_usd=exit_fee,
            fee_creation_usd=creation_fee,
            subscribers_total=total_subscribers,
            subscribers_paying=paying,
            subscription_revenue_usd=sub_gross,
            subscription_margin_usd=sub_margin,
            angels_total=total_angels,
            angel_revenue_usd=angel_sub,
            angel_opo_fees_usd=angel_opo,
            compute_spend_usd=compute_cost,
            compute_margin_usd=compute_margin,
        )

        # Calculate ratios
        fee_only = revenue.total_fee_revenue_usd
        combined = revenue.total_revenue_usd

        fee_only_ratio = fee_only / self.monthly_burn_usd if self.monthly_burn_usd > 0 else 0
        combined_ratio = combined / self.monthly_burn_usd if self.monthly_burn_usd > 0 else 0

        # ROC-FIRST: Primary sustainability gate (compute productivity)
        # ROC = (V_generated - C_compute) / C_compute
        roc_ratio = compute_margin / compute_cost if compute_cost > 0 else 0.0
        is_compute_positive = roc_ratio > 0  # PRIMARY GATE

        # ROI-PATH: Secondary gate (traditional revenue breakeven)
        margin = combined - self.monthly_burn_usd
        is_roi_sustainable = margin >= 0  # SECONDARY GATE

        # Combined: Both gates must pass for full sustainability
        is_sustainable = is_compute_positive and is_roi_sustainable

        # Runway calculation
        if margin < 0:
            # How many months until reserves depleted?
            # Placeholder: assume 12 months reserve
            reserve_usd = 12 * self.monthly_burn_usd
            months_runway = reserve_usd / abs(margin) if margin != 0 else float('inf')
        else:
            months_runway = float('inf')

        return SustainabilityMetrics(
            revenue=revenue,
            monthly_burn_usd=self.monthly_burn_usd,
            monthly_burn_sats=self.monthly_burn_sats,
            fee_only_ratio=fee_only_ratio,
            combined_ratio=combined_ratio,
            compute_backing=self.compute_backing,
            # ROC-FIRST gates
            is_compute_positive=is_compute_positive,
            is_roi_sustainable=is_roi_sustainable,
            is_sustainable=is_sustainable,
            sustainability_margin_usd=margin,
            months_runway=months_runway,
        )


# ============================================================================
# QUICK COMPARISON
# ============================================================================

def compare_sustainability_models() -> None:
    """Compare fee-only vs unified sustainability."""

    calc = UnifiedSustainabilityCalculator()

    # Scenario: Year 1 baseline
    metrics = calc.calculate_sustainability(
        total_subscribers=25_000,
        total_angels=200,
        tasks_per_month=500_000,
        monthly_dex_volume_usd=50_000,
        monthly_exits_usd=10_000,
        monthly_creations_usd=5_000,
    )

    print("\n" + "=" * 80)
    print("UNIFIED SUSTAINABILITY ANALYSIS")
    print("=" * 80)

    print(f"\n{'BURN':-^40}")
    print(f"  Monthly burn: ${metrics.monthly_burn_usd:,.0f}")

    print(f"\n{'REVENUE STREAMS':-^40}")
    print(f"  DEX fees:      ${metrics.revenue.fee_dex_usd:,.0f}")
    print(f"  Exit fees:     ${metrics.revenue.fee_exit_usd:,.0f}")
    print(f"  Creation fees: ${metrics.revenue.fee_creation_usd:,.0f}")
    print(f"  {'-' * 28}")
    print(f"  Fee subtotal:  ${metrics.revenue.total_fee_revenue_usd:,.0f}")
    print()
    print(f"  Subscriptions: ${metrics.revenue.subscription_margin_usd:,.0f} (margin)")
    print(f"  Angel subs:    ${metrics.revenue.angel_revenue_usd:,.0f}")
    print(f"  Angel OPO:     ${metrics.revenue.angel_opo_fees_usd:,.0f}")
    print(f"  Compute spend: ${metrics.revenue.compute_spend_usd:,.0f}")
    print(f"  Compute value: ${metrics.compute_generated_value_usd:,.0f}")
    print(f"  Compute margin:${metrics.revenue.compute_margin_usd:,.0f}")
    print(f"  {'-' * 28}")
    print(f"  TOTAL:         ${metrics.revenue.total_revenue_usd:,.0f}")

    print(f"\n{'ROC-FIRST SUSTAINABILITY':-^40}")
    print(f"  ROC (ratio):         {metrics.roc_ratio:.4f}")
    print(f"  ROC (percent):       {metrics.return_on_compute_percent:.2f}%")
    print(f"  Is compute positive: {metrics.is_compute_positive} [PRIMARY GATE]")
    print()
    print(f"  ROI-path ratio:      {metrics.combined_ratio:.2f}")
    print(f"  Is ROI sustainable:  {metrics.is_roi_sustainable} [SECONDARY GATE]")
    print()
    print(f"  COMBINED SUSTAINABLE:{metrics.is_sustainable}")
    print(f"  Monthly margin:      ${metrics.sustainability_margin_usd:,.0f}")

    print(f"\n{'COMPUTE BACKING':-^40}")
    print(f"  Total compute spend: ${metrics.compute_backing.total_compute_usd:,.2f}")
    print(f"  Gross compute value: ${metrics.compute_generated_value_usd:,.2f}")
    print(f"  RoC (ratio):         {metrics.return_on_compute_ratio:.4f}")
    print(f"  RoC (percent):       {metrics.return_on_compute_percent:.2f}%")
    print(f"  Value per $1 compute:{metrics.value_per_compute_dollar:.2f}x")
    print(f"  Total tasks:         {metrics.compute_backing.total_tasks_executed:,}")
    print(f"  Compute reserve:     {metrics.compute_backing.compute_reserve_sats:,} sats")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    compare_sustainability_models()
