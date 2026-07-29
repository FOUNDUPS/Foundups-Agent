'use strict';

const assert = require('assert');
const EventEmitter = require('events');
const Module = require('module');
const path = require('path');
const health = require('../runtime_health_query');
const freshness = require('../model_freshness_query');
const diagnosticRouter = require('../local_diagnostic_router');
const workState = require('../authoritative_work_state_query');

const originalResolve = Module._resolveFilename;
const vscodePath = path.join(__dirname, '..', 'node_modules', 'vscode', 'index.js');
require.cache[vscodePath] = {
  exports: {
    window: {},
    workspace: { workspaceFolders: [], getConfiguration: () => ({ get: (_key, fallback) => fallback }) },
    commands: {},
    extensions: { getExtension: () => undefined },
    env: {},
    Uri: {},
    ViewColumn: { Beside: 2 }
  },
  loaded: true,
  id: vscodePath
};
Module._resolveFilename = function(request, parent, isMain, options) {
  if (request === 'vscode') return vscodePath;
  return originalResolve.call(this, request, parent, isMain, options);
};
const extension = require('../extension');
Module._resolveFilename = originalResolve;

function childFor(payload) {
  const child = new EventEmitter();
  child.stdout = new EventEmitter();
  child.stdin = {
    end: () => setImmediate(() => {
      child.stdout.emit('data', JSON.stringify(payload) + '\n');
      child.emit('close', 0);
    })
  };
  child.kill = () => {};
  return child;
}

async function main() {
  for (const prompt of [
    'test holoindex is it working?',
    'Is HoloIndex working?',
    'check holo index health'
  ]) assert.strictEqual(health.isRuntimeHealthQuestion(prompt), true, prompt);
  for (const prompt of [
    'fix HoloIndex',
    'reindex HoloIndex',
    'audit how HoloIndex health works',
    'is HoloIndex working and delete the index?',
    'is HoloIndex working; run shell diagnostics',
    '```text\ntest holoindex is it working?\n```'
  ]) assert.strictEqual(health.isRuntimeHealthQuestion(prompt), false, prompt);

  const healthClass = extension.classifyTaskForRedDog(
    'test holoindex is it working?', 'auto', 'reddog_architect'
  );
  assert.strictEqual(healthClass.tier, 'REGULAR');
  assert.strictEqual(healthClass.localFastPath, 'runtime_health');
  assert.strictEqual(
    extension.resolveModelMode(healthClass, 'auto', 'reddog_architect'),
    'local_runtime_health'
  );
  assert.strictEqual(workState.isLocalFastPath('runtime_health'), true);
  const wireSource = require('fs').readFileSync(
    path.join(__dirname, '..', 'extension.js'), 'utf8'
  );
  assert(
    wireSource.indexOf('const localFastPath = authoritativeWorkStateQuery.isLocalFastPath')
      < wireSource.indexOf('if (modelBindingBlock && !localFastPath)'),
    'local diagnostics must be classified before model-binding admission'
  );
  const productionDiagnosticCall = wireSource.match(
    /const runLocalDiagnosticQuery = [^\n]+/
  )[0];
  assert.strictEqual(productionDiagnosticCall.includes('queryOwner'), false);
  assert.strictEqual(productionDiagnosticCall.includes('isAccepted'), false);

  const owner = {
    retrieval_mode: 'semantic',
    freshness_generation_id: 'sha256:' + 'a'.repeat(64),
    repo_head_sha: '1'.repeat(40),
    query_receipt: { receipt_id: 'sha256:' + 'b'.repeat(64) },
    index_gap_detected: false,
    no_holoindex_reindex_performed: true
  };
  const healthResult = await health.runHoloIndexHealth({
    root: 'O:/repo',
    interpreterPath: 'python',
    env: {},
    queryOwner: () => owner,
    isAccepted: (value) => value === owner
  });
  assert.strictEqual(healthResult.made_network_call, false);
  assert.strictEqual(healthResult.diagnostic_ready, true);
  assert.strictEqual(healthResult.review_packet.health_ready, true);
  assert(healthResult.content.includes('HoloIndex is working'));
  class SilentWorker extends EventEmitter {
    terminate() { this.terminated = true; }
  }
  const timedHealth = await health.runHoloIndexHealth({
    root: 'O:/repo', interpreterPath: 'python', env: {},
    Worker: SilentWorker, timeoutMs: 1
  });
  assert.strictEqual(timedHealth.diagnostic_ready, false);
  assert.strictEqual(timedHealth.review_packet.error, 'holoindex_health_timeout');

  for (const prompt of [
    'are models the latest?',
    'Are we using the newest model panel?',
    'check principal model freshness'
  ]) assert.strictEqual(freshness.isModelFreshnessQuestion(prompt), true, prompt);
  for (const prompt of [
    'switch to the latest models',
    'benchmark the newest models',
    'implement model selection',
    'are models the latest and delete old model configs?',
    'are the latest models safe to deploy?'
  ]) assert.strictEqual(freshness.isModelFreshnessQuestion(prompt), false, prompt);

  const modelClass = extension.classifyTaskForRedDog(
    'are models the latest?', 'auto', 'reddog_architect'
  );
  assert.strictEqual(modelClass.tier, 'REGULAR');
  assert.strictEqual(modelClass.localFastPath, 'model_freshness');
  assert.strictEqual(
    extension.resolveModelMode(modelClass, 'auto', 'reddog_architect'),
    'local_model_freshness'
  );

  const now = Date.now();
  const receipt = {
    schema_version: 'reddog_model_freshness_query.v1',
    accepted: true,
    status: 'MODEL_FRESHNESS_READY',
    rejection_reasons: [],
    requested_model_ids: ['z-ai/glm-5.2'],
    provider_receipt_id: 'model_provider_catalog_discovery_receipt:' + 'c'.repeat(64),
    candidate_snapshot_id: 'model_provider_catalog_candidate_snapshot:' + 'd'.repeat(64),
    observed_at_ms: now - 1000,
    fresh_until_ms: now + 60000,
    queried_at_ms: now,
    configured_models: [{
      model_id: 'z-ai/glm-5.2',
      available: true,
      canonical_slug: 'z-ai/glm-5.2-20260616',
      created: 1781631930,
      chronology_known: true,
      provider_latest_known: true,
      newer_provider_model_ids: []
    }],
    provider: 'openrouter',
    provider_endpoint: 'https://openrouter.ai/api/v1/models',
    catalog_fresh: true,
    all_configured_models_available: true,
    chronology_complete: true,
    all_configured_models_provider_latest: true,
    latestness_status: 'ALL_PROVIDER_LATEST',
    credential_free_catalog_egress: true,
    public_catalog_egress_gate: 'PASS',
    external_catalog_call_performed: true,
    no_model_inference_performed: true,
    no_model_selection_changed: true,
    no_runtime_binding_changed: true,
    no_repository_mutation_performed: true,
    no_holoindex_reindex_performed: true
  };
  receipt.receipt_id = freshness.digest(receipt);
  const parsed = await freshness.runConfiguredQuery({
    interpreter: 'python',
    script: 'freshness.py',
    repoRoot: 'O:/repo',
    env: {},
    modelIds: ['z-ai/glm-5.2'],
    spawn: () => childFor(receipt)
  });
  assert.strictEqual(parsed.accepted, true);
  const local = freshness.buildLocalResult(parsed);
  assert.strictEqual(local.made_network_call, true);
  assert.strictEqual(local.diagnostic_ready, true);
  assert.strictEqual(local.review_packet.model_freshness_ready, true);
  assert(local.content.includes('challenger, not an automatic production replacement'));

  const forged = { ...receipt, configured_models: [{ ...receipt.configured_models[0], available: false }] };
  assert.strictEqual(freshness.validate(forged).accepted, false);
  assert.strictEqual(freshness.validate(forged).rejection_reasons[0], 'model_freshness_receipt_invalid');
  const substituted = {
    ...receipt,
    requested_model_ids: ['attacker/model'],
    configured_models: [{ ...receipt.configured_models[0], model_id: 'attacker/model' }]
  };
  delete substituted.receipt_id;
  substituted.receipt_id = freshness.digest(substituted);
  assert.strictEqual(
    freshness.validate(substituted, ['z-ai/glm-5.2'], now).rejection_reasons[0],
    'model_freshness_request_binding_invalid'
  );

  const stale = { ...receipt, fresh_until_ms: now - 1 };
  delete stale.receipt_id;
  stale.receipt_id = freshness.digest(stale);
  assert.strictEqual(freshness.validate(stale, ['z-ai/glm-5.2'], now).accepted, false);
  const future = { ...receipt, observed_at_ms: now + 1 };
  delete future.receipt_id;
  future.receipt_id = freshness.digest(future);
  assert.strictEqual(freshness.validate(future, ['z-ai/glm-5.2'], now).accepted, false);
  const extra = { ...receipt, attacker_field: true };
  delete extra.receipt_id;
  extra.receipt_id = freshness.digest(extra);
  assert.strictEqual(freshness.validate(extra, ['z-ai/glm-5.2'], now).accepted, false);

  const secretFree = diagnosticRouter.catalogEnvironment({
    SystemRoot: 'C:/Windows',
    TEMP: 'C:/Temp',
    OPENROUTER_API_KEY: 'must-not-cross',
    GITHUB_TOKEN: 'must-not-cross',
    REDDOG_SOVEREIGN_TOKEN: 'must-not-cross'
  });
  assert.strictEqual(secretFree.SystemRoot, 'C:/Windows');
  assert.strictEqual(secretFree.OPENROUTER_API_KEY, undefined);
  assert.strictEqual(secretFree.GITHUB_TOKEN, undefined);
  assert.strictEqual(secretFree.REDDOG_SOVEREIGN_TOKEN, undefined);

  const spawnFailure = await freshness.runConfiguredQuery({
    spawn: () => { throw new Error('blocked'); }
  });
  assert.deepStrictEqual(spawnFailure.rejection_reasons, ['model_freshness_bridge_spawn_failed']);
  const timeoutChild = new EventEmitter();
  timeoutChild.stdout = new EventEmitter();
  timeoutChild.stdin = { end: () => {} };
  timeoutChild.kill = () => { timeoutChild.killed = true; };
  const timedOut = await freshness.runConfiguredQuery({
    interpreter: 'python', script: 'freshness.py', repoRoot: 'O:/repo',
    env: {}, modelIds: ['z-ai/glm-5.2'], timeoutMs: 1,
    spawn: () => timeoutChild
  });
  assert.deepStrictEqual(timedOut.rejection_reasons, ['model_freshness_bridge_timeout']);
  assert.strictEqual(timeoutChild.killed, true);

  const oversized = childFor(receipt);
  oversized.stdin.end = () => setImmediate(() => {
    oversized.stdout.emit('data', 'x'.repeat(1024 * 1024 + 1));
  });
  const tooLarge = await freshness.runConfiguredQuery({
    interpreter: 'python', script: 'freshness.py', repoRoot: 'O:/repo',
    env: {}, modelIds: ['z-ai/glm-5.2'], spawn: () => oversized
  });
  assert.deepStrictEqual(tooLarge.rejection_reasons, ['model_freshness_bridge_output_too_large']);
  console.log('health and model freshness query tests passed');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
