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
          <h1 style={{ margin: "0 0 12px", fontSize: "clamp(2.2rem,7vw,5.5rem)", lineHeight: 1.02, letterSpacing: "-.045em" }}>
            これが、20年後の福井でいいですか？
          </h1>
          <p style={{ margin: "0 0 24px", fontSize: "clamp(1rem,2.2vw,1.45rem)", lineHeight: 1.65, maxWidth: 920 }}>
            千葉・印西で進む大規模データセンター集積を、福井の田園のスケールで考える。これは福井で確定した計画ではありません。公開情報に基づく概念比較です。
          </p>
          <figure style={{ margin: 0 }}>
            <img
              src="/yumori-inzai-fukui-comparison.webp"
              alt="千葉・印西クラスの大規模データセンター用地を福井の田園に重ねた概念比較図"
              style={{ width: "100%", height: "auto", display: "block", borderRadius: "18px 18px 0 0" }}
            />
          </figure>
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
