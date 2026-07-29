'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const filesystem = require('./backend_compatibility_filesystem');
const manifestContract = require('./backend_compatibility_manifest');

function materializationError(reasons) {
  const detail = Array.from(new Set(reasons)).join(',');
  return new Error('backend_runtime_materialization_rejected:' + detail);
}

function verifiedManifest(rootState, deps) {
  const read = manifestContract.readManifest(rootState, deps);
  const reasons = read.reason ? [read.reason] : [];
  if (read.manifest) {
    reasons.push(...manifestContract.validateManifest(read.manifest));
    reasons.push(...manifestContract.verifyRuntimeFiles(
      rootState, read.manifest, deps
    ).reasons);
  }
  if (reasons.length || !read.manifest) throw materializationError(reasons);
  return read;
}

function verifiedSource(rootState, relativePath, expected, deps) {
  const located = filesystem.containedRegularFile(rootState, relativePath, deps);
  if (!located.ok) throw materializationError(['source_missing:' + relativePath]);
  const raw = deps.fs.readFileSync(located.candidate);
  const observed = filesystem.sha256Hex(
    filesystem.normalizedTextBytes(raw), deps.crypto
  );
  if (observed !== expected) {
    throw materializationError(['source_changed:' + relativePath]);
  }
  return raw;
}

function destination(runtimeRoot, relativePath, deps) {
  const target = deps.path.resolve(runtimeRoot, relativePath);
  const relative = deps.path.relative(runtimeRoot, target);
  if (!relative || relative.startsWith('..') || deps.path.isAbsolute(relative)) {
    throw materializationError(['destination_escape']);
  }
  return target;
}

function writeSource(runtimeRoot, relativePath, raw, deps) {
  const target = destination(runtimeRoot, relativePath, deps);
  deps.fs.mkdirSync(deps.path.dirname(target), { recursive: true, mode: 0o700 });
  deps.fs.writeFileSync(target, raw, { flag: 'wx', mode: 0o600 });
}

function runtimeScript(runtimeRoot, repoRoot, sourcePath, deps) {
  const absolute = deps.path.resolve(sourcePath);
  const relative = deps.path.relative(repoRoot, absolute);
  if (!relative || relative.startsWith('..') || deps.path.isAbsolute(relative)) {
    throw materializationError(['script_outside_repo']);
  }
  return destination(runtimeRoot, relative, deps);
}

function cleanup(runtimeRoot, deps) {
  try {
    deps.fs.rmSync(runtimeRoot, { recursive: true, force: true });
  } catch (_error) {
    // The next OS temp cleanup pass may remove a handle-delayed Windows tree.
  }
}

function separatedRuntimeRoot(candidate, repoRoot, deps) {
  const stats = deps.fs.lstatSync(candidate);
  if (!stats.isDirectory() || stats.isSymbolicLink()) return '';
  const root = deps.fs.realpathSync(candidate);
  const fromRepo = deps.path.relative(repoRoot, root);
  const fromRuntime = deps.path.relative(root, repoRoot);
  const separated = (
    (fromRepo.startsWith('..') || deps.path.isAbsolute(fromRepo))
    && (fromRuntime.startsWith('..') || deps.path.isAbsolute(fromRuntime))
  );
  return separated ? root : '';
}

function populate(rootState, manifest, runtimeRoot, deps) {
  for (const relativePath of manifest.required_runtime_files) {
    const raw = verifiedSource(
      rootState, relativePath,
      manifest.required_runtime_sha256[relativePath], deps
    );
    writeSource(runtimeRoot, relativePath, raw, deps);
  }
}

function materializedResult(rootState, runtimeRoot, deps) {
  return Object.freeze({
    runtimeRoot: deps.fs.realpathSync(runtimeRoot),
    targetRepoRoot: rootState.canonicalRoot,
    scriptPath: (sourcePath) => runtimeScript(
      runtimeRoot, rootState.canonicalRoot, sourcePath, deps
    ),
    cleanup: () => cleanup(runtimeRoot, deps)
  });
}

function materialize(repoRoot, options) {
  const opts = options && typeof options === 'object' ? options : {};
  const deps = filesystem.dependencies(opts);
  const rootState = filesystem.safeRoot(repoRoot, deps);
  if (rootState.reason) throw materializationError([rootState.reason]);
  const read = verifiedManifest(rootState, deps);
  const tempRoot = separatedRuntimeRoot(
    opts.tempRoot || os.tmpdir(), rootState.canonicalRoot, deps
  );
  if (!tempRoot) throw materializationError(['runtime_root_not_separated']);
  const runtimeRoot = deps.fs.mkdtempSync(
    deps.path.join(tempRoot, 'reddog-runtime-')
  );
  try {
    populate(rootState, read.manifest, runtimeRoot, deps);
    return materializedResult(rootState, runtimeRoot, deps);
  } catch (error) {
    cleanup(runtimeRoot, deps);
    throw error;
  }
}

module.exports = { materialize };
