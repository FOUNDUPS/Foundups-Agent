'use strict';

const cp = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const ENTITY_IDS = new Set(['trade', 'antifafm_001', 'agent_market']);
const FIXED_EVIDENCE = [
  'modules/foundups/foundup_registry.json',
  'modules/foundups/foundup_registry.schema.json',
  'modules/communication/moltbot_bridge/skillz/reddog_operations/SKILLz.md',
  'modules/infrastructure/wre_core/skillz/skills_registry_v2.json'
];
const MODULE_EVIDENCE = [
  'README.md', 'INTERFACE.md', 'ROADMAP.md', 'ModLog.md', 'tests/TestModLog.md'
];

function invalidFixturePath() {
  throw new Error('foundup_fixture_path_invalid');
}

function exactRelativeParts(relativePath) {
  if (typeof relativePath !== 'string' || !relativePath
    || relativePath.normalize('NFC') !== relativePath || relativePath.includes('\\')
    || relativePath.includes(':') || relativePath.includes('\0')
    || path.posix.isAbsolute(relativePath) || path.posix.normalize(relativePath) !== relativePath) {
    return invalidFixturePath();
  }
  const parts = relativePath.split('/');
  if (parts.some((part) => !part || part === '.' || part === '..')) return invalidFixturePath();
  return parts;
}

function inspectComponents(canonicalRoot, parts, mustExist) {
  let current = canonicalRoot;
  for (let index = 0; index < parts.length; index += 1) {
    current = path.join(current, parts[index]);
    let metadata;
    try { metadata = fs.lstatSync(current); }
    catch (error) {
      if (!mustExist && error && error.code === 'ENOENT') break;
      throw error;
    }
    if (metadata.isSymbolicLink()) return invalidFixturePath();
    if (index < parts.length - 1 && !metadata.isDirectory()) return invalidFixturePath();
    if (index === parts.length - 1 && !metadata.isFile()) return invalidFixturePath();
  }
}

function confinedFile(root, relativePath, mustExist) {
  const parts = exactRelativeParts(relativePath);
  const canonicalRoot = fs.realpathSync(root);
  const candidate = path.resolve(canonicalRoot, ...parts);
  const relative = path.relative(canonicalRoot, candidate);
  if (!relative || relative.startsWith('..' + path.sep) || path.isAbsolute(relative)) {
    return invalidFixturePath();
  }
  inspectComponents(canonicalRoot, parts, mustExist);
  if (mustExist && !fs.lstatSync(candidate).isFile()) return invalidFixturePath();
  return candidate;
}

function ensureConfinedParent(root, relativePath) {
  const target = confinedFile(root, relativePath, false);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  return confinedFile(root, relativePath, false);
}

function copyEvidence(sourceRoot, targetRoot, relativePath, required) {
  const source = confinedFile(sourceRoot, relativePath, required === true);
  if (required !== true) {
    try { confinedFile(sourceRoot, relativePath, true); }
    catch (error) {
      if (error && error.code === 'ENOENT') return;
      throw error;
    }
  }
  const target = ensureConfinedParent(targetRoot, relativePath);
  fs.copyFileSync(source, target);
  confinedFile(targetRoot, relativePath, true);
}

function copyCanonicalEvidence(sourceRoot, targetRoot) {
  for (const relativePath of FIXED_EVIDENCE) copyEvidence(sourceRoot, targetRoot, relativePath, true);
  const registry = JSON.parse(fs.readFileSync(
    confinedFile(sourceRoot, 'modules/foundups/foundup_registry.json', true), 'utf8'
  ));
  for (const entity of registry.entities.filter((item) => ENTITY_IDS.has(item.foundup_id))) {
    if (typeof entity.module_path === 'string' && entity.module_path) {
      ensureConfinedParent(targetRoot, entity.module_path + '/.reddog-fixture-placeholder');
      for (const suffix of MODULE_EVIDENCE) {
        copyEvidence(sourceRoot, targetRoot, entity.module_path + '/' + suffix, false);
      }
    }
    if (typeof entity.manifest_path === 'string' && entity.manifest_path) {
      copyEvidence(sourceRoot, targetRoot, entity.manifest_path, true);
    }
  }
}

function initializeRepository(repoRoot) {
  const hookSentinel = ensureConfinedParent(
    repoRoot, '.reddog-test-hooks/.reddog-fixture-placeholder'
  );
  const hooksPath = path.dirname(hookSentinel);
  const run = (args) => cp.execFileSync(
    'git', ['-c', 'core.hooksPath=' + hooksPath].concat(args), { cwd: repoRoot }
  );
  run(['init', '-q']);
  run(['config', 'core.autocrlf', 'false']);
  run(['add', '.']);
  run([
    '-c', 'commit.gpgsign=false',
    '-c', 'user.name=RedDog Test', '-c', 'user.email=reddog@example.invalid',
    'commit', '-qm', 'canonical FoundUp evidence fixture'
  ]);
}

function evidenceHits(repoRoot, typedTargets) {
  const candidates = Array.isArray(typedTargets && typedTargets.repo_file_targets)
    ? typedTargets.repo_file_targets : [];
  return candidates.map((relativePath) => {
    const source = confinedFile(repoRoot, relativePath, true);
    return {
      location: relativePath,
      need: 'governed direct-read target',
      content: fs.readFileSync(source, 'utf8').slice(0, 4096),
      direct_read: true
    };
  });
}

function baseResultFor(repoRoot, typedTargets) {
  const hits = evidenceHits(repoRoot, typedTargets);
  const paths = hits.map((hit) => hit.location);
  const bytes = hits.reduce((total, hit) => total + Buffer.byteLength(hit.content, 'utf8'), 0);
  const metadata = {
    retrieval_mode: 'lexical', embedding_backend: 'none',
    code_count: hits.length, wsp_count: 0, no_holoindex_reindex_performed: true
  };
  const directRead = {
    direct_read_fallback_used: true, direct_read_paths: paths,
    direct_read_rejected: [], direct_read_bytes: bytes, direct_read_truncated: []
  };
  return {
    ok: true,
    bundle_ok: true,
    owner_attempts: 0,
    no_holoindex_reindex_performed: true,
    bundle: {
      task_retrieval: { code_hits: hits, wsp_hits: [], metadata },
      direct_read: directRead
    }
  };
}

function create(sourceRoot, vscodeMock) {
  const workspaceUri = vscodeMock.workspace.workspaceFolders[0].uri;
  const originalRoot = workspaceUri.fsPath;
  const repoRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reddog-foundup-integration-'));
  let restored = false;
  const restore = () => {
    if (restored) return;
    restored = true;
    workspaceUri.fsPath = originalRoot;
    fs.rmSync(repoRoot, { recursive: true, force: true });
    process.removeListener('exit', restore);
  };
  process.once('exit', restore);
  try {
    copyCanonicalEvidence(sourceRoot, repoRoot);
    initializeRepository(repoRoot);
    workspaceUri.fsPath = repoRoot;
  } catch (error) {
    restore();
    throw error;
  }
  return Object.freeze({
    root: repoRoot,
    baseResultFor: (typedTargets) => baseResultFor(repoRoot, typedTargets),
    restore
  });
}

module.exports = Object.freeze({ create });
