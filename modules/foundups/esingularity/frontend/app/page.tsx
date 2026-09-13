import Image from 'next/image';
import Link from 'next/link';
import Brand from '../components/Brand';
import CampaignTicker from '../components/CampaignTicker';
import YumoriPresentation from '../components/YumoriPresentation';
import FukuiComparisonMap from '../components/FukuiComparisonMap';

const YUMORI_URL = 'https://yumori.me';

function YumoriAction({ children }: { children: string }) {
  return <a className="section-action" href={YUMORI_URL}><span>行動はYUMORI.me</span><strong>{children}</strong><b aria-hidden="true">↗</b></a>;
}

export default function Home() {
  return (
    <>
      <header className="site-header home-header">
        <Brand href="#top" />
        <nav className="desktop-nav" aria-label="主要ナビゲーション">
          <a href="#future-place">施設構想</a>
          <a href="#innovation-space">イノベーション・スペース</a>
          <a href="#proposal">COGDC</a>
          <Link href="/future">福井の未来</Link>
          <Link className="jhr-nav-link" href="/reports/jhr">JHR・最新レポート</Link>
        </nav>
        <a className="header-cta" href={YUMORI_URL}>YUMORI.me <span>↗</span></a>
        <div id="home-language-controls" />
        <details className="mobile-nav">
          <summary aria-label="メニューを開く">メニュー</summary>
          <div>
            <a href="#future-place">施設構想</a>
            <a href="#innovation-space">イノベーション・スペース</a>
            <a href="#proposal">COGDC</a>
            <Link href="/future">福井の未来</Link>
          <Link className="jhr-nav-link" href="/reports/jhr">JHR・最新レポート</Link>
            <a href={YUMORI_URL}>参加・行動はYUMORI.me ↗</a>
          </div>
        </details>
      </header>
      <CampaignTicker />

      <main id="top">
        <section className="hero project-hero" id="hero" aria-labelledby="hero-title">
          <div className="hero-grid" aria-hidden="true" />
          <div className="hero-copy">
            <p className="eyebrow"><span /> 構想 · 旧すかっとランド九頭竜</p>
            <h1 id="hero-title"><span className="hero-compute-question">コンピュートで、</span><em>温泉を救えるか。</em><span>地域を再生できるか。</span><span>日本を変えられるか。</span></h1>
            <p className="hero-lead">旧すかっとランド九頭竜の温泉、食、文化、学び、起業を、地域のAI計算基盤「COGDC」につなぐ構想。計算事業が費用と設備更新を賄い、その余剰で地域を支えられるか。熱の再利用とともに検証します。</p>
            <div className="hero-actions">
              <a className="button button-primary" href="?vision=1&slide=1#yumori-deck">10枚で構想を見る <span>↗</span></a>
              <a className="button button-ghost" href="/reports/jhr">JHR・最新レポート <span>→</span></a>
            </div>
            <a className="hero-jhr-news" href="/reports/jhr#latest"><span>JHR｜9月12日確認</span><strong>仙台200MW計画、9月11日に資金調達協議の基本合意を発表。</strong><small>ハイパースケーラー＝巨大なクラウド・AI計算基盤を運営する企業。全国の動きと福井への意味を読む →</small></a>
            <a className="hero-vote-action" href="https://docs.google.com/forms/d/e/1FAIpQLScSKFyzCym8NCarvNIa5cT9c2Pe8C-cY2AbC4zLgsDOKspYKA/viewform"><strong>この構想を、解体で終わらせない。</strong><span>解体予算に反対を。VOTE NO</span><b>湯守に登録・準備委員会に参加 →</b></a>
          </div>
          <FukuiComparisonMap />
        </section>

        <YumoriPresentation />

        <section className="future-place section" id="future-place" aria-labelledby="future-place-title">
          <div className="future-place-heading">
            <div><p className="eyebrow"><span /> 施設構想 · ここがどう変わる？</p><h2 id="future-place-title">温泉を残す。<br /><em>夜まで人が集まる場所</em>をつくる。</h2></div>
            <p>保存するだけではありません。温泉、地域の食、小さな商い、学び、光の文化を一つの場所につなぐ構想です。</p>
          </div>
          <div className="future-place-visuals">
            <figure className="future-place-visual">
              <Image src="/satellite-view.jpeg" alt="既存建物、駐車場、周辺土地を使ったプロジェクト配置構想" width={1320} height={1245} sizes="(max-width: 670px) 100vw, 50vw" />
              <figcaption><span>配置構想</span> 012提供の初期案です。完成済みの施設を示す画像ではありません。</figcaption>
            </figure>
            <figure className="future-place-visual">
              <Image src="/concept-onsen.jpg" alt="露天風呂と小さな飲食店が夜に集まる将来構想" width={440} height={290} sizes="(max-width: 670px) 100vw, 50vw" />
              <figcaption><span>温泉構想</span> 実際の配置・規模・熱利用は調査で決まります。</figcaption>
            </figure>
          </div>
          <div className="future-place-cards" role="list">
            <article role="listitem"><span>01 · 露天風呂</span><h3>COG DCの回収熱を、<br />露天風呂へ活かせるか。</h3><p>回収できる熱を温泉の補助加温に使えるか、温度、距離、年間需要、設備費を技術検証する構想です。</p><small>工学検証が必要です</small></article>
            <article className="media-card food-card" role="listitem">
              <a className="card-reference-image awara-reference-image" href="https://yukemuriyokocho.com/" target="_blank" rel="noreferrer"><span>実例：あわら温泉「湯けむり横丁」↗</span></a>
              <span>02 · 地域の食</span><h3>あわら型の、<br />小さなコンテナ横丁。</h3><p>あわら温泉の横丁型モデルに着想を得て、地域の料理人、農家、学生が小さく商いを始められる場所へ。</p><small>あわらの地域横丁を参考にした構想</small>
            </article>
            <article className="media-card akira-card" role="listitem">
              <a className="card-reference-image dk-reference-image" href="https://www.digital-kakejiku.com/" target="_blank" rel="noreferrer"><span>D-K公式ギャラリーを開く ↗</span></a>
              <span>03 · 夜の文化</span><h3>夜は、D-Kによる<br />光の舞台を提案。</h3><p>建物を毎晩変化する光のキャンバスにする構想。長谷川章氏の参加は未承認で、現在は提案段階です。</p>
              <div className="artist-reference"><Image src="/akira-hasegawa.jpeg" alt="D-K（デジタル掛け軸）を提唱する長谷川章氏" width={64} height={64} sizes="64px" /><a href="https://www.digital-kakejiku.com/" target="_blank" rel="noreferrer">長谷川章氏とD-Kの作品を見る <b>↗</b></a></div>
              <small>提案中のデジタル掛け軸体験</small>
            </article>
          </div>
          <YumoriAction>なくなる前に、温泉を残す仲間になる</YumoriAction>
        </section>

        <section className="innovation-hub section" id="innovation-space" aria-labelledby="innovation-space-title">
          <div className="hub-heading">
            <div><p className="eyebrow light"><span /> 仕組み · eSingularity イノベーション・スペース</p><h2 id="innovation-space-title">温泉の上に、<br /><em>福井の「学ぶ・創る・始める」</em>を重ねる。</h2></div>
            <p>1階の温泉を地域の居場所として再開し、その上を世代ごとの学び、研究、起業がつながる場所へ。建物調査と地域・所有者との合意を経て具体化します。</p>
          </div>

          <div className="compute-equation" aria-label="お米と人の関係は、コンピュートとAIの関係に似ています">
            <span><b>お米</b><small>人のごはん</small></span><i>:</i><strong>人</strong><em>=</em><span><b>コンピュート</b><small>AIのごはん</small></span><i>:</i><strong>AI</strong>
          </div>

          <div className="hub-floors" role="list" aria-label="イノベーション・スペースの階別構想">
            <article role="listitem"><span>低層階 · 公共・交流スペース</span><div><strong>温泉・地域・教育</strong><p>温泉、公共利用、教育、展示、ロボティクス、イベント、来訪者との交流。</p></div></article>
            <article role="listitem"><span>3階 · 挑戦・育成スペース</span><div><strong>学生・チームと初期FoundUpプロジェクト</strong><p>選抜された学生と小さなチームが、旧客室をプロジェクトスタジオとして使い、実課題を解きます。</p></div></article>
            <article role="listitem"><span>最上階 · 実証・発展スペース</span><div><strong>検証されたFoundUpプロジェクト</strong><p>実用性、実行力、現実の価値を示したプロジェクトが、独立したAIネイティブ事業を目指します。</p></div></article>
            <article role="listitem"><span>別棟 · COG DC</span><div><strong>私たちのCOG DC</strong><p>温泉棟とは別に配置し、そこで働く人とプロジェクトへ計算資源を提供する構想です。</p></div></article>
          </div>
          <p className="hub-caveat">構想図：階ごとの利用方法は、耐震・設備・消防・法令調査と関係者協議により変更されます。</p>

          <div className="return-heading"><p className="eyebrow light"><span /> 福井 × COG DC コンピュート</p><h3>私たちの計算資源が、<br />福井を動かす。</h3><p>福井には、AIを学ぶ大学、スマート農業、県民衛星、世界に誇るものづくりがすでにあります。COG DCは、それらをつなぎ、試し、育てるための地域基盤です。</p></div>
          <div className="compute-return" role="list">
            <article role="listitem"><span>🎓</span><strong>福井の学生と大学</strong><p>データサイエンス・AI教育を、地域の実験と研究へつなぎます。</p><a href="https://www.dsai.u-fukui.ac.jp/system/" target="_blank" rel="noreferrer">福井大学 AI教育研究センター <b>↗</b></a></article>
            <article role="listitem"><span>🌾</span><strong>福井の田んぼ</strong><p>自動走行農機、草刈り、収量計測、センシングの研究を地域で支えます。</p><a href="https://www.pref.fukui.lg.jp/doc/021037/service/service.html" target="_blank" rel="noreferrer">福井県 スマート農業支援 <b>↗</b></a></article>
            <article role="listitem"><span>🛰️</span><strong>県民衛星「すいせん」</strong><p>農地、森林、災害、文化財のデータを地域で活かす計算力へ。</p><a href="https://www.pref.fukui.lg.jp/doc/chisangi/fukusat/suisen_syokai.html" target="_blank" rel="noreferrer">福井県民衛星プロジェクト <b>↗</b></a></article>
            <article role="listitem"><span>🏭</span><strong>福井のものづくり</strong><p>設計、検査、自動化、新製品開発に使うAIを福井で育てます。</p><a href="https://kigyoritti.pref.fukui.lg.jp/outline/technical" target="_blank" rel="noreferrer">福井県の技術と産業 <b>↗</b></a></article>
          </div>
          <div className="local-control-callout"><strong>福井の知識とデータを、福井で価値に変える。</strong><p>すべてを地域だけに閉じるという意味ではありません。福井の組織が、計算、モデル、適切に管理されたデータを、より地域の管理下に置ける選択肢を増やします。</p></div>
          <p className="future-compute-line">電力 → COG DC → FoundUpプロジェクト → <strong>福井の未来。</strong></p>
          <YumoriAction>この場所を実現する仲間になる</YumoriAction>
        </section>

        <section className="story section" id="evidence" aria-labelledby="evidence-title">
          <div className="section-index">根拠 <span>/ 実在する公共施設</span></div>
          <div className="story-heading"><div><p className="eyebrow"><span /> 公表資料から始める</p><h2 id="evidence-title">構想と事実を、<br /><em>混ぜない。</em></h2></div><p>1994年に開館した実在施設です。公開資料で確認できる事実、プロジェクトの仮説、まだ必要な検証を分けて表示します。</p></div>
          <div className="fact-rail" role="list" aria-label="施設の公表事実">
            <article role="listitem"><span>46.8億円</span><strong>建設時</strong><p>福井市の公表資料に記載された建設費。</p></article>
            <article role="listitem"><span>8,099.56㎡</span><strong>延床面積</strong><p>福井市の財産資料に記載された既存建物の規模。</p></article>
            <article role="listitem"><span>約15.8億円</span><strong>将来の解体見込み</strong><p>2026年6月の市議会質問資料に示された見込みで、確定契約額ではありません。</p></article>
            <article role="listitem"><span>129,649人</span><strong>2018年度利用</strong><p>入館者と宿泊者を合わせた、閉館前の利用実績。</p></article>
          </div>
          <div className="evidence-boundary">
            <strong>再利用の事業性、資金調達、工事費は検証中です。</strong>
            <p>監査を通過していない売上、利益、投資回収などの数値は、このサイトの根拠として公開しません。</p>
            <div className="scenario-links"><a href="https://www.city.fukui.lg.jp/sisei/plan/reform/p071776_d/fil/SUKATTO.pdf" target="_blank" rel="noreferrer">福井市 財産資料 <b>↗</b></a><a href="https://www.city.fukui.lg.jp/sisei/gikai/shitsumon/p004052_d/fil/0806a.pdf" target="_blank" rel="noreferrer">福井市議会 2026年6月質問資料 <b>↗</b></a></div>
          </div>
          <YumoriAction>壊す前に、再利用案を比べる時間を求める</YumoriAction>
        </section>

        <section className="proposal section" id="proposal" aria-labelledby="proposal-title">
          <div className="section-index">技術構想 <span>/ AIの田んぼ</span></div>
          <div className="proposal-intro"><div><p className="eyebrow"><span /> 地域主体の小規模AI計算基盤</p><h2 id="proposal-title">AIにも、<br /><em>「ごはん」</em>が必要です。</h2></div><p>人にお米をつくる田んぼがあるように、AIには「計算する力」を生み出す場所が必要です。それがCOG DCです。</p></div>
          <div className="ai-rice-flow" aria-label="AIの田んぼが計算力を生み出す流れ">
            <article><span aria-hidden="true">⚡</span><strong>電力・データ・<br />コンピューター</strong></article><b aria-hidden="true">↓</b>
            <article className="field"><span aria-hidden="true">🌾</span><strong>AIの田んぼ</strong><small>COG DC</small></article><b aria-hidden="true">↓</b>
            <article><span aria-hidden="true">🧮</span><strong>計算する力</strong><small>コンピュート</small></article><b aria-hidden="true">↓</b>
            <article><span aria-hidden="true">🤖</span><strong>AIと人が課題を解く</strong></article>
          </div>
          <div className="local-compute"><p>この施設が農機を直接動かすわけではありません。学生・チームと初期FoundUpプロジェクトがCOG DCを使い、農業AI、教育、研究、ものづくりの開発と検証を進める構想です。</p><strong>電力 → COG DC → 解決策 → 福井の仕事</strong></div>
          <div className="compute-uses" role="list" aria-label="福井での活用例"><article role="listitem"><span>🌾</span><div><strong>農業</strong><p>ドローン、畑の見守り、雑草検知、収穫予測などの研究へ。</p></div></article><article role="listitem"><span>🎓</span><div><strong>教育・大学</strong><p>学生と研究者が、地域でAIを学び試せる環境へ。</p></div></article><article role="listitem"><span>🏭</span><div><strong>地域企業</strong><p>製造、設計、業務改善に使うAIを福井で育てる。</p></div></article></div>
          <YumoriAction>地域のコンピュートを、地域の手に</YumoriAction>
        </section>

        <section className="site-boundary section" aria-labelledby="site-boundary-title">
          <div><p className="eyebrow light"><span /> 二つのサイト、二つの役割</p><h2 id="site-boundary-title">構想を知る。<br /><em>行動につなぐ。</em></h2></div>
          <div className="boundary-grid">
            <article><span>eSingularity.ai / YUMORI.info</span><strong>プロジェクトと施設の情報</strong><p>建物、温泉、COG DC、イノベーション・スペース、根拠、検証状況を説明します。</p><a href="#yumori-deck">10枚の構想を見る ↑</a></article>
            <article className="boundary-action"><span>YUMORI.me</span><strong>参加と市民行動</strong><p>温泉を守る運動、参加登録、共有、市への働きかけは、キャンペーンサイトに集約します。</p><a href={YUMORI_URL}>YUMORI.meへ進む ↗</a></article>
          </div>
        </section>
      </main>

      <footer><Brand href="#top" /><p>温泉 × COG DC × 学び × 地域</p><a href={YUMORI_URL}>参加・行動はYUMORI.me ↗</a></footer>
    </>
  );
}
