'use strict';

const assert = require('assert');
const cp = require('child_process');
const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..', '..');
const governedDocuments = new Set([
  'extensions/reddog/INTERFACE.md',
  'extensions/reddog/README.md',
  'extensions/reddog/ROADMAP.md',
  'extensions/reddog/tests/README.md'
]);

function source(relative) {
  return fs.readFileSync(path.join(repoRoot, relative), 'utf8');
}

function baseSource(relative) {
  try {
    return cp.execFileSync('git', ['show', `HEAD:${relative}`], {
      cwd: repoRoot, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']
    });
  } catch (_err) { return ''; }
}

function physicalLines(content) {
  return content.replace(/\r\n/g, '\n').replace(/\n$/, '').split('\n').length;
}

function canonicalLines(content) {
  return physicalLines(content);
}

function maskJavaScript(content) {
  let output = '';
  let quote = '';
  let escaped = false;
  let lineComment = false;
  let blockComment = false;
  for (let index = 0; index < content.length; index += 1) {
    const char = content[index];
    const next = content[index + 1];
    if (char === '\n') { output += '\n'; lineComment = false; continue; }
    if (lineComment) { output += ' '; continue; }
    if (blockComment) {
      if (char === '*' && next === '/') { output += '  '; index += 1; blockComment = false; }
      else output += ' ';
      continue;
    }
    if (quote) {
      output += ' ';
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === quote) quote = '';
      continue;
    }
    if (char === '/' && next === '/') { output += '  '; index += 1; lineComment = true; }
    else if (char === '/' && next === '*') { output += '  '; index += 1; blockComment = true; }
    else if ('\'"`'.includes(char)) { output += ' '; quote = char; }
    else output += char;
  }
  return output;
}

function closingBrace(masked, opening) {
  let depth = 0;
  for (let index = opening; index < masked.length; index += 1) {
    if (masked[index] === '{') depth += 1;
    else if (masked[index] === '}' && --depth === 0) return index;
  }
  return -1;
}

function lineNumber(content, offset) {
  return content.slice(0, offset).split('\n').length;
}

function functionSpans(content) {
  const masked = maskJavaScript(content);
  const starts = [];
  const declarations = /\bfunction\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{/g;
  const arrows = /=>\s*\{/g;
  for (const [pattern, named] of [[declarations, true], [arrows, false]]) {
    let match;
    while ((match = pattern.exec(masked))) {
      const opening = masked.indexOf('{', match.index);
      const closing = closingBrace(masked, opening);
      if (closing >= 0) starts.push([match.index, closing, named ? match[1] : '']);
    }
  }
  return starts.map(([start, end, name]) => ({
    name,
    start: lineNumber(content, start),
    lines: lineNumber(content, end) - lineNumber(content, start) + 1
  }));
}

function assertJavaScriptLimits(relative) {
  const content = source(relative);
  if (relative === 'extensions/reddog/extension.js') {
    assert(canonicalLines(content) <= 8400, 'extension.js exceeds its reduced ceiling');
    const named = functionSpans(content);
    const wire = named.find((span) => span.name === 'wireFusionWebview');
    const call = named.find((span) => span.name === 'callFusion');
    assert(wire && wire.lines <= 581, 'wireFusionWebview exceeds 581 lines');
    assert(call && call.lines <= 180, 'callFusion exceeds its inherited ceiling');
    return;
  }
  assert(physicalLines(content) <= 400,
    relative + ' exceeds the candidate JavaScript 400-line ceiling');
  const spans = functionSpans(content);
  const baseline = functionSpans(baseSource(relative));
  let arrowIndex = 0;
  for (const span of spans) {
    const prior = span.name
      ? baseline.find((item) => item.name === span.name)
      : baseline.filter((item) => !item.name)[arrowIndex++];
    assert(span.lines <= 30 || (prior && span.lines <= prior.lines),
      relative + ':' + span.start + ' creates/grows candidate function debt');
  }
}

function changedCandidatePaths() {
  const commands = [
    ['diff', '--name-only', 'HEAD', '--', 'extensions/reddog'],
    ['ls-files', '--others', '--exclude-standard', '--', 'extensions/reddog']
  ];
  const found = new Set();
  for (const args of commands) {
    const output = cp.execFileSync('git', args, {
      cwd: repoRoot, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']
    });
    for (const relative of output.split(/\r?\n/)) {
      if (relative) found.add(relative.replace(/\\/g, '/'));
    }
  }
  return [...found].sort();
}

function assertDocumentLimits(relative) {
  assert(physicalLines(source(relative)) <= 1000,
    relative + ' exceeds the candidate documentation 1000-line ceiling');
}

const changedPaths = changedCandidatePaths();
const candidateJavaScript = changedPaths.filter((relative) => /\.(?:js|ts)$/.test(relative));
const candidateDocuments = changedPaths.filter((relative) => governedDocuments.has(relative));
assert(candidateJavaScript.length + candidateDocuments.length > 0,
  'candidate WSP 62 proof requires a changed/new JavaScript or governed-document surface');
for (const relative of candidateJavaScript) assertJavaScriptLimits(relative);
for (const relative of candidateDocuments) assertDocumentLimits(relative);

console.log('RedDog candidate WSP 62 file/function size proof: PASS');
console.log('Backend runtime WSP 62 compliance is a separate repository gate.');
