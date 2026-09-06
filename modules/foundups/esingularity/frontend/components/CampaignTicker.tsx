'use client';

const actions = [
  { label: 'NEW', text: 'YUMORI / COG DC 10枚のプレゼンを見る', href: '#yumori-deck' },
  { label: 'VISIT', text: '写真で現地を見る', href: 'https://pics.yumori.info' },
  { label: 'LISTEN', text: '九頭竜の音楽を聴く', href: 'https://music.yumori.me' },
  { label: 'LEARN', text: '再生計画を読む', href: 'https://pc.yumori.info' },
  { label: 'EXPLORE', text: 'YUMORI.infoでプロジェクトを見る', href: 'https://yumori.info' },
  { label: 'CONNECT', text: 'Monkとつながる', href: 'https://monk.yumori.info' },
  { label: 'JOIN', text: '温泉を守る準備委員会に名前を加える', href: 'https://docs.google.com/forms/d/e/1FAIpQLScSKFyzCym8NCarvNIa5cT9c2Pe8C-cY2AbC4zLgsDOKspYKA/viewform' },
  { label: 'ACT', text: '福井市役所へ声を届ける', href: '#city-action' },
] as const;

function ActionSet({ duplicate = false }: { duplicate?: boolean }) {
  return (
    <div className="campaign-ticker-set" aria-hidden={duplicate || undefined}>
      {actions.map((action) => {
        const external = action.href.startsWith('http');
        return (
          <a key={action.label} href={action.href} target={external ? '_blank' : undefined} rel={external ? 'noreferrer' : undefined} tabIndex={duplicate ? -1 : undefined}>
            <strong>{action.label}</strong><span>{action.text}</span>
          </a>
        );
      })}
      <a href="#act-now" tabIndex={duplicate ? -1 : undefined}><strong>SAVE THE DRAGON</strong><span>九頭竜を守れ。温泉を守れ。</span></a>
    </div>
  );
}

export default function CampaignTicker() {
  return (
    <aside className="campaign-ticker" aria-label="九頭竜を守るための行動メニュー">
      <div className="campaign-ticker-track">
        <ActionSet />
        <ActionSet duplicate />
      </div>
    </aside>
  );
}
