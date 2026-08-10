'use strict';

let dependencies = null;

function create(input) {
  dependencies = input && typeof input === 'object' ? input : null;
  return {
    beginGroundingFailurePromptTrace, beginNoModelPromptTrace, buildBasePromptTraceInput,
    beginBasePromptTrace, outputValidationOptions, statusMessages
  };
}

function statusMessages(auditDegraded, localStatus, draftStatus, conversationalDraft) {
  if (auditDegraded) return {
    route: 'Backend compatibility is degraded. A local audit receipt will be returned; no model or network call will be made.',
    assembly: '0102 prepared a local compatibility receipt; the WSP task prompt was not sent to a bridge or model.'
  };
  return {
    route: localStatus || (conversationalDraft ? draftStatus : ''),
    assembly: conversationalDraft
      ? '0102 isolated the supplied message as untrusted drafting data.'
      : '0102 assembled WSP task prompt from 012 work focus (bridge receives WSP task prompt, not raw focus alone).'
  };
}

function beginGroundingFailurePromptTrace(
  webview, baseInput, promptConstruction, stage, workFocus, preflight, scorecard
) {
  if (stage && stage.ok === true) {
    return beginNoModelPromptTrace(webview, promptConstruction,
      'holoindex_recovery_queue_no_model', 'holoindex_recovery_receipt');
  }
  const request = dependencies.groundingFailureDialogue.buildRequest(workFocus, preflight, scorecard);
  dependencies.postStatusAndProgress(webview, null,
    'Orchestration route changed to grounding-failure dialogue: role=RedDog Architect mode=openrouter_single.');
  return dependencies.orchestrationPromptTrace.beginTrace(webview, {
    systemPrompt: request.systemPrompt, taskPrompt: request.prompt,
    route: request.mode, worker: 'reddog_architect', reasoningTier: 'REGULAR',
    contextMode: 'grounding_failure_receipt', executionPlane: 'dialogue_and_no_effect_audit'
  }, promptConstruction);
}

function beginNoModelPromptTrace(webview, promptConstruction, route, contextMode) {
  return dependencies.orchestrationPromptTrace.beginTrace(webview, {
    systemPrompt: '', taskPrompt: '', route, worker: 'none', reasoningTier: 'NOT_APPLICABLE',
    contextMode, executionPlane: 'dialogue_and_no_effect_audit', modelCallExpected: false
  }, promptConstruction);
}

function buildBasePromptTraceInput(systemPrompt, taskPrompt, route, worker, tier, contextMode, action) {
  return {
    systemPrompt, taskPrompt, route, worker, reasoningTier: tier, contextMode,
    executionPlane: action ? 'governed_execution_candidate' : 'dialogue_and_no_effect_audit'
  };
}

function beginBasePromptTrace(webview, input, promptConstruction, route) {
  return dependencies.orchestrationPromptTrace.beginTrace(
    webview, route ? Object.assign({}, input, { route }) : input, promptConstruction
  );
}

function outputValidationOptions(workerType, mode, promptAuthoringRequired) {
  return { substantiveArchitect: true, mode, workerType, promptAuthoringRequired };
}

module.exports = { create };
