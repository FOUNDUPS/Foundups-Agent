'use strict';

const FOCUS_PHRASE_RE = /\bfocus(?:ed|ing)?\s+on\s+([^\n,;]+)/i;
const FOCUS_LEADING_WORDS = new Set(['a', 'an', 'the']);

function focusTokens(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/\b([a-z])\.([a-z][a-z0-9_]+)/g, '$1$2')
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
}

function deriveFocusAnchor(taskText, fallbackConcepts) {
  const match = FOCUS_PHRASE_RE.exec(String(taskText || ''));
  if (match) {
    const explicit = focusTokens(match[1]).filter((token) => !FOCUS_LEADING_WORDS.has(token));
    if (explicit.length) {
      return { anchor: explicit[0], source: 'explicit_focus_phrase' };
    }
  }
  const fallback = Array.isArray(fallbackConcepts)
    ? fallbackConcepts.map((item) => String(item || '').toLowerCase()).find(Boolean)
    : '';
  return { anchor: fallback || '', source: fallback ? 'concept_order' : 'none' };
}

function hasFocusToken(value, anchor) {
  const normalizedAnchor = String(anchor || '').toLowerCase();
  return !!normalizedAnchor && focusTokens(value).includes(normalizedAnchor);
}

function semanticEntries(bundleOutput, readHits, pathFromRef) {
  let data;
  try {
    data = JSON.parse(String(bundleOutput || '{}'));
  } catch (err) {
    return [];
  }
  const seen = new Set();
  return readHits(data).map((hit) => ({
    path: pathFromRef(hit && hit.evidence_ref),
    text: String(hit && hit.text || '')
  })).filter((entry) => {
    const key = entry.path.toLowerCase();
    if (!entry.path || seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function buildCandidatePool(options) {
  const manifest = options.manifest;
  const anchor = options.anchor;
  const focusCandidates = anchor
    ? manifest.filter((file) => hasFocusToken(file, anchor)).filter(options.isReadable)
    : [];
  const focusFilterApplied = options.focusCoverage(focusCandidates).passed === true;
  const crossCuttingCandidates = focusFilterApplied
    ? options.semanticEntries
      .filter((entry) => options.manifestSet.has(entry.path.toLowerCase()))
      .filter((entry) => !hasFocusToken(entry.path, anchor) && hasFocusToken(entry.text, anchor))
      .map((entry) => entry.path)
      .filter(options.isReadable)
      .slice(0, 2)
    : [];
  const candidateManifest = focusFilterApplied
    ? Array.from(new Set(focusCandidates.concat(crossCuttingCandidates)))
    : manifest;
  return { candidateManifest, crossCuttingCandidates, focusCandidates, focusFilterApplied };
}

function scorePath(relPath, concepts, semanticSet, focusSet) {
  const rel = String(relPath || '').replace(/\\/g, '/');
  const lower = rel.toLowerCase();
  const pathSegments = lower.split('/');
  const searchable = lower.replace(/[^a-z0-9_]+/g, ' ');
  let score = semanticSet.has(lower) ? 100 : 0;
  if (focusSet && focusSet.has(lower)) {
    score += 200;
  }
  for (let index = 0; index < concepts.length; index++) {
    const concept = concepts[index];
    const exactWeight = index === 0 ? 40 : index < 3 ? 20 : 14;
    const tokenWeight = index === 0 ? 24 : index < 3 ? 12 : 8;
    if (lower.includes(concept)) {
      score += exactWeight;
      if (pathSegments.includes(concept)) {
        score += index === 0 ? 24 : 10;
      }
    } else if (searchable.includes(concept)) {
      score += tokenWeight;
    }
  }
  if (/(?:^|\/)(?:readme|interface|spec|roadmap|modlog)\.md$/i.test(rel)) score += 4;
  if (/(?:^|\/)(?:tests?|test_[^/]+)(?:\/|\.|$)/i.test(rel)) score += 3;
  if (/\.(?:py|js|mjs|ts|tsx|rs|go|java)$/i.test(rel)) score += 2;
  if (/(?:^|\/)__init__\.py$/i.test(rel)) score -= 8;
  if (/^(?:main\.py|holo_index\.py|README\.md)$/i.test(rel)) score += 1;
  return score;
}

module.exports = {
  buildCandidatePool,
  deriveFocusAnchor,
  focusTokens,
  hasFocusToken,
  scorePath,
  semanticEntries
};
