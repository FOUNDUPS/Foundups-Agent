'use strict';

const ownerFallback = require('./holoindex_owner_fallback_bundle');

function parseBundle(bundleOutput) {
  try {
    const value = JSON.parse(String(bundleOutput || '{}'));
    return value && typeof value === 'object' ? value : null;
  } catch (_err) {
    return null;
  }
}

function replaceSemanticBuckets(task, ownerResult, deps) {
  const accepted = deps.isAccepted(ownerResult);
  const receipt = ownerResult && ownerResult.query_receipt
    && typeof ownerResult.query_receipt === 'object' ? ownerResult.query_receipt : {};
  const evidence = accepted ? deps.verifiedSemanticEvidence(ownerResult, receipt) : null;
  const raw = evidence || {};
  for (const bucket of deps.semanticBuckets) {
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
    if (identity && seen.has(identity)) continue;
    task.code_hits.push(hit);
    if (identity) seen.add(identity);
  }
}

function bucketCounts(task) {
  return {
    code_count: task.code_hits.length, wsp_count: task.wsp_hits.length,
    test_count: task.test_hits.length, skill_count: task.skill_hits.length,
    symbol_count: task.symbol_hits.length, docs_count: task.docs_hits.length,
    knowledge_count: task.knowledge_hits.length,
    work_ledger_count: task.work_ledger_hits.length
  };
}

function acceptedOwnerMetadata(task, priorMeta, ownerResult, raw) {
  const rawMeta = raw.metadata && typeof raw.metadata === 'object' ? raw.metadata : {};
  const receipt = ownerResult && ownerResult.query_receipt
    && typeof ownerResult.query_receipt === 'object' ? ownerResult.query_receipt : {};
  return Object.assign({}, priorMeta, rawMeta, bucketCounts(task), {
    owner_query_required: true, owner_query_ok: true,
    owner_query_error: String(ownerResult.error || ''),
    owner_query_attempts: Number(ownerResult.owner_attempts || 0),
    owner_query_retry_performed: ownerResult.owner_retry_performed === true,
    owner_query_retry_reason: String(ownerResult.owner_retry_reason || ''),
    owner_query_source: String(ownerResult.source || 'holoindex_owner_service'),
    freshness: String(ownerResult.freshness || 'UNKNOWN'),
    freshness_generation_id: String(ownerResult.freshness_generation_id || ''),
    freshness_receipt_digest: String(ownerResult.freshness_receipt_digest || ''),
    repo_head_sha: String(ownerResult.repo_head_sha || ''),
    repo_root_digest: String(ownerResult.repo_root_digest || ''),
    authority_repo_root_digest: String(ownerResult.authority_repo_root_digest || ''),
    workspace_overlay_present: ownerResult.workspace_overlay_present === true,
    semantic_evidence_authority: String(ownerResult.semantic_evidence_authority || ''),
    no_authority_worktree_mutation_performed:
      ownerResult.no_authority_worktree_mutation_performed === true,
    query_receipt_id: String(receipt.receipt_id || ''),
    no_holoindex_reindex_performed: ownerResult.no_holoindex_reindex_performed === true
  });
}

function ownerMetadata(task, priorMeta, ownerResult, raw, accepted, deps) {
  if (accepted) return acceptedOwnerMetadata(task, priorMeta, ownerResult, raw);
  const observed = deps.isObserved(ownerResult) ? ownerResult : {};
  return Object.assign({}, priorMeta, ownerFallback.rejectedOwnerMetadata(observed),
    bucketCounts(task));
}

function ownerQuerySummary(metadata, accepted) {
  return {
    accepted, freshness: metadata.freshness,
    generation_id: metadata.freshness_generation_id,
    freshness_receipt_digest: metadata.freshness_receipt_digest,
    repo_head_sha: metadata.repo_head_sha,
    repo_root_digest: metadata.repo_root_digest,
    authority_repo_root_digest: metadata.authority_repo_root_digest,
    workspace_overlay_present: metadata.workspace_overlay_present,
    semantic_evidence_authority: metadata.semantic_evidence_authority,
    no_authority_worktree_mutation_performed: metadata.no_authority_worktree_mutation_performed,
    query_receipt_id: metadata.query_receipt_id, error: metadata.owner_query_error,
    attempts: metadata.owner_query_attempts,
    retry_performed: metadata.owner_query_retry_performed,
    retry_reason: metadata.owner_query_retry_reason,
    no_holoindex_reindex_performed: metadata.no_holoindex_reindex_performed
  };
}

function mergeBundle(bundleOutput, ownerResult, deps) {
  const data = parseBundle(bundleOutput) || ownerFallback.buildOwnerFallbackBundle();
  const task = data.task_retrieval && typeof data.task_retrieval === 'object'
    ? Object.assign({}, data.task_retrieval) : {};
  const priorMeta = task.metadata && typeof task.metadata === 'object' ? task.metadata : {};
  const directHits = Array.isArray(task.code_hits)
    ? task.code_hits.filter((hit) => hit && hit.direct_read === true) : [];
  const replaced = replaceSemanticBuckets(task, ownerResult, deps);
  appendDirectHits(task, directHits);
  task.metadata = ownerMetadata(task, priorMeta, ownerResult,
    replaced.raw, replaced.accepted, deps);
  data.task_retrieval = task;
  data.holoindex_owner_query = ownerQuerySummary(task.metadata, replaced.accepted);
  return JSON.stringify(data);
}

function newOwnerMeta(usedOfflineFallback) {
  return {
    holoindex_status: usedOfflineFallback ? 'offline_fallback' : 'unknown',
    requested_retrieval_mode: usedOfflineFallback ? 'semantic' : 'unknown',
    retrieval_mode: usedOfflineFallback ? 'lexical' : 'unknown',
    embedding_backend: usedOfflineFallback ? 'none' : 'unknown',
    holoindex_owner_query_required: false, holoindex_owner_query_ok: false,
    holoindex_owner_query_error: 'unknown', holoindex_owner_attempts: 0,
    holoindex_owner_retry_performed: false, holoindex_owner_retry_reason: '',
    holoindex_query_source: 'unknown', holoindex_freshness: 'UNKNOWN',
    holoindex_generation_id: '', holoindex_freshness_receipt_digest: '',
    holoindex_repo_head_sha: '', holoindex_repo_root_digest: '',
    holoindex_authority_repo_root_digest: '', holoindex_workspace_overlay_present: false,
    holoindex_semantic_evidence_authority: 'unknown',
    no_authority_worktree_mutation_performed: false,
    holoindex_query_receipt_id: '', no_holoindex_reindex_performed: true
  };
}

function newIncidentMeta() {
  return {
    incident_repair_attempted: false, incident_repair_accepted: false,
    incident_repair_status: '', incident_repair_id: '', incident_repair_task_id: '',
    incident_repair_receipt_id: '', incident_repair_enqueued: false,
    incident_repair_owner_requery_performed: false,
    incident_repair_coding_candidate_required: false,
    incident_repair_rejection_reasons: []
  };
}

function newRecallMeta(emptyCoverageDigest) {
  return {
    routing_active: false, wsp_hits: 'unknown', code_hits: 'unknown', skill_hits: 'unknown',
    target_recall_ok: 'unknown', index_gap_detected: 'unknown',
    required_targets_total: 0, required_targets_recalled: 0, required_targets_missing: [],
    work_focus_targets_derived: false, work_focus_target_derivation_sources: [],
    work_focus_targets_dropped_low_confidence: [], typed_target_extraction_applied: false,
    repo_file_targets_count: 0, semantic_targets_count: 0,
    semantic_targets_required: 0, semantic_targets_grounded: 0,
    semantic_targets_missing: [], semantic_target_coverage: [],
    semantic_target_coverage_digest: emptyCoverageDigest,
    semantic_evidence_hits: [], external_research_targets_count: 0,
    quoted_reference_blocks_count: 0
  };
}

function newDirectReadMeta() {
  return {
    direct_read_fallback_used: false, direct_read_paths: [], direct_read_rejected: [],
    direct_read_bytes: 0, direct_read_truncated: [], direct_read_fetch_attempted: false,
    direct_read_fetch_error: null, direct_read_fetch_arg_count: 0,
    direct_read_fetch_timeout_ms: 0
  };
}

function newMeta(usedOfflineFallback, emptyCoverageDigest) {
  return Object.assign({}, newOwnerMeta(usedOfflineFallback), newIncidentMeta(),
    newRecallMeta(emptyCoverageDigest), newDirectReadMeta());
}

function applyOwnerIdentity(meta, bundleMeta) {
  meta.holoindex_freshness = String(bundleMeta.freshness || 'UNKNOWN');
  meta.holoindex_generation_id = String(bundleMeta.freshness_generation_id || '');
  meta.holoindex_freshness_receipt_digest = String(bundleMeta.freshness_receipt_digest || '');
  meta.holoindex_repo_head_sha = String(bundleMeta.repo_head_sha || '');
  meta.holoindex_repo_root_digest = String(bundleMeta.repo_root_digest || '');
  meta.holoindex_authority_repo_root_digest = String(bundleMeta.authority_repo_root_digest || '');
  meta.holoindex_workspace_overlay_present = bundleMeta.workspace_overlay_present === true;
  meta.holoindex_semantic_evidence_authority = String(
    bundleMeta.semantic_evidence_authority || 'unknown'
  );
  meta.no_authority_worktree_mutation_performed =
    bundleMeta.no_authority_worktree_mutation_performed === true;
  meta.holoindex_query_receipt_id = String(bundleMeta.query_receipt_id || '');
  meta.no_holoindex_reindex_performed = bundleMeta.no_holoindex_reindex_performed === true;
}

function applyOwnerMetadata(meta, bundleMeta, usedOfflineFallback) {
  meta.holoindex_status = usedOfflineFallback ? 'offline_fallback' : 'bundle_json_ok';
  meta.retrieval_mode = usedOfflineFallback ? 'lexical'
    : String(bundleMeta.retrieval_mode || bundleMeta.mode || 'unknown');
  meta.embedding_backend = usedOfflineFallback ? 'none'
    : String(bundleMeta.embedding_backend || 'unknown');
  meta.holoindex_owner_query_required = bundleMeta.owner_query_required === true;
  meta.holoindex_owner_query_ok = bundleMeta.owner_query_ok === true;
  meta.holoindex_owner_query_error = String(bundleMeta.owner_query_error || '');
  meta.holoindex_owner_attempts = Number(bundleMeta.owner_query_attempts || 0);
  meta.holoindex_owner_retry_performed = bundleMeta.owner_query_retry_performed === true;
  meta.holoindex_owner_retry_reason = String(bundleMeta.owner_query_retry_reason || '');
  meta.holoindex_query_source = String(bundleMeta.owner_query_source || 'unknown');
  applyOwnerIdentity(meta, bundleMeta);
  meta.routing_active = usedOfflineFallback ? false : bundleMeta.routing_active === true;
  meta.wsp_hits = Number(bundleMeta.wsp_count || 0);
  meta.code_hits = Number(bundleMeta.code_count || 0);
  meta.skill_hits = bundleMeta.skill_count === undefined
    ? 'unknown' : Number(bundleMeta.skill_count);
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
  meta.work_focus_target_derivation_sources = Array.isArray(
    recall.work_focus_target_derivation_sources
  ) ? recall.work_focus_target_derivation_sources : [];
  meta.work_focus_targets_dropped_low_confidence = Array.isArray(
    recall.work_focus_targets_dropped_low_confidence
  ) ? recall.work_focus_targets_dropped_low_confidence : [];
  meta.typed_target_extraction_applied = recall.typed_target_extraction_applied === true;
  meta.repo_file_targets_count = Number(recall.repo_file_targets_count || 0);
  meta.semantic_targets_count = Number(recall.semantic_targets_count || 0);
  meta.semantic_evidence_hits = dependencies.semanticEvidenceHitsFromBundleData(data);
  meta.external_research_targets_count = Number(recall.external_research_targets_count || 0);
  meta.quoted_reference_blocks_count = Number(recall.quoted_reference_blocks_count || 0);
}

function applyDirectReadMetadata(meta, data) {
  const value = data.direct_read && typeof data.direct_read === 'object'
    ? data.direct_read : null;
  if (!value) { meta.direct_read_fallback_used = false; return; }
  meta.direct_read_paths = Array.isArray(value.direct_read_paths) ? value.direct_read_paths : [];
  meta.direct_read_rejected = Array.isArray(value.direct_read_rejected)
    ? value.direct_read_rejected : [];
  meta.direct_read_bytes = Number(value.direct_read_bytes || 0);
  meta.direct_read_truncated = Array.isArray(value.direct_read_truncated)
    ? value.direct_read_truncated : [];
  meta.direct_read_fallback_used = value.direct_read_fallback_used === true
    && meta.direct_read_paths.length > 0 && meta.direct_read_bytes > 0;
  meta.direct_read_fetch_attempted = meta.direct_read_paths.length > 0
    && meta.direct_read_bytes > 0;
}

function buildMetaFromBundle(output, usedOfflineFallback, taskText, dependencies) {
  const deps = dependencies && typeof dependencies === 'object' ? dependencies : {};
  const digest = typeof deps.semanticTargetCoverageDigest === 'function'
    ? deps.semanticTargetCoverageDigest([]) : '';
  const meta = newMeta(usedOfflineFallback, digest);
  try {
    const data = JSON.parse(String(output || '{}'));
    const bundleMeta = data.task_retrieval && data.task_retrieval.metadata
      ? data.task_retrieval.metadata : {};
    const recall = deps.evaluateTargetRecall(taskText, data);
    applyOwnerMetadata(meta, bundleMeta, usedOfflineFallback);
    applyRecallMetadata(meta, recall, data, deps);
    applyDirectReadMetadata(meta, data);
    if (meta.holoindex_owner_query_required && meta.holoindex_owner_query_ok !== true) {
      meta.holoindex_status = 'generation_bound_query_failed';
    }
  } catch (_err) {
    meta.holoindex_status = usedOfflineFallback ? 'offline_fallback' : 'parse_error';
  }
  return meta;
}

function applyRejectedOwnerIdentity(meta, safe) {
  meta.holoindex_freshness = safe.freshness;
  meta.holoindex_generation_id = safe.freshness_generation_id;
  meta.holoindex_freshness_receipt_digest = safe.freshness_receipt_digest;
  meta.holoindex_repo_head_sha = safe.repo_head_sha;
  meta.holoindex_repo_root_digest = safe.repo_root_digest;
  meta.holoindex_authority_repo_root_digest = safe.authority_repo_root_digest;
  meta.holoindex_workspace_overlay_present = safe.workspace_overlay_present;
  meta.holoindex_semantic_evidence_authority = safe.semantic_evidence_authority;
  meta.no_authority_worktree_mutation_performed = safe.no_authority_worktree_mutation_performed;
  meta.holoindex_query_receipt_id = safe.query_receipt_id;
  meta.no_holoindex_reindex_performed = safe.no_holoindex_reindex_performed;
}

function applyRejectedOwnerMeta(meta, ownerResult, deps) {
  const observed = deps.isObserved(ownerResult) ? ownerResult : {};
  const safe = ownerFallback.rejectedOwnerMetadata(observed);
  Object.assign(meta, {
    holoindex_status: 'generation_bound_query_failed',
    holoindex_owner_query_required: true, holoindex_owner_query_ok: false,
    holoindex_owner_query_error: safe.owner_query_error,
    holoindex_owner_attempts: safe.owner_query_attempts,
    holoindex_owner_retry_performed: safe.owner_query_retry_performed,
    holoindex_owner_retry_reason: safe.owner_query_retry_reason,
    holoindex_query_source: safe.owner_query_source, index_gap_detected: true
  });
  applyRejectedOwnerIdentity(meta, safe);
  return meta;
}

function createBundleProjection(dependencies) {
  const deps = Object.freeze(Object.assign({}, dependencies));
  return Object.freeze({
    applyRejectedOwnerMeta: (meta, result) => applyRejectedOwnerMeta(meta, result, deps),
    buildMetaFromBundle,
    mergeBundle: (output, result) => mergeBundle(output, result, deps)
  });
}

module.exports = Object.freeze({ createBundleProjection });
