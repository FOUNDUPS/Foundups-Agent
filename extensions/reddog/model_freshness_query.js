'use strict';

const cp = require('child_process');
const crypto = require('crypto');

const LOCAL_FAST_PATH = 'model_freshness';
const SCHEMA = 'reddog_model_freshness_query.v1';
const MAX_OUTPUT_BYTES = 1024 * 1024;
const TIMEOUT_MS = 30000;
const PROVIDER_ENDPOINT = 'https://openrouter.ai/api/v1/models';
const EXACT_KEYS = new Set([
  'accepted', 'all_configured_models_available', 'all_configured_models_provider_latest',
  'candidate_snapshot_id', 'catalog_fresh', 'chronology_complete', 'configured_models',
  'credential_free_catalog_egress', 'external_catalog_call_performed', 'fresh_until_ms',
  'latestness_status', 'no_holoindex_reindex_performed', 'no_model_inference_performed',
  'no_model_selection_changed', 'no_repository_mutation_performed',
  'no_runtime_binding_changed', 'observed_at_ms', 'provider', 'provider_endpoint',
  'provider_receipt_id', 'public_catalog_egress_gate', 'queried_at_ms',
  'receipt_id', 'rejection_reasons', 'requested_model_ids', 'schema_version', 'status'
]);

function isModelFreshnessQuestion(value) {
  const text = String(value || '').trim();
  if (!text || text.length > 140 || /```|\n|[;&|]/.test(text)) return false;
  const subject = '(?:(?:the|our|configured)\\s+)?(?:models?|model\\s+panel|principal\\s+model)';
  const direct = new RegExp('^are\\s+' + subject + '\\s+(?:the\\s+)?(?:latest|newest|current|up[ -]?to[ -]?date)\\??$', 'i');
  const using = /^are\s+we\s+using\s+(?:the\s+)?(?:latest|newest|current)\s+(?:models?|model\s+panel)\??$/i;
  const command = /^(?:check|show|report)\s+(?:(?:the|our|configured)\s+)?(?:model|models|model\s+panel|principal\s+model)\s+(?:freshness|status)\??$/i;
  return direct.test(text) || using.test(text) || command.test(text);
}

function runConfiguredQuery(options) {
  const opts = options && typeof options === 'object' ? options : {};
  return new Promise((resolve) => {
    let child;
    try {
      child = (opts.spawn || cp.spawn)(
        opts.interpreter,
        ['-I', '-B', opts.script],
        { cwd: opts.repoRoot, env: opts.env, stdio: ['pipe', 'pipe', 'ignore'], windowsHide: true }
      );
    } catch (_err) {
      resolve(failure('model_freshness_bridge_spawn_failed'));
      return;
    }
    collect(child, opts, resolve);
  });
}

function collect(child, options, resolve) {
  let stdout = '';
  let settled = false;
  const finish = (value) => {
    if (settled) return;
    settled = true;
    clearTimeout(timer);
    resolve(value);
  };
  const timer = setTimeout(() => {
    if (typeof child.kill === 'function') child.kill();
    finish(failure('model_freshness_bridge_timeout'));
  }, options.timeoutMs || TIMEOUT_MS);
  child.stdout.on('data', (chunk) => {
    stdout += String(chunk || '');
    if (Buffer.byteLength(stdout, 'utf8') > MAX_OUTPUT_BYTES) {
      if (typeof child.kill === 'function') child.kill();
      finish(failure('model_freshness_bridge_output_too_large'));
    }
  });
  child.once('error', () => finish(failure('model_freshness_bridge_failed')));
  child.once('close', (code) => finish(parseOutput(code, stdout, options.modelIds, Date.now())));
  try {
    child.stdin.end(JSON.stringify({ configured_model_ids: options.modelIds }));
  } catch (_err) {
    finish(failure('model_freshness_bridge_input_failed'));
  }
}

function parseOutput(code, stdout, expectedModels, nowMs) {
  if (code !== 0) return failure('model_freshness_bridge_failed');
  try {
    const lines = String(stdout || '').trim().split(/\r?\n/);
    return validate(JSON.parse(lines[lines.length - 1]), expectedModels, nowMs);
  } catch (_err) {
    return failure('model_freshness_receipt_invalid');
  }
}

function validate(value, expectedModels, nowMs) {
  if (!validEnvelope(value)) return failure('model_freshness_receipt_invalid');
  const payload = { ...value };
  delete payload.receipt_id;
  if (value.receipt_id !== digest(payload) || !requiredEffects(value)) {
    return failure('model_freshness_receipt_invalid');
  }
  if (expectedModels !== undefined && !requestBindingValid(value, expectedModels)) {
    return failure('model_freshness_request_binding_invalid');
  }
  if (value.accepted === true && !acceptedEvidenceValid(value, nowMs)) {
    return failure('model_freshness_receipt_invalid');
  }
  return value;
}

function validEnvelope(value) {
  return Boolean(value)
    && value.schema_version === SCHEMA
    && typeof value.accepted === 'boolean'
    && Object.keys(value).every((key) => EXACT_KEYS.has(key))
    && (value.accepted !== true || Object.keys(value).length === EXACT_KEYS.size);
}

function requiredEffects(value) {
  return value.no_model_inference_performed === true
    && value.no_model_selection_changed === true
    && value.no_runtime_binding_changed === true
    && value.no_repository_mutation_performed === true
    && value.no_holoindex_reindex_performed === true;
}

function requestBindingValid(value, expectedModels) {
  const requested = uniqueModels(expectedModels || value.requested_model_ids);
  const receiptModels = uniqueModels(value.requested_model_ids);
  const rows = Array.isArray(value.configured_models)
    ? value.configured_models.map((item) => String((item && item.model_id) || ''))
    : [];
  if (!requested.length || JSON.stringify(requested) !== JSON.stringify(receiptModels)) return false;
  return value.accepted === true
    ? JSON.stringify(requested) === JSON.stringify(rows)
    : rows.length === 0 || JSON.stringify(requested) === JSON.stringify(rows);
}

function acceptedEvidenceValid(value, nowMs) {
  const now = Number(nowMs === undefined ? Date.now() : nowMs);
  return value.status === 'MODEL_FRESHNESS_READY'
    && value.provider === 'openrouter'
    && value.provider_endpoint === PROVIDER_ENDPOINT
    && /^model_provider_catalog_discovery_receipt:[0-9a-f]{64}$/.test(value.provider_receipt_id)
    && /^model_provider_catalog_candidate_snapshot:[0-9a-f]{64}$/.test(value.candidate_snapshot_id)
    && acceptedTimesValid(value, now)
    && acceptedFlagsValid(value)
    && acceptedRowsValid(value.configured_models);
}

function acceptedTimesValid(value, now) {
  return Number.isInteger(value.observed_at_ms)
    && Number.isInteger(value.fresh_until_ms)
    && Number.isInteger(value.queried_at_ms)
    && value.observed_at_ms <= value.queried_at_ms
    && value.queried_at_ms <= value.fresh_until_ms
    && value.observed_at_ms <= now
    && now <= value.fresh_until_ms;
}

function acceptedFlagsValid(value) {
  const expectedLatest = value.all_configured_models_provider_latest
    ? 'ALL_PROVIDER_LATEST' : 'NEWER_PROVIDER_MODELS_AVAILABLE';
  return value.catalog_fresh === true
    && value.all_configured_models_available === true
    && value.chronology_complete === true
    && value.credential_free_catalog_egress === true
    && value.public_catalog_egress_gate === 'PASS'
    && value.external_catalog_call_performed === true
    && value.latestness_status === expectedLatest;
}

function acceptedRowsValid(rows) {
  return Array.isArray(rows) && rows.length > 0 && rows.every((item) => (
    item && item.available === true
    && item.chronology_known === true
    && typeof item.provider_latest_known === 'boolean'
    && Array.isArray(item.newer_provider_model_ids)
  ));
}

function buildLocalResult(receipt) {
  const value = validate(receipt);
  const ready = value.accepted === true;
  return {
    ok: true,
    diagnostic_ready: ready,
    content: modelContent(value, ready),
    mode: 'local_model_freshness',
    lead_model: 'local_catalog',
    history: [],
    made_network_call: value.external_catalog_call_performed === true,
    retry_count: 0,
    no_execution_performed: true,
    no_enqueue_performed: true,
    review_packet: modelPacket(value, ready)
  };
}

function modelContent(value, ready) {
  const rows = modelEvidenceLines(value);
  return [
    '## Decision',
    decisionLine(value, ready),
    '', '## Configured Model Evidence',
    ...rows,
    '- latestness_status: ' + safe(value.latestness_status),
    '- catalog_snapshot_id: ' + safe(value.candidate_snapshot_id),
    '- provider_receipt_id: ' + safe(value.provider_receipt_id),
    '- observed_at_ms: ' + safe(value.observed_at_ms),
    '- fresh_until_ms: ' + safe(value.fresh_until_ms),
    '', '## Interpretation',
    '- Provider recency is not task fitness. A newer model is a challenger, not an automatic production replacement.',
    '- Production changes still require benchmark, independent verifier, promotion, and runtime-binding receipts.',
    '', '## WSP_97 Truth Boundary',
    '- OBSERVED: availability and chronology come from one credential-free bounded OpenRouter catalog receipt.',
    '- OBSERVED: no inference, selection change, binding change, repository mutation, or HoloIndex re-index occurred.',
    '- NEEDS_VERIFICATION: provider metadata does not prove benchmark superiority for FoundUps tasks.'
  ].join('\n');
}

function decisionLine(value, ready) {
  if (!ready) return 'OBSERVED: Model freshness is NOT_READY; currentness remains UNKNOWN.';
  return value.all_configured_models_provider_latest === true
    ? 'OBSERVED: Every configured RedDog model is available and provider-latest in the fresh catalog.'
    : 'OBSERVED: Every configured model is available, but at least one has a newer provider model.';
}

function modelEvidenceLines(value) {
  const rows = Array.isArray(value.configured_models) ? value.configured_models.map((item) => (
    '- `' + safe(item.model_id) + '`: available=' + String(item.available === true)
      + ', chronology_known=' + String(item.chronology_known === true)
      + ', provider_latest_known=' + String(item.provider_latest_known === true)
      + ', newer_provider_models=' + JSON.stringify(safeList(item.newer_provider_model_ids))
  )) : [];
  if (!value.accepted) rows.push('- rejection_reasons: ' + JSON.stringify(safeList(value.rejection_reasons)));
  return rows;
}

function modelPacket(value, ready) {
  return {
    local_fast_path: LOCAL_FAST_PATH,
    diagnostic_ready: ready,
    model_freshness_ready: ready,
    model_freshness_receipt: value,
    no_execution_performed: true,
    no_enqueue_performed: true
  };
}

function digest(value) {
  return 'sha256:' + crypto.createHash('sha256').update(canonical(value), 'utf8').digest('hex');
}

function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map((key) => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
  }
  return JSON.stringify(value);
}

function failure(reason) {
  const value = {
    schema_version: SCHEMA,
    accepted: false,
    status: 'MODEL_FRESHNESS_NOT_READY',
    rejection_reasons: [reason],
    no_model_inference_performed: true,
    no_model_selection_changed: true,
    no_runtime_binding_changed: true,
    no_repository_mutation_performed: true,
    no_holoindex_reindex_performed: true
  };
  value.receipt_id = digest(value);
  return value;
}

function safe(value) {
  const text = String(value === undefined || value === null || value === '' ? 'none' : value);
  return /^[A-Za-z0-9_.:/-]{1,220}$/.test(text) ? text : 'redacted';
}

function safeList(values) {
  return Array.isArray(values) ? values.map(safe).slice(0, 8) : [];
}

function uniqueModels(values) {
  return Array.isArray(values)
    ? Array.from(new Set(values.map((item) => String(item || '').trim().toLowerCase()).filter(Boolean)))
    : [];
}

module.exports = {
  LOCAL_FAST_PATH,
  buildLocalResult,
  digest,
  failure,
  isModelFreshnessQuestion,
  parseOutput,
  runConfiguredQuery,
  validate
};
