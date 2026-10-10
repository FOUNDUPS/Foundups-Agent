// Shared handler is injectable so validation is tested without a production DB.
export type InterestInput = { name: string; email: string; relationship: string; story: string | null };
export const MAX_INTEREST_BYTES = 8192;
const relationships = new Set(['天菅生町・近隣の住民', '施設を利用したことがある', '福井市・福井県の住民', '学生・教育・研究', '農業・地域産業', '技術・データセンター', '行政・公共政策', 'その他']);
class InputError extends Error {
  status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}
async function readBody(request: Request): Promise<Record<string, unknown>> {
  if (request.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== 'application/json') throw new InputError(415, 'unsupported_media_type');
  const length = request.headers.get('content-length');
  if (length !== null && (!/^\d+$/.test(length) || Number(length) > MAX_INTEREST_BYTES)) throw new InputError(413, 'body_too_large');
  if (!request.body) throw new InputError(400, 'invalid_submission');
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_INTEREST_BYTES) {
        await reader.cancel();
        throw new InputError(413, 'body_too_large');
      }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  try {
    const body: unknown = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
    if (!body || typeof body !== 'object' || Array.isArray(body)) throw new Error();
    return body as Record<string, unknown>;
  } catch { throw new InputError(400, 'invalid_submission'); }
}
export function createInterestHandler(save: (input: InterestInput, client: string) => Promise<boolean>) {
  return async function POST(request: Request) {
    const reply = (body: object, status: number, retry = false) => Response.json(body, {
      status, headers: { 'Cache-Control': 'no-store', ...(retry ? { 'Retry-After': '3600' } : {}) },
    });
    try {
      // Browsers may submit only from the current origin. Direct API callers still
      // face durable admission limits; Origin alone is not authentication.
      const origin = request.headers.get('origin');
      if (origin && origin !== new URL(request.url).origin) return reply({ ok: false, error: 'invalid_origin' }, 403);
      const body = await readBody(request);
      if (typeof body.website === 'string' && body.website.trim()) return reply({ ok: true }, 200);
      const field = (key: string) => typeof body[key] === 'string' ? (body[key] as string).trim() : '';
      const name = field('name'), email = field('email').toLowerCase(), relationship = field('relationship'), story = field('story');
      if (!name || name.length > 80 || !email || email.length > 160 || !/^\S+@\S+\.\S+$/.test(email) || !relationships.has(relationship) || story.length > 1500 || body.consent !== 'yes') return reply({ ok: false, error: 'invalid_submission' }, 400);
      // Cloudflare overwrites this at ingress. Never accept X-Forwarded-For.
      // Missing ingress metadata shares one conservative quota.
      const client = request.headers.get('cf-connecting-ip')?.slice(0, 64) || 'unknown';
      const accepted = await save({ name, email, relationship, story: story || null }, client);
      return accepted ? reply({ ok: true }, 201) : reply({ ok: false, error: 'submission_limited' }, 429, true);
    } catch (error) {
      if (error instanceof InputError) return reply({ ok: false, error: error.message }, error.status);
      return reply({ ok: false, error: 'submission_failed' }, 503);
    }
  };
}
