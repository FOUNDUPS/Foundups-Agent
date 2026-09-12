from modules.foundups.esingularity.src.yumori_facility_history import (
    HISTORY_SCHEMA_VERSION,
    load_facility_history,
)


def test_facility_history_loads_and_reconciles_city_costs():
    history = load_facility_history()
    assert history.schema_version == HISTORY_SCHEMA_VERSION
    assert history.operating_history[-1].period == "FY2018"
    assert history.operating_history[-1].users == 129_649
    assert history.operating_history[-1].user_fee_revenue_jpy == 124_886_000
    assert history.city_fiscal_history[-1].city_net_cost_jpy == 19_615_602


def test_closed_facility_known_carrying_cost_matches_components():
    history = load_facility_history()
    carrying = history.current_carrying_cost
    assert carrying["known_annual_cost_jpy"] == 7_892_646
    assert sum(carrying["components"].values()) == 7_892_646
    assert carrying["land_burden_reference_jpy_per_m2"] == 454.86


def test_reopened_onsen_opex_remains_explicit_evidence_gap():
    history = load_facility_history()
    evidence = history.operator_cost_evidence
    assert evidence["fy2015_personnel_cost_jpy"] == 70_110_000
    assert evidence["full_reopened_onsen_opex_jpy"] is None
    assert "Do not substitute" in evidence["evidence_gap"]
