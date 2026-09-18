import { isIP } from 'node:net';
import { REDDOG_ORIGINS, RedDogError, exactKeys, hex, publicText, readBoundedJson, type Surface } from './reddog-policy';
import { RedDogStore } from './reddog-store';
import { publicReply, type ProviderConfig } from './reddog-openrouter';
import { KNOWLEDGE_REVISION } from './reddog-knowledge';

export type RedDogEnv = ProviderConfig & { DB: D1Database; REDDOG_SUBJECT_KEY?: string;
  REDDOG_INGRESS_VERIFIED?: string; REDDOG_ENABLED?: string };
const operations = new Set(['encounter', 'turn', 'status', 'withdraw']);
// Sites dispatch must preserve the Cloudflare edge-owned peer header. Activation
// requires spoofed-header canaries; absent proof/configuration fails closed.
export async function peerSubject(request: Request, config: RedDogEnv) {
  const address = request.headers.get('cf-connecting-ip');
  if (config.REDDOG_INGRESS_VERIFIED !== 'cloudflare-connecting-ip-v1' || !address || !isIP(address) ||
      !config.REDDOG_SUBJECT_KEY || config.REDDOG_SUBJECT_KEY.length < 32)
    throw new RedDogError('public_ingress_unavailable', 503);
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(config.REDDOG_SUBJECT_KEY),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return Array.from(new Uint8Array(await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(address))), b => b.toString(16).padStart(2,'0')).join('');
}
function response(data: unknown, status: number, origin = '') {
  const headers: Record<string,string> = { 'Cache-Control': 'no-store', Vary: 'Origin', 'X-Content-Type-Options':'nosniff' };
  if (origin) headers['Access-Control-Allow-Origin'] = origin;
  if (status === 429) headers['Retry-After'] = '60';
  return Response.json(data, { status, headers });
}
export async function handlePublicRequest(request: Request, surfaceName: string, operation: string, config: RedDogEnv,
  responder = publicReply, now: () => number = () => Math.floor(Date.now()/1000)) {
  let origin = '';
  try {
    if (!Object.hasOwn(REDDOG_ORIGINS, surfaceName) || !operations.has(operation)) throw new RedDogError('public_route_not_found',404);
    const surface = surfaceName as Surface;
    if (request.headers.get('origin') !== REDDOG_ORIGINS[surface]) throw new RedDogError('public_surface_denied',403);
    origin = REDDOG_ORIGINS[surface];
    if (request.method === 'OPTIONS') {
      const res = response({},200,origin); res.headers.set('Access-Control-Allow-Methods','POST');
      res.headers.set('Access-Control-Allow-Headers','Authorization, Content-Type'); return res;
    }
    if (request.method !== 'POST') throw new RedDogError('public_method_denied',405);
    if (request.headers.get('content-type')?.split(';')[0].trim() !== 'application/json') throw new RedDogError('public_content_type_invalid',415);
    if (config.REDDOG_ENABLED !== 'true' || !config.DB || !config.OPENROUTER_API_KEY || !config.OPENROUTER_MODEL)
      throw new RedDogError('public_service_unavailable',503);
    const identity = { surface, origin, subject: await peerSubject(request, config) };
    const store = new RedDogStore(config.DB);
    const body = await readBoundedJson(request, 12288, AbortSignal.timeout(2000));
    if (operation === 'encounter') {
      exactKeys(body,['consent','consent_version','actor_claim']);
      if (body.consent !== true || body.consent_version !== 'reddog.public-guest.v1' ||
          typeof body.actor_claim !== 'string' || !['human','agent','unspecified'].includes(body.actor_claim)) throw new RedDogError('public_consent_required',403);
      return response(await store.open(identity,now()),200,origin);
    }
    const authorization = request.headers.get('authorization') ?? '';
    if (!authorization.startsWith('Bearer ')) throw new RedDogError('public_session_denied',403);
    const token = hex(authorization.slice(7)), row = await store.session(token,identity,now());
    if (operation !== 'turn') {
      exactKeys(body,[]);
      return response(operation === 'status' ? store.status(row,now()) : await store.withdraw(row),200,origin);
    }
    exactKeys(body,['nonce','revision','message']);
    if (!Number.isSafeInteger(body.revision) || Number(body.revision)<0) throw new RedDogError('public_revision_invalid');
    const message = publicText(body.message);
    const turn = await store.reserve(row,hex(body.nonce),body.revision as number,now());
    try {
      await store.session(token,identity,now());
      const answer = await responder(message,surface,config,turn.deadline);
      // Withdrawal/session expiry wins over a late provider response.
      await store.session(token,identity,now());
      if (now() >= turn.deadline) throw new RedDogError('public_reply_timeout',504);
      return response({ ...answer, nonce: turn.nonce, revision: turn.revision, remaining_turns: turn.remaining_turns },200,origin);
    } catch (error) {
      const failure = error instanceof RedDogError ? error : new RedDogError('public_reply_failed',502);
      return response({ error:failure.code, resume:{ nonce:turn.nonce,revision:turn.revision,remaining_turns:turn.remaining_turns } },failure.status,origin);
    } finally {
      // This is an active-transport ceiling, not proof of remote generation
      // termination. Daily usage is never refunded. Failed cleanup retains its
      // durable slot; a process restart does not silently clear orphaned slots.
      await store.finish(row.token_hash,turn.reservation);
    }
  } catch (error) {
    const failure = error instanceof RedDogError ? error : new RedDogError('public_service_unavailable',503);
    return response({error:failure.code},failure.status,origin);
  }
}
export function health(config: RedDogEnv) {
  return response({ configured: config.REDDOG_ENABLED === 'true' && !!config.DB && !!config.OPENROUTER_API_KEY &&
    !!config.OPENROUTER_MODEL && config.OPENROUTER_MODEL.length<=160 && (config.REDDOG_SUBJECT_KEY?.length??0)>=32 && config.REDDOG_INGRESS_VERIFIED === 'cloudflare-connecting-ip-v1',
    knowledge_revision: KNOWLEDGE_REVISION, knowledge_as_of:'2026-09-09', mosh_pit:'curated_public_snapshot',
    disclosure:'public',effect_ceiling:'NONE' },200);
}
