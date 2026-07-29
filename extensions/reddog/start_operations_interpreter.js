'use strict';

const fs = require('fs');
const path = require('path');

function approved(interpreter, repoRoot) {
  if (!path.isAbsolute(String(interpreter || ''))) return '';
  if (!path.isAbsolute(String(repoRoot || ''))) return '';
  try {
    const root = fs.realpathSync(path.resolve(repoRoot, '.venv'));
    const executable = fs.realpathSync(path.resolve(interpreter));
    const relative = path.relative(root, executable);
    const contained = relative && !relative.startsWith('..' + path.sep)
      && !path.isAbsolute(relative);
    return contained && fs.statSync(executable).isFile() ? executable : '';
  } catch (_error) {
    return '';
  }
}

module.exports = { approved };
