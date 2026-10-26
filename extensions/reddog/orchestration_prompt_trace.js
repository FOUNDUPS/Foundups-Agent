'use strict';

const crypto = require('crypto');

const SCHEMA_VERSION = 'reddog_orchestration_prompt_trace.v1';
const MAX_DISPLAY_CHARS = 12000;
const METADATA_DIGEST_KEY = crypto.randomBytes(32);

function digest(text) {
  return 'sha256:' + crypto.createHash('sha256').update(String(text || ''), 'utf8').digest('hex');
}

function metadataDigest(text) {
  const raw = String(text || '');
  return {
    hash: crypto.createHmac('sha256', METADATA_DIGEST_KEY)
      .update(raw, 'utf8').digest('hex').slice(0, 16),
    length: raw.length
  };
}

function bounded(text) {
  const source = String(text || '');
  if (source.length <= MAX_DISPLAY_CHARS) return { text: source, truncated: false };
  return { text: source.slice(0, MAX_DISPLAY_CHARS), truncated: true };
}

function fenced(text) {
  const source = String(text || '');
  let longest = 0;
  for (const match of source.matchAll(/`+/g)) longest = Math.max(longest, match[0].length);
  const marker = '`'.repeat(Math.max(3, longest + 1));
  return marker + 'text\n' + source + '\n' + marker;
}

function buildPromptConstructionMetadata(workFocus, taskPrompt, diagnostic, contextPacket) {
  const packet = contextPacket && typeof contextPacket === 'object' ? contextPacket : {};
  return {
    work_focus_digest: metadataDigest(workFocus),
    daemon_diagnostic_payload_digest: diagnostic && diagnostic.payload_digest,
    daemon_diagnostic_projection_digest: diagnostic && diagnostic.projection_digest,
    daemon_diagnostic_line_count: diagnostic && diagnostic.line_count,
    daemon_diagnostic_signal_count: diagnostic && diagnostic.signal_count,
    daemon_diagnostic_secret_redactions_applied: diagnostic && diagnostic.secret_redactions_applied,
    wsp_prompt_digest: metadataDigest(taskPrompt),
    audit_context_requested: packet.audit_context === true,
    required_targets_authoritative_paths: Array.isArray(packet.required_targets_authoritative_paths)
      ? packet.required_targets_authoritative_paths.slice() : []
  };
}

function buildTrace(input) {
  const source = input && typeof input === 'object' ? input : {};
  return Object.freeze({
    schema_version: SCHEMA_VERSION,
    display_scope: 'local_policy_projection',
    authority: 'display_only_not_execution_authority',
    self: '0102',
    role: String(source.worker || 'reddog_architect'),
    origin: 'external_principal',
    execution_plane: String(source.executionPlane || 'dialogue_and_no_effect_audit'),
    route: String(source.route || 'unknown'),
    reasoning_tier: String(source.reasoningTier || 'HIGH'),
    context_mode: String(source.contextMode || 'unknown'),
    model_call_expected: source.modelCallExpected !== false,
    wsp00_status: 'prompt_contract_declared_runtime_attestation_separate',
    wsp15_allocation_status: 'not_issued_at_prompt_stage',
    task_prompt_digest: null,
    exact_redacted_task_prompt: '',
    exact_redacted_task_prompt_digest: null,
    task_prompt_truncated: false,
    outbound_confirmation: 'pending_authoritative_redaction_gate'
  });
}

function safeDisplayCandidate(candidate, suppliedDigest, integrityMismatch, displaySanitizer) {
  const sanitizer = typeof displaySanitizer === 'function' ? displaySanitizer : (value) => value;
  let displayCandidate = '';
  let localRedactionFailed = false;
  if (candidate && suppliedDigest && !integrityMismatch) {
    try {
      displayCandidate = String(sanitizer(candidate));
    } catch (error) {
      localRedactionFailed = true;
    }
  }
  const localRedactionMismatch = Boolean(candidate && !localRedactionFailed
    && displayCandidate !== candidate);
  return { localRedactionFailed, localRedactionMismatch, prompt: localRedactionMismatch ? '' : displayCandidate };
}

function confirmOutbound(trace, result, displaySanitizer) {
  const packet = result && typeof result === 'object' ? result : {};
  const candidate = packet.ok === true && typeof packet.redacted_task_prompt === 'string'
    ? packet.redacted_task_prompt : '';
  const suppliedDigest = /^sha256:[a-f0-9]{64}$/.test(String(packet.redacted_task_prompt_digest || ''))
    ? String(packet.redacted_task_prompt_digest) : null;
  const integrityMismatch = Boolean(candidate && suppliedDigest && digest(candidate) !== suppliedDigest);
  const local = safeDisplayCandidate(candidate, suppliedDigest, integrityMismatch, displaySanitizer);
  const prompt = local.prompt;
  const displayed = bounded(prompt);
  return Object.freeze(Object.assign({}, trace || {}, {
    outbound_confirmation: integrityMismatch
      ? 'redacted_task_prompt_integrity_mismatch'
      : local.localRedactionFailed
      ? 'local_copy_redaction_failed'
      : local.localRedactionMismatch
      ? 'local_copy_redaction_changed_prompt'
      : prompt
      ? (displayed.truncated ? 'bounded_exact_redacted_task_prompt_display' : 'exact_redacted_task_prompt')
      : (suppliedDigest ? 'digest_only_after_unsuccessful_call' : 'unavailable'),
    exact_redacted_task_prompt: displayed.text,
    exact_redacted_task_prompt_digest: prompt ? digest(prompt) : suppliedDigest,
    task_prompt_digest: prompt ? digest(prompt) : null,
    task_prompt_truncated: displayed.truncated
  }));
}

function beginTrace(webview, input, promptConstruction) {
  const trace = buildTrace(input);
  promptConstruction.orchestration_prompt_trace_schema = trace.schema_version;
  webview.postMessage({ command: 'orchestrationPrompt', text: markdownSection(trace) });
  return trace;
}

function finishTrace(webview, result, pendingTrace, displaySanitizer) {
  const trace = confirmOutbound(pendingTrace, result, displaySanitizer);
  result.orchestration_prompt_trace = trace;
  webview.postMessage({ command: 'orchestrationPrompt', text: markdownSection(trace) });
  return trace;
}

function markdownSection(trace) {
  const value = trace && typeof trace === 'object' ? trace : {};
  return traceLines(value).concat(promptDisclosureLines(value)).join('\n');
}

function traceLines(value) {
  return [
    '## Orchestration Prompt Trace',
    '- schema_version: ' + (value.schema_version || SCHEMA_VERSION),
    '- display_scope: ' + (value.display_scope || 'unknown'),
    '- authority: ' + (value.authority || 'unknown'),
    '- self: ' + (value.self || 'unknown'),
    '- role: ' + (value.role || 'unknown'),
    '- origin: ' + (value.origin || 'unknown'),
    '- execution_plane: ' + (value.execution_plane || 'unknown'),
    '- route: ' + (value.route || 'unknown'),
    '- reasoning_tier: ' + (value.reasoning_tier || 'unknown'),
    '- context_mode: ' + (value.context_mode || 'unknown'),
    '- model_call_expected: ' + (value.model_call_expected === true ? 'true' : 'false'),
    '- wsp00_status: ' + (value.wsp00_status || 'unknown'),
    '- wsp15_allocation_status: ' + (value.wsp15_allocation_status || 'unknown'),
    '- task_prompt_digest: ' + (value.task_prompt_digest || 'unknown'),
    '- outbound_confirmation: ' + (value.outbound_confirmation || 'unknown'),
    '- exact_redacted_task_prompt_digest: ' + (value.exact_redacted_task_prompt_digest || 'unknown')
  ];
}

function promptDisclosureLines(value) {
  if (value.model_call_expected === false) {
    return ['', 'No model call was made for this route; no task prompt body exists.'];
  }
  if (value.exact_redacted_task_prompt) {
    return [
      '',
      '### Exact redacted task prompt admitted by the bridge',
      fenced(value.exact_redacted_task_prompt),
      value.task_prompt_truncated ? '- display_truncated: true' : '- display_truncated: false'
    ];
  }
  if (value.outbound_confirmation === 'digest_only_after_unsuccessful_call') {
    return ['', 'The provider call did not succeed. Only the gate-redacted task prompt digest is shown.'];
  }
  if (value.outbound_confirmation === 'redacted_task_prompt_integrity_mismatch') {
    return ['', 'The bridge task prompt body and digest disagree. The body is withheld.'];
  }
  if (value.outbound_confirmation === 'local_copy_redaction_changed_prompt') {
    return ['', 'The bridge-admitted prompt required additional local redaction. The body is withheld.'];
  }
  if (value.outbound_confirmation === 'local_copy_redaction_failed') {
    return ['', 'The local disclosure sanitizer failed. The body is withheld.'];
  }
  return ['', 'The task prompt body is withheld until the authoritative redaction gate confirms it.'];
}

module.exports = {
  SCHEMA_VERSION, beginTrace, buildPromptConstructionMetadata, buildTrace,
  confirmOutbound, digest, fenced, finishTrace, markdownSection, metadataDigest
};
