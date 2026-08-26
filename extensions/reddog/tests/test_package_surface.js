'use strict';

const assert = require('assert');
const cp = require('child_process');
const fs = require('fs');
const path = require('path');
const surface = require('./reddog_package_surface_contract');

function materializeFromIndex(files, autocrlf, target) {
  const prefix = `${target.replace(/\\/g, '/')}/`;
  const repoPaths = files.map((relative) => `extensions/reddog/${relative}`);
  const result = cp.spawnSync('git', [
    '-c', `core.autocrlf=${autocrlf}`, 'checkout-index', '--force',
    `--prefix=${prefix}`, '--', ...repoPaths
  ], {
    cwd: surface.repoRoot, encoding: 'utf8', shell: false, timeout: 30000,
    maxBuffer: 2 * 1024 * 1024
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`git checkout-index failed: ${String(result.stderr).slice(0, 500)}`);
  }
  return surface.digestPackageMembers(files, path.join(target, 'extensions', 'reddog'));
}

const first = surface.runVsceList();
const second = surface.runVsceList();

assert.deepStrictEqual(second, first, 'two vsce listings must be byte-order stable');
assert.strictEqual(new Set(first).size, first.length, 'package surface must not contain duplicates');
assert.deepStrictEqual([...first].sort(), surface.EXPECTED_PACKAGE_FILES);
assert.strictEqual(first.length, 67);
const receipt = surface.packageSurfaceReceipt(first);
const eol = surface.packageLineEndingPolicy(first);
assert.strictEqual(receipt.file_count, 67);
assert.strictEqual(receipt.raw_byte_cap, 1024 * 1024);
assert.strictEqual(receipt.within_cap, true);
assert.strictEqual(eol.schema_version, 'reddog_package_eol_policy.v1');
assert.strictEqual(eol.text_eol, 'lf');
assert.strictEqual(eol.text_file_count, 66);
assert.strictEqual(eol.binary_file_count, 1);
assert.match(eol.policy_digest, /^sha256:[0-9a-f]{64}$/);
assert.strictEqual(receipt.schema_version, 'reddog_package_surface_receipt.v2');
assert.strictEqual(receipt.text_eol_policy, eol.schema_version);
assert.strictEqual(receipt.text_eol, 'lf');
assert.strictEqual(receipt.text_file_count, 66);
assert.strictEqual(receipt.binary_file_count, 1);
assert.strictEqual(receipt.eol_policy_digest, eol.policy_digest);
assert.match(receipt.content_digest, /^sha256:[0-9a-f]{64}$/);

assert.strictEqual(surface.validatePackageMemberBytes(
  'extension.js', Buffer.from('const valid = true;\n', 'utf8')
), 'text');
assert.throws(() => surface.validatePackageMemberBytes(
  'extension.js', Buffer.from('const invalid = true;\r\n', 'utf8')
), /contains CR bytes/);
assert.throws(() => surface.validatePackageMemberBytes(
  'extension.js', Buffer.from('const invalid = true;\rnext\n', 'utf8')
), /contains CR bytes/);
assert.strictEqual(surface.validatePackageMemberBytes(
  'icon.png', Buffer.from([0x89, 0x50, 0x0d, 0x0a])
), 'binary');

const effective = surface.readEffectiveAttributes(first);
assert.strictEqual(surface.validateEffectiveAttributes(first, effective).length, 67);
const missing = new Map(effective);
missing.delete('extensions/reddog/extension.js');
assert.throws(() => surface.validateEffectiveAttributes(first, missing),
  /missing effective RedDog package attributes/);
const overridden = new Map(effective);
overridden.set('extensions/reddog/extension.js', new Map([
  ['text', 'set'], ['eol', 'crlf']
]));
assert.throws(() => surface.validateEffectiveAttributes(first, overridden),
  /not text\/eol=lf/);

const tempParent = path.resolve(surface.extDir, 'tests');
const tempRoot = fs.mkdtempSync(path.join(tempParent, '.reddog-package-materialization-'));
if (path.dirname(tempRoot) !== tempParent || !path.basename(tempRoot).startsWith(
  '.reddog-package-materialization-')) {
  throw new Error('unsafe RedDog materialization test root');
}
try {
  const oversizedRoot = path.join(tempRoot, 'oversized');
  fs.mkdirSync(oversizedRoot);
  const oversizedPath = path.join(oversizedRoot, 'extension.js');
  const oversized = fs.openSync(oversizedPath, 'w');
  try {
    fs.ftruncateSync(oversized, surface.MAX_PACKAGE_RAW_BYTES + 1);
  } finally {
    fs.closeSync(oversized);
  }
  assert.throws(() => surface.digestPackageMembers(['extension.js'], oversizedRoot),
    /package raw closure exceeds/);
  const enabled = materializeFromIndex(first, 'true', path.join(tempRoot, 'true'));
  const disabled = materializeFromIndex(first, 'false', path.join(tempRoot, 'false'));
  assert.strictEqual(enabled.raw_bytes, disabled.raw_bytes);
  assert.strictEqual(enabled.content_digest, disabled.content_digest);
  assert.deepStrictEqual(enabled.members, disabled.members);
} finally {
  fs.rmSync(tempRoot, { recursive: true, force: true });
}

console.log('RedDog deterministic 67-file package surface: PASS ' + JSON.stringify(receipt));
