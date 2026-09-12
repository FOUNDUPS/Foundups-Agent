import Link from 'next/link';
import Brand from '../../components/Brand';
import FinanceDashboard from '../../components/FinanceDashboard';
import LineButton from '../../components/LineButton';

const LINE_URL = 'https://line.me/ti/p/baXEozL_Q6';

export default function FinancePage() {
  return (
    <>
      <header className="site-header team-site-header">
        <Brand href="/" />
        <nav aria-label="Primary navigation">
          <Link href="/">温泉を守る</Link>
          <Link href="/#innovation-hub">AI拠点</Link>
          <Link href="/future">福井の未来</Link>
          <Link href="/finance" aria-current="page">FIN.YUMORI</Link>
          <Link href="/team">チーム</Link>
        </nav>
        <LineButton />
      </header>

      <FinanceDashboard />

      <footer>
        <Brand href="/" />
        <p>FIN.YUMORI · REPO-OWNED PYTHON MODEL · EVIDENCE FIRST</p>
        <a href={LINE_URL} target="_blank" rel="noreferrer">LINEで参加 ↗</a>
      </footer>
    </>
  );
}
