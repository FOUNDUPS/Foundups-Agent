"""Entry-side anti-manipulation tests for F_i order books."""

from __future__ import annotations

from modules.foundups.simulator.economics.fi_orderbook import (
    EntryProtectionConfig,
    FiOrderBook,
    OrderStatus,
)


def test_buy_rejected_when_notional_exceeds_low_adoption_cap() -> None:
    config = EntryProtectionConfig(
        base_max_order_btc=0.001,  # 100k sats baseline
        max_liquidity_boost=0.0,  # keep cap deterministic for test
    )
    book = FiOrderBook(foundup_id="f_low_adoption", entry_protection_config=config)
    book.update_market_context(adoption_rate=0.05, liquidity_hint_ups=0.0)

    # 100k UPS order notional vs 50k UPS cap at 5% adoption (0.5x scale).
    order, trades = book.place_buy_order(
        human_id="buyer_1",
        price=1000.0,
        quantity=100.0,
    )

    assert order.status == OrderStatus.CANCELLED
    assert order.rejection_reason is not None
    assert order.rejection_reason.startswith("entry_notional_limit_exceeded")
    assert trades == []
    assert book.rejected_buy_orders == 1
    assert len(book.buy_orders) == 0


def test_buy_allowed_when_adoption_matures() -> None:
    config = EntryProtectionConfig(
        base_max_order_btc=0.001,  # 100k sats baseline
        max_liquidity_boost=0.0,
    )
    book = FiOrderBook(foundup_id="f_mature", entry_protection_config=config)
    book.update_market_context(adoption_rate=0.95, liquidity_hint_ups=0.0)

    # Same 100k UPS notional should pass at high adoption (9.5x scale).
    order, trades = book.place_buy_order(
        human_id="buyer_1",
        price=1000.0,
        quantity=100.0,
    )

    assert order.status == OrderStatus.OPEN
    assert order.rejection_reason is None
    assert trades == []
    assert book.rejected_buy_orders == 0
    assert len(book.buy_orders) == 1


def test_depth_impact_guard_blocks_single_order_whale_sweep() -> None:
    config = EntryProtectionConfig(
        base_max_order_btc=10.0,  # disable notional cap as limiting factor
        min_depth_for_impact_guard_ups=100.0,
        max_single_order_share_of_opposing_depth=0.25,
    )
    book = FiOrderBook(foundup_id="f_depth_guard", entry_protection_config=config)
    book.update_market_context(adoption_rate=1.0, liquidity_hint_ups=0.0)

    # Seed opposing depth: 1000 UPS total ask side.
    sell_order, _ = book.place_sell_order(
        human_id="seller_1",
        price=10.0,
        quantity=100.0,
    )
    assert sell_order.status == OrderStatus.OPEN

    # 400 UPS buy order exceeds 25% of opposing depth (cap = 250 UPS).
    whale_buy, trades = book.place_buy_order(
        human_id="buyer_whale",
        price=10.0,
        quantity=40.0,
    )

    assert whale_buy.status == OrderStatus.CANCELLED
    assert whale_buy.rejection_reason is not None
    assert whale_buy.rejection_reason.startswith("depth_impact_limit_exceeded")
    assert trades == []
    assert book.rejected_buy_orders == 1


from copy import deepcopy
import pytest
from modules.foundups.simulator.economics.fi_orderbook import Order, OrderSide


def _b11_book(enabled=True):
    return FiOrderBook("f", entry_protection_config=EntryProtectionConfig(enabled=enabled))


def _b11_place(book, side, human, price, quantity):
    return getattr(book, "place_" + side + "_order")(human, price, quantity)


def _b11_other(side):
    return "sell" if side == "buy" else "buy"


def _b11_metrics(book):
    return (len(book.trades), book.total_volume_fi, book.total_volume_ups, book.total_fees_collected)


@pytest.mark.parametrize("side", ["buy", "sell"])
@pytest.mark.parametrize("enabled", [True, False])
def test_b11_self_cross_cancels_incoming_with_truthful_placement_counters(side, enabled):
    book = _b11_book(enabled)
    maker, _ = _b11_place(book, _b11_other(side), "same", 10, 5)
    maker_before = deepcopy(vars(maker))
    order, trades = _b11_place(book, side, "same", 10, 3)
    assert order.status is OrderStatus.CANCELLED and order.rejection_reason == "self_trade_prevention"
    assert order.filled == 0 and order.remaining == 3 and trades == []
    assert vars(maker) == maker_before and getattr(book, side + "_orders") == []
    assert getattr(book, _b11_other(side) + "_orders") == [maker]
    assert book.all_orders[order.order_id] is order and len(book.all_orders) == 2
    assert maker.order_id != order.order_id and _b11_metrics(book) == (0, 0, 0, 0)
    assert getattr(book, "rejected_" + side + "_orders") == 1
    assert getattr(book, "rejected_" + _b11_other(side) + "_orders") == 0
    assert book.cancel_order(order.order_id) is False


@pytest.mark.parametrize("side", ["buy", "sell"])
def test_b11_partial_external_fills_survive_later_self_cancellation(side):
    book = _b11_book()
    external_price, own_price, incoming_price = (9, 10, 12) if side == "buy" else (11, 10, 8)
    external, _ = _b11_place(book, _b11_other(side), "external", external_price, 2)
    maker, _ = _b11_place(book, _b11_other(side), "same", own_price, 5)
    maker_before = deepcopy(vars(maker))
    order, trades = _b11_place(book, side, "same", incoming_price, 5)
    assert len(trades) == 1 and trades[0].buyer_id != trades[0].seller_id
    total = 2 * (external_price if side == "buy" else incoming_price)
    assert (trades[0].quantity, trades[0].ups_total, trades[0].fee_ups) == pytest.approx((2, total, total * .02))
    assert order.status is OrderStatus.CANCELLED and order.rejection_reason == "self_trade_prevention"
    assert order.filled == 2 and order.remaining == 3 and vars(maker) == maker_before
    assert external.status is OrderStatus.FILLED and external.filled == 2
    assert getattr(book, side + "_orders") == []
    assert getattr(book, _b11_other(side) + "_orders") == [maker]
    assert _b11_metrics(book) == pytest.approx((1, 2, total, total * .02))
    assert getattr(book, "rejected_" + side + "_orders") == 1 and len(book.all_orders) == 3


@pytest.mark.parametrize("side", ["buy", "sell"])
def test_b11_self_best_is_not_skipped_for_worse_external_liquidity(side):
    book = _b11_book()
    own, worse, limit = (10, 11, 12) if side == "buy" else (12, 11, 10)
    maker, _ = _b11_place(book, _b11_other(side), "same", own, 5)
    external, _ = _b11_place(book, _b11_other(side), "external", worse, 5)
    before = deepcopy((vars(maker), vars(external)))
    order, trades = _b11_place(book, side, "same", limit, 3)
    assert order.status is OrderStatus.CANCELLED and trades == []
    assert (vars(maker), vars(external)) == before and _b11_metrics(book) == (0, 0, 0, 0)
    assert getattr(book, side + "_orders") == []


@pytest.mark.parametrize("side", ["buy", "sell"])
def test_b11_noncrossing_self_orders_stay_open(side):
    book = _b11_book()
    own, incoming = (12, 10) if side == "buy" else (8, 10)
    maker, _ = _b11_place(book, _b11_other(side), "same", own, 3)
    order, trades = _b11_place(book, side, "same", incoming, 3)
    assert order.status is OrderStatus.OPEN and order.rejection_reason is None and trades == []
    assert getattr(book, side + "_orders") == [order]
    assert getattr(book, _b11_other(side) + "_orders") == [maker]
    assert book.rejected_buy_orders == book.rejected_sell_orders == 0


@pytest.mark.parametrize("side", ["buy", "sell"])
def test_b11_distinct_case_sensitive_ids_keep_seller_price_and_fee(side):
    book = _b11_book()
    _b11_place(book, _b11_other(side), "owner", 7 if side == "buy" else 9, 3)
    order, trades = _b11_place(book, side, "OWNER", 9 if side == "buy" else 7, 3)
    assert order.status is OrderStatus.FILLED and len(trades) == 1
    trade = trades[0]
    assert trade.buyer_id != trade.seller_id and trade.price == 7
    assert (trade.quantity, trade.ups_total, trade.fee_ups) == pytest.approx((3, 21, .42))
    assert _b11_metrics(book) == pytest.approx((1, 3, 21, .42))
    assert book.rejected_buy_orders == book.rejected_sell_orders == 0


@pytest.mark.parametrize("side", ["buy", "sell"])
def test_b11_repeated_self_attempts_add_only_placement_and_rejection_history(side):
    book = _b11_book(False)
    maker, _ = _b11_place(book, _b11_other(side), "same", 10, 10)
    before = deepcopy(vars(maker))
    orders = [_b11_place(book, side, "same", 10, 1)[0] for _ in range(3)]
    assert all(o.status is OrderStatus.CANCELLED and o.rejection_reason == "self_trade_prevention" for o in orders)
    assert len({o.order_id for o in orders}) == 3 and len(book.all_orders) == 4
    assert vars(maker) == before and _b11_metrics(book) == (0, 0, 0, 0)
    assert getattr(book, "rejected_" + side + "_orders") == 3
    assert getattr(book, side + "_orders") == []


def test_b11_private_execution_rejects_before_any_participating_write():
    book = _b11_book()
    book.place_sell_order("seller", 5, 1)
    book.place_buy_order("buyer", 5, 1)
    buy = Order("manual-buy", "f", "same", OrderSide.BUY, 11, 3, filled=.5)
    sell = Order("manual-sell", "f", "same", OrderSide.SELL, 10, 3, filled=.5)
    before = deepcopy((vars(book), vars(buy), vars(sell)))
    with pytest.raises(ValueError):
        book._execute_trade(buy, sell)
    assert (vars(book), vars(buy), vars(sell)) == before


@pytest.mark.parametrize("side", ["buy", "sell"])
@pytest.mark.parametrize("price,quantity,reason", [(0, 1, "invalid_price_non_positive"), (10, 0, "invalid_quantity_non_positive")])
def test_b11_existing_invalid_entry_reasons_precede_matching(side, price, quantity, reason):
    book = _b11_book(False)
    _b11_place(book, _b11_other(side), "same", 10, 3)
    order, trades = _b11_place(book, side, "same", price, quantity)
    assert order.status is OrderStatus.CANCELLED and order.rejection_reason == reason and trades == []
    assert getattr(book, "rejected_" + side + "_orders") == 1 and _b11_metrics(book) == (0, 0, 0, 0)


@pytest.mark.parametrize("side", ["buy", "sell"])
def test_b11_full_external_fill_does_not_cancel_for_next_own_maker(side):
    book = _b11_book()
    first, own, limit = (9, 10, 12) if side == "buy" else (11, 10, 8)
    _b11_place(book, _b11_other(side), "external", first, 2)
    maker, _ = _b11_place(book, _b11_other(side), "same", own, 5)
    before = deepcopy(vars(maker))
    order, trades = _b11_place(book, side, "same", limit, 2)
    assert order.status is OrderStatus.FILLED and order.rejection_reason is None and len(trades) == 1
    assert vars(maker) == before and getattr(book, "rejected_" + side + "_orders") == 0


@pytest.mark.parametrize("side", ["buy", "sell"])
def test_b11_ordinary_manual_cancellation_still_removes_only_its_order(side):
    book = _b11_book()
    order, _ = _b11_place(book, side, "external", 10, 3)
    assert book.cancel_order(order.order_id) is True
    assert book.cancel_order(order.order_id) is False and order.status is OrderStatus.CANCELLED
    assert order.rejection_reason is None and getattr(book, side + "_orders") == []
    assert book.rejected_buy_orders == book.rejected_sell_orders == 0
