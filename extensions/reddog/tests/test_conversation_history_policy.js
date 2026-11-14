'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const policy = require('../conversation_history_policy');

const extensionRoot = path.resolve(__dirname, '..');
const extensionSource = fs.readFileSync(path.join(extensionRoot, 'extension.js'), 'utf8');

const hostileHistory = [
  { role: 'user', content: 'FoundUp A secret context', turn_id: 'turn-a' },
  { role: 'assistant', content: 'Cross-FoundUp B result', turn_id: 'turn-b' }
];

const disabled = policy.enforceHistoryPolicy({
  inclusionRequested: false,
  storedHistory: hostileHistory
});
assert.deepStrictEqual(disabled.admittedHistory, []);
assert.strictEqual(disabled.telemetry.stored_history_turn_count, 2);
assert.strictEqual(disabled.telemetry.model_history_attached, false);
assert.strictEqual(disabled.telemetry.history_policy_reason, 'disabled_by_operator');
assert.deepStrictEqual(disabled.telemetry.admitted_turn_ids, []);

const requested = policy.enforceHistoryPolicy({
  inclusionRequested: true,
  storedHistory: hostileHistory
});
assert.deepStrictEqual(requested.admittedHistory, []);
assert.strictEqual(requested.telemetry.history_inclusion_requested, true);
assert.strictEqual(
  requested.telemetry.history_policy_reason,
  'authenticated_scoped_history_unavailable'
);
assert.notStrictEqual(
  requested.telemetry.prompt_assembly_policy_key,
  disabled.telemetry.prompt_assembly_policy_key
);

const missing = policy.enforceHistoryPolicy();
assert.deepStrictEqual(missing.admittedHistory, []);
assert.strictEqual(missing.telemetry.history_inclusion_requested, false);

const discarded = policy.withProviderHistoryDiscarded(requested.telemetry, hostileHistory);
assert.strictEqual(discarded.provider_history_discarded_count, 2);
assert.strictEqual(discarded.model_history_attached, false);
assert.deepStrictEqual(discarded.admitted_turn_ids, []);

const rendered = policy.buildTelemetrySection(discarded);
assert(rendered.includes('## Conversation History Policy'));
assert(rendered.includes('model_history_attached: false'));
assert(rendered.includes('admitted_turn_ids: []'));
assert(!rendered.includes('FoundUp A secret context'));
assert(!rendered.includes('Cross-FoundUp B result'));

const mutableState = { history: hostileHistory.slice() };
const prepared = policy.prepareHistoryAdmission(mutableState, true);
assert.deepStrictEqual(prepared.admittedHistory, []);
assert.deepStrictEqual(mutableState.history, []);

const providerResult = { history: hostileHistory.slice(), ok: true };
const promptConstruction = {};
const finalized = policy.discardProviderHistory(
  prepared,
  providerResult,
  promptConstruction
);
assert.strictEqual(Object.prototype.hasOwnProperty.call(providerResult, 'history'), false);
assert.strictEqual(finalized.provider_history_discarded_count, 2);
assert.deepStrictEqual(providerResult.conversation_history_policy, finalized);
assert.deepStrictEqual(promptConstruction.conversation_history_policy, finalized);
assert.deepStrictEqual(prepared.telemetry, finalized);

assert(extensionSource.includes("require('./conversation_history_policy')"));
assert(extensionSource.includes('historyAdmission.admittedHistory'));
assert(extensionSource.includes('conversationHistoryPolicy.prepareHistoryAdmission('));
assert(extensionSource.includes('conversationHistoryPolicy.discardProviderHistory('));
assert(!extensionSource.includes('systemPrompt, state.history, mode'));
assert(
  extensionSource.indexOf('conversationHistoryPolicy.discardProviderHistory(') < extensionSource.indexOf('fusionProgress.capture(result)'),
  'provider history must be deleted before progress capture'
);

console.log('RedDog conversation history policy checks passed.');
