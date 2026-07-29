'use strict';

const SEMANTIC_WORK_ACTION_PATTERN = /\b(?:analy[sz]e|assess|audit|build|compare|complete|create|debug|design|determine|enhance|evaluate|fix|harden|implement|improve|inspect|investigate|plan|refactor|research|review|update|verify)\b/i;
const BROAD_AUDIT_ACTION_PATTERN = /\b(?:analy[sz]e|assess|audit|evaluate|inspect|investigate|review|verify)\b/i;
const BROAD_AUDIT_QUERY_TERMS = [
  'architecture',
  'implementation',
  'source',
  'tests',
  'contracts',
  'interface',
  'roadmap',
  'workflow'
];
const SEMANTIC_GROUNDING_STOPWORDS = new Set([
  'about', 'after', 'against', 'agent', 'all', 'analyze', 'analyse', 'assess', 'audit',
  'based', 'before', 'bug', 'build', 'code', 'compare', 'complete', 'concept', 'create',
  'continue', 'current', 'debug', 'design', 'determine', 'does', 'enhance', 'evaluate',
  'everything', 'fix',
  'following', 'foundups', 'from', 'governance', 'grounding', 'harden', 'implement',
  'implementation', 'improve', 'inspect', 'into', 'investigate', 'issue', 'it', 'make',
  'mapping', 'module', 'need', 'needed', 'needs', 'output', 'paper', 'pipeline', 'plan', 'please',
  'problem', 'question', 'read', 'refactor', 'repo', 'research', 'review', 'selection',
  'should', 'something', 'system', 'that', 'the', 'them', 'this', 'through', 'to',
  'topic', 'update', 'using', 'verify', 'whether', 'with', 'work', 'workflow', 'wsp'
]);

function collapseWhitespace(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function normalizeSemanticQuery(value) {
  return collapseWhitespace(String(value || '')
    .toLowerCase()
    .replace(/[`"'()[\]{}<>]/g, ' ')
    .replace(/[_./\\:-]+/g, ' '));
}

function tokenizeSemanticQuery(value) {
  const tokens = normalizeSemanticQuery(value).match(/[a-z0-9]+/g) || [];
  return Array.from(new Set(tokens.filter((token) => token.length >= 3 && !SEMANTIC_GROUNDING_STOPWORDS.has(token))));
}

function hasSubstantiveSemanticSubject(value) {
  return tokenizeSemanticQuery(value).length > 0;
}

function semanticEvidenceText(hit) {
  if (!hit || typeof hit !== 'object') {
    return String(hit || '');
  }
  return [
    hit.need,
    hit.title,
    hit.summary,
    hit.preview,
    hit.snippet,
    hit.content,
    hit.text
  ].map((field) => String(field || '')).join(' ');
}

function semanticEvidenceCategory(hit) {
  const source = hit && typeof hit === 'object' ? hit : {};
  const bucket = String(source.bucket || '').toLowerCase();
  const ref = String(source.evidence_ref || source.location || source.path || '').replace(/\\/g, '/').toLowerCase();
  if (bucket === 'test' || /(?:^|\/)tests?(?:\/|$)|(?:^|\/)test_|[._-]test\./.test(ref)) {
    return 'verification';
  }
  if (bucket === 'wsp' || bucket === 'work_ledger') {
    return 'authoritative';
  }
  if (bucket === 'docs' || bucket === 'knowledge' || bucket === 'skill' || /\.(?:md|rst|txt)(?::\d+)?$/.test(ref)) {
    return 'verification';
  }
  if (bucket === 'code' || bucket === 'symbol' || /\.(?:c|cc|cpp|go|java|js|jsx|mjs|py|rs|ts|tsx)(?::\d+)?$/.test(ref)) {
    return 'implementation';
  }
  return 'supporting';
}

function isBroadAuditSemanticTarget(target) {
  return BROAD_AUDIT_ACTION_PATTERN.test(String(target || ''));
}

function assessBroadAuditEvidence(target, hits) {
  if (!isBroadAuditSemanticTarget(target)) {
    return { required: false, passed: true, evidence_refs: [], categories: [] };
  }
  const records = Array.isArray(hits) ? hits : [];
  const refs = Array.from(new Set(records.map((hit) => String(hit.evidence_ref || '')).filter(Boolean)));
  const categories = Array.from(new Set(records.map(semanticEvidenceCategory)));
  const hasPrimary = categories.includes('implementation') || categories.includes('authoritative');
  const hasCorroboration = categories.includes('verification') || categories.includes('authoritative');
  return {
    required: true,
    passed: refs.length >= 2 && categories.length >= 2 && hasPrimary && hasCorroboration,
    evidence_refs: refs,
    categories
  };
}

function buildEffectiveHoloQuery(taskText, semanticTargets) {
  const original = collapseWhitespace(taskText).slice(0, 500)
    || 'FoundUps RedDog WSP_00 WSP_97 WSP_15 current task';
  const broadAudit = (Array.isArray(semanticTargets) ? semanticTargets : []).some(isBroadAuditSemanticTarget);
  if (!broadAudit) {
    return {
      original_query: original,
      effective_query: original,
      expansion_strategy: 'none'
    };
  }
  const lower = original.toLowerCase();
  const additions = BROAD_AUDIT_QUERY_TERMS.filter((term) => !lower.includes(term));
  return {
    original_query: original,
    effective_query: collapseWhitespace(original + ' ' + additions.join(' ')).slice(0, 500),
    expansion_strategy: 'broad_audit_v1'
  };
}

module.exports = {
  SEMANTIC_WORK_ACTION_PATTERN,
  assessBroadAuditEvidence,
  buildEffectiveHoloQuery,
  hasSubstantiveSemanticSubject,
  normalizeSemanticQuery,
  semanticEvidenceCategory,
  semanticEvidenceText,
  tokenizeSemanticQuery
};
