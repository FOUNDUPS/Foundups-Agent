#!/usr/bin/env python3
"""Bind review scope to repository bytes, not legal truth or reviewer credentials."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def validate_reviews(manifest,root=ROOT):
 errors=[]
 catalog={d['path'] for d in json.loads((root/'web/documents.json').read_text())}
 rows=manifest.get('documents',[])
 paths=[x.get('path') for x in rows]
 if len(paths)!=len(set(paths)) or set(paths)!=catalog:errors.append('review catalog mismatch')
 for row in rows:
  rel=row.get('path','');path=root/rel
  if rel not in catalog or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
   errors.append('invalid review path');continue
  if hashlib.sha256(path.read_bytes()).hexdigest()!=row.get('sha256'):errors.append('stale review bytes: '+rel)
  if row.get('human_legal_review')!='pending':errors.append('unrecorded human legal approval')
  if not isinstance(row.get('scope'),str) or not row['scope'].strip():errors.append('missing review scope')
 return errors
if __name__=='__main__':
 data=json.loads((ROOT/'data/document-reviews.json').read_text());errors=validate_reviews(data)
 print(json.dumps({'scope_digest_validation':not errors,'errors':errors,'professional_legal_signoff':False}));raise SystemExit(bool(errors))
