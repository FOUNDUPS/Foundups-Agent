'use strict';

const cp = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const extDir = path.resolve(__dirname, '..');
const repoRoot = path.resolve(extDir, '..', '..');
const MAX_PACKAGE_RAW_BYTES = 1024 * 1024;
const EXPECTED_PACKAGE_EOL_RULES = Object.freeze([
  'extensions/reddog/*.js text eol=lf',
  'extensions/reddog/start_operations_python_bootstrap.py text eol=lf',
  'extensions/reddog/package.json text eol=lf',
  'extensions/reddog/README.md text eol=lf',
  'extensions/reddog/LICENSE text eol=lf',
  'extensions/reddog/icon.png -text'
]);
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
  'conversation_plane_policy.js',
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
  'webview_security.js',
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

function sha256(value) {
  return `sha256:${crypto.createHash('sha256').update(value).digest('hex')}`;
}

function classifyPackageMember(relative) {
  if (relative === 'icon.png') return 'binary';
  const validText = new Set(['.js', '.json', '.md', '.py', '.yaml', '']);
  if (!validText.has(path.posix.extname(relative))) {
    throw new Error(`RedDog package EOL file classification drift: ${relative}`);
  }
  return 'text';
}

function validatePackageMemberBytes(relative, bytes) {
  const kind = classifyPackageMember(relative);
  if (kind === 'text' && bytes.includes(0x0d)) {
    throw new Error(`RedDog package text member contains CR bytes: ${relative}`);
  }
  return kind;
}

function preflightPackageMembers(files, root) {
  const candidates = [];
  let rawBytes = 0;
  for (const relative of [...files].sort()) {
    const candidate = path.resolve(root, relative);
    const withinRoot = path.relative(root, candidate);
    if (!withinRoot || withinRoot.startsWith('..') || path.isAbsolute(withinRoot)) {
      throw new Error(`package path escapes extension root: ${relative}`);
    }
    const stat = fs.lstatSync(candidate);
    if (!stat.isFile() || stat.isSymbolicLink()) {
      throw new Error(`package entry is not a regular file: ${relative}`);
    }
    if (!Number.isSafeInteger(stat.size) || stat.size < 0 ||
        rawBytes > MAX_PACKAGE_RAW_BYTES - stat.size) {
      throw new Error(`package raw closure exceeds ${MAX_PACKAGE_RAW_BYTES} bytes`);
    }
    rawBytes += stat.size;
    candidates.push(Object.freeze({ relative, candidate, size: stat.size }));
  }
  return Object.freeze({ candidates: Object.freeze(candidates), raw_bytes: rawBytes });
}

function digestPackageMembers(files, root = extDir) {
  const preflight = preflightPackageMembers(files, root);
  const members = [];
  for (const entry of preflight.candidates) {
    const { relative, candidate, size } = entry;
    const bytes = fs.readFileSync(candidate);
    if (bytes.length !== size) {
      throw new Error(`package entry size changed during inspection: ${relative}`);
    }
    validatePackageMemberBytes(relative, bytes);
    members.push(Object.freeze({
      path: relative, raw_bytes: bytes.length, sha256: sha256(bytes)
    }));
  }
  return Object.freeze({
    members: Object.freeze(members), raw_bytes: preflight.raw_bytes,
    content_digest: sha256(Buffer.from(JSON.stringify(members), 'utf8'))
  });
}

function readEffectiveAttributes(files) {
  const repoPaths = files.map((relative) => `extensions/reddog/${relative}`);
  const result = cp.spawnSync('git', [
    'check-attr', '-z', 'text', 'eol', '--', ...repoPaths
  ], {
    cwd: repoRoot, encoding: 'utf8', shell: false, timeout: 30000,
    maxBuffer: 2 * 1024 * 1024
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`git check-attr failed: ${String(result.stderr).slice(0, 500)}`);
  }
  const tokens = String(result.stdout).split('\0');
  if (tokens[tokens.length - 1] === '') tokens.pop();
  if (tokens.length % 3 !== 0) throw new Error('malformed git check-attr output');
  const attributes = new Map();
  for (let index = 0; index < tokens.length; index += 3) {
    const [repoPath, attribute, value] = tokens.slice(index, index + 3);
    if (!repoPaths.includes(repoPath) || !['text', 'eol'].includes(attribute)) {
      throw new Error('unexpected git check-attr record');
    }
    if (!attributes.has(repoPath)) attributes.set(repoPath, new Map());
    const record = attributes.get(repoPath);
    if (record.has(attribute)) throw new Error('duplicate git check-attr record');
    record.set(attribute, value);
  }
  return attributes;
}

function validateEffectiveAttributes(files, attributes) {
  const effective = [];
  for (const relative of [...files].sort()) {
    const repoPath = `extensions/reddog/${relative}`;
    const record = attributes.get(repoPath);
    if (!record || !record.has('text') || !record.has('eol')) {
      throw new Error(`missing effective RedDog package attributes: ${relative}`);
    }
    const kind = classifyPackageMember(relative);
    const text = record.get('text');
    const eol = record.get('eol');
    if (kind === 'text' && (text !== 'set' || eol !== 'lf')) {
      throw new Error(`effective RedDog text attributes are not text/eol=lf: ${relative}`);
    }
    if (kind === 'binary' && (text !== 'unset' || eol !== 'unspecified')) {
      throw new Error(`effective RedDog binary attributes are not -text: ${relative}`);
    }
    effective.push(Object.freeze({ path: relative, kind, text, eol }));
  }
  return Object.freeze(effective);
}

function packageSurfaceReceipt(files) {
  const eol = packageLineEndingPolicy(files);
  const content = digestPackageMembers(files);
  const rawBytes = content.raw_bytes;
  return Object.freeze({ schema_version: 'reddog_package_surface_receipt.v2',
    file_count: files.length, raw_bytes: rawBytes,
    raw_byte_cap: MAX_PACKAGE_RAW_BYTES, within_cap: true,
    text_eol_policy: eol.schema_version, text_eol: eol.text_eol,
    text_file_count: eol.text_file_count, binary_file_count: eol.binary_file_count,
    eol_policy_digest: eol.policy_digest, content_digest: content.content_digest });
}

function packageLineEndingPolicy(files) {
  const lines = new Set(fs.readFileSync(path.join(repoRoot, '.gitattributes'), 'utf8')
    .replace(/\r\n/g, '\n').split('\n').map((line) => line.trim()).filter(Boolean));
  const missing = EXPECTED_PACKAGE_EOL_RULES.filter((rule) => !lines.has(rule));
  if (missing.length) throw new Error(`missing RedDog package EOL rules: ${missing.join(', ')}`);
  const binary = files.filter((relative) => classifyPackageMember(relative) === 'binary');
  const text = files.filter((relative) => classifyPackageMember(relative) === 'text');
  if (binary.length !== 1 || binary[0] !== 'icon.png') {
    throw new Error('RedDog package EOL file classification drift');
  }
  const effective = validateEffectiveAttributes(files, readEffectiveAttributes(files));
  const policyBody = Object.freeze({
    schema_version: 'reddog_package_eol_policy.v1',
    rules: [...EXPECTED_PACKAGE_EOL_RULES].sort(), effective
  });
  return Object.freeze({ schema_version: 'reddog_package_eol_policy.v1',
    text_eol: 'lf', text_file_count: text.length, binary_file_count: binary.length,
    policy_digest: sha256(Buffer.from(JSON.stringify(policyBody), 'utf8')) });
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
  EXPECTED_IGNORE_RULES, EXPECTED_PACKAGE_EOL_RULES, EXPECTED_PACKAGE_FILES,
  EXPECTED_RUNTIME_FILES,
  MAX_PACKAGE_RAW_BYTES, deriveRuntimeFiles, digestPackageMembers, extDir,
  packageSurfaceReceipt, packageLineEndingPolicy, readEffectiveAttributes,
  readIgnoreRules, repoRoot, runVsceList, validateEffectiveAttributes,
  validatePackageMemberBytes
});
