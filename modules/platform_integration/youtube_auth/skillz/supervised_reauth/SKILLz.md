---
name: youtube_oauth_supervised_reauth
version: "1.0"
category: workflow
autonomous: false
requires_012: true
evals: []
retirement_date: null
---

# youtube_oauth_supervised_reauth

## Purpose

Guide 012 through opening the correct authorize script for a credential set. Worker assists but NEVER performs credential entry.

## Supervised Boundary (WSP 97)

- **Autonomous**: PARTIAL (can prepare, cannot execute without 012)
- **Credential inspection**: NO
- **Credential mutation**: NO (012 performs OAuth in browser)
- **Browser control**: NO (script opens browser, 012 interacts)

## Input

```yaml
set_id: 1 | 10
reason: "invalid_grant" | "identity_mismatch" | "operator_requested"
```

## Workflow

1. **Validate set_id** (must be 1 or 10)
2. **Determine browser**:
   - Set 1 = Chrome (UnDaoDu / Move2Japan)
   - Set 10 = Edge (FoundUps / antifaFM)
3. **Display guidance to 012**:
   ```
   Set 1 requires Chrome browser with UnDaoDu Google account
   Set 10 requires Edge browser with FoundUps Google account
   ```
4. **Wait for 012 confirmation**
5. **Run authorize script** (only when 012 confirms):
   ```bash
   python modules/platform_integration/youtube_auth/scripts/authorize_set{N}.py
   ```
6. **Observe output** (do not parse tokens)
7. **Invoke identity_verify** after completion
8. **Report result**

## Output

```yaml
action_taken: script_launched | aborted_by_012 | error
set_id: int
browser: Chrome | Edge
identity_verified: true | false | pending
follow_up_skill: identity_verify
```

## Allowed Actions

- Open runbook documentation
- Run authorize script WHEN 012 approves
- Display account selection guidance
- Read redacted status after completion
- Write durable event/artifact

## Forbidden Actions

- Perform credential entry
- Parse or inspect token file contents
- Claim "reauth complete" if only browser opened
- Auto-select Google account
- Bypass 012 confirmation

## Runbook Reference

```
modules/platform_integration/youtube_auth/docs/SET1_REAUTH_OPERATOR_RUNBOOK.md
```

## Integration Points

- **AI Overseer**: Creates supervised_reauth task on invalid_grant
- **Claw/OpenClaw**: Executes under 012 supervision
- **WRE**: Records outcome in pattern memory
