'use strict';

const assert = require('assert');
const EventEmitter = require('events');
const fs = require('fs');
const os = require('os');
const path = require('path');
const owner = require('../holoindex_generation_bound_query');

function options(root, transport) {
  return {
    root, query: 'audit pfmall', limit: 5, interpreterPath: 'python',
    interpreterProvenance: { verified: false, status: 'test_unverified' },
    request: { retrieval_mode: 'lexical', include_bundle: true,
      bundle_only: true, must_include: ['README.md'] },
    execFile: transport, env: {}
  };
}

async function assertBridgeFailure(root, transport) {
  const result = await owner.runOwnerQueryAsync(options(root, transport));
  assert.strictEqual(result.ok, false);
  assert.strictEqual(result.error, 'owner_query_bridge_error');
  assert.strictEqual(result.interpreter_provenance.status, 'test_unverified');
  return result;
}

function assertSourceContracts(root) {
  const provenance = fs.readFileSync(
    path.join(root, 'extensions', 'reddog', 'holoindex_interpreter_provenance.js'), 'utf8'
  );
  assert(!provenance.includes('readFileSync'),
    'interpreter provenance must never allocate/read the whole executable');
  assert(provenance.includes('fs.readSync(fd, chunk'),
    'interpreter provenance must stream fixed-size descriptor chunks');
  assert(provenance.includes('const HASH_CHUNK_BYTES = 64 * 1024;'),
    'interpreter provenance chunk allocation must remain explicitly bounded');
  const extension = fs.readFileSync(path.join(root, 'extensions', 'reddog', 'extension.js'), 'utf8');
  const disposal = extension.indexOf('panel.onDidDispose(() => {');
  const disposedFirst = extension.indexOf('state.disposed = true;', disposal);
  const cancelHolo = extension.indexOf('state.holoLifecycleRegistry.dispose();', disposal);
  const killProvider = extension.indexOf('killBridgeChild(state);', disposal);
  assert(disposal >= 0 && disposedFirst < cancelHolo && cancelHolo < killProvider);
  assert(extension.includes('buildBoundedRepoContextAsync(input.contextMode, input.workFocus, lifecycle)'));
  assert(extension.includes("holoIndexOutputAsync(workspaceRoot(), taskText || '', 18000, lifecycle)"));
  assert(extension.includes('await holoGenerationBoundQuery.runOwnerQueryAsync({'));
}

async function assertNonBlockingRequest(root) {
  let request = null;
  let eventLoopAdvanced = false;
  const transport = (_exe, _args, opts, callback) => {
    assert.strictEqual(opts.timeout, 300000);
    setTimeout(() => callback(null, JSON.stringify({
      ok: false, source: 'holoindex_owner_service', freshness: 'UNKNOWN',
      raw_result: {}, error: 'TEST_OWNER_REJECT', index_gap_detected: true,
      stale_reasons: ['test'], no_holoindex_reindex_performed: true
    })), 20);
    return { stdin: { end: (value) => { request = JSON.parse(value); } } };
  };
  const pending = owner.runOwnerQueryAsync(options(root, transport));
  setImmediate(() => { eventLoopAdvanced = true; });
  const result = await pending;
  assert.strictEqual(eventLoopAdvanced, true, 'bridge blocked the Node event loop');
  assert.deepStrictEqual(request.must_include, ['README.md']);
  assert.strictEqual(result.error, 'TEST_OWNER_REJECT');
  assert.strictEqual(result.interpreter_provenance.status, 'test_unverified');
}

async function assertBasicFailures(root) {
  await assertBridgeFailure(root, () => { throw new Error('transport failed'); });
  const timeout = await owner.runOwnerQueryAsync(options(root,
    (_exe, _args, _opts, callback) => {
      setImmediate(() => callback(Object.assign(new Error('timeout'), { code: 'ETIMEDOUT' })));
      return { stdin: { end() {} }, kill() {} };
    }));
  assert.strictEqual(timeout.error, 'owner_query_timeout');
  let missingInputKills = 0;
  await assertBridgeFailure(root, () => ({ kill: () => { missingInputKills += 1; } }));
  assert.strictEqual(missingInputKills, 1);
}

async function assertThrownInput(root) {
  let lateCallback;
  let kills = 0;
  const result = await assertBridgeFailure(root, (_exe, _args, _opts, callback) => {
    lateCallback = callback;
    return { kill: () => { kills += 1; },
      stdin: { end: () => { throw new Error('stdin failed'); } } };
  });
  lateCallback(null, JSON.stringify({ ok: true, freshness: 'CURRENT' }));
  await new Promise((resolve) => setImmediate(resolve));
  assert.strictEqual(result.error, 'owner_query_bridge_error');
  assert.strictEqual(kills, 1);
}

async function assertPipeFailure(root) {
  const stdin = new EventEmitter();
  let callback;
  let kills = 0;
  stdin.end = () => setImmediate(() => {
    stdin.emit('error', Object.assign(new Error('broken pipe'), { code: 'EPIPE' }));
    setImmediate(() => callback(null, JSON.stringify({ ok: true })));
  });
  const result = await assertBridgeFailure(root, (_exe, _args, _opts, transportCallback) => {
    callback = transportCallback;
    return { stdin, kill: () => { kills += 1; } };
  });
  await new Promise((resolve) => setTimeout(resolve, 10));
  assert.strictEqual(result.error, 'owner_query_bridge_error');
  assert.strictEqual(kills, 1);
}

async function assertCancellation(root) {
  const registry = owner.createProcessLifecycleRegistry();
  const lifecycle = registry.begin();
  let callback;
  let kills = 0;
  const pending = owner.runOwnerQueryAsync(Object.assign(options(root,
    (_exe, _args, _opts, transportCallback) => {
      callback = transportCallback;
      return { stdin: { end() {} }, kill: () => { kills += 1; } };
    }), { lifecycle }));
  registry.dispose();
  const result = await pending;
  assert.strictEqual(result.error, 'owner_query_cancelled');
  assert.strictEqual(result.cancelled, true);
  assert.strictEqual(kills, 1);
  callback(null, JSON.stringify({ ok: true, freshness: 'CURRENT' }));
  await new Promise((resolve) => setImmediate(resolve));
  assert.strictEqual(result.error, 'owner_query_cancelled');
}

async function assertLargeInterpreter(root) {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-holo-python-'));
  const name = process.platform === 'win32' ? 'python.exe' : 'python';
  const interpreter = path.join(tempRoot, name);
  const original = fs.readFileSync;
  try {
    fs.writeFileSync(interpreter, Buffer.alloc(32 * 1024 * 1024, 0x51));
    let yielded = false;
    let parentReads = 0;
    fs.readFileSync = function(candidate, ...args) {
      if (candidate === interpreter || (Number.isInteger(candidate) && candidate >= 0)) parentReads += 1;
      return original.call(this, candidate, ...args);
    };
    const pending = owner.resolveInterpreterAsync(tempRoot, interpreter, process.platform);
    assert.strictEqual(parentReads, 0, 'provenance descriptor/hash ran on parent thread');
    fs.readFileSync = original;
    setImmediate(() => { yielded = true; });
    const runtime = await pending;
    assert.strictEqual(yielded, true, 'large interpreter hashing blocked the event loop');
    assert.strictEqual(runtime.provenance.size, 32 * 1024 * 1024);
    assert(/^sha256:[0-9a-f]{64}$/.test(runtime.provenance.canonical_path_digest));
    assert(/^[0-9a-f]{64}$/.test(runtime.provenance.sha256));
  } finally {
    fs.readFileSync = original;
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
}

function assertDirectReadProjection() {
  const dependencies = {
    semanticTargetCoverageDigest: () => 'sha256:test',
    evaluateTargetRecall: () => ({ target_recall_ok: true, index_gap_detected: false,
      recall_targets: [], required_targets_total: 1, required_targets_recalled: 1,
      required_targets_missing: [], semantic_targets_count: 0 }),
    semanticEvidenceHitsFromBundleData: () => []
  };
  const bundle = JSON.stringify({
    task_retrieval: { metadata: {}, code_hits: [], wsp_hits: [] },
    direct_read: { direct_read_fallback_used: true,
      direct_read_paths: ['README.md'], direct_read_bytes: 12,
      direct_read_rejected: [], direct_read_truncated: [] }
  });
  const meta = owner.buildMetaFromBundle(bundle, false, 'README.md', dependencies);
  assert.strictEqual(meta.direct_read_fallback_used, true);
  assert.strictEqual(meta.direct_read_fetch_attempted, true);
  const empty = owner.buildMetaFromBundle(JSON.stringify({ task_retrieval: { metadata: {} },
    direct_read: { direct_read_fallback_used: true, direct_read_paths: [],
      direct_read_bytes: 0 } }), false, 'README.md', dependencies);
  assert.strictEqual(empty.direct_read_fallback_used, false);
  assert.strictEqual(empty.direct_read_fetch_attempted, false);
}

async function main() {
  const root = path.resolve(__dirname, '..', '..', '..');
  assertSourceContracts(root);
  assertDirectReadProjection();
  await assertNonBlockingRequest(root);
  await assertBasicFailures(root);
  await assertThrownInput(root);
  await assertPipeFailure(root);
  await assertCancellation(root);
  await assertLargeInterpreter(root);
  console.log('RedDog governed HoloIndex async bridge contracts: PASS');
}

main().catch((error) => {
  console.error(error && error.stack || error);
  process.exitCode = 1;
});
