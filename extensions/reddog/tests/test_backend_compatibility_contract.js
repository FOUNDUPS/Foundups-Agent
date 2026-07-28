'use strict';

const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const extensionRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(extensionRoot, '..', '..');
const preflight = require('../backend_compatibility_preflight');
const manifest = JSON.parse(
  fs.readFileSync(path.join(repoRoot, preflight.BACKEND_MANIFEST_PATH), 'utf8')
);
const extensionSource = fs.readFileSync(path.join(extensionRoot, 'extension.js'), 'utf8');
const interfaceSource = fs.readFileSync(path.join(extensionRoot, 'INTERFACE.md'), 'utf8');
const preflightSource = fs.readFileSync(
  path.join(extensionRoot, 'backend_compatibility_preflight.js'),
  'utf8'
);
const asyncSource = fs.readFileSync(
  path.join(extensionRoot, 'backend_compatibility_async.js'),
  'utf8'
);

function canonicalize(value) {
  if (Array.isArray(value)) {
    return value.map(canonicalize);
  }
  if (!value || typeof value !== 'object') {
    return value;
  }
  return Object.fromEntries(
    Object.keys(value).sort().map((key) => [key, canonicalize(value[key])])
  );
}

function assertManifestContract() {
  assert.strictEqual(manifest.schema_version, preflight.BACKEND_MANIFEST_SCHEMA);
  assert.strictEqual(manifest.product, preflight.BACKEND_PRODUCT);
  assert.strictEqual(manifest.backend_api_version, preflight.BACKEND_API_VERSION);
  assert.deepStrictEqual(
    manifest.required_executable_files.slice().sort(),
    preflight.REQUIRED_EXECUTABLE_FILES.slice().sort()
  );
  assert.deepStrictEqual(
    manifest.required_bridge_files.slice().sort(),
    preflight.REQUIRED_BRIDGE_FILES.slice().sort()
  );
  assert.deepStrictEqual(
    Object.keys(manifest.required_runtime_sha256).sort(),
    manifest.required_runtime_files.slice().sort()
  );
  assert(manifest.required_runtime_files.length >= 900);
  for (const executable of preflight.REQUIRED_EXECUTABLE_FILES) {
    assert(manifest.required_runtime_files.includes(executable));
  }
  for (const sentinel of [
    'holo_index.py',
    'modules/communication/moltbot_bridge/src/openclaw_dae.py',
    'modules/foundups/src/foundup_registry_loader.py',
    'modules/platform_integration/linkedin_agent/src/linkedin_agent.py'
  ]) {
    assert(manifest.required_runtime_files.includes(sentinel), sentinel);
  }
}

function assertPinnedDigest() {
  const digest = crypto.createHash('sha256')
    .update(JSON.stringify(canonicalize(manifest)))
    .digest('hex');
  assert.strictEqual(digest, preflight.EXPECTED_MANIFEST_SHA256);
}

function assertRuntimeOrdering() {
  const askStart = extensionSource.indexOf('function wireFusionWebview');
  const askEnd = extensionSource.indexOf('function killBridgeChild', askStart);
  const askSource = extensionSource.slice(askStart, askEnd);
  const gate = askSource.indexOf('blockIncompatibleBackend');
  assert(askStart >= 0 && askEnd > askStart);
  assert(gate >= 0);
  assert(gate < askSource.indexOf('const workFocus = message.text'));
  assert(gate < askSource.indexOf('classifyTaskForRedDog'));
  assert(gate < askSource.indexOf('buildBoundedRepoContext'));
  assert(askSource.includes('backendCompatibility.enforceRuntimeGate'));
  assert(
    askSource.indexOf('backendCompatibility.enforceRuntimeGate')
      < askSource.indexOf('runGithubPermissionProbeBridge')
  );
  assert(asyncSource.includes('async function blockIncompatibleBackend'));
  assert(asyncSource.includes('backend_compatibility_worker_failed'));
  const fusionStart = extensionSource.indexOf('function callFusion');
  const fusionEnd = extensionSource.indexOf('function buildSystemPrompt', fusionStart);
  const fusionSource = extensionSource.slice(fusionStart, fusionEnd);
  assert(fusionSource.includes('currentBackendCompatibility()'));
  assert(
    fusionSource.indexOf('currentBackendCompatibility()')
      < fusionSource.indexOf('new Promise')
  );
  for (const functionName of ['runRepairGuard', 'runJudgmentVerifier']) {
    const source = namedFunctionSource(functionName);
    assert(source.includes('currentBackendCompatibilitySync()'), functionName);
    assert(
      source.indexOf('currentBackendCompatibilitySync()')
        < source.indexOf('cp.execFileSync'),
      functionName
    );
  }
}

function namedFunctionSource(name) {
  const lines = extensionSource.split(/\r?\n/);
  const start = lines.findIndex((line) => (
    line.startsWith('function ' + name)
    || line.startsWith('async function ' + name)
  ));
  assert(start >= 0, name);
  let depth = 0;
  for (let end = start; end < lines.length; end += 1) {
    depth += (lines[end].match(/{/g) || []).length;
    depth -= (lines[end].match(/}/g) || []).length;
    if (end > start && depth === 0) return lines.slice(start, end + 1).join('\n');
  }
  return '';
}

function functionLineCount(name) {
  return namedFunctionSource(name).split(/\r?\n/).length;
}

function assertSafeBlockedProjection() {
  const client = {
    extensionId: 'foundups.reddog',
    legacyExtensionId: 'foundups.foundups-fusion-worker',
    extensionVersion: '0.4.29',
    buildInstallStateSection: () => ''
  };
  const result = preflight.buildBlockedResult({
    extension_id: 'secret-extension-id',
    backend_compatibility: {
      checked: true,
      passed: false,
      rejection_reasons: [
        'backend_api_version_mismatch',
        'secret value must not cross'
      ],
      workspace_root_digest: 'sha256:' + '0'.repeat(64),
      product: 'secret-product-value'
    }
  }, client);
  const serialized = JSON.stringify(result);
  assert.strictEqual(result.ok, false);
  assert.strictEqual(result.review_packet.made_network_call, false);
  assert(!serialized.includes(repoRoot));
  assert(!serialized.includes('secret-product-value'));
  assert(!serialized.includes('secret value must not cross'));
  assert(!serialized.includes('secret-extension-id'));
}

assertManifestContract();
assertPinnedDigest();
assertRuntimeOrdering();
assertSafeBlockedProjection();
assert(functionLineCount('wireFusionWebview') <= 581);
assert(interfaceSource.includes(
  'before target extraction, HoloIndex lookup, model execution, permission probing, or work-order creation'
));
const current = preflight.runBackendCompatibilityPreflight(repoRoot);
assert.strictEqual(current.passed, true);
assert.strictEqual(current.no_holoindex_query_performed, true);
assert.strictEqual(current.no_model_call_performed, true);
for (const forbidden of ['child_process', 'execFile', 'spawn(', 'holo_index.py --index']) {
  assert.strictEqual(preflightSource.includes(forbidden), false, forbidden);
}

console.log('backend compatibility contract tests passed');
