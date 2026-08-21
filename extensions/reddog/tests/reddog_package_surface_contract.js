'use strict';

const cp = require('child_process');
const fs = require('fs');
const path = require('path');

const extDir = path.resolve(__dirname, '..');
const MAX_PACKAGE_RAW_BYTES = 1024 * 1024;
const EXPECTED_RUNTIME_FILES = Object.freeze([
  'authoritative_work_state_query.js',
  'backend_compatibility_async.js',
  'backend_compatibility_constants.js',
  'backend_compatibility_filesystem.js',
  'backend_compatibility_manifest.js',
  'backend_compatibility_preflight.js',
  'backend_compatibility_render.js',
  'backend_compatibility_runtime_materializer.js',
  'backend_compatibility_worker.js',
  'continuation_prompt.js',
  'conversation_history_policy.js',
  'conversation_session_authority_source.js',
  'conversational_draft_policy.js',
  'daemon_diagnostic_analysis.js',
  'daemon_diagnostic_secret_filter.js',
  'extension.js',
  'foundup_target_phrase.js',
  'foundup_work_grounding.js',
  'foundup_work_runtime_binding.js',
  'fusion_progress_receipt.js',
  'governed_git_context.js',
  'governed_git_executable.js',
  'governed_git_projection.js',
  'governed_git_readiness.js',
  'governed_git_repo_state.js',
  'governed_git_storage.js',
  'grounded_target_continuity.js',
  'grounding_failure_dialogue.js',
  'holoindex_blocked_request_recovery.js',
  'holoindex_bundle_projection.js',
  'holoindex_evidence_boundary.js',
  'holoindex_generation_bound_query.js',
  'holoindex_incident_repair.js',
  'holoindex_interpreter_provenance.js',
  'holoindex_owner_fallback_bundle.js',
  'holoindex_owner_proof.js',
  'holoindex_owner_runtime.js',
  'json_schema_subset_validator.js',
  'local_diagnostic_router.js',
  'model_freshness_query.js',
  'model_runtime_binding_query.js',
  'operator_wardrobe_selection_proof.js',
  'orchestration_prompt_routes.js',
  'orchestration_prompt_trace.js',
  'principal_memex_disclosure_source.js',
  'progressive_execution_stage.js',
  'repo_audit_grounding.js',
  'repo_deep_dive_focus_policy.js',
  'resident_architect_session_contract.js',
  'runtime_health_query.js',
  'runtime_health_worker.js',
  'sealed_python_json_once.js',
  'semantic_grounding_policy.js',
  'start_operations_bridge.js',
  'start_operations_control.js',
  'start_operations_environment.js',
  'start_operations_extension_adapter.js',
  'start_operations_interpreter.js',
  'start_operations_python_bootstrap.py',
  'target_read_path_policy.js',
  'worker_prompt_contract.js'
]);
const EXPECTED_PACKAGE_FILES = Object.freeze([
  ...EXPECTED_RUNTIME_FILES, 'LICENSE', 'README.md', 'icon.png', 'package.json'
].sort());
const EXPECTED_IGNORE_RULES = Object.freeze([
  'tests/**', 'docs/**', '*.vsix', 'node_modules/**', '.vscode/**',
  'ModLog.md', 'ROADMAP.md', 'INTERFACE.md', 'HOLOINDEX.md',
  'wsp_62_exemptions.yaml', '**/__pycache__/**', '**/.pytest_cache/**',
  '**/.cache/**', '**/coverage/**', '**/.coverage*', '**/.nyc_output/**',
  '**/*.py[cod]', '**/*.log', '.env*', '**/.env*', '**/*.pem', '**/*.key',
  '**/*.pfx', '**/*.p12', '**/*.jks', '**/*.keystore', '.vscodeignore'
]);

function localDependencies(relative) {
  const source = fs.readFileSync(path.join(extDir, relative), 'utf8');
  return Array.from(source.matchAll(/require\(\s*['"](\.\.?\/[^'"]+)['"]\s*\)/g), (match) => {
    let target = path.posix.normalize(path.posix.join(path.posix.dirname(relative), match[1]));
    if (!path.posix.extname(target)) target += '.js';
    if (!fs.existsSync(path.join(extDir, target))) throw new Error(`missing runtime require: ${target}`);
    return target;
  });
}

function deriveRuntimeFiles() {
  const queue = ['extension.js', 'backend_compatibility_worker.js', 'runtime_health_worker.js'];
  const seen = new Set();
  while (queue.length) {
    const relative = queue.shift();
    if (seen.has(relative)) continue;
    seen.add(relative);
    queue.push(...localDependencies(relative));
  }
  seen.add('start_operations_python_bootstrap.py');
  return [...seen].sort();
}

function readIgnoreRules() {
  return fs.readFileSync(path.join(extDir, '.vscodeignore'), 'utf8')
    .replace(/\r\n/g, '\n').split('\n').map((line) => line.trim())
    .filter((line) => line && !line.startsWith('#'));
}

function packageSurfaceReceipt(files) {
  let rawBytes = 0;
  for (const relative of files) {
    const candidate = path.resolve(extDir, relative);
    const withinRoot = path.relative(extDir, candidate);
    if (!withinRoot || withinRoot.startsWith('..') || path.isAbsolute(withinRoot)) {
      throw new Error(`package path escapes extension root: ${relative}`);
    }
    const stat = fs.lstatSync(candidate);
    if (!stat.isFile() || stat.isSymbolicLink()) {
      throw new Error(`package entry is not a regular file: ${relative}`);
    }
    rawBytes += stat.size;
  }
  if (!Number.isSafeInteger(rawBytes) || rawBytes > MAX_PACKAGE_RAW_BYTES) {
    throw new Error(`package raw closure exceeds ${MAX_PACKAGE_RAW_BYTES} bytes`);
  }
  return Object.freeze({ schema_version: 'reddog_package_surface_receipt.v1',
    file_count: files.length, raw_bytes: rawBytes,
    raw_byte_cap: MAX_PACKAGE_RAW_BYTES, within_cap: true });
}

function vsceInvocation() {
  if (process.platform !== 'win32') return { executable: 'vsce', prefix: [] };
  for (const directory of String(process.env.PATH || '').split(path.delimiter)) {
    if (!directory || !fs.existsSync(path.join(directory, 'vsce.cmd'))) continue;
    const entrypoint = path.join(directory, 'node_modules', '@vscode', 'vsce', 'vsce');
    if (fs.existsSync(entrypoint)) return { executable: process.execPath, prefix: [entrypoint] };
  }
  throw new Error('installed vsce CLI not found on PATH');
}

function runVsceList() {
  const invocation = vsceInvocation();
  const result = cp.spawnSync(invocation.executable, [
    ...invocation.prefix, 'ls', '--no-dependencies'
  ], {
    cwd: extDir, encoding: 'utf8', shell: false, timeout: 60000, maxBuffer: 2 * 1024 * 1024
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`vsce ls failed: ${String(result.stderr).slice(0, 500)}`);
  return String(result.stdout).replace(/\r\n/g, '\n').trim().split('\n').filter(Boolean);
}

module.exports = Object.freeze({
  EXPECTED_IGNORE_RULES, EXPECTED_PACKAGE_FILES, EXPECTED_RUNTIME_FILES,
  MAX_PACKAGE_RAW_BYTES, deriveRuntimeFiles, extDir, packageSurfaceReceipt,
  readIgnoreRules, runVsceList
});
