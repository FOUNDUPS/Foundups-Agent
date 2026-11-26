'use strict';

// Pure source binding only: no filesystem, Git, network, allocation or publication.
// The caller must resolve its reviewed Git source and supply any known Hosting ID.
const { createHash } = require('node:crypto');

const CONTEXT_KEYS = ['sourceSha', 'channelId', 'projectionSource', 'discoveryCatalog', 'probeSource', 'hostingVersion'];
const META_KEYS = ['source_sha', 'app_source_sha', 'channel_id', 'mall_build', 'discovery_generation', 'probe_sha256', 'hosting_version', 'stage_status'];
const own = (value, key) => Object.prototype.hasOwnProperty.call(value, key);

function dataObject(value, allowed) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const proto = Object.getPrototypeOf(value);
  if (proto !== null && proto !== Object.prototype) return false;
  return Reflect.ownKeys(value).every(key => {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    return typeof key === 'string' && (!allowed || allowed.includes(key)) && descriptor?.enumerable && own(descriptor, 'value');
  });
}

function invalid(message) { throw new TypeError('Invalid preview metadata context: ' + message); }

// A small lexical reader for the fixed JS declaration owner, not a JS evaluator.
// Comments, quoted strings, regex literals and templates cannot supply a build.
function buildFromProjection(source) {
  if (typeof source !== 'string' || !source.length || source.length > 2 * 1024 * 1024) invalid('projection source');
  let at = 0;
  const tokens = [];
  const regexPrefix = token => !token ||
    token.kind === 'controlEnd' ||
    (token.kind === 'punct' && ['=', '(', '[', '{', '}', ',', ':', ';', '!', '?', '&', '|', '+', '-', '*', '%', '~'].includes(token.value)) ||
    (token.kind === 'word' && ['return', 'throw', 'case', 'delete', 'void', 'typeof', 'in', 'of', 'new', 'yield', 'await', 'else', 'do'].includes(token.value));

  function quoted(quote) {
    const start = at++;
    while (at < source.length) {
      const char = source[at++];
      if (char === '\\') { at++; continue; }
      if (char === quote) return source.slice(start, at);
      if (char === '\n' || char === '\r') invalid('unterminated JS string');
    }
    invalid('unterminated JS string');
  }

  function regexLiteral() {
    at++;
    let characterClass = false;
    while (at < source.length) {
      const char = source[at++];
      if (char === '\\') { at++; continue; }
      if (char === '[') characterClass = true;
      else if (char === ']') characterClass = false;
      else if (char === '/' && !characterClass) {
        while (/[a-z]/i.test(source[at] || '') && at < source.length) at++;
        return;
      } else if (char === '\n' || char === '\r') invalid('unterminated JS regex');
    }
    invalid('unterminated JS regex');
  }

  function template() {
    at++;
    while (at < source.length) {
      const char = source[at++];
      if (char === '\\') { at++; continue; }
      if (char === '`') return;
      if (char === '$' && source[at] === '{') { at++; scan(false, true); }
    }
    invalid('unterminated JS template');
  }

  function scan(collect, interpolation = false) {
    let depth = 0;
    let previous = null;
    let beforePrevious = null;
    const parentheses = [];
    while (at < source.length) {
      const char = source[at];
      if (/\s/.test(char)) { at++; continue; }
      if (char === '/' && source[at + 1] === '/') {
        at += 2;
        while (at < source.length && !'\r\n'.includes(source[at])) at++;
        continue;
      }
      if (char === '/' && source[at + 1] === '*') {
        const end = source.indexOf('*/', at + 2);
        if (end === -1) invalid('unterminated JS comment');
        at = end + 2; continue;
      }
      let token;
      if (char === '"' || char === "'") token = { kind: 'string', value: quoted(char) };
      else if (char === '`') { template(); token = { kind: 'other', value: 'template' }; }
      else if (char === '/' && regexPrefix(previous)) { regexLiteral(); token = { kind: 'other', value: 'regex' }; }
      else if (/[A-Za-z_$]/.test(char)) {
        const start = at++;
        while (at < source.length && /[A-Za-z0-9_$]/.test(source[at])) at++;
        token = { kind: 'word', value: source.slice(start, at) };
      } else {
        at++;
        if (interpolation && char === '}' && depth === 0) return;
        if (char === '{') depth++;
        else if (char === '}') depth--;
        if (char === '(') parentheses.push(previous?.kind === 'word' &&
          (['if', 'while', 'for', 'with', 'switch', 'catch'].includes(previous.value) ||
           (previous.value === 'await' && beforePrevious?.value === 'for')));
        const controlEnd = char === ')' && parentheses.pop() === true;
        token = { kind: controlEnd ? 'controlEnd' : 'punct', value: char };
      }
      if (collect) tokens.push(token);
      beforePrevious = previous;
      previous = token;
    }
    if (interpolation) invalid('unterminated template interpolation');
  }
  scan(true);
  const builds = [];
  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i].kind !== 'word' || tokens[i].value !== 'const' ||
        tokens[i + 1]?.kind !== 'word' || tokens[i + 1].value !== 'mallBuild') continue;
    const literal = tokens[i + 3];
    const match = literal?.kind === 'string' && /^(['"])(v[0-9]{1,4})\1$/.exec(literal.value);
    if (tokens[i + 2]?.value !== '=' || !match || tokens[i + 4]?.value !== ';') invalid('nonliteral mallBuild declaration');
    builds.push(match[2]);
  }
  if (builds.length !== 1) invalid('one mallBuild declaration required');
  return builds[0];
}

function buildMetadata(context) {
  if (!dataObject(context, CONTEXT_KEYS)) invalid('shape');
  if (!CONTEXT_KEYS.slice(0, 5).every(key => own(context, key))) invalid('required own inputs');
  if (typeof context.sourceSha !== 'string' || !/^[a-f0-9]{40}$/.test(context.sourceSha)) invalid('full source SHA');
  if (typeof context.channelId !== 'string' || !/^[a-z][a-z0-9_-]{0,63}$/.test(context.channelId) ||
      context.channelId === 'live') invalid('non-live preview channel');
  if (!dataObject(context.discoveryCatalog) || !own(context.discoveryCatalog, 'generation') ||
      typeof context.discoveryCatalog.generation !== 'string' || !/^[a-f0-9]{64}$/.test(context.discoveryCatalog.generation)) invalid('discovery generation');
  const probe = context.probeSource;
  if ((!Buffer.isBuffer(probe) && typeof probe !== 'string') || !probe.length ||
      Buffer.byteLength(probe) > 16 * 1024 * 1024) invalid('probe bytes');
  let hosting = 'unverified';
  if (own(context, 'hostingVersion') && context.hostingVersion !== undefined) {
    if (typeof context.hostingVersion !== 'string' || !/^[a-f0-9]{8,40}$/.test(context.hostingVersion)) invalid('allocated Hosting ID');
    hosting = context.hostingVersion;
  }
  return Object.freeze({
    source_sha: context.sourceSha,
    app_source_sha: context.sourceSha,
    channel_id: context.channelId,
    mall_build: buildFromProjection(context.projectionSource),
    discovery_generation: context.discoveryCatalog.generation,
    probe_sha256: createHash('sha256').update(probe).digest('hex'),
    hosting_version: hosting,
    stage_status: 'SOURCE_BOUND_ARTIFACT'
  });
}

function validateMetadata(data, context, options = {}) {
  try {
    if (!dataObject(options, ['requireHosting']) ||
        (own(options, 'requireHosting') && typeof options.requireHosting !== 'boolean') ||
        !dataObject(data, META_KEYS) || Reflect.ownKeys(data).length !== META_KEYS.length) return false;
    const expected = buildMetadata(context);
    if (own(options, 'requireHosting') && options.requireHosting === true && expected.hosting_version === 'unverified') return false;
    return META_KEYS.every(key => own(data, key) && data[key] === expected[key]);
  } catch (error) { return false; }
}

module.exports = { buildMetadata, validateMetadata };
