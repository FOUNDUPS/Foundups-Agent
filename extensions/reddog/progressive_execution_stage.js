'use strict';

const AUDIT = 'audit';
const BOUNDED_EXECUTION = 'boundedExecution';
const PRODUCTION = 'production';
const SUPPORTED = new Set([AUDIT, BOUNDED_EXECUTION]);
const MUTATION_REQUEST = /\b(?:fix|implement|edit|write|create|delete|merge|publish|release|deploy|execute|run\s+(?:shell|command))\b/i;

function resolveStage(value) {
  const candidate = typeof value === 'string' ? value.trim() : '';
  return SUPPORTED.has(candidate) ? candidate : AUDIT;
}

function allowsActionPlanning(stage) {
  return resolveStage(stage) === BOUNDED_EXECUTION;
}

function isReadonlyAuditRequest(text, auditIntentDetected) {
  return auditIntentDetected === true && !MUTATION_REQUEST.test(String(text || ''));
}

function project(stage, runtimeGatePassed) {
  const configured = resolveStage(stage);
  return Object.freeze({
    configured_stage: configured,
    audit_dialogue_allowed: true,
    action_planning_ceiling_open: (
      configured === BOUNDED_EXECUTION && runtimeGatePassed === true
    ),
    production_stage_available: false,
    setting_grants_authority: false
  });
}

function runTraceLines(value) {
  const receipt = value && typeof value === 'object' ? value : project(AUDIT, false);
  return [
    '- progressive_execution_stage: ' + receipt.configured_stage,
    '- audit_dialogue_allowed: ' + (receipt.audit_dialogue_allowed === true ? 'true' : 'false'),
    '- action_planning_ceiling_open: ' + (receipt.action_planning_ceiling_open === true ? 'true' : 'false'),
    '- production_stage_available: false',
    '- stage_setting_grants_authority: false'
  ];
}

module.exports = {
  AUDIT,
  BOUNDED_EXECUTION,
  PRODUCTION,
  allowsActionPlanning,
  isReadonlyAuditRequest,
  project,
  resolveStage,
  runTraceLines
};
