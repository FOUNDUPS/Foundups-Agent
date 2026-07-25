'use strict';

const assert = require('assert');
const path = require('path');
const asyncCompatibility = require('../backend_compatibility_async');

const repoRoot = path.resolve(__dirname, '..', '..', '..');

(async () => {
  let eventLoopAdvanced = false;
  setTimeout(() => {
    eventLoopAdvanced = true;
  }, 0);
  const result = await asyncCompatibility.runBackendCompatibilityPreflightAsync(
    repoRoot
  );
  assert.strictEqual(result.passed, true);
  assert.strictEqual(eventLoopAdvanced, true);

  const rejected = await asyncCompatibility.runBackendCompatibilityPreflightAsync('');
  assert.strictEqual(rejected.passed, false);
  assert(rejected.rejection_reasons.includes('workspace_root_missing'));

  const messages = [];
  const state = {};
  const blocked = await asyncCompatibility.blockIncompatibleBackend(
    {},
    state,
    { postMessage: (message) => messages.push(message) },
    {
      detect: async () => {
        throw new Error('worker failed');
      },
      build: (installState) => ({
        ok: false,
        review_packet: installState.backend_compatibility
      }),
      post: (_webview, _stage, text) => messages.push({ text: text })
    }
  );
  assert.strictEqual(blocked, true);
  assert.strictEqual(state.lastReviewPacket.passed, false);
  assert.strictEqual(messages.length, 2);
  console.log('backend compatibility async tests passed');
})().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
