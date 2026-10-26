'use strict';

const { assert, cp, fs, os, path, roots, outsideRoots, api, gitStorage, newRepo,
  assertBlocked, linkedRepo, batchUnavailable, cleanup } = require('./governed_git_test_helpers.js');

function proveNestedDirectoryLinksBlocked() {
  const junctionCases = [
    { fixture: { root: newRepo(true) }, relative: 'info', label: 'direct info' },
    { fixture: linkedRepo(), relative: 'objects/info', label: 'linked objects/info' }
  ];
  for (const item of junctionCases) {
    const common = item.fixture.common || path.join(item.fixture.root, '.git');
    const governedRoot = item.fixture.linked || item.fixture.root;
    const nested = path.join(common, ...item.relative.split('/'));
    const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-git-nested-outside-'));
    outsideRoots.push(outside);
    assert(fs.lstatSync(nested).isDirectory(), item.label + ' must exist after git init');
    fs.rmSync(nested, { recursive: true, force: true });
    fs.symlinkSync(outside, nested, process.platform === 'win32' ? 'junction' : 'dir');
    assert.strictEqual(gitStorage.registeredGitMetadataReceipt(governedRoot).valid, false,
      item.label + ' external directory link must invalidate the public receipt');
    assertBlocked(governedRoot, item.label + ' external directory link');
  }
}

function proveNestedDirectoryShapeBlocked() {
  const missing = newRepo(true);
  fs.rmSync(path.join(missing, '.git', 'info'), { recursive: true, force: true });
  assert.strictEqual(gitStorage.registeredGitMetadataReceipt(missing).valid, false,
    'missing required common info directory must fail closed');

  const nonDirectory = newRepo(true);
  const objectInfo = path.join(nonDirectory, '.git', 'objects', 'info');
  fs.rmSync(objectInfo, { recursive: true, force: true });
  fs.writeFileSync(objectInfo, 'not a directory\n', 'ascii');
  assert.strictEqual(gitStorage.registeredGitMetadataReceipt(nonDirectory).valid, false,
    'non-directory common objects/info must fail closed');
}

function proveNestedDirectorySubstitutionBlocked() {
  const substituted = newRepo(true);
  const target = path.join(substituted, '.git', 'objects', 'info');
  const displaced = target + '.r9-displaced';
  const originalRealpath = fs.realpathSync;
  let replaced = false;
  fs.realpathSync = function(candidate) {
    const resolved = originalRealpath.apply(this, arguments);
    if (!replaced && path.resolve(String(candidate)) === target) {
      fs.renameSync(target, displaced);
      fs.mkdirSync(target);
      replaced = true;
    }
    return resolved;
  };
  try {
    assert.strictEqual(gitStorage.registeredGitMetadataReceipt(substituted).valid, false,
      'nested directory path substitution inside one receipt must fail closed');
    assert.strictEqual(replaced, true, 'nested substitution fixture must execute');
  } finally {
    fs.realpathSync = originalRealpath;
  }
}

function proveNestedGitDirectoryConfinement() {
  proveNestedDirectoryLinksBlocked();
  proveNestedDirectoryShapeBlocked();
  proveNestedDirectorySubstitutionBlocked();
}

function proveAcceptedHeadRefs() {
  const accepted = newRepo(true);
  cp.execFileSync('git', ['branch', 'feature/r9.ok-1'], { cwd: accepted });
  fs.writeFileSync(path.join(accepted, '.git', 'HEAD'),
    'ref: refs/heads/feature/r9.ok-1\n', 'ascii');
  assert.strictEqual(gitStorage.registeredGitMetadataReceipt(accepted).valid, true,
    'supported multi-component heads ref must remain accepted');

  const unborn = newRepo(true);
  fs.writeFileSync(path.join(unborn, '.git', 'HEAD'),
    'ref: refs/heads/feature/r9-unborn\n', 'ascii');
  assert.strictEqual(gitStorage.registeredGitMetadataReceipt(unborn).valid, true,
    'supported absent heads ref must retain unborn behavior');
}

function proveRejectedHeadRefs() {
  const rejected = [
    'refs/heads/foo.lock/bar',
    'refs/heads/foo./bar',
    'refs/heads/foo/.hidden',
    'refs/heads/foo/bar.',
    'refs/heads/foo//bar',
    'refs/heads/foo..bar',
    'refs/heads/foo@{bar',
    'refs/heads/foo bar'
  ];
  for (const refName of rejected) {
    const root = newRepo(true);
    fs.writeFileSync(path.join(root, '.git', 'HEAD'), 'ref: ' + refName + '\n', 'ascii');
    assert.strictEqual(gitStorage.registeredGitMetadataReceipt(root).valid, false,
      refName + ' must be outside the internally supported heads grammar');
    assertBlocked(root, refName);
  }
}

function proveSupportedHeadRefGrammar() {
  proveAcceptedHeadRefs();
  proveRejectedHeadRefs();
}

function packedCurrentFixture() {
  const root = newRepo(true);
  cp.execFileSync('git', ['pack-refs', '--all', '--prune'], { cwd: root });
  const refName = fs.readFileSync(path.join(root, '.git', 'HEAD'), 'ascii')
    .trim().replace(/^ref:\s*/, '');
  const oid = cp.execFileSync('git', ['rev-parse', 'HEAD'], {
    cwd: root, encoding: 'utf8'
  }).trim();
  const packedPath = path.join(root, '.git', 'packed-refs');
  const source = fs.readFileSync(packedPath, 'ascii');
  const canonical = oid + ' ' + refName;
  assert(source.split(/\r?\n/).includes(canonical),
    'packed current-ref fixture must start canonical');
  return { root, refName, oid, packedPath, source, canonical };
}

function proveMalformedPackedCurrentEntries() {
  const rewrites = [
    (item) => item.oid + '  ' + item.refName,
    (item) => item.oid + '\t' + item.refName,
    (item) => item.oid + ' ' + item.refName + ' ',
    (item) => 'not-an-oid ' + item.refName,
    (item) => '^' + item.oid + ' ' + item.refName,
    (item) => item.oid + ' ' + item.refName + ' extra'
  ];
  for (const rewrite of rewrites) {
    const item = packedCurrentFixture();
    fs.writeFileSync(item.packedPath,
      item.source.replace(item.canonical, rewrite(item)), 'ascii');
    assert.strictEqual(gitStorage.registeredGitMetadataReceipt(item.root).valid, false,
      'malformed line targeting the exact current ref must not become unborn');
    batchUnavailable(api.gitOutputs(item.root, ['TRACKED_PATHS']),
      'malformed packed current-ref line');
  }
}

function proveDuplicatePeeledAndAbsentPackedEntries() {
  const duplicate = packedCurrentFixture();
  fs.appendFileSync(duplicate.packedPath, duplicate.canonical + '\n', 'ascii');
  assert.strictEqual(gitStorage.registeredGitMetadataReceipt(duplicate.root).valid, false,
    'duplicate canonical current packed entries must fail closed');

  const peeled = packedCurrentFixture();
  fs.writeFileSync(peeled.packedPath,
    peeled.source.replace(peeled.canonical,
      peeled.canonical + '\n^' + peeled.oid), 'ascii');
  assert.strictEqual(gitStorage.registeredGitMetadataReceipt(peeled.root).valid, false,
    'peeled annotation after a branch current entry must fail closed');

  const absent = packedCurrentFixture();
  fs.writeFileSync(path.join(absent.root, '.git', 'HEAD'),
    'ref: refs/heads/true-unborn-r9\n', 'ascii');
  assert.strictEqual(gitStorage.registeredGitMetadataReceipt(absent.root).valid, true,
    'an exact current ref absent from loose and packed storage must remain unborn');
}

function provePackedCurrentEntryClassification() {
  proveMalformedPackedCurrentEntries();
  proveDuplicatePeeledAndAbsentPackedEntries();
}

function proveRepairLoop2Contracts() {
  const failures = [];
  for (const [label, contract] of [
    ['nested confinement', proveNestedGitDirectoryConfinement],
    ['supported heads grammar', proveSupportedHeadRefGrammar],
    ['packed current classification', provePackedCurrentEntryClassification]
  ]) {
    try {
      contract();
    } catch (err) {
      failures.push(label + ': ' + err.message);
    }
  }
  assert.deepStrictEqual(failures, [], 'repair-loop verifier contracts must all pass');
}

function makeDanglingEntry(entry, label) {
  const missing = path.join(os.tmpdir(), 'reddog-missing-' + label + '-'
    + Date.now() + '-' + Math.random().toString(16).slice(2));
  assert.strictEqual(fs.existsSync(missing), false, label + ' target must be absent');
  fs.mkdirSync(path.dirname(entry), { recursive: true });
  fs.symlinkSync(missing, entry, process.platform === 'win32' ? 'junction' : 'dir');
  assert(fs.lstatSync(entry).isSymbolicLink(), label + ' entry must exist without following');
  assert.strictEqual(fs.existsSync(entry), false,
    label + ' must reproduce follow-target absence');
}

function proveDanglingReceiptControl(label, relative) {
  const root = newRepo(true);
  const entry = path.join(root, '.git', ...relative.split('/'));
  if (relative === 'info/exclude') fs.unlinkSync(entry);
  makeDanglingEntry(entry, label);
  assert.strictEqual(gitStorage.registeredGitMetadataReceipt(root).valid, false);
  if (relative === 'objects/info/alternates') assertBlocked(root, label);
}

function proveDanglingWorktreeConfig(label) {
  const root = newRepo(true);
  cp.execFileSync('git', ['config', 'extensions.worktreeConfig', 'true'], { cwd: root });
  makeDanglingEntry(path.join(root, '.git', 'config.worktree'), label);
  const receipt = gitStorage.registeredGitMetadataReceipt(root);
  assert.strictEqual(receipt.valid, false);
  assert.strictEqual(receipt.worktree_config_state, 'invalid');
}

function proveDanglingPlainControl(label) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-plain-control-'));
  roots.push(root);
  const entry = path.join(root, 'optional-control');
  makeDanglingEntry(entry, label);
  assert.strictEqual(gitStorage.plainControlFile(entry), false);
}

function proveDanglingRootGit(label) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-empty-root-'));
  roots.push(root);
  assert.strictEqual(api.governedGitStatus(root, 8000), '');
  makeDanglingEntry(path.join(root, '.git'), label);
  assert(api.governedGitStatus(root, 8000).startsWith('[git context unavailable:'));
}

function proveRootGitLookupError() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-lookup-error-'));
  roots.push(root);
  const errorEntry = path.join(root, '.git');
  const originalLstat = fs.lstatSync;
  fs.lstatSync = function(candidate) {
    if (path.resolve(String(candidate)) === errorEntry) {
      const error = new Error('synthetic lookup denial');
      error.code = 'EACCES';
      throw error;
    }
    return originalLstat.apply(this, arguments);
  };
  try { assert(api.governedGitStatus(root, 8000).startsWith('[git context unavailable:')); }
  finally { fs.lstatSync = originalLstat; }
}

function noFollowContracts() {
  return [
    ['forbidden alternates', (label) => proveDanglingReceiptControl(label,
      'objects/info/alternates')],
    ['optional config.worktree', proveDanglingWorktreeConfig],
    ['optional info/exclude', (label) => proveDanglingReceiptControl(label, 'info/exclude')],
    ['direct commondir', (label) => proveDanglingReceiptControl(label, 'commondir')],
    ['plainControlFile', proveDanglingPlainControl],
    ['root .git', proveDanglingRootGit],
    ['lookup error', proveRootGitLookupError]
  ];
}

function proveNoFollowPresenceClassification() {
  const failures = [];
  for (const [label, contract] of noFollowContracts()) {
    try { contract(label); } catch (err) { failures.push(label + ': ' + err.message); }
  }
  assert.deepStrictEqual(failures, [], 'all no-follow presence sites must pass');
}

function refFixture(mode) {
  const fixture = mode === 'direct' ? { root: newRepo(true) } : linkedRepo();
  return { fixture, root: fixture.linked || fixture.root,
    common: fixture.common || path.join(fixture.root, '.git') };
}

function proveDanglingFinalRef(mode) {
  const item = refFixture(mode);
  const refName = fs.readFileSync(path.join(item.fixture.admin || item.common, 'HEAD'),
    'ascii').trim().replace(/^ref:\s*/, '');
  const loose = path.join(item.common, ...refName.split('/'));
  fs.unlinkSync(loose);
  makeDanglingEntry(loose, mode + '-current-loose');
  assert.strictEqual(gitStorage.registeredGitMetadataReceipt(item.root).valid, false);
  assertBlocked(item.root, mode + ' dangling final current ref');
}

function proveDanglingIntermediateRef(mode) {
  const item = refFixture(mode);
  const admin = item.fixture.admin || item.common;
  fs.writeFileSync(path.join(admin, 'HEAD'), 'ref: refs/heads/topic/deep\n', 'ascii');
  makeDanglingEntry(path.join(item.common, 'refs', 'heads', 'topic'),
    mode + '-current-parent');
  assert.strictEqual(gitStorage.registeredGitMetadataReceipt(item.root).valid, false);
  assertBlocked(item.root, mode + ' dangling intermediate current-ref parent');
}

function proveMissingHeadsDirectory() {
  const root = newRepo(true);
  fs.rmSync(path.join(root, '.git', 'refs', 'heads'), { recursive: true, force: true });
  assert.strictEqual(gitStorage.registeredGitMetadataReceipt(root).valid, false);
}

function proveCurrentRefNoFollowParentChain() {
  const failures = [];
  const check = (label, contract) => {
    try { contract(); } catch (err) { failures.push(label + ': ' + err.message); }
  };
  for (const mode of ['direct', 'linked']) {
    check(mode + ' dangling final current ref', () => proveDanglingFinalRef(mode));
  }
  for (const mode of ['direct', 'linked']) {
    check(mode + ' dangling intermediate current-ref parent',
      () => proveDanglingIntermediateRef(mode));
  }
  check('missing required refs/heads', proveMissingHeadsDirectory);
  assert.deepStrictEqual(failures, [], 'all current-ref parent-chain sites must pass');
}

function proveRepairLoop3Contracts() {
  const failures = [];
  for (const [label, contract] of [
    ['no-follow entry state', proveNoFollowPresenceClassification],
    ['current-ref parent chain', proveCurrentRefNoFollowParentChain]
  ]) {
    try {
      contract();
    } catch (err) {
      failures.push(label + ': ' + err.message);
    }
  }
  assert.deepStrictEqual(failures, [], 'repair-loop 3 verifier contracts must all pass');
}

function run() {
  proveRepairLoop3Contracts();
  proveRepairLoop2Contracts();
}

if (require.main === module) {
  try { run(); } finally { cleanup(); }
  console.log('RedDog governed Git topology/ref contracts: PASS');
}

module.exports = { run, proveRepairLoop2Contracts, proveRepairLoop3Contracts };
