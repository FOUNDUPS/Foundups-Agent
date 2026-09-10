import { cleanProjection, membershipFor, MOSH_LIMIT, MOSH_PROJECT, MOSH_SITE, utcExpiry, type Projection } from './mosh-pit-policy';

export type GatewayConfig = {
  MOSH_PIT_MEMBERSHIPS_JSON?: string;
  MOSH_PIT_SOURCE_URL?: string;
  MOSH_PIT_SOURCE_TOKEN?: string;
};
export type FeedResult = { status: 'ready'; projection: Projection } |
  { status: 'signed_out' | 'not_approved' | 'unavailable' };

// Only callable on the server with dispatch-verified identity. No browser token.
// Upstream must implement the separate, project-scoped gateway contract.
export async function readMoshPit(
  userId: string | null, config: GatewayConfig, request: typeof fetch = fetch,
): Promise<FeedResult> {
  const access = membershipFor(config.MOSH_PIT_MEMBERSHIPS_JSON, userId);
  if (access.status !== 'allowed') return access;
  try {
    if (!config.MOSH_PIT_SOURCE_URL || !config.MOSH_PIT_SOURCE_TOKEN || config.MOSH_PIT_SOURCE_TOKEN.length < 32) return { status: 'unavailable' };
    const url = new URL(config.MOSH_PIT_SOURCE_URL);
    if (url.protocol !== 'https:' || url.username || url.password || url.hash || url.search) return { status: 'unavailable' };
    const snapshot = crypto.randomUUID();
    const response = await request(url, {
      method: 'POST', redirect: 'error', cache: 'no-store', signal: AbortSignal.timeout(10_000),
      headers: { Authorization: `Bearer ${config.MOSH_PIT_SOURCE_TOKEN}`, 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ schema_version: 'mosh_pit_gateway_read.v1', site_id: MOSH_SITE,
        viewer_id: access.membership.userId, membership_revision: access.membership.version,
        foundup_id: MOSH_PROJECT, disclosure_class: 'stakeholder', snapshot_id: snapshot,
        timezone: 'Asia/Tokyo', limit: MOSH_LIMIT }),
    });
    if (response.status === 401 || response.status === 403) return { status: 'not_approved' };
    if (!response.ok || !response.headers.get('content-type')?.includes('application/json') || !response.body) return { status: 'unavailable' };
    // Bound the actual decoded response, including chunked/compressed bodies.
    const reader = response.body.getReader();
    const chunks: Uint8Array[] = [];
    let size = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        size += value.length;
        if (size > 1_000_000) throw Error('response_too_large');
        chunks.push(value);
      }
    } finally {
      await reader.cancel();
    }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
    const envelope = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
    const now = Date.now();
    const expires = utcExpiry(envelope.expires_at);
    if (envelope.schema_version !== 'mosh_pit_gateway_snapshot.v1' || envelope.site_id !== MOSH_SITE ||
        envelope.viewer_id !== userId || envelope.membership_revision !== access.membership.version ||
        !Number.isFinite(expires) || expires <= now || expires > now + 60_000 ||
        access.membership.expiresAt <= now) return { status: 'unavailable' };
    return { status: 'ready', projection: cleanProjection(envelope.projection, snapshot) };
  } catch {
    // Do not log response bodies, credentials, identities or private activity.
    return { status: 'unavailable' };
  }
}
