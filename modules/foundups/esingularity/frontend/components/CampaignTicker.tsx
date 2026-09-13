'use client';

import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { currentFieldStatus } from '../content/current-field-status';

const actions = [
  { label: 'VOTE NO', text: currentFieldStatus.tickerJa, href: currentFieldStatus.href },
  { label: '市議会', text: '設立準備委員会から福井市議会へのメッセージを読む', href: 'https://yumori.me/vote-no#council' },
  { label: '市長', text: '設立準備委員会から福井市長へのメッセージを読む', href: 'https://yumori.me/vote-no#mayor' },
  { label: '声を届ける', text: '福井市議会・福井市へ連絡する', href: 'https://yumori.me/vote-no#contact' },
  { label: 'JHR', text: 'UPDATE 9/10｜仙台200MW・印西の地区計画・福井の選択肢', href: '/reports/jhr' },
  { label: 'NEW', text: 'YUMORI / COG DC 10枚のプレゼンを見る', href: '#yumori-deck' },
  { label: 'VISIT', text: '写真で現地を見る', href: 'https://pics.yumori.info' },
  { label: 'LISTEN', text: '九頭竜の音楽を聴く', href: 'https://music.yumori.me' },
  { label: 'LEARN', text: '再生計画を読む', href: 'https://pc.yumori.info' },
  { label: 'EXPLORE', text: 'YUMORI.infoでプロジェクトを見る', href: 'https://yumori.info' },
  { label: 'JOIN', text: '温泉を守る準備委員会に名前を加える', href: 'https://docs.google.com/forms/d/e/1FAIpQLScSKFyzCym8NCarvNIa5cT9c2Pe8C-cY2AbC4zLgsDOKspYKA/viewform' },
] as const;

function ActionSet({ duplicate = false, movement = false }: { duplicate?: boolean; movement?: boolean }) {
  return (
    <div className="campaign-ticker-set" aria-hidden={duplicate || undefined}>
      {actions.map((action) => {
        const href = movement && action.href.startsWith('#') ? `https://esingularity.ai/${action.href}` : action.href;
        const external = href.startsWith('http');
        return (
          <a key={action.label} href={href} target={external ? '_blank' : undefined} rel={external ? 'noreferrer' : undefined} tabIndex={duplicate ? -1 : undefined}>
            <strong>{action.label}</strong><span>{action.text}</span>
          </a>
        );
      })}
      <a href={movement ? 'https://esingularity.ai/#act-now' : '#act-now'} tabIndex={duplicate ? -1 : undefined}><strong>SAVE THE DRAGON</strong><span>九頭竜を守れ。温泉を守れ。</span></a>
    </div>
  );
}

export default function CampaignTicker({ movement = false }: { movement?: boolean }) {
  const [reading, setReading] = useState(false);
  const tickerRef = useRef<HTMLElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const ticker = tickerRef.current;
    const track = trackRef.current;
    if (!ticker || !track) return;
    const update = () => {
      if (ticker.dataset.reading === 'true') return;
      const width = ticker.getBoundingClientRect().width;
      const pixelsPerSecond = width <= 600 ? 10 : width <= 1200 ? 20 : 32;
      const distance = track.scrollWidth / 2;
      ticker.style.setProperty('--ticker-duration', `${Math.max(48, distance / pixelsPerSecond)}s`);
    };
    const observer = new ResizeObserver(update);
    observer.observe(ticker);
    observer.observe(track);
    document.fonts.ready.then(update);
    update();
    return () => observer.disconnect();
  }, []);
  return (
    <aside ref={tickerRef} data-reading={reading} style={{ '--ticker-duration': '300s' } as CSSProperties} className={movement ? 'campaign-ticker campaign-ticker-inline' : 'campaign-ticker'} aria-label="九頭竜を守るための行動メニュー">
      <button className="campaign-ticker-control" type="button" aria-pressed={reading} onClick={() => setReading(!reading)}>{reading ? '再開' : '停止して読む'}</button>
      <div className="campaign-ticker-window">
      <div ref={trackRef} className="campaign-ticker-track">
        <ActionSet movement={movement} />
        <ActionSet duplicate movement={movement} />
      </div>
      </div>
    </aside>
  );
}
