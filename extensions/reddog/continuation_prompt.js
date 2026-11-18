'use strict';

function prepareContinuationPrompt(prompt, enabled, summary, actions) {
  const appended = enabled && !!summary;
  const sourceRunId = appended
    ? (summary.previous_run_id || 'unknown')
    : 'none';
  let prepared = prompt;
  if (appended) {
    prepared = actions.append(prompt, summary);
    actions.post('Continuation: appended WSP_97-safe summary from last RedDog packet (not raw Copy MD). source_run_id=' + sourceRunId);
  } else if (!enabled) {
    actions.post('Continuation: disabled for this run.');
  } else {
    actions.post('Continuation: enabled but no prior RedDog packet stored yet; nothing appended.');
  }
  return {
    prompt: prepared,
    telemetry: {
      continuation_enabled: enabled,
      continuation_appended: appended,
      continuation_source_run_id: sourceRunId
    }
  };
}

module.exports = {
  prepareContinuationPrompt
};
