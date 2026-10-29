assert.strictEqual(orchestrator.isRepoDeepDiveRequest(rddAttentionPrompt), true,
  'RDD-001A: generic codebase-attention request is a repository deep dive');
assert.strictEqual(orchestrator.isRepoDeepDiveRequest(
  'I need advice: what in the codebase needs attention?'
), true, 'RDD-001A: an earlier need token cannot hide a later deep-dive request');
assert.strictEqual(orchestrator.isRepoDeepDiveRequest(
  'look at the codebase what' + ' '.repeat(200000) + 'needs attention?'
), true, 'RDD-001A: long spacing must remain linear and preserve attention intent');
assert.deepStrictEqual(orchestrator.repoDeepDiveConcepts(rddAttentionPrompt), [],
  'RDD-001A: generic attention words cannot become misleading subsystem concepts');
assert.strictEqual(orchestrator.isRepoDeepDiveRequest('Explain this function.'), false, 'RDD-001: ordinary question is not a repository deep dive');
assert.strictEqual(orchestrator.moduleHintFromActive(root, rddPrompt), '', 'RDD-002: repo-wide audit ignores active-editor module bias');
const rddConcepts = orchestrator.repoDeepDiveConcepts(rddPrompt);
assert(rddConcepts.includes('pfmall'), 'RDD-003: dotted product name contributes a searchable concept');
const rddBundle = JSON.stringify({
  task_retrieval: {
    code_hits: [
      { location: 'public/member/js/shell-bridge-interceptor.js:1', content: 'generic runtime architecture semantic decoy' },
      { location: 'modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py:1', content: 'cross-cutting p.fMALL runtime router' },
      { location: 'modules/foundups/pfmall/http_api.py:1', content: 'p.fMALL HTTP API runtime' },
      { location: 'modules/foundups/pfmall/tests/test_http_api.py:1', content: 'p.fMALL HTTP API tests' },
      { location: 'modules/foundups/docs/PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md:1', content: 'p.fMALL route contract' }
    ],
    metadata: { retrieval_mode: 'semantic', code_count: 3, wsp_count: 1 }
  }
});
const rddGovernedGitExecutable = require(path.join(extDir, 'governed_git_executable.js'));
const rddOriginalBind = rddGovernedGitExecutable.bind;
let rddDiscovery;
let rddFallbackIndex; const rddFallbackFixture = fixtures.createRepoDeepDiveFallbackFixture(root); process.once('exit', rddFallbackFixture.cleanup);
rddGovernedGitExecutable.bind = () => { throw new Error('forced governed Git unavailable'); };
try {
  rddDiscovery = orchestrator.discoverRepoDeepDiveTargets(rddFallbackFixture.root, rddPrompt, rddBundle, 12);
  rddFallbackIndex = orchestrator.repoFileIndex(rddFallbackFixture.root, 20000);
} finally {
  rddGovernedGitExecutable.bind = rddOriginalBind;
}
assert.strictEqual(rddDiscovery.manifest_generated, true, 'RDD-003: manifest generated');
assert(rddDiscovery.manifest_file_count > 0, 'RDD-003: manifest is non-empty');
assert.strictEqual(rddDiscovery.manifest_truncated || rddFallbackIndex.some((file) => /^(?:\.claude\/worktrees|\.worktrees|\.cache|\.next|foundups-mcp-env|\.reddog_test_tmp|\.pytest_tmp|\.pytest_cache|\.mypy_cache|\.ruff_cache)\//.test(file)), false, 'RDD-003: complete repository fixture excludes local administrative/runtime trees');
assert(rddFallbackIndex.includes('.claude/CLAUDE.md'), 'RDD-003: tracked-like .claude guidance remains discoverable');
assert(rddDiscovery.targets.length > 0 && rddDiscovery.targets.length <= 12, 'RDD-003: bounded non-empty targets');
assert(rddDiscovery.targets.some((p) => /modules\/foundups\/pfmall\/[^/]+\.py$/i.test(p)), 'RDD-004: implementation target selected');
assert(rddDiscovery.targets.some((p) => /(?:^|\/)tests?(?:\/|_)/i.test(p)), 'RDD-004: test target selected');
assert(rddDiscovery.targets.some((p) => /\.md$/i.test(p)), 'RDD-004: contract/document target selected');
assert(!rddDiscovery.targets.some((p) => /extensions\/reddog\/extension\.js$/i.test(p)), 'RDD-004: RedDog self-file cannot satisfy discovery');
assert.strictEqual(rddDiscovery.focus_coverage_passed, true,
  'RDD-004: selected evidence covers implementation, test, and document for the focus anchor');
assert.strictEqual(rddDiscovery.focus_filter_applied, true,
  'RDD-004: a complete p.fMALL corpus activates focus-bound selection');
assert(rddDiscovery.focus_candidate_count >= 3,
  'RDD-004: focus-bound selection records its eligible corpus size');
assert(rddDiscovery.semantic_paths.includes('public/member/js/shell-bridge-interceptor.js'),
  'RDD-004: the generic semantic decoy is observed before focus filtering');
assert(rddFallbackIndex.includes('main.py'),
  'RDD-004: bounded fallback observes policy-admitted root files');
assert(rddFallbackIndex.includes('docs/README.md'),
  'RDD-004: bounded fallback observes repository documentation trees');
assert(rddFallbackIndex.includes('WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md'),
  'RDD-004: bounded fallback observes the WSP authority tree');
assert(!rddDiscovery.targets.includes('public/member/js/shell-bridge-interceptor.js'),
  'RDD-004: generic semantic decoy cannot consume focused evidence budget');
assert(rddDiscovery.targets.includes('modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py'),
  'RDD-004: semantic cross-cutting evidence that names p.fMALL retains a bounded slot');
assert.deepStrictEqual(rddDiscovery.cross_cutting_targets,
  ['modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py'],
  'RDD-004: cross-cutting targets are explicit and bounded');
assert(rddDiscovery.targets.filter((p) => repoDeepDiveFocusPolicy.hasFocusToken(p, 'pfmall')).length >= 3,
  'RDD-004: semantic dependencies cannot displace the focused implementation/test/doc core');
assert.strictEqual(repoDeepDiveFocusPolicy.hasFocusToken('modules/small/runtime.py', 'mall'), false,
  'RDD-004: focus matching is token-bound, not substring-bound');
assert.strictEqual(repoDeepDiveFocusPolicy.hasFocusToken('modules/rapid/api.py', 'api'), true,
  'RDD-004: exact path tokens remain eligible');
assert.strictEqual(repoDeepDiveFocusPolicy.hasFocusToken('modules/rapid/runtime.py', 'api'), false,
  'RDD-004: api cannot match rapid');
const rddHostTyped = orchestrator.extractTypedTargets(rddHostPrompt);
assert.deepStrictEqual(rddHostTyped.external_research_targets, [],
  'RDD-010: a repository deep dive is not an external-research request');
const rddHostConcepts = orchestrator.repoDeepDiveConcepts(rddHostPrompt);
assert.deepStrictEqual(rddHostConcepts, ['pfmall', 'runtime'],
  'RDD-010: instruction/WSP words cannot outrank the named subsystem');
const rddHostDiscovery = orchestrator.discoverRepoDeepDiveTargets(root, rddHostPrompt, JSON.stringify({
  task_retrieval: { code_hits: [], metadata: { retrieval_mode: 'lexical' } }
}), 12);
assert(rddHostDiscovery.targets.some((p) => /^modules\/foundups\/pfmall\/[^/]+\.py$/i.test(p)),
  'RDD-010: local manifest discovery selects p.fMALL implementation; targets=' + JSON.stringify(rddHostDiscovery.targets));
assert(rddHostDiscovery.targets.some((p) => /^modules\/foundups\/pfmall\/tests\//i.test(p)),
  'RDD-010: local manifest discovery selects p.fMALL verification');
assert(rddHostDiscovery.targets.some((p) => /PFMALL.*\.md$/i.test(p)),
  'RDD-010: local manifest discovery selects p.fMALL contract/document evidence');
assert.strictEqual(rddHostDiscovery.focus_anchor, 'pfmall', 'RDD-010: p.fMALL is the focus anchor');
assert.strictEqual(rddHostDiscovery.focus_coverage_passed, true,
  'RDD-010: local evidence quorum is tied to p.fMALL, not generic repository files');
assert.strictEqual(rddHostDiscovery.focus_filter_applied, true,
  'RDD-010: host prompt uses only the complete p.fMALL evidence corpus');
assert.strictEqual(rddHostDiscovery.focus_anchor_source, 'explicit_focus_phrase',
  'RDD-010: host focus anchor comes from the explicit focusing-on phrase');
const rddNoisyFocus = orchestrator.discoverRepoDeepDiveTargets(root,
  'Please audit production runtime in the repository, focusing on p.fMALL.',
  JSON.stringify({ task_retrieval: { code_hits: [], metadata: { retrieval_mode: 'semantic' } } }), 12);
assert.strictEqual(rddNoisyFocus.focus_anchor, 'pfmall',
  'RDD-010: leading prose cannot replace the explicit subsystem focus');
(function rddManifestCompletenessTruth() {
  const indexed = orchestrator.repoFileIndexFromTrackedOutput(
    'modules/foundups/pfmall/api.py\n' + 'x'.repeat(1000100), 20000);
  assert.strictEqual(indexed.manifest_truncated, true,
    'RDD-010: character-truncated git manifests cannot claim completeness');
  assert.strictEqual(indexed.manifest_source_count, 2,
    'RDD-010: manifest source count remains explicit after character truncation');
  assert.strictEqual(orchestrator.repoFileIndexFromTrackedOutput(null, 20000), null,
    'RDD-010: non-string tracked output fails closed');
  assert.strictEqual(orchestrator.repoFileIndexFromTrackedOutput(Object.create(null), 20000), null,
    'RDD-010: hostile tracked-output objects fail closed before property access');
  for (const invalidMax of ['20000', true, 0, 20001]) {
    assert.strictEqual(orchestrator.repoFileIndexFromTrackedOutput('main.py', invalidMax), null,
      'RDD-010: non-exact or out-of-range manifest bounds fail closed');
  }
})();
assert(!rddHostDiscovery.targets.some((p) => /(?:livechat|banter|worker_help|help_command)/i.test(p)),
  'RDD-010: unrelated generic runtime/worker files cannot enter the host evidence packet');
const rddBroadFallback = orchestrator.discoverRepoDeepDiveTargets(root,
  'Complete deep dive into the FoundUps-Agent repository, focusing on quuxzz runtime architecture.',
  JSON.stringify({
    task_retrieval: {
      code_hits: [{ location: 'main.py:1', content: 'repository runtime entry point' }],
      metadata: { retrieval_mode: 'semantic' }
    }
  }), 12);
assert.strictEqual(rddBroadFallback.focus_filter_applied, false,
  'RDD-010: incomplete focus corpora retain the broad fail-closed discovery path');
assert(rddBroadFallback.targets.includes('main.py'),
  'RDD-010: broad fallback retains generation-bound semantic candidates');
const rddAugmented = orchestrator.taskTextWithDiscoveredRepoTargets(rddPrompt, rddDiscovery.targets);
const rddCollected = orchestrator.collectRequiredTargets(rddAugmented);
assert.strictEqual(rddCollected.targets.length, rddDiscovery.targets.length, 'RDD-005: discovered paths enter the existing required-target contract');
const rddBlockedGate = orchestrator.evaluateRepoDeepDiveGate({
  repo_deep_dive_requested: true,
  repo_manifest_generated: true,
  repo_manifest_file_count: rddDiscovery.manifest_file_count,
  repo_deep_dive_targets: [],
  direct_read_fetch_attempted: false,
  direct_read_bytes: 0,
  target_recall_ok: 'unknown'
}, null);
assert.strictEqual(rddBlockedGate.passed, false, 'RDD-006: zero-evidence deep dive fails closed');
assert(rddBlockedGate.rejection_reasons.includes('no_repository_targets'), 'RDD-006: zero-target reason surfaced');
assert(rddBlockedGate.rejection_reasons.includes('direct_read_not_attempted'), 'RDD-006: no-read reason surfaced');
const rddPassedGate = orchestrator.evaluateRepoDeepDiveGate({
  repo_deep_dive_requested: true,
  repo_manifest_generated: true,
  repo_manifest_file_count: rddDiscovery.manifest_file_count,
  repo_deep_dive_targets: rddDiscovery.targets,
  repo_deep_dive_focus_coverage_passed: true,
  direct_read_fetch_attempted: true,
  direct_read_bytes: 1234,
  target_recall_ok: true
}, { chars: 1234 });
assert.strictEqual(rddPassedGate.passed, true, 'RDD-007: source-bearing deep dive passes');
const rddWrongFocusGate = orchestrator.evaluateRepoDeepDiveGate({
  repo_deep_dive_requested: true,
  repo_manifest_generated: true,
  repo_manifest_file_count: 3,
  repo_deep_dive_targets: ['modules/other/runtime.py', 'modules/other/tests/test_runtime.py', 'modules/other/README.md'],
  repo_deep_dive_focus_coverage_passed: false,
  direct_read_fetch_attempted: true,
  direct_read_bytes: 1234,
  target_recall_ok: true
}, { chars: 1234 });
assert.strictEqual(rddWrongFocusGate.passed, false,
  'RDD-007: readable but off-focus files cannot satisfy a repository deep dive');
assert(rddWrongFocusGate.rejection_reasons.includes('repository_focus_coverage_incomplete'),
  'RDD-007: focus-coverage rejection is explicit');
const rddFilterViolationGate = orchestrator.evaluateRepoDeepDiveGate({
  repo_deep_dive_requested: true, repo_manifest_generated: true, repo_manifest_file_count: 3,
  repo_deep_dive_targets: ['modules/foundups/pfmall/api.py', 'modules/other/unrelated.py'],
  repo_deep_dive_focus_anchor: 'pfmall', repo_deep_dive_focus_filter_applied: true,
  repo_deep_dive_focus_coverage_passed: true, direct_read_fetch_attempted: true,
  direct_read_bytes: 1234, target_recall_ok: true
}, { chars: 1234 });
assert(rddFilterViolationGate.rejection_reasons.includes('repository_focus_filter_violation'),
  'RDD-007: focus-filter metadata cannot authorize an off-focus target');
const rddTruncatedManifestGate = orchestrator.evaluateRepoDeepDiveGate({
  repo_deep_dive_requested: true, repo_manifest_generated: true, repo_manifest_file_count: 18000,
  repo_manifest_truncated: true, repo_deep_dive_targets: rddDiscovery.targets,
  repo_deep_dive_focus_coverage_passed: true, direct_read_fetch_attempted: true,
  direct_read_bytes: 1234, target_recall_ok: true
}, { chars: 1234 });
assert(rddTruncatedManifestGate.rejection_reasons.includes('repository_manifest_truncated'),
  'RDD-007: capped repository manifest is explicit and fails closed');
const rddBlockedPreflight = orchestrator.buildTypedGroundingPreflight(rddPrompt, 'wsp_holo', {
  holoindex_scorecard: {
    repo_deep_dive_requested: true,
    repo_deep_dive_gate_passed: false,
    repo_deep_dive_gate_rejection_reasons: ['no_repository_targets'],
    repo_deep_dive_targets: [],
    target_recall_ok: 'unknown',
    required_targets_missing: [],
    semantic_evidence_hits: []
  }
});
assert.strictEqual(rddBlockedPreflight.passed, false, 'RDD-007: failed deep-dive gate blocks grounding');
assert(rddBlockedPreflight.rejection_reasons.includes('repo_deep_dive_evidence_incomplete'), 'RDD-007: preflight surfaces deep-dive failure');
assert.strictEqual(rddBlockedPreflight.no_model_call_when_failed, true, 'RDD-007: failed deep dive cannot call Fusion');
const rddAttentionBlockedPreflight = orchestrator.buildTypedGroundingPreflight(rddAttentionPrompt, 'wsp_holo', {
  holoindex_scorecard: {
    repo_deep_dive_requested: true,
    repo_deep_dive_gate_passed: false,
    repo_deep_dive_gate_rejection_reasons: ['direct_read_not_attempted'],
    repo_deep_dive_targets: [],
    target_recall_ok: 'unknown',
    required_targets_missing: [],
    semantic_evidence_hits: []
  }
});
assert.strictEqual(rddAttentionBlockedPreflight.passed, false,
  'RDD-007A: codebase-attention request cannot reach Fusion without repository evidence');
assert(rddAttentionBlockedPreflight.rejection_reasons.includes('repo_deep_dive_evidence_incomplete'),
  'RDD-007A: generic attention request exposes deep-dive evidence failure');
const rddScorecard = orchestrator.extractHoloIndexScorecard('wsp_holo', {
  repo_deep_dive_requested: true,
  repo_manifest_generated: true,
  repo_manifest_file_count: rddDiscovery.manifest_file_count,
  repo_manifest_source_count: rddDiscovery.manifest_source_count,
  repo_manifest_truncated: false,
  repo_manifest_complete: true,
  repo_deep_dive_targets: rddDiscovery.targets,
  repo_deep_dive_targets_count: rddDiscovery.targets.length,
  repo_deep_dive_focus_anchor: rddDiscovery.focus_anchor,
  repo_deep_dive_focus_anchor_source: rddDiscovery.focus_anchor_source,
  repo_deep_dive_focus_filter_applied: rddDiscovery.focus_filter_applied,
  repo_deep_dive_focus_candidate_count: rddDiscovery.focus_candidate_count,
  repo_deep_dive_focus_match_mode: rddDiscovery.focus_match_mode,
  repo_deep_dive_pool_strategy: rddDiscovery.pool_strategy,
  repo_deep_dive_cross_cutting_targets: rddDiscovery.cross_cutting_targets,
  repo_deep_dive_fallback_reason: rddDiscovery.fallback_reason,
  repo_deep_dive_focus_coverage: rddDiscovery.focus_coverage,
  repo_deep_dive_focus_coverage_passed: true,
  repo_deep_dive_gate_applied: true,
  repo_deep_dive_gate_passed: true,
  repo_deep_dive_gate_rejection_reasons: []
});
const rddLines = orchestrator.formatHoloIndexScorecardLines(rddScorecard).join('\n');
includes(rddLines, '- repo_deep_dive_gate_passed: true', 'RDD-008: Run Trace exposes acceptance gate');
includes(rddLines, '- repo_deep_dive_targets_count: ' + rddDiscovery.targets.length, 'RDD-008: Run Trace exposes target count');
includes(rddLines, '- repo_manifest_truncated: false', 'RDD-008: Run Trace exposes manifest completeness');
includes(rddLines, '- repo_manifest_complete: true', 'RDD-008: Run Trace distinguishes complete manifests');
includes(rddLines, '- repo_deep_dive_focus_coverage_passed: true', 'RDD-008: Run Trace exposes focus coverage');
includes(rddLines, '- repo_deep_dive_focus_filter_applied: true', 'RDD-008: Run Trace exposes focus filtering');
includes(rddLines, '- repo_deep_dive_focus_anchor_source: explicit_focus_phrase', 'RDD-008: Run Trace exposes focus provenance');
includes(rddLines, '- repo_deep_dive_pool_strategy: focus_core_plus_semantic_cross_cutting', 'RDD-008: Run Trace exposes pool strategy');

(function rdd009RealBundleRegression() {
  const targets = rddDiscovery.targets.concat(['modules/ai_intelligence/pfmall_discovery/README.md']); const hits = targets.map((target) => ({ location: target, need: 'governed direct-read target', content: 'evidence for ' + target, direct_read: true }));
  const bundle = { task_retrieval: { code_hits: hits, wsp_hits: [], metadata: { retrieval_mode: 'lexical', embedding_backend: 'none', code_count: hits.length, wsp_count: 0, no_holoindex_reindex_performed: true } }, direct_read: { direct_read_fallback_used: true, direct_read_paths: targets, direct_read_rejected: [], direct_read_bytes: hits.reduce((total, hit) => total + hit.content.length, 0), direct_read_truncated: [] } };
  const result = orchestrator.holoIndexOutput(rddFallbackFixture.root, rddPrompt, 18000, { baseResult: { ok: true, bundle_ok: true, bundle, owner_attempts: 0, no_holoindex_reindex_performed: true }, allowBundleOnlyBridge: false });
  const meta = result && result.meta ? result.meta : {};
  assert.strictEqual(meta.repo_deep_dive_requested, true, 'RDD-009: runtime marks the deep-dive request');
  assert.strictEqual(meta.repo_manifest_generated, true, 'RDD-009: runtime creates the tracked-file manifest');
  assert(meta.repo_manifest_file_count > 0, 'RDD-009: runtime manifest is non-empty');
  assert(meta.repo_deep_dive_targets_count > 0, 'RDD-009: runtime derives source targets');
  assert.strictEqual(meta.direct_read_fetch_attempted, true, 'RDD-009: one-shot owner direct-read evidence is receipt-visible');
  assert(meta.direct_read_bytes > 0, 'RDD-009: runtime reads nonzero source bytes');
  assert.strictEqual(meta.target_recall_ok, true, 'RDD-009: every discovered source target is recalled; missing=' + JSON.stringify(meta.required_targets_missing));
  assert.strictEqual(meta.repo_deep_dive_gate_passed, true, 'RDD-009: source-bearing runtime deep dive passes');
  assert(result.direct_read_section && result.direct_read_section.chars > 0, 'RDD-009: source context reaches the bounded packet');
})();

function assertRdd011Failure(result) {
  const meta = result.meta || {};
  assert.strictEqual(meta.holoindex_owner_query_ok, false, 'RDD-011: semantic owner failure remains explicit');
  assert.notStrictEqual(meta.direct_read_fetch_attempted, true, 'RDD-011: owner failure cannot invoke a raw fallback');
  assert.strictEqual(meta.target_recall_ok, false, 'RDD-011: failed owner cannot claim target recall');
  assert.strictEqual(Number(meta.direct_read_bytes || 0), 0, 'RDD-011: failed owner supplies no source bytes');
  assert.strictEqual(meta.repo_deep_dive_focus_coverage_passed, true,
    'RDD-011: local manifest category coverage remains distinct from source recall');
  assert.strictEqual(meta.repo_deep_dive_gate_passed, false,
    'RDD-011: repository evidence gate fails closed');
  assert(!result.direct_read_section || result.direct_read_section.chars === 0,
    'RDD-011: failed owner supplies no direct-read source context');
  assert.strictEqual(meta.no_holoindex_reindex_performed, true,
    'RDD-011: failed owner path performs no reindex');
}

function assertRdd011Preflight(meta) {
  const scorecard = orchestrator.extractHoloIndexScorecard('wsp_holo', meta);
  const preflight = orchestrator.buildTypedGroundingPreflight(rddHostPrompt, 'wsp_holo', {
    holoindex_scorecard: scorecard
  });
  assert.strictEqual(preflight.external_research_targets_count, 0,
    'RDD-011: repository wording cannot invent external research');
  assert.strictEqual(preflight.semantic_targets_required, 1,
    'RDD-011: unresolved repository audit intent remains a required semantic target');
  assert.strictEqual(preflight.passed, false,
    'RDD-011: repository-only audit cannot reach Fusion without evidence');
}

(function rdd011OwnerFailureFailsClosed() {
  const originalMode = process.env.REDDOG_HOLO_RETRIEVAL_MODE;
  process.env.REDDOG_HOLO_RETRIEVAL_MODE = 'semantic';
  try {
    const result = orchestrator.holoIndexOutput(root, rddHostPrompt, 18000, {
      baseResult: hsfOwnerFailure,
      allowBundleOnlyBridge: false
    });
    const meta = result.meta || {};
    assertRdd011Failure(result);
    assertRdd011Preflight(meta);
  } finally {
    if (originalMode === undefined) {
      delete process.env.REDDOG_HOLO_RETRIEVAL_MODE;
    } else {
      process.env.REDDOG_HOLO_RETRIEVAL_MODE = originalMode;
    }
  }
})();

// REDDOG_HOLOINDEX_GENERATION_BOUND_QUERY_RUNTIME_PHASE1 (HGBQ-001..010): only the
// authenticated owner response may supply semantic hit authority. The legacy direct
// bundle remains useful for structured-memory assembly and governed explicit direct read.
const hgbqGeneration = 'sha256:' + 'a'.repeat(64);
const hgbqFreshnessDigest = 'sha256:' + 'b'.repeat(64);
const hgbqHead = 'c'.repeat(40);
const hgbqRootDigest = 'sha256:' + 'd'.repeat(64);
const hgbqRankerDigest = 'sha256:' + 'e'.repeat(64);
const hgbqRuntimeDigest = 'sha256:' + 'f'.repeat(64);
const hgbqSemanticEvidence = {
  schema_version: 'holoindex_semantic_evidence.v1',
  code_hits: [{ path: 'modules/foundups/pfmall/api.py', preview: 'PFMall implementation API.' }],
  wsp_hits: [],
  test_hits: [{ path: 'modules/foundups/pfmall/tests/test_api.py', summary: 'PFMall API verification.' }],
  skill_hits: [],
  symbol_hits: [],
  docs_hits: [],
  knowledge_hits: [],
  work_ledger_hits: [],
  metadata: { retrieval_mode: 'semantic', embedding_backend: 'sentence_transformers' }
};
const hgbqSemanticEvidenceJson = JSON.stringify(hgbqSemanticEvidence);
const hgbqReceipt = {
  schema_version: 'holoindex_query_receipt.v1',
  source: 'holoindex_owner_service',
  source_class: 'holoindex',
  ok: true,
  query: 'audit pfmall',
  freshness: 'CURRENT',
  hits: [],
  error: '',
  freshness_generation_id: hgbqGeneration,
  freshness_receipt_digest: hgbqFreshnessDigest,
  freshness_receipt_path: 'E:/HoloIndex/indexes/holoindex_freshness_receipt.json',
  repo_head_sha: hgbqHead,
  repo_root_digest: hgbqRootDigest,
  workspace_repo_head_sha: hgbqHead,
  authority_repo_head_sha: hgbqHead,
  authority_repo_root_digest: hgbqRootDigest,
  workspace_overlay_present: true,
  semantic_evidence_authority: 'committed_head_only',
  no_authority_worktree_mutation_performed: true,
  index_gap_detected: false,
  stale_reasons: [],
  no_holoindex_reindex_performed: true,
  retrieval_runtime_ranker_digest: hgbqRankerDigest,
  runtime_environment_digest: hgbqRuntimeDigest,
  runtime_environment_exact_closure_verified: false,
  semantic_evidence_digest: holoGenerationBoundQuery.semanticEvidenceDigest(hgbqSemanticEvidenceJson),
  semantic_evidence_count: 2
};
hgbqReceipt.receipt_id = holoGenerationBoundQuery.queryReceiptId(hgbqReceipt);
const hgbqReceiptId = hgbqReceipt.receipt_id;
