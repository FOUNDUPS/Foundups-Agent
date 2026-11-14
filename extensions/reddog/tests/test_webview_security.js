'use strict';

const assert = require('assert');
const security = require('../webview_security');

const deterministic = security.createWebviewSecurity(
  'vscode-webview://012-reddog',
  () => Buffer.alloc(security.NONCE_BYTES, 0xab)
);
assert.strictEqual(deterministic.nonce, 'ab'.repeat(security.NONCE_BYTES));
assert.strictEqual(
  deterministic.policy,
  "default-src 'none'; img-src vscode-webview://012-reddog; " +
    "style-src 'unsafe-inline'; script-src 'nonce-" + deterministic.nonce + "';"
);
assert(Object.isFrozen(deterministic));

for (const source of ['', "'unsafe-inline'", 'https://ok; script-src *', 'x y']) {
  assert.throws(() => security.createWebviewSecurity(source),
    /reddog_webview_csp_source_invalid/);
}
assert.throws(
  () => security.createWebviewSecurity('vscode-resource:', () => Buffer.alloc(15)),
  /reddog_webview_nonce_invalid/
);
assert.match(
  security.createWebviewSecurity('vscode-resource:').nonce,
  /^[a-f0-9]{32}$/
);

console.log('RedDog webview CSP/nonce contract: PASS');
