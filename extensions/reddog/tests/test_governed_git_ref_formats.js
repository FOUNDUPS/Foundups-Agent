'use strict';

const assert = require('assert');
const cp = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const governed = require('../governed_git_context.js');
const storage = require('../governed_git_storage.js');

const roots = [];

function git(root, args, options) {
  return cp.execFileSync('git', ['-C', root, ...args], options);
}

function createRepo(format) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-ref-format-'));
  roots.push(root);
  const init = ['init', '-q'];
  if (format === 'sha256') init.push('--object-format=sha256');
  init.push(root);
  cp.execFileSync('git', init);
  git(root, ['config', 'core.autocrlf', 'false']);
  fs.writeFileSync(path.join(root, 'allowed.py'), 'allowed = true\n', 'utf8');
  git(root, ['add', 'allowed.py']);
  git(root, ['-c', 'user.name=RedDog Test', '-c',
    'user.email=reddog@example.invalid', 'commit', '-qm', 'fixture']);
  return root;
}

function receiptValid(root) {
  return storage.registeredGitMetadataReceipt(root).valid;
}

function headPath(root) {
  return git(root, ['rev-parse', '--absolute-git-dir'], { encoding: 'utf8' })
    .trim() + path.sep + 'HEAD';
}

function writeHead(root, value) {
  fs.writeFileSync(headPath(root), value + '\n', 'utf8');
}

function currentRef(root) {
  return fs.readFileSync(headPath(root), 'utf8').trim().replace(/^ref:\s*/, '');
}

function oid(root) {
  return git(root, ['rev-parse', '--verify', 'HEAD^{commit}'], { encoding: 'utf8' }).trim();
}

function commonConfig(root) {
  return git(root, ['rev-parse', '--path-format=absolute', '--git-common-dir'], {
    encoding: 'utf8'
  }).trim() + path.sep + 'config';
}

function rewriteObjectFormat(root, setting) {
  const config = commonConfig(root);
  const before = fs.readFileSync(config, 'utf8');
  assert(/^\s*objectformat\s*=.*$/im.test(before),
    'fixture must contain objectFormat setting');
  const after = before.replace(/^\s*objectformat\s*=.*$/im, '\t' + setting);
  fs.writeFileSync(config, after, 'utf8');
}

function checkRefStatus(refName) {
  return cp.spawnSync('git', ['check-ref-format', refName], { encoding: 'utf8' }).status;
}

function proveGitAcceptedNames() {
  for (const branch of ['feature+r9', '\u7279\u6027-r9']) {
    const root = createRepo('sha1');
    const refName = 'refs/heads/' + branch;
    assert.strictEqual(checkRefStatus(refName), 0, refName + ' must be Git-valid');
    git(root, ['branch', branch]);
    writeHead(root, 'ref: ' + refName);
    assert.strictEqual(oid(root).length, 40, refName + ' must resolve semantically');
    assert.strictEqual(receiptValid(root), true, refName + ' must be receipt-valid');
  }
}

function proveGitRejectedNames() {
  const invalid = [
    '/leading', 'trailing/', '/empty', 'two//parts', 'two..dots', 'at@{brace',
    '.hidden', 'topic/.hidden', 'trailing.', 'topic/trailing.', 'name.lock',
    'topic/name.lock', 'has space', 'has~tilde', 'has^caret', 'has:colon',
    'has?question', 'has*star', 'has[bracket', 'has\\slash', 'has\u0001control',
    'has\u007fdelete'
  ];
  for (const branch of invalid) {
    const root = createRepo('sha1');
    const refName = 'refs/heads/' + branch;
    assert.notStrictEqual(checkRefStatus(refName), 0, refName + ' must be Git-invalid');
    writeHead(root, 'ref: ' + refName);
    assert.strictEqual(receiptValid(root), false, refName + ' must fail closed');
  }
}

function proveLooseAndDetached(format, expectedLength) {
  const loose = createRepo(format);
  assert.strictEqual(oid(loose).length, expectedLength);
  assert.strictEqual(receiptValid(loose), true, format + ' loose ref');
  const detached = createRepo(format);
  const detachedOid = oid(detached);
  writeHead(detached, detachedOid);
  assert.strictEqual(receiptValid(detached), true, format + ' detached HEAD');
}

function provePacked(format, expectedLength) {
  const root = createRepo(format);
  const refName = currentRef(root);
  assert.strictEqual(oid(root).length, expectedLength);
  git(root, ['pack-refs', '--all']);
  assert.strictEqual(fs.existsSync(path.join(root, '.git', ...refName.split('/'))), false);
  assert.strictEqual(receiptValid(root), true, format + ' packed current ref');
}

function createLinked(format) {
  const main = createRepo(format);
  const linked = main + '-linked';
  git(main, ['worktree', 'add', '-q', '-b', 'linked-r9', linked]);
  roots.push(linked);
  return { main, linked };
}

function proveLinked(format, expectedLength) {
  const loose = createLinked(format);
  assert.strictEqual(oid(loose.linked).length, expectedLength);
  assert.strictEqual(receiptValid(loose.linked), true, format + ' linked loose ref');
  const packed = createLinked(format);
  git(packed.main, ['pack-refs', '--all']);
  assert.strictEqual(receiptValid(packed.linked), true, format + ' linked packed ref');
  git(packed.linked, ['checkout', '-q', '--detach']);
  assert.strictEqual(receiptValid(packed.linked), true, format + ' linked detached HEAD');
}

function malformedValues() {
  return [39, 41, 63, 65].map((length) => 'a'.repeat(length)).concat([
    'g' + 'a'.repeat(39), 'g' + 'a'.repeat(63)
  ]);
}

function proveMalformedDetached(format) {
  for (const malformed of malformedValues()) {
    const root = createRepo(format);
    writeHead(root, malformed);
    assert.strictEqual(receiptValid(root), false,
      format + ' detached length ' + malformed.length + ' must fail');
  }
}

function proveMalformedLoose(format) {
  for (const malformed of malformedValues()) {
    const root = createRepo(format);
    const refName = currentRef(root);
    fs.writeFileSync(path.join(root, '.git', ...refName.split('/')),
      malformed + '\n', 'ascii');
    assert.strictEqual(receiptValid(root), false,
      format + ' loose length ' + malformed.length + ' must fail');
  }
}

function proveMalformedPacked(format) {
  for (const malformed of malformedValues()) {
    const root = createRepo(format);
    const refName = currentRef(root);
    fs.unlinkSync(path.join(root, '.git', ...refName.split('/')));
    fs.writeFileSync(path.join(root, '.git', 'packed-refs'),
      '# pack-refs with: peeled fully-peeled sorted\n' + malformed + ' ' + refName + '\n',
      'ascii');
    assert.strictEqual(receiptValid(root), false,
      format + ' packed length ' + malformed.length + ' must fail');
  }
}

function prepareRefMode(root, mode) {
  if (mode === 'packed') git(root, ['pack-refs', '--all']);
  if (mode === 'detached') git(root, ['checkout', '-q', '--detach']);
}

function proveSha256ConfigSpelling(root, variant, topology) {
  prepareRefMode(root, variant.mode);
  rewriteObjectFormat(root, variant.setting);
  assert.strictEqual(git(root, ['config', '--get', 'extensions.objectFormat'], {
    encoding: 'utf8'
  }).trim(), 'sha256', topology + ' ' + variant.label + ' config semantics');
  assert.strictEqual(oid(root).length, 64,
    topology + ' ' + variant.label + ' commit semantics');
  assert.strictEqual(receiptValid(root), true,
    topology + ' ' + variant.label + ' receipt');
}

function proveSha256ConfigSpellings() {
  const variants = [
    { label: 'canonical', setting: 'objectformat = sha256', mode: 'loose' },
    { label: 'quoted', setting: 'objectformat = "sha256"', mode: 'packed' },
    { label: 'hash-comment', setting: 'objectformat = sha256 # inline', mode: 'detached' },
    { label: 'semicolon-comment', setting: 'objectformat = sha256 ; inline', mode: 'loose' }
  ];
  for (const variant of variants) {
    proveSha256ConfigSpelling(createRepo('sha256'), variant, 'direct');
    const linked = createLinked('sha256');
    proveSha256ConfigSpelling(linked.linked, variant, 'linked');
  }
}

function installOidShape(root, placement, value) {
  const refName = currentRef(root);
  if (placement === 'detached') return writeHead(root, value);
  const loose = path.join(root, '.git', ...refName.split('/'));
  if (fs.existsSync(loose)) fs.unlinkSync(loose);
  if (placement === 'loose') return fs.writeFileSync(loose, value + '\n', 'ascii');
  return fs.writeFileSync(path.join(root, '.git', 'packed-refs'),
    '# pack-refs with: peeled fully-peeled sorted\n' + value + ' ' + refName + '\n', 'ascii');
}

function assertGitSemanticFailure(root, label) {
  fs.appendFileSync(path.join(root, 'allowed.py'), '# changed\n', 'utf8');
  const names = ['HEAD_SHA', 'FOUNDUP_REGISTRY_STATUS', 'TRACKED_PATHS', 'DIRTY_PATHS'];
  for (const name of names) {
    assert(governed.gitOutputs(root, [name])[0].startsWith('[git context unavailable:'),
      label + ' must fail ' + name + ' closed when requested alone');
  }
  const outputs = governed.gitOutputs(root, names);
  assert(outputs.every((value) => value.startsWith('[git context unavailable:')),
    label + ' must fail every named output closed');
  assert.strictEqual(governed.governedGitReadiness(root).ready, true,
    label + ' structural/config readiness must not claim command success');
  const snapshot = governed.governedGitSnapshot(root);
  assert(['status', 'stat', 'diff'].every((key) =>
    snapshot[key].startsWith('[git context unavailable:')),
  label + ' must fail the whole projection closed');
}

function proveCrossFormatShapesAreStructuralOnly() {
  for (const scenario of [
    { format: 'sha1', length: 64 }, { format: 'sha256', length: 40 }
  ]) {
    for (const placement of ['detached', 'loose', 'packed']) {
      const root = createRepo(scenario.format);
      installOidShape(root, placement, 'a'.repeat(scenario.length));
      assert.strictEqual(receiptValid(root), true,
        scenario.format + ' ' + placement + ' cross-format structural receipt');
      assertGitSemanticFailure(root, scenario.format + ' ' + placement + ' cross-format OID');
    }
  }
}

function sha256Supported() {
  const probe = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-sha256-probe-'));
  roots.push(probe);
  return cp.spawnSync('git', ['init', '-q', '--object-format=sha256', probe]).status === 0;
}

function proveObjectFormat(format, expectedLength) {
  proveLooseAndDetached(format, expectedLength);
  provePacked(format, expectedLength);
  proveLinked(format, expectedLength);
  proveMalformedDetached(format);
  proveMalformedLoose(format);
  proveMalformedPacked(format);
}

try {
  proveGitAcceptedNames();
  proveGitRejectedNames();
  proveObjectFormat('sha1', 40);
  if (sha256Supported()) {
    proveObjectFormat('sha256', 64);
    proveSha256ConfigSpellings();
    proveCrossFormatShapesAreStructuralOnly();
  }
  else console.log('RedDog SHA-256 Git fixtures: SKIP (local Git lacks object-format support)');
} finally {
  for (const root of roots.reverse()) {
    if (fs.existsSync(root)) fs.rmSync(root, { recursive: true, force: true });
  }
}

console.log('RedDog governed Git ref-format/object-format contracts: PASS');
