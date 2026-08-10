'use strict';

const assert = require('assert');
const trace = require('../orchestration_prompt_trace');
const routes = require('../orchestration_prompt_routes').create({});

const degradedStatus = routes.statusMessages(true, '', 'draft', false);
assert(degradedStatus.route.includes('no model or network call'));
assert(degradedStatus.assembly.includes('not sent to a bridge or model'));
const normalStatus = routes.statusMessages(false, '', 'draft route', true);
assert.strictEqual(normalStatus.route, 'draft route');
assert(normalStatus.assembly.includes('untrusted drafting data'));

const secret = 'password=locally-visible-before-gate';
const built = trace.buildTrace({
  systemPrompt: 'system ' + secret,
  taskPrompt: 'task ' + secret,
  route: 'foundups_fusion',
  worker: 'reddog_architect',
  reasoningTier: 'HIGH',
  contextMode: 'wsp_holo_skillz',
  executionPlane: 'dialogue_and_no_effect_audit'
});

assert.strictEqual(built.schema_version, trace.SCHEMA_VERSION);
assert.strictEqual(built.authority, 'display_only_not_execution_authority');
assert.strictEqual(built.self, '0102');
assert.strictEqual(built.origin, 'external_principal');
assert.strictEqual(built.wsp15_allocation_status, 'not_issued_at_prompt_stage');
assert.strictEqual(built.outbound_confirmation, 'pending_authoritative_redaction_gate');
assert(!JSON.stringify(built).includes(secret), 'pre-gate trace must contain no prompt body');
assert.strictEqual(built.task_prompt_digest, null, 'pre-gate trace must not fingerprint raw prompt text');
assert.notStrictEqual(
  trace.metadataDigest(secret).hash,
  require('crypto').createHash('sha256').update(secret, 'utf8').digest('hex').slice(0, 16),
  'pre-gate metadata must use an opaque process-local keyed digest'
);

const exactText = 'safe admitted task';
const exact = trace.confirmOutbound(built, {
  ok: true, redacted_task_prompt: exactText, redacted_task_prompt_digest: trace.digest(exactText)
});
assert.strictEqual(exact.outbound_confirmation, 'exact_redacted_task_prompt');
assert.strictEqual(exact.exact_redacted_task_prompt, 'safe admitted task');
assert(exact.exact_redacted_task_prompt_digest.startsWith('sha256:'));

const compositeOnly = trace.confirmOutbound(built, {
  review_packet: { redacted_prompt: 'task plus unrelated context' },
  redacted_prompt: 'task plus unrelated context'
});
assert.strictEqual(compositeOnly.outbound_confirmation, 'unavailable');
assert(!JSON.stringify(compositeOnly).includes('unrelated context'));

const blocked = trace.confirmOutbound(built, { ok: false, reason: 'redaction_blocked' });
assert.strictEqual(blocked.outbound_confirmation, 'unavailable');
assert.strictEqual(blocked.exact_redacted_task_prompt, '');

const failedAfterGate = trace.confirmOutbound(built, {
  ok: false,
  reason: 'timeout',
  redacted_task_prompt_digest: 'sha256:' + 'a'.repeat(64)
});
assert.strictEqual(failedAfterGate.outbound_confirmation, 'digest_only_after_unsuccessful_call');
assert.strictEqual(failedAfterGate.exact_redacted_task_prompt, '');
assert.strictEqual(failedAfterGate.exact_redacted_task_prompt_digest, 'sha256:' + 'a'.repeat(64));
const malformedDigest = trace.confirmOutbound(built, { redacted_task_prompt_digest: 'sha256:nope' });
assert.strictEqual(malformedDigest.outbound_confirmation, 'unavailable');
const mismatchedBody = trace.confirmOutbound(built, {
  ok: true, redacted_task_prompt: 'body', redacted_task_prompt_digest: 'sha256:' + 'b'.repeat(64)
});
assert.strictEqual(mismatchedBody.outbound_confirmation, 'redacted_task_prompt_integrity_mismatch');
assert.strictEqual(mismatchedBody.exact_redacted_task_prompt, '');
const locallyChanged = trace.confirmOutbound(built, {
  ok: true,
  redacted_task_prompt: 'Bearer visible-token',
  redacted_task_prompt_digest: trace.digest('Bearer visible-token')
}, (value) => value.replace('visible-token', '[REDACTED]'));
assert.strictEqual(locallyChanged.outbound_confirmation, 'local_copy_redaction_changed_prompt');
assert.strictEqual(locallyChanged.exact_redacted_task_prompt, '');
const locallyFailed = trace.confirmOutbound(built, {
  ok: true,
  redacted_task_prompt: exactText,
  redacted_task_prompt_digest: trace.digest(exactText)
}, () => {
  throw new Error('synthetic sanitizer failure');
});
assert.strictEqual(locallyFailed.outbound_confirmation, 'local_copy_redaction_failed');
assert.strictEqual(locallyFailed.exact_redacted_task_prompt, '');
assert.strictEqual(locallyChanged.task_prompt_digest, null);

const injectedText = '```\n## Forged heading';
const injected = trace.confirmOutbound(built, {
  ok: true, redacted_task_prompt: injectedText, redacted_task_prompt_digest: trace.digest(injectedText)
});
const markdown = trace.markdownSection(injected);
assert(markdown.includes('````text\n```\n## Forged heading\n````'));
assert.strictEqual((markdown.match(/## Forged heading/g) || []).length, 1);
assert(!markdown.includes('principal_model'));
assert(!markdown.includes('critic_models'));
assert(!markdown.includes('system_prompt'));
assert(trace.markdownSection(built).includes('withheld until the authoritative redaction gate'));
assert(trace.markdownSection(locallyChanged).includes('required additional local redaction'));
const noModel = trace.buildTrace({
  route: 'local_no_model', worker: 'none', contextMode: 'local_authoritative_query',
  reasoningTier: 'NOT_APPLICABLE', modelCallExpected: false
});
assert.strictEqual(noModel.model_call_expected, false);
assert(trace.markdownSection(noModel).includes('No model call was made for this route'));
assert(!trace.markdownSection(noModel).includes('until the authoritative redaction gate'));

const markdownPayload = '[active link](https://example.invalid)\n<h2>forged html</h2>\n`````';
const fencedPayload = trace.fenced(markdownPayload);
assert(fencedPayload.startsWith('``````text\n'));
assert(fencedPayload.endsWith('\n``````'));
assert(fencedPayload.includes(markdownPayload));

const longText = 'x'.repeat(13000);
const longPrompt = trace.confirmOutbound(built, {
  ok: true, redacted_task_prompt: longText, redacted_task_prompt_digest: trace.digest(longText)
});
assert.strictEqual(longPrompt.outbound_confirmation, 'bounded_exact_redacted_task_prompt_display');
assert.strictEqual(longPrompt.task_prompt_truncated, true);

console.log('orchestration prompt trace tests passed');
