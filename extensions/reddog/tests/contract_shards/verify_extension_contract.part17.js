const imperativeHoloUnrelated = orchestrator.buildTypedGroundingPreflight(imperativeHoloPrompt, 'wsp_holo', {
  semantic_evidence_hits: [{
    location: 'modules/foundups/pfmall/src/pfmall_dae.py:1',
    title: 'PFMall runtime'
  }]
});
assert.strictEqual(imperativeHoloUnrelated.passed, false,
  'TGP-008B: unrelated evidence cannot satisfy an imperative HoloIndex request');
const coordinatedImperative = 'continue do the work needed to enhance HoloIndex and OpenClaw';
const coordinatedPartial = orchestrator.buildTypedGroundingPreflight(coordinatedImperative, 'wsp_holo', {
  semantic_evidence_hits: [{
    location: 'holo_index/core/search_engine.py:1',
    title: 'HoloIndex and semantic search engine'
  }]
});
assert.strictEqual(coordinatedPartial.passed, false,
  'TGP-008C: evidence for only one coordinated subject cannot ground the entire request');
const coordinatedPass = orchestrator.buildTypedGroundingPreflight(coordinatedImperative, 'wsp_holo', {
  semantic_evidence_hits: [{
    location: 'docs/reddog_holo_openclaw.md',
    title: 'HoloIndex and OpenClaw integration'
  }]
});
assert.strictEqual(coordinatedPass.passed, true,
  'TGP-008C: evidence naming every coordinated subject can ground the request');
for (const connector of ['then', 'along with', 'as well as']) {
  const alternateCoordinated = 'fix HoloIndex ' + connector + ' OpenClaw';
  const alternatePartial = orchestrator.buildTypedGroundingPreflight(alternateCoordinated, 'wsp_holo', {
    semantic_evidence_hits: [{
      location: 'holo_index/core/search_engine.py:1',
      title: 'HoloIndex ' + connector + ' semantic search'
    }]
  });
  assert.strictEqual(alternatePartial.passed, false,
    'TGP-008C: connector cannot substitute for missing OpenClaw evidence: ' + connector);
  const alternatePass = orchestrator.buildTypedGroundingPreflight(alternateCoordinated, 'wsp_holo', {
    semantic_evidence_hits: [{
      location: 'docs/reddog_holo_openclaw.md',
      title: 'HoloIndex OpenClaw integration'
    }]
  });
  assert.strictEqual(alternatePass.passed, true,
    'TGP-008C: every subject remains groundable across connector syntax: ' + connector);
}
for (const explicitWord of ['Enhance', 'Continue']) {
  const explicitPrompt = 'Semantic target: ' + explicitWord;
  const explicitPreflight = orchestrator.buildTypedGroundingPreflight(explicitPrompt, 'wsp_holo', {
    semantic_evidence_hits: [{
      location: 'docs/' + explicitWord.toLowerCase() + '.md',
      title: explicitWord + ' language concept'
    }]
  });
  assert.strictEqual(explicitPreflight.passed, true,
    'TGP-008D: explicit operator target preserves an inferred-command stopword: ' + explicitWord);
}
const quotedEnhance = orchestrator.buildTypedGroundingPreflight(
  'What does the word "enhance" mean?', 'wsp_holo', {}
);
assert.strictEqual(quotedEnhance.grounding_target_universe_required, false,
  'TGP-008E: a quoted action-word mention does not activate semantic work');
assert.deepStrictEqual(quotedEnhance.typed_targets.semantic_targets, [],
  'TGP-008E: a quoted action-word mention does not invent a semantic target');
const smartQuotedEnhance = orchestrator.buildTypedGroundingPreflight(
  'What does the word \u201cenhance\u201d mean?', 'wsp_holo', {}
);
assert.strictEqual(smartQuotedEnhance.grounding_target_universe_required, false,
  'TGP-008E: a smart-quoted action-word mention does not activate semantic work');
assert.deepStrictEqual(smartQuotedEnhance.typed_targets.semantic_targets, [],
  'TGP-008E: a smart-quoted action-word mention does not invent a semantic target');
const escapedQuotedEnhance = orchestrator.extractTypedTargets(
  String.raw`{"message":"please \"enhance\" output"}`
);
assert.deepStrictEqual(escapedQuotedEnhance.semantic_targets, [],
  'TGP-008E: escaped nested quotes cannot leak quoted action words');
assert.strictEqual(
  semanticGroundingPolicy.hasSemanticWorkAction(String.raw`"quoted \\" enhance HoloIndex`),
  true,
  'TGP-008E: an even backslash run leaves the quote delimiter active'
);
const quoteStressStarted = Date.now();
const quoteStressTargets = orchestrator.extractTypedTargets(
  '\u201c'.repeat(100000) + '\\'.repeat(100000) + '"enhance"'
);
assert(Date.now() - quoteStressStarted < 1000,
  'TGP-008E: pathological quote/escape input remains bounded under the single-pass scanner');
assert.deepStrictEqual(quoteStressTargets.semantic_targets, [],
  'TGP-008E: pathological quote/escape input cannot activate semantic work');
const ambiguousImperative = orchestrator.buildTypedGroundingPreflight(
  'continue do the work needed to fix enhance it', 'wsp_holo', {
    semantic_evidence_hits: [{
      location: 'holo_index/core/search_engine.py:1',
      title: 'HoloIndex semantic search engine'
    }]
  }
);
assert.strictEqual(ambiguousImperative.passed, false,
  'TGP-008F: a subjectless imperative follow-up remains fail-closed');
assert(ambiguousImperative.rejection_reasons.includes('grounding_target_universe_empty'),
  'TGP-008F: subjectless follow-up reports an empty grounding universe');
const emptyAuditPreflight = orchestrator.buildTypedGroundingPreflight('Audit it.', 'wsp_holo', {
  semantic_evidence_hits: []
});
assert.strictEqual(emptyAuditPreflight.passed, false, 'TGP-009: unparseable substantive audit cannot pass vacuously');
assert(emptyAuditPreflight.rejection_reasons.includes('grounding_target_universe_empty'), 'TGP-009: empty target universe has a stable fail-closed reason');
assert.strictEqual(emptyAuditPreflight.no_model_call_when_failed, true, 'TGP-010: empty target universe blocks before Fusion');
const identityPreflight = orchestrator.buildTypedGroundingPreflight('Are you RedDog?', 'none', {});
assert.strictEqual(identityPreflight.passed, true, 'TGP-011: simple identity prompt remains exempt from grounding targets');
assert.strictEqual(identityPreflight.grounding_target_universe_required, false, 'TGP-011: identity fast path does not require target evidence');
const diagnosticPreflight = orchestrator.buildTypedGroundingPreflight([
  'Assess this Run Trace:',
  '## Run Trace',
  '- extension_version: 0.4.2',
  '- runtime status: stopped',
  '- redaction gate status: BLOCKED_LOCALLY',
  '- made_network_call: false',
  '- stderr: timeout',
  '- warning: worker stopped',
  '- operator message: failed before model output'
].join('\n'), 'none', {});
assert.strictEqual(diagnosticPreflight.passed, true, 'TGP-012: pasted operational diagnostics remain on the local evidence path');
assert.strictEqual(diagnosticPreflight.grounding_target_universe_required, false, 'TGP-012: operational diagnostic payload is exempt');
assert(!/runtime[^\n]{0,80}(?:reindex|--index)/i.test(extensionJs.slice(extensionJs.indexOf('function buildTypedGroundingPreflight'), extensionJs.indexOf('function buildGroundingPreflightBlockedResult'))),
  'TGP-013: grounding preflight remains query-only and never triggers runtime reindex');
const actionableLogPrompt = [
  'Implement a fix for this runtime failure.',
  'DAEmon output:',
  '- runtime status: stopped',
  '- stderr: timeout',
  '- warning: worker failed',
  '- operator message: blocked',
  '- result: error',
  '- output: no model response',
  '- trace: failed'
].join('\n');
assert.strictEqual(orchestrator.isDaemonOutputAssessmentRequest(actionableLogPrompt), true,
  'TGP-014: implementation request containing logs remains typed as diagnostic evidence');
const actionableLogClass = orchestrator.classifyTaskForRedDog(actionableLogPrompt);
assert.strictEqual(actionableLogClass.localFastPath, null,
  'TGP-014: implementation request containing logs cannot terminate on the local diagnostic path');
assert.strictEqual(actionableLogClass.daemonDiagnosticAnalysis, true,
  'TGP-014: implementation request containing logs must reach governed architect analysis');
const actionableLogPreflight = orchestrator.buildTypedGroundingPreflight(actionableLogPrompt, 'wsp_holo', {});
assert.strictEqual(actionableLogPreflight.passed, true,
  'TGP-014: typed diagnostic evidence may reach architect analysis without inventing repository targets');
const actionableGate = orchestrator.buildRuntimeConsumptionGate({
  ok: true,
  redaction: { decision: 'PASSED', made_network_call: true },
  output_validation: { passed: true },
  review_packet: { fusion_panel_quorum: { passed: true } }
}, { validated: true }, 'foundups_fusion', true, actionableLogClass);
assert.strictEqual(actionableLogClass.daemonDiagnosticActionRequested, true,
  'TGP-014: operator implementation prefix is the explicit action request');
assert.strictEqual(actionableGate.passed, true,
  'TGP-014: explicit action may enter existing governed planning after all gates pass');
assert(!actionableGate.rejection_reasons.includes('daemon_diagnostic_analysis_requires_explicit_work_promotion'),
  'TGP-014: explicit action must not require a duplicate promotion phrase');
for (const subjectless of ['Audit it.', 'Research this.', 'Review everything.']) {
  const subjectlessPreflight = orchestrator.buildTypedGroundingPreflight(subjectless, 'wsp_holo', {});
  assert.strictEqual(subjectlessPreflight.passed, false, 'TGP-015: subjectless work must fail: ' + subjectless);
  assert(subjectlessPreflight.rejection_reasons.includes('grounding_target_universe_empty'),
    'TGP-015: subjectless work gets stable empty-universe reason: ' + subjectless);
}
for (const genericSubject of ['Audit kosei.', 'Audit arbitrary_widget.']) {
  assert.strictEqual(orchestrator.extractTypedTargets(genericSubject).semantic_targets.length, 1,
    'TGP-016: arbitrary semantic subject derives without a hardcoded domain noun: ' + genericSubject);
}
const mixedGroundingPrompt = [
  'Audit payment pipeline architecture.',
  'Read first: modules/payments/core.py'
].join('\n');
const mixedTargets = orchestrator.extractTypedTargets(mixedGroundingPrompt);
assert.deepStrictEqual(mixedTargets.repo_file_targets, ['modules/payments/core.py'], 'TGP-017: mixed prompt retains repo target');
assert.deepStrictEqual(mixedTargets.semantic_targets, ['Audit payment pipeline architecture.'], 'TGP-017: mixed prompt retains semantic obligation');
const mixedPreflight = orchestrator.buildTypedGroundingPreflight(mixedGroundingPrompt, 'wsp_holo', {
  holoindex_scorecard: { target_recall_ok: true, required_targets_missing: [] }
});
assert.strictEqual(mixedPreflight.passed, false, 'TGP-017: green file recall cannot replace missing semantic evidence');
assert(mixedPreflight.rejection_reasons.includes('semantic_target_grounding_incomplete'),
  'TGP-017: mixed prompt reports missing semantic grounding');
const pathOnlySemantic = orchestrator.buildTypedGroundingPreflight(broadAuditPrompt, 'wsp_holo', {
  semantic_evidence_hits: [{ location: 'docs/pfmall.md' }]
});
assert.strictEqual(pathOnlySemantic.passed, false, 'TGP-018: matching filename alone is not content-bearing evidence');
const previewSemantic = orchestrator.buildTypedGroundingPreflight(broadAuditPrompt, 'wsp_holo', {
  semantic_evidence_hits: [
    { location: 'modules/pfmall/runtime.py', preview: 'PFMall runtime architecture and current implementation.' },
    { location: 'tests/test_pfmall_runtime.py', summary: 'PFMall runtime behavior verification.' }
  ]
});
assert.strictEqual(previewSemantic.passed, true, 'TGP-018: matching content preview with a citation grounds the target');

// REDDOG_SEMANTIC_GROUNDING_PER_TARGET_PROOF_PHASE1 (SGP-001..012): every semantic target
// needs its own content-bearing HoloIndex evidence. Aggregate code_hits/wsp_hits cannot ground
// unrelated semantic targets.
includes(extensionJs, 'function buildSemanticTargetCoverage', 'SGP-001: per-target semantic coverage builder missing');
const semanticPrompt = [
  'Research topic: alpha lane ledger reconciliation; beta prompt library governance',
  'Determine whether both concepts are grounded.'
].join('\n');
const alphaSemanticHit = {
  location: 'docs/audits/alpha_lane_ledger_reconciliation.md',
  need: 'alpha lane ledger reconciliation evidence',
  title: 'Alpha lane ledger reconciliation'
};
const betaSemanticHit = {
  location: 'docs/contracts/beta_prompt_library_governance.md',
  need: 'beta prompt library governance evidence',
  title: 'Beta prompt library governance'
};
const semanticPartial = orchestrator.buildTypedGroundingPreflight(semanticPrompt, 'wsp_holo', {
  semantic_evidence_hits: [alphaSemanticHit]
});
assert.strictEqual(semanticPartial.passed, false, 'SGP-002: evidence for one of two semantic targets must fail');
assert.strictEqual(semanticPartial.semantic_targets_required, 2, 'SGP-002: both semantic targets are required');
assert.strictEqual(semanticPartial.semantic_targets_grounded, 1, 'SGP-002: only one semantic target is grounded');
assert.deepStrictEqual(semanticPartial.semantic_targets_missing, ['beta prompt library governance'], 'SGP-002: missing semantic target is named');
assert(semanticPartial.rejection_reasons.includes('semantic_target_grounding_incomplete'), 'SGP-002: semantic incomplete reason present');
assert.strictEqual(semanticPartial.semantic_target_coverage[0].verdict, 'SUFFICIENT', 'SGP-002: first target has sufficient coverage');
assert.strictEqual(semanticPartial.semantic_target_coverage[1].verdict, 'UNSAFE_TO_ACT', 'SGP-002: second target fails closed');
assert(semanticPartial.semantic_target_coverage_digest.startsWith('sha256:'), 'SGP-002: coverage digest is bound');

const semanticUnrelated = orchestrator.buildTypedGroundingPreflight(semanticPrompt, 'wsp_holo', {
  holoindex_scorecard: {
    code_hits_count: 1,
    wsp_hits: 4,
    semantic_evidence_hits: [
      { location: 'docs/global_architecture.md', need: 'global architecture overview unrelated to requested targets' }
    ]
  }
});
assert.strictEqual(semanticUnrelated.passed, false, 'SGP-003: unrelated global hits cannot satisfy semantic targets');
assert.strictEqual(semanticUnrelated.semantic_targets_grounded, 0, 'SGP-003: unrelated hit grounds zero targets');

const semanticPass = orchestrator.buildTypedGroundingPreflight(semanticPrompt, 'wsp_holo', {
  semantic_evidence_hits: [alphaSemanticHit, betaSemanticHit]
});
assert.strictEqual(semanticPass.passed, true, 'SGP-004: each semantic target with independent evidence passes');
assert.strictEqual(semanticPass.semantic_targets_grounded, 2, 'SGP-004: both targets are grounded');
assert.deepStrictEqual(semanticPass.semantic_targets_missing, [], 'SGP-004: no missing semantic targets');
assert(semanticPass.semantic_target_coverage.every((record) => record.evidence_refs.length === 1), 'SGP-004: each target carries evidence refs');

const semanticBackendError = orchestrator.buildTypedGroundingPreflight(semanticPrompt, 'wsp_holo', {
  semantic_evidence_hits: [alphaSemanticHit, betaSemanticHit],
  semantic_target_errors: {
    'beta prompt library governance': 'backend_error'
  }
});
assert.strictEqual(semanticBackendError.passed, false, 'SGP-005: backend error for one semantic target fails closed');
assert(semanticBackendError.rejection_reasons.includes('semantic_grounding_backend_error'), 'SGP-005: backend error reason present');
assert.deepStrictEqual(semanticBackendError.semantic_targets_missing, ['beta prompt library governance'], 'SGP-005: errored semantic target is missing');

const semanticEmptyRef = orchestrator.buildTypedGroundingPreflight(semanticPrompt, 'wsp_holo', {
  semantic_evidence_hits: [
    { need: 'alpha lane ledger reconciliation beta prompt library governance evidence without location' }
  ]
});
assert.strictEqual(semanticEmptyRef.passed, false, 'SGP-006: empty evidence_refs cannot pass');
assert.strictEqual(semanticEmptyRef.semantic_targets_grounded, 0, 'SGP-006: evidence without refs grounds zero targets');

const semanticBundleOutput = JSON.stringify({
  task_retrieval: {
    code_hits: [alphaSemanticHit, betaSemanticHit],
    metadata: { code_count: 2, wsp_count: 0, skill_count: 0 }
  }
});
const semanticBundleMeta = orchestrator.holoIndexMetaFromBundle(semanticBundleOutput, false, semanticPrompt);
assert.strictEqual(Array.isArray(semanticBundleMeta.semantic_evidence_hits), true, 'SGP-007: bundle meta projects semantic evidence hits');
assert.strictEqual(semanticBundleMeta.semantic_evidence_hits.length, 2, 'SGP-007: projected semantic evidence hit count');
const semanticBucketMeta = orchestrator.holoIndexMetaFromBundle(JSON.stringify({
  task_retrieval: {
    test_hits: [{ path: 'tests/test_pfmall.py', title: 'PFMall behavior tests' }],
    symbol_hits: [{ path: 'modules/pfmall/runtime.py', title: 'PFMall runtime symbol' }],
    knowledge_hits: [{ path: 'WSP_knowledge/pfmall.md', summary: 'PFMall prior verified research' }],
    metadata: { code_count: 0, wsp_count: 0 }
  }
}), false, broadAuditPrompt);
assert.deepStrictEqual(semanticBucketMeta.semantic_evidence_hits.map((hit) => hit.bucket).sort(), ['knowledge', 'symbol', 'test'],
  'SGP-007: test, symbol, and knowledge buckets are projected for semantic evidence');
const semanticBundlePreflight = orchestrator.buildTypedGroundingPreflight(semanticPrompt, 'wsp_holo', {
  holoindex_meta: semanticBundleMeta
});
assert.strictEqual(semanticBundlePreflight.passed, true, 'SGP-007: projected bundle evidence grounds semantic targets');

const semanticNoHolo = orchestrator.buildTypedGroundingPreflight(semanticPrompt, 'plain_context', {
  semantic_evidence_hits: [alphaSemanticHit, betaSemanticHit]
});
assert.strictEqual(semanticNoHolo.passed, false, 'SGP-008: semantic targets require a HoloIndex context');
assert(semanticNoHolo.rejection_reasons.includes('semantic_grounding_holoindex_required'), 'SGP-008: HoloIndex required reason present');

const semanticWardrobePayload = orchestrator.buildWardrobeSelectionPayload(semanticPrompt, {}, {}, {}, {
  groundingPreflight: semanticPartial
});
assert.strictEqual(semanticWardrobePayload.grounding_preflight.passed, false, 'SGP-009: wardrobe receipt preserves failed grounding');
assert.strictEqual(semanticWardrobePayload.grounding_preflight.semantic_targets_required, 2, 'SGP-009: wardrobe receipt carries semantic required count');
assert.strictEqual(semanticWardrobePayload.grounding_preflight.semantic_targets_grounded, 1, 'SGP-009: wardrobe receipt carries semantic grounded count');
assert.deepStrictEqual(semanticWardrobePayload.grounding_preflight.semantic_targets_missing, ['beta prompt library governance'], 'SGP-009: wardrobe receipt carries semantic missing list');
assert.strictEqual(semanticWardrobePayload.grounding_preflight.semantic_target_coverage_digest, semanticPartial.semantic_target_coverage_digest, 'SGP-009: wardrobe receipt binds semantic coverage digest');
let semanticSelectionRunnerCalled = false;
const semanticSelectionBlocked = orchestrator.runOperatorWardrobeSelectionBridge(null, semanticPrompt, {}, {}, {}, {
  groundingPreflight: semanticPartial,
  selectionRunner: () => {
    semanticSelectionRunnerCalled = true;
    return { decision: 'SHOULD_NOT_RUN' };
  }
});
assert.strictEqual(semanticSelectionRunnerCalled, false, 'SGP-010: wardrobe selection runner is not invoked after grounding failure');
assert.strictEqual(semanticSelectionBlocked.decision, 'WARDROBE_SELECTION_REJECT', 'SGP-010: wardrobe selection blocks on failed semantic grounding');
const semanticBlockedResult = orchestrator.buildGroundingPreflightBlockedResult(semanticPartial);
const semanticRuntimeGate = orchestrator.buildRuntimeConsumptionGate(semanticBlockedResult, { validated: false }, 'foundups_fusion', true);
assert.strictEqual(semanticRuntimeGate.passed, false, 'SGP-011: runtime gate blocks after grounding failure result');
assert(semanticRuntimeGate.rejection_reasons.includes('grounding_preflight_blocked'), 'SGP-011: runtime gate carries grounding failure reason');

const semanticExternalStillBlocked = orchestrator.buildTypedGroundingPreflight(typedPrompt, 'wsp_holo', {
  semantic_evidence_hits: [
    { location: 'docs/research/autoresearch_git_loop.md', need: 'autoresearch git-centric edit evaluate loop' }
  ],
  holoindex_scorecard: {
    target_recall_ok: true,
    required_targets_missing: [],
    code_hits_count: 2,
    wsp_hits: 1
  }
});
assert.strictEqual(semanticExternalStillBlocked.passed, false, 'SGP-012: external research remains fail-closed even when semantic evidence exists');
assert(semanticExternalStillBlocked.rejection_reasons.includes('external_research_retrieval_not_implemented'), 'SGP-012: external research fail-closed reason preserved');

const cleanInstallState = orchestrator.detectRedDogInstallState({
  extension: { id: 'foundups.reddog' }
});
assert.strictEqual(cleanInstallState.stale_install_detected, false, 'RPI-001: canonical RedDog install is not stale');
const originalGetExtension = vscodeMock.extensions.getExtension;
vscodeMock.extensions.getExtension = (id) => (
  id === 'foundups.foundups-fusion-worker'
    ? { id, packageJSON: { version: '0.3.68' } }
    : id === 'foundups.reddog'
      ? { id, packageJSON: { version: '0.4.97' } }
      : undefined
);
const duplicateDetectedState = orchestrator.detectRedDogInstallState({
  extension: { id: 'foundups.reddog' }
});
assert.strictEqual(duplicateDetectedState.duplicate_extension_detected, true, 'RPI-002: legacy duplicate install must be detected');
const installSection = orchestrator.buildRedDogInstallStateSection(duplicateDetectedState);
includes(installSection, '- duplicate_extension_detected: true', 'RPI-003: install state section renders duplicate');
vscodeMock.extensions.getExtension = originalGetExtension;

includes(extensionJs, 'REDDOG_RESIDENT_ARCHITECT_SESSION_SCRIPT', 'RAS-001: resident architect session script constant missing');
includes(JSON.stringify(pkg), 'reddog.enableResidentArchitectSession', 'RAS-001: canonical resident session setting missing');
includes(JSON.stringify(pkg), 'foundupsFusion.enableResidentArchitectSession', 'RAS-001: legacy resident session setting missing');
includes(extensionJs, "reddogConfigValue('enableResidentArchitectSession'", 'RAS-001: resident session runtime setting helper missing');
includes(extensionJs, 'function runResidentArchitectSessionBridge', 'RAS-001: resident session extension bridge missing');
includes(extensionJs, 'resident_architect_session_result', 'RAS-001: resident session result must attach to review packet');
includes(extensionJs, 'buildResidentArchitectSessionSection', 'RAS-001: Copy MD resident session section missing');
includes(residentArchitectBridgePy, 'RedDogResidentArchitectClient', 'RAS-002: bridge must use canonical authenticated resident client');
includes(residentArchitectBridgePy, 'lease_current_generation_conversation_session', 'RAS-002: bridge must authenticate under the current-generation lease');
includes(conversationSessionAuthoritySourceJs, 'SECRET_KEY', 'RAS-002: extension secret source missing');
assert(!conversationSessionAuthoritySourceJs.includes('_make_session_token'), 'RAS-002: production source must never mint session tokens');
includes(residentArchitectBridgePy, 'explicit_resident_architect_session_requested', 'RAS-002: bridge must require explicit request');
includes(residentArchitectBridgePy, 'no_holoindex_reindex_performed', 'RAS-002: bridge must surface no-reindex attestation');
includes(residentArchitectBridgePy, 'no_repo_mutation_performed', 'RAS-002: bridge must surface no-repo-mutation attestation');

const residentPayloadSkipped = orchestrator.buildResidentArchitectSessionPayload('work focus', {});
assert.strictEqual(residentPayloadSkipped.ok, false, 'RAS-003: resident payload skips without explicit request');
assert(residentPayloadSkipped.rejection_reasons.includes('explicit_resident_architect_session_request_missing'), 'RAS-003: missing explicit request reason');
const residentUngrounded = orchestrator.buildResidentArchitectSessionPayload('audit work', {
  explicitResidentArchitectSessionRequested: true
});
assert.strictEqual(residentUngrounded.ok, false, 'GTC-001: explicit ungrounded resident intent fails closed');
assert(residentUngrounded.rejection_reasons.includes('grounded_target_receipt_not_ready'),
  'GTC-001: ungrounded intent exposes the stable rejection reason');

const residentCoverage = [{ target: 'audit work', verdict: 'SUFFICIENT', evidence_refs: ['code:reddog'] }];
