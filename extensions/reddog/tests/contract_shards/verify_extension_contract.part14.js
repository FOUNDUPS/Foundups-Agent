try {
  cp.execFileSync('git', ['init', '-q'], { cwd: weakenedStatRoot });
  cp.execFileSync('git', ['config', '--local', 'core.checkStat', 'minimal'], { cwd: weakenedStatRoot });
  includes(orchestrator.governedGitDiff(weakenedStatRoot, 24000), '[git context unavailable:',
    'core.checkStat weakening must fail governed context collection closed');
  cp.execFileSync('git', ['config', '--local', '--unset-all', 'core.checkStat'], { cwd: weakenedStatRoot });
  cp.execFileSync('git', ['config', '--local', 'core.trustctime', 'false'], { cwd: weakenedStatRoot });
  includes(orchestrator.governedGitDiff(weakenedStatRoot, 24000), '[git context unavailable:',
    'core.trustctime weakening must fail governed context collection closed');
  includes(governedGitReadinessJs, 'core.checkStat=default',
    'governed Git commands must pin full stat checking');
  includes(governedGitReadinessJs, 'core.trustctime=true',
    'governed Git commands must pin ctime trust');
  cp.execFileSync('git', ['config', '--local', '--unset-all', 'core.trustctime'], { cwd: weakenedStatRoot });
  cp.execFileSync('git', ['config', '--local', 'extensions.partialClone', 'origin'], { cwd: weakenedStatRoot });
  includes(orchestrator.governedGitDiff(weakenedStatRoot, 24000), '[git context unavailable:',
    'partial-clone configuration must fail governed context collection closed');
  includes(governedGitReadinessJs, "GIT_NO_LAZY_FETCH: '1'",
    'governed Git environment must disable lazy object fetches');
  cp.execFileSync('git', ['config', '--local', '--unset-all', 'extensions.partialClone'],
    { cwd: weakenedStatRoot });
  fs.mkdirSync(path.join(weakenedStatRoot, '.git', 'objects', 'info'), { recursive: true });
  fs.writeFileSync(path.join(weakenedStatRoot, '.git', 'objects', 'info', 'alternates'),
    path.join(governedDiffRoot, '.git', 'objects') + '\n', 'utf8');
  includes(orchestrator.governedGitDiff(weakenedStatRoot, 24000), '[git context unavailable:',
    'alternate object stores must fail governed context collection closed');
} finally {
  fs.rmSync(weakenedStatRoot, { recursive: true, force: true });
}

const replacementRefRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-git-replace-'));
const replacementHeadSource = path.join(os.tmpdir(), `reddog-head-control-${process.pid}-${Date.now()}`);
try {
  cp.execFileSync('git', ['init', '-q'], { cwd: replacementRefRoot });
  fs.writeFileSync(path.join(replacementRefRoot, 'allowed.py'), 'authentic = 1\n', 'utf8');
  cp.execFileSync('git', ['add', 'allowed.py'], { cwd: replacementRefRoot });
  const identity = ['-c', 'user.name=RedDog Test', '-c', 'user.email=reddog@example.invalid'];
  cp.execFileSync('git', [...identity, 'commit', '-qm', 'authentic'], { cwd: replacementRefRoot });
  const authenticHead = cp.execFileSync('git', ['rev-parse', 'HEAD'],
    { cwd: replacementRefRoot, encoding: 'utf8' }).trim();
  fs.writeFileSync(path.join(replacementRefRoot, 'allowed.py'), 'authentic = 2\n', 'utf8');
  cp.execFileSync('git', ['add', 'allowed.py'], { cwd: replacementRefRoot });
  cp.execFileSync('git', [...identity, 'commit', '-qm', 'replacement'], { cwd: replacementRefRoot });
  const replacementHead = cp.execFileSync('git', ['rev-parse', 'HEAD'],
    { cwd: replacementRefRoot, encoding: 'utf8' }).trim();
  cp.execFileSync('git', ['reset', '--hard', '-q', authenticHead], { cwd: replacementRefRoot });
  fs.writeFileSync(path.join(replacementRefRoot, 'allowed.py'), 'authentic = 2\n', 'utf8');
  cp.execFileSync('git', ['add', 'allowed.py'], { cwd: replacementRefRoot });
  cp.execFileSync('git', ['replace', authenticHead, replacementHead], { cwd: replacementRefRoot });
  const replacementProof = orchestrator.governedGitDiff(replacementRefRoot, 24000);
  includes(replacementProof, 'authentic = 2',
    'replacement refs must not make an attacker-selected staged change appear clean');
  includes(governedGitReadinessJs, "GIT_NO_REPLACE_OBJECTS: '1'",
    'governed Git environment must disable replacement objects');
  includes(governedGitReadinessJs, "'--no-replace-objects'",
    'every governed Git command must explicitly disable replacement objects');
  const headControl = path.join(replacementRefRoot, '.git', 'HEAD');
  fs.writeFileSync(replacementHeadSource, fs.readFileSync(headControl));
  fs.rmSync(headControl);
  fs.linkSync(replacementHeadSource, headControl);
  includes(orchestrator.governedGitDiff(replacementRefRoot, 24000), '[git context unavailable:',
    'Git storage cache must invalidate when a critical control file is replaced');
} finally {
  fs.rmSync(replacementRefRoot, { recursive: true, force: true });
  fs.rmSync(replacementHeadSource, { force: true });
}

const externalGitRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-git-external-source-'));
const gitfileWorkspace = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-gitfile-workspace-'));
const forgedAdminRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-forged-admin-'));
try {
  cp.execFileSync('git', ['init', '-q'], { cwd: externalGitRoot });
  fs.writeFileSync(path.join(externalGitRoot, 'allowed.py'), 'EXTERNAL_GIT_BLOB_SECRET\n', 'utf8');
  cp.execFileSync('git', ['add', 'allowed.py'], { cwd: externalGitRoot });
  cp.execFileSync('git', ['-c', 'user.name=RedDog Test', '-c', 'user.email=reddog@example.invalid',
    'commit', '-qm', 'external'], { cwd: externalGitRoot });
  fs.writeFileSync(path.join(gitfileWorkspace, '.git'),
    `gitdir: ${path.join(externalGitRoot, '.git')}\n`, 'utf8');
  const blockedGitfile = orchestrator.governedGitDiff(gitfileWorkspace, 24000);
  includes(blockedGitfile, '[git context unavailable:',
    'workspace gitfiles must not redirect governed context to another repository');
  assert(!blockedGitfile.includes('EXTERNAL_GIT_BLOB_SECRET'),
    'external repository blobs must not enter model context');
  const forgedAdmin = path.join(forgedAdminRoot, 'worktrees', 'forged');
  fs.mkdirSync(forgedAdmin, { recursive: true });
  fs.writeFileSync(path.join(forgedAdmin, 'commondir'), path.join(externalGitRoot, '.git'), 'utf8');
  fs.writeFileSync(path.join(forgedAdmin, 'gitdir'), path.join(gitfileWorkspace, '.git'), 'utf8');
  fs.writeFileSync(path.join(gitfileWorkspace, '.git'), `gitdir: ${forgedAdmin}\n`, 'utf8');
  const blockedCrossCommon = orchestrator.governedGitDiff(gitfileWorkspace, 24000);
  includes(blockedCrossCommon, '[git context unavailable:',
    'worktree admin must reside under its resolved common Git directory');
  assert(!blockedCrossCommon.includes('EXTERNAL_GIT_BLOB_SECRET'),
    'cross-common forged worktree metadata must not expose external blobs');
} finally {
  fs.rmSync(externalGitRoot, { recursive: true, force: true });
  fs.rmSync(gitfileWorkspace, { recursive: true, force: true });
  fs.rmSync(forgedAdminRoot, { recursive: true, force: true });
}

const deletedBlobRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-git-deleted-blob-'));
try {
  cp.execFileSync('git', ['init', '-q'], { cwd: deletedBlobRoot });
  fs.writeFileSync(path.join(deletedBlobRoot, 'removed.py'), 'HISTORICAL_BLOB_MUST_NOT_LEAK\n', 'utf8');
  cp.execFileSync('git', ['add', 'removed.py'], { cwd: deletedBlobRoot });
  cp.execFileSync('git', ['-c', 'user.name=RedDog Test', '-c', 'user.email=reddog@example.invalid',
    'commit', '-qm', 'fixture'], { cwd: deletedBlobRoot });
  fs.rmSync(path.join(deletedBlobRoot, 'removed.py'));
  const deletedProjection = orchestrator.governedGitDiff(deletedBlobRoot, 24000);
  includes(deletedProjection, 'diff --reddog-deleted removed.py',
    'deleted files must be represented without reading historical blobs');
  assert(!deletedProjection.includes('HISTORICAL_BLOB_MUST_NOT_LEAK'),
    'historical Git blob content must never enter model context');
} finally {
  fs.rmSync(deletedBlobRoot, { recursive: true, force: true });
}

const oversizedGitRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-git-oversized-'));
try {
  cp.execFileSync('git', ['init', '-q'], { cwd: oversizedGitRoot });
  const oversizedPath = path.join(oversizedGitRoot, 'allowed.txt');
  fs.writeFileSync(oversizedPath, 'a'.repeat(140000), 'utf8');
  cp.execFileSync('git', ['add', 'allowed.txt'], { cwd: oversizedGitRoot });
  cp.execFileSync('git', ['-c', 'user.name=RedDog Test', '-c', 'user.email=reddog@example.invalid', 'commit', '-qm', 'fixture'], { cwd: oversizedGitRoot });
  fs.writeFileSync(oversizedPath, 'b'.repeat(140000), 'utf8');
  const oversizedProjection = orchestrator.governedGitDiff(oversizedGitRoot, 1000);
  assert(oversizedProjection.endsWith('[REDDOG_GIT_OUTPUT_TRUNCATED]'),
    'oversized current-file evidence must carry an explicit bounded truncation marker');
} finally {
  fs.rmSync(oversizedGitRoot, { recursive: true, force: true });
}

const truncatedGitRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-git-truncated-'));
try {
  cp.execFileSync('git', ['init', '-q'], { cwd: truncatedGitRoot });
  const truncatedPath = path.join(truncatedGitRoot, 'allowed.txt');
  fs.writeFileSync(truncatedPath, 'a'.repeat(5000), 'utf8');
  cp.execFileSync('git', ['add', 'allowed.txt'], { cwd: truncatedGitRoot });
  cp.execFileSync('git', ['-c', 'user.name=RedDog Test', '-c', 'user.email=reddog@example.invalid', 'commit', '-qm', 'fixture'], { cwd: truncatedGitRoot });
  fs.writeFileSync(truncatedPath, 'b'.repeat(5000), 'utf8');
  const truncatedDiff = orchestrator.governedGitDiff(truncatedGitRoot, 1000);
  assert(truncatedDiff.length <= 1000, 'bounded Git diff must honor its character budget');
  assert(truncatedDiff.endsWith('[REDDOG_GIT_OUTPUT_TRUNCATED]'),
    'bounded Git diff must preserve its truncation marker inside the budget');
} finally {
  fs.rmSync(truncatedGitRoot, { recursive: true, force: true });
}

const copyTargets = orchestrator.inferRecallTargetPaths(fixtures.BUILD_COPY_MARKDOWN_PROMPT);
assert(copyTargets.includes(fixtures.EXT_ACC_001_TARGET_PATH), 'buildCopyMarkdown prompt must map to extension.js');

// ADDENDUM F - redaction-safe target snippets (reuse fixtures; gate probe via Python policy)
assert.strictEqual(targetSection.meta.target_content_sanitized, true, 'extension.js snippet must be sanitized for gate safety');
assert(targetSection.meta.target_content_sanitized_categories.length > 0, 'sanitized categories must be recorded');
includes(targetSection.text, '[SANITIZED_BLOCK:', 'sanitized placeholders must preserve review shape');
assert(!targetSection.text.includes('grant authority'), 'raw grant authority must not remain in target recall section');
assert(!targetSection.text.includes('hidden chain-of-thought'), 'raw hidden chain-of-thought must not remain in target recall section');
assert(!targetSection.text.includes('redaction_gate_passed'), 'raw redaction_gate_passed must not remain in target recall section');

const targetRecallSection = extractTargetRecallSection(boundedContext.text);
assert(targetRecallSection.length > 0, 'target recall section must exist for gate probe');
assertFusionRedactionGatePasses(targetRecallSection, 'target recall section must pass fusion redaction gate');
assertFusionRedactionGatePasses(boundedContext.text, 'EXT-ACC-001 bounded context must pass fusion redaction gate');
assert.strictEqual(boundedContext.holoindex_scorecard.target_content_sanitized, true, 'scorecard target_content_sanitized must be true when replacements occurred');
assert(boundedContext.holoindex_scorecard.target_content_sanitized_categories.length > 0, 'scorecard must list sanitized categories');

// ADDENDUM B - REDDOG_ALWAYS_HOLOINDEX_GROUNDING_PHASE1 (THG-001..THG-006)
const regularHoloContext = orchestrator.buildBoundedRepoContext('wsp_holo', fixtures.REGULAR_SMOKE_PROMPT);
includes(regularHoloContext.text, '### HoloIndex recall', 'THG-004: wsp_holo must include HoloIndex recall section');
assert(regularHoloContext.holoindex_scorecard !== null, 'THG-005: wsp_holo must return holoindex_scorecard');
const regularReasoning = orchestrator.modeSelectionReasoning(regular, 'regular', 'openrouter_single', 'wsp_holo');
includes(regularReasoning, 'wsp_holo', 'THG-006: REGULAR mode selection must cite wsp_holo');
includes(regularReasoning, 'HoloIndex-grounded', 'THG-006: REGULAR mode selection must state HoloIndex grounding');

// ADDENDUM G - REDDOG_CONTEXT_UNICODE_NORMALIZATION_PHASE1 (UNI-001..UNI-007)
let uni001Failed = false;
try {
  cp.execFileSync('python', ['-B', '-c', "import hashlib; s='PR\\udc94'; hashlib.sha256(s.encode('utf-8')).hexdigest()"], {
    cwd: root,
    encoding: 'utf8',
    timeout: 30000
  });
} catch (err) {
  uni001Failed = /UnicodeEncodeError|surrogate/i.test(String(err && (err.stderr || err.message || err)));
}
assert(uni001Failed, 'UNI-001: lone surrogate must break UTF-8 digest path without normalization');

const uni002Reason = cp.execFileSync('python', ['-B', '-c', "from modules.communication.moltbot_bridge.src.fusion_redaction_gate import evaluate_redaction_gate; r=evaluate_redaction_gate('012 work focus digest placeholder for gate probe', 'PR\\udc94 tail'); print(r.reason)"], {
  cwd: root,
  encoding: 'utf8',
  timeout: 30000
}).trim();
assert.strictEqual(uni002Reason, 'redactor_error', 'UNI-002: Python surrogate in context must fail gate before normalization');

const normalizedMalformed = orchestrator.normalizeBridgeTextForUnicode(fixtures.MALFORMED_UNICODE_CONTEXT, 'context');
assert(normalizedMalformed.unicode_replacements_count > 0, 'UNI-003: lone surrogate must increment replacement count');
includes(normalizedMalformed.text, orchestrator.UNICODE_SURROGATE_PLACEHOLDER, 'UNI-003: lone surrogate must become ASCII placeholder');
assert(!normalizedMalformed.text.includes('\udc94'), 'UNI-007: raw malformed surrogate must not remain in normalized text');
assertFusionRedactionGatePasses(normalizedMalformed.text, 'UNI-004: normalized malformed context must pass fusion redaction gate');
assertFusionRedactionGateBlocks(fixtures.BLOCKED_POLICY_CONTEXT, 'blocked_policy', 'UNI-005: blocked_policy context must still block after normalization contract');
assertFusionRedactionGatePasses(fixtures.EMDASH_UNICODE_CONTEXT, 'UNI-008: U+2014 em dash context must pass fusion redaction gate when UTF-8 decoded');

const bridgeEnv = orchestrator.buildBridgePythonEnv({});
assert.strictEqual(bridgeEnv.PYTHONIOENCODING, 'utf-8', 'UNI-009: bridge child env must force PYTHONIOENCODING=utf-8');
assert.strictEqual(bridgeEnv.PYTHONUTF8, '1', 'UNI-009: bridge child env must force PYTHONUTF8=1');

const bridgeEmDashProbe = cp.execFileSync('python', ['-B', '-m', 'pytest', 'scripts/tests/test_advisory_model_once_hardening.py::AdvisoryBridgeHardeningTests::test_main_em_dash_utf8_stdin_not_redactor_error', '-q'], {
  cwd: root,
  encoding: 'utf8',
  timeout: 120000,
  env: Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' })
}).trim();
includes(bridgeEmDashProbe, '1 passed', 'UNI-010: bridge UTF-8 stdin em dash must not redactor_error');

const unicodeTrace = orchestrator.buildRunTraceSection({
  review_packet: {
    task_classification: { tier: 'HIGH' },
    resolved_effort: 'high',
    resolved_mode: 'openrouter_single',
    resolved_context: 'wsp_holo_skillz',
    mode_selection_reasoning: 'Single-model GLM principal',
    principal_model: 'z-ai/glm-5.2',
    panel_models: ['deepseek/deepseek-v4-pro'],
    unicode_normalization_applied: true,
    unicode_replacements_count: 1,
    unicode_normalization_sources: 'context',
    unicode_normalization_form: 'NFC',
    holoindex_scorecard: {
      holoindex_status: 'bundle_json_ok',
      wsp_hits: 3,
      code_hits_count: 3,
      code_hits: 3
    },
    output_validation: { validated: false, skipped: true }
  }
}, 'reddog_architect', 'Repo context attached', null, 'high');
includes(unicodeTrace, 'unicode_normalization_applied: true', 'UNI-006: Run Trace must expose unicode normalization applied');
includes(unicodeTrace, 'unicode_replacements_count: 1', 'UNI-006: Run Trace must expose replacement count');
includes(unicodeTrace, 'unicode_normalization_sources: context', 'UNI-006: Run Trace must expose normalization sources');
includes(unicodeTrace, 'unicode_normalization_form: NFC', 'UNI-006: Run Trace must expose normalization form');
assert(!unicodeTrace.includes('\udc94'), 'UNI-007: Run Trace must not echo raw malformed surrogate');

// ADDENDUM G - redaction-safe continuation memory (REDDOG_REVIEW_PACKET_MEMORY_AND_FOLLOWUP_PHASE1)
includes(extensionJs, 'buildSanitizedContinuationSummary', 'continuation summary builder missing');
includes(extensionJs, 'appendContinuationSummaryToWspPrompt', 'continuation append helper missing');
includes(extensionJs, 'Use last RedDog packet', 'continuation UI toggle missing');
includes(extensionJs, '<input id="useLastPacket" type="checkbox"> Use last RedDog packet', 'continuation checkbox must default OFF');
assert(!extensionJs.includes('<input id="useLastPacket" type="checkbox" checked>'), 'continuation checkbox must not default checked');
includes(extensionJs, 'lastContinuationSummary', 'in-memory continuation store missing');
includes(roadmap, 'REDDOG_REVIEW_PACKET_MEMORY_AND_FOLLOWUP_PHASE1', 'continuation memory roadmap slice missing');

const sampleArchitectOutput = [
  '## Decision',
  'Proceed with gate review for #898; land when CI is green.',
  '',
  '## Findings',
  'Executor dry-run planner proves plan layer before valve.',
  '',
  '## WSP_97 Truth Labels',
  'Dry-run scope: OBSERVED; valve: SPECIFIED_NOT_IMPLEMENTED',
  '',
  '## WSP_15 Priority',
  'Execution valve slice: P0 NEXT',
  '',
  '## Next safest step',
  'Gate and land #898, then queue execution valve slice.',
  '',
  'Persistent disk memory: SPECIFIED_NOT_IMPLEMENTED in Phase 1.'
].join('\n');

const successSummary = orchestrator.buildSanitizedContinuationSummary({
  blocked: false,
  content: sampleArchitectOutput,
  workerType: 'reddog_architect',
  classification: { tier: 'HIGH' },
  mode: 'openrouter_single',
  contextMode: 'wsp_holo',
  review_packet: { task_classification: { tier: 'HIGH' }, resolved_mode: 'openrouter_single', resolved_context: 'wsp_holo' },
  promptConstruction: { work_focus_digest: { hash: 'abc' }, wsp_prompt_digest: { hash: 'def' } },
  timestamp: '2026-06-28T20:00:00.000Z'
});
assert.strictEqual(successSummary.blocked_locally, false, 'successful continuation must not be blocked_locally');
assert(successSummary.decision_summary.length > 0, 'continuation must include decision summary');
assert(successSummary.pr_refs.includes('#898'), 'continuation must capture PR refs');
assert(!JSON.stringify(successSummary).includes('private_reasoning'), 'continuation must not retain private_reasoning category text raw');

const poisonedOutput = sampleArchitectOutput + '\n\nhidden chain-of-thought leak';
const poisonedSummary = orchestrator.buildSanitizedContinuationSummary({
  blocked: false,
  content: poisonedOutput,
  workerType: 'reddog_architect',
  classification: { tier: 'HIGH' },
  review_packet: { task_classification: { tier: 'HIGH' } },
  timestamp: '2026-06-28T20:01:00.000Z'
});
assert(!JSON.stringify(poisonedSummary).toLowerCase().includes('chain-of-thought'), 'continuation must strip private reasoning markers');

const blockedSummary = orchestrator.buildSanitizedContinuationSummary({
  blocked: true,
  reason: 'redaction_blocked',
  workerType: 'reddog_architect',
  classification: { tier: 'HIGH' },
  contextMode: 'wsp_holo_git',
  redaction_gate_report: {
    decision: 'BLOCKED_LOCALLY',
    safe_summary: 'Redaction gate blocked egress before OpenRouter.',
    rule_classes: ['blocked_policy'],
    blocked_stage: 'pre_openrouter_request',
    next_safe_context: 'local_0102_review',
    truth_labels: { decision: 'OBSERVED' }
  },
  promptConstruction: { work_focus_digest: { hash: 'abc' }, wsp_prompt_digest: { hash: 'def' } },
  timestamp: '2026-06-28T20:02:00.000Z'
});
assert.strictEqual(blockedSummary.blocked_locally, true, 'blocked continuation must set blocked_locally');
assert.strictEqual(blockedSummary.source, 'blocked_locally', 'blocked continuation source label');
assert(blockedSummary.redaction_gate_summary.includes('blocked_policy'), 'blocked continuation must include safe gate summary');
assert(!blockedSummary.findings_summary.includes('OPENROUTER_API_KEY'), 'blocked continuation must not include secrets');

const followupPrompt = orchestrator.appendContinuationSummaryToWspPrompt(
  orchestrator.constructWspTaskPrompt('Follow up on executor dry-run land status.', { tier: 'HIGH', reasons: ['architecture'] }, 'bundle_json_ok', 'reddog_architect'),
  successSummary
);
includes(followupPrompt, 'Continuation from last RedDog packet', 'follow-up prompt must include continuation block');
includes(followupPrompt, 'previous_run_id:', 'follow-up prompt must include previous_run_id');
assertFusionRedactionGatePasses(followupPrompt, 'continuation-augmented WSP prompt must pass fusion redaction gate');
assertFusionRedactionGatePasses(orchestrator.formatContinuationSummaryBlock(successSummary), 'continuation summary block must pass fusion redaction gate');

const continuationCopy = orchestrator.buildCopyMarkdown(
  { ok: true, content: sampleArchitectOutput, review_packet: { task_classification: { tier: 'HIGH' }, output_validation: { validated: true } } },
  'reddog_architect',
  'Repo context attached',
  [],
  null,
  'high',
  {
    substantive: true,
    continuationEnabled: true,
    continuationSummary: successSummary,
    continuationTelemetry: { continuation_enabled: true, continuation_appended: true, continuation_source_run_id: successSummary.previous_run_id }
  }
);
includes(continuationCopy, 'Continuation from last RedDog packet', 'Copy MD may include safe continuation summary section');

// ADDENDUM H - deterministic Use-last-packet toggle + continuation telemetry
// (REDDOG_CONTINUATION_TOGGLE_HARDENING_PHASE1)
// Backend fail-closed default: continuation is included ONLY on explicit useLastPacket === true.
includes(extensionJs, 'continuationEnabled: message.useLastPacket === true', 'backend must fail closed (useLastPacket === true)');
assert(!extensionJs.includes('message.useLastPacket !== false'), 'legacy permissive default must be removed');
includes(continuationPromptJs, 'const appended = enabled && !!summary', 'single continuation_appended boolean must gate inclusion');
includes(extensionJs, 'Continuation: disabled for this run.', 'UI must show disabled status line');
includes(extensionJs, 'buildContinuationTelemetrySection', 'Copy MD continuation telemetry section missing');
includes(extensionJs, 'formatContinuationTelemetryLines', 'Run Trace continuation telemetry lines missing');

// Telemetry section (Copy MD) shape.
const telemetryOnSection = orchestrator.buildContinuationTelemetrySection({
  continuation_enabled: true,
  continuation_appended: true,
  continuation_source_run_id: 'run_abc123'
});
includes(telemetryOnSection, '## Continuation Telemetry', 'telemetry section header missing');
includes(telemetryOnSection, 'continuation_enabled: true', 'telemetry must report continuation_enabled');
includes(telemetryOnSection, 'continuation_appended: true', 'telemetry must report continuation_appended');
includes(telemetryOnSection, 'continuation_source_run_id: run_abc123', 'telemetry must report source run id');

// Telemetry appears in Run Trace section too.
const runTraceWithTelemetry = orchestrator.buildRunTraceSection(
  { review_packet: {
    task_classification: { tier: 'HIGH' },
    continuation_telemetry: { continuation_enabled: true, continuation_appended: true, continuation_source_run_id: 'run_xyz789' },
    model_binding_source: 'receipt_bound_runtime',
    model_runtime_binding_status: 'MODEL_RUNTIME_BINDING_READY',
    model_runtime_binding_receipt_id: 'reddog_model_runtime_binding:test',
    model_selection_receipt_id: 'model_selection_receipt:test',
    model_catalog_snapshot_id: 'model_catalog_snapshot:test',
    model_task_family: 'reddog_runtime_model_call',
    model_role_bindings: [{ role: 'principal', model_id: 'openai/gpt-5.6-sol', provider: 'openai' }]
  } },
  'reddog_architect', null, null, 'high'
);
includes(runTraceWithTelemetry, 'continuation_enabled: true', 'Run Trace must include continuation_enabled');
includes(runTraceWithTelemetry, 'continuation_appended: true', 'Run Trace must include continuation_appended');
includes(runTraceWithTelemetry, 'continuation_source_run_id: run_xyz789', 'Run Trace must include continuation_source_run_id');
includes(runTraceWithTelemetry, 'model binding source: receipt_bound_runtime', 'Run Trace model source missing');
includes(runTraceWithTelemetry, 'model runtime binding receipt: reddog_model_runtime_binding:test', 'Run Trace binding lineage missing');
includes(runTraceWithTelemetry, 'model role bindings: [{"role":"principal","model_id":"openai/gpt-5.6-sol","provider":"openai"}]', 'Run Trace role topology missing');

// Case 1: enabled + stored summary => appended in Copy MD (prompt-side parity via appendContinuationSummaryToWspPrompt).
const enabledTelemetry = { continuation_enabled: true, continuation_appended: true, continuation_source_run_id: successSummary.previous_run_id };
const copyEnabled = orchestrator.buildCopyMarkdown(
  { ok: true, content: sampleArchitectOutput, review_packet: { task_classification: { tier: 'HIGH' }, output_validation: { validated: true }, continuation_telemetry: enabledTelemetry } },
  'reddog_architect', 'Repo context attached', [], null, 'high',
  { substantive: true, continuationEnabled: true, continuationSummary: successSummary, continuationTelemetry: enabledTelemetry }
);
includes(copyEnabled, 'Continuation from last RedDog packet', 'enabled: Copy MD must include continuation summary');
includes(copyEnabled, 'continuation_appended: true', 'enabled: Copy MD telemetry must report appended=true');
includes(copyEnabled, 'continuation_enabled: true', 'enabled: Copy MD telemetry must report enabled=true');
const promptEnabled = orchestrator.appendContinuationSummaryToWspPrompt('WSP task prompt body', successSummary);
includes(promptEnabled, 'Continuation from last RedDog packet', 'enabled: model prompt must include continuation block');

// Case 2: disabled + stored summary => NOT appended (Copy MD) and telemetry enabled=false, appended=false.
