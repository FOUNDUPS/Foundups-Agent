'use strict';

const fs = require('fs');
const path = require('path');
const { buildGovernedGit } = require('./start_operations_environment');
const defaultGitExecutable = require('./governed_git_executable');

const GIT_READINESS_SCHEMA = 'reddog_governed_git_readiness.v2';
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
    config_write_performed: false, git_executable_binding: null,
    reason: 'unproven'
  }, overrides || {}));
}

function setGitReadiness(root, overrides, binding, authority) {
  const evidence = readinessEvidence(Object.assign({}, overrides || {}, {
    git_executable_binding: binding
      ? defaultGitExecutable.toPublicExecutableReceipt(binding) : null
  }));
  gitReadinessByRoot.set(root, { evidence, binding: binding || null,
    authority: authority || defaultGitExecutable });
}

function governedGitReadiness(root) {
  const canonicalRoot = validatedCanonicalRoot(root);
  if (!canonicalRoot) return readinessEvidence({ reason: 'canonical_root_invalid' });
  const stored = gitReadinessByRoot.get(canonicalRoot);
  if (!stored) return readinessEvidence({
    canonical_root_validated: true, reason: 'not_probed'
  });
  if (!stored.binding) return stored.evidence;
  try {
    const current = stored.authority.revalidate(stored.binding);
    return readinessEvidence({ ...stored.evidence,
      git_executable_binding: defaultGitExecutable.toPublicExecutableReceipt(current) });
  } catch (_err) {
    return readinessEvidence({ ...stored.evidence, ready: false,
      git_executable_binding: null, reason: 'git_executable_changed' });
  }
}

function sanitizedGitEnv(source) {
  return buildGovernedGit(source && typeof source === 'object' ? source : process.env);
}

const GIT_RISKY_SETTING_PATTERN =
  /^(?:core\.(?:attributesfile|checkstat|excludesfile|trustctime|worktree)|extensions\.(?:partialclone|refstorage)|remote\..*\.(?:partialclonefilter|promisor)|filter\..*\.(?:clean|process)|diff\..*\.(?:textconv|command)|diff\.external)$/i;
const GIT_INCLUDE_PATTERN = /^(?:include\.path|includeif\..*\.path)$/i;
const GIT_CONFIG_TIMEOUT_MS = 5000;

function gitConfigNames(root, env, scope, safeDirectory, binding, authority) {
  try {
    const prefix = safeDirectory ? ['-c', 'safe.directory=' + root] : [];
    const output = authority.execFileSync(
      binding, [...prefix, 'config', scope, '--no-includes', '--null', '--name-only', '--list'],
      { cwd: root, encoding: 'utf8', env, timeout: GIT_CONFIG_TIMEOUT_MS, windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe'] }
    );
    return String(output || '').split('\0').filter(Boolean);
  } catch (err) {
    return null;
  }
}

function gitOwnershipReadiness(root, env, binding, authority) {
  if (gitConfigNames(root, env, '--local', false, binding, authority) !== null) {
    return { overrideRequired: false };
  }
  return gitConfigNames(root, env, '--local', true, binding, authority) !== null
    ? { overrideRequired: true } : null;
}

function worktreeGitConfigEnabled(root, env, safeDirectory, binding, authority) {
  try {
    const prefix = safeDirectory ? ['-c', 'safe.directory=' + root] : [];
    const output = authority.execFileSync(
      binding, [...prefix,
        'config', '--local', '--no-includes', '--type=bool', '--get', 'extensions.worktreeConfig'],
      { cwd: root, encoding: 'utf8', env, timeout: GIT_CONFIG_TIMEOUT_MS, windowsHide: true }
    );
    return String(output || '').trim() === 'true';
  } catch (err) {
    return err && err.status === 1 ? false : null;
  }
}

function configuredGitRiskySettings(root, env, safeDirectory, worktreeConfigState,
  binding, authority) {
  const localNames = gitConfigNames(
    root, env, '--local', safeDirectory, binding, authority
  );
  if (localNames === null) return null;
  const localRisks = localNames.filter((name) =>
    GIT_INCLUDE_PATTERN.test(name) || GIT_RISKY_SETTING_PATTERN.test(name));
  if (localRisks.length) return localRisks;
  const worktreeEnabled = worktreeGitConfigEnabled(
    root, env, safeDirectory, binding, authority
  );
  if (worktreeEnabled === null) return null;
  if (!worktreeEnabled) return [];
  if (worktreeConfigState === 'absent') return [];
  if (worktreeConfigState !== 'present') return null;
  const worktreeNames = gitConfigNames(
    root, env, '--worktree', safeDirectory, binding, authority
  );
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
  GIT_CONFIG_TIMEOUT_MS,
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
