'use strict';

function compatibilityNumber(value, fallback) {
  return Number.isInteger(value) ? value : fallback;
}

function compatibilityReasons(value) {
  return Array.isArray(value) && value.length ? value.join(', ') : '(none)';
}

function installIdentityLines(state, constants) {
  return [
    '## RedDog Install State',
    '- extension_id: ' + (state.extension_id || 'unknown') + ' [OBSERVED]',
    '- expected_extension_id: ' + (state.expected_extension_id || constants.extensionId) + ' [OBSERVED]',
    '- extension_version: ' + (state.version || constants.extensionVersion) + ' [OBSERVED]',
    '- legacy_extension_present: ' + (state.legacy_extension_present === true ? 'true' : 'false') + ' [OBSERVED]',
    '- duplicate_extension_detected: ' + (state.duplicate_extension_detected === true ? 'true' : 'false') + ' [OBSERVED]',
    '- stale_install_detected: ' + (state.stale_install_detected === true ? 'true' : 'false') + ' [OBSERVED]',
    '- legacy_extension_version: ' + (state.legacy_extension_version || 'none') + ' [OBSERVED]'
  ];
}

function compatibilityLines(compatibility, constants) {
  return [
    '- backend_compatibility_checked: ' + (compatibility.checked === true ? 'true' : 'false') + ' [OBSERVED]',
    '- backend_compatibility_passed: ' + (compatibility.passed === true ? 'true' : 'false') + ' [OBSERVED]',
    '- backend_api_version: ' + compatibilityNumber(compatibility.backend_api_version, 'unknown') + ' [OBSERVED]',
    '- extension_backend_api_version: ' + compatibilityNumber(
      compatibility.extension_backend_api_version,
      constants.backendApiVersion
    ) + ' [OBSERVED]',
    '- backend_runtime_integrity_verified: ' + (
      compatibility.backend_runtime_integrity_verified === true ? 'true' : 'false'
    ) + ' [OBSERVED]',
    '- required_runtime_file_count: ' + compatibilityNumber(
      compatibility.required_runtime_file_count,
      0
    ) + ' [OBSERVED]',
    '- backend_compatibility_rejection_reasons: ' + compatibilityReasons(
      compatibility.rejection_reasons
    ) + ' [OBSERVED]',
    '- backend_workspace_root_digest: ' + (
      compatibility.workspace_root_digest || 'unknown'
    ) + ' [OBSERVED]'
  ];
}

function buildInstallStateSection(state, constants) {
  const value = state && typeof state === 'object' ? state : {};
  const compatibility = value.backend_compatibility && typeof value.backend_compatibility === 'object'
    ? value.backend_compatibility
    : {};
  return installIdentityLines(value, constants)
    .concat(compatibilityLines(compatibility, constants))
    .join('\n');
}

function resolveFusionWorker(configValue, defaults, panelLimit) {
  const cleanModel = (value, fallback) => (
    typeof value === 'string' && value.trim() && value.length <= 120
      ? value.trim()
      : fallback
  );
  const lead = cleanModel(configValue('leadModel', defaults.lead), defaults.lead);
  const configuredPanel = configValue('panelModels', defaults.panel);
  return {
    title: defaults.title,
    lead,
    panel: Array.isArray(configuredPanel)
      ? configuredPanel.map((item) => cleanModel(item, '')).filter(Boolean).slice(0, panelLimit)
      : defaults.panel
  };
}

module.exports = {
  buildInstallStateSection,
  resolveFusionWorker
};
