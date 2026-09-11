'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { YumoriLocale } from '../content/yumori-presentation';
import { getYumoriVisionSlides, visionUi } from '../content/yumori-vision';
import styles from './YumoriPresentation.module.css';

const AUTOPLAY_MS = 9000;
const SPRITE_URL = '/vision/vision-sprite.jpg';

export default function YumoriPresentation() {
  const [locale, setLocale] = useState<YumoriLocale>('ja');
  const [active, setActive] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [fullscreen, setFullscreen] = useState(false);
  const pointerStart = useRef<number | null>(null);
  const slides = useMemo(() => getYumoriVisionSlides(locale), [locale]);
  const slide = slides[active];
  const ui = visionUi[locale];

  const move = useCallback((delta: number) => {
    setPlaying(false);
    setActive((current) => (current + delta + slides.length) % slides.length);
  }, [slides.length]);

  const select = useCallback((index: number) => {
    setPlaying(false);
    setActive(index);
  }, []);

  useEffect(() => {
    const readLocale = () => {
      const lang = document.documentElement.lang.toLowerCase();
      setLocale(lang.startsWith('pt') ? 'pt' : lang.startsWith('en') ? 'en' : 'ja');
    };
    readLocale();
    const observer = new MutationObserver(readLocale);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const url = new URL(window.location.href);
    const requested = Number(url.searchParams.get('slide'));
    if (Number.isInteger(requested) && requested >= 1 && requested <= slides.length) setActive(requested - 1);
    if (url.searchParams.get('vision') === '1') setFullscreen(true);
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) setPlaying(false);
  }, [slides.length]);

  useEffect(() => {
    if (!fullscreen) return;
    const url = new URL(window.location.href);
    url.searchParams.set('vision', '1');
    url.searchParams.set('slide', String(active + 1));
    url.hash = 'yumori-deck';
    window.history.replaceState({}, '', url);
  }, [active, fullscreen]);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setTimeout(() => setActive((current) => (current + 1) % slides.length), AUTOPLAY_MS);
    return () => window.clearTimeout(timer);
  }, [active, playing, slides.length]);

  useEffect(() => {
    document.body.style.overflow = fullscreen ? 'hidden' : '';
    if (!fullscreen) return () => { document.body.style.overflow = ''; };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'ArrowLeft') move(-1);
      if (event.key === 'ArrowRight') move(1);
      if (event.key === 'Escape') setFullscreen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [fullscreen, move]);

  function closeFullscreen() {
    setFullscreen(false);
    const url = new URL(window.location.href);
    url.searchParams.delete('vision');
    url.searchParams.delete('slide');
    url.hash = 'yumori-deck';
    window.history.replaceState({}, '', url);
  }

  const spriteStyle = {
    backgroundImage: `url(${SPRITE_URL})`,
    backgroundPosition: `center ${(active / (slides.length - 1)) * 100}%`,
  };

  return (
    <section
      className={`${styles.deck} ${fullscreen ? styles.fullscreen : ''}`}
      id="yumori-deck"
      data-yumori-localized
      aria-labelledby="yumori-deck-title"
      onPointerDown={(event) => { pointerStart.current = event.clientX; }}
      onPointerUp={(event) => {
        if (pointerStart.current === null) return;
        const distance = event.clientX - pointerStart.current;
        pointerStart.current = null;
        if (Math.abs(distance) > 55) move(distance > 0 ? -1 : 1);
      }}
    >
      <div className={styles.heading}>
        <div>
          <p>{ui.label}</p>
          <h2 id="yumori-deck-title">{ui.title}</h2>
        </div>
        <div className={styles.headingActions}>
          <a className={styles.controlLink} href="/reports/jhr">{ui.jhr} ↗</a>
          <a className={styles.controlLink} href="https://yumori.me">{ui.join} ↗</a>
          <button className={styles.fullscreenButton} type="button" onClick={() => fullscreen ? closeFullscreen() : setFullscreen(true)}>{fullscreen ? ui.exit : ui.fullscreen}</button>
        </div>
      </div>

      <div className={styles.stage} aria-label={`${active + 1} / ${slides.length}: ${slide.title}`}>
        <div className={styles.sprite} style={spriteStyle} role="img" aria-label={slide.alt} />
        <span className={styles.slideCounter}>{String(active + 1).padStart(2, '0')} / {String(slides.length).padStart(2, '0')}</span>
        <div className={styles.nav}>
          <button type="button" onClick={() => move(-1)} aria-label={ui.previous}>←</button>
          <button type="button" onClick={() => move(1)} aria-label={ui.next}>→</button>
        </div>
      </div>

      <div className={styles.controls}>
        <button className={`${styles.iconButton} ${styles.play}`} type="button" onClick={() => setPlaying((current) => !current)}>{playing ? `Ⅱ ${ui.pause}` : `▶ ${ui.play}`}</button>
        <div className={styles.dots} role="group" aria-label="slide navigation">
          {slides.map((item, index) => (
            <button key={item.id} className={index === active ? styles.active : ''} type="button" aria-label={`${index + 1}: ${item.title}`} aria-current={index === active ? 'step' : undefined} onClick={() => select(index)} />
          ))}
        </div>
        <span className={styles.screenReader} aria-live="polite">{slide.title}. {slide.summary}</span>
      </div>

      <div className={styles.meta}>
        <details className="yumori-slide-details" onToggle={(event) => { if (event.currentTarget.open) setPlaying(false); }}>
          <summary>{ui.details}</summary>
          <div className={styles.metaBody}>
            <h3>{slide.title}</h3>
            <p>{slide.summary}</p>
            <ul>{slide.evidence.map((item) => <li key={item}>{item}</li>)}</ul>
            <a href={slide.link.href} target={slide.link.href.startsWith('http') ? '_blank' : undefined} rel={slide.link.href.startsWith('http') ? 'noreferrer' : undefined}>{slide.link.label} ↗</a>
          </div>
        </details>
      </div>
    </section>
  );
}
