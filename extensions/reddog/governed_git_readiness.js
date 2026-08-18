'use strict';

const cp = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const GIT_READINESS_SCHEMA = 'reddog_governed_git_readiness.v1';
const gitReadinessByRoot = new Map();

function sameCanonicalPath(left, right) {
  const normalize = (value) => {
    const resolved = path.resolve(value);
    return process.platform === 'win32' ? resolved.toLowerCase() : resolved;
  };
  return normalize(left) === normalize(right);
}

function validatedCanonicalRoot(root) {
  try {
    if (typeof root !== 'string' || !path.isAbsolute(root) || root.length > 4096
      || /[\0\r\n]/.test(root) || root.replace(/\\/g, '/').split('/').includes('..')) return '';
    const resolved = path.resolve(root);
    const canonical = fs.realpathSync(resolved);
    const metadata = fs.lstatSync(canonical);
    if (!metadata.isDirectory() || metadata.isSymbolicLink()
      || !sameCanonicalPath(canonical, resolved) || canonical === '*') return '';
    return canonical;
  } catch (err) {
    return '';
  }
}

function readinessEvidence(overrides) {
  return Object.freeze(Object.assign({
    schema_version: GIT_READINESS_SCHEMA, ready: false,
    canonical_root_validated: false, git_metadata_validated: false,
    ownership_mismatch_observed: false, safe_directory_override_applied: false,
    safe_directory_scope: 'none', safe_directory_wildcard: false,
    config_write_performed: false, reason: 'unproven'
  }, overrides || {}));
}

function setGitReadiness(root, overrides) {
  gitReadinessByRoot.set(root, readinessEvidence(overrides));
}

function governedGitReadiness(root) {
  const canonicalRoot = validatedCanonicalRoot(root);
  if (!canonicalRoot) return readinessEvidence({ reason: 'canonical_root_invalid' });
  return gitReadinessByRoot.get(canonicalRoot)
    || readinessEvidence({ canonical_root_validated: true, reason: 'not_probed' });
}

function sanitizedGitEnv() {
  const env = {};
  for (const [key, value] of Object.entries(process.env)) {
    if (!key.toUpperCase().startsWith('GIT_')) env[key] = value;
  }
  return Object.assign(env, {
    GIT_CONFIG_NOSYSTEM: '1',
    GIT_CONFIG_GLOBAL: process.platform === 'win32' ? 'NUL' : os.devNull,
    GIT_ATTR_NOSYSTEM: '1', GIT_EXTERNAL_DIFF: '', GIT_NO_LAZY_FETCH: '1',
    GIT_NO_REPLACE_OBJECTS: '1', GIT_OPTIONAL_LOCKS: '0', GIT_PAGER: 'cat'
  });
}

const GIT_RISKY_SETTING_PATTERN =
  /^(?:core\.(?:attributesfile|checkstat|excludesfile|trustctime|worktree)|extensions\.partialclone|remote\..*\.(?:partialclonefilter|promisor)|filter\..*\.(?:clean|process)|diff\..*\.(?:textconv|command)|diff\.external)$/i;
const GIT_INCLUDE_PATTERN = /^(?:include\.path|includeif\..*\.path)$/i;

function gitConfigNames(root, env, scope, safeDirectory = true) {
  try {
    const prefix = safeDirectory ? ['-c', 'safe.directory=' + root] : [];
    const output = cp.execFileSync(
      'git', [...prefix, 'config', scope, '--no-includes', '--null', '--name-only', '--list'],
      { cwd: root, encoding: 'utf8', env, timeout: 2000, windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe'] }
    );
    return String(output || '').split('\0').filter(Boolean);
  } catch (err) {
    return null;
  }
}

function gitOwnershipReadiness(root, env) {
  if (gitConfigNames(root, env, '--local', false) !== null) {
    return { overrideRequired: false };
  }
  return gitConfigNames(root, env, '--local', true) !== null
    ? { overrideRequired: true } : null;
}

function worktreeGitConfigEnabled(root, env, safeDirectory) {
  try {
    const prefix = safeDirectory ? ['-c', 'safe.directory=' + root] : [];
    const output = cp.execFileSync(
      'git', [...prefix,
        'config', '--local', '--no-includes', '--type=bool', '--get', 'extensions.worktreeConfig'],
      { cwd: root, encoding: 'utf8', env, timeout: 2000, windowsHide: true }
    );
    return String(output || '').trim() === 'true';
  } catch (err) {
    return err && err.status === 1 ? false : null;
  }
}

function configuredGitRiskySettings(root, env, safeDirectory) {
  const localNames = gitConfigNames(root, env, '--local', safeDirectory);
  if (localNames === null) return null;
  const localRisks = localNames.filter((name) =>
    GIT_INCLUDE_PATTERN.test(name) || GIT_RISKY_SETTING_PATTERN.test(name));
  if (localRisks.length) return localRisks;
  const worktreeEnabled = worktreeGitConfigEnabled(root, env, safeDirectory);
  if (worktreeEnabled === null) return null;
  if (!worktreeEnabled) return [];
  const worktreeNames = gitConfigNames(root, env, '--worktree', safeDirectory);
  if (worktreeNames === null) return null;
  return worktreeNames.filter((name) =>
    GIT_INCLUDE_PATTERN.test(name) || GIT_RISKY_SETTING_PATTERN.test(name));
}

function governedGitArgs(root, safeDirectory, args) {
  const safe = safeDirectory ? ['-c', 'safe.directory=' + root] : [];
  const nullPath = '/dev/null';
  return [
    '--no-replace-objects', '--no-optional-locks', ...safe,
    '-c', 'core.checkStat=default', '-c', 'core.fsmonitor=false',
    '-c', 'core.trustctime=true', '-c', 'core.worktree=' + root,
    '-c', 'core.hooksPath=' + nullPath,
    '-c', 'core.attributesFile=' + nullPath,
    '-c', 'core.excludesFile=' + nullPath,
    '-c', 'diff.external=', '-c', 'core.useReplaceRefs=false', ...args
  ];
}

module.exports = {
  GIT_READINESS_SCHEMA,
  configuredGitRiskySettings,
  governedGitArgs,
  gitOwnershipReadiness,
  governedGitReadiness,
  sameCanonicalPath,
  sanitizedGitEnv,
  setGitReadiness,
  validatedCanonicalRoot
};
