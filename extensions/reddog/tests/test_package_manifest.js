'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const surface = require('./reddog_package_surface_contract');
require('./test_webview_security');

const pkg = JSON.parse(fs.readFileSync(path.join(surface.extDir, 'package.json'), 'utf8'));
const extensionSource = fs.readFileSync(path.join(surface.extDir, 'extension.js'), 'utf8');

assert.deepStrictEqual(pkg.capabilities, {
  untrustedWorkspaces: { supported: false },
  virtualWorkspaces: { supported: false }
});
assert.strictEqual(pkg.publisher, 'foundups');
assert.strictEqual(pkg.version, '0.4.126');
assert.strictEqual(pkg.main, './extension.js');
for (const key of ['reddog.allowEvaluationFallback',
  'foundupsFusion.allowEvaluationFallback']) {
  const setting = pkg.contributes.configuration.properties[key];
  assert.deepStrictEqual({ type: setting.type, default: setting.default },
    { type: 'boolean', default: false });
}
assert(extensionSource.includes(
  "allowEvaluationFallback: reddogConfigValue('allowEvaluationFallback', false) === true"
));
assert(extensionSource.includes("require('./webview_security')"));
assert(extensionSource.includes('webviewSecurity.createWebviewSecurity(panel.webview.cspSource)'));
assert(extensionSource.includes('http-equiv="Content-Security-Policy"'));
assert(extensionSource.includes('content="${escapedCspPolicy}"'));
assert(extensionSource.includes('<script nonce="${escapedCspNonce}">'));
assert(!extensionSource.includes('\n  <script>'));
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
assert.strictEqual(surface.EXPECTED_RUNTIME_FILES.length, 63);
assert.strictEqual(surface.EXPECTED_PACKAGE_FILES.length, 67);
const packageReceipt = surface.packageSurfaceReceipt(surface.EXPECTED_PACKAGE_FILES);
assert.strictEqual(packageReceipt.file_count, 67);
assert(packageReceipt.raw_bytes > 0);
assert.strictEqual(packageReceipt.raw_byte_cap, 1024 * 1024);
assert.strictEqual(packageReceipt.within_cap, true);
assert.strictEqual(packageReceipt.schema_version, 'reddog_package_surface_receipt.v2');
assert.strictEqual(packageReceipt.text_eol_policy, 'reddog_package_eol_policy.v1');
assert.strictEqual(packageReceipt.text_eol, 'lf');
assert.strictEqual(packageReceipt.text_file_count, 66);
assert.strictEqual(packageReceipt.binary_file_count, 1);
assert.match(packageReceipt.eol_policy_digest, /^sha256:[0-9a-f]{64}$/);
assert.match(packageReceipt.content_digest, /^sha256:[0-9a-f]{64}$/);
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
