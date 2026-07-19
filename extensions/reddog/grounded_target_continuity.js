'use strict';

const crypto = require('crypto');

const SCHEMA_VERSION = 'reddog_grounded_target_receipt.v1';

function asciiJsonString(value) {
  return JSON.stringify(value).replace(/[\u007f-\uffff]/g, (character) => {
    return '\\u' + character.charCodeAt(0).toString(16).padStart(4, '0');
  });
}

function canonicalJson(value) {
  if (Array.isArray(value)) {
    return '[' + value.map(canonicalJson).join(',') + ']';
  }
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map((key) => {
      return asciiJsonString(key) + ':' + canonicalJson(value[key]);
    }).join(',') + '}';
  }
  return typeof value === 'string' ? asciiJsonString(value) : JSON.stringify(value);
}

function canonicalDigest(value) {
  return 'sha256:' + crypto.createHash('sha256').update(canonicalJson(value), 'utf8').digest('hex');
}

function strings(value) {
  return Array.isArray(value)
    ? value.map((item) => String(item || '').trim()).filter(Boolean)
    : [];
}

function frozenTypedTargets(preflight) {
  const typed = preflight && preflight.typed_targets && typeof preflight.typed_targets === 'object'
    ? preflight.typed_targets
    : {};
  const quoted = Array.isArray(typed.quoted_reference_blocks) ? typed.quoted_reference_blocks : [];
  return {
    repo_file_targets: strings(typed.repo_file_targets),
    semantic_targets: strings(typed.semantic_targets),
    external_research_targets: strings(typed.external_research_targets),
    quoted_reference_blocks_count: quoted.length,
    quoted_reference_blocks_digest: canonicalDigest(quoted)
  };
}

function buildGroundedTargetReceipt(workFocus, groundingPreflight, holoScorecard, sourceSurface) {
  const preflight = groundingPreflight && typeof groundingPreflight === 'object' ? groundingPreflight : {};
  const scorecard = holoScorecard && typeof holoScorecard === 'object' ? holoScorecard : {};
  const typed = frozenTypedTargets(preflight);
  const coverage = Array.isArray(preflight.semantic_target_coverage)
    ? preflight.semantic_target_coverage.slice()
    : [];
  const payload = {
    schema_version: SCHEMA_VERSION,
    source_surface: String(sourceSurface || 'editor_thin_client'),
    work_focus_digest: canonicalDigest({ work_focus: String(workFocus || '') }),
    typed_targets: typed,
    typed_targets_digest: canonicalDigest(typed),
    grounding_preflight_applied: preflight.applied === true,
    grounding_preflight_passed: preflight.passed === true,
    grounding_preflight_rejection_reasons: strings(preflight.rejection_reasons),
    grounding_target_universe_required: preflight.grounding_target_universe_required === true,
    repo_file_targets_count: typed.repo_file_targets.length,
    semantic_targets_count: typed.semantic_targets.length,
    external_research_targets_count: typed.external_research_targets.length,
    quoted_reference_blocks_count: typed.quoted_reference_blocks_count,
    semantic_target_coverage: coverage,
    semantic_target_coverage_digest: canonicalDigest({ semantic_target_coverage: coverage }),
    target_recall_ok: scorecard.target_recall_ok === true ? true : (scorecard.target_recall_ok === false ? false : null),
    required_targets_missing: strings(scorecard.required_targets_missing),
    direct_read_paths: strings(scorecard.direct_read_paths),
    holoindex_owner_query_ok: scorecard.holoindex_owner_query_ok === true,
    holoindex_freshness: String(scorecard.holoindex_freshness || 'UNKNOWN'),
    holoindex_generation_id: String(scorecard.holoindex_generation_id || ''),
    holoindex_freshness_receipt_digest: String(scorecard.holoindex_freshness_receipt_digest || ''),
    holoindex_repo_head_sha: String(scorecard.holoindex_repo_head_sha || ''),
    holoindex_query_receipt_id: String(scorecard.holoindex_query_receipt_id || ''),
    holoindex_index_gap_detected: scorecard.index_gap_detected === true,
    no_holoindex_reindex_performed: scorecard.no_holoindex_reindex_performed === true
  };
  return Object.assign({}, payload, { receipt_id: canonicalDigest(payload) });
}

function receiptReady(receipt) {
  const value = receipt && typeof receipt === 'object' ? receipt : {};
  const typed = value.typed_targets && typeof value.typed_targets === 'object' ? value.typed_targets : {};
  const targetCount = strings(typed.repo_file_targets).length
    + strings(typed.semantic_targets).length
    + strings(typed.external_research_targets).length;
  return value.schema_version === SCHEMA_VERSION
    && value.grounding_preflight_applied === true
    && value.grounding_preflight_passed === true
    && (!value.grounding_target_universe_required || targetCount > 0)
    && value.receipt_id === canonicalDigest(Object.fromEntries(
      Object.entries(value).filter(([key]) => key !== 'receipt_id')
    ));
}

module.exports = {
  SCHEMA_VERSION,
  canonicalDigest,
  buildGroundedTargetReceipt,
  receiptReady
};
