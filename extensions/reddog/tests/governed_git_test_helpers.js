'use strict';

const assert = require('assert');
const cp = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const governed = require('../governed_git_context.js');
const gitStorage = require('../governed_git_storage.js');

const outsideLinks = [];
const outsideRoots = [];
const roots = [];
function safeResolve(root, relPath) {
  try {
    const full = fs.realpathSync(path.resolve(root, relPath));
    const base = fs.realpathSync(root);
    const metadata = fs.lstatSync(full);
    return full.startsWith(base + path.sep) && metadata.isFile()
      && !metadata.isSymbolicLink() && metadata.nlink === 1
      ? { ok: true, full } : { ok: false };
  } catch (err) {
    return { ok: false };
  }
}
const api = governed.create({
  isTargetReadPathDenied: () => false,
  resolveSafeRepoFile: safeResolve,
  readBoundedRepoFile: () => ''
});

function newRepo(commit) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-git-controls-'));
  roots.push(root);
  cp.execFileSync('git', ['init', '-q'], { cwd: root });
  cp.execFileSync('git', ['config', 'core.autocrlf', 'false'], { cwd: root });
  fs.writeFileSync(path.join(root, 'allowed.py'), 'allowed = true\n', 'utf8');
  cp.execFileSync('git', ['add', 'allowed.py'], { cwd: root });
  if (commit) {
    cp.execFileSync('git', ['-c', 'user.name=RedDog Test', '-c',
      'user.email=reddog@example.invalid', 'commit', '-qm', 'fixture'], { cwd: root });
  }
  return root;
}

function aliasIndexRepo(paths, createAll) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-git-alias-'));
  roots.push(root);
  cp.execFileSync('git', ['init', '-q'], { cwd: root });
  cp.execFileSync('git', ['config', 'core.autocrlf', 'false'], { cwd: root });
  fs.writeFileSync(path.join(root, paths[0]), 'one physical identity\n', 'utf8');
  const oid = cp.execFileSync('git', ['hash-object', '-w', paths[0]], {
    cwd: root, encoding: 'utf8'
  }).trim();
  for (const relPath of paths) {
    if (createAll && relPath !== paths[0]) {
      fs.writeFileSync(path.join(root, relPath), 'second physical identity\n', 'utf8');
    }
    cp.execFileSync('git', ['update-index', '--add', '--cacheinfo',
      `100644,${oid},${relPath}`], { cwd: root });
  }
  return root;
}

function hardlinkOutside(root, source, label) {
  const target = root + '-' + label;
  fs.linkSync(source, target);
  outsideLinks.push(target);
}

function assertBlocked(root, label) {
  assert(
    api.governedGitStatus(root, 8000).includes('[git context unavailable:'),
    label + ' must fail closed'
  );
}

function firstLooseObject(root) {
  const objects = path.join(root, '.git', 'objects');
  for (const name of fs.readdirSync(objects)) {
    const directory = path.join(objects, name);
    if (name.length !== 2 || !fs.statSync(directory).isDirectory()) continue;
    const entries = fs.readdirSync(directory);
    if (entries.length) return path.join(directory, entries[0]);
  }
  throw new Error('loose object fixture missing');
}

function isContentCommand(file, args) {
  return isGitExecutable(file) && args.some((arg) =>
    ['diff', 'ls-files', 'rev-parse'].includes(String(arg)));
}

function isGitExecutable(file) {
  return /^git(?:\.exe)?$/i.test(path.basename(file));
}

function linkedRepo() {
  const main = newRepo(true);
  const linked = main + '-linked-authority';
  cp.execFileSync('git', ['worktree', 'add', '-q', '-b',
    'reddog-linked-authority', linked], { cwd: main });
  roots.push(linked);
  const admin = cp.execFileSync('git', ['rev-parse', '--absolute-git-dir'], {
    cwd: linked, encoding: 'utf8'
  }).trim();
  return { main, linked, admin, common: path.join(main, '.git') };
}

function batchUnavailable(values, reason) {
  assert(values.length > 0, reason + ' must retain batch shape');
  assert(values.every((value) => value.startsWith('[git context unavailable:')),
    reason + ' must fail the whole batch closed');
}

function commitFile(root, relativePath, content, message, runner) {
  const execute = runner || cp.execFileSync;
  fs.writeFileSync(path.join(root, relativePath), content, 'utf8');
  execute('git', ['add', relativePath], { cwd: root });
  execute('git', ['-c', 'user.name=RedDog Test', '-c',
    'user.email=reddog@example.invalid', 'commit', '-qm', message], { cwd: root });
}

function assertWholeSnapshotUnavailable(snapshot, label) {
  assert(snapshot.status.startsWith('[git context unavailable:'), label + ' status');
  assert.strictEqual(snapshot.stat, snapshot.status, label + ' stat must fail atomically');
  assert.strictEqual(snapshot.diff, snapshot.status, label + ' diff must fail atomically');
  assert.strictEqual(snapshot.projection_receipt, undefined, label + ' must not mint a receipt');
}

function cleanup() {
  for (const link of outsideLinks) {
    if (fs.existsSync(link)) fs.unlinkSync(link);
  }
  for (const root of roots.reverse()) {
    if (fs.existsSync(root)) fs.rmSync(root, { recursive: true, force: true });
  }
  for (const root of outsideRoots.reverse()) {
    if (fs.existsSync(root)) fs.rmSync(root, { recursive: true, force: true });
  }
}

module.exports = { assert, cp, fs, os, path, governed, gitStorage, outsideLinks,
  outsideRoots, roots, api, safeResolve, newRepo, aliasIndexRepo, hardlinkOutside,
  assertBlocked, firstLooseObject, isContentCommand, linkedRepo, batchUnavailable,
  isGitExecutable, commitFile, assertWholeSnapshotUnavailable, cleanup };
