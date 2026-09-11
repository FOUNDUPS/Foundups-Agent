import type { Metadata } from "next";
import type { ReactNode } from "react";

const YUMORI_ME = "https://yumori.me/";
const YUMORI_INFO = "https://yumori.info/";

export const metadata: Metadata = {
  openGraph: {
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

const signal = {
  padding: "18px 20px",
  background: "#fff",
  border: "1px solid rgba(11,45,87,.14)",
  borderRadius: 14,
} as const;

export default function JhrLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <header
        aria-label="Japan Hyperscaler Report visual introduction"
        style={{
          background: "#f4f1e8",
          color: "#0b2d57",
          padding: "clamp(28px,5vw,64px) 5vw 0",
        }}
      >
        <div style={{ maxWidth: 1180, margin: "0 auto" }}>
          <p style={{ margin: "0 0 8px", fontWeight: 900, letterSpacing: ".12em", fontSize: ".82rem" }}>
            JAPAN HYPERSCALER REPORT / JHR
          </p>
          <p style={{ margin: "0 0 12px", fontWeight: 900, fontSize: "clamp(2.2rem,7vw,5.5rem)", lineHeight: 1.02, letterSpacing: "-.045em" }}>
            これが、20年後の福井でいいですか？
          </p>
          <p style={{ margin: "0 0 24px", fontSize: "clamp(1rem,2.2vw,1.45rem)", lineHeight: 1.65, maxWidth: 920 }}>
            千葉・印西で進む大規模データセンター集積を、福井の田園のスケールで考える。これは福井で確定した計画ではありません。公開情報に基づく概念比較です。
          </p>
          <figure style={{ margin: 0 }}>
            <img
              src="/yumori-inzai-fukui-comparison.webp"
              alt="千葉・印西クラスの大規模データセンター用地を福井の田園に重ねた概念比較図"
              style={{ width: "100%", height: "auto", display: "block", borderRadius: 18 }}
            />
            <figcaption style={{ margin: "10px 0 0", fontSize: ".82rem", lineHeight: 1.55, opacity: .72 }}>
              概念比較図。福井でこの規模の開発が決定したことを示すものではありません。
            </figcaption>
          </figure>

          <section aria-label="JHR #001 key signals" style={{ padding: "24px 0 28px" }}>
            <p style={{ margin: "0 0 12px", fontWeight: 900, letterSpacing: ".1em", fontSize: ".78rem" }}>3 SIGNALS / まず知ってほしい3点</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 12 }}>
              <div style={signal}>
                <strong style={{ display: "block", fontSize: "1.45rem" }}>30ha+ / GW級</strong>
                <span style={{ display: "block", marginTop: 6, lineHeight: 1.55 }}>国のデータセンター集積型GX戦略地域で想定される候補地スケール。個別案件の確定値ではありません。</span>
              </div>
              <div style={signal}>
                <strong style={{ display: "block", fontSize: "1.45rem" }}>仙台 200MW</strong>
                <span style={{ display: "block", marginTop: 6, lineHeight: 1.55 }}>2026年9月に事業者が公表したAIデータセンター構想。現時点で自治体の開発許可を意味しません。</span>
              </div>
              <div style={signal}>
                <strong style={{ display: "block", fontSize: "1.45rem" }}>福井の第三の選択肢</strong>
                <span style={{ display: "block", marginTop: 6, lineHeight: 1.55 }}>巨大集積かゼロかではなく、既存資産を再利用する1〜20MW級COG DCを先に検証できるかを問います。</span>
              </div>
            </div>
          </section>

          <div style={{ background: "#0b2d57", color: "#fff", padding: "16px clamp(16px,3vw,28px)", display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center", justifyContent: "space-between" }}>
            <strong>日本語を一次言語として掲載。全国47都道府県の政策・系統・立地・地域影響を追跡。</strong>
            <span style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
              <a href={YUMORI_ME} style={{ color: "#fff", fontWeight: 850 }}>YUMORI.me ↗</a>
              <a href={YUMORI_INFO} style={{ color: "#fff", fontWeight: 850 }}>YUMORI.info ↗</a>
            </span>
          </div>
        </div>
      </header>
      {children}
    </>
  );
}
