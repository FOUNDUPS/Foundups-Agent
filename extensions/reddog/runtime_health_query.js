'use strict';

const path = require('path');
const { Worker } = require('worker_threads');

const LOCAL_FAST_PATH = 'runtime_health';
const HEALTH_QUERY = 'HoloIndex current generation semantic query health';
const HEALTH_TIMEOUT_MS = 30000;

function isRuntimeHealthQuestion(value) {
  const text = String(value || '').trim();
  if (!text || text.length > 120 || /```|\n|[;&|]/.test(text)) return false;
  const subject = '(?:the\\s+)?(?:holo\\s*index|holoindex)';
  const direct = new RegExp('^is\\s+' + subject + '\\s+(?:working|ready|healthy)\\??$', 'i');
  const command = new RegExp('^(?:test|check|show|report)\\s+' + subject
    + '(?:\\s+(?:health|status))?(?:\\s+(?:is\\s+it\\s+)?(?:working|ready|healthy))?\\??$', 'i');
  return direct.test(text) || command.test(text);
}

function runHoloIndexHealth(options) {
  const opts = options && typeof options === 'object' ? options : {};
  if (typeof opts.queryOwner === 'function' && typeof opts.isAccepted === 'function') {
    const result = opts.queryOwner(ownerOptions(opts));
    return Promise.resolve(buildLocalResult(result, opts.isAccepted(result)));
  }
  return new Promise((resolve) => startHealthWorker(opts, resolve));
}

function ownerOptions(options) {
  return {
    root: options.root,
    interpreterPath: options.interpreterPath,
    env: options.env,
    query: HEALTH_QUERY,
    limit: 1
  };
}

function startHealthWorker(options, resolve) {
  let worker;
  try {
    worker = new (options.Worker || Worker)(
      path.join(__dirname, 'runtime_health_worker.js'),
      { workerData: ownerOptions(options) }
    );
  } catch (_err) {
    resolve(buildLocalResult({ error: 'holoindex_health_worker_failed' }, false));
    return;
  }
  collectHealthWorker(worker, options.timeoutMs || HEALTH_TIMEOUT_MS, resolve);
}

function collectHealthWorker(worker, timeoutMs, resolve) {
  let settled = false;
  const finish = (result, accepted) => {
    if (settled) return;
    settled = true;
    clearTimeout(timer);
    resolve(buildLocalResult(result, accepted));
  };
  const timer = setTimeout(() => {
    if (typeof worker.terminate === 'function') worker.terminate();
    finish({ error: 'holoindex_health_timeout' }, false);
  }, timeoutMs);
  worker.once('message', (message) => finish(message.result, message.accepted === true));
  worker.once('error', () => finish({ error: 'holoindex_health_worker_failed' }, false));
  worker.once('exit', (code) => {
    if (code !== 0) finish({ error: 'holoindex_health_worker_failed' }, false);
  });
}

function buildLocalResult(result, accepted) {
  const value = result && typeof result === 'object' ? result : {};
  const ready = accepted === true;
  return {
    ok: true,
    diagnostic_ready: ready,
    content: healthContent(value, ready),
    mode: 'local_runtime_health',
    lead_model: 'local',
    history: [],
    made_network_call: false,
    retry_count: 0,
    no_execution_performed: true,
    no_enqueue_performed: true,
    review_packet: healthPacket(value, ready)
  };
}

function healthContent(value, ready) {
  const receipt = value.query_receipt && typeof value.query_receipt === 'object'
    ? value.query_receipt : {};
  return [
    '## Decision',
    ready
      ? 'OBSERVED: HoloIndex is working through the authenticated generation-bound semantic owner.'
      : 'OBSERVED: HoloIndex health is NOT_READY. No model call was made and no repair was attempted.',
    '', '## Health Receipt',
    '- status: ' + (ready ? 'CURRENT' : 'NOT_READY'),
    '- retrieval_mode: ' + safe(value.retrieval_mode),
    '- generation_id: ' + safe(value.freshness_generation_id),
    '- repository_head: ' + safe(value.repo_head_sha),
    '- query_receipt_id: ' + safe(receipt.receipt_id),
    '- index_gap_detected: ' + String(value.index_gap_detected === true),
    '- error: ' + safe(value.error),
    '', '## WSP_97 Truth Boundary',
    '- OBSERVED: the result is accepted only when the worker validates the existing process-local Holo owner proof.',
    '- OBSERVED: no OpenRouter inference, Fusion, re-index, repository mutation, queue mutation, or worker dispatch occurred.',
    '- SPECIFIED_NOT_IMPLEMENTED: this diagnostic does not authorize automatic repair.',
    '', '## Next Safest Step',
    ready ? 'No repair is required. Submit the repository work focus separately.'
      : 'Route the owner error to governed Holo maintenance, then repeat this health query.'
  ].join('\n');
}

function healthPacket(value, ready) {
  const receipt = value.query_receipt && typeof value.query_receipt === 'object'
    ? value.query_receipt : {};
  return {
    made_network_call: false,
    local_fast_path: LOCAL_FAST_PATH,
    component: 'holoindex',
    diagnostic_ready: ready,
    health_ready: ready,
    query_receipt_id: safe(receipt.receipt_id),
    generation_id: safe(value.freshness_generation_id),
    index_gap_detected: value.index_gap_detected === true,
    error: safe(value.error),
    no_holoindex_reindex_performed: value.no_holoindex_reindex_performed === true,
    no_execution_performed: true,
    no_enqueue_performed: true
  };
}

function safe(value) {
  const text = String(value === undefined || value === null || value === '' ? 'none' : value);
  return /^[A-Za-z0-9_.:/-]{1,200}$/.test(text) ? text : 'redacted';
}

module.exports = {
  HEALTH_QUERY,
  LOCAL_FAST_PATH,
  buildLocalResult,
  isRuntimeHealthQuestion,
  runHoloIndexHealth
};
