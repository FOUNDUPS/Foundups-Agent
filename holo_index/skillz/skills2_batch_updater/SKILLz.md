---
name: skills2_batch_updater
description: Batch update all SKILL.md and SKILLz.md files with Skills 2.0 fields (category, evals, retirement_date)
version: 1.0
author: 0102
created: 2026-03-15
agents: [qwen]
primary_agent: qwen
intent_type: MAINTENANCE
promotion_state: production
pattern_fidelity_threshold: 0.90
trigger:
  event: schema_update
category: workflow
evals:
  - name: dry_run_scan
    input: "--scan"
    expected: "lists files, no modifications"
  - name: batch_update
    input: "--update"
    expected: "updates files, reports count"
retirement_date: null
---

# Skills 2.0 Batch Updater

**Purpose**: Update all skill files (SKILL.md and SKILLz.md) with Skills 2.0 compliance fields.

**Skills 2.0 Fields Added**:
- `category`: `workflow` or `capability-uplift`
- `evals`: `[]` (benchmark test cases)
- `retirement_date`: `null` (for capability-uplift skills only)

---

## Execution

```bash
# Scan only (dry run)
python holo_index/skillz/skills2_batch_updater/executor.py --scan

# Dry run (show what would change)
python holo_index/skillz/skills2_batch_updater/executor.py --dry-run

# Apply updates
python holo_index/skillz/skills2_batch_updater/executor.py --update

# JSON output
python holo_index/skillz/skills2_batch_updater/executor.py --scan --json
```

---

## Category Detection

**Capability Uplift** (fills model gaps):
- PDF processing, presentations, Excel, Word
- Image/video/audio processing, OCR
- Has `retirement_date` field

**Workflow** (automates tasks):
- Orchestration, DAE, monitoring, audit
- Enhancement, refactoring, compliance
- Content generation, moderation

---

## WRE Connection

- **Trigger**: `event:schema_update`
- **Agent**: Qwen (batch file operations)
- **JSON Output**: Yes

---

## Autonomy Test

**Can N compute cycles complete without 012?** YES
- Scans all skill files automatically
- Detects category from name/description
- Applies standard fields consistently

---

*WSP Compliance*: WSP 97 (CoT/CoR), WSP 103 (CLI Standard)
