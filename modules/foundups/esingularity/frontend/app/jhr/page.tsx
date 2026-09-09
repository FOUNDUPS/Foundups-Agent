import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Japan Hyperscaler Report #001 | eSingularity",
  description:
    "印西で起きているハイパースケール・データセンター集積と、福井が今から考えるべき地域分散型AIインフラ。",
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
  alternates: { canonical: "https://esingularity.ai/jhr" },
  openGraph: {
    title: "JHR #001 — 印西から福井が学ぶべきこと",
    description: "巨大データセンターが地域を変える前に、福井はAIインフラを設計できるか。",
    type: "article",
    url: "https://esingularity.ai/jhr",
  },
};

const sources = [
  {
    label: "経済産業省 — GX戦略地域制度（2026年4月24日）",
    href: "https://www.meti.go.jp/press/2026/04/20260424007/20260424007.html",
  },
  {
    label: "経済産業省 — GX戦略地域制度",
    href: "https://www.meti.go.jp/policy/energy_environment/global_warming/gx_strategy_area.html",
  },
  {
    label: "印西市 — 駅周辺等のまちづくりに関する新ルール検討",
    href: "https://www.city.inzai.lg.jp/0000019530.html",
  },
  {
    label: "印西市 — 印西牧の原東地区地区計画変更（2026年8月31日）",
    href: "https://www.city.inzai.lg.jp/0000022249.html",
  },
  {
    label: "R.E.port — DPDC印西パーク航空写真・開発記事",
    href: "https://www.re-port.net/article/news/0000074457/",
  },
];

export default function JapanHyperscalerReport() {
  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "48px 20px 96px", lineHeight: 1.8 }}>
      <p style={{ letterSpacing: ".12em", fontWeight: 700 }}>JAPAN HYPERSCALER REPORT / JHR #001</p>
      <h1 style={{ fontSize: "clamp(2rem, 6vw, 4.5rem)", lineHeight: 1.05 }}>
        印西から福井が学ぶべきこと
      </h1>
      <p style={{ fontSize: "1.25rem" }}>
        巨大データセンターが地域を変える前に、福井はAIインフラを自分たちで設計できるか。
      </p>
      <p><strong>発行:</strong> 0102 / Project eSingularity　<strong>日付:</strong> 2026-09-09</p>

      <figure style={{ margin: "36px 0" }}>
        <img
          src="https://www.re-port.net/picture_l/report/0000074457_09.png"
          alt="千葉県印西市 DPDC印西パークの大規模データセンター建設地の航空写真"
          style={{ width: "100%", height: "auto", borderRadius: 12 }}
        />
        <figcaption style={{ fontSize: ".9rem" }}>
          DPDC印西パーク建設地の航空写真。画像出典: R.E.port（大和ハウス工業の開発地公開記事）。
          本画像は規模を理解するための外部参照画像で、eSingularity所有画像ではありません。
        </figcaption>
      </figure>

      <h2>結論</h2>
      <p>
        日本は、AI時代の電力需要に対応するため、データセンターを東京・大阪周辺だけに集中させず、
        新しい地域へ分散させる政策段階に入っています。ただし、現在の中心的な発想は
        「巨大な集積地を別の地域にもつくる」ことです。これは真の地域分散型コンピューティングとは同じではありません。
      </p>

      <h2>印西では、すでに「データセンター問題」が都市政策になった</h2>
      <p>
        印西市は2025年、駅周辺や生活圏に隣接するデータセンター開発について、市民からさまざまな意見が寄せられていると公式に認め、
        市独自の新しいまちづくりルールの検討を開始しました。さらに2026年8月31日の都市計画変更資料では、
        駅周辺のデータセンター建設について<strong>景観・騒音への懸念</strong>が顕在化していると明記しています。
      </p>
      <p>
        これは重要です。問題は「データセンターが良いか悪いか」ではありません。
        土地、電力、景観、住宅、学校、交通、農地、地域経済を含む<strong>都市そのものの設計問題</strong>になったということです。
      </p>

      <h2>福井は「遅れている」のではない</h2>
      <p>
        2026年4月、経済産業省が公表したGX戦略地域の一次審査では、データセンター集積型として9地域が選ばれました。
        福井県はその9地域には入っていません。
      </p>
      <p>
        しかし同じ制度の<strong>脱炭素電源活用型</strong>では、福井市と小浜市が有望地域に選ばれています。
        つまり福井には「巨大DC集積地の後追い」以外の入口があります。
      </p>

      <h2>eSingularityの問い</h2>
      <p>
        日本の地方分散は、9個、20個、50個の「次の印西」を造るだけでよいのでしょうか。
        それとも1MW、5MW、10MW、20MW級の計算資源を既存建物、地域電源、学校、大学、産業、温浴施設などと結び、
        廃熱まで地域で使う<strong>Community-Owned Green Data Center (COG DC)</strong>という別の層も必要でしょうか。
      </p>
      <p>
        福井がまだ巨大ハイパースケール集積地として固定されていないことは、弱点ではなく設計余地です。
        土地と送電容量が先に押さえられ、地域が後から対応するのではなく、今の段階で
        「福井ではAI計算資源をどう配置し、誰が利益を得て、熱と電力をどう地域に戻すか」を議論できます。
      </p>

      <h2>JHRが追跡するもの</h2>
      <p>
        JHRは、国のGX・ワットビット政策、47都道府県の誘致・規制、電力系統、ハイパースケール計画、
        土地利用、住民・農家・寺院・地域団体の反応、地方議会、新聞・ラジオなどを継続的に追跡します。
        ニュースを量産することが目的ではありません。重要な変化があり、複数の証拠で確認できた場合だけレポート候補を作ります。
      </p>

      <h2>出典</h2>
      <ul>
        {sources.map((source) => (
          <li key={source.href}>
            <a href={source.href} target="_blank" rel="noreferrer">{source.label}</a>
          </li>
        ))}
      </ul>

      <p style={{ marginTop: 42, fontWeight: 700 }}>
        #JapanHyperscalerReport #JHR #データセンター #ハイパースケーラー #印西 #福井
        #GX戦略地域 #ワットビット連携 #AIインフラ #COGDC #eSingularity
      </p>
      <p style={{ fontSize: ".9rem" }}>
        Truth boundary: JHRは公開情報に基づく調査報告です。計画・候補・認定・稼働を区別し、未確認情報を確定事実として扱いません。
      </p>
    </main>
  );
}
