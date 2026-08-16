'use strict';

const assert = require('assert');
const cp = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const governed = require('../governed_git_context.js');

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
  return file === 'git' && args.some((arg) =>
    ['diff', 'ls-files', 'rev-parse'].includes(String(arg)));
}

function assertWholeSnapshotUnavailable(snapshot, label) {
  assert(snapshot.status.startsWith('[git context unavailable:'), label + ' status');
  assert.strictEqual(snapshot.stat, snapshot.status, label + ' stat must fail atomically');
  assert.strictEqual(snapshot.diff, snapshot.status, label + ' diff must fail atomically');
  assert.strictEqual(snapshot.projection_receipt, undefined, label + ' must not mint a receipt');
}

function proveSnapshotMutationBlocked(label, phase, mutate) {
  const root = newRepo(true);
  fs.writeFileSync(path.join(root, 'allowed.py'), 'changed = true\n', 'utf8');
  const originalExec = cp.execFileSync;
  let contentCalls = 0;
  let mutated = false;
  cp.execFileSync = function(file, args, options) {
    const content = isContentCommand(file, args);
    if (content) contentCalls += 1;
    if (!mutated && phase === 'before-first' && contentCalls === 1) {
      mutate(root);
      mutated = true;
    }
    const result = originalExec.apply(this, arguments);
    if (!mutated && phase === 'between' && contentCalls === 1) {
      mutate(root);
      mutated = true;
    }
    if (!mutated && phase === 'before-final' && content
      && args.includes('--ignored')) {
      mutate(root);
      mutated = true;
    }
    return result;
  };
  try {
    const snapshot = api.governedGitSnapshot(root, {
      status: 8000, stat: 8000, diff: 24000
    });
    assert(mutated, label + ' mutation hook must run');
    assertWholeSnapshotUnavailable(snapshot, label);
  } finally {
    cp.execFileSync = originalExec;
  }
}

function proveBatchMutationBlocked() {
  const root = newRepo(true);
  const originalExec = cp.execFileSync;
  let contentCalls = 0;
  cp.execFileSync = function(file, args) {
    const result = originalExec.apply(this, arguments);
    if (isContentCommand(file, args) && ++contentCalls === 1) {
      fs.appendFileSync(path.join(root, '.git', 'info', 'exclude'),
        '\nreddog-batch-race-fixture\n', 'utf8');
    }
    return result;
  };
  try {
    const outputs = api.gitOutputs(root, ['HEAD_SHA', 'TRACKED_PATHS']);
    assert.strictEqual(contentCalls, 2, 'batch must execute both governed content commands');
    assert.deepStrictEqual(outputs, [
      '[git context unavailable: Git storage changed during batch]',
      '[git context unavailable: Git storage changed during batch]'
    ], 'batch mutation must fail every projection closed');
  } finally {
    cp.execFileSync = originalExec;
  }
}

function proveNamedBatchContract() {
  const root = newRepo(true);
  assert.deepStrictEqual(api.gitOutputs(root, []),
    ['[git context unavailable: invalid named Git batch]']);
  for (const invalid of [
    ['HEAD_SHA', 'HEAD_SHA'], ['UNKNOWN'], [{ args: ['rev-parse', 'HEAD'] }],
    ['-c'], ['--version']
  ]) {
    assert(api.gitOutputs(root, invalid).every((value) =>
      value === '[git context unavailable: invalid named Git batch]'));
  }
  assert.strictEqual(api.gitOutputs(root, Array(17).fill('HEAD_SHA')).length, 16);

  const originalExec = cp.execFileSync;
  cp.execFileSync = function(file, args) {
    if (file === 'git' && args.includes('status')) throw new Error('fixture failure');
    return originalExec.apply(this, arguments);
  };
  try {
    const failed = api.gitOutputs(root, ['HEAD_SHA', 'FOUNDUP_REGISTRY_STATUS']);
    assert.strictEqual(failed.length, 2);
    assert(failed.every((value) =>
      value === '[git context unavailable: named Git batch command failed]'));
  } finally {
    cp.execFileSync = originalExec;
  }

  const names = ['HEAD_SHA', 'TRACKED_PATHS'];
  let mutated = false;
  cp.execFileSync = function(file, args) {
    const result = originalExec.apply(this, arguments);
    if (!mutated && file === 'git' && args.includes('rev-parse')) {
      names[1] = 'UNKNOWN';
      names.push('-c');
      mutated = true;
    }
    return result;
  };
  try {
    const values = api.gitOutputs(root, names);
    assert(mutated);
    assert.strictEqual(values.length, 2);
    assert(values.every((value) => !value.startsWith('[git context unavailable:')));
  } finally {
    cp.execFileSync = originalExec;
  }
}

function proveIgnoredExclusion() {
  const root = newRepo(true);
  fs.writeFileSync(path.join(root, '.gitignore'), 'cache/\nsecret.fixture\n', 'utf8');
  cp.execFileSync('git', ['add', '.gitignore'], { cwd: root });
  cp.execFileSync('git', ['-c', 'user.name=RedDog Test', '-c',
    'user.email=reddog@example.invalid', 'commit', '-qm', 'ignore policy'], { cwd: root });
  fs.mkdirSync(path.join(root, 'cache'));
  fs.writeFileSync(path.join(root, 'cache', 'ignored.txt'), 'never-return-this', 'utf8');
  fs.writeFileSync(path.join(root, 'secret.fixture'), 'never-return-this-either', 'utf8');
  const snapshot = api.governedGitSnapshot(root, { status: 8000, stat: 8000, diff: 24000 });
  assert(!snapshot.status.startsWith('[git context unavailable:'));
  assert(snapshot.projection_receipt.ignored_excluded_count >= 2);
  const serialized = JSON.stringify(snapshot);
  assert(!serialized.includes('cache/ignored.txt'));
  assert(!serialized.includes('secret.fixture'));
  assert(!serialized.includes('never-return-this'));
}

function proveIgnoredCollisionBlocked() {
  const root = newRepo(true);
  fs.writeFileSync(path.join(root, 'allowed.py'), 'changed = true\n', 'utf8');
  const originalExec = cp.execFileSync;
  cp.execFileSync = function(file, args) {
    const result = originalExec.apply(this, arguments);
    return file === 'git' && args.includes('--ignored') ? result + 'allowed.py\0' : result;
  };
  try {
    assertWholeSnapshotUnavailable(api.governedGitSnapshot(root), 'ignored/candidate collision');
  } finally {
    cp.execFileSync = originalExec;
  }
}

function snapshotWithInjectedIgnored(root, ignoredPath) {
  const originalExec = cp.execFileSync;
  cp.execFileSync = function(file, args) {
    const result = originalExec.apply(this, arguments);
    return file === 'git' && args.includes('--ignored') ? result + ignoredPath + '\0' : result;
  };
  try {
    return api.governedGitSnapshot(root);
  } finally {
    cp.execFileSync = originalExec;
  }
}

function provePlatformPathIdentityRules() {
  const caseRoot = aliasIndexRepo(['Foo.txt', 'foo.txt'], process.platform !== 'win32');
  const caseSnapshot = api.governedGitSnapshot(caseRoot);
  if (process.platform === 'win32') {
    assertWholeSnapshotUnavailable(caseSnapshot, 'Windows case-alias index');
  } else {
    assert.strictEqual(caseSnapshot.projection_receipt.changed_path_count, 2,
      'case-sensitive platforms must preserve distinct files');
  }

  const ignoredCaseRoot = newRepo(true);
  fs.writeFileSync(path.join(ignoredCaseRoot, 'allowed.py'), 'changed = true\n');
  const ignoredCase = snapshotWithInjectedIgnored(ignoredCaseRoot, 'ALLOWED.py');
  if (process.platform === 'win32') {
    assertWholeSnapshotUnavailable(ignoredCase, 'Windows ignored case alias');
  } else {
    assert(ignoredCase.projection_receipt, 'case-sensitive ignored names remain distinct');
  }

  const prefixRoot = newRepo(true);
  fs.mkdirSync(path.join(prefixRoot, 'Cache'));
  fs.writeFileSync(path.join(prefixRoot, 'Cache', 'entry.py'), 'base = true\n');
  cp.execFileSync('git', ['add', 'Cache/entry.py'], { cwd: prefixRoot });
  cp.execFileSync('git', ['-c', 'user.name=RedDog Test', '-c',
    'user.email=reddog@example.invalid', 'commit', '-qm', 'prefix fixture'], { cwd: prefixRoot });
  fs.writeFileSync(path.join(prefixRoot, 'Cache', 'entry.py'), 'changed = true\n');
  const ignoredPrefix = snapshotWithInjectedIgnored(prefixRoot, 'cache/');
  if (process.platform === 'win32') {
    assertWholeSnapshotUnavailable(ignoredPrefix, 'Windows ignored directory alias');
  } else {
    assert(ignoredPrefix.projection_receipt, 'case-sensitive ignored prefixes remain distinct');
  }
  assertWholeSnapshotUnavailable(snapshotWithInjectedIgnored(prefixRoot, 'Cache\\'),
    'ignored separator-normalized directory alias');

  const unicodeRoot = aliasIndexRepo(['caf\u00e9.txt', 'cafe\u0301.txt'], false);
  const unicodeEntries = cp.execFileSync('git', ['ls-files', '-z'], {
    cwd: unicodeRoot, encoding: 'utf8'
  }).split('\0').filter(Boolean);
  if (unicodeEntries.length === 2) {
    assertWholeSnapshotUnavailable(api.governedGitSnapshot(unicodeRoot),
      'Unicode-normalized repo-relative alias');
  }
}

function proveCanonicalFileIdentityUnique() {
  const root = aliasIndexRepo(['first.txt', 'second.txt'], true);
  const first = fs.realpathSync(path.join(root, 'first.txt'));
  const redirected = governed.create({
    isTargetReadPathDenied: () => false,
    resolveSafeRepoFile: () => ({ ok: true, full: first })
  });
  assertWholeSnapshotUnavailable(redirected.governedGitSnapshot(root),
    'duplicate canonical full-path identity');

  const hardlinkRoot = newRepo(true);
  const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-projection-hardlink-'));
  outsideRoots.push(outside);
  const outsideFile = path.join(outside, 'outside.py');
  fs.writeFileSync(outsideFile, 'outside = true\n');
  fs.linkSync(outsideFile, path.join(hardlinkRoot, 'linked.py'));
  assertWholeSnapshotUnavailable(api.governedGitSnapshot(hardlinkRoot),
    'changed hardlink identity');
}

function proveWorktreeReadMutationBlocked() {
  const root = newRepo(true);
  const file = path.join(root, 'allowed.py');
  fs.writeFileSync(file, 'first projection\n', 'utf8');
  const originalRead = fs.readFileSync;
  let mutated = false;
  fs.readFileSync = function(target) {
    const result = originalRead.apply(this, arguments);
    if (!mutated && typeof target === 'number') {
      fs.writeFileSync(file, 'second projection\n', 'utf8');
      mutated = true;
    }
    return result;
  };
  try {
    assertWholeSnapshotUnavailable(api.governedGitSnapshot(root), 'mutation during stable read');
    assert(mutated);
  } finally {
    fs.readFileSync = originalRead;
  }
}

function proveSecondEnumerationMutation(label, mutate) {
  const root = newRepo(true);
  fs.writeFileSync(path.join(root, 'allowed.py'), 'changed = true\n', 'utf8');
  const originalExec = cp.execFileSync;
  let enumerations = 0;
  cp.execFileSync = function(file, args) {
    if (file === 'git' && args.includes('ls-files') && args.includes('-v')
      && ++enumerations === 2) mutate(root, originalExec);
    return originalExec.apply(this, arguments);
  };
  try {
    assertWholeSnapshotUnavailable(api.governedGitSnapshot(root), label);
    assert.strictEqual(enumerations, 2, label + ' must reach the second enumeration');
  } finally {
    cp.execFileSync = originalExec;
  }
}

function proveIgnoredJunctionNotTraversed() {
  const root = newRepo(true);
  const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-ignored-outside-'));
  outsideRoots.push(outside);
  fs.writeFileSync(path.join(outside, 'sentinel.txt'), 'IGNORED_OUTSIDE_SENTINEL', 'utf8');
  fs.writeFileSync(path.join(root, '.gitignore'), 'ignored-link/\n', 'utf8');
  cp.execFileSync('git', ['add', '.gitignore'], { cwd: root });
  cp.execFileSync('git', ['-c', 'user.name=RedDog Test', '-c',
    'user.email=reddog@example.invalid', 'commit', '-qm', 'ignore link'], { cwd: root });
  const link = path.join(root, 'ignored-link');
  fs.symlinkSync(outside, link, process.platform === 'win32' ? 'junction' : 'dir');
  try {
    const snapshot = api.governedGitSnapshot(root);
    assert(snapshot.projection_receipt, 'ignored junction must not make snapshot unavailable');
    assert(snapshot.projection_receipt.ignored_excluded_count >= 1);
    assert(!JSON.stringify(snapshot).includes('IGNORED_OUTSIDE_SENTINEL'));
  } finally {
    fs.unlinkSync(link);
  }
}

function proveFactoryInstanceIsolation() {
  const root = newRepo(true);
  fs.writeFileSync(path.join(root, 'allowed.py'), 'changed = true\n', 'utf8');
  const allow = { isTargetReadPathDenied: () => false, resolveSafeRepoFile: safeResolve };
  const deny = { isTargetReadPathDenied: () => true, resolveSafeRepoFile: safeResolve };
  const defaultBefore = governed.governedGitSnapshot(root);
  const allowApi = governed.create(allow);
  const denyApi = governed.create(deny);
  assert.strictEqual(allowApi.governedGitSnapshot(root).projection_receipt.changed_path_count, 1);
  assert.strictEqual(denyApi.governedGitSnapshot(root).projection_receipt.changed_path_count, 0);
  assert.strictEqual(allowApi.governedGitSnapshot(root).projection_receipt.changed_path_count, 1);
  const denyFirst = governed.create(deny);
  const allowSecond = governed.create(allow);
  const third = governed.create(allow);
  assert.strictEqual(denyFirst.governedGitSnapshot(root).projection_receipt.changed_path_count, 0);
  assert.strictEqual(allowSecond.governedGitSnapshot(root).projection_receipt.changed_path_count, 1);
  assert.strictEqual(third.governedGitSnapshot(root).projection_receipt.changed_path_count, 1);
  allow.isTargetReadPathDenied = () => true;
  assert.strictEqual(allowApi.governedGitSnapshot(root).projection_receipt.changed_path_count, 1);
  assert(governed.create({}).governedGitStatus(root, 8000).startsWith('[git context unavailable:'));
  const bad = new Proxy({}, { get: () => { throw new Error('bad factory'); } });
  assert(governed.create(bad).governedGitStatus(root, 8000).startsWith('[git context unavailable:'));
  const defaultAfter = governed.governedGitSnapshot(root);
  assert.strictEqual(defaultAfter.status, defaultBefore.status);
  assert.strictEqual(defaultAfter.stat, defaultBefore.stat);
  assert.strictEqual(defaultAfter.diff, defaultBefore.diff);
  assert.strictEqual(defaultAfter.projection_receipt.path_set_digest,
    defaultBefore.projection_receipt.path_set_digest);
  assert.strictEqual(defaultAfter.projection_receipt.content_digest,
    defaultBefore.projection_receipt.content_digest);
  assert.strictEqual(defaultAfter.projection_receipt.root_digest,
    allowApi.governedGitSnapshot(root).projection_receipt.root_digest);
  const other = newRepo(true);
  fs.writeFileSync(path.join(other, 'allowed.py'), 'other = true\n', 'utf8');
  assert.notStrictEqual(allowApi.governedGitSnapshot(root).projection_receipt.root_digest,
    allowApi.governedGitSnapshot(other).projection_receipt.root_digest);
}

function proveFinalReceiptIsAbsoluteLastRead() {
  const root = newRepo(true);
  fs.writeFileSync(path.join(root, 'allowed.py'), 'changed = true\n', 'utf8');
  const originalRead = fs.readFileSync;
  let contentReads = 0;
  fs.readFileSync = function(target) {
    const result = originalRead.apply(this, arguments);
    if (typeof target === 'number' && ++contentReads === 3) {
      fs.appendFileSync(path.join(root, '.git', 'info', 'exclude'), '\nr6-late-control\n');
    }
    return result;
  };
  try {
    assertWholeSnapshotUnavailable(api.governedGitSnapshot(root),
      'Git control mutation during final capture');
    assert.strictEqual(contentReads, 3);
  } finally {
    fs.readFileSync = originalRead;
  }

  const orderRoot = newRepo(true);
  fs.writeFileSync(path.join(orderRoot, 'allowed.py'), 'changed = true\n', 'utf8');
  const originalLstat = fs.lstatSync;
  const originalExec = cp.execFileSync;
  let receipts = 0;
  let finalProofStarted = false;
  let protectedReadAfterFinal = false;
  fs.lstatSync = function(target) {
    const resolved = path.resolve(String(target));
    if (resolved === path.join(orderRoot, '.git') && ++receipts === 3) finalProofStarted = true;
    if (finalProofStarted && !resolved.startsWith(path.join(orderRoot, '.git'))) {
      protectedReadAfterFinal = true;
    }
    return originalLstat.apply(this, arguments);
  };
  fs.readFileSync = function(target) {
    if (finalProofStarted && typeof target === 'number') protectedReadAfterFinal = true;
    return originalRead.apply(this, arguments);
  };
  cp.execFileSync = function(file) {
    if (finalProofStarted && file === 'git') protectedReadAfterFinal = true;
    return originalExec.apply(this, arguments);
  };
  try {
    const snapshot = api.governedGitSnapshot(orderRoot);
    assert(snapshot.projection_receipt);
    assert.strictEqual(receipts, 3);
    assert.strictEqual(protectedReadAfterFinal, false);
  } finally {
    fs.lstatSync = originalLstat;
    fs.readFileSync = originalRead;
    cp.execFileSync = originalExec;
  }
  fs.writeFileSync(path.join(orderRoot, 'allowed.py'), 'post-proof point in time\n', 'utf8');
}

function proveCachedHardlinkRevalidation() {
  const root = newRepo(false);
  assert(!api.governedGitStatus(root, 8000).includes('[git context unavailable:'));
  hardlinkOutside(root, firstLooseObject(root), 'loose-object-link');
  assertBlocked(root, 'cached loose-object hardlink mutation');
}

function proveBoundControlFile(relativePath, setup) {
  const root = newRepo(relativePath === 'shallow');
  const control = path.join(root, '.git', ...relativePath.split('/'));
  fs.mkdirSync(path.dirname(control), { recursive: true });
  if (setup) setup(root, control);
  else fs.writeFileSync(control, 'synthetic\n', 'utf8');
  assert(!api.governedGitStatus(root, 8000).includes('[git context unavailable:'));
  hardlinkOutside(root, control, relativePath.replace('/', '-'));
  assertBlocked(root, relativePath + ' hardlink mutation');
}

try {
  provePlatformPathIdentityRules();
  proveCanonicalFileIdentityUnique();
  proveFactoryInstanceIsolation();
  proveFinalReceiptIsAbsoluteLastRead();
  proveNamedBatchContract();
  proveIgnoredExclusion();
  proveIgnoredCollisionBlocked();
  proveIgnoredJunctionNotTraversed();
  proveWorktreeReadMutationBlocked();
  proveSecondEnumerationMutation('new path during second enumeration', (root) => {
    fs.writeFileSync(path.join(root, 'new.py'), 'new = true\n', 'utf8');
  });
  proveSecondEnumerationMutation('removed path during second enumeration', (root) => {
    fs.unlinkSync(path.join(root, 'allowed.py'));
  });
  proveSecondEnumerationMutation('renamed path during second enumeration', (root) => {
    fs.renameSync(path.join(root, 'allowed.py'), path.join(root, 'renamed.py'));
  });
  proveSecondEnumerationMutation('index change during second enumeration',
    (root, originalExec) => originalExec('git', ['add', 'allowed.py'], { cwd: root }));
  proveCachedHardlinkRevalidation();
  for (const name of ['info/attributes', 'info/exclude']) {
    proveBoundControlFile(name);
  }
  proveBoundControlFile('shallow', (root, control) => {
    const head = cp.execFileSync('git', ['rev-parse', 'HEAD'], {
      cwd: root, encoding: 'utf8'
    }).trim();
    fs.writeFileSync(control, head + '\n', 'ascii');
  });

  proveSnapshotMutationBlocked('HEAD hardlink before first content command',
    'before-first', (root) => {
      hardlinkOutside(root, path.join(root, '.git', 'HEAD'), 'snapshot-head-link');
    });
  proveSnapshotMutationBlocked('config hardlink between content commands',
    'between', (root) => {
      hardlinkOutside(root, path.join(root, '.git', 'config'), 'snapshot-config-link');
    });
  proveSnapshotMutationBlocked('exclude mutation immediately before final validation',
    'before-final', (root) => {
      fs.appendFileSync(path.join(root, '.git', 'info', 'exclude'),
        '\nreddog-race-fixture\n', 'utf8');
    });
  proveBatchMutationBlocked();

  const graftRoot = newRepo(true);
  fs.writeFileSync(path.join(graftRoot, '.git', 'info', 'grafts'),
    '0'.repeat(40) + '\n', 'ascii');
  assertBlocked(graftRoot, 'legacy graft control');

  const configRoot = newRepo(false);
  assert(!api.governedGitStatus(configRoot, 8000).includes('[git context unavailable:'));
  hardlinkOutside(configRoot, path.join(configRoot, '.git', 'config'), 'config-link');
  assertBlocked(configRoot, 'config hardlink mutation');

  const worktreeConfigRoot = newRepo(false);
  cp.execFileSync('git', ['config', 'extensions.worktreeConfig', 'true'], {
    cwd: worktreeConfigRoot
  });
  cp.execFileSync('git', ['config', '--worktree', 'reddog.fixture', 'true'], {
    cwd: worktreeConfigRoot
  });
  assert(!api.governedGitStatus(worktreeConfigRoot, 8000)
    .includes('[git context unavailable:'));
  hardlinkOutside(worktreeConfigRoot,
    path.join(worktreeConfigRoot, '.git', 'config.worktree'), 'worktree-config-link');
  assertBlocked(worktreeConfigRoot, 'config.worktree hardlink mutation');

  const argvRoot = newRepo(false);
  const calls = [];
  const originalExec = cp.execFileSync;
  cp.execFileSync = function(file, args, options) {
    calls.push({ file, args: Array.from(args || []), options });
    return originalExec.apply(this, arguments);
  };
  try {
    assert(!api.governedGitStatus(argvRoot, 8000).includes('[git context unavailable:'));
  } finally {
    cp.execFileSync = originalExec;
  }
  const readiness = api.governedGitReadiness(argvRoot);
  assert.strictEqual(readiness.ownership_mismatch_observed, false);
  assert.strictEqual(readiness.safe_directory_override_applied, false);
  assert.strictEqual(readiness.safe_directory_scope, 'none');
  const contentCalls = calls.filter((call) =>
    call.args.some((arg) => ['diff', 'ls-files', 'rev-parse'].includes(arg)));
  assert(contentCalls.length > 0);
  const nullPath = '/dev/null';
  for (const call of contentCalls) {
    assert(!call.args.some((arg) => String(arg).startsWith('safe.directory=')),
      'owned-repo content command must not apply an undisclosed override');
    assert(call.args.includes('--no-optional-locks'));
    assert(call.args.includes('core.hooksPath=' + nullPath));
    assert(call.args.includes('core.attributesFile=' + nullPath));
    assert(call.args.includes('core.excludesFile=' + nullPath));
    assert.strictEqual(call.options.env.GIT_EXTERNAL_DIFF, '');
  }
} finally {
  for (const link of outsideLinks) {
    if (fs.existsSync(link)) fs.unlinkSync(link);
  }
  for (const root of roots) {
    fs.rmSync(root, { recursive: true, force: true });
  }
  for (const root of outsideRoots) {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

console.log('RedDog governed Git storage/control hardening contracts: PASS');
