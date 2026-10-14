"""BTC reserve semantics regression tests.

Ensures canonical UPS naming/behavior:
- total_ups_circulating is canonical
- total_ups_minted remains a backward-compatible alias
- route_ups_from_treasury is canonical routing API
- genesis UPS denomination remains 1,000 sats per UPS
"""

from __future__ import annotations

import pytest

from modules.foundups.simulator.economics.btc_reserve import BTCReserve

SATS_PER_BTC = 100_000_000


def test_route_api_updates_circulating_supply() -> None:
    reserve = BTCReserve(total_btc=1.0, genesis_ups_per_btc=1000.0)
    routed = reserve.route_ups_from_treasury(250.0)
    assert routed == 250.0
    assert reserve.total_ups_circulating == 250.0
    assert reserve.total_ups_minted == 250.0  # legacy alias mirrors canonical


def test_legacy_mint_alias_routes_same_supply() -> None:
    reserve = BTCReserve(total_btc=1.0, genesis_ups_per_btc=1000.0)
    routed = reserve.mint_ups(100.0)
    assert routed == 100.0
    assert reserve.total_ups_circulating == 100.0


def test_legacy_setter_maps_to_canonical_supply() -> None:
    reserve = BTCReserve(total_btc=1.0, genesis_ups_per_btc=1000.0)
    reserve.total_ups_minted = 400.0
    assert reserve.total_ups_circulating == 400.0
    reserve.total_ups_minted = -10.0
    assert reserve.total_ups_circulating == 0.0


def test_stats_expose_both_legacy_and_canonical_keys() -> None:
    reserve = BTCReserve(total_btc=2.0, genesis_ups_per_btc=1000.0)
    reserve.route_ups_from_treasury(300.0)
    stats = reserve.get_stats()
    assert stats["ups_minted"] == 300.0
    assert stats["ups_circulating"] == 300.0


def test_default_genesis_ups_per_btc_matches_tokenomics_docs() -> None:
    reserve = BTCReserve()
    assert reserve.genesis_ups_per_btc == 100_000.0


def test_genesis_ups_value_is_1000_sats() -> None:
    reserve = BTCReserve()
    genesis_ups_value_btc = reserve.ups_value_btc
    genesis_ups_value_sats = genesis_ups_value_btc * SATS_PER_BTC

    assert genesis_ups_value_btc == pytest.approx(0.00001)
    assert genesis_ups_value_sats == pytest.approx(1000.0)


def test_ups_value_btc_floats_after_circulation_exists() -> None:
    reserve = BTCReserve(total_btc=0.5, total_ups_circulating=50_000.0)
    assert reserve.ups_per_btc == 100_000.0
    assert reserve.ups_value_btc == pytest.approx(0.00001)
    assert reserve.ups_value_btc * SATS_PER_BTC == pytest.approx(1000.0)
