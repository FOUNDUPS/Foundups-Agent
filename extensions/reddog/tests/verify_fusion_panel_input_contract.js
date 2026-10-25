const assert = require('assert');
const cp = require('child_process');
const fs = require('fs');
const path = require('path');
const Module = require('module');
const EventEmitter = require('events');

const root = path.resolve(__dirname, '..', '..', '..');
const extDir = path.join(root, 'extensions', 'reddog');
const extensionSource = fs.readFileSync(path.join(extDir, 'extension.js'), 'utf8');
const packageJson = JSON.parse(fs.readFileSync(path.join(extDir, 'package.json'), 'utf8'));
const bridgePython = fs.readFileSync(path.join(root, 'scripts', 'advisory_model_once.py'), 'utf8');
const rootExemptionYaml = fs.readFileSync(path.join(root, 'wsp_62_exemptions.yaml'), 'utf8');
const exemptionYaml = fs.readFileSync(path.join(extDir, 'wsp_62_exemptions.yaml'), 'utf8');
const roadmap = fs.readFileSync(path.join(extDir, 'ROADMAP.md'), 'utf8');
const fusionProgress = require(path.join(extDir, 'fusion_progress_receipt.js'));
const runtimeBindingQuery = require(path.join(extDir, 'model_runtime_binding_query.js'));
const defaultPanel = packageJson.contributes.configuration.properties['reddog.panelModels'].default;
const configState = {
  reddog: {},
  foundupsFusion: {}
};

const vscodeMock = {
  window: {
    activeTextEditor: null,
    visibleTextEditors: [],
    createWebviewPanel: () => ({
      webview: {
        onDidReceiveMessage: () => ({ dispose() {} }),
        asWebviewUri: () => ({ toString: () => '' })
      },
      dispose() {}
    })
  },
  workspace: {
    workspaceFolders: [{ uri: { fsPath: root } }],
    getConfiguration: (namespace) => ({
      get: (key) => {
        const values = configState[namespace] || {};
        return Object.prototype.hasOwnProperty.call(values, key) ? values[key] : undefined;
      }
    })
  },
  commands: { registerCommand: () => ({ dispose() {} }) },
  extensions: { getExtension: () => undefined },
  env: { clipboard: { writeText: async () => {} } },
  Uri: { joinPath: () => ({ fsPath: path.join(extDir, 'icon.png') }) },
  ViewColumn: { Beside: 2 }
};

const vscodePath = path.join(extDir, 'node_modules', 'vscode', 'index.js');
require.cache[vscodePath] = { exports: vscodeMock, loaded: true, id: vscodePath };
const originalResolve = Module._resolveFilename;
Module._resolveFilename = function(request, parent, isMain, options) {
  if (request === 'vscode') {
    return vscodePath;
  }
  return originalResolve.call(this, request, parent, isMain, options);
};
const reddog = require(path.join(extDir, 'extension.js'));
Module._resolveFilename = originalResolve;

function workerWithPanel(panelValue, supplied) {
  configState.reddog = supplied ? { panelModels: panelValue } : {};
  configState.foundupsFusion = {};
  return reddog.fusionWorkerFromConfig();
}

function runtimeBindingReceipt(worker) {
  const models = [worker.lead, ...worker.panel];
  const value = {
    schema_version: runtimeBindingQuery.SCHEMA_VERSION, configured: true, accepted: true,
    status: runtimeBindingQuery.STATUS_READY,
    binding_receipt_id: 'reddog_model_runtime_binding:' + 'a'.repeat(64),
    runtime_surface: 'reddog_backend_architect', catalog_snapshot_id: 'snapshot:test',
    selection_receipt_id: 'selection:test', task_family: 'reddog_runtime_model_call',
    principal_model: worker.lead, panel_models: worker.panel,
    role_bindings: models.map((model, index) => ({ role: index ? 'critic_' + index : 'principal', model_id: model, provider: 'test' })),
    benchmark_evidence_receipt_ids: [], promotion_evidence_receipt_ids: [],
    signed_promotion_receipt_ids: [], min_verifier_pass_rate: 0.9,
    topology_resolution_receipt_id: 'verified_model_runtime_topology:' + 'b'.repeat(64),
    topology_verification_receipt_id: 'verification:test',
    topology_valid_until: Math.floor(Date.now() / 1000) + 60,
    available_providers: ['test'], rejection_reasons: [],
    no_model_call_performed: true, no_holoindex_query_performed: true,
    no_holoindex_reindex_performed: true, no_command_execution_performed: true,
    no_repo_mutation_performed: true, no_runtime_artifact_mutation_performed: true
  };
  value.query_receipt_id = runtimeBindingQuery.canonicalDigest(value);
  return value;
}

function finishFakeBridge(child, onPayload, stdinText) {
  const payload = JSON.parse(stdinText);
  onPayload(payload);
  const progress = JSON.stringify({
    event: 'progress', stage: 'lead_start', text: 'Lead request started.',
    run_id: 'run-contract', event_id: 'event-contract', sequence: 1,
    status: 'STARTED', role: 'lead', model: 'model-a', elapsed_ms: 3
  });
  child.stderr.emit('data', Buffer.from(progress.slice(0, 23)));
  child.stderr.emit('data', Buffer.from(progress.slice(23)));
  child.stdout.emit('data', Buffer.from(JSON.stringify({
    ok: false, reason: 'contract_probe',
    fusion_progress_receipt: {
      run_id: payload.bridge_run_id, receipt_id: 'contract-receipt'
    },
    fusion_progress_receipt_validation: {
      applied: true, valid: true, rejection_reasons: []
    }
  })));
  child.emit('close', 0);
}

function fakeBridgeChild(onPayload) {
  const child = new EventEmitter();
  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  child.killed = false;
  child.kill = () => {
    child.killed = true;
  };
  let stdinText = '';
  child.stdin = {
    write: (chunk) => {
      stdinText += String(chunk);
    },
    end: () => finishFakeBridge(child, onPayload, stdinText)
  };
  return child;
}

async function captureBridgeInvocation(worker, mode) {
  const originalSpawn = cp.spawn;
  let invocation = null;
  let payload = null;
  let spawnCount = 0;
  const progressEvents = [];
  cp.spawn = (command, args, options) => {
    spawnCount += 1;
    invocation = { command, args, options };
    return fakeBridgeChild((value) => {
      payload = value;
    });
  };
  try {
    const state = { bridgeChild: null, disposed: false };
    const result = await reddog.callFusion({}, worker, 'contract prompt', 'bounded context', 'system prompt', [], mode,
      (stage, text, metadata) => progressEvents.push({ stage, text, metadata }), state, {}, {
        backendCompatibility: { passed: true },
        runtimeBindingQuery: async () => runtimeBindingReceipt(worker)
      });
    return { invocation, payload, progressEvents, result, spawnCount, state };
  } finally {
    cp.spawn = originalSpawn;
  }
}

function assertRuntimeLimits() {
  const runtimeCapMatch = bridgePython.match(/^MAX_PANEL_MODELS = (\d+)$/m);
  assert(runtimeCapMatch, 'Python MAX_PANEL_MODELS contract missing');
  const pythonRuntimeCap = Number(runtimeCapMatch[1]);
  assert.strictEqual(reddog.FUSION_PANEL_RUNTIME_LIMIT, pythonRuntimeCap, 'JS/Python runtime cap drift');
  assert.strictEqual(
    reddog.FUSION_PANEL_FORWARD_LIMIT,
    pythonRuntimeCap + 1,
    'extension must preserve one overflow sentinel'
  );
  const properties = packageJson.contributes.configuration.properties;
  assert.strictEqual(properties['reddog.panelModels'].maxItems, reddog.FUSION_PANEL_FORWARD_LIMIT);
  assert.strictEqual(properties['foundupsFusion.panelModels'].maxItems, reddog.FUSION_PANEL_FORWARD_LIMIT);
}

function assertWsp62Contracts() {
  const thresholdMatch = exemptionYaml.match(/threshold_override:\s*(\d+)/);
  assert(thresholdMatch, 'extension.js WSP_62 threshold missing');
  assert(extensionSource.trimEnd().split(/\r?\n/).length <= Number(thresholdMatch[1]));
  assert(exemptionYaml.includes('file: "extension.js"'), 'exemption must be exact-file scoped');
  assert(exemptionYaml.includes('temporary: true'), 'exemption must be temporary');
  assert(exemptionYaml.includes('owner: "RedDog Maintainers"'), 'exemption owner missing');
  assert(exemptionYaml.includes('expires_on: "2026-09-30"'), 'exemption expiry missing');
  assert(rootExemptionYaml.includes('file: "scripts/advisory_model_once.py"'), 'bridge exemption missing');
  assert(rootExemptionYaml.includes('functions: ["_run_foundups_fusion_core", "main"]'), 'bridge functions missing');
  assert(rootExemptionYaml.includes('owner: "RedDog Maintainers"'), 'bridge exemption owner missing');
  assert(rootExemptionYaml.includes('expires_on: "2026-09-30"'), 'bridge exemption expiry missing');
  assert(rootExemptionYaml.includes('remediation: "extensions/reddog/ROADMAP.md#reddog-advisory-python-bridge-wsp_62-decomposition"'), 'bridge remediation missing');
  assert(roadmap.includes('### RedDog extension.js WSP_62 decomposition'), 'remediation roadmap missing');
  assert(roadmap.includes('### RedDog advisory Python bridge WSP_62 decomposition'), 'bridge roadmap missing');
}

function panelCases() {
  const aboveLegacyCap = ['m0', 'm1', 'm2', 'm3', 'm4'];
  const overRuntimeCap = ['m0', 'm1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7'];
  return [
    ['omitted', undefined, false, defaultPanel],
    ['non_list', 'not-a-list', true, defaultPanel],
    ['empty', [], true, []],
    ['invalid_only', ['', null, 7, '   '], true, []],
    ['above_legacy_four', aboveLegacyCap, true, aboveLegacyCap],
    [
      'over_runtime_cap',
      overRuntimeCap,
      true,
      overRuntimeCap.slice(0, reddog.FUSION_PANEL_FORWARD_LIMIT)
    ]
  ];
}

async function assertModeCases(mode, cases) {
  for (const [name, configured, supplied, expected] of cases) {
    const worker = workerWithPanel(configured, supplied);
    assert.deepStrictEqual(worker.panel, expected, mode + '/' + name + ': ingress panel mismatch');
    const captured = await captureBridgeInvocation(worker, mode);
    assert.strictEqual(captured.spawnCount, 1, mode + '/' + name + ': one local bridge spawn expected');
    assert.deepStrictEqual(
      captured.invocation.args,
      [path.join(root, 'scripts', 'advisory_model_once.py')],
      mode + '/' + name + ': models and prompts must not enter argv'
    );
    assert.strictEqual(captured.invocation.options.env.OPENROUTER_API_KEY, undefined);
    assert.strictEqual(captured.payload.mode, mode, mode + '/' + name + ': mode mismatch');
    assert(/^reddog_bridge_run:[0-9a-f]{32}$/.test(captured.payload.bridge_run_id), mode + '/' + name + ': bridge run ID missing');
    assert.deepStrictEqual(
      captured.payload.panel_models,
      expected.slice(0, reddog.FUSION_PANEL_RUNTIME_LIMIT),
      mode + '/' + name + ': receipt-bound stdin mismatch'
    );
    const bridgeProgress = captured.progressEvents.filter((event) => event.stage === 'lead_start');
    assert.strictEqual(bridgeProgress.length, 1, mode + '/' + name + ': fragmented progress must decode once');
    assert.strictEqual(bridgeProgress[0].metadata.role, 'lead', mode + '/' + name + ': progress metadata missing');
    const collector = fusionProgress.createFusionProgressCollector();
    collector.capture(captured.result);
    assert.strictEqual(collector.snapshot().length, 1, mode + '/' + name + ': local run binding must survive callFusion return');
    assert.strictEqual(captured.state.bridgeChild, null, mode + '/' + name + ': child state must clear');
  }
}

function restoreApiKey(value) {
  if (value === undefined) {
    delete process.env.OPENROUTER_API_KEY;
  } else {
    process.env.OPENROUTER_API_KEY = value;
  }
}

async function assertProviderEnvironmentScope() {
  const priorKey = process.env.OPENROUTER_API_KEY;
  const priorSentinel = process.env.REDDOG_UNRELATED_SENTINEL;
  process.env.OPENROUTER_API_KEY = 'provider-contract-marker';
  process.env.REDDOG_UNRELATED_SENTINEL = 'ambient-contract-marker';
  try {
    const captured = await captureBridgeInvocation(
      workerWithPanel(undefined, false), 'foundups_fusion'
    );
    assert.strictEqual(
      captured.invocation.options.env.OPENROUTER_API_KEY,
      'provider-contract-marker'
    );
    assert.strictEqual(
      captured.invocation.options.env.REDDOG_UNRELATED_SENTINEL, undefined
    );
  } finally {
    restoreApiKey(priorKey);
    if (priorSentinel === undefined) delete process.env.REDDOG_UNRELATED_SENTINEL;
    else process.env.REDDOG_UNRELATED_SENTINEL = priorSentinel;
  }
}

async function main() {
  assertRuntimeLimits();
  assertWsp62Contracts();
  const priorApiKey = process.env.OPENROUTER_API_KEY;
  delete process.env.OPENROUTER_API_KEY;
  try {
    await assertModeCases('foundups_fusion', panelCases());
    await assertModeCases('openrouter_fusion_alias', panelCases());
    await assertProviderEnvironmentScope();
  } finally {
    restoreApiKey(priorApiKey);
  }
  console.log('PASS: RedDog Fusion panel ingress and bridge payload contract');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
