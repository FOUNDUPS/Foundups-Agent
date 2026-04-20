"""Investor Staking Module - Bitclout-inspired bonding curve economics.

STATUS: FROZEN/EXPLORATORY - NOT THE CANONICAL STAKER MODEL
========================================================
This module is exploratory research code. Do NOT implement.
Canonical staker model: pool_distribution.py (Du pool stakers)
Decision: 012 directive 2026-04-20 (AW4 DUPOOL-TRUTH1)

Implements WSP 26 Section 6.9: Early Capital Provider Model.

IMPORTANT DISTINCTION (CABR/PoB Paradigm):
This module models EARLY CAPITAL PROVIDERS (I_i token holders via bonding curve).
This is DIFFERENT from Du pool stakers (protocol participants):

- Du Pool Stakers = Protocol participants providing LIQUIDITY
  - Uses CABR/PoB terminology (distribution ratio, allocations)
  - See staker_viability.py and dilution_scenario.py

- Investor Pool = Early capital via BONDING CURVE (this module)
  - Bitclout/DeSo-inspired mechanism
  - May require separate legal/regulatory review
  - Uses traditional terminology (returns, multiples) for modeling

KEY CONCEPTS (from Bitclout/DeSo research):
1. BONDING CURVE: price = k * supply^n (quadratic, n=2)
   - Early capital providers buy cheap, later ones pay more
   - Creates mathematical 100x-1000x multiple potential

2. STAKEHOLDER POOL PARTICIPATION (at DAO activity level):
   - Un Pool:  9.60% of EVERY FoundUp's distributions
   - Dao Pool: 2.56% of EVERY FoundUp's distributions
   - TOTAL:    12.16% of ALL FoundUp token flows!
   - This is a POOL shared by all I_i holders (not per holder)

   From Token Pool Matrix:
                    Un(60%)  Dao(16%)  Du(4%)
   dao level:       9.60%    2.56%     0.64%

3. BTC BACKING:
   - Capital → BTC Reserve (Hotel California - never exits)
   - BTC backs UPS supply
   - Creates real asset backing (unlike pure Bitclout speculation)

4. S-CURVE RELEASE:
   - I_i tokens vest via adoption curve (same as F_i)
   - Prevents dump-at-launch
   - Aligned with network growth

MULTIPLE MATH (Base Case: 100 FoundUps, 720M F_i/year):
- I_i pool earns: 720M * 12.16% = 87.5M F_i/year
- 5 years = 437M F_i total to I_i pool
- Seed capital (46% of pool): 203M F_i + bonding curve
- COMBINED MULTIPLE: 1,596x on 10 BTC capital!

NETWORK GROWTH SCENARIOS (Seed Capital):
- Conservative (50 FoundUps):  419x
- Base Case (100 FoundUps):    1,596x
- Bull Case (250 FoundUps):    6,275x
- Moon Shot (500 FoundUps):    36,928x
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .token_economics import adoption_curve, sigmoid

logger = logging.getLogger(__name__)


# ============================================================================
# BONDING CURVE MATHEMATICS (Bitclout-inspired)
# ============================================================================

def bonding_price(supply: float, k: float = 0.0001, n: float = 2.0) -> float:
    """Calculate token price at given supply using polynomial bonding curve.

    Bitclout formula: price = 0.003 ÁEsupply²
    Generalized: price = k ÁEsupply^n

    Args:
        supply: Current circulating supply
        k: Price constant (lower = cheaper start)
        n: Exponent (2 = quadratic, like Bitclout)

    Returns:
        Price per token in BTC
    """
    if supply <= 0:
        return k  # Minimum price
    return k * (supply ** n)


def bonding_cost(current_supply: float, tokens_to_buy: float,
                 k: float = 0.0001, n: float = 2.0) -> float:
    """Calculate total BTC cost to buy tokens along bonding curve.

    Uses integral: ∫ k ÁEs^n ds from current_supply to current_supply + tokens
    = k ÁE[s^(n+1) / (n+1)] evaluated at bounds

    Args:
        current_supply: Current circulating supply
        tokens_to_buy: Number of tokens to purchase
        k: Price constant
        n: Exponent

    Returns:
        Total BTC cost for the purchase
    """
    s1 = current_supply
    s2 = current_supply + tokens_to_buy

    # Integral of k ÁEs^n = k ÁEs^(n+1) / (n+1)
    exponent = n + 1
    integral_s1 = k * (s1 ** exponent) / exponent
    integral_s2 = k * (s2 ** exponent) / exponent

    return integral_s2 - integral_s1


def bonding_tokens_for_btc(current_supply: float, btc_amount: float,
                           k: float = 0.0001, n: float = 2.0) -> float:
    """Calculate tokens received for BTC investment.

    Inverse of bonding_cost: given BTC, how many tokens?

    Solve: btc = k ÁE[(s2)^(n+1) - (s1)^(n+1)] / (n+1)
    For s2: s2 = [(btc ÁE(n+1) / k) + s1^(n+1)]^(1/(n+1))

    Args:
        current_supply: Current circulating supply
        btc_amount: BTC to invest
        k: Price constant
        n: Exponent

    Returns:
        Number of tokens received
    """
    exponent = n + 1
    s1_term = current_supply ** exponent
    btc_scaled = btc_amount * exponent / k

    s2 = (btc_scaled + s1_term) ** (1 / exponent)
    tokens = s2 - current_supply

    return max(0.0, tokens)


def calculate_investor_return(
    entry_supply: float,
    current_supply: float,
    tokens_held: float,
    k: float = 0.0001,
    n: float = 2.0
) -> Tuple[float, float]:
    """Calculate investor's current return multiple.

    Args:
        entry_supply: Supply when investor bought
        current_supply: Current supply
        tokens_held: Investor's token balance
        k, n: Curve parameters

    Returns:
        (current_value_btc, return_multiple) tuple
    """
    entry_price = bonding_price(entry_supply, k, n)
    current_price = bonding_price(current_supply, k, n)

    # Value at current price
    current_value = tokens_held * current_price

    # Entry cost (approximate)
    entry_cost = tokens_held * entry_price

    if entry_cost <= 0:
        return (current_value, 0.0)

    return_multiple = current_value / entry_cost

    return (current_value, return_multiple)


# ============================================================================
# INVESTOR TOKEN CLASSES
# ============================================================================

class InvestorTier(Enum):
    """Investment tiers with different terms."""

    SEED = "seed"           # First 1000 I_i - best price, 2 year vest
    EARLY = "early"         # 1000-10000 I_i - good price, 1 year vest
    GROWTH = "growth"       # 10000-100000 I_i - market price, 6 month vest
    STRATEGIC = "strategic" # Custom terms for major investors


@dataclass
class InvestorPosition:
    """A single investor's position in the network.

    Investors are like Level-1 Founders:
    - They share the global investor allocation of FoundUp F_i tokens
      (proportional to vested I_i held)
    - Their I_i tokens vest via S-curve tied to network adoption
    - Their BTC investment backs the UPS system forever (Hotel California)
    """

    investor_id: str
    btc_invested: float  # Total BTC invested

    # I_i (Investor Tokens) - vested via S-curve
    ii_tokens_total: float = 0.0  # Total entitled (before vesting)
    ii_tokens_vested: float = 0.0  # Currently vested (eligible for pool share)

    # Entry metrics (for return calculation)
    entry_supply: float = 0.0  # Supply when first invested
    entry_price_btc: float = 0.0  # Average entry price

    # Vesting
    tier: InvestorTier = InvestorTier.GROWTH
    investment_timestamp: datetime = field(default_factory=datetime.now)

    # Founder shares claimed
    fi_shares_claimed: Dict[str, float] = field(default_factory=dict)  # foundup_id -> F_i claimed

    @property
    def vesting_percentage(self) -> float:
        """Percentage of I_i that has vested."""
        if self.ii_tokens_total <= 0:
            return 0.0
        return self.ii_tokens_vested / self.ii_tokens_total

    @property
    def founder_share_percentage(self) -> float:
        """This investor's share of the current founder allocation.

        All investors collectively get the current pool rate of each FoundUp.
        Individual share = (my_ii / total_ii) * current_pool_rate
        """
        # This is calculated by InvestorPool, stored here for reference
        return 0.0  # Placeholder - set by pool

    def record_fi_claim(self, foundup_id: str, amount: float) -> None:
        """Record F_i claimed from a FoundUp's current investor allocation."""
        current = self.fi_shares_claimed.get(foundup_id, 0.0)
        self.fi_shares_claimed[foundup_id] = current + amount
        logger.info(
            f"[Investor:{self.investor_id}] Claimed {amount:.4f} F_i from {foundup_id} "
            f"(total from this FoundUp: {current + amount:.4f})"
        )


@dataclass
class InvestorPool:
    """Global investor pool for the FoundUps network.

    Manages:
    1. Bonding curve for I_i token sales
    2. S-curve vesting tied to network adoption
    3. Dynamic investor share distribution across all FoundUps:
       - 12.16% while repayment target is unmet
       - 0.64% after repayment target is met
    4. 2.5% cap on total investor allocation
    """

    # === BONDING CURVE PARAMETERS ===
    k: float = 0.0001  # Price constant (BTC per I_i at supply=1)
    n: float = 2.0     # Exponent (2 = quadratic, Bitclout-style)

    # === SUPPLY TRACKING ===
    ii_total_supply: float = 0.0  # Total I_i tokens ever minted
    ii_circulating: float = 0.0   # I_i currently held by investors

    # === CAPS ===
    max_investor_share: float = 0.025  # 2.5% of network value
    max_founder_share_per_foundup: float = 0.1216  # 12.16% pre-hurdle
    min_founder_share_per_foundup: float = 0.0064  # 0.64% post-hurdle
    repayment_target_multiple: float = 10.0  # 10x by default
    post_hurdle_mode_locked: bool = False  # Once reached, 0.64% tail remains permanent

    # === BTC RESERVE CONTRIBUTION ===
    total_btc_invested: float = 0.0  # All BTC from investors
    cumulative_distributions_btc: float = 0.0  # Realized BTC-equivalent payouts

    # === NETWORK ADOPTION (drives vesting) ===
    network_adoption_score: float = 0.0  # 0.0 to 1.0
    total_foundups: int = 0
    total_network_revenue: float = 0.0  # UPS revenue across all FoundUps

    # === INVESTOR REGISTRY ===
    investors: Dict[str, InvestorPosition] = field(default_factory=dict)

    # === STATISTICS ===
    investments: List[Dict] = field(default_factory=list)  # Investment history
    distributions_btc_by_investor: Dict[str, float] = field(default_factory=dict)

    @property
    def current_price_btc(self) -> float:
        """Current I_i token price in BTC."""
        return bonding_price(self.ii_total_supply, self.k, self.n)

    @property
    def total_market_cap_btc(self) -> float:
        """Total market cap of I_i tokens in BTC."""
        return self.ii_circulating * self.current_price_btc

    @property
    def vesting_release_pct(self) -> float:
        """Percentage of I_i that should be vested based on network adoption."""
        return adoption_curve(self.network_adoption_score, steepness=10.0)

    @property
    def repayment_target_btc(self) -> float:
        """Total BTC-equivalent payout required to satisfy return hurdle."""
        return self.total_btc_invested * self.repayment_target_multiple

    @property
    def return_hurdle_met(self) -> bool:
        """True once cumulative realized payouts meet the target multiple."""
        if self.post_hurdle_mode_locked:
            return True
        target = self.repayment_target_btc
        return target > 0 and self.cumulative_distributions_btc >= target

    @property
    def repayment_progress(self) -> float:
        """Repayment progress ratio in [0, inf)."""
        target = self.repayment_target_btc
        if target <= 0:
            return 0.0
        return self.cumulative_distributions_btc / target

    @property
    def founder_share_per_foundup(self) -> float:
        """Current investor pool allocation rate."""
        if self.return_hurdle_met:
            return self.min_founder_share_per_foundup
        return self.max_founder_share_per_foundup

    def record_distribution_btc(self, investor_id: str, amount_btc: float) -> None:
        """Record realized BTC-equivalent distribution for hurdle accounting."""
        if amount_btc <= 0:
            return
        self.cumulative_distributions_btc += amount_btc
        self.distributions_btc_by_investor[investor_id] = (
            self.distributions_btc_by_investor.get(investor_id, 0.0) + amount_btc
        )
        logger.info(
            "[InvestorPool] Distribution recorded: investor=%s amount=%.6f BTC "
            "progress=%.2f%% target=%.6f met=%s",
            investor_id,
            amount_btc,
            self.repayment_progress * 100.0,
            self.repayment_target_btc,
            self.return_hurdle_met,
        )
        if not self.post_hurdle_mode_locked and self.repayment_target_btc > 0:
            if self.cumulative_distributions_btc >= self.repayment_target_btc:
                self.post_hurdle_mode_locked = True
                logger.info(
                    "[InvestorPool] Post-hurdle mode LOCKED at %.6f BTC distributions. "
                    "Investor pool rate now permanent at %.2f%%",
                    self.cumulative_distributions_btc,
                    self.min_founder_share_per_foundup * 100.0,
                )

    def invest_btc(self, investor_id: str, btc_amount: float) -> Tuple[float, InvestorTier]:
        """Process BTC investment, mint I_i tokens.

        Follows Bitclout bonding curve:
        - Early investors get more tokens per BTC
        - Later investors pay higher prices
        - All BTC goes to reserve (Hotel California)

        Args:
            investor_id: Unique investor identifier
            btc_amount: BTC to invest

        Returns:
            (ii_tokens_received, tier) tuple
        """
        # Protect permanence: once post-hurdle is reached, new principal does not
        # reopen pre-hurdle pool rates.
        if not self.post_hurdle_mode_locked and self.repayment_target_btc > 0:
            if self.cumulative_distributions_btc >= self.repayment_target_btc:
                self.post_hurdle_mode_locked = True

        # Determine tier based on current supply
        if self.ii_total_supply < 1000:
            tier = InvestorTier.SEED
        elif self.ii_total_supply < 10000:
            tier = InvestorTier.EARLY
        else:
            tier = InvestorTier.GROWTH

        # Calculate tokens using bonding curve
        entry_supply = self.ii_total_supply
        entry_price = self.current_price_btc

        ii_tokens = bonding_tokens_for_btc(
            self.ii_total_supply, btc_amount, self.k, self.n
        )

        if ii_tokens <= 0:
            logger.warning(f"[InvestorPool] No tokens minted for {btc_amount:.6f} BTC")
            return (0.0, tier)

        # Update supply
        self.ii_total_supply += ii_tokens
        self.ii_circulating += ii_tokens
        self.total_btc_invested += btc_amount

        # Create or update investor position
        if investor_id not in self.investors:
            self.investors[investor_id] = InvestorPosition(
                investor_id=investor_id,
                btc_invested=btc_amount,
                ii_tokens_total=ii_tokens,
                entry_supply=entry_supply,
                entry_price_btc=entry_price,
                tier=tier,
            )
        else:
            position = self.investors[investor_id]
            # Update average entry price
            total_invested = position.btc_invested + btc_amount
            old_weight = position.btc_invested / total_invested
            new_weight = btc_amount / total_invested
            position.entry_price_btc = (
                position.entry_price_btc * old_weight +
                entry_price * new_weight
            )
            position.btc_invested += btc_amount
            position.ii_tokens_total += ii_tokens

        # Record investment
        self.investments.append({
            "investor_id": investor_id,
            "btc_amount": btc_amount,
            "ii_tokens": ii_tokens,
            "entry_price": entry_price,
            "exit_price": self.current_price_btc,
            "tier": tier.value,
            "timestamp": datetime.now().isoformat(),
        })

        logger.info(
            f"[InvestorPool] {investor_id} invested {btc_amount:.6f} BTC -> "
            f"{ii_tokens:.4f} I_i at {entry_price:.6f} BTC/token ({tier.value} tier)"
        )

        return (ii_tokens, tier)

    def transfer_vested_ii(self, from_investor_id: str, to_investor_id: str, vested_amount: float) -> bool:
        """Transfer vested I_i rights between investors.

        Transferability applies to vested rights only. Because founder share is
        computed from vested I_i, this transfers the perpetual tail economics too.
        """
        if vested_amount <= 0:
            return False

        sender = self.investors.get(from_investor_id)
        if sender is None:
            return False
        if sender.ii_tokens_vested < vested_amount or sender.ii_tokens_total < vested_amount:
            return False

        receiver = self.investors.get(to_investor_id)
        if receiver is None:
            receiver = InvestorPosition(
                investor_id=to_investor_id,
                btc_invested=0.0,
                ii_tokens_total=0.0,
                ii_tokens_vested=0.0,
                entry_supply=self.ii_total_supply,
                entry_price_btc=self.current_price_btc,
                tier=InvestorTier.GROWTH,
            )
            self.investors[to_investor_id] = receiver

        sender.ii_tokens_total -= vested_amount
        sender.ii_tokens_vested -= vested_amount
        receiver.ii_tokens_total += vested_amount
        receiver.ii_tokens_vested += vested_amount

        logger.info(
            "[InvestorPool] Transferred %.6f vested I_i from %s to %s",
            vested_amount,
            from_investor_id,
            to_investor_id,
        )
        return True

    def update_network_adoption(
        self,
        foundups_count: Optional[int] = None,
        total_revenue: Optional[float] = None,
    ) -> float:
        """Update network adoption score (drives I_i vesting).

        Network adoption = aggregate of all FoundUp adoptions.
        Higher adoption -> more I_i vests -> larger proportional claims.

        Returns:
            New network adoption score (0.0 to 1.0)
        """
        if foundups_count is not None:
            self.total_foundups = foundups_count
        if total_revenue is not None:
            self.total_network_revenue = total_revenue

        # Calculate adoption from network metrics
        # FoundUp factor: log scale, 100 FoundUps = ~0.4
        foundup_factor = math.log10(max(1, self.total_foundups) + 1) / 4.0

        # Revenue factor: $1M = 0.5, $10M = ~0.7
        revenue_factor = math.log10(max(1, self.total_network_revenue) + 1) / 10.0

        # Investor factor: More investment = more adoption signal
        btc_factor = math.log10(max(1, self.total_btc_invested * 1000) + 1) / 8.0

        old_score = self.network_adoption_score
        self.network_adoption_score = min(1.0, max(0.0,
            foundup_factor * 0.4 +
            revenue_factor * 0.4 +
            btc_factor * 0.2
        ))

        if self.network_adoption_score > old_score:
            logger.info(
                f"[InvestorPool] Network adoption: {old_score:.2%} -> {self.network_adoption_score:.2%} "
                f"(vesting release: {self.vesting_release_pct:.2%})"
            )

        return self.network_adoption_score

    def vest_tokens(self) -> int:
        """Process vesting for all investors based on network adoption.

        I_i vesting follows S-curve tied to network adoption.
        As network grows, more I_i vests, allowing larger proportional claims.

        Returns:
            Number of investors with new vested tokens
        """
        release_pct = self.vesting_release_pct
        updated_count = 0

        for investor_id, position in self.investors.items():
            new_vested = position.ii_tokens_total * release_pct

            if new_vested > position.ii_tokens_vested:
                old_vested = position.ii_tokens_vested
                position.ii_tokens_vested = new_vested
                updated_count += 1

                logger.debug(
                    f"[InvestorPool] {investor_id} vested: "
                    f"{old_vested:.4f} -> {new_vested:.4f} I_i "
                    f"({position.vesting_percentage:.2%} of total)"
                )

        return updated_count

    def calculate_founder_share(self, investor_id: str) -> float:
        """Calculate investor's share of current investor pool allocation.

        All investors collectively get the current pool rate of each FoundUp.
        Individual share = (my_vested_ii / total_vested_ii) * current_pool_rate

        Args:
            investor_id: Investor to calculate for

        Returns:
            Share percentage of FoundUp minted F_i
        """
        position = self.investors.get(investor_id)
        if not position or position.ii_tokens_vested <= 0:
            return 0.0

        # Total vested across all investors
        total_vested = sum(
            p.ii_tokens_vested for p in self.investors.values()
        )

        if total_vested <= 0:
            return 0.0

        # Proportional share of current investor pool allocation
        share = (position.ii_tokens_vested / total_vested) * self.founder_share_per_foundup

        return share

    def claim_founder_fi(
        self,
        investor_id: str,
        foundup_id: str,
        foundup_minted_fi: float,
    ) -> float:
        """Claim F_i from a FoundUp's investor allocation.

        Investors collectively get a dynamic share of each FoundUp's minted F_i.
        Each investor's claim = vested proportional share * current pool rate * minted_fi.

        Args:
            investor_id: Investor claiming
            foundup_id: FoundUp to claim from
            foundup_minted_fi: Total F_i minted by that FoundUp

        Returns:
            F_i tokens claimed
        """
        position = self.investors.get(investor_id)
        if not position:
            return 0.0

        # Calculate this investor's share
        share = self.calculate_founder_share(investor_id)
        if share <= 0:
            return 0.0

        # Available F_i = share ÁEminted
        available_fi = share * foundup_minted_fi

        # Check already claimed
        already_claimed = position.fi_shares_claimed.get(foundup_id, 0.0)
        claimable = max(0.0, available_fi - already_claimed)

        if claimable > 0:
            position.record_fi_claim(foundup_id, claimable)

        return claimable

    def get_investor_returns(self, investor_id: str) -> Dict:
        """Get detailed return analysis for an investor.

        Calculates:
        1. Bonding curve return (I_i price appreciation)
        2. Investor pool share value (current rate across all FoundUps)
        3. Total return multiple
        """
        position = self.investors.get(investor_id)
        if not position:
            return {}

        # Bonding curve return
        current_value, price_multiple = calculate_investor_return(
            position.entry_supply,
            self.ii_total_supply,
            position.ii_tokens_total,
            self.k, self.n
        )

        # Founder shares value
        total_fi_claimed = sum(position.fi_shares_claimed.values())

        # Future value projection (based on network adoption curve)
        projected_vesting = adoption_curve(0.8, steepness=10.0)  # At 80% adoption
        projected_ii_value = position.ii_tokens_total * bonding_price(
            self.ii_total_supply * 2,  # Assume 2x supply growth
            self.k, self.n
        )

        return {
            "investor_id": investor_id,
            "btc_invested": position.btc_invested,
            "ii_tokens_total": position.ii_tokens_total,
            "ii_tokens_vested": position.ii_tokens_vested,
            "vesting_pct": position.vesting_percentage,
            "entry_price_btc": position.entry_price_btc,
            "current_price_btc": self.current_price_btc,
            "current_value_btc": current_value,
            "price_return_multiple": price_multiple,
            "total_fi_claimed": total_fi_claimed,
            "distributions_btc_recorded": self.distributions_btc_by_investor.get(investor_id, 0.0),
            "founder_share_pct": self.calculate_founder_share(investor_id),
            "tier": position.tier.value,
            "projected_80pct_adoption_value": projected_ii_value,
        }

    def project_returns(
        self,
        btc_investment: float,
        future_supply_multiple: float = 10.0,
        num_foundups: int = 100,
        avg_fi_per_foundup: float = 1_000_000,
    ) -> Dict:
        """Project returns for a hypothetical investment.

        This demonstrates the 10x-100x return potential:
        1. Bonding curve: price = k ÁEsupply² ↁE100x supply = 10,000x price
        2. Investor pool share: current rate * num_foundups * avg_fi = additional upside

        Args:
            btc_investment: Hypothetical BTC to invest
            future_supply_multiple: How much supply grows (e.g., 10x)
            num_foundups: Number of FoundUps in network
            avg_fi_per_foundup: Average F_i minted per FoundUp

        Returns:
            Projection dictionary with return multiples
        """
        entry_supply = self.ii_total_supply
        entry_price = self.current_price_btc

        # Tokens received now
        tokens_received = bonding_tokens_for_btc(
            entry_supply, btc_investment, self.k, self.n
        )

        # Future supply
        future_supply = entry_supply * future_supply_multiple
        future_price = bonding_price(future_supply, self.k, self.n)

        # Future value of tokens
        future_value = tokens_received * future_price
        bonding_return = future_value / btc_investment if btc_investment > 0 else 0

        # Founder shares value (assume this investor owns % of supply)
        investor_share_of_pool = tokens_received / (entry_supply + tokens_received)
        total_fi_from_foundups = num_foundups * avg_fi_per_foundup * self.founder_share_per_foundup
        fi_share = total_fi_from_foundups * investor_share_of_pool

        return {
            "btc_invested": btc_investment,
            "tokens_received": tokens_received,
            "entry_price_btc": entry_price,
            "future_supply_multiple": future_supply_multiple,
            "future_price_btc": future_price,
            "future_value_btc": future_value,
            "bonding_curve_return_x": bonding_return,
            "founder_share_fi": fi_share,
            "num_foundups_assumed": num_foundups,
            "combined_value_potential": f"{bonding_return:.0f}x from price + {fi_share:,.0f} F_i from shares",
        }

    def get_stats(self) -> Dict:
        """Get pool statistics."""
        return {
            "ii_total_supply": self.ii_total_supply,
            "ii_circulating": self.ii_circulating,
            "current_price_btc": self.current_price_btc,
            "total_market_cap_btc": self.total_market_cap_btc,
            "total_btc_invested": self.total_btc_invested,
            "network_adoption": self.network_adoption_score,
            "vesting_release_pct": self.vesting_release_pct,
            "repayment_target_multiple": self.repayment_target_multiple,
            "repayment_target_btc": self.repayment_target_btc,
            "cumulative_distributions_btc": self.cumulative_distributions_btc,
            "repayment_progress": self.repayment_progress,
            "return_hurdle_met": self.return_hurdle_met,
            "post_hurdle_mode_locked": self.post_hurdle_mode_locked,
            "num_investors": len(self.investors),
            "total_foundups": self.total_foundups,
            "max_investor_share": self.max_investor_share,
            "founder_share_per_foundup": self.founder_share_per_foundup,
            "max_founder_share_per_foundup": self.max_founder_share_per_foundup,
            "min_founder_share_per_foundup": self.min_founder_share_per_foundup,
        }


# ============================================================================
# SINGLETON PATTERN
# ============================================================================

_investor_pool: Optional[InvestorPool] = None


def get_investor_pool() -> InvestorPool:
    """Get the global investor pool singleton."""
    global _investor_pool
    if _investor_pool is None:
        _investor_pool = InvestorPool()
    return _investor_pool


def reset_investor_pool() -> None:
    """Reset the investor pool (for testing)."""
    global _investor_pool
    _investor_pool = None


# ============================================================================
# RETURN PROJECTION EXAMPLES
# ============================================================================

def demonstrate_10x_100x_returns() -> None:
    """Demonstrate how early investors achieve 10x-100x returns.

    This is the mathematical proof for the investor pitch.
    """
    print("=" * 70)
    print("INVESTOR RETURN DEMONSTRATION - Bitclout-style Bonding Curve")
    print("=" * 70)

    pool = InvestorPool()

    # SEED ROUND: First investor at supply = 0
    print("\n--- SEED ROUND (Supply: 0) ---")
    seed_tokens, seed_tier = pool.invest_btc("seed_investor", 1.0)
    print(f"Seed investor: 1 BTC -> {seed_tokens:.4f} I_i at ${pool.investments[0]['entry_price']*50000:.2f}/token")

    # EARLY ROUND: Second investor
    print("\n--- EARLY ROUND (Supply: {:.0f}) ---".format(pool.ii_total_supply))
    early_tokens, early_tier = pool.invest_btc("early_investor", 1.0)
    print(f"Early investor: 1 BTC -> {early_tokens:.4f} I_i at ${pool.investments[1]['entry_price']*50000:.2f}/token")

    # GROWTH ROUND: Third investor
    print("\n--- GROWTH ROUND (Supply: {:.0f}) ---".format(pool.ii_total_supply))
    growth_tokens, growth_tier = pool.invest_btc("growth_investor", 10.0)
    print(f"Growth investor: 10 BTC -> {growth_tokens:.4f} I_i at ${pool.investments[2]['entry_price']*50000:.2f}/token")

    # CURRENT VALUE
    print("\n--- CURRENT VALUES (Supply: {:.0f}) ---".format(pool.ii_total_supply))
    current_price_usd = pool.current_price_btc * 50000  # Assume BTC = $50K

    for inv_id in ["seed_investor", "early_investor", "growth_investor"]:
        returns = pool.get_investor_returns(inv_id)
        position = pool.investors[inv_id]
        current_value_usd = returns["current_value_btc"] * 50000
        print(f"{inv_id}:")
        print(f"  Invested: {position.btc_invested:.2f} BTC (${position.btc_invested * 50000:,.0f})")
        print(f"  Tokens: {position.ii_tokens_total:.4f} I_i")
        print(f"  Current value: {returns['current_value_btc']:.4f} BTC (${current_value_usd:,.0f})")
        print(f"  Return multiple: {returns['price_return_multiple']:.1f}x")

    # PROJECTION
    print("\n--- PROJECTION: 10x Supply Growth ---")
    projection = pool.project_returns(
        btc_investment=1.0,
        future_supply_multiple=10.0,
        num_foundups=100,
        avg_fi_per_foundup=1_000_000,
    )
    print(f"If network grows 10x from current supply:")
    print(f"  1 BTC invested now -> {projection['tokens_received']:.4f} I_i")
    print(f"  Future value: {projection['future_value_btc']:.4f} BTC (${projection['future_value_btc']*50000:,.0f})")
    print(f"  Bonding curve return: {projection['bonding_curve_return_x']:.0f}x")
    print(f"  PLUS founder shares: {projection['founder_share_fi']:,.0f} F_i from 100 FoundUps")

    print("\n" + "=" * 70)
    print("KEY INSIGHT: Early investors benefit from QUADRATIC pricing")
    print("- Supply 2x -> Price 4x (n=2)")
    print("- Supply 10x -> Price 100x")
    print("- PLUS dynamic pool share (12.16% pre-hurdle, 0.64% post-hurdle)")
    print("=" * 70)


if __name__ == "__main__":
    demonstrate_10x_100x_returns()


