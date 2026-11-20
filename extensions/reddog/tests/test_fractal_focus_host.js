'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const host = require('../fractal_focus_host');

function preflight(overrides) {
  const receipt = { applied: true, passed: true, foundup_id: 'hpc', receipt_id: 'receipt-1' };
  return Object.assign({
    passed: true,
    foundup_work_grounding_applied: true,
    foundup_work_grounding_passed: true,
    foundup_use_time_verified: true,
    foundup_id: 'hpc',
    foundup_work_grounding_receipt_id: 'receipt-1',
    typed_targets: { foundup_work_grounding: receipt }
  }, overrides || {});
}

assert.deepStrictEqual(host.modelFromPreflight({ passed: true,
  foundup_work_grounding_applied: false }, true), host.NONE);
assert.deepStrictEqual(host.modelFromPreflight(preflight(), false),
  { state: 'selected', foundupId: 'hpc', canAsk: false });
assert.deepStrictEqual(host.modelFromPreflight(preflight(), true),
  { state: 'selected', foundupId: 'hpc', canAsk: true });
assert.deepStrictEqual(host.modelFromPreflight(preflight({ passed: false }), true), host.UNAVAILABLE);
assert.deepStrictEqual(host.modelFromPreflight(preflight({ foundup_use_time_verified: false }), true), host.UNAVAILABLE);
assert.deepStrictEqual(host.modelFromPreflight(preflight({ foundup_id: 'HPC' }), true), host.UNAVAILABLE);
const newlineReceipt = { applied: true, passed: true, foundup_id: 'hpc\n', receipt_id: 'receipt-1' };
assert.deepStrictEqual(host.modelFromPreflight(preflight({ foundup_id: 'hpc\n',
  typed_targets: { foundup_work_grounding: newlineReceipt } }), true), host.UNAVAILABLE);
assert.deepStrictEqual(host.modelFromPreflight(preflight({
  foundup_work_grounding_receipt_id: ''
}), true), host.UNAVAILABLE);

const messages = [];
const webview = { postMessage: (message) => { messages.push(message); return true; } };
const state = { fractalFocusEpoch: 0, fractalFocusBinding: null, requestInFlight: false };
host.post(webview, state, host.modelFromPreflight(preflight(), false));
assert.strictEqual(state.fractalFocusBinding, null);
host.post(webview, state, host.modelFromPreflight(preflight(), true));
assert.deepStrictEqual(state.fractalFocusBinding, { foundupId: 'hpc', epoch: 2 });
assert.strictEqual(host.handleAsk(webview, state, { foundupId: 'hpc', epoch: 1 }), false);
assert.strictEqual(host.handleAsk(webview, state, { foundupId: 'vote', epoch: 2 }), false);
assert.strictEqual(host.handleAsk(webview, state, { foundupId: 'hpc', epoch: 2 }), true);
assert.deepStrictEqual(messages.at(-1), { command: 'fractalFocusPrefill', epoch: 2,
  question: 'What should I know about the hpc FoundUp?' });
host.post(webview, state, host.UNAVAILABLE);
assert.strictEqual(state.fractalFocusBinding, null);
assert.strictEqual(host.handleAsk(webview, state, { foundupId: 'hpc', epoch: 2 }), false);

const panelMessages = [];
let click = null;
const composer = { value: ' ', focused: false, focus() { this.focused = true; } };
const handlePanel = host.bindPanel({}, composer,
  (_container, _model, onAsk) => { click = onAsk; },
  (message) => panelMessages.push(message), () => false);
handlePanel({ command: 'fractalFocus', epoch: 7,
  model: { state: 'selected', foundupId: 'hpc', canAsk: true } });
click('hpc');
assert.deepStrictEqual(panelMessages, [
  { command: 'fractalFocusAsk', foundupId: 'hpc', epoch: 7 }
]);
assert.strictEqual(handlePanel({ command: 'fractalFocusPrefill', epoch: 7, question: 'scoped' }), false);
assert.strictEqual(composer.value, ' ');
composer.value = '';
assert.strictEqual(handlePanel({ command: 'fractalFocusPrefill', epoch: 6, question: 'stale' }), false);
assert.strictEqual(handlePanel({ command: 'fractalFocusPrefill', epoch: 7, question: 'scoped' }), true);
assert.strictEqual(composer.value, 'scoped');
assert.strictEqual(composer.focused, true);
composer.value = '';
assert.strictEqual(handlePanel({ command: 'fractalFocus', epoch: 8,
  model: { state: 'unavailable', foundupId: null, canAsk: false } }), true);
assert.strictEqual(handlePanel({ command: 'fractalFocus', epoch: 7,
  model: { state: 'selected', foundupId: 'hpc', canAsk: true } }), false);
assert.strictEqual(handlePanel({ command: 'fractalFocusPrefill', epoch: 8, question: 'stale' }), false);
assert.strictEqual(composer.value, '');

const source = fs.readFileSync(path.join(__dirname, '..', 'extension.js'), 'utf8');
const hostSource = fs.readFileSync(path.join(__dirname, '..', 'fractal_focus_host.js'), 'utf8');
assert(source.includes("require('./fractal_focus_front')"));
assert(source.includes('renderFractalFocus.toString()'));
assert(source.includes('fractalFocusHost.bindPanel.toString()'));
assert(source.includes('<script nonce="${escapedCspNonce}">'));
assert(hostSource.includes("composer.value !== ''"));
assert(!hostSource.includes('composer.value.trim()'));
assert(hostSource.includes('message.epoch !== epoch'));

console.log('RedDog fractal focus host contract: PASS');
