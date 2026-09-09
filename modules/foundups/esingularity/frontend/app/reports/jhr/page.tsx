import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Japan Hyperscaler Report #001 | eSingularity",
  description:
    "印西で進むハイパースケール・データセンター集積と、福井が先回りして考えるべき地域分散型AIインフラ。",
  keywords: [
    "Japan Hyperscaler Report",
    "JHR",
    "日本 データセンター",
    "ハイパースケーラー",
    "印西 データセンター",
    "福井 データセンター",
    "GX戦略地域",
    "ワット・ビット連携",
    "AIインフラ",
    "COG DC",
    "eSingularity",
  ],
  alternates: { canonical: "https://esingularity.ai/reports/jhr" },
  openGraph: {
    title: "JHR #001 — 日本は『次の印西』を全国につくろうとしているのか",
    description: "巨大データセンターが地域を変える前に、福井はAIインフラを自分たちで設計できるか。",
    type: "article",
    url: "https://esingularity.ai/reports/jhr",
  },
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
    label: "R.E.port：DPDC印西パーク開発記事・航空写真",
    href: "https://www.re-port.net/article/news/0000074457/",
  },
];

export default function JapanHyperscalerReportPage() {
  return (
    <main style={{ maxWidth: 920, margin: "0 auto", padding: "48px 24px 96px", lineHeight: 1.75 }}>
      <p style={{ fontWeight: 700, letterSpacing: "0.08em" }}>JAPAN HYPERSCALER REPORT / JHR #001</p>
      <h1 style={{ fontSize: "clamp(2rem, 6vw, 4rem)", lineHeight: 1.08, marginBottom: 16 }}>
        日本は「次の印西」を全国につくろうとしているのか
      </h1>
      <p style={{ fontSize: "1.1rem", opacity: 0.8 }}>2026年9月 — 0102 / Project eSingularity</p>

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
          日本のデータセンター政策は、単なる施設誘致から、
          <strong>大規模データセンター集積地を国土政策として計画する段階</strong>
          に入っています。経済産業省の「データセンター集積型GX戦略地域」は、既存集積地以外の地方に新たな大規模拠点を形成し、電力・通信・関連産業を一体で整備する方向を明示しています。
        </p>
      </section>

      <section style={{ marginTop: 36 }}>
        <h2>GW級とは何か</h2>
        <p>
          政府資料では、将来的に10年程度で<strong>GW級</strong>へ拡張できることが選定要件の例として示されています。
          1GWは1,000MWです。eSingularityが検討する最初の1MW COG DCを「1」とすると、1GWはその<strong>1,000個分</strong>。20MW施設でも<strong>50個分</strong>です。
        </p>
      </section>

      <section style={{ marginTop: 36 }}>
        <h2>印西は成功例だけではない</h2>
        <p>
          千葉県印西市ではデータセンター集積が進む一方、生活圏に隣接する建設をめぐって市民意見、景観・騒音への懸念、地区計画の見直しなどが都市政策の課題になっています。
          問題はデータセンターの賛否だけではなく、土地、電力、住宅、農地、交通、景観を誰が先に設計するかです。
        </p>
      </section>

      <section style={{ marginTop: 36 }}>
        <h2>Fukui Signal</h2>
        <p>
          福井が現時点でハイパースケール集積の中心地として固定されていないことは、先回りする余地でもあります。
          土地取得や巨大系統予約が進む前に、1〜20MW級の分散拠点、既存建物再利用、地域電源、排熱利用、学校・大学・病院・企業への地域計算資源という別のインフラ設計を検証できます。
        </p>
      </section>

      <section style={{ marginTop: 36 }}>
        <h2>JHRが追跡するもの</h2>
        <p>
          47都道府県の政策・誘致・規制、GX戦略地域、系統接続、変電所・送電線、ハイパースケールキャンパス、農地・森林・寺社・集落周辺の土地転換、住民・農家・地権者の反応、ゾーニング、環境・水・騒音・排熱、税収・雇用・教育、そして福井が先回りできる政策機会を継続観測します。
        </p>
      </section>

      <section style={{ marginTop: 48 }}>
        <h2>Primary Sources / Visual Reference</h2>
        <ol>
          {sources.map((source) => (
            <li key={source.href} style={{ marginBottom: 10 }}>
              <a href={source.href} target="_blank" rel="noreferrer">{source.label}</a>
            </li>
          ))}
        </ol>
      </section>

      <footer style={{ marginTop: 56, paddingTop: 24, borderTop: "1px solid currentColor" }}>
        <p>#JapanHyperscalerReport #JHR #DataCenter #Hyperscaler #Inzai #Chiba #GX戦略地域 #ワットビット連携 #Fukui #福井 #COGDC #eSingularity</p>
        <p style={{ fontSize: ".9rem" }}>
          Truth boundary: JHRは公開情報に基づく調査報告です。計画・候補・認定・建設・稼働を区別し、未確認情報を確定事実として扱いません。
        </p>
      </footer>
    </main>
  );
}
