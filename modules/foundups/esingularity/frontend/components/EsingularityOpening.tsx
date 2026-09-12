'use client';

import Image from 'next/image';
import { useEffect, useState } from 'react';
import FukuiComparisonMap from './FukuiComparisonMap';
import { OPENING_IMAGE, OPENING_SIGNUP_URL, openingCopy } from '../content/esingularity-opening';
import styles from './EsingularityOpening.module.css';

export default function EsingularityOpening() {
  const [locale, setLocale] = useState<'ja' | 'en' | 'pt'>('ja');
  useEffect(() => {
    const update = () => {
      const lang = document.documentElement.lang;
      setLocale(lang.startsWith('pt') ? 'pt' : lang.startsWith('en') ? 'en' : 'ja');
    };
    update();
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
    return () => observer.disconnect();
  }, []);
  const copy = openingCopy[locale];
  return <section className={styles.opening} id="hero" aria-labelledby="hero-title">
    <div data-yumori-localized lang={locale === 'pt' ? 'pt-BR' : locale}>
      <p className={styles.label}>{copy.label}</p>
      <h1 id="hero-title">{copy.title}</h1>
      <figure className={styles.visual}>
        <a href="?vision=1&slide=1#yumori-deck" aria-label={copy.fullscreen}>
          <Image src={OPENING_IMAGE} alt={copy.alt} width={1672} height={941} sizes="(max-width: 800px) 100vw, 92vw" priority />
          <span className={styles.fullscreen}>{copy.fullscreen} ⛶</span>
          <span className={styles.left}>{copy.left}</span><span className={styles.right}>{copy.right}</span>
        </a>
        <figcaption>{copy.note} {copy.costNote} <a href="https://www.city.fukui.lg.jp/sisei/gikai/shitsumon/p004052_d/fil/0806a.pdf">{copy.source} ↗</a></figcaption>
      </figure>
      <div className={styles.message}>
        <div><p className={styles.body}>{copy.body}</p><p className={styles.mission}>{copy.mission}</p></div>
        <div className={styles.action}><a href={OPENING_SIGNUP_URL}>{copy.join} ↗</a><p>{copy.vote}</p></div>
      </div>
    </div>
    <details className={styles.research}>
      <summary data-yumori-localized>{copy.map}</summary>
      <FukuiComparisonMap />
    </details>
  </section>;
}
