'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const surface = require('./reddog_package_surface_contract');

const pkg = JSON.parse(fs.readFileSync(path.join(surface.extDir, 'package.json'), 'utf8'));

assert.deepStrictEqual(pkg.capabilities, {
  untrustedWorkspaces: { supported: false },
  virtualWorkspaces: { supported: false }
});
assert.strictEqual(pkg.publisher, 'foundups');
assert.strictEqual(pkg.version, '0.4.103');
assert.strictEqual(pkg.main, './extension.js');
assert.deepStrictEqual(pkg.activationEvents, [
  'onCommand:reddog.open',
  'onCommand:foundupsFusion.open',
  'onCommand:reddog.setConversationSessionCredential',
  'onCommand:reddog.clearConversationSessionCredential',
  'onCommand:reddog.setPrincipalMemexDisclosure',
  'onCommand:reddog.clearPrincipalMemexDisclosure'
]);
assert.deepStrictEqual(
  pkg.contributes.commands.map((command) => `onCommand:${command.command}`),
  pkg.activationEvents
);
assert.deepStrictEqual(surface.deriveRuntimeFiles(), surface.EXPECTED_RUNTIME_FILES);
assert.strictEqual(surface.EXPECTED_RUNTIME_FILES.length, 61);
assert.strictEqual(surface.EXPECTED_PACKAGE_FILES.length, 65);
const packageReceipt = surface.packageSurfaceReceipt(surface.EXPECTED_PACKAGE_FILES);
assert.strictEqual(packageReceipt.file_count, 65);
assert(packageReceipt.raw_bytes > 0);
assert.strictEqual(packageReceipt.raw_byte_cap, 1024 * 1024);
assert.strictEqual(packageReceipt.within_cap, true);
const canonicalLicense = (value) => value.replace(/\r\n/g, '\n')
  .replace(/[ \t]+$/gm, '').trimEnd();
assert.strictEqual(
  canonicalLicense(fs.readFileSync(path.join(surface.extDir, 'LICENSE'), 'utf8')),
  canonicalLicense(fs.readFileSync(path.join(surface.extDir, '..', '..', 'LICENSE'), 'utf8')),
  'packaged license text must match the repository authority'
);
assert.deepStrictEqual(surface.readIgnoreRules(), surface.EXPECTED_IGNORE_RULES);
assert(fs.readFileSync(path.join(surface.extDir, 'backend_compatibility_async.js'), 'utf8')
  .includes("'backend_compatibility_worker.js'"));
assert(fs.readFileSync(path.join(surface.extDir, 'runtime_health_query.js'), 'utf8')
  .includes("'runtime_health_worker.js'"));
assert(fs.readFileSync(path.join(surface.extDir, 'start_operations_bridge.js'), 'utf8')
  .includes("'start_operations_python_bootstrap.py'"));

const rootJavaScript = fs.readdirSync(surface.extDir).filter((name) => name.endsWith('.js')).sort();
assert.deepStrictEqual(
  rootJavaScript,
  surface.EXPECTED_RUNTIME_FILES.filter((name) => name.endsWith('.js')),
  'every root JavaScript file must be in the runtime closure'
);

console.log('RedDog package manifest/runtime-closure contract: PASS ' +
  JSON.stringify(packageReceipt));
