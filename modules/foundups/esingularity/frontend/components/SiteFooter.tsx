import Brand from './Brand';
import { projectData, type Locale } from '@/lib/project-data';
import { sharedCopy } from '@/lib/i18n';

export default function SiteFooter({ locale }: { locale: Locale }) {
  const copy = sharedCopy[locale];
  return (
    <footer className="global-footer">
      <Brand href={`/${locale}`} />
      <p>{copy.footer.summary}</p>
      <a href={projectData.line.url} target="_blank" rel="noreferrer">{copy.line.join} ↗</a>
    </footer>
  );
}
