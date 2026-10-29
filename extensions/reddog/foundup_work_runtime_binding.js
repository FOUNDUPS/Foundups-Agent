'use strict';

const grounding = require('./foundup_work_grounding');

function clone(value) {
  return value && typeof value === 'object' ? JSON.parse(JSON.stringify(value)) : null;
}

function strings(value) {
  return Array.isArray(value) ? Array.from(new Set(value.map(String).filter(Boolean))) : [];
}

function number(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function authorityContext(root, gitOutput, unavailableMarker, gitOutputs) {
  const operations = Object.freeze([
    'HEAD_SHA', 'FOUNDUP_REGISTRY_STATUS', 'TRACKED_PATHS', 'DIRTY_PATHS'
  ]);
  const values = typeof gitOutputs === 'function'
    ? gitOutputs(root, operations)
    : operations.map((name) => gitOutput(root, name));
  const head = values[0].trim();
  const status = values[1];
  const tracked = values[2];
  const dirty = values[3];
  const unavailable = [head, status, tracked, dirty]
    .some((value) => value.startsWith('[git context unavailable:'));
  return {
    repo_head_sha: unavailable ? '' : head,
    registry_status_clean: !unavailable && status.trim() === '',
    tracked_paths: unavailable || tracked.includes(unavailableMarker) ? [] : tracked.split(/\r?\n/).filter(Boolean),
    dirty_paths: unavailable || dirty.includes(unavailableMarker) ? [] : dirty.split(/\r?\n/).filter(Boolean)
  };
}

function resolve(root, taskText, gitOutput, unavailableMarker, gitOutputs) {
  return grounding.resolveFoundupWorkGrounding(
    root, taskText, authorityContext(root, gitOutput, unavailableMarker, gitOutputs)
  );
}

function verifyAtUse(root, receipt, gitOutput, unavailableMarker, gitOutputs) {
  return grounding.verifyFoundupWorkGroundingReceipt(
    root, receipt, authorityContext(root, gitOutput, unavailableMarker, gitOutputs)
  );
}

function preflightState(root, receipt, scorecard, gitOutput, unavailableMarker, gitOutputs) {
  const value = receipt && typeof receipt === 'object' ? receipt
    : { applied: false, passed: true, rejection_reasons: [], evidence_targets: [] };
  const verified = value.applied !== true || (value.passed === true
    && verifyAtUse(root, value, gitOutput, unavailableMarker, gitOutputs));
  const reasons = [];
  if (value.applied === true && value.passed !== true) {
    reasons.push('foundup_work_grounding_failed', ...strings(value.rejection_reasons));
  }
  if (value.applied === true && !verified) reasons.push('foundup_work_grounding_use_time_verification_failed');
  if (value.applied === true && scorecard && scorecard.foundup_work_grounding_receipt_id !== undefined
    && scorecard.foundup_work_grounding_receipt_id !== value.receipt_id) {
    reasons.push('foundup_work_grounding_receipt_mismatch');
  }
  return { receipt: value, verified, reasons, fields: {
    foundup_work_grounding_applied: value.applied === true,
    foundup_work_grounding_passed: value.passed === true,
    foundup_work_grounding_receipt_id: value.receipt_id || null,
    foundup_id: value.foundup_id || null,
    foundup_evidence_targets: strings(value.evidence_targets),
    foundup_grants_authority: value.grants_authority === true,
    foundup_resolution: value.foundup_resolution || (value.applied === true ? 'REGISTERED' : 'NOT_APPLICABLE'),
    foundup_requires_wsp109_resolution: value.requires_wsp109_resolution === true,
    foundup_use_time_verified: verified
  } };
}

function applyGroundingMeta(meta, receipt) {
  const target = meta && typeof meta === 'object' ? meta : {};
  const value = receipt && typeof receipt === 'object' ? receipt : {};
  target.foundup_work_grounding_applied = value.applied === true;
  target.foundup_work_grounding_passed = value.passed === true;
  target.foundup_work_grounding_rejection_reasons = strings(value.rejection_reasons);
  target.foundup_work_grounding_receipt_id = value.receipt_id || null;
  target.foundup_id = value.foundup_id || null;
  target.foundup_module_path = value.module_path || null;
  target.foundup_evidence_targets = strings(value.evidence_targets);
  target.foundup_grants_authority = value.grants_authority === true;
  if ((value.applied === true || value.foundup_language_present === true) && value.passed === true) {
    target.work_focus_target_derivation_sources = strings(
      (target.work_focus_target_derivation_sources || []).concat('foundup_registry')
    );
    target.work_focus_targets_derived = true;
  }
  return target;
}

function applyTypedMeta(meta, typedTargets) {
  const target = meta && typeof meta === 'object' ? meta : {};
  const typed = typedTargets && typeof typedTargets === 'object' ? typedTargets : {};
  if (typed.repo_file_targets_derived === true) {
    target.work_focus_targets_derived = true;
    target.work_focus_target_derivation_sources = strings(typed.repo_file_derivation_sources);
  }
  target.work_focus_targets_dropped_low_confidence = strings(typed.dropped_low_confidence);
  return target;
}

function wardrobePreflight(scorecard, options) {
  const observed = scorecard && typeof scorecard === 'object' ? scorecard : {};
  const opts = options && typeof options === 'object' ? options : {};
  const explicit = opts.groundingPreflight && typeof opts.groundingPreflight === 'object'
    ? opts.groundingPreflight : null;
  const source = explicit || observed;
  const reasons = strings(source.grounding_preflight_rejection_reasons || source.rejection_reasons);
  const typed = source.typed_targets && typeof source.typed_targets === 'object' ? source.typed_targets : {};
  const foundupState = typed.foundup_work_grounding && typeof typed.foundup_work_grounding === 'object'
    ? typed.foundup_work_grounding : null;
  const foundup = foundupState && foundupState.applied === true ? foundupState : null;
  const applied = explicit ? source.applied === true : source.grounding_preflight_applied === true;
  return {
    applied,
    passed: applied ? (explicit ? source.passed === true : source.grounding_preflight_passed === true) : true,
    rejection_reasons: reasons,
    repo_file_targets_count: number(source.repo_file_targets_count),
    semantic_targets_count: number(source.semantic_targets_count),
    semantic_targets_required: number(source.semantic_targets_required),
    semantic_targets_grounded: number(source.semantic_targets_grounded),
    semantic_targets_missing: strings(source.semantic_targets_missing),
    semantic_target_coverage_digest: source.semantic_target_coverage_digest || '',
    external_research_targets_count: number(source.external_research_targets_count),
    quoted_reference_blocks_count: number(source.quoted_reference_blocks_count),
    direct_read_required: source.direct_read_required === true || number(source.repo_file_targets_count) > 0,
    semantic_grounding_required: source.semantic_grounding_required === true || number(source.semantic_targets_count) > 0,
    external_research_required: source.external_research_required === true || number(source.external_research_targets_count) > 0,
    quoted_blocks_context_only: source.quoted_blocks_context_only === true || number(source.quoted_reference_blocks_count) > 0,
    registered_foundup_target_receipt: clone(foundup),
    registered_foundup_target_receipt_id: foundup && foundup.receipt_id || '',
    foundup_id: foundup && foundup.foundup_id || '',
    foundup_use_time_verified: source.foundup_use_time_verified === true,
    foundup_resolution: foundupState && foundupState.foundup_resolution || (foundup ? 'REGISTERED' : 'NOT_APPLICABLE'),
    foundup_requires_wsp109_resolution: !!foundupState && foundupState.requires_wsp109_resolution === true,
    safe_mutation_surfaces: foundup ? strings(foundup.safe_mutation_surfaces) : []
  };
}

function workOrderBinding(preflight, explicitReceipt, requestedPaths) {
  const observed = (preflight && preflight.typed_targets
    && preflight.typed_targets.foundup_work_grounding) || null;
  const unresolved = !!observed && observed.requires_wsp109_resolution === true;
  const receipt = observed && observed.applied === true ? observed : null;
  const explicitMatches = !explicitReceipt || !!receipt
    && JSON.stringify(explicitReceipt) === JSON.stringify(receipt);
  const targetValid = !unresolved && (!receipt ? !explicitReceipt : preflight.foundup_use_time_verified === true
    && grounding.receiptIntegrityValid(receipt) && explicitMatches);
  const safe = targetValid && receipt ? strings(receipt.safe_mutation_surfaces) : [];
  const requested = strings(requestedPaths);
  const scopeValid = targetValid && (!receipt || requested.every((item) => safe.includes(item)));
  return {
    receipt,
    targetValid,
    safe,
    scopeValid,
    allowed: unresolved ? [] : receipt || explicitReceipt ? (requested.length ? (scopeValid ? requested : []) : safe) : requested
  };
}

function selectionMatches(foundupId, receiptId, selection) {
  return !receiptId || !!selection && selection.foundup_id === foundupId
    && selection.registered_foundup_target_receipt_id === receiptId;
}

function targetSelectionRejections(receipt, selection) {
  const reasons = [];
  if (receipt && !grounding.receiptIntegrityValid(receipt)) reasons.push('registered_foundup_target_receipt_invalid');
  if (receipt && !selectionMatches(receipt.foundup_id, receipt.receipt_id, selection)) {
    reasons.push('registered_foundup_target_selection_mismatch');
  }
  return reasons;
}

function residentScope(groundingReceipt, requestedFoundupId) {
  const receipt = groundingReceipt && groundingReceipt.registered_foundup_target;
  const requested = String(requestedFoundupId || '').trim();
  const foundupId = receipt ? String(receipt.foundup_id || '').trim() : requested;
  return { foundupId, conflict: !!receipt && !!requested && requested !== foundupId };
}

module.exports = {
  applyGroundingMeta, applyTypedMeta, authorityContext, resolve, residentScope,
  preflightState, selectionMatches, targetSelectionRejections, verifyAtUse,
  wardrobePreflight, workOrderBinding
};
