# Set 1 Reauth Operator Runbook

**Document**: YT2 — YouTube Set 1 Reauth Operator Runbook Phase 1
**Status**: Active
**Last Updated**: 2026-04-19
**Owner**: 012 (manual browser action required)

---

## Current State Detection

### Quick Status Check

```bash
# Read the credential health artifact (no API calls)
cat modules/platform_integration/youtube_auth/reports/oauth_credential_health.json
```

### Status Vocabulary

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| `healthy` | Refresh token valid, quota available | None |
| `token_expired_or_revoked` | `invalid_grant` but cause indistinguishable | **Manual reauth** |
| `token_revoked` | User explicitly revoked in Google UI | Manual reauth |
| `quota_exhausted` | Daily 10K limit hit, resets midnight PST | Wait for reset |

### Current State (as of 2026-04-18)

```json
{
  "credential_sets": {
    "operational": [10],
    "dead": [1],
    "effective_daily_quota_estimate": 10000
  },
  "per_set": [
    {
      "set_id": 1,
      "account_label": "UnDaoDu / Move2Japan",
      "status": "token_expired_or_revoked",
      "operator_action": "python modules/platform_integration/youtube_auth/scripts/authorize_set1.py"
    },
    {
      "set_id": 10,
      "account_label": "FoundUps / antifaFM",
      "status": "healthy"
    }
  ]
}
```

**Interpretation**: Set 10 (antifaFM) is operational. Set 1 (UnDaoDu/Move2Japan) needs manual reauth.

---

## Reauth Procedure for Set 1

### Prerequisites

1. Access to UnDaoDu Google account credentials
2. Chrome browser (preferred per `browser_hint`)
3. Terminal with Python environment active

### Step-by-Step

**Step 1: Start the reauth script**

```bash
cd O:\Foundups-Agent
python modules/platform_integration/youtube_auth/scripts/authorize_set1.py
```

**Step 2: Browser opens automatically**

- Script opens Chrome to Google OAuth consent page
- If Chrome doesn't open, manually navigate to the URL printed in terminal

**Step 3: Authenticate**

- Sign in with **UnDaoDu** Google account
- Grant YouTube API permissions when prompted
- Scopes requested:
  - `youtube.force-ssl` (write access)
  - `youtube.readonly` (read access)

**Step 4: Return to terminal**

- Browser redirects to `localhost:8080`
- Script captures the authorization code automatically
- Terminal shows:
  ```
  [OK] Successfully authorized Set 1!
  [SAVE] Token saved to: credentials/oauth_token.json
  [OK] Successfully connected to channel: <channel_name>
  ```

**Step 5: Verify success** (see next section)

---

## Verification After Reauth

### Method 1: Run token check script

```bash
python modules/platform_integration/youtube_auth/scripts/check_all_tokens.py
```

Expected output for Set 1:
```
Set 1: [OK] Valid - Channel: Move2Japan
```

### Method 2: Trigger health artifact regeneration

The health artifact regenerates on next `get_authenticated_service()` call. Force it:

```bash
python -c "
from modules.platform_integration.youtube_auth.src.youtube_auth import get_authenticated_service
svc = get_authenticated_service()
print('[OK] Service obtained')
"
```

Then verify artifact:

```bash
cat modules/platform_integration/youtube_auth/reports/oauth_credential_health.json
```

Expected:
```json
{
  "credential_sets": {
    "operational": [1, 10],
    "dead": [],
    "effective_daily_quota_estimate": 20000
  }
}
```

### Method 3: Check token file timestamp

```bash
ls -la credentials/oauth_token.json
```

File should show today's date if reauth succeeded.

---

## Troubleshooting

### Script fails with "Client secret file not found"

```
[FAIL] Client secret file not found: credentials/client_secret.json
```

**Cause**: `credentials/client_secret.json` missing or misnamed.

**Fix**: Ensure the file exists. If lost, download from Google Cloud Console > APIs & Services > Credentials.

### Browser doesn't open

**Cause**: `webbrowser` module cannot find Chrome.

**Fix**: Set `CHROME_PATH` environment variable:
```bash
export CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
```

Or manually copy the URL from terminal output.

### Port 8080 in use

**Cause**: Another process using port 8080.

**Fix**: Set alternative port:
```bash
set OAUTH_PORT_SET1=8081
python modules/platform_integration/youtube_auth/scripts/authorize_set1.py
```

### "Access blocked" in browser

**Cause**: OAuth consent screen not configured for test users.

**Fix**: In Google Cloud Console > OAuth consent screen, add the UnDaoDu email to test users list.

### Token file created but health artifact still shows dead

**Cause**: Health artifact is a snapshot; regenerates on next auth call.

**Fix**: Run verification Method 2 above to trigger regeneration.

---

## Credential Set Reference

| Set | Account | Token File | Browser | Port |
|-----|---------|------------|---------|------|
| 1 | UnDaoDu / Move2Japan | `credentials/oauth_token.json` | Chrome | 8080 |
| 10 | FoundUps / antifaFM | `credentials/oauth_token10.json` | Edge | 8089 |

---

## Related Files

- **Health artifact**: `modules/platform_integration/youtube_auth/reports/oauth_credential_health.json`
- **Reauth script**: `modules/platform_integration/youtube_auth/scripts/authorize_set1.py`
- **Health module**: `modules/platform_integration/youtube_auth/src/oauth_health.py`
- **INTERFACE.md**: `modules/platform_integration/youtube_auth/INTERFACE.md` (status vocabulary)

---

## Automation Note

This runbook documents a **manual** procedure. The browser OAuth flow requires human interaction with Google's consent screen. 0102 agents cannot perform this step — only 012 can authorize.

After 012 completes reauth, stream resolver and quota management resume automatically without further intervention.
