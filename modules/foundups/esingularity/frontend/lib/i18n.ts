import type { Locale } from './project-data';

export type SharedCopy = {
  languageName: string;
  nav: {
    save: string;
    future: string;
    team: string;
  };
  line: {
    join: string;
    tapInstruction: string;
    qrInstruction: string;
  };
  footer: {
    summary: string;
    sourceLabel: string;
  };
};

export const sharedCopy: Record<Locale, SharedCopy> = {
  ja: {
    languageName: '日本語',
    nav: { save: '温泉を守る', future: '福井の未来', team: 'チーム' },
    line: {
      join: 'LINEに参加',
      tapInstruction: 'スマホの方はこちらをタップ',
      qrInstruction: '別の端末からはQRコードを読み取ってください',
    },
    footer: {
      summary: '温泉 × イノベーション × 福井の計算力 × 地域',
      sourceLabel: '根拠と出典',
    },
  },
  en: {
    languageName: 'English',
    nav: { save: 'Save the Onsen', future: 'Fukui’s Future', team: 'Team' },
    line: {
      join: 'Join on LINE',
      tapInstruction: 'On a phone, tap here to open LINE',
      qrInstruction: 'On another device, scan the QR code',
    },
    footer: {
      summary: 'Onsen × Innovation × Fukui Compute × Community',
      sourceLabel: 'Evidence and sources',
    },
  },
  pt: {
    languageName: 'Português',
    nav: { save: 'Salvar o onsen', future: 'Futuro de Fukui', team: 'Equipe' },
    line: {
      join: 'Entrar pelo LINE',
      tapInstruction: 'No celular, toque aqui para abrir o LINE',
      qrInstruction: 'Em outro aparelho, leia o código QR',
    },
    footer: {
      summary: 'Onsen × Inovação × Computação de Fukui × Comunidade',
      sourceLabel: 'Evidências e fontes',
    },
  },
};

export function pathForLocale(pathname: string, locale: Locale) {
  const parts = pathname.split('/').filter(Boolean);
  if (parts[0] === 'ja' || parts[0] === 'en' || parts[0] === 'pt') parts.shift();
  const suffix = parts.length ? `/${parts.join('/')}` : '';
  return `/${locale}${suffix}`;
}
