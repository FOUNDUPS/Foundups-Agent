'use strict';

const grounding = require('./grounded_target_continuity');
const {
  GIT_READINESS_SCHEMA,
  governedGitReadiness,
  validatedCanonicalRoot
} = require('./governed_git_readiness');

const SCHEMA = 'reddog_governed_git_repo_state.v2';

function nullRecords(output) {
  return String(output || '').split('\0').filter(Boolean);
}

function dirtyPaths(output) {
  const records = nullRecords(output);
  const paths = [];
  for (let index = 0; index < records.length; index += 1) {
    const record = records[index];
    if (record.length < 4) continue;
    paths.push(record.slice(3).replace(/\\/g, '/'));
    if (/^[RC]/.test(record)) index += 1;
  }
  return [...new Set(paths)].sort();
}

function capture(root, outputs) {
  const canonicalRoot = validatedCanonicalRoot(root);
  if (!canonicalRoot || typeof outputs !== 'function') return null;
  const values = outputs(['HEAD_SHA', 'REPO_STATUS', 'WORKTREE_LIST']);
  if (!Array.isArray(values) || values.length !== 3
    || values.some((value) => String(value)
      .startsWith('[git context unavailable:'))) return null;
  const readiness = governedGitReadiness(canonicalRoot);
  if (!readiness.ready || readiness.schema_version !== GIT_READINESS_SCHEMA
    || !readiness.git_executable_binding) return null;
  const body = {
    schema_version: SCHEMA,
    repo_root_digest: grounding.canonicalDigest({ repo_root: canonicalRoot }),
    head_sha: String(values[0] || '').trim(),
    dirty_paths: dirtyPaths(values[1]),
    dirty_digest: grounding.canonicalDigest(nullRecords(values[1])),
    worktree_digest: grounding.canonicalDigest(nullRecords(values[2])),
    governed_git_readiness: readiness
  };
  return Object.freeze({ ...body, content_digest: grounding.canonicalDigest(body) });
}

module.exports = { SCHEMA, capture };
