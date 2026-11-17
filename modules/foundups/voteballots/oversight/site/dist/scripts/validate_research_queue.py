#!/usr/bin/env python3
"""Validate read-only planning tickets. Does not assign work or establish truth."""
import argparse,json
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker
from validate_evidence import public_url
ROOT=Path(__file__).resolve().parents[1]
def validate_queue(queue):
 schema=json.loads((ROOT/'schemas/research-queue.schema.json').read_text())
 errors=[e.message for e in Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(queue)]
 if errors:return errors
 ids=[t['ticket_id'] for t in queue['tickets']]
 if len(ids)!=len(set(ids)):errors.append('duplicate ticket IDs')
 for t in queue['tickets']:
  for url in t['allowed_sources']:
   try:safe=public_url(url)
   except ValueError:safe=False
   if not safe:errors.append('unsafe public-source URL')
  if t['worker'] is not None or t['reviewer'] is not None:errors.append('planning board cannot assert runtime assignments')
  if t['human_release']:errors.append('planning task cannot authorize publication')
 return errors
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('path',nargs='?',type=Path,default=ROOT/'investigations/research-queue.json');args=p.parse_args()
 errors=validate_queue(json.loads(args.path.read_text()));print(json.dumps({'planning_validation':not errors,'errors':errors,'runtime_admission':False,'truth_verification':False}));raise SystemExit(bool(errors))
