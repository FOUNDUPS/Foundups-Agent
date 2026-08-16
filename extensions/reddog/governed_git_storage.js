'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { sameCanonicalPath } = require('./governed_git_readiness');

const STORAGE_DIRS = ['objects', 'refs'];
const CONTROL_FILES = [
  'HEAD', 'index', 'packed-refs', 'config', 'config.worktree', 'shallow',
  'info/attributes', 'info/exclude'
];
const FORBIDDEN_CONTROLS = [
  'objects/info/alternates', 'objects/info/http-alternates', 'commondir',
  'info/grafts'
];
const storageCache = new Map();

function plainControlFile(filePath) {
  if (!fs.existsSync(filePath)) return true;
  const metadata = fs.lstatSync(filePath);
  return metadata.isFile() && !metadata.isSymbolicLink() && metadata.nlink === 1
    && sameCanonicalPath(fs.realpathSync(filePath), filePath);
}

function controlFingerprint(gitDir, name) {
  const candidate = path.join(gitDir, name);
  if (!fs.existsSync(candidate)) return [name, 'missing'];
  const metadata = fs.lstatSync(candidate);
  const kind = metadata.isFile() ? 'f' : metadata.isDirectory() ? 'd' : 'x';
  return [name, kind, metadata.ino, metadata.mtimeMs, metadata.ctimeMs,
    metadata.size, metadata.nlink];
}

function readDirectory(directory, state) {
  const metadata = fs.lstatSync(directory);
  if (!metadata.isDirectory() || metadata.isSymbolicLink()
    || !sameCanonicalPath(fs.realpathSync(directory), directory)) return null;
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

function appendEntryFingerprint(gitDir, directory, entry, parts, pending, state) {
  const candidate = path.join(directory, entry.name);
  const metadata = fs.lstatSync(candidate);
  const kind = metadata.isDirectory() ? 'd' : metadata.isFile() ? 'f' : 'x';
  const relative = path.relative(gitDir, candidate).replace(/\\/g, '/');
  parts.push(relative, kind, metadata.ino, metadata.mtimeMs, metadata.ctimeMs,
    metadata.size, metadata.nlink);
  if (metadata.isSymbolicLink() || kind === 'x'
    || (kind === 'f' && metadata.nlink !== 1)) {
    state.valid = false;
    return;
  }
  if (kind === 'd') pending.push(candidate);
}

function storageFingerprint(gitDir, entryCap) {
  const pending = STORAGE_DIRS.map((name) => path.join(gitDir, name));
  const controls = [...CONTROL_FILES, ...FORBIDDEN_CONTROLS];
  const parts = controls.flatMap((name) => controlFingerprint(gitDir, name));
  const state = { inspected: 0, entryCap, valid: true };
  while (pending.length) {
    const directory = pending.pop();
    const snapshot = readDirectory(directory, state);
    if (!snapshot) return { fingerprint: 'invalid', valid: false };
    parts.push(path.relative(gitDir, directory), snapshot.metadata.ino,
      snapshot.metadata.mtimeMs, snapshot.metadata.ctimeMs, snapshot.entries.length);
    for (const entry of snapshot.entries) {
      appendEntryFingerprint(gitDir, directory, entry, parts, pending, state);
    }
  }
  const fingerprint = crypto.createHash('sha256')
    .update(parts.join('\0'), 'utf8').digest('hex');
  return { fingerprint, valid: state.valid };
}

function governedStorage(gitDir, force) {
  const snapshot = storageFingerprint(gitDir, 20000);
  const fingerprint = snapshot.fingerprint;
  const cached = storageCache.get(gitDir);
  if (!force && cached && cached.fingerprint === fingerprint) {
    return { fingerprint, valid: cached.valid };
  }
  let valid = snapshot.valid;
  valid = valid && !FORBIDDEN_CONTROLS.some((name) =>
    fs.existsSync(path.join(gitDir, name)));
  valid = valid && CONTROL_FILES.every((name) =>
    plainControlFile(path.join(gitDir, name)));
  storageCache.set(gitDir, { fingerprint, valid });
  return { fingerprint, valid };
}

function directGitDirectory(gitEntry, metadata, force) {
  if (!metadata.isDirectory() || metadata.isSymbolicLink()
    || !sameCanonicalPath(fs.realpathSync(gitEntry), gitEntry)) return null;
  const storage = governedStorage(gitEntry, force);
  return { fingerprint: 'direct\0' + storage.fingerprint, valid: storage.valid };
}

function linkedGitDirectory(root, gitEntry, metadata, force) {
  if (!metadata.isFile() || metadata.isSymbolicLink()
    || metadata.nlink !== 1 || metadata.size > 4096) return null;
  const match = /^gitdir:\s*([^\r\n]+)\s*$/i.exec(fs.readFileSync(gitEntry, 'utf8'));
  if (!match) return null;
  const admin = fs.realpathSync(path.resolve(root, match[1]));
  if (!fs.lstatSync(admin).isDirectory()
    || path.basename(path.dirname(admin)).toLowerCase() !== 'worktrees') return null;
  if (!['HEAD', 'index', 'commondir', 'gitdir', 'config.worktree'].every((name) =>
    plainControlFile(path.join(admin, name)))) return null;
  const common = fs.realpathSync(path.resolve(
    admin, fs.readFileSync(path.join(admin, 'commondir'), 'utf8').trim()));
  if (path.basename(common).toLowerCase() !== '.git'
    || !sameCanonicalPath(path.dirname(admin), path.join(common, 'worktrees'))) return null;
  const backRef = fs.readFileSync(path.join(admin, 'gitdir'), 'utf8').trim();
  if (!sameCanonicalPath(path.resolve(admin, backRef), gitEntry)) return null;
  const storage = governedStorage(common, force);
  const controls = ['HEAD', 'index', 'commondir', 'gitdir', 'config.worktree']
    .flatMap((name) => controlFingerprint(admin, name));
  const fingerprint = crypto.createHash('sha256')
    .update(['linked', storage.fingerprint, ...controls].join('\0'), 'utf8')
    .digest('hex');
  return { fingerprint, valid: storage.valid };
}

function registeredGitMetadataReceipt(root, options) {
  try {
    const force = Boolean(options && options.force);
    const gitEntry = path.join(root, '.git');
    const metadata = fs.lstatSync(gitEntry);
    const receipt = directGitDirectory(gitEntry, metadata, force)
      || linkedGitDirectory(root, gitEntry, metadata, force);
    return receipt || { fingerprint: '', valid: false };
  } catch (err) {
    return { fingerprint: '', valid: false };
  }
}

function registeredGitMetadata(root) {
  return registeredGitMetadataReceipt(root).valid;
}

module.exports = {
  plainControlFile, registeredGitMetadata, registeredGitMetadataReceipt
};
