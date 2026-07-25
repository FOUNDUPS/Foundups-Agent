'use strict';

const assert = require('assert');
const EventEmitter = require('events');
const path = require('path');

const query = require(path.join('..', 'model_runtime_binding_query.js'));

function receipt(overrides) {
  const value = Object.assign({
    schema_version: query.SCHEMA_VERSION,
    configured: true,
    accepted: true,
    status: query.STATUS_READY,
    binding_receipt_id: 'reddog_model_runtime_binding:' + 'a'.repeat(64),
    runtime_surface: 'reddog_backend_architect',
    catalog_snapshot_id: 'model_catalog_snapshot:test',
    selection_receipt_id: 'model_selection_receipt:test',
    task_family: 'reddog_runtime_model_call',
    principal_model: 'openai/gpt-5.6-sol',
    panel_models: ['deepseek/deepseek-v4-pro', 'moonshotai/kimi-k3'],
    role_bindings: [
      { role: 'principal', model_id: 'openai/gpt-5.6-sol', provider: 'openai' },
      { role: 'critic_1', model_id: 'deepseek/deepseek-v4-pro', provider: 'deepseek' },
      { role: 'critic_2', model_id: 'moonshotai/kimi-k3', provider: 'moonshotai' }
    ],
    benchmark_evidence_receipt_ids: ['a', 'b', 'c'],
    promotion_evidence_receipt_ids: ['d', 'e', 'f'],
    signed_promotion_receipt_ids: ['g', 'h', 'i'],
    min_verifier_pass_rate: 0.9,
    rejection_reasons: [],
    no_model_call_performed: true,
    no_holoindex_query_performed: true,
    no_holoindex_reindex_performed: true,
    no_command_execution_performed: true,
    no_repo_mutation_performed: true,
    no_runtime_artifact_mutation_performed: true
  }, overrides || {});
  const body = { ...value };
  delete body.query_receipt_id;
  value.query_receipt_id = query.canonicalDigest(body);
  return value;
}

function fakeChild(output) {
  const child = new EventEmitter();
  child.stdout = new EventEmitter();
  child.stdin = { end() {} };
  child.kill = () => {};
  process.nextTick(() => {
    child.stdout.emit('data', JSON.stringify(output) + '\n');
    child.emit('close', 0);
  });
  return child;
}

async function main() {
  const valid = query.validateReceipt(receipt());
  assert.strictEqual(valid.accepted, true);
  const worker = query.resolveWorker(
    { title: 'RedDog', lead: 'fallback/lead', panel: ['fallback/critic'] },
    valid,
    6
  );
  assert.strictEqual(worker.lead, 'openai/gpt-5.6-sol');
  assert.deepStrictEqual(worker.panel, ['deepseek/deepseek-v4-pro', 'moonshotai/kimi-k3']);
  assert.strictEqual(worker.modelBindingSource, 'receipt_bound_runtime');

  const unconfiguredBody = {
    ...query.failureReceipt(false, 'model_runtime_binding_unconfigured'),
    rejection_reasons: []
  };
  unconfiguredBody.query_receipt_id = query.canonicalDigest(unconfiguredBody);
  const fallback = query.resolveWorker(
    { title: 'RedDog', lead: 'fallback/lead', panel: ['fallback/critic'] },
    unconfiguredBody,
    6
  );
  assert.strictEqual(fallback.modelBindingSource, 'evaluation_config');
  assert.strictEqual(fallback.modelBindingBlocked, false);

  const rejected = query.resolveWorker(
    { title: 'RedDog', lead: 'fallback/lead', panel: ['fallback/critic'] },
    query.failureReceipt(true, 'artifact_invalid'),
    6
  );
  assert.strictEqual(rejected.modelBindingSource, 'runtime_binding_rejected');
  assert.strictEqual(rejected.modelBindingBlocked, true);

  const tampered = receipt();
  tampered.principal_model = 'attacker/forged';
  assert.strictEqual(query.validateReceipt(tampered).accepted, false);

  const verifierRole = receipt({
    role_bindings: [
      { role: 'principal', model_id: 'openai/gpt-5.6-sol', provider: 'openai' },
      { role: 'verifier', model_id: 'deepseek/deepseek-v4-pro', provider: 'deepseek' },
      { role: 'critic_2', model_id: 'moonshotai/kimi-k3', provider: 'moonshotai' }
    ]
  });
  assert.strictEqual(query.validateReceipt(verifierRole).accepted, false);

  const bridge = await query.runQuery({
    interpreter: 'python',
    script: 'bridge.py',
    repoRoot: 'O:\\Foundups-Agent',
    env: {},
    spawn: () => fakeChild(receipt()),
    timeoutMs: 1000
  });
  assert.strictEqual(bridge.accepted, true);
  console.log('model runtime binding query tests passed');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
