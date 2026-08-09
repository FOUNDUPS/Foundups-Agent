'use strict';

const assert = require('assert');
const EventEmitter = require('events');
const fs = require('fs');
const path = require('path');
const query = require('../authoritative_work_state_query');

const extensionSource = fs.readFileSync(
  path.join(__dirname, '..', 'extension.js'),
  'utf8'
);

function fakeChild(output, exitCode) {
  const child = new EventEmitter();
  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  child.stdin = {
    end: () => {
      setImmediate(() => {
        child.stdout.emit('data', JSON.stringify(output) + '\n');
        child.emit('close', exitCode);
      });
    }
  };
  child.kill = () => {};
  return child;
}

async function main() {
  assert.strictEqual(
    query.localModelMode('authoritative_work_state'),
    'local_authoritative_work_state'
  );
  assert.strictEqual(query.localModelMode('unknown'), null);
  for (const prompt of [
    'What do we need to work on?',
    'What should RedDog work on next?',
    'Show the current authoritative work status.',
    'Which is the current selected slice?'
  ]) {
    assert.strictEqual(query.isAuthoritativeWorkStateQuestion(prompt), true, prompt);
  }
  for (const prompt of [
    'Audit how current work-state selection is implemented.',
    'Implement the next slice.',
    'Explain WRE queue architecture.',
    '```text\nWhat do we need to work on?\n```'
  ]) {
    assert.strictEqual(query.isAuthoritativeWorkStateQuestion(prompt), false, prompt);
  }

  const receipt = {
    schema_version: 'reddog_authoritative_work_state_query.v1',
    accepted: true,
    status: 'AUTHORITATIVE_WORK_STATE_READY',
    selected_slice: 'REDDOG_NEXT_SLICE_PHASE1',
    next_required_gate: 'SIGNED_AUTHORITY_REQUIRED',
    rejection_reasons: [],
    no_model_call_performed: true,
    no_holoindex_query_performed: true,
    no_holoindex_reindex_performed: true,
    no_queue_mutation_performed: true,
    no_claim_mutation_performed: true,
    no_worker_spawn_performed: true,
    no_shell_command_executed: true,
    no_repo_mutation_performed: true,
    no_execution_performed: true
  };
  receipt.receipt_id = query.canonicalDigest(receipt);
  const result = await query.runAuthoritativeWorkStateQuery({
    interpreter: 'python',
    script: 'query.py',
    repoRoot: 'O:/repo',
    env: {},
    spawn: () => fakeChild(receipt, 0)
  });
  assert.strictEqual(result.accepted, true);
  const tampered = { ...receipt, selected_slice: 'ATTACKER_SLICE' };
  assert.strictEqual(query.parseBridgeOutput(0, JSON.stringify(tampered)).accepted, false);
  assert.strictEqual(
    query.buildLocalResult(tampered).review_packet.authoritative_work_state_ready,
    false
  );

  const local = query.buildLocalResult(result);
  assert.strictEqual(local.ok, true);
  assert.strictEqual(local.made_network_call, false);
  assert.strictEqual(local.review_packet.authoritative_work_state_ready, true);
  assert(local.content.includes('REDDOG_NEXT_SLICE_PHASE1'));

  const rejected = await query.runAuthoritativeWorkStateQuery({
    interpreter: 'python',
    script: 'query.py',
    repoRoot: 'O:/repo',
    env: {},
    spawn: () => {
      throw new Error('spawn failed');
    }
  });
  assert.strictEqual(rejected.accepted, false);
  assert(rejected.rejection_reasons.includes('authoritative_work_state_bridge_spawn_failed'));
  const inputFailed = await query.runAuthoritativeWorkStateQuery({
    interpreter: 'python',
    script: 'query.py',
    repoRoot: 'O:/repo',
    env: {},
    spawn: () => {
      const child = fakeChild(receipt, 0);
      child.stdin.end = () => {
        throw new Error('stdin failed');
      };
      return child;
    }
  });
  assert(inputFailed.rejection_reasons.includes(
    'authoritative_work_state_bridge_input_failed'
  ));

  assert(extensionSource.includes("localFastPath = 'authoritative_work_state'"));
  assert(extensionSource.includes('runAuthoritativeWorkStateQueryBridge'));
  const wireStart = extensionSource.indexOf('function wireFusionWebview');
  const wireEnd = extensionSource.indexOf('function killBridgeChild', wireStart);
  const wireSource = extensionSource.slice(wireStart, wireEnd);
  assert(wireSource.includes('const contextPacket = auditDegraded || localFastPath ?'));
  assert(wireSource.includes('const compatibility = await currentBackendCompatibility()'));
  assert(wireSource.indexOf('if (localFastPath)')
    < wireSource.indexOf('result = await callFusion'));
  assert(wireSource.indexOf('resolveLocalResult')
    < wireSource.indexOf('result = await callFusion'));
  console.log('authoritative work-state query tests passed');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
