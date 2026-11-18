'use strict';

const crypto = require('crypto');
const { createOwnerProof } = require('./holoindex_owner_proof');

const RECEIPT_FIELDS = Object.freeze([
  'selection_id', 'work_focus_digest', 'selected_wardrobe', 'wsp97_depth',
  'selected_context_mode', 'selected_model_mode', 'selected_effort',
  'execution_plane', 'wre_required', 'authority_boundary',
  'holoindex_query_digest', 'holoindex_freshness_label', 'index_gap_detected',
  'direct_read_required', 'grounding_preflight_applied',
  'grounding_preflight_passed', 'grounding_preflight_digest',
  'grounding_preflight_rejection_reasons', 'foundup_id',
  'registered_foundup_target_receipt_id', 'skillz_candidates', 'lane_refs',
  'rejection_reasons', 'no_execution_performed', 'no_enqueue_performed',
  'implementation_status'
]);
const PLANES = Object.freeze({
  wsp97_solo_retrieval: 'advisory_only',
  wsp97_architect_audit: 'audit_only',
  wsp97_implementation_slice: 'worker_draft_pr',
  wsp97_sovereign_execution: 'governed_execution_candidate'
});
const AUTHORITIES = Object.freeze({
  wsp97_solo_retrieval: Object.freeze(['no_authority']),
  wsp97_architect_audit: Object.freeze(['no_authority']),
  wsp97_implementation_slice: Object.freeze(['draft_pr_only']),
  wsp97_sovereign_execution: Object.freeze(['signed_valve_required', 'sovereign_token_required'])
});

function canonicalJson(value) {
  if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort()
    .map((key) => JSON.stringify(key) + ':' + canonicalJson(value[key])).join(',') + '}';
  return JSON.stringify(value);
}

function shapeAccepted(result) {
  const receipt = result && result.receipt;
  const strings = receipt && ['work_focus_digest', 'wsp97_depth', 'selected_context_mode',
    'selected_model_mode', 'selected_effort', 'holoindex_query_digest',
    'holoindex_freshness_label', 'foundup_id', 'implementation_status'];
  return Boolean(result && result.decision === 'WARDROBE_SELECTION_ACCEPT' && receipt
    && Object.keys(receipt).sort().join('|') === RECEIPT_FIELDS.slice().sort().join('|')
    && /^[a-f0-9]{64}$/.test(receipt.selection_id)
    && strings.every((key) => typeof receipt[key] === 'string')
    && ['work_focus_digest', 'holoindex_query_digest', 'grounding_preflight_digest']
      .every((key) => /^[a-f0-9]{64}$/.test(receipt[key]))
    && ['wsp97_depth', 'selected_context_mode', 'selected_model_mode', 'selected_effort']
      .every((key) => receipt[key].length > 0)
    && PLANES[receipt.selected_wardrobe] === receipt.execution_plane
    && AUTHORITIES[receipt.selected_wardrobe].includes(receipt.authority_boundary)
    && receipt.implementation_status === 'SPECIFIED_NOT_IMPLEMENTED'
    && ['wre_required', 'index_gap_detected', 'direct_read_required', 'grounding_preflight_applied',
      'grounding_preflight_passed', 'no_execution_performed', 'no_enqueue_performed']
      .every((key) => typeof receipt[key] === 'boolean')
    && ['grounding_preflight_rejection_reasons', 'skillz_candidates', 'lane_refs', 'rejection_reasons']
      .every((key) => Array.isArray(receipt[key]))
    && receipt.rejection_reasons.length === 0
    && receipt.grounding_preflight_rejection_reasons.length === 0
    && (!receipt.grounding_preflight_applied || receipt.grounding_preflight_passed)
    && receipt.no_execution_performed && receipt.no_enqueue_performed
    && result.no_execution_performed === true && result.no_enqueue_performed === true
    && (!Object.prototype.hasOwnProperty.call(result, 'rejection_reasons')
      || (Array.isArray(result.rejection_reasons) && result.rejection_reasons.length === 0)));
}

function digestPayload(payload, result) {
  const receipt = result.receipt;
  const value = {};
  RECEIPT_FIELDS.filter((key) => key !== 'selection_id')
    .forEach((key) => { value[key] = receipt[key]; });
  value.principal_ref = String(payload.principal_ref || 'unknown');
  value.authority_request = String(result.authority_request || 'none');
  value.wsp_refs = Array.isArray(result.governing_wsps) ? result.governing_wsps : [];
  value.continuation_packet_digest = String(payload.continuation_packet_digest || '');
  return value;
}

function createWardrobeSelectionProof(originAccepted) {
  const sourceAccepted = typeof originAccepted === 'function'
    ? originAccepted : () => false;
  const proof = createOwnerProof(shapeAccepted);
  return Object.freeze({
    verifyAndObserve(payload, result) {
      if (!sourceAccepted(result) || !shapeAccepted(result)) return result;
      const expected = crypto.createHash('sha256')
        .update(canonicalJson(digestPayload(payload, result)), 'utf8').digest('hex');
      return expected === result.receipt.selection_id ? proof.observe(result) : result;
    },
    isAccepted(result) { return proof.isAccepted(result); },
    rejection(result, required, build, decision) {
      if (!required || proof.isAccepted(result)) return null;
      return build(decision, {
        rejection_reasons: ['selection_proof_missing'],
        not_invoked_reason: 'selection_proof_missing'
      });
    }
  });
}

module.exports = { createWardrobeSelectionProof };
