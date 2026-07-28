'use strict';

const grounding = require('./grounded_target_continuity');

const CONTROL_SCHEMA = 'reddog_start_operations_control.v1';
const RESULT_SCHEMA = 'reddog_start_operations_control_result.v1';
const PROGRESS_SCHEMA = 'reddog_start_operations_progress.v1';
const PROFILE_ID = 'reddog_readonly_architect_operations.v1';
const COMMANDS = new Map([
  ['start operations', 'submit'],
  ['operations status', 'status'],
  ['stop operations', 'cancel'],
  ['resume operations', 'resume']
]);
const REQUIRED_BOUNDARY_FIELDS = [
  'no_extension_fusion_call_performed',
  'no_maintenance_performed',
  'no_repo_mutation_performed',
  'no_shell_command_executed',
  'no_hermes_dispatch_performed',
  'no_worktree_operation_performed',
  'no_pr_created',
  'no_merge_performed'
];

function classify(text) {
  const raw = String(text || '');
  if (!/^[\x20-\x7e]*$/.test(raw)) return null;
  const normalized = raw.trim().toLowerCase();
  const action = COMMANDS.get(normalized);
  if (!action || /[\r\n]/.test(raw)) return null;
  return { action, normalized, operationsProfileId: PROFILE_ID };
}

function buildRequest(command, intentId, repoRoot) {
  const value = command && typeof command === 'object' ? command : {};
  return {
    schema_version: CONTROL_SCHEMA,
    action: value.action,
    operations_profile_id: PROFILE_ID,
    intent_id: value.action === 'submit' ? '' : String(intentId || ''),
    repo_root: String(repoRoot || '')
  };
}

function validateProgress(value) {
  if (!value || value.schema_version !== PROGRESS_SCHEMA) return null;
  const body = { ...value };
  delete body.progress_id;
  return value.progress_id === grounding.canonicalDigest(body)
    && value.stage === 'resident_cycle_submitting'
    && String(value.intent_id || '').startsWith('sha256:')
    && value.operations_profile_id === PROFILE_ID
    ? value
    : null;
}

function validateResult(value) {
  if (!value || value.schema_version !== RESULT_SCHEMA) return null;
  const body = { ...value };
  delete body.response_id;
  if (value.response_id !== grounding.canonicalDigest(body)) return null;
  if (value.operations_profile_id !== PROFILE_ID) return null;
  if (!['submit', 'status', 'cancel', 'resume'].includes(value.action)) return null;
  if (!Array.isArray(value.rejection_reasons)) return null;
  if (!REQUIRED_BOUNDARY_FIELDS.every((field) => value[field] === true)) return null;
  return value;
}

function failureResult(action, reason) {
  return {
    schema_version: RESULT_SCHEMA,
    accepted: false,
    action: String(action || ''),
    operations_profile_id: PROFILE_ID,
    intent_id: '',
    cycle_id: '',
    status: 'REJECTED',
    repo_head_sha: '',
    architect_action: '',
    architect_next_slice: '',
    determination_id: '',
    task_status_counts: {},
    duplicate_intent_reused: false,
    recovered_existing_cycle: false,
    deferred_holo_maintenance: false,
    rejection_reasons: [String(reason || 'start_operations_bridge_failed')],
    no_extension_fusion_call_performed: true,
    no_maintenance_performed: true,
    no_repo_mutation_performed: true,
    no_shell_command_executed: true,
    no_hermes_dispatch_performed: true,
    no_worktree_operation_performed: true,
    no_pr_created: true,
    no_merge_performed: true
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
    '- rejection_reasons: ' + JSON.stringify(value.rejection_reasons || []) + ' [OBSERVED]',
    '',
    'This control starts or manages the bounded read-only audit/determination cycle.',
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
