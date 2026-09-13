import type { Metadata } from "next";
import type { ReactNode } from "react";

const YUMORI_ME = "https://yumori.me/";
const YUMORI_INFO = "https://yumori.info/";

export const metadata: Metadata = {
  title: "Japan Hyperscaler Report | eSingularity",
  description: "JHRの最新号と過去号を1本の継続アーカイブとして掲載。福井のAI交番、COGDC、ハイパースケーラー政策を日本語・英語で追跡。",
  openGraph: {
    title: "Japan Hyperscaler Report — JHR #002: なぜ福井にAI交番が必要なのか",
    description: "巨大ハイパースケーラーだけに依存しない、地域所有のAIインフラという第三の選択肢。",
    images: [
      {
        url: "/yumori-inzai-fukui-comparison.webp",
        width: 1600,
        height: 1200,
        alt: "千葉・印西クラスの大型データセンター用地を福井の田園に重ねた概念比較",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    images: ["/yumori-inzai-fukui-comparison.webp"],
  },
};

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

export default function JhrLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <section
        id="jhr-002"
        style={{ maxWidth: 960, margin: "0 auto", padding: "48px 24px 8px", lineHeight: 1.78, scrollMarginTop: 96 }}
      >
        <article style={{ border: "1px solid #173b67", borderRadius: 20, overflow: "hidden", background: "#f8fbff", boxShadow: "0 24px 70px rgba(3,18,38,.14)" }}>
          <div style={{ padding: "36px clamp(22px,5vw,52px) 28px", background: "linear-gradient(145deg,#07172d,#0d2c54)", color: "#f6fbff" }}>
            <p style={{ margin: 0, fontWeight: 900, letterSpacing: ".1em", color: "#70ddff" }}>JAPAN HYPERSCALER REPORT / JHR #002 · 2026-09-14</p>
            <p style={{ margin: "10px 0 0", fontSize: ".94rem", opacity: .76 }}>NEWSLETTER ARCHIVE — 最新号を上に、過去号を下に積み重ねる継続記録</p>
            <h1 style={{ fontSize: "clamp(2.15rem,6vw,4.7rem)", lineHeight: 1.04, margin: "28px 0 18px", letterSpacing: "-.035em" }}>なぜ福井に「AI交番」が必要なのか</h1>
            <p style={{ fontSize: "1.12rem", maxWidth: 780, opacity: .9 }}>ハイパースケーラーだけに依存しない。地域が自ら使い、学び、管理できる計算資源を持つという第三の選択肢。</p>
            <p>
              <a href="#jhr-001" style={pill}>JHR #001へ ↓</a>
              <a href={YUMORI_ME} target="_blank" rel="noreferrer" style={pill}>JOIN YUMORI.me</a>
              <a href={YUMORI_INFO} target="_blank" rel="noreferrer" style={pill}>eSingularity / 資料</a>
            </p>
          </div>

          <figure style={{ margin: 0, background: "#07172d" }}>
            <img src="/yumori-inzai-fukui-comparison.webp" alt="大型データセンター用地の規模を福井の田園に重ねた概念比較図" style={{ width: "100%", maxHeight: 500, objectFit: "cover" }} />
            <figcaption style={{ padding: "12px 24px 16px", fontSize: ".84rem", color: "#d7e9ff" }}>JHR visual comparison. 大規模集積のスケールを福井で考えるための概念図。福井で確定した建設計画を示すものではありません。</figcaption>
          </figure>

          <div style={{ padding: "34px clamp(22px,5vw,52px) 46px", color: "#06101c" }}>
            <p><span style={tag}>JAPANESE / PRIMARY</span></p>
            <p>日本のAI政策は、国内の計算資源、データセンター、地域でのAI実装、そして海外サービスへの過度な依存を減らす方向へ進んでいます。</p>
            <p>これはAWS、Google、Microsoftなどを排除するという話ではありません。巨大クラウドは必要です。問題は、AIが教育、農業、製造、行政、研究、地域産業そのものを支える時代に、日本の地域が永遠に「計算資源を借りる側」だけでよいのか、ということです。</p>

            <h2>AI交番とは何か</h2>
            <p>YUMORI / eSingularityが提案するのが、<strong>COGDC — Community-Owned Green Data Center</strong>です。その地域モデルを「AI交番」と呼びます。</p>
            <p>交番は本部ではありません。地域のすぐ近くにある小さな拠点で、必要な時にはより大きなネットワークにつながります。AI交番も同じです。</p>
            <p>学校、大学、農業、製造業、中小企業、自治体、地域研究などが利用できる、小規模で地域責任型のAI計算・学習・データ・ガバナンス拠点です。巨大なAI能力が必要なら国内外の大規模クラウドにつなぐ。しかし、すべてを外から借りるのではなく、福井自身も計算資源を持つ。福井自身もAIを学ぶ。福井自身もデータを管理する選択肢を持つ。福井で生まれる価値の一部を福井に残す。</p>
            <p><strong>AI交番は警察権限や住民監視システムを意味しません。</strong> 地域に近く、地域が責任を持てるAIインフラという設計思想です。</p>

            <h2>なぜ今、建物を壊す前に調べるのか</h2>
            <p>AIは、もはや単なるソフトウェアではありません。半導体、建物、送電、冷却、電力、土地、そして資本を必要とする物理インフラです。日本には、世界最先端を支える巨大AIインフラと、地域が自ら使い、学び、管理できる地域AIインフラの両方が必要です。</p>
            <p>福井は、その第二の層を実証できる可能性があります。その候補地が旧すかっとランド九頭竜です。</p>
            <p>YUMORIが求めているのは、9月25日にCOGDCを承認することでも、AI交番に公費を投入することでもありません。要求はもっと単純です。<strong>壊す前に調べること。</strong></p>
            <p>地域AI計算資源、教育、農業、ものづくり、起業、温浴施設、サーバー排熱利用を組み合わせた官民連携施設として再利用できるのか。成立しないなら、その結果を公開する。成立する可能性があるなら、解体案と比較する。それから決めればいい。</p>
            <p style={{ fontSize: "1.2rem", fontWeight: 900 }}>壊すことは後からでもできます。壊した建物を後から戻すことはできません。</p>
            <p><strong>9月25日：VOTE NO.</strong> これはYUMORI案への賛成票ではありません。比較検証を終える前に、地域AI基盤として使えるかもしれない物理的選択肢を消さないための票です。</p>

            <hr style={{ margin: "50px 0" }} />

            <div lang="en">
              <p><span style={tag}>ENGLISH / SECONDARY</span></p>
              <h2>Why Fukui Needs an AI Koban</h2>
              <p>Japan is moving toward more domestic computing capacity, data-center infrastructure, regional AI deployment, and less excessive dependence on overseas digital services.</p>
              <p>This is not an argument against AWS, Google, Microsoft, or global cloud infrastructure. Japan needs them. The question is whether Japanese communities should only rent the productive infrastructure of the AI economy as AI becomes essential to education, agriculture, manufacturing, government, research, and regional industry.</p>
              <h3>What is an AI Koban?</h3>
              <p>YUMORI / eSingularity proposes a <strong>COGDC — Community-Owned Green Data Center</strong>. We call the community-scale model an <strong>AI Koban</strong>.</p>
              <p>A koban is not national headquarters. It is a small local node close to the community and connected to a much larger network. An AI Koban follows the same architecture: a locally accountable node for compute, learning, data, and AI governance that can connect outward to larger Japanese and global cloud infrastructure when needed.</p>
              <p>The goal is choice: Fukui can own some compute, build AI skills, retain options over local data, and keep part of the value created by AI inside Fukui.</p>
              <p><strong>AI Koban does not mean police authority or resident surveillance.</strong> It is a design metaphor for AI infrastructure that is close to the community, accountable to the community, and connected to a larger network.</p>
              <h3>Why test the option before demolition?</h3>
              <p>AI is physical infrastructure. It requires chips, buildings, transmission, cooling, electricity, land, and capital. Japan needs both frontier-scale infrastructure and regional infrastructure that communities can use, understand, and govern.</p>
              <p>Fukui has an opportunity to test that second layer at the former Sukatto Land Kuzuryu. YUMORI is not asking Fukui City to approve COGDC on September 25, and it is not asking the city to fund an AI Koban. The request is simpler: <strong>test the option before destroying it.</strong></p>
              <p>Can the building be reused for regional compute, education, agriculture, manufacturing, entrepreneurship, onsen operations, and server heat recovery? If it does not work, publish the evidence. If it may work, compare it fairly against demolition. Then decide.</p>
              <p style={{ fontSize: "1.2rem", fontWeight: 900 }}>You can demolish a building later. You cannot restore the option after it is gone.</p>
              <p><strong>September 25: VOTE NO.</strong> Preserve the option. Test the evidence. Let Fukui investigate a community model of AI infrastructure before eliminating the physical asset that could host it.</p>
            </div>
          </div>
        </article>

        <div id="jhr-001" style={{ marginTop: 58, paddingTop: 28, borderTop: "4px solid #0b2d57", scrollMarginTop: 96 }}>
          <p style={{ fontWeight: 900, letterSpacing: ".08em" }}>ARCHIVE CONTINUES ↓ · JHR #001</p>
          <p style={{ opacity: .72 }}>以下は既存の第1号を保持しています。今後も新しい号をこの上に追加し、JHRの履歴を1本のページで追える構造にします。</p>
        </div>
      </section>
      {children}
    </>
  );
}
