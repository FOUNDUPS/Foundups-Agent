import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: '温泉を守る | Project eSingularity 福井',
    short_name: '温泉を守る',
    description: '旧すかっとランド九頭竜を壊す前に、もう一つの未来を。',
    start_url: '/',
    display: 'standalone',
    background_color: '#020812',
    theme_color: '#082d5b',
    lang: 'ja',
    icons: [
      { src: '/pwa-icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any maskable' },
      { src: '/pwa-icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
    ],
  };
}
