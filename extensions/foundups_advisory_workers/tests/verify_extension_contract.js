const fs = require('fs');
const path = require('path');
const assert = require('assert');
const cp = require('child_process');
const Module = require('module');

const fixtures = require('./fixtures');

const root = path.resolve(__dirname, '..', '..', '..');
const extDir = path.join(root, 'extensions', 'foundups_advisory_workers');
const extensionJs = fs.readFileSync(path.join(extDir, 'extension.js'), 'utf8');
const bridgePy = fs.readFileSync(path.join(root, 'scripts', 'advisory_model_once.py'), 'utf8');
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

assert.strictEqual(pkg.version, '0.3.32', 'package version must be 0.3.32');
includes(extensionJs, "const EXTENSION_VERSION = '0.3.32'", 'extension build mismatch');
assert.strictEqual(pkg.name, 'foundups-fusion-worker', 'package id must remain stable in branding slice');
assert.strictEqual(pkg.displayName, 'Foundups®Agent', 'display name must be Foundups®Agent');
includes(JSON.stringify(pkg), 'Foundups®Agent: Open', 'command title must use Foundups®Agent');
includes(extensionJs, "title: 'Foundups®Agent'", 'webview title must use Foundups®Agent');
includes(readme, 'Foundups®Agent is the product surface', 'README product identity statement missing');
includes(iface, 'Fusion is one internal reasoning mode, not the product identity', 'INTERFACE mode identity statement missing');
includes(roadmap, 'Foundups®Agent is the product surface', 'ROADMAP product identity statement missing');
includes(extensionJs, 'id="reddogWorkingTrail"', 'working trail DOM missing');
includes(extensionJs, 'data-reddog-pixel', 'trail pixel attribute missing');
includes(extensionJs, "command: 'progress'", 'progress command shape missing');
includes(extensionJs, 'Stopped before OpenRouter. Nothing left the machine.', 'redaction operator message missing');
assert(!extensionJs.includes("command: 'status', stage"), 'status must not carry stage field');
includes(extensionJs, 'REDDOG_STAGE_ACTIONS', 'structured stage map missing');
includes(extensionJs, 'REDDOG_PROGRESS_ACTIONS', 'progress regex fallback missing');
includes(extensionJs, 'function matchReddogProgress', 'matchReddogProgress missing');
includes(extensionJs, 'function formatElapsed', 'formatElapsed missing');
includes(readme, 'Version: 0.3.32', 'README version mismatch');
includes(extensionJs, 'function buildBridgePythonEnv', 'bridge Python UTF-8 env helper missing');
includes(extensionJs, 'PYTHONIOENCODING', 'bridge must set PYTHONIOENCODING=utf-8');
includes(extensionJs, 'PYTHONUTF8', 'bridge must set PYTHONUTF8=1');
includes(bridgePy, 'def _read_stdin_json', 'bridge must read stdin as UTF-8 bytes');
includes(bridgePy, 'sys.stdin.buffer.read()', 'bridge UTF-8 stdin invariant missing');
includes(extensionJs, 'UNICODE_SURROGATE_PLACEHOLDER', 'unicode surrogate placeholder missing');
includes(extensionJs, 'function normalizeBridgeTextForUnicode', 'unicode normalization helper missing');
includes(extensionJs, 'unicode_normalization_applied', 'unicode normalization telemetry missing');
includes(extensionJs, 'function applyBridgeContextBudget', 'context budget missing');
includes(extensionJs, 'function killBridgeChild', 'orphan cleanup missing');
includes(extensionJs, 'output_cap_exceeded', 'output cap failure reason missing');
includes(extensionJs, 'bridge_meta', 'bridge metadata payload missing');
includes(bridgePy, 'MAX_PANEL_MODELS = 6', 'panel cap missing in bridge');
includes(bridgePy, 'RETRYABLE_HTTP_STATUS', 'retryable status set missing');
includes(bridgePy, 'reason="missing_key"', 'missing_key taxonomy missing');

const acceptanceDoc = fs.readFileSync(path.join(extDir, 'docs', 'REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md'), 'utf8');
includes(acceptanceDoc, 'REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1', 'acceptance baseline doc title missing');
includes(acceptanceDoc, 'EXT-ACC-001', 'acceptance prompt pack missing EXT-ACC-001');
includes(acceptanceDoc, 'EXT-ACC-015', 'acceptance prompt pack missing EXT-ACC-015');
includes(acceptanceDoc, 'BASELINE_NOT_FIX', 'acceptance WSP_97 row missing');
includes(acceptanceDoc, 'LANE_B_EXCLUDED', 'acceptance lane lock missing');
includes(acceptanceDoc, 'NO_LIVE_OPENROUTER_IN_CI', 'acceptance CI boundary missing');
includes(acceptanceDoc, 'blocked_context_needs_local_0102_review', 'acceptance blocked handoff reference missing');
includes(roadmap, 'REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1', 'ROADMAP acceptance baseline missing');
includes(iface, 'External Acceptance Baseline', 'INTERFACE acceptance boundary missing');

includes(extensionJs, 'grid-template-rows: auto minmax(0, 1fr) auto', 'terminal/chat grid rows missing');
includes(extensionJs, 'html, body { height: 100%; overflow: hidden; }', 'body overflow lock missing');
includes(extensionJs, '#log { min-height: 0; overflow-y: auto;', 'scrollback output contract missing');
assert(extensionJs.indexOf('<main id="log"') < extensionJs.indexOf('<form id="form">'), 'output must precede bottom composer');
assert(!extensionJs.includes('>Send<'), 'Send button should not exist');
assert(!extensionJs.includes('>Clear<'), 'Clear button should not exist');

includes(extensionJs, 'RedDog Architect', 'RedDog Architect worker missing');
includes(extensionJs, 'WSP_15', 'WSP_15 requirement missing');
includes(extensionJs, 'WSP_97', 'WSP_97 requirement missing');
includes(extensionJs, 'Every finding must include a proposed fix', 'proposed-fix contract missing');
includes(extensionJs, 'HOLO_SKIP_MODEL', 'HoloIndex fastpath env missing');
includes(extensionJs, '--bundle-json', 'bundle-json retrieval missing');
includes(extensionJs, '--offline', 'offline fallback missing');
includes(extensionJs, 'Skillz/Wardrobe/Rolodex discovery', 'Skillz/Rolodex discovery context missing');

includes(bridgePy, 'evaluate_redaction_gate(prompt, context_for_gate)', 'prompt/context redaction gate missing');
includes(bridgePy, 'redacted_user_message = gate.redacted_prompt', 'redacted user assembly missing');
includes(bridgePy, 'messages = [{"role": "system", "content": _system_prompt(payload)}]', 'Fusion alias system prompt missing');
includes(bridgePy, 'base_system = _system_prompt(payload)', 'manual panel system prompt missing');
includes(bridgePy, 'GLM_PRINCIPAL_MODEL = "z-ai/glm-5.2"', 'bridge GLM principal missing');
includes(bridgePy, 'DEEPSEEK_CRITIC_MODEL = "deepseek/deepseek-v4-pro"', 'bridge DeepSeek V4 critic missing');

includes(iface, 'SPECIFIED_NOT_IMPLEMENTED', 'interface truth boundary missing');
includes(iface, 'WSP_15 Priority', 'interface priority contract missing');
includes(roadmap, 'REDDOG_FOUNDUP_INTAKE_PACKET_MODE_PHASE1', 'FoundUp intake roadmap missing');

includes(extensionJs, 'function classifyTaskForRedDog', 'auto effort classifier missing');
includes(extensionJs, 'function resolveAutoEffort', 'resolveAutoEffort missing');
includes(extensionJs, 'function resolveAutoContextMode', 'resolveAutoContextMode missing');
includes(extensionJs, 'function resolveModelMode', 'resolveModelMode missing');
includes(extensionJs, 'function validateRedDogOutput', 'validateRedDogOutput missing');
includes(extensionJs, 'function buildRepairPrompt', 'buildRepairPrompt missing');
includes(extensionJs, 'output_validation', 'review packet validator status missing');
includes(extensionJs, 'function buildRepairBoundedContext', 'repair bounded context helper missing');
includes(extensionJs, 'function mergeRepairedOutput', 'merge repaired output helper missing');
includes(extensionJs, 'repair_minimal', 'repair context mode telemetry missing');
includes(extensionJs, 'egress-safe placeholders', 'repair prompt placeholder provenance missing');
includes(extensionJs, 'repair_single_started', 'repair single trail event missing');
includes(extensionJs, 'normalizeRepairBridgeStageToWorkTrail', 'repair trail normalizer missing');
includes(extensionJs, 'function extractMarkdownSection', 'extractMarkdownSection missing');
includes(extensionJs, 'function modeSelectionReasoning', 'mode selection reasoning missing');
includes(extensionJs, 'Architect Trace', 'architect trace schema missing');
includes(extensionJs, 'Verification gaps', 'verification gaps schema missing');
includes(extensionJs, "mode === 'wsp_holo_skillz' || mode === 'wsp_holo_git_skillz'", 'skillz context wiring in buildBoundedRepoContext missing');
includes(extensionJs, 'mode_selection_reasoning', 'review packet mode selection reasoning missing');
includes(readme, 'WSP_97 Truth Table', 'README WSP_97 truth table missing');
includes(roadmap, 'REDDOG_GOVERNED_HANDOFF_CONTRACT_PHASE1', 'governed handoff roadmap slice missing');
includes(auditDoc, 'RedDogGovernedWorkOrder', 'audit doc schema missing');
const dryrunPy = fs.readFileSync(path.join(root, 'modules', 'communication', 'moltbot_bridge', 'src', 'reddog_governed_work_order_dryrun.py'), 'utf8');
includes(dryrunPy, 'validate_work_order_dryrun', 'dry-run validator missing');
includes(dryrunPy, 'WOULD_ACCEPT_WITH_RETRIEVAL_GAP', 'dry-run retrieval gap decision missing');
includes(dryrunPy, 'HoloIndexEvidencePacket', 'HoloIndex evidence packet missing');
const probePy = fs.readFileSync(path.join(root, 'modules', 'platform_integration', 'github_integration', 'src', 'reddog_github_permission_probe.py'), 'utf8');
includes(probePy, 'probe_repo_permission', 'GitHub permission probe missing');
includes(probePy, 'raw_secret_included', 'probe raw_secret_included flag missing');
const policyGatePy = fs.readFileSync(path.join(root, 'modules', 'communication', 'moltbot_bridge', 'src', 'reddog_openclaw_work_order_policy_gate.py'), 'utf8');
includes(policyGatePy, 'evaluate_work_order_policy_gate', 'OpenClaw policy gate missing');
includes(policyGatePy, 'POLICY_ACCEPT_WITH_RETRIEVAL_GAP', 'policy gate retrieval gap decision missing');
includes(policyGatePy, 'no_execution_performed', 'policy gate no_execution_performed missing');
includes(policyGatePy, 'permission_truth_label', 'policy gate permission_truth_label missing');
const receiptPy = fs.readFileSync(path.join(root, 'modules', 'communication', 'moltbot_bridge', 'src', 'reddog_work_order_receipt.py'), 'utf8');
includes(receiptPy, 'emit_work_order_receipt', 'RedDog work order receipt emitter missing');
includes(receiptPy, 'RedDogWorkOrderReceipt', 'RedDogWorkOrderReceipt schema missing');
includes(receiptPy, 'no_execution_performed', 'work order receipt no_execution_performed missing');
const invokePy = fs.readFileSync(path.join(root, 'modules', 'communication', 'moltbot_bridge', 'src', 'reddog_work_order_runtime_invocation.py'), 'utf8');
includes(invokePy, 'invoke_reddog_work_order_dryrun', 'runtime invocation dryrun missing');
includes(invokePy, 'no_execution_performed', 'runtime invocation no_execution_performed missing');
includes(iface, 'reddog_work_order_runtime_invocation.py', 'INTERFACE runtime invocation pointer missing');
includes(iface, 'reddog_work_order_receipt.py', 'INTERFACE work order receipt pointer missing');
includes(iface, 'reddog_openclaw_work_order_policy_gate.py', 'INTERFACE policy gate pointer missing');
includes(iface, 'reddog_github_permission_probe.py', 'INTERFACE permission probe pointer missing');
includes(iface, 'reddog_governed_work_order_dryrun.py', 'INTERFACE dry-run module pointer missing');
includes(auditDoc, 'authenticated principal', 'audit doc principal wording missing');
includes(auditDoc, 'HoloIndex Discoverability', 'audit doc discoverability section missing');
includes(auditDoc, 'F0_AUTONOMOUS_MERGE_NOT_IMPLEMENTED', 'audit doc F0 merge row missing');
includes(iface, 'REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md', 'INTERFACE audit doc pointer missing');
includes(readme, 'REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md', 'README audit doc pointer missing');
includes(roadmap, 'docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md', 'audit doc path missing from roadmap');
includes(roadmap, 'REDDOG_GITHUB_PERMISSION_PROBE_PHASE1', 'github permission probe slice missing');
includes(roadmap, 'REDDOG_OPENCLAW_WORK_ORDER_POLICY_GATE_PHASE1', 'OpenClaw policy gate slice missing');
includes(roadmap, 'REDDOG_HERMES_WORK_ORDER_RECEIPT_PHASE1', 'Hermes work order receipt slice missing');
includes(roadmap, 'REDDOG_WORK_ORDER_RUNTIME_INVOCATION_DRYRUN_PHASE1', 'runtime invocation dryrun slice missing');
includes(roadmap, 'REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1', 'WRE executor contract slice missing');
includes(executorContractDoc, 'WREExecutorResult', 'executor contract output schema missing');
includes(executorContractDoc, 'Execution valve', 'executor contract execution valve missing');
includes(executorContractDoc, 'no autonomous merge', 'executor contract merge guard missing');
includes(executorContractDoc, 'WSP_97 truth table', 'executor contract WSP_97 table missing');
includes(executorContractDoc, 'WSP_15 — Next implementation slices', 'executor contract WSP_15 slices missing');
includes(iface, 'REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1.md', 'INTERFACE executor contract pointer missing');
includes(roadmap, 'docs/audits/architecture/REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1.md', 'executor contract path missing from roadmap');
const executorDryrunPy = fs.readFileSync(path.join(root, 'modules', 'communication', 'moltbot_bridge', 'src', 'reddog_wre_executor_dryrun.py'), 'utf8');
includes(executorDryrunPy, 'plan_wre_isolated_worktree_execution_dryrun', 'WRE executor dryrun planner missing');
includes(executorDryrunPy, 'WREExecutorPlan', 'WREExecutorPlan schema missing');
includes(executorDryrunPy, 'no_mutation_performed', 'executor dryrun no_mutation_performed missing');
includes(iface, 'reddog_wre_executor_dryrun.py', 'INTERFACE executor dryrun pointer missing');
includes(roadmap, 'REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_DRYRUN_PHASE1', 'executor dryrun slice missing');
const adapterContractDocPath = path.join(root, 'docs', 'audits', 'architecture', 'REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1.md');
const adapterContractDoc = fs.readFileSync(adapterContractDocPath, 'utf8');
includes(adapterContractDoc, 'AssignmentDispatcher', 'adapter contract AssignmentDispatcher ruling missing');
includes(adapterContractDoc, 'FoundUpJob', 'adapter contract FoundUpJob target missing');
includes(adapterContractDoc, 'autonomous_task', 'adapter contract autonomous_task target missing');
includes(adapterContractDoc, 'Receipt reconciliation', 'adapter contract receipt reconciliation missing');
includes(adapterContractDoc, 'WSP_97 truth table', 'adapter contract WSP_97 table missing');
includes(iface, 'REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1.md', 'INTERFACE OpenClaw adapter pointer missing');
includes(roadmap, 'REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1', 'OpenClaw adapter contract slice missing');
const valveContractDocPath = path.join(root, 'docs', 'audits', 'architecture', 'REDDOG_WRE_EXECUTION_VALVE_CONTRACT_PHASE1.md');
const valveContractDoc = fs.readFileSync(valveContractDocPath, 'utf8');
includes(valveContractDoc, 'VALVE_CLOSED', 'execution valve contract default state missing');
includes(valveContractDoc, 'VALVE_OPEN_DRYRUN_ONLY', 'execution valve dryrun state missing');
includes(valveContractDoc, 'VALVE_OPEN_WORKTREE_CREATE', 'execution valve worktree state missing');
includes(valveContractDoc, 'assignment_dispatcher', 'execution valve AssignmentDispatcher reject missing');
const valvePy = fs.readFileSync(path.join(root, 'modules', 'communication', 'moltbot_bridge', 'src', 'reddog_wre_execution_valve.py'), 'utf8');
includes(valvePy, 'evaluate_reddog_execution_valve', 'execution valve evaluator missing');
includes(valvePy, 'no_execution_performed', 'execution valve no_execution_performed missing');
includes(iface, 'reddog_wre_execution_valve.py', 'INTERFACE execution valve pointer missing');
includes(roadmap, 'REDDOG_WRE_EXECUTION_VALVE_PHASE1', 'execution valve slice missing');
const adapterDryrunContractDocPath = path.join(root, 'docs', 'audits', 'architecture', 'REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_CONTRACT_PHASE1.md');
const adapterDryrunContractDoc = fs.readFileSync(adapterDryrunContractDocPath, 'utf8');
includes(adapterDryrunContractDoc, 'no_enqueue_performed', 'adapter dryrun contract no_enqueue missing');
includes(adapterDryrunContractDoc, 'VALVE_OPEN_DRYRUN_ONLY', 'adapter dryrun contract valve requirement missing');
includes(adapterDryrunContractDoc, 'foundup_job', 'adapter dryrun contract foundup_job target missing');
includes(adapterDryrunContractDoc, 'autonomous_task', 'adapter dryrun contract autonomous_task target missing');
const adapterDryrunPy = fs.readFileSync(path.join(root, 'modules', 'communication', 'moltbot_bridge', 'src', 'reddog_openclaw_adapter_dryrun.py'), 'utf8');
includes(adapterDryrunPy, 'plan_reddog_openclaw_adapter_dryrun', 'adapter dryrun planner missing');
includes(adapterDryrunPy, 'no_enqueue_performed', 'adapter dryrun no_enqueue_performed missing');
includes(iface, 'reddog_openclaw_adapter_dryrun.py', 'INTERFACE adapter dryrun pointer missing');
includes(roadmap, 'REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_PHASE1', 'adapter dryrun slice missing');
includes(roadmap, 'External RedDog Lane Queue (post-#888)', 'post-#888 external lane queue missing');
includes(roadmap, 'REDDOG_GOVERNED_REPO_WORK_ORDER_DRYRUN_PHASE1', 'governed work order dryrun slice missing');
includes(roadmap, 'REDDOG_RUN_TRACE_TELEMETRY_CORRECTION_PHASE1', 'run trace telemetry correction slice missing');
includes(roadmap, 'REDDOG_PFMALL_SURFACE_BINDING_PHASE1', 'pfMALL binding roadmap slice missing');
includes(roadmap, 'REDDOG_REVIEW_PACKET_MEMORY_PHASE1', 'review packet memory roadmap slice missing');
includes(extensionJs, 'function constructWspTaskPrompt', 'constructWspTaskPrompt missing');
includes(extensionJs, 'function redactedDigest', 'redactedDigest missing');
includes(extensionJs, '0102_generated_from_work_focus', 'prompt construction marker missing');
includes(extensionJs, 'work_focus_digest', 'work focus digest in review packet missing');
includes(extensionJs, 'wsp_prompt_digest', 'wsp prompt digest in review packet missing');
includes(extensionJs, 'id="workFocus"', 'work focus composer missing');
includes(extensionJs, '012 work focus', '012 work focus label missing');
assert(!extensionJs.includes('012 prompt'), 'legacy 012 prompt label must be removed');
includes(readme, 'Work Focus Contract', 'README work focus contract missing');
includes(iface, '012 Work Focus to 0102 WSP Task Prompt', 'INTERFACE work focus contract missing');
includes(roadmap, 'REDDOG_BRIDGE_HARDENING_PHASE1', 'bridge hardening roadmap slice missing');
includes(extensionJs, 'Routing: Auto via WSP_15', 'auto routing label missing');
includes(extensionJs, 'deepseek/deepseek-v4-pro', 'DeepSeek V4 Pro critic default missing');
includes(extensionJs, 'z-ai/glm-5.2', 'GLM 5.2 principal default missing');
includes(extensionJs, 'openrouter_fusion_alias', 'OpenRouter Fusion alias path must remain implemented');
assert(!extensionJs.includes('<select id="mode"'), 'Mode must not be a 012-facing dropdown');
assert(!extensionJs.includes('<select id="contextMode"'), 'Context must not be a 012-facing dropdown');
assert(!extensionJs.includes('<select id="effort"'), 'Effort must not be a 012-facing dropdown');

const vscodeMock = {
  window: {
    activeTextEditor: null,
    visibleTextEditors: [],
    createWebviewPanel: () => ({ webview: { onDidReceiveMessage: () => ({ dispose() {} }), asWebviewUri: () => ({ toString: () => '' }) }, dispose() {} })
  },
  workspace: {
    workspaceFolders: [{ uri: { fsPath: root } }],
    getConfiguration: () => ({ get: (_key, fallback) => fallback })
  },
  commands: { registerCommand: () => ({ dispose() {} }) },
  env: { clipboard: { writeText: async () => {} } },
  Uri: { joinPath: (_base, _name) => ({ fsPath: path.join(extDir, 'icon.png') }) },
  ViewColumn: { Beside: 2 }
};
const vscodePath = path.join(extDir, 'node_modules', 'vscode', 'index.js');
require.cache[vscodePath] = { exports: vscodeMock, loaded: true, id: vscodePath };
const originalResolve = Module._resolveFilename;
Module._resolveFilename = function(request, parent, isMain, options) {
  if (request === 'vscode') {
    return vscodePath;
  }
  return originalResolve.call(this, request, parent, isMain, options);
};

const orchestrator = require(path.join(extDir, 'extension.js'));
Module._resolveFilename = originalResolve;

const ultra = orchestrator.classifyTaskForRedDog('Audit OAuth auth secrets on live runtime deploy path', 'auto', 'reddog_architect');
assert.strictEqual(ultra.tier, 'ULTRA', 'security/auth prompts must classify ULTRA');

const wsp = orchestrator.classifyTaskForRedDog('Review WSP protocol architecture and HoloIndex gap', 'auto', 'wsp_gate_critic');
assert(wsp.tier === 'HIGH' || wsp.tier === 'ULTRA', 'WSP/architecture prompts must classify HIGH or ULTRA');

const regular = orchestrator.classifyTaskForRedDog('Reply with exactly: regular mode works', 'auto', 'smoke_tester');
assert.strictEqual(regular.tier, 'REGULAR', 'simple smoke prompts must classify REGULAR');

assert.strictEqual(
  orchestrator.resolveModelMode(wsp, 'auto', 'reddog_architect'),
  'foundups_fusion',
  'RedDog WSP work must auto-route to auditable manual panel'
);
assert.strictEqual(
  orchestrator.resolveModelMode(wsp, 'openrouter_fusion_alias', 'reddog_architect'),
  'openrouter_fusion_alias',
  'OpenRouter Fusion alias must remain available as an explicit path'
);
assert.strictEqual(
  orchestrator.resolveModelMode(regular, 'auto', 'smoke_tester'),
  'openrouter_single',
  'Regular smoke work must auto-route to single-model mode'
);

assert.strictEqual(orchestrator.resolveAutoEffort(ultra, 'auto'), 'ultra', 'auto effort must map ULTRA classification to ultra');
assert.strictEqual(orchestrator.resolveAutoContextMode(ultra, 'auto'), 'wsp_holo_git_skillz', 'ULTRA must attach WSP/Holo/git/Skillz context');
assert.strictEqual(orchestrator.resolveAutoContextMode(wsp, 'auto'), 'wsp_holo_skillz', 'HIGH/WSP must attach WSP/Holo/Skillz context');
assert.strictEqual(orchestrator.resolveAutoContextMode(regular, 'auto'), 'wsp_holo', 'REGULAR must attach wsp_holo HoloIndex grounding');
assert.strictEqual(orchestrator.resolveAutoEffort(regular, 'auto'), 'regular', 'auto effort must map REGULAR classification to regular');

const reasoning = orchestrator.modeSelectionReasoning(wsp, 'high', 'foundups_fusion', 'wsp_holo_skillz');
includes(reasoning, 'Fusion manual panel', 'mode selection reasoning must explain Fusion path');
includes(reasoning, 'wsp_holo_skillz', 'mode selection reasoning must cite resolved context');

const singleReasoning = orchestrator.modeSelectionReasoning(regular, 'regular', 'openrouter_single', 'none');
includes(singleReasoning, 'Single-model GLM', 'mode selection reasoning must explain single-model path');

const architectBad = 'Decision\nFindings\nEvidence\nProposed fixes\nUncertainties\nWSP_97 Truth Labels\nWSP_15 Priority\nNext safest step';
const architectValidation = orchestrator.validateRedDogOutput(architectBad, { substantiveArchitect: true, mode: 'openrouter_single' });
assert.strictEqual(architectValidation.valid, false, 'architect validator must require Architect Trace and Verification gaps');
assert(architectValidation.missingSections.includes('Architect Trace'), 'architect validator must list Architect Trace');

const fusionBad = architectBad + '\nArchitect Trace\nVerification gaps';
const fusionValidation = orchestrator.validateRedDogOutput(fusionBad, { substantiveArchitect: true, mode: 'foundups_fusion' });
assert.strictEqual(fusionValidation.valid, false, 'fusion validator must require Lead/Synthesis structure');
assert(fusionValidation.missingSections.some((s) => /Fusion panel/i.test(s)), 'fusion validator must flag missing panel structure');

const badOutput = 'Decision\nFindings\nEvidence';
const validation = orchestrator.validateRedDogOutput(badOutput);
assert.strictEqual(validation.valid, false, 'validator must detect missing sections');
assert(validation.missingSections.includes('Proposed fixes'), 'validator must list missing Proposed fixes');

const repairPrompt = orchestrator.buildRepairPrompt('task', badOutput, validation.missingSections);
includes(repairPrompt, 'Do not invent evidence', 'repair prompt must forbid invented evidence');
includes(repairPrompt, 'egress-safe placeholders', 'repair prompt must warn on sanitized placeholders');
includes(repairPrompt, 'Preserve factual content', 'repair prompt must preserve draft content');

// OSR-001..OSR-006 REDDOG_OUTPUT_SCHEMA_REPAIR_HARDENING_PHASE1
const repairContext = orchestrator.buildRepairBoundedContext();
assert(repairContext.length < 2000, 'OSR-001: repair context must stay minimal');
includes(repairContext, 'REPAIR_PASS_BOUNDED_CONTEXT', 'OSR-001: repair context must declare repair pass');
includes(repairContext, 'egress-safe placeholders', 'OSR-002: repair context must note placeholder provenance');
assertFusionRedactionGatePasses(repairContext, 'OSR-003: minimal repair context must pass gate');

const blockDraftPrompt = orchestrator.buildRepairPrompt('safe task', fixtures.REPAIR_DRAFT_WITH_BLOCK_LITERALS, ['Proposed fixes']);
assert(!blockDraftPrompt.includes('grant authority'), 'OSR-004: repair prompt must sanitize block literals in draft');
assertFusionRedactionGatePasses(blockDraftPrompt, 'OSR-004: sanitized repair prompt must pass gate');

const fusionPrimary = '## RedDog Routing\n\n## Lead (z-ai/glm-5.2)\n\n## Decision\n\nok\n\n## Findings\n\nF1\n\n## Critic (deepseek/deepseek-v4-pro)\n\nNone\n\n## Synthesis (z-ai/glm-5.2)\n\n## Decision\n\nok\n\n## Findings\n\nF1';
const mergedRepair = orchestrator.mergeRepairedOutput(
  fusionPrimary,
  fixtures.REPAIR_SUPPLEMENT_SECTIONS,
  ['Proposed fixes', 'Uncertainties', 'WSP_97 Truth Labels', 'WSP_15 Priority', 'Verification gaps', 'Next safest step', 'Architect Trace', 'Evidence']
);
const mergedValidation = orchestrator.validateRedDogOutput(mergedRepair.text, { substantiveArchitect: true, mode: 'foundups_fusion' });
assert.strictEqual(mergedValidation.valid, true, 'OSR-005: merged primary+supplement must satisfy schema');
assert(mergedRepair.text.includes('## Schema repair supplement'), 'OSR-005: merged output must retain supplement marker');

const primaryMissingTail = fusionPrimary;
const combinedSupplement = fixtures.REPAIR_TAIL_SUPPLEMENT + '\n\n' + fixtures.REPAIR_SUPPLEMENT_SECTIONS;
const tailMerge = orchestrator.mergeRepairedOutput(
  primaryMissingTail,
  combinedSupplement,
  ['Evidence', 'Verification gaps', 'Next safest step', 'Architect Trace', 'Proposed fixes', 'Uncertainties', 'WSP_97 Truth Labels', 'WSP_15 Priority']
);
includes(tailMerge.text, '## Evidence', 'OSR-007: tail merge must include Evidence');
includes(tailMerge.text, '## Verification gaps', 'OSR-007: tail merge must include Verification gaps');
includes(tailMerge.text, '## Next safest step', 'OSR-007: tail merge must include Next safest step');
includes(tailMerge.text, '## Architect Trace', 'OSR-007: tail merge must include Architect Trace');
const tailValidation = orchestrator.validateRedDogOutput(tailMerge.text, { substantiveArchitect: true, mode: 'foundups_fusion' });
assert.strictEqual(tailValidation.valid, true, 'OSR-007: tail supplement must complete schema');

const repairStage = orchestrator.normalizeRepairBridgeStageToWorkTrail('single_start', 'Regular OpenRouter request started');
assert.strictEqual(repairStage.event, 'repair_single_started', 'OSR-008: repair single_start maps to repair_single_started');
const repairPanelStage = orchestrator.normalizeRepairBridgeStageToWorkTrail('panel_start', 'Panel requests started');
assert.strictEqual(repairPanelStage.event, 'repair_single_started', 'OSR-008: repair panel_start must not emit panel_started');

const repairPromptSections = orchestrator.buildRepairPrompt('task', 'draft', ['Evidence', 'Architect Trace', 'Next safest step']);
includes(repairPromptSections, '## Evidence', 'OSR-009: repair prompt must list required headers');
includes(repairPromptSections, '## Architect Trace', 'OSR-009: repair prompt must list Architect Trace header');
includes(repairPromptSections, '## Next safest step', 'OSR-009: repair prompt must list Next safest step header');

const repairTraceFailed = orchestrator.buildRunTraceSection({
  review_packet: {
    task_classification: { tier: 'HIGH' },
    resolved_effort: 'high',
    resolved_mode: 'foundups_fusion',
    resolved_context: 'wsp_holo_skillz',
    mode_selection_reasoning: 'Fusion manual panel',
    principal_model: 'z-ai/glm-5.2',
    panel_models: ['deepseek/deepseek-v4-pro'],
    output_validation: {
      validated: false,
      repair_attempted: true,
      repair_ok: false,
      repair_context_mode: 'repair_minimal',
      repair_mode: 'openrouter_single',
      missing_sections_after_repair: ['Evidence', 'Next safest step']
    }
  }
}, 'reddog_architect', 'Repo context attached', null, 'high');
includes(repairTraceFailed, 'repair_context_mode: repair_minimal', 'OSR-010: Run Trace must expose repair context on failed repair');
includes(repairTraceFailed, 'repair_mode: openrouter_single', 'OSR-010: Run Trace must expose repair mode on failed repair');
includes(repairTraceFailed, 'missing_sections_after_repair: Evidence, Next safest step', 'OSR-010: Run Trace must list remaining missing sections');

const handoffContext = orchestrator.skillzWardrobeRolodexContext(root, 'process all youtube comments with existing skillz', 12000);
includes(handoffContext, 'Skillz/Wardrobe/Rolodex discovery', 'handoff context header missing');
assert(/youtube|comments|skillz/i.test(handoffContext), 'handoff context must surface relevant YouTube/comment/Skillz paths');
assert(!handoffContext.includes('(no matching Skillz/Wardrobe/Rolodex paths found'), 'handoff context must not be empty for YouTube comments');

const ytFocus = 'process youtube comments';
const ytClass = orchestrator.classifyTaskForRedDog(ytFocus, 'auto', 'reddog_architect');
const ytWsp = orchestrator.constructWspTaskPrompt(ytFocus, ytClass, 'HoloIndex ok', 'reddog_architect');
includes(ytWsp, 'WSP_00', 'WSP prompt must include WSP_00 operating frame');
includes(ytWsp, 'WSP_97', 'WSP prompt must include WSP_97 truth boundary');
includes(ytWsp, 'WSP_15 tier', 'WSP prompt must include WSP_15 tier/routing');
includes(ytWsp, ytFocus, 'WSP prompt must embed bounded work focus excerpt');
includes(ytWsp, '012 work focus (non-authoritative input)', 'WSP prompt must declare non-authoritative input');
assert.notStrictEqual(ytWsp.trim(), ytFocus.trim(), 'raw work focus must not bypass constructWspTaskPrompt');
assert(ytWsp.length > ytFocus.length + 50, 'WSP task prompt must wrap work focus with 0102 contract framing');

const longFocus = 'process youtube comments '.repeat(200);
const focusDigest = orchestrator.redactedDigest(longFocus, 180);
assert.strictEqual(typeof focusDigest.hash, 'string', 'digest hash required');
assert(focusDigest.excerpt.length <= 180, 'digest excerpt must be bounded');
assert(!Object.prototype.hasOwnProperty.call(focusDigest, 'raw'), 'digest must not store raw full focus');
assert(focusDigest.length === longFocus.length, 'digest length metadata may exceed excerpt');

const wspDigest = orchestrator.redactedDigest(ytWsp, 320);
assert(wspDigest.excerpt.length <= 320, 'wsp prompt digest excerpt must be bounded');

function extractBridgeStages(source) {
  const stages = [];
  const re = /_progress\("([^"]+)"/g;
  let match;
  while ((match = re.exec(source)) !== null) {
    stages.push(match[1]);
  }
  return [...new Set(stages)].sort();
}

const bridgeStages = extractBridgeStages(bridgePy);
const mappedStages = Object.keys(orchestrator.REDDOG_STAGE_ACTIONS).sort();
assert.deepStrictEqual(mappedStages, bridgeStages, 'REDDOG_STAGE_ACTIONS must cover every advisory bridge stage');
assert.strictEqual(bridgeStages.length, 16, 'expected 16 unique bridge stages');
assert.strictEqual(orchestrator.REDDOG_TERMINAL_HOLD_MS, 3000, 'terminal hold must be 3000ms');

const redactionMatch = orchestrator.matchReddogProgress({ stage: 'redaction_blocked', text: 'Redaction gate blocked before network.' });
assert.strictEqual(redactionMatch.action, 'barking', 'redaction_blocked must map to barking');
assert.strictEqual(redactionMatch.pixel, '!rd!', 'redaction_blocked must use barking pixel');

const successMatch = orchestrator.matchReddogProgress({ stage: 'single_done', text: 'Regular OpenRouter response received: x' });
assert.strictEqual(successMatch.action, 'pointing', 'single_done must map to pointing');
assert.strictEqual(successMatch.pixel, '>rd>', 'single_done must use pointing pixel');

const failureMatch = orchestrator.matchReddogProgress({ stage: 'panel_blocked', text: 'Panel blocked: x' });
assert.strictEqual(failureMatch.action, 'sitting', 'panel_blocked must map to sitting');
assert.strictEqual(failureMatch.pixel, '.rd.', 'panel_blocked must use sitting pixel');

const diggingMatch = orchestrator.matchReddogProgress({ stage: null, text: 'Output schema incomplete. Missing: Architect Trace. Running one repair pass...' });
assert.strictEqual(diggingMatch.action, 'digging', 'repair pass text must map to digging');

const sniffMatch = orchestrator.matchReddogProgress({ stage: null, text: 'Work focus sent. 0102 will assemble WSP task prompt...' });
assert.strictEqual(sniffMatch.action, 'sniffing', 'work focus sent must map to sniffing');

assert.strictEqual(orchestrator.formatElapsed(45000), '45s', 'formatElapsed under 60s');
assert.strictEqual(orchestrator.formatElapsed(62000), '1m02s', 'formatElapsed above 60s');

const blocked = orchestrator.enrichRedactionBlockResult({ ok: false, reason: 'redaction_blocked' });
assert.strictEqual(blocked.review_packet.made_network_call, false, 'redaction block must set made_network_call=false');
assert.strictEqual(blocked.review_packet.retry_count, 0, 'redaction block must set retry_count=0');
assert.strictEqual(orchestrator.REDACTION_BLOCK_OPERATOR_MESSAGE, 'Stopped before OpenRouter. Nothing left the machine.', 'operator message constant');

const forbiddenPixels = ['\u2022', '\u0254', '\u1401', '\u1400'];
for (const glyph of forbiddenPixels) {
  assert(!extensionJs.includes(glyph), 'trail pixel grammar must stay ASCII-only');
}

const budget = orchestrator.applyBridgeContextBudget('p'.repeat(20000), 'c'.repeat(60000));
assert.strictEqual(budget.budget.truncation_applied, true, 'context budget must truncate oversized prompt/context');
assert(budget.budget.truncation_reason === 'prompt_char_budget' || budget.budget.truncation_reason === 'prompt_and_context_char_budget', 'truncation_reason must be low-cardinality');
assert(budget.prompt.length <= orchestrator.BRIDGE_MAX_PROMPT_CHARS, 'prompt must respect cap');
assert(budget.context.length <= orchestrator.BRIDGE_MAX_CONTEXT_CHARS, 'context must respect cap');

const truncatedFocus = 'process youtube comments '.repeat(400);
const truncatedClass = orchestrator.classifyTaskForRedDog(truncatedFocus, 'auto', 'reddog_architect');
const truncatedWsp = orchestrator.constructWspTaskPrompt(truncatedFocus, truncatedClass, 'HoloIndex ok', 'reddog_architect');
const budgetedWsp = orchestrator.applyBridgeContextBudget(truncatedWsp, 'c'.repeat(60000));
includes(budgetedWsp.prompt, 'WSP_97', 'WSP_97 contract must survive context truncation');
includes(budgetedWsp.prompt, '012 work focus (non-authoritative input)', 'work-focus contract must survive truncation');
assert.strictEqual(budgetedWsp.budget.truncation_applied, true, 'oversized work focus must trigger truncation_applied');

assert.strictEqual(
  orchestrator.bridgeStreamCapExceeded(orchestrator.BRIDGE_MAX_STDOUT_BYTES - 1024, 2048, orchestrator.BRIDGE_MAX_STDOUT_BYTES),
  true,
  'stdout cap helper must detect overflow before retaining full stream'
);
assert.strictEqual(
  orchestrator.bridgeStreamCapExceeded(orchestrator.BRIDGE_MAX_STDOUT_BYTES - 4096, 1024, orchestrator.BRIDGE_MAX_STDOUT_BYTES),
  false,
  'stdout cap helper must allow bounded streams'
);

const fakeChild = {
  killed: false,
  killCount: 0,
  kill() {
    this.killCount += 1;
    this.killed = true;
  }
};
const bridgeState = { bridgeChild: fakeChild, disposed: false };
orchestrator.killBridgeChild(bridgeState);
assert.strictEqual(fakeChild.killCount, 1, 'dispose cleanup must call child.kill() once');
assert.strictEqual(bridgeState.bridgeChild, null, 'bridge child reference must clear after kill');

assert.strictEqual(orchestrator.shouldAcceptBridgeCompletion(false, { disposed: true }), false, 'disposed panel must reject late completion packets');
assert.strictEqual(orchestrator.shouldAcceptBridgeCompletion(false, { disposed: false }), true, 'active panel must accept first completion packet');
assert.strictEqual(orchestrator.shouldAcceptBridgeCompletion(true, { disposed: false }), false, 'settled bridge must ignore duplicate completion packets');

const configuredPath = path.join(root, 'scripts', 'advisory_model_once.py');
const configuredInterp = orchestrator.resolvePythonInterpreter(root, configuredPath);
assert.strictEqual(configuredInterp.source, 'configured', 'existing configured path must win');
assert.strictEqual(configuredInterp.path, configuredPath, 'configured interpreter path must be selected');

const systemRoot = fs.mkdtempSync(path.join(require('os').tmpdir(), 'reddog-bridge-'));
const systemInterp = orchestrator.resolvePythonInterpreter(systemRoot, 'python');
assert.strictEqual(systemInterp.source, 'system', 'default python must fall back to system when no workspace venv');
includes(systemInterp.path, 'python', 'system fallback must return python executable name');

if (fs.existsSync(path.join(root, '.venv'))) {
  const dotVenvInterp = orchestrator.resolvePythonInterpreter(root, 'python');
  assert.strictEqual(dotVenvInterp.source, 'workspace_dotvenv', 'workspace .venv must win over default python');
}

const interpreter = orchestrator.resolvePythonInterpreter(systemRoot, 'python');
assert(['configured', 'workspace_dotvenv', 'workspace_venv', 'system'].includes(interpreter.source), 'resolver source must be configured|workspace_dotvenv|workspace_venv|system');
try {
  fs.rmSync(systemRoot, { recursive: true, force: true });
} catch (err) {
  // ignore temp cleanup errors on Windows file locks
}

assert(!extensionJs.includes('for="workerType">Worker<'), 'Worker UI label must be renamed to 0102 Role');
includes(extensionJs, 'for="workerType">0102 Role<', '0102 Role label missing');
assert(extensionJs.indexOf('id="reddogWorkingTrail"') < extensionJs.indexOf('class="toolbar"'), 'Working Tail must precede controls row');
assert(extensionJs.indexOf('class="toolbar"') < extensionJs.indexOf('id="workFocus"'), 'controls row must precede 012 work focus composer');
includes(extensionJs, 'function buildCopyMarkdown', 'buildCopyMarkdown missing');
includes(extensionJs, 'function buildRunTraceSection', 'buildRunTraceSection missing');
includes(extensionJs, 'function buildWorkTrailSection', 'buildWorkTrailSection missing');
includes(extensionJs, 'function buildRedactionGateReport', 'buildRedactionGateReport missing');
includes(extensionJs, 'function buildGovernedHandoffRecommendation', 'buildGovernedHandoffRecommendation missing');
includes(extensionJs, 'function detectMojibake', 'detectMojibake missing');
includes(extensionJs, 'copy_markdown', 'copy_markdown payload missing');

const mojibakeSample = orchestrator.detectMojibake('section \u7aa6 broken \u7aaa tail');
assert.strictEqual(mojibakeSample.detected, true, 'mojibake detector must catch attached-output pattern');
assert(mojibakeSample.markers.includes('\u7aa6'), 'mojibake detector must catch U+7AA6');
assert(mojibakeSample.markers.includes('\u7aaa'), 'mojibake detector must catch U+7AAA');

const handoffRec = orchestrator.buildGovernedHandoffRecommendation('audit WRE bridge handoff', { tier: 'ULTRA' }, 'reddog_architect', 'wsp_holo_skillz', {
  substantive: true,
  workFocusDigest: 'abc123',
  wspPromptDigest: 'def456'
});
assert.strictEqual(handoffRec.target, 'WRE', 'substantive WRE task must target WRE handoff');
assert.strictEqual(handoffRec.handoff_needed, 'true', 'successful substantive WRE task may recommend handoff');
assert.strictEqual(handoffRec.authority_level, 'advisory_only', 'handoff must remain advisory_only');

const blockedHandoffRec = orchestrator.buildGovernedHandoffRecommendation('audit WRE bridge handoff', { tier: 'ULTRA' }, 'reddog_architect', 'wsp_holo_skillz', {
  substantive: true,
  redactionBlockedOnly: true,
  workFocusDigest: 'abc123',
  wspPromptDigest: 'def456'
});
assert.strictEqual(blockedHandoffRec.handoff_needed, 'unknown', 'redaction-block-only run must use conservative handoff_needed');
assert.strictEqual(blockedHandoffRec.target, 'WRE', 'target may remain inferred for blocked-local packet');
assert.strictEqual(blockedHandoffRec.reason, 'blocked_context_needs_local_0102_review', 'blocked-local handoff must include conservative reason');
assert.strictEqual(blockedHandoffRec.wsp15_priority, 'P1', 'blocked-local handoff must default to P1');
assert.strictEqual(blockedHandoffRec.suggested_slice_name, 'none', 'blocked-local handoff must not invent slice name');

const dedupeTrail = orchestrator.createWorkTrail();
dedupeTrail.push('redaction_gate_blocked', 'Redaction gate blocked before network.');
dedupeTrail.push('redaction_gate_blocked');
assert.strictEqual(dedupeTrail.count(), 1, 'adjacent duplicate Work Trail events must dedupe');
assert.strictEqual(dedupeTrail.toEvents()[0].detail, 'Redaction gate blocked before network.', 'dedupe must keep detail-bearing event');

const blockedCopy = orchestrator.buildCopyMarkdown({
  reason: 'redaction_blocked',
  redaction_reason: 'blocked_policy',
  review_packet: {
    task_classification: { tier: 'HIGH' },
    resolved_effort: 'high',
    resolved_mode: 'openrouter_single',
    resolved_context: 'wsp_holo_skillz',
    mode_selection_reasoning: 'Single-model GLM principal',
    principal_model: 'z-ai/glm-5.2',
    panel_models: ['deepseek/deepseek-v4-pro'],
    holoindex_scorecard: {
      holoindex_status: 'bundle_json_ok',
      wsp_hits: 3,
      code_hits_count: 3,
      code_hits: 3,
      skill_hits: 1,
      target_recall_ok: false,
      index_gap_detected: true,
      direct_read_fallback_used: false
    },
    output_validation: { validated: false, reason: 'redaction_blocked' },
    made_network_call: false,
    retry_count: 0
  }
}, 'reddog_architect', 'Repo context attached: wsp_holo_skillz', orchestrator.createWorkTrail(), {
  holoindex_status: 'bundle_json_ok',
  wsp_hits: 3,
  code_hits_count: 3,
  code_hits: 3,
  skill_hits: 1,
  target_recall_ok: false,
  index_gap_detected: true,
  direct_read_fallback_used: false
}, 'high', {
  promptConstruction: {
    work_focus_digest: { hash: 'abc1234567890abcd' },
    wsp_prompt_digest: { hash: 'def1234567890abcd' }
  },
  contextMode: 'wsp_holo_skillz',
  substantive: true,
  handoffRecommendation: blockedHandoffRec
});
includes(blockedCopy, '## Run Trace', 'Copy MD must include Run Trace');
includes(blockedCopy, '## Work Trail', 'Copy MD must include Work Trail');
includes(blockedCopy, '## Redaction Gate Report', 'blocked Copy MD must include Redaction Gate Report');
includes(blockedCopy, '0102 role: RedDog Architect', 'Run Trace must include 0102 role');
includes(blockedCopy, 'BLOCKED_LOCALLY', 'redaction Copy MD must include BLOCKED_LOCALLY');
includes(blockedCopy, 'made_network_call: false', 'redaction Copy MD must include made_network_call=false');
includes(blockedCopy, 'blocked_payload_part: unknown', 'unknown payload part must stay unknown');
includes(blockedCopy, 'raw_snippets_included: false', 'blocked packet must declare no raw snippets');
includes(blockedCopy, 'holoindex_status:', 'Copy MD must include HoloIndex recall scorecard');
includes(blockedCopy, 'code_hits_count:', 'Run Trace must include code_hits_count');
includes(blockedCopy, 'target_recall_ok:', 'Run Trace must include target_recall_ok');

const recallHit = orchestrator.evaluateTargetRecall('Review extensions/foundups_advisory_workers/extension.js for WSP_97', {
  task_retrieval: {
    code_hits: [{ location: 'extensions/foundups_advisory_workers/extension.js', need: 'path match: extension.js' }]
  }
});
assert.strictEqual(recallHit.target_recall_ok, true, 'target recall must pass when extension.js is in hits');
assert.strictEqual(recallHit.index_gap_detected, false, 'index_gap must be false when target recall ok');

const recallMiss = orchestrator.evaluateTargetRecall('Review extensions/foundups_advisory_workers/extension.js for WSP_97', {
  task_retrieval: {
    code_hits: [{ location: 'extensions/foundups_advisory_workers/package.json', need: 'path match: package.json' }]
  }
});
assert.strictEqual(recallMiss.target_recall_ok, false, 'target recall must fail when only adjacent paths hit');
assert.strictEqual(recallMiss.index_gap_detected, true, 'index_gap must be true on target-specific miss');

// REDDOG_TARGET_RECALL_PATH_AWARE_PHASE1 (slice 1/3): path-aware required-target detector.
includes(extensionJs, 'function parseRequiredTargetPaths', 'required-target parser missing');
includes(extensionJs, 'function isSelfFileLocation', 'self-file guard missing');
includes(extensionJs, 'required_targets_total', 'required_targets_total scorecard field missing');
includes(extensionJs, 'required_targets_recalled', 'required_targets_recalled scorecard field missing');
includes(extensionJs, 'required_targets_missing', 'required_targets_missing scorecard field missing');

// TRP-001: explicit required list is parsed into repo-relative paths.
const trpParsed = orchestrator.parseRequiredTargetPaths(fixtures.FOUNDUP_CREATION_PROMPT);
assert.strictEqual(trpParsed.length, fixtures.FOUNDUP_REQUIRED_TARGETS.length, 'TRP-001: parser must recover every required target');
for (const req of fixtures.FOUNDUP_REQUIRED_TARGETS) {
  assert(trpParsed.includes(req), 'TRP-001: parser must include ' + req);
}
assert.strictEqual(orchestrator.parseRequiredTargetPaths('Review extension.js for WSP_97').length, 0, 'TRP-001: no required list => empty parse (backward compatible)');

// TRP-002: 0 of N required targets in bundle => honest blind report.
const trpMissAll = orchestrator.evaluateTargetRecall(fixtures.FOUNDUP_CREATION_PROMPT, {
  task_retrieval: { code_hits: [{ location: 'docs/unrelated.md', need: 'path match: unrelated.md' }] }
});
assert.strictEqual(trpMissAll.index_gap_detected, true, 'TRP-002: 0/N required must set index_gap_detected=true');
assert.strictEqual(trpMissAll.target_recall_ok, false, 'TRP-002: 0/N required must set target_recall_ok=false');
assert.strictEqual(trpMissAll.required_targets_total, fixtures.FOUNDUP_REQUIRED_TARGETS.length, 'TRP-002: required_targets_total must equal N');
assert.strictEqual(trpMissAll.required_targets_recalled, 0, 'TRP-002: required_targets_recalled must be 0');
assert.strictEqual(trpMissAll.required_targets_missing.length, fixtures.FOUNDUP_REQUIRED_TARGETS.length, 'TRP-002: all required must be missing');
for (const req of fixtures.FOUNDUP_REQUIRED_TARGETS) {
  assert(trpMissAll.required_targets_missing.includes(req), 'TRP-002: missing list must name ' + req);
}

// TRP-003: self-file guard - retrieving ONLY extension.js must NOT satisfy required targets.
const trpSelfOnly = orchestrator.evaluateTargetRecall(fixtures.FOUNDUP_CREATION_PROMPT, {
  task_retrieval: { code_hits: [{ location: 'extensions/foundups_advisory_workers/extension.js', need: 'path match: extension.js' }] }
});
assert.strictEqual(trpSelfOnly.index_gap_detected, true, 'TRP-003: self-file only must set index_gap_detected=true');
assert.strictEqual(trpSelfOnly.required_targets_recalled, 0, 'TRP-003: self-file must not count toward required recall');
assert(orchestrator.isSelfFileLocation('extensions/foundups_advisory_workers/extension.js'), 'TRP-003: extension.js path must be self-file');
assert(orchestrator.isSelfFileLocation('some/other/extension.js'), 'TRP-003: extension.js basename must be self-file');
assert(!orchestrator.isSelfFileLocation('WSP_framework/src/WSP_109_FoundUp_Onboarding_Protocol.md'), 'TRP-003: required target must not be self-file');

// TRP-004: all required targets present in content => honest satisfied report.
const trpAllPresent = orchestrator.evaluateTargetRecall(fixtures.FOUNDUP_CREATION_PROMPT, {
  task_retrieval: { code_hits: fixtures.FOUNDUP_REQUIRED_TARGETS.map((p) => ({ location: p, need: 'path match: ' + p })) }
});
assert.strictEqual(trpAllPresent.index_gap_detected, false, 'TRP-004: all required present must set index_gap_detected=false');
assert.strictEqual(trpAllPresent.target_recall_ok, true, 'TRP-004: all required present must set target_recall_ok=true');
assert.strictEqual(trpAllPresent.required_targets_recalled, fixtures.FOUNDUP_REQUIRED_TARGETS.length, 'TRP-004: required_targets_recalled must equal N');
assert.strictEqual(trpAllPresent.required_targets_missing.length, 0, 'TRP-004: no required target may be missing');

// TRP-005: self-file plus required targets present => required still satisfied (self-file ignored, not penalized).
const trpMixed = orchestrator.evaluateTargetRecall(fixtures.FOUNDUP_CREATION_PROMPT, {
  task_retrieval: { code_hits: [{ location: 'extensions/foundups_advisory_workers/extension.js', need: 'self' }].concat(
    fixtures.FOUNDUP_REQUIRED_TARGETS.map((p) => ({ location: p, need: 'path match: ' + p }))
  ) }
});
assert.strictEqual(trpMixed.target_recall_ok, true, 'TRP-005: self-file alongside required targets must still satisfy recall');
assert.strictEqual(trpMixed.required_targets_recalled, fixtures.FOUNDUP_REQUIRED_TARGETS.length, 'TRP-005: self-file must not reduce recalled count');

// TRP-006: backward-compat - no required list preserves prior inference behavior and never claims unknown as a gap.
const trpLegacy = orchestrator.evaluateTargetRecall('Review extensions/foundups_advisory_workers/extension.js for WSP_97', {
  task_retrieval: { code_hits: [{ location: 'extensions/foundups_advisory_workers/extension.js', need: 'path match: extension.js' }] }
});
assert.strictEqual(trpLegacy.target_recall_ok, true, 'TRP-006: legacy inferred recall must still pass');
assert.strictEqual(trpLegacy.index_gap_detected, false, 'TRP-006: legacy inferred recall must not flag gap');
assert.strictEqual(trpLegacy.required_targets_total, 0, 'TRP-006: legacy path reports zero required targets');

const trpEmptyMeta = orchestrator.evaluateTargetRecall('generic task with no targets', { task_retrieval: { code_hits: [] } });
assert.strictEqual(trpEmptyMeta.target_recall_ok, 'unknown', 'TRP-006: no targets at all must remain unknown, not a false gap');
assert.strictEqual(trpEmptyMeta.index_gap_detected, false, 'TRP-006: unknown recall must not fabricate a gap');

// TRP-007: scorecard surfaces the truthful required-target vocabulary for the blind case.
const trpScorecard = orchestrator.extractHoloIndexScorecard('wsp_holo', {
  target_recall_ok: false,
  index_gap_detected: true,
  required_targets_total: 3,
  required_targets_recalled: 0,
  required_targets_missing: fixtures.FOUNDUP_REQUIRED_TARGETS.slice()
});
const trpScorecardLines = orchestrator.formatHoloIndexScorecardLines(trpScorecard).join('\n');
assert.strictEqual(trpScorecard.required_targets_total, 3, 'TRP-007: scorecard required_targets_total must pass through');
assert.strictEqual(trpScorecard.required_targets_recalled, 0, 'TRP-007: scorecard required_targets_recalled must pass through');
assert(Array.isArray(trpScorecard.required_targets_missing) && trpScorecard.required_targets_missing.length === 3, 'TRP-007: scorecard required_targets_missing must be preserved');
includes(trpScorecardLines, '- required_targets_total: 3', 'TRP-007: rendered scorecard must show required_targets_total');
includes(trpScorecardLines, '- required_targets_recalled: 0', 'TRP-007: rendered scorecard must show required_targets_recalled');
includes(trpScorecardLines, '- required_targets_missing: ', 'TRP-007: rendered scorecard must show required_targets_missing');

// REDDOG_DIRECT_READ_FALLBACK_BY_PATH_PHASE1 (slice 2/3): governed direct-read telemetry.
includes(extensionJs, 'function buildMustIncludeArgs', 'DRF: must-include arg builder missing');
includes(extensionJs, 'function buildDirectReadContentSection', 'DRF: direct-read content section builder missing');
includes(extensionJs, '--bundle-must-include', 'DRF: extension must request must-include paths from the Python bundle layer');
includes(extensionJs, 'direct_read_fallback_used', 'DRF: direct_read_fallback_used telemetry missing');
includes(extensionJs, 'direct_read_paths', 'DRF: direct_read_paths telemetry missing');
includes(extensionJs, 'direct_read_rejected', 'DRF: direct_read_rejected telemetry missing');
includes(extensionJs, 'direct_read_bytes', 'DRF: direct_read_bytes telemetry missing');
includes(extensionJs, 'direct_read_truncated', 'DRF: direct_read_truncated telemetry missing');

// DRF-001: must-include args are built from missing targets, symbols excluded, deduped, path-quoted per --bundle-must-include.
const drfArgs = orchestrator.buildMustIncludeArgs([
  'WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md',
  'symbol:createFoundUp',
  'WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md',
  'modules/foundups/agent/src/source_authority.py'
]);
assert.deepStrictEqual(drfArgs, [
  '--bundle-must-include', 'WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md',
  '--bundle-must-include', 'modules/foundups/agent/src/source_authority.py'
], 'DRF-001: must-include args must dedup, drop symbols, and prefix each path with --bundle-must-include');
assert.deepStrictEqual(orchestrator.buildMustIncludeArgs([]), [], 'DRF-001: empty missing list => no fetch args');
assert.deepStrictEqual(orchestrator.buildMustIncludeArgs(['symbol:only']), [], 'DRF-001: symbol-only missing list => no fetch args');

// DRF-002: direct-read telemetry from the Python bundle flows into meta + scorecard.
const drfBundle = JSON.stringify({
  task_retrieval: {
    code_hits: [
      { location: 'WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md', need: 'direct-read target', direct_read: true, content: '# WSP 109 onboarding', content_truncated: true },
      { location: 'modules/foundups/agent/src/source_authority.py', need: 'direct-read target', direct_read: true, content: 'class SourceAuthority: pass', content_truncated: false }
    ],
    metadata: { code_count: 2, wsp_count: 0 }
  },
  direct_read: {
    direct_read_fallback_used: true,
    direct_read_paths: ['WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md', 'modules/foundups/agent/src/source_authority.py'],
    direct_read_rejected: [{ path: '.env', reason: 'denied_basename' }, { path: '../../etc/passwd', reason: 'traversal' }],
    direct_read_bytes: 4096,
    direct_read_truncated: [{ path: 'WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md', bytes: 12000 }]
  }
});
const drfPrompt = [
  'Audit the FoundUp creation monorepo WSP_109 execution path.',
  '',
  'Required direct-read targets:',
  '- WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md',
  '- modules/foundups/agent/src/source_authority.py',
  '',
  'Produce required architect sections.'
].join('\n');
const drfMeta = orchestrator.holoIndexMetaFromBundle(drfBundle, false, drfPrompt);
assert.strictEqual(drfMeta.direct_read_fallback_used, true, 'DRF-002: direct_read_fallback_used must reflect the Python fetch');
assert.deepStrictEqual(drfMeta.direct_read_paths, ['WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md', 'modules/foundups/agent/src/source_authority.py'], 'DRF-002: direct_read_paths must pass through');
assert.strictEqual(drfMeta.direct_read_bytes, 4096, 'DRF-002: direct_read_bytes must pass through');
assert.strictEqual(drfMeta.direct_read_rejected.length, 2, 'DRF-002: direct_read_rejected must pass through');
assert.strictEqual(drfMeta.direct_read_truncated.length, 1, 'DRF-002: direct_read_truncated must pass through');

// DRF-003: after the fetch is present, slice-1 recall reports satisfied (gap resolved).
assert.strictEqual(drfMeta.target_recall_ok, true, 'DRF-003: fetched targets must satisfy required recall');
assert.strictEqual(drfMeta.index_gap_detected, false, 'DRF-003: index gap must clear once targets are fetched');
assert.strictEqual(drfMeta.required_targets_recalled, 2, 'DRF-003: both required targets must count as recalled');

// DRF-004: scorecard surfaces the direct-read vocabulary for the Work Trail.
const drfScorecard = orchestrator.extractHoloIndexScorecard('wsp_holo', drfMeta);
const drfLines = orchestrator.formatHoloIndexScorecardLines(drfScorecard).join('\n');
includes(drfLines, '- direct_read_fallback_used: true', 'DRF-004: rendered scorecard must show direct_read_fallback_used');
includes(drfLines, '- direct_read_paths: ', 'DRF-004: rendered scorecard must show direct_read_paths');
includes(drfLines, '- direct_read_rejected: .env (denied_basename)', 'DRF-004: rendered scorecard must show rejected path + reason');
includes(drfLines, '- direct_read_bytes: 4096', 'DRF-004: rendered scorecard must show direct_read_bytes');
includes(drfLines, '- direct_read_truncated: ', 'DRF-004: rendered scorecard must show direct_read_truncated');

// DRF-005: direct-read content section renders the fetched source (no fs re-read; from bundle JSON).
const drfSection = orchestrator.buildDirectReadContentSection(drfBundle);
assert(drfSection.text.length > 0, 'DRF-005: direct-read content section must render when direct_read hits exist');
includes(drfSection.text, '# WSP 109 onboarding', 'DRF-005: fetched content must be present in the section');
includes(drfSection.text, 'class SourceAuthority: pass', 'DRF-005: every fetched target content must be present');
includes(drfSection.text, '(truncated to governed budget)', 'DRF-005: truncated targets must be labelled');
assert.strictEqual(drfSection.paths.length, 2, 'DRF-005: section must list both fetched paths');
const drfEmptySection = orchestrator.buildDirectReadContentSection(JSON.stringify({ task_retrieval: { code_hits: [] } }));
assert.strictEqual(drfEmptySection.text, '', 'DRF-005: no direct_read hits => empty section (no fabricated content)');

// DRF-006: benign fetched content passes the EXISTING redaction gate unchanged.
// (This proves the direct-read section is normal context text; slice 2 adds no
// new sanitizer and weakens none.)
const drfBenignBundle = JSON.stringify({
  task_retrieval: {
    code_hits: [
      { location: 'modules/foundups/agent/src/example_readme.md', need: 'direct-read target', direct_read: true, content: '# Example\nThis module wires the onboarding flow and returns a status dict.', content_truncated: false }
    ],
    metadata: { code_count: 1, wsp_count: 0 }
  }
});
const drfBenignSection = orchestrator.buildDirectReadContentSection(drfBenignBundle);
assertFusionRedactionGatePasses(drfBenignSection.text, 'DRF-006: benign direct-read content must pass the existing redaction gate');

// DRF-007: SLICE BOUNDARY PROOF. Governance-adjacent fetched content is STILL
// blocked by the EXISTING redaction gate (source_authority category), unchanged
// by slice 2. Slice 3 owns audit-mode redaction relaxation; slice 2 must not
// weaken (or expand) any redaction category. The gate behavior is identical to
// before this slice for such content.
const drfGovSection = orchestrator.buildDirectReadContentSection(drfBundle);
let drfGovBlocked = false;
let drfGovCategory = '';
try {
  assertFusionRedactionGatePasses(drfGovSection.text, 'probe');
} catch (govErr) {
  drfGovBlocked = true;
  drfGovCategory = String((govErr && govErr.stdout) || '');
}
assert(drfGovBlocked, 'DRF-007: governance-adjacent fetched content must STILL be blocked by the DEFAULT redaction gate (audit-mode is opt-in)');
includes(drfGovCategory, 'source_authority', 'DRF-007: the existing source_authority category must still fire on the default (non-audit) path');

// DRF-008 (REDDOG_AUDIT_MODE_REDACTION_PHASE1, slice 3/3): the SAME governance-adjacent
// fetched content that DRF-007 shows BLOCKS by default now PASSES in audit_mode with the
// governance STRUCTURE preserved. Direct-read of required targets IS an audit context, so
// buildDirectReadContentSection surfaces audit_context=true.
assert.strictEqual(drfGovSection.audit_context, true, 'DRF-008: direct-read of required targets must surface audit_context=true');
assert.strictEqual(drfEmptySection.audit_context, false, 'DRF-008: no direct-read => audit_context stays false (backward compatible)');
const drfAuditRedacted = fusionRedactionGateAuditMode(drfGovSection.text, 'DRF-008 audit-mode gate');
includes(drfAuditRedacted, 'SourceAuthority', 'DRF-008: audit-mode must preserve the SourceAuthority enum identifier');
includes(drfAuditRedacted, 'source_authority', 'DRF-008: audit-mode must preserve the source_authority field name');

// DRF-009: CRITICAL SAFETY. In audit-mode a SYNTHETIC secret embedded in fetched content
// is STILL redacted (structure readable != secret readable). Fake key is split-prefixed so
// no literal provider secret is committed to this test source.
const _drfFakeKey = ('s' + 'k-') + 'FAKE' + 'Z'.repeat(44);
const drfSecretBundle = JSON.stringify({
  task_retrieval: {
    code_hits: [
      { location: 'modules/foundups/agent/src/source_authority.py', need: 'direct-read target', direct_read: true,
        content: 'class SourceAuthority(str, enum.Enum):\n    MONOREPO_POC = "monorepo_poc"\napi_key = "' + _drfFakeKey + '"\ncabr_payout = 12500.50', content_truncated: false }
    ],
    metadata: { code_count: 1, wsp_count: 0 }
  }
});
const drfSecretSection = orchestrator.buildDirectReadContentSection(drfSecretBundle);
const drfSecretRedacted = fusionRedactionGateAuditMode(drfSecretSection.text, 'DRF-009 audit-mode gate');
includes(drfSecretRedacted, 'SourceAuthority', 'DRF-009: audit-mode keeps governance structure readable');
includes(drfSecretRedacted, 'MONOREPO_POC', 'DRF-009: audit-mode keeps enum member readable');
includes(drfSecretRedacted, 'cabr_payout', 'DRF-009: audit-mode keeps the payout identifier readable');
assert(!drfSecretRedacted.includes(_drfFakeKey), 'DRF-009: SECRET VALUE must STILL be redacted in audit mode (no under-redaction)');
assert(!drfSecretRedacted.includes('12500.50'), 'DRF-009: payout AMOUNT must STILL be redacted in audit mode');
includes(drfSecretRedacted, '[REDACTED', 'DRF-009: redaction placeholder must be present for the stripped value');

includes(blockedCopy, '## Governed Handoff Recommendation', 'substantive task must include governed handoff recommendation');
includes(blockedCopy, 'handoff_needed: unknown', 'blocked-local packet must use conservative handoff_needed');
includes(blockedCopy, 'reason: blocked_context_needs_local_0102_review', 'blocked-local packet must include conservative handoff reason');
includes(blockedCopy, 'WSP_15 priority: P1', 'blocked-local packet must default handoff priority to P1');
includes(blockedCopy, 'suggested_slice_name: none', 'blocked-local packet must not invent slice name');
includes(blockedCopy, 'authority_level: advisory_only', 'handoff must remain advisory_only');
assert(!blockedCopy.includes('OPENROUTER_API_KEY'), 'Copy MD must not include secret-adjacent env names');
assert(!blockedCopy.includes('Bearer sk-'), 'Copy MD must not include bearer/token patterns');

const blockedTrail = orchestrator.createWorkTrail();
blockedTrail.push('orchestrator_started');
blockedTrail.push('redaction_gate_blocked', 'Redaction gate blocked before network.');
blockedTrail.push('redaction_gate_blocked');
const blockedTrailCopy = orchestrator.buildCopyMarkdown({
  reason: 'redaction_blocked',
  review_packet: { made_network_call: false, retry_count: 0, output_validation: { validated: false, reason: 'redaction_blocked' } }
}, 'reddog_architect', '', blockedTrail, null, 'high', { substantive: true, handoffRecommendation: blockedHandoffRec });
const trailLines = blockedTrailCopy.split('\n').filter((line) => line.startsWith('- redaction_gate_blocked'));
assert.strictEqual(trailLines.length, 1, 'blocked-local Copy MD must not show adjacent duplicate Work Trail events');

const cappedTrail = orchestrator.createWorkTrail();
for (let i = 0; i < 60; i++) {
  cappedTrail.push('orchestrator_started', 'event-' + i);
}
assert.strictEqual(cappedTrail.count(), orchestrator.WORK_TRAIL_MAX_EVENTS, 'Work Trail must cap normalized events');

const repairFailCopy = orchestrator.buildCopyMarkdown({
  ok: true,
  content: '## Decision\npartial answer',
  review_packet: {
    task_classification: { tier: 'HIGH' },
    resolved_effort: 'high',
    resolved_mode: 'openrouter_single',
    resolved_context: 'wsp_holo',
    mode_selection_reasoning: 'Single-model GLM principal',
    principal_model: 'z-ai/glm-5.2',
    panel_models: ['deepseek/deepseek-v4-pro'],
    made_network_call: true,
    output_validation: {
      validated: false,
      output_validation_failed: true,
      repair_attempted: true,
      repair_failure_reason: 'redaction_blocked',
      missing_sections: ['Architect Trace', 'WSP_15 Priority']
    }
  }
}, 'reddog_architect', 'Repo context attached', null, null, 'high', { substantive: false });
includes(repairFailCopy, 'OUTPUT_VALIDATION_FAILED', 'repair-blocked Copy MD must include validation failure');
includes(repairFailCopy, 'repair_failure_reason: redaction_blocked', 'repair-blocked Copy MD must include repair_failure_reason');
includes(repairFailCopy, 'Architect Trace', 'repair-blocked Copy MD must list missing sections');
includes(repairFailCopy, 'Output failed local contract validation.', 'repair-blocked Copy MD must include local fallback footer');
includes(repairFailCopy, 'reddog_effort:', 'Run Trace must include reddog_effort');
includes(repairFailCopy, 'provider_reasoning_requested:', 'Run Trace must include provider reasoning requested');
includes(repairFailCopy, 'provider_reasoning_applied: unknown', 'provider reasoning applied must be unknown in report-only slice');

const sanitized = orchestrator.sanitizeCopyMdText('OPENROUTER_API_KEY visible to bridge: yes');
includes(sanitized, 'key_env_present: true', 'trail sanitizer must normalize secret-adjacent env phrase');

// ADDENDUM E - 0102 test-first content inclusion (no OpenRouter)
// Fixtures: tests/fixtures.js — reuse EXT_ACC_001_PROMPT; do not duplicate.
const extAcc001Prompt = fixtures.EXT_ACC_001_PROMPT;

const recallTargets = orchestrator.inferRecallTargetPaths(extAcc001Prompt);
assert(recallTargets.includes(fixtures.EXT_ACC_001_TARGET_PATH), 'EXT-ACC-001 prompt must map to extension.js');

const extensionSnippet = orchestrator.readBoundedTargetSnippet(root, fixtures.EXT_ACC_001_TARGET_PATH, 24000);
includes(extensionSnippet.content, "const EXTENSION_VERSION = '0.3.32'", 'target snippet must include extension.js source');
assert(extensionSnippet.chars > 0, 'target snippet chars must be nonzero');
assert.strictEqual(extensionSnippet.omitted_reason, 'none', 'extension.js snippet must not be omitted');

for (const [badPath, label] of fixtures.TARGET_READ_DENIED_PATHS) {
  assert(orchestrator.isTargetReadPathDenied(badPath), 'must reject ' + label + ': ' + badPath);
}

const safeResolve = orchestrator.resolveSafeRepoFile(root, fixtures.EXT_ACC_001_TARGET_PATH);
assert.strictEqual(safeResolve.ok, true, 'extension.js must resolve inside workspace root');

const targetSection = orchestrator.buildTargetRecallContentSection(root, extAcc001Prompt, 24000);
includes(targetSection.text, '### Target recall content', 'target recall section header missing');
includes(targetSection.text, fixtures.EXT_ACC_001_TARGET_PATH, 'target recall must cite extension.js path');
includes(targetSection.text, "const EXTENSION_VERSION = '0.3.32'", 'target recall must include source snippet');
assert.strictEqual(targetSection.meta.target_content_included, true, 'target_content_included must be true when snippets present');
assert(targetSection.meta.target_content_chars > 0, 'target_content_chars must be > 0');

const wsp97Excerpt = orchestrator.buildWsp97ProtocolExcerpt(root, 4096);
includes(wsp97Excerpt.text, '### WSP protocol excerpt (bounded)', 'WSP_97 excerpt header missing');
includes(wsp97Excerpt.text, 'WSP 97: System Execution Prompting Protocol', 'WSP_97 excerpt must include protocol title');
assert.strictEqual(wsp97Excerpt.meta.wsp97_excerpt_included, true, 'wsp97_excerpt_included must be true');

const boundedContext = orchestrator.buildBoundedRepoContext('wsp_holo_skillz', extAcc001Prompt);
includes(boundedContext.text, '### Target recall content', 'bounded context must include target recall section');
includes(boundedContext.text, fixtures.EXT_ACC_001_TARGET_PATH, 'bounded context must include extension.js path');
includes(boundedContext.text, "const EXTENSION_VERSION = '0.3.32'", 'bounded context must include extension.js source snippet');
includes(boundedContext.text, '### WSP protocol excerpt (bounded)', 'WSP_97 task must include protocol excerpt');
includes(boundedContext.text, 'WSP 97: System Execution Prompting Protocol', 'bounded context must include WSP_97 excerpt body');
assert.strictEqual(boundedContext.holoindex_scorecard.target_content_included, true, 'scorecard target_content_included must be true');
assert(boundedContext.holoindex_scorecard.target_content_chars > 0, 'scorecard target_content_chars must be > 0');
includes(boundedContext.holoindex_scorecard.target_content_paths.join(','), fixtures.EXT_ACC_001_TARGET_PATH, 'scorecard must list included path');

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
includes(extensionJs, 'const continuationEnabled = message.useLastPacket === true', 'backend must fail closed (useLastPacket === true)');
assert(!extensionJs.includes('message.useLastPacket !== false'), 'legacy permissive default must be removed');
includes(extensionJs, 'const continuationAppended = continuationEnabled', 'single continuation_appended boolean must gate inclusion');
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
  { review_packet: { task_classification: { tier: 'HIGH' }, continuation_telemetry: { continuation_enabled: true, continuation_appended: true, continuation_source_run_id: 'run_xyz789' } } },
  'reddog_architect', null, null, 'high'
);
includes(runTraceWithTelemetry, 'continuation_enabled: true', 'Run Trace must include continuation_enabled');
includes(runTraceWithTelemetry, 'continuation_appended: true', 'Run Trace must include continuation_appended');
includes(runTraceWithTelemetry, 'continuation_source_run_id: run_xyz789', 'Run Trace must include continuation_source_run_id');

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

console.log('Foundups®Agent extension contract checks passed.');
