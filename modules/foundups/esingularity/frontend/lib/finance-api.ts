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
  catalog: FinanceCatalog;
  capacity_planning: CapacityPlan[];
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
