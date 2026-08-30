import type { Metadata } from 'next';
import { Noto_Sans_JP, Space_Mono } from 'next/font/google';
import LanguageSwitcher from '../components/LanguageSwitcher';
import PwaRegister from '../components/PwaRegister';
import './globals.css';

const noto = Noto_Sans_JP({ variable: '--font-noto', subsets: ['latin'], weight: ['400', '500', '600', '700', '900'] });
const mono = Space_Mono({ variable: '--font-mono', subsets: ['latin'], weight: ['400', '700'] });

export const metadata: Metadata = {
  metadataBase: new URL('https://esingularity.ai'),
  title: '温泉を守る | Project eSingularity 福井',
  description: '旧すかっとランド九頭竜を壊す前に、もう一つの未来を。温泉、学び、福井のAI基盤、食、文化をつなぐ地域再生プロジェクトです。',
  manifest: '/manifest.webmanifest',
  icons: { icon: '/favicon.svg', apple: '/pwa-icon-192.png' },
  openGraph: {
    title: '温泉を守る。福井のAIの未来をつくる。',
    description: '旧すかっとランド九頭竜を壊す前に、地域で別の未来を比べる機会を。',
    url: 'https://esingularity.ai',
    siteName: 'eSingularity.ai',
    locale: 'ja_JP',
    type: 'website',
    images: [{ url: '/campaign-phase-2.jpg', width: 930, height: 1280, alt: 'eSingularity.ai 温泉を守るキャンペーン' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: '温泉を守る。福井のAIの未来をつくる。',
    description: '旧すかっとランド九頭竜を壊す前に、地域で別の未来を比べる機会を。',
    images: ['/campaign-phase-2.jpg'],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ja"><body className={`${noto.variable} ${mono.variable}`}><LanguageSwitcher /><PwaRegister />{children}</body></html>;
}
