'use client';

import Image from 'next/image';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getYumoriVisionSlides, visionUi, type YumoriLocale } from '../content/yumori-vision';
import styles from './YumoriPresentation.module.css';

const AUTOPLAY_MS = 9000;
const SWIPE_DISTANCE = 55;

export default function YumoriPresentation() {
  const [locale, setLocale] = useState<YumoriLocale>('ja');
  const [active, setActive] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [fullscreen, setFullscreen] = useState(false);
  const [inView, setInView] = useState(false);
  const [pageVisible, setPageVisible] = useState(true);
  const pointerStart = useRef<{ x: number; y: number } | null>(null);
  const deckRef = useRef<HTMLElement>(null);
  const fullscreenButtonRef = useRef<HTMLButtonElement>(null);
  const returnFocus = useRef(false);
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

  const closeFullscreen = useCallback(() => {
    setFullscreen(false);
    const url = new URL(window.location.href);
    url.searchParams.delete('vision');
    url.searchParams.delete('slide');
    url.hash = 'yumori-deck';
    window.history.replaceState({}, '', url);
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
    const node = deckRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), { threshold: 0.2 });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const onVisibilityChange = () => setPageVisible(document.visibilityState === 'visible');
    onVisibilityChange();
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => document.removeEventListener('visibilitychange', onVisibilityChange);
  }, []);

  useEffect(() => {
    if (!fullscreen) return;
    const url = new URL(window.location.href);
    url.searchParams.set('vision', '1');
    url.searchParams.set('slide', String(active + 1));
    url.hash = 'yumori-deck';
    window.history.replaceState({}, '', url);
  }, [active, fullscreen]);

  useEffect(() => {
    if (!playing || (!fullscreen && !inView) || !pageVisible) return;
    const timer = window.setTimeout(() => setActive((current) => (current + 1) % slides.length), AUTOPLAY_MS);
    return () => window.clearTimeout(timer);
  }, [active, fullscreen, inView, pageVisible, playing, slides.length]);

  useEffect(() => {
    if (!fullscreen) {
      if (returnFocus.current) {
        returnFocus.current = false;
        window.requestAnimationFrame(() => fullscreenButtonRef.current?.focus());
      }
      return;
    }

    returnFocus.current = true;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.requestAnimationFrame(() => deckRef.current?.focus());

    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'ArrowLeft') move(-1);
      if (event.key === 'ArrowRight') move(1);
      if (event.key === 'Escape') closeFullscreen();
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [closeFullscreen, fullscreen, move]);

  return (
    <section
      ref={deckRef}
      className={`${styles.deck} ${fullscreen ? styles.fullscreen : ''}`}
      id="yumori-deck"
      data-yumori-localized
      aria-labelledby="yumori-deck-title"
      role={fullscreen ? 'dialog' : undefined}
      aria-modal={fullscreen ? true : undefined}
      tabIndex={fullscreen ? -1 : undefined}
    >
      <div className={styles.heading}>
        <div>
          <p>{ui.label}</p>
          <h2 id="yumori-deck-title">{ui.title}</h2>
        </div>
        <div className={styles.headingActions}>
          <a className={styles.controlLink} href="https://yumori.me">{ui.join} ↗</a>
          <button ref={fullscreenButtonRef} className={styles.fullscreenButton} type="button" onClick={() => fullscreen ? closeFullscreen() : setFullscreen(true)}>{fullscreen ? ui.exit : ui.fullscreen}</button>
        </div>
      </div>

      <div
        className={styles.stage}
        aria-label={`${active + 1} / ${slides.length}: ${slide.title}`}
        onPointerDown={(event) => {
          if (event.pointerType === 'mouse' && event.button !== 0) return;
          pointerStart.current = { x: event.clientX, y: event.clientY };
        }}
        onPointerUp={(event) => {
          if (!pointerStart.current) return;
          const distanceX = event.clientX - pointerStart.current.x;
          const distanceY = event.clientY - pointerStart.current.y;
          pointerStart.current = null;
          if (Math.abs(distanceX) > SWIPE_DISTANCE && Math.abs(distanceX) > Math.abs(distanceY) * 1.2) move(distanceX > 0 ? -1 : 1);
        }}
        onPointerCancel={() => { pointerStart.current = null; }}
      >
        <Image className={styles.slideImage} src={slide.image} alt={slide.alt} fill sizes="100vw" draggable={false} />
        <div className={styles.imageScrim} aria-hidden="true" />
        <div className={styles.stageCopy}>
          <span>{String(active + 1).padStart(2, '0')} / {String(slides.length).padStart(2, '0')}</span>
          <h3>{slide.title}</h3>
          <p>{slide.summary}</p>
        </div>
        <a className={styles.stageAction} href="https://yumori.me">
          <span>YUMORI</span><strong>{slide.action}</strong><b aria-hidden="true">↗</b>
        </a>
        <div className={styles.nav}>
          <button type="button" onClick={() => move(-1)} aria-label={ui.previous}>←</button>
          <button type="button" onClick={() => move(1)} aria-label={ui.next}>→</button>
        </div>
      </div>

      <div className={styles.controls}>
        <button className={`${styles.iconButton} ${styles.play}`} type="button" onClick={() => setPlaying((current) => !current)}>{playing ? `Ⅱ ${ui.pause}` : `▶ ${ui.play}`}</button>
        <div className={styles.dots} role="group" aria-label={ui.navigation}>
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
