'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

function dependencies(options) {
  const opts = options && typeof options === 'object' ? options : {};
  return {
    fs: opts.fs || fs,
    path: opts.path || path,
    crypto: opts.crypto || crypto
  };
}

function sha256Hex(value, cryptoImpl) {
  return cryptoImpl.createHash('sha256').update(value).digest('hex');
}

function sha256Receipt(value, cryptoImpl) {
  return 'sha256:' + sha256Hex(Buffer.from(String(value), 'utf8'), cryptoImpl);
}

function normalizedTextBytes(value) {
  return Buffer.from(value.toString('utf8').replace(/\r\n/g, '\n'), 'utf8');
}

function realpath(fsImpl, value) {
  const resolver = fsImpl.realpathSync.native || fsImpl.realpathSync;
  return resolver.call(fsImpl.realpathSync, value);
}

function safeRoot(rootValue, deps) {
  if (typeof rootValue !== 'string' || !rootValue || rootValue !== rootValue.trim()) {
    return { root: '', canonicalRoot: '', reason: 'workspace_root_missing' };
  }
  const root = deps.path.resolve(rootValue);
  try {
    const stats = deps.fs.lstatSync(root);
    if (!stats.isDirectory() || stats.isSymbolicLink()) {
      return { root, canonicalRoot: '', reason: 'workspace_root_unsafe' };
    }
    return { root, canonicalRoot: realpath(deps.fs, root), reason: '' };
  } catch (err) {
    return { root, canonicalRoot: '', reason: 'workspace_root_missing' };
  }
}

function lexicalCandidate(rootState, relativePath, deps) {
  const candidate = deps.path.resolve(rootState.root, relativePath);
  const relative = deps.path.relative(rootState.root, candidate);
  if (!relative || relative.startsWith('..') || deps.path.isAbsolute(relative)) {
    return { ok: false, candidate: '', parts: [], reason: 'path_escape' };
  }
  return { ok: true, candidate, parts: relative.split(deps.path.sep), reason: '' };
}

function hasUnsafePathComponent(rootState, parts, deps) {
  let current = rootState.root;
  for (const part of parts) {
    current = deps.path.join(current, part);
    const stats = deps.fs.lstatSync(current);
    if (stats.isSymbolicLink()) {
      return true;
    }
  }
  return false;
}

function canonicalCandidateIsContained(rootState, candidate, deps) {
  const relative = deps.path.relative(rootState.canonicalRoot, realpath(deps.fs, candidate));
  return !!relative && !relative.startsWith('..') && !deps.path.isAbsolute(relative);
}

function containedRegularFile(rootState, relativePath, deps) {
  const located = lexicalCandidate(rootState, relativePath, deps);
  if (!located.ok) {
    return located;
  }
  try {
    if (hasUnsafePathComponent(rootState, located.parts, deps)) {
      return { ok: false, candidate: '', reason: 'unsafe_path_component' };
    }
    const stats = deps.fs.lstatSync(located.candidate);
    if (!stats.isFile() || !canonicalCandidateIsContained(rootState, located.candidate, deps)) {
      return { ok: false, candidate: '', reason: 'not_regular_contained_file' };
    }
    return { ok: true, candidate: located.candidate, size: stats.size, reason: '' };
  } catch (err) {
    return { ok: false, candidate: '', reason: 'missing_or_unreadable' };
  }
}

module.exports = {
  containedRegularFile,
  dependencies,
  normalizedTextBytes,
  safeRoot,
  sha256Hex,
  sha256Receipt
};
