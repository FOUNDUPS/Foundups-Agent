'use strict';

const fs = require('fs');
const path = require('path');

function contained(parent, candidate) {
  const relative = path.relative(parent, candidate);
  return relative && !relative.startsWith('..' + path.sep)
    && !path.isAbsolute(relative);
}

function sitePackages(venvRoot) {
  const candidates = [path.join(venvRoot, 'Lib', 'site-packages')];
  const lib = path.join(venvRoot, 'lib');
  if (fs.existsSync(lib)) {
    for (const name of fs.readdirSync(lib)) {
      if (/^python\d+\.\d+$/.test(name)) {
        candidates.push(path.join(lib, name, 'site-packages'));
      }
    }
  }
  const accepted = candidates.filter((candidate) => {
    if (!fs.existsSync(candidate)) return false;
    const real = fs.realpathSync(candidate);
    return contained(venvRoot, real) && fs.statSync(real).isDirectory();
  });
  return accepted.length === 1 ? fs.realpathSync(accepted[0]) : '';
}

function approved(interpreter, repoRoot) {
  if (!path.isAbsolute(String(interpreter || ''))) return '';
  if (!path.isAbsolute(String(repoRoot || ''))) return '';
  try {
    const repo = fs.realpathSync(path.resolve(repoRoot));
    const venvPath = path.resolve(repo, '.venv');
    if (fs.lstatSync(venvPath).isSymbolicLink()) return '';
    const root = fs.realpathSync(venvPath);
    if (!contained(repo, root)) return '';
    const executable = fs.realpathSync(path.resolve(interpreter));
    const dependencies = sitePackages(root);
    if (!contained(root, executable) || !fs.statSync(executable).isFile()) {
      return '';
    }
    if (!dependencies) return '';
    return {
      interpreter: executable,
      repoRoot: repo,
      sitePackages: dependencies
    };
  } catch (_error) {
    return '';
  }
}

module.exports = { approved, contained, sitePackages };
