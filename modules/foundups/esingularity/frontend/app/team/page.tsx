import type { Metadata } from 'next';
import Link from 'next/link';
import Image from 'next/image';
import LineButton from '../../components/LineButton';
import Brand from '../../components/Brand';
import { publicTeamProfiles } from '../../lib/team';

const LINE_URL = 'https://line.me/ti/p/baXEozL_Q6';

export const metadata: Metadata = {
  title: 'Team & Network | eSingularity.ai',
  description: 'eSingularity.aiを立ち上げる012と0102。人とAIが協働して、温泉と福井の未来をつくるチームです。',
  openGraph: {
    title: 'Team & Network | eSingularity.ai',
    description: 'いまは二人から。012とAI共同開発者0102が、温泉と福井の未来をつくります。',
    url: 'https://esingularity.ai/team',
    images: [{ url: '/team/012-landowners-private.png', width: 1342, height: 1172, alt: 'eSingularity.ai team and community' }],
  },
};

export default function TeamPage() {
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
            <h1>いまは、<br /><em>二人から。</em></h1>
          </div>
          <div className="directory-intro">
            <p>人間の012と、AI共同開発者の0102。小さな創設チームが、地域の声と専門家をつなぎながら、この計画を育てています。</p>
            <div><span>LAUNCH TEAM</span><strong>確認できた役割だけを公開します。</strong></div>
          </div>
        </section>

        <section className="directory-group directory-core" id="core">
          <div className="directory-group-heading"><span>01</span><div><p>FOUNDING PAIR</p><h2>012 ↔ 0102</h2></div><p>人間の経験とAIの調査・翻訳・設計力を、一つの責任ある実行チームへ。</p></div>
          <div className="portrait-grid portrait-count-2">{publicTeamProfiles.map((profile) => <Link className="portrait-card" href={`/team/${profile.slug}`} key={profile.slug} aria-label={`${profile.name}のプロフィールを開く`}><div className="portrait-image"><Image src={profile.image} alt={profile.imageAlt} fill sizes="(max-width: 760px) 92vw, (max-width: 1100px) 46vw, 31vw" style={{ objectPosition: profile.imagePosition ?? '50% 50%' }} /><span className="portrait-index">{profile.slug}</span></div><div className="portrait-copy"><span>{profile.role}</span><h3>{profile.name}</h3><p>{profile.secondary}</p><b>PROFILE ↗</b></div></Link>)}</div>
        </section>

        <section className="directory-join"><span>THE DIRECTORY GROWS WITH PERMISSION</span><h2>あなたも、<br />このチームの一人になる。</h2><div><Link className="button button-primary" href="/#join">名前を加える <span>→</span></Link><a className="button button-ghost" href={LINE_URL} target="_blank" rel="noreferrer">LINEで参加 <span>↗</span></a></div></section>
      </main>

      <footer><Brand href="/#top" /><p>PEOPLE × PLACE × COMPUTE × COMMUNITY</p><a href={LINE_URL} target="_blank" rel="noreferrer">LINEで参加 ↗</a></footer>
    </>
  );
}
