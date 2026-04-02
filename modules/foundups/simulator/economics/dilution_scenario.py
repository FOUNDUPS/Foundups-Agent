"""Du Pool Dilution Scenario Analysis.

Models the core economic question: "What distribution ratios do participants receive?"

PARADIGM: CABR/PoB (not CAGR/ROI)
- Stakers provide LIQUIDITY (energy for UPS capacity)
- BTC → Reserve → Backs UPS → Protocol runs
- Stakers receive F_i DISTRIBUTIONS (protocol mechanics)
- This is PROTOCOL PARTICIPATION, not investment

BOUNDARY NOTE (2026-03-31):
- Du pool stakers = CABR/PoB participation lane (this file)
- I_i holders in investor_staking.py = SEPARATE bonding-curve lane
- Do NOT conflate these two models

Key Questions:
1. At what member count does Du pool distribution become negligible?
2. What's the break-even time (stake cost vs distributions)?
3. How does invite-gated adoption compare to open adoption?

Historical References:
- Gmail (2004): Invite-only for 3 years, ~5 invites/user, created massive FOMO
- Google Wave (2009): 100K invites initially, slow rollout, still failed
- ChatGPT (2022-2023): 100M users in 2 months (NOT gated - pure viral)
- AI tools (2025-2026): Explosive adoption but often gated (Claude, etc.)

The FoundUps model is GATED:
- Genesis members invite new members
- Invite scarcity creates value perception
- But Du pool (4%) is SHARED among all founding members
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum

from .token_economics import sigmoid, adoption_curve


class AdoptionModel(Enum):
    """Different adoption patterns to model."""
    GMAIL_GATED = "gmail"           # Invite-only, slow, high FOMO
    GOOGLE_WAVE = "wave"            # Invite-only but failed (comparison)
    CHATGPT_VIRAL = "chatgpt"       # Mass viral, no gate
    AI_TOOLS_2025 = "ai_2025"       # Current AI wave, mixed gating
    FOUNDUPS_GATED = "foundups"     # Our model: invite-gated + BTC staking


@dataclass
class AdoptionConfig:
    """Configuration for invite-gated adoption model."""

    # Viral mechanics
    invites_per_member: int = 5        # How many invites each member gets
    invite_conversion_rate: float = 0.4  # % of invites that convert
    invite_refresh_epochs: int = 30    # Epochs before new invites granted

    # Time parameters
    epochs_per_month: int = 30         # ~1 epoch/day
    saturation_months: int = 36        # Time to reach max adoption

    # Market size
    total_addressable_market: int = 10_000_000  # TAM for FoundUps
    genesis_cohort_size: int = 100     # Initial genesis members

    # Staking economics
    min_stake_btc: float = 0.001       # Minimum BTC stake
    avg_stake_btc: float = 0.01        # Average BTC stake
    max_stake_btc: float = 0.1         # Maximum BTC stake (whales)


@dataclass
class DilutionSnapshot:
    """Snapshot of Du pool economics at a point in time."""

    epoch: int
    month: float

    # Member counts
    total_members: int
    du_tier_members: int      # <10x earned (80% of Du pool)
    dao_tier_members: int     # 10x-100x earned (16%)
    un_tier_members: int      # >100x earned (4%)

    # F_i minted this epoch
    fi_minted_epoch: float

    # Pool allocations
    du_pool_fi: float         # 4% of fi_minted
    du_tier_share: float      # 80% of du_pool
    individual_share_du: float   # What each du-tier member gets
    individual_share_dao: float  # What each dao-tier member gets
    individual_share_un: float   # What each un-tier member gets

    # Distribution metrics (CABR/PoB paradigm)
    avg_stake_value_btc: float
    cumulative_fi_earned: float
    fi_to_btc_rate: float
    dist_ratio: float         # cumulative_fi_value / stake_cost (distribution ratio)

    @property
    def individual_share_per_1000_fi(self) -> float:
        """Share per 1000 F_i minted (normalized metric)."""
        return (self.individual_share_du / self.fi_minted_epoch * 1000) if self.fi_minted_epoch > 0 else 0


@dataclass
class DilutionScenario:
    """Full dilution scenario over time."""

    name: str
    config: AdoptionConfig
    snapshots: List[DilutionSnapshot] = field(default_factory=list)

    # Calculated metrics (CABR/PoB paradigm)
    break_even_epoch: Optional[int] = None  # When distribution ratio hits 1x
    ten_x_epoch: Optional[int] = None       # When distribution ratio hits 10x
    hundred_x_epoch: Optional[int] = None   # When distribution ratio hits 100x
    max_viable_members: Optional[int] = None  # Where distributions become negligible

    def summary(self) -> Dict:
        """Generate scenario summary."""
        if not self.snapshots:
            return {}

        final = self.snapshots[-1]
        peak_share = max(s.individual_share_du for s in self.snapshots)
        min_share = min(s.individual_share_du for s in self.snapshots if s.individual_share_du > 0)

        return {
            "scenario": self.name,
            "final_members": final.total_members,
            "final_month": final.month,
            "final_individual_share_fi": final.individual_share_du,
            "peak_individual_share_fi": peak_share,
            "min_individual_share_fi": min_share,
            "dilution_factor": peak_share / min_share if min_share > 0 else float("inf"),
            "break_even_epoch": self.break_even_epoch,
            "break_even_months": self.break_even_epoch / self.config.epochs_per_month if self.break_even_epoch else None,
            "ten_x_epoch": self.ten_x_epoch,
            "hundred_x_epoch": self.hundred_x_epoch,
            "final_dist_ratio": final.dist_ratio,
        }


def invite_gated_growth(
    epoch: int,
    current_members: int,
    config: AdoptionConfig,
) -> int:
    """Calculate member growth for invite-gated model.

    Gmail pattern:
    - Each member gets limited invites
    - Invites create FOMO (not everyone can join)
    - Viral coefficient is dampened by invite scarcity

    Args:
        epoch: Current epoch number
        current_members: Current member count
        config: Adoption configuration

    Returns:
        New member count after this epoch
    """
    # Viral coefficient = invites × conversion × (1 / refresh_rate)
    effective_viral = (
        config.invites_per_member *
        config.invite_conversion_rate /
        config.invite_refresh_epochs
    )

    # S-curve dampening - growth slows as we approach saturation
    saturation_ratio = current_members / config.total_addressable_market
    saturation_dampener = 1.0 - sigmoid(saturation_ratio, k=10, x0=0.5)

    # New members this epoch
    new_members = int(current_members * effective_viral * saturation_dampener)

    # Minimum 1 new member until saturation
    if new_members == 0 and saturation_ratio < 0.9:
        new_members = 1

    return current_members + new_members


def calculate_fi_minted(
    epoch: int,
    total_members: int,
    config: AdoptionConfig,
    base_fi_per_epoch: float = 1000.0,
) -> float:
    """Calculate F_i minted this epoch.

    F_i minting scales with:
    - Active work (more members = more work = more minting)
    - But follows S-curve (adoption_curve function)

    Args:
        epoch: Current epoch
        total_members: Current member count
        config: Adoption config
        base_fi_per_epoch: Base F_i rate at full activity

    Returns:
        F_i minted this epoch
    """
    # Adoption score based on member penetration
    adoption_score = min(1.0, total_members / config.total_addressable_market * 10)

    # S-curve release rate
    release_rate = adoption_curve(adoption_score, steepness=8.0)

    # Activity multiplier (more members = more work)
    activity_mult = math.log10(max(10, total_members)) / 4.0  # Log scale

    return base_fi_per_epoch * release_rate * activity_mult


def calculate_tier_distribution(
    total_members: int,
    epoch: int,
    avg_earnings_per_member: float,
) -> Tuple[int, int, int]:
    """Estimate how members distribute across degressive tiers.

    Over time:
    - Early members earn more → move to higher tiers (dao, un)
    - New members start in du tier

    Returns:
        (du_count, dao_count, un_count)
    """
    if total_members <= 10:
        # Very early - everyone in du tier
        return total_members, 0, 0

    # As time passes, early members accumulate and graduate tiers
    # Simplified model: 80% stay du, 15% graduate to dao, 5% to un
    # (In reality this depends on individual earnings)

    # Time factor - more graduation over time
    time_factor = min(1.0, epoch / 360)  # Maxes out at ~1 year

    du_ratio = 0.95 - (0.20 * time_factor)   # 95% → 75%
    dao_ratio = 0.04 + (0.15 * time_factor)  # 4% → 19%
    un_ratio = 0.01 + (0.05 * time_factor)   # 1% → 6%

    du_count = int(total_members * du_ratio)
    dao_count = int(total_members * dao_ratio)
    un_count = total_members - du_count - dao_count

    return max(1, du_count), max(0, dao_count), max(0, un_count)


def run_dilution_scenario(
    name: str,
    config: AdoptionConfig,
    epochs: int = 1080,  # 3 years at 30 epochs/month
    base_fi_per_epoch: float = 1000.0,
    fi_to_btc_rate: float = 0.00001,  # 1 F_i = 0.00001 BTC
) -> DilutionScenario:
    """Run a full dilution scenario simulation.

    Args:
        name: Scenario name
        config: Adoption configuration
        epochs: Total epochs to simulate
        base_fi_per_epoch: Base F_i minting rate
        fi_to_btc_rate: F_i to BTC conversion rate

    Returns:
        Complete scenario with all snapshots
    """
    scenario = DilutionScenario(name=name, config=config)

    # Initial state
    current_members = config.genesis_cohort_size
    cumulative_fi_earned = 0.0
    avg_stake = config.avg_stake_btc

    for epoch in range(1, epochs + 1):
        # Calculate growth
        current_members = invite_gated_growth(epoch, current_members, config)

        # Calculate F_i minted
        fi_minted = calculate_fi_minted(epoch, current_members, config, base_fi_per_epoch)

        # Du pool = 4% of total F_i
        du_pool = fi_minted * 0.04

        # Calculate tier distribution
        du_count, dao_count, un_count = calculate_tier_distribution(
            current_members, epoch, cumulative_fi_earned / max(1, current_members)
        )

        # Calculate individual shares (CRITICAL: divided by count at tier)
        du_tier_share = du_pool * 0.80  # 80% of du pool
        dao_tier_share = du_pool * 0.16  # 16% of du pool
        un_tier_share = du_pool * 0.04   # 4% of du pool

        individual_du = du_tier_share / max(1, du_count)
        individual_dao = dao_tier_share / max(1, dao_count) if dao_count > 0 else 0
        individual_un = un_tier_share / max(1, un_count) if un_count > 0 else 0

        # Update cumulative earnings (average across all members)
        cumulative_fi_earned += individual_du

        # Calculate distribution ratio (CABR/PoB paradigm)
        cumulative_fi_value_btc = cumulative_fi_earned * fi_to_btc_rate
        dist_ratio = cumulative_fi_value_btc / avg_stake if avg_stake > 0 else 0

        # Create snapshot
        snapshot = DilutionSnapshot(
            epoch=epoch,
            month=epoch / config.epochs_per_month,
            total_members=current_members,
            du_tier_members=du_count,
            dao_tier_members=dao_count,
            un_tier_members=un_count,
            fi_minted_epoch=fi_minted,
            du_pool_fi=du_pool,
            du_tier_share=du_tier_share,
            individual_share_du=individual_du,
            individual_share_dao=individual_dao,
            individual_share_un=individual_un,
            avg_stake_value_btc=avg_stake,
            cumulative_fi_earned=cumulative_fi_earned,
            fi_to_btc_rate=fi_to_btc_rate,
            dist_ratio=dist_ratio,
        )
        scenario.snapshots.append(snapshot)

        # Track milestones (distribution ratio thresholds)
        if scenario.break_even_epoch is None and dist_ratio >= 1.0:
            scenario.break_even_epoch = epoch
        if scenario.ten_x_epoch is None and dist_ratio >= 10.0:
            scenario.ten_x_epoch = epoch
        if scenario.hundred_x_epoch is None and dist_ratio >= 100.0:
            scenario.hundred_x_epoch = epoch

    # Calculate max viable members (where individual share drops below 0.01 F_i)
    for snapshot in scenario.snapshots:
        if snapshot.individual_share_du < 0.01:
            scenario.max_viable_members = snapshot.total_members
            break

    return scenario


def compare_adoption_models() -> Dict[str, DilutionScenario]:
    """Compare different adoption models.

    Returns scenarios for:
    1. Gmail-style gated (conservative, high FOMO)
    2. Aggressive AI adoption (2025-2026 wave)
    3. Moderate FoundUps growth
    """
    scenarios = {}

    # Gmail-style: Very conservative, high FOMO
    gmail_config = AdoptionConfig(
        invites_per_member=5,
        invite_conversion_rate=0.3,
        invite_refresh_epochs=60,  # 2 months between invite refreshes
        genesis_cohort_size=100,
        saturation_months=36,
    )
    scenarios["gmail_conservative"] = run_dilution_scenario(
        "Gmail-style (Conservative)", gmail_config
    )

    # AI wave 2025: More aggressive
    ai_config = AdoptionConfig(
        invites_per_member=10,
        invite_conversion_rate=0.5,
        invite_refresh_epochs=14,  # 2 weeks
        genesis_cohort_size=500,
        saturation_months=18,
    )
    scenarios["ai_wave_2025"] = run_dilution_scenario(
        "AI Wave 2025 (Aggressive)", ai_config
    )

    # FoundUps baseline: What we're planning
    foundups_config = AdoptionConfig(
        invites_per_member=5,
        invite_conversion_rate=0.4,
        invite_refresh_epochs=30,  # Monthly
        genesis_cohort_size=100,
        saturation_months=24,
        avg_stake_btc=0.01,
    )
    scenarios["foundups_baseline"] = run_dilution_scenario(
        "FoundUps Baseline", foundups_config
    )

    return scenarios


def print_dilution_analysis(scenarios: Dict[str, DilutionScenario]) -> None:
    """Print comprehensive dilution analysis."""
    print("\n" + "=" * 80)
    print("DU POOL DILUTION ANALYSIS")
    print("=" * 80)

    for name, scenario in scenarios.items():
        summary = scenario.summary()
        print(f"\n### {summary['scenario']}")
        print("-" * 60)

        # Key metrics
        print(f"Final Members: {summary['final_members']:,}")
        print(f"Timeline: {summary['final_month']:.1f} months")
        print(f"Dilution Factor: {summary['dilution_factor']:.1f}x")

        # Individual share trajectory
        print(f"\nIndividual Share (F_i per epoch):")
        print(f"  Peak:  {summary['peak_individual_share_fi']:.4f} F_i")
        print(f"  Final: {summary['final_individual_share_fi']:.6f} F_i")

        # Distribution ratio milestones (CABR/PoB paradigm)
        print(f"\nDistribution Ratio Milestones:")
        if summary['break_even_months']:
            print(f"  1x (break-even): {summary['break_even_months']:.1f} months")
        else:
            print(f"  1x (break-even): NOT REACHED")

        if summary['ten_x_epoch']:
            print(f"  10x: {summary['ten_x_epoch'] / 30:.1f} months")
        else:
            print(f"  10x: NOT REACHED")

        if summary['hundred_x_epoch']:
            print(f"  100x: {summary['hundred_x_epoch'] / 30:.1f} months")
        else:
            print(f"  100x: NOT REACHED")

        print(f"\nFinal Distribution Ratio: {summary['final_dist_ratio']:.2f}x")

        # Key snapshots
        print(f"\nMember Count Trajectory:")
        checkpoints = [30, 90, 180, 360, 720]  # 1mo, 3mo, 6mo, 1yr, 2yr
        for cp in checkpoints:
            if cp < len(scenario.snapshots):
                s = scenario.snapshots[cp - 1]
                print(f"  Month {s.month:5.1f}: {s.total_members:8,} members, "
                      f"share={s.individual_share_du:.6f} F_i")

    print("\n" + "=" * 80)


def analyze_minimum_viable_pool(
    target_ratio: float = 10.0,
    epochs_to_target: int = 360,  # 1 year
    fi_to_btc_rate: float = 0.00001,
    avg_stake_btc: float = 0.01,
) -> Dict:
    """Calculate maximum viable Du pool size for target distribution ratio.

    CABR/PoB paradigm - expresses outcomes as ratios, not returns.

    Given:
    - Target distribution ratio (e.g., 10x)
    - Timeline (e.g., 1 year)
    - F_i/BTC rate
    - Average stake

    Calculate:
    - Maximum members before distributions become negligible
    - Minimum F_i minting rate needed
    """
    # Target: stake * target_ratio = cumulative_fi_earned * fi_to_btc_rate
    # cumulative_fi_earned = (stake * target_ratio) / fi_to_btc_rate
    required_fi_total = (avg_stake_btc * target_ratio) / fi_to_btc_rate

    # Required F_i per epoch = total / epochs
    required_fi_per_epoch = required_fi_total / epochs_to_target

    # Du pool is 4% of minted, du tier gets 80% of that
    # individual_share = (fi_minted * 0.04 * 0.80) / member_count
    # Solving for max_members:
    # member_count = (fi_minted * 0.04 * 0.80) / required_fi_per_epoch

    # Assuming 1000 F_i minted per epoch baseline
    fi_minted_baseline = 1000.0

    max_members = (fi_minted_baseline * 0.04 * 0.80) / required_fi_per_epoch

    return {
        "target_ratio": target_ratio,
        "timeline_months": epochs_to_target / 30,
        "avg_stake_btc": avg_stake_btc,
        "fi_to_btc_rate": fi_to_btc_rate,
        "required_fi_total": required_fi_total,
        "required_fi_per_epoch": required_fi_per_epoch,
        "max_viable_members": int(max_members),
        "recommendation": (
            f"For {target_ratio}x distribution ratio in {epochs_to_target/30:.0f} months, "
            f"Du pool should have max {int(max_members)} members "
            f"(at 1000 F_i/epoch baseline)"
        ),
    }


if __name__ == "__main__":
    # Run analysis
    print("\n" + "=" * 80)
    print("FOUNDUPS DU POOL DILUTION ANALYSIS")
    print("What are the distribution ratios for founding participants?")
    print("=" * 80)

    # Compare adoption models
    scenarios = compare_adoption_models()
    print_dilution_analysis(scenarios)

    # Maximum viable pool analysis
    print("\n" + "=" * 80)
    print("MAXIMUM VIABLE POOL SIZE ANALYSIS")
    print("=" * 80)

    for target_ratio in [2, 5, 10, 100]:
        analysis = analyze_minimum_viable_pool(target_ratio=target_ratio)
        print(f"\n{analysis['recommendation']}")
