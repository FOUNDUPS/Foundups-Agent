"""F_i Token Order Book - Buy/Sell FoundUp Tokens.

When F_i tokens are scarce (tier hasn't unlocked enough) or users want to trade:
- BUY orders: Users bid UPS for F_i tokens
- SELL orders: Users offer F_i tokens for UPS

This is a minimal exchange mechanism:
- All trading fees → BTC Reserve (Hotel California)
- Creates price discovery for each FoundUp's tokens
- Agents earn F_i, but users can also BUY F_i with UPS

Key Flows:
1. Agent mines F_i → gives to human owner
2. Human can SELL F_i on orderbook → gets UPS
3. Other human can BUY F_i with UPS → gets F_i
4. Trading fee → BTC Reserve
"""

from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import heapq

logger = logging.getLogger(__name__)
SATS_PER_BTC: float = 100_000_000.0


class OrderSide(Enum):
    """Order side (buy or sell)."""
    BUY = "buy"  # Bid: offering UPS for F_i
    SELL = "sell"  # Ask: offering F_i for UPS


class OrderStatus(Enum):
    """Order status."""
    OPEN = "open"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass
class EntryProtectionConfig:
    """Anti-manipulation controls for early-stage order books.

    First-principles goal:
    - Keep order sizes proportional to observed adoption/liquidity.
    - Prevent one large order from dominating thin books.
    """

    enabled: bool = True
    base_max_order_btc: float = 0.10  # Baseline max notional at 1.0x scale.
    min_adoption_scale: float = 0.50  # Floor at 5% adoption style startup phase.
    adoption_scale_multiplier: float = 10.0  # 50% adoption -> 5.0x base size.
    max_adoption_scale: float = 10.0  # Hard ceiling from adoption alone.
    liquidity_reference_btc: float = 1.0  # 1 BTC observed liquidity -> +1x scale.
    max_liquidity_boost: float = 4.0  # Max +4x from liquidity.
    min_depth_for_impact_guard_ups: float = 1000.0
    max_single_order_share_of_opposing_depth: float = 0.35


@dataclass
class Order:
    """An order in the F_i orderbook."""

    order_id: str
    foundup_id: str
    human_id: str
    side: OrderSide
    price: float  # UPS per F_i
    quantity: float  # F_i amount
    filled: float = 0.0
    status: OrderStatus = OrderStatus.OPEN
    rejection_reason: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def remaining(self) -> float:
        """Remaining quantity to fill."""
        return self.quantity - self.filled

    def __lt__(self, other: Order) -> bool:
        """For heap ordering: buys by highest price, sells by lowest."""
        if self.side == OrderSide.BUY:
            return self.price > other.price  # Higher bids first
        return self.price < other.price  # Lower asks first


@dataclass
class Trade:
    """A completed trade between buyer and seller."""

    trade_id: str
    foundup_id: str
    buyer_id: str
    seller_id: str
    price: float  # UPS per F_i
    quantity: float  # F_i traded
    ups_total: float  # Total UPS exchanged
    fee_ups: float  # Trading fee in UPS
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FiOrderBook:
    """Order book for a single FoundUp's F_i tokens.

    Matching engine:
    - BUY orders (bids) sorted by highest price first
    - SELL orders (asks) sorted by lowest price first
    - When bid >= ask, trade executes at ask price
    """

    foundup_id: str

    # Order storage
    buy_orders: List[Order] = field(default_factory=list)  # Max-heap by price
    sell_orders: List[Order] = field(default_factory=list)  # Min-heap by price
    all_orders: Dict[str, Order] = field(default_factory=dict)

    # Trade history
    trades: List[Trade] = field(default_factory=list)

    # Trading fee (goes to BTC Reserve)
    trading_fee_rate: float = 0.02  # 2% per trade
    entry_protection_config: EntryProtectionConfig = field(default_factory=EntryProtectionConfig)

    # Statistics
    total_volume_fi: float = 0.0
    total_volume_ups: float = 0.0
    total_fees_collected: float = 0.0
    rejected_buy_orders: int = 0
    rejected_sell_orders: int = 0

    # Market context for dynamic anti-whale sizing.
    market_adoption_rate: float = 0.05
    market_liquidity_hint_ups: float = 0.0

    # Order counter
    _order_counter: int = 0
    _trade_counter: int = 0

    def update_market_context(
        self,
        adoption_rate: Optional[float] = None,
        liquidity_hint_ups: Optional[float] = None,
    ) -> None:
        """Update market context used by entry-side order limits."""
        if adoption_rate is not None:
            self.market_adoption_rate = max(0.0, min(1.0, float(adoption_rate)))
        if liquidity_hint_ups is not None:
            self.market_liquidity_hint_ups = max(0.0, float(liquidity_hint_ups))

    def _opposing_depth_notional_ups(self, side: OrderSide, levels: int = 5) -> float:
        """Estimate opposing-side depth notional for impact guards."""
        if side == OrderSide.BUY:
            opposing_orders = sorted(self.sell_orders)[:levels]
        else:
            opposing_orders = sorted(self.buy_orders, reverse=True)[:levels]
        return sum(max(0.0, o.remaining) * max(0.0, o.price) for o in opposing_orders)

    def _max_buy_notional_ups(self) -> float:
        """Adoption/liquidity-scaled max notional for buy orders."""
        cfg = self.entry_protection_config
        adoption_scale = max(
            cfg.min_adoption_scale,
            min(cfg.max_adoption_scale, self.market_adoption_rate * cfg.adoption_scale_multiplier),
        )
        observed_liquidity_btc = max(
            self.market_liquidity_hint_ups / SATS_PER_BTC,
            self.total_volume_ups / SATS_PER_BTC,
        )
        liquidity_scale = 1.0 + min(
            cfg.max_liquidity_boost,
            observed_liquidity_btc / max(1e-9, cfg.liquidity_reference_btc),
        )
        max_btc = cfg.base_max_order_btc * adoption_scale * liquidity_scale
        return max_btc * SATS_PER_BTC

    def _validate_order(self, side: OrderSide, price: float, quantity: float) -> Optional[str]:
        """Return rejection reason if order violates anti-manipulation controls."""
        if price <= 0:
            return "invalid_price_non_positive"
        if quantity <= 0:
            return "invalid_quantity_non_positive"

        cfg = self.entry_protection_config
        if not cfg.enabled:
            return None

        order_notional_ups = price * quantity

        # Entry-specific guard: throttle oversized BUY notional in low-adoption stages.
        if side == OrderSide.BUY:
            max_buy_notional = self._max_buy_notional_ups()
            if order_notional_ups > max_buy_notional:
                max_btc = max_buy_notional / SATS_PER_BTC
                order_btc = order_notional_ups / SATS_PER_BTC
                return (
                    "entry_notional_limit_exceeded:"
                    f" order={order_btc:.6f}BTC cap={max_btc:.6f}BTC"
                    f" adoption={self.market_adoption_rate:.3f}"
                )

        # Whale impact guard on both sides once meaningful opposing depth exists.
        opposing_depth_ups = self._opposing_depth_notional_ups(side=side)
        if opposing_depth_ups >= cfg.min_depth_for_impact_guard_ups:
            max_impact_notional = opposing_depth_ups * cfg.max_single_order_share_of_opposing_depth
            if order_notional_ups > max_impact_notional:
                return (
                    "depth_impact_limit_exceeded:"
                    f" order={order_notional_ups:.2f}UPS"
                    f" cap={max_impact_notional:.2f}UPS"
                )
        return None

    def place_buy_order(
        self,
        human_id: str,
        price: float,
        quantity: float,
    ) -> Tuple[Order, List[Trade]]:
        """Place a buy order (bid for F_i with UPS).

        Args:
            human_id: Buyer
            price: Max UPS per F_i willing to pay
            quantity: F_i amount wanted

        Returns:
            (order, trades) - The order and any immediate trades
        """
        self._order_counter += 1
        order = Order(
            order_id=f"buy_{self.foundup_id}_{self._order_counter}",
            foundup_id=self.foundup_id,
            human_id=human_id,
            side=OrderSide.BUY,
            price=price,
            quantity=quantity,
        )
        self.all_orders[order.order_id] = order

        rejection = self._validate_order(OrderSide.BUY, price=price, quantity=quantity)
        if rejection:
            order.status = OrderStatus.CANCELLED
            order.rejection_reason = rejection
            self.rejected_buy_orders += 1
            logger.warning(
                f"[OrderBook:{self.foundup_id}] BUY rejected {order.order_id}: {rejection}",
            )
            return (order, [])

        # Try to match against sell orders
        trades = self._match_buy_order(order)

        # If not fully filled, add to book
        if order.remaining > 0 and order.status != OrderStatus.CANCELLED:
            heapq.heappush(self.buy_orders, order)

        logger.info(
            f"[OrderBook:{self.foundup_id}] BUY order {order.order_id}: "
            f"{quantity:.2f} F_i @ {price:.4f} UPS/F_i (filled: {order.filled:.2f})"
        )

        return (order, trades)

    def place_sell_order(
        self,
        human_id: str,
        price: float,
        quantity: float,
    ) -> Tuple[Order, List[Trade]]:
        """Place a sell order (offer F_i for UPS).

        Args:
            human_id: Seller
            price: Min UPS per F_i willing to accept
            quantity: F_i amount offered

        Returns:
            (order, trades) - The order and any immediate trades
        """
        self._order_counter += 1
        order = Order(
            order_id=f"sell_{self.foundup_id}_{self._order_counter}",
            foundup_id=self.foundup_id,
            human_id=human_id,
            side=OrderSide.SELL,
            price=price,
            quantity=quantity,
        )
        self.all_orders[order.order_id] = order

        rejection = self._validate_order(OrderSide.SELL, price=price, quantity=quantity)
        if rejection:
            order.status = OrderStatus.CANCELLED
            order.rejection_reason = rejection
            self.rejected_sell_orders += 1
            logger.warning(
                f"[OrderBook:{self.foundup_id}] SELL rejected {order.order_id}: {rejection}",
            )
            return (order, [])

        # Try to match against buy orders
        trades = self._match_sell_order(order)

        # If not fully filled, add to book
        if order.remaining > 0 and order.status != OrderStatus.CANCELLED:
            heapq.heappush(self.sell_orders, order)

        logger.info(
            f"[OrderBook:{self.foundup_id}] SELL order {order.order_id}: "
            f"{quantity:.2f} F_i @ {price:.4f} UPS/F_i (filled: {order.filled:.2f})"
        )

        return (order, trades)

    def _match_buy_order(self, buy_order: Order) -> List[Trade]:
        """Match a buy order against existing sell orders."""
        trades = []

        while buy_order.remaining > 0 and self.sell_orders:
            best_sell = self.sell_orders[0]

            # Check if prices cross (buyer willing to pay >= seller asking)
            if buy_order.price < best_sell.price:
                break  # No match possible

            if buy_order.human_id == best_sell.human_id:
                buy_order.status = OrderStatus.CANCELLED
                buy_order.rejection_reason = "self_trade_prevention"
                self.rejected_buy_orders += 1
                return trades

            # Execute trade at seller's price
            trade = self._execute_trade(buy_order, best_sell)
            trades.append(trade)

            # Remove filled sell order
            if best_sell.remaining <= 0:
                heapq.heappop(self.sell_orders)
                best_sell.status = OrderStatus.FILLED

        # Update buy order status
        if buy_order.filled >= buy_order.quantity:
            buy_order.status = OrderStatus.FILLED
        elif buy_order.filled > 0:
            buy_order.status = OrderStatus.PARTIAL

        return trades

    def _match_sell_order(self, sell_order: Order) -> List[Trade]:
        """Match a sell order against existing buy orders."""
        trades = []

        while sell_order.remaining > 0 and self.buy_orders:
            best_buy = self.buy_orders[0]

            # Check if prices cross (buyer willing to pay >= seller asking)
            if best_buy.price < sell_order.price:
                break  # No match possible

            if sell_order.human_id == best_buy.human_id:
                sell_order.status = OrderStatus.CANCELLED
                sell_order.rejection_reason = "self_trade_prevention"
                self.rejected_sell_orders += 1
                return trades

            # Execute trade at seller's price (sell_order.price)
            trade = self._execute_trade(best_buy, sell_order)
            trades.append(trade)

            # Remove filled buy order
            if best_buy.remaining <= 0:
                heapq.heappop(self.buy_orders)
                best_buy.status = OrderStatus.FILLED

        # Update sell order status
        if sell_order.filled >= sell_order.quantity:
            sell_order.status = OrderStatus.FILLED
        elif sell_order.filled > 0:
            sell_order.status = OrderStatus.PARTIAL

        return trades

    def _execute_trade(self, buy_order: Order, sell_order: Order) -> Trade:
        """Execute a trade between buy and sell orders."""
        if buy_order.human_id == sell_order.human_id:
            raise ValueError("self-trade is not allowed")
        self._trade_counter += 1

        # Trade quantity is minimum of both remaining
        trade_qty = min(buy_order.remaining, sell_order.remaining)

        # Trade at seller's price
        trade_price = sell_order.price
        ups_total = trade_qty * trade_price

        # Calculate fee
        fee_ups = ups_total * self.trading_fee_rate

        # Update orders
        buy_order.filled += trade_qty
        sell_order.filled += trade_qty

        # Create trade record
        trade = Trade(
            trade_id=f"trade_{self.foundup_id}_{self._trade_counter}",
            foundup_id=self.foundup_id,
            buyer_id=buy_order.human_id,
            seller_id=sell_order.human_id,
            price=trade_price,
            quantity=trade_qty,
            ups_total=ups_total,
            fee_ups=fee_ups,
        )
        self.trades.append(trade)

        # Update statistics
        self.total_volume_fi += trade_qty
        self.total_volume_ups += ups_total
        self.total_fees_collected += fee_ups

        logger.info(
            f"[OrderBook:{self.foundup_id}] TRADE: {trade_qty:.2f} F_i @ {trade_price:.4f} "
            f"({buy_order.human_id} <- {sell_order.human_id}, fee: {fee_ups:.4f})"
        )

        return trade

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        order = self.all_orders.get(order_id)
        if not order or order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            return False

        order.status = OrderStatus.CANCELLED

        # Remove from active orders
        if order.side == OrderSide.BUY:
            self.buy_orders = [o for o in self.buy_orders if o.order_id != order_id]
            heapq.heapify(self.buy_orders)
        else:
            self.sell_orders = [o for o in self.sell_orders if o.order_id != order_id]
            heapq.heapify(self.sell_orders)

        logger.info(f"[OrderBook:{self.foundup_id}] Order {order_id} cancelled")
        return True

    @property
    def best_bid(self) -> Optional[float]:
        """Highest buy price."""
        if not self.buy_orders:
            return None
        return self.buy_orders[0].price

    @property
    def best_ask(self) -> Optional[float]:
        """Lowest sell price."""
        if not self.sell_orders:
            return None
        return self.sell_orders[0].price

    @property
    def spread(self) -> Optional[float]:
        """Bid-ask spread."""
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    @property
    def mid_price(self) -> Optional[float]:
        """Mid-point between bid and ask."""
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2

    def get_order_book_depth(self, levels: int = 5) -> Dict:
        """Get order book depth for display."""
        bids = []
        for order in sorted(self.buy_orders, reverse=True)[:levels]:
            bids.append({"price": order.price, "quantity": order.remaining})

        asks = []
        for order in sorted(self.sell_orders)[:levels]:
            asks.append({"price": order.price, "quantity": order.remaining})

        return {
            "foundup_id": self.foundup_id,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "spread": self.spread,
            "mid_price": self.mid_price,
            "bids": bids,
            "asks": asks,
        }

    def get_stats(self) -> Dict:
        """Get orderbook statistics."""
        return {
            "foundup_id": self.foundup_id,
            "open_buy_orders": len(self.buy_orders),
            "open_sell_orders": len(self.sell_orders),
            "total_trades": len(self.trades),
            "total_volume_fi": self.total_volume_fi,
            "total_volume_ups": self.total_volume_ups,
            "total_fees_collected": self.total_fees_collected,
            "rejected_buy_orders": self.rejected_buy_orders,
            "rejected_sell_orders": self.rejected_sell_orders,
            "market_adoption_rate": self.market_adoption_rate,
            "max_buy_notional_ups": self._max_buy_notional_ups(),
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "spread": self.spread,
        }


class OrderBookManager:
    """Manages order books for all FoundUps."""

    def __init__(
        self,
        trading_fee_rate: float = 0.02,
        entry_protection_config: Optional[EntryProtectionConfig] = None,
    ):
        self.order_books: Dict[str, FiOrderBook] = {}
        self.trading_fee_rate = trading_fee_rate
        self.entry_protection_config = entry_protection_config or EntryProtectionConfig()

    def get_or_create_book(self, foundup_id: str) -> FiOrderBook:
        """Get or create order book for a FoundUp."""
        if foundup_id not in self.order_books:
            self.order_books[foundup_id] = FiOrderBook(
                foundup_id=foundup_id,
                trading_fee_rate=self.trading_fee_rate,
                entry_protection_config=deepcopy(self.entry_protection_config),
            )
        return self.order_books[foundup_id]

    def place_buy(
        self,
        foundup_id: str,
        human_id: str,
        price: float,
        quantity: float,
        adoption_rate: Optional[float] = None,
        liquidity_hint_ups: Optional[float] = None,
    ) -> Tuple[Order, List[Trade]]:
        """Place a buy order for F_i tokens."""
        book = self.get_or_create_book(foundup_id)
        book.update_market_context(
            adoption_rate=adoption_rate,
            liquidity_hint_ups=liquidity_hint_ups,
        )
        return book.place_buy_order(human_id, price, quantity)

    def place_sell(
        self,
        foundup_id: str,
        human_id: str,
        price: float,
        quantity: float,
        adoption_rate: Optional[float] = None,
        liquidity_hint_ups: Optional[float] = None,
    ) -> Tuple[Order, List[Trade]]:
        """Place a sell order for F_i tokens."""
        book = self.get_or_create_book(foundup_id)
        book.update_market_context(
            adoption_rate=adoption_rate,
            liquidity_hint_ups=liquidity_hint_ups,
        )
        return book.place_sell_order(human_id, price, quantity)

    def get_total_fees(self) -> float:
        """Get total trading fees across all books."""
        return sum(book.total_fees_collected for book in self.order_books.values())

    def get_all_stats(self) -> Dict:
        """Get statistics for all order books."""
        return {
            "num_order_books": len(self.order_books),
            "total_fees_collected": self.get_total_fees(),
            "books": {fid: book.get_stats() for fid, book in self.order_books.items()},
        }
