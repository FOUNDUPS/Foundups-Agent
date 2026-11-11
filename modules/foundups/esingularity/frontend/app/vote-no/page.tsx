import type { Metadata } from 'next';
import CampaignTicker from '../../components/CampaignTicker';
import { councilMessage, mayorMessage } from '../../content/civic-messages';

const JOIN_URL = 'https://docs.google.com/forms/d/e/1FAIpQLScSKFyzCym8NCarvNIa5cT9c2Pe8C-cY2AbC4zLgsDOKspYKA/viewform';

export const metadata: Metadata = {
  title: '9月25日の公開記録と現在のPPP/PFI要請 — YUMORI.me',
  description: 'YUMORI.me設立準備委員会が福井市長・福井市議会へ送った、旧すかっとランド九頭竜の解体準備予算に関する要請の公開記録です。',
  alternates: { canonical: 'https://yumori.me/vote-no' },
};

export default function VoteNoPage() {
  return <main className="civic-page">
    <header className="civic-header">
      <a href="https://yumori.me/">YUMORI.me / 湯守</a>
      <nav aria-label="ページ内ナビゲーション">
        <a href="#council">市議会へのメッセージ</a>
        <a href="#mayor">市長へのメッセージ</a>
        <a href="#contact">声を届ける</a>
      </nav>
      <div id="home-language-controls" />
    </header>
    <CampaignTicker movement />
    <section className="civic-hero">
      <p className="civic-kicker">SAVE THE ONSEN / PUBLIC RECORD</p>
      <h1>採決は終わった。<br />比較検証は、まだできる。</h1>
      <p className="civic-lead">旧すかっとランド九頭竜を壊す前に、解体案とPPP／COGDCによる再利用案を、同じ証拠で比較してください。</p>
      <p className="civic-now"><strong>現在の要請：</strong> 9月25日の採決後は、不可逆な解体調達・工事へ進む前に、福井市がPPP/PFIの官民連携ルートを指定し、再利用案との比較検証、必要資料・現地調査へのアクセス、技術・財務・VFM・リスク分担の確認を行うことです。以下のVOTE NO文書は送付時点の歴史的公開記録です。</p>
      <div className="civic-actions"><a href="#contact">福井市長・市議会へ声を届ける</a><a href={JOIN_URL} target="_blank" rel="noreferrer">JOIN YUMORI.me / 湯守になる</a></div>
    </section>
    <section className="civic-content" aria-label="送付メッセージ公開記録">
      <article className="civic-record" id="council">
        <header><p className="civic-kicker">2026年9月10日 送付</p><h2>設立準備委員会から福井市議会へ</h2><p className="civic-meta">件名：9月25日 VOTE NO／反対票を — 旧すかっとランド九頭竜 解体準備予算に反対し、PPP・COGDC検証を</p></header>
        <details><summary>公開用本文を読む</summary><div className="civic-transcript">{councilMessage}</div></details>
      </article>
      <article className="civic-record" id="mayor">
        <header><p className="civic-kicker">2026年9月7日 送付</p><h2>設立準備委員会から福井市長へ</h2><p className="civic-meta">件名：9月25日の最終採決を延期し、YUMORI.me再利用案の独立検証を</p></header>
        <p className="civic-history"><strong>履歴注記：</strong> この文書は送付時点の記録です。採決延期・期限付き検証の要請はその後撤回され、9月25日の反対票要請も採決終了により歴史的記録となりました。現在はPPP/PFIによる解体案と再利用案の比較検証を求めています。</p>
        <details><summary>公開用本文を読む</summary><div className="civic-transcript">{mayorMessage}</div></details>
      </article>
      <section className="civic-contact" id="contact">
        <p className="civic-kicker">ACTION / 声を届ける</p><h2>温泉を守る意思を、届ける。</h2>
        <div className="civic-contact-grid">
          <a href="mailto:gikai@city.fukui.lg.jp?subject=%E6%97%A7%E3%81%99%E3%81%8B%E3%81%A3%E3%81%A8%E3%83%A9%E3%83%B3%E3%83%89%E4%B9%9D%E9%A0%AD%E7%AB%9C%E3%81%AEPPP%2FPFI%E6%AF%94%E8%BC%83%E6%A4%9C%E8%A8%BC%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6">福井市議会へメールする<small>議会事務局：gikai@city.fukui.lg.jp</small></a>
          <a href="https://www.city.fukui.lg.jp/sisei/kotyou/request/i-asking.html" target="_blank" rel="noreferrer">福井市へ意見を送る<small>福井市公式「ご意見・ご提案」ページ ↗</small></a>
        </div>
      </section>
      <p className="civic-source-note">公開用転記では、配信先の個人メールアドレス、BCC、個人連絡先、重複する資料リンクを除いています。政策・技術・費用に関する記述は送付時点の委員会の主張・仮説であり、行政の認定や事業成立を示すものではありません。</p>
    </section>
    <footer className="civic-footer"><a href="https://yumori.me/">YUMORI.meへ戻る</a>　·　<a href="https://yumori.info/">YUMORI.infoで再生構想を見る</a></footer>
  </main>;
}
