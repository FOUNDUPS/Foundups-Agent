'use strict';

const SAFE_PROGRESS_KEYS = Object.freeze([
  'run_id', 'event_id', 'sequence', 'status', 'role', 'model', 'elapsed_ms'
]);
const EXPECTED_RUN_ID = Symbol('reddogExpectedBridgeRunId');
const SECRET_LIKE = /(?:sk-or-v1-[A-Za-z0-9_-]{8,}|sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{20,}|xox[baprs]-[0-9A-Za-z-]{10,}|eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._~-]{8,})/gi;
const STAGE_TEXT = Object.freeze({
  bridge_start: 'Bridge Python started.', env_check: 'Bridge environment checked.',
  redaction_start: 'Redaction gate started.', redaction_pass: 'Redaction gate passed.',
  redaction_blocked: 'Redaction gate blocked.', fusion_alias_start: 'Fusion alias request started.',
  fusion_alias_done: 'Fusion alias response received.', lead_start: 'Lead request started.',
  lead_done: 'Lead response received.', panel_start: 'Panel requests started.',
  panel_done: 'Panel response received.', panel_blocked: 'Panel request blocked.',
  synthesis_start: 'Synthesis request started.', synthesis_done: 'Synthesis complete.',
  single_start: 'OpenRouter request started.', single_done: 'OpenRouter response received.'
});

function sanitizeProgressText(stage, text) {
  if (STAGE_TEXT[stage]) return STAGE_TEXT[stage];
  return String(text || '').replace(SECRET_LIKE, '[REDACTED]').replace(/[\r\n\u0000-\u001f]+/g, ' ').slice(0, 240);
}

function sanitizeProgressMetadataString(value) {
  const cleaned = String(value || '').replace(SECRET_LIKE, '').replace(/[\r\n\u0000-\u001f]+/g, '').slice(0, 256);
  return /^[A-Za-z0-9][A-Za-z0-9._:/@+()-]*$/.test(cleaned) ? cleaned : '';
}

function bindFusionProgressResultToRun(result, expectedRunId) {
  if (result && typeof result === 'object') {
    Object.defineProperty(result, EXPECTED_RUN_ID, { value: String(expectedRunId || ''), enumerable: false });
  }
  return result;
}

function buildProgressMessage(stage, text, metadata) {
  const source = metadata && typeof metadata === 'object' ? metadata : {};
  const message = { command: 'progress', stage: stage || null, text: sanitizeProgressText(stage, text) };
  for (const key of SAFE_PROGRESS_KEYS) {
    const value = source[key];
    if (typeof value === 'string') {
      const cleaned = sanitizeProgressMetadataString(value);
      if (cleaned) message[key] = cleaned;
    } else if (typeof value === 'number' && Number.isFinite(value) && value >= 0) {
      message[key] = value;
    }
  }
  return message;
}

function createProgressLineDecoder(onProgress) {
  let buffered = '';
  const consume = (line) => {
    if (!line.trim()) return;
    try {
      const event = JSON.parse(line);
      if (event && event.event === 'progress' && event.text) {
        onProgress(event.stage || null, event.text, event);
      }
    } catch (err) {
      // Python dependencies may write non-JSON diagnostics to stderr.
    }
  };
  return {
    push(text) {
      buffered += String(text || '');
      const lines = buffered.split(/\r?\n/);
      buffered = lines.pop() || '';
      lines.forEach(consume);
    },
    flush() {
      consume(buffered);
      buffered = '';
    }
  };
}

function createFusionProgressCollector() {
  const receipts = [];
  const rejectionReasons = [];
  let seen = 0;
  return {
    capture(result) {
      const receipt = result && result.fusion_progress_receipt;
      if (!receipt || typeof receipt !== 'object') return;
      seen += 1;
      const validation = result && result.fusion_progress_receipt_validation;
      const expectedRunId = result && result[EXPECTED_RUN_ID];
      if (validation && validation.valid === true && expectedRunId && receipt.run_id === expectedRunId) {
        receipts.push(receipt);
        return;
      }
      const reasons = expectedRunId && receipt.run_id !== expectedRunId
        ? ['fusion_progress_receipt_run_id_mismatch']
        : validation && Array.isArray(validation.rejection_reasons)
        ? validation.rejection_reasons
        : ['fusion_progress_receipt_validation_missing'];
      rejectionReasons.push(...reasons.map(String));
    },
    snapshot() {
      return receipts.slice();
    },
    validation() {
      return {
        applied: seen > 0,
        valid: seen > 0 && rejectionReasons.length === 0 && receipts.length === seen,
        receipt_count: seen,
        rejection_reasons: Array.from(new Set(rejectionReasons))
      };
    }
  };
}

function formatFusionProgressReceiptLines(reviewPacket) {
  const rp = reviewPacket && typeof reviewPacket === 'object' ? reviewPacket : {};
  const validation = rp.fusion_progress_receipt_validation && typeof rp.fusion_progress_receipt_validation === 'object'
    ? rp.fusion_progress_receipt_validation
    : null;
  const validationLines = [
    '- fusion_progress_receipt_validation: ' + (validation && validation.applied === true ? (validation.valid === true ? 'passed' : 'failed') : 'not_applied'),
    '- fusion_progress_receipt_rejection_reasons: ' + (validation && Array.isArray(validation.rejection_reasons) && validation.rejection_reasons.length
      ? validation.rejection_reasons.join(', ') : '(none)')
  ];
  const receipts = Array.isArray(rp.fusion_progress_receipts)
    ? rp.fusion_progress_receipts
    : (rp.fusion_progress_receipt && typeof rp.fusion_progress_receipt === 'object' ? [rp.fusion_progress_receipt] : []);
  if (!receipts.length) return ['- fusion_progress_receipts: 0', ...validationLines];
  const calls = [];
  const receiptIds = [];
  let eventCount = 0;
  for (const receipt of receipts) {
    if (!receipt || typeof receipt !== 'object') continue;
    if (receipt.receipt_id) receiptIds.push(String(receipt.receipt_id));
    eventCount += Number(receipt.event_count) || 0;
    if (Array.isArray(receipt.openrouter_calls)) calls.push(...receipt.openrouter_calls);
  }
  const usage = calls.reduce((total, call) => {
    const item = call && call.usage && typeof call.usage === 'object' ? call.usage : {};
    for (const key of ['prompt_tokens', 'completion_tokens', 'total_tokens', 'reasoning_tokens', 'cached_tokens', 'cost_microcredits']) {
      total[key] += Number(item[key]) || 0;
    }
    return total;
  }, { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0, reasoning_tokens: 0, cached_tokens: 0, cost_microcredits: 0 });
  const generations = calls.map((call) => String(call && call.generation_id || '')).filter(Boolean);
  const routes = calls.map((call) => {
    const meta = call && call.router_metadata && typeof call.router_metadata === 'object' ? call.router_metadata : {};
    return [meta.response_provider, meta.response_model].filter(Boolean).join(':');
  }).filter(Boolean);
  const usageVerifiedCount = calls.filter((call) => call && call.usage_verified === true).length;
  const costAccountingComplete = calls.length > 0
    && calls.every((call) => call && call.cost_accounting_complete === true);
  const failedCallCount = calls.filter((call) => call && call.status === 'FAILED').length;
  const retryCount = calls.reduce((total, call) => total + (Number(call && call.retry_count) || 0), 0);
  const durationMs = calls.reduce((total, call) => total + (Number(call && call.duration_ms) || 0), 0);
  return [
    '- fusion_progress_receipts: ' + receipts.length,
    ...validationLines,
    '- fusion_progress_receipt_ids: ' + (receiptIds.length ? receiptIds.join(', ') : '(none)'),
    '- fusion_progress_events: ' + eventCount,
    '- openrouter_calls_receipted: ' + calls.length,
    '- openrouter_calls_failed: ' + failedCallCount,
    '- openrouter_retries: ' + retryCount,
    '- openrouter_duration_ms: ' + durationMs,
    '- openrouter_usage_verified_calls: ' + usageVerifiedCount + '/' + calls.length,
    '- openrouter_cost_accounting_complete: ' + costAccountingComplete,
    '- openrouter_generation_ids: ' + (generations.length ? generations.join(', ') : '(none)'),
    '- openrouter_selected_routes: ' + (routes.length ? routes.join(', ') : '(none)'),
    '- openrouter_prompt_tokens: ' + usage.prompt_tokens,
    '- openrouter_completion_tokens: ' + usage.completion_tokens,
    '- openrouter_reasoning_tokens: ' + usage.reasoning_tokens,
    '- openrouter_total_tokens: ' + usage.total_tokens,
    '- openrouter_cached_tokens: ' + usage.cached_tokens,
    '- openrouter_cost_microcredits: ' + (costAccountingComplete ? usage.cost_microcredits : 'unknown')
  ];
}

module.exports = {
  bindFusionProgressResultToRun,
  buildProgressMessage,
  createFusionProgressCollector,
  createProgressLineDecoder,
  formatFusionProgressReceiptLines
};
