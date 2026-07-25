'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const BACKEND_MANIFEST_SCHEMA = 'reddog_backend_manifest.v1';
const BACKEND_PRODUCT = 'foundups-agent-reddog-backend';
const BACKEND_API_VERSION = 1;
const BACKEND_MANIFEST_PATH = 'scripts/reddog_backend_manifest.json';
const EXPECTED_MANIFEST_SHA256 = '03106d604ea9bda657c934c123e94df6d6010d4255227c0d9211f97ddb20ab45';
const MAX_MANIFEST_BYTES = 32768;
const MAX_BRIDGE_BYTES = 2 * 1024 * 1024;
const REQUIRED_BRIDGE_FILES = Object.freeze([
  'scripts/advisory_model_once.py',
  'scripts/reddog_extension_live_enqueue_invoke_once.py',
  'scripts/reddog_extension_wre_spine_invoke_once.py',
  'scripts/reddog_github_permission_probe_once.py',
  'scripts/reddog_holoindex_owner_query_once.py',
  'scripts/reddog_judgment_verifier_once.py',
  'scripts/reddog_operator_wardrobe_selection_once.py',
  'scripts/reddog_repair_guard_once.py',
  'scripts/reddog_resident_architect_session_once.py'
]);
const REQUIRED_REPOSITORY_MARKERS = Object.freeze([
  'main.py',
  'holo_index.py',
  'WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md'
]);
const MANIFEST_KEYS = Object.freeze([
  'schema_version',
  'product',
  'backend_api_version',
  'required_bridge_files',
  'required_bridge_sha256',
  'required_repository_markers'
]);
const SHA256_PATTERN = /^[a-f0-9]{64}$/;

function sha256Hex(value, cryptoImpl) {
  return cryptoImpl.createHash('sha256').update(value).digest('hex');
}

function sha256Receipt(value, cryptoImpl) {
  return 'sha256:' + sha256Hex(Buffer.from(String(value), 'utf8'), cryptoImpl);
}

function normalizeTextBytes(value) {
  return Buffer.from(value.toString('utf8').replace(/\r\n/g, '\n'), 'utf8');
}

function stableUniqueStrings(value) {
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) {
    return null;
  }
  const result = value.slice().sort();
  return new Set(result).size === result.length ? result : null;
}

function arraysEqual(left, right) {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

function canonicalize(value) {
  if (Array.isArray(value)) {
    return value.map(canonicalize);
  }
  if (value && typeof value === 'object') {
    const result = {};
    for (const key of Object.keys(value).sort()) {
      result[key] = canonicalize(value[key]);
    }
    return result;
  }
  return value;
}

function realpath(fsImpl, value) {
  const resolver = fsImpl.realpathSync.native || fsImpl.realpathSync;
  return resolver.call(fsImpl.realpathSync, value);
}

function safeRoot(rootValue, dependencies) {
  if (typeof rootValue !== 'string' || !rootValue || rootValue !== rootValue.trim()) {
    return { root: '', canonicalRoot: '', reason: 'workspace_root_missing' };
  }
  const root = dependencies.path.resolve(rootValue);
  try {
    const stats = dependencies.fs.lstatSync(root);
    if (!stats.isDirectory() || stats.isSymbolicLink()) {
      return { root, canonicalRoot: '', reason: 'workspace_root_unsafe' };
    }
    return { root, canonicalRoot: realpath(dependencies.fs, root), reason: '' };
  } catch (err) {
    return { root, canonicalRoot: '', reason: 'workspace_root_missing' };
  }
}

function containedRegularFile(rootState, relativePath, dependencies) {
  const candidate = dependencies.path.resolve(rootState.root, relativePath);
  const lexicalRelative = dependencies.path.relative(rootState.root, candidate);
  if (!lexicalRelative || lexicalRelative.startsWith('..') || dependencies.path.isAbsolute(lexicalRelative)) {
    return { ok: false, candidate: '', reason: 'path_escape' };
  }
  try {
    const stats = dependencies.fs.lstatSync(candidate);
    if (!stats.isFile() || stats.isSymbolicLink()) {
      return { ok: false, candidate: '', reason: 'not_regular_file' };
    }
    const canonicalCandidate = realpath(dependencies.fs, candidate);
    const canonicalRelative = dependencies.path.relative(
      rootState.canonicalRoot,
      canonicalCandidate
    );
    if (
      !canonicalRelative
      || canonicalRelative.startsWith('..')
      || dependencies.path.isAbsolute(canonicalRelative)
    ) {
      return { ok: false, candidate: '', reason: 'canonical_path_escape' };
    }
    return { ok: true, candidate, size: stats.size, reason: '' };
  } catch (err) {
    return { ok: false, candidate: '', reason: 'missing_or_unreadable' };
  }
}

function readManifest(rootState, dependencies, expectedManifestSha256) {
  const located = containedRegularFile(rootState, BACKEND_MANIFEST_PATH, dependencies);
  if (!located.ok) {
    return { manifest: null, manifestDigest: '', reason: 'backend_manifest_missing_or_unsafe' };
  }
  try {
    const raw = dependencies.fs.readFileSync(located.candidate);
    if (raw.length <= 0 || raw.length > MAX_MANIFEST_BYTES) {
      return { manifest: null, manifestDigest: '', reason: 'backend_manifest_size_invalid' };
    }
    const manifest = JSON.parse(raw.toString('utf8'));
    if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) {
      return { manifest: null, manifestDigest: '', reason: 'backend_manifest_invalid' };
    }
    const canonical = Buffer.from(JSON.stringify(canonicalize(manifest)), 'utf8');
    const manifestDigest = sha256Hex(canonical, dependencies.crypto);
    return manifestDigest === expectedManifestSha256
      ? { manifest, manifestDigest, reason: '' }
      : { manifest: null, manifestDigest, reason: 'backend_manifest_integrity_mismatch' };
  } catch (err) {
    return { manifest: null, manifestDigest: '', reason: 'backend_manifest_invalid' };
  }
}

function validateManifest(manifest) {
  const reasons = [];
  const keys = Object.keys(manifest).sort();
  const bridgeFiles = stableUniqueStrings(manifest.required_bridge_files);
  const markers = stableUniqueStrings(manifest.required_repository_markers);
  const bridgeDigests = manifest.required_bridge_sha256;
  if (!arraysEqual(keys, MANIFEST_KEYS.slice().sort())) {
    reasons.push('backend_manifest_shape_invalid');
  }
  if (manifest.schema_version !== BACKEND_MANIFEST_SCHEMA) {
    reasons.push('backend_manifest_schema_mismatch');
  }
  if (manifest.product !== BACKEND_PRODUCT) {
    reasons.push('backend_product_mismatch');
  }
  if (manifest.backend_api_version !== BACKEND_API_VERSION) {
    reasons.push('backend_api_version_mismatch');
  }
  if (!bridgeFiles || !arraysEqual(bridgeFiles, REQUIRED_BRIDGE_FILES.slice().sort())) {
    reasons.push('backend_bridge_contract_mismatch');
  }
  if (!markers || !arraysEqual(markers, REQUIRED_REPOSITORY_MARKERS.slice().sort())) {
    reasons.push('backend_repository_marker_contract_mismatch');
  }
  if (
    !bridgeDigests
    || typeof bridgeDigests !== 'object'
    || Array.isArray(bridgeDigests)
    || !arraysEqual(Object.keys(bridgeDigests).sort(), REQUIRED_BRIDGE_FILES.slice().sort())
    || Object.values(bridgeDigests).some(
      (value) => typeof value !== 'string' || !SHA256_PATTERN.test(value)
    )
  ) {
    reasons.push('backend_bridge_digest_contract_mismatch');
  }
  return reasons;
}

function verifyBridgeFiles(rootState, manifest, dependencies) {
  const reasons = [];
  const observedDigests = {};
  for (const relativePath of REQUIRED_BRIDGE_FILES) {
    const located = containedRegularFile(rootState, relativePath, dependencies);
    if (!located.ok || located.size <= 0 || located.size > MAX_BRIDGE_BYTES) {
      reasons.push('required_bridge_missing_or_unsafe:' + relativePath);
      continue;
    }
    try {
      const raw = dependencies.fs.readFileSync(located.candidate);
      const observed = sha256Hex(normalizeTextBytes(raw), dependencies.crypto);
      observedDigests[relativePath] = observed;
      if (observed !== manifest.required_bridge_sha256[relativePath]) {
        reasons.push('required_bridge_integrity_mismatch:' + relativePath);
      }
    } catch (err) {
      reasons.push('required_bridge_missing_or_unsafe:' + relativePath);
    }
  }
  return { reasons, observedDigests };
}

function verifyRepositoryMarkers(rootState, dependencies) {
  const reasons = [];
  for (const relativePath of REQUIRED_REPOSITORY_MARKERS) {
    if (!containedRegularFile(rootState, relativePath, dependencies).ok) {
      reasons.push('repository_marker_missing_or_unsafe:' + relativePath);
    }
  }
  return reasons;
}

function runBackendCompatibilityPreflight(rootValue, options) {
  const opts = options && typeof options === 'object' ? options : {};
  const dependencies = {
    fs: opts.fs || fs,
    path: opts.path || path,
    crypto: opts.crypto || crypto
  };
  const rootState = safeRoot(rootValue, dependencies);
  const reasons = rootState.reason ? [rootState.reason] : [];
  const read = reasons.length
    ? { manifest: null, manifestDigest: '', reason: '' }
    : readManifest(rootState, dependencies, EXPECTED_MANIFEST_SHA256);
  if (read.reason) {
    reasons.push(read.reason);
  }
  let observedDigests = {};
  if (read.manifest) {
    const manifestReasons = validateManifest(read.manifest);
    reasons.push(...manifestReasons);
    if (!manifestReasons.length) {
      const bridgeResult = verifyBridgeFiles(rootState, read.manifest, dependencies);
      observedDigests = bridgeResult.observedDigests;
      reasons.push(...bridgeResult.reasons);
      reasons.push(...verifyRepositoryMarkers(rootState, dependencies));
    }
  }
  const uniqueReasons = Array.from(new Set(reasons));
  const evidencePayload = JSON.stringify({
    manifest_digest: read.manifestDigest,
    bridge_digests: observedDigests
  });
  return Object.freeze({
    schema_version: 'reddog_backend_compatibility_preflight.v1',
    checked: true,
    passed: uniqueReasons.length === 0,
    backend_manifest_integrity_verified: read.manifestDigest === EXPECTED_MANIFEST_SHA256,
    backend_api_version: read.manifest && Number.isInteger(read.manifest.backend_api_version)
      ? read.manifest.backend_api_version
      : null,
    extension_backend_api_version: BACKEND_API_VERSION,
    required_bridge_count: REQUIRED_BRIDGE_FILES.length,
    required_repository_marker_count: REQUIRED_REPOSITORY_MARKERS.length,
    workspace_root_digest: sha256Receipt(rootState.canonicalRoot || rootState.root, dependencies.crypto),
    backend_evidence_digest: sha256Receipt(evidencePayload, dependencies.crypto),
    rejection_reasons: Object.freeze(uniqueReasons),
    no_holoindex_query_performed: true,
    no_model_call_performed: true,
    no_permission_probe_performed: true,
    no_work_order_emitted: true,
    no_repo_mutation_performed: true
  });
}

function projectBackendCompatibility(value) {
  const source = value && typeof value === 'object' ? value : {};
  const safeDigest = (candidate) => (
    typeof candidate === 'string' && /^sha256:[a-f0-9]{64}$/.test(candidate)
      ? candidate
      : 'unknown'
  );
  const reasons = Array.isArray(source.rejection_reasons)
    ? source.rejection_reasons.map((reason) => (
      typeof reason === 'string'
      && reason.length <= 240
      && /^[A-Za-z0-9_./:-]+$/.test(reason)
        ? reason
        : 'backend_compatibility_rejection_redacted'
    ))
    : ['backend_compatibility_unavailable'];
  return Object.freeze({
    schema_version: 'reddog_backend_compatibility_preflight.v1',
    checked: source.checked === true,
    passed: source.passed === true,
    backend_manifest_integrity_verified: source.backend_manifest_integrity_verified === true,
    backend_api_version: Number.isInteger(source.backend_api_version)
      ? source.backend_api_version
      : null,
    extension_backend_api_version: Number.isInteger(source.extension_backend_api_version)
      ? source.extension_backend_api_version
      : BACKEND_API_VERSION,
    required_bridge_count: Number.isInteger(source.required_bridge_count)
      ? source.required_bridge_count
      : 0,
    required_repository_marker_count: Number.isInteger(source.required_repository_marker_count)
      ? source.required_repository_marker_count
      : 0,
    workspace_root_digest: safeDigest(source.workspace_root_digest),
    backend_evidence_digest: safeDigest(source.backend_evidence_digest),
    rejection_reasons: Object.freeze(Array.from(new Set(reasons))),
    no_holoindex_query_performed: source.no_holoindex_query_performed === true,
    no_model_call_performed: source.no_model_call_performed === true,
    no_permission_probe_performed: source.no_permission_probe_performed === true,
    no_work_order_emitted: source.no_work_order_emitted === true,
    no_repo_mutation_performed: source.no_repo_mutation_performed === true
  });
}

function workspaceRoot(vscode, fallback) {
  const folders = vscode && vscode.workspace ? vscode.workspace.workspaceFolders : null;
  const folder = folders && folders[0];
  return folder && folder.uri && typeof folder.uri.fsPath === 'string'
    ? folder.uri.fsPath
    : fallback;
}

function configurationValue(vscode, currentNamespace, legacyNamespace, key, fallback) {
  const current = vscode.workspace.getConfiguration(currentNamespace);
  const legacy = vscode.workspace.getConfiguration(legacyNamespace);
  const currentValue = current.get(key);
  if (currentValue !== undefined && currentValue !== null && currentValue !== '') {
    return currentValue;
  }
  const legacyValue = legacy.get(key);
  return legacyValue !== undefined && legacyValue !== null && legacyValue !== ''
    ? legacyValue
    : fallback;
}

function detectInstallState(vscode, context, constants) {
  const legacy = vscode.extensions.getExtension(constants.legacyExtensionId);
  const current = vscode.extensions.getExtension(constants.extensionId);
  const legacyPresent = !!legacy && legacy.id !== context.extension.id;
  return {
    extension_id: context.extension.id,
    expected_extension_id: constants.extensionId,
    legacy_extension_id: constants.legacyExtensionId,
    version: constants.extensionVersion,
    duplicate_extension_detected: legacyPresent && !!current,
    legacy_extension_present: legacyPresent,
    stale_install_detected: legacyPresent || context.extension.id !== constants.extensionId,
    legacy_extension_version: legacy && legacy.packageJSON
      ? String(legacy.packageJSON.version || '')
      : '',
    backend_compatibility: runBackendCompatibilityPreflight(workspaceRoot(vscode, ''))
  };
}

function buildBlockedResult(installState, constants) {
  const state = installState && typeof installState === 'object' ? installState : {};
  const compatibility = projectBackendCompatibility(state.backend_compatibility);
  const safeLegacyVersion = (
    typeof state.legacy_extension_version === 'string'
    && /^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$/.test(state.legacy_extension_version)
      ? state.legacy_extension_version
      : ''
  );
  const safeState = {
    extension_id: state.extension_id === constants.extensionId ? constants.extensionId : 'unknown',
    expected_extension_id: constants.extensionId,
    legacy_extension_id: constants.legacyExtensionId,
    version: constants.extensionVersion,
    duplicate_extension_detected: state.duplicate_extension_detected === true,
    legacy_extension_present: state.legacy_extension_present === true,
    stale_install_detected: state.stale_install_detected === true,
    legacy_extension_version: safeLegacyVersion,
    backend_compatibility: compatibility
  };
  const reasons = compatibility.rejection_reasons.slice();
  const reviewPacket = {
    schema_version: 'reddog_backend_compatibility_block.v1',
    decision: 'BLOCKED_LOCALLY',
    blocked_stage: 'pre_grounding_backend_compatibility',
    backend_compatibility_preflight: compatibility,
    typed_target_extraction_applied: false,
    grounding_preflight_applied: false,
    no_holoindex_query_performed: true,
    no_model_call_performed: true,
    made_network_call: false,
    no_permission_probe_performed: true,
    no_work_order_emitted: true,
    no_repo_mutation_performed: true
  };
  const content = [
    '## RedDog Backend Compatibility',
    '',
    '- decision: BLOCKED_LOCALLY [OBSERVED]',
    '- blocked_stage: pre_grounding_backend_compatibility [OBSERVED]',
    '- reasons: ' + reasons.join(', ') + ' [OBSERVED]',
    '- next_action: Open a current compatible Foundups-Agent workspace and retry. [INFERRED]',
    '- no_holoindex_query_performed: true [OBSERVED]',
    '- no_model_call_performed: true [OBSERVED]',
    '- made_network_call: false [OBSERVED]',
    '- no_permission_probe_performed: true [OBSERVED]',
    '- no_work_order_emitted: true [OBSERVED]'
  ].join('\n');
  return {
    ok: false,
    reason: 'backend_compatibility_preflight_blocked',
    detail: reasons.join(', '),
    content,
    review_packet: reviewPacket,
    install_state: safeState,
    copy_markdown: content + '\n\n' + constants.buildInstallStateSection(safeState)
  };
}

function installStatusMessage(state) {
  const value = state && typeof state === 'object' ? state : {};
  const compatibility = value.backend_compatibility;
  if (value.stale_install_detected) {
    return 'Legacy extension detected: remove foundups-fusion-worker after migration.';
  }
  if (!compatibility || compatibility.passed !== true) {
    const reasons = compatibility && Array.isArray(compatibility.rejection_reasons)
      ? compatibility.rejection_reasons.join(', ')
      : 'backend_compatibility_unavailable';
    return 'Backend compatibility: BLOCKED (' + reasons + ').';
  }
  return 'Install state: canonical RedDog extension. Backend compatibility: PASS.';
}

function activationWarning(state) {
  const value = state && typeof state === 'object' ? state : {};
  if (value.stale_install_detected) {
    return 'RedDog detected a legacy Foundups Fusion Worker install. Keep only one RedDog extension active after migration.';
  }
  return value.backend_compatibility && value.backend_compatibility.passed === true
    ? ''
    : installStatusMessage(value);
}

function enforceRuntimeGate(runtimeGate, compatibility) {
  const gate = runtimeGate && typeof runtimeGate === 'object' ? runtimeGate : {};
  if (!compatibility || compatibility.passed !== true) {
    gate.passed = false;
    gate.rejection_reasons = Array.from(new Set([
      ...(Array.isArray(gate.rejection_reasons) ? gate.rejection_reasons : []),
      'backend_compatibility_changed_before_action_planning'
    ]));
  }
  return gate;
}

module.exports = {
  BACKEND_API_VERSION,
  BACKEND_MANIFEST_PATH,
  BACKEND_MANIFEST_SCHEMA,
  BACKEND_PRODUCT,
  EXPECTED_MANIFEST_SHA256,
  MAX_BRIDGE_BYTES,
  MAX_MANIFEST_BYTES,
  REQUIRED_BRIDGE_FILES,
  REQUIRED_REPOSITORY_MARKERS,
  activationWarning,
  buildBlockedResult,
  configurationValue,
  detectInstallState,
  enforceRuntimeGate,
  installStatusMessage,
  projectBackendCompatibility,
  runBackendCompatibilityPreflight,
  validateManifest,
  workspaceRoot
};
