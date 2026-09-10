export type JhrIssue = {
  id: string;
  number: number;
  publishedAt: string;
  updatedAt: string;
  titleJa: string;
  tickerJa: string;
  href: string;
  status: 'published' | 'draft';
};

export const jhrIssues: readonly JhrIssue[] = [
  {
    id: 'jhr-001',
    number: 1,
    publishedAt: '2026-09-10',
    updatedAt: '2026-09-10',
    titleJa: '日本は「次の印西」を全国につくろうとしているのか',
    tickerJa: 'JHR #001｜仙台200MW・印西の地区計画・福井の選択肢',
    href: '/reports/jhr',
    status: 'published',
  },
] as const;

export function getLatestPublishedJhrIssue(): JhrIssue {
  const published = jhrIssues
    .filter((issue) => issue.status === 'published')
    .sort((a, b) => b.number - a.number);

  if (published.length === 0) {
    throw new Error('JHR registry has no published issue');
  }

  return published[0];
}
