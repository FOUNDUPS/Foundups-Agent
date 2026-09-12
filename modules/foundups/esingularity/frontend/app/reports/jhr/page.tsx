import type { Metadata } from "next";

const YUMORI_ME = "https://yumori.me/";
const YUMORI_INFO = "https://yumori.info/";

export const metadata: Metadata = {
  title: "Japan Hyperscaler Report #001 | eSingularity",
  description:
    "日本全国のハイパースケール・データセンター政策、仙台200MW計画、印西の地区計画、福井の分散型AIインフラを日本語・英語で追跡。",
  keywords: [
    "Japan Hyperscaler Report",
    "JHR",
    "日本 データセンター",
    "ハイパースケーラー",
    "印西 データセンター",
    "仙台 AI データセンター",
    "福井 データセンター",
    "GX戦略地域",
    "ワット・ビット連携",
    "AIインフラ",
    "COG DC",
    "YUMORI.me",
    "eSingularity",
  ],
  alternates: { canonical: "https://esingularity.ai/reports/jhr" },
  openGraph: {
    title: "JHR #001 — 日本は『次の印西』を全国につくろうとしているのか",
    description: "仙台200MW、印西の地区計画、GX戦略地域。巨大化する前に福井は地域分散型AIインフラを選べるか。",
    type: "article",
    url: "https://esingularity.ai/reports/jhr",
  },
};

const sources = [
  {
    label: "経済産業省：GX戦略地域制度の有望地域（1次審査通過地域）",
    href: "https://www.meti.go.jp/press/2026/04/20260424007/20260424007.html",
  },
  {
    label: "内閣官房GX実行推進室：GX戦略地域制度に係る検討状況",
    href: "https://www.meti.go.jp/shingikai/enecho/denryoku_gas/jisedai_kiban/pdf/004_07_00.pdf",
  },
  {
    label: "fantasista：仙台市に200MW規模のAIデータセンターを開発へ",
    href: "https://prtimes.jp/main/html/rd/p/000000061.000093934.html",
  },
  {
    label: "印西市：印西牧の原駅圏の地区計画の変更等に係る説明会",
    href: "https://www.city.inzai.lg.jp/0000022189.html",
  },
  {
    label: "印西市：千葉ニュータウン中央駅圏の地区計画の変更等に係る説明会",
    href: "https://www.city.inzai.lg.jp/0000022309.html",
  },
  {
    label: "印西市：広報いんざい 令和8年9月号",
    href: "https://www.city.inzai.lg.jp/0000022304.html",
  },
  {
    label: "NTT DATA：印西・白井エリア 約250MWデータセンターキャンパス",
    href: "https://www.nttdata.com/global/ja/news/release/2026/041700/",
  },
  {
    label: "FERC：Large Load Integration action, June 2026",
    href: "https://www.ferc.gov/news-events/news/ferc-launches-aggressive-targeted-action-speed-large-load-integration",
  },
  {
    label: "New York State：Statewide hyperscale data-center moratorium, July 2026",
    href: "https://www.governor.ny.gov/news/first-statewide-moratorium-new-hyperscale-data-centers-launched-governor-kathy-hochul",
  },
  {
    label: "経済産業省：GX戦略地域制度",
    href: "https://www.meti.go.jp/policy/energy_environment/global_warming/gx_strategy_area.html",
  },
];

const tag = {
  display: "inline-block",
  padding: "3px 8px",
  border: "1px solid currentColor",
  borderRadius: 999,
  fontSize: ".78rem",
  fontWeight: 800,
  letterSpacing: ".04em",
  marginRight: 8,
} as const;

const button = {
  display: "inline-block",
  padding: "10px 14px",
  border: "1px solid currentColor",
  borderRadius: 999,
  color: "inherit",
  textDecoration: "none",
  fontWeight: 800,
  marginRight: 10,
  marginBottom: 10,
} as const;

export default function JapanHyperscalerReportPage() {
  return (
    <main style={{ maxWidth: 920, margin: "0 auto", padding: "48px 24px 96px", lineHeight: 1.78 }}>
      <p style={{ fontWeight: 800, letterSpacing: "0.08em" }}>JAPAN HYPERSCALER REPORT / JHR #001</p>
      <p style={{ fontWeight: 800 }}>追記 / ADDENDUM: 2026-09-12 · 本文 / MAIN REPORT: 2026-09-10</p>
      <h1 style={{ fontSize: "clamp(2rem, 6vw, 4rem)", lineHeight: 1.08, marginBottom: 16 }}>
        日本は「次の印西」を全国につくろうとしているのか
      </h1>
      <p style={{ fontSize: "1.1rem", opacity: 0.8 }}>0102 / Project eSingularity — 日本語を一次言語、英語を二次言語として掲載</p>
      <p>
        <a href={YUMORI_ME} target="_blank" rel="noreferrer" style={button}>YUMORI.me / JOIN</a>
        <a href={YUMORI_INFO} target="_blank" rel="noreferrer" style={button}>YUMORI.info / 資料</a>
      </p>

      <section id="latest" style={{ marginTop: 32, padding: 24, border: '2px solid #0b2d57', scrollMarginTop: 24 }}>
        <h2>最新動向｜2026年9月12日確認</h2>
        <p><strong>9月11日・仙台：</strong>fantasistaは、総受電容量200MW規模の計画について、米国の投資運用会社側と資金調達・協業の条件協議を始める基本合意を発表しました。資金調達の完了や開発許可の取得を意味しません。</p>
        <p><a href="https://prtimes.jp/main/html/rd/p/000000062.000093934.html" target="_blank" rel="noreferrer">事業者発表（9月11日） →</a></p>
        <p>全国で計画が具体化する中、福井ではどの規模・立地・地域還元が望ましいかを先に議論する必要があります。このニュースは、旧すかっとランド九頭竜周辺への立地決定を示すものではありません。</p>
      </section>
      <section id="land-area" style={{ marginTop: 32, scrollMarginTop: 24 }}>
        <h2>大きさは、MWだけでは比べられない</h2>
        <p>敷地面積と建物の延床面積は別の数字です。地図に重ねる比較には、敷地面積と原図の縮尺を使います。</p>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <caption style={{ textAlign: 'left', marginBottom: 12 }}>事業者公表の敷地面積</caption>
            <thead><tr><th>比較対象</th><th>敷地面積</th><th>同面積の正方形</th></tr></thead>
            <tbody>
              <tr><td><a href="https://www.daiwahouse.com/about/release/house/20220329190642.html">DPDC印西パーク</a></td><td>約270,000㎡（27ha）</td><td>一辺 約520m</td></tr>
              <tr><td><a href="https://prtimes.jp/main/html/rd/p/000000061.000093934.html">仙台・200MW計画</a></td><td>約71,787㎡（7.18ha）</td><td>一辺 約268m</td></tr>
            </tbody>
          </table>
        </div>
        <p>面積比は約3.76倍です（270,000 ÷ 71,787）。正方形の一辺は各面積の平方根を丸めたものです。実際の区画形状を示す数値ではありません。</p>
        <p>トップページの白枠は、比較用に指定された範囲です。原図には縮尺がないため、白枠を27haと認定したり、印西より大きい・小さいと断定したりすることはできません。距離の基準を確認後、同じ面積になるように調整します。</p>
      </section>

      <figure style={{ margin: "36px 0" }}>
        <img
          src="https://www.re-port.net/picture_l/report/0000074457_09.png"
          alt="千葉県印西市の大規模データセンター開発地を上空から見た写真"
          style={{ width: "100%", height: "auto", borderRadius: 12 }}
        />
        <figcaption style={{ fontSize: ".9rem", opacity: 0.8 }}>
          DPDC印西パーク建設地の航空写真。画像出典：R.E.port。規模理解のための外部参照画像で、eSingularity所有画像ではありません。
        </figcaption>
      </figure>

      <section style={{ marginTop: 48 }}>
        <h2>結論</h2>
        <p>
          日本のデータセンター政策は、単なる施設誘致から、<strong>大規模データセンター集積地を国土政策として計画する段階</strong>に入っています。
          経済産業省はデータセンター集積型GX戦略地域の有望地域として9道県を一次審査通過地域に選び、将来的なGW級への拡張、30ha以上を目安とする産業用地、電力、通信、水、交通、災害耐性、自治体のコミット、地域との共生を要件に置いています。
        </p>
        <p>
          同時に、印西では地区計画の変更が具体化し、2026年9月9日には仙台で200MW級AIデータセンター計画が事業者から公表されました。
          JHRが問うのは、日本が地方に「次の印西」を複数つくるだけなのか、それとも1〜20MW級の地域分散型・既存資産再利用型コンピュートを組み合わせられるのか、です。
        </p>
      </section>

      <section style={{ marginTop: 36 }}>
        <h2>1. 国家政策 — GX戦略地域</h2>
        <p><span style={tag}>OFFICIAL</span>2026年4月24日、METIは北海道、秋田、宮城、栃木、茨城、富山、香川、福岡、鹿児島の9道県を「データセンター集積型」の有望地域として公表しました。これは最終認定や個別開発許可ではなく、一次審査通過地域です。</p>
        <p><span style={tag}>OFFICIAL</span>選定要件には、10年程度でGW級へ拡張できる可能性、半径10km圏内で合計30ha以上を目安とする産業用地、通信、水、交通、災害耐性、段階的な立地、地域共生が含まれます。</p>
        <p><span style={tag}>ANALYSIS</span>これは一棟の誘致ではなく、複数DC、送変電、通信、関連産業を地域単位で集積させる政策です。30haは30万㎡、農地感覚では約300反です。「30haの田んぼを必ず潰す」という意味ではなく、国が想定する土地規模を理解する尺度です。</p>
      </section>

      <section style={{ marginTop: 36 }}>
        <h2>2. UPDATE — 仙台200MW AIデータセンター</h2>
        <p><span style={tag}>OFFICIAL / OPERATOR</span>fantasistaは2026年9月9日、仙台市青葉区の約71,787㎡の土地を活用し、総受電容量200MW規模のAIデータセンター開発を進める方針を公表しました。第Ⅰ期は2028年度中の開発許可取得を目指し、事業予算は約4,000億円としています。</p>
        <p><span style={tag}>TRUTH BOUNDARY</span>これは現時点で政府・自治体による開発許可ではありません。土地利用、インフラ、電力供給などは今後の協議対象です。</p>
        <p><span style={tag}>ANALYSIS</span>宮城県はすでにMETIのデータセンター集積型有望地域です。国の集積政策と民間の大型AIインフラ投資が同じ地域で重なり始めた重要なシグナルです。</p>
      </section>

      <section style={{ marginTop: 36 }}>
        <h2>3. 千葉・印西 — 集積からゾーニングへ</h2>
        <p><span style={tag}>OFFICIAL / UPDATE</span>印西市は2026年8月、データセンター等の建設をめぐる市独自ルールについて、複数の選択肢から都市計画法に基づく<strong>地区計画の変更</strong>を選択し、作業を進めていると公表しました。印西牧の原駅圏と千葉ニュータウン中央駅圏で説明会を予定し、印西牧の原東地区では8月4日に都市計画法に基づく決定がなされたと説明しています。</p>
        <p><span style={tag}>OFFICIAL</span>「広報いんざい」2026年9月号も3〜7面を「まちのルールをどう創る？〜データセンターと地区計画〜」に充てています。</p>
        <p><span style={tag}>ANALYSIS</span>印西は成功例だけではありません。集積が進むと、駅前、住宅、景観、騒音、地権者、生活圏との衝突を都市計画で扱う必要が出てくることを示しています。</p>
      </section>

      <section style={{ marginTop: 36 }}>
        <h2>4. 千葉・白井 — 200MW級キャンパスが続く</h2>
        <p><span style={tag}>OFFICIAL / OPERATOR</span>NTT DATAは2026年4月、白井市の印西・白井エリアで、6棟・総IT容量約200MWのTKY12キャンパス計画を公表しました。近隣のTKY11と合わせると約250MW規模です。</p>
        <p><span style={tag}>ANALYSIS</span>「印西問題」は一自治体だけではなく、白井を含む広域のハイパースケール・クラスターとして見る必要があります。</p>
      </section>

      <section style={{ marginTop: 36 }}>
        <h2>5. 米国比較 — 先に巨大集積した地域</h2>
        <p><span style={tag}>OFFICIAL / U.S.</span>FERCは2026年6月、6つの地域系統運用者に対し、データセンター等の大口需要家の系統接続ルールを正当化または改革するよう命じました。</p>
        <p><span style={tag}>OFFICIAL / U.S.</span>New York州は2026年7月、新規ハイパースケール・データセンターに1年間の州レベルのモラトリアムを設定し、送電・インフラ費用、環境、地域利益の新たな枠組みを整備すると発表しました。</p>
        <p><span style={tag}>ANALYSIS</span>米国では巨大集積が先行し、その後に電力料金、送電費、土地、水、騒音、税制、地域還元のルールが追いかけています。日本は同じ順序を繰り返す必要はありません。</p>
      </section>

      <section style={{ marginTop: 36 }}>
        <h2>6. Fukui Signal — 福井は先に選択肢をつくれる</h2>
        <p><span style={tag}>OFFICIAL</span>福井県は現時点でデータセンター集積型9道県には入っていません。一方、福井市と小浜市は別類型の「脱炭素電源活用型」の有望地域です。</p>
        <p><span style={tag}>ANALYSIS</span>これは「福井に巨大データセンターが来ることが決まった」という意味ではありません。しかし、AI需要、脱炭素電源、ワット・ビット連携、地方産業立地の方向を見ると、福井も先に土地・電力・地域利益のルールを持つべきです。</p>
        <p style={{ fontSize: "1.18rem", fontWeight: 800 }}>
          YUMORI.meの立場はデータセンター反対ではありません。田んぼ、山、集落の土地を何十haも集約する大型キャンパスだけを唯一の未来にしないことです。
        </p>
      </section>

      <section style={{ marginTop: 36 }}>
        <h2>7. ハイパースケール vs COG DC</h2>
        <h3>モデルA — ハイパースケール集積</h3>
        <ul>
          <li>100MW〜GW級へ拡張する大型キャンパス</li>
          <li>数十ha規模の産業用地</li>
          <li>大規模な送電・変電・通信増強</li>
          <li>大きな設備投資・税収の可能性</li>
          <li>土地、系統、景観、生活圏、住民合意への負荷が集中</li>
        </ul>
        <h3>モデルB — COG DC / 地域分散型</h3>
        <ul>
          <li>1MWから検証し、5→10→20MWへ需要に応じて拡張</li>
          <li>既存建物・既存インフラの再利用を優先</li>
          <li>学校、大学、病院、自治体、企業、農業への近距離コンピュート</li>
          <li>排熱を温泉、給湯、暖房、融雪、農業へ活用する可能性</li>
          <li>地域所有・地域利益・地域教育を事業設計に組み込む</li>
        </ul>
        <p><span style={tag}>ANALYSIS</span>分散型がハイパースケールを完全に代替するわけではありません。両方が必要になる可能性があります。JHRが問うのは、地域が「巨大施設を受け入れるか拒否するか」の二択になる前に第三の選択肢を持てるかです。</p>
      </section>

      <section style={{ marginTop: 36 }}>
        <h2>8. YUMORI.me — 壊す前に調べる</h2>
        <p>YUMORI.meは、旧すかっとランド九頭竜を解体する前に、60日間だけでも正式に再利用可能性を調べることを求めています。COG DC、温泉、教育、起業、文化の複合拠点として成立するかは未検証です。だからこそ、電力、通信、構造、資金、需要、温泉運営を先に調べる。</p>
        <p>
          <a href={YUMORI_ME} target="_blank" rel="noreferrer" style={button}>YUMORI.me / 参加・現場</a>
          <a href={YUMORI_INFO} target="_blank" rel="noreferrer" style={button}>YUMORI.info / 計画・資料</a>
        </p>
      </section>

      <hr style={{ margin: "64px 0 48px" }} />

      <section lang="en">
        <p style={{ fontWeight: 800, letterSpacing: ".08em" }}>ENGLISH / SECONDARY LANGUAGE</p>
        <h2 style={{ fontSize: "clamp(1.8rem,5vw,3rem)", lineHeight: 1.15 }}>Is Japan trying to create the “next Inzai” across the country?</h2>
        <p><strong>Bottom line:</strong> Japan is moving from attracting individual facilities toward planning large data-center clusters as national industrial infrastructure. METI has named nine prefectures as first-stage promising areas for its Data Center Concentration category, with criteria that contemplate gigawatt-scale expansion, roughly 30 hectares or more of industrial land, power, communications, water, resilience and community coexistence.</p>

        <h3>September 12 addendum — latest news and land-area comparison</h3>
        <p>On September 11, fantasista announced a basic agreement to begin financing and cooperation discussions with a U.S. investment manager&apos;s fund for the Sendai 200 MW total receiving-capacity project. This is not completed financing or development permission. <a href="https://prtimes.jp/main/html/rd/p/000000062.000093934.html">Operator announcement</a>.</p>
        <p>These developments support discussing scale, location and community benefit in Fukui early; they do not establish a project near the onsen.</p>
        <p>Published site areas: DPDC Inzai Park approximately 270,000 m² (27 ha), versus approximately 71,787 m² (7.18 ha) for Sendai. Inzai&apos;s area is about 3.76 times larger. Equivalent squares have sides of about 520 m and 268 m, calculated as the square root of each area. These are area comparisons, not actual plot shapes. <a href="https://www.daiwahouse.com/about/release/house/20220329190642.html">Daiwa House source</a>; <a href="https://prtimes.jp/main/html/rd/p/000000061.000093934.html">Sendai source</a>.</p>
        <p>Site area differs from total floor area, and MW alone does not determine land requirements. The homepage outline follows the area selected for comparison. The supplied map has no scale bar; its outline is not yet calibrated to 27 ha, and cannot yet establish whether the marked area is larger or smaller than Inzai. A known map distance is needed before an equal-area overlay can be finalized.</p>

        <h3>Sendai — 200 MW proposal</h3>
        <p><span style={tag}>OFFICIAL / OPERATOR</span>On September 9, 2026, fantasista announced a plan to advance a 200 MW AI data center on approximately 71,787 square meters in Aoba Ward, Sendai. Phase I targets development permission in FY2028 with an indicated project budget of roughly ¥400 billion. This is an operator decision, <strong>not yet a government development approval</strong>.</p>

        <h3>Inzai — from concentration to zoning</h3>
        <p><span style={tag}>OFFICIAL / UPDATE</span>Inzai City says it has chosen district-plan changes under the City Planning Act as the route for new local rules responding to data centers near stations and residential areas. Public explanation processes are underway for the Inzai-Makinohara and Chiba New Town Chuo station areas.</p>

        <h3>Chiba / Shiroi — hyperscale continues</h3>
        <p><span style={tag}>OFFICIAL / OPERATOR</span>NTT DATA has announced a six-building, approximately 200 MW IT-load campus in Shiroi. Together with nearby TKY11, the company describes an approximately 250 MW cluster.</p>

        <h3>U.S. comparison</h3>
        <p><span style={tag}>OFFICIAL / U.S.</span>FERC ordered regional grid operators in June 2026 to justify or reform rules for connecting data centers and other large loads. New York announced a one-year statewide moratorium on new hyperscale data centers in July 2026 while it develops stronger rules for infrastructure costs, environmental impacts and community benefits.</p>
        <p><span style={tag}>ANALYSIS</span>The U.S. pattern is often concentration first, followed by disputes over grid costs, land, water, noise, tax incentives and community benefits. Japan can design those rules earlier.</p>

        <h3>Fukui signal</h3>
        <p><span style={tag}>OFFICIAL</span>Fukui is not currently among the nine Data Center Concentration promising prefectures. Fukui City and Obama City are included in the separate Decarbonized Power Utilization category.</p>
        <p><span style={tag}>ANALYSIS</span>This does not mean a hyperscale campus is confirmed for Fukui. It means Fukui is already inside a national policy environment connecting clean power, industrial location and digital infrastructure. The YUMORI position is not anti-data-center: large greenfield campuses consuming tens of hectares should not become the only model.</p>

        <h3>Community-scale alternative</h3>
        <p>Before major land conversion, Fukui can test whether existing public buildings, factories, hotels, warehouses and hot-spring facilities can support modular 1→5→10→20 MW compute where structure, power, fiber, cooling and heat reuse make sense. Distributed compute will not replace every hyperscale facility. The point is to create a third option before communities face a binary accept-or-reject decision.</p>

        <p>
          <a href={YUMORI_ME} target="_blank" rel="noreferrer" style={button}>YUMORI.me / Join & field activity</a>
          <a href={YUMORI_INFO} target="_blank" rel="noreferrer" style={button}>YUMORI.info / Project material</a>
        </p>
      </section>

      <section style={{ marginTop: 56 }}>
        <h2>Primary Sources / Visual Reference</h2>
        <ol>
          {sources.map((source) => (
            <li key={source.href} style={{ marginBottom: 10 }}>
              <a href={source.href} target="_blank" rel="noreferrer">{source.label}</a>
            </li>
          ))}
        </ol>
      </section>

      <section style={{ marginTop: 48 }}>
        <h2>JHRが追跡するもの / Watchlist</h2>
        <p>47都道府県の政策・誘致・規制、GX戦略地域の最終認定、系統接続、変電所・送電線、キャンパス計画、農地・森林・集落周辺の土地転換、住民・農家・地権者の反応、ゾーニング、水、騒音、排熱、税収、雇用、教育、米国の規制・費用負担、福井の分散型政策機会を継続観測します。</p>
      </section>

      <footer style={{ marginTop: 56, paddingTop: 24, borderTop: "1px solid currentColor" }}>
        <p>#JapanHyperscalerReport #JHR #DataCenter #Hyperscaler #Inzai #Shiroi #Chiba #Sendai #Miyagi #GX戦略地域 #Fukui #福井 #COGDC #YUMORI #eSingularity</p>
        <p style={{ fontSize: ".9rem" }}>
          Truth boundary: JHRは公開情報に基づく調査報告です。候補、事業者方針、認定、開発許可、建設、稼働を区別し、未確認情報を確定事実として扱いません。 / JHR distinguishes candidate status, operator intent, designation, development approval, construction and operation.
        </p>
      </footer>
    </main>
  );
}
