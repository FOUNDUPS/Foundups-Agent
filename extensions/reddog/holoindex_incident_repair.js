'use strict';

const cp = require('child_process');
const path = require('path');

const REPAIRABLE_ERRORS = Object.freeze([
  'HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH',
  'HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP',
  'QUERY_OWNER_POISONED',
  'SEMANTIC_BACKEND_UNAVAILABLE'
]);
const MAX_OUTPUT_BYTES = 256 * 1024;
const MAX_INPUT_BYTES = 64 * 1024;
const MAX_QUERY_CHARS = 16000;
const EXHAUSTED_OWNER_ATTEMPTS = 3;

function shouldCoordinate(ownerResult, ownerObserved) {
  const value = ownerResult && typeof ownerResult === 'object' ? ownerResult : {};
  if (Object.values(value).includes(value)) return false;
  const staleAuthority = value.error === 'HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH';
  const attemptsValid = staleAuthority
    ? value.owner_attempts === 0
    : value.owner_attempts === EXHAUSTED_OWNER_ATTEMPTS;
  return ownerObserved === true
    && value.ok === false
    && typeof value.error === 'string'
    && REPAIRABLE_ERRORS.includes(value.error)
    && value.index_gap_detected === true
    && value.no_holoindex_reindex_performed === true
    && attemptsValid
    && typeof value.workspace_repo_head_sha === 'string'
    && /^[0-9a-f]{40}$/.test(value.workspace_repo_head_sha)
    && typeof value.authority_repo_head_sha === 'string'
    && /^[0-9a-f]{40}$/.test(value.authority_repo_head_sha)
    && typeof value.authority_repo_root_digest === 'string'
    && /^sha256:[0-9a-f]{64}$/.test(value.authority_repo_root_digest)
    && (!staleAuthority
      || value.workspace_repo_head_sha !== value.authority_repo_head_sha)
    && value.no_authority_worktree_mutation_performed === true;
}

function compactOwnerFailure(value) {
  return {
    ok: value.ok,
    error: value.error,
    index_gap_detected: value.index_gap_detected === true,
    no_holoindex_reindex_performed: value.no_holoindex_reindex_performed === true,
    owner_attempts: value.owner_attempts,
    workspace_repo_head_sha: value.workspace_repo_head_sha,
    authority_repo_head_sha: value.authority_repo_head_sha,
    authority_repo_root_digest: value.authority_repo_root_digest,
    no_authority_worktree_mutation_performed: value.no_authority_worktree_mutation_performed === true
  };
}

function failure(reason) {
  return {
    accepted: false,
    status: 'REJECTED',
    rejection_reasons: [String(reason || 'holoindex_incident_bridge_failed')]
  };
}

function parseResult(stdout) {
  try {
    const value = JSON.parse(String(stdout || '{}'));
    return value && typeof value === 'object' ? value : failure('bridge_result_invalid');
  } catch (err) {
    return failure('bridge_result_invalid');
  }
}

function classifyError(err) {
  if (err && err.code === 'ETIMEDOUT') return 'bridge_timeout';
  if (err && err.code === 'ENOBUFS') return 'bridge_output_too_large';
  if (err && typeof err.status === 'number') return 'bridge_process_failed';
  return 'bridge_invocation_failed';
}

function coordinate(options) {
  const opts = options && typeof options === 'object' ? options : {};
  if (!shouldCoordinate(opts.ownerResult, opts.ownerObserved)) {
    return failure('owner_failure_not_repairable');
  }
  const query = typeof opts.query === 'string' ? opts.query.trim() : '';
  if (!query || query.length > MAX_QUERY_CHARS) return failure('incident_query_invalid');
  const payload = JSON.stringify({ query, owner_failure: compactOwnerFailure(opts.ownerResult) });
  if (Buffer.byteLength(payload, 'utf8') > MAX_INPUT_BYTES) {
    return failure('bridge_input_too_large');
  }
  const script = path.join(opts.root, 'scripts', 'reddog_holoindex_incident_repair_once.py');
  try {
    const stdout = cp.execFileSync(opts.interpreterPath, ['-B', script], {
      input: payload,
      cwd: opts.root,
      env: opts.env,
      encoding: 'utf8',
      timeout: 90000,
      maxBuffer: MAX_OUTPUT_BYTES,
      windowsHide: true
    });
    return parseResult(stdout);
  } catch (err) {
    return failure(classifyError(err));
  }
}

function immutableReceipt(value, reasons) {
  return {
    accepted: value.accepted === true,
    status: String(value.status || 'REJECTED'),
    schema_version: String(value.schema_version || ''),
    incident_kind: String(value.incident_kind || ''),
    incident_id: String(value.incident_id || ''),
    task_id: String(value.task_id || ''),
    request_event_id: String(value.request_event_id || ''),
    target_repo_head_sha: String(value.target_repo_head_sha || ''),
    workspace_repo_head_sha: String(value.workspace_repo_head_sha || ''),
    observed_authority_head_sha: String(value.observed_authority_head_sha || ''),
    authority_root_digest: String(value.authority_root_digest || ''),
    generation_id: String(value.generation_id || ''),
    freshness_receipt_digest: String(value.freshness_receipt_digest || ''),
    maintenance_enqueued: value.maintenance_enqueued === true,
    owner_requery_performed: value.owner_requery_performed === true,
    coding_candidate_required: value.coding_candidate_required === true,
    rejection_reasons: reasons,
    receipt_id: String(value.receipt_id || '')
  };
}

function metadataFields(value, reasons) {
  return {
    incident_repair_attempted: true,
    incident_repair_accepted: value.accepted === true,
    incident_repair_status: String(value.status || 'REJECTED'),
    incident_repair_id: String(value.incident_id || ''),
    incident_repair_task_id: String(value.task_id || ''),
    incident_repair_receipt_id: String(value.receipt_id || ''),
    incident_repair_target_repo_head_sha: String(value.target_repo_head_sha || ''),
    incident_repair_authority_root_digest: String(value.authority_root_digest || ''),
    incident_repair_generation_id: String(value.generation_id || ''),
    incident_repair_freshness_receipt_digest: String(value.freshness_receipt_digest || ''),
    incident_repair_enqueued: value.maintenance_enqueued === true,
    incident_repair_owner_requery_performed: value.owner_requery_performed === true,
    incident_repair_coding_candidate_required: value.coding_candidate_required === true,
    incident_repair_rejection_reasons: reasons,
    incident_repair_receipt: immutableReceipt(value, reasons)
  };
}

function metadata(receipt) {
  const value = receipt && typeof receipt === 'object' ? receipt : {};
  const reasons = Array.isArray(value.rejection_reasons)
    ? value.rejection_reasons.map(String) : [];
  return metadataFields(value, reasons);
}

module.exports = {
  compactOwnerFailure,
  shouldCoordinate,
  parseResult,
  coordinate,
  metadata
};
