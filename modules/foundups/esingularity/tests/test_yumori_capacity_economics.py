import pytest

from modules.foundups.esingularity.src.yumori_capacity_economics import (
    capacity_economics,
    capacity_economics_table,
)


def test_capacity_table_covers_1_to_5mw_without_capacity_drift():
    rows = capacity_economics_table()
    assert [row.mw for row in rows] == [1, 2, 3, 4, 5]
    assert [row.gpus for row in rows] == [384, 768, 1152, 1536, 1920]
    assert [row.eight_gpu_nodes for row in rows] == [48, 96, 144, 192, 240]


def test_operating_preview_scales_linearly_from_1mw():
    one = capacity_economics(1)
    five = capacity_economics(5)
    assert abs(five.year1_revenue_jpy - one.year1_revenue_jpy * 5) < 0.5
    assert abs(five.year1_operating_cost_jpy - one.year1_operating_cost_jpy * 5) < 0.5
    assert abs(five.year1_ebitda_jpy - one.year1_ebitda_jpy * 5) < 0.5


def test_facility_capex_is_fixed_while_compute_capex_scales():
    one = capacity_economics(1)
    two = capacity_economics(2)
    assert round(one.estimated_project_cost_jpy) == 2_085_000_000
    assert round(two.estimated_project_cost_jpy - one.estimated_project_cost_jpy) == 1_800_000_000


def test_history_comparisons_are_not_presented_as_full_onsen_opex():
    row = capacity_economics(1)
    assert row.historic_fy2018_city_net_cost_coverage_x > 0
    assert row.current_dormant_carrying_cost_coverage_x > 0
    assert "full reopened-onsen OPEX" in row.scaling_rule


def test_invalid_public_capacity_fails_closed():
    with pytest.raises(ValueError, match="1 to 5 MW"):
        capacity_economics(0)
    with pytest.raises(ValueError, match="1 to 5 MW"):
        capacity_economics(6)
