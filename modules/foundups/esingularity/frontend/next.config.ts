import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  async rewrites() {
    return {
      // Run before the existing app/page.tsx route is selected. This is an
      // internal rewrite: the visitor keeps YUMORI.me in the address bar.
      beforeFiles: [
        {
          source: '/',
          has: [{ type: 'host', value: '(?:www\\.)?yumori\\.me' }],
          destination: '/yumori',
        },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
};

// eSingularity.ai keeps app/page.tsx. YUMORI.info's existing external
// redirect is intentionally not replaced here. Reports, APIs, assets and
// direct /yumori links retain their existing paths on the shared host.
export default nextConfig;
