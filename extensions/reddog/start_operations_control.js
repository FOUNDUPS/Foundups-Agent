'use strict';

const crypto = require('crypto');
const grounding = require('./grounded_target_continuity');

const CONTROL_SCHEMA = 'reddog_start_operations_control.v1';
const RESULT_SCHEMA = 'reddog_start_operations_control_result.v1';
const PROGRESS_SCHEMA = 'reddog_start_operations_progress.v1';
const PROFILE_ID = 'reddog_readonly_architect_operations.v1';
const EFFECT_EVIDENCE_LEVEL = 'IMPLEMENTATION_BOUNDARY_ATTESTATION';
const COMMANDS = new Map([
  ['start operations', 'submit'],
  ['operations status', 'status'],
  ['stop operations', 'cancel'],
  ['resume operations', 'resume']
]);
const REQUIRED_BOUNDARY_FIELDS = [
  'no_extension_fusion_call_performed',
  'no_repo_mutation_performed',
  'no_shell_command_executed',
  'no_hermes_dispatch_performed',
  'no_worktree_operation_performed',
  'no_pr_created',
  'no_merge_performed'
];
const BOUNDARY_ATTESTATIONS = Object.freeze({
  effect_evidence_level: EFFECT_EVIDENCE_LEVEL,
  no_extension_fusion_call_performed: true,
  no_maintenance_performed: true,
  no_repo_mutation_performed: true,
  no_shell_command_executed: true,
  no_hermes_dispatch_performed: true,
  no_worktree_operation_performed: true,
  no_pr_created: true,
  no_merge_performed: true
});
const EMPTY_RESULT_FIELDS = Object.freeze({
  intent_id: '', cycle_id: '', repo_head_sha: '',
  architect_action: '', architect_next_slice: '', determination_id: '',
  task_status_counts: Object.freeze({}), duplicate_intent_reused: false,
  recovered_existing_cycle: false, deferred_holo_maintenance: false,
  holo_repair_attempted: false, holo_repair_task_id: '',
  holo_repair_status: '', holo_repair_generation_id: '',
  holo_repair_freshness_receipt_digest: '',
  grounding_retried_after_repair: false
});

function classify(text) {
  const raw = String(text || '');
  if (!/^[\x20-\x7e]*$/.test(raw)) return null;
  const normalized = raw.trim().toLowerCase();
  const action = COMMANDS.get(normalized);
  if (!action || /[\r\n]/.test(raw)) return null;
  return { action, normalized, operationsProfileId: PROFILE_ID };
}

function buildRequest(command, intentId, repoRoot, repoStateReceipt) {
  const value = command && typeof command === 'object' ? command : {};
  return {
    schema_version: CONTROL_SCHEMA,
    action: value.action,
    control_request_id: 'sha256:' + crypto.randomBytes(32).toString('hex'),
    operations_profile_id: PROFILE_ID,
    intent_id: value.action === 'submit' ? '' : String(intentId || ''),
    repo_root: String(repoRoot || ''),
    repo_state_receipt: copiedReceipt(repoStateReceipt)
  };
}

function copiedReceipt(value) {
  try {
    return value && typeof value === 'object'
      ? JSON.parse(JSON.stringify(value)) : null;
  } catch (_err) {
    return null;
  }
}

function validateProgress(value, request) {
  if (!value || value.schema_version !== PROGRESS_SCHEMA) return null;
  const body = { ...value };
  delete body.progress_id;
  return value.progress_id === grounding.canonicalDigest(body)
    && value.stage === 'resident_cycle_submitting'
    && matchesRequest(value, request)
    && String(value.intent_id || '').startsWith('sha256:')
    && value.operations_profile_id === PROFILE_ID
    ? value
    : null;
}

function validateResult(value, request) {
  if (!value || value.schema_version !== RESULT_SCHEMA) return null;
  const body = { ...value };
  delete body.response_id;
  if (value.response_id !== grounding.canonicalDigest(body)) return null;
  if (value.operations_profile_id !== PROFILE_ID) return null;
  if (!['submit', 'status', 'cancel', 'resume'].includes(value.action)) return null;
  if (!Array.isArray(value.rejection_reasons)) return null;
  if (!REQUIRED_BOUNDARY_FIELDS.every((field) => value[field] === true)) return null;
  if (!validHoloRepairEvidence(value)) return null;
  if (value.effect_evidence_level !== EFFECT_EVIDENCE_LEVEL) return null;
  if (!matchesRequest(value, request)) return null;
  return value;
}

function validHoloRepairEvidence(value) {
  if (typeof value.no_maintenance_performed !== 'boolean') return false;
  if (value.holo_repair_attempted !== true) return validNoRepair(value);
  if (!['OWNER_READY', 'REPAIRED', 'DEFERRED', 'FAILED', 'REJECTED']
    .includes(value.holo_repair_status)) return false;
  if (value.holo_repair_status === 'OWNER_READY') return validReadyOwner(value);
  if (value.holo_repair_status === 'REPAIRED') return validRepairedOwner(value);
  if (value.grounding_retried_after_repair !== false) return false;
  if (value.holo_repair_generation_id !== ''
    || value.holo_repair_freshness_receipt_digest !== '') return false;
  if (value.no_maintenance_performed === false
    && !String(value.holo_repair_task_id || '')
      .startsWith('reddog_start_operations_holo_repair:')) return false;
  return true;
}

function validNoRepair(value) {
  return value.no_maintenance_performed === true
    && value.holo_repair_task_id === ''
    && value.holo_repair_status === ''
    && value.holo_repair_generation_id === ''
    && value.holo_repair_freshness_receipt_digest === ''
    && value.grounding_retried_after_repair === false;
}

function validReadyOwner(value) {
  return value.no_maintenance_performed === true
    && value.holo_repair_task_id === ''
    && value.grounding_retried_after_repair === true
    && validRepairDigests(value);
}

function validRepairedOwner(value) {
  return typeof value.no_maintenance_performed === 'boolean'
    && String(value.holo_repair_task_id || '')
      .startsWith('reddog_start_operations_holo_repair:')
    && value.grounding_retried_after_repair === true
    && validRepairDigests(value);
}

function validRepairDigests(value) {
  return /^sha256:[a-f0-9]{64}$/.test(
    String(value.holo_repair_generation_id || '')
  ) && /^sha256:[a-f0-9]{64}$/.test(
    String(value.holo_repair_freshness_receipt_digest || '')
  );
}

function matchesRequest(value, request) {
  if (!request || value.action !== request.action) return false;
  if (value.control_request_id !== request.control_request_id) return false;
  return request.action === 'submit' || value.intent_id === request.intent_id;
}

function failureResult(action, reason, request) {
  const expected = request && typeof request === 'object' ? request : {};
  return {
    schema_version: RESULT_SCHEMA,
    ...EMPTY_RESULT_FIELDS,
    ...BOUNDARY_ATTESTATIONS,
    accepted: false,
    action: String(action || ''),
    control_request_id: String(expected.control_request_id || ''),
    operations_profile_id: PROFILE_ID,
    status: 'REJECTED',
    rejection_reasons: [String(reason || 'start_operations_bridge_failed')]
  };
}

function requiresProductionBinding(command) {
  return Boolean(command && ['submit', 'resume'].includes(command.action));
}

function bindingRejection(command, worker) {
  if (!requiresProductionBinding(command)) return '';
  return worker && worker.modelBindingSource === 'receipt_bound_runtime'
    ? ''
    : 'start_operations_requires_receipt_bound_model_runtime';
}

function render(result) {
  const value = result && typeof result === 'object' ? result : {};
  return [
    '## RedDog Operations Control',
    '- profile: ' + (value.operations_profile_id || PROFILE_ID) + ' [OBSERVED]',
    '- action: ' + (value.action || 'unknown') + ' [OBSERVED]',
    '- accepted: ' + (value.accepted === true ? 'true' : 'false') + ' [OBSERVED]',
    '- status: ' + (value.status || 'unknown') + ' [OBSERVED]',
    '- intent_id: ' + (value.intent_id || '(none)') + ' [OBSERVED]',
    '- cycle_id: ' + (value.cycle_id || '(none)') + ' [OBSERVED]',
    '- repo_head_sha: ' + (value.repo_head_sha || '(none)') + ' [OBSERVED]',
    '- architect_action: ' + (value.architect_action || '(none)') + ' [OBSERVED]',
    '- architect_next_slice: ' + (value.architect_next_slice || '(none)') + ' [OBSERVED]',
    '- deferred_holo_maintenance: ' + (value.deferred_holo_maintenance === true ? 'true' : 'false') + ' [OBSERVED]',
    '- holo_repair_status: ' + (value.holo_repair_status || '(none)') + ' [OBSERVED]',
    '- grounding_retried_after_repair: ' + (value.grounding_retried_after_repair === true ? 'true' : 'false') + ' [OBSERVED]',
    '- rejection_reasons: ' + JSON.stringify(value.rejection_reasons || []) + ' [OBSERVED]',
    '- effect_evidence_level: ' + (value.effect_evidence_level || '(none)') + ' [OBSERVED]',
    '',
    'This control starts or manages the bounded read-only audit/determination cycle.',
    'No-effect fields are implementation-boundary attestations, not independent forensic proof.',
    'It does not grant source, shell, worktree, PR, merge, HoloIndex mutation, or Hermes authority.'
  ].join('\n');
}

module.exports = {
  CONTROL_SCHEMA,
  PROFILE_ID,
  PROGRESS_SCHEMA,
  RESULT_SCHEMA,
  bindingRejection,
  buildRequest,
  classify,
  failureResult,
  render,
  requiresProductionBinding,
  validateProgress,
  validateResult
};
