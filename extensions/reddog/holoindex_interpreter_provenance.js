'use strict';

const crypto = require('crypto');
const fs = require('fs');
const workerThreads = require('worker_threads');
const existsSync = fs.existsSync;
const joinPath = require('path').join;

const MAX_INTERPRETER_BYTES = 256 * 1024 * 1024;
const HASH_CHUNK_BYTES = 64 * 1024;

function rejected(status, source) {
  return { verified: false, status, source };
}

function openStableInterpreter(candidate, source) {
  const before = fs.lstatSync(candidate);
  if (!before.isFile() || before.isSymbolicLink() || before.nlink !== 1
      || before.size < 1 || before.size > MAX_INTERPRETER_BYTES) {
    return { error: rejected('interpreter_identity_rejected', source) };
  }
  const canonical = fs.realpathSync(candidate);
  const fd = fs.openSync(candidate, 'r');
  const opened = fs.fstatSync(fd);
  if (!opened.isFile() || opened.nlink !== 1 || opened.dev !== before.dev
      || opened.ino !== before.ino || opened.size !== before.size) {
    fs.closeSync(fd);
    return { error: rejected('interpreter_identity_changed', source) };
  }
  return { fd, opened, canonical };
}

function hashDescriptor(fd, size) {
  const hash = crypto.createHash('sha256');
  const chunk = Buffer.allocUnsafe(Math.min(HASH_CHUNK_BYTES, size));
  let offset = 0;
  while (offset < size) {
    const count = fs.readSync(fd, chunk, 0, Math.min(chunk.length, size - offset), offset);
    if (count < 1) throw new Error('interpreter_descriptor_short_read');
    hash.update(chunk.subarray(0, count));
    offset += count;
  }
  return hash.digest('hex');
}

function proveFinalIdentity(candidate, descriptor, source, digest) {
  const final = fs.lstatSync(candidate);
  if (!final.isFile() || final.isSymbolicLink() || final.nlink !== 1
      || final.dev !== descriptor.opened.dev || final.ino !== descriptor.opened.ino
      || final.size !== descriptor.opened.size) {
    return rejected('interpreter_identity_changed', source);
  }
  return { verified: true, status: 'verified_file', source,
    canonical_path_digest: 'sha256:' + crypto.createHash('sha256')
      .update(descriptor.canonical).digest('hex'),
    sha256: digest, size: descriptor.opened.size };
}

function verifiedInterpreterProvenance(candidate, source) {
  let descriptor = null;
  try {
    descriptor = openStableInterpreter(candidate, source);
    if (descriptor.error) return descriptor.error;
    const digest = hashDescriptor(descriptor.fd, descriptor.opened.size);
    return proveFinalIdentity(candidate, descriptor, source, digest);
  } catch (_err) {
    return rejected('interpreter_proof_failed', source);
  } finally {
    if (descriptor && descriptor.fd !== undefined) {
      try { fs.closeSync(descriptor.fd); } catch (_) { /* closed */ }
    }
  }
}

function selectInterpreter(root, configuredPath, platform) {
  const trimmed = typeof configuredPath === 'string' ? configuredPath.trim() : '';
  if (trimmed && trimmed !== 'python' && existsSync(trimmed)) {
    return { path: trimmed, source: 'configured', verify: true };
  }
  const isWin = (platform || process.platform) === 'win32';
  const executable = isWin ? 'python.exe' : 'python';
  const dotVenv = joinPath(root, '.venv', isWin ? 'Scripts' : 'bin', executable);
  if (existsSync(dotVenv)) return { path: dotVenv, source: 'workspace_dotvenv', verify: true };
  const venv = joinPath(root, 'venv', isWin ? 'Scripts' : 'bin', executable);
  if (existsSync(venv)) return { path: venv, source: 'workspace_venv', verify: true };
  const status = trimmed && trimmed !== 'python' ? 'configured_path_unresolved' : 'ambient_path';
  return { path: trimmed || 'python', source: 'system',
    verify: false, unverifiedStatus: status + '_unverified' };
}

function resolveInterpreter(root, configuredPath, platform) {
  const selected = selectInterpreter(root, configuredPath, platform);
  return { path: selected.path, source: selected.source,
    provenance: selected.verify
      ? verifiedInterpreterProvenance(selected.path, selected.source)
      : rejected(selected.unverifiedStatus, selected.source) };
}

function cancelledProof(source) {
  return rejected('interpreter_proof_cancelled', source);
}

function provenanceWorker(candidate, source, lifecycle) {
  return new Promise((resolve) => {
    let settled = false;
    let worker;
    let removeCancel = () => {};
    const finish = (value) => {
      if (settled) return;
      settled = true;
      removeCancel();
      if (lifecycle) lifecycle.release(worker);
      resolve(value);
    };
    if (lifecycle && lifecycle.isCancelled()) return finish(cancelledProof(source));
    try {
      worker = new workerThreads.Worker(__filename, {
        workerData: { reddogTask: 'interpreter_provenance', candidate, source }
      });
      if (lifecycle && !lifecycle.own(worker)) return finish(cancelledProof(source));
      if (lifecycle) removeCancel = lifecycle.onCancel(() => finish(cancelledProof(source)));
      worker.once('message', finish);
      worker.once('error', () => finish(rejected('interpreter_proof_failed', source)));
      worker.once('exit', (code) => {
        if (code !== 0) finish(rejected('interpreter_proof_failed', source));
      });
    } catch (_err) {
      finish(rejected('interpreter_proof_failed', source));
    }
  });
}

async function resolveInterpreterAsync(root, configuredPath, platform, lifecycle) {
  const selected = selectInterpreter(root, configuredPath, platform);
  if (!selected.verify) return { path: selected.path, source: selected.source,
    provenance: rejected(selected.unverifiedStatus, selected.source) };
  return { path: selected.path, source: selected.source,
    provenance: await provenanceWorker(selected.path, selected.source, lifecycle) };
}

if (!workerThreads.isMainThread && workerThreads.workerData
    && workerThreads.workerData.reddogTask === 'interpreter_provenance') {
  workerThreads.parentPort.postMessage(verifiedInterpreterProvenance(
    workerThreads.workerData.candidate, workerThreads.workerData.source
  ));
}

module.exports = Object.freeze({
  HASH_CHUNK_BYTES,
  resolveInterpreter,
  resolveInterpreterAsync,
  verifiedInterpreterProvenance
});
