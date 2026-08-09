'use strict';

const constants = require('./backend_compatibility_constants');
const filesystem = require('./backend_compatibility_filesystem');
const manifestContract = require('./backend_compatibility_manifest');

function runtimeEvidencePayload(manifestRead, runtimeResult) {
  return JSON.stringify({
    manifest_digest: manifestRead.manifestDigest,
    runtime_file_count: Object.keys(runtimeResult.observedDigests).length,
    runtime_total_bytes: runtimeResult.totalBytes,
    runtime_digests: runtimeResult.observedDigests
  });
}

function verifyBackend(rootState, deps) {
  const read = manifestContract.readManifest(rootState, deps);
  const reasons = read.reason ? [read.reason] : [];
  let runtimeResult = { reasons: [], observedDigests: {}, totalBytes: 0 };
  if (read.manifest) {
    const contractReasons = manifestContract.validateManifest(read.manifest);
    reasons.push(...contractReasons);
    if (!contractReasons.length) {
      runtimeResult = manifestContract.verifyRuntimeFiles(rootState, read.manifest, deps);
      reasons.push(...runtimeResult.reasons);
      reasons.push(...manifestContract.verifyRepositoryMarkers(rootState, deps));
    }
  }
  return { read, reasons, runtimeResult };
}

function preflightCounts(manifest) {
  return {
    required_bridge_count: constants.REQUIRED_BRIDGE_FILES.length,
    required_runtime_file_count: manifest && Array.isArray(manifest.required_runtime_files)
      ? manifest.required_runtime_files.length
      : 0,
    required_repository_marker_count: constants.REQUIRED_REPOSITORY_MARKERS.length
  };
}

function preflightReceipt(rootState, verified, deps) {
  const reasons = Array.from(new Set(verified.reasons));
  const manifest = verified.read.manifest;
  const evidence = runtimeEvidencePayload(verified.read, verified.runtimeResult);
  return Object.freeze({
    schema_version: 'reddog_backend_compatibility_preflight.v2',
    checked: true,
    passed: reasons.length === 0,
    backend_manifest_integrity_verified:
      verified.read.manifestDigest === constants.EXPECTED_MANIFEST_SHA256,
    backend_runtime_integrity_verified:
      !!manifest && verified.runtimeResult.reasons.length === 0,
    backend_api_version: manifest && Number.isInteger(manifest.backend_api_version)
      ? manifest.backend_api_version
      : null,
    extension_backend_api_version: constants.BACKEND_API_VERSION,
    ...preflightCounts(manifest),
    workspace_root_digest: filesystem.sha256Receipt(
      rootState.canonicalRoot || rootState.root,
      deps.crypto
    ),
    backend_evidence_digest: filesystem.sha256Receipt(evidence, deps.crypto),
    rejection_reasons: Object.freeze(reasons),
    no_holoindex_query_performed: true,
    no_model_call_performed: true,
    no_permission_probe_performed: true,
    no_work_order_emitted: true,
    no_repo_mutation_performed: true
  });
}

function runBackendCompatibilityPreflight(rootValue, options) {
  const deps = filesystem.dependencies(options);
  const rootState = filesystem.safeRoot(rootValue, deps);
  if (rootState.reason) {
    return preflightReceipt(
      rootState,
      {
        read: { manifest: null, manifestDigest: '' },
        reasons: [rootState.reason],
        runtimeResult: { reasons: [], observedDigests: {}, totalBytes: 0 }
      },
      deps
    );
  }
  return preflightReceipt(rootState, verifyBackend(rootState, deps), deps);
}

function safeDigest(candidate) {
  return typeof candidate === 'string' && /^sha256:[a-f0-9]{64}$/.test(candidate)
    ? candidate
    : 'unknown';
}

function safeReasons(value) {
  if (!Array.isArray(value)) {
    return ['backend_compatibility_unavailable'];
  }
  return Array.from(new Set(value.map((reason) => (
    typeof reason === 'string'
    && reason.length <= 240
    && /^[A-Za-z0-9_./:-]+$/.test(reason)
      ? reason
      : 'backend_compatibility_rejection_redacted'
  ))));
}

function projectedCounts(source) {
  const count = (key) => Number.isInteger(source[key]) ? source[key] : 0;
  return {
    required_bridge_count: count('required_bridge_count'),
    required_runtime_file_count: count('required_runtime_file_count'),
    required_repository_marker_count: count('required_repository_marker_count')
  };
}

function projectBackendCompatibility(value) {
  const source = value && typeof value === 'object' ? value : {};
  return Object.freeze({
    schema_version: 'reddog_backend_compatibility_preflight.v2',
    checked: source.checked === true,
    passed: source.passed === true,
    backend_manifest_integrity_verified: source.backend_manifest_integrity_verified === true,
    backend_runtime_integrity_verified: source.backend_runtime_integrity_verified === true,
    backend_api_version: Number.isInteger(source.backend_api_version)
      ? source.backend_api_version
      : null,
    extension_backend_api_version: Number.isInteger(source.extension_backend_api_version)
      ? source.extension_backend_api_version
      : constants.BACKEND_API_VERSION,
    ...projectedCounts(source),
    workspace_root_digest: safeDigest(source.workspace_root_digest),
    backend_evidence_digest: safeDigest(source.backend_evidence_digest),
    rejection_reasons: Object.freeze(safeReasons(source.rejection_reasons)),
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

function explicitConfigurationValue(configuration, key) {
  if (!configuration || typeof configuration.inspect !== 'function') return undefined;
  const inspected = configuration.inspect(key);
  if (!inspected || typeof inspected !== 'object') return undefined;
  for (const field of [
    'workspaceFolderLanguageValue', 'workspaceFolderValue',
    'workspaceLanguageValue', 'workspaceValue',
    'globalLanguageValue', 'globalValue'
  ]) {
    const value = inspected[field];
    if (value !== undefined && value !== null && value !== '') return value;
  }
  return undefined;
}

function configurationValue(vscode, currentNamespace, legacyNamespace, key, fallback) {
  const current = vscode.workspace.getConfiguration(currentNamespace);
  const legacy = vscode.workspace.getConfiguration(legacyNamespace);
  const explicitCurrent = explicitConfigurationValue(current, key);
  if (explicitCurrent !== undefined) return explicitCurrent;
  const explicitLegacy = explicitConfigurationValue(legacy, key);
  if (explicitLegacy !== undefined) return explicitLegacy;
  const currentValue = current.get(key);
  if (currentValue !== undefined && currentValue !== null && currentValue !== '') {
    return currentValue;
  }
  const legacyValue = legacy.get(key);
  return legacyValue !== undefined && legacyValue !== null && legacyValue !== ''
    ? legacyValue
    : fallback;
}

function detectInstallState(vscode, context, client) {
  const legacy = vscode.extensions.getExtension(client.legacyExtensionId);
  const current = vscode.extensions.getExtension(client.extensionId);
  const legacyPresent = !!legacy && legacy.id !== context.extension.id;
  return {
    extension_id: context.extension.id,
    expected_extension_id: client.extensionId,
    legacy_extension_id: client.legacyExtensionId,
    version: client.extensionVersion,
    duplicate_extension_detected: legacyPresent && !!current,
    legacy_extension_present: legacyPresent,
    stale_install_detected: legacyPresent || context.extension.id !== client.extensionId,
    legacy_extension_version: legacy && legacy.packageJSON
      ? String(legacy.packageJSON.version || '')
      : '',
    backend_compatibility: runBackendCompatibilityPreflight(workspaceRoot(vscode, ''))
  };
}

function safeInstallState(state, compatibility, client) {
  const version = typeof state.legacy_extension_version === 'string'
    && /^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$/.test(state.legacy_extension_version)
    ? state.legacy_extension_version
    : '';
  return {
    extension_id: state.extension_id === client.extensionId ? client.extensionId : 'unknown',
    expected_extension_id: client.extensionId,
    legacy_extension_id: client.legacyExtensionId,
    version: client.extensionVersion,
    duplicate_extension_detected: state.duplicate_extension_detected === true,
    legacy_extension_present: state.legacy_extension_present === true,
    stale_install_detected: state.stale_install_detected === true,
    legacy_extension_version: version,
    backend_compatibility: compatibility
  };
}

function blockedReviewPacket(compatibility) {
  return {
    schema_version: 'reddog_backend_compatibility_block.v2',
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
}

function blockedContent(reasons) {
  return [
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
}

function buildBlockedResult(installState, client) {
  const source = installState && typeof installState === 'object' ? installState : {};
  const compatibility = projectBackendCompatibility(source.backend_compatibility);
  const safeState = safeInstallState(source, compatibility, client);
  const content = blockedContent(compatibility.rejection_reasons);
  return {
    ok: false,
    reason: 'backend_compatibility_preflight_blocked',
    detail: compatibility.rejection_reasons.join(', '),
    content,
    review_packet: blockedReviewPacket(compatibility),
    install_state: safeState,
    copy_markdown: content + '\n\n' + client.buildInstallStateSection(safeState)
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
  ...constants,
  activationWarning,
  buildBlockedResult,
  configurationValue,
  detectInstallState,
  enforceRuntimeGate,
  installStatusMessage,
  projectBackendCompatibility,
  runBackendCompatibilityPreflight,
  validateManifest: manifestContract.validateManifest,
  workspaceRoot
};
