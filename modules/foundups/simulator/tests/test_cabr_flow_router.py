"""Unit tests for CABR treasury flow routing semantics."""

from __future__ import annotations

from dataclasses import replace
import random

import pytest

from modules.foundups.simulator.economics.cabr_flow_router import (
    CABRFlowInputs,
    route_cabr_ups_flow,
)


def test_valve_closed_routes_zero_flow() -> None:
    result = route_cabr_ups_flow(
        CABRFlowInputs(
            treasury_ups_available=1000.0,
            cabr_pipe_size=0.9,
            pob_validated=False,
            requested_ups=100.0,
            release_rate=0.1,
        )
    )
    assert result.valve_open is False
    assert result.routed_ups == 0.0
    assert result.treasury_ups_after == 1000.0


def test_pipe_size_controls_flow_rate() -> None:
    low = route_cabr_ups_flow(
        CABRFlowInputs(
            treasury_ups_available=1000.0,
            cabr_pipe_size=0.25,
            pob_validated=True,
            requested_ups=100.0,
            release_rate=0.1,
        )
    )
    high = route_cabr_ups_flow(
        CABRFlowInputs(
            treasury_ups_available=1000.0,
            cabr_pipe_size=0.75,
            pob_validated=True,
            requested_ups=100.0,
            release_rate=0.1,
        )
    )
    assert high.routed_ups == low.routed_ups * 3


def test_release_budget_caps_flow() -> None:
    result = route_cabr_ups_flow(
        CABRFlowInputs(
            treasury_ups_available=50.0,
            cabr_pipe_size=1.0,
            pob_validated=True,
            requested_ups=1000.0,
            release_rate=0.1,  # 10% of treasury per event
        )
    )
    assert result.epoch_release_budget_ups == 5.0
    assert result.routed_ups == 5.0
    assert result.treasury_ups_after == 45.0


@pytest.mark.parametrize("flag", ["false", "true", 0, 1, None, [], [False], {}])
def test_pob_requires_exact_boolean(flag) -> None:
    """A05: an untrusted truthy payload must not open the allocation valve."""
    with pytest.raises(ValueError):
        route_cabr_ups_flow(CABRFlowInputs(1000.0, 1.0, flag, 100.0))


@pytest.mark.parametrize("field", [
    "treasury_ups_available", "cabr_pipe_size", "requested_ups", "release_rate",
])
@pytest.mark.parametrize("value", [True, "1", None, float("nan"),
                                  float("inf"), float("-inf"), 10**400])
def test_nonfinite_or_coercible_quantity_is_rejected(field, value) -> None:
    inputs = replace(CABRFlowInputs(1000.0, 1.0, True, 100.0), **{field: value})
    with pytest.raises(ValueError):
        route_cabr_ups_flow(inputs)


def test_rejects_custom_scalar_without_invoking_coercion() -> None:
    class Scalar:
        def __float__(self):
            pytest.fail("Untrusted coercion must not execute")
    with pytest.raises(ValueError):
        route_cabr_ups_flow(CABRFlowInputs(1000.0, Scalar(), True, 100.0))


@pytest.mark.parametrize("seed", [0, 7, 3102])
def test_seeded_flow_conserves_treasury_and_preserves_existing_clamps(seed) -> None:
    """Pure calculation property; no proof authentication or funded settlement."""
    rng = random.Random(seed)
    for _ in range(256):
        treasury = rng.uniform(-100.0, 1000000.0)
        requested = rng.uniform(-100.0, 1000000.0)
        pipe, rate = rng.uniform(-1.0, 2.0), rng.uniform(-1.0, 2.0)
        validated = rng.choice([False, True])
        result = route_cabr_ups_flow(CABRFlowInputs(treasury, pipe, validated, requested, rate))
        before = max(0.0, treasury)
        budget = min(max(0.0, requested), before * max(0.0, min(1.0, rate)))
        expected = budget * max(0.0, min(1.0, pipe)) if validated else 0.0
        assert result.routed_ups == expected
        assert result.treasury_ups_after + result.routed_ups == pytest.approx(before)
        assert 0.0 <= result.routed_ups <= before


def test_finite_negative_amounts_keep_existing_zero_clamp() -> None:
    result = route_cabr_ups_flow(CABRFlowInputs(-1, -1, True, -1, -1))
    assert result.treasury_ups_before == result.routed_ups == result.requested_ups == 0
