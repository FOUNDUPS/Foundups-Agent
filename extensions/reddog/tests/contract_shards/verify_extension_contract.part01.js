const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');
const cp = require('child_process');
const Module = require('module');

// Keep the exhaustive contract suite fast and deterministic. Production has
// no such override and therefore exercises RedDog's semantic-first default;
// a dedicated live semantic smoke runs separately from this suite.
process.env.REDDOG_HOLO_RETRIEVAL_MODE = 'lexical';

const fixtures = require('./fixtures');

const root = path.resolve(__dirname, '..', '..', '..');
const extDir = path.join(root, 'extensions', 'reddog');
const extensionJs = fs.readFileSync(path.join(extDir, 'extension.js'), 'utf8');
const daemonDiagnosticJs = fs.readFileSync(
  path.join(extDir, 'daemon_diagnostic_analysis.js'), 'utf8'
);
const orchestrationPromptTraceJs = fs.readFileSync(
  path.join(extDir, 'orchestration_prompt_trace.js'), 'utf8'
);
const orchestrationPromptRoutesJs = fs.readFileSync(
  path.join(extDir, 'orchestration_prompt_routes.js'), 'utf8'
);
const governedGitContextJs = fs.readFileSync(
  path.join(extDir, 'governed_git_context.js'), 'utf8'
);
const governedGitReadinessJs = fs.readFileSync(
  path.join(extDir, 'governed_git_readiness.js'), 'utf8'
);
const orchestrationPromptTrace = require(path.join(extDir, 'orchestration_prompt_trace.js'));
const workerPromptContractJs = fs.readFileSync(
  path.join(extDir, 'worker_prompt_contract.js'), 'utf8'
);
const targetReadPathPolicy = require(path.join(extDir, 'target_read_path_policy.js'));
const daemonDiagnosticSecretFilter = require(
  path.join(extDir, 'daemon_diagnostic_secret_filter.js')
);
const continuationPromptJs = fs.readFileSync(path.join(extDir, 'continuation_prompt.js'), 'utf8');
const conversationHistoryPolicyJs = fs.readFileSync(path.join(extDir, 'conversation_history_policy.js'), 'utf8');
const conversationHistoryPolicy = require(path.join(extDir, 'conversation_history_policy.js'));
const fusionProgressJs = fs.readFileSync(path.join(extDir, 'fusion_progress_receipt.js'), 'utf8');
const fusionProgress = require(path.join(extDir, 'fusion_progress_receipt.js'));
const holoGenerationBoundQueryJs = fs.readFileSync(path.join(extDir, 'holoindex_generation_bound_query.js'), 'utf8');
const holoGenerationBoundQuery = require(path.join(extDir, 'holoindex_generation_bound_query.js'));
const groundedTargetContinuity = require(path.join(extDir, 'grounded_target_continuity.js'));
const repoDeepDiveFocusPolicy = require(path.join(extDir, 'repo_deep_dive_focus_policy.js'));
const startOperationsControlJs = fs.readFileSync(path.join(extDir, 'start_operations_control.js'), 'utf8');
const startOperationsBridgeJs = fs.readFileSync(path.join(extDir, 'start_operations_bridge.js'), 'utf8');
const startOperationsEnvironmentJs = fs.readFileSync(path.join(extDir, 'start_operations_environment.js'), 'utf8');
const conversationSessionAuthoritySourceJs = fs.readFileSync(
  path.join(extDir, 'conversation_session_authority_source.js'), 'utf8'
);
const conversationSessionAuthoritySource = require(path.join(extDir, 'conversation_session_authority_source.js'));
const testWardrobeSourceProof = require(path.join(extDir, 'holoindex_owner_proof.js'))
  .createOwnerProof((value) => Boolean(value && typeof value === 'object'));
const testWardrobeProof = require(path.join(extDir, 'operator_wardrobe_selection_proof.js'))
  .createWardrobeSelectionProof(testWardrobeSourceProof.isAccepted);
const startOperationsInterpreterJs = fs.readFileSync(path.join(extDir, 'start_operations_interpreter.js'), 'utf8');
const runtimeMaterializerJs = fs.readFileSync(
  path.join(extDir, 'backend_compatibility_runtime_materializer.js'), 'utf8'
);
const startOperationsBootstrapPy = fs.readFileSync(
  path.join(extDir, 'start_operations_python_bootstrap.py'), 'utf8'
);
const bridgePy = fs.readFileSync(path.join(root, 'scripts', 'advisory_model_once.py'), 'utf8');
const holoOwnerBridgePy = fs.readFileSync(path.join(root, 'scripts', 'reddog_holoindex_owner_query_once.py'), 'utf8');
const residentArchitectBridgePy = fs.readFileSync(path.join(root, 'scripts', 'reddog_resident_architect_session_once.py'), 'utf8');
const pkg = JSON.parse(fs.readFileSync(path.join(extDir, 'package.json'), 'utf8'));
const readme = fs.readFileSync(path.join(extDir, 'README.md'), 'utf8');
const iface = fs.readFileSync(path.join(extDir, 'INTERFACE.md'), 'utf8');
const roadmap = fs.readFileSync(path.join(extDir, 'ROADMAP.md'), 'utf8');
const auditDocPath = path.join(root, 'docs', 'audits', 'architecture', 'REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md');
const auditDoc = fs.readFileSync(auditDocPath, 'utf8');
const executorContractDocPath = path.join(root, 'docs', 'audits', 'architecture', 'REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1.md');
const executorContractDoc = fs.readFileSync(executorContractDocPath, 'utf8');

function includes(haystack, needle, label) {
  assert(haystack.includes(needle), label || `missing ${needle}`);
}

// REDDOG_DIRECT_READ_FALLBACK_TRIGGER_DIAGNOSTIC_PHASE1: the golden FoundUp-creation
// audit prompt. Its "Required direct-read targets" list is what the 0.3.31 golden run
// parsed to required_targets_total=8 / recalled=0. Seven are real, fetchable repo
// files (identical to the bundle_json pytest FOUNDUP_ACCEPTANCE_TARGETS); the 8th is a
// non-fetchable symbol, so total=8 but arg_count=7 (symbols are dropped by
// buildMustIncludeArgs). These fetchable files exist on disk so DRT-005/007 run a
// real enriched fetch through the Python bundle CLI under the raised buffer.
const GOLDEN_FETCHABLE_TARGETS = [
  'WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md',
  'modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py',
  'modules/foundups/agent/src/hermes_foundup_job_executor.py',
  'modules/communication/moltbot_bridge/src/foundup_job_contract.py',
  'modules/communication/moltbot_bridge/src/reddog_governed_work_order_dryrun.py',
  'modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py',
  'modules/foundups/agent/src/source_authority.py'
];
// The 8th required target is a symbol reference (non-fetchable by path): total 8, fetchable 7.
const GOLDEN_SYMBOL_TARGET = 'symbol:create_foundup';
const GOLDEN_FOUNDUP_PROMPT = [
  'Audit the FoundUp creation monorepo WSP_109 execution path.',
  '',
  'Required direct-read targets:',
  ...GOLDEN_FETCHABLE_TARGETS.map((t) => '- ' + t),
  '- ' + GOLDEN_SYMBOL_TARGET,
  '',
  'Produce required RedDog architect output sections per contract.'
].join('\n');

// REDDOG_AUDIT_CONTEXT_BRIDGE_WIRE_PHASE1: golden 7-file FoundUp creation audit prompt
// (file paths only -- no symbol targets that direct-read-by-path cannot fetch).
const GOLDEN_7FILE_TARGETS = [
  'WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md',
  'WSP_framework/src/WSP_95_WRE_SKILLz_Wardrobe_Protocol.md',
  'modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py',
  'modules/foundups/agent/src/hermes_foundup_job_executor.py',
  'modules/communication/moltbot_bridge/src/foundup_job_contract.py',
  'modules/communication/moltbot_bridge/src/reddog_governed_work_order_dryrun.py',
  'modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py'
];
const GOLDEN_7FILE_FOUNDUP_PROMPT = [
  'Audit the FoundUp creation monorepo WSP_109 execution path.',
  '',
  'Required direct-read targets:',
  ...GOLDEN_7FILE_TARGETS.map((t) => '- ' + t),
  '',
  'Determine:',
  '1. Whether WSP_109 intake is specified, implemented, or missing.',
  '2. Whether a FoundUpCreationWorkOrder exists or is still missing.',
  '3. Whether RedDogGovernedWorkOrder can represent FoundUp creation.',
  '4. Whether FoundUpJob can represent FoundUp creation.',
  '5. Whether build_foundup creates a new FoundUp or aliases extract_foundup.',
  '6. Whether OpenClaw genesis/onboarding gates are built.',
  '7. Whether Hermes/WRE can write production FoundUp scaffolds today or only dry-run/evidence scaffolds.',
  '8. Whether the correct next slice is WSP_109 intake packet generation, Skillz authoring, scaffold writer, or live execution.',
  '',
  'Use WSP_97 labels for every claim.',
  'End with WSP_15 priority and the next safest slice.'
].join('\n');

// Keep the historical 6-target golden shape stable; WSP_95 policy safety is proven separately.
// Golden wire proof uses the 6 governance/code targets that pass audit-mode egress.
const GOLDEN_6FILE_AUDIT_PROMPT = [
  'Audit the FoundUp creation monorepo WSP_109 execution path.',
  '',
  'Required direct-read targets:',
  ...GOLDEN_7FILE_TARGETS.filter((t) => !t.includes('WSP_95')).map((t) => '- ' + t),
  '',
  'Use WSP_97 labels for every claim.'
].join('\n');

// REDDOG_REQUIRED_TARGET_CONTEXT_PACKING_PHASE1 (RTP-001..005 + ADDENDUM B): the golden
// 6-file FoundUp-creation audit prompt used to prove protected required-target packing.
// Uses the historical 6 governance/code targets (WSP_95 safety is tested separately)
// and DELIBERATELY omits "WSP_97" prose so the packing tests
// do not trip the WSP_97 excerpt path -- this is a pure PACKING proof.
const GOLDEN_6FILE_TARGETS = GOLDEN_7FILE_TARGETS.filter((t) => !t.includes('WSP_95'));
const GOLDEN_6FILE_FOUNDUP_PROMPT = [
  'Audit the FoundUp creation monorepo execution path.',
  '',
  'Required direct-read targets:',
  ...GOLDEN_6FILE_TARGETS.map((t) => '- ' + t),
  '',
  'Determine whether FoundUp creation is specified, implemented, or missing.',
  'End with the next safest slice.'
].join('\n');

function assertFusionRedactionGatePasses(contextText, label) {
  const script = [
    'import sys',
    'from modules.communication.moltbot_bridge.src.fusion_redaction_gate import evaluate_redaction_gate, REDACTION_GATE_PASSED',
    'ctx = sys.stdin.buffer.read().decode("utf-8", errors="replace")',
    'r = evaluate_redaction_gate("012 work focus digest placeholder for gate probe", ctx)',
    'if r.status != REDACTION_GATE_PASSED:',
    '    cats = ",".join(r.report.blocked_categories)',
    '    print("BLOCKED:" + r.reason + ":" + cats)',
    '    sys.exit(1)',
    'print("PASSED")'
  ].join('\n');
  const out = cp.execFileSync('python', ['-B', '-c', script], {
    cwd: root,
    input: Buffer.from(String(contextText || ''), 'utf8'),
    encoding: 'utf8',
    timeout: 30000,
    maxBuffer: 1024 * 1024,
    env: Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' })
  }).trim();
  assert.strictEqual(out, 'PASSED', label || 'bounded context must pass fusion redaction gate');
}

// Audit-mode gate probe (REDDOG_AUDIT_MODE_REDACTION_PHASE1, slice 3/3): runs the
// egress redaction gate with audit_mode=True and returns the REDACTED context so the
// caller can assert (a) it PASSED, (b) governance STRUCTURE survived, (c) secret
// VALUES are gone. Fails the test if the gate blocks.
function fusionRedactionGateAuditMode(contextText, label) {
  const script = [
    'import sys, json',
    'from modules.communication.moltbot_bridge.src.fusion_redaction_gate import evaluate_redaction_gate, REDACTION_GATE_PASSED',
    'ctx = sys.stdin.buffer.read().decode("utf-8", errors="replace")',
    'r = evaluate_redaction_gate("012 work focus digest placeholder for gate probe", ctx, audit_mode=True)',
    'if r.status != REDACTION_GATE_PASSED:',
    '    cats = ",".join(r.report.blocked_categories)',
    '    print("BLOCKED:" + r.reason + ":" + cats)',
    '    sys.exit(1)',
    'sys.stdout.write(json.dumps({"redacted_context": r.redacted_context or ""}))'
  ].join('\n');
  const out = cp.execFileSync('python', ['-B', '-c', script], {
    cwd: root,
    input: Buffer.from(String(contextText || ''), 'utf8'),
    encoding: 'utf8',
    timeout: 30000,
    maxBuffer: 1024 * 1024,
    env: Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' })
  }).trim();
  assert(!out.startsWith('BLOCKED:'), (label || 'audit-mode gate') + ' must PASS in audit mode: ' + out);
  return JSON.parse(out).redacted_context;
}

function extractTargetRecallSection(contextText) {
  const marker = '### Target recall content';
  const start = String(contextText || '').indexOf(marker);
  if (start === -1) {
    return '';
  }
  const tail = contextText.slice(start);
  const next = tail.indexOf('\n### ', marker.length);
  return next === -1 ? tail : tail.slice(0, next);
}

function assertFusionRedactionGateBlocks(contextText, expectedReason, label) {
  const script = [
    'import sys',
    'from modules.communication.moltbot_bridge.src.fusion_redaction_gate import evaluate_redaction_gate, REDACTION_GATE_PASSED',
    'ctx = sys.stdin.buffer.read().decode("utf-8", errors="replace")',
    'r = evaluate_redaction_gate("012 work focus digest placeholder for gate probe", ctx)',
    'if r.status == REDACTION_GATE_PASSED:',
    '    print("UNEXPECTED_PASS")',
    '    sys.exit(1)',
    'print(r.reason)'
  ].join('\n');
  const out = cp.execFileSync('python', ['-B', '-c', script], {
    cwd: root,
    input: Buffer.from(String(contextText || ''), 'utf8'),
    encoding: 'utf8',
    timeout: 30000,
    maxBuffer: 1024 * 1024,
    env: Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' })
  }).trim();
  assert.strictEqual(out, expectedReason, label || 'bounded context must be blocked by fusion redaction gate');
}

function assertFusionRedactionGateFails(contextText, expectedReason, label) {
  assertFusionRedactionGateBlocks(contextText, expectedReason, label);
}

assert.strictEqual(pkg.version, '0.4.133', 'package version must be 0.4.133');
includes(extensionJs, "const EXTENSION_VERSION = '0.4.133'", 'extension build mismatch');
assert.strictEqual(pkg.name, 'reddog', 'package id must be canonical RedDog in 0.4.0');
assert.strictEqual(pkg.displayName, 'RedDog - FoundUps Architect', 'display name must be canonical RedDog');
includes(JSON.stringify(pkg), 'RedDog: Open', 'canonical command title must use RedDog');
includes(JSON.stringify(pkg), 'foundupsFusion.open', 'legacy command alias must be retained for 0.4.0 migration');
includes(JSON.stringify(pkg), 'reddog.enableResidentArchitectSession', 'canonical resident session setting missing');
includes(JSON.stringify(pkg), 'foundupsFusion.enableResidentArchitectSession', 'legacy resident session setting alias missing');
assert.strictEqual(pkg.contributes.configuration.properties['reddog.enableResidentArchitectSession'].default, true,
  'governed action orchestration must be enabled by default');
includes(extensionJs, "title: 'RedDog'", 'webview title must use RedDog');
includes(extensionJs, 'startOperationsAdapter.handleMessage(', 'exact operations control route missing');
includes(extensionJs, 'REDDOG_START_OPERATIONS_CONTROL_SCRIPT', 'operations control bridge missing');
includes(startOperationsControlJs, "'start operations', 'submit'", 'exact start operations command missing');
includes(startOperationsControlJs, 'receipt_bound_runtime', 'production model-binding gate missing');
includes(startOperationsBridgeJs, 'cp.spawn', 'asynchronous operations bridge missing');
includes(startOperationsBridgeJs, "'-I', '-S', '-B'", 'sealed Python launch missing');
includes(startOperationsBridgeJs, 'PYTHON_BOOTSTRAP', 'explicit dependency bootstrap missing');
includes(startOperationsBridgeJs, 'runtimeMaterializer.materialize', 'sealed source materializer missing');
includes(startOperationsBridgeJs, 'stdoutBytes', 'cumulative stdout cap missing');
includes(startOperationsControlJs, 'control_request_id', 'request correlation missing');
includes(startOperationsEnvironmentJs, 'ALLOWED_KEYS', 'operations env allowlist missing');
includes(startOperationsEnvironmentJs, "PYTHONNOUSERSITE = '1'", 'user-site guard missing');
includes(startOperationsInterpreterJs, "path.resolve(repo, '.venv')", 'workspace venv pin missing');
includes(startOperationsInterpreterJs, 'contained(repo, root)', 'redirected venv guard missing');
includes(runtimeMaterializerJs, 'required_runtime_files', 'manifest runtime copy missing');
includes(runtimeMaterializerJs, 'verifiedSource', 'copy-time digest recheck missing');
includes(runtimeMaterializerJs, 'runtime_root_not_separated', 'runtime root guard missing');
includes(startOperationsBootstrapPy, 'sys.path.extend([str(source_root)', 'sealed source precedence missing');
includes(startOperationsBootstrapPy, '_VerifiedSourceLoader', 'import-time source verifier missing');
includes(startOperationsBootstrapPy, 'runtime_source_digest_mismatch', 'post-copy tamper gate missing');
includes(startOperationsBootstrapPy, '_reserved_bindings', 'reserved module binding missing');
includes(startOperationsBootstrapPy, 'reserved_runtime_module_missing', 'reserved module fail-close missing');
assert(
  startOperationsBootstrapPy.split(/\r?\n/).length <= 200,
  'start operations Python bootstrap exceeds WSP_62 file limit'
);
assert(
  !startOperationsBootstrapPy.includes('subprocess'),
  'Python bootstrap may not execute commands'
);
includes(extensionJs, "workspaceState.get('reddog.operationsIntentId'", 'durable operations intent missing');
includes(extensionJs, 'startOperationsEnvironment.build(process.env)', 'ambient extension env exposed');
const operationsIntercept = extensionJs.indexOf('startOperationsAdapter.handleMessage('); const conversationPromptAssembly = extensionJs.indexOf('const basePrompt = conversationPlanePolicy.selectUserPrompt(');
assert(
  operationsIntercept >= 0 && conversationPromptAssembly >= 0 && operationsIntercept < conversationPromptAssembly,
  'operations control must intercept before WSP prompt/Fusion assembly'
);
includes(readme, 'The VSIX is the IDE-side thin client for RedDog, the operator-facing identity/persona of the principal-scoped 0102 Digital Twin.', 'README product identity statement missing');
includes(iface, 'Fusion is one internal reasoning mode, not the product identity', 'INTERFACE mode identity statement missing');
includes(roadmap, 'RedDog is the resident FoundUps architect identity and conversation product across thin-client surfaces.', 'ROADMAP product identity statement missing');
includes(extensionJs, 'id="reddogWorkingTrail"', 'working trail DOM missing');
includes(extensionJs, 'data-reddog-pixel', 'trail pixel attribute missing');
includes(fusionProgressJs, "command: 'progress'", 'progress command shape missing');
const safeProgress = fusionProgress.buildProgressMessage('lead_start', 'Lead request started.', {
  run_id: 'run-1', role: 'lead', model: 'model-a', status: 'STARTED', elapsed_ms: 12,
  prompt: 'must-not-cross', reasoning: 'must-not-cross', nested: { secret: true }
});
assert.deepStrictEqual(safeProgress, {
  command: 'progress', stage: 'lead_start', text: 'Lead request started.', run_id: 'run-1',
  status: 'STARTED', role: 'lead', model: 'model-a', elapsed_ms: 12
}, 'progress UI projection must allowlist operational metadata');
const retryProgress = fusionProgress.buildProgressMessage(
  'lead_retry',
  'Lead returned empty or None; one bounded semantic retry is starting.',
  { role: 'lead', model: 'model-a' }
);
includes(retryProgress.text, 'bounded semantic retry', 'retry reason must remain visible to 012');
const decodedProgress = [];
const decoder = fusionProgress.createProgressLineDecoder((stage, text, event) => decodedProgress.push({ stage, text, event }));
const fragmentedEvent = JSON.stringify({ event: 'progress', stage: 'critic_done', text: 'Critic complete.', role: 'critic' });
decoder.push(fragmentedEvent.slice(0, 17));
decoder.push(fragmentedEvent.slice(17));
assert.strictEqual(decodedProgress.length, 0, 'unterminated fragmented progress must remain buffered');
decoder.flush();
assert.strictEqual(decodedProgress.length, 1, 'fragmented trailing progress must decode exactly once');
const progressSummary = fusionProgress.formatFusionProgressReceiptLines({
  fusion_panel_quorum: {
    lead_semantic_retry_count: 1,
    critic_challenge_retry_models: ['critic-a'],
    abstaining_critics: ['critic-b']
  },
  fusion_progress_receipts: [{
    receipt_id: 'sha256:receipt', event_count: 3,
    openrouter_calls: [{
      generation_id: 'gen-1',
      status: 'COMPLETED', retry_count: 1, duration_ms: 25,
      usage_verified: true, cost_accounting_complete: true,
      usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15, reasoning_tokens: 2, cached_tokens: 1, cost_microcredits: 200 },
      router_metadata: { response_provider: 'Provider A', response_model: 'served/model' }
    }]
  }]
}).join('\n');
includes(progressSummary, '- openrouter_total_tokens: 15', 'progress token total missing');
includes(progressSummary, '- openrouter_cost_microcredits: 200', 'OpenRouter credit total missing');
includes(progressSummary, '- openrouter_cost_accounting_complete: true', 'complete OpenRouter accounting status missing');
includes(progressSummary, '- openrouter_usage_verified_calls: 1/1', 'verified OpenRouter usage count missing');
includes(progressSummary, '- openrouter_retries: 1', 'OpenRouter retry total missing');
includes(progressSummary, '- openrouter_duration_ms: 25', 'OpenRouter duration total missing');
includes(progressSummary, '- openrouter_selected_routes: Provider A:served/model', 'provider route missing');
includes(progressSummary, '- fusion_lead_semantic_retries: 1', 'semantic lead retry telemetry missing');
includes(progressSummary, '- fusion_critic_challenge_retry_models: critic-a', 'critic challenge retry telemetry missing');
includes(progressSummary, '- fusion_abstaining_critics: critic-b', 'critic abstention telemetry missing');
const incompleteProgressSummary = fusionProgress.formatFusionProgressReceiptLines({
  fusion_progress_receipts: [{
    receipt_id: 'sha256:incomplete', event_count: 1,
    openrouter_calls: [{
      status: 'FAILED', retry_count: 2, duration_ms: 30,
      usage_verified: false, cost_accounting_complete: false,
      usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0, reasoning_tokens: 0, cached_tokens: 0, cost_microcredits: 0 },
      router_metadata: {}
    }]
  }]
}).join('\n');
includes(incompleteProgressSummary, '- openrouter_calls_failed: 1', 'failed OpenRouter call count missing');
includes(incompleteProgressSummary, '- openrouter_cost_accounting_complete: false', 'incomplete accounting must remain explicit');
includes(incompleteProgressSummary, '- openrouter_cost_microcredits: unknown', 'missing provider cost must not render as zero');
const progressCollector = fusionProgress.createFusionProgressCollector();
progressCollector.capture({ fusion_progress_receipt: { receipt_id: 'bad' } });
assert.strictEqual(progressCollector.snapshot().length, 0, 'unvalidated progress receipt must not be consumed');
assert.strictEqual(progressCollector.validation().valid, false, 'missing validation must fail aggregate receipt validation');
const validProgressCollector = fusionProgress.createFusionProgressCollector();
const boundProgressResult = fusionProgress.bindFusionProgressResultToRun({
  fusion_progress_receipt: { receipt_id: 'good', run_id: 'run-good' },
  fusion_progress_receipt_validation: { applied: true, valid: true, rejection_reasons: [] }
}, 'run-good');
validProgressCollector.capture(boundProgressResult);
assert.strictEqual(validProgressCollector.snapshot().length, 1, 'validated progress receipt must be retained');
assert.strictEqual(validProgressCollector.validation().valid, true, 'validated receipt aggregate must pass');
const foreignProgressCollector = fusionProgress.createFusionProgressCollector();
foreignProgressCollector.capture(fusionProgress.bindFusionProgressResultToRun({
  fusion_progress_receipt: { receipt_id: 'foreign', run_id: 'run-foreign' },
  fusion_progress_receipt_validation: { applied: true, valid: true, rejection_reasons: [] }
}, 'run-local'));
assert.strictEqual(foreignProgressCollector.snapshot().length, 0, 'foreign-run receipt must not be retained');
assert(foreignProgressCollector.validation().rejection_reasons.includes('fusion_progress_receipt_run_id_mismatch'), 'foreign-run rejection reason missing');
const secretProgress = fusionProgress.buildProgressMessage(null, 'route sk-or-v1-THIS-IS-A-SECRET-TOKEN', {
  model: 'sk-or-v1-THIS-IS-A-SECRET-TOKEN'
});
assert(!secretProgress.text.includes('sk-or-v1-'), 'progress UI must redact secret-like text');
assert.strictEqual(secretProgress.model, undefined, 'progress UI must drop secret-like metadata');
assert.strictEqual(fusionProgress.buildProgressMessage('lead_start', 'attacker-controlled text', {}).text, 'Lead request started.', 'known stages must use canonical UI text');
includes(extensionJs, 'Stopped before OpenRouter. Nothing left the machine.', 'redaction operator message missing');
