"""Price comparison logic for YUMORI model targets vs public market evidence.

This module does not set YUMORI prices and does not convert currencies. It only
compares a MODEL ONLY target to VERIFIED benchmark evidence when the product,
unit basis, and currency permit a direct arithmetic comparison. Cross-currency
rows are returned as ``FX_REQUIRED`` until a dated/source-attributed FX input is
provided by a future market-data adapter.

WSP: 3, 15, 22, 50, 84, 95, 97.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Dict

from .yumori_financial_catalog import FinancialCatalog, MarketBenchmark, load_catalog


def _gpu_hour_basis(benchmark: MarketBenchmark) -> float | None:
    if benchmark.normalized_gpu_hour is not None:
        return benchmark.normalized_gpu_hour
    if benchmark.unit == "GPU-hour":
        return benchmark.price
    return None


def build_price_reconciliation(
    catalog: FinancialCatalog | None = None,
) -> Dict[str, object]:
    """Compare YUMORI GPU-hour targets to eligible public benchmarks.

    A matching currency does not imply equivalent service scope. The output is a
    price ratio only and carries the original benchmark notes/source for context.
    """
    c = catalog or load_catalog()
    rows = []
    for target in c.yumori_price_targets:
        comparisons = []
        for benchmark in c.benchmarks_for_product(target.product_id):
            basis = _gpu_hour_basis(benchmark)
            if basis is None or target.unit != "GPU-hour":
                comparisons.append(
                    {
                        "benchmark": asdict(benchmark),
                        "comparison_status": "UNIT_NOT_COMPARABLE",
                        "target_price": target.price,
                        "target_currency": target.currency,
                        "target_unit": target.unit,
                    }
                )
                continue
            if benchmark.currency != target.currency:
                comparisons.append(
                    {
                        "benchmark": asdict(benchmark),
                        "comparison_status": "FX_REQUIRED",
                        "target_price": target.price,
                        "target_currency": target.currency,
                        "target_unit": target.unit,
                        "benchmark_gpu_hour_basis": basis,
                    }
                )
                continue
            delta = target.price - basis
            delta_pct = delta / basis if basis else None
            comparisons.append(
                {
                    "benchmark": asdict(benchmark),
                    "comparison_status": "DIRECT_PRICE_RATIO_ONLY",
                    "target_price": target.price,
                    "target_currency": target.currency,
                    "target_unit": target.unit,
                    "benchmark_gpu_hour_basis": basis,
                    "absolute_delta": delta,
                    "delta_pct": delta_pct,
                    "target_to_benchmark_ratio": target.price / basis if basis else None,
                    "scope_warning": (
                        "Arithmetic price comparison only. Hardware configuration, "
                        "reservation/availability, CPU/RAM/storage/network, SLA, "
                        "support, tax, and geography may differ."
                    ),
                }
            )
        rows.append(
            {
                "target": asdict(target),
                "comparisons": comparisons,
                "direct_comparison_count": sum(
                    1
                    for comparison in comparisons
                    if comparison["comparison_status"] == "DIRECT_PRICE_RATIO_ONLY"
                ),
                "fx_required_count": sum(
                    1
                    for comparison in comparisons
                    if comparison["comparison_status"] == "FX_REQUIRED"
                ),
            }
        )
    return {
        "as_of": c.as_of,
        "truth_boundary": (
            "YUMORI target prices are MODEL ONLY. VERIFIED external prices are "
            "comparison evidence, not demand validation or a pricing recommendation. "
            "Cross-currency comparison requires a dated/source-attributed FX rate."
        ),
        "targets": rows,
    }
