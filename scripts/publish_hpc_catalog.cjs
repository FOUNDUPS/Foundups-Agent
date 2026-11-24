'use strict';

// HPC collection-only Hosting publication. This reuses the installed Firebase CLI
// authentication and REST client; it never deploys a local public directory.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const zlib = require('node:zlib');
const { Readable } = require('node:stream');
const { isDeepStrictEqual } = require('node:util');

const PROJECT = 'gen-lang-client-0061781628';
const SITE = 'foundupscom';
const ORIGIN = 'https://hpc.foundups.com';
const CHANNEL_ID = 'UC-LSSlOZwpGIRIYihaz8zCw';
const TARGET = /^\/member\/(?:hpc-v[0-9]+\/)?mall-public-video-catalog\.json$/;
const HEX = /^[a-f0-9]{64}$/;
const LIMIT = 4 * 1024 * 1024;
const sha256 = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const jsonBytes = value => Buffer.from(JSON.stringify(value, null, 2) + '\n');
function requireThat(ok, code) { if (!ok) throw Object.assign(new Error(code), { safeCode: code }); }
function plain(value) { return value && typeof value === 'object' && !Array.isArray(value); }
function normalizeVersion(name) {
  const pattern = /^(?:projects\/(?:gen-lang-client-0061781628|56566376153|-)\/)?sites\/foundupscom\/versions\/([a-f0-9]{8,40})$/;
  const match = typeof name === 'string' && pattern.exec(name);
  requireThat(match, 'HOSTING_VERSION_OUTSIDE_SCOPE');
  return `projects/${PROJECT}/sites/${SITE}/versions/${match[1]}`;
}
function versionId(name) { return normalizeVersion(name).split('/').at(-1); }
function fresh(receipt, catalogBytes, now) {
  requireThat(receipt.schema_version === 'hpc_youtube_refresh.v1' && receipt.complete === true &&
    receipt.scope === 'hpc' && receipt.source_channel_id === CHANNEL_ID, 'REFRESH_RECEIPT_INCOMPLETE');
  const checked = Date.parse(receipt.checked_at), expires = Date.parse(receipt.expires_at);
  requireThat(Number.isFinite(checked) && Number.isFinite(expires) && checked <= now + 300000 &&
    expires > now && expires > checked && expires - checked <= 86400000, 'REFRESH_RECEIPT_STALE');
  requireThat(HEX.test(receipt.catalog_sha256 || '') && receipt.catalog_sha256 === sha256(catalogBytes), 'CATALOG_DIGEST_MISMATCH');
}
function videosOf(document) {
  const lane = document?.hpc?.lane;
  requireThat(plain(lane) && lane.foundup_id === 'hpc' && Array.isArray(lane.videos) &&
    lane.videos.length <= 10000 && lane.video_count === lane.videos.length,
  'INVALID_HPC_COLLECTION');
  const seen = new Set();
  for (const video of lane.videos) {
    requireThat(plain(video) && /^[A-Za-z0-9_-]{11}$/.test(video.video_id || '') && !seen.has(video.video_id), 'INVALID_OR_DUPLICATE_VIDEO');
    seen.add(video.video_id);
    requireThat(typeof video.title === 'string' && video.title.trim() && typeof video.source_label === 'string' &&
      video.source_label.trim() && typeof video.editorial_label === 'string' && video.editorial_label.trim(), 'VIDEO_ATTRIBUTION_MISSING');
    requireThat(video.embed_url === `https://www.youtube.com/embed/${video.video_id}` &&
      [`https://www.youtube.com/watch?v=${video.video_id}`, `https://www.youtube.com/shorts/${video.video_id}`].includes(video.source_url),
    'VIDEO_SOURCE_MISMATCH');
  }
  return lane.videos;
}
function collectionDocument(oldDocument, newVideos, receipt) {
  const oldVideos = videosOf(oldDocument), nextById = new Map(newVideos.map(v => [v.video_id, v]));
  const oldById = new Map(oldVideos.map(v => [v.video_id, v]));
  const retainedOld = oldVideos.filter(v => nextById.has(v.video_id));
  const oldIds = new Set(oldVideos.map(v => v.video_id));
  const excluded = new Set((receipt.excluded || []).map(item => item.video_id));
  requireThat(oldVideos.every(v => nextById.has(v.video_id) || excluded.has(v.video_id)), 'EXISTING_VIDEO_REMOVAL_UNVERIFIED');
  const retainedNext = newVideos.filter(v => oldIds.has(v.video_id));
  requireThat(isDeepStrictEqual(retainedOld.map(v => v.video_id), retainedNext.map(v => v.video_id)), 'EXISTING_QUEUE_REORDERED');
  for (const old of retainedOld) requireThat(nextById.get(old.video_id).editorial_label === old.editorial_label, 'EDITORIAL_LABEL_CHANGED');
  const mergedVideos = newVideos.map(video => ({ ...oldById.get(video.video_id), ...video }));
  // Retain production metadata, credits, links and every unrelated collection.
  return { ...oldDocument, hpc: { ...oldDocument.hpc, lane: { ...oldDocument.hpc.lane,
    videos: mergedVideos, video_count: mergedVideos.length } } };
}
function fileMap(files) {
  requireThat(Array.isArray(files) && files.length > 0 && files.length <= 10000, 'HOSTING_FILE_LIST_INVALID');
  const result = {};
  for (const file of files) {
    requireThat(typeof file.path === 'string' && file.path.startsWith('/') && !Object.hasOwn(result, file.path) &&
      HEX.test(file.hash || '') && file.status === 'ACTIVE', 'HOSTING_FILE_INVALID');
    result[file.path] = file.hash;
  }
  return result;
}
function assertPreserved(files, expected) {
  requireThat(isDeepStrictEqual(fileMap(files), expected), 'HOSTING_FILE_PRESERVATION_FAILED');
}
function liveIdentity(live) {
  requireThat(typeof live?.release?.name === 'string' && /\/channels\/live\/releases\/[0-9]+$/.test(live.release.name), 'LIVE_RELEASE_MISSING');
  return { release: live.release.name, version: normalizeVersion(live.release.version?.name) };
}
function assertLive(live, baseline) { requireThat(isDeepStrictEqual(liveIdentity(live), baseline), 'LIVE_RELEASE_MOVED'); }

async function publish(options, host) {
  const now = options.now || Date.now;
  requireThat(/^[a-f0-9]{40}$/.test(options.sourceSha || ''), 'EXACT_SOURCE_SHA_REQUIRED');
  const bytes = options.catalogBytes, receipt = options.refreshReceipt;
  requireThat(Buffer.isBuffer(bytes) && bytes.length <= LIMIT, 'CATALOG_SIZE_INVALID');
  fresh(receipt, bytes, now());
  const document = JSON.parse(bytes.toString('utf8')), videos = videosOf(document);
  requireThat(isDeepStrictEqual(receipt.eligible_ids, videos.map(v => v.video_id)), 'ELIGIBLE_IDS_MISMATCH');
  const result = { schema_version: 'hpc_catalog_publication.v1', project: PROJECT, site: SITE, scope: 'hpc',
    source_sha: options.sourceSha, catalog_sha256: sha256(bytes), checked_at: new Date(now()).toISOString(),
    applied: false, cloud_writes: [], status: 'PREPARING',
    concurrency_limit: 'Live release rechecked immediately before release; Firebase exposes no compare-and-swap release precondition.' };
  const save = phase => { result.phase = phase; options.checkpoint?.(result); options.emit?.(phase); };
  try {
    save('READ_CURRENT_LIVE');
    const live = await host.getLive(), baseline = liveIdentity(live);
    result.previous_release = baseline.release; result.rollback_version = baseline.version;
    const prior = await host.getVersion(baseline.version);
    requireThat(normalizeVersion(prior.name) === baseline.version && prior.status === 'FINALIZED' && plain(prior.config), 'LIVE_VERSION_INVALID');
    const originalMap = fileMap(await host.listFiles(baseline.version));
    result.original_manifest_sha256 = sha256(jsonBytes(originalMap));
    result.config_sha256 = sha256(jsonBytes(prior.config));
    const targets = Object.keys(originalMap).filter(p => TARGET.test(p)).sort();
    requireThat(targets.includes('/member/mall-public-video-catalog.json') && targets.length <= 16, 'LIVE_CATALOG_PATHS_MISSING');
    const replacements = new Map();
    for (const target of targets) {
      const oldBytes = await host.readPublic(target, originalMap[target]);
      const oldDocument = JSON.parse(oldBytes.toString('utf8'));
      const merged = collectionDocument(oldDocument, videos, receipt);
      if (!isDeepStrictEqual(merged, oldDocument)) {
        const replacement = jsonBytes(merged), compressed = zlib.gzipSync(replacement, { level: 9 });
        replacements.set(target, { bytes: replacement, compressed, hash: sha256(compressed) });
      }
    }
    assertLive(await host.getLive(), baseline);
    result.paths = [...replacements].map(([target, value]) => ({ path: target, previous_hash: originalMap[target],
      hash: value.hash, raw_sha256: sha256(value.bytes) }));
    result.preserved_file_count = Object.keys(originalMap).length - replacements.size;
    if (!options.apply || !replacements.size) {
      result.status = replacements.size ? 'PLANNED' : 'UNCHANGED'; save('FINISHED'); return result;
    }
    fresh(receipt, bytes, now());
    save('CLONE_CURRENT_LIVE');
    const candidate = normalizeVersion(await host.clone(baseline.version));
    requireThat(candidate !== baseline.version, 'CLONE_REUSED_LIVE_VERSION');
    result.candidate_version = candidate; result.cloud_writes.push('cloned_current_live'); save('VERIFY_CLONE');
    const cloned = await host.getVersion(candidate);
    requireThat(cloned.status === 'CREATED' && isDeepStrictEqual(cloned.config, prior.config), 'CLONE_CONFIG_CHANGED');
    assertPreserved(await host.listFiles(candidate), originalMap);
    const changes = Object.fromEntries([...replacements].map(([target, value]) => [target, value.hash]));
    const populated = await host.populate(candidate, changes); result.cloud_writes.push('populated_only_catalog_paths'); save('UPLOAD_CATALOGS');
    const byHash = new Map([...replacements.values()].map(v => [v.hash, v.compressed]));
    requireThat(Array.isArray(populated.uploadRequiredHashes) && new Set(populated.uploadRequiredHashes).size === populated.uploadRequiredHashes.length &&
      populated.uploadRequiredHashes.every(hash => byHash.has(hash)), 'UNEXPECTED_UPLOAD_HASH');
    for (const hash of populated.uploadRequiredHashes) await host.upload(candidate, populated.uploadUrl, hash, byHash.get(hash));
    const expected = { ...originalMap, ...changes };
    save('FINALIZE_AND_VERIFY');
    await host.finalize(candidate, prior.config);
    result.cloud_writes.push('finalized_catalog_version');
    const finalized = await host.getVersion(candidate);
    requireThat(finalized.status === 'FINALIZED' && isDeepStrictEqual(finalized.config, prior.config), 'FINALIZED_CONFIG_CHANGED');
    assertPreserved(await host.listFiles(candidate), expected);
    result.final_manifest_sha256 = sha256(jsonBytes(expected));
    fresh(receipt, bytes, now());
    assertLive(await host.getLive(), baseline);
    save('RELEASE_CATALOG_ONLY');
    // No automatic retry or rollback: another publisher might have acquired live.
    await host.release(candidate, options.sourceSha);
    result.cloud_writes.push('released_catalog_version'); save('VERIFY_LIVE');
    const delivered = liveIdentity(await host.getLive());
    requireThat(delivered.version === candidate, 'RELEASE_READBACK_MISMATCH');
    result.release = delivered.release;
    assertPreserved(await host.listFiles(candidate), expected);
    const deliveredVersion = await host.getVersion(candidate);
    requireThat(isDeepStrictEqual(deliveredVersion.config, prior.config), 'DELIVERED_CONFIG_CHANGED');
    for (const [target, value] of replacements) requireThat(sha256(await host.readPublic(target, value.hash)) === sha256(value.bytes), 'PUBLIC_CATALOG_READBACK_MISMATCH');
    result.applied = true; result.status = 'PUBLISHED'; save('FINISHED'); return result;
  } catch (error) {
    result.status = 'FAILED'; result.error_code = error.safeCode || 'PUBLICATION_FAILED'; options.checkpoint?.(result);
    error.publicationReceipt = result; throw error;
  }
}

async function readPublic(target, expectedHash) {
  requireThat(TARGET.test(target), 'PUBLIC_PATH_OUTSIDE_SCOPE');
  const response = await fetch(ORIGIN + target + '?hpc-refresh=' + Date.now(), {
    redirect: 'error', signal: AbortSignal.timeout(15000),
    headers: { 'Cache-Control': 'no-cache', 'Accept-Encoding': 'identity' } });
  requireThat(response.ok && /application\/json/i.test(response.headers.get('content-type') || ''), 'PUBLIC_CATALOG_UNAVAILABLE');
  requireThat(HEX.test(expectedHash || '') && new RegExp('^(?:W/)?"' + expectedHash + '(?:-br|-gzip)?"$').test(response.headers.get('etag') || ''), 'PUBLIC_CATALOG_VERSION_MISMATCH');
  const reader = response.body.getReader(), chunks = []; let size = 0;
  while (true) {
    const { done, value } = await reader.read(); if (done) break;
    size += value.length; if (size > LIMIT) { await reader.cancel(); requireThat(false, 'PUBLIC_CATALOG_TOO_LARGE'); }
    chunks.push(Buffer.from(value));
  }
  return Buffer.concat(chunks);
}
async function createHost(cliRoot, cwd) {
  const cliPath = name => path.join(cliRoot, 'lib', name);
  const version = JSON.parse(fs.readFileSync(path.join(cliRoot, 'package.json'), 'utf8')).version;
  requireThat(['14.26.0', '14.27.0'].includes(version), 'UNREVIEWED_FIREBASE_CLI');
  requireThat(!process.env.FIREBASE_TOKEN, 'UNSUPPORTED_AUTH_OVERRIDE');
  if (process.env.GOOGLE_APPLICATION_CREDENTIALS) {
    const credentials = JSON.parse(regularBytes(process.env.GOOGLE_APPLICATION_CREDENTIALS).toString('utf8'));
    requireThat(credentials.type === 'service_account' && credentials.project_id === PROJECT, 'ADC_PROJECT_OR_TYPE_INVALID');
  }
  require(cliPath('logger.js')).logger.silent = true;
  const { Command } = require(cliPath('command.js')), { requireAuth } = require(cliPath('requireAuth.js'));
  const { Client } = require(cliPath('apiv2.js'));
  const auth = { project: PROJECT, site: SITE, json: true, nonInteractive: true, cwd };
  await new Command('hpc-catalog-only').prepare(auth);
  requireThat(auth.projectId === PROJECT, 'AUTH_PROJECT_MISMATCH');
  await requireAuth(auth); // Existing cached CLI account or CI ADC; no token export.
  const client = new Client({ urlPrefix: 'https://firebasehosting.googleapis.com', apiVersion: 'v1beta1', auth: true });
  const get = async (name, queryParams) => (await client.get('/' + name, { timeout: 15000, queryParams })).body;
  return {
    getLive: () => get(`projects/${PROJECT}/sites/${SITE}/channels/live`),
    getVersion: name => get(normalizeVersion(name)),
    async listFiles(name) {
      const files = [], seen = new Set(); let token;
      do {
        const body = await get(normalizeVersion(name) + '/files', { pageSize: 1000, ...(token ? { pageToken: token } : {}) });
        files.push(...(body.files || [])); token = body.nextPageToken;
        requireThat(files.length <= 10000 && (!token || !seen.has(token)) && seen.size < 12, 'HOSTING_PAGINATION_INVALID');
        if (token) seen.add(token);
      } while (token);
      return files;
    },
    readPublic,
    async clone(name) {
      let operation = (await client.post(`/projects/${PROJECT}/sites/${SITE}/versions:clone`, {
        sourceVersion: normalizeVersion(name), finalize: false }, { timeout: 15000, retries: 0 })).body;
      for (let polls = 0; !operation.done; polls++) {
        requireThat(polls < 100 && /^(?:projects\/(?:gen-lang-client-0061781628|56566376153|-)\/)?sites\/foundupscom\/operations\/[A-Za-z0-9_-]+$/.test(operation.name || ''), 'CLONE_OPERATION_INVALID');
        await new Promise(resolve => setTimeout(resolve, 250)); operation = await get(operation.name);
      }
      requireThat(!operation.error, 'CLONE_OPERATION_FAILED'); return normalizeVersion(operation.response?.name);
    },
    async populate(name, files) { return (await client.post('/' + normalizeVersion(name) + ':populateFiles', { files }, { timeout: 15000, retries: 0 })).body; },
    async upload(name, url, hash, bytes) {
      requireThat(url === `https://upload-firebasehosting.googleapis.com/upload/sites/${SITE}/versions/${versionId(name)}/files`, 'UPLOAD_DESTINATION_INVALID');
      const uploader = new Client({ urlPrefix: url, auth: true });
      await uploader.request({ method: 'POST', path: '/' + hash, body: Readable.from([bytes]),
        timeout: 15000, retries: 0, responseType: 'stream' });
    },
    finalize: (name, config) => client.patch('/' + normalizeVersion(name), { status: 'FINALIZED', config }, {
      timeout: 15000, retries: 0, queryParams: { updateMask: 'status,config' } }),
    release: (name, sourceSha) => client.post(`/projects/${PROJECT}/sites/${SITE}/channels/live/releases`, {
      message: 'HPC WikiTube collection refresh ' + sourceSha }, {
      timeout: 15000, retries: 0, queryParams: { versionName: normalizeVersion(name) } })
  };
}
function regularBytes(file) {
  const stat = fs.lstatSync(file); requireThat(stat.isFile() && !stat.isSymbolicLink() && stat.size <= LIMIT, 'INPUT_FILE_INVALID');
  return fs.readFileSync(file);
}
function parse(argv) {
  const options = { catalog: path.resolve(__dirname, '../public/member/mall-public-video-catalog.json'), apply: false };
  const names = { '--catalog': 'catalog', '--refresh-receipt': 'refreshReceiptPath', '--receipt': 'receiptPath', '--source-sha': 'sourceSha' };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--apply') { options.apply = true; continue; }
    requireThat(names[argv[i]] && i + 1 < argv.length && !argv[i + 1].startsWith('--'), 'ARGUMENT_INVALID');
    options[names[argv[i]]] = argv[++i];
  }
  requireThat(options.refreshReceiptPath && options.receiptPath && options.sourceSha, 'REQUIRED_ARGUMENT_MISSING');
  return options;
}
async function main() {
  const options = parse(process.argv.slice(2));
  // Never replace a prior receipt: ambiguous failed writes require reconciliation.
  const output = path.resolve(options.receiptPath);
  requireThat(!fs.existsSync(output), 'PUBLICATION_RECEIPT_ALREADY_EXISTS');
  fs.mkdirSync(path.dirname(output), { recursive: true });
  options.catalogBytes = regularBytes(options.catalog);
  options.refreshReceipt = JSON.parse(regularBytes(options.refreshReceiptPath).toString('utf8'));
  fresh(options.refreshReceipt, options.catalogBytes, Date.now());
  let phase = 'AUTH';
  options.emit = value => { phase = value; process.stdout.write(JSON.stringify({ phase }) + '\n'); };
  options.checkpoint = value => { const temporary = output + '.next'; fs.writeFileSync(temporary, jsonBytes(value), { flag: 'wx', mode: 0o600 }); fs.renameSync(temporary, output); };
  const heartbeat = setInterval(() => process.stdout.write(JSON.stringify({ phase: 'HEARTBEAT', active_phase: phase }) + '\n'), 5000);
  const deadline = setTimeout(() => { process.stdout.write(JSON.stringify({ status: 'TIMEOUT', recovery: 'Inspect saved receipt; do not retry or roll back blindly.' }) + '\n'); process.exit(124); }, 180000);
  try {
    const cliRoot = process.env.FIREBASE_CLI_ROOT || path.join(process.env.APPDATA || '', 'npm/node_modules/firebase-tools');
    const host = await createHost(cliRoot, path.resolve(__dirname, '..'));
    const result = await publish(options, host);
    process.stdout.write(JSON.stringify({ status: result.status, applied: result.applied, paths: result.paths?.map(p => p.path), receipt: output }) + '\n');
  } finally { clearInterval(heartbeat); clearTimeout(deadline); }
}
module.exports = { publish, fresh, videosOf, collectionDocument, fileMap, normalizeVersion, createHost, sha256, jsonBytes, parse };
if (require.main === module) main().catch(error => { process.stdout.write(JSON.stringify({ status: 'FAILED', error_code: error.safeCode || 'PUBLICATION_FAILED' }) + '\n'); process.exitCode = 1; });
