/** Real tab-activity owner; synthetic events only, with prohibited APIs trapped. */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';

const memberRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const source = readFileSync(join(memberRoot, 'js/mall-local-activity.js'), 'utf8');
const activityEvents = ['mallVideoPlayback', 'videoPlayerOpen', 'videoPlayerClose',
  'videoPlayerModeChange', 'videoPlayerTuck', 'videoPlayerSave', 'videoPlayerDismiss'];
const copy = value => JSON.parse(JSON.stringify(value));
let checks = 0;
function check(name, callback) { callback(); checks++; console.log('PASS ' + name); }

function runtime(snapshot = null) {
  const forbidden = [];
  const deny = name => () => { forbidden.push(name); throw Error('Forbidden activity side effect: ' + name); };
  const listeners = new Map();
  let snapshots = 0;
  const view = {
    addEventListener(name, callback) {
      if (!listeners.has(name)) listeners.set(name, new Set());
      listeners.get(name).add(callback);
    },
    removeEventListener(name, callback) { listeners.get(name)?.delete(callback); },
    mallVideoPlayer: { getPlaybackSnapshot() { snapshots++; return snapshot; } },
    fetch: deny('view.fetch'), WebSocket: deny('WebSocket'), Worker: deny('Worker'),
    navigator: { mediaDevices: { getUserMedia: deny('getUserMedia') }, sendBeacon: deny('sendBeacon') },
    localStorage: { getItem: deny('storage read'), setItem: deny('storage write') },
    setTimeout: deny('timer'), setInterval: deny('polling')
  };
  const context = { fetch: deny('fetch'), WebSocket: view.WebSocket, Worker: view.Worker,
    navigator: view.navigator, localStorage: view.localStorage,
    setTimeout: view.setTimeout, setInterval: view.setInterval };
  // Strip ESM export syntax only; execute the unchanged function bodies in a
  // bounded VM without DOM, network, media, persistence, model or timer owners.
  runInNewContext(source.replace(/^export /gm, ''), context, { timeout: 1000 });
  const api = context.createLocalActivityMonitor(view);
  return { api, view, forbidden, snapshots: () => snapshots,
    owner: () => context.createLocalActivityMonitor(view),
    count: name => listeners.get(name)?.size || 0,
    emit(name, detail) { for (const callback of [...(listeners.get(name) || [])]) callback({ type: name, detail }); } };
}

check('monitor is opt-in, has one owner per tab, and repeated enable never duplicates listeners', () => {
  const h = runtime({ videoId: 'HPC00000001', state: 'playing' });
  assert.equal(h.owner(), h.api);
  assert.equal(h.count('pagehide'), 1);
  assert.deepEqual(copy(h.api.getSnapshot()), { enabled: false, entries: [] });
  h.emit('mallVideoPlayback', { videoId: 'HPC00000001', state: 'playing' });
  assert.equal(h.api.getSnapshot().entries.length, 0);
  assert.equal(h.snapshots(), 0);
  h.api.setEnabled(true); h.api.setEnabled(true); h.api.setEnabled(true);
  assert.equal(h.snapshots(), 1);
  assert.equal(h.api.getSnapshot().entries.length, 1);
  for (const event of activityEvents) assert.equal(h.count(event), 1, event);
  h.api.setEnabled(false); h.api.setEnabled(false);
  for (const event of activityEvents) assert.equal(h.count(event), 0, event);
  assert.deepEqual(h.forbidden, []);
});

check('event values use a bounded field allowlist without invoking payload getters or serializers', () => {
  const h = runtime(); h.api.setEnabled(true);
  let getters = 0;
  const hostile = Object.create({ get videoId() { getters++; return 'HPC00000001'; } });
  for (const key of ['state', 'code', 'saved', 'privateText']) {
    Object.defineProperty(hostile, key, { enumerable: true, get() { getters++; throw Error('Payload getter'); } });
  }
  hostile.toJSON = () => { getters++; throw Error('Payload serializer'); };
  h.emit('mallVideoPlayback', hostile);
  h.emit('videoPlayerSave', { videoId: 'HPC00000001', state: 'paused', code: 153, saved: false,
    transcript: 'private fixture text', caption: 'discarded fixture caption', credential: 'discarded fixture value' });
  h.emit('videoPlayerOpen', { videoId: 'not-a-video-id', state: 'invented', code: 999, saved: 'true' });
  h.emit('unregistered-private-event', { videoId: 'HPC00000001' });
  const entries = copy(h.api.getSnapshot()).entries;
  assert.equal(getters, 0);
  assert.equal(entries.length, 3);
  assert.deepEqual(Object.keys(entries[0]).sort(), ['action', 'sequence', 'time']);
  assert.deepEqual(Object.keys(entries[1]).sort(), ['action', 'code', 'saved', 'sequence', 'state', 'time', 'videoId']);
  assert.equal(entries[1].saved, false);
  assert.equal(entries[1].code, 153);
  assert.deepEqual(Object.keys(entries[2]).sort(), ['action', 'sequence', 'time']);
  assert.equal(JSON.stringify(entries).includes('private fixture'), false);
  const canonicalStates = ['configuration', 'playback-error', 'client-identification',
    'timeout', 'continuity-unavailable', 'provider-state'];
  for (const state of canonicalStates) h.emit('mallVideoPlayback', { videoId: 'HPC00000001', state });
  assert.deepEqual(copy(h.api.getSnapshot()).entries.slice(3).map(entry => entry.state), canonicalStates,
    'Canonical provider failures must remain distinct in the local activity feed');
  assert.deepEqual(h.forbidden, []);
});

check('repeated playback snapshots deduplicate while changed state remains observable', () => {
  const h = runtime(); h.api.setEnabled(true);
  for (let i = 0; i < 25; i++) h.emit('mallVideoPlayback', {
    videoId: 'HPC00000001', state: 'playing', positionSeconds: i, providerPayload: { i }
  });
  assert.equal(h.api.getSnapshot().entries.length, 1);
  h.emit('mallVideoPlayback', { videoId: 'HPC00000001', state: 'paused' });
  h.emit('mallVideoPlayback', { videoId: 'HPC00000001', state: 'playing' });
  assert.deepEqual(copy(h.api.getSnapshot()).entries.map(e => e.state), ['playing', 'paused', 'playing']);
  assert.deepEqual(copy(h.api.getSnapshot()).entries.map(e => e.sequence), [1, 2, 3]);
  assert.deepEqual(h.forbidden, []);
});

check('history retains at most100 entries and consumers cannot mutate retained data', () => {
  const h = runtime(); h.api.setEnabled(true);
  for (let i = 0; i < 125; i++) h.emit('videoPlayerOpen', { videoId: 'HPC00000001' });
  const snapshot = h.api.getSnapshot();
  assert.equal(snapshot.entries.length, 100);
  assert.equal(snapshot.entries[0].sequence, 26);
  assert.equal(snapshot.entries.at(-1).sequence, 125);
  snapshot.entries[0].videoId = 'altered'; snapshot.entries.length = 0;
  assert.equal(h.api.getSnapshot().entries.length, 100);
  assert.equal(h.api.getSnapshot().entries[0].videoId, 'HPC00000001');
  h.api.clear();
  assert.equal(h.api.getSnapshot().enabled, true);
  assert.equal(h.api.getSnapshot().entries.length, 0);
  h.emit('mallVideoPlayback', { videoId: 'HPC00000001', state: 'playing' });
  assert.equal(h.api.getSnapshot().entries.length, 1);
  assert.deepEqual(h.forbidden, []);
});

check('pagehide detaches activity listeners; explicit re-enable remains single and bounded', () => {
  const h = runtime(); h.api.setEnabled(true);
  h.emit('videoPlayerOpen', { videoId: 'HPC00000001' });
  h.emit('pagehide', {});
  assert.equal(h.api.getSnapshot().enabled, false);
  for (const event of activityEvents) assert.equal(h.count(event), 0, event);
  h.emit('mallVideoPlayback', { videoId: 'HPC00000001', state: 'playing' });
  assert.equal(h.api.getSnapshot().entries.length, 1);
  h.api.setEnabled(true); h.api.setEnabled(true);
  for (const event of activityEvents) assert.equal(h.count(event), 1, event);
  assert.equal(h.count('pagehide'), 1);
  h.emit('videoPlayerClose', {});
  assert.equal(h.api.getSnapshot().entries.length, 2);
  assert.deepEqual(h.forbidden, []);
});

check('subscription snapshots are isolated and unsubscribe stops delivery', () => {
  const h = runtime(); const good = [];
  const off = h.api.subscribe(value => good.push(copy(value)));
  h.api.subscribe(value => { if (value.enabled) throw Error('Consumer failure'); });
  h.api.setEnabled(true);
  h.emit('videoPlayerOpen', { videoId: 'HPC00000001' });
  assert.equal(good.at(-1).entries.length, 1);
  good.at(-1).entries[0].videoId = 'changed';
  assert.equal(h.api.getSnapshot().entries[0].videoId, 'HPC00000001');
  const calls = good.length; off(); off();
  h.api.clear(); h.api.setEnabled(false);
  assert.equal(good.length, calls);
  assert.deepEqual(h.forbidden, []);
});

console.log(JSON.stringify({ checks, real_browser: 'UNEXECUTED', microphone: 'UNEXECUTED',
  model: 'UNEXECUTED', network_or_storage_calls: 0, synthetic_events_only: true }));
