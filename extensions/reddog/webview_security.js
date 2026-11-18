'use strict';

const crypto = require('crypto');

const NONCE_BYTES = 16;
const CSP_SOURCE = /^[A-Za-z][A-Za-z0-9+.-]*:(?:\/\/[A-Za-z0-9._:-]+)?$/;

function createWebviewSecurity(cspSource, randomBytes) {
  const source = String(cspSource || '');
  if (!CSP_SOURCE.test(source) || source.length > 512) {
    throw new Error('reddog_webview_csp_source_invalid');
  }
  const bytes = (randomBytes || crypto.randomBytes)(NONCE_BYTES);
  if (!Buffer.isBuffer(bytes) || bytes.length !== NONCE_BYTES) {
    throw new Error('reddog_webview_nonce_invalid');
  }
  const nonce = bytes.toString('hex');
  return Object.freeze({
    nonce,
    policy: `default-src 'none'; img-src ${source}; ` +
      `style-src 'unsafe-inline'; script-src 'nonce-${nonce}';`
  });
}

module.exports = Object.freeze({ NONCE_BYTES, createWebviewSecurity });
