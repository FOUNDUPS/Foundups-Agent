assert(!extensionJs.includes("command: 'status', stage"), 'status must not carry stage field');
includes(extensionJs, 'REDDOG_STAGE_ACTIONS', 'structured stage map missing');
includes(extensionJs, 'REDDOG_PROGRESS_ACTIONS', 'progress regex fallback missing');
includes(extensionJs, 'function matchReddogProgress', 'matchReddogProgress missing');
includes(extensionJs, 'function formatElapsed', 'formatElapsed missing');
includes(readme, 'Version: 0.4.135', 'README version mismatch');
includes(extensionJs, 'function buildBridgePythonEnv', 'bridge Python UTF-8 env helper missing');
includes(startOperationsEnvironmentJs, 'PYTHONIOENCODING', 'bridge must set PYTHONIOENCODING=utf-8');
includes(startOperationsEnvironmentJs, 'PYTHONUTF8', 'bridge must set PYTHONUTF8=1');
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
includes(extensionJs, 'REDDOG_HOLO_RETRIEVAL_MODE', 'HoloIndex explicit lexical opt-down missing');
includes(extensionJs, "delete env.HOLO_SKIP_MODEL", 'semantic-first path must clear inherited lexical override');
includes(extensionJs, 'include_bundle: true', 'governed bundle request missing');
includes(extensionJs, 'allowBundleOnlyBridge: false', 'async owner bundle reuse gate missing');
includes(extensionJs, 'Skillz/Wardrobe/Rolodex discovery', 'Skillz/Rolodex discovery context missing');

includes(bridgePy, 'evaluate_redaction_gate(', 'prompt/context redaction gate missing');
includes(bridgePy, 'audit_mode=audit_context_requested', 'audit_context bridge wire missing');
includes(bridgePy, 'redacted_user_message = gate.redacted_prompt', 'redacted user assembly missing');
includes(bridgePy, 'messages = [{"role": "system", "content": _system_prompt(payload)}]', 'Fusion alias system prompt missing');
includes(bridgePy, 'base_system = _system_prompt(payload)', 'manual panel system prompt missing');
includes(bridgePy, 'GLM_PRINCIPAL_MODEL = "z-ai/glm-5.2"', 'bridge GLM principal missing');
includes(bridgePy, 'DEEPSEEK_CRITIC_MODEL = "deepseek/deepseek-v4-pro"', 'bridge DeepSeek V4 critic missing'); includes(bridgePy, 'QWEN_MAX_PANEL_MODEL = "qwen/qwen3.8-max"', 'bridge Qwen 3.8 Max critic missing');
includes(bridgePy, 'KIMI_PANEL_MODEL = "moonshotai/kimi-k3"', 'bridge Kimi K3 critic missing');
includes(bridgePy, 'KIMI_K3_PANEL_MAX_TOKENS = 4096', 'Kimi K3 critic budget missing');
includes(bridgePy, 'body["reasoning"] = {"effort": "max"}', 'Kimi K3 max-reasoning request contract missing');
includes(bridgePy, '"panel_max_tokens": panel_max_tokens', 'Kimi K3 actual panel budget receipt missing');

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
includes(bridgePy, 'fusion_quorum_missing_required_evidence', 'Fusion quorum must block missing required evidence');
includes(bridgePy, 'fusion_quorum_lead_missing', 'Fusion quorum must block empty/None lead output');
includes(bridgePy, 'fusion_quorum_challenging_critic_missing', 'Fusion quorum must require a critic challenge');
includes(bridgePy, 'fusion_quorum_synthesis_unavailable', 'Fusion quorum must fail closed on synthesis failure');
includes(bridgePy, '_critic_challenges_framing_and_priority', 'Fusion quorum must check framing and priority challenge');
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
includes(executorContractDoc, 'WSP_15 \u2014 Next implementation slices', 'executor contract WSP_15 slices missing');
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
const liveEnqueueContractDocPath = path.join(root, 'docs', 'audits', 'architecture', 'REDDOG_OPENCLAW_LIVE_ENQUEUE_CONTRACT_PHASE1.md');
const liveEnqueueContractDoc = fs.readFileSync(liveEnqueueContractDocPath, 'utf8');
includes(liveEnqueueContractDoc, 'RedDogOpenClawLiveEnqueueContractReceipt', 'live enqueue contract receipt missing');
includes(liveEnqueueContractDoc, 'VALVE_OPEN_LIVE_ENQUEUE', 'live enqueue contract valve state missing');
includes(liveEnqueueContractDoc, 'no_enqueue_performed', 'live enqueue contract no_enqueue missing');
includes(liveEnqueueContractDoc, 'AssignmentDispatcher', 'live enqueue contract AssignmentDispatcher ruling missing');
includes(liveEnqueueContractDoc, 'SPECIFIED_NOT_IMPLEMENTED', 'live enqueue contract implementation status missing');
includes(iface, 'REDDOG_OPENCLAW_LIVE_ENQUEUE_CONTRACT_PHASE1.md', 'INTERFACE live enqueue contract pointer missing');
includes(roadmap, 'REDDOG_OPENCLAW_LIVE_ENQUEUE_CONTRACT_PHASE1', 'live enqueue contract slice missing');
includes(roadmap, 'External RedDog Lane Queue (post-#888)', 'post-#888 external lane queue missing');
includes(roadmap, 'REDDOG_GOVERNED_REPO_WORK_ORDER_DRYRUN_PHASE1', 'governed work order dryrun slice missing');
includes(roadmap, 'REDDOG_RUN_TRACE_TELEMETRY_CORRECTION_PHASE1', 'run trace telemetry correction slice missing');
includes(roadmap, 'REDDOG_PFMALL_SURFACE_BINDING_PHASE1', 'pfMALL binding roadmap slice missing');
includes(roadmap, 'REDDOG_REVIEW_PACKET_MEMORY_PHASE1', 'review packet memory roadmap slice missing');
includes(extensionJs, 'function constructWspTaskPrompt', 'constructWspTaskPrompt missing');
includes(orchestrationPromptTraceJs, 'function metadataDigest', 'redactedDigest implementation missing');
includes(orchestrationPromptTraceJs, 'createHmac',
  'pre-gate prompt metadata must use an opaque process-local keyed digest');
includes(extensionJs.replace(/\r\n/g, '\n'), 'finishTrace(\n      webview, result, localPromptTrace, sanitizeCopyMdText',
  'Copy MD sanitizer must gate exact prompt disclosure before digest-backed display');
includes(orchestrationPromptRoutesJs, "worker: 'reddog_architect'",
  'grounding-failure prompt trace must record its actual architect fallback role');
includes(orchestrationPromptRoutesJs, "contextMode: 'grounding_failure_receipt'",
  'grounding-failure prompt trace must record its actual bounded context route');
includes(extensionJs + orchestrationPromptRoutesJs, "'backend_compatibility_audit_degraded_no_model', 'backend_compatibility_receipt'",
  'compatibility-degraded local result must use an explicit no-model route');
includes(orchestrationPromptRoutesJs, "'holoindex_recovery_queue_no_model', 'holoindex_recovery_receipt'",
  'queued HoloIndex recovery must use an explicit no-model route');
includes(extensionJs, "'local_no_model', 'local_authoritative_query'",
  'local authoritative results must use an explicit no-model route');
includes(extensionJs + orchestrationPromptRoutesJs, 'A local audit receipt will be returned; no model or network call will be made.',
  'compatibility degradation must not announce a bridge or model call');
includes(extensionJs + orchestrationPromptRoutesJs, 'the WSP task prompt was not sent to a bridge or model.',
  'compatibility degradation must report that prompt assembly was not transmitted');
assert(
  extensionJs.indexOf('} else if (auditDegraded) {')
    < extensionJs.indexOf('} else if (!groundingPreflight.passed) {'),
  'compatibility degradation must resolve locally before grounding-failure routing'
);
includes(extensionJs, '0102_generated_from_work_focus', 'prompt construction marker missing');
includes(extensionJs, 'work_focus_digest', 'work focus digest in review packet missing');
includes(extensionJs, 'wsp_prompt_digest', 'wsp prompt digest in review packet missing');
includes(extensionJs, 'id="workFocus"', 'work focus composer missing');
includes(extensionJs, '012 work focus', '012 work focus label missing');
assert(!extensionJs.includes('012 prompt'), 'legacy 012 prompt label must be removed');
includes(readme, 'Work Focus Contract', 'README work focus contract missing');
includes(iface, '012 Work Focus to 0102 WSP Task Prompt', 'INTERFACE work focus contract missing');
includes(roadmap, 'REDDOG_BRIDGE_HARDENING_PHASE1', 'bridge hardening roadmap slice missing');
includes(extensionJs, 'Routing: Auto task-fit heuristic', 'truthful auto routing label missing');
assert(!extensionJs.includes('Routing: Auto via WSP_15'),
  'model routing must not masquerade as a WSP_15 allocation');
includes(extensionJs, 'deepseek/deepseek-v4-pro', 'DeepSeek V4 Pro critic default missing'); includes(extensionJs, 'qwen/qwen3.8-max', 'Qwen 3.8 Max critic default missing');
includes(extensionJs, 'moonshotai/kimi-k3', 'Kimi K3 critic default missing');
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
  extensions: {
    getExtension: () => undefined
  },
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
const semanticGroundingPolicy = require(path.join(extDir, 'semantic_grounding_policy.js'));
Module._resolveFilename = originalResolve;

// REDDOG_HOLO_SEMANTIC_FIRST_PHASE1: mode selection and truth receipts.
assert.strictEqual(orchestrator.resolveHoloRetrievalMode({}), 'semantic', 'HSF-001: production default must be semantic');
assert.strictEqual(orchestrator.resolveHoloRetrievalMode({ REDDOG_HOLO_RETRIEVAL_MODE: 'lexical' }), 'lexical', 'HSF-001: lexical mode must require explicit opt-down');
assert.strictEqual(orchestrator.resolveHoloRetrievalMode({ REDDOG_HOLO_RETRIEVAL_MODE: 'unexpected' }), 'semantic', 'HSF-001: invalid modes must fail to semantic');
const hsfSemanticEnv = orchestrator.buildHoloQueryEnv({ HOLO_SKIP_MODEL: '1', HOLO_OFFLINE: '1', KEEP_ME: 'yes' }, 'semantic');
assert.strictEqual(hsfSemanticEnv.HOLO_SKIP_MODEL, undefined, 'HSF-002: semantic mode must clear inherited HOLO_SKIP_MODEL');
assert.strictEqual(hsfSemanticEnv.HOLO_OFFLINE, '1', 'HSF-002: semantic mode must preserve the operator offline/network boundary');
assert.strictEqual(hsfSemanticEnv.HOLOINDEX_QUERY_READONLY, '1', 'HSF-002: semantic queries remain read-only');
assert.strictEqual(hsfSemanticEnv.KEEP_ME, undefined, 'HSF-002: unrelated environment must not cross');
const hsfLexicalEnv = orchestrator.buildHoloQueryEnv({}, 'lexical');
assert.strictEqual(hsfLexicalEnv.HOLO_SKIP_MODEL, '1', 'HSF-003: explicit lexical opt-down must set HOLO_SKIP_MODEL');
assert.strictEqual(hsfLexicalEnv.HOLOINDEX_QUERY_READONLY, '1', 'HSF-003: lexical queries remain read-only');

const hsfSemanticBundle = JSON.stringify({
  task_retrieval: {
    code_hits: [],
    metadata: {
      retrieval_mode: 'semantic',
      embedding_backend: 'sentence_transformers',
      routing_active: false,
      code_count: 3,
      wsp_count: 2
    }
  }
});
const hsfMeta = orchestrator.holoIndexMetaFromBundle(hsfSemanticBundle, false, 'semantic audit');
assert.strictEqual(hsfMeta.retrieval_mode, 'semantic', 'HSF-004: actual retrieval mode must enter RedDog telemetry');
assert.strictEqual(hsfMeta.embedding_backend, 'sentence_transformers', 'HSF-004: actual embedding backend must enter RedDog telemetry');
assert.strictEqual(hsfMeta.routing_active, false, 'HSF-004: routing truth must enter RedDog telemetry');
const hsfScorecard = orchestrator.extractHoloIndexScorecard('wsp_holo', hsfMeta);
const hsfLines = orchestrator.formatHoloIndexScorecardLines(hsfScorecard).join('\n');
includes(hsfLines, '- retrieval_mode: semantic', 'HSF-004: scorecard must expose semantic retrieval truth');
includes(hsfLines, '- embedding_backend: sentence_transformers', 'HSF-004: scorecard must expose backend truth');
const hsfSummary = orchestrator.summarizeHoloBundle(hsfSemanticBundle);
includes(hsfSummary, 'mode=semantic', 'HSF-005: bundle summary must expose semantic mode');
includes(hsfSummary, 'backend=sentence_transformers', 'HSF-005: bundle summary must expose backend');

// HSF-006: prove the pre-existing block-scope defect is closed. A failed
// bundle must reach the lexical fallback with a valid read-only environment.
const hsfOriginalExecFileSync = cp.execFileSync;
const hsfOriginalMode = process.env.REDDOG_HOLO_RETRIEVAL_MODE;
const hsfOwnerRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-owner-failure-'));
const hsfOwnerScripts = path.join(hsfOwnerRoot, 'scripts');
fs.mkdirSync(hsfOwnerScripts);
const hsfOwnerFailure = {
  ok: false,
  source: 'holoindex_owner_service',
  freshness: 'UNKNOWN',
  raw_result: {},
  error: 'simulated_owner_unavailable',
  owner_attempts: 2,
  owner_retry_performed: true,
  owner_retry_reason: 'HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP',
  index_gap_detected: true,
  stale_reasons: ['holoindex_owner_query_failed'],
  no_holoindex_reindex_performed: true
};
const hsfOwnerPayload = Buffer.from(JSON.stringify(hsfOwnerFailure), 'utf8').toString('base64');
fs.writeFileSync(
  path.join(hsfOwnerScripts, 'reddog_holoindex_owner_query_once.py'),
  [
    'import base64',
    'import sys',
    'sys.stdin.buffer.read()',
    `sys.stdout.write(base64.b64decode("${hsfOwnerPayload}").decode("utf-8"))`
  ].join('\n'),
  'utf8'
);
let hsfExecCalls = 0;
try {
  process.env.REDDOG_HOLO_RETRIEVAL_MODE = 'semantic';
  cp.execFileSync = function(_exe, args) {
    hsfExecCalls += 1;
    throw new Error(
      'HSF-006: raw Holo CLI fallback must not run: '
      + JSON.stringify(args)
    );
  };
  // The governed owner one-shot owns both bounded semantic and lexical bundles.
  // The extension must not regain a second raw Holo CLI fallback authority.
  // This interceptor is a tripwire for that forbidden regression.
  const hsfFallback = orchestrator.holoIndexOutput(hsfOwnerRoot, 'semantic fallback contract', 18000);
  assert.strictEqual(hsfExecCalls, 0, 'HSF-006: owner failure must not invoke a raw lexical fallback');
  assert.strictEqual(hsfFallback.meta.holoindex_status, 'generation_bound_query_failed', 'HSF-006: failed owner proof must outrank the lexical fallback status');
  assert.strictEqual(hsfFallback.meta.holoindex_owner_attempts, 2, 'HSF-006: rejected owner retains bounded attempt telemetry');
  assert.strictEqual(hsfFallback.meta.holoindex_owner_retry_performed, true, 'HSF-006: rejected owner retains retry occurrence');
  assert.strictEqual(hsfFallback.meta.holoindex_owner_retry_reason,
    'HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP', 'HSF-006: rejected owner retains retry reason');
  assert.strictEqual(hsfFallback.meta.requested_retrieval_mode, 'semantic', 'HSF-006: receipt must retain the requested mode');
  assert.strictEqual(hsfFallback.meta.retrieval_mode, 'lexical', 'HSF-006: receipt must expose actual lexical behavior');
  assert.strictEqual(hsfFallback.meta.holoindex_owner_query_required, true, 'HSF-006: semantic authority remains required');
  assert.strictEqual(hsfFallback.meta.holoindex_owner_query_ok, false, 'HSF-006: failed owner is never accepted');
  assert.strictEqual(hsfFallback.meta.no_holoindex_reindex_performed, true, 'HSF-006: failure path performs no reindex');
  assert.strictEqual(hsfFallback.meta.index_gap_detected, true, 'HSF-006: failed authority remains an explicit index gap');
} finally {
  cp.execFileSync = hsfOriginalExecFileSync;
  process.env.REDDOG_HOLO_RETRIEVAL_MODE = hsfOriginalMode;
  fs.rmSync(hsfOwnerRoot, { recursive: true, force: true });
}

// HSF-007: broad audits use one bounded, read-only expanded query. The original query and
// expansion strategy remain receipt-visible, and no indexing/direct-read flag is introduced.
const hsfExpansionPlan = semanticGroundingPolicy.buildEffectiveHoloQuery('Audit pfmall.', ['Audit pfmall.']);
assert.strictEqual(hsfExpansionPlan.original_query, 'Audit pfmall.', 'HSF-007: original query is preserved');
includes(hsfExpansionPlan.effective_query, 'architecture', 'HSF-007: broad audit query gains generic architecture vocabulary');
includes(hsfExpansionPlan.effective_query, 'tests', 'HSF-007: broad audit query gains generic verification vocabulary');
assert.strictEqual(hsfExpansionPlan.expansion_strategy, 'broad_audit_v1', 'HSF-007: expansion strategy is explicit');
const hsfExpandedOwner = {
  ok: true, bundle_ok: true, owner_attempts: 0, no_holoindex_reindex_performed: true,
  bundle: { task_retrieval: { code_hits: [], metadata: {
    retrieval_mode: 'lexical', embedding_backend: 'none', code_count: 0, wsp_count: 0
  } }, direct_read: { direct_read_fallback_used: false } }
};
try {
  process.env.REDDOG_HOLO_RETRIEVAL_MODE = 'lexical';
  const hsfExpanded = orchestrator.holoIndexOutput(root, 'Audit pfmall.', 18000,
    { baseResult: hsfExpandedOwner });
  assert.strictEqual(hsfExecCalls, 0, 'HSF-007: bounded owner bundle does not invoke raw Holo CLI');
  assert.strictEqual(hsfExpandedOwner.no_holoindex_reindex_performed, true, 'HSF-007: bounded owner result prohibits reindex');
  assert.strictEqual(hsfExpanded.meta.direct_read_fallback_used, false, 'HSF-007: semantic expansion invents no direct-read fallback');
  assert.strictEqual(hsfExpanded.meta.requested_retrieval_mode, 'lexical', 'HSF-007: requested diagnostic mode is receipt-visible');
  assert.strictEqual(hsfExpanded.meta.original_query, 'Audit pfmall.', 'HSF-007: meta preserves original query');
  assert.strictEqual(hsfExpanded.meta.expansion_strategy, 'broad_audit_v1', 'HSF-007: meta preserves expansion strategy');
} finally {
  process.env.REDDOG_HOLO_RETRIEVAL_MODE = hsfOriginalMode;
}

// REDDOG_REPO_DEEP_DIVE_DISCOVERY_PHASE1 (RDD-001..008): broad repository
// audits must derive real source targets and cannot pass on semantic prose alone.
const rddPrompt = 'Complete deep dive into the FoundUps-Agent repository, focusing on p.fMALL runtime architecture.';
const rddHostPrompt = 'Complete a deep dive into the FoundUps-Agent repository, focusing on '
  + 'p.fMALL runtime architecture. Apply WSP_97, cite direct file evidence, identify '
  + 'implemented versus missing behavior, and apply WSP_15 to the recommended next work.';
assert.strictEqual(orchestrator.isRepoDeepDiveRequest(rddPrompt), true, 'RDD-001: broad repository deep dive detected');
const rddAttentionPrompt = 'look at the codebase what needs attention?';
