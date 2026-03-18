---
name: qwen_bulk_import_migration
description: Bulk import migration assistant for Python modules
version: 1.0_prototype
author: 0102
created: 2026-03-18
agents: [qwen]
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

**Version**: 1.0.0
**Agents**: qwen (planning), gemma (validation)
**Intent Type**: REFACTOR
**Promotion State**: production
**WSP Chain**: WSP 77, WSP 50, WSP 84, WSP 22

## Purpose

Migrate hardcoded values across multiple files to use a central registry import.
Uses Qwen for strategic planning and Gemma for validation.

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
1. Qwen: Parse migration spec, identify target files
2. Qwen: Generate import statement for each file
3. Qwen: Generate replacement code for each occurrence
4. Gemma: Validate syntax of generated code
5. Gemma: Check import doesn't create circular dependency
6. Apply changes (if not dry_run)
7. Update ModLogs per WSP 22
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
- **Validation**: Gemma validates each change before apply
- **Rollback**: Stores rollback script in case of issues
