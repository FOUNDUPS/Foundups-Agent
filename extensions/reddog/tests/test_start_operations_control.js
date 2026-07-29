'use strict';

const assert = require('assert');
const cp = require('child_process');
const EventEmitter = require('events');
const fs = require('fs');
const os = require('os');
const path = require('path');

const protocol = require(path.join('..', 'start_operations_control.js'));
const bridge = require(path.join('..', 'start_operations_bridge.js'));
const adapter = require(path.join('..', 'start_operations_extension_adapter.js'));
const operationsEnvironment = require(path.join('..', 'start_operations_environment.js'));
const interpreterPolicy = require(path.join('..', 'start_operations_interpreter.js'));
const grounding = require(path.join('..', 'grounded_target_continuity.js'));

function signedResult(request, overrides) {
  const value = Object.assign(protocol.failureResult(
    request.action, 'none', request
  ), {
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

function signedProgress(request) {
  const value = {
    schema_version: protocol.PROGRESS_SCHEMA,
    stage: 'resident_cycle_submitting',
    action: request.action,
    control_request_id: request.control_request_id,
    intent_id: 'sha256:' + 'a'.repeat(64),
    repo_head_sha: 'c'.repeat(40),
    operations_profile_id: protocol.PROFILE_ID
  };
  value.progress_id = grounding.canonicalDigest(value);
  return value;
}

function pythonResult(request) {
  const repoRoot = path.resolve(__dirname, '..', '..', '..');
  const code = [
    'from modules.communication.moltbot_bridge.src.reddog_start_operations_control_receipt import reject,result_json',
    'from modules.communication.moltbot_bridge.src.reddog_start_operations_profile import StartOperationsProfile',
    `print(result_json(reject("submit", StartOperationsProfile(), {}, ("test_rejection",), control_request_id="${request.control_request_id}")))`
  ].join(';');
  const executable = process.env.PYTHON || 'python';
  return JSON.parse(cp.execFileSync(
    executable, ['-B', '-c', code], { cwd: repoRoot, encoding: 'utf8' }
  ).trim());
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

function chunkedChild(chunks) {
  const child = new EventEmitter();
  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  child.stdin = { end() {} };
  child.kill = () => { child.killed = true; };
  process.nextTick(() => {
    for (const chunk of chunks) child.stdout.emit('data', chunk);
    child.emit('close', 0);
  });
  return child;
}

function approvedRuntime() {
  const repoRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-operations-'));
  const bin = path.join(repoRoot, '.venv', 'Scripts');
  fs.mkdirSync(bin, { recursive: true });
  const interpreter = path.join(bin, 'python.exe');
  fs.writeFileSync(interpreter, '');
  return { repoRoot, interpreter };
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

  const request = protocol.buildRequest(
    { action: 'submit' }, '', 'O:\\Foundups-Agent'
  );
  const progress = signedProgress(request);
  const terminal = signedResult(request);
  assert(protocol.validateProgress(progress, request));
  assert(protocol.validateResult(terminal, request));
  assert(protocol.validateResult(pythonResult(request), request));
  const tampered = { ...terminal, status: 'ATTACKER' };
  assert.strictEqual(protocol.validateResult(tampered, request), null);
  const unsafe = signedResult(request, { no_repo_mutation_performed: false });
  assert.strictEqual(protocol.validateResult(unsafe, request), null);
  const staleRequest = protocol.buildRequest(
    { action: 'status' }, 'sha256:' + 'd'.repeat(64), 'O:\\Foundups-Agent'
  );
  assert.strictEqual(protocol.validateResult(terminal, staleRequest), null);

  let observedProgress = null;
  const runtime = approvedRuntime();
  assert.strictEqual(
    interpreterPolicy.approved(runtime.interpreter, runtime.repoRoot),
    fs.realpathSync(runtime.interpreter)
  );
  assert.strictEqual(interpreterPolicy.approved('python', runtime.repoRoot), '');
  const result = await bridge.run({
    interpreter: runtime.interpreter,
    script: 'bridge.py',
    repoRoot: runtime.repoRoot,
    env: {},
    request,
    spawn: () => fakeChild([JSON.stringify(progress), JSON.stringify(terminal)]),
    deadlineMs: 1000,
    onProgress: (value) => { observedProgress = value; }
  });
  assert.strictEqual(result.accepted, true);
  assert.strictEqual(observedProgress.intent_id, progress.intent_id);
  const line = JSON.stringify({ ignored: 'x'.repeat(9000) }) + '\n';
  const oversized = await bridge.run({
    interpreter: runtime.interpreter, script: 'bridge.py',
    repoRoot: runtime.repoRoot,
    env: {}, request, spawn: () => chunkedChild([
      line.repeat(125), line.repeat(125)
    ]), deadlineMs: 1000
  });
  assert(oversized.rejection_reasons.includes(
    'start_operations_bridge_output_too_large'
  ));

  const originalRun = bridge.run;
  const state = {};
  let persisted = '';
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
      persistIntentId: (value) => { persisted = value; },
      postStatus: (text) => statuses.push(text),
      postResult: (value) => { posted = value; }
    }), true);
  } finally {
    bridge.run = originalRun;
  }
  assert.strictEqual(state.operationsIntentId, terminal.intent_id);
  assert.strictEqual(persisted, terminal.intent_id);
  assert.strictEqual(posted.ok, true);
  assert(statuses.some((text) => text.includes('submit requested')));
  assert(statuses.some((text) => text.includes('Resident cycle submitted')));
  const filtered = operationsEnvironment.build({
    PATH: 'runtime-path',
    PYTHONPATH: 'C:/attacker',
    PYTHONHOME: 'C:/attacker-home',
    OPENROUTER_API_KEY: 'required-secret',
    GITHUB_TOKEN: 'forbidden',
    REDDOG_SOVEREIGN_TOKEN: 'forbidden'
  });
  assert.strictEqual(filtered.PATH, 'runtime-path');
  assert.strictEqual(filtered.OPENROUTER_API_KEY, 'required-secret');
  assert.strictEqual(filtered.PYTHONPATH, undefined);
  assert.strictEqual(filtered.PYTHONHOME, undefined);
  assert.strictEqual(filtered.PYTHONNOUSERSITE, '1');
  assert.strictEqual(filtered.GITHUB_TOKEN, undefined);
  assert.strictEqual(filtered.REDDOG_SOVEREIGN_TOKEN, undefined);
  fs.rmSync(runtime.repoRoot, { recursive: true, force: true });
  console.log('start operations control tests passed');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
