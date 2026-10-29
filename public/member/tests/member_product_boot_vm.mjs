/** Execute the actual member page boot and account script with controlled I/O.
 * Recovered implementation is revalidated here; these are fresh execution receipts.
 * Only dynamic imports are replaced with the test's module resolver. No account
 * function or admission/race decision is copied out of the production script.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const here = path.dirname(fileURLToPath(import.meta.url));
const html = fs.readFileSync(path.join(here, '../index.html'), 'utf8');
const require = createRequire(import.meta.url);
const search = require('../../move2japan/property-search.js');
const runtime = html.match(/<script type="module" id="memberRuntime">([\s\S]*?)<\/script>/)?.[1];
const boot = html.match(/<script id="productDiscoveryBoot">([\s\S]*?)<\/script>/)?.[1];
assert.ok(runtime && boot, 'the actual shared member script and product boot must exist');
const script = new vm.Script(runtime.replace(/\bimport\(/g, '__import('), { filename: 'member/index.html#memberRuntime' });
const ordinaryCatalog = [{ foundup_id: 'foundups', source_type: 'youtube' }, { foundup_id: 'move2japan', source_type: 'youtube' }];
const user = id => ({ id, firstName: id, primaryEmailAddress: { emailAddress: id + '@example.invalid' } });
const admitted = (username, extras = {}) => ({ inviteValidated: true, username, inviteCodes: [], ...extras });
const snapshot = data => ({ exists: () => data !== null, data: () => data });
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((a, b) => { resolve = a; reject = b; });
  return { promise, resolve, reject };
};
const flush = async () => { for (let i = 0; i < 8; i++) await new Promise(resolve => setImmediate(resolve)); };

function harness(options = {}) {
  let page = new URL(options.url || 'https://foundups.com/member/?foundup=move2japan');
  const location = {};
  for (const key of ['pathname', 'search', 'hash', 'hostname', 'origin']) {
    Object.defineProperty(location, key, { get: () => page[key] });
  }
  Object.defineProperty(location, 'href', {
    get: () => page.href, set: value => { page = new URL(value, page.href); },
  });
  const state = { imports: [], reads: [], writes: [], fetches: [], admissions: [], identities: [],
    foundups: [], invites: [], opens: 0, field: [], planes: [], redirects: [], consumes: 0, errors: [] };
  location.replace = value => state.redirects.push(value);
  const nodes = new Map();
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, { id, style: {}, textContent: '', innerHTML: '', hidden: false,
      value: '', listeners: [], classList: { add() {}, remove() {} },
      addEventListener(type, handler) { this.listeners.push({ type, handler }); } });
    return nodes.get(id);
  }
  const visibility = [];
  const document = { visibilityState: 'visible', body: { classList: { add() {}, remove() {} }, appendChild() {} },
    getElementById: node, createElement: () => node('temporary'),
    addEventListener(type, handler) { if (type === 'visibilitychange') visibility.push(handler); } };
  const storage = new Map(options.pendingCode ? [['pendingInviteCode', options.pendingCode]] : []);
  const localStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) };
  const listeners = [];
  const timers = [];
  const clerk = options.noClerk ? undefined : {
    user: options.user ?? null,
    load: options.clerkLoad || (() => Promise.resolve()),
    addListener(callback) { listeners.push(callback); },
  };
  const redDog = {
    setDiscoveryAdmission(value) {
      state.admissions.push(value);
      state.admitted = value;
      if (!value) { state.currentIdentity = null; state.currentInvites = []; }
    },
    setIdentity(account, data) { state.identities.push({ id: account.id, username: data.username }); state.currentIdentity = account.id; },
    setFoundUps(items) { state.foundups.push(items); },
    setInvites(items) { state.invites.push(items); state.currentInvites = items; },
    open() { state.opens++; }, close() {},
  };
  const win = { location, document, localStorage, Clerk: clerk, redDog,
    Move2JapanSearch: search, FOUNDUPS_CLERK_APPEARANCE: {},
    mallStateRestore: {
      consumeProductReturn() { state.consumes++; return options.productReturn || null; },
      restore() {}, bindAutoSave() {},
    },
    mallTileField: { initialize(items) { state.field.push(['initialize', items]); },
      expandFoundUp(index) { state.field.push(['expand', index]); } },
    mallPlanes: { setCatalog(items) { state.planes.push(items); } },
    addEventListener() {},
  };
  let fetchNumber = 0;
  const fetch = async (url, init) => {
    state.fetches.push({ url, init });
    const response = options.fetch ? await options.fetch(++fetchNumber, url) : null;
    return response || { ok: true, json: async () => ordinaryCatalog, headers: { get: () => null } };
  };
  const modules = {
    'https://www.gstatic.com/firebasejs/11.4.0/firebase-app.js': { initializeApp: () => ({}) },
    '/js/firebase-runtime-config.js': { loadFirebaseRuntimeConfig: async () => ({}) },
    'https://www.gstatic.com/firebasejs/11.4.0/firebase-firestore.js': {
      getFirestore: () => ({}), doc: (_, collection, id) => ({ collection, id }),
      getDoc: async ref => { state.reads.push(ref); return options.getDoc ? options.getDoc(ref) : snapshot(options.data ?? admitted(ref.id)); },
      setDoc: async (...args) => { state.writes.push(args); },
      collection: (_, name) => ({ name }), where: (field, op, value) => ({ field, op, value }),
      query: (collection, ...filters) => ({ collection, filters }),
      getDocs: async query => options.getDocs ? options.getDocs(query) : ({ empty: true, docs: [] }),
    },
  };
  const context = vm.createContext({ window: win, document, localStorage, fetch, URL, URLSearchParams,
    console: { log() {}, warn: (...args) => state.errors.push(args), error: (...args) => state.errors.push(args) },
    setTimeout(callback, ms) { timers.push({ callback, ms }); if (ms < 8000) queueMicrotask(callback); return timers.length; },
    clearTimeout() {},
    __import: async specifier => { state.imports.push(specifier); return modules[specifier]; },
  });
  script.runInContext(context);
  return { state, win, nodes, timers, storage, visibility,
    emit(account) { win.Clerk.user = account; listeners.forEach(callback => callback({ user: account })); },
  };
}

let passed = 0;
async function check(name, action) { await action(); passed++; process.stdout.write('PASS ' + name + '\n'); }

await check('actual product boot selects its state owner before mounting the shared shell', async () => {
  const calls = [];
  const win = { location: new URL('https://foundups.com/member/?foundup=move2japan'),
    Move2JapanSearch: { isShellProductRoute: search.isShellProductRoute, mount: (_, url) => calls.push(['mount', url]) },
    mallStateRestore: { selectProduct: id => calls.push(['select', id]) } };
  vm.runInNewContext(boot, { window: win });
  assert.deepEqual(calls, [['select', 'move2japan'], ['mount', '/move2japan/properties.json']]);
  win.location.search = '?creator=move2japan'; calls.length = 0;
  vm.runInNewContext(boot, { window: win });
  assert.deepEqual(calls, []);
});

await check('public houses remain independent of missing Clerk and Firebase', async () => {
  const h = harness({ noClerk: true }); await flush();
  assert.equal(h.state.imports.length, 0);
  assert.equal(h.state.writes.length, 0);
  assert.equal(h.state.field.length, 0);
  assert.equal(h.state.redirects.length, 0);
});

await check('a Clerk guest never imports account data modules', async () => {
  const h = harness(); await flush();
  assert.equal(h.state.imports.length, 0);
  assert.equal(h.state.reads.length, 0);
});

await check('rejected Clerk loading leaves the house field alone', async () => {
  const h = harness({ user: user('A'), clerkLoad: () => Promise.reject(new Error('SDK offline')) }); await flush();
  assert.equal(h.state.imports.length, 0);
  assert.equal(h.state.field.length, 0);
  assert.equal(h.state.errors.length, 1);
});

await check('the account wait is bounded without an auth gate over public houses', async () => {
  const h = harness({ user: user('A'), clerkLoad: () => new Promise(() => {}) });
  h.timers.find(timer => timer.ms === 8000).callback(); await flush();
  assert.equal(h.state.imports.length, 0);
  assert.equal(h.nodes.has('inviteGate'), false);
});

await check('real admitted accounts populate the existing controller without replacing house data', async () => {
  const h = harness({ user: user('A'), data: admitted('alpha') }); await flush();
  assert.deepEqual(h.state.identities, [{ id: 'A', username: 'alpha' }]);
  assert.equal(h.state.admitted, true);
  assert.equal(h.nodes.get('mallUserHandle').textContent, '@alpha');
  assert.equal(h.state.foundups[0], ordinaryCatalog);
  assert.equal(h.state.field.length, 0);
  assert.equal(h.state.planes.length, 0);
  assert.equal(h.state.writes.length, 0);
});

await check('an unadmitted account cannot consume a pending invite from house discovery', async () => {
  const h = harness({ user: user('A'), data: { username: 'alpha' }, pendingCode: 'PENDING-CODE' }); await flush();
  assert.equal(h.state.admitted, false);
  assert.equal(h.state.identities.length, 0);
  assert.equal(h.state.writes.length, 0);
  assert.equal(h.storage.get('pendingInviteCode'), 'PENDING-CODE');
  assert.equal(h.nodes.get('gateVerifyBtn')?.listeners.length || 0, 0);
});

await check('a blank username does not bypass the shared admission contract', async () => {
  const h = harness({ user: user('A'), data: admitted('   ') }); await flush();
  assert.equal(h.state.admitted, false);
  assert.equal(h.state.fetches.length, 0);
});

await check('existing used-invite admission remains compatible with the normal Mall', async () => {
  const h = harness({ user: user('A'), data: { usedInviteCode: 'EXISTING', username: 'alpha' } }); await flush();
  assert.equal(h.state.admitted, true);
});

await check('a missing account document never creates a new profile on public discovery', async () => {
  const h = harness({ user: user('A'), getDoc: () => snapshot(null) }); await flush();
  assert.equal(h.state.admitted, false);
  assert.equal(h.state.writes.length, 0);
});

await check('an account read failure leaves discovery in guest mode', async () => {
  const h = harness({ user: user('A'), getDoc: () => Promise.reject(new Error('offline')) }); await flush();
  assert.equal(h.state.admitted, false);
  assert.equal(h.state.identities.length, 0);
  assert.equal(h.state.writes.length, 0);
});

await check('missing invite records are unknown rather than active entitlements', async () => {
  const h = harness({ user: user('A'), data: admitted('alpha', { inviteCodes: ['MISSING', null] }) }); await flush();
  assert.equal(h.state.currentInvites.length, 1);
  assert.equal(h.state.currentInvites[0].code, 'MISSING');
  assert.equal(h.state.currentInvites[0].status, 'unknown');
});

await check('sign-out revokes identity before a pending invite lookup resolves', async () => {
  const inviteRead = deferred();
  const h = harness({ user: user('A'), data: admitted('alpha', { inviteCodes: ['CODE'] }), getDocs: () => inviteRead.promise }); await flush();
  assert.equal(h.state.currentIdentity, 'A');
  h.emit(null);
  assert.equal(h.state.admitted, false);
  inviteRead.resolve({ empty: false, docs: [{ data: () => ({ status: 'active' }) }] }); await flush();
  assert.equal(h.state.currentIdentity, null);
  assert.equal(h.state.currentInvites.length, 0);
  assert.equal(h.nodes.get('mallUserHandle').textContent, 'Foundups account');
});

await check('sign-out during the user read prevents late admission', async () => {
  const read = deferred();
  const h = harness({ user: user('A'), getDoc: () => read.promise }); await flush();
  h.emit(null); read.resolve(snapshot(admitted('alpha'))); await flush();
  assert.equal(h.state.admitted, false);
  assert.equal(h.state.identities.length, 0);
  assert.equal(h.state.fetches.length, 0);
});

await check('a slow previous account cannot overwrite the newly selected account', async () => {
  const old = deferred();
  const h = harness({ user: user('A'), getDoc: ref => ref.id === 'A' ? old.promise : snapshot(admitted('bravo')) }); await flush();
  h.emit(user('B')); await flush();
  assert.equal(h.state.currentIdentity, 'B');
  old.resolve(snapshot(admitted('alpha'))); await flush();
  assert.equal(h.state.currentIdentity, 'B');
  assert.equal(h.nodes.get('mallUserHandle').textContent, '@bravo');
  assert.deepEqual(h.state.identities, [{ id: 'B', username: 'bravo' }]);
});

await check('failure of a superseded account read cannot revoke the current account', async () => {
  const old = deferred();
  const h = harness({ user: user('A'), getDoc: ref => ref.id === 'A' ? old.promise : snapshot(admitted('bravo')) }); await flush();
  h.emit(user('B')); await flush();
  old.reject(new Error('old request failed')); await flush();
  assert.equal(h.state.currentIdentity, 'B');
  assert.equal(h.state.admitted, true);
  assert.equal(h.nodes.get('mallUserHandle').textContent, '@bravo');
});

await check('a late catalog response for the previous account cannot restore its identity', async () => {
  const old = deferred();
  const h = harness({ user: user('A'), fetch: number => number === 1 ? old.promise : null }); await flush();
  h.emit(user('B')); await flush();
  old.resolve({ ok: true, json: async () => ordinaryCatalog, headers: { get: () => null } }); await flush();
  assert.equal(h.state.currentIdentity, 'B');
  assert.deepEqual(h.state.identities, [{ id: 'B', username: 'B' }]);
});

await check('generation guards also reject stale reads for the same account ID', async () => {
  const old = deferred(); let reads = 0;
  const h = harness({ user: user('A'), getDoc: () => ++reads === 1 ? old.promise : snapshot(admitted('renamed')) }); await flush();
  h.visibility[0](); await flush();
  old.resolve(snapshot(admitted('oldname'))); await flush();
  assert.equal(h.nodes.get('mallUserHandle').textContent, '@renamed');
  assert.deepEqual(h.state.identities, [{ id: 'A', username: 'renamed' }]);
});

await check('the original ordinary Mall still sends guests through its sign-in gate', async () => {
  const h = harness({ url: 'https://foundups.com/member/' }); await flush();
  assert.equal(h.state.imports.length, 3);
  assert.equal(h.win.location.href, 'https://foundups.com/?signin=required');
  assert.equal(h.state.field.length, 0);
});

await check('the account return is consumed only after the normal admission gate succeeds', async () => {
  const h = harness({ url: 'https://foundups.com/member/?account=1', user: user('A'), data: admitted('alpha'),
    productReturn: '/member/?foundup=move2japan&city=Wakasa#account' }); await flush();
  assert.equal(h.state.consumes, 1);
  assert.deepEqual(h.state.redirects, ['/member/?foundup=move2japan&city=Wakasa#account']);
  assert.equal(h.state.field.length, 0);
  const guest = harness({ url: 'https://foundups.com/member/?account=1', user: user('A'), data: { username: 'alpha' },
    productReturn: '/member/?foundup=move2japan#account' }); await flush();
  assert.equal(guest.state.consumes, 0);
  assert.equal(guest.nodes.get('inviteGate').style.display, 'flex');
});

await check('the explicit videos entry expands the existing Move2Japan channel in the admitted Mall', async () => {
  const h = harness({ url: 'https://foundups.com/member/?creator=move2japan', user: user('A'), data: admitted('alpha') }); await flush();
  assert.equal(h.state.admissions.length, 0);
  assert.equal(h.state.field[0][0], 'initialize');
  assert.deepEqual(h.state.field[1], ['expand', 1]);
  assert.equal(h.state.planes.length, 1);
});

console.log(`${passed} actual member boot checks passed`);
