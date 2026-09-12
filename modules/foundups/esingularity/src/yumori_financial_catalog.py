"""Governed market, product, and public-funding catalog for YUMORI finance.

This module is evidence/configuration adjacent to the canonical calculation engines:

- ``yumori_financial_model.py`` owns operating/P&L equations.
- ``yumori_feasibility_finance.py`` owns customer/offtake and funding-gate equations.
- this module owns normalized product definitions, public market benchmarks,
  model-only YUMORI price targets, and public-funding opportunity metadata.

The catalog is repository data, not a second financial engine.  External facts may
be VERIFIED while project pricing/funding remains MODEL ONLY or POTENTIAL.
Generated Excel/website/JSON surfaces consume this contract; they do not become
calculation authority.

WSP: 3, 15, 22, 50, 84, 95, 97, 109.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Dict, Iterable, Mapping, Sequence, Tuple

CATALOG_SCHEMA_VERSION = "yumori.finance.catalog.v1"
DEFAULT_CATALOG_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "finance" / "catalog_v1.json"
)

_ALLOWED_EVIDENCE = {"VERIFIED", "COMMITTED", "POTENTIAL", "MODEL ONLY"}
_ALLOWED_FUNDING_TREATMENT = {
    "POTENTIAL_UNTIL_AWARDED",
    "AWARDED",
    "COMMITTED",
    "MODEL_ONLY",
}
_ALLOWED_CAPACITY_ACCOUNTING = {
    "EXCLUSIVE_GPU_POOL",
    "EXCLUSIVE_GPU_POOL_PLUS_SERVICE",
    "CPU_POOL",
    "STORAGE_POOL",
    "NETWORK_POOL",
    "ADDITIVE_SERVICE",
    "FACILITY_POWER_SPACE",
    "THERMAL_COPRODUCT",
}


@dataclass(frozen=True)
class ProductOffering:
    id: str
    name_en: str
    name_ja: str
    category: str
    billing_units: Tuple[str, ...]
    capacity_accounting: str
    customer_types: Tuple[str, ...]
    description: str

    @property
    def consumes_shared_gpu_pool(self) -> bool:
        return self.capacity_accounting.startswith("EXCLUSIVE_GPU_POOL")


@dataclass(frozen=True)
class PriceTarget:
    id: str
    product_id: str
    price: float
    currency: str
    unit: str
    evidence_status: str
    source_ref: str
    notes: str


@dataclass(frozen=True)
class MarketBenchmark:
    id: str
    provider: str
    market: str
    product_id: str
    description: str
    hardware: str
    price: float
    currency: str
    unit: str
    normalized_gpu_hour: float | None
    tax_included: bool
    effective_or_checked_date: str
    evidence_status: str
    source_url: str
    notes: str


@dataclass(frozen=True)
class FundingOpportunity:
    id: str
    kind: str
    program_name: str
    agency: str
    jurisdiction: str
    lifecycle: str
    open_date: str
    deadlines: Tuple[str, ...]
    subsidy_rate_text: str
    cap_text: str
    eligibility_summary: str
    yumori_relevance: str
    blockers_or_gates: str
    funding_treatment: str
    evidence_status: str
    checked_date: str
    source_url: str
    detail_url: str

    @property
    def counts_as_committed_project_funding(self) -> bool:
        return self.funding_treatment in {"AWARDED", "COMMITTED"}


@dataclass(frozen=True)
class FinancialCatalog:
    schema_version: str
    foundup_id: str
    as_of: str
    truth_boundary: str
    products: Tuple[ProductOffering, ...]
    yumori_price_targets: Tuple[PriceTarget, ...]
    market_benchmarks: Tuple[MarketBenchmark, ...]
    funding_opportunities: Tuple[FundingOpportunity, ...]

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)

    def product_map(self) -> Mapping[str, ProductOffering]:
        return {product.id: product for product in self.products}

    def benchmarks_for_product(self, product_id: str) -> Tuple[MarketBenchmark, ...]:
        return tuple(
            benchmark
            for benchmark in self.market_benchmarks
            if benchmark.product_id == product_id
        )

    def active_funding(self) -> Tuple[FundingOpportunity, ...]:
        return tuple(
            opportunity
            for opportunity in self.funding_opportunities
            if opportunity.lifecycle not in {"CLOSED", "ARCHIVED"}
        )


def _require_nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_unique_ids(name: str, records: Iterable[object]) -> None:
    seen: set[str] = set()
    for record in records:
        record_id = getattr(record, "id")
        if record_id in seen:
            raise ValueError(f"Duplicate {name} id: {record_id}")
        seen.add(record_id)


def _require_http_url(name: str, value: str) -> None:
    if not value.startswith(("https://", "http://")):
        raise ValueError(f"{name} must be an http(s) URL: {value}")


def _parse_product(raw: Mapping[str, object]) -> ProductOffering:
    product = ProductOffering(
        id=str(raw["id"]),
        name_en=str(raw["name_en"]),
        name_ja=str(raw["name_ja"]),
        category=str(raw["category"]),
        billing_units=tuple(str(v) for v in raw["billing_units"]),  # type: ignore[index]
        capacity_accounting=str(raw["capacity_accounting"]),
        customer_types=tuple(str(v) for v in raw["customer_types"]),  # type: ignore[index]
        description=str(raw["description"]),
    )
    for name in ("id", "name_en", "name_ja", "category", "description"):
        _require_nonempty(f"product.{name}", getattr(product, name))
    if product.capacity_accounting not in _ALLOWED_CAPACITY_ACCOUNTING:
        raise ValueError(
            f"Unsupported capacity_accounting for {product.id}: "
            f"{product.capacity_accounting}"
        )
    if not product.billing_units:
        raise ValueError(f"Product {product.id} must declare at least one billing unit")
    return product


def _parse_price_target(raw: Mapping[str, object]) -> PriceTarget:
    target = PriceTarget(
        id=str(raw["id"]),
        product_id=str(raw["product_id"]),
        price=float(raw["price"]),
        currency=str(raw["currency"]),
        unit=str(raw["unit"]),
        evidence_status=str(raw["evidence_status"]),
        source_ref=str(raw["source_ref"]),
        notes=str(raw["notes"]),
    )
    if target.price < 0:
        raise ValueError(f"Price target {target.id} cannot be negative")
    if target.evidence_status not in _ALLOWED_EVIDENCE:
        raise ValueError(f"Unsupported evidence status: {target.evidence_status}")
    return target


def _parse_benchmark(raw: Mapping[str, object]) -> MarketBenchmark:
    normalized = raw.get("normalized_gpu_hour")
    benchmark = MarketBenchmark(
        id=str(raw["id"]),
        provider=str(raw["provider"]),
        market=str(raw["market"]),
        product_id=str(raw["product_id"]),
        description=str(raw["description"]),
        hardware=str(raw["hardware"]),
        price=float(raw["price"]),
        currency=str(raw["currency"]),
        unit=str(raw["unit"]),
        normalized_gpu_hour=None if normalized is None else float(normalized),
        tax_included=bool(raw["tax_included"]),
        effective_or_checked_date=str(raw["effective_or_checked_date"]),
        evidence_status=str(raw["evidence_status"]),
        source_url=str(raw["source_url"]),
        notes=str(raw["notes"]),
    )
    if benchmark.price < 0:
        raise ValueError(f"Benchmark {benchmark.id} cannot have a negative price")
    if benchmark.normalized_gpu_hour is not None and benchmark.normalized_gpu_hour < 0:
        raise ValueError(f"Benchmark {benchmark.id} normalized price cannot be negative")
    if benchmark.evidence_status not in _ALLOWED_EVIDENCE:
        raise ValueError(f"Unsupported evidence status: {benchmark.evidence_status}")
    _require_http_url(f"benchmark.{benchmark.id}.source_url", benchmark.source_url)
    return benchmark


def _parse_funding(raw: Mapping[str, object]) -> FundingOpportunity:
    opportunity = FundingOpportunity(
        id=str(raw["id"]),
        kind=str(raw["kind"]),
        program_name=str(raw["program_name"]),
        agency=str(raw["agency"]),
        jurisdiction=str(raw["jurisdiction"]),
        lifecycle=str(raw["lifecycle"]),
        open_date=str(raw["open_date"]),
        deadlines=tuple(str(v) for v in raw["deadlines"]),  # type: ignore[index]
        subsidy_rate_text=str(raw["subsidy_rate_text"]),
        cap_text=str(raw["cap_text"]),
        eligibility_summary=str(raw["eligibility_summary"]),
        yumori_relevance=str(raw["yumori_relevance"]),
        blockers_or_gates=str(raw["blockers_or_gates"]),
        funding_treatment=str(raw["funding_treatment"]),
        evidence_status=str(raw["evidence_status"]),
        checked_date=str(raw["checked_date"]),
        source_url=str(raw["source_url"]),
        detail_url=str(raw["detail_url"]),
    )
    if opportunity.evidence_status not in _ALLOWED_EVIDENCE:
        raise ValueError(f"Unsupported evidence status: {opportunity.evidence_status}")
    if opportunity.funding_treatment not in _ALLOWED_FUNDING_TREATMENT:
        raise ValueError(
            f"Unsupported funding_treatment for {opportunity.id}: "
            f"{opportunity.funding_treatment}"
        )
    _require_http_url(f"funding.{opportunity.id}.source_url", opportunity.source_url)
    _require_http_url(f"funding.{opportunity.id}.detail_url", opportunity.detail_url)
    return opportunity


def load_catalog(path: str | Path | None = None) -> FinancialCatalog:
    """Load and validate the repository-owned finance catalog.

    Validation fails closed on duplicate IDs, unknown product references,
    unsupported truth-status values, invalid source URLs, and invalid prices.
    """
    catalog_path = Path(path) if path is not None else DEFAULT_CATALOG_PATH
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))

    if raw.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported finance catalog schema: {raw.get('schema_version')!r}; "
            f"expected {CATALOG_SCHEMA_VERSION!r}"
        )

    products = tuple(_parse_product(v) for v in raw["products"])
    targets = tuple(_parse_price_target(v) for v in raw["yumori_price_targets"])
    benchmarks = tuple(_parse_benchmark(v) for v in raw["market_benchmarks"])
    funding = tuple(_parse_funding(v) for v in raw["funding_opportunities"])

    _require_unique_ids("product", products)
    _require_unique_ids("price target", targets)
    _require_unique_ids("benchmark", benchmarks)
    _require_unique_ids("funding opportunity", funding)

    product_ids = {product.id for product in products}
    for record in (*targets, *benchmarks):
        if record.product_id not in product_ids:
            raise ValueError(
                f"{record.id} references unknown product_id: {record.product_id}"
            )

    catalog = FinancialCatalog(
        schema_version=str(raw["schema_version"]),
        foundup_id=str(raw["foundup_id"]),
        as_of=str(raw["as_of"]),
        truth_boundary=str(raw["truth_boundary"]),
        products=products,
        yumori_price_targets=targets,
        market_benchmarks=benchmarks,
        funding_opportunities=funding,
    )
    _require_nonempty("foundup_id", catalog.foundup_id)
    _require_nonempty("as_of", catalog.as_of)
    _require_nonempty("truth_boundary", catalog.truth_boundary)
    return catalog


def build_public_catalog_snapshot(
    catalog: FinancialCatalog | None = None,
) -> Dict[str, object]:
    """Return the stable read model intended for XLSX/API/web projections.

    No operating financial equations are duplicated here. This function only
    normalizes the repo evidence catalog and exposes explicit truth boundaries.
    """
    c = catalog or load_catalog()
    return {
        "schema_version": c.schema_version,
        "foundup_id": c.foundup_id,
        "as_of": c.as_of,
        "truth_boundary": c.truth_boundary,
        "counts": {
            "products": len(c.products),
            "yumori_price_targets": len(c.yumori_price_targets),
            "market_benchmarks": len(c.market_benchmarks),
            "funding_opportunities": len(c.funding_opportunities),
            "active_funding_opportunities": len(c.active_funding()),
        },
        "products": [asdict(v) for v in c.products],
        "yumori_price_targets": [asdict(v) for v in c.yumori_price_targets],
        "market_benchmarks": [asdict(v) for v in c.market_benchmarks],
        "funding_opportunities": [asdict(v) for v in c.funding_opportunities],
        "accounting_rules": {
            "market_benchmark": "External comparison only; not YUMORI revenue.",
            "yumori_price_target": "MODEL ONLY until a quote or contract validates it.",
            "funding_opportunity": (
                "Verified program existence does not equal awarded project funding. "
                "Only AWARDED/COMMITTED treatment may enter committed capital."
            ),
            "gpu_capacity": (
                "Products marked EXCLUSIVE_GPU_POOL or EXCLUSIVE_GPU_POOL_PLUS_SERVICE "
                "draw from the same physical GPU inventory and must not be double-counted."
            ),
        },
    }
