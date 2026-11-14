'use strict';

const { assert, cp, fs, path, api, newRepo,
  hardlinkOutside, assertBlocked, cleanup } = require('./governed_git_test_helpers.js');
const projection = require('./governed_git_projection_contracts.js');
const projectionRaces = require('./governed_git_projection_race_contracts.js');
const storage = require('./governed_git_storage_contracts.js');
const refs = require('./governed_git_ref_contracts.js');
const authority = require('./governed_git_authority_contracts.js');
const readiness = require('../governed_git_readiness.js');

assert.strictEqual(readiness.GIT_CONFIG_TIMEOUT_MS, 5000,
  'governed Git config probes must retain their concurrent-release bound');

function runFinalFixtures() {
  const graftRoot = newRepo(true);
  fs.writeFileSync(path.join(graftRoot, '.git', 'info', 'grafts'),
    '0'.repeat(40) + '\n', 'ascii');
  assertBlocked(graftRoot, 'legacy graft control');

  const configRoot = newRepo(false);
  assert(!api.governedGitStatus(configRoot, 8000).includes('[git context unavailable:'));
  hardlinkOutside(configRoot, path.join(configRoot, '.git', 'config'), 'config-link');
  assertBlocked(configRoot, 'config hardlink mutation');

  const worktreeRoot = newRepo(false);
  cp.execFileSync('git', ['config', 'extensions.worktreeConfig', 'true'], {
    cwd: worktreeRoot
  });
  cp.execFileSync('git', ['config', '--worktree', 'reddog.fixture', 'true'], {
    cwd: worktreeRoot
  });
  assert(!api.governedGitStatus(worktreeRoot, 8000).includes('[git context unavailable:'));
  hardlinkOutside(worktreeRoot, path.join(worktreeRoot, '.git', 'config.worktree'),
    'worktree-config-link');
  assertBlocked(worktreeRoot, 'config.worktree hardlink mutation');

  proveOwnedRepoArguments();
}

function proveOwnedRepoArguments() {
  const root = newRepo(false);
  const calls = [];
  const originalExec = cp.execFileSync;
  cp.execFileSync = function(file, args, options) {
    calls.push({ file, args: Array.from(args || []), options });
    return originalExec.apply(this, arguments);
  };
  try { assert(!api.governedGitStatus(root, 8000).includes('[git context unavailable:')); }
  finally { cp.execFileSync = originalExec; }
  const readiness = api.governedGitReadiness(root);
  assert.strictEqual(readiness.ownership_mismatch_observed, false);
  assert.strictEqual(readiness.safe_directory_override_applied, false);
  assert.strictEqual(readiness.safe_directory_scope, 'none');
  const contentCalls = calls.filter((call) => call.args.some((arg) =>
    ['diff', 'ls-files', 'rev-parse'].includes(arg)));
  assert(contentCalls.length > 0);
  for (const call of contentCalls) {
    assert(!call.args.some((arg) => String(arg).startsWith('safe.directory=')));
    assert(call.args.includes('--no-optional-locks'));
    assert(call.args.includes('core.hooksPath=/dev/null'));
    assert(call.args.includes('core.attributesFile=/dev/null'));
    assert(call.args.includes('core.excludesFile=/dev/null'));
    assert.strictEqual(call.options.env.GIT_EXTERNAL_DIFF, '');
  }
}

try {
  refs.proveRepairLoop3Contracts();
  refs.proveRepairLoop2Contracts();
  projection.provePlatformPathIdentityRules();
  projection.proveCanonicalFileIdentityUnique();
  projectionRaces.proveFactoryInstanceIsolation();
  projectionRaces.proveFinalReceiptIsAbsoluteLastRead();
  projection.proveNamedBatchContract();
  projection.proveIgnoredExclusion();
  projection.proveIgnoredCollisionBlocked();
  projectionRaces.proveIgnoredJunctionNotTraversed();
  projectionRaces.proveWorktreeReadMutationBlocked();
  projectionRaces.proveSecondEnumerationMutation('new path during second enumeration',
    (root) => fs.writeFileSync(path.join(root, 'new.py'), 'new = true\n', 'utf8'));
  projectionRaces.proveSecondEnumerationMutation('removed path during second enumeration',
    (root) => fs.unlinkSync(path.join(root, 'allowed.py')));
  projectionRaces.proveSecondEnumerationMutation('renamed path during second enumeration',
    (root) => fs.renameSync(path.join(root, 'allowed.py'), path.join(root, 'renamed.py')));
  projectionRaces.proveSecondEnumerationMutation('index change during second enumeration',
    (root, originalExec) => originalExec('git', ['add', 'allowed.py'], { cwd: root }));
  storage.proveUnrelatedLooseObjectHardlinkSurvives();
  authority.proveAbsentOptionalWorktreeConfigAccepted();
  authority.proveAbsentWorktreeConfigMutationBlocked();
  storage.proveLinkedSharedStoreChurnSurvives();
  storage.proveLinkedSnapshotSurvivesSiblingCommit();
  storage.proveNoRecursiveSharedStoreTraversal();
  storage.proveGrowingControlReadIsLengthBounded();
  storage.proveIncompleteControlReadIsRejected();
  storage.proveControlPathSubstitutionIsRejected();
  storage.proveMalformedUnrelatedPackedRefBoundary();
  authority.proveRelevantAuthorityMutationsBlocked();
  authority.proveOutputDoubleExecutionFailures();
  authority.proveTopologyAndObjectFailures();
  for (const name of ['info/attributes', 'info/exclude']) authority.proveBoundControlFile(name);
  authority.proveBoundControlFile('shallow', (root, control) => {
    const head = cp.execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim();
    fs.writeFileSync(control, head + '\n', 'ascii');
  });
  projection.proveSnapshotMutationBlocked('HEAD hardlink before first content command',
    'before-first', (root) => hardlinkOutside(root, path.join(root, '.git', 'HEAD'), 'snapshot-head-link'));
  projection.proveSnapshotMutationBlocked('config hardlink between content commands',
    'between', (root) => hardlinkOutside(root, path.join(root, '.git', 'config'), 'snapshot-config-link'));
  projection.proveSnapshotMutationBlocked('exclude mutation immediately before final validation',
    'before-final', (root) => fs.appendFileSync(path.join(root, '.git', 'info', 'exclude'),
      '\nreddog-race-fixture\n', 'utf8'));
  projection.proveBatchMutationBlocked();
  runFinalFixtures();
} finally { cleanup(); }

console.log('RedDog governed Git storage/control hardening contracts: PASS');
