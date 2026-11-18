#!/usr/bin/env python3
"""Export repository skills with two-key frontmatter; never install them."""
from pathlib import Path
import argparse,json,shutil,sys
import yaml

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[3])
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    root=args.root.resolve(); destination=args.output.resolve()
    source=root/'skills'
    if destination==source or source in destination.parents:
        parser.error('Output must be outside the source skill tree')
    if destination.exists():
        parser.error('Output must not already exist; exports never overwrite files')
    shutil.copytree(source,destination)
    manifest=[]
    for path in sorted(destination.rglob('SKILL.md')):
        raw=path.read_text()
        if not raw.startswith('---\n'):
            parser.error(f'Missing frontmatter: {path}')
        front,body=raw[4:].split('\n---\n',1)
        metadata=yaml.safe_load(front)
        essential={k:metadata[k] for k in ('name','description')}
        extended={k:metadata[k] for k in ('triggers','inputs','outputs','required_citations')}
        body+='\n## Portable task metadata\n\n'
        for key,values in extended.items():
            body+='### '+key.replace('_',' ').capitalize()+'\n\n'
            body+=''.join('- '+str(value)+'\n' for value in values)+'\n'
        path.write_text('---\n'+yaml.safe_dump(essential,sort_keys=False,width=1000)+'---\n'+body)
        manifest.append({'name':essential['name'],'path':str(path.relative_to(destination))})
    (destination/'skill-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'skills_exported':len(manifest),'output':str(destination),'installed':False}))
    return 0
if __name__=='__main__':sys.exit(main())
