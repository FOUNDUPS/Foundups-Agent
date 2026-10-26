'use strict';

const crypto = require('crypto');
const ownerFallback = require('./holoindex_owner_fallback_bundle');
const { createOwnerProof } = require('./holoindex_owner_proof');
const { createOwnerRuntime } = require('./holoindex_owner_runtime');
const { createBundleProjection } = require('./holoindex_bundle_projection');

const OWNER_QUERY_SCRIPT = 'reddog_holoindex_owner_query_once.py';
const HOLOINDEX_SEMANTIC_BUCKETS = [
  'code_hits', 'wsp_hits', 'test_hits', 'skill_hits', 'symbol_hits',
  'docs_hits', 'knowledge_hits', 'work_ledger_hits'
];
const SEMANTIC_EVIDENCE_SCHEMA_VERSION = 'holoindex_semantic_evidence.v1';
const MAX_SEMANTIC_EVIDENCE_BYTES = 4 * 1024 * 1024;

function failureResult(error, query) {
  return {
    ok: false, source: 'holoindex_owner_service', freshness: 'UNKNOWN', raw_result: {},
    error: String(error || 'owner_query_bridge_error'), query: String(query || ''),
    index_gap_detected: true, stale_reasons: ['holoindex_owner_query_failed'],
    no_holoindex_reindex_performed: true
  };
}

function hasCurrentOwnerResult(value) {
  return value.ok === true && value.source === 'holoindex_owner_service'
    && value.freshness === 'CURRENT' && value.index_gap_detected === false
    && value.retrieval_mode === 'semantic' && Array.isArray(value.stale_reasons)
    && value.stale_reasons.length === 0 && value.no_holoindex_reindex_performed === true
    && typeof value.freshness_generation_id === 'string'
    && value.freshness_generation_id.length > 0
    && typeof value.freshness_receipt_digest === 'string'
    && value.freshness_receipt_digest.length > 0
    && typeof value.repo_head_sha === 'string' && value.repo_head_sha.length > 0
    && /^sha256:[0-9a-f]{64}$/.test(String(value.repo_root_digest || ''))
    && /^sha256:[0-9a-f]{64}$/.test(String(value.retrieval_runtime_ranker_digest || ''))
    && /^sha256:[0-9a-f]{64}$/.test(String(value.runtime_environment_digest || ''))
    && typeof value.runtime_environment_exact_closure_verified === 'boolean'
    && value.authority_repo_root_digest === value.repo_root_digest
    && value.workspace_repo_head_sha === value.repo_head_sha
    && value.authority_repo_head_sha === value.repo_head_sha
    && typeof value.workspace_overlay_present === 'boolean'
    && ['clean_workspace_head', 'committed_head_only'].includes(value.semantic_evidence_authority)
    && value.no_authority_worktree_mutation_performed === true;
}

function asciiJsonString(value) {
  return JSON.stringify(value).replace(/[\u007f-\uffff]/g, (character) => {
    return '\\u' + character.charCodeAt(0).toString(16).padStart(4, '0');
  });
}

function canonicalJson(value) {
  if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map((key) => {
      return asciiJsonString(key) + ':' + canonicalJson(value[key]);
    }).join(',') + '}';
  }
  return typeof value === 'string' ? asciiJsonString(value) : JSON.stringify(value);
}

function queryReceiptId(receipt) {
  const payload = Object.assign({}, receipt);
  delete payload.receipt_id;
  return 'sha256:' + crypto.createHash('sha256')
    .update(canonicalJson(payload), 'utf8').digest('hex');
}

function semanticEvidenceDigest(value) {
  return 'sha256:' + crypto.createHash('sha256')
    .update(String(value || ''), 'utf8').digest('hex');
}

function semanticEvidenceShape(evidence) {
  return evidence && typeof evidence === 'object' && !Array.isArray(evidence)
    && evidence.schema_version === SEMANTIC_EVIDENCE_SCHEMA_VERSION
    && evidence.metadata && typeof evidence.metadata === 'object'
    && !Array.isArray(evidence.metadata);
}

function semanticEvidenceCount(evidence) {
  let count = 0;
  for (const bucket of HOLOINDEX_SEMANTIC_BUCKETS) {
    if (!Array.isArray(evidence[bucket]) || evidence[bucket].some((item) => {
      return !item || typeof item !== 'object' || Array.isArray(item);
    })) return -1;
    count += evidence[bucket].length;
  }
  return count;
}

function verifiedSemanticEvidence(value, receipt) {
  const serialized = value && typeof value.semantic_evidence_json === 'string'
    ? value.semantic_evidence_json : '';
  if (!serialized || Buffer.byteLength(serialized, 'utf8') > MAX_SEMANTIC_EVIDENCE_BYTES
      || !/^sha256:[0-9a-f]{64}$/.test(String(receipt.semantic_evidence_digest || ''))
      || semanticEvidenceDigest(serialized) !== receipt.semantic_evidence_digest
      || !Number.isInteger(receipt.semantic_evidence_count)
      || receipt.semantic_evidence_count < 0) return null;
  try {
    const evidence = JSON.parse(serialized);
    if (!semanticEvidenceShape(evidence)) return null;
    return semanticEvidenceCount(evidence) === receipt.semantic_evidence_count ? evidence : null;
  } catch (_err) { return null; }
}

function receiptIdentityMatches(receipt, value) {
  return receipt.freshness_generation_id === value.freshness_generation_id
    && receipt.freshness_receipt_digest === value.freshness_receipt_digest
    && receipt.repo_head_sha === value.repo_head_sha
    && receipt.repo_root_digest === value.repo_root_digest
    && receipt.workspace_repo_head_sha === value.workspace_repo_head_sha
    && receipt.authority_repo_head_sha === value.authority_repo_head_sha
    && receipt.authority_repo_root_digest === value.authority_repo_root_digest
    && receipt.workspace_overlay_present === value.workspace_overlay_present
    && receipt.semantic_evidence_authority === value.semantic_evidence_authority
    && receipt.retrieval_runtime_ranker_digest === value.retrieval_runtime_ranker_digest
    && receipt.runtime_environment_digest === value.runtime_environment_digest
    && receipt.runtime_environment_exact_closure_verified
      === value.runtime_environment_exact_closure_verified;
}

function receiptMatchesResult(receipt, value) {
  return receipt.schema_version === 'holoindex_query_receipt.v1'
    && receipt.source === 'holoindex_owner_service' && receipt.source_class === 'holoindex'
    && receipt.ok === true && typeof value.requested_query === 'string'
    && value.requested_query.length > 0 && receipt.query === value.requested_query
    && value.query === value.requested_query && receipt.freshness === 'CURRENT'
    && receipt.index_gap_detected === false && receipt.no_holoindex_reindex_performed === true
    && receiptIdentityMatches(receipt, value)
    && receipt.no_authority_worktree_mutation_performed === true
    && verifiedSemanticEvidence(value, receipt) !== null
    && typeof receipt.receipt_id === 'string'
    && receipt.receipt_id === queryReceiptId(receipt);
}

function ownerResultMatchesReceipt(result) {
  const value = result && typeof result === 'object' ? result : {};
  const receipt = value.query_receipt && typeof value.query_receipt === 'object'
    ? value.query_receipt : {};
  return hasCurrentOwnerResult(value) && receiptMatchesResult(receipt, value);
}

const OWNER_PROOF = createOwnerProof(ownerResultMatchesReceipt);
const RUNTIME = createOwnerRuntime({
  failureResult, observe: OWNER_PROOF.observe, scriptName: OWNER_QUERY_SCRIPT
});
const PROJECTION = createBundleProjection({
  isAccepted: OWNER_PROOF.isAccepted,
  isObserved: OWNER_PROOF.isObserved,
  semanticBuckets: HOLOINDEX_SEMANTIC_BUCKETS,
  verifiedSemanticEvidence
});

function applyInterpreterMeta(meta, result) {
  const proof = result && result.interpreter_provenance
    && typeof result.interpreter_provenance === 'object'
    ? result.interpreter_provenance : {};
  meta.holoindex_interpreter_source = String(
    proof.source || (result && result.interpreter_source) || 'unknown'
  );
  meta.holoindex_interpreter_provenance = Object.assign({}, proof);
  meta.holoindex_interpreter_path_digest = String(
    proof.canonical_path_digest || (result && result.interpreter_path_digest) || ''
  );
  return meta;
}

function cancelledOutput(taskText, lifecycle, buildMeta) {
  const meta = buildMeta('', false, taskText);
  Object.assign(meta, { holoindex_status: 'request_cancelled', request_cancelled: true,
    cancellation_reason: lifecycle ? lifecycle.reason() : 'request_cancelled' });
  return { output: '', quality: 'HoloIndex request cancelled.', meta,
    direct_read_section: null, repo_deep_dive_targets: [] };
}

module.exports = Object.freeze({
  HOLOINDEX_SEMANTIC_BUCKETS,
  failureResult,
  queryReceiptId,
  semanticEvidenceDigest,
  verifiedSemanticEvidence,
  isAccepted: OWNER_PROOF.isAccepted,
  isObserved: OWNER_PROOF.isObserved,
  classifyOwnerBridgeError: RUNTIME.classifyOwnerBridgeError,
  resolveInterpreter: RUNTIME.resolveInterpreter,
  applyInterpreterMeta,
  buildOwnedContext: RUNTIME.buildOwnedContext,
  cancelledOutput,
  createProcessLifecycleRegistry: RUNTIME.createProcessLifecycleRegistry,
  runOwnerQuery: RUNTIME.runOwnerQuery,
  runOwnerQueryAsync: RUNTIME.runOwnerQueryAsync,
  resolveInterpreterAsync: RUNTIME.resolveInterpreterAsync,
  mergeBundle: PROJECTION.mergeBundle,
  buildMetaFromBundle: PROJECTION.buildMetaFromBundle,
  applyRejectedOwnerMeta: PROJECTION.applyRejectedOwnerMeta,
  ownerFallback
});
