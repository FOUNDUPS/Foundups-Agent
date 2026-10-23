'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { locales, type Locale } from '@/lib/project-data';
import { pathForLocale, sharedCopy } from '@/lib/i18n';

const flags: Record<Locale, string> = { ja: '🇯🇵', en: '🇬🇧', pt: '🇧🇷' };

export default function LanguageFlags({ locale }: { locale: Locale }) {
  const pathname = usePathname();

  useEffect(() => {
    window.localStorage.setItem('esingularity-language', locale);
  }, [locale]);

  return (
    <nav className="locale-flags" aria-label="Language selection">
      {locales.map((option) => (
        <Link
          key={option}
          href={pathForLocale(pathname, option)}
          hrefLang={option === 'pt' ? 'pt-BR' : option}
          lang={option === 'pt' ? 'pt-BR' : option}
          aria-label={sharedCopy[option].languageName}
          aria-current={option === locale ? 'page' : undefined}
          title={sharedCopy[option].languageName}
        >
          <span aria-hidden="true">{flags[option]}</span>
        </Link>
      ))}
    </nav>
  );
}
