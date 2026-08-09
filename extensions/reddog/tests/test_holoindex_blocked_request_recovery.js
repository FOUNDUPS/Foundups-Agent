'use strict';

const assert = require('assert');
const cp = require('child_process');
const fs = require('fs');
const path = require('path');
const { Writable } = require('stream');
const recovery = require('../holoindex_blocked_request_recovery');

class SecretStorage {
  constructor() { this.values = new Map(); }
  async get(key) { return this.values.get(key); }
  async store(key, value) { this.values.set(key, value); }
  async delete(key) { this.values.delete(key); }
}

const HEAD = 'a'.repeat(40);
const DIGEST = (char) => 'sha256:' + char.repeat(64);
const message = {
  command: 'ask', text: 'audit HoloIndex \ud83d\udd0e', contextMode: 'wsp_holo',
  diagnosticEvidence: 'ERROR: semantic backend unavailable',
  workerType: 'architect', effort: 'high', mode: 'foundups_fusion', useLastPacket: false
};
const incident = {
  accepted: true, status: 'QUEUED',
  schema_version: 'reddog_holoindex_incident_repair.v2',
  incident_kind: 'HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH',
  incident_id: DIGEST('1'),
  task_id: 'holoindex_postmerge_refresh:' + HEAD, target_repo_head_sha: HEAD,
  request_event_id: 'holoindex_postmerge_requested:' + HEAD,
  workspace_repo_head_sha: HEAD, observed_authority_head_sha: 'f'.repeat(40),
  authority_root_digest: DIGEST('3'), generation_id: '', freshness_receipt_digest: '',
  maintenance_enqueued: true, owner_requery_performed: false,
  coding_candidate_required: false, rejection_reasons: [], receipt_id: ''
};
const incidentUnsigned = { ...incident };
delete incidentUnsigned.receipt_id;
incident.receipt_id = recovery.digest(incidentUnsigned);
const meta = {
  incident_repair_accepted: true, incident_repair_enqueued: true,
  incident_repair_status: 'QUEUED', incident_repair_id: incident.incident_id,
  incident_repair_receipt_id: incident.receipt_id,
  incident_repair_receipt: incident
};

function fakeExecFile(result, calls) {
  return (_file, _args, _options, callback) => {
    let raw = '';
    const child = {};
    child.stdin = new Writable({ write(chunk, _encoding, done) { raw += chunk; done(); } });
    child.stdin.on('finish', () => setImmediate(() => {
      const payload = JSON.parse(raw);
      calls.push(payload);
      callback(null, JSON.stringify(typeof result === 'function' ? result(payload) : result));
    }));
    return child;
  };
}

function readyResult(packet) {
  const stage = recovery.stageBinding(packet);
  return {
    ok: true, status: 'READY', reason: '', incident_id: incident.incident_id,
    incident_task_id: incident.task_id, incident_repair_receipt_id: incident.receipt_id,
    target_repo_head_sha: HEAD, authority_root_digest: incident.authority_root_digest,
    generation_id: DIGEST('4'), freshness_receipt_digest: DIGEST('5'),
    recovery_id: packet.recovery_id, request_digest: packet.request_digest,
    query_digest: packet.query_digest,
    stage_event_id: 'reddog_holoindex_blocked_retry_staged:' + stage.payload_digest.slice(7),
    stage_payload_digest: stage.payload_digest,
    claim_event_id: 'reddog_holoindex_blocked_retry_claimed:' + packet.recovery_id.slice(7),
    claim_payload_digest: DIGEST('6'),
    no_holoindex_reindex_performed: true, authority_effect: 'none'
  };
}

function stageResult(packet) {
  const stage = recovery.stageBinding(packet);
  return {
    ok: true, status: 'STAGED', reason: '',
    stage_event_id: 'reddog_holoindex_blocked_retry_staged:' + stage.payload_digest.slice(7),
    stage_payload_digest: stage.payload_digest,
    incident_id: packet.incident_receipt.incident_id,
    incident_repair_receipt_id: packet.incident_receipt.receipt_id,
    recovery_id: packet.recovery_id, task_id: packet.incident_receipt.task_id,
    request_event_id: packet.incident_receipt.request_event_id,
    target_repo_head_sha: packet.incident_receipt.target_repo_head_sha,
    authority_root_digest: packet.incident_receipt.authority_root_digest,
    authority_effect: 'none'
  };
}

function normalBridgeResult(envelope) {
  return envelope.operation === 'stage'
    ? stageResult(envelope.packet) : readyResult(envelope.packet);
}

async function stageWith(storage) {
  return recovery.stage({
    root: path.resolve(__dirname, '..', '..', '..'), interpreterPath: 'python',
    env: {}, secretStorage: storage
  }, message, meta);
}

async function main() {
  assert.strictEqual(recovery.eligible(meta, message), true);
  assert.strictEqual(recovery.eligible(meta, { ...message, useLastPacket: true }), false);
  assert.strictEqual(await recovery.hasPending(new SecretStorage()), false);
  assert.strictEqual(await recovery.hasPending({ get: async () => { throw new Error('fail'); } }), true);
  assert.strictEqual(
    recovery.digest({ query: 'audit HoloIndex \ud83d\udd0e' }),
    'sha256:467681a774f1051c4cb7a0ba61360de284220a0e928a0d514233498fa1891e44'
  );
  const original = cp.execFile;

  const stageBlocked = new SecretStorage();
  const stageBlockedCalls = [];
  cp.execFile = fakeExecFile(normalBridgeResult, stageBlockedCalls);
  try {
    const stageOptions = {
      root: path.resolve('root-a'), interpreterPath: 'python', env: {},
      secretStorage: stageBlocked
    };
    let stageCheckedRoot = '';
    const result = await recovery.stageAfterCompatibility(
      stageOptions, message, meta,
      async (root) => { stageCheckedRoot = root; return false; }
    );
    assert.strictEqual(result.status, 'BLOCKED');
    assert.strictEqual(stageCheckedRoot, stageOptions.root);
    assert.strictEqual(stageBlockedCalls.length, 0);
    assert.strictEqual(await stageBlocked.get(recovery.SECRET_KEY), undefined);
  } finally { cp.execFile = original; }

  const secretStorage = new SecretStorage();
  const calls = [];
  cp.execFile = fakeExecFile(normalBridgeResult, calls);
  try {
    const staged = await stageWith(secretStorage);
    assert.strictEqual(staged.ok, true);
    assert.strictEqual(staged.authority_effect, 'none');
    assert.strictEqual(staged.record, undefined);
    assert.strictEqual(JSON.stringify(staged).includes(message.text), false);
    assert.strictEqual(JSON.stringify(staged).includes('"request"'), false);
    assert.strictEqual(JSON.stringify(staged).includes('"query"'), false);
    assert.strictEqual(calls.length, 1);
    assert.strictEqual(calls[0].operation, 'stage');
    const claimed = await recovery.claim({
      root: path.resolve(__dirname, '..', '..', '..'), interpreterPath: 'python',
      env: {}, secretStorage
    });
    assert.strictEqual(claimed.ok, true);
    assert.deepStrictEqual(claimed.request, recovery.exactMessage(message));
    assert.strictEqual(calls[1].operation, 'claim');
    assert.strictEqual(calls[1].packet.query, message.text);
    assert.strictEqual(
      calls[1].packet.request.diagnosticEvidence,
      message.diagnosticEvidence
    );
    assert.deepStrictEqual(calls[1].packet.incident_receipt, incident);
    assert.deepStrictEqual(calls[1].packet.request, recovery.exactMessage(message));
    assert.strictEqual(await secretStorage.get(recovery.SECRET_KEY), undefined);
    assert.strictEqual((await recovery.finish({}, claimed.recovery_id, { ok: true }, true)).status, 'COMPLETED');
  } finally { cp.execFile = original; }

  const concurrent = new SecretStorage();
  let admissions = 0;
  cp.execFile = fakeExecFile((envelope) => {
    if (envelope.operation === 'stage') return stageResult(envelope.packet);
    return admissions++ === 0 ? readyResult(envelope.packet)
      : { ok: false, status: 'REJECTED', reason: 'recovery_already_claimed' };
  }, []);
  try {
    await stageWith(concurrent);
    const options = { root: '.', interpreterPath: 'python', env: {}, secretStorage: concurrent };
    const claims = await Promise.all([recovery.claim(options), recovery.claim(options)]);
    assert.strictEqual(claims.filter((item) => item.ok && item.request).length, 1);
  } finally { cp.execFile = original; }

  const incompatible = new SecretStorage();
  const incompatibleCalls = [];
  cp.execFile = fakeExecFile(normalBridgeResult, incompatibleCalls);
  try {
    assert.strictEqual((await stageWith(incompatible)).ok, true);
    incompatibleCalls.length = 0;
    const incompatibleOptions = { root: path.resolve('root-a'), secretStorage: incompatible };
    let checkedRoot = '';
    const blocked = await recovery.claimAfterCompatibility(
      incompatibleOptions, async (root) => { checkedRoot = root; return false; }
    );
    assert.strictEqual(blocked.ok, false);
    assert.strictEqual(blocked.status, 'BLOCKED');
    assert.strictEqual(blocked.reason, 'backend_compatibility_preflight_blocked');
    assert.strictEqual(checkedRoot, incompatibleOptions.root);
    assert.strictEqual(incompatibleCalls.length, 0);
  } finally { cp.execFile = original; }

  const waiting = new SecretStorage();
  cp.execFile = fakeExecFile((envelope) => envelope.operation === 'stage'
    ? stageResult(envelope.packet)
    : { ok: false, status: 'WAITING', reason: 'repair_pending' }, []);
  try {
    await stageWith(waiting);
    assert.strictEqual((await recovery.claim({
      root: '.', interpreterPath: 'python', env: {}, secretStorage: waiting
    })).status, 'WAITING');
    assert.notStrictEqual(await waiting.get(recovery.SECRET_KEY), undefined);
  } finally { cp.execFile = original; }

  const rejected = new SecretStorage();
  cp.execFile = fakeExecFile((envelope) => envelope.operation === 'stage'
    ? stageResult(envelope.packet)
    : { ok: false, status: 'REJECTED', reason: 'bad_receipt' }, []);
  try {
    await stageWith(rejected);
    await recovery.claim({ root: '.', interpreterPath: 'python', env: {}, secretStorage: rejected });
    assert.strictEqual(await rejected.get(recovery.SECRET_KEY), undefined);
  } finally { cp.execFile = original; }

  const tampered = new SecretStorage();
  cp.execFile = fakeExecFile((envelope) => stageResult(envelope.packet), []);
  try { await stageWith(tampered); } finally { cp.execFile = original; }
  const packet = JSON.parse(await tampered.get(recovery.SECRET_KEY));
  packet.request.mode = 'exec';
  await tampered.store(recovery.SECRET_KEY, JSON.stringify(packet));
  assert.strictEqual((await recovery.loadPacket(tampered)).ok, false);
  assert.strictEqual((await recovery.claim({ secretStorage: tampered })).ok, false);
  assert.strictEqual(await tampered.get(recovery.SECRET_KEY), undefined);

  const evidenceTampered = new SecretStorage();
  cp.execFile = fakeExecFile((envelope) => stageResult(envelope.packet), []);
  try { await stageWith(evidenceTampered); } finally { cp.execFile = original; }
  const evidencePacket = JSON.parse(await evidenceTampered.get(recovery.SECRET_KEY));
  evidencePacket.request.diagnosticEvidence = 'attacker replacement';
  await evidenceTampered.store(recovery.SECRET_KEY, JSON.stringify(evidencePacket));
  assert.strictEqual((await recovery.loadPacket(evidenceTampered)).ok, false);
  assert.strictEqual((await recovery.claim({ secretStorage: evidenceTampered })).ok, false);
  assert.strictEqual(await evidenceTampered.get(recovery.SECRET_KEY), undefined);

  const legacy = new SecretStorage();
  cp.execFile = fakeExecFile((envelope) => stageResult(envelope.packet), []);
  try { await stageWith(legacy); } finally { cp.execFile = original; }
  const legacyPacket = JSON.parse(await legacy.get(recovery.SECRET_KEY));
  legacyPacket.schema_version = 'reddog_holoindex_blocked_request_recovery.v1';
  legacyPacket.request_digest = recovery.digest({
    schema_version: legacyPacket.schema_version,
    request: legacyPacket.request
  });
  legacyPacket.recovery_id = recovery.digest({
    request_digest: legacyPacket.request_digest,
    incident_receipt_id: legacyPacket.incident_receipt.receipt_id
  });
  await legacy.store(recovery.SECRET_KEY, JSON.stringify(legacyPacket));
  assert.strictEqual((await recovery.loadPacket(legacy)).ok, false);
  assert.strictEqual((await recovery.claim({ secretStorage: legacy })).ok, false);
  assert.strictEqual(await legacy.get(recovery.SECRET_KEY), undefined);

  const replaced = new SecretStorage();
  await replaced.store(recovery.SECRET_KEY, '{invalid');
  cp.execFile = fakeExecFile((envelope) => stageResult(envelope.packet), []);
  try { assert.strictEqual((await stageWith(replaced)).ok, true); }
  finally { cp.execFile = original; }
  assert.strictEqual((await recovery.loadPacket(replaced)).ok, true);

  const expired = new SecretStorage();
  cp.execFile = fakeExecFile((envelope) => stageResult(envelope.packet), []);
  try { await stageWith(expired); } finally { cp.execFile = original; }
  const expiresAt = JSON.parse(await expired.get(recovery.SECRET_KEY)).expires_at_epoch_ms;
  const realNow = Date.now;
  Date.now = () => expiresAt;
  try {
    assert.strictEqual((await recovery.claim({ secretStorage: expired })).ok, false);
    assert.strictEqual(await expired.get(recovery.SECRET_KEY), undefined);
  } finally { Date.now = realNow; }

  const extension = fs.readFileSync(path.join(__dirname, '..', 'extension.js'), 'utf8');
  const moduleSource = fs.readFileSync(path.join(__dirname, '..', 'holoindex_blocked_request_recovery.js'), 'utf8');
  assert(extension.includes('holoBlockedRequestRecovery.stageAfterCompatibility('));
  assert(extension.includes('currentBackendCompatibilityAtRoot(root)'));
  assert(extension.includes('holoBlockedRequestRecovery.claimAfterCompatibility('));
  assert(extension.includes('blockedRecoveryOutcomeVerified(result, classification, validation)'));
  assert(extension.includes('const { actionPlanningAllowed } = sessionPolicy;'));
  assert(extension.includes('residentSessionStagePolicy('));
  assert(extension.includes('progressiveExecutionStage.allowsActionPlanning(progressiveStage.configured)'));
  assert(extension.includes('&& !recoveryContext'));
  assert(extension.includes("if (actionStageEnabled && !recoveryContext && await startOperationsAdapter.handleMessage("));
  assert(extension.includes('const residentArchitectSessionResult = recoveryContext ? null'));
  assert(extension.includes('const bridgeState = bridgeStateForRequest(state, recoveryContext)'));
  assert(extension.includes('onBridgeProgress, bridgeState, promptConstruction'));
  assert(extension.includes("claim.reason !== 'recovery_secret_missing'"));
  const attemptSource = extension.slice(
    extension.indexOf('async function attemptBlockedRequestRecovery'),
    extension.indexOf('function createFusionMessageReceiver')
  );
  assert.strictEqual((attemptSource.match(/state\.disposed/g) || []).length, 1);
  assert(attemptSource.indexOf('state.disposed') < attemptSource.indexOf('holoBlockedRequestRecovery.claimAfterCompatibility('));
  assert(attemptSource.indexOf('blockIncompatibleBackend(') < attemptSource.indexOf("status === 'REJECTED'"));
  assert(attemptSource.includes('blockIncompatibleBackend(context, state, webview, root)'));
  assert(extension.includes('scheduleBlockedRecoveryPoll(state, attempt, 1000)'));
  assert(extension.includes('scheduleBlockedRecoveryPoll(state, attempt, 15000)'));
  assert(extension.includes('state.holoRecoveryTimer = null'));
  assert(!moduleSource.includes('execFileSync'));
  assert(!moduleSource.includes('AgentDbHoloBlockedRequestRecoveryStore'));
  const handler = extension.slice(extension.indexOf('function wireFusionWebview'));
  assert(handler.indexOf('stageBlockedRequestRecovery(') < handler.indexOf('runBlockedGroundingResponse('));
}

main().catch((err) => { console.error(err); process.exit(1); });
