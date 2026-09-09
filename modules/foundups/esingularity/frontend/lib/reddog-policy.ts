// Cloudflare adapter of moltbot_bridge/reddog_public_policy.py. Keep ceilings in sync.
export const REDDOG_POLICY = Object.freeze({ session_seconds: 600, idle_seconds: 120,
  session_turns: 10, subject_sessions_daily: 3, global_sessions_daily: 200,
  subject_turns_daily: 20, global_turns_daily: 1000, concurrent_calls: 4,
  input_chars: 2000, output_tokens: 256, reply_chars: 4000, request_seconds: 15 });
export const REDDOG_ORIGINS = Object.freeze({ foundups: 'https://foundups.com', esingularity: 'https://esingularity.ai' });
export type Surface = keyof typeof REDDOG_ORIGINS;
export class RedDogError extends Error {
  constructor(public code: string, public status = 400) { super(code); }
}
export function exactKeys(body: unknown, keys: string[]): asserts body is Record<string, unknown> {
  if (!body || typeof body !== 'object' || Array.isArray(body) ||
      Object.keys(body).sort().join(',') !== [...keys].sort().join(',')) throw new RedDogError('public_shape_invalid');
}
export function publicText(value: unknown, limit: number = REDDOG_POLICY.input_chars): string {
  if (typeof value !== 'string' || !value.trim() || [...value].length > limit ||
      /[\p{Cc}\p{Cf}\p{Cs}]/u.test(value.replace(/[\n\r\t]/g, ''))) throw new RedDogError('public_text_invalid');
  return value.trim();
}
export function hex(value: unknown): string {
  if (typeof value !== 'string' || !/^[0-9a-f]{64}$/.test(value)) throw new RedDogError('public_session_denied', 403);
  return value;
}
export function randomHex() { return Array.from(crypto.getRandomValues(new Uint8Array(32)), b => b.toString(16).padStart(2, '0')).join(''); }
export async function digest(value: string) {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))), b => b.toString(16).padStart(2, '0')).join('');
}
export async function readBoundedJson(response: Request | Response, maximum: number, signal?: AbortSignal) {
  if (!response.body) throw new RedDogError('public_json_invalid');
  const reader = response.body.getReader();
  const abort = () => { void reader.cancel().catch(() => {}); };
  signal?.addEventListener('abort', abort, { once: true });
  const chunks: Uint8Array[] = []; let size = 0;
  try {
    for (;;) {
      signal?.throwIfAborted();
      const { done, value } = await reader.read(); if (done) break;
      size += value.length;
      if (size > maximum) throw new RedDogError('public_body_too_large', 413);
      chunks.push(value);
    }
    signal?.throwIfAborted();
    const bytes = new Uint8Array(size); let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
    const text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    // Reject duplicate object keys before JSON.parse's last-value-wins behavior.
    const scopes: (Set<string> | null)[] = [];
    for (let i=0;i<text.length;i++) {
      const char=text[i];
      if (char === '{') scopes.push(new Set());
      else if (char === '[') scopes.push(null);
      else if (char === '}' || char === ']') scopes.pop();
      else if (char === '"') {
        const start=i;
        for (++i;i<text.length;i++) { if (text[i] === '\\') i++; else if (text[i] === '"') break; }
        let next=i+1; while (/\s/.test(text[next]??'') && next<text.length) next++;
        if (text[next] === ':') {
          const scope=scopes.at(-1), key=JSON.parse(text.slice(start,i+1));
          if (scope?.has(key)) throw new RedDogError('public_json_duplicate_key');
          scope?.add(key);
        }
      }
    }
    return JSON.parse(text);
  } finally { signal?.removeEventListener('abort', abort); await reader.cancel().catch(() => {}); }
}
