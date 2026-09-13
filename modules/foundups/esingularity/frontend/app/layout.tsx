import type { Metadata } from 'next';
import { Noto_Sans_JP, Space_Mono } from 'next/font/google';
import JapaneseSurfacePolisher from '../components/JapaneseSurfacePolisher';
import LanguageSwitcher from '../components/LanguageSwitcher';
import PwaRegister from '../components/PwaRegister';
import './globals.css';

const noto = Noto_Sans_JP({ variable: '--font-noto', subsets: ['latin'], weight: ['400', '500', '600', '700', '900'] });
const mono = Space_Mono({ variable: '--font-mono', subsets: ['latin'], weight: ['400', '700'] });

export const metadata: Metadata = {
  metadataBase: new URL('https://esingularity.ai'),
  title: 'Project eSingularity | 温泉 × COG DC × 学びの地域再生構想',
  description: '旧すかっとランド九頭竜を、温泉、地域の食、文化、教育、FoundUpプロジェクト、地域主体の小規模AI計算基盤（COG DC）につなぐ施設再利用構想です。',
  manifest: '/manifest.webmanifest',
  icons: { icon: '/favicon.svg', apple: '/pwa-icon-192.png' },
  openGraph: {
    title: 'Project eSingularity — 温泉 × COG DC × 学び',
    description: '旧すかっとランド九頭竜の施設、温泉、イノベーション・スペース、地域AI計算基盤をつなぐ再利用構想。',
    url: 'https://esingularity.ai',
    siteName: 'eSingularity.ai',
    locale: 'ja_JP',
    type: 'website',
    images: [{ url: '/yumori-compute-field.webp', width: 1672, height: 941, alt: '福井の田園と地域AI計算基盤を組み合わせたProject eSingularity構想' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Project eSingularity — 温泉 × COG DC × 学び',
    description: '旧すかっとランド九頭竜の施設再利用と、地域主体のAI計算基盤の構想。',
    images: ['/yumori-compute-field.webp'],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ja">
      <body className={`${noto.variable} ${mono.variable}`}>
        <LanguageSwitcher />
        <JapaneseSurfacePolisher />
        <PwaRegister />
        {children}
      </body>
    </html>
  );
}
