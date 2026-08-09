'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const stage = require('../progressive_execution_stage');

assert.strictEqual(stage.resolveStage(undefined), stage.AUDIT);
assert.strictEqual(stage.resolveStage('invalid'), stage.AUDIT);
assert.strictEqual(stage.resolveStage(stage.PRODUCTION), stage.AUDIT);
assert.strictEqual(stage.resolveStage(stage.BOUNDED_EXECUTION), stage.BOUNDED_EXECUTION);
assert.strictEqual(stage.allowsActionPlanning(stage.AUDIT), false);
assert.strictEqual(stage.allowsActionPlanning(stage.BOUNDED_EXECUTION), true);
assert.strictEqual(stage.isReadonlyAuditRequest(
  'Audit the FoundUps repository and cite direct file evidence.', true
), true);
assert.strictEqual(stage.isReadonlyAuditRequest(
  'Audit and fix the FoundUps repository.', true
), false);

const audit = stage.project(stage.AUDIT, true);
assert.strictEqual(audit.audit_dialogue_allowed, true);
assert.strictEqual(audit.action_planning_ceiling_open, false);
assert.strictEqual(audit.setting_grants_authority, false);
assert.strictEqual(audit.production_stage_available, false);

const runtimeBlocked = stage.project(stage.BOUNDED_EXECUTION, false);
assert.strictEqual(runtimeBlocked.action_planning_ceiling_open, false);
const bounded = stage.project(stage.BOUNDED_EXECUTION, true);
assert.strictEqual(bounded.action_planning_ceiling_open, true);
assert.strictEqual(bounded.setting_grants_authority, false);

const trace = stage.runTraceLines(bounded).join('\n');
assert(trace.includes('progressive_execution_stage: boundedExecution'));
assert(trace.includes('stage_setting_grants_authority: false'));

const extension = fs.readFileSync(path.join(__dirname, '..', 'extension.js'), 'utf8');
assert(extension.includes("reddogConfigValue('progressiveExecutionStage'"));
assert(extension.includes('progressiveExecutionStage.allowsActionPlanning'));
assert(extension.includes('runtimeConsumptionGate.passed === true'));
assert(extension.includes('result.review_packet.progressive_execution_stage'));
assert(extension.includes('actionStageEnabled && await blockIncompatibleBackend'));
assert(extension.includes('compatibility.passed !== true'));
assert(extension.includes('buildBackendCompatibilityAuditDegradedResult(state)'));
const askStart = extension.indexOf('function wireFusionWebview');
const askEnd = extension.indexOf('function killBridgeChild', askStart);
const askSource = extension.slice(askStart, askEnd);
const earlyCompatibility = askSource.indexOf('const compatibility = await currentBackendCompatibility()');
const boundedContextBuild = askSource.indexOf('buildBoundedRepoContext');
assert(earlyCompatibility >= 0 && boundedContextBuild > earlyCompatibility);
assert(askSource.includes('const auditDegraded = !actionStageEnabled && compatibility.passed !== true'));
assert(askSource.includes('const contextPacket = auditDegraded || localFastPath'));
const callFusionStart = extension.indexOf('async function callFusion(');
const spawnStart = extension.indexOf('const child = cp.spawn', callFusionStart);
const compatibilityReturn = extension.indexOf('buildBackendCompatibilityAuditDegradedResult(state)', callFusionStart);
assert(callFusionStart >= 0 && compatibilityReturn > callFusionStart && spawnStart > compatibilityReturn);
assert(extension.includes('actionStageEnabled && !recoveryContext && await startOperationsAdapter.handleMessage'));

const manifest = JSON.parse(
  fs.readFileSync(path.join(__dirname, '..', 'package.json'), 'utf8')
);
const config = manifest.contributes.configuration.properties[
  'reddog.progressiveExecutionStage'
];
assert.strictEqual(config.default, 'audit');
assert.deepStrictEqual(config.enum, ['audit', 'boundedExecution']);
assert(!config.enum.includes('production'));

console.log('progressive execution stage tests passed');
