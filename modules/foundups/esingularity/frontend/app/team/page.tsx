import type { Metadata } from 'next';
import Link from 'next/link';
import Image from 'next/image';
import LineButton from '../../components/LineButton';
import Brand from '../../components/Brand';
import { publicTeamProfiles, type TeamProfile } from '../../lib/team';

const LINE_URL = 'https://line.me/ti/p/baXEozL_Q6';

export const metadata: Metadata = {
  title: 'Team & Network | eSingularity.ai',
  description: 'eSingularity.aiを立ち上げる012と0102、そしてAI交番の成立性を検証する専門家ネットワーク。',
  openGraph: {
    title: 'Team & Network | eSingularity.ai',
    description: '012と0102を中心に、地域・技術・資本をつなぐ実行チームを形成しています。',
    url: 'https://esingularity.ai/team',
    images: [{ url: '/team/012-landowners-private.png', width: 1342, height: 1172, alt: 'eSingularity.ai team and community' }],
  },
};

function ProfileCard({ profile }: { profile: TeamProfile }) {
  return (
    <Link className="portrait-card" href={`/team/${profile.slug}`} aria-label={`${profile.name}のプロフィールを開く`}>
      <div className="portrait-image">
        {profile.image ? (
          <Image src={profile.image} alt={profile.imageAlt ?? profile.name} fill sizes="(max-width: 760px) 92vw, (max-width: 1100px) 46vw, 31vw" style={{ objectPosition: profile.imagePosition ?? '50% 50%' }} />
        ) : (
          <div
            aria-hidden="true"
            style={{
              position: 'absolute',
              inset: 0,
              display: 'grid',
              placeItems: 'center',
              padding: '24px',
              textAlign: 'center',
              background: 'radial-gradient(circle at 50% 30%, #164d9b 0, #071b37 45%, #020813 100%)',
              color: 'var(--white)',
              fontFamily: 'var(--font-mono), monospace',
              fontSize: 'clamp(18px, 2.4vw, 30px)',
              lineHeight: 1.1,
            }}
          >
            AI KOBAN<br />TECHNICAL ADVISOR
          </div>
        )}
        <span className="portrait-index">{profile.slug === '012' || profile.slug === '0102' ? profile.slug : 'eS'}</span>
      </div>
      <div className="portrait-copy"><span>{profile.role}</span><h3>{profile.name}</h3><p>{profile.secondary}</p><b>PROFILE ↗</b></div>
    </Link>
  );
}

export default function TeamPage() {
  const coreProfiles = publicTeamProfiles.filter((profile) => profile.group === 'core');
  const collaborators = publicTeamProfiles.filter((profile) => profile.group === 'collaborators');

  return (
    <>
      <header className="site-header team-site-header">
        <Brand href="/#top" />
        <nav aria-label="Primary navigation"><Link href="/">温泉を守る</Link><Link href="/#innovation-hub">AI拠点</Link><Link href="/future">福井の未来</Link><Link href="/team" aria-current="page">チーム</Link></nav>
        <LineButton />
      </header>

      <main className="directory-page">
        <section className="directory-hero">
          <div>
            <p className="eyebrow light"><span /> PEOPLE BEFORE ORGANIZATION</p>
            <h1>始まりは、<br /><em>012 ↔ 0102。</em></h1>
          </div>
          <div className="directory-intro">
            <p>人間の012とAI共同開発者0102を起点に、地域の声、地権者、技術、金融、法務を、確認できた役割から一つの実行チームへつないでいます。</p>
            <div><span>BUILD IN PUBLIC</span><strong>関係・役割・確約のレベルを分けて公開します。</strong></div>
          </div>
        </section>

        <section className="directory-group directory-core" id="core">
          <div className="directory-group-heading"><span>01</span><div><p>FOUNDING PAIR</p><h2>012 ↔ 0102</h2></div><p>人間の経験とAIの調査・翻訳・設計力を、一つの責任ある実行チームへ。</p></div>
          <div className="portrait-grid portrait-count-2">{coreProfiles.map((profile) => <ProfileCard profile={profile} key={profile.slug} />)}</div>
        </section>

        {collaborators.length > 0 && (
          <section className="directory-group" id="collaborators">
            <div className="directory-group-heading"><span>02</span><div><p>TECHNICAL COLLABORATORS</p><h2>専門性をつなぐ。</h2></div><p>AI交番を構想で終わらせないため、設備・電力・通信・金融・法務などの専門性を案件形成へ接続します。</p></div>
            <div className={`portrait-grid portrait-count-${Math.min(collaborators.length, 3)}`}>{collaborators.map((profile) => <ProfileCard profile={profile} key={profile.slug} />)}</div>
          </section>
        )}

        <section className="directory-join"><span>THE DIRECTORY GROWS WITH PERMISSION</span><h2>役割が確認できた人から、<br />チームに加える。</h2><div><Link className="button button-primary" href="/#join">参加する <span>→</span></Link><a className="button button-ghost" href={LINE_URL} target="_blank" rel="noreferrer">LINEで参加 <span>↗</span></a></div></section>
      </main>

      <footer><Brand href="/#top" /><p>PEOPLE × PLACE × COMPUTE × COMMUNITY</p><a href={LINE_URL} target="_blank" rel="noreferrer">LINEで参加 ↗</a></footer>
    </>
  );
}
