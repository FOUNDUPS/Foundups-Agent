'use strict';

const assert = require('assert');
const cp = require('child_process');
const fs = require('fs');
const path = require('path');

const extDir = path.resolve(__dirname, '..');
const repair = require(path.join(extDir, 'holoindex_incident_repair.js'));
const extensionSource = fs.readFileSync(path.join(extDir, 'extension.js'), 'utf8');
const pkg = JSON.parse(fs.readFileSync(path.join(extDir, 'package.json'), 'utf8'));
const HEAD = 'a'.repeat(40);
const ROOT_DIGEST = 'sha256:' + 'b'.repeat(64);

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
assert.strictEqual(repair.shouldCoordinate(failure(), false), false);
assert.strictEqual(repair.shouldCoordinate(failure({ owner_attempts: 1 }), true), false);
assert.strictEqual(repair.shouldCoordinate(failure({ error: 'forged' }), true), false);
assert.strictEqual(repair.shouldCoordinate(failure({ ok: true }), true), false);
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
      incident_id: 'sha256:incident',
      task_id: 'holoindex_postmerge_refresh:' + 'a'.repeat(40),
      receipt_id: 'sha256:receipt',
      maintenance_enqueued: true,
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

  const meta = repair.metadata(result);
  assert.strictEqual(meta.incident_repair_attempted, true);
  assert.strictEqual(meta.incident_repair_enqueued, true);
  assert.strictEqual(meta.incident_repair_coding_candidate_required, false);

  const huge = failure({ error: 'x'.repeat(8 * 1024 * 1024) });
  assert.strictEqual(repair.coordinate({
    root: 'O:/repo', query: 'bounded', ownerResult: huge,
    ownerObserved: true, interpreterPath: 'python'
  }).accepted, false);
  assert.strictEqual(calls, 1);

  const cyclic = failure();
  cyclic.untrusted = cyclic;
  assert.strictEqual(repair.coordinate({
    root: 'O:/repo', query: 'bounded', ownerResult: cyclic,
    ownerObserved: true, interpreterPath: 'python'
  }).accepted, false);
  assert.strictEqual(calls, 1);
} finally {
  cp.execFileSync = original;
}

assert.strictEqual(repair.parseResult('{bad').accepted, false);
assert.strictEqual(repair.coordinate({ ownerResult: failure({ owner_attempts: 1 }), ownerObserved: true }).accepted, false);
assert.strictEqual(repair.coordinate({
  ownerResult: failure(), ownerObserved: true, query: 'x'.repeat(16001)
}).rejection_reasons[0], 'incident_query_invalid');
assert(extensionSource.includes("require('./holoindex_incident_repair')"));
assert(extensionSource.includes('holoGenerationBoundQuery.isObserved(ownerResult)'));
assert(extensionSource.includes('holoIncidentRepair.shouldCoordinate(ownerResult, ownerObserved)'));
assert(extensionSource.includes('coordinateHoloIndexIncident(root, query, ownerResult, ownerObserved)'));
assert((extensionSource.match(/holoIncidentRepair\.metadata\(incidentRepair\)/g) || []).length >= 4);
assert.strictEqual(pkg.version, '0.4.64');
assert(extensionSource.includes("const EXTENSION_VERSION = '0.4.64'"));
assert(!fs.readFileSync(path.join(extDir, 'holoindex_incident_repair.js'), 'utf8').includes('qwen'));

console.log('RedDog HoloIndex incident repair extension tests passed.');
