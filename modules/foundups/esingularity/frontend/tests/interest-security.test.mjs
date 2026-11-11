import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { existsSync } from 'node:fs';
import { createInterestHandler } from '../lib/interest.ts';
import * as schema from '../db/schema.ts';
import { publicTeamProfiles } from '../lib/team.ts';
const valid = { name: 'Test', email: 'TEST@example.test', relationship: 'その他', story: '', consent: 'yes' };
const req = (body = valid, headers = {}) => new Request('https://esingularity.ai/api/interest', { method: 'POST', headers: { 'content-type': 'application/json', ...headers }, body: typeof body === 'string' ? body : JSON.stringify(body) });
test('valid request normalizes data, trusts only Cloudflare ingress IP, and is not cached', async () => {
  let input, client;
  const handler = createInterestHandler(async (i, c) => { input = i; client = c; return true; });
  const res = await handler(req(valid, { 'x-forwarded-for': 'spoofed' }));
  assert.equal(res.status, 201); assert.equal(res.headers.get('cache-control'), 'no-store');
  assert.equal(input.email, 'test@example.test'); assert.equal(client, 'unknown');
});
test('rejects malformed, oversized, invalid and cross-origin requests before storage', async () => {
  let calls = 0; const handler = createInterestHandler(async () => { calls++; return true; });
  for (const [r, code] of [[req('{'), 400], [req('null'), 400], [req('[]'), 400], [req({ ...valid, consent: 'no' }), 400], [req(valid, { origin: 'https://attacker.test' }), 403], [req(valid, { 'content-type': 'text/plain' }), 415], [req(valid, { 'content-length': '999999' }), 413], [req(' '.repeat(8193)), 413]]) assert.equal((await handler(r)).status, code);
  assert.equal(calls, 0);
});
test('actual streamed bytes are bounded even when Content-Length is a lie', async () => {
  let cancelled = false;
  const stream = new ReadableStream({ pull(c) { c.enqueue(new Uint8Array(5000)); }, cancel() { cancelled = true; } });
  const r = new Request('https://esingularity.ai/api/interest', { method: 'POST', headers: { 'content-type': 'application/json', 'content-length': '1' }, body: stream, duplex: 'half' });
  const response = await createInterestHandler(async () => { throw Error('must not store'); })(r);
  assert.equal(response.status, 413); assert.equal(cancelled, true);
});
test('honeypot avoids storage; rate limit and storage failures cannot report success', async () => {
  let calls = 0;
  assert.equal((await createInterestHandler(async () => { calls++; return true; })(req({ ...valid, website: 'bot' }))).status, 200);
  assert.equal(calls, 0);
  const limited = await createInterestHandler(async () => false)(req());
  assert.equal(limited.status, 429); assert.equal(limited.headers.get('retry-after'), '3600');
  const failed = await createInterestHandler(async () => { throw Error('private DB details'); })(req());
  assert.equal(failed.status, 503); assert.doesNotMatch(await failed.text(), /private DB/);
});
function database() {
  const db = new DatabaseSync(':memory:');
  for (const sql of [schema.createInterestTable, schema.createInterestCreatedIndex, schema.createInterestAdmissionTable, schema.createInterestAdmissionTimeIndex, schema.createInterestAdmissionClientIndex, schema.createInterestEmailIndex]) db.exec(sql);
  return db;
}
function submit(db, client, email, epoch = 2000000000, previousClient = client) {
  const id = crypto.randomUUID();
  db.exec('BEGIN');
  try {
    const result = db.prepare(schema.insertInterestWithLimits).run(id, 'Test', email, 'その他', null, new Date(epoch * 1000).toISOString(), new Date((epoch - 86400) * 1000).toISOString(), epoch - 3600, client, previousClient);
    db.prepare(schema.insertInterestAdmission).run(id, client, epoch);
    db.prepare(schema.pruneInterestAdmission).run(epoch - 3600);
    db.exec('COMMIT');
    return result.changes;
  } catch (error) { db.exec('ROLLBACK'); throw error; }
}
test('real SQL enforces five per client/hour, deduplication and recovery after expiry', () => {
  const db = database();
  assert.equal(submit(db, 'client', 'first@example.test'), 1);
  assert.equal(submit(db, 'other', 'first@example.test'), 0);
  for (let i = 0; i < 4; i++) assert.equal(submit(db, 'client', `${i}@example.test`), 1);
  assert.equal(submit(db, 'client', 'blocked@example.test'), 0);
  assert.equal(db.prepare('SELECT count(*) AS n FROM community_interest_admission').get().n, 5);
  assert.equal(submit(db, 'client', 'later@example.test', 2000003601), 1);
  assert.equal(db.prepare('SELECT count(*) AS n FROM community_interest_admission').get().n, 1);
  db.close();
});
test('global quota stops rotating clients at 100/hour and retains existing submissions', () => {
  const db = database();
  for (let i = 0; i < 100; i++) assert.equal(submit(db, `client-${i}`, `${i}@example.test`), 1);
  assert.equal(submit(db, 'new', 'blocked@example.test'), 0);
  assert.equal(db.prepare('SELECT count(*) AS n FROM community_interest').get().n, 100);
  db.close();
});
test('published profiles retain assets; unpublished portraits are outside public root', () => {
  for (const p of publicTeamProfiles) for (const src of [p.image, ...p.gallery.map(x => x.src)]) assert.equal(existsSync(new URL(`../public${src}`, import.meta.url)), true, src);
  for (const name of ['hasegawa', 'brock-pierce', 'global-network', 'japan-network', 'world-blockchain-summit']) for (const suffix of ['.jpg', '-private.png']) assert.equal(existsSync(new URL(`../public/team/${name}${suffix}`, import.meta.url)), false);
});

test('daily key rotation retains previous-day quota within the rolling hour', () => {
  const db = database();
  for (let i = 0; i < 5; i++) assert.equal(submit(db, 'yesterday-key', `${i}@example.test`), 1);
  assert.equal(submit(db, 'today-key', 'new@example.test', 2000000010, 'yesterday-key'), 0);
  assert.equal(submit(db, 'today-key', 'new@example.test', 2000003601, 'yesterday-key'), 1);
  db.close();
});
