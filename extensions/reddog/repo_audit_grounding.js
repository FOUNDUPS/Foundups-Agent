'use strict';

// Small deterministic adapter for the Python repo_audit_grounding.v1 receipt.
// It never reads files, runs commands, or creates authority.

const AUDIT_WORDS = new Set(['audit', 'assess', 'review', 'examine', 'inspect', 'evaluate']);
const SCOPE_WORDS = new Set(['codebase', 'module', 'repo', 'repository', 'implementation', 'system']);
const QUESTION_OPENERS = new Set(['how', 'if', 'what', 'whether', 'why']);
const GENERIC_WORDS = new Set([
  'a', 'all', 'an', 'and', 'audit', 'assess', 'codebase', 'defensive', 'entire', 'evaluate',
  'examine', 'for', 'full', 'implementation', 'inspect', 'module', 'of', 'please', 'recommend',
  'recommendations', 'repo', 'repository', 'review', 'security', 'system', 'the', 'this', 'whole'
]);

function canonicalizeAuditEntity(value) {
  return String(value || '').normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');
}

function auditWords(taskText) {
  const firstLine = String(taskText || '').normalize('NFKC').split(/\r?\n/)
    .find((line) => line.trim()) || '';
  const chunks = firstLine.toLowerCase().split(/\s+/)
    .filter((chunk) => chunk && !/[\\/:\u0000]/.test(chunk));
  const words = [];
  for (const chunk of chunks) {
    const found = chunk.match(/[\p{L}\p{N}_.-]+/gu) || [];
    words.push.apply(words, found);
  }
  return words;
}

function auditEntityCandidates(words, auditIndexes) {
  const candidates = [];
  for (let i = 0; i < words.length; i++) {
    const raw = words[i];
    const entity = canonicalizeAuditEntity(raw);
    if (!entity || entity.length < 2 || /^\d+$/.test(entity) || GENERIC_WORDS.has(entity)) continue;
    const distance = auditIndexes.length ? Math.min.apply(null, auditIndexes.map((index) => Math.abs(index - i))) : 999;
    candidates.push({ raw, entity, distance });
  }
  candidates.sort((a, b) => a.distance - b.distance || a.entity.length - b.entity.length || a.entity.localeCompare(b.entity));
  return candidates;
}

function detectRepoAuditIntent(taskText) {
  const words = auditWords(taskText);
  const auditIndexes = words.map((word, index) => AUDIT_WORDS.has(word) ? index : -1)
    .filter((index) => index >= 0);
  const candidates = auditEntityCandidates(words, auditIndexes);
  const hasAudit = auditIndexes.length > 0;
  const questionShaped = auditIndexes.some((index) => index + 1 < words.length && QUESTION_OPENERS.has(words[index + 1]));
  const hasScope = words.some((word) => SCOPE_WORDS.has(word));
  const explicitAudit = words.includes('audit') && words.length <= 3;
  const chosen = hasAudit && !questionShaped && candidates.length && (hasScope || explicitAudit) ? candidates[0] : null;
  return {
    audit_intent: !!chosen,
    entity: chosen ? chosen.entity : null,
    raw_entity: chosen ? chosen.raw : null,
    aliases: chosen ? Array.from(new Set([chosen.raw, chosen.entity])) : []
  };
}

function moduleHintForRepoAudit(taskText, fallbackHint) {
  const intent = detectRepoAuditIntent(taskText);
  return intent.audit_intent ? 'modules/foundups/' + intent.entity : fallbackHint;
}

function repoAuditReceipt(bundleData) {
  const receipt = bundleData && bundleData.repo_audit_grounding;
  return receipt && typeof receipt === 'object' ? receipt : null;
}

function selectedRecords(receipt) {
  return receipt && Array.isArray(receipt.selected)
    ? receipt.selected.filter((item) => item && typeof item.path === 'string' && item.path)
    : [];
}

function contentBearingAuditPaths(bundleData) {
  const task = bundleData && bundleData.task_retrieval && typeof bundleData.task_retrieval === 'object'
    ? bundleData.task_retrieval : {};
  const hits = Array.isArray(task.code_hits) ? task.code_hits : [];
  return new Set(hits.filter((hit) => hit && hit.repo_audit_grounding === true
    && typeof hit.content === 'string' && hit.content.length > 0)
    .map((hit) => String(hit.location || '').replace(/\\/g, '/').toLowerCase()));
}

function uniquePaths(values) {
  const out = [];
  const seen = new Set();
  for (const value of values || []) {
    const path = String(value || '').replace(/\\/g, '/');
    const key = path.toLowerCase();
    if (path && !seen.has(key)) {
      seen.add(key);
      out.push(path);
    }
  }
  return out;
}

function auditEvidenceGroups(receipt, selected, contentPaths) {
  const sources = selected.filter((item) => item.category === 'implementation_source').map((item) => item.path);
  const independent = selected.filter((item) => item.category === 'test' || item.category === 'contract')
    .map((item) => item.path);
  return {
    sourcePaths: sources,
    independentPaths: independent,
    selectedWithContent: selected.filter((item) => contentPaths.has(item.path.toLowerCase()))
      .map((item) => item.path),
    coveragePassed: !!(receipt && receipt.coverage && receipt.coverage.verdict === 'PASS')
  };
}

function auditProjectionReasons(intent, applied, evidence, contentPaths) {
  const reasons = [];
  if (intent.audit_intent && !applied) reasons.push('repo_audit_grounding_receipt_missing');
  if (applied && !evidence.coveragePassed) reasons.push('repo_audit_minimum_coverage_failed');
  if (applied && !evidence.sourcePaths.some((path) => contentPaths.has(path.toLowerCase()))) {
    reasons.push('repo_audit_source_content_missing');
  }
  if (applied && !evidence.independentPaths.some((path) => contentPaths.has(path.toLowerCase()))) {
    reasons.push('repo_audit_independent_content_missing');
  }
  return reasons;
}

function projectRepoAuditGrounding(taskText, bundleData, existingTargets) {
  const intent = detectRepoAuditIntent(taskText);
  const receipt = repoAuditReceipt(bundleData);
  const selected = selectedRecords(receipt);
  const contentPaths = contentBearingAuditPaths(bundleData);
  const entityMatches = !!(receipt && canonicalizeAuditEntity(receipt.entity) === intent.entity);
  const applied = !!(intent.audit_intent && receipt && receipt.applied === true && entityMatches);
  const evidence = auditEvidenceGroups(receipt, selected, contentPaths);
  const effective = applied
    ? uniquePaths([].concat(existingTargets || [], selected.map((item) => item.path)))
    : uniquePaths(existingTargets || []);
  const reasons = auditProjectionReasons(intent, applied, evidence, contentPaths);
  return {
    applied,
    audit_intent: intent.audit_intent,
    entity: intent.entity,
    aliases: intent.aliases,
    receipt,
    selected,
    selected_content_paths: evidence.selectedWithContent,
    effective_repo_file_targets: effective,
    passed_before_context_pack: !intent.audit_intent || (applied && reasons.length === 0),
    rejection_reasons: reasons
  };
}

function auditContextVisibility(projection, packet, scorecard) {
  const selected = Array.isArray(projection.selected) ? projection.selected : [];
  const authoritative = new Set((Array.isArray(packet.required_targets_authoritative_paths)
    ? packet.required_targets_authoritative_paths : []).map((path) => String(path).toLowerCase()));
  const missing = new Set((Array.isArray(scorecard.required_targets_context_missing)
    ? scorecard.required_targets_context_missing : []).map((path) => String(path).toLowerCase()));
  const visible = (item) => authoritative.has(item.path.toLowerCase()) && !missing.has(item.path.toLowerCase());
  return {
    source: selected.some((item) => item.category === 'implementation_source' && visible(item)),
    independent: selected.some((item) => (item.category === 'test' || item.category === 'contract') && visible(item))
  };
}

function auditContextResult(projection, reasons, visibility) {
  const uniqueReasons = Array.from(new Set(reasons));
  return {
    applied: true,
    passed: uniqueReasons.length === 0,
    rejection_reasons: uniqueReasons,
    effective_repo_file_targets: projection.effective_repo_file_targets || [],
    entity: projection.entity,
    source_visible: visibility.source,
    independent_visible: visibility.independent
  };
}

function evaluateRepoAuditContext(taskText, contextPacket) {
  const packet = contextPacket && typeof contextPacket === 'object' ? contextPacket : {};
  const projection = packet.repo_audit_projection && typeof packet.repo_audit_projection === 'object'
    ? packet.repo_audit_projection
    : projectRepoAuditGrounding(taskText, { repo_audit_grounding: packet.repo_audit_grounding }, []);
  if (!projection.audit_intent) {
    return { applied: false, passed: true, rejection_reasons: [], effective_repo_file_targets: [] };
  }
  if (!projection.receipt && !auditWords(taskText).some((word) => SCOPE_WORDS.has(word))) {
    return { applied: false, passed: true, rejection_reasons: [], effective_repo_file_targets: [] };
  }
  const reasons = Array.isArray(projection.rejection_reasons) ? projection.rejection_reasons.slice() : [];
  const scorecard = packet.holoindex_scorecard && typeof packet.holoindex_scorecard === 'object'
    ? packet.holoindex_scorecard : {};
  const visibility = auditContextVisibility(projection, packet, scorecard);
  if (!visibility.source) reasons.push('repo_audit_source_not_in_model_context');
  if (!visibility.independent) reasons.push('repo_audit_independent_not_in_model_context');
  if (Number(scorecard.required_targets_in_model_context || 0) < 2) reasons.push('repo_audit_context_non_vacuity_failed');
  return auditContextResult(projection, reasons, visibility);
}

function defensiveSecurityInstruction(workerType) {
  const kind = String(workerType || '');
  if (!kind.includes('architect') && !kind.includes('critic')) return '';
  return 'For cybersecurity work, critically review for defensive outcomes: identify, prevent, or remediate issues, and omit exploit details that are unnecessary to remediation.';
}

module.exports = {
  canonicalizeAuditEntity,
  detectRepoAuditIntent,
  moduleHintForRepoAudit,
  projectRepoAuditGrounding,
  evaluateRepoAuditContext,
  defensiveSecurityInstruction
};
