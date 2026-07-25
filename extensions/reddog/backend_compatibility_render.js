'use strict';

function buildInstallStateSection(state, constants) {
  const s = state && typeof state === 'object' ? state : {};
  const compatibility = s.backend_compatibility && typeof s.backend_compatibility === 'object'
    ? s.backend_compatibility
    : {};
  return [
    '## RedDog Install State',
    '- extension_id: ' + (s.extension_id || 'unknown') + ' [OBSERVED]',
    '- expected_extension_id: ' + (s.expected_extension_id || constants.extensionId) + ' [OBSERVED]',
    '- extension_version: ' + (s.version || constants.extensionVersion) + ' [OBSERVED]',
    '- legacy_extension_present: ' + (s.legacy_extension_present === true ? 'true' : 'false') + ' [OBSERVED]',
    '- duplicate_extension_detected: ' + (s.duplicate_extension_detected === true ? 'true' : 'false') + ' [OBSERVED]',
    '- stale_install_detected: ' + (s.stale_install_detected === true ? 'true' : 'false') + ' [OBSERVED]',
    '- legacy_extension_version: ' + (s.legacy_extension_version || 'none') + ' [OBSERVED]',
    '- backend_compatibility_checked: ' + (compatibility.checked === true ? 'true' : 'false') + ' [OBSERVED]',
    '- backend_compatibility_passed: ' + (compatibility.passed === true ? 'true' : 'false') + ' [OBSERVED]',
    '- backend_api_version: ' + (
      Number.isInteger(compatibility.backend_api_version)
        ? compatibility.backend_api_version
        : 'unknown'
    ) + ' [OBSERVED]',
    '- extension_backend_api_version: ' + (
      Number.isInteger(compatibility.extension_backend_api_version)
        ? compatibility.extension_backend_api_version
        : constants.backendApiVersion
    ) + ' [OBSERVED]',
    '- backend_compatibility_rejection_reasons: ' + (
      Array.isArray(compatibility.rejection_reasons) && compatibility.rejection_reasons.length
        ? compatibility.rejection_reasons.join(', ')
        : '(none)'
    ) + ' [OBSERVED]',
    '- backend_workspace_root_digest: ' + (
      compatibility.workspace_root_digest || 'unknown'
    ) + ' [OBSERVED]'
  ].join('\n');
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
