# YUMORI Economic Model

## 位置づけ / Ownership

これは **YUMORI.me / eSingularity FoundUp の事業経済モデル**である。一般的な FoundUps のトークン経済、ROC、CABR、配当・報酬モデルではない。

- 計算本体: `src/yumori_economic_model.py`
- 日本のAIインフラ関係台帳: `jhr/data/japan_ai_infrastructure_flows.json`
- 回帰テスト: `tests/test_yumori_economic_model.py`
- 参照ワークブック: `FIN — YUMORI Phase 1 Financial Model & Grant Audit`

Pythonを計算の権威とし、スプレッドシートは入力確認・感度分析・説明用の投影として扱う。公表値にするには、電力会社、設計者、機器ベンダー、顧客、金融機関、補助金執行機関の証拠が別途必要である。

## 現行ベースケースとの一致

デフォルト入力は現行FIN.YUMORI機能モデルを再現する。これは予測や保証ではない。

| 指標 | Pythonデフォルト | 証拠状態 |
| --- | ---: | --- |
| 総CapEx | ¥2,085,000,000 | MODEL ONLY |
| 基本ケース必要エクイティ | ¥550,000,000 | debt/grant assumptions are MODEL ONLY |
| Year 1 gross revenue | ¥808,630,528 | price/utilization are VERIFY |
| Year 1 EBITDA | ¥599,427,112 | calculated from VERIFY/MODEL inputs |
| Minimum DSCR | 1.2896x | scenario test; no covenant claimed |
| 5-year cumulative FCFE | ¥1,732,492,960 | modeled, not forecast |
| Equity IRR | 40.93% | modeled, not investor return promise |
| 12% discount-rate equity NPV | ¥609,079,292 | MODEL INPUT |
| Simple interpolated payback | 2.46 years | modeled, not guarantee |

未採択補助金は基本ケースの必要資金から控除しない。`potential_grants_scenario_jpy` は表示・感度分析専用で、`committed_awarded_grants_jpy` のみが資金調達額を減らす。

## 事業計算

年 (t) の利用率を (u_t)、GPU台数を (G)、年間時間を (H=8{,}760) とする。

### Compute revenue

\[
\text{GPU-hours}_t = G \times H \times u_t
\]

\[
\text{Compute revenue}_t = \sum_i G \times s_i \times H \times u_t \times p_i \times (1+g_p)^{t-1}
\]

ここで (s_i) は料金区分の配分、(p_i) はGPU-hour単価、(g_p) は単価上昇率。配分合計が100%でなければ計算は停止する。

### Electricity

\[
L_t = L_{idle} + (1-L_{idle})u_t
\]

\[
\text{kWh}_t = \text{IT kW} \times \text{PUE} \times H \times L_t
\]

\[
\text{Electricity cost}_t = \text{kWh}_t \times \text{tariff}_1 \times (1+g_e)^{t-1}
\]

現行ワークブックとの一致のため、デフォルトのアイドル負荷率は0である。実施設計ではサーバのアイドル電力、ポンプ、ネットワーク、BESS、冷却の固定負荷を測定し、必ず置き換える。

### Funding, debt and cash flow

\[
\text{Equity required} = \max(0,\;CapEx-\text{awarded grants}-\text{compute debt}-\text{infrastructure debt})
\]

各借入は元金均等返済で、年初残高に利率を掛ける。

\[
\text{DSCR}_t = \frac{\text{EBITDA}_t}{\text{principal}_t+\text{interest}_t}
\]

\[
\text{FCFE}_t = \text{net income}_t + D\&A_t - \Delta WC_t - \text{maintenance CapEx}_t - \text{principal}_t
\]

IRRは ((-Equity, FCFE_1,\ldots,FCFE_5)) のNPVを0にする割引率。NPVは指定したエクイティ割引率で計算し、単純回収期間は累積FCFEが初期エクイティを超える年を線形補間する。

## 温泉・排熱の計算

固定の「排熱収入」をそのまま売上にせず、回収できる熱、配管等で届く熱、実際の温浴需要の最小値だけを価値化する。

\[
Q_{source}=\text{IT kW}\times\text{load fraction}
\]

\[
Q_{recovered}=Q_{source}\times\eta_{recovery}
\]

\[
Q_{delivered}=Q_{recovered}\times\eta_{delivery}
\]

\[
Q_{usable}=\min(Q_{delivered},Q_{demand})
\]

\[
\text{Annual usable heat}=Q_{usable}\times8{,}760\times\text{availability}
\]

\[
\text{Annual heat value}=\text{usable kWh}_{th}\times\text{avoided heat cost per kWh}_{th}
\]

東京都は、GPUサーバの廃熱を高温回収し、近隣温浴施設や地域熱供給に使う実証事業を公式に開始している。これはYUMORIの技術仮説に日本国内の制度・実証先例があることを示すが、旧すかっとランド九頭竜で成立する証明ではない。現地の給湯負荷、必要温度、熱交換器、距離、配管損失、季節変動、稼働率、代替燃料単価を測る必要がある。

## Japan AI infrastructure dependency ledger

[AI Circular Economy](https://ai-circular-economy.com/) は、出資、compute commitment、partnership、venture、M&Aを有向グラフで結び、契約状態と出典を残す。公開検索では同等の日本専用マップを確認できなかったため、JHRの証拠レーンに日本向け台帳を置く。

初期台帳は13件の公式ソース関係を収録する。KDDI大阪堺データセンターの旧Sharp資産再利用、HPE/NVIDIA系設備、Google Gemini、Takeda、ELYZA、Morgenrot/TOHKnetとの分散GPU実証、東京都のデータセンター廃熱実証を含む。金額が公式ソースで開示されていない項目は `null` のままとし、投資・提携・選定をYUMORIの売上や確定補助金へ転記しない。

### 再現した3つの計算指標

1. **Reciprocal-flow share**（元サイト重み25%）  
   逆向きエッジも存在する有向エッジの割合。10%を0点、60%を100点として線形スケールする。
2. **Announced-vs-paid / paper share**（15%）  
   `completed/operating=0`, `signed=0.5`, `LOI=1`, `paused=1`, unknown=0.5 の平均。15%を0点、70%を100点として線形スケールする。
3. **Counterparty concentration**（10%）  
   各主体のエンドポイント次数比から (HHI=\sum_j share_j^2)、実効参加者数 (N_{eff}=1/HHI)、raw (=1-N_{eff}/N)。25%を0点、70%を100点として線形スケールする。

\[
\text{Computed component score}=
\frac{0.25S_{circular}+0.15S_{paper}+0.10S_{concentration}}{0.50}
\]

これは元手法の50%だけを再現する部分診断である。元サイトの手動評価である revenue gap vs CapEx（20%）、financing quality（20%）、market behavior（10%）は、YUMORI側では値を作らず省略する。したがって「Japan bubble index」や投資判断として公表しない。台帳は選択バイアスを持つため、スコアは市場全体を表さない。

## Official source set

- [KDDI acquisition of the former Sharp Sakai assets](https://newsroom.kddi.com/english/news/detail/kddi_nr-565_3853.html)
- [KDDI–HPE AI infrastructure collaboration](https://newsroom.kddi.com/english/news/detail/kddi_nr-630_3986.html)
- [Osaka Sakai Data Center operating and use-case relationships](https://newsroom.kddi.com/english/news/detail/kddi_nr-916_4323.html)
- [Distributed data-center / Watt-Bit demonstration](https://newsroom.kddi.com/english/news/detail/kddi_nr-1169_4724.html)
- [Tokyo data-center waste-heat demonstration](https://www.metro.tokyo.lg.jp/information/press/2026/07/2026071607)
- [Original circular-flow map and methodology](https://ai-circular-economy.com/)

## 実行

```powershell
python -m pytest modules/foundups/esingularity/tests/test_yumori_economic_model.py -q
```

依存ライブラリがない環境でも、計算本体はPython標準ライブラリだけで動く。

## 次の証拠ゲート

次の入力が確認されるまで、デフォルト値を提案書の確定値・予測値・利回り保証として扱わない。

- Hokuriku Electricの実効料金、接続可能容量、工事負担金、受電時期
- GPU/サーバ/ネットワーク/冷却/BESSの構成と有効見積
- 建物構造、耐震、用途変更、消防、騒音、水、温泉設備の現地調査
- 顧客別GPU-hour需要、価格、最低利用量、契約期間、信用力
- 温浴側の時間別・季節別熱需要、供給温度、配管距離、損失、代替燃料費
- 借入条件、元利返済方法、担保、コベナンツ、更新投資
- 補助金の申請主体、対象費、採択・交付決定額、併用可否
- 運営主体、土地建物の使用権、PPP/PFI/SPC構造、税務

