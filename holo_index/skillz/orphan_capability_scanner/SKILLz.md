---
name: orphan_capability_scanner
description: Scan codebase for CLI capabilities without WRE connection and generate SKILLz.md templates
version: 1.0
author: 0102
created: 2026-03-08
agents: [qwen]
primary_agent: qwen
intent_type: AUDIT
promotion_state: production
pattern_fidelity_threshold: 0.90
trigger:
  cadence: daily
  event: post_commit
category: workflow
evals: []
---
# Orphan Capability Scanner

**Purpose**: Find code with CLI entrypoints (`if __name__ == "__main__"`) that isn't WRE-connected (no SKILLz.md) and generate connection templates.

**Problem Solved**: "Tons of code sitting waiting for 012 to use... 012 will never use it."

---

## What This Skill Does

1. **Scans** all `modules/`, `holo_index/`, `automation/`, `tools/` directories
2. **Finds** Python files with `if __name__ == "__main__"` blocks
3. **Loads** SKILLz.md registry (all registered skills)
4. **Loads** file-specific `*_SKILLz.md` bindings (CF4)
5. **Cross-references** to identify orphans (CLI without SKILLz.md)
6. **Generates** SKILLz.md templates for top orphans

---

## Binding Types (CF4)

The scanner supports two binding mechanisms:

### Directory-Level Binding (original)
- `SKILLz.md` binds all CLI entrypoints in its directory/subtree
- Good for cohesive modules where all files share a contract

### File-Specific Binding (CF4)
- `<name>_SKILLz.md` binds exactly one CLI entrypoint
- Requires `target_file:` frontmatter field
- Falls back to filename inference if unambiguous
- Good for distinct commands sharing a directory

Example file-specific binding:
```yaml
---
name: m2m_compression_sentinel
target_file: m2m_compression_sentinel.py
---
```

**Precedence**: File-specific bindings take precedence over directory-level

---

## Execution

```bash
# Full scan with human-readable output
python holo_index/skillz/orphan_capability_scanner/executor.py --scan

# Generate templates for top N orphans
python holo_index/skillz/orphan_capability_scanner/executor.py --generate 10

# JSON output for OpenClaw/WRE consumption
python holo_index/skillz/orphan_capability_scanner/executor.py --scan --json

# Summary only (for dashboards)
python holo_index/skillz/orphan_capability_scanner/executor.py --summary
```

---

## WRE Connection

- **Trigger**: `cadence:daily` + `event:post_commit`
- **Agent**: Qwen (strategic analysis of orphan priority)
- **JSON Output**: Yes (WSP 103 compliant)
- **PatternMemory**: Stores scan results for trend analysis

---

## Output Schema (JSON)

```json
{
  "scan_timestamp": "2026-04-19T...",
  "total_cli_entrypoints": 687,
  "registered_skills": 113,
  "file_specific_bindings": 1,
  "orphan_count": 567,
  "wre_connected_count": 120,
  "templates_generated": 0,
  "scan_duration_ms": 15000,
  "file_specific_warnings": [],
  "orphans": [
    {
      "path": "modules/infrastructure/wre_core/...",
      "module_name": "modules.infrastructure.wre_core...",
      "line_count": 1814,
      "category": "infrastructure",
      "has_json_flag": false,
      "suggested_trigger": "manual",
      "binding_type": "none"
    }
  ]
}
```

New CF4 fields:
- `file_specific_bindings`: Count of `*_SKILLz.md` bindings
- `file_specific_warnings`: Ambiguous/missing target warnings
- `binding_type`: `"directory"` | `"file_specific"` | `"none"`

---

## Autonomy Test

**Question**: Can N compute cycles complete without 012?

**Answer**: YES
- Runs on daily cadence or post-commit event
- Produces JSON for WRE consumption
- Generates actionable templates
- No hang actions (fully autonomous)

---

## Benchmark Test Cases

### Test 1: Fresh Scan
- **Input**: Run `--scan` on full codebase
- **Expected**: Detects ~1200+ orphans, completes <60s
- **Pass Criteria**: JSON parseable, orphan_count > 0

### Test 2: Template Generation
- **Input**: Run `--generate 5`
- **Expected**: Creates 5 SKILLz.md templates in `reports/orphan_skillz_templates/`
- **Pass Criteria**: Files exist, valid YAML frontmatter

### Test 3: Incremental Scan
- **Input**: Add new SKILLz.md, re-run scan
- **Expected**: Orphan count decreases by 1
- **Pass Criteria**: Delta matches expectation

---

## Related WSPs

- **WSP 77**: Agent Coordination (Qwen primary)
- **WSP 88**: Orphan Analysis (import chain tracing)
- **WSP 103**: CLI Standard (--json flag)
- **WSP 91**: Observability (scan metrics)

---

## Dependencies

- Python 3.10+
- No external packages (stdlib only)
- Access to `modules/`, `holo_index/` directories

---

*This skill is itself WRE-connected - not an orphan.*
*Created: 2026-03-08 | Author: 0102*
