import Link from 'next/link';
import LanguageFlags from './LanguageFlags';
import Brand from './Brand';
import { projectData, type Locale } from '@/lib/project-data';
import { sharedCopy } from '@/lib/i18n';

export default function SiteHeader({ locale }: { locale: Locale }) {
  const copy = sharedCopy[locale];
  return (
    <header className="global-header">
      <Brand href={`/${locale}`} />
      <nav className="primary-nav" aria-label="Primary navigation">
        <Link href={`/${locale}`}>{copy.nav.save}</Link>
        <Link href={`/${locale}/future`}>{copy.nav.future}</Link>
        <Link href={`/${locale}/team`}>{copy.nav.team}</Link>
      </nav>
      <div className="header-actions">
        <LanguageFlags locale={locale} />
        <a className="header-line" href={projectData.line.url} target="_blank" rel="noreferrer">
          {copy.line.join}<span aria-hidden="true">↗</span>
        </a>
      </div>
    </header>
  );
}
