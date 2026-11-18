'use strict';

const { assert, fs, path, fixtureRoot, executableFile, validSignature,
  createResolver, cleanup } = require('./governed_git_executable_test_helpers');

function proveLexicalResolution() {
  const root = fixtureRoot();
  const first = path.join(root, 'first');
  const second = path.join(root, 'second');
  const firstGit = executableFile(first, 'git.EXE', 'first');
  executableFile(second, 'git.EXE', 'second');
  const resolver = createResolver();
  const binding = resolver.bind({
    Path: [first, second].join(path.delimiter), PATHEXT: '.EXE;.CMD'
  });
  assert.strictEqual(binding.canonical_path, fs.realpathSync(firstGit));

  const preferred = executableFile(first, 'git.CMD', 'preferred');
  const extensionBinding = resolver.bind({
    Path: first, PATHEXT: '.CMD;.EXE'
  }, { cache: false });
  assert.strictEqual(extensionBinding.canonical_path, fs.realpathSync(preferred));
  assert.throws(() => resolver.bind({ Path: path.join(root, 'missing'), PATHEXT: '.EXE' },
    { cache: false }), /governed_git_executable_not_found/);
}

function proveStableIdentityAndPathIndependence() {
  const root = fixtureRoot();
  const first = path.join(root, 'first');
  const second = path.join(root, 'second');
  const original = executableFile(first, 'git.EXE', 'original');
  executableFile(second, 'git.EXE', 'replacement');
  const source = { Path: first, PATHEXT: '.EXE' };
  const resolver = createResolver();
  const binding = resolver.bind(source);
  source.Path = second;
  assert.strictEqual(resolver.revalidate(binding).canonical_path, fs.realpathSync(original));
  fs.writeFileSync(original, 'changed!');
  assert.throws(() => resolver.revalidate(binding), /governed_git_executable_changed/);
}

function proveLinksAndSignaturePolicy() {
  const root = fixtureRoot();
  const source = executableFile(root, 'source.EXE', 'same bytes');
  const hardlinkDir = path.join(root, 'hardlink');
  fs.mkdirSync(hardlinkDir);
  const hardlink = path.join(hardlinkDir, 'git.EXE');
  fs.linkSync(source, hardlink);
  const hardlinkBinding = createResolver().bind({ Path: hardlinkDir, PATHEXT: '.EXE' });
  assert.strictEqual(hardlinkBinding.start_identity.nlink >= 2, true);

  const symlinkDir = path.join(root, 'symlink');
  fs.mkdirSync(symlinkDir);
  const symlink = path.join(symlinkDir, 'git.EXE');
  try {
    fs.symlinkSync(source, symlink, 'file');
    assert.throws(() => createResolver().bind({ Path: symlinkDir, PATHEXT: '.EXE' }),
      /governed_git_executable_link_denied/);
  } catch (error) {
    if (!error || !['EPERM', 'EACCES', 'UNKNOWN'].includes(error.code)) throw error;
  }
  assert.throws(() => createResolver({ verifySignature: () => ({ status: 'invalid' }) })
    .bind({ Path: hardlinkDir, PATHEXT: '.EXE' }), /governed_git_signature_invalid/);
}

function proveBoundInvocationAndPortableProof() {
  const root = fixtureRoot();
  const directory = path.join(root, 'bin');
  const target = executableFile(directory, 'git.EXE', 'bound executable');
  let observed = null;
  const resolver = createResolver({
    execFileSync: (file, args, options) => {
      observed = { file, args, options };
      return 'ok';
    }
  });
  const binding = resolver.bind({ Path: directory, PATHEXT: '.EXE' });
  const output = resolver.execFileSync(binding, ['version'], {
    env: { PATH: 'attacker', Path: 'attacker', PATHEXT: '.CMD', SAFE: 'yes' }
  });
  assert.strictEqual(output, 'ok');
  assert.strictEqual(observed.file, fs.realpathSync(target));
  assert.deepStrictEqual(observed.args, ['version']);
  assert.strictEqual(observed.options.env.PATH, undefined);
  assert.strictEqual(observed.options.env.Path, undefined);
  assert.strictEqual(observed.options.env.PATHEXT, undefined);
  assert.strictEqual(observed.options.env.SAFE, 'yes');
  assert.match(binding.sha256, /^[a-f0-9]{64}$/);
  assert.strictEqual(binding.size, Buffer.byteLength('bound executable'));
  assert.strictEqual(binding.signature.status, 'valid');
  assert.strictEqual(binding.schema_version, 'reddog_governed_git_executable.v1');
  provePublicReceipt(binding, target);
  provePortableProof(directory, target);
}

function provePublicReceipt(binding, gitPath) {
  const executable = require('../governed_git_executable');
  const publicReceipt = executable.toPublicExecutableReceipt(binding);
  const strings = serializedStrings(publicReceipt);
  assert.strictEqual(Object.hasOwn(publicReceipt, 'canonical_path'), false);
  assert.strictEqual(strings.includes(gitPath), false);
  if (publicReceipt.signature.verifier) {
    assert.strictEqual(Object.hasOwn(publicReceipt.signature.verifier, 'canonical_path'), false);
    assert.strictEqual(Object.hasOwn(publicReceipt.signature.verifier,
      'system_root_containment_proof'), true);
  }
  assert.strictEqual(binding.canonical_path, gitPath);
}

function serializedStrings(value) {
  if (typeof value === 'string') return [value];
  if (Array.isArray(value)) return value.flatMap(serializedStrings);
  if (!value || typeof value !== 'object') return [];
  return Object.values(value).flatMap(serializedStrings);
}

function provePortableProof(directory, target) {
  const native = createResolver({ platform: process.platform,
    verifySignature: process.platform === 'win32'
      ? () => validSignature(target) : undefined });
  const nativeBinding = native.bind({
    [process.platform === 'win32' ? 'Path' : 'PATH']: directory,
    PATHEXT: '.EXE'
  });
  assert(nativeBinding.start_identity.portable);
  assert(nativeBinding.start_identity.native);
  assert.strictEqual(nativeBinding.signature.status,
    process.platform === 'win32' ? 'valid' : 'not_applicable');
}

function run() {
  proveLexicalResolution();
  proveStableIdentityAndPathIndependence();
  proveLinksAndSignaturePolicy();
  proveBoundInvocationAndPortableProof();
}

try { run(); } finally { cleanup(); }
console.log('RedDog governed Git executable provenance contracts: PASS');
