#!/usr/bin/env python3
"""Validate portable skill metadata and local Markdown links without executing skills."""
from pathlib import Path
import argparse,json,re,sys
import yaml
from jsonschema import Draft202012Validator

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[3])
    args=parser.parse_args()
    root=args.root.resolve()
    skill_root=root/"skills"
    schema_path=skill_root/"00-master-orchestrator/schemas/skill-metadata.schema.json"
    validator=Draft202012Validator(json.loads(schema_path.read_text()))
    errors=[];count=0
    for path in sorted(skill_root.rglob("SKILL.md")):
        count+=1;raw=path.read_text()
        if not raw.startswith("---\n"):
            errors.append(f"{path.relative_to(root)}: missing frontmatter");continue
        try:
            front,body=raw[4:].split("\n---\n",1)
            metadata=yaml.safe_load(front)
        except Exception as exc:
            errors.append(f"{path.relative_to(root)}: {exc}");continue
        for err in validator.iter_errors(metadata):
            errors.append(f"{path.relative_to(root)}: {err.message}")
        if not re.search(r"^## Procedure$",body,re.M):
            errors.append(f"{path.relative_to(root)}: missing procedure")
        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)",body):
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:",link) or link.startswith("#"):
                continue
            target=(root/link.lstrip("/") if link.startswith("/") else path.parent/link).resolve()
            if root not in target.parents and target!=root:
                errors.append(f"{path.relative_to(root)}: link escapes repository: {link}")
            elif not target.exists():
                errors.append(f"{path.relative_to(root)}: broken link: {link}")
    if not count:errors.append("No skills found")
    print(json.dumps({"skill_count":count,"errors":errors},indent=2))
    return 1 if errors else 0
if __name__=="__main__":sys.exit(main())
