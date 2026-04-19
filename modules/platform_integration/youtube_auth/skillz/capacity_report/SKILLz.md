---
name: youtube_oauth_capacity_report
version: "1.0"
category: capability-uplift
autonomous: true
requires_012: false
evals: []
retirement_date: null
---

# youtube_oauth_capacity_report

## Purpose

Summarize effective YouTube API quota capacity after accounting for dead, exhausted, and healthy credential sets. Emit degraded-mode warning if capacity is reduced.

## Supervised Boundary (WSP 97)

- **Autonomous**: YES
- **Credential inspection**: NO
- **API calls**: NO (reads artifacts only)

## Input Sources

```
modules/platform_integration/youtube_auth/reports/oauth_credential_health.json
modules/platform_integration/youtube_auth/memory/quota_usage.json (if exists)
```

## Output

```yaml
report_time: ISO timestamp
capacity:
  total_configured_sets: 2
  operational_sets: [list of set IDs]
  dead_sets: [list of set IDs]
  quota_exhausted_today: [list of set IDs]
  
quota:
  daily_limit_per_set: 10000
  effective_daily_capacity: int  # operational_sets * 10000
  estimated_remaining_today: int | null  # if quota tracking available
  
status: full_capacity | degraded | critical | exhausted

warnings: [list of warning strings]

operator_actions:
  - action: str
    set_id: int
    command: str
```

## Capacity Status Definitions

| Status | Condition |
|--------|-----------|
| full_capacity | All configured sets operational |
| degraded | 1+ sets dead but some still operational |
| critical | Only 1 set operational |
| exhausted | All sets dead or quota exhausted |

## Example Output

```yaml
capacity:
  total_configured_sets: 2
  operational_sets: [10]
  dead_sets: [1]
  quota_exhausted_today: []
  
quota:
  daily_limit_per_set: 10000
  effective_daily_capacity: 10000
  
status: degraded

warnings:
  - "Set 1 is dead (token_expired_or_revoked) - 50% capacity loss"
  - "Running on single credential set - no failover available"

operator_actions:
  - action: "Reauthorize Set 1"
    set_id: 1
    command: "python modules/platform_integration/youtube_auth/scripts/authorize_set1.py"
```

## Trigger

- After oauth_health_check detects degraded capacity
- Scheduled capacity audit (e.g., daily)
- Manual `/youtube-quota-status` command
- AI Overseer quota warning threshold

## Integration Points

- **AI Overseer**: Capacity alerts
- **health_check**: Calls capacity_report for detailed breakdown
- **WRE**: Pattern memory for capacity degradation trends
- **DAE Operations**: Degraded mode decisions
