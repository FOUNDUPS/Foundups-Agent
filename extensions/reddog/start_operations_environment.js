'use strict';

const os = require('os');

const ALLOWED_KEYS = Object.freeze([
  'PATH', 'Path', 'SYSTEMROOT', 'SystemRoot', 'COMSPEC', 'ComSpec', 'PATHEXT',
  'TEMP', 'TMP', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'PROGRAMDATA',
  'VIRTUAL_ENV',
  'FOUNDUPS_DB_PATH',
  'REDDOG_AUTHENTICATED_PRINCIPAL_ID', 'REDDOG_AUTHORIZED_FOUNDUP_IDS',
  'REDDOG_RESIDENT_ARCHITECT_FOUNDUP_ID',
  'REDDOG_RESIDENT_MODEL_RUNTIME_BINDING_ROOT',
  'REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_RECEIPT_PATH',
  'REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_RECEIPT_PATH',
  'REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_EXPECTED_RECEIPT_ID',
  'REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_EXPECTED_RECEIPT_ID',
  'REDDOG_MODEL_SELECTION_RECEIPT_PATH',
  'REDDOG_MODEL_CATALOG_SNAPSHOT_PATH',
  'REDDOG_MODEL_BENCHMARK_EVIDENCE_RECEIPTS_PATH',
  'REDDOG_MODEL_PROMOTION_EVIDENCE_RECEIPTS_PATH',
  'REDDOG_MODEL_PRODUCTION_EVIDENCE_BUNDLE_PATH',
  'REDDOG_MODEL_RUNTIME_BINDING_POLICY_PATH',
  'REDDOG_MODEL_EVIDENCE_TRUSTED_KEYS_PATH',
  'REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS',
  'REDDOG_AUTHORITATIVE_WORK_STATE_PATH',
  'REDDOG_PROVIDER_CALL_EVIDENCE_STORE_PATH',
  'REDDOG_EXTERNAL_RESEARCH_SNAPSHOT_PATH',
  'REDDOG_START_OPERATIONS_MAX_CLAIMS',
  'REDDOG_START_OPERATIONS_TIMEOUT_SECONDS',
  'REDDOG_READONLY_AUDIT_RUNTIME_MODE',
  'REDDOG_BACKEND_ARCHITECT_RUNTIME_MODE',
  'HOLOINDEX_SSD_PATH', 'HOLOINDEX_FRESHNESS_RECEIPT',
  'REDDOG_HOLOINDEX_QUERY_REPLICA_ROOT',
  'HOLOINDEX_QUERY_SERVICE_URL', 'HOLOINDEX_QUERY_SERVICE_TOKEN'
]);

const BRIDGE_SYSTEM_KEYS = Object.freeze([
  'PATH', 'Path', 'PATHEXT', 'SYSTEMROOT', 'SystemRoot', 'WINDIR',
  'COMSPEC', 'ComSpec', 'TEMP', 'TMP', 'TMPDIR', 'HOME', 'USERPROFILE',
  'APPDATA', 'LOCALAPPDATA', 'PROGRAMDATA', 'VIRTUAL_ENV', 'LANG', 'LC_ALL',
  'SSL_CERT_FILE', 'SSL_CERT_DIR'
]);

const BRIDGE_PROFILE_KEYS = Object.freeze({
  default: Object.freeze([]),
  advisory_provider: Object.freeze([
    'OPENROUTER_API_KEY',
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
  ]),
  authoritative_work_state: Object.freeze([
    'REDDOG_AUTHORITATIVE_WORK_STATE_PATH'
  ]),
  model_runtime_binding: Object.freeze([
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
  ]),
  holo_query: Object.freeze([
    'HOLOINDEX_SSD_PATH', 'HOLO_SSD_PATH', 'HOLO_OFFLINE'
  ]),
  holoindex_owner: Object.freeze([
    'HOLOINDEX_QUERY_SERVICE_URL', 'HOLOINDEX_QUERY_SERVICE_TOKEN',
    'REDDOG_HOLOINDEX_OWNER_AUTO_START', 'HOLOINDEX_SSD_PATH',
    'REDDOG_HOLOINDEX_QUERY_REPLICA_ROOT',
    'REDDOG_SEALED_RUNTIME_REQUIRED', 'REDDOG_SEALED_RUNTIME_ROOT',
    'REDDOG_SEALED_RUNTIME_MANIFEST_PATH',
    'REDDOG_SEALED_RUNTIME_MANIFEST_DIGEST',
    'REDDOG_SEALED_RUNTIME_BOOTSTRAP_PATH',
    'REDDOG_SEALED_RUNTIME_SITE_PACKAGES'
  ]),
  resident_architect: Object.freeze([
    'REDDOG_SIGNER_SYSTEM_SERVICE_OWNER_CONFIG_PATH',
    'REDDOG_EXTERNAL_RESEARCH_SNAPSHOT_PATH',
    'REDDOG_AUTHORITATIVE_WORK_STATE_PATH', 'HOLOINDEX_FRESHNESS_RECEIPT',
    'HOLOINDEX_SSD_PATH', 'REDDOG_RUNTIME_ARTIFACT_ROOT',
    'REDDOG_HOLOINDEX_QUERY_REPLICA_ROOT',
    'REDDOG_AUTHORITY_RUNTIME_STATE_PATH', 'REDDOG_AUTHORITY_PROFILE_PATH'
  ])
});

const GOVERNED_GIT_SHARED_KEYS = Object.freeze([
  'TEMP', 'TMP', 'LANG', 'LC_ALL', 'LC_CTYPE'
]);

function copyPresentStrings(input, output, keys) {
  for (const key of keys) {
    if (!Object.prototype.hasOwnProperty.call(input, key)) continue;
    if (typeof input[key] !== 'string' || input[key].length === 0) continue;
    output[key] = input[key];
  }
}

function copyFirstPresentString(input, output, outputKey, keys) {
  for (const key of keys) {
    if (!Object.prototype.hasOwnProperty.call(input, key)) continue;
    if (typeof input[key] !== 'string' || input[key].length === 0) continue;
    output[outputKey] = input[key];
    return;
  }
}

function copyGovernedGitSystem(input, output) {
  copyPresentStrings(input, output, GOVERNED_GIT_SHARED_KEYS);
  if (process.platform !== 'win32') {
    copyPresentStrings(input, output, ['TMPDIR']);
    return;
  }
  copyFirstPresentString(input, output, 'SystemRoot', ['SystemRoot', 'SYSTEMROOT']);
  copyFirstPresentString(input, output, 'ComSpec', ['ComSpec', 'COMSPEC']);
  copyPresentStrings(input, output, ['WINDIR']);
}

function buildGovernedGit(source) {
  const input = source && typeof source === 'object' ? source : {};
  const output = {};
  copyGovernedGitSystem(input, output);
  return Object.assign(output, {
    GIT_CONFIG_NOSYSTEM: '1',
    GIT_CONFIG_GLOBAL: process.platform === 'win32' ? 'NUL' : os.devNull,
    GIT_ATTR_NOSYSTEM: '1', GIT_EXTERNAL_DIFF: '', GIT_NO_LAZY_FETCH: '1',
    GIT_NO_REPLACE_OBJECTS: '1', GIT_OPTIONAL_LOCKS: '0', GIT_PAGER: 'cat',
    GIT_TERMINAL_PROMPT: '0'
  });
}

function buildBridge(source, profile) {
  const input = source && typeof source === 'object' ? source : {};
  const output = {};
  const profileKeys = typeof profile === 'string'
    && Object.prototype.hasOwnProperty.call(BRIDGE_PROFILE_KEYS, profile)
    ? BRIDGE_PROFILE_KEYS[profile] : BRIDGE_PROFILE_KEYS.default;
  copyPresentStrings(input, output, BRIDGE_SYSTEM_KEYS);
  copyPresentStrings(input, output, profileKeys);
  output.PYTHONIOENCODING = 'utf-8';
  output.PYTHONUTF8 = '1';
  output.PYTHONNOUSERSITE = '1';
  return output;
}

function build(source) {
  const input = source && typeof source === 'object' ? source : {};
  const output = {};
  for (const key of ALLOWED_KEYS) {
    if (Object.prototype.hasOwnProperty.call(input, key)) output[key] = input[key];
  }
  output.PYTHONIOENCODING = 'utf-8';
  output.PYTHONUTF8 = '1';
  output.PYTHONNOUSERSITE = '1';
  return output;
}

module.exports = {
  ALLOWED_KEYS,
  BRIDGE_PROFILE_KEYS,
  BRIDGE_SYSTEM_KEYS,
  build,
  buildBridge,
  buildGovernedGit
};
