import Link from 'next/link';
import LineButton from '../../components/LineButton';
import Brand from '../../components/Brand';

const LINE_URL = 'https://line.me/ti/p/baXEozL_Q6';

const benefits = [
  ['♨️', '温泉', 'いまある地域の居場所を残し、もう一度人が集まる場所へ。'],
  ['🎓', '教育', '福井の学生と大学が、AIを学び、実課題に試せる環境へ。'],
  ['🌾', '農業', '農業ロボット、ドローン、畑の見守りなどの研究を支える。'],
  ['🏭', '地域企業', '製造、設計、業務改善に使うAIを福井で育てる。'],
  ['🍜', '起業と食', '小さな店や台所から、地域の商いを始められる場所へ。'],
  ['👷', '仕事', '改修、運営、保守と、その周りに新しい地域の仕事を生む可能性を調べる。'],
  ['💻', '私たちのCOG DC', 'そこで働く人とプロジェクトが使えるコンピュートをつくる。'],
  ['🎨', '文化と観光', '祭り、季節の催し、提案するD-Kの光で、新しい夜の目的地へ。'],
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
          <p>データセンターをつくることだけが目的ではありません。温泉を中心に、学び、農業、仕事、商い、文化がつながり、そこで働く人とプロジェクトが私たちのCOG DCコンピュートを使える土台を検証します。</p>
          <a className="button button-primary" href="#benefits">8つの地域価値を見る <span>↓</span></a>
        </section>

        <section className="future-benefits section" id="benefits" aria-labelledby="benefits-title">
          <div className="future-heading"><p className="eyebrow"><span /> WHAT FUKUI GETS</p><h2 id="benefits-title">計算機だけではない。<br /><em>地域に残る価値</em>です。</h2><p>一つひとつは小さく始められます。大切なのは、別々の事業にせず、温泉を中心に人と仕事が循環する仕組みにすることです。</p></div>
          <div className="benefit-grid" role="list">{benefits.map(([icon, title, body]) => <article key={title} role="listitem"><span aria-hidden="true">{icon}</span><div><h3>{title}</h3><p>{body}</p></div></article>)}</div>
        </section>

        <section className="money-loop section" aria-labelledby="loop-title">
          <p className="eyebrow light"><span /> KEEP VALUE IN FUKUI</p>
          <h2 id="loop-title">COG DCの電力から、<br /><em>福井の仕事へ。</em></h2>
          <div className="money-loop-flow" aria-label="COG DCから福井の地域経済へつながる流れ"><span>電力</span><b>→</b><span>私たちのCOG DCコンピュート</span><b>→</b><span>学生・FoundUps</span><b>→</b><span>農業・教育・企業</span><b>→</b><span>解決策と仕事</span></div>
          <p>すべての仕事やデータを地域内に限定するという意味ではありません。COG DCで働く人とプロジェクトが、計算、モデル、知識、適切に管理されたデータを使い、福井の実課題に取り組める選択肢を増やします。</p>
        </section>

        <section className="growth section" aria-labelledby="growth-title">
          <p className="eyebrow"><span /> START SMALL · GROW WITH DEMAND</p>
          <h2 id="growth-title">小さく始める。<br /><em>必要な分だけ育てる。</em></h2>
          <p className="growth-lead">最初から巨大施設を約束しません。まず約1 MWを検討単位として、需要、工学、経済性、熱利用を確かめます。実際の利用が成長を正当化するときだけ、次の段階を検討します。</p>
          <details className="growth-details">
            <summary>詳しく見る <span>段階的な検証</span></summary>
            <ol><li><span>01</span><strong>需要を確認</strong><p>学生、FoundUps、研究、地域プロジェクトが何を使うかを具体化します。</p></li><li><span>02</span><strong>工学を確認</strong><p>電力、通信、冷却、安全、別棟配置、回収熱の温度と距離を調べます。</p></li><li><span>03</span><strong>経済性を確認</strong><p>設備費、運営費、利用契約、熱利用の価値を実測・見積もりで比べます。</p></li><li><span>04</span><strong>約1 MWから</strong><p>契約・許認可済み容量ではなく、最初の検証規模です。</p></li><li><span>NEXT</span><strong>利用が育った時だけ</strong><p>電力、許認可、資金、土地、需要、地域合意がそろってから拡張を判断します。</p></li></ol>
            <p className="growth-caveat">容量、時期、費用、熱利用、収益は未確定です。調査と関係者合意なしに建設を約束しません。</p>
          </details>
        </section>

        <section className="future-cta">
          <p>いま必要なのは、投資ではなく地域の参加です。</p>
          <h2>温泉の次の未来を、<br />一緒に考えませんか。</h2>
          <div><a className="button button-primary" href={LINE_URL} target="_blank" rel="noreferrer">LINEに参加 <span>↗</span></a><Link className="button button-ghost" href="/">温泉を守る計画へ <span>←</span></Link></div>
        </section>
      </main>

      <footer><Brand href="/" /><p>ONSEN × LEARNING × OUR COG DC COMPUTE × COMMUNITY</p><a href={LINE_URL} target="_blank" rel="noreferrer">LINEで参加 ↗</a></footer>
    </>
  );
}
