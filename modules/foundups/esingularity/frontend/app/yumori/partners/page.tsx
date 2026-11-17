import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '企業・団体の参加相談 | YUMORI.me',
  description: '福井の地域AI基盤を一緒に検討する企業・団体の代表者・AI担当者向けの参加相談窓口。',
  alternates: { canonical: 'https://yumori.me/partners' },
};

const INQUIRY_EMAIL = 'mike@foundups.org';
const subject = 'YUMORI.me｜企業・団体パートナー参加の相談';
const message = `YUMORI.me ご担当者様

企業・団体として、福井の地域AI基盤の検討に関心があります。

組織名：
公式ウェブサイト：
担当者名・役職（例：AI責任者／DX担当者）：
返信先メールアドレス：
関心分野（利用需要／運営／技術・設計／教育・研究／資金／地域連携）：
初回のご相談内容：

※これは参加・出資・契約の確約ではありません。`;
const inquiryUrl = 'mailto:' + INQUIRY_EMAIL + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(message);
const panel = { padding: 'clamp(40px,7vw,88px) 6vw' } as const;
const cta = { display:'inline-block',padding:'14px 22px',borderRadius:999,background:'#f4f1e8',color:'#0b0d0c',textDecoration:'none',fontWeight:850 } as const;

export default function PartnersPage() {
  return <main className="yumori-page" style={{background:'#0b0d0c',color:'#f4f1e8',minHeight:'100vh',fontFamily:'system-ui,sans-serif'}}>
    <header className="yumori-header"><a href="https://yumori.me/">YUMORI.me / 湯守</a><div id="home-language-controls" /></header>
    <section style={{...panel,background:'#172119'}}>
      <p style={{fontWeight:850,letterSpacing:'.14em'}}>福井 / 企業・団体の参加相談</p>
      <h1 style={{fontSize:'clamp(2.2rem,6vw,4.6rem)',lineHeight:1.07,margin:'18px 0'}}>福井のAI基盤を、<br/>ともにつくるために。</h1>
      <p style={{maxWidth:800,fontSize:'clamp(1rem,1.7vw,1.25rem)',lineHeight:1.85}}>福井の企業、大学、研究・教育機関、農業関係者、設備・運営事業者の皆さまへ。経営者やAI責任者、DX担当者など、組織を代表して話し合える方を募集します。正式なChief AI Officerの肩書きは必要ありません。</p>
      <p style={{maxWidth:800,lineHeight:1.85}}>初回は15分程度の意見交換から始め、計算需要、地域のデータ管理、運営・技術条件や事業化の可能性について伺います。必要に応じてYUMORI.me設立準備委員会の発起人（僧・カズル泰澄）との面談を調整します。参加は法的な共同提案、資金拠出、建設・運営への同意を意味しません。</p>
      <a href={inquiryUrl} style={cta}>企業・団体の相談メールを作成 →</a>
      <p style={{opacity:.8,fontSize:14,marginTop:18}}>メールアプリが開き、日本語のひな形を編集して送信できます。自動送信ではありません。現在、専用オンラインフォームは未接続です。</p>
    </section>
    <section style={panel}>
      <h2 style={{fontSize:'clamp(1.6rem,4vw,2.8rem)'}}>一緒に検討すること</h2>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,260px),1fr))',gap:18,maxWidth:1050}}>
        {[
          ['地域の需要','企業・大学・農業・医療・教育機関の実際の計算需要を確認する'],
          ['技術と運営','経験ある運営事業者と電力・通信・設備・維持管理を検討する'],
          ['地域への還元','データの管理、地元の仕事、学習、土地・環境への影響を検討する'],
        ].map(([heading,description])=><article key={heading} style={{background:'#172119',borderRadius:18,padding:24}}><h3>{heading}</h3><p style={{lineHeight:1.8}}>{description}</p></article>)}
      </div>
      <p style={{lineHeight:1.9,maxWidth:950,marginTop:32}}>福井市の旧羽生小学校を初期候補として検討中です。旧下宇坂小学校は教育・拡張の候補であり、旧すかっとランド九頭竜は別の条件付き資産です。施設利用権・電力容量・需要契約・資金・行政承認・運営参加は未確定です。実現可能性と地域利益を調べ、成立しない条件も公開できる検証を目指します。</p>
      <p><a href="https://esingularity.ai/" style={{color:'inherit',fontWeight:800}}>eSingularity.ai / 福井の計画と技術構想 →</a></p>
      <p><a href="/reports/jhr" style={{color:'inherit',fontWeight:800}}>ジャパン・ハイパースケーラー・レポート（JHR）を読む →</a></p>
      <p><a href="https://yumori.me/" style={{color:'inherit'}}>YUMORI.me の運動に戻る →</a></p>
    </section>
  </main>;
}
