# Japan compute precedents for Hanyu-first feasibility

Research date: 2026-10-01. Public Japanese primary sources only. This is benchmark evidence and modelling guidance, not a quotation, demand forecast, site engineering assessment, or change to an existing FIN model.

## Conclusion

Japan provides credible existing models for a small, staged compute business: repurposed-school batch inference, container-based colocation, regional backup hosting, and short-duration GPU rental. These are sufficient to begin a Japan-grounded feasibility model. Buyer contracts are a later evidence layer, not a prerequisite for this initial benchmark exercise.

Use four distinct evidence categories:

1. **Comparable supply economics:** published retail offers, installed configurations, and completed facilities
2. **Demand evidence:** identifiable Japanese workloads and customer interviews; these establish use cases, not demand for Hanyu specifically
3. **Project design assumptions:** Hanyu equipment, power connection, building works, cooling and service level; label unverified inputs explicitly
4. **Investment commitments:** site rights, dated supplier quotations, financing and customer commitments; obtain when advancing beyond preliminary feasibility

No Intelligent Internet lead or hypothetical hyperscaler tenant is required as the foundation of this benchmark model. No named organization below should be represented as a prospect, partner, or committed customer of YUMORI/eSingularity.

## Five comparable operating models

| Model | Verified evidence | Price, demand and important gaps | Appropriate use in FIN |
|---|---|---|---|
| **1. Highreso, Genkai: school reuse and batch inference** | Opened 2025-08-22. The operator describes a small initial AI batch-inference facility, with expansion by classroom as compute demand grows. It attributes the site's economics to local electricity pricing, flexible expansion and local cooperation. Current business description identifies A4000 GPUs and image-generation SaaS, distributed from its Shika operation. [Opening](https://highreso.jp/press/21830/), [operator opening report](https://highreso.jp/press/28289/), [service/site mapping](https://highreso.jp/business/) | Actual operating reuse precedent with an identified workload category. Public sources inspected do not establish site rack count, contracted IT kW, annual PUE, utilization, site capex breakdown, or realized revenue. | Strongest process precedent for a modest first phase and workload-led expansion. A reused building can support batch jobs; the site-specific electricity advantage is not automatically transferable. |
| **2. GX Technology / Getworks, Yuzawa: container hosting** | Operator facility page describes an operating container DC and 80 containers; individual modules integrate distribution, cooling and servers. Current capacity is an undated operator claim, not independently audited. [Facility](https://www.gxtec.co.jp/data-center/) | Indexed official tariff: 36U full rack, 5 kVA, one IP, shared 1 Gbps from **JPY 125,000/month**, initial fee free. Power expansion up to 60 kVA is an option. Container rental and purchase are quote-only; standard sale configuration lists five racks. Tax basis not established. Direct page retrieval returned 502, so the indexed official evidence must be reconfirmed before use as a current quote. [Tariff](https://www.gxtec.co.jp/gx-data-center-price/) | Useful modular supply and rent-versus-build comparator. Do not treat 5 kVA as measured 5 kW or extrapolate the starter rack price to high-density GPU power. Whole-site capex, billed occupancy and margins remain unknown. |
| **3. Tohoku Electric: GPU rental before infrastructure commitment** | GPU cloud launched 2025-02-20 with Getworks and GX Technology, targeting AI developers and education/research. On 2025-07-14 it added divided computing capacity, daily use and reservations in response to customers asking for smaller, planned usage. The original dedicated server has eight H200 GPUs. [Launch](https://www.tohoku-epco.co.jp/news/normal/1246196_2558.html), [service change](https://www.tohoku-epco.co.jp/news/normal/__icsFiles/afieldfile/2025/07/14/1247248.pdf) | Public page offers day reservations and dedicated periods; electricity and data communications included, price on quotation. Additional equipment provision is advertised at an indicative 2–3 months, subject to availability and conditions. No public occupancy or profitability found. [Service](https://www.tohoku-epco.co.jp/ai/gpucloud/) | Particularly useful for a low-capex workload pilot, customer interviews and representative job costing before buying hardware. The January 2026 Miyagi idle-land container-colocation announcement is an MOU to pursue a facility, not evidence that it was already operating. [MOU](https://www.tohoku-epco.co.jp/news/normal/1247944_2558.html) |
| **4. Nedia, Gunma: regional colocation and DR** | Current operator site positions the service as a second DC for backup/DR, with unit/rack hosting, UPS, generator, cooling, physical access controls and remote hands. [Facility/service](https://www.gunma-dc.jp/) | Current headline: **JPY 23,000/month+ per 1U**, **JPY 125,000/month+ per full rack**, tax-exclusive, electricity/cooling/network included, configurations and initial fees quoted. A separate itemized page lists 42U space at JPY 100,000/month, JPY 150,000 initial, excluding power; up to 3 kVA with generation is JPY 34,000/month and shared 100 Mbps JPY 30,000/month. These are different published offer structures, not interchangeable totals. [Itemized rates](https://www.nedia.ne.jp/service/dc-price) | Conventional hosting/backup can be modelled separately from GPU cloud. Useful for separating space, power, network and hands-on support. No named customer proof, annual PUE, capacity utilization or operator margin established by this review. Hanyu hazard suitability needs its own assessment. |
| **5. Sakura, Ishikari: larger modular GPU reference** | Container DC operational from 2025-06-11; completed May 2025. **40 racks**, **20 per container**, approximately **3.5 MVA** supply capacity, approximately **1,000 H200 GPUs**. DLC supports up to five servers per rack versus two in the operator's prior configuration. Planning-to-completion was about 18 months. [Release/specification](https://www.sakura.ad.jp/corporate/information/newsreleases/2025/06/11/1968219778/) | Real modular deployment, but materially larger and supported by an established operator. Release does not disclose project capex, annual whole-site PUE, utilization or realized pricing. 3.5 MVA is apparent supply capacity, not 3.5 MW IT load. | Upper-scale engineering reference; not the default Hanyu starting size. Its 18-month elapsed programme also cautions against interpreting every container vendor's short equipment lead time as total site delivery time. |

## Reuse precedent does not supply an inexpensive capex coefficient

Highreso's Ayagawa facility opened 2026-03-03 beneath the gymnasium of a former middle school, with approximately 1,008 m² and announced investment of **JPY 11 billion (110億円)**. Its school classrooms were planned for community use. The opening release lists H100/A4000 and future high-end additions, while the current business page lists H200. Preserve the dates rather than merging equipment descriptions. The disclosed total does not separate GPUs, electrical/cooling works, buildings, grants or phases; it cannot become a generic renovation cost per square metre. [Ayagawa opening](https://highreso.jp/press/40442/)

Another reuse example, Highreso Takamatsu, began operation in December 2024 in an underused research facility. The September 2026 operator announcement gives approximately 687 m² and JPY 10 billion investment, and describes a SINET6/IOWN connection enabling university/research access. Network availability is a route to a market, not proof of sold capacity. [Takamatsu/SINET6, 2026-09-24](https://highreso.jp/press/51135/)

## Japanese workload evidence

| Evidence | What it supports | What it does not support |
|---|---|---|
| **Senju Pharmaceutical customer interview**, information as of February 2024: GPU use for drug-discovery research, image analysis, JOIR and AlphaFold2; limited infrastructure expertise, upfront investment and security concerns influenced the choice. [Interview](https://soroban.highreso.jp/case-001) | A concrete Japanese research buyer persona; value in configuration/support as well as raw GPU time; a credible interview guide | Hanyu sales, recurring contracted volume, or a pharmaceutical customer ready to migrate |
| **GPUSOROBAN named customer accounts:** Tohoku University describes earthquake-fault estimation; Kyoto University quantum simulation; Skymatix crop classification and orthophoto generation for agricultural DX. [Operator case summaries](https://soroban.highreso.jp/aispacon) | Several distinct compute jobs beyond foundation-model training; useful candidate workload classes for feasibility tests | Audited spend, utilization, current purchasing intent or site-specific hosting location |
| **Tohoku Electric's July 2025 service change**, based on requests for just the required amount at scheduled times | Explicit evidence that smaller increments and short-duration access matter to some Japanese customers | A public addressable-market size or paid GPU-hour forecast |

Research and customer interviews can establish the first workload assumptions now. Later, pilots can measure job duration, GPU memory, CPU/storage requirements, data transfer, setup/support labour, reliability needs and willingness to pay. Contracts then support investment sizing if the project advances.

## Public GPU price benchmarks and normalization

These are customer-facing prices, not provider net revenue, profit, or guaranteed Hanyu selling prices. Rates were observed on 2026-10-01; availability and applicable terms require rechecking.

| Offer | Published unit and price | Normalization/caveat |
|---|---|---|
| GPUSOROBAN A4000 16 GB ×1 | JPY 50/hour or JPY 33,000/month | Tax included; customer selects hourly or monthly billing. Standard storage and transfer included. The page's separate hyperscaler comparison is explicitly dated April 2023; do not repeat it as a current market-wide price comparison. |
| GPUSOROBAN A100 40 GB ×1 / 80 GB ×1 | JPY 361 / 398 per hour; JPY 223,133 / 243,631 per month | Tax included; GPU model/memory and included host resources matter. These are separate products from A4000 and H100/H200. |
| Sakura VRT H100 SXM 80 GB ×1 | JPY 990/hour; JPY 23,100/day; JPY 385,000/month | Tax included; capped on-demand billing. Boot disk separately contracted; external network options may add cost. A continuously rented month cannot be modelled as 990 × 720 if the monthly cap applies. |
| GPUSOROBAN H200 | Eight H200 GPUs in one dedicated node; price by inquiry | 1,128 GB is node-total GPU memory. Do not convert eight-GPU node pricing into a one-GPU offer without matching minimum unit and interconnect. |

Sources: [GPUSOROBAN current plan table and billing notes](https://soroban.highreso.jp/compute), [Sakura official price/specification](https://cloud.sakura.ad.jp/products/server/gpu/), [Sakura VM configuration](https://cloud.sakura.ad.jp/lp/vrt/), [H200 product](https://soroban.highreso.jp/aispacon).

Illustrative arithmetic only: Sakura's JPY 385,000 cap corresponds to about JPY 534.72 per available hour in a 720-hour month, including tax, or JPY 486.11 excluding 10% consumption tax. This is a price normalization, not an operator utilization or revenue estimate. Maintain separate billing occupancy, GPU computational utilization and electrical load-factor variables.

## Power and cooling evidence relevant to a Hokuriku model

### Dated electricity structure

Use Hokuriku-area inputs for the Hanyu model, subject to the actual supplier, contract and connection. TEPCO or Genkai-area prices should only appear as separately labelled geographic comparators.

Hokuriku Electric's high-voltage page links its standard terms effective 2026-04-01. It lists, tax included:

- Business-use power: JPY 2,151/kW/month plus JPY 27.25/kWh
- Industrial high-voltage A, below 500 kW: JPY 1,876/kW/month plus JPY 27.53/kWh
- Industrial high-voltage B, 500 kW and above: JPY 2,151/kW/month plus JPY 26.34/kWh

These are menu components, not all-in bills. Do not assume the industrial classification applies to a data centre. Renewable surcharge, monthly fuel/market adjustment, power-factor adjustment and contract terms must be included. [Official high-voltage menu](https://www.rikuden.co.jp/jiyuka/ryokin2.html), [dated standard terms](https://www.rikuden.co.jp/jiyuka/attach/hyojunyakkan2_20260401.pdf)

The **2026-09-29** release gives October 2026 high-voltage fuel-plus-market adjustment of **minus JPY 7.81/kWh**, including **JPY 1.80/kWh temporary government relief**; the market component is zero. November fuel adjustment is **minus JPY 5.89/kWh**, with its market component due for announcement on October 29 and no relief. The release gives renewable surcharge of **JPY 4.18/kWh**. Do not carry temporary aid into a multi-year base case or treat a not-yet-fixed November market adjustment as zero. [Dated announcement, pp. 1–2](https://www.rikuden.co.jp/press/attach/26092901.pdf)

For contracts below 500 kW, the utility explains that monthly contract demand uses the highest 30-minute demand in the current and previous eleven months. A short peak can therefore influence a year of demand charges. [Billing mechanics](https://www.rikuden.co.jp/jiyuka/bizshikumi.html)

### Cooling claims: preserve the measurement boundary

NTTPC/Getworks/Fixstars reported **pPUE 1.114** on 2025-12-17 from a water-cooled GPU container proof-of-concept. Their definition covers the specific container server room, including room air conditioning and lighting, divided by that room's ICT load. It is not a measured annual whole-site PUE and does not establish Hanyu performance. [Primary release and definition](https://www.nttpc.co.jp/press/2025/12/202512171500.html)

Their technical write-up states that the tested CDU was liquid-to-air. For intermittent LLM inference, CDU-inclusive power was approximately equal to or slightly above the compared air-cooled server, despite lower temperatures. This is strong reason to benchmark the actual workload and total cooling boundary before claiming a universal water-cooling cost saving. [Technical results, 2025-12-16](https://www.nttpc.co.jp/gpu/article/benchmark28.html)

## FIN modelling implications, without changing existing values

1. **Keep alternatives separate.** Compare rented GPU pilot, GPU owned in third-party colocation, and owned local facility. Give conventional colocation/DR a separate revenue model. Avoid charging one customer both a full inclusive GPU-cloud tariff and a full inclusive rack tariff for the same resource.
2. **Use a workload-sized first phase.** Starter GPU/server count, then rack and power requirements, should be explicit scenario inputs. The public evidence does not justify a single universal starter kW figure. Model one deployment increment and show the cost and trigger for the next.
3. **Price by matching product.** Record GPU model, memory, node size, interconnect, duration, included CPU/RAM/storage/traffic/support, tax and monthly caps. Refresh price assumptions rather than treating GPU generations as interchangeable.
4. **Separate three utilization measures.** Sold/reserved hours, GPU busy time, and electrical load are different. Idle hardware, storage/networking, minimum cooling and fixed demand charges persist. A customer reserving a full node can pay while its GPUs are not continuously busy.
5. **Compute electricity from load profiles.** Estimate IT kWh from idle and active server draw plus storage/networking. Add cooling and facility power, or apply a boundary-consistent PUE, but do not add the same overhead twice. Apply dated energy adjustments and demand charges separately.
6. **Expose missing costs.** Site rights; structural/fire/seismic conversion; grid connection; transformers/switchgear; UPS and generation; cooling/water treatment; fibre and redundancy; GPU servers; storage/fabric; software; spares; remote hands; insurance; refresh and decommissioning. An empty building or a container shell is only part of the system.
7. **Scenario-test uncertainty.** Low/base/high cases should vary workload volume, achieved selling price, customer mix, hardware cost/refresh, electricity, cooling, staffing and capital timing. Mark these as assumptions, not observed comparable utilization or margin.
8. **Stage evidence, not invented certainty.** Public Japanese benchmarks support the first model. Local surveys and supplier quotes improve the design. Workload interviews/pilots improve demand and service assumptions. Binding commitments are relevant when accepting expenditure and expanding, rather than being required to start research.

## Concise Japanese inquiry questions

These are draft research questions only; no messages or forms were sent.

### Operator / equipment supplier

1. 初期導入を最小単位で始める場合、ラック数、実効IT電力（kW）、受電容量（kVA）、GPU構成と増設単位を教えてください。
2. 建屋・コンテナ、受変電、UPS・発電機、冷却、通信、GPU機器の費用を分けた概算と、補助金適用前の金額をいただけますか。
3. PUEまたはpPUEの測定範囲、測定期間、負荷率、季節条件と、低負荷時の実績を教えてください。
4. 表示料金の税込・税別、最低利用期間、電力・通信・保守の含有範囲、追加費用、解約条件を教えてください。
5. 公開可能な範囲で、主な顧客用途、導入時の規模、増設判断の基準をご教示ください。

### Utility / site owner

6. 対象施設で利用可能な供給電圧・容量、増設可能量、工事費負担、概算工期と適用料金メニューを確認できますか。
7. 基本料金、燃料費・市場価格調整、再エネ賦課金、力率割引を含む、想定負荷別の年間試算をいただけますか。
8. 既存施設の用途変更、床荷重、耐震・消防、騒音、冷却設備設置、通信引込について、確認が必要な条件は何ですか。

### Japanese workload interview

9. 現在どの処理に、どのGPU・メモリ容量を、月に何時間ほど使っていますか。処理待ち、費用、データ管理で困る点はありますか。
10. 必要な納期・稼働時間、データ容量、国内保管・秘密保持、障害時の許容時間を教えてください。
11. 少量の実データまたは公開データを使う試験で、処理時間、費用、運用支援の何が確認できれば採用を検討できますか。

## Research limitations

- No supplier, utility, municipality or customer was contacted; no quotations or private commercial data were obtained.
- No reviewed source supplies a dependable Hanyu-specific utilization, annual PUE, capex, margin or signed demand figure.
- Operator customer stories are attributable primary testimony, not independent audits. Named examples are research evidence only.
- GX's official indexed pages were readable in search results, but live retrieval failed; their numeric offers have lower verification confidence until reconfirmed.
- Retail prices and electricity adjustments change. Preserve source date, retrieval date, geographic scope, tax basis and billing unit with every imported assumption.
