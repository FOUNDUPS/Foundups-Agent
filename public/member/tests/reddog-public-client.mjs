import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = await readFile(new URL('../../js/reddog-public-client.js', import.meta.url), 'utf8');
assert.equal(source, await readFile(new URL('../../../modules/foundups/esingularity/frontend/lib/reddog-public-client.js', import.meta.url), 'utf8'));
const { RedDogPublicClient, safeSources } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const answer = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
const session = { token: 'synthetic-public-token', nonce: 'one', revision: 0, remaining_turns: 10, expires_at: 2000, idle_expires_at: 1500 };
const calls = [];
let queue = [];
globalThis.fetch = async (url, options) => {
  calls.push({ operation: url.split('/').at(-1), body: JSON.parse(options.body), headers: options.headers });
  const next = queue.shift();
  if (!next) throw new Error('Unexpected request');
  if (next instanceof Error) throw next;
  return typeof next === 'function' ? await next() : next;
};
const client = new RedDogPublicClient('foundups');
queue = [answer(session)];
await client.start();
assert.deepEqual(calls[0].body, { consent: true, consent_version: 'reddog.public-guest.v1', actor_claim: 'unspecified' });
assert.equal(calls[0].headers.Authorization, undefined);

queue = [new Error('Lost after provider accepted'), answer({ ...session, revision: 1, nonce: 'two', remaining_turns: 9, in_flight: false })];
await assert.rejects(client.send('What is the project?'), (error) => error.code === 'uncertain');
assert.deepEqual(calls.map((call) => call.operation), ['encounter', 'turn', 'status']);
assert.equal(client.session.revision, 1);
assert.equal(client.needsStatus, false);

queue = [answer({ revision: 2, nonce: 'three', remaining_turns: 8, reply: 'A community proposal.' })];
await client.send('A new explicit question');
assert.equal(calls.at(-1).body.nonce, 'two');
assert.equal(calls.at(-1).body.revision, 1);
assert.equal(calls.at(-1).headers.Authorization, 'Bearer synthetic-public-token');

queue = [answer({}, 410)];
await assert.rejects(client.send('Expired question'), (error) => error.code === 'expired');
assert.equal(client.session, null);
const countAfterExpired = calls.length;
await assert.rejects(client.send('Cannot silently restart'), (error) => error.code === 'expired');
assert.equal(calls.length, countAfterExpired);

queue = [answer(session)];
await client.start();
let releaseTurn;
const waiting = new Promise((resolve) => { releaseTurn = resolve; });
queue = [() => waiting, answer({ withdrawn: true })];
const turn = client.send('Question in flight');
await client.end();
releaseTurn(answer({ revision: 1, nonce: 'late', remaining_turns: 9, reply: 'Must not display' }));
await assert.rejects(turn, (error) => error.code === 'ended');
assert.equal(client.session, null);
assert.equal(client.busy, false);

queue = [answer(session), new Error('Uncertain'), answer({ ...session, nonce: 'busy', revision: 1, remaining_turns: 9, in_flight: true })];
await client.start();
await assert.rejects(client.send('In flight'), (error) => error.code === 'uncertain');
assert.equal(client.needsStatus, true);
const countWhileBusy = calls.length;
await assert.rejects(client.send('Cannot resend while pending'), (error) => error.code === 'busy');
assert.equal(calls.length, countWhileBusy);
queue = [answer({ ...session, nonce: 'busy', revision: 1, remaining_turns: 9, in_flight: false })];
await client.check();
assert.equal(client.needsStatus, false);

assert.deepEqual(safeSources([{ title: 'bad', url: 'javascript:alert(1)' }, { title: 'Project', url: 'https://yumori.me' }]), [{ title: 'Project', url: 'https://yumori.me' }]);
console.log('PASS: consent, nonce continuation, no lost-turn replay, explicit restart, withdrawal suppresses late reply, in-flight recovery, HTTPS source links.');
