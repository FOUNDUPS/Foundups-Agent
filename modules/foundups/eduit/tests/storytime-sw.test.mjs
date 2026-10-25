import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {test} from 'node:test';

const template = fs.readFileSync(new URL('../../../../public/eduit/storytime-sw.js', import.meta.url), 'utf8');
const origin = 'https://storytime.eduit.org';
const shell = ['/storytime/', '/manifest.json', '/revisions/1234567890abcdef/storytime/game.js'];
function worker(host = origin) {
  const events = {}, cacheNames = ['pfmall-member-v5', 'eduit-storytime-old', 'eduit-storytime-previous', 'eduit-storytime-1234567890abcdef'];
  const added = [], removed = [], fetched = [], messages = [];
  let skipped = 0;
  const self = {location: {origin: host}, addEventListener: (name, callback) => {events[name] = callback;}, skipWaiting: () => {skipped++;}};
  const context = {self, URL, Response, fetch: async (...args) => {fetched.push(args); return 'network';}, caches: {
    keys: async () => cacheNames,
    open: async () => ({addAll: async paths => {added.push(...paths);}, match: async key => 'cached:' + key}),
    delete: async key => {removed.push(key);}
  }};
  vm.runInNewContext(template.replaceAll('__STORYTIME_REVISION__', '1234567890abcdef')
    .replace('__STORYTIME_PWA_ORIGINS__', JSON.stringify([origin]))
    .replace('__STORYTIME_SHELL_ASSETS__', JSON.stringify(shell)), context);
  const fetchEvent = (path, options = {}) => {
    let result;
    events.fetch({request: {url: new URL(path, host).href, method: options.method || 'GET',
      mode: options.mode || 'cors', headers: new Headers(options.headers)}, respondWith: value => {result = value;}});
    return result;
  };
  return {events, added, removed, fetched, fetchEvent, get skipped() {return skipped;}};
}

test('installation is bounded and never forces activation', async () => {
  const scope = worker();
  let done;
  scope.events.install({waitUntil: work => {done = work;}});
  await done;
  assert.deepEqual(scope.added, shell);
  assert.equal(scope.skipped, 0);
  scope.events.activate({waitUntil: work => {done = work;}});
  await done;
  assert.deepEqual(scope.removed, ['eduit-storytime-old']);
});

test('root worker is inert on shared FoundUps and unapproved origins', async () => {
  const scope = worker('https://foundups.com');
  let called = false;
  scope.events.install({waitUntil: () => {called = true;}});
  assert.equal(called, false);
  assert.equal(scope.fetchEvent('/storytime/', {mode: 'navigate'}), undefined);
});

test('only fixed public shell is intercepted; ranges, video, auth, APIs and queries use the network', async () => {
  const scope = worker();
  for (const path of ['/api/child-records', '/sso-callback/', '/review/', '/member/', '/unknown.js',
    '/revisions/1234567890abcdef/storytime/assets/little-shrew.mp4', '/manifest.json?account=private',
    'https://another.example/manifest.json']) assert.equal(scope.fetchEvent(path), undefined, path);
  assert.equal(scope.fetchEvent(shell[2], {headers: {Range: 'bytes=0-99'}}), undefined);
  assert.equal(scope.fetchEvent('/manifest.json', {method: 'POST'}), undefined);
  assert.equal(await scope.fetchEvent('/storytime/', {mode: 'navigate'}), 'cached:/storytime/');
  assert.equal(await scope.fetchEvent('/storytime/index.html', {mode: 'navigate'}), 'cached:/storytime/');
  assert.equal(scope.fetched.length, 0);
});

test('activation requires explicit message from an exact same-origin episode client', () => {
  const scope = worker();
  scope.events.message({data: {type: 'STORYTIME_ACTIVATE'}, source: {url: 'https://attacker.example/storytime/'}});
  scope.events.message({data: {type: 'STORYTIME_ACTIVATE'}, source: {url: origin + '/review/'}});
  scope.events.message({data: {type: 'OTHER'}, source: {url: origin + '/storytime/'}});
  assert.equal(scope.skipped, 0);
  scope.events.message({data: {type: 'STORYTIME_ACTIVATE'}, source: {url: origin + '/storytime/'}});
  assert.equal(scope.skipped, 1);
});

test('offline root navigation redirects to the bound episode using an absolute URL', async () => {
  const response = await worker().fetchEvent('/', {mode: 'navigate'});
  assert.equal(response.status, 302);
  assert.equal(response.headers.get('location'), origin + '/storytime/');
});
