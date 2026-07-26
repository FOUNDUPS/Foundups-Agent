'use strict';

const crypto = require('crypto');
const fs = require('fs');

const HOLOINDEX_SEMANTIC_BUCKETS = [
  'code_hits',
  'wsp_hits',
  'test_hits',
  'skill_hits',
  'symbol_hits',
  'docs_hits',
  'knowledge_hits',
  'work_ledger_hits'
];
const SEMANTIC_EVIDENCE_SCHEMA_VERSION = 'holoindex_semantic_evidence.v1';
const MAX_SEMANTIC_EVIDENCE_BYTES = 4 * 1024 * 1024;

function failureResult(error, query) {
  return {
    ok: false,
    source: 'holoindex_owner_service',
    freshness: 'UNKNOWN',
    raw_result: {},
    error: String(error || 'owner_query_bridge_error'),
    query: String(query || ''),
    index_gap_detected: true,
    stale_reasons: ['holoindex_owner_query_failed'],
    no_holoindex_reindex_performed: true
  };
}

function hasCurrentOwnerResult(value) {
  return value.ok === true
    && value.source === 'holoindex_owner_service'
    && value.freshness === 'CURRENT'
    && value.index_gap_detected === false
    && value.retrieval_mode === 'semantic'
    && Array.isArray(value.stale_reasons)
    && value.stale_reasons.length === 0
    && value.no_holoindex_reindex_performed === true
    && typeof value.freshness_generation_id === 'string'
    && value.freshness_generation_id.length > 0
    && typeof value.freshness_receipt_digest === 'string'
    && value.freshness_receipt_digest.length > 0
    && typeof value.repo_head_sha === 'string'
    && value.repo_head_sha.length > 0
    && /^sha256:[0-9a-f]{64}$/.test(String(value.repo_root_digest || ''))
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

function queryReceiptId(receipt) {
  const payload = Object.assign({}, receipt);
  delete payload.receipt_id;
  return 'sha256:' + crypto.createHash('sha256').update(canonicalJson(payload), 'utf8').digest('hex');
}

function semanticEvidenceDigest(value) {
  return 'sha256:' + crypto.createHash('sha256').update(String(value || ''), 'utf8').digest('hex');
}

function verifiedSemanticEvidence(value, receipt) {
  const serialized = value && typeof value.semantic_evidence_json === 'string'
    ? value.semantic_evidence_json
    : '';
  if (!serialized || Buffer.byteLength(serialized, 'utf8') > MAX_SEMANTIC_EVIDENCE_BYTES) {
    return null;
  }
  if (!/^sha256:[0-9a-f]{64}$/.test(String(receipt.semantic_evidence_digest || ''))
      || semanticEvidenceDigest(serialized) !== receipt.semantic_evidence_digest
      || !Number.isInteger(receipt.semantic_evidence_count)
      || receipt.semantic_evidence_count < 0) {
    return null;
  }
  try {
    const evidence = JSON.parse(serialized);
    if (!evidence || typeof evidence !== 'object' || Array.isArray(evidence)
        || evidence.schema_version !== SEMANTIC_EVIDENCE_SCHEMA_VERSION
        || !evidence.metadata || typeof evidence.metadata !== 'object'
        || Array.isArray(evidence.metadata)) {
      return null;
    }
    let count = 0;
    for (const bucket of HOLOINDEX_SEMANTIC_BUCKETS) {
      if (!Array.isArray(evidence[bucket])
          || evidence[bucket].some((item) => !item || typeof item !== 'object' || Array.isArray(item))) {
        return null;
      }
      count += evidence[bucket].length;
    }
    return count === receipt.semantic_evidence_count ? evidence : null;
  } catch (err) {
    return null;
  }
}

function receiptMatchesResult(receipt, value) {
  return receipt.schema_version === 'holoindex_query_receipt.v1'
    && receipt.source === 'holoindex_owner_service'
    && receipt.source_class === 'holoindex'
    && receipt.ok === true
    && typeof value.requested_query === 'string'
    && value.requested_query.length > 0
    && receipt.query === value.requested_query
    && value.query === value.requested_query
    && receipt.freshness === 'CURRENT'
    && receipt.index_gap_detected === false
    && receipt.no_holoindex_reindex_performed === true
    && receipt.freshness_generation_id === value.freshness_generation_id
    && receipt.freshness_receipt_digest === value.freshness_receipt_digest
    && receipt.repo_head_sha === value.repo_head_sha
    && receipt.repo_root_digest === value.repo_root_digest
    && receipt.workspace_repo_head_sha === value.workspace_repo_head_sha
    && receipt.authority_repo_head_sha === value.authority_repo_head_sha
    && receipt.authority_repo_root_digest === value.authority_repo_root_digest
    && receipt.workspace_overlay_present === value.workspace_overlay_present
    && receipt.semantic_evidence_authority === value.semantic_evidence_authority
    && receipt.no_authority_worktree_mutation_performed === true
    && verifiedSemanticEvidence(value, receipt) !== null
    && typeof receipt.receipt_id === 'string'
    && receipt.receipt_id === queryReceiptId(receipt);
}

function isAccepted(result) {
  const value = result && typeof result === 'object' ? result : {};
  const receipt = value.query_receipt && typeof value.query_receipt === 'object'
    ? value.query_receipt
    : {};
  return hasCurrentOwnerResult(value) && receiptMatchesResult(receipt, value);
}

function parseBridgeResult(stdout) {
  const lines = String(stdout || '').trim().split('\n');
  const result = JSON.parse(lines[lines.length - 1]);
  return result && typeof result === 'object'
    ? result
    : failureResult('owner_response_invalid');
}

function classifyOwnerBridgeError(err) {
  const value = err && typeof err === 'object' ? err : {};
  if (value.code === 'ETIMEDOUT') {
    return 'owner_query_timeout';
  }
  if (value instanceof SyntaxError) {
    return 'owner_response_invalid';
  }
  if (typeof value.status === 'number') {
    return 'owner_query_process_error';
  }
  return 'owner_query_bridge_error';
}

function runOwnerQuery(options) {
  const opts = options && typeof options === 'object' ? options : {};
  try {
    const script = opts.path.join(opts.root, 'scripts', 'reddog_holoindex_owner_query_once.py');
    const fsImpl = opts.fs && typeof opts.fs.existsSync === 'function' ? opts.fs : fs;
    if (!fsImpl.existsSync(script)) {
      return failureResult('owner_query_bridge_missing', opts.query);
    }
    const stdout = opts.cp.execFileSync(opts.interpreterPath, ['-B', script], {
      input: JSON.stringify({ query: String(opts.query || ''), limit: Number(opts.limit || 5) }),
      cwd: opts.root,
      env: opts.env,
      encoding: 'utf8',
      timeout: 90000,
      maxBuffer: 32 * 1024 * 1024,
      windowsHide: true
    });
    const result = parseBridgeResult(stdout);
    result.requested_query = String(opts.query || '');
    return result;
  } catch (err) {
    return failureResult(classifyOwnerBridgeError(err), opts.query);
  }
}

function parseBundle(bundleOutput) {
  try {
    const value = JSON.parse(String(bundleOutput || '{}'));
    return value && typeof value === 'object' ? value : null;
  } catch (err) {
    return null;
  }
}

function replaceSemanticBuckets(task, ownerResult) {
  const accepted = isAccepted(ownerResult);
  const receipt = ownerResult && ownerResult.query_receipt && typeof ownerResult.query_receipt === 'object'
    ? ownerResult.query_receipt
    : {};
  const evidence = accepted ? verifiedSemanticEvidence(ownerResult, receipt) : null;
  const raw = evidence || {};
  for (const bucket of HOLOINDEX_SEMANTIC_BUCKETS) {
    task[bucket] = accepted && Array.isArray(raw[bucket]) ? raw[bucket].slice() : [];
  }
  return { accepted, raw };
}

function appendDirectHits(task, directHits) {
  const seen = new Set(task.code_hits
    .filter((hit) => hit && hit.direct_read === true)
    .map((hit) => String((hit.location || hit.path) || '').toLowerCase()));
  for (const hit of directHits) {
    const identity = String(hit.location || hit.path || '').toLowerCase();
    if (identity && seen.has(identity)) {
      continue;
    }
    task.code_hits.push(hit);
    if (identity) {
      seen.add(identity);
    }
  }
}

function ownerMetadata(task, priorMeta, ownerResult, raw, accepted) {
  const rawMeta = raw.metadata && typeof raw.metadata === 'object' ? raw.metadata : {};
  const receipt = ownerResult && ownerResult.query_receipt && typeof ownerResult.query_receipt === 'object'
    ? ownerResult.query_receipt
    : {};
  return Object.assign({}, priorMeta, rawMeta, {
    code_count: task.code_hits.length,
    wsp_count: task.wsp_hits.length,
    test_count: task.test_hits.length,
    skill_count: task.skill_hits.length,
    symbol_count: task.symbol_hits.length,
    docs_count: task.docs_hits.length,
    knowledge_count: task.knowledge_hits.length,
    work_ledger_count: task.work_ledger_hits.length,
    owner_query_required: true,
    owner_query_ok: accepted,
    owner_query_error: String((ownerResult && ownerResult.error) || ''),
    owner_query_attempts: Number((ownerResult && ownerResult.owner_attempts) || 0),
    owner_query_retry_performed: ownerResult && ownerResult.owner_retry_performed === true,
    owner_query_retry_reason: String((ownerResult && ownerResult.owner_retry_reason) || ''),
    owner_query_source: String((ownerResult && ownerResult.source) || 'holoindex_owner_service'),
    freshness: String((ownerResult && ownerResult.freshness) || 'UNKNOWN'),
    freshness_generation_id: String((ownerResult && ownerResult.freshness_generation_id) || ''),
    freshness_receipt_digest: String((ownerResult && ownerResult.freshness_receipt_digest) || ''),
    repo_head_sha: String((ownerResult && ownerResult.repo_head_sha) || ''),
    repo_root_digest: String((ownerResult && ownerResult.repo_root_digest) || ''),
    authority_repo_root_digest: String((ownerResult && ownerResult.authority_repo_root_digest) || ''),
    workspace_overlay_present: ownerResult && ownerResult.workspace_overlay_present === true,
    semantic_evidence_authority: String((ownerResult && ownerResult.semantic_evidence_authority) || ''),
    no_authority_worktree_mutation_performed: ownerResult && ownerResult.no_authority_worktree_mutation_performed === true,
    query_receipt_id: String(receipt.receipt_id || ''),
    no_holoindex_reindex_performed: ownerResult && ownerResult.no_holoindex_reindex_performed === true
  });
}

function ownerQuerySummary(metadata, accepted) {
  return {
    accepted,
    freshness: metadata.freshness,
    generation_id: metadata.freshness_generation_id,
    freshness_receipt_digest: metadata.freshness_receipt_digest,
    repo_head_sha: metadata.repo_head_sha,
    repo_root_digest: metadata.repo_root_digest,
    authority_repo_root_digest: metadata.authority_repo_root_digest,
    workspace_overlay_present: metadata.workspace_overlay_present,
    semantic_evidence_authority: metadata.semantic_evidence_authority,
    no_authority_worktree_mutation_performed: metadata.no_authority_worktree_mutation_performed,
    query_receipt_id: metadata.query_receipt_id,
    error: metadata.owner_query_error,
    attempts: metadata.owner_query_attempts,
    retry_performed: metadata.owner_query_retry_performed,
    retry_reason: metadata.owner_query_retry_reason,
    no_holoindex_reindex_performed: metadata.no_holoindex_reindex_performed
  };
}

function mergeBundle(bundleOutput, ownerResult) {
  const data = parseBundle(bundleOutput);
  if (!data) {
    return String(bundleOutput || '');
  }
  const task = data.task_retrieval && typeof data.task_retrieval === 'object'
    ? Object.assign({}, data.task_retrieval)
    : {};
  const priorMeta = task.metadata && typeof task.metadata === 'object' ? task.metadata : {};
  const directHits = Array.isArray(task.code_hits)
    ? task.code_hits.filter((hit) => hit && hit.direct_read === true)
    : [];
  const replaced = replaceSemanticBuckets(task, ownerResult);
  appendDirectHits(task, directHits);
  task.metadata = ownerMetadata(task, priorMeta, ownerResult, replaced.raw, replaced.accepted);
  data.task_retrieval = task;
  data.holoindex_owner_query = ownerQuerySummary(task.metadata, replaced.accepted);
  return JSON.stringify(data);
}

function newMeta(usedOfflineFallback, emptyCoverageDigest) {
  return {
    holoindex_status: usedOfflineFallback ? 'offline_fallback' : 'unknown', requested_retrieval_mode: usedOfflineFallback ? 'semantic' : 'unknown',
    retrieval_mode: usedOfflineFallback ? 'lexical' : 'unknown', embedding_backend: usedOfflineFallback ? 'none' : 'unknown',
    holoindex_owner_query_required: false,
    holoindex_owner_query_ok: false,
    holoindex_owner_query_error: 'unknown',
    holoindex_owner_attempts: 0,
    holoindex_owner_retry_performed: false,
    holoindex_owner_retry_reason: '',
    holoindex_query_source: 'unknown',
    holoindex_freshness: 'UNKNOWN',
    holoindex_generation_id: '',
    holoindex_freshness_receipt_digest: '',
    holoindex_repo_head_sha: '',
    holoindex_repo_root_digest: '',
    holoindex_authority_repo_root_digest: '',
    holoindex_workspace_overlay_present: false,
    holoindex_semantic_evidence_authority: 'unknown',
    no_authority_worktree_mutation_performed: false,
    holoindex_query_receipt_id: '',
    no_holoindex_reindex_performed: true,
    routing_active: false,
    wsp_hits: 'unknown', code_hits: 'unknown', skill_hits: 'unknown',
    target_recall_ok: 'unknown', index_gap_detected: 'unknown',
    direct_read_fallback_used: false,
    required_targets_total: 0, required_targets_recalled: 0, required_targets_missing: [],
    work_focus_targets_derived: false, work_focus_target_derivation_sources: [],
    work_focus_targets_dropped_low_confidence: [], typed_target_extraction_applied: false,
    repo_file_targets_count: 0, semantic_targets_count: 0,
    semantic_targets_required: 0, semantic_targets_grounded: 0, semantic_targets_missing: [],
    semantic_target_coverage: [], semantic_target_coverage_digest: emptyCoverageDigest,
    semantic_evidence_hits: [], external_research_targets_count: 0,
    quoted_reference_blocks_count: 0, direct_read_paths: [], direct_read_rejected: [],
    direct_read_bytes: 0, direct_read_truncated: [], direct_read_fetch_attempted: false,
    direct_read_fetch_error: null, direct_read_fetch_arg_count: 0, direct_read_fetch_timeout_ms: 0
  };
}

function applyOwnerMetadata(meta, bundleMeta, usedOfflineFallback) {
  meta.holoindex_status = usedOfflineFallback ? 'offline_fallback' : 'bundle_json_ok';
  meta.retrieval_mode = usedOfflineFallback ? 'lexical' : String(bundleMeta.retrieval_mode || bundleMeta.mode || 'unknown');
  meta.embedding_backend = usedOfflineFallback ? 'none' : String(bundleMeta.embedding_backend || 'unknown');
  meta.holoindex_owner_query_required = bundleMeta.owner_query_required === true;
  meta.holoindex_owner_query_ok = bundleMeta.owner_query_ok === true;
  meta.holoindex_owner_query_error = String(bundleMeta.owner_query_error || '');
  meta.holoindex_owner_attempts = Number(bundleMeta.owner_query_attempts || 0);
  meta.holoindex_owner_retry_performed = bundleMeta.owner_query_retry_performed === true;
  meta.holoindex_owner_retry_reason = String(bundleMeta.owner_query_retry_reason || '');
  meta.holoindex_query_source = String(bundleMeta.owner_query_source || 'unknown');
  meta.holoindex_freshness = String(bundleMeta.freshness || 'UNKNOWN');
  meta.holoindex_generation_id = String(bundleMeta.freshness_generation_id || '');
  meta.holoindex_freshness_receipt_digest = String(bundleMeta.freshness_receipt_digest || '');
  meta.holoindex_repo_head_sha = String(bundleMeta.repo_head_sha || '');
  meta.holoindex_repo_root_digest = String(bundleMeta.repo_root_digest || '');
  meta.holoindex_authority_repo_root_digest = String(bundleMeta.authority_repo_root_digest || '');
  meta.holoindex_workspace_overlay_present = bundleMeta.workspace_overlay_present === true;
  meta.holoindex_semantic_evidence_authority = String(bundleMeta.semantic_evidence_authority || 'unknown');
  meta.no_authority_worktree_mutation_performed = bundleMeta.no_authority_worktree_mutation_performed === true;
  meta.holoindex_query_receipt_id = String(bundleMeta.query_receipt_id || '');
  meta.no_holoindex_reindex_performed = bundleMeta.no_holoindex_reindex_performed === true;
  meta.routing_active = usedOfflineFallback ? false : bundleMeta.routing_active === true;
  meta.wsp_hits = Number(bundleMeta.wsp_count || 0);
  meta.code_hits = Number(bundleMeta.code_count || 0);
  meta.skill_hits = bundleMeta.skill_count !== undefined ? Number(bundleMeta.skill_count) : 'unknown';
}

function applyRecallMetadata(meta, recall, data, dependencies) {
  meta.target_recall_ok = recall.target_recall_ok;
  meta.index_gap_detected = recall.index_gap_detected
    || (meta.holoindex_owner_query_required && meta.holoindex_owner_query_ok !== true);
  meta.recall_targets = recall.recall_targets;
  meta.required_targets_total = recall.required_targets_total;
  meta.required_targets_recalled = recall.required_targets_recalled;
  meta.required_targets_missing = recall.required_targets_missing;
  meta.work_focus_targets_derived = recall.work_focus_targets_derived === true;
  meta.work_focus_target_derivation_sources = Array.isArray(recall.work_focus_target_derivation_sources)
    ? recall.work_focus_target_derivation_sources : [];
  meta.work_focus_targets_dropped_low_confidence = Array.isArray(recall.work_focus_targets_dropped_low_confidence)
    ? recall.work_focus_targets_dropped_low_confidence : [];
  meta.typed_target_extraction_applied = recall.typed_target_extraction_applied === true;
  meta.repo_file_targets_count = Number(recall.repo_file_targets_count || 0);
  meta.semantic_targets_count = Number(recall.semantic_targets_count || 0);
  meta.semantic_evidence_hits = dependencies.semanticEvidenceHitsFromBundleData(data);
  meta.external_research_targets_count = Number(recall.external_research_targets_count || 0);
  meta.quoted_reference_blocks_count = Number(recall.quoted_reference_blocks_count || 0);
}

function applyDirectReadMetadata(meta, data, usedOfflineFallback) {
  const directRead = data.direct_read && typeof data.direct_read === 'object' ? data.direct_read : null;
  if (!directRead) {
    meta.direct_read_fallback_used = false;
    return;
  }
  meta.direct_read_paths = Array.isArray(directRead.direct_read_paths) ? directRead.direct_read_paths : [];
  meta.direct_read_rejected = Array.isArray(directRead.direct_read_rejected) ? directRead.direct_read_rejected : [];
  meta.direct_read_bytes = Number(directRead.direct_read_bytes || 0);
  meta.direct_read_truncated = Array.isArray(directRead.direct_read_truncated) ? directRead.direct_read_truncated : [];
  meta.direct_read_fallback_used = directRead.direct_read_fallback_used === true
    && meta.direct_read_paths.length > 0
    && meta.direct_read_bytes > 0;
}

function buildMetaFromBundle(output, usedOfflineFallback, taskText, dependencies) {
  const deps = dependencies && typeof dependencies === 'object' ? dependencies : {};
  const digest = typeof deps.semanticTargetCoverageDigest === 'function'
    ? deps.semanticTargetCoverageDigest([]) : '';
  const meta = newMeta(usedOfflineFallback, digest);
  try {
    const data = JSON.parse(String(output || '{}'));
    const bundleMeta = data.task_retrieval && data.task_retrieval.metadata ? data.task_retrieval.metadata : {};
    const recall = deps.evaluateTargetRecall(taskText, data);
    applyOwnerMetadata(meta, bundleMeta, usedOfflineFallback);
    applyRecallMetadata(meta, recall, data, deps);
    applyDirectReadMetadata(meta, data, usedOfflineFallback);
    if (meta.holoindex_owner_query_required && meta.holoindex_owner_query_ok !== true) {
      meta.holoindex_status = 'generation_bound_query_failed';
    }
  } catch (err) {
    meta.holoindex_status = usedOfflineFallback ? 'offline_fallback' : 'parse_error';
  }
  return meta;
}

function applyRejectedOwnerMeta(meta, ownerResult) {
  const value = ownerResult && typeof ownerResult === 'object' ? ownerResult : {};
  const receipt = value.query_receipt && typeof value.query_receipt === 'object' ? value.query_receipt : {};
  Object.assign(meta, {
    holoindex_status: 'generation_bound_query_failed',
    holoindex_owner_query_required: true,
    holoindex_owner_query_ok: false,
    holoindex_owner_query_error: String(value.error || 'unknown'),
    holoindex_owner_attempts: Number(value.owner_attempts || 0),
    holoindex_owner_retry_performed: value.owner_retry_performed === true,
    holoindex_owner_retry_reason: String(value.owner_retry_reason || ''),
    holoindex_query_source: String(value.source || 'holoindex_owner_service'),
    holoindex_freshness: String(value.freshness || 'UNKNOWN'),
    holoindex_generation_id: String(value.freshness_generation_id || ''),
    holoindex_freshness_receipt_digest: String(value.freshness_receipt_digest || ''),
    holoindex_repo_head_sha: String(value.repo_head_sha || ''),
    holoindex_repo_root_digest: String(value.repo_root_digest || ''),
    holoindex_authority_repo_root_digest: String(value.authority_repo_root_digest || ''),
    holoindex_workspace_overlay_present: value.workspace_overlay_present === true,
    holoindex_semantic_evidence_authority: String(value.semantic_evidence_authority || 'unknown'),
    no_authority_worktree_mutation_performed: value.no_authority_worktree_mutation_performed === true,
    holoindex_query_receipt_id: String(receipt.receipt_id || ''),
    no_holoindex_reindex_performed: value.no_holoindex_reindex_performed === true,
    index_gap_detected: true
  });
  return meta;
}

module.exports = {
  HOLOINDEX_SEMANTIC_BUCKETS,
  failureResult,
  queryReceiptId,
  semanticEvidenceDigest,
  verifiedSemanticEvidence,
  isAccepted,
  classifyOwnerBridgeError,
  runOwnerQuery,
  mergeBundle,
  buildMetaFromBundle,
  applyRejectedOwnerMeta
};
