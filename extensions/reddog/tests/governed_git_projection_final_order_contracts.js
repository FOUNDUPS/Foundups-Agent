'use strict';

const { assert, cp, fs, path, api, newRepo,
  isGitExecutable } = require('./governed_git_test_helpers.js');

function installFinalFileHooks(state) {
  fs.lstatSync = function(target) {
    const resolved = path.resolve(String(target));
    if (resolved === path.join(state.root, '.git') && ++state.receipts === 3)
      state.started = true;
    if (state.complete && resolved.startsWith(state.root + path.sep)
      && !resolved.startsWith(path.join(state.root, '.git'))) state.late = true;
    return state.originalLstat.apply(this, arguments);
  };
  fs.openSync = function(target) {
    const resolved = path.resolve(String(target));
    if (state.complete && resolved.startsWith(state.root + path.sep)
      && !resolved.startsWith(path.join(state.root, '.git'))) state.late = true;
    const handle = state.originalOpen.apply(this, arguments);
    if (state.started && resolved === state.finalRef) state.finalHandle = handle;
    return handle;
  };
  fs.closeSync = function(handle) {
    const result = state.originalClose.apply(this, arguments);
    if (handle === state.finalHandle) state.complete = true;
    return result;
  };
  fs.readSync = function() { return state.originalRead.apply(this, arguments); };
}

function finalOrderState(root) {
  const headRef = fs.readFileSync(path.join(root, '.git', 'HEAD'), 'utf8')
    .trim().replace(/^ref:\s*/, '');
  return { root, finalRef: path.join(root, '.git', ...headRef.split('/')),
    receipts: 0, started: false, complete: false, finalHandle: null, late: false,
    originalLstat: fs.lstatSync, originalOpen: fs.openSync,
    originalClose: fs.closeSync, originalRead: fs.readSync,
    originalExec: cp.execFileSync };
}

function installFinalGitHook(state) {
  cp.execFileSync = function(file) {
    if (state.complete && isGitExecutable(file)) state.late = true;
    return state.originalExec.apply(this, arguments);
  };
}

function restoreFinalOrderHooks(state) {
  fs.lstatSync = state.originalLstat;
  fs.openSync = state.originalOpen;
  fs.closeSync = state.originalClose;
  fs.readSync = state.originalRead;
  cp.execFileSync = state.originalExec;
}

function proveFinalReceiptOrdering() {
  const root = newRepo(true);
  fs.writeFileSync(path.join(root, 'allowed.py'), 'changed = true\n', 'utf8');
  const state = finalOrderState(root);
  installFinalFileHooks(state);
  installFinalGitHook(state);
  try {
    const snapshot = api.governedGitSnapshot(root);
    assert(snapshot.projection_receipt);
    assert.strictEqual(state.receipts, 3);
    assert.strictEqual(state.late, false);
  } finally { restoreFinalOrderHooks(state); }
  fs.writeFileSync(path.join(root, 'allowed.py'), 'post-proof point in time\n');
}

module.exports = { proveFinalReceiptOrdering };
