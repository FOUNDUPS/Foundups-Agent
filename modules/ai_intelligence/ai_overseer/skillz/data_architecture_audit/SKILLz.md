---
name: data_architecture_audit
description: Audit data architecture for orphan tables and schema issues
version: 1.0_prototype
author: 0102
created: 2026-03-18
agents: [qwen, gemma]
primary_agent: qwen
intent_type: AUDIT
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: workflow
evals: []
trigger:
  cadence: weekly
---
# Data Architecture Audit Skillz

## Overview
Qwen-orchestrated skillz for WSP 78 compliance auditing of FoundUps data architecture.

**Status**: Implemented
**Executor**: `executor.py`

## Invocation
```
/audit-data [scope]
```

**Scopes**:
- `core` - Core operational stores only (default)
- `full` - All SQLite files including satellites
- `sim` - Simulator stores only
- `events` - FAM/DAE event stores only

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    /audit-data Skill                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Phase 1: SQLite Scanner (Python, no LLM)                   │
│  ├── Run sqlite_audit.run_sqlite_audit()                    │
│  ├── Collect pragma states, integrity, table counts         │
│  └── Output: audit_raw.json                                 │
│                                                              │
│  Phase 2: WSP 78 Checker (Gemma 270M)                       │
│  ├── Binary compliance checks per requirement               │
│  ├── Input: audit_raw.json + WSP 78 checklist               │
│  └── Output: compliance_results.json (pass/fail per item)   │
│                                                              │
│  Phase 3: Gap Analyzer (Qwen 1.5B)                          │
│  ├── Identify missing documentation                         │
│  ├── Flag satellite stores without retention policy         │
│  └── Output: gaps.json                                      │
│                                                              │
│  Phase 4: Report Generator (Qwen 1.5B)                      │
│  ├── Synthesize findings into structured report             │
│  ├── Generate patch recommendations                         │
│  └── Output: audit_report.json + audit_report.md            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## WSP 78 Compliance Checks

| Check ID | Description | Method |
|----------|-------------|--------|
| WSP78-01 | WAL mode on long-lived DBs | `PRAGMA journal_mode` |
| WSP78-02 | foreign_keys=ON per connection | `PRAGMA foreign_keys` after enable |
| WSP78-03 | busy_timeout configured | `PRAGMA busy_timeout` |
| WSP78-04 | Event store dedupe keys | Schema inspection |
| WSP78-05 | Event store sequence monotonic | `SELECT MAX(sequence_id)` |
| WSP78-06 | JSONL/SQLite parity | Line count vs row count |
| WSP78-07 | Satellite stores documented | Check for SATELLITE_STORES.md |
| WSP78-08 | Namespace contract | Table prefix validation |

## Token Budget

| Phase | Agent | Budget |
|-------|-------|--------|
| Phase 1 | Python | 0 tokens |
| Phase 2 | Gemma | 100-200 tokens |
| Phase 3 | Qwen | 200-400 tokens |
| Phase 4 | Qwen | 300-500 tokens |
| **Total** | | **600-1100 tokens** |

## Output Schema

```json
{
  "audit_id": "audit_2026-02-22_001",
  "scope": "core",
  "generated_at": "2026-02-22T12:00:00Z",
  "summary": {
    "stores_audited": 6,
    "compliance_score": 0.875,
    "critical_findings": 1,
    "warnings": 2
  },
  "compliance": {
    "WSP78-01": {"status": "pass", "evidence": "..."},
    "WSP78-02": {"status": "pass", "evidence": "..."}
  },
  "gaps": [
    {"type": "missing_doc", "path": "...", "recommendation": "..."}
  ],
  "patches": [
    {"file": "...", "action": "...", "priority": "critical"}
  ]
}
```

## Dependencies

- `modules/infrastructure/database/src/sqlite_audit.py` - Core scanner
- `holo_index/models/gemma-3-270m-it-Q4_K_M.gguf` - Gemma model
- LM Studio or llama_cpp for Qwen inference

## WSP Compliance

- WSP 78: Database Architecture (this skill audits compliance)
- WSP 96: WRE Skills Protocol (skill structure)
- WSP 77: Agent Coordination (Qwen/Gemma phases)

## Future Extensions

1. **Scheduled audits**: Run daily via DAEmon heartbeat
2. **Drift detection**: Compare current vs baseline
3. **Auto-remediation**: Apply safe patches automatically
4. **Blockchain readiness**: Layer D settlement connector audit
