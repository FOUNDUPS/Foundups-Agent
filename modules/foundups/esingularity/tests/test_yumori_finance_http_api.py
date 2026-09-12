from fastapi.testclient import TestClient

from modules.foundups.esingularity.http_api import app


client = TestClient(app)


def test_finance_health_identifies_python_calculation_authority():
    response = client.get("/esingularity/finance/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["foundup_id"] == "esingularity_001"
    assert body["persistent_mutation"] is False
    assert body["calculation_authority"].endswith("src/yumori_financial_model.py")


def test_catalog_endpoint_exposes_products_benchmarks_and_funding_without_award_inference():
    response = client.get("/esingularity/finance/catalog")
    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["products"] == 14
    assert body["counts"]["market_benchmarks"] >= 7
    assert body["counts"]["funding_opportunities"] >= 4
    assert all(
        item["funding_treatment"] == "POTENTIAL_UNTIL_AWARDED"
        for item in body["funding_opportunities"]
    )


def test_snapshot_endpoint_preserves_default_model_and_does_not_invent_feasibility():
    response = client.get("/esingularity/finance/snapshot")
    assert response.status_code == 200
    body = response.json()
    assert round(body["operating_model"]["summary"]["five_year_revenue_jpy"]) == 5_374_487_296
    assert body["feasibility"]["status"] == "NOT_RUN"


def test_scenario_contract_is_bounded():
    response = client.get("/esingularity/finance/scenario-contract")
    assert response.status_code == 200
    body = response.json()
    assert "pue" in body["scalar_fields"]
    assert "utilization" in body["schedule_fields"]
    assert "tier_prices" in body["structured_fields"]


def test_dynamic_scenario_recalculates_in_python_without_persistence():
    base = client.get("/esingularity/finance/snapshot").json()
    response = client.post(
        "/esingularity/finance/scenario",
        json={"tier_prices": {"tier_a": 500.0}},
    )
    assert response.status_code == 200
    scenario = response.json()
    assert scenario["scenario"]["status"] == "MODEL ONLY / DYNAMIC SCENARIO"
    assert (
        scenario["operating_model"]["years"][0]["gross_revenue_jpy"]
        > base["operating_model"]["years"][0]["gross_revenue_jpy"]
    )


def test_invalid_scenario_returns_422_instead_of_silent_fallback():
    response = client.post(
        "/esingularity/finance/scenario",
        json={"magic_revenue_multiplier": 2},
    )
    assert response.status_code == 422
    assert "Unsupported scenario fields" in response.json()["detail"]
