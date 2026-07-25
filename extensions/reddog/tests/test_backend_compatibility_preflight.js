'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const preflight = require('../backend_compatibility_preflight');
const repoRoot = path.resolve(__dirname, '..', '..', '..');

function writeFixture(mutator) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-backend-'));
  for (const relativePath of preflight.REQUIRED_BRIDGE_FILES) {
    const target = path.join(root, relativePath);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.copyFileSync(path.join(repoRoot, relativePath), target);
  }
  for (const relativePath of preflight.REQUIRED_REPOSITORY_MARKERS) {
    const target = path.join(root, relativePath);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, '# repository marker\n', 'utf8');
  }
  const manifest = JSON.parse(
    fs.readFileSync(path.join(repoRoot, preflight.BACKEND_MANIFEST_PATH), 'utf8')
  );
  if (typeof mutator === 'function') {
    mutator(manifest, root);
  }
  const manifestPath = path.join(root, preflight.BACKEND_MANIFEST_PATH);
  fs.mkdirSync(path.dirname(manifestPath), { recursive: true });
  const raw = Buffer.from(JSON.stringify(manifest), 'utf8');
  fs.writeFileSync(manifestPath, raw);
  return { root, manifestPath };
}

function runFixture(fixture) {
  return preflight.runBackendCompatibilityPreflight(fixture.root);
}

{
  const fixture = writeFixture();
  const result = runFixture(fixture);
  assert.strictEqual(result.passed, true);
  assert.strictEqual(result.backend_manifest_integrity_verified, true);
  assert.strictEqual(result.backend_api_version, 1);
  assert.strictEqual(result.rejection_reasons.length, 0);
  assert.strictEqual(result.workspace_root_digest.startsWith('sha256:'), true);
  assert.strictEqual(result.backend_evidence_digest.startsWith('sha256:'), true);
  assert.strictEqual(JSON.stringify(result).includes(fixture.root), false);
  fs.rmSync(fixture.root, { recursive: true, force: true });
}

for (const invalidRoot of ['', ' ', null, undefined, false, 0]) {
  const result = preflight.runBackendCompatibilityPreflight(invalidRoot);
  assert.strictEqual(result.passed, false);
  assert.deepStrictEqual(result.rejection_reasons, ['workspace_root_missing']);
}

{
  const fixture = writeFixture((manifest) => {
    manifest.backend_api_version = 99;
  });
  const result = runFixture(fixture);
  assert.strictEqual(result.passed, false);
  assert(result.rejection_reasons.includes('backend_manifest_integrity_mismatch'));
  assert(preflight.validateManifest({
    ...JSON.parse(fs.readFileSync(path.join(repoRoot, preflight.BACKEND_MANIFEST_PATH), 'utf8')),
    backend_api_version: 99
  }).includes('backend_api_version_mismatch'));
  fs.rmSync(fixture.root, { recursive: true, force: true });
}

{
  const fixture = writeFixture((manifest) => {
    manifest.required_bridge_files.pop();
  });
  const result = runFixture(fixture);
  assert.strictEqual(result.passed, false);
  assert(result.rejection_reasons.includes('backend_manifest_integrity_mismatch'));
  const malformed = JSON.parse(
    fs.readFileSync(path.join(repoRoot, preflight.BACKEND_MANIFEST_PATH), 'utf8')
  );
  malformed.required_bridge_files.pop();
  assert(preflight.validateManifest(malformed).includes('backend_bridge_contract_mismatch'));
  fs.rmSync(fixture.root, { recursive: true, force: true });
}

{
  const fixture = writeFixture();
  fs.writeFileSync(
    path.join(fixture.root, preflight.REQUIRED_BRIDGE_FILES[0]),
    '# tampered bridge\n',
    'utf8'
  );
  const result = runFixture(fixture);
  assert.strictEqual(result.passed, false);
  assert(
    result.rejection_reasons.includes(
      'required_bridge_integrity_mismatch:' + preflight.REQUIRED_BRIDGE_FILES[0]
    )
  );
  fs.rmSync(fixture.root, { recursive: true, force: true });
}

{
  const fixture = writeFixture();
  fs.rmSync(path.join(fixture.root, preflight.REQUIRED_BRIDGE_FILES[0]));
  const result = runFixture(fixture);
  assert.strictEqual(result.passed, false);
  assert(result.rejection_reasons.some((reason) => reason.startsWith('required_bridge_missing_or_unsafe:')));
  fs.rmSync(fixture.root, { recursive: true, force: true });
}

{
  const fixture = writeFixture();
  fs.rmSync(fixture.manifestPath);
  const result = runFixture(fixture);
  assert.strictEqual(result.passed, false);
  assert.deepStrictEqual(result.rejection_reasons, ['backend_manifest_missing_or_unsafe']);
  fs.rmSync(fixture.root, { recursive: true, force: true });
}

{
  const fixture = writeFixture();
  fs.writeFileSync(fixture.manifestPath, '{', 'utf8');
  const result = preflight.runBackendCompatibilityPreflight(fixture.root);
  assert.strictEqual(result.passed, false);
  assert.deepStrictEqual(result.rejection_reasons, ['backend_manifest_invalid']);
  fs.rmSync(fixture.root, { recursive: true, force: true });
}

{
  const fixture = writeFixture();
  fs.writeFileSync(fixture.manifestPath, 'x'.repeat(preflight.MAX_MANIFEST_BYTES + 1), 'utf8');
  const result = runFixture(fixture);
  assert.strictEqual(result.passed, false);
  assert.deepStrictEqual(result.rejection_reasons, ['backend_manifest_size_invalid']);
  fs.rmSync(fixture.root, { recursive: true, force: true });
}

{
  const fixture = writeFixture();
  const target = path.join(fixture.root, preflight.REQUIRED_REPOSITORY_MARKERS[0]);
  fs.rmSync(target);
  fs.mkdirSync(target);
  const result = runFixture(fixture);
  assert.strictEqual(result.passed, false);
  assert(result.rejection_reasons.some((reason) => reason.startsWith('repository_marker_missing_or_unsafe:')));
  fs.rmSync(fixture.root, { recursive: true, force: true });
}

{
  const fixture = writeFixture((manifest) => {
    manifest.product = 'secret-value-must-not-be-reflected';
  });
  const result = runFixture(fixture);
  assert.strictEqual(result.passed, false);
  assert(result.rejection_reasons.includes('backend_manifest_integrity_mismatch'));
  assert.strictEqual(JSON.stringify(result).includes('secret-value-must-not-be-reflected'), false);
  const malformed = JSON.parse(
    fs.readFileSync(path.join(repoRoot, preflight.BACKEND_MANIFEST_PATH), 'utf8')
  );
  malformed.product = 'other-product';
  assert(preflight.validateManifest(malformed).includes('backend_product_mismatch'));
  fs.rmSync(fixture.root, { recursive: true, force: true });
}

{
  const fixture = writeFixture();
  const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-backend-outside-'));
  const sourceScripts = path.join(fixture.root, 'scripts');
  const outsideScripts = path.join(outside, 'scripts');
  fs.renameSync(sourceScripts, outsideScripts);
  fs.symlinkSync(
    outsideScripts,
    sourceScripts,
    process.platform === 'win32' ? 'junction' : 'dir'
  );
  const result = runFixture(fixture);
  assert.strictEqual(result.passed, false);
  assert.deepStrictEqual(result.rejection_reasons, ['backend_manifest_missing_or_unsafe']);
  fs.rmSync(fixture.root, { recursive: true, force: true });
  fs.rmSync(outside, { recursive: true, force: true });
}

if (process.platform !== 'win32') {
  const fixture = writeFixture();
  const target = path.join(fixture.root, preflight.REQUIRED_BRIDGE_FILES[0]);
  fs.rmSync(target);
  fs.symlinkSync(__filename, target);
  const result = runFixture(fixture);
  assert.strictEqual(result.passed, false);
  assert(result.rejection_reasons.some((reason) => reason.startsWith('required_bridge_missing_or_unsafe:')));
  fs.rmSync(fixture.root, { recursive: true, force: true });
}

{
  const source = fs.readFileSync(path.join(__dirname, '..', 'backend_compatibility_preflight.js'), 'utf8');
  for (const forbidden of ['execFile', 'spawn(', 'subprocess', 'holo_index.py --index']) {
    assert.strictEqual(source.includes(forbidden), false, 'forbidden runtime capability: ' + forbidden);
  }
}

console.log('backend compatibility preflight tests passed');
