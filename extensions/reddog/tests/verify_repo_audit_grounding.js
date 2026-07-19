'use strict';

const assert = require('assert');
const path = require('path');
const Module = require('module');

process.env.REDDOG_HOLO_RETRIEVAL_MODE = 'lexical';

const root = path.resolve(__dirname, '..', '..', '..');
const extDir = path.join(root, 'extensions', 'reddog');
const grounding = require(path.join(extDir, 'repo_audit_grounding.js'));

for (const alias of ['pfmall', 'p.fMALL', 'p-fmall', 'PFMALL']) {
  const intent = grounding.detectRepoAuditIntent('Audit the ' + alias + ' codebase');
  assert.strictEqual(intent.audit_intent, true);
  assert.strictEqual(intent.entity, 'pfmall');
}
assert.strictEqual(
  grounding.moduleHintForRepoAudit('Audit p.fMALL codebase', 'extensions/reddog'),
  'modules/foundups/pfmall',
  'grounded audit entity must override active-editor module hint'
);
assert.strictEqual(
  grounding.moduleHintForRepoAudit('Review extensions/reddog/extension.js for WSP_97', 'extensions/reddog'),
  'extensions/reddog',
  'path review is not a codebase/module audit'
);

const receipt = {
  applied: true,
  entity: 'pfmall',
  coverage: { verdict: 'PASS', reasons: [] },
  selected: [
    { path: 'modules/foundups/pfmall/api.py', category: 'implementation_source', digest: 'sha256:a', bytes: 10 },
    { path: 'modules/foundups/pfmall/tests/test_api.py', category: 'test', digest: 'sha256:b', bytes: 10 }
  ]
};
const bundle = {
  repo_audit_grounding: receipt,
  task_retrieval: { code_hits: [
    { location: receipt.selected[0].path, content: 'source', repo_audit_grounding: true },
    { location: receipt.selected[1].path, content: 'test', repo_audit_grounding: true }
  ] }
};
const projection = grounding.projectRepoAuditGrounding('Audit PFMALL module', bundle, []);
assert.strictEqual(projection.applied, true);
assert.strictEqual(projection.passed_before_context_pack, true);
assert.deepStrictEqual(projection.effective_repo_file_targets, receipt.selected.map((item) => item.path));

const contextPass = grounding.evaluateRepoAuditContext('Audit pfmall codebase', {
  repo_audit_projection: projection,
  required_targets_authoritative_paths: projection.effective_repo_file_targets,
  holoindex_scorecard: {
    required_targets_in_model_context: 2,
    required_targets_context_missing: []
  }
});
assert.strictEqual(contextPass.passed, true);
assert.strictEqual(contextPass.source_visible, true);
assert.strictEqual(contextPass.independent_visible, true);

const contextFail = grounding.evaluateRepoAuditContext('Audit pfmall codebase', {
  repo_audit_projection: projection,
  required_targets_authoritative_paths: [receipt.selected[0].path],
  holoindex_scorecard: {
    required_targets_in_model_context: 1,
    required_targets_context_missing: [receipt.selected[1].path]
  }
});
assert.strictEqual(contextFail.passed, false);
assert(contextFail.rejection_reasons.includes('repo_audit_independent_not_in_model_context'));
assert(contextFail.rejection_reasons.includes('repo_audit_context_non_vacuity_failed'));

assert.strictEqual(
  grounding.evaluateRepoAuditContext('Explain current architecture', {}).passed,
  true,
  'non-audit zero-target behavior remains unchanged'
);
assert(grounding.defensiveSecurityInstruction('reddog_architect').includes('identify, prevent, or remediate'));
assert(grounding.defensiveSecurityInstruction('wsp_gate_critic').includes('omit exploit details'));

const activeEditor = {
  document: {
    uri: { scheme: 'file', fsPath: path.join(extDir, 'extension.js') },
    languageId: 'javascript',
    getText: () => 'const activeEditorIsRedDog = true;'
  },
  selection: { isEmpty: true }
};
const vscodeMock = {
  window: { activeTextEditor: activeEditor, visibleTextEditors: [activeEditor] },
  workspace: {
    workspaceFolders: [{ uri: { fsPath: root } }],
    getConfiguration: () => ({ get: (_key, fallback) => fallback })
  },
  commands: {}, extensions: { getExtension: () => undefined }, env: {}, Uri: {}, ViewColumn: { Beside: 2 }
};
const vscodePath = path.join(extDir, 'node_modules', 'vscode', 'index.js');
require.cache[vscodePath] = { exports: vscodeMock, loaded: true, id: vscodePath };
const originalResolve = Module._resolveFilename;
Module._resolveFilename = function(request, parent, isMain, options) {
  if (request === 'vscode') return vscodePath;
  return originalResolve.call(this, request, parent, isMain, options);
};
const extension = require(path.join(extDir, 'extension.js'));
Module._resolveFilename = originalResolve;

const missingReceiptPreflight = extension.buildTypedGroundingPreflight(
  'Audit pfmall codebase',
  'wsp_holo',
  { holoindex_scorecard: { target_recall_ok: true, required_targets_missing: [] } }
);
assert.strictEqual(missingReceiptPreflight.passed, false);
assert(missingReceiptPreflight.rejection_reasons.includes('codebase_audit_evidence_incomplete'));
const missingReceiptBlocked = extension.buildGroundingPreflightBlockedResult(missingReceiptPreflight);
assert.strictEqual(missingReceiptBlocked.reason, 'codebase_audit_evidence_incomplete');
assert.strictEqual(missingReceiptBlocked.made_network_call, false);

const primaryPacket = {
  fusion_panel_quorum: { applied: true, passed: true, challenging_critics: ['critic-a'] },
  resolved_mode: 'foundups_fusion',
  lead_model: 'lead-a'
};
const primary = { ok: true, review_packet: primaryPacket, lead_model: 'lead-a', content: 'primary' };
const repair = {
  ok: true,
  mode: 'openrouter_single',
  lead_model: 'repair-a',
  review_packet: { fusion_panel_quorum: { passed: false }, resolved_mode: 'openrouter_single' },
  content: 'repair'
};
const merged = extension.mergeSuccessfulSchemaRepair(primary, repair, 'merged output', 'foundups_fusion');
assert.strictEqual(merged.review_packet, primaryPacket, 'schema repair must preserve exact primary review_packet');
assert.strictEqual(merged.content, 'merged output');
assert.strictEqual(merged.schema_repair_telemetry.mode, 'openrouter_single');
assert.strictEqual(
  extension.buildRuntimeConsumptionGate(merged, { validated: true }, 'foundups_fusion', true).passed,
  true,
  'primary passed quorum remains passed after valid repair'
);

const noPrimaryQuorum = extension.mergeSuccessfulSchemaRepair(
  { ok: true, review_packet: {}, content: 'primary' },
  { ok: true, review_packet: { fusion_panel_quorum: { passed: true } }, content: 'repair' },
  'merged output',
  'foundups_fusion'
);
const failedGate = extension.buildRuntimeConsumptionGate(
  noPrimaryQuorum, { validated: true }, 'foundups_fusion', true
);
assert.strictEqual(failedGate.passed, false);
assert(failedGate.rejection_reasons.includes('fusion_panel_quorum_not_passed'));

const actualPrompt = 'Audit p.fMALL codebase and recommend defensive repairs.';
const actualContext = extension.buildBoundedRepoContext('wsp_holo', actualPrompt);
assert(
  actualContext.repo_audit_grounding && actualContext.repo_audit_grounding.entity === 'pfmall',
  JSON.stringify({ quality: actualContext.quality, meta: actualContext.holoindex_meta })
);
assert.strictEqual(actualContext.repo_audit_grounding.holo_first, true);
assert.strictEqual(actualContext.repo_audit_grounding.coverage.verdict, 'PASS');
const selectedSource = actualContext.repo_audit_grounding.selected.find((item) => item.category === 'implementation_source');
const selectedIndependent = actualContext.repo_audit_grounding.selected.find((item) => item.category === 'test' || item.category === 'contract');
assert(selectedSource && actualContext.text.includes('### Required direct-read target: ' + selectedSource.path));
assert(selectedIndependent && actualContext.text.includes('### Required direct-read target: ' + selectedIndependent.path));
const actualPreflight = extension.buildTypedGroundingPreflight(actualPrompt, 'wsp_holo', actualContext);
assert.strictEqual(actualPreflight.repo_audit_grounding_applied, true);
assert.strictEqual(actualPreflight.repo_audit_grounding_passed, true);
assert.strictEqual(actualPreflight.passed, true);
assert(actualPreflight.repo_file_targets_count >= 2);

console.log('RedDog repo-audit grounding and repair provenance contracts: PASS');
