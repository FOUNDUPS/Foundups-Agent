'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { sameCanonicalPath } = require('./governed_git_readiness');

const AUTHORITY_CONTROLS = ['HEAD', 'index', 'config.worktree'];
const COMMON_CONTROLS = ['config', 'shallow', 'info/attributes', 'info/exclude'];
const FORBIDDEN_CONTROLS = [
  'objects/info/alternates', 'objects/info/http-alternates', 'info/grafts',
  'reftable'
];
const MAX_CONTROL_BYTES = 1024 * 1024;

function controlLimit(name) {
  if (name === 'index') return 64 * MAX_CONTROL_BYTES;
  if (name === 'packed-refs') return 16 * MAX_CONTROL_BYTES;
  return MAX_CONTROL_BYTES;
}

function digest(parts) {
  return crypto.createHash('sha256').update(parts.join('\0'), 'utf8').digest('hex');
}

function noFollowPathEntry(filePath) {
  try {
    return { state: 'present', metadata: fs.lstatSync(filePath) };
  } catch (err) {
    return { state: err && err.code === 'ENOENT' ? 'absent' : 'error', metadata: null };
  }
}

function plainControlFile(filePath) {
  const entry = noFollowPathEntry(filePath);
  if (entry.state === 'absent') return true;
  if (entry.state !== 'present') return false;
  const metadata = entry.metadata;
  return metadata.isFile() && !metadata.isSymbolicLink() && metadata.nlink === 1
    && sameCanonicalPath(fs.realpathSync(filePath), filePath);
}

function sameFile(left, right) {
  return left.isFile() && right.isFile() && !left.isSymbolicLink()
    && !right.isSymbolicLink() && left.ino === right.ino
    && left.size === right.size && left.mtimeMs === right.mtimeMs
    && left.ctimeMs === right.ctimeMs && left.nlink === 1 && right.nlink === 1;
}

function sameDirectory(left, right) {
  return left.isDirectory() && right.isDirectory() && !left.isSymbolicLink()
    && !right.isSymbolicLink() && left.dev === right.dev && left.ino === right.ino;
}

function readStableControl(candidate, before, limit) {
  if (before.size > limit) return null;
  const handle = fs.openSync(candidate, 'r');
  try {
    const opened = fs.fstatSync(handle);
    if (!sameFile(before, opened) || opened.size > limit) return null;
    const content = Buffer.allocUnsafe(opened.size);
    let offset = 0;
    while (offset < opened.size) {
      const count = fs.readSync(handle, content, offset, opened.size - offset, offset);
      if (!Number.isInteger(count) || count <= 0) return null;
      offset += count;
    }
    const after = fs.fstatSync(handle);
    const final = fs.lstatSync(candidate);
    return sameFile(opened, after) && sameFile(after, final) ? content : null;
  } finally {
    fs.closeSync(handle);
  }
}

function controlRecord(base, name, required) {
  const candidate = path.join(base, name);
  const entry = noFollowPathEntry(candidate);
  if (entry.state === 'absent') {
    return { valid: !required, present: false, content: '', parts: [name, 'missing'] };
  }
  if (entry.state !== 'present') {
    return { valid: false, present: true, content: '', parts: [name, 'error'] };
  }
  const metadata = entry.metadata;
  const valid = metadata.isFile() && !metadata.isSymbolicLink()
    && metadata.nlink === 1 && metadata.size <= controlLimit(name)
    && sameCanonicalPath(fs.realpathSync(candidate), candidate);
  if (!valid) return { valid: false, present: true, content: '', parts: [name, 'invalid'] };
  const content = readStableControl(candidate, metadata, controlLimit(name));
  if (!content) return { valid: false, present: true, content: '', parts: [name, 'unstable'] };
  return { valid: true, present: true,
    content: name === 'index' ? '' : content.toString('utf8'),
    parts: [name, 'f', metadata.ino, metadata.mtimeMs, metadata.ctimeMs,
      metadata.size, crypto.createHash('sha256').update(content).digest('hex')] };
}

function directoryRecord(base, name) {
  const candidate = path.join(base, name);
  const entry = noFollowPathEntry(candidate);
  if (entry.state === 'absent') {
    return { valid: false, present: false, parts: [name, 'missing'] };
  }
  if (entry.state !== 'present') {
    return { valid: false, present: true, parts: [name, 'error'] };
  }
  const before = entry.metadata;
  if (!before.isDirectory() || before.isSymbolicLink()) {
    return { valid: false, present: true, parts: [name, 'invalid', before.ino] };
  }
  const canonical = fs.realpathSync(candidate);
  const after = noFollowPathEntry(candidate);
  const valid = after.state === 'present' && sameCanonicalPath(canonical, candidate)
    && sameDirectory(before, after.metadata);
  return { valid, present: true,
    parts: [name, valid ? 'd' : 'invalid', before.dev, before.ino] };
}

function records(base, names, requiredNames) {
  const required = new Set(requiredNames || []);
  const values = names.map((name) => controlRecord(base, name, required.has(name)));
  return { valid: values.every((item) => item.valid), values,
    parts: values.flatMap((item) => item.parts) };
}

function safeRefName(value) {
  const prefix = 'refs/heads/';
  if (typeof value !== 'string' || !value.startsWith(prefix)) return false;
  const relative = value.slice(prefix.length);
  if (!relative || relative.startsWith('/') || relative.endsWith('/')
    || relative.includes('//') || relative.includes('..') || relative.includes('@{')) return false;
  for (const character of relative) {
    const code = character.codePointAt(0);
    if (code <= 0x20 || code === 0x7f || '~^:?*[\\'.includes(character)) return false;
  }
  return relative.split('/').every((part) => part && !part.startsWith('.')
    && !part.endsWith('.') && !part.endsWith('.lock'));
}

function validOid(value) {
  return (value.length === 40 || value.length === 64) && /^[0-9a-f]+$/i.test(value);
}

function packedRefOid(content, refName) {
  let found = '';
  let previousWasCurrent = false;
  for (const line of String(content || '').split(/\r?\n/)) {
    if (!line || line.startsWith('#')) {
      previousWasCurrent = false;
      continue;
    }
    const tokens = line.trim().split(/\s+/);
    const targetsCurrent = tokens.includes(refName);
    if (line.startsWith('^')) {
      if (previousWasCurrent || targetsCurrent) return null;
      previousWasCurrent = false;
      continue;
    }
    if (!targetsCurrent) {
      previousWasCurrent = false;
      continue;
    }
    const canonical = /^([0-9a-f]+) ([^\s]+)$/i.exec(line);
    if (!canonical || !validOid(canonical[1])
      || canonical[2] !== refName || found) return null;
    found = canonical[1].toLowerCase();
    previousWasCurrent = true;
  }
  return found;
}

function refParentChain(common, refName) {
  const components = refName.split('/');
  const parts = [];
  for (let index = 2; index < components.length - 1; index += 1) {
    const relative = components.slice(0, index + 1).join('/');
    const record = directoryRecord(common, relative);
    if (!record.present) return { valid: true, parts: [...parts, relative, 'missing'] };
    parts.push(...record.parts);
    if (!record.valid) return { valid: false, parts };
  }
  return { valid: true, parts };
}

function symbolicRefBinding(common, refName) {
  if (!safeRefName(refName)) return { valid: false, state: 'invalid',
    parts: ['ref', 'invalid'] };
  const parents = refParentChain(common, refName);
  if (!parents.valid) return { valid: false, state: 'invalid',
    parts: ['ref', refName, 'parent-invalid', ...parents.parts] };
  const loose = controlRecord(common, refName, false);
  if (!loose.valid) return { valid: false, state: 'invalid',
    parts: ['ref', refName, 'invalid'] };
  if (loose.present) {
    const oid = loose.content.trim();
    const valid = validOid(oid);
    return { valid, state: valid ? 'bound' : 'invalid', parts: ['ref', refName, 'loose',
      oid.toLowerCase(), ...parents.parts, ...loose.parts] };
  }
  const packed = controlRecord(common, 'packed-refs', false);
  if (!packed.valid) return { valid: false, state: 'invalid',
    parts: ['ref', refName, 'packed-invalid'] };
  const oid = packedRefOid(packed.content, refName);
  return { valid: oid !== null, state: oid === null ? 'invalid' : oid ? 'bound' : 'unborn',
    parts: ['ref', refName,
    oid ? 'packed' : 'unborn', oid || '', ...parents.parts] };
}

function headBinding(common, head) {
  if (!head.valid || !head.present) return { valid: false, state: 'invalid',
    parts: ['HEAD', 'invalid'] };
  const value = head.content.trim();
  if (validOid(value)) return { valid: true, state: 'bound',
    parts: ['HEAD', 'detached', value.toLowerCase(), ...head.parts] };
  const match = /^ref: ([^\r\n]+)$/.exec(value);
  if (!match) return { valid: false, state: 'invalid',
    parts: ['HEAD', 'invalid-content'] };
  const ref = symbolicRefBinding(common, match[1]);
  return { valid: ref.valid, state: ref.state,
    parts: ['HEAD', 'symbolic', ...head.parts, ...ref.parts] };
}

function forbiddenControlsAbsent(common) {
  return [...FORBIDDEN_CONTROLS, 'commondir'].every((name) =>
    noFollowPathEntry(path.join(common, name)).state === 'absent');
}

function directTopology(root, gitEntry, metadata) {
  if (!metadata.isDirectory() || metadata.isSymbolicLink()
    || !sameCanonicalPath(fs.realpathSync(gitEntry), gitEntry)) return null;
  return { kind: 'direct', common: gitEntry, admin: gitEntry,
    parts: ['direct', fs.realpathSync(root), metadata.ino] };
}

function linkedTopology(root, gitEntry, metadata) {
  if (!metadata.isFile() || metadata.isSymbolicLink()
    || metadata.nlink !== 1 || metadata.size > 4096) return null;
  const marker = controlRecord(root, '.git', true);
  const match = marker.valid && /^gitdir:\s*([^\r\n]+)\s*$/i.exec(marker.content);
  if (!match) return null;
  const admin = fs.realpathSync(path.resolve(root, match[1]));
  if (!directoryRecord(path.dirname(admin), path.basename(admin)).valid
    || path.basename(path.dirname(admin)).toLowerCase() !== 'worktrees') return null;
  const topology = records(admin, ['commondir', 'gitdir'], ['commondir', 'gitdir']);
  if (!topology.valid) return null;
  const common = fs.realpathSync(path.resolve(admin, topology.values[0].content.trim()));
  if (path.basename(common).toLowerCase() !== '.git'
    || !sameCanonicalPath(path.dirname(admin), path.join(common, 'worktrees'))) return null;
  if (!sameCanonicalPath(path.resolve(admin, topology.values[1].content.trim()), gitEntry)) return null;
  return { kind: 'linked', common, admin,
    parts: ['linked', fs.realpathSync(root), ...marker.parts, ...topology.parts] };
}

function topology(root, knownEntry) {
  const gitEntry = path.join(root, '.git');
  const entry = knownEntry || noFollowPathEntry(gitEntry);
  if (entry.state !== 'present') return null;
  return directTopology(root, gitEntry, entry.metadata)
    || linkedTopology(root, gitEntry, entry.metadata);
}

function authorityReceipt(root, gitEntry) {
  const current = topology(root, gitEntry);
  if (!current) return null;
  const authority = records(current.admin, AUTHORITY_CONTROLS, ['HEAD']);
  const common = records(current.common, COMMON_CONTROLS, ['config']);
  const dirs = ['objects', 'refs', 'refs/heads', 'info', 'objects/info']
    .map((name) => directoryRecord(current.common, name));
  const head = headBinding(current.common, authority.values[0]);
  const valid = authority.valid && common.valid && head.valid
    && dirs.every((item) => item.valid) && forbiddenControlsAbsent(current.common);
  const worktree = authority.values[2];
  return { valid, headState: head.state, worktreeConfigState: !worktree.present ? 'absent'
    : worktree.valid ? 'present' : 'invalid', parts: [...current.parts,
      ...authority.parts, ...common.parts, ...dirs.flatMap((item) => item.parts), ...head.parts] };
}

function invalidReceipt() {
  return Object.freeze({ fingerprint: '', valid: false,
    worktree_config_state: 'invalid' });
}

function registeredGitMetadataState(root) {
  try {
    const entry = noFollowPathEntry(path.join(root, '.git'));
    if (entry.state !== 'present') {
      return Object.freeze({ state: entry.state, headState: 'invalid',
        receipt: invalidReceipt() });
    }
    const authority = authorityReceipt(root, entry);
    if (!authority) return Object.freeze({ state: 'present', headState: 'invalid',
      receipt: invalidReceipt() });
    const receipt = Object.freeze({ fingerprint: digest(authority.parts),
      valid: authority.valid, worktree_config_state: authority.worktreeConfigState });
    return Object.freeze({ state: 'present', headState: authority.headState, receipt });
  } catch (err) {
    return Object.freeze({ state: 'error', headState: 'invalid', receipt: invalidReceipt() });
  }
}

function registeredGitMetadataReceipt(root) {
  return registeredGitMetadataState(root).receipt;
}

function registeredGitMetadata(root) {
  return registeredGitMetadataReceipt(root).valid;
}

module.exports = {
  noFollowPathEntry, plainControlFile, registeredGitMetadata,
  registeredGitMetadataReceipt, registeredGitMetadataState
};
