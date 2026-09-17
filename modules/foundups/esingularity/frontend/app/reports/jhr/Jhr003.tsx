const YUMORI_ME = "https://yumori.me/";
const YUMORI_INFO = "https://yumori.info/";

const pill = {
  display: "inline-flex",
  alignItems: "center",
  gap: 8,
  padding: "9px 13px",
  border: "1px solid currentColor",
  borderRadius: 999,
  color: "inherit",
  textDecoration: "none",
  fontWeight: 850,
  marginRight: 10,
  marginBottom: 10,
} as const;

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

const sourceLink = {
  color: "inherit",
  fontWeight: 750,
} as const;

export default function Jhr003() {
  return (
    <section id="jhr-003" style={{ maxWidth: 960, margin: "0 auto", padding: "48px 24px 8px", lineHeight: 1.78, scrollMarginTop: 96 }}>
      <article style={{ border: "1px solid #173b67", borderRadius: 20, overflow: "hidden", background: "#f8fbff", boxShadow: "0 24px 70px rgba(3,18,38,.14)" }}>
        <header style={{ padding: "36px clamp(22px,5vw,52px) 30px", background: "linear-gradient(145deg,#07172d,#123a68)", color: "#f6fbff" }}>
          <p style={{ margin: 0, fontWeight: 900, letterSpacing: ".1em", color: "#70ddff" }}>JAPAN HYPERSCALER REPORT / JHR #003 · 2026-09-17</p>
          <p style={{ margin: "10px 0 0", fontSize: ".94rem", opacity: .76 }}>JAPANESE / PRIMARY · ENGLISH / SECONDARY</p>
          <h1 style={{ fontSize: "clamp(2.1rem,6vw,4.55rem)", lineHeight: 1.04, margin: "28px 0 18px", letterSpacing: "-.035em" }}>
            「計算主権」の時代へ — なぜ日本にAI交番が必要なのか
          </h1>
          <p style={{ fontSize: "1.12rem", maxWidth: 800, opacity: .92 }}>
            欧州中央銀行総裁のAI主権論、日本のワット・ビット連携、そして福井市のGX戦略地域候補。巨大データセンターだけでは埋まらない、地域分散型コンピュートの空白を考える。
          </p>
          <p>
            <a href="#jhr-002" style={pill}>JHR #002へ ↓</a>
            <a href={YUMORI_ME} target="_blank" rel="noreferrer" style={pill}>JOIN YUMORI.me</a>
            <a href={YUMORI_INFO} target="_blank" rel="noreferrer" style={pill}>eSingularity / 資料</a>
          </p>
        </header>

        <div style={{ padding: "34px clamp(22px,5vw,52px) 48px", color: "#06101c" }}>
          <p><span style={tag}>JAPANESE / PRIMARY</span></p>

          <p><strong>AIは、もはやソフトウェアだけの問題ではありません。</strong> 電力、半導体、通信、データセンター、冷却、土地、そして誰が計算資源を所有・運営するのかという物理インフラの問題です。</p>

          <p>
            2026年9月14日、欧州中央銀行（ECB）のクリスティーヌ・ラガルド総裁はウィーンでの講演で、米国が世界のAI計算能力のおよそ4分の3を保有する一方、欧州は約5%にとどまると指摘しました。さらに、外国のAI基盤への依存は、データ、法域、アクセス条件、重要サービスの継続性に関わると論じています。これは「外国技術を使うべきではない」という話ではありません。<strong>重要なのは、社会が必要とする計算能力を、自らも一定程度持てるかどうかです。</strong>{" "}
            <a href="https://www.ecb.europa.eu/press/key/date/2026/html/ecb.sp260914_2~a3f0efbee4.en.html" target="_blank" rel="noreferrer" style={sourceLink}>ECB講演 →</a>
          </p>

          <h2>日本も、同じ構造問題に直面している</h2>
          <p><span style={tag}>OFFICIAL</span>資源エネルギー庁の「エネルギー白書2025」によれば、2023年時点で日本のデータセンター面積の約90%が東京圏・大阪圏に集中しています。白書は、大規模災害時のデジタルインフラ維持や、地方の土地・産業用水・系統余力の活用という観点から、地域分散が重要だとしています。</p>
          <p>
            さらに政府は、電力インフラとデジタルインフラを一体で考える「ワット・ビット連携」を掲げています。電力を大量に遠距離送電するだけでなく、電力側から見て望ましい地域にデータセンターを誘導し、通信で需要地と結ぶ考え方です。{" "}
            <a href="https://www.enecho.meti.go.jp/about/whitepaper/2025/html/1-2-2.html" target="_blank" rel="noreferrer" style={sourceLink}>エネルギー白書2025 →</a>
          </p>

          <h2>そして福井市は、すでにこの政策地図の中にいる</h2>
          <p><span style={tag}>OFFICIAL</span>2026年4月24日、経済産業省はGX戦略地域制度の一次審査を通過した「有望地域」を公表しました。そのうち<strong>脱炭素電源活用型</strong>として、福井県の<strong>福井市・小浜市</strong>が選ばれています。これは最終認定ではありませんが、福井市が国のGX産業立地政策の検討対象に入っていることを意味します。</p>
          <p>
            <a href="https://www.meti.go.jp/press/2026/04/20260424007/20260424007.html" target="_blank" rel="noreferrer" style={sourceLink}>経済産業省：GX戦略地域 有望地域 →</a>
          </p>

          <aside style={{ margin: "30px 0", padding: "24px", borderLeft: "5px solid #0b5ea8", background: "#edf6ff" }}>
            <p style={{ marginTop: 0, fontWeight: 900, fontSize: "1.15rem" }}>ここで福井市に問うべきこと</p>
            <p style={{ marginBottom: 0 }}>福井市自身がGX、脱炭素電源、デジタルインフラの新しい産業立地を国と検討しているなら、既存公共資産を地域AIインフラへ転換できる可能性を、解体前に比較検証する価値はないのか。</p>
          </aside>

          <h2>AI交番は、ハイパースケーラーの代替ではない</h2>
          <p><span style={tag}>ANALYSIS</span>巨大なハイパースケール・データセンターは、基盤モデルの学習、大規模クラウド、全国規模のサービスに必要です。AI交番は、それを置き換える構想ではありません。</p>
          <p>AI交番は、地域の近くに置く小規模・分散型の計算拠点です。学校、大学、研究、農業、製造、中小企業、自治体などが共有できる計算能力を地域に持ち、必要に応じて国内外の大規模クラウドへ接続する。交番が警察本部ではなく、地域に近いネットワーク拠点であるのと同じ発想です。</p>
          <p><strong>大規模計算は上流へ。日常的で地域密着型の計算は地域へ。</strong> この階層構造が、AI時代のレジリエンスと地域所有の両方をつくります。</p>

          <h2>旧すかっとランド九頭竜が検証場所になり得る理由</h2>
          <p><span style={tag}>ANALYSIS</span>旧すかっとランド九頭竜には、既存建物、温浴設備、地域インフラがあります。データセンターは電力を計算に変え、その過程で大量の熱を出します。一方、温浴施設は熱を必要とします。技術的・経済的に成立するなら、サーバー排熱を給湯、浴槽、暖房、融雪などに利用できる可能性があります。</p>
          <p>ただし、これは現時点で成立が証明された事業ではありません。受電容量、系統接続、光回線、構造、耐震、アスベスト、冷却、排熱回収効率、資金、需要、運営主体を調査する必要があります。</p>
          <p><strong>だから必要なのは、信じることではなく、比較することです。</strong></p>

          <h2>福井市にとっての実務的な選択肢</h2>
          <p>市に求めるべき最初の判断は「AI交番を採用するか」ではありません。次の二つを同じ基準で比較できる状態をつくることです。</p>
          <ol>
            <li><strong>解体：</strong>解体費、将来の跡地利用、失われる既存資産価値。</li>
            <li><strong>適応再利用：</strong>建物を残し、地域AI計算拠点、教育・研究、温浴、排熱利用を組み合わせられるか。</li>
          </ol>
          <p>国家政策が地域分散、ワット・ビット連携、GX産業立地へ動いている今、比較せずに物理的選択肢を消すこと自体が政策上の判断になります。</p>

          <h2>AIギガファクトリーからAI交番まで</h2>
          <p>AI時代の国家インフラは、一種類のデータセンターだけでは構成されません。</p>
          <p style={{ fontSize: "1.15rem", fontWeight: 900 }}>ハイパースケーラーは「主権の規模」を担う。AI交番は「主権の分散」を担う。</p>
          <p>日本が必要とするのは、どちらか一方ではなく、大規模計算、地域計算、エッジ計算をつなぐ階層型の計算基盤です。福井は、その地域層を先に実証できる可能性があります。</p>

          <h2>一次資料</h2>
          <ul>
            <li><a href="https://www.ecb.europa.eu/press/key/date/2026/html/ecb.sp260914_2~a3f0efbee4.en.html" target="_blank" rel="noreferrer" style={sourceLink}>ECB — Christine Lagarde, “A new age of capital: growth, sovereignty and AI,” 2026-09-14</a></li>
            <li><a href="https://www.enecho.meti.go.jp/about/whitepaper/2025/html/1-2-2.html" target="_blank" rel="noreferrer" style={sourceLink}>資源エネルギー庁 — エネルギー白書2025 第1部第2章第2節</a></li>
            <li><a href="https://www.meti.go.jp/press/2026/04/20260424007/20260424007.html" target="_blank" rel="noreferrer" style={sourceLink}>経済産業省 — GX戦略地域制度の有望地域（1次審査通過地域）</a></li>
            <li><a href="https://www.meti.go.jp/policy/energy_environment/global_warming/gx_strategy_area.html" target="_blank" rel="noreferrer" style={sourceLink}>経済産業省 — GX戦略地域制度</a></li>
          </ul>

          <hr style={{ margin: "54px 0" }} />

          <div lang="en">
            <p><span style={tag}>ENGLISH / SECONDARY</span></p>
            <h2>The Age of Compute Sovereignty — Why Japan Needs an AI Koban</h2>
            <p><strong>AI is no longer only a software issue.</strong> It is a physical-infrastructure question involving electricity, semiconductors, networks, data centers, cooling, land, and ultimately who owns and operates computing capacity.</p>
            <p>On September 14, 2026, European Central Bank President Christine Lagarde noted that the United States hosts roughly three-quarters of global AI computing capacity while Europe hosts about 5%. She argued that dependence on foreign AI infrastructure raises questions involving data, jurisdiction, access conditions and continuity of critical services. The point is not that societies should reject foreign technology. It is that they should retain meaningful computing capability of their own.</p>

            <h3>Japan faces the same structural problem</h3>
            <p>Japan's Energy White Paper 2025 states that approximately 90% of Japanese data-center floor area was concentrated in the Tokyo and Osaka regions in 2023. It explicitly argues for regional dispersion to support disaster resilience and make better use of regional land, water and grid capacity.</p>
            <p>Japan is also pursuing “Watt-Bit collaboration”: planning electricity and digital infrastructure together, locating compute where power infrastructure is advantageous and connecting that compute to demand centers through communications networks.</p>

            <h3>Fukui City is already on this policy map</h3>
            <p>On April 24, 2026, METI named Fukui Prefecture — specifically Fukui City and Obama City — among the first-stage promising locations in the decarbonized-power utilization category of the GX Strategic Area program. This is not final designation, but it places Fukui City inside a national policy process focused on new industrial clusters built around decarbonized power.</p>

            <h3>Where the AI Koban fits</h3>
            <p>An AI Koban is not a replacement for hyperscalers. Hyperscale facilities are required for frontier training, large cloud services and national-scale workloads. The AI Koban fills a different layer: small, distributed, locally accountable compute serving schools, universities, research, agriculture, manufacturing, SMEs and public-sector workloads, while connecting upward to larger domestic or international cloud capacity when needed.</p>
            <p><strong>Large compute goes upstream. Routine and locality-sensitive compute can remain closer to the community.</strong></p>

            <h3>Why test Sukatto Land Kuzuryu?</h3>
            <p>The former Sukatto Land Kuzuryu already contains a building, bathing infrastructure and a local physical footprint. Computing converts electricity into computation and heat; bathing facilities require heat. If engineering and economics support it, server heat could potentially contribute to hot-water production, space heating or snow melting.</p>
            <p>This has not yet been proven for the site. Electrical capacity, grid connection, fiber, structural condition, seismic requirements, asbestos, cooling, heat-recovery efficiency, financing, demand and governance all require investigation. That is precisely why the immediate decision should be whether to compare adaptive reuse with demolition before the physical option disappears.</p>

            <h3>From AI gigafactories to AI Koban</h3>
            <p style={{ fontSize: "1.15rem", fontWeight: 900 }}>Hyperscalers provide sovereign scale. AI Koban provides sovereign distribution.</p>
            <p>A resilient Japanese AI infrastructure can use both: large national and regional facilities linked to smaller community compute nodes. Fukui may have an opportunity to test that missing community layer.</p>
          </div>
        </div>
      </article>
    </section>
  );
}
