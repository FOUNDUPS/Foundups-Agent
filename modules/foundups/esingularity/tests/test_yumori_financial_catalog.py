import json

import pytest

from modules.foundups.esingularity.src.yumori_financial_catalog import (
    BENCHMARK_SCHEMA_VERSION,
    CATALOG_SCHEMA_VERSION,
    build_public_catalog_snapshot,
    load_catalog,
)


def test_default_catalog_loads_and_has_expected_domains():
    catalog = load_catalog()
    assert catalog.schema_version == CATALOG_SCHEMA_VERSION
    assert catalog.foundup_id == "esingularity_001"
    assert len(catalog.products) == 14
    assert len(catalog.yumori_price_targets) == 3
    assert len(catalog.market_benchmarks) == 16
    assert len(catalog.funding_opportunities) == 4


def test_yumori_prices_remain_model_only_and_external_benchmarks_are_verified():
    catalog = load_catalog()
    assert {target.evidence_status for target in catalog.yumori_price_targets} == {
        "MODEL ONLY"
    }
    assert {benchmark.evidence_status for benchmark in catalog.market_benchmarks} == {
        "VERIFIED"
    }


def test_gpu_products_share_one_exclusive_physical_pool():
    catalog = load_catalog()
    gpu_products = {
        product.id
        for product in catalog.products
        if product.consumes_shared_gpu_pool
    }
    assert {
        "gpu_burst",
        "gpu_reserved",
        "gpu_academic",
        "gpu_private_cluster",
        "managed_inference",
        "training_finetune",
    }.issubset(gpu_products)
    assert "object_storage" not in gpu_products
    assert "heat_offtake" not in gpu_products


def test_sakura_8gpu_benchmark_normalizes_to_373_5_jpy_per_gpu_hour():
    catalog = load_catalog()
    benchmark = next(
        item
        for item in catalog.market_benchmarks
        if item.id == "sakura_dok_h100_8gpu_2026-09-12"
    )
    assert benchmark.price == 2988.0
    assert benchmark.unit == "8-GPU-node-hour"
    assert benchmark.normalized_gpu_hour == 373.5


def test_global_supplement_normalizes_lambda_coreweave_and_gcp_without_fx():
    catalog = load_catalog()
    by_id = {item.id: item for item in catalog.market_benchmarks}
    assert by_id["lambda_h100_sxm_1gpu_2026-09-12"].normalized_gpu_hour == 4.29
    assert by_id["coreweave_hgx_h100_8gpu_2026-09-12"].normalized_gpu_hour == 6.155
    assert by_id["gcp_dws_a3_high_h100_8gpu_2026-09-12"].normalized_gpu_hour == 4.79
    assert by_id["coreweave_internet_transfer_2026-09-12"].price == 0.0
    assert all(
        item.currency == "USD"
        for key, item in by_id.items()
        if key.startswith(("lambda_", "coreweave_", "gcp_"))
    )


def test_public_program_existence_does_not_create_committed_project_funding():
    catalog = load_catalog()
    assert catalog.funding_opportunities
    assert all(
        not opportunity.counts_as_committed_project_funding
        for opportunity in catalog.funding_opportunities
    )
    assert all(
        opportunity.funding_treatment == "POTENTIAL_UNTIL_AWARDED"
        for opportunity in catalog.funding_opportunities
    )


def test_public_snapshot_carries_explicit_accounting_rules():
    snapshot = build_public_catalog_snapshot()
    assert snapshot["counts"]["products"] == 14
    assert snapshot["counts"]["market_benchmarks"] == 16
    assert "not YUMORI revenue" in snapshot["accounting_rules"]["market_benchmark"]
    assert "Only AWARDED/COMMITTED" in snapshot["accounting_rules"]["funding_opportunity"]
    assert "must not be double-counted" in snapshot["accounting_rules"]["gpu_capacity"]
    assert "dated FX source" in snapshot["accounting_rules"]["currency"]


def test_unknown_product_reference_fails_closed(tmp_path):
    source = load_catalog().as_dict()
    source["schema_version"] = CATALOG_SCHEMA_VERSION
    source["market_benchmarks"][0]["product_id"] = "not_a_real_product"
    path = tmp_path / "bad_catalog.json"
    path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")

    empty_supplement = tmp_path / "empty_benchmarks.json"
    empty_supplement.write_text(
        json.dumps(
            {
                "schema_version": BENCHMARK_SCHEMA_VERSION,
                "as_of": "2026-09-12",
                "truth_boundary": "test fixture",
                "market_benchmarks": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown product_id"):
        load_catalog(path, benchmark_supplement_path=empty_supplement)
