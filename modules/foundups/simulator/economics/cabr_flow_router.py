"""CABR flow router for UPS treasury distribution.

Canonical model:
- UPS already exists in treasury (sats-backed accounting unit)
- CABR score is pipe size (0.0-1.0 flow-rate control)
- PoB validation is the valve (closed => zero flow)

No UPS is minted here. This module only routes existing UPS.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


DEFAULT_RELEASE_RATE = 0.02


@dataclass(frozen=True)
class CABRFlowInputs:
    """Inputs for one treasury flow decision."""

    treasury_ups_available: float
    cabr_pipe_size: float
    pob_validated: bool
    requested_ups: float
    release_rate: float = DEFAULT_RELEASE_RATE


@dataclass(frozen=True)
class CABRFlowResult:
    """Computed flow result for one routing decision."""

    valve_open: bool
    cabr_pipe_size: float
    treasury_ups_before: float
    treasury_ups_after: float
    epoch_release_budget_ups: float
    requested_ups: float
    routed_ups: float


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def route_cabr_ups_flow(inputs: CABRFlowInputs) -> CABRFlowResult:
    """Route UPS from treasury using CABR pipe-size + PoB valve semantics.

    Math:
      epoch_budget = min(requested_ups, treasury_ups_available * release_rate)
      routed_ups = epoch_budget * cabr_pipe_size, if valve open, else 0

    Requires finite built-in numeric inputs and an exact boolean PoB decision.
    This calculation does not authenticate the decision or consume Treasury funds.
    """

    if type(inputs.pob_validated) is not bool:
        raise ValueError("PoB validation must be a boolean")
    # Preserve the existing signed finite clamps; the nonnegative token helper
    # intentionally has a different admission contract.
    for value in (inputs.treasury_ups_available, inputs.cabr_pipe_size,
                  inputs.requested_ups, inputs.release_rate):
        if type(value) not in (int, float):
            raise ValueError("CABR inputs must be finite built-in numbers")
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError("CABR inputs must be finite built-in numbers")

    treasury_before = max(0.0, float(inputs.treasury_ups_available))
    pipe_size = _clamp(float(inputs.cabr_pipe_size), 0.0, 1.0)
    release_rate = _clamp(float(inputs.release_rate), 0.0, 1.0)
    requested = max(0.0, float(inputs.requested_ups))
    valve_open = inputs.pob_validated

    epoch_budget = min(requested, treasury_before * release_rate)
    routed = epoch_budget * pipe_size if valve_open else 0.0
    routed = min(routed, treasury_before)
    treasury_after = max(0.0, treasury_before - routed)

    return CABRFlowResult(
        valve_open=valve_open,
        cabr_pipe_size=pipe_size,
        treasury_ups_before=treasury_before,
        treasury_ups_after=treasury_after,
        epoch_release_budget_ups=epoch_budget,
        requested_ups=requested,
        routed_ups=routed,
    )
