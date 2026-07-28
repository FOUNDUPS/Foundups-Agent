'use strict';

const assert = require('assert');
const EventEmitter = require('events');
const path = require('path');

const protocol = require(path.join('..', 'start_operations_control.js'));
const bridge = require(path.join('..', 'start_operations_bridge.js'));
const adapter = require(path.join('..', 'start_operations_extension_adapter.js'));
const grounding = require(path.join('..', 'grounded_target_continuity.js'));

function signedResult(overrides) {
  const value = Object.assign(protocol.failureResult('submit', 'none'), {
    accepted: true,
    status: 'DETERMINED',
    intent_id: 'sha256:' + 'a'.repeat(64),
    cycle_id: 'sha256:' + 'b'.repeat(64),
    repo_head_sha: 'c'.repeat(40),
    rejection_reasons: []
  }, overrides || {});
  const body = { ...value };
  delete body.response_id;
  value.response_id = grounding.canonicalDigest(body);
  return value;
}

function signedProgress() {
  const value = {
    schema_version: protocol.PROGRESS_SCHEMA,
    stage: 'resident_cycle_submitting',
    intent_id: 'sha256:' + 'a'.repeat(64),
    repo_head_sha: 'c'.repeat(40),
    operations_profile_id: protocol.PROFILE_ID
  };
  value.progress_id = grounding.canonicalDigest(value);
  return value;
}

function fakeChild(lines, exitCode) {
  const child = new EventEmitter();
  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  child.stdin = { end() {} };
  child.kill = () => { child.killed = true; };
  process.nextTick(() => {
    child.stdout.emit('data', lines.join('\n') + '\n');
    child.emit('close', exitCode || 0);
  });
  return child;
}

async function main() {
  assert.deepStrictEqual(protocol.classify('start operations').action, 'submit');
  assert.deepStrictEqual(protocol.classify('  START OPERATIONS  ').action, 'submit');
  assert.deepStrictEqual(protocol.classify('operations status').action, 'status');
  assert.deepStrictEqual(protocol.classify('stop operations').action, 'cancel');
  assert.deepStrictEqual(protocol.classify('resume operations').action, 'resume');
  for (const value of [
    'go', 'start operation', 'please start operations', 'start\noperations',
    'start\u200b operations', '\u0455tart operations'
  ]) {
    assert.strictEqual(protocol.classify(value), null, value + ' must not route');
  }
  assert.strictEqual(
    protocol.bindingRejection(
      { action: 'submit' },
      { modelBindingSource: 'evaluation_config' }
    ),
    'start_operations_requires_receipt_bound_model_runtime'
  );
  assert.strictEqual(
    protocol.bindingRejection(
      { action: 'submit' },
      { modelBindingSource: 'receipt_bound_runtime' }
    ),
    ''
  );
  assert.strictEqual(
    protocol.bindingRejection(
      { action: 'cancel' },
      { modelBindingSource: 'evaluation_config' }
    ),
    ''
  );

  const progress = signedProgress();
  const terminal = signedResult();
  assert(protocol.validateProgress(progress));
  assert(protocol.validateResult(terminal));
  const tampered = { ...terminal, status: 'ATTACKER' };
  assert.strictEqual(protocol.validateResult(tampered), null);
  const unsafe = signedResult({ no_repo_mutation_performed: false });
  assert.strictEqual(protocol.validateResult(unsafe), null);

  let observedProgress = null;
  const result = await bridge.run({
    interpreter: 'python',
    script: 'bridge.py',
    repoRoot: 'O:\\Foundups-Agent',
    env: {},
    request: protocol.buildRequest({ action: 'submit' }, '', 'O:\\Foundups-Agent'),
    spawn: () => fakeChild([JSON.stringify(progress), JSON.stringify(terminal)]),
    deadlineMs: 1000,
    onProgress: (value) => { observedProgress = value; }
  });
  assert.strictEqual(result.accepted, true);
  assert.strictEqual(observedProgress.intent_id, progress.intent_id);

  const originalRun = bridge.run;
  const state = {};
  const statuses = [];
  let posted = null;
  bridge.run = async (options) => {
    options.onProgress(progress);
    return terminal;
  };
  try {
    assert.strictEqual(await adapter.handleMessage({
      text: 'ordinary audit request',
      state,
      postStatus() {},
      postResult() {}
    }), false);
    assert.strictEqual(await adapter.handleMessage({
      text: 'start operations',
      worker: { modelBindingSource: 'receipt_bound_runtime' },
      state,
      interpreter: 'python',
      script: 'bridge.py',
      repoRoot: 'O:\\Foundups-Agent',
      env: {},
      postStatus: (text) => statuses.push(text),
      postResult: (value) => { posted = value; }
    }), true);
  } finally {
    bridge.run = originalRun;
  }
  assert.strictEqual(state.operationsIntentId, terminal.intent_id);
  assert.strictEqual(posted.ok, true);
  assert(statuses.some((text) => text.includes('submit requested')));
  assert(statuses.some((text) => text.includes('Resident cycle submitted')));
  console.log('start operations control tests passed');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
