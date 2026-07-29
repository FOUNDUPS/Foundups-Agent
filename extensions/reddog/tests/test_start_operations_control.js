'use strict';

const assert = require('assert');
const cp = require('child_process');
const EventEmitter = require('events');
const fs = require('fs');
const os = require('os');
const path = require('path');

const protocol = require(path.join('..', 'start_operations_control.js'));
const bridge = require(path.join('..', 'start_operations_bridge.js'));
const runtimeMaterializer = require(
  path.join('..', 'backend_compatibility_runtime_materializer.js')
);
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
  const sitePackages = path.join(repoRoot, '.venv', 'Lib', 'site-packages');
  fs.mkdirSync(bin, { recursive: true });
  fs.mkdirSync(sitePackages, { recursive: true });
  const interpreter = path.join(bin, 'python.exe');
  fs.writeFileSync(interpreter, '');
  return { repoRoot, interpreter, sitePackages };
}

function fakeMaterializer(runtime) {
  return () => ({
    runtimeRoot: runtime.repoRoot,
    targetRepoRoot: runtime.repoRoot,
    scriptPath: (value) => value,
    cleanup() {}
  });
}

function assertStartupHooksExcluded() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-python-seal-'));
  const venv = path.join(root, '.venv');
  cp.execFileSync(process.env.PYTHON || 'python', ['-m', 'venv', venv]);
  const interpreter = path.join(venv, 'Scripts', 'python.exe');
  const dependencies = path.join(venv, 'Lib', 'site-packages');
  const sentinel = path.join(root, 'startup-hook-ran');
  const source = path.join(root, 'sealed-source');
  const target = path.join(root, 'audited-target');
  fs.mkdirSync(source);
  fs.mkdirSync(target);
  fs.writeFileSync(
    path.join(dependencies, 'attacker.pth'),
    `import pathlib;pathlib.Path(${JSON.stringify(sentinel)}).write_text("x")\n`
  );
  fs.writeFileSync(path.join(dependencies, 'dep_probe.py'), 'VALUE="dependency"\n');
  const attacker = [
    'import pathlib',
    `pathlib.Path(${JSON.stringify(sentinel)}).write_text("x")`
  ].join(';');
  fs.writeFileSync(path.join(target, 'json.py'), attacker + '\n');
  fs.writeFileSync(path.join(target, 'dep_probe.py'), attacker + '\n');
  const script = path.join(source, 'probe.py');
  fs.writeFileSync(
    script,
    'import json,dep_probe\nprint("sealed:"+dep_probe.VALUE)\n'
  );
  const runtime = interpreterPolicy.approved(interpreter, root);
  const args = [
    '-I', '-S', '-B', '-c', bridge.PYTHON_BOOTSTRAP,
    script, source, target, runtime.sitePackages
  ];
  assert.strictEqual(cp.execFileSync(
    runtime.interpreter, args, { cwd: root, encoding: 'utf8' }
  ).trim(), 'sealed:dependency');
  assert.strictEqual(fs.existsSync(sentinel), false);
  fs.rmSync(root, { recursive: true, force: true });
}

function assertRuntimeMaterialized() {
  const repoRoot = path.resolve(__dirname, '..', '..', '..');
  assert.throws(
    () => runtimeMaterializer.materialize(repoRoot, { tempRoot: repoRoot }),
    /runtime_root_not_separated/
  );
  const runtime = runtimeMaterializer.materialize(repoRoot);
  try {
    assert.strictEqual(
      fs.existsSync(runtime.scriptPath(
        path.join(repoRoot, 'scripts', 'reddog_start_operations_control_once.py')
      )),
      true
    );
    const relative = path.relative(repoRoot, runtime.runtimeRoot);
    assert(relative.startsWith('..') || path.isAbsolute(relative));
  } finally {
    runtime.cleanup();
  }
}

function assertRedirectedVenvRejected() {
  const repoRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-repo-'));
  const external = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-venv-'));
  const bin = path.join(external, 'Scripts');
  fs.mkdirSync(bin, { recursive: true });
  fs.mkdirSync(path.join(external, 'Lib', 'site-packages'), { recursive: true });
  const interpreter = path.join(bin, 'python.exe');
  fs.writeFileSync(interpreter, '');
  fs.symlinkSync(external, path.join(repoRoot, '.venv'), 'junction');
  assert.strictEqual(interpreterPolicy.approved(interpreter, repoRoot), '');
  fs.rmSync(repoRoot, { recursive: true, force: true });
  fs.rmSync(external, { recursive: true, force: true });
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
  const approved = interpreterPolicy.approved(
    runtime.interpreter, runtime.repoRoot
  );
  assert.strictEqual(approved.interpreter, fs.realpathSync(runtime.interpreter));
  assert.strictEqual(approved.sitePackages, fs.realpathSync(runtime.sitePackages));
  assert.strictEqual(interpreterPolicy.approved('python', runtime.repoRoot), '');
  assertStartupHooksExcluded();
  assertRedirectedVenvRejected();
  const result = await bridge.run({
    interpreter: runtime.interpreter,
    script: 'bridge.py',
    repoRoot: runtime.repoRoot,
    env: {},
    materialize: fakeMaterializer(runtime),
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
    env: {}, request, materialize: fakeMaterializer(runtime),
    spawn: () => chunkedChild([
      line.repeat(125), line.repeat(125)
    ]), deadlineMs: 1000
  });
  assert(oversized.rejection_reasons.includes(
    'start_operations_bridge_output_too_large'
  ));
  let overLimitCallbacks = 0;
  const overLimitFrames = Array.from(
    { length: bridge.MAX_FRAMES + 1 },
    () => JSON.stringify(progress)
  );
  const overLimit = await bridge.run({
    interpreter: runtime.interpreter,
    script: 'bridge.py',
    repoRoot: runtime.repoRoot,
    env: {},
    request,
    materialize: fakeMaterializer(runtime),
    spawn: () => fakeChild(overLimitFrames),
    deadlineMs: 1000,
    onProgress: () => { overLimitCallbacks += 1; }
  });
  assert(overLimit.rejection_reasons.includes(
    'start_operations_bridge_frame_limit_exceeded'
  ));
  assert.strictEqual(overLimitCallbacks, bridge.MAX_FRAMES);

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
  assertRuntimeMaterialized();
  fs.rmSync(runtime.repoRoot, { recursive: true, force: true });
  console.log('start operations control tests passed');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
