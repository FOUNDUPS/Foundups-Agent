'use strict';

const childProcess = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const SCHEMA = 'reddog_governed_git_executable.v1';
const MAX_EXECUTABLE_BYTES = 256 * 1024 * 1024;
const PATH_KEYS = Object.freeze(['PATH', 'Path', 'PATHEXT']);
const WINDOWS_VERIFIER_RELATIVE = 'System32/WindowsPowerShell/v1.0/powershell.exe';

function digest(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function canonicalDigest(value) {
  return 'sha256:' + digest(Buffer.from(String(value), 'utf8'));
}

function environmentValue(source, keys) {
  for (const key of keys) {
    if (typeof source[key] === 'string' && source[key]) return source[key];
  }
  return '';
}

function samePath(left, right, platform) {
  const normalize = (value) => path.resolve(value);
  return platform === 'win32'
    ? normalize(left).toLowerCase() === normalize(right).toLowerCase()
    : normalize(left) === normalize(right);
}

function pathCandidates(source, deps) {
  const pathValue = environmentValue(source, deps.platform === 'win32'
    ? ['Path', 'PATH'] : ['PATH']);
  if (!pathValue) return [];
  const names = deps.platform === 'win32'
    ? windowsExecutableNames(environmentValue(source, ['PATHEXT'])) : ['git'];
  const values = [];
  for (const directory of pathValue.split(deps.pathDelimiter)) {
    if (!directory || !path.isAbsolute(directory)) continue;
    for (const name of names) values.push(path.resolve(directory, name));
  }
  return values;
}

function windowsExecutableNames(pathExt) {
  const extensions = String(pathExt || '.COM;.EXE;.BAT;.CMD').split(';')
    .map((value) => value.trim()).filter((value) => /^\.[A-Za-z0-9]+$/.test(value));
  return [...new Set(extensions.map((extension) => 'git' + extension))];
}

function statIdentity(stat) {
  const native = Object.freeze({
    dev: String(stat.dev), ino: String(stat.ino), mode: String(stat.mode),
    nlink: Number(stat.nlink), birthtime_ns: String(stat.birthtimeNs || 0),
    ctime_ns: String(stat.ctimeNs || 0), mtime_ns: String(stat.mtimeNs || 0)
  });
  const portable = canonicalDigest([
    String(stat.size), native.mode, native.birthtime_ns,
    native.ctime_ns, native.mtime_ns
  ].join('\0'));
  return Object.freeze({ portable, native, nlink: native.nlink });
}

function sameStat(left, right) {
  return left.isFile() && right.isFile() && !left.isSymbolicLink()
    && !right.isSymbolicLink() && left.dev === right.dev && left.ino === right.ino
    && left.mode === right.mode && left.nlink === right.nlink
    && left.size === right.size && left.birthtimeNs === right.birthtimeNs
    && left.ctimeNs === right.ctimeNs && left.mtimeNs === right.mtimeNs;
}

function readOpened(handle, size, io) {
  if (size < 0n || size > BigInt(MAX_EXECUTABLE_BYTES)) {
    throw new Error('governed_git_executable_size_invalid');
  }
  const length = Number(size);
  const content = Buffer.allocUnsafe(length);
  let offset = 0;
  while (offset < length) {
    const count = io.readSync(handle, content, offset, length - offset, offset);
    if (!Number.isInteger(count) || count <= 0) {
      throw new Error('governed_git_executable_read_failed');
    }
    offset += count;
  }
  return content;
}

function captureFile(candidate, deps) {
  const absolute = path.resolve(candidate);
  const before = deps.fs.lstatSync(absolute, { bigint: true });
  const canonical = deps.fs.realpathSync.native(absolute);
  if (!before.isFile() || before.isSymbolicLink()
    || !samePath(absolute, canonical, deps.platform)) {
    throw new Error('governed_git_executable_link_denied');
  }
  const handle = deps.fs.openSync(absolute, 'r');
  try {
    const opened = deps.fs.fstatSync(handle, { bigint: true });
    if (!sameStat(before, opened)) throw new Error('governed_git_executable_changed');
    const content = readOpened(handle, opened.size, deps.fs);
    const after = deps.fs.fstatSync(handle, { bigint: true });
    const final = deps.fs.lstatSync(absolute, { bigint: true });
    const finalCanonical = deps.fs.realpathSync.native(absolute);
    if (!sameStat(opened, after) || !sameStat(after, final)
      || !samePath(canonical, finalCanonical, deps.platform)) {
      throw new Error('governed_git_executable_changed');
    }
    return Object.freeze({ canonical_path: canonical, size: Number(opened.size),
      sha256: digest(content), start_identity: statIdentity(before),
      final_identity: statIdentity(final), stat: final });
  } finally {
    deps.fs.closeSync(handle);
  }
}

function boundedSystemVerifier(deps) {
  const source = deps.environment;
  const declared = environmentValue(source, ['SystemRoot', 'SYSTEMROOT', 'WINDIR']);
  if (!declared || !path.isAbsolute(declared)) {
    throw new Error('governed_git_signature_verifier_unavailable');
  }
  const root = deps.fs.realpathSync.native(path.resolve(declared));
  const candidate = path.join(root, 'System32', 'WindowsPowerShell', 'v1.0',
    'powershell.exe');
  const verifier = captureFile(candidate, deps);
  const relative = path.relative(root, verifier.canonical_path);
  if (!relative || relative.startsWith('..' + path.sep) || path.isAbsolute(relative)) {
    throw new Error('governed_git_signature_verifier_unbounded');
  }
  const rootDigest = canonicalDigest(root);
  const pathDigest = canonicalDigest(verifier.canonical_path);
  const relativeDigest = canonicalDigest(WINDOWS_VERIFIER_RELATIVE);
  return Object.freeze({ ...verifier, system_root_digest: rootDigest,
    fixed_relative_path_digest: relativeDigest,
    system_root_containment_proof: canonicalDigest(
      [rootDigest, pathDigest, relativeDigest].join('\0')
    ) });
}

function defaultWindowsSignature(target, deps) {
  const verifier = boundedSystemVerifier(deps);
  const script = "$ErrorActionPreference='Stop';"
    + "$Target=[Environment]::GetEnvironmentVariable('REDDOG_GIT_SIGNATURE_TARGET','Process');"
    + "$s=Get-AuthenticodeSignature -LiteralPath $Target;"
    + "$o=[ordered]@{status=[string]$s.Status;"
    + "thumbprint=[string]$s.SignerCertificate.Thumbprint;"
    + "subject=[string]$s.SignerCertificate.Subject};"
    + "$o|ConvertTo-Json -Compress";
  const output = deps.execFileSync(verifier.canonical_path,
    ['-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script], {
      encoding: 'utf8', timeout: 10000, windowsHide: true,
      env: signatureEnvironment(deps.environment, target)
    });
  const parsed = JSON.parse(String(output || ''));
  if (String(parsed.status || '').toLowerCase() !== 'valid') {
    throw new Error('governed_git_signature_invalid');
  }
  return Object.freeze({ status: 'valid',
    subject_digest: canonicalDigest(parsed.subject || ''),
    thumbprint_digest: canonicalDigest(parsed.thumbprint || ''),
    verifier: verifierProof(verifier) });
}

function signatureEnvironment(source, target) {
  const output = {};
  for (const key of ['SystemRoot', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP']) {
    if (typeof source[key] === 'string' && source[key]) output[key] = source[key];
  }
  output.REDDOG_GIT_SIGNATURE_TARGET = target;
  return output;
}

function verifierProof(verifier) {
  return Object.freeze({ canonical_path: verifier.canonical_path,
    canonical_path_digest: canonicalDigest(verifier.canonical_path),
    sha256: verifier.sha256, size: verifier.size,
    start_identity: verifier.start_identity, final_identity: verifier.final_identity,
    system_root_digest: verifier.system_root_digest,
    fixed_relative_path_digest: verifier.fixed_relative_path_digest,
    system_root_containment_proof: verifier.system_root_containment_proof });
}

function stableSignature(binding, deps) {
  if (deps.platform !== 'win32') return binding.signature;
  if (!binding.signature || binding.signature.status !== 'valid') {
    throw new Error('governed_git_signature_invalid');
  }
  if (deps.verifySignature) {
    const proof = signatureProof(binding.canonical_path, deps);
    if (JSON.stringify(proof) !== JSON.stringify(binding.signature)) {
      throw new Error('governed_git_signature_changed');
    }
    return proof;
  }
  const captured = captureFile(binding.signature.verifier.canonical_path, deps);
  const current = verifierProof({ ...captured,
    system_root_digest: binding.signature.verifier.system_root_digest,
    fixed_relative_path_digest: binding.signature.verifier.fixed_relative_path_digest,
    system_root_containment_proof:
      binding.signature.verifier.system_root_containment_proof });
  if (JSON.stringify(current) !== JSON.stringify(binding.signature.verifier)) {
    throw new Error('governed_git_signature_verifier_changed');
  }
  return binding.signature;
}

function signatureProof(target, deps) {
  if (deps.platform !== 'win32') return Object.freeze({ status: 'not_applicable' });
  const proof = deps.verifySignature
    ? deps.verifySignature(target, deps) : defaultWindowsSignature(target, deps);
  if (!proof || proof.status !== 'valid' || !proof.verifier
    || !path.isAbsolute(proof.verifier.canonical_path || '')) {
    throw new Error('governed_git_signature_invalid');
  }
  return Object.freeze(proof);
}

function bindingFromCapture(captured, signature) {
  return Object.freeze({ schema_version: SCHEMA,
    canonical_path: captured.canonical_path,
    canonical_path_digest: canonicalDigest(captured.canonical_path),
    sha256: captured.sha256, size: captured.size,
    start_identity: captured.start_identity, final_identity: captured.final_identity,
    signature });
}

function publicIdentity(identity) {
  const native = identity.native;
  return Object.freeze({ portable: identity.portable,
    native: Object.freeze({ dev: native.dev, ino: native.ino, mode: native.mode,
      nlink: native.nlink, birthtime_ns: native.birthtime_ns,
      ctime_ns: native.ctime_ns, mtime_ns: native.mtime_ns }), nlink: identity.nlink });
}

function publicVerifier(verifier) {
  return Object.freeze({ canonical_path_digest: verifier.canonical_path_digest,
    sha256: verifier.sha256, size: verifier.size,
    start_identity: publicIdentity(verifier.start_identity),
    final_identity: publicIdentity(verifier.final_identity),
    system_root_digest: verifier.system_root_digest,
    fixed_relative_path_digest: verifier.fixed_relative_path_digest,
    system_root_containment_proof: verifier.system_root_containment_proof });
}

function publicSignature(signature) {
  if (signature.status === 'not_applicable') {
    return Object.freeze({ status: 'not_applicable' });
  }
  return Object.freeze({ status: signature.status,
    subject_digest: signature.subject_digest,
    thumbprint_digest: signature.thumbprint_digest,
    verifier: publicVerifier(signature.verifier) });
}

function toPublicExecutableReceipt(binding) {
  if (!binding || binding.schema_version !== SCHEMA) {
    throw new Error('governed_git_executable_public_receipt_invalid');
  }
  return Object.freeze({ schema_version: SCHEMA,
    canonical_path_digest: binding.canonical_path_digest,
    sha256: binding.sha256, size: binding.size,
    start_identity: publicIdentity(binding.start_identity),
    final_identity: publicIdentity(binding.final_identity),
    signature: publicSignature(binding.signature) });
}

function sameBinding(binding, captured) {
  return binding && binding.schema_version === SCHEMA
    && binding.canonical_path === captured.canonical_path
    && binding.canonical_path_digest === canonicalDigest(captured.canonical_path)
    && binding.sha256 === captured.sha256 && binding.size === captured.size
    && JSON.stringify(binding.final_identity) === JSON.stringify(captured.start_identity);
}

function closedExecutionOptions(options) {
  const output = Object.assign({}, options || {});
  output.env = Object.assign({}, output.env || {});
  for (const key of PATH_KEYS) delete output.env[key];
  return output;
}

function resolverDependencies(options) {
  const values = options && typeof options === 'object' ? options : {};
  return Object.freeze({
    platform: values.platform || process.platform,
    pathDelimiter: values.pathDelimiter
      || ((values.platform || process.platform) === 'win32' ? ';' : path.delimiter),
    fs: values.fs || fs,
    execFileSync: values.execFileSync
      || ((...args) => childProcess.execFileSync(...args)),
    verifySignature: values.verifySignature,
    environment: values.environment || process.env
  });
}

function revalidateBound(state, binding) {
  const captured = captureFile(binding && binding.canonical_path, state.deps);
  if (!sameBinding(binding, captured)) throw new Error('governed_git_executable_changed');
  return bindingFromCapture(captured, stableSignature(binding, state.deps));
}

function bindResolved(state, source, controls) {
  if ((!controls || controls.cache !== false) && state.cached) {
    return revalidateBound(state, state.cached);
  }
  const candidate = pathCandidates(source || state.deps.environment, state.deps)
    .find((value) => {
      try { return state.deps.fs.lstatSync(value).isFile(); }
      catch (_err) { return false; }
    });
  if (!candidate) throw new Error('governed_git_executable_not_found');
  const captured = captureFile(candidate, state.deps);
  const binding = bindingFromCapture(
    captured, signatureProof(captured.canonical_path, state.deps)
  );
  if (!controls || controls.cache !== false) state.cached = binding;
  return binding;
}

function executeBound(state, binding, args, execOptions) {
  const current = revalidateBound(state, binding);
  const output = state.deps.execFileSync(current.canonical_path, args,
    closedExecutionOptions(execOptions));
  revalidateBound(state, current);
  return output;
}

function create(options) {
  const state = { deps: resolverDependencies(options), cached: null };
  return Object.freeze({
    bind: (source, controls) => bindResolved(state, source, controls),
    revalidate: (binding) => revalidateBound(state, binding),
    toPublicExecutableReceipt,
    execFileSync: (binding, args, execOptions) =>
      executeBound(state, binding, args, execOptions)
  });
}

const defaultResolver = create();

module.exports = { SCHEMA, create, toPublicExecutableReceipt,
  bind: (source) => defaultResolver.bind(source),
  revalidate: (binding) => defaultResolver.revalidate(binding),
  execFileSync: (binding, args, options) =>
    defaultResolver.execFileSync(binding, args, options) };
