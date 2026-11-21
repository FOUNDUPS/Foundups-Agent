/** Actual shared state owner in a bounded Node VM; no provider/auth/network claims. */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const source = readFileSync(join(root, 'js/mall-state-restore.js'), 'utf8');
const INTENT = 'pfmall_admission_intent_v1';
const OPTIONS = 'pfmall_video_options_v1';
const TTL = 15 * 60 * 1000;
const copy = value => JSON.parse(JSON.stringify(value));
const defaults = { autoplayNext: true, frameDestination: 'wikitube', collapseDestination: 'mall', revealSelectedPlayer: true };
let checks = 0;
function check(name, fn) { fn(); checks++; console.log('PASS ' + name); }

function runtime({ href = 'https://play.foundups.com/member/?foundup=hpc#account', local = new Map(), session = new Map() } = {}) {
  let now = 1000000;
  const writes = [], events = {};
  const blocked = { local: {}, session: {} };
  const storage = (map, kind) => ({
    getItem(key) { if (blocked[kind].get) throw Error('blocked'); return map.get(key) ?? null; },
    setItem(key, value) { if (blocked[kind].set) throw Error('blocked'); writes.push(key); map.set(key, value); },
    removeItem(key) { if (blocked[kind].remove) throw Error('blocked'); map.delete(key); }
  });
  const wrapper = { scrollTop: 91, scrollLeft: 0 };
  const window = {
    location: new URL(href),
    addEventListener(kind, callback) { (events[kind] ||= []).push(callback); },
    mallTileField: {
      getProjection: () => 'default', getLayoutMode: () => 'grid', getRowOffsets: () => ({}),
      getFieldScope: () => ({ type: 'query', query: 'saved browse' }),
      getActiveVideo: () => ({ foundupId: 'hpc', videoId: 'abcDEF_12-3', queueQuery: '' })
    }
  };
  const document = {
    querySelector(selector) { return selector === '#mallTileField' ? { parentElement: wrapper } : wrapper; },
    addEventListener() {}, visibilityState: 'visible'
  };
  runInNewContext(source, { window, document, URL, URLSearchParams, Date: { now: () => now },
    localStorage: storage(local, 'local'), sessionStorage: storage(session, 'session'),
    setTimeout() {}, clearTimeout() {}, requestAnimationFrame() {} });
  return { api: window.mallStateRestore, local, session, writes, blocked,
    time(value) { now = value; }, fire(event) { for (const fn of events.storage || []) fn(event); } };
}

check('typed intent saves browse state first and never grants authority', () => {
  const h = runtime();
  assert.equal(h.api.rememberAdmissionIntent({ action: 'add-video', foundupId: 'hpc', videoId: 'abcDEF_12-3' }), true);
  assert.ok(h.writes.indexOf('pfmall_mall_state_v1') < h.writes.indexOf(INTENT));
  assert.deepEqual(copy(h.api.peekAdmissionIntent()), {
    version: 1, createdAt: 1000000, action: 'add-video', foundupId: 'hpc', videoId: 'abcDEF_12-3', returnPath: '/member/?foundup=hpc#account'
  });
  const snapshot = h.api.peekAdmissionIntent(); snapshot.action = 'account';
  assert.equal(h.api.peekAdmissionIntent().action, 'add-video');
  assert.equal('capabilities' in h.api.peekAdmissionIntent(), false);
  assert.equal(h.api.rememberAdmissionIntent({ action: 'add-video', foundupId: 'hpc' }), true, 'new-video intent needs no existing clip');
});

check('peek does not renew expiry; consume is single use', () => {
  const h = runtime();
  assert.equal(h.api.rememberAdmissionIntent({ action: 'account' }), true);
  h.time(1000000 + TTL - 1);
  assert.equal(h.api.peekAdmissionIntent().createdAt, 1000000);
  assert.equal(h.api.consumeAdmissionIntent().action, 'account');
  assert.equal(h.api.consumeAdmissionIntent(), null);
  assert.equal(h.session.has(INTENT), false);
});

check('owner timestamps, malformed records, future times and exact expiry reject', () => {
  const h = runtime(); h.api.rememberAdmissionIntent({ action: 'account' });
  const valid = JSON.parse(h.session.get(INTENT));
  for (const patch of [{ createdAt: 1000001 }, { createdAt: 1000000 - TTL }, { createdAt: '1000000' },
    { version: 2 }, { returnPath: null }, { returnPath: 'https://other.example/member/' }, { capabilities: null }]) {
    h.session.set(INTENT, JSON.stringify({ ...valid, ...patch }));
    assert.equal(h.api.peekAdmissionIntent(), null);
    assert.equal(h.api.consumeAdmissionIntent(), null);
    assert.equal(h.session.has(INTENT), false);
  }
  for (const raw of ['{', 'null', '[]', ' '.repeat(2049)]) {
    h.session.set(INTENT, raw); assert.equal(h.api.peekAdmissionIntent(), null);
  }
});

check('unknown fields, inherited objects, accessors and prototype IDs reject atomically', () => {
  const h = runtime(); h.api.rememberAdmissionIntent({ action: 'account' });
  const before = h.session.get(INTENT); let getters = 0;
  const accessor = { get action() { getters++; return 'account'; } };
  for (const value of [null, [], { action: 'publish' }, { action: 'add-video' }, { action: 'account', capabilities: null },
    { action: 'account', authenticated: true }, { action: 'account', createdAt: 1 }, { action: 'account', foundupId: '__proto__' },
    { action: 'account', foundupId: 'constructor' }, { action: 'account', foundupId: 'HPC' },
    { action: 'add-video', foundupId: 'hpc', videoId: 'short' }, Object.create({ action: 'account' }), accessor,
    { action: 'account', [Symbol('authority')]: true }, JSON.parse('{"action":"account","__proto__":{}}')]) {
    assert.equal(h.api.rememberAdmissionIntent(value), false);
    assert.equal(h.session.get(INTENT), before);
  }
  assert.equal(getters, 0);
  const oddPrototype = Object.create(null);
  Object.defineProperty(oddPrototype, 'constructor', { get() { getters++; return Object; } });
  Object.defineProperty(oddPrototype, 'action', { get() { getters++; return 'account'; } });
  assert.equal(h.api.rememberAdmissionIntent(Object.create(oddPrototype)), false);
  assert.equal(h.api.rememberAdmissionIntent({}), false);
  assert.equal(getters, 0, 'prototype accessors must not execute');
});

check('relative public views allow exact paths; redirects and ambiguous paths reject', () => {
  const h = runtime();
  for (const path of ['/member', '/member/', '/member/index.html', '/member/?foundup=hpc#red-dog', '/member/?creator=move2japan']) {
    assert.equal(h.api.rememberAdmissionIntent({ action: 'account', returnPath: path }), true, path);
    assert.equal(h.api.peekAdmissionIntent().returnPath, path);
  }
  for (const path of ['https://play.foundups.com/member/', '//other.example/member/', '/member/../sso-callback/',
    '/member//', '/member/\\evil', '/%6dember/', '/member/?signin=required', '/member/?enter=hpc',
    '/member/?next=https://other.example', '/member/?foundup=hpc&foundup=hpc', '/member/?foundup=hpc&creator=move2japan',
    '/member/?foundup=__proto__', '/member/?foundup=hpc%00', '/member/#%61ccount', '/member/#signin', '/member/\n']) {
    assert.equal(h.api.rememberAdmissionIntent({ action: 'account', returnPath: path }), false, path);
  }
  assert.equal(h.api.rememberAdmissionIntent({ action: 'add-video', foundupId: 'hpc', returnPath: '/member/?foundup=move2japan' }), false);
  assert.equal(runtime({ href: 'https://play.foundups.com/sso-callback/' }).api.rememberAdmissionIntent({ action: 'account' }), false);
});

check('intent persists across same-tab runtimes and consumption fails closed on removal error', () => {
  const first = runtime(); first.api.rememberAdmissionIntent({ action: 'account' });
  const second = runtime({ session: first.session });
  assert.equal(second.api.consumeAdmissionIntent().action, 'account');
  assert.equal(first.api.peekAdmissionIntent(), null);
  first.api.rememberAdmissionIntent({ action: 'account' });
  first.blocked.session.remove = true;
  assert.equal(first.api.consumeAdmissionIntent(), null);
  assert.equal(first.api.peekAdmissionIntent(), null);
});

check('a failed read cannot consume a persistent intent through memory and replay it', () => {
  const first = runtime(); first.api.rememberAdmissionIntent({ action: 'account' });
  first.blocked.session.get = true;
  assert.equal(first.api.peekAdmissionIntent(), null);
  assert.equal(first.api.consumeAdmissionIntent(), null);
  const second = runtime({ session: first.session });
  assert.equal(second.api.consumeAdmissionIntent(), null);
});

check('blocked persistent intent writes refuse the handoff instead of claiming a memory-only return', () => {
  const h = runtime(); h.api.rememberAdmissionIntent({ action: 'account' });
  h.blocked.session.set = true;
  assert.equal(h.api.rememberAdmissionIntent({ action: 'add-foundup' }), false);
  assert.equal(h.api.peekAdmissionIntent(), null);
  assert.equal(h.api.consumeAdmissionIntent(), null);
  assert.equal(h.session.has(INTENT), false);
  h.blocked.session.get = true;
  assert.equal(h.api.rememberAdmissionIntent({ action: 'account' }), false);
  assert.equal(h.api.consumeAdmissionIntent(), null);
});

check('video defaults preserve current WikiTube expansion and persist valid patches', () => {
  const h = runtime(); assert.deepEqual(copy(h.api.getVideoOptions()), defaults);
  assert.equal(h.api.setVideoOptions({ autoplayNext: false, frameDestination: 'full-video' }), true);
  const options = { ...defaults, autoplayNext: false, frameDestination: 'full-video' };
  assert.deepEqual(copy(h.api.getVideoOptions()), options);
  assert.deepEqual(copy(runtime({ local: h.local }).api.getVideoOptions()), options);
  const snapshot = h.api.getVideoOptions(); snapshot.collapseDestination = 'wikitube';
  assert.equal(h.api.getVideoOptions().collapseDestination, 'mall');
});

check('invalid preference patches reject atomically without authority flags or getters', () => {
  const h = runtime(); h.api.setVideoOptions({ collapseDestination: 'wikitube' });
  const before = h.local.get(OPTIONS); let getters = 0;
  for (const patch of [null, [], { autoplayNext: 'false' }, { revealSelectedPlayer: 1 }, { frameDestination: 'native' },
    { collapseDestination: 'account' }, { capabilities: null }, { editor: true }, Object.create({ autoplayNext: false }),
    { get autoplayNext() { getters++; return false; } }, JSON.parse('{"__proto__":{}}')]) {
    assert.equal(h.api.setVideoOptions(patch), false); assert.equal(h.local.get(OPTIONS), before);
  }
  assert.equal(getters, 0);
});

check('blocked preference reads or writes retain validated memory', () => {
  for (const mode of ['get', 'set']) {
    const h = runtime(); h.blocked.local[mode] = true;
    assert.equal(h.api.setVideoOptions({ autoplayNext: false, revealSelectedPlayer: false }), true);
    assert.equal(h.api.getVideoOptions().autoplayNext, false);
    assert.equal(h.api.getVideoOptions().revealSelectedPlayer, false);
  }
});

check('subscriptions isolate snapshots/errors and unsubscribe is idempotent', () => {
  const h = runtime(); const calls = [], isolated = [];
  const off = h.api.subscribeVideoOptions(value => { calls.push(copy(value)); value.autoplayNext = true; });
  const bad = h.api.subscribeVideoOptions(() => { throw Error('consumer'); });
  h.api.subscribeVideoOptions(value => isolated.push(copy(value)));
  assert.equal(h.api.subscribeVideoOptions(null), null);
  h.api.setVideoOptions({ autoplayNext: false }); assert.equal(calls.length, 1);
  assert.equal(isolated[0].autoplayNext, false);
  h.api.setVideoOptions({ autoplayNext: false }); assert.equal(calls.length, 1);
  off(); off(); bad(); h.api.setVideoOptions({ revealSelectedPlayer: false });
  assert.equal(calls.length, 1); assert.equal(h.api.getVideoOptions().autoplayNext, false);
});

check('bounded storage events accept only versioned preference data', () => {
  const h = runtime(); let calls = 0; h.api.subscribeVideoOptions(() => calls++);
  for (const raw of ['{', ' '.repeat(1025), JSON.stringify({ version: 2, options: defaults }),
    JSON.stringify({ version: 1, options: { ...defaults, capabilities: null } })]) {
    h.fire({ key: OPTIONS, newValue: raw });
  }
  h.fire({ key: INTENT, newValue: null }); assert.equal(calls, 0);
  const raw = JSON.stringify({ version: 1, options: { ...defaults, autoplayNext: false } });
  h.local.set(OPTIONS, raw); h.fire({ key: OPTIONS, newValue: raw });
  assert.equal(calls, 1); assert.equal(h.api.getVideoOptions().autoplayNext, false);
});

console.log(JSON.stringify({ checks, real_auth: 'UNEXECUTED', graph_runtime_imported: false, writes_or_publication: false }));
