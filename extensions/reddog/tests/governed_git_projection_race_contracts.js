'use strict';

const { assert, cp, fs, os, path, governed, outsideRoots, api, safeResolve, newRepo,
  assertWholeSnapshotUnavailable, isGitExecutable,
  cleanup } = require('./governed_git_test_helpers.js');
const finalOrder = require('./governed_git_projection_final_order_contracts.js');

function installWorktreeMutation(file) {
  const originalOpen = fs.openSync;
  const originalClose = fs.closeSync;
  const originalRead = fs.readSync;
  const handles = new Set();
  let mutated = false;
  fs.openSync = function(target) {
    const handle = originalOpen.apply(this, arguments);
    if (path.resolve(String(target)) === file) handles.add(handle);
    return handle;
  };
  fs.closeSync = function(handle) {
    handles.delete(handle);
    return originalClose.apply(this, arguments);
  };
  fs.readSync = function(target) {
    const result = originalRead.apply(this, arguments);
    if (!mutated && handles.has(target)) {
      fs.writeFileSync(file, 'second projection\n', 'utf8');
      mutated = true;
    }
    return result;
  };
  return { originalOpen, originalClose, originalRead, mutated: () => mutated };
}

function proveWorktreeReadMutationBlocked() {
  const root = newRepo(true);
  const file = path.join(root, 'allowed.py');
  fs.writeFileSync(file, 'first projection\n', 'utf8');
  const hook = installWorktreeMutation(file);
  try {
    assertWholeSnapshotUnavailable(api.governedGitSnapshot(root), 'mutation during stable read');
    assert(hook.mutated());
  } finally {
    fs.openSync = hook.originalOpen;
    fs.closeSync = hook.originalClose;
    fs.readSync = hook.originalRead;
  }
}

function installGrowthReadProbe(file, options = {}) {
  const original = { open: fs.openSync, close: fs.closeSync, fstat: fs.fstatSync,
    readFile: fs.readFileSync, read: fs.readSync, alloc: Buffer.allocUnsafe };
  const state = { handles: new Set(), mutated: false, opened: 0,
    maxRead: 0, maxRequest: 0, maxAllocation: 0, allocations: [], mocked: false };
  fs.openSync = function(target) { const matches = path.resolve(String(target)) === file;
    if (matches && options.beforeOpen && !state.mutated) {
      state.mutated = true; options.beforeOpen();
    }
    const handle = original.open.apply(this, arguments);
    if (matches) state.handles.add(handle); return handle; };
  fs.closeSync = function(handle) { state.handles.delete(handle);
    return original.close.apply(this, arguments); };
  fs.fstatSync = function(handle) { const stat = original.fstat.apply(this, arguments);
    if (state.handles.has(handle) && options.openedSize !== undefined && !state.mocked) {
      state.mocked = true; return Object.assign(stat, { size: options.openedSize });
    }
    if (state.handles.has(handle) && !state.mutated) { state.opened = stat.size;
      fs.writeFileSync(file, Buffer.alloc(2 * 1024 * 1024 + 4104, 120)); state.mutated = true; }
    return stat; };
  fs.readFileSync = function(target) { const bytes = original.readFile.apply(this, arguments);
    if (typeof target === 'number' && state.handles.has(target)) state.maxRead = bytes.length;
    return bytes; };
  fs.readSync = function(handle, buffer, offset, length) { state.maxRequest = Math.max(
    state.maxRequest, state.handles.has(handle) ? length : 0); const count = original.read.apply(
      this, arguments); state.maxRead = Math.max(state.maxRead, state.handles.has(handle) ? count : 0);
    return count; };
  Buffer.allocUnsafe = function(size) { if (state.handles.size) {
    state.allocations.push(size); state.maxAllocation = Math.max(state.maxAllocation, size); }
    return original.alloc.apply(this, arguments); };
  return { original, state };
}

function restoreGrowthReadProbe(hook) {
  fs.openSync = hook.original.open; fs.closeSync = hook.original.close;
  fs.fstatSync = hook.original.fstat;
  fs.readFileSync = hook.original.readFile; fs.readSync = hook.original.read;
  Buffer.allocUnsafe = hook.original.alloc;
}

function proveGrowthReadBounded() {
  const root = newRepo(true); const file = path.join(root, 'allowed.py');
  fs.writeFileSync(file, '12345678', 'utf8');
  const hook = installGrowthReadProbe(file);
  try {
    assertWholeSnapshotUnavailable(api.governedGitSnapshot(root), 'growth after opened size');
    assert(hook.state.mutated); assert.strictEqual(hook.state.opened, 8);
    assert(hook.state.maxRead <= 8,
      'stable read consumed ' + hook.state.maxRead + ' bytes from an 8-byte open');
    assert(hook.state.maxRequest <= 8, 'fd request must not exceed opened size');
    assert(hook.state.maxAllocation <= 8, 'allocation must not exceed opened size');
  } finally { restoreGrowthReadProbe(hook); }
}

function provePreOpenMutationRejected(label, mutate) {
  const root = newRepo(true); const file = path.join(root, 'allowed.py');
  fs.writeFileSync(file, '12345678', 'utf8');
  const hook = installGrowthReadProbe(file, { beforeOpen: () => mutate(root, file) });
  try { assertWholeSnapshotUnavailable(api.governedGitSnapshot(root), label);
    assert(hook.state.mutated); assert.strictEqual(hook.state.allocations.length, 0);
    assert.strictEqual(hook.state.maxRequest, 0); assert.strictEqual(hook.state.maxRead, 0);
  } finally { restoreGrowthReadProbe(hook); }
}

function proveInvalidOpenedSizesRejected() {
  for (const size of [-1, 2.5, Number.MAX_SAFE_INTEGER + 1, NaN]) {
    const root = newRepo(true); const file = path.join(root, 'allowed.py');
    fs.writeFileSync(file, '12345678', 'utf8');
    const hook = installGrowthReadProbe(file, { openedSize: size });
    try { assertWholeSnapshotUnavailable(api.governedGitSnapshot(root), 'unsafe opened size');
      assert.strictEqual(hook.state.allocations.length, 0); assert.strictEqual(hook.state.maxRead, 0);
    } finally { restoreGrowthReadProbe(hook); }
  }
}

function installTerminatingRead(file, mode) {
  const originalOpen = fs.openSync; const originalRead = fs.readSync;
  const handles = new Set(); let calls = 0;
  fs.openSync = function(target) { const handle = originalOpen.apply(this, arguments);
    if (path.resolve(String(target)) === file) handles.add(handle); return handle; };
  fs.readSync = function(handle, buffer, offset, length, position) {
    if (!handles.has(handle)) return originalRead.apply(this, arguments);
    calls += 1; if (mode === 'zero' || calls > 1) return 0;
    const count = originalRead.call(this, handle, buffer, offset, Math.max(1, length - 1), position);
    if (mode === 'truncate') fs.truncateSync(file, 0); return count;
  };
  return { originalOpen, originalRead, calls: () => calls };
}

function proveTerminatingReadRejected(mode) {
  const root = newRepo(true); const file = path.join(root, 'allowed.py');
  fs.writeFileSync(file, 'x'.repeat(64), 'utf8'); const hook = installTerminatingRead(file, mode);
  try { assertWholeSnapshotUnavailable(api.governedGitSnapshot(root), mode + ' fd read');
    assert(hook.calls() > 0, mode + ' hook must observe bounded fd reads'); }
  finally { fs.openSync = hook.originalOpen; fs.readSync = hook.originalRead; }
}

function proveProjectionFileSizeBoundaries() {
  const maximum = 2 * 1024 * 1024;
  const empty = newRepo(true); fs.writeFileSync(path.join(empty, 'allowed.py'), '', 'utf8');
  const emptySnapshot = api.governedGitSnapshot(empty);
  assert.strictEqual(emptySnapshot.projection_receipt.captured_bytes, 0);
  const exact = newRepo(true); fs.writeFileSync(path.join(exact, 'allowed.py'), Buffer.alloc(maximum));
  const exactSnapshot = api.governedGitSnapshot(exact, { diff: 256 });
  assert.strictEqual(exactSnapshot.projection_receipt.captured_bytes, maximum);
  const over = newRepo(true);
  fs.writeFileSync(path.join(over, 'allowed.py'), Buffer.alloc(maximum + 1));
  assertWholeSnapshotUnavailable(api.governedGitSnapshot(over), 'maximum plus one byte');
}

function proveSecondEnumerationMutation(label, mutate) {
  const root = newRepo(true);
  fs.writeFileSync(path.join(root, 'allowed.py'), 'changed = true\n', 'utf8');
  const originalExec = cp.execFileSync;
  let enumerations = 0;
  cp.execFileSync = function(file, args) {
    if (isGitExecutable(file) && args.includes('ls-files') && args.includes('-v')
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

function assertFactoryPolicyIsolation(root, allow, deny, allowApi, denyApi) {
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
}

function assertDefaultApiIsolation(root, allowApi, defaultBefore) {
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

function proveFactoryInstanceIsolation() {
  const root = newRepo(true);
  fs.writeFileSync(path.join(root, 'allowed.py'), 'changed = true\n', 'utf8');
  const allow = { isTargetReadPathDenied: () => false, resolveSafeRepoFile: safeResolve };
  const deny = { isTargetReadPathDenied: () => true, resolveSafeRepoFile: safeResolve };
  const defaultBefore = governed.governedGitSnapshot(root);
  const allowApi = governed.create(allow);
  assertFactoryPolicyIsolation(root, allow, deny, allowApi, governed.create(deny));
  assertDefaultApiIsolation(root, allowApi, defaultBefore);
}

function installLateControlMutation(root, worktreeFile) {
  const originalOpen = fs.openSync;
  const originalContentClose = fs.closeSync;
  const originalRead = fs.readSync;
  const worktreeHandles = new Set();
  let contentReads = 0;
  fs.openSync = function(target) {
    const handle = originalOpen.apply(this, arguments);
    if (path.resolve(String(target)) === worktreeFile) worktreeHandles.add(handle);
    return handle;
  };
  fs.closeSync = function(handle) {
    worktreeHandles.delete(handle);
    return originalContentClose.apply(this, arguments);
  };
  fs.readSync = function(target) {
    const result = originalRead.apply(this, arguments);
    if (typeof target === 'number' && worktreeHandles.has(target)
      && ++contentReads === 3) {
      fs.appendFileSync(path.join(root, '.git', 'info', 'exclude'), '\nr6-late-control\n');
    }
    return result;
  };
  return { originalOpen, originalContentClose, originalRead,
    reads: () => contentReads };
}

function proveLateControlMutationBlocked() {
  const root = newRepo(true);
  const worktreeFile = path.join(root, 'allowed.py');
  fs.writeFileSync(worktreeFile, 'changed = true\n', 'utf8');
  const hook = installLateControlMutation(root, worktreeFile);
  try {
    assertWholeSnapshotUnavailable(api.governedGitSnapshot(root),
      'Git control mutation during final capture');
    assert.strictEqual(hook.reads(), 3);
  } finally {
    fs.openSync = hook.originalOpen;
    fs.closeSync = hook.originalContentClose;
    fs.readSync = hook.originalRead;
  }
}

function proveFinalReceiptIsAbsoluteLastRead() {
  proveLateControlMutationBlocked();
  finalOrder.proveFinalReceiptOrdering();
}


function run() {
  proveWorktreeReadMutationBlocked();
  proveGrowthReadBounded();
  provePreOpenMutationRejected('pre-open growth', (root, file) => {
    fs.writeFileSync(file, Buffer.alloc(2 * 1024 * 1024 + 1));
  });
  provePreOpenMutationRejected('pre-open replacement', (root, file) => {
    fs.renameSync(file, path.join(root, 'replaced.py')); fs.writeFileSync(file, '12345678');
  });
  proveInvalidOpenedSizesRejected();
  proveTerminatingReadRejected('short');
  proveTerminatingReadRejected('zero');
  proveTerminatingReadRejected('truncate');
  proveProjectionFileSizeBoundaries();
  proveIgnoredJunctionNotTraversed();
  proveFactoryInstanceIsolation();
  proveFinalReceiptIsAbsoluteLastRead();
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
}

if (require.main === module) {
  try { run(); } finally { cleanup(); }
  console.log('RedDog governed Git projection race contracts: PASS');
}

module.exports = { run, proveWorktreeReadMutationBlocked,
  proveGrowthReadBounded, proveTerminatingReadRejected, proveProjectionFileSizeBoundaries,
  provePreOpenMutationRejected, proveInvalidOpenedSizesRejected,
  proveSecondEnumerationMutation, proveIgnoredJunctionNotTraversed,
  proveFactoryInstanceIsolation, proveFinalReceiptIsAbsoluteLastRead };
