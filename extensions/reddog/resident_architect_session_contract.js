'use strict';

const crypto = require('crypto');

function buildPayload(workFocus, options, bindings) {
  const opts = options && typeof options === 'object' ? options : {};
  const deps = bindings && typeof bindings === 'object' ? bindings : {};
  if (opts.explicitResidentArchitectSessionRequested !== true) {
    return rejected('explicit_resident_architect_session_request_missing');
  }
  const focus = String(workFocus || '');
  const groundingReceipt = deps.groundedTargetContinuity.buildGroundedTargetReceipt(
    focus, opts.groundingPreflight, opts.holoScorecard, 'editor_thin_client'
  );
  if (!deps.groundedTargetContinuity.receiptReady(groundingReceipt)) {
    return rejected('grounded_target_receipt_not_ready');
  }
  const residentFoundupTarget = groundingReceipt.registered_foundup_target;
  const root = opts.repoRoot || deps.workspaceRoot();
  if (residentFoundupTarget && !deps.foundupWorkRuntime.verifyAtUse(
    root, residentFoundupTarget, deps.gitOutput, deps.gitOutputTruncatedMarker
  )) {
    return rejected('registered_foundup_target_use_time_verification_failed');
  }
  const authenticatedPrincipal = String(
    opts.authenticatedPrincipal || deps.environment.REDDOG_AUTHENTICATED_PRINCIPAL_ID || ''
  ).trim();
  const authorizedFoundupIds = authorizedFoundups(opts, deps.environment);
  const scope = deps.foundupWorkRuntime.residentScope(groundingReceipt, opts.foundupId);
  if (scope.conflict) return rejected('resident_architect_grounded_foundup_mismatch');
  if (!authenticatedPrincipal || !scope.foundupId || !authorizedFoundupIds.includes(scope.foundupId)) {
    return rejected('resident_architect_authenticated_scope_missing');
  }
  const intentId = digestIntent(groundingReceipt, authenticatedPrincipal, scope.foundupId, deps);
  return {
    ok: true,
    rejection_reasons: [],
    payload: buildIntentPayload(focus, groundingReceipt, authenticatedPrincipal, scope.foundupId, intentId, opts, deps)
  };
}

function authorizedFoundups(options, environment) {
  if (Array.isArray(options.authorizedFoundupIds)) {
    return options.authorizedFoundupIds.map(clean).filter(Boolean);
  }
  return String(environment.REDDOG_AUTHORIZED_FOUNDUP_IDS || '').split(',').map(clean).filter(Boolean);
}

function digestIntent(groundingReceipt, principalId, foundupId, bindings) {
  return 'sha256:' + crypto.createHash('sha256').update([
    bindings.productSlice,
    bindings.extensionVersion,
    groundingReceipt.receipt_id,
    principalId,
    foundupId
  ].join('|'), 'utf8').digest('hex');
}

function buildIntentPayload(focus, groundingReceipt, principalId, foundupId, intentId, options, bindings) {
  return {
    red_dog_intent: {
      schema_version: 'reddog_intent.v2',
      intent_id: intentId,
      origin: 'extension',
      source_surface: 'editor_thin_client',
      principal_ref: principalId,
      foundup_id: foundupId,
      extension_id: bindings.extensionId,
      extension_version: bindings.extensionVersion,
      work_focus: focus,
      grounding_receipt: groundingReceipt,
      requested_operation: 'resident_architect_session',
      submits_executable_authority: false,
      shell_authority_requested: false,
      repo_write_authority_requested: false,
      merge_authority_requested: false
    },
    intent_id: intentId,
    grounding_receipt_id: groundingReceipt.receipt_id,
    explicit_resident_architect_session_requested: true,
    work_focus: focus,
    repo_root: options.repoRoot ? String(options.repoRoot) : undefined,
    work_state_path: options.workStatePath ? String(options.workStatePath) : undefined,
    holoindex_receipt_path: options.holoindexReceiptPath ? String(options.holoindexReceiptPath) : undefined,
    holoindex_ssd_path: options.holoindexSsdPath ? String(options.holoindexSsdPath) : undefined,
    timeout_seconds: Number(options.timeoutSeconds || 60)
  };
}

function buildResult(decision, fields, bindings) {
  const payload = fields && typeof fields === 'object' ? fields : {};
  return Object.assign({
    product_slice_name: bindings.productSlice,
    slice_name: bindings.sessionSlice,
    decision,
    accepted: false,
    resident_backend_invoked: false,
    red_dog_intent_submitted: false,
    intent_id: '', cycle_id: '', python_invocation_performed: false,
    snapshot_id: '', final_snapshot_id: '', swarm_id: '',
    initial_status: '', final_status: '',
    task_count: 0, reports_persisted: 0,
    readonly_audit_tasks_enqueued: false,
    readonly_audit_tasks_executed: false,
    architect_action: '', architect_next_slice: '', architect_determination_id: '',
    queue_candidate_count: 0,
    no_shell_command_executed: true,
    no_repo_mutation_performed: true,
    no_holoindex_reindex_performed: true,
    no_hermes_dispatch_performed: true,
    no_worktree_operation_performed: true,
    no_pr_created: true,
    no_pattern_memory_promotion_performed: true,
    no_live_foundup_enqueue_performed: true,
    coding_worker_spawned: false,
    rejection_reasons: []
  }, payload);
}

function renderSection(sessionResult, bindings) {
  const r = sessionResult && typeof sessionResult === 'object' ? sessionResult : {};
  return [
    '## Resident RedDog Architect Session',
    line('product_slice_name', r.product_slice_name || bindings.productSlice),
    line('slice_name', r.slice_name || bindings.sessionSlice),
    line('red_dog_intent_submitted', flag(r.red_dog_intent_submitted)),
    line('intent_id', r.intent_id || 'unknown'),
    line('cycle_id', r.cycle_id || r.swarm_id || 'unknown'),
    line('decision', r.decision || 'unknown'),
    line('accepted', flag(r.accepted)),
    line('resident_backend_invoked', flag(r.resident_backend_invoked)),
    line('python_invocation_performed', flag(r.python_invocation_performed)),
    line('snapshot_id', r.snapshot_id || 'unknown'),
    line('final_snapshot_id', r.final_snapshot_id || 'unknown'),
    line('swarm_id', r.swarm_id || 'unknown'),
    line('initial_status', r.initial_status || 'unknown'),
    line('final_status', r.final_status || 'unknown'),
    line('task_count', Number(r.task_count || 0)),
    line('reports_persisted', Number(r.reports_persisted || 0)),
    line('readonly_audit_tasks_enqueued', flag(r.readonly_audit_tasks_enqueued)),
    line('readonly_audit_tasks_executed', flag(r.readonly_audit_tasks_executed)),
    line('architect_action', r.architect_action || 'unknown'),
    line('architect_next_slice', r.architect_next_slice || 'unknown'),
    line('architect_determination_id', r.architect_determination_id || 'unknown'),
    line('queue_candidate_count', Number(r.queue_candidate_count || 0)),
    line('no_repo_mutation_performed', flag(r.no_repo_mutation_performed)),
    line('no_holoindex_reindex_performed', flag(r.no_holoindex_reindex_performed)),
    line('no_hermes_dispatch_performed', flag(r.no_hermes_dispatch_performed)),
    line('no_worktree_operation_performed', flag(r.no_worktree_operation_performed)),
    line('no_pr_created', flag(r.no_pr_created)),
    line('no_live_foundup_enqueue_performed', flag(r.no_live_foundup_enqueue_performed)),
    line('coding_worker_spawned', flag(r.coding_worker_spawned)),
    line('rejection_reasons', JSON.stringify(r.rejection_reasons || [])),
    line('not_invoked_reason', r.not_invoked_reason || 'none')
  ].join('\n');
}

function rejected(reason) {
  return { ok: false, rejection_reasons: [reason], payload: null };
}

function clean(value) {
  return String(value || '').trim();
}

function flag(value) {
  return value === true ? 'true' : 'false';
}

function line(name, value) {
  return '- ' + name + ': ' + value + ' [OBSERVED]';
}

module.exports = { buildPayload, buildResult, renderSection };
