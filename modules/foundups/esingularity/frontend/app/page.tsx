import Image from 'next/image';
import Link from 'next/link';
import EventAlert from '../components/EventAlert';
import LineButton from '../components/LineButton';
import Brand from '../components/Brand';
import HeroMusic from '../components/HeroMusic';

const LINE_URL = 'https://line.me/ti/p/baXEozL_Q6';

const campaignSteps = [
  ['01', 'STOP', '解体を止め、比較の時間を確保する', '条件を満たす代案を比較できるまで、後戻りできない解体契約を結ばないよう求める。'],
  ['02', 'ASSEMBLE', 'COGDC推進チームをつくる', '地域住民、発起人、技術・運営の実務家、公益パートナーを一つの実行チームへ。'],
  ['03', 'LAND', '地権者と合意する', '地代、責任、期間、将来の選択肢を含む土地利用の条件を、地権者と協議する。'],
  ['04', 'CITY', '市が審査できる代案にする', '安全性、責任移管、資金計画、市の財政効果を示し、正式に比較できる提案へ。'],
  ['05', 'UNIVERSITIES', '福井の大学と利用計画をつくる', '教育・研究で必要な計算力と、最初に実行する地域プロジェクトを具体化する。'],
  ['06', 'CUSTOMERS + PARTNERS', '企業顧客・事業パートナーを確保する', '電力、通信、建設、運営の体制と、計算力を利用する中核顧客の約束を積み上げる。'],
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
          <div className="future-place-visuals">
            <figure className="future-place-visual">
              <Image src="/satellite-view.jpeg" alt="既存建物、駐車場、周辺土地を使ったプロジェクト配置構想" width={1320} height={1245} sizes="(max-width: 670px) 100vw, 50vw" />
              <figcaption><span>SITE CONCEPT</span> 012提供の配置構想です。完成済みの施設を示す画像ではありません。</figcaption>
            </figure>
            <figure className="future-place-visual">
              <Image src="/concept-onsen.jpg" alt="露天風呂と小さな飲食店が夜に集まる将来構想" width={440} height={290} sizes="(max-width: 670px) 100vw, 50vw" />
              <figcaption><span>ONSEN CONCEPT</span> 温泉と地域の食がつながる将来イメージです。実際の配置・規模・熱利用は調査で決まります。</figcaption>
            </figure>
          </div>
          <div className="future-place-cards" role="list">
            <article role="listitem"><span>01 · ROTENBURO</span><h3>日本初を目指す、<br />コンピュート排熱の露天風呂。</h3><p>回収できる熱を片側の露天風呂に集中し、男女どちらの湯を温めるかを日替わりでシステムが案内する構想です。</p><small>ENGINEERING VALIDATION REQUIRED</small></article>
            <article className="media-card food-card" role="listitem">
              <a className="card-reference-image awara-reference-image" href="https://yukemuriyokocho.com/" target="_blank" rel="noreferrer"><span>実例を見る：あわら温泉「湯けむり横丁」↗</span></a>
              <span>02 · FOOD</span><h3>あわら型の、<br />小さなコンテナ横丁。</h3><p>あわら温泉の横丁型モデルに着想を得て、地域の料理人、農家、学生が小さく商いを始められる場所へ。</p><small>AWARA-INSPIRED COMMUNITY FOOD COURT</small>
            </article>
            <article className="media-card akira-card" role="listitem">
              <a className="card-reference-image dk-reference-image" href="https://www.digital-kakejiku.com/" target="_blank" rel="noreferrer"><span>D-K公式ギャラリーを開く ↗</span></a>
              <span>03 · NIGHT</span><h3>夜は、長谷川章氏の<br />D-Kという光の舞台へ。</h3><p>建物を毎晩変化する光のキャンバスにする構想。九頭竜の水と龍を、地域の新しい夜景にします。</p>
              <div className="artist-reference"><Image src="/akira-hasegawa.jpeg" alt="D-K（デジタル掛け軸）を提唱する長谷川章氏" width={64} height={64} sizes="64px" /><a href="https://www.digital-kakejiku.com/" target="_blank" rel="noreferrer">長谷川章氏とD-Kの作品を見る <b>↗</b></a></div>
              <small>PROPOSED DIGITAL KAKEJIKU EXPERIENCE</small>
            </article>
          </div>
        </section>

        <section className="innovation-hub section" id="innovation-hub" aria-labelledby="innovation-hub-title">
          <div className="hub-heading">
            <div><p className="eyebrow light"><span /> HOW · ESINGULARITY INNOVATION HUB</p><h2 id="innovation-hub-title">温泉の上に、<br /><em>福井の「学ぶ・創る・始める」</em>を重ねる。</h2></div>
            <p>1階の温泉を地域の居場所として再開し、その上を世代ごとの学び、研究、起業がつながる場所へ。これは現時点の構想であり、建物調査と地域・所有者との合意を経て具体化します。</p>
          </div>

          <div className="compute-equation" aria-label="お米と人の関係は、コンピュートとAIの関係に似ています">
            <span><b>お米</b><small>人のごはん</small></span><i>:</i><strong>人</strong><em>=</em><span><b>Compute</b><small>AIのごはん</small></span><i>:</i><strong>AI</strong>
          </div>

          <div className="hub-floors" role="list" aria-label="Innovation Hub floor concept">
            <article role="listitem"><span>GROUND FLOOR · GATHER</span><div><strong>温泉とコミュニティ空間</strong><p>温泉、大きな露天風呂、あわら型コンテナ・フードコート。</p></div></article>
            <article role="listitem"><span>2ND FLOOR · LEARN</span><div><strong>AI学習スタジオ（小・中学生）</strong><p>保護者と先生が見守る中で、子どもたちがAIの仕組みを安全に学び、対話し、一緒に創る場所。</p></div></article>
            <article role="listitem"><span>3RD FLOOR · CREATE</span><div><strong>AI創造ラボ（高校生・大学生）</strong><p>AIと協働し、地域の課題を研究し、実践的な解決策を生み出す場所。</p></div></article>
            <article role="listitem"><span>4TH FLOOR · LAUNCH</span><div><strong>AIローンチ・ハブ（大学プロジェクト・スタートアップ）</strong><p>AIを活用した研究とアイデアを、福井の新しいプロジェクト、起業、仕事へ育てる場所。</p></div></article>
          </div>
          <p className="hub-caveat">構想図：階ごとの利用方法は、耐震・設備・消防・法令調査と関係者協議により変更されます。</p>

          <div className="return-heading"><p className="eyebrow light"><span /> FUKUI × COMPUTE</p><h3>Computeが、<br />福井を動かす。</h3><p>福井には、AIを学ぶ大学、スマート農業、県民衛星、世界に誇るものづくりがすでにあります。地域の計算力は、それらをつなぎ、試し、育てる基盤です。</p></div>
          <div className="compute-return" role="list">
            <article role="listitem"><span>🎓</span><strong>福井の学生と大学</strong><p>福井大学や福井県立大学では、データサイエンス・AI教育がすでに進んでいます。地域の計算力で、授業を実験と研究へ。</p><a href="https://www.dsai.u-fukui.ac.jp/" target="_blank" rel="noreferrer">福井大学 AI教育研究センター <b>↗</b></a></article>
            <article role="listitem"><span>🌾</span><strong>福井の田んぼ</strong><p>自動走行農機、ロボット草刈機、収量計測、センシングドローン。福井の農業を、福井のAIで支える。</p><a href="https://www.pref.fukui.lg.jp/doc/021037/service/service.html" target="_blank" rel="noreferrer">福井県 スマート農業支援 <b>↗</b></a></article>
            <article role="listitem"><span>🛰️</span><strong>県民衛星「すいせん」</strong><p>福井は衛星をつくり、農地、森林、災害、文化財にデータを活用しています。次は、そのデータを地域で計算する力へ。</p><a href="https://www.pref.fukui.lg.jp/doc/chisangi/fukusat/suisen_syokai.html" target="_blank" rel="noreferrer">福井県民衛星プロジェクト <b>↗</b></a></article>
            <article role="listitem"><span>🏭</span><strong>福井のものづくり</strong><p>繊維、眼鏡、機械、電子部品。地域の計算力で、設計、検査、自動化、新製品開発を加速する。</p><a href="https://kigyoritti.pref.fukui.lg.jp/outline/technical" target="_blank" rel="noreferrer">福井県の技術と産業 <b>↗</b></a></article>
          </div>
          <div className="local-control-callout"><strong>福井の知識とデータを、福井で価値に変える。</strong><p>すべてを地域だけに閉じるという意味ではありません。福井の組織が、計算、モデル、適切に管理されたデータを、より地域の管理下に置ける選択肢を増やします。</p></div>
          <p className="future-compute-line">未来を動かすのは、<strong>Compute。</strong><br />福井の電力 → 福井の計算力 → 福井の未来。</p>
        </section>

        <section className="vision-overview section" id="vision" aria-labelledby="vision-title">
          <div className="vision-heading">
            <div><p className="eyebrow"><span /> 選択肢を比べる</p><h2 id="vision-title">壊すだけではない。<br /><em>こう変えられる。</em></h2></div>
            <p>閉館した施設を、そのまま残す話ではありません。温泉を中心に、人が集まり、学び、働き、挑戦できる場所へ育てる提案です。</p>
          </div>
          <div className="vision-cards" role="list" aria-label="再生後の五つの役割">
            <article role="listitem"><span aria-hidden="true">♨️</span><div><strong>温泉 — 地域の目的地となる大露天風呂</strong><p>1階の温泉を地域の集いの場として再開し、AIの田んぼ（データセンター）の回収熱で温泉水を補助加温できるかを技術検証します。</p></div></article>
            <article role="listitem"><span aria-hidden="true">🎓</span><div><strong>学ぶ・試す・立ち上げる</strong><p>上階を、学生・研究者がAIを学び、試し、福井発の解決策を立ち上げる拠点へ。</p></div></article>
            <article role="listitem"><span aria-hidden="true">🌾</span><div><strong>AIの「田んぼ」— 地域の計算力</strong><p>既存の温泉棟とは別に、周辺の土地へ福井で使う計算力をつくる。</p></div></article>
            <article role="listitem"><span aria-hidden="true">🍜</span><div><strong>食と起業</strong><p>小さな店や台所から、低い初期負担で地域の食の商いを始められる場所へ。</p></div></article>
            <article role="listitem"><span aria-hidden="true">🎨</span><div><strong>D-Kの光・祭り・文化</strong><p>長谷川章氏のD-Kによる夜の光の体験と地域イベントで、福井内外から人が集まる場所へ。</p></div></article>
          </div>
        </section>

        <section className="story section" id="story" aria-labelledby="story-title">
          <div className="section-index">WHY <span>/ THE BUILDING</span></div>
          <div className="story-heading"><div><p className="eyebrow"><span /> A PUBLIC ASSET WITH A HISTORY</p><h2 id="story-title">これは、古い建物の話ではない。<br /><em>福井の次の30年を動かす計算力を、</em>誰が持つかという話です。</h2></div><p>1994年、市民の健康・交流・憩いのために開館。天然温泉、体育館、宴会場、宿泊・研修機能を備え、2018年度には約13万人が利用しました。公の施設としての機能は2021年6月に廃止されました。</p></div>

          <div className="fact-rail" role="list" aria-label="Facility facts">
            <article role="listitem"><span>46.8億円</span><strong>建設時</strong><p>福井市の公表資料に記載された建設費。</p></article>
            <article role="listitem"><span>約68億円</span><strong>指数換算参考</strong><p>国の建設工事費指数による参考値。鑑定額ではありません。</p></article>
            <article role="listitem"><span>約15.8億円</span><strong>解体見込み</strong><p>2026年6月の福井市議会質問資料に示された見込み。</p></article>
            <article role="listitem"><span>129,649人</span><strong>2018年度利用</strong><p>入館者と宿泊者を合わせた、閉館前の利用実績。</p></article>
          </div>

          <div className="visitor-impact" aria-labelledby="visitor-impact-title">
            <div className="visitor-impact-copy"><p className="eyebrow"><span /> VISITOR ECONOMY · SCREENING SCENARIO</p><h3 id="visitor-impact-title">年間129,649人。<br /><em>需要は、すでにあった。</em></h3><p>次の価値は、一回の来場を地域での食事、買い物、宿泊、交通にどれだけつなげられるかで決まります。</p></div>
            <div className="visitor-impact-number"><span>約1.3億〜7.2億円 / 年</span><strong>来場者の直接消費シナリオ</strong><code>129,649 visits × ¥1,000–¥5,546</code></div>
            <div className="visitor-opportunities" role="list"><span role="listitem">🍜 地域の食・横丁</span><span role="listitem">🎨 D-K・祭り・夜間滞在</span><span role="listitem">♨️ 温泉・宿泊</span><span role="listitem">✈️ 空港・新幹線からの周遊</span></div>
            <div className="impact-layers" role="list" aria-label="経済効果を検証する三つの段階"><article className="measured" role="listitem"><span>NOW · CALCULATED</span><strong>来場者の直接消費</strong><p>現在数字で示しているのは、この層だけです。</p></article><article role="listitem"><span>NEXT · INPUT-OUTPUT</span><strong>県内取引と所得への波及</strong><p>消費項目と県内調達率を確認し、福井県産業連関表で分析します。</p></article><article role="listitem"><span>AFTER VALIDATION</span><strong>雇用・税収・地域への還元</strong><p>分析が完了するまで、数字を掲載しません。</p></article></div>
            <details className="impact-method"><summary>30年間の参考累計と計算方法</summary><div><span>約38.9億〜215.7億円 / 30年</span><strong>来場者数と消費額が一定の場合の単純累計</strong><p>割引を行わない説明用の参考値であり、予測ではありません。</p></div></details>
            <div className="scenario-note"><strong>PROJECT SCENARIO — NOT A FORECAST</strong><p>2018年度の利用実績に、1人あたり1,000円の追加消費仮定から、福井県の2025年日帰り観光消費単価5,546円までを掛けた単純な試算です。この試算に含むのは来場者の直接消費だけです。取引先への波及、所得、雇用、税収は、福井県産業連関表による分析が完了するまで含めません。</p><div className="scenario-links"><a href="https://www.pref.fukui.lg.jp/doc/kankou/fukuiken-kankoukyakusu_d/fil/024.pdf" target="_blank" rel="noreferrer">福井県観光客入込数（推計）2025年 <b>↗</b></a><a href="https://www.pref.fukui.lg.jp/doc/toukei-jouhou/hakyukouka.html" target="_blank" rel="noreferrer">福井県 経済波及効果分析 <b>↗</b></a></div></div>
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
          <div className="people-intro"><p className="eyebrow"><span /> NOT A TOP-DOWN PROJECT</p><h2 id="people-title">最初に集めるのは、<br />お金ではなく<em>当事者</em>です。</h2><p>資金の話を始める前に、解体を止め、土地・行政・教育・需要を一つの実行可能な代案につなぎます。</p></div>
          <ol className="campaign-sequence" aria-label="温泉を守るための関係者づくりの順序">{campaignSteps.map(([number, phase, title, body]) => <li key={number}><div className="campaign-step-label"><span>{number}</span><small>{phase}</small></div><h3>{title}</h3><p>{body}</p></li>)}</ol>
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
