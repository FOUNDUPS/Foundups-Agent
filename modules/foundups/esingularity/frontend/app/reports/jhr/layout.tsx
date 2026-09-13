import type { Metadata } from "next";
import type { ReactNode } from "react";

const YUMORI_ME = "https://yumori.me/";
const YUMORI_INFO = "https://yumori.info/";
const EVIDENCE_03 = "https://docs.google.com/document/d/1yeO6-6_mTLW8QswosVKmCVCHSRgWiacq-7FL7-9clsE/edit";

export const metadata: Metadata = {
  title: "Japan Hyperscaler Report | eSingularity",
  description: "JHRの最新号と過去号を1本の継続アーカイブとして掲載。福井のAI交番、COGDC、ハイパースケーラー政策を日本語・英語で追跡。",
  openGraph: {
    title: "Japan Hyperscaler Report — JHR #002: なぜ福井にAI交番が必要なのか",
    description: "巨大ハイパースケーラーだけに依存しない、地域所有のAIインフラという第三の選択肢。",
    images: [{ url: "/yumori-inzai-fukui-comparison.webp", width: 1600, height: 1200, alt: "千葉・印西クラスの大型データセンター用地を福井の田園に重ねた概念比較" }],
  },
  twitter: { card: "summary_large_image", images: ["/yumori-inzai-fukui-comparison.webp"] },
};

const pill = { display: "inline-flex", alignItems: "center", gap: 8, padding: "9px 13px", border: "1px solid currentColor", borderRadius: 999, color: "inherit", textDecoration: "none", fontWeight: 850, marginRight: 10, marginBottom: 10 } as const;
const tag = { display: "inline-block", padding: "3px 8px", border: "1px solid currentColor", borderRadius: 999, fontSize: ".78rem", fontWeight: 800, letterSpacing: ".04em", marginRight: 8 } as const;

export default function JhrLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <section id="jhr-002" style={{ maxWidth: 960, margin: "0 auto", padding: "48px 24px 8px", lineHeight: 1.78, scrollMarginTop: 96 }}>
        <article style={{ border: "1px solid #173b67", borderRadius: 20, overflow: "hidden", background: "#f8fbff", boxShadow: "0 24px 70px rgba(3,18,38,.14)" }}>
          <div style={{ padding: "36px clamp(22px,5vw,52px) 28px", background: "linear-gradient(145deg,#07172d,#0d2c54)", color: "#f6fbff" }}>
            <p style={{ margin: 0, fontWeight: 900, letterSpacing: ".1em", color: "#70ddff" }}>JAPAN HYPERSCALER REPORT / JHR #002 · 2026-09-14</p>
            <p style={{ margin: "10px 0 0", fontSize: ".94rem", opacity: .76 }}>NEWSLETTER ARCHIVE — 最新号を上に、過去号を下に積み重ねる継続記録</p>
            <h1 style={{ fontSize: "clamp(2.15rem,6vw,4.7rem)", lineHeight: 1.04, margin: "28px 0 18px", letterSpacing: "-.035em" }}>なぜ福井に「AI交番」が必要なのか</h1>
            <p style={{ fontSize: "1.12rem", maxWidth: 780, opacity: .9 }}>AI時代のインフラを、ただ誘致するのか。地域自身も持つのか。福井が巨大ハイパースケーラーだけに依存しないための第三の選択肢。</p>
            <p>
              <a href="#jhr-001" style={pill}>JHR #001へ ↓</a>
              <a href={EVIDENCE_03} target="_blank" rel="noreferrer" style={pill}>03｜根拠資料を読む</a>
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
            <p><strong>最初に、ハイパースケーラーそのものを敵にしません。</strong> 大規模クラウドと大規模データセンターは、日本のAI、産業、研究を支える重要なインフラです。問題は「来るか、来ないか」だけではありません。土地、電力、計算設備、データ、運営権、そしてAI時代に生まれる経済価値を、誰が所有し、誰が長期的に受け取るのかです。</p>
            <p>巨大データセンターは、大きな設備投資、固定資産税、建設需要、雇用を地域にもたらす可能性があります。一方で、施設の所有者、計算資源、主要顧客、利益配分、意思決定が地域外にある場合、地域が土地と電力を提供するだけで、AI経済の生産資本そのものを持てるとは限りません。<strong>「誘致」と「地域がAI資本を持つこと」は同じではありません。</strong></p>
            <p>だからJHRが問うのは、ハイパースケーラーへの賛否ではありません。日本の地域に、もう一つの選択肢をつくれるかです。</p>

            <h2>AI交番 — 地域が持つ小さなAIインフラ</h2>
            <p>YUMORI / eSingularityが提案するのが、<strong>COGDC — Community-Owned Green Data Center</strong>です。その地域モデルを「AI交番」と呼びます。</p>
            <p>交番は巨大な本部ではありません。地域の近くにあり、日常の需要に応え、必要な時には大きなネットワークにつながる小さな拠点です。AI交番も同じ発想です。</p>
            <p>学校、大学、農業、製造業、中小企業、自治体、研究機関が利用できる地域密着型の計算拠点を、小さく始める。地域自身がAIを学び、地域自身が一定の計算資源を持ち、データの扱いを選択できる能力を育てる。大規模な能力が必要な時には、国内外のクラウドにつなぐ。<strong>世界のクラウドを拒否するのではなく、地域が一方的に依存しない構造をつくる。</strong></p>
            <p><strong>AI交番は警察権限や住民監視システムを意味しません。</strong> 「地域の近くにある、小さく分散した、地域に責任を持つネットワーク拠点」という日本の交番の構造を、AIインフラの比喩として使っています。</p>

            <h2>なぜ旧すかっとランド九頭竜なのか</h2>
            <p>AIはソフトウェアだけでは動きません。半導体、建物、電力、通信、冷却、土地、資本が必要です。つまり、AIは物理インフラです。</p>
            <p>旧すかっとランド九頭竜には、すでに建物があります。温浴設備があります。地域があります。そして、再利用できるかどうかをまだ検証できる段階にあります。新しい土地を造成し、新しい巨大建物を建てる前に、既存の公共資産をAI時代の地域インフラへ転換できるかを調べることには、政策上の意味があります。</p>
            <p>構想は、1MW級から検証を始め、需要と成立性が確認できた場合に段階的に拡張するものです。計算資源を教育、大学・研究、農業、製造、起業、行政などへつなぎ、技術的に成立するならサーバー排熱を温泉、給湯、暖房、融雪、農業などに再利用する。<strong>建物を保存すること自体が目的ではなく、既存資産を新しい生産インフラへ変えられるかを検証することが目的です。</strong></p>

            <h2>9月25日に何を決めるのか</h2>
            <p>YUMORIが9月25日に求めているのは、COGDCの事業承認でも、市の出資でも、AI交番への公費投入でもありません。</p>
            <p><strong>解体を前提とする予算判断を先に確定させないことです。</strong></p>
            <p>成立するかどうかは、技術、構造、アスベスト、電力、通信、資金、収益、運営主体、地域便益を検証しなければ分かりません。だからこそ、再利用案を解体案と同じテーブルに載せ、同じ事実と基準で比較する必要があります。</p>
            <p style={{ fontSize: "1.2rem", fontWeight: 900 }}>解体は後からでもできます。解体した後に、この選択肢を検証することはできません。</p>
            <p><strong>9月25日：VOTE NO.</strong> YUMORI案に賛成する票ではありません。比較検証を終える前に、福井が持っている物理的な選択肢を消さないための票です。</p>
            <p>数字、政策整合、技術、法務、PPP/PFI再利用案、予算論点は、<a href={EVIDENCE_03} target="_blank" rel="noreferrer"><strong>公式キャンペーン文書03「解体準備予算反対・支援資料」</strong></a>に集約しています。賛成する前に、反対する前に、まず根拠を確認してください。</p>

            <hr style={{ margin: "50px 0" }} />

            <div lang="en">
              <p><span style={tag}>ENGLISH / SECONDARY</span></p>
              <h2>Why Fukui Needs an AI Koban</h2>
              <p>This is not an argument against hyperscalers. Large cloud and data-center infrastructure are important to Japan. The deeper question is ownership: who owns the land-intensive compute infrastructure, who controls it, and where the long-term economic value of the AI economy accumulates.</p>
              <p>A hyperscale campus can bring major capital investment, construction activity, taxes and jobs. But attracting infrastructure is not the same as a community owning productive AI capital. YUMORI / eSingularity therefore proposes a complementary model: <strong>COGDC — Community-Owned Green Data Center</strong>, with the community-scale node described as an <strong>AI Koban</strong>.</p>
              <p>A koban is not national headquarters. It is a small local node close to the community and connected to a much larger network. An AI Koban follows the same architecture: locally accountable compute, learning and data capability that connects outward to Japanese and global cloud infrastructure when larger capacity is needed.</p>
              <p><strong>AI Koban does not mean police authority or resident surveillance.</strong> It is a structural metaphor for small, distributed infrastructure close to the community.</p>
              <h3>Why test the option before demolition?</h3>
              <p>AI is physical infrastructure. It requires chips, buildings, transmission, cooling, electricity, land and capital. The former Sukatto Land Kuzuryu is an existing physical asset. The question is whether it can be repurposed before Fukui eliminates that option.</p>
              <p>YUMORI is not asking Fukui City to approve COGDC on September 25, and it is not asking the city to fund an AI Koban. It is asking for the reuse alternative to be tested against demolition using the same evidence and standards.</p>
              <p style={{ fontSize: "1.2rem", fontWeight: 900 }}>Demolition can happen later. Once demolished, this option cannot be tested.</p>
              <p><strong>September 25: VOTE NO.</strong> Preserve the option, test the evidence, then decide. The supporting economic, policy, technical, legal and PPP/PFI record is collected in <a href={EVIDENCE_03} target="_blank" rel="noreferrer">Campaign Document 03</a>.</p>
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
