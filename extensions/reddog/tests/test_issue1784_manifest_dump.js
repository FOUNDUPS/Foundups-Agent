'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..');
const manifestPath = path.join(repoRoot, 'scripts', 'reddog_backend_manifest.json');
const registryRelative = 'modules/infrastructure/wre_core/skillz/skills_registry_v2.json';
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const registryBytes = fs.readFileSync(path.join(repoRoot, registryRelative));
const registryDigest = crypto.createHash('sha256')
  .update(Buffer.from(registryBytes.toString('utf8').replace(/\r\n/g, '\n'), 'utf8'))
  .digest('hex');
manifest.required_runtime_sha256[registryRelative] = registryDigest;
const bytes = Buffer.from(JSON.stringify(manifest, null, 2) + '\n', 'utf8');
console.log('[issue-1784-manifest-base64]' + bytes.toString('base64'));
