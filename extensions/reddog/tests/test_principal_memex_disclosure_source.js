'use strict';

const assert = require('assert');
const path = require('path');
const source = require('../principal_memex_disclosure_source');
const pkg = require(path.join('..', 'package.json'));

const SHA = 'sha256:' + 'a'.repeat(64);

function disclosure(overrides = {}) {
  return JSON.stringify(Object.assign({
    audience: 'foundups.reddog',
    conversation_id: SHA,
    conversation_record_digest: SHA,
    conversation_revision: 0,
    credential_id: SHA,
    decision_item_ids: [SHA],
    disclosure_id: SHA,
    expires_at: 1800000060,
    grounding_receipt_id: SHA,
    intent_id: SHA,
    issued_at: 1800000000,
    model_runtime_binding_digest: SHA,
    model_runtime_binding_receipt_id: 'reddog_model_runtime_binding:' + 'b'.repeat(64),
    nonce: SHA,
    principal_id: 'principal_012',
    principal_provider: 'principal-signature',
    purpose: 'resident_architect_context',
    repo_full_name: 'FOUNDUPS/Foundups-Agent',
    runtime_surface: 'reddog_backend_architect',
    schema_version: source.DISCLOSURE_SCHEMA,
    sensitivity: 'public',
    session_binding_digest: SHA,
    session_id: SHA,
    signature: 'ed25519-sig-v1:test',
    transport: 'editor'
  }, overrides));
}

function packet(overrides = {}) {
  return JSON.stringify(Object.assign({
    serialized_disclosure: disclosure(),
    conversation_id: SHA,
    expected_conversation_revision: 0
  }, overrides));
}

function storage(initial = '') {
  let value = initial;
  const calls = [];
  return {
    calls,
    async get(key) { calls.push(['get', key]); return value; },
    async store(key, next) { calls.push(['store', key]); value = next; },
    async delete(key) { calls.push(['delete', key]); value = ''; },
    current() { return value; }
  };
}

(async () => {
  const parsed = source.parseSupply(packet());
  assert(parsed);
  assert.strictEqual(parsed.conversation_id, SHA);
  assert.strictEqual(parsed.expected_conversation_revision, 0);
  assert.strictEqual(parsed.serialized_disclosure, disclosure());
  assert(pkg.activationEvents.includes('onCommand:reddog.setPrincipalMemexDisclosure'));

  assert.strictEqual(source.parseSupply(packet({ extra: true })), null);
  assert.strictEqual(source.parseSupply(packet({ conversation_id: 'invalid' })), null);
  assert.strictEqual(source.parseSupply(packet({ expected_conversation_revision: true })), null);
  assert.strictEqual(source.parseSupply(packet({ serialized_disclosure: disclosure({ extra: true }) })), null);
  assert.strictEqual(source.parseSupply(packet({ serialized_disclosure: disclosure({ schema_version: 'v1' }) })), null);
  assert.strictEqual(source.parseSupply(packet({ serialized_disclosure: disclosure({ principal_id: '\u2603' }) })), null);

  const bridged = source.bridgePayload(
    { red_dog_intent: { intent_id: SHA } }, 'credential', parsed
  );
  assert.deepStrictEqual(bridged.principal_memex_source_supply, parsed);
  assert.strictEqual(
    Object.prototype.hasOwnProperty.call(
      bridged.red_dog_intent, 'principal_memex_source_supply'
    ),
    false
  );

  const oneUse = storage(packet());
  const taken = await source.take(oneUse);
  assert(taken.supply);
  assert.strictEqual(oneUse.current(), '');
  assert.deepStrictEqual(oneUse.calls.map((call) => call[0]), ['get', 'delete']);
  assert.deepStrictEqual(await source.take(oneUse), { supply: null, reason: '' });

  const preserved = storage(packet());
  const preservedResult = await source.invokeStored(
    preserved,
    async (supply) => ({
      accepted: true,
      supplied: Boolean(supply),
      principal_memex_source_consumed: false
    })
  );
  assert.strictEqual(preservedResult.value.supplied, true);
  assert.strictEqual(preserved.current(), packet());
  assert.deepStrictEqual(preserved.calls.map((call) => call[0]), ['get', 'delete', 'store']);

  const consumed = storage(packet());
  const consumedResult = await source.invokeStored(
    consumed,
    async () => ({ accepted: true, principal_memex_source_consumed: true })
  );
  assert.strictEqual(consumedResult.value.principal_memex_source_consumed, true);
  assert.strictEqual(consumed.current(), '');

  const concurrent = storage(packet());
  let releaseFirst;
  let markStarted;
  const firstStarted = new Promise((resolve) => { markStarted = resolve; });
  const first = source.invokeStored(concurrent, async (supply) => {
    assert(supply);
    markStarted();
    await new Promise((resolve) => { releaseFirst = resolve; });
    return { principal_memex_source_consumed: true };
  });
  await firstStarted;
  const second = source.invokeStored(
    concurrent,
    async (supply) => ({ supplied: Boolean(supply) })
  );
  releaseFirst();
  const [firstResult, secondResult] = await Promise.all([first, second]);
  assert.strictEqual(firstResult.value.principal_memex_source_consumed, true);
  assert.strictEqual(secondResult.value.supplied, false);
  assert.strictEqual(concurrent.current(), '');
  assert.deepStrictEqual(
    concurrent.calls.map((call) => call[0]), ['get', 'delete', 'get']
  );

  const failed = storage(packet());
  await assert.rejects(
    source.invokeStored(failed, async () => { throw new Error('bridge failed'); }),
    /bridge failed/
  );
  assert.strictEqual(failed.current(), '');

  const indeterminate = storage(packet());
  const indeterminateResult = await source.invokeStored(
    indeterminate, async () => ({ accepted: false })
  );
  assert.strictEqual(indeterminateResult.value.accepted, false);
  assert.strictEqual(indeterminate.current(), '');

  const preflightRejected = storage(packet());
  let preflightInvocations = 0;
  const preflightResult = await source.runConfigured({
    secretStorage: preflightRejected,
    workFocus: 'original work focus',
    options: { groundingPreflight: {}, holoScorecard: {} },
    credential: 'credential',
    claims: { principalId: 'principal_012', foundupScope: ['foundup-a'] },
    buildPayload: () => ({
      ok: false,
      rejection_reasons: ['exact_preflight_rejection', 'second_rejection'],
      payload: null
    }),
    invoke: async () => { preflightInvocations += 1; },
    skip: (reason, reasons) => ({ reason, reasons })
  });
  assert.deepStrictEqual(preflightResult, {
    reason: 'exact_preflight_rejection',
    reasons: ['exact_preflight_rejection', 'second_rejection']
  });
  assert.strictEqual(preflightInvocations, 0);
  assert.deepStrictEqual(preflightRejected.calls, []);
  assert.strictEqual(preflightRejected.current(), packet());

  const invalid = storage('{"malformed":true}');
  assert.deepStrictEqual(await source.take(invalid), {
    supply: null,
    reason: 'principal_memex_source_supply_invalid'
  });
  assert.strictEqual(invalid.current(), '');

  const prompted = storage();
  const vscode = {
    window: {
      showInputBox: async (options) => {
        assert.strictEqual(options.password, true);
        assert.strictEqual(options.validateInput(packet()), undefined);
        return packet();
      }
    }
  };
  assert.deepStrictEqual(await source.storeFromPrompt(vscode, prompted), {
    stored: true,
    reason: ''
  });
  assert.strictEqual(prompted.current(), packet());
  assert.deepStrictEqual(await source.clear(prompted), { cleared: true, reason: '' });
  assert.strictEqual(prompted.current(), '');

  console.log('principal_memex_disclosure_source: PASS');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
