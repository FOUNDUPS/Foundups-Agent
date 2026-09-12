'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import {
  calculateFinanceScenario,
  fetchFinanceSnapshot,
  FinanceSnapshot,
} from '../lib/finance-api';

const money = new Intl.NumberFormat('ja-JP', {
  style: 'currency',
  currency: 'JPY',
  maximumFractionDigits: 0,
});
const number = new Intl.NumberFormat('ja-JP', { maximumFractionDigits: 1 });
const percent = new Intl.NumberFormat('ja-JP', {
  style: 'percent',
  maximumFractionDigits: 1,
});

function priceLabel(price: number, currency: string, unit: string) {
  const formatted = new Intl.NumberFormat(currency === 'JPY' ? 'ja-JP' : 'en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: currency === 'JPY' ? 0 : 3,
  }).format(price);
  return `${formatted} / ${unit}`;
}

function dateLabel(value: string) {
  if (!value) return '未定 / TBD';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) return value;
  return new Intl.DateTimeFormat('ja-JP', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: value.includes('T') ? '2-digit' : undefined,
    minute: value.includes('T') ? '2-digit' : undefined,
    timeZone: 'Asia/Tokyo',
  }).format(parsed);
}

export default function FinanceDashboard() {
  const [snapshot, setSnapshot] = useState<FinanceSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState('');
  const [pue, setPue] = useState('');
  const [tariff, setTariff] = useState('');
  const [utilizationY1, setUtilizationY1] = useState('');
  const [enterprisePrice, setEnterprisePrice] = useState('');
  const [burstPrice, setBurstPrice] = useState('');
  const [academicPrice, setAcademicPrice] = useState('');

  function populateControls(data: FinanceSnapshot) {
    const a = data.operating_model.assumptions;
    setPue(String(a.pue));
    setTariff(String(a.electricity_tariff_jpy_per_kwh));
    setUtilizationY1(String(a.utilization[0]));
    const tiers = Object.fromEntries(a.tiers.map((tier) => [tier.key, tier]));
    setEnterprisePrice(String(tiers.tier_a?.price_jpy_per_gpu_hour ?? ''));
    setBurstPrice(String(tiers.tier_b?.price_jpy_per_gpu_hour ?? ''));
    setAcademicPrice(String(tiers.tier_c?.price_jpy_per_gpu_hour ?? ''));
  }

  async function loadDefault() {
    setLoading(true);
    setError('');
    try {
      const data = await fetchFinanceSnapshot();
      setSnapshot(data);
      populateControls(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Finance API error');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDefault();
  }, []);

  async function runScenario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!snapshot) return;
    setCalculating(true);
    setError('');
    const baseUtilization = snapshot.operating_model.assumptions.utilization;
    try {
      const data = await calculateFinanceScenario({
        pue: Number(pue),
        electricity_tariff_jpy_per_kwh: Number(tariff),
        utilization: [Number(utilizationY1), ...baseUtilization.slice(1)],
        tier_prices: {
          tier_a: Number(enterprisePrice),
          tier_b: Number(burstPrice),
          tier_c: Number(academicPrice),
        },
      });
      setSnapshot(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scenario calculation failed');
    } finally {
      setCalculating(false);
    }
  }

  const targetsByProduct = useMemo(() => {
    if (!snapshot) return new Map();
    return new Map(snapshot.catalog.yumori_price_targets.map((target) => [target.product_id, target]));
  }, [snapshot]);

  if (loading) {
    return <main className="future-page"><section className="section"><p>FIN.YUMORI を読み込み中…</p></section></main>;
  }

  if (!snapshot) {
    return (
      <main className="future-page">
        <section className="section">
          <p className="eyebrow"><span /> FINANCE API</p>
          <h1>財務モデルAPIが未接続です。</h1>
          <p>この画面はローカル計算にフォールバックしません。Python財務APIを接続すると、同じコードベースの計算結果が表示されます。</p>
          {error && <p role="alert">{error}</p>}
        </section>
      </main>
    );
  }

  const summary = snapshot.operating_model.summary;
  const assumptions = snapshot.operating_model.assumptions;

  return (
    <main className="future-page">
      <section className="future-hero">
        <p className="eyebrow light"><span /> FIN.YUMORI · LIVE PYTHON MODEL</p>
        <h1>数字を固定しない。<br /><em>根拠と一緒に動かす。</em></h1>
        <p>財務計算はPythonモデルが実行します。価格、需要、電力、助成制度を証拠ステータスと一緒に確認し、シナリオをその場で再計算するための試験画面です。</p>
        <p><strong>{snapshot.operating_model.status}</strong> · as of {snapshot.as_of}</p>
      </section>

      <section className="section" aria-labelledby="finance-summary-title">
        <div className="future-heading">
          <p className="eyebrow"><span /> MODEL OUTPUT</p>
          <h2 id="finance-summary-title">現在のモデル・<em>サマリー</em></h2>
          <p>{snapshot.operating_model.truth_boundary}</p>
        </div>
        <div className="benefit-grid" role="list">
          <article role="listitem"><div><h3>5年売上 / Revenue</h3><p>{money.format(summary.five_year_revenue_jpy)}</p></div></article>
          <article role="listitem"><div><h3>5年 EBITDA</h3><p>{money.format(summary.five_year_ebitda_jpy)}</p></div></article>
          <article role="listitem"><div><h3>5年 FCFE</h3><p>{money.format(summary.five_year_fcfe_jpy)}</p></div></article>
          <article role="listitem"><div><h3>株主 IRR</h3><p>{summary.equity_irr == null ? 'N/A' : percent.format(summary.equity_irr)}</p></div></article>
        </div>
      </section>

      <section className="growth section" aria-labelledby="scenario-title">
        <p className="eyebrow"><span /> DYNAMIC SCENARIO</p>
        <h2 id="scenario-title">前提を変えて、<em>Pythonで再計算</em></h2>
        <p className="growth-lead">ここで変更する値はすべて「MODEL ONLY」です。保存・契約・資金コミットは行いません。</p>
        <form onSubmit={runScenario}>
          <div className="benefit-grid">
            <label><strong>PUE</strong><br /><input type="number" min="1" step="0.001" value={pue} onChange={(e) => setPue(e.target.value)} /></label>
            <label><strong>電力単価 / JPY-kWh</strong><br /><input type="number" min="0" step="0.1" value={tariff} onChange={(e) => setTariff(e.target.value)} /></label>
            <label><strong>Year 1 利用率</strong><br /><input type="number" min="0" max="1" step="0.01" value={utilizationY1} onChange={(e) => setUtilizationY1(e.target.value)} /></label>
            <label><strong>企業予約 / JPY-GPUh</strong><br /><input type="number" min="0" step="1" value={enterprisePrice} onChange={(e) => setEnterprisePrice(e.target.value)} /></label>
            <label><strong>バースト / JPY-GPUh</strong><br /><input type="number" min="0" step="1" value={burstPrice} onChange={(e) => setBurstPrice(e.target.value)} /></label>
            <label><strong>大学研究 / JPY-GPUh</strong><br /><input type="number" min="0" step="1" value={academicPrice} onChange={(e) => setAcademicPrice(e.target.value)} /></label>
          </div>
          <p><button className="button button-primary" type="submit" disabled={calculating}>{calculating ? 'Pythonで計算中…' : 'シナリオを再計算'}</button> <button className="button button-ghost" type="button" onClick={() => void loadDefault()}>既定値へ戻す</button></p>
          {error && <p role="alert">{error}</p>}
        </form>
      </section>

      <section className="section" aria-labelledby="capacity-title">
        <div className="future-heading"><p className="eyebrow"><span /> 1–5 MW INVENTORY</p><h2 id="capacity-title">売る前に、<em>物理在庫を守る</em></h2><p>GPU商品は同じ物理プールから消費します。同じGPUを企業・大学・バーストで二重計上しません。</p></div>
        <div className="benefit-grid" role="list">
          {snapshot.capacity_planning.map((plan) => <article key={plan.mw} role="listitem"><div><h3>{number.format(plan.mw)} MW</h3><p>{number.format(plan.gpus)} GPUs<br />{number.format(plan.eight_gpu_nodes)} × 8-GPU nodes</p></div></article>)}
        </div>
      </section>

      <section className="section" aria-labelledby="menu-title">
        <div className="future-heading"><p className="eyebrow"><span /> DATA CENTER MENU</p><h2 id="menu-title">データセンターを、<em>コーヒーショップのメニュー</em>のように見る</h2><p>計算、AI運用、ストレージ、回線、運用支援、コロケーション、排熱までを別商品として管理します。</p></div>
        <div className="benefit-grid" role="list">
          {snapshot.catalog.products.map((product) => {
            const target = targetsByProduct.get(product.id);
            return <article key={product.id} role="listitem"><div><h3>{product.name_ja}</h3><p><strong>{product.name_en}</strong></p><p>{product.description}</p><p>{product.billing_units.join(' · ')}</p>{target && <p>YUMORI target: {priceLabel(target.price, target.currency, target.unit)} · {target.evidence_status}</p>}</div></article>;
          })}
        </div>
      </section>

      <section className="section" aria-labelledby="benchmark-title">
        <div className="future-heading"><p className="eyebrow"><span /> JAPAN + GLOBAL BENCHMARKS</p><h2 id="benchmark-title">市場価格を、<em>出典付きで比較</em></h2><p>通貨は原通貨を保持します。為替を固定して見かけ上の比較を作りません。</p></div>
        <div className="benefit-grid" role="list">
          {snapshot.catalog.market_benchmarks.map((item) => <article key={item.id} role="listitem"><div><h3>{item.provider}</h3><p>{item.market} · {item.hardware}</p><p><strong>{priceLabel(item.price, item.currency, item.unit)}</strong></p>{item.normalized_gpu_hour != null && <p>Normalized: {priceLabel(item.normalized_gpu_hour, item.currency, 'GPU-hour')}</p>}<p>checked {item.effective_or_checked_date} · {item.evidence_status}</p><p><a href={item.source_url} target="_blank" rel="noreferrer">一次情報 / source ↗</a></p></div></article>)}
        </div>
      </section>

      <section className="section" aria-labelledby="grants-title">
        <div className="future-heading"><p className="eyebrow"><span /> GRANTS + PUBLIC FUNDING</p><h2 id="grants-title">制度は見せる。<em>採択前は資金にしない。</em></h2><p>公募の存在が確認できても、採択・コミットされるまでは建設資金に算入しません。</p></div>
        <div className="benefit-grid" role="list">
          {snapshot.catalog.funding_opportunities.map((grant) => <article key={grant.id} role="listitem"><div><h3>{grant.program_name}</h3><p>{grant.agency} · {grant.lifecycle}</p><p><strong>{grant.subsidy_rate_text}</strong><br />{grant.cap_text}</p><p>締切: {grant.deadlines.length ? grant.deadlines.map(dateLabel).join(' / ') : '個別確認 / confirm with agency'}</p><p>{grant.yumori_relevance}</p><p>{grant.funding_treatment} · checked {grant.checked_date}</p><p><a href={grant.source_url} target="_blank" rel="noreferrer">一次情報 / source ↗</a></p></div></article>)}
        </div>
      </section>

      <section className="section">
        <p className="eyebrow"><span /> CURRENT BASE INPUTS</p>
        <p>{assumptions.total_gpus} GPUs · IT {number.format(assumptions.it_power_kw)} kW · site {number.format(assumptions.total_site_power_kw)} kW · PUE {assumptions.pue} · electricity {money.format(assumptions.electricity_tariff_jpy_per_kwh)}/kWh</p>
        <p>Legacy grants input shown by the operating model: {money.format(assumptions.grants_jpy)}. This remains a model assumption and is not treated as awarded funding by the grants/NCDS ledger.</p>
      </section>
    </main>
  );
}
