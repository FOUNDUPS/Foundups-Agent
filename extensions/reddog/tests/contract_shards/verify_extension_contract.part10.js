const liveSignedReceiptChain = {
  decision: 'SIGNED_RECEIPT_CHAIN_ACCEPT',
  accepted: true,
  terminal_receipt_hash: 'sha256:terminal-live',
  no_execution_performed: true,
  no_reward_settlement_performed: true
};
const liveValveDecision = {
  valve_state: 'VALVE_OPEN_LIVE_ENQUEUE',
  decision_digest: 'sha256:valve-live',
  no_execution_performed: true,
  rejection_reasons: []
};
const liveRuntimeGate = { passed: true, rejection_reasons: [] };
const blockedLivePayload = orchestrator.buildOpenClawLiveEnqueueRuntimeBindingPayload(
  {},
  liveSelectionResult,
  { passed: false, rejection_reasons: ['fusion_panel_quorum_not_passed'] },
  {}
);
assert.strictEqual(blockedLivePayload.ok, false, 'failed runtime consumption gate blocks live enqueue payload');
assert(blockedLivePayload.rejection_reasons.includes('runtime_consumption_gate_not_passed'), 'live enqueue payload carries runtime gate rejection');
const missingLiveArtifacts = orchestrator.buildOpenClawLiveEnqueueRuntimeBindingPayload(
  {},
  liveSelectionResult,
  liveRuntimeGate,
  {}
);
assert.strictEqual(missingLiveArtifacts.ok, false, 'live enqueue payload requires structured artifacts');
assert(missingLiveArtifacts.rejection_reasons.includes('adapter_result_missing'), 'live enqueue payload requires adapter result');
assert(missingLiveArtifacts.rejection_reasons.includes('signed_receipt_chain_result_missing'), 'live enqueue payload requires signed receipt chain');
const livePayload = orchestrator.buildOpenClawLiveEnqueueRuntimeBindingPayload(
  {
    openclaw_adapter_result: liveAdapterResult,
    policy_gate_receipt: livePolicyReceipt,
    signed_receipt_chain_result: liveSignedReceiptChain,
    live_enqueue_valve_decision: liveValveDecision
  },
  liveSelectionResult,
  liveRuntimeGate,
  { enableConcreteWriter: false, seenLiveEnqueueKeys: new Set(['existing:key']) }
);
assert.strictEqual(livePayload.ok, true, 'valid live enqueue metadata builds bridge payload');
assert.strictEqual(livePayload.payload.enable_concrete_writer, false, 'bridge payload disables concrete writer');
assert.deepStrictEqual(livePayload.payload.seen_live_enqueue_keys, ['existing:key'], 'bridge payload carries idempotency keys');
const fakeLiveInvoke = orchestrator.invokeOpenClawLiveEnqueueRuntimeBindingBridge(
  null,
  {
    openclaw_adapter_result: liveAdapterResult,
    policy_gate_receipt: livePolicyReceipt,
    signed_receipt_chain_result: liveSignedReceiptChain,
    live_enqueue_valve_decision: liveValveDecision
  },
  liveSelectionResult,
  liveRuntimeGate,
  {
    enableConcreteWriter: false,
    invokeRunner: (payload) => {
      assert.strictEqual(payload.enable_concrete_writer, false, 'fake live enqueue runner sees disabled writer');
      return {
        decision: 'EXTENSION_LIVE_ENQUEUE_INVOKE_REJECT',
        rejection_reasons: ['REJECT_LIVE_ENQUEUE_WRITER_MISSING'],
        concrete_writer_enabled: false,
        openclaw_enqueue_performed: false,
        hermes_dispatch_performed: false,
        worktree_create_performed: false,
        task_execution_performed: false,
        file_edit_performed: false,
        pr_created: false,
        merge_performed: false,
        reward_settlement_performed: false
      };
    }
  }
);
assert.strictEqual(fakeLiveInvoke.decision, 'EXTENSION_OPENCLAW_LIVE_ENQUEUE_SKIPPED',
  'direct live enqueue call without process-local selector proof is skipped');
assert(fakeLiveInvoke.rejection_reasons.includes('selection_proof_missing'),
  'direct live enqueue call exposes the missing proof');
assert.strictEqual(fakeLiveInvoke.openclaw_enqueue_performed, false, 'fake live enqueue bridge performs no enqueue');
assert.strictEqual(fakeLiveInvoke.concrete_writer_enabled, false, 'fake live enqueue bridge keeps writer disabled');
const fakeLiveInvokeSection = orchestrator.buildOpenClawLiveEnqueueRuntimeBindingSection(fakeLiveInvoke);
includes(fakeLiveInvokeSection, '## OpenClaw Live Enqueue Runtime Binding', 'live enqueue section header');
includes(fakeLiveInvokeSection, 'concrete_writer_enabled: false [OBSERVED]', 'live enqueue section shows disabled writer');
includes(fakeLiveInvokeSection, 'openclaw_enqueue_performed: false [OBSERVED]', 'live enqueue section shows no enqueue');
const realLiveInvoke = JSON.parse(cp.execFileSync('python', ['-B', path.join(root, 'scripts', 'reddog_extension_live_enqueue_invoke_once.py')], {
  cwd: root,
  input: JSON.stringify(livePayload.payload),
  encoding: 'utf8',
  env: Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' }),
  maxBuffer: 262144
}));
assert.strictEqual(realLiveInvoke.decision, 'EXTENSION_LIVE_ENQUEUE_INVOKE_REJECT', 'one-shot live enqueue bridge rejects without concrete writer');
assert.strictEqual(realLiveInvoke.python_invocation_performed, true, 'one-shot live enqueue bridge marks Python invocation');
assert.strictEqual(realLiveInvoke.concrete_writer_enabled, false, 'one-shot live enqueue bridge keeps writer disabled');
assert.strictEqual(realLiveInvoke.openclaw_enqueue_performed, false, 'one-shot live enqueue bridge performs no enqueue');
assert(realLiveInvoke.rejection_reasons.includes('REJECT_AUTHORITATIVE_LIVE_ENQUEUE_ADMISSION_MISSING'), 'one-shot live enqueue bridge preserves admission-before-writer rejection');

// REDDOG_EXTENSION_GITHUB_PERMISSION_PROBE_RUNTIME_BRIDGE_PHASE1:
// extension obtains a read-only GitHub permission snapshot and feeds it to the work-order candidate.
const permissionProbePayload = orchestrator.buildGithubPermissionProbePayload({
  repoFullName: 'FOUNDUPS/Foundups-Agent',
  principalLogin: 'operator-012',
  allowMockBackend: true,
  mockBackend: {
    authenticated: true,
    login: 'operator-012',
    permission: 'write',
    default_branch: 'main',
    scopes: ['repo'],
    branch_protection_observed: 'true',
    source: 'mock'
  }
});
assert.strictEqual(permissionProbePayload.repo_full_name, 'FOUNDUPS/Foundups-Agent', 'permission probe payload carries repo');
assert.strictEqual(permissionProbePayload.principal_login, 'operator-012', 'permission probe payload carries principal for mock test');
assert.strictEqual(permissionProbePayload.allow_mock_backend, true, 'permission probe test payload can use injected mock backend');
const fakePermissionProbe = orchestrator.runGithubPermissionProbeBridge(null, {
  permissionProbeRunner: (payload) => {
    assert.strictEqual(payload.repo_full_name, 'FOUNDUPS/Foundups-Agent', 'fake permission runner receives repo');
    return {
      decision: 'GITHUB_PERMISSION_PROBE_OBSERVED',
      repo_permission_snapshot: {
        permission_level: 'write',
        captured_at: '2026-07-12T12:00:00Z',
        expires_at: '2026-07-12T12:05:00Z',
        source: 'mock',
        digest: 'sha256:' + 'c'.repeat(64),
        repo_full_name: 'FOUNDUPS/Foundups-Agent',
        principal_login: 'operator-012',
        principal_provider: 'github',
        can_read: true,
        can_write: true,
        can_admin: false,
        extension_probe_performed: true
      },
      probe_performed: true,
      permission_observed: true,
      permission: 'write',
      can_read: true,
      can_write: true,
      can_admin: false,
      source: 'mock',
      raw_secret_included: false,
      token_scopes_count: 1,
      rejection_reasons: []
    };
  }
});
assert.strictEqual(fakePermissionProbe.decision, 'GITHUB_PERMISSION_PROBE_OBSERVED', 'fake permission bridge observes write permission');
assert.strictEqual(fakePermissionProbe.python_invocation_performed, false, 'fake permission bridge does not invoke Python');
assert.strictEqual(fakePermissionProbe.no_repo_mutation_performed, true, 'fake permission bridge performs no repo mutation');
assert.strictEqual(fakePermissionProbe.no_execution_performed, true, 'fake permission bridge performs no execution');
assert.strictEqual(fakePermissionProbe.no_enqueue_performed, true, 'fake permission bridge performs no enqueue');
const fakePermissionSection = orchestrator.buildGithubPermissionProbeSection(fakePermissionProbe);
includes(fakePermissionSection, '## RedDog GitHub Permission Probe', 'permission probe section header');
includes(fakePermissionSection, 'permission: write [OBSERVED]', 'permission probe section shows permission');
includes(fakePermissionSection, 'no_repo_mutation_performed: true [OBSERVED]', 'permission probe section shows no repo mutation');
assert(!fakePermissionSection.includes('repo,read:org'), 'permission probe section must not print raw token scopes');

const realPermissionProbe = JSON.parse(cp.execFileSync('python', ['-B', path.join(root, 'scripts', 'reddog_github_permission_probe_once.py')], {
  cwd: root,
  input: JSON.stringify(permissionProbePayload),
  encoding: 'utf8',
  env: Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' }),
  maxBuffer: 262144
}));
assert.strictEqual(realPermissionProbe.decision, 'GITHUB_PERMISSION_PROBE_OBSERVED', 'one-shot permission bridge accepts mock read-only probe');
assert.strictEqual(realPermissionProbe.no_repo_mutation_performed, true, 'one-shot permission bridge performs no repo mutation');
assert.strictEqual(realPermissionProbe.no_execution_performed, true, 'one-shot permission bridge performs no execution');
assert.strictEqual(realPermissionProbe.repo_permission_snapshot.permission_level, 'write', 'one-shot permission bridge maps permission level');
assert.strictEqual(realPermissionProbe.repo_permission_snapshot.source, 'mock', 'one-shot permission bridge maps trusted source');
assert(realPermissionProbe.repo_permission_snapshot.expires_at, 'one-shot permission bridge must include expires_at for freshness binding');
assert.strictEqual(realPermissionProbe.repo_permission_snapshot.extension_probe_performed, true, 'one-shot permission bridge marks extension probe provenance');
assert(!JSON.stringify(realPermissionProbe).includes('ghp_'), 'one-shot permission bridge output must not leak token-looking strings');

const permissionObservedPreview = orchestrator.buildWreOperationalSpineDryRunPreview(
  'Fix a narrow RedDog slice',
  { tier: 'ULTRA' },
  handoffRec,
  {
    createdAt: '2026-07-12T12:00:00Z',
    repoPermissionSnapshot: fakePermissionProbe.repo_permission_snapshot,
    promptConstruction: {
      required_targets_authoritative_paths: ['extensions/reddog/extension.js']
    }
  }
);
assert.strictEqual(permissionObservedPreview.governed_work_order_runtime_emission.permission_binding.permission_truth_label, 'OBSERVED', 'fresh probed permission should be observed');
assert.strictEqual(permissionObservedPreview.governed_work_order_runtime_emission.permission_binding.probe_performed, true, 'permission bridge marks probe performed');
assert.strictEqual(permissionObservedPreview.governed_work_order_runtime_emission.permission_binding.no_live_probe_performed_by_extension, false, 'permission bridge clears no-live-probe flag');
assert.strictEqual(permissionObservedPreview.governed_work_order_runtime_emission.ready_for_wre_invocation, false, 'permission alone cannot make candidate ready');
assert(permissionObservedPreview.governed_work_order_runtime_emission.not_ready_reasons.includes('signed_work_authority_not_verified'), 'permission bridge leaves signed-authority gate closed');

const wrePreviewCopy = orchestrator.buildCopyMarkdown(
  {
    ok: true,
    content: '## Decision\nProceed with preview only.',
    review_packet: { task_classification: { tier: 'ULTRA' }, output_validation: { validated: true } },
    wre_operational_spine_dryrun_preview: spinePreview
  },
  'reddog_architect',
  'Repo context attached',
  [],
  null,
  'ultra',
  {
    substantive: true,
    handoffRecommendation: handoffRec,
    operatorWardrobeSelectionResult: fakeWardrobeSelection,
    githubPermissionProbeResult: fakePermissionProbe,
    wreSpineDryRunPreview: spinePreview
  }
);
includes(wrePreviewCopy, '## Governed Handoff Recommendation', 'WRE preview Copy MD keeps governed handoff section');
includes(wrePreviewCopy, '## RedDog Operator Wardrobe Selection', 'WRE preview Copy MD must include wardrobe selection section');
includes(wrePreviewCopy, '## RedDog GitHub Permission Probe', 'WRE preview Copy MD must include permission probe section');
includes(wrePreviewCopy, '## RedDog Governed Work Order Candidate', 'WRE preview Copy MD must include candidate section');
includes(wrePreviewCopy, '## WRE Operational Spine Dry-Run Preview', 'WRE preview Copy MD must include preview section');
includes(wrePreviewCopy, 'raw_work_focus_stored: false [OBSERVED]', 'WRE preview Copy MD must state raw focus is not stored');

const candidateSection = orchestrator.buildRedDogGovernedWorkOrderCandidateSection(spinePreview.governed_work_order_runtime_emission);
includes(candidateSection, 'permission_snapshot_source: extension_runtime_candidate [OBSERVED]', 'candidate section must show unverified permission source');
includes(candidateSection, 'permission_truth_label: NEEDS_VERIFICATION [OBSERVED]', 'candidate section must show permission truth label');
includes(candidateSection, 'no_live_probe_performed_by_extension: true [OBSERVED]', 'candidate section must state extension did not probe GitHub');
includes(candidateSection, 'no_signature_verification_performed_by_extension: true [OBSERVED]', 'candidate section must state extension did not verify crypto');
includes(candidateSection, 'ready_for_wre_invocation: false [OBSERVED]', 'candidate section must show not ready');
assert(!wrePreviewCopy.includes('OPENROUTER_API_KEY'), 'WRE preview Copy MD must not leak env key name');

const fixedAuthorityCreatedAt = '2026-07-12T12:00:00Z';
const freshPermissionSnapshot = {
  permission: 'write',
  checked_at: fixedAuthorityCreatedAt,
  expires_at: '2026-07-12T12:05:00Z',
  source: 'gh_cli',
  evidence_digest: 'sha256:' + 'a'.repeat(64)
};
const authoritySeed = orchestrator.buildRedDogGovernedWorkOrderCandidate(
  'Fix a narrow RedDog slice',
  {},
  handoffRec,
  {
    createdAt: fixedAuthorityCreatedAt,
    repoPermissionSnapshot: freshPermissionSnapshot,
    allowedPaths: ['extensions/reddog/**'],
    requiredTargets: ['extensions/reddog/extension.js']
  }
);
const authorityBound = orchestrator.buildRedDogGovernedWorkOrderCandidate(
  'Fix a narrow RedDog slice',
  {},
  handoffRec,
  {
    createdAt: fixedAuthorityCreatedAt,
    repoPermissionSnapshot: freshPermissionSnapshot,
    signatureVerificationResult: {
      accepted: true,
      reason_codes: [],
      work_order_id: authoritySeed.work_order.work_order_id,
      signature: 'must-not-leak'
    },
    explicitValveRequested: true,
    allowedPaths: ['extensions/reddog/**'],
    requiredTargets: ['extensions/reddog/extension.js']
  }
);
assert.strictEqual(authorityBound.permission_binding.permission_truth_label, 'OBSERVED', 'fresh trusted permission snapshot should be observed');
assert.strictEqual(authorityBound.signed_authority_binding.signed_authority_verified, true, 'accepted matching signature result should bind');
assert.strictEqual(authorityBound.ready_for_wre_invocation, true, 'candidate should become ready only after permission, signature, scope, and explicit valve');
assert.strictEqual(authorityBound.not_ready_reasons.length, 0, 'ready candidate must have no not-ready reasons');
const authorityBoundSection = orchestrator.buildRedDogGovernedWorkOrderCandidateSection(authorityBound);
assert(!authorityBoundSection.includes('must-not-leak'), 'candidate section must not leak raw signature material');

const skippedInvoke = orchestrator.invokeWreOperationalSpineExplicitValveBridge(null, spinePreview, {});
assert.strictEqual(skippedInvoke.decision, 'EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_SKIPPED', 'runtime wire must skip without explicit invoke metadata');
assert.strictEqual(skippedInvoke.python_invocation_performed, false, 'skipped runtime wire must not invoke Python');
assert(skippedInvoke.rejection_reasons.includes('selection_proof_missing'),
  'skipped runtime wire must reject before payload assembly without selector proof');
const skippedInvokeSection = orchestrator.buildWreOperationalSpineInvokeSection(skippedInvoke);
includes(skippedInvokeSection, '## WRE Operational Spine Runtime Wire', 'runtime wire section header');
includes(skippedInvokeSection, 'python_invocation_performed: false [OBSERVED]', 'runtime wire skipped section must show no Python invocation');

const readyPreview = Object.assign({}, spinePreview, {
  governed_work_order_candidate: authorityBound.work_order,
  governed_work_order_candidate_digest: authorityBound.work_order_digest,
  governed_work_order_runtime_emission: authorityBound,
  governed_work_order_authority_binding: {
    permission_binding: authorityBound.permission_binding,
    signed_authority_binding: authorityBound.signed_authority_binding,
    authority_binding_performed: true
  },
  governed_work_order_ready_for_invocation: true,
  governed_work_order_not_ready_reasons: []
});
const sovereignSelectionReceipt = {
  selected_wardrobe: 'wsp97_sovereign_execution',
  execution_plane: 'governed_execution_candidate',
  authority_boundary: 'sovereign_token_required',
  rejection_reasons: [],
  no_execution_performed: true,
  no_enqueue_performed: true
};
const readyInvokePayload = orchestrator.buildWreOperationalSpineInvokePayload(readyPreview, {
  explicitWreOperationalSpineRequested: true,
  selectionReceipt: sovereignSelectionReceipt,
  valveEnvironment: {
    valve_worktree_create_enabled: true,
    sovereign_worktree_token: 'must-not-leak-token'
  },
  signatureVerificationResult: {
    accepted: true,
    reason_codes: [],
    work_order_id: authorityBound.work_order.work_order_id,
    signature: 'must-not-leak-signature'
  }
});
assert.strictEqual(readyInvokePayload.ok, true, 'ready runtime wire payload should be buildable from supplied authority metadata');
assert.strictEqual(readyInvokePayload.payload.work_order.work_order_id, authorityBound.work_order.work_order_id, 'runtime wire payload must bind work_order_id');
assert.strictEqual(readyInvokePayload.payload.explicit_wre_operational_spine_requested, true, 'runtime wire payload must carry explicit invoke request');
assert.strictEqual(readyInvokePayload.payload.selection_receipt.selected_wardrobe, 'wsp97_sovereign_execution', 'runtime wire payload must carry sovereign wardrobe selection');
assert(!JSON.stringify(readyInvokePayload.payload.signature_verification_result).includes('must-not-leak-signature'), 'runtime wire payload must strip raw signature material');

const fakeInvoke = orchestrator.invokeWreOperationalSpineExplicitValveBridge(null, readyPreview, {
  explicitWreOperationalSpineRequested: true,
  selectionReceipt: sovereignSelectionReceipt,
  valveEnvironment: {
    valve_worktree_create_enabled: true,
    sovereign_worktree_token: 'must-not-leak-token'
  },
  signatureVerificationResult: {
    accepted: true,
    reason_codes: [],
    work_order_id: authorityBound.work_order.work_order_id,
    signature: 'must-not-leak-signature'
  },
  invokeRunner: (payload) => {
    assert.strictEqual(payload.work_order.work_order_id, authorityBound.work_order.work_order_id, 'fake runner receives bound work order');
    return {
      decision: 'EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_ACCEPT',
      python_invocation_performed: true,
      wre_spine_invoked: true,
      worktree_create_performed: true,
      task_execution_performed: false,
      file_edit_performed: false,
      pr_created: false,
      openclaw_enqueue_performed: false,
      hermes_dispatch_performed: false,
      merge_performed: false,
      reward_settlement_performed: false,
      main_checkout_untouched: true,
      rejection_reasons: []
    };
  }
});
assert.strictEqual(fakeInvoke.decision, 'EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_SKIPPED',
  'direct WRE call without process-local selector proof is skipped');
assert(fakeInvoke.rejection_reasons.includes('selection_proof_missing'),
  'direct WRE call exposes the missing proof');
assert.strictEqual(fakeInvoke.wre_spine_invoked, false, 'unproved WRE call cannot invoke the spine');
const fakeInvokeSection = orchestrator.buildWreOperationalSpineInvokeSection(fakeInvoke);
assert(!fakeInvokeSection.includes('must-not-leak'), 'runtime wire section must not leak sovereign token or signature');

const bridgeReject = JSON.parse(cp.execFileSync('python', ['-B', path.join(root, 'scripts', 'reddog_extension_wre_spine_invoke_once.py')], {
  cwd: root,
  input: '{}',
  encoding: 'utf8',
  env: Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' }),
  maxBuffer: 262144
}));
assert.strictEqual(bridgeReject.decision, 'EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_REJECT', 'one-shot bridge must reject empty payload');
assert.strictEqual(bridgeReject.python_invocation_performed, true, 'one-shot bridge must report Python invocation');

const signatureMismatch = orchestrator.buildRedDogGovernedWorkOrderCandidate(
  'Fix a narrow RedDog slice',
  {},
  handoffRec,
  {
    createdAt: fixedAuthorityCreatedAt,
    repoPermissionSnapshot: freshPermissionSnapshot,
    signatureVerificationResult: { accepted: true, reason_codes: [], work_order_id: 'rdog-wo-deadbeefdeadbeef' },
    explicitValveRequested: true,
    requiredTargets: ['extensions/reddog/extension.js']
  }
);
assert.strictEqual(signatureMismatch.ready_for_wre_invocation, false, 'signature work_order_id mismatch must block readiness');
assert(signatureMismatch.not_ready_reasons.includes('signed_work_authority_work_order_mismatch'), 'signature mismatch reason must be explicit');
