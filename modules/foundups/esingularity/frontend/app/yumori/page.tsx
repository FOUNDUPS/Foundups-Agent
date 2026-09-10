import type { Metadata } from 'next';
import { currentFieldStatus } from '../../content/current-field-status';
import YumoriImageRotator from './YumoriImageRotator';

const FORM_URL = 'https://docs.google.com/forms/d/e/1FAIpQLScSKFyzCym8NCarvNIa5cT9c2Pe8C-cY2AbC4zLgsDOKspYKA/viewform';
const JHR_URL = '/reports/jhr';
const ESINGULARITY_URL = 'https://esingularity.ai/';
const YUMORI_INFO_URL = 'https://yumori.info/';
const INZAI_IMAGE = 'https://www.re-port.net/picture_l/report/0000074457_09.png';
const FUKUI_HYPERSCALE_COMPARISON_IMAGE = '/yumori-inzai-fukui-comparison.webp';
const CITY_CONTACT_URL = 'https://www.city.fukui.lg.jp/inquiry/mailform101607.html?PAGE_NO=15196';
const MAYOR_CONTACT_URL = 'https://www.city.fukui.lg.jp/inquiry/mailform10662.html?PAGE_NO=178';
const COUNCIL_ROSTER_URL = 'https://www.city.fukui.lg.jp/sisei/gikai/giin/p015976.html';
const COUNCIL_MEMBERS_URL = 'https://www.city.fukui.lg.jp/sisei/gikai/giin/p020856.html';

const budgetCommittee = [
  { name: '八田 一以', phone: '0776-54-0849', role: '委員長' },
  { name: '堀川 秀樹', phone: '090-3292-0136', role: '副委員長' },
  { name: '奥島 光晴', phone: '0776-36-3418' },
  { name: '堀江 廣海', phone: '0776-41-2589' },
  { name: '藤田 諭', phone: '0776-98-4556' },
  { name: '田中 義乃', phone: '0776-23-2131' },
  { name: '近藤 實', phone: '0776-54-7921' },
  { name: '菅生 敬一', phone: '0776-54-3672' },
  { name: '池上 優徳', phone: '0776-86-1155' },
  { name: '寺島 恭也', phone: '0776-25-4677' },
  { name: '山田 文葉', phone: '090-9767-7469' },
  { name: '酒井 良樹', phone: '0776-54-0590' },
  { name: '榊原 光賀', phone: '080-3048-2989' },
  { name: '漆﨑 與', phone: '0776-38-1350' },
  { name: '髙田 稔浩', phone: '0776-34-2075' },
] as const;

const heroSlides = [
  {
    src: '/yumori-protest-1.svg',
    alt: '九頭龍の旗を掲げてYUMORIの一人抗議を行う僧',
    caption: 'YUMORIは現場から始まります。九頭龍の旗とともに、一人で声を上げる。',
  },
  {
    src: FUKUI_HYPERSCALE_COMPARISON_IMAGE,
    alt: '印西クラスの巨大データセンターを旧すかっとランド九頭竜周辺の田園に重ねた概念比較図',
    caption: 'もし印西クラスの土地利用が福井に来たら？ 概念比較図です。タップして詳しく見る。',
    href: '#hyperscale',
  },
  {
    src: INZAI_IMAGE,
    alt: '千葉県印西市の大規模データセンター開発地',
    caption: 'CHIBA / INZAI — 大規模データセンター集積の現実。タップして福井との比較を見る。',
    href: '#hyperscale',
  },
] as const;

const hyperscaleSlides = [
  {
    src: INZAI_IMAGE,
    alt: '千葉県印西市の大規模データセンター開発地',
    caption: 'CHIBA / INZAI — 現実の集積。DPDC印西パーク開発地。画像出典: R.E.port。規模理解のための外部参照画像。',
  },
  {
    src: FUKUI_HYPERSCALE_COMPARISON_IMAGE,
    alt: '印西クラスの大規模データセンターを旧すかっとランド九頭竜周辺の田園に重ねた概念比較図',
    caption: 'FUKUI — もし同じ規模の土地利用が来たら。公開情報をもとにした概念比較。実際の用地計画・測量・立地決定ではありません。',
  },
] as const;

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
    <section aria-label="現在の現場情報" style={{padding:'12px 6vw',background:'#f4f1e8',color:'#111511',lineHeight:1.5}}>
      <strong style={{marginRight:10}}>LIVE · {currentFieldStatus.updatedLabelJa}</strong>
      <span>{currentFieldStatus.detailJa}</span>
      <span lang="en" style={{display:'block',fontSize:12,opacity:.7,marginTop:3}}>{currentFieldStatus.detailEn}</span>
    </section>

    <section style={{ ...panel, minHeight:'80vh', display:'grid', gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))', gap:36, alignItems:'end' }}>
      <div>
        <p style={{ letterSpacing:'.18em', fontWeight:850 }}>YUMORI.me / 湯守</p>
        <h1 style={{ fontSize:'clamp(4.5rem,14vw,10rem)', lineHeight:.8, letterSpacing:'-.075em', margin:'20px 0 32px' }}>YUMORI<span style={{opacity:.5}}>.me</span></h1>
        <p style={{ fontSize:'clamp(1.6rem,4vw,3.5rem)', lineHeight:1.15, fontWeight:800, maxWidth:1000 }}>I am a guardian.<br/>地域を守る。地域のAIを、地域のためにつくる。</p>
        <p style={body}>湯守は、湯と場所を守る人。YUMORI.meは、その考えを地域の建物、土地、文化、知識、電力、そしてAI時代の計算力へ広げます。</p>
        <div style={{marginTop:30,display:'flex',gap:12,flexWrap:'wrap'}}>
          <Join />
          <a href="#hyperscale" style={{...join,background:'#8b5b2b',color:'#fff'}}>福井に何が来るのか見る ↓</a>
          <a href={JHR_URL} style={{...join,background:'#334537',color:'#fff'}}>JHR 最新レポート →</a>
          <a href={YUMORI_INFO_URL} target="_blank" rel="noreferrer" style={{...join,background:'#6b3e2e',color:'#fff'}}>YUMORI.info / 資料 ↗</a>
        </div>
        <p style={{marginTop:18, opacity:.65}}>最初の目標：1,000 YUMORI。1,000人に達した段階で、全国運動を支える正式な組織化を検討します。</p>
      </div>
      <YumoriImageRotator slides={heroSlides} intervalMs={5500} aspectRatio="16 / 9" maxHeight={620} />
    </section>

    <section style={{...panel, background:'#f0eadf', color:'#111511'}}>
      <p style={{fontWeight:850,letterSpacing:'.15em'}}>01 / THE HEART OF THE COMMUNITY</p>
      <h2 style={title}>地域の心臓を、<br/>壊す前に調べてほしい。</h2>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))',gap:34,alignItems:'start'}}>
        <div>
          <p style={body}>YUMORI.meは、旧すかっとランド九頭竜を守る活動から始まりました。閉館したからといって、建物の価値、地域の記憶、将来の用途までゼロになるわけではありません。</p>
          <p style={body}>福井市議会資料には解体見込み約15.8億円が示されています。問うべきなのは、<strong>その費用を支出する前に、再利用・民間投資・地域コンピュートなどの代替案を十分に比較したのか</strong>ということです。</p>
          <p style={body}><strong>今の最優先は、解体を止めることです。</strong> 解体前に、再利用の可能性を検証する時間を確保してほしい。壊す前に調べる。それがYUMORIの出発点です。</p>
          <div style={{marginTop:26}}><Join dark /></div>
        </div>
        <figure style={{margin:0}}>
          <img src="/yumori-economic-flow-ja.svg" alt="約15.8億円の解体案と地域再生案を比較するYUMORI経済フロー" style={{width:'100%',display:'block',borderRadius:18,background:'#fff'}}/>
          <figcaption style={{fontSize:12,opacity:.65,marginTop:8}}>既存のYUMORI経済フロー。約15.8億円は市議会質問資料に示された解体見込み。再生案は成立性を検証する構想です。</figcaption>
        </figure>
      </div>
    </section>

    <section id="hyperscale" style={{...panel, background:'#dce2d6', color:'#111511', scrollMarginTop:24}}>
      <p style={{fontWeight:850,letterSpacing:'.15em'}}>02 / SEE WHAT IS COMING — HYPERSCALE</p>
      <h2 style={title}>印西を見てください。<br/>これが福井の田園に来たら？</h2>
      <p style={{...body,maxWidth:1050}}>千葉・印西／白井は、国内最大級のデータセンター集積地です。NTT DATAは2026年4月、このエリアで<strong>約250MW</strong>の新キャンパス開発を発表しました。印西市では、駅周辺のデータセンター建設に伴う景観・騒音への懸念が都市計画上の課題として明記され、地区計画の変更も進んでいます。</p>
      <p style={{...body,maxWidth:1050}}>国も地方分散を進めています。経済産業省は9道県を「データセンター集積型GX戦略地域」の有望地域として一次選定し、将来的なGW級拡張や30ha以上を目安とする産業用地を想定しています。9月9日には仙台で、約7.2ha・200MW級のAIデータセンター構想も発表されました。</p>

      <div style={{maxWidth:980,margin:'30px 0 26px'}}>
        <YumoriImageRotator slides={hyperscaleSlides} intervalMs={6500} aspectRatio="4 / 3" maxHeight={720} />
      </div>

      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))',gap:34,alignItems:'start'}}>
        <div>
          <p style={body}>福井にハイパースケール・キャンパスの立地が決まったわけではありません。ただし、福井市と小浜市はすでにGX戦略地域の<strong>「脱炭素電源活用型」有望地域</strong>に入っています。電力とAIインフラをめぐる全国競争の外にいるわけではありません。</p>
          <p style={body}>だからYUMORIが提案するのは「データセンター反対」ではありません。<strong>地域の需要を、地域の小さなコンピュートで先に満たす。</strong> 既存建物を再利用し、1MWから始め、5→10→20MWへ必要な分だけ育てる。学校、大学、病院、農業、自治体、地域企業が使える計算資源を地域に残し、排熱も地域で使う。</p>
          <p style={body}>巨大な外部キャンパスが来てから土地・電力・景観を守るのでは遅い。<strong>今のうちに地域側のAIインフラを設計することが、ハイパースケール集中への現実的な緩和策です。</strong></p>
          <div style={{display:'flex',gap:12,flexWrap:'wrap',marginTop:22}}>
            <a href={JHR_URL} style={{...darkJoin,background:'#334537'}}>JAPAN HYPERSCALER REPORT — 9/10更新版 →</a>
            <a href={YUMORI_INFO_URL} target="_blank" rel="noreferrer" style={{...darkJoin,background:'#4b5660'}}>YUMORI.info / 詳細資料 ↗</a>
            <Join dark />
          </div>
        </div>
        <aside style={{padding:'22px',borderRadius:18,background:'#111511',color:'#fff'}}>
          <p style={{margin:'0 0 8px',fontWeight:900,letterSpacing:'.1em'}}>YUMORI POSITION</p>
          <p style={{fontSize:'clamp(1.15rem,2vw,1.55rem)',lineHeight:1.55,margin:0,fontWeight:800}}>データセンターは来る。<br/>だから、地域の土地・電力・利益を守る設計を先にする。</p>
          <p lang="en" style={{fontSize:14,lineHeight:1.65,opacity:.8,marginBottom:0}}>Data centers are coming. The choice is whether communities design local compute first—or wait until land, power and value are concentrated elsewhere.</p>
        </aside>
      </div>
    </section>

    <section style={panel}>
      <p style={{fontWeight:850,letterSpacing:'.15em'}}>03 / REUSE — TURN WASTE INTO INFRASTRUCTURE</p>
      <h2 style={title}>壊して終わる建物を、<br/>地域のAIインフラへ。</h2>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))',gap:34,alignItems:'start'}}>
        <div>
          <p style={body}>全国には、公共施設、工場、ホテル、倉庫、温浴施設など、十分に使われていない建物があります。すべてをデータセンターにできるわけではありません。だから構造、電力、光回線、冷却、排熱先を先に調べ、成立する場所だけを再利用する。</p>
          <p style={body}><strong>COG DC — Community-Owned Green Data Center</strong> は1MWから始め、5→10→20MWへ必要な分だけ育てるモジュール型。第一用途は計算力の輸出ではなく、地域の学校、大学、農業、病院、自治体、ものづくり、企業です。</p>
          <p style={body}>Educational Singularity Lab、学生、研究、FoundUps、地域企業を同じ拠点につなぎ、データセンターを「箱」ではなく地域再生のハブにする。</p>
          <p><a href={ESINGULARITY_URL} target="_blank" rel="noreferrer" style={link}>eSingularity / 福井の実証構想を見る →</a></p>
          <Join />
        </div>
        <figure style={{margin:0}}>
          <img src="/satellite-view.jpeg" alt="旧すかっとランド九頭竜と周辺土地を使った既存のYUMORI配置構想" style={{width:'100%',display:'block',borderRadius:18}}/>
          <figcaption style={{fontSize:12,opacity:.65,marginTop:8}}>既存のYUMORI配置構想。完成済み施設ではなく、再利用可能性を検討するための概念図です。</figcaption>
        </figure>
      </div>
    </section>

    <section style={{...panel, background:'#7a1f1f', color:'#fff'}}>
      <p style={{fontWeight:900,letterSpacing:'.15em'}}>緊急行動 / CALL NOW</p>
      <h2 style={title}>9月25日を待たないでください。</h2>
      <p style={{...body,fontWeight:750}}>旧すかっとランド九頭竜の解体を止めるため、<strong>今、市長と予算特別委員へ声を届けてください。</strong> 解体予算が決まれば、止めることはさらに難しくなります。</p>

      <div style={{margin:'28px 0',padding:'22px',background:'rgba(255,255,255,.1)',borderRadius:18,maxWidth:980}}>
        <p style={{margin:'0 0 8px',fontWeight:900}}>電話では、これだけ伝えてください。</p>
        <p style={{fontSize:'clamp(1.2rem,2.5vw,1.8rem)',lineHeight:1.55,margin:0,fontWeight:850}}>「旧すかっとランド九頭竜を、再活用の可能性を十分に検証する前に解体しないでください。解体予算に反対してください。」</p>
      </div>

      <div style={{display:'flex',gap:12,flexWrap:'wrap',margin:'24px 0 34px'}}>
        <a href="tel:0776205205" style={{...join,background:'#fff',color:'#7a1f1f'}}>☎ 西行市長・秘書課 0776-20-5205</a>
        <a href={MAYOR_CONTACT_URL} target="_blank" rel="noreferrer" style={{...join,background:'#fff',color:'#7a1f1f'}}>✉ 市長へメール ↗</a>
        <a href="tel:0776205510" style={{...join,background:'#111511',color:'#fff'}}>☎ 市議会 議事調査課 0776-20-5510</a>
        <Join />
      </div>

      <h3 style={{fontSize:'clamp(1.5rem,3vw,2.4rem)',margin:'0 0 18px'}}>予算特別委員会 — 一人ひとりに電話できます</h3>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(220px,1fr))',gap:12,maxWidth:1100}}>
        {budgetCommittee.map((member) => (
          <a key={member.name} href={`tel:${member.phone.replace(/-/g,'')}`} style={{display:'block',padding:'16px 18px',borderRadius:14,background:'#fff',color:'#111511',textDecoration:'none'}}>
            <strong style={{display:'block',fontSize:'1.08rem'}}>{member.name}{'role' in member && member.role ? `　${member.role}` : ''}</strong>
            <span style={{display:'block',marginTop:6,fontWeight:800}}>☎ {member.phone}</span>
          </a>
        ))}
      </div>

      <p style={{marginTop:22,fontSize:13,opacity:.8}}>委員会名簿は福井市公式サイト（2026年8月31日現在）、電話番号は福井市議員名簿を参照。</p>
      <p style={{marginTop:8}}>
        <a href={COUNCIL_ROSTER_URL} target="_blank" rel="noreferrer" style={{...link,color:'#fff'}}>福井市 予算特別委員会名簿 ↗</a>
        <a href={COUNCIL_MEMBERS_URL} target="_blank" rel="noreferrer" style={{...link,color:'#fff'}}>福井市 議員名簿・連絡先 ↗</a>
      </p>
    </section>

    <section style={{...panel, background:'#f4f1e8', color:'#111511'}}>
      <p style={{fontWeight:850,letterSpacing:'.15em'}}>ACT / JOIN · READ · CALL</p>
      <h2 style={title}>1,000人のYUMORIから、<br/>地域の選択肢をつくる。</h2>
      <p style={body}>参加する。新しいJapan Hyperscaler Reportを読む。YUMORI.infoで資料を確認する。家族や地域に知らせる。そして行政や議会に「壊す前に代替案を比較してほしい」「ハイパースケールが来る前に地域AIインフラ政策を議論してほしい」と伝える。</p>
      <div style={{display:'flex',gap:12,flexWrap:'wrap',margin:'28px 0'}}>
        <Join dark />
        <a href={JHR_URL} style={{...darkJoin,background:'#334537'}}>UPDATED 9/10 — JAPAN HYPERSCALER REPORT #001 →</a>
        <a href={YUMORI_INFO_URL} target="_blank" rel="noreferrer" style={{...darkJoin,background:'#4b5660'}}>YUMORI.info / 計画・資料 ↗</a>
        <a href={CITY_CONTACT_URL} target="_blank" rel="noreferrer" aria-label="福井市へ電話・連絡する" style={{...darkJoin,background:'#6b3e2e'}}>☎ 福井市に電話・連絡する ↗</a>
      </div>
    </section>
  </main>;
}
