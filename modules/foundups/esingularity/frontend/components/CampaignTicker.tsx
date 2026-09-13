'use client';

import { currentFieldStatus } from '../content/current-field-status';

const actions = [
  { label: 'LIVE', text: currentFieldStatus.tickerJa, href: currentFieldStatus.href },
  { label: 'JHR', text: 'UPDATE 9/10｜仙台200MW・印西の地区計画・福井の選択肢', href: '/reports/jhr' },
  { label: 'NEW', text: 'YUMORI / COG DC 10枚のプレゼンを見る', href: '#yumori-deck' },
  { label: 'VISIT', text: '写真で現地を見る', href: 'https://pics.yumori.info' },
  { label: 'LISTEN', text: '九頭竜の音楽を聴く', href: 'https://music.yumori.me' },
  { label: 'LEARN', text: '再生計画を読む', href: 'https://pc.yumori.info' },
  { label: 'EXPLORE', text: 'YUMORI.infoでプロジェクトを見る', href: 'https://yumori.info' },
  { label: 'CONNECT', text: 'Monkとつながる', href: 'https://monk.yumori.info' },
  { label: 'JOIN', text: '温泉を守る準備委員会に名前を加える', href: 'https://docs.google.com/forms/d/e/1FAIpQLScSKFyzCym8NCarvNIa5cT9c2Pe8C-cY2AbC4zLgsDOKspYKA/viewform' },
  { label: 'ACT', text: '福井市役所へ声を届ける', href: '#city-action' },
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
  return (
    <aside className={movement ? 'campaign-ticker campaign-ticker-inline' : 'campaign-ticker'} aria-label="九頭竜を守るための行動メニュー">
      <div className="campaign-ticker-track">
        <ActionSet movement={movement} />
        <ActionSet duplicate movement={movement} />
      </div>
    </aside>
  );
}
