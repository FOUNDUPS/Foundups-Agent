---
name: qwen_bulk_import_migration
description: Bulk import migration assistant for Python modules
version: 1.0_prototype
author: 0102
created: 2026-03-18
agents: [qwen, gemma]
primary_agent: qwen
intent_type: REFACTORING
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: workflow
evals: []
trigger:
  manual
---
# Qwen Bulk Import Migration Skill

**Version**: 1.0_prototype
**Agents**: qwen/gemma are intended future roles; no model adapter is bound
**Intent Type**: REFACTORING
**Promotion State**: prototype
**WSP Chain**: WSP 77, WSP 50, WSP 84, WSP 22

## Purpose

Prototype deterministic migration planner for replacing hardcoded values with
central registry imports. The current executor does not call Qwen or Gemma.

## Use Cases

1. **Registry Migration**: Replace hardcoded IDs with central registry imports
2. **Import Consolidation**: Standardize imports across modules
3. **Config Externalization**: Move hardcoded values to env vars

## Input Schema

```json
{
  "migration_type": "registry_import",
  "search_patterns": ["1263645", "68706058"],
  "registry_module": "modules.infrastructure.shared_utilities.linkedin_account_registry",
  "registry_imports": ["get_company_id", "get_default_company"],
  "replacement_map": {
    "1263645": "get_company_id('foundups')",
    "68706058": "get_company_id('undaodu')"
  },
  "target_glob": "modules/**/*.py",
  "exclude_patterns": [".worktrees/", "__pycache__/", "linkedin_account_registry.py"],
  "dry_run": true
}
```

## Output Schema

```json
{
  "files_scanned": 150,
  "files_modified": 12,
  "replacements_made": 28,
  "validation_passed": true,
  "changes": [
    {
      "file": "path/to/file.py",
      "line": 42,
      "old": "COMPANY_ID = \"1263645\"",
      "new": "COMPANY_ID = get_company_id('foundups')"
    }
  ],
  "errors": []
}
```

## Execution Flow

```
1. Parse migration spec and identify target files deterministically
2. Generate configured imports and literal replacements
3. Apply the current balanced-parentheses rule check
4. Apply changes only when `dry_run` is explicitly false
5. Leave independent syntax, circular-dependency, test, and review gates to
   the caller; they are not implemented by this prototype
```

## CLI Usage

```bash
# Dry run - preview changes
python -m modules.infrastructure.wre_core.skillz.qwen_bulk_import_migration.executor \
  --spec migration_spec.json --dry-run

# Execute migration
python -m modules.infrastructure.wre_core.skillz.qwen_bulk_import_migration.executor \
  --spec migration_spec.json

# LinkedIn registry migration (built-in)
python -m modules.infrastructure.wre_core.skillz.qwen_bulk_import_migration.executor \
  --preset linkedin_registry --dry-run
```

## Built-in Presets

### linkedin_registry
Migrates hardcoded LinkedIn company IDs to central registry.

### youtube_registry
Migrates hardcoded YouTube channel IDs to central registry.

## Safety

- **Dry run by default**: Must explicitly set `dry_run: false` to apply changes
- **Backup**: Creates .bak files before modification
- **Validation**: Current rule check is not Gemma or full syntax validation
- **Recovery aid**: Creates `.bak` files; no governed rollback script exists
