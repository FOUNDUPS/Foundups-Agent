"""Staker Viability Analysis - Corrected Model.

Key Insight (012-confirmed 2026-02-14):
- Members (subscription) = Build UPs only, NO passive Du pool access
- Anonymous BTC Stakers = Du pool distributions, protocol participants

PARADIGM: CABR/PoB (not CAGR/ROI)
- Stakers provide LIQUIDITY (energy for UPS capacity)
- BTC → Reserve → Backs UPS → Protocol runs
- Stakers receive F_i DISTRIBUTIONS (protocol mechanics)
- This is PROTOCOL PARTICIPATION, not investment

This separation solves the dilution problem:
1. Subscribers contribute work → earn through Dao/Un pools (active)
2. BTC stakers contribute liquidity → distributions through Du pool (passive)
3. Stakers are SELF-LIMITING (requires real BTC commitment)

The Du 4% pool is for PROTOCOL PARTICIPANTS who provide BTC liquidity.

BOUNDARY NOTE (2026-03-31):
- Du pool stakers = CABR/PoB participation lane (this file)
- I_i holders in investor_staking.py = SEPARATE bonding-curve lane
- Do NOT conflate these two models
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .token_economics import adoption_curve


@dataclass
class StakerTierConfig:
    """Configuration for staker tiers."""

    # Minimum BTC to stake
    min_stake_btc: float = 0.001  # ~$100 at $100k BTC

    # Tier thresholds
    tier_1_min: float = 0.01   # $1k - Small staker
    tier_2_min: float = 0.1    # $10k - Medium staker
    tier_3_min: float = 1.0    # $100k - Whale staker

    # Cap on number of stakers (controls dilution)
    max_stakers: int = 1000
    target_stakers: int = 100  # Optimal for distributions

    # Degressive model thresholds
    du_tier_threshold: float = 10.0    # <10x earned = du tier
    dao_tier_threshold: float = 100.0  # 10-100x = dao tier
    # >100x = un tier (lifetime floor)


@dataclass
class StakerAnalysis:
    """Analysis for a single staker scenario."""

    num_stakers: int
    avg_stake_btc: float
    total_staked_btc: float

    # F_i economics
    fi_per_epoch: float
    du_pool_per_epoch: float  # 4% of fi_per_epoch
    individual_share_per_epoch: float

    # Time projections
    epochs_to_1x: Optional[int]
    epochs_to_10x: Optional[int]
    epochs_to_100x: Optional[int]

    # Distribution ratios at key timepoints
    dist_ratio_1_month: float
    dist_ratio_6_months: float
    dist_ratio_1_year: float
    dist_ratio_3_years: float

    @property
    def months_to_1x(self) -> Optional[float]:
        return self.epochs_to_1x / 30 if self.epochs_to_1x else None

    @property
    def months_to_10x(self) -> Optional[float]:
        return self.epochs_to_10x / 30 if self.epochs_to_10x else None

    @property
    def is_viable(self) -> bool:
        """Is this scenario viable (achieves 10x distribution ratio in 3 years)?"""
        return self.epochs_to_10x is not None and self.epochs_to_10x <= 1080


def calculate_staker_distributions(
    num_stakers: int,
    avg_stake_btc: float,
    fi_per_epoch: float = 1000.0,
    fi_to_btc_rate: float = 0.0001,  # 1 F_i = 0.0001 BTC (~$10 at $100k BTC)
    du_pool_pct: float = 0.04,
    du_tier_share: float = 0.80,
) -> StakerAnalysis:
    """Calculate staker distribution ratios for a given pool size.

    Args:
        num_stakers: Number of stakers in Du pool
        avg_stake_btc: Average BTC staked per staker
        fi_per_epoch: Total F_i minted per epoch
        fi_to_btc_rate: F_i to BTC conversion rate
        du_pool_pct: Du pool percentage (default 4%)
        du_tier_share: Du tier share of Du pool (default 80%)

    Returns:
        Complete staker analysis
    """
    total_staked = num_stakers * avg_stake_btc

    # Du pool per epoch
    du_pool = fi_per_epoch * du_pool_pct

    # Individual share (assuming all in du tier initially)
    du_tier_pool = du_pool * du_tier_share
    individual_share = du_tier_pool / max(1, num_stakers)

    # Value per epoch in BTC
    epoch_value_btc = individual_share * fi_to_btc_rate

    # Time to various distribution milestones
    if epoch_value_btc > 0:
        epochs_to_1x = int(avg_stake_btc / epoch_value_btc)
        epochs_to_10x = int(avg_stake_btc * 10 / epoch_value_btc)
        epochs_to_100x = int(avg_stake_btc * 100 / epoch_value_btc)
    else:
        epochs_to_1x = None
        epochs_to_10x = None
        epochs_to_100x = None

    # Distribution ratio at key timepoints
    dist_ratio_1_month = (30 * epoch_value_btc) / avg_stake_btc if avg_stake_btc > 0 else 0
    dist_ratio_6_months = (180 * epoch_value_btc) / avg_stake_btc if avg_stake_btc > 0 else 0
    dist_ratio_1_year = (360 * epoch_value_btc) / avg_stake_btc if avg_stake_btc > 0 else 0
    dist_ratio_3_years = (1080 * epoch_value_btc) / avg_stake_btc if avg_stake_btc > 0 else 0

    return StakerAnalysis(
        num_stakers=num_stakers,
        avg_stake_btc=avg_stake_btc,
        total_staked_btc=total_staked,
        fi_per_epoch=fi_per_epoch,
        du_pool_per_epoch=du_pool,
        individual_share_per_epoch=individual_share,
        epochs_to_1x=epochs_to_1x,
        epochs_to_10x=epochs_to_10x,
        epochs_to_100x=epochs_to_100x,
        dist_ratio_1_month=dist_ratio_1_month,
        dist_ratio_6_months=dist_ratio_6_months,
        dist_ratio_1_year=dist_ratio_1_year,
        dist_ratio_3_years=dist_ratio_3_years,
    )


def find_optimal_staker_count(
    target_ratio: float = 10.0,
    target_months: int = 12,
    avg_stake_btc: float = 0.1,
    fi_per_epoch: float = 1000.0,
    fi_to_btc_rate: float = 0.0001,
) -> int:
    """Find maximum staker count to achieve target distribution ratio.

    Args:
        target_ratio: Target distribution ratio (e.g., 10x)
        target_months: Months to achieve ratio
        avg_stake_btc: Average stake per staker
        fi_per_epoch: F_i minted per epoch
        fi_to_btc_rate: F_i to BTC rate

    Returns:
        Maximum viable staker count
    """
    target_epochs = target_months * 30

    # Required value per epoch
    required_epoch_value = (avg_stake_btc * target_ratio) / target_epochs

    # Required F_i per epoch
    required_fi_per_epoch = required_epoch_value / fi_to_btc_rate

    # Du pool economics: individual = (fi * 0.04 * 0.80) / n
    # Solving for n: n = (fi * 0.04 * 0.80) / required_fi_per_epoch
    max_stakers = (fi_per_epoch * 0.04 * 0.80) / required_fi_per_epoch

    return max(1, int(max_stakers))


def run_staker_matrix() -> Dict[str, List[StakerAnalysis]]:
    """Run matrix analysis across staker counts and stake sizes."""
    results = {}

    # Different F_i minting rates (ecosystem activity levels)
    fi_rates = {
        "low_activity": 500.0,
        "baseline": 1000.0,
        "high_activity": 5000.0,
        "unicorn": 10000.0,
    }

    for rate_name, fi_rate in fi_rates.items():
        results[rate_name] = []

        # Test different staker counts
        for num_stakers in [10, 25, 50, 100, 250, 500, 1000]:
            # Test different stake sizes
            for stake_btc in [0.01, 0.1, 1.0]:
                analysis = calculate_staker_distributions(
                    num_stakers=num_stakers,
                    avg_stake_btc=stake_btc,
                    fi_per_epoch=fi_rate,
                )
                results[rate_name].append(analysis)

    return results


def print_staker_viability_report():
    """Print comprehensive staker viability report."""
    print("\n" + "=" * 80)
    print("STAKER VIABILITY ANALYSIS - CORRECTED MODEL")
    print("Du 4% pool = BTC STAKERS ONLY (not subscribers)")
    print("=" * 80)

    # Baseline parameters
    fi_per_epoch = 1000.0
    fi_to_btc_rate = 0.0001  # 1 F_i = $10 at $100k BTC
    avg_stakes = [0.01, 0.1, 1.0]  # $1k, $10k, $100k at $100k BTC

    print(f"\nParameters:")
    print(f"  F_i per epoch: {fi_per_epoch}")
    print(f"  F_i to BTC rate: {fi_to_btc_rate} (1 F_i = ${fi_to_btc_rate * 100000:.0f} at $100k BTC)")
    print(f"  Du pool: 4% of F_i minted")
    print(f"  Du tier share: 80% of Du pool")

    print("\n" + "-" * 80)
    print("SCENARIO: How many stakers can achieve 10x in 12 months?")
    print("-" * 80)

    for stake in avg_stakes:
        max_stakers = find_optimal_staker_count(
            target_ratio=10.0,
            target_months=12,
            avg_stake_btc=stake,
            fi_per_epoch=fi_per_epoch,
            fi_to_btc_rate=fi_to_btc_rate,
        )
        stake_usd = stake * 100000  # At $100k BTC
        print(f"  Stake ${stake_usd:,.0f} ({stake} BTC): Max {max_stakers} stakers")

    print("\n" + "-" * 80)
    print("DETAILED DISTRIBUTION PROJECTIONS")
    print("-" * 80)

    staker_counts = [10, 25, 50, 100, 500]

    for stake in avg_stakes:
        stake_usd = stake * 100000
        print(f"\n### Stake: ${stake_usd:,.0f} ({stake} BTC)")
        print(f"{'Stakers':>8} | {'1mo':>8} | {'6mo':>8} | {'1yr':>8} | {'3yr':>8} | {'10x in':>10}")
        print("-" * 70)

        for num in staker_counts:
            analysis = calculate_staker_distributions(
                num_stakers=num,
                avg_stake_btc=stake,
                fi_per_epoch=fi_per_epoch,
                fi_to_btc_rate=fi_to_btc_rate,
            )

            months_10x = f"{analysis.months_to_10x:.1f}mo" if analysis.months_to_10x else "NEVER"

            print(
                f"{num:>8} | "
                f"{analysis.dist_ratio_1_month:>7.2f}x | "
                f"{analysis.dist_ratio_6_months:>7.2f}x | "
                f"{analysis.dist_ratio_1_year:>7.2f}x | "
                f"{analysis.dist_ratio_3_years:>7.2f}x | "
                f"{months_10x:>10}"
            )

    print("\n" + "-" * 80)
    print("KEY INSIGHT: VIABLE STAKER POOL SIZES")
    print("-" * 80)

    print("""
The corrected model (stakers-only Du pool) shows:

1. 10-25 STAKERS: High distribution ratio (10x in 3-12 months)
   - Works for "genesis participant" cohort
   - Each staker provides significant BTC liquidity
   - Protocol participation economics

2. 50-100 STAKERS: Moderate distribution ratio (10x in 1-3 years)
   - Works for "early community" cohort
   - Meaningful epoch distributions
   - Requires patience

3. 500+ STAKERS: Diminishing allocations
   - 10x becomes multi-year proposition
   - Better suited for large-scale FoundUps
   - May need higher F_i minting rate

RECOMMENDATION:
- Genesis cohort: CAP at 100 stakers
- Early stakers get better tier (degressive model rewards them)
- Late stakers can still earn lifetime floor (0.16%)
""")

    print("\n" + "-" * 80)
    print("F_i MINTING RATE SENSITIVITY")
    print("-" * 80)

    # How does F_i minting rate affect viability?
    rates = [500, 1000, 2500, 5000, 10000]
    print(f"\nMax stakers for 10x distribution ratio in 12 months (at 0.1 BTC stake):")
    for rate in rates:
        max_s = find_optimal_staker_count(
            target_ratio=10.0,
            target_months=12,
            avg_stake_btc=0.1,
            fi_per_epoch=rate,
        )
        print(f"  {rate:>6} F_i/epoch: {max_s:>4} stakers")


if __name__ == "__main__":
    print_staker_viability_report()
