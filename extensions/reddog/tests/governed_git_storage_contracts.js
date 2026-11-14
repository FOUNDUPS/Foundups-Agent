'use strict';

const { assert, cp, fs, path, api, gitStorage, newRepo, hardlinkOutside, firstLooseObject, isContentCommand, linkedRepo, commitFile, cleanup } = require('./governed_git_test_helpers.js');

function proveUnrelatedLooseObjectHardlinkSurvives() {
  const root = newRepo(false);
  assert(!api.governedGitStatus(root, 8000).includes('[git context unavailable:'));
  hardlinkOutside(root, firstLooseObject(root), 'loose-object-link');
  assert(!api.governedGitStatus(root, 8000).includes('[git context unavailable:'),
    'ordinary reads do not claim global unrelated-object hygiene');
}

function applySharedStoreChurn(fixture, originalExec) {
  commitFile(fixture.main, 'sibling.txt', 'safe sibling commit\n',
    'sibling churn', originalExec);
  fs.writeFileSync(path.join(fixture.common, 'config.worktree'),
    '[reddog]\nmainOnly = true\n', 'utf8');
  const replacement = originalExec('git', ['rev-parse', 'HEAD'], {
    cwd: fixture.main, encoding: 'utf8'
  }).trim();
  const authority = originalExec('git', ['rev-parse', 'HEAD'], {
    cwd: fixture.linked, encoding: 'utf8'
  }).trim();
  originalExec('git', ['update-ref', 'refs/replace/' + authority, replacement], {
    cwd: fixture.main
  });
  originalExec('git', ['tag', 'unrelated-r9'], { cwd: fixture.main });
  originalExec('git', ['pack-refs', '--include', 'refs/tags/unrelated-r9'], {
    cwd: fixture.main
  });
}

function installSharedStoreChurn(fixture) {
  const originalExec = cp.execFileSync;
  let contentCalls = 0;
  let churned = false;
  cp.execFileSync = function(file, args) {
    const result = originalExec.apply(this, arguments);
    if (isContentCommand(file, args)) contentCalls += 1;
    if (!churned && contentCalls === 1) {
      applySharedStoreChurn(fixture, originalExec);
      churned = true;
    }
    return result;
  };
  return { originalExec, churned: () => churned, calls: () => contentCalls };
}

function proveLinkedSharedStoreChurnSurvives() {
  const fixture = linkedRepo();
  cp.execFileSync('git', ['config', 'extensions.worktreeConfig', 'true'], {
    cwd: fixture.main
  });
  const hook = installSharedStoreChurn(fixture);
  try {
    const values = api.gitOutputs(fixture.linked, ['HEAD_SHA', 'TRACKED_PATHS']);
    assert.strictEqual(hook.churned(), true);
    assert.strictEqual(hook.calls(), 4, 'safe churn batch must complete both passes');
    assert(!values.some((value) => value.startsWith('[git context unavailable:')),
      'unrelated shared-store/main-worktree churn must not invalidate authority');
    assert(values[1].split(/\r?\n/).includes('allowed.py'));
  } finally {
    cp.execFileSync = hook.originalExec;
  }
}

function proveLinkedSnapshotSurvivesSiblingCommit() {
  const fixture = linkedRepo();
  fs.writeFileSync(path.join(fixture.linked, 'allowed.py'), 'linked change\n', 'utf8');
  const originalExec = cp.execFileSync;
  let churned = false;
  cp.execFileSync = function(file, args) {
    const result = originalExec.apply(this, arguments);
    if (!churned && isContentCommand(file, args)) {
      commitFile(fixture.main, 'sibling-snapshot.txt', 'sibling snapshot\n',
        'snapshot sibling churn', originalExec);
      churned = true;
    }
    return result;
  };
  try {
    const snapshot = api.governedGitSnapshot(fixture.linked);
    assert.strictEqual(churned, true);
    assert(snapshot.projection_receipt,
      'stable linked projection must survive unrelated sibling commit');
    assert(snapshot.diff.includes('linked change'));
  } finally {
    cp.execFileSync = originalExec;
  }
}

function proveNoRecursiveSharedStoreTraversal() {
  const fixture = linkedRepo();
  const originalOpen = fs.opendirSync;
  fs.opendirSync = function(target) {
    const resolved = path.resolve(String(target));
    if (resolved.startsWith(path.join(fixture.common, 'objects'))
      || resolved.startsWith(path.join(fixture.common, 'refs'))) {
      throw new Error('recursive shared-store traversal forbidden');
    }
    return originalOpen.apply(this, arguments);
  };
  try {
    const values = api.gitOutputs(fixture.linked, ['HEAD_SHA', 'TRACKED_PATHS']);
    assert(!values.some((value) => value.startsWith('[git context unavailable:')),
      'authority receipts must not recursively traverse shared objects or refs');
  } finally {
    fs.opendirSync = originalOpen;
  }
}

function growingControlState(control) {
  return { control, handle: null, openedSize: null, requested: 0, accepted: 0,
    unbounded: false, grew: false, originalOpen: fs.openSync,
    originalFstat: fs.fstatSync, originalReadFile: fs.readFileSync,
    originalRead: fs.readSync, originalClose: fs.closeSync };
}

function growControl(state) {
  if (state.grew) return;
  fs.appendFileSync(state.control, Buffer.alloc((1024 * 1024) + 4096, 0x78));
  state.grew = true;
}

function installGrowingControlHooks(state) {
  fs.openSync = function(target, flags) {
    const handle = state.originalOpen.apply(this, arguments);
    if (path.resolve(String(target)) === state.control && flags === 'r') state.handle = handle;
    return handle;
  };
  fs.fstatSync = function(handle) {
    const metadata = state.originalFstat.apply(this, arguments);
    if (handle === state.handle && state.openedSize === null) state.openedSize = metadata.size;
    return metadata;
  };
  fs.readFileSync = function(target) {
    if (target === state.handle) { state.unbounded = true; growControl(state); }
    const result = state.originalReadFile.apply(this, arguments);
    if (target === state.handle) state.accepted += result.length;
    return result;
  };
}

function installGrowingReadHooks(state) {
  fs.readSync = function(handle, buffer, offset, length) {
    if (handle === state.handle) { growControl(state); state.requested += length; }
    const count = state.originalRead.apply(this, arguments);
    if (handle === state.handle) state.accepted += count;
    return count;
  };
  fs.closeSync = function(handle) {
    const result = state.originalClose.apply(this, arguments);
    if (handle === state.handle) state.handle = null;
    return result;
  };
}

function restoreGrowingControlHooks(state) {
  fs.openSync = state.originalOpen;
  fs.fstatSync = state.originalFstat;
  fs.readFileSync = state.originalReadFile;
  fs.readSync = state.originalRead;
  fs.closeSync = state.originalClose;
}

function proveGrowingControlReadIsLengthBounded() {
  const root = newRepo(true);
  const control = path.join(root, '.git', 'info', 'exclude');
  fs.writeFileSync(control, 'bounded\n', 'ascii');
  const state = growingControlState(control);
  installGrowingControlHooks(state);
  installGrowingReadHooks(state);
  try {
    const receipt = gitStorage.registeredGitMetadataReceipt(root);
    assert.strictEqual(state.grew, true, 'control must grow after the opened size is captured');
    assert.strictEqual(receipt.valid, false, 'control growth must fail the receipt closed');
    assert.strictEqual(state.unbounded, false,
      'stable controls must not use an unbounded fd read');
    assert(state.requested <= state.openedSize,
      'fd read requests must not exceed the opened control size');
    assert(state.accepted <= state.openedSize,
      'accepted control bytes must not exceed the opened control size');
    assert(state.accepted <= 1024 * 1024,
      'accepted info/exclude bytes must not exceed its name-specific cap');
  } finally {
    restoreGrowingControlHooks(state);
  }
}

function installControlReadHook(control, onRead) {
  const originalOpen = fs.openSync;
  const originalRead = fs.readSync;
  const originalClose = fs.closeSync;
  let controlHandle = null;
  fs.openSync = function(target, flags) {
    const handle = originalOpen.apply(this, arguments);
    if (path.resolve(String(target)) === control && flags === 'r') controlHandle = handle;
    return handle;
  };
  fs.readSync = function(handle) {
    if (handle === controlHandle && onRead()) return 0;
    return originalRead.apply(this, arguments);
  };
  fs.closeSync = function(handle) {
    const result = originalClose.apply(this, arguments);
    if (handle === controlHandle) controlHandle = null;
    return result;
  };
  return () => {
    fs.openSync = originalOpen;
    fs.readSync = originalRead;
    fs.closeSync = originalClose;
  };
}

function proveIncompleteControlReadIsRejected() {
  const root = newRepo(true);
  const control = path.join(root, '.git', 'info', 'exclude');
  fs.writeFileSync(control, 'short-read\n', 'ascii');
  let interrupted = false;
  const restore = installControlReadHook(control, () => {
    if (interrupted) return false;
    interrupted = true;
    return true;
  });
  try {
    assert.strictEqual(gitStorage.registeredGitMetadataReceipt(root).valid, false,
      'zero-byte completion before the opened size must fail closed');
    assert.strictEqual(interrupted, true, 'short-read fixture must reach the fd reader');
  } finally {
    restore();
  }
}

function proveControlPathSubstitutionIsRejected() {
  const root = newRepo(true);
  const control = path.join(root, '.git', 'info', 'exclude');
  const displaced = control + '.r9-original';
  fs.writeFileSync(control, 'original\n', 'ascii');
  let substituted = false;
  const restore = installControlReadHook(control, () => {
    if (substituted) return false;
    fs.renameSync(control, displaced);
    fs.writeFileSync(control, 'replaced\n', 'ascii');
    substituted = true;
    return false;
  });
  try {
    assert.strictEqual(gitStorage.registeredGitMetadataReceipt(root).valid, false,
      'path substitution during an fd read must fail closed');
    assert.strictEqual(substituted, true, 'substitution fixture must reach the fd reader');
  } finally {
    restore();
  }
}

function proveMalformedUnrelatedPackedRefBoundary() {
  const root = newRepo(true);
  cp.execFileSync('git', ['tag', 'unrelated-packed-r9'], { cwd: root });
  cp.execFileSync('git', ['pack-refs', '--all', '--prune'], { cwd: root });
  fs.appendFileSync(path.join(root, '.git', 'packed-refs'),
    'malformed-unrelated-packed-ref-line\n', 'ascii');
  assert.strictEqual(gitStorage.registeredGitMetadataReceipt(root).valid, true,
    'narrow receipt must not claim global validation of unrelated packed-ref lines');
  assert.deepStrictEqual(api.gitOutputs(root, ['HEAD_SHA']),
    ['[git context unavailable: named Git batch command failed]'],
    'Git authority resolution must fail malformed packed-ref storage closed');
}

function run() {
  proveUnrelatedLooseObjectHardlinkSurvives();
  proveLinkedSharedStoreChurnSurvives();
  proveLinkedSnapshotSurvivesSiblingCommit();
  proveNoRecursiveSharedStoreTraversal();
  proveGrowingControlReadIsLengthBounded();
  proveIncompleteControlReadIsRejected();
  proveControlPathSubstitutionIsRejected();
  proveMalformedUnrelatedPackedRefBoundary();
}

if (require.main === module) {
  try { run(); } finally { cleanup(); }
  console.log('RedDog governed Git stable-I/O contracts: PASS');
}

module.exports = { run, proveUnrelatedLooseObjectHardlinkSurvives, proveLinkedSharedStoreChurnSurvives, proveLinkedSnapshotSurvivesSiblingCommit, proveNoRecursiveSharedStoreTraversal, proveGrowingControlReadIsLengthBounded, proveIncompleteControlReadIsRejected, proveControlPathSubstitutionIsRejected, proveMalformedUnrelatedPackedRefBoundary };
