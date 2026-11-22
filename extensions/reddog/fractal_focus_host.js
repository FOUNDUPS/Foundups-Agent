'use strict';

const FOUNDUP_ID = /^[a-z0-9][a-z0-9_-]{0,79}(?![\s\S])/;
const NONE = Object.freeze({ state: 'none', foundupId: null, canAsk: false });
const UNAVAILABLE = Object.freeze({ state: 'unavailable', foundupId: null, canAsk: false });

function modelFromPreflight(preflight, canAsk) {
  const value = preflight && typeof preflight === 'object' ? preflight : {};
  if (value.passed !== true) return UNAVAILABLE;
  if (value.foundup_work_grounding_applied !== true) return NONE;
  const receipt = value.typed_targets && value.typed_targets.foundup_work_grounding;
  const foundupId = typeof value.foundup_id === 'string' ? value.foundup_id : '';
  const receiptId = receipt && receipt.receipt_id;
  const accepted = value.foundup_work_grounding_passed === true
    && value.foundup_use_time_verified === true && receipt && receipt.applied === true
    && receipt.passed === true && FOUNDUP_ID.test(foundupId) && receipt.foundup_id === foundupId
    && typeof receiptId === 'string' && receiptId.length > 0
    && receiptId === value.foundup_work_grounding_receipt_id;
  return accepted
    ? { state: 'selected', foundupId, canAsk: canAsk === true }
    : UNAVAILABLE;
}

function post(webview, state, model) {
  const epoch = Number.isSafeInteger(state.fractalFocusEpoch) ? state.fractalFocusEpoch + 1 : 1;
  state.fractalFocusEpoch = epoch;
  const actionable = model && model.state === 'selected' && model.canAsk === true
    && typeof model.foundupId === 'string' && FOUNDUP_ID.test(model.foundupId);
  state.fractalFocusBinding = actionable ? { foundupId: model.foundupId, epoch } : null;
  return webview.postMessage({ command: 'fractalFocus', model, epoch });
}

function postPreflight(webview, state, preflight) {
  return post(webview, state, modelFromPreflight(preflight, false));
}

function postOutcome(webview, state, preflight, result) {
  const model = result && result.ok === true
    ? modelFromPreflight(preflight, true) : UNAVAILABLE;
  return post(webview, state, model);
}

function handleAsk(webview, state, message) {
  const binding = state.fractalFocusBinding;
  if (state.requestInFlight || !binding || message.foundupId !== binding.foundupId
    || message.epoch !== binding.epoch) return false;
  webview.postMessage({ command: 'fractalFocusPrefill', epoch: binding.epoch,
    question: 'What should I know about the ' + binding.foundupId + ' FoundUp?' });
  return true;
}

function bindPanel(container, composer, render, postMessage, isRunning) {
  let epoch = 0;
  let actionable = false;
  function draw(model, nextEpoch) {
    if (!Number.isSafeInteger(nextEpoch) || nextEpoch <= epoch) return false;
    epoch = nextEpoch;
    actionable = !!model && model.state === 'selected' && model.canAsk === true;
    render(container, model, (foundupId) => {
      postMessage({ command: 'fractalFocusAsk', foundupId, epoch });
    });
    return true;
  }
  render(container, { state: 'none', foundupId: null, canAsk: false }, () => {});
  return (message) => {
    if (message.command === 'fractalFocus') {
      return draw(message.model, message.epoch);
    }
    if (message.command !== 'fractalFocusPrefill' || !actionable || isRunning()
      || message.epoch !== epoch || composer.value !== ''
      || typeof message.question !== 'string') return false;
    composer.value = message.question;
    composer.focus();
    return true;
  };
}

async function handleClipboardMessage(deps, webview, state, message) {
  if (message.command === 'copyReview') {
    if (state.lastReviewPacket) {
      await deps.clipboard.writeText(JSON.stringify(state.lastReviewPacket, null, 2));
      webview.postMessage({ command: 'status', text: 'Copied redacted review packet for 0102.' });
    } else webview.postMessage({ command: 'status', text: 'No review packet available yet.' });
    return true;
  }
  if (message.command !== 'copyMarkdown' || typeof message.text !== 'string') return false;
  await deps.clipboard.writeText(message.text);
  webview.postMessage({ command: 'status', text: 'Copied assistant markdown.' });
  return true;
}

function createMessageReceiver(deps, webview, state, executeAsk) {
  return async (message) => {
    if (!message || typeof message !== 'object') return;
    if (message.command === 'fractalFocusAsk') return handleAsk(webview, state, message);
    if (await handleClipboardMessage(deps, webview, state, message)) return;
    if (message.command !== 'ask' || typeof message.text !== 'string') return;
    if (state.requestInFlight) {
      deps.postStatusAndProgress(webview, null, 'RedDog is already processing one request.');
      return;
    }
    state.requestInFlight = true;
    post(webview, state, NONE);
    try {
      const result = await executeAsk(message, null);
      if (!result || result.ok !== true) post(webview, state, UNAVAILABLE);
    } catch (err) {
      post(webview, state, UNAVAILABLE);
      throw err;
    } finally { state.requestInFlight = false; }
  };
}

function bindReceiverLifecycle(deps, params) {
  const attempt = () => deps.attemptBlockedRequestRecovery(params);
  params.webview.onDidReceiveMessage(createMessageReceiver(
    deps, params.webview, params.state, params.executeAsk
  ));
  deps.startBlockedRecoveryPolling(params.state, attempt);
  return attempt;
}

module.exports = Object.freeze({
  NONE, UNAVAILABLE, bindPanel, bindReceiverLifecycle, createMessageReceiver,
  handleAsk, modelFromPreflight, post, postOutcome, postPreflight
});
