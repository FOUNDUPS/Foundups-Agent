import type { Metadata } from 'next';
import Link from 'next/link';
import { chatGPTSignInPath, chatGPTSignOutPath } from '@/app/chatgpt-auth';
import { MOSH_PATH } from '@/lib/mosh-pit-policy';
import { currentMoshPit } from '@/lib/mosh-pit-server';
import MoshPitFeed from '@/components/MoshPitFeed';
import './mosh-pit.css';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = {
  title: 'Mosh Pit · YUMORI.me', description: 'プロジェクト関係者の活動ログ。',
  robots: { index: false, follow: false },
  openGraph: { title: 'Mosh Pit · YUMORI.me', description: 'プロジェクト関係者の活動ログ。', images: [] },
  twitter: { card: 'summary', title: 'Mosh Pit · YUMORI.me', description: 'プロジェクト関係者の活動ログ。', images: [] },
};

export default async function MoshPitPage() {
  const result = await currentMoshPit();
  return <main className="mosh-page" lang="ja" data-yumori-localized>
    <header className="mosh-header"><Link href="/">YUMORI.me</Link><h1>Mosh Pit <span>活動ログ</span></h1>
      {result.status !== 'signed_out' && <a href={chatGPTSignOutPath(MOSH_PATH)} target="_top">ログアウト</a>}
    </header>
    {result.status === 'ready' ? <>
      <MoshPitFeed projection={result.projection} />
      <aside className="mosh-bottom"><p>活動を開くと、詳細と会話を確認できます。</p><p>現在は閲覧のみです。新しい活動・返信の投稿は準備中です。</p></aside>
    </> : <section className="mosh-gate" aria-live="polite">
      <h2>{result.status === 'signed_out' ? '関係者の活動ログへ' : result.status === 'not_approved' ? '参加承認が必要です' : '活動ログを準備しています'}</h2>
      <p>{result.status === 'signed_out' ? '承認された関係者が、日々の活動と会話を共有する場所です。' : result.status === 'not_approved' ? 'このアカウントは現在、このプロジェクトの閲覧を承認されていません。プロジェクト管理者に確認してください。' : '現在、活動ログを表示できません。時間をおいて再度お試しください。'}</p>
      {result.status === 'signed_out' ? <a className="mosh-button" href={chatGPTSignInPath(MOSH_PATH)} target="_top">ChatGPTでログイン</a> : <a className="mosh-button" href={MOSH_PATH}>再読み込み</a>}
    </section>}
  </main>;
}
