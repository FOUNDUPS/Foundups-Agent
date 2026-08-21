'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const environment = require('../start_operations_environment');
const sessionAuthority = require('../conversation_session_authority_source');

const extensionSource = fs.readFileSync(
  path.join(__dirname, '..', 'extension.js'), 'utf8'
);

const SYSTEM_FIXTURE = Object.freeze({
  PATH: 'runtime-path',
  Path: 'runtime-path-case',
  PATHEXT: '.EXE',
  SYSTEMROOT: 'runtime-system-root',
  SystemRoot: 'runtime-system-root-case',
  WINDIR: 'runtime-windows-dir',
  COMSPEC: 'runtime-command-shell',
  ComSpec: 'runtime-command-shell-case',
  TEMP: 'runtime-temp',
  TMP: 'runtime-tmp',
  TMPDIR: 'runtime-tmpdir',
  HOME: 'runtime-home',
  USERPROFILE: 'runtime-profile',
  APPDATA: 'runtime-appdata',
  LOCALAPPDATA: 'runtime-localappdata',
  PROGRAMDATA: 'runtime-programdata',
  VIRTUAL_ENV: 'runtime-virtual-env',
  LANG: 'en_US.UTF-8',
  LC_ALL: 'C.UTF-8'
});

const CONFIG_FIXTURE = Object.freeze({
  OPENROUTER_API_KEY: 'provider-marker',
  REDDOG_AUTHORITATIVE_WORK_STATE_PATH: 'work-state-marker',
  REDDOG_RESIDENT_MODEL_RUNTIME_BINDING_ROOT: 'binding-root-marker',
  REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_RECEIPT_PATH: 'binding-receipt-marker',
  REDDOG_MODEL_SELECTION_RECEIPT_PATH: 'selection-marker',
  REDDOG_MODEL_CATALOG_SNAPSHOT_PATH: 'catalog-marker',
  REDDOG_MODEL_BENCHMARK_EVIDENCE_RECEIPTS_PATH: 'benchmarks-marker',
  REDDOG_MODEL_PROMOTION_EVIDENCE_RECEIPTS_PATH: 'promotions-marker',
  REDDOG_MODEL_PRODUCTION_EVIDENCE_BUNDLE_PATH: 'evidence-marker',
  REDDOG_MODEL_RUNTIME_BINDING_POLICY_PATH: 'policy-marker',
  REDDOG_MODEL_EVIDENCE_TRUSTED_KEYS_PATH: 'keys-marker',
  REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS: 'openrouter',
  HOLOINDEX_QUERY_SERVICE_URL: 'owner-url-marker',
  HOLOINDEX_QUERY_SERVICE_TOKEN: 'owner-token-marker',
  HOLO_SSD_PATH: 'legacy-ssd-marker',
  HOLO_OFFLINE: '1',
  REDDOG_HOLOINDEX_OWNER_AUTO_START: '0',
  HOLOINDEX_SSD_PATH: 'holo-store-marker',
  REDDOG_SEALED_RUNTIME_REQUIRED: '1',
  REDDOG_SEALED_RUNTIME_ROOT: 'sealed-root-marker',
  REDDOG_SEALED_RUNTIME_MANIFEST_PATH: 'sealed-manifest-marker',
  REDDOG_SEALED_RUNTIME_MANIFEST_DIGEST: 'sealed-digest-marker',
  REDDOG_SEALED_RUNTIME_BOOTSTRAP_PATH: 'sealed-bootstrap-marker',
  REDDOG_SEALED_RUNTIME_SITE_PACKAGES: 'sealed-site-marker',
  REDDOG_SIGNER_SYSTEM_SERVICE_OWNER_CONFIG_PATH: 'owner-config-marker',
  REDDOG_EXTERNAL_RESEARCH_SNAPSHOT_PATH: 'research-marker',
  HOLOINDEX_FRESHNESS_RECEIPT: 'freshness-marker',
  HOLOINDEX_SSD_PATH: 'ssd-marker',
  REDDOG_RUNTIME_ARTIFACT_ROOT: 'artifact-root-marker',
  REDDOG_AUTHORITY_RUNTIME_STATE_PATH: 'authority-state-marker',
  REDDOG_AUTHORITY_PROFILE_PATH: 'authority-profile-marker'
});

const FORBIDDEN_FIXTURE = Object.freeze({
  GITHUB_TOKEN: 'ambient-marker',
  AWS_SECRET_ACCESS_KEY: 'ambient-marker',
  PYTHONPATH: 'ambient-marker',
  PYTHONHOME: 'ambient-marker',
  PYTHONSTARTUP: 'ambient-marker',
  NODE_OPTIONS: 'ambient-marker',
  GENERIC_ACCESS_TOKEN: 'ambient-marker',
  CALLER_ARBITRARY_KEY: 'ambient-marker',
  UNRELATED_SENTINEL: 'ambient-marker'
});

const HOLO_QUERY_FORBIDDEN_KEYS = Object.freeze([
  'UNRELATED_SENTINEL', 'GITHUB_TOKEN', 'GENERIC_ACCESS_TOKEN',
  'OPENROUTER_API_KEY', 'PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP',
  'CALLER_ARBITRARY_KEY'
]);

function mergedFixture() {
  return Object.assign({}, SYSTEM_FIXTURE, CONFIG_FIXTURE, FORBIDDEN_FIXTURE);
}

function assertSystemKeys(env) {
  for (const [key, value] of Object.entries(SYSTEM_FIXTURE)) {
    assert.strictEqual(env[key], value, key + ' must survive when present');
  }
  assert.strictEqual(env.PYTHONIOENCODING, 'utf-8');
  assert.strictEqual(env.PYTHONUTF8, '1');
  assert.strictEqual(env.PYTHONNOUSERSITE, '1');
}

function assertForbiddenKeys(env) {
  for (const key of Object.keys(FORBIDDEN_FIXTURE)) {
    assert.strictEqual(env[key], undefined, key + ' must not cross');
  }
}

function assertProfile(profile, allowed) {
  const env = environment.buildBridge(mergedFixture(), profile);
  assertSystemKeys(env);
  assertForbiddenKeys(env);
  for (const key of Object.keys(CONFIG_FIXTURE)) {
    const expected = allowed.includes(key) ? CONFIG_FIXTURE[key] : undefined;
    assert.strictEqual(env[key], expected, profile + ' profile mismatch for ' + key);
  }
}

function assertProfiles() {
  const modelRuntimeKeys = [
    'REDDOG_RESIDENT_MODEL_RUNTIME_BINDING_ROOT',
    'REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_RECEIPT_PATH',
    'REDDOG_MODEL_SELECTION_RECEIPT_PATH',
    'REDDOG_MODEL_CATALOG_SNAPSHOT_PATH',
    'REDDOG_MODEL_BENCHMARK_EVIDENCE_RECEIPTS_PATH',
    'REDDOG_MODEL_PROMOTION_EVIDENCE_RECEIPTS_PATH',
    'REDDOG_MODEL_PRODUCTION_EVIDENCE_BUNDLE_PATH',
    'REDDOG_MODEL_RUNTIME_BINDING_POLICY_PATH',
    'REDDOG_MODEL_EVIDENCE_TRUSTED_KEYS_PATH',
    'REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS'
  ];
  assertProfile('default', []);
  assertProfile('advisory_provider', ['OPENROUTER_API_KEY', ...modelRuntimeKeys]);
  assertProfile('authoritative_work_state', [
    'REDDOG_AUTHORITATIVE_WORK_STATE_PATH'
  ]);
  assertProfile('model_runtime_binding', modelRuntimeKeys);
  assertProfile('holo_query', [
    'HOLOINDEX_SSD_PATH', 'HOLO_SSD_PATH', 'HOLO_OFFLINE'
  ]);
  assertProfile('holoindex_owner', [
    'HOLOINDEX_QUERY_SERVICE_URL', 'HOLOINDEX_QUERY_SERVICE_TOKEN',
    'REDDOG_HOLOINDEX_OWNER_AUTO_START', 'HOLOINDEX_SSD_PATH',
    'REDDOG_SEALED_RUNTIME_REQUIRED', 'REDDOG_SEALED_RUNTIME_ROOT',
    'REDDOG_SEALED_RUNTIME_MANIFEST_PATH',
    'REDDOG_SEALED_RUNTIME_MANIFEST_DIGEST',
    'REDDOG_SEALED_RUNTIME_BOOTSTRAP_PATH',
    'REDDOG_SEALED_RUNTIME_SITE_PACKAGES'
  ]);
  assertProfile('resident_architect', [
    'REDDOG_SIGNER_SYSTEM_SERVICE_OWNER_CONFIG_PATH',
    'REDDOG_EXTERNAL_RESEARCH_SNAPSHOT_PATH',
    'REDDOG_AUTHORITATIVE_WORK_STATE_PATH', 'HOLOINDEX_FRESHNESS_RECEIPT',
    'HOLOINDEX_SSD_PATH', 'REDDOG_RUNTIME_ARTIFACT_ROOT',
    'REDDOG_AUTHORITY_RUNTIME_STATE_PATH', 'REDDOG_AUTHORITY_PROFILE_PATH'
  ]);
}

function assertInputSafety() {
  const source = mergedFixture();
  const before = JSON.stringify(source);
  const first = environment.buildBridge(source, 'default');
  const second = environment.buildBridge(source, 'default');
  assert.notStrictEqual(first, source);
  assert.notStrictEqual(first, second);
  first.PATH = 'changed';
  assert.strictEqual(second.PATH, SYSTEM_FIXTURE.PATH);
  assert.strictEqual(JSON.stringify(source), before);
  assert.strictEqual(environment.buildBridge(undefined, 'advisory_provider').OPENROUTER_API_KEY, undefined);
  assert.strictEqual(environment.buildBridge({ OPENROUTER_API_KEY: '' }, 'advisory_provider').OPENROUTER_API_KEY, undefined);
  assert.strictEqual(environment.buildBridge(source, ['GITHUB_TOKEN']).GITHUB_TOKEN, undefined);
  assert.strictEqual(environment.buildBridge(source, { keys: ['GITHUB_TOKEN'] }).GITHUB_TOKEN, undefined);
  assert.strictEqual(environment.buildBridge(source, '__proto__').GITHUB_TOKEN, undefined);
}

function assertSessionProfile() {
  const env = sessionAuthority.buildBridgeEnvironment(mergedFixture());
  assertSystemKeys(env);
  assertForbiddenKeys(env);
  assert.strictEqual(env.OPENROUTER_API_KEY, undefined);
  assert.strictEqual(
    env.REDDOG_SIGNER_SYSTEM_SERVICE_OWNER_CONFIG_PATH,
    CONFIG_FIXTURE.REDDOG_SIGNER_SYSTEM_SERVICE_OWNER_CONFIG_PATH
  );
}

function assertExtensionProfiles() {
  assert(!extensionSource.includes('Object.assign({}, baseEnv || process.env'),
    'bridge helper must not clone the whole editor environment');
  assert(!extensionSource.includes('Object.assign({}, envLike && typeof envLike'),
    'Holo query helper must not clone the whole editor environment');
  assert(!/buildBridgePythonEnv\(process\.env\)/.test(extensionSource),
    'every bridge call must select a closed environment profile');
  for (const profile of [
    'default', 'advisory_provider', 'authoritative_work_state',
    'model_runtime_binding', 'holo_query', 'holoindex_owner'
  ]) {
    assert(extensionSource.includes("'" + profile + "'"),
      'extension must wire the ' + profile + ' profile');
  }
}

function loadLiveHoloQueryEnvironmentBuilder() {
  const normalizedSource = extensionSource.replace(/\r\n/g, '\n');
  const start = normalizedSource.indexOf('function buildHoloQueryEnv(');
  const endMarker = '\n}\n\n// REDDOG_DIRECT_READ_FALLBACK_BY_PATH_PHASE1';
  const end = normalizedSource.indexOf(endMarker, start);
  assert(start >= 0 && end > start, 'live Holo query environment helper must be extractable');
  const functionSource = normalizedSource.slice(start, end + 2);
  return vm.runInNewContext('(' + functionSource + ')', {
    process: { env: {} },
    startOperationsEnvironment: environment
  });
}

function assertNoHoloQueryLeak(env, context) {
  for (const key of HOLO_QUERY_FORBIDDEN_KEYS) {
    assert.strictEqual(env[key], undefined, key + ' must not cross ' + context);
  }
}

function assertHoloQueryConfiguration(env) {
  assert.strictEqual(env.HOLOINDEX_QUERY_READONLY, '1');
  assert.strictEqual(env.HOLOINDEX_SSD_PATH, CONFIG_FIXTURE.HOLOINDEX_SSD_PATH);
  assert.strictEqual(env.HOLO_SSD_PATH, CONFIG_FIXTURE.HOLO_SSD_PATH);
  assert.strictEqual(env.HOLO_OFFLINE, CONFIG_FIXTURE.HOLO_OFFLINE);
  assert.strictEqual(env.PYTHONNOUSERSITE, undefined,
    'local Holo query must preserve its existing interpreter package visibility');
}

function assertLiveHoloQueryEnvironmentIsClosed() {
  const buildHoloQueryEnv = loadLiveHoloQueryEnvironmentBuilder();
  const source = Object.assign(mergedFixture(), {
    HOLOINDEX_QUERY_READONLY: '0',
    HOLO_SKIP_MODEL: '0'
  });
  const before = JSON.stringify(source);
  const first = buildHoloQueryEnv(source, 'lexical');
  const second = buildHoloQueryEnv(source, 'lexical');
  assert.notStrictEqual(first, source, 'Holo query environment must not alias its source');
  assert.notStrictEqual(first, second, 'Holo query environments must be fresh objects');
  assert.strictEqual(JSON.stringify(source), before, 'Holo query builder must not mutate its source');
  assertNoHoloQueryLeak(first, 'the Holo query boundary');
  assertHoloQueryConfiguration(first);
  assert.strictEqual(first.HOLO_SKIP_MODEL, '1');
  first.PATH = 'changed';
  assert.strictEqual(second.PATH, SYSTEM_FIXTURE.PATH, 'Holo query results must not alias each other');
  const semantic = buildHoloQueryEnv(source, 'semantic');
  assertHoloQueryConfiguration(semantic);
  assert.strictEqual(semantic.HOLO_SKIP_MODEL, undefined);
  const unknown = buildHoloQueryEnv(source, 'unrecognized');
  assert.strictEqual(unknown.HOLOINDEX_QUERY_READONLY, '1');
  assert.strictEqual(unknown.HOLO_SKIP_MODEL, undefined);
  assertNoHoloQueryLeak(unknown, 'an unknown retrieval mode');
}

assertExtensionProfiles();
assertProfiles();
assertInputSafety();
assertSessionProfile();
assertLiveHoloQueryEnvironmentIsClosed();
console.log('RedDog bridge Python environment checks passed.');
