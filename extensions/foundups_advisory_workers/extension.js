const vscode = require('vscode');
const cp = require('child_process');
const crypto = require('crypto');
const path = require('path');
const fs = require('fs');

const EXTENSION_VERSION = '0.3.21';
const REDDOG_TERMINAL_HOLD_MS = 3000;
const REDACTION_BLOCK_OPERATOR_MESSAGE = 'Stopped before OpenRouter. Nothing left the machine.';
const BRIDGE_MAX_STDOUT_BYTES = 262144;
const BRIDGE_MAX_STDERR_BYTES = 65536;
const BRIDGE_MAX_CONTEXT_CHARS = 48000;
const BRIDGE_MAX_PROMPT_CHARS = 12000;
const MOJIBAKE_MARKERS = ['\u7aa6', '\u7aaa'];
const WORK_TRAIL_MAX_EVENTS = 50;
const VALIDATION_FAILED_FOOTER = [
  '## Verification Gaps',
  'Output failed local contract validation.',
  '',
  '## Next safest step',
  'Re-run with narrower context or hand packet to 0102 for review.'
].join('\n');

const WORK_TRAIL_ALLOWLIST = new Set([
  'orchestrator_started',
  'repo_context_attached',
  'holoindex_result',
  'wsp_prompt_assembled',
  'redaction_gate_started',
  'redaction_gate_passed',
  'redaction_gate_blocked',
  'lead_started',
  'panel_started',
  'synthesis_started',
  'validator_started',
  'repair_started',
  'repair_blocked',
  'repair_complete',
  'completed',
  'failed'
]);

const BRIDGE_STAGE_WORK_TRAIL = {
  bridge_start: 'orchestrator_started',
  env_check: 'orchestrator_started',
  redaction_start: 'redaction_gate_started',
  redaction_blocked: 'redaction_gate_blocked',
  redaction_pass: 'redaction_gate_passed',
  lead_start: 'lead_started',
  lead_done: 'lead_started',
  panel_start: 'panel_started',
  panel_done: 'panel_started',
  panel_blocked: 'panel_started',
  synthesis_start: 'synthesis_started',
  synthesis_done: 'synthesis_started',
  single_start: 'lead_started',
  single_done: 'lead_started',
  fusion_alias_start: 'panel_started',
  fusion_alias_done: 'panel_started'
};

const ADVISORY_BRIDGE_STAGES = [
  'bridge_start',
  'env_check',
  'redaction_start',
  'redaction_blocked',
  'redaction_pass',
  'fusion_alias_start',
  'fusion_alias_done',
  'lead_start',
  'lead_done',
  'panel_start',
  'panel_done',
  'panel_blocked',
  'synthesis_start',
  'synthesis_done',
  'single_start',
  'single_done'
];

const REDDOG_STAGE_ACTIONS = {
  bridge_start: { action: 'sorting', pixel: '<rd>' },
  env_check: { action: 'nosing', pixel: '<rd>' },
  redaction_start: { action: 'nosing', pixel: '<rd>' },
  redaction_blocked: { action: 'barking', pixel: '!rd!' },
  redaction_pass: { action: 'nosing', pixel: '<rd>' },
  fusion_alias_start: { action: 'fetching', pixel: '<rd>' },
  fusion_alias_done: { action: 'crystallizing', pixel: '<rd>' },
  lead_start: { action: 'fetching', pixel: '<rd>' },
  lead_done: { action: 'herding', pixel: '<rd>' },
  panel_start: { action: 'herding', pixel: '<rd>' },
  panel_done: { action: 'herding', pixel: '<rd>' },
  panel_blocked: { action: 'sitting', pixel: '.rd.' },
  synthesis_start: { action: 'crystallizing', pixel: '<rd>' },
  synthesis_done: { action: 'pointing', pixel: '>rd>' },
  single_start: { action: 'fetching', pixel: '<rd>' },
  single_done: { action: 'pointing', pixel: '>rd>' }
};

const REDDOG_PROGRESS_ACTIONS = [
  { prefix: 'Work focus sent.', action: 'sniffing', pixel: '.rd.' },
  { prefix: 'Mode: ', action: 'sorting', pixel: '<rd>' },
  { prefix: 'Bridge process starting', action: 'sorting', pixel: '<rd>' },
  { prefix: 'Workspace root: ', action: 'sorting', pixel: '<rd>' },
  { prefix: 'Bridge script: ', action: 'sorting', pixel: '<rd>' },
  { prefix: 'OpenRouter key visible to Cursor process: ', action: 'sorting', pixel: '<rd>' },
  { prefix: 'Context budget applied: ', action: 'tracking', pixel: '<rd>' },
  { prefix: 'Python interpreter: ', action: 'sorting', pixel: '<rd>' },
  { prefix: 'Orchestrator: effort=', action: 'sorting', pixel: '<rd>' },
  { prefix: 'Bridge started. Redaction gate runs', action: 'nosing', pixel: '<rd>' },
  { prefix: 'Repo context attached: ', action: 'tracking', pixel: '<rd>' },
  { prefix: 'Repo context: WSP operating contract only.', action: 'tracking', pixel: '<rd>' },
  { prefix: '0102 assembled WSP task prompt', action: 'sniffing', pixel: '.rd.' },
  { prefix: 'Output schema incomplete. Missing: ', action: 'digging', pixel: '<rd>' }
];

function formatElapsed(ms) {
  const s = Math.floor(Math.max(0, ms) / 1000);
  if (s < 60) {
    return s + 's';
  }
  return Math.floor(s / 60) + 'm' + String(s % 60).padStart(2, '0') + 's';
}

function matchReddogProgress(input) {
  const stage = input && input.stage ? String(input.stage) : '';
  const text = input && input.text ? String(input.text) : '';
  if (stage && Object.prototype.hasOwnProperty.call(REDDOG_STAGE_ACTIONS, stage)) {
    return Object.assign({}, REDDOG_STAGE_ACTIONS[stage]);
  }
  for (const rule of REDDOG_PROGRESS_ACTIONS) {
    if (rule.prefix && text.startsWith(rule.prefix)) {
      return { action: rule.action, pixel: rule.pixel };
    }
  }
  return null;
}

function postStatusMessage(webview, text) {
  webview.postMessage({ command: 'status', text: text });
}

function postProgressMessage(webview, stage, text) {
  webview.postMessage({
    command: 'progress',
    stage: stage || null,
    text: text || ''
  });
}

function postStatusAndProgress(webview, stage, text) {
  if (text) {
    postStatusMessage(webview, text);
  }
  postProgressMessage(webview, stage, text);
}

function enrichRedactionBlockResult(result) {
  if (!result || result.reason !== 'redaction_blocked') {
    return result;
  }
  const packet = result.review_packet && typeof result.review_packet === 'object'
    ? Object.assign({}, result.review_packet)
    : {};
  packet.made_network_call = false;
  packet.retry_count = 0;
  packet.reason = 'redaction_blocked';
  return Object.assign({}, result, { review_packet: packet, retry_count: 0 });
}

function detectMojibake(text) {
  const src = String(text || '');
  const markers = MOJIBAKE_MARKERS.filter((marker) => src.includes(marker));
  return { detected: markers.length > 0, markers: markers };
}

function formatOutputValidationStatus(validationState) {
  const vs = validationState && typeof validationState === 'object' ? validationState : {};
  if (vs.output_validation_failed || (vs.repair_attempted && !vs.validated)) {
    return 'failed';
  }
  if (vs.validated === true) {
    return 'passed';
  }
  if (vs.skipped) {
    return 'skipped';
  }
  return 'unknown';
}

function buildValidationFailedSection(validationState) {
  const vs = validationState && typeof validationState === 'object' ? validationState : {};
  const missing = vs.missing_sections_after_repair || vs.missing_sections || [];
  const lines = [
    '## OUTPUT_VALIDATION_FAILED',
    '- missing sections: ' + (missing.length ? missing.join(', ') : '(none listed)'),
    '- repair_failure_reason: ' + (vs.repair_failure_reason || vs.reason || 'schema_incomplete'),
    '- note: Output is advisory and incomplete.'
  ];
  return lines.join('\n');
}

function sanitizeCopyMdText(text) {
  let s = String(text || '');
  const keyPresent = (_m, yn) => (String(yn).toLowerCase() === 'yes' ? 'true' : 'false');
  s = s.replace(/OPENROUTER_API_KEY visible to bridge:\s*(yes|no)/gi, (_m, yn) => `key_env_present: ${keyPresent(_m, yn)}`);
  s = s.replace(/OpenRouter key visible to Cursor process:\s*(yes|no)/gi, (_m, yn) => `key_env_present: ${keyPresent(_m, yn)}`);
  s = s.replace(/Bearer\s+[A-Za-z0-9._-]+/gi, 'Bearer [REDACTED]');
  s = s.replace(/\bsk-[A-Za-z0-9]+\b/gi, 'sk-[REDACTED]');
  return s;
}

function createWorkTrail() {
  const events = [];
  return {
    push(name, detail) {
      if (!WORK_TRAIL_ALLOWLIST.has(name)) {
        return;
      }
      const entry = { event: name };
      if (detail) {
        entry.detail = sanitizeCopyMdText(String(detail)).slice(0, 240);
      }
      const last = events[events.length - 1];
      if (last && last.event === name) {
        const lastDetail = last.detail || '';
        const newDetail = entry.detail || '';
        if (!newDetail && lastDetail) {
          return;
        }
        if (newDetail && !lastDetail) {
          last.detail = newDetail;
          return;
        }
        if (newDetail && lastDetail && newDetail === lastDetail) {
          return;
        }
      }
      events.push(entry);
      while (events.length > WORK_TRAIL_MAX_EVENTS) {
        events.shift();
      }
    },
    toEvents() {
      return events.slice();
    },
    count() {
      return events.length;
    }
  };
}

function normalizeBridgeStageToWorkTrail(stage, text) {
  const stageName = stage ? String(stage) : '';
  if (stageName && BRIDGE_STAGE_WORK_TRAIL[stageName]) {
    return { event: BRIDGE_STAGE_WORK_TRAIL[stageName], detail: sanitizeCopyMdText(text) };
  }
  const sanitized = sanitizeCopyMdText(text || '');
  if (/Output schema incomplete/.test(sanitized)) {
    return { event: 'validator_started', detail: 'schema_check' };
  }
  if (/Running one repair pass/.test(sanitized)) {
    return { event: 'repair_started', detail: 'repair_pass' };
  }
  return null;
}

function buildWorkTrailSection(workTrail) {
  const events = workTrail && typeof workTrail.toEvents === 'function'
    ? workTrail.toEvents()
    : Array.isArray(workTrail) ? workTrail : [];
  const capped = events.slice(-WORK_TRAIL_MAX_EVENTS);
  const lines = ['## Work Trail'];
  for (const entry of capped) {
    const label = entry && entry.event ? entry.event : 'unknown';
    lines.push('- ' + label + (entry.detail ? ': ' + entry.detail : ''));
  }
  if (!capped.length) {
    lines.push('- (no normalized trail events recorded)');
  }
  return lines.join('\n');
}

function resolveProviderReasoningReport(resolvedEffort) {
  const effort = String(resolvedEffort || 'high').toLowerCase();
  const requestedMap = { regular: 'none', high: 'medium', ultra: 'high' };
  return {
    provider_reasoning_requested: requestedMap[effort] || 'medium',
    provider_reasoning_applied: 'unknown',
    provider_reasoning_note: 'Report-only in v0.3.20; bridge does not confirm provider reasoning application.'
  };
}

function extractHoloIndexScorecard(contextMode, holoMeta) {
  if (!contextMode || !String(contextMode).includes('holo')) {
    return null;
  }
  const meta = holoMeta && typeof holoMeta === 'object' ? holoMeta : {};
  return {
    holoindex_status: meta.holoindex_status || 'unknown',
    wsp_hits: meta.wsp_hits !== undefined ? meta.wsp_hits : 'unknown',
    code_hits: meta.code_hits !== undefined ? meta.code_hits : 'unknown',
    skill_hits: meta.skill_hits !== undefined ? meta.skill_hits : 'unknown',
    index_gap_detected: meta.index_gap_detected !== undefined ? meta.index_gap_detected : 'unknown',
    direct_read_fallback_used: meta.direct_read_fallback_used !== undefined ? meta.direct_read_fallback_used : 'unknown'
  };
}

function formatHoloIndexScorecardLines(scorecard) {
  if (!scorecard) {
    return [];
  }
  return [
    '- holoindex_status: ' + scorecard.holoindex_status,
    '- wsp_hits: ' + scorecard.wsp_hits,
    '- code_hits: ' + scorecard.code_hits,
    '- skill_hits: ' + scorecard.skill_hits,
    '- index_gap_detected: ' + scorecard.index_gap_detected,
    '- direct_read_fallback_used: ' + scorecard.direct_read_fallback_used
  ];
}

function buildRunTraceSection(result, workerType, contextSummary, holoScorecard, resolvedEffort) {
  const rp = result && result.review_packet && typeof result.review_packet === 'object' ? result.review_packet : {};
  const cls = rp.task_classification && typeof rp.task_classification === 'object' ? rp.task_classification : {};
  const workerLabel = WORKER_TYPES[cleanWorkerType(workerType)] ? WORKER_TYPES[cleanWorkerType(workerType)].label : String(workerType || 'unknown');
  const panelModels = Array.isArray(rp.panel_models) ? rp.panel_models.join(' + ') : 'unknown';
  const providerReport = resolveProviderReasoningReport(rp.resolved_effort || resolvedEffort);
  const reddogEffort = String(rp.resolved_effort || resolvedEffort || 'unknown').toLowerCase();
  const lines = [
    '## Run Trace',
    '- 0102 role: ' + workerLabel,
    '- WSP_15 tier: ' + (cls.tier || 'unknown'),
    '- reddog_effort: ' + reddogEffort,
    '- effort: ' + (rp.resolved_effort || resolvedEffort || 'unknown'),
    '- provider_reasoning_requested: ' + providerReport.provider_reasoning_requested,
    '- provider_reasoning_applied: ' + providerReport.provider_reasoning_applied,
    '- provider_reasoning_note: ' + providerReport.provider_reasoning_note,
    '- mode: ' + (rp.resolved_mode || result.mode || 'unknown'),
    '- mode selection reason: ' + (rp.mode_selection_reasoning || 'unknown'),
    '- principal model: ' + (rp.principal_model || result.lead_model || 'unknown'),
    '- panel models: ' + panelModels,
    '- context mode: ' + (rp.resolved_context || 'unknown')
  ];
  if (contextSummary) {
    lines.push('- HoloIndex/context summary: ' + sanitizeCopyMdText(String(contextSummary)).slice(0, 500));
  }
  lines.push.apply(lines, formatHoloIndexScorecardLines(holoScorecard || rp.holoindex_scorecard));
  if (result && result.reason === 'redaction_blocked') {
    lines.push('- redaction gate status: BLOCKED_LOCALLY');
    lines.push('- made_network_call: false');
    lines.push('- operator message: ' + REDACTION_BLOCK_OPERATOR_MESSAGE);
  } else {
    lines.push('- redaction gate status: passed');
    lines.push('- made_network_call: ' + (rp.made_network_call === true ? 'true' : rp.made_network_call === false ? 'false' : 'unknown'));
    if (rp.retry_count !== undefined && rp.retry_count !== null) {
      lines.push('- retry_count: ' + rp.retry_count);
    }
  }
  lines.push('- output_validation: ' + formatOutputValidationStatus(rp.output_validation));
  return lines.join('\n');
}

function compositePayloadDigest(promptConstruction) {
  if (!promptConstruction || typeof promptConstruction !== 'object') {
    return undefined;
  }
  const parts = [];
  if (promptConstruction.work_focus_digest && promptConstruction.work_focus_digest.hash) {
    parts.push('work_focus:' + promptConstruction.work_focus_digest.hash);
  }
  if (promptConstruction.wsp_prompt_digest && promptConstruction.wsp_prompt_digest.hash) {
    parts.push('wsp_prompt:' + promptConstruction.wsp_prompt_digest.hash);
  }
  if (!parts.length) {
    return undefined;
  }
  return 'sha256:' + crypto.createHash('sha256').update(parts.join('|'), 'utf8').digest('hex');
}

function inferNextSafeContext(contextMode) {
  const mode = String(contextMode || 'none');
  if (mode === 'none') {
    return 'wsp_only';
  }
  if (mode.includes('git')) {
    return 'narrowed_diff';
  }
  return 'local_0102_review';
}

function buildRedactionGateReport(result, promptConstruction, contextMode) {
  const observedReason = typeof result.redaction_reason === 'string' && result.redaction_reason.length > 0;
  const ruleClasses = observedReason ? [String(result.redaction_reason)] : ['unknown'];
  const ruleCounts = observedReason ? { [String(result.redaction_reason)]: 1 } : { unknown: 'unknown' };
  const digest = compositePayloadDigest(promptConstruction);
  return {
    decision: 'BLOCKED_LOCALLY',
    made_network_call: false,
    blocked_stage: 'pre_openrouter_request',
    blocked_payload_part: 'unknown',
    rule_classes: ruleClasses,
    rule_counts: ruleCounts,
    raw_snippets_included: false,
    redacted_payload_digest: digest || 'unknown',
    safe_summary: 'Redaction gate blocked egress before OpenRouter. No raw blocked content is included in this packet.',
    next_safe_context: inferNextSafeContext(contextMode),
    truth_labels: {
      decision: 'OBSERVED',
      made_network_call: 'OBSERVED',
      blocked_stage: 'OBSERVED',
      blocked_payload_part: 'UNKNOWN',
      rule_classes: observedReason ? 'OBSERVED' : 'UNKNOWN',
      rule_counts: observedReason ? 'OBSERVED' : 'UNKNOWN',
      raw_snippets_included: 'OBSERVED',
      redacted_payload_digest: digest ? 'OBSERVED' : 'UNKNOWN',
      safe_summary: 'OBSERVED',
      next_safe_context: 'INFERRED'
    }
  };
}

function buildRedactionGateReportSection(report) {
  const r = report && typeof report === 'object' ? report : {};
  const labels = r.truth_labels && typeof r.truth_labels === 'object' ? r.truth_labels : {};
  const lines = ['## Redaction Gate Report'];
  const entries = [
    ['decision', r.decision],
    ['made_network_call', r.made_network_call],
    ['blocked_stage', r.blocked_stage],
    ['blocked_payload_part', r.blocked_payload_part],
    ['rule_classes', JSON.stringify(r.rule_classes || ['unknown'])],
    ['rule_counts', JSON.stringify(r.rule_counts || { unknown: 'unknown' })],
    ['raw_snippets_included', r.raw_snippets_included],
    ['redacted_payload_digest', r.redacted_payload_digest || 'unknown'],
    ['safe_summary', r.safe_summary || 'unknown'],
    ['next_safe_context', r.next_safe_context || 'unknown']
  ];
  for (const entry of entries) {
    const key = entry[0];
    const label = labels[key] || 'UNKNOWN';
    lines.push('- ' + key + ': ' + entry[1] + ' [' + label + ']');
  }
  return lines.join('\n');
}

function buildGovernedHandoffRecommendation(workFocus, classification, workerType, contextMode, options) {
  const opts = options && typeof options === 'object' ? options : {};
  const substantive = !!opts.substantive;
  const redactionBlockedOnly = !!opts.redactionBlockedOnly;
  const text = String(workFocus || '').toLowerCase();
  let target = 'none';
  if (/\bwre\b/.test(text)) {
    target = 'WRE';
  } else if (/\bopenclaw\b/.test(text)) {
    target = 'OpenClaw';
  } else if (/\bhermes\b/.test(text)) {
    target = 'Hermes';
  } else if (/\bsentinel\b/.test(text)) {
    target = 'Sentinel';
  }
  const evidenceRefs = [];
  if (opts.workFocusDigest) {
    evidenceRefs.push('work_focus_digest:' + opts.workFocusDigest);
  }
  if (opts.wspPromptDigest) {
    evidenceRefs.push('wsp_prompt_digest:' + opts.wspPromptDigest);
  }
  if (contextMode) {
    evidenceRefs.push('context_mode:' + String(contextMode));
  }
  if (redactionBlockedOnly) {
    return {
      handoff_needed: 'unknown',
      target: target,
      authority_level: 'advisory_only',
      reason: 'blocked_context_needs_local_0102_review',
      suggested_slice_name: 'none',
      wsp15_priority: 'P1',
      required_human_gate: 'none',
      evidence_refs: evidenceRefs.length ? evidenceRefs : ['unknown']
    };
  }
  let handoffNeeded = 'false';
  if (!substantive) {
    handoffNeeded = 'false';
  } else if (target !== 'none') {
    handoffNeeded = 'true';
  } else {
    handoffNeeded = 'unknown';
  }
  const tier = classification && classification.tier ? classification.tier : 'HIGH';
  const priority = tier === 'ULTRA' ? 'P0' : tier === 'REGULAR' ? 'P2' : 'P1';
  return {
    handoff_needed: handoffNeeded,
    target: target,
    authority_level: 'advisory_only',
    suggested_slice_name: target !== 'none' ? 'REDDOG_' + target + '_GOVERNED_HANDOFF_PHASE1' : 'none',
    wsp15_priority: priority,
    required_human_gate: handoffNeeded === 'true' ? '012_sovereign' : 'none',
    evidence_refs: evidenceRefs.length ? evidenceRefs : ['unknown']
  };
}

function buildGovernedHandoffSection(recommendation) {
  const rec = recommendation && typeof recommendation === 'object' ? recommendation : {};
  const lines = [
    '## Governed Handoff Recommendation',
    '- handoff_needed: ' + (rec.handoff_needed || 'unknown') + ' [INFERRED]',
    '- target: ' + (rec.target || 'none') + ' [INFERRED]',
    '- authority_level: advisory_only [OBSERVED]'
  ];
  if (rec.reason) {
    lines.push('- reason: ' + rec.reason + ' [INFERRED]');
  }
  lines.push(
    '- suggested_slice_name: ' + (rec.suggested_slice_name || 'none') + ' [INFERRED]',
    '- WSP_15 priority: ' + (rec.wsp15_priority || 'unknown') + ' [INFERRED]',
    '- required_human_gate: ' + (rec.required_human_gate || 'none') + ' [INFERRED]',
    '- evidence_refs: ' + JSON.stringify(rec.evidence_refs || ['unknown']) + ' [OBSERVED]'
  );
  return lines.join('\n');
}

function buildCopyMarkdown(result, workerType, contextSummary, workTrail, holoScorecard, resolvedEffort, copyContext) {
  const packet = result && typeof result === 'object' ? result : {};
  const ctx = copyContext && typeof copyContext === 'object' ? copyContext : {};
  const sections = [buildRunTraceSection(packet, workerType, contextSummary, holoScorecard, resolvedEffort)];
  sections.push(buildWorkTrailSection(workTrail || packet.work_trail || []));
  if (packet.reason === 'redaction_blocked') {
    const report = packet.redaction_gate_report || buildRedactionGateReport(packet, ctx.promptConstruction, ctx.contextMode);
    sections.push(buildRedactionGateReportSection(report));
  }
  const validation = packet.review_packet && packet.review_packet.output_validation;
  if (validation && (validation.output_validation_failed || (validation.repair_attempted && !validation.validated))) {
    sections.push(buildValidationFailedSection(validation));
    sections.push(VALIDATION_FAILED_FOOTER);
  }
  if (ctx.substantive) {
    sections.push(buildGovernedHandoffSection(ctx.handoffRecommendation || packet.governed_handoff_recommendation));
  }
  const mojibake = detectMojibake(packet.content || '');
  const flagged = (validation && validation.mojibake_detected) || mojibake.detected;
  if (flagged) {
    const markers = (validation && validation.mojibake_markers) || mojibake.markers;
    sections.push('## Mojibake Warning\n- mojibake_detected: true\n- markers: ' + markers.join(', '));
  }
  if (packet.reason === 'redaction_blocked') {
    sections.push('## 0102 Output');
    sections.push('(no model output - blocked locally before OpenRouter)');
  } else if (packet.content) {
    sections.push('## 0102 Output');
    sections.push(sanitizeCopyMdText(String(packet.content)));
  }
  return sanitizeCopyMdText(sections.join('\n\n'));
}

function appendValidationFailureContent(content, validationState) {
  const missing = validationState.missing_sections_after_repair || validationState.missing_sections || [];
  const reason = validationState.repair_failure_reason || 'schema_incomplete_after_repair';
  return String(content || '') + '\n\n---\n\n**OUTPUT_VALIDATION_FAILED**\n'
    + '- missing sections: ' + (missing.length ? missing.join(', ') : '(none listed)') + '\n'
    + '- repair_failure_reason: ' + reason + '\n'
    + '- note: Output is advisory and incomplete.\n\n'
    + VALIDATION_FAILED_FOOTER;
}
const DEFAULT_FUSION_WORKER = {
  title: 'Foundups®Agent',
  lead: 'z-ai/glm-5.2',
  panel: ['deepseek/deepseek-v4-pro', 'moonshotai/kimi-k2.7-code']
};

const REDDOG_ARCHITECT_SYSTEM_PROMPT = [
  'You are 0102 operating as the RedDog Architect advisory surface for FoundUps.',
  'Operate in WSP_00: self=0102, role=architect unless a narrower role is supplied, origin=external_principal.',
  'Apply WSP_97: retrieve/evaluate supplied evidence before stating facts; separate OBSERVED, INFERRED, and NEEDS_VERIFICATION; never claim direct repo access beyond the bounded context packet.',
  'Apply WSP_15 at the bottom of every substantive answer: score each recommended next action with Complexity, Importance, Deferability, Impact, MPS total, and P0-P4 priority.',
  'For every finding, include an actionable proposed fix or a reason the fix must be deferred.',
  'If the 012 work focus describes operational work, map it to an existing Skillz/Wardrobe/Rolodex/OpenClaw/Hermes handoff surface when evidence is supplied; do not execute it from this advisory tab.',
  'If HoloIndex recall is weak, offline, stale, or returns zero WSP hits, treat that as a retrieval-quality finding and propose the next retrieval/index repair step instead of overclaiming.',
  'If a public/, pfMALL, RedDog, WRE, OpenClaw, Hermes, Kanban, CABR, or FoundUp onboarding boundary appears, classify whether it is implemented, specified-not-implemented, inferred, or unknown.',
  'Do not edit files, run commands, merge PRs, create repos, grant authority, route payouts, or claim CABR/verification truth. Advisory only.',
  'Never expose raw hidden chain-of-thought. Use a structured Architect Trace: evidence retrieved, alternatives considered, critic disagreements, and synthesis rationale.',
  'Output format: Decision, Findings, Evidence, Proposed fixes, Uncertainties, Architect Trace, WSP_97 Truth Labels, WSP_15 Priority, Verification gaps, Next safest step.'
].join(' ');

const REDDOG_REQUIRED_OUTPUT_SECTIONS = [
  'Decision',
  'Findings',
  'Evidence',
  'Proposed fixes',
  'Uncertainties',
  'WSP_97 Truth Labels',
  'WSP_15 Priority',
  'Verification gaps',
  'Next safest step'
];

const ARCHITECT_TRACE_SECTIONS = [
  'Architect Trace',
  'Verification gaps'
];

const ULTRA_TASK_PATTERNS = [
  /\bauth(entication|orize|orization)?\b/i,
  /\bsecurity\b/i,
  /\bsecret(s)?\b/i,
  /\bcredential(s)?\b/i,
  /\boauth\b/i,
  /\blive runtime\b/i,
  /\bruntime control\b/i,
  /\bpublic\/\b/i,
  /\bpf\s?mall\b/i,
  /\bwre\b/i,
  /\bopenclaw\b/i,
  /\bhermes\b/i,
  /\bkanban\b/i,
  /\bcabr\b/i,
  /\bmerge authority\b/i,
  /\bmerge pr\b/i,
  /\brepo creation\b/i,
  /\bcreate repo\b/i,
  /\bdeploy(ment)?\b/i,
  /\bfirebase hosting\b/i
];

const HIGH_TASK_PATTERNS = [
  /\barchitecture\b/i,
  /\bwsp[_\s-]?\d+/i,
  /\bholoindex\b/i,
  /\bextension routing\b/i,
  /\bfoundup intake\b/i,
  /\breddog\b/i,
  /\borchestrat/i,
  /\bprotocol\b/i,
  /\bgate report\b/i,
  /\brepair slice\b/i,
  /\bmodlog\b/i,
  /\binterface\.md\b/i,
  /\bprocess all youtube comments\b/i,
  /\byoutube comments?\b/i,
  /\bcomment engagement\b/i,
  /\bskillz\b/i,
  /\bwardrobe\b/i,
  /\brolodex\b/i,
  /\bgoverned handoff\b/i
];

const REGULAR_TASK_PATTERNS = [
  /\bsmoke test\b/i,
  /\breply with exactly\b/i,
  /\bsimple explain\b/i,
  /\bui polish\b/i,
  /\bregular mode works\b/i
];

function classifyTaskForRedDog(prompt, contextMode, workerType) {
  const text = String(prompt || '');
  const worker = cleanWorkerType(workerType);
  const mode = cleanContextMode(contextMode);
  const haystack = text + ' ' + mode + ' ' + worker;
  let tier = 'HIGH';
  let reasons = [];

  if (ULTRA_TASK_PATTERNS.some((pattern) => pattern.test(haystack))) {
    tier = 'ULTRA';
    reasons.push('ultra_keyword_match');
  } else if (REGULAR_TASK_PATTERNS.some((pattern) => pattern.test(haystack)) && worker === 'smoke_tester') {
    tier = 'REGULAR';
    reasons.push('regular_smoke_prompt');
  } else if (HIGH_TASK_PATTERNS.some((pattern) => pattern.test(haystack))) {
    tier = 'HIGH';
    reasons.push('high_keyword_match');
  } else if (worker === 'smoke_tester') {
    tier = 'REGULAR';
    reasons.push('smoke_tester_default');
  } else {
    tier = 'HIGH';
    reasons.push('uncertain_default_high');
  }

  const preferManualPanel = tier !== 'REGULAR' || worker !== 'smoke_tester';
  return {
    tier,
    reasons,
    worker,
    contextMode: mode,
    preferManualPanel,
    prefersAuditablePanel: preferManualPanel && worker !== 'smoke_tester'
  };
}

function resolveAutoContextMode(classification, selectedContextMode) {
  const mode = cleanContextMode(selectedContextMode);
  if (mode !== 'auto') {
    return mode;
  }
  const tier = classification && classification.tier ? classification.tier : 'HIGH';
  if (tier === 'REGULAR') {
    return 'none';
  }
  if (tier === 'ULTRA') {
    return 'wsp_holo_git_skillz';
  }
  return 'wsp_holo_skillz';
}

function resolveAutoEffort(classification, selectedEffort) {
  const effort = cleanEffort(selectedEffort);
  if (effort !== 'auto') {
    return effort;
  }
  const tier = classification && classification.tier ? classification.tier : 'HIGH';
  if (tier === 'ULTRA') {
    return 'ultra';
  }
  if (tier === 'REGULAR') {
    return 'regular';
  }
  return 'high';
}

function resolveModelMode(classification, selectedMode, workerType) {
  const mode = cleanMode(selectedMode);
  const worker = cleanWorkerType(workerType);
  if (mode === 'auto') {
    return classification && classification.tier === 'REGULAR' ? 'openrouter_single' : 'foundups_fusion';
  }
  if (worker === 'smoke_tester') {
    return mode;
  }
  if (mode === 'openrouter_fusion_alias') {
    return mode;
  }
  if (classification && classification.prefersAuditablePanel) {
    return 'foundups_fusion';
  }
  return mode;
}

function validateRedDogOutput(markdown, options) {
  const opts = options || {};
  const sections = REDDOG_REQUIRED_OUTPUT_SECTIONS.slice();
  if (opts.substantiveArchitect) {
    for (const section of ARCHITECT_TRACE_SECTIONS) {
      if (!sections.includes(section)) {
        sections.push(section);
      }
    }
  }
  const text = String(markdown || '');
  const missingSections = [];
  for (const section of sections) {
    const pattern = new RegExp('(^|\\n)\\s*(#{1,3}\\s*)?' + section.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'i');
    if (!pattern.test(text)) {
      missingSections.push(section);
    }
  }
  const fusionPanelOk = opts.mode !== 'foundups_fusion' || (/## Lead/i.test(text) && /## Synthesis/i.test(text));
  if (opts.mode === 'foundups_fusion' && !fusionPanelOk) {
    missingSections.push('Fusion panel structure (Lead + Synthesis)');
  }
  return {
    valid: missingSections.length === 0,
    missingSections,
    fusion_panel_ok: fusionPanelOk
  };
}

function modeSelectionReasoning(classification, resolvedEffort, resolvedMode, resolvedContextMode) {
  const tier = classification && classification.tier ? classification.tier : 'HIGH';
  if (resolvedMode === 'openrouter_single') {
    return 'Single-model GLM principal: REGULAR-tier or smoke-classified work; avoids panel latency/cost; context=' + resolvedContextMode + '.';
  }
  if (resolvedMode === 'openrouter_fusion_alias') {
    return 'Explicit Fusion alias path: black-box synthesis; critic transcripts not exposed.';
  }
  if (tier === 'ULTRA') {
    return 'Fusion manual panel: ULTRA-tier security/runtime/auth/public-surface work needs adversarial critics; context=' + resolvedContextMode + ' includes git + Skillz/Rolodex handoff candidates.';
  }
  return 'Fusion manual panel: HIGH-tier WSP/architecture/operational work; auditable lead+critic+synthesis trail; context=' + resolvedContextMode + ' includes Skillz/Rolodex discovery for governed handoff only.';
}

function redactedDigest(text, maxExcerpt) {
  const raw = String(text || '');
  const excerpt = raw.replace(/\s+/g, ' ').trim().slice(0, maxExcerpt || 240);
  const hash = crypto.createHash('sha256').update(raw, 'utf8').digest('hex').slice(0, 16);
  return { hash: hash, excerpt: excerpt, length: raw.length };
}

function constructWspTaskPrompt(workFocus, classification, contextQuality, workerType) {
  const focus = String(workFocus || '').trim();
  const tier = classification && classification.tier ? classification.tier : 'HIGH';
  const reasons = classification && Array.isArray(classification.reasons) ? classification.reasons.join(', ') : '';
  const worker = cleanWorkerType(workerType);
  const lines = [
    'WSP Task Prompt (0102-generated from 012 work focus; 012 work focus (non-authoritative input))',
    '',
    'WSP_00: Operate as 0102 RedDog Architect advisory surface. 012 remains external principal; this tab has no execution authority.',
    'WSP_97: Separate OBSERVED, INFERRED, NEEDS_VERIFICATION, and SPECIFIED_NOT_IMPLEMENTED. Do not overclaim beyond bounded context.',
    'WSP_15 tier (auto-classified): ' + tier + (reasons ? ' (' + reasons + ')' : ''),
    'Worker mode: ' + worker,
    '',
    '012 work focus (non-authoritative):',
    focus.slice(0, 4000)
  ];
  if (contextQuality) {
    lines.push('', 'Retrieval quality note: ' + String(contextQuality).slice(0, 500));
  }
  lines.push('', 'Produce required RedDog architect output sections per contract.');
  return lines.join('\n');
}

function buildRepairPrompt(originalPrompt, badOutput, missingSections) {
  const sections = Array.isArray(missingSections) ? missingSections : [];
  return [
    'Repair pass: preserve the existing answer content and add only the missing required schema sections.',
    'Do not invent evidence, repo paths, test results, or authority.',
    'Label claims with WSP_97 truth labels where applicable.',
    'Missing sections: ' + (sections.length ? sections.join(', ') : '(none listed)'),
    '',
    'Original WSP task prompt:',
    String(originalPrompt || '').slice(0, 4000),
    '',
    'Draft answer to repair:',
    String(badOutput || '').slice(0, 12000)
  ].join('\n');
}

function isSubstantiveRedDogWorker(workerType) {
  const worker = cleanWorkerType(workerType);
  return worker === 'reddog_architect' || worker === 'wsp_gate_critic' || worker === 'repair_planner';
}

function attachOrchestratorMetadata(reviewPacket, classification, resolvedEffort, resolvedMode, validationState, resolvedContextMode, worker, promptConstruction, holoScorecard, workTrail) {
  const base = reviewPacket && typeof reviewPacket === 'object' ? reviewPacket : {};
  const construction = promptConstruction && typeof promptConstruction === 'object' ? promptConstruction : {};
  const providerReport = resolveProviderReasoningReport(resolvedEffort);
  return Object.assign({}, base, {
    task_classification: classification,
    resolved_effort: resolvedEffort,
    reddog_effort: String(resolvedEffort || 'unknown').toLowerCase(),
    resolved_mode: resolvedMode,
    resolved_context: resolvedContextMode,
    principal_model: worker && worker.lead ? worker.lead : undefined,
    panel_models: worker && Array.isArray(worker.panel) ? worker.panel : undefined,
    mode_selection_reasoning: modeSelectionReasoning(classification, resolvedEffort, resolvedMode, resolvedContextMode),
    work_focus_digest: construction.work_focus_digest,
    wsp_prompt_digest: construction.wsp_prompt_digest,
    prompt_construction: '0102_generated_from_work_focus',
    output_validation: validationState,
    holoindex_scorecard: holoScorecard || undefined,
    work_trail: workTrail && typeof workTrail.toEvents === 'function' ? workTrail.toEvents() : workTrail,
    provider_reasoning_requested: providerReport.provider_reasoning_requested,
    provider_reasoning_applied: providerReport.provider_reasoning_applied,
    provider_reasoning_note: providerReport.provider_reasoning_note
  });
}

function routingSummary(workerType, classification, resolvedEffort, resolvedMode, resolvedContextMode, worker) {
  const resolvedWorker = WORKER_TYPES[cleanWorkerType(workerType)];
  return [
    '## RedDog Routing',
    '- 0102 role: ' + resolvedWorker.label,
    '- WSP_15 tier: ' + (classification && classification.tier ? classification.tier : 'HIGH'),
    '- Effort: ' + resolvedEffort,
    '- Mode: ' + resolvedMode,
    '- Mode selection: ' + modeSelectionReasoning(classification, resolvedEffort, resolvedMode, resolvedContextMode),
    '- Principal: ' + worker.lead,
    '- Panel: ' + worker.panel.join(' + '),
    '- Context: ' + resolvedContextMode,
    '- Boundary: advisory-only; Skillz/OpenClaw/Hermes execution requires governed handoff.'
  ].join('\n');
}

const WORKER_TYPES = {
  reddog_architect: {
    label: 'RedDog Architect',
    prompt: REDDOG_ARCHITECT_SYSTEM_PROMPT
  },
  wsp_gate_critic: {
    label: 'WSP Gate Critic',
    prompt: REDDOG_ARCHITECT_SYSTEM_PROMPT + ' Emphasize gate failure modes, WSP_97 truth boundaries, missing evidence, non-vacuity, and exact return-to-author criteria.'
  },
  repair_planner: {
    label: 'Repair Planner',
    prompt: REDDOG_ARCHITECT_SYSTEM_PROMPT + ' Emphasize smallest valid repair slices, test contracts, ModLog/TestModLog memory, and PR-ready work breakdowns.'
  },
  smoke_tester: {
    label: 'Smoke Test',
    prompt: REDDOG_ARCHITECT_SYSTEM_PROMPT + ' Emphasize bounded smoke tests, expected output, failure reasons, and no destructive/live actions unless explicitly authorized.'
  }
};

const EFFORT_GUIDANCE = {
  auto: 'Effort: AUTO. Classify risk from supplied context. Use high rigor for WSP/security/architecture, normal rigor for simple smoke checks.',
  regular: 'Effort: REGULAR. Keep concise, verify core claims, avoid broad architecture unless needed.',
  high: 'Effort: HIGH. Run micro/macro reasoning over supplied context, compare alternatives, and include specific tests.',
  ultra: 'Effort: ULTRA. Treat as adversarial architecture review: include competing interpretations, non-vacuity checks, and failure-mode analysis.'
};

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand('foundupsFusion.open', () => openFusionEditor(context))
  );
}

function openFusionEditor(context) {
  const worker = fusionWorkerFromConfig();
  const panel = vscode.window.createWebviewPanel(
    'foundupsFusionWorker',
    worker.title,
    vscode.ViewColumn.Beside,
    {
      enableScripts: true,
      retainContextWhenHidden: true,
      localResourceRoots: [context.extensionUri]
    }
  );
  const logoUri = panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri, 'icon.png'));
  const state = { history: [], lastReviewPacket: null, bridgeChild: null, disposed: false };
  wireFusionWebview(context, panel.webview, worker, state);
  panel.onDidDispose(() => {
    killBridgeChild(state);
    state.disposed = true;
  });
  panel.webview.html = renderHtml(worker, 'editor', logoUri.toString());
}

function workspaceRoot() {
  const folder = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
  return folder ? folder.uri.fsPath : process.cwd();
}

function fusionWorkerFromConfig() {
  const config = vscode.workspace.getConfiguration('foundupsFusion');
  const lead = cleanModel(config.get('leadModel'), DEFAULT_FUSION_WORKER.lead);
  const configuredPanel = config.get('panelModels');
  const panel = Array.isArray(configuredPanel)
    ? configuredPanel.map((item) => cleanModel(item, '')).filter(Boolean).slice(0, 4)
    : DEFAULT_FUSION_WORKER.panel;
  return {
    title: DEFAULT_FUSION_WORKER.title,
    lead,
    panel: panel.length ? panel : DEFAULT_FUSION_WORKER.panel
  };
}

function cleanModel(value, fallback) {
  return typeof value === 'string' && value.trim() && value.length <= 120 ? value.trim() : fallback;
}

function wireFusionWebview(context, webview, worker, state) {
  webview.onDidReceiveMessage(async (message) => {
    if (!message || typeof message !== 'object') {
      return;
    }
    if (message.command === 'copyReview') {
      if (state.lastReviewPacket) {
        await vscode.env.clipboard.writeText(JSON.stringify(state.lastReviewPacket, null, 2));
        webview.postMessage({ command: 'status', text: 'Copied redacted review packet for 0102.' });
      } else {
        webview.postMessage({ command: 'status', text: 'No review packet available yet.' });
      }
      return;
    }
    if (message.command === 'copyMarkdown' && typeof message.text === 'string') {
      await vscode.env.clipboard.writeText(message.text);
      webview.postMessage({ command: 'status', text: 'Copied assistant markdown.' });
      return;
    }
    if (message.command !== 'ask' || typeof message.text !== 'string') {
      return;
    }

    const workFocus = message.text;
    const selectedContextMode = cleanContextMode(message.contextMode);
    const workerType = cleanWorkerType(message.workerType);
    const selectedEffort = cleanEffort(message.effort);
    const selectedMode = cleanMode(message.mode);
    const classification = classifyTaskForRedDog(workFocus, selectedContextMode, workerType);
    const effort = resolveAutoEffort(classification, selectedEffort);
    const mode = resolveModelMode(classification, selectedMode, workerType);
    const contextMode = resolveAutoContextMode(classification, selectedContextMode);
    const contextPacket = buildBoundedRepoContext(contextMode, workFocus);
    const wspTaskPrompt = constructWspTaskPrompt(workFocus, classification, contextPacket.quality, workerType);
    const promptConstruction = {
      work_focus_digest: redactedDigest(workFocus, 180),
      wsp_prompt_digest: redactedDigest(wspTaskPrompt, 320)
    };
    const systemPrompt = buildSystemPrompt(workerType, effort, contextPacket.quality);

    postStatusAndProgress(webview, null, 'Orchestrator: effort=' + effort + ' mode=' + mode + ' tier=' + classification.tier + ' context=' + contextMode + ' principal=' + worker.lead + ' panel=' + worker.panel.join(' + ') + ' (' + classification.reasons.join(', ') + ')');
    postStatusAndProgress(webview, null, 'Bridge started. Redaction gate runs before any OpenRouter API call.');
    if (contextPacket.summary) {
      postStatusAndProgress(webview, null, contextPacket.summary);
    }
    postStatusAndProgress(webview, null, '0102 assembled WSP task prompt from 012 work focus (bridge receives WSP task prompt, not raw focus alone).');
    const holoScorecard = contextPacket.holoindex_scorecard || extractHoloIndexScorecard(contextMode, contextPacket.holoindex_meta);
    const workTrail = createWorkTrail();
    workTrail.push('orchestrator_started');
    if (contextPacket.summary) {
      workTrail.push('repo_context_attached', contextPacket.summary);
    }
    if (holoScorecard) {
      workTrail.push('holoindex_result', 'wsp_hits=' + holoScorecard.wsp_hits + '; code_hits=' + holoScorecard.code_hits);
    }
    workTrail.push('wsp_prompt_assembled');

    let validationState = { validated: false, skipped: true, reason: 'not_validated' };
    const onBridgeProgress = (stage, text) => {
      postStatusMessage(webview, text);
      postProgressMessage(webview, stage, text);
      const normalized = normalizeBridgeStageToWorkTrail(stage, text);
      if (normalized) {
        workTrail.push(normalized.event, normalized.detail);
      }
    };
    let result = await callFusion(context, worker, wspTaskPrompt, contextPacket.text, systemPrompt, state.history, mode, onBridgeProgress, state, promptConstruction);
    if (result.ok && isSubstantiveRedDogWorker(workerType)) {
      workTrail.push('validator_started');
      const validation = validateRedDogOutput(result.content || '', { substantiveArchitect: true, mode: mode });
      validationState = {
        validated: validation.valid,
        missing_sections: validation.missingSections,
        repair_attempted: false,
        repair_ok: false
      };
      if (!validation.valid && validation.missingSections.length) {
        validationState.repair_attempted = true;
        workTrail.push('repair_started');
        postStatusAndProgress(webview, null, 'Output schema incomplete. Missing: ' + validation.missingSections.join(', ') + '. Running one repair pass...');
        const repairPrompt = buildRepairPrompt(wspTaskPrompt, result.content, validation.missingSections);
        const repairResult = await callFusion(
          context,
          worker,
          repairPrompt,
          contextPacket.text,
          systemPrompt + '\n\nRepair pass: add missing schema sections only. Do not invent evidence.',
          state.history,
          mode,
          onBridgeProgress,
          state,
          promptConstruction
        );
        if (repairResult.ok) {
          const repairValidation = validateRedDogOutput(repairResult.content || '', { substantiveArchitect: true, mode: mode });
          validationState.repair_ok = repairValidation.valid;
          validationState.missing_sections_after_repair = repairValidation.missingSections;
          if (repairValidation.valid) {
            result = repairResult;
            validationState.validated = true;
            validationState.missing_sections = [];
            workTrail.push('repair_complete');
          } else {
            validationState.validated = false;
            validationState.output_validation_failed = true;
            validationState.repair_failure_reason = 'schema_incomplete_after_repair';
            result.content = appendValidationFailureContent(result.content, validationState);
          }
        } else {
          validationState.validated = false;
          validationState.output_validation_failed = true;
          validationState.repair_ok = false;
          validationState.repair_failure_reason = repairResult.reason || 'unknown';
          workTrail.push(repairResult.reason === 'redaction_blocked' ? 'repair_blocked' : 'repair_blocked', validationState.repair_failure_reason);
          result.content = appendValidationFailureContent(result.content, validationState);
        }
      }
    } else if (result.ok) {
      validationState = { validated: false, skipped: true, reason: 'non_substantive_worker' };
    } else if (result.reason === 'redaction_blocked') {
      validationState = { validated: false, skipped: true, reason: 'redaction_blocked' };
      workTrail.push('redaction_gate_blocked');
    } else {
      workTrail.push('failed', result.reason || 'unknown');
    }
    const substantiveTask = isSubstantiveRedDogWorker(workerType);
    const handoffRecommendation = buildGovernedHandoffRecommendation(workFocus, classification, workerType, contextMode, {
      substantive: substantiveTask,
      redactionBlockedOnly: result.reason === 'redaction_blocked',
      workFocusDigest: promptConstruction.work_focus_digest && promptConstruction.work_focus_digest.hash,
      wspPromptDigest: promptConstruction.wsp_prompt_digest && promptConstruction.wsp_prompt_digest.hash
    });
    result.review_packet = attachOrchestratorMetadata(
      result.review_packet || {},
      classification,
      effort,
      mode,
      validationState,
      contextMode,
      worker,
      promptConstruction,
      holoScorecard,
      workTrail
    );
    result.governed_handoff_recommendation = handoffRecommendation;
    if (result.reason === 'redaction_blocked') {
      result.redaction_gate_report = buildRedactionGateReport(result, promptConstruction, contextMode);
      result.review_packet.redaction_gate_report = result.redaction_gate_report;
    }
    if (result.ok) {
      workTrail.push('completed');
    }
    result.work_trail = workTrail.toEvents();
    if (result.ok && result.content) {
      result.content = routingSummary(workerType, classification, effort, mode, contextMode, worker) + '\n\n' + result.content;
      const mojibake = detectMojibake(result.content);
      if (mojibake.detected) {
        result.review_packet.output_validation = Object.assign({}, result.review_packet.output_validation || {}, {
          mojibake_detected: true,
          mojibake_markers: mojibake.markers
        });
      }
    }
    if (result.ok && Array.isArray(result.history)) {
      state.history = result.history;
    }
    result = enrichRedactionBlockResult(result);
    if (result.review_packet) {
      state.lastReviewPacket = result.review_packet;
    }
    result.copy_markdown = buildCopyMarkdown(result, workerType, contextPacket.summary, workTrail, holoScorecard, effort, {
      promptConstruction: promptConstruction,
      contextMode: contextMode,
      substantive: substantiveTask,
      handoffRecommendation: handoffRecommendation
    });
    webview.postMessage({ command: 'result', result });
  });
}

function killBridgeChild(state) {
  if (!state || !state.bridgeChild) {
    return;
  }
  try {
    if (!state.bridgeChild.killed) {
      state.bridgeChild.kill();
    }
  } catch (err) {
    // ignore kill errors on already-exited children
  }
  state.bridgeChild = null;
}

function resolvePythonInterpreter(root, configuredPath) {
  const trimmed = typeof configuredPath === 'string' ? configuredPath.trim() : '';
  if (trimmed && trimmed !== 'python' && fs.existsSync(trimmed)) {
    return { path: trimmed, source: 'configured' };
  }
  const isWin = process.platform === 'win32';
  const dotVenv = path.join(root, '.venv', isWin ? 'Scripts' : 'bin', isWin ? 'python.exe' : 'python');
  if (fs.existsSync(dotVenv)) {
    return { path: dotVenv, source: 'workspace_dotvenv' };
  }
  const venvPath = path.join(root, 'venv', isWin ? 'Scripts' : 'bin', isWin ? 'python.exe' : 'python');
  if (fs.existsSync(venvPath)) {
    return { path: venvPath, source: 'workspace_venv' };
  }
  return { path: trimmed || 'python', source: 'system' };
}

function bridgeStreamCapExceeded(currentBytes, chunkLength, cap) {
  return currentBytes + chunkLength > cap;
}

function applyBridgeContextBudget(prompt, context) {
  const budget = {
    truncation_applied: false,
    truncation_reason: null,
    prompt_chars_before: String(prompt || '').length,
    context_chars_before: String(context || '').length
  };
  let boundedPrompt = String(prompt || '');
  let boundedContext = String(context || '');
  if (boundedPrompt.length > BRIDGE_MAX_PROMPT_CHARS) {
    boundedPrompt = boundedPrompt.slice(0, BRIDGE_MAX_PROMPT_CHARS);
    budget.truncation_applied = true;
    budget.truncation_reason = 'prompt_char_budget';
  }
  if (boundedContext.length > BRIDGE_MAX_CONTEXT_CHARS) {
    boundedContext = boundedContext.slice(0, BRIDGE_MAX_CONTEXT_CHARS);
    budget.truncation_applied = true;
    budget.truncation_reason = budget.truncation_reason ? 'prompt_and_context_char_budget' : 'context_char_budget';
  }
  return { prompt: boundedPrompt, context: boundedContext, budget: budget };
}

function attachBridgeMetadata(reviewPacket, bridgeMeta) {
  if (!reviewPacket || typeof reviewPacket !== 'object') {
    return reviewPacket;
  }
  const meta = bridgeMeta && typeof bridgeMeta === 'object' ? bridgeMeta : {};
  return Object.assign({}, reviewPacket, meta);
}

function callFusion(context, worker, prompt, boundedContext, systemPrompt, history, mode, onProgress, state, bridgeMeta) {
  return new Promise((resolve) => {
    const root = workspaceRoot();
    const script = path.join(root, 'scripts', 'advisory_model_once.py');
    const config = vscode.workspace.getConfiguration('foundupsFusion');
    const configuredPython = config.get('pythonPath') || 'python';
    const interpreter = resolvePythonInterpreter(root, configuredPython);
    const budgeted = applyBridgeContextBudget(prompt, boundedContext);
    onProgress(null, 'Mode: ' + mode);
    onProgress(null, 'Python interpreter: ' + interpreter.path + ' (' + interpreter.source + ')');
    onProgress(null, 'Bridge process starting');
    onProgress(null, 'Workspace root: ' + root);
    onProgress(null, 'Bridge script: ' + script);
    onProgress(null, 'OpenRouter key visible to Cursor process: ' + (process.env.OPENROUTER_API_KEY ? 'yes' : 'no'));
    if (budgeted.budget.truncation_applied) {
      onProgress(null, 'Context budget applied: ' + budgeted.budget.truncation_reason);
    }
    let settled = false;
    function finish(result) {
      if (!shouldAcceptBridgeCompletion(settled, state)) {
        return;
      }
      settled = true;
      if (state) {
        state.bridgeChild = null;
      }
      resolve(result);
    }

    const child = cp.spawn(interpreter.path, [script], {
      cwd: root,
      env: process.env,
      windowsHide: true,
      stdio: ['pipe', 'pipe', 'pipe']
    });
    if (state) {
      state.bridgeChild = child;
    }

    let stdout = '';
    let stderr = '';
    let stdoutBytes = 0;
    let stderrBytes = 0;
    const payload = {
      mode,
      prompt: budgeted.prompt,
      context: budgeted.context,
      system: systemPrompt,
      model: mode === 'openrouter_single' ? worker.lead : undefined,
      history,
      lead_model: worker.lead,
      panel_models: worker.panel,
      max_tokens: 2200,
      temperature: 0.2,
      timeout: mode === 'foundups_fusion' ? 120 : 90,
      bridge_meta: Object.assign({}, bridgeMeta || {}, {
        python_interpreter: interpreter.path,
        python_interpreter_source: interpreter.source,
        truncation_applied: budgeted.budget.truncation_applied,
        truncation_reason: budgeted.budget.truncation_reason
      })
    };

    child.stdout.on('data', (chunk) => {
      stdoutBytes += chunk.length;
      if (bridgeStreamCapExceeded(stdoutBytes, 0, BRIDGE_MAX_STDOUT_BYTES)) {
        killBridgeChild(state);
        finish({ ok: false, reason: 'output_cap_exceeded', detail: 'stdout cap exceeded' });
        return;
      }
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderrBytes += chunk.length;
      if (bridgeStreamCapExceeded(stderrBytes, 0, BRIDGE_MAX_STDERR_BYTES)) {
        killBridgeChild(state);
        finish({ ok: false, reason: 'output_cap_exceeded', detail: 'stderr cap exceeded' });
        return;
      }
      const text = chunk.toString();
      stderr += text;
      for (const line of text.split(/\r?\n/)) {
        if (!line.trim()) continue;
        try {
          const event = JSON.parse(line);
          if (event && event.event === 'progress' && event.text) {
            onProgress(event.stage || null, event.text);
          }
        } catch (err) {
          // stderr can contain non-JSON diagnostics from Python dependencies.
        }
      }
    });
    child.on('error', (err) => {
      finish({ ok: false, reason: 'subprocess_failed', detail: err.message });
    });
    child.on('close', (code) => {
      if (settled) {
        return;
      }
      try {
        const parsed = JSON.parse(stdout || '{}');
        if (!parsed.ok && code !== 0 && !parsed.reason) {
          parsed.reason = 'subprocess_failed';
          parsed.exit_code = code;
        }
        finish(parsed);
      } catch (err) {
        finish({ ok: false, reason: 'malformed_response', detail: stderr.slice(0, 500) });
      }
    });
    child.stdin.write(JSON.stringify(payload));
    child.stdin.end();
  });
}

function cleanContextMode(value) {
  if (value === 'auto' || value === 'wsp_holo' || value === 'wsp_holo_git' || value === 'wsp_holo_skillz' || value === 'wsp_holo_git_skillz' || value === 'active_editor' || value === 'git_diff' || value === 'none') {
    return value;
  }
  return 'auto';
}

function cleanWorkerType(value) {
  return Object.prototype.hasOwnProperty.call(WORKER_TYPES, value) ? value : 'reddog_architect';
}

function cleanEffort(value) {
  return Object.prototype.hasOwnProperty.call(EFFORT_GUIDANCE, value) ? value : 'auto';
}

function buildSystemPrompt(workerType, effort, retrievalQuality) {
  const worker = WORKER_TYPES[cleanWorkerType(workerType)];
  const effortText = EFFORT_GUIDANCE[cleanEffort(effort)];
  const qualityText = retrievalQuality ? 'Retrieval quality note: ' + retrievalQuality : '';
  return [worker.prompt, effortText, qualityText, 'Always end with a WSP_15 Priority block and one Next safest step.'].filter(Boolean).join('\n\n');
}

function buildBoundedRepoContext(mode, taskText) {
  const root = workspaceRoot();
  const sections = [
    '## WSP_OPERATING_CONTRACT',
    '- You are an advisory 0102 worker surface. 012 remains the external principal and final decision holder.',
    '- Operate in WSP_00: HoloIndex-first recall, anti-vibecoding, verify before recommending action.',
    '- Apply WSP_97: label each factual claim as OBSERVED, INFERRED, or NEEDS_VERIFICATION.',
    '- Apply WSP_15: every recommended fix must include C/I/D/Impact/MPS/Priority.',
    '- Every finding must include a proposed fix or an explicit defer/block reason.',
    '- No shell, repo modification, credential, browser, deploy, or runtime control. Return recommendations only.',
    '',
    '## BOUNDED_REPO_CONTEXT',
    'The model cannot read the filesystem. The following context was gathered by the local Cursor extension and redaction-gated before egress.',
    'Context mode: ' + mode,
    'Workspace root: ' + root
  ];
  let quality = 'No HoloIndex requested for this context mode.';
  let holoindex_meta = null;
  let holoindex_scorecard = null;
  if (mode === 'none') {
    const text = sections.join('\n');
    return { text, summary: 'Repo context: WSP operating contract only.', quality, holoindex_meta, holoindex_scorecard };
  }
  if (mode === 'wsp_holo' || mode === 'wsp_holo_git' || mode === 'wsp_holo_skillz' || mode === 'wsp_holo_git_skillz') {
    const holo = holoIndexOutput(root, taskText || '', 18000);
    quality = holo.quality;
    holoindex_meta = holo.meta || null;
    holoindex_scorecard = extractHoloIndexScorecard(mode, holoindex_meta);
    sections.push('### HoloIndex recall (WSP_00 bundle-json first; offline fallback only if needed)\n```text\n' + (holo.output || '(no HoloIndex output)') + '\n```');
  }
  if (mode === 'wsp_holo_skillz' || mode === 'wsp_holo_git_skillz') {
    const skillz = skillzWardrobeRolodexContext(root, taskText || '', 12000);
    sections.push(skillz);
    if (skillz.includes('(no matching Skillz/Wardrobe/Rolodex paths found')) {
      quality = (quality ? quality + '; ' : '') + 'Skillz/Rolodex discovery returned zero matches; treat handoff recommendations as NEEDS_VERIFICATION.';
    }
  }
  const active = activeEditorContext(root);
  if (active) {
    sections.push(active);
  }
  if (mode === 'git_diff' || mode === 'wsp_holo_git' || mode === 'wsp_holo_git_skillz') {
    const status = gitOutput(root, ['status', '--short'], 8000);
    const stat = gitOutput(root, ['diff', '--stat'], 8000);
    const diff = gitOutput(root, ['diff', '--', '.'], 24000);
    sections.push('### git status --short\n```text\n' + (status || '(clean)') + '\n```');
    sections.push('### git diff --stat\n```text\n' + (stat || '(no diff)') + '\n```');
    sections.push('### git diff -- . (bounded)\n```diff\n' + (diff || '(no diff)') + '\n```');
  }
  const text = sections.join('\n\n').slice(0, 42000);
  return { text, summary: 'Repo context attached: ' + mode + ' (' + text.length + ' chars). ' + quality, quality, holoindex_meta, holoindex_scorecard };
}

function activeEditorContext(root) {
  const editor = vscode.window.activeTextEditor || (vscode.window.visibleTextEditors && vscode.window.visibleTextEditors[0]);
  if (!editor || !editor.document) {
    return '';
  }
  const doc = editor.document;
  if (!doc.uri || doc.uri.scheme !== 'file') {
    return '';
  }
  const filePath = doc.uri.fsPath;
  const rel = relativePath(root, filePath);
  const selected = editor.selection && !editor.selection.isEmpty;
  const raw = selected ? doc.getText(editor.selection) : doc.getText();
  const max = selected ? 16000 : 24000;
  const clipped = raw.length > max ? raw.slice(0, max) + '\n...[TRUNCATED ' + (raw.length - max) + ' chars]' : raw;
  return '### active editor ' + (selected ? 'selection' : 'file') + ': ' + rel + '\n```' + (doc.languageId || 'text') + '\n' + clipped + '\n```';
}

function repoFileIndex(root, maxFiles) {
  const gitFiles = gitOutput(root, ['ls-files'], 1000000);
  if (gitFiles && !gitFiles.startsWith('[git context unavailable')) {
    const files = gitFiles.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    if (files.length) {
      return files.slice(0, maxFiles);
    }
  }
  const roots = ['modules', 'holo_index', '.claude', 'extensions', 'scripts', 'data'];
  const files = [];
  for (const relRoot of roots) {
    walkRepoFiles(root, relRoot, files, maxFiles);
    if (files.length >= maxFiles) {
      break;
    }
  }
  return files;
}

function walkRepoFiles(root, relDir, files, maxFiles) {
  if (files.length >= maxFiles) {
    return;
  }
  const fullDir = path.resolve(root, relDir);
  const resolvedRoot = path.resolve(root);
  if (fullDir !== resolvedRoot && !fullDir.startsWith(resolvedRoot + path.sep)) {
    return;
  }
  let entries;
  try {
    entries = fs.readdirSync(fullDir, { withFileTypes: true });
  } catch (err) {
    return;
  }
  for (const entry of entries) {
    if (files.length >= maxFiles) {
      return;
    }
    if (entry.name === '.git' || entry.name === 'node_modules' || entry.name === '__pycache__' || entry.name === '.venv' || entry.name === 'dist' || entry.name === 'build') {
      continue;
    }
    const rel = path.posix.join(relDir.replace(/\\/g, '/'), entry.name);
    if (entry.isDirectory()) {
      walkRepoFiles(root, rel, files, maxFiles);
    } else if (entry.isFile()) {
      files.push(rel);
    }
  }
}

function skillzWardrobeRolodexContext(root, taskText, maxChars) {
  const files = repoFileIndex(root, 12000);
  const queryTokens = String(taskText || '')
    .toLowerCase()
    .split(/[^a-z0-9_]+/)
    .filter((token) => token.length >= 3)
    .slice(0, 24);
  const candidates = files
    .filter((file) => isSkillzRolodexPath(file))
    .map((file) => ({ file, score: scoreSkillzPath(file, queryTokens) }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || a.file.localeCompare(b.file))
    .slice(0, 40);
  const lines = [
    '### Skillz/Wardrobe/Rolodex discovery (advisory handoff only)',
    'RedDog may recommend these governed surfaces, but this extension does not execute them.',
    'Top matches:'
  ];
  if (!candidates.length) {
    lines.push('(no matching Skillz/Wardrobe/Rolodex paths found by bounded git index scan)');
  }
  for (const item of candidates) {
    lines.push('- ' + item.file + ' (score=' + item.score + ')');
  }
  const snippets = [];
  for (const item of candidates.slice(0, 8)) {
    if (!/\.(md|json|py|js)$/i.test(item.file)) {
      continue;
    }
    const snippet = readBoundedRepoFile(root, item.file, 1400);
    if (snippet) {
      snippets.push('#### ' + item.file + '\n```text\n' + snippet + '\n```');
    }
  }
  const text = lines.join('\n') + (snippets.length ? '\n\n' + snippets.join('\n\n') : '');
  return text.slice(0, maxChars);
}

function isSkillzRolodexPath(file) {
  const normalized = String(file || '').replace(/\\/g, '/').toLowerCase();
  return normalized.includes('/skillz/')
    || normalized.includes('/skills/')
    || normalized.includes('skills_registry')
    || normalized.includes('skills_index')
    || normalized.includes('wardrobe')
    || normalized.includes('rolodex')
    || normalized.includes('command_rolodex')
    || normalized.includes('agent_cli_catalog')
    || normalized.includes('hermes_job_executor')
    || normalized.includes('openclaw');
}

function scoreSkillzPath(file, tokens) {
  const normalized = String(file || '').replace(/\\/g, '/').toLowerCase();
  let score = 1;
  if (normalized.includes('skillz')) score += 3;
  if (normalized.includes('skills_registry') || normalized.includes('skills_index')) score += 4;
  if (normalized.includes('wardrobe') || normalized.includes('rolodex')) score += 5;
  if (normalized.includes('hermes') || normalized.includes('openclaw')) score += 3;
  if (normalized.endsWith('skillz.md') || normalized.endsWith('.json')) score += 2;
  for (const token of tokens) {
    if (normalized.includes(token)) score += 4;
  }
  return score;
}

function readBoundedRepoFile(root, relPath, maxChars) {
  try {
    const full = path.resolve(root, relPath);
    const resolvedRoot = path.resolve(root);
    if (full !== resolvedRoot && !full.startsWith(resolvedRoot + path.sep)) {
      return '';
    }
    const stat = fs.statSync(full);
    if (!stat.isFile() || stat.size > 500000) {
      return '';
    }
    return fs.readFileSync(full, 'utf8').slice(0, maxChars);
  } catch (err) {
    return '';
  }
}

function relativePath(root, filePath) {
  try {
    const rel = path.relative(root, filePath);
    if (rel && !rel.startsWith('..') && !path.isAbsolute(rel)) {
      return rel;
    }
  } catch (err) {
    // fall through to basename
  }
  return path.basename(filePath);
}

function moduleHintFromActive(root) {
  const editor = vscode.window.activeTextEditor || (vscode.window.visibleTextEditors && vscode.window.visibleTextEditors[0]);
  if (!editor || !editor.document || !editor.document.uri || editor.document.uri.scheme !== 'file') {
    return 'extensions/foundups_advisory_workers';
  }
  const rel = relativePath(root, editor.document.uri.fsPath).replace(/\\/g, '/');
  if (!rel || rel.startsWith('..')) {
    return 'extensions/foundups_advisory_workers';
  }
  const parts = rel.split('/');
  if (parts[0] === 'modules' && parts.length >= 3) {
    return parts.slice(0, 3).join('/');
  }
  if (parts[0] === 'extensions' && parts.length >= 2) {
    return parts.slice(0, 2).join('/');
  }
  return parts[0];
}

function holoIndexMetaFromBundle(output, usedOfflineFallback) {
  const meta = {
    holoindex_status: usedOfflineFallback ? 'offline_fallback' : 'unknown',
    wsp_hits: 'unknown',
    code_hits: 'unknown',
    skill_hits: 'unknown',
    index_gap_detected: 'unknown',
    direct_read_fallback_used: usedOfflineFallback ? true : false
  };
  try {
    const data = JSON.parse(String(output || '{}'));
    const bundleMeta = data.task_retrieval && data.task_retrieval.metadata ? data.task_retrieval.metadata : {};
    const missing = data.structured_memory && Array.isArray(data.structured_memory.missing_required)
      ? data.structured_memory.missing_required
      : [];
    meta.holoindex_status = usedOfflineFallback ? 'offline_fallback' : 'bundle_json_ok';
    meta.wsp_hits = Number(bundleMeta.wsp_count || 0);
    meta.code_hits = Number(bundleMeta.code_count || 0);
    meta.skill_hits = bundleMeta.skill_count !== undefined ? Number(bundleMeta.skill_count) : 'unknown';
    meta.index_gap_detected = missing.length > 0 || meta.wsp_hits === 0;
    meta.direct_read_fallback_used = !!usedOfflineFallback;
  } catch (err) {
    meta.holoindex_status = usedOfflineFallback ? 'offline_fallback' : 'parse_error';
  }
  return meta;
}

function holoIndexOutput(root, taskText, maxChars) {
  const query = String(taskText || '').replace(/\s+/g, ' ').trim().slice(0, 500) || 'FoundUps RedDog WSP_00 WSP_97 WSP_15 current task';
  const moduleHint = moduleHintFromActive(root);
  try {
    const env = Object.assign({}, process.env, { HOLO_SKIP_MODEL: '1' });
    const output = cp.execFileSync('python', ['-B', 'holo_index.py', '--bundle-json', '--search', query, '--bundle-module-hint', moduleHint, '--limit', '5', '--quiet-root-alerts'], {
      cwd: root,
      env,
      encoding: 'utf8',
      timeout: 25000,
      maxBuffer: Math.max(maxChars * 4, 65536),
      windowsHide: true
    });
    const meta = holoIndexMetaFromBundle(output, false);
    return { output: String(output || '').slice(0, maxChars), quality: summarizeHoloBundle(output), meta: meta };
  } catch (bundleErr) {
    try {
      const output = cp.execFileSync('python', ['-B', 'holo_index.py', '--offline', '--search', query, '--limit', '5'], {
        cwd: root,
        encoding: 'utf8',
        timeout: 20000,
        maxBuffer: Math.max(maxChars * 4, 65536),
        windowsHide: true
      });
      const meta = holoIndexMetaFromBundle(output, true);
      return {
        output: String(output || '').slice(0, maxChars),
        quality: 'HoloIndex bundle-json failed; offline lexical fallback used. Treat protocol coverage as NEEDS_VERIFICATION and propose re-index/bundle repair if WSP hits are missing.',
        meta: meta
      };
    } catch (offlineErr) {
      return {
        output: '[HoloIndex unavailable: ' + (offlineErr && offlineErr.message ? offlineErr.message.slice(0, 180) : 'unknown') + ']',
        quality: 'HoloIndex unavailable. Use supplied editor/git evidence only; propose HoloIndex recovery as a fix when retrieval affects the decision.',
        meta: holoIndexMetaFromBundle('', false)
      };
    }
  }
}

function summarizeHoloBundle(output) {
  try {
    const data = JSON.parse(String(output || '{}'));
    const meta = data.task_retrieval && data.task_retrieval.metadata ? data.task_retrieval.metadata : {};
    const wspCount = Number(meta.wsp_count || 0);
    const codeCount = Number(meta.code_count || 0);
    const missing = data.structured_memory && Array.isArray(data.structured_memory.missing_required)
      ? data.structured_memory.missing_required
      : [];
    const parts = ['HoloIndex bundle-json ok', 'wsp=' + wspCount, 'code=' + codeCount];
    if (missing.length) {
      parts.push('missing_required=' + missing.join(','));
    }
    if (wspCount === 0) {
      parts.push('WSP hits are zero; propose retrieval/index repair before strong protocol claims.');
    }
    return parts.join('; ');
  } catch (err) {
    return 'HoloIndex bundle-json returned non-JSON output; treat recall as NEEDS_VERIFICATION.';
  }
}

function gitOutput(root, args, maxChars) {
  try {
    if (!fs.existsSync(path.join(root, '.git'))) {
      return '';
    }
    const output = cp.execFileSync('git', args, {
      cwd: root,
      encoding: 'utf8',
      timeout: 5000,
      maxBuffer: Math.max(maxChars * 4, 65536),
      windowsHide: true
    });
    return String(output || '').slice(0, maxChars);
  } catch (err) {
    return '[git context unavailable: ' + (err && err.message ? err.message.slice(0, 180) : 'unknown') + ']';
  }
}

function cleanMode(value) {
  if (value === 'auto' || value === 'openrouter_single' || value === 'openrouter_fusion_alias' || value === 'foundups_fusion') {
    return value;
  }
  return 'auto';
}

function reddogTrailWebviewBootstrapJson() {
  return JSON.stringify({
    stageActions: REDDOG_STAGE_ACTIONS,
    progressActions: REDDOG_PROGRESS_ACTIONS,
    terminalHoldMs: REDDOG_TERMINAL_HOLD_MS,
    operatorMessage: REDACTION_BLOCK_OPERATOR_MESSAGE
  });
}

function renderHtml(worker, surface, logoUri) {
  const escapedTitle = escapeHtml(worker.title);
  const escapedLead = escapeHtml(worker.lead);
  const escapedPanel = escapeHtml(worker.panel.join(' + '));
  const escapedSurface = escapeHtml(surface);
  const escapedLogoUri = escapeHtml(logoUri || '');
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapedTitle}</title>
  <style>
    :root { color-scheme: dark; }
    html, body { height: 100%; overflow: hidden; }
    body { margin: 0; font-family: var(--vscode-font-family); color: var(--vscode-foreground); background: var(--vscode-editor-background); }
    .wrap { display: grid; grid-template-rows: auto minmax(0, 1fr) auto; height: 100vh; overflow: hidden; }
    header { padding: 8px 12px; border-bottom: 1px solid var(--vscode-panel-border); background: var(--vscode-editor-background); }
    .brand { display: flex; align-items: center; gap: 9px; margin-bottom: 3px; }
    .brand img { width: 30px; height: 30px; object-fit: contain; }
    h1 { margin: 0; font-size: 14px; font-weight: 600; }
    .meta { color: var(--vscode-descriptionForeground); font-size: 11px; line-height: 1.35; }
    #log { min-height: 0; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; gap: 10px; scroll-behavior: smooth; }
    .entry { border: 1px solid var(--vscode-panel-border); border-radius: 6px; padding: 8px; white-space: pre-wrap; line-height: 1.45; font-size: 12px; overflow-wrap: anywhere; }
    .entry .label { display: block; margin-bottom: 5px; color: var(--vscode-descriptionForeground); font-size: 10px; text-transform: uppercase; letter-spacing: 0; }
    .user { border-left: 3px solid var(--vscode-charts-blue); }
    .assistant { border-left: 3px solid var(--vscode-charts-green); }
    .status { border-left: 3px solid var(--vscode-descriptionForeground); color: var(--vscode-descriptionForeground); background: var(--vscode-sideBar-background); }
    .error { border-left: 3px solid var(--vscode-errorForeground); color: var(--vscode-errorForeground); }
    form { display: grid; grid-template-columns: 1fr; gap: 7px; padding: 10px; border-top: 1px solid var(--vscode-panel-border); background: var(--vscode-editor-background); z-index: 1; }
    .toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; color: var(--vscode-descriptionForeground); font-size: 11px; }
    .pill { border: 1px solid var(--vscode-panel-border); border-radius: 999px; padding: 3px 7px; color: var(--vscode-descriptionForeground); background: var(--vscode-sideBar-background); }
    select, button { color: var(--vscode-dropdown-foreground); background: var(--vscode-dropdown-background); border: 1px solid var(--vscode-dropdown-border); padding: 3px 6px; }
    button { cursor: pointer; }
    textarea { resize: none; min-height: 74px; max-height: 180px; padding: 8px; color: var(--vscode-input-foreground); background: var(--vscode-input-background); border: 1px solid var(--vscode-input-border); font-family: var(--vscode-editor-font-family); }
    textarea:focus { outline: 1px solid var(--vscode-focusBorder); }
    .hint { color: var(--vscode-descriptionForeground); font-size: 11px; }
    .reddog-working-trail {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 3px 0 2px 0;
      font-size: 11px;
      font-family: var(--vscode-editor-font-family);
      color: var(--vscode-descriptionForeground);
      min-height: 18px;
      user-select: none;
    }
    .reddog-working-trail[data-active="true"] { color: var(--vscode-charts-green); }
    .reddog-working-trail[data-active="error"] { color: var(--vscode-errorForeground); }
    [data-reddog-elapsed] { font-variant-numeric: tabular-nums; }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="brand"><img src="${escapedLogoUri}" alt="RedDawg"><h1>${escapedTitle}</h1></div>
      <div class="meta">Build: ${EXTENSION_VERSION}<br>Surface: ${escapedSurface}<br>Principal: ${escapedLead}<br>Panel: ${escapedPanel}<br>Advisory only. Redaction-gated. No repo, shell, or merge authority.</div>
    </header>
    <main id="log" aria-label="Foundups®Agent output scrollback">
      <div class="entry status"><span class="label">status</span>Foundups®Agent extension ${EXTENSION_VERSION} loaded.</div>
      <div class="entry status"><span class="label">status</span>OPENROUTER_API_KEY must be set in the environment used to launch Cursor. Do not paste secrets.</div>
    </main>
    <form id="form">
      <div id="reddogWorkingTrail" class="reddog-working-trail" aria-live="polite" aria-atomic="false">
        <span data-reddog-pixel>~~~</span>
        <span data-reddog-action>idle</span>
        <span data-reddog-elapsed></span>
      </div>
      <div class="toolbar">
        <label for="workerType">0102 Role</label><select id="workerType"><option value="reddog_architect" selected>RedDog Architect</option><option value="wsp_gate_critic">WSP Gate Critic</option><option value="repair_planner">Repair Planner</option><option value="smoke_tester">Smoke Test</option></select>
        <span class="pill">Routing: Auto via WSP_15</span>
        <span class="pill">Context: Auto WSP + HoloIndex + Skillz/Rolodex</span>
        <label for="testWorkFocus">Tests</label><select id="testWorkFocus"><option value="">Select test...</option><option value="regular">Regular smoke</option><option value="fusion">Fusion smoke</option><option value="wsp97">WSP_97 repo review</option><option value="reddog">RedDog architect review</option></select>
        <button id="copyMd" type="button">Copy MD</button>
      </div>
      <textarea id="workFocus" placeholder="Describe your work focus (012). 0102 converts this to a WSP task prompt for RedDog." aria-label="012 work focus"></textarea>
      <div class="hint">012 work focus: Enter sends. Shift+Enter adds a new line. Ctrl+Shift+C copies the redacted review packet.</div>
    </form>
  </div>
  <script>
    const vscode = acquireVsCodeApi();
    const TRAIL = ${reddogTrailWebviewBootstrapJson()};
    const form = document.getElementById('form');
    const workFocus = document.getElementById('workFocus');
    const workerType = document.getElementById('workerType');
    const testWorkFocus = document.getElementById('testWorkFocus');
    const copyMd = document.getElementById('copyMd');
    const trailEl = document.getElementById('reddogWorkingTrail');
    let lastAssistantMarkdown = '';
    const log = document.getElementById('log');
    let running = false;
    let startedAt = 0;
    let lastTrailUpdate = 0;
    let elapsedTimer = null;
    let idleCycleTimer = null;
    let sittingTimer = null;
    let terminalTimer = null;
    let idleFrame = 0;
    const idleFrames = ['~~~', '.rd.', '<rd>', '.rd.'];
    let currentTrailAction = 'idle';
    let currentTrailPixel = '~~~';

    function formatElapsed(ms) {
      const s = Math.floor(Math.max(0, ms) / 1000);
      if (s < 60) return s + 's';
      return Math.floor(s / 60) + 'm' + String(s % 60).padStart(2, '0') + 's';
    }

    function matchReddogProgressWeb(input) {
      const stage = input && input.stage ? String(input.stage) : '';
      const text = input && input.text ? String(input.text) : '';
      if (stage && TRAIL.stageActions[stage]) {
        return TRAIL.stageActions[stage];
      }
      for (const rule of TRAIL.progressActions) {
        if (rule.prefix && text.startsWith(rule.prefix)) {
          return { action: rule.action, pixel: rule.pixel };
        }
      }
      return null;
    }

    function updateReddogTrail(action, pixel, suffix, opts) {
      const pixelEl = trailEl.querySelector('[data-reddog-pixel]');
      const actionEl = trailEl.querySelector('[data-reddog-action]');
      const elapsedEl = trailEl.querySelector('[data-reddog-elapsed]');
      currentTrailAction = action;
      currentTrailPixel = pixel;
      pixelEl.textContent = pixel;
      actionEl.textContent = suffix ? action + ' ' + suffix : action;
      const elapsedMs = running && startedAt ? Date.now() - startedAt : 0;
      elapsedEl.textContent = running && elapsedMs > 0 ? formatElapsed(elapsedMs) : '';
      trailEl.removeAttribute('data-active');
      trailEl.removeAttribute('data-active-error');
      if (opts && opts.error) {
        trailEl.setAttribute('data-active', 'error');
      } else if (running || (opts && opts.active)) {
        trailEl.setAttribute('data-active', 'true');
      }
      lastTrailUpdate = Date.now();
    }

    function resetTrailIdle() {
      updateReddogTrail('idle', '~~~', '', {});
    }

    function clearTrailTimers() {
      if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }
      if (idleCycleTimer) { clearInterval(idleCycleTimer); idleCycleTimer = null; }
      if (sittingTimer) { clearInterval(sittingTimer); sittingTimer = null; }
    }

    function refreshTrailElapsed() {
      if (!running) return;
      const elapsedEl = trailEl.querySelector('[data-reddog-elapsed]');
      const elapsedMs = startedAt ? Date.now() - startedAt : 0;
      elapsedEl.textContent = elapsedMs > 0 ? formatElapsed(elapsedMs) : '';
    }

    function startTrailTimers() {
      clearTrailTimers();
      elapsedTimer = setInterval(refreshTrailElapsed, 1000);
      idleCycleTimer = setInterval(() => {
        if (!running || Date.now() - lastTrailUpdate < 2000) return;
        if (currentTrailAction === 'idle' || currentTrailPixel === '>rd>' || currentTrailPixel === '!rd!') return;
        idleFrame = (idleFrame + 1) % idleFrames.length;
        trailEl.querySelector('[data-reddog-pixel]').textContent = idleFrames[idleFrame];
      }, 800);
      sittingTimer = setInterval(() => {
        if (!running) return;
        if (Date.now() - lastTrailUpdate > 10000) {
          updateReddogTrail('sitting', '.rd.', '', { active: true });
        }
      }, 1000);
    }

    function applyProgressEvent(msg) {
      const matched = matchReddogProgressWeb({ stage: msg.stage, text: msg.text });
      if (matched) {
        updateReddogTrail(matched.action, matched.pixel, '', { active: true });
      }
    }

    function add(cls, text, label) {
      const el = document.createElement('div');
      el.className = 'entry ' + cls;
      const span = document.createElement('span');
      span.className = 'label';
      span.textContent = label || cls;
      el.appendChild(span);
      el.appendChild(document.createTextNode(text));
      log.appendChild(el);
      log.scrollTop = log.scrollHeight;
    }

    function elapsed() {
      return startedAt ? ' [' + Math.round((Date.now() - startedAt) / 1000) + 's]' : '';
    }

    function addStatus(text) {
      add('status', text + elapsed(), 'status');
    }

    function setRunning(value, result) {
      if (terminalTimer) {
        clearTimeout(terminalTimer);
        terminalTimer = null;
      }
      running = value;
      workFocus.disabled = value;
      workerType.disabled = value;
      testWorkFocus.disabled = value;
      copyMd.disabled = value;
      if (value) {
        startedAt = Date.now();
        lastTrailUpdate = Date.now();
        idleFrame = 0;
        applyProgressEvent({ stage: null, text: 'Work focus sent.' });
        startTrailTimers();
        return;
      }
      clearTrailTimers();
      let action = 'growling';
      let pixel = '!rd!';
      let suffix = 'stopped';
      let error = true;
      if (result && result.ok) {
        action = 'pointing';
        pixel = '>rd>';
        suffix = 'complete';
        error = false;
      } else if (result && result.reason === 'redaction_blocked') {
        action = 'barking';
        pixel = '!rd!';
        suffix = 'blocked';
        error = true;
      }
      updateReddogTrail(action, pixel, suffix, { error: error, active: false });
      terminalTimer = setTimeout(() => {
        if (!running) {
          resetTrailIdle();
        }
      }, TRAIL.terminalHoldMs);
    }

    testWorkFocus.addEventListener('change', () => {
      const value = testWorkFocus.value;
      if (value === 'regular') { workerType.value = 'smoke_tester'; workFocus.value = 'Reply with exactly: regular mode works'; }
      if (value === 'fusion') { workerType.value = 'smoke_tester'; workFocus.value = 'Fusion smoke test. Reply with one consensus, one contradiction, and one blind spot. Keep it under 80 words.'; }
      if (value === 'wsp97') { workerType.value = 'wsp_gate_critic'; workFocus.value = 'Apply WSP_00, WSP_97, and WSP_15 to the supplied context. Provide findings, evidence, proposed fixes, uncertainties, WSP_15 priority, and next safest step.'; }
      if (value === 'reddog') { workerType.value = 'reddog_architect'; workFocus.value = 'Operate as RedDog Architect. Review the supplied repo context as a FoundUps intake/orchestration surface. For each issue, propose the WSP-compliant fix path and end with WSP_15 priority.'; }
      testWorkFocus.value = '';
      workFocus.focus();
    });

    copyMd.addEventListener('click', () => {
      if (!lastAssistantMarkdown) { addStatus('No assistant markdown available to copy.'); return; }
      vscode.postMessage({ command: 'copyMarkdown', text: lastAssistantMarkdown });
    });

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      sendWorkFocus();
    });

    workFocus.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendWorkFocus();
      }
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 'c') {
        event.preventDefault();
        vscode.postMessage({ command: 'copyReview' });
      }
    });

    function sendWorkFocus() {
      const text = workFocus.value.trim();
      if (!text) return;
      if (running) {
        addStatus('A request is already running. Wait for the final response.');
        return;
      }
      setRunning(true);
      addStatus('Work focus sent. 0102 will assemble WSP task prompt...');
      add('user', text, '012 work focus');
      workFocus.value = '';
      vscode.postMessage({ command: 'ask', text, mode: 'auto', contextMode: 'auto', workerType: workerType.value, effort: 'auto' });
    }

    function failureText(result) {
      if (!result) return 'unknown';
      const parts = [result.reason || 'unknown'];
      if (result.status) parts.push('status=' + result.status);
      if (result.lead_model) parts.push('lead=' + result.lead_model);
      if (result.detail && result.detail !== result.reason) parts.push(result.detail);
      return parts.join(' | ');
    }

    window.addEventListener('message', (event) => {
      const msg = event.data;
      if (!msg) return;
      if (msg.command === 'status') addStatus(msg.text);
      if (msg.command === 'progress') applyProgressEvent(msg);
      if (msg.command === 'result') {
        setRunning(false, msg.result);
        const copyPayload = (msg.result && msg.result.copy_markdown) || (msg.result && msg.result.content) || '';
        lastAssistantMarkdown = copyPayload;
        if (msg.result && msg.result.ok) {
          addStatus('Complete: ' + (msg.result.mode || msg.result.model || 'ok'));
          const ov = msg.result.review_packet && msg.result.review_packet.output_validation;
          if (ov && (ov.output_validation_failed || (ov.repair_attempted && !ov.validated))) {
            add('error', 'OUTPUT_VALIDATION_FAILED: advisory output incomplete. See Copy MD for Run Trace and missing sections.', 'validation');
          }
          add('assistant', msg.result.content || '', '0102 output');
        } else if (msg.result && msg.result.reason === 'redaction_blocked') {
          addStatus(TRAIL.operatorMessage);
          add('error', TRAIL.operatorMessage, 'error');
        } else {
          const failure = failureText(msg.result);
          addStatus('Stopped: ' + failure);
          add('error', 'Blocked/failed: ' + failure, 'error');
        }
        workFocus.focus();
      }
    });
  </script>
</body>
</html>`;
}

function failureText(result) {
  if (!result) {
    return 'unknown';
  }
  const parts = [result.reason || 'unknown'];
  if (result.status) {
    parts.push('status=' + result.status);
  }
  if (result.lead_model) {
    parts.push('lead=' + result.lead_model);
  }
  if (result.detail && result.detail !== result.reason) {
    parts.push(result.detail);
  }
  return parts.join(' | ');
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function shouldAcceptBridgeCompletion(settled, state) {
  return !settled && !(state && state.disposed);
}

function deactivate() {}

module.exports = {
  activate,
  deactivate,
  classifyTaskForRedDog,
  resolveAutoEffort,
  resolveAutoContextMode,
  resolveModelMode,
  validateRedDogOutput,
  buildRepairPrompt,
  constructWspTaskPrompt,
  redactedDigest,
  resolvePythonInterpreter,
  applyBridgeContextBudget,
  killBridgeChild,
  bridgeStreamCapExceeded,
  shouldAcceptBridgeCompletion,
  BRIDGE_MAX_CONTEXT_CHARS,
  BRIDGE_MAX_PROMPT_CHARS,
  BRIDGE_MAX_STDOUT_BYTES,
  BRIDGE_MAX_STDERR_BYTES,
  modeSelectionReasoning,
  skillzWardrobeRolodexContext,
  buildBoundedRepoContext,
  REDDOG_REQUIRED_OUTPUT_SECTIONS,
  formatElapsed,
  matchReddogProgress,
  REDDOG_STAGE_ACTIONS,
  REDDOG_PROGRESS_ACTIONS,
  REDDOG_TERMINAL_HOLD_MS,
  REDACTION_BLOCK_OPERATOR_MESSAGE,
  ADVISORY_BRIDGE_STAGES,
  enrichRedactionBlockResult,
  detectMojibake,
  buildRunTraceSection,
  buildWorkTrailSection,
  buildCopyMarkdown,
  appendValidationFailureContent,
  formatOutputValidationStatus,
  sanitizeCopyMdText,
  createWorkTrail,
  buildRedactionGateReport,
  buildRedactionGateReportSection,
  buildGovernedHandoffRecommendation,
  buildGovernedHandoffSection,
  compositePayloadDigest,
  extractHoloIndexScorecard,
  MOJIBAKE_MARKERS,
  WORK_TRAIL_MAX_EVENTS,
  VALIDATION_FAILED_FOOTER
};
