'use strict';

const SAFE_TOKEN = /^[A-Za-z0-9_:-]{1,96}$/;

function safeToken(value, fallback) {
  const token = String(value || '');
  return SAFE_TOKEN.test(token) ? token : fallback;
}

function buildOwnerFallbackBundle() {
  return {
    schema_version: 'holoindex_owner_fallback_bundle.v1',
    structured_memory: {
      coverage_state: 'unavailable',
      missing_required: null
    },
    task_retrieval: {
      metadata: {
        structured_bundle_fallback: true,
        structured_bundle_fallback_reason: 'legacy_bundle_non_json'
      }
    },
    direct_read: {
      direct_read_fallback_used: false,
      direct_read_paths: [],
      direct_read_rejected: [],
      direct_read_bytes: 0,
      direct_read_truncated: []
    }
  };
}

function rejectedOwnerMetadata(value) {
  const source = value && typeof value === 'object' ? value : {};
  const attempts = Number.isInteger(source.owner_attempts)
    ? Math.max(0, Math.min(source.owner_attempts, 2))
    : 0;
  return {
    owner_query_required: true,
    owner_query_ok: false,
    owner_query_error: safeToken(source.error, 'owner_query_rejected'),
    owner_query_attempts: attempts,
    owner_query_retry_performed: source.owner_retry_performed === true,
    owner_query_retry_reason: safeToken(source.owner_retry_reason, ''),
    owner_query_source: 'holoindex_owner_service',
    freshness: 'UNKNOWN',
    freshness_generation_id: '',
    freshness_receipt_digest: '',
    repo_head_sha: '',
    repo_root_digest: '',
    authority_repo_root_digest: '',
    workspace_overlay_present: false,
    semantic_evidence_authority: 'unverified',
    no_authority_worktree_mutation_performed: false,
    query_receipt_id: '',
    no_holoindex_reindex_performed: true
  };
}

module.exports = {
  buildOwnerFallbackBundle,
  rejectedOwnerMetadata
};
