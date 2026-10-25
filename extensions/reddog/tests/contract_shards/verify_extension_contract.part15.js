const disabledTelemetry = { continuation_enabled: false, continuation_appended: false, continuation_source_run_id: 'none' };
const copyDisabled = orchestrator.buildCopyMarkdown(
  { ok: true, content: sampleArchitectOutput, review_packet: { task_classification: { tier: 'HIGH' }, output_validation: { validated: true }, continuation_telemetry: disabledTelemetry } },
  'reddog_architect', 'Repo context attached', [], null, 'high',
  { substantive: true, continuationEnabled: false, continuationSummary: null, continuationTelemetry: disabledTelemetry }
);
assert(!copyDisabled.includes('Continuation from last RedDog packet'), 'disabled: Copy MD must NOT include continuation summary');
includes(copyDisabled, 'continuation_enabled: false', 'disabled: Copy MD telemetry must report enabled=false');
includes(copyDisabled, 'continuation_appended: false', 'disabled: Copy MD telemetry must report appended=false');
includes(copyDisabled, 'continuation_source_run_id: none', 'disabled: Copy MD telemetry must report source=none');

// Case 3: missing toggle (fail-closed) mirrors disabled: enabled false when summary passed as null.
const missingTelemetry = orchestrator.normalizeContinuationTelemetry(undefined);
assert.strictEqual(missingTelemetry.continuation_enabled, false, 'missing toggle must normalize to enabled=false (fail-closed)');
assert.strictEqual(missingTelemetry.continuation_appended, false, 'missing toggle must normalize to appended=false');
assert.strictEqual(missingTelemetry.continuation_source_run_id, 'none', 'missing toggle must normalize source to none');
const copyMissing = orchestrator.buildCopyMarkdown(
  { ok: true, content: sampleArchitectOutput, review_packet: { task_classification: { tier: 'HIGH' }, output_validation: { validated: true } } },
  'reddog_architect', 'Repo context attached', [], null, 'high',
  { substantive: true, continuationSummary: successSummary }
);
assert(!copyMissing.includes('Continuation from last RedDog packet'), 'missing/undefined continuationEnabled must NOT include continuation summary (fail-closed)');

// REDDOG_CONTINUATION_DEFAULT_OFF_PHASE1 (v0.3.36) - continuation is opt-IN.
// (a) Webview checkbox default is UNCHECKED (no `checked` attribute); feature stays manually available.
const useLastPacketInputMatch = extensionJs.match(/<input id="useLastPacket" type="checkbox"([^>]*)>/);
assert(useLastPacketInputMatch, 'useLastPacket checkbox input must exist (feature stays manually available)');
assert(
  !/\bchecked\b/.test(useLastPacketInputMatch[1]),
  'useLastPacket checkbox must default OFF (no `checked` attribute) - continuation is opt-in'
);
// Frontend still sends the deterministic boolean from the checkbox state.
includes(extensionJs, 'useLastPacket: continuationOn', 'frontend must send useLastPacket from checkbox state');
includes(extensionJs, 'const continuationOn = !!(useLastPacket && useLastPacket.checked)', 'frontend continuation flag must derive from checkbox.checked');

// (b) Default submit: useLastPacket false/absent => continuation_enabled=false AND continuation_appended=false.
//     Mirrors the backend fail-closed derivation (message.useLastPacket === true), reusing #911's telemetry path.
const defaultOffFromFalse = orchestrator.normalizeContinuationTelemetry(
  { continuation_enabled: (false === true), continuation_appended: ((false === true) && true) }
);
assert.strictEqual(defaultOffFromFalse.continuation_enabled, false, 'default off (useLastPacket=false): continuation_enabled must be false');
assert.strictEqual(defaultOffFromFalse.continuation_appended, false, 'default off (useLastPacket=false): continuation_appended must be false');
const defaultOffFromAbsent = orchestrator.normalizeContinuationTelemetry(
  { continuation_enabled: (undefined === true), continuation_appended: ((undefined === true) && true) }
);
assert.strictEqual(defaultOffFromAbsent.continuation_enabled, false, 'default off (useLastPacket absent): continuation_enabled must be false');
assert.strictEqual(defaultOffFromAbsent.continuation_appended, false, 'default off (useLastPacket absent): continuation_appended must be false');
const copyDefaultOff = orchestrator.buildCopyMarkdown(
  { ok: true, content: sampleArchitectOutput, review_packet: { task_classification: { tier: 'HIGH' }, output_validation: { validated: true }, continuation_telemetry: defaultOffFromFalse } },
  'reddog_architect', 'Repo context attached', [], null, 'high',
  { substantive: true, continuationEnabled: false, continuationSummary: successSummary, continuationTelemetry: defaultOffFromFalse }
);
assert(!copyDefaultOff.includes('Continuation from last RedDog packet'), 'default off: Copy MD must NOT append continuation summary even when a prior packet exists');
includes(copyDefaultOff, 'continuation_enabled: false', 'default off: Copy MD telemetry must report enabled=false');
includes(copyDefaultOff, 'continuation_appended: false', 'default off: Copy MD telemetry must report appended=false');

// (c) Manual check (useLastPacket=true) still appends when a summary is present (feature not removed).
const manualCheckTelemetry = orchestrator.normalizeContinuationTelemetry(
  { continuation_enabled: (true === true), continuation_appended: ((true === true) && true), continuation_source_run_id: successSummary.previous_run_id }
);
assert.strictEqual(manualCheckTelemetry.continuation_enabled, true, 'manual check (useLastPacket=true): continuation_enabled must be true');
assert.strictEqual(manualCheckTelemetry.continuation_appended, true, 'manual check + prior packet: continuation_appended must be true');
const copyManualCheck = orchestrator.buildCopyMarkdown(
  { ok: true, content: sampleArchitectOutput, review_packet: { task_classification: { tier: 'HIGH' }, output_validation: { validated: true }, continuation_telemetry: manualCheckTelemetry } },
  'reddog_architect', 'Repo context attached', [], null, 'high',
  { substantive: true, continuationEnabled: true, continuationSummary: successSummary, continuationTelemetry: manualCheckTelemetry }
);
includes(copyManualCheck, 'Continuation from last RedDog packet', 'manual check: Copy MD must still append continuation summary (feature available on opt-in)');
includes(copyManualCheck, 'continuation_enabled: true', 'manual check: Copy MD telemetry must report enabled=true');

// REDDOG_CONVERSATION_HISTORY_POLICY_ENFORCEMENT_PHASE1 (v0.4.57): the existing
// continuation toggle controls only the sanitized last-packet summary. Raw provider
// history remains fail-closed until P1 supplies authenticated FoundUp-scoped turns.
const deniedRawHistory = conversationHistoryPolicy.enforceHistoryPolicy({
  inclusionRequested: true,
  storedHistory: [
    { role: 'user', content: 'FoundUp A secret', turn_id: 'turn-a' },
    { role: 'assistant', content: 'FoundUp B result', turn_id: 'turn-b' }
  ]
});
assert.deepStrictEqual(deniedRawHistory.admittedHistory, [], 'raw history must be excluded until authenticated scoped state exists');
assert.strictEqual(deniedRawHistory.telemetry.model_history_attached, false, 'telemetry must report no raw model history');
assert.deepStrictEqual(deniedRawHistory.telemetry.admitted_turn_ids, [], 'no unauthenticated turn IDs may be admitted');
assert.strictEqual(deniedRawHistory.telemetry.history_policy_reason, 'authenticated_scoped_history_unavailable');
includes(conversationHistoryPolicyJs, 'no_work_authority_from_history: true', 'history non-authority invariant missing');
includes(extensionJs, 'historyAdmission.admittedHistory', 'Fusion must receive policy-admitted history only');
includes(extensionJs, 'conversationHistoryPolicy.prepareHistoryAdmission(', 'stored history must clear before Fusion');
includes(extensionJs, 'conversationHistoryPolicy.discardProviderHistory(', 'provider history discard wiring missing');
includes(conversationHistoryPolicyJs, 'mutableState.history = []', 'policy must clear stored history');
includes(conversationHistoryPolicyJs, 'delete result.history', 'provider-returned history must be deleted');
assert(!extensionJs.includes('systemPrompt, state.history, mode'), 'raw state.history must never reach Fusion');
assert(
  extensionJs.indexOf('conversationHistoryPolicy.discardProviderHistory(') < extensionJs.indexOf('fusionProgress.capture(result)'),
  'provider-returned history must be discarded before progress capture'
);
const historyPolicyTrace = orchestrator.buildRunTraceSection(
  { review_packet: { conversation_history_policy: deniedRawHistory.telemetry } },
  'reddog_architect', null, null, 'high'
);
includes(historyPolicyTrace, 'model_history_attached: false', 'Run Trace must expose actual history attachment state');
includes(historyPolicyTrace, 'admitted_turn_ids: []', 'Run Trace must expose admitted turn IDs');

// REDDOG_REPAIR_PRESERVES_EVIDENCE_PHASE1: the repair path must protect a primary Determine
// answer block through the schema-repair pass (reuses the Python guard; no rules duplicated in JS).
// (a) source wiring: pre-repair protect-block injection + post-merge revalidate + keep-original.
includes(extensionJs, "runRepairGuard(context, 'protect'", 'repair path must inject the protected Determine block before repair');
includes(extensionJs, "runRepairGuard(context, 'guard'", 'repair path must revalidate the merged output against the guard');
includes(extensionJs, 'repair_dropped_determine_evidence', 'repair path must keep the original when the repair loses Determine evidence');
includes(extensionJs, 'repair_evidence_preserved', 'repair path must record evidence-preservation telemetry');
assert(fs.existsSync(path.join(root, 'scripts', 'reddog_repair_guard_once.py')), 'repair guard bridge script must exist');

// (b) hasDetermineAnswersBlock presence check (fail-closed fallback): ATX + SETEXT, not prose.
assert(orchestrator.hasDetermineAnswersBlock('## Determine Answers\n\n```json\n[]\n```') === true, 'ATX Determine block detected');
assert(orchestrator.hasDetermineAnswersBlock('Determine Answers\n=================\n') === true, 'SETEXT Determine block detected');
assert(orchestrator.hasDetermineAnswersBlock('## Decision\n\nprose only, no block') === false, 'prose must not be detected as a block');

// (c) end-to-end through the real Python guard bridge (reuses assert_repair_preserves).
const rgPrompt = 'Audit.\n\nDetermine:\n1. Is the valve closed?\n2. Is the gate built?\n\nEnd.\n';
const rgAnswers = [
  { index: 1, question_text: 'Is the valve closed?', answer: 'yes', wsp97_label: 'OBSERVED', evidence_refs: ['modules/x/valve.py:9'] },
  { index: 2, question_text: 'Is the gate built?', answer: 'no', wsp97_label: 'OBSERVED', evidence_refs: ['modules/x/gate.py:12'] }
];
const rgBlock = (answers) => '## Determine Answers\n\n```json\n' + JSON.stringify(answers, null, 2) + '\n```';
const rgPrimary = '## Decision\n\nProceed.\n\n' + rgBlock(rgAnswers);
const rgProtect = orchestrator.runRepairGuard(null, 'protect', rgPrompt, rgPrimary, null);
if (rgProtect && rgProtect.ok) {
  assert(rgProtect.has_determine === true, 'protect: block detected');
  assert(/modules\/x\/valve\.py:9/.test(rgProtect.protected_context || ''), 'protect: context carries file:line evidence, not just a summary');
  const rgFaithful = orchestrator.runRepairGuard(null, 'guard', rgPrompt, rgPrimary, rgPrimary + '\n\n## Findings\n\nadded.');
  assert(rgFaithful.ok === true && rgFaithful.keep_original === false, 'guard: faithful repair (adds a section) is accepted');
  const rgStripped = orchestrator.runRepairGuard(null, 'guard', rgPrompt, rgPrimary, '## Decision\n\nProceed.\n\n' + rgBlock([Object.assign({}, rgAnswers[0], { evidence_refs: [] }), rgAnswers[1]]));
  assert(rgStripped.ok === true && rgStripped.keep_original === true, 'guard: evidence-stripping repair keeps original');
  const rgDropped = orchestrator.runRepairGuard(null, 'guard', rgPrompt, rgPrimary, '## Decision\n\nProceed. See above.\n');
  assert(rgDropped.ok === true && rgDropped.keep_original === true, 'guard: repair that drops the whole block keeps original');
  console.log('  repair-evidence guard bridge end-to-end: OK');
} else {
  console.log('  repair-evidence guard bridge unavailable (python) -- source wiring + presence checks still enforced');
}

// REDDOG_JUDGMENT_GENERATION_WIRING_PHASE1: generation must request canonical Determine
// answers, then run the deterministic verifier bridge against already-fetched direct-read hits.
includes(extensionJs, 'Determine answer contract: the 012 work focus contains a Determine numbered list', 'judgment wiring must inject Determine answer generation instructions');
includes(extensionJs, 'function runJudgmentVerifier', 'judgment verifier bridge wrapper missing');
includes(extensionJs, 'reddog_judgment_verifier_once.py', 'judgment verifier bridge script missing from extension source');
includes(extensionJs, 'judgment_verifier_started', 'judgment verifier work trail event missing');
includes(extensionJs, 'judgment_verification', 'judgment verifier telemetry missing');
includes(extensionJs, 'buildJudgmentVerificationSection', 'Copy MD judgment verification section missing');
includes(extensionJs, 'formatJudgmentVerificationLines', 'Run Trace judgment verifier fields missing');
assert(fs.existsSync(path.join(root, 'scripts', 'reddog_judgment_verifier_once.py')), 'judgment verifier bridge script must exist');

const jvPrompt = 'Audit.\n\nDetermine:\n1. Does build_foundup dispatch exist?\n';
const jvOutput = '## Determine Answers\n\n```json\n' + JSON.stringify([
  {
    index: 1,
    question_text: 'Does build_foundup dispatch exist?',
    answer: 'yes',
    wsp97_label: 'OBSERVED',
    evidence_refs: ['modules/foundups/agent/src/hermes_foundup_job_executor.py:2']
  }
], null, 2) + '\n```\n';
const jvResult = orchestrator.runJudgmentVerifier(null, jvPrompt, jvOutput, {
  direct_read_fallback_used: true,
  direct_read_paths: ['modules/foundups/agent/src/hermes_foundup_job_executor.py']
}, [
  {
    location: 'modules/foundups/agent/src/hermes_foundup_job_executor.py',
    content: ['class Builder:', '    def build_foundup(self):', '        return True', ''].join('\n')
  }
]);
if (jvResult && jvResult.ok) {
  assert.strictEqual(jvResult.applied, true, 'judgment verifier must apply to Determine prompts');
  assert.strictEqual(jvResult.verified, true, 'judgment verifier must verify supported file:line evidence');
  assert.strictEqual(jvResult.verified_count, 1, 'judgment verifier verified_count must be 1');
  assert(jvResult.index_gap_event && jvResult.index_gap_event.event === 'INDEX_GAP', 'judgment verifier must emit advisory INDEX_GAP event when direct-read masks stale index');
  const jvMissing = orchestrator.runJudgmentVerifier(null, jvPrompt, '## Decision\nMissing answer block.\n', {}, []);
  assert(jvMissing.ok === true && jvMissing.verified === false && jvMissing.reason === 'missing_determine_answers_block',
    'judgment verifier must fail closed when a Determine prompt lacks the canonical answer block');
  console.log('  judgment verifier bridge end-to-end: OK');
} else {
  console.log('  judgment verifier bridge unavailable (python) -- source wiring + telemetry checks still enforced');
}

// REDDOG_SYMBOL_AWARE_EXCERPT_DEPTH_PHASE1: a required direct-read target may be `path#symbol`.
// The extension forwards the FULL token to --bundle-must-include (so the Python bundle layer returns
// a bounded line window around the symbol's definition) but matches recall/resolve by the BARE path.
assert.strictEqual(orchestrator.stripSymbolSuffix('modules/x/foo.py#build_foundup'), 'modules/x/foo.py',
  'stripSymbolSuffix removes a trailing #identifier');
assert.strictEqual(orchestrator.stripSymbolSuffix('modules/x/foo.py'), 'modules/x/foo.py',
  'stripSymbolSuffix leaves a plain path untouched');
assert.strictEqual(orchestrator.stripSymbolSuffix('weird#name.md'), 'weird#name.md',
  'stripSymbolSuffix leaves a non-identifier # suffix (real path) untouched');
// recall: a path#symbol required target is satisfied by the fetched BARE-path location
assert(orchestrator.requiredTargetMatchesLocation('modules/x/foo.py#build_foundup', 'modules/x/foo.py'),
  'path#symbol recall matches the bare-path fetched location');
// the token survives parsing (list marker stripped upstream) and end-to-end block parsing
const symToks = orchestrator.extractTargetTokensFromLine('modules/x/hermes.py#build_foundup');
assert(symToks.includes('modules/x/hermes.py#build_foundup'), 'path#symbol token is parsed and kept');
const symBlock = orchestrator.parseRequiredTargetPaths(
  'Audit.\n\nRequired direct-read targets:\n- modules/x/hermes.py#build_foundup\n- modules/x/plain.py\n');
assert(symBlock.includes('modules/x/hermes.py#build_foundup') && symBlock.includes('modules/x/plain.py'),
  'parseRequiredTargetPaths keeps a path#symbol target end-to-end');
const symArgs = orchestrator.buildMustIncludeArgs(['modules/x/hermes.py#build_foundup']);
assert(symArgs.includes('modules/x/hermes.py#build_foundup'),
  'path#symbol is forwarded to --bundle-must-include (not dropped)');
// a pathless `symbol:` prefix is still excluded (unchanged)
assert(!orchestrator.buildMustIncludeArgs(['symbol:create_foundup']).includes('symbol:create_foundup'),
  'pathless symbol: prefix is still excluded from direct-read');

// REDDOG_WORK_FOCUS_TARGET_DERIVATION_PHASE1 (WFTD-001..WFTD-012): free-form target derivation.
// Repo paths named with read-intent OUTSIDE the exact "Required direct-read targets:" header must
// still be promoted to required direct-read targets so the governed fetch fires. Reuses the SAME
// governed direct-read gate (bundle_json.py); no HoloIndex ranking/index changes.
includes(extensionJs, 'function deriveWorkFocusTargets', 'WFTD: work-focus target deriver missing');
includes(extensionJs, 'function collectRequiredTargets', 'WFTD: merged required-target collector missing');
includes(extensionJs, 'work_focus_targets_derived', 'WFTD: derivation telemetry field missing');
includes(extensionJs, 'work_focus_target_derivation_sources', 'WFTD: derivation-source telemetry field missing');

// WFTD-001: existing exact "Required direct-read targets:" prompt is byte-identical (backward compat).
// The merged collector's targets must equal the header-only parser's output, in the same order.
const wftdHeaderParsed = orchestrator.parseRequiredTargetPaths(fixtures.FOUNDUP_CREATION_PROMPT);
const wftdHeaderCollected = orchestrator.collectRequiredTargets(fixtures.FOUNDUP_CREATION_PROMPT);
assert.deepStrictEqual(wftdHeaderCollected.targets, wftdHeaderParsed, 'WFTD-001: header-only shape must collect byte-identically to parseRequiredTargetPaths');
assert.strictEqual(wftdHeaderCollected.derived, false, 'WFTD-001: pure header shape must not report derivation');
assert(wftdHeaderCollected.derivation_sources.includes('required_block'), 'WFTD-001: header shape source is required_block');

// WFTD-002: "Read first:" list with 3 repo paths derives all 3.
const wftdReadFirst = orchestrator.collectRequiredTargets(fixtures.WORK_FOCUS_READ_FIRST_PROMPT);
for (const p of fixtures.WORK_FOCUS_ORCH_PATHS) {
  assert(wftdReadFirst.targets.includes(p), 'WFTD-002: Read-first must derive ' + p);
}
assert.strictEqual(wftdReadFirst.derived, true, 'WFTD-002: Read-first must report derived=true');
assert(wftdReadFirst.derivation_sources.includes('read_first'), 'WFTD-002: source must be read_first');

// WFTD-003: WSP_99 M2M READ: array derives all paths.
const wftdM2m = orchestrator.collectRequiredTargets(fixtures.WORK_FOCUS_M2M_READ_PROMPT);
assert(wftdM2m.targets.includes(fixtures.WORK_FOCUS_ORCH_PATHS[0]), 'WFTD-003: M2M READ must derive first path');
assert(wftdM2m.targets.includes(fixtures.WORK_FOCUS_ORCH_PATHS[2]), 'WFTD-003: M2M READ must derive third path');
assert(wftdM2m.derivation_sources.includes('m2m_read'), 'WFTD-003: source must be m2m_read');

// WFTD-004: M2M CTX.FILES derives all paths (and does NOT capture the CTX.FILES key token).
const wftdCtx = orchestrator.collectRequiredTargets(fixtures.WORK_FOCUS_CTX_FILES_PROMPT);
assert(wftdCtx.targets.includes(fixtures.WORK_FOCUS_ORCH_PATHS[0]), 'WFTD-004: CTX.FILES must derive first path');
assert(wftdCtx.targets.includes(fixtures.WORK_FOCUS_ORCH_PATHS[1]), 'WFTD-004: CTX.FILES must derive second path');
assert(!wftdCtx.targets.some((t) => /^ctx\.files$/i.test(t)), 'WFTD-004: the CTX.FILES key token must NOT be derived as a path');
assert(wftdCtx.derivation_sources.includes('ctx_files'), 'WFTD-004: source must be ctx_files');

// WFTD-005: backticked repo paths derive correctly.
const wftdBacktick = orchestrator.collectRequiredTargets(fixtures.WORK_FOCUS_BACKTICK_PROMPT);
assert(wftdBacktick.targets.includes(fixtures.WORK_FOCUS_ORCH_PATHS[2]), 'WFTD-005: backtick path 1 derived');
assert(wftdBacktick.targets.includes(fixtures.WORK_FOCUS_ORCH_PATHS[1]), 'WFTD-005: backtick path 2 derived');
assert(wftdBacktick.derivation_sources.includes('backtick_path'), 'WFTD-005: source must be backtick_path');

// WFTD-006: inline prose repo paths derive AND do not capture surrounding words.
const wftdInline = orchestrator.collectRequiredTargets(fixtures.WORK_FOCUS_INLINE_PROMPT);
assert(wftdInline.targets.includes(fixtures.WORK_FOCUS_ORCH_PATHS[0]), 'WFTD-006: inline path 1 derived');
assert(wftdInline.targets.includes(fixtures.WORK_FOCUS_ORCH_PATHS[2]), 'WFTD-006: inline path 2 derived');
// no derived token may contain a space or an English filler word from the prose
for (const t of wftdInline.targets) {
  assert(!/\s/.test(t), 'WFTD-006: derived inline token must not contain whitespace: ' + t);
  assert(!/(^|\/)(for|and|check|too|see|before|the)(\/|$)/i.test(t), 'WFTD-006: derived token must not capture prose words: ' + t);
}
assert(wftdInline.derivation_sources.includes('inline_path'), 'WFTD-006: source must be inline_path');

// WFTD-007: invalid/traversal/.env/secret paths are EMITTED honestly by derivation but REJECTED by
// the existing governed gate (they must never be fetched). Derivation stays truthful; the Python
// gate is the enforcement boundary. Verify (a) the deriver emits them and (b) the gate denies them.
const wftdDenied = orchestrator.collectRequiredTargets(fixtures.WORK_FOCUS_DENIED_MIX_PROMPT);
assert(wftdDenied.targets.includes('.env'), 'WFTD-007: deriver emits .env honestly (gate rejects it, not the deriver)');
assert(wftdDenied.targets.includes('../outside.txt'), 'WFTD-007: deriver emits traversal honestly');
assert(wftdDenied.targets.includes('modules/communication/moltbot_bridge/src/foundup_job_contract.py'), 'WFTD-007: legitimate path still derived');
assert(orchestrator.isTargetReadPathDenied('.env'), 'WFTD-007: .env must be denied by the existing gate');
assert(orchestrator.isTargetReadPathDenied('../outside.txt'), 'WFTD-007: traversal must be denied by the existing gate');
// buildMustIncludeArgs forwards them (the Python gate is authoritative), but they land in rejected.
const wftdMustInc = orchestrator.buildMustIncludeArgs(wftdDenied.targets);
assert(wftdMustInc.length >= 2, 'WFTD-007: must-include args are built for the derived targets');

// WFTD-008: HoloIndex miss + explicit/derived path list still direct-reads. evaluateTargetRecall on
// a derived-path prompt whose bundle recalled NOTHING must report index_gap_detected=true (fetch will
// fire) with required_targets_total>0 -- the exact dormant-stack failure this slice fixes.
const wftdRecallMiss = orchestrator.evaluateTargetRecall(fixtures.WORK_FOCUS_READ_FIRST_PROMPT, {
  task_retrieval: { code_hits: [{ location: 'docs/unrelated.md', need: 'semantic: unrelated' }] }
});
assert.strictEqual(wftdRecallMiss.required_targets_total, fixtures.WORK_FOCUS_ORCH_PATHS.length, 'WFTD-008: derived paths make required_targets_total > 0');
assert.strictEqual(wftdRecallMiss.index_gap_detected, true, 'WFTD-008: HoloIndex miss on derived paths sets index_gap_detected=true (fetch fires)');
assert.strictEqual(wftdRecallMiss.target_recall_ok, false, 'WFTD-008: none recalled => target_recall_ok=false');
assert.strictEqual(wftdRecallMiss.work_focus_targets_derived, true, 'WFTD-008: recall telemetry reports work_focus_targets_derived=true');
assert(Array.isArray(wftdRecallMiss.work_focus_target_derivation_sources) && wftdRecallMiss.work_focus_target_derivation_sources.includes('read_first'), 'WFTD-008: recall telemetry carries derivation sources');

// WFTD-009: no explicit AND no derivable paths -> behavior unchanged (total stays 0; inference intact).
const wftdNoneRecall = orchestrator.evaluateTargetRecall(fixtures.REGULAR_SMOKE_PROMPT, { task_retrieval: { code_hits: [] } });
assert.strictEqual(wftdNoneRecall.required_targets_total, 0, 'WFTD-009: no derivable paths keeps required_targets_total=0');
assert.strictEqual(wftdNoneRecall.target_recall_ok, 'unknown', 'WFTD-009: unknown recall unchanged (no fabricated gap)');
assert.strictEqual(wftdNoneRecall.work_focus_targets_derived, false, 'WFTD-009: nothing derived');
assert.strictEqual(orchestrator.collectRequiredTargets(fixtures.REGULAR_SMOKE_PROMPT).targets.length, 0, 'WFTD-009: collector empty for a no-path prompt');

// WFTD-010: guard B-i -- a ```powershell validation block naming extension.js must NOT derive it.
const wftdCmdFence = orchestrator.collectRequiredTargets(fixtures.WORK_FOCUS_COMMAND_FENCE_PROMPT);
assert.strictEqual(wftdCmdFence.targets.length, 0, 'WFTD-010: command/validation fence must derive no targets');
assert(!wftdCmdFence.targets.some((t) => /extension\.js$/i.test(t)), 'WFTD-010: extension.js in a command fence must not be derived');
assert.strictEqual(wftdCmdFence.derived, false, 'WFTD-010: command fence => derived=false');

// WFTD-011: guard B-ii -- a "SCOPE - OUT" bullet naming a path must NOT derive; the in-scope
// "Read first" path in the same prompt still derives.
const wftdScope = orchestrator.collectRequiredTargets(fixtures.WORK_FOCUS_SCOPE_OUT_PROMPT);
assert(!wftdScope.targets.some((t) => /off_limits/.test(t)), 'WFTD-011: SCOPE-OUT paths must not be derived');
assert(wftdScope.targets.includes('modules/in/scope.py'), 'WFTD-011: in-scope Read-first path still derived');

// WFTD-012: REGRESSION -- the real multi-lane orchestration audit prompt shape. Names 3 repo files
// in a "Read first" block (no explicit header). Must yield required_targets_total >= 3 AND fire the
// governed fetch; the three files are included OR honestly rejected (never silently ignored). Runs
// the real Python bundle CLI end-to-end.
(function wftd012Regression() {
  const holo = orchestrator.holoIndexOutput(root, fixtures.WORK_FOCUS_READ_FIRST_PROMPT, 18000);
  const m = holo && holo.meta ? holo.meta : {};
  assert(m.required_targets_total >= 3, 'WFTD-012: derived required_targets_total must be >= 3');
  assert.strictEqual(m.work_focus_targets_derived, true, 'WFTD-012: meta must record work_focus_targets_derived=true');
  assert(Array.isArray(m.work_focus_target_derivation_sources) && m.work_focus_target_derivation_sources.includes('read_first'), 'WFTD-012: meta carries read_first source');
  assert.strictEqual(m.direct_read_fetch_attempted, true, 'WFTD-012: governed direct-read fetch must be ATTEMPTED for the derived-path prompt');
  const fetched = new Set(Array.isArray(m.direct_read_paths) ? m.direct_read_paths : []);
  const rejected = new Set((Array.isArray(m.direct_read_rejected) ? m.direct_read_rejected : []).map((r) => (r && r.path ? String(r.path).replace(/\\/g, '/') : String(r))));
  const missing = new Set(Array.isArray(m.required_targets_missing) ? m.required_targets_missing : []);
  for (const p of fixtures.WORK_FOCUS_ORCH_PATHS) {
    const accountedFor = fetched.has(p) || rejected.has(p) || missing.has(p);
    assert(accountedFor, 'WFTD-012: orchestration target must be fetched, rejected, or honestly-missing (never silently ignored): ' + p);
  }
})();

// WFTD-013: derivation telemetry surfaces in the scorecard + Run Trace.
const wftdMeta = { holoindex_status: 'bundle_json_ok', code_hits: 2, wsp_hits: 1, skill_hits: 0,
  required_targets_total: 3, required_targets_recalled: 0, required_targets_missing: fixtures.WORK_FOCUS_ORCH_PATHS,
  work_focus_targets_derived: true, work_focus_target_derivation_sources: ['read_first'] };
const wftdScorecard = orchestrator.extractHoloIndexScorecard('wsp_holo', wftdMeta);
assert.strictEqual(wftdScorecard.work_focus_targets_derived, true, 'WFTD-013: scorecard carries work_focus_targets_derived');
assert(Array.isArray(wftdScorecard.work_focus_target_derivation_sources) && wftdScorecard.work_focus_target_derivation_sources.includes('read_first'), 'WFTD-013: scorecard carries derivation sources');
const wftdLines = orchestrator.formatHoloIndexScorecardLines(wftdScorecard).join('\n');
includes(wftdLines, '- work_focus_targets_derived: true', 'WFTD-013: Run Trace renders work_focus_targets_derived');
includes(wftdLines, '- work_focus_target_derivation_sources: read_first', 'WFTD-013: Run Trace renders derivation sources');

// WFTD-014: the bullet-list marker is stripped by a ReDoS-safe LINEAR helper, not the
// /^(?:[-*+]|\d+[.)])\s+(.*)$/ polynomial-redos regex CodeQL flagged (alert #174 + 2 new PR #942
// instances). Guard: (a) stripListMarker parity with the old regex semantics, (b) the flagged
// regex literal is absent from extension.js source so it cannot silently return.
assert.deepStrictEqual(orchestrator.stripListMarker('- docs/a/b.py'), { isList: true, itemText: 'docs/a/b.py' }, 'WFTD-014: dash bullet stripped');
assert.deepStrictEqual(orchestrator.stripListMarker('12. src/main.go'), { isList: true, itemText: 'src/main.go' }, 'WFTD-014: numbered bullet stripped');
assert.deepStrictEqual(orchestrator.stripListMarker('*   a/b.md'), { isList: true, itemText: 'a/b.md' }, 'WFTD-014: multi-space bullet stripped');
assert.strictEqual(orchestrator.stripListMarker('plain prose line').isList, false, 'WFTD-014: non-list line not treated as bullet');
assert.strictEqual(orchestrator.stripListMarker('-nospace').isList, false, 'WFTD-014: marker without following whitespace is not a bullet');
assert(!/\.match\(\/\^\(\?:\[-\*\+\]/.test(extensionJs), 'WFTD-014: polynomial-redos bullet regex USE (.match(/^(?:[-*+]...) must be absent from source');
// Pathological-input ReDoS budget: stripping a 200KB whitespace line stays linear (<200ms).
const wftdRedosStart = Date.now();
orchestrator.stripListMarker('* ' + ' '.repeat(200000) + 'x/y.py');
assert(Date.now() - wftdRedosStart < 200, 'WFTD-014: stripListMarker stays linear on pathological whitespace');

// REDDOG_WORK_FOCUS_READ_CAPTURE_PROSE_TOKENIZATION_PHASE1 (WFTD-015..WFTD-020): the exact failed
// 0.3.44 flowing-prose "Read first:" prompt must now derive the 3 real files cleanly, drop the
// slash-only English fragment as low-confidence, and NOT flip target_recall_ok. Uses the same
// governed direct-read gate; no HoloIndex ranking / Python changes.
includes(extensionJs, 'function extractProsePathTokens', 'WFTD-015: prose token partitioner missing');
includes(extensionJs, 'work_focus_targets_dropped_low_confidence', 'WFTD-015: dropped-low-confidence telemetry field missing');

// WFTD-015: the flowing-prose Read-first prompt derives EXACTLY the 3 real files, clean.
const wftdProse = orchestrator.collectRequiredTargets(fixtures.WORK_FOCUS_PROSE_READ_FIRST_PROMPT);
for (const p of fixtures.WORK_FOCUS_ORCH_PATHS) {
  assert(wftdProse.targets.includes(p), 'WFTD-015: flowing prose must derive ' + p);
}
// breadcrumb_tracer.py must be present AND clean (no trailing " Determine..." glued on).
const wftdBreadcrumb = fixtures.WORK_FOCUS_ORCH_PATHS[2];
assert(wftdProse.targets.includes(wftdBreadcrumb), 'WFTD-015: breadcrumb_tracer.py must be derived');
assert(!wftdProse.targets.some((t) => /breadcrumb_tracer\.py\s+determine/i.test(t) || /breadcrumb_tracer\.py\.$/.test(t)), 'WFTD-015: breadcrumb_tracer.py must be clean (no trailing prose / period)');
assert.strictEqual(wftdProse.derived, true, 'WFTD-015: prose prompt must report derived=true');
assert(wftdProse.derivation_sources.includes('read_first'), 'WFTD-015: source must be read_first');

// WFTD-016: recall on the flowing-prose prompt with all 3 real files present = total 3 / recalled 3 /
// recall_ok true / gap false (the exact 0.3.44 failure inverted: was total 4 / recalled 2 / ok false).
const wftdProseHits = { task_retrieval: { code_hits: fixtures.WORK_FOCUS_ORCH_PATHS.map((p) => ({ location: p, need: 'semantic: ' + p })) } };
const wftdProseRecall = orchestrator.evaluateTargetRecall(fixtures.WORK_FOCUS_PROSE_READ_FIRST_PROMPT, wftdProseHits);
assert.strictEqual(wftdProseRecall.required_targets_total, 3, 'WFTD-016: required_targets_total must be 3 (not 4)');
assert.strictEqual(wftdProseRecall.required_targets_recalled, 3, 'WFTD-016: required_targets_recalled must be 3');
assert.strictEqual(wftdProseRecall.target_recall_ok, true, 'WFTD-016: target_recall_ok must be true');
assert.strictEqual(wftdProseRecall.index_gap_detected, false, 'WFTD-016: index_gap_detected must be false');
// The 3 direct_read-eligible required targets are exactly the 3 real files (no garbage 4th target).
assert.deepStrictEqual([...wftdProseRecall.recall_targets].sort(), [...fixtures.WORK_FOCUS_ORCH_PATHS].sort(), 'WFTD-016: required targets are exactly the 3 real files');

// WFTD-017: the breadcrumb/handoff-style slash-only fragment IS in dropped-low-confidence, is NOT a
// required target, and does NOT affect target_recall_ok.
const wftdDropped = wftdProseRecall.work_focus_targets_dropped_low_confidence;
assert(Array.isArray(wftdDropped), 'WFTD-017: dropped-low-confidence must be an array');
assert(wftdDropped.some((t) => /breadcrumb\/handoff/i.test(t)), 'WFTD-017: breadcrumb/handoff fragment must be dropped');
assert(!wftdProseRecall.recall_targets.some((t) => /breadcrumb\/handoff/i.test(t)), 'WFTD-017: dropped fragment must NOT be a required target');
assert(!wftdProseRecall.required_targets_missing.some((t) => /breadcrumb\/handoff/i.test(t)), 'WFTD-017: dropped fragment must NOT be in required_targets_missing (cannot flip recall_ok)');
// Even with the fragment's directory absent from the bundle, recall stays ok (fragment excluded).
assert.strictEqual(wftdProseRecall.target_recall_ok, true, 'WFTD-017: dropped fragment does not flip target_recall_ok');

// WFTD-018: Fix C -- normalizeTargetPath (via the exported extractTargetTokensFromLine) trims trailing
// . , ; : ) ] } from a derived path.
for (const trail of ['.', ',', ';', ':', ')', ']', '}']) {
  const toks = orchestrator.extractTargetTokensFromLine('x/y.py' + trail);
  assert.deepStrictEqual(toks, ['x/y.py'], 'WFTD-018: trailing "' + trail + '" must be trimmed');
}
// The prose extractor also trims a ${path}-style brace wrapper down to the clean path.
