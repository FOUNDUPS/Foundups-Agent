---
name: security_scan
description: Autonomous security vulnerability scanning via CLI tools
version: 1.0.0
author: 0102
created: 2026-04-18
agents: [autonomous]
primary_agent: autonomous
intent_type: SECURITY_AUDIT
promotion_state: prototype
pattern_fidelity_threshold: 0.90
category: capability-uplift
evals: []
retirement_date: null
trigger:
  manual
---
# Security Scan Skill

**Version**: 1.0.0
**Agents**: autonomous (no LLM required for scan execution)
**Intent Type**: SECURITY_AUDIT
**Promotion State**: prototype
**WSP Chain**: WSP 97, WSP 77, WSP 84

## Purpose

WRE skill wrapper for autonomous security scanning.
Wraps SEC1 (scanner) for execution and SEC2 (policy) for routing decisions.

## Architecture

```
SEC1 (infrastructure/security_scanner)  → subprocess execution, JSON output
SEC2 (ai_overseer/vulnerability_scan_policy) → severity routing, 012 gates
SEC3 (this skill) → orchestration wrapper
```

## Tools Supported

| Tool | Type | Description |
|------|------|-------------|
| snyk | SCA/SAST | Dependency and code scanning |
| trivy | SCA | Container and filesystem scanning |
| semgrep | SAST | Static analysis with patterns |
| all | Aggregate | Run all available tools |

## Input Schema

```json
{
  "tool": "snyk|trivy|semgrep|all",
  "target": "."
}
```

## Output Schema

```json
{
  "generated_at": "2026-04-18T12:00:00Z",
  "scan_tool": "snyk",
  "target": ".",
  "tool_available": true,
  "scan_status": "completed|tool_unavailable|error",
  "findings": [...],
  "max_severity": "critical|high|medium|low|info",
  "total_findings": 5,
  "critical_count": 1,
  "high_count": 2,
  "policy_decision": "gate_012|modlog_only|report_only|ignore",
  "requires_012": true,
  "recommended_next_action": "escalate_012|log_modlog|review_report|none",
  "raw_report_path": "modules/infrastructure/reports/security/snyk_scan_20260418_120000.json",
  "error_message": null
}
```

## CLI Usage

```bash
# Scan with snyk
python -m modules.infrastructure.wre_core.skillz.security_scan.executor snyk --target .

# Scan with all available tools
python -m modules.infrastructure.wre_core.skillz.security_scan.executor all

# Save report to file
python -m modules.infrastructure.wre_core.skillz.security_scan.executor trivy --output report.json
```

## Policy Routing

| Severity | Default Escalation | 012 Gate |
|----------|-------------------|----------|
| CRITICAL | gate_012 | YES (hardcoded) |
| HIGH | modlog_only | NO |
| MEDIUM | report_only | NO |
| LOW | report_only | NO |
| INFO | ignore | NO |

**INVARIANT**: CRITICAL severity ALWAYS requires 012 confirmation.

## Truthful Reporting

- Missing CLI tools reported as `tool_available: false`, not failure
- No scan results fabricated
- Policy decisions reflect actual findings

## Out of Scope

- HoloDAE triggers (SEC4)
- Auto-remediation
- Qwen/Gemma fix generation
- CLI tool installation
