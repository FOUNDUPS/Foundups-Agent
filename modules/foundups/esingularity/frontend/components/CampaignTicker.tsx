'use client';

import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { currentFieldStatus } from '../content/current-field-status';

type FieldStatus = {
  updatedAt: string;
  updatedLabelJa: string;
  locationJa: string;
  tickerJa: string;
  detailJa: string;
  detailEn: string;
  href: string;
};

type LiveFieldStatusPayload = FieldStatus & {
  version: number;
  active: boolean;
  expiresAt: string;
  source?: string;
};

const LIVE_FIELD_STATUS_URL = 'https://raw.githubusercontent.com/FOUNDUPS/Foundups-Agent/refs/heads/live/yumori-field-status/modules/foundups/esingularity/frontend/status/live-field-status.json';
const LIVE_FIELD_STATUS_POLL_MS = 60_000;

const fallbackFieldStatus: FieldStatus = {
  updatedAt: currentFieldStatus.updatedAt,
  updatedLabelJa: currentFieldStatus.updatedLabelJa,
  locationJa: currentFieldStatus.locationJa,
  tickerJa: currentFieldStatus.tickerJa,
  detailJa: currentFieldStatus.detailJa,
  detailEn: currentFieldStatus.detailEn,
  href: currentFieldStatus.href,
};

function parseLiveFieldStatus(value: unknown): FieldStatus | null {
  if (!value || typeof value !== 'object') return null;
  const payload = value as Record<string, unknown>;
  if (payload.version !== 1 || payload.active !== true) return null;

  const required = ['updatedAt', 'expiresAt', 'updatedLabelJa', 'locationJa', 'tickerJa', 'detailJa', 'detailEn', 'href'] as const;
  for (const field of required) {
    if (typeof payload[field] !== 'string' || !(payload[field] as string).trim()) return null;
  }

  const updatedAt = Date.parse(payload.updatedAt as string);
  const expiresAt = Date.parse(payload.expiresAt as string);
  if (!Number.isFinite(updatedAt) || !Number.isFinite(expiresAt) || expiresAt <= updatedAt || Date.now() >= expiresAt) return null;
  if (!(payload.href as string).startsWith('https://')) return null;

  return {
    updatedAt: payload.updatedAt as string,
    updatedLabelJa: payload.updatedLabelJa as string,
    locationJa: payload.locationJa as string,
    tickerJa: payload.tickerJa as string,
    detailJa: payload.detailJa as string,
    detailEn: payload.detailEn as string,
    href: payload.href as string,
  };
}

function useLiveFieldStatus(): FieldStatus {
  const [fieldStatus, setFieldStatus] = useState<FieldStatus>(fallbackFieldStatus);

  useEffect(() => {
    let cancelled = false;

    const refresh = async () => {
      try {
        const response = await fetch(`${LIVE_FIELD_STATUS_URL}?t=${Date.now()}`, { cache: 'no-store' });
        if (!response.ok) throw new Error(`live field status ${response.status}`);
        const parsed = parseLiveFieldStatus((await response.json()) as LiveFieldStatusPayload);
        if (!cancelled) setFieldStatus(parsed ?? fallbackFieldStatus);
      } catch {
        if (!cancelled) setFieldStatus(fallbackFieldStatus);
      }
    };

    void refresh();
    const interval = window.setInterval(() => void refresh(), LIVE_FIELD_STATUS_POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  return fieldStatus;
}

function ActionSet({ fieldStatus, duplicate = false, movement = false }: { fieldStatus: FieldStatus; duplicate?: boolean; movement?: boolean }) {
  const actions = [
    { label: 'VOTE NO', text: fieldStatus.tickerJa, href: fieldStatus.href },
    { label: '市議会', text: '設立準備委員会から福井市議会へのメッセージを読む', href: 'https://yumori.me/vote-no#council' },
    { label: '市長', text: '設立準備委員会から福井市長へのメッセージを読む', href: 'https://yumori.me/vote-no#mayor' },
    { label: '声を届ける', text: '福井市議会・福井市へ連絡する', href: 'https://yumori.me/vote-no#contact' },
    { label: 'JHR', text: 'UPDATE 9/14｜なぜ福井に「AI交番」が必要なのか｜日本語＋English', href: '/reports/jhr' },
    { label: 'NEW', text: 'YUMORI / COG DC 10枚のプレゼンを見る', href: '#yumori-deck' },
    { label: 'VISIT', text: '写真で現地を見る', href: 'https://pics.yumori.info' },
    { label: 'LISTEN', text: '九頭竜の音楽を聴く', href: 'https://music.yumori.me' },
    { label: 'LEARN', text: '再生計画を読む', href: 'https://pc.yumori.info' },
    { label: 'EXPLORE', text: 'YUMORI.infoでプロジェクトを見る', href: 'https://yumori.info' },
    { label: 'JOIN', text: '温泉を守る準備委員会に名前を加える', href: 'https://docs.google.com/forms/d/e/1FAIpQLScSKFyzCym8NCarvNIa5cT9c2Pe8C-cY2AbC4zLgsDOKspYKA/viewform' },
  ] as const;

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
  const fieldStatus = useLiveFieldStatus();
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
  }, [fieldStatus.tickerJa]);
  const tickerStyle = {
    '--ticker-duration': '300s',
    ...(movement ? {} : { position: 'relative', top: 'auto', marginTop: '112px' }),
  } as CSSProperties;
  return (
    <aside ref={tickerRef} data-reading={reading} style={tickerStyle} className={movement ? 'campaign-ticker campaign-ticker-inline' : 'campaign-ticker'} aria-label="九頭竜を守るための行動メニュー">
      <button className="campaign-ticker-control" type="button" aria-pressed={reading} onClick={() => setReading(!reading)}>{reading ? '再開' : '停止して読む'}</button>
      <div className="campaign-ticker-window">
      <div ref={trackRef} className="campaign-ticker-track">
        <ActionSet fieldStatus={fieldStatus} movement={movement} />
        <ActionSet fieldStatus={fieldStatus} duplicate movement={movement} />
      </div>
      </div>
    </aside>
  );
}
