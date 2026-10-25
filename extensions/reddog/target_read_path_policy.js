'use strict';

const path = require('path');

const BLOCKED_SEGMENTS = new Set([
  '.git', '.ssh', '.gnupg', '.aws', '.azure', '.gcloud',
  'node_modules', '__pycache__', '.venv'
]);
const BLOCKED_BASENAMES = Object.freeze([
  '.env', '.npmrc', '.pypirc', '.netrc', '.git-credentials', '.dockerconfigjson'
]);
const SOURCE_EXTENSIONS = new Set([
  '.c', '.cc', '.cpp', '.cs', '.go', '.h', '.hpp', '.java', '.js', '.jsx',
  '.md', '.mjs', '.py', '.rs', '.rst', '.ts', '.tsx'
]);
const SENSITIVE_TOKEN = /(?:^|[._-])(?:api[_-]?keys?|auth|private[_-]?keys?|service[_-]?accounts?|signing[_-]?keys?)(?=[._-]|$)/i;
const PRIVATE_CONTAINER = /(?:^|\.)(?:jks|key|keystore|p12|pem|pfx|vsix)(?:\.|$)/i;
const SSH_KEY_BASENAME = /^id_(?:rsa|dsa|ecdsa|ed25519)(?:\.pub)?(?:[._-]|$)/i;
const SENSITIVE_CONTAINER = /(?:^|[._-])(?:secrets?|credentials?|api[_-]?keys?|private[_-]?keys?|signing[_-]?keys?|service[_-]?accounts?)(?=[._-]|$)|^(?:tokens?)(?:[._-](?:data|store|cache|secret|vault))?$/i;
const SENSITIVE_SOURCE_BASENAME = /(?:^|[._-])(?:secrets?|credentials?|api[_-]?keys?|private[_-]?keys?|signing[_-]?keys?|service[_-]?accounts?)(?=[._-]|$)/i;
const WINDOWS_RESERVED = /^(?:CON|PRN|AUX|NUL|(?:COM|LPT)(?:[1-9]|\u00b9|\u00b2|\u00b3))$/i;

function normalizeRelRepoPath(relPath) {
  return String(relPath || '').replace(/\\/g, '/');
}

function canonicalPolicySegments(value) {
  return String(value || '').split('/').map(trimPolicySuffix);
}

function trimPolicySuffix(segment) {
  const value = String(segment || '');
  let end = value.length;
  while (end > 0 && (value[end - 1] === '.' || value[end - 1] === ' ')) end -= 1;
  return value.slice(0, end);
}

function isSensitiveBasename(value) {
  const basename = String(value || '').toLowerCase();
  if (PRIVATE_CONTAINER.test(basename) || SSH_KEY_BASENAME.test(basename)) return true;
  if (SOURCE_EXTENSIONS.has(path.posix.extname(basename))) {
    return SENSITIVE_SOURCE_BASENAME.test(basename);
  }
  return SENSITIVE_TOKEN.test(basename);
}

function isBlockedSegment(segment, sourcePath) {
  return BLOCKED_SEGMENTS.has(segment)
    || segment === '.env'
    || segment.startsWith('.env.')
    || SENSITIVE_CONTAINER.test(segment)
    || !sourcePath && ['secret', 'credential', 'token'].some((marker) => segment.includes(marker));
}

function invalidPolicySegment(segment) {
  if (!segment || segment === '.' || segment === '..') return true;
  const deviceStem = segment.split('.')[0];
  return WINDOWS_RESERVED.test(deviceStem);
}

function isTargetReadPathDenied(relPath) {
  const normalized = normalizeRelRepoPath(relPath);
  if (!normalized || /[\x00-\x1f\x7f]/.test(normalized)) return 'path_missing';
  if (path.isAbsolute(normalized) || /^(?:[a-zA-Z]:|\/\/)/.test(normalized)) return 'outside_root';
  if (normalized.includes(':')) return 'outside_root';
  const parts = canonicalPolicySegments(normalized);
  if (parts.some(invalidPolicySegment)) return 'outside_root';
  const lower = parts.map((segment) => segment.toLowerCase());
  const base = lower[lower.length - 1];
  const sourcePath = SOURCE_EXTENSIONS.has(path.posix.extname(base));
  if (lower.some((segment) => isBlockedSegment(segment, sourcePath))) return 'outside_root';
  if (BLOCKED_BASENAMES.some((name) => base === name || base.startsWith(name + '.'))) return 'outside_root';
  if (isSensitiveBasename(base)) return 'outside_root';
  return null;
}

module.exports = { isTargetReadPathDenied, normalizeRelRepoPath };
