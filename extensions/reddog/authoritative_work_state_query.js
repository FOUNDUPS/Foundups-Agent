'use strict';

const cp = require('child_process');
const crypto = require('crypto');

const LOCAL_FAST_PATH = 'authoritative_work_state';
const MAX_OUTPUT_BYTES = 2 * 1024 * 1024;
const BRIDGE_TIMEOUT_MS = 15000;
const LOCAL_FAST_PATHS = new Set([
  'simple_identity',
  'run_trace_assessment',
  'daemon_output_assessment',
  LOCAL_FAST_PATH
]);

function isAuthoritativeWorkStateQuestion(value) {
  const text = stripQuotedData(value).trim();
  if (!text || text.length > 500 || /```/.test(text)) {
    return false;
  }
  return [
    /^(?:what(?:'s| is)\s+next|what\s+(?:do|should|must|can)\s+(?:we|i|reddog)\s+(?:need\s+to\s+)?(?:do|work\s+on)(?:\s+next)?)[?.!]*$/i,
    /^(?:show|give|report)\s+(?:me\s+)?(?:the\s+)?(?:current\s+)?(?:authoritative\s+)?(?:work|queue|slice)\s+(?:state|status|priority|plan)[?.!]*$/i,
    /^(?:what|which)\s+(?:is|are)\s+(?:the\s+)?(?:current\s+)?(?:selected|next|highest-priority)\s+(?:work|slice|queue item)[?.!]*$/i
  ].some((pattern) => pattern.test(text));
}

function stripQuotedData(value) {
  const lines = String(value || '').split(/\r?\n/);
  let fenced = false;
  return lines.filter((line) => {
    if (line.trim().startsWith('```')) {
      fenced = !fenced;
      return false;
    }
    return !fenced && !line.trim().startsWith('>');
  }).join('\n');
}

function isLocalFastPath(name) {
  return LOCAL_FAST_PATHS.has(String(name || ''));
}

function localModelMode(name) {
  const modes = {
    simple_identity: 'local_identity_fast_path',
    run_trace_assessment: 'local_run_trace_assessment',
    daemon_output_assessment: 'local_daemon_output_assessment',
    authoritative_work_state: 'local_authoritative_work_state'
  };
  return modes[String(name || '')] || null;
}

function emptyContextPacket() {
  return {
    text: '',
    summary: '',
    quality: 'local_authoritative_work_state_query',
    holoindex_meta: null,
    holoindex_scorecard: null,
    audit_context: false,
    direct_read_hits: [],
    required_targets_authoritative_paths: []
  };
}

function runAuthoritativeWorkStateQuery(options) {
  const opts = options && typeof options === 'object' ? options : {};
  return new Promise((resolve) => {
    let child;
    try {
      child = (opts.spawn || cp.spawn)(
        opts.interpreter,
        ['-B', opts.script],
        {
          cwd: opts.repoRoot,
          env: opts.env,
          stdio: ['pipe', 'pipe', 'ignore'],
          windowsHide: true
        }
      );
    } catch (_err) {
      resolve(failureReceipt('authoritative_work_state_bridge_spawn_failed'));
      return;
    }
    collectBridgeResult(child, opts, resolve);
  });
}

function runConfiguredQuery(options) {
  const root = options.workspaceRoot();
  const interpreter = options.resolveInterpreter(
    root,
    options.configValue('pythonPath', 'python')
  );
  return runAuthoritativeWorkStateQuery({
    interpreter: interpreter.path,
    script: options.scriptPath(root),
    repoRoot: root,
    env: options.bridgeEnv(process.env)
  });
}

function statusText(name) {
  const messages = {
    simple_identity: 'Simple RedDog identity question answered locally. No HoloIndex, OpenRouter, Fusion, repair, or downstream action planning.',
    run_trace_assessment: 'Run Trace diagnostics answered locally. No HoloIndex, OpenRouter, Fusion, repair, or downstream action planning.',
    daemon_output_assessment: 'DAEmon/log diagnostics answered locally. Pasted operational text is treated as data; no HoloIndex, OpenRouter, Fusion, repair, or downstream action planning.',
    authoritative_work_state: 'Reading authoritative work state locally. No HoloIndex, OpenRouter, Fusion, queue mutation, or worker dispatch.'
  };
  return messages[String(name || '')] || '';
}

async function resolveLocalResult(name, options) {
  if (name === 'simple_identity') {
    return options.identity();
  }
  if (name === 'run_trace_assessment') {
    return options.runTrace();
  }
  if (name === 'daemon_output_assessment') {
    return options.daemon();
  }
  if (name === LOCAL_FAST_PATH) {
    return buildLocalResult(await options.workState());
  }
  return null;
}

function collectBridgeResult(child, options, resolve) {
  let stdout = '';
  let settled = false;
  const finish = (value) => {
    if (settled) return;
    settled = true;
    clearTimeout(timer);
    resolve(value);
  };
  const timer = setTimeout(() => {
    if (child && typeof child.kill === 'function') child.kill();
    finish(failureReceipt('authoritative_work_state_bridge_timeout'));
  }, options.timeoutMs || BRIDGE_TIMEOUT_MS);
  child.stdout.on('data', (chunk) => {
    stdout += String(chunk || '');
    if (Buffer.byteLength(stdout, 'utf8') > MAX_OUTPUT_BYTES) {
      if (typeof child.kill === 'function') child.kill();
      finish(failureReceipt('authoritative_work_state_bridge_output_too_large'));
    }
  });
  child.once('error', () => finish(
    failureReceipt('authoritative_work_state_bridge_failed')
  ));
  child.once('close', (code) => finish(
    parseBridgeOutput(code, stdout)
  ));
  sendBridgeInput(child, options.repoRoot, finish);
}

function sendBridgeInput(child, repoRoot, finish) {
  try {
    child.stdin.end(JSON.stringify({ repo_root: repoRoot }));
  } catch (_err) {
    finish(failureReceipt('authoritative_work_state_bridge_input_failed'));
  }
}

function parseBridgeOutput(code, stdout) {
  if (code !== 0) {
    return failureReceipt('authoritative_work_state_bridge_failed');
  }
  try {
    const lines = String(stdout || '').trim().split(/\r?\n/);
    const value = JSON.parse(lines[lines.length - 1]);
    return validateReceipt(value);
  } catch (_err) {
    return failureReceipt('authoritative_work_state_receipt_invalid');
  }
}

function validateReceipt(value) {
  if (!value || value.schema_version !== 'reddog_authoritative_work_state_query.v1') {
    return failureReceipt('authoritative_work_state_receipt_invalid');
  }
  if (value.accepted !== true) {
    return value;
  }
  const requiredTrue = [
    'no_model_call_performed', 'no_holoindex_query_performed',
    'no_holoindex_reindex_performed', 'no_queue_mutation_performed',
    'no_claim_mutation_performed', 'no_worker_spawn_performed',
    'no_shell_command_executed', 'no_repo_mutation_performed',
    'no_execution_performed'
  ];
  const payload = { ...value };
  delete payload.receipt_id;
  const valid = value.status === 'AUTHORITATIVE_WORK_STATE_READY'
    && Array.isArray(value.rejection_reasons) && value.rejection_reasons.length === 0
    && requiredTrue.every((key) => value[key] === true)
    && value.receipt_id === canonicalDigest(payload);
  return valid ? value : failureReceipt('authoritative_work_state_receipt_invalid');
}

function canonicalDigest(value) {
  const canonical = JSON.stringify(sortCanonical(value));
  const ascii = canonical.replace(/[^\x00-\x7f]/g, (character) => (
    '\\u' + character.charCodeAt(0).toString(16).padStart(4, '0')
  ));
  return crypto.createHash('sha256').update(ascii, 'utf8').digest('hex');
}

function sortCanonical(value) {
  if (Array.isArray(value)) return value.map(sortCanonical);
  if (!value || typeof value !== 'object') return value;
  return Object.keys(value).sort().reduce((result, key) => {
    result[key] = sortCanonical(value[key]);
    return result;
  }, {});
}

function failureReceipt(reason) {
  return {
    schema_version: 'reddog_authoritative_work_state_query.v1',
    accepted: false,
    status: 'AUTHORITATIVE_WORK_STATE_NOT_READY',
    rejection_reasons: [reason],
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
}

function buildLocalResult(receipt) {
  const candidate = receipt && typeof receipt === 'object'
    ? receipt
    : failureReceipt('authoritative_work_state_receipt_missing');
  const value = candidate.accepted === true ? validateReceipt(candidate) : candidate;
  const accepted = value.accepted === true;
  return {
    ok: true,
    content: buildContent(value),
    mode: 'local_authoritative_work_state',
    lead_model: 'local',
    history: [],
    made_network_call: false,
    retry_count: 0,
    no_execution_performed: true,
    no_enqueue_performed: true,
    review_packet: {
      made_network_call: false,
      retry_count: 0,
      local_fast_path: LOCAL_FAST_PATH,
      authoritative_work_state_ready: accepted,
      authoritative_work_state_query_receipt: value,
      no_execution_performed: true,
      no_enqueue_performed: true
    }
  };
}

function buildContent(receipt) {
  const accepted = receipt.accepted === true;
  const reasons = safeStrings(receipt.rejection_reasons);
  return [
    '## Decision',
    accepted
      ? 'OBSERVED: The authoritative RedDog work queue is ready for its next governed gate.'
      : 'OBSERVED: Authoritative work state is NOT_READY. RedDog will not speculate about the next task.',
    '',
    '## Authoritative Work State',
    ...workStateLines(receipt),
    '- rejection_reasons: ' + JSON.stringify(reasons),
    '',
    '## WSP_97 Truth Boundary',
    '- OBSERVED: values above come from one revision-validated, fresh, governed-lineage queue receipt.',
    '- OBSERVED: no HoloIndex query, model call, queue/claim mutation, shell, worker spawn, or execution occurred.',
    '- SPECIFIED_NOT_IMPLEMENTED: this query does not authorize or dispatch the selected work.',
    '',
    '## Next Safest Step',
    accepted
      ? 'Proceed only through `' + safe(receipt.next_required_gate) + '` using the bound queue and WSP_15 receipts.'
      : 'Refresh/reconcile authoritative work state locally, then repeat this query. Do not route this question to Fusion.'
  ].join('\n');
}

function workStateLines(receipt) {
  return [
    '- status: ' + safe(receipt.status),
    '- receipt_id: ' + safe(receipt.receipt_id),
    '- snapshot_revision: ' + safe(receipt.snapshot_revision),
    '- snapshot_content_digest: ' + safe(receipt.snapshot_content_digest),
    '- queue_consumer_receipt_id: ' + safe(receipt.queue_consumer_receipt_id),
    '- queue_item_id: ' + safe(receipt.queue_item_id),
    '- selected_slice: ' + safe(receipt.selected_slice),
    '- claim_id: ' + safe(receipt.claim_id),
    '- worker_id: ' + safe(receipt.worker_id),
    '- wsp15_allocation_receipt_id: ' + safe(receipt.wsp15_allocation_receipt_id),
    '- wsp15_allocation_digest: ' + safe(receipt.wsp15_allocation_digest),
    '- WSP_15 priority: ' + safe(receipt.wsp15_priority),
    '- WSP_15 MPS total: ' + safe(receipt.wsp15_mps_total),
    '- reasoning_tier: ' + safe(receipt.reasoning_tier),
    '- next_required_gate: ' + safe(receipt.next_required_gate)
  ];
}

function safe(value) {
  const text = String(value === undefined || value === null ? 'none' : value);
  return /^[A-Za-z0-9_.:/-]{1,180}$/.test(text) ? text : 'redacted';
}

function safeStrings(values) {
  return Array.isArray(values)
    ? values.map(safe).filter((value) => value !== 'redacted').slice(0, 20)
    : [];
}

module.exports = {
  LOCAL_FAST_PATH,
  buildLocalResult,
  canonicalDigest,
  emptyContextPacket,
  failureReceipt,
  isAuthoritativeWorkStateQuestion,
  isLocalFastPath,
  localModelMode,
  parseBridgeOutput,
  resolveLocalResult,
  runConfiguredQuery,
  statusText,
  runAuthoritativeWorkStateQuery
};
