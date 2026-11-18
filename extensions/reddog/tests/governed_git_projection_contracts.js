'use strict';

const { assert, cp, fs, os, path, governed, roots, outsideRoots, api, safeResolve,
  newRepo, aliasIndexRepo, assertWholeSnapshotUnavailable, isContentCommand,
  isGitExecutable, cleanup } = require('./governed_git_test_helpers.js');

function installSnapshotMutationHook(root, phase, mutate) {
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
  return { originalExec, mutated: () => mutated };
}

function proveSnapshotMutationBlocked(label, phase, mutate) {
  const root = newRepo(true);
  fs.writeFileSync(path.join(root, 'allowed.py'), 'changed = true\n', 'utf8');
  const hook = installSnapshotMutationHook(root, phase, mutate);
  try {
    const snapshot = api.governedGitSnapshot(root, {
      status: 8000, stat: 8000, diff: 24000
    });
    assert(hook.mutated(), label + ' mutation hook must run');
    assertWholeSnapshotUnavailable(snapshot, label);
  } finally {
    cp.execFileSync = hook.originalExec;
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
    assert.strictEqual(contentCalls, 4,
      'batch must execute the immutable operation list twice');
    assert.deepStrictEqual(outputs, [
      '[git context unavailable: Git storage changed during batch]',
      '[git context unavailable: Git storage changed during batch]'
    ], 'batch mutation must fail every projection closed');
  } finally {
    cp.execFileSync = originalExec;
  }
}

function proveNamedBatchValidation(root) {
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
}

function proveNamedBatchCommandFailure(root) {
  const originalExec = cp.execFileSync;
  cp.execFileSync = function(file, args) {
    if (isGitExecutable(file) && args.includes('status')) throw new Error('fixture failure');
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
}

function proveNamedBatchInputSnapshot(root) {
  const originalExec = cp.execFileSync;
  const names = ['HEAD_SHA', 'TRACKED_PATHS'];
  let mutated = false;
  cp.execFileSync = function(file, args) {
    const result = originalExec.apply(this, arguments);
    if (!mutated && isGitExecutable(file) && args.includes('rev-parse')) {
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

function proveNamedBatchContract() {
  const root = newRepo(true);
  proveNamedBatchValidation(root);
  proveNamedBatchCommandFailure(root);
  proveNamedBatchInputSnapshot(root);
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
    return isGitExecutable(file) && args.includes('--ignored') ? result + 'allowed.py\0' : result;
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
    return isGitExecutable(file) && args.includes('--ignored') ? result + ignoredPath + '\0' : result;
  };
  try {
    return api.governedGitSnapshot(root);
  } finally {
    cp.execFileSync = originalExec;
  }
}

function proveCaseIdentityRules() {
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
}

function provePrefixIdentityRules() {
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
}

function proveUnicodeIdentityRules() {
  const unicodeRoot = aliasIndexRepo(['caf\u00e9.txt', 'cafe\u0301.txt'], false);
  const unicodeEntries = cp.execFileSync('git', ['ls-files', '-z'], {
    cwd: unicodeRoot, encoding: 'utf8'
  }).split('\0').filter(Boolean);
  if (unicodeEntries.length === 2) {
    assertWholeSnapshotUnavailable(api.governedGitSnapshot(unicodeRoot),
      'Unicode-normalized repo-relative alias');
  }
}

function provePlatformPathIdentityRules() {
  proveCaseIdentityRules();
  provePrefixIdentityRules();
  proveUnicodeIdentityRules();
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

function nestedDeletionRepo(relative) {
  const root = newRepo(true);
  const full = path.join(root, ...relative.split('/'));
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, 'tracked nested content\n', 'utf8');
  cp.execFileSync('git', ['add', relative], { cwd: root });
  cp.execFileSync('git', ['-c', 'user.name=RedDog Test', '-c',
    'user.email=reddog@example.invalid', 'commit', '-qm', 'nested fixture'], { cwd: root });
  fs.unlinkSync(full);
  return { root, full };
}

function directoryLink(target, link) {
  fs.symlinkSync(target, link, process.platform === 'win32' ? 'junction' : 'dir');
}

function proveNestedDeletionAccepted() {
  const fixture = nestedDeletionRepo('nested/tracked.txt');
  const snapshot = api.governedGitSnapshot(fixture.root);
  assert(snapshot.projection_receipt, 'ordinary nested deletion must mint a receipt');
  assert(snapshot.status.includes('D  nested/tracked.txt'));
  assert(snapshot.diff.includes('diff --reddog-deleted nested/tracked.txt'));
}

function proveDanglingParentRejected() {
  const fixture = nestedDeletionRepo('linked/tracked.txt');
  fs.rmdirSync(path.dirname(fixture.full));
  const missing = path.join(os.tmpdir(), 'reddog-missing-parent-' + Date.now());
  directoryLink(missing, path.join(fixture.root, 'linked'));
  assertWholeSnapshotUnavailable(api.governedGitSnapshot(fixture.root),
    'tracked deletion below dangling parent');
}

function proveDanglingFinalRejected() {
  const fixture = nestedDeletionRepo('dangling.txt');
  const missing = path.join(os.tmpdir(), 'reddog-missing-final-' + Date.now());
  directoryLink(missing, fixture.full);
  assertWholeSnapshotUnavailable(api.governedGitSnapshot(fixture.root),
    'tracked dangling final path');
}

function proveNonDirectoryParentRejected() {
  const fixture = nestedDeletionRepo('blocked/tracked.txt');
  fs.rmdirSync(path.dirname(fixture.full));
  fs.writeFileSync(path.join(fixture.root, 'blocked'), 'not a directory\n', 'utf8');
  assertWholeSnapshotUnavailable(api.governedGitSnapshot(fixture.root),
    'tracked deletion below non-directory parent');
}

function proveParentLookupErrorRejected() {
  const fixture = nestedDeletionRepo('unreadable/tracked.txt');
  const parent = path.dirname(fixture.full);
  const originalLstat = fs.lstatSync;
  fs.lstatSync = function(target) {
    if (path.resolve(String(target)) === parent) {
      const err = new Error('synthetic parent lookup failure'); err.code = 'EACCES'; throw err;
    }
    return originalLstat.apply(this, arguments);
  };
  try {
    assertWholeSnapshotUnavailable(api.governedGitSnapshot(fixture.root),
      'tracked deletion with parent lookup error');
  } finally { fs.lstatSync = originalLstat; }
}

function proveUntrackedAbsentRejected() {
  const root = newRepo(true);
  const originalExec = cp.execFileSync;
  cp.execFileSync = function(file, args) {
    const result = originalExec.apply(this, arguments);
    return isGitExecutable(file) && args.includes('ls-files') && args.includes('--others')
      && !args.includes('--ignored') ? result + 'ghost.txt\0' : result;
  };
  try {
    assertWholeSnapshotUnavailable(api.governedGitSnapshot(root), 'absent untracked path');
  } finally { cp.execFileSync = originalExec; }
}

function proveParentMutationRejected() {
  const fixture = nestedDeletionRepo('moving/deeper/tracked.txt');
  const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-parent-race-'));
  outsideRoots.push(outside); fs.mkdirSync(path.join(outside, 'deeper'));
  const parent = path.join(fixture.root, 'moving');
  const saved = path.join(fixture.root, 'moving-saved');
  const deeper = path.join(parent, 'deeper');
  const originalExists = fs.existsSync; const originalLstat = fs.lstatSync;
  let mutated = false;
  const mutate = () => {
    if (mutated) return; fs.renameSync(parent, saved); directoryLink(outside, parent); mutated = true;
  };
  fs.existsSync = function(target) { if (path.resolve(String(target)) === fixture.full) mutate();
    return originalExists.apply(this, arguments); };
  fs.lstatSync = function(target) { if (path.resolve(String(target)) === deeper) mutate();
    return originalLstat.apply(this, arguments); };
  try { assertWholeSnapshotUnavailable(api.governedGitSnapshot(fixture.root),
    'parent substitution between component checks'); assert(mutated); }
  finally { fs.existsSync = originalExists; fs.lstatSync = originalLstat; }
}

function run() {
  provePlatformPathIdentityRules();
  proveCanonicalFileIdentityUnique();
  proveNestedDeletionAccepted();
  proveDanglingParentRejected();
  proveDanglingFinalRejected();
  proveNonDirectoryParentRejected();
  proveParentLookupErrorRejected();
  proveUntrackedAbsentRejected();
  proveParentMutationRejected();
  proveNamedBatchContract();
  proveIgnoredExclusion();
  proveIgnoredCollisionBlocked();
}

if (require.main === module) {
  try { run(); } finally { cleanup(); }
  console.log('RedDog governed Git projection identity contracts: PASS');
}

module.exports = { run, proveSnapshotMutationBlocked, proveBatchMutationBlocked,
  proveNamedBatchContract, proveIgnoredExclusion, proveIgnoredCollisionBlocked,
  provePlatformPathIdentityRules, proveCanonicalFileIdentityUnique,
  proveNestedDeletionAccepted, proveDanglingParentRejected, proveDanglingFinalRejected,
  proveNonDirectoryParentRejected, proveParentLookupErrorRejected,
  proveUntrackedAbsentRejected, proveParentMutationRejected };
