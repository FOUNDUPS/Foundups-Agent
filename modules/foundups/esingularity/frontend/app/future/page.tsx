import Link from 'next/link';
import LineButton from '../../components/LineButton';
import Brand from '../../components/Brand';

const LINE_URL = 'https://line.me/ti/p/baXEozL_Q6';

const benefits = [
  ['♨️', '温泉', 'いまある地域の居場所を残し、もう一度人が集まる場所へ。'],
  ['🎓', '教育', '福井の学生と大学が、地域でAIを学び、試せる環境へ。'],
  ['🌾', '農業', '農業ロボット、ドローン、畑の見守りなどの研究を支える。'],
  ['🏭', '地域企業', '製造、設計、業務改善に使うAIを福井で育てる。'],
  ['🍜', '起業と食', '小さな店や台所から、地域の商いを始められる場所へ。'],
  ['👷', '仕事', '建設、運営、保守と、その周りに新しい地域の仕事を生む。'],
  ['💻', '福井の計算力', '福井の組織が使えるAI基盤を、福井につくる。'],
  ['🎨', '文化と観光', '祭り、季節の催し、D-Kの光で、新しい夜の目的地へ。'],
];

export default function FuturePage() {
  return (
    <>
      <header className="site-header team-site-header">
        <Brand href="/" />
        <nav aria-label="Primary navigation"><Link href="/">温泉を守る</Link><Link href="/#innovation-hub">AI拠点</Link><Link href="/future" aria-current="page">福井の未来</Link><Link href="/team">チーム</Link></nav>
        <LineButton />
      </header>

      <main className="future-page">
        <section className="future-hero">
          <p className="eyebrow light"><span /> FUKUI ECONOMIC FUTURE</p>
          <h1>福井に、<br /><em>何が残る？</em></h1>
          <p>データセンターをつくることが目的ではありません。温泉を中心に、学び、農業、仕事、商い、文化がつながる地域の土台をつくることが目的です。</p>
          <a className="button button-primary" href="#benefits">8つの地域価値を見る <span>↓</span></a>
        </section>

        <section className="future-benefits section" id="benefits" aria-labelledby="benefits-title">
          <div className="future-heading"><p className="eyebrow"><span /> WHAT FUKUI GETS</p><h2 id="benefits-title">計算機だけではない。<br /><em>地域に残る価値</em>です。</h2><p>一つひとつは小さく始められます。大切なのは、別々の事業にせず、温泉を中心に人と仕事が循環する仕組みにすることです。</p></div>
          <div className="benefit-grid" role="list">{benefits.map(([icon, title, body]) => <article key={title} role="listitem"><span aria-hidden="true">{icon}</span><div><h3>{title}</h3><p>{body}</p></div></article>)}</div>
        </section>

        <section className="money-loop section" aria-labelledby="loop-title">
          <p className="eyebrow light"><span /> KEEP VALUE IN FUKUI</p>
          <h2 id="loop-title">福井の電力から、<br /><em>福井の仕事へ。</em></h2>
          <div className="money-loop-flow" aria-label="福井の地域経済循環"><span>福井の電力</span><b>→</b><span>福井の計算力</span><b>→</b><span>福井の知恵</span><b>→</b><span>農業・教育・企業</span><b>→</b><span>仕事と地域所得</span></div>
          <p>すべての仕事やデータを地域内に限定するという意味ではありません。福井の組織が、自分たちの計算、モデル、知識、適切に管理されたデータを、より地域で扱える選択肢を増やすという使命です。</p>
        </section>

        <section className="growth section" aria-labelledby="growth-title">
          <p className="eyebrow"><span /> START SMALL · GROW WITH DEMAND</p>
          <h2 id="growth-title">小さく始める。<br /><em>必要な分だけ育てる。</em></h2>
          <p className="growth-lead">最初から巨大施設を約束しません。まず1 MWで需要、運営、熱利用を確かめます。その後は、電力、許認可、資金、利用者、地域の合意がそろった段階でだけ進みます。</p>
          <details className="growth-details">
            <summary>詳しく見る <span>段階的な計画</span></summary>
            <ol><li><span>2027–2028</span><strong>約1 MW</strong><p>最初の実証。需要と運営を確認します。</p></li><li><span>2029–2030</span><strong>合計 約5 MW</strong><p>実証後、必要性が確認できた場合に追加します。</p></li><li><span>2031–2033</span><strong>合計 約10 MW</strong><p>福井の利用が育った場合の地域拠点。</p></li><li><span>2034–2036</span><strong>合計 約15–20 MW</strong><p>地域需要が支える場合だけ拡張します。</p></li><li><span>長期の選択肢</span><strong>20–30 MW級</strong><p>敷地の可能性であり、建設の約束ではありません。</p></li></ol>
            <p className="growth-caveat">すべての段階は、北陸の電力網、許認可、土木・洪水・冷却設計、資金、利用契約、実際に使える敷地、地域合意が条件です。</p>
          </details>
        </section>

        <section className="future-cta">
          <p>いま必要なのは、投資ではなく地域の参加です。</p>
          <h2>温泉の次の未来を、<br />一緒に考えませんか。</h2>
          <div><a className="button button-primary" href={LINE_URL} target="_blank" rel="noreferrer">LINEに参加 <span>↗</span></a><Link className="button button-ghost" href="/">温泉を守る計画へ <span>←</span></Link></div>
        </section>
      </main>

      <footer><Brand href="/" /><p>ONSEN × LEARNING × LOCAL COMPUTE × COMMUNITY</p><a href={LINE_URL} target="_blank" rel="noreferrer">LINEで参加 ↗</a></footer>
    </>
  );
}
