'use strict';
const assert = require('assert');
const cp = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const protocol = require(path.join('..', 'start_operations_control.js'));
const bridge = require(path.join('..', 'start_operations_bridge.js'));
const sealedJsonOnce = require(path.join('..', 'sealed_python_json_once.js'))
  .createSealedPythonJsonRunner();
const runtimeMaterializer = require(
  path.join('..', 'backend_compatibility_runtime_materializer.js')
);
const adapter = require(path.join('..', 'start_operations_extension_adapter.js'));
const operationsEnvironment = require(path.join('..', 'start_operations_environment.js'));
const interpreterPolicy = require(path.join('..', 'start_operations_interpreter.js'));
const grounding = require(path.join('..', 'grounded_target_continuity.js'));
const helpers = require('./start_operations_control_test_helpers');
const { approvedRuntime, chunkedChild, fakeChild, fakeMaterializer, pythonResult, signedProgress, signedResult } = helpers;
function startupFixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-python-seal-'));
  const venv = path.join(root, '.venv');
  cp.execFileSync(process.env.PYTHON || 'python', ['-m', 'venv', venv]);
  const dependencies = path.join(venv, 'Lib', 'site-packages');
  const sentinel = path.join(root, 'startup-hook-ran');
  const source = path.join(root, 'sealed-source');
  const target = path.join(root, 'audited-target');
  fs.mkdirSync(source); fs.mkdirSync(target);
  fs.mkdirSync(path.join(target, '.git'));
  return { root, interpreter: path.join(venv, 'Scripts', 'python.exe'),
    dependencies, sentinel, source, target };
}
function writeStartupAttackers(fixture) {
  const { dependencies, sentinel, source, target } = fixture;
  fs.writeFileSync(
    path.join(dependencies, 'attacker.pth'),
    `import pathlib;pathlib.Path(${JSON.stringify(sentinel)}).write_text("x")\n`
  );
  fs.writeFileSync(path.join(dependencies, 'dep_probe.py'), 'VALUE="dependency"\n');
  const sourcePackage = path.join(source, 'modules');
  const dependencyPackage = path.join(dependencies, 'modules');
  const attacker = [
    'import pathlib',
    `pathlib.Path(${JSON.stringify(sentinel)}).write_text("x")`
  ].join(';');
  fs.mkdirSync(sourcePackage);
  fs.mkdirSync(dependencyPackage);
  fs.writeFileSync(path.join(sourcePackage, '__init__.py'), '');
  fs.writeFileSync(path.join(sourcePackage, 'probe.py'), 'VALUE="source"\n');
  fs.writeFileSync(path.join(source, 'policy.txt'), 'manifest-policy\n');
  fs.writeFileSync(path.join(dependencyPackage, '__init__.py'), attacker + '\n');
  fs.writeFileSync(path.join(dependencyPackage, 'probe.py'), attacker + '\n');
  fs.writeFileSync(path.join(target, 'json.py'), attacker + '\n');
  fs.writeFileSync(path.join(target, 'dep_probe.py'), attacker + '\n');
  return sourcePackage;
}
function writeStartupSource(fixture, sourcePackage) {
  const { source, target } = fixture;
  const script = path.join(source, 'probe.py');
  const policy = path.join(source, 'policy.txt');
  fs.writeFileSync(
    script,
    'import json,dep_probe,os\nfrom modules import probe\n'
      + 'print("sealed:"+dep_probe.VALUE+":"+probe.VALUE+":"'
      + '+os.environ["REDDOG_SEALED_RUNTIME_TARGET_REPO_ROOT"]+":"'
      + '+REDDOG_VERIFIED_RUNTIME_READ_TEXT('
      + '__file__.replace("probe.py","policy.txt")).strip())\n'
  );
  const relativeFiles = [
    'probe.py', 'policy.txt', 'modules/__init__.py', 'modules/probe.py'
  ];
  return { script, policy, relativeFiles, sourcePackage, target };
}
function startupManifest(fixture, sourceState) {
  const runtimeDigests = {};
  for (const relative of sourceState.relativeFiles) {
    const raw = fs.readFileSync(path.join(fixture.source, relative));
    runtimeDigests[relative] = crypto.createHash('sha256').update(raw).digest('hex');
  }
  const manifest = { required_runtime_sha256: runtimeDigests };
  const manifestPath = path.join(fixture.source, '.reddog-runtime-manifest.json');
  fs.writeFileSync(manifestPath, JSON.stringify(manifest));
  return { manifestPath, manifestDigest: grounding.canonicalDigest(manifest).slice(7) };
}
function assertStartupHooksExcluded() {
  const fixture = startupFixture();
  const sourceState = writeStartupSource(fixture, writeStartupAttackers(fixture));
  const manifest = startupManifest(fixture, sourceState);
  const runtime = interpreterPolicy.approved(fixture.interpreter, fixture.root);
  const args = ['-I', '-S', '-B', bridge.PYTHON_BOOTSTRAP, sourceState.script,
    fixture.source, fixture.target, runtime.sitePackages,
    manifest.manifestPath, manifest.manifestDigest];
  assert.strictEqual(cp.execFileSync(
    runtime.interpreter, args, { cwd: fixture.root, encoding: 'utf8' }
  ).trim(), `sealed:dependency:source:${fixture.target}:manifest-policy`);
  assert.strictEqual(fs.existsSync(fixture.sentinel), false);
  fs.writeFileSync(sourceState.policy, 'attacker-policy\n');
  assert.throws(() => cp.execFileSync(runtime.interpreter, args,
    { cwd: fixture.root, encoding: 'utf8' }), /runtime_source_digest_mismatch/);
  fs.writeFileSync(sourceState.policy, 'manifest-policy\n');
  fs.rmSync(path.join(sourceState.sourcePackage, '__init__.py'));
  assert.throws(() => cp.execFileSync(runtime.interpreter, args,
    { cwd: fixture.root, encoding: 'utf8' }), /reserved_runtime_module_missing/);
  assert.strictEqual(fs.existsSync(fixture.sentinel), false);
  fs.rmSync(fixture.root, { recursive: true, force: true });
}
function assertRuntimeMaterialized() {
  const repoRoot = path.resolve(__dirname, '..', '..', '..');
  assert.throws(
    () => runtimeMaterializer.materialize(repoRoot, { tempRoot: repoRoot }),
    /runtime_root_not_separated/
  );
  const runtime = runtimeMaterializer.materialize(repoRoot);
  try {
    const script = runtime.scriptPath(
      path.join(repoRoot, 'scripts', 'reddog_start_operations_control_once.py')
    );
    assert.strictEqual(fs.existsSync(script), true);
    assert.strictEqual(fs.existsSync(runtime.manifestPath), true);
    const relative = path.relative(repoRoot, runtime.runtimeRoot);
    assert(relative.startsWith('..') || path.isAbsolute(relative));
    const sentinel = path.join(runtime.runtimeRoot, 'post-copy-tamper-ran');
    fs.writeFileSync(
      script,
      `import pathlib;pathlib.Path(${JSON.stringify(sentinel)}).write_text("x")\n`
    );
    const args = [
      '-I', '-S', '-B', bridge.PYTHON_BOOTSTRAP,
      script, runtime.runtimeRoot, repoRoot,
      path.dirname(process.execPath), runtime.manifestPath, runtime.manifestDigest
    ];
    assert.throws(
      () => cp.execFileSync(process.env.PYTHON || 'python', args),
      /runtime_source_digest_mismatch/
    );
    assert.strictEqual(fs.existsSync(sentinel), false);
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
function assertClassification() {
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
  assert.strictEqual(protocol.bindingRejection({ action: 'submit' },
    { modelBindingSource: 'evaluation_config' }),
  'start_operations_requires_receipt_bound_model_runtime');
  assert.strictEqual(protocol.bindingRejection({ action: 'submit' },
    { modelBindingSource: 'receipt_bound_runtime' }), '');
  assert.strictEqual(protocol.bindingRejection({ action: 'cancel' },
    { modelBindingSource: 'evaluation_config' }), '');
}
function validatedReceipts() {
  const request = protocol.buildRequest(
    { action: 'submit' }, '', 'O:\\Foundups-Agent'
  );
  const progress = signedProgress(request);
  const terminal = signedResult(request);
  assert(protocol.validateProgress(progress, request));
  assert(protocol.validateResult(terminal, request));
  const repaired = signedResult(request, {
    no_maintenance_performed: false,
    holo_repair_attempted: true,
    holo_repair_task_id: 'reddog_start_operations_holo_repair:abc',
    holo_repair_status: 'REPAIRED',
    holo_repair_generation_id: 'sha256:' + 'e'.repeat(64),
    holo_repair_freshness_receipt_digest: 'sha256:' + 'f'.repeat(64),
    grounding_retried_after_repair: true
  });
  assert(protocol.validateResult(repaired, request));
  const noRefreshRepaired = signedResult(request, {
    no_maintenance_performed: true,
    holo_repair_attempted: true,
    holo_repair_task_id: 'reddog_start_operations_holo_repair:abc',
    holo_repair_status: 'REPAIRED',
    holo_repair_generation_id: 'sha256:' + 'e'.repeat(64),
    holo_repair_freshness_receipt_digest: 'sha256:' + 'f'.repeat(64),
    grounding_retried_after_repair: true
  });
  assert(protocol.validateResult(noRefreshRepaired, request));
  return { request, progress, terminal };
}
function assertRejectedReceipts(receipts) {
  const { request, terminal } = receipts;
  assert.strictEqual(protocol.validateResult(signedResult(request, {
    no_maintenance_performed: false,
    holo_repair_attempted: true,
    holo_repair_task_id: 'reddog_start_operations_holo_repair:abc',
    holo_repair_status: 'REPAIRED',
    holo_repair_generation_id: 'sha256:attacker',
    holo_repair_freshness_receipt_digest: 'sha256:' + 'f'.repeat(64),
    grounding_retried_after_repair: true
  }), request), null);
  assert.strictEqual(protocol.validateResult(signedResult(request, {
    holo_repair_attempted: false,
    holo_repair_status: 'REPAIRED'
  }), request), null);
  assert(protocol.validateResult(pythonResult(request), request));
  const tampered = { ...terminal, status: 'ATTACKER' };
  assert.strictEqual(protocol.validateResult(tampered, request), null);
  const unsafe = signedResult(request, { no_repo_mutation_performed: false });
  assert.strictEqual(protocol.validateResult(unsafe, request), null);
  const staleRequest = protocol.buildRequest(
    { action: 'status' }, 'sha256:' + 'd'.repeat(64), 'O:\\Foundups-Agent'
  );
  assert.strictEqual(protocol.validateResult(terminal, staleRequest), null);
}
function assertSealedRuntime(runtime) {
  const approved = interpreterPolicy.approved(runtime.interpreter, runtime.repoRoot);
  assert.strictEqual(approved.interpreter, fs.realpathSync(runtime.interpreter));
  assert.strictEqual(approved.sitePackages, fs.realpathSync(runtime.sitePackages));
  assert.strictEqual(interpreterPolicy.approved('python', runtime.repoRoot), '');
  let sealedInvocation = null;
  const sealedResult = sealedJsonOnce.run({
    interpreter: runtime.interpreter, repoRoot: runtime.repoRoot,
    script: 'selector.py', request: { action: 'select' }, env: {},
    materialize: fakeMaterializer(runtime),
    execFileSync: (command, args, options) => {
      sealedInvocation = { command, args, options };
      return JSON.stringify({ accepted: true });
    }
  });
  assert.deepStrictEqual(sealedResult, { accepted: true });
  assert.strictEqual(sealedJsonOnce.isAccepted(sealedResult), true);
  assert.strictEqual(sealedJsonOnce.isAccepted(Object.assign({}, sealedResult)), false);
  assert.strictEqual(sealedInvocation.command, fs.realpathSync(runtime.interpreter));
  assert.deepStrictEqual(sealedInvocation.args.slice(0, 3), ['-I', '-S', '-B']);
  assert(sealedInvocation.args[3].startsWith(runtime.repoRoot));
  assert.strictEqual(sealedInvocation.options.env.REDDOG_SEALED_RUNTIME_REQUIRED, '1');
  assert.throws(() => sealedJsonOnce.run({
    interpreter: process.execPath, repoRoot: runtime.repoRoot,
    script: 'selector.py', request: {}
  }), /unapproved_interpreter/);
  assertStartupHooksExcluded();
  assertRedirectedVenvRejected();
}
async function assertBridgeSuccess(runtime, receipts) {
  const { request, progress, terminal } = receipts;
  let observedProgress = null;
  let spawnedEnvironment = null;
  const result = await bridge.run({
    interpreter: runtime.interpreter,
    script: 'bridge.py',
    repoRoot: runtime.repoRoot,
    env: {},
    materialize: fakeMaterializer(runtime),
    request,
    spawn: (_command, _args, options) => {
      spawnedEnvironment = options.env;
      return fakeChild([JSON.stringify(progress), JSON.stringify(terminal)]);
    },
    deadlineMs: 1000,
    onProgress: (value) => { observedProgress = value; }
  });
  assert.strictEqual(result.accepted, true);
  assert.strictEqual(observedProgress.intent_id, progress.intent_id);
  assert.strictEqual(spawnedEnvironment.REDDOG_SEALED_RUNTIME_REQUIRED, '1');
  assert.strictEqual(spawnedEnvironment.REDDOG_SEALED_RUNTIME_ROOT, runtime.repoRoot);
  assert(spawnedEnvironment.REDDOG_SEALED_RUNTIME_BOOTSTRAP_PATH.endsWith(
    path.join('extensions', 'reddog', 'start_operations_python_bootstrap.py')
  ));
}
async function assertBridgeByteBound(runtime, request) {
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
}
async function assertBridgeFrameBound(runtime, receipts) {
  const { request, progress } = receipts;
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
}
function adapterInput(state, capture) {
  return {
    text: 'start operations',
    worker: { modelBindingSource: 'receipt_bound_runtime' },
    state, interpreter: 'python', script: 'bridge.py',
    repoRoot: 'O:\\Foundups-Agent', env: {},
    persistIntentId: (value) => { capture.persisted = value; },
    postStatus: (text) => capture.statuses.push(text),
    postResult: (value) => { capture.posted = value; }
  };
}
async function runExtensionAdapter(receipts) {
  const { progress, terminal } = receipts;
  const originalRun = bridge.run;
  const state = {};
  const capture = { persisted: '', statuses: [], posted: null };
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
    assert.strictEqual(await adapter.handleMessage(adapterInput(state, capture)), true);
  } finally {
    bridge.run = originalRun;
  }
  return Object.assign({ state, terminal }, capture);
}
function assertExtensionAdapterResult(result) {
  assert.strictEqual(result.state.operationsIntentId, result.terminal.intent_id);
  assert.strictEqual(result.persisted, result.terminal.intent_id);
  assert.strictEqual(result.posted.ok, true);
  assert(result.statuses.some((text) => text.includes('submit requested')));
  assert(result.statuses.some((text) => text.includes('Resident cycle submitted')));
}
function assertOperationsEnvironment() {
  const filtered = operationsEnvironment.build({
    PATH: 'runtime-path',
    PYTHONPATH: 'C:/attacker',
    PYTHONHOME: 'C:/attacker-home',
    OPENROUTER_API_KEY: 'provider-only-marker',
    GITHUB_TOKEN: 'forbidden',
    REDDOG_SOVEREIGN_TOKEN: 'forbidden'
  });
  assert.strictEqual(filtered.PATH, 'runtime-path');
  assert.strictEqual(filtered.OPENROUTER_API_KEY, undefined);
  assert.strictEqual(filtered.PYTHONPATH, undefined);
  assert.strictEqual(filtered.PYTHONHOME, undefined);
  assert.strictEqual(filtered.PYTHONNOUSERSITE, '1');
  assert.strictEqual(filtered.GITHUB_TOKEN, undefined);
  assert.strictEqual(filtered.REDDOG_SOVEREIGN_TOKEN, undefined);
}
async function main() {
  assertClassification();
  const receipts = validatedReceipts();
  assertRejectedReceipts(receipts);
  const runtime = approvedRuntime();
  assertSealedRuntime(runtime);
  await assertBridgeSuccess(runtime, receipts);
  await assertBridgeByteBound(runtime, receipts.request);
  await assertBridgeFrameBound(runtime, receipts);
  assertExtensionAdapterResult(await runExtensionAdapter(receipts));
  assertOperationsEnvironment();
  assertRuntimeMaterialized();
  fs.rmSync(runtime.repoRoot, { recursive: true, force: true });
  console.log('start operations control tests passed');
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
