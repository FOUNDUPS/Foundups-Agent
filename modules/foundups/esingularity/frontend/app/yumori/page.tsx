import type { Metadata } from 'next';
import CampaignTicker from '../../components/CampaignTicker';

const FORM_URL = 'https://docs.google.com/forms/d/e/1FAIpQLScSKFyzCym8NCarvNIa5cT9c2Pe8C-cY2AbC4zLgsDOKspYKA/viewform';
const JHR_URL = '/reports/jhr';
const ESINGULARITY_URL = 'https://esingularity.ai/';
const INZAI_IMAGE = 'https://www.re-port.net/picture_l/report/0000074457_09.png';

export const metadata: Metadata = {
  title: 'YUMORI.me — 湯守になる。地域を守り、地域のAIをつくる',
  description: '福井の企業・大学・農業・地域とともに、独立性のある地域AI基盤の実現可能性を検討するYUMORI.me。企業のAI担当代表者・実装パートナーを募ります。',
  keywords: ['YUMORI.me','湯守','Japan Hyperscaler Report','JHR','COG DC','地域コンピュート','ハイパースケーラー','印西','福井','eSingularity'],
  alternates: { canonical: 'https://yumori.me/' },
  openGraph: { title: 'YUMORI.me — 湯守になる', description: '知る。守る。つくる。湯守になる。', type: 'website', url: 'https://yumori.me/' },
};

const join = { display:'inline-block', padding:'14px 22px', borderRadius:999, background:'#f4f1e8', color:'#0b0d0c', textDecoration:'none', fontWeight:850 } as const;
const darkJoin = { ...join, background:'#111511', color:'#fff' } as const;
const link = { display:'inline-block', marginRight:18, color:'inherit', fontWeight:750 } as const;
const panel = { padding:'clamp(48px,8vw,100px) 6vw' } as const;
const title = { fontSize:'clamp(2.2rem,6vw,5rem)', lineHeight:1.03, letterSpacing:'-.045em', margin:'12px 0 24px' } as const;
const body = { fontSize:'clamp(1rem,1.7vw,1.25rem)', lineHeight:1.85, maxWidth:850 } as const;

function Join({ dark=false }: { dark?: boolean }) {
  return <a href={FORM_URL} target="_blank" rel="noreferrer" style={dark ? darkJoin : join}>JOIN YUMORI.me / 湯守になる ↗</a>;
}
export default function YumoriPage() {
  return <main className="yumori-page" style={{ background:'#0b0d0c', color:'#f4f1e8', minHeight:'100vh', fontFamily:'system-ui,sans-serif' }}>
    <header className="yumori-header"><a href="https://yumori.me/">YUMORI.me / 湯守</a><div id="home-language-controls" /></header>
    <CampaignTicker movement />
    <section aria-labelledby="coalition-title" style={{...panel, background:'#172119', color:'#f4f1e8'}}>
      <p style={{letterSpacing:'.15em',fontWeight:850}}>福井 / AIパートナー連携 — 企業・団体の参加相談</p>
      <h2 id="coalition-title" style={title}>福井のAI基盤を、<br/>福井の企業と地域でつくる。</h2>
      <p style={body}>企業のAI責任者・担当代表者の皆さまへ。地域企業、大学、農業、教育機関が必要とする計算資源を、地域の電力・土地・暮らしと両立させるためのパートナー連携を準備しています。運営・技術・利用・資金・教育の観点から、一緒に実現条件を検討しませんか。</p>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,260px),1fr))',gap:14,maxWidth:900,margin:'24px 0'}}>
        <div style={{padding:22,border:'1px solid #63866a',borderRadius:18,background:'#20342a'}}><strong>企業・大学・農業・地域</strong><p>AIの利用課題・必要なサービス・地域への効果</p></div>
        <div style={{padding:22,border:'1px solid #63866a',borderRadius:18,background:'#20342a'}}><strong>YUMORI.me パートナー連携</strong><p>需要調査・計画・実施体制・資金条件の検討</p></div>
        <div style={{padding:22,border:'1px solid #63866a',borderRadius:18,background:'#20342a'}}><strong>運営・技術パートナー</strong><p>設計・整備・運営の実施可能性を検証</p></div>
      </div>
      <p style={{fontSize:13,opacity:.82,maxWidth:850}}>構想・協議の段階です。参加企業、建物利用権、受電容量、顧客契約、資金、市の承認や事業成立は未確定です。福井市の旧羽生小学校を初期候補として調査し、旧下宇坂小学校は教育・拡張候補、旧すかっとランド九頭竜は別の条件付き検討対象です。</p>
      <div style={{display:'flex',gap:14,flexWrap:'wrap',marginTop:26}}>
        <a href="/yumori/partners" style={join}>企業・団体の参加を相談する →</a>
        <a href={ESINGULARITY_URL} style={{...link,alignSelf:'center'}}>計画と技術構想を知る →</a>
      </div>
      <p style={{marginTop:18,fontSize:14}}>個人の湯守参加も継続しています。 <a href={FORM_URL} target="_blank" rel="noreferrer" style={{color:'inherit',fontWeight:800}}>JOIN YUMORI.me / 湯守になる →</a></p>
    </section>
    <section className="yumori-hero" style={panel}>
      <p style={{ letterSpacing:'.18em', fontWeight:850 }}>YUMORI.me / 湯守</p>
      <h1 className="yumori-wordmark">YUMORI<span style={{opacity:.5}}>.me</span></h1>
      <p style={{ fontSize:'clamp(1.6rem,4vw,3.5rem)', lineHeight:1.15, fontWeight:800, maxWidth:1000 }}>私は湯守！ / me GUARDIAN! = YUMORI.me<br/>日本の地域を守り、地域のAIをつくる。</p>
      <figure className="yumori-hero-image"><img src="/yumori-compute-field.png" width="1672" height="941" alt="田園と地域の小規模AI計算基盤を組み合わせた再生構想" fetchPriority="high" /><figcaption>地域の未来を、地域でつくる。<span>再生構想のイメージ・実在の完成施設ではありません</span></figcaption></figure>
      <p style={body}>湯守は、本来、湯と場所を守る人。YUMORI.meは、その考えを地域へ広げます。AIインフラは必要です。しかし、土地・電力・知識・文化の未来を、地域の外だけで決めさせない。知る。守る。そして別の形をつくる。</p>
      <p style={body}>9月25日の採決は終了しました。旧すかっとランド九頭竜について、設立準備委員会は解体工事に進む前のPPP/PFIによる解体案と再利用案の比較検証を求めています。<a href="/vote-no" style={link}>現在の要請と公開記録を見る →</a></p>
      <div style={{marginTop:30}}><Join /></div>
      <p style={{marginTop:18, opacity:.65}}>準備委員会の最初の目標：1,000人。1,000人に達した段階で、全国運動を支える正式な組織化を検討します。</p>
    </section>

    <section style={{...panel, background:'#e9e3d6', color:'#111511'}}>
      <p style={{fontWeight:850,letterSpacing:'.15em'}}>01 / WHY — KNOW WHAT IS COMING</p>
      <h2 style={title}>ハイパースケールは、<br/>建物一棟の話ではない。</h2>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,280px),1fr))',gap:32,alignItems:'start'}}>
        <div><p style={body}>千葉・印西では巨大データセンターの集積が、電力、土地、景観、騒音、都市計画、地域との共存の問題になっています。米国ではさらに先の巨大集積をすでに経験しています。日本は、その結果を見てから動く必要はありません。</p>
          <p style={body}>YUMORIはデータセンターそのものに反対する運動ではありません。地域が、巨大投資の後ではなく<strong>前に</strong>選択できるようにする運動です。</p>
          <p><a href={JHR_URL} style={link}>ジャパン・ハイパースケーラー・レポート（JHR）を読む →</a></p><Join dark /></div>
        <figure style={{margin:0}}><img src={INZAI_IMAGE} alt="印西の大規模データセンター開発地" style={{width:'100%',borderRadius:18}}/><figcaption style={{fontSize:12,opacity:.6,marginTop:8}}>DPDC印西パーク開発地。画像出典: R.E.port。</figcaption></figure>
      </div>
    </section>

    <section style={panel}>
      <p style={{fontWeight:850,letterSpacing:'.15em'}}>02 / WHAT — REUSE BEFORE DEMOLITION</p>
      <h2 style={title}>壊す前に調べる。<br/>地域の建物を、地域のAIインフラへ。</h2>
      <p style={body}>YUMORI.meは、旧すかっとランド九頭竜を守る活動から始まりました。使える可能性のある公共施設、工場、ホテル、倉庫、温浴施設を、解体費を払って消す前に、構造・電力・光回線・冷却・排熱利用を調べる。成立する場所では、解体費を生産的な再生投資へ変えられないか検証します。</p>
      <p style={body}><strong>COG DC — Community-Owned Green Data Center</strong> は、MWを先に決めて建てる構想ではありません。学校、大学、農業、病院、自治体、ものづくり、企業が実際に必要とする計算サービスと契約需要から必要な計算資源を逆算し、電力・光回線・建物条件が成立する範囲で段階的に拡張します。地域のデータだけでなく、農業の経験、工程、教材、方言、歴史、文化的記憶を含む「地域の知」を地域で扱える選択肢をつくります。</p>
      <div style={{marginTop:28}}><Join /></div>
    </section>

    <section style={{...panel, background:'#172119'}}>
      <p style={{fontWeight:850,letterSpacing:'.15em'}}>03 / HOW — TURN COMPUTE INTO REVITALIZATION</p>
      <h2 style={title}>データセンターを箱で終わらせない。<br/>地域再生のハブにする。</h2>
      <p style={body}>COG DCの隣にEducational Singularity Labを置く。学生が地域の計算資源で学び、研究し、地域課題を解く。FoundUpsと地域企業が試作し、起業する。回収可能な熱は、温浴、暖房、農業、融雪など、その地域に合う用途を技術検証する。</p>
      <p style={body}>そして方法そのものをエージェントで反復可能にします。候補施設 → 構造 → 電力 → 光回線 → 熱需要 → 顧客・地域の計算需要 → 売上・資金条件 → 必要な計算資源 → 段階導入 → 実利用に応じた拡張。福井で学んだ方法を、次の地域が最初から使えるようにする。</p>
      <p><a href={ESINGULARITY_URL} style={link}>eSingularity / 福井の実証を見る →</a></p><Join />
    </section>

    <section style={{...panel, background:'#f4f1e8', color:'#111511', textAlign:'center'}}>
      <p style={{fontWeight:850,letterSpacing:'.15em'}}>ACT / 1,000 YUMORI</p>
      <h2 style={{...title,maxWidth:1000,margin:'12px auto 24px'}}>地域を守る人が、地域の未来を決める。</h2>
      <p style={{...body,margin:'0 auto 30px'}}>準備委員会に参加する。JHRを読む。地域の人に知らせる。議員・市長・県議・国会議員に「ハイパースケールが来る前に地域のAIインフラ政策を議論してほしい」と伝える。福井だけの運動ではありません。</p>
      <Join dark />
    </section>
  </main>;
}
