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
const disposedRecoveryPanel = { disposed: false, bridgeChild: { killed: false } };
const detachedRecoveryState = orchestrator.bridgeStateForRequest(disposedRecoveryPanel, { recoveryId: 'r' });
disposedRecoveryPanel.disposed = true;
assert.notStrictEqual(detachedRecoveryState, disposedRecoveryPanel, 'recovery bridge must detach from panel lifecycle');
assert.strictEqual(detachedRecoveryState.detachedRecovery, true, 'detached recovery marker missing');
assert.strictEqual(orchestrator.shouldAcceptBridgeCompletion(false, detachedRecoveryState), true, 'panel disposal must not suppress admitted recovery completion');
assert.strictEqual(orchestrator.bridgeStateForRequest(disposedRecoveryPanel, null), disposedRecoveryPanel, 'ordinary bridge must retain panel lifecycle');

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
includes(extensionJs, 'function buildRedDogGovernedWorkOrderCandidate', 'governed work-order candidate builder missing');
includes(extensionJs, 'function buildRedDogGovernedWorkOrderCandidateSection', 'governed work-order candidate section builder missing');
includes(extensionJs, 'function normalizePermissionSnapshotBinding', 'permission snapshot binding helper missing');
includes(extensionJs, 'function normalizeSignedAuthorityBinding', 'signed authority binding helper missing');
includes(extensionJs, 'function buildWreOperationalSpineDryRunPreview', 'WRE spine dry-run preview builder missing');
includes(extensionJs, 'function buildWreOperationalSpineDryRunPreviewSection', 'WRE spine dry-run preview section builder missing');
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

// REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_DRYRUN_WIRE_PHASE1:
// extension emits a typed dry-run preview only; it does NOT call the WRE spine or create a worktree.
const spinePreview = orchestrator.buildWreOperationalSpineDryRunPreview(
  'continue the WRE worker slice; OPENROUTER_API_KEY visible to bridge: yes; dry-run only',
  { tier: 'ULTRA' },
  handoffRec,
  {
    promptConstruction: {
      work_focus_digest: { hash: 'abc123' },
      wsp_prompt_digest: { hash: 'def456' },
      required_targets_authoritative_paths: [
        'modules/communication/moltbot_bridge/src/reddog_wre_operational_spine.py',
        'modules/communication/moltbot_bridge/tests/test_reddog_wre_operational_spine.py'
      ]
    },
    contextMode: 'wsp_holo_git_skillz'
  }
);
assert.strictEqual(spinePreview.slice_name, 'REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_DRYRUN_WIRE_PHASE1', 'WRE preview slice name');
assert.strictEqual(spinePreview.target, 'reddog_wre_operational_spine', 'WRE preview target');
assert.strictEqual(spinePreview.dry_run_only, true, 'WRE preview must be dry-run only');
assert.strictEqual(spinePreview.candidate_work_order_emitted, true, 'WRE preview emits typed candidate shape');
assert(spinePreview.governed_work_order_candidate, 'WRE preview must include governed work-order candidate');
assert(/^rdog-wo-[a-f0-9]{16}$/.test(spinePreview.governed_work_order_candidate.work_order_id), 'candidate work_order_id shape');
assert.strictEqual(spinePreview.governed_work_order_candidate.red_dog_instance_id, 'foundups-agent-0.4.101', 'candidate must bind extension version');
assert.strictEqual(spinePreview.governed_work_order_candidate.repo_permission_snapshot.source, 'extension_runtime_candidate', 'candidate must not forge permission source');
assert.strictEqual(spinePreview.governed_work_order_candidate.repo_permission_snapshot.permission_level, 'needs_verification', 'candidate must fail closed on permission');
assert.deepStrictEqual(spinePreview.governed_work_order_candidate.allowed_paths, [],
  'direct-read evidence must never derive mutation authority');
assert(spinePreview.governed_work_order_runtime_emission.not_ready_reasons.includes('allowed_paths_missing_or_unverified'),
  'evidence-only candidate must fail closed without an explicit mutation scope');
assert.strictEqual(spinePreview.governed_work_order_runtime_emission.runtime_emission_performed, true, 'candidate emission flag');
assert.strictEqual(spinePreview.governed_work_order_runtime_emission.authority_binding_performed, true, 'authority binding metadata must be emitted');
assert.strictEqual(spinePreview.governed_work_order_runtime_emission.permission_binding.permission_truth_label, 'NEEDS_VERIFICATION', 'missing permission snapshot remains unverified');
assert.strictEqual(spinePreview.governed_work_order_runtime_emission.signed_authority_binding.signed_authority_verified, false, 'missing signed authority remains unverified');
assert.strictEqual(spinePreview.governed_work_order_runtime_emission.ready_for_wre_invocation, false, 'candidate must not be invocation-ready without authority');
assert(spinePreview.governed_work_order_runtime_emission.not_ready_reasons.includes('fresh_github_permission_probe_missing'), 'candidate must require fresh permission probe');
assert(spinePreview.governed_work_order_runtime_emission.not_ready_reasons.includes('signed_work_authority_not_verified'), 'candidate must require signed authority');
assert(spinePreview.governed_work_order_runtime_emission.not_ready_reasons.includes('explicit_worktree_valve_not_requested'), 'candidate must require explicit valve request');
assert(/^sha256:[a-f0-9]{64}$/.test(spinePreview.governed_work_order_candidate_digest), 'candidate digest must be full SHA256');
assert.strictEqual(spinePreview.raw_work_focus_stored, false, 'WRE preview must not store raw work focus');
assert.strictEqual(spinePreview.python_invocation_performed, false, 'WRE preview must not invoke Python');
assert.strictEqual(spinePreview.wre_spine_invoked, false, 'WRE preview must not invoke the spine');
assert.strictEqual(spinePreview.worktree_create_performed, false, 'WRE preview must not create a worktree');
assert.strictEqual(spinePreview.task_execution_performed, false, 'WRE preview must not execute tasks');
assert.strictEqual(spinePreview.openclaw_enqueue_performed, false, 'WRE preview must not enqueue OpenClaw');
assert.strictEqual(spinePreview.hermes_dispatch_performed, false, 'WRE preview must not dispatch Hermes');
assert.strictEqual(spinePreview.required_future_valve, 'VALVE_OPEN_WORKTREE_CREATE', 'WRE preview requires future valve');
assert.strictEqual(spinePreview.required_human_gate, '012_sovereign', 'WRE preview keeps 012 gate');
assert(/^sha256:[a-f0-9]{64}$/.test(spinePreview.command_digest), 'WRE preview command_digest must be full SHA256');
assert(!spinePreview.command_redacted_summary.includes('OPENROUTER_API_KEY'), 'WRE preview summary must sanitize secret-adjacent env name');
includes(spinePreview.command_redacted_summary, 'key_env_present: true', 'WRE preview summary should carry safe key-presence fact');
const spinePreviewSection = orchestrator.buildWreOperationalSpineDryRunPreviewSection(spinePreview);
includes(spinePreviewSection, '## WRE Operational Spine Dry-Run Preview', 'WRE preview section header');
includes(spinePreviewSection, 'governed_work_order_authority_binding_performed: true [OBSERVED]', 'WRE preview section must show authority binding metadata');
includes(spinePreviewSection, 'governed_work_order_ready_for_invocation: false [OBSERVED]', 'WRE preview section must show candidate is not invocation-ready');
includes(spinePreviewSection, 'python_invocation_performed: false [OBSERVED]', 'WRE preview section must show no Python invocation');
includes(spinePreviewSection, 'worktree_create_performed: false [OBSERVED]', 'WRE preview section must show no worktree creation');
includes(spinePreviewSection, 'required_future_valve: VALVE_OPEN_WORKTREE_CREATE [OBSERVED]', 'WRE preview section must show valve');
assert(!/execFileSync\([^;]*reddog_wre_operational_spine\.py/s.test(extensionJs), 'extension must not execFileSync the WRE operational spine directly');
includes(extensionJs, "scripts/reddog_extension_wre_spine_invoke_once.py", 'runtime wire must use one-shot explicit invoke bridge');
includes(extensionJs, "scripts/reddog_operator_wardrobe_selection_once.py", 'operator wardrobe bridge must use one-shot selection script');
includes(extensionJs, "scripts/reddog_github_permission_probe_once.py", 'GitHub permission bridge must use one-shot permission probe script');
includes(extensionJs, "result.reason !== 'redaction_blocked'", 'blocked-local packets must not receive WRE dry-run preview');

// REDDOG_EXTENSION_OPERATOR_WARDROBE_SELECTION_RUNTIME_BRIDGE_PHASE1:
// extension obtains a deterministic wardrobe-selection receipt and feeds it to the runtime wire.
assert.strictEqual(orchestrator.inferWardrobeAuthorityRequest('Please merge PR #123', handoffRec), 'merge', 'wardrobe inference detects merge authority');
assert.strictEqual(orchestrator.inferWardrobeAuthorityRequest('Run pytest in a governed worktree', handoffRec), 'worktree_write', 'wardrobe inference detects worktree/shell authority');
assert.strictEqual(orchestrator.inferWardrobeAuthorityRequest('Proceed with live enqueue only', handoffRec), 'live_enqueue', 'wardrobe inference detects live enqueue');
assert.strictEqual(orchestrator.inferWardrobeAuthorityRequest('Spawn workers for recursive worker orchestration', handoffRec), 'worker_orchestration', 'wardrobe inference detects recursive worker orchestration');
const wardrobePayload = orchestrator.buildWardrobeSelectionPayload(
  'Run governed worktree worker',
  {
    holoindex_query: 'operator wardrobe query',
    holoindex_status: 'bundle_json_ok',
    index_gap_detected: false,
    code_hits_count: 3,
    wsp_hits: 2,
    skill_hits: 1,
    direct_read_fallback_used: true,
    target_recall_ok: true
  },
  {
    required_targets_authoritative_paths: [
      'extensions/reddog/extension.js',
      'scripts/reddog_operator_wardrobe_selection_once.py'
    ]
  },
  handoffRec,
  { authorityRequest: 'worktree_write', laneRefs: ['judgment'], continuationPacketDigest: 'sha256:' + 'b'.repeat(64) }
);
assert.strictEqual(wardrobePayload.authority_request, 'worktree_write', 'wardrobe payload carries authority request');
assert.deepStrictEqual(wardrobePayload.required_targets, [
  'extensions/reddog/extension.js',
  'scripts/reddog_operator_wardrobe_selection_once.py'
], 'wardrobe payload carries required targets');
assert.strictEqual(wardrobePayload.holoindex_evidence.holoindex_status, 'bundle_json_ok', 'wardrobe payload carries HoloIndex status');
assert.strictEqual(wardrobePayload.holoindex_evidence.direct_read_fallback_used, true, 'wardrobe payload carries direct-read status');
assert.strictEqual(wardrobePayload.target_recall_ok, true, 'wardrobe payload carries target recall');
assert.strictEqual(wardrobePayload.grounding_preflight.applied, false, 'wardrobe payload carries default grounding preflight state');
const groundedWardrobePayload = orchestrator.buildWardrobeSelectionPayload(
  'Implement a scoped RedDog slice',
  {
    holoindex_status: 'bundle_json_ok',
    index_gap_detected: false,
    target_recall_ok: true,
    grounding_preflight_applied: true,
    grounding_preflight_passed: true,
    grounding_preflight_rejection_reasons: [],
    repo_file_targets_count: 1,
    semantic_targets_count: 0,
    external_research_targets_count: 0,
    quoted_reference_blocks_count: 0
  },
  { required_targets_authoritative_paths: ['extensions/reddog/extension.js'] },
  handoffRec,
  { authorityRequest: 'draft_pr' }
);
assert.strictEqual(groundedWardrobePayload.grounding_preflight.applied, true, 'wardrobe payload carries applied grounding preflight');
assert.strictEqual(groundedWardrobePayload.grounding_preflight.passed, true, 'wardrobe payload carries passed grounding preflight');
assert.strictEqual(groundedWardrobePayload.grounding_preflight.repo_file_targets_count, 1, 'wardrobe payload carries grounding target counts');
let failedGroundingRunnerCalled = false;
const failedGroundingWardrobe = orchestrator.runOperatorWardrobeSelectionBridge(
  null,
  'Implement with ungrounded external research',
  {
    holoindex_status: 'bundle_json_ok',
    index_gap_detected: false,
    target_recall_ok: false,
    grounding_preflight_applied: true,
    grounding_preflight_passed: false,
    grounding_preflight_rejection_reasons: ['external_research_retrieval_not_implemented'],
    repo_file_targets_count: 0,
    semantic_targets_count: 0,
    external_research_targets_count: 1,
    quoted_reference_blocks_count: 0
  },
  { required_targets_authoritative_paths: [] },
  handoffRec,
  {
    selectionRunner: () => {
      failedGroundingRunnerCalled = true;
      return { decision: 'WARDROBE_SELECTION_ACCEPT' };
    }
  }
);
assert.strictEqual(failedGroundingRunnerCalled, false, 'failed grounding must not invoke wardrobe selection runner');
assert.strictEqual(failedGroundingWardrobe.decision, 'WARDROBE_SELECTION_REJECT', 'failed grounding rejects wardrobe selection');
assert.strictEqual(failedGroundingWardrobe.python_invocation_performed, false, 'failed grounding must not invoke Python wardrobe bridge');
assert.deepStrictEqual(failedGroundingWardrobe.rejection_reasons, ['grounding_preflight_not_passed'], 'failed grounding carries stable rejection reason');
const fakeWardrobeSelection = orchestrator.runOperatorWardrobeSelectionBridge(
  null,
  'Run governed worktree worker',
  { holoindex_status: 'bundle_json_ok', index_gap_detected: false },
  { required_targets_authoritative_paths: ['extensions/reddog/extension.js'] },
  handoffRec,
  {
    authorityRequest: 'worktree_write',
    selectionRunner: (payload) => {
      assert.strictEqual(payload.authority_request, 'worktree_write', 'fake selection runner receives inferred authority request');
      return {
        decision: 'WARDROBE_SELECTION_ACCEPT',
        receipt: {
          selection_id: 'fake-selection',
          selected_wardrobe: 'wsp97_sovereign_execution',
          execution_plane: 'governed_execution_candidate',
          authority_boundary: 'sovereign_token_required',
          selected_context_mode: 'wsp_holo_git_skillz',
          selected_model_mode: 'foundups_fusion',
          selected_effort: 'ultra',
          wre_required: true,
          index_gap_detected: false,
          direct_read_required: true,
          grounding_preflight_applied: true,
          grounding_preflight_passed: true,
          rejection_reasons: [],
          no_execution_performed: true,
          no_enqueue_performed: true
        }
      };
    }
  }
);
assert.strictEqual(fakeWardrobeSelection.decision, 'WARDROBE_SELECTION_ACCEPT', 'fake wardrobe bridge accepts');
assert.strictEqual(fakeWardrobeSelection.python_invocation_performed, false, 'fake wardrobe bridge does not invoke Python');
assert.strictEqual(fakeWardrobeSelection.no_execution_performed, true, 'fake wardrobe bridge performs no execution');
assert.strictEqual(fakeWardrobeSelection.no_enqueue_performed, true, 'fake wardrobe bridge performs no enqueue');
assert.strictEqual(fakeWardrobeSelection.receipt.authority_boundary, 'sovereign_token_required', 'fake wardrobe receipt requires sovereign boundary');
assert.strictEqual(testWardrobeProof.isAccepted({
  decision: 'WARDROBE_SELECTION_REJECT', receipt: null,
  no_execution_performed: true, no_enqueue_performed: true
}), false, 'rejected wardrobe selection cannot admit resident submission');
assert.strictEqual(testWardrobeProof.isAccepted({
  decision: 'WARDROBE_SELECTION_ACCEPT', receipt: null,
  no_execution_performed: true, no_enqueue_performed: true
}), false, 'receipt-less wardrobe acceptance cannot admit resident submission');
assert.strictEqual(testWardrobeProof.isAccepted({
  decision: 'WARDROBE_SELECTION_ACCEPT', receipt: {},
  no_execution_performed: true, no_enqueue_performed: true
}), false, 'empty wardrobe receipts cannot admit resident submission');
includes(extensionJs,
  'wardrobeSelectionResult: operatorWardrobeSelectionResult,',
  'resident submission must consume the receipt-bearing wardrobe admission result');
const fakeWardrobeSection = orchestrator.buildOperatorWardrobeSelectionSection(fakeWardrobeSelection);
includes(fakeWardrobeSection, '## RedDog Operator Wardrobe Selection', 'wardrobe selection section header');
includes(fakeWardrobeSection, 'selected_wardrobe: wsp97_sovereign_execution [OBSERVED]', 'wardrobe selection section shows selected wardrobe');
includes(fakeWardrobeSection, 'no_execution_performed: true [OBSERVED]', 'wardrobe selection section shows no execution');

const realWardrobeSelection = JSON.parse(cp.execFileSync('python', ['-B', path.join(root, 'scripts', 'reddog_operator_wardrobe_selection_once.py')], {
  cwd: root, input: JSON.stringify(wardrobePayload), encoding: 'utf8',
  env: Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' }),
  maxBuffer: 262144
}));
assert.strictEqual(realWardrobeSelection.decision, 'WARDROBE_SELECTION_ACCEPT', 'one-shot wardrobe bridge must accept governed worktree request');
assert.strictEqual(realWardrobeSelection.no_execution_performed, true, 'one-shot wardrobe bridge performs no execution');
assert.strictEqual(realWardrobeSelection.no_enqueue_performed, true, 'one-shot wardrobe bridge performs no enqueue');
assert.strictEqual(realWardrobeSelection.receipt.selected_wardrobe, 'wsp97_sovereign_execution', 'one-shot wardrobe bridge selects sovereign wardrobe');
assert.strictEqual(realWardrobeSelection.receipt.authority_boundary, 'sovereign_token_required', 'one-shot wardrobe bridge preserves sovereign boundary');
assert.strictEqual(realWardrobeSelection.receipt.wre_required, true, 'one-shot wardrobe bridge marks WRE required for worktree authority');
testWardrobeSourceProof.observe(realWardrobeSelection);
testWardrobeProof.verifyAndObserve(wardrobePayload, realWardrobeSelection);
assert.strictEqual(testWardrobeProof.isAccepted(realWardrobeSelection), true,
  'canonical receipt-bearing wardrobe selection admits resident submission');
const unsafeWardrobeReceipt = JSON.parse(JSON.stringify(realWardrobeSelection));
unsafeWardrobeReceipt.receipt.no_execution_performed = false;
unsafeWardrobeReceipt.receipt.no_enqueue_performed = false;
unsafeWardrobeReceipt.receipt.rejection_reasons = ['unsafe'];
assert.strictEqual(testWardrobeProof.isAccepted(unsafeWardrobeReceipt), false,
  'receipt-level side effects or rejection must block resident submission');
const extendedWardrobeReceipt = JSON.parse(JSON.stringify(realWardrobeSelection));
extendedWardrobeReceipt.receipt.attacker_extra = true;
assert.strictEqual(testWardrobeProof.isAccepted(extendedWardrobeReceipt), false,
  'unknown wardrobe receipt fields fail closed');
const recomputedWardrobeReceipt = JSON.parse(JSON.stringify(realWardrobeSelection));
recomputedWardrobeReceipt.receipt.foundup_id = 'attacker-selected';
recomputedWardrobeReceipt.receipt.selection_id = require('crypto').createHash('sha256').update(
  JSON.stringify({ attacker: true }), 'utf8'
).digest('hex');
assert.strictEqual(testWardrobeProof.verifyAndObserve(wardrobePayload, recomputedWardrobeReceipt), recomputedWardrobeReceipt);
assert.strictEqual(testWardrobeProof.isAccepted(recomputedWardrobeReceipt), false,
  'recomputed receipt without sealed source proof cannot acquire admission');

// REDDOG_EXTENSION_TO_OPENCLAW_LIVE_ENQUEUE_RUNTIME_BINDING_PHASE1:
// extension may reach the explicit live-enqueue invoke guard only after runtime gating,
// with structured artifacts and the concrete writer disabled in this slice.
includes(extensionJs, "scripts/reddog_extension_live_enqueue_invoke_once.py", 'live enqueue runtime binding must use one-shot invoke bridge');
includes(extensionJs, "operatorWardrobeSelectionResult.authority_request === 'live_enqueue'", 'live enqueue binding must require live_enqueue authority request');
includes(extensionJs, 'enableConcreteWriter: false', 'live enqueue binding must disable concrete writer from extension runtime');
includes(extensionJs, 'openclaw_live_enqueue_runtime_binding_result', 'live enqueue binding result must be attached to review packet');
const liveBindingFunctionStart = extensionJs.indexOf('function buildOpenClawLiveEnqueueRuntimeBindingPayload');
const liveBindingFunctionEnd = extensionJs.indexOf('function buildOpenClawLiveEnqueueRuntimeBindingResult');
assert(liveBindingFunctionStart > 0 && liveBindingFunctionEnd > liveBindingFunctionStart, 'live enqueue payload builder must exist');
const liveBindingPayloadBuilder = extensionJs.slice(liveBindingFunctionStart, liveBindingFunctionEnd);
assert(!liveBindingPayloadBuilder.includes('result.content'), 'live enqueue binding must not mine model output prose for runtime artifacts');

const liveSelectionReceipt = {
  selected_wardrobe: 'wsp97_sovereign_execution',
  execution_plane: 'governed_execution_candidate',
  authority_boundary: 'signed_valve_required',
  rejection_reasons: [],
  no_execution_performed: true,
  no_enqueue_performed: true
};
const liveSelectionResult = {
  authority_request: 'live_enqueue',
  receipt: liveSelectionReceipt
};
const liveAdapterResult = {
  decision: 'ADAPTER_DRYRUN_ACCEPT',
  work_order_id: 'wo-live-extension-001',
  proposed_intake: {
    target_type: 'foundup_job',
    proposed_job_id: 'reddog-fj-live-extension-001',
    proposed_task_id: null,
    work_order_id: 'wo-live-extension-001',
    operation: 'feature_slice',
    requested_action: 'validate_foundup',
    repo_scope: 'FOUNDUPS/Foundups-Agent',
    allowed_paths: ['modules/communication/moltbot_bridge/**'],
    denied_paths: ['.env'],
    required_tests: ['modules/communication/moltbot_bridge/tests/test_reddog_openclaw_live_enqueue.py'],
    evidence_refs: ['policy_gate:sha256:policy-live'],
    no_enqueue_performed: true,
    no_execution_performed: true
  },
  adapter_receipt: {
    adapter_receipt_digest: 'sha256:adapter-live',
    target_type: 'foundup_job',
    work_order_id: 'wo-live-extension-001',
    rejection_reasons: []
  },
  no_enqueue_performed: true,
  no_execution_performed: true
};
const livePolicyReceipt = {
  decision: 'POLICY_ACCEPT',
  receipt_digest: 'sha256:policy-live',
  signature_gate_status: 'SIGNATURE_GATE_ACCEPTED',
  signature_gate_digest: 'sha256:signed-live',
  no_execution_performed: true
};
