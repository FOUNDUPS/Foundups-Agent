'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const zlib = require('node:zlib');
const fs = require('node:fs');
const path = require('node:path');
const { Readable } = require('node:stream');
const { publish, sha256, jsonBytes, normalizeVersion, uploadWithClient } = require('../publish_hpc_catalog.cjs');
const NOW = Date.parse('2026-11-25T03:00:00Z');
const oldVersion = normalizeVersion('sites/foundupscom/versions/12345678');
const newVersion = normalizeVersion('sites/foundupscom/versions/87654321');
const first = { video_id: 'iJuguXpbRR4', title: 'Existing title', source_label: 'Move2Japan', editorial_label: 'Satire',
  source_url: 'https://www.youtube.com/shorts/iJuguXpbRR4', embed_url: 'https://www.youtube.com/embed/iJuguXpbRR4' };
const added = { ...first, video_id: '8qO3908bKAM', title: 'HasanAbi 4 House Speaker', editorial_label: 'Opinion',
  source_url: 'https://www.youtube.com/watch?v=8qO3908bKAM', embed_url: 'https://www.youtube.com/embed/8qO3908bKAM' };
function fixture(existingMetadata = {}) {
  const old = { other: { important: true }, hpc: { disclosure: 'live disclosure', credit: 'Creator',
    lane: { foundup_id: 'hpc', videos: [{ ...first, ...existingMetadata }], video_count: 1, poster_url: 'live poster', metadata: 'preserve' } } };
  const next = { other: { shouldNotPublish: true }, hpc: { disclosure: 'stale local disclosure',
    lane: { foundup_id: 'hpc', videos: [first, added], video_count: 2 } } };
  const paths = ['/member/mall-public-video-catalog.json', '/member/hpc-v25/mall-public-video-catalog.json'];
  let liveVersion = oldVersion, release = 'projects/p/sites/foundupscom/channels/live/releases/1';
  const config = { headers: [{ glob: '**', headers: { 'Referrer-Policy': 'strict-origin-when-cross-origin' } }], redirects: [{ location: '/member/hpc-v25/', statusCode: 302 }] };
  const bodies = new Map(paths.map(p => [p, jsonBytes(old)]));
  const initial = Object.fromEntries([...bodies].map(([p, b]) => [p, sha256(zlib.gzipSync(b, { level: 9 }))]));
  initial['/member/hpc-v25/js/player.js'] = 'a'.repeat(64);
  initial['/vote/index.html'] = 'b'.repeat(64);
  const versions = new Map([[oldVersion, { name: oldVersion, status: 'FINALIZED', config, files: { ...initial } }]]);
  const uploads = new Map(), writes = [];
  const files = version => Object.entries(versions.get(version).files).map(([path, hash]) => ({ path, hash, status: 'ACTIVE' }));
  const host = {
    getLive: async () => ({ release: { name: release, version: { name: liveVersion } } }),
    getVersion: async v => structuredClone(versions.get(v)), listFiles: async v => files(v),
    readPublic: async p => bodies.get(p),
    clone: async v => { writes.push('clone'); versions.set(newVersion, { ...structuredClone(versions.get(v)), name: newVersion, status: 'CREATED' }); return newVersion; },
    populate: async (v, changes) => { writes.push('populate'); Object.assign(versions.get(v).files, changes); return { uploadRequiredHashes: [...new Set(Object.values(changes))], uploadUrl: 'safe-mock' }; },
    upload: async (v, url, hash, bytes) => { writes.push('upload'); assert.equal(sha256(bytes), hash); uploads.set(hash, zlib.gunzipSync(bytes)); },
    finalize: async (v, c) => { writes.push('finalize'); assert.deepEqual(c, config); versions.get(v).status = 'FINALIZED'; },
    release: async v => { writes.push('release'); liveVersion = v; release = 'projects/p/sites/foundupscom/channels/live/releases/2';
      for (const p of paths) bodies.set(p, uploads.get(versions.get(v).files[p])); }
  };
  const catalogBytes = jsonBytes(next);
  const options = { sourceSha: 'c'.repeat(40), catalogBytes, apply: true, now: () => NOW,
    refreshReceipt: { schema_version: 'hpc_youtube_refresh.v1', scope: 'hpc', complete: true,
      source_channel_id: 'UC-LSSlOZwpGIRIYihaz8zCw', checked_at: '2026-11-25T02:59:00Z',
      expires_at: '2026-11-25T08:59:00Z', catalog_sha256: sha256(catalogBytes),
      eligible_ids: [first.video_id, added.video_id], excluded: [] } };
  return { host, options, old, next, bodies, versions, writes, paths, initial, config };
}
test('dry run plans both deployed catalog paths without any cloud writes', async () => {
  const f = fixture(); f.options.apply = false; const result = await publish(f.options, f.host);
  assert.equal(result.status, 'PLANNED'); assert.deepEqual(result.paths.map(p => p.path).sort(), f.paths.sort()); assert.deepEqual(f.writes, []);
});
test('publication appends regular video and preserves production metadata, unrelated bytes and config', async () => {
  const f = fixture(); const result = await publish(f.options, f.host); assert.equal(result.status, 'PUBLISHED');
  assert.equal(result.rollback_version, oldVersion); assert.equal(result.applied, true);
  for (const p of f.paths) {
    const delivered = JSON.parse(f.bodies.get(p)); assert.deepEqual(delivered.other, f.old.other);
    assert.equal(delivered.hpc.disclosure, f.old.hpc.disclosure); assert.equal(delivered.hpc.lane.poster_url, 'live poster');
    assert.deepEqual(delivered.hpc.lane.videos, [first, added]); assert.equal(delivered.hpc.lane.video_count, 2);
  }
  assert.equal(f.versions.get(newVersion).files['/vote/index.html'], f.initial['/vote/index.html']);
  assert.equal(f.versions.get(newVersion).files['/member/hpc-v25/js/player.js'], f.initial['/member/hpc-v25/js/player.js']);
  assert.deepEqual(f.versions.get(newVersion).config, f.config);
});
test('same output rerun does not allocate or publish a version', async () => {
  const f = fixture(); await publish(f.options, f.host); f.writes.length = 0;
  assert.equal((await publish(f.options, f.host)).status, 'UNCHANGED'); assert.deepEqual(f.writes, []);
});
test('retained editorial metadata survives refreshed source fields and an unchanged rerun', async () => {
  const f = fixture({ stable_id: 'hpc-reviewed-001', editorial_note: 'Previously reviewed context' });
  const refreshed = { ...first, title: 'Corrected official source title', timestamp: '2026-11-11T01:00:25Z' };
  f.next.hpc.lane.videos[0] = refreshed;
  f.options.catalogBytes = jsonBytes(f.next); f.options.refreshReceipt.catalog_sha256 = sha256(f.options.catalogBytes);
  assert.equal((await publish(f.options, f.host)).status, 'PUBLISHED');
  for (const p of f.paths) {
    const delivered = JSON.parse(f.bodies.get(p)).hpc.lane.videos;
    assert.equal(delivered[0].stable_id, 'hpc-reviewed-001');
    assert.equal(delivered[0].editorial_note, 'Previously reviewed context');
    assert.equal(delivered[0].title, refreshed.title); assert.equal(delivered[0].timestamp, refreshed.timestamp);
    assert.deepEqual(delivered[1], added);
  }
  f.writes.length = 0;
  assert.equal((await publish(f.options, f.host)).status, 'UNCHANGED'); assert.deepEqual(f.writes, []);
});
test('candidate IDs must equal the complete fresh eligibility receipt', async () => {
  const f = fixture(); f.options.refreshReceipt.eligible_ids = [first.video_id];
  await assert.rejects(publish(f.options, f.host), { message: 'ELIGIBLE_IDS_MISMATCH' }); assert.deepEqual(f.writes, []);
});
test('existing video removal requires a source exclusion', async () => {
  const f = fixture(); f.next.hpc.lane.videos = [added]; f.next.hpc.lane.video_count = 1;
  f.options.catalogBytes = jsonBytes(f.next); f.options.refreshReceipt.catalog_sha256 = sha256(f.options.catalogBytes);
  f.options.refreshReceipt.eligible_ids = [added.video_id];
  await assert.rejects(publish(f.options, f.host), { message: 'EXISTING_VIDEO_REMOVAL_UNVERIFIED' }); assert.deepEqual(f.writes, []);
  f.options.refreshReceipt.excluded = [{ video_id: first.video_id, reason: 'unavailable' }];
  assert.equal((await publish(f.options, f.host)).status, 'PUBLISHED');
});
test('all source videos excluded publishes an empty eligible collection', async () => {
  const f = fixture(); f.next.hpc.lane.videos = []; f.next.hpc.lane.video_count = 0;
  f.options.catalogBytes = jsonBytes(f.next); f.options.refreshReceipt.catalog_sha256 = sha256(f.options.catalogBytes);
  f.options.refreshReceipt.eligible_ids = []; f.options.refreshReceipt.excluded = [{ video_id: first.video_id, reason: 'unavailable' }];
  assert.equal((await publish(f.options, f.host)).status, 'PUBLISHED');
  for (const p of f.paths) { const delivered = JSON.parse(f.bodies.get(p)); assert.deepEqual(delivered.hpc.lane.videos, []); assert.equal(delivered.hpc.lane.video_count, 0); }
});
test('existing queue IDs retain their order', async () => {
  const f = fixture(); await publish(f.options, f.host); f.writes.length = 0;
  f.next.hpc.lane.videos = [added, first]; f.options.catalogBytes = jsonBytes(f.next);
  f.options.refreshReceipt.catalog_sha256 = sha256(f.options.catalogBytes); f.options.refreshReceipt.eligible_ids = [added.video_id, first.video_id];
  await assert.rejects(publish(f.options, f.host), { message: 'EXISTING_QUEUE_REORDERED' }); assert.deepEqual(f.writes, []);
});
for (const [name, change, code] of [
  ['stale receipt', f => { f.options.refreshReceipt.expires_at = '2026-11-25T02:00:00Z'; }, 'REFRESH_RECEIPT_STALE'],
  ['digest mismatch', f => { f.options.refreshReceipt.catalog_sha256 = '0'.repeat(64); }, 'CATALOG_DIGEST_MISMATCH'],
  ['wrong source', f => { f.options.refreshReceipt.source_channel_id = 'different'; }, 'REFRESH_RECEIPT_INCOMPLETE'],
  ['duplicate IDs', f => { f.next.hpc.lane.videos.push(added); f.next.hpc.lane.video_count++; }, 'INVALID_OR_DUPLICATE_VIDEO'],
  ['changed editorial label', f => { f.next.hpc.lane.videos[0] = { ...first, editorial_label: 'Opinion' }; }, 'EDITORIAL_LABEL_CHANGED']
]) test(name + ' refuses before cloud mutation', async () => {
  const f = fixture(); change(f);
  if (name === 'duplicate IDs' || name === 'changed editorial label') {
    f.options.catalogBytes = jsonBytes(f.next); f.options.refreshReceipt.catalog_sha256 = sha256(f.options.catalogBytes);
    f.options.refreshReceipt.eligible_ids = f.next.hpc.lane.videos.map(v => v.video_id);
  }
  await assert.rejects(publish(f.options, f.host), { message: code }); assert.deepEqual(f.writes, []);
});
test('release drift after finalization refuses promotion and records recoverable version', async () => {
  const f = fixture(); let calls = 0; const original = f.host.getLive;
  f.host.getLive = async () => { const value = await original(); if (++calls === 3) value.release.name += '9'; return value; };
  await assert.rejects(publish(f.options, f.host), error => {
    assert.equal(error.message, 'LIVE_RELEASE_MOVED'); assert.equal(error.publicationReceipt.candidate_version, newVersion); return true;
  }); assert.ok(!f.writes.includes('release'));
});
test('clone config drift refuses all asset changes', async () => {
  const f = fixture(), clone = f.host.clone; f.host.clone = async v => { const result = await clone(v); f.versions.get(result).config = {}; return result; };
  await assert.rejects(publish(f.options, f.host), { message: 'CLONE_CONFIG_CHANGED' }); assert.deepEqual(f.writes, ['clone']);
});
test('unrelated file change refuses release', async () => {
  const f = fixture(), finalize = f.host.finalize; f.host.finalize = async (v, c) => { await finalize(v, c); f.versions.get(v).files['/vote/index.html'] = 'e'.repeat(64); };
  await assert.rejects(publish(f.options, f.host), { message: 'HOSTING_FILE_PRESERVATION_FAILED' }); assert.ok(!f.writes.includes('release'));
});
test('unexpected requested upload hash refuses transmission', async () => {
  const f = fixture(), populate = f.host.populate; f.host.populate = async (v, c) => ({ ...await populate(v, c), uploadRequiredHashes: ['e'.repeat(64)] });
  await assert.rejects(publish(f.options, f.host), { message: 'UNEXPECTED_UPLOAD_HASH' }); assert.ok(!f.writes.includes('upload'));
});
test('public readback mismatch fails after saved release without blind rollback', async () => {
  const f = fixture(), release = f.host.release; f.host.release = async v => { await release(v); f.bodies.set(f.paths[0], Buffer.from('{}')); };
  await assert.rejects(publish(f.options, f.host), error => {
    assert.equal(error.message, 'PUBLIC_CATALOG_READBACK_MISMATCH'); assert.equal(error.publicationReceipt.rollback_version, oldVersion); return true;
  }); assert.equal(f.writes.filter(w => w === 'release').length, 1);
});
test('native upload adapter satisfies vendor response guard and sends compressed binary bytes', async () => {
  const bytes = zlib.gzipSync(Buffer.from('HPC catalog payload')), hash = sha256(bytes);
  let requests = 0;
  class GuardedClient {
    constructor(options) { assert.equal(options.auth, true); }
    async request(options) {
      // Firebase CLI 14.26/14.27 Client.request rejects this combination before
      // any network operation; keep that vendor boundary represented in CI.
      if (options.responseType === 'stream' && !options.resolveOnHTTPError) throw new Error('VENDOR_STREAM_HTTP_ERROR_GUARD');
      requests++;
      assert.equal(options.method, 'POST'); assert.equal(options.path, '/' + hash);
      assert.equal(options.responseType, 'json'); assert.equal(options.resolveOnHTTPError, undefined);
      assert.equal(options.headers['Content-Type'], 'application/octet-stream');
      assert.equal(options.retries, 0); assert.equal(options.timeout, 15000);
      assert.ok(options.body instanceof Readable);
      const chunks = []; for await (const chunk of options.body) chunks.push(chunk);
      assert.deepEqual(Buffer.concat(chunks), bytes);
      return { status: 200, body: undefined };
    }
  }
  await uploadWithClient(GuardedClient, newVersion,
    'https://upload-firebasehosting.googleapis.com/upload/sites/foundupscom/versions/87654321/files', hash, bytes);
  assert.equal(requests, 1);
});
test('native upload adapter propagates HTTP rejection without suppression or retry', async () => {
  let requests = 0;
  class RejectedClient {
    async request(options) {
      requests++; assert.equal(options.resolveOnHTTPError, undefined); assert.equal(options.retries, 0);
      throw Object.assign(new Error('offline denied upload'), { status: 403 });
    }
  }
  await assert.rejects(uploadWithClient(RejectedClient, newVersion,
    'https://upload-firebasehosting.googleapis.com/upload/sites/foundupscom/versions/87654321/files', 'a'.repeat(64), Buffer.from('gzip fixture')),
  { status: 403 });
  assert.equal(requests, 1);
});
test('installed native Client accepts empty success and rejects HTTP error using offline fetch', async t => {
  const cliRoot = process.env.FIREBASE_CLI_ROOT || path.join(process.env.APPDATA || '', 'npm/node_modules/firebase-tools');
  if (!fs.existsSync(path.join(cliRoot, 'lib/apiv2.js'))) { t.skip('Optional installed Firebase CLI unavailable; vendor contract tests above remain mandatory'); return; }
  const cliVersion = JSON.parse(fs.readFileSync(path.join(cliRoot, 'package.json'), 'utf8')).version;
  assert.ok(['14.26.0', '14.27.0'].includes(cliVersion));
  const { logger } = require(path.join(cliRoot, 'lib/logger.js'));
  const previousSilent = logger.silent; logger.silent = true;
  const { Client } = require(path.join(cliRoot, 'lib/apiv2.js'));
  const nodeFetch = require(require.resolve('node-fetch', { paths: [cliRoot] }));
  const originalFetch = nodeFetch.default;
  const bytes = zlib.gzipSync(Buffer.from('native offline upload')), hash = sha256(bytes);
  let status = 200, requests = 0;
  // Disable authentication before entering the real vendor request/response
  // code; replace its fetch before any request, so this test has no network.
  class OfflineClient extends Client { constructor(options) { super({ ...options, auth: false }); } }
  nodeFetch.default = async (url, options) => {
    requests++; assert.equal(url, 'https://upload-firebasehosting.googleapis.com/upload/sites/foundupscom/versions/87654321/files/' + hash);
    assert.equal(options.headers.get('Content-Type'), 'application/octet-stream');
    const chunks = []; for await (const chunk of options.body) chunks.push(chunk);
    assert.deepEqual(Buffer.concat(chunks), bytes);
    return new nodeFetch.Response(status === 200 ? '' : JSON.stringify({ error: { code: 403, message: 'offline denied upload', status: 'PERMISSION_DENIED' } }), { status });
  };
  try {
    const url = 'https://upload-firebasehosting.googleapis.com/upload/sites/foundupscom/versions/87654321/files';
    await uploadWithClient(OfflineClient, newVersion, url, hash, bytes);
    status = 403;
    await assert.rejects(uploadWithClient(OfflineClient, newVersion, url, hash, bytes), { status: 403 });
    assert.equal(requests, 2);
  } finally { nodeFetch.default = originalFetch; logger.silent = previousSilent; }
});
