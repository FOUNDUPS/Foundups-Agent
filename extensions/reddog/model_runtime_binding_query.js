'use strict';

const cp = require('child_process');
const crypto = require('crypto');

const SCHEMA_VERSION = 'reddog_model_runtime_binding_query.v1';
const STATUS_READY = 'MODEL_RUNTIME_BINDING_READY';
const STATUS_UNCONFIGURED = 'MODEL_RUNTIME_BINDING_UNCONFIGURED';
const MAX_OUTPUT_BYTES = 2 * 1024 * 1024;
const BRIDGE_TIMEOUT_MS = 15000;
const MODEL_RE = /^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,119}$/;

function runConfiguredQuery(options) {
  const root = options.workspaceRoot();
  const interpreter = options.resolveInterpreter(
    root,
    options.configValue('pythonPath', 'python')
  );
  return runQuery({
    interpreter: interpreter.path,
    script: options.scriptPath(root),
    repoRoot: root,
    env: options.bridgeEnv(process.env)
  });
}

function runQuery(options) {
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
      resolve(failureReceipt(true, 'model_runtime_binding_bridge_spawn_failed'));
      return;
    }
    collectResult(child, opts, resolve);
  });
}

function collectResult(child, options, resolve) {
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
    finish(failureReceipt(true, 'model_runtime_binding_bridge_timeout'));
  }, options.timeoutMs || BRIDGE_TIMEOUT_MS);
  child.stdout.on('data', (chunk) => {
    stdout += String(chunk || '');
    if (Buffer.byteLength(stdout, 'utf8') > MAX_OUTPUT_BYTES) {
      if (typeof child.kill === 'function') child.kill();
      finish(failureReceipt(true, 'model_runtime_binding_bridge_output_too_large'));
    }
  });
  child.once('error', () => finish(
    failureReceipt(true, 'model_runtime_binding_bridge_failed')
  ));
  child.once('close', (code) => finish(parseOutput(code, stdout)));
  sendInput(child, options.repoRoot, finish);
}

function sendInput(child, repoRoot, finish) {
  try {
    child.stdin.end(JSON.stringify({ repo_root: repoRoot }));
  } catch (_err) {
    finish(failureReceipt(true, 'model_runtime_binding_bridge_input_failed'));
  }
}

function parseOutput(code, stdout) {
  if (code !== 0) {
    return failureReceipt(true, 'model_runtime_binding_bridge_failed');
  }
  try {
    const lines = String(stdout || '').trim().split(/\r?\n/);
    return validateReceipt(JSON.parse(lines[lines.length - 1]));
  } catch (_err) {
    return failureReceipt(true, 'model_runtime_binding_query_receipt_invalid');
  }
}

function validateReceipt(value) {
  if (!value || value.schema_version !== SCHEMA_VERSION) {
    return failureReceipt(true, 'model_runtime_binding_query_receipt_invalid');
  }
  const body = { ...value };
  delete body.query_receipt_id;
  if (value.query_receipt_id !== canonicalDigest(body)) {
    return failureReceipt(value.configured === true, 'model_runtime_binding_query_receipt_invalid');
  }
  if (!validNoMutationClaims(value)) {
    return failureReceipt(value.configured === true, 'model_runtime_binding_query_receipt_invalid');
  }
  if (value.configured !== true) {
    return value.status === STATUS_UNCONFIGURED && value.accepted === false
      ? value
      : failureReceipt(false, 'model_runtime_binding_query_receipt_invalid');
  }
  return value.accepted === true && validReadyReceipt(value)
    ? value
    : (value.accepted === false ? value : failureReceipt(true, 'model_runtime_binding_query_receipt_invalid'));
}

function validReadyReceipt(value) {
  const panel = Array.isArray(value.panel_models) ? value.panel_models : [];
  const roles = Array.isArray(value.role_bindings) ? value.role_bindings : [];
  const models = [value.principal_model, ...panel];
  const roleNames = roles.map((item) => String(item && item.role || ''));
  const roleModels = roles.map((item) => String(item && item.model_id || ''));
  return value.status === STATUS_READY
    && models.every((model) => MODEL_RE.test(String(model || '')))
    && new Set(models).size === models.length
    && roleNames.filter((role) => role === 'principal').length === 1
    && !roleNames.includes('verifier')
    && new Set(roleNames).size === roleNames.length
    && JSON.stringify(roleModels) === JSON.stringify(models)
    && typeof value.binding_receipt_id === 'string'
    && value.binding_receipt_id.startsWith('reddog_model_runtime_binding:');
}

function validNoMutationClaims(value) {
  return [
    'no_model_call_performed', 'no_holoindex_query_performed',
    'no_holoindex_reindex_performed', 'no_command_execution_performed',
    'no_repo_mutation_performed', 'no_runtime_artifact_mutation_performed'
  ].every((key) => value[key] === true);
}

function resolveWorker(fallback, receipt, panelLimit) {
  const base = fallback && typeof fallback === 'object' ? fallback : {};
  const value = receipt && typeof receipt === 'object'
    ? validateReceipt(receipt)
    : failureReceipt(false, 'model_runtime_binding_query_receipt_missing');
  if (value.accepted === true) {
    return {
      title: base.title || 'RedDog',
      lead: value.principal_model,
      panel: value.panel_models.slice(0, panelLimit),
      modelBindingSource: 'receipt_bound_runtime',
      modelBindingBlocked: false,
      modelBindingReceipt: value
    };
  }
  return {
    title: base.title || 'RedDog',
    lead: base.lead,
    panel: Array.isArray(base.panel) ? base.panel.slice(0, panelLimit) : [],
    modelBindingSource: value.configured === true ? 'runtime_binding_rejected' : 'evaluation_config',
    modelBindingBlocked: value.configured === true,
    modelBindingReceipt: value
  };
}

function metadata(worker) {
  const receipt = worker && worker.modelBindingReceipt || {};
  return {
    model_binding_source: worker && worker.modelBindingSource,
    model_runtime_binding_status: receipt.status,
    model_runtime_binding_receipt_id: receipt.binding_receipt_id,
    model_selection_receipt_id: receipt.selection_receipt_id,
    model_catalog_snapshot_id: receipt.catalog_snapshot_id,
    model_task_family: receipt.task_family,
    model_role_bindings: receipt.role_bindings
  };
}

function runTraceLines(reviewPacket) {
  const rp = reviewPacket && typeof reviewPacket === 'object' ? reviewPacket : {};
  return [
    '- model binding source: ' + (rp.model_binding_source || 'unknown'),
    '- model runtime binding status: ' + (rp.model_runtime_binding_status || 'unknown'),
    '- model runtime binding receipt: ' + (rp.model_runtime_binding_receipt_id || '(none)'),
    '- model selection receipt: ' + (rp.model_selection_receipt_id || '(none)'),
    '- model catalog snapshot: ' + (rp.model_catalog_snapshot_id || '(none)'),
    '- model task family: ' + (rp.model_task_family || 'unknown'),
    '- model role bindings: ' + JSON.stringify(rp.model_role_bindings || [])
  ];
}

function blockedReason(worker) {
  if (!worker || worker.modelBindingBlocked !== true) return null;
  const receipt = worker.modelBindingReceipt || {};
  return Array.isArray(receipt.rejection_reasons) && receipt.rejection_reasons.length
    ? receipt.rejection_reasons.join(', ')
    : 'model_runtime_binding_not_ready';
}

function canonicalDigest(value) {
  const canonical = JSON.stringify(sortCanonical(value));
  const ascii = canonical.replace(/[^\x00-\x7f]/g, (character) => (
    '\\u' + character.charCodeAt(0).toString(16).padStart(4, '0')
  ));
  return 'sha256:' + crypto.createHash('sha256').update(ascii, 'utf8').digest('hex');
}

function sortCanonical(value) {
  if (Array.isArray(value)) return value.map(sortCanonical);
  if (!value || typeof value !== 'object') return value;
  return Object.keys(value).sort().reduce((result, key) => {
    result[key] = sortCanonical(value[key]);
    return result;
  }, {});
}

function failureReceipt(configured, reason) {
  return {
    schema_version: SCHEMA_VERSION,
    configured: configured === true,
    accepted: false,
    status: configured === true ? 'MODEL_RUNTIME_BINDING_NOT_READY' : STATUS_UNCONFIGURED,
    rejection_reasons: [reason],
    no_model_call_performed: true,
    no_holoindex_query_performed: true,
    no_holoindex_reindex_performed: true,
    no_command_execution_performed: true,
    no_repo_mutation_performed: true,
    no_runtime_artifact_mutation_performed: true
  };
}

module.exports = {
  SCHEMA_VERSION,
  STATUS_READY,
  STATUS_UNCONFIGURED,
  blockedReason,
  canonicalDigest,
  failureReceipt,
  metadata,
  parseOutput,
  resolveWorker,
  runTraceLines,
  runConfiguredQuery,
  runQuery,
  validateReceipt
};
