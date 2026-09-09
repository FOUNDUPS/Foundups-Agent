import type { Metadata } from 'next';

const FORM_URL = 'https://docs.google.com/forms/d/e/1FAIpQLScSKFyzCym8NCarvNIa5cT9c2Pe8C-cY2AbC4zLgsDOKspYKA/viewform';
const JHR_URL = '/reports/jhr';
const ESINGULARITY_URL = '/';
const INZAI_IMAGE = 'https://www.re-port.net/picture_l/report/0000074457_09.png';
const CITY_CONTACT_URL = 'https://www.city.fukui.lg.jp/inquiry/mailform101607.html?PAGE_NO=15196';

export const metadata: Metadata = {
  title: 'YUMORI.me — 湯守になる。壊す前に守る。地域のAIを地域へ。',
  description: 'YUMORI.meは、地域の大切な建物を壊す前に再利用を調べ、地域向けCOG DCとEducational Singularity Labへ再生する可能性を検証し、ハイパースケール時代に地域の選択権を守る市民運動です。',
  keywords: ['YUMORI.me','湯守','すかっとランド九頭竜','Japan Hyperscaler Report','JHR','COG DC','地域コンピュート','ハイパースケーラー','印西','福井','eSingularity'],
  alternates: { canonical: 'https://yumori.me/' },
  openGraph: { title: 'YUMORI.me — I am a guardian.', description: '壊す前に調べる。地域の建物・知・計算力を地域に残す。', type: 'website', url: 'https://yumori.me/' },
};

const join = { display:'inline-block', padding:'14px 22px', borderRadius:999, background:'#f4f1e8', color:'#0b0d0c', textDecoration:'none', fontWeight:850 } as const;
const darkJoin = { ...join, background:'#111511', color:'#fff' } as const;
const link = { display:'inline-block', marginRight:18, marginBottom:12, color:'inherit', fontWeight:750 } as const;
const panel = { padding:'clamp(48px,8vw,100px) 6vw' } as const;
const title = { fontSize:'clamp(2.2rem,6vw,5rem)', lineHeight:1.03, letterSpacing:'-.045em', margin:'12px 0 24px' } as const;
const body = { fontSize:'clamp(1rem,1.7vw,1.25rem)', lineHeight:1.85, maxWidth:880 } as const;

function Join({ dark=false }: { dark?: boolean }) {
  return <a href={FORM_URL} target="_blank" rel="noreferrer" style={dark ? darkJoin : join}>JOIN YUMORI / 湯守になる ↗</a>;
}

export default function YumoriPage() {
  return <main style={{ background:'#0b0d0c', color:'#f4f1e8', minHeight:'100vh', fontFamily:'system-ui,sans-serif' }}>
    <section style={{ ...panel, minHeight:'80vh', display:'grid', gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))', gap:36, alignItems:'end' }}>
      <div>
        <p style={{ letterSpacing:'.18em', fontWeight:850 }}>YUMORI.me / 湯守</p>
        <h1 style={{ fontSize:'clamp(4.5rem,14vw,10rem)', lineHeight:.8, letterSpacing:'-.075em', margin:'20px 0 32px' }}>YUMORI<span style={{opacity:.5}}>.me</span></h1>
        <p style={{ fontSize:'clamp(1.6rem,4vw,3.5rem)', lineHeight:1.15, fontWeight:800, maxWidth:1000 }}>I am a guardian.<br/>地域を守る。地域のAIを、地域のためにつくる。</p>
        <p style={body}>湯守は、湯と場所を守る人。YUMORI.meは、その考えを地域の建物、土地、文化、知識、電力、そしてAI時代の計算力へ広げます。</p>
        <div style={{marginTop:30}}><Join /></div>
        <p style={{marginTop:18, opacity:.65}}>最初の目標：1,000 YUMORI。1,000人に達した段階で、全国運動を支える正式な組織化を検討します。</p>
      </div>
      <figure style={{margin:0}}>
        <img src="/team/012-landowners.jpg" alt="YUMORI.meの地域活動写真" style={{width:'100%',display:'block',borderRadius:22,maxHeight:620,objectFit:'cover'}}/>
        <figcaption style={{fontSize:12,opacity:.65,marginTop:8}}>YUMORI.meは現場から始まった市民・地域運動です。既存の活動写真を使用。</figcaption>
      </figure>
    </section>

    <section style={{...panel, background:'#f0eadf', color:'#111511'}}>
      <p style={{fontWeight:850,letterSpacing:'.15em'}}>01 / THE HEART OF THE COMMUNITY</p>
      <h2 style={title}>地域の心臓を、<br/>壊す前に調べてほしい。</h2>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))',gap:34,alignItems:'start'}}>
        <div>
          <p style={body}>YUMORI.meは、旧すかっとランド九頭竜を守る活動から始まりました。閉館したからといって、建物の価値、地域の記憶、将来の用途までゼロになるわけではありません。</p>
          <p style={body}>福井市議会資料には解体見込み約15.8億円が示されています。問うべきなのは、<strong>その費用を支出する前に、再利用・民間投資・地域コンピュートなどの代替案を十分に比較したのか</strong>ということです。</p>
          <p style={body}>私たちは結論を決めつけません。60日間、比較してほしい。壊す前に調べる。それがYUMORIの出発点です。</p>
          <div style={{marginTop:26}}><Join dark /></div>
        </div>
        <figure style={{margin:0}}>
          <img src="/yumori-economic-flow-ja.svg" alt="約15.8億円の解体案と地域再生案を比較するYUMORI経済フロー" style={{width:'100%',display:'block',borderRadius:18,background:'#fff'}}/>
          <figcaption style={{fontSize:12,opacity:.65,marginTop:8}}>既存のYUMORI経済フロー。約15.8億円は市議会質問資料に示された解体見込み。再生案は成立性を検証する構想です。</figcaption>
        </figure>
      </div>
    </section>

    <section style={panel}>
      <p style={{fontWeight:850,letterSpacing:'.15em'}}>02 / REUSE — TURN WASTE INTO INFRASTRUCTURE</p>
      <h2 style={title}>壊して終わる建物を、<br/>地域のAIインフラへ。</h2>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))',gap:34,alignItems:'start'}}>
        <div>
          <p style={body}>全国には、公共施設、工場、ホテル、倉庫、温浴施設など、十分に使われていない建物があります。すべてをデータセンターにできるわけではありません。だから構造、電力、光回線、冷却、排熱先を先に調べ、成立する場所だけを再利用する。</p>
          <p style={body}><strong>COG DC — Community-Owned Green Data Center</strong> は1MWから始め、5→10→20MWへ必要な分だけ育てるモジュール型。第一用途は計算力の輸出ではなく、地域の学校、大学、農業、病院、自治体、ものづくり、企業です。</p>
          <p style={body}>Educational Singularity Lab、学生、研究、FoundUps、地域企業を同じ拠点につなぎ、データセンターを「箱」ではなく地域再生のハブにする。</p>
          <p><a href={ESINGULARITY_URL} style={link}>eSingularity / 福井の実証構想を見る →</a></p>
          <Join />
        </div>
        <figure style={{margin:0}}>
          <img src="/satellite-view.jpeg" alt="旧すかっとランド九頭竜と周辺土地を使った既存のYUMORI配置構想" style={{width:'100%',display:'block',borderRadius:18}}/>
          <figcaption style={{fontSize:12,opacity:.65,marginTop:8}}>既存のYUMORI配置構想。完成済み施設ではなく、再利用可能性を検討するための概念図です。</figcaption>
        </figure>
      </div>
    </section>

    <section style={{...panel, background:'#dce2d6', color:'#111511'}}>
      <p style={{fontWeight:850,letterSpacing:'.15em'}}>03 / SEE WHAT IS COMING — HYPERSCALE</p>
      <h2 style={title}>印西を見てください。<br/>次は、あなたの地域かもしれない。</h2>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))',gap:34,alignItems:'start'}}>
        <div>
          <p style={body}>千葉・印西では、巨大データセンターの集積が、電力、土地、景観、騒音、都市計画、地域との共存の問題になっています。米国ではさらに大きな集積が先に進み、広大なキャンパスと送電インフラが地域の景色そのものを変えてきました。</p>
          <p style={body}>寺、神社、田んぼ、学校、病院、住宅がある景色を見て、その隣に数十ヘクタール、数百MW級の施設が来る未来を想像してください。YUMORIはデータセンターそのものに反対するのではなく、<strong>地域が来る前にルールと代替案を持つ</strong>ための運動です。</p>
          <p><a href={JHR_URL} style={link}>JAPAN HYPERSCALER REPORT #001 を読む →</a></p>
          <Join dark />
        </div>
        <figure style={{margin:0}}><img src={INZAI_IMAGE} alt="千葉県印西市の大規模データセンター開発地" style={{width:'100%',display:'block',borderRadius:18}}/><figcaption style={{fontSize:12,opacity:.65,marginTop:8}}>DPDC印西パーク開発地。画像出典: R.E.port。規模理解のための外部参照画像。</figcaption></figure>
      </div>
    </section>

    <section style={{...panel, background:'#f4f1e8', color:'#111511'}}>
      <p style={{fontWeight:850,letterSpacing:'.15em'}}>ACT / JOIN · READ · CALL</p>
      <h2 style={title}>1,000人のYUMORIから、<br/>地域の選択肢をつくる。</h2>
      <p style={body}>参加する。新しいJapan Hyperscaler Reportを読む。家族や地域に知らせる。そして行政や議会に「壊す前に代替案を比較してほしい」「ハイパースケールが来る前に地域AIインフラ政策を議論してほしい」と伝える。</p>
      <div style={{display:'flex',gap:12,flexWrap:'wrap',margin:'28px 0'}}>
        <Join dark />
        <a href={JHR_URL} style={{...darkJoin,background:'#334537'}}>NEW — JAPAN HYPERSCALER REPORT #001 →</a>
        <a href={CITY_CONTACT_URL} target="_blank" rel="noreferrer" aria-label="福井市へ電話・連絡する" style={{...darkJoin,background:'#6b3e2e'}}>☎ 福井市に電話・連絡する ↗</a>
      </div>
    </section>
  </main>;
}
