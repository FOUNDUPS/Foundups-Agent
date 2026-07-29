'use strict';

const protocol = require('./start_operations_control');
const bridge = require('./start_operations_bridge');
const modelRuntimeBindingQuery = require('./model_runtime_binding_query');

async function execute(options) {
  const opts = options && typeof options === 'object' ? options : {};
  const command = opts.command;
  const bindingReason = protocol.bindingRejection(command, opts.worker);
  if (bindingReason) {
    return packet(protocol.failureResult(command.action, bindingReason), opts.worker);
  }
  const intentId = command.action === 'submit' ? '' : String(opts.intentId || '');
  if (!intentId && command.action !== 'submit') {
    return packet(
      protocol.failureResult(command.action, 'start_operations_intent_not_available'),
      opts.worker
    );
  }
  const request = protocol.buildRequest(command, intentId, opts.repoRoot);
  const result = await bridge.run({
    interpreter: opts.interpreter,
    script: opts.script,
    repoRoot: opts.repoRoot,
    env: opts.env,
    request,
    onProgress: opts.onProgress
  });
  return packet(result, opts.worker);
}

async function executeMessage(options) {
  const opts = options && typeof options === 'object' ? options : {};
  const command = protocol.classify(opts.text);
  if (!command) return null;
  if (typeof opts.onRequested === 'function') opts.onRequested(command);
  const outcome = await execute({ ...opts, command });
  return { command, ...outcome };
}

async function handleMessage(options) {
  const opts = options && typeof options === 'object' ? options : {};
  const outcome = await executeMessage({
    ...opts,
    intentId: opts.state && opts.state.operationsIntentId,
    onRequested: (command) => opts.postStatus(
      'RedDog operations control: ' + command.action + ' requested.'
    ),
    onProgress: (progress) => {
      persistIntent(opts, progress.intent_id);
      opts.postStatus('Resident cycle submitted: ' + progress.intent_id);
    }
  });
  if (!outcome) return false;
  if (outcome.result.intent_id) {
    persistIntent(opts, outcome.result.intent_id);
  }
  opts.postResult(outcome.packet);
  return true;
}

function persistIntent(options, intentId) {
  const value = String(intentId || '');
  if (!value) return;
  if (options.state) options.state.operationsIntentId = value;
  if (typeof options.persistIntentId !== 'function') return;
  Promise.resolve(options.persistIntentId(value)).catch(() => {});
}

function packet(result, worker) {
  const value = {
    ok: result.accepted === true,
    reason: result.accepted === true
      ? 'operations_control_completed'
      : 'operations_control_rejected',
    content: protocol.render(result),
    review_packet: Object.assign(
      { start_operations_control_result: result },
      modelRuntimeBindingQuery.metadata(worker)
    )
  };
  value.copy_markdown = value.content;
  return { result, packet: value };
}

module.exports = {
  classify: protocol.classify,
  execute,
  executeMessage,
  handleMessage
};
