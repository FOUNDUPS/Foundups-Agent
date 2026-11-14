"""BTC Reserve - The "Hole in the Bucket" for Bitcoin.

FoundUps is a Bitcoin sink - BTC flows IN but NEVER flows OUT.
BTC gets transformed into UPS backing.

SUBSCRIPTION PAYMENTS (Multi-Crypto):
- Pay in ANY crypto: BTC, ETH, SOL, USDC, etc.
- All crypto converts to BTC → Reserve
- Pay in UPS → BURNS UPS (reduces supply, strengthens currency)

BTC Sources:
1. Subscription payments (any crypto) → Convert to BTC → Reserve
2. Demurrage decay from unused wallet UPS → Reserve
3. Exit fees (11% mined, 5% staked) → Reserve
4. F_i trading fees → Reserve

UPS VALUE MODEL:
- UPS floats with BTC price (not USD-pegged)
- UPS value = (BTC Reserve × BTC Price) / UPS Supply
- Natural contraction when BTC drops, expansion when BTC pumps
- No artificial circuit breaker needed - organic adjustment

Key Insight: The system absorbs Bitcoin and never releases it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from datetime import datetime
from fractions import Fraction
import hashlib
import json
import math
import re

logger = logging.getLogger(__name__)


class BTCSourceType(Enum):
    """Sources of BTC flowing into the reserve."""
    SUBSCRIPTION = "subscription"  # Monthly subscription payments
    SUBSCRIPTION_UPS_BURN = "subscription_ups_burn"  # Subscription paid in UPS (burned)
    DEMURRAGE = "demurrage"  # Decay from unused UPS in wallets
    MINED_EXIT_FEE = "mined_exit_fee"  # 11% fee on mined F_i extraction
    STAKED_EXIT_FEE = "staked_exit_fee"  # 5% fee on staked F_i unstaking
    STAKED_ENTRY_FEE = "staked_entry_fee"  # 3% fee on staking
    TRADING_FEE = "trading_fee"  # Fees from F_i order book
    CASHOUT_FEE = "cashout_fee"  # 7% fee on UPS → external


class PaymentCrypto(Enum):
    """Supported cryptocurrencies for subscription payments."""
    BTC = "btc"
    ETH = "eth"
    SOL = "sol"
    USDC = "usdc"
    USDT = "usdt"
    UPS = "ups"  # Pay with UPS - gets BURNED


@dataclass
class CryptoRates:
    """Current crypto-to-BTC conversion rates (simulated)."""
    # All rates are: 1 unit of crypto = X BTC
    btc_per_eth: float = 0.035  # 1 ETH = 0.035 BTC (~$3,500 ETH, $100K BTC)
    btc_per_sol: float = 0.0015  # 1 SOL = 0.0015 BTC (~$150 SOL)
    btc_per_usdc: float = 0.00001  # 1 USDC = 0.00001 BTC ($1 = 0.00001 BTC at $100K)
    btc_per_usdt: float = 0.00001  # Same as USDC
    btc_usd_price: float = 100000.0  # Current BTC price in USD

    def get_btc_amount(self, crypto: PaymentCrypto, amount: float) -> float:
        """Convert any crypto amount to BTC equivalent."""
        if crypto == PaymentCrypto.BTC:
            return amount
        elif crypto == PaymentCrypto.ETH:
            return amount * self.btc_per_eth
        elif crypto == PaymentCrypto.SOL:
            return amount * self.btc_per_sol
        elif crypto == PaymentCrypto.USDC:
            return amount * self.btc_per_usdc
        elif crypto == PaymentCrypto.USDT:
            return amount * self.btc_per_usdt
        elif crypto == PaymentCrypto.UPS:
            # UPS is valued at current UPS price (floating with BTC)
            # This will be calculated by the reserve itself
            return 0.0  # Handled specially - burns UPS
        return 0.0


@dataclass
class BTCInflow:
    """Record of BTC flowing into the reserve."""
    source: BTCSourceType
    btc_amount: float
    usd_value: float  # USD value at time of inflow
    timestamp: str
    foundup_id: Optional[str] = None  # Which FoundUp (if applicable)
    human_id: Optional[str] = None  # Which human triggered this
    original_crypto: Optional[PaymentCrypto] = None  # What crypto was paid
    original_amount: Optional[float] = None  # Original amount before conversion


@dataclass
class BTCReserve:
    """The Bitcoin Reserve - backs UPS supply.

    Hotel California: BTC checks in, never checks out.

    UPS VALUE MODEL (Floating):
    - UPS value floats with BTC price
- ups_value_usd = (total_btc * btc_usd_price) / total_ups_circulating
    - Natural expansion/contraction with BTC price moves
    """

    # Total BTC in reserve (only grows)
    total_btc: float = 0.0

    # Track by source for analytics
    btc_by_source: Dict[BTCSourceType, float] = field(default_factory=lambda: {
        BTCSourceType.SUBSCRIPTION: 0.0,
        BTCSourceType.SUBSCRIPTION_UPS_BURN: 0.0,
        BTCSourceType.DEMURRAGE: 0.0,
        BTCSourceType.MINED_EXIT_FEE: 0.0,
        BTCSourceType.STAKED_EXIT_FEE: 0.0,
        BTCSourceType.STAKED_ENTRY_FEE: 0.0,
        BTCSourceType.TRADING_FEE: 0.0,
        BTCSourceType.CASHOUT_FEE: 0.0,
    })

    # Track by FoundUp for individual backing
    btc_by_foundup: Dict[str, float] = field(default_factory=dict)

    # Inflow history
    inflows: List[BTCInflow] = field(default_factory=list)

    # UPS supply tracking (canonical)
    total_ups_circulating: float = 0.0
    total_ups_burned: float = 0.0  # Track burns from UPS subscriptions

    # Crypto conversion rates (simulated, updateable)
    crypto_rates: CryptoRates = field(default_factory=CryptoRates)

    # Genesis rate: initial UPS per BTC when system starts
    # After genesis, UPS value floats with reserve
    genesis_ups_per_btc: float = 100000.0  # 1 BTC = 100,000 UPS at genesis

    @property
    def btc_usd_price(self) -> float:
        """Current BTC price in USD."""
        return self.crypto_rates.btc_usd_price

    @btc_usd_price.setter
    def btc_usd_price(self, value: float) -> None:
        """Update BTC price (for simulation)."""
        self.crypto_rates.btc_usd_price = value

    @property
    def ups_value_usd(self) -> float:
        """Current UPS value in USD (floats with BTC).

        UPS value = (BTC Reserve × BTC Price) / UPS Supply
        """
        if self.total_ups_circulating <= 0:
            return 1.0  # Genesis price
        return (self.total_btc * self.btc_usd_price) / self.total_ups_circulating

    @property
    def ups_value_btc(self) -> float:
        """Current UPS value in BTC."""
        if self.total_ups_circulating <= 0:
            return 1.0 / self.genesis_ups_per_btc
        return self.total_btc / self.total_ups_circulating

    @property
    def total_ups_minted(self) -> float:
        """Legacy alias for backward compatibility.

        Canonical term is total_ups_circulating.
        """
        return self.total_ups_circulating

    @total_ups_minted.setter
    def total_ups_minted(self, value: float) -> None:
        self.total_ups_circulating = max(0.0, float(value))

    def receive_btc(
        self,
        btc_amount: float,
        source: BTCSourceType,
        foundup_id: Optional[str] = None,
        human_id: Optional[str] = None,
        original_crypto: Optional[PaymentCrypto] = None,
        original_amount: Optional[float] = None,
    ) -> None:
        """Receive BTC into the reserve. One-way flow.

        This is the Hotel California - BTC enters, never leaves.
        """
        if btc_amount <= 0:
            return

        # Add to total
        self.total_btc += btc_amount

        # Track by source
        self.btc_by_source[source] = self.btc_by_source.get(source, 0.0) + btc_amount

        # Track by FoundUp if applicable
        if foundup_id:
            self.btc_by_foundup[foundup_id] = self.btc_by_foundup.get(foundup_id, 0.0) + btc_amount

        # Record inflow
        inflow = BTCInflow(
            source=source,
            btc_amount=btc_amount,
            usd_value=btc_amount * self.btc_usd_price,
            timestamp=datetime.now().isoformat(),
            foundup_id=foundup_id,
            human_id=human_id,
            original_crypto=original_crypto,
            original_amount=original_amount,
        )
        self.inflows.append(inflow)

        logger.info(
            f"[Reserve] +{btc_amount:.8f} BTC from {source.value} "
            f"(total: {self.total_btc:.8f} BTC = ${self.total_btc * self.btc_usd_price:,.2f})"
        )

    def receive_subscription_payment(
        self,
        usd_amount: float,
        human_id: str,
    ) -> float:
        """Convert subscription USD payment to BTC in reserve.

        Args:
            usd_amount: Subscription price in USD
            human_id: Subscriber

        Returns:
            BTC amount added to reserve
        """
        btc_amount = usd_amount / self.btc_usd_price
        self.receive_btc(
            btc_amount,
            BTCSourceType.SUBSCRIPTION,
            human_id=human_id,
            original_crypto=PaymentCrypto.USDC,  # Treat USD as USDC
            original_amount=usd_amount,
        )
        return btc_amount

    def receive_crypto_subscription(
        self,
        crypto: PaymentCrypto,
        amount: float,
        human_id: str,
    ) -> Tuple[float, bool]:
        """Receive subscription payment in any cryptocurrency.

        Pay with BTC, ETH, SOL, USDC, USDT, or UPS.
        All crypto converts to BTC. UPS gets BURNED (strengthens currency).

        Args:
            crypto: Which cryptocurrency
            amount: Amount of that crypto
            human_id: Subscriber

        Returns:
            (btc_equivalent, was_ups_burned) tuple
        """
        if crypto == PaymentCrypto.UPS:
            # Special case: UPS subscription BURNS the UPS
            return self.receive_ups_subscription(amount, human_id)

        # Convert crypto to BTC
        btc_amount = self.crypto_rates.get_btc_amount(crypto, amount)

        if btc_amount <= 0:
            logger.warning(f"[Reserve] Invalid crypto payment: {amount} {crypto.value}")
            return (0.0, False)

        self.receive_btc(
            btc_amount,
            BTCSourceType.SUBSCRIPTION,
            human_id=human_id,
            original_crypto=crypto,
            original_amount=amount,
        )

        logger.info(
            f"[Reserve] Subscription: {human_id} paid {amount:.4f} {crypto.value} "
            f"= {btc_amount:.8f} BTC"
        )
        return (btc_amount, False)

    def receive_ups_subscription(
        self,
        ups_amount: float,
        human_id: str,
    ) -> Tuple[float, bool]:
        """Receive subscription payment in UPS - BURNS the UPS.

        Paying with UPS is special:
        - UPS gets burned (reduces supply)
        - Backing ratio IMPROVES (same BTC, less UPS)
        - This strengthens the currency for everyone

        Args:
            ups_amount: UPS to burn for subscription
            human_id: Subscriber

        Returns:
            (btc_equivalent, was_ups_burned=True) tuple
        """
        # Calculate BTC equivalent at current UPS value
        btc_equivalent = ups_amount * self.ups_value_btc

        # Burn the UPS (reduce supply, BTC stays)
        self.total_ups_burned += ups_amount
        self.total_ups_circulating = max(0.0, self.total_ups_circulating - ups_amount)

        # Track the burn (no BTC added, but track for analytics)
        self.btc_by_source[BTCSourceType.SUBSCRIPTION_UPS_BURN] = (
            self.btc_by_source.get(BTCSourceType.SUBSCRIPTION_UPS_BURN, 0.0) + btc_equivalent
        )

        # Record as special inflow (BTC equivalent, but actually a burn)
        inflow = BTCInflow(
            source=BTCSourceType.SUBSCRIPTION_UPS_BURN,
            btc_amount=0.0,  # No actual BTC added
            usd_value=ups_amount * self.ups_value_usd,
            timestamp=datetime.now().isoformat(),
            human_id=human_id,
            original_crypto=PaymentCrypto.UPS,
            original_amount=ups_amount,
        )
        self.inflows.append(inflow)

        logger.info(
            f"[Reserve] UPS BURN: {human_id} paid {ups_amount:.2f} UPS "
            f"(burned, new backing ratio: {self.backing_ratio:.2%})"
        )
        return (btc_equivalent, True)

    def process_demurrage(
        self,
        ups_decayed: float,
        human_id: str,
    ) -> float:
        """Process decayed UPS - burns supply, frees BTC capacity.

        HOTEL CALIFORNIA MODEL:
        - BTC is ALREADY in reserve (never leaves)
        - UPS decay = UPS destroyed = supply reduced
        - BTC backing is FREED (not added)
        - Freed capacity strengthens remaining UPS value

        This method:
        1. Burns the decayed UPS (reduces circulating supply)
        2. Returns the BTC capacity freed (for Network/Participation Pool routing)

        Args:
            ups_decayed: Amount of UPS that decayed
            human_id: Whose wallet decayed

        Returns:
            BTC capacity freed (NOT new BTC added - capacity for ecosystem use)
        """
        if ups_decayed <= 0:
            return 0.0

        # Calculate BTC capacity freed (not new BTC - capacity that was backing this UPS)
        btc_capacity_freed = ups_decayed / self.ups_per_btc

        # Burn the UPS (reduces supply, BTC stays locked)
        self.burn_ups(ups_decayed)

        # Track for analytics (but NOT as btc_received - just capacity freed)
        self.btc_by_source[BTCSourceType.DEMURRAGE] = (
            self.btc_by_source.get(BTCSourceType.DEMURRAGE, 0.0) + btc_capacity_freed
        )

        logger.info(
            f"[Reserve] Demurrage: {human_id} UPS burned {ups_decayed:.4f} "
            f"(capacity freed: {btc_capacity_freed:.8f} BTC equivalent, "
            f"new backing ratio: {self.backing_ratio:.2%})"
        )

        return btc_capacity_freed

    def receive_exit_fee(
        self,
        fee_ups: float,
        source: BTCSourceType,
        foundup_id: str,
        human_id: str,
    ) -> float:
        """Convert exit fee to BTC in reserve.

        Exit fees from F_i conversion go to BTC reserve.
        """
        btc_amount = fee_ups / self.ups_per_btc
        self.receive_btc(btc_amount, source, foundup_id=foundup_id, human_id=human_id)
        return btc_amount

    @property
    def ups_per_btc(self) -> float:
        """Current UPS per BTC (floating rate).

        At genesis this equals genesis_ups_per_btc.
        As reserve grows relative to circulating supply, this adjusts.
        """
        if self.total_btc <= 0 or self.total_ups_circulating <= 0:
            return self.genesis_ups_per_btc
        return self.total_ups_circulating / self.total_btc

    @property
    def ups_capacity(self) -> float:
        """Maximum UPS that can be routed at genesis rate.

        Note: With floating UPS, this represents theoretical max if
        we used genesis conversion rate. Actual UPS value floats.
        """
        return self.total_btc * self.genesis_ups_per_btc

    @property
    def ups_remaining(self) -> float:
        """UPS that can still be routed at genesis rate."""
        return max(0.0, self.ups_capacity - self.total_ups_circulating)

    @property
    def backing_ratio(self) -> float:
        """How much of circulating UPS is backed by BTC.

        With floating UPS, this is always 1.0 by definition
        (UPS value adjusts to match backing).
        This metric is kept for monitoring reserve health.
        """
        if self.total_ups_circulating == 0:
            return 1.0
        # In floating model, backing is always 100% by definition
        # But we track the ratio vs genesis rate for health monitoring
        return self.ups_capacity / self.total_ups_circulating

    @property
    def reserve_usd_value(self) -> float:
        """Total USD value of BTC reserve."""
        return self.total_btc * self.btc_usd_price

    def route_ups_from_treasury(self, amount: float) -> float:
        """Route UPS from treasury capacity into circulation.

        Returns:
            Actual routed amount (may be less if insufficient backing capacity)
        """
        routable = min(amount, self.ups_remaining)
        if routable <= 0:
            logger.warning(f"[Reserve] Cannot route {amount:.2f} UPS - insufficient backing")
            return 0.0

        self.total_ups_circulating += routable
        logger.info(
            f"[Reserve] Routed {routable:.2f} UPS "
            f"(circulating: {self.total_ups_circulating:.2f}, backing: {self.backing_ratio:.2%})"
        )
        return routable

    def mint_ups(self, amount: float) -> float:
        """Legacy alias for route_ups_from_treasury()."""
        return self.route_ups_from_treasury(amount)

    def burn_ups(self, amount: float) -> None:
        """Burn UPS (e.g., from demurrage or fees).

        The BTC backing stays in reserve - UPS is destroyed.
        """
        self.total_ups_circulating = max(0.0, self.total_ups_circulating - amount)
        logger.info(
            f"[Reserve] Burned {amount:.2f} UPS "
            f"(remaining: {self.total_ups_circulating:.2f}, backing: {self.backing_ratio:.2%})"
        )

    def get_stats(self) -> Dict:
        """Get reserve statistics."""
        return {
            "total_btc": self.total_btc,
            "btc_usd_price": self.btc_usd_price,
            "reserve_usd_value": self.reserve_usd_value,
            "ups_minted": self.total_ups_circulating,  # legacy key
            "ups_burned": self.total_ups_burned,
            "ups_circulating": self.total_ups_circulating,
            "ups_value_usd": self.ups_value_usd,
            "ups_value_btc": self.ups_value_btc,
            "backing_ratio_vs_genesis": self.backing_ratio,
            "btc_by_source": {k.value: v for k, v in self.btc_by_source.items()},
            "num_foundups_backed": len(self.btc_by_foundup),
            "total_inflows": len(self.inflows),
        }


@dataclass(frozen=True, slots=True)
class SimulatorQuoteSnapshot:
    """Immutable simulator data; construction and identity confer no authority."""
    format_version: int
    interpretation: str
    source_kind: str
    context_id: str
    tick: int
    branch: str
    reserve_btc: Tuple[int, int]
    circulating_ups: Tuple[int, int]
    genesis_ups_per_btc: Tuple[int, int]
    sats_per_ups: Tuple[int, int]
    identity_sha256: str


def _quote_fraction(value):
    if type(value) not in (int, float):
        raise ValueError("quote source must be a built-in number")
    if value < 0 or (type(value) is float and not math.isfinite(value)):
        raise ValueError("quote source must be finite and nonnegative")
    if type(value) is int and value.bit_length() > 1100:
        raise ValueError("quote source exceeds work bound")
    result = Fraction(value) if type(value) is int else Fraction(str(value))
    if max(len(str(result.numerator)), len(str(result.denominator))) > 330:
        raise ValueError("quote source exceeds digit bound")
    return result


def _quote_context(context_id, tick):
    if (type(context_id) is not str or len(context_id) > 128
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", context_id) is None):
        raise ValueError("invalid quote context")
    if type(tick) is not int or not 0 <= tick <= 2**63 - 1:
        raise ValueError("invalid quote tick")


def _quote_identity(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("ascii")
    if len(encoded) > 8192:
        raise ValueError("quote payload exceeds work bound")
    return hashlib.sha256(b"foundups.simulator.reserve-quote.v1\0" + encoded).hexdigest()


def snapshot_simulator_quote(reserve: BTCReserve, *, context_id: str,
                             tick: int) -> SimulatorQuoteSnapshot:
    """Observe host-serialized state using the prospective decimal view.

    This is not atomic across concurrent writes or proof of current funded value.
    """
    if type(reserve) is not BTCReserve:
        raise ValueError("quote requires an exact BTCReserve")
    _quote_context(context_id, tick)
    source = (reserve.total_btc, reserve.total_ups_circulating, reserve.genesis_ups_per_btc)
    if any(type(value) not in (int, float) for value in source):
        raise ValueError("quote source must be a built-in number")
    btc, ups, genesis = (_quote_fraction(value) for value in source)
    if genesis <= 0:
        raise ValueError("quote genesis must be positive")
    if ups == 0:
        branch, quote = "genesis_notional", Fraction(100_000_000) / genesis
    elif btc > 0:
        branch, quote = "reserve_ratio", Fraction(100_000_000) * btc / ups
    else:
        raise ValueError("quote cannot value outstanding UPS with zero reserve")
    quote_pair = (quote.numerator, quote.denominator)
    if max(len(str(value)) for value in quote_pair) > 668:
        raise ValueError("derived quote exceeds digit bound")
    pairs = [(value.numerator, value.denominator) for value in (btc, ups, genesis)]
    payload = dict(format_version=1, interpretation="decimal_view_v1", source_kind="simulator_state",
                   context_id=context_id, tick=tick, branch=branch, reserve_btc=pairs[0],
                   circulating_ups=pairs[1], genesis_ups_per_btc=pairs[2], sats_per_ups=quote_pair)
    return SimulatorQuoteSnapshot(**payload, identity_sha256=_quote_identity(payload))


# Global singleton for the BTC Reserve
_btc_reserve: Optional[BTCReserve] = None


def get_btc_reserve() -> BTCReserve:
    """Get the singleton BTC Reserve instance."""
    global _btc_reserve
    if _btc_reserve is None:
        _btc_reserve = BTCReserve()
    return _btc_reserve


def reset_btc_reserve() -> None:
    """Reset the BTC Reserve (for testing)."""
    global _btc_reserve
    _btc_reserve = None
