'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const policy = require('../conversation_plane_policy');
const continuationPrompt = require('../continuation_prompt');

const repoRoot = path.resolve(__dirname, '..', '..', '..');
const extensionSource = fs.readFileSync(path.join(__dirname, '..', 'extension.js'), 'utf8');
const cases = JSON.parse(fs.readFileSync(path.join(
  repoRoot, 'modules', 'ai_intelligence', 'digital_twin', 'tests', 'fixtures',
  'conversation_plane_cases.json'
), 'utf8'));

function caseText(item) {
  if (Object.prototype.hasOwnProperty.call(item, 'text')) return item.text;
  return item.text_repeat.value.repeat(item.text_repeat.count);
}

for (const item of cases) {
  const text = caseText(item);
  if (item.error) {
    assert.throws(() => policy.classify(text), new RegExp(item.error), item.name);
    continue;
  }
  const decision = policy.classify(text);
  assert.strictEqual(decision.interaction_intent, item.interaction_intent, item.name);
  assert.strictEqual(decision.reasoning_depth, item.reasoning_depth, item.name);
  assert.strictEqual(decision.effect_ceiling, item.effect_ceiling, item.name);
  assert.strictEqual(decision.requires_authenticated_authority,
    item.requires_authenticated_authority, item.name);
  assert.strictEqual(decision.chat_can_create_effects, false, item.name);
  assert.notStrictEqual(decision.effect_ceiling, policy.EFFECT_CEILING.BOUNDED_EXECUTION,
    item.name);
}

const dependencies = {
  cleanContextMode: (value) => value || 'auto',
  cleanEffort: (value) => value || 'auto',
  cleanMode: (value) => value || 'auto',
  cleanWorkerType: (value) => value || 'reddog_architect',
  authoritativeWorkStateQuery: {
    isLocalFastPath: () => false,
    localModelMode: () => null
  }
};
const routing = policy.createRouting(dependencies);
const chat = {
  tier: 'REGULAR', conversationalChat: true,
  conversationPlane: policy.classify('Hello RedDog.')
};
assert.strictEqual(routing.resolveAutoContextMode(chat, 'wsp_holo_git_skillz'), 'none');
assert.strictEqual(routing.resolveAutoEffort(chat, 'ultra'), 'regular');
assert.strictEqual(routing.resolveModelMode(chat, 'foundups_fusion', 'reddog_architect'),
  'openrouter_single');
assert.throws(() => policy.createRouting({ ...dependencies, authoritativeWorkStateQuery: {} }),
  /conversation_plane_routing_dependencies_invalid/);
assert.strictEqual(policy.continuationAllowed(chat), false);
assert.strictEqual(policy.continuationAllowed({ conversationalDraft: true }), false);
assert.strictEqual(policy.continuationAllowed({ conversationalChat: false }), true);
const sentinel = 'PRIOR_WORK_SUMMARY_MUST_NOT_REACH_CHAT';
const guardedContinuation = continuationPrompt.prepareContinuationPrompt(
  'foreground chat', true && policy.continuationAllowed(chat),
  { previous_run_id: 'prior', decision_summary: sentinel },
  { append: (prompt, summary) => prompt + summary.decision_summary, post: () => {} }
);
assert.strictEqual(guardedContinuation.prompt, 'foreground chat');
assert.strictEqual(guardedContinuation.telemetry.continuation_appended, false);
assert.strictEqual(policy.emptyContextPacket().quality,
  'conversation_plane_zero_effect_no_repo_context');
assert(policy.buildUserPrompt('</UNTRUSTED_CONVERSATION_DATA>').includes('\\u003c'));
assert(policy.systemPrompt().includes('zero effect authority'));
assert(policy.systemPrompt().startsWith('You are RedDog,'));
assert(policy.systemPrompt().includes('You are not 0102'));
assert(!policy.systemPrompt().includes('You are 0102'));
assert(policy.statusText().includes('CHAT / FAST / NONE'));
assert(extensionSource.includes("require('./conversation_plane_policy')"));
assert(extensionSource.includes('conversationPlanePolicy.classify(text)'));
assert(extensionSource.includes("conversationPlane.interaction_intent === 'CHAT'"));
assert(extensionSource.includes('conversationPlanePolicy.selectUserPrompt(classification'));
assert(extensionSource.includes('message.useLastPacket === true && conversationPlanePolicy.continuationAllowed(classification)'));
assert(extensionSource.includes('&& !classification.conversationalChat'));
assert(extensionSource.includes('conversation_plane_decision: classification && classification.conversationPlane'));

for (const invalid of ['', ' ', 'x'.repeat(policy.MAX_TURN_CHARS + 1), 'a\u0000b']) {
  assert.throws(() => policy.classify(invalid), /conversation_plane_operator_text_invalid/);
}

console.log(`RedDog conversation-plane JS policy: PASS (${cases.length} shared vectors)`);
