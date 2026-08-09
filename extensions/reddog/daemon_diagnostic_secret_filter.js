'use strict';

const SECRETS = [
  /\bsk-(?:or-|ant-api)?[A-Za-z0-9_-]{16,}/i,
  /\bsk_(?:live|test)_[A-Za-z0-9]{16,}/i,
  /\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}/,
  /\b(?:xai-|AIza|ya29\.|AKIA|gh[posru]_|github_pat_|xox[baprs]-)[A-Za-z0-9_.\/-]{10,}/i,
  /\b1\/\/[0-9A-Za-z._-]{10,}/,
  /\bBearer\s+[A-Za-z0-9._-]{8,}/i,
  /\bOPENROUTER_[A-Z_]*\s*[:=]\s*\S+/i,
  /[?&](?:code|access_token|refresh_token|id_token|token)=[^\s&"'}]+/i,
  /\b(?:access_token|refresh_token|id_token|client_secret|client_id|user_code|authorization_code|password|passwd|api_key|apikey|token|secret)\b\s*["']?\s*[:=]/i,
  /\b[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|APIKEY|CREDENTIAL)\b\s*[:=]/,
  /\b(?:set-cookie|cookie|session[_-]?id|sessionid)\b\s*[:=]/i,
  /[?&](?:signature|sig|x-amz-signature|x-goog-signature|x-amz-credential)=[^\s&"'}]+/i,
  /https?:\/\/[^\s/:]+:[^\s/@]+@/i,
  /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/,
  /(?:<\s*think(?:ing)?\b|<\s*scratchpad|chain[\s_-]?of[\s_-]?thought|hidden[\s_-]?reasoning|private[\s_-]?reasoning)/i
];
const IDENTIFIER = /[A-Za-z][A-Za-z0-9_-]{1,80}/g;
const SECRET_KEY_PARTS = new Set([
  'authorization', 'credential', 'credentials', 'password', 'passwd', 'secret', 'token'
]);
const QUALIFIED_KEY_PARTS = new Set([
  'api', 'access', 'aws', 'client', 'private', 'secret', 'session', 'signing'
]);
const AUTHORIZATION_HEADER = /\b(?:proxy[\s_-]+)?authorization(?:[\s_-]+header)?\s*(?::|=>|=)/i;
const DETACHED_AUTH_VALUE = /\b(?:Basic|Digest|Negotiate|NTLM|AWS4-HMAC-SHA256|ApiKey|Token)\s+\S{4,}/i;

function assignmentDelimiter(source, end) {
  let cursor = end;
  if (source[cursor] === '"' || source[cursor] === "'") cursor += 1;
  while (source[cursor] === ' ' || source[cursor] === '\t') cursor += 1;
  return source[cursor] === ':' || source[cursor] === '=';
}

function hasSensitiveAssignment(line) {
  const source = String(line || '');
  IDENTIFIER.lastIndex = 0;
  let match;
  while ((match = IDENTIFIER.exec(source)) !== null) {
    const before = match.index ? source[match.index - 1] : '';
    if (/[A-Za-z0-9_-]/.test(before) || !assignmentDelimiter(source, IDENTIFIER.lastIndex)) continue;
    const normalized = match[0].replace(/([a-z0-9])([A-Z])/g, '$1_$2')
      .toLowerCase().replace(/[^a-z0-9]+/g, '_');
    const parts = normalized.split('_').filter(Boolean);
    if (parts.some((part) => SECRET_KEY_PARTS.has(part))) return true;
    if (parts.includes('key') && parts.some((part) => QUALIFIED_KEY_PARTS.has(part))) return true;
  }
  return false;
}

function privateKeyArmor(line, marker) {
  const source = String(line || '').toUpperCase();
  const prefix = '-----' + marker + ' ';
  const start = source.indexOf(prefix);
  if (start < 0) return false;
  const labelStart = start + prefix.length;
  const labelEnd = source.indexOf('-----', labelStart);
  return labelEnd >= labelStart && source.slice(labelStart, labelEnd).includes('PRIVATE KEY');
}

function containsSecret(line) {
  const source = String(line || '');
  return AUTHORIZATION_HEADER.test(source) || hasSensitiveAssignment(source)
    || SECRETS.some((pattern) => pattern.test(source));
}

function omitSecretLines(lines) {
  const safe = [];
  let omitted = 0;
  let authorizationContinuation = false;
  let privateKeyBlock = false;
  for (const rawLine of lines) {
    const line = String(rawLine || '');
    if (privateKeyArmor(line, 'BEGIN')) privateKeyBlock = true;
    if (privateKeyBlock) {
      omitted += 1;
      authorizationContinuation = false;
      if (privateKeyArmor(line, 'END')) privateKeyBlock = false;
      continue;
    }
    if (authorizationContinuation) {
      if (!line.trim()) {
        authorizationContinuation = false;
        safe.push(line);
        continue;
      }
      if (/^\s/.test(line) || DETACHED_AUTH_VALUE.test(line)) {
        omitted += 1;
        authorizationContinuation = false;
        continue;
      }
      authorizationContinuation = false;
    }
    if (AUTHORIZATION_HEADER.test(line)) {
      omitted += 1;
      authorizationContinuation = /(?::|=>|=)\s*$/.test(line);
      continue;
    }
    if (containsSecret(line)) {
      omitted += 1;
      continue;
    }
    safe.push(line);
  }
  return { lines: safe, omitted };
}

function sanitizeLine(sanitizeCopyMdText, line) {
  let out = sanitizeCopyMdText(String(line || ''));
  out = out.replace(/\bghp_[A-Za-z0-9_]+\b/g, 'ghp_[REDACTED]');
  out = out.replace(/\bgithub_pat_[A-Za-z0-9_]+\b/g, 'github_pat_[REDACTED]');
  out = out.replace(/\bgho_[A-Za-z0-9_]+\b/g, 'gho_[REDACTED]');
  out = out.replace(/\b(?:proxy[\s_-]+)?authorization(?:[\s_-]+header)?\s*(?::|=>|=)\s*[^\r\n]+/gi, 'authorization: [REDACTED]');
  out = out.replace(/\b(?:api[_-]?key|token|secret|password|passwd)\s*[:=]\s*[^,\s\]]+/gi, '[REDACTED_CREDENTIAL]');
  out = out.replace(/\s+/g, ' ').trim();
  return out.length > 220 ? out.slice(0, 220) + '...[truncated]' : out;
}

module.exports = { containsSecret, omitSecretLines, sanitizeLine };
