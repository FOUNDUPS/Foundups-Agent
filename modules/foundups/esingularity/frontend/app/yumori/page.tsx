import type { Metadata } from 'next';

const FORM_URL = 'https://docs.google.com/forms/d/e/1FAIpQLScSKFyzCym8NCarvNIa5cT9c2Pe8C-cY2AbC4zLgsDOKspYKA/viewform';
const FORM_EMBED_URL = `${FORM_URL}?embedded=true`;
const JHR_URL = '/reports/jhr';
const ESINGULARITY_URL = '/';
const INZAI_IMAGE = 'https://www.re-port.net/picture_l/report/0000074457_09.png';

export const metadata: Metadata = {
  title: 'YUMORI.me — 地域を守り、地域のAIをつくる',
  description:
    'YUMORI.meは、巨大な外部集積だけに依存せず、既存資産を再利用し、地域向けのオープンソースAI計算資源を地域で育てるための市民・技術・教育の運動です。',
  keywords: [
    'YUMORI.me',
    '湯守',
    '地域主権AI',
    '地域コンピュート',
    'COG DC',
    'Community-Owned Green Data Center',
    'Japan Hyperscaler Report',
    'データセンター',
    'ハイパースケーラー',
    '印西',
    '福井',
    'eSingularity',
    'Educational Singularity Lab',
  ],
  alternates: { canonical: 'https://yumori.me/' },
  openGraph: {
    title: 'YUMORI.me — I am a guardian.',
    description: '地域の建物・電力・知識・文化を、地域のAIインフラへ。',
    type: 'website',
    url: 'https://yumori.me/',
  },
};

const pillars = [
  ['01', 'LOCAL COMPUTE', '計算力を、まず地域へ。', 'COG DCの第一目的は計算力の輸出ではありません。学校、大学、農業、病院、自治体、ものづくり、地域企業のための計算基盤です。'],
  ['02', 'OPEN SOURCE', '必要十分なAIを、低コストで。', '教育、農業、検査、翻訳、地域業務では、常に最大級モデルが必要なわけではありません。用途別のオープンソースモデルを地域で運用し、費用と依存を抑えます。'],
  ['03', 'REUSE', '壊す前に、使えるか調べる。', '空いた公共施設、工場、ホテル、倉庫、温浴施設などを、まず構造・電力・通信・熱利用の観点から調査。解体費を払う前に、再生投資へ転換できるかを検証します。'],
  ['04', 'EDUCATION', '建物そのものを、教育装置へ。', 'Educational Singularity Labでは、地域の計算資源を使って学生がAIを学び、地域課題を解き、研究と実装をつなげます。'],
  ['05', 'ENTREPRENEURSHIP', '計算拠点を、起業の拠点へ。', '小さなFoundUpsや地域企業が、すぐ隣にある計算資源を使って試作・自動化・新事業を始める。データセンターを「箱」で終わらせません。'],
  ['06', 'MODULAR', '1MWから始め、必要な分だけ育てる。', '1MW → 5MW → 10MW → 20MW。需要、資金、電力、地域合意に合わせて段階的に増設し、巨大投資を前提にしない地域型インフラを目指します。'],
];

const systemFlow = [
  '候補となる既存施設を見つける',
  '構造・電力・光回線・冷却・排熱先を調べる',
  '地域の学校・大学・産業・自治体の計算需要を調べる',
  '1MW級の最小実証案を作る',
  '地域資本・事業者・公益主体の参加方法を設計する',
  'Educational Singularity Labを併設する',
  '実績に合わせて5 / 10 / 20MWへ拡張する',
  '得られた知見を次の地域へコピーする',
];

export default function YumoriPage() {
  return (
    <main style={{ background: '#0b0d0c', color: '#f4f1e8', minHeight: '100vh', fontFamily: 'system-ui, sans-serif' }}>
      <section style={{ minHeight: '88vh', display: 'grid', alignItems: 'end', padding: '8vw 6vw 6vw', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(circle at 75% 25%, rgba(136,180,150,.18), transparent 35%), linear-gradient(180deg, rgba(11,13,12,.1), #0b0d0c 82%)' }} />
        <div style={{ position: 'relative', maxWidth: 1100 }}>
          <p style={{ letterSpacing: '.18em', fontWeight: 800, fontSize: 13 }}>YUMORI.me / 湯守</p>
          <h1 style={{ fontSize: 'clamp(4rem, 13vw, 10rem)', lineHeight: .82, margin: '24px 0 28px', letterSpacing: '-.07em' }}>YUMORI<br /><span style={{ opacity: .58 }}>.me</span></h1>
          <p style={{ fontSize: 'clamp(1.45rem, 4vw, 3.2rem)', maxWidth: 900, lineHeight: 1.2, fontWeight: 750, margin: 0 }}>I am a guardian.<br />地域を守り、地域のAIをつくる。</p>
          <p style={{ maxWidth: 820, fontSize: 'clamp(1rem, 1.8vw, 1.3rem)', lineHeight: 1.8, marginTop: 28, opacity: .82 }}>
            日本にはAIインフラが必要です。だからこそ、どこに、誰のために、誰が所有し、地域に何を残すのかを、巨大投資のあとではなく、その前に決める必要があります。
          </p>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 32 }}>
            <a href="#join" style={primaryButton}>YUMORIになる</a>
            <a href={JHR_URL} style={secondaryButton}>JHRで現実を見る</a>
          </div>
        </div>
      </section>

      <section style={sectionStyle}>
        <p style={kicker}>MESSAGE / 僧・九頭龍泰澄</p>
        <div style={{ maxWidth: 980 }}>
          <h2 style={headline}>守るとは、止めることだけではない。<br />次の形を、先に示すこと。</h2>
          <p style={bodyText}>
            この僧が守ろうとしているのは、一つの温泉だけではありません。土地、水、記憶、建物、祭り、仕事、学び、そして地域が自分たちの未来を選ぶ余地です。
          </p>
          <p style={bodyText}>
            長谷川章氏のD-Kが建物や自然を一枚の固定された画面ではなく、刻々と変化する「場」として見せるように、YUMORIも地域を固定された過去として保存するのではなく、文化と技術が共存して変化できる場として守ります。
          </p>
          <p style={{ ...bodyText, fontWeight: 800, fontSize: 'clamp(1.35rem, 3vw, 2.3rem)' }}>壊す前に調べる。奪われる前に設計する。地域の知を、地域の力へ。</p>
        </div>
      </section>

      <section style={{ ...sectionStyle, background: '#e8e2d4', color: '#121512' }}>
        <p style={{ ...kicker, color: '#3d493e' }}>WHY NOW / 印西から見えること</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 30, alignItems: 'start' }}>
          <div>
            <h2 style={{ ...headline, color: '#121512' }}>巨大データセンターは、<br />都市計画そのものを変える。</h2>
            <p style={{ ...bodyText, color: '#273027' }}>
              印西市では、生活圏や駅周辺へのデータセンター建設をめぐり、景観・騒音・排熱・土地利用への懸念が市の公式議論になり、地区計画や新しいルールづくりが進んでいます。
            </p>
            <p style={{ ...bodyText, color: '#273027' }}>
              YUMORIは「データセンター反対」ではありません。必要な計算資源を、地域と共存できる規模・場所・所有・用途でつくるべきだと考えます。
            </p>
            <a href={JHR_URL} style={{ ...secondaryButton, color: '#121512', borderColor: '#121512' }}>Japan Hyperscaler Report →</a>
          </div>
          <figure style={{ margin: 0 }}>
            <img src={INZAI_IMAGE} alt="千葉県印西市の大規模データセンター開発地の航空写真" style={{ width: '100%', display: 'block', borderRadius: 18 }} />
            <figcaption style={{ fontSize: 12, lineHeight: 1.6, marginTop: 10, opacity: .65 }}>DPDC印西パーク開発地。画像出典: R.E.port。規模理解のための外部参照画像。</figcaption>
          </figure>
        </div>
      </section>

      <section style={sectionStyle}>
        <p style={kicker}>THE ALTERNATIVE / COG DC</p>
        <h2 style={headline}>Community-Owned Green Data Center.<br />地域のための、地域コンピュート。</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 14, marginTop: 40 }}>
          {pillars.map(([n, en, title, text]) => (
            <article key={n} style={{ border: '1px solid rgba(255,255,255,.16)', borderRadius: 18, padding: 24, minHeight: 245 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 12, letterSpacing: '.12em', opacity: .6 }}><span>{n}</span><span>{en}</span></div>
              <h3 style={{ fontSize: 26, lineHeight: 1.25, margin: '32px 0 14px' }}>{title}</h3>
              <p style={{ lineHeight: 1.75, opacity: .78, margin: 0 }}>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section style={{ ...sectionStyle, borderTop: '1px solid rgba(255,255,255,.12)' }}>
        <p style={kicker}>LOCAL INTELLIGENCE / 地域の知を守る</p>
        <h2 style={headline}>データだけではない。<br />地域の「知」を、地域に残す。</h2>
        <div style={{ maxWidth: 940 }}>
          <p style={bodyText}>
            ここでいうIPは、企業の特許だけではありません。農家の経験、工場の工程、学校の教材、方言、地域史、設計ノウハウ、災害対応、文化財の記録など、地域が長い時間をかけて蓄積してきた知的資産と文化的記憶を含みます。
          </p>
          <p style={bodyText}>
            用途別のオープンソースモデルを地域の計算基盤で動かせば、すべての知識を海外クラウドへ送り続ける以外の選択肢を持てます。必要なものは外部モデルも使う。しかし、地域で完結できる仕事は地域で計算する。その選択権を持つことが重要です。
          </p>
        </div>
      </section>

      <section style={{ ...sectionStyle, background: '#172119' }}>
        <p style={kicker}>COOKIE-CUTTER / AGENT-RUN</p>
        <h2 style={headline}>一つの温泉を救う方法ではなく、<br />全国で再利用できる方法をつくる。</h2>
        <ol style={{ maxWidth: 940, padding: 0, margin: '40px 0 0', listStyle: 'none' }}>
          {systemFlow.map((item, index) => (
            <li key={item} style={{ display: 'grid', gridTemplateColumns: '54px 1fr', gap: 18, borderTop: '1px solid rgba(255,255,255,.18)', padding: '18px 0', fontSize: 'clamp(1rem,2vw,1.3rem)' }}>
              <span style={{ opacity: .48 }}>{String(index + 1).padStart(2, '0')}</span><span>{item}</span>
            </li>
          ))}
        </ol>
        <p style={{ ...bodyText, marginTop: 36, maxWidth: 900 }}>
          エージェントは、候補地調査、電力・通信・規制・需要・ステークホルダー・経済性の一次調査を反復し、各地域で得た知見を次の地域へ継承します。Sukatto Land Kuzuryu / eSingularityは、この仕組みの最初の実証候補です。
        </p>
      </section>

      <section id="join" style={{ ...sectionStyle, background: '#f0eee7', color: '#151815' }}>
        <p style={{ ...kicker, color: '#445246' }}>JOIN / YUMORI.me</p>
        <h2 style={{ ...headline, color: '#151815' }}>YUMORIになる。<br />地域の未来を、決まる前に守る。</h2>
        <p style={{ ...bodyText, color: '#303830', maxWidth: 850 }}>
          印西、千葉、福井、そして全国へ。住民、農家、学生、研究者、技術者、地権者、自治体関係者、経営者。巨大化した後に対処するのではなく、地域に合ったAIインフラを先に設計する準備委員会へ参加してください。
        </p>
        <div style={{ marginTop: 30, border: '1px solid #c9c5ba', borderRadius: 20, overflow: 'hidden', background: '#fff' }}>
          <iframe title="YUMORI.me 準備委員会参加フォーム" src={FORM_EMBED_URL} width="100%" height="980" style={{ border: 0, display: 'block' }} loading="lazy">読み込めない場合は参加フォームを開いてください。</iframe>
        </div>
        <p style={{ marginTop: 18 }}><a href={FORM_URL} target="_blank" rel="noreferrer" style={{ color: '#151815', fontWeight: 800 }}>フォームを別画面で開く ↗</a></p>
      </section>

      <footer style={{ padding: '44px 6vw 70px', borderTop: '1px solid rgba(255,255,255,.12)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap', maxWidth: 1200 }}>
          <div><strong>YUMORI.me</strong><p style={{ opacity: .6 }}>Guard the place. Build the alternative.</p></div>
          <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}><a href={JHR_URL} style={footerLink}>JHR</a><a href={ESINGULARITY_URL} style={footerLink}>eSingularity</a><a href="#join" style={footerLink}>JOIN</a></div>
        </div>
      </footer>
    </main>
  );
}

const sectionStyle = { padding: 'clamp(64px, 10vw, 130px) 6vw', maxWidth: 1440, margin: '0 auto' } as const;
const kicker = { letterSpacing: '.14em', fontSize: 12, fontWeight: 800, opacity: .58 } as const;
const headline = { fontSize: 'clamp(2.4rem, 6vw, 5.5rem)', lineHeight: 1.02, letterSpacing: '-.05em', margin: '18px 0 28px' } as const;
const bodyText = { fontSize: 'clamp(1.05rem, 1.8vw, 1.32rem)', lineHeight: 1.85, opacity: .82 } as const;
const primaryButton = { display: 'inline-block', padding: '14px 20px', background: '#f4f1e8', color: '#0b0d0c', borderRadius: 999, fontWeight: 800, textDecoration: 'none' } as const;
const secondaryButton = { display: 'inline-block', padding: '13px 20px', color: '#f4f1e8', border: '1px solid rgba(244,241,232,.55)', borderRadius: 999, fontWeight: 800, textDecoration: 'none' } as const;
const footerLink = { color: '#f4f1e8', textDecoration: 'none', fontWeight: 700 } as const;
