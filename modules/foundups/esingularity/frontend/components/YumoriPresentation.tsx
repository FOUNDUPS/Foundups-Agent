'use client';

import Image from 'next/image';
import { useEffect, useRef, useState } from 'react';
import { yumoriPresentation, type YumoriLocale, type YumoriSlide } from '../content/yumori-presentation';

const AUTOPLAY_MS = 9000;

const outreach = [
  { name: '廣瀬 勝一 / 樋口 健', institution: '福井大学 データ科学・AI教育研究センター', fit: { ja: '地域AI教育、データベース、産学連携', en: 'Regional AI education, databases, industry–university collaboration', pt: 'Educação regional em IA, bancos de dados e colaboração universidade–indústria' }, href: 'https://www.dsai.u-fukui.ac.jp/system/' },
  { name: '高橋 泰岳 / 築地原 里樹', institution: '福井大学 インタラクティブ・ロボティクス研究室', fit: { ja: 'ロボット学習、人と環境に共存する自律システム', en: 'Robot learning and autonomous systems that coexist with people and environments', pt: 'Aprendizagem robótica e sistemas autônomos que coexistem com pessoas e ambientes' }, href: 'https://www.eng.u-fukui.ac.jp/graduate_school/knowledge_society/his/research/index.html' },
  { name: '長谷川 達人', institution: '福井大学 Hasegawa Lab', fit: { ja: '機械学習、深層学習、センシング、エッジ応用', en: 'Machine learning, deep learning, sensing, and edge applications', pt: 'Aprendizado de máquina, aprendizado profundo, sensoriamento e aplicações de borda' }, href: 'https://haselab.fuis.u-fukui.ac.jp/' },
  { name: '岩野 優樹', institution: '福井工業大学 FUT未来ロボティクスセンター', fit: { ja: '農業支援ロボット、草刈り・除草、地域実装', en: 'Agricultural support robots, mowing, weeding, and regional deployment', pt: 'Robôs de apoio agrícola, corte, capina e implantação regional' }, href: 'https://www.fukui-ut.ac.jp/robotics/' },
  { name: '村田 知也', institution: '福井県立大学 情報センター', fit: { ja: 'AI・IoT・PBL、次世代農業の環境制御', en: 'AI, IoT, project-based learning, and next-generation farm control', pt: 'IA, IoT, aprendizagem por projetos e controle agrícola de nova geração' }, href: 'https://www.fpu.ac.jp/faculty_members/d000000f.html' },
] as const;

const outreachLabels = {
  ja: { title: '福井のAI・ロボティクス連携候補', note: '公開情報に基づく未連絡の候補です。参加・支持を示すものではありません。' },
  en: { title: 'Fukui AI and robotics outreach candidates', note: 'Uncontacted candidates identified from public sources. Listing does not imply participation or support.' },
  pt: { title: 'Candidatos de IA e robótica em Fukui', note: 'Candidatos ainda não contatados, identificados em fontes públicas. A lista não implica participação nem apoio.' },
} as const;

const visualLabels = {
  ja: { flow: '電力からCOG DC、コンピュートと熱、地域へつながる流れ', floors: '旧施設のFoundUp育成階層と別棟COG DCの構想', top: '実用性・実行力・価値を検証', third: '小さなプロジェクトスタジオ', lower: '教育・展示・ロボティクス・イベント', japan: '福井から他地域へ検証可能性が広がる概念図' },
  en: { flow: 'Flow from energy through COG DC to compute, recoverable heat, and community', floors: 'FoundUp development floors in the retained building with a separate COG DC', top: 'Validated usefulness, execution, and value', third: 'Small project studios', lower: 'Education, exhibits, robotics, and events', japan: 'Concept map showing possible validation beyond Fukui' },
  pt: { flow: 'Fluxo de energia pelo COG DC até computação, calor recuperável e comunidade', floors: 'Andares de desenvolvimento FoundUp no edifício preservado com COG DC separado', top: 'Utilidade, execução e valor validados', third: 'Pequenos estúdios de projeto', lower: 'Educação, exposições, robótica e eventos', japan: 'Mapa conceitual da possível validação além de Fukui' },
} as const;

function SlideVisual({ slide, priority, locale }: { slide: YumoriSlide; priority: boolean; locale: YumoriLocale }) {
  const labels = visualLabels[locale];
  if (slide.visual === 'cogdc') {
    return (
      <div className="yumori-flow-visual" aria-label={labels.flow}>
        <span>ENERGY</span><b>↓</b><strong>COG DC<small>COMMUNITY-OWNED GREEN DATA CENTER</small></strong><b>↓</b><span>COMPUTE + HEAT</span><b>↓</b><span>COMMUNITY</span>
      </div>
    );
  }

  if (slide.visual === 'floors') {
    return (
      <div className="yumori-floor-visual" aria-label={labels.floors}>
        <div className="yumori-building-stack">
          <span><small>TOP FLOOR</small><strong>ADVANCED FOUNDUPS</strong><em>{labels.top}</em></span>
          <span><small>THIRD FLOOR</small><strong>STUDENTS + EMERGING FOUNDUPS</strong><em>{labels.third}</em></span>
          <span><small>LOWER / PUBLIC</small><strong>ONSEN + COMMUNITY</strong><em>{labels.lower}</em></span>
        </div>
        <div className="yumori-cogdc-block"><small>SEPARATE INFRASTRUCTURE</small><strong>OUR COG DC</strong><span>COMPUTE ↗</span></div>
      </div>
    );
  }

  if (slide.visual === 'japan') {
    return (
      <div className="yumori-japan-visual" aria-label={labels.japan}>
        <div className="yumori-islands" aria-hidden="true">{Array.from({ length: 18 }, (_, index) => <i key={index} />)}</div>
        <span className="yumori-fukui-light">FUKUI<strong>PROTOTYPE</strong></span>
        <span className="yumori-network-question">SCHOOLS · CIVIC ASSETS · ONSENS<br /><strong>?</strong></span>
      </div>
    );
  }

  return (
    <div className={`yumori-image-visual yumori-image-${slide.visual}`}>
      {slide.image && <Image src={slide.image} alt={slide.alt ?? ''} fill priority={priority} sizes="(max-width: 760px) 100vw, 56vw" />}
      <div className="yumori-image-scrim" aria-hidden="true" />
      {slide.visual === 'economics' && <div className="yumori-value-tags"><span>VERIFIED</span><span>REPORTED</span><span>MODELLED</span></div>}
      {slide.visual === 'ecosystem' && <div className="yumori-ecosystem-tags"><span>ONSEN</span><span>COG DC</span><span>FOUNDUPS</span><span>STUDENTS</span><span>FARMS</span><span>EVENTS</span></div>}
      {slide.visual === 'agriculture' && <div className="yumori-field-loop">LOCAL PROBLEM → PROTOTYPE → FIELD TEST → COMPANY</div>}
      {slide.visual === 'festival' && <span className="yumori-proposal-stamp">PROPOSED CULTURAL EXPERIENCE</span>}
    </div>
  );
}

export default function YumoriPresentation() {
  const [locale, setLocale] = useState<YumoriLocale>('ja');
  const [active, setActive] = useState(0);
  const [playing, setPlaying] = useState(true);
  const pointerStart = useRef<number | null>(null);
  const copy = yumoriPresentation[locale];
  const outreachLabel = outreachLabels[locale];
  const slide = copy.slides[active];

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
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      window.setTimeout(() => setPlaying(false), 0);
    }
  }, []);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setTimeout(() => setActive((current) => (current + 1) % copy.slides.length), AUTOPLAY_MS);
    return () => window.clearTimeout(timer);
  }, [active, playing, copy.slides.length]);

  function move(delta: number) {
    setPlaying(false);
    setActive((current) => (current + delta + copy.slides.length) % copy.slides.length);
  }

  function select(index: number) {
    setPlaying(false);
    setActive(index);
  }

  return (
    <section className="yumori-deck" id="yumori-deck" data-yumori-localized aria-labelledby="yumori-deck-title" onFocusCapture={() => setPlaying(false)} onWheel={() => setPlaying(false)} onPointerDown={(event) => { setPlaying(false); pointerStart.current = event.clientX; }} onPointerUp={(event) => { if (pointerStart.current === null) return; const distance = event.clientX - pointerStart.current; pointerStart.current = null; if (Math.abs(distance) > 55) move(distance > 0 ? -1 : 1); }}>
      <div className="yumori-deck-heading">
        <p>{copy.label}</p>
        <h2 id="yumori-deck-title">{copy.title}</h2>
      </div>

      <article key={slide.id} className={`yumori-slide yumori-slide-${slide.visual}`} aria-label={`${copy.controls.slide} ${active + 1} / ${copy.slides.length}`}>
        <SlideVisual slide={slide} priority={active === 0} locale={locale} />
        <div className="yumori-slide-copy">
          <div className="yumori-slide-index"><span>{slide.kicker}</span><b>{String(active + 1).padStart(2, '0')} / {String(copy.slides.length).padStart(2, '0')}</b></div>
          <h3 aria-live="polite">{slide.proposition}</h3>
          {slide.number && <div className="yumori-slide-number"><strong>{slide.number}</strong>{slide.numberLabel && <span>{slide.numberLabel}</span>}</div>}
          <details className="yumori-slide-details" onToggle={(event) => { if (event.currentTarget.open) setPlaying(false); }}>
            <summary>{copy.controls.details}<span aria-hidden="true">＋</span></summary>
            <div>
              <p>{slide.explanation}</p>
              <ul>{slide.evidence.map((item) => <li key={item}>{item}</li>)}</ul>
              <a href={slide.link.href} target={slide.link.href.startsWith('http') ? '_blank' : undefined} rel={slide.link.href.startsWith('http') ? 'noreferrer' : undefined}>{slide.link.label}<span aria-hidden="true">↗</span></a>
            </div>
          </details>
        </div>
      </article>

      <div className="yumori-deck-controls">
        <button type="button" onClick={() => move(-1)} aria-label={copy.controls.previous}><span aria-hidden="true">←</span>{copy.controls.previous}</button>
        <div className="yumori-deck-dots" role="group" aria-label={`${copy.controls.slide} navigation`}>
          {copy.slides.map((item, index) => <button key={item.id} type="button" className={index === active ? 'active' : ''} aria-label={`${copy.controls.slide} ${index + 1}`} aria-current={index === active ? 'step' : undefined} onClick={() => select(index)}><span>{String(index + 1).padStart(2, '0')}</span></button>)}
        </div>
        <button type="button" onClick={() => move(1)}>{copy.controls.next}<span aria-hidden="true">→</span></button>
        <button className="yumori-play" type="button" onClick={() => setPlaying((current) => !current)} aria-label={playing ? copy.controls.pause : copy.controls.play}>{playing ? 'Ⅱ' : '▶'}<span>{playing ? copy.controls.pause : copy.controls.play}</span></button>
      </div>

      <aside className="yumori-outreach" id="yumori-outreach" aria-labelledby="yumori-outreach-title">
        <div><p>07 · RESEARCH OUTREACH</p><h3 id="yumori-outreach-title">{outreachLabel.title}</h3><span>{outreachLabel.note}</span></div>
        <ol>{outreach.map((candidate) => <li key={candidate.name}><a href={candidate.href} target="_blank" rel="noreferrer"><strong>{candidate.name}</strong><span>{candidate.institution}</span><small>{candidate.fit[locale]} ↗</small></a></li>)}</ol>
      </aside>
    </section>
  );
}
