import { currentMoshPit } from '@/lib/mosh-pit-server';

export const dynamic = 'force-dynamic';

export async function GET() {
  const result = await currentMoshPit();
  const status = { ready: 200, signed_out: 401, not_approved: 403, unavailable: 503 }[result.status];
  return Response.json(result, { status, headers: {
    'Cache-Control': 'private, no-store, max-age=0', 'Vary': 'Cookie',
    'X-Robots-Tag': 'noindex, nofollow',
  } });
}
