'use strict';

const SCHEMA_VERSION = 'reddog_conversation_history_policy.v1';
const MODE = 'raw_history_disabled_until_authenticated_scope';

function boundedCount(value) {
  return Array.isArray(value) ? Math.min(value.length, 1000) : 0;
}

function promptAssemblyKey(requested) {
  return SCHEMA_VERSION + ':' + (requested ? 'requested' : 'disabled') + ':admitted=0';
}

function enforceHistoryPolicy(options) {
  const opts = options && typeof options === 'object' ? options : {};
  const requested = opts.inclusionRequested === true;
  const storedCount = boundedCount(opts.storedHistory);
  return {
    admittedHistory: [],
    telemetry: {
      schema_version: SCHEMA_VERSION,
      policy_mode: MODE,
      history_inclusion_requested: requested,
      stored_history_turn_count: storedCount,
      admitted_turn_count: 0,
      admitted_turn_ids: [],
      model_history_attached: false,
      scoped_history_authority_available: false,
      history_policy_reason: requested
        ? 'authenticated_scoped_history_unavailable'
        : 'disabled_by_operator',
      prompt_assembly_policy_key: promptAssemblyKey(requested),
      provider_history_discarded_count: 0,
      no_work_authority_from_history: true
    }
  };
}

function prepareHistoryAdmission(state, inclusionRequested) {
  const mutableState = state && typeof state === 'object' ? state : {};
  const admission = enforceHistoryPolicy({
    inclusionRequested,
    storedHistory: mutableState.history
  });
  mutableState.history = [];
  return admission;
}

function withProviderHistoryDiscarded(telemetry, providerHistory) {
  return Object.assign({}, normalizeTelemetry(telemetry), {
    provider_history_discarded_count: boundedCount(providerHistory),
    model_history_attached: false,
    admitted_turn_count: 0,
    admitted_turn_ids: []
  });
}

function discardProviderHistory(admission, result, promptConstruction) {
  const context = admission && typeof admission === 'object' ? admission : {};
  const updated = withProviderHistoryDiscarded(context.telemetry, result && result.history);
  context.telemetry = updated;
  if (result && typeof result === 'object') {
    delete result.history;
    result.conversation_history_policy = updated;
  }
  if (promptConstruction && typeof promptConstruction === 'object') {
    promptConstruction.conversation_history_policy = updated;
  }
  return updated;
}

function normalizeTelemetry(value) {
  const incoming = value && typeof value === 'object' ? value : {};
  const requested = incoming.history_inclusion_requested === true;
  return {
    schema_version: SCHEMA_VERSION,
    policy_mode: MODE,
    history_inclusion_requested: requested,
    stored_history_turn_count: Number.isInteger(incoming.stored_history_turn_count)
      ? Math.max(0, incoming.stored_history_turn_count)
      : 0,
    admitted_turn_count: 0,
    admitted_turn_ids: [],
    model_history_attached: false,
    scoped_history_authority_available: false,
    history_policy_reason: requested
      ? 'authenticated_scoped_history_unavailable'
      : 'disabled_by_operator',
    prompt_assembly_policy_key: promptAssemblyKey(requested),
    provider_history_discarded_count: Number.isInteger(incoming.provider_history_discarded_count)
      ? Math.max(0, incoming.provider_history_discarded_count)
      : 0,
    no_work_authority_from_history: true
  };
}

function formatTelemetryLines(value) {
  const telemetry = normalizeTelemetry(value);
  return [
    '- conversation_history_policy: ' + telemetry.policy_mode,
    '- history_inclusion_requested: ' + (telemetry.history_inclusion_requested ? 'true' : 'false'),
    '- stored_history_turn_count: ' + telemetry.stored_history_turn_count,
    '- admitted_turn_count: 0',
    '- admitted_turn_ids: []',
    '- model_history_attached: false',
    '- scoped_history_authority_available: false',
    '- history_policy_reason: ' + telemetry.history_policy_reason,
    '- prompt_assembly_policy_key: ' + telemetry.prompt_assembly_policy_key,
    '- provider_history_discarded_count: ' + telemetry.provider_history_discarded_count,
    '- no_work_authority_from_history: true'
  ];
}

function buildTelemetrySection(value) {
  return ['## Conversation History Policy'].concat(formatTelemetryLines(value)).join('\n');
}

module.exports = {
  MODE,
  SCHEMA_VERSION,
  buildTelemetrySection,
  discardProviderHistory,
  enforceHistoryPolicy,
  formatTelemetryLines,
  normalizeTelemetry,
  prepareHistoryAdmission,
  withProviderHistoryDiscarded
};
