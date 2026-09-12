export type FinanceProduct = {
  id: string;
  name_en: string;
  name_ja: string;
  category: string;
  billing_units: string[];
  capacity_accounting: string;
  customer_types: string[];
  description: string;
};

export type PriceTarget = {
  id: string;
  product_id: string;
  price: number;
  currency: string;
  unit: string;
  evidence_status: string;
  source_ref: string;
  notes: string;
};

export type MarketBenchmark = {
  id: string;
  provider: string;
  market: string;
  product_id: string;
  description: string;
  hardware: string;
  price: number;
  currency: string;
  unit: string;
  normalized_gpu_hour: number | null;
  tax_included: boolean;
  effective_or_checked_date: string;
  evidence_status: string;
  source_url: string;
  notes: string;
};

export type PriceComparison = {
  benchmark: MarketBenchmark;
  comparison_status: 'DIRECT_PRICE_RATIO_ONLY' | 'FX_REQUIRED' | 'UNIT_NOT_COMPARABLE';
  target_price: number;
  target_currency: string;
  target_unit: string;
  benchmark_gpu_hour_basis?: number;
  absolute_delta?: number;
  delta_pct?: number | null;
  target_to_benchmark_ratio?: number | null;
  scope_warning?: string;
};

export type PriceReconciliationTarget = {
  target: PriceTarget;
  comparisons: PriceComparison[];
  direct_comparison_count: number;
  fx_required_count: number;
};

export type PriceReconciliation = {
  as_of: string;
  truth_boundary: string;
  targets: PriceReconciliationTarget[];
};

export type FundingOpportunity = {
  id: string;
  kind: string;
  program_name: string;
  agency: string;
  jurisdiction: string;
  lifecycle: string;
  open_date: string;
  deadlines: string[];
  subsidy_rate_text: string;
  cap_text: string;
  eligibility_summary: string;
  yumori_relevance: string;
  blockers_or_gates: string;
  funding_treatment: string;
  evidence_status: string;
  checked_date: string;
  source_url: string;
  detail_url: string;
};

export type FinanceCatalog = {
  schema_version: string;
  foundup_id: string;
  as_of: string;
  truth_boundary: string;
  counts: Record<string, number>;
  products: FinanceProduct[];
  yumori_price_targets: PriceTarget[];
  market_benchmarks: MarketBenchmark[];
  funding_opportunities: FundingOpportunity[];
  accounting_rules: Record<string, string>;
};

export type CapacityPlan = {
  mw: number;
  gpus: number;
  eight_gpu_nodes: number;
};

export type CapacityEconomics = {
  mw: number;
  gpus: number;
  eight_gpu_nodes: number;
  estimated_project_cost_jpy: number;
  year1_revenue_jpy: number;
  year1_operating_cost_jpy: number;
  year1_ebitda_jpy: number;
  historic_fy2018_user_fee_revenue_coverage_x: number;
  historic_fy2018_city_net_cost_coverage_x: number;
  current_dormant_carrying_cost_coverage_x: number;
  status: string;
  scaling_rule: string;
};

export type FacilityOperatingHistory = {
  period: string;
  period_label: string;
  users: number;
  lodging_users: number;
  day_users: number;
  user_fee_revenue_jpy: number;
  evidence_status: string;
  scope: string;
  source_url: string;
};

export type FacilityUsageOnlyHistory = Omit<FacilityOperatingHistory, 'user_fee_revenue_jpy'> & {
  user_fee_revenue_jpy: number | null;
};

export type FacilityManagementFinance = {
  period: string;
  management_fee_jpy: number;
  payment_to_city_jpy: number;
  evidence_status: string;
  scope: string;
  source_url: string;
};

export type FacilityCityFiscalHistory = {
  period: string;
  city_revenue_jpy: number;
  city_expenditure_jpy: number;
  city_net_cost_jpy: number;
  combined_users: number;
  cost_per_user_jpy: number;
  scope: string;
  evidence_status: string;
  source_url: string;
};

export type FacilityHistory = {
  schema_version: string;
  facility: string;
  as_of: string;
  truth_boundary: string;
  operating_history: FacilityOperatingHistory[];
  usage_only_history: FacilityUsageOnlyHistory[];
  management_finance_history: FacilityManagementFinance[];
  city_fiscal_history: FacilityCityFiscalHistory[];
  current_carrying_cost: {
    period: string;
    known_annual_cost_jpy: number;
    components: Record<string, number>;
    excluded: string[];
    land_burden_reference_jpy_per_m2: number;
    building_rent_if_regional_promotion_use: number;
    evidence_status: string;
    source_url: string;
  };
  operator_cost_evidence: {
    fy2015_personnel_cost_jpy: number;
    latest_audited_direction: string;
    full_reopened_onsen_opex_jpy: number | null;
    evidence_gap: string;
    evidence_status: string;
    source_url: string;
  };
  accounting_rules: Record<string, string>;
};

export type YearResult = {
  year: number;
  utilization: number;
  gross_revenue_jpy: number;
  ebitda_jpy: number;
  power_cost_jpy: number;
  fcfe_jpy: number;
  dscr: number | null;
};

export type ModelAssumptions = {
  utilization: number[];
  total_gpus: number;
  pue: number;
  it_power_kw: number;
  total_site_power_kw: number;
  electricity_tariff_jpy_per_kwh: number;
  facility_capex_jpy: number;
  compute_capex_jpy: number;
  grants_jpy: number;
  sponsor_equity_jpy: number;
  tiers: Array<{
    key: string;
    name: string;
    gpu_count: number;
    price_jpy_per_gpu_hour: number;
    status: string;
    source: string;
  }>;
};

export type FinanceSnapshot = {
  schema_version: string;
  foundup_id: string;
  as_of: string;
  operating_model: {
    status: string;
    model_name: string;
    assumptions: ModelAssumptions;
    years: YearResult[];
    summary: {
      five_year_revenue_jpy: number;
      five_year_ebitda_jpy: number;
      five_year_fcfe_jpy: number;
      equity_irr: number | null;
      equity_npv_jpy: number;
      initial_equity_jpy: number;
      visitor_spend_30y_low_jpy: number;
      visitor_spend_30y_high_jpy: number;
    };
    validation: Record<string, boolean>;
    truth_boundary: string;
  };
  facility_history: FacilityHistory;
  catalog: FinanceCatalog;
  price_reconciliation: PriceReconciliation;
  capacity_planning: CapacityPlan[];
  capacity_economics: CapacityEconomics[];
  capacity_allocation: Record<string, unknown>;
  feasibility: Record<string, unknown>;
  scenario?: {
    status: string;
    overrides: Record<string, unknown>;
  };
};

function financeApiBase(): string {
  const value = process.env.NEXT_PUBLIC_ESINGULARITY_FINANCE_API_URL?.trim();
  return value ? value.replace(/\/$/, '') : '';
}

export function financeApiConfigured(): boolean {
  return Boolean(financeApiBase());
}

function financeUrl(path: string): string {
  const base = financeApiBase();
  if (!base) {
    throw new Error('NEXT_PUBLIC_ESINGULARITY_FINANCE_API_URL is not configured');
  }
  return `${base}/esingularity/finance/${path.replace(/^\//, '')}`;
}

async function financeFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(financeUrl(path), {
    ...init,
    headers: {
      'content-type': 'application/json',
      ...(init?.headers ?? {}),
    },
    cache: 'no-store',
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      // Preserve HTTP status when upstream does not return JSON.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function fetchFinanceSnapshot(): Promise<FinanceSnapshot> {
  return financeFetch<FinanceSnapshot>('snapshot');
}

export function fetchFinanceCatalog(): Promise<FinanceCatalog> {
  return financeFetch<FinanceCatalog>('catalog');
}

export function calculateFinanceScenario(
  overrides: Record<string, unknown>,
): Promise<FinanceSnapshot> {
  return financeFetch<FinanceSnapshot>('scenario', {
    method: 'POST',
    body: JSON.stringify(overrides),
  });
}
