# 福井県 eSingularity Labs ノード・アーキテクチャ

Date: 2026-09-16  
Status: public concept / feasibility architecture  
Owner: Project eSingularity (`esingularity_001`)

## Decision

福井県を **eSingularity Labs のパイオニア都道府県ノード**として検証する。

このノードは一つの会社が全事業・全投資を抱えるモデルではない。上位に **産学官民連携の地域共創ガバナンス**を置き、その下に分野別の事業体・SPV／SPC・運営契約を配置する。

福井県で成立した標準、ソフトウェア、需要調査、運営知見、教育プログラム、ガバナンス手順を共有しながら、将来は条件の合う各都道府県に一つずつ地域主体のノードを展開する。全国展開は福井での技術・需要・資金・運営検証に依存し、現時点の確約ではない。

## 1. 上位構造 — 産学官民連携の地域共創組織

想定する参加レイヤー：

- **官** — 福井県、市町、関係行政機関
- **学** — 大学、短大、高専、研究機関、学校教育関係者
- **産** — 地域企業、運営会社、技術事業者、投資家
- **民** — 地域住民、利用者、地権者、地域団体
- **伴走** — eSingularity Labs

上位組織は、地域ミッション、情報公開、利益相反、地域還元、共通の安全・データ・AI利用原則を扱う。個別事業の損益や投資リスクを一つに混在させない。

## 2. 分野別サテライト事業

各事業は、必要に応じて独立したSPV／SPC、運営法人、テナント契約、公的連携事業として組成する。

### COGDC / AI交番 — 計算基盤

- 地域需要向けの小規模・段階型AI計算基盤
- 地産地消型AIクラウド
- GPU / CPU / storage / networking / private AI / security
- 地域内データ処理と、必要時の国内・グローバルクラウドへのフェデレーション
- データセンター投資家と運営事業者を、飲食・温浴等の事業リスクから分離

### 温泉・ウェルネス

- 温浴、休憩、健康、地域交流
- 計算事業からの地域還元候補
- 排熱利用は技術・経済検証後に導入
- 温泉会計は計算事業と分離

### レストラン / フード

- 店舗ごとのテナント、運営会社、または小規模SPV
- 飲食を理解する投資家・事業者が参加できる構造
- 地元食材、創業支援、来訪者消費の地域循環

### 教育プログラム

- 学校向け来訪型AI教育
- 教員AI研修
- 探究学習、PBL、ロボット / Physical AI、0102との課題解決体験
- 学校AIルーム / 分岐ノードへの展開
- 公的連携、委託、補助、協賛等を組み合わせた無償または低廉な教育利用枠を検証

### 起業・研究・実証

- FoundUps / AI-native small teams
- 大学・企業との共同研究
- 地域課題のプロトタイプと現場実証
- 事業ごとに独立した投資・研究・契約構造を選択

### エネルギー・蓄電・廃熱利用

- BESS、受変電、冷却、再エネ、熱交換、ヒートポンプ等
- 計算設備とは別の設備金融・補助制度・事業体を比較可能にする

## 3. 地産地消型AIクラウド

中核原則：

> **地域で生み出した計算資源を、まず地域で使う。**

目的は、福井県の計算能力を域外へ大量販売することではない。学校、大学、研究、医療、製造、農業、中小企業、行政、起業家等が、地域で使える安全かつ手頃な計算基盤を持つことを第一に検証する。

ハイパースケーラーや国内大規模クラウドを置き換えるものではない。地域ノードで適切な処理を行い、規模や機能が不足する場合は外部インフラへ接続する補完型アーキテクチャとする。

## 4. 電子フィージビリティ（e-FS）— 需要から容量を決める

**1MWを先に決めない。**

企業、大学、学校、医療、農業、行政等がオンラインで要求を入力し、集約された需要から設備規模を逆算する。

最低取得項目：

- 現在のcloud / GPU spend
- workload type / data size
- GPU type / memory / interconnect
- GPU-hours per month
- start date / contract term
- maximum acceptable price
- data residency / security requirements
- discovery / interest / LOI / reservation / paid pilot / contract の状態

出力：

`workloads → concurrency → GPU/CPU/storage/network → IT kW → facility kW → phased build`

100kW、300kW、600kW、1MW等は入力ではなく **需要から導く候補値**とする。既存FINモデルの約1MW / 384 GPUは比較用の内部仮置きであり、確定したPhase 1仕様ではない。

## 5. 教育ハブ — 既存教育制度へ接続する

新しい教育行政を発明するのではなく、既存の福井県教育制度へ接続する。

接続候補：

- 福井県教育庁
- 福井県教育総合研究所（教職研修センター等）
- 市町教育委員会（例：坂井市教育委員会）
- 県内8高等教育機関（大学・短大・高専等）
- 福井県DX推進課 / 県民向けサービス連携基盤（技術的接続候補）

### 来訪型プログラム

学校はバス等で福井県ノードを訪問し、AI基礎、対話型課題解決、ロボット、PBL、大学・起業家・技術者による講義やワークショップを利用できる。温泉・地域文化体験は任意の付加プログラムとし、教育利用だけでも完結可能とする。

### 教員研修

AI活用、授業設計、評価、著作権、個人情報、セキュリティ、安全運用を扱う。福井県教育総合研究所等の既存研修へ、地域AI計算資源を利用した実証メニューとして接続できるかを検討する。

### 学校AIルーム / 分岐ノード

各学校が大規模GPU設備を購入する代わりに、既存PC室等を安全なAI利用拠点へ段階的に拡張する。重い処理、モデル、データ管理、共通セキュリティは福井県ノード側で提供する構造を検討する。

## 6. Founder / partner layer

### 九頭龍 泰澄 / UnDaoDu / Michael James Trout

- EDUIT founder; long-running Educational Singularity / eSingularity thesis
- NCDS capital-campaign / feasibility experience
- FoundUps / distributed organization / AI agent work
- film / media production background
- international technology, startup, investment and blockchain network

Founder history is context, not proof of technical or financial feasibility. Detailed profile remains in YUMORI document 04 / `monk.YUMORI.info`.

### Jorge Sebastian

Technical advisor / collaborating partner for feasibility and infrastructure translation.

Public background references describe 30+ years in technology and innovation, former CTO of Huawei Technologies, technology leadership across multiple countries, Dubai-based work, and a DeCenter technology leadership role. For this project, the intended function is to help convert measured workloads and service requirements into capacity, architecture, networking, security, vendor and operating requirements.

Final contractual, investment and operating roles remain to be documented.

## 7. Diagram assets

The current Japanese concept diagrams are embedded in YUMORI document 03:

- `fukui_esingularity_labs_regional_ai_network.png` — overall Fukui pioneer-node / satellite-business / prefectural-network architecture
- `福井県ai教育ハブの未来図.png` — education hub / teacher training / school branch-node architecture

**Repository note:** the present GitHub connector can write UTF-8 text but cannot upload the generated PNG binaries. The semantic architecture is therefore committed here; binary asset synchronization remains a separate repo action.

## 8. Truth boundaries

- Participation by government, universities, schools or companies is not implied until independently documented.
- Community-owned means community-level governance and retained rights must be defined legally; the label alone is insufficient.
- Education compute may be targeted as free / low-cost, but this is not guaranteed until funding and allocation rules are established.
- Local data processing does not remove the need for privacy, cybersecurity, procurement and education-sector compliance.
- Jorge Sebastian's exact legal/contractual role must be documented separately.
- Network relationships are reach and access, not endorsements or financing commitments.
- Fukui is the proposed pioneer node; other prefectural nodes are a future replication hypothesis.

## Canonical relationship

- **eSingularity.ai** — project vision and canonical semantic layer
- **YUMORI.me** — civic movement / join surface
- **YUMORI document 03** — city/prefecture/council evidence + current architecture
- **FIN.YUMORI** — scenario and demand model
- this document — repository recovery point for the Fukui Labs node architecture
