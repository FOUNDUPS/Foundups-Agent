---
name: youtube_oauth_health_check
version: "1.0"
category: capability-uplift
autonomous: true
requires_012: false
evals: []
retirement_date: null
---

# youtube_oauth_health_check

## Purpose

Read the redacted `oauth_credential_health.json` artifact, classify token/capacity state, and recommend next operator action.

## Supervised Boundary (WSP 97)

- **Autonomous**: YES
- **Credential inspection**: NO (reads artifact, not tokens)
- **Credential mutation**: NO

## Input

None required. Reads from:
```
modules/platform_integration/youtube_auth/reports/oauth_credential_health.json
```

## Output

```yaml
status: healthy | degraded | critical
sets:
  operational: [list of set IDs]
  dead: [list of set IDs]
  quota_exhausted: [list of set IDs]
effective_daily_quota: int
operator_action: null | "reauth required" | "wait for quota reset"
recommended_skill: null | supervised_reauth | capacity_report
```

## Allowed Claims

- "Token refresh valid" (if status=healthy in artifact)
- "Capacity degraded" (if dead sets > 0)
- "Operator action required" (if reauth_needed)

## Forbidden Claims

- "OAuth fixed" without artifact verification
- Any claim about token contents
- Any claim about which Google account owns a set (use identity_verify for that)

## Trigger

- AI Overseer detects oauth preflight fail
- Scheduled health check
- Manual `/youtube-oauth-status` command

## Example Invocation

```python
# AI Overseer hook
if preflight_failed:
    result = invoke_skill("youtube_oauth_health_check")
    if result["status"] == "critical":
        create_task("supervised_reauth", requires_012=True)
```

## Integration Points

- **AI Overseer**: Preflight failure hook
- **Claw/OpenClaw**: Status query
- **WRE**: Pattern memory for failure trends
