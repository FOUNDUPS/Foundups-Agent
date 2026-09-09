import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Japan Hyperscaler Report | eSingularity",
  description:
    "Japan's hyperscale data-center policy, grid, land-use and community response — tracked from Chiba/Inzai to Fukui.",
  keywords: [
    "Japan Hyperscaler Report",
    "JHR",
    "Japan data center",
    "Hyperscaler",
    "Inzai",
    "Chiba",
    "GX戦略地域",
    "ワット・ビット連携",
    "Fukui",
    "COG DC",
    "eSingularity",
  ],
};

const sources = [
  {
    label: "経済産業省：GX戦略地域 公募要領（データセンター集積型）",
    href: "https://www.meti.go.jp/policy/energy_environment/global_warming/gx_strategy_area/Yoryo_2.pdf",
  },
  {
    label: "内閣官房GX実行推進室：GX戦略地域制度に係る検討状況",
    href: "https://www.meti.go.jp/shingikai/enecho/denryoku_gas/jisedai_kiban/pdf/004_07_00.pdf",
  },
  {
    label: "経済産業省：データセンター集積型における課題と方向性",
    href: "https://www.meti.go.jp/shingikai/sankoshin/shin_kijiku/pdf/030_01_00.pdf",
  },
  {
    label: "印西市：駅周辺等のまちづくりに関する新たなルールづくり",
    href: "https://www.city.inzai.lg.jp/0000019530.html",
  },
  {
    label: "印西市：令和8年第2回定例記者会見",
    href: "https://www.city.inzai.lg.jp/0000021271.html",
  },
];

export default function JapanHyperscalerReportPage() {
  return (
    <main style={{ maxWidth: 920, margin: "0 auto", padding: "48px 24px 96px", lineHeight: 1.75 }}>
      <p style={{ fontWeight: 700, letterSpacing: "0.08em" }}>JAPAN HYPERSCALER REPORT / JHR 001</p>
      <h1 style={{ fontSize: "clamp(2rem, 6vw, 4rem)", lineHeight: 1.08, marginBottom: 16 }}>
        日本は「次の印西」を全国につくろうとしているのか
      </h1>
      <p style={{ fontSize: "1.1rem", opacity: 0.8 }}>
        2026年9月 — eSingularity.ai
      </p>

      <section style={{ marginTop: 48 }}>
        <h2>結論</h2>
        <p>
          日本のデータセンター政策は、単なる施設誘致から、
          <strong>大規模データセンター集積地を国土政策として計画する段階</strong>
          に入っています。経済産業省の「データセンター集積型GX戦略地域」は、
          既存集積地以外の地方に新たな大規模拠点を形成し、電力・通信・関連産業を
          一体で整備する方向を明示しています。
        </p>
      </section>

      <section style={{ marginTop: 36 }}>
        <h2>GW級とは何か</h2>
        <p>
          政府資料では、将来的に10年程度で<strong>GW級</strong>へ拡張できることが選定要件の例として示されています。
          1GWは1,000MWです。eSingularityが検討する最初の1MW COG DCを「1」とすると、
          1GWはその<strong>1,000個分</strong>。20MWまで拡張した施設でも<strong>50個分</strong>です。
        </p>
      </section>

      <section style={{ marginTop: 36 }}>
        <h2>印西は成功例だけではない</h2>
        <p>
          千葉県印西市ではデータセンター集積が進む一方、生活圏に隣接する建設をめぐって
          市民意見、署名、訴訟、地区計画の見直しが表面化しています。市長はデータセンターを
          必要な産業・地域パートナーと評価しながらも、共存には<strong>ゾーニング</strong>と
          事業者の地域貢献が重要だと説明しています。
        </p>
      </section>

      <section style={{ marginTop: 36 }}>
        <h2>Fukui Signal</h2>
        <p>
          福井が現時点でハイパースケール集積の中心地として固定されていないことは、
          先回りする余地でもあります。土地取得や巨大系統予約が進む前に、1〜20MW級の
          分散拠点、既存建物再利用、地域電源、排熱利用、教育・大学・病院・企業への地域計算資源という
          別のインフラ設計を検証できます。
        </p>
      </section>

      <section style={{ marginTop: 36 }}>
        <h2>JHRが追跡するもの</h2>
        <p>
          47都道府県の政策・誘致・規制、GX戦略地域、系統接続、変電所・送電線、
          ハイパースケールキャンパス、農地・森林・寺社・集落周辺の土地転換、住民・農家・地権者の反応、
          ゾーニング、環境・水・騒音・排熱、税収・雇用・教育、そして福井が先回りできる政策機会を継続観測します。
        </p>
      </section>

      <section style={{ marginTop: 48 }}>
        <h2>Primary Sources</h2>
        <ol>
          {sources.map((source) => (
            <li key={source.href} style={{ marginBottom: 10 }}>
              <a href={source.href} target="_blank" rel="noreferrer">
                {source.label}
              </a>
            </li>
          ))}
        </ol>
      </section>

      <footer style={{ marginTop: 56, paddingTop: 24, borderTop: "1px solid currentColor" }}>
        <p>
          #JapanHyperscalerReport #JHR #DataCenter #Hyperscaler #Inzai #Chiba #GX戦略地域
          #ワットビット連携 #Fukui #福井 #COGDC #eSingularity
        </p>
      </footer>
    </main>
  );
}
