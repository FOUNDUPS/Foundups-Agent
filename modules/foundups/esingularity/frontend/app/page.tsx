import Image from 'next/image';
import Link from 'next/link';
import EventAlert from '../components/EventAlert';
import LineButton from '../components/LineButton';
import Brand from '../components/Brand';
import HeroMusic from '../components/HeroMusic';

const LINE_URL = 'https://line.me/ti/p/baXEozL_Q6';

const stakeholderRings = [
  ['01', '天菅生町と近隣住民', '騒音・水・交通・景観・温泉再開について、最初に話を聞く人たち。'],
  ['02', '子ども・学生・研究者', '大安寺の学びと、まず県内5大学の研究・教育に地域の計算資源をつなぐ。'],
  ['03', '農業・地域産業', '農業AI、ドローン、自動運転農機、ものづくりDXを地域で育てる。'],
  ['04', '技術・運営パートナー', '電力、通信、冷却、建築、セキュリティ、データセンター運営の実務家。'],
  ['05', '福井市と市民', '解体か再生かを、公開された根拠と地域の声で判断する。'],
];

export default function Home() {
  return (
    <>
      <header className="site-header">
        <Brand href="#top" />
        <nav aria-label="Primary navigation"><a href="#top">温泉を守る</a><a href="#innovation-hub">AI拠点</a><Link href="/future">福井の未来</Link><Link href="/team">チーム</Link></nav>
        <LineButton />
      </header>

      <main id="top">
        <section className="hero" id="hero" aria-labelledby="hero-title">
          <div className="hero-grid" aria-hidden="true" />
          <EventAlert />
          <div className="hero-copy">
            <p className="eyebrow"><span /> WHY · 温泉を守る</p>
            <h1 id="hero-title">温泉を守り、<br /><em>地域のAI基盤でまちを元気に。</em></h1>
            <p className="hero-lead">壊すために公費を使う前に、この建物で福井の未来をつくろう。温泉を再開する。学びと起業の拠点をつくる。地域のコンピュートの熱を、地域へ返す。</p>
            <div className="hero-actions"><a className="button button-primary" href={LINE_URL} target="_blank" rel="noreferrer">LINEで仲間になる <span>↗</span></a><a className="button button-ghost" href="#story">計画を見る <span>↓</span></a></div>
            <HeroMusic />
          </div>
        </section>

        <section className="future-place section" id="future-place" aria-labelledby="future-place-title">
          <div className="future-place-heading">
            <div><p className="eyebrow"><span /> WHAT · ここがどう変わる？</p><h2 id="future-place-title">温泉を残す。<br /><em>夜まで人が集まる場所</em>をつくる。</h2></div>
            <p>保存するだけではありません。温泉、地域の食、小さな商い、学び、光の文化を一つの場所につなぐ構想です。</p>
          </div>
          <figure className="future-place-visual">
            <Image src="/onsen-future-concept-v4.webp" alt="既存の南北に長い建物と南端の曲線棟、駐車場を残し、南側に露天風呂を加えた再生構想イメージ" width={1293} height={1217} sizes="(max-width: 670px) 100vw, 86vw" />
            <figcaption><span>CONCEPT RENDER</span> 現時点の構想イメージです。実際の配置・規模・熱利用は、建物・設備・法令・事業性の調査で決まります。</figcaption>
          </figure>
          <div className="future-place-cards" role="list">
            <article role="listitem"><span>01 · ROTENBURO</span><h3>日本初を目指す、<br />コンピュート排熱の露天風呂。</h3><p>回収できる熱を片側の露天風呂に集中し、男女どちらの湯を温めるかを日替わりでシステムが案内する構想です。</p><small>ENGINEERING VALIDATION REQUIRED</small></article>
            <article role="listitem"><span>02 · FOOD</span><h3>あわら型の、<br />小さなコンテナ横丁。</h3><p>あわら温泉の横丁型モデルに着想を得て、地域の料理人、農家、学生が小さく商いを始められる場所へ。</p><small>AWARA-INSPIRED COMMUNITY FOOD COURT</small></article>
            <article role="listitem"><span>03 · NIGHT</span><h3>夜は、長谷川章氏の<br />D-Kという光の舞台へ。</h3><p>建物を毎晩変化する光のキャンバスにする構想。九頭竜の水と龍を、地域の新しい夜景にします。</p><small>PROPOSED DIGITAL KAKEJIKU EXPERIENCE</small></article>
          </div>
        </section>

        <section className="innovation-hub section" id="innovation-hub" aria-labelledby="innovation-hub-title">
          <div className="hub-heading">
            <div><p className="eyebrow light"><span /> HOW · ESINGULARITY INNOVATION HUB</p><h2 id="innovation-hub-title">温泉の上に、<br /><em>福井の学びと挑戦</em>を重ねる。</h2></div>
            <p>1階の温泉を地域の居場所として再開し、その上を世代ごとの学び、研究、起業がつながる場所へ。これは現時点の構想であり、建物調査と地域・所有者との合意を経て具体化します。</p>
          </div>

          <div className="compute-equation" aria-label="お米と人の関係は、コンピュートとAIの関係に似ています">
            <span><b>お米</b><small>人のごはん</small></span><i>:</i><strong>人</strong><em>=</em><span><b>Compute</b><small>AIのごはん</small></span><i>:</i><strong>AI</strong>
          </div>

          <div className="hub-floors" role="list" aria-label="Innovation Hub floor concept">
            <article role="listitem"><span>GROUND FLOOR</span><div><strong>温泉とコミュニティ空間</strong><p>温泉、大きな露天風呂、あわら型コンテナ・フードコート。</p></div></article>
            <article role="listitem"><span>2ND FLOOR</span><div><strong>小・中学生</strong><p>AIを安全に学び、先生と一緒に試せる学習スタジオ。</p></div></article>
            <article role="listitem"><span>3RD FLOOR</span><div><strong>高校生・大学生</strong><p>地域の課題を通じて、研究と実践をつなぐ場所。</p></div></article>
            <article role="listitem"><span>4TH FLOOR</span><div><strong>大学プロジェクト・スタートアップ</strong><p>研究を試し、福井の新しい仕事へ育てる場所。</p></div></article>
          </div>
          <p className="hub-caveat">構想図：階ごとの利用方法は、耐震・設備・消防・法令調査と関係者協議により変更されます。</p>

          <div className="return-heading"><p className="eyebrow light"><span /> RETURN ON COMPUTE</p><h3>計算力から、<br />福井に何が返る？</h3><p>データセンターの価値は、機械の台数ではありません。地域の人が、その計算力で何を学び、試し、つくれるかです。</p></div>
          <div className="compute-return" role="list">
            <article role="listitem"><span>🎓</span><strong>一人ひとりの学び</strong><p>先生の代わりではなく、先生と子どもを支えるAIを、地域で学び試す。</p><a href="https://www.mext.go.jp/zyoukatsu/ai/index.html" target="_blank" rel="noreferrer">文部科学省の取組 <b>↗</b></a></article>
            <article role="listitem"><span>🌾</span><strong>自動化する農業</strong><p>ドローン、自動走行農機、草刈り・除草、圃場の見守りを支えるAI研究へ。</p><a href="https://www.maff.go.jp/j/nousin/noukan/tyotei/kizyun/attach/tebiki.html" target="_blank" rel="noreferrer">農林水産省の手引き <b>↗</b></a></article>
            <article role="listitem"><span>🧪</span><strong>試せる場所</strong><p>学生、大学、地域企業、起業家が、自分たちの課題でAIを実験できる。</p><a href="https://www.meti.go.jp/policy/mono_info_service/geniac/" target="_blank" rel="noreferrer">経済産業省 GENIAC <b>↗</b></a></article>
            <article role="listitem"><span>🛡️</span><strong>地域で管理できる選択肢</strong><p>計算、モデル、適切に管理されたデータを、より地域の管理下に置ける選択肢を増やす。</p><a href="https://www.meti.go.jp/press/2024/04/20240419002/20240419002.html" target="_blank" rel="noreferrer">国内計算資源と経済安全保障 <b>↗</b></a></article>
          </div>
          <p className="future-compute-line">未来を動かすのは、<strong>Compute。</strong><br />福井の電力から、福井が使える計算力を。</p>
        </section>

        <section className="vision-overview section" id="vision" aria-labelledby="vision-title">
          <div className="vision-heading">
            <div><p className="eyebrow"><span /> 選択肢を比べる</p><h2 id="vision-title">壊すだけではない。<br /><em>こう変えられる。</em></h2></div>
            <p>閉館した施設を、そのまま残す話ではありません。温泉を中心に、人が集まり、学び、働き、挑戦できる場所へ育てる提案です。</p>
          </div>
          <div className="choice-path" aria-label="現在から二つの選択肢への流れ">
            <article><span>いま</span><strong>閉館した施設</strong><p>解体に向けた手続きが進んでいます。</p></article>
            <b aria-hidden="true">↓</b>
            <article className="choice"><span>選択</span><strong>解体する</strong><i>または</i><strong>もう一つの未来を比べる</strong></article>
            <b aria-hidden="true">↓</b>
            <article className="future"><span>私たちの提案</span><strong>温泉を中心に、地域の未来をつくる</strong></article>
          </div>
          <div className="vision-cards" role="list" aria-label="再生後の五つの役割">
            <article role="listitem"><span aria-hidden="true">♨️</span><div><strong>温泉</strong><p>1階の温泉を再開し、地域の居場所を取り戻す。</p></div></article>
            <article role="listitem"><span aria-hidden="true">🎓</span><div><strong>学びと挑戦</strong><p>上階を学生、研究者、地域企業の活動拠点へ。</p></div></article>
            <article role="listitem"><span aria-hidden="true">🌾</span><div><strong>AIの田んぼ</strong><p>周辺の土地に、福井で使う計算力をつくる。</p></div></article>
            <article role="listitem"><span aria-hidden="true">🍜</span><div><strong>食と起業</strong><p>小さな店や台所から、地域の商いを始める。</p></div></article>
            <article role="listitem"><span aria-hidden="true">🎨</span><div><strong>祭りと文化</strong><p>イベントと光で、夜も人が集まる場所へ。</p></div></article>
          </div>
        </section>

        <section className="story section" id="story" aria-labelledby="story-title">
          <div className="section-index">WHY <span>/ THE BUILDING</span></div>
          <div className="story-heading"><div><p className="eyebrow"><span /> A PUBLIC ASSET WITH A HISTORY</p><h2 id="story-title">これは、古い建物の話ではない。<br /><em>次の30年</em>を選ぶ話です。</h2></div><p>1994年、市民の健康・交流・憩いのために開館。天然温泉、体育館、宴会場、宿泊・研修機能を備え、2018年度には約13万人が利用しました。公の施設としての機能は2021年6月に廃止されました。</p></div>

          <div className="fact-rail" role="list" aria-label="Facility facts">
            <article role="listitem"><span>1994</span><strong>開館</strong><p>高齢者を中心とした健康・交流の公共拠点として誕生。</p></article>
            <article role="listitem"><span>8,099㎡</span><strong>延床面積</strong><p>宿泊・研修、健康、交流の複数棟からなる大規模資産。</p></article>
            <article role="listitem"><span>129,649人</span><strong>2018年度利用</strong><p>入館者と宿泊者を合わせた、閉館前の利用実績。</p></article>
            <article role="listitem"><span>2021</span><strong>機能廃止</strong><p>いま問われているのは、解体前に再利用を検証するかどうか。</p></article>
          </div>

        </section>

        <section className="pause section" aria-labelledby="pause-title">
          <Image src="/campaign-message.jpg" alt="温泉を守れ、すかっとランド九頭竜の解体を止めよう" width={1280} height={330} sizes="(max-width: 1050px) 90vw, 40vw" />
          <div className="pause-copy"><p className="eyebrow light"><span /> THE COUNCIL AMENDMENT</p><h2 id="pause-title">解体準備は進めても、<br /><em>代案の扉は閉じない</em>。</h2><p>求めるのは、固定60日間の停止ではありません。補正予算、附帯決議、または同等の正式措置により、解体契約の締結など後戻りが困難になる時点まで、条件を満たす再生案を受け付け、解体執行前に比較評価できる道を残すことです。</p><div className="no-money ask-rule"><strong>THE RULE</strong><span>期限前に、安全性、実行主体、借地合意、資金計画、市の財政効果を証明できた場合、解体案と同じ条件で正式に審査する。</span></div><ul className="decision-conditions"><li><strong>期限</strong> 解体契約締結など、公費上の後戻りが困難になる前</li><li><strong>責任移管</strong> 改修・運営・維持・将来処分を適法な範囲で新主体へ</li><li><strong>土地合意</strong> 全敷地の土地所有者と借地条件・負担について合意</li></ul></div>
        </section>

        <section className="proposal section" id="proposal" aria-labelledby="proposal-title">
          <div className="section-index">HOW <span>/ AI RICE FIELD</span></div>
          <div className="proposal-intro"><div><p className="eyebrow"><span /> AIの田んぼ</p><h2 id="proposal-title">AIにも、<br /><em>「ごはん」</em>が必要です。</h2></div><p>人にお米をつくる田んぼがあるように、AIには「計算する力」を生み出す場所が必要です。それがデータセンターです。</p></div>
          <div className="ai-rice-flow" aria-label="AIの田んぼが計算力を生み出す流れ">
            <article><span aria-hidden="true">⚡</span><strong>電力・データ・<br />コンピューター</strong></article>
            <b aria-hidden="true">↓</b>
            <article className="field"><span aria-hidden="true">🌾</span><strong>AIの田んぼ</strong><small>データセンター</small></article>
            <b aria-hidden="true">↓</b>
            <article><span aria-hidden="true">🧮</span><strong>計算する力</strong><small>コンピュート</small></article>
            <b aria-hidden="true">↓</b>
            <article><span aria-hidden="true">🤖</span><strong>AIが仕事をする</strong></article>
          </div>
          <div className="local-compute"><p>この施設が農機を直接動かすわけではありません。地域で使える計算力が、農業AI、教育、研究、ものづくりの開発と利用を支えます。</p><strong>福井の電力 → 福井の計算力 → 福井の知恵 → 福井の仕事</strong></div>
          <div className="compute-uses" role="list" aria-label="福井での活用例"><article role="listitem"><span>🌾</span><div><strong>農業</strong><p>ドローン、畑の見守り、雑草検知、収穫予測などの研究へ。</p></div></article><article role="listitem"><span>🎓</span><div><strong>教育・大学</strong><p>学生と研究者が、地域でAIを学び試せる環境へ。</p></div></article><article role="listitem"><span>🏭</span><div><strong>地域企業</strong><p>製造、設計、業務改善に使うAIを福井で育てる。</p></div></article></div>
        </section>

        <section className="people section" id="people" aria-labelledby="people-title">
          <div className="section-index">WHO <span>/ COMMUNITY</span></div>
          <div className="people-grid"><div className="people-intro"><p className="eyebrow"><span /> NOT A TOP-DOWN PROJECT</p><h2 id="people-title">最初に集めるのは、<br />お金ではなく<em>当事者</em>です。</h2><Image src="/why-preserve.jpg" alt="公共資産、地域AI基盤、農業・教育・産業の未来を守る" width={451} height={486} sizes="(max-width: 1050px) 70vw, 38vw" /></div><div className="stakeholder-list">{stakeholderRings.map(([number, title, body]) => <article key={number}><span>{number}</span><div><h3>{title}</h3><p>{body}</p></div></article>)}</div></div>
        </section>

        <section className="community-calendar section" id="meetings" aria-labelledby="meetings-title">
          <div className="calendar-heading"><div><p className="eyebrow light"><span /> WHEN · COMMUNITY MEETINGS</p><h2 id="meetings-title">会って、<br /><em>話す。</em></h2></div><p>ウェブサイトだけで決めるプロジェクトではありません。周辺地域を歩き、住民の経験、心配、希望を聞くことから始めます。</p></div>
          <div className="calendar-grid">
            <article className="public-meeting"><span>次回の公開ミーティング</span><strong>日程・場所を確認中</strong><p>公開できる情報が確定してから掲載します。先に案内を受け取りたい方は、LINEコミュニティにご参加ください。</p><a href={LINE_URL} target="_blank" rel="noreferrer">LINEで案内を受け取る <b>↗</b></a></article>
            <details className="member-calendar"><summary><span>メンバー予定</span><strong>LINEコミュニティ参加者向け</strong></summary><div><p>地域での小さな対話、準備会、情報共有の詳しい予定を、参加メンバーへLINEでお知らせする構想です。</p><p className="calendar-honesty">現在、このウェブサイトに会員認証や保護されたカレンダーはありません。ボタンが専用ページを開くようには見せません。</p><a href={LINE_URL} target="_blank" rel="noreferrer">LINEに参加 <b>↗</b></a></div></details>
          </div>
        </section>

        <section className="join simple-join section" id="join" aria-labelledby="join-title">
          <div className="join-copy"><p className="eyebrow light"><span /> ADD YOUR NAME · SAVE THE ONSEN</p><h2 id="join-title">温泉を守るチームに、<br /><em>あなたの名前</em>を。</h2><p>これは寄付や投資の申込みではありません。イベントで声を届けたい人、施設を利用したことがある人、教育・農業・技術で協力できる人をつなぎ、代案を実行できるチームへ育てるための登録です。登録名を本人の許可なく公開することはありません。</p><a className="line-button" href={LINE_URL} target="_blank" rel="noreferrer"><span>LINE</span><strong>LINEでチームに参加</strong><i>↗</i></a><div className="location"><span>PROJECT SITE</span><strong>旧すかっとランド九頭竜</strong><p>福井県福井市天菅生町3-10</p></div></div>
        </section>

      </main>

      <footer><Brand href="#top" /><p>AI × ONSEN × EDUCATION × AGRICULTURE × COMMUNITY</p><a href={LINE_URL} target="_blank" rel="noreferrer">LINEで参加 ↗</a></footer>
    </>
  );
}
