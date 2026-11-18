'use strict';

const { isTargetReadPathDenied } = require('./target_read_path_policy');

const FIELD_RULES = Object.freeze([
  ['WSP_00', 12, /^self=0102;\s*role=WORKER_ROLE;\s*origin=external_principal;\s*role_lock=immutable$/, false],
  ['WSP_97', 12, /^retrieve_before_claim=required;\s*truth_labels=required;\s*cor=required;\s*evidence_invention=forbidden$/, false],
  ['WSP_15', 12, /^economy_gate=required;\s*score=C\+I\+D\+Impact;\s*priority=P0-P4$/, false],
  ['AUTHOR_PROFILE', 4, /^(?:REDDOG_ARCHITECT|WSP_GATE_CRITIC|REPAIR_PLANNER|SMOKE_TESTER)$/, false],
  ['EXECUTION_PLANE', 4, /^(?:audit|read[ _-]?only|no[ _-]?effect(?:[ _-][a-z]+)*|bounded[ _-]?execution|implementation|verification)$/i, false],
  ['AUTHORITY_BOUNDARY', 4, /^PROMPT_IS_NON_AUTHORITATIVE$/, false],
  ['FAIL_POLICY', 4, /^FAIL_CLOSED$/, false]
]);
const SECTION_RULES = Object.freeze([
  [['MISSION', 'PURPOSE'], 12, null, true, 3],
  [['READ_FIRST', 'READ'], 4, /(?:[A-Za-z0-9_.-]+[\\/][A-Za-z0-9_.\\/-]+|\b[A-Za-z0-9_-]+\.[A-Za-z0-9]{1,8}\b)/, true, 1],
  [['FAIL', 'REJECT'], 4, null, false, 1],
  [['VALIDATION', 'TESTS', 'CHECK'], 12, /\b(?:test|pytest|node|check|validate|verify|lint|security|codeql|diff|ascii)\w*/i, true, 2],
  [['RETURN'], 12, /\b(?:verified_ready|draft[ _-]?pr|report|evidence|files?[ _-]?changed|test[ _-]?count|receipt|decision)\b/i, true, 2]
]);

function isPromptAuthoringRequest(text) {
  const source = String(text || '').toLowerCase();
  if (!source.includes('prompt')) return false;
  return /\b(?:provide|create|draft|author|write|generate|improve|enhance|audit|evaluate)\b[\s\S]{0,120}\bprompt\b/.test(source)
    || /\bprompt\b[\s\S]{0,120}\b(?:for|to|worker|slice|phase1|phase_1|author|implement|audit|execute)\b/.test(source)
    || /\b(?:m2m|worker|reddog)\s+prompt\b/.test(source);
}

function hasExecutableWorkerPromptBlock(markdown, expectedAuthorProfile) {
  const body = extractWorkerPromptBody(markdown);
  if (!body || containsCommentSyntax(body) || containsGovernanceContradiction(body)) return false;
  return FIELD_RULES.every((rule) => hasInlineField(body, rule))
    && SECTION_RULES.every((rule) => hasStructuredSection(body, rule))
    && hasRequiredGovernanceClauses(body, expectedAuthorProfile);
}

function fieldValue(body, field) {
  const match = new RegExp('^' + field + ':[ \\t]*(.*)$', 'im').exec(body);
  return match ? String(match[1] || '').trim() : '';
}

function hasRequiredGovernanceClauses(body, expectedAuthorProfile) {
  const wsp00 = fieldValue(body, 'WSP_00');
  const wsp97 = fieldValue(body, 'WSP_97');
  const wsp15 = fieldValue(body, 'WSP_15');
  const author = fieldValue(body, 'AUTHOR_PROFILE');
  const expected = String(expectedAuthorProfile || '').trim().toUpperCase();
  return /(?:^|;)\s*self=0102\s*(?:;|$)/i.test(wsp00)
    && /(?:^|;)\s*role=[A-Z0-9_]+\s*(?:;|$)/i.test(wsp00)
    && /(?:^|;)\s*origin=external_principal\s*(?:;|$)/i.test(wsp00)
    && /(?:^|;)\s*role_lock=immutable\s*(?:;|$)/i.test(wsp00)
    && /(?:^|;)\s*retrieve_before_claim=required\s*(?:;|$)/i.test(wsp97)
    && /(?:^|;)\s*truth_labels=required\s*(?:;|$)/i.test(wsp97)
    && /(?:^|;)\s*cor=required\s*(?:;|$)/i.test(wsp97)
    && /(?:^|;)\s*evidence_invention=forbidden\s*(?:;|$)/i.test(wsp97)
    && /(?:^|;)\s*economy_gate=required\s*(?:;|$)/i.test(wsp15)
    && /(?:^|;)\s*score=C\+I\+D\+Impact\s*(?:;|$)/i.test(wsp15)
    && /(?:^|;)\s*priority=P0-P4\s*(?:;|$)/i.test(wsp15)
    && (!expected || author === expected);
}

function containsGovernanceContradiction(body) {
  return [
    /\brole\s+(?:may|can|will|should|must)\s+(?:change|expand|escalate|promote)\b/i,
    /\b(?:invent|fabricate|make[ -]?up)\b[^.\n]{0,60}\bevidence\b/i,
    /\bevidence\b[^.\n]{0,60}\b(?:may|can|will|should|must)\s+be\s+(?:invented|fabricated|made[ -]?up)\b/i,
    /\b(?:complexity|importance|deferability|impact|priority|WSP_15)\b[^.\n]{0,80}\b(?:irrelevant|optional|ignored|bypassed)\b/i,
    /\b(?:ignore|bypass|override|disable)\b[^.\n]{0,60}\b(?:WSP_00|WSP_97|WSP_15|FAIL_POLICY|AUTHORITY_BOUNDARY)\b/i
  ].some((pattern) => pattern.test(body));
}

function containsCommentSyntax(body) {
  const source = String(body || '');
  if (['#', '//', '*', '<!--', '-->', '--!>'].some((marker) => source.includes(marker))) return true;
  return source.split(/\r?\n/).some((line) => /^[^A-Za-z0-9]*;/.test(line));
}

function extractWorkerPromptBody(markdown) {
  const lines = String(markdown || '').split(/\r?\n/);
  const headings = lines.map((line, index) => (
    /^#{1,3}[ \t]+Worker[ \t]+Prompt\b/i.test(line.trim()) ? index : -1
  )).filter((index) => index >= 0);
  if (headings.length !== 1) return '';
  let inFence = false;
  let closed = false;
  let body = '';
  for (let index = headings[0] + 1; index < lines.length; index += 1) {
    const line = lines[index];
    const trimmed = line.trim();
    if (/^#{1,3}[ \t]+\S/.test(trimmed)) break;
    if (!inFence && !closed) {
      if (!trimmed) continue;
      if (!/^```text[ \t]*$/i.test(trimmed)) return '';
      inFence = true;
      continue;
    }
    if (inFence && trimmed === '```') {
      inFence = false;
      closed = true;
    } else if (inFence) body += line + '\n';
    else if (trimmed) return '';
  }
  return closed && !inFence ? body : '';
}

function hasInlineField(body, rule) {
  const allPattern = new RegExp('^[ \\t]*' + rule[0] + ':', 'gim');
  if (Array.from(String(body || '').matchAll(allPattern)).length !== 1) return false;
  const canonical = new RegExp('^' + rule[0] + ':[ \\t]*(.*)$', 'im').exec(body);
  return Boolean(canonical && ruleMatches(canonical[1], rule));
}

function hasStructuredSection(body, rule) {
  if (sectionHeaderCount(body, rule[0]) !== 1) return false;
  const content = sectionContent(body, rule[0]);
  if (!ruleMatches(content, rule)) return false;
  if (rule[0].some((label) => /^(?:READ_FIRST|READ)$/.test(label))) {
    return hasCanonicalReadTargets(body, rule[0]);
  }
  if (rule[0].some((label) => /^(?:FAIL|REJECT)$/.test(label))) {
    return hasCanonicalFailureConditions(body, rule[0]);
  }
  return true;
}

function sectionHeaderCount(body, labels) {
  const pattern = new RegExp('^[ \\t]*(?:' + labels.join('|') + '):', 'gim');
  return Array.from(String(body || '').matchAll(pattern)).length;
}

function hasCanonicalReadTargets(body, labels) {
  const emptyHeader = new RegExp('^(?:' + labels.join('|') + '):[ \\t]*$', 'im');
  if (!emptyHeader.test(body)) return false;
  const lines = sectionLines(body, labels).filter((line) => line.trim());
  return lines.length > 0 && lines.every((line) => {
    const match = /^[ \t]*-[ \t]+READ_PATH:[ \t]+([A-Za-z0-9_.-]+(?:\/[A-Za-z0-9_.-]+)*)[ \t]*$/.exec(line);
    return Boolean(match && isCanonicalRepoPath(match[1]));
  });
}

function isCanonicalRepoPath(value) {
  const segments = String(value || '').split('/');
  return segments.length >= 1
    && !isTargetReadPathDenied(value)
    && segments.every((segment) => (
      segment && segment !== '.' && segment !== '..' && !isWindowsReservedSegment(segment)
    ));
}

function isWindowsReservedSegment(segment) {
  const basename = String(segment || '').replace(/[. ]+$/, '').split('.')[0].toUpperCase();
  return /^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$/.test(basename);
}

function hasCanonicalFailureConditions(body, labels) {
  const emptyHeader = new RegExp('^(?:' + labels.join('|') + '):[ \\t]*$', 'im');
  if (!emptyHeader.test(body)) return false;
  const lines = sectionLines(body, labels).filter((line) => line.trim());
  return lines.length > 0 && lines.every((line) => (
    /^[ \t]*-[ \t]+REJECT_ON:[ \t]+(?=[A-Z0-9_]{3,64}[ \t]*$)[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*[ \t]*$/.test(line)
  ));
}

function sectionLines(body, labels) {
  const lines = String(body || '').split(/\r?\n/);
  const header = new RegExp('^(?:' + labels.join('|') + '):', 'i');
  const start = lines.findIndex((line) => header.test(line));
  if (start < 0) return [];
  const end = lines.slice(start + 1).findIndex((line) => isSectionBoundary(line));
  return lines.slice(start + 1, end < 0 ? lines.length : start + 1 + end);
}

function sectionContent(body, labels) {
  const lines = String(body || '').split(/\r?\n/);
  const header = new RegExp('^(?:' + labels.join('|') + '):[ \\t]*(.*)$', 'i');
  for (let index = 0; index < lines.length; index += 1) {
    const match = header.exec(lines[index]);
    if (!match) continue;
    const content = [normalizeContentLine(match[1])];
    for (let cursor = index + 1; cursor < lines.length; cursor += 1) {
      if (isSectionBoundary(lines[cursor])) break;
      content.push(normalizeContentLine(lines[cursor]));
    }
    return content.filter(Boolean).join(' ');
  }
  return '';
}

function normalizeContentLine(value) {
  const text = String(value || '').trim().replace(/^[-*][ \t]*/, '').trim();
  if (!text || /^(?:#|\/\/|;|\/\*|\*|<!--)/.test(text)) return '';
  const label = /^[A-Z][A-Z0-9_ -]*:[ \t]*(.*)$/i.exec(text);
  return label ? normalizeContentLine(label[1]) : text;
}

function substantive(value, minimumLength) {
  const text = normalizeContentLine(value);
  const tokens = text.match(/[A-Za-z0-9][A-Za-z0-9_.-]*/g) || [];
  const minimum = Number.isInteger(minimumLength) ? minimumLength : 4;
  return text.length >= minimum && tokens.length >= (minimum >= 12 ? 2 : 1)
    && !/^(?:[([{<][ \t]*)?(?:none|n\/a|todo|tbd|unknown|placeholder)(?:[ \t]*[\])}>])?\.?$/i.test(text)
    && !/^(?:\{.*\}|\[.*\]|<.*>|[.]+)$/i.test(text);
}

function ruleMatches(value, rule) {
  const text = normalizeContentLine(value);
  if (!substantive(text, rule[1])) return false;
  if (rule[2] && !rule[2].test(text)) return false;
  if (rule[3] && negatesRequiredAction(text, rule[2])) return false;
  const tokens = text.toLowerCase().match(/[a-z0-9][a-z0-9_.-]*/g) || [];
  return new Set(tokens).size >= (rule[4] || 1);
}

function negatesRequiredAction(value, semanticPattern) {
  const clauses = String(value || '').split(/[.;!?]+/).map((item) => item.trim()).filter(Boolean);
  const negation = /(?:^(?:do[ \t]+not|don't|skip|ignore|omit|bypass|refuse)\b|\b(?:must|shall|should|will|may|can|could|do|does|did)\b(?:[ \t,]+[a-z-]+){0,3}[ \t,]+(?:not|never|skip|ignore|omit|bypass|refuse)\b|\bnever\b)/i;
  return clauses.some((clause) => (!semanticPattern || semanticPattern.test(clause)) && negation.test(clause));
}

function isSectionBoundary(value) {
  return /^[ \t]*(?:WSP_00|WSP_97|WSP_15|AUTHOR_PROFILE|EXECUTION_PLANE|AUTHORITY_BOUNDARY|FAIL_POLICY|MISSION|PURPOSE|READ_FIRST|READ|FAIL|REJECT|VALIDATION|TESTS|CHECK|RETURN):/i.test(
    String(value || '')
  );
}

module.exports = { hasExecutableWorkerPromptBlock, isPromptAuthoringRequest };
