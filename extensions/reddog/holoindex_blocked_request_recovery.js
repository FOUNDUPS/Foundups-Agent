'use strict';

const cp = require('child_process');
const crypto = require('crypto');
const path = require('path');

const SCHEMA_VERSION = 'reddog_holoindex_blocked_request_recovery.v1';
const INCIDENT_SCHEMA = 'reddog_holoindex_incident_repair.v2';
const SECRET_KEY = 'reddog.holoBlockedRequestRecovery.v1';
const STAGE_EVENT_PREFIX = 'reddog_holoindex_blocked_retry_staged:';
const CLAIM_EVENT_PREFIX = 'reddog_holoindex_blocked_retry_claimed:';
const DEFERRED = new Set(['ASSIGNED', 'EXECUTING', 'PENDING', 'QUEUED', 'REQUEUED', 'RETRY_WAIT', 'WAITING_COMPLETION_RECEIPT']);
const INCIDENT_KINDS = new Set(['HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH', 'HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP', 'QUERY_OWNER_POISONED', 'SEMANTIC_BACKEND_UNAVAILABLE']);
const SHA = /^sha256:[0-9a-f]{64}$/;
const GIT_SHA = /^[0-9a-f]{40}$/;
const REQUEST_EVENT_PREFIX = 'holoindex_postmerge_requested:';
const MAX_SECRET_BYTES = 32 * 1024;
const MAX_BRIDGE_BYTES = 256 * 1024;
const MAX_AGE_MS = 30 * 60 * 1000;
const PACKET_KEYS = ['created_at_epoch_ms', 'expires_at_epoch_ms', 'incident_receipt', 'query', 'query_digest', 'recovery_id', 'request', 'request_digest', 'schema_version'];
let secretOperation = Promise.resolve();

function serializeSecretOperation(action) {
  const next = secretOperation.then(action, action);
  secretOperation = next.catch(() => undefined);
  return next;
}
function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (!value || typeof value !== 'object') return value;
  const result = {};
  for (const key of Object.keys(value).sort()) result[key] = stable(value[key]);
  return result;
}

function digest(value) {
  const raw = JSON.stringify(stable(value)).replace(/[\u007f-\uffff]/g, (char) => (
    '\\u' + char.charCodeAt(0).toString(16).padStart(4, '0')
  ));
  return 'sha256:' + crypto.createHash('sha256').update(raw, 'ascii').digest('hex');
}

function exactMessage(message) {
  return {
    command: 'ask', text: String(message.text || ''),
    contextMode: String(message.contextMode || ''), workerType: String(message.workerType || ''),
    effort: String(message.effort || ''), mode: String(message.mode || ''),
    useLastPacket: false
  };
}

function incidentReceipt(meta) {
  const receipt = meta && meta.incident_repair_receipt;
  return receipt && typeof receipt === 'object' && !Array.isArray(receipt) ? stable(receipt) : null;
}

function deferredIncidentValid(receipt) {
  if (!receipt || receipt.schema_version !== INCIDENT_SCHEMA) return false;
  const unsigned = { ...receipt };
  delete unsigned.receipt_id;
  const mismatch = receipt.incident_kind === 'HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH';
  return receipt.accepted === true && receipt.maintenance_enqueued === true
    && DEFERRED.has(receipt.status) && SHA.test(String(receipt.incident_id || ''))
    && receipt.receipt_id === digest(unsigned) && SHA.test(receipt.authority_root_digest || '')
    && GIT_SHA.test(receipt.target_repo_head_sha || '')
    && receipt.workspace_repo_head_sha === receipt.target_repo_head_sha
    && INCIDENT_KINDS.has(receipt.incident_kind)
    && GIT_SHA.test(receipt.observed_authority_head_sha || '')
    && (mismatch
      ? receipt.observed_authority_head_sha !== receipt.target_repo_head_sha
      : receipt.observed_authority_head_sha === receipt.target_repo_head_sha)
    && receipt.task_id === 'holoindex_postmerge_refresh:' + receipt.target_repo_head_sha
    && receipt.request_event_id === REQUEST_EVENT_PREFIX + receipt.target_repo_head_sha;
}

function eligible(meta, message) {
  const value = meta && typeof meta === 'object' ? meta : {};
  const receipt = incidentReceipt(value);
  return message && message.useLastPacket !== true && deferredIncidentValid(receipt)
    && value.incident_repair_receipt_id === receipt.receipt_id;
}

function failure(reason, status) {
  return { ok: false, status: status || 'REJECTED', reason: String(reason), record: null };
}

function parseBridgeResult(stdout) {
  try {
    const result = JSON.parse(stdout);
    return result && typeof result === 'object'
      ? result : failure('recovery_bridge_result_invalid');
  } catch (err) { return failure('recovery_bridge_result_invalid'); }
}

function bridge(options, operation, packet) {
  const script = path.join(options.root, 'scripts', 'reddog_holoindex_blocked_request_recovery_once.py');
  return new Promise((resolve) => {
    let child;
    try {
      child = cp.execFile(options.interpreterPath, ['-B', script], {
        cwd: options.root, env: options.env, encoding: 'utf8', timeout: 90000,
        maxBuffer: MAX_BRIDGE_BYTES, windowsHide: true
      }, (err, stdout) => {
        if (err) return resolve(failure(
          err.code === 'ETIMEDOUT' ? 'recovery_bridge_timeout' : 'recovery_bridge_failed'
        ));
        resolve(parseBridgeResult(stdout));
      });
    } catch (err) { resolve(failure('recovery_bridge_failed')); return; }
    child.stdin.on('error', () => resolve(failure('recovery_bridge_failed')));
    child.stdin.end(JSON.stringify({ operation, packet }));
  });
}

function buildPacket(message, receipt) {
  const request = exactMessage(message);
  const createdAt = Date.now();
  const requestDigest = digest({ schema_version: SCHEMA_VERSION, request });
  const expiresAt = createdAt + MAX_AGE_MS;
  const recoveryId = digest({
    request_digest: requestDigest, incident_receipt_id: receipt.receipt_id
  });
  return {
    schema_version: SCHEMA_VERSION, recovery_id: recoveryId,
    request_digest: requestDigest, query_digest: digest({ query: request.text }),
    query: request.text, request, incident_receipt: receipt,
    created_at_epoch_ms: createdAt, expires_at_epoch_ms: expiresAt
  };
}

function stageBinding(packet) {
  const receipt = packet.incident_receipt;
  const payload = {
    schema_version: SCHEMA_VERSION, status: 'STAGED',
    recovery_id: packet.recovery_id, request_digest: packet.request_digest,
    query_digest: packet.query_digest, incident_id: receipt.incident_id,
    incident_receipt_id: receipt.receipt_id, incident_kind: receipt.incident_kind,
    task_id: receipt.task_id, request_event_id: receipt.request_event_id,
    target_repo_head_sha: receipt.target_repo_head_sha,
    workspace_repo_head_sha: receipt.workspace_repo_head_sha,
    observed_authority_head_sha: receipt.observed_authority_head_sha,
    authority_root_digest: receipt.authority_root_digest,
    created_at_epoch_ms: packet.created_at_epoch_ms,
    expires_at_epoch_ms: packet.expires_at_epoch_ms,
    authority_effect: 'none'
  };
  payload.payload_digest = digest(payload);
  return payload;
}

function expectedStageEventId(packet) {
  return STAGE_EVENT_PREFIX + stageBinding(packet).payload_digest.slice(7);
}

function stagedReceipt(packet, result) {
  return {
    ok: true,
    status: 'PENDING_REPAIR',
    reason: '',
    recovery_id: packet.recovery_id,
    request_digest: packet.request_digest,
    query_digest: packet.query_digest,
    incident_id: packet.incident_receipt.incident_id,
    incident_task_id: packet.incident_receipt.task_id,
    incident_repair_receipt_id: packet.incident_receipt.receipt_id,
    request_event_id: packet.incident_receipt.request_event_id,
    target_repo_head_sha: packet.incident_receipt.target_repo_head_sha,
    authority_root_digest: packet.incident_receipt.authority_root_digest,
    stage_event_id: result.stage_event_id,
    stage_payload_digest: result.stage_payload_digest,
    expires_at_epoch_ms: packet.expires_at_epoch_ms,
    authority_effect: 'none'
  };
}

async function persistStagePacket(options, packet, receipt) {
  const existing = await options.secretStorage.get(SECRET_KEY);
  const raw = JSON.stringify(packet);
  if (Buffer.byteLength(raw, 'utf8') > MAX_SECRET_BYTES) return failure('recovery_secret_too_large');
  let selected = packet;
  if (existing) {
    const prior = await loadPacket(options.secretStorage);
    if (prior.ok) {
      if (
        prior.request_digest !== packet.request_digest
        || prior.incident_receipt.receipt_id !== receipt.receipt_id
      ) return failure('recovery_secret_already_pending');
      selected = prior;
    } else {
      await options.secretStorage.delete(SECRET_KEY);
      if (await options.secretStorage.get(SECRET_KEY)) {
        return failure('recovery_secret_retire_failed');
      }
    }
  }
  if (!existing || selected === packet) await options.secretStorage.store(SECRET_KEY, raw);
  return selected;
}

async function stageLocked(options, message, meta) {
  if (!eligible(meta, message)) return failure('recovery_not_eligible');
  const receipt = incidentReceipt(meta);
  const selected = await persistStagePacket(options, buildPacket(message, receipt), receipt);
  if (selected.ok === false) return selected;
  const result = await bridge(options, 'stage', selected);
  if (!stageResultMatches(result, selected)) {
    await options.secretStorage.delete(SECRET_KEY);
    return failure(result.reason || 'recovery_stage_binding_failed');
  }
  return stagedReceipt(selected, result);
}

function stage(options, message, meta) {
  return serializeSecretOperation(() => stageLocked(options, message, meta));
}

async function stageAfterCompatibility(options, message, meta, verifyCompatibility) {
  let compatible = false;
  try { compatible = await verifyCompatibility(options.root); } catch (err) { compatible = false; }
  return compatible === true
    ? stage(options, message, meta)
    : failure('backend_compatibility_preflight_blocked', 'BLOCKED');
}

async function claimLocked(options) {
  const packet = await loadPacket(options.secretStorage);
  if (!packet.ok) {
    if (packet.reason !== 'recovery_secret_missing') {
      await options.secretStorage.delete(SECRET_KEY);
    }
    return packet;
  }
  const result = await bridge(options, 'claim', packet);
  if (!result.ok) {
    if (result.status !== 'WAITING') await options.secretStorage.delete(SECRET_KEY);
    return Object.assign({}, result, { request: null });
  }
  if (!readyResultMatches(result, packet)) {
    await options.secretStorage.delete(SECRET_KEY);
    return failure('recovery_ready_binding_mismatch');
  }
  await options.secretStorage.delete(SECRET_KEY);
  if (await options.secretStorage.get(SECRET_KEY)) return failure('recovery_secret_consume_failed');
  return Object.assign({}, result, { recovery_id: packet.recovery_id, request: packet.request });
}

function claim(options) {
  return serializeSecretOperation(() => claimLocked(options));
}

async function hasPending(secretStorage) {
  try { return Boolean(await secretStorage.get(SECRET_KEY)); }
  catch (err) { return true; }
}

async function claimAfterCompatibility(options, verifyCompatibility) {
  let compatible = false;
  try { compatible = await verifyCompatibility(options.root); } catch (err) { compatible = false; }
  return compatible === true
    ? claim(options)
    : failure('backend_compatibility_preflight_blocked', 'BLOCKED');
}

function readyResultMatches(result, packet) {
  const receipt = packet.incident_receipt;
  return result.status === 'READY'
    && result.incident_id === receipt.incident_id
    && result.incident_task_id === receipt.task_id
    && result.incident_repair_receipt_id === receipt.receipt_id
    && result.recovery_id === packet.recovery_id
    && result.request_digest === packet.request_digest
    && result.query_digest === packet.query_digest
    && result.stage_event_id === expectedStageEventId(packet)
    && result.stage_payload_digest === stageBinding(packet).payload_digest
    && result.claim_event_id === CLAIM_EVENT_PREFIX + packet.recovery_id.slice(7)
    && SHA.test(String(result.claim_payload_digest || ''))
    && result.target_repo_head_sha === receipt.target_repo_head_sha
    && result.authority_root_digest === receipt.authority_root_digest
    && SHA.test(String(result.generation_id || ''))
    && SHA.test(String(result.freshness_receipt_digest || ''))
    && result.no_holoindex_reindex_performed === true
    && result.authority_effect === 'none';
}

function stageResultMatches(result, packet) {
  const binding = stageBinding(packet);
  return Boolean(
    result && result.ok === true && result.status === 'STAGED'
    && result.stage_event_id === STAGE_EVENT_PREFIX + binding.payload_digest.slice(7)
    && result.stage_payload_digest === binding.payload_digest
    && result.incident_id === packet.incident_receipt.incident_id
    && result.incident_repair_receipt_id === packet.incident_receipt.receipt_id
    && result.recovery_id === packet.recovery_id
    && result.task_id === packet.incident_receipt.task_id
    && result.request_event_id === packet.incident_receipt.request_event_id
    && result.target_repo_head_sha === packet.incident_receipt.target_repo_head_sha
    && result.authority_root_digest === packet.incident_receipt.authority_root_digest
    && result.authority_effect === 'none'
  );
}

async function finish(_options, recoveryId, result, succeeded) {
  return {
    ok: succeeded === true,
    status: succeeded === true ? 'COMPLETED' : 'FAILED',
    reason: succeeded === true ? '' : 'recovery_output_not_verified',
    recovery_id: recoveryId,
    terminal_result_digest: digest({ result: result && typeof result === 'object' ? result : null }),
    authority_effect: 'none'
  };
}

async function loadPacket(secretStorage) {
  const raw = await secretStorage.get(SECRET_KEY);
  if (!raw) return failure('recovery_secret_missing');
  try {
    const value = JSON.parse(raw);
    const normalized = exactMessage(value.request || {});
    const requestDigest = digest({ schema_version: SCHEMA_VERSION, request: value.request });
  const recoveryId = digest({
    request_digest: requestDigest,
    incident_receipt_id: value.incident_receipt && value.incident_receipt.receipt_id
    });
    if (
      Object.keys(value).sort().join('|') !== PACKET_KEYS.join('|')
      || value.schema_version !== SCHEMA_VERSION || value.request_digest !== requestDigest
      || value.recovery_id !== recoveryId || value.query_digest !== digest({ query: value.query })
      || value.query !== value.request.text || digest({ request: value.request }) !== digest({ request: normalized })
      || value.request.useLastPacket !== false || !Number.isSafeInteger(value.created_at_epoch_ms)
      || value.expires_at_epoch_ms !== value.created_at_epoch_ms + MAX_AGE_MS
      || Date.now() >= value.expires_at_epoch_ms || !incidentReceipt({ incident_repair_receipt: value.incident_receipt })
    ) return failure('recovery_secret_invalid');
    return Object.assign({ ok: true, status: 'PENDING_REPAIR' }, value);
  } catch (err) {
    return failure('recovery_secret_invalid');
  }
}

module.exports = {
  SCHEMA_VERSION, SECRET_KEY, claim, claimAfterCompatibility, digest, eligible, exactMessage, finish,
  hasPending, loadPacket, readyResultMatches, stage, stageAfterCompatibility,
  stageBinding, stageResultMatches, deferredIncidentValid
};
