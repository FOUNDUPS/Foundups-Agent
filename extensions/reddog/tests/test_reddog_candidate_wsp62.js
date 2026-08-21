'use strict';

const assert = require('assert');
const cp = require('child_process');
const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..', '..');
const candidateJavaScript = [
  'extensions/reddog/backend_compatibility_constants.js',
  'extensions/reddog/conversation_session_authority_source.js',
  'extensions/reddog/extension.js',
  'extensions/reddog/governed_git_context.js',
  'extensions/reddog/governed_git_executable.js',
  'extensions/reddog/governed_git_projection.js',
  'extensions/reddog/governed_git_readiness.js',
  'extensions/reddog/governed_git_repo_state.js',
  'extensions/reddog/governed_git_storage.js',
  'extensions/reddog/holoindex_bundle_projection.js',
  'extensions/reddog/holoindex_generation_bound_query.js',
  'extensions/reddog/holoindex_incident_repair.js',
  'extensions/reddog/holoindex_interpreter_provenance.js',
  'extensions/reddog/holoindex_owner_runtime.js',
  'extensions/reddog/start_operations_control.js',
  'extensions/reddog/start_operations_environment.js',
  'extensions/reddog/start_operations_extension_adapter.js',
  'extensions/reddog/tests/governed_git_authority_contracts.js',
  'extensions/reddog/tests/governed_git_executable_test_helpers.js',
  'extensions/reddog/tests/governed_git_projection_contracts.js',
  'extensions/reddog/tests/governed_git_projection_final_order_contracts.js',
  'extensions/reddog/tests/governed_git_projection_race_contracts.js',
  'extensions/reddog/tests/governed_git_ref_contracts.js',
  'extensions/reddog/tests/governed_git_storage_contracts.js',
  'extensions/reddog/tests/governed_git_test_helpers.js',
  'extensions/reddog/tests/test_bridge_python_environment.js',
  'extensions/reddog/tests/test_extension_contract_shards.js',
  'extensions/reddog/tests/test_governed_git_context_hardening.js',
  'extensions/reddog/tests/test_governed_git_executable.js',
  'extensions/reddog/tests/test_governed_git_production_scan.js',
  'extensions/reddog/tests/test_governed_git_environment.js',
  'extensions/reddog/tests/test_governed_git_ref_formats.js',
  'extensions/reddog/tests/test_holoindex_async_bridge.js',
  'extensions/reddog/tests/test_holoindex_incident_repair.js',
  'extensions/reddog/tests/reddog_package_surface_contract.js',
  'extensions/reddog/tests/reddog_test_plan.js',
  'extensions/reddog/tests/reddog_contract_execution.js',
  'extensions/reddog/tests/reddog_release_supervisor.js',
  'extensions/reddog/tests/reddog_release_worker.js',
  'extensions/reddog/tests/run_reddog_test_tier.js',
  'extensions/reddog/tests/start_operations_control_test_helpers.js',
  'extensions/reddog/tests/test_backend_compatibility_contract.js',
  'extensions/reddog/tests/test_reddog_release_supervisor.js',
  'extensions/reddog/tests/test_reddog_test_tiering.js',
  'extensions/reddog/tests/test_package_manifest.js',
  'extensions/reddog/tests/test_package_surface.js',
  'extensions/reddog/tests/test_reddog_candidate_wsp62.js',
  'extensions/reddog/tests/test_start_operations_control.js',
  'extensions/reddog/tests/verify_extension_contract.js',
  'extensions/reddog/tests/verify_fusion_panel_input_contract.js',
  'extensions/reddog/tests/contract_shards/verify_extension_contract.part01.js',
  'extensions/reddog/tests/contract_shards/verify_extension_contract.part02.js',
  'extensions/reddog/tests/contract_shards/verify_extension_contract.part03.js',
  'extensions/reddog/tests/contract_shards/verify_extension_contract.part09.js',
  'extensions/reddog/tests/contract_shards/verify_extension_contract.part12.js',
  'extensions/reddog/tests/contract_shards/verify_extension_contract.part13.js',
  'extensions/reddog/tests/contract_shards/verify_extension_contract.part14.js',
  'extensions/reddog/tests/contract_shards/verify_extension_contract.part17.js',
  'extensions/reddog/tests/contract_shards/verify_extension_contract.part18.js'
];
const candidateDocuments = [
  'extensions/reddog/INTERFACE.md',
  'extensions/reddog/README.md',
  'extensions/reddog/ROADMAP.md',
  'extensions/reddog/tests/README.md'
];

function source(relative) {
  return fs.readFileSync(path.join(repoRoot, relative), 'utf8');
}

function baseSource(relative) {
  try {
    return cp.execFileSync('git', ['show', `HEAD:${relative}`], {
      cwd: repoRoot, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']
    });
  } catch (_err) { return ''; }
}

function physicalLines(content) {
  return content.replace(/\r\n/g, '\n').replace(/\n$/, '').split('\n').length;
}

function canonicalLines(content) {
  return physicalLines(content);
}

function maskJavaScript(content) {
  let output = '';
  let quote = '';
  let escaped = false;
  let lineComment = false;
  let blockComment = false;
  for (let index = 0; index < content.length; index += 1) {
    const char = content[index];
    const next = content[index + 1];
    if (char === '\n') { output += '\n'; lineComment = false; continue; }
    if (lineComment) { output += ' '; continue; }
    if (blockComment) {
      if (char === '*' && next === '/') { output += '  '; index += 1; blockComment = false; }
      else output += ' ';
      continue;
    }
    if (quote) {
      output += ' ';
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === quote) quote = '';
      continue;
    }
    if (char === '/' && next === '/') { output += '  '; index += 1; lineComment = true; }
    else if (char === '/' && next === '*') { output += '  '; index += 1; blockComment = true; }
    else if ('\'"`'.includes(char)) { output += ' '; quote = char; }
    else output += char;
  }
  return output;
}

function closingBrace(masked, opening) {
  let depth = 0;
  for (let index = opening; index < masked.length; index += 1) {
    if (masked[index] === '{') depth += 1;
    else if (masked[index] === '}' && --depth === 0) return index;
  }
  return -1;
}

function lineNumber(content, offset) {
  return content.slice(0, offset).split('\n').length;
}

function functionSpans(content) {
  const masked = maskJavaScript(content);
  const starts = [];
  const declarations = /\bfunction\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{/g;
  const arrows = /=>\s*\{/g;
  for (const [pattern, named] of [[declarations, true], [arrows, false]]) {
    let match;
    while ((match = pattern.exec(masked))) {
      const opening = masked.indexOf('{', match.index);
      const closing = closingBrace(masked, opening);
      if (closing >= 0) starts.push([match.index, closing, named ? match[1] : '']);
    }
  }
  return starts.map(([start, end, name]) => ({
    name,
    start: lineNumber(content, start),
    lines: lineNumber(content, end) - lineNumber(content, start) + 1
  }));
}

function assertJavaScriptLimits(relative) {
  const content = source(relative);
  if (relative === 'extensions/reddog/extension.js') {
    assert(canonicalLines(content) <= 8400, 'extension.js exceeds its reduced ceiling');
    const named = functionSpans(content);
    const wire = named.find((span) => span.name === 'wireFusionWebview');
    const call = named.find((span) => span.name === 'callFusion');
    assert(wire && wire.lines <= 581, 'wireFusionWebview exceeds 581 lines');
    assert(call && call.lines <= 180, 'callFusion exceeds its inherited ceiling');
    return;
  }
  assert(physicalLines(content) <= 400,
    relative + ' exceeds the candidate JavaScript 400-line ceiling');
  const spans = functionSpans(content);
  const baseline = functionSpans(baseSource(relative));
  let arrowIndex = 0;
  for (const span of spans) {
    const prior = span.name
      ? baseline.find((item) => item.name === span.name)
      : baseline.filter((item) => !item.name)[arrowIndex++];
    assert(span.lines <= 30 || (prior && span.lines <= prior.lines),
      relative + ':' + span.start + ' creates/grows candidate function debt');
  }
}

function changedJavaScript() {
  const commands = [
    ['diff', '--name-only', 'HEAD', '--', 'extensions/reddog'],
    ['ls-files', '--others', '--exclude-standard', '--', 'extensions/reddog']
  ];
  const found = new Set();
  for (const args of commands) {
    const output = cp.execFileSync('git', args, {
      cwd: repoRoot, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']
    });
    for (const relative of output.split(/\r?\n/)) {
      if (/\.(?:js|ts)$/.test(relative)) found.add(relative.replace(/\\/g, '/'));
    }
  }
  return [...found].sort();
}

function assertDocumentLimits(relative) {
  assert(physicalLines(source(relative)) <= 1000,
    relative + ' exceeds the candidate documentation 1000-line ceiling');
}

assert.deepStrictEqual([...candidateJavaScript].sort(), changedJavaScript(),
  'candidate JavaScript audit list must equal the complete Git changed/new surface');
for (const relative of candidateJavaScript) assertJavaScriptLimits(relative);
for (const relative of candidateDocuments) assertDocumentLimits(relative);

console.log('RedDog candidate WSP 62 file/function size proof: PASS');
console.log('Backend runtime WSP 62 compliance is a separate repository gate.');
