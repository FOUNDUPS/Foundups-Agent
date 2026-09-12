'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import {
  calculateFinanceScenario,
  fetchFinanceSnapshot,
  FinanceSnapshot,
} from '../lib/finance-api';

const money = new Intl.NumberFormat('ja-JP', { style: 'currency', currency: 'JPY', maximumFractionDigits: 0 });
const number = new Intl.NumberFormat('ja-JP', { maximumFractionDigits: 1 });
const percent = new Intl.NumberFormat('ja-JP', { style: 'percent', maximumFractionDigits: 1 });
const multiple = new Intl.NumberFormat('ja-JP', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

function priceLabel(price: number, currency: string, unit: string) {
  const formatted = new Intl.NumberFormat(currency === 'JPY' ? 'ja-JP' : 'en-US', {
    style: 'currency', currency, maximumFractionDigits: currency === 'JPY' ? 0 : 3,
  }).format(price);
  return `${formatted} / ${unit}`;
}

function dateLabel(value: string) {
  if (!value) return '未定 / TBD';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) return value;
  return new Intl.DateTimeFormat('ja-JP', {
    year: 'numeric', month: 'short', day: 'numeric',
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
  const [selectedMw, setSelectedMw] = useState(1);
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

  useEffect(() => { void loadDefault(); }, []);

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

  if (loading) return <main className="future-page"><section className="section"><p>FIN.YUMORI を読み込み中…</p></section></main>;
  if (!snapshot) return <main className="future-page"><section className="section"><p className="eyebrow"><span /> FINANCE API</p><h1>財務モデルAPIが未接続です。</h1><p>この画面はローカル計算にフォールバックしません。Python財務APIを接続すると表示されます。</p>{error && <p role="alert">{error}</p>}</section></main>;

  const summary = snapshot.operating_model.summary;
  const assumptions = snapshot.operating_model.assumptions;
  const history = snapshot.facility_history;
  const fy2018 = history.operating_history.find((row) => row.period === 'FY2018') ?? history.operating_history.at(-1)!;
  const fy2018City = history.city_fiscal_history.find((row) => row.period === 'FY2018') ?? history.city_fiscal_history.at(-1)!;
  const selected = snapshot.capacity_economics.find((row) => row.mw === selectedMw) ?? snapshot.capacity_economics[0];

  return (
    <main className="future-page">
      <section className="future-hero">
        <p className="eyebrow light"><span /> FIN.YUMORI · SIMPLE BUSINESS VIEW</p>
        <h1>温泉を残すために、<br /><em>計算機はいくら稼げる？</em></h1>
        <p>まずは難しい財務表ではなく、旧施設の実績と、1〜5 MW の現在モデルを並べて見ます。数字はPythonから取得し、画面側では計算しません。</p>
        <p><strong>{snapshot.operating_model.status}</strong> · as of {snapshot.as_of}</p>
      </section>

      <section className="section" aria-labelledby="history-title">
        <div className="future-heading"><p className="eyebrow"><span /> HISTORIC ONsen</p><h2 id="history-title">旧施設は、<em>実際どうだった？</em></h2><p>{history.truth_boundary}</p></div>
        <div className="benefit-grid" role="list">
          <article role="listitem"><div><h3>2018 利用者</h3><p>{number.format(fy2018.users)} 人</p><p>{fy2018.evidence_status}</p></div></article>
          <article role="listitem"><div><h3>2018 利用料金収入</h3><p>{money.format(fy2018.user_fee_revenue_jpy)}</p><p>旧すかっとランド九頭竜</p></div></article>
          <article role="listitem"><div><h3>2018 市の純負担</h3><p>{money.format(fy2018City.city_net_cost_jpy)}</p><p>すかっとランド＋すこやかドームの市側コスト</p></div></article>
          <article role="listitem"><div><h3>閉館中の既知維持費</h3><p>{money.format(history.current_carrying_cost.known_annual_cost_jpy)}</p><p>土地・人件費・再開運営費等は除外</p></div></article>
        </div>
        <p><strong>重要：</strong>再開後の温泉全体OPEXはまだ確定していません。市の純負担や閉館中維持費を「温泉の総運営費」と置き換えません。</p>
      </section>

      <section className="growth section" aria-labelledby="mw-title">
        <p className="eyebrow"><span /> 1–5 MW BUSINESS SCALE</p>
        <h2 id="mw-title">規模を動かすと、<em>事業はどう変わる？</em></h2>
        <p className="growth-lead">現在の1 MWモデルを単純に1〜5 MWへ展開した「検討用」の見方です。実際の電力工事・冷却・人員・資金調達は別途検証します。</p>
        <label htmlFor="mw-slider"><strong>データセンター規模：{selectedMw} MW</strong></label>
        <input id="mw-slider" type="range" min="1" max="5" step="1" value={selectedMw} onChange={(e) => setSelectedMw(Number(e.target.value))} style={{ width: '100%' }} />
        <p>1 MW　—　2 MW　—　3 MW　—　4 MW　—　5 MW</p>
        <div className="benefit-grid" role="list">
          <article role="listitem"><div><h3>GPU在庫</h3><p>{number.format(selected.gpus)} GPUs</p><p>{number.format(selected.eight_gpu_nodes)} × 8-GPU nodes</p></div></article>
          <article role="listitem"><div><h3>概算プロジェクト費</h3><p>{money.format(selected.estimated_project_cost_jpy)}</p><p>MODEL ONLY</p></div></article>
          <article role="listitem"><div><h3>Year 1 売上</h3><p>{money.format(selected.year1_revenue_jpy)}</p></div></article>
          <article role="listitem"><div><h3>Year 1 運営費</h3><p>{money.format(selected.year1_operating_cost_jpy)}</p></div></article>
          <article role="listitem"><div><h3>Year 1 EBITDA</h3><p>{money.format(selected.year1_ebitda_jpy)}</p></div></article>
        </div>
        <div className="benefit-grid" role="list">
          <article role="listitem"><div><h3>旧2018利用料収入との比率</h3><p>{multiple.format(selected.historic_fy2018_user_fee_revenue_coverage_x)}×</p></div></article>
          <article role="listitem"><div><h3>2018市純負担との比率</h3><p>{multiple.format(selected.historic_fy2018_city_net_cost_coverage_x)}×</p></div></article>
          <article role="listitem"><div><h3>閉館維持費との比率</h3><p>{multiple.format(selected.current_dormant_carrying_cost_coverage_x)}×</p></div></article>
        </div>
        <p>{selected.scaling_rule}</p>
      </section>

      <section className="section" aria-labelledby="panels-title">
        <div className="future-heading"><p className="eyebrow"><span /> OPEN THE NUMBERS</p><h2 id="panels-title">必要な時だけ、<em>詳しく見る</em></h2></div>

        <details className="growth-details">
          <summary>旧施設の実績を見る <span>City evidence</span></summary>
          <div className="benefit-grid" role="list">
            {history.operating_history.map((row) => <article key={row.period} role="listitem"><div><h3>{row.period_label}</h3><p>{number.format(row.users)} users</p><p>{money.format(row.user_fee_revenue_jpy)} 利用料金</p><p><a href={row.source_url} target="_blank" rel="noreferrer">福井市資料 ↗</a></p></div></article>)}
          </div>
          <p>既知の旧運営人件費（FY2015）: {money.format(history.operator_cost_evidence.fy2015_personnel_cost_jpy)}。監査は直近収支が赤字だったとしています。</p>
          <p>{history.operator_cost_evidence.evidence_gap}</p>
        </details>

        <details className="growth-details">
          <summary>データセンターの商品を見る <span>Revenue menu</span></summary>
          <div className="benefit-grid" role="list">
            {snapshot.catalog.products.map((product) => {
              const target = targetsByProduct.get(product.id);
              return <article key={product.id} role="listitem"><div><h3>{product.name_ja}</h3><p>{product.name_en}</p><p>{product.description}</p>{target ? <p>{priceLabel(target.price, target.currency, target.unit)} · {target.evidence_status}</p> : <p>価格: TBD</p>}</div></article>;
            })}
          </div>
        </details>

        <details className="growth-details">
          <summary>日本・世界の価格を見る <span>Market benchmarks</span></summary>
          <div className="benefit-grid" role="list">
            {snapshot.catalog.market_benchmarks.map((item) => <article key={item.id} role="listitem"><div><h3>{item.provider}</h3><p>{item.market} · {item.hardware}</p><p><strong>{priceLabel(item.price, item.currency, item.unit)}</strong></p><p>{item.evidence_status} · {item.effective_or_checked_date}</p><p><a href={item.source_url} target="_blank" rel="noreferrer">一次情報 ↗</a></p></div></article>)}
          </div>
        </details>

        <details className="growth-details">
          <summary>助成金・公的支援を見る <span>Grants</span></summary>
          <p>制度が存在しても、採択されるまでは建設資金として数えません。</p>
          <div className="benefit-grid" role="list">
            {snapshot.catalog.funding_opportunities.map((grant) => <article key={grant.id} role="listitem"><div><h3>{grant.program_name}</h3><p>{grant.agency} · {grant.lifecycle}</p><p>{grant.subsidy_rate_text}<br />{grant.cap_text}</p><p>締切: {grant.deadlines.length ? grant.deadlines.map(dateLabel).join(' / ') : '要確認'}</p><p>{grant.yumori_relevance}</p><p><a href={grant.source_url} target="_blank" rel="noreferrer">一次情報 ↗</a></p></div></article>)}
          </div>
        </details>

        <details className="growth-details">
          <summary>高度な財務モデルを見る <span>Advanced scenario</span></summary>
          <div className="benefit-grid" role="list">
            <article role="listitem"><div><h3>5年売上</h3><p>{money.format(summary.five_year_revenue_jpy)}</p></div></article>
            <article role="listitem"><div><h3>5年 EBITDA</h3><p>{money.format(summary.five_year_ebitda_jpy)}</p></div></article>
            <article role="listitem"><div><h3>5年 FCFE</h3><p>{money.format(summary.five_year_fcfe_jpy)}</p></div></article>
            <article role="listitem"><div><h3>株主 IRR</h3><p>{summary.equity_irr == null ? 'N/A' : percent.format(summary.equity_irr)}</p></div></article>
          </div>
          <form onSubmit={runScenario}>
            <div className="benefit-grid">
              <label><strong>PUE</strong><br /><input type="number" min="1" step="0.001" value={pue} onChange={(e) => setPue(e.target.value)} /></label>
              <label><strong>電力単価 / JPY-kWh</strong><br /><input type="number" min="0" step="0.1" value={tariff} onChange={(e) => setTariff(e.target.value)} /></label>
              <label><strong>Year 1 利用率</strong><br /><input type="number" min="0" max="1" step="0.01" value={utilizationY1} onChange={(e) => setUtilizationY1(e.target.value)} /></label>
              <label><strong>企業予約 / JPY-GPUh</strong><br /><input type="number" min="0" step="1" value={enterprisePrice} onChange={(e) => setEnterprisePrice(e.target.value)} /></label>
              <label><strong>バースト / JPY-GPUh</strong><br /><input type="number" min="0" step="1" value={burstPrice} onChange={(e) => setBurstPrice(e.target.value)} /></label>
              <label><strong>大学研究 / JPY-GPUh</strong><br /><input type="number" min="0" step="1" value={academicPrice} onChange={(e) => setAcademicPrice(e.target.value)} /></label>
            </div>
            <p><button className="button button-primary" type="submit" disabled={calculating}>{calculating ? 'Pythonで計算中…' : 'Pythonで再計算'}</button> <button className="button button-ghost" type="button" onClick={() => void loadDefault()}>既定値へ戻す</button></p>
            {error && <p role="alert">{error}</p>}
          </form>
          <p>Base: {assumptions.total_gpus} GPUs · IT {number.format(assumptions.it_power_kw)} kW · PUE {assumptions.pue} · electricity {money.format(assumptions.electricity_tariff_jpy_per_kwh)}/kWh</p>
        </details>
      </section>
    </main>
  );
}
