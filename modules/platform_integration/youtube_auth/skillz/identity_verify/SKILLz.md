---
name: youtube_oauth_identity_verify
version: "1.0"
category: capability-uplift
autonomous: true
requires_012: false
evals: []
retirement_date: null
---

# youtube_oauth_identity_verify

## Purpose

Verify that credential Set N maps to the expected Google account/YouTube channel using safe API metadata or existing artifacts.

## Supervised Boundary (WSP 97)

- **Autonomous**: YES (if token exists and API read approved)
- **Credential inspection**: NO (uses token, does not read contents)
- **API calls**: YES (channels.list mine=True, 1 quota unit)

## Input

```yaml
set_id: 1 | 10
expected_channels:
  1: ["UC-LSSlOZwpGIRIYihaz8zCw", "UCfHM9Fw9HD-NwiS0seD_oIA"]  # Move2Japan, UnDaoDu
  10: ["UCSNTUXjAgpd4sgWYP0xoJgw", "UCVSmg5aOhP4tnQ9KFUg97qA"]  # FoundUps, antifaFM
```

## Verification Method

1. Load credentials for set_id (via get_authenticated_service)
2. Call `channels.list(part='snippet', mine=True)`
3. Extract channel_id from response
4. Compare to expected_channels[set_id]
5. Return identity_status

## Output

```yaml
identity_status: verified | mismatch | not_verified | error
set_id: int
observed_channel_id: str | null
observed_channel_title: str | null
expected_channel_ids: [list]
match_found: true | false
error: str | null
```

## Allowed Claims

- "Identity verified by channel ID" (when observed matches expected)
- "Identity mismatch" (when observed does not match expected)
- "Identity not verified" (when API call fails or no channel found)

## Forbidden Claims

- "Set 1 is UnDaoDu" without channel/account verification
- Any claim about Google account email
- Any claim about token contents

## Expected Channel Mapping

| Set | Account | Expected Channels |
|-----|---------|-------------------|
| 1 | UnDaoDu | Move2Japan (UC-LSSlOZwpGIRIYihaz8zCw), UnDaoDu (UCfHM9Fw9HD-NwiS0seD_oIA) |
| 10 | FoundUps | FoundUps (UCSNTUXjAgpd4sgWYP0xoJgw), antifaFM (UCVSmg5aOhP4tnQ9KFUg97qA) |

## Trigger

- After supervised_reauth completes
- On preflight when token valid but identity unknown
- Manual `/youtube-oauth-verify {set_id}` command

## Integration Points

- **AI Overseer**: Post-reauth verification
- **supervised_reauth**: Follow-up skill
- **health_check**: Identity status in health report
