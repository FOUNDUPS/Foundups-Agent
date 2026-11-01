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

    # Reserve growth must change the value instead of retaining the genesis rate.
    reserve.total_btc = 1.0
    assert reserve.ups_per_btc == 50_000.0
    assert reserve.ups_value_btc == pytest.approx(0.00002)
    assert reserve.ups_value_btc * SATS_PER_BTC == pytest.approx(2000.0)


"""Independent desired reserve-quote acceptance; no future API imported at collection."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict, fields
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
from math import gcd
import pytest
from modules.foundups.simulator.economics import btc_reserve as bm


def _quote(reserve=None, context_id="quote:test", tick=0):
    return bm.snapshot_simulator_quote(bm.BTCReserve() if reserve is None else reserve,
                                       context_id=context_id, tick=tick)


def _payload(snapshot):
    data = asdict(snapshot)
    data.pop("identity_sha256")
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _pair(value):
    rational = Fraction(value) if type(value) is int else Fraction(str(value))
    return rational.numerator, rational.denominator


@pytest.mark.parametrize("vector", [0, 1])
def test_q01_literal_identity_goldens(vector):
    values = [(0, 0, 100000, "golden.reserve-v1:0", 0),
              (0.3, 0.1, 7, "golden.ratio", 17)]
    btc, ups, genesis, context, tick = values[vector]
    snapshot = _quote(bm.BTCReserve(total_btc=btc, total_ups_circulating=ups,
                                   genesis_ups_per_btc=genesis), context, tick)
    expected = ("7f733945065af4b8b1170681b555f62091b6eaf2d17fd20e44b38327ef1d9553",
                "f2e3ae025315df726d477eadbea2c46f9dfc0023bb14ba4a7062053a8d6d80b3")
    assert snapshot.identity_sha256 == expected[vector]
    assert hashlib.sha256(b"foundups.simulator.reserve-quote.v1\0" + _payload(snapshot)).hexdigest() == expected[vector]


@pytest.mark.parametrize("case", ["empty", "notional", "decimal_up", "decimal_down",
    "third", "large_int", "negative_zero", "largest_over_smallest", "smallest_over_largest",
    "source_330_digits", "tiny_over_330_digits"])
def test_q02_exact_formulas_and_reachable_work_envelope(case):
    maximum = float.fromhex("0x1.fffffffffffffp+1023")
    tiny = float.fromhex("0x0.0000000000001p-1022")
    values = {"empty": (0, 0, 100000), "notional": (5, 0, 250),
        "decimal_up": (0.3, 0.1, 7), "decimal_down": (0.1, 0.3, 7),
        "third": (1, 3, 100000), "large_int": (2**53 + 1, 2, 1),
        "negative_zero": (-0.0, 0.0, 100000),
        "largest_over_smallest": (maximum, tiny, maximum),
        "smallest_over_largest": (tiny, maximum, tiny),
        "source_330_digits": (10**330 - 1, tiny, 10**330 - 1),
        "tiny_over_330_digits": (tiny, 10**330 - 1, tiny)}
    btc, ups, genesis = values[case]
    snapshot = _quote(bm.BTCReserve(total_btc=btc, total_ups_circulating=ups,
                                   genesis_ups_per_btc=genesis))
    assert snapshot.reserve_btc == _pair(btc) and snapshot.circulating_ups == _pair(ups)
    assert snapshot.genesis_ups_per_btc == _pair(genesis)
    expected = Fraction(100000000) / Fraction(*_pair(genesis)) if ups == 0 else Fraction(100000000) * Fraction(*_pair(btc)) / Fraction(*_pair(ups))
    assert snapshot.sats_per_ups == (expected.numerator, expected.denominator)
    assert snapshot.branch == ("genesis_notional" if ups == 0 else "reserve_ratio")
    for name in ("reserve_btc", "circulating_ups", "genesis_ups_per_btc", "sats_per_ups"):
        pair = getattr(snapshot, name)
        assert type(pair) is tuple and len(pair) == 2 and all(type(v) is int for v in pair)
        assert pair[0] >= 0 and pair[1] > 0 and gcd(*pair) == 1
        assert max(len(str(abs(v))) for v in pair) <= (668 if name == "sats_per_ups" else 330)
    assert len(_payload(snapshot)) <= 8192


def test_q03_record_is_exact_frozen_slotted_and_detached():
    reserve = bm.BTCReserve(total_btc=1, total_ups_circulating=2)
    snapshot = _quote(reserve)
    assert type(snapshot) is bm.SimulatorQuoteSnapshot and not hasattr(snapshot, "__dict__")
    assert {f.name for f in fields(snapshot)} == {"format_version", "interpretation", "source_kind", "context_id", "tick", "branch", "reserve_btc", "circulating_ups", "genesis_ups_per_btc", "sats_per_ups", "identity_sha256"}
    assert type(snapshot.format_version) is int and snapshot.format_version == 1
    assert snapshot.interpretation == "decimal_view_v1" and snapshot.source_kind == "simulator_state"
    before = asdict(snapshot)
    with pytest.raises((FrozenInstanceError, AttributeError)): snapshot.reserve_btc = (99, 1)
    with pytest.raises(TypeError): snapshot.reserve_btc[0] = 99
    reserve.total_btc = 99
    reserve.btc_by_foundup["later"] = 5
    assert asdict(snapshot) == before


def test_q04_observation_preserves_all_source_state_without_legacy_callbacks(monkeypatch):
    reserve = bm.BTCReserve(total_btc=0.3, total_ups_circulating=0.1)
    reserve.btc_by_foundup["existing"] = 3
    before = deepcopy(vars(reserve))
    def forbidden(*args, **kwargs): raise AssertionError("callback invoked")
    monkeypatch.setattr(bm.BTCReserve, "ups_value_btc", property(forbidden))
    monkeypatch.setattr(bm.BTCReserve, "ups_per_btc", property(forbidden))
    monkeypatch.setattr(bm.BTCReserve, "get_stats", forbidden)
    for name in ("info", "warning", "error", "debug"): monkeypatch.setattr(bm.logger, name, forbidden)
    assert _quote(reserve).sats_per_ups == (300000000, 1)
    assert vars(reserve) == before


@pytest.mark.parametrize("field", ["total_btc", "total_ups_circulating", "genesis_ups_per_btc"])
@pytest.mark.parametrize("kind", ["bool", "negative", "negative_float", "nan", "inf", "string", "decimal",
    "int_subclass", "float_subclass", "hostile", "container", "source_cap_plus_one", "bit_cap_plus_one"])
def test_q05_bad_source_scalars_reject_without_coercion_or_mutation(field, kind):
    calls = []
    def forbidden(*args): calls.append(1); raise AssertionError("coercion hook")
    class IntSubclass(int): __int__ = __index__ = __str__ = forbidden
    class FloatSubclass(float): __float__ = __str__ = forbidden
    class Hostile: __float__ = __int__ = __index__ = __str__ = __lt__ = __gt__ = forbidden
    values = {"bool": True, "negative": -1, "negative_float": -0.1, "nan": float("nan"), "inf": float("inf"),
        "string": "1", "decimal": Decimal("1"), "int_subclass": IntSubclass(1),
        "float_subclass": FloatSubclass(1), "hostile": Hostile(), "container": [],
        "source_cap_plus_one": 10**330, "bit_cap_plus_one": 1 << 1100}
    reserve = bm.BTCReserve(total_btc=1, total_ups_circulating=1)
    setattr(reserve, field, values[kind])
    before = dict(vars(reserve))
    scalar_fields = {"total_btc", "total_ups_circulating", "genesis_ups_per_btc"}
    nested = deepcopy({k: v for k, v in before.items() if k not in scalar_fields})
    with pytest.raises(ValueError): _quote(reserve)
    assert all(vars(reserve)[k] is v for k, v in before.items()) and calls == []
    assert {k: v for k, v in vars(reserve).items() if k not in scalar_fields} == nested


@pytest.mark.parametrize("zero", [0, -0.0])
def test_q06_genesis_must_remain_positive_even_when_not_used(zero):
    reserve = bm.BTCReserve(total_btc=1, total_ups_circulating=1, genesis_ups_per_btc=zero)
    with pytest.raises(ValueError): _quote(reserve)


@pytest.mark.parametrize("kind", ["none", "object", "subclass"])
def test_q07_receiver_exact_type_is_checked_without_hooks(kind):
    calls = []
    class Derived(bm.BTCReserve):
        def __getattribute__(self, name): calls.append(name); raise AssertionError("receiver hook")
    value = {"none": None, "object": object(), "subclass": Derived()}[kind]
    with pytest.raises(ValueError): bm.snapshot_simulator_quote(value, context_id="ok", tick=0)
    assert calls == []


@pytest.mark.parametrize("kind", ["empty", "long", "space", "slash", "newline", "control",
    "unicode", "underscore_first", "none", "bool", "bytes", "subclass"])
def test_q08_context_rejects_exact_type_grammar_and_size_violations(kind):
    calls = []
    class Subclass(str):
        def __str__(self): calls.append(1); raise AssertionError("context hook")
    values = {"empty": "", "long": "a" * 129, "space": "a b", "slash": "a/b",
        "newline": "a\n", "control": "a\x7f", "unicode": "aé", "underscore_first": "_a",
        "none": None, "bool": True, "bytes": b"a", "subclass": Subclass("a")}
    with pytest.raises(ValueError): _quote(context_id=values[kind])
    assert calls == []


@pytest.mark.parametrize("kind", ["bool", "negative", "overflow", "float", "string", "none", "subclass"])
def test_q09_tick_is_bounded_exact_integer_label(kind):
    calls = []
    class Subclass(int):
        def __int__(self): calls.append(1); raise AssertionError("tick hook")
    values = {"bool": True, "negative": -1, "overflow": 2**63, "float": 1.0,
              "string": "1", "none": None, "subclass": Subclass(1)}
    with pytest.raises(ValueError): _quote(tick=values[kind])
    assert calls == []


@pytest.mark.parametrize("context,tick", [("Z", 0), ("A.z_0:-", 2**63 - 1), ("a" * 128, 1)])
def test_q10_valid_observation_label_boundaries(context, tick):
    snapshot = _quote(context_id=context, tick=tick)
    assert snapshot.context_id == context and snapshot.tick == tick


def test_q11_zero_backing_rejects_without_changing_discrepant_legacy_properties():
    reserve = bm.BTCReserve(total_btc=0, total_ups_circulating=1)
    assert reserve.ups_value_btc == 0 and reserve.ups_per_btc == 100000
    before = deepcopy(vars(reserve))
    with pytest.raises(ValueError): _quote(reserve)
    assert vars(reserve) == before
    assert reserve.ups_value_btc == 0 and reserve.ups_per_btc == 100000


@pytest.mark.parametrize("changed", ["context", "tick", "total_btc", "total_ups_circulating", "genesis_ups_per_btc"])
def test_q12_identity_binds_every_source_scalar_and_context(changed):
    reserve = bm.BTCReserve(total_btc=1, total_ups_circulating=2)
    original = _quote(reserve)
    if changed in ("context", "tick"):
        other = _quote(reserve, context_id="different" if changed == "context" else "quote:test",
                       tick=1 if changed == "tick" else 0)
    else:
        setattr(reserve, changed, getattr(reserve, changed) + 1)
        other = _quote(reserve)
    assert other.identity_sha256 != original.identity_sha256


def test_q13_equivalent_decimal_values_repeat_and_unrelated_state_do_not_change_identity():
    reserve = bm.BTCReserve(total_btc=1, total_ups_circulating=2, genesis_ups_per_btc=100000)
    first = _quote(reserve)
    reserve.total_btc, reserve.total_ups_circulating, reserve.genesis_ups_per_btc = 1.0, 2.0, 100000.0
    reserve.btc_usd_price = 1
    reserve.total_ups_burned = 99
    reserve.btc_by_foundup["unrelated"] = 88
    second = _quote(reserve)
    assert asdict(first) == asdict(second) and first is not second


def test_q14_decimal_context_is_not_changed_or_used_to_round_quote():
    with localcontext() as context:
        context.prec, context.Emin, context.Emax = 3, -6, 6
        before = (context.prec, context.Emin, context.Emax, context.rounding, dict(context.flags))
        snapshot = _quote(bm.BTCReserve(total_btc=0.1, total_ups_circulating=0.3))
        assert snapshot.sats_per_ups == (100000000, 3)
        assert (context.prec, context.Emin, context.Emax, context.rounding, dict(context.flags)) == before
