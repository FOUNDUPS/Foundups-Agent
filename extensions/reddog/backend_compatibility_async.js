'use strict';

const path = require('path');
const { Worker } = require('worker_threads');

const WORKER_TIMEOUT_MS = 15000;

function failureReceipt(reason) {
  return Object.freeze({
    checked: true,
    passed: false,
    rejection_reasons: Object.freeze([reason]),
    no_holoindex_query_performed: true,
    no_model_call_performed: true,
    no_permission_probe_performed: true,
    no_work_order_emitted: true,
    no_repo_mutation_performed: true
  });
}

function startBackendCompatibilityWorker(rootValue) {
  return new Promise((resolve) => {
    const workerPath = path.join(__dirname, 'backend_compatibility_worker.js');
    const worker = new Worker(workerPath, { workerData: { root: rootValue } });
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(value);
    };
    const timer = setTimeout(() => {
      worker.terminate();
      finish(failureReceipt('backend_compatibility_worker_timeout'));
    }, WORKER_TIMEOUT_MS);
    worker.once('message', (value) => finish(
      value && typeof value === 'object'
        ? value
        : failureReceipt('backend_compatibility_worker_invalid_result')
    ));
    worker.once('error', () => finish(
      failureReceipt('backend_compatibility_worker_failed')
    ));
    worker.once('exit', (code) => {
      if (code !== 0) {
        finish(failureReceipt('backend_compatibility_worker_failed'));
      }
    });
  });
}

function runBackendCompatibilityPreflightAsync(rootValue) {
  return startBackendCompatibilityWorker(rootValue).catch(() => (
    failureReceipt('backend_compatibility_worker_failed')
  ));
}

async function detectInstallStateAsync(vscode, context, client, helpers) {
  const legacy = vscode.extensions.getExtension(client.legacyExtensionId);
  const current = vscode.extensions.getExtension(client.extensionId);
  const legacyPresent = !!legacy && legacy.id !== context.extension.id;
  const root = helpers.workspaceRoot(vscode, '');
  return {
    extension_id: context.extension.id,
    expected_extension_id: client.extensionId,
    legacy_extension_id: client.legacyExtensionId,
    version: client.extensionVersion,
    duplicate_extension_detected: legacyPresent && !!current,
    legacy_extension_present: legacyPresent,
    stale_install_detected: legacyPresent || context.extension.id !== client.extensionId,
    legacy_extension_version: legacy && legacy.packageJSON
      ? String(legacy.packageJSON.version || '')
      : '',
    backend_compatibility: await runBackendCompatibilityPreflightAsync(root)
  };
}

async function blockIncompatibleBackend(context, state, webview, actions) {
  try {
    state.installState = await actions.detect(context);
  } catch (_err) {
    state.installState = {
      backend_compatibility: failureReceipt('backend_compatibility_worker_failed')
    };
  }
  const compatibility = state.installState.backend_compatibility;
  if (compatibility && compatibility.passed === true) {
    return false;
  }
  const blockedResult = actions.build(state.installState);
  state.lastReviewPacket = blockedResult.review_packet;
  actions.post(
    webview,
    null,
    'Stopped before grounding: RedDog backend compatibility preflight failed.'
  );
  webview.postMessage({ command: 'result', result: blockedResult });
  return true;
}

module.exports = {
  blockIncompatibleBackend,
  detectInstallStateAsync,
  failureReceipt,
  runBackendCompatibilityPreflightAsync
};
