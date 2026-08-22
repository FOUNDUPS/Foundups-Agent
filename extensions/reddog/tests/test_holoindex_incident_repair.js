'use strict';

const assert = require('assert');
const cp = require('child_process');
const EventEmitter = require('events');
const fs = require('fs');
const path = require('path');

const extDir = path.resolve(__dirname, '..');
const repair = require(path.join(extDir, 'holoindex_incident_repair.js'));
const ownerBridge = require(path.join(extDir, 'holoindex_generation_bound_query.js'));
const extensionSource = fs.readFileSync(path.join(extDir, 'extension.js'), 'utf8');
const pkg = JSON.parse(fs.readFileSync(path.join(extDir, 'package.json'), 'utf8'));
const HEAD = 'a'.repeat(40);
const ROOT_DIGEST = 'sha256:' + 'b'.repeat(64);
const INCIDENT_DIGEST = 'sha256:' + 'c'.repeat(64);
const RECEIPT_DIGEST = 'sha256:' + 'd'.repeat(64);
const STALE_HEAD = 'e'.repeat(40);

function failure(changes) {
  return Object.assign({
    ok: false,
    error: 'SEMANTIC_BACKEND_UNAVAILABLE',
    index_gap_detected: true,
    no_holoindex_reindex_performed: true,
    owner_attempts: 2,
    workspace_repo_head_sha: HEAD,
    authority_repo_head_sha: HEAD,
    authority_repo_root_digest: ROOT_DIGEST,
    no_authority_worktree_mutation_performed: true
  }, changes || {});
}

assert.strictEqual(repair.shouldCoordinate(failure(), true), true);
assert.strictEqual(repair.shouldCoordinate(failure({
  error: 'HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH',
  owner_attempts: 0,
  authority_repo_head_sha: STALE_HEAD
}), true), true);
assert.strictEqual(repair.shouldCoordinate(failure(), false), false);
assert.strictEqual(repair.shouldCoordinate(failure({ owner_attempts: 1 }), true), false);
assert.strictEqual(repair.shouldCoordinate(failure({ error: 'forged' }), true), false);
assert.strictEqual(repair.shouldCoordinate(failure({ ok: true }), true), false);
assert.strictEqual(repair.shouldCoordinate(failure({
  error: 'HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH',
  owner_attempts: 2,
  authority_repo_head_sha: STALE_HEAD
}), true), false);
assert.strictEqual(repair.shouldCoordinate(failure({
  error: 'HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH',
  owner_attempts: 0,
  authority_repo_head_sha: HEAD
}), true), false);
assert.strictEqual(repair.shouldCoordinate(failure({
  workspace_repo_head_sha: new String(HEAD)
}), true), false);

const original = cp.execFileSync;
try {
  let invocation = null;
  let calls = 0;
  cp.execFileSync = (interpreter, args, options) => {
    calls += 1;
    invocation = { interpreter, args, options };
    return JSON.stringify({
      accepted: true,
      status: 'QUEUED',
      schema_version: 'reddog_holoindex_incident_repair.v2',
      incident_kind: 'SEMANTIC_BACKEND_UNAVAILABLE',
      incident_id: INCIDENT_DIGEST,
      task_id: 'holoindex_postmerge_refresh:' + 'a'.repeat(40),
      request_event_id: 'holoindex_postmerge_requested:' + HEAD,
      target_repo_head_sha: HEAD,
      workspace_repo_head_sha: HEAD,
      observed_authority_head_sha: HEAD,
      authority_root_digest: ROOT_DIGEST,
      generation_id: '',
      freshness_receipt_digest: '',
      receipt_id: RECEIPT_DIGEST,
      maintenance_enqueued: true,
      owner_requery_performed: false,
      coding_candidate_required: false,
      rejection_reasons: []
    });
  };
  const result = repair.coordinate({
    root: 'O:/repo',
    query: 'semantic repair',
    ownerResult: failure(),
    ownerObserved: true,
    interpreterPath: 'python',
    env: { SAFE: '1' }
  });
  assert.strictEqual(result.status, 'QUEUED');
  assert.strictEqual(invocation.interpreter, 'python');
  assert.deepStrictEqual(invocation.args.slice(0, 1), ['-B']);
  assert.strictEqual(invocation.options.timeout, 90000);
  assert.strictEqual(invocation.options.maxBuffer, 256 * 1024);
  assert.strictEqual(invocation.options.shell, undefined);
  const payload = JSON.parse(invocation.options.input);
  assert.strictEqual(payload.query, 'semantic repair');
  assert.strictEqual(payload.owner_failure.error, 'SEMANTIC_BACKEND_UNAVAILABLE');
  assert.strictEqual(Object.keys(payload.owner_failure).length, 9);

  const mismatchResult = repair.coordinate({
    root: 'O:/repo',
    query: 'repair stale authority',
    ownerResult: failure({
      error: 'HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH',
      owner_attempts: 0,
      authority_repo_head_sha: STALE_HEAD
    }),
    ownerObserved: true,
    interpreterPath: 'python',
    env: { SAFE: '1' }
  });
  assert.strictEqual(mismatchResult.status, 'QUEUED');
  assert.strictEqual(calls, 2);
  const mismatchPayload = JSON.parse(invocation.options.input);
  assert.strictEqual(
    mismatchPayload.owner_failure.error,
    'HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH'
  );
  assert.strictEqual(mismatchPayload.owner_failure.owner_attempts, 0);
  assert.strictEqual(
    mismatchPayload.owner_failure.authority_repo_head_sha,
    STALE_HEAD
  );

  const meta = repair.metadata(result);
  assert.strictEqual(meta.incident_repair_attempted, true);
  assert.strictEqual(meta.incident_repair_enqueued, true);
  assert.strictEqual(meta.incident_repair_coding_candidate_required, false);
  assert.strictEqual(meta.incident_repair_receipt.receipt_id, RECEIPT_DIGEST);
  assert.strictEqual(meta.incident_repair_receipt.target_repo_head_sha, HEAD);
  assert.notStrictEqual(meta.incident_repair_receipt, result);

  const huge = failure({ error: 'x'.repeat(8 * 1024 * 1024) });
  assert.strictEqual(repair.coordinate({
    root: 'O:/repo', query: 'bounded', ownerResult: huge,
    ownerObserved: true, interpreterPath: 'python'
  }).accepted, false);
  assert.strictEqual(calls, 2);

  const cyclic = failure();
  cyclic.untrusted = cyclic;
  assert.strictEqual(repair.coordinate({
    root: 'O:/repo', query: 'bounded', ownerResult: cyclic,
    ownerObserved: true, interpreterPath: 'python'
  }).accepted, false);
  assert.strictEqual(calls, 2);
} finally {
  cp.execFileSync = original;
}

assert.strictEqual(repair.parseResult('{bad').accepted, false);
assert.strictEqual(repair.coordinate({ ownerResult: failure({ owner_attempts: 1 }), ownerObserved: true }).accepted, false);
assert.strictEqual(repair.coordinate({
  ownerResult: failure(), ownerObserved: true, query: 'x'.repeat(16001)
}).rejection_reasons[0], 'incident_query_invalid');
assert(extensionSource.includes("require('./holoindex_incident_repair')"));
assert(extensionSource.includes('holoGenerationBoundQuery.isObserved(baseResult)'));
assert(extensionSource.includes('holoIncidentRepair.shouldCoordinate(baseResult, observed)'));
assert(extensionSource.includes('await holoIncidentRepair.coordinateAsync'));
assert((extensionSource.match(/holoIncidentRepair\.metadata\(incidentRepair\)/g) || []).length >= 4);
assert.strictEqual(pkg.version, '0.4.105');
assert(extensionSource.includes("const EXTENSION_VERSION = '0.4.105'"));
assert(!fs.readFileSync(path.join(extDir, 'holoindex_incident_repair.js'), 'utf8').includes('qwen'));

function asyncBase() {
  return {
    root: 'O:/repo', query: 'async repair', ownerResult: failure(),
    ownerObserved: true, interpreterPath: 'python', env: {}
  };
}

async function assertAsyncSuccess(base) {
  let eventLoopAdvanced = false;
  let invocation = null;
  let payload = null;
  const resultPromise = repair.coordinateAsync(Object.assign({}, base, {
    execFile: (interpreter, args, options, callback) => {
      invocation = { interpreter, args, options };
      const child = { kill() {}, stdin: { end(value) {
        payload = JSON.parse(value);
        setTimeout(() => callback(null, JSON.stringify({
          accepted: true, status: 'QUEUED', rejection_reasons: []
        })), 20);
      } } };
      return child;
    }
  }));
  setImmediate(() => { eventLoopAdvanced = true; });
  const asyncResult = await resultPromise;
  assert.strictEqual(eventLoopAdvanced, true, 'incident repair blocked the event loop');
  assert.strictEqual(asyncResult.status, 'QUEUED');
  assert.strictEqual(invocation.options.timeout, 90000);
  assert.strictEqual(invocation.options.maxBuffer, 256 * 1024);
  assert.strictEqual(payload.owner_failure.error, 'SEMANTIC_BACKEND_UNAVAILABLE');
}

async function assertAsyncCancellation(base) {
  const registry = ownerBridge.createProcessLifecycleRegistry();
  const lifecycle = registry.begin();
  let lateCallback;
  let kills = 0;
  const cancelled = repair.coordinateAsync(Object.assign({}, base, { lifecycle,
    execFile: (_exe, _args, _options, callback) => {
      lateCallback = callback;
      return { kill: () => { kills += 1; }, stdin: { end() {} } };
    }
  }));
  registry.dispose();
  const cancelledResult = await cancelled;
  assert.strictEqual(cancelledResult.rejection_reasons[0], 'incident_repair_cancelled');
  assert.strictEqual(kills, 1);
  lateCallback(null, JSON.stringify({ accepted: true, status: 'QUEUED' }));
  await new Promise((resolve) => setImmediate(resolve));
  assert.strictEqual(cancelledResult.status, 'REJECTED', 'late callback reopened settlement');
}

async function assertAsyncInputFailures(base) {
  let missingInputKills = 0;
  const missingInput = await repair.coordinateAsync(Object.assign({}, base, {
    execFile: () => ({ kill: () => { missingInputKills += 1; } })
  }));
  assert.strictEqual(missingInput.accepted, false);
  assert.strictEqual(missingInputKills, 1);

  const stdin = new EventEmitter();
  let pipeKills = 0;
  stdin.end = () => setImmediate(() => stdin.emit('error', Object.assign(
    new Error('broken pipe'), { code: 'EPIPE' }
  )));
  const pipeResult = await repair.coordinateAsync(Object.assign({}, base, {
    execFile: () => ({ stdin, kill: () => { pipeKills += 1; } })
  }));
  assert.strictEqual(pipeResult.accepted, false);
  assert.strictEqual(pipeKills, 1);
}

async function assertAsyncTimeout(base) {
  const timeout = await repair.coordinateAsync(Object.assign({}, base, {
    execFile: (_exe, _args, _options, callback) => {
      setImmediate(() => callback(Object.assign(new Error('timeout'), { code: 'ETIMEDOUT' })));
      return { stdin: { end() {} }, kill() {} };
    }
  }));
  assert.strictEqual(timeout.rejection_reasons[0], 'bridge_timeout');
}

async function asyncContracts() {
  const base = asyncBase();
  await assertAsyncSuccess(base);
  await assertAsyncCancellation(base);
  await assertAsyncInputFailures(base);
  await assertAsyncTimeout(base);
  console.log('RedDog HoloIndex incident repair extension tests passed.');
}

asyncContracts().catch((error) => {
  console.error(error && error.stack || error);
  process.exitCode = 1;
});
