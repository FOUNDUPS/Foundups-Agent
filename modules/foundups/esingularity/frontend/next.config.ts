import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  async headers() {
    return ['/f/esingularity_001/mosh-pit', '/api/mosh-pit'].map(source => ({
      source,
      headers: [
        { key: 'Cache-Control', value: 'private, no-store, max-age=0' },
        { key: 'X-Robots-Tag', value: 'noindex, nofollow' },
        { key: 'Referrer-Policy', value: 'no-referrer' },
      ],
    }));
  },
};

export default nextConfig;
