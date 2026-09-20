'use client';

import { useEffect, useRef, useState, type CSSProperties } from 'react';
import compiledFieldStatus from '../content/current-field-status.json';

type TickerLanguage = 'ja' | 'en' | 'pt';
type LocalizedCopy = Record<TickerLanguage, string>;

type FieldStatus = {
  schemaVersion: 1;
  visible: true;
  updatedAt: string;
  expiresAt: string;
  label: LocalizedCopy;
  message: LocalizedCopy;
  href: string;
};

type TickerAction = {
  label: LocalizedCopy;
  message: LocalizedCopy;
  href: string;
};

const LIVE_FIELD_STATUS_URL = 'https://raw.githubusercontent.com/FOUNDUPS/Foundups-Agent/refs/heads/live/yumori-field-status/modules/foundups/esingularity/frontend/content/current-field-status.json';
const LIVE_FIELD_STATUS_POLL_MS = 60_000;
const ALLOWED_STATUS_ORIGINS = new Set(['https://yumori.me', 'https://www.yumori.me', 'https://esingularity.ai']);

const fallbackAction: TickerAction = {
  label: { ja: 'VOTE NO', en: 'VOTE NO', pt: 'VOTE NÃO' },
  message: {
    ja: '解体の前に再利用案を比較する時間を。YUMORI.meの市議会・市長へのメッセージを読み、声を届けてください。',
    en: 'Ask for time to compare reuse before demolition. Read the YUMORI.me messages to the City Council and mayor, then make your voice heard.',
    pt: 'Peça tempo para comparar o reuso antes da demolição. Leia as mensagens da YUMORI.me ao Conselho Municipal e ao prefeito e faça sua voz ser ouvida.',
  },
  href: 'https://yumori.me/vote-no',
};

const staticActions: TickerAction[] = [
  {
    label: { ja: '市議会', en: 'COUNCIL', pt: 'CONSELHO' },
    message: {
      ja: '設立準備委員会から福井市議会へのメッセージを読む',
      en: 'Read the Preparatory Committee message to Fukui City Council',
      pt: 'Leia a mensagem do Comitê Preparatório ao Conselho Municipal de Fukui',
    },
    href: 'https://yumori.me/vote-no#council',
  },
  {
    label: { ja: '市長', en: 'MAYOR', pt: 'PREFEITO' },
    message: {
      ja: '設立準備委員会から福井市長へのメッセージを読む',
      en: 'Read the Preparatory Committee message to the Mayor of Fukui',
      pt: 'Leia a mensagem do Comitê Preparatório ao prefeito de Fukui',
    },
    href: 'https://yumori.me/vote-no#mayor',
  },
  {
    label: { ja: '声を届ける', en: 'CONTACT', pt: 'CONTATO' },
    message: {
      ja: '福井市議会・福井市へ連絡する',
      en: 'Contact Fukui City Council and Fukui City',
      pt: 'Entre em contato com o Conselho Municipal e a Prefeitura de Fukui',
    },
    href: 'https://yumori.me/vote-no#contact',
  },
  {
    label: { ja: 'JHR', en: 'JHR', pt: 'JHR' },
    message: {
      ja: 'UPDATE 9/14｜なぜ福井に「AI交番」が必要なのか｜日本語＋English',
      en: 'UPDATE 9/14 | Why Fukui needs an “AI koban” | Japanese + English',
      pt: 'ATUALIZAÇÃO 14/9 | Por que Fukui precisa de um “koban de IA” | Japonês + inglês',
    },
    href: '/reports/jhr#jhr-002',
  },
  {
    label: { ja: 'NEW', en: 'NEW', pt: 'NOVO' },
    message: {
      ja: 'YUMORI / COG DC 10枚のプレゼンを見る',
      en: 'See the new 10-slide YUMORI / COG DC presentation',
      pt: 'Veja a nova apresentação YUMORI / COG DC em 10 slides',
    },
    href: '#yumori-deck',
  },
  {
    label: { ja: 'VISIT', en: 'VISIT', pt: 'VISITE' },
    message: { ja: '写真で現地を見る', en: 'See the site in photos', pt: 'Veja o local em fotos' },
    href: 'https://pics.yumori.info',
  },
  {
    label: { ja: 'LISTEN', en: 'LISTEN', pt: 'OUÇA' },
    message: { ja: '九頭竜の音楽を聴く', en: 'Listen to the music of Kuzuryu', pt: 'Ouça a música de Kuzuryu' },
    href: 'https://music.yumori.me',
  },
  {
    label: { ja: 'LEARN', en: 'LEARN', pt: 'SAIBA MAIS' },
    message: { ja: '再生計画を読む', en: 'Read the renewal plan', pt: 'Leia o plano de renovação' },
    href: 'https://pc.yumori.info',
  },
  {
    label: { ja: 'EXPLORE', en: 'EXPLORE', pt: 'EXPLORE' },
    message: {
      ja: 'YUMORI.infoでプロジェクトを見る',
      en: 'Explore the project on YUMORI.info',
      pt: 'Explore o projeto no YUMORI.info',
    },
    href: 'https://yumori.info',
  },
  {
    label: { ja: 'JOIN', en: 'JOIN', pt: 'PARTICIPE' },
    message: {
      ja: '温泉を守る準備委員会に名前を加える',
      en: 'Add your name to the Save Onsen Preparatory Committee',
      pt: 'Adicione seu nome ao Comitê Preparatório para Salvar o Onsen',
    },
    href: 'https://docs.google.com/forms/d/e/1FAIpQLScSKFyzCym8NCarvNIa5cT9c2Pe8C-cY2AbC4zLgsDOKspYKA/viewform',
  },
];

const closingAction: TickerAction = {
  label: { ja: 'SAVE THE DRAGON', en: 'SAVE THE DRAGON', pt: 'SALVE O DRAGÃO' },
  message: {
    ja: '九頭竜を守れ。温泉を守れ。',
    en: 'Save Kuzuryu. Save the onsen.',
    pt: 'Salve Kuzuryu. Salve o onsen.',
  },
  href: '#act-now',
};

const tickerUi = {
  ariaLabel: { ja: '九頭竜を守るための行動メニュー', en: 'Actions to save Kuzuryu', pt: 'Ações para salvar Kuzuryu' },
  stop: { ja: '停止して読む', en: 'Stop to read', pt: 'Parar para ler' },
  resume: { ja: '再開', en: 'Resume', pt: 'Retomar' },
} satisfies Record<string, LocalizedCopy>;

function validLocalizedCopy(value: unknown, maximumLength: number): value is LocalizedCopy {
  if (!value || typeof value !== 'object') return false;
  const copy = value as Record<string, unknown>;
  return (['ja', 'en', 'pt'] as const).every((language) => {
    const text = copy[language];
    return typeof text === 'string' && text.trim().length > 0 && text.length <= maximumLength;
  });
}

function parseFieldStatus(value: unknown, now = Date.now()): FieldStatus | null {
  if (!value || typeof value !== 'object') return null;
  const payload = value as Record<string, unknown>;
  if (payload.schemaVersion !== 1 || payload.visible !== true) return null;
  if (typeof payload.updatedAt !== 'string' || typeof payload.expiresAt !== 'string' || typeof payload.href !== 'string') return null;
  if (!validLocalizedCopy(payload.label, 80) || !validLocalizedCopy(payload.message, 800)) return null;

  const updatedAt = Date.parse(payload.updatedAt);
  const expiresAt = Date.parse(payload.expiresAt);
  if (!Number.isFinite(updatedAt) || !Number.isFinite(expiresAt) || expiresAt <= updatedAt || now >= expiresAt) return null;
  if (updatedAt > now + 5 * 60_000 || expiresAt - updatedAt > 14 * 24 * 60 * 60_000) return null;

  try {
    const destination = new URL(payload.href);
    if (destination.protocol !== 'https:' || !ALLOWED_STATUS_ORIGINS.has(destination.origin)) return null;
  } catch {
    return null;
  }

  return payload as FieldStatus;
}

function documentLanguage(): TickerLanguage {
  const language = document.documentElement.lang.toLowerCase();
  if (language.startsWith('pt')) return 'pt';
  if (language.startsWith('en')) return 'en';
  return 'ja';
}

function useTickerLanguage(): TickerLanguage {
  const [language, setLanguage] = useState<TickerLanguage>('ja');

  useEffect(() => {
    const update = () => setLanguage(documentLanguage());
    update();
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
    return () => observer.disconnect();
  }, []);

  return language;
}

function useFieldStatus(): FieldStatus | null {
  const [fieldStatus, setFieldStatus] = useState<FieldStatus | null>(() => parseFieldStatus(compiledFieldStatus));

  useEffect(() => {
    let cancelled = false;

    const refresh = async () => {
      try {
        const minute = Math.floor(Date.now() / LIVE_FIELD_STATUS_POLL_MS);
        const response = await fetch(`${LIVE_FIELD_STATUS_URL}?v=${minute}`, { cache: 'no-store' });
        if (!response.ok) throw new Error(`live field status ${response.status}`);
        const parsed = parseFieldStatus(await response.json());
        if (!cancelled) setFieldStatus(parsed ?? parseFieldStatus(compiledFieldStatus));
      } catch {
        if (!cancelled) setFieldStatus(parseFieldStatus(compiledFieldStatus));
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

function ActionSet({ fieldStatus, language, duplicate = false, movement = false }: { fieldStatus: FieldStatus | null; language: TickerLanguage; duplicate?: boolean; movement?: boolean }) {
  const leadAction: TickerAction = fieldStatus
    ? { label: fieldStatus.label, message: fieldStatus.message, href: fieldStatus.href }
    : fallbackAction;
  const actions = [leadAction, ...staticActions, closingAction];

  return (
    <div className="campaign-ticker-set" aria-hidden={duplicate || undefined}>
      {actions.map((action) => {
        const href = movement && action.href.startsWith('#') ? `https://esingularity.ai/${action.href}` : action.href;
        const external = href.startsWith('http');
        return (
          <a key={`${action.href}-${action.label.ja}`} href={href} target={external ? '_blank' : undefined} rel={external ? 'noreferrer' : undefined} tabIndex={duplicate ? -1 : undefined}>
            <strong>{action.label[language]}</strong><span>{action.message[language]}</span>
          </a>
        );
      })}
    </div>
  );
}

export default function CampaignTicker({ movement = false }: { movement?: boolean }) {
  const [reading, setReading] = useState(false);
  const language = useTickerLanguage();
  const fieldStatus = useFieldStatus();
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
  }, [fieldStatus, language]);
  const tickerStyle = {
    '--ticker-duration': '300s',
    ...(movement ? {} : { position: 'relative', top: 'auto', marginTop: '112px' }),
  } as CSSProperties;
  return (
    <aside ref={tickerRef} data-yumori-localized data-reading={reading} style={tickerStyle} className={movement ? 'campaign-ticker campaign-ticker-inline' : 'campaign-ticker'} aria-label={tickerUi.ariaLabel[language]}>
      <button className="campaign-ticker-control" type="button" aria-pressed={reading} onClick={() => setReading(!reading)}>{reading ? tickerUi.resume[language] : tickerUi.stop[language]}</button>
      <div className="campaign-ticker-window">
      <div ref={trackRef} className="campaign-ticker-track">
        <ActionSet fieldStatus={fieldStatus} language={language} movement={movement} />
        <ActionSet fieldStatus={fieldStatus} language={language} duplicate movement={movement} />
      </div>
      </div>
    </aside>
  );
}
