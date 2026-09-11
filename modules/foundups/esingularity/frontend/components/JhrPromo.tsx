'use client';

import { usePathname } from 'next/navigation';
import { getLatestPublishedJhrIssue } from '../content/jhr-issues';

export default function JhrPromo() {
  const pathname = usePathname();
  const issue = getLatestPublishedJhrIssue();

  if (pathname.startsWith('/reports/jhr')) return null;

  return (
    <a
      href={issue.href}
      target="_blank"
      rel="noreferrer"
      aria-label={`Japan Hyperscaler Report #${issue.number}を読む`}
      style={{
        position: 'fixed', right: 14, bottom: 14, zIndex: 1000,
        width: 'min(390px, calc(100vw - 28px))', display: 'grid',
        gridTemplateColumns: '96px 1fr', overflow: 'hidden', borderRadius: 16,
        background: '#0b2545', color: '#fff', textDecoration: 'none',
        boxShadow: '0 10px 34px rgba(0,0,0,.32)', border: '1px solid rgba(255,255,255,.2)',
      }}
    >
      <img
        src={issue.heroImage}
        alt="福井の田園と大規模データセンター用地の概念比較"
        style={{ width: 96, height: '100%', minHeight: 108, objectFit: 'cover', display: 'block' }}
      />
      <span style={{ padding: '12px 14px', display: 'block' }}>
        <strong style={{ display: 'block', fontSize: 12, letterSpacing: '.1em', marginBottom: 5 }}>
          JAPAN HYPERSCALER REPORT #{String(issue.number).padStart(3, '0')}
        </strong>
        <span style={{ display: 'block', fontWeight: 900, lineHeight: 1.35, fontSize: 14 }}>
          {issue.titleJa}
        </span>
        <span style={{ display: 'block', marginTop: 7, fontSize: 12, opacity: .82 }}>
          READ REPORT →
        </span>
      </span>
    </a>
  );
}
