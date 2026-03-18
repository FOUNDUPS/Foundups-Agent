---
name: holo-search
description: HoloIndex semantic search integration for codebase navigation
user-invocable: true
command-dispatch: tool
command-tool: bash
command-arg-mode: raw
category: workflow
evals: []
---
# HoloIndex Search Skill

Use this skill to search the Foundups codebase semantically BEFORE making any changes.

## Quick Search

```bash
cd O:/Foundups-Agent && python holo_index.py --search "{query}" --limit 5
```

## Search Types

### Code Search
```bash
python holo_index.py --search "function name or pattern" --type code
```

### Documentation Search
```bash
python holo_index.py --search "concept or protocol" --type docs
```

### WSP Search
```bash
python holo_index.py --search "WSP number or topic" --type wsp
```

## CRITICAL RULE

**NEVER create new files without first searching for existing implementations.**

This is the "no vibecoding" principle from WSP framework.
