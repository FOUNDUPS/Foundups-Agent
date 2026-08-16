'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { sameCanonicalPath } = require('./governed_git_readiness');

const SCHEMA = 'reddog_git_projection_receipt.v1';
const MAX_CHANGED_PATHS = 500;
const MAX_IGNORED_PATHS = 5000;
const MAX_FILE_BYTES = 2 * 1024 * 1024;
const MAX_TOTAL_BYTES = 16 * 1024 * 1024;
const TRUNCATED = '[REDDOG_GIT_OUTPUT_TRUNCATED]';

function digest(parts) {
  const hash = crypto.createHash('sha256');
  for (const part of parts) hash.update(part);
  return hash.digest('hex');
}

function normalizedPath(value) {
  const rel = String(value || '').replace(/\\/g, '/').replace(/\/+$/, '');
  if (!rel || rel.length > 4096 || /[\0\r\n]/.test(rel)
    || path.posix.isAbsolute(rel)
    || rel.split('/').some((part) => !part || part === '.' || part === '..')) return '';
  return rel;
}

function comparisonKey(value) {
  const normalized = String(value || '').replace(/\\/g, '/').normalize('NFC');
  return process.platform === 'win32' ? normalized.toLowerCase() : normalized;
}

function parsePaths(value, cap) {
  const raw = value.split('\0').filter(Boolean);
  if (raw.length > cap) return null;
  const paths = raw.map(normalizedPath);
  const keys = paths.map(comparisonKey);
  return paths.some((item) => !item) || new Set(keys).size !== paths.length
    ? null : paths;
}

function concealedIndex(output) {
  const result = output(['ls-files', '-v', '-z'], 1000000);
  if (result.startsWith('[git context unavailable') || result.includes(TRUNCATED)) return null;
  return result.split('\0').filter(Boolean).some((record) => {
    const tag = record.charAt(0);
    return tag === 'S' || (/[a-z]/.test(tag) && tag === tag.toLowerCase());
  });
}

function changeSets(hasHead, output) {
  const tracked = hasHead ? ['diff', 'HEAD', '--name-only', '--no-renames', '-z']
    : ['diff', '--cached', '--name-only', '--no-renames', '-z'];
  return {
    tracked: output(['--literal-pathspecs', ...tracked, '--', '.'], 1000000),
    untracked: output(['--literal-pathspecs', 'ls-files', '--others',
      '--exclude-standard', '-z', '--', '.'], 1000000),
    ignored: output(['--literal-pathspecs', 'ls-files', '--others', '--ignored',
      '--exclude-standard', '--directory', '-z', '--', '.'], 1000000)
  };
}

function existingFileIdentity(root, relPath, policy) {
  try {
    const resolved = policy.resolveSafeRepoFile(root, relPath);
    if (!resolved || !resolved.ok || typeof resolved.full !== 'string') return null;
    const canonicalRoot = fs.realpathSync(path.resolve(root));
    const requested = path.resolve(resolved.full);
    const full = fs.realpathSync(requested);
    const metadata = fs.lstatSync(full);
    const rootKey = comparisonKey(canonicalRoot);
    const fullKey = comparisonKey(full);
    if (!sameCanonicalPath(requested, full) || !fullKey.startsWith(rootKey + '/')
      || !metadata.isFile() || metadata.isSymbolicLink() || metadata.nlink !== 1) return null;
    return { full, key: fullKey };
  } catch (err) {
    return null;
  }
}

function admittedRecords(root, records, policy) {
  const seen = new Set();
  const existing = new Set();
  const admitted = [];
  if (records.length > MAX_CHANGED_PATHS) return null;
  for (const record of records) {
    const key = comparisonKey(record.relPath);
    if (seen.has(key)) return null;
    seen.add(key);
    if (policy.isTargetReadPathDenied(record.relPath)) continue;
    const full = path.resolve(root, record.relPath);
    if (!fs.existsSync(full)) {
      admitted.push({ ...record, exists: false });
      continue;
    }
    const identity = existingFileIdentity(root, record.relPath, policy);
    if (!identity || existing.has(identity.key)) return null;
    existing.add(identity.key);
    admitted.push({ ...record, exists: true, canonicalFullPath: identity.full });
  }
  return admitted;
}

function intersects(ignored, records) {
  return ignored.some((item) => records.some(({ relPath }) => {
    const ignoredKey = comparisonKey(item);
    const recordKey = comparisonKey(relPath);
    return recordKey === ignoredKey || recordKey.startsWith(ignoredKey + '/')
      || ignoredKey.startsWith(recordKey + '/');
  }));
}

function enumerate(root, output, policy) {
  const concealed = concealedIndex(output);
  if (concealed === null || concealed) return null;
  const head = output(['rev-parse', '--verify', '--quiet', 'HEAD'], 256);
  const sets = changeSets(!head.startsWith('[git context unavailable'), output);
  if (Object.values(sets).some((value) =>
    value.startsWith('[git context unavailable') || value.includes(TRUNCATED))) return null;
  const tracked = parsePaths(sets.tracked, MAX_CHANGED_PATHS);
  const untracked = parsePaths(sets.untracked, MAX_CHANGED_PATHS);
  const ignored = parsePaths(sets.ignored, MAX_IGNORED_PATHS);
  if (!tracked || !untracked || !ignored) return null;
  const records = admittedRecords(root, [
    ...tracked.map((relPath) => ({ relPath, untracked: false })),
    ...untracked.map((relPath) => ({ relPath, untracked: true }))
  ], policy);
  if (!records || intersects(ignored, records)) return null;
  const excluded = ignored.slice().sort();
  return { records, ignoredExcludedCount: excluded.length,
    ignoredExcludedSetDigest: digest([Buffer.from(excluded.join('\0'), 'utf8')]) };
}

function statIdentity(stat) {
  return [stat.dev, stat.ino, stat.mode, stat.nlink, stat.size,
    stat.mtimeMs, stat.ctimeMs].join(':');
}

function readStable(root, record, policy) {
  const resolved = existingFileIdentity(root, record.relPath, policy);
  if (!resolved || resolved.key !== comparisonKey(record.canonicalFullPath)) return null;
  let handle;
  try {
    const before = fs.lstatSync(resolved.full);
    if (!before.isFile() || before.isSymbolicLink() || before.nlink !== 1
      || before.size > MAX_FILE_BYTES) return null;
    handle = fs.openSync(resolved.full,
      fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0));
    const opened = fs.fstatSync(handle);
    const bytes = fs.readFileSync(handle);
    const afterHandle = fs.fstatSync(handle);
    const afterPath = fs.lstatSync(resolved.full);
    if (statIdentity(before) !== statIdentity(opened)
      || statIdentity(opened) !== statIdentity(afterHandle)
      || statIdentity(afterHandle) !== statIdentity(afterPath)
      || !sameCanonicalPath(fs.realpathSync(resolved.full), resolved.full)
      || bytes.length !== before.size) return null;
    return { bytes, identity: statIdentity(afterPath), digest: digest([bytes]) };
  } catch (err) {
    return null;
  } finally {
    if (handle !== undefined) fs.closeSync(handle);
  }
}

function capture(root, changed, policy) {
  let totalBytes = 0;
  const files = [];
  for (const record of changed.records) {
    if (!record.exists) {
      if (record.untracked) return null;
      files.push({ ...record, exists: false, bytes: Buffer.alloc(0), digest: '' });
      continue;
    }
    const item = readStable(root, record, policy);
    if (!item || (totalBytes += item.bytes.length) > MAX_TOTAL_BYTES) return null;
    files.push({ ...record, exists: true, ...item });
  }
  const parts = files.map((item) => Buffer.from([
    item.relPath, item.untracked ? 'u' : 't', item.exists ? '1' : '0',
    item.identity || '', item.digest
  ].join('\0'), 'utf8'));
  return { files, contentDigest: digest(parts), totalBytes };
}

function bounded(text, maxChars) {
  if (text.length <= maxChars) return text;
  const suffix = '\n' + TRUNCATED;
  return text.slice(0, Math.max(0, maxChars - suffix.length)) + suffix;
}

function recordProjection(record, kind) {
  const { relPath, untracked, exists } = record;
  if (kind === 'status') return (untracked ? '?? ' : exists ? 'M  ' : 'D  ') + relPath + '\n';
  if (kind === 'stat') return relPath + (untracked ? ' | untracked\n'
    : exists ? ' | modified\n' : ' | deleted\n');
  if (!exists) return 'diff --reddog-deleted ' + relPath + '\n--- ' + relPath + '\n[deleted]\n';
  return 'diff --reddog-' + (untracked ? 'untracked' : 'current') + ' ' + relPath
    + '\n+++ ' + relPath + '\n' + record.bytes.toString('utf8');
}

function render(captured, kind, maxChars) {
  const chunks = [];
  let chars = 0;
  for (let index = 0; index < captured.files.length; index += 1) {
    const remaining = maxChars - chars;
    if (remaining <= 0) return bounded(chunks.join('\n') + '\n' + TRUNCATED, maxChars);
    const output = recordProjection(captured.files[index], kind);
    chunks.push(output);
    chars += output.length;
    if (output.includes(TRUNCATED) && index < captured.files.length - 1) {
      return bounded(chunks.join('\n'), maxChars);
    }
  }
  return bounded(chunks.join('\n'), maxChars);
}

function changedSetDigest(changed) {
  const parts = changed.records.map((item) =>
    [item.relPath, item.untracked ? 'u' : 't'].join('\0'));
  parts.push(String(changed.ignoredExcludedCount), changed.ignoredExcludedSetDigest);
  return digest([Buffer.from(parts.join('\0'), 'utf8')]);
}

function receipt(prepared, captured, finalFingerprint) {
  return Object.freeze({ schema_version: SCHEMA,
    captured_at: new Date().toISOString(), point_in_time_only: true,
    root_digest: digest([Buffer.from(prepared.canonicalRoot, 'utf8')]),
    changed_path_count: prepared.changed.records.length,
    path_set_digest: changedSetDigest(prepared.changed),
    content_digest: captured.contentDigest, captured_bytes: captured.totalBytes,
    ignored_excluded_count: prepared.changed.ignoredExcludedCount,
    ignored_excluded_set_digest: prepared.changed.ignoredExcludedSetDigest,
    git_start_fingerprint: prepared.receipt.fingerprint,
    git_final_fingerprint: finalFingerprint });
}

function create(policy) {
  const fixed = Object.freeze({
    isTargetReadPathDenied: policy.isTargetReadPathDenied,
    resolveSafeRepoFile: policy.resolveSafeRepoFile
  });
  return Object.freeze({
    enumerate: (root, output) => enumerate(root, output, fixed),
    capture: (root, changed) => capture(root, changed, fixed),
    render, changedSetDigest, receipt
  });
}

module.exports = { create, SCHEMA };
