const vscode = require('vscode');
const cp = require('child_process');
const crypto = require('crypto');
const path = require('path');
const fs = require('fs');

const EXTENSION_VERSION = '0.3.31';
const UNICODE_SURROGATE_PLACEHOLDER = '[MALFORMED_SURROGATE]';
const TARGET_READ_BLOCKED_SEGMENTS = ['.git', 'node_modules', '__pycache__', '.venv'];
const TARGET_READ_BLOCKED_BASENAMES = ['.env'];
const TARGET_READ_BLOCKED_EXTENSIONS = ['.vsix'];
const TARGET_SNIPPET_MAX_FILE_BYTES = 500000;
const TARGET_SNIPPET_DEFAULT_CHARS = 16000;
const WSP97_EXCERPT_MAX_CHARS = 4096;
const WSP97_PROTOCOL_REL_PATH = 'WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md';
// Mirrors fusion_redaction_gate.py BLOCK categories only (policy v1). Do not weaken Python gate.
const TARGET_SNIPPET_BLOCK_SANITIZERS = [
  ['private_key_residual', /-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----/gi],
  ['private_reasoning', /(?:<\s*think(?:ing)?\b|<\/\s*think|<\s*scratchpad|chain[\s_\-]?of[\s_\-]?thought|hidden[\s_\-]+chain[\s_\-]?of[\s_\-]?thought|hidden[\s_\-]?reasoning|private[\s_\-]?reasoning)/gi],
  ['merge_authorization', /\b(?:pull_request_merge|merge[\s_\-]?token|auto[\s_\-]?merge[\s_\-]?token|merge[\s_\-]?authoriz\w*)\b/gi],
  ['source_authority', /\bsource[\s_\-]?authority\b/gi],
  ['cabr_payout_authority', /\b(?:cabr[\s_\-]?ready|cabr[\s_\-]?payout|payout[\s_\-]?ready|payout[\s_\-]?routing|benefit[\s_\-]?routing|route[\s_\-]?payouts|capability_token\w*)\b/gi],
  ['governance_instruction', /\b(?:internal[\s_\-]?governance|governance[\s_\-]?instruction|redaction_gate_(?:passed|blocked|started)|gate[\s_\-]?passed|grant[\s_\-]?authority)\b/gi]
];
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
  'repair_redaction_started',
  'repair_redaction_passed',
  'repair_redaction_blocked',
  'repair_single_started',
  'repair_single_done',
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

const BRIDGE_REPAIR_STAGE_WORK_TRAIL = {
  bridge_start: 'repair_started',
  env_check: 'repair_started',
  redaction_start: 'repair_redaction_started',
  redaction_blocked: 'repair_redaction_blocked',
  redaction_pass: 'repair_redaction_passed',
  single_start: 'repair_single_started',
  single_done: 'repair_single_done',
  lead_start: 'repair_single_started',
  lead_done: 'repair_single_done',
  panel_start: 'repair_single_started',
  panel_done: 'repair_single_started',
  synthesis_start: 'repair_single_started',
  synthesis_done: 'repair_single_started'
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

function normalizeRepairBridgeStageToWorkTrail(stage, text) {
  const stageName = stage ? String(stage) : '';
  if (stageName && BRIDGE_REPAIR_STAGE_WORK_TRAIL[stageName]) {
    return { event: BRIDGE_REPAIR_STAGE_WORK_TRAIL[stageName], detail: sanitizeCopyMdText(text) };
  }
  return null;
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
    provider_reasoning_note: 'Report-only in v0.3.23; bridge does not confirm provider reasoning application.'
  };
}

// Self-file guard: retrieving RedDog itself (or the module-under-audit shell)
// must never count toward required-target recall. This was the false-positive
// source in REDDOG_HOLOINDEX_INDEX_GAP_ARCHITECT_REVIEW_PHASE1 where retrieving
// extension.js falsely satisfied the recall check.
const TARGET_RECALL_SELF_FILE_BASENAMES = ['extension.js'];
const TARGET_RECALL_SELF_FILE_PATHS = ['extensions/foundups_advisory_workers/extension.js'];

// Header lines that introduce an explicit required-direct-read-target list in a
// 012 work focus / prompt. Matched case-insensitively; list items follow until a
// blank line or a non-list line.
const REQUIRED_TARGET_HEADER_PATTERNS = [
  /required\s+direct[\s_-]?read\s+targets?/i,
  /required\s+read\s+targets?/i,
  /direct[\s_-]?read\s+targets?\s*(?:\(required\))?/i
];

function normalizeTargetPath(raw) {
  return String(raw || '')
    .replace(/\\/g, '/')
    .replace(/^[`'"(\[]+/, '')
    .replace(/[`'")\].,;:]+$/, '')
    .trim();
}

// Extract repo-relative path/glob tokens from a single list line. A line may hold
// one path or a slash-delimited "a / b / c" alternatives list (as prompts often
// phrase them). Symbol tokens (symbol:foo) are preserved verbatim.
function extractTargetTokensFromLine(line) {
  const tokens = [];
  const body = normalizeTargetPath(line);
  if (!body) {
    return tokens;
  }
  if (/^symbol:/i.test(body)) {
    tokens.push('symbol:' + body.slice(7).trim());
    return tokens;
  }
  // Split on whitespace-padded slashes used as "or" separators, or on commas,
  // while keeping intra-path slashes intact (those have no surrounding spaces).
  const parts = body.split(/\s*(?:,|\s\/\s|\bor\b)\s*/i);
  for (const part of parts) {
    const candidate = normalizeTargetPath(part);
    if (!candidate) {
      continue;
    }
    // A target must look like a path/glob or a bare source filename.
    if (/[\/]/.test(candidate) || /\.[a-z0-9]{1,6}$/i.test(candidate) || /[*?]/.test(candidate)) {
      tokens.push(candidate);
    }
  }
  return tokens;
}

// Parse an explicit "Required direct-read targets" section from prompt text into
// a de-duplicated list of repo-relative paths/globs. Returns [] when no such
// section is present (backward compatible: callers then fall back to inference).
function parseRequiredTargetPaths(taskText) {
  const text = String(taskText || '');
  const lines = text.split(/\r?\n/);
  const targets = [];
  const seen = new Set();
  let capturing = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const stripped = line.trim();
    if (!capturing) {
      if (REQUIRED_TARGET_HEADER_PATTERNS.some((pattern) => pattern.test(stripped))) {
        capturing = true;
        // Header may itself carry inline targets after a colon.
        const colonIdx = stripped.indexOf(':');
        if (colonIdx !== -1) {
          const inline = stripped.slice(colonIdx + 1);
          for (const token of extractTargetTokensFromLine(inline)) {
            const norm = token.toLowerCase();
            if (!seen.has(norm)) {
              seen.add(norm);
              targets.push(token);
            }
          }
        }
      }
      continue;
    }
    // Capturing mode: stop at a blank line (end of list block).
    if (!stripped) {
      break;
    }
    // Only consume list-style lines (-, *, digit., or bare path). Stop if a new
    // prose header appears before any list content is a paragraph, not a target.
    const listMatch = stripped.match(/^(?:[-*+]|\d+[.)])\s+(.*)$/);
    const itemText = listMatch ? listMatch[1] : stripped;
    const tokens = extractTargetTokensFromLine(itemText);
    if (!tokens.length) {
      // A non-list, non-path line ends the section.
      if (!listMatch) {
        break;
      }
      continue;
    }
    for (const token of tokens) {
      const norm = token.toLowerCase();
      if (!seen.has(norm)) {
        seen.add(norm);
        targets.push(token);
      }
    }
  }
  return targets;
}

function isSelfFileLocation(location) {
  const loc = String(location || '').replace(/\\/g, '/').toLowerCase();
  if (!loc) {
    return false;
  }
  if (TARGET_RECALL_SELF_FILE_PATHS.some((p) => loc === p.toLowerCase() || loc.endsWith('/' + p.toLowerCase()))) {
    return true;
  }
  const base = loc.split('/').pop();
  return TARGET_RECALL_SELF_FILE_BASENAMES.includes(base);
}

function inferRecallTargetPaths(taskText) {
  const task = String(taskText || '').toLowerCase();
  const targets = [];
  if (/extension\.js|foundups.*agent|copy md|run trace|work trail|buildcopymarkdown|reddog.*extension/.test(task)) {
    targets.push('extensions/foundups_advisory_workers/extension.js');
  }
  if (/buildcopymarkdown/.test(task)) {
    targets.push('symbol:buildCopyMarkdown');
  }
  if (/advisory_model_once|openrouter bridge|redaction gate bridge/.test(task)) {
    targets.push('scripts/advisory_model_once.py');
  }
  if (/acceptance baseline|ext-acc|external acceptance/.test(task)) {
    targets.push('extensions/foundups_advisory_workers/docs/REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md');
  }
  return targets;
}

// Match a required repo-relative path/glob against the content-bearing locations
// actually present in the bundle. Self-file locations are excluded by the caller
// before this runs so retrieving RedDog itself cannot satisfy a required target.
function requiredTargetMatchesLocation(target, location) {
  const want = normalizeTargetPath(target).toLowerCase();
  const have = String(location || '').replace(/\\/g, '/').toLowerCase();
  if (!want || !have) {
    return false;
  }
  if (have === want) {
    return true;
  }
  // Glob support: translate * and ? to a bounded regex (path-segment safe).
  if (/[*?]/.test(want)) {
    const escaped = want.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '[^/]*').replace(/\?/g, '[^/]');
    const re = new RegExp('(^|/)' + escaped + '$');
    return re.test(have);
  }
  // Basename fallback only when the required token is a bare filename (no dir),
  // so a required directoried path is not satisfied by an unrelated same-name file.
  if (!want.includes('/')) {
    return have.split('/').pop() === want;
  }
  return have.endsWith('/' + want);
}

function evaluateTargetRecall(taskText, bundleData) {
  const hits = bundleData && bundleData.task_retrieval && Array.isArray(bundleData.task_retrieval.code_hits)
    ? bundleData.task_retrieval.code_hits
    : [];
  const locations = hits.map((h) => String(h.location || '').replace(/\\/g, '/').toLowerCase());
  const needs = hits.map((h) => String(h.need || '').toLowerCase());

  // Slice 1: an explicit "Required direct-read targets" list, when present, is the
  // authoritative recall contract. Compare each required path against content-bearing
  // locations, excluding self-file hits (extension.js / module-under-audit shell).
  const required = parseRequiredTargetPaths(taskText);
  if (required.length) {
    const contentLocations = locations.filter((loc) => !isSelfFileLocation(loc));
    const missing = [];
    let recalled = 0;
    for (const target of required) {
      let found = false;
      if (target.startsWith('symbol:')) {
        // Symbols cannot be honestly resolved from a path-only bundle; a symbol in
        // a required list is only satisfied by a non-self content location whose
        // need/location names it. It must NOT be satisfied by the self-file.
        const symbol = target.slice(7).toLowerCase();
        found = hits.some((h) => {
          const loc = String(h.location || '').replace(/\\/g, '/').toLowerCase();
          if (isSelfFileLocation(loc)) {
            return false;
          }
          return String(h.need || '').toLowerCase().includes(symbol);
        });
      } else {
        found = contentLocations.some((loc) => requiredTargetMatchesLocation(target, loc));
      }
      if (found) {
        recalled += 1;
      } else {
        missing.push(target);
      }
    }
    return {
      target_recall_ok: missing.length === 0,
      index_gap_detected: missing.length > 0,
      recall_targets: required,
      required_targets_total: required.length,
      required_targets_recalled: recalled,
      required_targets_missing: missing
    };
  }

  // Backward-compatible inference path (no explicit required list in prompt).
  const targets = inferRecallTargetPaths(taskText);
  if (!targets.length) {
    return {
      target_recall_ok: 'unknown',
      index_gap_detected: false,
      recall_targets: [],
      required_targets_total: 0,
      required_targets_recalled: 0,
      required_targets_missing: []
    };
  }
  let allFound = true;
  for (const target of targets) {
    if (target.startsWith('symbol:')) {
      const symbol = target.slice(7).toLowerCase();
      const symbolHit = needs.some((n) => n.includes(symbol)) || locations.some((loc) => loc.endsWith('extension.js'));
      if (!symbolHit) {
        allFound = false;
      }
      continue;
    }
    const normalized = target.toLowerCase();
    if (!locations.some((loc) => loc === normalized || loc.endsWith('/' + normalized.split('/').pop()))) {
      allFound = false;
    }
  }
  return {
    target_recall_ok: allFound,
    index_gap_detected: !allFound,
    recall_targets: targets,
    required_targets_total: 0,
    required_targets_recalled: 0,
    required_targets_missing: []
  };
}

function extractHoloIndexScorecard(contextMode, holoMeta) {
  if (!contextMode || !String(contextMode).includes('holo')) {
    return null;
  }
  const meta = holoMeta && typeof holoMeta === 'object' ? holoMeta : {};
  return {
    holoindex_status: meta.holoindex_status || 'unknown',
    code_hits_count: meta.code_hits !== undefined ? meta.code_hits : 'unknown',
    wsp_hits: meta.wsp_hits !== undefined ? meta.wsp_hits : 'unknown',
    code_hits: meta.code_hits !== undefined ? meta.code_hits : 'unknown',
    skill_hits: meta.skill_hits !== undefined ? meta.skill_hits : 'unknown',
    target_recall_ok: meta.target_recall_ok !== undefined ? meta.target_recall_ok : 'unknown',
    index_gap_detected: meta.index_gap_detected !== undefined ? meta.index_gap_detected : 'unknown',
    required_targets_total: meta.required_targets_total !== undefined ? meta.required_targets_total : 'unknown',
    required_targets_recalled: meta.required_targets_recalled !== undefined ? meta.required_targets_recalled : 'unknown',
    required_targets_missing: Array.isArray(meta.required_targets_missing) ? meta.required_targets_missing : 'unknown',
    direct_read_fallback_used: meta.direct_read_fallback_used !== undefined ? meta.direct_read_fallback_used : 'unknown',
    direct_read_paths: Array.isArray(meta.direct_read_paths) ? meta.direct_read_paths : 'unknown',
    direct_read_rejected: Array.isArray(meta.direct_read_rejected) ? meta.direct_read_rejected : 'unknown',
    direct_read_bytes: meta.direct_read_bytes !== undefined ? meta.direct_read_bytes : 'unknown',
    direct_read_truncated: Array.isArray(meta.direct_read_truncated) ? meta.direct_read_truncated : 'unknown',
    target_content_included: meta.target_content_included !== undefined ? meta.target_content_included : 'unknown',
    target_content_paths: Array.isArray(meta.target_content_paths) ? meta.target_content_paths : 'unknown',
    target_content_chars: meta.target_content_chars !== undefined ? meta.target_content_chars : 'unknown',
    target_content_omitted_reason: meta.target_content_omitted_reason !== undefined ? meta.target_content_omitted_reason : 'unknown',
    target_content_truncated: meta.target_content_truncated !== undefined ? meta.target_content_truncated : 'unknown',
    target_content_sanitized: meta.target_content_sanitized !== undefined ? meta.target_content_sanitized : 'unknown',
    target_content_sanitized_categories: Array.isArray(meta.target_content_sanitized_categories)
      ? meta.target_content_sanitized_categories
      : 'unknown'
  };
}

function formatHoloIndexScorecardLines(scorecard) {
  if (!scorecard) {
    return [];
  }
  return [
    '- holoindex_status: ' + scorecard.holoindex_status,
    '- code_hits_count: ' + scorecard.code_hits_count,
    '- wsp_hits: ' + scorecard.wsp_hits,
    '- skill_hits: ' + scorecard.skill_hits,
    '- target_recall_ok: ' + scorecard.target_recall_ok,
    '- index_gap_detected: ' + scorecard.index_gap_detected,
    '- required_targets_total: ' + scorecard.required_targets_total,
    '- required_targets_recalled: ' + scorecard.required_targets_recalled,
    '- required_targets_missing: ' + (Array.isArray(scorecard.required_targets_missing) ? (scorecard.required_targets_missing.length ? scorecard.required_targets_missing.join(', ') : '(none)') : scorecard.required_targets_missing),
    '- direct_read_fallback_used: ' + scorecard.direct_read_fallback_used,
    '- direct_read_paths: ' + (Array.isArray(scorecard.direct_read_paths) ? (scorecard.direct_read_paths.length ? scorecard.direct_read_paths.join(', ') : '(none)') : scorecard.direct_read_paths),
    '- direct_read_rejected: ' + (Array.isArray(scorecard.direct_read_rejected) ? (scorecard.direct_read_rejected.length ? scorecard.direct_read_rejected.map((r) => (r && r.path ? r.path + ' (' + r.reason + ')' : String(r))).join(', ') : '(none)') : scorecard.direct_read_rejected),
    '- direct_read_bytes: ' + scorecard.direct_read_bytes,
    '- direct_read_truncated: ' + (Array.isArray(scorecard.direct_read_truncated) ? (scorecard.direct_read_truncated.length ? scorecard.direct_read_truncated.map((t) => (t && t.path ? t.path + ' (' + t.bytes + 'B)' : String(t))).join(', ') : '(none)') : scorecard.direct_read_truncated),
    '- target_content_included: ' + scorecard.target_content_included,
    '- target_content_paths: ' + (Array.isArray(scorecard.target_content_paths) ? scorecard.target_content_paths.join(', ') : scorecard.target_content_paths),
    '- target_content_chars: ' + scorecard.target_content_chars,
    '- target_content_omitted_reason: ' + scorecard.target_content_omitted_reason,
    '- target_content_truncated: ' + scorecard.target_content_truncated,
    '- target_content_sanitized: ' + scorecard.target_content_sanitized,
    '- target_content_sanitized_categories: ' + (Array.isArray(scorecard.target_content_sanitized_categories)
      ? scorecard.target_content_sanitized_categories.join(', ')
      : scorecard.target_content_sanitized_categories)
  ];
}

function normalizeBridgeTextForUnicode(text, sourceLabel) {
  const source = typeof sourceLabel === 'string' && sourceLabel.length ? sourceLabel : 'unknown';
  const input = String(text || '');
  let replacements = 0;
  let stripped = '';
  for (let i = 0; i < input.length; i++) {
    const code = input.charCodeAt(i);
    if (code >= 0xD800 && code <= 0xDBFF) {
      if (i + 1 < input.length) {
        const next = input.charCodeAt(i + 1);
        if (next >= 0xDC00 && next <= 0xDFFF) {
          stripped += input[i] + input[i + 1];
          i += 1;
          continue;
        }
      }
      stripped += UNICODE_SURROGATE_PLACEHOLDER;
      replacements += 1;
    } else if (code >= 0xDC00 && code <= 0xDFFF) {
      stripped += UNICODE_SURROGATE_PLACEHOLDER;
      replacements += 1;
    } else {
      stripped += input[i];
    }
  }
  let normalized = stripped;
  let form = 'none';
  try {
    normalized = stripped.normalize('NFC');
    form = 'NFC';
  } catch (err) {
    normalized = stripped;
  }
  return {
    text: normalized,
    unicode_normalization_applied: replacements > 0,
    unicode_replacements_count: replacements,
    unicode_normalization_source: source,
    unicode_normalization_form: form
  };
}

function emptyUnicodeNormalizationMeta() {
  return {
    unicode_normalization_applied: false,
    unicode_replacements_count: 0,
    unicode_normalization_sources: '',
    unicode_normalization_form: 'none'
  };
}

function mergeUnicodeNormalizationMeta(existing, incoming) {
  const base = existing && typeof existing === 'object' ? existing : emptyUnicodeNormalizationMeta();
  if (!incoming || typeof incoming !== 'object') {
    return base;
  }
  const sources = new Set(String(base.unicode_normalization_sources || '').split('|').filter(Boolean));
  if (incoming.unicode_normalization_source) {
    sources.add(String(incoming.unicode_normalization_source));
  }
  if (Array.isArray(incoming.unicode_normalization_sources)) {
    incoming.unicode_normalization_sources.forEach((item) => {
      if (item) {
        sources.add(String(item));
      }
    });
  } else if (typeof incoming.unicode_normalization_sources === 'string' && incoming.unicode_normalization_sources) {
    incoming.unicode_normalization_sources.split('|').filter(Boolean).forEach((item) => sources.add(item));
  }
  const replacementDelta = typeof incoming.unicode_replacements_count === 'number' ? incoming.unicode_replacements_count : 0;
  const applied = base.unicode_normalization_applied === true
    || incoming.unicode_normalization_applied === true
    || replacementDelta > 0;
  const form = incoming.unicode_normalization_form && incoming.unicode_normalization_form !== 'none'
    ? incoming.unicode_normalization_form
    : base.unicode_normalization_form || 'none';
  return {
    unicode_normalization_applied: applied,
    unicode_replacements_count: (base.unicode_replacements_count || 0) + replacementDelta,
    unicode_normalization_sources: Array.from(sources).sort().join('|'),
    unicode_normalization_form: form
  };
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
  lines.push('- unicode_normalization_applied: ' + (rp.unicode_normalization_applied === true ? 'true' : rp.unicode_normalization_applied === false ? 'false' : 'unknown'));
  lines.push('- unicode_replacements_count: ' + (typeof rp.unicode_replacements_count === 'number' ? rp.unicode_replacements_count : 'unknown'));
  lines.push('- unicode_normalization_sources: ' + (typeof rp.unicode_normalization_sources === 'string' && rp.unicode_normalization_sources.length ? rp.unicode_normalization_sources : '(none)'));
  lines.push('- unicode_normalization_form: ' + (rp.unicode_normalization_form || 'none'));
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
  if (rp.output_validation && rp.output_validation.repair_attempted) {
    lines.push('- repair_context_mode: ' + (rp.output_validation.repair_context_mode || 'unknown'));
    lines.push('- repair_mode: ' + (rp.output_validation.repair_mode || 'unknown'));
    if (Array.isArray(rp.output_validation.missing_sections_after_repair) && rp.output_validation.missing_sections_after_repair.length) {
      lines.push('- missing_sections_after_repair: ' + rp.output_validation.missing_sections_after_repair.join(', '));
    }
  }
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
  if (ctx.continuationSummary) {
    sections.push(buildContinuationSummaryCopySection(ctx.continuationSummary));
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
    return 'wsp_holo';
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
    if (tier === 'REGULAR') {
      return 'Single-model GLM principal: REGULAR-tier work; HoloIndex-grounded wsp_holo (no Fusion panel, Skillz, or git); context=' + resolvedContextMode + '.';
    }
    return 'Single-model GLM principal: smoke-classified work; avoids panel latency/cost; context=' + resolvedContextMode + '.';
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

const CONTINUATION_FIELD_MAX_CHARS = 480;
const CONTINUATION_TOTAL_MAX_CHARS = 3200;
const CONTINUATION_SECRET_PATTERNS = [
  /\bghp_[A-Za-z0-9_]+\b/g,
  /\bgithub_pat_[A-Za-z0-9_]+\b/g,
  /\bgho_[A-Za-z0-9_]+\b/g,
  /\bsk-[A-Za-z0-9_]+\b/gi,
  /Bearer\s+[A-Za-z0-9._-]+/gi
];

function sanitizeContinuationField(text, maxChars) {
  const limit = maxChars || CONTINUATION_FIELD_MAX_CHARS;
  let out = sanitizeCopyMdText(String(text || ''));
  const sanitized = sanitizeTargetSnippetForRedaction(out);
  out = sanitized.text;
  for (const pattern of CONTINUATION_SECRET_PATTERNS) {
    out = out.replace(pattern, '[REDACTED_SECRET]');
  }
  out = out.replace(/\s+/g, ' ').trim();
  if (out.length > limit) {
    out = out.slice(0, limit) + '...[truncated]';
  }
  return out;
}

function extractContinuationRefs(text) {
  const src = String(text || '');
  const prRefs = [];
  const prSeen = new Set();
  let match;
  const prPattern = /#(\d{1,5})\b/g;
  while ((match = prPattern.exec(src)) !== null) {
    const label = '#' + match[1];
    if (!prSeen.has(label)) {
      prSeen.add(label);
      prRefs.push(label);
    }
  }
  const commitRefs = [];
  const commitSeen = new Set();
  const commitPattern = /\b(?:commit|landed|merge|sha)[:\s]+([0-9a-f]{7,40})\b/gi;
  while ((match = commitPattern.exec(src)) !== null) {
    const hash = match[1].toLowerCase();
    if (!commitSeen.has(hash)) {
      commitSeen.add(hash);
      commitRefs.push(hash);
    }
  }
  return { pr_refs: prRefs.slice(0, 8), commit_refs: commitRefs.slice(0, 4) };
}

function extractResidualSpecifiedNotImplemented(text) {
  const src = String(text || '');
  const lines = src.split('\n');
  const hits = [];
  for (const line of lines) {
    if (/SPECIFIED_NOT_IMPLEMENTED/i.test(line)) {
      hits.push(sanitizeContinuationField(line, 160));
    }
  }
  if (!hits.length && /specified[- ]not[- ]implemented/i.test(src)) {
    hits.push('SPECIFIED_NOT_IMPLEMENTED mentioned in prior run (details omitted).');
  }
  return hits.slice(0, 6).join(' | ');
}

function continuationPreviousRunId(reviewPacket, promptConstruction, timestamp) {
  const rp = reviewPacket && typeof reviewPacket === 'object' ? reviewPacket : {};
  const parts = [
    String(timestamp || ''),
    rp.work_focus_digest || '',
    rp.wsp_prompt_digest || '',
    rp.resolved_mode || '',
    rp.resolved_context || ''
  ];
  return 'run_' + crypto.createHash('sha256').update(parts.join('|'), 'utf8').digest('hex').slice(0, 16);
}

function buildSanitizedContinuationSummary(params) {
  const p = params && typeof params === 'object' ? params : {};
  const reviewPacket = p.review_packet && typeof p.review_packet === 'object' ? p.review_packet : {};
  const cls = reviewPacket.task_classification && typeof reviewPacket.task_classification === 'object'
    ? reviewPacket.task_classification
    : (p.classification && typeof p.classification === 'object' ? p.classification : {});
  const workerType = cleanWorkerType(p.workerType || reviewPacket.worker_type || 'reddog_architect');
  const workerLabel = WORKER_TYPES[workerType] ? WORKER_TYPES[workerType].label : workerType;
  const timestamp = p.timestamp || new Date().toISOString();
  const blocked = p.blocked === true || p.reason === 'redaction_blocked';
  const base = {
    previous_run_id: continuationPreviousRunId(reviewPacket, p.promptConstruction, timestamp),
    timestamp: timestamp,
    role_0102: workerLabel,
    wsp15_tier: cls.tier || reviewPacket.resolved_effort || 'unknown',
    mode: reviewPacket.resolved_mode || p.mode || 'unknown',
    context_mode: reviewPacket.resolved_context || p.contextMode || 'unknown',
    blocked_locally: blocked,
    source: blocked ? 'blocked_locally' : 'successful_run',
    pr_refs: [],
    commit_refs: []
  };

  if (blocked) {
    const report = p.redaction_gate_report && typeof p.redaction_gate_report === 'object'
      ? p.redaction_gate_report
      : (reviewPacket.redaction_gate_report && typeof reviewPacket.redaction_gate_report === 'object'
        ? reviewPacket.redaction_gate_report
        : buildRedactionGateReport(p.result || p, p.promptConstruction, p.contextMode));
    base.decision_summary = 'BLOCKED_LOCALLY before OpenRouter';
    base.findings_summary = sanitizeContinuationField(report.safe_summary || 'Redaction gate blocked egress.', 320);
    base.wsp97_labels_summary = sanitizeContinuationField(
      report.truth_labels ? JSON.stringify(report.truth_labels) : 'blocked_stage: OBSERVED',
      240
    );
    base.wsp15_priorities_summary = 'none (blocked locally)';
    base.next_safest_step = sanitizeContinuationField(
      'Review blocked context locally. next_safe_context: ' + (report.next_safe_context || 'local_0102_review'),
      240
    );
    base.residual_specified_not_implemented = 'Prior run blocked; no architect output to carry forward.';
    base.redaction_gate_summary = sanitizeContinuationField(
      'rule_classes: ' + JSON.stringify(report.rule_classes || ['unknown'])
        + '; blocked_stage: ' + (report.blocked_stage || 'pre_openrouter_request'),
      320
    );
    return base;
  }

  const content = String(p.content || '');
  base.decision_summary = sanitizeContinuationField(extractMarkdownSection(content, 'Decision'), 360);
  base.findings_summary = sanitizeContinuationField(extractMarkdownSection(content, 'Findings'), 360);
  base.wsp97_labels_summary = sanitizeContinuationField(extractMarkdownSection(content, 'WSP_97 Truth Labels'), 360);
  base.wsp15_priorities_summary = sanitizeContinuationField(extractMarkdownSection(content, 'WSP_15 Priority'), 360);
  base.next_safest_step = sanitizeContinuationField(extractMarkdownSection(content, 'Next safest step'), 360);
  base.residual_specified_not_implemented = sanitizeContinuationField(
    extractResidualSpecifiedNotImplemented(content),
    360
  );
  const refs = extractContinuationRefs(content);
  base.pr_refs = refs.pr_refs;
  base.commit_refs = refs.commit_refs;
  base.redaction_gate_summary = null;
  if (!base.decision_summary) {
    base.decision_summary = sanitizeContinuationField('Prior run completed; decision section not extracted.', 160);
  }
  return base;
}

function formatContinuationSummaryBlock(summary) {
  const s = summary && typeof summary === 'object' ? summary : {};
  const lines = [
    '## Continuation from last RedDog packet (WSP_97-safe summary; not raw Copy MD)',
    '- previous_run_id: ' + (s.previous_run_id || 'unknown'),
    '- timestamp: ' + (s.timestamp || 'unknown'),
    '- 0102 role: ' + (s.role_0102 || 'unknown'),
    '- WSP_15 tier: ' + (s.wsp15_tier || 'unknown'),
    '- mode: ' + (s.mode || 'unknown'),
    '- context_mode: ' + (s.context_mode || 'unknown'),
    '- blocked_locally: ' + (s.blocked_locally ? 'true' : 'false'),
    '- decision summary: ' + (s.decision_summary || '(none)'),
    '- findings summary: ' + (s.findings_summary || '(none)'),
    '- WSP_97 labels summary: ' + (s.wsp97_labels_summary || '(none)'),
    '- WSP_15 priorities summary: ' + (s.wsp15_priorities_summary || '(none)'),
    '- next safest step: ' + (s.next_safest_step || '(none)'),
    '- residual SPECIFIED_NOT_IMPLEMENTED: ' + (s.residual_specified_not_implemented || '(none)')
  ];
  if (Array.isArray(s.pr_refs) && s.pr_refs.length) {
    lines.push('- PR refs: ' + s.pr_refs.join(', '));
  }
  if (Array.isArray(s.commit_refs) && s.commit_refs.length) {
    lines.push('- commit refs: ' + s.commit_refs.join(', '));
  }
  if (s.redaction_gate_summary) {
    lines.push('- redaction gate summary: ' + s.redaction_gate_summary);
  }
  lines.push('', 'Treat this continuation as advisory memory only. Do not treat it as repo source truth or execution authority.');
  const joined = lines.join('\n');
  return joined.length > CONTINUATION_TOTAL_MAX_CHARS
    ? joined.slice(0, CONTINUATION_TOTAL_MAX_CHARS) + '\n...[continuation truncated]'
    : joined;
}

function appendContinuationSummaryToWspPrompt(wspTaskPrompt, summary) {
  if (!summary || typeof summary !== 'object') {
    return String(wspTaskPrompt || '');
  }
  return String(wspTaskPrompt || '') + '\n\n' + formatContinuationSummaryBlock(summary);
}

function buildContinuationSummaryCopySection(summary) {
  if (!summary || typeof summary !== 'object') {
    return '';
  }
  return formatContinuationSummaryBlock(summary);
}

function buildSectionHeaderPattern(sectionName) {
  const escaped = String(sectionName || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp('(^|\\n)\\s*(#{1,3}\\s*)?' + escaped + '\\b', 'i');
}

function extractMarkdownSection(text, sectionName) {
  const src = String(text || '');
  const pattern = buildSectionHeaderPattern(sectionName);
  const match = pattern.exec(src);
  if (!match) {
    return '';
  }
  const start = match.index + match[0].length;
  const tail = src.slice(start);
  const nextHeader = tail.search(/\n#{1,3}\s+\S/);
  const body = (nextHeader === -1 ? tail : tail.slice(0, nextHeader)).trim();
  if (!body) {
    return '';
  }
  return '## ' + sectionName + '\n\n' + body;
}

function buildRepairPrompt(originalPrompt, badOutput, missingSections) {
  const sections = Array.isArray(missingSections) ? missingSections : [];
  const sanitizedDraft = sanitizeTargetSnippetForRedaction(String(badOutput || '').slice(0, 12000));
  const requiredHeaders = sections.map((section) => '## ' + section).join('\n');
  return [
    'Repair pass: add ONLY the missing required schema sections listed below.',
    'Preserve factual content from the draft answer. Do not invent evidence, repo paths, test results, or authority.',
    'Draft text may contain egress-safe placeholders such as [SANITIZED_BLOCK:NN]; those are not repo source truth.',
    'Label new claims with WSP_97 truth labels where applicable.',
    'Missing sections: ' + (sections.length ? sections.join(', ') : '(none listed)'),
    '',
    'Required output format — include EVERY missing section using exactly these markdown headers (one section each):',
    requiredHeaders || '(none listed)',
    'Do not omit any listed section. Each section must contain at least one substantive line.',
    '',
    'Original WSP task prompt (bounded excerpt):',
    String(originalPrompt || '').slice(0, 2000),
    '',
    'Draft answer to repair (sanitized for redaction gate):',
    sanitizedDraft.text
  ].join('\n');
}

function buildRepairBoundedContext() {
  return [
    '## REPAIR_PASS_BOUNDED_CONTEXT',
    'Schema repair pass only. Full repo/HoloIndex context was consumed in the primary advisory pass.',
    'Do not treat this packet as fresh repo evidence. Complete missing schema sections from the draft in the user prompt.',
    'Target recall snippets may contain egress-safe placeholders; do not claim placeholders exist in committed repo source.',
    '',
    '## WSP_OPERATING_CONTRACT',
    '- Advisory only. No shell, repo modification, credential, browser, deploy, or runtime control.',
    '- Apply WSP_97 truth labels on any new claims.'
  ].join('\n');
}

function mergeRepairedOutput(primaryContent, repairContent, missingSections) {
  const primary = String(primaryContent || '').trim();
  const repair = String(repairContent || '').trim();
  const wanted = Array.isArray(missingSections) ? missingSections.slice() : [];
  let merged = primary;
  if (repair) {
    if (/^## Decision\b/m.test(repair) && /## (?:Lead|Synthesis)\b/m.test(repair)) {
      merged = repair;
    } else if (!primary) {
      merged = repair;
    } else {
      merged = primary + '\n\n## Schema repair supplement\n\n' + repair;
    }
  }
  const appended = [];
  for (const section of wanted) {
    if (buildSectionHeaderPattern(section).test(merged)) {
      continue;
    }
    const extracted = extractMarkdownSection(repair, section);
    if (extracted) {
      merged += '\n\n' + extracted;
      appended.push(section);
    }
  }
  const stillMissing = wanted.filter((section) => !buildSectionHeaderPattern(section).test(merged));
  return { text: merged, appendedSections: appended, stillMissing: stillMissing };
}

function isSubstantiveRedDogWorker(workerType) {
  const worker = cleanWorkerType(workerType);
  return worker === 'reddog_architect' || worker === 'wsp_gate_critic' || worker === 'repair_planner';
}

function attachOrchestratorMetadata(reviewPacket, classification, resolvedEffort, resolvedMode, validationState, resolvedContextMode, worker, promptConstruction, holoScorecard, workTrail, unicodeMeta) {
  const base = reviewPacket && typeof reviewPacket === 'object' ? reviewPacket : {};
  const construction = promptConstruction && typeof promptConstruction === 'object' ? promptConstruction : {};
  const providerReport = resolveProviderReasoningReport(resolvedEffort);
  const unicode = unicodeMeta && typeof unicodeMeta === 'object' ? unicodeMeta : emptyUnicodeNormalizationMeta();
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
    provider_reasoning_note: providerReport.provider_reasoning_note,
    unicode_normalization_applied: unicode.unicode_normalization_applied === true,
    unicode_replacements_count: typeof unicode.unicode_replacements_count === 'number' ? unicode.unicode_replacements_count : 0,
    unicode_normalization_sources: typeof unicode.unicode_normalization_sources === 'string' ? unicode.unicode_normalization_sources : '',
    unicode_normalization_form: unicode.unicode_normalization_form || 'none'
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
  const state = { history: [], lastReviewPacket: null, lastContinuationSummary: null, bridgeChild: null, disposed: false };
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
    const useLastPacket = message.useLastPacket !== false;
    const classification = classifyTaskForRedDog(workFocus, selectedContextMode, workerType);
    const effort = resolveAutoEffort(classification, selectedEffort);
    const mode = resolveModelMode(classification, selectedMode, workerType);
    const contextMode = resolveAutoContextMode(classification, selectedContextMode);
    const contextPacket = buildBoundedRepoContext(contextMode, workFocus);
    let wspTaskPrompt = constructWspTaskPrompt(workFocus, classification, contextPacket.quality, workerType);
    if (useLastPacket && state.lastContinuationSummary) {
      wspTaskPrompt = appendContinuationSummaryToWspPrompt(wspTaskPrompt, state.lastContinuationSummary);
      postStatusAndProgress(webview, null, 'Continuation: appended WSP_97-safe summary from last RedDog packet (not raw Copy MD).');
    }
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
    let unicodeMeta = emptyUnicodeNormalizationMeta();
    const absorbUnicodeMeta = (bridgeResult) => {
      if (!bridgeResult || typeof bridgeResult !== 'object') {
        return;
      }
      unicodeMeta = mergeUnicodeNormalizationMeta(unicodeMeta, {
        unicode_normalization_applied: bridgeResult.unicode_normalization_applied,
        unicode_replacements_count: bridgeResult.unicode_replacements_count,
        unicode_normalization_sources: bridgeResult.unicode_normalization_sources,
        unicode_normalization_form: bridgeResult.unicode_normalization_form
      });
    };
    const onBridgeProgress = (stage, text) => {
      postStatusMessage(webview, text);
      postProgressMessage(webview, stage, text);
      const normalized = normalizeBridgeStageToWorkTrail(stage, text);
      if (normalized) {
        workTrail.push(normalized.event, normalized.detail);
      }
    };
    const onRepairBridgeProgress = (stage, text) => {
      postStatusMessage(webview, text);
      postProgressMessage(webview, stage, text);
      const normalized = normalizeRepairBridgeStageToWorkTrail(stage, text);
      if (normalized) {
        workTrail.push(normalized.event, normalized.detail);
      }
    };
    let result = await callFusion(context, worker, wspTaskPrompt, contextPacket.text, systemPrompt, state.history, mode, onBridgeProgress, state, promptConstruction);
    absorbUnicodeMeta(result);
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
        validationState.repair_context_mode = 'repair_minimal';
        validationState.repair_mode = 'openrouter_single';
        workTrail.push('repair_started', 'repair_mode=openrouter_single; context=repair_minimal');
        postStatusAndProgress(webview, null, 'Output schema incomplete. Missing: ' + validation.missingSections.join(', ') + '. Running one repair pass...');
        const repairPrompt = buildRepairPrompt(wspTaskPrompt, result.content, validation.missingSections);
        const repairContext = buildRepairBoundedContext();
        const repairSystemPrompt = [
          'Complete missing advisory markdown sections only.',
          'Output ONLY the missing section headers and bodies listed in the user prompt.',
          'Use openrouter_single repair semantics; do not invoke a Fusion panel.',
          'Do not repeat the full document unless necessary.'
        ].join(' ');
        const repairResult = await callFusion(
          context,
          worker,
          repairPrompt,
          repairContext,
          repairSystemPrompt,
          [],
          'openrouter_single',
          onRepairBridgeProgress,
          state,
          promptConstruction,
          { promptSource: 'repair_prompt', maxTokens: 2400 }
        );
        absorbUnicodeMeta(repairResult);
        if (repairResult.ok) {
          const mergeResult = mergeRepairedOutput(result.content, repairResult.content, validation.missingSections);
          validationState.repair_appended_sections = mergeResult.appendedSections;
          const repairValidation = validateRedDogOutput(mergeResult.text, { substantiveArchitect: true, mode: mode });
          validationState.repair_ok = repairValidation.valid;
          validationState.missing_sections_after_repair = repairValidation.missingSections.length
            ? repairValidation.missingSections
            : mergeResult.stillMissing;
          if (repairValidation.valid) {
            result = Object.assign({}, repairResult, { content: mergeResult.text, mode: mode });
            validationState.validated = true;
            validationState.missing_sections = [];
            workTrail.push('repair_complete', 'schema_repair_pass');
          } else {
            validationState.validated = false;
            validationState.output_validation_failed = true;
            validationState.repair_failure_reason = 'schema_incomplete_after_repair';
            result.content = appendValidationFailureContent(mergeResult.text, validationState);
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
      workTrail,
      unicodeMeta
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
    const continuationSummary = buildSanitizedContinuationSummary({
      blocked: result.reason === 'redaction_blocked',
      reason: result.reason,
      content: result.content,
      review_packet: result.review_packet,
      redaction_gate_report: result.redaction_gate_report,
      workerType: workerType,
      classification: classification,
      mode: mode,
      contextMode: contextMode,
      promptConstruction: promptConstruction,
      result: result,
      timestamp: new Date().toISOString()
    });
    state.lastContinuationSummary = continuationSummary;
    result.continuation_summary = continuationSummary;
    result.copy_markdown = buildCopyMarkdown(result, workerType, contextPacket.summary, workTrail, holoScorecard, effort, {
      promptConstruction: promptConstruction,
      contextMode: contextMode,
      substantive: substantiveTask,
      handoffRecommendation: handoffRecommendation,
      continuationSummary: continuationSummary
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

function buildBridgePythonEnv(baseEnv) {
  return Object.assign({}, baseEnv || process.env, {
    PYTHONIOENCODING: 'utf-8',
    PYTHONUTF8: '1'
  });
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

function callFusion(context, worker, prompt, boundedContext, systemPrompt, history, mode, onProgress, state, bridgeMeta, callOptionsArg) {
  return new Promise((resolve) => {
    const root = workspaceRoot();
    const script = path.join(root, 'scripts', 'advisory_model_once.py');
    const config = vscode.workspace.getConfiguration('foundupsFusion');
    const configuredPython = config.get('pythonPath') || 'python';
    const interpreter = resolvePythonInterpreter(root, configuredPython);
    const callOptions = callOptionsArg && typeof callOptionsArg === 'object' ? callOptionsArg : {};
    const promptSource = callOptions.promptSource ? callOptions.promptSource : 'prompt';
    const promptNorm = normalizeBridgeTextForUnicode(prompt, promptSource);
    const contextNorm = normalizeBridgeTextForUnicode(boundedContext, 'context');
    const unicodeMeta = mergeUnicodeNormalizationMeta(null, Object.assign({}, promptNorm, { unicode_normalization_source: promptSource }));
    const mergedUnicodeMeta = mergeUnicodeNormalizationMeta(unicodeMeta, Object.assign({}, contextNorm, { unicode_normalization_source: 'context' }));
    const budgeted = applyBridgeContextBudget(promptNorm.text, contextNorm.text);
    onProgress(null, 'Mode: ' + mode);
    onProgress(null, 'Python interpreter: ' + interpreter.path + ' (' + interpreter.source + ')');
    onProgress(null, 'Bridge process starting');
    onProgress(null, 'Workspace root: ' + root);
    onProgress(null, 'Bridge script: ' + script);
    onProgress(null, 'OpenRouter key visible to Cursor process: ' + (process.env.OPENROUTER_API_KEY ? 'yes' : 'no'));
    if (budgeted.budget.truncation_applied) {
      onProgress(null, 'Context budget applied: ' + budgeted.budget.truncation_reason);
    }
    if (mergedUnicodeMeta.unicode_normalization_applied) {
      onProgress(null, 'Unicode normalization applied before redaction gate: replacements=' + mergedUnicodeMeta.unicode_replacements_count + ' sources=' + (mergedUnicodeMeta.unicode_normalization_sources || 'unknown'));
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
      env: buildBridgePythonEnv(process.env),
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
      max_tokens: callOptions.maxTokens || 2200,
      temperature: 0.2,
      timeout: mode === 'foundups_fusion' ? 120 : 90,
      bridge_meta: Object.assign({}, bridgeMeta || {}, {
        python_interpreter: interpreter.path,
        python_interpreter_source: interpreter.source,
        truncation_applied: budgeted.budget.truncation_applied,
        truncation_reason: budgeted.budget.truncation_reason,
        unicode_normalization_applied: mergedUnicodeMeta.unicode_normalization_applied,
        unicode_replacements_count: mergedUnicodeMeta.unicode_replacements_count,
        unicode_normalization_sources: mergedUnicodeMeta.unicode_normalization_sources,
        unicode_normalization_form: mergedUnicodeMeta.unicode_normalization_form
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
        finish(Object.assign({}, parsed, mergedUnicodeMeta));
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
    // REDDOG_DIRECT_READ_FALLBACK_BY_PATH_PHASE1: surface the governed direct-read
    // content as a dedicated bounded section so the truncated recall JSON does not
    // drop the fetched source the model needs to reason on.
    if (holo.direct_read_section && holo.direct_read_section.text) {
      sections.push(holo.direct_read_section.text);
    }
  }
  let targetContentMeta = null;
  if (mode !== 'none') {
    const targetSection = buildTargetRecallContentSection(root, taskText || '', 24000);
    if (targetSection.text) {
      sections.push(targetSection.text);
    }
    targetContentMeta = targetSection.meta;
    holoindex_meta = mergeTargetContentMeta(holoindex_meta, targetContentMeta);
    holoindex_scorecard = extractHoloIndexScorecard(mode, holoindex_meta);
    if (taskMentionsWsp97(taskText)) {
      const wsp97 = buildWsp97ProtocolExcerpt(root, WSP97_EXCERPT_MAX_CHARS);
      if (wsp97.text) {
        sections.push(wsp97.text);
        holoindex_meta = applyWsp97SanitizationMeta(holoindex_meta, wsp97.meta);
        holoindex_scorecard = extractHoloIndexScorecard(mode, holoindex_meta);
      }
    }
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

function normalizeRelRepoPath(relPath) {
  return String(relPath || '').replace(/\\/g, '/').replace(/^\/+/, '');
}

function isTargetReadPathDenied(relPath) {
  const normalized = normalizeRelRepoPath(relPath);
  if (!normalized) {
    return 'path_missing';
  }
  if (path.isAbsolute(normalized) || /^[a-zA-Z]:/.test(normalized)) {
    return 'outside_root';
  }
  if (normalized.includes('..')) {
    return 'outside_root';
  }
  const lower = normalized.toLowerCase();
  const parts = lower.split('/');
  for (const seg of TARGET_READ_BLOCKED_SEGMENTS) {
    if (parts.includes(seg)) {
      return 'outside_root';
    }
  }
  const base = path.basename(lower);
  for (const name of TARGET_READ_BLOCKED_BASENAMES) {
    if (base === name || base.startsWith(name + '.')) {
      return 'outside_root';
    }
  }
  for (const ext of TARGET_READ_BLOCKED_EXTENSIONS) {
    if (lower.endsWith(ext)) {
      return 'outside_root';
    }
  }
  return null;
}

function resolveSafeRepoFile(root, relPath) {
  const deny = isTargetReadPathDenied(relPath);
  if (deny) {
    return { ok: false, reason: deny };
  }
  try {
    const resolvedRoot = path.resolve(root);
    const full = path.resolve(resolvedRoot, relPath);
    if (full !== resolvedRoot && !full.startsWith(resolvedRoot + path.sep)) {
      return { ok: false, reason: 'outside_root' };
    }
    const realpathFn = fs.realpathSync.native || fs.realpathSync;
    const real = realpathFn(full);
    const realRoot = realpathFn(resolvedRoot);
    if (real !== realRoot && !real.startsWith(realRoot + path.sep)) {
      return { ok: false, reason: 'outside_root' };
    }
    return { ok: true, full: real };
  } catch (err) {
    return { ok: false, reason: 'path_missing' };
  }
}

function isLikelyBinaryFile(fullPath) {
  try {
    const fd = fs.openSync(fullPath, 'r');
    const buf = Buffer.alloc(8192);
    const n = fs.readSync(fd, buf, 0, 8192, 0);
    fs.closeSync(fd);
    return buf.slice(0, n).includes(0);
  } catch (err) {
    return true;
  }
}

function targetSnippetLanguageId(relPath) {
  const normalized = normalizeRelRepoPath(relPath).toLowerCase();
  if (normalized.endsWith('.py')) {
    return 'python';
  }
  if (normalized.endsWith('.js')) {
    return 'javascript';
  }
  if (normalized.endsWith('.md')) {
    return 'markdown';
  }
  return 'text';
}

function sanitizeTargetSnippetForRedaction(raw) {
  let out = String(raw || '');
  const categories = [];
  TARGET_SNIPPET_BLOCK_SANITIZERS.forEach((entry, idx) => {
    const cat = entry[0];
    const rx = entry[1];
    const placeholder = '[SANITIZED_BLOCK:' + String(idx + 1).padStart(2, '0') + ']';
    let hit = false;
    out = out.replace(rx, () => {
      hit = true;
      return placeholder;
    });
    if (hit && categories.indexOf(cat) === -1) {
      categories.push(cat);
    }
  });
  return { text: out, sanitized: categories.length > 0, categories: categories };
}

function mergeSanitizedCategories(into, from) {
  const merged = Array.isArray(into) ? into.slice() : [];
  if (!Array.isArray(from)) {
    return merged;
  }
  for (const cat of from) {
    if (merged.indexOf(cat) === -1) {
      merged.push(cat);
    }
  }
  return merged;
}

function readBoundedTargetSnippet(root, relPath, maxChars) {
  const max = maxChars || TARGET_SNIPPET_DEFAULT_CHARS;
  const resolved = resolveSafeRepoFile(root, relPath);
  if (!resolved.ok) {
    return { content: '', omitted_reason: resolved.reason, truncated: false, chars: 0 };
  }
  try {
    const stat = fs.statSync(resolved.full);
    if (!stat.isFile()) {
      return { content: '', omitted_reason: 'path_missing', truncated: false, chars: 0 };
    }
    if (stat.size > TARGET_SNIPPET_MAX_FILE_BYTES) {
      return { content: '', omitted_reason: 'binary_or_oversized', truncated: false, chars: 0 };
    }
    if (isLikelyBinaryFile(resolved.full)) {
      return { content: '', omitted_reason: 'binary_or_oversized', truncated: false, chars: 0 };
    }
    const raw = fs.readFileSync(resolved.full, 'utf8');
    const truncated = raw.length > max;
    const clipped = truncated ? raw.slice(0, max) + '\n...[TRUNCATED ' + (raw.length - max) + ' chars]' : raw;
    const sanitized = sanitizeTargetSnippetForRedaction(clipped);
    return {
      content: sanitized.text,
      omitted_reason: 'none',
      truncated,
      chars: sanitized.text.length,
      sanitized: sanitized.sanitized,
      sanitized_categories: sanitized.categories
    };
  } catch (err) {
    return { content: '', omitted_reason: 'read_error', truncated: false, chars: 0, sanitized: false, sanitized_categories: [] };
  }
}

function readBoundedTargetSnippets(root, taskText, opts) {
  const options = opts && typeof opts === 'object' ? opts : {};
  const built = buildTargetRecallContentSection(root, taskText, options.maxChars || 24000);
  return {
    sections: built.text ? [built.text] : [],
    meta: built.meta
  };
}

function buildTargetRecallContentSection(root, taskText, maxChars) {
  const budget = maxChars || 24000;
  const targets = inferRecallTargetPaths(taskText).filter((target) => !target.startsWith('symbol:'));
  const meta = {
    target_content_included: false,
    target_content_paths: [],
    target_content_chars: 0,
    target_content_omitted_reason: 'no_targets',
    target_content_truncated: false,
    target_content_sanitized: false,
    target_content_sanitized_categories: []
  };
  if (!targets.length) {
    return { text: '', meta };
  }
  const sections = [];
  let used = 0;
  let anyIncluded = false;
  let truncatedAny = false;
  const omitted = [];
  for (const rel of targets) {
    const perFile = Math.max(2000, Math.floor(budget / targets.length));
    const snippet = readBoundedTargetSnippet(root, rel, perFile);
    if (snippet.content) {
      anyIncluded = true;
      meta.target_content_paths.push(rel);
      used += snippet.chars;
      if (snippet.truncated) {
        truncatedAny = true;
      }
      if (snippet.sanitized) {
        meta.target_content_sanitized = true;
        meta.target_content_sanitized_categories = mergeSanitizedCategories(meta.target_content_sanitized_categories, snippet.sanitized_categories);
      }
      sections.push('#### ' + rel + '\n```' + targetSnippetLanguageId(rel) + '\n' + snippet.content + '\n```');
    } else if (snippet.omitted_reason && snippet.omitted_reason !== 'none') {
      omitted.push(snippet.omitted_reason);
    }
  }
  meta.target_content_included = anyIncluded;
  meta.target_content_chars = used;
  meta.target_content_truncated = truncatedAny;
  meta.target_content_omitted_reason = anyIncluded ? 'none' : (omitted[0] || 'path_missing');
  if (!sections.length) {
    return { text: '', meta };
  }
  return { text: '### Target recall content\n' + sections.join('\n\n'), meta };
}

function taskMentionsWsp97(taskText) {
  return /wsp[_\s-]?97|truth[\s_-]?label/i.test(String(taskText || ''));
}

function buildWsp97ProtocolExcerpt(root, maxChars) {
  const snippet = readBoundedTargetSnippet(root, WSP97_PROTOCOL_REL_PATH, maxChars || WSP97_EXCERPT_MAX_CHARS);
  if (!snippet.content) {
    return { text: '', meta: { wsp97_excerpt_included: false, wsp97_excerpt_chars: 0, wsp97_excerpt_sanitized: false, wsp97_excerpt_sanitized_categories: [] } };
  }
  return {
    text: '### WSP protocol excerpt (bounded)\n```markdown\n' + snippet.content + '\n```',
    meta: {
      wsp97_excerpt_included: true,
      wsp97_excerpt_chars: snippet.chars,
      wsp97_excerpt_sanitized: !!snippet.sanitized,
      wsp97_excerpt_sanitized_categories: snippet.sanitized_categories || []
    }
  };
}

function mergeTargetContentMeta(holoMeta, targetMeta) {
  const meta = holoMeta && typeof holoMeta === 'object' ? Object.assign({}, holoMeta) : {};
  if (targetMeta) {
    meta.target_content_included = targetMeta.target_content_included;
    meta.target_content_paths = targetMeta.target_content_paths || [];
    meta.target_content_chars = targetMeta.target_content_chars || 0;
    meta.target_content_omitted_reason = targetMeta.target_content_omitted_reason || 'unknown';
    meta.target_content_truncated = !!targetMeta.target_content_truncated;
    meta.target_content_sanitized = !!targetMeta.target_content_sanitized;
    meta.target_content_sanitized_categories = Array.isArray(targetMeta.target_content_sanitized_categories)
      ? targetMeta.target_content_sanitized_categories.slice()
      : [];
  }
  return meta;
}

function applyWsp97SanitizationMeta(holoMeta, wsp97Meta) {
  const meta = holoMeta && typeof holoMeta === 'object' ? Object.assign({}, holoMeta) : {};
  if (!wsp97Meta || !wsp97Meta.wsp97_excerpt_sanitized) {
    return meta;
  }
  meta.target_content_sanitized = true;
  meta.target_content_sanitized_categories = mergeSanitizedCategories(
    meta.target_content_sanitized_categories,
    wsp97Meta.wsp97_excerpt_sanitized_categories
  );
  return meta;
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

function holoIndexMetaFromBundle(output, usedOfflineFallback, taskText) {
  const meta = {
    holoindex_status: usedOfflineFallback ? 'offline_fallback' : 'unknown',
    wsp_hits: 'unknown',
    code_hits: 'unknown',
    skill_hits: 'unknown',
    target_recall_ok: 'unknown',
    index_gap_detected: 'unknown',
    direct_read_fallback_used: usedOfflineFallback ? true : false,
    required_targets_total: 0,
    required_targets_recalled: 0,
    required_targets_missing: [],
    direct_read_paths: [],
    direct_read_rejected: [],
    direct_read_bytes: 0,
    direct_read_truncated: []
  };
  try {
    const data = JSON.parse(String(output || '{}'));
    const bundleMeta = data.task_retrieval && data.task_retrieval.metadata ? data.task_retrieval.metadata : {};
    const recall = evaluateTargetRecall(taskText, data);
    meta.holoindex_status = usedOfflineFallback ? 'offline_fallback' : 'bundle_json_ok';
    meta.wsp_hits = Number(bundleMeta.wsp_count || 0);
    meta.code_hits = Number(bundleMeta.code_count || 0);
    meta.skill_hits = bundleMeta.skill_count !== undefined ? Number(bundleMeta.skill_count) : 'unknown';
    meta.target_recall_ok = recall.target_recall_ok;
    meta.index_gap_detected = recall.index_gap_detected;
    meta.recall_targets = recall.recall_targets;
    meta.required_targets_total = recall.required_targets_total;
    meta.required_targets_recalled = recall.required_targets_recalled;
    meta.required_targets_missing = recall.required_targets_missing;
    // REDDOG_DIRECT_READ_FALLBACK_BY_PATH_PHASE1: surface the Python-side
    // governed direct-read telemetry when the bundle carried a fetch.
    const dr = data.direct_read && typeof data.direct_read === 'object' ? data.direct_read : null;
    if (dr) {
      meta.direct_read_fallback_used = !!dr.direct_read_fallback_used;
      meta.direct_read_paths = Array.isArray(dr.direct_read_paths) ? dr.direct_read_paths : [];
      meta.direct_read_rejected = Array.isArray(dr.direct_read_rejected) ? dr.direct_read_rejected : [];
      meta.direct_read_bytes = Number(dr.direct_read_bytes || 0);
      meta.direct_read_truncated = Array.isArray(dr.direct_read_truncated) ? dr.direct_read_truncated : [];
    } else {
      meta.direct_read_fallback_used = !!usedOfflineFallback;
    }
  } catch (err) {
    meta.holoindex_status = usedOfflineFallback ? 'offline_fallback' : 'parse_error';
  }
  return meta;
}

// REDDOG_DIRECT_READ_FALLBACK_BY_PATH_PHASE1 (slice 2/3): when slice-1's
// detector reports a required-target index gap, ask the Python bundle layer to
// fetch the missing repo-relative targets (governed direct-read). The fetch and
// the hard security allowlist live in bundle_json.py; the extension only names
// the paths. Content flows back through the EXISTING redaction gate unchanged.
function buildMustIncludeArgs(missingTargets) {
  const args = [];
  const seen = new Set();
  for (const raw of (Array.isArray(missingTargets) ? missingTargets : [])) {
    const target = String(raw || '').trim();
    if (!target || target.startsWith('symbol:')) {
      // Symbols cannot be direct-read by path; leave them for later retrieval.
      continue;
    }
    const norm = target.toLowerCase();
    if (seen.has(norm)) {
      continue;
    }
    seen.add(norm);
    args.push('--bundle-must-include', target);
  }
  return args;
}

function holoIndexOutput(root, taskText, maxChars) {
  const query = String(taskText || '').replace(/\s+/g, ' ').trim().slice(0, 500) || 'FoundUps RedDog WSP_00 WSP_97 WSP_15 current task';
  const moduleHint = moduleHintFromActive(root);
  try {
    const env = Object.assign({}, process.env, { HOLO_SKIP_MODEL: '1' });
    const baseArgs = ['-B', 'holo_index.py', '--bundle-json', '--search', query, '--bundle-module-hint', moduleHint, '--limit', '5', '--quiet-root-alerts'];
    let output = cp.execFileSync('python', baseArgs, {
      cwd: root,
      env,
      encoding: 'utf8',
      timeout: 25000,
      maxBuffer: Math.max(maxChars * 4, 65536),
      windowsHide: true
    });
    let meta = holoIndexMetaFromBundle(output, false, taskText);
    // Direct-read fallback: if a required-target list was present and any target
    // is missing from the semantic bundle, re-run once asking the Python layer
    // to fetch exactly those paths, then re-evaluate recall on the enriched bundle.
    const missing = Array.isArray(meta.required_targets_missing) ? meta.required_targets_missing : [];
    if (meta.index_gap_detected === true && missing.length) {
      const mustInclude = buildMustIncludeArgs(missing);
      if (mustInclude.length) {
        try {
          const enrichedArgs = baseArgs.concat(mustInclude);
          const enriched = cp.execFileSync('python', enrichedArgs, {
            cwd: root,
            env,
            encoding: 'utf8',
            timeout: 30000,
            maxBuffer: Math.max(maxChars * 8, 131072),
            windowsHide: true
          });
          output = enriched;
          meta = holoIndexMetaFromBundle(enriched, false, taskText);
        } catch (fetchErr) {
          // Fetch failure must not abort recall; keep the pre-fetch bundle+meta.
        }
      }
    }
    const directReadSection = buildDirectReadContentSection(output);
    return {
      output: String(output || '').slice(0, maxChars),
      quality: summarizeHoloBundle(output),
      meta: meta,
      direct_read_section: directReadSection
    };
  } catch (bundleErr) {
    try {
      const output = cp.execFileSync('python', ['-B', 'holo_index.py', '--offline', '--search', query, '--limit', '5'], {
        cwd: root,
        encoding: 'utf8',
        timeout: 20000,
        maxBuffer: Math.max(maxChars * 4, 65536),
        windowsHide: true
      });
      const meta = holoIndexMetaFromBundle(output, true, query);
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

// Render the Python-fetched direct-read target content (already budget-bounded
// and security-allowlisted by bundle_json.py) into a dedicated bounded section.
// This does NOT re-read the filesystem and does NOT apply any redaction logic here;
// the assembled context still passes through the existing Python egress redaction
// gate before leaving the machine.
//
// REDDOG_AUDIT_MODE_REDACTION_PHASE1 (slice 3/3): when direct-read fetched required
// targets (slice-2 fallback), this IS an audit-context retrieval. The section carries
// an audit_context=true signal so the egress redaction gate can run in audit_mode --
// preserving STRUCTURAL governance identifiers while STILL redacting every secret
// VALUE / payout AMOUNT / authorization TOKEN. audit_context stays false when no
// direct-read fetch occurred (backward compatible; default egress path unchanged).
function buildDirectReadContentSection(output) {
  const empty = { text: '', paths: [], chars: 0, audit_context: false };
  let data;
  try {
    data = JSON.parse(String(output || '{}'));
  } catch (err) {
    return empty;
  }
  const hits = data && data.task_retrieval && Array.isArray(data.task_retrieval.code_hits)
    ? data.task_retrieval.code_hits
    : [];
  const directHits = hits.filter((h) => h && h.direct_read === true && typeof h.content === 'string' && h.content.length);
  if (!directHits.length) {
    return empty;
  }
  const sections = [];
  const paths = [];
  let used = 0;
  for (const hit of directHits) {
    const rel = String(hit.location || '').replace(/\\/g, '/');
    const lang = targetSnippetLanguageId(rel);
    const truncatedNote = hit.content_truncated ? ' (truncated to governed budget)' : '';
    sections.push('#### ' + rel + truncatedNote + '\n```' + lang + '\n' + hit.content + '\n```');
    paths.push(rel);
    used += hit.content.length;
  }
  return {
    text: '### Direct-read target content (governed fetch by path)\n'
      + 'Fetched by the Python bundle layer under the direct-read allowlist; still redaction-gated before egress '
      + '(audit-mode: governance STRUCTURE readable, secret/payout/authority VALUES redacted).\n\n'
      + sections.join('\n\n'),
    paths: paths,
    chars: used,
    // Direct-read of required targets == governance audit context. The egress gate
    // uses this to run in audit_mode (structure-preserving, value-redacting).
    audit_context: true
  };
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
        <label for="useLastPacket"><input id="useLastPacket" type="checkbox" checked> Use last RedDog packet</label>
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
    const useLastPacket = document.getElementById('useLastPacket');
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
      vscode.postMessage({
        command: 'ask',
        text,
        mode: 'auto',
        contextMode: 'auto',
        workerType: workerType.value,
        effort: 'auto',
        useLastPacket: !!(useLastPacket && useLastPacket.checked)
      });
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
  buildRepairBoundedContext,
  mergeRepairedOutput,
  extractMarkdownSection,
  buildSectionHeaderPattern,
  normalizeRepairBridgeStageToWorkTrail,
  BRIDGE_REPAIR_STAGE_WORK_TRAIL,
  constructWspTaskPrompt,
  appendContinuationSummaryToWspPrompt,
  buildSanitizedContinuationSummary,
  buildContinuationSummaryCopySection,
  formatContinuationSummaryBlock,
  sanitizeContinuationField,
  redactedDigest,
  resolvePythonInterpreter,
  buildBridgePythonEnv,
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
  formatHoloIndexScorecardLines,
  evaluateTargetRecall,
  inferRecallTargetPaths,
  parseRequiredTargetPaths,
  isSelfFileLocation,
  requiredTargetMatchesLocation,
  holoIndexMetaFromBundle,
  buildMustIncludeArgs,
  buildDirectReadContentSection,
  isTargetReadPathDenied,
  resolveSafeRepoFile,
  readBoundedTargetSnippet,
  readBoundedTargetSnippets,
  buildTargetRecallContentSection,
  taskMentionsWsp97,
  buildWsp97ProtocolExcerpt,
  mergeTargetContentMeta,
  applyWsp97SanitizationMeta,
  sanitizeTargetSnippetForRedaction,
  mergeSanitizedCategories,
  TARGET_SNIPPET_BLOCK_SANITIZERS,
  WSP97_PROTOCOL_REL_PATH,
  MOJIBAKE_MARKERS,
  WORK_TRAIL_MAX_EVENTS,
  VALIDATION_FAILED_FOOTER,
  UNICODE_SURROGATE_PLACEHOLDER,
  normalizeBridgeTextForUnicode,
  emptyUnicodeNormalizationMeta,
  mergeUnicodeNormalizationMeta
};
