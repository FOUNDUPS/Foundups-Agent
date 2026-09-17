import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import LineButton from '../../../components/LineButton';
import Brand from '../../../components/Brand';
import { notFound } from 'next/navigation';
import { getTeamProfile, publicTeamProfiles } from '../../../lib/team';

const LINE_URL = 'https://line.me/ti/p/baXEozL_Q6';

export function generateStaticParams() {
  return publicTeamProfiles.map((profile) => ({ slug: profile.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const profile = getTeamProfile(slug);
  if (!profile) return {};
  return {
    title: `${profile.name} | Team | eSingularity.ai`,
    description: profile.introduction,
    openGraph: {
      title: `${profile.name} | eSingularity.ai`,
      description: profile.introduction,
      url: `https://esingularity.ai/team/${profile.slug}`,
      ...(profile.image ? { images: [{ url: profile.image, alt: profile.imageAlt ?? profile.name }] } : {}),
    },
  };
}

function ProfileVisual({ name, role }: { name: string; role: string }) {
  return (
    <div
      aria-label={`${name} — ${role}`}
      style={{
        position: 'absolute',
        inset: 0,
        display: 'grid',
        placeItems: 'center',
        alignContent: 'center',
        gap: '12px',
        padding: '28px',
        textAlign: 'center',
        background: 'radial-gradient(circle at 50% 35%, #164d9b 0, #071b37 45%, #020813 100%)',
      }}
    >
      <small style={{ fontFamily: 'var(--font-mono), monospace', letterSpacing: '.16em', color: 'var(--cyan)' }}>AI KOBAN · COGDC</small>
      <strong style={{ maxWidth: '460px', color: 'var(--white)', fontSize: 'clamp(26px, 4vw, 52px)', lineHeight: 1.05 }}>{name}</strong>
      <span style={{ maxWidth: '430px', color: 'rgba(248,251,255,.65)', fontSize: '11px', lineHeight: 1.7 }}>{role}</span>
    </div>
  );
}

export default async function TeamProfilePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const profile = getTeamProfile(slug);
  if (!profile) notFound();

  return (
    <>
      <header className="site-header team-site-header">
        <Brand href="/#top" />
        <nav aria-label="Primary navigation"><Link href="/">温泉を守る</Link><Link href="/#innovation-hub">AI拠点</Link><Link href="/future">福井の未来</Link><Link href="/team">チーム</Link></nav>
        <LineButton />
      </header>

      <main className="profile-page">
        <section className="profile-hero">
          <div className="profile-photo">
            {profile.image ? (
              <Image src={profile.image} alt={profile.imageAlt ?? profile.name} fill priority sizes="(max-width: 900px) 100vw, 50vw" style={{ objectPosition: profile.imagePosition ?? '50% 50%' }} />
            ) : (
              <ProfileVisual name={profile.name} role={profile.role} />
            )}
            <span>{profile.role}</span>
          </div>
          <div className="profile-title">
            <Link href="/team">← TEAM DIRECTORY</Link>
            <p>{profile.role}</p>
            <h1>{profile.name}</h1>
            <strong>{profile.secondary}</strong>
            <div className="profile-number">{profile.slug === '012' || profile.slug === '0102' ? profile.slug : 'eS'}</div>
          </div>
        </section>

        <section className="profile-story">
          <div className="profile-lead"><p className="eyebrow"><span /> WHY THIS PERSON IS HERE</p><h2>{profile.introduction}</h2></div>
          <div className="profile-statement"><p>{profile.statement}</p>{profile.disclosure && <aside><span>TRANSPARENCY</span>{profile.disclosure}</aside>}</div>
        </section>

        <section className="profile-facts">
          {profile.facts.map((fact) => <article key={fact.label}><span>{fact.label}</span><strong>{fact.value}</strong></article>)}
        </section>

        {profile.slug === '012' && (
          <section className="profile-memory" id="onsen-memory">
            <div><p className="eyebrow light"><span /> A MEMORY FROM THE ONSEN</p><h2>温泉は、建物ではなく、<br />思い出も残す。</h2></div>
            <blockquote><p>長男トミーを初めて温泉に抱いて入った日のことを覚えています。見上げて笑い、声を上げて喜んでいました。次の瞬間、小さな「うんち」が湯にぷかり。驚いたけれど、いま振り返ると家族で笑える、昨日のことのような思い出です。</p><footer>— 012 · 九頭龍 泰澄</footer></blockquote>
          </section>
        )}

        {profile.slug === '012' && (
          <section className="profile-special">
            <div><p className="eyebrow light"><span /> THE EDUCATIONAL SINGULARITY</p><h2>2007年に始めた未来が、<br />第3段階へ向かう。</h2></div>
            <ol><li><span>01 · FOUNDATION</span><strong>デジタルで学びへ到達する</strong><p>教材とネットワークが、場所や所得によるアクセスの壁を下げる。</p></li><li><span>02 · AI</span><strong>AIが個別に教える</strong><p>生成AIが専門知識、言語、創作、技術を対話によって個別最適化する。</p></li><li><span>03 · COMPUTE</span><strong>AIが地域革新の基盤になる</strong><p>学校、大学、農業、企業、地域が、自分たちが利用できる計算力を持つ。AI交番はこの層を検証する。</p></li></ol>
          </section>
        )}

        {profile.slug === '012' && (
          <section className="profile-special ai-principles">
            <div><p className="eyebrow light"><span /> FOUNDUPS · BEFORE ETHEREUM</p><h2>分散型組織を、<br />長く試してきた。</h2></div>
            <ol>
              <li><span>01 · 2010–2011</span><strong>O!F · Open Corps · Foundup$</strong><p>保存されたFoundUps資料には、crowdfunding・crowdsourcing・team-sourcingを一体化したOpen !ncubator Framework、Open Corps、仮想報酬Foundup$の構想が残る。</p></li>
              <li><span>02 · 2011–2012</span><strong>Mihai Alisieとの記録</strong><p>後のEthereum共同創設者Mihai Alisieと、Open Corporations、bottom-up型の組織・資金形成、BitcoinをOpen Startup !ncubatorで使う可能性についてSkypeで直接議論した記録が残る。</p></li>
              <li><span>03 · TRANSPARENCY</span><strong>交流の記録 ≠ Ethereumの発明</strong><p>Alisieは2014年、EthereumがTroutの仕事から生まれたという主張を明確に否定した。本サイトは、Ethereum以前の実質的な対話を記録するが、Ethereumの発明・著作者であるとは主張しない。</p></li>
            </ol>
          </section>
        )}

        {profile.slug === 'jorge-sabastian' && (
          <section className="profile-special">
            <div><p className="eyebrow light"><span /> FROM DEMAND TO INFRASTRUCTURE</p><h2>構想を、<br />設備仕様へ落とす。</h2></div>
            <ol>
              <li><span>01 · SIZE</span><strong>需要から初期容量を決める</strong><p>100kW、300kW、600kW、1MWなどを固定観念で選ばず、地域ワークロードと同時利用率から比較する。</p></li>
              <li><span>02 · ARCHITECTURE</span><strong>電力・通信・冗長性を設計条件へ</strong><p>GPUだけでなく、受電、ネットワーク、冷却、セキュリティ、保守、更新まで含めて成立条件を整理する。</p></li>
              <li><span>03 · FEASIBILITY</span><strong>成立しない条件も先に見つける</strong><p>AI交番は実証仮説。技術・価格・需要・工程に重大な障害があれば、それもフィージビリティの成果として明示する。</p></li>
            </ol>
          </section>
        )}

        {profile.slug === '0102' && (
          <section className="profile-special ai-principles">
            <div><p className="eyebrow light"><span /> HUMAN AUTHORITY · AI CAPABILITY</p><h2>速く考える。<br />勝手には決めない。</h2></div>
            <ol><li><span>01</span><strong>Evidence</strong><p>根拠、出典、仮説を分ける。</p></li><li><span>02</span><strong>Options</strong><p>一つの答えではなく、比較できる選択肢をつくる。</p></li><li><span>03</span><strong>Human decision</strong><p>地域、市、土地所有者、専門家が最終判断する。</p></li></ol>
          </section>
        )}

        {profile.slug === '0102' && (
          <section className="profile-music" aria-labelledby="music-title">
            <div className="music-cover">
              <Image src="/team/0102-music-cover.jpeg" alt="The Cry of Kuzuryu playlist cover showing rain over a bridge and papers illuminated on a table" fill sizes="(max-width: 760px) 100vw, 48vw" />
              <span>01 · PLAYLIST</span>
            </div>
            <div className="music-copy">
              <p className="eyebrow light"><span /> LISTEN TO KUZURYU</p>
              <h2 id="music-title">0102 MUSIC</h2>
              <strong>The Cry of Kuzuryu<br />— The Monk, the Boy, and the Spring</strong>
              <p>九頭竜の物語を、言葉だけでなく音からも感じるための音楽。0102の創作レイヤーです。</p>
              <div className="music-wave" aria-hidden="true">
                {[30, 62, 42, 86, 54, 100, 72, 44, 82, 58, 92, 48, 74, 36, 64, 28].map((height, index) => <i key={index} style={{ height: `${height}%` }} />)}
              </div>
              <a className="music-listen" href="https://suno.com/s/frgo9C2oirC5Zgfn" target="_blank" rel="noreferrer">Sunoでプレイリストを聴く <span>▶</span></a>
              <small>外部サイトSunoで開きます。自動再生はしません。</small>
            </div>
          </section>
        )}

        {profile.gallery.length > 0 && (
          <section className="profile-gallery"><div className="profile-gallery-heading"><span>FIELD NOTES</span><h2>一枚の顔から、<br />活動の背景へ。</h2></div><div className="profile-gallery-grid">{profile.gallery.map((item) => <figure key={item.src}><div><Image src={item.src} alt={item.alt} fill sizes="(max-width: 760px) 92vw, 45vw" style={{ objectPosition: item.position ?? '50% 50%' }} /></div><figcaption>{item.caption}</figcaption></figure>)}</div></section>
        )}

        {profile.links && <section className="profile-links"><span>VERIFIED PUBLIC LINKS</span>{profile.links.map((link) => <a href={link.href} key={link.href} target="_blank" rel="noreferrer">{link.label} <b>↗</b></a>)}</section>}

        <section className="profile-next"><span>BACK TO THE PEOPLE</span><h2>この一人から、<br />チーム全体を見る。</h2><Link className="button button-primary" href="/team">TEAM DIRECTORY <span>→</span></Link></section>
      </main>

      <footer><Brand href="/#top" /><p>PEOPLE × PLACE × COMPUTE × COMMUNITY</p><a href={LINE_URL} target="_blank" rel="noreferrer">LINEで参加 ↗</a></footer>
    </>
  );
}
