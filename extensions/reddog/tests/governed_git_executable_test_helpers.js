'use strict';

const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');

const roots = [];

function fixtureRoot() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-git-executable-'));
  roots.push(root);
  return root;
}

function executableFile(directory, name, content) {
  fs.mkdirSync(directory, { recursive: true });
  const target = path.join(directory, name);
  fs.writeFileSync(target, content || 'fixture executable bytes\n');
  fs.chmodSync(target, 0o755);
  return target;
}

function validSignature(target, verifier) {
  const identity = Object.freeze({ portable: 'sha256:' + 'e'.repeat(64),
    native: Object.freeze({ dev: '1', ino: '2', mode: '33261', nlink: 1,
      birthtime_ns: '3', ctime_ns: '4', mtime_ns: '5' }), nlink: 1 });
  const pathDigest = 'sha256:' + 'c'.repeat(64);
  const rootDigest = 'sha256:' + 'f'.repeat(64);
  const relativeDigest = 'sha256:' + crypto.createHash('sha256')
    .update('System32/WindowsPowerShell/v1.0/powershell.exe').digest('hex');
  const containment = 'sha256:' + crypto.createHash('sha256')
    .update([rootDigest, pathDigest, relativeDigest].join('\0')).digest('hex');
  return Object.freeze({
    status: 'valid', subject_digest: 'sha256:' + 'a'.repeat(64),
    thumbprint_digest: 'sha256:' + 'b'.repeat(64),
    verifier: Object.freeze({
      canonical_path: verifier || target,
      canonical_path_digest: pathDigest, sha256: 'd'.repeat(64), size: 1,
      start_identity: identity, final_identity: identity,
      system_root_digest: rootDigest, fixed_relative_path_digest: relativeDigest,
      system_root_containment_proof: containment
    })
  });
}

function createResolver(overrides) {
  const executable = require('../governed_git_executable');
  const opts = Object.assign({
    platform: 'win32', pathDelimiter: path.delimiter,
    verifySignature: (target) => validSignature(target)
  }, overrides || {});
  return executable.create(opts);
}

function cleanup() {
  for (const root of roots.reverse()) {
    if (fs.existsSync(root)) fs.rmSync(root, { recursive: true, force: true });
  }
}

module.exports = { assert, fs, path, fixtureRoot, executableFile,
  validSignature, createResolver, cleanup };
