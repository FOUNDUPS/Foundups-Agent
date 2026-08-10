'use strict';

const cp = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');

const GIT_OUTPUT_TRUNCATED_MARKER = '[REDDOG_GIT_OUTPUT_TRUNCATED]';
let isTargetReadPathDenied;
let resolveSafeRepoFile;
let readBoundedRepoFile;

function create(options) {
  const policy = options && typeof options === 'object' ? options : {};
  isTargetReadPathDenied = policy.isTargetReadPathDenied;
  resolveSafeRepoFile = policy.resolveSafeRepoFile;
  readBoundedRepoFile = policy.readBoundedRepoFile;
  return { gitOutput, governedGitStatus, governedGitStat, governedGitDiff };
}

function sameCanonicalPath(left, right) {
  const normalize = (value) => {
    const resolved = path.resolve(value);
    return process.platform === 'win32' ? resolved.toLowerCase() : resolved;
  };
  return normalize(left) === normalize(right);
}

function plainGitControlFile(filePath) {
  if (!fs.existsSync(filePath)) return true;
  const metadata = fs.lstatSync(filePath);
  return metadata.isFile() && !metadata.isSymbolicLink() && metadata.nlink === 1
    && sameCanonicalPath(fs.realpathSync(filePath), filePath);
}

function confinedGitTree(root, entryCap) {
  const pending = [root];
  let inspected = 0;
  while (pending.length) {
    const directory = pending.pop();
    const handle = fs.opendirSync(directory);
    try {
      let entry;
      while ((entry = handle.readSync()) !== null) {
        inspected += 1;
        if (inspected > entryCap || entry.isSymbolicLink()) return false;
        const candidate = path.join(directory, entry.name);
        const metadata = fs.lstatSync(candidate);
        if (!sameCanonicalPath(fs.realpathSync(candidate), candidate)) return false;
        if (entry.isDirectory()) pending.push(candidate);
        else if (!entry.isFile() || metadata.nlink > 1) return false;
      }
    } finally {
      handle.closeSync();
    }
  }
  return true;
}

const gitStorageValidationCache = new Map();

function gitControlFingerprint(gitDir, name) {
  const candidate = path.join(gitDir, name);
  if (!fs.existsSync(candidate)) return [name, 'missing'];
  const metadata = fs.lstatSync(candidate);
  const kind = metadata.isFile() ? 'f' : metadata.isDirectory() ? 'd' : 'x';
  return [name, kind, metadata.ino, metadata.mtimeMs, metadata.ctimeMs,
    metadata.size, metadata.nlink];
}

function readGitDirectory(directory, state) {
  const metadata = fs.lstatSync(directory);
  if (!metadata.isDirectory() || metadata.isSymbolicLink()) return null;
  const entries = [];
  const handle = fs.opendirSync(directory);
  try {
    let entry;
    while ((entry = handle.readSync()) !== null) {
      state.inspected += 1;
      if (state.inspected > state.entryCap) return null;
      entries.push(entry);
    }
  } finally {
    handle.closeSync();
  }
  entries.sort((left, right) => left.name.localeCompare(right.name));
  return { metadata, entries };
}

function appendGitEntryFingerprint(gitDir, current, entry, parts, pending) {
  const candidate = path.join(current.directory, entry.name);
  const kind = entry.isDirectory() ? 'd' : entry.isFile() ? 'f' : 'x';
  const relative = path.relative(gitDir, candidate).replace(/\\/g, '/');
  const bindFile = current.bindFiles || /^objects\/(?:info|pack)\//.test(relative);
  if (kind === 'd') {
    const child = fs.lstatSync(candidate);
    parts.push(entry.name, kind, child.ino, child.mtimeMs, child.ctimeMs, child.nlink);
    pending.push({ directory: candidate,
      bindFiles: current.bindFiles || /^objects\/(?:info|pack)$/.test(relative) });
  } else if (bindFile) {
    const child = fs.lstatSync(candidate);
    parts.push(entry.name, kind, child.ino, child.mtimeMs, child.ctimeMs, child.size, child.nlink);
  } else {
    parts.push(entry.name, kind);
  }
}

function gitStorageFingerprint(gitDir, entryCap) {
  const pending = [
    { directory: path.join(gitDir, 'objects'), bindFiles: false },
    { directory: path.join(gitDir, 'refs'), bindFiles: true }
  ];
  const parts = ['HEAD', 'index', 'packed-refs'].flatMap(
    (name) => gitControlFingerprint(gitDir, name));
  const state = { inspected: 0, entryCap };
  while (pending.length) {
    const current = pending.pop();
    const snapshot = readGitDirectory(current.directory, state);
    if (!snapshot) return 'invalid';
    parts.push(path.relative(gitDir, current.directory), snapshot.metadata.ino,
      snapshot.metadata.mtimeMs, snapshot.metadata.ctimeMs, snapshot.entries.length);
    for (const entry of snapshot.entries) {
      appendGitEntryFingerprint(gitDir, current, entry, parts, pending);
    }
  }
  return crypto.createHash('sha256').update(parts.join('\0'), 'utf8').digest('hex');
}

function governedGitStorage(gitDir) {
  const fingerprint = gitStorageFingerprint(gitDir, 20000);
  const cached = gitStorageValidationCache.get(gitDir);
  if (cached && cached.fingerprint === fingerprint) return cached.valid;
  let valid = true;
  for (const name of ['objects', 'refs']) {
    const candidate = path.join(gitDir, name);
    if (!fs.existsSync(candidate)) valid = false;
    if (!valid) break;
    const metadata = fs.lstatSync(candidate);
    if (!metadata.isDirectory() || metadata.isSymbolicLink()
      || !sameCanonicalPath(fs.realpathSync(candidate), candidate)
      || !confinedGitTree(candidate, 20000)) valid = false;
  }
  for (const name of ['objects/info/alternates', 'objects/info/http-alternates', 'commondir']) {
    if (fs.existsSync(path.join(gitDir, name))) valid = false;
  }
  valid = valid && ['HEAD', 'index', 'packed-refs'].every((name) =>
    plainGitControlFile(path.join(gitDir, name)));
  gitStorageValidationCache.set(gitDir, { fingerprint, valid });
  return valid;
}

function registeredGitMetadata(root) {
  try {
    const gitEntry = path.join(root, '.git');
    const metadata = fs.lstatSync(gitEntry);
    if (metadata.isDirectory() && !metadata.isSymbolicLink()
      && sameCanonicalPath(fs.realpathSync(gitEntry), gitEntry)) {
      return governedGitStorage(gitEntry);
    }
    if (!metadata.isFile() || metadata.isSymbolicLink() || metadata.size > 4096) return false;
    const match = /^gitdir:\s*([^\r\n]+)\s*$/i.exec(fs.readFileSync(gitEntry, 'utf8'));
    if (!match) return false;
    const admin = fs.realpathSync(path.resolve(root, match[1]));
    if (!fs.lstatSync(admin).isDirectory()
      || path.basename(path.dirname(admin)).toLowerCase() !== 'worktrees') return false;
    if (!['HEAD', 'index', 'commondir', 'gitdir'].every((name) =>
      plainGitControlFile(path.join(admin, name)))) return false;
    const commonRef = fs.readFileSync(path.join(admin, 'commondir'), 'utf8').trim();
    const common = fs.realpathSync(path.resolve(admin, commonRef));
    if (path.basename(common).toLowerCase() !== '.git') return false;
    if (!sameCanonicalPath(path.dirname(admin), path.join(common, 'worktrees'))) return false;
    const backRef = fs.readFileSync(path.join(admin, 'gitdir'), 'utf8').trim();
    return sameCanonicalPath(path.resolve(admin, backRef), gitEntry)
      && governedGitStorage(common);
  } catch (err) {
    return false;
  }
}

function gitOutput(root, args, maxChars) {
  try {
    const canonicalRoot = fs.realpathSync(root);
    const gitEntry = path.join(canonicalRoot, '.git');
    if (!fs.existsSync(gitEntry)) {
      return '';
    }
    if (!registeredGitMetadata(canonicalRoot)) {
      return '[git context unavailable: external or linked Git directory denied]';
    }
    const env = sanitizedGitEnv();
    const riskySettings = configuredGitRiskySettings(canonicalRoot, env);
    if (riskySettings === null) {
      return '[git context unavailable: Git configuration unreadable]';
    }
    if (riskySettings.length) {
      return '[git context unavailable: configured Git setting denied]';
    }
    return executeGitOutput(canonicalRoot, args, maxChars, env);
  } catch (err) {
    return '[git context unavailable: ' + (err && err.message ? err.message.slice(0, 180) : 'unknown') + ']';
  }
}

function executeGitOutput(canonicalRoot, args, maxChars, env) {
  const safeArgs = [
    '--no-replace-objects', '-c', 'core.checkStat=default', '-c', 'core.fsmonitor=false',
    '-c', 'core.trustctime=true', '-c', 'core.worktree=' + canonicalRoot
  ];
  const output = cp.execFileSync('git', [...safeArgs, ...args], {
    cwd: canonicalRoot, encoding: 'utf8', env, timeout: 5000,
    maxBuffer: Math.max(maxChars * 4, 65536), windowsHide: true
  });
  return boundedGitOutput(String(output || ''), maxChars);
}

function boundedGitOutput(text, maxChars) {
  if (text.length <= maxChars) return text;
  const suffix = '\n' + GIT_OUTPUT_TRUNCATED_MARKER;
  return text.slice(0, Math.max(0, maxChars - suffix.length)) + suffix;
}

function sanitizedGitEnv() {
  const env = {};
  for (const [key, value] of Object.entries(process.env)) {
    if (!key.toUpperCase().startsWith('GIT_')) env[key] = value;
  }
  return Object.assign(env, {
    GIT_CONFIG_NOSYSTEM: '1',
    GIT_CONFIG_GLOBAL: process.platform === 'win32' ? 'NUL' : os.devNull,
    GIT_ATTR_NOSYSTEM: '1',
    GIT_EXTERNAL_DIFF: '',
    GIT_NO_LAZY_FETCH: '1',
    GIT_NO_REPLACE_OBJECTS: '1',
    GIT_OPTIONAL_LOCKS: '0',
    GIT_PAGER: 'cat'
  });
}

const GIT_RISKY_SETTING_PATTERN =
  /^(?:core\.(?:attributesfile|checkstat|excludesfile|trustctime|worktree)|extensions\.partialclone|remote\..*\.(?:partialclonefilter|promisor)|filter\..*\.(?:clean|process)|diff\..*\.(?:textconv|command)|diff\.external)$/i;
const GIT_INCLUDE_PATTERN = /^(?:include\.path|includeif\..*\.path)$/i;

function gitConfigNames(root, env, scope) {
  try {
    const output = cp.execFileSync(
      'git',
      ['config', scope, '--no-includes', '--null', '--name-only', '--list'],
      { cwd: root, encoding: 'utf8', env, timeout: 2000, windowsHide: true }
    );
    return String(output || '').split('\0').filter(Boolean);
  } catch (err) {
    return null;
  }
}

function worktreeGitConfigEnabled(root, env) {
  try {
    const output = cp.execFileSync(
      'git',
      ['config', '--local', '--no-includes', '--type=bool', '--get', 'extensions.worktreeConfig'],
      { cwd: root, encoding: 'utf8', env, timeout: 2000, windowsHide: true }
    );
    return String(output || '').trim() === 'true';
  } catch (err) {
    return err && err.status === 1 ? false : null;
  }
}

function configuredGitRiskySettings(root, env) {
  const localNames = gitConfigNames(root, env, '--local');
  if (localNames === null) return null;
  const localRisks = localNames.filter((name) =>
    GIT_INCLUDE_PATTERN.test(name) || GIT_RISKY_SETTING_PATTERN.test(name));
  if (localRisks.length) return localRisks;
  const worktreeEnabled = worktreeGitConfigEnabled(root, env);
  if (worktreeEnabled === null) return null;
  if (!worktreeEnabled) return [];
  const worktreeNames = gitConfigNames(root, env, '--worktree');
  if (worktreeNames === null) return null;
  return worktreeNames.filter((name) =>
    GIT_INCLUDE_PATTERN.test(name) || GIT_RISKY_SETTING_PATTERN.test(name));
}

function concealedGitIndexState(root) {
  const output = gitOutput(root, ['ls-files', '-v', '-z'], 1000000);
  if (output.startsWith('[git context unavailable') || output.includes(GIT_OUTPUT_TRUNCATED_MARKER)) {
    return null;
  }
  return output.split('\0').filter(Boolean).some((record) => {
    const tag = record.charAt(0);
    return tag === 'S' || (/[a-z]/.test(tag) && tag === tag.toLowerCase());
  });
}

function readGitChangeSets(root, hasHead) {
  const trackedArgs = hasHead
    ? ['diff', 'HEAD', '--name-only', '--no-renames', '-z']
    : ['diff', '--cached', '--name-only', '--no-renames', '-z'];
  return {
    tracked: gitOutput(root, ['--literal-pathspecs', ...trackedArgs, '--', '.'], 1000000),
    untracked: gitOutput(root,
    ['--literal-pathspecs', 'ls-files', '--others', '--exclude-standard', '-z', '--', '.'],
    1000000),
    ignored: gitOutput(root,
    ['--literal-pathspecs', 'ls-files', '--others', '--ignored', '--exclude-standard', '--directory', '-z', '--', '.'],
    1000000)
  };
}

function admitGitRecords(root, records) {
  const seen = new Set();
  let resolutionFailed = false;
  const admitted = records.filter(({ relPath }) => {
    if (seen.has(relPath) || isTargetReadPathDenied(relPath)) return false;
    seen.add(relPath);
    const full = path.resolve(root, relPath);
    if (!fs.existsSync(full)) return true;
    const resolved = resolveSafeRepoFile(root, relPath);
    if (!resolved.ok) resolutionFailed = true;
    return resolved.ok;
  });
  return resolutionFailed || admitted.length > 500 ? null : admitted;
}

function governedGitChangedPaths(root) {
  const concealedIndexState = concealedGitIndexState(root);
  if (concealedIndexState === null || concealedIndexState) return null;
  const head = gitOutput(root, ['rev-parse', '--verify', '--quiet', 'HEAD'], 256);
  const hasHead = !head.startsWith('[git context unavailable');
  const sets = readGitChangeSets(root, hasHead);
  if (Object.values(sets).some((value) =>
    value.startsWith('[git context unavailable') || value.includes(GIT_OUTPUT_TRUNCATED_MARKER))) {
    return null;
  }
  const admittedIgnored = sets.ignored.split('\0').filter(Boolean)
    .filter((relPath) => !isTargetReadPathDenied(relPath.replace(/\/$/, '')));
  if (admittedIgnored.length) return null;
  const records = [
    ...sets.tracked.split('\0').filter(Boolean).map((relPath) => ({ relPath, untracked: false })),
    ...sets.untracked.split('\0').filter(Boolean).map((relPath) => ({ relPath, untracked: true }))
  ];
  const admitted = admitGitRecords(root, records);
  if (!admitted) return null;
  return { hasHead, records: admitted };
}

function currentGitProjection(root, record, kind, maxChars) {
  const { relPath, untracked } = record;
  const exists = fs.existsSync(path.resolve(root, relPath));
  if (kind === 'status') return (untracked ? '?? ' : exists ? 'M  ' : 'D  ') + relPath + '\n';
  if (kind === 'stat') return relPath + (untracked ? ' | untracked\n' : exists ? ' | modified\n' : ' | deleted\n');
  if (!exists) return 'diff --reddog-deleted ' + relPath + '\n--- ' + relPath + '\n[deleted]\n';
  const content = readBoundedRepoFile(root, relPath, maxChars);
  const size = fs.statSync(path.resolve(root, relPath)).size;
  if (!content && size > 0) return '[git context unavailable: governed current-file read failed]';
  const label = untracked ? 'untracked' : 'current';
  return 'diff --reddog-' + label + ' ' + relPath + '\n+++ ' + relPath + '\n' + content;
}

function governedGitProjection(root, kind, maxChars) {
  const chunks = [];
  let chars = 0;
  const changed = governedGitChangedPaths(root);
  if (changed === null) return '[git context unavailable: governed change enumeration failed]';
  for (let index = 0; index < changed.records.length; index += 1) {
    const record = changed.records[index];
    const { relPath } = record;
    const remaining = maxChars - chars;
    if (remaining <= 0) {
      return boundedGitOutput(chunks.join('\n') + '\n' + GIT_OUTPUT_TRUNCATED_MARKER, maxChars);
    }
    const output = currentGitProjection(root, record, kind, remaining);
    if (output.startsWith('[git context unavailable')) {
      return '[git context unavailable: governed ' + kind + ' projection failed]';
    }
    if (!output) continue;
    chunks.push(output);
    chars += output.length;
    if (output.includes(GIT_OUTPUT_TRUNCATED_MARKER) && index < changed.records.length - 1) {
      return boundedGitOutput(chunks.join('\n'), maxChars);
    }
  }
  return boundedGitOutput(chunks.join('\n'), maxChars);
}

function governedGitStatus(root, maxChars) {
  return governedGitProjection(root, 'status', maxChars);
}

function governedGitStat(root, maxChars) {
  return governedGitProjection(root, 'stat', maxChars);
}

function governedGitDiff(root, maxChars) {
  return governedGitProjection(root, 'diff', maxChars);
}

module.exports = { create, GIT_OUTPUT_TRUNCATED_MARKER };
