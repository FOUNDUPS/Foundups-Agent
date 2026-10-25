'use strict';

const { assert, cp, fs, path, roots, api, gitStorage, newRepo, hardlinkOutside,
  assertBlocked, isContentCommand, linkedRepo, batchUnavailable, commitFile,
  cleanup } = require('./governed_git_test_helpers.js');
const gitExecutable = require('../governed_git_executable.js');

function proveExecutableReplacementWithholdsBatch() {
  const root = newRepo(true);
  let replaced = false;
  const authority = {
    bind: (source) => gitExecutable.bind(source),
    revalidate: (binding) => {
      if (replaced) throw new Error('governed_git_executable_changed');
      return gitExecutable.revalidate(binding);
    },
    execFileSync: (binding, args, options) => {
      const output = gitExecutable.execFileSync(binding, args, options);
      if (args.includes('ls-files')) replaced = true;
      return output;
    }
  };
  const replacementApi = require('../governed_git_context.js').create({
    isTargetReadPathDenied: () => false,
    resolveSafeRepoFile: require('./governed_git_test_helpers.js').safeResolve,
    gitExecutable: authority
  });
  batchUnavailable(replacementApi.gitOutputs(root, ['TRACKED_PATHS']),
    'executable replacement during batch');
  assert.strictEqual(replaced, true, 'replacement hook must follow content execution');
}

function proveBatchMutation(label, setup, mutate, operationNames, expectedReason) {
  const fixture = linkedRepo();
  if (setup) setup(fixture);
  const originalExec = cp.execFileSync;
  let contentCalls = 0;
  let mutated = false;
  cp.execFileSync = function(file, args) {
    const result = originalExec.apply(this, arguments);
    if (!mutated && isContentCommand(file, args) && ++contentCalls === 1) {
      mutate(fixture, originalExec);
      mutated = true;
    }
    return result;
  };
  try {
    const values = api.gitOutputs(fixture.linked,
      operationNames || ['HEAD_SHA', 'TRACKED_PATHS']);
    assert.strictEqual(mutated, true, label + ' mutation hook must run');
    batchUnavailable(values, label);
    if (expectedReason) assert(values.every((value) => value.includes(expectedReason)));
  } finally {
    cp.execFileSync = originalExec;
  }
}

function proveCurrentRefMutationsBlocked() {
  proveBatchMutation('current symbolic ref move', (fixture) => {
    commitFile(fixture.main, 'ref-move.txt', 'ref move\n', 'ref move target');
  }, (fixture, originalExec) => {
    const target = originalExec('git', ['rev-parse', 'HEAD'], {
      cwd: fixture.main, encoding: 'utf8'
    }).trim();
    originalExec('git', ['update-ref', 'refs/heads/reddog-linked-authority', target], {
      cwd: fixture.main
    });
  });
  proveBatchMutation('detached HEAD move', (fixture) => {
    commitFile(fixture.main, 'second.txt', 'second\n', 'second commit');
    cp.execFileSync('git', ['checkout', '--detach', '-q'], { cwd: fixture.linked });
  }, (fixture, originalExec) => {
    const other = originalExec('git', ['rev-parse', 'master'], {
      cwd: fixture.main, encoding: 'utf8'
    }).trim();
    fs.writeFileSync(path.join(fixture.admin, 'HEAD'), other + '\n', 'ascii');
  });
}

function proveIndexAndPackedMutationsBlocked() {
  proveBatchMutation('authority index move', null, (fixture, originalExec) => {
    fs.writeFileSync(path.join(fixture.linked, 'indexed.txt'), 'index move\n');
    originalExec('git', ['add', 'indexed.txt'], { cwd: fixture.linked });
  }, ['TRACKED_PATHS']);
  proveBatchMutation('packed current ref gains loose override', (fixture) => {
    cp.execFileSync('git', ['pack-refs', '--all', '--prune'], { cwd: fixture.main });
  }, (fixture) => {
    const oid = cp.execFileSync('git', ['rev-parse', 'HEAD'], {
      cwd: fixture.linked, encoding: 'utf8'
    }).trim();
    const loose = path.join(fixture.common, 'refs', 'heads', 'reddog-linked-authority');
    fs.mkdirSync(path.dirname(loose), { recursive: true });
    fs.writeFileSync(loose, oid + '\n', 'ascii');
  });
}

function proveCommonControlMutationsBlocked() {
  for (const relative of ['config', 'shallow', 'info/attributes', 'info/exclude']) {
    proveBatchMutation('relevant common ' + relative + ' drift', (fixture) => {
      if (relative === 'shallow') {
        const oid = cp.execFileSync('git', ['rev-parse', 'HEAD'], {
          cwd: fixture.linked, encoding: 'utf8'
        }).trim();
        fs.writeFileSync(path.join(fixture.common, relative), oid + '\n', 'ascii');
      }
    }, (fixture) => {
      const target = path.join(fixture.common, relative);
      fs.mkdirSync(path.dirname(target), { recursive: true });
      fs.appendFileSync(target, '\n# r9 relevant drift\n');
    });
  }
}

function proveRelevantAuthorityMutationsBlocked() {
  proveCurrentRefMutationsBlocked();
  proveIndexAndPackedMutationsBlocked();
  proveCommonControlMutationsBlocked();
}

function proveOutputDoubleExecutionFailures() {
  const root = newRepo(true);
  const originalExec = cp.execFileSync;
  let contentCalls = 0;
  cp.execFileSync = function(file, args) {
    const result = originalExec.apply(this, arguments);
    if (isContentCommand(file, args) && ++contentCalls === 2) return result + 'r9-drift\n';
    return result;
  };
  try {
    batchUnavailable(api.gitOutputs(root, ['TRACKED_PATHS']), 'A/B output mismatch');
    assert.strictEqual(contentCalls, 4,
      'bound non-HEAD batch must execute semantic HEAD proof plus output twice');
  } finally {
    cp.execFileSync = originalExec;
  }

  let calls = 0;
  cp.execFileSync = function(file, args) {
    if (isContentCommand(file, args) && ++calls === 2) throw new Error('second pass failed');
    return originalExec.apply(this, arguments);
  };
  try {
    const failed = api.gitOutputs(root, ['TRACKED_PATHS']);
    assert.deepStrictEqual(failed,
      ['[git context unavailable: named Git batch command failed]']);
  } finally {
    cp.execFileSync = originalExec;
  }
}

function proveForbiddenControlsBlocked() {
  for (const relative of ['objects/info/alternates',
    'objects/info/http-alternates', 'info/grafts']) {
    const root = newRepo(true);
    const target = path.join(root, '.git', ...relative.split('/'));
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, 'forbidden\n');
    assertBlocked(root, relative);
  }
}

function proveLinkedTopologyForgeriesBlocked() {
  const forged = linkedRepo();
  fs.unlinkSync(path.join(forged.linked, '.git'));
  fs.writeFileSync(path.join(forged.linked, '.git'), 'not-a-gitfile\n', 'utf8');
  assertBlocked(forged.linked, 'forged gitfile');
  const cross = linkedRepo();
  const other = newRepo(true);
  fs.writeFileSync(path.join(cross.admin, 'commondir'), path.join(other, '.git') + '\n');
  assertBlocked(cross.linked, 'cross-common worktree');
  const backref = linkedRepo();
  fs.writeFileSync(path.join(backref.admin, 'gitdir'), path.join(backref.main, '.git') + '\n');
  assertBlocked(backref.linked, 'forged worktree backref');

  const linkedControl = linkedRepo();
  hardlinkOutside(linkedControl.linked, path.join(linkedControl.admin, 'HEAD'),
    'linked-head-control');
  assertBlocked(linkedControl.linked, 'hardlinked linked HEAD');
}

function proveUnsupportedStorageBlocked() {
  const unsupported = newRepo(true);
  fs.appendFileSync(path.join(unsupported, '.git', 'config'),
    '\n[extensions]\n\trefStorage = reftable\n');
  assertBlocked(unsupported, 'unsupported ref storage');
}

function proveRequiredObjectFailures() {
  for (const mode of ['missing', 'corrupt']) {
    const root = newRepo(true);
    const oid = cp.execFileSync('git', ['rev-parse', 'HEAD'], {
      cwd: root, encoding: 'utf8'
    }).trim();
    const object = path.join(root, '.git', 'objects', oid.slice(0, 2), oid.slice(2));
    if (mode === 'missing') fs.unlinkSync(object);
    else {
      fs.chmodSync(object, 0o666);
      fs.writeFileSync(object, 'not a git object', 'utf8');
    }
    batchUnavailable(api.gitOutputs(root, ['HEAD_SHA']), mode + ' required HEAD object');
  }
}

function assertAbsentConfigReadable(root, config, label) {
  assert.strictEqual(fs.existsSync(config), false,
    label + ' fixture must start without optional config.worktree');
  const receipt = gitStorage.registeredGitMetadataReceipt(root);
  assert.strictEqual(Object.isFrozen(receipt), true);
  assert.strictEqual(receipt.worktree_config_state, 'absent');
  const outputs = api.gitOutputs(root, ['HEAD_SHA', 'TRACKED_PATHS']);
  assert(!outputs.some((value) => value.startsWith('[git context unavailable:')),
    'verified ' + label + ' config.worktree absence must remain readable');
  assert(outputs[1].split(/\r?\n/).includes('allowed.py'));
  assert.strictEqual(api.governedGitReadiness(root).ready, true);
  assert.strictEqual(api.governedGitReadiness(root).config_write_performed, false);
  assert.strictEqual(fs.existsSync(config), false,
    'governed Git must not create optional ' + label + ' config.worktree');
}

function proveDirectAbsentWorktreeConfig() {
  const root = newRepo(true);
  cp.execFileSync('git', ['config', 'extensions.worktreeConfig', 'true'], {
    cwd: root
  });
  assertAbsentConfigReadable(root, path.join(root, '.git', 'config.worktree'), 'direct');
  return root;
}

function proveLinkedAbsentWorktreeConfig(directRoot) {
  const linkedRoot = directRoot + '-linked';
  cp.execFileSync('git', ['worktree', 'add', '-q', '-b', 'reddog-linked-fixture', linkedRoot], {
    cwd: directRoot
  });
  roots.push(linkedRoot);
  const linkedAdmin = cp.execFileSync('git', ['rev-parse', '--absolute-git-dir'], {
    cwd: linkedRoot, encoding: 'utf8'
  }).trim();
  assertAbsentConfigReadable(linkedRoot, path.join(linkedAdmin, 'config.worktree'), 'linked');
}

function proveAbsentOptionalWorktreeConfigAccepted() {
  proveLinkedAbsentWorktreeConfig(proveDirectAbsentWorktreeConfig());
}

function proveTopologyAndObjectFailures() {
  proveForbiddenControlsBlocked();
  proveLinkedTopologyForgeriesBlocked();
  proveUnsupportedStorageBlocked();
  proveRequiredObjectFailures();
}

function proveAbsentWorktreeConfigMutationBlocked() {
  const root = newRepo(true);
  cp.execFileSync('git', ['config', 'extensions.worktreeConfig', 'true'], { cwd: root });
  const config = path.join(root, '.git', 'config.worktree');
  const originalExec = cp.execFileSync;
  let mutated = false;
  cp.execFileSync = function(file, args) {
    if (!mutated && isContentCommand(file, args)) {
      fs.writeFileSync(config, '[reddog]\nfixture = true\n', 'utf8');
      mutated = true;
    }
    return originalExec.apply(this, arguments);
  };
  try {
    assert.deepStrictEqual(api.gitOutputs(root, ['TRACKED_PATHS']),
      ['[git context unavailable: Git storage changed during batch]']);
    assert.strictEqual(mutated, true,
      'absent config.worktree mutation must reach the final receipt gate');
  } finally {
    cp.execFileSync = originalExec;
  }
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

function run() {
  proveAbsentOptionalWorktreeConfigAccepted();
  proveAbsentWorktreeConfigMutationBlocked();
  proveRelevantAuthorityMutationsBlocked();
  proveOutputDoubleExecutionFailures();
  proveExecutableReplacementWithholdsBatch();
  proveTopologyAndObjectFailures();
}

if (require.main === module) {
  try { run(); } finally { cleanup(); }
  console.log('RedDog governed Git authority/readiness contracts: PASS');
}

module.exports = { run, proveRelevantAuthorityMutationsBlocked, proveOutputDoubleExecutionFailures, proveExecutableReplacementWithholdsBatch, proveTopologyAndObjectFailures, proveAbsentOptionalWorktreeConfigAccepted, proveAbsentWorktreeConfigMutationBlocked, proveBoundControlFile };
